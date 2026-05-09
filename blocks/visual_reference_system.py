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

        "response_style": "guidance"
    }

    # =================================================
    # 🔥 SEARCHING / EXPLORATION STATE
    # =================================================

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

        result["support_level"] += 0.5

        result["lightweight_mode"] = True

        result["suppress_generation"] = True

    # =================================================
    # 🔥 SEMANTIC VISUAL EXPECTATION
    # =================================================

    if semantic.get(
        "visual_expectation",
        0.0
    ) >= 0.5:

        result["enabled"] = True

        result["support_level"] += 0.4

    # =================================================
    # 🔥 EXAMPLE EXPECTATION
    # =================================================

    if semantic.get(
        "example_expectation",
        0.0
    ) >= 0.5:

        result["enabled"] = True

        result["support_level"] += 0.4

    # =================================================
    # 🔥 COGNITIVE EXPLORATION
    # =================================================

    if cognition.get(
        "exploration_mode"
    ):

        result["enabled"] = True

        result["lightweight_mode"] = True

        result["suppress_generation"] = True

        result["response_style"] = "soft_guidance"

    # =================================================
    # 🔥 USER LEADS
    # =================================================

    if cognition.get(
        "user_leads_direction"
    ):

        result["direction_detected"] = True

        result["suppress_generation"] = True

        result["lightweight_mode"] = True

    # =================================================
    # 🔥 ATMOSPHERE DETECTION
    # =================================================

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

        result["reference_confidence"] += 0.85

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
                    "Мягкая кофейная атмосфера",
                "weight": 0.95
            },

            {
                "type": "lighting",
                "title":
                    "Лампы с тёплым рассеянным светом",
                "weight": 0.8
            },

            {
                "type": "style",
                "title":
                    "Дерево, мягкие тени и спокойные цвета",
                "weight": 0.9
            }
        ]

        result["guidance"] = (

            "Похоже, тебе сейчас "
            "ближе мягкая камерная "
            "атмосфера с тёплым светом "
            "и спокойным интерьером."
        )

        result["support_level"] += 0.6

    # =================================================
    # 🔥 CYBERPUNK DETECTION
    # =================================================

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

        result["reference_confidence"] += 0.85

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
                    "Ночной futuristic city mood",
                "weight": 0.9
            },

            {
                "type": "style",
                "title":
                    "Тёмные поверхности и контрастный свет",
                "weight": 0.85
            }
        ]

        result["guidance"] = (

            "Сейчас направление "
            "больше уходит в futuristic "
            "и neon атмосферу."
        )

    # =================================================
    # 🔥 MINIMALISM DETECTION
    # =================================================

    minimal_words = [

        "минимализм",
        "minimal",
        "чисто",
        "просто",
        "аккуратно",
        "спокойно"
    ]

    if any(x in t for x in minimal_words):

        result["enabled"] = True

        result["mode"] = "minimal"

        result["emotion"] = "calm"

        result["reference_confidence"] += 0.75

        result["references"] = [

            {
                "type": "style",
                "title":
                    "Минималистичный clean design",
                "weight": 0.9
            },

            {
                "type": "palette",
                "title":
                    "Спокойные нейтральные цвета",
                "weight": 0.85
            }
        ]

        result["guidance"] = (

            "Похоже, тебе ближе "
            "спокойный минималистичный стиль "
            "без перегруза."
        )

    # =================================================
    # 🔥 CONFIRMATION DETECTION
    # =================================================

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

        # 🔥 НЕ запускаем генерацию
        result["should_generate"] = False

        result["suppress_generation"] = True

    # =================================================
    # 🔥 HARD GENERATION REQUEST
    # =================================================

    generate_words = [

        "сгенерируй",
        "создай изображение",
        "нарисуй",
        "сделай картинку",
        "покажи изображение"
    ]

    if any(x in t for x in generate_words):

        if not result["suppress_generation"]:

            result["should_generate"] = True

    # =================================================
    # 🔥 REFERENCE SORT
    # =================================================

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
    # =================================================

    if result["support_level"] > 1.0:

        result["support_level"] = 1.0

    if result["reference_confidence"] > 1.0:

        result["reference_confidence"] = 1.0

    return result
