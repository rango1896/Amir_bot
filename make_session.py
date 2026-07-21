import asyncio
import os
from telethon import TelegramClient

# === حتما این مقادیر رو با اطلاعات واقعی خودت پر کن ===
API_ID =    17349            # عدد واقعی api_id
API_HASH = "344583e45741c457fe1862106095a5eb"      # رشته واقعی api_hash
SESSION_NAME = "user1"          # مطابق session_name در accounts.json
# =====================================================

async def main():
    os.makedirs("sessions", exist_ok=True)
    client = TelegramClient(f"sessions/{SESSION_NAME}", API_ID, API_HASH)
    
    print("Connecting to Telegram...")
    await client.start()  # شماره تلفن و کد لاگین رو ازت میخواد
    
    me = await client.get_me()
    print(f"\nSuccess! Session built for {me.first_name} (ID: {me.id})")
    print(f"File saved at: sessions/{SESSION_NAME}.session")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())