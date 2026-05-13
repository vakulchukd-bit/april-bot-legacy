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
        "поехали"
    ]

    if t in continuation_words:

        return True

    if len(t) <= 20:

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

    # 🔥 continuation НЕ question

    if is_continuation(t):

        return False

    # 🔥 short exploration НЕ question

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
# 🧠 GENERATION DETECTION
# =====================================================

def is_generate_request(
    text: str
):

    t = normalize(text)

    # =================================================
    # 🔥 SAFE GENERATION ONLY
    # =================================================

    generate_triggers = [

        "создай изображение",
        "сгенерируй изображение",
        "нарисуй картинку",
        "создай картинку",
        "generate image",
        "draw image"
    ]

    return contains_any(
        t,
        generate_triggers
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

    patch_intent_detect(t)

    # =================================================
    # 🔥 CONTINUATION PRIORITY
    # =================================================

    if is_continuation(t):

        if active_flow:

            return {

                "intent": "continuation",

                "confidence": 0.82,

                "source": "continuation"
            }

        return {

            "intent": "chat",

            "confidence": 0.55,

            "source": "soft_continuation"
        }

    # =================================================
    # 🔥 LINK
    # =================================================

    if is_link_request(t):

        return {

            "intent": "link",

            "confidence": 0.92,

            "source": "link"
        }

    # =================================================
    # 🔥 EDIT
    # =================================================

    if is_edit_request(t):

        return {

            "intent": "edit",

            "confidence": 0.88,

            "source": "edit"
        }

    # =================================================
    # 🔥 GENERATION
    # =================================================

    if is_generate_request(t):

        return {

            "intent": "generate",

            "confidence": 0.9,

            "source": "generate"
        }

    # =================================================
    # 🔥 TEXT REQUEST
    # =================================================

    if is_text_request(t):

        return {

            "intent": "text",

            "confidence": 0.84,

            "source": "text"
        }

    # =================================================
    # 🔥 QUESTION
    # =================================================

    if is_real_question(t):

        return {

            "intent": "question",

            "confidence": 0.72,

            "source": "question"
        }

    # =================================================
    # 🔥 ACTIVE FLOW PROTECTION
    # =================================================

    if active_flow:

        flow_type = active_flow.get(
            "type"
        )

        if flow_type in [

            "image_generate",
            "image_edit",
            "image",
            "math"
        ]:

            return {

                "intent": "continuation",

                "confidence": 0.68,

                "source": "trajectory"
            }

    # =================================================
    # 🔥 DEFAULT CHAT
    # =================================================

    return {

        "intent": "chat",

        "confidence": 0.5,

        "source": "default"
    }
