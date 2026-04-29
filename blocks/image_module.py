import base64
import asyncio
from openai import OpenAI

from storage import get_user_plan, get_limits, get_conn, today

client = OpenAI()

ADMIN_ID = 2016592532


def save_to_memory(state, item):
    memory = state.get("image_memory", [])
    memory.append(item)

    if len(memory) > 3:
        memory = memory[-3:]

    state["image_memory"] = memory
    state["image_context"] = item


def clean_prompt(text: str):
    if not text:
        return ""

    t = text.strip()

    banned = ["система", "анализ личности", "контекст:", "опыт:"]
    for b in banned:
        if b in t.lower():
            t = t.lower().replace(b, "")

    return t.strip()


def extract_image_prompt(text: str):
    if not text:
        return ""

    t = text.lower()

    banned = [
        "давай", "хочу", "сделай", "создай", "нарисуй",
        "пожалуйста", "можешь", "как думаешь"
    ]

    for b in banned:
        t = t.replace(b, "")

    t = t.strip()

    if len(t) > 300:
        t = t[:300]

    return t


# ===== V1 =====
async def generate_image(prompt):
    def run():
        try:
            response = client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size="512x512",
                quality="low"
            )

            if not response or not response.data:
                print("🔥 IMAGE ERROR: пустой response (v1)")
                return None

            if not hasattr(response.data[0], "b64_json"):
                print("🔥 IMAGE ERROR: нет b64_json (v1)")
                return None

            image_base64 = response.data[0].b64_json

            if not image_base64:
                print("🔥 IMAGE ERROR: пустой base64 (v1)")
                return None

            return base64.b64decode(image_base64)

        except Exception as e:
            print("🔥 IMAGE ERROR (v1):", e)
            return None

    return await asyncio.get_event_loop().run_in_executor(None, run)


# ===== V2 =====
async def generate_image_v2(prompt):
    def run():
        try:
            response = client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size="512x512",
                quality="low"
            )

            if not response or not response.data:
                print("🔥 IMAGE ERROR: пустой response (v2)")
                return None

            if not hasattr(response.data[0], "b64_json"):
                print("🔥 IMAGE ERROR: нет b64_json (v2)")
                return None

            image_base64 = response.data[0].b64_json

            if not image_base64:
                print("🔥 IMAGE ERROR: пустой base64 (v2)")
                return None

            return base64.b64decode(image_base64)

        except Exception as e:
            print("🔥 IMAGE ERROR (v2):", e)
            return None

    return await asyncio.get_event_loop().run_in_executor(None, run)


def increment_images(user_id):
    conn = get_conn()
    if not conn:
        return

    uid = str(user_id)

    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT images_today, last_reset FROM users WHERE user_id = %s",
                (uid,)
            )
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


async def process(user_id, text, state):
    try:
        prompt = clean_prompt(text)
        prompt = extract_image_prompt(prompt)

        if not prompt:
            return {
                "type": "error",
                "data": "❌ Пустой запрос для генерации"
            }

        is_admin = user_id == ADMIN_ID
        plan = get_user_plan(user_id)

        if not is_admin and plan == "free":
            limit = 1
            limits = get_limits(user_id, img_limit=limit)

            if limits["images_used"] >= limits["images_limit"]:
                return {
                    "type": "text",
                    "data": "Сегодня лимит на создание изображений исчерпан 🙂"
                }

        img = await generate_image_v2(prompt)

        if img:
            if not is_admin and plan == "free":
                increment_images(user_id)

            save_to_memory(state, {
                "type": "generated",
                "source": "v2",
                "prompt": prompt,
                "hint": prompt,
                "path": None
            })

            return {"type": "image", "data": img}

        img = await generate_image(prompt)

        if img:
            if not is_admin and plan == "free":
                increment_images(user_id)

            save_to_memory(state, {
                "type": "generated",
                "source": "v1",
                "prompt": prompt,
                "hint": prompt,
                "path": None
            })

            return {"type": "image", "data": img}

        print("🔥 IMAGE ERROR: обе генерации вернули None")

        return {
            "type": "final_error",
            "data": "⚠️ Не удалось создать изображение"
        }

    except Exception as e:
        print("🔥 IMAGE PROCESS ERROR:", e)
        return {"type": "error", "data": None}


async def retry_process(user_id, text, state):
    try:
        prompt = clean_prompt(text)
        prompt = extract_image_prompt(prompt)

        if not prompt:
            return {
                "type": "final_error",
                "data": "❌ Пустой запрос"
            }

        is_admin = user_id == ADMIN_ID

        img = await generate_image_v2(prompt)

        if not img:
            img = await generate_image(prompt)

        if img:
            plan = get_user_plan(user_id)
            if not is_admin and plan == "free":
                increment_images(user_id)

            save_to_memory(state, {
                "type": "generated",
                "source": "retry",
                "prompt": prompt,
                "hint": prompt,
                "path": None
            })

            return {"type": "image", "data": img}

        print("🔥 IMAGE RETRY ERROR: обе генерации None")

        return {
            "type": "final_error",
            "data": "⚠️ Не удалось создать изображение"
        }

    except Exception as e:
        print("🔥 IMAGE RETRY ERROR:", e)
        return {"type": "final_error", "data": "⚠️ Сервис временно недоступен"}
