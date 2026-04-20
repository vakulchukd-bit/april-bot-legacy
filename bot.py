import asyncio
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI

from storage import check_subscription, set_subscription, should_warn, can_send_message, can_generate_image
from blocks.router_system import decide_action
from blocks.response_mode import detect_response_mode
from blocks.image_system import analyze_image
from blocks.image_module import process as image_process
from blocks.text_module import process as text_process

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

ADMIN_ID = 2016592532

# ===== MEMORY =====
dialog_memory = {}
last_prompt = {}
awaiting_image_prompt = {}
image_context = {}

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

        image_context[user_id] = {
            "type": "uploaded",
            "path": path,
            "hint": None,
            "full": None
        }

        awaiting_image_prompt[user_id] = True

        await message.answer("📷 Изображение получено\n\n✏️ Что хочешь с ним сделать?")
        return

    # ===== VOICE =====
    if message.voice:
        text = await run_with_typing(
            message.chat.id,
            voice_to_text(message, user_id)
        )

        if not text or text.strip() == "":
            await message.answer("🎤 Не расслышал, попробуй ещё раз")
            return

        await message.answer(f"🎤 {text}")
    else:
        text = message.text or ""

    # ===== РЕДАКТИРОВАНИЕ =====
    if awaiting_image_prompt.get(user_id):
        awaiting_image_prompt[user_id] = False

        ctx = image_context.get(user_id)
        if not ctx:
            await message.answer("❌ Нет изображения")
            return

        if not ctx["hint"]:
            try:
                ctx["hint"] = await analyze_image(ctx["path"])
            except:
                ctx["hint"] = "изображение"

        base = last_prompt.get(user_id, ctx["hint"])
        new_prompt = base + ", IMPORTANT: " + text

        result = await run_with_typing(
            message.chat.id,
            image_process(user_id, new_prompt, {})
        )

        last_prompt[user_id] = new_prompt

        await message.answer_photo(
            BufferedInputFile(result["data"], filename="edited.png")
        )
        return

    # ===== ПЕРЕХВАТ ОПИСАНИЯ =====
    if any(w in text.lower() for w in [
        "что на картинке", "что здесь", "опиши", "что изображено"
    ]):
        ctx = image_context.get(user_id)
        if ctx:
            if not ctx["hint"]:
                try:
                    ctx["hint"] = await analyze_image(ctx["path"])
                except:
                    ctx["hint"] = "Не удалось определить"
            await message.answer(ctx["hint"])
            return

    # ===== ПРЯМОЙ ТРИГГЕР ГЕНЕРАЦИИ =====
    if any(w in text.lower() for w in [
        "сгенерируй", "создай", "нарисуй",
        "картинку", "изображение",
        "можешь сгенерировать",
        "сделай картинку",
        "хочу картинку",
        "дай картинку",
        "generate image", "create image",
        "draw", "make a picture"
    ]):
        result = await run_with_typing(
            message.chat.id,
            image_process(user_id, text, {})
        )

        image_context[user_id] = {
            "type": "generated",
            "path": None,
            "hint": text,
            "full": text
        }

        last_prompt[user_id] = text

        sent = await message.answer_photo(
            BufferedInputFile(result["data"], filename="image.png")
        )

        await message.answer("Оцени 👇", reply_markup=main_keyboard(sent.message_id))
        return

    # ===== ROUTER =====
    decision = decide_action(text, dialog_memory.get(user_id, []))
    action = decision["action"]

    mode = detect_response_mode(text)

    if user_id != ADMIN_ID:
        if not check_subscription(user_id):
            if not can_send_message(user_id):
                await message.answer("⛔ Лимит сообщений исчерпан")
                return

    # ===== IMAGE =====
    if action == "image":
        if user_id != ADMIN_ID:
            if not check_subscription(user_id):
                if not can_generate_image(user_id):
                    await message.answer("⛔ Лимит картинок исчерпан")
                    return

        result = await run_with_typing(
            message.chat.id,
            image_process(user_id, text, {})
        )

        image_context[user_id] = {
            "type": "generated",
            "path": None,
            "hint": text,
            "full": text
        }

        last_prompt[user_id] = text

        sent = await message.answer_photo(
            BufferedInputFile(result["data"], filename="image.png")
        )

        await message.answer("Оцени 👇", reply_markup=main_keyboard(sent.message_id))
        return

    # ===== GPT (через модуль) =====
    state = {
        "dialog": dialog_memory.get(user_id, []),
        "image_context": image_context.get(user_id)
    }

    result = await run_with_typing(
        message.chat.id,
        text_process(user_id, text, state)
    )

    reply = result["content"]

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


# ===== START =====
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
