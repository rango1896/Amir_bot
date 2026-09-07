import asyncio
from telethon import events
import core
from core import client

art_active = False
art_name = ""
art_task = None

async def click_btn(g_id, text, timeout=10):
    """صبر می‌کنه تا دکمه با متن مشخص شده بیاد و روش کلیک می‌کنه"""
    for _ in range(timeout):
        if not art_active: return False
        await asyncio.sleep(1)
        async for msg in client.iter_messages(g_id, limit=5):
            if msg.buttons and msg.sender and msg.sender.bot:
                for row in msg.buttons:
                    for btn in row:
                        if text in btn.text:
                            try:
                                await btn.click()
                                return True
                            except:
                                pass
    return False

async def get_current_panel(g_id):
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
        clicked_texts = set() # ذخیره اسم دکمه‌هایی که کلیک کردیم
            
        try:
            # ۱. ارسال پیو آرت
            await client.send_message(g_id, "پیو آرت")
            print("📤 پیو آرت فرستاده شد...")
            await asyncio.sleep(4)
            
            # ۲. کلیک روی مارکت آرت
            if not await click_btn(g_id, "مارکت آرت", timeout=15):
                print("⚠️ مارکت آرت پیدا نشد. ۶۰ ثانیه دیگه تلاش میشه.")
                await asyncio.sleep(60)
                continue
                
            await asyncio.sleep(4)
            
            # ۳. چرخه صفحه‌بندی
            while art_active:
                panel = await get_current_panel(g_id)
                if not panel:
                    print("⚠️ هیچ پنلی پیدا نشد. استارت مجدد...")
                    break
                
                # اگه هنوز تو صفحه جزئیات یک آرت هستیم (توش قیمت یا 🖼 هست)
                # باید دکمه بازگشت رو بزنیم تا برگردیم به لیست
                if "🖼" in (panel.text or "") or "قیمت" in (panel.text or ""):
                    print("⏳ هنوز تو صفحه آرت هستیم، کلیک روی بازگشت...")
                    await click_btn(g_id, "بازگشت", timeout=5)
                    await asyncio.sleep(3)
                    continue # برمی‌گردیم اول حلقه تا لیست رو دوباره بخونیم
                
                # الان تو صفحه لیست مارکت هستیم
                target_btn = None
                next_btn = None
                
                for row in panel.buttons:
                    for btn in row:
                        txt = btn.text
                        if art_name in txt and "مارکت" not in txt and "بعد" not in txt and "بازگشت" not in txt:
                            if txt not in clicked_texts:
                                target_btn = btn
                        elif "بعد" in txt or "next" in txt.lower() or "›" in txt or "⏭" in txt or "برو" in txt or "➡️" in txt:
                            next_btn = btn
                            
                # ۴. اگه آرت پیدا شد، روش کلیک کن
                if target_btn:
                    try:
                        clicked_texts.add(target_btn.text)
                        await target_btn.click()
                        print(f"🔍 کلیک روی آرت: {target_btn.text}")
                        await asyncio.sleep(4) # صبر برای لود شدن صفحه جزئیات آرت
                        
                        # صفحه جزئیات رو پیدا می‌کنیم
                        detail = await get_current_panel(g_id)
                        if detail and ("🖼" in (detail.text or "") or "قیمت" in (detail.text or "")):
                            try:
                                await client.forward_messages('me', detail.id, g_id)
                                print("✅ آرت فوروارد شد.")
                            except Exception as e:
                                print(f"خطا در فوروارد: {e}")
                            # کلیک روی بازگشت
                            await click_btn(g_id, "بازگشت", timeout=10)
                            await asyncio.sleep(3)
                        else:
                            # اگه صفحه جزئیات لود نشد، شاید ربات کرده، یه کم صبر کن
                            await asyncio.sleep(2)
                            
                    except Exception as e:
                        print(f"خطا در کلیک دکمه: {e}")
                    continue # میره سراغ بررسی دوباره (اول چک میکنه اگه تو صفحه آرت هست برش گردونه، بعدش میره سراغ بقیه)
                
                # ۵. اگه آرتی تو این صفحه پیدا نشد، بره صفحه بعد
                if next_btn and art_active:
                    print("➡️ رفتن به صفحه بعد...")
                    try:
                        await next_btn.click()
                    except:
                        pass
                    await asyncio.sleep(4) # صبر برای لود شدن صفحه جدید
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
