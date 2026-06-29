
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



# =========================================================
# 🧠 WIDESCENE CONTENT RESOLVER
# =========================================================

def resolve_scene_content(result):

    content = (
        result.get("content")
        or result.get("response")
        or result.get("data")
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

    scene = result.get("scene")

    if scene:
        return ""

    blocks = result.get(
        "render_blocks",
        result.get("blocks", [])
    )

    if blocks:
        return ""

    return ""


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
            resolve_scene_content(
                result
            ),

        "scene_present":
            bool(
                result.get("scene")
            ),

        "blocks_present":
            bool(
                result.get("render_blocks")
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
                result.get(
                    "render_blocks",
                    result.get(
                        "blocks",
                        []
                    )
                )
            ),

        "scene":
            safe_json(
                result.get(
                    "scene",
                    {}
                )
            ),

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
                result.get("graph")
            ),

        "formula":
            safe_json(
                result.get("formula")
            ),

        "table":
            safe_json(
                result.get("table")
            ),

        "gallery":
            safe_json(
                result.get("gallery")
            ),

        "layout":
            safe_json(
                result.get("layout")
            ),

        "visual":
            safe_json(
                result.get("visual")
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
            safe_json(
                result.get(
                    "renderer_state",
                    {}
                )
            ),

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
            "scene": bool(result.get("scene")),
            "artifact": bool(result.get("artifact")),
            "blocks": bool(
                result.get("render_blocks")
                or result.get("blocks")
            )
        }
    )

    print("🌐 EXECUTOR RAW:")
    print(result)

    print("🌐 NORMALIZED:")
    print(normalized)

    normalized["scene_contract"] = build_gateway_scene_contract(normalized)
    return normalized



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
    """
    Gateway must transparently forward the Scene Contract without
    rebuilding it.
    """
    return {
        "version": 1,
        "scene": normalized.get("scene", {}),
        "render_blocks": normalized.get("render_blocks", []),
        "renderer_state": normalized.get("renderer_state", {}),
        "artifact_packet": normalized.get("artifact_packet"),
        "continuity": normalized.get("continuity", {}),
        "trajectory": normalized.get("trajectory", {}),
        "space": normalized.get("space", {}),
    }


# =========================================================
# 🧠 WEB EXECUTION
# =========================================================

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

    result = await execute(

        user_id=user_id,

        text=text,

        chat_id=user_id,

        run_with_activity=run_with_activity
    )

    # =====================================================
    # 🔥 NORMALIZE FOR WEB SPACE
    # =====================================================

    normalized = (
        normalize_executor_response(
            result
        )
    )

    return normalized


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

        result = asyncio.run(

            process_web_message(

                user_id="web_voice",

                text=transcript
            )
        )

        return jsonify({

            "success": True,

            "transcript":
                transcript,

            "response":
                result

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

        return jsonify({

            "success": True,

            "space_response":
                safe_json(result),

            "type":
                result.get("type"),

            "graph":
                result.get("graph"),

            "formula":
                result.get("formula"),

            "table":
                result.get("table"),

            "gallery":
                result.get("gallery"),

            "layout":
                result.get("layout"),

            "visual":
                result.get("visual"),

            "blocks":
                result.get("render_blocks", []),

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
