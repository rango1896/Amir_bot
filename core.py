import asyncio
import os
import re
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from telethon import TelegramClient, events, utils
from telethon.tl.functions.account import UpdateProfileRequest

# FIX(F11 - امنیتی، اختیاری): اگه متغیرهای محیطی PIOU_API_ID/PIOU_API_HASH
# تنظیم شده باشن، همونا استفاده میشن؛ در غیر این‌صورت همون مقادیر قبلی
# به‌عنوان فال‌بک می‌مونن تا هیچ رفتاری بدون تنظیم صریح عوض نشه.
# پیشنهاد: این دو مقدار (به‌خصوص API_HASH) از کد خارج و در یک فایل .env
# (خارج از گیت/هرجای عمومی) نگهداری بشن — همون‌طور که الان هستن، هر کسی که
# این فایل رو ببینه به اکانت تلگرام API دسترسی داره.
API_ID = int(os.environ.get("PIOU_API_ID", 17349))
API_HASH = os.environ.get("PIOU_API_HASH", "344583e45741c457fe1862106095a5eb")
TARGET_GROUP = -1004290700072  # گروه بازی خودت
group_entity = None

client = TelegramClient('sessions/amir_session', API_ID, API_HASH)

# === متغیرهای مشترک ربات ===
collect_points_active = False
fishing_active = False
stray_cat_active = True
factory_active = False

DB_TAG = "#DB_AMIR"
DB_CHAT = "hankhhh" # گروهی که دیتابیس اصلی توش ذخیره میشه
anti_delete_active = False
anti_delete_targets = {}
message_cache = {}
scheduled_messages = []
keyword_alert_active = False
keywords_list = set()
ghost_mode_active = False
tag_targets = {}
notes_list = []
auto_react_targets = {}
NOTES_PASSWORD = "amir1370"
TEHRAN_TZ = ZoneInfo("Asia/Tehran")

# === متغیرهای پیو ===
DB_PIOU_TAG = "#DB_PIOU"
pio_active_group = None
pio_target_links = {}

# === توابع کمکی ===
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

# === توابع دیتابیس تلگرامی ===
async def load_db():
    global anti_delete_targets, tag_targets, notes_list, keywords_list, auto_react_targets
    global pio_active_group, pio_target_links

    # لود دیتابیس اصلی ربات از گروه hankhhh
    # FIX(F10): قبلاً اگه خود iter_messages خطا میداد (مثلاً DB_CHAT در دسترس
    # نبود/ریمو شده بود)، این خطا هیچ‌جا گرفته نمی‌شد و کل استارتاپ main.py
    # کرش می‌کرد. حالا این حلقه هم محافظت میشه و ربات با دیتابیس خالی بالا
    # میاد به‌جای این‌که اصلاً روشن نشه.
    try:
        async for msg in client.iter_messages(DB_CHAT, limit=50):
            if msg.text and msg.text.startswith(DB_TAG):
                try:
                    json_str = msg.text.replace(DB_TAG, "").strip()
                    if json_str:
                        data = json.loads(json_str)
                        anti_delete_targets = {int(k): v for k, v in data.get("anti_delete", {}).items()}
                        tag_targets = {int(k): v for k, v in data.get("tags", {}).items()}
                        notes_list = data.get("notes", [])
                        keywords_list = set(data.get("keywords", []))
                        auto_react_targets = {int(k): v for k, v in data.get("reactions", {}).items()}
                        print("✅ دیتابیس ربات از گروه بارگذاری شد.")
                except Exception as e:
                    print(f"❌ خطا در خواندن دیتابیس: {e}")
                break
    except Exception as e:
        print(f"❌ خطا در دسترسی به گروه دیتابیس ({DB_CHAT}) — دیتابیس اصلی خالی شروع میشه: {e}")

    # لود دیتابیس پیو از گروه hankhhh
    try:
        async for msg in client.iter_messages(DB_CHAT, limit=50):
            if msg.text and msg.text.startswith(DB_PIOU_TAG):
                try:
                    json_str = msg.text.replace(DB_PIOU_TAG, "").strip()
                    if json_str:
                        data = json.loads(json_str)
                        pio_active_group = data.get("active_group", None)
                        pio_target_links = {int(k): v for k, v in data.get("links", {}).items()}
                        print("✅ تنظیمات پیو از گروه بارگذاری شد.")
                except Exception as e:
                    print(f"❌ خطا در خواندن دیتابیس پیو: {e}")
                break
    except Exception as e:
        print(f"❌ خطا در دسترسی به گروه دیتابیس ({DB_CHAT}) — تنظیمات پیو خالی شروع میشه: {e}")

