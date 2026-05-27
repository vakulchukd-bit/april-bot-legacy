# blocks/event_system.py

# =====================================================
# 🧠 APRIL EVENT SYSTEM
# =====================================================

"""
Unified internal event layer.

Этот слой:

✅ удерживает continuity
✅ удерживает structured history
✅ удерживает semantic event flow
✅ помогает trajectory tracking
✅ помогает DeepHub context
✅ помогает executor continuity

❌ НЕ telegram formatter
❌ НЕ text beautifier
❌ НЕ trigger router
❌ НЕ legacy event logger

Главная задача:
единый machine-readable event flow.
"""

from blocks.state_manager import (

    add_dialog,

    update_memory_summary
)

# =====================================================
# 🔥 EVENT TYPES
# =====================================================

EVENT_USER = "user"

EVENT_ASSISTANT = "assistant"

EVENT_SYSTEM = "system"

EVENT_VISUAL = "visual"

EVENT_RENDER = "render"

EVENT_EXECUTION = "execution"

EVENT_MEMORY = "memory"

EVENT_SCENE = "scene"

EVENT_REASONING = "reasoning"

# =====================================================
# 🔥 VISUAL EVENTS
# =====================================================

VISUAL_EVENTS = {

    "graph",
    "diagram",
    "formula",
    "table",
    "scene",
    "image",
    "renderer",
    "visual"
}

# =====================================================
# 🔥 HELPERS
# =====================================================

def normalize_text(
    text
):

    return str(
        text or ""
    ).strip()


def normalize_lower(
    text
):

    return normalize_text(
        text
    ).lower()


def build_event_payload(

    role,
    event_type,
    content
):

    """
    Machine-readable event payload.

    ВАЖНО:
    event flow теперь строится
    НЕ через human trigger text,
    а через semantic structure.
    """

    return {

        "role":
            role,

        "event":
            event_type,

        "content":
            normalize_text(
                content
            ),

        "visual":

            event_type in VISUAL_EVENTS,

        "semantic":

            event_type in [

                EVENT_REASONING,
                EVENT_SCENE,
                EVENT_MEMORY
            ],

        "renderer":

            event_type in [

                EVENT_RENDER,
                "graph",
                "formula",
                "diagram",
                "scene"
            ]
    }


def build_dialog_trace(
    payload
):

    """
    Safe dialog trace.

    Нужен:
    - для continuity;
    - для state manager;
    - для debug visibility.

    НЕ должен:
    - ломать renderer blocks;
    - flatten renderer payload.
    """

    role = payload.get(
        "role",
        "unknown"
    )

    event_type = payload.get(
        "event",
        "unknown"
    )

    content = payload.get(
        "content",
        ""
    )

    return (

        f"[{event_type}] "

        f"{content}"
    )


# =====================================================
# 🔥 EVENT ENTRY
# =====================================================

def add_event(
    user_id,
    role,
    event_type,
    content
):

    """
    Unified semantic event entry.

    Flow:

    user/action
        ↓
    semantic payload
        ↓
    dialog continuity
        ↓
    memory continuity
        ↓
    DeepHub context
    """

    # =================================================
    # 🔥 PAYLOAD
    # =====================================================

    payload = build_event_payload(

        role,

        event_type,

        content
    )

    # =================================================
    # 🔥 SAFE TRACE
    # =====================================================

    dialog_trace = build_dialog_trace(
        payload
    )

    # =================================================
    # 🔥 DIALOG
    # =====================================================

    add_dialog(

        user_id,

        role,

        dialog_trace
    )

    # =================================================
    # 🔥 MEMORY
    # =====================================================

    update_memory_summary(

        user_id,

        dialog_trace
    )

    # =================================================
    # 🔥 RETURN PAYLOAD
    # =====================================================

    return payload
