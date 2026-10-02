import asyncio
from telethon import events
import core
from core import client

async def enemy_loop():
    """چرخه شلیک به دشمنان هر ۱۵ ثانیه یکبار"""
    while core.enemy_active:
        try:
            # Iterate over a copy of the dictionary
            for enemy_id, info in list(core.enemy_targets.items()):
                try:
                    entity = await client.get_entity(int(enemy_id))
                    common_chats = await client.get_common_chats(entity)
                    
                    shot_fired = False
                    for chat in common_chats:
                        try:
                            # Find the latest message from the enemy in this chat
                            async for msg in client.iter_messages(chat.id, from_user=entity.id, limit=1):
                                if msg:
                                    # Send "شلیک" as a reply
                                    shoot_msg = await client.send_message(chat.id, "شلیک", reply_to=msg.id)
                                    await asyncio.sleep(3) # wait 3 seconds
                                    await shoot_msg.delete() # delete the "شلیک" message
                                    shot_fired = True
                                    break # move to next enemy
                        except:
                            pass
                        
                        if shot_fired:
                            break # break the chat loop
                            
                except Exception as e:
                    print(f"Error shooting enemy {enemy_id}: {e}")
            
            # Wait 15 seconds for the next round
            await asyncio.sleep(15)
            
        except Exception as e:
            print(f"Enemy loop error: {e}")
            await asyncio.sleep(15)

@client.on(events.NewMessage(outgoing=True, pattern=r'^دشمن روشن$'))
async def enemy_on(event):
    if not core.enemy_active:
        core.enemy_active = True
        await core.save_db()
        await event.reply("🎯 سیستم دشمن روشن شد! در حال پاک کردن ۱۵۰ پیام آخر...")
        
        # Delete last 150 messages sent by me in this chat
        deleted_count = 0
        me = await client.get_me()
        async for msg in client.iter_messages(event.chat_id, from_user=me.id, limit=150):
            try:
                await msg.delete()
                deleted_count += 1
                await asyncio.sleep(0.1) # small delay to avoid flood
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
