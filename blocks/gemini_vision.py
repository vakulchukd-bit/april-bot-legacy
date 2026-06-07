# =====================================================
# 🧠 APRIL VISUAL SEMANTIC ORCHESTRATOR CORE
# =====================================================

"""
APRIL VISUAL ORCHESTRATOR CORE

APRIL_FILE_ID:
APRIL_VISUAL_SEMANTIC_ORCHESTRATOR_CORE

ROLE:
CENTRAL_VISUAL_SEMANTIC_COORDINATOR

INPUT:
IMAGE_PATH
EXECUTOR_MACHINE_CONTEXT
VISUAL_STATE
SCENE_STATE

OUTPUT:
VISUAL_SCENE
SEMANTIC_VISUAL_CONTEXT
VISUAL_MACHINE_PAYLOAD
RENDERER_SAFE_VISUAL_STATE

THIS FILE IS:
- visual semantic coordinator
- renderer-oriented visual analyzer
- multimodal scene stabilizer
- provider coordination layer
- visual continuity system
- visual memory synchronization layer

THIS FILE IS NOT:
- telegram image handler
- user-facing response layer
- personality system
- renderer authority
- orchestration engine

GOLDEN APRIL PRINCIPLES:
- renderer-first architecture
- semantic continuity
- multimodal stability
- provider-safe execution
- no raw visual leakage
- scene continuity first
"""

# =====================================================
# 🔥 IMPORTS
# =====================================================

import os
import time
import json

from datetime import datetime

from google import genai
from openai import OpenAI

# =====================================================
# 🔥 PROVIDER ROUTER
# =====================================================

from blocks.provider_router import (

    provider_state,

    should_restore_gemini,

    mark_gemini_failure,

    mark_gemini_success,

    provider_log
)

# =====================================================
# 🔥 FILE ID
# =====================================================

APRIL_FILE_ID = (
    "APRIL_VISUAL_SEMANTIC_ORCHESTRATOR_CORE"
)

# =====================================================
# 🔥 PROVIDERS
# =====================================================

gemini_client = genai.Client(

    api_key=os.getenv(
        "GEMINI_API_KEY"
    )
)

openai_client = OpenAI(

    api_key=os.getenv(
        "OPENAI_API_KEY"
    )
)

# =====================================================
# 🔥 ACTIVE VISUAL PROVIDER
# =====================================================

ACTIVE_PROVIDER = "gemini"

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

INPUT_MACHINE_CHANNEL = {

    "source":
        "executor",

    "type":
        "visual_machine_input",

    "isolated":
        True
}

OUTPUT_MACHINE_CHANNEL = {

    "target":
        "executor_visual_pipeline",

    "type":
        "visual_machine_output",

    "isolated":
        True
}

# =====================================================
# 🔥 MACHINE LOGGING
# =====================================================

def build_visual_input_log():

    """
    INPUT MACHINE TRACE
    """

    return {

        "file_id":
            APRIL_FILE_ID,

        "event":
            "visual_input",

        "channel":
            INPUT_MACHINE_CHANNEL,

        "provider":
            ACTIVE_PROVIDER,

        "timestamp":
            datetime.utcnow().isoformat(),

        "machine_only":
            True
    }


def build_visual_output_log(
    scene_type,
    provider
):

    """
    OUTPUT MACHINE TRACE
    """

    return {

        "file_id":
            APRIL_FILE_ID,

        "event":
            "visual_output",

        "channel":
            OUTPUT_MACHINE_CHANNEL,

        "scene_type":
            scene_type,

        "provider":
            provider,

        "timestamp":
            datetime.utcnow().isoformat(),

        "machine_only":
            True
    }

# =====================================================
# 🔥 VISUAL MEMORY CONFIG
# =====================================================

MAX_OBJECTS = 12

MAX_VISIBLE_TEXT = 10

MAX_SCENE_SUMMARY = 1200

MAX_TASK_SUMMARY = 800

MAX_CONTINUITY_SUMMARY = 600

MAX_PASSIVE_SCENES = 6

# =====================================================
# 🔥 PROVIDER SWITCHING
# =====================================================

def set_provider(
    name: str
):

    global ACTIVE_PROVIDER

    ACTIVE_PROVIDER = name

    provider_log(

        f"🧠 VISUAL PROVIDER: "

        f"{ACTIVE_PROVIDER}"
    )

# =====================================================
# 🔥 PROVIDER GETTER
# =====================================================

def get_provider():

    return ACTIVE_PROVIDER

# =====================================================
# 🔥 PROVIDER RECOVERY
# =====================================================

def can_try_gemini():

    if ACTIVE_PROVIDER == "gemini":

        return should_restore_gemini()

    return False

