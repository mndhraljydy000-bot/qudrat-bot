import os
import telebot
import google.generativeai as genai
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "برنامج Qudrat Bot يعمل الآن بنجاح تام!"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا منذر! بوت القدرات يعمل الآن وجاهز للإجابة على أسئلتك 🚀.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        if message.from_user.is_bot:
            return
        response = model.generate_content(message.text)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"عذراً يا منذر، حدث خطأ تقني بسيط: {str(e)}")

# تشغيل البوت وخادم الويب معاً بشكل متزامن
if __name__ == "__main__":
    import threading
    
    # دالة لتشغيل البوت في الخلفية مع إيقاف أي تداخل سابق
    def run_bot():
        try:
            bot.infinity_polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"Polling error: {e}")

    threading.Thread(target=run_bot, daemon=True).start()
    
    # تشغيل خادم الويب لإرضاء منصة Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
