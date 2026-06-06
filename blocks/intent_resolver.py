# =====================================================
# 🧠 APRIL INTENT RESOLVER
# =====================================================

"""
APRIL_FILE_ID:
APRIL_INTENT_RESOLVER

ROLE:
TRAJECTORY_SAFE_INTENT_RESOLVER

INPUT:
DIALOG_HISTORY
SESSION_STATE
ACTIVE_FLOW
SEMANTIC_CONTEXT

OUTPUT:
RESOLVED_INTENT_STATE
MACHINE_TASK
TRAJECTORY_CONTINUITY_STATE

=====================================================

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

=====================================================

Главный authority:
- cognition
- semantic_core
- active_flow
- response_decision

=====================================================

GOLDEN APRIL PRINCIPLE:

Resolver НЕ принимает решение.
Resolver помогает orchestration continuity.
"""

import re
import time

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

INPUT_MACHINE_CHANNEL = {

    "source":
        "executor_semantic_pipeline",

    "type":
        "intent_resolution_input",

    "isolated":
        True
}

OUTPUT_MACHINE_CHANNEL = {

    "target":
        "executor_orchestration_pipeline",

    "type":
        "intent_resolution_output",

    "isolated":
        True
}

# =====================================================
# 🔥 MACHINE LOGS
# =====================================================

INTENT_RESOLVER_LOGS = []

MAX_INTENT_RESOLVER_LOGS = 120


def log_resolver_event(
    event,
    payload=None
):

    try:

        INTENT_RESOLVER_LOGS.append({

            "timestamp":
                time.time(),

            "event":
                event,

            "payload":
                payload or {},

            "file_id":
                "APRIL_INTENT_RESOLVER",

            "machine_only":
                True
        })

        if len(INTENT_RESOLVER_LOGS) > MAX_INTENT_RESOLVER_LOGS:

            INTENT_RESOLVER_LOGS.pop(0)

    except:
        pass

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

    payload = {

        "raw":
            text,

        "normalized":
            normalized,

        "mode":
            mode,

        "semantic_ready":
            True,

        "continuation_safe":
            True,

        "machine_context": {

            "length":
                len(normalized),

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
        },

        # =================================================
        # 🔥 MACHINE FLAGS
        # =====================================================

        "machine_only":
            True
    }

    log_resolver_event(

        "machine_task_created",

        {

            "mode":
                mode,

            "normalized":
                normalized[:80]
        }
    )

    return payload

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

        log_resolver_event(
            "explicit_keyword_detected"
        )

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

            log_resolver_event(

                "explicit_pattern_detected",

                {
                    "pattern":
                        pattern
                }
            )

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

        log_resolver_event(
            "reference_detected"
        )

        return True

    if len(t) <= 20:

        if any(
            x in t
            for x in continuation_words
        ):

            log_resolver_event(
                "short_reference_detected"
            )

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

    detected = any(
        t in l
        for t in triggers
    )

    if detected:

        log_resolver_event(
            "contradiction_detected"
        )

    return detected

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

            log_resolver_event(
                "explicit_task_restored"
            )

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

    log_resolver_event(
        "resolver_started"
    )

    state = state or {}

    active_flow = state.get(
        "active_flow",
        {}
    )

    if not history:

        return {

            "mode":
                "dialog",

            "text":
                "",

            "confidence":
                0.0,

            "source":
                "empty",

            "machine_context":
                {},

            "machine_only":
                True
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
    # =====================================================

    if contradicts(

        last,

        task["raw"]
        if task else ""

    ):

        log_resolver_event(
            "trajectory_reset"
        )

        return {

            "mode":
                "dialog",

            "text":
                last,

            "confidence":
                0.9,

            "source":
                "contradiction",

            "machine_context": {

                "trajectory_reset":
                    True
            },

            "machine_only":
                True
        }

    # =================================================
    # 🔥 CONTINUATION PRIORITY
    # =====================================================

    if is_reference(last):

        if active_flow:

            flow_type = active_flow.get(
                "type"
            )

            log_resolver_event(

                "active_flow_continuation",

                {
                    "flow_type":
                        flow_type
                }
            )

            return {

                "mode":
                    "continuation",

                "text":
                    last,

                "confidence":
                    0.82,

                "source":
                    "active_flow",

                "machine_context": {

                    "trajectory_active":
                        True,

                    "flow_type":
                        flow_type
                },

                "machine_only":
                    True
            }

        if task:

            log_resolver_event(
                "semantic_restore"
            )

            return {

                "mode":
                    "soft_execute",

                "text":
                    task["raw"],

                "confidence":
                    0.62,

                "source":
                    "reference_task",

                "machine_task":
                    task,

                "machine_context": {

                    "semantic_restore":
                        True,

                    "trajectory_resume":
                        True,

                    "restore_type":
                        task.get(
                            "mode"
                        )
                },

                "machine_only":
                    True
            }

        return {

            "mode":
                "dialog",

            "text":
                last,

            "confidence":
                0.55,

            "source":
                "reference_dialog",

            "machine_context": {

                "light_continuation":
                    True
            },

            "machine_only":
                True
        }

    # =================================================
    # 🔥 EXPLICIT EXECUTION
    # =====================================================

    if is_explicit(last):

        log_resolver_event(
            "explicit_execution"
        )

        return {

            "mode":
                "execute",

            "text":
                last,

            "confidence":
                0.9,

            "source":
                "explicit",

            "machine_task":
                build_machine_task(

                    last,

                    mode="execution"
                ),

            "machine_context": {

                "execution_ready":
                    True
            },

            "machine_only":
                True
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

            log_resolver_event(

                "trajectory_protection",

                {
                    "flow_type":
                        flow_type
                }
            )

            return {

                "mode":
                    "continuation",

                "text":
                    last,

                "confidence":
                    0.74,

                "source":
                    "trajectory",

                "machine_context": {

                    "trajectory_locked":
                        True,

                    "flow_type":
                        flow_type
                },

                "machine_only":
                    True
            }

    # =================================================
    # 🔥 SAFE TASK CONTINUATION
    # =====================================================

    if task:

        log_resolver_event(
            "memory_task_restore"
        )

        return {

            "mode":
                "soft_execute",

            "text":
                task["raw"],

            "confidence":
                0.45,

            "source":
                "memory_task",

            "machine_task":
                task,

            "machine_context": {

                "semantic_memory_restore":
                    True,

                "trajectory_soft_resume":
                    True,

                "machine_only":
                    True
            },

            "machine_only":
                True
        }

    # =================================================
    # 🔥 DEFAULT DIALOG
    # =====================================================

    log_resolver_event(
        "default_dialog"
    )

    return {

        "mode":
            "dialog",

        "text":
            last,

        "confidence":
            0.5,

        "source":
            "default",

        "machine_context": {

            "dialog_safe":
                True
        },

        "machine_only":
            True
    }


# =====================================================
# 🧠 DYNAMIC FOCUS INTENT UPGRADE
# =====================================================

def detect_focus_shift(text, state):

    focus = state.get("dynamic_focus", {})

    primary = str(
        focus.get("primary_focus", "")
    ).lower()

    current = normalize(text)

    if not primary:
        return False

    overlap = 0

    for word in primary.split():
        if len(word) >= 4 and word in current:
            overlap += 1

    return overlap == 0


def build_focus_intent_state(text, state):

    shifted = detect_focus_shift(
        text,
        state or {}
    )

    return {
        "focus_shift_detected": shifted,
        "focus_priority": not shifted,
        "requires_focus_refresh": shifted
    }
