import asyncio
import re
import random
from telethon import events
import core
from core import client

# متغیر برای نگه داشتن آیدی گروهی که دانجن توش فعال شده
dungeon_chat_id = None

def parse_time(text):
    """استخراج زمان از متن و تبدیل به ثانیه"""
    seconds = 0
    # پیدا کردن ساعت
    h_match = re.search(r'(\d+)\s*ساعت', text)
    if h_match:
        seconds += int(h_match.group(1)) * 3600
    # پیدا کردن دقیقه
    m_match = re.search(r'(\d+)\s*دقیقه', text)
    if m_match:
        seconds += int(m_match.group(1)) * 60
    # پیدا کردن ثانیه (برای احتیاط)
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
            print("🌀 شروع چرخه دانجن...")
            # ۱. ارسال پیو دانجن
            await client.send_message(dungeon_chat_id, "پیو دانجن")
            await asyncio.sleep(4)
            
            # ۲. پیدا کردن پیام ربات و کلیک روی اولین دکمه
            target_msg = None
            async for m in client.iter_messages(dungeon_chat_id, limit=5):
                if m.buttons:
                    target_msg = m
                    break
                    
            if not target_msg or not target_msg.buttons:
                print("⚠️ پیام دانجن پیدا نشد.")
                await asyncio.sleep(15)
                continue
                
            # کلیک روی اولین دکمه (گزینه زیر پیام اول)
            try:
                await target_msg.click(0, 0)
                print("✅ کلیک روی دکمه اول انجام شد.")
            except: pass
            await asyncio.sleep(4)
            
            # ۳. پیدا کردن دکمه "انتخاب پارتی"
            target_msg = None
            async for m in client.iter_messages(dungeon_chat_id, limit=5):
                if m.buttons and any("انتخاب پارتی" in btn.text for row in m.buttons for btn in row):
                    target_msg = m
                    break
                    
            if not target_msg:
                print("⚠️ دکمه انتخاب پارتی پیدا نشد. شاید زمان صبر کردن رفته.")
                # بررسی اینکه آیا ربات پیام صبر کردن داده یا خیر
                async for m in client.iter_messages(dungeon_chat_id, limit=3):
                    if m.text and ("صبر کن" in m.text or "وارد دانجن شد" in m.text):
                        wait_time = parse_time(m.text)
                        if wait_time > 0:
                            print(f"⏳ زمان استراحت استخراج شد: {wait_time} ثانیه")
                            await asyncio.sleep(wait_time + 5)
                        break
                continue
                
            # کلیک روی انتخاب پارتی
            for row in target_msg.buttons:
                for btn in row:
                    if "انتخاب پارتی" in btn.text:
                        await target_msg.click(text=btn.text)
                        print("✅ کلیک روی انتخاب پارتی انجام شد.")
                        break
            await asyncio.sleep(4)
            
            # ۴. انتخاب فن‌آرت‌ها (رندوم)
            target_msg = None
            async for m in client.iter_messages(dungeon_chat_id, limit=5):
                if m.buttons and any("فن‌آرت" in btn.text for row in m.buttons for btn in row if btn):
                    # گاهی دکمه فن‌آرت متنش عوض میشه، پس چک میکنیم اگه دکمه‌های زیادی داره
                    target_msg = m
                    break
                elif m.buttons and len(m.buttons) > 1: # اگه چندتا دکمه اومد
                    target_msg = m
                    break
                    
            if target_msg and target_msg.buttons:
                # جمع آوری تمام دکمه‌ها
                all_buttons = [btn for row in target_msg.buttons for btn in row if btn]
                # اگر ۴ تا یا کمتر بود، همه رو می‌زنه، اگر بیشتر بود ۴ تاش رندوم
                num_to_select = min(4, len(all_buttons))
                chosen_buttons = random.sample(all_buttons, num_to_select)
                
                for btn in chosen_buttons:
                    try:
                        await target_msg.click(text=btn.text)
                        print(f"✅ انتخاب فن‌آرت: {btn.text}")
                        await asyncio.sleep(1.5)
                    except: pass
            else:
                print("⚠️ پیام فن‌آرت‌ها پیدا نشد!")
                
            await asyncio.sleep(4)
            
            # ۵. کلیک روی دکمه شروع (x عضو)
            target_msg = None
            async for m in client.iter_messages(dungeon_chat_id, limit=5):
                if m.buttons and any("شروع" in btn.text for row in m.buttons for btn in row if btn):
                    target_msg = m
                    break
                    
            if target_msg:
                for row in target_msg.buttons:
                    for btn in row:
                        if "شروع" in btn.text:
                            await target_msg.click(text=btn.text)
                            print(f"✅ کلیک روی دکمه: {btn.text}")
                            break
            else:
                print("⚠️ دکمه شروع پیدا نشد!")
                
            await asyncio.sleep(4)
            
            # ۶. خواندن زمان استراحت (وارد دانجن شد یا صبر کن)
            target_msg = None
            async for m in client.iter_messages(dungeon_chat_id, limit=5):
                if m.text and ("وارد دانجن شد" in m.text or "صبر کن" in m.text or "نتیجه رو" in m.text):
                    target_msg = m
                    break
                    
            if target_msg and target_msg.text:
                wait_time = parse_time(target_msg.text)
                if wait_time > 0:
                    print(f"⏳ دانجن انجام شد. ربات {wait_time} ثانیه استراحت می‌کند...")
                    # یکم زمان اضافه برای اطمینان
                    await asyncio.sleep(wait_time + 10)
                else:
                    print("⚠️ زمانی پیدا نشد، ۶۰ ثانیه استراحت پیش‌فرض.")
                    await asyncio.sleep(60)
            else:
                print("⚠️ پیام تایید نهایی پیدا نشد. ۶۰ ثانیه استراحت.")
                await asyncio.sleep(60)
                
        except Exception as e:
            print(f"❌ خطای کلی در دانجن: {e}")
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
