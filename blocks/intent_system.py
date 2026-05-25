# ===============================
# 🧠 APRIL INTENT SYSTEM
# ===============================

"""
APRIL ORCHESTRATION INTENT SYSTEM

Intent system теперь:
- lightweight semantic helper;
- continuation-safe signal layer;
- orchestration-aware classifier;
- renderer-first assistant;
- provider-safe interpreter.

Intent system НЕ:
- command router;
- hard execution authority;
- fallback trigger;
- Telegram-era dispatcher;
- aggressive escalation layer.

APRIL PRINCIPLES:

1. continuation before coercion
2. renderer before generation
3. orchestration before commands
4. lightweight before heavy
5. semantic neutrality
6. no hidden escalation
7. no Telegram assumptions
"""

# ===============================
# 🔥 SAFE PATCH MODE
# ===============================

PATCH_LOG = []


def safe_patch_log(msg):

    try:

        print(
            "INTENT PATCH:",
            msg
        )

        PATCH_LOG.append(msg)

    except Exception:
        pass


# =====================================================
# 🧠 PATCH HELPERS
# =====================================================

def patch_intent_detect(text):

    safe_patch_log(
        f"INTENT DETECT: {text[:60]}"
    )

    return text


def patch_intent_future(
    *args,
    **kwargs
):

    return None


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
# 🧠 CONTINUATION DETECTION
# =====================================================

def is_continuation(
    text: str
):

    t = normalize(text)

    continuation_words = [

        "да",
        "ага",
        "ок",
        "окей",
        "давай",
        "вот",
        "примерно",
        "ближе",
        "уже лучше",
        "не то",
        "чуть темнее",
        "чуть ярче",
        "продолжай",
        "с этого",
        "поехали",
        "дальше",
        "теперь",
        "еще",
        "ещё",
        "в таком стиле",
        "оставь",
        "вот это",
        "ближе к этому",
        "продолжим",
        "вернемся",
        "вернёмся"
    ]

    if t in continuation_words:

        return True

    if len(t) <= 36:

        if contains_any(
            t,
            continuation_words
        ):

            return True

    return False


# =====================================================
# 🧠 QUESTION DETECTION
# =====================================================

def is_real_question(
    text: str
):

    t = normalize(text)

    if is_continuation(t):

        return False

    if len(t) <= 10:

        return False

    question_triggers = [

        "как",
        "что",
        "почему",
        "зачем",
        "умеешь",
        "можешь",
        "где",
        "когда",
        "сколько",
        "какой",
        "какая",
        "какие"
    ]

    if "?" in t:

        return True

    return contains_any(
        t,
        question_triggers
    )


# =====================================================
# 🧠 EDIT DETECTION
# =====================================================

def is_edit_request(
    text: str
):

    t = normalize(text)

    edit_triggers = [

        "добавь",
        "измени",
        "убери",
        "замени",
        "поменяй",
        "улучши",
        "подправь",
        "ярче",
        "темнее",
        "переделай",
        "исправь",
        "сделай темнее",
        "сделай ярче"
    ]

    return contains_any(
        t,
        edit_triggers
    )


# =====================================================
# 🧠 HEAVY GENERATION DETECTION
# =====================================================

def is_generate_request(
    text: str
):

    t = normalize(text)

    generate_triggers = [

        "создай изображение",
        "сгенерируй изображение",
        "нарисуй картинку",
        "создай картинку",
        "draw image",
        "generate image",

        # 🔥 explicit heavy visual

        "ultra realistic",
        "4k render",
        "cinematic render",
        "photorealistic",
        "realistic render"
    ]

    return contains_any(
        t,
        generate_triggers
    )


# =====================================================
# 🧠 LIGHTWEIGHT VISUAL
# =====================================================

def is_lightweight_visual_request(
    text: str
):

    t = normalize(text)

    lightweight_words = [

        "пример",
        "референс",
        "концепт",
        "идея",
        "вариант",
        "атмосфера",
        "примерно",
        "визуально",
        "как выглядит",
        "схема",
        "layout",
        "структура",
        "расположение"
    ]

    return contains_any(
        t,
        lightweight_words
    )


# =====================================================
# 🧠 RENDERER DETECTION
# =====================================================

def detect_renderer_subtype(
    text: str
):

    t = normalize(text)

    if "график" in t:

        return "graph"

    if "формула" in t:

        return "formula"

    if (
        "таблица" in t
        or "grid" in t
    ):

        return "table"

    if (
        "diagram" in t
        or "диаграмма" in t
        or "схема" in t
    ):

        return "diagram"

    if (
        "layout" in t
        or "пространство" in t
        or "scene" in t
        or "композиция" in t
    ):

        return "scene"

    return "renderer"


