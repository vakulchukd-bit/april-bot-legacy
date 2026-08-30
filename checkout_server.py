
# =========================================================
# 🌐 APRIL WEB GATEWAY
# =========================================================

"""
APRIL WEB SPACE GATEWAY

Это больше НЕ:
- text-only flask layer;
- plain request → plain text system.

Теперь это:
- web orchestration gateway;
- scene transport layer;
- renderer-aware gateway;
- multimodal response bridge;
- continuity-aware web entrypoint.

Главная задача:
НЕ схлопывать April обратно в текст.

Web gateway должен:
- сохранять scene packets;
- сохранять renderer blocks;
- сохранять multimodal continuity;
- передавать executor response как space state;
- поддерживать future live scene-space.

Это foundation для:
- April Web;
- live renderer;
- scene continuity;
- semantic UI;
- multimodal orchestration.
"""

# =========================================================
# 🔥 IMPORTS
# =========================================================

import os
import json
import asyncio
import time
import tempfile
from pathlib import Path

from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    render_template_string
)

from flask_cors import CORS

import requests
from dataclasses import is_dataclass

from blocks.paypal_module import (
    get_access_token,
    capture_payment,
    get_order
)

from storage import (
    set_subscription,
    save_payment,
    find_or_create_user,
    init_db
)

from core.executor import execute
from blocks.state_manager import (
    get_state,
    add_dialog,
    update_visual_summary,
    prepare_visual_context_for_turn,
    restore_visual_context_after_turn,
    persist_state,
)
from blocks.provider_router import (
    transcribe_voice
)

from blocks.image_system import (
    analyze_image
)


# =========================================================
# 🔥 CONFIG
# =========================================================

PORT = int(
    os.getenv(
        "CHECKOUT_PORT",
        8080
    )
)

DOMAIN = os.getenv(
    "CHECKOUT_DOMAIN",
    "https://aprill.site"
)

PAYPAL_CLIENT_ID = os.getenv(
    "PAYPAL_CLIENT_ID"
)

BASE_URL = (
    "https://api-m.paypal.com"
)

# =========================================================
# 🔥 APRIL WEB MODES
# =========================================================

WEB_RENDERER_MODE = True

WEB_SCENE_MODE = True

WEB_CONTINUITY_MODE = True

WEB_MULTIMODAL_MODE = True

ALLOW_TEXT_COLLAPSE = False

ALLOW_RENDER_PACKET_LOSS = False

ALLOW_SCENE_RESET = False


# =========================================================
# 🔥 FLASK
# =========================================================

app = Flask(__name__)

CORS(app)


# =========================================================
# 🧠 SAFE JSON
# =========================================================

def _json_safe_snapshot(value, _active=None):
    """Preserve rich transport structures while breaking runtime cycles."""
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


def safe_json(value):
    return _json_safe_snapshot(value)


def _checkout_best_text(*values):
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def scene_contract_to_dict(contract):
    """Return a shallow transport view of SceneContract.

    Do not call dataclasses.asdict() here: asdict() recursively deep-copies
    every nested field and can invoke custom container implementations. In
    the current production payload that boundary was able to surface
    ``slice(None, 5, None)`` after the provider had already produced a valid
    MachineResponse. The canonical contract must be projected without
    recursively rebuilding its nested payloads.
    """
    if contract is None:
        return {}

    if isinstance(contract, dict):
        return contract

    try:
        values = vars(contract)
        if isinstance(values, dict):
            return dict(values)
    except Exception:
        pass

    if is_dataclass(contract):
        try:
            # Dataclass fields are read directly rather than using asdict(),
            # preserving nested machine payload objects untouched.
            return {
                field_name: getattr(contract, field_name)
                for field_name in contract.__dataclass_fields__
            }
        except Exception:
            pass

    return {}



# =========================================================
# 🧠 WIDESCENE CONTENT RESOLVER
# =========================================================

def resolve_scene_content(result):

    result = result if isinstance(result, dict) else {}
    contract = scene_contract_view(result.get("scene_contract"))
    gateway = scene_contract_view(result.get("gateway_transport"))

    for k in ("answer", "content", "summary"):
        value = _checkout_best_text(
            contract.get(k),
            contract.get("metadata", {}).get(k),
            gateway.get(k),
            gateway.get("metadata", {}).get(k),
            result.get("machine_response", {}).get(k) if isinstance(result.get("machine_response"), dict) else "",
            result.get(k),
        )
        if value:
            return value

    content = _checkout_best_text(
        result.get("answer"),
        result.get("content"),
        result.get("summary"),
        result.get("response"),
        result.get("data"),
        contract.get("content"),
        contract.get("answer"),
        contract.get("summary"),
        gateway.get("content"),
        gateway.get("answer"),
        gateway.get("summary"),
    )

    if content:
        return content

    artifact = result.get("artifact")

    if artifact:

        if isinstance(artifact, str):
            return artifact

        if isinstance(artifact, dict):

            for field in [
                "content",
                "text",
                "summary",
                "analysis",
                "description",
                "research_summary",
                "observation_report",
                "topic"
            ]:

                value = artifact.get(field)

                if value:
                    return value

    blocks = (
        contract.get("render_blocks")
        or gateway.get("render_blocks")
        or result.get("render_blocks")
        or contract.get("blocks")
        or gateway.get("blocks")
        or result.get("blocks", [])
    )

    if isinstance(blocks, list):
        for block in blocks:
            if isinstance(block, dict):
                for field in ("content", "text", "description"):
                    value = block.get(field)
                    if isinstance(value, str) and value.strip():
                        return value

    return ""



