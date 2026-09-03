import asyncio
import re
from telethon import events
import core
from core import client
import shooting

PIOU_GROUP = -1004346927517
TARGET_MSG_ID = 18
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
    if not smart_active or event.chat_id != PIOU_GROUP: return
    
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
        shooting.piou_active = False
        print("🛑 ربات shooting.py خاموش شد.")
        
        await client.send_message(PIOU_GROUP, "حالت مرده فعال شد")
        my_msg = await client.send_message(PIOU_GROUP, "پیو من")
        
        bandages = 0
        for _ in range(5):
            await asyncio.sleep(2)
            msgs = await client.get_messages(PIOU_GROUP, reply_to=my_msg.id, limit=1)
            if msgs and msgs[0].sender and msgs[0].sender.bot:
                panel_text = msgs[0].text or ""
                b_match = re.search(r'جعبه‌های کمک اولیه:\s*(\d+)\s*/\s*\d+', panel_text)
                if b_match:
                    bandages = int(b_match.group(1))
                    break
        
        await client.send_message(PIOU_GROUP, f"تعداد بانداژ ها محاسبه شد ({bandages} تا)")
        
        print(f"⏳ صبر میکنیم تا یارو زنده بشه: {death_seconds + 2} ثانیه")
        await asyncio.sleep(death_seconds + 2)
        
        for _ in range(bandages):
            if not smart_active: return
            await client.send_message(PIOU_GROUP, "شلیک", reply_to=TARGET_MSG_ID)
            await asyncio.sleep(2)
            await client.send_message(PIOU_GROUP, "پیو هیل", reply_to=TARGET_MSG_ID)
            await asyncio.sleep(16)
            
    except asyncio.CancelledError:
        print("🔄 چرخه مرگ لغو شد!")
        return

async def refill_cycle_task():
    try:
        await client.send_message(PIOU_GROUP, "حالت جعبه های کمک اولیه فعال شد")
        
        print(f"⏳ صبر میکنیم تا بانداژها پر شوند: {refill_seconds} ثانیه")
        await asyncio.sleep(refill_seconds + 2)
        
        if not smart_active: return
        
        # چرخه بی‌نهایت: ۱۰ شلیک + ۶ دقیقه استراحت
        while smart_active:
            print("🔫 شلیک ۱۰ تایی...")
            for _ in range(10):
                if not smart_active: return
                await client.send_message(PIOU_GROUP, "شلیک", reply_to=TARGET_MSG_ID)
                await asyncio.sleep(2)
                await client.send_message(PIOU_GROUP, "پیو هیل", reply_to=TARGET_MSG_ID)
                await asyncio.sleep(16)
            
            if not smart_active: return
            
            print("⏳ ۶ دقیقه استراحت (چرخه بانداژ)...")
            await asyncio.sleep(360)
            
    except asyncio.CancelledError:
        print("🔄 چرخه پر شدن بانداژ لغو شد!")
        return
