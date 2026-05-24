# ===============================
# 🧠 APRIL INTENT SYSTEM
# ===============================

"""
DeepHub stabilized intent system.

Intent system больше НЕ:
- hard trigger authority;
- execution launcher;
- scene breaker.

Intent system теперь:
- lightweight signal layer;
- dialog-aware helper;
- continuation-safe classifier;
- renderer-aware router;
- trajectory-friendly assistant.
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

    except:
        pass


# =====================================================
# 🧠 PATCH HELPERS
# =====================================================

def patch_intent_detect(text):

    safe_patch_log(
        f"INTENT DETECT: {text[:50]}"
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
        "в таком стиле",
        "оставь",
        "вот это",
        "ближе к этому"
    ]

    if t in continuation_words:

        return True

    if len(t) <= 24:

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

    if is_continuation(t):

        return False

    if len(t) <= 12:

        return False

    if "?" in t:

        return True

    if contains_any(
        t,
        question_triggers
    ):

        return True

    return False


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

        # 🔥 explicit image only

        "ultra realistic",
        "4k render",
        "cinematic render"
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
        "композиция"
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
        "рядом",
        "пространство",
        "scene",
        "layout"
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
        "сейчас в"
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
    # 🔥 CONTINUATION PRIORITY
    # =====================================================

    if is_continuation(t):

        if active_flow:

            return {

                "intent": "continuation",

                "confidence": 0.88,

                "source": "continuation"
            }

        if active_visual_scene:

            return {

                "intent": "visual_continuation",

                "confidence": 0.84,

                "source": "visual_scene"
            }

        return {

            "intent": "chat",

            "confidence": 0.55,

            "source": "soft_continuation"
        }

    # =================================================
    # 🔥 WEB
    # =====================================================

    if is_web_request(t):

        return {

            "intent": "web",

            "confidence": 0.88,

            "source": "web"
        }

    # =================================================
    # 🔥 LINK
    # =====================================================

    if is_link_request(t):

        return {

            "intent": "link",

            "confidence": 0.92,

            "source": "link"
        }

    # =================================================
    # 🔥 EDIT
    # =====================================================

    if is_edit_request(t):

        return {

            "intent": "edit",

            "confidence": 0.88,

            "source": "edit"
        }

    # =================================================
    # 🔥 SPATIAL RENDER
    # =====================================================

    if is_spatial_request(t):

        return {

            "intent": "spatial",

            "confidence": 0.82,

            "source": "spatial"
        }

    # =================================================
    # 🔥 RENDERER SPACE
    # =====================================================

    if is_renderer_request(t):

        return {

            "intent": "render",

            "confidence": 0.86,

            "source": "renderer"
        }

    # =================================================
    # 🔥 LIGHTWEIGHT VISUAL
    # =====================================================

    if is_lightweight_visual_request(t):

        return {

            "intent": "lightweight_visual",

            "confidence": 0.8,

            "source": "lightweight_visual"
        }

    # =================================================
    # 🔥 HEAVY GENERATION
    # =====================================================

    if is_generate_request(t):

        return {

            "intent": "generate",

            "confidence": 0.9,

            "source": "generate"
        }

    # =================================================
    # 🔥 TEXT REQUEST
    # =====================================================

    if is_text_request(t):

        return {

            "intent": "text",

            "confidence": 0.84,

            "source": "text"
        }

    # =================================================
    # 🔥 QUESTION
    # =====================================================

    if is_real_question(t):

        return {

            "intent": "question",

            "confidence": 0.72,

            "source": "question"
        }

    # =================================================
    # 🔥 ACTIVE FLOW PROTECTION
    # =====================================================

    if active_flow:

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

            return {

                "intent": "continuation",

                "confidence": 0.74,

                "source": "trajectory"
            }

    # =================================================
    # 🔥 DEFAULT CHAT
    # =====================================================

    return {

        "intent": "chat",

        "confidence": 0.5,

        "source": "default"
    }