# =========================================================
# 🧠 EXECUTOR CONTRACT PASS-THROUGH
# =========================================================

def executor_contract_passthrough(result):
    
    if not isinstance(result, dict):
        return result

    if result.get("scene_contract"):
        result.setdefault("gateway_contract", True)
        result.setdefault("gateway_transport_only", True)
        return result

    if not result.get("scene_contract"):
        raise RuntimeError("Executor must provide canonical scene_contract.")

    return result


# =========================================================
# GATEWAY COMPATIBILITY LAYER (Stage 2)
# =========================================================
# Temporary compatibility only.
# These helpers exist while AprilWeb migrates.
# Future owner: April CPU.
# - resolve_scene_content()
# - normalize_executor_response()
# - build_gateway_scene_contract()
# - build_gateway_transport_payload()
# =========================================================


# =========================================================
# 🧠 CANONICAL SCENE CONTRACT ADAPTER (Stage 1)
# =========================================================

def scene_contract_view(contract):
    """
    Temporary adapter while Gateway migrates from dict to
    canonical SceneContract dataclass.
    """
    contract = scene_contract_to_dict(contract)
    if not contract:
        return {}

    view = dict(contract)

    if "render_blocks" not in view or view.get("render_blocks") in (None, ""):
        view["render_blocks"] = view.get("blocks", []) or []

    if "blocks" not in view:
        view["blocks"] = view.get("render_blocks", []) or []

    view.setdefault("active_scene", "")
    view.setdefault("space_continuity", {})
    view.setdefault("renderer_state", {})
    view.setdefault("metadata", {})

    return view




# =========================================================
# 🧠 CANONICAL SCENE ACCESSORS (Stage 2)
# =========================================================

def canonical_scene_blocks(contract):
    return scene_contract_view(contract).get("render_blocks", [])

def canonical_scene_metadata(contract):
    return scene_contract_view(contract).get("metadata", {})



# =========================================================
# 🧠 CANONICAL CPU RETURN / TRANSPORT HELPERS
# =========================================================
# These helpers are intentionally transport-only. They do not route, render,
# call Provider, or create a parallel response path.

def gateway_return_cpu_result(result):
    """
    Return the single canonical CPU result without collapsing SceneContract
    into legacy text. This function is the missing gateway boundary that
    previously caused:
        NameError: gateway_return_cpu_result
    after Provider had already produced a valid response.
    """
    if result is None:
        raise RuntimeError("CPU returned no result.")

    if not isinstance(result, dict):
        return {
            "success": True,
            "scene_contract": {},
            "content": str(result),
            "answer": str(result),
            "summary": "",
            "render_blocks": [],
            "canonical_route": "/api/v1/chat",
            "single_route": True,
        }

    # Preserve the canonical CPU object exactly; only add transport metadata.
    # The gateway never creates a second response object or a renderer route.
    if isinstance(result, dict):
        result.setdefault("single_route", True)
        result.setdefault("canonical_route", "/api/v1/chat")
        result.setdefault("gateway_transport_only", True)
        # Keep the canonical response visible for downstream transport only.
        result.setdefault("gateway_contract", True)
        return result

    return {
        "success": True,
        "scene_contract": {},
        "content": str(result),
        "answer": str(result),
        "summary": "",
        "render_blocks": [],
        "canonical_route": "/api/v1/chat",
        "single_route": True,
        "gateway_transport_only": True,
        "gateway_contract": True,
    }


def build_gateway_transport_payload(result):
    """
    Project the already-created CPU SceneContract into the HTTP transport
    envelope. No new scene, response, provider, or renderer is created here.
    """
    if not isinstance(result, dict):
        result = gateway_return_cpu_result(result)

    scene = scene_contract_view(result.get("scene_contract"))
    machine = result.get("machine_response")
    machine = machine if isinstance(machine, dict) else {}

    render_blocks = (
        scene.get("render_blocks")
        or result.get("render_blocks")
        or machine.get("render_blocks")
        or []
    )

    # SceneContract is already canonical. Transport must not choose between
    # answer/content/summary or manufacture a new human text field.
    content = scene.get("content") if isinstance(scene.get("content"), str) else result.get("content", "")
    answer = scene.get("answer") if isinstance(scene.get("answer"), str) else result.get("answer", "")

    summary = _checkout_best_text(
        scene.get("summary"),
        machine.get("summary"),
        result.get("summary"),
    )

    return {
        "success": True,
        "canonical_route": "/api/v1/chat",
        "single_route": True,
        "scene_contract": safe_json(scene),
        "render_blocks": safe_json(render_blocks),
        "content": content,
        "answer": answer,
        "summary": summary,
        "active_visual_scene": safe_json(
            result.get("active_visual_scene")
            or scene.get("active_visual_scene")
            or {}
        ),
        "space_continuity": safe_json(
            result.get("space_continuity")
            or scene.get("space_continuity")
            or {}
        ),
        "transport_role": "gateway_only",
    }



