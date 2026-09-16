import asyncio
import re
import random
from telethon import events
import core
from core import client

ring_active = False
ring_task = None

@client.on(events.NewMessage(outgoing=True, pattern=r'^رینگ روشن$'))
async def ring_on(event):
    global ring_active, ring_task
    if not ring_active:
        if not core.pio_active_group:
            return await event.reply("❗ اول با دستور `اد لینک` یه پیام هدف ثبت کن!")
        ring_active = True
        await event.reply("🏋️ سیستم رینگ **روشن** شد.")
        if ring_task is None or ring_task.done():
            ring_task = asyncio.create_task(ring_loop(core.pio_active_group))

@client.on(events.NewMessage(outgoing=True, pattern=r'^رینگ خاموش$'))
async def ring_off(event):
    global ring_active, ring_task
    ring_active = False
    if ring_task and not ring_task.done():
        ring_task.cancel()
    await event.reply("🛑 سیستم رینگ **خاموش** شد.")

def parse_panel(text):
    """استخراج لول مهارت‌ها و زمان از متن پنل"""
    skills = {}
    # پیدا کردن لول هر مهارت
    matches = re.findall(r'•\s*(سرعت|مهارت|قدرت|سلامتی):\s*لول\s*(\d+)', text)
    for name, lvl in matches:
        skills[name] = int(lvl)
        
    # پیدا کردن زمان پر شدن انرژی
    time_match = re.search(r'(\d+)\s*ساعت\s*و\s*(\d+)\s*دقیقه', text)
    if time_match:
        hours = int(time_match.group(1))
        mins = int(time_match.group(2))
        return skills, (hours * 3600) + (mins * 60)
        
    # اگه فقط دقیقه نوشته بود
    time_match_min = re.search(r'(\d+)\s*دقیقه', text)
    if time_match_min:
        return skills, int(time_match_min.group(1)) * 60
        
    return skills, 3600 # پیش‌فرض ۱ ساعت اگه زمان رو نفهمید

async def click_skill(panel_msg, skill_name):
    """کلیک هوشمند روی دکمه مهارت مورد نظر"""
    if not panel_msg.buttons:
        return None
    for row in panel_msg.buttons:
        for button in row:
            if skill_name in button.text:
                return await button.click()
    return None

async def ring_loop(chat_id):
    """حلقه اصلی ربات رینگ"""
    while ring_active:
        try:
            # ۱. فرستادن پیو رینگ
            sent_msg = await client.send_message(chat_id, "پیو رینگ")
            await asyncio.sleep(5) # صبر ۵ ثانیه‌ای تا ربات بازی جواب بده
            
            # ۲. گرفتن ریپلای روی پیام خودمون
            replies = await client.get_messages(chat_id, reply_to=sent_msg.id, limit=1)
            
            if not replies or not replies[0].text or "رینگ" not in replies[0].text:
                # اگه ریپلای نبود یا پنل نبود، ۱۰ ثانیه صبر کن و دوباره بفرست
                await asyncio.sleep(10)
                continue
                
            panel_msg = replies[0] # پنل رو ریپلای شده گرفتیم
            text = panel_msg.text
            
            # ۳. تحلیل پنل
            skills, sleep_secs = parse_panel(text)
            if not skills:
                await asyncio.sleep(10)
                continue
                
            levels = list(skills.values())
            min_lvl = min(levels)
            max_lvl = max(levels)
            
            # ۴. تصمیم‌گیری برای ارتقا
            if min_lvl == max_lvl:
                # همه لول‌ها مساویند -> یه مهارت رندوم انتخاب میشه
                target_skill = random.choice(list(skills.keys()))
            else:
                # مساوی نیستن -> کمترین لول رو پیدا کن
                target_skill = [k for k, v in skills.items() if v == min_lvl][0]
                
            # ۵. کلیک روی دکمه
            res = await click_skill(panel_msg, target_skill)
            await asyncio.sleep(2) # تاخیر ۲ ثانیه‌ای برای جلوگیری از اسپم
            
            # ۶. بررسی پاپ‌آپ انرژی
            if res and hasattr(res, 'message') and res.message and "انرژی" in res.message:
                # انرژی کمه، باید بخوابه
                await client.send_message(chat_id, f"🔋 انرژی کافی نیست. {sleep_secs//3600} ساعت و {(sleep_secs%3600)//60} دقیقه صبر میکنم...")
                # خوابیدن (با قابلیت بیدار شدن فوری اگه خاموش شد)
                try:
                    await asyncio.sleep(sleep_secs + 60) # ۱ دقیقه اضافه برای اطمینان
                except asyncio.CancelledError:
                    break
                continue
                
            # اگه پاپ‌آپ انرژی نیومد، یعنی ارتقا انجام شده. حلقه از اول اجرا میشه و پنل جدید رو می‌خونه.
                
        except asyncio.CancelledError:
            # اگه دستور خاموش رو زدیم، حلقه ترک میشه
            break
        except Exception as e:
            print(f"❌ خطا در حلقه رینگ: {e}")
            await asyncio.sleep(15) # اگه اروری داد، ۱۵ ثانیه صبر کن و دوباره تلاش کن
