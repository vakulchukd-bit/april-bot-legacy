# =====================================================
# 🧠 APRIL PASSIVE IMAGE ANALYZER
# =====================================================

"""
Passive legacy image analyzer.

DeepHub stabilized version.

Этот модуль:
- НЕ управляет trajectory;
- НЕ принимает orchestration decisions;
- НЕ заменяет image rooms;
- НЕ вмешивается в cognition;
- НЕ конкурирует с renderer-space;
- НЕ конкурирует с Gemini helper;
- НЕ является primary visual system.

Он используется только как:
- passive visual helper;
- lightweight fallback;
- safe OpenAI visual backup.

Главная задача:
безопасно и кратко анализировать изображения,
не ломая continuity April
и не создавая visual conflicts.

Future philosophy:
этот модуль должен оставаться
тихим passive visual support layer
для OpenAI-first architecture.
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
# 🔥 PASSIVE STABILIZATION
# =====================================================

PASSIVE_MODE = True

FALLBACK_ONLY = True

ALLOW_PARALLEL_VISUAL_ANALYSIS = False

ALLOW_RENDERER_CONFLICT = False

ALLOW_PROVIDER_ROUTING = False

ALLOW_HEAVY_VISUAL_REASONING = False

PRIMARY_VISUAL_SYSTEM = False

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
# 🔥 PASSIVE VALIDATION
# =====================================================

def passive_analysis_allowed():

    """
    DeepHub philosophy:

    Этот модуль НЕ должен:
    - становиться main visual pipeline;
    - конкурировать с renderer-space;
    - создавать parallel visual execution;
    - создавать orchestration conflicts.

    Он всегда работает:
    - тихо;
    - локально;
    - как passive helper.
    """

    if not PASSIVE_MODE:
        return False

    if not FALLBACK_ONLY:
        return False

    if ALLOW_PARALLEL_VISUAL_ANALYSIS:
        return False

    if ALLOW_RENDERER_CONFLICT:
        return False

    if ALLOW_PROVIDER_ROUTING:
        return False

    if ALLOW_HEAVY_VISUAL_REASONING:
        return False

    if PRIMARY_VISUAL_SYSTEM:
        return False

    return True


# =====================================================
# 🔥 ANALYZE IMAGE
# =====================================================

async def analyze_image(path: str):

    # ================================================
    # 🔒 PASSIVE SAFETY
    # ================================================

    if not passive_analysis_allowed():

        return (
            "Passive visual helper "
            "temporarily disabled."
        )

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
                                            "Без лишней болтовни. "
                                            "Без robotic AI tone."
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