# =========================================================
# 🧠 RESPONSE NORMALIZATION
# =========================================================

def normalize_executor_response(
    result
):

    if not isinstance(result, dict):

        return {

            "type": "text",

            "content": str(result),

            "space": {}
        }

    scene_contract = scene_contract_view(result.get("scene_contract"))
    root_scene = scene_contract if isinstance(scene_contract, dict) else {}

    print("========== NORMALIZE EXECUTOR RESPONSE ==========")
    print("RESULT TYPE:", type(result))
    if isinstance(result, dict):
        print("RESULT KEYS:", list(result.keys()))
        scene_obj = result.get("scene")
        print("ROOT RENDER_BLOCKS:", bool(result.get("render_blocks")))
        if isinstance(scene_obj, dict):
            print("SCENE KEYS:", list(scene_obj.keys()))
            print("SCENE RENDER_BLOCKS:", bool(scene_obj.get("render_blocks")))
            print("SCENE BLOCKS:", bool(scene_obj.get("blocks")))
    
    normalized = {

        # =================================================
        # 🔥 CORE
        # =================================================

        "type":
            result.get(
                "type",
                "text"
            ),

        "content":
            resolve_scene_content(result),

        "answer":
            safe_json(result.get("answer") or scene_contract.get("answer")),

        "summary":
            safe_json(result.get("summary") or scene_contract.get("summary")),

        "scene_present":
            bool(
                scene_contract or result.get("scene")
            ),

        "blocks_present":
            bool(
                scene_contract.get("render_blocks")
                or result.get("render_blocks")
                or result.get("blocks")
            ),

        "artifact_present":
            bool(
                result.get("artifact")
            ),

        # =================================================
        # 🔥 RENDER
        # =================================================

        "render_blocks":
            safe_json(
                scene_contract.get("render_blocks")
                or result.get("render_blocks")
                or scene_contract.get("blocks")
                or result.get("blocks", [])
            ),

        "scene":
            safe_json(root_scene.get("scene", result.get("scene", {}))),

        "space":
            safe_json(
                result.get(
                    "space",
                    {}
                )
            ),

        # =================================================
        # 🔥 SCIENCE RENDERERS
        # =================================================

        "graph":
            safe_json(
                result.get("graph") or scene_contract.get("graph")
            ),

        "formula":
            safe_json(
                result.get("formula") or scene_contract.get("formula")
            ),

        "table":
            safe_json(
                result.get("table") or scene_contract.get("table")
            ),

        "gallery":
            safe_json(
                result.get("gallery") or scene_contract.get("gallery")
            ),

        "layout":
            safe_json(
                result.get("layout") or scene_contract.get("layout")
            ),

        "visual":
            safe_json(
                result.get("visual") or scene_contract.get("visual")
            ),

        # =================================================
        # 🔥 CONTINUITY
        # =================================================

        "continuity":
            safe_json(
                result.get(
                    "continuity",
                    {}
                )
            ),

        "trajectory":
            safe_json(
                result.get(
                    "trajectory",
                    {}
                )
            ),

        # =================================================
        # 🔥 MULTIMODAL
        # =================================================

        "visual_blocks":
            safe_json(
                result.get(
                    "visual_blocks",
                    []
                )
            ),

        "ui_actions":
            safe_json(
                result.get(
                    "ui_actions",
                    []
                )
            ),

        "renderer_state":
            safe_json(scene_contract.get("renderer_state", result.get("renderer_state", {}))),

        "artifact_packet":
            safe_json(
                build_artifact_packet(result)
            ) if result.get("artifact") else None
    }

    # =====================================================
    # 🔥 LEGACY TEXT SAFETY
    # =====================================================

    if (

        not ALLOW_TEXT_COLLAPSE

        and normalized["render_blocks"]
    ):

        normalized[
            "preserve_render_space"
        ] = True


    print(
        "🌐 WIDESCENE:",
        {
            "scene_contract": bool(result.get("scene_contract")),
            "artifact": bool(result.get("artifact")),
            "blocks": bool(
                scene_contract.get("render_blocks")
            )
        }
    )

    print("🌐 EXECUTOR RAW:")
    print(result)

    print("🌐 NORMALIZED:")
    print(normalized)

    
    canonical = scene_contract_view(result.get("scene_contract")) if isinstance(result, dict) else None
    executor_final = False
    if canonical:
        executor_final = canonical.get("scene_contract_final") or result.get("scene_contract_final")

    if canonical:
        canonical = scene_contract_view(canonical)
        canonical.setdefault("content", normalized.get("content"))
        canonical.setdefault("answer", normalized.get("answer"))
        canonical.setdefault("summary", normalized.get("summary"))
        canonical.setdefault("render_blocks", normalized.get("render_blocks", []))
        normalized["scene_contract"] = canonical
    elif not executor_final:
        normalized["scene_contract"] = build_gateway_scene_contract(normalized)
    else:
        normalized["scene_contract"] = canonical

    
    normalized["legacy_renderers"] = {
        "graph": normalized.get("graph"),
        "formula": normalized.get("formula"),
        "table": normalized.get("table"),
        "gallery": normalized.get("gallery"),
        "layout": normalized.get("layout"),
        "visual": normalized.get("visual"),
    }

    normalized["preferred_transport"] = "scene_contract"
    normalized["transport_role"] = "gateway_only"
    normalized["gateway_mutation"] = False
    return gateway_return_cpu_result(normalized)



