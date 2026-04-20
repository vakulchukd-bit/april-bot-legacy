# blocks/image_edit_module.py

import base64
import asyncio
from openai import OpenAI

client = OpenAI()


async def edit_image(image_path, prompt):
    def run():
        with open(image_path, "rb") as f:
            result = client.images.edit(
                model="gpt-image-1",
                image=f,
                prompt=prompt
            )

        if not result or not result.data:
            return None

        try:
            return base64.b64decode(result.data[0].b64_json)
        except Exception:
            return None

    return await asyncio.to_thread(run)


async def process(user_id, image_path, prompt):
    try:
        img = await asyncio.wait_for(
            edit_image(image_path, prompt),
            timeout=40
        )

        if not img:
            return {
                "type": "error",
                "data": None,
                "error": "edit_failed"
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
