import asyncio
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile
from openai import OpenAI

from storage import check_subscription, should_warn, can_send_message, can_generate_image
from blocks.router_system import decide_action
from blocks.response_mode import detect_response_mode
from blocks.image_system import analyze_image
from blocks.image_module import process as image_process
from blocks.text_module import process as text_process
from blocks.ui import main_keyboard, buy_keyboard
from blocks.state_manager import (
    get_state,
    set_image_context,
    get_image_context,
    set_awaiting,
    get_awaiting,
    set_last_prompt,
    get_last_prompt,
    add_dialog
)

# 🔥 ANCHOR
from blocks.anchor_system import (
    get_anchor,
    create_anchor,
    update_anchor,
    clear_anchor
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


# ===== MAIN =====
@dp.message()
async def handle(message: types.Message):
    user_id = message.from_user.id

    if should_warn(user_id):
        await message.answer("⚠️ Подписка закончится через 24 часа")

    access = True if user_id == ADMIN_ID else check_subscription(user_id)

    if not access:
        await message.answer(
            "💳 Подписка 30 дней — 150 грн\n\nОформить?",
            reply_markup=buy_keyboard()
        )
        return

    # ===== PHOTO =====
    if message.photo:
        file = await bot.get_file(message.photo[-1].file_id)
        path = f"{user_id}.jpg"
        await bot.download_file(file.file_path, destination=path)

        set_image_context(user_id, {
            "type": "uploaded",
            "path": path,
            "hint": None,
            "full": None
        })

        set_awaiting(user_id, True)

        # 🔥 создаём якорь (пока без hint, позже обновим)
        create_anchor(user_id, "image", "изображение")

        await message.answer("📷 Изображение получено\n\n✏️ Что хочешь с ним сделать?")
        return

    # ===== VOICE =====
    if message.voice:
        text = await run_with_typing(
            message.chat.id,
            voice_to_text(message, user_id)
        )

        if not text or text.strip() == "":
            await message.answer("🎤 Не расслышал, попробуй ещё раз")
            return

        await message.answer(f"🎤 {text}")
    else:
        text = message.text or ""

    # ===== РЕДАКТИРОВАНИЕ =====
    if get_awaiting(user_id):
        set_awaiting(user_id, False)

        ctx = get_image_context(user_id)
        if not ctx:
            await message.answer("❌ Нет изображения")
            return

        if not ctx["hint"]:
            try:
                ctx["hint"] = await analyze_image(ctx["path"])
            except:
                ctx["hint"] = "изображение"

        # 🔥 якорь
        anchor = get_anchor(user_id)
        if anchor:
            base = anchor["current"]
        else:
            base = get_last_prompt(user_id) or ctx["hint"]

        new_prompt = base + ", IMPORTANT: " + text

        result = await run_with_typing(
            message.chat.id,
            image_process(user_id, new_prompt, {})
        )

        set_last_prompt(user_id, new_prompt)

        # 🔥 обновляем якорь
        update_anchor(user_id, new_prompt)

        await message.answer_photo(
            BufferedInputFile(result["data"], filename="edited.png")
        )
        return

    # ===== ROUTER =====
    state = get_state(user_id)

    decision = decide_action(text, state["dialog"])
    action = decision["action"]

    mode = detect_response_mode(text)

    if user_id != ADMIN_ID:
        if not check_subscription(user_id):
            if not can_send_message(user_id):
                await message.answer("⛔ Лимит сообщений исчерпан")
                return

    # ===== IMAGE =====
    if action == "image":
        if user_id != ADMIN_ID:
            if not check_subscription(user_id):
                if not can_generate_image(user_id):
                    await message.answer("⛔ Лимит картинок исчерпан")
                    return

        result = await run_with_typing(
            message.chat.id,
            image_process(user_id, text, state)
        )

        set_image_context(user_id, {
            "type": "generated",
            "path": None,
            "hint": text,
            "full": text
        })

        set_last_prompt(user_id, text)

        # 🔥 якорь
        create_anchor(user_id, "image", text)

        sent = await message.answer_photo(
            BufferedInputFile(result["data"], filename="image.png")
        )

        await message.answer("Оцени 👇", reply_markup=main_keyboard(sent.message_id))
        return

    # ===== GPT =====
    anchor = get_anchor(user_id)
    if anchor:
        text = f"Контекст: {anchor['current']}\n\n{text}"

    result = await run_with_typing(
        message.chat.id,
        text_process(user_id, text, state)
    )

    reply = result["content"]

    if mode == "copy":
        clean = reply.replace("```", "").strip()
        reply = f"```text\n{clean}\n```"

    add_dialog(user_id, "user", text)
    add_dialog(user_id, "assistant", reply)

    await message.answer(reply, reply_markup=main_keyboard(message.message_id))


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
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
