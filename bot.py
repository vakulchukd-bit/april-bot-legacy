import asyncio
import os
import time
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

ADMIN_ID = 2016592532

user_words = {}
paid_users = {}
user_history = {}
good_memory = {}
user_voice = {}
last_bot_message = {}
last_image = {}

SYSTEM_PROMPT = """
Ты — Aprill, умный AI-ассистент и эксперт.

Твоя задача — не просто отвечать, а вести человека к результату.

— задавай уточняющие вопросы
— объясняй по шагам
— адаптируйся под пользователя

Если код — оформляй в python блоке и делай копируемым.
"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

def save_all():
    with open("users.json","w") as f:
        json.dump(paid_users,f)
    with open("good.json","w") as f:
        json.dump(good_memory,f)

def load_all():
    global paid_users, good_memory
    try:
        with open("users.json") as f:
            paid_users = {int(k):v for k,v in json.load(f).items()}
    except:
        paid_users = {}
    try:
        with open("good.json") as f:
            good_memory = {int(k):v for k,v in json.load(f).items()}
    except:
        good_memory = {}

def is_paid(uid):
    return uid in paid_users and time.time() < paid_users[uid]

def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍", callback_data="like")],
        [InlineKeyboardButton(text="🔊 Читать", callback_data="choose_voice")]
    ])

def voice_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨", callback_data="voice_male"),
         InlineKeyboardButton(text="👩", callback_data="voice_female")]
    ])

def image_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👀 Что на картинке", callback_data="img_explain"),
         InlineKeyboardButton(text="🎨 Улучшить", callback_data="img_improve")]
    ])

def payment_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url="https://www.privat24.ua/send/j3z5r")],
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data="paid")]
    ])

async def speak_text(message, uid, text):
    voice = user_voice.get(uid,"female")
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy" if voice=="male" else "nova",
        input=text
    )
    await message.answer_audio(BufferedInputFile(speech.read(),"voice.mp3"))

async def generate_image(message, prompt):
    await message.answer("🎨 Генерирую...")
    img = client.images.generate(
        model="gpt-image-1",
        prompt=f"{prompt}, ultra realistic, 8k"
    )
    await message.answer_photo(
        BufferedInputFile(base64.b64decode(img.data[0].b64_json),"img.png"),
        reply_markup=main_keyboard()
    )
@dp.message()
async def handle(message: types.Message):
    uid = message.from_user.id

    if message.voice:
        try:
            file = await bot.get_file(message.voice.file_id)
            path = file.file_path
            fname = f"{uid}.ogg"
            await bot.download_file(path, destination=fname)

            with open(fname,"rb") as a:
                t = client.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe", file=a)
            text = t.text
            await message.answer(f"📝 {text}")
        except:
            await message.answer("❌ Ошибка голоса")
            return
    else:
        text = message.text or ""

    if message.photo:
        last_image[uid] = message.photo[-1].file_id
        await message.answer("Что сделать с картинкой?", reply_markup=image_keyboard())
        return

    if not is_paid(uid):
        user_words[uid] = user_words.get(uid,0)+len(text.split())
        if user_words[uid]>100:
            await message.answer("🚫 Лимит", reply_markup=payment_keyboard())
            return
user_history.setdefault(uid,[]).append(text)
    user_history[uid]=user_history[uid][-10:]

    msgs=[{"role":"system","content":SYSTEM_PROMPT}]
    for m in user_history[uid]:
        msgs.append({"role":"user","content":m})
    for m in good_memory.get(uid,[])[:3]:
        msgs.append({"role":"user","content":m})

    r=client.responses.create(model="gpt-4o-mini", input=msgs)
    reply=r.output_text

    last_bot_message[uid]=reply

    await message.answer(
        reply,
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data=="choose_voice")
async def choose(c):
    await c.message.answer("Выбери голос", reply_markup=voice_keyboard())

@dp.callback_query(lambda c: c.data=="voice_male")
async def male(c):
    user_voice[c.from_user.id]="male"
    await speak_text(c.message,c.from_user.id,last_bot_message.get(c.from_user.id,""))

@dp.callback_query(lambda c: c.data=="voice_female")
async def female(c):
    user_voice[c.from_user.id]="female"
    await speak_text(c.message,c.from_user.id,last_bot_message.get(c.from_user.id,""))

@dp.callback_query(lambda c: c.data=="img_explain")
async def explain(c):
    await c.message.answer("Опиши, что разобрать")

@dp.callback_query(lambda c: c.data=="img_improve")
async def improve(c):
    await c.message.answer("Опиши улучшения")

@dp.callback_query(lambda c: c.data=="like")
async def like(c):
    uid=c.from_user.id
    good_memory.setdefault(uid,[]).append(c.message.text)
    save_all()
    await c.message.answer("💙 Запомнил")

@dp.callback_query(lambda c: c.data=="paid")
async def paid(c):
    paid_users[c.from_user.id]=time.time()+30*24*3600
    save_all()
    await c.message.answer("✅ Подписка активна")

async def main():
    threading.Thread(target=run_server).start()
    load_all()
    await dp.start_polling(bot)

if __name__=="__main__":
    asyncio.run(main())
