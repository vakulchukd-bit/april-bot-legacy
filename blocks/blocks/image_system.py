print("❗ SECOND IMAGE SYSTEM WORKING")
from openai import OpenAI
import asyncio

client = OpenAI()

async def analyze_image(path: str) -> str:
    def run():
        with open(path, "rb") as img:
            result = client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": "Кратко опиши, что на изображении"},
                            {"type": "input_image", "image": img.read()}
                        ]
                    }
                ]
            )
        return result.output_text

    return await asyncio.to_thread(run)
