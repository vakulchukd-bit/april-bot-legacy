# =========================================================
# 🧠 APRIL CENTRAL BRAIN CORE
# =========================================================

"""
APRIL CENTRAL BRAIN CORE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEW GOLDEN ARCHITECTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file is now:

✅ semantic orchestration core
✅ trajectory-aware machine router
✅ modality synchronization center
✅ scene-first coordination layer
✅ machine-language execution hub
✅ continuity-safe room dispatcher
✅ renderer-aware executor
✅ unified response contract authority

This file is NOT:

❌ trigger router
❌ keyword dispatcher
❌ telegram-style controller
❌ text-first chatbot core
❌ frontend renderer
❌ ui formatter
❌ transport pipeline

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 GOLDEN FLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Human Layer
    ↓
BotRoot / Web
    ↓
Human → Machine Translator
    ↓
APRIL CENTRAL BRAIN
    ↓
Semantic State
Trajectory
Scene Continuity
Modality Context
    ↓
TASK CHANNEL
    ↓
Rooms
    ↓
RESPONSE CHANNEL
    ↓
Unified Machine Payload
    ↓
BotRoot Human Translator
    ↓
Web Renderer Space

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 GOLDEN RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Rooms NEVER compete using keywords.

2. Routing is based on:
- trajectory
- modality
- continuity
- semantic intent
- scene ownership

3. Human language NEVER routes rooms directly.

4. Machine channels are isolated.

5. Scene continuity is higher priority
than trigger words.

6. "show", "continue", "fix", "this"
must inherit active trajectory.

7. Renderer payloads are sacred.

Never flatten:
- graph
- formula
- diagram
- scene
- layout
- multimodal blocks

8. Executor owns orchestration.

Rooms only execute cognition tasks.
"""

# =========================================================
# 🔥 CORE IMPORTS
# =========================================================

import traceback
import time

from datetime import datetime

# =========================================================
# 🧠 COGNITIVE SYSTEMS
# =========================================================

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
# 🧠 MEMORY + CONTEXT
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
    build_deephub_context
)

# =========================================================
# 🧠 ROOMS
# =========================================================

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
# 🧠 PRESENTATION
# =========================================================

from blocks.presentation_formatter import (
    format_response_presentation
)

# =========================================================
# 🧠 EXPERIENCE
# =========================================================

from blocks.energy_manager import (
    get_energy
)

from blocks.experience import (
    update_experience,
    load_experience
)

# =========================================================
# 🔥 MACHINE CHANNELS
# =========================================================

TASK_CHANNEL = {

    "type": "machine_task_channel",

    "isolated": True,

    "human_access": False
}

RESPONSE_CHANNEL = {

    "type": "machine_response_channel",

    "isolated": True,

    "human_access": False
}

# =========================================================
# 🔥 EXECUTION MAP
# =========================================================

