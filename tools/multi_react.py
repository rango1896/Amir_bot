import asyncio
import random
import json
import os
from telethon import TelegramClient, events, utils
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

def clean_target_string(target_str):
    if "t.me/" in target_str:
        parts = target_str.split("t.me/")[-1].split("/")
        if parts[0]: return parts[0]
    return target_str.replace("@", "")

@core.client.on(events.NewMessage(outgoing=True, pattern=r'^واکنش\s+([0-9۰-۹]+|مختلف)\s+(\S+)\s+(.+)$'))
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
            count = int(core.fa_to_en_digits(count_str))
            
        # ذخیره در دیتابیس تلگرامی
        core.multi_active_reactions[chat_id] = {"count": count, "emojis": emojis, "target_str": clean_target}
        await core.save_db()  # <--- سیو کردن تو دیتابیس تلگرام
        
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
        if chat_id in core.multi_active_reactions:
            del core.multi_active_reactions[chat_id]
            await core.save_db()  # <--- سیو کردن تغییرات تو دیتابیس تلگرام
            await event.reply("❌ پاک شد.")
        else:
            await event.reply("❗ تو لیست نیست.")
    except:
        await event.reply("❗ پیدا نشد.")

@core.client.on(events.NewMessage(outgoing=True, pattern=r'^لیست واکنش$'))
async def list_reactions(event):
    if not core.multi_active_reactions:
        return await event.reply("📭 لیست واکنش‌ها خالیه.")
        
    text = "❤️ **لیست واکنش‌های فعال:**\n\n"
    for chat_id, config in core.multi_active_reactions.items():
        target_str = config.get("target_str", "نامشخص")
        count = config.get("count", 0)
        emojis = " ".join(config.get("emojis", []))
        
        text += f"💬 `{target_str}` (آیدی: `{chat_id}`)\n"
        text += f"└─ تعداد: {count}\n"
        text += f"└─ ایموجی‌ها: {emojis}\n\n"
        
    await event.reply(text)

@core.client.on(events.NewMessage())
async def auto_react_handler(event):
    chat_id = event.chat_id
    if chat_id in core.multi_active_reactions:
        config = core.multi_active_reactions[chat_id]
        count = config["count"]
        emojis = config["emojis"]
        target_str = config.get("target_str")
        
        # گرفتن آدرس چت (input_peer) به صورت امن برای جلوگیری از ارور NoneType
        input_peer = await event.get_input_chat()
        if not input_peer:
            return # اگه چت پیدا نشد، از واکنش می‌گذریم تا ارور نده
        
        # ۱. واکنش اکانت اصلی
        emoji = random.choice(emojis)
        try:
            await core.client(SendReactionRequest(peer=input_peer, msg_id=event.id, reaction=[ReactionEmoji(emoticon=emoji)]))
            print(f"✅ اکانت اصلی واکنش {emoji} گذاشت.")
        except Exception as e:
            err_msg = f"❌ خطا اکانت اصلی:\n{e}"
            print(err_msg)
            await core.client.send_message('me', err_msg)
        
        # ۲. واکنش سنیورها
        if count != 1:
            workers_to_use = worker_clients if count == "all" else worker_clients[:count-1]
            
            for i, w_client in enumerate(workers_to_use):
                await asyncio.sleep(random.randint(1, 3))
                try:
                    w_entity = await w_client.get_entity(target_str)
                    w_input_peer = utils.get_input_peer(w_entity)
                    e = random.choice(emojis)
                    await w_client(SendReactionRequest(peer=w_input_peer, msg_id=event.id, reaction=[ReactionEmoji(emoticon=e)]))
                    print(f"✅ سنیور {i+1} واکنش {e} گذاشت.")
                except Exception as ex:
                    err_msg = f"❌ خطا سنیور {i+1}:\n{ex}"
                    print(err_msg)
                    await core.client.send_message('me', err_msg)

async def start_multi_clients():
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
