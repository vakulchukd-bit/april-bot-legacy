import asyncio
import os
import json
import base64
import threading
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from openai import OpenAI

# ================= CONFIG =================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

ADMINS = [2016592532]

# ================= STORAGE =================
users = {}  # {id: {sub_until, words, images, edits}}
memory = {}
likes = {}
last_reply = {}
user_lang = {}

# ================= SERVER =================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

# ================= SUB =================
def get_user(uid):
    return users.setdefault(uid, {
        "sub_until": None,
        "words": 0,
        "images": 0,
        "edits": 0
    })

def has_sub(uid):
    u = get_user(uid)
    if uid in ADMINS:
        return True
    return u["sub_until"] and datetime.now() < u["sub_until"]

def give_sub(uid, days=30):
    get_user(uid)["sub_until"] = datetime.now() + timedelta(days=days)

# ================= LANGUAGE =================
def detect_lang(text):
    if any(c in text for c in "іїє"):
        return "ua"
    if any(c in text for c in "abcdefghijklmnopqrstuvwxyz"):
        return "en"
    return "ru"

# ================= STYLE =================
def analyze(text):
    return {
        "short": len(text) < 30,
        "deep": len(text) > 120
    }

# ================= INTENT =================
def intent(text):
    t = text.lower()
    if "рецепт" in t or "приготов" in t:
        return "cook"
    if "код" in t or "python" in t:
        return "dev"
    if "игра" in t:
        return "game"
    if "задач" in t:
        return "study"
    return "normal"

# ================= PROMPT =================
def build_prompt(uid, text):
    lang = detect_lang(text)
    user_lang[uid] = lang

    style = analyze(text)
    role = intent(text)

    base = "Ты живой ассистент. Отвечай естественно.\n"

    roles = {
        "cook": "Ты повар. Давай рецепты.",
        "dev": "Ты программист. Пиши код.",
        "game": "Ты геймер.",
        "study": "Ты учитель.",
        "normal": ""
    }

    base += roles.get(role, "")

    if style["short"]:
        base += " Отвечай коротко."
    if style["deep"]:
        base += " Объясняй подробно."

    # лайки
    liked = likes.get(uid, [])
    if liked:
        base += "\nПользователю нравится стиль:\n"
        for l in liked[-2:]:
            base += f"- {l}\n"

    return base

# ================= UI =================
def kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍", callback_data="like")]
    ])

# ================= TYPING =================
async def typing(chat):
    while True:
        try:
            await bot.send_chat_action(chat, "typing")
            await asyncio.sleep(4)
        except:
            break

# ================= LIMIT =================
def check_limits(uid, text):
    if uid in ADMINS:
        return True, None

    u = get_user(uid)

    if not has_sub(uid):
        if len(text.split()) > 50:
            return False, "❌ Лимит 50 слов. Купи подписку /paid"
        if u["images"] >= 1:
            return False, "❌ Лимит генерации. /paid"
        if u["edits"] >= 1:
            return False, "❌ Лимит редактирования. /paid"

    return True, None

# ================= COMMANDS =================
@dp.message(lambda m: m.text == "/paid")
async def paid(m: types.Message):
    await m.answer("💰 Подписка 150 грн\nНапиши 'оплатил'")

@dp.message(lambda m: m.text and m.text.startswith("/give"))
async def give(m: types.Message):
    if m.from_user.id not in ADMINS:
        return
    try:
        uid = int(m.text.split()[1])
        give_sub(uid)
        await m.answer("✅ выдано")
    except:
        await m.answer("ошибка")

# ================= VOICE =================
async def voice_to_text(message):
    file = await bot.get_file(message.voice.file_id)
    path = "voice.ogg"
    await bot.download_file(file.file_path, path)

    with open(path, "rb") as f:
        t = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=f
        )
    return t.text

# ================= IMAGE =================
async def analyze_image(path):
    with open(path, "rb") as f:
        b = base64.b64encode(f.read()).decode()

    r = client.responses.create(
        model="gpt-4o",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Опиши это"},
                {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b}"}
            ]
        }]
    )
    return r.output_text

async def gen_image(prompt):
    r = client.images.generate(
        model="gpt-image-1",
        prompt=prompt
    )
    img = base64.b64decode(r.data[0].b64_json)
    return img

# ================= MAIN =================
@dp.message(lambda m: m.text or m.voice or m.photo)
async def handle(m: types.Message):
    uid = m.from_user.id
    u = get_user(uid)

    # голос
    if m.voice:
        text = await voice_to_text(m)
    else:
        text = m.text or ""

    # фото
    if m.photo:
        file = await bot.get_file(m.photo[-1].file_id)
        path = f"{uid}.jpg"
        await bot.download_file(file.file_path, path)
        result = await analyze_image(path)
        await m.answer(result)
        return

    if not text:
        return

    # генерация картинки
    if "сделай картинку" in text:
        ok, err = check_limits(uid, text)
        if not ok:
            await m.answer(err)
            return

        img = await gen_image(text)
        u["images"] += 1

        await m.answer_photo(BufferedInputFile(img, "img.png"))
        return

    # лимиты
    ok, err = check_limits(uid, text)
    if not ok:
        await m.answer(err)
        return

    # уточнение
    if len(text.split()) < 2:
        await m.answer("Уточни подробнее")
        return

    prompt = build_prompt(uid, text)

    t = asyncio.create_task(typing(m.chat.id))

    try:
        r = await asyncio.to_thread(
            lambda: client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text}
                ]
            )
        )
    finally:
        t.cancel()

    reply = r.output_text

    last_reply[uid] = reply
    memory.setdefault(uid, []).append({"q": text, "a": reply})

    await m.answer(reply, reply_markup=kb())

# ================= LIKE =================
@dp.callback_query(F.data == "like")
async def like(c: types.CallbackQuery):
    uid = c.from_user.id
    await c.answer("👍")

    txt = last_reply.get(uid)
    if txt:
        likes.setdefault(uid, []).append(txt)

    await c.message.answer("💙 сохранено")

# ================= START =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main())
