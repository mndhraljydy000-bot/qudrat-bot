import os
import sys

# 🟢 الحل الجذري: إعادة تهيئة تدفقات الإخراج إلى UTF-8 لمنع أخطاء ASCII في سجلات Render
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
    تنظيف النص لضمان توافقه التام دون الإضرار باللغة العربية.
    """
    if not text:
        return "عذراً، لم أتمكن من صياغة إجابة."
    cleaned = (
        text.replace('\u2022', '•')
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
        raw_text = response.text if response and response.text else "عذراً، لم أ
