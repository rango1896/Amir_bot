import requests
import json
from telethon import events
import core
import asyncio

# دیکشنری برای ذخیره حافظه مکالمات
chat_histories = {}

# متغیر برای نگه داشتن توکن خام DuckDuckGo
ddg_vqd = None

def get_ddg_token():
    """گرفتن توکن اولیه از DuckDuckGo"""
    url = "https://duckduckgo.com/duckchat/v1/status"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "x-vqd-accept": "1"
    }
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.headers.get("x-vqd-4")
    return None

def ask_ddg(messages, model="gpt-4o-mini"):
    """ارسال درخواست به هوش مصنوعی DuckDuckGo"""
    global ddg_vqd
    if not ddg_vqd:
        ddg_vqd = get_ddg_token()
        if not ddg_vqd:
            raise Exception("Cannot get DDG Token (Maybe blocked by Render IP)")

    url = "https://duckduckgo.com/duckchat/v1/chat"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "x-vqd-4": ddg_vqd,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages
    }

    r = requests.post(url, headers=headers, json=payload, stream=True)

    if r.status_code == 429:
        ddg_vqd = None # ریست کردن توکن برای دفعه بعد
        raise Exception("DuckDuckGo Rate Limit. Please wait a moment.")
    elif r.status_code != 200:
        ddg_vqd = None
        raise Exception(f"DDG Error: {r.status_code}")

    full_response = ""
    # خواندن جواب به صورت استریم (همون جواب‌های روان که کلمه به کلمه میاد)
    for line in r.iter_lines():
        if line:
            decoded_line = line.decode("utf-8")
            if decoded_line.startswith("data: "):
                json_str = decoded_line[6:]
                if json_str == "[DONE]":
                    break
                try:
                    data = json.loads(json_str)
                    if data.get("message"):
                        full_response += data["message"]
                except:
                    pass

    # آپدیت کردن توکن برای پیام بعدی
    new_vqd = r.headers.get("x-vqd-4")
    if new_vqd:
        ddg_vqd = new_vqd

    return full_response


@core.client.on(events.NewMessage(outgoing=True, pattern=r'^هوش پاک کن$'))
async def clear_chat(event):
    chat_id = event.chat_id
    if chat_id in chat_histories:
        del chat_histories[chat_id]
    await event.edit("🧹 حافظه هوش مصنوعی پاک شد!")

@core.client.on(events.NewMessage(outgoing=True, pattern=r'^هوش (.+)$'))
async def ai_chat_handler(event):
    question = event.pattern_match.group(1)
    chat_id = event.chat_id
    
    processing_msg = await event.edit(f"🧠 در حال فکر کردن به سوال...\n\n**سوال:** {question}")
    
    if chat_id not in chat_histories:
        chat_histories[chat_id] = []
        
    chat_histories[chat_id].append({"role": "user", "content": question})
    
    # محدود کردن حافظه به ۱۰ پیام آخر
    if len(chat_histories[chat_id]) > 10:
        chat_histories[chat_id] = chat_histories[chat_id][-10:]
        
    try:
        # ارسال مستقیم تاریخچه چت به هوش مصنوعی (دقیقا مثل OpenAI)
        response_text = await asyncio.to_thread(ask_ddg, chat_histories[chat_id])
        
        if response_text:
            # ذخیره جواب هوش مصنوعی در حافظه
            chat_histories[chat_id].append({"role": "assistant", "content": response_text})
            
            final_answer = f"🤖 **پاسخ هوش مصنوعی:**\n\n{response_text}"
            
            if len(final_answer) > 4000:
                final_answer = final_answer[:4000] + "..."
                
            await processing_msg.edit(final_answer)
        else:
            chat_histories[chat_id].pop()
            await processing_msg.edit("❌ هوش مصنوعی هیچ پاسخی برنگرداند.")
                
    except Exception as e:
        chat_histories[chat_id].pop()
        await processing_msg.edit(f"❌ خطا در ارتباط با هوش مصنوعی:\n`{e}`")
