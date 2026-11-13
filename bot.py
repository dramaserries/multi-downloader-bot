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

# यहाँ अपना नया टेलीग्राम बॉट टोकन डालें
TOKEN = "9103593916:AAHb0TpBBkCkzNi1Q2xe8kPhsGZ15B9t4x4"

app = Flask(name)

@app.route('/')
def home():
    return "NishuAI Bot is alive!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# लिंक मिलने पर क्वालिटी के बटन दिखाना
async def link_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    context.user_data['url'] = url
    
    keyboard = [
        [InlineKeyboardButton("🔥 1080p", callback_data="dl_1080"),
         InlineKeyboardButton("⚡️ 720p", callback_data="dl_720")],
        [InlineKeyboardButton("📱 360p (Small)", callback_data="dl_360"),
         InlineKeyboardButton("🎵 Audio (MP3)", callback_data="dl_mp3")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "◈ NISHU AI DOWNLOADER\n👇 Please select your download quality:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# डाउनलोड शुरू करना और प्रोग्रेस बार दिखाना
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    url = context.user_data.get('url')
    
    if not url:
        await query.edit_message_text("⚠️ Link not found. Please send the link again.")
        return

    # YouTube ब्लॉक बायपास और कंप्रेशन सेटिंग्स
    base_opts = {
    'extractor_args': {'youtube': {'player_client': ['ios', 'mweb']}}, # iOS क्लाइंट ब्लॉक को बायपास करेगा
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

    # 1. इनिशियल प्रोग्रेस बार मैसेज
    msg = await query.edit_message_text(
        f"◈ NISHU AI • ENGINE v2.0\n"
        f"╭──────────────────────\n"
        f"│ 🎬 Quality: {quality_text}\n"
        f"│ ⚡️ Status: Initializing...\n"
        f"│ 📊 Progress: ▱▱▱▱▱▱▱▱▱▱ 0%**\n"
        f"╰──────────────────────\n"
        f"🚀 *Connecting to servers...*",
        parse_mode='Markdown'
    )

    last_update_time = 0
    loop = asyncio.get_running_loop()

    # 2. लाइव प्रोग्रेस हुक (प्रोग्रेस बार को अपडेट करने के लिए)
    def progress_hook(d):
        nonlocal last_update_time
        if d['status'] == 'downloading':
            current_time = time.time()
            # हर 4 सेकंड में अपडेट करें ताकि Telegram ब्लॉक न करे
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
                    # सुरक्षित तरीके से मैसेज अपडेट करें
                    asyncio.run_coroutine_threadsafe(msg.edit_text(text, parse_mode='Markdown'), loop)

    # 3. डाउनलोड शुरू करें
    ydl_opts['progress_hooks'] = [progress_hook]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if action == "dl_mp3":
                filename = filename.rsplit('.', 1)[0] + '.mp3'

        # 4. फाइल का साइज़ चेक करें (50MB लिमिट)
        file_size_mb = os.path.getsize(filename) / (1024 * 1024)
        
        if file_size_mb > 50:
            await msg.edit_text(f"❌ फाइल बहुत बड़ी है!\nफाइल का साइज़ {file_size_mb:.1f}MB है। Telegram बॉट की लिमिट 50MB है।\nकृपया 360p या MP3 चुनें।", parse_mode='Markdown')
            os.remove(filename)
            return

        # 5. फाइल भेजें
        await msg.edit_text("⚡️ Download Complete!\n📤 *Uploading to Telegram...*", parse_mode='Markdown')
        
        if action == "dl_mp3":
            with open(filename, 'rb') as audio:
                await query.message.reply_audio(audio=audio, title=info.get('title', 'Audio'))
        else:
            with open(filename, 'rb') as video:
                await query.message.reply_video(video=video, caption=f"✅ {quality_text} वीडियो डाउनलोड हो गया!\n🤖 @NishuAI_Bot", parse_mode='Markdown')
        
        # 6. सफाई (Cleanup)
        os.remove(filename)
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Download Failed:\n{str(e)[:100]}\n(हो सकता है लिंक गलत हो या वीडियो 50MB से बड़ा हो)", parse_mode='Markdown')

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, link_received))
    application.add_handler(CallbackQueryHandler(button_click))
    application.run_polling()

if name == 'main':
    threading.Thread(target=run_flask).start()
    main()