# =====================================================
# 🔥 MACHINE VISUAL PAYLOAD
# =====================================================

def build_visual_machine_payload(
    visual_scene: dict
):

    """
    Renderer-safe machine payload.
    """

    return {

        "file_id":
            APRIL_FILE_ID,

        "channel":
            OUTPUT_MACHINE_CHANNEL,

        "machine_only":
            True,

        "human_visible":
            False,

        "scene":
            visual_scene,

        "provider":
            ACTIVE_PROVIDER,

        "visual_pipeline_active":
            True,

        "continuity_safe":
            True
    }

# =====================================================
# 🔥 VISUAL SCENE NORMALIZATION
# =====================================================

def normalize_visual_scene(
    raw_scene: dict
):

    """
    Safe visual normalization layer.
    """

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
        # =================================================
        # 🔥 TASK CONTEXT
        # =====================================================

        "task_context": {

            "task_type":

                raw_scene.get(
                    "task_type",
                    ""
                ),

            "problem_detected":

                raw_scene.get(
                    "problem_detected",
                    ""
                ),

            "goal":

                raw_scene.get(
                    "goal",
                    ""
                ),

            "current_step":

                raw_scene.get(
                    "current_step",
                    ""
                ),

            "next_expected_step":

                raw_scene.get(
                    "next_expected_step",
                    ""
                ),

            "resolution_status":

                raw_scene.get(
                    "resolution_status",
                    ""
                )
        },

        # =================================================
        # 🔥 CONTINUITY CONTEXT
        # =====================================================

        "continuity_context": {

            "topic_signature":

                raw_scene.get(
                    "topic_signature",
                    ""
                ),

            "scene_hash":

                raw_scene.get(
                    "scene_hash",
                    ""
                ),

            "related_previous_scene":

                raw_scene.get(
                    "related_previous_scene",
                    False
                ),

            "is_followup_candidate":

                raw_scene.get(
                    "is_followup_candidate",
                    False
                )
        },

        # =================================================
        # 🔥 MEMORY ANCHOR
        # =====================================================

        "memory_anchor": {

            "topic":

                raw_scene.get(
                    "topic",
                    ""
                ),

            "focus":

                raw_scene.get(
                    "focus",
                    ""
                ),

            "object":

                raw_scene.get(
                    "object",
                    ""
                ),

            "intent":

                raw_scene.get(
                    "intent",
                    ""
                )
        },

        # =================================================
        # 🔥 CORE SEMANTICS
        # =====================================================

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

        # =================================================
        # 🔥 OBJECTS
        # =====================================================

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

        # =================================================
        # 🔥 CONTINUITY
        # =====================================================

        "continuity_active":
            True,

        "scene_alive":
            True,

        "lifecycle_state":
            "ACTIVE",

        # =================================================
        # 🔥 PROVIDER
        # =====================================================

        "provider":
            ACTIVE_PROVIDER,

        "timestamp":
            time.time(),

        # =================================================
        # 🔥 MACHINE FLAGS
        # =====================================================

        "file_id":
            APRIL_FILE_ID,

        "machine_only":
            True,

        "human_visible":
            False
    }

    return normalized

# =====================================================
# 🔥 VISUAL SCENE COMPRESSION
# =====================================================

def compress_visual_scene(
    scene: dict
):

    """
    Passive continuity compression.
    """

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

        "task_context":

            scene.get(
                "task_context",
                {}
            ),

        "continuity_context":

            scene.get(
                "continuity_context",
                {}
            ),

        "memory_anchor":

            scene.get(
                "memory_anchor",
                {}
            ),

        "lifecycle_state":
            "PASSIVE",

        "machine_only":
            True
    }

# =====================================================
# 🔥 VISUAL MEMORY UPDATE
# =====================================================

def update_visual_memory(
    state: dict,
    visual_scene: dict
):

    """
    Visual continuity synchronization.
    """

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
    # 🔥 ARCHIVE PREVIOUS SCENE
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
    # 🔥 STORE ACTIVE SCENE
    # =====================================================

    state[
        "active_visual_scene"
    ] = visual_scene

    state[
        "passive_visual_memory"
    ] = passive_memory

    # =================================================
    # 🔥 EXECUTOR SYNCHRONIZATION
    # =====================================================

    scene_state = state.get(
        "scene_state",
        {}
    )

    scene_state[
        "visual_mode"
    ] = True

    scene_state[
        "visual_continuity"
    ] = True

    scene_state[
        "active_visual_provider"
    ] = ACTIVE_PROVIDER

    scene_state[
        "visual_orchestrator_active"
    ] = True

    state[
        "scene_state"
    ] = scene_state

# =====================================================
# 🔥 GEMINI VISUAL ANALYSIS
# =====================================================

