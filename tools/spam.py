import asyncio
from telethon import events
from telethon.errors import FloodWaitError
import core
from core import client, fa_to_en_digits

# --- اسپم ---
async def run_spam(model, count, text, chat_id, reply_to=None, delay=0.5):
    try:
        if model == 1:
            for _ in range(count):
                await client.send_message(chat_id, text, reply_to=reply_to)
                await asyncio.sleep(delay)
        elif model == 2:
            full_text = (text + " ") * count
            if len(full_text) > 4096: full_text = full_text[:4090] + "..."
            await client.send_message(chat_id, full_text, reply_to=reply_to)
    except Exception as e: print(f"❌ خطا اسپم: {e}")

@client.on(events.NewMessage(outgoing=True, pattern=r'^اسپم\s+(.+)$'))
async def spam_handler(event):
    args = event.pattern_match.group(1).split()
    if len(args) < 3: return
    model = int(fa_to_en_digits(args[0]))
    count = int(fa_to_en_digits(args[1]))
    text = " ".join(args[2:])
    delay = 0.5
    if len(args) >= 4:
        if fa_to_en_digits(args[2]).replace('.', '', 1).isdigit():
            delay = float(fa_to_en_digits(args[2]))
            text = " ".join(args[3:])
    reply_to_id = None
    if event.message.is_reply:
        r = await event.message.get_reply_message()
        if r: reply_to_id = r.id
    reply_msg = await event.reply("🚀 اسپم...")
    await event.delete()
    await reply_msg.delete()
    asyncio.create_task(run_spam(model, count, text, event.chat_id, reply_to_id, delay))

# --- پاکسازی پیشرفته ---
async def safe_clear(chat_id, limit, only_me=False):
    deleted = 0
    async for msg in client.iter_messages(chat_id, limit=limit, from_user='me' if only_me else None):
        try:
            await msg.delete(revoke=True)
            deleted += 1
            if deleted % 100 == 0: await asyncio.sleep(2)
            else: await asyncio.sleep(0.1)
        except FloodWaitError as e: await asyncio.sleep(e.seconds + 1)
        except: pass
    return deleted

@client.on(events.NewMessage(outgoing=True, pattern=r'^پاکسازی\s+([\d۰-۹]+)$'))
async def clear_me_handler(event):
    count = int(fa_to_en_digits(event.pattern_match.group(1)))
    await event.delete()
    d = await safe_clear(event.chat_id, count, only_me=True)
    c = await event.reply(f"🧹 {d} پیام شما پاک شد.")
    await asyncio.sleep(3)
    await c.delete()

@client.on(events.NewMessage(outgoing=True, pattern=r'^پاکسازی همه\s+([\d۰-۹]+)$'))
async def clear_all_handler(event):
    count = int(fa_to_en_digits(event.pattern_match.group(1)))
    await event.delete()
    d = await safe_clear(event.chat_id, count, only_me=False)
    c = await event.reply(f"🧹 {d} پیام (برای همه) پاک شد.")
    await asyncio.sleep(3)
    await c.delete()
