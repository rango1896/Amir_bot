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
            # --- باز کردن پنل کارخونه ---
            print("🏭 شروع چرخه کارخونه...")
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
            
            # --- بررسی اینکه آیا در حال تولید هستیم یا خیر ---
            # کلیک روی دکمه تولید برای دیدن وضعیت
            await click_factory_button(panel_id, "تولید")
            await asyncio.sleep(3)
            
            # جستجوی متن "زمان باقی مانده" در پیام‌های اخیر (چه پیام جدید چه ادیت شده)
            time_text = ""
            async for m in client.iter_messages(core.group_entity, limit=10):
                if m.text and "زمان باقی مانده" in m.text:
                    time_text = m.text
                    break
            
            # --- اگر در حال تولید نبود، استارت می‌زنیم ---
            if not time_text:
                print("⚙️ تولید استارت نخورده بود. در حال استارت زدن تولید...")
                if not await click_factory_button(panel_id, "تولیدی هواپیما"): continue
                await asyncio.sleep(2)
                if not await click_factory_coords(panel_id, 0, 2): continue
                await asyncio.sleep(2)
                if not await click_factory_coords(panel_id, 0, 3): continue
                await asyncio.sleep(2)
                if not await click_factory_button(panel_id, "شروع تولید"): continue
                await asyncio.sleep(3)
                
                # بعد از استارت، دوباره دکمه تولید رو می‌زنیم تا زمان رو بهمون نشون بده
                await click_factory_button(panel_id, "تولید")
                await asyncio.sleep(3)
                
                async for m in client.iter_messages(core.group_entity, limit=10):
                    if m.text and "زمان باقی مانده" in m.text:
                        time_text = m.text
                        break
            
            if not time_text:
                print("⚠️ هنوز نتونستیم زمان رو پیدا کنیم. ۱۰ ثانیه دیگه تلاش می‌کنیم...")
                await asyncio.sleep(10)
                continue
            
            # --- استخراج زمان ---
            match = re.search(r'زمان باقی مانده\s*:\s*([0-9:]+)', time_text)
            if not match:
                print("⚠️ فرمت زمان پیدا نشد.")
                await asyncio.sleep(10)
                continue
                
            time_str = match.group(1)
            parts = time_str.split(':')
            
            # تبدیل زمان به ثانیه (چه فرمت 10:50:41 باشه چه 50:41)
            if len(parts) == 3: 
                h, m, s = map(int, parts)
                total_seconds = h * 3600 + m * 60 + s
            elif len(parts) == 2: 
                m, s = map(int, parts)
                total_seconds = m * 60 + s
            else:
                total_seconds = 0
                
            if total_seconds <= 0:
                print("⚠️ زمان صفر یا نامعتبر است.")
                await asyncio.sleep(10)
                continue
            
            # ۵ ثانیه اضافه فقط برای اطمینان از اینکه تولید صددرصد تموم شده باشه
            total_seconds += 5
            
            # ارسال پیام اطلاع‌رسانی به شما
            h_fmt = total_seconds // 3600
            m_fmt = (total_seconds % 3600) // 60
            notify_text = f"✅ زمان باقی‌مانده استخراج شد: {time_str}\n🔄 ربات به مدت {h_fmt} ساعت و {m_fmt} دقیقه استراحت می‌کنه تا تولید تموم بشه."
            await client.send_message(core.group_entity, notify_text)
            print(notify_text)
            
            # --- استراحت ---
            waited = 0
            while waited < total_seconds and core.factory_active:
                await asyncio.sleep(60)
                waited += 60
            
            if not core.factory_active:
                break
            
            # --- فاز فروش ---
            print("💰 زمان فروش رسید. شروع فاز فروش...")
            sold_successfully = False
            
            for attempt in range(3): 
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
                    break 
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
