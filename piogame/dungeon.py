import asyncio
import re
import random
from telethon import events
import core
from core import client

dungeon_chat_id = None
debug_msg = None  # پیام دیباگ که تو تلگرام آپدیت میشه

async def log(text):
    """تابع دیباگ که پیام رو تو تلگرام آپدیت میکنه"""
    global debug_msg
    if debug_msg:
        try:
            await debug_msg.edit(f"🐞 **دیباگ دانجن:**\n\n{text}")
        except:
            pass

def parse_time(text):
    """استخراج زمان از متن (پشتیبانی از اعداد فارسی و انگلیسی)"""
    if not text:
        return 0
        
    # تبدیل اعداد فارسی به انگلیسی
    text = core.fa_to_en_digits(text)
    seconds = 0
    
    h_match = re.search(r'(\d+)\s*ساعت', text)
    if h_match:
        seconds += int(h_match.group(1)) * 3600
        
    m_match = re.search(r'(\d+)\s*دقیقه', text)
    if m_match:
        seconds += int(m_match.group(1)) * 60
        
    s_match = re.search(r'(\d+)\s*ثانیه', text)
    if s_match:
        seconds += int(s_match.group(1))
        
    return seconds

async def dungeon_loop():
    global dungeon_chat_id
    while core.dungeon_active:
        if not dungeon_chat_id:
            await asyncio.sleep(5)
            continue
            
        try:
            await log("🌀 شروع چرخه جدید...\nدر حال ارسال 'پیو دانجن'")
            await client.send_message(dungeon_chat_id, "پیو دانجن")
            await asyncio.sleep(4)
            
            msgs = await client.get_messages(dungeon_chat_id, limit=3)
            if not msgs:
                await log("⚠️ هیچ پیامی تو گروه پیدا نشد!")
                await asyncio.sleep(15)
                continue
                
            latest_msg = msgs[0]
            await log(f"🐛 آخرین پیام ربات:\n`{latest_msg.text or 'بدون متن'}`")
            
            # ۱. چک کردن اینکه آیا ربات گفته صبر کنیم یا نه
            wait_time = parse_time(latest_msg.text)
            if wait_time > 0 and ("صبر کن" in latest_msg.text or "وارد دانجن شد" in latest_msg.text or "نتیجه" in latest_msg.text):
                await log(f"⏳ ربات گفته صبر کن!\nزمان استخراج شده: `{wait_time}` ثانیه\nدر حال خواب...")
                await asyncio.sleep(wait_time + 10)
                continue 
                
            # ۲. کلیک روی دکمه‌ها
            if not latest_msg.buttons:
                await log("⚠️ دکمه‌ای روی آخرین پیام پیدا نشد!")
                await asyncio.sleep(30)
                continue
                
            await log("🖱️ کلیک روی اولین دکمه (0,0)...")
            try:
                await latest_msg.click(0, 0)
            except: pass
            await asyncio.sleep(4)
            
            # پیدا کردن دکمه "انتخاب پارتی"
            panel_msg = None
            msgs = await client.get_messages(dungeon_chat_id, limit=3)
            for m in msgs:
                if m.buttons and any("انتخاب پارتی" in btn.text for row in m.buttons for btn in row if btn):
                    panel_msg = m
                    break
                    
            if panel_msg:
                await log("🖱️ کلیک روی دکمه 'انتخاب پارتی'...")
                for row in panel_msg.buttons:
                    for btn in row:
                        if "انتخاب پارتی" in btn.text:
                            await panel_msg.click(text=btn.text)
                            break
                await asyncio.sleep(4)
            else:
                await log("⚠️ دکمه 'انتخاب پارتی' پیدا نشد!")
                
            # پیدا کردن دکمه‌های فن‌آرت
            art_msg = None
            msgs = await client.get_messages(dungeon_chat_id, limit=3)
            for m in msgs:
                if m.buttons:
                    all_btns = [btn for row in m.buttons for btn in row if btn]
                    if len(all_btns) >= 2:
                        art_msg = m
                        break
                        
            if art_msg:
                all_buttons = [btn for row in art_msg.buttons for btn in row if btn]
                await log(f"🔢 تعداد فن‌آرت‌های پیدا شده: {len(all_buttons)}")
                
                num_to_select = min(4, len(all_buttons))
                chosen_buttons = random.sample(all_buttons, num_to_select)
                
                selected_names = []
                for btn in chosen_buttons:
                    selected_names.append(btn.text)
                    await art_msg.click(text=btn.text)
                    await asyncio.sleep(1.5)
                await log(f"✅ انتخاب فن‌آرت‌ها:\n{', '.join(selected_names)}")
                await asyncio.sleep(4)
            else:
                await log("⚠️ پیام فن‌آرت‌ها پیدا نشد!")
                
            # پیدا کردن دکمه شروع
            start_msg = None
            msgs = await client.get_messages(dungeon_chat_id, limit=3)
            for m in msgs:
                if m.buttons and any("شروع" in btn.text for row in m.buttons for btn in row if btn):
                    start_msg = m
                    break
                    
            if start_msg:
                for row in start_msg.buttons:
                    for btn in row:
                        if "شروع" in btn.text:
                            await log(f"🖱️ کلیک روی دکمه: {btn.text}")
                            await start_msg.click(text=btn.text)
                            break
                await asyncio.sleep(4)
            else:
                await log("⚠️ دکمه 'شروع' پیدا نشد!")
                
            # خواندن زمان استراحت نهایی
            msgs = await client.get_messages(dungeon_chat_id, limit=3)
            if msgs:
                final_msg = msgs[0]
                await log(f"🐛 پیام نهایی ربات:\n`{final_msg.text or 'بدون متن'}`")
                wait_time = parse_time(final_msg.text)
                if wait_time > 0:
                    await log(f"⏳ دانجن شروع شد!\nربات {wait_time} ثانیه استراحت می‌کنه...")
                    await asyncio.sleep(wait_time + 10)
                else:
                    await log("⚠️ زمانی تو پیام نهایی پیدا نشد! ۶۰ ثانیه استراحت...")
                    await asyncio.sleep(60)
            else:
                await asyncio.sleep(60)
                
        except Exception as e:
            await log(f"❌ خطای کلی در دانجن:\n`{e}`")
            await asyncio.sleep(30)

@client.on(events.NewMessage(outgoing=True, pattern=r'^دانجن روشن$'))
async def dungeon_on(event):
    global dungeon_chat_id, debug_msg
    if not core.dungeon_active:
        core.dungeon_active = True
        dungeon_chat_id = event.chat_id
        # ساخت پیام دیباگ تو تلگرام
        debug_msg = await event.reply("🌀 سیستم دانجن روشن شد!\n🐞 دیباگ فعال است...")
        asyncio.create_task(dungeon_loop())
    else:
        await event.reply("❗ دانجن از قبل روشنه.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^دانجن خاموش$'))
async def dungeon_off(event):
    global debug_msg
    core.dungeon_active = False
    if debug_msg:
        await debug_msg.edit("🛑 سیستم دانجن خاموش شد.")
        debug_msg = None
    else:
        await event.reply("🛑 سیستم دانجن خاموش شد.")
