# =========================================================
# 🧠 APRIL CENTRAL BRAIN CORE
# =========================================================

"""
APRIL CENTRAL BRAIN CORE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MAIN ROLE:
This file is the MAIN BRAIN of April.

This is NOT:
- Telegram pipeline
- UI layer
- transport layer
- frontend renderer
- payment system
- admin system

This file IS:
- April orchestration intelligence
- cognitive routing center
- machine-language coordination layer
- room synchronization system
- execution authority core

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 APRIL ARCHITECTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User
 ↓
BotRoot / Web Router
 ↓
APRIL CENTRAL BRAIN CORE (THIS FILE)
 ↓
Cognitive / System / Helper Rooms
 ↓
Machine Response Assembly
 ↓
BotRoot Human Formatting Layer
 ↓
Web User

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 IMPORTANT PRINCIPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. April is ONE personality.
All rooms are helper cognition systems of April.

2. Rooms are NOT isolated personalities.
They are internal intelligence extensions.

3. Machine channels are isolated.

TASK CHANNEL:
Executor → Rooms

RESPONSE CHANNEL:
Rooms → Executor

Human layer NEVER enters internal routing.

4. BotRoot NEVER communicates directly with rooms.

ONLY:
BotRoot ↔ Executor ↔ Rooms

5. This file MUST remain clean and stable.

DO NOT RE-ADD:
- Telegram
- aiogram
- subscriptions
- premium systems
- admin panels
- legacy payment logic
- map scanners
- heavy UI logic
- frontend rendering
- transport formatting

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 APRIL SPACE PHILOSOPHY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- calm orchestration
- continuity-first execution
- renderer-safe routing
- cognitive synchronization
- stable machine communication
- human-safe output isolation
"""

# =========================================================
# 🔥 CORE IMPORTS
# =========================================================

import traceback
import re

from datetime import datetime

# =========================================================
# 🧠 COGNITIVE SYSTEMS
# =========================================================

"""
All imported systems below are helper cognition
extensions of April central intelligence.
"""

from blocks.semantic_core import (
    analyze as semantic_analyze
)

from blocks.goal_engine import (
    detect_goal
)

from blocks.reasoning_state import (
    build_reasoning_state
)

from blocks.cognitive_core import (
    analyze_cognition
)

from blocks.response_decision import (
    build_response_decision
)

from blocks.visual_reference_system import (
    build_visual_reference
)

from blocks.april_personality import (
    apply_april_personality
)

from blocks.april_authority import (

    should_override,

    build_authority_decision
)

# =========================================================
# 🧠 MEMORY + STATE
# =========================================================

from blocks.state_manager import (

    get_state,

    add_dialog,

    update_memory_summary,

    get_active_flow
)

from blocks.mode_manager import (
    get_mode
)

from blocks.context_system import (
    build_context_text
)

# =========================================================
# 🧠 EXECUTION ROOMS
# =========================================================

"""
Rooms are internal execution spaces of April.

They receive:
- machine task payloads

They return:
- machine response payloads
"""

from blocks.rooms_registry import (
    ROOMS
)

# =========================================================
# 🧠 TEXT FALLBACK
# =========================================================

from blocks.text_module import (
    process as text_process
)

# =========================================================
# 🧠 PRESENTATION SAFETY
# =========================================================

from blocks.presentation_formatter import (
    format_response_presentation
)

# =========================================================
# 🧠 ENERGY + EXPERIENCE
# =========================================================

from blocks.energy_manager import (
    get_energy
)

from blocks.experience import (
    update_experience,
    load_experience
)

# =========================================================
# 🧠 INTERNAL EXECUTION MAP
# =========================================================

"""
Internal monitoring metadata.

NOT exposed to BotRoot.
NOT exposed to users.
"""

EMAPS = {

    "active_systems": set(),

    "active_rooms": set(),

    "routing_chains": [],

    "task_types": set(),

    "execution_sessions": []
}

# =========================================================
# 🔥 MACHINE CHANNELS
# =========================================================

"""
Two isolated machine channels exist inside April.

1. TASK CHANNEL
Executor → Rooms

2. RESPONSE CHANNEL
Rooms → Executor

This isolation prevents:
- response corruption
- orchestration leakage
- human-layer contamination
"""

TASK_CHANNEL = {

    "channel": "machine_task_channel",

    "isolated": True
}

RESPONSE_CHANNEL = {

    "channel": "machine_response_channel",

    "isolated": True
}

# =========================================================
# 🔥 HELPERS
# =========================================================

def normalize_text(text):

    return (
        text or ""
    ).strip()


def clamp(
    value,
    minimum=0.0,
    maximum=1.0
):

    if value < minimum:
        return minimum

    if value > maximum:
        return maximum

    return value

# =========================================================
# 🧠 EXECUTION TRACKING
# =========================================================

