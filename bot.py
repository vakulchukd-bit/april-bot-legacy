import asyncio
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from datetime import datetime
import pytz

from aiogram import Bot, Dispatcher, types
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI

from storage import (
    check_subscription,
    should_warn,
    can_send_message,
    can_generate_image,
    set_subscription
)

from core.executor import execute

from blocks.ui import main_keyboard, buy_keyboard
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
from blocks.image_module import retry_process

# 🔥 МЕНЮ
from blocks.menu_system import get_menu


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

ADMIN_ID = 2016592532

tz = pytz.timezone("Europe/Kyiv")


def final_control(text: str) -> str:
    if not text or not text.strip():
        return "⚠️ Ответ не сгенерирован. Попробуй ещё раз."
    if len(text) > 3500:
        text = text[:3500] + "\n\n…обрезано"
    return text.strip()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")


def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()


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


@dp.message()
async def handle(message: types.Message):
    user_id = message.from_user.id
    text = message.text or message.caption or ""

    state = get_state(user_id)
    now = datetime.now(tz)

    state["hour"] = now.hour
    register_user(user_id)

    access = True if user_id == ADMIN_ID else check_subscription(user_id)

    if not access:
        await message.answer(
            "💳 Подписка 30 дней — 150 грн\n\nОформить?",
            reply_markup=buy_keyboard()
        )
        return

    result = await execute(user_id, text, message.chat.id, run_with_typing)

    if result["type"] == "image":
        compressed = compress_image(result["data"])
        await message.answer_photo(
            BufferedInputFile(compressed, filename="image.jpg")
        )
    else:
        await message.answer(result["data"])


# ===== CALLBACK =====
@dp.callback_query()
async def handle_callbacks(callback: types.CallbackQuery):
    data = callback.data
    await callback.answer()

    # ===== МЕНЮ =====
    if data == "menu":
        text, keyboard = get_menu(callback.from_user.id)
        await callback.message.answer(text, reply_markup=keyboard)
        return

    # ===== ПОДПИСКА → АДМИН =====
    if data == "buy_yes":
        user_id = callback.from_user.id

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm_{user_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_{user_id}")
            ]
        ])

        await bot.send_message(
            ADMIN_ID,
            f"💳 Запрос на подписку\nПользователь: {user_id}",
            reply_markup=keyboard
        )

        await callback.message.answer("⏳ Запрос отправлен администратору")
        return

    if data.startswith("admin_confirm_"):
        user_id = int(data.split("_")[2])
        set_subscription(user_id)

        await bot.send_message(user_id, "✅ Подписка активирована")
        await callback.message.answer("✔ Подтверждено")
        return

    if data.startswith("admin_reject_"):
        user_id = int(data.split("_")[2])

        await bot.send_message(user_id, "❌ Подписка отклонена")
        await callback.message.answer("❌ Отклонено")
        return


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
