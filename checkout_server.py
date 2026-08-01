
# =========================================================
# 🌐 APRIL WEB GATEWAY
# =========================================================

"""
APRIL WEB SPACE GATEWAY

Это больше НЕ:
- text-only flask layer;
- telegram-era bridge;
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

from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    render_template_string
)

from flask_cors import CORS

import requests
from dataclasses import asdict, is_dataclass

from openai import OpenAI

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
    update_visual_summary
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

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY"
)

client = OpenAI(
    api_key=OPENAI_API_KEY
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

def safe_json(value):

    try:

        json.dumps(value)

        return value

    except:

        return str(value)


def scene_contract_to_dict(contract):
    if contract is None:
        return {}

    if isinstance(contract, dict):
        return contract

    if is_dataclass(contract):
        try:
            return asdict(contract)
        except Exception:
            pass

    if hasattr(contract, "__dict__"):
        try:
            return dict(vars(contract))
        except Exception:
            pass

    return {}



# =========================================================
# 🧠 WIDESCENE CONTENT RESOLVER
# =========================================================

def resolve_scene_content(result):

    result = result if isinstance(result, dict) else {}
    contract = scene_contract_view(result.get("scene_contract"))

    for k in ("answer", "content", "summary"):
        value = contract.get(k)
        if value:
            return value

    content = (
        result.get("answer")
        or result.get("content")
        or result.get("summary")
        or result.get("response")
        or result.get("data")
        or contract.get("content")
        or contract.get("answer")
        or contract.get("summary")
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
        or result.get("render_blocks")
        or contract.get("blocks")
        or result.get("blocks", [])
    )

    if isinstance(blocks, list):
        for block in blocks:
            if isinstance(block, dict):
                for field in ("content", "text", "description"):
                    value = block.get(field)
                    if isinstance(value, str) and value.strip():
                        return value

    scene = result.get("scene") or contract.get("scene")

    if scene:
        return ""

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

async def gateway_forward_to_cpu(user_id, text, run_with_activity):
    return await execute(
        user_id=user_id,
        text=text,
        chat_id=user_id,
        run_with_activity=run_with_activity,
    )



# =========================================================
# APRIL CPU EXECUTION BRIDGE (Final Gateway Pass)
# =========================================================
# Single CPU bridge used by all web entrypoints.

async def gateway_cpu_execute(user_id, text, run_with_activity):
    result = await gateway_forward_to_cpu(
        user_id=user_id,
        text=text,
        run_with_activity=run_with_activity,
    )
    return gateway_return_cpu_result(result)

async def process_web_message(
    user_id,
    text
):

    async def run_with_activity(chat_id, coro):

        print("🔥 ACTIVITY WRAPPER START")
        print("🔥 CHAT:", chat_id)

        result = await coro

        print("🔥 ACTIVITY WRAPPER END")
        print("🔥 RESULT TYPE:", type(result))

        return result

    # Canonical CPU bridge
    result = await gateway_cpu_execute(

        user_id=user_id,
        text=text,
        run_with_activity=run_with_activity
    )

    

    result = executor_contract_passthrough(result)

    if isinstance(result, dict) and result.get("scene_contract"):
        scene_view = scene_contract_view(result["scene_contract"])
        normalized = {
            "scene_contract": scene_view,
            "content": (scene_view.get("content")
                        or scene_view.get("answer")
                        or scene_view.get("summary")
                        or ""),
            "answer": scene_view.get("answer"),
            "summary": scene_view.get("summary"),
            "render_blocks": scene_view.get("render_blocks", []),
            "scene": (scene_view.get("machine_scene")
                      or scene_view.get("scene", {})),
            "graph": scene_view.get("graph"),
            "formula": scene_view.get("formula"),
            "table": scene_view.get("table"),
            "gallery": scene_view.get("gallery"),
            "layout": scene_view.get("layout"),
            "visual": scene_view.get("visual"),
        }
        normalized["space_continuity"] = build_space_continuity(normalized)
    else:
        # Compatibility path until CPU returns canonical transport only
        normalized = normalize_executor_response(result)

    try:
        sc = normalized.get("scene_contract") if isinstance(normalized, dict) else None
        print("="*80)
        print("🧭 FIBER SCENE CONTRACT AUDIT")
        print("SCENE_CONTRACT TYPE:", type(sc))
        if isinstance(sc, dict):
            print("SCENE_CONTRACT KEYS:", list(sc.keys()))
            rb = sc.get("render_blocks", [])
            print("RENDER_BLOCKS COUNT:", len(rb) if isinstance(rb, list) else "not-list")
            print("RENDERER_STATE KEYS:", list((sc.get("renderer_state") or {}).keys()))
        else:
            print("SCENE_CONTRACT VALUE:", sc)
        print("="*80)
    except Exception as audit_error:
        print("SCENE CONTRACT AUDIT ERROR:", audit_error)

    normalized["space_continuity"] = build_space_continuity(normalized)

    return normalized




# =========================================================
# GATEWAY TRANSPORT POLICY (Stage 4)
# =========================================================
# Checkout Server MUST NOT:
#   - choose execution routes
#   - build business logic
#   - orchestrate subsystems
#   - own SceneContract semantics
#
# Checkout Server MAY:
#   - receive HTTP requests
#   - forward requests to April CPU
#   - return canonical CPU response
#   - expose infrastructure endpoints
# =========================================================

def gateway_return_cpu_result(cpu_result):
    """Final gateway return point.
    Future logging/trace hooks should be attached here.
    """
    return cpu_result


# =========================================================
# LEGACY SCENE CONTRACT STATUS (Stage 3)
# =========================================================
# Gateway no longer owns SceneContract semantics.
# Executor + Artifact Factory are canonical owners.
# Remaining compatibility code exists only to serialize the
# canonical transport during migration to AprilWeb.
# =========================================================

# =========================================================
# 🧠 FINAL GATEWAY TRANSPORT
# =========================================================

def build_gateway_transport_payload(normalized):
    
    # Forward canonical contract without rebuilding.
    contract = scene_contract_view(normalized.get("scene_contract"))
    contract.setdefault("gateway_transport_only", True)
    contract.setdefault("gateway_owner", "checkout_server")
    return {
        "scene_contract": contract,
        "contract_version": contract.get("version", 1),
        "transport_mode":"passthrough",
        "gateway_rebuild":False,
        "space_continuity": normalized.get("space_continuity", {}),
        "render_blocks": contract.get("render_blocks", []),
        "renderer_state": contract.get("renderer_state", {}),
        "content": contract.get("content", ""),
        "answer": contract.get("answer", normalized.get("answer")),
        "summary": contract.get("summary", normalized.get("summary")),
    }

# =========================================================
# 🎨 SUCCESS HTML
# =========================================================

SUCCESS_HTML = """
<!DOCTYPE html>
<html>
<head>

