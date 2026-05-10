# =====================================================
# 🧠 APRIL PASSIVE IMAGE ANALYZER
# =====================================================

"""
Passive legacy image analyzer.

Этот модуль:
- НЕ управляет trajectory;
- НЕ принимает orchestration decisions;
- НЕ заменяет image rooms;
- НЕ вмешивается в cognition.

Он используется только как:
lightweight visual helper/fallback.

Главная задача:
безопасно и кратко анализировать изображения,
не ломая continuity April.
"""

# =====================================================
# 🔥 IMPORTS
# =====================================================

from openai import OpenAI

import asyncio
import os

client = OpenAI()

# =====================================================
# 🔥 CONFIG
# =====================================================

IMAGE_ANALYZE_MODEL = "gpt-4o-mini"

MAX_DESCRIPTION_SIZE = 500

# =====================================================
# 🔥 SAFE RESPONSE
# =====================================================

def safe_output(text: str):

    if not text:
        return (
            "Я увидела изображение, "
            "но не смогла нормально "
            "его проанализировать."
        )

    text = str(text).strip()

    if len(text) > MAX_DESCRIPTION_SIZE:

        text = (
            text[:MAX_DESCRIPTION_SIZE]
            + "…"
        )

    return text

# =====================================================
# 🔥 ANALYZE IMAGE
# =====================================================

async def analyze_image(path: str):

    # ================================================
    # 🔒 FILE SAFETY
    # ================================================

    if not path:

        return (
            "Изображение не найдено."
        )

    if not os.path.exists(path):

        return (
            "Файл изображения отсутствует."
        )

    # ================================================
    # 🚀 OPENAI CALL
    # ================================================

    def run():

        try:

            with open(path, "rb") as img:

                result = client.responses.create(

                    model=IMAGE_ANALYZE_MODEL,

                    input=[

                        {
                            "role": "user",

                            "content": [

                                {
                                    "type": "input_text",

                                    "text":
                                        (
                                            "Кратко и естественно "
                                            "опиши изображение. "
                                            "Без лишней болтовни."
                                        )
                                },

                                {
                                    "type": "input_image",

                                    "image": img.read()
                                }
                            ]
                        }
                    ]
                )

            output = getattr(
                result,
                "output_text",
                None
            )

            return safe_output(output)

        except Exception:

            return (
                "Не удалось "
                "проанализировать изображение."
            )

    # ================================================
    # 🧠 ASYNC SAFE
    # ================================================

    return await asyncio.to_thread(run)
