import asyncio
import time
from telethon import events
import core
from core import client

# متغیر برای نگه داشتن آیدی گروهی که دشمن در اون فعال شده
enemy_active_chat = None

# دیکشنری برای نگه داشتن زمان مرگ دشمن‌ها (enemy_id: timestamp)
dead_enemies = {}

async def send_debug(text):
    """ارسال لاگ‌های دیباگ به پیام‌های ذخیره شده"""
    print(f"🐞 DEBUG: {text}") 
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
                
            current_time = time.time()
            
            # پاک کردن دشمن‌هایی که زمان مرگشون تموم شده از لیست مرده‌ها
            for eid in list(dead_enemies.keys()):
                if current_time >= dead_enemies[eid]:
                    del dead_enemies[eid]
                    await send_debug(f"♻️ زمان مرگ یک دشمن تموم شد و دوباره هدف قرار گرفت.")
            
            for enemy_id, info in list(core.enemy_targets.items()):
                try:
                    # اگه دشمن مرده بود، از شلیک بهش می‌پریم
                    if enemy_id in dead_enemies:
                        continue
                        
                    entity = await client.get_entity(int(enemy_id))
                    
                    # پیدا کردن آخرین پیام شخص تو گروه
                    target_msg = None
                    try:
                        async for msg in client.iter_messages(enemy_active_chat, from_user=entity, limit=1):
                            target_msg = msg
                            break
                    except Exception as search_err:
                        await send_debug(f"❌ خطا در جستجوی پیام {info['name']}:\n`{search_err}`")
                        continue
                        
                    # شلیک و پاک کردن
                    if target_msg:
                        try:
                            shoot_msg = await client.send_message(enemy_active_chat, "شلیک", reply_to=target_msg.id)
                            await asyncio.sleep(1.5) # تغییر زمان به 1.5 ثانیه
                            await shoot_msg.delete()
                            
                            # بررسی اینکه آیا دشمن کشته شده یا خیر (چک کردن ۳ پیام اخیر)
                            await asyncio.sleep(2) # کمی صبر تا ربات بازی جواب بده
                            recent_msgs = await client.get_messages(enemy_active_chat, limit=3)
                            is_dead = False
                            
                            for m in recent_msgs:
                                if m.text and info['name'] in m.text and ("مُرد" in m.text or "مرده" in m.text):
                                    is_dead = True
                                    break
                                    
                            if is_dead:
                                # ثبت زمان ۱۰ دقیقه (۶۰۰ ثانیه) برای این دشمن
                                dead_enemies[enemy_id] = current_time + 600
                                await send_debug(f"☠️ {info['name']} مُرد!\nربات به مدت 10 دقیقه بهش شلیک نمی‌کنه.")
                        
                        except Exception as shoot_err:
                            await send_debug(f"❌ خطا در ارسال/پاک کردن شلیک به {info['name']}:\n`{shoot_err}`")
                    else:
                        # پیامی برای شلیک پیدا نشده بود، صبر می‌کنیم تا پیام بده
                        pass
                        
                except Exception as e:
                    await send_debug(f"❌ خطای کلی در پردازش دشمن {enemy_id}:\n`{e}`")
                    
            # ۱۵ ثانیه صبر (طبق درخواست اولیه شما)
            await asyncio.sleep(15)
            
        except Exception as e:
            await send_debug(f"❌ خطای اصلی در چرخه دشمن (خارج از حلقه):\n`{e}`")
            await asyncio.sleep(15)

@client.on(events.NewMessage(outgoing=True, pattern=r'^دشمن روشن$'))
async def enemy_on(event):
    global enemy_active_chat
    if not core.enemy_active:
        core.enemy_active = True
        enemy_active_chat = event.chat_id
        await core.save_db()
        
        start_msg = await event.reply("🎯 سیستم دشمن تو همین گروه روشن شد!\nدر حال پاک کردن ۱۵۰ پیام آخر شما...")
        
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
                
        # پاک کردن پیام استارت و پیام موفقیت
        success_msg = await event.reply(f"✅ {deleted_count} پیام پاک شد. شلیک به دشمنان شروع شد!")
        await asyncio.sleep(2)
        await success_msg.delete()
        await start_msg.delete()
        
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
