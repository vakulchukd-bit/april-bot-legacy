import asyncio
import os
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

good_memory = {}
last_bot_message = {}
last_image = {}
edit_mode = {}

SYSTEM_PROMPT = "Ты — живой ассистент. Отвечай просто."

# ---------- SERVER ----------
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

# ---------- UI ----------
def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍", callback_data="like")]
    ])

def image_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👀 Описать", callback_data="img_describe"),
            InlineKeyboardButton(text="🎨 Изменить", callback_data="img_edit")
        ]
    ])

# ---------- TYPING ----------
async def send_typing(chat_id):
    try:
        while True:
            await bot.send_chat_action(chat_id, "typing")
            await asyncio.sleep(3)
    except:
        pass

# ---------- IMAGE ----------
async def analyze_image(file_path):
    with open(file_path, "rb") as img:
        image_bytes = img.read()

    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    response = client.responses.create(
        model="gpt-4o",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Определи что это"},
                {"type": "input_image", "image_url": f"data:image/jpeg;base64,{base64_image}"}
            ]
        }]
    )

    return response.output_text


async def edit_image(message, file_path, user_text):
    with open(file_path, "rb") as img:
        result = client.images.edit(
            model="gpt-image-1",
            image=img,
            prompt=user_text
        )

    image_bytes = base64.b64decode(result.data[0].b64_json)
    photo = BufferedInputFile(image_bytes, filename="edit.png")

    await message.answer_photo(photo)

# ---------- HANDLER ----------
@dp.message(lambda m: m.text or m.photo)
async def handle(message: types.Message):
    user_id = message.from_user.id

    # ---------- PHOTO ----------
    if message.photo:
        file = await bot.get_file(message.photo[-1].file_id)
        file_path = f"image_{user_id}.jpg"
        await bot.download_file(file.file_path, destination=file_path)

        last_image[user_id] = file_path
        await message.answer("📷 Выбери действие:", reply_markup=image_keyboard())
        return

    text = message.text or ""
    if not text:
        return

    # ---------- EDIT MODE ----------
    if user_id in edit_mode and user_id in last_image:
        await edit_image(message, last_image[user_id], text)
        del edit_mode[user_id]
        del last_image[user_id]
        return

    # ---------- TYPING + GPT ----------
    typing_task = asyncio.create_task(send_typing(message.chat.id))

    try:
        response = await asyncio.to_thread(
            lambda: client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ]
            )
        )
    finally:
        typing_task.cancel()

    reply = response.output_text

    last_bot_message[user_id] = reply

    await message.answer(reply, reply_markup=main_keyboard())

# ---------- CALLBACKS ----------
@dp.callback_query(F.data == "like")
async def like(c: types.CallbackQuery):
    try:
        await c.answer("👍")

        user_id = c.from_user.id
        text = last_bot_message.get(user_id)

        if not text:
            await c.message.answer("⚠️ Нет сообщения")
            return

        good_memory.setdefault(user_id, []).append(text)

        with open("memory.json", "w") as f:
            json.dump(good_memory, f)

        await c.message.answer("💙 Лайк сохранён")

    except Exception as e:
        await c.message.answer(f"Ошибка: {e}")

@dp.callback_query(F.data == "img_describe")
async def img_describe(c: types.CallbackQuery):
    user_id = c.from_user.id
    await c.answer()

    result = await analyze_image(last_image[user_id])
    await c.message.answer(result)

@dp.callback_query(F.data == "img_edit")
async def img_edit(c: types.CallbackQuery):
    user_id = c.from_user.id
    await c.answer()

    edit_mode[user_id] = True
    await c.message.answer("✏️ Что изменить?")

# ---------- START ----------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
