# =========================================================
# 🌐 APRIL WEB ROUTER CORE
# =========================================================

"""
APRIL WEB ROUTER CORE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GOLDEN WEB ARCHITECTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file is now:

✅ human ↔ machine translator
✅ multimodal transport router
✅ renderer-safe web bridge
✅ continuity-safe response gateway
✅ machine payload stabilizer
✅ scene continuity synchronizer
✅ modality transport layer
✅ structured response organizer

This file is NOT:

❌ intelligence core
❌ reasoning engine
❌ room orchestrator
❌ trigger dispatcher
❌ semantic analyzer
❌ frontend renderer
❌ telegram transport

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 GOLDEN FLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User
 ↓
Web Router
 ↓
Human → Machine Translation
 ↓
Executor
 ↓
Rooms
 ↓
Machine Response
 ↓
Machine → Human Translation
 ↓
Structured Web Payload
 ↓
Renderer Space

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 GOLDEN PRINCIPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Web router NEVER decides cognition.

2. Executor owns orchestration.

3. Rooms NEVER communicate directly
with Web layer.

4. Human language NEVER enters
machine routing directly.

5. Renderer payloads are sacred.

Never flatten:
- graph
- formula
- table
- diagram
- layout
- scene
- visual blocks

6. Scene continuity must survive
between requests.

7. Web transport must remain lightweight.

8. Multimedia responses must preserve
machine structure integrity.
"""

# =========================================================
# 🔥 CORE IMPORTS
# =========================================================

import asyncio
import json
import os
import re
import traceback

from datetime import datetime

from flask import (
    request,
    jsonify
)

# =========================================================
# 🧠 EXECUTOR
# =========================================================

from core.executor import execute

# =========================================================
# 🧠 STATE
# =========================================================

from blocks.state_manager import (
    get_state
)

# =========================================================
# 🌐 SERVER
# =========================================================

from checkout_server import app

# =========================================================
# 🔥 CONFIG
# =========================================================

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY"
)

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

CHECKOUT_DOMAIN = os.getenv(
    "CHECKOUT_DOMAIN",
    "https://aprill.site"
)

# =========================================================
# 🔥 RENDERER TYPES
# =========================================================

RENDERER_TYPES = [

    "graph",
    "formula",
    "diagram",
    "scene",
    "layout",
    "visual",
    "renderer_scene",
    "table",
    "gallery"
]

# =========================================================
# 🔥 MACHINE LEAK FILTER
# =========================================================

MACHINE_PATTERNS = [

    r"machine_state",
    r"execution_pressure",
    r"internal_noise",
    r"signal_overload",
    r"trajectory_locked",
    r"continuity_strength",
    r"routing_chains",
    r"reasoning_state",
    r"executor",
    r"semantic_core",
    r"traceback",
    r"syntaxerror",
    r"machine_channel",
    r"response_decision",
    r"cognition",
    r"semantic",
    r"task_channel",
    r"response_channel"
]

# =========================================================
# 🔥 HELPERS
# =========================================================

def safe_string(value):

    if value is None:
        return ""

    return str(value)


def safe_truncate(
    text,
    limit=4000
):

    text = safe_string(text)

    if len(text) <= limit:
        return text

    return text[:limit] + "..."

# =========================================================
# 🔥 MACHINE CLEANER
# =========================================================

def remove_machine_garbage(
    text
):

    text = safe_string(text)

    if not text:
        return ""

    lines = text.splitlines()

    cleaned = []

    for line in lines:

        lowered = line.lower()

        blocked = False

        for pattern in MACHINE_PATTERNS:

            if re.search(

                pattern,

                lowered,

                re.IGNORECASE
            ):

                blocked = True
                break

        if not blocked:

            cleaned.append(line)

    text = "\n".join(cleaned)

    text = re.sub(
        r"\{[^\}]*machine[^\}]*\}",
        "",
        text,
        flags=re.IGNORECASE
    )

    return text.strip()

# =========================================================
# 🔥 HUMAN TRANSLATOR
# =========================================================

def machine_to_human(
    payload,
    result_type="text"
):

    if not isinstance(
        payload,
        str
    ):

        return payload

    if result_type in RENDERER_TYPES:

        return payload

    payload = remove_machine_garbage(
        payload
    )

    replacements = {

        "необходимо": "нужно",

        "следует": "лучше",

        "рекомендуется": "можно",

        "представлено": "видно"
    }

    for old, new in replacements.items():

        payload = payload.replace(
            old,
            new
        )

    return safe_truncate(
        payload,
        3000
    )


