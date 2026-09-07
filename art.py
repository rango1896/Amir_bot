import asyncio
from telethon import events
import core
from core import client

art_active = False
art_name = ""
art_task = None

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

async def click_button_if_exists(g_id, keywords, timeout=15):
    """تابع کمکی: صبر می‌کنه تا دکمه بیاد و روش کلیک می‌کنه"""
    for _ in range(timeout):
        if not art_active: return False
        await asyncio.sleep(1)
        async for msg in client.iter_messages(g_id, limit=5):
            if msg.buttons and msg.sender and msg.sender.bot:
                for row in msg.buttons:
                    for btn in row:
                        if any(kw in btn.text for kw in keywords):
                            try:
                                await btn.click()
                                return True
                            except:
                                pass
    return False

async def art_loop():
    while art_active:
        if not core.pio_active_group:
            await asyncio.sleep(5)
            continue
            
        g_id = core.pio_active_group
        try:
            # ۱. ارسال پیو آرت
            await client.send_message(g_id, "پیو آرت")
            print("📤 پیو آرت فرستاده شد. منتظر باز شدن مارکت...")
            await asyncio.sleep(3)
            
            # ۲. کلیک روی مارکت آرت (با ۱۵ ثانیه انتظار)
            opened = await click_button_if_exists(g_id, ["مارکت آرت"], timeout=15)
            if not opened:
                print("⚠️ دکمه مارکت آرت پیدا نشد. ۶۰ ثانیه دیگه تلاش میشه.")
                await asyncio.sleep(60)
                continue
                
            await asyncio.sleep(4) # صبر برای لود شدن لیست مارکت
            
            # ۳. چرخه صفحه‌بندی (اینجا ربات صفحه به صفحه میره جلو)
            while art_active:
                list_msg = None
                # پیدا کردن پیام لیست مارکت
                async for msg in client.iter_messages(g_id, limit=5):
                    if msg.buttons and msg.sender and msg.sender.bot:
                        list_msg = msg
                        break
                        
                if not list_msg:
                    print("⚠️ لیست مارکت پیدا نشد. استارت مجدد...")
                    break
                    
                art_btns = []
                next_btn = None
                
                for row in list_msg.buttons:
                    for btn in row:
                        txt = btn.text
                        if art_name in txt and "مارکت" not in txt and "بعد" not in txt and "بازگشت" not in txt:
                            art_btns.append(btn)
                        elif "بعد" in txt or "›" in txt or "»" in txt or "next" in txt.lower():
                            next_btn = btn
                            
                # ۴. کلیک روی آرت‌های پیدا شده تو این صفحه
                if art_btns:
                    for btn in art_btns:
                        if not art_active: break
                        await btn.click()
                        print(f"🔍 کلیک روی آرت: {btn.text}")
                        await asyncio.sleep(3) # صبر برای لود شدن اطلاعات آرت
                        
                        # فوروارد کردن پیام آرت به پیام ذخیره شده
                        async for detail in client.iter_messages(g_id, limit=3):
                            if detail.sender and detail.sender.bot and detail.id != list_msg.id:
                                if "🖼" in (detail.text or "") or "قیمت" in (detail.text or ""):
                                    try:
                                        await client.forward_messages('me', detail.id, g_id)
                                        print("✅ آرت فوروارد شد.")
                                    except Exception as e:
                                        print(f"خطا در فوروارد: {e}")
                                    break
                        
                        # کلیک روی دکمه بازگشت برای برگشت به لیست
                        await asyncio.sleep(1)
                        clicked_back = await click_button_if_exists(g_id, ["بازگشت"], timeout=10)
                        if clicked_back:
                            await asyncio.sleep(3) # صبر برای لود شدن لیست قبلی
                        else:
                            print("⚠️ دکمه بازگشت پیدا نشد.")
                            break
                
                # ۵. رفتن به صفحه بعد
                if next_btn and art_active:
                    print("➡️ رفتن به صفحه بعد...")
                    await next_btn.click()
                    await asyncio.sleep(4)
                else:
                    print("ℹ️ به انتهای مارکت رسیدیم. ۶۰ ثانیه دیگه دوباره چک میشه...")
                    break
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"❌ خطا در سیستم آرت: {e}")
            await asyncio.sleep(10)
            
        if art_active:
            await asyncio.sleep(60) # صبر قبل از شروع دوباره کل چرخه
