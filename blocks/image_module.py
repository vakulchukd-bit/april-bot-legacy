import base64
import asyncio
from openai import OpenAI

client = OpenAI()


# ===== 🔥 ДОБАВЛЕНО: СОХРАНЕНИЕ В ПАМЯТЬ =====
def save_to_memory(state, item):
    memory = state.get("image_memory", [])

    # добавляем новую
    memory.append(item)

    # ограничиваем до 3 последних
    if len(memory) > 3:
        memory = memory[-3:]

    state["image_memory"] = memory
    state["image_context"] = item  # текущая активная


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
        prompt = text

        # ===== ПЕРВАЯ ПОПЫТКА =====
        try:
            img = await asyncio.wait_for(generate_image(prompt), timeout=60)
        except asyncio.TimeoutError:
            print("⏱️ TIMEOUT FIRST ATTEMPT")
            img = None

        if img:
            item = {
                "type": "generated",
                "source": "text",
                "prompt": prompt,
                "hint": prompt,
                "path": None
            }

            # 🔥 СОХРАНЕНИЕ В ПАМЯТЬ
            save_to_memory(state, item)

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


# 🔥 ВТОРАЯ ПОПЫТКА (отдельно вызывается)
async def retry_process(user_id, text, state):
    try:
        prompt = text

        try:
            img = await asyncio.wait_for(generate_image(prompt), timeout=60)
        except asyncio.TimeoutError:
            print("⏱️ TIMEOUT SECOND ATTEMPT")
            img = None

        if img:
            item = {
                "type": "generated",
                "source": "text",
                "prompt": prompt,
                "hint": prompt,
                "path": None
            }

            # 🔥 СОХРАНЕНИЕ В ПАМЯТЬ
            save_to_memory(state, item)

            return {
                "type": "image",
                "data": img
            }

        # ===== ФИНАЛЬНАЯ ОШИБКА =====
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
