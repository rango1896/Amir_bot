import asyncio
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from telethon import TelegramClient, events, utils
from telethon.tl.functions.account import UpdateProfileRequest
from deep_translator import GoogleTranslator
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "ربات زنده‌ست! 🐱"

def run_web():
    app.run(host='0.0.0.0', port=8080)

API_ID = 17349
API_HASH = "344583e45741c457fe1862106095a5eb"
TARGET_GROUP = -1004290700072
group_entity = None

client = TelegramClient('sessions/amir_session', API_ID, API_HASH, parse_mode='html')

collect_points_active = False
fishing_active = False
stray_cat_active = True
factory_active = False

# متغیرهای سیستم ضد حذف
anti_delete_active = False
anti_delete_targets = {}
message_cache = {}

# متغیرهای سیستم زمان‌بندی
scheduled_messages = []

# متغیرهای سیستم هشدار کلمات
keyword_alert_active = False
keywords_list = set()

# متغیرهای حالت شبح
ghost_mode_active = False

# متغیرهای سیستم تگ
tag_targets = {}

# متغیرهای سیستم یادداشت
notes_list = []

# تابع تبدیل اعداد فارسی به انگلیسی
def fa_to_en_digits(text):
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    english_digits = '0123456789'
    translation_table = str.maketrans(persian_digits, english_digits)
    return text.translate(translation_table)

def to_double_struck(text):
    normal = "0123456789"
    double_struck = "𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡"
    result = ""
    for char in text:
        if char in normal:
            index = normal.index(char)
            result += double_struck[index]
        else:
            result += char
    return result

def strip_clock(name):
    parts = name.rsplit(' ', 1)
    if len(parts) == 2:
        last = parts[1]
        if re.fullmatch(r'[0-9𝟘-𝟡]+:[0-9𝟘-𝟡]+', last):
            return parts[0]
    return name

# ================= سیستم هلپ =================
@client.on(events.NewMessage(outgoing=True, pattern=r'^هلپ$'))
async def help_handler(event):
    help_text = (
        "📖 **راهنمای دستورات سلف‌بات:**\n\n"
        "🔹 **ترجمه کن**\n(با ریپلای) متن را به فارسی ترجمه می‌کند.\n\n"
        "🔹 **اسپم [مدل] [تعداد] [ثانیه تاخیر] [متن]**\nمثال: `اسپم ۱ ۱۰ ۵ سلام` (اعداد فارسی/خارجی پشتیبانی میشن)\n\n"
        "🔹 **پاکسازی [تعداد]**\nپاک کردن پیام‌های خودتان در چت.\n\n"
        "🔹 **ضد حذف روشن/خاموش** و **اد حذف [آیدی/ریپلای]** و **حذف اد [آیدی/ریپلای]**\nسیستم ضبط پیام‌های پاک شده.\n\n"
        "🔹 **هشدار [کلمه]** / **لیست هشدار** / **هشدار خاموش**\nاطلاع رسانی کلمات کلیدی.\n\n"
        "🔹 **شبح روشن/خاموش**\nعدم نشان دادن آنلاین بودن و خواندن پیام‌ها.\n\n"
        "🔹 **زمان [ساعت] [متن]** / **لیست زمان**\nارسال زمان‌بندی شده پیام.\n\n"
        "🔹 **اد تگ [آیدی/ریپلای] [اسم]** / **لیست تگ** / **حذف تگ [آیدی/ریپلای]**\nمدیریت لیست تگ.\n\n"
        "🔹 **تگ همه** / **تگ [اسم]**\nتگ کردن افراد (دستور شما پاک میشود).\n\n"
        "🔹 **اطلاعات [آیدی/ریپلای]**\nدریافت اطلاعات کامل یک کاربر.\n\n"
        "🔹 **یادداشت [متن]** / **یادداشت بخوان**\nفلش مموری شخصی.\n\n"
        "🔹 **پوینت/ماهی/کارخونه میویی روشن/خاموش**\nسیستم‌های بازی (کارخونه هر ۱۳.۲۵ ساعت)."
    )
    await event.reply(help_text)
# ==============================================

