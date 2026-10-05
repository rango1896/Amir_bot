import asyncio
import time
from telethon import events
from telethon.errors import MessageNotModifiedError, FloodWaitError
import core
from core import client

# فریم‌های انیمیشن
ANIMATIONS = {
    "خورشید": [
        "☀️\n      ☁️\n🌴   🌴   🌴",
        "☀️   💨\n   ☁️   💨\n🍃   🍃   🍃",
        "🌤     💨💨\n  ☁️     💨💨\n🌿   🌿   🌿",
        "⛈⚡️   💨💨💨\n   🌧🌧\n🌪   🌪   🌪",
        "☀️\n      ☁️\n🌴   🌴   🌴"
    ],
    "تفنگ": [
        "▄︻̷̿┻̿═━一          👤",
        "💥💥 BANG! 💥💥\n\n▄︻̷̿┻̿═━一  •       👤",
        "💨 *fwoosh*\n\n▄︻̷̿┻̿═━一      •   👤",
        "🎯 **DIRECT HIT**\n\n▄︻̷̿┻̿═━一          💥💀",
        "🪦 RIP\n\n▄︻̷̿┻̿═━一            🪦"
    ],
    "کیر": [
        "\n".join([
            """.
            ⠀⠀ ⠀⢀⡀⠀⠀⠀
             ⠀⠀⠀⢐⠊⠀⠀⠀
            ⠀ ⠀⠀⠨⠔⠀⠀⠀""",
            """              ⠀ ⢀⢤⢄⠀⠀⠀
               ⠀⡍⠈⠁⡃⠀⠀
               ⠀⡇⠀⠀⡇⠀⠀
               ⠀⡃⠀⠀⡃⠀⠀
              ⡊⠉⠉⢰⠔⠃⢄⠀
              ⠉⠢⠤⢇⣀⣀⡌⠀"""
        ]),
        "\n".join([
            """.
            ⠀⠀ ⠀⢠⡄⠀⠀⠀
              ⠀⠀⢐⠊⠀⠀⠀
             ⠀⠀⠐⠨⠀⠂⠀⠀""",
            """              ⠀ ⢀⢤⢄⠀⠀⠀
               ⠀⡍⠈⠁⡃⠀⠀
               ⠀⡇⠀⠀⡇⠀⠀
               ⠀⡃⠀⠀⡃⠀⠀
              ⡊⠉⠉⢰⠔⠃⢄⠀
              ⠉⠢⠤⢇⣀⣀⡌⠀"""
        ]),
        "\n".join([
            """.
            ⠀⠀ ⢀⠎⠱⡀⠀⠀
            ⠀ ⠀⠀⢐⠊⠀⠀⠀
             ⠀⠈⠀⠨⠀⠀⠁⠀""",
            """                  ⢀⢤⢄⠀⠀⠀
               ⠀⡍⠈⠁⡃⠀⠀
               ⠀⡇⠀⠀⡇⠀⠀
               ⠀⡃⠀⠀⡃⠀⠀
              ⡊⠉⠉⢰⠔⠃⢄⠀
              ⠉⠢⠤⢇⣀⣀⡌⠀"""
        ]),
        "\n".join([
            """.
             ⠀⡠⠊⠀⠀⠱⢄⠀
            ⠀ ⠀⠀⢐⠀⠀⠀⠀
             ⠊⠀⠀⠨⠀⠀⠀⠂""",
            """              ⠀ ⢀⢤⢄⠀⠀⠀
               ⠀⡍⠈⠁⡃⠀⠀
               ⠀⡇⠀⠀⡇⠀⠀
               ⠀⡃⠀⠀⡃⠀⠀
              ⡊⠉⠉⢰⠔⠃⢄⠀
              ⠉⠢⠤⢇⣀⣀⡌⠀"""
        ]),
        "\n".join([
            """.
               ⠀⠀⢀⡀⠀⠀⠀
            ⠀⠁⠀⠀⢐⠊⠀⠀⠈
            ⠀⠀⠀⠨⠔⠀⠀⠀""",
            """              ⠀ ⢀⢤⢄⠀⠀⠀⠀
               ⠀⡍⠈⠁⡃⠀⠀
               ⠀⡇⠀⠀⡇⠀⠀
               ⠀⡃⠀⠀⡃⠀⠀
              ⡊⠉⠉⢰⠔⠃⢄⠀
              ⠉⠢⠤⢇⣀⣀⡌⠀"""
        ])
    ]
}

@client.on(events.NewMessage(outgoing=True, pattern=r'^(خورشید|تفنگ|کیر)$'))
async def emoji_animation_handler(event):
    # گرفتن کلمه انیمیشن از پیام
    choice = event.pattern_match.group(1)
    
    frames = ANIMATIONS[choice]
    frame_count = len(frames)
    current_frame = 0
    
    # تایمر ۳۰ ثانیه‌ای
    start_time = time.time()
    duration = 30 
    
    while time.time() - start_time < duration:
        try:
            # ویرایش پیام با فریم بعدی
            await event.edit(frames[current_frame])
            
            # رفتن به فریم بعدی (اگه رسید آخر، برگرده اول)
            current_frame = (current_frame + 1) % frame_count
            
            # تاخیر 1 ثانیه‌ای
            await asyncio.sleep(1)
            
        except MessageNotModifiedError:
            # اگه تلگرام گیر داد که متن تکراریه، نادیده بگیر
            pass 
        except FloodWaitError as e:
            # اگه تلگرام محدودت کرد، همون‌قدر صبر کن تا باز بشی
            print(f"[انیمیشن] تلگرام محدود کرد! {e.seconds} ثانیه صبر میکنیم.")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"[انیمیشن] ارور: {e}")
            break

    # پاک کردن پیام بعد از تموم شدن ۳۰ ثانیه
    try:
        await event.delete()
    except:
        pass
