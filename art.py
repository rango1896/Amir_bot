import asyncio
from telethon import events
import core
from core import client

art_active = False
art_name = ""
art_task = None

async def get_bot_msg(g_id):
    """آخرین پیام ربات بازی که دکمه داره رو پیدا می‌کنه"""
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
        clicked_texts = set() # ذخیره اسم دکمه‌هایی که کلیک کردیم تا دوباره روشون کلیک نکنیم
            
        try:
            # ۱. ارسال پیو آرت
            await client.send_message(g_id, "پیو آرت")
            print("📤 پیو آرت فرستاده شد...")
            await asyncio.sleep(5)
            
            # ۲. پیدا کردن و کلیک روی مارکت آرت
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
                print("⚠️ مارکت آرت پیدا نشد. ۶۰ ثانیه دیگه تلاش میشه.")
                await asyncio.sleep(60)
                continue
                
            await asyncio.sleep(5) # صبر برای لود شدن لیست مارکت
            
            # ۳. چرخه صفحه‌بندی
            while art_active:
                list_msg = await get_bot_msg(g_id)
                if not list_msg:
                    print("⚠️ لیست مارکت پیدا نشد. استارت مجدد...")
                    break
                
                # پیدا کردن دکمه‌های آرت و دکمه صفحه بعد تو این صفحه
                target_btn = None
                next_btn = None
                
                for row in list_msg.buttons:
                    for btn in row:
                        txt = btn.text
                        if art_name in txt and "مارکت" not in txt and "بعد" not in txt and "بازگشت" not in txt:
                            if txt not in clicked_texts: # اگه هنوز روش کلیک نکرده بودیم
                                target_btn = btn
                        elif "بعد" in txt or "next" in txt.lower() or "›" in txt or "⏭" in txt or "برو" in txt or "➡️" in txt:
                            next_btn = btn
                
                # ۴. اگه تو این لیست یه آرت جدید پیدا کردیم
                if target_btn:
                    clicked_texts.add(target_btn.text) # یادگاری می‌گیریم که کلیکش کردیم
                    await target_btn.click()
                    print(f"🔍 کلیک روی آرت: {target_btn.text}")
                    await asyncio.sleep(4) # صبر برای لود شدن صفحه جزئیات
                    
                    # فوروارد کردن پیام جزئیات
                    detail_msg = await get_bot_msg(g_id)
                    if detail_msg:
                        try:
                            await client.forward_messages('me', detail_msg.id, g_id)
                            print("✅ آرت فوروارد شد.")
                        except Exception as e:
                            print(f"خطا در فوروارد: {e}")
                        
                        # کلیک روی دکمه بازگشت
                        back_clicked = False
                        for row in detail_msg.buttons:
                            for btn in row:
                                if "بازگشت" in btn.text:
                                    await btn.click()
                                    back_clicked = True
                                    break
                            if back_clicked: break
                        
                        if not back_clicked and list_msg: # اگه دکمه بازگشت تو جزئیات نبود، از تو لیست بزنیم
                            for row in list_msg.buttons:
                                for btn in row:
                                    if "بازگشت" in btn.text:
                                        await btn.click()
                                        back_clicked = True
                                        break
                                if back_clicked: break

                        await asyncio.sleep(4) # صبر برای برگشتن لیست
                    
                    continue # برمی‌گردیم اول حلقه تا لیست رو دوباره چک کنیم به دنبال بقیه آرت‌ها
                
                # ۵. اگه تو این لیست دیگه آرتی پیدا نشد، بره صفحه بعد
                if next_btn and art_active:
                    print("➡️ رفتن به صفحه بعد...")
                    try:
                        await next_btn.click()
                    except:
                        pass
                    await asyncio.sleep(5) # صبر برای لود شدن صفحه جدید
                else:
                    print("ℹ️ به انتهای مارکت رسیدیم. ۶۰ ثانیه دیگه دوباره چک میشه...")
                    break
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"❌ خطا در سیستم آرت: {e}")
            await asyncio.sleep(10)
            
        if art_active:
            await asyncio.sleep(60)
