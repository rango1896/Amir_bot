import asyncio
import re
import os
import urllib.request
from datetime import datetime
from telethon import events, utils
from telethon.errors import FloodWaitError
from deep_translator import GoogleTranslator
import core
from core import client, fa_to_en_digits, save_db, TEHRAN_TZ

# --- متغیرهای این فایل ---
try:
    from vosk import Model, KaldiRecognizer
    import soundfile as sf
    import wave
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False

# --- ماشین حساب ---
def parse_persian_math(text):
    mapping = {
        'صفر': '0', 'یک': '1', 'دو': '2', 'سه': '3', 'چهار': '4', 'پنج': '5',
        'شش': '6', 'شیش': '6', 'هفت': '7', 'هشت': '8', 'نه': '9', 'ده': '10',
        'بیست': '20', 'سی': '30', 'چهل': '40', 'پنجاه': '50', 'شصت': '60',
        'هفتاد': '70', 'هشتاد': '80', 'نود': '90', 'صد': '100', 'هزار': '1000',
        'جمع': '+', 'به‌علاوه': '+', 'به علاوه': '+', 'و': '+',
        'ضرب': '*', 'ضربدر': '*', 'در': '*',
        'تقسیم': '/', 'تقسیم‌بر': '/', 'تقسیم بر': '/', 'بخش': '/',
        'تفریق': '-', 'منهای': '-', 'کم': '-'
    }
    words = text.split()
    translated = []
    for w in words:
        w_en = fa_to_en_digits(w)
        if w_en.isdigit():
            translated.append(w_en)
        elif w in mapping:
            translated.append(mapping[w])
        else:
            translated.append(w)
    return " ".join(translated)

@client.on(events.NewMessage(outgoing=True, pattern=r'^محاسبه\s+(.+)$'))
async def math_calc(event):
    expr = event.pattern_match.group(1)
    expr = parse_persian_math(expr)
    safe_expr = re.sub(r'[^0-9\+\-\*\/\(\)\.\s]', '', expr)
    if not safe_expr: return await event.reply("❗ عبارت نامعتبر است.")
    try:
        result = eval(safe_expr)
        await event.reply(f"🧮 نتیجه: `{result}`")
    except: await event.reply("❗ خطا در محاسبه.")

# --- وضعیت ربات ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^وضعیت$'))
async def status_handler(event):
    def st(b): return "✅ روشن" if b else "❌ خاموش"
    text = (
        "📊 **وضعیت قابلیت‌های ربات:**\n\n"
        f"👻 شبح: {st(core.ghost_mode_active)}\n"
        f"🗑 ضد حذف: {st(core.anti_delete_active)}\n"
        f"🚨 هشدار کلمات: {st(core.keyword_alert_active)}\n"
        f"🐈 شکارچی گربه‌ها: {st(core.stray_cat_active)}\n"
        f"🔹 پوینت خودکار: {st(core.collect_points_active)}\n"
        f"🎣 ماهیگیری: {st(core.fishing_active)}\n"
        f"🏭 کارخونه: {st(core.factory_active)}\n"
        f"🪄 واکنش خودکار: {st(True if core.auto_react_targets else False)}\n"
    )
    await event.reply(text)

