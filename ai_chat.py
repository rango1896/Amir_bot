import urllib.parse
import urllib.request
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
        # تابع همگام برای پرسش از هوش مصنوعی (بدون نیاز به API و کتابخانه)
        def ask_ai():
            # کدگذاری سوال برای استفاده در URL
            encoded_question = urllib.parse.quote(question)
            url = f"https://text.pollinations.ai/{encoded_question}"
            
            # ایجاد درخواست با User-Agent (برای جلوگیری از بلاک شدن)
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            
            # ارسال درخواست و خواندن پاسخ
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read().decode('utf-8')
        
        # اجرای تابع همگام در یک ترد جداگانه تا ربات تلگرام فریز نشود
        response_text = await asyncio.to_thread(ask_ai)
        
        # اگر هوش مصنوعی جوابی داد
        if response_text:
            final_answer = f"🤖 **پاسخ هوش مصنوعی:**\n\n{response_text}"
            
            # جلوگیری از ارور تلگرام برای متن‌های خیلی طولانی (محدودیت 4096 کاراکتر)
            if len(final_answer) > 4000:
                final_answer = final_answer[:4000] + "..."
                
            await processing_msg.edit(final_answer)
        else:
            await processing_msg.edit("❌ هوش مصنوعی هیچ پاسخی برنگرداند.")
            
    except Exception as e:
        await processing_msg.edit(f"❌ خطا در ارتباط با هوش مصنوعی:\n`{e}`")
