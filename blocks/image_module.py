import base64
import asyncio
from openai import OpenAI

# 🔥 ДОБАВИЛИ
from storage import get_user_plan, get_limits, get_conn, today

client = OpenAI()

ADMIN_ID = 2016592532  # 🔥 ДОБАВИЛИ


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


# ===== ОСНОВНОЙ ГЕНЕРАТОР =====
async def generate_image(prompt):
    def run():
        print("🚀 START IMAGE GENERATION (v1):", prompt)

        try:
            result = client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size="768x768"
            )

            if not result or not result.data:
                return None

            if not hasattr(result.data[0], "b64_json"):
                return None

            image_base64 = result.data[0].b64_json

            if not image_base64:
                return None

            return base64.b64decode(image_base64)

        except Exception as e:
            print("🔥 IMAGE V1 ERROR:", e)
            return None

    return await asyncio.to_thread(run)


# ===== FALLBACK ГЕНЕРАТОР (v2) =====
async def generate_image_v2(prompt):
    def run():
        print("🟡 FALLBACK IMAGE GENERATION (v2):", prompt)

        try:
            result = client.images.generate(
                model="gpt-image-1",  # 👉 тут потом поставишь 5.5
                prompt=prompt,
                size="768x768"
            )

            if not result or not result.data:
                return None

            if not hasattr(result.data[0], "b64_json"):
                return None

            image_base64 = result.data[0].b64_json

            if not image_base64:
                return None

            return base64.b64decode(image_base64)

        except Exception as e:
            print("🔥 IMAGE V2 ERROR:", e)
            return None

    try:
        return await asyncio.wait_for(asyncio.to_thread(run), timeout=25)
    except:
        return None


# 🔥 ДОБАВИЛИ (инкремент)
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
                    "data": "Сегодня лимит на создание изображений исчерпан 🙂 Попробуй завтра или переходи на Premium 👑"
                }

        # ===== ПЕРВАЯ ПОПЫТКА =====
        try:
            img = await asyncio.wait_for(generate_image(prompt), timeout=20)
        except asyncio.TimeoutError:
            print("⏱️ TIMEOUT V1")
            img = None

        # ===== УСПЕХ =====
        if img:
            if not is_admin and plan == "free":
                increment_images(user_id)

            item = {
                "type": "generated",
                "source": "v1",
                "prompt": prompt,
                "hint": prompt,
                "path": None
            }

            save_to_memory(state, item)

            return {
                "type": "image",
                "data": img
            }

        # ===== FALLBACK =====
        print("⚠️ SWITCH TO V2")

        img = await generate_image_v2(prompt)

        if img:
            if not is_admin and plan == "free":
                increment_images(user_id)

            item = {
                "type": "generated",
                "source": "v2",
                "prompt": prompt,
                "hint": prompt,
                "path": None
            }

            save_to_memory(state, item)

            return {
                "type": "image",
                "data": img
            }

        # ===== ОБА НЕ СРАБОТАЛИ =====
        return {
            "type": "final_error",
            "data": "⚠️ Не удалось создать изображение даже через резервную систему"
        }

    except Exception as e:
        print("🔥 PROCESS ERROR:", e)

        return {
            "type": "error",
            "data": None,
            "error": str(e)
        }


# ===== ВТОРАЯ ПОПЫТКА (оставили как есть) =====
async def retry_process(user_id, text, state):
    try:
        prompt = clean_prompt(text)

        if not prompt:
            return {
                "type": "final_error",
                "data": "❌ Пустой запрос"
            }

        is_admin = user_id == ADMIN_ID

        try:
            img = await asyncio.wait_for(generate_image(prompt), timeout=60)
        except asyncio.TimeoutError:
            print("⏱️ TIMEOUT SECOND ATTEMPT")
            img = None

        if img:
            plan = get_user_plan(user_id)
            if not is_admin and plan == "free":
                increment_images(user_id)

            item = {
                "type": "generated",
                "source": "retry",
                "prompt": prompt,
                "hint": prompt,
                "path": None
            }

            save_to_memory(state, item)

            return {
                "type": "image",
                "data": img
            }

        return {
            "type": "final_error",
            "data": "⚠️ Не удалось создать изображение.\nПопробуй ещё раз чуть позже 🙏"
        }

    except Exception as e:
        print("🔥 RETRY PROCESS ERROR:", e)

        return {
            "type": "final_error",
            "data": "⚠️ Сервис временно недоступен"
        }
