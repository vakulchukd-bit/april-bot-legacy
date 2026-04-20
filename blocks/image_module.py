# blocks/image_module.py

import base64
import asyncio
from openai import OpenAI

client = OpenAI()


async def generate_image(prompt):
    def run():
        result = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )
        return base64.b64decode(result.data[0].b64_json)

    return await asyncio.to_thread(run)


async def process(user_id, text, state):
    try:
        img = await asyncio.wait_for(generate_image(text), timeout=30)

        return {
            "type": "image",
            "data": img,
            "caption": "Оцени 👇"
        }

    except asyncio.TimeoutError:
        return {
            "type": "error",
            "text": "⏳ Слишком долго генерируется. Попробуй ещё раз"
        }

    except Exception as e:
        return {
            "type": "error",
            "text": "❌ Ошибка генерации картинки"
        }
