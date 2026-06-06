# =====================================================
# 🧠 VISUAL MEMORY LIBRARY
# =====================================================

"""
April visual cognitive memory system.

НЕ генерация.
НЕ image pipeline.

Это lightweight visual cognition layer.

Главная задача:
помогать April понимать,
как направлять пользователя
через visual references,
а не сразу уходить
в тяжёлую генерацию.

Система используется для:

- atmosphere guidance
- exploration support
- visual thinking
- intent clarification
- soft direction
- emotional atmosphere detection
- reference suggestion
- cognitive trajectory support

Это:
НЕ renderer
НЕ image creator

Это:
visual understanding memory.
"""

# =====================================================
# 🔥 VISUAL ATMOSPHERES
# =====================================================

VISUAL_ATMOSPHERES = {

    "cozy_cafe": {

        "title":
            "Уютная кофейная атмосфера",

        "keywords": [

            "уют",
            "кофейня",
            "вечером",
            "лампы",
            "теплый свет",
            "атмосфера",
            "мягкий свет",
            "спокойствие",
            "уютно"
        ],

        "references": [

            {
                "type": "lighting",
                "title":
                    "Тёплые подвесные лампы"
            },

            {
                "type": "mood",
                "title":
                    "Спокойная вечерняя атмосфера"
            },

            {
                "type": "interior",
                "title":
                    "Тёмное дерево и мягкие тени"
            },

            {
                "type": "emotion",
                "title":
                    "Ощущение расслабленности"
            }
        ],

        "guidance": (
            "Пользователь, вероятно, "
            "ищет не конкретный объект, "
            "а эмоциональную атмосферу."
        )
    },

    # =================================================

    "modern_clean": {

        "title":
            "Современный минимализм",

        "keywords": [

            "минимализм",
            "современно",
            "чисто",
            "аккуратно",
            "просторно",
            "минимально"
        ],

        "references": [

            {
                "type": "style",
                "title":
                    "Чистые поверхности"
            },

            {
                "type": "color",
                "title":
                    "Нейтральные цвета"
            },

            {
                "type": "lighting",
                "title":
                    "Мягкий дневной свет"
            }
        ],

        "guidance": (
            "Пользователь тянется "
            "к спокойному и чистому "
            "визуальному стилю."
        )
    },

    # =================================================

    "creative_workspace": {

        "title":
            "Креативное рабочее пространство",

        "keywords": [

            "рабочее место",
            "вдохновение",
            "дизайн",
            "креатив",
            "студия",
            "рабочая зона"
        ],

        "references": [

            {
                "type": "workspace",
                "title":
                    "Тёплый рабочий свет"
            },

            {
                "type": "focus",
                "title":
                    "Минимум визуального шума"
            },

            {
                "type": "emotion",
                "title":
                    "Ощущение вдохновения"
            }
        ],

        "guidance": (
            "Пользователь пытается "
            "найти состояние концентрации "
            "и вдохновения."
        )
    }
}

# =====================================================
# 🔥 VISUAL EXPLORATION PHRASES
# =====================================================

VISUAL_EXPLORATION_PHRASES = [

    "примерно так",
    "что-то похожее",
    "не знаю чего хочу",
    "как будто",
    "вроде бы",
    "примерно",
    "наверное",
    "не понимаю",
    "что лучше",
    "что выбрать",
    "как сделать уютнее",
    "как улучшить",
    "не уверен",
    "не определился"
]

# =====================================================
# 🔥 LIGHTWEIGHT VISUAL SUPPORT
# =====================================================

LIGHTWEIGHT_VISUAL_SUPPORT = {

    "enabled": True,

    "prefer_references_over_generation": True,

    "prefer_guidance_over_execution": True,

    "allow_soft_visual_direction": True,

    "allow_atmosphere_support": True,

    "allow_reference_examples": True,

    "reduce_heavy_generation": True
}

# =====================================================
# 🔥 EMOTIONAL VISUAL STATES
# =====================================================

EMOTIONAL_VISUAL_STATES = {

    "comfort": [

        "уют",
        "спокойствие",
        "мягкость",
        "тепло",
        "лампово"
    ],

    "focus": [

        "концентрация",
        "рабочее",
        "эффективность",
        "организация"
    ],

    "exploration": [

        "не знаю",
        "ищу",
        "примерно",
        "может быть"
    ],

    "creative": [

        "креатив",
        "вдохновение",
        "нестандартно",
        "атмосферно"
    ]
}

# =====================================================
# 🔥 VISUAL COGNITION HELPERS
# =====================================================

def detect_visual_atmosphere(text: str):

    t = (text or "").lower()

    best_match = None
    best_score = 0

    for key, data in VISUAL_ATMOSPHERES.items():

        score = 0

        for kw in data["keywords"]:

            if kw in t:
                score += 1

        if score > best_score:

            best_score = score
            best_match = key

    if not best_match:
        return None

    return VISUAL_ATMOSPHERES.get(best_match)


# =====================================================

def detect_visual_exploration(text: str):

    t = (text or "").lower()

    for phrase in VISUAL_EXPLORATION_PHRASES:

        if phrase in t:
            return True

    return False


# =====================================================

def detect_emotional_visual_state(text: str):

    t = (text or "").lower()

    result = {

        "state": None,
        "confidence": 0.0
    }

    best_score = 0

    for state, words in EMOTIONAL_VISUAL_STATES.items():

        score = 0

        for word in words:

            if word in t:
                score += 1

        if score > best_score:

            best_score = score

            result["state"] = state

            result["confidence"] = min(
                score / 3,
                1.0
            )

    return result


# =====================================================


# =====================================================
# 🧠 VISUAL FOCUS MEMORY UPGRADE
# =====================================================

def build_visual_focus_snapshot(text: str):

    t = (text or "").lower()

    focus_object = None

    candidates = [
        "объект","предмет","человек","машина",
        "дом","кот","собака","график","схема"
    ]

    for item in candidates:
        if item in t:
            focus_object = item
            break

    return {
        "focus_object": focus_object,
        "focus_active": focus_object is not None,
        "visual_context_refresh": focus_object is not None
    }


def build_visual_memory_response(text: str):

    atmosphere = detect_visual_atmosphere(text)

    emotion = detect_emotional_visual_state(text)

    exploration = detect_visual_exploration(text)

    focus_snapshot = build_visual_focus_snapshot(text)

    return {

        "atmosphere": atmosphere,

        "emotion": emotion,

        "exploration": exploration,

        "visual_focus": focus_snapshot,

        "lightweight_mode":
            LIGHTWEIGHT_VISUAL_SUPPORT[
                "enabled"
            ],

        "prefer_references":
            LIGHTWEIGHT_VISUAL_SUPPORT[
                "prefer_references_over_generation"
            ]
    }

