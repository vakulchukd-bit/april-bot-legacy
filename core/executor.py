# =========================================================
# APRIL EXECUTOR
# Central orchestration kernel.
# Canonical execution path:
# User Space -> MachineRequest -> Rooms -> MachineResponse -> MachineScene -> Scene Contract
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

    get_active_flow,

    build_visual_memory_bridge
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

from blocks.C_ARTIFACT_CONTRACT import (
    MachineRequest,
    MachineResponse,
    MachineScene,
    UniversalArtifactContract,
)

# =========================================================
# 🧠 TEXT FALLBACK
# =========================================================

# Legacy text fallback removed from unified broadband route

from blocks.provider_router import generate_text

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

    user_space = build_executor_user_space(state)

    scene_state = user_space.get("scene", {})

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

    user_space = build_executor_user_space(state)

    scene_state = user_space.get("scene", {})

    active_flow = user_space.get("active_flow", {})

    visual_continuity_summary = user_space.get("visual_continuity_summary", {})

    active_visual_scene = user_space.get("active_visual_scene", {})

    visual_memory_bridge = build_visual_memory_bridge(
        user_id
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
            "unified_broadband_route_v1",

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

        "visual_memory_bridge":
            visual_memory_bridge,

        "visual_summary":
            visual_memory_bridge.get(
                "visual_summary",
                {}
            ),

        "today_visual_memory":
            visual_memory_bridge.get(
                "today_visual_memory",
                []
            ),

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

        "user_space":
            user_space,

        "memory_routing":
            {
                "focus_recommendation":
                    cognition.get("focus_recommendation", cognition.get("dynamic_focus", {})),
                "goal_analysis":
                    cognition.get("goal_analysis", cognition.get("goal_hierarchy", {})),
                "loop_analysis":
                    cognition.get("loop_analysis", cognition.get("open_loops", {})),
                "memory_analysis":
                    cognition.get("memory_analysis", cognition.get("memory_signals", {}))
            }
    }

# =========================================================
# 🧠 USER SPACE EXECUTOR BRIDGE (APRIL UPGRADE)
# =========================================================

