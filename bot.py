import os
import telebot
import google.generativeai as genai

# جلب المفاتيح من إعدادات الاستضافة بأمان تام
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# إعداد نموذج جيميناي
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا منذر! بوت القدرات التجريبي يعمل بنجاح 🚀. أرسل لي أي سؤال تجريبي لنختبر الاستجابة.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        # إرسال السؤال إلى جيميناي والحصول على الرد
        response = model.generate_content(message.text)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"عذراً، حدث خطأ تقني بسيط: {str(e)}")

if __name__ == "__main__":
    bot.infinity_polling()
