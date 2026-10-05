import asyncio
import re
from datetime import datetime
from telethon import events, utils
import core
from core import client, fa_to_en_digits, save_db, TEHRAN_TZ

# --- وضعیت ---
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
        f"🎯 دشمن: {st(core.enemy_active)}\n"
        f"🌀 دانجن: {st(core.dungeon_active)}\n"
        f"🪄 واکنش خودکار: {st(True if core.multi_active_reactions else False)}\n"
    )
    await event.reply(text)

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
        if w_en.isdigit(): translated.append(w_en)
        elif w in mapping: translated.append(mapping[w])
        else: translated.append(w)
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
    await event.reply(f"⏰ پیام برای ساعت `{tm}` ثبت شد.")

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

# --- هلپ (جدید و فوق‌العاده) ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^هلپ$'))
async def help_handler(event):
    help_text = (
        "╭━━━ 🎮 **راهنمای سلف‌بات** ━━━╮\n"
        "┃ ⚡ **قدرتمند • سریع • خودکار**\n"
        "╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
        
        "🎮 **Piou Game | بازی**\n\n"
        
        "🐣 **پیو**\n"
        "• `پیو روشن` — شلیک خودکار + هیل + خرید مهمات + شلیک کور + ارسال گوشت\n"
        "• `پیو خاموش` — توقف پیو\n\n"
        
        "🧠 **هوشمند**\n"
        "• `هوشمند روشن` — مدیریت هوشمند مرگ و جعبه کمک اولیه\n"
        "• `هوشمند خاموش`\n\n"
        
        "🩹 **بانداژ**\n"
        "• `بانداژ روشن` — تأمین خودکار بانداژ\n"
        "• `بانداژ خاموش`\n\n"
        
        "🥊 **رینگ**\n"
        "• `رینگ روشن` — ارتقای هوشمند مهارت‌ها\n"
        "• `رینگ خاموش`\n\n"
        
        "🔫 **اسکواد**\n"
        "• `اسکواد روشن` — استخراج خودکار گان‌پوینت هر ۱۰ دقیقه\n"
        "• `اسکواد خاموش`\n\n"
        
        "🎨 **آرت**\n"
        "• `پیدا کردن آرت [اسم]` — جستجوی خودکار فن‌آرت در مارکت\n"
        "• `آرت متوقف` — توقف جستجو\n\n"
        
        "🏰 **دانجن**\n"
        "• `دانجن روشن` — پارتی‌بندی خودکار + انتخاب رندوم فن‌آرت + شروع دانجن\n"
        "• `دانجن خاموش`\n\n"
        
        "🏭 **کارخونه میویی**\n"
        "• `کارخونه میویی روشن` — مدیریت هوشمند تولید و فروش\n"
        "• `کارخونه میویی خاموش`\n\n"
        
        "🎯 **تنظیمات شلیک**\n"
        "• `تنظیم تیر [تعداد]`\n"
        "• `تنظیم زمان شلیک [ثانیه]`\n\n"
        
        "╭━━━ 🎯 **سیستم دشمن** ━━━╮\n\n"
        "⚔️ `دشمن روشن`\n"
        "شروع شلیک خودکار به دشمنان\n"
        "⚠️ ابتدا ۱۵۰ پیام آخر کاربر پاک می‌شود.\n"
        "💀 اگر دشمن بمیرد، تا ۱۰ دقیقه به او شلیک نمی‌شود.\n\n"
        "🛑 `دشمن خاموش` — توقف سیستم\n\n"
        "➕ `پیو دشمن [آیدی/یوزرنیم]`\n"
        "➖ `پیو حذف دشمن [آیدی/یوزرنیم]`\n"
        "📋 `لیست دشمن`\n\n"
        
        "╭━━━ 🛠 **ابزارهای کاربردی** ━━━╮\n\n"
        "🧮 `محاسبه [عبارت]`\n"
        "پشتیبانی از اعداد و حروف فارسی\n"
        "مثال: `محاسبه دو ضربدر پنج`\n\n"
        "⏰ `زمان [ساعت] [متن]`\n"
        "ارسال خودکار پیام در ساعت مشخص\n\n"
        "📊 `وضعیت`\n"
        "نمایش وضعیت تمام قابلیت‌ها\n\n"
        "🧹 `پاکسازی [تعداد]`\n"
        "پاک کردن پیام‌های خودکار\n\n"
        "🗑 `پاکسازی همه [تعداد]`\n"
        "پاک کردن کل پیام‌های گروه\n\n"
        "📨 `اسپم [مدل] [تعداد] [تاخیر] [متن]`\n"
        "اسپمر پیشرفته\n\n"
        "👤 `اطلاعات [آیدی/ریپلای]`\n"
        "نمایش نام، آیدی، یوزرنیم و شماره\n\n"
        "📥 `دزدی [ریپلای/لینک]`\n"
        "ذخیره ویس، عکس، استیکر یا متن در پیام‌های ذخیره‌شده\n\n"
        "🕐 `ساعت خودکار`\n"
        "نمایش ساعت کنونی کنار نام با فونت خاص\n\n"
        
        "╭━━━ 🪄 **واکنش و انیمیشن** ━━━╮\n\n"
        "❤️ `واکنش [تعداد/مختلف] [آیدی/یوزرنیم/لینک] [ایموجی‌ها]`\n"
        "واکنش خودکار با اکانت اصلی و سنیورها\n\n"
        "❌ `حذف واکنش [آیدی/یوزرنیم]`\n"
        "توقف واکنش در چت مشخص\n\n"
        "✨ **انیمیشن متنی**\n"
        "• ☀️ `خورشید`\n"
        "• 🔫 `تفنگ`\n"
        "⏱ اجرای انیمیشن‌های ایموجی تا ۳۰ ثانیه\n\n"
        
        "╭━━━ 🕵️ **مانیتورینگ و امنیت** ━━━╮\n\n"
        "👁 **ضد حذف**\n"
        "• `ضد حذف روشن`\n"
        "• `ضد حذف خاموش`\n"
        "ذخیره پیام‌های حذف‌شده افراد مشخص\n\n"
        "👤 **مدیریت ضد حذف**\n"
        "• `اد حذف`\n"
        "• `حذف اد`\n"
        "• `لیست اد حذف`\n\n"
        "🚨 **هشدار کلمه**\n"
        "• `هشدار [کلمه]`\n"
        "• `حذف هشدار`\n"
        "• `لیست هشدار`\n"
        "دریافت هشدار فوری هنگام استفاده از کلمه مشخص در گروه‌ها\n\n"
        "👻 **شبح**\n"
        "• `شبح روشن`\n"
        "• `شبح خاموش`\n"
        "مخفی کردن وضعیت آنلاین و تیک آبی\n\n"
        "📥 **دانلود خودکار**\n"
        "• `اد دانلود [آیدی گروه]`\n"
        "• `حذف دانلود`\n"
        "دانلود خودکار ویدیو از سرویس‌های مجاز مثل یوتیوب، اینستاگرام و تیک‌تاک\n\n"
        
        "╭━━━ ⚡ **نکته** ━━━╮\n"
        "💡 دستورات را دقیقاً با همین فرمت ارسال کنید.\n"
        "🔄 برای قابلیت‌های روشن/خاموش، وضعیت فعلی را با `وضعیت` مشاهده کنید.\n\n"
        "╰━━━ 🤖 **SelfBot** ━━━╯"
    )
    await event.reply(help_text, link_preview=False)
