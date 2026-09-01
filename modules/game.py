import asyncio
from datetime import datetime
from telethon import events
from telethon.tl.functions.account import UpdateProfileRequest
import core
from core import client, fa_to_en_digits, to_double_struck, strip_clock, TEHRAN_TZ

stray_lock = asyncio.Lock()

# --- ساعت پروفایل ---
async def update_name_clock():
    while True:
        try:
            me = await client.get_me()
            base_name = strip_clock(me.first_name or "")
            now = datetime.now(TEHRAN_TZ).strftime("%H:%M")
            clock_str = to_double_struck(now)
            new_name = f"{base_name} {clock_str}" if base_name else clock_str
            await client(UpdateProfileRequest(first_name=new_name))
            print(f"🕒 اسم به‌روز شد: {new_name}")
        except Exception as e:
            print(f"❌ خطا: {e}")
        await asyncio.sleep(60)

# --- میو کردن ---
async def meow_loop():
    while True:
        try:
            await client.send_message(core.group_entity, "میو")
            print("🐱 میو فرستاده شد")
        except Exception as e:
            print(f"❌ خطا: {e}")
        await asyncio.sleep(300)

# --- پوینت ---
POINTS_INTERVAL = 600
async def do_collect_points():
    try:
        await client.send_message(core.group_entity, "پیشی")
        found = False
        for _ in range(30):
            await asyncio.sleep(2)
            messages = await client.get_messages(core.group_entity, limit=10)
            for msg in messages:
                if msg.buttons:
                    for row in msg.buttons:
                        for btn in row:
                            if "برداشت" in btn.text and "میو" in btn.text:
                                await msg.click(text=btn.text)
                                found = True
                                break
                        if found: break
                if found: break
            if found: break
    except Exception as e:
        print(f"❌ خطا پوینت: {e}")

@client.on(events.NewMessage(outgoing=True, pattern=r'^پوینت روشن$'))
async def points_on(event):
    core.collect_points_active = True
    await event.reply("✅ جمع‌آوری پوینت **روشن** شد.")
    await do_collect_points()

@client.on(events.NewMessage(outgoing=True, pattern=r'^پوینت خاموش$'))
async def points_off(event):
    core.collect_points_active = False
    await event.reply("🛑 جمع‌آوری پوینت **خاموش** شد.")

async def collect_points_loop():
    while True:
        await asyncio.sleep(POINTS_INTERVAL)
        if core.collect_points_active:
            await do_collect_points()

# --- ماهیگیری ---
FISHING_INTERVAL = 1800
async def do_fishing():
    try:
        await client.send_message(core.group_entity, "ماهی")
        found = False
        for _ in range(30):
            await asyncio.sleep(2)
            messages = await client.get_messages(core.group_entity, limit=10)
            for msg in messages:
                if msg.buttons:
                    for row in msg.buttons:
                        for btn in row:
                            if "بده پیشی" in btn.text:
                                await msg.click(text=btn.text)
                                found = True
                                break
                        if found: break
                if found: break
            if found: break
    except Exception as e:
        print(f"❌ خطا ماهی: {e}")

@client.on(events.NewMessage(outgoing=True, pattern=r'^ماهی روشن$'))
async def fishing_on(event):
    core.fishing_active = True
    await event.reply("🎣 سیستم ماهیگیری **روشن** شد.")
    await do_fishing()

@client.on(events.NewMessage(outgoing=True, pattern=r'^ماهی خاموش$'))
async def fishing_off(event):
    core.fishing_active = False
    await event.reply("🛑 سیستم ماهیگیری **خاموش** شد.")

async def fishing_loop():
    while True:
        await asyncio.sleep(FISHING_INTERVAL)
        if core.fishing_active:
            await do_fishing()

