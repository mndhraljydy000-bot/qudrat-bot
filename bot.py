import os
import sys

# 🟢 إعادة تهيئة تدفقات الإخراج لمنع أخطاء السجلات
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# --- اعتراض httpx لتجنب أخطاء ترميز الرؤوس ---
import httpx
try:
    from httpx._utils import normalize_header_value as _orig_normalize
    def _utf8_normalize_header_value(value, encoding=None, lower=False):
        return _orig_normalize(value, encoding='utf-8', lower=lower)
    httpx._utils.normalize_header_value = _utf8_normalize_header_value
    import httpx._models
    if hasattr(httpx._models, 'normalize_header_value'):
        httpx._models.normalize_header_value = _utf8_normalize_header_value
except Exception as e:
    print(f"Patch warning: {e}")

import telebot
from flask import Flask, request, abort
from google import genai
from google.genai import types  # للتحكم في نوع الاستجابة ومحددات التكوين
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

# --- الطبقة الثالثة: التنظيف البرمجي الآمن (Safety Net) ---
def sanitize_response_safely(text: str) -> str:
    """
    لا تحذف الحروف العربية، بل تستبدل أي رمز نقطة قديم أو شاذ بشرطة آمنة.
    """
    if not text:
        return "عذراً، لم أتمكن من صياغة إجابة."
    return (
        text.replace('\u2022', '-')
            .replace('•', '-')
            .replace('–', '-')
            .replace('—', '-')
    )

# --- استدعاء جيميناي متوافق مع طبقات الحماية ---
def generate_gemini_response(user_question: str) -> str:
    try:
        # الطبقة الأولى: التوجيه الإيجابي في الـ Prompt
        prompt = f"""
أنت خبير ذكي ومختص في شرح اختبار القدرات العامة للطلاب.
أجب عن السؤال التالي باللغة العربية الفصحى وبشكل دقيق ومختصر.
**قاعدة التنسيق الإلزامية:** استخدم الأرقام (1.، 2.، 3.) أو الشرطات (-) حصراً لأي تعداد، واكتب الإجابة بوضوح وتجنب استخدام الرموز المعقدة.

السؤال: {user_question}
"""

        # الطبقة الثانية: التحكم في نوع الاستجابة (Plain Text) من خلال GenerationConfig
        response = genai_client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="text/plain",  # طلب نص عادي لتجنب ماركداوند المعقد
                temperature=0.3,
            )
        )
        
        raw_text = response.text if response and getattr(response, "text", None) else ""
        if not raw_text:
            return "عذراً، لم أتمكن من صياغة إجابة."
            
        # تطبيق الطبقة الثالثة (التنظيف الآمن)
        return sanitize_response_safely(raw_text)

    except UnicodeEncodeError as ue:
        print(f"CRITICAL UnicodeEncodeError caught: {ue}")
        return "عذراً يا منذر، واجهت مشكلة تقنية مؤقتة في ترميز النص. الرجاء إعادة إرسال السؤال."
    except Exception as e:
        err_msg = str(e)
        print(f"General Gemini Error: {err_msg}")
        return f"عذراً يا منذر، حدث خطأ تقني غير متوقع. حاول مرة أخرى."

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا منذر! بوت القدرات يعمل الآن بكفاءة وبأمان تام باللغة العربية 🚀.")

# --- الطبقة الرابعة: معالجة الأخطاء الشاملة في معالج الرسائل ---
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        if message.from_user.is_bot:
            return
        bot.send_chat_action(message.chat.id, 'typing')
        
        response_text = generate_gemini_response(message.text)
        bot.reply_to(message, response_text)
        
    except Exception as e:
        print(f"Error handling message wrapper: {e}")
        try:
            bot.reply_to(message, "عذراً، حدث خطأ أثناء إرسال الرد.")
        except:
            pass

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
