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
awaiting_image_prompt = {}

# ===== SYSTEM =====
SYSTEM_PROMPT = """
Ты — Aprill, интеллектуальный ассистент.

Ты:
- понимаешь контекст диалога
- отвечаешь логично
- не теряешь связь между сообщениями
- если не уверен — уточняешь
"""

IMAGE_STYLE = """
high quality, detailed, realistic, cinematic lighting,
4k, sharp focus, natural colors
"""

def enhance_prompt(user_prompt):
    return f"{IMAGE_STYLE}\n\n{user_prompt}"

# ===== HELPERS =====
def is_image_request(text):
    return any(w in text.lower() for w in ["картин", "фото", "изображен", "сгенерируй"])

def is_edit_request(text):
    return any(w in text.lower() for w in ["убери", "удали", "измени", "замени", "добавь"])

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

# ===== ДОБАВИЛИ =====
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
                    {"type": "input_image", "image_url": f"data:image/png;base64,{b64}"}
                ]
            }]
