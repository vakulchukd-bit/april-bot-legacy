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

CARD_NUMBER = "5168745162781329"


# ---------- МИНИ-СЕРВЕР ДЛЯ RENDER ----------

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")


def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()


# ---------- СОХРАНЕНИЕ ----------

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


# ---------- УТИЛИТЫ ----------

def is_paid(user_id):
    return user_id in paid_users and time.time() < paid_users[user_id]


def count_words(text):
    return len(text.split())


# ---------- КНОПКИ ----------

def payment_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏦 Оплатить", url="https://www.privat24.ua/send/j3z5r")],
        [InlineKeyboardButton(text="📋 Скопировать карту", callback_data="copy_card")],
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data="paid")]
    ])


def admin_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")
        ]
    ])


# ---------- ГЕНЕРАЦИЯ ----------

async def generate_portrait(message, user_id):

    if user_id != ADMIN_ID and not is_paid(user_id):
        await message.answer(
            "❌ Доступ только по подписке\n\n💳 50 грн / 30 дней\n\n📋 Карта:\n5168 7451 6278 1329",
            reply_markup=payment_keyboard()
        )
        return

    await message.answer("🧠 Анализирую тебя...")

    try:
        history_text = "\n".join(user_history.get(user_id, []))

        analysis = client.responses.create(
            model="gpt-4o-mini",
            input=f"Опиши личность:\n{history_text}"
        )

        personality = analysis.output_text or "interesting personality"

        await message.answer("🎨 Создаю портрет...")

        img = client.images.generate(
            model="gpt-image-1",
            prompt=f"Psychological portrait: {personality}"
        )

        image_bytes = base64.b64decode(img.data[0].b64_json)
        photo = BufferedInputFile(image_bytes, filename="portrait.png")

        await message.answer_photo(photo)

    except Exception as e:
        await message.answer("⚠️ Ошибка генерации")


# ---------- ОСНОВНОЙ ХЕНДЛЕР ----------

@dp.message()
async def handle(message: types.Message):
    user_id = message.from_user.id
    text = None

    # 🎤 ГОЛОС
    if message.voice:
        try:
            await message.answer("🎤 Слушаю тебя...")

            file = await bot.get_file(message.voice.file_id)
            file_path = file.file_path

            file_name = f"voice_{user_id}.ogg"
            await bot.download_file(file_path, destination=file_name)

            with open(file_name, "rb") as audio:
                transcript = client.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe",
                    file=audio
                )

            text = transcript.text

            await message.answer(f"📝 Ты сказал:\n{text}")

            os.remove(file_name)

        except Exception:
            await message.answer("❌ Ошибка распознавания")
            return

    elif message.text:
        text = message.text.strip()

    else:
        await message.answer("Я понимаю только текст и голос 🙂")
        return

    # ПАМЯТЬ
    user_history.setdefault(user_id, []).append(text)
    user_history[user_id] = user_history[user_id][-15:]

    user_words[user_id] = user_words.get(user_id, 0) + count_words(text)

    if user_id != ADMIN_ID and not is_paid(user_id):
        if user_words[user_id] >= 100:
            await message.answer(
                "🚫 Лимит достигнут\n\n💳 50 грн / 30 дней",
                reply_markup=payment_keyboard()
            )
            return

    lower = text.lower()

    # ТРИГГЕР
    if (
        any(w in lower for w in ["сделай", "создай", "нарисуй", "сгенерируй"]) and
        any(t in lower for t in ["портрет", "фото", "картин"])
    ):
        await generate_portrait(message, user_id)
        return

    # ОТВЕТ
    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=text
        )
        reply = response.output_text or "..."
    except:
        reply = "⚠️ Ошибка"

    await message.answer(reply)


# ---------- CALLBACK ----------

@dp.callback_query(lambda c: c.data == "copy_card")
async def copy_card(callback: types.CallbackQuery):
    await callback.message.answer("📋 5168 7451 6278 1329")


@dp.callback_query(lambda c: c.data == "paid")
async def paid(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    await bot.send_message(
        ADMIN_ID,
        f"💰 Пользователь {user_id} нажал 'Я оплатил'",
        reply_markup=admin_keyboard(user_id)
    )

    await callback.message.answer("⏳ Ожидаем подтверждение оплаты")


@dp.callback_query(lambda c: c.data.startswith("approve_"))
async def approve(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])

    paid_users[user_id] = time.time() + 30 * 24 * 60 * 60
    save_data()

    await bot.send_message(user_id, "✅ Оплата подтверждена! Доступ на 30 дней")
    await callback.message.answer("Подтверждено")


@dp.callback_query(lambda c: c.data.startswith("reject_"))
async def reject(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])

    await bot.send_message(user_id, "❌ Оплата не подтверждена")
    await callback.message.answer("Отклонено")


# ---------- ЗАПУСК ----------

async def main():
    load_data()
    await dp.start_polling(bot)


if __name__ == "__main__":
    # запускаем сервер в отдельном потоке
    threading.Thread(target=run_server, daemon=True).start()

    # запускаем бота
    asyncio.run(main())
