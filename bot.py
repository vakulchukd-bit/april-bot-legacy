# ключевые фиксы:
# 1. показываем реальные ошибки
# 2. защита от пустых команд
# 3. не уходим в image если нет смысла

import asyncio
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile
from openai import OpenAI

from storage import check_subscription, should_warn
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


# ===== SAFE IMAGE =====
async def safe_image(chat_id, user_id, prompt):
    try:
        if not prompt or len(prompt.strip()) < 3:
            return {"type": "error", "text": "⚠️ Слишком пустой запрос"}

        result = await image_process(user_id, prompt, {})

        if result["type"] == "error":
            return result

        return result

    except Exception as e:
        return {"type": "error", "text": f"❌ Ошибка: {str(e)}"}


# ===== MAIN =====
@dp.message()
async def handle(message: types.Message):
    user_id = message.from_user.id

    try:
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
                "path": path,
                "hint": hint
            })

            set_task(user_id, {
                "type": "image_edit",
                "hint": hint
            })

            await message.answer("📷 Что изменить?")
            return

        # ===== TASK =====
        task = get_task(user_id)

        if task and task["type"] == "image_edit":
            if len(text.strip()) < 3 or text.lower() in ["ничего", "нет"]:
                await message.answer("Ок, ничего не меняем 👍")
                clear_task(user_id)
                return

            base = task.get("hint", "")
            prompt = base + ", " + text

            result = await safe_image(message.chat.id, user_id, prompt)

            if result["type"] == "error":
                await message.answer(result["text"])
                return

            await message.answer_photo(
                BufferedInputFile(result["data"], filename="edit.png")
            )
            return

        # ===== IMAGE =====
        if "картин" in text.lower() or "нарисуй" in text.lower():
            result = await safe_image(message.chat.id, user_id, text)

            if result["type"] == "error":
                await message.answer(result["text"])
                return

            await message.answer_photo(
                BufferedInputFile(result["data"], filename="image.png")
            )
            return

        # ===== GPT =====
        state = get_state(user_id)

        result = await text_process(user_id, text, state)

        reply = result["content"]

        add_dialog(user_id, "user", text)
        add_dialog(user_id, "assistant", reply)

        await message.answer(reply)

    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)}")


# ===== START =====
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
