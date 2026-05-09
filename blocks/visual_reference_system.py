# blocks/visual_reference_system.py

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

        "support_level": 0.0
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
        "как сделать уютнее"
    ]

    if any(x in t for x in exploration_words):

        result["enabled"] = True

        result["mode"] = "exploration"

        result["support_level"] += 0.5

    # =================================================
    # 🔥 VISUAL EXPECTATION
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

        result["references"] = [

            {
                "type": "mood",
                "title":
                    "Тёплый локальный свет"
            },

            {
                "type": "interior",
                "title":
                    "Мягкая кофейная атмосфера"
            },

            {
                "type": "lighting",
                "title":
                    "Лампы с тёплым рассеянным светом"
            },

            {
                "type": "style",
                "title":
                    "Дерево, мягкие тени и спокойные цвета"
            }
        ]

        result["guidance"] = (

            "Похоже, ты двигаешься "
            "в сторону мягкой и уютной "
            "вечерней атмосферы."
        )

        result["support_level"] += 0.6

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

        result["should_generate"] = True

    # =================================================
    # 🔥 NORMALIZATION
    # =================================================

    if result["support_level"] > 1.0:

        result["support_level"] = 1.0

    return result
