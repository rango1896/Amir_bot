from telethon import events
import core
from core import client, save_db

# --- هشدار کلمات ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^هشدار\s+(.+)$'))
async def add_alert(event):
    kw = event.pattern_match.group(1).strip()
    if kw == "خاموش":
        core.keyword_alert_active = False
        return await event.reply("🛑 هشدار خاموش شد.")
    core.keywords_list.add(kw)
    core.keyword_alert_active = True
    await save_db()
    await event.reply(f"✅ کلمه `{kw}` اضافه شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^حذف هشدار\s+(.+)$'))
async def remove_alert(event):
    kw = event.pattern_match.group(1).strip()
    if kw in core.keywords_list:
        core.keywords_list.remove(kw)
        await save_db()
        await event.reply(f"✅ کلمه `{kw}` از لیست حذف شد.")
    else: await event.reply("❗ در لیست نیست.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^لیست هشدار$'))
async def list_alert(event):
    if not core.keywords_list: return await event.reply("خالی.")
    t = "📋 **هشدارها:**\n\n" + "\n".join([f"▫️ `{k}`" for k in core.keywords_list])
    await event.reply(t)

@client.on(events.NewMessage())
async def alert_handler(event):
    if not core.keyword_alert_active or not core.keywords_list: return
    txt = event.message.text or ""
    if not txt: return
    for kw in core.keywords_list:
        if kw in txt:
            try:
                s = await event.get_sender()
                c = await event.get_chat()
                s_name = getattr(s, 'first_name', None) or "ناشناس"
                c_name = getattr(c, 'title', None) or "پیوی"
                link = "ندارد"
                if event.chat_id < 0:
                    cid = str(event.chat_id)
                    iid = cid[4:] if cid.startswith("-100") else cid[1:]
                    link = f"https://t.me/c/{iid}/{event.id}"
                elif hasattr(c, 'username') and c.username:
                    link = f"https://t.me/{c.username}/{event.id}"
                await client.send_message('me', f"🚨 **هشدار: `{kw}`**\n👤 {s_name}\n💬 {c_name}\n🔗 {link}\n\n📝 {txt}", link_preview=False)
            except: pass
            break

# --- حالت شبح ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^شبح (روشن|خاموش)$'))
async def ghost(event):
    core.ghost_mode_active = True if event.pattern_match.group(1) == "روشن" else False
    await event.reply(f"👻 شبح **{event.pattern_match.group(1)}** شد.")