# --- واکنش خودکار ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^واکنش\s+(.+)\s+(\S+)$'))
async def add_react(event):
    target_str = event.pattern_match.group(1)
    emoji = event.pattern_match.group(2)
    if target_str in ["لیست", "حذف"]: return
    try:
        pid = int(target_str) if target_str.lstrip('-').isdigit() else utils.get_peer_id(await client.get_entity(target_str))
        core.auto_react_targets[pid] = emoji
        await save_db()
        await event.reply(f"✅ واکنش {emoji} برای `{target_str}` تنظیم شد.")
    except: await event.reply("❗ کاربر/کانال پیدا نشد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^حذف واکنش\s+(.+)$'))
async def rem_react(event):
    target_str = event.pattern_match.group(1)
    try:
        pid = int(target_str) if target_str.lstrip('-').isdigit() else utils.get_peer_id(await client.get_entity(target_str))
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

# --- هلپ (کاملا جامع و ریز) ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^هلپ$'))
async def help_handler(event):
    help_text = (
        "📖 **راهنمای جامع و کامل سلف‌بات** 🤖\n\n"
        "سلام! تمام دستورات من به صورت دسته‌بندی شده در زیر آمده است. هر دستور دقیقاً همانطور که نوشته شده استفاده می‌شود.\n\n"
        
        "🛠 **بخش اول: ابزارهای کاربردی**\n"
        "🔹 **ترجمه کن** (با ریپلای) -> متن ریپلای شده را به فارسی ترجمه می‌کند.\n\n"
        "🔹 **اسپم [مدل] [تعداد] [تاخیر] [متن]**\n"
        "🔑 *مدل ۱:* ارسال تعداد پیام جداگانه. مثال: `اسپم 1 10 5 سلام` (۱۰ پیام با ۵ ثانیه فاصله)\n"
        "🔑 *مدل ۲:* ارسال یک پیام حاوی تکرار متن. مثال: `اسپم 2 10 سلام` (یک پیام می‌فرستد که ۱۰ بار نوشته سلام)\n\n"
        "🔹 **پاکسازی [تعداد]** -> پیام‌های خودتان را در چت برای همه پاک می‌کند.\n"
        "🔹 **پاکسازی همه [تعداد]** -> پیام‌های همه اعضا را پاک می‌کند (فقط ادمین‌ها).\n\n"
        "🔹 **یادداشت [متن]** -> ذخیره یک یادداشت شخصی.\n"
        "🔹 **یادداشت بخوان [رمز]** -> نمایش یادداشت‌ها (رمز: amir1370)\n"
        "🔹 **یادداشت پاک [رمز]** -> پاک کردن کل یادداشت‌ها.\n\n"
        "🔹 **متن** (با ریپلای روی ویس) -> استخراج متن از ویس فارسی/خارجی.\n\n"
        "🔹 **محاسبه [عبارت]** -> ماشین حساب با پشتیبانی از حروف فارسی.\n"
        "📝 مثال: `محاسبه 10 + 20` یا `محاسبه دو ضربدر پنج`\n\n"
        "🔹 **وضعیت** -> مشاهده اینکه کدام قابلیت‌های ربات روشن یا خاموش هستند.\n\n"

        "🪄 **بخش دوم: واکنش خودکار**\n"
        "🔹 **واکنش [آیدی/یوزرنیم/لینک] [ایموجی]**\n"
        "🔑 *کاربرد:* به پیام‌های یک شخص یا کانال خاص، به صورت خودکار ایموجی می‌زند.\n"
        "📝 مثال: `واکنش https://t.me/TweetyChannel 🤣`\n\n"
        "🔹 **حذف واکنش [آیدی/یوزرنیم/لینک]** -> حذف کردن شخص از لیست واکنش خودکار.\n"
        "🔹 **لیست واکنش** یا **واکنش لیست** -> نمایش لیست افراد ثبت شده.\n\n"

        "🕵️ **بخش سوم: مانیتورینگ و جاسوسی**\n"
        "🔹 **ضد حذف روشن / ضد حذف خاموش** -> فعال/غیرفعال کردن سیستم.\n"
        "🔹 **اد حذف [آیدی/ریپلای]** -> اضافه کردن شخص به لیست ضد حذف.\n"
        "🔹 **حذف اد [آیدی/ریپلای]** -> حذف شخص از لیست.\n"
        "🔹 **لیست اد حذف** -> مشاهده لیست.\n\n"
        "🔹 **هشدار [کلمه]** -> ثبت کلمه کلیدی (اگر کسی نوشت، ربات به پیام ذخیره شده شما اطلاع می‌دهد).\n"
        "🔹 **حذف هشدار [کلمه]** -> حذف کلمه از لیست.\n"
        "🔹 **هشدار خاموش** -> خاموش کردن موقت سیستم هشدار.\n"
        "🔹 **لیست هشدار** -> مشاهده کلمات ثبت شده.\n\n"
        "🔹 **شبح روشن / شبح خاموش** -> مخفی ماندن آنلاین بودن و عدم خواندن پیام‌ها (تیک آبی).\n\n"

        "📌 **بخش چهارم: منشن و تگ**\n"
        "🔹 **اد تگ [آیدی/ریپلای] [اسم]** -> اضافه کردن شخص به لیست تگ.\n"
        "🔹 **حذف تگ [آیدی/اسم/ریپلای]** -> حذف شخص از لیست.\n"
        "🔹 **لیست تگ** -> مشاهده لیست.\n"
        "🔹 **تگ همه** -> تگ کردن همه افراد لیست (با ریپلای روی پیام، تگ به آن پیام ریپلای می‌شود).\n"
        "🔹 **تگ [اسم]** -> تگ کردن یک شخص خاص با نوتیفیکیشن (زنگ خوردن گوشی).\n\n"

        "ℹ️ **بخش پنجم: اطلاعات و زمان‌بندی**\n"
        "🔹 **اطلاعات [آیدی/ریپلای]** -> دریافت مشخصات کاربر (نام، آیدی، یوزرنیم، شماره).\n"
        "🔹 **زمان [ساعت] [متن]** یا **زمان [آیدی] [ساعت] [متن]** -> ارسال زمان‌بندی شده پیام.\n"
        "📝 مثال: `زمان 14:30 رسیدم`\n"
        "🔹 **لیست زمان** -> مشاهده پیام‌های در انتظار ارسال.\n\n"

        "🎮 **بخش ششم: سیستم‌های بازی**\n"
        "🔹 **پوینت روشن / پوینت خاموش** -> جمع‌آوری خودکار پوینت (هر ۱۰ دقیقه).\n"
        "🔹 **ماهی روشن / ماهی خاموش** -> سیستم ماهیگیری خودکار (هر ۳۰ دقیقه).\n"
        "🔹 **کارخونه میویی روشن / کارخونه میویی خاموش** -> تولید و فروش خودکار (هر ۱۳ ساعت و ۱۵ دقیقه).\n"
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
    except Exception as e: await event.reply(f"❌ خطا: {e}")

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
        except: return None
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
async def alert_and_react_handler(event):
    # هشدار کلمات
    if core.keyword_alert_active and core.keywords_list:
        txt = event.message.text or ""
        if txt:
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
    
    # واکنش خودکار (با استفاده از chat_id که برای کانال و گروه درست کار میکنه)
    if core.auto_react_targets and event.chat_id in core.auto_react_targets:
        try:
            emoji = core.auto_react_targets[event.chat_id]
            await event.message.react(emoji)
        except Exception as e:
            print(f"خطا در واکنش خودکار: {e}")

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
