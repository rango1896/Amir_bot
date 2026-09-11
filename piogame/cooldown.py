import time
import re
from telethon import events
import core
from core import client

@client.on(events.NewMessage(incoming=True))
async def cooldown_listener(event):
    if not core.pio_active_group or event.chat_id != core.pio_active_group: return
    text = event.message.text or ""
    
    if "تازه شلیک کردی" in text and "ثانی" in text:
        match = re.search(r'(\d+)\s*ثانی', text)
        if match:
            secs = int(match.group(1))
            new_time = time.time() + secs + 1
            # اگه زمان جدید بیشتر از زمان فعلیه، آپدیت میکنه
            if new_time > core.next_shoot_time:
                core.next_shoot_time = new_time
                try:
                    await client.send_message(event.chat_id, f"⏳ {secs} ثانیه دیگه شلیک میکنم.")
                except: pass
