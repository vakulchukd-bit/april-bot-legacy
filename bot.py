# ==================== 🔴 BLOCK 1: INIT ====================
import asyncio
import os
import base64
import threading
import time
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

ADMIN_ID = 2016592532

last_bot_message = {}
last_image = {}
edit_mode = {}
user_words = {}
image_uses = {}

CARD_NUMBER = "5168745162781329"

# ==================== 🔴 BLOCK 2: DATABASE ====================
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    expire_time REAL
)
""")
conn.commit()

def add_user(user_id):
    expire = time.time() + 30*86400
    cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (user_id, expire))
    conn.commit()

def is_paid(user_id):
    cursor.execute("SELECT expire_time FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row and time.time() < row[0]

def get_all_users():
    cursor.execute("SELECT user_id FROM users")
    return cursor.fetchall()

# ==================== 🔴 BLOCK 3: SERVER ====================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

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
        b64 = base64.b64encode(img.read()).decode()

    response = client.responses.create(
        model="gpt-4o",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Что это?"},
                {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"}
            ]
        }]
    )
    return response.output_text

async def edit_image(message, file_path, prompt):
    with open(file_path, "rb") as img:
        result = client.images.edit(
            model="gpt-image-1",
            image=img,
            prompt=prompt
        )
    img_bytes = base64.b64decode(result.data[0].b64_json)
    await message.answer_photo(BufferedInputFile(img_bytes, "edit.png"))

# ==================== 🔴 BLOCK 8: MAIN HANDLER ====================
@dp.message()
async def handle(message: types.Message):
    user_id = message.from_user.id

    # PHOTO
    if message.photo:
        file = await bot.get_file(message.photo[-1].file_id)
        path = f"{user_id}.jpg"
        await bot.download_file(file.file_path, destination=path)

        last_image[user_id] = path
        await message.answer("📷 Выбери действие:", reply_markup=image_keyboard())
        return

    # TEXT / VOICE
    if message.voice:
        text = await transcribe_voice(message, user_id)
    else:
        text = (message.text or "").lower()

    # LIMIT TEXT
    if not is_paid(user_id):
        user_words[user_id] = user_words.get(user_id, 0) + len(text.split())
        if user_words[user_id] > 70:
            await message.answer("🚫 Лимит", reply_markup=payment_keyboard())
            return

    # IMAGE EDIT
    if user_id in edit_mode and user_id in last_image:

        if not is_paid(user_id) and image_uses.get(user_id, 0) >= 1:
            await message.answer("🚫 Бесплатный лимит исчерпан", reply_markup=payment_keyboard())
            return

        await message.answer("🎨 Делаю...")

        await run_with_action(
            message.chat.id,
            "upload_photo",
            edit_image(message, last_image[user_id], text)
        )

        if not is_paid(user_id):
            image_uses[user_id] = image_uses.get(user_id, 0) + 1

        del edit_mode[user_id]
        del last_image[user_id]
        return

    # GPT
    response = await run_with_action(
        message.chat.id,
        "typing",
        asyncio.to_thread(lambda: client.responses.create(
            model="gpt-4o-mini",
            input=text
        ))
    )

    reply = response.output_text
    last_bot_message[user_id] = reply

    await message.answer(reply, reply_markup=main_keyboard())

# ==================== 🔴 BLOCK 9: CALLBACKS ====================
@dp.callback_query(lambda c: c.data == "img_describe")
async def desc(c):
    uid = c.from_user.id

    result = await run_with_action(
        c.message.chat.id,
        "typing",
        analyze_image(last_image[uid])
    )

    await c.message.answer(result)

@dp.callback_query(lambda c: c.data == "img_edit")
async def edit(c):
    uid = c.from_user.id

    if not is_paid(uid) and image_uses.get(uid, 0) >= 1:
        await c.message.answer("🚫 Только после оплаты", reply_markup=payment_keyboard())
        return

    edit_mode[uid] = True
    await c.message.answer("✏️ Напиши что изменить")

@dp.callback_query(lambda c: c.data == "like")
async def like(c):
    await c.answer()
    await c.message.answer("💙 Принял")

@dp.callback_query(lambda c: c.data == "copy_card")
async def copy_card(c):
    await c.answer()
    await c.message.answer(f"💳 Карта:\n{CARD_NUMBER}")

# 💳 ОПЛАТА
@dp.callback_query(lambda c: c.data == "paid")
async def paid(c):
    uid = c.from_user.id
    await bot.send_message(ADMIN_ID, f"💰 {uid} хочет доступ", reply_markup=admin_kb(uid))
    await c.message.answer("⏳ Ожидай подтверждения")

@dp.callback_query(lambda c: c.data.startswith("approve_"))
async def approve(c):
    if c.from_user.id != ADMIN_ID:
        return
    uid = int(c.data.split("_")[1])
    add_user(uid)
    await bot.send_message(uid, "✅ Доступ открыт")

@dp.callback_query(lambda c: c.data.startswith("reject_"))
async def reject(c):
    if c.from_user.id != ADMIN_ID:
        return
    uid = int(c.data.split("_")[1])
    await bot.send_message(uid, "❌ Оплата не подтверждена")

@dp.message(lambda m: m.text == "/users")
async def users(m):
    if m.from_user.id != ADMIN_ID:
        return
    users = get_all_users()
    text = "\n".join([str(u[0]) for u in users]) or "Нет"
    await m.answer(text)

# ==================== 🔴 BLOCK 10: START ====================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
