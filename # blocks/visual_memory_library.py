# =====================================================
# 🧠 VISUAL MEMORY LIBRARY
# =====================================================

"""
April visual cognitive memory.

НЕ генерация.

Это:
- lightweight references
- atmosphere guidance
- exploration support
- visual direction
- trajectory stabilization
- cognitive assistance

Главная цель:
помогать пользователю
формировать intent,
а не сразу финализировать
через тяжёлую генерацию.
"""

# =====================================================
# 🔥 MEMORY PACKS
# =====================================================

VISUAL_MEMORY = {

    # =================================================
    # ☕ COZY CAFE
    # =================================================

    "cozy_cafe": {

        "category": "atmosphere",

        "keywords": [

            "кофейня",
            "уют",
            "уютно",
            "тепло",
            "лампы",
            "вечер",
            "мягкий свет",
            "coffee",
            "cafe"
        ],

        "mood": [

            "тёплый свет",
            "мягкие тени",
            "деревянные элементы",
            "спокойная атмосфера",
            "лампы с рассеянным светом"
        ],

        "guidance": [

            "Можно сделать атмосферу более тёплой через локальный свет.",

            "Хорошо подойдут мягкие оранжевые оттенки и приглушённые тени.",

            "Сейчас направление ближе к уютной вечерней кофейне."
        ],

        "reference_titles": [

            "Тёплая кофейная атмосфера",
            "Мягкий локальный свет",
            "Уютный интерьер"
        ],

        "generation_readiness": 0.4
    },

    # =================================================
    # 🌃 CYBERPUNK
    # =================================================

    "cyberpunk": {

        "category": "style",

        "keywords": [

            "cyberpunk",
            "неон",
            "киберпанк",
            "futuristic",
            "future",
            "sci-fi"
        ],

        "mood": [

            "неоновое освещение",
            "контрастный свет",
            "тёмный фон",
            "яркие акценты"
        ],

        "guidance": [

            "Направление уходит в футуристичную атмосферу.",

            "Можно усилить ощущение неона и контраста."
        ],

        "reference_titles": [

            "Cyberpunk neon mood",
            "Futuristic city lighting",
            "Dark neon interface"
        ],

        "generation_readiness": 0.6
    },

    # =================================================
    # 📱 MOBILE UI
    # =================================================

    "mobile_ui": {

        "category": "ui",

        "keywords": [

            "приложение",
            "ui",
            "интерфейс",
            "мобильный",
            "экран",
            "app",
            "ios",
            "android"
        ],

        "mood": [

            "чистый интерфейс",
            "крупные кнопки",
            "простая навигация",
            "минимализм"
        ],

        "guidance": [

            "Лучше начать с простого и чистого интерфейса.",

            "Сейчас больше подходит минималистичный mobile UI."
        ],

        "reference_titles": [

            "Minimal mobile UI",
            "Clean app structure",
            "Simple onboarding flow"
        ],

        "generation_readiness": 0.5
    },

    # =================================================
    # 🌐 LANDING PAGE
    # =================================================

    "landing_page": {

        "category": "website",

        "keywords": [

            "сайт",
            "landing",
            "лендинг",
            "страница",
            "web",
            "website"
        ],

        "mood": [

            "hero block",
            "крупный заголовок",
            "чистая структура",
            "визуальный акцент"
        ],

        "guidance": [

            "Сейчас направление ближе к современному лендингу.",

            "Можно сначала определить атмосферу главного экрана."
        ],

        "reference_titles": [

            "Modern landing page",
            "Minimal website structure",
            "Hero section example"
        ],

        "generation_readiness": 0.55
    },

    # =================================================
    # 🧠 AI DASHBOARD
    # =================================================

    "ai_dashboard": {

        "category": "dashboard",

        "keywords": [

            "dashboard",
            "панель",
            "ai",
            "графики",
            "аналитика",
            "statistics"
        ],

        "mood": [

            "тёмная панель",
            "карточки",
            "графики",
            "структурированный layout"
        ],

        "guidance": [

            "Можно сделать структуру более dashboard-oriented.",

            "Сейчас хорошо подойдут карточки и блоки аналитики."
        ],

        "reference_titles": [

            "AI dashboard",
            "Analytics layout",
            "Modern admin panel"
        ],

        "generation_readiness": 0.65
    }
}

