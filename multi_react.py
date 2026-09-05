import asyncio
from telethon import TelegramClient, events
from telethon.tl.functions.messages import SendReactionRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import ReactionEmoji
import core
from core import client as client1

# --- ساخت سشن‌های رفیقات از پوشه react_sessions ---
client2 = TelegramClient('react_sessions/friend2_session', core.API_ID, core.API_HASH)
client3 = TelegramClient('react_sessions/friend3_session', core.API_ID, core.API_HASH)
client4 = TelegramClient('react_sessions/friendAmir_session', core.API_ID, core.API_HASH)

multi_clients = [client1, client2, client3, client4]

# متغیرهای واکنش عمومی
multi_react_chat_id = None
multi_react_emoji = None

async def start_multi_clients():
    if not client2.is_connected(): await client2.start()
    if not client3.is_connected(): await client3.start()
    if not client4.is_connected(): await client4.start()
    print("✅ تمام ۴ سشن برای واکنش عمومی متصل شدند.")

@client1.on(events.NewMessage(outgoing=True, pattern=r'^اد واکنش عمومی\s+(\S+)\s+(\S+)$'))
async def add_multi_react(event):
    global multi_react_chat_id, multi_react_emoji
    link = event.pattern_match.group(1)
    emoji = event.pattern_match.group(2)
    
    try:
        # پیدا کردن آیدی گروه/کانال
        if "t.me/c/" in link:
            parts = link.split("t.me/c/")[-1].split("/")
            if len(parts) == 2 and parts[0].isdigit():
                entity = await client1.get_entity(int("-100" + parts[0]))
            else:
                return await event.reply("❗ لینک گروه خصوصی اشتباه است.")
        else:
            username = link.split("t.me/")[-1].split("/")[0]
            entity = await client1.get_entity(username)
            
        # عضو شدن سشن خودمون (client1) تو کانال/گروه
        try:
            await client1(JoinChannelRequest(entity))
            print(f"✅ سشن شما عضو {entity.title} شد.")
        except Exception as e:
            print(f"عضو شدن انجام نشد (شاید قبلا عضو بوده‌اید): {e}")

        multi_react_chat_id = entity.id
        multi_react_emoji = emoji
        
        await start_multi_clients()
        await event.reply(f"✅ واکنش عمومی {emoji} فعال شد.\nسشن شما عضو شد و منتظر میمونه تا پست جدید بیاد، بعدش بقیه سشن‌ها رو خبر می‌کنه.")
    except Exception as e:
        await event.reply(f"❗ خطا در ثبت لینک: {e}")

@client1.on(events.NewMessage(outgoing=True, pattern=r'^اد حذف واکنش عمومی$'))
async def remove_multi_react(event):
    global multi_react_chat_id, multi_react_emoji
    multi_react_chat_id = None
    multi_react_emoji = None
    await event.reply("🛑 واکنش عمومی متوقف شد.")

@client1.on(events.NewMessage(incoming=True))
async def multi_react_listener(event):
    # اگه واکنش عمومی روشن بود و پیام از کانال هدف اومد
    if multi_react_chat_id and event.chat_id == multi_react_chat_id and multi_react_emoji:
        try:
            # ۱. اول سشن خودمون واکنش میده
            await client1(SendReactionRequest(peer=event.input_chat, msg_id=event.id, reaction=[ReactionEmoji(emoticon=multi_react_emoji)]))
            
            # ۲. بعد بقیه سشن‌ها رو خبر می‌کنیم که بیان و واکنش بزنن
            for c in [client2, client3, client4]:
                try:
                    await c(SendReactionRequest(peer=event.input_chat, msg_id=event.id, reaction=[ReactionEmoji(emoticon=multi_react_emoji)]))
                except Exception as e:
                    print(f"خطا در واکنش سشن رفیق: {e}")
        except Exception as e:
            print(f"خطا در واکنش عمومی: {e}")
