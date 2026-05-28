# =========================================================
# 🧠 APRIL AI POLICY CORE
# =========================================================

"""
APRIL AI POLICY CORE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ROLE IN APRIL:
This file is the CENTRAL AI POLICY
and PROVIDER NERVOUS SYSTEM of April.

This file does NOT think instead of Executor.

Executor = central brain.
This file = execution regulation layer.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 MAIN RESPONSIBILITIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This helper core controls:

- provider priorities
- AI execution policies
- renderer-first safety
- model routing logic
- escalation prevention
- execution stabilization
- continuity behavior
- lightweight orchestration
- cognition pressure balancing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 APRIL ARCHITECTURE POSITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BotRoot
 ↓
Executor
 ↓
AI Policy Core (THIS FILE)
 ↓
Cognitive / Tool / Render Rooms

This file NEVER:
- formats frontend output
- controls transport
- performs orchestration
- replaces Executor authority

This file ONLY:
- regulates
- stabilizes
- routes providers
- defines execution policies

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 MACHINE CHANNEL SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file operates through TWO isolated channels.

1. POLICY TASK CHANNEL
Executor → AI Policy Core

2. POLICY RESPONSE CHANNEL
AI Policy Core → Executor

Human-layer logic NEVER mixes with
internal machine execution routing.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 GOLDEN APRIL PRINCIPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- renderer-first architecture
- continuation before generation
- explicit image generation only
- no hidden escalation
- no fallback chaos
- stable cognition pressure
- lightweight orchestration
- provider-aware execution
- unified April intelligence

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 IMPORTANT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DO NOT RE-ADD:
- Telegram logic
- UI systems
- frontend rendering
- transport logic
- admin systems
- subscriptions
- premium systems
- orchestration duplication

This file must remain:
- lightweight
- centralized
- policy-oriented
- Executor-connected
- future-expandable
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
# 🧠 PROVIDER PRIORITIES
# =========================================================

"""
Provider routing authority.

Executor consults this core
before model escalation.
"""

TEXT_PROVIDER = "openai"

VISION_PROVIDER = "gemini"

VOICE_PROVIDER = "openai"

# =========================================================
# 🧠 PRIMARY MODELS
# =========================================================

"""
Main cognitive execution models.
"""

TEXT_MODEL = "gpt-4o-mini"

VISION_FALLBACK_MODEL = "gpt-4.1-mini"

VOICE_MODEL = "gpt-4o-mini-transcribe"

IMAGE_MODEL = "gpt-image-1"

# =========================================================
# 🧠 EXECUTION LIMITS
# =========================================================

"""
Lightweight execution stabilization.
"""

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

"""
Renderer-first architecture.

