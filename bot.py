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

📌 ГЛАВНОЕ:
Если запрос практический — давай ГОТОВОЕ РЕШЕНИЕ, а не рассуждения.

---

📌 ССЫЛКИ:
Если просят сайты / где купить:

Формат:
1. Название
🔗 ссылка
📝 кратко

---

📌 СХЕМЫ И ВИЗУАЛ:
Если пользователь просит:
- схему
- подключение
- визуально
- нарисуй

👉 ВСЕГДА:
1. Дай схему (ASCII)
2. Дай объяснение
3. Без фраз "я не могу"

---

📌 СТИЛЬ:
- чётко
- структурировано
- без воды
- как инженер

---

📌 Если код — давай в ```python```

📌 Если изображение:
- опиши
- распознай текст
- объясни интерфейс
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
# ==================== 🔴 BLOCK 6: IMAGE + SMART INTENT ====================

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


def detect_intent(text):
    text_lower = text.lower()

    # 🔥 БЫСТРЫЙ УРОВЕНЬ (главный)
    if any(w in text_lower for w in ["картин", "изображен", "нарисуй", "визуал", "покажи"]):
        return "image"

    if any(w in text_lower for w in ["схема", "подключ", "как собрать", "как работает"]):
        return "scheme"

    if any(w in text_lower for w in ["где купить", "ссылки", "сайт"]):
        return "links"

    # 🤖 GPT ТОЛЬКО ЕСЛИ НЕ ПОНЯТНО
    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": "Ответь одним словом: image, scheme, links или text."},
                {"role": "user", "content": text}
            ]
        )

        intent = response.output_text.lower().strip()

        # 🔥 нормализация
        if "image" in intent:
            return "image"
        if "scheme" in intent:
            return "scheme"
        if "links" in intent:
            return "links"

        return "text"

    except:
        return "text"


async def generate_scheme_image(message, text):
    try:
        analysis = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": "Разбей задачу на элементы схемы."},
                {"role": "user", "content": text}
            ]
        )

        structured = analysis.output_text

        prompt = f"""
        Create a clean technical diagram.

        Based on:
        {structured}

        Style:
        - white background
        - labeled blocks
        - arrows
        - clear layout
        """

        result = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )

        image_bytes = base64.b64decode(result.data[0].b64_json)
        photo = BufferedInputFile(image_bytes, filename="scheme.png")

        await message.answer_photo(photo)

    except Exception as e:
        await message.answer(f"⚠️ Ошибка генерации схемы: {e}")
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
        user_history.setdefault(user_id, [])

        text = ""

        # 🎤 голос
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
            await message.answer(f"📝 {text}")

        else:
            text = message.text or ""

        if not text.strip():
            await message.answer("⚠️ Я не понял сообщение")
            return

        # 🔥 intent
        intent = detect_intent(text)

        # ================== РЕАКЦИЯ ==================

        if intent == "image":
            await generate_scheme_image(message, text)
            return

        if intent == "scheme":
            await generate_scheme_image(message, text)

            response = client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ]
            )

            await message.answer(response.output_text, reply_markup=main_keyboard())
            return

        # 📷 входящая картинка
        if message.photo:
            file = await bot.get_file(message.photo[-1].file_id)
            file_path = f"image_{user_id}.jpg"
            await bot.download_file(file.file_path, destination=file_path)

            last_image[user_id] = file_path

            await message.answer(
                "📷 Что сделать с изображением?\n"
                "— Описать\n— Улучшить\n— Изменить"
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

        # 🧠 память
        user_history[user_id].append({"role": "user", "content": text})
        user_history[user_id] = user_history[user_id][-20:]

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if user_id in paid_users and user_id in good_memory:
            memory_text = "\n".join(good_memory[user_id][-15:])
            messages.append({"role": "system", "content": memory_text})

        messages.extend(user_history[user_id])

        response = client.responses.create(
            model="gpt-4o-mini",
            input=messages
        )

        reply = response.output_text

        user_history[user_id].append({"role": "assistant", "content": reply})
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
