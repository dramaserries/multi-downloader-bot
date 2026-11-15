import os
import imageio_ffmpeg

# FFmpeg Setup for Render
os.environ["PATH"] += os.pathsep + os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())

import time
import asyncio
import threading
import yt_dlp
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# अपना बॉट टोकन यहाँ डालें
TOKEN = "9103593916:AAGVgk8FHYwxGdXgFC047KycAIWamTMSps8"

app = Flask(__name__)

USER_URLS = {}

@app.route('/')
def home():
    return "NishuAI Bot is alive!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

async def link_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_id = update.effective_user.id
    USER_URLS[user_id] = url
    
    # Check if link is Instagram or YouTube
    if "instagram.com" in url:
        keyboard = [[InlineKeyboardButton("📥 Download Instagram Reel/Video", callback_data="dl_insta")]]
    else:
        keyboard = [
            [InlineKeyboardButton("🔥 YouTube 1080p", callback_data="dl_1080"),
             InlineKeyboardButton("⚡️ YouTube 720p", callback_data="dl_720")],
            [InlineKeyboardButton("🎵 YouTube Audio (MP3)", callback_data="dl_mp3")]
        ]
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "◈ NISHU AI DOWNLOADER\n👇 Click below to download:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    user_id = update.effective_user.id
    url = USER_URLS.get(user_id)
    
    if not url:
        await query.edit_message_text("⚠️ Link not found or session expired. Please send the link again.")
        return

    msg = await query.edit_message_text(
        "🚀 *Processing download, please wait...*",
        parse_mode='Markdown'
    )

    try:
        if action == "dl_insta":
            ydl_opts = {
                'outtmpl': 'media.%(ext)s',
                'quiet': True,
                'nocheckcertificate': True
            }
        elif action == "dl_mp3":
            ydl_opts = {
                'extractor_args': {'youtube': {'player_client': ['android']}},
                'outtmpl': 'media.%(ext)s',
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '128',
                }],
                'quiet': True
            }
        else:
            q = "1080" if action == "dl_1080" else "720"
            ydl_opts = {
                'extractor_args': {'youtube': {'player_client': ['android']}},
                'outtmpl': 'media.%(ext)s',
                'format': f'best[height<={q}]/best',
                'quiet': True
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if action == "dl_mp3":
                filename = filename.rsplit('.', 1)[0] + '.mp3'

        file_size_mb = os.path.getsize(filename) / (1024 * 1024)

        if file_size_mb > 50:
            await msg.edit_text(f"❌ File too large ({file_size_mb:.1f}MB). Telegram limit is 50MB.")
            os.remove(filename)
            return

        await msg.edit_text("📤 *Uploading to Telegram...*", parse_mode='Markdown')

        if action == "dl_mp3":
            with open(filename, 'rb') as audio:
                await query.message.reply_audio(audio=audio, title=info.get('title', 'Audio'))
        else:
            with open(filename, 'rb') as video:
                await query.message.reply_video(video=video, caption="✅ Downloaded Successfully!\n🤖 @NishuAI_Bot", parse_mode='Markdown')

        os.remove(filename)
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Download Failed:\n{str(e)[:150]}", parse_mode='Markdown')

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, link_received))
    application.add_handler(CallbackQueryHandler(button_click))
    application.run_polling()

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    main()
