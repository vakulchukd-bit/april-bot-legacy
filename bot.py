import asyncio
import os
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

user_history = {}
good_memory = {}
user_voice = {}
last_bot_message = {}

SYSTEM_PROMPT = """
Ты — Aprill, умный ассистент.

— общайся живо
— помогай по шагам
— если картинка — анализируй
— если код — объясняй как программист
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

def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍", callback_data="like")],
        [InlineKeyboardButton(text="🔊 Читать", callback_data="choose_voice")]
    ])

def image_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👀 Что на картинке", callback_data="img_explain"),
            InlineKeyboardButton(text="🎨 Улучшить", callback_data="img_improve")
        ]
    ])

def voice_choice_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👨 Мужской", callback_data="voice_male"),
            InlineKeyboardButton(text="👩 Женский", callback_data="voice_female")
        ]
    ])

async def speak_text(message, user_id, text):
    voice = user_voice.get(user_id, "female")

    try:
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy" if voice == "male" else "nova",
            input=text
        )

        audio_bytes = speech.read()
        audio_file = BufferedInputFile(audio_bytes, filename="voice.mp3")

        await message.answer_audio(audio_file)

    except:
        await message.answer("⚠️ Ошибка озвучки")

async def generate_image(message, prompt):
    await message.answer("🎨 Делаю красиво...")

    img = client.images.generate(
        model="gpt-image-1",
        prompt=f"{prompt}, ultra realistic, cinematic lighting, 8k"
    )

    image_bytes = base64.b64decode(img.data[0].b64_json)
    photo = BufferedInputFile(image_bytes, filename="image.png")

    await message.answer_photo(photo, reply_markup=main_keyboard())
    @dp.message()
async def handle(message: types.Message):
    user_id = message.from_user.id

    # 📸 ЕСЛИ КАРТИНКА
    if message.photo:
        last_bot_message[user_id] = message.photo[-1].file_id

        if message.caption:
            text = message.caption
        else:
            await message.answer(
                "👀 Я вижу изображение. Что хочешь сделать?",
                reply_markup=image_keyboard()
            )
            return

        # анализ с текстом
        try:
            file = await bot.get_file(message.photo[-1].file_id)
            file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file.file_path}"

            response = client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": text},
                            {"type": "input_image", "image_url": file_url}
                        ]
                    }
                ]
            )

            reply = response.output_text
            last_bot_message[user_id] = reply

            await message.answer(reply, reply_markup=main_keyboard())
            return

        except:
            await message.answer("⚠️ Ошибка обработки")
            return

    # 💬 ОБЫЧНЫЙ ТЕКСТ
    text = message.text or ""

    user_history.setdefault(user_id, []).append(text)
    user_history[user_id] = user_history[user_id][-5:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for msg in user_history[user_id]:
        messages.append({"role": "user", "content": msg})

    for msg in good_memory.get(user_id, [])[-3:]:
        messages.append({"role": "user", "content": msg})

    response = client.responses.create(
        model="gpt-4o-mini",
        input=messages
    )

    reply = response.output_text
    last_bot_message[user_id] = reply

    await message.answer(reply, reply_markup=main_keyboard())


@dp.callback_query(lambda c: c.data == "choose_voice")
async def choose_voice(callback: types.CallbackQuery):
    await callback.message.answer("🎤 Выбери голос:", reply_markup=voice_choice_keyboard())


@dp.callback_query(lambda c: c.data == "voice_male")
async def male(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_voice[user_id] = "male"
    await speak_text(callback.message, user_id, last_bot_message.get(user_id, ""))


@dp.callback_query(lambda c: c.data == "voice_female")
async def female(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_voice[user_id] = "female"
    await speak_text(callback.message, user_id, last_bot_message.get(user_id, ""))


@dp.callback_query(lambda c: c.data == "like")
async def like(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    text = callback.message.text

    good_memory.setdefault(user_id, []).append(text)
    save_all()

    await callback.message.answer("💙 Спасибо!")


async def main():
    threading.Thread(target=run_server).start()
    load_all()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
