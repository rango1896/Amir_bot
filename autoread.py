import asyncio
from telethon import events, utils
import core
from core import client

# --- شنود پیام‌های ورودی برای سین خودکار ---
@client.on(events.NewMessage(incoming=True))
async def autoread_listener(event):
    # اگه گپ تو لیست سین خودکار باشه، پیام رو سین کن
    if event.chat_id in core.autoread_chats:
        try:
            await event.message.mark_read()
        except:
            pass

# --- دستور فعال کردن سین ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^سین\s+(\S+)$'))
async def add_autoread(event):
    link = event.pattern_match.group(1)
    try:
        entity = await client.get_entity(link)
        if entity.id not in core.autoread_chats:
            core.autoread_chats.add(entity.id)
            await event.reply(f"✅ سین خودکار برای `{entity.title}` فعال شد.")
    except Exception as e:
        await event.reply(f"❌ خطا: {e}")

# --- دستور غیرفعال کردن سین ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^حذف سین\s+(\S+)$'))
async def remove_autoread(event):
    link = event.pattern_match.group(1)
    try:
        entity = await client.get_entity(link)
        if entity.id in core.autoread_chats:
            core.autoread_chats.discard(entity.id)
            await event.reply(f"🛑 سین خودکار برای `{entity.title}` غیرفعال شد.")
    except Exception as e:
        await event.reply(f"❌ خطا: {e}")
