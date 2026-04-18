# ==================== 🔴 BLOCK 1: INIT ====================
import asyncio
import os
import base64
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

ADMIN_ID = 2016592532

good_memory = {}
last_bot_message = {}
last_image = {}
edit_mode = {}

paid_users = {}
user_words = {}
image_uses = {}

CARD_NUMBER = "5168745162781329"

SYSTEM_PROMPT = "Ты — живой ассистент Ayprill."

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
def save_users():
    with open("users.json", "w") as f:
        json.dump(paid_users, f)

def load_users():
    global paid_users
    try:
        with open("users.json", "r") as f:
            paid_users = json.load(f)
            paid_users = {int(k): v for k, v in paid_users.items()}
    except:
        paid_users = {}

def is_paid(user_id):
    return user_id in paid_users and time.time() < paid_users[user_id]

def can_use_image(user_id):
    if is_paid(user_id):
        return True
    return image_uses.get(user_id, 0) < 1

# ==================== 🔴 BLOCK 4: UI ====================
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

def payment_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url="https://www.privat24.ua/send/j3z5r")],
        [InlineKeyboardButton(text="📋 Скопировать карту", callback_data="copy_card")],
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data="paid")]
    ])

def admin_kb(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_{uid}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{uid}")
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

# ==================== 🔴 BLOCK 7: IMAGE ANALYSIS ====================
async def analyze_image(file_path):
    with open(file_path, "rb") as img:
        image_bytes = img.read()

    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    response = client.responses.create(
        model="gpt-4o",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Что это?"},
                {"type": "input_image","image_url":f"data:image/jpeg;base64,{base64_image}"}
            ]
        }]
    )
    return response.output_text

# ==================== 🔴 BLOCK 8: IMAGE EDIT ====================
async def edit_image(message, file_path, prompt):
    with open(file_path, "rb") as img:
        result = client.images.edit(
            model="gpt-image-1",
            image=img,
            prompt=prompt
        )
    img_bytes = base64.b64decode(result.data[0].b64_json)
    await message.answer_photo(BufferedInputFile(img_bytes,"edit.png"))

# ==================== 🔴 BLOCK 9: MAIN HANDLER ====================
@dp.message()
async def handle(message: types.Message):
    user_id = message.from_user.id

    if message.photo:
        file = await bot.get_file(message.photo[-1].file_id)
        path = f"img_{user_id}.jpg"
        await bot.download_file(file.file_path, destination=path)
        last_image[user_id] = path
        await message.answer("📷 Выбери действие:", reply_markup=image_keyboard())
        return

    if message.voice:
        text = await transcribe_voice(message, user_id)
    else:
        text = (message.text or "").lower()

    if not is_paid(user_id):
        user_words[user_id] = user_words.get(user_id, 0) + len(text.split())
        if user_words[user_id] > 70:
            await message.answer("🚫 Лимит", reply_markup=payment_keyboard())
            return

    if user_id in edit_mode and user_id in last_image:
        if not can_use_image(user_id):
            await message.answer("🚫 Лимит изображений", reply_markup=payment_keyboard())
            return

        await message.answer("🎨 Делаю...")
        await edit_image(message, last_image[user_id], text)

        if not is_paid(user_id):
            image_uses[user_id] = image_uses.get(user_id, 0) + 1

        del edit_mode[user_id]
        del last_image[user_id]
        return

    response = client.responses.create(
        model="gpt-4o-mini",
        input=text
    )

    reply = response.output_text
    last_bot_message[user_id] = reply
    await message.answer(reply, reply_markup=main_keyboard())

# ==================== 🔴 BLOCK 10: CALLBACKS ====================
@dp.callback_query(lambda c: c.data=="img_describe")
async def desc(c):
    uid = c.from_user.id
    await c.message.answer(await analyze_image(last_image[uid]))

@dp.callback_query(lambda c: c.data=="img_edit")
async def edit(c):
    uid = c.from_user.id
    if not can_use_image(uid):
        await c.message.answer("🚫 Только после оплаты", reply_markup=payment_keyboard())
        return
    edit_mode[uid] = True
    await c.message.answer("✏️ Напиши что изменить")

@dp.callback_query(lambda c: c.data=="paid")
async def paid(c):
    uid = c.from_user.id
    await bot.send_message(ADMIN_ID, f"💰 {uid} оплатил", reply_markup=admin_kb(uid))
    await c.message.answer("⏳ Ожидай подтверждения")

@dp.callback_query(lambda c: c.data.startswith("approve_"))
async def approve(c):
    if c.from_user.id != ADMIN_ID:
        return
    uid = int(c.data.split("_")[1])
    paid_users[uid] = time.time() + 30*86400
    save_users()
    await bot.send_message(uid, "✅ Оплата подтверждена")

@dp.callback_query(lambda c: c.data.startswith("reject_"))
async def reject(c):
    if c.from_user.id != ADMIN_ID:
        return
    uid = int(c.data.split("_")[1])
    await bot.send_message(uid, "❌ Оплата отклонена")

@dp.message(lambda m: m.text=="/users")
async def users(m):
    if m.from_user.id != ADMIN_ID:
        return
    text="Платные:\n"
    for uid in paid_users:
        text+=f"{uid}\n"
    await m.answer(text)

# ==================== 🔴 BLOCK 11: START ====================
async def main():
    load_users()
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
