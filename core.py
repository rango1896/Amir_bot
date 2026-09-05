import json
from telethon import TelegramClient

API_ID = 17349
API_HASH = "344583e45741c457fe1862106095a5eb"
TARGET_GROUP = -1004408912158  # گروه پیش‌فرض (دیگه بهش وابسته نیستیم)

client = TelegramClient('sessions/friend2_session', API_ID, API_HASH)

# === دیتابیس تلگرامی برای تنظیمات پیو ===
DB_TAG = "#DB_PIOU"
pio_active_group = None  # گروه فعلی (در ابتدا خالیه)
pio_target_links = {}     # لیست لینک‌ها

async def load_db():
    global pio_active_group, pio_target_links
    async for msg in client.iter_messages('me', limit=50):
        if msg.text and msg.text.startswith(DB_TAG):
            try:
                json_str = msg.text.replace(DB_TAG, "").strip()
                if json_str:
                    data = json.loads(json_str)
                    pio_active_group = data.get("active_group", None)
                    pio_target_links = {int(k): v for k, v in data.get("links", {}).items()}
                    print("✅ تنظیمات پیو از دیتابیس بارگذاری شد.")
            except Exception as e:
                print(f"❌ خطا در خواندن دیتابیس: {e}")
            return

async def save_db():
    data = {
        "active_group": pio_active_group,
        "links": {str(k): v for k, v in pio_target_links.items()}
    }
    json_str = json.dumps(data, ensure_ascii=False)
    text_to_save = f"{DB_TAG} {json_str}"
    
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