# =====================================================
# 🔥 EXPLORATION DETECTION
# =====================================================

EXPLORATION_WORDS = [

    "примерно",
    "не знаю",
    "что-то",
    "как будто",
    "наверное",
    "может",
    "посоветуй",
    "не уверен",
    "пока думаю",
    "хочу атмосферу",
    "ближе",
    "вроде"
]

# =====================================================
# 🔥 CONFIRMATION WORDS
# =====================================================

CONFIRMATION_WORDS = [

    "да",
    "ага",
    "вот",
    "ближе",
    "примерно",
    "уже лучше"
]

# =====================================================
# 🔥 HARD GENERATION REQUESTS
# =====================================================

GENERATION_WORDS = [

    "сгенерируй",
    "создай изображение",
    "сделай картинку",
    "нарисуй",
    "покажи изображение"
]

# =====================================================
# 🔥 VISUAL MEMORY SEARCH
# =====================================================

def search_visual_memory(text: str):

    t = (text or "").lower()

    matches = []

    for key, pack in VISUAL_MEMORY.items():

        score = 0

        for kw in pack["keywords"]:

            if kw in t:
                score += 1

        if score > 0:

            matches.append({

                "id": key,

                "score": score,

                "pack": pack
            })

    matches.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return matches[:3]

# =====================================================
# 🔥 EXPLORATION STATE
# =====================================================

def detect_exploration_state(text: str):

    t = (text or "").lower()

    return any(
        w in t
        for w in EXPLORATION_WORDS
    )

# =====================================================
# 🔥 GENERATION READINESS
# =====================================================

def detect_generation_readiness(
    text: str,
    semantic: dict,
    cognition: dict
):

    t = (text or "").lower()

    # =================================================
    # HARD REQUEST
    # =================================================

    if any(
        w in t
        for w in GENERATION_WORDS
    ):

        return 0.95

    # =================================================
    # EXPLORATION BLOCK
    # =================================================

    if detect_exploration_state(text):

        return 0.2

    # =================================================
    # CONFIRMATION IS NOT FINALIZATION
    # =================================================

    if any(
        w in t
        for w in CONFIRMATION_WORDS
    ):

        return 0.35

    # =================================================
    # COGNITION
    # =================================================

    pressure = cognition.get(
        "execution_pressure",
        0.0
    )

    wants_visual = cognition.get(
        "wants_visual",
        0.0
    )

    # =================================================
    # SEMANTIC
    # =================================================

    visual_expectation = semantic.get(
        "visual_expectation",
        0.0
    )

    readiness = (
        pressure * 0.4
        + wants_visual * 0.3
        + visual_expectation * 0.3
    )

    return min(readiness, 1.0)

# =====================================================
# 🔥 BUILD VISUAL GUIDANCE
# =====================================================

def build_visual_guidance(
    text: str,
    semantic: dict,
    cognition: dict,
    state: dict
):

    matches = search_visual_memory(text)

    result = {

        "enabled": False,

        "references": [],

        "guidance": [],

        "should_generate": False,

        "generation_readiness": 0.0,

        "exploration_mode": False,

        "trajectory_support": False
    }

    if not matches:
        return result

    result["enabled"] = True

    result["trajectory_support"] = True

    readiness = detect_generation_readiness(
        text,
        semantic,
        cognition
    )

    result[
        "generation_readiness"
    ] = readiness

    if readiness >= 0.75:

        result["should_generate"] = True

    if readiness <= 0.45:

        result["exploration_mode"] = True

    for item in matches:

        pack = item["pack"]

        result["references"].extend(
            pack.get(
                "reference_titles",
                []
            )
        )

        result["guidance"].extend(
            pack.get(
                "guidance",
                []
            )
        )

    return result
