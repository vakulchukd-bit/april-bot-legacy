# (твои импорты без изменений)
import asyncio
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from datetime import datetime
import pytz

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from openai import OpenAI

from storage import (
    check_subscription,
    should_warn,
    can_send_message,
    set_subscription,
    get_remaining_messages,
    get_remaining_days,
    get_limits,
    get_admin_stats,
    get_user_plan,
    get_all_users,
    init_db,
    ensure_user_db,
    get_reset_seconds,
    format_time
)

from core.executor import execute

from blocks.ui import main_keyboard, buy_keyboard, тариф_keyboard, payments_keyboard, upgrade_keyboard

from blocks.state_manager import (
    set_image_context,
    set_awaiting,
    add_dialog,
    get_state
)

from blocks.anchor_system import create_anchor, clear_anchor
from blocks.error_handler import handle_error, get_errors

from blocks.admin_system import (
    register_user,
    log_event,
    get_admin_panel
)

from blocks.mode_manager import get_mode, set_mode, clear_mode
from blocks.session_manager import is_session_expired
from blocks.menu_system import get_menu, build_tariffs_menu, build_info_menu


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

ADMIN_ID = 2016592532
tz = pytz.timezone("Europe/Kyiv")


LANG_TZ_MAP = {
    "uk": "Europe/Kyiv",
    "ru": "Europe/Kyiv",
    "fr": "Europe/Paris",
    "de": "Europe/Berlin",
    "en": "Europe/London"
}


async def typing_loop(chat_id, is_image=False):
    try:
        while True:
            await bot.send_chat_action(chat_id, "typing")
            await asyncio.sleep(2)
    except:
        pass


async def run_with_typing(chat_id, coro, is_image=False):
    task = asyncio.create_task(typing_loop(chat_id, is_image))
    try:
        result = await coro
        return result
    finally:
        task.cancel()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")


def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()


@dp.message()
async def handle(message: types.Message):
    user_id = message.from_user.id
    ensure_user_db(user_id)

    text = message.text or message.caption or ""
    state = get_state(user_id)

    register_user(user_id)

    # 🔥 ВОТ ЭТО ТЫ ПОТЕРЯЛ
    mode = get_mode(user_id)
    if user_id == ADMIN_ID and mode == "broadcast":
        users = get_all_users()
        success = 0

        for uid in users:
            if int(uid) == ADMIN_ID:
                continue
            try:
                await bot.send_message(uid, f"📢 {text}")
                success += 1
            except:
                pass

        clear_mode(user_id)
        await message.answer(f"✅ Рассылка отправлена: {success}")
        return

    # обычная логика
    try:
        result = await run_with_typing(
            message.chat.id,
            execute(user_id, text, message.chat.id, run_with_typing)
        )

        if not result:
            await message.answer("⚠️ Ошибка. Попробуй ещё раз.")
            return

        if result.get("type") == "text":
            await message.answer(
                result.get("data", ""),
                reply_markup=main_keyboard(message.message_id)
            )

    except Exception as e:
        await handle_error(bot, message, e, "global_handler")


@dp.callback_query()
async def handle_callbacks(callback: types.CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id

    if data == "menu":
        text, keyboard = get_menu(user_id)
        await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        return

    if data == "admin_broadcast":
        set_mode(user_id, "broadcast")
        await callback.answer("📢 Введи текст", show_alert=True)
        return

    if data.startswith("like_"):
        await callback.answer("👍 Спасибо")
        return

    try:
        result = await execute(
            user_id,
            "",
            callback.message.chat.id,
            run_with_typing,
            callback_data=data
        )

        if result and result.get("type") == "text":
            await callback.message.answer(result.get("data", ""))

    except Exception as e:
        await handle_error(bot, callback.message, e, "callback_handler")

    await callback.answer()


async def main():
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
