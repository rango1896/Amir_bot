import asyncio
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from telethon import TelegramClient, events
from telethon.tl.functions.account import UpdateProfileRequest
from deep_translator import GoogleTranslator
from flask import Flask
import threading

# ====== وب‌سرور برای بیدار موندن ======
app = Flask(__name__)

@app.route('/')
def home():
    return "ربات زنده‌ست! 🐱"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# ====== تنظیمات تلگرام ======
API_ID = 17349
API_HASH = "344583e45741c457fe1862106095a5eb"
TARGET_GROUP = -1004290700072
group_entity = None

client = TelegramClient('amir_session', API_ID, API_HASH)

collect_points_active = False
fishing_active = False
stray_cat_active = True

def to_double_struck(text):
    normal = "0123456789"
    double_struck = "𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡"
    result = ""
    for char in text:
        if char in normal:
            index = normal.index(char)
            result += double_struck[index]
        else:
            result += char
    return result

def strip_clock(name):
    parts = name.rsplit(' ', 1)
    if len(parts) == 2:
        last = parts[1]
        if re.fullmatch(r'[0-9𝟘-𝟡]+:[0-9𝟘-𝟡]+', last):
            return parts[0]
    return name

@client.on(events.NewMessage(outgoing=True, pattern=r'^ترجمه کن$'))
async def translate_reply(event):
    if not event.message.is_reply:
        await event.reply("❗ لطفاً روی یه پیام ریپلای بزن و بعد دستور رو بفرست.")
        return
    replied_msg = await event.message.get_reply_message()
    if not replied_msg or not replied_msg.text:
        await event.reply("❗ پیام ریپلای شده متن نداره.")
        return
    original_text = replied_msg.text
    try:
        translated = GoogleTranslator(source='auto', target='fa').translate(original_text)
        await event.reply(f"🔸 ترجمه:\n{translated}")
    except Exception as e:
        await event.reply(f"❌ خطا: {type(e).__name__}: {e}")

POINTS_INTERVAL = 600

async def do_collect_points():
    try:
        await client.send_message(group_entity, "پیشی")
        print("📩 پیشی فرستاده شد. منتظر پنل...")
        found = False
        for attempt in range(30):
            await asyncio.sleep(2)
            messages = await client.get_messages(group_entity, limit=10)
            for msg in messages:
                if msg.buttons:
                    for row in msg.buttons:
                        for btn in row:
                            if "برداشت" in btn.text and "میو" in btn.text:
                                await msg.click(text=btn.text)
                                print(f"✅ روی دکمه «{btn.text}» کلیک شد.")
                                found = True
                                break
                        if found:
                            break
                if found:
                    break
            if found:
                break
        if not found:
            print("⚠️ دکمه برداشت پیدا نشد.")
    except Exception as e:
        print(f"❌ خطا: {type(e).__name__}: {e}")

@client.on(events.NewMessage(outgoing=True, pattern=r'^پوینت روشن$'))
async def points_on(event):
    global collect_points_active
    collect_points_active = True
    await event.reply("✅ جمع‌آوری خودکار پوینت **روشن** شد.")
    await do_collect_points()

@client.on(events.NewMessage(outgoing=True, pattern=r'^پوینت خاموش$'))
async def points_off(event):
    global collect_points_active
    collect_points_active = False
    await event.reply("🛑 جمع‌آوری خودکار پوینت **خاموش** شد.")

FISHING_INTERVAL = 3600

async def do_fishing():
    try:
        await client.send_message(group_entity, "ماهی")
        print("📩 ماهی فرستاده شد. منتظر پنل...")
        found = False
        for attempt in range(30):
            await asyncio.sleep(2)
            messages = await client.get_messages(group_entity, limit=10)
            for msg in messages:
                if msg.buttons:
                    for row in msg.buttons:
                        for btn in row:
                            if "بده پیشی" in btn.text:
                                await msg.click(text=btn.text)
                                print(f"✅ روی دکمه «{btn.text}» کلیک شد.")
                                found = True
                                break
                        if found:
                            break
                if found:
                    break
            if found:
                break
        if not found:
            print("⚠️ دکمه ماهیگیری پیدا نشد.")
    except Exception as e:
        print(f"❌ خطا: {type(e).__name__}: {e}")