# ================= سیستم اسپم (اصلاح شده) =================
async def run_spam(model, count, text, chat_id, reply_to=None, delay=0.5):
    try:
        if model == 1:
            for i in range(count):
                await client.send_message(chat_id, text, reply_to=reply_to)
                await asyncio.sleep(delay)
        elif model == 2:
            full_text = (text + " ") * count
            if len(full_text) > 4096:
                full_text = full_text[:4090] + "..."
            await asyncio.sleep(delay)
            await client.send_message(chat_id, full_text, reply_to=reply_to)
    except Exception as e:
        print(f"❌ خطا در اسپم: {type(e).__name__}: {e}")

@client.on(events.NewMessage(outgoing=True, pattern=r'^اسپم\s+(.+)$'))
async def spam_handler(event):
    args = event.pattern_match.group(1).split()
    if len(args) < 3:
        await event.reply("❗ فرمت اشتباه است.\nمثال: `اسپم 1 10 سلام`")
        return
        
    model_str = fa_to_en_digits(args[0])
    count_str = fa_to_en_digits(args[1])
    
    if not model_str.isdigit() or not count_str.isdigit():
        await event.reply("❗ مدل و تعداد باید عدد باشند.")
        return
        
    model = int(model_str)
    count = int(count_str)
    text = ""
    delay = 0.5
    
    if len(args) >= 4:
        potential_delay = fa_to_en_digits(args[2]).replace('.', '', 1)
        if potential_delay.isdigit():
            delay = float(fa_to_en_digits(args[2]))
            text = " ".join(args[3:])
        else:
            text = " ".join(args[2:])
    else:
        text = " ".join(args[2:])
        
    if not text:
        await event.reply("❗ متنی برای اسپم وارد نشده.")
        return
        
    if count > 1000:
        await event.reply("❗ حداکثر تعداد ۱۰۰۰ تعیین شده.")
        return

    reply_to_id = None
    if event.message.is_reply:
        replied_msg = await event.message.get_reply_message()
        if replied_msg:
            reply_to_id = replied_msg.id

    reply_msg = await event.reply(f"🚀 شروع اسپم مدل {model} ({count} بار با تاخیر {delay}ث)...")
    await event.delete()
    await reply_msg.delete()

    asyncio.create_task(run_spam(model, count, text, event.chat_id, reply_to_id, delay))
# ==============================================

# ================= سیستم پاکسازی =================
@client.on(events.NewMessage(outgoing=True, pattern=r'^پاکسازی ([\d۰-۹]+)$'))
async def clear_handler(event):
    count = int(fa_to_en_digits(event.pattern_match.group(1)))
    if count > 1000:
        await event.reply("❗ حداکثر ۱۰۰۰ پیام در دفعات.")
        return
        
    await event.delete()
    deleted_count = 0
    async for msg in client.iter_messages(event.chat_id, from_user='me', limit=count):
        try:
            await msg.delete(revoke=True)
            deleted_count += 1
            await asyncio.sleep(0.1)
        except:
            pass
    confirm = await event.reply(f"🧹 {deleted_count} پیام پاک شد.")
    await asyncio.sleep(3)
    await confirm.delete()
# ==============================================

