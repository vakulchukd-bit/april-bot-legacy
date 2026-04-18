# ==================== 🔴 IMPORTS ====================
import asyncio
import os
import base64
import threading
import json
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ADMIN_ID = 2016592532

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ==================== 💾 USERS ====================
USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users():
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

users = load_users()

def get_user(user_id):
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            "is_premium": False,
            "messages": 0,
            "expires_at": None,
            "image_context": None
        }
    return users[uid]

def is_premium(user):
    if not user["is_premium"]:
        return False
    if not user["expires_at"]:
        return False
    return datetime.now() < datetime.fromisoformat(user["expires_at"])

FREE_LIMIT = 20

# ===== MEMORY =====
dialog_memory = {}
last_image = {}
edit_mode = {}
feedback_memory = {}
awaiting_image_prompt = {}

# ===== SYSTEM =====
SYSTEM_PROMPT = """
Ты — Aprill, интеллектуальный ассистент.
Ты понимаешь контекст диалога.
"""

IMAGE_STYLE = """
high quality, detailed, realistic, cinematic lighting
"""

def enhance_prompt(user_prompt, context=None):
    if context:
        return f"{IMAGE_STYLE}\n\nКонтекст: {context}\n\n{user_prompt}"
    return f"{IMAGE_STYLE}\n\n{user_prompt}"

# ===== IMAGE ANALYSIS =====
async def analyze_image(path):
    def run():
        with open(path, "rb") as img:
            r = client.responses.create(
                model="gpt-4o-mini",
                input=[{
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "Коротко опиши изображение"},
                        {"type": "input_image", "image": img.read()}
                    ]
                }]
            )
        return r.output_text
    return await asyncio.to_thread(run)

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
        [InlineKeyboardButton(text="🎨 Изменить", callback_data="img_edit")]
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

# ===== IMAGE =====
async def generate_image(prompt, context=None):
    def run():
        result = client.images.generate(
            model="gpt-image-1",
            prompt=enhance_prompt(prompt, context),
            size="1024x1024"
        )
        return base64.b64decode(result.data[0].b64_json)
    return await asyncio.to_thread(run)

async def edit_image(file_path, prompt, context=None):
    def run():
        with open(file_path, "rb") as img:
            result = client.images.edit(
                model="gpt-image-1",
                image=img,
                prompt=enhance_prompt(prompt, context)
            )
        return base64.b64decode(result.data[0].b64_json)
    return await asyncio.to_thread(run)

# ===== MAIN =====
@dp.message(lambda m: m.text or m.photo or m.voice)
async def handle(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    # 🔥 ЛИМИТ
    if not is_premium(user):
        user["messages"] += 1
        if user["messages"] > FREE_LIMIT:
            await message.answer("⛔ Демо закончено")
            save_users()
            return

    # PHOTO
    if message.photo:
        file = await bot.get_file(message.photo[-1].file_id)
        path = f"{user_id}.jpg"
        await bot.download_file(file.file_path, destination=path)

        last_image[user_id] = path

        # анализ (тихо)
        user["image_context"] = await analyze_image(path)
        save_users()

        await message.answer("📷 Что сделать?", reply_markup=image_keyboard())
        return

    text = message.text or ""

    # EDIT MODE
    if user_id in edit_mode:
        edit_mode.pop(user_id)

        img = await run_with_typing(
            message.chat.id,
            edit_image(last_image[user_id], text, user.get("image_context"))
        )

        sent = await message.answer_photo(BufferedInputFile(img, "edit.png"))
        await message.answer("Оцени 👇", reply_markup=main_keyboard(sent.message_id))
        return

    # IMAGE REQUEST
    if user_id in awaiting_image_prompt:
        awaiting_image_prompt.pop(user_id)

        img = await run_with_typing(
            message.chat.id,
            generate_image(text, user.get("image_context"))
        )

        sent = await message.answer_photo(BufferedInputFile(img, "gen.png"))
        await message.answer("Оцени 👇", reply_markup=main_keyboard(sent.message_id))
        return

    if "картин" in text.lower():
        awaiting_image_prompt[user_id] = True
        await message.answer("Какое изображение нужно?")
        return

    # GPT
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

    await message.answer(reply, reply_markup=main_keyboard(message.message_id))
    save_users()

# ===== CALLBACKS =====
@dp.callback_query(F.data == "img_edit")
async def edit_btn(c: types.CallbackQuery):
    edit_mode[c.from_user.id] = True
    await c.message.answer("✏️ Как изменить?")
    await c.answer()

@dp.callback_query(F.data.startswith("like_"))
async def like(c: types.CallbackQuery):
    await c.answer("👍")

@dp.callback_query(F.data.startswith("dislike_"))
async def dislike(c: types.CallbackQuery):
    await c.answer("👎")

# ===== START =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
