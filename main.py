import os
import sys
import asyncio
import threading
from flask import Flask

# === رفع خودکار مشکل فاصله اضافه در نام پوشه گیتهاب ===
if os.path.exists('modules ') and not os.path.exists('modules'):
    # اون پوشه قاطی شده با فاصله رو به یه پوشه درست تبدیل میکنه
    os.rename('modules ', 'modules')
elif os.path.exists('modules ') and os.path.exists('modules'):
    # اگه هر دو بودن، پوشه خراب رو پاک میکنه
    import shutil
    shutil.rmtree('modules ')

# حالا ادامه کدهای اصلی
import core
from core import client

# اضافه کردن مسیر فعلی به پایتون
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# لود کردن تمام ماژول‌ها از پوشه‌ها (الان پوشه درست شده و پیدا میشه)
from modules.games import factory, fishing, cats
from modules.security import anti_delete, alerts
from modules.mentions import tags, user_info
from modules.tools import spam, voice, reactions, misc

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
