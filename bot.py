import asyncio
import os
import base64
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ===== MEMORY =====
dialog_memory = {}
last_image = {}
edit_mode = {}
feedback_memory = {}

# ===== SYSTEM =====
SYSTEM_PROMPT = """
Ты — Aprill, интеллектуальный ассистент.

Ты:
- понимаешь пользователя
- отвечаешь как человек
- уточняешь, если не уверен
- не спешишь делать, если задача неясна
- стремишься к качеству

Если запрос неполный — сначала уточни.
"""

# ===== IMAGE STYLE =====
IMAGE_STYLE = """
psychological portrait, cinematic lighting,
ultra realistic, high detail, 4k,
dramatic shadows, depth, professional
"""

def enhance_prompt(user_prompt):
    return f"""
{IMAGE_STYLE}

{user_prompt}

high quality, masterpiece
"""

# ===== SMART CHECKS =====
def is_image_request(text: str):
    return any(w in text.lower() for w in ["картин", "фото", "изображен", "сгенерируй"])

def is_clear_image_request(text: str):
    if len(text.split()) < 3:
        return False
    return True

def is_complaint(text: str):
    bad = ["не то", "неправильно", "не понял", "почему", "ошибка", "не так"]
    return any(w in text.lower() for w in bad)

# ===== SERVER =====
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

# ===== UI =====
def main_keyboard(msg_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍", callback_data=f"like_{msg_id}"),
            InlineKeyboardButton(text="👎", callback_data=f"dislike_{msg_id}")
        ]
    ])

def image_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👀 Описать", callback_data="img_describe"),
            InlineKeyboardButton(text="🎨 Изменить", callback_data="img_edit")
        ]
    ])

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

# ===== IMAGE GENERATE =====
async def generate_image(prompt):
    def run():
        result = client.images.generate(
            model="gpt-image-1",
            prompt=enhance_prompt(prompt),
            size="1024x1024"
        )
        return base64.b64decode(result.data[0].b64_json)

    return await asyncio.to_thread(run)

# ===== IMAGE ANALYZE =====
async def analyze_image(file_path):
    def run():
        with open(file_path, "rb") as img:
            b64 = base64.b64encode(img.read()).decode()

        r = client.responses.create(
            model="gpt-4o",
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Опиши изображение"},
                    {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"}
                ]
            }]
        )
        return r.output_text

    return await asyncio.to_thread(run)

# ===== IMAGE EDIT =====
async def edit_image(file_path, prompt):
    def run():
        with open(file_path, "rb") as img:
            result = client.images.edit(
                model="gpt-image-1",
                image=img,
                prompt=enhance_prompt(prompt)
            )
        return base64.b64decode(result.data[0].b64_json)

    return await asyncio.to_thread(run)

# ===== VOICE =====
async def voice_to_text(message, user_id):
    file = await bot.get_file(message.voice.file_id)
    path = f"{user_id}.ogg"
    await bot.download_file(file.file_path, destination=path)

    def run():
        with open(path, "rb") as f:
            t = client.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                file=f
            )
        return t.text

    return await asyncio.to_thread(run)

# ===== MAIN =====
@dp.message(lambda m: m.text or m.photo or m.voice)
async def handle(message: types.Message):
    user_id = message.from_user.id

    # PHOTO
    if message.photo:
        file = await bot.get_file(message.photo[-1].file_id)
        path = f"{user_id}.jpg"
        await bot.download_file(file.file_path, destination=path)

        last_image[user_id] = path
        await message.answer("📷 Что сделать?", reply_markup=image_keyboard())
        return

    # VOICE
    if message.voice:
        text = await run_with_typing(
            message.chat.id,
            voice_to_text(message, user_id)
        )
        await message.answer(f"🎤 Ты сказал: {text}")
    else:
        text = message.text or ""

    # ===== SMART IMAGE LOGIC =====
    if is_image_request(text):

        if is_complaint(text):
            await message.answer(
                "Понял тебя. Давай сделаем правильно 🙌\n\n"
                "Опиши подробнее:\n"
                "- что именно\n"
                "- стиль (реализм / арт)\n"
                "- атмосферу"
            )
            return

        if not is_clear_image_request(text):
            await message.answer(
                "Хочу сделать точно 👇\n\n"
                "Уточни:\n"
                "- что на изображении\n"
                "- настроение\n"
                "- стиль\n\n"
                "Например: остров в океане, закат, спокойствие"
            )
            return

        await message.answer("🎨 Создаю изображение...")

        img = await run_with_typing(
            message.chat.id,
            generate_image(text)
        )

        sent = await message.answer_photo(
            BufferedInputFile(img, filename="image.png")
        )

        await message.answer("Оцени результат 👇", reply_markup=main_keyboard(sent.message_id))
        return

    # ===== EDIT MODE =====
    if user_id in edit_mode and user_id in last_image:
        img = await run_with_typing(
            message.chat.id,
            edit_image(last_image[user_id], text)
        )

        sent = await message.answer_photo(
            BufferedInputFile(img, filename="edit.png")
        )

        await message.answer("Оцени 👇", reply_markup=main_keyboard(sent.message_id))

        del edit_mode[user_id]
        del last_image[user_id]
        return

    # ===== GPT =====
    history = dialog_memory.get(user_id, [])[-6:]

    async def ask():
        def run():
            r = client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *history,
                    {"role": "user", "content": text}
                ]
            )
            return r.output_text

        return await asyncio.to_thread(run)

    reply = await run_with_typing(message.chat.id, ask())

    dialog_memory.setdefault(user_id, []).append({"role": "user", "content": text})
    dialog_memory[user_id].append({"role": "assistant", "content": reply})

    sent = await message.answer(reply, reply_markup=main_keyboard(message.message_id))

# ===== CALLBACKS =====
@dp.callback_query(F.data.startswith("like_"))
async def like(c: types.CallbackQuery):
    feedback_memory[c.data] = "like"
    await c.answer("👍")

@dp.callback_query(F.data.startswith("dislike_"))
async def dislike(c: types.CallbackQuery):
    feedback_memory[c.data] = "dislike"
    await c.answer("👎")

@dp.callback_query(F.data == "img_describe")
async def img_describe(c: types.CallbackQuery):
    uid = c.from_user.id
    await c.answer()

    result = await run_with_typing(
        c.message.chat.id,
        analyze_image(last_image[uid])
    )

    await c.message.answer(result)

@dp.callback_query(F.data == "img_edit")
async def img_edit(c: types.CallbackQuery):
    uid = c.from_user.id
    await c.answer()

    edit_mode[uid] = True
    await c.message.answer("Что изменить?")

# ===== START =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