# --- نجات گربه ---
async def rescue_stray_cat(msg):
    async with stray_lock:
        for i in range(3):
            try:
                current_msg = await client.get_messages(core.group_entity, ids=msg.id)
                if not current_msg or not current_msg.buttons: break
                for row in current_msg.buttons:
                    for btn in row:
                        if "نجات پیشی خیابونی" in btn.text:
                            await current_msg.click(text=btn.text)
                            break
                    else: continue
                    break
                if i < 2: await asyncio.sleep(2)
            except Exception as e:
                print(f"❌ خطا گربه: {e}")
                break

@client.on(events.NewMessage(incoming=True))
async def stray_cat_handler(event):
    if not core.stray_cat_active: return
    if not event.is_group or event.chat_id != core.TARGET_GROUP: return
    if event.message.buttons:
        for row in event.message.buttons:
            for btn in row:
                if "نجات پیشی خیابونی" in btn.text:
                    await rescue_stray_cat(event.message)
                    return

# --- کارخونه میویی ---
async def click_factory_button(msg_id, target_text, timeout=30):
    for _ in range(timeout):
        await asyncio.sleep(1)
        msg = await client.get_messages(core.group_entity, ids=msg_id)
        if msg and msg.buttons:
            for row in msg.buttons:
                for btn in row:
                    if target_text in btn.text:
                        await msg.click(text=btn.text)
                        return True
    return False

async def click_factory_coords(msg_id, row_idx, col_idx, timeout=30):
    for _ in range(timeout):
        await asyncio.sleep(1)
        msg = await client.get_messages(core.group_entity, ids=msg_id)
        if msg and msg.buttons:
            try:
                await msg.click(row_idx, col_idx)
                return True
            except: pass
    return False

async def factory_cycle():
    while core.factory_active:
        try:
            await client.send_message(core.group_entity, "کارخونه میویی")
            await asyncio.sleep(3)
            panel_msg = None
            async for m in client.iter_messages(core.group_entity, limit=5):
                if m.buttons:
                    panel_msg = m
                    break
            if not panel_msg:
                await asyncio.sleep(10)
                continue
            
            panel_id = panel_msg.id
            if not await click_factory_button(panel_id, "تولید"): continue
            await asyncio.sleep(2)
            if not await click_factory_button(panel_id, "تولیدی هواپیما"): continue
            await asyncio.sleep(2)
            if not await click_factory_coords(panel_id, 0, 2): continue
            await asyncio.sleep(2)
            if not await click_factory_coords(panel_id, 0, 3): continue
            await asyncio.sleep(2)
            if not await click_factory_button(panel_id, "شروع تولید"): continue
            
            print("⏳ کارخونه استارت خورد (۱۳ ساعت و ۱۵ دقیقه صبر)...")
            waited = 0
            while waited < 47700 and core.factory_active:
                await asyncio.sleep(60)
                waited += 60
            
            if not core.factory_active: break
            
            await client.send_message(core.group_entity, "کارخونه میویی")
            await asyncio.sleep(3)
            panel_msg = None
            async for m in client.iter_messages(core.group_entity, limit=5):
                if m.buttons:
                    panel_msg = m
                    break
            if not panel_msg: continue
            
            panel_id = panel_msg.id
            if not await click_factory_button(panel_id, "انبار"): continue
            await asyncio.sleep(2)
            if not await click_factory_coords(panel_id, 0, 0): continue
            await asyncio.sleep(2)
            if not await click_factory_button(panel_id, "فروش محصول"): continue
            print("✅ فروش انجام شد.")
            await asyncio.sleep(3)
        except Exception as e:
            print(f"❌ خطا کارخونه: {e}")
            await asyncio.sleep(10)

@client.on(events.NewMessage(outgoing=True, pattern=r'^کارخونه میویی روشن$'))
async def factory_on(event):
    if not core.factory_active:
        core.factory_active = True
        await event.reply("🏭 سیستم کارخونه میویی **روشن** شد.")
        asyncio.create_task(factory_cycle())
    else:
        await event.reply("❗ کارخونه از قبل روشنه.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^کارخونه میویی خاموش$'))
async def factory_off(event):
    core.factory_active = False
    await event.reply("🛑 سیستم کارخونه میویی **خاموش** شد.")
