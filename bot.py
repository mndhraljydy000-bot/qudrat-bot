import os
import telebot
import google.generativeai as genai
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://qudrat-bot-l22t.onrender.com")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# إنشاء البوت بدون خيوط متداخلة ليتوافق مع Flask
bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False)

@app.route('/')
def home():
    return "برنامج Qudrat Bot يعمل بنظام Webhook بنجاح تام!"

# مسار استقبال الرسائل من تيليجرام تلقائياً
@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "ok", 200
    else:
        return "Forbidden", 403

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا منذر! بوت القدرات يعمل الآن بنظام Webhook السريع والذكي 🚀.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        if message.from_user.is_bot:
            return
            
        response = model.generate_content(message.text)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"عذراً يا منذر، حدث خطأ تقني بسيط: {str(e)}")

if __name__ == "__main__":
    # حذف أي ويبهوك قديم وربط الرابط الجديد مباشرة بتيليجرام
    bot.remove_webhook()
    bot.set_webhook(url=f"{RENDER_URL}/{TELEGRAM_TOKEN}")
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
