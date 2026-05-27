import os
import time
import json

from google import genai
from google.genai import errors as gemini_errors

from openai import OpenAI

# =====================================================
# 🔥 SHARED PROVIDER STATE
# =====================================================

from blocks.provider_router import (

    provider_state,

    should_restore_gemini,

    mark_gemini_failure,

    mark_gemini_success,

    provider_log
)

# =====================================================
# 🔥 PROVIDERS
# =====================================================

gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# =====================================================
# 🔥 VISUAL PROVIDER MODE
# =====================================================

ACTIVE_PROVIDER = "gemini"

# =====================================================
# 🔥 VISUAL MEMORY CONFIG
# =====================================================

MAX_OBJECTS = 12
MAX_VISIBLE_TEXT = 10
MAX_SCENE_SUMMARY = 320
MAX_PASSIVE_SCENES = 6

# =====================================================
# 🔥 PROVIDER SWITCH
# =====================================================

def set_provider(name: str):

    global ACTIVE_PROVIDER

    ACTIVE_PROVIDER = name

    provider_log(
        f"🧠 ACTIVE VISUAL PROVIDER: "
        f"{ACTIVE_PROVIDER}"
    )


def get_provider():

    return ACTIVE_PROVIDER

# =====================================================
# 🔥 SAFE GEMINI RECOVERY
# =====================================================

def can_try_gemini():

    if ACTIVE_PROVIDER == "gemini":

        return should_restore_gemini()

    return False

# =====================================================
# 🔥 VISUAL SCENE NORMALIZATION
# =====================================================

def normalize_visual_scene(
    raw_scene: dict
):

    raw_scene = raw_scene or {}

    objects = raw_scene.get(
        "objects",
        []
    )

    visible_text = raw_scene.get(
        "visible_text",
        []
    )

    normalized = {

        "scene_type":
            raw_scene.get(
                "scene_type",
                "unknown"
            ),

        "semantic_focus":
            raw_scene.get(
                "semantic_focus",
                "general"
            ),

        "summary":
            str(
                raw_scene.get(
                    "summary",
                    ""
                )
            )[:MAX_SCENE_SUMMARY],

        "objects":
            objects[:MAX_OBJECTS],

        "visible_text":
            visible_text[:MAX_VISIBLE_TEXT],

        "environment":
            raw_scene.get(
                "environment",
                {}
            ),

        "colors":
            raw_scene.get(
                "colors",
                []
            ),

        "brands":
            raw_scene.get(
                "brands",
                []
            ),

        "positions":
            raw_scene.get(
                "positions",
                []
            ),

        "continuity_active": True,

        "scene_alive": True,

        "lifecycle_state": "ACTIVE",

        "provider":
            ACTIVE_PROVIDER,

        "timestamp":
            time.time()
    }

    return normalized

# =====================================================
# 🔥 VISUAL SCENE COMPRESSION
# =====================================================

def compress_visual_scene(
    scene: dict
):

    if not scene:
        return {}

    return {

        "scene_type":
            scene.get(
                "scene_type"
            ),

        "semantic_focus":
            scene.get(
                "semantic_focus"
            ),

        "summary":
            scene.get(
                "summary"
            ),

        "objects":
            scene.get(
                "objects",
                []
            )[:5],

        "brands":
            scene.get(
                "brands",
                []
            )[:5],

        "colors":
            scene.get(
                "colors",
                []
            )[:5],

        "lifecycle_state":
            "PASSIVE"
    }

# =====================================================
# 🔥 VISUAL MEMORY UPDATE
# =====================================================

def update_visual_memory(
    state: dict,
    visual_scene: dict
):

    if not state:
        return

    previous_scene = state.get(
        "active_visual_scene"
    )

    passive_memory = state.get(
        "passive_visual_memory",
        []
    )

    # =================================================
    # 🔥 ARCHIVE PREVIOUS
    # =====================================================

    if previous_scene:

        compressed = compress_visual_scene(
            previous_scene
        )

        passive_memory.append(
            compressed
        )

        passive_memory = (
            passive_memory[
                -MAX_PASSIVE_SCENES:
            ]
        )

    # =================================================
    # 🔥 STORE ACTIVE
    # =====================================================

    state[
        "active_visual_scene"
    ] = visual_scene

    state[
        "passive_visual_memory"
    ] = passive_memory

# =====================================================
# 🔥 GEMINI VISUAL EXTRACTION
# =====================================================

