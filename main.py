import asyncio
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from telethon import TelegramClient, events
from telethon.tl.functions.account import UpdateProfileRequest
from deep_translator import GoogleTranslator
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "ربات زنده‌ست! 🐱"

def run_web():
    app.run(host='0.0.0.0', port=8080)

API_ID = 17349
API_HASH = "344583e45741c457fe1862106095a5eb"
TARGET_GROUP = -1004290700072
group_entity = None

client = TelegramClient('sessions/amir_session', API_ID, API_HASH)

collect_points_active = False
fishing_active = False
stray_cat_active = True
factory_active = False

# تابع تبدیل اعداد فارسی به انگلیسی
def fa_to_en_digits(text):
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    english_digits = '0123456789'
    translation_table = str.maketrans(persian_digits, english_digits)
    return text.translate(translation_table)

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

# ================= سیستم هلپ =================
@client.on(events.NewMessage(outgoing=True, pattern=r'^هلپ$'))
async def help_handler(event):
    help_text = (
        "📖 **راهنمای دستورات سلف‌بات:**\n\n"
        "🔹 **ترجمه کن**\n(با ریپلای روی یک پیام) متن را به فارسی ترجمه می‌کند.\n\n"
        "🔹 **اسپم 1 [تعداد] [متن]**\nمثال: `اسپم 1 10 سلام` یا `اسپم ۱ ۱۰ سلام`\nتعداد مشخص شده پیام جداگانه حاوی متن را می‌فرستد. (اگه ریپلای کنی، پیام‌ها ریپلای میشن)\n\n"
        "🔹 **اسپم 2 [تعداد] [متن]**\nمثال: `اسپم 2 10 سلام` یا `اسپم ۲ ۱۰ سلام`\nیک پیام می‌فرستد که در آن متن به تعداد مشخص شده تکرار شده است.\n\n"
        "🔹 **پوینت روشن / پوینت خاموش**\nجمع‌آوری خودکار پوینت بازی را روشن یا خاموش می‌کند.\n\n"
        "🔹 **ماهی روشن / ماهی خاموش**\nسیستم ماهیگیری خودکار را روشن یا خاموش می‌کند.\n\n"
        "🔹 **کارخونه میویی روشن / کارخونه میویی خاموش**\nچرخه کامل تولید و فروش کارخونه را مدیریت می‌کند (هر ۲۴ ساعت).\n\n"
        "🔹 **هلپ**\nهمین پیام راهنما را نمایش می‌دهد."
    )
    await event.reply(help_text)
# ==============================================

# ================= سیستم اسپم =================
async def run_spam(model, count, text, chat_id, reply_to=None):
    try:
        if model == 1:
            for i in range(count):
                await client.send_message(chat_id, text, reply_to=reply_to)
                await asyncio.sleep(0.5) # تاخیر نیم ثانیه‌ای برای جلوگیری از بن
        elif model == 2:
            full_text = (text + " ") * count
            if len(full_text) > 4096:
                full_text = full_text[:4090] + "..."
                print("⚠️ متن خیلی طولانی بود، کوتاه شد تا تلگرام ارور نده.")
            await client.send_message(chat_id, full_text, reply_to=reply_to)
    except Exception as e:
        print(f"❌ خطا در اسپم: {type(e).__name__}: {e}")

@client.on(events.NewMessage(outgoing=True, pattern=r'^اسپم ([12۱۲]) ([\d۰-۹]+) (.+)$'))
async def spam_handler(event):
    # تبدیل اعداد فارسی به انگلیسی
    model_str = fa_to_en_digits(event.pattern_match.group(1))
    count_str = fa_to_en_digits(event.pattern_match.group(2))
    
    model = int(model_str)
    count = int(count_str)
    text = event.pattern_match.group(3)
    chat_id = event.chat_id
    
    if count > 1000:
        await event.reply("❗ برای جلوگیری از بن، حداکثر تعداد ۱۰۰۰ تعیین شده.")
        return

    # بررسی اینکه آیا کاربر روی پیامی ریپلای کرده یا نه
    reply_to_id = None
    if event.message.is_reply:
        replied_msg = await event.message.get_reply_message()
        if replied_msg:
            reply_to_id = replied_msg.id

    # فرستادن پیام تایید، پاک کردن دستور کاربر و پاک کردن پیام تایید
    reply_msg = await event.reply(f"🚀 شروع اسپم مدل {model} ({count} بار)...")
    await event.delete()
    await reply_msg.delete()

    # اجرای اسپم در پس‌زمینه
    asyncio.create_task(run_spam(model, count, text, chat_id, reply_to_id))