<meta charset="utf-8">

<title>APRIL PAYMENT</title>

<style>

body{
    background:#0f1117;
    color:white;
    font-family:Arial;
    text-align:center;
    padding-top:80px;
}

.box{
    max-width:500px;
    margin:auto;
    background:#1c1f2b;
    padding:40px;
    border-radius:24px;
}

.title{
    font-size:32px;
    margin-bottom:20px;
}

.text{
    font-size:18px;
    opacity:.8;
}

</style>

</head>

<body>

<div class="box">

<div class="title">
✅ Оплата успешна
</div>

<div class="text">
Возвращаемся в APRIL Space...
</div>

</div>

</body>
</html>
"""

# =========================================================
# ❌ CANCEL HTML
# =========================================================

CANCEL_HTML = """
<!DOCTYPE html>
<html>
<head>

<meta charset="utf-8">

<title>APRIL PAYMENT</title>

<style>

body{
    background:#0f1117;
    color:white;
    font-family:Arial;
    text-align:center;
    padding-top:80px;
}

.box{
    max-width:500px;
    margin:auto;
    background:#1c1f2b;
    padding:40px;
    border-radius:24px;
}

.title{
    font-size:32px;
    margin-bottom:20px;
}

.text{
    font-size:18px;
    opacity:.8;
}

