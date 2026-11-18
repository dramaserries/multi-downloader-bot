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
TOKEN = "9103593916:AAGDuMwa_5fcMhP8S4uZpMHbh-4FG25TdQ0"

app = Flask(__name__)

@app.route('/')
def home():
    return "NishuAI Bot is alive!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

async def link_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    context.user_data['url'] = url
    
    keyboard = [
        [InlineKeyboardButton("🔥 1080p (Best)", callback_data="dl_1080"),
         InlineKeyboardButton("⚡ 720p", callback_data="dl_720")],
        [InlineKeyboardButton("📱 360p (Small Size)", callback_data="dl_360"),
         InlineKeyboardButton("🎵 Audio (MP3)", callback_data="dl_mp3")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👇 Please select your download quality:",
        reply_markup=reply_markup
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    url = context.user_data.get('url')
    
    if not url:
        await query.edit_message_text("⚠️ Link not found. Please send the link again.")
        return

    # --- कुकीज़ चेक करें (अगर फाइल है तो लगाओ, नहीं तो बिना फाइल के ट्राई करो) ---
    base_opts = {
        'extractor_args': {'youtube': {'player_client': ['tv', 'mweb', 'web_safari']}},
        'force_ipv4': True,
        'outtmpl': 'media.%(ext)s',
        'quiet': True,
        'nocheckcertificate': True
    }

    if "instagram.com" in url:
        if os.path.exists('insta_cookies.txt'):
            base_opts['cookiefile'] = 'insta_cookies.txt'
    else:
        if os.path.exists('cookies.txt'):
            base_opts['cookiefile'] = 'cookies.txt'

    if action == "dl_1080":
        ydl_opts = {**base_opts, 'format': 'best'}
        quality_text = "1080p"
    elif action == "dl_720":
        ydl_opts = {**base_opts, 'format': 'bestvideo[height<=720]+bestaudio/best'}
        quality_text = "720p"
    elif action == "dl_360":
        ydl_opts = {
            **base_opts, 
            'format': 'bestvideo[height<=360]+bestaudio/best',
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

    # यहाँ से सारी Markdown हटा दी गई है ताकि टेलीग्राम कभी एरर न दे
    msg = await query.edit_message_text(f"⏳ {quality_text} में डाउनलोड हो रहा है, कृपया प्रतीक्षा करें...")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if action == "dl_mp3":
                filename = filename.rsplit('.', 1)[0] + '.mp3'

        file_size_mb = os.path.getsize(filename) / (1024 * 1024)
        
        if file_size_mb > 50:
            await msg.edit_text(f"❌ File too large!\nSize is {file_size_mb:.1f}MB. Telegram limit is 50MB.\nPlease choose 360p or MP3.")
            os.remove(filename)
            return

        await msg.edit_text("📤 Uploading to Telegram...")
        
        if action == "dl_mp3":
            with open(filename, 'rb') as audio:
                await query.message.reply_audio(audio=audio, title=info.get('title', 'Audio'))
        else:
            with open(filename, 'rb') as video:
                await query.message.reply_video(video=video, caption=f"✅ {quality_text} Downloaded Successfully!")
        
        os.remove(filename)
        await msg.delete()

    except Exception as e:
        # असली एरर को साफ करके आपको भेजें (कोई भी स्पेशल कैरेक्टर हटा दिया गया है)
        error_str = str(e)[:150].replace('_', ' ').replace('*', ' ').replace('[', ' ').replace('`', ' ').replace(']', ' ')
        error_msg = f"❌ Download Failed:\n{error_str}\n\n(Instagram block kar raha hai, ya link galat hai.)"
        await msg.edit_text(error_msg)

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, link_received))
    application.add_handler(CallbackQueryHandler(button_click))
    application.run_polling()

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    main()