@client.on(events.NewMessage(outgoing=True, pattern=r'^ماهی روشن$'))
async def fishing_on(event):
    global fishing_active
    fishing_active = True
    await event.reply("🎣 سیستم ماهیگیری **روشن** شد.")
    await do_fishing()

@client.on(events.NewMessage(outgoing=True, pattern=r'^ماهی خاموش$'))
async def fishing_off(event):
    global fishing_active
    fishing_active = False
    await event.reply("🛑 سیستم ماهیگیری **خاموش** شد.")

async def collect_points_loop():
    global collect_points_active
    while True:
        await asyncio.sleep(POINTS_INTERVAL)
        if collect_points_active:
            await do_collect_points()

async def fishing_loop():
    global fishing_active
    while True:
        await asyncio.sleep(FISHING_INTERVAL)
        if fishing_active:
            await do_fishing()

# ====== 📌 ساعت زنده با وقت تهران ======
TEHRAN_TZ = ZoneInfo("Asia/Tehran")

async def update_name_clock():
    while True:
        try:
            me = await client.get_me()
            base_name = strip_clock(me.first_name or "")
            now = datetime.now(TEHRAN_TZ).strftime("%H:%M")
            clock_str = to_double_struck(now)
            new_name = f"{base_name} {clock_str}" if base_name else clock_str
            await client(UpdateProfileRequest(first_name=new_name))
            print(f"🕒 اسم به‌روز شد (تهران): {new_name}")
        except Exception as e:
            print(f"❌ خطا: {type(e).__name__}: {e}")
        await asyncio.sleep(60)

# ==================================

async def meow_loop():
    while True:
        try:
            await client.send_message(group_entity, "میو")
            print("🐱 میو فرستاده شد")
        except Exception as e:
            print(f"❌ خطا: {type(e).__name__}: {e}")
        await asyncio.sleep(300)

stray_lock = asyncio.Lock()

async def rescue_stray_cat(msg):
    async with stray_lock:
        print("🐈 شروع عملیات نجات گربه خیابونی...")
        for i in range(3):
            try:
                current_msg = await client.get_messages(group_entity, ids=msg.id)
                if not current_msg or not current_msg.buttons:
                    print("⚠️ پیام گربه ناپدید شد.")
                    break
                for row in current_msg.buttons:
                    for btn in row:
                        if "نجات پیشی خیابونی" in btn.text:
                            await current_msg.click(text=btn.text)
                            print(f"✅ کلیک {i+1}/۳ روی «{btn.text}»")
                            break
                    else:
                        continue
                    break
                else:
                    print("⚠️ دکمه نجات پیدا نشد.")
                    break
                if i < 2:
                    await asyncio.sleep(2)
            except Exception as e:
                print(f"❌ خطا: {type(e).__name__}: {e}")
                break
        print("🏁 عملیات نجات تموم شد.")

@client.on(events.NewMessage(incoming=True))
async def stray_cat_handler(event):
    if not stray_cat_active:
        return
    if not event.is_group or event.chat_id != TARGET_GROUP:
        return
    if event.message.buttons:
        for row in event.message.buttons:
            for btn in row:
                if "نجات پیشی خیابونی" in btn.text:
                    print("🐈 گربه خیابونی دیده شد! شروع نجات...")
                    await rescue_stray_cat(event.message)
                    return

async def main():
    global group_entity
    await client.start()
    group_entity = await client.get_entity(TARGET_GROUP)
    print(f"✅ گروه پیدا شد: {group_entity.title}")
    print("✅ سلف‌بات Amir روشن شد!")

    await asyncio.gather(
        meow_loop(),
        update_name_clock(),
        collect_points_loop(),
        fishing_loop()
    )

def keep_alive():
    """یه حلقه ساده برای بیدار نگه داشتن Render"""
    import time
    while True:
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    with client:
        client.loop.run_until_complete(main())
