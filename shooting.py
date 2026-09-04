import asyncio
import time
from telethon import events
import core
from core import client

# === سیستم مدیریت گروه‌ها و لینک‌ها ===
active_shoot_group = -1004346927517  # گروه پیش‌فرض
target_links = {-1004346927517: 18}  # {group_id: message_id}
ammo_counter = 0  # شمارنده خرید مهمات

piou_active = False
piou_shoot_active = True
last_meat_time = 0

# --- دستورات مدیریت لینک و گروه ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^اد لینک\s+(\S+)$'))
async def add_link(event):
    global active_shoot_group
    link = event.pattern_match.group(1)
    try:
        if "t.me/c/" in link:
            parts = link.split("t.me/c/")[-1].split("/")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                g_id = int("-100" + parts[0])
                m_id = int(parts[1])
                target_links[g_id] = m_id
                active_shoot_group = g_id
                await event.reply(f"✅ لینک ثبت شد. شلیک‌ها از این به بعد در این گروه روی پیام `{m_id}` انجام میشه.")
            else: await event.reply("❗ فرمت لینک اشتباه است.")
        else:
            parts = link.split("t.me/")[-1].split("/")
            if len(parts) == 2:
                ent = await client.get_entity(parts[0])
                g_id = ent.id
                m_id = int(parts[1])
                target_links[g_id] = m_id
                active_shoot_group = g_id
                await event.reply(f"✅ لینک ثبت شد. شلیک‌ها از این به بعد در این گروه روی پیام `{m_id}` انجام میشه.")
            else: await event.reply("❗ فرمت لینک اشتباه است.")
    except:
        await event.reply("❗ خطا در ثبت لینک.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^حذف اد لینک$'))
async def remove_link(event):
    global active_shoot_group
    if active_shoot_group in target_links and active_shoot_group != -1004346927517:
        del target_links[active_shoot_group]
    active_shoot_group = -1004346927517
    target_links[-1004346927517] = 18
    await event.reply("✅ لینک پاک شد و به حالت پیش‌فرض (گروه و پیام ۱۸) برگشتیم.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^اد گروه\s+(.+)$'))
async def add_group(event):
    global active_shoot_group
    g_str = event.pattern_match.group(1)
    try:
        if g_str.lstrip('-').isdigit():
            g_id = int(g_str)
        else:
            ent = await client.get_entity(g_str)
            g_id = ent.id
            
        if g_id in target_links:
            active_shoot_group = g_id
            await event.reply(f"✅ گروه فعال تغییر کرد. الان تو گروه `{g_id}` شلیک میشه روی پیام `{target_links[g_id]}`.")
        else:
            await event.reply("❗ برای این گروه هنوز لینکی ثبت نشده. اول `اد لینک` بزن.")
    except:
        await event.reply("❗ گروه پیدا نشد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^حذف اد گروه$'))
async def remove_group(event):
    global active_shoot_group
    if active_shoot_group != -1004346927517 and active_shoot_group in target_links:
        del target_links[active_shoot_group]
    active_shoot_group = -1004346927517
    target_links[-1004346927517] = 18
    await event.reply("✅ گروه فعلی حذف شد و ربات به گروه پیش‌فرض برگشت.")

# --- لوپ ارسال گوشت (درجا + هر ۳۰ دقیقه) ---
async def meat_loop():
    global last_meat_time
    while True:
        if piou_active and (time.time() - last_meat_time >= 1800):
            try:
                await client.send_message(active_shoot_group, "🥩")
                last_meat_time = time.time()
            except Exception as e:
                print(f"خطا گوشت: {e}")
        await asyncio.sleep(5)

# --- لوپ شلیک کور (درجا + هر ۵ دقیقه) ---
async def blind_shot_loop():
    while True:
        if piou_active:
            try:
                await client.send_message(active_shoot_group, "شلیک")
            except Exception as e:
                print(f"خطا شلیک کور: {e}")
            
            for _ in range(300):
                if not piou_active: break
                await asyncio.sleep(1)
        else:
            await asyncio.sleep(5)

# --- لوپ اصلی شلیک و پیو هیل (با ریپلای) ---
async def piou_main_loop():
    global ammo_counter
    while True:
        if piou_active and piou_shoot_active:
            try:
                cycle_count = 0
                while piou_active and piou_shoot_active:
                    cycle_count += 1
                    g_id = active_shoot_group
                    m_id = target_links.get(g_id, 18)
                    
                    # ۱. شلیک
                    await client.send_message(g_id, "شلیک", reply_to=m_id)
                    ammo_counter += 1
                    await asyncio.sleep(2)
                    
                    # ۲. پیو هیل
                    await client.send_message(g_id, "پیو هیل", reply_to=m_id)
                    
                    # ۳. خرید مهمات (هر ۹ شلیک)
                    if ammo_counter % 9 == 0:
                        await client.send_message(g_id, "خرید مهمات", reply_to=m_id)
                    
                    # ۴. استراحت ۶ دقیقه (هر ۱۰ بار)
                    if cycle_count % 10 == 0:
                        print("⏳ ۶ دقیقه استراحت...")
                        for _ in range(360):
                            if not piou_active or not piou_shoot_active: break
                            await asyncio.sleep(1)
                        if not piou_active or not piou_shoot_active: break
                    else:
                        # فاصله ۱۵ ثانیه‌ای بین شلیک‌ها
                        for _ in range(15):
                            if not piou_active or not piou_shoot_active: break
                            await asyncio.sleep(1)
                        if not piou_active or not piou_shoot_active: break

            except Exception as e:
                print(f"❌ خطا در سیستم پیو: {e}")
                await asyncio.sleep(10)
        else:
            await asyncio.sleep(1)

@client.on(events.NewMessage(outgoing=True, pattern=r'^پیو روشن$'))
async def piou_on(event):
    global piou_active, last_meat_time
    if not piou_active:
        piou_active = True
        last_meat_time = 0
        await event.reply("🔫 سیستم پیو **روشن** شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^پیو خاموش$'))
async def piou_off(event):
    global piou_active
    piou_active = False
    await event.reply("🛑 سیستم پیو **خاموش** شد.")
