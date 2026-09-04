import asyncio
import re
from telethon import events
import core
from core import client
import shooting

smart_active = False
refill_active = True
current_task = None
death_seconds = 0
refill_seconds = 0

@client.on(events.NewMessage(outgoing=True, pattern=r'^هوشمند روشن$'))
async def smart_on(event):
    global smart_active, current_task
    if not smart_active:
        smart_active = True
        await event.reply("🧠 سیستم شلیک هوشمند **روشن** شد. منتظر پیام‌های بازی...")
        if current_task is None or current_task.done():
            current_task = asyncio.create_task(wait_for_events())

@client.on(events.NewMessage(outgoing=True, pattern=r'^هوشمند خاموش$'))
async def smart_off(event):
    global smart_active, current_task
    smart_active = False
    if current_task and not current_task.done():
        current_task.cancel()
    shooting.piou_shoot_active = True
    await event.reply("🛑 سیستم شلیک هوشمند **خاموش** شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^بانداژ روشن$'))
async def refill_on(event):
    global refill_active
    refill_active = True
    await event.reply("🩹 سیستم بانداژ **روشن** شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^بانداژ خاموش$'))
async def refill_off(event):
    global refill_active
    refill_active = False
    await event.reply("🛑 سیستم بانداژ **خاموش** شد.")

@client.on(events.NewMessage(incoming=True))
async def game_listener(event):
    global smart_active, death_seconds, refill_seconds, current_task, refill_active
    if not smart_active or event.chat_id != shooting.active_shoot_group: return
    
    text = event.message.text or ""
    
    # ۱. تشخیص پیام مرگ
    if "مرده" in text and "زنده" in text and "تا" in text:
        seconds = 0
        match_min = re.search(r'تا\s+(\d+)\s*دقیق', text)
        match_sec = re.search(r'تا\s+(\d+)\s*ثانی', text)
        if match_min: seconds = int(match_min.group(1)) * 60
        elif match_sec: seconds = int(match_sec.group(1))
        
        if seconds > 0:
            death_seconds = seconds
            if current_task and not current_task.done():
                current_task.cancel()
            current_task = asyncio.create_task(death_cycle_task())

    # ۲. تشخیص پیام تموم شدن بانداژها
    elif refill_active and "جعبه‌های کمک اولیه‌ات تموم شده" in text and "تا" in text:
        seconds = 0
        match_min = re.search(r'تا\s+(\d+)\s*دقیق', text)
        match_sec = re.search(r'تا\s+(\d+)\s*ثانی', text)
        if match_min: seconds = int(match_min.group(1)) * 60
        elif match_sec: seconds = int(match_sec.group(1))
        
        if seconds > 0:
            refill_seconds = seconds
            if current_task and not current_task.done():
                current_task.cancel()
            current_task = asyncio.create_task(refill_cycle_task())

async def wait_for_events():
    pass

async def death_cycle_task():
    try:
        shooting.piou_shoot_active = False
        g_id = shooting.active_shoot_group
        m_id = shooting.target_links.get(g_id, 18)
        
        await client.send_message(g_id, "حالت مرده فعال شد")
        my_msg = await client.send_message(g_id, "پیو من")
        
        bandages = 0
        for _ in range(5):
            await asyncio.sleep(2)
            msgs = await client.get_messages(g_id, reply_to=my_msg.id, limit=1)
            if msgs and msgs[0].sender and msgs[0].sender.bot:
                panel_text = msgs[0].text or ""
                b_match = re.search(r'جعبه‌های کمک اولیه:\s*(\d+)\s*/\s*\d+', panel_text)
                if b_match:
                    bandages = int(b_match.group(1))
                    break
        
        await client.send_message(g_id, f"تعداد بانداژ ها محاسبه شد ({bandages} تا)")
        await asyncio.sleep(death_seconds + 2)
        
        for _ in range(bandages):
            if not smart_active: 
                shooting.piou_shoot_active = True
                return
            await client.send_message(g_id, "شلیک", reply_to=m_id)
            shooting.ammo_counter += 1
            await asyncio.sleep(2)
            await client.send_message(g_id, "پیو هیل", reply_to=m_id)
            
            # خرید مهمات (بر اساس تنظیم تیر در shooting.py)
            if shooting.ammo_counter % shooting.ammo_limit == 0:
                await client.send_message(g_id, "خرید مهمات", reply_to=m_id)
            
            await asyncio.sleep(20)
        
        shooting.piou_shoot_active = True
            
    except asyncio.CancelledError:
        return

async def refill_cycle_task():
    try:
        shooting.piou_shoot_active = False
        g_id = shooting.active_shoot_group
        m_id = shooting.target_links.get(g_id, 18)
        
        await client.send_message(g_id, "حالت جعبه های کمک اولیه فعال شد")
        await asyncio.sleep(refill_seconds + 2)
        
        if not smart_active:
            shooting.piou_shoot_active = True
            return
        
        while smart_active:
            for _ in range(10):
                if not smart_active: 
                    shooting.piou_shoot_active = True
                    return
                await client.send_message(g_id, "شلیک", reply_to=m_id)
                shooting.ammo_counter += 1
                await asyncio.sleep(2)
                await client.send_message(g_id, "پیو هیل", reply_to=m_id)
                
                # خرید مهمات (بر اساس تنظیم تیر در shooting.py)
                if shooting.ammo_counter % shooting.ammo_limit == 0:
                    await client.send_message(g_id, "خرید مهمات", reply_to=m_id)
                
                await asyncio.sleep(20)
            
            if not smart_active:
                shooting.piou_shoot_active = True
                return
            
            await asyncio.sleep(360)
            
    except asyncio.CancelledError:
        return
