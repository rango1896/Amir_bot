from telethon import events
import core
from core import client

@client.on(events.NewMessage(outgoing=True, pattern=r'^اطلاعات(?:\s+(.+))?$'))
async def user_info(event):
    tgt = event.pattern_match.group(1)
    ent = None
    if event.message.is_reply and not tgt:
        r = await event.get_reply_message()
        if r: ent = await r.get_sender()
    elif tgt:
        try: ent = await client.get_entity(int(tgt) if tgt.lstrip('-').isdigit() else tgt)
        except: return await event.reply("❗ پیدا نشد.")
    else: return await event.reply("❗ ریپلای یا آیدی بده.")
    name = getattr(ent, 'first_name', None) or "ناشناس"
    uid = ent.id
    user = f"@{ent.username}" if hasattr(ent, 'username') and ent.username else "ندارد"
    ph = f"+{ent.phone}" if getattr(ent, 'phone', None) else "مخفی"
    await event.reply(f"👤 **اطلاعات**\n\n📛 {name}\n🆔 `{uid}`\n🔖 {user}\n📱 {ph}")
