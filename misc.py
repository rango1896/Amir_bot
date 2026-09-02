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
        f"🪄 واکنش خودکار: {st(True if core.auto_react_targets else False)}\n"
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

# --- زمان‌بندی (اصلاح شده) ---
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

# --- هلپ (بدون یادداشت) ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^هلپ$'))
async def help_handler(event):
    help_text = (
        "📖 **راهنمای جامع و کامل سلف‌بات** 🤖\n\n"
        "🛠 **بخش اول: ابزارهای کاربردی**\n"
        "🔹 **اسپم [مدل] [تعداد] [تاخیر] [متن]** -> `اسپم 1 10 5 سلام`\n"
        "🔹 **پاکسازی [تعداد]** -> پاک کردن پیام‌های خودتان.\n"
        "🔹 **پاکسازی همه [تعداد]** -> پاک کردن پیام‌های همه (ادمین‌ها).\n\n"
        "🔹 **متن** (با ریپلای روی ویس) -> استخراج متن از ویس.\n\n"
        "🔹 **محاسبه [عبارت]** -> ماشین حساب (عددی یا حروفی)\nمثال: `محاسبه دو ضربدر پنج`\n\n"
        "🔹 **وضعیت** -> مشاهده روشن/خاموش بودن قابلیت‌ها.\n\n"

        "🪄 **بخش دوم: واکنش خودکار**\n"
        "🔹 **واکنش [آیدی/یوزرنیم/لینک] [ایموجی]** -> `واکنش @channel 🤣`\n"
        "🔹 **حذف واکنش [آیدی/یوزرنیم/لینک]**\n"
        "🔹 **لیست واکنش**\n\n"

        "🕵️ **بخش سوم: مانیتورینگ و جاسوسی**\n"
        "🔹 **ضد حذف روشن/خاموش** / **اد حذف [آیدی/ریپلای]** / **حذف اد**\n"
        "🔹 **هشدار [کلمه]** / **حذف هشدار [کلمه]** / **هشدار خاموش** / **لیست هشدار**\n"
        "🔹 **شبح روشن / شبح خاموش**\n\n"

        "📌 **بخش چهارم: منشن و تگ**\n"
        "🔹 **اد تگ [آیدی/ریپلای] [اسم]** / **حذف تگ** / **لیست تگ**\n"
        "🔹 **تگ همه** / **تگ [اسم]**\n\n"

        "ℹ️ **بخش پنجم: اطلاعات و زمان‌بندی**\n"
        "🔹 **اطلاعات [آیدی/ریپلای]** -> مشخصات کاربر.\n"
        "🔹 **زمان [ساعت] [متن]** -> `زمان 14:30 سلام`\n\n"

        "🎮 **بخش ششم: سیستم‌های بازی**\n"
        "🔹 **پوینت/ماهی/کارخونه میویی روشن/خاموش**\n"
    )
    await event.reply(help_text)
