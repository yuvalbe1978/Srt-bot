import os
import logging
import subprocess
import math
import requests
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from groq import Groq

# שרת Web קטן לשמירת השרת ער ב-Render (עבור UptimeRobot)
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Bot is active and running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host='0.0.0.0', port=port)

# הגדרות הבוט וה-API שלך
BOT_TOKEN = "8492251026:AAFR3lHfdE2zopg1HVXjM4OEnjwkyZBpO2c"
GROQ_API_KEY = "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"

groq_client = Groq(api_key=GROQ_API_KEY)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def seconds_to_srt_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int(int((seconds - int(seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

def get_video_duration(file_path):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(result.stdout.strip())
    except:
        return 0.0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 שלום יובל! הבוט מוכן לקבל סרטונים לעיבוד ותמלול בענן.")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    status_msg = await message.reply_text("📥 מקבל את הקובץ ומתחיל בעיבוד בענן...")
    input_path = "original_media.mp4"
    try:
        media_file = message.video or message.document or message.audio
        file_obj = await context.bot.get_file(media_file.file_id)
        response = requests.get(file_obj.file_path, stream=True)
        with open(input_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024*1024):
                if chunk:
                    f.write(chunk)
        
        duration = get_video_duration(input_path)
        chunk_duration = 90
        total_parts = math.ceil(duration / chunk_duration) if duration > 0 else 1
        await status_msg.edit_text(f"⚙ מעבד ב-{total_parts} חלקים...")
        
        for i in range(total_parts):
            start_time = i * chunk_duration
            part_input = f"part_{i}.mp4"
            part_srt = f"part_{i}.srt"
            part_output = f"subtitled_part_{i}.mp4"
            
            subprocess.run(["ffmpeg", "-y", "-ss", str(start_time), "-i", input_path, "-t", str(chunk_duration), "-c", "copy", part_input], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if not os.path.exists(part_input) or os.path.getsize(part_input) == 0:
                continue
                
            with open(part_input, "rb") as f_trans:
                transcription = groq_client.audio.transcriptions.create(
                    file=(part_input, f_trans.read()), 
                    model="whisper-large-v3", 
                    language="he", 
                    response_format="verbose_json"
                )
                
            with open(part_srt, "w", encoding="utf-8") as srt_file:
                for idx, segment in enumerate(transcription.segments, start=1):
                    start_str = seconds_to_srt_time(segment["start"])
                    end_str = seconds_to_srt_time(segment["end"])
                    text = segment["text"].strip()
                    srt_file.write(f"{idx}\n{start_str} --> {end_str}\n{text}\n\n")
                    
            subprocess.run(["ffmpeg", "-y", "-i", part_input, "-vf", f"subtitles={part_srt}", "-c:a", "copy", part_output], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            await status_msg.edit_text(f"📤 שולח חלק {i+1} מתוך {total_parts}...")
            with open(part_output, "rb") as vid_out:
                await message.reply_video(video=vid_out, caption=f"🎬 חלק {i+1}/{total_parts}")
                
            for p in [part_input, part_srt, part_output]:
                if os.path.exists(p):
                    os.remove(p)
                    
        await status_msg.edit_text("✅ הסתיים בהצלחה!")
        if os.path.exists(input_path):
            os.remove(input_path)
            
    except Exception as e:
        logging.error(e)
        await status_msg.edit_text(f"❌ שגיאה: {str(e)}")

def main():
    # הפעלת שרת ה-Web ברקע
    t = Thread(target=run_web)
    t.start()

    # הפעלת הבוט של טלגרם
    app = ApplicationBuilder().token(BOT_TOKEN).read_timeout(900).write_timeout(900).connect_timeout(60).pool_timeout(60).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL | filters.AUDIO, handle_media))
    
    print("הבוט ושרת ה-Web רצים בהצלחה!")
    app.run_polling()

if __name__ == "__main__":
    main()
