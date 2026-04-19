import asyncio
import os
import base64
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI

from subscription_system import *
from storage import check_subscription, set_subscription, should_warn, can_send_message, can_generate_image
from blocks.router_system import decide_action
from blocks.response_mode import detect_response_mode
from blocks.image_system import analyze_image

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

ADMIN_ID = 2016592532

# ===== MEMORY =====
dialog_memory = {}
last_image = {}
last_prompt = {}
awaiting_image_prompt = {}
image_context = {}

# ===== SYSTEM =====
SYSTEM_PROMPT = """
Ты — Aprill, интеллектуальный ассистент.

Ты:
- понимаешь диалог
- помнишь контекст
- работаешь с изображениями

ВАЖНО:
- ты МОЖЕШЬ генерировать изображения
- ты МОЖЕШЬ анализировать изображения
- никогда не говори "я не могу"

Если пользователь говорит про картинку:
- учитывай последнюю картинку из контекста

Если пользователь просит текст для копирования:
- возвращай только текст
"""

def enhance_prompt(user_prompt):
    return user_prompt

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

# ===== MAIN =====
@dp.message(lambda m: m.text or m.photo or m.voice)
async def handle(message: types.Message):
    user_id = message.from_user.id

    sub_register(user_id)

    if should_warn(user_id):
        await message.answer("⚠️ Подписка закончится через 24 часа")

    access = True if user_id == ADMIN_ID else check_subscription(user_id)

    if not access:
        await message.answer(
            "💳 Подписка 30 дней — 150 грн\n\nОформить?",
            reply_markup=buy_keyboard()
        )
        return

    # ===== PHOTO =====
    if message.photo:
        file = await bot.get_file(message.photo[-1].file_id)
        path = f"{user_id}.jpg"
        await bot.download_file(file.file_path, destination=path)

        hint = await analyze_image(path)

        image_context[user_id] = {
            "type": "uploaded",
            "path": path,
            "hint": hint,
            "full": None
        }

        last_prompt[user_id] = hint

        await message.answer(f"📷 Я вижу: {hint}\n\nЧто сделать?", reply_markup=image_keyboard())
        return

    text = message.text or ""

    # ===== РЕДАКТИРОВАНИЕ =====
    if awaiting_image_prompt.get(user_id):
        awaiting_image_prompt[user_id] = False

        ctx = image_context.get(user_id)
        if not ctx:
            await message.answer("❌ Нет изображения")
            return

        base = last_prompt.get(user_id, ctx["hint"])
        new_prompt = base + ", " + text

        img = await run_with_typing(message.chat.id, generate_image(new_prompt))

        last_prompt[user_id] = new_prompt

        await message.answer_photo(
            BufferedInputFile(img, filename="edited.png"),
            reply_markup=image_keyboard()
        )
        return

    # ===== ПЕРЕХВАТ ОПИСАНИЯ =====
    if any(w in text.lower() for w in [
        "что на картинке", "что здесь", "опиши", "что изображено"
    ]):
        ctx = image_context.get(user_id)
        if ctx:
            await message.answer(ctx["hint"])
            return

    # ===== ROUTER =====
    decision = decide_action(text, dialog_memory.get(user_id, []))
    action = decision["action"]

    mode = detect_response_mode(text)

    if not check_subscription(user_id):
        if not can_send_message(user_id):
            await message.answer("⛔ Лимит сообщений исчерпан")
            return

    # ===== IMAGE =====
    if action == "image":
        if not check_subscription(user_id):
            if not can_generate_image(user_id):
                await message.answer("⛔ Лимит картинок исчерпан")
                return

        img = await run_with_typing(message.chat.id, generate_image(text))

        image_context[user_id] = {
            "type": "generated",
            "path": None,
            "hint": text,
            "full": text
        }

        last_prompt[user_id] = text

        sent = await message.answer_photo(
            BufferedInputFile(img, filename="image.png")
        )

        await message.answer("Оцени 👇", reply_markup=main_keyboard(sent.message_id))
        return

    # ===== GPT =====
    async def ask():
        def run():
            ctx = image_context.get(user_id)

            extra = []
            if ctx:
                extra.append({
                    "role": "system",
                    "content": f"Контекст изображения: {ctx['hint']}"
                })

            r = client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *extra,
                    *dialog_memory.get(user_id, [])[-6:],
                    {"role": "user", "content": text}
                ]
            )
            return r.output_text

        return await asyncio.to_thread(run)

    reply = await run_with_typing(message.chat.id, ask())

    if mode == "copy":
        clean = reply.replace("```", "").strip()
        reply = f"```text\n{clean}\n```"

    dialog_memory.setdefault(user_id, []).append({"role": "user", "content": text})
    dialog_memory[user_id].append({"role": "assistant", "content": reply})

    await message.answer(reply, reply_markup=main_keyboard(message.message_id))

# ===== CALLBACK =====
@dp.callback_query(F.data == "img_edit")
async def edit_image(c: types.CallbackQuery):
    user_id = c.from_user.id
    awaiting_image_prompt[user_id] = True
    await c.answer()
    await c.message.answer("✏️ Напиши, что изменить")

# ===== START =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
