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

async def get_list_msg(g_id):
    """پیدا کردن پیام لیست مارکت (پیامی که قیمت یا 🖼 توش نیست)"""
    # پیام‌ها رو از جدیدترین به قدیمی می‌خونه و limit رو گذاشتم روی ۱۰۰۰ تا تو گپ‌های شلوغ گم نشه
    async for msg in client.iter_messages(g_id, limit=1000):
        if msg.buttons and msg.sender and msg.sender.bot:
            text = msg.text or ""
            # پیام لیست رو تشخیص میدیم (پیام جزئیات نیست)
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
        clicked_ids = set() # یادگاری دکمه‌هایی که کلیک کردیم
            
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
                
            await asyncio.sleep(5) # صبر برای لود شدن لیست
            
            # ۳. چرخه صفحه‌بندی
            while art_active:
                list_msg = await get_list_msg(g_id)
                if not list_msg:
                    # اگه لیست پیدا نشد، از اول شروع نکن، فقط ۳ ثانیه صبر کن و دوباره چک کن
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
                    
                    # چون لیست پاک نمیشه، فقط صبر می‌کنیم تا پیام جزئیات بیاد
                    detail_msg = await get_detail_msg(g_id, timeout=10)
                    if detail_msg:
                        try:
                            await client.forward_messages('me', detail_msg.id, g_id)
                            print("✅ آرت فوروارد شد.")
                        except Exception as e:
                            await log_to_chat(g_id, f"⚠️ گیر کردم: فوروارد ارور داد: {e}")
                    else:
                        await log_to_chat(g_id, "⚠️ گیر کردم: پیام جزئیات آرت لود نشد.")
                    
                    # برمی‌گردیم به سراغ همون لیست برای کلیک روی آرت بعدی
                    continue 
                
                # ۵. اگه تو این لیست دیگه آرتی نبود، بره صفحه بعد
                if next_btn and art_active:
                    print("➡️ تلاش برای رفتن به صفحه بعد...")
                    old_list_id = list_msg.id
                    
                    # سیستم تلاش مجدد برای دکمه بعدی
                    clicked_next_successfully = False
                    for _ in range(10): # ۱۰ بار تلاش می‌کنه (هر بار ۳ ثانیه)
                        if not art_active: break
                        try:
                            await next_btn.click()
                        except:
                            pass # اگه کلیک ارور داد، دوباره تلاش می‌کنیم
                        
                        await asyncio.sleep(3) # ۳ ثانیه صبر برای لود شدن لیست جدید
                        
                        new_list_msg = await get_list_msg(g_id)
                        # اگه پیام لیست عوض شد، یعنی صفحه بعد لود شده
                        if new_list_msg and new_list_msg.id != old_list_id:
                            print("✅ صفحه بعد لود شد.")
                            clicked_next_successfully = True
                            break
                        else:
                            print("⏳ لیست عوض نشد، دوباره روی بعدی کلیک می‌کنم...")
                    
                    if not clicked_next_successfully:
                        await log_to_chat(g_id, "ℹ️ به انتهای مارکت رسیدیم یا ربات بازی جواب نمیده. ۶۰ ثانیه دیگه چرخه رو از اول شروع می‌کنم.")
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
