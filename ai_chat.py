import requests
import urllib.parse
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
    
    if chat_id not in chat_histories:
        chat_histories[chat_id] = []
        
    chat_histories[chat_id].append({"role": "user", "content": question})
    
    # محدود کردن حافظه به ۶ پیام آخر (برای جلوگیری از طولانی شدن بیش از حد)
    if len(chat_histories[chat_id]) > 6:
        chat_histories[chat_id] = chat_histories[chat_id][-6:]
        
    try:
        def ask_ai():
            # تبدیل تاریخچه مکالمات به یک متن واحد تا هوش مصنوعی حرف‌های قبلی رو بخونه
            full_prompt = "You are a helpful assistant.\n"
            for msg in chat_histories[chat_id]:
                role = "User" if msg["role"] == "user" else "Assistant"
                full_prompt += f"{role}: {msg['content']}\n"
            
            full_prompt += "Assistant: "
            
            # کدگذاری متن برای استفاده در URL
            encoded_prompt = urllib.parse.quote(full_prompt)
            
            # استفاده از موتور رایگان Mistral در پولینیشن (بدون نیاز به API Key)
            url = f"https://text.pollinations.ai/{encoded_prompt}?model=mistral"
            
            headers = {
                "User-Agent": "Mozilla/5.0"
            }
            
            response = requests.get(url, headers=headers, timeout=40)
            response.raise_for_status()
            
            # پاسخ مستقیم به صورت متن برمیگرده
            return response.text
        
        # اجرای تابع همگام در یک ترد جداگانه
        response_text = await asyncio.to_thread(ask_ai)
        
        if response_text:
            # ذخیره جواب هوش مصنوعی در حافظه
            chat_histories[chat_id].append({"role": "assistant", "content": response_text})
            
            final_answer = f"🤖 **پاسخ هوش مصنوعی:**\n\n{response_text}"
            
            if len(final_answer) > 4000:
                final_answer = final_answer[:4000] + "..."
                
            await processing_msg.edit(final_answer)
        else:
            chat_histories[chat_id].pop()
            await processing_msg.edit("❌ هوش مصنوعی هیچ پاسخی برنگرداند. لطفا دوباره امتحان کنید.")
            
    except Exception as e:
        # اگر اروری داد، سوال رو از حافظه برمیداریم
        chat_histories[chat_id].pop()
        await processing_msg.edit(f"❌ خطا در ارتباط با هوش مصنوعی:\n`{e}`")
