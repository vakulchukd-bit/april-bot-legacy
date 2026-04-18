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

good_memory = {}
last_bot_message = {}
last_image = {}

SYSTEM_PROMPT = """
Ты — живой и умный ассистент Ayprill.

Отвечай естественно, как человек.
Не пиши: "на изображении изображено", "можно увидеть".

Если изображение:
— скажи кратко что это
— объясни зачем это
— будь простым и понятным

Говори как человеку, а не как отчёт.
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

# ==================== 🔴 BLOCK 5: UX ====================
async def send_action(chat_id, action):
    while True:
        try:
            await bot.send_chat_action(chat_id, action)
            await asyncio.sleep(4)
        except:
            break

async def run_with_action(chat_id, action, coro):
    task = asyncio.create_task(send_action(chat_id, action))
    try:
        return await coro
    finally:
        task.cancel()

# ==================== 🔴 BLOCK 6: VOICE ====================
async def speak_text(message, user_id, text):
    try:
        if not text:
            await message.answer("⚠️ Нечего озвучивать")
            return

        await bot.send_chat_action(message.chat.id, "record_voice")

        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="nova",
            input=text
        )

        audio = BufferedInputFile(speech.read(), "voice.mp3")
        await message.answer_audio(audio)

    except Exception as e:
        await message.answer(f"⚠️ Ошибка озвучки: {e}")

# ==================== 🔴 BLOCK 7: IMAGE ANALYSIS ====================
async def analyze_image(file_path):
    try:
        with open(file_path, "rb") as img:
            image_bytes = img.read()

        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        response = client.responses.create(
            model="gpt-4o-mini",
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Что это на изображении и зачем это? Ответь просто."},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{base64_image}"
                    }
                ]
            }]
        )

        return response.output_text

    except Exception as e:
        return f"⚠️ Ошибка анализа: {e}"

# ==================== 🔴 BLOCK 8: IMAGE EDIT ====================
async def edit_image(message, file_path, user_text):
    try:
        with open(file_path, "rb") as img:
            result = client.images.edit(
                model="gpt-image-1",
                image=img,
                prompt=user_text
            )

        image_bytes = base64.b64decode(result.data[0].b64_json)
        photo = BufferedInputFile(image_bytes, filename="edit.png")

        await message.answer_photo(photo)

    except Exception as e:
        await message.answer(f"⚠️ Ошибка редактирования: {e}")

# ==================== 🔴 BLOCK 9: MAIN HANDLER ====================
@dp.message()
async def handle(message: types.Message):
    try:
        user_id = message.from_user.id

        # ---------- VOICE ----------
        if message.voice:
            file = await bot.get_file(message.voice.file_id)
            fname = f"{user_id}.ogg"
            await bot.download_file(file.file_path, destination=fname)

            with open(fname, "rb") as a:
                t = client.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe",
                    file=a
                )

            await message.answer(f"📝 {t.text}")
            return

        # ---------- PHOTO ----------
        if message.photo:
            file = await bot.get_file(message.photo[-1].file_id)
            file_path = f"image_{user_id}.jpg"

            await bot.download_file(file.file_path, destination=file_path)
            last_image[user_id] = file_path

            await message.answer("📷 Напиши: ОПИСАТЬ или ИЗМЕНИ")
            return

        text = (message.text or "").lower()

        # ---------- IMAGE MODE ----------
        if user_id in last_image:

            if any(x in text for x in ["опис", "опиши"]):
                await message.answer("🔍 Думаю...")

                await asyncio.sleep(1)

                result = await run_with_action(
                    message.chat.id,
                    "typing",
                    analyze_image(last_image[user_id])
                )

                await message.answer(result)

                del last_image[user_id]
                return

            if any(x in text for x in ["измени", "добав", "сделай"]):
                await message.answer("🎨 Делаю...")

                await asyncio.sleep(1)

                await run_with_action(
                    message.chat.id,
                    "upload_photo",
                    edit_image(message, last_image[user_id], text)
                )

                del last_image[user_id]
                return

        # ---------- TEXT ----------
        await bot.send_chat_action(message.chat.id, "typing")

        response = await asyncio.to_thread(
            lambda: client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ]
            )
        )

        reply = response.output_text
        last_bot_message[user_id] = reply

        await message.answer(reply, reply_markup=main_keyboard())

    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}")

# ==================== 🔴 BLOCK 10: CALLBACKS ====================
@dp.callback_query(lambda c: c.data == "voice")
async def voice(c):
    await c.answer()
    await speak_text(c.message, c.from_user.id, last_bot_message.get(c.from_user.id, ""))

@dp.callback_query(lambda c: c.data == "like")
async def like(c):
    try:
        await c.answer()

        user_id = c.from_user.id
        text = last_bot_message.get(user_id, "ответ")

        good_memory.setdefault(user_id, []).append(text)
        save_memory()

        await c.message.answer("💙 Сохранено")

    except Exception as e:
        await c.message.answer(f"⚠️ Ошибка лайка: {e}")

# ==================== 🔴 BLOCK 11: START ====================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
