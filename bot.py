import os
import sys

# (اختياري) تأكيد ترميز الإخراج القياسي
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# --- اعتراض httpx لاستخدام utf-8 في ترميز الرؤوس ---
import httpx
try:
    from httpx._utils import normalize_header_value as _orig_normalize

    def _utf8_normalize_header_value(value, encoding=None, lower=False):
        """نسخة معدلة تفرض utf-8 بدلاً من ascii"""
        return _orig_normalize(value, encoding='utf-8', lower=lower)

    httpx._utils.normalize_header_value = _utf8_normalize_header_value
    # إعادة ربط الدالة داخل الوحدات التي استوردتها مسبقاً
    import httpx._models
    if hasattr(httpx._models, 'normalize_header_value'):
        httpx._models.normalize_header_value = _utf8_normalize_header_value
    print("✅ httpx header encoding patched to UTF-8")
except Exception as e:
    print(f"⚠️ Could not patch httpx header encoding: {e}")

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

# --- دالة آمنة لاستدعاء Gemini ---
def safe_generate_content(prompt: str) -> str:
    """
    تلتف حول generate_content لضمان عدم تسرب أي استثناء ترميز.
    """
    try:
        response = genai_client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        raw = response.text if response and getattr(response, "text", None) else ""
        return raw if raw else "عذراً، لم أتمكن من صياغة إجابة."
    except UnicodeEncodeError as ue:
        print(f"UnicodeEncodeError inside Gemini SDK: {ue}")
        return "عذراً، واجهت مشكلة في ترميز النص. حاول مرة أخرى."
    except Exception as e:
        err = str(e)
        print(f"General Gemini Error: {err}")
        return f"عذراً، حدث خطأ تقني: {err[:120]}"

def sanitize_arabic_text(text: str) -> str:
    """
    تنظيف النص مع الحفاظ على الحروف العربية وكل محارف UTF-8.
    """
    if not text:
        return "عذراً، لم أتمكن من صياغة إجابة."
    return text.replace('\u2022', '•')

def generate_gemini_response(prompt: str) -> str:
    raw = safe_generate_content(prompt)
    return sanitize_arabic_text(raw)

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
