import os
import imageio_ffmpeg

# FFmpeg Setup
os.environ["PATH"] += os.pathsep + os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())

import time
import asyncio
import threading
import yt_dlp
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# यहाँ अपना नया टोकन डालें
TOKEN = "9103593916:AAHb0TpBBkCkzNi1Q2xe8kPhsGZ15B9t4x4"

app = Flask(name)

@app.route('/')
def home():
    return "NishuAI Bot is alive!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

async def link_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    context.user_data['url'] = url
    
    keyboard = [
        [InlineKeyboardButton("🔥 1080p", callback_data="dl_1080"),
         InlineKeyboardButton("⚡️ 720p", callback_data="dl_720")],
        [InlineKeyboardButton("📱 360p (Small Size)", callback_data="dl_360"),
         InlineKeyboardButton("🎵 Audio (MP3)", callback_data="dl_mp3")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "◈ NISHU AI DOWNLOADER\n👇 Please select your download quality:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    url = context.user_data.get('url')
    
    if not url:
        await query.edit_message_text("⚠️ Link not found. Please send the link again.")
        return

    # YouTube Block Bypass (iOS Client)
    base_opts = {
        'extractor_args': {'youtube': {'player_client': ['ios', 'mweb']}},
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'outtmpl': 'media.%(ext)s',
        'quiet': True,
        'nocheckcertificate': True
    }

    if action == "dl_1080":
        ydl_opts = {**base_opts, 'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'}
        quality_text = "1080p"
    elif action == "dl_720":
        ydl_opts = {**base_opts, 'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]'}
        quality_text = "720p"
    elif action == "dl_360":
        ydl_opts = {
            **base_opts, 
            'format': 'bestvideo[height<=360]+bestaudio/best[height<=360]',
            'postprocessor_args': ['-crf', '32', '-preset', 'ultrafast'],
        }
        quality_text = "360p (Compressed)"
    elif action == "dl_mp3":
        ydl_opts = {
            **base_opts,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '64',
            }],
        }
        quality_text = "MP3 (64kbps)"
    else:
        return

    msg = await query.edit_message_text(
        f"◈ NISHU AI • ENGINE v2.0\n"
        f"╭──────────────────────\n"
        f"│ 🎬 Quality: {quality_text}\n"
        f"│ ⚡️ Status: Initializing...\n"
        f"│ 📊 Progress: ▱▱▱▱▱▱▱▱▱▱ 0%\n"
        f"╰──────────────────────\n"
        f"🚀 *Connecting to servers...*",
        parse_mode='Markdown'
    )

    last_update_time = 0
    loop = asyncio.get_running_loop()

 def progress_hook(d):
    nonlocal last_update_time
    if d['status'] == 'downloading':
        current_time = time.time()
        if current_time - last_update_time >= 4:
            last_update_time = current_time
            
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            speed = d.get('_speed_str', 'N/A').strip()
            
            if total > 0:
                percent = int((downloaded / total) * 100)
                filled = int(percent / 10)
                bar = "▰" * filled + "▱" * (10 - filled)
                
                text = (
                    f"◈ NISHU AI • ENGINE v2.0\n"
                    f"╭──────────────────────\n"
                    f"│ 🎬 Quality: {quality_text}\n"
                    f"│ 🚀 Speed: {speed}\n"
                    f"│ 📊 Progress: {bar} {percent}%\n"
                    f"╰──────────────────────\n"
                    f"📥 *Downloading... Please wait.*"
                )
                asyncio.run_coroutine_threadsafe(msg.edit_text(text, parse_mode='Markdown'), loop)
    ydl_opts['progress_hooks'] = [progress_hook]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if action == "dl_mp3":
                filename = filename.rsplit('.', 1)[0] + '.mp3'

        file_size_mb = os.path.getsize(filename) / (1024 * 1024)
        
        if file_size_mb > 50:
            await msg.edit_text(f"❌ File too large!\nSize is {file_size_mb:.1f}MB. Telegram bot limit is 50MB.\nPlease choose 360p or MP3.", parse_mode='Markdown')
            os.remove(filename)
            return

        await msg.edit_text("⚡️ Download Complete!\n📤 *Uploading to Telegram...*", parse_mode='Markdown')
        
        if action == "dl_mp3":
            with open(filename, 'rb') as audio:
                await query.message.reply_audio(audio=audio, title=info.get('title', 'Audio'))
        else:
            with open(filename, 'rb') as video:
                await query.message.reply_video(video=video, caption=f"✅ {quality_text} Downloaded Successfully!\n🤖 @NishuAI_Bot", parse_mode='Markdown')
        
        os.remove(filename)
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Download Failed:\n{str(e)[:100]}\n(The link might be invalid or blocked by YouTube)", parse_mode='Markdown')

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, link_received))
    application.add_handler(CallbackQueryHandler(button_click))
    application.run_polling()

if name == 'main':
    threading.Thread(target=run_flask).start()
    main()
