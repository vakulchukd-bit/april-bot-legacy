# blocks/image_module.py

import base64
import asyncio
from openai import OpenAI

client = OpenAI()


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

            # проверка ответа
            if not result or not result.data:
                print("❌ EMPTY RESULT FROM OPENAI")
                return None

            # проверяем наличие base64
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
        img = await asyncio.wait_for(generate_image(text), timeout=30)

        if not img:
            return {
                "type": "error",
                "data": None,
                "error": "generation_failed"
            }

        return {
            "type": "image",
            "data": img
        }

    except asyncio.TimeoutError:
        print("⏱️ IMAGE GENERATION TIMEOUT")

        return {
            "type": "error",
            "data": None,
            "error": "timeout"
        }

    except Exception as e:
        print("🔥 PROCESS ERROR:", e)

        return {
            "type": "error",
            "data": None,
            "error": str(e)
        }
