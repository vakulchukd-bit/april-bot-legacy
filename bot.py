import asyncio
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile
from openai import OpenAI

from storage import check_subscription, should_warn
from blocks.router_system import decide_action
from blocks.image_system import analyze_image
from blocks.image_module import process as image_process
from blocks.text_module import process as text_process
from blocks.ui import main_keyboard, buy_keyboard
from blocks.state_manager import (
    get_state,
    set_image_context,
    get_image_context,
    add_dialog,
    set_task,
    get_task,
    clear_task
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

ADMIN_ID = 2016592532


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
    try:
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

    except:
        return ""


# ===== SAFE IMAGE CALL =====
async def safe_image(chat_id, user_id, prompt):
    try:
        result = await run_with_typing(
            chat_id,
            image_process(user_id, prompt, {})
        )

        if result["type"] == "error":
            return result

        return result

    except Exception:
        return {"type": "error", "text": "❌ Ошибка при генерации изображения"}


# ===== MAIN =====
@dp.message(lambda m: m.text or m.photo or m.voice)
async def handle(message: types.Message):
    user_id = message.from_user.id

    try:
        if should_warn(user_id):
            await message.answer("⚠️ Подписка закончится через 24 часа")

        access = True if user_id == ADMIN_ID else check_subscription(user_id)

        if not access:
            await message.answer(
                "💳 Подписка 30 дней — 150 грн\n\nОформить?",
                reply_markup=buy_keyboard()
            )
            return

        # ===== VOICE =====
        if message.voice:
            text = await voice_to_text(message, user_id)

            if not text.strip():
                await message.answer("🎤 Не расслышал, попробуй ещё раз")
                return

            await message.answer(f"🎤 {text}")
        else:
            text = message.text or ""

        # ===== PHOTO =====
        if message.photo:
            file = await bot.get_file(message.photo[-1].file_id)
            path = f"{user_id}.jpg"
            await bot.download_file(file.file_path, destination=path)

            try:
                hint = await analyze_image(path)
            except:
                hint = "изображение"

            set_image_context(user_id, {
                "type": "uploaded",
                "path": path,
                "hint": hint
            })

            set_task(user_id, {
                "type": "image_edit",
                "hint": hint,
                "steps": 0
            })

            await message.answer("📷 Изображение получено\n\n✏️ Что изменить?")
            return

        # ===== TASK =====
        task = get_task(user_id)

        if task and task["type"] == "image_edit":
            if len(text.split()) < 6:
                base = task.get("hint", "")
                new_prompt = base + ", " + text

                result = await safe_image(message.chat.id, user_id, new_prompt)

                if result["type"] == "error":
                    await message.answer(result["text"])
                    return

                task["steps"] += 1

                if task["steps"] >= 2:
                    clear_task(user_id)

                await message.answer_photo(
                    BufferedInputFile(result["data"], filename="edit.png")
                )
                return
            else:
                clear_task(user_id)

        # ===== IMAGE =====
        if any(w in text.lower() for w in [
            "сгенерируй", "создай", "нарисуй",
            "картинку", "изображение"
        ]):
            result = await safe_image(message.chat.id, user_id, text)

            if result["type"] == "error":
                await message.answer(result["text"])
                return

            set_task(user_id, {
                "type": "image_generate",
                "prompt": text
            })

            sent = await message.answer_photo(
                BufferedInputFile(result["data"], filename="image.png")
            )

            await message.answer("Оцени 👇", reply_markup=main_keyboard(sent.message_id))
            return

        # ===== GPT =====
        state = get_state(user_id)

        result = await run_with_typing(
            message.chat.id,
            text_process(user_id, text, state)
        )

        reply = result["content"]

        add_dialog(user_id, "user", text)
        add_dialog(user_id, "assistant", reply)

        clear_task(user_id)

        await message.answer(reply, reply_markup=main_keyboard(message.message_id))

    except Exception as e:
        await message.answer("⚠️ Что-то пошло не так, попробуй ещё раз")


# ===== CALLBACKS =====
@dp.callback_query(F.data.startswith("like_"))
async def like(c: types.CallbackQuery):
    await c.answer()
    await c.message.answer("👍 Спасибо!")


@dp.callback_query(F.data.startswith("dislike_"))
async def dislike(c: types.CallbackQuery):
    await c.answer()
    await c.message.answer("👎 Принял!")


# ===== START =====
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
