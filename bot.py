# ==================== 🔴 BLOCK 1: INIT ====================
import asyncio
import os
import base64
import json
import threading
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI

from PIL import Image, ImageEnhance
import cv2
import numpy as np

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

ADMINS = [2016592532]

good_memory = {}
last_bot_message = {}
last_image = {}
edit_mode = {}

SYSTEM_PROMPT = """
Ты — живой ассистент Ayprill.
Отвечай просто и по-человечески.
Без фраз типа "на изображении изображено".
Если фото:
— скажи что это
— объясни зачем это
"""

# ==================== 🔴 SUBS ====================
def load_subs():
    try:
        with open("subs.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_subs():
    with open("subs.json", "w") as f:
        json.dump(subscriptions, f)

subscriptions = load_subs()

# ==================== 🔴 LOG ====================
def load_logs():
    try:
        with open("subs_log.json", "r") as f:
            return json.load(f)
    except:
        return []

def save_logs():
    with open("subs_log.json", "w") as f:
        json.dump(sub_logs, f, indent=2)

sub_logs = load_logs()

def log_sub(user_id, days):
    sub_logs.append({
        "user_id": user_id,
        "days": days,
        "date": datetime.now().isoformat()
    })
    save_logs()

# ==================== 🔴 SUB LOGIC ====================
def has_sub(user_id):
    if user_id in ADMINS:
        return True

    user_id = str(user_id)

    if user_id not in subscriptions:
        return False

    expire = datetime.fromisoformat(subscriptions[user_id])
    return expire > datetime.now()

def give_sub(user_id, days=30):
    expire = datetime.now() + timedelta(days=days)
    subscriptions[str(user_id)] = expire.isoformat()
    save_subs()
    log_sub(user_id, days)

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

def image_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👀 Описать", callback_data="img_describe"),
            InlineKeyboardButton(text="🎨 Изменить", callback_data="img_edit")
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
async def transcribe_voice(message, user_id):
    file = await bot.get_file(message.voice.file_id)
    fname = f"{user_id}.ogg"
    await bot.download_file(file.file_path, destination=fname)

    with open(fname, "rb") as a:
        t = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=a
        )

    return t.text.lower()

# ==================== 🔴 BLOCK 7: IMAGE ====================
async def analyze_image(file_path):
    with open(file_path, "rb") as img:
        image_bytes = img.read()

    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    response = client.responses.create(
        model="gpt-4o",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Определи что это и объясни смысл"},
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

# ==================== 🔴 HYBRID ====================
def brighten_image(path):
    img = Image.open(path)
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.5)
    img.save(path)

def add_snow(path):
    img = cv2.imread(path)
    snow = np.random.randint(200, 255, img.shape, dtype=np.uint8)
    result = cv2.addWeighted(img, 0.8, snow, 0.2, 0)
    cv2.imwrite(path, result)

def detect_actions(text):
    actions = []
    if "освет" in text or "светлее" in text:
        actions.append("brighten")
    if "снег" in text:
        actions.append("snow")
    return actions

# ==================== 🔴 COMMANDS ====================
@dp.message(lambda m: m.text == "/paid")
async def paid(message: types.Message):
    give_sub(message.from_user.id)
    await message.answer("✅ Подписка активирована")

# ==================== 🔴 MAIN ====================
@dp.message()
async def handle(message: types.Message):
    try:
        user_id = message.from_user.id

        if not has_sub(user_id):
            await message.answer("🔒 Нет доступа. Напиши /paid")
            return

        if message.photo:
            file = await bot.get_file(message.photo[-1].file_id)
            file_path = f"{user_id}.jpg"
            await bot.download_file(file.file_path, destination=file_path)

            last_image[user_id] = file_path
            await message.answer("📷 Выбери:", reply_markup=image_keyboard())
            return

        if message.voice:
            text = await transcribe_voice(message, user_id)
        else:
            text = (message.text or "").lower()

        # 🔥 ГИБРИД
        if edit_mode.get(user_id) and user_id in last_image:
            file_path = last_image[user_id]
            actions = detect_actions(text)

            if actions:
                if "brighten" in actions:
                    brighten_image(file_path)
                if "snow" in actions:
                    add_snow(file_path)

                with open(file_path, "rb") as img:
                    photo = BufferedInputFile(img.read(), filename="result.jpg")

                await message.answer_photo(photo)

            else:
                await run_with_action(
                    message.chat.id,
                    "upload_photo",
                    edit_image(message, file_path, text)
                )

            del edit_mode[user_id]
            del last_image[user_id]
            return

        response = await asyncio.to_thread(
            lambda: client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ]
            )
        )

        await message.answer(response.output_text, reply_markup=main_keyboard())

    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}")

# ==================== 🔴 CALLBACKS ====================
@dp.callback_query(lambda c: c.data == "img_describe")
async def img_describe(c):
    user_id = c.from_user.id
    await c.answer()

    result = await analyze_image(last_image[user_id])
    await c.message.answer(result)

@dp.callback_query(lambda c: c.data == "img_edit")
async def img_edit(c):
    user_id = c.from_user.id
    await c.answer()
    edit_mode[user_id] = True
    await c.message.answer("✏️ Что изменить?")

# ==================== 🔴 START ====================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