def track_system(name):

    if not name:
        return

    EMAPS[
        "active_systems"
    ].add(name)


def track_room(name):

    if not name:
        return

    EMAPS[
        "active_rooms"
    ].add(name)


def track_task(task_type):

    if not task_type:
        return

    EMAPS[
        "task_types"
    ].add(task_type)

# =========================================================
# 🧠 RESPONSE QUALITY
# =========================================================

def evaluate_response_quality(result):

    """
    Prevents unstable or corrupted
    machine payloads from escaping rooms.
    """

    if not result:

        return False

    output = str(
        result.get("data", "")
    ).strip()

    if len(output) <= 5:

        return False

    blocked_words = [

        "traceback",
        "pipeline",
        "syntaxerror",
        "execution room"
    ]

    if any(
        x in output.lower()
        for x in blocked_words
    ):

        return False

    return True

# =========================================================
# 🧠 TASK TYPE DETECTION
# =========================================================

def detect_task_type(text):

    t = normalize_text(
        text
    ).lower()

    renderer_words = [

        "diagram",
        "scene",
        "layout",
        "renderer",
        "graph",
        "formula"
    ]

    if any(
        x in t
        for x in renderer_words
    ):

        return "renderer_scene"

    image_words = [

        "image",
        "photo",
        "picture",
        "draw",
        "render"
    ]

    if any(
        x in t
        for x in image_words
    ):

        return "image"

    math_words = [

        "equation",
        "function",
        "solve",
        "math",
        "graph"
    ]

    if any(
        x in t
        for x in math_words
    ):

        return "math"

    return "text"

# =========================================================
# 🧠 EXECUTOR CONTEXT
# =========================================================

def build_executor_context(

    user_id,
    chat_id,
    state,
    semantic,
    reasoning,
    cognition,
    response_decision,
    visual_reference,
    task_type,
    text
):

    """
    Builds unified machine context for all rooms.

    Rooms NEVER receive raw human-layer state.
    """

    return {

        "user_id": user_id,

        "chat_id": chat_id,

        "task_type": task_type,

        "semantic": semantic,

        "reasoning": reasoning,

        "cognition": cognition,

        "response_decision":
            response_decision,

        "visual_reference":
            visual_reference,

        "state": state,

        "machine_channel":
            TASK_CHANNEL,

        "text": text
    }

# =========================================================
# 🧠 ROOM SCORING
# =========================================================

def stabilize_room_score(

    room,
    score,
    semantic,
    cognition,
    response_decision
):

    """
    Stabilizes orchestration behavior
    between cognitive rooms.
    """

    if semantic.get(
        "render_intent"
    ):

        if room.name == "science":

            score += 5.0

    if cognition.get(
        "prefer_visual"
    ):

        if room.name in [

            "image_generate",
            "image_edit"
        ]:

            score += 2.0

    if response_decision.get(
        "avoid_heavy_generation"
    ):

        if room.name in [

            "image_generate",
            "image_edit"
        ]:

            score -= 5.0

    return clamp(
        score,
        -5.0,
        15.0
    )

# =========================================================
# 🧠 ROOM EXECUTION PIPELINE
# =========================================================

async def execute_rooms(

    user_id,
    text,
    context,
    semantic,
    cognition,
    response_decision,
    run_with_activity
):

    """
    Central room orchestration system.

    Flow:
    Executor
      ↓
    TASK CHANNEL
      ↓
    Rooms
      ↓
    RESPONSE CHANNEL
      ↓
    Executor
    """

    scored_rooms = []

    for room in ROOMS:

        try:

            score = room.evaluate(
                text,
                context
            )

            score = stabilize_room_score(

                room=room,

                score=score,

                semantic=semantic,

                cognition=cognition,

                response_decision=response_decision
            )

            if score <= 0:
                continue

            scored_rooms.append(
                (score, room)
            )

        except Exception as e:

            print(
                f"ROOM SCORE ERROR [{room.name}]",
                e
            )

    scored_rooms.sort(

        key=lambda x: x[0],

        reverse=True
    )

    # =====================================================
    # 🧠 EXECUTION LOOP
    # =====================================================

    for score, room in scored_rooms:

        try:

            track_room(
                room.name
            )

            machine_task_payload = {

                "channel":
                    TASK_CHANNEL,

                "room":
                    room.name,

                "context":
                    context
            }

            result = await room.handle(

                user_id,

                text,

                machine_task_payload,

                run_with_activity
            )

            if not result:
                continue

            machine_response_payload = {

                "channel":
                    RESPONSE_CHANNEL,

                "room":
                    room.name,

                "result":
                    result
            }

            if not evaluate_response_quality(
                result
            ):

                continue

            override = should_override(

                result=result,

                semantic=semantic,

                cognition=cognition,

                state=context.get(
                    "state",
                    {}
                )
            )

            if override:

                continue

            return machine_response_payload

        except Exception as e:

            print(
                f"ROOM EXECUTION ERROR [{room.name}]",
                e
            )

            traceback.print_exc()

    return None

