import asyncio
from datetime import datetime
from telethon import events
from telethon.tl.functions.account import UpdateProfileRequest
import core
from core import client, to_double_struck, strip_clock, TEHRAN_TZ

stray_lock = asyncio.Lock()

async def update_name_clock():
    while True:
        try:
            me = await client.get_me()
            base_name = strip_clock(me.first_name or "")
            now = datetime.now(TEHRAN_TZ).strftime("%H:%M")
            clock_str = to_double_struck(now)
            new_name = f"{base_name} {clock_str}" if base_name else clock_str
            await client(UpdateProfileRequest(first_name=new_name))
            print(f"🕒 اسم به‌روز شد: {new_name}")
        except Exception as e:
            print(f"❌ خطا: {e}")
        await asyncio.sleep(60)

async def meow_loop():
    while True:
        try:
            await client.send_message(core.group_entity, "میو")
            print("🐱 میو فرستاده شد")
        except Exception as e:
            print(f"❌ خطا: {e}")
        await asyncio.sleep(300)

async def rescue_stray_cat(msg):
    async with stray_lock:
        for i in range(3):
            try:
                current_msg = await client.get_messages(core.group_entity, ids=msg.id)
                if not current_msg or not current_msg.buttons: break
                for row in current_msg.buttons:
                    for btn in row:
                        if "نجات پیشی خیابونی" in btn.text:
                            await current_msg.click(text=btn.text)
                            break
                    else: continue
                    break
                if i < 2: await asyncio.sleep(2)
            except Exception as e:
                print(f"❌ خطا گربه: {e}")
                break

@client.on(events.NewMessage(incoming=True))
async def stray_cat_handler(event):
    if not core.stray_cat_active: return
    if not event.is_group or event.chat_id != core.TARGET_GROUP: return
    if event.message.buttons:
        for row in event.message.buttons:
            for btn in row:
                if "نجات پیشی خیابونی" in btn.text:
                    await rescue_stray_cat(event.message)
                    return