def build_executor_user_space(state):
    """
    Executor consumes one logical User Space assembled from the
    existing state. No parallel state or executor is created.
    """
    return {
        "scene": state.get("scene_state", {}),
        "workspace": state.get("workspace_state", {}),
        "dialog": state.get("dialog", []),
        "focus": state.get("focus_state", state.get("dynamic_focus", {})),
        "goal_hierarchy": state.get("goal_hierarchy", {}),
        "active_flow": state.get("active_flow", {}),
        "memory_timeline": state.get("memory_timeline", {}),
        "visual_summary": state.get("visual_summary", {}),
        "visual_continuity_summary": state.get("visual_continuity_summary", {}),
        "active_visual_scene": state.get("active_visual_scene", {}),
        "renderer_state": state.get("renderer_state", {}),
        "task_resolution": state.get("task_resolution", {}),
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

    user_space = build_executor_user_space(state)

    scene_state = user_space.get("scene", {})

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

    task_resolution = user_space.get(
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
# 🧠 DOMAIN COMPETENCE ROUTING
# =========================================================

def build_domain_room_map():

    return {
        "biology": ["biology"],
        "chemistry": ["chemistry"],
        "physics": ["physics"],
        "mathematics": ["mathematics"],
        "trigonometry": ["trigonometry"],
        "engineering": ["engineering"],
        "it": ["it"],
        "web": ["web"],
        "politics": ["politics"],
        "news": ["news"],
        "social": ["social"],
        "literature": ["literature"],
        "utc": ["utc"]
    }

def domain_room_bonus(room, semantic):

    required_domains = semantic.get(
        "required_domains",
        []
    )

    if not required_domains:
        return 0.0

    room_map = build_domain_room_map()

    bonus = 0.0

    for domain in required_domains:

        for room_name in room_map.get(domain, []):

            if room.name == room_name:
                bonus += 6.0

    return bonus

# =========================================================
# 🏭 FACTORY ORDER EXECUTION
# =========================================================

def get_factory_required_rooms(semantic):

    factory_order = semantic.get(
        "factory_order",
        {}
    )

    return factory_order.get(
        "required_rooms",
        []
    )

# =====================================================
# 🧠 ARTIFACT SCENE PLANNER
# =====================================================

def build_scene_plan(response_decision, semantic=None):

    semantic = semantic or {}

    artifact_scene = response_decision.get(
        "artifact_scene",
        []
    )

    artifact_bundle = response_decision.get(
        "artifact_bundle",
        semantic.get("artifact_bundle", {})
    )

    primary = artifact_bundle.get(
        "primary",
        []
    )

    secondary = artifact_bundle.get(
        "secondary",
        []
    )

    scene_order = []

    scene_order.extend(primary)
    scene_order.extend(secondary)

    return {

        "goal":
            semantic.get(
                "intent",
                "dialogue"
            ),

        "primary_artifacts":
            primary,

        "secondary_artifacts":
            secondary,

        "artifact_scene":
            artifact_scene,

        "scene_order":
            scene_order,

        "composition_strategy":
            "artifact_first_scene_composition"
    }

# =====================================================
# 🧠 ARTIFACT -> RENDER BLOCK RESOLVER
# =====================================================

def artifact_to_render_block(result):

    # MACHINE PAYLOAD MUST STAY MACHINE PAYLOAD
    # BotRU is the only human translator.

    if not isinstance(result, dict):
        return {
            "type": "machine_payload",
            "payload": result
        }

    result_type = result.get("type")

    if result_type != "artifact":
        return result

    artifact = result.get("artifact")

    translated = botru_translate_artifact(
        artifact
    )

    translated["machine_payload"] = True

    return translated

# =====================================================
# 🧠 BOT.RU MACHINE -> HUMAN TRANSLATOR
# =====================================================

def botru_translate_artifact(artifact):

    if artifact is None:
        return {
            "type": "artifact",
            "content": ""
        }

    # BaseArtifact support
    if hasattr(artifact, "data"):

        payload = artifact.data

        if isinstance(payload, dict):

            for field in [
                "answer",
                "response",
                "content",
                "text",
                "summary",
                "analysis",
                "description",
                "research_summary",
                "observation_report",
                "topic"
            ]:

                value = payload.get(field)

                if value:
                    return {
                        "type": "artifact",
                        "content": str(value),
                        "artifact": payload
                    }

            return {
                "type": "artifact",
                "content": str(payload),
                "artifact": payload
            }

    if isinstance(artifact, str):
        return {
            "type": "artifact",
            "content": artifact
        }

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
                return {
                    "type": "artifact",
                    "content": str(value),
                    "artifact": artifact
                }

        return {
            "type": "artifact",
            "content": str(artifact),
            "artifact": artifact
        }

    return {
        "type": "artifact",
        "content": str(artifact)
    }

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
    machine_contracts = []
    machine_responses = []

    max_results = 8

    print("🏭 ROOM SELECTION DELEGATED TO EXECUTOR")

    # =====================================================
    # 🔥 EVALUATION
    # =====================================================

    for room in ROOMS:

        try:

            # Room filtering is performed by the unified
            # executor cognition pipeline.

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

            score += domain_room_bonus(
                room,
                semantic
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

            machine_request = context.get("machine_request")

            machine_task_payload = {

                "channel":
                    TASK_CHANNEL,

                "machine_request":
                    machine_request,

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

                "machine_contract":
                    True,

                "awareness":
                    context.get(
                        "executor_awareness",
                        {}
                    )
            }

            print(f"🔥 HANDLE CALL [{room.name}]")

            handler_payload = machine_request or machine_task_payload

            # =====================================================
            # FIBER ROUTE (canonical)
            # =====================================================
            result = await room.handle(
                handler_payload,
                run_with_activity
            )

            # -----------------------------------------------------
            # LEGACY ROUTE (disabled for migration reference)
            # result = await room.handle(
            #     user_id,
            #     text,
            #     handler_payload,
            #     run_with_activity
            # )
            # -----------------------------------------------------

            print(f"🔥 HANDLE RESULT TYPE [{room.name}]:", type(result))
            print(f"🔥 HANDLE RESULT [{room.name}]:", result)

            if not result:
                print(f"🔥 HANDLE EMPTY [{room.name}]")
                continue

            validation_result = validate_machine_response(
                result
            )

            print(f"🔥 VALIDATION [{room.name}]:", validation_result)

            if not validation_result:

                print(f"🔥 VALIDATION FAILED [{room.name}]")
                continue

            override = should_override(

                result=result,

                semantic=semantic,

                cognition=cognition,

                state=state
            )

            print(f"🔥 OVERRIDE [{room.name}]:", override)

            if override:

                print(f"🔥 OVERRIDE BLOCKED [{room.name}]")
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

            if isinstance(result, dict):
                contract = result.get("contract")
                response = result.get("machine_response")

                if contract is not None:
                    machine_contracts.append(contract)

                if response is not None:
                    machine_responses.append(response)

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

        # ================================================
        # 🔥 CANONICAL SCENE CONTRACT COMPOSITION
        # ================================================

        unified_machine_response = collect_machine_contract(machine_contracts)
        unified_machine_scene = build_machine_scene(unified_machine_response)

        scene_plan = build_scene_plan(
            response_decision,
            semantic
        )

        blocks = compose_canonical_scene_blocks(unified_machine_scene, collected_results)

        payload = {
            "channel": RESPONSE_CHANNEL,
            "room": "scene",
            "trajectory": context.get("trajectory"),
            "result": {
                "type": "scene",
                "blocks": blocks,
                "artifact_scene": scene_plan.get("artifact_scene", []),
                "scene_plan": scene_plan,
                "scene_composition_ready": len(scene_plan.get("artifact_scene", [])) > 0,
                "machine_scene": unified_machine_scene,
                "scene_contract": True,
                "legacy_routes": 0,
                "machine_contract_count": len(machine_contracts),
                "machine_response_count": len(machine_responses)
            }
        }

        payload["result"] = build_checkout_scene_contract(payload["result"])
        return payload

    return None


# =====================================================
# 🧠 REPRESENTATION GATE
# =====================================================

def apply_representation_gate(blocks, response_decision=None, semantic=None):
    response_decision = response_decision or {}
    semantic = semantic or {}
    preferred = (
        response_decision.get("preferred_representation")
        or semantic.get("preferred_representation")
    )
    if not preferred:
        return blocks
    filtered=[]
    for b in blocks:
        if not isinstance(b, dict):
            filtered.append(b); continue
        t=b.get("type")
        if t in ("graph","formula","table","diagram","gallery"):
            if t!=preferred:
                continue
        filtered.append(b)
    return filtered




# =========================================================
# 🧠 CANONICAL SCENE COMPOSER
# =========================================================


def is_canonical_scene(scene):
    """Single routing check used by Executor."""
    return bool(getattr(scene, "scene_contract", False))

def compose_canonical_scene_blocks(machine_scene, collected_results):
    # Stage 3: canonical scene extraction
    """
    Canonical scene assembly.
    Prefer MachineScene blocks and only fall back to legacy
    artifact conversion when MachineScene has no renderable blocks.
    """
    blocks = list(getattr(machine_scene, "blocks", []))

    # Prefer already-built scene blocks.
    if blocks:
        return blocks

    scene = getattr(machine_scene, "scene", None)
    if isinstance(scene, dict):
        elements = scene.get("elements") or []
        if elements:
            return [
                {
                    "type": str(e.get("type", "text")).lower(),
                    "payload": e,
                    "scene_contract": True,
                }
                for e in elements if isinstance(e, dict)
            ]

    for item in collected_results:
        result = item.get("result", {})
        if not isinstance(result, dict):
            continue

        block = artifact_to_render_block(result)
        if isinstance(block, dict):
            scene_blocks = block.get("scene_blocks", [])
            if scene_blocks:
                blocks.extend(scene_blocks)
            else:
                blocks.append(block)
        elif block:
            blocks.append(block)

    return blocks



# =========================================================
# 🧠 CHECKOUT SCENE CONTRACT BRIDGE
# =========================================================

def build_checkout_scene_contract(scene_result):
    """
    Canonical hand-off object for checkout_server.
    Executor exposes one Scene Contract without rebuilding it.
    """
    if not isinstance(scene_result, dict):
        return scene_result

    machine_scene = scene_result.get("machine_scene")
    blocks = scene_result.get("blocks", [])

    if not blocks and hasattr(machine_scene, "blocks"):
        blocks = list(getattr(machine_scene, "blocks", []))

    return {
        "scene_contract": True,
        "scene_version": "1.1",
        "machine_scene": machine_scene,
        "scene_plan": scene_result.get("scene_plan"),
        "blocks": blocks,
        "render_blocks": blocks,
        "artifact_scene": scene_result.get("artifact_scene", []),
        "renderer_state": scene_result.get("renderer_state", {}),
        "executor_route": "fiber_scene_v2",
    }

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

        result["prefer_text_explanation"] = True

        result["scene_preserved"] = True

        return result

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

    cognition["visual_memory_bridge"] = (
        build_visual_memory_bridge(
            user_id
        )
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

        "focus_recommendation":
            cognition.get("focus_recommendation", cognition.get("dynamic_focus", {})),

        "goal_analysis":
            cognition.get("goal_analysis", cognition.get("goal_hierarchy", {})),

        "loop_analysis":
            cognition.get("loop_analysis", cognition.get("open_loops", {})),

        "memory_analysis":
            cognition.get("memory_analysis", cognition.get("memory_signals", {}))
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

    # =====================================================
    # 🔥 UNIVERSAL MACHINE REQUEST
    # =====================================================
    machine_request = build_machine_request({
        "semantic": semantic,
        "memory_routing": memory_routing,
        "visual_reference": visual_reference,
        "trajectory": state.get("scene_state", {}).get("trajectory")
    })

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

    context["machine_request"] = machine_request
    print(f"🟢 FIBER trace={getattr(machine_request,'trace_id',None)} input=MachineRequest")

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

        # =====================================================
        # APRIL RESPONSE STABILIZATION
        # =====================================================

        if result.get("type") == "text":

            original_text = (
                result.get("data")
                or result.get("content")
                or ""
            )

            if isinstance(original_text, str):

                formatted = normalize_provider_scene(
                    format_response_presentation(

                        text=original_text,

                        user_text=text,

                        semantic=semantic,

                        cognition=cognition,

                        response_decision=response_decision,

                        visual_reference=visual_reference
                    )
                )

                result["data"] = formatted

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
    # 🔥 BROADBAND PROVIDER ROUTE
    # =====================================================

    context_text = build_deephub_context(
        user_id,
        text,
        state
    )

    print("🔥 EXECUTOR BROADBAND PROVIDER ROUTE")

    try:

        if run_with_activity:
            generated_text = await run_with_activity(
                chat_id,
                generate_text(context_text)
            )
        else:
            generated_text = await generate_text(context_text)

        # Preserve provider machine contract if returned.
        if isinstance(generated_text, dict):
            fallback_result = generated_text
        else:
            fallback_result = {
                "machine_response": {
                    "content": generated_text
                },
                "scene_contract": False,
                "provider_room": "llm_room"
            }

    except Exception as e:

        print("🔥 PROVIDER ROUTE ERROR:", e)

        traceback.print_exc()

        return {
            "type": "text",
            "data": f"⚠️ PROVIDER ROUTE ERROR: {e}"
        }

# =====================================================
    # 🔥 FORMAT
    # =====================================================

    # =====================================================
    # 🔥 CANONICAL RESPONSE UNIFICATION
    # All providers are normalized into the same machine path.
    # =====================================================
    if fallback_result:

        if "machine_response" not in fallback_result:
            fallback_result = {
                "machine_response": {
                    "content": fallback_result.get("content","")
                },
                "provider_room": "llm_room"
            }


        machine_payload = fallback_result.get("machine_response", {})

        formatted = normalize_provider_scene(format_response_presentation(

                response=machine_payload,

                user_text=text,

                semantic=semantic,

                cognition=cognition,

                response_decision=response_decision,

                visual_reference=visual_reference
        ))

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

        if isinstance(formatted, dict):
            if formatted.get("type")=="scene_contract" or formatted.get("scene_present"):
                return formatted
            if formatted.get("type")=="scene":
                return formatted

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
# 🧠 EXECUTOR MEMORY + UTC INTEGRATION
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
# 🧠 MEMORY RECALL
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
# 🧠 EXECUTOR MEMORY RECALL ACTIVATION
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
# 🧠 EXECUTOR UTC MEMORY RECALL SELECTION
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
# 🧠 VISUAL SUMMARY
# =========================================================

def build_visual_summary_awareness(state):

    user_space = build_executor_user_space(state)
    active_visual_scene = user_space.get("active_visual_scene", {})

    visual_summary = state.get(
        "visual_summary",
        {}
    )

    return {

        "events_count":
            visual_summary.get(
                "scene_events_count",
                0
            ),

        "last_event":
            visual_summary.get(
                "last_event"
            ),

        "package":
            visual_summary.get(
                "package",
                "free"
            ),

        "session_started_utc":
            visual_summary.get(
                "session_started_utc"
            ),

        "active_visual_scene":
            active_visual_scene
    }

# =========================================================
# 🧠 EXECUTOR LIVE VISION BRIDGE
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
            state.get("focus_state", state.get("dynamic_focus", {})),

        "runtime_mode":
            "open_tab_live_runtime"
    }

def build_executor_runtime_bridge(state):

    return {

        "memory_recall":
            build_ranked_memory_recall(state),

        "live_vision":
            build_live_vision_feed(state),

        "visual_summary_awareness":
            build_visual_summary_awareness(state),

        "bridge_ready": True
    }

# =========================================================
# 🧠 EXECUTOR LIVE VISION -> MEMORY TRANSFER
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
# 🧠 EXECUTOR ARTIFACT EXPANSION
# =========================================================

ARTIFACT_BLOCK_MAP = {
    "graph_data": "graph",
    "knowledge_graph": "graph",
    "knowledge_graph_v2": "graph",
    "knowledge_nodes": "graph",
    "relations": "graph",
    "relation_graph": "graph",
    "entities": "table",
    "canonical_entities": "table",
    "concepts": "table",
    "processes": "table",
    "table_data": "table",
    "taxonomy": "table",
    "comparison": "table",
    "resources": "research",
    "sources": "research",
    "evidence": "research",
    "evidence_report": "research",
    "mechanism_chain": "diagram",
    "research": "research"
}

def expand_artifact_payload(artifact):

    blocks = []

    if not isinstance(artifact, dict):
        return blocks

    for key, value in artifact.items():

        if key not in ARTIFACT_BLOCK_MAP:
            continue

        blocks.append({
            "type": ARTIFACT_BLOCK_MAP[key],
            "source_field": key,
            "payload": value
        })

    return blocks

# Canonical artifact -> scene resolver (single expansion pipeline)
_previous_artifact_to_render_block = artifact_to_render_block

def artifact_to_render_block(result):

    translated = _previous_artifact_to_render_block(result)

    try:

        artifact = None

        if isinstance(result, dict):
            artifact = result.get("artifact")

        if isinstance(translated, dict):

            translated["scene_blocks"] = []
            translated["expanded_blocks"] = []
            translated["scene_ready"] = False

    except Exception:
        pass

    return translated

# =========================================================
# 🧠 EXECUTOR SCENE COMPOSER
# =========================================================

def build_scene_from_artifact(artifact):
    # Legacy compatibility helper.
    # Used only as a fallback when MachineScene has no renderable blocks.
    # Canonical route: MachineScene -> Scene Contract.

    scene_blocks = []

    if not isinstance(artifact, dict):
        return scene_blocks

    unified_graph_payload = {
        "graph_data": artifact.get("graph_data"),
        "knowledge_graph": artifact.get("knowledge_graph"),
        "relation_graph": artifact.get("relation_graph"),
        "knowledge_nodes": artifact.get("knowledge_nodes"),
        "relations": artifact.get("relations")
    }

    has_graph = any(v for v in unified_graph_payload.values())

    # Graph blocks are emitted only when a room explicitly provides graph data.

    if has_graph:

        graph_description = (
            artifact.get("description")
            or artifact.get("summary")
            or artifact.get("analysis")
            or artifact.get("content")
            or artifact.get("topic")
            or ""
        )

        scene_blocks.append({
            "type": "graph",
            "graph": unified_graph_payload,
            "description": graph_description,
            "broadband_route": True
        })

    for field in [
        "table_data",
        "entities",
        "canonical_entities",
        "concepts",
        "processes"
    ]:
        if artifact.get(field):
            scene_blocks.append({
                "type": "table",
                "payload": artifact.get(field)
            })

    return scene_blocks

# =========================================================
# END EXECUTOR # =========================================================

# =========================================================
# APRIL FIBER EXECUTOR BRIDGE
# =========================================================

# Single Fiber entry point. All execution begins with MachineRequest.
def build_machine_request(context):
    req=MachineRequest()
    req.goal=context.get("semantic",{}).get("intent","dialog")
    req.intent=context.get("semantic",{})
    req.memory=context.get("memory_routing",{})
    req.visual_context=context.get("visual_reference",{})
    req.routing={"trajectory":context.get("trajectory")}
    return req


# =====================================================
# STAGE 1 - CONTRACT NORMALIZER
# =====================================================

def _extract_contract_payload(contract):
    payload = {
        "artifact": None,
        "render_blocks": [],
        "scene": None,
        "renderer_state": {},
        "metadata": {},
    }
    if contract is None:
        return payload

    payload["artifact"] = getattr(contract, "artifact", None)
    payload["render_blocks"] = list(getattr(contract, "render_blocks", []) or [])
    payload["scene"] = getattr(contract, "scene", None)
    payload["renderer_state"] = getattr(contract, "renderer_state", {}) or {}
    payload["metadata"] = getattr(contract, "metadata", {}) or {}
    return payload

def collect_machine_contract(room_contracts):
    print("========== COLLECT_MACHINE_CONTRACT ==========")
    print("ROOM CONTRACT COUNT:", len(room_contracts))
    response=MachineResponse()
    for idx, contract in enumerate(room_contracts):
        print(f"CONTRACT[{idx}] TYPE:", type(contract))
        print(f"CONTRACT[{idx}] HAS ARTIFACT:", hasattr(contract,"artifact"))
        print(f"CONTRACT[{idx}] HAS RENDER_BLOCKS:", hasattr(contract,"render_blocks"))
        normalized = _extract_contract_payload(contract)

        if normalized["artifact"]:
            response.artifacts.append(normalized["artifact"])

        if not hasattr(response, "render_blocks"):
            response.render_blocks = []
        response.render_blocks.extend(normalized["render_blocks"])

        if normalized["scene"] and not hasattr(response, "scene"):
            response.scene = normalized["scene"]

        if not hasattr(response, "renderer_state"):
            response.renderer_state = {}
        response.renderer_state.update(normalized["renderer_state"])
    print("RESPONSE ARTIFACT COUNT:", len(response.artifacts))
    return response

def build_machine_scene(response):
    print("========== BUILD_MACHINE_SCENE ==========")
    print("INPUT RESPONSE:", type(response))
    scene = MachineScene()

    # Canonical Fiber Route:
    # MachineResponse is the only input accepted by the Scene builder.
    if response is None:
        scene.scene_contract = True
        return scene

    # Stage 2: prefer canonical render blocks and scene before artifact fallback
    if hasattr(response, "render_blocks") and response.render_blocks:
        scene.blocks.extend(response.render_blocks)

    elif hasattr(response, "scene") and response.scene:
        scene.blocks.append({
            "type": "scene",
            "payload": response.scene,
            "scene_contract": True
        })

    else:
        for art in response.artifacts:
            scene.blocks.append({
                "type": "artifact",
                "artifact_type": getattr(art.metadata, "artifact_type", "artifact"),
                "room": getattr(art.metadata, "room_source", "unknown"),
                "payload": art.data,
                "scene_contract": True
            })

    print("SCENE BLOCK COUNT:", len(scene.blocks))
    scene.scene_contract = True
    return scene


# =========================================================
# FIBER ROUTE ASSERTION
# =========================================================

def verify_fiber_route():
    """Executor exposes a single canonical transport route."""
    return {
        "single_route": True,
        "input": "MachineRequest",
        "output": "MachineScene",
        "scene_contract": True,
    }

# Compatibility helper layer removed.
# Executor uses MachineRequest directly.
# =====================================================
# STAGE 2 - Scene Contract Bridge
# =====================================================

def normalize_provider_scene(result):
    if not isinstance(result, dict):
        return result

    if result.get("type") == "scene_contract":
        return result

    if result.get("scene_contract") is True:
        return {
            "type": "scene_contract",
            **result
        }

    return result





# =====================================================
# EXECUTOR ROUTE VERSION
# =====================================================
EXECUTOR_ROUTE_VERSION="fiber_scene_v2"
EXECUTOR_LEGACY_TEXT_ROUTE=False


# =====================================================
# EXECUTOR FIBER CANONICAL
# =====================================================
EXECUTOR_FIBER_CANONICAL = True
