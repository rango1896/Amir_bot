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
        list_msg_id = None  # ذخیره آیدی پیام لیست که گم نشه
        last_detail_id = 0  # ذخیره آیدی آخرین پیامی که فوروارد کردیم
            
        try:
            # ۱. ارسال پیو آرت
            await client.send_message(g_id, "پیو آرت")
            await asyncio.sleep(5)
            
            # ۲. پیدا کردن و کلیک روی مارکت آرت
            opened_market = False
            async for msg in client.iter_messages(g_id, limit=15):
                if msg.buttons and msg.sender and msg.sender.bot:
                    for row in msg.buttons:
                        for btn in row:
                            if "مارکت آرت" in btn.text:
                                await btn.click()
                                opened_market = True
                                break
                        if opened_market: break
                    if opened_market: break
            
            if not opened_market:
                await log_to_chat(g_id, "⚠️ گیر کردم: دکمه مارکت آرت پیدا نشد.")
                await asyncio.sleep(60)
                continue
                
            await asyncio.sleep(5) # صبر برای لود شدن لیست
            
            # ۳. پیدا کردن آیدی پیام لیست مارکت
            # چون گروه شلوغه، فقط ۱۵ پیام آخر رو چک میکنیم تا لیست رو پیدا کنیم
            async for msg in client.iter_messages(g_id, limit=15):
                if msg.buttons and msg.sender and msg.sender.bot:
                    text = msg.text or ""
                    if "بازار فن‌آرت" in text and "🖼" not in text:
                        list_msg_id = msg.id
                        break
            
            if not list_msg_id:
                await log_to_chat(g_id, "⚠️ گیر کردم: پیام لیست مارکت پیدا نشد.")
                await asyncio.sleep(60)
                continue
                
            # ۴. چرخه صفحه‌بندی (حالا که آیدی رو داریم، دیگه گم نمیشه)
            while art_active:
                # فراخوانی مستقیم پیام لیست با آیدی (حتی اگه 100 تا پیام اومده باشه)
                list_msg = await client.get_messages(g_id, ids=list_msg_id)
                if not list_msg or not list_msg.buttons:
                    await log_to_chat(g_id, "⚠️ گیر کردم: لیست مارکت پاک شده یا دکمه‌هاش از بین رفتن.")
                    break
                
                target_btns = []
                next_btn = None
                
                # پیدا کردن دکمه‌های آرت و دکمه بعدی تو همین لیست
                for row in list_msg.buttons:
                    for btn in row:
                        txt = btn.text
                        if art_name in txt and "مارکت" not in txt and "بعد" not in txt and "قبلی" not in txt:
                            target_btns.append(btn)
                        elif "بعدی" in txt and ("▶️" in txt or "◀️" in txt or "next" in txt.lower()):
                            next_btn = btn
                
                # ۵. کلیک روی آرت‌های پیدا شده
                if target_btns:
                    for btn in target_btns:
                        if not art_active: break
                        try:
                            await btn.click()
                            print(f"🔍 کلیک روی آرت: {btn.text}")
                            await asyncio.sleep(3) # صبر ۳ ثانیه برای لود پیام جزئیات
                            
                            # پیدا کردن پیام جزئیات (بعد از آخرین پیامی که فوروارد کردیم)
                            detail_found = False
                            async for detail in client.iter_messages(g_id, limit=30):
                                if detail.sender and detail.sender.bot:
                                    d_text = detail.text or ""
                                    if "🖼" in d_text and "قیمت" in d_text and detail.id > last_detail_id:
                                        try:
                                            await client.forward_messages('me', detail.id, g_id)
                                            last_detail_id = detail.id
                                            print("✅ آرت فوروارد شد.")
                                            detail_found = True
                                        except Exception as e:
                                            print(f"خطا فوروارد: {e}")
                                        break
                                if detail.id <= last_detail_id:
                                    break # رسیدیم به پیام‌های قدیمی
                            
                            if not detail_found:
                                print("⚠️ پیام جزئیات تو ۳۰ پیام اخیر پیدا نشد.")
                        except Exception as e:
                            print(f"خطا در کلیک دکمه: {e}")
                
                # ۶. رفتن به صفحه بعد
                if next_btn and art_active:
                    print("➡️ رفتن به صفحه بعد...")
                    try:
                        await next_btn.click()
                        await asyncio.sleep(7) # صبر ۷ ثانیه برای لود شدن صفحه جدید
                        # لیست تو همون پیام آپدیت میشه، پس تو دور بعدی حلقه، همون آیدی رو دوباره می‌خونیم
                    except:
                        pass
                else:
                    await log_to_chat(g_id, "ℹ️ به انتهای مارکت رسیدیم یا دکمه بعدی پیدا نشد. ۶۰ ثانیه دیگه از اول شروع میکنم.")
                    break
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            await log_to_chat(g_id, f"❌ گیر کردم: یه خطای کلی پیش اومده: {e}")
            await asyncio.sleep(10)
            
        if art_active:
            await asyncio.sleep(60)
