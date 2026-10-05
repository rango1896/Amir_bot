import asyncio
import time
from telethon import events
import core
from core import client

# دیکشنری برای نگه داشتن زمان مرگ دشمن‌ها
dead_enemies = {}

async def send_debug(text):
    """ارسال لاگ‌های دیباگ به پیام‌های ذخیره شده"""
    print(f"🐞 DEBUG: {text}") 
    try:
        await client.send_message('me', f"🐞 **[دیباگ دشمن]**:\n\n{text}")
    except:
        pass

# --- سیستم شکارچی (برای شناسایی کسایی که با آیدی عددی اد شدن) ---
@client.on(events.NewMessage(incoming=True))
async def enemy_entity_catcher(event):
    if not core.enemy_active or not core.enemy_targets: return
    sender_id = str(event.sender_id)
    # اگه فرستنده پیام، تو لیست دشمن‌های ما بود و اسمش هنوز نامشخص بود
    if sender_id in core.enemy_targets:
        info = core.enemy_targets[sender_id]
        if "Unknown" in info['name'] or (not info.get('username') or info['username'] == "None"):
            # اسم و یوزرنیمش رو آپدیت می‌کنیم
            info['name'] = event.sender.first_name or "Unknown"
            info['username'] = event.sender.username or "None"
            await core.save_db()
            await send_debug(f"🎯 دشمن شناسایی شد: {info['name']} (@{info['username']})")

async def enemy_loop():
    """چرخه شلیک به دشمنان هر ۱۵ ثانیه یکبار"""
    while core.enemy_active:
        try:
            if not core.enemy_active_chat:
                await send_debug("گروه فعال مشخص نیست! (None). شاید ربات ری‌استارت شده. لطفا دوباره 'دشمن روشن' بزن.")
                await asyncio.sleep(15)
                continue
                
            if not core.enemy_targets:
                await send_debug("لیست دشمن‌ها خالیه! کسی برای شلیک وجود نداره.")
                await asyncio.sleep(15)
                continue
                
            current_time = time.time()
            
            # پاک کردن دشمن‌هایی که زمان مرگشون تموم شده
            for eid in list(dead_enemies.keys()):
                if current_time >= dead_enemies[eid]:
                    del dead_enemies[eid]
                    await send_debug("♻️ زمان مرگ یک دشمن تموم شد و دوباره هدف قرار گرفت.")
            
            for enemy_id, info in list(core.enemy_targets.items()):
                try:
                    # اگه دشمن مرده بود، از شلیک بهش می‌پریم
                    if enemy_id in dead_enemies:
                        continue
                        
                    # --- حل مشکل Entity --- 
                    entity = None
                    try:
                        if info.get('username') and info['username'] != "None":
                            entity = await client.get_entity(info['username'])
                        else:
                            entity = await client.get_entity(int(enemy_id))
                    except:
                        pass
                        
                    # پیدا کردن آخرین پیام شخص
                    target_msg = None
                    if entity:
                        # جستجوی سریع و عمیق (می‌تونه ۱۰۰۰۰ تا رو هم تو چند ثانیه بگرده)
                        async for msg in client.iter_messages(core.enemy_active_chat, from_user=entity, limit=1):
                            target_msg = msg
                            break
                    else:
                        # جستجوی دستی تو ۱۰۰۰ پیام اخیر (برای وقتی که با آیدی عددی اد شده و هنوز شناخته نشده)
                        async for msg in client.iter_messages(core.enemy_active_chat, limit=1000):
                            if str(msg.sender_id) == str(enemy_id):
                                target_msg = msg
                                break
                        
                    # شلیک و پاک کردن
                    if target_msg:
                        try:
                            shoot_msg = await client.send_message(core.enemy_active_chat, "شلیک", reply_to=target_msg.id)
                            await asyncio.sleep(1.5)
                            await shoot_msg.delete()
                            
                            # بررسی اینکه آیا دشمن کشته شده یا خیر
                            await asyncio.sleep(2)
                            recent_msgs = await client.get_messages(core.enemy_active_chat, limit=3)
                            is_dead = False
                            
                            for m in recent_msgs:
                                if m.text and info['name'] in m.text and ("مُرد" in m.text or "مرده" in m.text):
                                    is_dead = True
                                    break
                                    
                            if is_dead:
                                dead_enemies[enemy_id] = current_time + 600
                                await send_debug(f"☠️ {info['name']} مُرد!\nربات به مدت 10 دقیقه بهش شلیک نمی‌کنه.")
                        
                        except Exception as shoot_err:
                            await send_debug(f"❌ خطا در شلیک به {info['name']}:\n`{shoot_err}`")
                    else:
                        await send_debug(f"⚠️ پیامی برای {info['name']} تو گروه پیدا نشد. صبر می‌کنم تا پیام بده.")
                        
                except Exception as e:
                    await send_debug(f"❌ خطای کلی در پردازش دشمن {enemy_id}:\n`{e}`")
                    
            await asyncio.sleep(15)
            
        except Exception as e:
            await send_debug(f"❌ خطای اصلی در چرخه دشمن (خارج از حلقه):\n`{e}`")
            await asyncio.sleep(15)

