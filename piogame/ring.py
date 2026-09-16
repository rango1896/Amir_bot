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
    # پیدا کردن لول هر مهارت (با حذف فاصله‌های اضافی)
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
            
            panel_msg = None
            
            # ۲. جستجوی هوشمند برای پیدا کردن پنل (تا ۱۵ ثانیه)
            for _ in range(3):
                await asyncio.sleep(5) # هر ۵ ثانیه یه بار چک میکنه
                # اسکن ۵ پیام آخر چت
                async for msg in client.iter_messages(chat_id, limit=5):
                    # اگه پیام بعد از دستور ما بود و توش این کلمات بود، همون پنله!
                    if msg.id > sent_msg.id and msg.text and "انرژی:" in msg.text and "لول" in msg.text:
                        panel_msg = msg
                        break
                if panel_msg:
                    break # پنل پیدا شد، برو برای ارتقا
                    
            if not panel_msg:
                # اگه بعد از ۱۵ ثانیه پنل پیدا نشد
                print("❗ پنل رینگ پیدا نشد، دوباره تلاش میکنم...")
                await asyncio.sleep(10)
                continue
                
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
            
            # ۶. بررسی پاپ‌آپ انرژی (تقویت شده)
            if res and hasattr(res, 'message') and res.message and "انرژی" in res.message:
                # انرژی کمه، باید بخوابه
                hours = sleep_secs // 3600
                mins = (sleep_secs % 3600) // 60
                await client.send_message(chat_id, f"🔋 انرژی کافی نیست. {hours} ساعت و {mins} دقیقه صبر میکنم...")
                
                # خوابیدن (با قابلیت بیدار شدن فوری اگه خاموش شد)
                try:
                    await asyncio.sleep(sleep_secs + 60) # ۱ دقیقه اضافه برای اطمینان
                except asyncio.CancelledError:
                    break # اگه دستور خاموش زده شد، از خواب بیدار شو و تموم کن
                continue # بعد از بیدار شدن، حلقه از اول شروع میشه
                
            # اگه پاپ‌آپ انرژی نیومد، یعنی ارتقا انجام شده. حلقه از اول اجرا میشه و پنل جدید رو می‌خونه.
                
        except asyncio.CancelledError:
            # اگه دستور خاموش رو زدیم، حلقه ترک میشه
            break
        except Exception as e:
            print(f"❌ خطا در حلقه رینگ: {e}")
            await asyncio.sleep(15) # اگه اروری داد، ۱۵ ثانیه صبر کن و دوباره تلاش کن