async def analyze_with_gemini(
    path: str
):

    provider_log(
        "🧠 GEMINI VISUAL START"
    )

    uploaded_file = gemini_client.files.upload(
        file=path
    )

    provider_log(
        "🧠 GEMINI FILE UPLOADED"
    )

    response = gemini_client.models.generate_content(

        model="gemini-2.5-flash",

        contents=[

            uploaded_file,

            """
Ты visual semantic extractor внутри April.

Твоя задача:
НЕ писать человеческий ответ.

Нужно извлечь semantic visual scene.

Верни JSON:

{
  "scene_type": "...",
  "semantic_focus": "...",
  "summary": "...",

  "objects": [
    {
      "type": "...",
      "brand": "...",
      "model": "...",
      "color": "...",
      "position": "..."
    }
  ],

  "visible_text": [],
  "colors": [],
  "brands": [],
  "positions": [],

  "environment": {
    "location_type": "...",
    "lighting": "...",
    "atmosphere": "..."
  }
}

Правила:
- НЕ roleplay;
- НЕ объясняй;
- НЕ говори как AI;
- НЕ добавляй markdown;
- только JSON;
- кратко;
- semantic continuity priority.
"""
        ]
    )

    raw_text = (
        response.text
        if response.text
        else "{}"
    )

    try:

        parsed = json.loads(
            raw_text
        )

    except Exception:

        parsed = {

            "scene_type": "unknown",

            "semantic_focus": "general",

            "summary":
                raw_text[:220],

            "objects": []
        }

    mark_gemini_success()

    provider_log(
        "🧠 GEMINI VISUAL SUCCESS"
    )

    return normalize_visual_scene(
        parsed
    )

# =====================================================
# 🔥 OPENAI FALLBACK
# =====================================================

async def analyze_with_openai(
    path: str
):

    provider_log(
        "⚠️ OPENAI VISUAL FALLBACK"
    )

    with open(path, "rb") as image_file:

        image_bytes = image_file.read()

    response = openai_client.responses.create(

        model="gpt-4.1-mini",

        input=[

            {
                "role": "user",

                "content": [

                    {
                        "type": "input_text",

                        "text": """
Extract visual semantic scene.

Return ONLY JSON.

No markdown.
No explanations.
No AI phrases.
"""
                    },

                    {
                        "type": "input_image",

                        "image_data": image_bytes
                    }
                ]
            }
        ]
    )

    raw_text = getattr(
        response,
        "output_text",
        "{}"
    )

    try:

        parsed = json.loads(
            raw_text
        )

    except Exception:

        parsed = {

            "scene_type": "unknown",

            "semantic_focus": "general",

            "summary":
                raw_text[:220],

            "objects": []
        }

    provider_log(
        "🧠 OPENAI VISUAL SUCCESS"
    )

    return normalize_visual_scene(
        parsed
    )

# =====================================================
# 🔥 MAIN VISUAL SYSTEM
# =====================================================

async def analyze_image_gemini(
    path: str,
    state: dict = None
):

    global ACTIVE_PROVIDER

    state = state or {}

    try:

        # =================================================
        # 🔥 GEMINI PRIMARY
        # =====================================================

        if can_try_gemini():

            try:

                visual_scene = await analyze_with_gemini(
                    path
                )

                update_visual_memory(
                    state,
                    visual_scene
                )

                return visual_scene

            except Exception as gemini_error:

                provider_log(
                    "🔥 GEMINI VISUAL ERROR:",
                    gemini_error
                )

                mark_gemini_failure()

                set_provider(
                    "openai"
                )

        # =================================================
        # 🔥 OPENAI FALLBACK
        # =====================================================

        visual_scene = await analyze_with_openai(
            path
        )

        update_visual_memory(
            state,
            visual_scene
        )

        # =================================================
        # 🔥 GEMINI RECOVERY
        # =====================================================

        now = time.time()

        last_failure = provider_state.get(
            "last_gemini_failure",
            0
        )

        cooldown = provider_state.get(
            "recovery_cooldown",
            45
        )

        if now - last_failure >= cooldown:

            provider_log(
                "🧠 GEMINI RECOVERY READY"
            )

            set_provider(
                "gemini"
            )

        return visual_scene

    except Exception as e:

        provider_log(
            "🔥 VISUAL SYSTEM ERROR:",
            e
        )

        return {

            "scene_type": "error",

            "semantic_focus": "error",

            "summary":
                "visual analysis failed",

            "objects": [],

            "continuity_active": False
        }
