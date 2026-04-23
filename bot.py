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
    is_expiring_soon,
    get_admin_stats
)

from core.executor import execute

from blocks.ui import main_keyboard, buy_keyboard, тариф_keyboard, payments_keyboard
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


# ===== 🔥 TIME CHECK =====
def is_time_question(text: str):
    text = text.lower()

    triggers = [
        "сколько времени",
        "который час",
        "какая дата",
        "какой сегодня день",
        "текущее время",
        "сегодняшняя дата",
        "сколько время"
    ]

    return any(t in text for t in triggers)


# ===== TYPING =====
async def typing_loop(chat_id):
    try:
        elapsed = 0
        while True:
            if elapsed < 4:
                await bot.send_chat_action(chat_id, "typing")
            else:
                await bot.send_chat_action(chat_id, "upload_photo")
            await asyncio.sleep(2)
            elapsed += 2
    except:
        pass


async def run_with_typing(chat_id, coro):
    task = asyncio.create_task(typing_loop(chat_id))
    try:
        result = await coro
        await asyncio.sleep(0.1)
        return result
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

    state = get_state(user_id)

    now = datetime.now(tz)
    state["time_str"] = now.strftime("%H:%M")
    state["date_str"] = now.strftime("%d.%m.%Y")
    state["day"] = now.strftime("%A")

    state["allow_time"] = is_time_question(text)

    if message.voice:
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

        text = await asyncio.to_thread(run)

        if not text.strip():
            await message.answer("🎤 Не расслышал")
            return

        await message.answer(f"🎤 {text}")

    if text == "/admin":
        if user_id == ADMIN_ID:
            await message.answer(get_admin_panel(), reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 Анализ", callback_data="admin_stats")],
                [InlineKeyboardButton(text="💳 Оплаты", callback_data="admin_payments")],
                [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")]
            ]))
        else:
            await message.answer("⛔ Нет доступа")
        return

    register_user(user_id)

    is_admin = user_id == ADMIN_ID
    is_pro = check_subscription(user_id)

    if not is_admin and not is_pro:
        remaining = get_remaining_messages(user_id)
        if remaining == 0:
            await message.answer("⛔ Лимит исчерпан", reply_markup=buy_keyboard())
            return
        can_send_message(user_id)

    try:
        result = await execute(user_id, text, message.chat.id, run_with_typing)

        add_dialog(user_id, "user", text)
        add_dialog(user_id, "assistant", result["data"])

        reply = final_control(result["data"])

        if is_admin or is_pro:
            status = f"\n\n👑 PRO: {get_remaining_days(user_id)} дн."
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
    user_id = callback.from_user.id
    is_pro = check_subscription(user_id)

    if data.startswith("like_"):
        await callback.answer("👍 Сохранено", show_alert=False)
        return

    if data.startswith("dislike_"):
        await callback.answer("👎 Учту и улучшу", show_alert=False)
        return

    if data == "menu":
        await callback.answer()
        text, keyboard = get_menu(user_id)
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
        return

    # ✅ FIX INFO
    if data == "info":
        await callback.answer()
        text, keyboard = build_info_menu(user_id)
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
        return

    if data == "tariffs":
        await callback.answer()
        text, keyboard = build_tariffs_menu(user_id)
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
        return

    # ✅ FIX BUY LOGIC
    if data == "buy_lite":
        await callback.answer()

        if is_pro:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Да", callback_data="confirm_yes"),
                    InlineKeyboardButton(text="❌ Нет", callback_data="confirm_no")
                ]
            ])
            await callback.message.answer("⚠️ Перейти на Lite тариф?", reply_markup=keyboard)
        else:
            await callback.message.answer("💳 Отправить запрос?", reply_markup=buy_keyboard())
        return

    if data == "buy_premium":
        await callback.answer()

        if is_pro:
            return  # ничего не делаем (уже Premium)
        else:
            await callback.message.answer("💳 Отправить запрос?", reply_markup=buy_keyboard())
        return

    if data == "confirm_yes":
        await callback.answer()
        await callback.message.answer("⚡ Тариф изменён на Lite")
        return

    if data == "confirm_no":
        await callback.answer()
        await callback.message.answer("❌ Отменено")
        return

    if data == "buy_yes":
        await callback.answer()

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm_{user_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_{user_id}")
            ]
        ])

        await bot.send_message(ADMIN_ID, f"💳 Запрос от {user_id}", reply_markup=keyboard)
        await callback.message.answer("⏳ Ожидай подтверждения")
        return

    if data == "admin_stats":
        await callback.answer()
        errors = get_errors()

        if not errors:
            await callback.message.answer("✅ Ошибок нет")
            return

        text = "❌ ОШИБКИ:\n\n"
        for err in errors[-5:]:
            text += f"{err}\n\n"

        await callback.message.answer(text)
        return

    if data == "admin_payments":
        await callback.answer()
        await callback.message.answer("💳 Платежи:", reply_markup=payments_keyboard())
        return

    if data == "admin_broadcast":
        await callback.answer()
        set_mode(callback.from_user.id, "broadcast")
        await callback.message.answer("📢 Введи текст")
        return

    if data.startswith("admin_confirm_"):
        await callback.answer()
        user_id = int(data.split("_")[2])
        set_subscription(user_id)
        await bot.send_message(user_id, "✅ Подписка активирована")
        return

    if data.startswith("admin_reject_"):
        await callback.answer()
        user_id = int(data.split("_")[2])
        await bot.send_message(user_id, "❌ Отклонено")
        return


# ===== START =====
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
