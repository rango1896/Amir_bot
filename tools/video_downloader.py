import os
import re
import asyncio
from telethon import events, utils
import core
import static_ffmpeg

# اضافه کردن مسیر FFmpeg
static_ffmpeg.add_paths()

# ساخت پوشه دانلود
if not os.path.exists('downloads'):
    os.makedirs('downloads')

# الگوی جستجوی لینک‌ها
URL_REGEX = r'(https?://(?:www\.)?(?:instagram\.com|youtube\.com|youtu\.be|tiktok\.com|twitter\.com|x\.com|pinterest\.com|facebook\.com)/\S+)'

# ساخت صف دانلود
download_queue = asyncio.Queue()

def download_video(url):
    import yt_dlp
    
    if not os.path.exists('cookies.txt'):
        raise Exception("فایل cookies.txt پیدا نشد!")

    ydl_opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'cookiefile': 'cookies.txt',
        'noplaylist': True,
        # استفاده از کلاینت اندروید همراه با کوکی
        'extractor_args': {'youtube': {'player_client': ['android']}}
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

@core.client.on(events.NewMessage(outgoing=True, pattern=r'^اد دانلود\s+(\S+)$'))
async def add_download_chat(event):
    target_str = event.pattern_match.group(1)
    try:
        ent = await core.client.get_entity(target_str)
        chat_id = utils.get_peer_id(ent)
        core.downloader_whitelist.add(chat_id)
        await core.save_db()
        await event.reply(f"✅ `{chat_id}` به لیست دانلود اضافه شد.")
    except Exception as e:
        await event.reply(f"❗ پیدا نشد: {e}")

@core.client.on(events.NewMessage(outgoing=True, pattern=r'^حذف دانلود\s+(\S+)$'))
async def rem_download_chat(event):
    target_str = event.pattern_match.group(1)
    try:
        ent = await core.client.get_entity(target_str)
        chat_id = utils.get_peer_id(ent)
        if chat_id in core.downloader_whitelist:
            core.downloader_whitelist.discard(chat_id)
            await core.save_db()
            await event.reply(f"❌ `{chat_id}` از لیست دانلود حذف شد.")
        else:
            await event.reply("❗ تو لیست نیست.")
    except Exception as e:
        await event.reply(f"❗ پیدا نشد: {e}")

@core.client.on(events.NewMessage())
async def video_downloader_handler(event):
    text = event.message.text or ""
    url_match = re.search(URL_REGEX, text, re.IGNORECASE)
    
    if url_match and event.chat_id in core.downloader_whitelist:
        url = url_match.group(1)
        await event.reply("⏳ درخواست شما در صف دانلود قرار گرفت. لطفا صبر کنید...")
        await download_queue.put((event, url))

async def download_worker():
    while True:
        event, url = await download_queue.get()
        try:
            file_path = await asyncio.to_thread(download_video, url)
            await event.reply(file=file_path, force_document=False)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            await event.reply(f"❌ خطا در دانلود ویدیو:\n`{e}`")
        finally:
            download_queue.task_done()

async def start_download_worker():
    asyncio.ensure_future(download_worker())
