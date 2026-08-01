print("🔥 MAIN IMAGE SYSTEM WORKING")

# =====================================================
# 🧠 APRIL IMAGE SYSTEM
# =====================================================

"""
APRIL IMAGE SYSTEM

APRIL_FILE_ID:
APRIL_IMAGE_SYSTEM_BRIDGE

ROLE:
VISUAL_PROVIDER_BRIDGE
VISUAL_CONTINUITY_COORDINATOR

INPUT:
IMAGE_PATH
VISUAL_STATE
PROVIDER_VISUAL_ANALYSIS

OUTPUT:
VISUAL_MEMORY
ACTIVE_VISUAL_SCENE
CONTINUITY_STATE
VISUAL_ANALYSIS_RESULT

=====================================================

Этот модуль больше НЕ:
- vision AI;
- OCR interpreter;
- trigger detector;
- scene classifier;
- fallback analyzer;
- keyword parser.

=====================================================

Этот модуль теперь:
- provider bridge;
- visual continuity layer;
- semantic scene memory;
- lightweight visual orchestrator;
- multimodal context synchronizer.

=====================================================

Главная архитектурная идея:

Gemini / OpenAI / future providers
ПОНИМАЮТ изображение.

April:
- сохраняет continuity;
- организует сцену;
- удерживает visual context;
- передаёт semantic understanding
  дальше в cognition / memory / dialogue.

=====================================================

APRIL PRINCIPLES:

1. providers understand
2. April orchestrates
3. no trigger hallucinations
4. no regex vision
5. no forced scene classification
6. continuity before interpretation
7. renderer-safe architecture
"""

from blocks.provider_router import (
    analyze_image as provider_analyze_image
)

# =====================================================
# 🔥 FILE ID
# =====================================================

APRIL_FILE_ID = (
    "APRIL_IMAGE_SYSTEM_BRIDGE"
)

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

INPUT_MACHINE_CHANNEL = {

    "source":
        "executor_visual_input",

    "type":
        "visual_analysis_request",

    "isolated":
        True
}

OUTPUT_MACHINE_CHANNEL = {

    "target":
        "executor_visual_memory",

    "type":
        "visual_analysis_result",

    "isolated":
        True
}

# =====================================================
# 🔥 MACHINE LOGS
# =====================================================

IMAGE_SYSTEM_LOGS = []

MAX_IMAGE_SYSTEM_LOGS = 50


def log_image_system_event(
    event,
    payload=None
):

    try:

        IMAGE_SYSTEM_LOGS.append({

            "file_id":
                APRIL_FILE_ID,

            "event":
                event,

            "payload":
                payload or {},

            "machine_only":
                True
        })

        if len(IMAGE_SYSTEM_LOGS) > MAX_IMAGE_SYSTEM_LOGS:

            IMAGE_SYSTEM_LOGS.pop(0)

    except:
        pass

# =====================================================
# 🔥 SAFE NORMALIZATION
# =====================================================

def normalize_text(
    text
):

    if text is None:
        return ""

    return str(text).strip()

# =====================================================
# 🔥 SAFE SUMMARY
# =====================================================

def build_visual_summary(
    analysis_text
):

    """
    Lightweight semantic summary.

    НЕ:
    - reinterpretation;
    - hallucination;
    - object guessing.

    ONLY:
    provider semantic preservation.
    """

    text = normalize_text(
        analysis_text
    )

    if not text:
        return ""

    return text[:1200]

# =====================================================
# 🔥 VISUAL MEMORY PACKAGE
# =====================================================

def build_visual_memory(
    analysis_text,
    provider="openai"
):

    """
    IMPORTANT:

    This is NOT scene interpretation.

    This is:
    semantic continuity packaging.

    Provider already understood image.
    April only organizes continuity.
    """

    text = normalize_text(
        analysis_text
    )

    summary = build_visual_summary(
        text
    )

    # =================================================
    # 🔥 CONTINUITY ESTIMATION
    # =====================================================

    continuity_weight = 0.72

    if len(summary) >= 200:
        continuity_weight += 0.08

    if len(summary) >= 500:
        continuity_weight += 0.05

    continuity_weight = min(
        continuity_weight,
        0.9
    )

    # =================================================
    # 🔥 RESULT
    # =====================================================

    visual_memory = {

        # =================================================
        # 🔥 CORE
        # =====================================================

        "summary":
            summary,

        "raw_analysis":
            text,

        # =================================================
        # 🔥 PROVIDER
        # =====================================================

        "provider":
            provider,

        "provider_driven":
            True,

        "semantic_source":
            provider,

        # =================================================
        # 🔥 CONTINUITY
        # =====================================================

        "continuity_weight":
            continuity_weight,

        "continuity_ready":
            True,

        "dialog_ready":
            True,

        "memory_ready":
            True,

        # =================================================
        # 🔥 APRIL WEB SPACE
        # =====================================================

        "renderer_compatible":
            True,

        "web_space_ready":
            True,

        "scene_oriented":
            True,

        # =================================================
        # 🔥 SAFETY
        # =====================================================

        "trigger_based":
            False,

        "hallucination_safe":
            True,

        "forced_scene_detection":
            False,

        "regex_vision":
            False,

        "lightweight_mode":
            True,

        # =================================================
        # 🔥 MACHINE
        # =====================================================

        "machine_only":
            True,

        "human_visible":
            False
    }

    log_image_system_event(

        "visual_memory_created",

        {
            "provider":
                provider,

            "continuity_weight":
                continuity_weight
        }
    )

    return visual_memory

