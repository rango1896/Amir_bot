import asyncio
import core
from flask import Flask
import threading
from telethon import events
import urllib.request

# === لود کردن ماژول‌ها از پوشه piogame ===
from piogame import shooting, smart_shoot, cooldown, art, squad, ring, enemy, dungeon

# === لود کردن ماژول‌ها از پوشه tools ===
from tools import anti_delete, alerts, user_info, spam, reactions, misc, multi_react, stealer, video_downloader, animation, name_clock

app = Flask(__name__)
@app.route('/')
def home():
    return "ربات زنده‌ست! 🐱"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# === دستور ترکیبی پیو همه روشن ===
@core.client.on(events.NewMessage(outgoing=True, pattern=r'^پیو همه روشن$'))
async def pio_all_on(event):
    g_id = event.chat_id
    # فقط همون کلمات رو از طرف شما میفرسته
    await core.client.send_message(g_id, "پیو روشن")
    await asyncio.sleep(3)
    await core.client.send_message(g_id, "بانداژ روشن")
    await asyncio.sleep(3)
    await core.client.send_message(g_id, "هوشمند روشن")
    await asyncio.sleep(4)
    await core.client.send_message(g_id, "اسکواد روشن")

# === دستور ترکیبی پیو همه خاموش ===
@core.client.on(events.NewMessage(outgoing=True, pattern=r'^پیو همه خاموش$'))
async def pio_all_off(event):
    g_id = event.chat_id
    # فقط همون کلمات رو از طرف شما میفرسته
    await core.client.send_message(g_id, "پیو خاموش")
    await asyncio.sleep(3)
    await core.client.send_message(g_id, "بانداژ خاموش")
    await asyncio.sleep(3)
    await core.client.send_message(g_id, "هوشمند خاموش")
    await asyncio.sleep(4)
    await core.client.send_message(g_id, "اسکواد خاموش")

# === دستور روشن کردن همه قابلیت‌ها ===
@core.client.on(events.NewMessage(outgoing=True, pattern=r'^روشن همه$'))
async def turn_on_all(event):
    core.anti_delete_active = True
    core.keyword_alert_active = True
    core.stray_cat_active = True
    core.collect_points_active = True
    core.fishing_active = True
    core.ghost_mode_active = True
    smart_shoot.smart_active = True
    
    if hasattr(reactions, 'react_active'):
        reactions.react_active = True

    shooting.piou_active = True
    await event.reply("✅ تمام قابلیت‌های ربات **روشن** شدند!")

async def main():
    await core.client.start()
    await core.load_db()
    
    try:
        core.group_entity = await core.client.get_entity(core.TARGET_GROUP)
        print(f"✅ گروه پیدا شد: {core.group_entity.title}")
    except:
        print("⚠️ گروه پیش‌فرض پیدا نشد، اما ربات روشن میشه.")
        
    print("✅ سلف‌بات Amir روشن شد!")
    
    asyncio.ensure_future(misc.schedule_loop())
    asyncio.ensure_future(shooting.meat_loop())
    asyncio.ensure_future(shooting.blind_shot_loop())
    asyncio.ensure_future(shooting.piou_main_loop())
    asyncio.ensure_future(multi_react.start_multi_clients())  # <--- این خط سنیورها رو وصل میکنه
    asyncio.ensure_future(squad.squad_loop())
    asyncio.ensure_future(art.art_loop())
    asyncio.ensure_future(video_downloader.start_download_worker())
    asyncio.ensure_future(ring.start_ring_if_active())
    asyncio.ensure_future(name_clock.start_name_clock())
    await core.client.run_until_disconnected()

def keep_alive():
    import time
    while True:
        try:
            urllib.request.urlopen("https://friendpiobot.onrender.com/")
        except:
            pass
        time.sleep(280)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    with core.client:
        core.client.loop.run_until_complete(main())
