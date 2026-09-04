import aiohttp
from urllib.parse import quote
from telethon import events
import core
from core import client

@client.on(events.NewMessage(outgoing=True, pattern=r'^هوش‌\s+(.+)$'))
async def ai_handler(event):
    prompt = event.pattern_match.group(1).strip()
    if not prompt:
        return await event.reply("❗ سوالی نپرسیدی! مثال: `هوش‌ آب پختن پلو چقدر طول میکشه؟`")
    
    # اضافه کردن درخواست برای جواب فارسی
    full_prompt = f"{prompt} - جواب را فقط به زبان فارسی و کوتاه بده"
    encoded_prompt = quote(full_prompt)
    
    # نشون دادن حالت تایپ کردن تا ربات جواب رو بیاره
    async with client.action(event.chat_id, 'typing'):
        try:
            # استفاده از متد GET سایت Pollinations با مدل رایگان mistral
            url = f"https://text.pollinations.ai/{encoded_prompt}?model=mistral&referrer=amir_bot"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=60) as resp:
                    if resp.status == 200:
                        answer = await resp.text()
                        if answer:
                            await event.reply(f"🤖 **پاسخ هوش مصنوعی:**\n\n{answer}")
                        else:
                            await event.reply("کیرم تو مغزت")
                    elif resp.status == 429:
                        await event.reply("⏳ کیرم تو مغزت ۲ هاها، .")
                    elif resp.status == 402:
                        await event.reply("💰 محدودیت رایگان پر شده، لطفا چند دقیقه دیگه امتحان کن.")
                    else:
                        await event.reply(f"❌ خطا در ارتباط با سرور. (کد: {resp.status})")
        except Exception as e:
            await event.reply(f"❌ خطا در دریافت جواب: {e}")
