# ==================== 🧠 APRIL LEGACY ROUTER ====================

"""
APRIL LEGACY COMPATIBILITY ROUTER

⚠️ IMPORTANT:
Этот router больше НЕ является главным мозгом April.

Главные authority системы теперь:
- semantic_core
- cognitive_core
- response_decision
- executor orchestration

Router теперь:
- compatibility helper;
- weak hypothesis layer;
- continuity-safe stabilizer;
- lightweight orchestration assistant.

Router НЕ:
- execution authority;
- hard trigger layer;
- recursive router;
- generation authority;
- telegram dispatcher.
"""

# =====================================================
# 🔥 MACHINE IDENTITY
# =====================================================

APRIL_FILE_ID = "APRIL_LEGACY_ROUTER"

ROUTER_MACHINE_CHANNEL = {

    "type": "legacy_router",

    "mode": "supportive",

    "authority": "soft",

    "continuity_safe": True,

    "web_safe": True,

    "renderer_first": True
}

# =====================================================
# 🔥 ROUTER CONTRACT
# =====================================================

def build_router_contract():

    return {

        "legacy_compatible":
            True,

        "execution_authority":
            False,

        "generation_authority":
            False,

        "renderer_authority":
            False,

        "hard_trigger_behavior":
            False,

        "continuity_first":
            True,

        "trajectory_safe":
            True,

        "web_oriented":
            True
    }

ROUTER_CONTRACT = build_router_contract()

# =====================================================
# 🔥 LOGGING
# =====================================================

ROUTER_PATCH_LOG = []

def safe_router_log(msg):

    try:

        print(
            "APRIL LEGACY ROUTER:",
            msg
        )

        ROUTER_PATCH_LOG.append(
            str(msg)
        )

    except:
        pass

safe_router_log(
    "LEGACY ROUTER INITIALIZED"
)

# =====================================================
# 🧠 SAFE HELPERS
# =====================================================

def normalize(text):

    return (
        text or ""
    ).lower().strip()


def contains_any(text, words):

    return any(
        w in text
        for w in words
    )

# =====================================================
# 🧠 NEGATION DETECTION
# =====================================================

def has_negation(text):

    negations = [

        "не надо",
        "не делай",
        "не нужно",
        "не хочу",
        "не генерируй",
        "не создавай"
    ]

    return contains_any(
        text,
        negations
    )

# =====================================================
# 🧠 EXPLORATION DETECTION
# =====================================================

def is_exploration(text):

    exploration_words = [

        "примерно",
        "может",
        "наверное",
        "идея",
        "атмосфера",
        "посмотрим",
        "подумаем",
        "направление",
        "что-то",
        "как будто",
        "не уверен",
        "вариант",
        "настроение"
    ]

    return contains_any(
        text,
        exploration_words
    )

# =====================================================
# 🧠 USER LEADS DETECTION
# =====================================================

def user_leads_direction(text):

    direction_words = [

        "вот",
        "в таком стиле",
        "ближе",
        "примерно так",
        "вот это",
        "атмосфера",
        "идея"
    ]

    return contains_any(
        text,
        direction_words
    )

# =====================================================
# 🧠 LIGHT VISUAL DETECTION
# =====================================================

def wants_visual_reference(text):

    visual_words = [

        "референс",
        "пример",
        "атмосфера",
        "визуально",
        "идея",
        "примерно",
        "стиль"
    ]

    return contains_any(
        text,
        visual_words
    )

# =====================================================
# 🧠 IMAGE GENERATION DETECTION
# =====================================================

def wants_real_generation(text):

    generation_words = [

        "сгенерируй",
        "создай изображение",
        "нарисуй",
        "сделай картинку",
        "покажи изображение"
    ]

    return contains_any(
        text,
        generation_words
    )

# =====================================================
# 🧠 SHORT CONTINUATION
# =====================================================

def is_short_continuation(text):

    continuation_words = [

        "да",
        "ага",
        "вот",
        "не то",
        "ближе",
        "примерно",
        "уже лучше",
        "не знаю",
        "ну вот"
    ]

    if len(text.split()) <= 3:

        if contains_any(
            text,
            continuation_words
        ):

            return True

    return False

# =====================================================
# 🧠 SAFE RESULT TEMPLATE
# =====================================================

def build_result():

    return {

        "action": "chat",

        "confidence": 0.5,

        "is_soft_decision": True,

        "trajectory_safe": True,

        "continuity_safe": True,

        "exploration_mode": False,

        "visual_guidance": False,

        "generation_allowed": False,

        "continuation_detected": False,

        "legacy_router": True,

        "hard_authority": False,

        "executor_override_allowed": True,

        "renderer_first": True,

        "web_safe": True
    }

# =====================================================
# 🧠 MAIN ROUTER
# =====================================================

def decide_action(
    text: str,
    history: list
):

    t = normalize(text)

    safe_router_log(
        f"INPUT: {t[:80]}"
    )

    # =================================================
    # 🔥 BASE RESULT
    # =====================================================

    result = build_result()

    # =================================================
    # 🔥 NEGATION
    # =====================================================

    if has_negation(t):

        result["action"] = "chat"

        result["confidence"] = 0.9

        return result

    # =================================================
    # 🔥 SHORT CONTINUATION
    # =====================================================

    if is_short_continuation(t):

        result["action"] = "continue"

        result[
            "continuation_detected"
        ] = True

        result["confidence"] = 0.85

        return result

    # =================================================
    # 🔥 EXPLORATION
    # =====================================================

    if is_exploration(t):

        result[
            "exploration_mode"
        ] = True

        result["action"] = "guide"

        result["confidence"] = 0.75

    # =================================================
    # 🔥 USER LEADS
    # =====================================================

    if user_leads_direction(t):

        result[
            "trajectory_safe"
        ] = True

        result[
            "exploration_mode"
        ] = True

        result["action"] = "guide"

        result["confidence"] = 0.8

    # =================================================
    # 🔥 VISUAL GUIDANCE
    # =====================================================

    if wants_visual_reference(t):

        result[
            "visual_guidance"
        ] = True

        result["action"] = "reference"

        result["confidence"] = 0.75

    # =================================================
    # 🔥 REAL GENERATION
    # =====================================================

    if wants_real_generation(t):

        # exploration suppresses generation

        if not result[
            "exploration_mode"
        ]:

            result[
                "generation_allowed"
            ] = True

            result["action"] = "image"

            result["confidence"] = 0.9

    # =================================================
    # 🔥 DIAGRAM
    # =====================================================

    diagram_words = [

        "чертеж",
        "чертёж",
        "схема",
        "диаграмма"
    ]

    if contains_any(
        t,
        diagram_words
    ):

        result["action"] = "diagram"

        result["confidence"] = 0.8

    # =================================================
    # 🔥 QUESTION
    # =====================================================

    question_words = [

        "что",
        "почему",
        "как",
        "зачем"
    ]

    if (

        "?" in t

        or contains_any(
            t,
            question_words
        )
    ):

        if result["action"] == "chat":

            result["confidence"] = 0.7

    # =================================================
    # 🔥 WEAK SHORT INPUT
    # =====================================================

    if len(t.split()) <= 2:

        if result["action"] == "chat":

            result["action"] = "continue"

            result["confidence"] = 0.55

            result[
                "continuation_detected"
            ] = True

    # =================================================
    # 🔥 FINAL SAFETY
    # =====================================================

    result[
        "executor_override_allowed"
    ] = True

    result[
        "hard_authority"
    ] = False

    result[
        "trajectory_safe"
    ] = True

    result[
        "continuity_safe"
    ] = True

    return result
