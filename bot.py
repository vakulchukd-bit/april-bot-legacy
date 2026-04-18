import asyncio
import os
import base64
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ===== MEMORY =====
dialog_memory = {}
last_image = {}
edit_mode = {}
feedback_memory = {}
awaiting_image_prompt = {}

# ===== SYSTEM =====
SYSTEM_PROMPT = """
Ты — Aprill, интеллектуальный ассистент.

Ты:
- отвечаешь как человек
- даёшь точные и умные ответы
- адаптируешься под пользователя
- стремишься к качеству

Если можно сделать лучше — делай лучше.
"""

# ===== IMAGE STYLE =====
IMAGE_STYLE = """
high quality, detailed, realistic, 4k, natural colors
"""

def enhance_prompt(user_prompt):
    return f"{IMAGE_STYLE}\n{user_prompt}"

# ===== SERVER =====
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

# ===== UI =====
def main_keyboard(msg_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍", callback_data=f"like_{msg_id}"),
            InlineKeyboardButton(text="👎", callback_data=f"dislike_{msg_id}")
        ]
    ])

def image_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👀 Описать", callback_data="img_describe"),
            InlineKeyboardButton(text="🎨 Изменить", callback_data="img_edit")
        ]
    ])

# ===== TYPING =====
async def typing_loop(chat_id):
    try:
        while True:
            await bot.send_chat_action(chat_id, "typing")
            await asyncio.sleep(2)
    except:
        pass

async def run_with_typing(chat_id, coro):
    task = asyncio.create_task(typing_loop(chat_id))
    try:
        return await coro
    finally:
        task.cancel()

# ===== IMAGE GENERATE =====
async def generate_image(prompt, user_id):
    def run():
        result = client.images.generate(
            model="gpt-image-1",
            prompt=enhance_prompt(prompt),
            size="1024x1024"
        )
        return base64.b64decode(result.data[0].b64_json)

    img_bytes = await asyncio.to_thread(run)

    # 🔥 СОХРАНЯЕМ ФАЙЛ (чтобы кнопки работали)
    path = f"{user_id}_image.png"
    with open(path, "wb") as f:
        f.write(img_bytes)

    last_image[user_id] = path
    return img_bytes

# ===== IMAGE ANALYZE =====
async def analyze_image(file_path):
    def run():
        with open(file_path, "rb") as img:
            b64 = base64.b64encode(img.read()).decode()

        r = client.responses.create(
            model="gpt-4o",
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Опиши изображение подробно"},
                    {"type": "input_image", "image_url": f"data:image/png;base64,{b64}"}
                ]
            }]
        )
        return r.output_text

    return await asyncio.to_thread(run)

# ===== IMAGE EDIT =====
async def edit_image(file_path, prompt, user_id):
    def run():
        with open(file_path, "rb") as img:
            result = client.images.edit(
                model="gpt-image-1",
                image=img,
                prompt=enhance_prompt(prompt)
            )
        return base64.b64decode(result.data[0].b64_json)

    img_bytes = await asyncio.to_thread(run)

    # 🔥 обновляем файл
    path = f"{user_id}_edit.png"
    with open(path, "wb") as f:
        f.write(img_bytes)

    last_image[user_id] = path
    return img_bytes

# ===== VOICE =====
async def voice_to_text(message, user_id):
    file = await bot.get_file(message.voice.file_id)
    path = f"{user_id}.ogg"
    await bot.download_file(file.file_path, destination=path)

    def run():
        with open(path, "rb") as f:
            t = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=f
            )
        return t.text

    return await asyncio.to_thread(run)

# ===== MAIN =====
@dp.message(lambda m: m.text or m.photo or m.voice)
async def handle(message: types.Message):
    user_id = message.from_user.id

    # VOICE
    if message.voice:
        text = await run_with_typing(
            message.chat.id,
            voice_to_text(message, user_id)
        )
        await message.answer(f"🎤 Ты сказал: {text}")
    else:
        text = message.text or ""

    # ===== УТОЧНЕНИЕ ДЛЯ КАРТИНКИ =====
    if user_id in awaiting_image_prompt:
        awaiting_image_prompt.pop(user_id)

        img = await run_with_typing(
            message.chat.id,
            generate_image(text, user_id)
        )

        sent = await message.answer_photo(
            BufferedInputFile(img, filename="image.png"),
            reply_markup=image_keyboard()  # 🔥 КНОПКИ ТУТ
        )

        await message.answer("Оцени 👇", reply_markup=main_keyboard(sent.message_id))
        return

    # ===== ЗАПРОС НА КАРТИНКУ =====
    if any(w in text.lower() for w in ["картин", "фото", "изображен", "сгенерируй"]):
        awaiting_image_prompt[user_id] = True
        await message.answer("Какое именно изображение тебе нужно?")
        return

    # ===== РЕДАКТИРОВАНИЕ (после кнопки) =====
    if user_id in edit_mode and user_id in last_image:
        img = await run_with_typing(
            message.chat.id,
            edit_image(last_image[user_id], text, user_id)
        )

        sent = await message.answer_photo(
            BufferedInputFile(img, filename="edit.png"),
            reply_markup=image_keyboard()
        )

        await message.answer("Оцени 👇", reply_markup=main_keyboard(sent.message_id))

        del edit_mode[user_id]
        return

    # ===== GPT =====
    history = dialog_memory.get(user_id, [])[-6:]

    async def ask():
        def run():
            r = client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *history,
                    {"role": "user", "content": text}
                ]
            )
            return r.output_text
        return await asyncio.to_thread(run)

    reply = await run_with_typing(message.chat.id, ask())

    dialog_memory.setdefault(user_id, []).append({"role": "user", "content": text})
    dialog_memory[user_id].append({"role": "assistant", "content": reply})

    await message.answer(reply)

# ===== CALLBACKS =====
@dp.callback_query(F.data == "img_describe")
async def img_describe(c: types.CallbackQuery):
    uid = c.from_user.id
    await c.answer()

    if uid not in last_image:
        await c.message.answer("Нет изображения")
        return

    result = await analyze_image(last_image[uid])
    await c.message.answer(result)

@dp.callback_query(F.data == "img_edit")
async def img_edit(c: types.CallbackQuery):
    uid = c.from_user.id
    await c.answer()

    if uid not in last_image:
        await c.message.answer("Нет изображения")
        return

    edit_mode[uid] = True
    await c.message.answer("Что изменить?")

# ===== START =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
