# =====================================================
# 🧠 APRIL INTENT RESOLVER
# =====================================================

"""
DeepHub stabilized resolver.

Resolver больше НЕ:
- hard authority;
- execution trigger;
- scene override system.

Resolver теперь:
- lightweight helper;
- continuation-safe analyzer;
- trajectory-aware assistant.

Главный authority:
- cognition
- semantic_core
- active_flow
- response_decision
"""

import re


# =====================================================
# 🧠 SAFE HELPERS
# =====================================================

def normalize(
    text: str
) -> str:

    return (
        text or ""
    ).strip().lower()


# =====================================================
# 🧠 EXPLICIT EXECUTION
# =====================================================

def is_explicit(
    text: str
) -> bool:

    t = normalize(text)

    if not t:
        return False

    # =================================================
    # 🔥 SAFE KEYWORDS
    # =================================================

    keywords = [

        "реши",
        "посчитай",
        "вычисли",
        "найди значение",
        "построй график",
        "реши уравнение",
        "вычисли выражение"
    ]

    if any(
        word in t
        for word in keywords
    ):

        return True

    # =================================================
    # 🔥 SAFE MATH DETECTION
    # =================================================

    math_patterns = [

        r"\d+\s*[\+\-\*\/]\s*\d+",
        r"y\s*=",
        r"sin\s*\(",
        r"cos\s*\(",
        r"tan\s*\(",
        r"x\^",
    ]

    for pattern in math_patterns:

        if re.search(
            pattern,
            t
        ):

            return True

    return False


# =====================================================
# 🧠 CONTINUATION DETECTION
# =====================================================

def is_reference(
    text: str
) -> bool:

    t = normalize(text)

    continuation_words = [

        "да",
        "ок",
        "давай",
        "с этого",
        "начни",
        "поехали",
        "продолжай",
        "вот",
        "ага",
        "примерно",
        "ближе",
        "уже лучше",
        "не то"
    ]

    if t in continuation_words:

        return True

    if len(t) <= 20:

        if any(
            x in t
            for x in continuation_words
        ):

            return True

    return False


# =====================================================
# 🧠 CONTRADICTION DETECTION
# =====================================================

def contradicts(
    last: str,
    task: str
) -> bool:

    if not last or not task:
        return False

    l = normalize(last)

    triggers = [

        "не надо",
        "забудь",
        "отмена",
        "другое",
        "погоди",
        "стой",
        "остановись",
        "не это",
        "не то"
    ]

    return any(
        t in l
        for t in triggers
    )


# =====================================================
# 🧠 SAFE TASK SEARCH
# =====================================================

def find_explicit_task(
    history: list
):

    if not history:
        return None

    # =================================================
    # 🔥 SEARCH ONLY RECENT
    # =================================================

    recent = history[-6:]

    for msg in reversed(recent):

        text = msg.get(
            "content",
            ""
        )

        if is_explicit(text):

            return text

    return None


# =====================================================
# 🧠 MAIN RESOLVER
# =====================================================

def resolve_input(
    history: list,
    state: dict = None
):

    """
    DeepHub logic:

    Resolver НЕ должен:
    - forcing execute;
    - resurrect old tasks;
    - override active scene;
    - break continuation.

    Resolver only suggests.
    """

    state = state or {}

    active_flow = state.get(
        "active_flow",
        {}
    )

    if not history:

        return {

            "mode": "dialog",

            "text": "",

            "confidence": 0.0,

            "source": "empty"
        }

    last = history[-1].get(
        "content",
        ""
    )

    task = find_explicit_task(
        history
    )

    t = normalize(last)

    # =================================================
    # 🔥 HARD CANCEL
    # =================================================

    if contradicts(last, task):

        return {

            "mode": "dialog",

            "text": last,

            "confidence": 0.9,

            "source": "contradiction"
        }

    # =================================================
    # 🔥 CONTINUATION PRIORITY
    # =================================================

    if is_reference(last):

        if active_flow:

            return {

                "mode": "continuation",

                "text": last,

                "confidence": 0.82,

                "source": "active_flow"
            }

        if task:

            return {

                "mode": "soft_execute",

                "text": task,

                "confidence": 0.62,

                "source": "reference_task"
            }

        return {

            "mode": "dialog",

            "text": last,

            "confidence": 0.55,

            "source": "reference_dialog"
        }

    # =================================================
    # 🔥 EXPLICIT EXECUTION
    # =================================================

    if is_explicit(last):

        return {

            "mode": "execute",

            "text": last,

            "confidence": 0.9,

            "source": "explicit"
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

                "mode": "continuation",

                "text": last,

                "confidence": 0.74,

                "source": "trajectory"
            }

    # =================================================
    # 🔥 SAFE TASK CONTINUATION
    # =================================================

    if task:

        # 🔥 DeepHub:
        # больше НЕ forcing execute

        return {

            "mode": "soft_execute",

            "text": task,

            "confidence": 0.45,

            "source": "memory_task"
        }

    # =================================================
    # 🔥 DEFAULT DIALOG
    # =================================================

    return {

        "mode": "dialog",

        "text": last,

        "confidence": 0.5,

        "source": "default"
    }
