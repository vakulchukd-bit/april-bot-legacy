# =========================================================
# 🌐 APRIL WEB ROUTER CORE
# =========================================================

"""
APRIL WEB ROUTER CORE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ROLE IN APRIL:
This file is NOT the intelligence core of April.

This file works as:
- transport router
- machine ↔ human translator
- response organizer
- multimedia response formatter
- Web communication layer

APRIL ARCHITECTURE:
User
  ↓
Web Router Core (THIS FILE)
  ↓
Executor / ExtruderCore
  ↓
Internal April Systems
  ↓
Machine Response Assembly
  ↓
Web Router Core
  ↓
Human Structured Output

MAIN RESPONSIBILITIES:
- receive Web requests
- normalize user payloads
- forward tasks into April core
- distribute execution into April systems
- receive machine-formatted responses
- clean machine garbage
- organize multimedia responses
- structure complex multi-question outputs
- return human-readable Web payloads

THIS FILE MUST REMAIN LIGHTWEIGHT.

DO NOT RE-ADD:
- Telegram
- aiogram
- polling
- admin systems
- subscriptions
- premium logic
- heavy orchestration
- transport-side reasoning
- map scanners
- legacy payment systems
- transport AI execution

REAL INTELLIGENCE EXISTS INSIDE:
- core.executor
- ExtruderCore
- renderer systems
- memory systems
- reasoning systems
- tool systems
- scene systems

THIS FILE ONLY:
- routes
- cleans
- formats
- structures
- stabilizes
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

from openai import OpenAI

# =========================================================
# 🧠 APRIL EXECUTOR
# =========================================================

"""
Executor is the real intelligence entrypoint.

This router MUST NOT replace executor logic.
"""

from core.executor import execute

# =========================================================
# 🧠 STATE SYSTEM
# =========================================================

from blocks.state_manager import get_state

# =========================================================
# 🌐 WEB SERVER
# =========================================================

from checkout_server import app

# =========================================================
# 🔥 API CONFIGURATION
# =========================================================

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY"
)

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

# Payment credentials intentionally preserved
# for future Web monetization integration.

PAYPAL_CLIENT_ID = os.getenv(
    "PAYPAL_CLIENT_ID"
)

PAYPAL_SECRET = os.getenv(
    "PAYPAL_SECRET"
)

CHECKOUT_DOMAIN = os.getenv(
    "CHECKOUT_DOMAIN",
    "https://aprill.site"
)

# =========================================================
# 🧠 OPENAI CLIENT
# =========================================================

client = OpenAI(
    api_key=OPENAI_API_KEY
)

# =========================================================
# 🎨 RENDERER RESPONSE TYPES
# =========================================================

"""
These payloads are processed by frontend
renderer systems separately.
"""

RENDERER_RESPONSE_TYPES = [

    "graph",
    "formula",
    "diagram",
    "table",
    "scene",
    "gallery",
    "layout",
    "visual",
    "function",
    "renderer_scene"
]

# =========================================================
# 🧠 INTERNAL MACHINE FILTER
# =========================================================

"""
April internally operates using machine-oriented
execution language.

