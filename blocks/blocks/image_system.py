# =====================================================
# 🧠 APRIL PASSIVE IMAGE ANALYZER
# =====================================================

"""
Passive visual support layer.

April renderer-first architecture.

Этот модуль:
- НЕ orchestration layer;
- НЕ trajectory authority;
- НЕ renderer;
- НЕ primary cognition;
- НЕ visual narrator;
- НЕ standalone image system.

Он:
- помогает visual continuity;
- извлекает lightweight scene observations;
- поддерживает semantic visual understanding;
- работает как passive provider helper;
- не ломает active scene.

Главная задача:
давать April
спокойные structured visual signals,
а НЕ narration или storytelling.

Архитектурный принцип:
machine-readable inside,
human-safe outside.
"""

# =====================================================
# 🔥 IMPORTS
# =====================================================

from openai import OpenAI

import asyncio
import os
import re

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
# 🔥 MACHINE VISUAL FORMAT
# =====================================================

MACHINE_VISUAL_PROMPT = """

Analyze image safely.

Return ONLY lightweight visual observations.

Avoid:
- narration;
- storytelling;
- assumptions;
- emotional overexplaining;
- "probably";
- "maybe";
- "looks like";
- AI-style commentary.

Focus only on:

- visible objects
- ui elements
- layout
- text
- colors
- scene type
- atmosphere
- continuity-safe observations

Keep response compact.
"""

# =====================================================
# 🔥 NOISE FILTER
# =====================================================

NOISE_PATTERNS = [

    "вероятно",
    "возможно",
    "похоже",
    "кажется",
    "скорее всего",

    "probably",
    "maybe",
    "it seems",
    "appears to",
    "looks like"
]

# =====================================================
# 🔥 SAFE CLEAN
# =====================================================

def clean_visual_noise(
    text: str
):

    if not text:
        return ""

    cleaned = str(text)

    for pattern in NOISE_PATTERNS:

        cleaned = re.sub(
            pattern,
            "",
            cleaned,
            flags=re.IGNORECASE
        )

    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned
    )

    return cleaned.strip()

# =====================================================
# 🔥 SAFE OUTPUT
# =====================================================

def safe_output(text: str):

    if not text:

        return (
            "Visual observation unavailable."
        )

    text = clean_visual_noise(
        text
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
    Passive visual support only.

    Этот модуль:
    - не конкурирует с renderer-space;
    - не заменяет cognition;
    - не управляет trajectory;
    - не создает orchestration conflicts.
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
# 🔥 BUILD MACHINE VISUAL STATE
# =====================================================

def build_machine_visual_state(
    text: str
):

    text = safe_output(text)

    return {

        "type": "passive_visual_observation",

        "continuity_safe": True,

        "renderer_conflict": False,

        "provider": "openai",

        "mode": "passive_helper",

        "summary": text
    }

# =====================================================
# 🔥 ANALYZE IMAGE
# =====================================================

async def analyze_image(path: str):

    # ================================================
    # 🔒 PASSIVE SAFETY
    # ================================================

    if not passive_analysis_allowed():

        return build_machine_visual_state(

            "Passive visual helper disabled."
        )

    # ================================================
    # 🔒 FILE SAFETY
    # ================================================

    if not path:

        return build_machine_visual_state(

            "Image path missing."
        )

    if not os.path.exists(path):

        return build_machine_visual_state(

            "Image file missing."
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
                                        MACHINE_VISUAL_PROMPT
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

            return build_machine_visual_state(

                safe_output(output)
            )

        except Exception:

            return build_machine_visual_state(

                "Passive visual analysis failed."
            )

    # ================================================
    # 🧠 ASYNC SAFE
    # ================================================

    return await asyncio.to_thread(run)
