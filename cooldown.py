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
        # شرط: حتما باید روی پیام ما ریپلای کرده باشه
        if event.message.is_reply:
            try:
                replied_msg = await event.message.get_reply_message()
                me = await client.get_me()
                # مطمئن میشیم پیام شلیک مال خودمونه
                if replied_msg and replied_msg.sender_id == me.id and (replied_msg.text or "").strip() == "شلیک":
                    match = re.search(r'(\d+)\s*ثانی', text)
                    if match:
                        secs = int(match.group(1))
                        new_time = time.time() + secs + 1  # ۱ ثانیه امنیت
                        # اگه زمان جدید بیشتر از زمان فعلیه، آپدیت میکنه
                        if new_time > core.pio_cooldown_until:
                            core.pio_cooldown_until = new_time
                            try:
                                await client.send_message(event.chat_id, f"⏳ {secs} ثانیه دیگه شلیک میکنم.")
                            except: pass
            except: pass
