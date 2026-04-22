import asyncio
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from datetime import datetime
import pytz

from aiogram import Bot, Dispatcher, types
from aiogram.types import BufferedInputFile
from openai import OpenAI

from storage import (
    check_subscription,
    should_warn,
    can_send_message
)

# CORE
from core.executor import execute

from blocks.ui import buy_keyboard
from blocks.state_manager import (
    set_image_context,
    set_awaiting,
    add_dialog,
    get_state
)

from blocks.anchor_system import create_anchor, clear_anchor
from blocks.error_handler import handle_error

from blocks.admin_system import (
    register_user,
    log_event,
    get_admin_panel
)

from blocks.cost_system import add_image, add_text
from blocks.mode_manager import get_mode, set_mode, clear_mode
from blocks.session_manager import is_session_expired
from blocks.image_utils import compress_image

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

ADMIN_ID = 2016592532
tz = pytz.timezone("Europe/Kyiv")


# ===== FINAL CONTROL =====
def final_control(text: str) -> str:
    if not text or not text.strip():
        return "⚠️ Ответ не сгенерирован. Попробуй ещё раз."

    if len(text) > 3500:
        text = text[:3500] + "\n\n…обрезано"

    return text.strip()


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


# ===== MAIN =====
@dp.message()
async def handle(message: types.Message):
    user_id = message.from_user.id
    text = message.text or message.caption or ""

    # ===== ENGINEERING =====
    if text.lower() == "/analiz" and user_id == ADMIN_ID:
        set_mode(user_id, "engineering")
        await message.answer("🛠 Режим анализа включен")
        return

    if text.lower() == "/exit" and user_id == ADMIN_ID:
        clear_mode(user_id)
        await message.answer("❌ Режим анализа выключен")
        return

    if get_mode(user_id) == "engineering" and user_id == ADMIN_ID:
        result = await execute(user_id, text, message.chat.id, run_with_typing)
        await message.answer(result.get("data", "Ошибка"))
        return

    # ===== STATE =====
    state = get_state(user_id)
    now = datetime.now(tz)

    state["time_str"] = now.strftime("%H:%M")
    state["date_str"] = now.strftime("%d.%m.%Y")
    state["weekday"] = now.strftime("%A")

    register_user(user_id)

    # ===== SESSION =====
    if is_session_expired(user_id):
        clear_anchor(user_id)
        set_image_context(user_id, None)
        await message.answer("🧠 Сессия обновлена")

    if should_warn(user_id):
        await message.answer("⚠️ Подписка скоро закончится")

    # ===== ACCESS =====
    if user_id != ADMIN_ID and not check_subscription(user_id):
        await message.answer("💳 Оформить подписку?", reply_markup=buy_keyboard())
        return

    try:
        # ===== PHOTO =====
        if message.photo:
            file = await bot.get_file(message.photo[-1].file_id)
            path = f"{user_id}.jpg"
            await bot.download_file(file.file_path, destination=path)

            set_image_context(user_id, {
                "path": path,
                "hint": None
            })

            set_mode(user_id, "image_edit")
            create_anchor(user_id, "image", "изображение")

            await message.answer("📷 Что изменить?")
            return

        log_event(user_id, "text")
        add_text()

        result = await execute(
            user_id,
            text,
            message.chat.id,
            run_with_typing
        )

        # ===== 🔥 ЖЁСТКИЙ КОНТРОЛЬ =====
        if not result or "type" not in result:
            await message.answer("⚠️ Ошибка выполнения")
            return

        rtype = result["type"]

        # ===== IMAGE =====
        if rtype == "image":
            log_event(user_id, "image")
            add_image()

            compressed = compress_image(result["data"])

            await message.answer_photo(
                BufferedInputFile(compressed, filename="image.jpg")
            )
            return

        # ===== TEXT =====
        elif rtype == "text":
            content = result.get("data")

            if not content:
                await message.answer("⚠️ Пустой ответ")
                return

            add_dialog(user_id, "user", text)
            add_dialog(user_id, "assistant", content)

            reply = final_control(content)
            await message.answer(reply)
            return

        # ===== ❌ UNKNOWN =====
        else:
            print("❌ UNKNOWN:", result)
            await message.answer("⚠️ Ошибка выполнения")
            return

    except Exception as e:
        await handle_error(bot, message, e, "global")


# ===== START =====
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
