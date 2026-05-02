from openai import OpenAI
import asyncio

client = OpenAI()


def detect_intent_local(text: str):
    t = text.lower()

    # 🔥 быстрые и бесплатные проверки
    if any(x in t for x in ["нарисуй", "создай", "сгенерируй", "картинку", "изображение"]):
        return "generate_image"

    if any(x in t for x in ["измени", "добавь", "убери", "замени"]):
        return "edit_image"

    if any(x in t for x in ["что на картинке", "что изображено", "что это"]):
        return "analyze_image"

    return None


# 🔥 ОБНОВЛЕНО: добавили state, но НЕ ломаем логику
async def detect_intent_ai(text: str, state: dict = None):
    # 🔥 1. Сначала пробуем бесплатно
    local = detect_intent_local(text)
    if local:
        return {
            "intent": local
        }

    # 🔥 2. Короткие и простые сообщения не гоняем в OpenAI
    if len(text.strip()) < 15:
        return {
            "intent": "text"
        }

    def run():
        try:
            prompt = f"""
Определи намерение пользователя.

Варианты:
- generate_image
- analyze_image
- edit_image
- text

Ответь ОДНИМ словом.

Текст: {text}
"""

            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=5
            )

            intent = res.choices[0].message.content.strip().lower()

            return {
                "intent": intent
            }

        except Exception as e:
            print("🔥 INTENT AI ERROR:", e)
            return {
                "intent": "text"
            }

    return await asyncio.to_thread(run)
