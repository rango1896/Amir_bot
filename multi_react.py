import asyncio
import re
from telethon import TelegramClient, events
from telethon.tl.functions.messages import SendReactionRequest
from telethon.tl.types import ReactionEmoji
import core
from core import client as client1

# --- ساخت سشن‌های رفیقات از پوشه react_sessions ---
client2 = TelegramClient('react_sessions/friend2_session', core.API_ID, core.API_HASH)
client3 = TelegramClient('react_sessions/friend3_session', core.API_ID, core.API_HASH)
client4 = TelegramClient('react_sessions/friendAmir_session', core.API_ID, core.API_HASH)

multi_clients = [client1, client2, client3, client4]
multi_react_active = False
react_task = None
last_msg_id = 0

async def start_multi_clients():
    if not client2.is_connected(): await client2.start()
    if not client3.is_connected(): await client3.start()
    if not client4.is_connected(): await client4.start()
    print("✅ تمام ۴ سشن برای واکنش عمومی متصل شدند.")

def extract_username(link):
    if "t.me/c/" in link: return None # یعنی گروه خصوصیه
    parts = link.split("t.me/")[-1].split("/")
    return parts[0] if parts[0] else None

@client1.on(events.NewMessage(outgoing=True, pattern=r'^واکنش عمومی\s+(\S+)\s+(\S+)$'))
async def add_multi_react(event):
    global multi_react_active, react_task, last_msg_id
    link = event.pattern_match.group(1)
    emoji = event.pattern_match.group(2)
    
    username = extract_username(link)
    if not username:
        return await event.reply("❗ این لینک مال گروه خصوصیه! توی گروه‌های خصوصی نمیشه بدون عضو شدن واکنش زد. لطفا لینک کانال/گروه عمومی بده.")
        
    multi_react_active = True
    last_msg_id = 0
    if react_task and not react_task.done(): react_task.cancel()
    
    await start_multi_clients()
    react_task = asyncio.create_task(poll_and_react_loop(username, emoji))
    await event.reply(f"✅ واکنش عمومی {emoji} برای `{username}` فعال شد. (۴ اکانت همزمان واکنش میدن بدون عضو شدن)")

@client1.on(events.NewMessage(outgoing=True, pattern=r'^حذف واکنش عمومی$'))
async def remove_multi_react(event):
    global multi_react_active, react_task
    multi_react_active = False
    if react_task and not react_task.done(): react_task.cancel()
    await event.reply("🛑 واکنش عمومی متوقف شد.")

async def poll_and_react_loop(username, emoji):
    global last_msg_id
    try:
        entity = await client1.get_entity(username)
        # گرفتن آخرین پست برای اینکه روی پست‌های قدیمی واکنش نزنه
        msgs = await client1.get_messages(entity, limit=1)
        if msgs: last_msg_id = msgs[0].id
    except Exception as e:
        print(f"❌ خطا در پیدا کردن کانال: {e}")
        return

    while multi_react_active:
        try:
            msgs = await client1.get_messages(entity, limit=1)
            if msgs and msgs[0].id > last_msg_id:
                last_msg_id = msgs[0].id
                print(f"🔔 پست جدید در {username}! ۴ اکانت در حال واکنش...")
                
                for c in multi_clients:
                    try:
                        await c(SendReactionRequest(peer=entity, msg_id=last_msg_id, reaction=[ReactionEmoji(emoticon=emoji)]))
                    except Exception as e:
                        print(f"خطا در واکنش یه اکانت: {e}")
        except Exception as e:
            print(f"خطا در چک کردن کانال: {e}")
            
        await asyncio.sleep(5) # هر ۵ ثانیه یه بار چک میکنه
