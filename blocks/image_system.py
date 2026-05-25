print("🔥 MAIN IMAGE SYSTEM WORKING")

from blocks.gemini_vision import (
    analyze_image_gemini
)

# =================================================
# 🧠 APRIL IMAGE SYSTEM
# =====================================================

"""
APRIL IMAGE SYSTEM — PROVIDER-AWARE
VISUAL CONTINUITY BRIDGE

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

# =================================================
# 🔥 SAFE NORMALIZATION
# =====================================================

def normalize_text(
    text
):

    if text is None:
        return ""

    return str(text).strip()


# =================================================
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


# =================================================
# 🔥 VISUAL MEMORY PACKAGE
# =====================================================

def build_visual_memory(
    analysis_text,
    provider="gemini"
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

    return {

        # =================================================
        # 🔥 CORE
        # =====================================================

        "summary": summary,

        "raw_analysis": text,

        # =================================================
        # 🔥 PROVIDER
        # =====================================================

        "provider": provider,

        "provider_driven": True,

        "semantic_source": provider,

        # =================================================
        # 🔥 CONTINUITY
        # =====================================================

        "continuity_weight":
            continuity_weight,

        "continuity_ready": True,

        "dialog_ready": True,

        "memory_ready": True,

        # =================================================
        # 🔥 APRIL WEB SPACE
        # =====================================================

        "renderer_compatible": True,

        "web_space_ready": True,

        "scene_oriented": True,

        # =================================================
        # 🔥 SAFETY
        # =====================================================

        "trigger_based": False,

        "hallucination_safe": True,

        "forced_scene_detection": False,

        "regex_vision": False,

        "lightweight_mode": True
    }


# =================================================
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

    return history


# =================================================
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

        return cached

    return None


# =================================================
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

    return await analyze_image_gemini(
        path
    )


# =================================================
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

        # =================================================
        # 🔥 CACHE
        # =====================================================

        cached = restore_visual_cache(
            state,
            path
        )

        if cached:

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

        print(
            "🧠 PROVIDER ANALYSIS COMPLETE"
        )

        # =================================================
        # 🔥 EMPTY SAFETY
        # =====================================================

        if not result:

            return (
                "⚠️ Не получилось "
                "проанализировать изображение."
            )

        # =================================================
        # 🔥 BUILD VISUAL MEMORY
        # =====================================================

        visual_memory = build_visual_memory(
            result,
            provider="gemini"
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

        # =================================================
        # 🔥 COMPLETE
        # =====================================================

        print(
            "🧠 ANALYZE IMAGE COMPLETE"
        )

        return result

    except Exception as e:

        print(
            f"🔥 IMAGE SYSTEM ERROR: {str(e)}"
        )

        return (
            "⚠️ Ошибка анализа изображения."
        )