async def save_db():
    data = {
        "anti_delete": {str(k): v for k, v in anti_delete_targets.items()},
        "tags": {str(k): v for k, v in tag_targets.items()},
        "notes": notes_list,
        "keywords": list(keywords_list),
        "reactions": {str(k): v for k, v in auto_react_targets.items()}
    }
    json_str = json.dumps(data, ensure_ascii=False)
    text_to_save = f"{DB_TAG} {json_str}" # همون فرمت ساده قبلی

    # FIX(F9 - مهم‌ترین باگ این فایل): قبلاً اینجا با text_to_save[:4000]
    # کاراکتر آخر بریده می‌شد. بریدن وسط یک رشته‌ی JSON تقریباً همیشه یک
    # JSON نامعتبر تولید میکنه. دفعه‌ی بعد که load_db همین پیام رو میخوند،
    # json.loads خطا میداد و anti_delete_targets/tag_targets/notes_list/
    # keywords_list/auto_react_targets همه به‌صورت خالی برمیگشتن — یعنی یک
    # «ذخیره‌ی موفق» در واقع کل دیتابیس رو در بارگذاری بعدی نابود میکرد.
    # حالا وقتی داده بزرگ‌تر از حد امنه، ذخیره متوقف میشه و پیام قبلیِ
    # سالم دست‌نخورده باقی می‌مونه، به‌جای این‌که با داده‌ی خراب جایگزین بشه.
    if len(text_to_save) > 4000:
        print(f"❌ دیتابیس اصلی خیلی بزرگ شده ({len(text_to_save)} کاراکتر) — "
              f"برای جلوگیری از خراب شدن داده، ذخیره انجام نشد. لازمه لیست‌ها کوچیک‌تر بشن.")
        return

    found_msg = None
    async for msg in client.iter_messages(DB_CHAT, limit=50):
        if msg.text and msg.text.startswith(DB_TAG):
            found_msg = msg; break
    try:
        if found_msg: await found_msg.edit(text_to_save, link_preview=False)
        else: await client.send_message(DB_CHAT, text_to_save, link_preview=False)
    except Exception as e: print(f"❌ خطا در ذخیره دیتابیس: {e}")

async def save_pio_db():
    data = {"active_group": pio_active_group, "links": {str(k): v for k, v in pio_target_links.items()}}
    json_str = json.dumps(data, ensure_ascii=False)
    text_to_save = f"{DB_PIOU_TAG} {json_str}"

    # FIX(F9 - همون گارد، برای یکدستی): این تابع اصلاً محافظتی در برابر رد
    # شدن از محدودیت طول پیام تلگرام نداشت.
    if len(text_to_save) > 4000:
        print(f"❌ دیتابیس پیو خیلی بزرگ شده ({len(text_to_save)} کاراکتر) — ذخیره انجام نشد.")
        return

    found_msg = None
    async for msg in client.iter_messages(DB_CHAT, limit=50):
        if msg.text and msg.text.startswith(DB_PIOU_TAG):
            found_msg = msg; break
    try:
        if found_msg: await found_msg.edit(text_to_save, link_preview=False)
        else: await client.send_message(DB_CHAT, text_to_save, link_preview=False)
    except Exception as e: print(f"❌ خطا در ذخیره دیتابیس پیو: {e}")
