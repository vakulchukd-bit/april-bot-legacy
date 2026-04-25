import base64
import asyncio
from openai import OpenAI

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


# ===== УМНЫЙ PROMPT =====
def build_smart_prompt(text, state):
    base = clean_prompt(text)

    last = state.get("image_context")

    if last and last.get("hint"):
        return f"""
Используй предыдущую сцену:
{last['hint']}

Изменение:
{base}

Сохрани стиль и композицию, измени только то, что указано.
Сделай результат естественным и аккуратным.
"""
    else:
        return f"""
Создай изображение:
{base}

Сделай его визуально приятным, с хорошим светом, композицией и деталями.
"""


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
        prompt = build_smart_prompt(text, state)

        if not prompt.strip():
            return {
                "type": "error",
                "data": "❌ Пустой запрос для генерации"
            }

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
                "hint": clean_prompt(text),
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
            "data": "⏳ Чуть дольше обычного… пробую ещё раз"
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
        prompt = build_smart_prompt(text, state)

        if not prompt.strip():
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
            item = {
                "type": "generated",
                "source": "text",
                "prompt": prompt,
                "hint": clean_prompt(text),
                "path": None
            }

            save_to_memory(state, item)

            return {
                "type": "image",
                "data": img
            }

        return {
            "type": "final_error",
            "data": "⚠️ Не получилось сейчас. Попробуй чуть позже 🙏"
        }

    except Exception as e:
        print("🔥 RETRY PROCESS ERROR:", e)

        return {
            "type": "final_error",
            "data": "⚠️ Сервис временно недоступен"
        }
