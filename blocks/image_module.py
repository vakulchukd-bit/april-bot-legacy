import base64
import asyncio
from openai import OpenAI

# 🔥 ДОБАВИЛИ
from storage import get_user_plan, get_limits, get_conn, today

client = OpenAI()


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


async def generate_image(prompt):
    def run():
        print("🚀 START IMAGE GENERATION:", prompt)

        try:
            result = client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size="1024x1024"
            )

            print("📦 RAW RESULT:", result)

            if not result or not result.data:
                print("❌ EMPTY RESULT FROM OPENAI")
                return None

            if not hasattr(result.data[0], "b64_json"):
                print("❌ NO b64_json IN RESPONSE:", result.data[0])
                return None

            image_base64 = result.data[0].b64_json

            if not image_base64:
                print("❌ EMPTY b64_json")
                return None

            return base64.b64decode(image_base64)

        except Exception as e:
            print("🔥 IMAGE GENERATION ERROR:", e)
            return None

    return await asyncio.to_thread(run)


# 🔥 ДОБАВИЛИ (инкремент)
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


async def process(user_id, text, state):
    try:
        prompt = clean_prompt(text)

        if not prompt:
            return {
                "type": "error",
                "data": "❌ Пустой запрос для генерации"
            }

        # ===== 🔥 ЛИМИТ =====
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
                "data": "Сегодня лимит на создание изображений исчерпан 🙂 Попробуй завтра или переходи на Premium 👑"
            }

        # ===== ПЕРВАЯ ПОПЫТКА =====
        try:
            img = await asyncio.wait_for(generate_image(prompt), timeout=60)
        except asyncio.TimeoutError:
            print("⏱️ TIMEOUT FIRST ATTEMPT")
            img = None

        if img:
            increment_images(user_id)  # 🔥 ВАЖНО

            item = {
                "type": "generated",
                "source": "text",
                "prompt": prompt,
                "hint": prompt,
                "path": None
            }

            save_to_memory(state, item)

            return {
                "type": "image",
                "data": img
            }

        print("⚠️ FIRST ATTEMPT FAILED → RETRY")

        return {
            "type": "retry_notice",
            "data": "⏳ Картинка генерируется дольше обычного… пробую ещё раз"
        }

    except Exception as e:
        print("🔥 PROCESS ERROR:", e)

        return {
            "type": "error",
            "data": None,
            "error": str(e)
        }


# ===== ВТОРАЯ ПОПЫТКА =====
async def retry_process(user_id, text, state):
    try:
        prompt = clean_prompt(text)

        if not prompt:
            return {
                "type": "final_error",
                "data": "❌ Пустой запрос"
            }

        try:
            img = await asyncio.wait_for(generate_image(prompt), timeout=60)
        except asyncio.TimeoutError:
            print("⏱️ TIMEOUT SECOND ATTEMPT")
            img = None

        if img:
            increment_images(user_id)  # 🔥 ВАЖНО

            item = {
                "type": "generated",
                "source": "text",
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
