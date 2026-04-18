# ==================== 🔴 BLOCK 1: INIT ====================  
import asyncio  
import os  
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
  
good_memory = {}  
last_bot_message = {}  
last_image = {}  
edit_mode = {}  
  
SYSTEM_PROMPT = """  
Ты — живой ассистент Ayprill.  
  
Отвечай просто и по-человечески.  
Без фраз типа "на изображении изображено".  
  
Если фото:  
— скажи что это  
— объясни зачем это  
"""  
  
# ==================== 🔴 BLOCK 2: SERVER ====================  
class Handler(BaseHTTPRequestHandler):  
    def do_GET(self):  
        self.send_response(200)  
        self.end_headers()  
        self.wfile.write(b"OK")  
  
def run_server():  
    port = int(os.environ.get("PORT", 10000))  
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()  
  
# ==================== 🔴 BLOCK 3: STORAGE ====================  
def save_memory():  
    with open("memory.json", "w") as f:  
        json.dump(good_memory, f)  
  
# ==================== 🔴 BLOCK 4: UI ====================  
def main_keyboard():  
    return InlineKeyboardMarkup(inline_keyboard=[  
        [  
            InlineKeyboardButton(text="👍", callback_data="like"),  
            InlineKeyboardButton(text="🔊 Озвучить", callback_data="voice")  
        ]  
    ])  
  
def image_keyboard():  
    return InlineKeyboardMarkup(inline_keyboard=[  
        [  
            InlineKeyboardButton(text="👀 Описать", callback_data="img_describe"),  
            InlineKeyboardButton(text="🎨 Изменить", callback_data="img_edit")  
        ]  
    ])  
  
# ==================== 🔴 BLOCK 5: UX ====================  
async def send_action(chat_id, action):  
    while True:  
        try:  
            await bot.send_chat_action(chat_id, action)  
            await asyncio.sleep(4)  
        except:  
            break  
  
async def run_with_action(chat_id, action, coro):  
    task = asyncio.create_task(send_action(chat_id, action))  
    try:  
        return await coro  
    finally:  
        task.cancel()  
  
# ==================== 🔴 BLOCK 6: VOICE ====================  
async def transcribe_voice(message, user_id):  
    file = await bot.get_file(message.voice.file_id)  
    fname = f"{user_id}.ogg"  
    await bot.download_file(file.file_path, destination=fname)  
  
    with open(fname, "rb") as a:  
        t = client.audio.transcriptions.create(  
            model="gpt-4o-mini-transcribe",  
            file=a  
        )  
  
    return t.text.lower()  
  
# ==================== 🔴 BLOCK 7: IMAGE ANALYSIS ====================  
async def analyze_image(file_path):  
    with open(file_path, "rb") as img:  
        image_bytes = img.read()  
  
    base64_image = base64.b64encode(image_bytes).decode("utf-8")  
  
    response = client.responses.create(  
        model="gpt-4o",  
        input=[{  
            "role": "user",  
            "content": [  
                {"type": "input_text", "text": "Определи что это и объясни смысл"},  
                {  
                    "type": "input_image",  
                    "image_url": f"data:image/jpeg;base64,{base64_image}"  
                }  
            ]  
        }]  
    )  
  
    return response.output_text  
  
# ==================== 🔴 BLOCK 8: IMAGE EDIT ====================  
async def edit_image(message, file_path, user_text):  
    with open(file_path, "rb") as img:  
        result = client.images.edit(  
            model="gpt-image-1",  
            image=img,  
            prompt=user_text  
        )  
  
    image_bytes = base64.b64decode(result.data[0].b64_json)  
    photo = BufferedInputFile(image_bytes, filename="edit.png")  
  
    await message.answer_photo(photo)  
  
# ==================== 🔴 BLOCK 9: MAIN HANDLER ====================  
@dp.message()  
async def handle(message: types.Message):  
    try:  
        user_id = message.from_user.id  
  
        # ---------- PHOTO ----------  
        if message.photo:  
            file = await bot.get_file(message.photo[-1].file_id)  
            file_path = f"image_{user_id}.jpg"  
            await bot.download_file(file.file_path, destination=file_path)  
  
            last_image[user_id] = file_path  
            await message.answer("📷 Выбери действие:", reply_markup=image_keyboard())  
            return  
  
        # ---------- TEXT / VOICE ----------  
        if message.voice:  
            text = await transcribe_voice(message, user_id)  
        else:  
            text = (message.text or "").lower()  
  
        # ---------- EDIT MODE ----------  
        if user_id in edit_mode and user_id in last_image:  
            await message.answer("🎨 Делаю...")  
            await asyncio.sleep(1)  
  
            await run_with_action(  
                message.chat.id,  
                "upload_photo",  
                edit_image(message, last_image[user_id], text)  
            )  
  
            del edit_mode[user_id]  
            del last_image[user_id]  
            return  
  
        # ---------- NORMAL TEXT ----------  
        await bot.send_chat_action(message.chat.id, "typing")  
  
        response = await asyncio.to_thread(  
            lambda: client.responses.create(  
                model="gpt-4o-mini",  
                input=[  
                    {"role": "system", "content": SYSTEM_PROMPT},  
                    {"role": "user", "content": text}  
                ]  
            )  
        )  
  
        reply = response.output_text  
        last_bot_message[user_id] = reply  
  
        await message.answer(reply, reply_markup=main_keyboard())  
  
    except Exception as e:  
        await message.answer(f"⚠️ Ошибка: {e}")  
  
# ==================== 🔴 BLOCK 10: CALLBACKS ====================  
@dp.callback_query(lambda c: c.data == "img_describe")  
async def img_describe(c):  
    user_id = c.from_user.id  
    await c.answer()  
    await c.message.edit_reply_markup(None)  
  
    await c.message.answer("🔍 Анализирую...")  
    await asyncio.sleep(1)  
  
    result = await run_with_action(  
        c.message.chat.id,  
        "typing",  
        analyze_image(last_image[user_id])  
    )  
  
    await c.message.answer(result)  
    del last_image[user_id]  
  
@dp.callback_query(lambda c: c.data == "img_edit")  
async def img_edit(c):  
    user_id = c.from_user.id  
    await c.answer()  
    await c.message.edit_reply_markup(None)  
  
    edit_mode[user_id] = True  
    await c.message.answer("✏️ Скажи или напиши, что изменить:")  
  
@dp.callback_query(lambda c: c.data == "voice")  
async def voice(c):  
    await c.answer()  
  
# ==================== 🔴 BLOCK 11: START ====================  
async def main():  
    await dp.start_polling(bot)  
  
if __name__ == "__main__":  
    threading.Thread(target=run_server, daemon=True).start()  
    asyncio.run(main())
