from telethon import events, utils
import core
from core import client, save_db

@client.on(events.NewMessage(outgoing=True, pattern=r'^اد تگ(?:\s+(.+))?$'))
async def add_tag(event):
    arg = event.pattern_match.group(1)
    if event.message.is_reply and not arg:
        r = await event.get_reply_message()
        if r:
            uid = r.sender_id
            name = getattr(r.sender, 'first_name', None) or "ناشناس"
            core.tag_targets[uid] = name
            await save_db()
            return await event.reply(f"✅ `{name}` اضافه شد.")
    elif arg:
        p = arg.split()
        tgt, name = p[0], " ".join(p[1:]) if len(p) > 1 else p[0]
        try:
            uid = int(tgt) if tgt.lstrip('-').isdigit() else utils.get_peer_id(await client.get_entity(tgt))
            core.tag_targets[uid] = name
            await save_db()
            return await event.reply(f"✅ `{name}` اضافه شد.")
        except: return await event.reply("❌ پیدا نشد.")
    await event.reply("❗ فرمت اشتباه.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^حذف تگ(?:\s+(.+))?$'))
async def rem_tag(event):
    arg = event.pattern_match.group(1)
    val, is_name = None, False
    if event.message.is_reply and not arg:
        r = await event.get_reply_message()
        if r: val = r.sender_id
    elif arg:
        if arg.lstrip('-').isdigit(): val = int(arg)
        else: val, is_name = arg, True
    else: return await event.reply("❗ ریپلای یا اسم بده.")
    for uid, name in list(core.tag_targets.items()):
        if (is_name and name == val) or (not is_name and uid == val):
            del core.tag_targets[uid]
            await save_db()
            return await event.reply(f"❌ `{name}` حذف شد.")
    await event.reply("❗ پیدا نشد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^لیست تگ$'))
async def list_tag(event):
    if not core.tag_targets: return await event.reply("📋 خالی.")
    t = "📋 **تگ‌ها:**\n\n" + "\n".join([f"▫️ {n} (`{i}`)" for i, n in core.tag_targets.items()])
    await event.reply(t)

@client.on(events.NewMessage(outgoing=True, pattern=r'^تگ همه$'))
async def tag_all(event):
    if not core.tag_targets: return
    mt = "📢 **تگ همه:**\n\n" + " ".join([f'<a href="tg://user?id={i}">{n}</a> ' for i, n in core.tag_targets.items()])
    r_id = None
    if event.message.is_reply:
        r = await event.message.get_reply_message()
        if r: r_id = r.id
    await event.delete()
    await client.send_message(event.chat_id, mt, reply_to=r_id, parse_mode='html')

@client.on(events.NewMessage(outgoing=True, pattern=r'^تگ\s+(.+)$'))
async def tag_single(event):
    name = event.pattern_match.group(1).strip()
    uid = None
    for i, n in core.tag_targets.items():
        if n == name: uid = i; break
    if not uid: return await event.reply(f"❗ `{name}` نیست.")
    mt = f'<a href="tg://user?id={uid}">{name}</a>'
    r_id = None
    if event.message.is_reply:
        r = await event.message.get_reply_message()
        if r: r_id = r.id
    await event.delete()
    await client.send_message(event.chat_id, mt, reply_to=r_id, parse_mode='html')