# =========================================================
# 🏭 ARTIFACT REPRESENTATION RESOLVER
# =========================================================

def build_artifact_packet(result):

    artifact = result.get("artifact")

    return {
        "artifact": safe_json(artifact),
        "artifact_type": result.get("artifact_type", "knowledge"),
        "domain": result.get("domain"),
        "available_representations": result.get(
            "available_representations",
            [
                "markdown",
                "graph",
                "table",
                "diagram",
                "formula",
                "timeline",
                "gallery",
                "link"
            ]
        ),
        "preferred_representation": result.get(
            "preferred_representation",
            "markdown"
        )
    }



# =========================================================
# 🧠 GATEWAY SCENE CONTRACT (APRIL UPGRADE)
# =========================================================

def build_gateway_scene_contract(normalized):
    """Fallback only. Canonical Scene Contract must come from Executor."""
    
    if normalized.get("scene_contract"):
        return normalized["scene_contract"]

    return {
        "version": 1,
        "scene": normalized.get("scene", {}),
        "render_blocks": normalized.get("render_blocks", []),
        "renderer_state": normalized.get("renderer_state", {}),
        "artifact_packet": normalized.get("artifact_packet"),
        "continuity": normalized.get("continuity", {}),
        "trajectory": normalized.get("trajectory", {}),
        "space": normalized.get("space", {}),
        "content": normalized.get("content"),
        "answer": normalized.get("answer"),
        "summary": normalized.get("summary"),
    }



# =========================================================
# 🧠 SPACE CONTINUITY PAYLOAD
# =========================================================

def build_space_continuity(normalized):
    
    return {
        "active_scene": normalized.get("scene", {}),
        "renderer_state": normalized.get("renderer_state", {}),
        "workspace": normalized.get("space", {}),
        "continuity": normalized.get("continuity", {}),
        "trajectory": normalized.get("trajectory", {}),
        "scene_contract": normalized.get("scene_contract", {}),
    }


# =========================================================
# APRIL CPU GATEWAY CONTRACT (Stage 1)
# =========================================================
# Checkout Server is a transport gateway only.
# Responsibilities:
# 1. Receive HTTP requests.
# 2. Forward requests to April CPU (execute()).
# 3. Return canonical Scene Contract.
# 4. Do not make routing decisions.
# CPU owns routing, orchestration and SceneContract creation.
# =========================================================

GATEWAY_ROLE = "TRANSPORT_ONLY"
GATEWAY_CANONICAL_ONLY = True
GATEWAY_PARALLEL_ROUTE = False
GATEWAY_PROVIDER_CALLS = 0
CPU_OWNS_ROUTING = True
CPU_OWNS_SCENE_CONTRACT = True

# =========================================================
# 🧠 WEB EXECUTION
# =========================================================

# Gateway wrapper: forwards to April CPU.

# =========================================================
# CPU FORWARDING LAYER (Stage 3)
# =========================================================
# Gateway delegates orchestration to April CPU.
# This wrapper is the single forwarding point.
# Future CPU diagnostics can be attached here without
# changing Flask routes.

async def gateway_forward_to_cpu(user_id, text, run_with_activity, *, internal_context=False, request_source="april_web"):
    return await execute(
        user_id=user_id,
        text=text,
        chat_id=user_id,
        run_with_activity=run_with_activity,
        internal_context=internal_context,
        request_source=request_source,
    )


# =========================================================
# APRIL CPU EXECUTION BRIDGE (Final Gateway Pass)
# =========================================================
# Single CPU bridge used by all web entrypoints.

async def gateway_cpu_execute(user_id, text, run_with_activity, *, internal_context=False, request_source="april_web"):
    result = await gateway_forward_to_cpu(
        user_id=user_id,
        text=text,
        run_with_activity=run_with_activity,
        internal_context=internal_context,
        request_source=request_source,
    )
    return gateway_return_cpu_result(result)

