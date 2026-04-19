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
edit_mode = {}
feedback_memory = {}
awaiting_image_prompt = {}
image_context = {}

# ===== SYSTEM =====
SYSTEM_PROMPT = """
Ты — Aprill, интеллектуальный ассистент.

Правила:
- понимаешь контекст диалога
- отвечаешь логично
- не теряешь связь между сообщениями

ВАЖНО:
- ты умеешь генерировать изображения
- ты умеешь анализировать изображения
- никогда не говори "я не могу"

Если пользователь просит текст для копирования:
- не добавляй пояснения
- возвращай только чистый текст
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

    if should_warn(user_id):
        await message.answer("⚠️ Подписка закончится через 24 часа")

    if user_id == ADMIN_ID:
        access = True
    else:
        access = check_subscription(user_id)

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

        last_image[user_id] = path

        try:
            hint = await analyze_image(path)
        except:
            hint = "Не удалось определить содержимое"

        image_context[user_id] = {
            "type": "uploaded",
            "path": path,
            "hint": hint,
            "full": None
        }

        await message.answer(f"📷 Я вижу: {hint}\n\nЧто сделать?", reply_markup=image_keyboard())
        return

    # ===== VOICE =====
    if message.voice:
        text = await run_with_typing(message.chat.id, voice_to_text(message, user_id))
        await message.answer(f"🎤 {text}")
    else:
        text = message.text or ""

    # ===== ПЕРЕХВАТ КАРТИНКИ =====
    if "что на картинке" in text.lower():
        ctx = image_context.get(user_id)

        if ctx:
            if ctx["type"] == "generated":
                await message.answer(f"На изображении: {ctx['hint']}")
                return

            if not ctx["full"]:
                try:
                    ctx["full"] = await analyze_image(ctx["path"])
                except:
                    ctx["full"] = "Не удалось проанализировать изображение"

            await message.answer(ctx["full"])
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

        sent = await message.answer_photo(
            BufferedInputFile(img, filename="image.png")
        )

        image_context[user_id] = {
            "type": "generated",
            "path": None,
            "hint": text,
            "full": text
        }

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
                    "content": f"Последнее изображение: {ctx['hint']}"
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

    # ===== COPY =====
    if mode == "copy":
        clean = reply.replace("```", "").strip()
        reply = f"```text\n{clean}\n```"

    dialog_memory.setdefault(user_id, []).append({"role": "user", "content": text})
    dialog_memory[user_id].append({"role": "assistant", "content": reply})

    await message.answer(reply, reply_markup=main_keyboard(message.message_id))

# ===== CALLBACKS =====
@dp.callback_query(F.data.startswith("like_"))
async def like(c: types.CallbackQuery):
    await c.answer()
    await c.message.answer("👍 Спасибо!")

@dp.callback_query(F.data.startswith("dislike_"))
async def dislike(c: types.CallbackQuery):
    await c.answer()
    await c.message.answer("👎 Принял!")

@dp.callback_query(F.data == "buy_yes")
async def buy_yes(c: types.CallbackQuery):
    user_id = c.from_user.id

    await bot.send_message(
        ADMIN_ID,
        f"💰 Новый запрос\n\nID: {user_id}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅", callback_data=f"approve_{user_id}"),
                InlineKeyboardButton(text="❌", callback_data=f"reject_{user_id}")
            ]
        ])
    )

    await c.answer()
    await c.message.answer("⏳ Ожидайте подтверждения")

@dp.callback_query(F.data.startswith("approve_"))
async def approve(c: types.CallbackQuery):
    user_id = int(c.data.split("_")[1])
    set_subscription(user_id)
    await bot.send_message(user_id, "✅ Подписка активирована!")
    await c.answer()

@dp.callback_query(F.data.startswith("reject_"))
async def reject(c: types.CallbackQuery):
    user_id = int(c.data.split("_")[1])
    await bot.send_message(user_id, "❌ Отказано")
    await c.answer()

@dp.callback_query(F.data == "buy_no")
async def buy_no(c: types.CallbackQuery):
    await c.answer()
    await c.message.answer("❌ Хорошо, если передумаешь — возвращайся")

# ===== START =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
