import asyncio
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
            
            print("⏳ تولید استارت خورد. سیستم ۱۳ ساعت و ۱۵ دقیقه صبر می‌کنه...")
            waited = 0
            while waited < 47700 and core.factory_active:
                await asyncio.sleep(60)
                waited += 60
            
            if not core.factory_active:
                break
            
            # --- فاز فروش (کاملاً اصلاح شده) ---
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
        await event.reply("🏭 سیستم کارخونه میویی **روشن** شد.")
        asyncio.create_task(factory_cycle())
    else:
        await event.reply("❗ کارخونه از قبل روشنه.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^کارخونه میویی خاموش$'))
async def factory_off(event):
    core.factory_active = False
    await event.reply("🛑 سیستم کارخونه میویی **خاموش** شد.")
