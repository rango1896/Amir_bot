import asyncio
from telethon import events
import core
from core import client

art_active = False
art_name = ""
art_task = None

async def log_to_chat(g_id, text):
    """ارسال پیام خطا یا وضعیت به گروه برای اطلاع کاربر"""
    try:
        await client.send_message(g_id, text)
    except:
        pass

async def get_bot_msg(g_id):
    async for msg in client.iter_messages(g_id, limit=5):
        if msg.buttons and msg.sender and msg.sender.bot:
            return msg
    return None

async def wait_for_list(g_id, timeout=15):
    """صبر می‌کند تا لیست مارکت (پیامی بدون دکمه بازگشت) بیاید"""
    for _ in range(timeout):
        if not art_active: return None
        await asyncio.sleep(1)
        msg = await get_bot_msg(g_id)
        if msg:
            has_back = any("بازگشت" in btn.text for row in msg.buttons for btn in row)
            if not has_back:
                return msg
    return None

async def wait_for_detail(g_id, timeout=15):
    """صبر می‌کند تا صفحه جزئیات آرت (پیامی با دکمه بازگشت) بیاید"""
    for _ in range(timeout):
        if not art_active: return None
        await asyncio.sleep(1)
        msg = await get_bot_msg(g_id)
        if msg:
            has_back = any("بازگشت" in btn.text for row in msg.buttons for btn in row)
            if has_back:
                return msg
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
        clicked_texts = set()
            
        try:
            # ۱. ارسال پیو آرت
            await client.send_message(g_id, "پیو آرت")
            await asyncio.sleep(5)
            
            # ۲. کلیک روی مارکت آرت
            msg = await get_bot_msg(g_id)
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
                await log_to_chat(g_id, "⚠️ گیر کردم: دکمه مارکت آرت پیدا نشد. ۶۰ ثانیه دیگه تلاش می‌کنم.")
                await asyncio.sleep(60)
                continue
                
            # ۳. صبر برای لود شدن لیست مارکت
            list_msg = await wait_for_list(g_id)
            if not list_msg:
                await log_to_chat(g_id, "⚠️ گیر کردم: لیست مارکت باز نشد. دوباره تلاش می‌کنم.")
                continue
            
            # ۴. چرخه صفحه‌بندی
            while art_active:
                list_msg = await get_bot_msg(g_id)
                if not list_msg:
                    await log_to_chat(g_id, "⚠️ گیر کردم: پیام لیست پیدا نشد.")
                    break
                
                # پیدا کردن دکمه‌های آرت و دکمه صفحه بعد
                target_btn = None
                next_btn = None
                
                for row in list_msg.buttons:
                    for btn in row:
                        txt = btn.text
                        if art_name in txt and "مارکت" not in txt and "بعد" not in txt and "بازگشت" not in txt:
                            if txt not in clicked_texts:
                                target_btn = btn
                        elif any(kw in txt for kw in ["بعد", "next", "›", "⏭", "برو", "➡️"]):
                            next_btn = btn
                
                # ۵. اگه آرت پیدا شد، روش کلیک کن
                if target_btn:
                    clicked_texts.add(target_btn.text)
                    await target_btn.click()
                    await asyncio.sleep(4)
                    
                    # صبر برای باز شدن صفحه جزئیات
                    detail_msg = await wait_for_detail(g_id)
                    if detail_msg:
                        try:
                            await client.forward_messages('me', detail_msg.id, g_id)
                        except Exception as e:
                            await log_to_chat(g_id, f"⚠️ گیر کردم: فوروارد ارور داد: {e}")
                        
                        # کلیک روی دکمه بازگشت
                        back_clicked = False
                        for row in detail_msg.buttons:
                            for btn in row:
                                if "بازگشت" in btn.text:
                                    await btn.click()
                                    back_clicked = True
                                    break
                            if back_clicked: break
                        
                        # صبر برای برگشتن لیست مارکت
                        await wait_for_list(g_id)
                    else:
                        await log_to_chat(g_id, "⚠️ گیر کردم: صفحه جزئیات آرت لود نشد.")
                    
                    continue # برمی‌گردیم سراغ چک کردن لیست برای بقیه آرت‌ها
                
                # ۶. اگه آرتی تو این صفحه پیدا نشد، بره صفحه بعد
                if next_btn and art_active:
                    await log_to_chat(g_id, "➡️ رفتن به صفحه بعد مارکت...")
                    try:
                        await next_btn.click()
                    except:
                        pass
                    # صبر برای لود شدن صفحه جدید
                    new_list = await wait_for_list(g_id)
                    if not new_list:
                        await log_to_chat(g_id, "⚠️ گیر کردم: صفحه بعد لود نشد.")
                        break
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
