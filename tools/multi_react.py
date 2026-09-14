import asyncio
import random
import json
import os
from telethon import events, utils
from telethon.sessions import StringSession
from telethon.tl.functions.messages import SendReactionRequest
from telethon.tl.types import ReactionEmoji
import core

# لود کردن سشن‌های فرعی از فایل accounts.json
worker_sessions = []
if os.path.exists('accounts.json'):
    with open('accounts.json', 'r') as f:
        worker_sessions = json.load(f)

# ساخت کلاینت‌های فرعی (سنیورها)
worker_clients = [TelegramClient(StringSession(s), core.API_ID, core.API_HASH) for s in worker_sessions]
active_reactions = {}

def clean_target_string(target_str):
    if "t.me/" in target_str:
        parts = target_str.split("t.me/")[-1].split("/")
        if parts[0]: return parts[0]
    return target_str.replace("@", "")

@core.client.on(events.NewMessage(outgoing=True, pattern=r'^واکنش\s+([0-9۰-9]+|مختلف)\s+(\S+)\s+(.+)$'))
async def add_react(event):
    count_str = event.pattern_match.group(1)
    target_str = event.pattern_match.group(2)
    emojis_str = event.pattern_match.group(3)
    
    emojis = emojis_str.split()
    clean_target = clean_target_string(target_str)
    
    try:
        ent = await core.client.get_entity(clean_target)
        chat_id = utils.get_peer_id(ent)
        
        if count_str == "مختلف":
            count = "all"
        else:
            # تبدیل عدد فارسی به انگلیسی
            count = int(core.fa_to_en_digits(count_str))
            
        active_reactions[chat_id] = {"count": count, "emojis": emojis}
        await event.reply(f"✅ واکنش تنظیم شد.\nچنل: `{clean_target}`\nتعداد: {count_str}\nایموجی‌ها: {' '.join(emojis)}")
    except Exception as e:
        await event.reply(f"❗ ارور در پیدا کردن چنل: {e}")

@core.client.on(events.NewMessage(outgoing=True, pattern=r'^حذف واکنش\s+(\S+)$'))
async def rem_react(event):
    target_str = event.pattern_match.group(1).strip()
    clean_target = clean_target_string(target_str)
    try:
        ent = await core.client.get_entity(clean_target)
        chat_id = utils.get_peer_id(ent)
        if chat_id in active_reactions:
            del active_reactions[chat_id]
            await event.reply("❌ پاک شد.")
        else:
            await event.reply("❗ تو لیست نیست.")
    except:
        await event.reply("❗ پیدا نشد.")

@core.client.on(events.NewMessage())
async def auto_react_handler(event):
    chat_id = event.chat_id
    if chat_id in active_reactions:
        config = active_reactions[chat_id]
        count = config["count"]
        emojis = config["emojis"]
        
        # ۱. واکنش اکانت اصلی
        emoji = random.choice(emojis)
        try:
            await core.client(SendReactionRequest(peer=chat_id, msg_id=event.id, reaction=[ReactionEmoji(emoticon=emoji)]))
            print(f"✅ اکانت اصلی واکنش {emoji} گذاشت.")
        except Exception as e:
            err_msg = f"❌ خطا اکانت اصلی:\n{e}"
            print(err_msg)
            await core.client.send_message('me', err_msg) # میفرسته تو پیوی خودت ببینی چشه
        
        # ۲. واکنش سنیورها
        if count != 1:
            workers_to_use = worker_clients if count == "all" else worker_clients[:count-1]
            
            for i, w_client in enumerate(workers_to_use):
                await asyncio.sleep(random.randint(1, 3))
                try:
                    e = random.choice(emojis)
                    await w_client(SendReactionRequest(peer=chat_id, msg_id=event.id, reaction=[ReactionEmoji(emoticon=e)]))
                    print(f"✅ سنیور {i+1} واکنش {e} گذاشت.")
                except Exception as ex:
                    err_msg = f"❌ خطا سنیور {i+1}:\n{ex}"
                    print(err_msg)
                    await core.client.send_message('me', err_msg)

async def start_multi_clients():
    """این تابع رو main.py صدا میزنه"""
    for i, w_client in enumerate(worker_clients):
        try:
            await w_client.connect()
            if await w_client.is_user_authorized():
                print(f"✅ سنیور واکنش {i+1} وصل شد.")
            else:
                print(f"❌ سنیور واکنش {i+1} لاگین نیست!")
                await core.client.send_message('me', f"❌ سنیور واکنش {i+1} لاگین نیست!")
        except Exception as e:
            print(f"❌ خطا سنیور {i+1}: {e}")import asyncio