async def process_web_message(
    user_id,
    text,
    *,
    internal_context=False,
    request_source="april_web"
):

    async def run_with_activity(chat_id, coro):
        print("🔥 ACTIVITY WRAPPER START")
        print("🔥 CHAT:", chat_id)
        result = await coro
        print("🔥 ACTIVITY WRAPPER END")
        print("🔥 RESULT TYPE:", type(result))
        return result

    visual_turn = prepare_visual_context_for_turn(user_id, text)
    print("🧠 VISUAL TURN GATE:", visual_turn)
    # The current human turn MUST NOT enter state.dialog before interpretation.
    # Interpretation needs the previous completed USER↔APRIL pair as its anchor.
    # Commit the current pair only after a successful canonical response.
    try:
        result = await gateway_cpu_execute(
            user_id=user_id,
            text=text,
            run_with_activity=run_with_activity,
            internal_context=internal_context,
            request_source=request_source,
        )

        result = executor_contract_passthrough(result)
        if not isinstance(result, dict) or not result.get("scene_contract"):
            raise RuntimeError("Canonical CPU SceneContract is required.")

        scene_view = scene_contract_view(result["scene_contract"])
        normalized = {
            "scene_contract": scene_view,
            "content": scene_view.get("content") or "",
            "answer": scene_view.get("answer") or "",
            "summary": scene_view.get("summary"),
            "render_blocks": scene_view.get("render_blocks", []),
            "scene": scene_view.get("machine_scene") or scene_view.get("scene", {}),
            "graph": scene_view.get("graph"),
            "formula": scene_view.get("formula"),
            "table": scene_view.get("table"),
            "gallery": scene_view.get("gallery"),
            "layout": scene_view.get("layout"),
            "visual": scene_view.get("visual"),
        }
        normalized["space_continuity"] = build_space_continuity(normalized)

        try:
            sc = normalized.get("scene_contract")
            print("="*80)
            print("🧭 FIBER SCENE CONTRACT AUDIT")
            print("SCENE_CONTRACT TYPE:", type(sc))
            if isinstance(sc, dict):
                print("SCENE_CONTRACT KEYS:", list(sc.keys()))
                rb = sc.get("render_blocks", [])
                print("RENDER_BLOCKS COUNT:", len(rb) if isinstance(rb, list) else "not-list")
                print("RENDERER_STATE KEYS:", list((sc.get("renderer_state") or {}).keys()))
            print("="*80)
        except Exception as audit_error:
            print("SCENE CONTRACT AUDIT ERROR:", audit_error)

        if not internal_context:
            visible_answer = normalized.get("answer") or normalized.get("content") or ""
            # Commit the completed USER↔APRIL pair only after successful execution.
            # This preserves strict turn ordering for the next interpretation pass.
            if text:
                add_dialog(
                    user_id,
                    "user",
                    text,
                    metadata={"source": "april_web", "modality": "text", "human_turn": True},
                )
            if visible_answer:
                add_dialog(
                    user_id,
                    "assistant",
                    visible_answer,
                    metadata={"source": "april_web", "modality": "text", "human_turn": True},
                )
        normalized["user_id"] = str(user_id)
        normalized["canonical_route"] = "/api/v1/chat"
        normalized["single_route"] = True
        normalized["space_continuity"] = build_space_continuity(normalized)

        # The Executor's update_scene_context() is the sole scene commit point.
        # Every completed USER↔APRIL turn becomes the current scene, including
        # text-only turns. Visual renderer types describe presentation; they do
        # not decide whether memory is a scene.
        return normalized
    finally:
        # If the turn did not produce a new visual scene, restore the stored scene
        # for future genuine continuation. It never re-enters the completed turn.
        blocks = []
        normalized_local = locals().get("normalized")
        try:
            blocks = normalized_local.get("render_blocks", []) if isinstance(normalized_local, dict) else []
        except Exception:
            pass
        visual_types = {"graph", "plot", "chart", "diagram", "schematic", "gallery", "image", "media", "visual", "scene", "table"}
        new_scene_active = any(
            isinstance(block, dict) and str(block.get("type") or block.get("artifact_type") or block.get("representation") or "").strip().lower() in visual_types
            for block in blocks
        )
        restore_visual_context_after_turn(user_id, new_scene_active=new_scene_active)



# =========================================================
# 🎤 APRIL VOICE — CANONICAL INPUT GATEWAY
# =========================================================
# Voice is input transport only:
#   audio -> transcription -> canonical transcript response.
# The frontend then continues through the same /api/v1/chat route.
# No second answer route is created here.

