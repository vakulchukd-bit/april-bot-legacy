import base64
import asyncio
from openai import OpenAI

from storage import get_user_plan, get_limits, get_conn, today

client = OpenAI()

ADMIN_ID = 2016592532


# ===== СОХРАНЕНИЕ В ПАМЯТЬ =====
def save_to_memory(state, item):
    memory = state.get("image_memory", [])

    memory.append(item)

    if len(memory) > 3:
        memory = memory[-3:]

    state["image_memory"] = memory
    state["image_context"] = item


# ===== ОЧИСТКА PROMPT =====
def clean_prompt(text: str):
    if not text:
        return ""

    t = text.strip()

    banned = ["система", "анализ личности", "контекст:", "опыт:"]
    for b in banned:
        if b in t.lower():
            t = t.lower().replace(b, "")

    return t.strip()


# ===== V1 (РЕЗЕРВ, БЕЗ TIMEOUT) =====
async def generate_image(prompt):
    def run():
        print("🟢 ENTER V1 (fallback):", prompt)

        try:
            response = client.images.generate(
                model="gpt-image-1",
                prompt=prompt
            )

            if not response or not response.data:
                print("❌ V1 EMPTY")
                return None

            if not hasattr(response.data[0], "b64_json"):
                print("❌ V1 NO BASE64")
                return None

            image_base64 = response.data[0].b64_json

            if not image_base64:
                print("❌ V1 EMPTY BASE64")
                return None

            print("🟢 EXIT V1 OK")

            return base64.b64decode(image_base64)

        except Exception as e:
            print("🔥 IMAGE V1 ERROR:", repr(e))
            return None

    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, run)
    except Exception as e:
        print("🔥 EXECUTOR V1 ERROR:", repr(e))
        return None


# ===== V2 (ОСНОВНОЙ, БЕЗ УБИЙСТВА) =====
async def generate_image_v2(prompt):
    def run():
        print("🟡 ENTER V2 (main):", prompt)

        try:
            response = client.images.generate(
                model="gpt-image-1",
                prompt=prompt
            )

            if not response or not response.data:
                print("❌ V2 EMPTY")
                return None

            if not hasattr(response.data[0], "b64_json"):
                print("❌ V2 NO BASE64")
                return None

            image_base64 = response.data[0].b64_json

            if not image_base64:
                print("❌ V2 EMPTY BASE64")
                return None

            print("🟡 EXIT V2 OK")

            return base64.b64decode(image_base64)

        except Exception as e:
            print("🔥 IMAGE V2 ERROR FULL:", repr(e))
            return None

    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, run)
    except Exception as e:
        print("🔥 EXECUTOR V2 ERROR:", repr(e))
        return None


# ===== ИНКРЕМЕНТ =====
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


# ===== PROCESS =====
async def process(user_id, text, state):
    try:
        prompt = clean_prompt(text)

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

        # ===== 🚀 ОСНОВНОЙ ПОТОК (ТОЛЬКО V2) =====
        print("🚀 TRY V2 FIRST")

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

        # ===== ⚠️ РЕДКИЙ FALLBACK (БЕЗ TIMEOUT И ПАНИКИ) =====
        print("⚠️ V2 FAILED → TRY V1 (fallback)")

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

        return {
            "type": "final_error",
            "data": "⚠️ Не удалось создать изображение"
        }

    except Exception as e:
        print("🔥 PROCESS ERROR:", repr(e))
        return {"type": "error", "data": None}


# ===== RETRY (ТОЖЕ БЕЗ УБИЙСТВА) =====
async def retry_process(user_id, text, state):
    try:
        prompt = clean_prompt(text)

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

        return {
            "type": "final_error",
            "data": "⚠️ Не удалось создать изображение"
        }

    except Exception as e:
        print("🔥 RETRY ERROR:", repr(e))
        return {"type": "final_error", "data": "⚠️ Сервис временно недоступен"}
