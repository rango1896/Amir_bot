import asyncio
import re
from telethon import events
import core
from core import client
import shooting # ایمپورت فایل قبلی برای خاموش کردنش

PIOU_GROUP = -1004346927517
TARGET_MSG_ID = 18
smart_active = False
is_processing = False

@client.on(events.NewMessage(outgoing=True, pattern=r'^هوشمند روشن$'))
async def smart_on(event):
    global smart_active
    smart_active = True
    await event.reply("🧠 سیستم شلیک هوشمند **روشن** شد.\nربات منتظر میشه تا یارو بمیره!")

@client.on(events.NewMessage(outgoing=True, pattern=r'^هوشمند خاموش$'))
async def smart_off(event):
    global smart_active, is_processing
    smart_active = False
    is_processing = False
    await event.reply("🛑 سیستم شلیک هوشمند **خاموش** شد.")

@client.on(events.NewMessage(incoming=True))
async def death_listener(event):
    global is_processing
    if not smart_active or is_processing: return
    if event.chat_id != PIOU_GROUP: return
    
    text = event.message.text or ""
    
    # ۱. تشخیص پیام مرگ
    if "مرده" in text and "زنده" in text and "تا" in text:
        # محاسبه زمان (دقیقه یا ثانیه)
        seconds = 0
        match_min = re.search(r'تا\s+(\d+)\s*دقیق', text)
        match_sec = re.search(r'تا\s+(\d+)\s*ثانی', text)
        
        if match_min:
            seconds = int(match_min.group(1)) * 60
        elif match_sec:
            seconds = int(match_sec.group(1))
            
        if seconds > 0:
            is_processing = True
            
            # ۲. خاموش کردن ربات shooting.py (بدون دست زدن به کدش)
            shooting.piou_active = False
            print("🛑 ربات shooting.py خاموش شد.")
            
            # ۳. اعلام حالت مرده
            await client.send_message(PIOU_GROUP, "حالت مرده فعال شد")
            
            # ۴. ارسال پیو من برای گرفتن پنل
            my_msg = await client.send_message(PIOU_GROUP, "پیو من")
            
            # ۵. گرفتن پنل آمار و خوندن بانداژها
            bandages = 0
            for _ in range(5): # ۵ بار چک میکنه تا پنل بیاد
                await asyncio.sleep(2)
                msgs = await client.get_messages(PIOU_GROUP, reply_to=my_msg.id, limit=1)
                if msgs and msgs[0].sender and msgs[0].sender.bot:
                    panel_text = msgs[0].text or ""
                    b_match = re.search(r'جعبه‌های کمک اولیه:\s*(\d+)\s*/\s*\d+', panel_text)
                    if b_match:
                        bandages = int(b_match.group(1))
                        break
            
            # ۶. اعلام محاسبه بانداژ
            await client.send_message(PIOU_GROUP, f"تعداد بانداژ ها محاسبه شد ({bandages} تا)")
            
            # ۷. صبر کردن تا یارو زنده بشه
            print(f"⏳ صبر میکنیم تا یارو زنده بشه: {seconds + 2} ثانیه")
            await asyncio.sleep(seconds + 2)
            
            # ۸. چرخه شلیک و پیو هیل
            for i in range(bandages):
                if not smart_active: break
                
                await client.send_message(PIOU_GROUP, "شلیک", reply_to=TARGET_MSG_ID)
                await asyncio.sleep(2)
                await client.send_message(PIOU_GROUP, "پیو هیل", reply_to=TARGET_MSG_ID)
                
                # ۹. استراحت ۱۶ ثانیه‌ای بین شلیک‌ها
                for _ in range(16):
                    if not smart_active: break
                    await asyncio.sleep(1)
            
            # ۱۰. استراحت ۶ دقیقه‌ای
            if smart_active:
                print("⏳ ۶ دقیقه استراحت...")
                for _ in range(360):
                    if not smart_active: break
                    await asyncio.sleep(1)
            
            is_processing = False
            print("✅ چرخه هوشمند تموم شد. منتظر پیام مرگ بعدی...")