async def analyze_with_gemini(
    path: str
):

    """
    Primary Gemini semantic analysis.
    """

    provider_log(
        "🧠 GEMINI VISUAL START"
    )

    uploaded_file = (

        gemini_client.files.upload(
            file=path
        )
    )

    response = (

        gemini_client.models.generate_content(

            model="gemini-2.5-flash",

            contents=[

                uploaded_file,

                """
Extract semantic visual scene.

Return ONLY JSON.

No markdown.
No explanations.
No human response.

Required structure:

{
  "scene_type": "",
  "semantic_focus": "",
  "summary": "",

  "task_type": "",
  "problem_detected": "",
  "goal": "",
  "current_step": "",
  "next_expected_step": "",
  "resolution_status": "",

  "topic_signature": "",
  "scene_hash": "",

  "related_previous_scene": false,
  "is_followup_candidate": false,

  "topic": "",
  "focus": "",
  "object": "",
  "intent": "",

  "objects": [],
  "visible_text": [],
  "colors": [],
  "brands": [],
  "positions": [],

  "environment": {}
}
"""
            ]
        )
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

            "scene_type":
                "unknown",

            "semantic_focus":
                "general",

            "summary":
                raw_text[:220],

            "objects":
                []
        }

    mark_gemini_success()

    provider_log(
        "🧠 GEMINI SUCCESS"
    )

    normalized = normalize_visual_scene(
        parsed
    )

    build_visual_output_log(
        normalized.get(
            "scene_type",
            "unknown"
        ),
        "gemini"
    )

    return normalized

# =====================================================
# 🔥 OPENAI FALLBACK
# =====================================================

async def analyze_with_openai(
    path: str
):

    """
    OpenAI fallback analysis.
    """

    provider_log(
        "⚠️ OPENAI VISUAL FALLBACK"
    )

    with open(path, "rb") as image_file:

        image_bytes = image_file.read()

    response = (

        openai_client.responses.create(

            model="gpt-4.1-mini",

            input=[

                {
                    "role": "user",

                    "content": [

                        {
                            "type":
                                "input_text",

                            "text": """
Extract semantic visual scene.

Detect:

- task_type
- problem_detected
- goal
- current_step
- next_expected_step
- resolution_status

- topic_signature
- scene_hash

- related_previous_scene
- is_followup_candidate

- topic
- focus
- object
- intent

Return ONLY JSON.
"""
                        },

                        {
                            "type":
                                "input_image",

                            "image_data":
                                image_bytes
                        }
                    ]
                }
            ]
        )
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

            "scene_type":
                "unknown",

            "semantic_focus":
                "general",

            "summary":
                raw_text[:220],

            "objects":
                []
        }

    provider_log(
        "🧠 OPENAI SUCCESS"
    )

    normalized = normalize_visual_scene(
        parsed
    )

    build_visual_output_log(
        normalized.get(
            "scene_type",
            "unknown"
        ),
        "openai"
    )

    return normalized

# =====================================================
# 🔥 MAIN VISUAL EXECUTION
# =====================================================

async def analyze_image_gemini(

    path: str,
    state: dict = None

):

    """
    Main visual semantic execution pipeline.
    """

    global ACTIVE_PROVIDER

    state = state or {}

    build_visual_input_log()

    try:

        # =================================================
        # 🔥 GEMINI PRIMARY
        # =====================================================

        if can_try_gemini():

            try:

                visual_scene = (

                    await analyze_with_gemini(
                        path
                    )
                )

                update_visual_memory(

                    state,
                    visual_scene
                )

                machine_payload = (

                    build_visual_machine_payload(
                        visual_scene
                    )
                )

                state[
                    "_visual_machine_payload"
                ] = machine_payload

                return visual_scene

            except Exception as gemini_error:

                provider_log(
                    "🔥 GEMINI ERROR"
                )

                provider_log(
                    gemini_error
                )

                mark_gemini_failure()

                set_provider(
                    "openai"
                )

        # =================================================
        # 🔥 OPENAI FALLBACK
        # =====================================================

        visual_scene = (

            await analyze_with_openai(
                path
            )
        )

        update_visual_memory(

            state,
            visual_scene
        )

        machine_payload = (

            build_visual_machine_payload(
                visual_scene
            )
        )

        state[
            "_visual_machine_payload"
        ] = machine_payload

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
            "🔥 VISUAL SYSTEM ERROR"
        )

        provider_log(e)

        build_visual_output_log(
            "error",
            ACTIVE_PROVIDER
        )

        return {

            "scene_type":
                "error",

            "semantic_focus":
                "error",

            "summary":
                "visual analysis failed",

            "objects":
                [],

            "continuity_active":
                False,

            "file_id":
                APRIL_FILE_ID,

            "machine_only":
                True
        }