@app.route(
    "/voice",
    methods=["POST"],
)
def voice_chat():
    temp_path = None
    try:
        voice_file = (
            request.files.get("voice")
            or request.files.get("audio")
            or request.files.get("file")
        )
        user_id = str(
            (request.form.get("user_id") or request.form.get("aprilId") or "")
        ).strip()

        if not voice_file:
            return jsonify({
                "success": False,
                "error": "voice file missing",
            }), 400

        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id required",
            }), 400

        suffix = Path(voice_file.filename or "voice.webm").suffix.lower() or ".webm"
        if not suffix.startswith(".") or len(suffix) > 12:
            suffix = ".webm"
        with tempfile.NamedTemporaryFile(
            prefix="april_voice_",
            suffix=suffix,
            delete=False,
        ) as handle:
            temp_path = handle.name
            voice_file.save(temp_path)

        print("=" * 80)
        print("🎤 VOICE REQUEST RECEIVED")
        print("VOICE INPUT RECEIVED", flush=True)

        language = str(
            request.form.get("language") or "en"
        ).strip().lower()

        try:
            transcript = asyncio.run(transcribe_voice(temp_path))
            transcript = _checkout_best_text(transcript)
        except Exception as exc:
            import traceback as _traceback
            print("VOICE TRANSCRIPTION FAILURE:", exc)
            _traceback.print_exc()
            return jsonify({
                "success": False,
                "error_code": "VOICE_TRANSCRIPTION_FAILED",
                "error": str(exc),
                "canonical_route": "/api/v1/chat",
                "voice_input": True,
                "processed": False,
                "language": language,
            }), 502

        if not transcript:
            return jsonify({
                "success": False,
                "error_code": "VOICE_TRANSCRIPTION_EMPTY",
                "error": "voice transcription returned empty text",
                "canonical_route": "/api/v1/chat",
                "voice_input": True,
                "processed": False,
                "language": language,
            }), 422

        print("🎤 VOICE TRANSCRIPTION COMPLETE", flush=True)
        print("🎤 VOICE ROUTE: transcript_only -> /api/v1/chat", flush=True)

        flow_id = None
        try:
            flow_id = request.form.get("flow_id")
        except Exception:
            pass

        payload = {
            "success": True,
            "canonical_route": "/api/v1/chat",
            "processed": False,
            "transcript": transcript,
            "user_id": user_id,
            "voice_input": True,
            "language": language,
        }
        if flow_id:
            payload["flow_id"] = flow_id

        return jsonify(payload), 200

    except Exception as exc:
        import traceback as _traceback
        print("VOICE ERROR:", exc)
        _traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(exc),
            "canonical_route": "/api/v1/chat",
            "voice_input": True,
        }), 500

    finally:
        if temp_path:
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass



# =========================================================
# 🖼️ APRIL IMAGE
# =========================================================

"""
APRIL IMAGE ENTRYPOINT

ROLE:
WEB_VISUAL_ENTRYPOINT

PURPOSE:
- receive image from April Web
- activate visual analysis
- create visual continuity
- bridge image understanding into April
"""

@app.route(
    "/image",
    methods=["POST"]
)
def image_chat():

    try:

        print(
            "🖼️ IMAGE REQUEST RECEIVED"
        )

        image_file = request.files.get(
            "image"
        )

        user_id = (request.form.get("user_id") or "").strip()

        if not image_file:

            return jsonify({

                "success": False,

                "error":
                    "image file missing"

            }), 400

        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id required"
            }), 400

        print(
            "🖼️ IMAGE FILE:",
            image_file.filename
        )

        temp_path = (
            f"image_{hashlib.sha256(user_id.encode('utf-8')).hexdigest()[:16]}_{int(time.time()*1000)}.jpg"
        )

        image_file.save(
            temp_path
        )

        print(
            "🖼️ IMAGE SAVED:",
            temp_path
        )

        print(
            "🧠 IMAGE ANALYSIS START"
        )

        # =====================================================
        # 🧠 REAL USER STATE
        # =====================================================

        user_state = get_state(
            user_id
        )

        try:
            result = asyncio.run(
                analyze_image(
                    temp_path,
                    state=user_state
                )
            )
        finally:
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass

        print(
            "🧠 IMAGE ANALYSIS COMPLETE"
        )

        print(
            "🧠 VISUAL STATE READY"
        )

        analysis_payload = safe_json(result)

        visual_summary = {
            "image_analysis": True,
            "user_id": user_id,
            "timestamp": time.time()
        }

        # =====================================================
        # 🧠 APRIL THINKING ROUTE
        # =====================================================

        visual_context = f"""
VISUAL_ANALYSIS:
{analysis_payload}

Проанализируй активную визуальную сцену пользователя.
Если изображение прислано впервые — дай краткое понятное описание.
Если изображение относится к текущему диалогу — ответь по контексту диалога и содержимому изображения.
Используй VISUAL_ANALYSIS как источник визуального контекста.
"""

        april_result = asyncio.run(

            process_web_message(
                user_id=user_id,
                text=visual_context,
                internal_context=True,
            )
        )

        return jsonify({

            "success": True,

            "space_response":
                safe_json(april_result),

            "analysis":
                analysis_payload,

            "renderer_mode":
                WEB_RENDERER_MODE,

            "scene_mode":
                WEB_SCENE_MODE,

            "visual_summary":
                safe_json(
                    visual_summary
                )
        })

    except Exception as e:

        print(
            "IMAGE ERROR:",
            e
        )

        return jsonify({

            "success": False,

            "error":
                str(e)

        }), 500