# =========================================================
# 🔥 ARTIFACT → HUMAN
# =========================================================

ARTIFACT_PRIORITY_FIELDS = [

    "answer",
    "response",
    "content",
    "summary",
    "analysis",
    "description",
    "result",
    "research_summary",
    "observation_report",
    "topic"
]


def extract_artifact_payload(
    artifact
):

    if artifact is None:
        return {}

    if isinstance(
        artifact,
        dict
    ):
        return artifact

    if hasattr(
        artifact,
        "data"
    ):
        payload = getattr(
            artifact,
            "data",
            {}
        )

        if isinstance(
            payload,
            dict
        ):
            return payload

    return {}


def artifact_to_human(
    artifact
):

    payload = extract_artifact_payload(
        artifact
    )

    for field in ARTIFACT_PRIORITY_FIELDS:

        value = payload.get(field)

        if value:

            return {

                "type":
                    "artifact",

                "content":
                    machine_to_human(
                        str(value)
                    ),

                "artifact":
                    payload
            }

    return {

        "type":
            "artifact",

        "content":
            machine_to_human(
                str(payload)
            ),

        "artifact":
            payload
    }


# =========================================================
# 🔥 HUMAN → MACHINE
# =========================================================

def human_to_machine(
    text,
    user_id
):

    state = get_state(
        user_id
    )

    scene_state = state.get(
        "scene_state",
        {}
    )

    active_visual_scene = state.get(
        "active_visual_scene"
    )

    return {

        "human_text":
            text,

        "machine_text":
            text,

        "trajectory":
            scene_state.get(
                "trajectory"
            ),

        "continuity_mode":
            scene_state.get(
                "continuity_mode"
            ),

        "active_visual_scene":
            active_visual_scene,

        "machine_transport":
            "web_router"
    }


