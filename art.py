import asyncio
from telethon import events
import core
from core import client

art_active = False
art_name = ""
art_task = None


async def log_to_chat(g_id, text):
    try:
        await client.send_message(g_id, text)
    except:
        pass


def _is_list_text(text):
    """پیام لیست (منو / گزینه‌های شیشه‌ای) هیچ‌وقت 🖼 یا قیمت توش نیست"""
    return "🖼" not in text and "قیمت" not in text


def _is_detail_text(text):
    """پیام جزئیات یه آرت همیشه 🖼 یا قیمت داره"""
    return "🖼" in text or "قیمت" in text


async def find_bot_msg(g_id, predicate, min_id=0, limit=1000, require_buttons=False):
    """جدیدترین پیام ربات بازی رو پیدا می‌کنه که predicate(text) درست باشه.
    min_id: فقط پیام‌های بعد از این آیدی رو در نظر می‌گیره -> تو گروه شلوغ
    باعث میشه یه پیام قدیمی/اشتباهی رو دوباره برنداریم."""
    async for msg in client.iter_messages(g_id, limit=limit, min_id=min_id):
        if not (msg.sender and msg.sender.bot):
            continue
        if require_buttons and not msg.buttons:
            continue
        if predicate(msg.text or ""):
            return msg
    return None


async def wait_for_list(g_id, min_id, timeout=20, delay=1.5):
    """صبر می‌کنه تا پیام لیست (دکمه‌دار، بدون 🖼/قیمت) با آیدی بزرگتر از
    min_id بیاد. برای: باز کردن مارکت، و برای صفحه‌ی بعدی."""
    tries = max(1, int(timeout / delay))
    for _ in range(tries):
        if not art_active:
            return None
        msg = await find_bot_msg(g_id, _is_list_text, min_id=min_id, require_buttons=True)
        if msg:
            return msg
        await asyncio.sleep(delay)
    return None


async def wait_for_detail(g_id, min_id, timeout=15, delay=1.5):
    """صبر می‌کنه تا پیام جزئیات آرت (🖼/قیمت) بیاد. طبق رفتار ربات بازی،
    این همیشه یه پیام تازه‌ست (نه ادیتِ چیز قبلی)."""
    tries = max(1, int(timeout / delay))
    for _ in range(tries):
        if not art_active:
            return None
        msg = await find_bot_msg(g_id, _is_detail_text, min_id=min_id, require_buttons=False)
        if msg:
            return msg
        await asyncio.sleep(delay)
    return None


@client.on(events.NewMessage(outgoing=True, pattern=r'^پیدا کردن آرت\s+(.+)$'))
async def art_on(event):
    global art_active, art_name, art_task
    if not core.pio_active_group:
        return await event.reply("❗ اول با دستور `اد گروه` یه گروه هدف ثبت کن!")
    if not art_active:
        art_active = True
        art_name = event.pattern_match.group(1).strip()
        await event.reply(f"🎨 جستجوی آرت '{art_name}' **روشن** شد.")
        if art_task is None or art_task.done():
            art_task = asyncio.create_task(art_loop())
    else:
        await event.reply("❗ جستجوی آرت از قبل روشنه.")


@client.on(events.NewMessage(outgoing=True, pattern=r'^آرت متوقف$'))
async def art_off(event):
    global art_active, art_task
    art_active = False
    if art_task and not art_task.done():
        art_task.cancel()
    await event.reply("🛑 جستجوی آرت **متوقف** شد.")


