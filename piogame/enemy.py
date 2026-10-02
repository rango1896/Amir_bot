import asyncio
from telethon import events
import core
from core import client

# متغیر برای نگه داشتن آیدی گروهی که دشمن در اون فعال شده
enemy_active_chat = None

async def enemy_loop():
    """چرخه شلیک به دشمنان هر ۱۵ ثانیه یکبار در گروه فعلی"""
    global enemy_active_chat
    while core.enemy_active:
        try:
            if not enemy_active_chat:
                await asyncio.sleep(5)
                continue
                
            for enemy_id, info in list(core.enemy_targets.items()):
                try:
                    entity = await client.get_entity(int(enemy_id))
                    
                    # پیدا کردن آخرین پیام دشمن در همون گروهی که روشن شده
                    target_msg = None
                    async for msg in client.iter_messages(enemy_active_chat, from_user=entity.id, limit=1):
                        target_msg = msg
                        break
                        
                    if target_msg:
                        # شلیک و پاک کردن
                        shoot_msg = await client.send_message(enemy_active_chat, "شلیک", reply_to=target_msg.id)
                        await asyncio.sleep(3)
                        await shoot_msg.delete()
                        print(f"✅ شلیک به {info['name']} انجام شد.")
                    else:
                        print(f"⚠️ پیامی برای {info['name']} تو گروه پیدا نشد.")
                        
                except Exception as e:
                    print(f"❌ خطا در شلیک به دشمن {enemy_id}: {e}")
                    
            # ۱۵ ثانیه صبر
            await asyncio.sleep(15)
            
        except Exception as e:
            print(f"❌ Enemy loop error: {e}")
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
