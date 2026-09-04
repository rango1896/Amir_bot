import asyncio
from telethon import events
import core
from core import client

PIOU_GROUP = -1004346927517
ammo_active = False
shot_counter = 0

# دیکشنری برای اعداد ترتیبی فارسی
persian_ordinals = {
    1: "اول", 2: "دوم", 3: "سوم", 4: "چهارم", 5: "پنجم", 6: "ششم",
    7: "هفتم", 8: "هشتم", 9: "نهم", 10: "دهم", 11: "یازدهم",
    12: "دوازدهم", 13: "سیزدهم", 14: "چهاردهم"
}

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
    reply_to_id = event.message.reply_to_msg_id
    
    # اگه کلمه شلیک توش بود و ریپلای کرده بودی (رو پیام 18 یا هر پیام دیگه)
    if "شلیک" in text and "فرستاده شد" not in text and reply_to_id is not None:
        shot_counter += 1
        print(f"🔫 شلیک شماره: {shot_counter}")
        
        # پیام دیباگ رو بدون صبر کردن میفرسته (اینجوری گیر نمیکنه)
        ordinal = persian_ordinals.get(shot_counter, str(shot_counter))
        asyncio.create_task(event.reply(f"شلیک {ordinal} فرستاده شد"))
        
        # هر ۱۴ بار
        if shot_counter >= 14:
            # رو همون پیامی که روش ریپلای کردی (پیام 18) میگه خرید مهمات
            asyncio.create_task(client.send_message(PIOU_GROUP, "خرید مهمات", reply_to=reply_to_id))
            print("🛒 خرید مهمات انجام شد!")
            shot_counter = 0 # صفر میکنه تا دوباره شمارش کنه