Heavy image generation is NOT
the default execution path.
"""

IMAGE_SIZE = "512x512"

IMAGE_QUALITY = "low"

RENDERER_FIRST = True

EXPLICIT_IMAGE_GENERATION_ONLY = True

BLOCK_HIDDEN_IMAGE_ESCALATION = True

BLOCK_AUTO_IMAGE_FALLBACKS = True

# =========================================================
# 🧠 CONTINUITY POLICY
# =========================================================

"""
April continuity stabilization.
"""

VISUAL_CONTINUITY_ENABLED = True

TEXT_CONTINUITY_ENABLED = True

SCENE_MEMORY_ENABLED = True

# =========================================================
# 🧠 EXECUTION STABILIZATION POLICY
# =========================================================

"""
Global execution safety rules.
"""

LIGHTWEIGHT_EXECUTION_PRIORITY = True

CALM_ORCHESTRATION_MODE = True

ALLOW_PROVIDER_ESCALATION = False

ALLOW_RECURSIVE_GENERATION = False

ALLOW_HEAVY_FALLBACK_CHAINS = False

# =========================================================
# 🧠 PROVIDER ROUTING POLICY
# =========================================================

def build_provider_policy_payload():

    """
    Central provider routing payload.

    Used internally by Executor.
    """

    return {

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

# =========================================================
# 🧠 EXECUTION POLICY PAYLOAD
# =========================================================

def build_execution_policy_payload():

    """
    Internal execution policy payload.

    Prevents policy duplication across
    cognitive helper cores.
    """

    return {

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

# =========================================================
# 🧠 CONTINUITY POLICY PAYLOAD
# =========================================================

def build_continuity_policy_payload():

    """
    Continuity stabilization payload.

    Shared internally across:
    - Executor
    - renderer rooms
    - memory systems
    - visual systems
    """

    return {

        "channel":
            POLICY_RESPONSE_CHANNEL,

        "visual_continuity":
            VISUAL_CONTINUITY_ENABLED,

        "text_continuity":
            TEXT_CONTINUITY_ENABLED,

        "scene_memory":
            SCENE_MEMORY_ENABLED
    }

# =========================================================
# 🧠 IMAGE EXECUTION AUTHORITY
# =========================================================

def should_allow_image_generation(

    semantic,
    cognition,
    response_decision
):

    """
    Centralized image escalation authority.

    Prevents hidden generation chaos.
    """

    if not EXPLICIT_IMAGE_GENERATION_ONLY:

        return True

    if semantic.get(
        "render_intent"
    ):

        return False

    if response_decision.get(
        "should_render"
    ):

        return False

    if response_decision.get(
        "avoid_heavy_generation"
    ):

        return False

    if cognition.get(
        "exploration_mode"
    ):

        return False

    explicit_request = semantic.get(
        "explicit_image_generation",
        False
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

    """
    Central provider routing authority.

    Executor asks this helper core
    which provider path should be used.
    """

    semantic = semantic or {}

    cognition = cognition or {}

    # =====================================================
    # 🧠 TEXT TASKS
    # =====================================================

    if task_type == "text":

        return {

            "channel":
                POLICY_RESPONSE_CHANNEL,

            "provider":
                TEXT_PROVIDER,

            "model":
                TEXT_MODEL
        }

    # =====================================================
    # 🧠 VISION TASKS
    # =====================================================

    if task_type in [

        "vision",
        "ocr",
        "analyze_image"
    ]:

        return {

            "channel":
                POLICY_RESPONSE_CHANNEL,

            "provider":
                VISION_PROVIDER,

            "model":
                VISION_FALLBACK_MODEL
        }

    # =====================================================
    # 🧠 VOICE TASKS
    # =====================================================

    if task_type == "voice":

        return {

            "channel":
                POLICY_RESPONSE_CHANNEL,

            "provider":
                VOICE_PROVIDER,

            "model":
                VOICE_MODEL
        }

    # =====================================================
    # 🧠 IMAGE GENERATION
    # =====================================================

    if task_type == "image_generate":

        allow = should_allow_image_generation(

            semantic,

            cognition,

            {}
        )

        if not allow:

            return {

                "channel":
                    POLICY_RESPONSE_CHANNEL,

                "blocked":
                    True,

                "reason":
                    "image_generation_policy"
            }

        return {

            "channel":
                POLICY_RESPONSE_CHANNEL,

            "provider":
                TEXT_PROVIDER,

            "model":
                IMAGE_MODEL
        }

    # =====================================================
    # 🧠 DEFAULT
    # =====================================================

    return {

        "channel":
            POLICY_RESPONSE_CHANNEL,

        "provider":
            TEXT_PROVIDER,

        "model":
            TEXT_MODEL
    }

# =========================================================
# 🧠 EXECUTOR POLICY BRIDGE
# =========================================================

def build_executor_policy_bridge():

    """
    Unified policy bridge payload
    for April Executor.

    Prevents duplicate policy logic
    across helper cores.
    """

    return {

        "channel":
            POLICY_RESPONSE_CHANNEL,

        "provider_policy":
            build_provider_policy_payload(),

        "execution_policy":
            build_execution_policy_payload(),

        "continuity_policy":
            build_continuity_policy_payload(),

        "renderer_first":
            True,

        "lightweight_execution":
            True,

        "stable_orchestration":
            True
    }
