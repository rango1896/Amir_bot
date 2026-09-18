import asyncio
import re
import random
from telethon import events
import core
from core import client

ring_task = None

@client.on(events.NewMessage(outgoing=True, pattern=r'^رینگ روشن$'))
async def ring_on(event):
    global ring_task
    if not core.ring_active_status:
        if not core.pio_active_group:
            return await event.reply("❗ اول با دستور `اد لینک` یه پیام هدف ثبت کن!")
        core.ring_active_status = True
        await core.save_db()
        await event.reply("🏋️ سیستم رینگ **روشن** شد.")
        if ring_task is None or ring_task.done():
            ring_task = asyncio.create_task(ring_loop(core.pio_active_group))

@client.on(events.NewMessage(outgoing=True, pattern=r'^رینگ خاموش$'))
async def ring_off(event):
    global ring_task
    core.ring_active_status = False
    await core.save_db()
    if ring_task and not ring_task.done():
        ring_task.cancel()
    await event.reply("🛑 سیستم رینگ **خاموش** شد.")

async def start_ring_if_active():
    """این تابع توسط main.py صدا زده میشه تا اگه رینگ قبلا روشن بوده، خودکار استارت بخوره"""
    global ring_task
    if core.ring_active_status and core.pio_active_group:
        if ring_task is None or ring_task.done():
            print("✅ رینگ از قبل روشن بوده، دوباره استارت میشه...")
            ring_task = asyncio.create_task(ring_loop(core.pio_active_group))

def parse_panel(text):
    clean_text = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2066-\u2069]', '', text)
    skills = {}
    matches = re.findall(r'(سرعت|مهارت|قدرت|سلامتی)\D*(\d+)', clean_text)
    for name, lvl in matches:
        skills[name] = int(lvl)
        
    time_match = re.search(r'(\d+)\D*ساعت\D*و\D*(\d+)\D*دقیقه', clean_text)
    if time_match:
        return skills, (int(time_match.group(1)) * 3600) + (int(time_match.group(2)) * 60)
        
    time_match_min = re.search(r'(\d+)\D*دقیقه', clean_text)
    if time_match_min:
        return skills, int(time_match_min.group(1)) * 60
        
    return skills, 3600

async def click_skill(panel_msg, skill_name):
    if not panel_msg.buttons: return None
    for row in panel_msg.buttons:
        for button in row:
            if skill_name in button.text:
                return await button.click()
    return None

async def ring_loop(chat_id):
    while core.ring_active_status:
        panel_msg = None
        try:
            sent_msg = await client.send_message(chat_id, "پیو رینگ")
            
            for _ in range(4):
                await asyncio.sleep(5)
                messages = await client.get_messages(chat_id, limit=10)
                for msg in messages:
                    if not msg.out and msg.text and "انرژی" in msg.text and "لول" in msg.text:
                        if msg.id > sent_msg.id or msg.reply_to_msg_id == sent_msg.id:
                            panel_msg = msg
                            break
                if panel_msg: break
                    
            if not panel_msg:
                await asyncio.sleep(random.randint(30, 60))
                continue
                
            await client.send_message(chat_id, "✅ پنل تشخیص داده شد! در حال پردازش...")
            
            while core.ring_active_status:
                text = panel_msg.text
                skills, sleep_secs = parse_panel(text)
                
                if not skills:
                    await client.send_message(chat_id, "❗ خطا: نتونستم لول‌ها رو از متن بخونم! پنل گم شد.")
                    break 
                    
                levels = list(skills.values())
                min_lvl = min(levels)
                max_lvl = max(levels)
                
                if min_lvl == max_lvl:
                    target_skill = random.choice(list(skills.keys()))
                    await client.send_message(chat_id, f"🤔 لول‌ها مساوی هستن. انتخاب رندوم: {target_skill}")
                else:
                    target_skill = [k for k, v in skills.items() if v == min_lvl][0]
                    await client.send_message(chat_id, f"🎯 کمترین لول: {target_skill} ({min_lvl}). در حال ارتقا...")
                    
                res = await click_skill(panel_msg, target_skill)
                if res is None:
                    await client.send_message(chat_id, f"❗ خطا: دکمه {target_skill} تو پنل پیدا نشد!")
                    break
                    
                await asyncio.sleep(2.5) 
                
                if res and hasattr(res, 'message') and res.message and "انرژی" in res.message:
                    hours = sleep_secs // 3600
                    mins = (sleep_secs % 3600) // 60
                    await client.send_message(chat_id, f"🔋 انرژی کافی نیست. {hours} ساعت و {mins} دقیقه صبر میکنم...")
                    try:
                        await asyncio.sleep(sleep_secs + 60) 
                    except asyncio.CancelledError:
                        return
                    break 
                
                try:
                    updated_msg = await client.get_messages(chat_id, ids=panel_msg.id)
                    if updated_msg and updated_msg.text and "انرژی" in updated_msg.text:
                        panel_msg = updated_msg
                    else:
                        break 
                except:
                    break 
                    
            if core.ring_active_status:
                await asyncio.sleep(random.randint(30, 60))
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"❌ خطا در حلقه رینگ: {e}")
            await asyncio.sleep(15)
