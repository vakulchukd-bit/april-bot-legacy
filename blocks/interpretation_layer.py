# =====================================================
# 🧠 APRIL INTERPRETATION LAYER
# =====================================================

"""
APRIL SEMANTIC INTERPRETATION LAYER

Этот слой:
- НЕ command router;
- НЕ execution engine;
- НЕ fallback trigger.

Interpretation layer теперь:
- semantic hint system;
- lightweight intention detector;
- continuity-aware interpreter;
- cognition-assisted interpretation layer;
- renderer-aware semantic adapter.

ВАЖНО:

Этот слой НЕ:
- навязывает execution;
- НЕ генерирует prompts;
- НЕ вызывает generation;
- НЕ ломает orchestration;
- НЕ force routing;
- НЕ принимает решения вместо cognition.

Он только:
- помогает semantic_core;
- помогает cognition;
- стабилизирует semantic continuity;
- подготавливает безопасные semantic hints;
- помогает executor понять тип сцены.
"""

# =====================================================
# 🔥 HELPERS
# =====================================================

def contains_any(
    text,
    words
):

    return any(
        w in text
        for w in words
    )


# =====================================================
# 🔥 SAFE NORMALIZATION
# =====================================================

def normalize_text(
    text: str
):

    return (
        text or ""
    ).strip()


# =====================================================
# 🔥 SAFE LOWER
# =====================================================

def normalize_lower(
    text: str
):

    return normalize_text(
        text
    ).lower()


# =====================================================
# 🔥 SEMANTIC GROUPS
# =====================================================

MATH_WORDS = [

    "график",
    "функция",
    "формула",
    "уравнение",
    "парабола",
    "синус",
    "косинус",
    "тангенс",

    "y=",
    "f(x)",
    "^2",
    "^3",
    "sin(",
    "cos(",
    "tan("
]

RENDERER_WORDS = [

    "график",
    "формула",
    "таблица",
    "сетка",
    "grid",
    "layout",
    "diagram",
    "схема",
    "line",
    "линия",
    "стрелка",
    "renderer",
    "render",
    "canvas",
    "scene",
    "пространство",
    "блок"
]

LIGHTWEIGHT_VISUAL_WORDS = [

    "пример",
    "идея",
    "вариант",
    "референс",
    "концепт",
    "атмосфера",
    "как выглядит",
    "примерно"
]

EXPLICIT_IMAGE_WORDS = [

    "создай изображение",
    "сгенерируй изображение",
    "нарисуй картинку",
    "создай арт",
    "draw image",
    "generate image",
    "сделай арт"
]

EXPLORATION_WORDS = [

    "идея",
    "вариант",
    "примерно",
    "атмосфера",
    "может",
    "посмотрим",
    "подумаем",
    "как думаешь"
]

CONTINUATION_WORDS = [

    "дальше",
    "продолжим",
    "теперь",
    "еще",
    "вернемся",
    "это",
    "этот",
    "эта",
    "снова"
]

WEB_WORDS = [

    "погода",
    "новости",
    "курс",
    "сейчас",
    "где находится",
    "маршрут",
    "рейс",
    "карта",
    "такси",
    "отель",
    "локация",
    "навигация"
]

CODE_WORDS = [

    "код",
    "кнопка",
    "анимация",
    "html",
    "css",
    "javascript",
    "python",
    "react",
    "api",
    "функция"
]

INFORMATIONAL_WORDS = [

    "информация",
    "данные",
    "расскажи",
    "объясни",
    "почему",
    "как работает",
    "что происходит",
    "можешь помочь",
    "что можешь сказать"
]


# =====================================================
# 🔥 SAFE DETECTORS
# =====================================================

def detect_math_expression(
    text
):

    return contains_any(
        normalize_lower(text),
        MATH_WORDS
    )


def detect_renderer_intent(
    text
):

    return contains_any(
        normalize_lower(text),
        RENDERER_WORDS
    )


def detect_lightweight_visual(
    text
):

    return contains_any(
        normalize_lower(text),
        LIGHTWEIGHT_VISUAL_WORDS
    )


def detect_explicit_image_generation(
    text
):

    return contains_any(
        normalize_lower(text),
        EXPLICIT_IMAGE_WORDS
    )


def detect_exploration(
    text
):

    return contains_any(
        normalize_lower(text),
        EXPLORATION_WORDS
    )


def detect_continuation(
    text
):

    return contains_any(
        normalize_lower(text),
        CONTINUATION_WORDS
    )


def detect_web_context(
    text
):

    return contains_any(
        normalize_lower(text),
        WEB_WORDS
    )


def detect_code_request(
    text
):

    return contains_any(
        normalize_lower(text),
        CODE_WORDS
    )


def detect_informational_request(
    text
):

    return contains_any(
        normalize_lower(text),
        INFORMATIONAL_WORDS
    )


# =====================================================
# 🔥 SCENE UNDERSTANDING
# =====================================================

def detect_scene_type(
    text,
    cognition=None
):

    cognition = cognition or {}

    lower = normalize_lower(
        text
    )

    # =================================================
    # 🔥 COGNITION PRIORITY
    # =====================================================

    if cognition.get(
        "prefer_renderer"
    ):

        if (
            "график" in lower
            or "plot" in lower
            or "graph" in lower
        ):

            return "graph"

        if (
            "формула" in lower
            or "equation" in lower
        ):

            return "formula"

        if (
            "таблица" in lower
            or "table" in lower
        ):

            return "table"

        return "scene"

    # =================================================
    # 🔥 SAFE SEMANTIC FALLBACK
    # =====================================================

    if detect_renderer_intent(
        lower
    ):

        if (
            "график" in lower
            or "plot" in lower
            or "graph" in lower
        ):

            return "graph"

        if (
            "формула" in lower
            or "equation" in lower
        ):

            return "formula"

        if (
            "таблица" in lower
            or "table" in lower
        ):

            return "table"

        return "scene"

    return None