# ================= سیستم هشدار کلمات =================
@client.on(events.NewMessage(outgoing=True, pattern=r'^هشدار\s+(.+)$'))
async def add_keyword_alert(event):
    global keyword_alert_active
    keyword = event.pattern_match.group(1).strip()
    if keyword == "خاموش":
        keyword_alert_active = False
        await event.reply("🛑 سیستم هشدار **خاموش** شد.")
        return
    elif keyword in ["لیست", "هشدار لیست"]:
        if not keywords_list:
            await event.reply("📋 لیست هشدار خالی است.")
            return
        text = "📋 **کلمات کلیدی هشدار:**\n\n"
        for kw in keywords_list:
            text += f"▫️ `{kw}`\n"
        await event.reply(text)
        return
        
    keywords_list.add(keyword)
    keyword_alert_active = True
    await event.reply(f"✅ کلمه `{keyword}` به لیست هشدار اضافه شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^لیست هشدار$'))
async def list_keyword_alert(event):
    if not keywords_list:
        await event.reply("📋 لیست هشدار خالی است.")
        return
    text = "📋 **کلمات کلیدی هشدار:**\n\n"
    for kw in keywords_list:
        text += f"▫️ `{kw}`\n"
    await event.reply(text)

@client.on(events.NewMessage())
async def keyword_alert_handler(event):
    if not keyword_alert_active or not keywords_list:
        return
    text = event.message.text or ""
    if not text:
        return
    for kw in keywords_list:
        if kw in text:
            try:
                sender = await event.get_sender()
                chat = await event.get_chat()
                sender_name = getattr(sender, 'first_name', None) or getattr(sender, 'title', None) or "ناشناس"
                chat_name = getattr(chat, 'title', None) or "پیوی"
                
                alert_text = (
                    f"🚨 **هشدار کلمه کلیدی: `{kw}`**\n\n"
                    f"👤 فرستنده: {sender_name}\n"
                    f"💬 چت: {chat_name}\n\n"
                    f"📝 متن:\n{text}"
                )
                await client.send_message('me', alert_text)
            except:
                pass
            break
# ==============================================

# ================= سیستم حالت شبح =================
@client.on(events.NewMessage(outgoing=True, pattern=r'^شبح (روشن|خاموش)$'))
async def ghost_mode_toggle(event):
    global ghost_mode_active
    status = event.pattern_match.group(1)
    if status == "روشن":
        ghost_mode_active = True
        await event.reply("👻 حالت شبح **روشن** شد.")
    else:
        ghost_mode_active = False
        await event.reply("🛑 حالت شبح **خاموش** شد.")
# ==============================================

# ================= سیستم ضد حذف =================
@client.on(events.NewMessage(outgoing=True, pattern=r'^ضد حذف (روشن|خاموش)$'))
async def anti_delete_toggle(event):
    global anti_delete_active
    status = event.pattern_match.group(1)
    if status == "روشن":
        anti_delete_active = True
        await event.reply("✅ سیستم ضد حذف **روشن** شد.")
    else:
        anti_delete_active = False
        await event.reply("🛑 سیستم ضد حذف **خاموش** شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^اد حذف(?:\s+(اد شه|(.+)))?$'))
async def add_anti_delete(event):
    targets_str = []
    text_arg = event.pattern_match.group(2)
    if event.message.is_reply and (not text_arg or event.pattern_match.group(1) == 'اد شه'):
        replied_msg = await event.get_reply_message()
        if replied_msg and replied_msg.sender_id:
            targets_str.append(str(replied_msg.sender_id))
    elif text_arg:
        targets_str.extend(text_arg.split())
    else:
        await event.reply("❗ فرمت اشتباه است. روی پیام ریپلای کنید یا آیدی بده.")
        return

    added_list = []
    for target in targets_str:
        try:
            if target.lstrip('-').isdigit():
                pid = int(target)
                name = target
                try:
                    ent = await client.get_entity(pid)
                    name = getattr(ent, 'first_name', None) or getattr(ent, 'title', None) or target
                except:
                    pass
            else:
                ent = await client.get_entity(target)
                pid = utils.get_peer_id(ent)
                name = getattr(ent, 'first_name', None) or getattr(ent, 'title', None) or target
            anti_delete_targets[pid] = name
            added_list.append(f"{name} (`{pid}`)")
        except:
            await event.reply(f"❌ `{target}` پیدا نشد.")

    if added_list:
        await event.reply("✅ اضافه شدند:\n" + "\n".join(added_list))

@client.on(events.NewMessage(outgoing=True, pattern=r'^حذف اد(?:\s+(.+))?$'))
async def remove_anti_delete(event):
    targets_str = []
    text_arg = event.pattern_match.group(1)
    if event.message.is_reply and not text_arg:
        replied_msg = await event.get_reply_message()
        if replied_msg and replied_msg.sender_id:
            targets_str.append(str(replied_msg.sender_id))
    elif text_arg:
        targets_str.extend(text_arg.split())
    else:
        await event.reply("❗ فرمت اشتباه است. روی پیام ریپلای کنید یا آیدی بده.")
        return

    removed_list = []
    for target in targets_str:
        try:
            if target.lstrip('-').isdigit():
                pid = int(target)
            else:
                ent = await client.get_entity(target)
                pid = utils.get_peer_id(ent)
            if pid in anti_delete_targets:
                removed_list.append(anti_delete_targets[pid])
                del anti_delete_targets[pid]
        except:
            pass

    if removed_list:
        await event.reply("❌ حذف شدند:\n" + ", ".join(removed_list))
    else:
        await event.reply("کسی برای حذف پیدا نشد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^لیست اد حذف$'))
async def list_anti_delete(event):
    if not anti_delete_targets:
        await event.reply("📋 لیست ضد حذف خالی است.")
        return
    text = "📋 **لیست ضد حذف:**\n\n"
    for chat_id, name in anti_delete_targets.items():
        text += f"▫️ {name} (`{chat_id}`)\n"
    await event.reply(text)

@client.on(events.NewMessage())
async def anti_delete_cacher(event):
    if not anti_delete_active:
        return
    chat_id = event.chat_id
    sender_id = event.sender_id
    if chat_id in anti_delete_targets or sender_id in anti_delete_targets:
        if chat_id not in message_cache:
            message_cache[chat_id] = {}
        message_cache[chat_id][event.id] = event.message
        if len(message_cache[chat_id]) > 100:
            first_key = next(iter(message_cache[chat_id]))
            del message_cache[chat_id][first_key]

@client.on(events.MessageDeleted)
async def anti_delete_handler(event):
    if not anti_delete_active:
        return
    for msg_id in event.deleted_ids:
        for chat_id, msgs in message_cache.items():
            if msg_id in msgs:
                msg = msgs[msg_id]
                try:
                    sender = await msg.get_sender()
                    chat = await msg.get_chat()
                    sender_name = getattr(sender, 'first_name', None) or getattr(sender, 'title', None) or "ناشناس"
                    sender_id = sender.id
                    sender_username = f"@{sender.username}" if sender.username else "ندارد"
                    chat_name = getattr(chat, 'title', None) or "پیوی"
                    chat_id_val = chat_id
                    chat_username = f"@{chat.username}" if hasattr(chat, 'username') and chat.username else "ندارد"
                    sent_time = msg.date.astimezone(TEHRAN_TZ).strftime("%Y-%m-%d %H:%M:%S")
                    del_time = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d %H:%M:%S")
                    report = (
                        f"🗑 **پیام حذف شد**\n\n"
                        f"👤 **فرستنده:** {sender_name}\n"
                        f"🆔 **آیدی عددی:** `{sender_id}`\n"
                        f"📛 **آیدی کاربر:** {sender_username}\n\n"
                        f"💬 **چت:** {chat_name}\n"
                        f"🆔 **آیدی چت:** `{chat_id_val}`\n"
                        f"🔗 **لینک چت:** {chat_username}\n\n"
                        f"⏱ **زمان ارسال:** {sent_time}\n"
                        f"⏱ **زمان حذف:** {del_time}\n"
                    )
                    if msg.media and (msg.photo or msg.document):
                        try:
                            sent_msg = await client.send_file('me', msg.media)
                            await sent_msg.reply(report)
                        except:
                            await client.send_message('me', f"{report}\n[مدیا قابل بارگذاری نبود]")
                    elif msg.text:
                        await client.send_message('me', f"{report}\n📝 **متن:**\n{msg.text}")
                    else:
                        await client.send_message('me', report)
                except:
                    pass
                del msgs[msg_id]
                break
# ==============================================

# ================= سیستم زمان‌بندی =================
@client.on(events.NewMessage(outgoing=True, pattern=r'^زمان (.+)$'))
async def schedule_message(event):
    parts = event.pattern_match.group(1).split()
    target = None
    time_str = None
    text = None
    if len(parts) >= 3 and re.match(r'^\d{1,2}:\d{2}$', parts[1]):
        target = parts[0]
        time_str = parts[1]
        text = " ".join(parts[2:])
    elif len(parts) >= 2 and re.match(r'^\d{1,2}:\d{2}$', parts[0]):
        time_str = parts[0]
        text = " ".join(parts[1:])
    if not time_str or not text:
        await event.reply("❗ فرمت اشتباه است.")
        return
    chat_id = event.chat_id
    if target:
        try:
            entity = await client.get_entity(target)
            chat_id = utils.get_peer_id(entity)
        except:
            await event.reply("❗ آیدی گیرنده پیدا نشد.")
            return
    scheduled_messages.append({'chat_id': chat_id, 'time': time_str, 'text': text})
    await event.reply(f"⏰ پیام برای ساعت `{time_str}` زمان‌بندی شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^لیست زمان$'))
async def list_schedule(event):
    if not scheduled_messages:
        await event.reply("📋 هیچ پیام زمان‌بندی شده‌ای وجود ندارد.")
        return
    text = "📋 **لیست پیام‌های زمان‌بندی شده:**\n\n"
    for i, job in enumerate(scheduled_messages, 1):
        text += f"{i}. ⏰ `{job['time']}` -> `{job['text'][:20]}...`\n"
    await event.reply(text)

async def schedule_loop():
    while True:
        now = datetime.now(TEHRAN_TZ).strftime("%H:%M")
        for job in scheduled_messages[:]:
            if job['time'] == now:
                try:
                    await client.send_message(job['chat_id'], job['text'])
                    scheduled_messages.remove(job)
                except:
                    pass
        await asyncio.sleep(20)
# ==============================================

# ================= سیستم تگ (Mention) =================
@client.on(events.NewMessage(outgoing=True, pattern=r'^اد تگ(?:\s+(اد شه|(.+)))?$'))
async def add_tag(event):
    text_arg = event.pattern_match.group(2)
    if event.message.is_reply and (not text_arg or event.pattern_match.group(1) == 'اد شه'):
        replied_msg = await event.get_reply_message()
        if replied_msg and replied_msg.sender_id:
            uid = replied_msg.sender_id
            name = getattr(replied_msg.sender, 'first_name', None) or "ناشناس"
            tag_targets[uid] = name
            await event.reply(f"✅ `{name}` به لیست تگ اضافه شد.")
    elif text_arg:
        parts = text_arg.split()
        target = parts[0]
        name = " ".join(parts[1:]) if len(parts) > 1 else target
        try:
            if target.lstrip('-').isdigit():
                uid = int(target)
            else:
                ent = await client.get_entity(target)
                uid = utils.get_peer_id(ent)
            tag_targets[uid] = name
            await event.reply(f"✅ `{name}` به لیست تگ اضافه شد.")
        except:
            await event.reply("❌ پیدا نشد.")
    else:
        await event.reply("❗ فرمت اشتباه است.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^حذف تگ(?:\s+(.+))?$'))
async def remove_tag(event):
    text_arg = event.pattern_match.group(1)
    uid = None
    if event.message.is_reply and not text_arg:
        replied_msg = await event.get_reply_message()
        if replied_msg:
            uid = replied_msg.sender_id
    elif text_arg:
        target = text_arg.split()[0]
        try:
            if target.lstrip('-').isdigit():
                uid = int(target)
            else:
                ent = await client.get_entity(target)
                uid = utils.get_peer_id(ent)
        except:
            pass
    if uid and uid in tag_targets:
        name = tag_targets[uid]
        del tag_targets[uid]
        await event.reply(f"❌ `{name}` از لیست تگ حذف شد.")
    else:
        await event.reply("کسی برای حذف پیدا نشد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^لیست تگ$'))
async def list_tag(event):
    if not tag_targets:
        await event.reply("📋 لیست تگ خالی است.")
        return
    text = "📋 **لیست تگ:**\n\n"
    for uid, name in tag_targets.items():
        text += f"▫️ {name} (`{uid}`)\n"
    await event.reply(text)

@client.on(events.NewMessage(outgoing=True, pattern=r'^تگ همه$'))
async def tag_all(event):
    if not tag_targets:
        await event.reply("❗ لیست تگ خالی است.")
        return
    mention_text = "📢 **تگ所有人:**\n\n"
    for uid, name in tag_targets.items():
        mention_text += f'<a href="tg://user?id={uid}">{name}</a> '
    
    reply_to_id = None
    if event.message.is_reply:
        replied_msg = await event.message.get_reply_message()
        if replied_msg:
            reply_to_id = replied_msg.id
            
    await event.delete()
    await client.send_message(event.chat_id, mention_text, reply_to=reply_to_id)

@client.on(events.NewMessage(outgoing=True, pattern=r'^تگ\s+(.+)$'))
async def tag_single(event):
    name_to_tag = event.pattern_match.group(1).strip()
    target_uid = None
    for uid, name in tag_targets.items():
        if name == name_to_tag:
            target_uid = uid
            break
    if not target_uid:
        await event.reply(f"❗ `{name_to_tag}` در لیست تگ نیست.")
        return
        
    mention_text = f'<a href="tg://user?id={target_uid}">{name_to_tag}</a>'
    reply_to_id = None
    if event.message.is_reply:
        replied_msg = await event.message.get_reply_message()
        if replied_msg:
            reply_to_id = replied_msg.id
            
    await event.delete()
    await client.send_message(event.chat_id, mention_text, reply_to=reply_to_id)
# ==============================================

# ================= سیستم اطلاعات کاربر =================
@client.on(events.NewMessage(outgoing=True, pattern=r'^اطلاعات(?:\s+(.+))?$'))
async def user_info(event):
    target = event.pattern_match.group(1)
    entity = None
    if event.message.is_reply and not target:
        replied_msg = await event.get_reply_message()
        if replied_msg:
            entity = await replied_msg.get_sender()
    elif target:
        try:
            if target.lstrip('-').isdigit():
                entity = await client.get_entity(int(target))
            else:
                entity = await client.get_entity(target)
        except:
            await event.reply("❗ کاربر پیدا نشد.")
            return
    else:
        await event.reply("❗ روی پیام ریپلای کنید یا آیدی بده.")
        return

    name = getattr(entity, 'first_name', None) or getattr(entity, 'title', None) or "ناشناس"
    uid = entity.id
    username = f"@{entity.username}" if hasattr(entity, 'username') and entity.username else "ندارد"
    phone = getattr(entity, 'phone', None)
    phone_str = f"+{phone}" if phone else "مخفی/نامشخص"
    
    info_text = (
        f"👤 **اطلاعات کاربر**\n\n"
        f"📛 **اسم:** {name}\n"
        f"🆔 **آیدی عددی:** `{uid}`\n"
        f"🔖 **یوزرنیم:** {username}\n"
        f"📱 **شماره:** {phone_str}"
    )
    await event.reply(info_text)
# ==============================================

# ================= سیستم یادداشت =================
@client.on(events.NewMessage(outgoing=True, pattern=r'^یادداشت\s+(.+)$'))
async def add_note(event):
    note_text = event.pattern_match.group(1)
    notes_list.append(note_text)
    await event.reply("📝 یادداشت ذخیره شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^یادداشت بخوان$'))
async def read_notes(event):
    if not notes_list:
        await event.reply("📋 هیچ یادداشتی وجود ندارد.")
        return
    text = "📋 **یادداشت‌های شما:**\n\n"
    for i, note in enumerate(notes_list, 1):
        text += f"{i}. {note}\n"
    await event.reply(text)
# ==============================================

POINTS_INTERVAL = 600

async def do_collect_points():
    try:
        await client.send_message(group_entity, "پیشی")
        print("📩 پیشی فرستاده شد. منتظر پنل...")
        found = False
        for attempt in range(30):
            await asyncio.sleep(2)
            messages = await client.get_messages(group_entity, limit=10)
            for msg in messages:
                if msg.buttons:
                    for row in msg.buttons:
                        for btn in row:
                            if "برداشت" in btn.text and "میو" in btn.text:
                                await msg.click(text=btn.text)
                                print(f"✅ روی دکمه «{btn.text}» کلیک شد.")
                                found = True
                                break
                        if found:
                            break
                if found:
                    break
            if found:
                break
        if not found:
            print("⚠️ دکمه برداشت پیدا نشد.")
    except Exception as e:
        print(f"❌ خطا: {type(e).__name__}: {e}")

@client.on(events.NewMessage(outgoing=True, pattern=r'^پوینت روشن$'))
async def points_on(event):
    global collect_points_active
    collect_points_active = True
    await event.reply("✅ جمع‌آوری خودکار پوینت **روشن** شد.")
    await do_collect_points()

@client.on(events.NewMessage(outgoing=True, pattern=r'^پوینت خاموش$'))
async def points_off(event):
    global collect_points_active
    collect_points_active = False
    await event.reply("🛑 جمع‌آوری خودکار پوینت **خاموش** شد.")

FISHING_INTERVAL = 1800 # ۳۰ دقیقه

async def do_fishing():
    try:
        await client.send_message(group_entity, "ماهی")
        print("📩 ماهی فرستاده شد. منتظر پنل...")
        found = False
        for attempt in range(30):
            await asyncio.sleep(2)
            messages = await client.get_messages(group_entity, limit=10)
            for msg in messages:
                if msg.buttons:
                    for row in msg.buttons:
                        for btn in row:
                            if "بده پیشی" in btn.text:
                                await msg.click(text=btn.text)
                                print(f"✅ روی دکمه «{btn.text}» کلیک شد.")
                                found = True
                                break
                        if found:
                            break
                if found:
                    break
            if found:
                break
        if not found:
            print("⚠️ دکمه ماهیگیری پیدا نشد.")
    except Exception as e:
        print(f"❌ خطا: {type(e).__name__}: {e}")

@client.on(events.NewMessage(outgoing=True, pattern=r'^ماهی روشن$'))
async def fishing_on(event):
    global fishing_active
    fishing_active = True
    await event.reply("🎣 سیستم ماهیگیری **روشن** شد.")
    await do_fishing()

@client.on(events.NewMessage(outgoing=True, pattern=r'^ماهی خاموش$'))
async def fishing_off(event):
    global fishing_active
    fishing_active = False
    await event.reply("🛑 سیستم ماهیگیری **خاموش** شد.")

async def collect_points_loop():
    global collect_points_active
    while True:
        await asyncio.sleep(POINTS_INTERVAL)
        if collect_points_active:
            await do_collect_points()

async def fishing_loop():
    global fishing_active
    while True:
        await asyncio.sleep(FISHING_INTERVAL)
        if fishing_active:
            await do_fishing()

TEHRAN_TZ = ZoneInfo("Asia/Tehran")

async def update_name_clock():
    while True:
        try:
            me = await client.get_me()
            base_name = strip_clock(me.first_name or "")
            now = datetime.now(TEHRAN_TZ).strftime("%H:%M")
            clock_str = to_double_struck(now)
            new_name = f"{base_name} {clock_str}" if base_name else clock_str
            await client(UpdateProfileRequest(first_name=new_name))
            print(f"🕒 اسم به‌روز شد (تهران): {new_name}")
        except Exception as e:
            print(f"❌ خطا: {type(e).__name__}: {e}")
        await asyncio.sleep(60)

async def meow_loop():
    while True:
        try:
            await client.send_message(group_entity, "میو")
            print("🐱 میو فرستاده شد")
        except Exception as e:
            print(f"❌ خطا: {type(e).__name__}: {e}")
        await asyncio.sleep(300)

stray_lock = asyncio.Lock()

async def rescue_stray_cat(msg):
    async with stray_lock:
        print("🐈 شروع عملیات نجات گربه خیابونی...")
        for i in range(3):
            try:
                current_msg = await client.get_messages(group_entity, ids=msg.id)
                if not current_msg or not current_msg.buttons:
                    print("⚠️ پیام گربه ناپدید شد.")
                    break
                for row in current_msg.buttons:
                    for btn in row:
                        if "نجات پیشی خیابونی" in btn.text:
                            await current_msg.click(text=btn.text)
                            print(f"✅ کلیک {i+1}/۳ روی «{btn.text}»")
                            break
                    else:
                        continue
                    break
                else:
                    print("⚠️ دکمه نجات پیدا نشد.")
                    break
                if i < 2:
                    await asyncio.sleep(2)
            except Exception as e:
                print(f"❌ خطا: {type(e).__name__}: {e}")
                break
        print("🏁 عملیات نجات تموم شد.")

@client.on(events.NewMessage(incoming=True))
async def stray_cat_handler(event):
    if not stray_cat_active:
        return
    if not event.is_group or event.chat_id != TARGET_GROUP:
        return
    if event.message.buttons:
        for row in event.message.buttons:
            for btn in row:
                if "نجات پیشی خیابونی" in btn.text:
                    print("🐈 گربه خیابونی دیده شد! شروع نجات...")
                    await rescue_stray_cat(event.message)
                    return

# ================= سیستم کارخونه =================

async def click_factory_button(msg_id, target_text, timeout=30):
    for _ in range(timeout):
        await asyncio.sleep(1)
        msg = await client.get_messages(group_entity, ids=msg_id)
        if msg and msg.buttons:
            for row in msg.buttons:
                for btn in row:
                    if target_text in btn.text:
                        await msg.click(text=btn.text)
                        print(f"✅ روی دکمه «{btn.text}» کلیک شد.")
                        return True
    print(f"⚠️ دکمه شامل «{target_text}» پیدا نشد.")
    return False

async def click_factory_coords(msg_id, row_idx, col_idx, timeout=30):
    for _ in range(timeout):
        await asyncio.sleep(1)
        msg = await client.get_messages(group_entity, ids=msg_id)
        if msg and msg.buttons:
            try:
                await msg.click(row_idx, col_idx)
                print(f"✅ روی مختصات (ردیف {row_idx}، ستون {col_idx}) کلیک شد.")
                return True
            except Exception:
                pass
    print(f"⚠️ دکمه در مختصات (ردیف {row_idx}، ستون {col_idx}) پیدا نشد.")
    return False

async def factory_cycle():
    global factory_active
    while factory_active:
        try:
            print("🏭 شروع چرخه کارخونه (فاز تولید)...")
            await client.send_message(group_entity, "کارخونه میویی")
            await asyncio.sleep(3)
            
            panel_msg = None
            async for m in client.iter_messages(group_entity, limit=5):
                if m.buttons:
                    panel_msg = m
                    break
            
            if not panel_msg:
                print("⚠️ پنل کارخونه پیدا نشد. تلاش مجدد در ۱۰ ثانیه...")
                await asyncio.sleep(10)
                continue
            
            panel_id = panel_msg.id
            
            if not await click_factory_button(panel_id, "تولید"): continue
            await asyncio.sleep(2)
            if not await click_factory_button(panel_id, "تولیدی هواپیما"): continue
            await asyncio.sleep(2)
            if not await click_factory_coords(panel_id, 0, 2): continue
            await asyncio.sleep(2)
            if not await click_factory_coords(panel_id, 0, 3): continue
            await asyncio.sleep(2)
            if not await click_factory_button(panel_id, "شروع تولید"): continue
            
            print("⏳ تولید استارت خورد. سیستم ۱۳ ساعت و ۱۵ دقیقه صبر می‌کنه...")
            waited = 0
            # 13 ساعت (46800 ثانیه) + 15 دقیقه (900 ثانیه) = 47700
            while waited < 47700 and factory_active: # 13.25 ساعت
                await asyncio.sleep(60)
                waited += 60
            
            if not factory_active:
                break
            
            print("💰 زمان فروش رسید. شروع فاز فروش...")
            await client.send_message(group_entity, "کارخونه میویی")
            await asyncio.sleep(3)
            
            panel_msg = None
            async for m in client.iter_messages(group_entity, limit=5):
                if m.buttons:
                    panel_msg = m
                    break
            
            if not panel_msg:
                print("⚠️ پنل فروش پیدا نشد.")
                continue
            
            panel_id = panel_msg.id
            
            if not await click_factory_button(panel_id, "انبار"): continue
            await asyncio.sleep(2)
            if not await click_factory_coords(panel_id, 0, 0): continue
            await asyncio.sleep(2)
            if not await click_factory_button(panel_id, "فروش محصول"): continue
            
            print("✅ فروش انجام شد. چرخه از اول تکرار میشه...")
            await asyncio.sleep(3)
            
        except Exception as e:
            print(f"❌ خطا در کارخونه: {type(e).__name__}: {e}")
            await asyncio.sleep(10)

@client.on(events.NewMessage(outgoing=True, pattern=r'^کارخونه میویی روشن$'))
async def factory_on(event):
    global factory_active
    if not factory_active:
        factory_active = True
        await event.reply("🏭 سیستم کارخونه میویی **روشن** شد.")
        asyncio.create_task(factory_cycle())
    else:
        await event.reply("❗ کارخونه از قبل روشنه.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^کارخونه میویی خاموش$'))
async def factory_off(event):
    global factory_active
    factory_active = False
    await event.reply("🛑 سیستم کارخونه میویی **خاموش** شد.")

async def main():
    global group_entity
    await client.start()
    group_entity = await client.get_entity(TARGET_GROUP)
    print(f"✅ گروه پیدا شد: {group_entity.title}")
    print("✅ سلف‌بات Amir روشن شد!")

    await asyncio.gather(
        meow_loop(),
        update_name_clock(),
        collect_points_loop(),
        fishing_loop(),
        schedule_loop()
    )

def keep_alive():
    import time
    while True:
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    with client:
        client.loop.run_until_complete(main())
