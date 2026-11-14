import os
import sys
import base64
import telebot
from flask import Flask, request, abort
from waitress import serve
from supabase import create_client
from google import genai
from google.genai import types

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SECRET = os.environ.get("SUPABASE_SECRET")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "qudrat_secret")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")

if not BOT_TOKEN or not GEMINI_API_KEY or not SUPABASE_URL:
    raise ValueError("Missing environment variables!")

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)
supabase = create_client(SUPABASE_URL, SUPABASE_SECRET)


def search_similar_questions(query_text):
    try:
        response = supabase.rpc(
            'search_qudrat_questions',
            {'query_text': query_text, 'match_count': 3}
        ).execute()
        return response.data
    except Exception as e:
        print("Search Error:", e)
        return []


def ask_gemini(user_text, similar_questions=None, image_b64=None):
    prompt = "أنت خبير القدرات. أجب باللغة العربية الفصحى المبسطة، مع خطوات الحل.\n\n"
    if similar_questions:
        prompt += "إليك أسئلة مشابهة من بنك الأسئلة للاستئناس:\n"
        for q in similar_questions:
            prompt += f"السؤال: {q['question_text']}\nالإجابة: {q['stored_answer']}\n---\n"
    prompt += f"\nسؤال الطالب: {user_text}"
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        contents = [prompt]
        if image_b64:
            image_part = types.Part.from_bytes(
                data=base64.b64decode(image_b64),
                mime_type="image/jpeg",
            )
            contents.append(image_part)
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=contents,
        )
        return response.text
    except Exception as e:
        print("Gemini Error:", e)
        return "عذراً، حدث خطأ أثناء الاتصال بالذكاء الاصطناعي."


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك! أنا خبير القدرات. أرسل لي سؤالك نصاً أو صورة وسأحله لك فوراً. 🚀")


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        file_info = bot.get_file(message.photo[-1].file_id)
        image_bytes = bot.download_file(file_info.file_path)
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        caption = message.caption if message.caption else "حل السؤال الموجود في الصورة."
        response_text = ask_gemini(caption, image_b64=image_b64)
        bot.reply_to(message, response_text)
    except Exception as e:
        print("Photo Error:", e)
        bot.reply_to(message, "عذراً، حدث خطأ في معالجة الصورة.")


@bot.message_handler(func=lambda message: True)
def handle_text(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        similar = search_similar_questions(message.text)
        response_text = ask_gemini(message.text, similar_questions=similar)
        bot.reply_to(message, response_text)
    except Exception as e:
        print("Text Error:", e)
        bot.reply_to(message, "عذراً، حدث خطأ في معالجة النص.")


@app.route(f"/{WEBHOOK_SECRET}", methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
        bot.process_new_updates([update])
        return '', 200
    abort(403)


@app.route('/health')
def health():
    return 'OK', 200


if __name__ == "__main__":
    if RENDER_URL:
        bot.remove_webhook()
        bot.set_webhook(url=f"{RENDER_URL}/{WEBHOOK_SECRET}")
    serve(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
