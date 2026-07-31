# =========================================================
# 🧠 APRIL AI POLICY CORE
# =========================================================

"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APRIL FILE ID
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

APRIL_FILE_ID:
APRIL_AI_POLICY_CORE

ROLE:
CENTRAL_AI_POLICY_SYSTEM

ROOM:
POLICY_ROOM

INPUT:
EXECUTOR_POLICY_REQUEST
PROVIDER_ROUTE_REQUEST
CONTINUITY_POLICY_REQUEST
IMAGE_POLICY_REQUEST
COGNITION_POLICY_SIGNAL

OUTPUT:
POLICY_PAYLOAD
PROVIDER_ROUTE
CONTINUITY_POLICY
EXECUTION_STABILIZATION
ANALYZER_TELEMETRY

DEPENDENCIES:
EXECUTOR
RENDERER_ROOMS
COGNITIVE_ROOMS
TOOL_ROOMS
ADMIN_MONITOR_CORE

CRITICAL:
TRUE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 GOLDEN RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file NEVER performs cognition.

This file ONLY:
- regulates
- stabilizes
- routes providers
- protects renderer-first execution
- preserves continuity policy
- exposes telemetry-safe diagnostics

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 ANALYZER VISIBILITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Analyzer may observe:
- provider routing
- policy states
- escalation blocking
- continuity stabilization
- renderer-first protection
- orchestration pressure

