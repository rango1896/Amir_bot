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

async def get_list_msg(g_id, min_id=0):
    """پیدا کردن پیام لیست مارکت (پیامی که قیمت یا 🖼 توش نیست)
    min_id: اگه صفر نباشه، فقط پیام‌هایی که آیدیشون از این بزرگتره در نظر گرفته میشه
    (برای اینکه بعد از کلیک 'بعدی' اشتباهی یه پیام قدیمی رو دوباره برنداریم)
    """
    async for msg in client.iter_messages(g_id, limit=1000, min_id=min_id):
        if msg.buttons and msg.sender and msg.sender.bot:
            text = msg.text or ""
            if "🖼" not in text and "قیمت" not in text:
                return msg
    return None

async def get_detail_msg(g_id, timeout=10):
    """پیدا کردن پیام جزئیات آرت (پیامی که قیمت یا 🖼 داره)"""
    for _ in range(timeout):
        if not art_active: return None
        await asyncio.sleep(1)
        async for msg in client.iter_messages(g_id, limit=1000):
            if msg.sender and msg.sender.bot:
                text = msg.text or ""
                if "🖼" in text or "قیمت" in text:
                    return msg
    return None

async def wait_for_page_update(g_id, old_msg, next_btn, max_attempts=6, tries_per_attempt=3, delay=3):
    """
    روی دکمه 'بعدی' کلیک می‌کنه و صبر می‌کنه تا صفحه واقعاً عوض بشه.

    نکته مهم: خیلی از ربات‌های بازی برای صفحه‌بندی، به‌جای فرستادن پیام جدید،
    همون پیام قبلی رو 'ادیت' می‌کنن. یعنی آیدی پیام عوض نمیشه، فقط متن/دکمه‌هاش
    عوض میشه. کد قبلی فقط آیدی رو چک می‌کرد، برای همین توی این حالت هیچ‌وقت
    متوجه لود شدن صفحه بعد نمیشد و بعد از چند تلاش، کل چرخه رو از اول شروع می‌کرد.

    این نسخه دو حالت رو چک می‌کنه:
      ۱. همون پیام قبلی ادیت شده (متنش با قبل فرق کرده)
      ۲. یه پیام لیست جدید با آیدی بزرگتر از قبلی اومده
    """
    old_id = old_msg.id
    old_text = old_msg.text or ""

    for attempt in range(max_attempts):
        if not art_active:
            return None
        try:
            await next_btn.click()
        except Exception:
            pass

        for _ in range(tries_per_attempt):
            if not art_active:
                return None
            await asyncio.sleep(delay)

            # حالت ۱: چک کن همون پیام ادیت شده یا نه
            try:
                refreshed = await client.get_messages(g_id, ids=old_id)
            except Exception:
                refreshed = None
            if refreshed and (refreshed.text or "") != old_text:
                return refreshed

            # حالت ۲: چک کن پیام لیست جدیدی بعد از این اومده یا نه
            newer = await get_list_msg(g_id, min_id=old_id)
            if newer:
                return newer

        print("⏳ صفحه هنوز آپدیت نشده، دوباره روی بعدی کلیک می‌کنم...")

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
        clicked_ids = set()  # یادگاری دکمه‌هایی که کلیک کردیم

        try:
            # ۱. ارسال پیو آرت
            await client.send_message(g_id, "پیو آرت")
            await asyncio.sleep(5)

            # ۲. کلیک روی مارکت آرت
            msg = await get_list_msg(g_id)
            opened_market = False
            if msg:
                for row in msg.buttons:
                    for btn in row:
                        if "مارکت آرت" in btn.text:
                            await btn.click()
                            opened_market = True
                            break
                    if opened_market: break

            if not opened_market:
                await log_to_chat(g_id, "⚠️ گیر کردم: دکمه مارکت آرت پیدا نشد.")
                await asyncio.sleep(60)
                continue

            await asyncio.sleep(5)  # صبر برای لود شدن لیست

            # ۳. چرخه صفحه‌بندی
            no_progress_count = 0

            while art_active:
                list_msg = await get_list_msg(g_id)
                if not list_msg:
                    await asyncio.sleep(3)
                    continue

                target_btn = None
                next_btn = None

                # پیدا کردن دکمه آرت و دکمه بعدی تو همین لیست
                for row in list_msg.buttons:
                    for btn in row:
                        btn_id = getattr(btn, 'data', btn.text)
                        if art_name in btn.text and "مارکت" not in btn.text and "بعد" not in btn.text:
                            if btn_id not in clicked_ids:
                                target_btn = btn
                        elif any(kw in btn.text for kw in ["بعد", "next", "›", "⏭", "برو", "➡️"]):
                            next_btn = btn

                # ۴. اگه آرت پیدا شد، روش کلیک کن
                if target_btn:
                    btn_id = getattr(target_btn, 'data', target_btn.text)
                    clicked_ids.add(btn_id)
                    await target_btn.click()
                    print(f"🔍 کلیک روی آرت: {target_btn.text}")

                    detail_msg = await get_detail_msg(g_id, timeout=10)
                    if detail_msg:
                        try:
                            await client.forward_messages('me', detail_msg.id, g_id)
                            print("✅ آرت فوروارد شد.")
                        except Exception as e:
                            await log_to_chat(g_id, f"⚠️ گیر کردم: فوروارد ارور داد: {e}")
                    else:
                        await log_to_chat(g_id, "⚠️ گیر کردم: پیام جزئیات آرت لود نشد.")

                    continue

                # ۵. اگه تو این لیست دیگه آرتی نبود، بره صفحه بعد
                if next_btn and art_active:
                    print("➡️ تلاش برای رفتن به صفحه بعد...")

                    updated_msg = await wait_for_page_update(g_id, list_msg, next_btn)

                    if updated_msg:
                        print("✅ صفحه بعد لود شد.")
                        clicked_ids = set()  # صفحه عوض شد، دکمه‌های صفحه قبل دیگه معتبر نیستن
                        no_progress_count = 0
                        continue
                    else:
                        # به‌جای شروع کردن از اول (پیو آرت)، فقط صبر می‌کنیم و دوباره امتحان می‌کنیم
                        no_progress_count += 1
                        if no_progress_count % 3 == 0:
                            await log_to_chat(
                                g_id,
                                "⏳ صفحه بعد هنوز لود نشده، منتظر می‌مونم و بدون شروع از اول دوباره امتحان می‌کنم..."
                            )
                        await asyncio.sleep(5)
                        continue
                else:
                    await log_to_chat(g_id, "ℹ️ به انتهای مارکت رسیدیم. ۶۰ ثانیه دیگه چرخه رو از اول شروع می‌کنم.")
                    break

        except asyncio.CancelledError:
            break
        except Exception as e:
            await log_to_chat(g_id, f"❌ گیر کردم: یه خطای کلی پیش اومده: {e}")
            await asyncio.sleep(10)

        if art_active:
            await asyncio.sleep(60)