def is_renderer_request(
    text: str
):

    t = normalize(text)

    renderer_words = [

        "график",
        "таблица",
        "формула",
        "diagram",
        "диаграмма",
        "схема",
        "layout",
        "структура",
        "grid",
        "line",
        "point",
        "arrow",
        "renderer",
        "пространство",
        "scene",
        "композиция",
        "canvas"
    ]

    return contains_any(
        t,
        renderer_words
    )


# =====================================================
# 🧠 SPATIAL SCENE DETECTION
# =====================================================

def is_spatial_request(
    text: str
):

    t = normalize(text)

    spatial_words = [

        "слева",
        "справа",
        "сверху",
        "снизу",
        "по центру",
        "размести",
        "поставь",
        "расположи",
        "между",
        "рядом"
    ]

    return contains_any(
        t,
        spatial_words
    )


# =====================================================
# 🧠 WEB DETECTION
# =====================================================

def is_web_request(
    text: str
):

    t = normalize(text)

    web_words = [

        "погода",
        "новости",
        "курс валют",
        "что происходит",
        "где находится",
        "карта",
        "маршрут",
        "рейс",
        "сейчас в",
        "такси",
        "отель",
        "навигация",
        "локация"
    ]

    return contains_any(
        t,
        web_words
    )


# =====================================================
# 🧠 TEXT DETECTION
# =====================================================

def is_text_request(
    text: str
):

    t = normalize(text)

    text_triggers = [

        "сообщение",
        "письмо",
        "текст",
        "шаблон",
        "ответ клиенту",
        "напиши письмо",
        "напиши сообщение"
    ]

    return contains_any(
        t,
        text_triggers
    )


# =====================================================
# 🧠 LINK DETECTION
# =====================================================

def is_link_request(
    text: str
):

    t = normalize(text)

    link_triggers = [

        "ссылка",
        "url",
        "линк",
        "короткая ссылка",
        "сократи ссылку",
        "short link"
    ]

    return contains_any(
        t,
        link_triggers
    )


# =====================================================
# 🧠 EXPLORATION DETECTION
# =====================================================

def is_exploration_request(
    text: str
):

    t = normalize(text)

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
# 🧠 MAIN DETECTOR
# =====================================================

