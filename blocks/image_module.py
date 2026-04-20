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

        # 🔥 проверка ответа
        if not result or not result.data:
            return None

        try:
            return base64.b64decode(result.data[0].b64_json)
        except Exception:
            return None

    return await asyncio.to_thread(run)


async def process(user_id, text, state):
    try:
        img = await asyncio.wait_for(generate_image(text), timeout=30)

        # 🔥 если пустой результат
        if not img:
            return {
                "type": "error",
                "data": None,
                "error": "empty_result"
            }

        return {
            "type": "image",
            "data": img
        }

    except asyncio.TimeoutError:
        return {
            "type": "error",
            "data": None,
            "error": "timeout"
        }

    except Exception as e:
        return {
            "type": "error",
            "data": None,
            "error": str(e)
        }
