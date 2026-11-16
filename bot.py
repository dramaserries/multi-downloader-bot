import os
import threading
import requests
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler

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
    
    if "instagram.com" in url:
        keyboard = [[InlineKeyboardButton("📥 Download Instagram Reel/Video", callback_data="dl_insta")]]
    else:
        keyboard = [
            [InlineKeyboardButton("🔥 YouTube 1080p", callback_data="dl_1080"),
             InlineKeyboardButton("⚡️ YouTube 720p", callback_data="dl_720")],
            [InlineKeyboardButton("🎵 YouTube Audio (MP3)", callback_data="dl_mp3")]
        ]
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👇 Click below to start downloading:", reply_markup=reply_markup)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    user_id = update.effective_user.id
    url = USER_URLS.get(user_id)
    
    if not url:
        await query.edit_message_text("⚠️ Link expired. Please send the link again.")
        return

    msg = await query.edit_message_text("🚀 Fetching download link via Fast API...")

    is_audio = (action == "dl_mp3")
    quality = "1080" if action == "dl_1080" else "720"

    # Using stable public Cobalt API v10/json
    api_url = "https://api.cobalt.tools/api/json"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    payload = {
        "url": url,
        "vQuality": quality,
        "isAudioOnly": is_audio
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        res_data = response.json()

        status = res_data.get("status")

        if status in ["stream", "redirect"]:
            download_url = res_data.get("url")
            
            await msg.edit_text("⚡️ Link fetched! Downloading file...")

            file_response = requests.get(download_url, stream=True)
            filename = "media.mp3" if is_audio else "media.mp4"
            
            with open(filename, "wb") as f:
                for chunk in file_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            file_size_mb = os.path.getsize(filename) / (1024 * 1024)

            if file_size_mb > 50:
                await msg.edit_text(f"❌ File too large ({file_size_mb:.1f}MB). Telegram limit is 50MB.")
                os.remove(filename)
                return

            await msg.edit_text("📤 Uploading to Telegram...")

            if is_audio:
                with open(filename, 'rb') as audio:
                    await query.message.reply_audio(audio=audio, title="Audio Download")
            else:
                with open(filename, 'rb') as video:
                    await query.message.reply_video(video=video, caption="✅ Downloaded Successfully via NishuAI!")

            os.remove(filename)
            await msg.delete()

        else:
            err_text = res_data.get("text", "Could not fetch media. Try another link.")
            await msg.edit_text(f"❌ Failed: {err_text}")

    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)[:120]}")

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, link_received))
    application.add_handler(CallbackQueryHandler(button_click))
    application.run_polling()

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    main()
