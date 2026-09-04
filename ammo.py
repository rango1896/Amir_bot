from telethon import events
import core
from core import client

PIOU_GROUP = -1004346927517
TARGET_MSG_ID = 18
ammo_active = False
shot_counter = 0

@client.on(events.NewMessage(outgoing=True, pattern=r'^مهمات روشن$'))
async def ammo_on(event):
    global ammo_active, shot_counter
    ammo_active = True
    shot_counter = 0
    await event.reply("🛒 سیستم خرید مهمات **روشن** شد. (هر ۱۴ شلیک، یک خرید)")

@client.on(events.NewMessage(outgoing=True, pattern=r'^مهمات خاموش$'))
async def ammo_off(event):
    global ammo_active
    ammo_active = False
    await event.reply("🛑 سیستم خرید مهمات **خاموش** شد.")

@client.on(events.NewMessage(outgoing=True))
async def ammo_tracker(event):
    global shot_counter, ammo_active
    if not ammo_active: return
    if event.chat_id != PIOU_GROUP: return
    
    text = (event.message.text or "").strip()
    # اگه پیام شلیک بود و ریپلای روی همون پیام هدف (شماره ۱۸) بود
    if text == "شلیک" and event.message.reply_to_msg_id == TARGET_MSG_ID:
        shot_counter += 1
        print(f"🔫 شلیک شماره: {shot_counter}")
        
        # هر ۱۴ بار
        if shot_counter >= 14:
            await client.send_message(PIOU_GROUP, "خرید مهمات", reply_to=TARGET_MSG_ID)
            print("🛒 خرید مهمات انجام شد!")
            shot_counter = 0 # صفر میکنه تا شمارش بعدی شروع بشه
