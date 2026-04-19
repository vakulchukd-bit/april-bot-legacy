import asyncio
import os
import base64
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI

from subscription_system import *

# 🔥 НОВОЕ (JSON)
from storage import check_subscription, set_subscription

# 🔑 ДОБАВЛЕНО (router)
from blocks.router_system import decide_action
# 🔥 ДОБАВЛЕНО (response mode)
from blocks.response_mode import detect_response_mode
# 🔥 ДОБАВЛЕНО (image system)
from blocks.image_system import analyze_image

# 🔥 АДМИН
ADMIN_ID = 2016592532

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ===== MEMORY =====
dialog_memory = {}
last_image = {}
edit_mode = {}
feedback_memory = {}
awaiting_image_prompt = {}
image_context = {}

# ===== SYSTEM =====
SYSTEM_PROMPT = """
Ты — Aprill, интеллектуальный ассистент.

Правила:
- понимаешь контекст диалога
- отвечаешь логично
- не теряешь связь между сообщениями
- если не уверен — уточняешь

ВАЖНО:
Если пользователь просит создать готовый текст (стих, письмо, заявление, шаблон):
- НЕ добавляй вступления
- НЕ пиши "вот текст" или "конечно"
- пиши сразу результат
"""

def enhance_prompt(user_prompt):
    return f"{user_prompt}"

# ===== HELPERS =====
def is_image_request(text):
    return any(w in text.lower() for w in ["картин", "фото", "изображен", "сгенерируй"])

def is_edit_request(text):
    return any(w in text.lower() for w in ["убери", "удали", "измени", "замени", "добавь"])

def is_diagram_request(text):
    return any(w in text.lower() for w in ["чертеж", "чертёж", "схема", "диаграмма"])

def build_diagram_prompt(text):
    return f"technical drawing, blueprint, schematic, black lines, white background\n\n{text}"

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
            InlineKeyboardButton(text="🎨 Изменить", callback_data="img_edit")
        ]
    ])

def buy_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="buy_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="buy_no")
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

# ===== IMAGE =====
async def generate_image(prompt):
    def run():
        result = client.images.generate(
            model="gpt-image-1",
            prompt=enhance_prompt(prompt),
            size="1024x1024"
        )
        return base64.b64decode(result.data[0].b64_json)
    return await asyncio.to_thread(run)

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
                model="gpt-4o-mini-transcribe",
                file=f
            )
        return t.text

    return await asyncio.to_thread(run)

# ===== MAIN =====
@dp.message(lambda m: m.text or m.photo or m.voice)
async def handle(message: types.Message):
    user_id = message.from_user.id

    sub_register(user_id)

    # 🔥 АДМИН ПРОПУСК
    if user_id == ADMIN_ID:
        access = True
    else:
        access = check_subscription(user_id)

    if not access:
        await message.answer(
            "💳 Подписка 30 дней — 150 грн\n\nОформить?",
            reply_markup=buy_keyboard()
        )
        return

    # ===== дальше без изменений =====
