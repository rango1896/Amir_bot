import asyncio
import time
from telethon import events, utils
import core
from core import client

ammo_counter = 0
ammo_limit = 9
piou_active = False
piou_shoot_active = True
last_meat_time = 0

@client.on(events.NewMessage(outgoing=True, pattern=r'^تنظیم تیر\s+(\d+)$'))
async def set_ammo_limit(event):
    global ammo_limit
    ammo_limit = int(event.pattern_match.group(1))
    await event.reply(f"✅ تنظیمات خرید مهمات تغییر کرد. از این به بعد هر {ammo_limit} شلیک، یک خرید مهمات انجام میشه.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^اد لینک\s+(\S+)$'))
async def add_link(event):
    link = event.pattern_match.group(1)
    try:
        if "t.me/c/" in link:
            parts = link.split("t.me/c/")[-1].split("/")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                g_id = int("-100" + parts[0]); m_id = int(parts[1])
                core.pio_target_links[g_id] = m_id; core.pio_active_group = g_id
                await core.save_pio_db()
                await event.reply(f"✅ لینک ثبت شد. شلیک‌ها روی پیام `{m_id}` انجام میشه.")
            else: await event.reply("❗ فرمت لینک اشتباه است.")
        else:
            parts = link.split("t.me/")[-1].split("/")
            if len(parts) == 2:
                ent = await client.get_entity(parts[0])
                g_id = utils.get_peer_id(ent)  # استخراج آیدی استاندارد از یوزرنیم
                m_id = int(parts[1])
                core.pio_target_links[g_id] = m_id; core.pio_active_group = g_id
                await core.save_pio_db()
                await event.reply(f"✅ لینک ثبت شد. شلیک‌ها روی پیام `{m_id}` انجام میشه.")
            else: await event.reply("❗ فرمت لینک اشتباه است.")
    except: await event.reply("❗ خطا در ثبت لینک.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^حذف اد لینک$'))
async def remove_link(event):
    if core.pio_active_group in core.pio_target_links:
        del core.pio_target_links[core.pio_active_group]
    core.pio_active_group = None
    await core.save_pio_db()
    await event.reply("✅ لینک پاک شد. ربات متوقف شد تا لینک جدید بدی.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^اد گروه\s+(.+)$'))
async def add_group(event):
    g_str = event.pattern_match.group(1)
    try:
        if g_str.lstrip('-').isdigit():
            g_id = int(g_str)
        else:
            ent = await client.get_entity(g_str)
            g_id = utils.get_peer_id(ent)  # استخراج آیدی استاندارد از یوزرنیم
            
        if g_id in core.pio_target_links:
            core.pio_active_group = g_id
            await core.save_pio_db()
            await event.reply(f"✅ گروه فعال شد. شلیک روی پیام `{core.pio_target_links[g_id]}`.")
        else: await event.reply("❗ برای این گروه هنوز لینکی ثبت نشده. اول `اد لینک` بزن.")
    except: await event.reply("❗ گروه پیدا نشد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^حذف اد گروه$'))
async def remove_group(event):
    if core.pio_active_group in core.pio_target_links:
        del core.pio_target_links[core.pio_active_group]
    core.pio_active_group = None
    await core.save_pio_db()
    await event.reply("✅ گروه فعلی حذف شد.")

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
    global ammo_counter
    while True:
        if piou_active and piou_shoot_active and core.pio_active_group:
            try:
                cycle_count = 0
                while piou_active and piou_shoot_active and core.pio_active_group:
                    cycle_count += 1
                    g_id = core.pio_active_group
                    m_id = core.pio_target_links.get(g_id, 18)
                    
                    await client.send_message(g_id, "شلیک", reply_to=m_id); ammo_counter += 1
                    await asyncio.sleep(2)
                    await client.send_message(g_id, "پیو هیل", reply_to=m_id)
                    if ammo_counter % ammo_limit == 0: await client.send_message(g_id, "خرید مهمات", reply_to=m_id)
                    
                    if cycle_count % 10 == 0:
                        for _ in range(360):
                            if not piou_active or not piou_shoot_active or not core.pio_active_group: break
                            await asyncio.sleep(1)
                    else:
                        for _ in range(20):
                            if not piou_active or not piou_shoot_active or not core.pio_active_group: break
                            await asyncio.sleep(1)
            except: await asyncio.sleep(10)
        else: await asyncio.sleep(1)

@client.on(events.NewMessage(outgoing=True, pattern=r'^پیو روشن$'))
async def piou_on(event):
    global piou_active, last_meat_time
    if not piou_active:
        if not core.pio_active_group:
            return await event.reply("❗ اول با دستور `اد لینک` یه پیام هدف ثبت کن!")
        piou_active = True; last_meat_time = 0
        await event.reply("🔫 سیستم پیو **روشن** شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^پیو خاموش$'))
async def piou_off(event):
    global piou_active; piou_active = False
    await event.reply("🛑 سیستم پیو **خاموش** شد.")
