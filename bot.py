import os
import sys
import time
import random
import requests

# 🟢 إجبار تدفقات الإخراج على UTF-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import telebot
from flask import Flask, request, abort
from waitress import serve

# --- تنظيف وقراءة متغيرات البيئة بـ strip لمنع أي أسطر جديدة بالخطأ ---
BOT_TOKEN = (os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN") or "").strip()
GEMINI_API_KEY = (os.environ.get("GEMINI_API_KEY") or "").strip()
RENDER_EXTERNAL_URL = (os.environ.get("RENDER_EXTERNAL_URL") or "").strip()
WEBHOOK_SECRET = (os.environ.get("WEBHOOK_SECRET") or "my-super-secret-path").strip()

if not BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Error: BOT_TOKEN and GEMINI_API_KEY must be set!")

# 🛡️ فحص احترازي لمنع تمرير أسطر جديدة داخل الرؤوس
if "\n" in BOT_TOKEN or "\r" in BOT_TOKEN or "\n" in GEMINI_API_KEY or "\r" in GEMINI_API_KEY:
    raise ValueError("CRITICAL: API Key or Token contains newline characters! Please fix in Render Environment.")

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

def generate_gemini_response(prompt: str) -> str:
    """
    استدعاء Gemini REST API مع نظام إعادة المحاولة الذكية والتبديل التلقائي بين النماذج لتجاوز ضغط الخوادم (503).
    """
    models_to_try = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-2.0-flash"]
    
    full_prompt = (
        f"{prompt}\n\n"
        "(أجب باللغة العربية الفصحى بشكل دقيق ومبسط يناسب طلاب اختبار القدرات، وتجنب الرموز المعقدة)."
    )
    
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}]
    }
    
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "x-goog-api-key": GEMINI_API_KEY
    }

    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        print(f"Trying model: {model_name}", flush=True)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=60)
                print(f"Gemini Status ({model_name}): {response.status_code}", flush=True)
                
                # إذا كان النموذج مزدحمًا (503)، انتظر وأعد المحاولة
                if response.status_code == 503:
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) + random.uniform(0, 1)
                        print(f"Model {model_name} is busy. Retrying in {wait_time:.1f}s...", flush=True)
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"Model {model_name} still busy after {max_retries} attempts. Switching model...", flush=True)
                        break
                
                # إذا كان النموذج غير موجود (404)، انتقل فورًا للنموذج التالي
                if response.status_code == 404:
                    print(f"Model {model_name} not found. Switching...", flush=True)
                    break
                
                response.raise_for_status()
                data = response.json()

                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        text = parts[0]["text"]
                        return text.replace('\u2022', '-').replace('•', '-')

                return "عذراً، لم أتمكن من صياغة إجابة."
                
            except requests.exceptions.HTTPError:
                print(f"HTTP Error on {model_name}. Switching...", flush=True)
                break
            except requests.exceptions.RequestException as e:
                print(f"RequestException on {model_name}: {e}", flush=True)
                if attempt == max_retries - 1:
                    break
                time.sleep(2 ** attempt)

    return "عذراً، جميع النماذج مزدحمة حالياً. الرجاء المحاولة بعد قليل."

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
        print(f"Error handling message: {e}", flush=True)

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
        print("RENDER_EXTERNAL_URL not set.", flush=True)
        return
    webhook_url = f"{RENDER_EXTERNAL_URL}/{WEBHOOK_SECRET}"
    print(f"Setting webhook to: {webhook_url}", flush=True)
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