Machine internals must NEVER leak into
public Web responses.
"""

MACHINE_PATTERNS = [

    r"\[\[APRIL_RENDERER:",
    r"machine_state",
    r"execution_pressure",
    r"renderer_space",
    r"internal_noise",
    r"signal_overload",
    r"continuity_strength",
    r"orchestration",
    r"semantic_core",
    r"routing_chains",
    r"trajectory_locked",
    r"visual_memory",
    r"scene_stability",
    r"reasoning_state",
    r"executor",
    r"pipeline",
    r"traceback",
    r"syntaxerror",
]

# =========================================================
# 🔥 SAFE HELPERS
# =========================================================

def safe_string(value):

    """
    Prevents NoneType transport crashes.
    """

    if value is None:
        return ""

    return str(value)


def safe_truncate(
    text,
    limit=4000
):

    """
    Prevents oversized response payloads.
    """

    text = safe_string(text)

    if len(text) <= limit:
        return text

    return text[:limit] + "\n\n..."

# =========================================================
# 🧠 MACHINE GARBAGE CLEANER
# =========================================================

def remove_machine_garbage(text):

    """
    Removes internal machine garbage
    before returning responses to users.
    """

    text = safe_string(text)

    lines = text.splitlines()

    cleaned = []

    for line in lines:

        lower = line.lower()

        blocked = False

        for pattern in MACHINE_PATTERNS:

            if re.search(
                pattern.lower(),
                lower
            ):

                blocked = True
                break

        if blocked:
            continue

        cleaned.append(line)

    text = "\n".join(cleaned)

    text = re.sub(
        r"\{[^\}]*machine[^\}]*\}",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\[[^\]]*renderer[^\]]*\]",
        "",
        text,
        flags=re.IGNORECASE
    )

    return text.strip()

# =========================================================
# 🧠 HUMAN LANGUAGE NORMALIZER
# =========================================================

def cleanup_response_text(
    text,
    result_type="text"
):

    """
    Converts machine-heavy wording into
    cleaner human-readable communication.
    """

    text = safe_string(text)

    if result_type in RENDERER_RESPONSE_TYPES:
        return text

    text = remove_machine_garbage(text)

    replacements = {

        "необходимо": "нужно",
        "следует": "лучше",
        "рекомендуется": "можно",
        "представлено": "видно"
    }

    for old, new in replacements.items():

        text = text.replace(old, new)

    return safe_truncate(
        text,
        limit=3000
    )

# =========================================================
# 🎨 SCENE CONTINUITY
# =========================================================

def build_scene_state(
    result,
    user_id
):

    """
    Preserves visual continuity between
    Web interactions.
    """

    state = get_state(user_id)

    if not result:
        return

    has_scene = any([

        result.get("scene"),

        result.get("layout"),

        result.get("visual"),

        result.get("graph"),

        result.get("formula")
    ])

    if not has_scene:
        return

    state["active_visual_scene"] = {

        "updated":
            datetime.now().isoformat(),

        "continuity_mode":
            "active",

        "scene":
            result.get("scene"),

        "layout":
            result.get("layout"),

        "visual":
            result.get("visual"),

        "graph":
            result.get("graph"),

        "formula":
            result.get("formula")
    }

# =========================================================
# 🧠 RESPONSE NORMALIZATION
# =========================================================

def normalize_result_payload(result):

    """
    Converts internal executor payloads
    into stable transport-safe structures.
    """

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
            ),

        "blocks":
            result.get(
                "blocks",
                []
            ),

        "sections":
            result.get(
                "sections",
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

    normalized["final_text"] = remove_machine_garbage(
        final_text
    )

    return normalized

# =========================================================
# 🧠 MULTIMEDIA RESPONSE ORGANIZER
# =========================================================

def organize_multimedia_response(result):

    """
    Core multimedia organization layer.

    This function transforms machine payloads
    into structured human-readable Web responses.

    Supports:
    - multiple questions
    - multiple tasks
    - renderer blocks
    - tables
    - links
    - scenes
    - visual sections
    - ordered response grouping
    """

    organized = {

        "response": cleanup_response_text(

            result.get(
                "final_text",
                ""
            ),

            result.get(
                "type",
                "text"
            )
        ),

        "sections": [],

        "visual_blocks": [],

        "tables": [],

        "graphs": [],

        "formulas": [],

        "links": [],

        "gallery": [],

        "scenes": []
    }

    # =====================================================
    # STRUCTURED BLOCKS
    # =====================================================

    for block in result.get("blocks", []):

        organized["sections"].append({

            "type":
                block.get(
                    "type",
                    "text"
                ),

            "title":
                block.get(
                    "title",
                    ""
                ),

            "content":
                cleanup_response_text(

                    block.get(
                        "content",
                        ""
                    )
                )
        })

    # =====================================================
    # TABLES
    # =====================================================

    if result.get("table"):

        organized["tables"].append(
            result.get("table")
        )

    # =====================================================
    # LINKS
    # =====================================================

    if result.get("links"):

        organized["links"] = result.get(
            "links",
            []
        )

    # =====================================================
    # VISUALS
    # =====================================================

    if result.get("visual"):

        organized["visual_blocks"].append({

            "type": "visual",
            "payload": result.get("visual")
        })

    # =====================================================
    # GRAPH
    # =====================================================

    if result.get("graph"):

        organized["graphs"].append(
            result.get("graph")
        )

    # =====================================================
    # FORMULA
    # =====================================================

    if result.get("formula"):

        organized["formulas"].append(
            result.get("formula")
        )

    # =====================================================
    # GALLERY
    # =====================================================

    if result.get("gallery"):

        organized["gallery"] = result.get(
            "gallery"
        )

    # =====================================================
    # SCENES
    # =====================================================

    if result.get("scene"):

        organized["scenes"].append({

            "scene":
                result.get("scene"),

            "layout":
                result.get("layout")
        })

    return organized

# =========================================================
# ⚡ APRIL EXECUTION WRAPPER
# =========================================================

async def process_april_request(
    user_id,
    text
):

    """
    Main routing pipeline.

    Human request
      ↓
    April executor
      ↓
    Machine response
      ↓
    Human multimedia organization
    """

    result = await execute(

        user_id,
        text,
        0,
        None
    )

    normalized = normalize_result_payload(
        result
    )

    build_scene_state(
        normalized,
        user_id
    )

    organized = organize_multimedia_response(
        normalized
    )

    return organized

# =========================================================
# 🌐 APRIL WEB CHAT API
# =========================================================

@app.route("/chat", methods=["POST"])
def april_web_chat():

    """
    Main April Web endpoint.

    Handles:
    - user requests
    - executor routing
    - multimedia formatting
    - structured Web responses
    """

    try:

        data = request.json or {}

        user_id = str(
            data.get(
                "user_id",
                "web_user"
            )
        )

        text = (
            data.get(
                "text",
                ""
            ).strip()
        )

        final_response = asyncio.run(

            process_april_request(
                user_id,
                text
            )
        )

        return jsonify({

            "success": True,

            "response":
                final_response.get(
                    "response"
                ),

            "sections":
                final_response.get(
                    "sections",
                    []
                ),

            "visual_blocks":
                final_response.get(
                    "visual_blocks",
                    []
                ),

            "tables":
                final_response.get(
                    "tables",
                    []
                ),

            "graphs":
                final_response.get(
                    "graphs",
                    []
                ),

            "formulas":
                final_response.get(
                    "formulas",
                    []
                ),

            "links":
                final_response.get(
                    "links",
                    []
                ),

            "gallery":
                final_response.get(
                    "gallery",
                    []
                ),

            "scenes":
                final_response.get(
                    "scenes",
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
# 🚀 START APRIL WEB CORE
# =========================================================

if __name__ == "__main__":

    """
    Starts April Web Router Core.

    Lightweight.
    Web-only.
    Transport-focused.
    """

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
