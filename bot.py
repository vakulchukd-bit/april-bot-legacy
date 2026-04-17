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
long_memory = {}

CARD_NUMBER = "5168745162781329"


# ---------- SYSTEM PROMPT (ФИНАЛЬНЫЙ УРОВЕНЬ) ----------

SYSTEM_PROMPT = """
Ты — Aprill, продвинутый AI-ассистент.

Ты:
— умный
— живой
— адаптивный
— технически подкованный (уровень IT-специалиста)

Ты не просто отвечаешь — ты понимаешь человека и подстраиваешься.

---

🔹 СТИЛЬ

— дружелюбный, живой
— лёгкий юмор (30–40%)
— не сухой

Используй аккуратные эмодзи:
👉 действия
⚠️ предупреждения
💡 советы
🔧 техника

НЕ перегружай текст

---

🔹 АДАПТАЦИЯ

Ты сам определяешь:

— новичок → объясняешь пошагово  
— опытный → говоришь короче  
— творчество → пишешь как автор  
— техника → становишься инженером  
— код → становишься программистом  

---

🔹 РЕЖИМЫ

🧭 НАВИГАТОР:
👉 пошагово объясняй:
Открой → Нажми → Выбери

Всегда указывай:
— где кнопка
— как она выглядит

Выделяй:
**«Названия кнопок»**

Работаешь с:
Telegram, YouTube, Instagram, TikTok, OLX, AliExpress

---

🧠 ЭКСПЕРТ:
— объясняй просто  
— затем глубже  
— используй примеры  

---

🔧 ИНЖЕНЕР:
— уточняй (цель, бюджет)
— объясняй безопасно  

⚠️ предупреждай о рисках  

---

💻 ПРОГРАММИСТ:

Ты умеешь:
— писать код  
— исправлять ошибки  
— объяснять код  
— помогать с ботами, сайтами, API  

Всегда:
👉 объясняй, что делает код  
👉 куда вставить  
👉 как запустить  

Если ошибка:
👉 найди причину  
👉 предложи исправление  

---

🛒 АНАЛИТИК:

Помогаешь с:
OLX, AliExpress и др.

Даёшь:
👉 дешёвый вариант  
👉 оптимальный  
👉 лучший  

Объясняешь разницу  

---

✍️ ПИСАТЕЛЬ:

Если текст:

— пиши живо  
— добавляй эмоции  
— используй ритм  

Пример:
“Иногда кажется, что всё остановилось…  
Но именно в этот момент начинается рост.”

НЕ пиши сухо  

---

🔹 ФОРМАТ

1. Короткое вступление  
2. Шаги 👉  
3. Совет 💡  

---

🔹 ВАЖНО

— не выдумывай опасное  
— если не уверен — скажи  
— помогай, а не усложняй  

---

🔹 ЦЕЛЬ

👉 чтобы человек понял  
👉 сделал  
👉 и остался доволен
"""


# ---------- СЕРВЕР ----------

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


def save_memory():
    with open("memory.json", "w") as f:
        json.dump(long_memory, f)


def load_memory():
    global long_memory
    try:
        with open("memory.json", "r") as f:
            long_memory = json.load(f)
            long_memory = {int(k): v for k, v in long_memory.items()}
    except:
        long_memory = {}


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


# ---------- КАРТИНКИ ----------

async def generate_image(message, user_id, prompt):

    if user_id != ADMIN_ID and not is_paid(user_id):
        await message.answer(
            "❌ Доступ только по подписке\n\n💳 50 грн / 30 дней",
            reply_markup=payment_keyboard()
        )
        return

    await message.answer("🎨 Делаю красиво...")

    try:
        enhanced_prompt = f"""
{prompt}

clean technical drawing
minimalistic style
soft blueprint background
light grid
engineering style
high clarity
"""

        img = client.images.generate(
            model="gpt-image-1",
            prompt=enhanced_prompt
        )

        image_bytes = base64.b64decode(img.data[0].b64_json)
        photo = BufferedInputFile(image_bytes, filename="image.png")

        await message.answer_photo(photo)

    except:
        await message.answer("⚠️ Ошибка генерации изображения")


# ---------- ОСНОВНОЙ ХЕНДЛЕР ----------

@dp.message()
async def handle(message: types.Message):
    user_id = message.from_user.id
    text = None

    if message.voice:
        try:
            await message.answer("🎤 Слушаю...")

            file = await bot.get_file(message.voice.file_id)
            file_name = f"voice_{user_id}.ogg"
            await bot.download_file(file.file_path, destination=file_name)

            with open(file_name, "rb") as audio:
                transcript = client.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe",
                    file=audio
                )

            text = transcript.text
            await message.answer(f"📝 Ты сказал:\n{text}")
            os.remove(file_name)

        except:
            await message.answer("❌ Ошибка")
            return

    elif message.text:
        text = message.text.strip()
    else:
        await message.answer("Я понимаю текст и голос 🙂")
        return

    user_history.setdefault(user_id, []).append(text)
    user_history[user_id] = user_history[user_id][-15:]

    user_words[user_id] = user_words.get(user_id, 0) + count_words(text)

    if user_id != ADMIN_ID and not is_paid(user_id):
        if user_words[user_id] >= 100:
            await message.answer(
                "🚫 Лимит\n💳 50 грн / 30 дней",
                reply_markup=payment_keyboard()
            )
            return

    lower = text.lower()

    if any(w in lower for w in ["сделай", "создай", "нарисуй", "схема", "чертеж"]):
        await generate_image(message, user_id, text)
        return

    # ---------- ПАМЯТЬ ----------

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for msg in user_history.get(user_id, [])[-10:-1]:
        messages.append({"role": "user", "content": msg})

    if is_paid(user_id):
        for msg in long_memory.get(user_id, [])[-20:]:
            messages.append({"role": "user", "content": msg})

    messages.append({"role": "user", "content": text})

    # ---------- ОТВЕТ ----------

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=messages
        )
        reply = response.output_text or "..."
    except:
        reply = "⚠️ Ошибка"

    await message.answer(reply)

    if is_paid(user_id):
        long_memory.setdefault(user_id, []).append(text)
        long_memory[user_id] = long_memory[user_id][-50:]
        save_memory()


# ---------- CALLBACK ----------

@dp.callback_query(lambda c: c.data == "copy_card")
async def copy_card(callback: types.CallbackQuery):
    await callback.message.answer("📋 5168 7451 6278 1329")


@dp.callback_query(lambda c: c.data == "paid")
async def paid(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    await bot.send_message(
        ADMIN_ID,
        f"💰 Пользователь {user_id} оплатил",
        reply_markup=admin_keyboard(user_id)
    )

    await callback.message.answer("⏳ Проверка оплаты")


@dp.callback_query(lambda c: c.data.startswith("approve_"))
async def approve(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    paid_users[user_id] = time.time() + 30*24*3600
    save_data()
    await bot.send_message(user_id, "✅ Оплата подтверждена!")


# ---------- ЗАПУСК ----------

async def main():
    print("Bot started...")
    threading.Thread(target=run_server).start()
    load_data()
    load_memory()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
