import base64
import asyncio
from openai import OpenAI

client = OpenAI()


# ===== 🔥 ПРОВЕРКА: ЭТО ТОЧНО ЗАПРОС НА ГЕНЕРАЦИЮ? =====
def is_valid_image_prompt(text: str) -> bool:
    t = text.lower()

    triggers = [
        "нарисуй",
        "сгенерируй",
        "создай",
        "draw",
        "generate"
    ]

    return any(x in t for x in triggers)


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


async def process(user_id, text, state):
    try:
        # 🚫 ЗАЩИТА ОТ СЛУЧАЙНОЙ ГЕНЕРАЦИИ
        if not is_valid_image_prompt(text):
            return {
                "type": "text",
                "data": "Я не вижу явного запроса на генерацию изображения 🤔\n\nНапиши, например: «нарисуй кота» или «создай картинку города»"
            }

        # ===== ПЕРВАЯ ПОПЫТКА =====
        try:
            img = await asyncio.wait_for(generate_image(text), timeout=60)
        except asyncio.TimeoutError:
            print("⏱️ TIMEOUT FIRST ATTEMPT")
            img = None

        if img:
            return {
                "type": "image",
                "data": img
            }

        # ===== СИГНАЛ О ПОВТОРЕ =====
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


# 🔥 ВТОРАЯ ПОПЫТКА
async def retry_process(user_id, text, state):
    try:
        # 🚫 ПОВТОРНАЯ ЗАЩИТА
        if not is_valid_image_prompt(text):
            return {
                "type": "final_error",
                "data": "⚠️ Запрос не похож на генерацию изображения"
            }

        try:
            img = await asyncio.wait_for(generate_image(text), timeout=60)
        except asyncio.TimeoutError:
            print("⏱️ TIMEOUT SECOND ATTEMPT")
            img = None

        if img:
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