# =========================================================
# 🌐 APRIL WEB EXECUTION
# =========================================================

@app.route(
    "/api/v1/chat",
    methods=["POST"]
)

def web_chat():

    try:

        data = request.json or {}

        user_id = str(data.get("user_id") or "").strip()
        if not user_id:
            return jsonify({
                "success": False,
                "error": "user_id required"
            }), 400

        text = str(data.get(
            "text",
            ""
        ) or "").strip()

        # Browser page-hide sends only visual_ledger synchronization. It is not
        # a user turn and must never create/replace the current USER↔APRIL scene.
        if not text:
            current_state = get_state(user_id)
            return jsonify({
                "success": True,
                "gateway_transport": {},
                "scene_contract": safe_json({
                    "active_visual_scene": current_state.get("active_visual_scene"),
                    "user_id": user_id,
                    "conversation_id": current_state.get("conversation_id"),
                }),
                "render_blocks": [],
                "content": "",
                "answer": "",
                "summary": "",
                "renderer_mode": WEB_RENDERER_MODE,
                "scene_mode": WEB_SCENE_MODE,
                "visual_summary": safe_json(current_state.get("visual_summary") or {}),
                "active_visual_scene": safe_json(current_state.get("active_visual_scene")),
                "canonical_route": "/api/v1/chat",
                "memory_sync_only": True,
            })

        visual_ledger = data.get(
            "visual_ledger",
            []
        )

        package = data.get(
            "package",
            "free"
        )

        session_started_utc = data.get(
            "session_started_utc"
        )

        visual_summary = {

            "user_id":
                user_id,

            "package":
                package,

            "session_started_utc":
                session_started_utc,

            "scene_events_count":
                len(visual_ledger),

            "last_event":
                visual_ledger[-1]
                if visual_ledger else None
        }

        # A plain user_message ledger event is dialogue evidence, not a new
        # visual scene. Do not refresh/extend the active visual scene here.
        # Scene memory is committed only after a visual SceneContract is
        # actually produced by the canonical CPU route.
        state_after_update = get_state(
            user_id
        )
        # Keep the frontend ledger current as evidence, but do not promote a
        # plain user_message into active visual scene state.
        state_after_update["visual_summary"] = visual_summary
        persist_state(user_id)

        print(
            "🧠 VISUAL STATE PRESERVED",
            state_after_update.get(
                "active_visual_scene"
            )
        )

        print(
            "🧠 VISUAL SUMMARY:",
            visual_summary
        )

        result = asyncio.run(

            process_web_message(
                user_id,
                text
            )
        )

        result["gateway_transport"] = build_gateway_transport_payload(result)

        # =========================================================
        # LEGACY TRANSPORT (TEMPORARILY DISABLED)
        # =========================================================
        #
        # The legacy response below unpacked Scene Contract back into
        # graph/formula/table/gallery/layout/visual/blocks fields.
        # This creates a parallel transport route and conflicts with
        # the canonical Fiber Route.
        #
        # Keep this block only as historical reference while migrating
        # AprilWeb. If testing confirms it is unnecessary, delete it
        # permanently. If a required capability is discovered, restore
        # it through Scene Contract rather than separate transport
        # fields.
        #
        # return jsonify({... legacy transport ...})
        #
        # =========================================================

        gt=result.get("gateway_transport",{})
        return jsonify({
            "success": True,
            "gateway_transport": safe_json(gt),
            "scene_contract": safe_json(gt.get("scene_contract", {})),
            "render_blocks": safe_json(gt.get("render_blocks", [])),
            "content": gt.get("content",""),
            "answer": gt.get("answer",""),
            "summary": gt.get("summary",""),
            "renderer_mode": WEB_RENDERER_MODE,
            "scene_mode": WEB_SCENE_MODE,
            "visual_summary": safe_json(visual_summary),
            "active_visual_scene": safe_json(gt.get("active_visual_scene")),
        })

    except Exception as e:

        import traceback as _traceback
        print(
            "WEB EXECUTION ERROR:",
            e
        )
        _traceback.print_exc()

        error_text = str(e)
        normalized_error = error_text.lower()

        if (
            "gpt-5.6 luna returned no textual output" in normalized_error
            or "canonical machineresponse contains no visible answer" in normalized_error
            or "gpt-5.6 luna returned an empty canonical answer" in normalized_error
        ):
            error_code = "PROVIDER_NO_TEXT"
        else:
            error_code = "WEB_EXECUTION_ERROR"

        return jsonify({
            "success": False,
            "error_code": error_code,
            "error": error_text,
            "canonical_route": "/api/v1/chat",
            "gateway_transport_only": True,
        }), 500


