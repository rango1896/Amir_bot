import asyncio
import re
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from telethon import TelegramClient, events, utils
from telethon.tl.functions.account import UpdateProfileRequest
from deep_translator import GoogleTranslator

API_ID = 17349
API_HASH = "344583e45741c457fe1862106095a5eb"
TARGET_GROUP = -1004290700072
group_entity = None

client = TelegramClient('sessions/amir_session', API_ID, API_HASH)

# === متغیرهای مشترک ===
collect_points_active = False
fishing_active = False
stray_cat_active = True
factory_active = False

DB_TAG = "#DB_AMIR"
anti_delete_active = False
anti_delete_targets = {}
message_cache = {}
scheduled_messages = []
keyword_alert_active = False
keywords_list = set()
ghost_mode_active = False
tag_targets = {}
notes_list = []
auto_react_targets = {} # متغیر جدید برای واکنش خودکار
NOTES_PASSWORD = "amir1370"
TEHRAN_TZ = ZoneInfo("Asia/Tehran")

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
    global anti_delete_targets, tag_targets, notes_list, keywords_list
    async for msg in client.iter_messages('me', limit=50):
        if msg.text and msg.text.startswith(DB_TAG):
            try:
                json_str = msg.text.replace(DB_TAG, "").strip()
                if json_str:
                    data = json.loads(json_str)
                    anti_delete_targets = {int(k): v for k, v in data.get("anti_delete", {}).items()}
                    tag_targets = {int(k): v for k, v in data.get("tags", {}).items()}
                    notes_list = data.get("notes", [])
                    keywords_list = set(data.get("keywords", []))
                    print("✅ دیتابیس از تلگرام بارگذاری شد.")
            except Exception as e:
                print(f"❌ خطا در خواندن دیتابیس: {e}")
            return

async def save_db():
    data = {
        "anti_delete": {str(k): v for k, v in anti_delete_targets.items()},
        "tags": {str(k): v for k, v in tag_targets.items()},
        "notes": notes_list,
        "keywords": list(keywords_list)
    }
    json_str = json.dumps(data, ensure_ascii=False)
    text_to_save = f"{DB_TAG} {json_str}"
    
    if len(text_to_save) > 4000:
        text_to_save = text_to_save[:4000]
    
    found_msg = None
    async for msg in client.iter_messages('me', limit=50):
        if msg.text and msg.text.startswith(DB_TAG):
            found_msg = msg
            break
            
    try:
        if found_msg:
            await found_msg.edit(text_to_save, link_preview=False)
        else:
            await client.send_message('me', text_to_save, link_preview=False)
    except Exception as e:
        print(f"❌ خطا در ذخیره دیتابیس: {e}")
