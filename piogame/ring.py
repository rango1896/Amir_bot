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
    matches = re.findall(r'•\s*(سرعت|مهارت|قدرت|سلامتی):\s*لول\s*(\d+)', text)
    for name, lvl in matches:
        skills[name] = int(lvl)
        
    time_match = re.search(r'(\d+)\s*ساعت\s*و\s*(\d+)\s*دقیقه', text)
    if time_match:
        hours = int(time_match.group(1))
        mins = int(time_match.group(2))
        return skills, (hours * 3600) + (mins * 60)
        
    time_match_min = re.search(r'(\d+)\s*دقیقه', text)
    if time_match_min:
        return skills, int(time_match_min.group(1)) * 60
        
    return skills, 3600

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
            panel_msg = None
            
            # ۲. جستجوی فوق‌قدرتمند برای پیدا کردن پنل (تا ۲۰ ثانیه)
            for _ in range(4):
                await asyncio.sleep(5) # هر ۵ ثانیه یه بار چک میکنه
                
                # خوندن ۱۰ پیام آخر گروه
                messages = await client.get_messages(chat_id, limit=10)
                for msg in messages:
                    # اگه پیام از طرف خودمون نبود و توش کلمات کلیدی پنل بود
                    if not msg.out and msg.text and "انرژی" in msg.text and "لول" in msg.text:
                        # اگه زمان پیام، بعد از زمان فرستادن دستور ما بود (یا ریپلای بود)
                        if msg.id > sent_msg.id or msg.reply_to_msg_id == sent_msg.id:
                            panel_msg = msg
                            break
                if panel_msg:
                    break # پنل پیدا شد، برو برای ارتقا
                    
            if not panel_msg:
                # اگه بعد از ۲۰ ثانیه پنل پیدا نشد
                print("❗ پنل رینگ پیدا نشد، دوباره تلاش میکنم...")
                await asyncio.sleep(5)
                continue
                
            # پیام تایید برای اینکه بدونی ربات پنل رو دیده
            await client.send_message(chat_id, "✅ پنل تشخیص داده شد! در حال پردازش مهارت‌ها...")
            
            text = panel_msg.text
            
            # ۳. تحلیل پنل
            skills, sleep_secs = parse_panel(text)
            if not skills:
                print("❗ مهارت‌ها در پنل پیدا نشد!")
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
                hours = sleep_secs // 3600
                mins = (sleep_secs % 3600) // 60
                await client.send_message(chat_id, f"🔋 انرژی کافی نیست. {hours} ساعت و {mins} دقیقه صبر میکنم...")
                
                try:
                    await asyncio.sleep(sleep_secs + 60) # ۱ دقیقه اضافه برای اطمینان
                except asyncio.CancelledError:
                    break # اگه دستور خاموش زده شد، بیدار شو و تموم کن
                continue # بعد از بیدار شدن، حلقه از اول شروع میشه
                
            # اگه پاپ‌آپ انرژی نیومد، یعنی ارتقا انجام شده. حلقه از اول اجرا میشه و پنل جدید رو می‌خونه.
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"❌ خطا در حلقه رینگ: {e}")
            await asyncio.sleep(15)
