# =========================================================
# 🧠 APRIL COGNITIVE ANCHOR CORE
# =========================================================

"""
APRIL COGNITIVE ANCHOR CORE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ROLE IN APRIL:
This file is the cognitive continuity
and trajectory stabilization core of April.

This helper core helps April:
- hold attention
- maintain continuity
- stabilize active flows
- preserve execution direction
- track conversational trajectory
- connect multi-step reasoning

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 WHAT THIS FILE IS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file IS:
- continuity anchor system
- cognitive focus holder
- active trajectory tracker
- scene continuation stabilizer
- execution continuity helper
- multi-step flow anchor

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 WHAT THIS FILE IS NOT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file is NOT:
- memory system
- orchestration engine
- response formatter
- frontend renderer
- Telegram logic
- analytics system
- personality core
- routing authority

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 WHY THIS FILE EXISTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Executor distributes tasks across rooms.

This helper core helps April:
- understand what is currently active
- preserve execution direction
- continue scenes correctly
- maintain cognitive focus
- avoid execution confusion
- stabilize multi-room execution

Without this system:
- scenes can break
- continuation can drift
- flows can mix together
- April can lose active focus

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 APRIL ARCHITECTURE POSITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BotRoot
 ↓
Executor
 ↓
Cognitive Anchor Core (THIS FILE)
 ↓
Execution Rooms

Executor asks this helper core:
- what is currently active?
- what trajectory is ongoing?
- what scene should continue?
- what flow is stabilized?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 GOLDEN MACHINE CHANNEL RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file operates using TWO isolated channels.

1. ANCHOR TASK CHANNEL
Executor → Anchor Core

2. ANCHOR RESPONSE CHANNEL
Anchor Core → Executor

Human-layer responses NEVER enter
internal continuity orchestration.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 IMPORTANT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DO NOT RE-ADD:
- Telegram logic
- frontend rendering
- response formatting
- subscriptions
- admin systems
- analytics logic
- orchestration duplication

This file must remain:
- lightweight
- continuity-focused
- Executor-connected
- Web-oriented
- cognition-safe
"""

# =========================================================
# 🧠 MACHINE CHANNELS
# =========================================================

ANCHOR_TASK_CHANNEL = {

    "channel":
        "anchor_machine_task_channel",

    "isolated":
        True
}

ANCHOR_RESPONSE_CHANNEL = {

    "channel":
        "anchor_machine_response_channel",

    "isolated":
        True
}

# =========================================================
# 🧠 ACTIVE COGNITIVE ANCHORS
# =========================================================

"""
Active continuity anchors.

Stores ONLY:
- current focus
- active trajectory
- continuation targets
- execution stabilization references

This is NOT long-term memory.
"""

anchors = {}

# =========================================================
# 🧠 CREATE ANCHOR
# =========================================================

def create_anchor(

    user_id,
    anchor_type,
    base
):

    """
    Creates active cognitive anchor.

    Example:
    - active scene
    - active reasoning flow
    - active visual trajectory
    - active execution branch
    """

    anchors[user_id] = {

        "type":
            anchor_type,

        "base":
            base,

        "current":
            base,

        "trajectory":
            "active",

        "continuity":
            True,

        "machine_channel":
            ANCHOR_RESPONSE_CHANNEL
    }

    return {

        "success": True,

        "channel":
            ANCHOR_RESPONSE_CHANNEL
    }

# =========================================================
# 🧠 GET ACTIVE ANCHOR
# =========================================================

def get_anchor(user_id):

    """
    Returns active cognitive focus state.

    Executor uses this to:
    - stabilize continuity
    - continue scenes
    - maintain reasoning direction
    """

    anchor = anchors.get(user_id)

    if not anchor:

        return None

    return {

        "channel":
            ANCHOR_RESPONSE_CHANNEL,

        "anchor":
            anchor
    }

# =========================================================
# 🧠 UPDATE ANCHOR
# =========================================================

def update_anchor(

    user_id,
    new_value
):

    """
    Updates active continuity state.

    Used when:
    - trajectory changes
    - scene evolves
    - reasoning expands
    - execution flow continues
    """

    if user_id not in anchors:

        return {

            "success": False,

            "reason":
                "anchor_not_found"
        }

    anchors[user_id][
        "current"
    ] = new_value

    return {

        "success": True,

        "channel":
            ANCHOR_RESPONSE_CHANNEL
    }

# =========================================================
# 🧠 CLEAR ANCHOR
# =========================================================

def clear_anchor(user_id):

    """
    Clears active continuity focus.

    Used when:
    - flow ends
    - trajectory resets
    - scene closes
    - execution completes
    """

    if user_id in anchors:

        del anchors[user_id]

    return {

        "success": True,

        "channel":
            ANCHOR_RESPONSE_CHANNEL
    }

# =========================================================
# 🧠 CONTINUITY ANALYSIS
# =========================================================

def analyze_continuity_state(user_id):

    """
    Lightweight continuity diagnostics
    for Executor awareness.
    """

    anchor = anchors.get(user_id)

    if not anchor:

        return {

            "channel":
                ANCHOR_RESPONSE_CHANNEL,

            "continuity_active":
                False
        }

    return {

        "channel":
            ANCHOR_RESPONSE_CHANNEL,

        "continuity_active":
            True,

        "anchor_type":
            anchor.get(
                "type"
            ),

        "trajectory":
            anchor.get(
                "trajectory"
            ),

        "current_focus":
            anchor.get(
                "current"
            )
    }

# =========================================================
# 🧠 EXECUTOR CONTINUITY PAYLOAD
# =========================================================

def build_executor_anchor_payload(user_id):

    """
    Internal continuity payload
    for Executor stabilization.

    NEVER exposed directly to users.
    """

    continuity = analyze_continuity_state(
        user_id
    )

    return {

        "channel":
            ANCHOR_RESPONSE_CHANNEL,

        "payload_type":
            "executor_continuity",

        "continuity":
            continuity
    }

# =========================================================
# 🧠 MULTI-ROOM FLOW SUPPORT
# =========================================================

def stabilize_execution_trajectory(

    user_id,
    trajectory_type,
    target
):

    """
    Helps Executor stabilize
    multi-room execution flows.

    Example:
    - renderer continuation
    - visual continuation
    - reasoning continuation
    - multi-block response flow
    """

    if user_id not in anchors:

        create_anchor(

            user_id,

            trajectory_type,

            target
        )

    else:

        anchors[user_id][
            "trajectory"
        ] = trajectory_type

        anchors[user_id][
            "current"
        ] = target

    return {

        "success": True,

        "channel":
            ANCHOR_RESPONSE_CHANNEL,

        "trajectory":
            trajectory_type
    }
