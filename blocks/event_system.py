# =====================================================
# 🧠 APRIL EVENT SYSTEM CORE
# =====================================================

"""
APRIL EVENT SYSTEM CORE

APRIL_FILE_ID:
APRIL_EVENT_SYSTEM_CORE

ROLE:
SEMANTIC_EVENT_CONTINUITY_AND_MACHINE_FLOW

INPUT:
USER_EVENTS
ASSISTANT_EVENTS
RENDER_EVENTS
SCENE_EVENTS
EXECUTION_EVENTS
MEMORY_EVENTS

OUTPUT:
MACHINE_READABLE_EVENT_PAYLOADS
DIALOG_CONTINUITY
MEMORY_CONTINUITY
DEEPHUB_EVENT_FLOW

THIS FILE IS:
- unified semantic event layer
- continuity stabilizer
- structured history system
- event trajectory helper
- DeepHub continuity bridge
- executor event support layer

THIS FILE IS NOT:
- telegram formatter
- frontend renderer
- beautifier
- trigger router
- orchestration authority
- legacy logger

GOLDEN APRIL RULES:
- continuity before fragmentation
- semantic structure before keywords
- renderer-safe event flow
- machine-readable architecture
- no renderer flattening
- no hidden rerouting
"""

from blocks.state_manager import (

    add_dialog,

    update_memory_summary
)

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

EVENT_TASK_CHANNEL = {

    "channel":
        "event_machine_task_channel",

    "isolated":
        True
}

EVENT_RESPONSE_CHANNEL = {

    "channel":
        "event_machine_response_channel",

    "isolated":
        True
}

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
# 🔥 EVENT LOGGING
# =====================================================

def build_event_input_log(

    role,
    event_type
):

    """
    INPUT MACHINE TRACE

    Used internally by:
    - continuity systems
    - diagnostics
    - DeepHub
    - governance
    """

    return {

        "file_id":
            "APRIL_EVENT_SYSTEM_CORE",

        "event":
            "event_input",

        "channel":
            EVENT_TASK_CHANNEL,

        "role":
            role,

        "event_type":
            event_type,

        "machine_only":
            True
    }


def build_event_output_log(
    payload
):

    """
    OUTPUT MACHINE TRACE

    Used internally by:
    - continuity systems
    - trajectory systems
    - machine analytics
    """

    return {

        "file_id":
            "APRIL_EVENT_SYSTEM_CORE",

        "event":
            "event_output",

        "channel":
            EVENT_RESPONSE_CHANNEL,

        "payload_type":
            payload.get(
                "event"
            ),

        "renderer":
            payload.get(
                "renderer",
                False
            ),

        "semantic":
            payload.get(
                "semantic",
                False
            ),

        "machine_only":
            True
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

# =====================================================
# 🔥 EVENT PAYLOAD
# =====================================================

def build_event_payload(

    role,
    event_type,
    content
):

    """
    Machine-readable semantic payload.

    Event flow now builds through:
    - semantic structure
    - renderer awareness
    - continuity-safe payloads

    NOT:
    - trigger words
    - telegram formatting
    """

    return {

        "channel":
            EVENT_RESPONSE_CHANNEL,

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
            ],

        "machine_only":
            True
    }

# =====================================================
# 🔥 DIALOG TRACE
# =====================================================

def build_dialog_trace(
    payload
):

    """
    Safe continuity trace.

    Used for:
    - state manager
    - continuity stabilization
    - memory trajectory
    - debug visibility

    MUST NOT:
    - flatten renderer payloads
    - destroy modality structure
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

    FLOW:

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

    build_event_input_log(

        role=role,

        event_type=event_type
    )

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
    # 🔥 DIALOG CONTINUITY
    # =====================================================

    add_dialog(

        user_id,

        role,

        dialog_trace
    )

    # =================================================
    # 🔥 MEMORY CONTINUITY
    # =====================================================

    update_memory_summary(

        user_id,

        dialog_trace
    )

    # =================================================
    # 🔥 MACHINE OUTPUT TRACE
    # =====================================================

    build_event_output_log(
        payload
    )

    # =================================================
    # 🔥 RETURN PAYLOAD
    # =====================================================

    return payload