# =====================================================
# 🔥 VISUAL HISTORY
# =====================================================

def update_visual_history(
    state,
    visual_memory
):

    history = state.get(
        "visual_scene_history",
        []
    )

    history.append(
        visual_memory
    )

    # =================================================
    # 🔥 CONTINUITY WINDOW
    # =====================================================

    if len(history) > 7:

        history = history[-7:]

    state[
        "visual_scene_history"
    ] = history

    log_image_system_event(

        "visual_history_updated",

        {
            "history_size":
                len(history)
        }
    )

    return history

# =====================================================
# 🔥 CACHE RESTORE
# =====================================================

def restore_visual_cache(
    state,
    path
):

    if not state:
        return None

    cached = state.get(
        "image_analysis"
    )

    cached_path = state.get(
        "image_analysis_path"
    )

    if (

        cached
        and cached_path == path

    ):

        print(
            "🧠 USING VISUAL CACHE"
        )

        log_image_system_event(
            "visual_cache_restored"
        )

        return cached

    return None

# =====================================================
# 🔥 PROVIDER ANALYSIS
# =====================================================

async def analyze_provider_image(
    path
):

    """
    Provider-aware bridge.

    Future-safe:
    Gemini / OpenAI / hybrid routing.
    """

    log_image_system_event(

        "provider_analysis_started",

        {
            "provider":
                "openai"
        }
    )

    result = await provider_analyze_image(
        path
    )

    log_image_system_event(

        "provider_analysis_completed",

        {
            "provider":
                "openai"
        }
    )

    return result

# =====================================================
# 🔥 MAIN ANALYZE IMAGE
# =====================================================

async def analyze_image(
    path: str,
    state=None
) -> str:

    try:

        print(
            "🧠 ANALYZE IMAGE START"
        )

        print(
            f"🧠 IMAGE PATH: {path}"
        )

        log_image_system_event(

            "analyze_image_started",

            {
                "path":
                    str(path)
            }
        )

        # =================================================
        # 🔥 CACHE
        # =====================================================

        cached = restore_visual_cache(
            state,
            path
        )

        if cached:

            log_image_system_event(
                "cache_hit"
            )

            return cached

        # =================================================
        # 🔥 PROVIDER ANALYSIS
        # =====================================================

        print(
            "🧠 PROVIDER ANALYSIS START"
        )

        result = await analyze_provider_image(
            path
        )

        # Normalize provider output to plain text
        if hasattr(result, "output_text"):
            result = result.output_text
        elif hasattr(result, "text"):
            result = result.text
        elif not isinstance(result, str):
            result = str(result)

        print(
            "🧠 PROVIDER ANALYSIS COMPLETE"
        )

        # =================================================
        # 🔥 EMPTY SAFETY
        # =====================================================

        if not result:

            log_image_system_event(
                "empty_provider_result"
            )

            return (
                "⚠️ Не получилось "
                "проанализировать изображение."
            )

        # =================================================
        # 🔥 BUILD VISUAL MEMORY
        # =====================================================

        visual_memory = build_visual_memory(
            result,
            provider="openai"
        )

        print(
            "🧠 VISUAL MEMORY CREATED"
        )

        # =================================================
        # 🔥 SAVE STATE
        # =====================================================

        if state is not None:

            # =================================================
            # 🔥 RAW PROVIDER RESULT
            # =====================================================

            state["image_analysis"] = (
                result
            )

            state["image_analysis_path"] = (
                path
            )

            # =================================================
            # 🔥 ACTIVE VISUAL CONTEXT
            # =====================================================

            state["active_visual_scene"] = (
                visual_memory
            )

            # =================================================
            # 🔥 CONTINUITY HISTORY
            # =====================================================

            update_visual_history(
                state,
                visual_memory
            )

            # =================================================
            # 🔥 LIGHTWEIGHT SNAPSHOT
            # =====================================================

            state[
                "last_visual_analysis"
            ] = {

                "summary":
                    visual_memory.get(
                        "summary"
                    ),

                "provider":
                    visual_memory.get(
                        "provider"
                    ),

                "continuity_weight":
                    visual_memory.get(
                        "continuity_weight"
                    )
            }

            print(
                "🧠 VISUAL STATE SAVED"
            )

            log_image_system_event(
                "visual_state_saved"
            )

        # =================================================
        # 🔥 COMPLETE
        # =====================================================

        print(
            "🧠 ANALYZE IMAGE COMPLETE"
        )

        log_image_system_event(
            "analyze_image_completed"
        )

        return result

    except Exception as e:

        print(
            f"🔥 IMAGE SYSTEM ERROR: {str(e)}"
        )

        log_image_system_event(

            "analyze_image_error",

            {
                "error":
                    str(e)
            }
        )

        return (
            "⚠️ Ошибка анализа изображения."
        )
