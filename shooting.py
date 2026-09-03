import asyncio
import time
from telethon import events
import core
from core import client

PIOU_GROUP = -1004346927517
TARGET_MSG_ID = 18  # آیدی پیامی که قراره روش ریپلای بشه (از لینک شما استخراج شد)
piou_active = False
last_meat_time = 0

# --- لوپ ارسال گوشت (درجا + هر ۳۰ دقیقه) ---
async def meat_loop():
    global last_meat_time
    while True:
        if piou_active and (time.time() - last_meat_time >= 1800):
            try:
                await client.send_message(PIOU_GROUP, "🥩")
                last_meat_time = time.time()
            except Exception as e:
                print(f"خطا گوشت: {e}")
        await asyncio.sleep(5)

# --- لوپ شلیک کور (درجا + هر ۵ دقیقه) ---
async def blind_shot_loop():
    while True:
        if piou_active:
            try:
                # ۱. درجا شلیک بدون ریپلای میکنه
                await client.send_message(PIOU_GROUP, "شلیک")
            except Exception as e:
                print(f"خطا شلیک کور: {e}")
            
            # ۲. بعدش ۵ دقیقه صبر میکنه (اگه وسطش خاموش کردی از حلقه میاد بیرون)
            for _ in range(300):
                if not piou_active: break
                await asyncio.sleep(1)
        else:
            await asyncio.sleep(5)

# --- لوپ اصلی شلیک و پیو هیل (با ریپلای) ---
async def piou_main_loop():
    while True:
        if piou_active:
            try:
                cycle_count = 0
                while piou_active:
                    cycle_count += 1
                    
                    # ۱. شلیک (ریپلای مستقیم روی پیام شماره ۱۸)
                    shalak_msg = await client.send_message(PIOU_GROUP, "شلیک", reply_to=TARGET_MSG_ID)
                    await asyncio.sleep(2)
                    
                    # ۲. پیو هیل (ریپلای مستقیم روی پیام شماره ۱۸)
                    await client.send_message(PIOU_GROUP, "پیو هیل", reply_to=TARGET_MSG_ID)
                    
                    # ۳. خرید مهمات (هر ۹ بار شلیک با ریپلای)
                    if cycle_count % 9 == 0:
                        await client.send_message(PIOU_GROUP, "خرید مهمات", reply_to=TARGET_MSG_ID)
                    
                    # ۴. استراحت ۴.۵ دقیقه (هر ۱۰ بار)
                    if cycle_count % 10 == 0:
                        print("⏳ ۴ دقیقه و ۳۰ ثانیه استراحت...")
                        for _ in range(270):
                            if not piou_active: break
                            await asyncio.sleep(1)
                        if not piou_active: break
                    else:
                        # فاصله ۱۵ ثانیه‌ای بین شلیک‌ها
                        for _ in range(15):
                            if not piou_active: break
                            await asyncio.sleep(1)
                        if not piou_active: break

            except Exception as e:
                print(f"❌ خطا در سیستم پیو: {e}")
                await asyncio.sleep(10)
        else:
            await asyncio.sleep(5)

@client.on(events.NewMessage(outgoing=True, pattern=r'^پیو روشن$'))
async def piou_on(event):
    global piou_active, last_meat_time
    if not piou_active:
        piou_active = True
        last_meat_time = 0  # این خط باعث میشه ربات درجا گوشت رو بفرسته
        await event.reply("🔫 سیستم پیو **روشن** شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^پیو خاموش$'))
async def piou_off(event):
    global piou_active
    piou_active = False
    await event.reply("🛑 سیستم پیو **خاموش** شد.")
