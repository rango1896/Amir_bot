from telethon import events, utils
from telethon.tl.functions.messages import SendReactionRequest
from telethon.tl.types import ReactionEmoji
import core
from core import client, save_db

def extract_username_from_url(text):
    if "t.me/" in text:
        parts = text.split("t.me/")[-1].split("/")
        return parts[0] if parts[0] else text
    return text

@client.on(events.NewMessage(outgoing=True, pattern=r'^واکنش\s+(.+)\s+(\S+)$'))
async def add_react(event):
    target_str = event.pattern_match.group(1).strip()
    emoji = event.pattern_match.group(2).strip()
    if target_str in ["لیست", "حذف"]: return
    try:
        if target_str.lstrip('-').isdigit():
            pid = int(target_str)
            ent = await client.get_entity(pid)
            pid = utils.get_peer_id(ent)
        else:
            clean_target = extract_username_from_url(target_str)
            ent = await client.get_entity(clean_target)
            pid = utils.get_peer_id(ent)
            
        core.auto_react_targets[pid] = emoji
        await save_db()
        await event.reply(f"✅ واکنش {emoji} برای `{target_str}` تنظیم شد.")
    except Exception as e:
        print(f"خطا در تنظیم واکنش: {e}")
        await event.reply("❗ کاربر/کانال پیدا نشد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^حذف واکنش\s+(.+)$'))
async def rem_react(event):
    target_str = event.pattern_match.group(1).strip()
    try:
        if target_str.lstrip('-').isdigit():
            pid = int(target_str)
            ent = await client.get_entity(pid)
            pid = utils.get_peer_id(ent)
        else:
            clean_target = extract_username_from_url(target_str)
            ent = await client.get_entity(clean_target)
            pid = utils.get_peer_id(ent)

        if pid in core.auto_react_targets:
            del core.auto_react_targets[pid]
            await save_db()
            await event.reply(f"❌ واکنش برای `{target_str}` حذف شد.")
        else: await event.reply("❗ در لیست نیست.")
    except: await event.reply("❗ پیدا نشد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^(لیست واکنش|واکنش لیست)$'))
async def list_react(event):
    if not core.auto_react_targets: return await event.reply("📋 لیست خالی است.")
    t = "📋 **لیست واکنش‌ها:**\n\n" + "\n".join([f"▫️ `{i}`: {n}" for i, n in core.auto_react_targets.items()])
    await event.reply(t)

@client.on(events.NewMessage())
async def auto_react_handler(event):
    if core.auto_react_targets and event.chat_id in core.auto_react_targets:
        try:
            emoji_str = core.auto_react_targets[event.chat_id]
            reaction = ReactionEmoji(emoticon=emoji_str)
            await client(SendReactionRequest(peer=event.chat_id, msg_id=event.id, reaction=[reaction]))
        except Exception as e:
            print(f"خطا در واکنش خودکار: {e}")
