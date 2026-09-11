import g4f
from g4f.client import Client
from telethon import events
import core
import asyncio

# این دیکشنری برای ذخیره حافظه مکالمات شماست
chat_histories = {}

@core.client.on(events.NewMessage(outgoing=True, pattern=r'^هوش پاک کن$'))
async def clear_chat(event):
    chat_id = event.chat_id
    if chat_id in chat_histories:
        del chat_histories[chat_id]
    await event.edit("🧹 حافظه هوش مصنوعی برای این چت پاک شد! از الان حرف‌های قبلی رو یادش نمیاد.")

@core.client.on(events.NewMessage(outgoing=True, pattern=r'^هوش (.+)$'))
async def ai_chat_handler(event):
    question = event.pattern_match.group(1)
    chat_id = event.chat_id
    
    processing_msg = await event.edit(f"🧠 در حال فکر کردن به سوال...\n\n**سوال:** {question}")
    
    # اگر چت جدید بود، یه حافظه خالی براش می‌سازیم
    if chat_id not in chat_histories:
        chat_histories[chat_id] = []
        
    # اضافه کردن سوال فعلی شما به انتهای تاریخچه
    chat_histories[chat_id].append({"role": "user", "content": question})
    
    # محدود کردن حافظه به ۱۰ پیام آخر (برای جلوگیری از پر شدن حجم و کند شدن ربات)
    if len(chat_histories[chat_id]) > 10:
        chat_histories[chat_id] = chat_histories[chat_id][-10:]
        
    try:
        def ask_ai():
            client = Client()
            # استفاده از مدل و پروایدر مشخص تا درگیر ارورهای کروم و پولی نشیم
            response = client.chat.completions.create(
                model="gpt-4",
                provider=g4f.Provider.Blackbox, # این سرویس بدون کروم و رایگانه
                messages=chat_histories[chat_id], # ارسال کل تاریخچه چت به جای فقط یک سوال
                timeout=30
            )
            return response.choices[0].message.content
        
        # اجرای تابع همگام در یک ترد جداگانه
        response_text = await asyncio.to_thread(ask_ai)
        
        if response_text:
            # ذخیره جواب هوش مصنوعی در حافظه تا پیام بعدی بدونه چی گفته بود
            chat_histories[chat_id].append({"role": "assistant", "content": response_text})
            
            final_answer = f"🤖 **پاسخ هوش مصنوعی:**\n\n{response_text}"
            
            if len(final_answer) > 4000:
                final_answer = final_answer[:4000] + "..."
                
            await processing_msg.edit(final_answer)
        else:
            # اگر جواب خالی بود، سوال رو از حافظه برمیداریم
            chat_histories[chat_id].pop()
            await processing_msg.edit("❌ هوش مصنوعی هیچ پاسخی برنگرداند. لطفا دوباره امتحان کنید.")
            
    except Exception as e:
        # اگر اروری داد، سوال رو از حافظه برمیداریم تا دفعه بعد گیر نکنه
        chat_histories[chat_id].pop()
        await processing_msg.edit(f"❌ خطا در ارتباط با هوش مصنوعی:\n`{e}`")
