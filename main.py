import asyncio
import core
from flask import Flask
import threading
from telethon import events
import urllib.request

# لود کردن مستقیم فایل‌ها
import factory
import fishing
import cats
import anti_delete
import alerts 
import user_info
import spam
import reactions
import misc
import shooting
import smart_shoot

app = Flask(__name__)
@app.route('/')
def home():
    return "ربات زنده‌ست! 🐱"

def run_web():
    app.run(host='0.0.0.0', port=8080)

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
    
    # روشن کردن کارخونه
    if not core.factory_active:
        core.factory_active = True
        asyncio.ensure_future(factory.factory_cycle())
        
    # روشن کردن واکنش خودکار
    if hasattr(reactions, 'react_active'):
        reactions.react_active = True

    # روشن کردن پیو
    shooting.piou_active = True

    await event.reply("✅ تمام قابلیت‌های ربات (شبح، ضدحذف، هشدار، گربه‌ها، پوینت، ماهیگیری، کارخونه، واکنش و پیو) **روشن** شدند!")

async def main():
    await core.client.start()
    await core.load_db()
    
    try:
        core.group_entity = await core.client.get_entity(core.TARGET_GROUP)
        print(f"✅ گروه پیدا شد: {core.group_entity.title}")
    except:
        print("⚠️ گروه پیش‌فرض پیدا نشد، اما ربات روشن میشه.")
        
    print("✅ سلف‌بات Amir روشن شد!")
    
    asyncio.ensure_future(cats.meow_loop())
    asyncio.ensure_future(cats.update_name_clock())
    asyncio.ensure_future(fishing.collect_points_loop())
    asyncio.ensure_future(fishing.fishing_loop())
    asyncio.ensure_future(misc.schedule_loop())
    asyncio.ensure_future(shooting.meat_loop())
    asyncio.ensure_future(shooting.blind_shot_loop())
    asyncio.ensure_future(shooting.piou_main_loop())
    
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
