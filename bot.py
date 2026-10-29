import os
import telebot
import google.generativeai as genai
from flask import Flask

# إعداد خادم الويب الوهمي لإرضاء منصة Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Qudrat Bot is active and running!"

# جلب المفاتيح من إعدادات الاستضافة
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا منذر! بوت القدرات يعمل بنجاح تام على الاستضافة الدائمة 🚀.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        response = model.generate_content(message.text)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"عذراً، حدث خطأ تقني بسيط: {str(e)}")

# تشغيل البوت مع الخادم المحلي
if __name__ == "__main__":
    import threading
    # تشغيل البوت في خلفية خادم الويب
    threading.Thread(target=bot.infinity_polling).start()
    # تشغيل خادم الويب على البورت المخصص من Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
