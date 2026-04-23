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


# ===== TIME CHECK =====
def is_time_question(text: str):
    text = text.lower()

    triggers = [
        "сколько времени",
        "который час",
        "какая дата",
        "какой сегодня день"
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

    # ===== VOICE =====
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

    state = get_state(user_id)

    now = datetime.now(tz)
    state["time_str"] = now.strftime("%H:%M")
    state["date_str"] = now.strftime("%d.%m.%Y")

    state["allow_time"] = is_time_question(text)

    # ===== TIME =====
    if state.get("allow_time"):
        await message.answer(
            f"🕒 Время: {now.strftime('%H:%M')}\n"
            f"📅 Дата: {now.strftime('%d.%m.%Y')}"
        )
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

    await callback.answer()

    # ===== LIKE =====
    if data.startswith("like_"):
        await callback.answer("👍 Сохранено", show_alert=False)
        return

    if data.startswith("dislike_"):
        await callback.answer("👎 Учту", show_alert=False)
        return

    # ===== MENU =====
    if data == "menu":
        text, keyboard = get_menu(user_id)
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
        return

    # ===== INFO =====
    if data == "info":
        text, keyboard = build_info_menu(user_id)
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
        return

    # ===== BUY =====
    if data == "buy_lite":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="buy_yes_lite"),
                InlineKeyboardButton(text="❌ Нет", callback_data="buy_no")
            ]
        ])
        await callback.message.answer("💳 Подтвердить переход на Lite?", reply_markup=keyboard)
        return

    if data == "buy_premium":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="buy_yes_premium"),
                InlineKeyboardButton(text="❌ Нет", callback_data="buy_no")
            ]
        ])
        await callback.message.answer("💳 Подтвердить переход на Premium?", reply_markup=keyboard)
        return

    # ===== SEND TO ADMIN =====
    if data == "buy_yes_lite":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm_lite_{user_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_lite_{user_id}")
            ]
        ])

        await bot.send_message(ADMIN_ID, f"💳 ЗАПРОС: LITE\nID: {user_id}", reply_markup=keyboard)
        await callback.message.answer("⏳ Отправлено администратору")
        return

    if data == "buy_yes_premium":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm_premium_{user_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_premium_{user_id}")
            ]
        ])

        await bot.send_message(ADMIN_ID, f"💳 ЗАПРОС: PREMIUM\nID: {user_id}", reply_markup=keyboard)
        await callback.message.answer("⏳ Отправлено администратору")
        return

    # ===== ADMIN CONFIRM =====
    if data.startswith("admin_confirm_"):
        parts = data.split("_")
        plan = parts[2]
        uid = int(parts[3])

        if plan == "premium":
            set_subscription(uid, 30)
        elif plan == "lite":
            set_subscription(uid, 15)

        await bot.send_message(uid, f"✅ Активирован {plan.upper()}")
        return

    # ===== ADMIN REJECT =====
    if data.startswith("admin_reject_"):
        parts = data.split("_")
        uid = int(parts[3])

        await bot.send_message(uid, "❌ Запрос отклонён")
        return


# ===== START =====
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
