import asyncio
import os
import time
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

ADMIN_ID = 2016592532

user_words = {}
paid_users = {}
user_history = {}
good_memory = {}

SYSTEM_PROMPT = """
Ты — Aprill, умный и безопасный AI-ассистент.

— не используй мат
— помогай понятно

Если даёшь код — делай его удобным для копирования

Используй:
👉 шаги
💡 советы
"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

def save_all():
    with open("good.json", "w") as f:
        json.dump(good_memory, f)

def load_all():
    global good_memory
    try:
        with open("good.json", "r") as f:
            good_memory = {int(k): v for k, v in json.load(f).items()}
    except:
        good_memory = {}

def like_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍", callback_data="like")]
    ])

async def generate_image(message, prompt):
    await message.answer("🎨 Генерирую...")

    enhanced_prompt = f"""
{prompt}

ultra realistic
cinematic lighting
high detail
8k quality
perfect composition
"""

    img = client.images.generate(
        model="gpt-image-1",
        prompt=enhanced_prompt
    )

    image_bytes = base64.b64decode(img.data[0].b64_json)
    photo = BufferedInputFile(image_bytes, filename="image.png")

    await message.answer_photo(photo, reply_markup=like_keyboard())
    @dp.message()
async def handle(message: types.Message):
    user_id = message.from_user.id
    text = message.text or ""

    user_history.setdefault(user_id, []).append(text)
    user_history[user_id] = user_history[user_id][-5:]

    lower = text.lower()

    if any(w in lower for w in ["сделай", "создай", "нарисуй", "картинку", "схему"]):
        await generate_image(message, text)
        return

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for msg in user_history[user_id]:
        messages.append({"role": "user", "content": msg})

    for msg in good_memory.get(user_id, [])[-3:]:
        messages.append({"role": "user", "content": f"(хороший ответ) {msg}"})

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=messages
        )
        reply = response.output_text or "..."
    except:
        reply = "⚠️ Ошибка"

    await message.answer(
        reply,
        reply_markup=like_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "like")
async def like_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    text = callback.message.text

    good_memory.setdefault(user_id, []).append(text)
    good_memory[user_id] = good_memory[user_id][-20:]

    save_all()

    await callback.message.answer("💙 Спасибо! Ты улучшаешь бота!")

async def main():
    print("Bot started...")
    threading.Thread(target=run_server).start()
    load_all()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
