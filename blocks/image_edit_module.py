# blocks/image_edit_module.py

import base64
import asyncio
import random
from openai import OpenAI

from storage import get_user_plan, get_limits, get_conn, today
from blocks.ai_config import IMAGE_MODEL, IMAGE_SIZE, IMAGE_QUALITY  # 👈 ДОБАВЛЕНО

client = OpenAI()


# 🔥 ЖИВЫЕ СООБЩЕНИЯ
def get_limit_message():
    messages = [
        "Сегодня ты уже выжал максимум из редактирования 😌",
        "Я бы продолжил менять изображение, но сегодня уже предел 👀",
        "На сегодня с изображениями всё, завтра продолжим 😉",
        "Похоже, лимит на сегодня закончился. Но мы ещё можем пообщаться 🙂",
        "Сегодня лимит закончился, но я всё ещё здесь, если нужно что-то другое 👍"
    ]
    return random.choice(messages)


async def edit_image(image_path, prompt):
    def run():
        with open(image_path, "rb") as f:
            result = client.images.edit(
                model=IMAGE_MODEL,        # 👈 через config
                image=f,
                prompt=prompt,
                size=IMAGE_SIZE,          # 👈 через config
                quality=IMAGE_QUALITY     # 👈 через config
            )

        if not result or not result.data:
            return None

        try:
            return base64.b64decode(result.data[0].b64_json)
        except Exception:
            return None

    return await asyncio.to_thread(run)


def increment_images(user_id):
    conn = get_conn()
    if not conn:
        return

    uid = str(user_id)

    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT images_today, last_reset FROM users WHERE user_id = %s", (uid,))
            user = cur.fetchone()

            if not user:
                return

            images = user["images_today"] or 0

            if user["last_reset"] != today():
                images = 0

            cur.execute("""
            UPDATE users
            SET images_today = %s, last_reset = %s
            WHERE user_id = %s
            """, (images + 1, today(), uid))


async def process(user_id, image_path, prompt):
    try:
        plan = get_user_plan(user_id)

        if plan == "premium":
            limit = 999
        elif plan == "lite":
            limit = 2
        else:
            limit = 1

        limits = get_limits(user_id, img_limit=limit)

        if limits["images_used"] >= limits["images_limit"]:
            return {
                "type": "text",
                "data": get_limit_message()
            }

        img = await asyncio.wait_for(
            edit_image(image_path, prompt),
            timeout=40
        )

        if not img:
            return {
                "type": "error",
                "data": None,
                "error": "edit_failed"
            }

        if plan != "premium":
            increment_images(user_id)

        return {
            "type": "image",
            "data": img
        }

    except asyncio.TimeoutError:
        return {
            "type": "error",
            "data": None,
            "error": "timeout"
        }

    except Exception as e:
        return {
            "type": "error",
            "data": None,
            "error": str(e)
        }
