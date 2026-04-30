print("🔥 MAIN IMAGE SYSTEM WORKING")
import base64
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def analyze_image(path: str, state=None) -> str:
    try:
        # 🔥 1. ЕСЛИ УЖЕ АНАЛИЗИРОВАЛИ — НЕ ИДЁМ В OPENAI
        if state:
            cached = state.get("image_analysis")
            cached_path = state.get("image_analysis_path")

            if cached and cached_path == path:
                print("🧠 USING CACHED IMAGE ANALYSIS")
                return cached

        # 🔥 2. ЧИТАЕМ ФАЙЛ
        with open(path, "rb") as img:
            image_bytes = img.read()

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # 🔥 3. ОДИН ЧЁТКИЙ ЗАПРОС (БЕЗ ЛИШНЕГО)
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Коротко опиши, что на изображении"
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    ]
                }
            ],
            max_output_tokens=150  # 🔥 ограничение
        )

        result = response.output_text

        # 🔥 4. СОХРАНЯЕМ В ПАМЯТЬ (чтобы не платить повторно)
        if state is not None:
            state["image_analysis"] = result
            state["image_analysis_path"] = path

        return result

    except Exception as e:
        return f"Ошибка анализа изображения: {str(e)}"