@client.on(events.NewMessage(outgoing=True, pattern=r'^دشمن روشن$'))
async def enemy_on(event):
    if not core.enemy_active:
        core.enemy_active = True
        core.enemy_active_chat = event.chat_id
        await core.save_db()
        
        start_msg = await event.reply("🎯 سیستم دشمن تو همین گروه روشن شد!\nدر حال پاک کردن ۱۵۰ پیام آخر شما...")
        
        deleted_count = 0
        me = await client.get_me()
        async for msg in client.iter_messages(event.chat_id, from_user=me.id, limit=150):
            try:
                await msg.delete()
                deleted_count += 1
                await asyncio.sleep(0.2)
            except:
                pass
                
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
        
        core.enemy_targets[eid_str] = {
            "name": entity.first_name or "Unknown",
            "username": entity.username or "None"
        }
        await core.save_db()
        await event.reply(f"✅ {entity.first_name} به لیست دشمن اضافه شد.")
        
    except Exception as e:
        if target.lstrip('-').isdigit():
            eid_str = target
            core.enemy_targets[eid_str] = {
                "name": "Unknown (Added by ID)",
                "username": "None"
            }
            await core.save_db()
            await event.reply(f"✅ آیدی `{target}` به لیست دشمن اضافه شد.\n⚠️ *نکته: ربات منتظر می‌مونه تا اون شخص تو هر گروهی پیام بده، به محض پیام دادن، شناخته‌ش می‌کنه و شلیک رو شروع می‌کنه.*")
        else:
            await event.reply(f"❌ پیدا نشد. مطمئن شو یوزرنیم درسته.\n`{e}`")

@client.on(events.NewMessage(outgoing=True, pattern=r'^پیو حذف دشمن (.+)$'))
async def remove_enemy(event):
    target = event.pattern_match.group(1).strip()
    try:
        entity = await client.get_entity(target)
        eid_str = str(entity.id)
    except:
        eid_str = target if target.lstrip('-').isdigit() else None
        
    if eid_str and eid_str in core.enemy_targets:
        del core.enemy_targets[eid_str]
        await core.save_db()
        await event.reply(f"🗑 دشمن با آیدی `{eid_str}` از لیست حذف شد.")
    else:
        await event.reply("❗ این شخص تو لیست دشمن نبود.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^لیست دشمن$'))
async def list_enemies(event):
    if not core.enemy_targets:
        await event.reply("📭 لیست دشمن خالیه.")
        return
        
    text = "🎯 **لیست دشمنان:**\n\n"
    for eid, info in core.enemy_targets.items():
        text += f"👤 {info['name']}\n└─ یوزر: @{info['username']}\n└─ آیدی: `{eid}`\n\n"
        
    await event.reply(text)
