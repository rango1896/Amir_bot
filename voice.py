import os
import json
import urllib.request
from telethon import events
import core
from core import client

try:
    from vosk import Model, KaldiRecognizer
    import soundfile as sf
    import wave
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False

async def setup_vosk():
    if not VOSK_AVAILABLE: return None
    if core.vosk_model: return core.vosk_model
    model_path = "vosk-model-small-fa-0.4"
    if not os.path.exists(model_path):
        await client.send_message('me', "⏳ دانلود مدل فارسی...")
        try:
            urllib.request.urlretrieve("https://alphacephei.com/vosk/models/vosk-model-small-fa-0.4.zip", "model.zip")
            import zipfile
            with zipfile.ZipFile("model.zip", 'r') as z: z.extractall(".")
            os.remove("model.zip")
        except: return None
    core.vosk_model = Model(model_path)
    return core.vosk_model

@client.on(events.NewMessage(outgoing=True, pattern=r'^متن$'))
async def voice_to_text(event):
    if not event.message.is_reply: return
    r = await event.get_reply_message()
    if not r or not r.voice: return await event.reply("❗ ویس نیست.")
    w = await event.reply("⏳ پردازش...")
    try:
        m = await setup_vosk()
        if not m: return await w.edit("❌ مدل لود نشد.")
        v_path = await r.download_media()
        wav_path = v_path.replace(".ogg", ".wav")
        data, sr = sf.read(v_path)
        sf.write(wav_path, data, sr)
        wf = wave.open(wav_path, "rb")
        rec = KaldiRecognizer(m, wf.getframerate())
        txt = ""
        while True:
            data = wf.readframes(4000)
            if len(data) == 0: break
            if rec.AcceptWaveform(data):
                txt += json.loads(rec.Result()).get("text", "")
        txt += json.loads(rec.FinalResult()).get("text", "")
        wf.close()
        os.remove(v_path); os.remove(wav_path)
        await w.edit(f"🎙 **متن:**\n\n{txt}" if txt.strip() else "❌ نامفهوم.")
    except Exception as e: await w.edit(f"❌ خطا: {e}")
