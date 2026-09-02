import asyncio
import core
from flask import Flask
import threading

# لود کردن مستقیم فایل‌ها (بدون پوشه، کاملاً بدون ارور)
import factory
import fishing
import cats
import anti_delete
import alerts
import tags
import user_info
import spam
import voice
import reactions
import misc

app = Flask(__name__)
@app.route('/')
def home():
    return "ربات زنده‌ست! 🐱"

def run_web():
    app.run(host='0.0.0.0', port=8080)

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
        misc.schedule_loop()
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