import random
import json
import os
from telethon import events, utils
from telethon.sessions import StringSession
from telethon.tl.functions.messages import SendReactionRequest
from telethon.tl.types import ReactionEmoji
import core

# لود کردن سشن‌های فرعی از فایل accounts.json
worker_sessions = []
if os.path.exists('accounts.json'):
    with open('accounts.json', 'r') as f:
        worker_sessions = json.load(f)

# ساخت کلاینت‌های فرعی (سنیورها)
worker_clients = [TelegramClient(StringSession(s), core.API_ID, core.API_HASH) for s in worker_sessions]
active_reactions = {}

def clean_target_string(target_str):
    if "t.me/" in target_str:
        parts = target_str.split("t.me/")[-1].split("/")
        if parts[0]: return parts[0]
    return target_str.replace("@", "")

@core.client.on(events.NewMessage(outgoing=True, pattern=r'^واکنش\s+([0-9۰-9]+|مختلف)\s+(\S+)\s+(.+)$'))
async def add_react(event):
    count_str = event.pattern_match.group(1)
    target_str = event.pattern_match.group(2)
    emojis_str = event.pattern_match.group(3)
    
    emojis = emojis_str.split()
    clean_target = clean_target_string(target_str)
    
    try:
        ent = await core.client.get_entity(clean_target)
        chat_id = utils.get_peer_id(ent)
        
        if count_str == "مختلف":
            count = "all"
        else:
            # تبدیل عدد فارسی به انگلیسی
            count = int(core.fa_to_en_digits(count_str))
            
        active_reactions[chat_id] = {"count": count, "emojis": emojis}
        await event.reply(f"✅ واکنش تنظیم شد.\nچنل: `{clean_target}`\nتعداد: {count_str}\nایموجی‌ها: {' '.join(emojis)}")
    except Exception as e:
        await event.reply(f"❗ ارور در پیدا کردن چنل: {e}")

@core.client.on(events.NewMessage(outgoing=True, pattern=r'^حذف واکنش\s+(\S+)$'))
async def rem_react(event):
    target_str = event.pattern_match.group(1).strip()
    clean_target = clean_target_string(target_str)
    try:
        ent = await core.client.get_entity(clean_target)
        chat_id = utils.get_peer_id(ent)
        if chat_id in active_reactions:
            del active_reactions[chat_id]
            await event.reply("❌ پاک شد.")
        else:
            await event.reply("❗ تو لیست نیست.")
    except:
        await event.reply("❗ پیدا نشد.")

@core.client.on(events.NewMessage())
async def auto_react_handler(event):
    chat_id = event.chat_id
    if chat_id in active_reactions:
        config = active_reactions[chat_id]
        count = config["count"]
        emojis = config["emojis"]
        
        # ۱. واکنش اکانت اصلی
        emoji = random.choice(emojis)
        try:
            await core.client(SendReactionRequest(peer=chat_id, msg_id=event.id, reaction=[ReactionEmoji(emoticon=emoji)]))
            print(f"✅ اکانت اصلی واکنش {emoji} گذاشت.")
        except Exception as e:
            err_msg = f"❌ خطا اکانت اصلی:\n{e}"
            print(err_msg)
            await core.client.send_message('me', err_msg) # میفرسته تو پیوی خودت ببینی چشه
        
        # ۲. واکنش سنیورها
        if count != 1:
            workers_to_use = worker_clients if count == "all" else worker_clients[:count-1]
            
            for i, w_client in enumerate(workers_to_use):
                await asyncio.sleep(random.randint(1, 3))
                try:
                    e = random.choice(emojis)
                    await w_client(SendReactionRequest(peer=chat_id, msg_id=event.id, reaction=[ReactionEmoji(emoticon=e)]))
                    print(f"✅ سنیور {i+1} واکنش {e} گذاشت.")
                except Exception as ex:
                    err_msg = f"❌ خطا سنیور {i+1}:\n{ex}"
                    print(err_msg)
                    await core.client.send_message('me', err_msg)

async def start_multi_clients():
    """این تابع رو main.py صدا میزنه"""
    for i, w_client in enumerate(worker_clients):
        try:
            await w_client.connect()
            if await w_client.is_user_authorized():
                print(f"✅ سنیور واکنش {i+1} وصل شد.")
            else:
                print(f"❌ سنیور واکنش {i+1} لاگین نیست!")
                await core.client.send_message('me', f"❌ سنیور واکنش {i+1} لاگین نیست!")
        except Exception as e:
            print(f"❌ خطا سنیور {i+1}: {e}")
