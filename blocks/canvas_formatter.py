# =========================================================
# 🧠 APRIL SPACE RENDER BRIDGE CORE
# =========================================================

"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APRIL FILE ID
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

APRIL_FILE_ID:
APRIL_SPACE_RENDER_BRIDGE_CORE

ROLE:
RENDER_BRIDGE_AND_WEB_SPACE_PACKAGER

ROOM:
RENDER_BRIDGE_ROOM

INPUT:
EXECUTOR_RENDER_REQUEST
ROOM_RENDER_PAYLOAD
SEMANTIC_VISUAL_STRUCTURE
CONTINUITY_RENDER_STATE
MULTI_BLOCK_RESPONSE

OUTPUT:
RENDERER_SAFE_PAYLOAD
WEB_RENDER_OBJECT
CONTINUITY_SAFE_RENDER_STRUCTURE
ANALYZER_RENDER_TELEMETRY

DEPENDENCIES:
EXECUTOR
WEB_RENDERER
SPACE_RENDER_SYSTEM
CONTINUITY_SYSTEM
ANALYZER_SYSTEM

CRITICAL:
TRUE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 GOLDEN RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file NEVER:
- performs orchestration
- performs cognition
- formats frontend UI
- executes renderer logic

This file ONLY:
- packages render structures
- stabilizes visual continuity
- protects renderer payloads
- prepares Web-space objects
"""

# =========================================================
# 🧠 MACHINE CHANNELS
# =========================================================

RENDER_TASK_CHANNEL = {

    "channel":
        "render_bridge_machine_task_channel",

    "isolated":
        True
}

RENDER_RESPONSE_CHANNEL = {

    "channel":
        "render_bridge_machine_response_channel",

    "isolated":
        True
}

# =========================================================
# 🔥 APRIL TRACE LOGS
# =========================================================

def APRIL_LOG_IN(
    room,
    metadata=None
):

    try:

        print({

            "type":
                "APRIL_LOG_IN",

            "room":
                room,

            "file":
                "APRIL_SPACE_RENDER_BRIDGE_CORE",

            "metadata":
                metadata or {}
        })

    except Exception:
        pass


def APRIL_LOG_OUT(
    room,
    metadata=None
):

    try:

        print({

            "type":
                "APRIL_LOG_OUT",

            "room":
                room,

            "file":
                "APRIL_SPACE_RENDER_BRIDGE_CORE",

            "metadata":
                metadata or {}
        })

    except Exception:
        pass

# =========================================================
# 🧠 SAFE HELPERS
# =========================================================

def safe_text(value):

    """
    Safe renderer text normalization.
    """

    if value is None:
        return ""

    return str(value).strip()

# =========================================================
# 🧠 RENDER TELEMETRY
# =========================================================

def build_render_bridge_telemetry():

    APRIL_LOG_IN(

        "RENDER_BRIDGE_ROOM",

        {
            "action":
                "build_render_bridge_telemetry"
        }
    )

    payload = {

        "file_id":
            "APRIL_SPACE_RENDER_BRIDGE_CORE",

        "room":
            "RENDER_BRIDGE_ROOM",

        "renderer_safe":
            True,

        "continuity_safe":
            True,

        "multi_block_supported":
            True,

        "executor_connected":
            True,

        "web_space_connected":
            True
    }

    APRIL_LOG_OUT(

        "RENDER_BRIDGE_ROOM",

        {
            "telemetry":
                "ready"
        }
    )

    return payload

# =========================================================
# 🧠 TEXT BLOCK
# =========================================================

def format_text(content):

    APRIL_LOG_IN(

        "RENDER_BRIDGE_ROOM",

        {
            "action":
                "format_text"
        }
    )

    result = safe_text(content)

    APRIL_LOG_OUT(

        "RENDER_BRIDGE_ROOM",

        {
            "text":
                "formatted"
        }
    )

    return result

# =========================================================
# 🧠 CODE BLOCK
# =========================================================

def format_code_block(

    content,
    file_name=None,
    block_name=None
):

    APRIL_LOG_IN(

        "RENDER_BRIDGE_ROOM",

        {
            "action":
                "format_code_block"
        }
    )

    content = safe_text(content)

    header = ""

    if file_name:

        header += (
            f"# === file: "
            f"{file_name} ===\n"
        )

    if block_name:

        header += (
            f"# === block: "
            f"{block_name} ===\n\n"
        )

    payload = {

        "channel":
            RENDER_RESPONSE_CHANNEL,

        "type":
            "code_block",

        "renderer_safe":
            True,

        "payload": (
            f"{header}{content}"
        )
    }

    APRIL_LOG_OUT(

        "RENDER_BRIDGE_ROOM",

        {
            "code_block":
                "ready"
        }
    )

    return payload

# =========================================================
# 🧠 FORMULA BLOCK
# =========================================================

def format_formula_block(

    formula,
    label="FORMULA"
):

    APRIL_LOG_IN(

        "RENDER_BRIDGE_ROOM",

        {
            "action":
                "format_formula_block"
        }
    )

    formula = safe_text(formula)

    if not formula:

        return None

    payload = {

        "channel":
            RENDER_RESPONSE_CHANNEL,

        "type":
            "formula",

        "renderer_safe":
            True,

        "payload": {

            "label":
                label,

            "content":
                formula
        }
    }

    APRIL_LOG_OUT(

        "RENDER_BRIDGE_ROOM",

        {
            "formula":
                "ready"
        }
    )

    return payload

# =========================================================
# 🧠 GRAPH BLOCK
# =========================================================

def format_graph_block(

    graph,
    title="GRAPH"
):

    APRIL_LOG_IN(

        "RENDER_BRIDGE_ROOM",

        {
            "action":
                "format_graph_block"
        }
    )

    graph = safe_text(graph)

    if not graph:

        return None

    payload = {

        "channel":
            RENDER_RESPONSE_CHANNEL,

        "type":
            "graph",

        "renderer_safe":
            True,

        "payload": {

            "title":
                title,

            "content":
                graph
        }
    }

    APRIL_LOG_OUT(

        "RENDER_BRIDGE_ROOM",

        {
            "graph":
                "ready"
        }
    )

    return payload

# =========================================================
# 🧠 TABLE BLOCK
# =========================================================

def format_table_block(

    rows,
    title="TABLE"
):

    APRIL_LOG_IN(

        "RENDER_BRIDGE_ROOM",

        {
            "action":
                "format_table_block"
        }
    )

    rows = rows or []

    payload = {

        "channel":
            RENDER_RESPONSE_CHANNEL,

        "type":
            "table",

        "renderer_safe":
            True,

        "payload": {

            "title":
                title,

            "rows":
                rows
        }
    }

    APRIL_LOG_OUT(

        "RENDER_BRIDGE_ROOM",

        {
            "table":
                "ready"
        }
    )

    return payload

# =========================================================
# 🧠 SCENE OBJECT
# =========================================================

def format_scene_object(

    object_type,
    content="",
    meta=None
):

    APRIL_LOG_IN(

        "RENDER_BRIDGE_ROOM",

        {
            "action":
                "format_scene_object"
        }
    )

    object_type = safe_text(
        object_type
    )

    content = safe_text(
        content
    )

    meta = meta or {}

    if not object_type:

        return None

    payload = {

        "channel":
            RENDER_RESPONSE_CHANNEL,

        "type":
            "scene_object",

        "renderer_safe":
            True,

        "payload": {

            "object_type":
                object_type,

            "content":
                content,

            "meta":
                meta
        }
    }

    APRIL_LOG_OUT(

        "RENDER_BRIDGE_ROOM",

        {
            "scene_object":
                object_type
        }
    )

    return payload

# =========================================================
# 🧠 MULTI-BLOCK RESPONSE
# =========================================================

def build_multi_block_response(

    blocks,
    continuity_id=None
):

    APRIL_LOG_IN(

        "RENDER_BRIDGE_ROOM",

        {
            "action":
                "build_multi_block_response"
        }
    )

    blocks = blocks or []

    payload = {

        "channel":
            RENDER_RESPONSE_CHANNEL,

        "type":
            "multi_block_scene",

        "continuity_id":
            continuity_id,

        "renderer_safe":
            True,

        "blocks":
            blocks
    }

    APRIL_LOG_OUT(

        "RENDER_BRIDGE_ROOM",

        {
            "blocks":
                len(blocks)
        }
    )

    return payload

# =========================================================
# 🧠 RENDERER SAFE PAYLOAD
# =========================================================

def build_renderer_payload(

    payload_type,
    payload,
    continuity=None
):

    APRIL_LOG_IN(

        "RENDER_BRIDGE_ROOM",

        {
            "action":
                "build_renderer_payload",

            "payload_type":
                payload_type
        }
    )

    result = {

        "channel":
            RENDER_RESPONSE_CHANNEL,

        "renderer_safe":
            True,

        "payload_type":
            payload_type,

        "continuity":
            continuity,

        "payload":
            payload,

        "telemetry":
            build_render_bridge_telemetry()
    }

    APRIL_LOG_OUT(

        "RENDER_BRIDGE_ROOM",

        {
            "payload":
                payload_type
        }
    )

    return result

# =========================================================
# 🧠 CONTINUITY RENDER STATE
# =========================================================

def build_continuity_render_state(

    continuity_id,
    trajectory=None,
    active_scene=None
):

    APRIL_LOG_IN(

        "RENDER_BRIDGE_ROOM",

        {
            "action":
                "build_continuity_render_state"
        }
    )

    payload = {

        "channel":
            RENDER_RESPONSE_CHANNEL,

        "continuity_id":
            continuity_id,

        "trajectory":
            trajectory,

        "active_scene":
            active_scene,

        "continuity_active":
            True
    }

    APRIL_LOG_OUT(

        "RENDER_BRIDGE_ROOM",

        {
            "continuity":
                continuity_id
        }
    )

    return payload
