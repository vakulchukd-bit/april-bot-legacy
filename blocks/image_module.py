import base64
import asyncio
from openai import OpenAI

client = OpenAI()


# ===== 🔥 НОРМАЛИЗАЦИЯ ПРОМПТА =====
def normalize_prompt(prompt: str) -> str:
    if not prompt:
        return ""

    # убираем лишнее
    p = prompt.strip()

    # если слишком короткий — не ок
    if len(p.split()) < 2:
        return ""

    return p


# ===== 🔥 ГЕНЕРАЦИЯ =====
async def generate_image(prompt):
    def run():
        print("🚀 START IMAGE GENERATION:", prompt)

        try:
            result = client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size="1024x1024"
            )

            if not result or not result.data:
                print("❌ EMPTY RESULT FROM OPENAI")
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


# ===== 🔥 ОСНОВНОЙ ПРОЦЕСС =====
async def process(user_id, text, state):
    try:
        prompt = text

        # ===== 🔥 ВОССТАНОВЛЕНИЕ ПРОМПТА =====
        if state.get("pending_action") == "generate_image":
            last = state.get("last_prompt")

            if last:
                print("♻️ USING LAST PROMPT")
                prompt = last

        # ===== 🔥 НОРМАЛИЗАЦИЯ =====
        prompt = normalize_prompt(prompt)

        # если после нормализации пусто → спрашиваем
        if not prompt:
            return {
                "type": "text",
                "data": "Опиши, какую картинку ты хочешь 🙂"
            }

        # сохраняем
        state["last_prompt"] = prompt

        # ===== ПЕРВАЯ ПОПЫТКА =====
        try:
            img = await asyncio.wait_for(generate_image(prompt), timeout=60)
        except asyncio.TimeoutError:
            print("⏱️ TIMEOUT FIRST ATTEMPT")
            img = None

        if img:
            state["pending_action"] = None  # 🔥 сброс после успеха
            return {
                "type": "image",
                "data": img
            }

        print("⚠️ FIRST ATTEMPT FAILED → RETRY")

        return {
            "type": "retry_notice",
            "data": "⏳ Генерация заняла больше времени… пробую ещё раз"
        }

    except Exception as e:
        print("🔥 PROCESS ERROR:", e)

        return {
            "type": "error",
            "data": None,
            "error": str(e)
        }


# ===== 🔁 RETRY =====
async def retry_process(user_id, text, state):
    try:
        prompt = normalize_prompt(state.get("last_prompt") or text)

        if not prompt:
            return {
                "type": "final_error",
                "data": "⚠️ Нет описания для генерации"
            }

        try:
            img = await asyncio.wait_for(generate_image(prompt), timeout=60)
        except asyncio.TimeoutError:
            print("⏱️ TIMEOUT SECOND ATTEMPT")
            img = None

        if img:
            state["pending_action"] = None  # 🔥 сброс
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
