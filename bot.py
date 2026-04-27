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
    ensure_user_db
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

from io import BytesIO  # 🔥 ДОБАВИЛИ

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

session = AiohttpSession(timeout=120)
bot = Bot(token=TOKEN, session=session)

dp = Dispatcher()

ADMIN_ID = 2016592532
tz = pytz.timezone("Europe/Kyiv")


def is_time_question(text: str):
    text = text.lower()
    triggers = [
        "сколько времени",
        "который час",
        "какая дата",
        "какой сегодня день"
    ]
    return any(t in text for t in triggers)


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
    print("📤 TRY SEND IMAGE")

    try:
        await message.answer_photo(
            BufferedInputFile(data, filename="image.png")
        )
        print("✅ IMAGE SENT SUCCESS")

    except Exception as e:
        print("🔥 PHOTO FAILED, TRY DOCUMENT:", e)

        try:
            bio = BytesIO(data)
            bio.name = "image.png"
            await message.answer_document(bio)
            print("✅ SENT AS DOCUMENT")
        except Exception as e2:
            print("🔥 DOCUMENT FAILED:", e2)
            await message.answer("⚠️ Картинка сгенерирована, но не отправилась")


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
            f"🕒 Время: {now.strftime('%H:%M')}\n"
            f"📅 Дата: {now.strftime('%d.%m.%Y')}"
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

    is_admin = user_id == ADMIN_ID
    plan = get_user_plan(user_id)

    if not is_admin and plan == "free":
        remaining = get_remaining_messages(user_id)

        if remaining == 0:
            next_time = now + timedelta(hours=24)

            text_limit = (
                "⛔ Ваш лимит на сегодня исчерпан.\n\n"
                f"Следующий доступ:\n{next_time.strftime('%d.%m.%Y в %H:%M')}\n\n"
                "Хочешь продолжить без ожидания?\n"
                "Выбери тариф ниже 👇"
            )

            await message.answer(text_limit, reply_markup=тариф_keyboard())
            return

        can_send_message(user_id)

    try:
        result = await execute(user_id, text, message.chat.id, run_with_typing)

        add_dialog(user_id, "user", text)
        add_dialog(user_id, "assistant", result.get("data", ""))

        if result["type"] == "text":
            reply = result["data"]

            if is_admin:
                status = "\n\n⚙️ ADMIN"
            elif plan == "premium":
                status = f"\n\n👑 PREMIUM: {get_remaining_days(user_id)} дн."
            elif plan == "lite":
                status = f"\n\n⚡ LITE: {get_remaining_days(user_id)} дн."
            else:
                limits = get_limits(user_id)
                status = f"\n\n📊 FREE: {limits['messages_used']} / {limits['messages_limit']}"

            await message.answer(reply + status, reply_markup=main_keyboard(message.message_id))

        elif result["type"] == "image_task":
            await message.answer("🎨 Генерирую изображение...")

            try:
                task = asyncio.create_task(
                    image_generate(user_id, result["prompt"], state)
                )

                await asyncio.sleep(5)

                if not task.done():
                    await message.answer("⏳ Генерация занимает больше времени...")

                img = await task

                if not img:
                    await message.answer("⚠️ Не удалось создать изображение")
                    return

                if img["type"] == "image":
                    await safe_send_image(message, img["data"])

                elif img["type"] in ["error", "final_error"]:
                    await message.answer(img["data"])

                else:
                    await message.answer("⚠️ Ошибка генерации")

            except Exception as e:
                print("🔥 IMAGE TASK ERROR:", e)
                await message.answer("⚠️ Ошибка генерации изображения")

        elif result["type"] == "image":
            await message.answer("🎨 Генерирую изображение...")

            async def send_image():
                await safe_send_image(message, result["data"])

            asyncio.create_task(send_image())

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

    if data == "noop":
        await callback.answer()
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

    try:
        result = await execute(user_id, "", callback.message.chat.id, run_with_typing, callback_data=data)

        if not result:
            return

        if result["type"] == "text":
            await callback.message.answer(result["data"], reply_markup=result.get("keyboard"))

        elif result["type"] == "image":
            await callback.message.answer("🎨 Генерирую изображение...")

            async def send_image():
                await safe_send_image(callback.message, result["data"])

            asyncio.create_task(send_image())

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
