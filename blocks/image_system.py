import base64
from openai import OpenAI

client = OpenAI()

async def analyze_image(path: str) -> str:
    try:
        with open(path, "rb") as img:
            image_bytes = img.read()

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "Опиши, что изображено на картинке"},
                        {
                            "type": "input_image",
                            "image_base64": image_b64
                        }
                    ]
                }
            ]
        )

        return response.output_text

    except Exception as e:
        return f"Ошибка анализа изображения: {str(e)}"
