import asyncio
import time
import re
from telethon import events, utils
import core
from core import client

# === متغیرهای شلیک ===
ammo_counter = 0
ammo_limit = 9
piou_active = False
piou_shoot_active = True
last_meat_time = 0
shoot_interval = 30
skip_next_heal = False

# === متغیرهای هوشمند و بانداژ ===
smart_active = False
refill_active = True
is_in_death_state = False
current_task = None
dead_targets_timers = {} # دفترچه زمان زنده شدن مرده‌ها

# === تابع دیباگ برای ارسال لاگ به پیام‌های ذخیره شده ===
async def log_debug(text):
    try:
        print(f"🐞 DEBUG: {text}")
        await client.send_message('me', f"🐞 **[دیباگ پیو]**:\n\n{text}")
    except:
        pass

def parse_time_from_text(text):
    text = core.fa_to_en_digits(text)
    seconds = 0
    match_min = re.search(r'تا\s*(\d+)\s*دقیق', text)
    match_sec = re.search(r'تا\s*(\d+)\s*ثانی', text)
    if match_min: seconds += int(match_min.group(1)) * 60
    if match_sec: seconds += int(match_sec.group(1))
    return seconds

# === تابع پیدا کردن نفر زنده بعدی ===
async def find_next_alive_target():
    for i in range(len(core.pio_target_links)):
        idx = (core.pio_active_link_index + 1 + i) % len(core.pio_target_links)
        if time.time() >= dead_targets_timers.get(idx, 0):
            return idx
    return None # همه مرده‌ن

