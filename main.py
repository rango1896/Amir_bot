import asyncio
import core
import modules.game
import modules.tools
from flask import Flask
import threading

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
        modules.game.meow_loop(),
        modules.game.update_name_clock(),
        modules.game.collect_points_loop(),
        modules.game.fishing_loop(),
        modules.tools.schedule_loop()
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
