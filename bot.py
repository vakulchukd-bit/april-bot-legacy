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


def is_time_question(text: str):
    text = text.lower()
    triggers = [
        "сколько времени",
        "который час",
        "какая дата",
        "какой сегодня день"
    ]
    return any(t in text for t in triggers)


async def typing_loop(chat_id, is_image=False):
    try:
        while True:
            if is_image:
                await bot.send_chat_action(chat_id, "upload_photo")
            else:
                await bot.send_chat_action(chat_id, "typing")

            await asyncio.sleep(2)
    except:
        pass


async def run_with_typing(chat_id, coro, is_image=False):
    task = asyncio.create_task(typing_loop(chat_id, is_image))
    try:
        result = await coro
        await asyncio.sleep(0.3)
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

    try:
        lang = message.from_user.language_code or "en"
        user_tz = LANG_TZ_MAP.get(lang, "Europe/Kyiv")

        from storage import get_conn

        conn = get_conn()
        if conn:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT timezone FROM users WHERE user_id = %s", (str(user_id),))
                    user = cur.fetchone()

                    if user and not user.get("timezone"):
                        cur.execute(
                            "UPDATE users SET timezone = %s WHERE user_id = %s",
                            (user_tz, str(user_id))
                        )
    except:
        pass

    text = message.text or message.caption or ""

    state = get_state(user_id)

    now = datetime.now(tz)
    state["time_str"] = now.strftime("%H:%M")
    state["date_str"] = now.strftime("%d.%m.%Y")

    register_user(user_id)

    is_admin = user_id == ADMIN_ID
    plan = get_user_plan(user_id)

    try:
        result = await run_with_typing(
            message.chat.id,
            execute(user_id, text, message.chat.id, run_with_typing)
        )

        if not result:
            await message.answer("⚠️ Ошибка. Попробуй ещё раз.")
            return

        add_dialog(user_id, "user", text)
        add_dialog(user_id, "assistant", result.get("data", ""))

        if result.get("type") == "text":
            reply = result.get("data", "")

            if is_admin:
                status = "\n\n⚙️ ADMIN"
            elif plan == "premium":
                status = f"\n\n👑 PREMIUM: {get_remaining_days(user_id)} дн."
            elif plan == "lite":
                status = f"\n\n⚡ LITE: {get_remaining_days(user_id)} дн."
            else:
                limits = get_limits(user_id)
                status = f"\n\n📊 FREE: {limits['messages_used']} / {limits['messages_limit']}"

            await message.answer(
                reply + status,
                reply_markup=main_keyboard(message.message_id)
            )

    except Exception as e:
        await handle_error(bot, message, e, "global_handler")


@dp.callback_query()
async def handle_callbacks(callback: types.CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id

    if data.startswith("like_"):
        await callback.answer("👍 Спасибо", show_alert=False)
        return

    if data.startswith("dislike_"):
        await callback.answer("👎 Учту", show_alert=False)
        return

    try:
        result = await execute(
            user_id,
            text="",
            chat_id=callback.message.chat.id,
            run_with_typing=run_with_typing,
            callback_data=data
        )

        if not result:
            await callback.answer()
            return

        if result.get("type") == "text":
            text = result.get("data", "")
            keyboard = result.get("keyboard")

            # 🔥 ГЛАВНЫЙ ФИКС — НЕ РЕДАКТИРУЕМ, НЕ СКЛЕИВАЕМ
            await callback.message.answer(
                text,
                reply_markup=keyboard or main_keyboard(callback.message.message_id)
            )

        elif result.get("type") == "notify_user":
            await bot.send_message(result["target_user"], result["data"])

        elif result.get("type") == "admin_request":
            plan = result["plan"]

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Подтвердить",
                        callback_data=f"admin_confirm_{plan}_{user_id}"
                    ),
                    InlineKeyboardButton(
                        text="❌ Отклонить",
                        callback_data=f"admin_reject_{plan}_{user_id}"
                    )
                ]
            ])

            await bot.send_message(
                ADMIN_ID,
                f"💳 ЗАПРОС: {plan.upper()}\nID: {user_id}",
                reply_markup=keyboard
            )

            await callback.message.answer("⏳ Отправлено администратору")

    except Exception as e:
        await handle_error(bot, callback.message, e, "callback_handler")

    await callback.answer()


async def main():
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
