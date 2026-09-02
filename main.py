import asyncio
import core
from flask import Flask
import threading

# لود کردن تمام ماژول‌ها از پوشه‌ها
import modules.games.factory
import modules.games.fishing
import modules.games.cats
import modules.security.anti_delete
import modules.security.alerts
import modules.mentions.tags
import modules.mentions.user_info
import modules.tools.spam
import modules.tools.voice
import modules.tools.reactions
import modules.tools.misc

app = Flask(__name__)
@app.route('/')
def home():
    return "ربات زنده‌ست! 🐱"

def run_web():
    app.run(host='0.0.0.0', port=8080)

async def main():
    await core.client.start()
    await core.load_db() # لود کردن دیتابیس از تلگرام
    core.group_entity = await core.client.get_entity(core.TARGET_GROUP)
    print(f"✅ گروه پیدا شد: {core.group_entity.title}")
    print("✅ سلف‌بات Amir روشن شد!")
    
    await asyncio.gather(
        modules.games.cats.meow_loop(),
        modules.games.cats.update_name_clock(),
        modules.games.fishing.collect_points_loop(),
        modules.games.fishing.fishing_loop(),
        modules.tools.misc.schedule_loop()
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