# =====================================================
# 🔥 MAIN INTERPRETER
# =====================================================

def interpret_request(
    text: str,
    cognition: dict = None,
    semantic: dict = None
):

    text = normalize_text(
        text
    )

    cognition = cognition or {}

    semantic = semantic or {}

    if not text:

        return None

    t = normalize_lower(
        text
    )

    # =====================================================
    # 🔥 BASE RESULT
    # =====================================================

    result = {

        # =================================================
        # 🔥 CORE
        # =====================================================

        "type": "text",

        "subtype": None,

        "scene_type": None,

        "normalized": text,

        # =================================================
        # 🔥 SEMANTIC HINTS
        # =====================================================

        "renderer_intent": False,

        "lightweight_visual": False,

        "exploration": False,

        "continuation": False,

        "web_context": False,

        "explicit_image_generation": False,

        # =================================================
        # 🔥 COGNITION COOPERATION
        # =====================================================

        "cognition_assisted": True,

        "continuity_aware": True,

        "scene_aware": True,

        "supports_executor": True,

        # =================================================
        # 🔥 ORCHESTRATION
        # =====================================================

        "prefer_renderer": False,

        "prefer_guidance": False,

        "prefer_execution": False,

        "prefer_continuation": False,

        # =================================================
        # 🔥 SAFETY
        # =====================================================

        "avoid_force_generation": True,

        "avoid_hidden_escalation": True,

        "avoid_telegram_behavior": True,

        "avoid_trigger_execution": True,

        "provider_safe": True,

        "renderer_first": True
    }

    # =====================================================
    # 🔥 CONTINUATION
    # =====================================================

    if (
        detect_continuation(t)
        or cognition.get(
            "needs_continuation"
        )
    ):

        result[
            "continuation"
        ] = True

        result[
            "prefer_continuation"
        ] = True

    # =====================================================
    # 🔥 EXPLORATION
    # =====================================================

    if (
        detect_exploration(t)
        or cognition.get(
            "exploration_mode"
        )
    ):

        result[
            "exploration"
        ] = True

        result[
            "lightweight_visual"
        ] = True

    # =====================================================
    # 🔥 WEB
    # =====================================================

    if (
        detect_web_context(t)
        or cognition.get(
            "internet_context_needed"
        )
    ):

        result[
            "web_context"
        ] = True

        result[
            "prefer_guidance"
        ] = True

        result[
            "subtype"
        ] = "web"

    # =====================================================
    # 🔥 IMAGE GENERATION
    # =====================================================

    if detect_explicit_image_generation(
        t
    ):

        result[
            "type"
        ] = "image"

        result[
            "subtype"
        ] = "generation"

        result[
            "explicit_image_generation"
        ] = True

    # =====================================================
    # 🔥 COGNITION-FIRST RENDERER
    # =====================================================

    elif (

        cognition.get(
            "prefer_renderer"
        )

        or cognition.get(
            "renderer_space_active"
        )

        or detect_renderer_intent(
            t
        )
    ):

        result[
            "renderer_intent"
        ] = True

        result[
            "prefer_renderer"
        ] = True

        result[
            "type"
        ] = "render"

        scene_type = detect_scene_type(
            t,
            cognition
        )

        result[
            "scene_type"
        ] = scene_type

        result[
            "subtype"
        ] = scene_type

    # =====================================================
    # 🔥 MATH
    # =====================================================

    elif (

        detect_math_expression(
            t
        )

        or cognition.get(
            "math_reasoning"
        )
    ):

        result[
            "type"
        ] = "math"

        result[
            "subtype"
        ] = "graph"

        result[
            "renderer_intent"
        ] = True

        result[
            "prefer_renderer"
        ] = True

    # =====================================================
    # 🔥 CODE
    # =====================================================

    elif detect_code_request(
        t
    ):

        result[
            "type"
        ] = "code"

        result[
            "subtype"
        ] = "implementation"

        result[
            "prefer_execution"
        ] = True

    # =====================================================
    # 🔥 INFORMATIONAL
    # =====================================================

    elif (

        detect_informational_request(
            t
        )

        or cognition.get(
            "needs_guidance"
        )
    ):

        result[
            "type"
        ] = "text"

        result[
            "subtype"
        ] = "guidance"

        result[
            "prefer_guidance"
        ] = True

    # =====================================================
    # 🔥 LIGHTWEIGHT VISUALS
    # =====================================================

    if (
        detect_lightweight_visual(
            t
        )

        or cognition.get(
            "visual_reference_mode"
        )
    ):

        result[
            "lightweight_visual"
        ] = True

    # =====================================================
    # 🔥 CONTINUITY STABILIZATION
    # =====================================================

    if cognition.get(
        "tracks_multiple_topics"
    ):

        result[
            "continuity_aware"
        ] = True

    if cognition.get(
        "avoid_topic_loss"
    ):

        result[
            "scene_aware"
        ] = True

    # =====================================================
    # 🔥 FINAL STABILIZATION
    # =====================================================

    if result.get(
        "prefer_renderer"
    ):

        result[
            "avoid_force_generation"
        ] = True

        result[
            "explicit_image_generation"
        ] = False

    # =====================================================
    # 🔥 EXECUTION STABILIZATION
    # =====================================================

    if cognition.get(
        "prefer_execution"
    ):

        result[
            "prefer_execution"
        ] = True

    # =====================================================
    # 🔥 FINAL
    # =====================================================

    return result
