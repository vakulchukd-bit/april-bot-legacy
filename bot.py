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
user_voice = {}
last_bot_message = {}
last_image = {}

CARD_NUMBER = "5168745162781329"

SYSTEM_PROMPT = """
Ты — умный ассистент.

Отвечай на языке пользователя (русский, украинский, английский и др).

Если код — давай в ```python```

Если изображение:
опиши, распознай текст, объясни интерфейс.

Отвечай понятно и живо.
"""
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

def save_data():
    with open("users.json", "w") as f:
        json.dump(paid_users, f)

def load_data():
    global paid_users
    try:
        with open("users.json", "r") as f:
            paid_users = json.load(f)
            paid_users = {int(k): v for k, v in paid_users.items()}
    except:
        paid_users = {}

def save_memory():
    with open("memory.json", "w") as f:
        json.dump(good_memory, f)
def is_paid(user_id):
    return user_id in paid_users and time.time() < paid_users[user_id]

def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍", callback_data="like")],
        [InlineKeyboardButton(text="🔊 Озвучить", callback_data="voice_menu")]
    ])

def voice_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔊 Мужской голос", callback_data="voice_male")],
        [InlineKeyboardButton(text="🔊 Женский голос", callback_data="voice_female")]
    ])

async def speak_text(message, user_id, text):
    await bot.send_chat_action(message.chat.id, "record_voice")
    await message.answer("🔊 Генерирую голос...")

    voice = user_voice.get(user_id, "female")

    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy" if voice == "male" else "nova",
        input=text
    )

    audio = BufferedInputFile(speech.read(), "voice.mp3")
    await message.answer_audio(audio)
async def analyze_image(message, file_url):
    response = client.responses.create(
        model="gpt-4o-mini",
        input=[{
            "role": "user",
            "content": [
                {"type":"input_text","text":"Опиши изображение, распознай текст и объясни интерфейс"},
                {"type":"input_image","image_url":file_url}
            ]
        }]
    )
    return response.output_text

async def improve_image(message, prompt):
    img = client.images.generate(
        model="gpt-image-1",
        prompt=f"{prompt}, youtube thumbnail, high contrast"
    )
    photo = BufferedInputFile(base64.b64decode(img.data[0].b64_json),"img.png")
    await message.answer_photo(photo)

@dp.message()
async def handle(message: types.Message):
    user_id = message.from_user.id

    if message.voice:
        file = await bot.get_file(message.voice.file_id)
        fname = f"{user_id}.ogg"
        await bot.download_file(file.file_path, destination=fname)

        with open(fname,"rb") as a:
            t = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe", file=a)

        text = t.text
        await message.answer(f"📝 {text}")
else:
        text = message.text or ""

    if message.photo:
        last_image[user_id] = message.photo[-1].file_id
        file = await bot.get_file(message.photo[-1].file_id)
        url = f"https://api.telegram.org/file/bot{TOKEN}/{file.file_path}"

        result = await analyze_image(message, url)
        await message.answer(result, reply_markup=main_keyboard())
        return

    response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {"role":"system","content":SYSTEM_PROMPT},
            {"role":"user","content":text}
        ]
    )

    reply = response.output_text
    last_bot_message[user_id] = reply

    await message.answer(reply, reply_markup=main_keyboard(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data=="voice_menu")
async def voice_menu(c):
    await c.message.answer("Выбери голос", reply_markup=voice_keyboard())

@dp.callback_query(lambda c: c.data=="voice_male")
async def male(c):
    user_voice[c.from_user.id]="male"
    await c.message.answer("🎙 Мужской голос выбран")
    await speak_text(c.message,c.from_user.id,last_bot_message.get(c.from_user.id,""))

@dp.callback_query(lambda c: c.data=="voice_female")
async def female(c):
    user_voice[c.from_user.id]="female"
    await c.message.answer("🎙 Женский голос выбран")
    await speak_text(c.message,c.from_user.id,last_bot_message.get(c.from_user.id,""))

@dp.callback_query(lambda c: c.data=="like")
async def like(c):
    good_memory.setdefault(c.from_user.id,[]).append(c.message.text)
    save_memory()
    await c.message.answer("💙 Спасибо! Ты помогаешь улучшать AI")

async def main():
    load_data()
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
