import os
import time
import asyncio
import threading
import requests
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
    
    keyboard = [
        [InlineKeyboardButton("🔥 1080p", callback_data="dl_1080"),
         InlineKeyboardButton("⚡️ 720p", callback_data="dl_720")],
        [InlineKeyboardButton("📱 360p", callback_data="dl_360"),
         InlineKeyboardButton("🎵 Audio (MP3)", callback_data="dl_mp3")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "◈ NISHU AI DOWNLOADER (Cobalt Engine)\n👇 Please select your download quality:",
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
        "🚀 *Fetching direct link via Cobalt API...*",
        parse_mode='Markdown'
    )

    quality_map = {
        "dl_1080": "1080",
        "dl_720": "720",
        "dl_360": "360",
        "dl_mp3": "720"
    }
    
    is_audio = (action == "dl_mp3")
    selected_quality = quality_map.get(action, "720")

    api_url = "https://api.cobalt.tools/api/json"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    payload = {
        "url": url,
        "vQuality": selected_quality,
        "isAudioOnly": is_audio
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        
        # Debugging ke liye response print karein
        print("Cobalt Response Text:", response.text)

        try:
            res_data = response.json()
        except Exception:
            await msg.edit_text("❌ Cobalt API returned an invalid format. Try another link.", parse_mode='Markdown')
            return

        status = res_data.get("status")

        if status in ["stream", "redirect"]:
            download_url = res_data.get("url")
            
            await msg.edit_text("⚡️ Link fetched! Downloading file to send...", parse_mode='Markdown')

            file_response = requests.get(download_url, stream=True)
            filename = "media.mp3" if is_audio else "media.mp4"
            
            with open(filename, "wb") as f:
                for chunk in file_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            file_size_mb = os.path.getsize(filename) / (1024 * 1024)

            if file_size_mb > 50:
                await msg.edit_text(f"❌ File too large ({file_size_mb:.1f}MB). Telegram limit is 50MB.", parse_mode='Markdown')
                os.remove(filename)
                return

            await msg.edit_text("📤 *Uploading to Telegram...*", parse_mode='Markdown')

            if is_audio:
                with open(filename, 'rb') as audio:
                    await query.message.reply_audio(audio=audio, title="Audio Download")
            else:
                with open(filename, 'rb') as video:
                    await query.message.reply_video(video=video, caption="✅ Downloaded Successfully via Cobalt!\n🤖 @NishuAI_Bot", parse_mode='Markdown')

            os.remove(filename)
            await msg.delete()

        else:
            err_text = res_data.get("text", "Unknown error from Cobalt API")
            await msg.edit_text(f"❌ Download Failed:\n{err_text}", parse_mode='Markdown')

    except Exception as e:
        await msg.edit_text(f"❌ Error:\n{str(e)[:100]}", parse_mode='Markdown')

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, link_received))
    application.add_handler(CallbackQueryHandler(button_script := button_click))
    application.run_polling()

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    main()
