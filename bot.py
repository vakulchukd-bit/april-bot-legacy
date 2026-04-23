import asyncio
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from datetime import datetime
import pytz

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI

from storage import (
    check_subscription,
    should_warn,
    can_send_message,
    set_subscription,
    get_remaining_messages,
    get_remaining_days,
    get_limits,
    is_expiring_soon
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

from blocks.mode_manager import get_mode, set_mode, clear_mode
from blocks.session_manager import is_session_expired
from blocks.menu_system import get_menu


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

ADMIN_ID = 2016592532
tz = pytz.timezone("Europe/Kyiv")


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


# ===== FINAL CONTROL =====
def final_control(text: str) -> str:
    if not text or not text.strip():
        return "⚠️ Ответ не сгенерирован. Попробуй ещё раз."

    if text.count("```") >= 2:
        text = text.replace("```", "").strip()

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


# ===== MAIN =====
@dp.message()
async def handle(message: types.Message):
    user_id = message.from_user.id
    text = message.text or message.caption or ""

    # ADMIN
    if text == "/admin":
        if user_id == ADMIN_ID:
            await message.answer(get_admin_panel())
        else:
            await message.answer("⛔ Ошибка доступа")
        return

    state = get_state(user_id)
    now = datetime.now(tz)

    state["time_str"] = now.strftime("%H:%M")
    state["date_str"] = now.strftime("%d.%m.%Y")

    register_user(user_id)

    # SESSION
    if is_session_expired(user_id):
        clear_anchor(user_id)
        clear_mode(user_id)
        set_image_context(user_id, None)
        await message.answer("🧠 Сессия обновлена")

    is_admin = user_id == ADMIN_ID
    is_pro = check_subscription(user_id)

    # PRO уведомления
    if is_pro:
        if should_warn(user_id):
            await message.answer("⚠️ Подписка скоро закончится")

        if is_expiring_soon(user_id):
            await message.answer(
                "⚠️ Подписка скоро закончится\n\n💳 Продлить?",
                reply_markup=buy_keyboard()
            )

    # FREE лимиты
    if not is_admin and not is_pro:
        remaining = get_remaining_messages(user_id)

        if remaining == 1:
            await message.answer(
                "⚠️ Осталось 1 сообщение\n\n💳 Без лимитов?",
                reply_markup=buy_keyboard()
            )
        elif remaining == 2:
            await message.answer("⚠️ Осталось 2 сообщения")

        if remaining == 0:
            await message.answer(
                "⛔ Лимит сообщений исчерпан\n\n💳 Оформить подписку?",
                reply_markup=buy_keyboard()
            )
            return

        can_send_message(user_id)

    try:
        # 🔥 ФИКС ТУТ
        result = await execute(
            user_id,
            text,
            message.chat.id,
            run_with_typing
        )

        add_dialog(user_id, "user", text)
        add_dialog(user_id, "assistant", result["data"])

        reply = final_control(result["data"])

        if is_admin or is_pro:
            days = get_remaining_days(user_id)
            status = f"\n\n👑 PRO: {days} дн."
        else:
            limits = get_limits(user_id)
            status = f"\n\n📊 FREE: {limits['messages_used']} / {limits['messages_limit']}"

        await message.answer(
            reply + status,
            reply_markup=main_keyboard(message.message_id)
        )

    except Exception as e:
        await handle_error(bot, message, e, "global_handler")


# ===== CALLBACK =====
@dp.callback_query()
async def handle_callbacks(callback: types.CallbackQuery):
    data = callback.data
    await callback.answer()

    if data == "menu":
        text, keyboard = get_menu(callback.from_user.id)
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
        return

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
            f"💳 Запрос на подписку\n\nПользователь: {user_id}",
            reply_markup=keyboard
        )

        await callback.message.answer("⏳ Запрос отправлен администратору")
        return

    if data.startswith("admin_confirm_"):
        user_id = int(data.split("_")[2])
        set_subscription(user_id)
        await bot.send_message(user_id, "✅ Подписка активирована 🎉")
        await callback.message.answer("✔ Подтверждено")
        return

    if data.startswith("admin_reject_"):
        user_id = int(data.split("_")[2])
        await bot.send_message(user_id, "❌ Подписка отклонена")
        await callback.message.answer("❌ Отклонено")
        return


# ===== START =====
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