EMAPS = {

    "active_rooms": set(),

    "active_trajectories": set(),

    "active_modalities": set(),

    "execution_sessions": [],

    "machine_routes": []
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
# 🔥 TRACKERS
# =========================================================

def track_room(name):

    if not name:
        return

    EMAPS[
        "active_rooms"
    ].add(name)


def track_trajectory(name):

    if not name:
        return

    EMAPS[
        "active_trajectories"
    ].add(name)


def track_modality(name):

    if not name:
        return

    EMAPS[
        "active_modalities"
    ].add(name)

# =========================================================
# 🔥 RESPONSE VALIDATION
# =========================================================

def validate_machine_response(
    result
):

    if not result:
        return False

    if not isinstance(
        result,
        dict
    ):

        return False

    blocked = [

        "traceback",
        "system prompt",
        "internal reasoning",
        "execution room",
        "cognitive state"
    ]

    payload = str(result)

    lower = payload.lower()

    for word in blocked:

        if word in lower:
            return False

    return True

# =========================================================
# 🔥 TASK TYPE
# =========================================================

def detect_task_type(
    semantic,
    cognition,
    state
):

    scene_state = state.get(
        "scene_state",
        {}
    )

    trajectory = scene_state.get(
        "trajectory"
    )

    if trajectory:

        track_trajectory(
            trajectory
        )

    if semantic.get(
        "render_intent"
    ):

        track_modality(
            "renderer"
        )

        return "renderer"

    if semantic.get(
        "visual_generation_needed"
    ):

        track_modality(
            "image"
        )

        return "image"

    if semantic.get(
        "math_intent"
    ):

        track_modality(
            "math"
        )

        return "math"

    return "text"

# =========================================================
# 🔥 EXECUTOR CONTEXT
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

    scene_state = state.get(
        "scene_state",
        {}
    )

    active_flow = state.get(
        "active_flow"
    )

    return {

        # =================================================
        # 🔥 MACHINE
        # =====================================================

        "machine_channel":
            TASK_CHANNEL,

        "task_type":
            task_type,

        "executor_version":
            "golden_machine_architecture",

        # =================================================
        # 🔥 USER
        # =====================================================

        "user_id":
            user_id,

        "chat_id":
            chat_id,

        # =================================================
        # 🔥 CORE
        # =====================================================

        "semantic":
            semantic,

        "reasoning":
            reasoning,

        "cognition":
            cognition,

        "response_decision":
            response_decision,

        "visual_reference":
            visual_reference,

        # =================================================
        # 🔥 CONTINUITY
        # =====================================================

        "scene_state":
            scene_state,

        "active_flow":
            active_flow,

        "trajectory":
            scene_state.get(
                "trajectory"
            ),

        "continuity_mode":
            scene_state.get(
                "continuity_mode"
            ),

        # =================================================
        # 🔥 MACHINE INPUT
        # =====================================================

        "machine_input":
            text,

        # =================================================
        # 🔥 FULL STATE
        # =====================================================

        "state":
            state
    }

# =========================================================
# 🔥 ROOM SCORING
# =========================================================

def stabilize_room_score(

    room,
    score,
    semantic,
    cognition,
    response_decision,
    state
):

    scene_state = state.get(
        "scene_state",
        {}
    )

    active_room = scene_state.get(
        "active_room"
    )

    # =====================================================
    # 🔥 ACTIVE ROOM CONTINUITY
    # =====================================================

    if active_room:

        if room.name == active_room:

            score += 4.0

    # =====================================================
    # 🔥 RENDERER PRIORITY
    # =====================================================

    if response_decision.get(
        "renderer_first_mode"
    ):

        if room.name in [

            "science",
            "renderer",
            "graph"
        ]:

            score += 5.0

    # =====================================================
    # 🔥 VISUAL GENERATION CONTROL
    # =====================================================

    if response_decision.get(
        "avoid_heavy_generation"
    ):

        if room.name in [

            "image_generate",
            "image_edit"
        ]:

            score -= 8.0

    # =====================================================
    # 🔥 TRAJECTORY LOCK
    # =====================================================

    if cognition.get(
        "trajectory_locked"
    ):

        room_type = getattr(
            room,
            "room_type",
            None
        )

        active_type = scene_state.get(
            "active_room_type"
        )

        if (

            room_type
            and active_type
            and room_type == active_type
        ):

            score += 3.0

    return clamp(
        score,
        -10.0,
        20.0
    )

# =========================================================
# 🔥 ROOM EXECUTION
# =========================================================

async def execute_rooms(

    user_id,
    text,
    context,
    semantic,
    cognition,
    response_decision,
    state,
    run_with_activity
):

    scored_rooms = []

    # =====================================================
    # 🔥 EVALUATION
    # =====================================================

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

                response_decision=response_decision,

                state=state
            )

            if score <= 0:
                continue

            scored_rooms.append(
                (score, room)
            )

        except Exception as e:

            print(
                f"ROOM EVALUATION ERROR [{room.name}]",
                e
            )

    # =====================================================
    # 🔥 SORT
    # =====================================================

    scored_rooms.sort(

        key=lambda x: x[0],

        reverse=True
    )

    # =====================================================
    # 🔥 EXECUTION
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

                "trajectory":
                    context.get(
                        "trajectory"
                    ),

                "scene_state":
                    context.get(
                        "scene_state"
                    ),

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

            if not validate_machine_response(
                result
            ):

                continue

            override = should_override(

                result=result,

                semantic=semantic,

                cognition=cognition,

                state=state
            )

            if override:

                continue

            machine_response_payload = {

                "channel":
                    RESPONSE_CHANNEL,

                "room":
                    room.name,

                "trajectory":
                    context.get(
                        "trajectory"
                    ),

                "result":
                    result
            }

            return machine_response_payload

        except Exception as e:

            print(
                f"ROOM EXECUTION ERROR [{room.name}]",
                e
            )

            traceback.print_exc()

    return None

# =========================================================
# 🚀 APRIL EXECUTOR
# =========================================================

