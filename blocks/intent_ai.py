from openai import OpenAI
import asyncio

client = OpenAI()


async def detect_intent_ai(text: str):
    def run():
        try:
            prompt = f"""
Определи намерение пользователя.

Варианты:
- generate_image (если хочет создать изображение)
- analyze_image (если спрашивает про картинку)
- edit_image (если хочет изменить изображение)
- text (обычный разговор)

Ответь ТОЛЬКО одним словом.

Текст: {text}
"""

            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )

            intent = res.choices[0].message.content.strip().lower()

            return intent

        except Exception as e:
            print("🔥 INTENT AI ERROR:", e)
            return None

    return await asyncio.to_thread(run)
