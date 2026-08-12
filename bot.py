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
import ast
import json
import os
import re
import traceback
from dataclasses import is_dataclass

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
    get_state,
    add_dialog,
)

# =========================================================
# 🌐 SERVER
# =========================================================

from checkout_server import app

# =========================================================
# 🔥 CANONICAL ROUTE CONFIG
# =========================================================

BOT_ROUTER_ROLE = "CANONICAL_MACHINE_BRIDGE"
BOT_ROUTER_PROVIDER_CALLS = 0
BOT_ROUTER_PARALLEL_ROUTE = False
BOT_ROUTER_SCENE_AUTHORITY = "QUANTUM_PROCESSOR"

# =========================================================
# 🔥 RENDERER TYPES
# =========================================================

BOT_ROUTER_GUARD = {
    "legacy_messenger_transport": False,
    "provider_authority": False,
    "cognition_authority": False,
    "renderer_authority": False,
    "scene_contract_authority": "QUANTUM_PROCESSOR",
    "single_route": True,
}

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




def _json_safe_snapshot(value, _active=None):
    """Detach transport/state objects without flattening rich renderer payloads."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if _active is None:
        _active = set()

    oid = id(value)
    if oid in _active:
        return {"__cycle__": True}

    if is_dataclass(value):
        try:
            value = {
                field_name: getattr(value, field_name)
                for field_name in value.__dataclass_fields__
            }
        except Exception:
            return str(value)

    if isinstance(value, dict):
        _active.add(oid)
        try:
            return {
                str(key): _json_safe_snapshot(item, _active)
                for key, item in value.items()
                if not str(key).startswith("_")
            }
        finally:
            _active.remove(oid)

    if isinstance(value, (list, tuple, set)):
        _active.add(oid)
        try:
            return [_json_safe_snapshot(item, _active) for item in value]
        finally:
            _active.remove(oid)

    try:
        return str(value)
    except Exception:
        return None


def scene_contract_to_dict(scene_contract):
    if scene_contract is None:
        return None

    if isinstance(scene_contract, dict):
        return scene_contract

    if isinstance(scene_contract, str):
        text = scene_contract.strip()
        if text:
            for parser in (json.loads, ast.literal_eval):
                try:
                    parsed = parser(text)
                except Exception:
                    continue
                if isinstance(parsed, dict):
                    return parsed
                if isinstance(parsed, list):
                    return {"items": parsed}

    if is_dataclass(scene_contract):
        try:
            return {
                field_name: getattr(scene_contract, field_name)
                for field_name in scene_contract.__dataclass_fields__
            }
        except Exception:
            pass

    if hasattr(scene_contract, "__dict__"):
        try:
            return dict(vars(scene_contract))
        except Exception:
            pass

    return scene_contract


def _value_is_present(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return value not in ([], {}, ())


RICH_TRANSPORT_KEYS = (
    "scene_contract",
    "gateway_transport",
    "render_blocks",
    "blocks",
    "renderer_state",
    "machine_scene",
    "scene_plan",
    "graph",
    "formula",
    "table",
    "gallery",
    "layout",
    "visual",
    "scene",
    "links",
    "signals",
    "payload",
    "artifact",
)

HUMAN_HINT_KEYS = (
    "answer",
    "content",
    "summary",
    "final_text",
    "text",
    "response",
    "message",
    "error",
    "detail",
    "reason",
)


def is_rich_transport_payload(payload):
    if not isinstance(payload, dict):
        return False
    return any(_value_is_present(payload.get(key)) for key in RICH_TRANSPORT_KEYS)


def compact_mapping_hint(mapping):
    if not isinstance(mapping, dict):
        return ""

    for key in HUMAN_HINT_KEYS:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if value is not None and not isinstance(value, (dict, list, tuple, set)):
            text = safe_string(value).strip()
            if text and text not in ("{}", "[]"):
                return text

    fragments = []
    for key, value in mapping.items():
        if key in RICH_TRANSPORT_KEYS:
            continue
        if isinstance(value, (dict, list, tuple, set)):
            continue
        if value is None:
            continue
        text = safe_string(value).strip()
        if not text:
            continue
        fragments.append(f"{key}={text}")
        if len(fragments) >= 3:
            break

    return "; ".join(fragments)


def _best_text(*candidates):
    for candidate in candidates:
        if candidate is None:
            continue

        if isinstance(candidate, dict):
            nested = resolve_canonical_scene_contract(candidate)
            if nested:
                candidate = nested

            for key in (
                "answer",
                "content",
                "summary",
                "final_text",
                "text",
                "response",
                "data",
            ):
                value = candidate.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

        elif isinstance(candidate, str):
            value = candidate.strip()
            if value:
                return value

        else:
            value = str(candidate).strip()
            if value:
                return value

    return ""


def resolve_canonical_scene_contract(payload):
    if isinstance(payload, str):
        parsed = scene_contract_to_dict(payload)
        if isinstance(parsed, dict):
            payload = parsed
        else:
            return {}

    if not isinstance(payload, dict):
        return {}

    for key in (
        "scene_contract",
        "gateway_transport",
        "machine_scene",
        "artifact",
        "response",
        "machine_response",
        "payload",
    ):
        candidate = payload.get(key)
        if isinstance(candidate, str):
            candidate = scene_contract_to_dict(candidate)

        if isinstance(candidate, dict):
            sc = scene_contract_to_dict(candidate)
            if sc:
                nested = resolve_canonical_scene_contract(sc)
                if nested:
                    return nested
                return sc

            if key in ("response", "machine_response", "payload"):
                nested = resolve_canonical_scene_contract(candidate)
                if nested:
                    return nested

    direct = {
        "answer": payload.get("answer"),
        "content": payload.get("content"),
        "summary": payload.get("summary"),
        "render_blocks": payload.get("render_blocks", []),
        "scene": payload.get("scene", {}),
        "graph": payload.get("graph"),
        "formula": payload.get("formula"),
        "table": payload.get("table"),
        "gallery": payload.get("gallery"),
        "layout": payload.get("layout"),
        "visual": payload.get("visual"),
        "renderer_state": payload.get("renderer_state", {}),
        "active_scene": payload.get("active_scene", ""),
        "metadata": payload.get("metadata", {}),
    }
    if any(v not in (None, "", [], {}) for v in direct.values()):
        return direct
    return {}
# =========================================================
# 🔥 MACHINE CLEANER
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
    # Canonical Bot.ru bridge:
    # Prefer the canonical scene contract, then gateway transport,
    # then any remaining compatibility payload.
    if isinstance(payload, dict):
        canonical = resolve_canonical_scene_contract(payload)
        source_mapping = canonical if isinstance(canonical, dict) and canonical else payload

        if result_type in RENDERER_TYPES:
            return payload

        candidate_text = _best_text(
            source_mapping.get("answer"),
            source_mapping.get("content"),
            source_mapping.get("summary"),
            source_mapping.get("final_text"),
            source_mapping.get("text"),
            source_mapping.get("response"),
            source_mapping.get("message"),
            source_mapping.get("error"),
            source_mapping.get("detail"),
            source_mapping.get("reason"),
        )

        if candidate_text:
            payload = candidate_text
        else:
            if is_rich_transport_payload(source_mapping):
                return ""
            payload = compact_mapping_hint(source_mapping)

        if not payload:
            return ""

    elif payload is None:
        payload = ""

    elif not isinstance(payload, str):
        payload = str(payload)

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
        payload = payload.replace(old, new)

    return safe_truncate(
        payload,
        8000
    )
# =========================================================
# 🔥 ARTIFACT → HUMAN
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
    embedded_response = result.get("response")
    if isinstance(embedded_response, dict):
        result = {
            **embedded_response,
            **{k: v for k, v in result.items() if k != "response"},
        }

    scene_contract = resolve_canonical_scene_contract(result)
    gateway_transport = scene_contract_to_dict(result.get("gateway_transport"))

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

    final_text = _best_text(
        normalized.get("content"),
        normalized.get("response"),
        normalized.get("data"),
        result.get("final_text"),
        scene_contract,
    )

    normalized["final_text"] = final_text

    # =====================================================
    # FIBER ROUTE PASSTHROUGH (Stage 1)
    # Preserve canonical transport contract from Executor.
    # =====================================================
    normalized["scene_contract"] = scene_contract
    normalized["gateway_transport"] = gateway_transport
    normalized["render_blocks"] = result.get(
        "render_blocks",
        normalized.get("blocks", [])
    )
    normalized["renderer_state"] = result.get("renderer_state")
    normalized["machine_scene"] = result.get("machine_scene")
    normalized["scene_plan"] = result.get("scene_plan")

    # Fiber Route Stage 1: preserve canonical Executor transport.
    if isinstance(scene_contract, dict):
        normalized["final_text"] = _best_text(
            scene_contract.get("answer"),
            scene_contract.get("content"),
            scene_contract.get("summary"),
            normalized["final_text"],
        )
        normalized["render_blocks"] = (
            scene_contract.get("render_blocks")
            or scene_contract.get("blocks")
            or normalized.get("render_blocks", [])
        )
        normalized["scene"] = scene_contract.get("scene", normalized.get("scene"))
        normalized["formula"] = scene_contract.get("formula", normalized.get("formula"))
        normalized["table"] = scene_contract.get("table", normalized.get("table"))
        normalized["graph"] = scene_contract.get("graph", normalized.get("graph"))
        normalized["layout"] = scene_contract.get("layout", normalized.get("layout"))
        normalized["visual"] = scene_contract.get("visual", normalized.get("visual"))

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

    scene_contract = scene_contract_to_dict(result.get("scene_contract"))

    has_visual = any([

        result.get("scene"),

        result.get("layout"),

        result.get("visual"),

        result.get("graph"),

        result.get("formula"),

        result.get("gallery"),

        result.get("render_blocks"),

        scene_contract.get("render_blocks") if isinstance(scene_contract, dict) else None
    ])

    if not has_visual:
        return

    state["active_visual_scene"] = _json_safe_snapshot({
        "updated": datetime.now().isoformat(),
        "scene": result.get("scene") or (scene_contract.get("scene") if isinstance(scene_contract, dict) else None),
        "layout": result.get("layout") or (scene_contract.get("layout") if isinstance(scene_contract, dict) else None),
        "visual": result.get("visual") or (scene_contract.get("visual") if isinstance(scene_contract, dict) else None),
        "graph": result.get("graph") or (scene_contract.get("graph") if isinstance(scene_contract, dict) else None),
        "formula": result.get("formula") or (scene_contract.get("formula") if isinstance(scene_contract, dict) else None),
        "gallery": result.get("gallery") or (scene_contract.get("gallery") if isinstance(scene_contract, dict) else None),
        "render_blocks": result.get("render_blocks") or (scene_contract.get("render_blocks") if isinstance(scene_contract, dict) else []),
        "scene_contract": scene_contract,
        "continuity_active": True,
    })

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

    result = result or {}
    if isinstance(result.get("response"), dict):
        result = {
            **result["response"],
            **{k: v for k, v in result.items() if k != "response"},
        }

    result_type = result.get("type", "text")
    scene_contract = resolve_canonical_scene_contract(result)

    canonical_text = _best_text(
        scene_contract.get("content"),
        scene_contract.get("answer"),
        scene_contract.get("summary"),
        scene_contract.get("final_text"),
        result.get("content"),
        result.get("answer"),
        result.get("summary"),
        result.get("final_text"),
        result.get("response"),
    )

    final_text = machine_to_human(
        canonical_text,
        result_type
    ) if canonical_text else ""

    organized = {
        "type": result_type,
        "content": canonical_text,
        "answer": _best_text(scene_contract.get("answer"), result.get("answer", "")),
        "summary": _best_text(scene_contract.get("summary"), result.get("summary", "")),
        "blocks": normalize_blocks(
            scene_contract.get("render_blocks", [])
            or result.get("blocks", [])
        ),
        "final_text": final_text or canonical_text,
        "graph": scene_contract.get("graph") or result.get("graph"),
        "formula": scene_contract.get("formula") or result.get("formula"),
        "scene": scene_contract.get("scene") or result.get("scene"),
        "layout": scene_contract.get("layout") or result.get("layout"),
        "visual": scene_contract.get("visual") or result.get("visual"),
        "table": scene_contract.get("table") or result.get("table"),
        "gallery": scene_contract.get("gallery") or result.get("gallery"),
        "links": result.get("links", []),
        "scene_contract": scene_contract,
        "gateway_transport": scene_contract_to_dict(result.get("gateway_transport")) or scene_contract,
        "render_blocks": scene_contract.get("render_blocks", []),
        "active_visual_scene": result.get("active_visual_scene"),
        "renderer_state": scene_contract.get("renderer_state"),
        "machine_scene": result.get("machine_scene"),
        "scene_plan": result.get("scene_plan"),
    }

    return organized
# =========================================================
# 🔥 APRIL REQUEST
# =========================================================
# 🔥 APRIL REQUEST
# =========================================================

async def process_april_request(

    user_id,
    text
):

    machine_request = human_to_machine(text, user_id)

    # Canonical dialog write: the Executor must see the user's real turn
    # before semantic/cognitive analysis. No parallel history is created.
    if text:
        add_dialog(
            user_id,
            "user",
            text,
            metadata={"source": "april_web", "modality": "text"},
        )

    async def run_with_activity(chat_id, coro):
        return await coro

    result = await execute(
        user_id=user_id,
        text=machine_request["machine_text"],
        chat_id=0,
        run_with_activity=run_with_activity
    )

    if not isinstance(result, dict):
        result = {"content": str(result), "type": "text"}

    result = preserve_executor_scene_contract(result)
    if not isinstance(result.get("scene_contract"), dict):
        raise RuntimeError("Canonical CPU SceneContract is required.")
    result.setdefault("gateway_transport", {})
    normalized = organize_multimodal_response(result)

    # Write April's final human-visible answer back into the SAME dialog.
    # This closes the turn pair used by the next request.
    visible_answer = (
        normalized.get("answer")
        or normalized.get("content")
        or normalized.get("final_text")
        or ""
    )
    if visible_answer:
        add_dialog(
            user_id,
            "assistant",
            visible_answer,
            metadata={"source": "april_web", "modality": "text"},
        )

    # Preserve continuity only if a visual scene exists.
    if normalized.get("scene_contract") or normalized.get("render_blocks"):
        synchronize_scene_continuity(user_id, normalized)

    return normalized


# =========================================================
# 🌐 CHAT ENDPOINT
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
        user_id = str(data.get("user_id", "")).strip()
        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id required"
            }), 400

        text = normalize_voice_text(data.get("text", ""))

        result = asyncio.run(process_april_request(user_id, text))

        return jsonify({
            "success": True,
            "canonical_route": "/chat",
            "single_route": True,
            "router_role": BOT_ROUTER_ROLE,
            "provider_calls": BOT_ROUTER_PROVIDER_CALLS,
            "type": result.get("type"),
            "content": result.get("content", ""),
            "answer": result.get("answer", ""),
            "summary": result.get("summary", ""),
            "blocks": result.get("blocks", []),
            "graph": result.get("graph"),
            "formula": result.get("formula"),
            "scene": result.get("scene"),
            "layout": result.get("layout"),
            "visual": result.get("visual"),
            "table": result.get("table"),
            "gallery": result.get("gallery"),
            "links": result.get("links", []),
            "scene_contract": result.get("scene_contract"),
            "gateway_transport": result.get("gateway_transport"),
            "render_blocks": result.get("render_blocks", []),
            "renderer_state": result.get("renderer_state"),
            "machine_scene": result.get("machine_scene"),
            "scene_plan": result.get("scene_plan"),
            "active_visual_scene": result.get("active_visual_scene")
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



# =====================================================
# FIBER ROUTE STAGE 2
# Canonical transport passthrough helper.
# =====================================================

def preserve_executor_scene_contract(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return payload

    scene = payload.get("scene_contract")
    if isinstance(scene, str):
        scene = scene_contract_to_dict(scene)

    if not isinstance(scene, dict):
        return payload

    payload["answer"] = scene.get("answer") or payload.get("answer")
    payload["summary"] = scene.get("summary") or payload.get("summary")
    payload["content"] = scene.get("content") or payload.get("content")

    if scene.get("render_blocks"):
        payload["render_blocks"] = scene["render_blocks"]

    payload["gateway_transport"] = payload.get("gateway_transport") or scene
    return payload


# =====================================================
# FIBER ROUTE STAGE 3
# Legacy normalization is intentionally kept for rollback.
# It is commented rather than removed.
# =====================================================

'''
LEGACY NORMALIZATION (kept for rollback/testing)

normalized = normalize_executor_response(result)
organized = organize_multimodal_response(normalized)

The canonical route should instead be:

Executor
    -> SceneContract
    -> checkout_server
    -> Bot.ru passthrough
    -> AprilWeb

Enable the legacy path only if rollback is required.
'''


# =====================================================
# FIBER ROUTE STAGE 4 (TEST MODE)
# Legacy route disabled for testing.
# =====================================================

'''
# LEGACY PATH (DISABLED)
# normalized = normalize_executor_response(result)
# organized = organize_multimodal_response(normalized)
# response = machine_to_human(organized)
'''

# ACTIVE CANONICAL PATH DISABLED AT IMPORT TIME.
# The endpoint above is the single canonical route.
# If a rollback is needed, the legacy path can be re-enabled in a guarded block.

# ACTIVE CANONICAL PATH DISABLED AT IMPORT TIME.
# The endpoint above is the single canonical route.
# If a rollback is needed, the legacy path can be re-enabled in a guarded block.
