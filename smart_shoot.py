import asyncio
import re
from telethon import events
import core
from core import client
import shooting

PIOU_GROUP = -1004346927517
TARGET_MSG_ID = 18
smart_active = False
current_task = None
death_seconds = 0

@client.on(events.NewMessage(outgoing=True, pattern=r'^هوشمند روشن$'))
async def smart_on(event):
    global smart_active, current_task
    if not smart_active:
        smart_active = True
        await event.reply("🧠 سیستم شلیک هوشمند **روشن** شد. منتظر مرگ یارو...")
        if current_task is None or current_task.done():
            current_task = asyncio.create_task(smart_main_loop())

@client.on(events.NewMessage(outgoing=True, pattern=r'^هوشمند خاموش$'))
async def smart_off(event):
    global smart_active, current_task
    smart_active = False
    if current_task and not current_task.done():
        current_task.cancel()
    await event.reply("🛑 سیستم شلیک هوشمند **خاموش** شد.")

@client.on(events.NewMessage(incoming=True))
async def death_listener(event):
    global death_seconds, current_task
    if not smart_active: return
    if event.chat_id != PIOU_GROUP: return
    
    text = event.message.text or ""
    if "مرده" in text and "زنده" in text and "تا" in text:
        seconds = 0
        match_min = re.search(r'تا\s+(\d+)\s*دقیق', text)
        match_sec = re.search(r'تا\s+(\d+)\s*ثانی', text)
        
        if match_min:
            seconds = int(match_min.group(1)) * 60
        elif match_sec:
            seconds = int(match_sec.group(1))
            
        if seconds > 0:
            death_seconds = seconds
            # اگه ربات تو حال انجام کار بود، اول کارش رو لغو میکنه و از اول شروع میکنه
            if current_task and not current_task.done():
                current_task.cancel()
            current_task = asyncio.create_task(smart_main_loop())

async def smart_main_loop():
    try:
        # ۱. خاموش کردن ربات قبلی
        shooting.piou_active = False
        print("🛑 ربات shooting.py خاموش شد.")
        
        # ۲. اعلام حالت مرده
        await client.send_message(PIOU_GROUP, "حالت مرده فعال شد")
        
        # ۳. ارسال پیو من
        my_msg = await client.send_message(PIOU_GROUP, "پیو من")
        
        # ۴. گرفتن پنل و خوندن بانداژها
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
        
        # ۵. اعلام محاسبه بانداژ
        await client.send_message(PIOU_GROUP, f"تعداد بانداژ ها محاسبه شد ({bandages} تا)")
        
        # ۶. صبر تا زنده شدن
        print(f"⏳ صبر میکنیم تا یارو زنده بشه: {death_seconds + 2} ثانیه")
        await asyncio.sleep(death_seconds + 2)
        
        # ۷. چرخه شلیک به تعداد بانداژها
        for i in range(bandages):
            if not smart_active: return
            await client.send_message(PIOU_GROUP, "شلیک", reply_to=TARGET_MSG_ID)
            await asyncio.sleep(2)
            await client.send_message(PIOU_GROUP, "پیو هیل", reply_to=TARGET_MSG_ID)
            await asyncio.sleep(16)
        
        if not smart_active: return
        
        # ۸. استراحت ۶ دقیقه‌ای
        print("⏳ ۶ دقیقه استراحت...")
        await asyncio.sleep(360)
        
        if not smart_active: return
        
        # ۹. شلیک ۱۰ تایی بعد از استراحت
        print("🔫 شلیک ۱۰ تایی پس از استراحت...")
        for i in range(10):
            if not smart_active: return
            await client.send_message(PIOU_GROUP, "شلیک", reply_to=TARGET_MSG_ID)
            await asyncio.sleep(2)
            await client.send_message(PIOU_GROUP, "پیو هیل", reply_to=TARGET_MSG_ID)
            await asyncio.sleep(16)
            
    except asyncio.CancelledError:
        # اگه یارو یهو بمیره و ربات داشت کاری میکرد، این ارور میده تا کار رو رها کنه و بره از اول
        print("🔄 یارو دوباره مرد! چرخه فعلی لغو شد و از اول شروع میشه.")
        return
