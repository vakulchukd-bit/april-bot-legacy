import asyncio
import os
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI

# ================= CONFIG =================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()
client = OpenAI(api_key=OPENAI_KEY)

# ================= STATE =================
dialog_memory = {}        # {user_id: [ {role, content}, ... ]}
last_bot_message = {}     # {user_id: "last reply text"}
last_image = {}           # {user_id: "path"}
edit_mode = {}            # {user_id: True}

SYSTEM_PROMPT = """
Ты умный ассистент.

Правила:
— Если задача ясна → сразу решай.
— Если не хватает данных → задай короткий уточняющий вопрос.
— Если пользователь говорит "не так" → признай и исправь.
— Если вопрос про предыдущий ответ → ответь по нему, не повторяй всё.
— Не давай лишнего, будь конкретным.
"""

# ================= SERVER (для Railway/Render) =================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

# ================= UI =================
def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍", callback_data="like")]
    ])

def image_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👀 Описать", callback_data="img_describe"),
            InlineKeyboardButton(text="🎨 Изменить", callback_data="img_edit")
        ]
    ])

# ================= TYPING =================
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

# ================= MEMORY HELPERS =================
def get_history(user_id, limit=6):
    return dialog_memory.get(user_id, [])[-limit:]

def push_memory(user_id, role, content):
    dialog_memory.setdefault(user_id, []).append({
        "role": role,
        "content": content
    })

# ================= THINK (ШАГ 1) =================
def think(user_id, text):
    history = get_history(user_id, 6)

    prompt = f"""
Ты анализируешь диалог и решаешь, что делать дальше.

История:
{history}

Новое сообщение:
{text}

Ответь строго JSON:

{{
"intent": "кратко что хочет пользователь",
"action": "answer | clarify | correct | followup",
"confidence": число от 0 до 100
}}
"""

    r = client.responses.create(
        model="gpt-4o-mini",
        input=prompt
    )

    try:
        return json.loads(r.output_text)
    except:
        return {"intent": text, "action": "answer", "confidence": 50}

# ================= VOICE =================
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

# ================= IMAGE =================
async def analyze_image(file_path):
    def run():
        with open(file_path, "rb") as img:
            b64 = base64.b64encode(img.read()).decode()

        r = client.responses.create(
            model="gpt-4o",
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text",
                     "text": "Скажи по-человечески что это и зачем это используется"},
                    {"type": "input_image",
                     "image_url": f"data:image/jpeg;base64,{b64}"}
                ]
            }]
        )
        return r.output_text

    return await asyncio.to_thread(run)

async def edit_image(file_path, prompt):
    def run():
        with open(file_path, "rb") as img:
            result = client.images.edit(
                model="gpt-image-1",
                image=img,
                prompt=f"Добавь максимально реалистично: {prompt}"
            )
        return base64.b64decode(result.data[0].b64_json)

    return await asyncio.to_thread(run)

# ================= MAIN HANDLER =================
@dp.message(lambda m: m.text or m.photo or m.voice)
async def handle(message: types.Message):
    user_id = message.from_user.id

    # ---------- PHOTO ----------
    if message.photo:
        file = await bot.get_file(message.photo[-1].file_id)
        path = f"image_{user_id}.jpg"
        await bot.download_file(file.file_path, destination=path)

        last_image[user_id] = path
        await message.answer("📷 Выбери действие:", reply_markup=image_keyboard())
        return

    # ---------- VOICE ----------
    if message.voice:
        text = await run_with_typing(
            message.chat.id,
            voice_to_text(message, user_id)
        )
        await message.answer(f"📝 {text}")
    else:
        text = (message.text or "").strip()

    if not text:
        return

    # ---------- EDIT MODE ----------
    if user_id in edit_mode and user_id in last_image:
        img = await run_with_typing(
            message.chat.id,
            edit_image(last_image[user_id], text)
        )
        await message.answer_photo(BufferedInputFile(img, filename="edit.png"))

        del edit_mode[user_id]
        del last_image[user_id]
        return

    # ---------- THINK ----------
    analysis = await asyncio.to_thread(think, user_id, text)

    action = analysis.get("action", "answer")
    intent = analysis.get("intent", text)
    confidence = int(analysis.get("confidence", 50))

    # ---------- DECIDE ----------
    if action == "clarify" and confidence < 60:
        await message.answer("Уточни, пожалуйста, чтобы я сделал точно как нужно")
        return

    if action == "correct":
        smart_text = f"""
Я ранее ошибся. Исправляю.

Новая задача:
{text}

Дай правильное решение.
"""
    elif action == "followup":
        prev = last_bot_message.get(user_id, "")
        smart_text = f"""
Вопрос по предыдущему ответу.

Предыдущий ответ:
{prev}

Вопрос:
{text}

Ответь кратко и по делу.
"""
    else:
        smart_text = f"""
Задача:
{intent}

Сделай максимально точно и без лишнего.
"""

    # ---------- ASK (ШАГ 2) ----------
    async def ask():
        def run():
            r = client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": smart_text}
                ]
            )
            return r.output_text
        return await asyncio.to_thread(run)

    reply = await run_with_typing(message.chat.id, ask())

    # ---------- SAVE MEMORY ----------
    push_memory(user_id, "user", text)
    push_memory(user_id, "assistant", reply)
    last_bot_message[user_id] = reply

    # ---------- PRETTY CODE OUTPUT ----------
    lower = reply.lower()
    if any(k in lower for k in ["<html", "<button", "css", "def ", "function "]):
        await message.answer(
            f"```html\n{reply}\n```",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )
    else:
        await message.answer(reply, reply_markup=main_keyboard())

# ================= CALLBACKS =================
@dp.callback_query(F.data == "like")
async def like(c: types.CallbackQuery):
    await c.answer("👍")
    await c.message.answer("💙 Сохранено")

@dp.callback_query(F.data == "img_describe")
async def img_describe(c: types.CallbackQuery):
    uid = c.from_user.id
    await c.answer()

    path = last_image.get(uid)
    if not path:
        await c.message.answer("⚠️ Нет изображения")
        return

    result = await run_with_typing(
        c.message.chat.id,
        analyze_image(path)
    )
    await c.message.answer(result)

@dp.callback_query(F.data == "img_edit")
async def img_edit(c: types.CallbackQuery):
    uid = c.from_user.id
    await c.answer()

    if uid not in last_image:
        await c.message.answer("⚠️ Сначала отправь фото")
        return

    edit_mode[uid] = True
    await c.message.answer("✏️ Что изменить?")

# ================= START =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main
