import os
import re
import asyncio
from telethon import events
import core
import static_ffmpeg

# اضافه کردن مسیر FFmpeg دانلود شده توسط پایتون به متغیرهای محیطی
os.environ["PATH"] = static_ffmpeg.run.add_path() + os.pathsep + os.environ.get("PATH", "")

# ساخت پوشه دانلود اگه وجود نداشت
if not os.path.exists('downloads'):
    os.makedirs('downloads')

# الگوی جستجوی لینک‌ها
URL_REGEX = r'(https?://(?:www\.)?(?:instagram\.com|youtube\.com|youtu\.be|tiktok\.com|twitter\.com|x\.com|pinterest\.com|facebook\.com)/\S+)'

def download_video(url):
    """تابع دانلود ویدیو"""
    import yt_dlp
    ydl_opts = {
        'format': 'best[height<=720]', 
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

@core.client.on(events.NewMessage(incoming=True))
async def video_downloader_handler(event):
    text = event.message.text or ""
    url_match = re.search(URL_REGEX, text, re.IGNORECASE)
    
    if url_match and not event.out:
        url = url_match.group(1)
        
        if event.is_private:
            await event.reply("⏳ در حال دانلود ویدیو... لطفا کمی صبر کن.")
            
            try:
                # اجرای دانلود در بک‌گراند
                file_path = await asyncio.to_thread(download_video, url)
                
                # ارسال ویدیو
                await event.reply(file=file_path, force_document=False)
                
                # پاک کردن فایل
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
            except Exception as e:
                await event.reply(f"❌ خطا در دانلود ویدیو:\n`{e}`")
