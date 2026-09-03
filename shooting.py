import asyncio
from telethon import events
import core
from core import client

PIOU_GROUP = -1004346927517
PIOU_TARGET = "cbjyz"
piou_active = False

# --- لوپ ارسال گوشت (هر ۳۰ دقیقه) ---
async def meat_loop():
    while True:
        if piou_active:
            try:
                await client.send_message(PIOU_GROUP, "🥩")
            except Exception as e:
                print(f"خطا گوشت: {e}")
        await asyncio.sleep(1800)

# --- لوپ شلیک کور (هر ۵ دقیقه) ---
async def blind_shot_loop():
    while True:
        if piou_active:
            try:
                await client.send_message(PIOU_GROUP, "شلیک")
            except Exception as e:
                print(f"خطا شلیک کور: {e}")
        await asyncio.sleep(300)

# --- لوپ اصلی شلیک و پیو هیل ---
async def piou_main_loop():
    while True:
        if piou_active:
            try:
                # پیدا کردن آخرین پیام یارو
                target_msg = None
                async for msg in client.iter_messages(PIOU_GROUP, limit=50):
                    if msg.sender and getattr(msg.sender, 'username', None) == PIOU_TARGET:
                        target_msg = msg
                        break
                
                if not target_msg:
                    print("⚠️ پیام کاربر @cbjyz تو گروه پیدا نشد.")
                    await asyncio.sleep(10)
                    continue

                cycle_count = 0
                while piou_active:
                    cycle_count += 1
                    
                    # ۱. شلیک (ریپلای روی پیام یارو)
                    shalak_msg = await client.send_message(PIOU_GROUP, "شلیک", reply_to=target_msg.id)
                    await asyncio.sleep(2)
                    
                    # ۲. پیو هیل (ریپلای روی پیام شلیک خودمون)
                    await client.send_message(PIOU_GROUP, "پیو هیل", reply_to=shalak_msg.id)
                    
                    # ۳. خرید مهمات (هر ۹ بار)
                    if cycle_count % 9 == 0:
                        await client.send_message(PIOU_GROUP, "خرید مهمات", reply_to=target_msg.id)
                    
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
    global piou_active
    piou_active = True
    await event.reply("🔫 سیستم پیو **روشن** شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^پیو خاموش$'))
async def piou_off(event):
    global piou_active
    piou_active = False
    await event.reply("🛑 سیستم پیو **خاموش** شد.")
