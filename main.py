import asyncio
import core
from flask import Flask
import threading
from telethon import events
import urllib.request

# === لود کردن ماژول‌ها از پوشه piogame (smart_shoot حذف شد) ===
from piogame import shooting, cooldown, art, squad, ring, enemy, dungeon

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
    # ابزارهای کاربردی
    core.anti_delete_active = True
    core.keyword_alert_active = True
    core.ghost_mode_active = True
    
    # واکنش خودکار
    if hasattr(reactions, 'react_active'):
        reactions.react_active = True

    # قابلیت‌های بازی پیو (اگه گروه هدف ثبت شده باشه)
    if core.pio_active_group:
        shooting.piou_active = True
        shooting.smart_active = True
        shooting.refill_active = True # بانداژ
        
        # روشن کردن رینگ
        if not core.ring_active_status:
            core.ring_active_status = True
            asyncio.create_task(ring.ring_loop(core.pio_active_group))
            
        # روشن کردن اسکواد
        if not squad.squad_active:
            squad.squad_active = True
            asyncio.create_task(squad.squad_loop())
            
        await event.reply("✅ تمام قابلیت‌های ربات (ابزارها + پیو + هوشمند + بانداژ + رینگ + اسکواد) **روشن** شدند!\n\n⚠️ *نکته: سیستم دشمن و دانجن برای امنیت باید دستی روشن بشن.*")
    else:
        await event.reply("✅ ابزارها روشن شدند!\n⚠️ اما قابلیت‌های بازی پیو روشن نشدن چون اول باید `اد لینک` بزنید.")

# === دستور خاموش کردن همه قابلیت‌ها ===
@core.client.on(events.NewMessage(outgoing=True, pattern=r'^خاموش همه$'))
async def turn_off_all(event):
    # خاموش کردن ابزارها
    core.anti_delete_active = False
    core.keyword_alert_active = False
    core.ghost_mode_active = False
    if hasattr(reactions, 'react_active'):
        reactions.react_active = False

    # خاموش کردن بازی‌ها
    core.factory_active = False
    shooting.piou_active = False
    shooting.smart_active = False
    shooting.refill_active = False
    core.ring_active_status = False
    squad.squad_active = False
    art.art_active = False
    
    # خاموش کردن سیستم خطرناک (دشمن و دانجن)
    core.enemy_active = False
    core.dungeon_active = False
    
    await event.reply("🛑 تمام قابلیت‌های ربات (ابزارها، بازی‌ها، رینگ، اسکواد، دشمن و دانجن) **خاموش** شدند!")

async def main():
    await core.client.start()
    await core.load_db()
    
    try:
        core.group_entity = await core.client.get_entity(core.TARGET_GROUP)
        print(f"✅ گروه پیدا شد: {core.group_entity.title}")
    except:
        print("⚠️ گروه پیش‌فرض پیدا نشد، اما ربات روشن میشه.")
        
    print("✅ سلف‌بات Amir روشن شد!")
    
    # استارت حلقه‌های پس‌زمینه
    asyncio.ensure_future(name_clock.start_name_clock())
    asyncio.ensure_future(misc.schedule_loop())
    asyncio.ensure_future(shooting.meat_loop())
    asyncio.ensure_future(shooting.blind_shot_loop())
    asyncio.ensure_future(shooting.piou_main_loop())
    asyncio.ensure_future(multi_react.start_multi_clients())
    asyncio.ensure_future(squad.squad_loop())
    asyncio.ensure_future(art.art_loop())
    asyncio.ensure_future(video_downloader.start_download_worker())
    asyncio.ensure_future(ring.start_ring_if_active())

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
