import os
from telethon import events
import core
from core import client

async def steal_and_send(target_msg, event):
    """تابع اصلی برای دزدیدن پیام و فرستادن به Saved Messages"""
    if not target_msg:
        return await event.reply("❗ پیامی پیدا نشد.")
    try:
        # پاک کردن دستور "دزدی" تا چت شلوغ نشه
        await event.delete()
        
        sender_name = "ناشناس"
        if target_msg.sender:
            sender_name = getattr(target_msg.sender, 'first_name', None) or getattr(target_msg.sender, 'title', None) or "ناشناس"
            
        caption = f"🥷 **دزدی شد!**\n👤 فرستنده: {sender_name}"
        
        # ۱. اگه پیام فایل/عکس/استیکر/ویس داشت (دانلود واقعی و آپلود مجدد برای دور زدن قفل)
        if target_msg.media:
            # فایل رو تو حافظه موقت سرور دانلود می‌کنه
            file_path = await client.download_media(target_msg.media)
            if file_path:
                # فایل رو به صورت یه پیام جدید می‌فرسته
                await client.send_file('me', file=file_path, caption=caption)
                # فایل رو از حافظه پاک می‌کنه تا سرور شلوغ نشه
                if os.path.exists(file_path):
                    os.remove(file_path)
            else:
                await event.reply("❗ فایل قابل دانلود نیست.")
            
        # ۲. اگه پیام فقط متن داشت
        elif target_msg.text:
            text_to_send = f"{caption}\n\n💬 متن:\n{target_msg.text}"
            await client.send_message('me', text_to_send)
            
        else:
            await client.send_message('me', "❗ این پیام هیچ متن یا فایلی نداره.")
            
    except Exception as e:
        await event.reply(f"❌ خطا در دزدی: {e}")

# --- حالت اول: دزدی با ریپلای ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^دزدی$'))
async def steal_reply(event):
    if not event.message.is_reply:
        return await event.reply("❗ روی یه پیام ریپلای کن یا لینکش رو بده!")
    
    replied_msg = await event.message.get_reply_message()
    await steal_and_send(replied_msg, event)

# --- حالت دوم: دزدی با لینک ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^دزدی\s+(https?://t\.me/.+)$'))
async def steal_link(event):
    link = event.pattern_match.group(1)
    try:
        # تشخیص نوع لینک (گروه خصوصی یا کانال/گروه عمومی)
        if "t.me/c/" in link:
            parts = link.split("t.me/c/")[-1].split("/")
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                chat_id = int("-100" + parts[0])
                msg_id = int(parts[1])
                entity = await client.get_entity(chat_id)
            else:
                return await event.reply("❗ فرمت لینک خصوصی اشتباه است.")
        else:
            parts = link.split("t.me/")[-1].split("/")
            if len(parts) >= 2 and parts[1].isdigit():
                username = parts[0]
                msg_id = int(parts[1])
                entity = await client.get_entity(username)
            else:
                return await event.reply("❗ فرمت لینک عمومی اشتباه است.")
                
        # گرفتن پیام از آیدی
        target_msg = await client.get_messages(entity, ids=msg_id)
        await steal_and_send(target_msg, event)
        
    except Exception as e:
        await event.reply(f"❌ خطا در گرفتن پیام از لینک: {e}")
