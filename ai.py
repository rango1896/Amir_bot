import aiohttp
from telethon import events
import core
from core import client

# کلید شما در سایت Groq (فعال شده)
GROQ_API_KEY = "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"

@client.on(events.NewMessage(outgoing=True, pattern=r'^هوش\s+(.+)$'))
async def ai_handler(event):
    prompt = event.pattern_match.group(1).strip()
    if not prompt:
        return await event.reply("❗ سوالی نپرسیدی! مثال: `هوش سلام`")
    
    # نشون دادن حالت تایپ کردن تا ربات جواب رو بیاره
    async with client.action(event.chat_id, 'typing'):
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama3-8b-8192", # مدل قدرتمند و رایگان متا
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant. Answer in Persian accurately and concisely."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=60) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        answer = data['choices'][0]['message']['content']
                        await event.reply(f"🤖 **پاسخ هوش مصنوعی:**\n\n{answer}")
                    else:
                        await event.reply(f"❌ خطا در ارتباط با سرور. (کد: {resp.status})")
        except Exception as e:
            await event.reply(f"❌ خطا: {e}")
