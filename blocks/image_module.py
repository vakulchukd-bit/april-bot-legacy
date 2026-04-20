# blocks/image_module.py

import base64
import asyncio
from openai import OpenAI

client = OpenAI()

def enhance_prompt(user_prompt):
    return user_prompt


async def generate_image(prompt):
    def run():
        result = client.images.generate(
            model="gpt-image-1",
            prompt=enhance_prompt(prompt),
            size="1024x1024"
        )
        return base64.b64decode(result.data[0].b64_json)

    return await asyncio.to_thread(run)


async def process(user_id, text, state):
    img = await generate_image(text)

    return {
        "type": "image",
        "data": img,
        "caption": "Оцени 👇"
    }
