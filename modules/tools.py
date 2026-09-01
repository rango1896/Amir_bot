import asyncio
import re
import os
import urllib.request
from datetime import datetime
from telethon import events, utils
from deep_translator import GoogleTranslator
import core
from core import client, fa_to_en_digits, save_db, TEHRAN_TZ

# --- ویس به متن ---
try:
    from vosk import Model, KaldiRecognizer
    import soundfile as sf
    import wave
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False

# --- هلپ ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^هلپ$'))
async def help_handler(event):
    help_text = (
        "📖 **راهنمای جامع سلف‌بات** 🤖\n\n"
        "🛠 **ابزارها:**\n"
        "🔹 `ترجمه کن` (ریپلای)\n"
        "🔹 `اسپم 1 10 5 سلام` (مدل/تعداد/تاخیر/متن)\n"
        "🔹 `پاکسازی 50`\n"
        "🔹 `یادداشت [متن]` / `یادداشت بخوان amir1370`\n"
        "🔹 `متن` (ریپلای روی ویس)\n\n"
        "🕵️ **مانیتورینگ:**\n"
        "🔹 `ضد حذف روشن/خاموش` / `اد حذف [آیدی/ریپلای]` / `حذف اد`\n"
        "🔹 `هشدار [کلمه]` / `هشدار خاموش`\n"
        "🔹 `شبح روشن/خاموش`\n\n"
        "📌 **تگ:**\n"
        "🔹 `اد تگ [آیدی] [اسم]` / `تگ همه` / `تگ [اسم]`\n\n"
        "ℹ️ **اطلاعات و زمان:**\n"
        "🔹 `اطلاعات` (ریپلای)\n"
        "🔹 `زمان 14:30 سلام`\n\n"
        "🎮 **بازی:** `پوینت/ماهی/کارخونه میویی روشن/خاموش`"
    )
    await event.reply(help_text)

# --- ترجمه ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^ترجمه کن$'))
async def translate_reply(event):
    if not event.message.is_reply: return
    replied_msg = await event.message.get_reply_message()
    if not replied_msg or not replied_msg.text: return
    try:
        translated = GoogleTranslator(source='auto', target='fa').translate(replied_msg.text)
        await event.reply(f"🔸 ترجمه:\n{translated}")
    except Exception as e:
        await event.reply(f"❌ خطا: {e}")

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

# --- پاکسازی ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^پاکسازی ([\d۰-۹]+)$'))
async def clear_handler(event):
    count = int(fa_to_en_digits(event.pattern_match.group(1)))
    await event.delete()
    deleted = 0
    async for msg in client.iter_messages(event.chat_id, from_user='me', limit=count):
        try:
            await msg.delete(revoke=True)
            deleted += 1
            await asyncio.sleep(0.1)
        except: pass
    c = await event.reply(f"🧹 {deleted} پاک شد.")
    await asyncio.sleep(3)
    await c.delete()

# --- یادداشت ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^یادداشت\s+(.+)$'))
async def add_note(event):
    txt = event.pattern_match.group(1)
    if txt.startswith("بخوان") or txt.startswith("پاک"): return
    core.notes_list.append(txt)
    await save_db()
    await event.reply("📝 ذخیره شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^یادداشت بخوان\s+(\S+)$'))
async def read_notes(event):
    if event.pattern_match.group(1) == core.NOTES_PASSWORD:
        if not core.notes_list: return await event.reply("لیست خالیه.")
        text = "📋 **یادداشت‌ها:**\n\n" + "\n".join([f"{i+1}. {n}" for i, n in enumerate(core.notes_list)])
        await event.reply(text)
    else: await event.reply("❌ رمز اشتباه.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^یادداشت پاک\s+(\S+)$'))
async def del_notes(event):
    if event.pattern_match.group(1) == core.NOTES_PASSWORD:
        core.notes_list.clear()
        await save_db()
        await event.reply("🧹 پاک شدند.")
    else: await event.reply("❌ رمز اشتباه.")

# --- ویس به متن ---
async def setup_vosk():
    if not VOSK_AVAILABLE: return None
    if core.vosk_model: return core.vosk_model
    model_path = "vosk-model-small-fa-0.4"
    if not os.path.exists(model_path):
        await client.send_message('me', "⏳ دانلود مدل فارسی...")
        try:
            urllib.request.urlretrieve("https://alphacephei.com/vosk/models/vosk-model-small-fa-0.4.zip", "model.zip")
            import zipfile
            with zipfile.ZipFile("model.zip", 'r') as z: z.extractall(".")
            os.remove("model.zip")
        except Exception as e: return None
    core.vosk_model = Model(model_path)
    return core.vosk_model

@client.on(events.NewMessage(outgoing=True, pattern=r'^متن$'))
async def voice_to_text(event):
    if not event.message.is_reply: return
    r = await event.get_reply_message()
    if not r or not r.voice: return await event.reply("❗ ویس نیست.")
    w = await event.reply("⏳ پردازش...")
    try:
        m = await setup_vosk()
        if not m: return await w.edit("❌ مدل لود نشد.")
        v_path = await r.download_media()
        wav_path = v_path.replace(".ogg", ".wav")
        data, sr = sf.read(v_path)
        sf.write(wav_path, data, sr)
        wf = wave.open(wav_path, "rb")
        rec = KaldiRecognizer(m, wf.getframerate())
        txt = ""
        while True:
            data = wf.readframes(4000)
            if len(data) == 0: break
            if rec.AcceptWaveform(data):
                txt += json.loads(rec.Result()).get("text", "")
        txt += json.loads(rec.FinalResult()).get("text", "")
        wf.close()
        os.remove(v_path); os.remove(wav_path)
        await w.edit(f"🎙 **متن:**\n\n{txt}" if txt.strip() else "❌ نامفهوم.")
    except Exception as e: await w.edit(f"❌ خطا: {e}")

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

# --- ضد حذف ---
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
                    s_user = f"@{s.username}" if s.username else "ندارد"
                    c_name = getattr(c, 'title', None) or "پیوی"
                    c_user = f"@{c.username}" if hasattr(c, 'username') and c.username else "ندارد"
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

# --- زمان‌بندی ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^زمان (.+)$'))
async def sched_msg(event):
    p = event.pattern_match.group(1).split()
    tgt, tm, txt = None, None, None
    if len(p) >= 3 and re.match(r'^\d{1,2}:\d{2}$', p[1]): tgt, tm, txt = p[0], p[1], " ".join(p[2:])
    elif len(p) >= 2 and re.match(r'^\d{1,2}:\d{2}$', p[0]): tm, txt = p[0], " ".join(p[1:])
    if not tm or not txt: return await event.reply("❗ فرمت اشتباه.")
    c_id = event.chat_id
    if tgt:
        try: c_id = utils.get_peer_id(await client.get_entity(tgt))
        except: return await event.reply("❗ آیدی پیدا نشد.")
    core.scheduled_messages.append({'chat_id': c_id, 'time': tm, 'text': txt})
    await event.reply(f"⏰ پیام برای `{tm}` ثبت شد.")

async def schedule_loop():
    while True:
        now = datetime.now(TEHRAN_TZ).strftime("%H:%M")
        for job in core.scheduled_messages[:]:
            if job['time'] == now:
                try:
                    await client.send_message(job['chat_id'], job['text'])
                    core.scheduled_messages.remove(job)
                except: pass
        await asyncio.sleep(20)

# --- تگ ---
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

# --- اطلاعات کاربر ---
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
