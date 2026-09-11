from duckduckgo_search import AsyncDDGS
from telethon import events
import core

# 注册命令: هوش [متن]
@core.client.on(events.NewMessage(outgoing=True, pattern=r'^هوش (.+)$'))
async def ai_chat_handler(event):
    # گرفتن متن سوال کاربر
    question = event.pattern_match.group(1)
    
    # اول پیام رو ادیت می‌کنیم تا نشون بده در حال پردازشه
    processing_msg = await event.edit(f"🧠 در حال فکر کردن به سوال...\n\n**سوال:** {question}")
    
    try:
        # استفاده از هوش مصنوعی DuckDuckGo به صورت غیرهمزمان (Async)
        # می‌تونید مدل رو بین "gpt-4o-mini" یا "claude-3-haiku" یا "llama-3.1-70b" تغییر بدید
        async with AsyncDDGS() as ddgs:
            response = await ddgs.chat(question, model="gpt-4o-mini")
        
        # اگر هوش مصنوعی جوابی داد
        if response:
            final_answer = f"🤖 **پاسخ هوش مصنوعی:**\n\n{response}"
            await processing_msg.edit(final_answer)
        else:
            await processing_msg.edit("❌ هوش مصنوعی هیچ پاسخی برنگرداند.")
            
    except Exception as e:
        await processing_msg.edit(f"❌ خطا در ارتباط با هوش مصنوعی:\n`{e}`")