# =========================================================
# 🔥 SAFE VOICE PAYLOAD
# =========================================================
def normalize_voice_text(value):
    """
    Voice pipeline may now return either a string or a machine dict.
    Always extract a safe text payload before calling .strip().
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("text","content","response","data"):
            v = value.get(key)
            if isinstance(v, str):
                return v.strip()
        return ""
    return str(value).strip()


# =========================================================
# 🔥 RESPONSE NORMALIZER
# =========================================================

def normalize_executor_response(
    result
):

    result = result or {}

    normalized = {

        "type":
            result.get(
                "type",
                "text"
            ),

        "content":
            result.get(
                "content"
            ),

        "response":
            result.get(
                "response"
            ),

        "data":
            result.get(
                "data"
            ),

        "blocks":
            result.get(
                "blocks",
                []
            ),

        "scene":
            result.get(
                "scene"
            ),

        "layout":
            result.get(
                "layout"
            ),

        "visual":
            result.get(
                "visual"
            ),

        "graph":
            result.get(
                "graph"
            ),

        "formula":
            result.get(
                "formula"
            ),

        "table":
            result.get(
                "table"
            ),

        "gallery":
            result.get(
                "gallery"
            ),

        "links":
            result.get(
                "links",
                []
            )
    }

    final_text = (

        normalized.get("content")

        or normalized.get("response")

        or (

            normalized.get("data")

            if isinstance(
                normalized.get("data"),
                str
            )

            else ""
        )

        or ""
    )

    normalized["final_text"] = final_text

    return normalized

# =========================================================
# 🔥 SCENE CONTINUITY
# =========================================================

def synchronize_scene_continuity(
    user_id,
    result
):

    state = get_state(
        user_id
    )

    has_visual = any([

        result.get("scene"),

        result.get("layout"),

        result.get("visual"),

        result.get("graph"),

        result.get("formula"),

        result.get("gallery")
    ])

    if not has_visual:
        return

    state["active_visual_scene"] = {

        "updated":
            datetime.now().isoformat(),

        "scene":
            result.get("scene"),

        "layout":
            result.get("layout"),

        "visual":
            result.get("visual"),

        "graph":
            result.get("graph"),

        "formula":
            result.get("formula"),

        "gallery":
            result.get("gallery"),

        "continuity_active":
            True
    }

# =========================================================
# 🔥 BLOCK NORMALIZER
# =========================================================

def normalize_blocks(
    blocks
):

    if not isinstance(
        blocks,
        list
    ):

        return []

    normalized = []

    for index, block in enumerate(blocks):

        if not isinstance(
            block,
            dict
        ):

            continue

        normalized.append({

            "type":
                block.get(
                    "type",
                    "text"
                ),

            "content":
                block.get(
                    "content"
                ),

            "graph":
                block.get(
                    "graph"
                ),

            "formula":
                block.get(
                    "formula"
                ),

            "scene":
                block.get(
                    "scene"
                ),

            "layout":
                block.get(
                    "layout"
                ),

            "visual":
                block.get(
                    "visual"
                ),

            "gallery":
                block.get(
                    "gallery"
                ),

            "image":
                block.get(
                    "image"
                ),

            "table":
                block.get(
                    "table"
                ),

            "continuation":
                block.get(
                    "continuation",
                    False
                ),

            "topic_group":
                block.get(
                    "topic_group"
                ),

            "sequence_index":
                block.get(
                    "sequence_index",
                    index
                )
        })

    return normalized

# =========================================================
# 🔥 MULTIMODAL ORGANIZER
# =========================================================

def organize_multimodal_response(
    result
):

    result_type = result.get(
        "type",
        "text"
    )

    final_text = machine_to_human(

        result.get(
            "final_text",
            ""
        ),

        result_type
    )

    organized = {

        "response":
            final_text,

        "type":
            result_type,

        "blocks":
            normalize_blocks(
                result.get(
                    "blocks",
                    []
                )
            ),

        "graph":
            result.get(
                "graph"
            ),

        "formula":
            result.get(
                "formula"
            ),

        "scene":
            result.get(
                "scene"
            ),

        "layout":
            result.get(
                "layout"
            ),

        "visual":
            result.get(
                "visual"
            ),

        "table":
            result.get(
                "table"
            ),

        "gallery":
            result.get(
                "gallery"
            ),

        "links":
            result.get(
                "links",
                []
            )
    }

    return organized

# =========================================================
# 🔥 APRIL REQUEST
# =========================================================

async def process_april_request(

    user_id,
    text
):

    # =====================================================
    # 🔥 HUMAN → MACHINE
    # =====================================================

    machine_request = human_to_machine(

        text,

        user_id
    )

    # =====================================================
    # 🔥 EXECUTOR
    # =====================================================

    # APRIL STABILIZATION PATCH
    # Do not pass None into Executor rooms pipeline.
    async def run_with_activity(chat_id, coro):
        return await coro

    result = await execute(

        user_id=user_id,

        text=machine_request[
            "machine_text"
        ],

        chat_id=0,

        run_with_activity=run_with_activity
    )

    # =====================================================
    # 🔥 NORMALIZE
    # =====================================================

    normalized = normalize_executor_response(
        result
    )

    # =====================================================
    # 🔥 CONTINUITY
    # =====================================================

    synchronize_scene_continuity(

        user_id,

        normalized
    )

    # =====================================================
    # 🔥 MACHINE → HUMAN
    # =====================================================

    organized = organize_multimodal_response(
        normalized
    )

    return organized

# =========================================================
# 🌐 CHAT ENDPOINT
# =========================================================

@app.route(
    "/chat",
    methods=["POST"]
)
def april_web_chat():

    try:

        data = request.json or {}

        user_id = str(

            data.get(
                "user_id",
                "web_user"
            )
        )

        text = normalize_voice_text(data.get("text", ""))

        result = asyncio.run(

            process_april_request(

                user_id,

                text
            )
        )

        return jsonify({

            "success": True,

            "response":
                result.get(
                    "response"
                ),

            "type":
                result.get(
                    "type"
                ),

            "blocks":
                result.get(
                    "blocks",
                    []
                ),

            "graph":
                result.get(
                    "graph"
                ),

            "formula":
                result.get(
                    "formula"
                ),

            "scene":
                result.get(
                    "scene"
                ),

            "layout":
                result.get(
                    "layout"
                ),

            "visual":
                result.get(
                    "visual"
                ),

            "table":
                result.get(
                    "table"
                ),

            "gallery":
                result.get(
                    "gallery"
                ),

            "links":
                result.get(
                    "links",
                    []
                )
        })

    except Exception as e:

        traceback.print_exc()

        return jsonify({

            "success": False,

            "error": str(e)
        }), 500

# =========================================================
# 🚀 START
# =========================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=int(
            os.environ.get(
                "PORT",
                10000
            )
        ),

        debug=False,

        use_reloader=False
    )
