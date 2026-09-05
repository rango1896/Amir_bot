import asyncio
import core
from flask import Flask
import threading
from telethon import events

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
    ammo.ammo_active = True
    # روشن کردن کارخونه
    if not core.factory_active:
        core.factory_active = True
        asyncio.create_task(factory.factory_cycle())
        
    # روشن کردن واکنش خودکار
    if hasattr(reactions, 'react_active'):
        reactions.react_active = True

    # روشن کردن پیو
    shooting.piou_active = True

    await event.reply("✅ تمام قابلیت‌های ربات (شبح، ضدحذف، هشدار، گربه‌ها، پوینت، ماهیگیری، کارخونه، واکنش و پیو) **روشن** شدند!")

async def main():
    await core.client.start()
    await core.load_db()
    core.group_entity = await core.client.get_entity(core.TARGET_GROUP)
    print(f"✅ گروه پیدا شد: {core.group_entity.title}")
    print("✅ سلف‌بات Amir روشن شد!")
    
    await asyncio.gather(
        cats.meow_loop(),
        cats.update_name_clock(),
        fishing.collect_points_loop(),
        fishing.fishing_loop(),
        misc.schedule_loop(),
        shooting.meat_loop(),
        shooting.blind_shot_loop(),
        shooting.piou_main_loop()
    )

def keep_alive():
    import time
    while True:
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    with core.client:
        core.client.loop.run_until_complete(main())
