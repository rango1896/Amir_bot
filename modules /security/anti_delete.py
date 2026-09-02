import asyncio
from datetime import datetime
from telethon import events, utils
import core
from core import client, save_db, TEHRAN_TZ

@client.on(events.NewMessage(outgoing=True, pattern=r'^ضد حذف (روشن|خاموش)$'))
async def anti_del_toggle(event):
    core.anti_delete_active = True if event.pattern_match.group(1) == "روشن" else False
    await event.reply(f"✅ ضد حذف **{event.pattern_match.group(1)}** شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^اد حذف(?:\s+(.+))?$'))
async def add_anti_del(event):
    t_str = []
    arg = event.pattern_match.group(1)
    if event.message.is_reply and not arg:
        r = await event.get_reply_message()
        if r: t_str.append(str(r.sender_id))
    elif arg: t_str.extend(arg.split())
    else: return await event.reply("❗ ریپلای یا آیدی بده.")
    added = []
    for t in t_str:
        try:
            pid = int(t) if t.lstrip('-').isdigit() else utils.get_peer_id(await client.get_entity(t))
            name = t
            try:
                ent = await client.get_entity(pid)
                name = getattr(ent, 'first_name', None) or getattr(ent, 'title', None) or t
            except: pass
            core.anti_delete_targets[pid] = name
            added.append(f"{name} (`{pid}`)")
        except: await event.reply(f"❌ `{t}` پیدا نشد.")
    if added:
        await save_db()
        await event.reply("✅ اضافه شدند:\n" + "\n".join(added))

@client.on(events.NewMessage(outgoing=True, pattern=r'^حذف اد(?:\s+(.+))?$'))
async def rem_anti_del(event):
    t_str = []
    arg = event.pattern_match.group(1)
    if event.message.is_reply and not arg:
        r = await event.get_reply_message()
        if r: t_str.append(str(r.sender_id))
    elif arg: t_str.append(arg)
    else: return await event.reply("❗ ریپلای یا آیدی بده.")
    rem = []
    for t in t_str:
        try:
            pid = int(t) if t.lstrip('-').isdigit() else utils.get_peer_id(await client.get_entity(t))
            if pid in core.anti_delete_targets:
                rem.append(core.anti_delete_targets[pid])
                del core.anti_delete_targets[pid]
        except: pass
    if rem:
        await save_db()
        await event.reply("❌ حذف شدند:\n" + ", ".join(rem))

@client.on(events.NewMessage(outgoing=True, pattern=r'^لیست اد حذف$'))
async def list_anti_del(event):
    if not core.anti_delete_targets: return await event.reply("📋 خالی.")
    t = "📋 **ضد حذف:**\n\n" + "\n".join([f"▫️ {n} (`{i}`)" for i, n in core.anti_delete_targets.items()])
    await event.reply(t)

@client.on(events.NewMessage())
async def anti_del_cacher(event):
    if not core.anti_delete_active: return
    c_id, s_id = event.chat_id, event.sender_id
    if c_id in core.anti_delete_targets or s_id in core.anti_delete_targets:
        if c_id not in core.message_cache: core.message_cache[c_id] = {}
        core.message_cache[c_id][event.id] = event.message
        if len(core.message_cache[c_id]) > 100:
            del core.message_cache[c_id][next(iter(core.message_cache[c_id]))]

@client.on(events.MessageDeleted)
async def anti_del_handler(event):
    if not core.anti_delete_active: return
    for m_id in event.deleted_ids:
        for c_id, msgs in core.message_cache.items():
            if m_id in msgs:
                msg = msgs[m_id]
                try:
                    s = await msg.get_sender()
                    c = await msg.get_chat()
                    s_name = getattr(s, 'first_name', None) or "ناشناس"
                    c_name = getattr(c, 'title', None) or "پیوی"
                    st = msg.date.astimezone(TEHRAN_TZ).strftime("%H:%M:%S")
                    dt = datetime.now(TEHRAN_TZ).strftime("%H:%M:%S")
                    rep = f"🗑 **حذف شد**\n\n👤 {s_name} (`{s.id}`)\n💬 {c_name}\n⏱ {st} -> {dt}\n\n📝 {msg.text or '[مدیا]'}"
                    if msg.media:
                        try:
                            sm = await client.send_file('me', msg.media)
                            await sm.reply(rep)
                        except: await client.send_message('me', rep)
                    else: await client.send_message('me', rep)
                except: pass
                del msgs[m_id]
                break
