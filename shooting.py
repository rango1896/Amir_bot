import asyncio
import time
import re
from telethon import events, utils
import core
from core import client

ammo_counter = 0
ammo_limit = 9
piou_active = False
piou_shoot_active = True
last_meat_time = 0
shoot_interval = 30
next_shoot_time = 0  # متغیر جدید برای مدیریت دقیق زمان
skip_next_heal = False

@client.on(events.NewMessage(outgoing=True, pattern=r'^تنظیم تیر\s+(\d+)$'))
async def set_ammo_limit(event):
    global ammo_limit
    n = int(event.pattern_match.group(1))
    # FIX(F2): جلوگیری از تنظیم صفر که باعث ZeroDivisionError در چرخه شلیک میشد
    if n < 1:
        return await event.reply("❗ عدد باید حداقل ۱ باشه.")
    ammo_limit = n
    await event.reply(f"✅ تنظیمات خرید مهمات تغییر کرد. از این به بعد هر {ammo_limit} شلیک، یک خرید مهمات انجام میشه.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^تنظیم زمان شلیک\s+(\d+)$'))
async def set_shoot_interval(event):
    global shoot_interval
    shoot_interval = int(event.pattern_match.group(1))
    await event.reply(f"✅ زمان‌بندی شلیک تغییر کرد. از این به بعد هر {shoot_interval} ثانیه یک‌بار شلیک و ۵ ثانیه بعدش پیو هیل فرستاده میشه.")

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
                g_id = utils.get_peer_id(ent)
                m_id = int(parts[1])
                core.pio_target_links[g_id] = m_id; core.pio_active_group = g_id
                await core.save_pio_db()
                await event.reply(f"✅ لینک ثبت شد. شلیک‌ها روی پیام `{m_id}` انجام میشه.")
            else: await event.reply("❗ فرمت لینک اشتباه است.")
    except Exception as e:
        # FIX(F6): دیگه خطا کاملاً بی‌صدا قورت داده نمیشه (لاگ میشه)
        print(f"❌ خطا در ثبت لینک پیو: {e}")
        await event.reply("❗ خطا در ثبت لینک.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^حذف اد لینک$'))
async def remove_link(event):
    try:
        if core.pio_active_group in core.pio_target_links:
            del core.pio_target_links[core.pio_active_group]
        core.pio_active_group = None
        await core.save_pio_db()
        await event.reply("✅ لینک پاک شد. ربات متوقف شد تا لینک جدید بدی.")
    except Exception as e:
        # FIX(F6): قبلاً save_pio_db() اینجا اصلاً محافظت نشده بود
        print(f"❌ خطا در حذف لینک پیو: {e}")
        await event.reply("❗ خطا در حذف لینک.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^اد گروه\s+(.+)$'))
async def add_group(event):
    g_str = event.pattern_match.group(1)
    try:
        if g_str.lstrip('-').isdigit():
            g_id = int(g_str)
        else:
            ent = await client.get_entity(g_str)
            g_id = utils.get_peer_id(ent)

        if g_id in core.pio_target_links:
            core.pio_active_group = g_id
            await core.save_pio_db()
            await event.reply(f"✅ گروه فعال شد. شلیک روی پیام `{core.pio_target_links[g_id]}`.")
        else: await event.reply("❗ برای این گروه هنوز لینکی ثبت نشده. اول `اد لینک` بزن.")
    except Exception as e:
        print(f"❌ خطا در تنظیم گروه پیو: {e}")
        await event.reply("❗ گروه پیدا نشد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^حذف اد گروه$'))
async def remove_group(event):
    try:
        if core.pio_active_group in core.pio_target_links:
            del core.pio_target_links[core.pio_active_group]
        core.pio_active_group = None
        await core.save_pio_db()
        await event.reply("✅ گروه فعلی حذف شد.")
    except Exception as e:
        print(f"❌ خطا در حذف گروه پیو: {e}")
        await event.reply("❗ خطا در حذف گروه.")

# --- شنود هوشمند پیام‌های ربات بازی ---
@client.on(events.NewMessage(incoming=True))
async def game_state_listener(event):
    global next_shoot_time, skip_next_heal
    if not core.pio_active_group or event.chat_id != core.pio_active_group: return
    text = event.message.text or ""

    # ۱. تشخیص خنکی شلیک (فقط اگه روی پیام "شلیک" خودمون ریپلای کرده باشه)
    if "تازه شلیک کردی" in text and "ثانی" in text and event.message.is_reply:
        try:
            replied_msg = await event.message.get_reply_message()
            me = await client.get_me()
            # مطمئن میشیم که پیام شلیک مال خودمونه
            if replied_msg and replied_msg.sender_id == me.id and (replied_msg.text or "").strip() == "شلیک":
                # FIX(F3): قبلاً فقط ثانیه پارس میشد؛ حالا دقیقه هم پشتیبانی میشه
                # (هم‌شکل با پارس زمان مرگ/بانداژ در smart_shoot.py)
                secs = 0
                m_min = re.search(r'(\d+)\s*دقیق', text)
                m_sec = re.search(r'(\d+)\s*ثانی', text)
                if m_min: secs += int(m_min.group(1)) * 60
                if m_sec: secs += int(m_sec.group(1))
                if secs > 0:
                    new_time = time.time() + secs + 1  # ۱ ثانیه امنیت اضافه میکنیم
                    # فقط اگه زمان جدید از زمان قبلی بیشتر باشه آپدیت میکنیم
                    if new_time > next_shoot_time:
                        next_shoot_time = new_time
                        try:
                            await client.send_message(event.chat_id, f"⏳ {secs} ثانیه دیگه شلیک میکنم.")
                        except Exception as e:
                            print(f"❌ خطا در ارسال پیام شمارش معکوس: {e}")
        except Exception as e:
            print(f"❌ خطا در تشخیص خنکی شلیک: {e}")

    # ۲. تشخیص خون پر
    elif "نیازی به هیل نیست" in text and "کامله" in text:
        skip_next_heal = True

async def meat_loop():
    global last_meat_time
    while True:
        if piou_active and core.pio_active_group and (time.time() - last_meat_time >= 1800):
            try:
                await client.send_message(core.pio_active_group, "🥩")
                last_meat_time = time.time()
            except Exception as e:
                print(f"❌ خطا در ارسال گوشت: {e}")
        await asyncio.sleep(5)

async def blind_shot_loop():
    global ammo_counter
    while True:
        # FIX(F1): قبلاً فقط piou_active چک میشد؛ در نتیجه در حین چرخه‌های
        # هوشمند (مرگ/بانداژ) هم شلیک کور ادامه پیدا میکرد و مستقیماً با
        # کول‌داونی که death_cycle_task/refill_cycle_task مدیریت میکنند تداخل میکرد.
        if piou_active and piou_shoot_active and core.pio_active_group:
            try:
                await client.send_message(core.pio_active_group, "شلیک")
                # FIX(F8): شلیک کور هم مهمات مصرف میکنه؛ قبلاً در ammo_counter
                # شمرده نمیشد و چرخه‌ی «خرید مهمات» این شلیک‌ها رو نادیده میگرفت.
                ammo_counter += 1
                if ammo_limit > 0 and ammo_counter % ammo_limit == 0:
                    await client.send_message(core.pio_active_group, "خرید مهمات")
            except Exception as e:
                print(f"❌ خطا در شلیک کور: {e}")
            for _ in range(300):
                if not piou_active or not piou_shoot_active: break
                await asyncio.sleep(1)
        else:
            await asyncio.sleep(5)

async def piou_main_loop():
    global ammo_counter, next_shoot_time, skip_next_heal
    while True:
        if piou_active and piou_shoot_active and core.pio_active_group:
            try:
                while piou_active and piou_shoot_active and core.pio_active_group:
                    g_id = core.pio_active_group
                    m_id = core.pio_target_links.get(g_id)
                    # FIX(F4): پیش‌فرض جادویی ۱۸ حذف شد. اگه پیام هدفی برای این
                    # گروه ثبت نشده باشه، به‌جای شلیک به یک پیام تصادفی صبر میکنیم.
                    if m_id is None:
                        print("❌ برای گروه فعال، پیام هدفی ثبت نشده؛ منتظر `اد لینک` هستیم.")
                        await asyncio.sleep(10)
                        continue

                    # چک کردن زمان شلیک بعدی (هر ۱ ثانیه بیدار میشه)
                    while time.time() < next_shoot_time:
                        if not piou_active or not piou_shoot_active or not core.pio_active_group: break
                        await asyncio.sleep(1)
                    if not piou_active or not piou_shoot_active: continue

                    # ۱. شلیک
                    await client.send_message(g_id, "شلیک", reply_to=m_id); ammo_counter += 1

                    # ۲. پیو هیل (اگه خون پر نبود)
                    if not skip_next_heal:
                        await asyncio.sleep(5)
                        await client.send_message(g_id, "پیو هیل", reply_to=m_id)
                    else:
                        skip_next_heal = False
                        await asyncio.sleep(2)

                    # FIX(F2): گارد دفاعی در برابر تقسیم بر صفر
                    if ammo_limit > 0 and ammo_counter % ammo_limit == 0:
                        await client.send_message(g_id, "خرید مهمات", reply_to=m_id)

                    # ۳. تنظیم زمان شلیک بعدی (پیش‌فرض ۳۰ ثانیه)
                    next_shoot_time = time.time() + shoot_interval
            except Exception as e:
                print(f"❌ خطا در چرخه اصلی شلیک: {e}")
                await asyncio.sleep(10)
        else:
            await asyncio.sleep(1)

@client.on(events.NewMessage(outgoing=True, pattern=r'^پیو روشن$'))
async def piou_on(event):
    global piou_active, last_meat_time
    # FIX(F5): حالا همیشه پاسخ میده، حتی اگه از قبل روشن باشه
    # (قبلاً در آن حالت هیچ پیامی نمی‌فرستاد و کاربر گیج میشد)
    if not core.pio_active_group:
        return await event.reply("❗ اول با دستور `اد لینک` یه پیام هدف ثبت کن!")
    if piou_active:
        return await event.reply("ℹ️ سیستم پیو از قبل روشنه.")
    piou_active = True; last_meat_time = 0
    await event.reply("🔫 سیستم پیو **روشن** شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^پیو خاموش$'))
async def piou_off(event):
    global piou_active
    if not piou_active:
        return await event.reply("ℹ️ سیستم پیو از قبل خاموشه.")
    piou_active = False
    await event.reply("🛑 سیستم پیو **خاموش** شد.")
