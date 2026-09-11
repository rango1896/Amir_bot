import asyncio
from telethon import events
import core
from core import client

POINTS_INTERVAL = 600
FISHING_INTERVAL = 1800

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