async def art_loop():
    while art_active:
        if not core.pio_active_group:
            await asyncio.sleep(5)
            continue

        g_id = core.pio_active_group

        try:
            # ---------- مرحله ۱: باز کردن مارکت (فقط همین یه بار) ----------
            await client.send_message(g_id, "پیو آرت")
            await asyncio.sleep(4)

            open_msg = await find_bot_msg(g_id, _is_list_text, limit=200, require_buttons=True)
            market_btn = None
            if open_msg:
                for row in open_msg.buttons:
                    for btn in row:
                        if "مارکت آرت" in btn.text:
                            market_btn = btn
                            break
                    if market_btn:
                        break

            if not market_btn:
                await log_to_chat(g_id, "⚠️ گیر کردم: دکمه مارکت آرت پیدا نشد. ۶۰ ثانیه دیگه دوباره تلاش می‌کنم.")
                await asyncio.sleep(60)
                continue

            await market_btn.click()
            list_msg = await wait_for_list(g_id, min_id=open_msg.id, timeout=20)
            if not list_msg:
                await log_to_chat(g_id, "⚠️ گیر کردم: لیست مارکت لود نشد. ۶۰ ثانیه دیگه دوباره تلاش می‌کنم.")
                await asyncio.sleep(60)
                continue

            # ---------- مرحله ۲: چرخه‌ی همیشگی جستجو -> کلیک -> بعدی ----------
            clicked_ids = set()   # دکمه‌هایی که تو همین صفحه کلیک کردیم
            last_seen_id = list_msg.id
            no_progress = 0

            while art_active:
                target_btn = None
                next_btn = None

                for row in list_msg.buttons:
                    for btn in row:
                        btn_id = getattr(btn, 'data', btn.text)
                        if art_name in btn.text and "مارکت" not in btn.text and "بعد" not in btn.text:
                            if btn_id not in clicked_ids:
                                target_btn = btn
                        elif any(kw in btn.text for kw in ["بعد", "next", "›", "⏭", "برو", "➡️"]):
                            next_btn = btn

                # ---- آرت پیدا شد: کلیک، صبر برای پیام جزئیات، فوروارد ----
                if target_btn:
                    btn_id = getattr(target_btn, 'data', target_btn.text)
                    clicked_ids.add(btn_id)
                    await target_btn.click()
                    print(f"🔍 کلیک روی آرت: {target_btn.text}")

                    detail_msg = await wait_for_detail(g_id, min_id=last_seen_id, timeout=15)
                    if detail_msg:
                        last_seen_id = detail_msg.id
                        try:
                            await client.forward_messages('me', detail_msg.id, g_id)
                            print("✅ آرت فوروارد شد.")
                        except Exception as e:
                            await log_to_chat(g_id, f"⚠️ گیر کردم: فوروارد ارور داد: {e}")
                    else:
                        await log_to_chat(g_id, "⚠️ گیر کردم: پیام جزئیات آرت لود نشد (احتمالاً گروه شلوغه).")

                    # لیست خودش عوض نمیشه، پس دوباره همین list_msg رو با
                    # clicked_ids آپدیت‌شده چک می‌کنیم (نه از اول)
                    continue

                # ---- تو این صفحه آرتی نمونده: برو صفحه بعد ----
                if next_btn:
                    print("➡️ تلاش برای رفتن به صفحه بعد...")
                    old_id = list_msg.id
                    old_text = list_msg.text or ""
                    new_list = None

                    for attempt in range(5):
                        if not art_active:
                            break
                        try:
                            await next_btn.click()
                        except Exception:
                            pass

                        # حالت ۱: پیام لیست جدید با آیدی بزرگتر اومده
                        new_list = await wait_for_list(g_id, min_id=old_id, timeout=8, delay=1.5)
                        if new_list:
                            break

                        # حالت ۲: خودِ همون پیام ادیت شده (آیدی عوض نمیشه)
                        try:
                            refreshed = await client.get_messages(g_id, ids=old_id)
                        except Exception:
                            refreshed = None
                        if refreshed and (refreshed.text or "") != old_text:
                            new_list = refreshed
                            break

                        print("⏳ صفحه هنوز آپدیت نشده، دوباره روی بعدی کلیک می‌کنم...")

                    if new_list:
                        print("✅ صفحه بعد لود شد.")
                        list_msg = new_list
                        last_seen_id = new_list.id
                        clicked_ids = set()
                        no_progress = 0
                        continue
                    else:
                        # به‌جای شروع از اول (پیو آرت)، فقط صبر می‌کنیم و
                        # همین چرخه رو دوباره امتحان می‌کنیم
                        no_progress += 1
                        if no_progress % 3 == 1:
                            await log_to_chat(
                                g_id,
                                "⏳ صفحه بعد پیدا نشد (احتمالاً گروه شلوغه)، منتظر می‌مونم و دوباره امتحان می‌کنم..."
                            )
                        await asyncio.sleep(8)
                        continue
                else:
                    # نه آرتی مونده نه دکمه بعدی؛ صبر می‌کنیم و همین پیام رو
                    # دوباره می‌خونیم (شاید ادیت بشه) - بدون این‌که از اول شروع کنیم
                    await asyncio.sleep(10)
                    try:
                        refreshed = await client.get_messages(g_id, ids=list_msg.id)
                    except Exception:
                        refreshed = None
                    if refreshed and refreshed.buttons:
                        list_msg = refreshed
                    continue

        except asyncio.CancelledError:
            break
        except Exception as e:
            await log_to_chat(g_id, f"❌ گیر کردم: یه خطای کلی پیش اومده: {e}")
            await asyncio.sleep(10)