# ==============================================

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

# ================= سیستم کارخونه =================

async def click_factory_button(msg_id, target_text, timeout=30):
    for _ in range(timeout):
        await asyncio.sleep(1)
        msg = await client.get_messages(group_entity, ids=msg_id)
        if msg and msg.buttons:
            for row in msg.buttons:
                for btn in row:
                    if target_text in btn.text:
                        await msg.click(text=btn.text)
                        print(f"✅ روی دکمه «{btn.text}» کلیک شد.")
                        return True
    print(f"⚠️ دکمه شامل «{target_text}» پیدا نشد.")
    return False

async def click_factory_coords(msg_id, row_idx, col_idx, timeout=30):
    for _ in range(timeout):
        await asyncio.sleep(1)
        msg = await client.get_messages(group_entity, ids=msg_id)
        if msg and msg.buttons:
            try:
                await msg.click(row_idx, col_idx)
                print(f"✅ روی مختصات (ردیف {row_idx}، ستون {col_idx}) کلیک شد.")
                return True
            except Exception:
                pass
    print(f"⚠️ دکمه در مختصات (ردیف {row_idx}، ستون {col_idx}) پیدا نشد.")
    return False

async def factory_cycle():
    global factory_active
    while factory_active:
        try:
            print("🏭 شروع چرخه کارخونه (فاز تولید)...")
            await client.send_message(group_entity, "کارخونه میویی")
            await asyncio.sleep(3)
            
            panel_msg = None
            async for m in client.iter_messages(group_entity, limit=5):
                if m.buttons:
                    panel_msg = m
                    break
            
            if not panel_msg:
                print("⚠️ پنل کارخونه پیدا نشد. تلاش مجدد در ۱۰ ثانیه...")
                await asyncio.sleep(10)
                continue
            
            panel_id = panel_msg.id
            
            if not await click_factory_button(panel_id, "تولید"): continue
            await asyncio.sleep(2)
            if not await click_factory_button(panel_id, "تولیدی هواپیما"): continue
            await asyncio.sleep(2)
            if not await click_factory_coords(panel_id, 0, 2): continue
            await asyncio.sleep(2)
            if not await click_factory_coords(panel_id, 0, 3): continue
            await asyncio.sleep(2)
            if not await click_factory_button(panel_id, "شروع تولید"): continue
            
            print("⏳ تولید استارت خورد. سیستم ۲۴ ساعت صبر می‌کنه...")
            waited = 0
            while waited < 86400 and factory_active:
                await asyncio.sleep(60)
                waited += 60
            
            if not factory_active:
                break
            
            print("💰 زمان فروش رسید. شروع فاز فروش...")
            await client.send_message(group_entity, "کارخونه میویی")
            await asyncio.sleep(3)
            
            panel_msg = None
            async for m in client.iter_messages(group_entity, limit=5):
                if m.buttons:
                    panel_msg = m
                    break
            
            if not panel_msg:
                print("⚠️ پنل فروش پیدا نشد.")
                continue
            
            panel_id = panel_msg.id
            
            if not await click_factory_button(panel_id, "انبار"): continue
            await asyncio.sleep(2)
            if not await click_factory_coords(panel_id, 0, 0): continue
            await asyncio.sleep(2)
            if not await click_factory_button(panel_id, "فروش محصول"): continue
            
            print("✅ فروش انجام شد. چرخه از اول تکرار میشه...")
            await asyncio.sleep(3)
            
        except Exception as e:
            print(f"❌ خطا در کارخونه: {type(e).__name__}: {e}")
            await asyncio.sleep(10)

@client.on(events.NewMessage(outgoing=True, pattern=r'^کارخونه میویی روشن$'))
async def factory_on(event):
    global factory_active
    if not factory_active:
        factory_active = True
        await event.reply("🏭 سیستم کارخونه میویی **روشن** شد.")
        asyncio.create_task(factory_cycle())
    else:
        await event.reply("❗ کارخونه از قبل روشنه.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^کارخونه میویی خاموش$'))
async def factory_off(event):
    global factory_active
    factory_active = False
    await event.reply("🛑 سیستم کارخونه میویی **خاموش** شد.")

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
    import time
    while True:
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    with client:
        client.loop.run_until_complete(main())
