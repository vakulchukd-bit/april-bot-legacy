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

# ================= MEMORY =================
dialog_memory = {}
last_bot_message = {}
last_image = {}
edit_mode = {}

SYSTEM_PROMPT = """
Ты умный ассистент.

Если пользователь исправляет тебя:
— признай ошибку
— извинись кратко
— сразу исправь

Если задача понятна:
— делай сразу

Если не понятна:
— уточни
"""

# ================= SERVER =================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

# ================= UI =================
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

# ================= TYPING =================
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

# ================= LOGIC =================
def is_correction(text):
    triggers = ["не так", "не надо", "не круглая", "ошибка", "не это"]
    return any(t in text.lower() for t in triggers)

def is_new_task(text):
    triggers = ["другое", "по другому", "сделай", "теперь"]
    return any(t in text.lower() for t in triggers)

def build_context(user_id, new_text):
    history = dialog_memory.get(user_id, [])[-4:]
    combined = ""

    for msg in history:
        if msg["role"] == "user":
            combined += msg["content"] + " "

    combined += new_text
    return combined.strip()

# ================= VOICE =================
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

# ================= IMAGE =================
async def analyze_image(file_path):
    def run():
        with open(file_path, "rb") as img:
            b64 = base64.b64encode(img.read()).decode()

        r = client.responses.create(
            model="gpt-4o",
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text",
                     "text": "Скажи по-человечески что это и зачем это используется"},
                    {"type": "input_image",
                     "image_url": f"data:image/jpeg;base64,{b64}"}
                ]
            }]
        )
        return r.output_text

    return await asyncio.to_thread(run)

async def edit_image(file_path, prompt):
    def run():
        with open(file_path, "rb") as img:
            result = client.images.edit(
                model="gpt-image-1",
                image=img,
                prompt=f"Добавь реалистично: {prompt}"
            )
        return base64.b64decode(result.data[0].b64_json)

    return await asyncio.to_thread(run)

# ================= MAIN =================
@dp.message(lambda m: m.text or m.photo or m.voice)
async def handle(message: types.Message):
    user_id = message.from_user.id

    # ---------- PHOTO ----------
    if message.photo:
        file = await bot.get_file(message.photo[-1].file_id)
        path = f"{user_id}.jpg"
        await bot.download_file(file.file_path, destination=path)

        last_image[user_id] = path
        await message.answer("📷 Выбери действие:", reply_markup=image_keyboard())
        return

    # ---------- VOICE ----------
    if message.voice:
        text = await run_with_typing(
            message.chat.id,
            voice_to_text(message, user_id)
        )
        await message.answer(f"📝 {text}")
    else:
        text = message.text or ""

    # ---------- EDIT ----------
    if user_id in edit_mode and user_id in last_image:
        img = await run_with_typing(
            message.chat.id,
            edit_image(last_image[user_id], text)
        )

        await message.answer_photo(
            BufferedInputFile(img, filename="edit.png")
        )

        del edit_mode[user_id]
        del last_image[user_id]
        return

    # ---------- LOGIC ----------
    if is_new_task(text):
        dialog_memory[user_id] = []

    if is_correction(text):
        smart_text = f"""
Я ошибся ранее. Исправляю.

Запрос пользователя:
{text}
"""
    else:
        smart_text = build_context(user_id, text)

    # ---------- GPT ----------
    async def ask():
        def run():
            r = client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": smart_text}
                ]
            )
            return r.output_text

        return await asyncio.to_thread(run)

    reply = await run_with_typing(message.chat.id, ask())

    last_bot_message[user_id] = reply

    # память
    dialog_memory.setdefault(user_id, []).append({
        "role": "user",
        "content": text
    })
    dialog_memory[user_id].append({
        "role": "assistant",
        "content": reply
    })

    # ---------- CODE FORMAT ----------
    if any(w in reply.lower() for w in ["<html", "button", "css", "def", "function"]):
        await message.answer(
            f"```html\n{reply}\n```",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )
    else:
        await message.answer(reply, reply_markup=main_keyboard())

# ================= CALLBACK =================
@dp.callback_query(F.data == "like")
async def like(c: types.CallbackQuery):
    await c.answer("👍")
    await c.message.answer("💙 Сохранено")

# ================= START =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
