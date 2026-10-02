import asyncio
from telethon import events
import core
from core import client

# متغیر برای نگه داشتن آیدی گروهی که دشمن در اون فعال شده
enemy_active_chat = None

async def send_debug(text):
    """ارسال لاگ‌های دیباگ به پیام‌های ذخیره شده"""
    print(f"🐞 DEBUG: {text}") # پرینت تو کنسول رندر
    try:
        await client.send_message('me', f"🐞 **[دیباگ دشمن]**:\n\n{text}")
    except:
        pass

async def enemy_loop():
    """چرخه شلیک به دشمنان هر ۱۵ ثانیه یکبار در گروه فعلی"""
    global enemy_active_chat
    while core.enemy_active:
        try:
            if not enemy_active_chat:
                await send_debug("گروه فعال مشخص نیست! (None). شاید ربات ری‌استارت شده. لطفا دوباره 'دشمن روشن' بزن.")
                await asyncio.sleep(15)
                continue
                
            if not core.enemy_targets:
                await send_debug("لیست دشمن‌ها خالیه! کسی برای شلیک وجود نداره.")
                await asyncio.sleep(15)
                continue
                
            for enemy_id, info in list(core.enemy_targets.items()):
                try:
                    # ۱. پیدا کردن شخص
                    entity = await client.get_entity(int(enemy_id))
                    
                    # ۲. پیدا کردن آخرین پیام شخص تو گروه
                    target_msg = None
                    try:
                        async for msg in client.iter_messages(enemy_active_chat, from_user=entity, limit=1):
                            target_msg = msg
                            break
                    except Exception as search_err:
                        await send_debug(f"❌ خطا در جستجوی پیام {info['name']}:\n`{search_err}`")
                        continue
                        
                    # ۳. شلیک و پاک کردن
                    if target_msg:
                        try:
                            shoot_msg = await client.send_message(enemy_active_chat, "شلیک", reply_to=target_msg.id)
                            await asyncio.sleep(3)
                            await shoot_msg.delete()
                            # پیام موفقیت رو فقط تو کنسول میدیم که Saved Messages اسپم نشه
                            print(f"✅ شلیک به {info['name']} انجام شد.") 
                        except Exception as shoot_err:
                            await send_debug(f"❌ خطا در ارسال/پاک کردن شلیک به {info['name']}:\n`{shoot_err}`")
                    else:
                        await send_debug(f"⚠️ پیامی برای {info['name']} تو گروه پیدا نشد. (شاید اخیراً پیام نداده)")
                        
                except Exception as e:
                    await send_debug(f"❌ خطای کلی در پردازش دشمن {enemy_id}:\n`{e}`")
                    
            # ۱۵ ثانیه صبر
            await asyncio.sleep(15)
            
        except Exception as e:
            await send_debug(f"❌ خطای اصلی در چرخه دشمن (خارج از حلقه):\n`{e}`")
            await asyncio.sleep(15)

@client.on(events.NewMessage(outgoing=True, pattern=r'^دشمن روشن$'))
async def enemy_on(event):
    global enemy_active_chat
    if not core.enemy_active:
        core.enemy_active = True
        # ذخیره گروهی که توش دستور داده شد
        enemy_active_chat = event.chat_id
        await core.save_db()
        
        await event.reply("🎯 سیستم دشمن تو همین گروه روشن شد!\nدر حال پاک کردن ۱۵۰ پیام آخر شما...")
        
        # پاک کردن ۱۵۰ پیام آخر شما
        deleted_count = 0
        me = await client.get_me()
        async for msg in client.iter_messages(event.chat_id, from_user=me.id, limit=150):
            try:
                await msg.delete()
                deleted_count += 1
                await asyncio.sleep(0.2)
            except:
                pass
                
        await event.reply(f"✅ {deleted_count} پیام پاک شد. شلیک به دشمنان شروع شد!")
        asyncio.create_task(enemy_loop())
    else:
        await event.reply("❗ سیستم دشمن از قبل روشنه.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^دشمن خاموش$'))
async def enemy_off(event):
    core.enemy_active = False
    await core.save_db()
    await event.reply("🛑 سیستم دشمن خاموش شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^پیو دشمن (.+)$'))
async def add_enemy(event):
    target = event.pattern_match.group(1).strip()
    try:
        entity = await client.get_entity(target)
        eid_str = str(entity.id)
        
        if eid_str in core.enemy_targets:
            await event.reply(f"❗ {entity.first_name} از قبل تو لیست دشمناست.")
            return
            
        core.enemy_targets[eid_str] = {
            "name": entity.first_name or "Unknown",
            "username": entity.username or "None"
        }
        await core.save_db()
        await event.reply(f"✅ {entity.first_name} به لیست دشمن اضافه شد.")
    except Exception as e:
        await event.reply(f"❌ پیدا نشد. مطمئن شو آیدی یا یوزرنیم درسته.\n`{e}`")

@client.on(events.NewMessage(outgoing=True, pattern=r'^پیو حذف دشمن (.+)$'))
async def remove_enemy(event):
    target = event.pattern_match.group(1).strip()
    try:
        entity = await client.get_entity(target)
        eid_str = str(entity.id)
        
        if eid_str in core.enemy_targets:
            del core.enemy_targets[eid_str]
            await core.save_db()
            await event.reply(f"🗑 {entity.first_name} از لیست دشمن حذف شد.")
        else:
            await event.reply("❗ این شخص تو لیست دشمن نبود.")
    except Exception as e:
        await event.reply(f"❌ پیدا نشد.\n`{e}`")

@client.on(events.NewMessage(outgoing=True, pattern=r'^لیست دشمن$'))
async def list_enemies(event):
    if not core.enemy_targets:
        await event.reply("📭 لیست دشمن خالیه.")
        return
        
    text = "🎯 **لیست دشمنان:**\n\n"
    for eid, info in core.enemy_targets.items():
        text += f"👤 {info['name']}\n└─ یوزر: @{info['username']}\n└─ آیدی: `{eid}`\n\n"
        
    await event.reply(text)
