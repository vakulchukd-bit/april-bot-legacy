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

    visual_continuity_summary = state.get(
        "visual_continuity_summary",
        {}
    )

    active_visual_scene = state.get(
        "active_visual_scene",
        {}
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

        "executor_awareness":
            {
                "discussion_mode":
                    response_decision.get("discussion_mode", False),

                "reflection_mode":
                    response_decision.get("reflection_mode", False),

                "space_discussion":
                    response_decision.get("space_discussion", False),

                "tool_discussion":
                    response_decision.get("tool_discussion", False),

                "self_action_discussion":
                    response_decision.get("self_action_discussion", False),

                "explanation_mode":
                    response_decision.get("explanation_mode", False)
            },

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

        "visual_continuity_summary":
            visual_continuity_summary,

        "active_visual_scene":
            active_visual_scene,

        "visual_goal":
            visual_continuity_summary.get(
                "active_goal"
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
            state,

        "memory_routing":
            {
                "dynamic_focus":
                    cognition.get("dynamic_focus", {}),
                "goal_hierarchy":
                    cognition.get("goal_hierarchy", {}),
                "open_loops":
                    cognition.get("open_loops", {}),
                "memory_signals":
                    cognition.get("memory_signals", {})
            }
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


    # =====================================================
    # 🔥 TASK RESOLUTION PRIORITY
    # =====================================================

    task_resolution = state.get(
        "task_resolution",
        {}
    )

    target_room = task_resolution.get(
        "target_room"
    )

    if target_room and room.name == target_room:
        score += 10.0

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
# 🧠 TASK RESOLUTION LAYER
# =========================================================

def build_task_resolution(
    cognition,
    response_decision,
    semantic,
    state
):

    task = cognition.get(
        "task_understanding",
        {}
    )

    next_step = cognition.get(
        "assistant_next_step",
        "ready_to_help"
    )

    confusion = cognition.get(
        "user_confusion",
        0.0
    )

    clarification_required = (
        response_decision.get(
            "task_requires_clarification",
            False
        )
    )

    resolution = {
        "mode": "execute",
        "next_step": next_step,
        "guidance_priority": False,
        "missing_information": task.get(
            "missing_information",
            []
        )
    }

    if clarification_required:
        resolution["mode"] = "clarify"
        resolution["guidance_priority"] = True

    if confusion >= 0.5:
        resolution["guidance_priority"] = True

    return resolution


def build_guidance_response(
    task_resolution
):

    step = task_resolution.get(
        "next_step"
    )

    messages = {
        "request_image":
            "Чтобы помочь точнее, пришли скриншот или изображение того, что ты видишь сейчас.",
        "request_formula":
            "Напиши формулу или опиши задачу своими словами. Если формулу не знаешь, я помогу её подобрать.",
        "request_error_details":
            "Покажи текст ошибки или пришли скриншот окна с ошибкой, и я проведу тебя дальше."
    }

    if step not in messages:
        return None

    return {
        "type": "text",
        "data": messages[step]
    }

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
    collected_results = []
    max_results = 2

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
                    context,

                "awareness":
                    context.get(
                        "executor_awareness",
                        {}
                    )
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

            # ================================================
            # INTERNAL SIGNALS ARE NOT USER ANSWERS
            # ================================================

            result_type = result.get("type")

            if result_type in [
                "internal_guidance",
                "internal_reasoning",
                "internal_state",
                "task_resolution"
            ]:

                state.setdefault(
                    "internal_signals",
                    []
                ).append(result)

                print(
                    f"🔥 INTERNAL SIGNAL [{room.name}]",
                    result_type
                )

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

            print(f"🔥 ROOM COLLECTED [{room.name}]")

            collected_results.append(
                machine_response_payload
            )

            if len(collected_results) >= max_results:
                break

            continue

        except Exception as e:

            print(
                f"ROOM EXECUTION ERROR [{room.name}]",
                e
            )

            traceback.print_exc()

    if collected_results:

        print(
            f"🔥 COLLECTED ROOMS: {len(collected_results)}"
        )

        blocks = []

        for item in collected_results:

            result = item.get("result", {})

            if isinstance(result, dict):
                blocks.append(result)

        return {
            "channel": RESPONSE_CHANNEL,
            "room": "scene",
            "trajectory": context.get("trajectory"),
            "result": {
                "type": "scene",
                "blocks": blocks
            }
        }

    return None


# =========================================================
# 🧠 APRIL ANSWER SYNTHESIS LAYER
# =========================================================

def synthesize_final_answer(
    result,
    cognition,
    response_decision,
    state
):

    if result is None:
        return None

    if not isinstance(result, dict):
        return result

    
    result_type = result.get("type")

    # =====================================================
    # 🔥 EXPLANATION-FIRST STABILIZATION
    # =====================================================
    #
    # If cognition determined that the user wants an
    # explanation of a graph/formula/table, preserve
    # dialogue format and do not force renderer output.
    #
    explanation_pref = (
        cognition.get("representation_understanding", {})
        .get("prefer_text_explanation", False)
    )

    if explanation_pref and result_type == "scene":
        return {
            "type": "text",
            "data": ""
        }

    if result_type != "text":
        return result

    dynamic_focus = cognition.get(
        "dynamic_focus",
        {}
    )

    open_loops = cognition.get(
        "open_loops",
        {}
    )

    memory_signals = cognition.get(
        "memory_signals",
        {}
    )

    result["trajectory_safe"] = True

    result["focus_context"] = (
        dynamic_focus.get(
            "primary_focus"
        )
    )

    result["continuity_priority"] = (
        memory_signals.get(
            "memory_priority",
            0
        )
    )

    result["open_loops_present"] = (
        open_loops.get(
            "has_open_loops",
            False
        )
    )

    result["discussion_context"] = (
        response_decision.get(
            "discussion_mode",
            False
        )
    )

    result["space_context"] = (
        response_decision.get(
            "space_discussion",
            False
        )
    )

    result["action_reason"] = (
        response_decision.get(
            "final_action",
            "dialogue"
        )
    )

    return result


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

    if run_with_activity is None:

        print(
            "🔥 WARNING: run_with_activity IS NONE"
        )

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
    # 🔥 VISUAL CONTINUITY INTEGRATION
    # =====================================================

    visual_continuity = state.get(
        "visual_continuity_summary",
        {}
    )

    cognition["visual_continuity"] = (
        visual_continuity
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
    # 🔥 GOLDEN MEMORY ROUTING LAYER
    # =====================================================

    memory_routing = {

        "dynamic_focus":
            cognition.get("dynamic_focus", {}),

        "goal_hierarchy":
            cognition.get("goal_hierarchy", {}),

        "open_loops":
            cognition.get("open_loops", {}),

        "memory_signals":
            cognition.get("memory_signals", {})
    }

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
    # 🧠 TASK RESOLUTION
    # =====================================================

    task_resolution = build_task_resolution(

        cognition=cognition,

        response_decision=response_decision,

        semantic=semantic,

        state=state
    )

    guidance_response = build_guidance_response(
        task_resolution
    )

    # =====================================================
    # 🔥 INTERNAL GUIDANCE ONLY
    # =====================================================
    #
    # Guidance is executor metadata.
    # It must help routing and rooms.
    # It must NOT become a user response.
    #
    state["task_resolution"] = task_resolution

    if guidance_response:
        state["guidance_response"] = guidance_response

    # =====================================================
    # 🔥 ROOM EXECUTION
    # =====================================================


    print("🔥 EXECUTOR CONTEXT READY")
    print("🔥 CONTEXT CHAT:", chat_id)
    print("🔥 CONTEXT USER:", user_id)
    print("🔥 TASK TYPE:", task_type)
    print("🔥 RUN:", run_with_activity)
    print("🔥 RUN TYPE:", type(run_with_activity))

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

        result = synthesize_final_answer(
            result=result,
            cognition=cognition,
            response_decision=response_decision,
            state=state
        )

        if result is None:

            return {
                "type": "text",
                "data": "⚠️ Empty synthesized result"
            }

        if not isinstance(result, dict):

            return {
                "type": "text",
                "data": str(result)
            }

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


# =========================================================
# 🧠 SCENE-AWARE ROUTING NOTES
# =========================================================
# Executor should consume:
# state["scene_relation"]
# state["scene_history"]
# state["dynamic_focus"]
# and preserve continuity before room switching.


# =========================================================
# 🧠 UNIFIED SCENE ROUTING CONTRACT
# =========================================================
#
# Routing priority order:
# 1. scene_relation
# 2. active_scene
# 3. dynamic_focus
# 4. goal_hierarchy
# 5. open_loops
#
# Rooms receive unified cognition context.
# Internal cognition never becomes renderer output.
#



# =========================================================
# 🧠 EXECUTOR V2 MEMORY + UTC INTEGRATION
# =========================================================

def build_executor_memory_awareness(cognition):

    return {

        "focus_state":
            cognition.get("focus_state", {}),

        "memory_timeline":
            cognition.get("memory_timeline", {}),

        "memory_cycle":
            cognition.get("memory_cycle", {}),

        "timeline_awareness":
            cognition.get("timeline_awareness", {}),

        "executor_guidance":
            cognition.get("executor_guidance", {})
    }


def build_scene_verification(

    result,
    cognition,
    state

):

    verification = {

        "scene_verified": True,

        "continuity_checked": True,

        "memory_checked": True
    }

    guidance = cognition.get(
        "executor_guidance",
        {}
    )

    if guidance.get(
        "executor_should_use_memory"
    ) is False:

        verification[
            "memory_checked"
        ] = False

    return verification


def memory_aware_room_bonus(
    room,
    cognition
):

    bonus = 0.0

    focus_state = cognition.get(
        "focus_state",
        {}
    )

    priority = float(
        focus_state.get(
            "priority_score",
            0
        )
    )

    freshness = float(
        focus_state.get(
            "intent_freshness",
            0
        )
    )

    if priority > 0:
        bonus += min(
            priority,
            5.0
        )

    if freshness > 0:
        bonus += min(
            freshness,
            3.0
        )

    return bonus


def utc_memory_gate(cognition):

    awareness = cognition.get(
        "timeline_awareness",
        {}
    )

    return {

        "utc_enabled":
            awareness.get(
                "utc_enabled",
                False
            ),

        "current_memory_day":
            awareness.get(
                "current_memory_day",
                "day_0"
            )
    }


# =========================================================
# 🧠 MEMORY RECALL ENGINE V3
# =========================================================

def build_memory_recall_context(state):

    timeline = state.get("memory_timeline", {})
    focus_state = state.get("focus_state", {})
    open_loops = state.get("open_loops", [])
    dynamic_focus = state.get("dynamic_focus", {})

    return {
        "today": timeline.get("day_0", {}),
        "yesterday": timeline.get("day_1", {}),
        "focus_state": focus_state,
        "dynamic_focus": dynamic_focus,
        "open_loops": open_loops
    }


def calculate_memory_relevance(memory_context):

    score = 0.0

    if memory_context.get("focus_state"):
        score += 0.3

    if memory_context.get("dynamic_focus"):
        score += 0.3

    if memory_context.get("open_loops"):
        score += 0.2

    if memory_context.get("today"):
        score += 0.2

    return min(score, 1.0)


def build_executor_memory_recall(state):

    memory_context = build_memory_recall_context(state)

    return {
        "memory_context": memory_context,
        "memory_relevance": calculate_memory_relevance(memory_context),
        "memory_active": True
    }

# =========================================================
# END OF MEMORY RECALL ENGINE V3
# =========================================================


# =========================================================
# 🧠 EXECUTOR V4 MEMORY RECALL ACTIVATION
# =========================================================

def build_recall_candidates(state):

    timeline = state.get("memory_timeline", {})

    candidates = []

    for day_name, day_data in timeline.items():

        if not isinstance(day_data, dict):
            continue

        for slot in ["A", "B", "C", "D", "E"]:

            for item in day_data.get(slot, []):

                candidates.append({
                    "day": day_name,
                    "slot": slot,
                    "data": item
                })

    return candidates


def build_memory_recall_payload(state):

    recall = build_executor_memory_recall(state)

    recall["candidates"] = build_recall_candidates(state)

    recall["candidate_count"] = len(
        recall["candidates"]
    )

    return recall

# =========================================================
# END OF EXECUTOR V4 MEMORY RECALL ACTIVATION
# =========================================================


# =========================================================
# 🧠 EXECUTOR V5 UTC MEMORY RECALL SELECTION
# =========================================================

from datetime import datetime, timezone

def get_current_utc_timestamp():
    return datetime.now(timezone.utc).timestamp()

def calculate_memory_age_weight(day_name):
    try:
        day_index = int(str(day_name).replace("day_", ""))
    except Exception:
        day_index = 6
    return max(0.05, 1.0 - (day_index * 0.12))

def score_memory_candidate(candidate, focus_state=None):

    focus_state = focus_state or {}

    score = 0.0

    score += calculate_memory_age_weight(
        candidate.get("day", "day_6")
    )

    data = candidate.get("data", {})

    active_topic = str(
        focus_state.get("active_topic", "")
    ).lower()

    topic = str(
        data.get("topic", "")
    ).lower()

    if active_topic and topic:
        if active_topic in topic or topic in active_topic:
            score += 2.0

    score += float(
        data.get("score", 0.0)
    )

    return score

def build_ranked_memory_recall(state):

    recall = build_memory_recall_payload(state)

    focus_state = state.get(
        "focus_state",
        {}
    )

    ranked = sorted(
        recall.get("candidates", []),
        key=lambda x: score_memory_candidate(
            x,
            focus_state
        ),
        reverse=True
    )

    recall["top_memories"] = ranked[:15]

    recall["utc_timestamp"] = (
        get_current_utc_timestamp()
    )

    return recall




# =========================================================
# 🧠 EXECUTOR V6 LIVE VISION BRIDGE
# =========================================================

def build_live_vision_feed(state):

    return {

        "active_visual_scene":
            state.get("active_visual_scene", {}),

        "visual_continuity_summary":
            state.get(
                "visual_continuity_summary",
                {}
            ),

        "scene_state":
            state.get("scene_state", {}),

        "current_focus":
            state.get("dynamic_focus", {}),

        "runtime_mode":
            "open_tab_live_runtime"
    }


def build_executor_runtime_bridge(state):

    return {

        "memory_recall":
            build_ranked_memory_recall(state),

        "live_vision":
            build_live_vision_feed(state),

        "bridge_ready": True
    }

# =========================================================
# END OF EXECUTOR V6 LIVE VISION BRIDGE
# =========================================================


# =========================================================
# 🧠 EXECUTOR V7 LIVE VISION -> MEMORY TRANSFER
# =========================================================

def build_live_scene_snapshot(state):

    return {
        "active_visual_scene":
            state.get("active_visual_scene", {}),
        "visual_continuity_summary":
            state.get("visual_continuity_summary", {}),
        "scene_state":
            state.get("scene_state", {}),
        "dynamic_focus":
            state.get("dynamic_focus", {}),
        "snapshot_type":
            "tab_close_snapshot"
    }


def transfer_scene_to_today_memory(state):

    snapshot = build_live_scene_snapshot(state)

    memory_timeline = state.setdefault(
        "memory_timeline",
        {}
    )

    today = memory_timeline.setdefault(
        "day_0",
        {}
    )

    today["last_visual_snapshot"] = snapshot

    today["last_visual_transfer_utc"] = (
        datetime.utcnow().isoformat()
    )

    return snapshot


def on_live_session_closed(state):

    snapshot = transfer_scene_to_today_memory(
        state
    )

    state["active_visual_scene"] = {}

    state["visual_continuity_summary"] = {}

    return {
        "transferred": True,
        "snapshot": snapshot
    }

# =========================================================
# END OF EXECUTOR V7 LIVE VISION -> MEMORY TRANSFER
# =========================================================