def detect_intent(
    text: str,
    state: dict = None
):

    t = normalize(text)

    state = state or {}

    active_flow = state.get(
        "active_flow",
        {}
    )

    active_visual_scene = state.get(
        "active_visual_scene",
        {}
    )

    patch_intent_detect(t)

    # =================================================
    # 🔥 BASE RESULT
    # =====================================================

    result = {

        # =================================================
        # 🔥 CORE
        # =====================================================

        "intent": "chat",

        "confidence": 0.5,

        "source": "default",

        # =================================================
        # 🔥 ORCHESTRATION
        # =====================================================

        "prefer_renderer": False,

        "prefer_lightweight": False,

        "prefer_guidance": False,

        "prefer_execution": False,

        "prefer_continuation": False,

        "prefer_web": False,

        # =================================================
        # 🔥 VISUAL
        # =====================================================

        "renderer_subtype": None,

        "lightweight_visual": False,

        "spatial_scene": False,

        "explicit_image_generation": False,

        # =================================================
        # 🔥 CONTINUITY
        # =====================================================

        "continuation": False,

        "trajectory_safe": True,

        "trajectory_priority": 0.5,

        # =================================================
        # 🔥 EXPLORATION
        # =====================================================

        "exploration": False,

        # =================================================
        # 🔥 SAFETY
        # =====================================================

        "avoid_heavy_generation": True,

        "avoid_hidden_escalation": True,

        "avoid_telegram_behavior": True,

        "provider_safe": True
    }

    # =================================================
    # 🔥 CONTINUATION PRIORITY
    # =====================================================

    if is_continuation(t):

        result[
            "continuation"
        ] = True

        result[
            "prefer_continuation"
        ] = True

        result[
            "trajectory_priority"
        ] = 0.9

        if active_flow:

            result[
                "intent"
            ] = "continuation"

            result[
                "confidence"
            ] = 0.88

            result[
                "source"
            ] = "continuation"

            return result

        if active_visual_scene:

            result[
                "intent"
            ] = "visual_continuation"

            result[
                "confidence"
            ] = 0.84

            result[
                "source"
            ] = "visual_scene"

            result[
                "prefer_renderer"
            ] = True

            return result

    # =================================================
    # 🔥 EXPLORATION
    # =====================================================

    if is_exploration_request(t):

        result[
            "exploration"
        ] = True

        result[
            "prefer_lightweight"
        ] = True

        result[
            "lightweight_visual"
        ] = True

        result[
            "trajectory_priority"
        ] = max(
            result[
                "trajectory_priority"
            ],
            0.72
        )

    # =================================================
    # 🔥 WEB
    # =====================================================

    if is_web_request(t):

        result[
            "intent"
        ] = "web"

        result[
            "confidence"
        ] = 0.88

        result[
            "source"
        ] = "web"

        result[
            "prefer_guidance"
        ] = True

        result[
            "prefer_web"
        ] = True

        result[
            "avoid_heavy_generation"
        ] = True

        return result

    # =================================================
    # 🔥 LINK
    # =====================================================

    if is_link_request(t):

        result[
            "intent"
        ] = "link"

        result[
            "confidence"
        ] = 0.92

        result[
            "source"
        ] = "link"

        return result

    # =================================================
    # 🔥 EDIT
    # =====================================================

    if is_edit_request(t):

        result[
            "intent"
        ] = "edit"

        result[
            "confidence"
        ] = 0.88

        result[
            "source"
        ] = "edit"

        result[
            "prefer_execution"
        ] = True

        return result

    # =================================================
    # 🔥 SPATIAL
    # =====================================================

    if is_spatial_request(t):

        result[
            "intent"
        ] = "spatial"

        result[
            "confidence"
        ] = 0.84

        result[
            "source"
        ] = "spatial"

        result[
            "prefer_renderer"
        ] = True

        result[
            "spatial_scene"
        ] = True

        result[
            "renderer_subtype"
        ] = "scene"

        return result

    # =================================================
    # 🔥 RENDERER SPACE
    # =====================================================

    if is_renderer_request(t):

        result[
            "intent"
        ] = "render"

        result[
            "confidence"
        ] = 0.88

        result[
            "source"
        ] = "renderer"

        result[
            "prefer_renderer"
        ] = True

        result[
            "renderer_subtype"
        ] = detect_renderer_subtype(
            t
        )

        result[
            "avoid_heavy_generation"
        ] = True

        return result

    # =================================================
    # 🔥 LIGHTWEIGHT VISUAL
    # =====================================================

    if is_lightweight_visual_request(t):

        result[
            "intent"
        ] = "lightweight_visual"

        result[
            "confidence"
        ] = 0.8

        result[
            "source"
        ] = "lightweight_visual"

        result[
            "prefer_lightweight"
        ] = True

        result[
            "lightweight_visual"
        ] = True

        result[
            "avoid_heavy_generation"
        ] = True

        return result

    # =================================================
    # 🔥 HEAVY GENERATION
    # =====================================================

    if is_generate_request(t):

        result[
            "intent"
        ] = "generate"

        result[
            "confidence"
        ] = 0.9

        result[
            "source"
        ] = "generate"

        result[
            "explicit_image_generation"
        ] = True

        result[
            "avoid_heavy_generation"
        ] = False

        return result

    # =================================================
    # 🔥 TEXT REQUEST
    # =====================================================

    if is_text_request(t):

        result[
            "intent"
        ] = "text"

        result[
            "confidence"
        ] = 0.84

        result[
            "source"
        ] = "text"

        result[
            "prefer_guidance"
        ] = True

        return result

    # =================================================
    # 🔥 QUESTION
    # =====================================================

    if is_real_question(t):

        result[
            "intent"
        ] = "question"

        result[
            "confidence"
        ] = 0.72

        result[
            "source"
        ] = "question"

        result[
            "prefer_guidance"
        ] = True

        return result

    # =================================================
    # 🔥 ACTIVE FLOW PROTECTION
    # =====================================================

    if active_flow:

        result[
            "continuation"
        ] = True

        result[
            "prefer_continuation"
        ] = True

        result[
            "trajectory_priority"
        ] = max(
            result[
                "trajectory_priority"
            ],
            0.74
        )

        flow_type = active_flow.get(
            "type"
        )

        if flow_type in [

            "renderer_space",
            "visual_scene",
            "image_generate",
            "image_edit",
            "image",
            "math"
        ]:

            result[
                "intent"
            ] = "continuation"

            result[
                "confidence"
            ] = 0.74

            result[
                "source"
            ] = "trajectory"

            if flow_type in [

                "renderer_space",
                "visual_scene",
                "math"
            ]:

                result[
                    "prefer_renderer"
                ] = True

    # =================================================
    # 🔥 FINAL DEFAULT
    # =====================================================

    return result