# =========================================================
# 🚀 APRIL CENTRAL EXECUTOR
# =========================================================

async def execute(

    user_id,
    text,
    chat_id,
    run_with_activity,
    callback_data=None
):

    """
    MAIN APRIL EXECUTION ENTRYPOINT.

    This is the central orchestration brain
    of the entire April system.
    """

    print("🧠 APRIL CENTRAL BRAIN ACTIVE")

    state = get_state(
        user_id
    )

    mode = get_mode(
        user_id
    )

    # =====================================================
    # 🧠 SEMANTIC ANALYSIS
    # =====================================================

    semantic = semantic_analyze(

        text=text,

        state=state,

        history=state.get(
            "dialog",
            []
        ),

        active_flow=get_active_flow(
            user_id
        ),

        dialog_state=state.get(
            "dialog_state",
            {}
        )
    )

    semantic = detect_goal(

        text=text,

        state=state,

        semantic=semantic
    )

    reasoning = build_reasoning_state(

        text=text,

        state=state,

        semantic=semantic
    )

    cognition = analyze_cognition(

        text=text,

        state=state,

        semantic=semantic,

        reasoning=reasoning
    )

    # =====================================================
    # 🧠 APRIL PERSONALITY
    # =====================================================

    cognition = apply_april_personality(

        cognition=cognition,

        semantic=semantic,

        reasoning=reasoning,

        response_decision={},

        state=state
    )

    # =====================================================
    # 🧠 VISUAL + RESPONSE DECISION
    # =====================================================

    visual_reference = (

        build_visual_reference(

            semantic=semantic,

            cognition=cognition,

            text=text,

            state=state
        )
    )

    response_decision = (

        build_response_decision(

            semantic=semantic,

            cognition=cognition,

            visual_reference=visual_reference,

            state=state
        )
    )

    authority_decision = (

        build_authority_decision(

            result={

                "type": "pre_execution",

                "data": ""
            },

            semantic=semantic,

            cognition=cognition,

            response_decision=response_decision,

            state=state
        )
    )

    # =====================================================
    # 🧠 MEMORY UPDATE
    # =====================================================

    add_dialog(

        user_id,
        "user",
        text
    )

    update_memory_summary(

        user_id,
        text
    )

    # =====================================================
    # 🧠 TASK DETECTION
    # =====================================================

    task_type = semantic.get(
        "intent"
    ) or detect_task_type(text)

    track_task(
        task_type
    )

    # =====================================================
    # 🧠 EXECUTOR CONTEXT
    # =====================================================

    context = build_executor_context(

        user_id=user_id,

        chat_id=chat_id,

        state=state,

        semantic=semantic,

        reasoning=reasoning,

        cognition=cognition,

        response_decision=response_decision,

        visual_reference=visual_reference,

        task_type=task_type,

        text=text
    )

    # =====================================================
    # 🧠 ROOM EXECUTION
    # =====================================================

    room_response = await execute_rooms(

        user_id=user_id,

        text=text,

        context=context,

        semantic=semantic,

        cognition=cognition,

        response_decision=response_decision,

        run_with_activity=run_with_activity
    )

    # =====================================================
    # 🧠 SUCCESS RESPONSE
    # =====================================================

    if room_response:

        result = room_response.get(
            "result"
        )

        output_text = str(
            result.get("data", "")
        )

        if output_text.strip():

            add_dialog(

                user_id,

                "assistant",

                output_text
            )

            update_memory_summary(

                user_id,

                output_text
            )

        return result

    # =====================================================
    # 🧠 SAFE FALLBACK
    # =====================================================

    energy = get_energy(
        user_id
    )

    context_text = build_context_text(

        user_id,
        text,
        state
    )

    fallback_result = await run_with_activity(

        chat_id,

        text_process(

            user_id,

            context_text,

            state,

            energy
        )
    )

    if (

        fallback_result
        and fallback_result.get(
            "content"
        )
    ):

        fallback_content = (

            format_response_presentation(

                text=fallback_result["content"],

                user_text=text,

                semantic=semantic,

                cognition=cognition,

                visual_reference=visual_reference
            )
        )

        add_dialog(

            user_id,

            "assistant",

            fallback_content
        )

        update_memory_summary(

            user_id,

            fallback_content
        )

        return {

            "type": "text",

            "data": fallback_content
        }

    # =====================================================
    # 🧠 FINAL SAFETY RETURN
    # =====================================================

    return {

        "type": "text",

        "data":
            "⚠️ April temporarily could not stabilize the request."
    }
