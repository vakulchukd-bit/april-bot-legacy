# ==================== 🔴 BLOCK 1: INIT ====================
import asyncio
import os
import base64
import json
import threading
import queue
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

ADMIN_ID = 2016592532

user_history = {}
dialog_summary = {}
last_bot_message = {}

# очередь изображений
image_queue = queue.Queue()

SYSTEM_PROMPT = """
Ты — умный ассистент.

📌 ГЛАВНОЕ:
- Выполняй запрос пользователя
- Если просят изображение — оно будет создано системой
- НЕ объясняй ограничения

📌 ЗАПРЕЩЕНО:
- "я не могу создать изображение"
- "я не умею"
- "используйте сторонние сервисы"
- любые отказы

📌 ПОВЕДЕНИЕ:
- если есть задача → выполняй
- не задавай лишних вопросов
- не спорь с пользователем

📌 СТИЛЬ:
- коротко
- по делу
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
# ==================== 🔴 BLOCK 6 ====================

async def plan_tasks(text):
    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {
                    "role": "system",
                    "content": """
Разбей запрос пользователя на задачи.

Возможные:
- text
- image
- links

Ответ строго JSON список:
["text", "image"]
"""
                },
                {"role": "user", "content": text}
            ]
        )

        data = response.output_text

        if "[" in data:
            return json.loads(data)

        return ["text"]

    except:
        return ["text"]


async def update_summary(user_id):
    try:
        history = user_history[user_id][-15:]

        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {
                    "role": "system",
                    "content": "Кратко опиши смысл диалога"
                },
                *history
            ]
        )

        dialog_summary[user_id] = response.output_text

    except:
        pass
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
 # ==================== 🔴 BLOCK 8 ====================
@dp.message()
async def handle(message: types.Message):
    try:
        user_id = message.from_user.id
        user_history.setdefault(user_id, [])

        await bot.send_chat_action(message.chat.id, "typing")

        # текст / голос
        if message.voice:
            file = await bot.get_file(message.voice.file_id)
            fname = f"{user_id}.ogg"
            await bot.download_file(file.file_path, destination=fname)

            with open(fname, "rb") as a:
                t = client.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe",
                    file=a
                )
            text = t.text
        else:
            text = message.text or ""

        if not text.strip():
            await message.answer("⚠️ Не понял сообщение")
            return

        text_lower = text.lower()

        user_history[user_id].append({
            "role": "user",
            "content": text
        })

        user_history[user_id] = user_history[user_id][-20:]

        # задачи
        tasks = await plan_tasks(text)

        # принудительная картинка
        if any(w in text_lower for w in ["схем", "картин", "визуал", "нарисуй"]):
            if "image" not in tasks:
                tasks.append("image")

        tasks = tasks[:3]

        # 🚀 ЕСЛИ НУЖНА КАРТИНКА — НЕ ВЫЗЫВАЕМ GPT
        if "image" in tasks:
            await message.answer("🎨 Делаю изображение...")
            image_queue.put((user_id, message.chat.id, text))
            return

        # ===== текст =====
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *user_history[user_id][-10:]
            ]
        )

        reply = response.output_text
        last_bot_message[user_id] = reply

        await message.answer(reply, reply_markup=main_keyboard())

        # ===== ссылки =====
        if "links" in tasks:
            links = client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {"role": "system", "content": "Дай сайты"},
                    {"role": "user", "content": text}
                ]
            )
            await message.answer(links.output_text)

        await update_summary(user_id)

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

import requests

def image_worker():
    while True:
        try:
            user_id, chat_id, text = image_queue.get()

            print("🟡 generating image...")

            result = client.images.generate(
                model="gpt-image-1",
                prompt=f"Simple scene: {text}",
                size="512x512"
            )

            print("🟢 image ready")

            image_bytes = base64.b64decode(result.data[0].b64_json)

            url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            files = {"photo": ("image.png", image_bytes)}
            data = {"chat_id": chat_id}

            r = requests.post(url, data=data, files=files)

            print("📤 sent:", r.status_code)

        except Exception as e:
            print("❌ worker error:", e)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    threading.Thread(target=image_worker, daemon=True).start()

    asyncio.run(main())