Analyzer may NEVER:
- alter policy
- inject cognition
- override Executor authority
"""

# =========================================================
# 🧠 MACHINE POLICY CHANNELS
# =========================================================

POLICY_TASK_CHANNEL = {

    "channel":
        "ai_policy_task_channel",

    "isolated":
        True
}

POLICY_RESPONSE_CHANNEL = {

    "channel":
        "ai_policy_response_channel",

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
                "APRIL_AI_POLICY_CORE",

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
                "APRIL_AI_POLICY_CORE",

            "metadata":
                metadata or {}
        })

    except Exception:
        pass

# =========================================================
# 🔥 ANALYZER TELEMETRY
# =========================================================

def build_policy_telemetry_payload():

    APRIL_LOG_IN(

        "POLICY_ROOM",

        {
            "action":
                "build_policy_telemetry_payload"
        }
    )

    payload = {

        "file_id":
            "APRIL_AI_POLICY_CORE",

        "room":
            "POLICY_ROOM",

        "renderer_first":
            RENDERER_FIRST,

        "visual_continuity":
            VISUAL_CONTINUITY_ENABLED,

        "text_continuity":
            TEXT_CONTINUITY_ENABLED,

        "scene_memory":
            SCENE_MEMORY_ENABLED,

        "lightweight_execution":
            LIGHTWEIGHT_EXECUTION_PRIORITY,

        "calm_orchestration":
            CALM_ORCHESTRATION_MODE,

        "provider_escalation":
            ALLOW_PROVIDER_ESCALATION,

        "recursive_generation":
            ALLOW_RECURSIVE_GENERATION,

        "heavy_fallbacks":
            ALLOW_HEAVY_FALLBACK_CHAINS,

        "text_provider":
            TEXT_PROVIDER,

        "vision_provider":
            VISION_PROVIDER,

        "voice_provider":
            VOICE_PROVIDER,

        "text_model":
            TEXT_MODEL,

        "vision_model":
            VISION_FALLBACK_MODEL,

        "voice_model":
            VOICE_MODEL,

        "image_model":
            IMAGE_MODEL
    }

    APRIL_LOG_OUT(

        "POLICY_ROOM",

        {
            "action":
                "policy_telemetry_ready"
        }
    )

    return payload

# =========================================================
# 🧠 PROVIDER PRIORITIES
# =========================================================

TEXT_PROVIDER = "openai"

VISION_PROVIDER = "gemini"

VOICE_PROVIDER = "openai"

# =========================================================
# 🧠 PRIMARY MODELS
# =========================================================

OPENAI_PRIMARY_MODEL = "gpt-5.6"
OPENAI_BALANCED_MODEL = "gpt-5.6-terra"
OPENAI_FAST_MODEL = "gpt-5.6-luna"


TEXT_MODEL = OPENAI_PRIMARY_MODEL

VISION_FALLBACK_MODEL = "gpt-4.1-mini"

VOICE_MODEL = "gpt-4o-mini-transcribe"

IMAGE_MODEL = "gpt-image-1"

# =========================================================
# 🧠 EXECUTION LIMITS
# =========================================================

MAX_OUTPUT_TOKENS = {

    "LOW": 180,

    "MEDIUM": 350,

    "HIGH": 650
}

TEMPERATURE = {

    "LOW": 0.5,

    "MEDIUM": 0.7,

    "HIGH": 0.85
}

# =========================================================
# 🧠 VISUAL EXECUTION POLICY
# =========================================================

IMAGE_SIZE = "512x512"

IMAGE_QUALITY = "low"

RENDERER_FIRST = True

EXPLICIT_IMAGE_GENERATION_ONLY = True

BLOCK_HIDDEN_IMAGE_ESCALATION = True

BLOCK_AUTO_IMAGE_FALLBACKS = True

# =========================================================
# 🧠 CONTINUITY POLICY
# =========================================================

VISUAL_CONTINUITY_ENABLED = True

TEXT_CONTINUITY_ENABLED = True

SCENE_MEMORY_ENABLED = True

# =========================================================
# 🧠 EXECUTION STABILIZATION POLICY
# =========================================================

LIGHTWEIGHT_EXECUTION_PRIORITY = True

CALM_ORCHESTRATION_MODE = True

ALLOW_PROVIDER_ESCALATION = False

ALLOW_RECURSIVE_GENERATION = False

ALLOW_HEAVY_FALLBACK_CHAINS = False

# =========================================================
# 🧠 PROVIDER ROUTING POLICY
# =========================================================

def build_provider_policy_payload():

    APRIL_LOG_IN(

        "POLICY_ROOM",

        {
            "action":
                "build_provider_policy_payload"
        }
    )

    payload = {

        "channel":
            POLICY_RESPONSE_CHANNEL,

        "providers": {

            "text":
                TEXT_PROVIDER,

            "vision":
                VISION_PROVIDER,

            "voice":
                VOICE_PROVIDER
        },

        "models": {

            "text":
                TEXT_MODEL,

            "vision_fallback":
                VISION_FALLBACK_MODEL,

            "voice":
                VOICE_MODEL,

            "image":
                IMAGE_MODEL
        }
    }

    APRIL_LOG_OUT(

        "POLICY_ROOM",

        {
            "action":
                "provider_policy_ready"
        }
    )

    return payload

# =========================================================
# 🧠 EXECUTION POLICY PAYLOAD
# =========================================================

def build_execution_policy_payload():

    APRIL_LOG_IN(

        "POLICY_ROOM",

        {
            "action":
                "build_execution_policy_payload"
        }
    )

    payload = {

        "channel":
            POLICY_RESPONSE_CHANNEL,

        "renderer_first":
            RENDERER_FIRST,

        "explicit_generation_only":
            EXPLICIT_IMAGE_GENERATION_ONLY,

        "block_hidden_escalation":
            BLOCK_HIDDEN_IMAGE_ESCALATION,

        "block_auto_fallbacks":
            BLOCK_AUTO_IMAGE_FALLBACKS,

        "lightweight_priority":
            LIGHTWEIGHT_EXECUTION_PRIORITY,

        "calm_orchestration":
            CALM_ORCHESTRATION_MODE
    }

    APRIL_LOG_OUT(

        "POLICY_ROOM",

        {
            "action":
                "execution_policy_ready"
        }
    )

    return payload

# =========================================================
# 🧠 CONTINUITY POLICY PAYLOAD
# =========================================================

def build_continuity_policy_payload():

    APRIL_LOG_IN(

        "POLICY_ROOM",

        {
            "action":
                "build_continuity_policy_payload"
        }
    )

    payload = {

        "channel":
            POLICY_RESPONSE_CHANNEL,

        "visual_continuity":
            VISUAL_CONTINUITY_ENABLED,

        "text_continuity":
            TEXT_CONTINUITY_ENABLED,

        "scene_memory":
            SCENE_MEMORY_ENABLED
    }

    APRIL_LOG_OUT(

        "POLICY_ROOM",

        {
            "action":
                "continuity_policy_ready"
        }
    )

    return payload

# =========================================================
# 🧠 IMAGE EXECUTION AUTHORITY
# =========================================================

def should_allow_image_generation(

    semantic,
    cognition,
    response_decision
):

    APRIL_LOG_IN(

        "POLICY_ROOM",

        {
            "action":
                "should_allow_image_generation"
        }
    )

    if not EXPLICIT_IMAGE_GENERATION_ONLY:

        APRIL_LOG_OUT(

            "POLICY_ROOM",

            {
                "result":
                    "allowed_global"
            }
        )

        return True

    if semantic.get(
        "render_intent"
    ):

        APRIL_LOG_OUT(

            "POLICY_ROOM",

            {
                "blocked":
                    "render_intent"
            }
        )

        return False

    if response_decision.get(
        "should_render"
    ):

        APRIL_LOG_OUT(

            "POLICY_ROOM",

            {
                "blocked":
                    "should_render"
            }
        )

        return False

    if response_decision.get(
        "avoid_heavy_generation"
    ):

        APRIL_LOG_OUT(

            "POLICY_ROOM",

            {
                "blocked":
                    "heavy_generation"
            }
        )

        return False

    if cognition.get(
        "exploration_mode"
    ):

        APRIL_LOG_OUT(

            "POLICY_ROOM",

            {
                "blocked":
                    "exploration_mode"
            }
        )

        return False

    explicit_request = semantic.get(

        "explicit_image_generation",

        False
    )

    APRIL_LOG_OUT(

        "POLICY_ROOM",

        {
            "explicit_request":
                explicit_request
        }
    )

    return explicit_request

# =========================================================
# 🧠 PROVIDER DECISION CORE
# =========================================================

def resolve_provider_route(

    task_type,
    semantic=None,
    cognition=None
):

    APRIL_LOG_IN(

        "POLICY_ROOM",

        {
            "action":
                "resolve_provider_route",

            "task_type":
                task_type
        }
    )

    semantic = semantic or {}

    cognition = cognition or {}

    if task_type == "text":

        route = {

            "channel":
                POLICY_RESPONSE_CHANNEL,

            "provider":
                TEXT_PROVIDER,

            "model":
                TEXT_MODEL
        }

        APRIL_LOG_OUT(

            "POLICY_ROOM",

            {
                "provider":
                    TEXT_PROVIDER,

                "model":
                    TEXT_MODEL
            }
        )

        return route

    if task_type in [

        "vision",
        "ocr",
        "analyze_image"
    ]:

        route = {

            "channel":
                POLICY_RESPONSE_CHANNEL,

            "provider":
                VISION_PROVIDER,

            "model":
                VISION_FALLBACK_MODEL
        }

        APRIL_LOG_OUT(

            "POLICY_ROOM",

            {
                "provider":
                    VISION_PROVIDER,

                "model":
                    VISION_FALLBACK_MODEL
            }
        )

        return route

    if task_type == "voice":

        route = {

            "channel":
                POLICY_RESPONSE_CHANNEL,

            "provider":
                VOICE_PROVIDER,

            "model":
                VOICE_MODEL
        }

        APRIL_LOG_OUT(

            "POLICY_ROOM",

            {
                "provider":
                    VOICE_PROVIDER,

                "model":
                    VOICE_MODEL
            }
        )

        return route

    if task_type == "image_generate":

        allow = should_allow_image_generation(

            semantic,

            cognition,

            {}
        )

        if not allow:

            APRIL_LOG_OUT(

                "POLICY_ROOM",

                {
                    "blocked":
                        "image_generation_policy"
                }
            )

            return {

                "channel":
                    POLICY_RESPONSE_CHANNEL,

                "blocked":
                    True,

                "reason":
                    "image_generation_policy"
            }

        route = {

            "channel":
                POLICY_RESPONSE_CHANNEL,

            "provider":
                TEXT_PROVIDER,

            "model":
                IMAGE_MODEL
        }

        APRIL_LOG_OUT(

            "POLICY_ROOM",

            {
                "provider":
                    TEXT_PROVIDER,

                "model":
                    IMAGE_MODEL
            }
        )

        return route

    route = {

        "channel":
            POLICY_RESPONSE_CHANNEL,

        "provider":
            TEXT_PROVIDER,

        "model":
            TEXT_MODEL
    }

    APRIL_LOG_OUT(

        "POLICY_ROOM",

        {
            "provider":
                TEXT_PROVIDER,

            "model":
                TEXT_MODEL,

            "fallback":
                True
        }
    )

    return route

# =========================================================
# 🧠 EXECUTOR POLICY BRIDGE
# =========================================================

def build_executor_policy_bridge():

    APRIL_LOG_IN(

        "POLICY_ROOM",

        {
            "action":
                "build_executor_policy_bridge"
        }
    )

    payload = {

        "channel":
            POLICY_RESPONSE_CHANNEL,

        "provider_policy":
            build_provider_policy_payload(),

        "execution_policy":
            build_execution_policy_payload(),

        "continuity_policy":
            build_continuity_policy_payload(),

        "policy_telemetry":
            build_policy_telemetry_payload(),

        "renderer_first":
            True,

        "lightweight_execution":
            True,

        "stable_orchestration":
            True
    }

    APRIL_LOG_OUT(

        "POLICY_ROOM",

        {
            "action":
                "executor_policy_bridge_ready"
        }
    )

    return payload