async def execute(

    user_id,
    text,
    chat_id,
    run_with_activity,
    callback_data=None
):

    print(
        "🧠 APRIL GOLDEN EXECUTOR ACTIVE"
    )

    text = normalize_text(
        text
    )

    state = get_state(
        user_id
    )

    mode = get_mode(
        user_id
    )

    # =====================================================
    # 🔥 SEMANTIC
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

    # =====================================================
    # 🔥 REASONING
    # =====================================================

    reasoning = build_reasoning_state(

        text=text,

        state=state,

        semantic=semantic
    )

    # =====================================================
    # 🔥 COGNITION
    # =====================================================

    cognition = analyze_cognition(

        text=text,

        state=state,

        semantic=semantic,

        reasoning=reasoning
    )

    # =====================================================
    # 🔥 PERSONALITY
    # =====================================================

    cognition = apply_april_personality(

        cognition=cognition,

        semantic=semantic,

        reasoning=reasoning,

        response_decision={},

        state=state
    )

    # =====================================================
    # 🔥 VISUAL REFERENCE
    # =====================================================

    visual_reference = (

        build_visual_reference(

            semantic=semantic,

            cognition=cognition,

            text=text,

            state=state
        )
    )

    # =====================================================
    # 🔥 RESPONSE DECISION
    # =====================================================

    response_decision = (

        build_response_decision(

            semantic=semantic,

            cognition=cognition,

            visual_reference=visual_reference,

            state=state
        )
    )

    # =====================================================
    # 🔥 AUTHORITY
    # =====================================================

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
    # 🔥 MEMORY
    # =====================================================

    add_dialog(

        user_id,

        "user",

        text
    )

    update_memory_summary(

        state,

        text,

        ""
    )

    # =====================================================
    # 🔥 TASK TYPE
    # =====================================================

    task_type = detect_task_type(

        semantic,

        cognition,

        state
    )

    # =====================================================
    # 🔥 EXECUTOR CONTEXT
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
    # 🔥 ROOM EXECUTION
    # =====================================================

    room_response = await execute_rooms(

        user_id=user_id,

        text=text,

        context=context,

        semantic=semantic,

        cognition=cognition,

        response_decision=response_decision,

        state=state,

        run_with_activity=run_with_activity
    )

    # =====================================================
    # 🔥 ROOM SUCCESS
    # =====================================================

    if room_response:

        result = room_response.get(
            "result",
            {}
        )

        result_payload = result.get(
            "data"
        )

        if result_payload:

            add_dialog(

                user_id,

                "assistant",

                str(result_payload)[:1200]
            )

            update_memory_summary(

                state,

                text,

                str(result_payload)[:500]
            )

        return result
        
    # =====================================================
    # 🔥 FALLBACK
    # =====================================================

    energy = get_energy(
        user_id
    )

    context_text = build_deephub_context(

        user_id,

        text,

        state
    )

    print(
        "🔥 EXECUTOR FALLBACK START"
    )

    print(
        "🔥 run_with_activity:",
        type(run_with_activity)
    )

    print(
        "🔥 energy:",
        energy
    )

    try:

        if run_with_activity:

            print(
                "🔥 USING ACTIVITY WRAPPER"
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

        else:

            print(
                "🔥 NO ACTIVITY WRAPPER"
            )

            fallback_result = await text_process(

                user_id,

                context_text,

                state,

                energy
            )

        print(
            "🔥 FALLBACK RESULT TYPE:",
            type(fallback_result)
        )

        print(
            "🔥 FALLBACK RESULT:",
            fallback_result
        )

    except Exception as e:

        print(
            "🔥 FALLBACK CRASH:",
            e
        )

        traceback.print_exc()

        return {

            "type": "text",

            "data":
                f"⚠️ FALLBACK ERROR: {e}"
        }
    
    # =====================================================
    # 🔥 FORMAT
    # =====================================================

    if (

        fallback_result
        and fallback_result.get(
            "content"
        )
    ):

        formatted = (

            format_response_presentation(

                text=fallback_result[
                    "content"
                ],

                user_text=text,

                semantic=semantic,

                cognition=cognition,

                response_decision=response_decision,

                visual_reference=visual_reference
            )
        )

        add_dialog(

            user_id,

            "assistant",

            str(formatted)[:1200]
        )

        update_memory_summary(

            state,

            text,

            str(formatted)[:500]
        )

        return {

            "type": "text",

            "data": formatted
        }

    # =====================================================
    # 🔥 FINAL SAFETY
    # =====================================================

    return {

        "type": "text",

        "data":
            "⚠️ April temporarily could not stabilize this trajectory."
    }
