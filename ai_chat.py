import g4f
from telethon import events
import core
import asyncio

@core.client.on(events.NewMessage(outgoing=True, pattern=r'^هوش (.+)$'))
async def ai_chat_handler(event):
    # گرفتن متن سوال کاربر
    question = event.pattern_match.group(1)
    
    # اول پیام رو ادیت می‌کنیم تا نشون بده در حال پردازشه
    processing_msg = await event.edit(f"🧠 در حال فکر کردن به سوال...\n\n**سوال:** {question}")
    
    try:
        # تابع همگام برای پرسش از هوش مصنوعی
        def ask_ai():
            # استفاده از موتور g4f که خودش بهترین سرویس‌های رایگان رو پیدا می‌کنه
            response = g4f.ChatCompletion.create(
                model="gpt-3.5-turbo", # میتونید gpt-4 یا claude هم بذارید
                messages=[{"role": "user", "content": question}],
                timeout=30
            )
            return response
        
        # اجرای تابع همگام در یک ترد جداگانه تا ربات تلگرام فریز نشود
        response_text = await asyncio.to_thread(ask_ai)
        
        # گاهی اوقات کتابخانه جواب رو به صورت لیست برمی‌گردونه، این کد اونو متن تبدیل می‌کنه
        if isinstance(response_text, list):
            response_text = "".join(response_text)
            
        # اگر هوش مصنوعی جوابی داد
        if response_text:
            final_answer = f"🤖 **پاسخ هوش مصنوعی:**\n\n{response_text}"
            
            # جلوگیری از ارور تلگرام برای متن‌های خیلی طولانی
            if len(final_answer) > 4000:
                final_answer = final_answer[:4000] + "..."
                
            await processing_msg.edit(final_answer)
        else:
            await processing_msg.edit("❌ هوش مصنوعی هیچ پاسخی برنگرداند.")
            
    except Exception as e:
        await processing_msg.edit(f"❌ خطا در ارتباط با هوش مصنوعی:\n`{e}`")
