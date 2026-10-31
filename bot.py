import os
import sys

# 🟢 الحل الجذري لترميز السجلات في Render
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import telebot
from flask import Flask, request, abort
from google import genai
from waitress import serve

# --- الإعدادات الأساسية ---
BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "my-super-secret-path")

if not BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Error: BOT_TOKEN and GEMINI_API_KEY must be set!")

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

try:
    genai_client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"Error initializing GenAI Client: {e}")

def sanitize_arabic_text(text: str) -> str:
    """
    تنظيف النص واستبدال الرموز الخاصة التي تسبب مشاكل ترميز (مثل النقاط)
    بشرطات آمنة 100%، مع الحفاظ الكامل على الحروف العربية.
    """
    if not text:
        return "عذراً، لم أتمكن من صياغة إجابة."
    
    # استبدال الرمز المزعج برموز ASCII آمنة تماماً
    cleaned = (
        text.replace('\u2022', '-')
        .replace('•', '-')
        .replace('–', '-')
        .replace('—', '-')
    )
    return cleaned

def generate_gemini_response(prompt: str) -> str:
    try:
        response = genai_client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        raw_text = response.text if response and response.text else "عذراً، لم أتمكن من صياغة إجابة."
        return sanitize_arabic_text(raw_text)
    except Exception as e:
        error_str = str(e)
        print(f"DETAILED GEMINI ERROR: {error_str}")
        return f"عذراً يا منذر، حدث خطأ تقني: {error_str}"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا منذر! بوت القدرات يعمل الآن بكفاءة وبأمان تام باللغة العربية 🚀.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        if message.from_user.is_bot:
            return
        bot.send_chat_action(message.chat.id, 'typing')
        response_text = generate_gemini_response(message.text)
        bot.reply_to(message, response_text)
    except Exception as e:
        print(f"Error handling message: {e}")

@app.route(f"/{WEBHOOK_SECRET}", methods=['POST'])
def webhook():
    secret_header = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    if WEBHOOK_SECRET and secret_header != WEBHOOK_SECRET:
        abort(403)
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        abort(403)

@app.route('/')
def index():
    return "Qudrat Bot is running successfully!"

def setup_webhook():
    if not RENDER_EXTERNAL_URL:
        print("RENDER_EXTERNAL_URL not set.")
        return
    webhook_url = f"{RENDER_EXTERNAL_URL}/{WEBHOOK_SECRET}"
    print(f"Setting webhook to: {webhook_url}")
    bot.remove_webhook()
    bot.set_webhook(
        url=webhook_url,
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    setup_webhook()
    port = int(os.environ.get("PORT", 10000))
    serve(app, host="0.0.0.0", port=port)
