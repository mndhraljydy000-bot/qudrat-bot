import os
import telebot
from google import genai
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://qudrat-bot-l22t.onrender.com")

client = genai.Client(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False)

@app.route('/')
def home():
    return "Qudrat Bot is running smoothly!"

# مسار ثابت ومباشر للـ webhook لضمان استقرار الاتصال مع تيليجرام
WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"

@app.route(WEBHOOK_PATH, methods=['POST'])
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
    try:
        bot.reply_to(message, "أهلاً بك يا منذر! بوت القدرات يعمل الآن بكفاءة تامة 🚀.")
    except Exception as e:
        print(f"Error in start: {e}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        if message.from_user.is_bot:
            return
            
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=message.text,
        )
        
        # معالجة النص وتأكيد ترميز UTF-8 لمنع أخطاء الـ ASCII نهائياً
        reply_text = response.text if response and response.text else "عذراً، لم أتمكن من صياغة إجابة."
        safe_reply = reply_text.encode('utf-8', errors='ignore').decode('utf-8')
        
        bot.reply_to(message, safe_reply)
    except Exception as e:
        error_msg = str(e).encode('utf-8', errors='ignore').decode('utf-8')
        bot.reply_to(message, f"عذراً يا منذر، حدث خطأ تقني: {error_msg}")

if __name__ == "__main__":
    # ضبط وإجبار تليجرام على تحديث رابط الـ Webhook بوضوح
    webhook_url = f"{RENDER_URL}{WEBHOOK_PATH}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    print(f"Webhook successfully set to: {webhook_url}")
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
