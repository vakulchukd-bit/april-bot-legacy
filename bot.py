import asyncio
import os
import base64
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI

# 🔑 ДОБАВЛЕНО
from subscription_system import *
from blocks.input_system import process_input
from blocks.diagram_system import build_diagram_prompt, is_diagram_request  # ← НОВЫЙ ИМПОРТ

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

# 🔑 ДОБАВЛЕНО
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

    # 🔑 ЕДИНЫЙ ВХОД
    data = await process_input(message)
    text = data["text"]
    intent = data["intent"]

    # 🔑 ДОБАВЛЕНО — diagram intent (перекрытие)
    if is_diagram_request(text):
        intent = "diagram"

    # 🔑 ДОБАВЛЕНО (регистрация)
    sub_register(user_id)

    # 🔑 ДОБАВЛЕНО (проверка доступа)
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

    # 🔥 РЕЖИМ ЧЕРТЕЖА (НОВЫЙ БЛОК)
    if intent == "diagram":
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

    # 🔥 РЕЖИМ ПОСЛЕ КНОПКИ "ИЗМЕНИТЬ"
    if user_id in edit_mode:
        edit_mode.pop(user_id)

        if user_id not in last_image:
            await message.answer("Нет изображения для редактирования")
            return

        await message.answer("🎨 Редактирую...")

        img = await run_with_typing(
            message.chat.id,
            edit_image(last_image[user_id], text)
        )

        sent = await message.answer_photo(
            BufferedInputFile(img, filename="edit.png")
        )

        await message.answer("Оцени 👇", reply_markup=main_keyboard(sent.message_id))

        sub_add_message(user_id)
        return

    if is_edit_request(text) and user_id in last_image:
        await message.answer("🎨 Редактирую...")

        img = await run_with_typing(
            message.chat.id,
            edit_image(last_image[user_id], text)
        )

        sent = await message.answer_photo(
            BufferedInputFile(img, filename="edit.png")
        )

        await message.answer("Оцени 👇", reply_markup=main_keyboard(sent.message_id))

        sub_add_message(user_id)
        return

    if user_id in awaiting_image_prompt:
        awaiting_image_prompt.pop(user_id)

        img = await run_with_typing(
            message.chat.id,
            generate_image(text)
        )

        sent = await message.answer_photo(
            BufferedInputFile(img, filename="image.png")
        )

        last_image[user_id] = f"{user_id}_last.png"

        await message.answer("Оцени 👇", reply_markup=main_keyboard(sent.message_id))

        sub_add_message(user_id)
        return

    # 🔑 УСИЛЕННЫЙ ТРИГГЕР
    if intent == "generate_image" or is_image_request(text):
        awaiting_image_prompt[user_id] = True
        await message.answer("Какое именно изображение тебе нужно?")
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

    sent = await message.answer(reply, reply_markup=main_keyboard(message.message_id))

    sub_add_message(user_id)

# ===== CALLBACKS =====
@dp.callback_query(F.data.startswith("like_"))
async def like(c: types.CallbackQuery):
    feedback_memory[c.data] = "like"
    await c.answer("👍")

@dp.callback_query(F.data.startswith("dislike_"))
async def dislike(c: types.CallbackQuery):
    feedback_memory[c.data] = "dislike"
    await c.answer("👎")

@dp.callback_query(F.data == "img_edit")
async def image_edit_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    edit_mode[user_id] = True
    await callback.message.answer("✏️ Как изменить изображение?")
    await callback.answer()

# 🔑 ДОБАВЛЕНО (покупка)
@dp.callback_query(F.data == "buy_yes")
async def buy_yes(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    sub_pending_payments.add(user_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")
        ]
    ])

    await bot.send_message(
        2016592532,
        f"💳 Запрос на подписку\nID: {user_id}",
        reply_markup=keyboard
    )

    await callback.message.answer("⏳ Ожидайте подтверждения")
    await callback.answer()

@dp.callback_query(F.data.startswith("approve_"))
async def approve(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])

    sub_activate(user_id)
    sub_pending_payments.discard(user_id)

    await bot.send_message(user_id, "🎉 Подписка активирована на 30 дней")
    await callback.answer("Подтверждено")

@dp.callback_query(F.data.startswith("reject_"))
async def reject(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])

    sub_pending_payments.discard(user_id)

    await bot.send_message(user_id, "❌ Оплата не подтверждена")
    await callback.answer("Отклонено")

# ===== START =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
