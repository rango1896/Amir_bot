import asyncio
import re
import random
from telethon import events
import core
from core import client

dungeon_chat_id = None

async def log(text):
    """تابع دیباگ که پیام‌های جداگانه تو تلگرام میفرسته"""
    if dungeon_chat_id:
        try:
            await client.send_message(dungeon_chat_id, f"🐞 {text}")
        except: pass

def parse_time(text):
    """استخراج زمان از متن (پشتیبانی از اعداد فارسی و انگلیسی)"""
    if not text:
        return 0
        
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
            await log("🌀 شروع چرخه جدید... در حال ارسال 'پیو دانجن'")
            my_msg = await client.send_message(dungeon_chat_id, "پیو دانجن")
            await asyncio.sleep(10) # صبر ۱۰ ثانیه‌ای برای کندی ربات پیو
            
            # گرفتن ۱۰ پیام اخیر گروه
            msgs = await client.get_messages(dungeon_chat_id, limit=10)
            
            # ۱. جستجو برای پیام استراحت یا ران فعال (فقط پیام‌های ربات بازی)
            found_cooldown = False
            for m in msgs:
                if m.id <= my_msg.id: continue # پیام‌های قبل از دستور ما رو نگا نکن
                if m.text and not m.out:
                    if "صبر کن" in m.text or "وارد دانجن شد" in m.text or "نتیجه" in m.text or "ران فعال" in m.text or "تموم می‌شه" in m.text:
                        wait_time = parse_time(m.text)
                        if wait_time > 0:
                            await log(f"⏳ پیام استراحت/ران فعال پیدا شد:\nربات {wait_time} ثانیه میخوابه.")
                            found_cooldown = True
                            await asyncio.sleep(wait_time + 10)
                            break
            
            if found_cooldown:
                continue
                
            # ۲. پیدا کردن پیام دکمه‌دار اول (برای کلیک 0,0)
            first_panel = None
            for m in msgs:
                if m.id <= my_msg.id: continue
                if m.buttons and not m.out:
                    first_panel = m
                    break
                    
            if not first_panel:
                await log("⚠️ پنل دکمه‌دار اول پیدا نشد!")
                await asyncio.sleep(30)
                continue
                
            await log("🖱️ کلیک روی اولین دکمه (0,0)...")
            try:
                await first_panel.click(0, 0)
            except: pass
            await asyncio.sleep(10)
            
            # ۳. پیدا کردن دکمه "انتخاب پارتی" (می‌تونه تو همون پیام ادیت شده باشه یا پیام جدید)
            msgs = await client.get_messages(dungeon_chat_id, limit=10)
            party_panel = None
            for m in msgs:
                if m.buttons and not m.out:
                    if any("پارتی" in btn.text for row in m.buttons for btn in row if btn):
                        party_panel = m
                        break
                        
            if party_panel:
                await log("🖱️ کلیک روی دکمه 'انتخاب پارتی'...")
                for row in party_panel.buttons:
                    for btn in row:
                        if "پارتی" in btn.text:
                            await party_panel.click(text=btn.text)
                            break
                await asyncio.sleep(10)
            else:
                await log("⚠️ دکمه 'انتخاب پارتی' پیدا نشد!")
                
            # ۴. پیدا کردن دکمه‌های فن‌آرت (دکمه‌هایی که پارتی یا شروع نیستن)
            msgs = await client.get_messages(dungeon_chat_id, limit=10)
            art_msg = None
            for m in msgs:
                if m.buttons and not m.out:
                    all_btns = [btn for row in m.buttons for btn in row if btn]
                    if len(all_btns) >= 2:
                        is_party = any("پارتی" in btn.text for row in m.buttons for btn in row if btn)
                        is_start = any("شروع" in btn.text for row in m.buttons for btn in row if btn)
                        if not is_party and not is_start:
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
                    await asyncio.sleep(2)
                await log(f"✅ انتخاب فن‌آرت‌ها:\n{', '.join(selected_names)}")
                await asyncio.sleep(10)
            else:
                await log("⚠️ پیام فن‌آرت‌ها پیدا نشد!")
                
            # ۵. پیدا کردن دکمه شروع
            msgs = await client.get_messages(dungeon_chat_id, limit=10)
            start_msg = None
            for m in msgs:
                if m.buttons and not m.out and any("شروع" in btn.text for row in m.buttons for btn in row if btn):
                    start_msg = m
                    break
                    
            if start_msg:
                for row in start_msg.buttons:
                    for btn in row:
                        if "شروع" in btn.text:
                            await log(f"🖱️ کلیک روی دکمه: {btn.text}")
                            await start_msg.click(text=btn.text)
                            break
                await asyncio.sleep(10)
            else:
                await log("⚠️ دکمه 'شروع' پیدا نشد!")
                
            # ۶. خواندن زمان استراحت نهایی
            msgs = await client.get_messages(dungeon_chat_id, limit=10)
            final_found = False
            for m in msgs:
                if m.id <= my_msg.id: continue
                if m.text and not m.out:
                    if "صبر کن" in m.text or "وارد دانجن شد" in m.text or "نتیجه" in m.text or "ران فعال" in m.text or "تموم می‌شه" in m.text:
                        wait_time = parse_time(m.text)
                        if wait_time > 0:
                            await log(f"⏳ دانجن شروع شد!\nربات {wait_time} ثانیه استراحت می‌کنه...")
                            final_found = True
                            await asyncio.sleep(wait_time + 10)
                            break
                            
            if not final_found:
                await log("⚠️ زمانی تو پیام نهایی پیدا نشد! ۶۰ ثانیه استراحت...")
                await asyncio.sleep(60)
                
        except Exception as e:
            await log(f"❌ خطای کلی در دانجن:\n`{e}`")
            await asyncio.sleep(30)

@client.on(events.NewMessage(outgoing=True, pattern=r'^دانجن روشن$'))
async def dungeon_on(event):
    global dungeon_chat_id
    if not core.dungeon_active:
        core.dungeon_active = True
        dungeon_chat_id = event.chat_id
        await event.reply("🌀 سیستم دانجن روشن شد!")
        asyncio.create_task(dungeon_loop())
    else:
        await event.reply("❗ دانجن از قبل روشنه.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^دانجن خاموش$'))
async def dungeon_off(event):
    core.dungeon_active = False
    await event.reply("🛑 سیستم دانجن خاموش شد.")
