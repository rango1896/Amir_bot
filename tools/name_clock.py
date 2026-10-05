import asyncio
from datetime import datetime
from telethon.tl.functions.account import UpdateProfileRequest
import core
from core import client

async def update_name_clock():
    """آپدیت کردن ساعت بغل اسم هر ۱ دقیقه"""
    while True:
        try:
            now = datetime.now(core.TEHRAN_TZ)
            time_str = now.strftime("%H:%M")
            
            # تبدیل اعداد به فونت دابل استراک (𝟘𝟙𝟚𝟛𝟜...)
            formatted_time = core.to_double_struck(time_str)
            
            me = await client.get_me()
            current_first_name = me.first_name or ""
            
            # پاک کردن ساعت قبلی از اسم (اگه هست)
            base_name = core.strip_clock(current_first_name)
            
            # ساخت اسم جدید با ساعت جدید
            new_first_name = f"{base_name} {formatted_time}".strip()
            
            # اگه اسم عوض شده بود، آپدیت رو انجام بده
            if new_first_name != current_first_name:
                await client(UpdateProfileRequest(first_name=new_first_name))
                
        except Exception as e:
            print(f"❌ خطا در آپدیت ساعت اسم: {e}")
            
        # هر ۶۰ ثانیه یک‌بار چک میکنه
        await asyncio.sleep(60)

async def start_name_clock():
    asyncio.ensure_future(update_name_clock())
