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
- trajectory-aware assistant;
- semantic continuity bridge;
- machine-context stabilizer.

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
# 🧠 MACHINE TASK PACKAGING
# =====================================================

def build_machine_task(
    text: str,
    mode: str = "generic"
):

    normalized = normalize(text)

    return {

        "raw": text,

        "normalized": normalized,

        "mode": mode,

        "semantic_ready": True,

        "continuation_safe": True,

        "machine_context": {

            "length": len(normalized),

            "contains_math":
                any(
                    x in normalized
                    for x in [
                        "=",
                        "+",
                        "-",
                        "*",
                        "/",
                        "sin",
                        "cos",
                        "tan"
                    ]
                ),

            "contains_visual":
                any(
                    x in normalized
                    for x in [
                        "картин",
                        "изображ",
                        "фото",
                        "схема",
                        "график"
                    ]
                )
        }
    }


# =====================================================
# 🧠 EXPLICIT EXECUTION
# =====================================================

def is_explicit(
    text: str
) -> bool:

    t = normalize(text)

    if not t:
        return False

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

    recent = history[-10:]

    for msg in reversed(recent):

        text = msg.get(
            "content",
            ""
        )

        if is_explicit(text):

            return build_machine_task(

                text=text,

                mode="explicit_task"
            )

    return None


# =====================================================
# 🧠 MAIN RESOLVER
# =====================================================

def resolve_input(
    history: list,
    state: dict = None
):

    """
    Resolver НЕ форсит execution.
    Resolver удерживает trajectory
    и semantic continuity.
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

            "source": "empty",

            "machine_context": {}
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

    if contradicts(

        last,

        task["raw"]
        if task else ""

    ):

        return {

            "mode": "dialog",

            "text": last,

            "confidence": 0.9,

            "source": "contradiction",

            "machine_context": {

                "trajectory_reset": True
            }
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

                "source": "active_flow",

                "machine_context": {

                    "trajectory_active": True,

                    "flow_type":
                        active_flow.get(
                            "type"
                        )
                }
            }

        if task:

            return {

                "mode": "soft_execute",

                "text":
                    task["raw"],

                "confidence": 0.62,

                "source": "reference_task",

                "machine_task":
                    task,

                "machine_context": {

                    "semantic_restore": True,

                    "trajectory_resume": True,

                    "restore_type":
                        task.get(
                            "mode"
                        )
                }
            }

        return {

            "mode": "dialog",

            "text": last,

            "confidence": 0.55,

            "source": "reference_dialog",

            "machine_context": {

                "light_continuation": True
            }
        }

    # =================================================
    # 🔥 EXPLICIT EXECUTION
    # =====================================================

    if is_explicit(last):

        return {

            "mode": "execute",

            "text": last,

            "confidence": 0.9,

            "source": "explicit",

            "machine_task":
                build_machine_task(

                    last,

                    mode="execution"
                ),

            "machine_context": {

                "execution_ready": True
            }
        }

    # =================================================
    # 🔥 ACTIVE FLOW PROTECTION
    # =====================================================

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

                "source": "trajectory",

                "machine_context": {

                    "trajectory_locked": True,

                    "flow_type": flow_type
                }
            }

    # =================================================
    # 🔥 SAFE TASK CONTINUATION
    # =====================================================

    if task:

        return {

            "mode": "soft_execute",

            "text":
                task["raw"],

            "confidence": 0.45,

            "source": "memory_task",

            "machine_task":
                task,

            "machine_context": {

                "semantic_memory_restore": True,

                "trajectory_soft_resume": True,

                "machine_only": True
            }
        }

    # =================================================
    # 🔥 DEFAULT DIALOG
    # =====================================================

    return {

        "mode": "dialog",

        "text": last,

        "confidence": 0.5,

        "source": "default",

        "machine_context": {

            "dialog_safe": True
        }
    }
