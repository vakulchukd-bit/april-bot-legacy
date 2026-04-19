import asyncio
import os
import base64
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI

from subscription_system import *
from storage import check_subscription, set_subscription
from blocks.router_system import decide_action
from blocks.response_mode import detect_response_mode
from blocks.image_system import analyze_image

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

# 🔥 АДМИН
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
- если не уверен — уточняешь

ВАЖНО:
Если пользователь просит создать готовый текст:
- пиши сразу результат
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

    # PHOTO
    if message.photo:
        file = await bot.get_file(message.photo[-1].file_id)
        path = f"{user_id}.jpg"
        await bot.download_file(file.file_path, destination=path)

        last_image[user_id] = path

        hint = await analyze_image(path)

        image_context[user_id] = {
            "path": path,
            "hint": hint,
            "full": None
        }

        await message.answer(f"📷 Я вижу: {hint}\n\nЧто сделать?", reply_markup=image_keyboard())
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

    # ROUTER
    history = dialog_memory.get(user_id, [])[-10:]
    decision = decide_action(text, history)
    action = decision["action"]

    mode = detect_response_mode(text)

    if "что на картинке" in text.lower():
        ctx = image_context.get(user_id)
        if ctx:
            if not ctx["full"]:
                ctx["full"] = await analyze_image(ctx["path"])
            await message.answer(ctx["full"])
            return

    if action == "diagram":
        prompt = "technical drawing, blueprint\n\n" + text
        img = await run_with_typing(message.chat.id, generate_image(prompt))
        sent = await message.answer_photo(BufferedInputFile(img, filename="diagram.png"))
        await message.answer("Оцени 👇", reply_markup=main_keyboard(sent.message_id))
        return

    if action == "image":
        img = await run_with_typing(message.chat.id, generate_image(text))
        sent = await message.answer_photo(BufferedInputFile(img, filename="image.png"))
        await message.answer("Оцени 👇", reply_markup=main_keyboard(sent.message_id))
        return

    if action == "clarify":
        await message.answer("Уточни, что именно ты хочешь?")
        return

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

    if mode == "copy":
        reply = f"```\n{reply.strip()}\n```"

    dialog_memory.setdefault(user_id, []).append({"role": "user", "content": text})
    dialog_memory[user_id].append({"role": "assistant", "content": reply})

    sent = await message.answer(reply, reply_markup=main_keyboard(message.message_id))

# ===== CALLBACKS =====
@dp.callback_query(F.data.startswith("like_"))
async def like(c: types.CallbackQuery):
    feedback_memory[c.data] = "like"
    await c.answer()
    await c.message.answer("👍 Спасибо!")

@dp.callback_query(F.data.startswith("dislike_"))
async def dislike(c: types.CallbackQuery):
    feedback_memory[c.data] = "dislike"
    await c.answer()
    await c.message.answer("👎 Принял!")

@dp.callback_query(F.data == "buy_yes")
async def buy_yes(c: types.CallbackQuery):
    user_id = c.from_user.id

    await bot.send_message(
        ADMIN_ID,
        f"💰 Новый запрос на подписку\n\nID: {user_id}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_{user_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")
            ]
        ])
    )

    await c.answer()
    await c.message.answer("⏳ Заявка отправлена на проверку")

@dp.callback_query(F.data.startswith("approve_"))
async def approve(c: types.CallbackQuery):
    user_id = int(c.data.split("_")[1])
    set_subscription(user_id)
    await bot.send_message(user_id, "✅ Подписка подтверждена!")
    await c.answer("Готово")

@dp.callback_query(F.data.startswith("reject_"))
async def reject(c: types.CallbackQuery):
    user_id = int(c.data.split("_")[1])
    await bot.send_message(user_id, "❌ Подписка отклонена")
    await c.answer("Отклонено")

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
