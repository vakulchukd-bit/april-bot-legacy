# =========================================================
# 🧠 APRIL SPACE RENDER BRIDGE CORE
# =========================================================

"""
APRIL SPACE RENDER BRIDGE CORE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ROLE IN APRIL:
This file is the render bridge layer
between April cognition and April Web Space.

This helper core transforms:
- cognitive objects
- semantic structures
- scene payloads
- renderer blocks
- execution visuals

into:
- stable Web render objects
- renderer-safe structures
- multi-block layouts
- continuity-safe scene payloads

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 WHAT THIS FILE IS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file IS:
- render bridge core
- scene packaging layer
- renderer object formatter
- Web-space preparation system
- semantic visual formatter
- continuity-safe visual packaging layer

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 WHAT THIS FILE IS NOT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file is NOT:
- renderer engine
- frontend renderer
- Telegram formatter
- personality system
- orchestration layer
- governance system
- routing system
- analytics system
- cognition engine

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 APRIL ARCHITECTURE POSITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BotRoot
 ↓
Executor
 ↓
Execution Rooms
 ↓
Render Bridge Core (THIS FILE)
 ↓
Web Renderer Space

Executor thinks.
Rooms generate cognition.
This file packages cognition into render structures.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 GOLDEN MACHINE CHANNEL RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file uses TWO isolated channels.

1. RENDER TASK CHANNEL
Executor/Rooms → Render Bridge

2. RENDER RESPONSE CHANNEL
Render Bridge → BotRoot/Web Renderer

Human-facing rendering NEVER mixes
with internal cognition orchestration.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 GOLDEN APRIL RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. cognition before rendering
2. renderer before heavy visuals
3. continuity before fragmentation
4. semantic structure before beautification
5. Web-space first
6. multi-block stability
7. renderer-safe payloads
8. no cognition leakage
9. no system leakage
10. no renderer chaos

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 IMPORTANT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DO NOT RE-ADD:
- Telegram formatting
- aiogram logic
- personality narration
- orchestration logic
- frontend rendering logic
- cognition logic
- analytics logic
- governance logic

This file must remain:
- lightweight
- renderer-safe
- structure-focused
- Web-oriented
- continuity-safe
- Executor-compatible
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
# 🧠 TEXT BLOCK
# =========================================================

def format_text(content):

    """
    Lightweight text normalization.

    Does NOT beautify.
    Does NOT narrate.
    """

    return safe_text(content)

# =========================================================
# 🧠 CODE BLOCK
# =========================================================

def format_code_block(

    content,
    file_name=None,
    block_name=None
):

    """
    Packages structured code blocks
    for Web-space rendering.
    """

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

    return {

        "channel":
            RENDER_RESPONSE_CHANNEL,

        "type":
            "code_block",

        "payload": (
            f"{header}{content}"
        )
    }

# =========================================================
# 🧠 FORMULA BLOCK
# =========================================================

def format_formula_block(

    formula,
    label="FORMULA"
):

    """
    Packages renderer-safe formulas
    for Web-space rendering.
    """

    formula = safe_text(formula)

    if not formula:

        return None

    return {

        "channel":
            RENDER_RESPONSE_CHANNEL,

        "type":
            "formula",

        "payload": {

            "label":
                label,

            "content":
                formula
        }
    }

# =========================================================
# 🧠 GRAPH BLOCK
# =========================================================

def format_graph_block(

    graph,
    title="GRAPH"
):

    """
    Packages graph objects
    for Web renderer space.
    """

    graph = safe_text(graph)

    if not graph:

        return None

    return {

        "channel":
            RENDER_RESPONSE_CHANNEL,

        "type":
            "graph",

        "payload": {

            "title":
                title,

            "content":
                graph
        }
    }

# =========================================================
# 🧠 TABLE BLOCK
# =========================================================

def format_table_block(

    rows,
    title="TABLE"
):

    """
    Packages structured table payloads
    for Web rendering.
    """

    rows = rows or []

    return {

        "channel":
            RENDER_RESPONSE_CHANNEL,

        "type":
            "table",

        "payload": {

            "title":
                title,

            "rows":
                rows
        }
    }

# =========================================================
# 🧠 SCENE OBJECT
# =========================================================

def format_scene_object(

    object_type,
    content="",
    meta=None
):

    """
    Packages semantic scene objects
    for April Space continuity rendering.
    """

    object_type = safe_text(
        object_type
    )

    content = safe_text(
        content
    )

    meta = meta or {}

    if not object_type:

        return None

    return {

        "channel":
            RENDER_RESPONSE_CHANNEL,

        "type":
            "scene_object",

        "payload": {

            "object_type":
                object_type,

            "content":
                content,

            "meta":
                meta
        }
    }

# =========================================================
# 🧠 MULTI-BLOCK RESPONSE
# =========================================================

def build_multi_block_response(

    blocks,
    continuity_id=None
):

    """
    Packages ordered multi-block
    Web-space render structures.

    Used for:
    - complex responses
    - multi-question dialogs
    - renderer continuity
    - structured Web presentation
    """

    blocks = blocks or []

    return {

        "channel":
            RENDER_RESPONSE_CHANNEL,

        "type":
            "multi_block_scene",

        "continuity_id":
            continuity_id,

        "blocks":
            blocks
    }

# =========================================================
# 🧠 RENDERER SAFE PAYLOAD
# =========================================================

def build_renderer_payload(

    payload_type,
    payload,
    continuity=None
):

    """
    Unified renderer-safe payload builder.

    Prevents:
    - renderer fragmentation
    - structure chaos
    - cognition leakage
    - inconsistent rendering
    """

    return {

        "channel":
            RENDER_RESPONSE_CHANNEL,

        "renderer_safe":
            True,

        "payload_type":
            payload_type,

        "continuity":
            continuity,

        "payload":
            payload
    }

# =========================================================
# 🧠 CONTINUITY RENDER STATE
# =========================================================

def build_continuity_render_state(

    continuity_id,
    trajectory=None,
    active_scene=None
):

    """
    Continuity-safe render state
    for stable Web-space scenes.
    """

    return {

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
