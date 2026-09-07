import asyncio
from telethon import events
import core
from core import client

squad_active = False
squad_task = None

@client.on(events.NewMessage(outgoing=True, pattern=r'^اسکواد روشن$'))
async def squad_on(event):
    global squad_active, squad_task
    if not core.pio_active_group:
        return await event.reply("❗ اول با دستور `اد لینک` و `اد گروه` یه گروه هدف ثبت کن!")
    if not squad_active:
        squad_active = True
        await event.reply("👥 سیستم اسکواد **روشن** شد. هر ۱۰ دقیقه یه بار استخراج میکنه.")
        if squad_task is None or squad_task.done():
            squad_task = asyncio.create_task(squad_loop())
    else:
        await event.reply("❗ اسکواد از قبل روشنه.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^اسکواد خاموش$'))
async def squad_off(event):
    global squad_active, squad_task
    squad_active = False
    if squad_task and not squad_task.done():
        squad_task.cancel()
    await event.reply("🛑 سیستم اسکواد **خاموش** شد.")

async def squad_loop():
    while squad_active:
        if core.pio_active_group:
            g_id = core.pio_active_group
            try:
                # ۱. ارسال پیام اسکواد
                await client.send_message(g_id, "پیو اسکواد")
                print("📤 پیو اسکواد فرستاده شد. منتظر دکمه استخراج (حداکثر ۲ دقیقه)...")
                
                extracted = False
                # ۲. چک کردن پیام‌ها تا ۲ دقیقه (۱۲ بار در هر ۱۰ ثانیه)
                for _ in range(12):
                    if not squad_active: break
                    await asyncio.sleep(10)
                    async for msg in client.iter_messages(g_id, limit=5):
                        if msg.buttons and msg.sender and msg.sender.bot:
                            for row in msg.buttons:
                                for btn in row:
                                    if "استخراج گان‌پوینت" in btn.text or "استخراج گان پوینت" in btn.text:
                                        try:
                                            await btn.click()
                                            print("✅ استخراج گان پوینت انجام شد!")
                                            extracted = True
                                        except Exception as e:
                                            print(f"خطا در کلیک دکمه: {e}")
                                        break # خروج از حلقه دکمه‌ها
                                if extracted: break # خروج از حلقه ردیف‌ها
                        if extracted: break # خروج از حلقه پیام‌ها
                    if extracted: break # خروج از حلقه زمان
                    
                if not extracted and squad_active:
                    print("⚠️ دکمه استخراج تو ۲ دقیقه پیدا نشد.")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ خطا در اسکواد: {e}")
            
            # ۳. صبر ۱۰ دقیقه (۶۰۰ ثانیه) تا چرخه بعدی
            for _ in range(600):
                if not squad_active: break
                await asyncio.sleep(1)
        else:
            await asyncio.sleep(5)
