import asyncio
from telethon import events
import core
from core import client

PIOU_GROUP = -1004346927517
ammo_active = False
shot_counter = 0

@client.on(events.NewMessage(outgoing=True, pattern=r'^مهمات روشن$'))
async def ammo_on(event):
    global ammo_active, shot_counter
    ammo_active = True
    shot_counter = 0
    await event.reply("🛒 سیستم خرید مهمات **روشن** شد. شمارش شلیک‌های ریپلای‌دار شروع شد.")

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
    
    # اگه پیام شلیک بود و ریپلای کرده بودی (رو پیام ۱۸ یا هر پیام دیگه)
    if text == "شلیک" and event.message.is_reply:
        shot_counter += 1
        print(f"🔫 شلیک شماره: {shot_counter}")
        
        # هر ۱۴ بار
        if shot_counter >= 14:
            # رو همون پیامی که روش ریپلای کردی (پیام ۱۸) میگه خرید مهمات
            await client.send_message(PIOU_GROUP, "خرید مهمات", reply_to=event.message.reply_to_msg_id)
            print("🛒 خرید مهمات انجام شد!")
            shot_counter = 0 # صفر میکنه تا دوباره شمارش کنه