</style>

</head>

<body>

<div class="box">

<div class="title">
❌ Оплата отменена
</div>

<div class="text">
Можно вернуться позже
</div>

</div>

</body>
</html>
"""

# =========================================================
# 🟢 HEALTH
# =========================================================

@app.route("/")
def health():

    return {

        "status":
            "APRIL WEB GATEWAY ONLINE",

        "renderer_mode":
            WEB_RENDERER_MODE,

        "scene_mode":
            WEB_SCENE_MODE,

        "continuity_mode":
            WEB_CONTINUITY_MODE,

        "multimodal_mode":
            WEB_MULTIMODAL_MODE
    }


# =========================================================
# 🚀 CHECKOUT
# =========================================================

@app.route("/checkout/<plan>/<user_id>")
def checkout(plan, user_id):

    if plan == "lite":

        amount = 12
        plan_name = "⚡ Lite"

    else:

        amount = 69
        plan_name = "👑 Premium"

    return render_template(

        "checkout.html",

        client_id=PAYPAL_CLIENT_ID,

        amount=amount,

        plan_name=plan,

        user_id=user_id
    )


# =========================================================
# 🔥 SAFE VOICE TRANSCRIPT
# =========================================================
def normalize_voice_transcript(transcript):
    if transcript is None:
        return ""
    if isinstance(transcript,str):
        return transcript.strip()
    if isinstance(transcript,dict):
        for k in ("text","content","response","data"):
            v=transcript.get(k)
            if isinstance(v,str):
                return v.strip()
        return ""
    return str(transcript).strip()


# =========================================================
# 🎤 APRIL VOICE
# =========================================================

@app.route(
    "/voice",
    methods=["POST"]
)
def voice_chat():

    try:

        print(
            "🎤 VOICE REQUEST RECEIVED"
        )

        audio_file = request.files.get(
            "audio"
        )

        if not audio_file:

            return jsonify({

                "success": False,

                "error":
                    "audio file missing"

            }), 400

        print(
            "VOICE FILE:",
            audio_file.filename
        )

        temp_path = "voice.webm"

        audio_file.save(
            temp_path
        )

        print(
            "VOICE SAVED:",
            temp_path
        )

        transcript = asyncio.run(

            transcribe_voice(
                temp_path
            )
        )

        transcript = normalize_voice_transcript(transcript)

        print(
            "TRANSCRIPT:",
            transcript
        )

        user_id = request.form.get("user_id", "web_voice")

        return jsonify({

            "success": True,

            "transcript": transcript

        })

    except Exception as e:

        print(
            "VOICE ERROR:",
            e
        )

        return jsonify({

            "success": False,

            "error":
                str(e)

        }), 500




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

        user_id = request.form.get(
            "user_id",
            "web_image"
        )

        if not image_file:

            return jsonify({

                "success": False,

                "error":
                    "image file missing"

            }), 400

        print(
            "🖼️ IMAGE FILE:",
            image_file.filename
        )

        temp_path = (
            f"image_{user_id}_{int(time.time()*1000)}.jpg"
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

        result = asyncio.run(

            analyze_image(
                temp_path,
                state=user_state
            )
        )

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
                text=visual_context
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

        user_id = data.get(
            "user_id"
        )

        text = data.get(
            "text",
            ""
        )

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

        update_visual_summary(
            user_id,
            visual_summary
        )

        state_after_update = get_state(
            user_id
        )

        print(
            "🧠 VISUAL STATE UPDATED",
            state_after_update.get(
                "active_visual_scene"
            )
        )

        if not user_id:

            return jsonify({

                "success": False,

                "error":
                    "user_id required"
            }), 400

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

        print(
            "WEB EXECUTION ERROR:",
            e
        )

        return jsonify({

            "success": False,

            "error": str(e)
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

        print("=" * 80)
        print("🌐 APRIL WEB DEBUG")
        print(json.dumps(data, indent=2, ensure_ascii=False))
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