# --- دستورات تنظیمات ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^تنظیم تیر\s+(\d+)$'))
async def set_ammo_limit(event):
    global ammo_limit
    ammo_limit = int(event.pattern_match.group(1))
    await event.reply(f"✅ تنظیمات خرید مهمات تغییر کرد. هر {ammo_limit} شلیک، یک خرید مهمات.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^تنظیم زمان شلیک\s+(\d+)$'))
async def set_shoot_interval(event):
    global shoot_interval
    shoot_interval = int(event.pattern_match.group(1))
    await event.reply(f"✅ زمان‌بندی شلیک تغییر شد. هر {shoot_interval} ثانیه یک‌بار شلیک.")

# --- دستورات لیست و گروه (پشتیبانی از چند لینک) ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^اد لینک\s+(.+)$'))
async def add_link(event):
    if not isinstance(core.pio_target_links, list):
        core.pio_target_links = []
        
    links_str = event.pattern_match.group(1)
    links_list = links_str.split()
    added_count = 0
    for link in links_list:
        try:
            if "t.me/c/" in link:
                parts = link.split("t.me/c/")[-1].split("/")
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    g_id = int("-100" + parts[0]); m_id = int(parts[1])
                    if not core.pio_active_group: core.pio_active_group = g_id
                    core.pio_target_links.append({"g_id": g_id, "m_id": m_id})
                    added_count += 1
                else:
                    await event.reply(f"❗ فرمت این لینک اشتباه است: {link}")
            else:
                parts = link.split("t.me/")[-1].split("/")
                if len(parts) == 2:
                    ent = await client.get_entity(parts[0])
                    g_id = utils.get_peer_id(ent); m_id = int(parts[1])
                    if not core.pio_active_group: core.pio_active_group = g_id
                    core.pio_target_links.append({"g_id": g_id, "m_id": m_id})
                    added_count += 1
                else:
                    await event.reply(f"❗ فرمت این لینک اشتباه است: {link}")
        except Exception as e:
            await event.reply(f"❗ خطا در ثبت لینک {link}:\n`{e}`")
            
    if added_count > 0:
        core.pio_active_link_index = 0
        await core.save_pio_db()
        await event.reply(f"✅ {added_count} لینک ثبت شد.")

# --- دستورات حذف لینک ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^حذف لینک پیام\s+(.+)$'))
async def remove_single_link(event):
    link = event.pattern_match.group(1).strip()
    try:
        target_dict = None
        if "t.me/c/" in link:
            parts = link.split("t.me/c/")[-1].split("/")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                g_id = int("-100" + parts[0]); m_id = int(parts[1])
                target_dict = {"g_id": g_id, "m_id": m_id}
        else:
            parts = link.split("t.me/")[-1].split("/")
            if len(parts) == 2:
                ent = await client.get_entity(parts[0])
                g_id = utils.get_peer_id(ent); m_id = int(parts[1])
                target_dict = {"g_id": g_id, "m_id": m_id}

        if not target_dict:
            return await event.reply("❗ فرمت لینک اشتباه است.")

        if target_dict in core.pio_target_links:
            idx_removed = core.pio_target_links.index(target_dict)
            core.pio_target_links.remove(target_dict)
            
            if not core.pio_target_links:
                core.pio_active_link_index = 0
                core.pio_active_group = None
            elif idx_removed < core.pio_active_link_index:
                core.pio_active_link_index -= 1
            elif idx_removed == core.pio_active_link_index:
                core.pio_active_link_index = core.pio_active_link_index % len(core.pio_target_links)
                
            await core.save_pio_db()
            await event.reply("✅ لینک مورد نظر با موفقیت حذف شد.")
        else:
            await event.reply("❗ این لینک تو لیست وجود نداره.")
    except Exception as e:
        await event.reply(f"❗ خطا در حذف لینک:\n`{e}`")

@client.on(events.NewMessage(outgoing=True, pattern=r'^حذف لینک همه$'))
async def remove_all_links(event):
    core.pio_target_links.clear()
    core.pio_active_link_index = 0
    core.pio_active_group = None
    await core.save_pio_db()
    await event.reply("✅ تمام لینک‌ها پاک شدند.")

# --- دستورات گروه ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^اد گروه\s+(.+)$'))
async def add_group(event):
    g_str = event.pattern_match.group(1)
    try:
        g_id = int(g_str) if g_str.lstrip('-').isdigit() else utils.get_peer_id(await client.get_entity(g_str))
        core.pio_active_group = g_id
        await core.save_pio_db()
        await event.reply(f"✅ گروه فعال شد.")
    except: await event.reply("❗ گروه پیدا نشد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^حذف اد گروه$'))
async def remove_group(event):
    core.pio_target_links.clear()
    core.pio_active_group = None
    await core.save_pio_db()
    await event.reply("✅ گروه فعلی حذف شد.")

# --- شنود پیام‌های ربات بازی ---
@client.on(events.NewMessage(incoming=True))
async def game_listener(event):
    global is_in_death_state, dead_targets_timers, current_task, smart_active, skip_next_heal
    
    if not core.pio_active_group or event.chat_id != core.pio_active_group: return
    text = event.message.text or ""
    
    # ۱. تشخیص خون پر
    if "نیازی به هیل نیست" in text and "کامله" in text:
        skip_next_heal = True
        return

    # ۲. تشخیص پیام‌های مرگ
    is_dead = False
    revive_time = 0
    
    if ("مرده" in text and "نمی‌شه درمانش کرد" in text) or \
       ("همین الان مرده" in text and "زنده نمی‌شه" in text) or \
       ("مُرد" in text and "مرده می‌مونه" in text):
        is_dead = True
        revive_time = parse_time_from_text(text)
        
    if is_dead and smart_active:
        # همیشه زمان مرگ رو ثبت می‌کنه، حتی وسط حالت مرگ
        dead_targets_timers[core.pio_active_link_index] = time.time() + revive_time
        await log_debug(f"⚠️ نفر شماره {core.pio_active_link_index} مرده شد!\nزمان زنده شدن: {revive_time} ثانیه.")
        # اگه تو حالت مرگ نیست، موتور مرگ رو روشن کن
        if not is_in_death_state:
            if current_task is None or current_task.done():
                current_task = asyncio.create_task(death_cycle_task())

# --- موتور اصلی حالت مرگ ---
async def death_cycle_task():
    global is_in_death_state, piou_shoot_active, ammo_counter
    is_in_death_state = True
    piou_shoot_active = False
    
    try:
        # ۱. ارسال پیو من و چک کردن بانداژها
        my_msg = await client.send_message(core.pio_active_group, "پیو من")
        await asyncio.sleep(2)
        bandages = 0
        msgs = await client.get_messages(core.pio_active_group, reply_to=my_msg.id, limit=1)
        if msgs and msgs[0].text:
            b_match = re.search(r'کمک اولیه.*?(\d+)\s*/\s*\d+', msgs[0].text)
            if b_match: bandages = int(b_match.group(1))
            
        await log_debug(f"📊 تعداد بانداژهای شما: {bandages} تا پیدا شد.")
        
        # ۲. شلیک با بانداژها به نفر بعدی
        shots_done = 0
        while shots_done < bandages:
            next_idx = await find_next_alive_target()
            
            # اگه همه مرده‌ن! (پیدا کردن کمترین زمان)
            if next_idx is None:
                valid_timers = {k: v for k, v in dead_targets_timers.items() if v > time.time()}
                if valid_timers:
                    min_time = min(valid_timers.values())
                    wait_time = min_time - time.time()
                    target_idx = [k for k, v in valid_timers.items() if v == min_time][0]
                    if wait_time > 0:
                        await log_debug(f"⏳ همه مرده‌ن! ربات {wait_time} ثانیه استراحت می‌کنه تا نفر شماره {target_idx} زاده بشه.")
                        await asyncio.sleep(wait_time)
                    core.pio_active_link_index = target_idx
                    await core.save_pio_db()
                    if target_idx in dead_targets_timers: del dead_targets_timers[target_idx]
                else:
                    await asyncio.sleep(5)
            else:
                core.pio_active_link_index = next_idx
                await core.save_pio_db()

            # شلیک به نفر پیدا شده
            target = core.pio_target_links[core.pio_active_link_index]
            g_id = target["g_id"]; m_id = target["m_id"]
            
            await client.send_message(g_id, "شلیک", reply_to=m_id); ammo_counter += 1; shots_done += 1
            
            if not skip_next_heal:
                await asyncio.sleep(2)
                await client.send_message(g_id, "پیو هیل", reply_to=m_id)
            else:
                skip_next_heal = False
                await asyncio.sleep(1)
                
            if ammo_counter % ammo_limit == 0: await client.send_message(g_id, "خرید مهمات", reply_to=m_id)
            
            if time.time() >= core.next_shoot_time:
                core.next_shoot_time = time.time() + shoot_interval
                
            await log_debug(f"🔫 شلیک {shots_done} از {bandages} به نفر شماره {core.pio_active_link_index} انجام شد.")
            
        # ۳. بررسی نهایی قبل از استراحت ۴ دقیقه
        next_idx = await find_next_alive_target()
        if next_idx is None:
            # اگه بعد از تموم شدن بانداژها همه هنوز مرده‌ن، معطل شارژ شدن نمیشیم و میریم سراغ زمان زنده شدن
            valid_timers = {k: v for k, v in dead_targets_timers.items() if v > time.time()}
            if valid_timers:
                min_time = min(valid_timers.values())
                wait_time = min_time - time.time()
                target_idx = [k for k, v in valid_timers.items() if v == min_time][0]
                if wait_time > 0:
                    await log_debug(f"⏳ بانداژها تموم شد و همه مرده‌ن! ربات {wait_time} ثانیه استراحت می‌کنه.")
                    await asyncio.sleep(wait_time)
                core.pio_active_link_index = target_idx
                await core.save_pio_db()
                if target_idx in dead_targets_timers: del dead_targets_timers[target_idx]
            else:
                await log_debug("⏳ ۴ دقیقه استراحت برای شارژ بانداژ...")
                await asyncio.sleep(240)
        else:
            await log_debug("⏳ ۴ دقیقه استراحت برای شارژ بانداژ...")
            await asyncio.sleep(240)
        
    except asyncio.CancelledError:
        pass
    except Exception as e:
        await log_debug(f"❌ خطا در چرخه مرگ:\n`{e}`")
    finally:
        is_in_death_state = False
        piou_shoot_active = True
        await log_debug("✅ حالت مرگ پایان یافت. شلیک عادی از سر گرفته شد.")

# --- لوپ‌های پس‌زمینه ---
async def meat_loop():
    global last_meat_time
    while True:
        if piou_active and core.pio_active_group and (time.time() - last_meat_time >= 1800):
            try: await client.send_message(core.pio_active_group, "🥩"); last_meat_time = time.time()
            except: pass
        await asyncio.sleep(5)

async def blind_shot_loop():
    while True:
        if piou_active and core.pio_active_group:
            try: await client.send_message(core.pio_active_group, "شلیک")
            except: pass
            for _ in range(300):
                if not piou_active: break
                await asyncio.sleep(1)
        else: await asyncio.sleep(5)

async def piou_main_loop():
    global ammo_counter, skip_next_heal
    while True:
        if piou_active and piou_shoot_active and core.pio_active_group and not is_in_death_state and core.pio_target_links:
            try:
                while piou_active and piou_shoot_active and core.pio_active_group and not is_in_death_state and core.pio_target_links:
                    # بررسی زنده بودن نفر فعلی قبل از شلیک
                    if time.time() < dead_targets_timers.get(core.pio_active_link_index, 0):
                        next_idx = await find_next_alive_target()
                        if next_idx is not None:
                            core.pio_active_link_index = next_idx
                            await core.save_pio_db()
                            continue
                        else:
                            # اگه همه مرده‌ن موتور مرگ رو روشن کن
                            if not is_in_death_state:
                                if current_task is None or current_task.done():
                                    current_task = asyncio.create_task(death_cycle_task())
                            await asyncio.sleep(2)
                            continue
                            
                    g_id = core.pio_active_group
                    target = core.pio_target_links[core.pio_active_link_index]
                    m_id = target["m_id"]
                    
                    while time.time() < core.next_shoot_time:
                        if not piou_active or not piou_shoot_active or is_in_death_state: break
                        await asyncio.sleep(1)
                    if not piou_active or not piou_shoot_active or is_in_death_state: continue
                    
                    await client.send_message(g_id, "شلیک", reply_to=m_id); ammo_counter += 1
                    
                    if not skip_next_heal:
                        await asyncio.sleep(5)
                        await client.send_message(g_id, "پیو هیل", reply_to=m_id)
                    else:
                        skip_next_heal = False
                        await asyncio.sleep(2)
                        
                    if ammo_counter % ammo_limit == 0: await client.send_message(g_id, "خرید مهمات", reply_to=m_id)
                    
                    if time.time() >= core.next_shoot_time:
                        core.next_shoot_time = time.time() + shoot_interval
            except: await asyncio.sleep(10)
        else: await asyncio.sleep(1)

# --- دستورات روشن و خاموش ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^پیو روشن$'))
async def piou_on(event):
    global piou_active, last_meat_time, smart_active, refill_active
    if not piou_active:
        if not core.pio_target_links:
            return await event.reply("❗ اول `اد لینک` بزن!")
        piou_active = True
        last_meat_time = 0
        smart_active = True
        refill_active = True
        help_text = (
            "🔫 سیستم پیو، هوشمند و بانداژ **روشن** شد!\n\n"
            "💡 **یادآوری حذف لینک‌ها:**\n"
            "• برای حذف یه لینک خاص:\n`حذف لینک پیام [لینک]`\n"
            "• برای پاک کردن کل لینک‌ها:\n`حذف لینک همه`"
        )
        await event.reply(help_text)

@client.on(events.NewMessage(outgoing=True, pattern=r'^پیو خاموش$'))
async def piou_off(event):
    global piou_active, smart_active, refill_active
    piou_active = False
    smart_active = False
    refill_active = False
    await event.reply("🛑 سیستم پیو، هوشمند و بانداژ **خاموش** شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^هوشمند روشن$'))
async def smart_on(event):
    global smart_active
    if not smart_active:
        if not core.pio_target_links:
            return await event.reply("❗ اول با دستور `اد لینک` یه پیام هدف ثبت کن!")
        smart_active = True
        await event.reply("🧠 سیستم شلیک هوشمند **روشن** شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^هوشمند خاموش$'))
async def smart_off(event):
    global smart_active; smart_active = False
    await event.reply("🛑 سیستم شلیک هوشمند **خاموش** شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^بانداژ روشن$'))
async def refill_on(event):
    global refill_active; refill_active = True
    await event.reply("🩹 بانداژ **روشن** شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^بانداژ خاموش$'))
async def refill_off(event):
    global refill_active; refill_active = False
    await event.reply("🛑 بانداژ **خاموش** شد.")
