import os
import imageio_ffmpeg
os.environ["PATH"] += os.pathsep + os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())

import time
import asyncio
import threading
import yt_dlp
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Enter your Telegram Bot Token inside the quotes
TOKEN = "9103593916:AAHb0TpBBkCkzNi1Q2xe8kPhsGZ15B9t4x4"

app = Flask(__name__)

@app.route('/')
def home():
    return "NishuAI Bot is alive!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# Show quality options when a link is received
async def link_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    context.user_data['url'] = url
    
    keyboard = [
        [InlineKeyboardButton("🔥 1080p", callback_data="dl_1080"),
         InlineKeyboardButton("⚡ 720p", callback_data="dl_720")],
        [InlineKeyboardButton("📱 360p", callback_data="dl_360"),
         InlineKeyboardButton("🎵 Audio (MP3)", callback_data="dl_mp3")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "◈ **NISHU AI DOWNLOADER**\n👇 Please select your download quality:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Start downloading when a quality button is clicked
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    url = context.user_data.get('url')
    
    if not url:
        await query.edit_message_text("⚠️ Link not found. Please send the link again.")
        return

    if action == "dl_1080":
        ydl_opts = {'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'}
        quality_text = "1080p"
    elif action == "dl_720":
        ydl_opts = {'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]'}
        quality_text = "720p"
    elif action == "dl_360":
        ydl_opts = {'format': 'bestvideo[height<=360]+bestaudio/best[height<=360]'}
        quality_text = "360p"
    elif action == "dl_mp3":
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        quality_text = "MP3 (Audio)"
    else:
        return

    # 1. Initial Pro Progress Bar Message
    msg = await query.edit_message_text(
        f"◈ **NISHU AI • ENGINE v2.0**\n"
        f"╭──────────────────────\n"
        f"│ 🎬 **Quality:** `{quality_text}`\n"
        f"│ ⚡ **Status:** `Initializing...`\n"
        f"│ 📊 **Progress:** `▱▱▱▱▱▱▱▱▱▱` **0%**\n"
        f"╰──────────────────────\n"
        f"🚀 *Connecting to NishuAI servers...*",
        parse_mode='Markdown'
    )

    last_update_time = 0
    loop = asyncio.get_running_loop()

    # 2. Live Progress Hook (0% to 100%)
    def progress_hook(d):
        nonlocal last_update_time
        if d['status'] == 'downloading':
            current_time = time.time()
            # Update every 3 seconds to avoid Telegram FloodWait limits
            if current_time - last_update_time >= 3:
                last_update_time = current_time
                
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                speed = d.get('_speed_str', 'N/A').strip()
                
                if total > 0:
                    percent = int((downloaded / total) * 100)
                    filled = int(percent / 10)
                    bar = "▰" * filled + "▱" * (10 - filled)
                    
                    text = (
                        f"◈ **NISHU AI • ENGINE v2.0**\n"
                        f"╭──────────────────────\n"
                        f"│ 🎬 **Quality:** `{quality_text}`\n"
                        f"│ 🚀 **Speed:** `{speed}`\n"
                        f"│ 📊 **Progress:** `{bar}` **{percent}%**\n"
                        f"╰──────────────────────\n"
                        f"⚡ *NishuAI is downloading your media...*"
                    )
                    asyncio.run_coroutine_threadsafe(
                        msg.edit_text(text, parse_mode='Markdown'), loop
                    )

        elif d['status'] == 'finished':
            text = (
                f"◈ **NISHU AI • ENGINE v2.0**\n"
                f"╭──────────────────────\n"
                f"│ 🎬 **Quality:** `{quality_text}`\n"
                f"│ ✅ **Status:** `Download Complete!`\n"
                f"│ 📊 **Progress:** `▰▰▰▰▰▰▰▰▰▰` **100%**\n"
                f"╰──────────────────────\n"
                f"📤 *Now uploading to Telegram...*"
            )
            asyncio.run_coroutine_threadsafe(
                msg.edit_text(text, parse_mode='Markdown'), loop
            )

    # Unique filename per user to prevent file conflicts
    unique_id = f"{query.from_user.id}_{int(time.time())}"
    ydl_opts['outtmpl'] = f'media_{unique_id}.%(ext)s'
    ydl_opts['progress_hooks'] = [progress_hook]

    # Background download function
    def download_media():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if action == "dl_mp3":
                filename = filename.rsplit('.', 1)[0] + '.mp3'
            return info, filename

    try:
        # Run download in a separate thread so the bot stays responsive
        info, filename = await asyncio.to_thread(download_media)

        caption_text = (
            f"✅ **{quality_text} Download Complete!**\n"
            f"⚡ *Powered by NishuAI Engine*"
        )

        if action == "dl_mp3":
            with open(filename, 'rb') as audio:
                await query.message.reply_audio(
                    audio=audio,
                    title=info.get('title', 'Audio'),
                    caption=caption_text,
                    parse_mode='Markdown'
                )
        else:
            with open(filename, 'rb') as video:
                await query.message.reply_video(
                    video=video,
                    caption=caption_text,
                    parse_mode='Markdown'
                )
        
        if os.path.exists(filename):
            os.remove(filename)
        await msg.delete()

    except Exception as e:
        await msg.edit_text(
            f"❌ **Download Failed:** `{str(e)}`\n"
            f"*(The video might be larger than 50MB, or the link could be invalid)*",
            parse_mode='Markdown'
        )

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, link_received))
    application.add_handler(CallbackQueryHandler(button_click))
    application.run_polling()

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    main()
