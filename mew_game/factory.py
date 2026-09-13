import asyncio
import re
from telethon import events
import core
from core import client

async def click_factory_button(msg_id, target_text, timeout=30):
    for _ in range(timeout):
        await asyncio.sleep(1)
        msg = await client.get_messages(core.group_entity, ids=msg_id)
        if msg and msg.buttons:
            for row in msg.buttons:
                for btn in row:
                    if target_text in btn.text:
                        await msg.click(text=btn.text)
                        return True
    return False

async def click_factory_coords(msg_id, row_idx, col_idx, timeout=30):
    for _ in range(timeout):
        await asyncio.sleep(1)
        msg = await client.get_messages(core.group_entity, ids=msg_id)
        if msg and msg.buttons:
            try:
                await msg.click(row_idx, col_idx)
                return True
            except: pass
    return False

async def factory_cycle():
    while core.factory_active:
        try:
            # --- فاز تولید ---
            print("🏭 شروع چرخه کارخونه (فاز تولید)...")
            await client.send_message(core.group_entity, "کارخونه میویی")
            await asyncio.sleep(3)
            
            panel_msg = None
            async for m in client.iter_messages(core.group_entity, limit=5):
                if m.buttons:
                    panel_msg = m
                    break
            
            if not panel_msg:
                print("⚠️ پنل کارخونه پیدا نشد. تلاش مجدد در ۱۰ ثانیه...")
                await asyncio.sleep(10)
                continue
            
            panel_id = panel_msg.id
            
            if not await click_factory_button(panel_id, "تولید"): continue
            await asyncio.sleep(2)
            if not await click_factory_button(panel_id, "تولیدی هواپیما"): continue
            await asyncio.sleep(2)
            if not await click_factory_coords(panel_id, 0, 2): continue
            await asyncio.sleep(2)
            if not await click_factory_coords(panel_id, 0, 3): continue
            await asyncio.sleep(2)
            if not await click_factory_button(panel_id, "شروع تولید"): continue
            
            # --- بخش جدید: استخراج زمان از متن ربات ---
            print("⏳ تولید استارت خورد. در حال استخراج زمان باقی‌مانده...")
            await asyncio.sleep(2) # یه کم صبر می‌کنیم تا ربات بازی پنل رو آپدیت کنه
            
            await client.send_message(core.group_entity, "کارخونه میویی")
            await asyncio.sleep(3)
            
            panel_msg_2 = None
            async for m in client.iter_messages(core.group_entity, limit=5):
                if m.buttons:
                    panel_msg_2 = m
                    break
            
            if not panel_msg_2:
                print("⚠️ پنل پیدا نشد تا زمان رو بخونیم. ۱۰ دقیقه استراحت و تلاش مجدد...")
                await asyncio.sleep(600)
                continue
                
            p_id_2 = panel_msg_2.id
            
            # کلیک مجدد روی دکمه تولید برای ظاهر شدن پیام "در حال تولید هستید"
            if not await click_factory_button(p_id_2, "تولید"):
                print("⚠️ دکمه تولید برای خوندن زمان پیدا نشد.")
                await asyncio.sleep(10)
                continue
                
            await asyncio.sleep(3) # صبر تا ربات پیام زمان رو بفرسته
            
            # پیدا کردن پیامی که توش زمان باقی‌مانده نوشته شده
            target_msg = None
            async for m in client.iter_messages(core.group_entity, limit=5):
                if m.text and "زمان باقی مانده" in m.text:
                    target_msg = m
                    break
            
            if not target_msg:
                print("⚠️ متن زمان باقی‌مانده تو پیام‌ها پیدا نشد!")
                await asyncio.sleep(10)
                continue
                
            text = target_msg.text
            # جستجوی زمان با ریجکس (مثلا 10:50:41)
            match = re.search(r'زمان باقی مانده\s*:\s*([0-9:]+)', text)
            
            if not match:
                print("⚠️ فرمت زمان پیدا نشد.")
                await asyncio.sleep(10)
                continue
                
            time_str = match.group(1)
            parts = time_str.split(':')
            
            # تبدیل زمان به ثانیه
            if len(parts) == 3: # فرمت HH:MM:SS
                h, m, s = map(int, parts)
                total_seconds = h * 3600 + m * 60 + s
            elif len(parts) == 2: # فرمت MM:SS
                m, s = map(int, parts)
                total_seconds = m * 60 + s
            else:
                total_seconds = 0
                
            if total_seconds <= 0:
                print("⚠️ زمان صفر یا نامعتبر است.")
                await asyncio.sleep(10)
                continue
                
            # ۳۰ ثانیه اضافه برای اطمینان از کامل شدن تولید
            total_seconds += 30
            
            # ارسال پیام اطلاع‌رسانی به شما
            h_fmt = total_seconds // 3600
            m_fmt = (total_seconds % 3600) // 60
            notify_text = f"✅ زمان باقی‌مانده استخراج شد: {time_str}\n🔄 ربات به مدت {h_fmt} ساعت و {m_fmt} دقیقه استراحت می‌کنه تا تولید تموم بشه."
            await client.send_message(core.group_entity, notify_text, reply_to=target_msg.id)
            print(notify_text)
            
            # استراحت به اندازه زمان استخراج شده
            waited = 0
            while waited < total_seconds and core.factory_active:
                await asyncio.sleep(60)
                waited += 60
            
            if not core.factory_active:
                break
            
            # --- فاز فروش (کد خودتون) ---
            print("💰 زمان فروش رسید. شروع فاز فروش...")
            sold_successfully = False
            
            for attempt in range(3): # ۳ بار تلاش میکنه تا بتونه بفروشه
                try:
                    await client.send_message(core.group_entity, "کارخونه میویی")
                    await asyncio.sleep(3)
                    
                    panel_msg = None
                    async for m in client.iter_messages(core.group_entity, limit=5):
                        if m.buttons:
                            panel_msg = m
                            break
                            
                    if not panel_msg:
                        print("⚠️ پنل فروش پیدا نشد. ۱۰ ثانیه دیگر تلاش می‌کنم...")
                        await asyncio.sleep(10)
                        continue
                        
                    p_id = panel_msg.id
                    
                    if not await click_factory_button(p_id, "انبار"): 
                        print("⚠️ دکمه انبار پیدا نشد.")
                        await asyncio.sleep(5)
                        continue

                    await asyncio.sleep(2)
                    
                    if not await click_factory_coords(p_id, 0, 0):
                        print("⚠️ دکمه موشک (فروش) پیدا نشد.")
                        await asyncio.sleep(5)
                        continue
                    await asyncio.sleep(2)
                    
                    if not await click_factory_button(p_id, "فروش محصول"):
                        print("⚠️ دکمه فروش محصول پیدا نشد.")
                        await asyncio.sleep(5)
                        continue
                        
                    print("✅ فروش با موفقیت انجام شد. چرخه از اول تکرار میشه...")
                    sold_successfully = True
                    break # اگه فروخت، از حلقه تلاش خارج میشه
                except Exception as e:
                    print(f"❌ خطا در تلاش {attempt+1} فروش: {e}")
                    await asyncio.sleep(5)
            
            if not sold_successfully:
                print("❌ فروش ناموفق بود. چرخه از فاز تولید مجدداً استارت می‌خوره.")
                
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"❌ خطای کلی در کارخونه: {e}")
            await asyncio.sleep(10)

@client.on(events.NewMessage(outgoing=True, pattern=r'^کارخونه میویی روشن$'))
async def factory_on(event):
    if not core.factory_active:
        core.factory_active = True
        await event.reply("🏭 سیستم کارخونه میویی روشن شد.")
        asyncio.create_task(factory_cycle())
    else:
        await event.reply("❗ کارخونه از قبل روشنه.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^کارخونه میویی خاموش$'))
async def factory_off(event):
    core.factory_active = False
    await event.reply("🛑 سیستم کارخونه میویی خاموش شد.")
