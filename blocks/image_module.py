import base64
import asyncio
from openai import OpenAI

client = OpenAI()


def normalize_prompt(prompt: str) -> str:
    if not prompt:
        return ""

    p = prompt.strip()

    if len(p.split()) < 2:
        return ""

    return p


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


async def process(user_id, text, state):
    try:
        prompt = text

        if state.get("pending_action") == "generate_image":
            last = state.get("last_prompt")
            if last:
                prompt = last

        prompt = normalize_prompt(prompt)

        if not prompt:
            return {
                "type": "text",
                "data": "Опиши, какую картинку ты хочешь 🙂"
            }

        state["last_prompt"] = prompt

        try:
            img = await asyncio.wait_for(generate_image(prompt), timeout=60)
        except asyncio.TimeoutError:
            print("⏱️ TIMEOUT")
            img = None

        if img:
            state["pending_action"] = None
            return {
                "type": "image",
                "data": img
            }

        # ❗ ВАЖНО: БОЛЬШЕ НИКАКИХ retry_notice
        return {
            "type": "text",
            "data": "⚠️ Не удалось создать изображение. Попробуй ещё раз."
        }

    except Exception as e:
        print("🔥 PROCESS ERROR:", e)

        return {
            "type": "text",
            "data": "⚠️ Ошибка при генерации изображения"
        }


async def retry_process(user_id, text, state):
    try:
        prompt = normalize_prompt(state.get("last_prompt") or text)

        if not prompt:
            return {
                "type": "text",
                "data": "⚠️ Нет описания для генерации"
            }

        try:
            img = await asyncio.wait_for(generate_image(prompt), timeout=60)
        except asyncio.TimeoutError:
            img = None

        if img:
            state["pending_action"] = None
            return {
                "type": "image",
                "data": img
            }

        return {
            "type": "text",
            "data": "⚠️ Не удалось создать изображение"
        }

    except Exception:
        return {
            "type": "text",
            "data": "⚠️ Сервис временно недоступен"
        }
