# =====================================================
# 🧠 VISUAL REFERENCE SYSTEM
# =====================================================

"""
APRIL VISUAL REFERENCE SYSTEM

Visual system больше НЕ:
- aggressive generation trigger;
- forced image escalation;
- telegram-style visual helper;
- standalone image authority.

Visual system теперь:
- renderer-aware support layer;
- lightweight semantic guidance;
- atmosphere continuity helper;
- exploration-safe visual assistant.

Главная цель:
поддерживать понимание пространства,
а не форсить image generation.
"""

# =====================================================
# 🧠 HELPERS
# =====================================================

def normalize(
    text: str
):

    return (
        text or ""
    ).lower().strip()


def contains_any(
    text: str,
    words: list
):

    return any(
        w in text
        for w in words
    )


# =====================================================
# 🧠 MAIN
# =====================================================

def build_visual_reference(
    semantic: dict,
    cognition: dict,
    text: str,
    state: dict
):

    t = normalize(text)

    active_flow = state.get(
        "active_flow"
    )

    active_visual_scene = state.get(
        "active_visual_scene"
    )

    reasoning = state.get(
        "reasoning",
        {}
    )

    # =================================================
    # 🧠 BASE
    # =====================================================

    result = {

        # =================================================
        # CORE
        # =================================================

        "enabled": False,

        "mode": None,

        "references": [],

        # =================================================
        # GENERATION
        # =================================================

        "should_generate": False,

        "suppress_generation": False,

        "generation_allowed": False,

        # =================================================
        # LIGHTWEIGHT
        # =================================================

        "lightweight_mode": False,

        "renderer_mode": True,

        "reference_priority": False,

        # =================================================
        # CONTINUITY
        # =================================================

        "trajectory_aligned": True,

        "dialogue_centered": True,

        "visual_should_continue_dialogue": True,

        "visual_should_not_interrupt": True,

        "visual_continuity": False,

        # =================================================
        # SUPPORT
        # =================================================

        "support_level": 0.0,

        "reference_confidence": 0.0,

        "direction_detected": False,

        "guidance": None,

        # =================================================
        # STYLE
        # =================================================

        "response_style": "guidance",

        "emotion": None,

        "atmosphere": None,

        # =================================================
        # SAFETY
        # =================================================

        "visual_is_supportive": True,

        "visual_requires_context": True,

        "visual_requires_meaning": True,

        "visual_is_not_random": True,

        "capability_awareness": True,

        "provider_aware": True,

        "avoid_heavy_generation": True
    }

    # =================================================
    # 🧠 STATE
    # =====================================================

    dialog_state = semantic.get(
        "dialog_state",
        "exploration"
    )

    ambiguity = semantic.get(
        "ambiguity_level",
        0.0
    )

    unresolved_intent = reasoning.get(
        "unresolved_intent",
        True
    )

    visual_expectation = semantic.get(
        "visual_expectation",
        0.0
    )

    example_expectation = semantic.get(
        "example_expectation",
        0.0
    )

    # =================================================
    # 🧠 VISUAL CONTINUITY
    # =====================================================

    if active_visual_scene:

        result[
            "visual_continuity"
        ] = True

        result[
            "trajectory_aligned"
        ] = True

        result[
            "dialogue_centered"
        ] = True

        result[
            "support_level"
        ] += 0.25

    # =================================================
    # 🧠 EXPLORATION
    # =====================================================

    exploration_words = [

        "примерно",
        "что-то",
        "не знаю",
        "как будто",
        "наверное",
        "атмосфера",
        "идея",
        "направление",
        "вариант",
        "референс",
        "пример"
    ]

    if contains_any(
        t,
        exploration_words
    ):

        result["enabled"] = True

        result["mode"] = "exploration"

        result["lightweight_mode"] = True

        result["reference_priority"] = True

        result["suppress_generation"] = True

        result["support_level"] += 0.45

        result["response_style"] = (
            "soft_guidance"
        )

    # =================================================
    # 🧠 SEMANTIC VISUAL SIGNALS
    # =====================================================

    if visual_expectation >= 0.45:

        result["enabled"] = True

        result["support_level"] += 0.25

    if example_expectation >= 0.45:

        result["enabled"] = True

        result["reference_priority"] = True

        result["support_level"] += 0.25

    # =================================================
    # 🧠 COGNITION EXPLORATION
    # =====================================================

    if cognition.get(
        "exploration_mode"
    ):

        result["enabled"] = True

        result["lightweight_mode"] = True

        result["reference_priority"] = True

        result["suppress_generation"] = True

        result["response_style"] = (
            "soft_guidance"
        )

    # =================================================
    # 🧠 USER LEADS
    # =====================================================

    if cognition.get(
        "user_leads_direction"
    ):

        result[
            "direction_detected"
        ] = True

        result[
            "reference_priority"
        ] = True

        result[
            "lightweight_mode"
        ] = True

        result[
            "suppress_generation"
        ] = True

    # =================================================
    # 🧠 DIALOG SAFETY
    # =====================================================

    if (

        dialog_state == "exploration"

        or ambiguity >= 0.45

        or unresolved_intent
    ):

        result[
            "lightweight_mode"
        ] = True

        result[
            "suppress_generation"
        ] = True

    # =================================================
    # 🧠 SCREENSHOT MODE
    # =====================================================

    screenshot_words = [

        "скрин",
        "скриншот",
        "screenshot"
    ]

    if contains_any(
        t,
        screenshot_words
    ):

        result["enabled"] = True

        result["mode"] = (
            "context_support"
        )

        result["lightweight_mode"] = True

        result["reference_priority"] = True

        result["suppress_generation"] = True

        result["guidance"] = (

            "Скриншот лучше использовать "
            "как часть понимания ситуации "
            "и continuity разговора."
        )

    # =================================================
    # 🧠 ATMOSPHERE
    # =====================================================

    cozy_words = [

        "уют",
        "кофейня",
        "тепло",
        "вечером",
        "лампы",
        "атмосфера",
        "мягкий свет"
    ]

    if contains_any(
        t,
        cozy_words
    ):

        result["enabled"] = True

        result["mode"] = "atmosphere"

        result["emotion"] = "cozy"

        result["atmosphere"] = (
            "warm_calm"
        )

        result[
            "reference_confidence"
        ] += 0.82

        result["support_level"] += 0.5

        result["direction_detected"] = True

        result["references"] = [

            {
                "type": "mood",
                "title":
                    "Тёплый локальный свет",
                "weight": 0.95
            },

            {
                "type": "lighting",
                "title":
                    "Мягкое вечернее освещение",
                "weight": 0.9
            },

            {
                "type": "style",
                "title":
                    "Спокойный уютный minimal",
                "weight": 0.88
            }
        ]

    # =================================================
    # 🧠 CYBERPUNK
    # =====================================================

    cyberpunk_words = [

        "неон",
        "киберпанк",
        "cyberpunk",
        "футуризм",
        "ночной город"
    ]

    if contains_any(
        t,
        cyberpunk_words
    ):

        result["enabled"] = True

        result["mode"] = "cyberpunk"

        result["emotion"] = (
            "futuristic"
        )

        result["atmosphere"] = (
            "neon_dark"
        )

        result[
            "reference_confidence"
        ] += 0.8

        result["references"] = [

            {
                "type": "lighting",
                "title":
                    "Неоновые акценты",
                "weight": 0.95
            },

            {
                "type": "mood",
                "title":
                    "Футуристическая ночная сцена",
                "weight": 0.9
            }
        ]

    # =================================================
    # 🧠 MINIMALISM
    # =====================================================

    minimal_words = [

        "минимализм",
        "minimal",
        "чисто",
        "аккуратно",
        "спокойно"
    ]

    if contains_any(
        t,
        minimal_words
    ):

        result["enabled"] = True

        result["mode"] = "minimal"

        result["emotion"] = "calm"

        result["atmosphere"] = (
            "minimal_soft"
        )

        result[
            "reference_confidence"
        ] += 0.72

        result["references"] = [

            {
                "type": "style",
                "title":
                    "Чистый спокойный minimal",
                "weight": 0.92
            },

            {
                "type": "palette",
                "title":
                    "Нейтральные мягкие цвета",
                "weight": 0.82
            }
        ]

    # =================================================
    # 🧠 CONFIRMATION
    # =====================================================

    confirmation_words = [

        "да",
        "вот",
        "ага",
        "ближе",
        "примерно",
        "уже лучше"
    ]

    if contains_any(
        t,
        confirmation_words
    ):

        result[
            "direction_detected"
        ] = True

        result[
            "suppress_generation"
        ] = True

        result[
            "reference_priority"
        ] = True

    # =================================================
    # 🧠 HARD GENERATION
    # =====================================================

    generate_words = [

        "создай изображение",
        "сгенерируй изображение",
        "нарисуй картинку",
        "сделай картинку"
    ]

    explicit_generation = contains_any(
        t,
        generate_words
    )

    if explicit_generation:

        # 🔥 provider-aware:
        # generation только
        # при explicit intent

        if (

            not result[
                "suppress_generation"
            ]

            and ambiguity < 0.4

            and dialog_state != (
                "exploration"
            )

            and not cognition.get(
                "exploration_mode"
            )
        ):

            result[
                "should_generate"
            ] = True

            result[
                "generation_allowed"
            ] = True

            result[
                "avoid_heavy_generation"
            ] = False

    # =================================================
    # 🧠 ACTIVE FLOW
    # =====================================================

    if active_flow:

        result[
            "trajectory_aligned"
        ] = True

        result[
            "dialogue_centered"
        ] = True

    # =================================================
    # 🧠 REFERENCE SORT
    # =====================================================

    result["references"] = sorted(

        result["references"],

        key=lambda x: x.get(
            "weight",
            0.0
        ),

        reverse=True
    )

    # =================================================
    # 🧠 NORMALIZATION
    # =====================================================

    if result[
        "support_level"
    ] > 1.0:

        result[
            "support_level"
        ] = 1.0

    if result[
        "reference_confidence"
    ] > 1.0:

        result[
            "reference_confidence"
        ] = 1.0

    # =================================================
    # 🧠 FINAL SAFETY
    # =====================================================

    if result[
        "lightweight_mode"
    ]:

        result[
            "should_generate"
        ] = False

    return result
