import asyncio
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from datetime import datetime
import pytz

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile
from openai import OpenAI

from storage import (
    check_subscription,
    should_warn,
    can_send_message,
    can_generate_image,
    set_subscription
)

# 🔥 CORE
from core.executor import execute

from blocks.ui import main_keyboard, buy_keyboard
from blocks.state_manager import (
    set_image_context,
    set_awaiting,
    add_dialog,
    get_state  # 🔥 ДОБАВИЛИ
)

from blocks.anchor_system import create_anchor, clear_anchor
from blocks.error_handler import handle_error

from blocks.admin_system import (
    register_user,
    log_event,
    get_admin_panel
)

# 🔥 COST
from blocks.cost_system import add_image, add_text

# 🔥 MODE
from blocks.mode_manager import set_mode, clear_mode

# 🔥 SESSION
from blocks.session_manager import is_session_expired

# 🔥 IMAGE UTILS
from blocks.image_utils import compress_image

# 🔥 NEW (retry)
from blocks.image_module import retry_process


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

ADMIN_ID = 2016592532

tz = pytz.timezone("Europe/Kyiv")  # 🔥 добавили


# ===== SERVER =====
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")


def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()


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
@dp.message()
async def handle(message: types.Message):
    user_id = message.from_user.id

    # 🔥 ВОТ ГЛАВНЫЙ ФИКС ВРЕМЕНИ
    state = get_state(user_id)
    now = datetime.now(tz)

    state["hour"] = now.hour
    state["minute"] = now.minute
    state["time_str"] = now.strftime("%H:%M")
    state["date_str"] = now.strftime("%d.%m.%Y")
    state["weekday"] = now.strftime("%A")

    register_user(user_id)

    # 🔥 ADMIN
    if message.text == "/admin":
        if user_id == ADMIN_ID:
            await message.answer(get_admin_panel())
        else:
            await message.answer("⛔ Ошибка доступа")
        return

    # 🔥 SESSION
    if is_session_expired(user_id):
        clear_anchor(user_id)
        clear_mode(user_id)
        set_image_context(user_id, None)
        await message.answer("🧠 Сессия обновлена. Начнём заново 🙂")

    if should_warn(user_id):
        await message.answer("⚠️ Подписка закончится через 24 часа")

    # 🔥 ДОСТУП
    access = True if user_id == ADMIN_ID else check_subscription(user_id)

    if not access:
        await message.answer(
            "💳 Подписка 30 дней — 150 грн\n\nОформить?",
            reply_markup=buy_keyboard()
        )
        return

    try:
        # ===== PHOTO =====
        if message.photo:
            file = await bot.get_file(message.photo[-1].file_id)
            path = f"{user_id}.jpg"
            await bot.download_file(file.file_path, destination=path)

            set_image_context(user_id, {
                "type": "uploaded",
                "path": path,
                "hint": None,
                "full": None
            })

            set_awaiting(user_id, True)
            set_mode(user_id, "image_edit")

            create_anchor(user_id, "image", "изображение")

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

        log_event(user_id, "text")
        add_text()

        # ===== LIMIT =====
        if user_id != ADMIN_ID:
            if not check_subscription(user_id):
                if not can_send_message(user_id):
                    await message.answer("⛔ Лимит сообщений исчерпан")
                    return

        # ===== CORE =====
        result = await execute(
            user_id,
            text,
            message.chat.id,
            run_with_typing
        )

        # ===== OUTPUT =====
        if result["type"] == "image":
            log_event(user_id, "image")
            add_image()

            compressed = compress_image(result["data"])

            await message.answer_photo(
                BufferedInputFile(compressed, filename="image.jpg")
            )

        else:
            add_dialog(user_id, "user", text)
            add_dialog(user_id, "assistant", result["data"])

            await message.answer(result["data"])

    except Exception as e:
        await handle_error(bot, message, e, "global_handler")


# ===== START =====
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
