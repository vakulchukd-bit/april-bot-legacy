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
- renderer-aware assistant layer.

ВАЖНО:

Этот слой НЕ:
- навязывает execution;
- НЕ генерирует prompts;
- НЕ вызывает generation;
- НЕ ломает orchestration;
- НЕ force routing.

Он только:
- помогает semantic_core;
- добавляет semantic hints;
- stabilizes interpretation continuity.
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
# 🔥 MATH DETECTION
# =====================================================

def detect_math_expression(
    text
):

    t = text.lower()

    math_words = [

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

    return contains_any(
        t,
        math_words
    )


# =====================================================
# 🔥 RENDERER DETECTION
# =====================================================

def detect_renderer_intent(
    text
):

    t = text.lower()

    renderer_words = [

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

    return contains_any(
        t,
        renderer_words
    )


# =====================================================
# 🔥 LIGHTWEIGHT VISUALS
# =====================================================

def detect_lightweight_visual(
    text
):

    t = text.lower()

    lightweight_words = [

        "пример",
        "идея",
        "вариант",
        "референс",
        "концепт",
        "атмосфера",
        "как выглядит",
        "примерно"
    ]

    return contains_any(
        t,
        lightweight_words
    )


# =====================================================
# 🔥 EXPLICIT IMAGE GENERATION
# =====================================================

def detect_explicit_image_generation(
    text
):

    t = text.lower()

    generation_words = [

        "создай изображение",
        "сгенерируй изображение",
        "нарисуй картинку",
        "создай арт",
        "draw image",
        "generate image",
        "сделай арт"
    ]

    return contains_any(
        t,
        generation_words
    )


# =====================================================
# 🔥 EXPLORATION DETECTION
# =====================================================

def detect_exploration(
    text
):

    t = text.lower()

    exploration_words = [

        "идея",
        "вариант",
        "примерно",
        "атмосфера",
        "может",
        "посмотрим",
        "подумаем",
        "как думаешь"
    ]

    return contains_any(
        t,
        exploration_words
    )


# =====================================================
# 🔥 CONTINUATION DETECTION
# =====================================================

def detect_continuation(
    text
):

    t = text.lower()

    continuation_words = [

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

    return contains_any(
        t,
        continuation_words
    )


# =====================================================
# 🔥 WEB / REALTIME DETECTION
# =====================================================

def detect_web_context(
    text
):

    t = text.lower()

    web_words = [

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

    return contains_any(
        t,
        web_words
    )


# =====================================================
# 🔥 CODE DETECTION
# =====================================================

def detect_code_request(
    text
):

    t = text.lower()

    code_words = [

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

    return contains_any(
        t,
        code_words
    )


# =====================================================
# 🔥 INFORMATIONAL DETECTION
# =====================================================

def detect_informational_request(
    text
):

    t = text.lower()

    informational_words = [

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

    return contains_any(
        t,
        informational_words
    )


# =====================================================
# 🔥 MAIN INTERPRETER
# =====================================================

def interpret_request(
    text: str
):

    text = normalize_text(
        text
    )

    if not text:

        return None

    t = text.lower()

    # =====================================================
    # 🔥 BASE RESULT
    # =====================================================

    result = {

        # =================================================
        # 🔥 CORE
        # =====================================================

        "type": "text",

        "subtype": None,

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

        "provider_safe": True
    }

    # =====================================================
    # 🔥 CONTINUATION
    # =====================================================

    if detect_continuation(
        t
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

    if detect_exploration(
        t
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

    if detect_web_context(
        t
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
    # 🔥 EXPLICIT IMAGE GENERATION
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
    # 🔥 RENDERER-FIRST
    # =====================================================

    elif detect_renderer_intent(
        t
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

        # =================================================
        # 🔥 RENDER SUBTYPES
        # =====================================================

        if "график" in t:

            result[
                "subtype"
            ] = "graph"

        elif "формула" in t:

            result[
                "subtype"
            ] = "formula"

        elif "таблица" in t:

            result[
                "subtype"
            ] = "table"

        elif (
            "diagram" in t
            or "схема" in t
        ):

            result[
                "subtype"
            ] = "diagram"

        else:

            result[
                "subtype"
            ] = "scene"

    # =====================================================
    # 🔥 MATH
    # =====================================================

    elif detect_math_expression(
        t
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

    elif detect_informational_request(
        t
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

    if detect_lightweight_visual(
        t
    ):

        result[
            "lightweight_visual"
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
    # 🔥 FINAL
    # =====================================================

    return result
