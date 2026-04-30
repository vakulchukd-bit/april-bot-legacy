import asyncio
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from datetime import datetime, timedelta
import pytz

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.client.session.aiohttp import AiohttpSession

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
    save_payment
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

from blocks.image_module import process as image_generate

from io import BytesIO

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

session = AiohttpSession(timeout=300)
bot = Bot(token=TOKEN, session=session)

dp = Dispatcher()

ADMIN_ID = 2016592532

tz = pytz.timezone("Europe/Kyiv")


def is_time_question(text: str):
    text = text.lower()
    return any(t in text for t in [
        "сколько времени", "который час", "какая дата", "какой сегодня день"
    ])


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


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")


def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()


async def safe_send_image(message, data):
    try:
        await message.answer_photo(
            BufferedInputFile(data, filename="image.png"),
            reply_markup=main_keyboard(message.message_id)
        )
    except:
        bio = BytesIO(data)
        bio.name = "image.png"
        await message.answer_document(
            bio,
            reply_markup=main_keyboard(message.message_id)
        )


@dp.message()
async def handle(message: types.Message):
    user_id = message.from_user.id
    ensure_user_db(user_id)

    text = message.text or message.caption or ""

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

    if message.photo:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)

        path = f"{user_id}_image.jpg"
        await bot.download_file(file.file_path, destination=path)

        set_image_context(user_id, {
            "type": "uploaded",
            "path": path
        })

        await message.answer("📸 Изображение получено. Можешь спросить про него.")
        return

    state = get_state(user_id)

    now = datetime.now(tz)
    state["time_str"] = now.strftime("%H:%M")
    state["date_str"] = now.strftime("%d.%m.%Y")

    if is_time_question(text):
        await message.answer(
            f"🕒 {state['time_str']}\n📅 {state['date_str']}"
        )
        return

    register_user(user_id)

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

    try:
        result = await execute(user_id, text, message.chat.id, run_with_typing)

        add_dialog(user_id, "user", text)
        add_dialog(user_id, "assistant", result.get("data", ""))

        if result["type"] == "text":
            await message.answer(
                result["data"],
                reply_markup=main_keyboard(message.message_id)
            )

        elif result["type"] == "image":
            await safe_send_image(message, result["data"])

    except Exception as e:
        await handle_error(bot, message, e, "global_handler")


@dp.callback_query()
async def handle_callbacks(callback: types.CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id

    if data.startswith("like_"):
        state = get_state(user_id)
        state["last_action"] = {
            "type": "feedback",
            "intent": "like",
            "status": "positive"
        }
        await callback.answer("👍")
        return

    if data.startswith("dislike_"):
        state = get_state(user_id)
        state["last_action"] = {
            "type": "feedback",
            "intent": "dislike",
            "status": "negative"
        }
        await callback.answer("👎")
        return

    if data == "menu":
        text, keyboard = get_menu(user_id)
        await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        return

    if data == "info":
        text, keyboard = build_info_menu(user_id)
        await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        return

    if user_id == ADMIN_ID:
        if data == "admin_stats":
            errors = get_errors()
            text = "📊 Анализ\n\n"
            text += "✅ Ошибок нет" if not errors else "\n".join(errors[-5:])
            await callback.answer(text[:200], show_alert=True)
            return

        if data == "admin_payments":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 OpenAI", url="https://platform.openai.com/account/billing")],
                [InlineKeyboardButton(text="🚂 Railway", url="https://railway.app/dashboard")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu")]
            ])
            await callback.message.answer("💳 Оплаты:", reply_markup=keyboard)
            await callback.answer()
            return

        if data == "admin_broadcast":
            set_mode(user_id, "broadcast")
            await callback.answer("📢 Введи текст", show_alert=True)
            return

    if data in ["buy_lite", "lite", "go_lite"]:
        await callback.message.answer(
            "💳 Подтвердить Lite?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Да", callback_data="buy_yes_lite"),
                    InlineKeyboardButton(text="❌ Нет", callback_data="cancel")
                ]
            ])
        )
        await callback.answer()
        return

    if data == "buy_premium":
        await callback.message.answer(
            "💳 Подтвердить Premium?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Да", callback_data="buy_yes_premium"),
                    InlineKeyboardButton(text="❌ Нет", callback_data="cancel")
                ]
            ])
        )
        await callback.answer()
        return

    if data == "buy_yes_lite":
        await bot.send_message(
            ADMIN_ID,
            f"💳 ЗАПРОС LITE от {user_id}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅", callback_data=f"admin_confirm_lite_{user_id}"),
                    InlineKeyboardButton(text="❌", callback_data=f"admin_reject_lite_{user_id}")
                ]
            ])
        )
        await callback.answer("Отправлено")
        return

    if data == "buy_yes_premium":
        await bot.send_message(
            ADMIN_ID,
            f"💳 ЗАПРОС PREMIUM от {user_id}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅", callback_data=f"admin_confirm_premium_{user_id}"),
                    InlineKeyboardButton(text="❌", callback_data=f"admin_reject_premium_{user_id}")
                ]
            ])
        )
        await callback.answer("Отправлено")
        return

    if data.startswith("admin_confirm_"):
        parts = data.split("_")
        plan = parts[2]
        uid = int(parts[3])

        set_subscription(uid, plan)
        save_payment(uid, plan)

        await bot.send_message(uid, f"✅ Активирован {plan.upper()}")
        await callback.answer("OK", show_alert=True)
        return

    if data.startswith("admin_reject_"):
        uid = int(data.split("_")[3])
        await bot.send_message(uid, "❌ Отклонено")
        await callback.answer("OK", show_alert=True)
        return

    if data == "cancel":
        await callback.message.answer("❌ Отменено")
        await callback.answer()
        return

    await callback.answer()


async def main():
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
