from duckduckgo_search import DDGS
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
            with DDGS() as ddgs:
                # مدل gpt-4o-mini رایگان و سریع است
                return ddgs.chat(question, model="gpt-4o-mini")
        
        # اجرای تابع همگام در یک ترد جداگانه تا ربات تلگرام فریز نشود
        response = await asyncio.to_thread(ask_ai)
        
        # اگر هوش مصنوعی جوابی داد
        if response:
            final_answer = f"🤖 **پاسخ هوش مصنوعی:**\n\n{response}"
            await processing_msg.edit(final_answer)
        else:
            await processing_msg.edit("❌ هوش مصنوعی هیچ پاسخی برنگرداند.")
            
    except Exception as e:
        await processing_msg.edit(f"❌ خطا در ارتباط با هوش مصنوعی:\n`{e}`")
