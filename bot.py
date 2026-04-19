import asyncio
import os
import base64
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI

from subscription_system import *

# 🔑 ДОБАВЛЕНО (router)
from blocks.router_system import decide_action
# 🔥 ДОБАВЛЕНО (response mode)
from blocks.response_mode import detect_response_mode

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
- понимаешь контекст диалога
- отвечаешь логично
- не теряешь связь между сообщениями
- если не уверен — уточняешь
"""

IMAGE_STYLE = """
high quality, detailed, realistic, cinematic lighting, 4k, sharp focus, natural colors
"""

def enhance_prompt(user_prompt):
    return f"{IMAGE_STYLE}\n\n{user_prompt}"

# ===== HELPERS =====
def is_image_request(text):
    return any(w in text.lower() for w in ["картин", "фото", "изображен", "сгенерируй"])

def is_edit_request(text):
    return any(w in text.lower() for w in ["убери", "удали", "измени", "замени", "добавь"])

def is_diagram_request(text):
    return any(w in text.lower() for w in ["чертеж", "чертёж", "схема", "диаграмма"])

def build_diagram_prompt(text):
    return f"technical drawing, blueprint, schematic, black lines, white background\n\n{text}"

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
            InlineKeyboardButton(text="🎨 Изменить", callback_data="img_edit")
        ]
    ])

def buy_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="buy_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="buy_no")
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

# ===== IMAGE =====
async def generate_image(prompt):
    def run():
        result = client.images.generate(
            model="gpt-image-1",
            prompt=enhance_prompt(prompt),
            size="1024x1024"
        )
        return base64.b64decode(result.data[0].b64_json)
    return await asyncio.to_thread(run)

async def edit_image(file_path, prompt):
    def run():
        with open(file_path, "rb") as img:
            result = client.images.edit(
                model="gpt-image-1",
                image=img,
                prompt=enhance_prompt(prompt)
            )
        return base64.b64decode(result.data[0].b64_json)
    return await asyncio.to_thread(run)

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

    sub_register(user_id)
    access, reason = sub_check_access(user_id)

    if not access:
        await message.answer(
            "💳 Подписка 30 дней — 150 грн\n\nОформить?",
            reply_markup=buy_keyboard()
        )
        return

    # PHOTO
    if message.photo:
        file = await bot.get_file(message.photo[-1].file_id)
        path = f"{user_id}.jpg"
        await bot.download_file(file.file_path, destination=path)

        last_image[user_id] = path
        await message.answer("📷 Что сделать?", reply_markup=image_keyboard())
        return

    # VOICE
    if message.voice:
        text = await run_with_typing(
            message.chat.id,
            voice_to_text(message, user_id)
        )
        await message.answer(f"🎤 {text}")
    else:
        text = message.text or ""

    # 🔑 ROUTER
    history = dialog_memory.get(user_id, [])[-10:]
    decision = decide_action(text, history)
    action = decision["action"]

    # 🔥 ДОБАВЛЕНО — режим ответа
    mode = detect_response_mode(text)

    # 🔥 DIAGRAM
    if action == "diagram":
        prompt = build_diagram_prompt(text)

        img = await run_with_typing(
            message.chat.id,
            generate_image(prompt)
        )

        sent = await message.answer_photo(
            BufferedInputFile(img, filename="diagram.png")
        )

        await message.answer("Оцени 👇", reply_markup=main_keyboard(sent.message_id))
        sub_add_message(user_id)
        return

    # 🔥 IMAGE
    if action == "image":
        img = await run_with_typing(
            message.chat.id,
            generate_image(text)
        )

        sent = await message.answer_photo(
            BufferedInputFile(img, filename="image.png")
        )

        await message.answer("Оцени 👇", reply_markup=main_keyboard(sent.message_id))
        sub_add_message(user_id)
        return

    # 🔥 CLARIFY
    if action == "clarify":
        await message.answer("Уточни, что именно ты хочешь?")
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

    # 🔥 ДОБАВЛЕНО — формат копирования
    if mode == "copy":
        reply = f"```text\n{reply}\n```"

    dialog_memory.setdefault(user_id, []).append({"role": "user", "content": text})
    dialog_memory[user_id].append({"role": "assistant", "content": reply})

    sent = await message.answer(reply, reply_markup=main_keyboard(message.message_id))
    sub_add_message(user_id)

# ===== CALLBACKS =====
@dp.callback_query(F.data.startswith("like_"))
async def like(c: types.CallbackQuery):
    feedback_memory[c.data] = "like"
    await c.answer()
    await c.message.answer("👍 Спасибо за лайк!")

@dp.callback_query(F.data.startswith("dislike_"))
async def dislike(c: types.CallbackQuery):
    feedback_memory[c.data] = "dislike"
    await c.answer()
    await c.message.answer("👎 Принял, буду лучше!")

# ===== START =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
