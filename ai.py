import aiohttp
from telethon import events
import core
from core import client

@client.on(events.NewMessage(outgoing=True, pattern=r'^هوش\s+(.+)$'))
async def ai_handler(event):
    prompt = event.pattern_match.group(1).strip()
    if not prompt:
        return await event.reply("❗ سوالی نپرسیدی! مثال: `هوش آب پختن پلو چقدر طول میکشه؟`")
    
    # نشون دادن حالت تایپ کردن تا ربات جواب رو بیاره
    async with client.action(event.chat_id, 'typing'):
        try:
            # درخواست به سایت Pollinations (بدون نیاز به API Key)
            url = "https://text.pollinations.ai/openai"
            payload = {
                "model": "openai", # استفاده از مدل قدرتمند openai
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant. Answer accurately and concisely in Persian."},
                    {"role": "user", "content": prompt}
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=60) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        answer = data.get('choices', [{}])[0].get('message', {}).get('content', 'جوابی پیدا نشد.')
                        await event.reply(f"🤖 **پاسخ هوش مصنوعی:**\n\n{answer}")
                    else:
                        await event.reply(f"❌ خطا در ارتباط با سرور. (کد: {resp.status})")
        except Exception as e:
            await event.reply(f"❌ خطا در دریافت جواب: {e}")