# =========================================================
# 🔥 CREATE ORDER
# =========================================================

@app.route(
    "/create-order",
    methods=["POST"]
)

def create_order():

    data = request.json

    amount = data.get("amount")

    plan = data.get("plan")

    user_id = data.get("user_id")

    token = get_access_token()

    if not token:

        return jsonify({

            "error":
                "TOKEN ERROR"

        }), 500

    response = requests.post(

        f"{BASE_URL}/v2/checkout/orders",

        headers={

            "Content-Type":
                "application/json",

            "Authorization":
                f"Bearer {token}"
        },

        json={

            "intent": "CAPTURE",

            "purchase_units": [

                {

                    "amount": {

                        "currency_code":
                            "USD",

                        "value":
                            str(amount)
                    },

                    "custom_id":
                        f"{user_id}:{plan}",

                    "description":
                        f"APRIL {plan.upper()}"
                }
            ]
        }
    )

    result = response.json()

    if "id" not in result:

        print(
            "PAYPAL CREATE ERROR:",
            result
        )

        return jsonify(result), 500

    return jsonify({

        "id":
            result["id"]
    })


# =========================================================
# 🔥 CAPTURE
# =========================================================

@app.route(
    "/capture-order",
    methods=["POST"]
)

def capture_order():

    data = request.json

    order_id = data.get(
        "orderID"
    )

    capture = capture_payment(
        order_id
    )

    if not capture:

        return jsonify({

            "error":
                "CAPTURE FAILED"

        }), 500

    order = get_order(order_id)

    if not order:

        return jsonify({

            "error":
                "ORDER ERROR"

        }), 500

    try:

        purchase = order[
            "purchase_units"
        ][0]

        custom_id = purchase[
            "custom_id"
        ]

        user_id, plan = (
            custom_id.split(":")
        )

        user_id = int(user_id)

        set_subscription(
            user_id,
            plan
        )

        save_payment(
            user_id,
            plan
        )

    except Exception as e:

        print(
            "CAPTURE ERROR:",
            e
        )

        return jsonify({

            "error":
                str(e)

        }), 500

    return jsonify({

        "status":
            "success"
    })


# =========================================================
# 🟢 SUCCESS
# =========================================================

@app.route("/paypal-success")
def paypal_success():

    return render_template_string(
        SUCCESS_HTML
    )


# =========================================================
# ❌ CANCEL
# =========================================================

@app.route("/paypal-cancel")
def paypal_cancel():

    return render_template_string(
        CANCEL_HTML
    )


# =========================================================
# 🔥 WEBHOOK
# =========================================================

@app.route(
    "/webhook/paypal",
    methods=["POST"]
)

def paypal_webhook():

    try:

        data = request.json

        print(

            "PAYPAL WEBHOOK:",

            json.dumps(
                data,
                indent=4
            )
        )

        return {

            "status": "ok"
        }

    except Exception as e:

        print(
            "WEBHOOK ERROR:",
            e
        )

        return {

            "status": "error"
        }




# =========================================================
# 🌐 APRIL FRONTEND DEBUG
# =========================================================

@app.route(
    "/frontend_log",
    methods=["POST"]
)
def frontend_log():

    try:
        data = request.json or {}

        safe_debug = {
            "room": data.get("room"),
            "stage": data.get("stage"),
            "status": data.get("status"),
            "error_code": data.get("error_code"),
            "canonical_route": data.get("canonical_route"),
        }
        print("=" * 80)
        print("🌐 APRIL WEB DEBUG")
        print(json.dumps(safe_debug, indent=2, ensure_ascii=False))
        print("=" * 80)

        return jsonify({
            "success": True
        })

    except Exception as e:

        print("FRONTEND DEBUG ERROR:", e)

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================================================
# 👤 APRIL USER REGISTRY
# =========================================================

@app.route(
    "/api/users/find-or-create",
    methods=["POST"]
)
def find_or_create_user_route():

    try:

        data = request.json or {}

        email = data.get("email")
        name = data.get("name", "")
        provider = data.get("provider", "google")
        provider_user_id = data.get(
            "provider_user_id"
        )

        if not email:

            return jsonify({
                "success": False,
                "error": "email required"
            }), 400

        user = find_or_create_user(
            email=email,
            name=name,
            provider=provider,
            provider_user_id=provider_user_id
        )

        return jsonify({
            "success": True,
            "user": {
                "aprilId": user.get("april_id")
                    or user.get("user_id"),
                "plan": user.get("plan", "free"),
                "email": user.get("email"),
                "name": user.get("name"),
            }
        })

    except Exception as e:

        print(
            "USER REGISTRY ERROR:",
            e
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================================================
# 🚀 START
# =========================================================

if __name__ == "__main__":

    print(
        "🌐 APRIL WEB GATEWAY STARTED"
    )

    init_db()

    app.run(

        host="0.0.0.0",

        port=PORT,

        debug=False,

        use_reloader=False
    )
