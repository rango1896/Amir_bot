import asyncio
from telethon import events
import core
from core import client

art_active = False
art_name = ""
art_task = None

async def click_btn_by_text(g_id, text, exact=False, timeout=10):
    """تابع کمکی: صبر می‌کنه تا دکمه با متن مشخص شده بیاد و روش کلیک می‌کنه"""
    for _ in range(timeout):
        if not art_active: return False
        await asyncio.sleep(1)
        async for msg in client.iter_messages(g_id, limit=3):
            if msg.buttons and msg.sender and msg.sender.bot:
                for row in msg.buttons:
                    for btn in row:
                        if (exact and btn.text == text) or (not exact and text in btn.text):
                            try:
                                await btn.click()
                                return True
                            except:
                                pass
    return False

async def get_latest_bot_msg(g_id):
    """پیدا کردن آخرین پیام ربات بازی که دکمه داره"""
    async for msg in client.iter_messages(g_id, limit=5):
        if msg.buttons and msg.sender and msg.sender.bot:
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
        try:
            # ۱. ارسال پیو آرت
            await client.send_message(g_id, "پیو آرت")
            print("📤 پیو آرت فرستاده شد. منتظر باز شدن مارکت...")
            await asyncio.sleep(4)
            
            # ۲. کلیک روی مارکت آرت
            if not await click_btn_by_text(g_id, "مارکت آرت", timeout=15):
                print("⚠️ دکمه مارکت آرت پیدا نشد. ۶۰ ثانیه دیگه تلاش میشه.")
                await asyncio.sleep(60)
                continue
                
            await asyncio.sleep(4) # صبر برای لود شدن لیست مارکت
            
            clicked_ids = set() # ذخیره آیدی مخفی دکمه‌ها (Callback Data) برای جلوگیری از کلیک مجدد روی همون دکمه
            
            # ۳. چرخه صفحه‌بندی
            while art_active:
                list_msg = await get_latest_bot_msg(g_id)
                if not list_msg:
                    print("⚠️ لیست مارکت پیدا نشد. استارت مجدد...")
                    break
                    
                # پیدا کردن دکمه‌های آرت و دکمه صفحه بعد تو این صفحه
                art_btn = None
                next_btn = None
                
                for row in list_msg.buttons:
                    for btn in row:
                        txt = btn.text
                        # اگه دکمه آرت بود و هنوز کلیک نشده بود (بر اساس آیدی مخفی)
                        if art_name in txt and "مارکت" not in txt and "بعد" not in txt and "بازگشت" not in txt:
                            btn_id = getattr(btn, 'data', txt) # گرفتن آیدی مخفی دکمه
                            if btn_id not in clicked_ids:
                                art_btn = btn
                        # اگه دکمه صفحه بعد بود
                        elif "بعد" in txt or "›" in txt or "»" in txt or "next" in txt.lower() or "➡️" in txt:
                            next_btn = btn
                            
                # ۴. اگه آرت پیدا شد، روش کلیک کن
                if art_btn:
                    btn_id = getattr(art_btn, 'data', art_btn.text)
                    try:
                        await art_btn.click()
                        clicked_ids.add(btn_id) # ثبت آیدی مخفی دکمه
                        print(f"🔍 کلیک روی آرت: {art_btn.text}")
                        await asyncio.sleep(3) # صبر برای لود شدن اطلاعات آرت
                        
                        # فوروارد کردن پیام آرت به پیام ذخیره شده
                        async for detail in client.iter_messages(g_id, limit=3):
                            if detail.sender and detail.sender.bot:
                                if "🖼" in (detail.text or "") or "قیمت" in (detail.text or ""):
                                    try:
                                        await client.forward_messages('me', detail.id, g_id)
                                        print("✅ آرت فوروارد شد.")
                                    except Exception as e:
                                        print(f"خطا در فوروارد: {e}")
                                    break
                        
                        # کلیک روی دکمه بازگشت برای برگشت به لیست
                        await click_btn_by_text(g_id, "بازگشت", timeout=10)
                        await asyncio.sleep(3) # صبر برای لود شدن لیست قبلی
                        continue # میره سراغ بررسی دوباره همون صفحه
                    except Exception as e:
                        print(f"خطا در کلیک دکمه: {e}")
                
                # ۵. اگه آرتی پیدا نشد، بره صفحه بعد
                if next_btn and art_active:
                    print("➡️ رفتن به صفحه بعد...")
                    try:
                        await next_btn.click()
                    except:
                        pass
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
