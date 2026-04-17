# ==================== 🔴 BLOCK 1: INIT ====================

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

ADMIN_ID = 2016592532

user_words = {}
paid_users = {}
user_history = {}
good_memory = {}
last_bot_message = {}
last_image = {}

SYSTEM_PROMPT = """
Ты — умный ассистент.
Отвечай на языке пользователя.
Если код — давай в ```python```
Если изображение: опиши, распознай текст, объясни интерфейс.
"""
# ==================== 🔴 BLOCK 2: SERVER ====================

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
# ==================== 🔴 BLOCK 3: STORAGE ====================

def save_memory():
    with open("memory.json", "w") as f:
        json.dump(good_memory, f)
# ==================== 🔴 BLOCK 4: UI ====================

def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍", callback_data="like"),
            InlineKeyboardButton(text="🔊 Озвучить", callback_data="voice")
        ]
    ])
# ==================== 🔴 BLOCK 5: VOICE ====================

async def speak_text(message, user_id, text):
    try:
        if not text or text.strip() == "":
            await message.answer("⚠️ Нечего озвучивать")
            return

        await bot.send_chat_action(message.chat.id, "record_voice")

        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="nova",  # только женский
            input=text
        )

        audio = BufferedInputFile(speech.read(), "voice.mp3")
        await message.answer_audio(audio)

    except Exception as e:
        await message.answer(f"⚠️ Ошибка озвучки: {e}")
# ==================== 🔴 BLOCK 6: IMAGE ANALYSIS ====================

async def analyze_image(file_path):
    try:
        with open(file_path, "rb") as img:
            response = client.responses.create(
                model="gpt-4o-mini",
                input=[{
                    "role": "user",
                    "content": [
                        {"type":"input_text","text":"Опиши изображение, распознай текст и объясни интерфейс"},
                        {"type":"input_image","image": img}
                    ]
                }]
            )
        return response.output_text
    except Exception as e:
        return f"⚠️ Ошибка анализа: {e}"
# ==================== 🔴 BLOCK 7: IMAGE EDIT ====================

async def edit_image(message, file_path, user_text):
    try:
        with open(file_path, "rb") as img:
            prompt = f"""
            Отредактируй изображение максимально реалистично.
            Задача пользователя:
            {user_text}
            Сохрани лицо, стиль и освещение.
            Сделай как будто это оригинал.
            """

            result = client.images.edit(
                model="gpt-image-1",
                image=img,
                prompt=prompt
            )

        image_bytes = base64.b64decode(result.data[0].b64_json)
        photo = BufferedInputFile(image_bytes, filename="edit.png")

        await message.answer_photo(photo)

    except Exception as e:
        await message.answer(f"⚠️ Ошибка редактирования: {e}")
# ==================== 🔴 BLOCK 8: MAIN HANDLER ====================

@dp.message()
async def handle(message: types.Message):
    try:
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
            file = await bot.get_file(message.photo[-1].file_id)
            file_path = f"image_{user_id}.jpg"
            await bot.download_file(file.file_path, destination=file_path)

            last_image[user_id] = file_path

            await message.answer(
                "📷 Что вы хотите сделать с изображением?\n\n"
                "— 👀 Описать\n"
                "— 🎨 Улучшить\n"
                "— ✏️ Изменить"
            )
            return

        if user_id in last_image:
            if "опис" in text.lower():
                result = await analyze_image(last_image[user_id])
                await message.answer(result)
                return

            if any(w in text.lower() for w in ["добав", "измени", "сделай"]):
                await edit_image(message, last_image[user_id], text)
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

        await message.answer(reply, reply_markup=main_keyboard())

    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}")
# ==================== 🔴 BLOCK 9: CALLBACKS ====================

@dp.callback_query(lambda c: c.data=="voice")
async def voice(c):
    await c.answer()
    await speak_text(c.message, c.from_user.id, last_bot_message.get(c.from_user.id, ""))


@dp.callback_query(lambda c: c.data=="like")
async def like(c):
    try:
        await c.answer()

        user_id = c.from_user.id
        text = last_bot_message.get(user_id, "ответ")

        good_memory.setdefault(user_id, []).append(text)

        try:
            save_memory()
        except:
            pass

        await c.message.answer("💙 Спасибо за лайк! Это помогает развитию AI и IT 🚀")

    except Exception as e:
        await c.message.answer(f"⚠️ Ошибка лайка: {e}")
# ==================== 🔴 BLOCK 10: START ====================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
