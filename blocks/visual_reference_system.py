# =====================================================
# 🧠 VISUAL REFERENCE SYSTEM
# =====================================================

def build_visual_reference(
    semantic: dict,
    cognition: dict,
    text: str,
    state: dict
):

    t = (text or "").lower().strip()

    active_flow = state.get(
        "active_flow"
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
        # SYSTEM ENABLED
        # =================================================

        "enabled": False,

        # =================================================
        # REFERENCE MODE
        # =================================================

        "mode": None,

        # =================================================
        # VISUAL REFERENCES
        # =================================================

        "references": [],

        # =================================================
        # SHOULD GENERATE
        # =================================================

        "should_generate": False,

        # =================================================
        # USER DIRECTION FOUND
        # =================================================

        "direction_detected": False,

        # =================================================
        # GUIDANCE TEXT
        # =================================================

        "guidance": None,

        # =================================================
        # VISUAL SUPPORT LEVEL
        # =================================================

        "support_level": 0.0,

        # =================================================
        # EMOTIONAL SPACE
        # =================================================

        "emotion": None,

        # =================================================
        # REFERENCE CONFIDENCE
        # =================================================

        "reference_confidence": 0.0,

        # =================================================
        # LIGHTWEIGHT MODE
        # =================================================

        "lightweight_mode": False,

        # =================================================
        # GENERATION SUPPRESSION
        # =================================================

        "suppress_generation": False,

        # =================================================
        # RESPONSE STYLE
        # =================================================

        "response_style": "guidance",

        # =================================================
        # DIALOG INTEGRATION
        # =================================================

        "trajectory_aligned": True,

        "dialogue_centered": True,

        "visual_is_supportive": True,

        "visual_should_continue_dialogue": True,

        "visual_should_not_interrupt": True,

        "visual_requires_meaning": True,

        "visual_requires_context": True,

        "visual_is_not_random": True,

        "capability_awareness": True
    }

    # =================================================
    # 🔥 DIALOG STATE
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

    # =================================================
    # 🔥 SEARCHING / EXPLORATION STATE
    # =====================================================

    exploration_words = [

        "примерно",
        "что-то",
        "не знаю",
        "как будто",
        "наверное",
        "хочу атмосферу",
        "не понимаю",
        "не уверен",
        "посоветуй",
        "что лучше",
        "как сделать уютнее",
        "идея",
        "направление"
    ]

    if any(x in t for x in exploration_words):

        result["enabled"] = True

        result["mode"] = "exploration"

        result["support_level"] += 0.45

        result["lightweight_mode"] = True

        result["suppress_generation"] = True

        result["response_style"] = (
            "soft_guidance"
        )

    # =================================================
    # 🔥 SEMANTIC VISUAL EXPECTATION
    # =====================================================

    if semantic.get(
        "visual_expectation",
        0.0
    ) >= 0.5:

        result["enabled"] = True

        result["support_level"] += 0.3

    # =================================================
    # 🔥 EXAMPLE EXPECTATION
    # =====================================================

    if semantic.get(
        "example_expectation",
        0.0
    ) >= 0.5:

        result["enabled"] = True

        result["support_level"] += 0.3

    # =================================================
    # 🔥 COGNITIVE EXPLORATION
    # =====================================================

    if cognition.get(
        "exploration_mode"
    ):

        result["enabled"] = True

        result["lightweight_mode"] = True

        result["suppress_generation"] = True

        result["response_style"] = (
            "soft_guidance"
        )

    # =================================================
    # 🔥 USER LEADS
    # =====================================================

    if cognition.get(
        "user_leads_direction"
    ):

        result["direction_detected"] = True

        result["suppress_generation"] = True

        result["lightweight_mode"] = True

    # =================================================
    # 🔥 VISUALS MUST FOLLOW DIALOGUE
    # =====================================================

    if (
        dialog_state == "exploration"
        or ambiguity >= 0.45
        or unresolved_intent
    ):

        result["lightweight_mode"] = True

        result["suppress_generation"] = True

    # =================================================
    # 🔥 SCREENSHOT PROTECTION
    # =====================================================

    screenshot_words = [

        "скрин",
        "скриншот",
        "screenshot"
    ]

    if any(x in t for x in screenshot_words):

        result["enabled"] = True

        result["lightweight_mode"] = True

        result["suppress_generation"] = True

        result["mode"] = "context_support"

        result["guidance"] = (

            "Скриншот лучше использовать "
            "как помощь для понимания темы "
            "или проблемы, а не отдельно "
            "от смысла разговора."
        )

    # =================================================
    # 🔥 ATMOSPHERE DETECTION
    # =====================================================

    cozy_words = [

        "уют",
        "кофейня",
        "вечером",
        "тепло",
        "лампы",
        "атмосфера",
        "мягкий свет"
    ]

    if any(x in t for x in cozy_words):

        result["enabled"] = True

        result["direction_detected"] = True

        result["mode"] = "atmosphere"

        result["emotion"] = "cozy"

        result["reference_confidence"] += 0.82

        result["references"] = [

            {
                "type": "mood",
                "title":
                    "Тёплый локальный свет",
                "weight": 0.9
            },

            {
                "type": "interior",
                "title":
                    "Мягкая камерная атмосфера",
                "weight": 0.95
            },

            {
                "type": "lighting",
                "title":
                    "Тёплое мягкое освещение",
                "weight": 0.8
            },

            {
                "type": "style",
                "title":
                    "Спокойные натуральные материалы",
                "weight": 0.85
            }
        ]

        result["guidance"] = (

            "Похоже, разговор сейчас "
            "движется в сторону "
            "мягкой спокойной атмосферы "
            "с тёплым визуальным ощущением."
        )

        result["support_level"] += 0.5

    # =================================================
    # 🔥 CYBERPUNK DETECTION
    # =====================================================

    cyberpunk_words = [

        "неон",
        "cyberpunk",
        "киберпанк",
        "футуризм",
        "ночной город",
        "фиолетовый свет"
    ]

    if any(x in t for x in cyberpunk_words):

        result["enabled"] = True

        result["mode"] = "cyberpunk"

        result["emotion"] = "futuristic"

        result["reference_confidence"] += 0.82

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
                    "Футуристическая ночная атмосфера",
                "weight": 0.9
            },

            {
                "type": "style",
                "title":
                    "Контрастный свет и тёмные поверхности",
                "weight": 0.85
            }
        ]

        result["guidance"] = (

            "Разговор сейчас больше "
            "уходит в futuristic "
            "и neon настроение."
        )

    # =================================================
    # 🔥 MINIMALISM DETECTION
    # =====================================================

    minimal_words = [

        "минимализм",
        "minimal",
        "чисто",
        "аккуратно",
        "спокойно"
    ]

    if any(x in t for x in minimal_words):

        result["enabled"] = True

        result["mode"] = "minimal"

        result["emotion"] = "calm"

        result["reference_confidence"] += 0.72

        result["references"] = [

            {
                "type": "style",
                "title":
                    "Чистый минималистичный стиль",
                "weight": 0.9
            },

            {
                "type": "palette",
                "title":
                    "Нейтральные спокойные цвета",
                "weight": 0.82
            }
        ]

        result["guidance"] = (

            "Сейчас направление разговора "
            "скорее идёт к спокойному "
            "минималистичному ощущению."
        )

    # =================================================
    # 🔥 CONFIRMATION DETECTION
    # =====================================================

    confirmation_words = [

        "да",
        "вот",
        "ближе",
        "примерно",
        "ага",
        "уже лучше"
    ]

    if any(x in t for x in confirmation_words):

        result["direction_detected"] = True

        result["should_generate"] = False

        result["suppress_generation"] = True

    # =================================================
    # 🔥 HARD GENERATION REQUEST
    # =====================================================

    generate_words = [

        "сгенерируй",
        "создай изображение",
        "нарисуй",
        "сделай картинку"
    ]

    explicit_generation = any(
        x in t
        for x in generate_words
    )

    if explicit_generation:

        # 🔥 generation только если trajectory готов
        if (
            not result["suppress_generation"]
            and ambiguity < 0.45
            and dialog_state != "exploration"
        ):

            result["should_generate"] = True

    # =================================================
    # 🔥 ACTIVE FLOW STABILIZATION
    # =====================================================

    if active_flow:

        result["trajectory_aligned"] = True

        result["dialogue_centered"] = True

    # =================================================
    # 🔥 REFERENCE SORT
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
    # 🔥 NORMALIZATION
    # =====================================================

    if result["support_level"] > 1.0:

        result["support_level"] = 1.0

    if result["reference_confidence"] > 1.0:

        result["reference_confidence"] = 1.0

    # =================================================
    # 🔥 FINAL TRAJECTORY SAFETY
    # =====================================================

    if result["lightweight_mode"]:

        result["should_generate"] = False

    return result
