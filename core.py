import asyncio
import re
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from telethon import TelegramClient, events, utils
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateProfileRequest

API_ID = 17349
API_HASH = "344583e45741c457fe1862106095a5eb"
TARGET_GROUP = -1004290700072
group_entity = None

MASTER_SESSION = "1BJWap1wBu1g94eIpgp67vezMPa8_27YNHWUg9ByBgLlNukX0Y-xTG3MXE3DK7-oX1KqsJLeY2n9QvsSVTJCBWHxYduBvumJFUx6DZPRU9WJPXsRDAnRAZe9jPdhkB74NC6Wigp-LpHuBzE2mntLE2EdcFcYvNQt9F3vxsZxLP_J0JFXWqlX_vnBUoGL6VR5Ee3ZyHWLb3-qYPo5ByAWtnoYeISTPAHlCaDpeTHRNQje2iLk2e0nLGmgd_aUXN5qt75oFP6u9A8NpM4peghCpwcwXFtbdHR59WTCDQpedWJ7ms8MIf1-btlKqFtEq6FvCeDNAJRGy4cbfnD6pwDSzNIPkGuIiWKM="
client = TelegramClient(StringSession(MASTER_SESSION), API_ID, API_HASH)

collect_points_active = False
fishing_active = False
stray_cat_active = True
factory_active = False

DB_TAG = "#DB_AMIR"
DB_CHAT = "hankhhh"
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
multi_active_reactions = {}
downloader_whitelist = set()
ring_active_status = False
enemy_active = False
enemy_targets = {}
enemy_active_chat = None
dungeon_active = False
NOTES_PASSWORD = "amir1370"
TEHRAN_TZ = ZoneInfo("Asia/Tehran")

# === تغییرات دیتابیس پیو ===
DB_PIOU_TAG = "#DB_PIOU"
pio_active_group = None
pio_target_links = []        # تغییر از دیکشنری به لیست (دفترچه)
pio_active_link_index = 0    # اضافه شد: شماره لینک فعلی (ناصر=0، علی=1، اصغر=2)
next_shoot_time = 0

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

async def load_db():
    global anti_delete_targets, tag_targets, notes_list, keywords_list, auto_react_targets
    global pio_active_group, pio_target_links, pio_active_link_index, multi_active_reactions, downloader_whitelist, ring_active_status, enemy_active, enemy_targets, enemy_active_chat, dungeon_active
    
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
                    multi_active_reactions = {int(k): v for k, v in data.get("multi_reactions", {}).items()}
                    downloader_whitelist = set(data.get("downloader_whitelist", []))
                    ring_active_status = data.get("ring_active", False)
                    enemy_active = data.get("enemy_active", False)
                    enemy_targets = data.get("enemy_targets", {})
                    enemy_active_chat = data.get("enemy_active_chat", None)
                    dungeon_active = data.get("dungeon_active", False)
                    print("✅ دیتابیس ربات از گروه بارگذاری شد.")
            except Exception as e:
                print(f"❌ خطا در خواندن دیتابیس: {e}")
            break

    async for msg in client.iter_messages(DB_CHAT, limit=50):
        if msg.text and msg.text.startswith(DB_PIOU_TAG):
            try:
                json_str = msg.text.replace(DB_PIOU_TAG, "").strip()
                if json_str:
                    data = json.loads(json_str)
                    pio_active_group = data.get("active_group", None)
                    pio_target_links = data.get("links", [])  # خواندن لیست لینک‌ها
                    pio_active_link_index = data.get("active_link_index", 0)  # خواندن شماره لینک فعلی
                    print("✅ تنظیمات پیو از گروه بارگذاری شد.")
            except Exception as e:
                print(f"❌ خطا در خواندن دیتابیس پیو: {e}")
            break

async def save_db():
    data = {
        "anti_delete": {str(k): v for k, v in anti_delete_targets.items()},
        "tags": {str(k): v for k, v in tag_targets.items()},
        "notes": notes_list,
        "keywords": list(keywords_list),
        "reactions": {str(k): v for k, v in auto_react_targets.items()},
        "multi_reactions": {str(k): v for k, v in multi_active_reactions.items()},
        "downloader_whitelist": list(downloader_whitelist),
        "ring_active": ring_active_status,
        "enemy_active": enemy_active,
        "enemy_targets": enemy_targets,
        "enemy_active_chat": enemy_active_chat,
        "dungeon_active": dungeon_active
    }
    json_str = json.dumps(data, ensure_ascii=False)
    text_to_save = f"{DB_TAG} {json_str}"
    
    if len(text_to_save) > 4000: text_to_save = text_to_save[:4000]
    found_msg = None
    async for msg in client.iter_messages(DB_CHAT, limit=50):
        if msg.text and msg.text.startswith(DB_TAG):
            found_msg = msg; break
    try:
        if found_msg: await found_msg.edit(text_to_save, link_preview=False)
        else: await client.send_message(DB_CHAT, text_to_save, link_preview=False)
    except Exception as e: print(f"❌ خطا در ذخیره دیتابیس: {e}")

async def save_pio_db():
    data = {
        "active_group": pio_active_group,
        "links": pio_target_links,               # ذخیره لیست لینک‌ها
        "active_link_index": pio_active_link_index  # ذخیره شماره لینک فعلی
    }
    json_str = json.dumps(data, ensure_ascii=False)
    text_to_save = f"{DB_PIOU_TAG} {json_str}"
    found_msg = None
    async for msg in client.iter_messages(DB_CHAT, limit=50):
        if msg.text and msg.text.startswith(DB_PIOU_TAG):
            found_msg = msg; break
    try:
        if found_msg: await found_msg.edit(text_to_save, link_preview=False)
        else: await client.send_message(DB_CHAT, text_to_save, link_preview=False)
    except Exception as e: print(f"❌ خطا در ذخیره دیتابیس پیو: {e}")
