# ==================== 🧠 ROUTER SYSTEM ====================

"""
Legacy compatibility router.

⚠️ IMPORTANT:
Этот router больше НЕ является главным мозгом April.

Главные authority системы теперь:
- semantic_core
- cognitive_core
- response_decision
- executor orchestration

Router теперь:
- помогает legacy совместимости;
- даёт weak hypotheses;
- НЕ должен ломать trajectory;
- НЕ должен делать hard trigger behavior.
"""

# =====================================================
# 🧠 SAFE HELPERS
# =====================================================

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
# 🧠 LIGHT IMAGE DETECTION
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
# 🧠 IMAGE EXECUTION DETECTION
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
# 🧠 MAIN ROUTER
# =====================================================

def decide_action(
    text: str,
    history: list
):

    t = text.lower().strip()

    # =================================================
    # 🔥 BASE RESULT
    # =================================================

    result = {

        "action": "chat",

        "confidence": 0.5,

        "is_soft_decision": True,

        "trajectory_safe": True,

        "exploration_mode": False,

        "visual_guidance": False,

        "generation_allowed": False,

        "continuation_detected": False
    }

    # =================================================
    # 🔥 NEGATION
    # =================================================

    if has_negation(t):

        result["action"] = "chat"

        result["confidence"] = 0.9

        return result

    # =================================================
    # 🔥 SHORT CONTINUATION
    # =================================================

    if is_short_continuation(t):

        result["action"] = "continue"

        result["continuation_detected"] = True

        result["confidence"] = 0.85

        return result

    # =================================================
    # 🔥 EXPLORATION MODE
    # =================================================

    if is_exploration(t):

        result["exploration_mode"] = True

        result["action"] = "guide"

        result["confidence"] = 0.75

    # =================================================
    # 🔥 USER LEADS
    # =================================================

    if user_leads_direction(t):

        result["trajectory_safe"] = True

        result["exploration_mode"] = True

        result["action"] = "guide"

        result["confidence"] = 0.8

    # =================================================
    # 🔥 VISUAL GUIDANCE
    # =================================================

    if wants_visual_reference(t):

        result["visual_guidance"] = True

        result["action"] = "reference"

        result["confidence"] = 0.75

    # =================================================
    # 🔥 REAL GENERATION
    # =================================================

    if wants_real_generation(t):

        # ⚠️ exploration suppresses generation
        if not result["exploration_mode"]:

            result["generation_allowed"] = True

            result["action"] = "image"

            result["confidence"] = 0.9

    # =================================================
    # 🔥 DIAGRAM
    # =================================================

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
    # =================================================

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
    # =================================================

    if len(t.split()) <= 2:

        # ⚠️ больше НЕ forcing clarify

        if result["action"] == "chat":

            result["action"] = "continue"

            result["confidence"] = 0.55

            result[
                "continuation_detected"
            ] = True

    # =================================================
    # 🔥 FINAL SAFETY
    # =================================================

    # Router больше НЕ имеет hard authority.
    # Executor / cognition / response_decision
    # могут полностью переопределить router result.

    result["legacy_router"] = True

    result["hard_authority"] = False

    result["executor_override_allowed"] = True

    return result
