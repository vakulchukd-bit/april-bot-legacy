
# ==========================================================
# XSCRUTER EXPERIMENTAL BUILD X-001
#
# Purpose:
# - Experimental CPU consolidation build.
# - Test version for route diagnostics.
# - Safe rollback expected if hypothesis is rejected.
#
# Hypothesis:
# Executor should become the single coordination CPU while
# preserving one Fiber route and one Artifact Contract.
#
# ==========================================================

# APRIL EXECUTOR CPU CONTRACT
#   -> reflection

# APRIL EXECUTOR
# Canonical execution path:
# User Space -> MachineRequest -> Rooms -> MachineResponse -> MachineScene -> Scene Contract

import traceback
import time

from datetime import datetime


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

# ==========================================================
# XSCRUTER MEMORY SUPERVISION
# CPU coordinates memory subsystems.
# Memory modules execute independently.
# ==========================================================

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


from blocks.rooms_registry import (
    ROOMS
)

from blocks.C_ARTIFACT_CONTRACT import (
    MachineRequest,
    MachineResponse,
    MachineScene,
    UniversalArtifactContract,
)



from blocks.provider_router import generate_text

# 🧠 PRESENTATION

from blocks.presentation_formatter import (
    format_response_presentation
)


from blocks.energy_manager import (
    get_energy
)

from blocks.experience import (
    update_experience,
    load_experience
)


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


EMAPS = {

    "active_rooms": set(),

    "active_trajectories": set(),

    "active_modalities": set(),

    "execution_sessions": [],

    "machine_routes": []
}


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


def validate_machine_response(
    result
):

    if not result:
        return False

    from blocks.C_ARTIFACT_CONTRACT import MachineResponse

    if isinstance(result, MachineResponse):
        return True

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

# ==========================================================
# XSCRUTER EXECUTION CONTEXT
# Unified runtime context prepared by CPU.
# ==========================================================

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


        "machine_channel":
            TASK_CHANNEL,

        "task_type":
            task_type,

        "executor_version":
            "unified_broadband_route_v1",


        "user_id":
            user_id,

        "chat_id":
            chat_id,


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


        "machine_input":
            text,


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


    if active_room:

        if room.name == active_room:

            score += 4.0


    if response_decision.get(
        "renderer_first_mode"
    ):

        if room.name in [

            "science",
            "renderer",
            "graph"
        ]:

            score += 5.0


    if response_decision.get(
        "avoid_heavy_generation"
    ):

        if room.name in [

            "image_generate",
            "image_edit"
        ]:

            score -= 8.0



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


def get_factory_required_rooms(semantic):

    factory_order = semantic.get(
        "factory_order",
        {}
    )

    return factory_order.get(
        "required_rooms",
        []
    )


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


def artifact_to_render_block(result):


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


def botru_translate_artifact(artifact):

    if artifact is None:
        return {
            "type": "artifact",
            "content": ""
        }

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

# ==========================================================
# ROOM EXECUTION PHASE
# Rooms execute tasks.
# CPU supervises and validates results.
# ==========================================================

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
    executor_room_report = []
    machine_contracts = []
    machine_responses = []

    max_results = 8

    print("🏭 ROOM SELECTION DELEGATED TO EXECUTOR")


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


    scored_rooms.sort(

        key=lambda x: x[0],

        reverse=True
    )


    for score, room in scored_rooms:

        try:

            track_room(
                room.name
            )
            executor_room_report = executor_cpu_register_room(
                executor_room_report,
                room.name,
                score=score,
                executed=True,
                accepted=False,
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

            # Rooms receive only the canonical MachineRequest.
            handler_payload = machine_request

            # FIBER ROUTE (canonical)
            result = await room.handle(
                user_id=user_id,
                text=text,
                context=handler_payload,
                run=run_with_activity
            )

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
                # X4.2 TEST: preserve canonical MachineResponse if already produced.
                if isinstance(result, dict) and result.get("machine_response") is not None:
                    print(f"🟢 X4.2 OVERRIDE BYPASSED [{room.name}]")
                elif hasattr(result, "answer") or hasattr(result, "artifacts"):
                    print(f"🟢 X4.2 OVERRIDE BYPASSED [{room.name}]")
                else:
                    print(f"🔥 OVERRIDE BLOCKED [{room.name}]")
                    continue


            if hasattr(result, "artifacts") and not isinstance(result, dict):
                collected_results.append({
                    "channel": RESPONSE_CHANNEL,
                    "room": room.name,
                    "trajectory": context.get("trajectory"),
                    "result": result,
                })
                machine_responses.append(result)
                continue

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
            executor_room_report[-1]["accepted"] = True

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

        # 🔥 CANONICAL SCENE CONTRACT COMPOSITION

        unified_machine_response = collect_machine_contract(machine_contracts)
        unified_machine_response = merge_machine_responses(unified_machine_response, machine_responses)

        # X012 STAGE4: Canonical response must never be discarded.
        if machine_responses:
            for _mr in machine_responses:
                if getattr(_mr, "answer", None):
                    unified_machine_response.answer = getattr(_mr, "answer", None)
                    unified_machine_response.content = (
                        getattr(_mr, "content", None) or unified_machine_response.answer
                    )
                    unified_machine_response.summary = (
                        getattr(_mr, "summary", None) or unified_machine_response.content
                    )
                    break
        if not getattr(unified_machine_response,'answer',None):
            for r in machine_responses:
                a=getattr(r,'answer',None)
                if a:
                    unified_machine_response.answer=a
                    unified_machine_response.content=getattr(r,'content',a)
                    unified_machine_response.summary=getattr(r,'summary',a)
                    print('🟢 X4.2 ANSWER RESTORED')
                    break
        reflection_context = {
            "semantic": semantic,
            "cognition": cognition,
            "response_decision": response_decision,
            "state": state,
        }

        executor_cpu_mark_object('machine_response', unified_machine_response, 'provider->executor')
        executor_cpu_verify_identity('machine_response', unified_machine_response)
        executor_cpu_capture_payload('machine_response', unified_machine_response)
        executor_cpu_after_response(unified_machine_response)
        executor_cpu_sync("machine_response", unified_machine_response)

        unified_machine_response = executor_cpu_reflect(
            semantic=semantic,
            cognition=cognition,
            response_decision=response_decision,
            state=state,
            machine_response=unified_machine_response,
        )

        unified_machine_response = executor_reflection_pass(
            unified_machine_response,
            reflection_context
        )

        # X007 TEST: canonical response guard
        if getattr(unified_machine_response, "answer", None) and not getattr(unified_machine_response, "content", None):
            unified_machine_response.content = unified_machine_response.answer
        if getattr(unified_machine_response, "content", None) and not getattr(unified_machine_response, "summary", None):
            unified_machine_response.summary = unified_machine_response.content
        print("🟢 X007 CPU CANONICAL",
              bool(getattr(unified_machine_response,"answer",None)),
              bool(getattr(unified_machine_response,"content",None)),
              bool(getattr(unified_machine_response,"summary",None)))
        unified_machine_scene = build_machine_scene(unified_machine_response)
        unified_machine_scene = executor_cpu_sync_scene(
            unified_machine_response,
            unified_machine_scene
        )
        unified_machine_scene = executor_cpu_finalize_scene(
            unified_machine_response,
            unified_machine_scene
        )
        unified_machine_scene = executor_cpu_validate_completeness(
            unified_machine_response,
            unified_machine_scene
        )
        executor_cpu_mark_object('machine_scene', unified_machine_scene, 'executor')
        executor_cpu_verify_identity('machine_scene', unified_machine_scene)
        executor_cpu_capture_payload('machine_scene', unified_machine_scene)
        executor_cpu_after_scene(unified_machine_scene)
        executor_cpu_sync("machine_scene", unified_machine_scene)

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
                "machine_response_count": len(machine_responses),

                # CANONICAL TEXT TRANSPORT
                "content": getattr(unified_machine_response, "content", None),
                "summary": getattr(unified_machine_response, "summary", None),
                "answer": getattr(unified_machine_response, "answer", None)
            }
        }

        unified_machine_scene = executor_cpu_attach_room_report(
            unified_machine_scene,
            executor_room_report
        )
        executor_cpu_contract_probe(
            "PRE_CHECKOUT",
            machine_response=unified_machine_response,
            machine_scene=unified_machine_scene,
            scene_contract=payload["result"],
        )
        
        # X008 TEST: verify canonical transport immediately before checkout
        if getattr(unified_machine_response, "answer", None):
            payload["result"]["answer"] = getattr(unified_machine_response, "answer", None)
        if getattr(unified_machine_response, "content", None):
            payload["result"]["content"] = getattr(unified_machine_response, "content", None)
        if getattr(unified_machine_response, "summary", None):
            payload["result"]["summary"] = getattr(unified_machine_response, "summary", None)
        print("🟢 X008 PRE-CHECKOUT CANONICAL",
              payload["result"].get("answer"),
              payload["result"].get("content"))

        if unified_machine_response.answer:
            payload["result"]["answer"] = unified_machine_response.answer
            payload["result"]["content"] = unified_machine_response.content
            payload["result"]["summary"] = unified_machine_response.summary
        # X017 TEST: switch to canonical single-space route
        payload["result"] = executor_cpu_finalize_transport(unified_machine_response)

        executor_cpu_contract_probe(
            "POST_CHECKOUT",
            machine_response=unified_machine_response,
            machine_scene=unified_machine_scene,
            scene_contract=payload["result"],
        )
        return payload

    return None


# 🧠 REPRESENTATION GATE

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




# ==========================================================
# CANONICAL SCENE COMPOSER
# Scene assembly owned by Executor CPU.
# ==========================================================


def is_canonical_scene(scene):
    """Single routing check used by Executor."""
    return bool(getattr(scene, "scene_contract", False))

def compose_canonical_scene_blocks(machine_scene, collected_results):
    """
    Canonical scene assembly.
    Prefer MachineScene blocks and only fall back to legacy
    artifact conversion when MachineScene has no renderable blocks.
    """
    blocks = list(getattr(machine_scene, "render_blocks", None) or getattr(machine_scene, "blocks", []))

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



# ==========================================================
# CPU → CHECKOUT HANDOFF
# Approved SceneContract leaves CPU here.
# ==========================================================


# ===== XSCRUTER X003 TEST DIAGNOSTICS =====
def executor_cpu_contract_probe(stage, machine_response=None, machine_scene=None, scene_contract=None):
    print(f"🟢 X003 [{stage}]")
    if machine_response is not None:
        print("  answer:", getattr(machine_response, "answer", None))
        print("  content:", getattr(machine_response, "content", None))
        print("  blocks:", len(getattr(machine_response, "render_blocks", []) or []))
    if machine_scene is not None:
        print("  scene_blocks:", len(getattr(machine_scene, "blocks", []) or []))
    if isinstance(scene_contract, dict):
        print("  contract_answer:", scene_contract.get("answer"))
        if getattr(machine_response, "answer", None) and not scene_contract.get("answer"):
            print("🟢 CPU CONTRACT LOSS DETECTED")
# ===== END X003 TEST DIAGNOSTICS =====

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
        blocks = list(getattr(machine_scene, "render_blocks", None) or getattr(machine_scene, "blocks", []))

    return {
        "scene_contract": {
            "render_blocks": blocks,
            "scene_plan": scene_result.get("scene_plan"),
            "renderer_state": scene_result.get("renderer_state", {}),
            "machine_scene": machine_scene,
            "scene_version": "1.2",
        },
        "scene_version": "1.2",
        "machine_scene": machine_scene,
        "scene_plan": scene_result.get("scene_plan"),
        "blocks": blocks,
        "render_blocks": blocks,
        "content": scene_result.get("content"),
        "summary": scene_result.get("summary"),
        "answer": scene_result.get("answer"),
        "artifact_scene": scene_result.get("artifact_scene", []),
        "renderer_state": scene_result.get("renderer_state", {}),
        "executor_route": "fiber_scene_v2",
        "scene_contract_owner": "executor",
        "scene_contract_final": True,
    }


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

# ==========================================================
# XSCRUTER MAIN EXECUTION LOOP
# Single lifecycle coordinator.
# ==========================================================

# XSCRUTER HYPOTHESIS:
# 1. Every request enters here.
# 2. CPU supervises every stage.
# 3. Every subsystem reports back here.
# 4. One canonical SceneContract exits here.
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

    executor_cpu_begin(text)
    executor_cpu_update("aprilweb_input", text)

    state = get_state(
        user_id
    )

    mode = get_mode(
        user_id
    )


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

    executor_cpu_after_semantic(semantic)
    executor_cpu_sync("semantic", semantic)

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


    cognition = apply_april_personality(

        cognition=cognition,

        semantic=semantic,

        reasoning=reasoning,

        response_decision={},

        state=state
    )


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

    # 🔥 GOLDEN MEMORY ROUTING LAYER

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

    # 🔥 MEMORY

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


    task_type = detect_task_type(

        semantic,

        cognition,

        state
    )

    # ==========================================================
# XSCRUTER EXECUTION CONTEXT
# Unified runtime context prepared by CPU.
# ==========================================================

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


    task_resolution = build_task_resolution(

        cognition=cognition,

        response_decision=response_decision,

        semantic=semantic,

        state=state
    )

    guidance_response = build_guidance_response(
        task_resolution
    )

    state["task_resolution"] = task_resolution

    if guidance_response:
        state["guidance_response"] = guidance_response

    # ==========================================================
# ROOM EXECUTION PHASE
# Rooms execute tasks.
# CPU supervises and validates results.
# ==========================================================

    print("🔥 EXECUTOR CONTEXT READY")
    print("🔥 CONTEXT CHAT:", chat_id)
    print("🔥 CONTEXT USER:", user_id)
    print("🔥 TASK TYPE:", task_type)
    print("🔥 RUN:", run_with_activity)
    print("🔥 RUN TYPE:", type(run_with_activity))

    executor_cpu_mark_object('machine_request', machine_request, 'executor')
    executor_cpu_verify_identity('machine_request', machine_request)
    executor_cpu_after_request(machine_request)
    executor_cpu_sync("machine_request", machine_request)

    context["machine_request"] = machine_request
    print(f"🟢 FIBER trace={getattr(machine_request,'trace_id',None)} input=MachineRequest")
    print("🟢 FIBER_CANONICAL_ONLY: legacy room payload disabled")

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


    if isinstance(room_response, dict) and room_response.get("executor_cpu_redirect"):
        executor_cpu_checkpoint(
            "CPU_REDIRECT_ACCEPTED",
            phase=room_response.get("next_stage"),
            route=room_response.get("route_target"),
        )

        machine_response = room_response.get("machine_response")

        if machine_response is not None:
            try:
                setattr(machine_response, "execution_phase", "POST_PROVIDER")
                setattr(machine_response, "fiber_pass", 2)
            except Exception:
                if isinstance(machine_response, dict):
                    machine_response["execution_phase"] = "POST_PROVIDER"
                    machine_response["fiber_pass"] = 2
            machine_response = executor_cpu_reflect(
                semantic=semantic,
                cognition=cognition,
                response_decision=response_decision,
                state=state,
                machine_response=machine_response,
            )
            machine_response = executor_reflection_pass(
                machine_response,
                {
                    "semantic": semantic,
                    "cognition": cognition,
                    "response_decision": response_decision,
                    "state": state,
                },
            )

            machine_scene = build_machine_scene(machine_response)
            machine_scene = executor_cpu_sync_scene(machine_response, machine_scene)
            machine_scene = executor_cpu_finalize_scene(machine_response, machine_scene)
            machine_scene = executor_cpu_validate_completeness(machine_response, machine_scene)

            return executor_cpu_finalize_transport(machine_response)

            # LEGACY (kept below for rollback reference)
            # return build_checkout_scene_contract({
                "machine_scene": machine_scene,
                "scene_plan": {},
                "blocks": list(getattr(machine_scene, "render_blocks", []) or getattr(machine_scene, "blocks", [])),
                "render_blocks": list(getattr(machine_scene, "render_blocks", []) or getattr(machine_scene, "blocks", [])),
                "content": getattr(machine_response, "content", None),
                "summary": getattr(machine_response, "summary", None),
                "answer": getattr(machine_response, "answer", None),
                "renderer_state": getattr(machine_response, "renderer_state", {}),
            })

        return {
            "type":"text",
            "data":"CPU redirect received without MachineResponse."
        }


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
        

    # Executor must complete the canonical Fiber route only.
    # CANONICAL CPU TERMINATION
    # Never leave Executor without a Scene Contract.
    # Canonical safeguard: do not replace a valid MachineResponse.
    if EXECUTOR_CPU_ROUTE.get("machine_response") is not None:
        mr = EXECUTOR_CPU_ROUTE["machine_response"]
        ms = build_machine_scene(mr)
        return build_checkout_scene_contract({
            "machine_scene": ms,
            "scene_plan": {},
            "blocks": list(getattr(ms,"render_blocks",[]) or getattr(ms,"blocks",[])),
            "content": getattr(mr,"content",None),
            "summary": getattr(mr,"summary",None),
            "answer": getattr(mr,"answer",None),
            "renderer_state": getattr(mr,"renderer_state",{}),
        })

    # X4.1 TEST: do not fabricate a canonical answer.
    executor_cpu_checkpoint(
        "CPU_ROUTE_INCOMPLETE",
        status="FAIL",
        reason="MachineResponse missing after canonical route",
    )
    raise RuntimeError(
        "Canonical MachineResponse missing after Executor route. "
        "Fallback response generation is disabled in X4.1 TEST."
    )

    fallback_response = MachineResponse()

    fallback_response = executor_cpu_reflect(
        semantic=semantic,
        cognition=cognition,
        response_decision=response_decision,
        state=state,
        machine_response=fallback_response,
    )

    fallback_response = executor_reflection_pass(
        fallback_response,
        {
            "semantic": semantic,
            "cognition": cognition,
            "response_decision": response_decision,
            "state": state,
        },
    )

    fallback_scene = build_machine_scene(fallback_response)
    fallback_scene = executor_cpu_sync_scene(fallback_response, fallback_scene)
    fallback_scene = executor_cpu_finalize_scene(fallback_response, fallback_scene)
    fallback_scene = executor_cpu_validate_completeness(fallback_response, fallback_scene)

    return build_checkout_scene_contract({
        "machine_scene": fallback_scene,
        "scene_plan": {},
        "blocks": list(getattr(fallback_scene,"render_blocks",[]) or getattr(fallback_scene,"blocks",[])),
        "content": fallback_response.content,
        "summary": getattr(fallback_response,"summary",None),
        "answer": fallback_response.answer,
        "renderer_state": {},
    })


    return {

        "type": "text",

        "data":
            "⚠️ April temporarily could not stabilize this trajectory."
    }


# 🧠 EXECUTOR MEMORY + UTC INTEGRATION

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

# ==========================================================
# MEMORY RECALL SUPERVISION
# CPU coordinates recall strategy.
# ==========================================================

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

# 🧠 EXECUTOR MEMORY RECALL ACTIVATION

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

# 🧠 EXECUTOR UTC MEMORY RECALL SELECTION

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

# 🧠 EXECUTOR LIVE VISION -> MEMORY TRANSFER

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


def build_scene_from_artifact(artifact):

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

# ==========================================================
# END OF XSCRUTER CORE
# Remaining helpers support the canonical CPU lifecycle.
# ==========================================================


def build_machine_request(context):
    req=MachineRequest()
    req.goal=context.get("semantic",{}).get("intent","dialog")
    req.intent=context.get("semantic",{})
    req.memory=context.get("memory_routing",{})
    req.visual_context=context.get("visual_reference",{})
    req.routing={"trajectory":context.get("trajectory")}
    return req



def _extract_contract_payload(contract):
    payload = {
        "artifact": None,
        "render_blocks": [],
        "scene": None,
        "renderer_state": {},
        "metadata": {},
        "content": None,
        "summary": None,
        "answer": None,
        "contributions": {},
    }
    if contract is None:
        return payload

    payload["artifact"] = getattr(contract, "artifact", None)
    payload["render_blocks"] = list(getattr(contract, "render_blocks", []) or [])
    payload["scene"] = getattr(contract, "scene", None)
    payload["renderer_state"] = getattr(contract, "renderer_state", {}) or {}
    payload["metadata"] = getattr(contract, "metadata", {}) or {}
    payload["content"] = getattr(contract, "content", None)
    payload["summary"] = getattr(contract, "summary", None)
    payload["answer"] = getattr(contract, "answer", None)
    payload["contributions"] = getattr(contract, "contributions", {}) or {}
    return payload

def collect_machine_contract(room_contracts):
    print("========== COLLECT_MACHINE_CONTRACT ==========")
    print("ROOM CONTRACT COUNT:", len(room_contracts))
    response=MachineResponse()
    response.content = None
    response.summary = None
    response.answer = None
    response.contributions = {}
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

        if normalized["content"] and not response.content:
            response.content = normalized["content"]
        if normalized["summary"] and not response.summary:
            response.summary = normalized["summary"]
        if normalized["answer"] and not response.answer:
            response.answer = normalized["answer"]
        response.contributions.update(normalized["contributions"])
    print("RESPONSE ARTIFACT COUNT:", len(response.artifacts))
    return response


def merge_machine_responses(unified_machine_response, machine_responses):
    for resp in machine_responses:
        if resp is None:
            continue
        if getattr(resp,"answer",None) and not getattr(unified_machine_response,"answer",None):
            unified_machine_response.answer=resp.answer
        if getattr(resp,"content",None) and not getattr(unified_machine_response,"content",None):
            unified_machine_response.content=resp.content
        if getattr(resp,"summary",None) and not getattr(unified_machine_response,"summary",None):
            unified_machine_response.summary=resp.summary
        if hasattr(resp,"artifacts"):
            unified_machine_response.artifacts.extend(list(getattr(resp,"artifacts",[]) or []))
        rb=list(getattr(resp,"render_blocks",[]) or [])
        if not hasattr(unified_machine_response,"render_blocks"):
            unified_machine_response.render_blocks=[]
        unified_machine_response.render_blocks.extend(rb)
        rs=getattr(resp,"renderer_state",{}) or {}
        if not hasattr(unified_machine_response,"renderer_state"):
            unified_machine_response.renderer_state={}
        unified_machine_response.renderer_state.update(rs)
    return unified_machine_response

def build_machine_scene(response):
    print("========== BUILD_MACHINE_SCENE ==========")
    print("INPUT RESPONSE:", type(response))
    scene = MachineScene()

    # Canonical Fiber Route:
    if response is None:
        scene.scene_contract = True
        return scene
    if hasattr(response, "render_blocks") and response.render_blocks:
        canonical_blocks=list(response.render_blocks)
        scene.blocks=canonical_blocks
        scene.render_blocks=canonical_blocks

    elif hasattr(response, "scene") and response.scene:
        scene.blocks.append({
            "type": "scene",
            "payload": response.scene,
            "scene_contract": True
        })

    else:
        text_payload = (
            getattr(response, "answer", None)
            or getattr(response, "content", None)
            or getattr(response, "summary", None)
        )

        if text_payload:
            scene.blocks.append({
                "type": "text",
                "content": text_payload,
                "scene_contract": True,
                "canonical_route": True,
            })

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



def verify_fiber_route():
    """Executor exposes a single canonical transport route."""
    return {
        "single_route": True,
        "input": "MachineRequest",
        "output": "MachineScene",
        "scene_contract": True,
    }

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










def executor_cpu_materialize_blocks(machine_response):
    """
    Convert CPU presentation decisions into canonical render_blocks.
    Never calls Provider/OpenAI.
    """
    plan = getattr(machine_response, "executor_presentation_plan", {}) or {}
    render_blocks = list(getattr(machine_response, "render_blocks", []) or [])

    if render_blocks:
        return machine_response

    answer = (
        getattr(machine_response, "answer", None)
        or getattr(machine_response, "content", None)
        or getattr(machine_response, "summary", None)
        or ""
    )

    for block in plan.get("blocks", []):
        if block == "table":
            render_blocks.append({
                "type": "table",
                "payload": {"source": "executor_cpu"},
                "scene_contract": True,
            })
        elif block == "graph":
            render_blocks.append({
                "type": "graph",
                "payload": {"source": "executor_cpu"},
                "scene_contract": True,
            })
        elif block == "formula":
            render_blocks.append({
                "type": "formula",
                "content": answer,
                "scene_contract": True,
            })

    if not render_blocks and answer:
        render_blocks.append({
            "type": "text",
            "content": answer,
            "scene_contract": True,
        })

    machine_response.render_blocks = render_blocks
    return machine_response



def executor_cpu_attach_artifact_payloads(machine_response):
    """
    Fill render_block payloads from artifact.data so AprilWeb receives
    real structured content instead of placeholder payloads.
    """
    artifacts = list(getattr(machine_response, "artifacts", []) or [])
    render_blocks = list(getattr(machine_response, "render_blocks", []) or [])

    artifact_data = {}
    for art in artifacts:
        data = getattr(art, "data", None)
        if isinstance(data, dict):
            artifact_data.update(data)

    for block in render_blocks:
        if not isinstance(block, dict):
            continue
        payload = block.setdefault("payload", {})
        btype = block.get("type")

        if btype == "table":
            payload["table_data"] = (
                artifact_data.get("table_data")
                or artifact_data.get("multiplication_table")
            )
        elif btype == "graph":
            payload["graph_data"] = artifact_data.get("graph_data")
        elif btype == "formula":
            payload["formula"] = artifact_data.get("formula")
        elif btype == "text":
            payload["structured"] = artifact_data

    machine_response.render_blocks = render_blocks
    return machine_response

def executor_reflection_pass(machine_response, executor_context):
    """
    Executor Pass #2.
    Local cognition only.
    Never calls Provider/OpenAI.
    Builds a presentation decision before MachineScene.
    """
    if machine_response is None:
        return machine_response

    semantic=executor_context.get("semantic",{}) or {}
    cognition=executor_context.get("cognition",{}) or {}
    response_decision=executor_context.get("response_decision",{}) or {}
    state=executor_context.get("state",{}) or {}

    blocks=list(getattr(machine_response,"render_blocks",[]) or [])

    answer=(getattr(machine_response,"answer",None)
        or getattr(machine_response,"content",None)
        or getattr(machine_response,"summary",None)
        or "")

    planner=getattr(machine_response,"executor_planner",None)
    if planner is None:
        planner={
            "goal":semantic.get("intent"),
            "representation":response_decision.get("preferred_representation")
                or semantic.get("preferred_representation")
                or "text",
            "memory_active":bool(state.get("memory_timeline")),
            "visual_active":bool(state.get("active_visual_scene")),
        }
    planner["reflection"]=True

    if not blocks:
        rep=planner["representation"]
        if rep not in ("text","table","graph","gallery","formula","diagram","link"):
            rep="text"
        blocks.append({
            "type":rep,
            "content":answer,
            "executor_generated":True,
            "executor_pass":2,
            "planner":planner
        })

    machine_response.render_blocks=blocks
    machine_response.executor_cpu_verified=True
    machine_response.executor_reflection={
        "pass":2,
        "planner":planner,
        "provider_reentry":False,
        "openai_reentry":False,
        "decision_complete":True
    }
    return machine_response

# EXECUTOR ROUTE VERSION
EXECUTOR_ROUTE_VERSION="fiber_scene_v2"
EXECUTOR_LEGACY_TEXT_ROUTE=False


# EXECUTOR FIBER CANONICAL
EXECUTOR_FIBER_CANONICAL = True


EXECUTOR_CPU_ENABLED = True


EXECUTOR_CPU_TRACE = []

def executor_cpu_checkpoint(stage, **payload):
    """Central CPU supervision. Never changes routing."""
    reg = executor_cpu_expected(stage)
    entry = {
        "stage": stage,
        "role": reg.get("role"),
        "expected_input": reg.get("input"),
        "expected_output": reg.get("output"),
        "next_stage": reg.get("next"),
        "status": payload.pop("status","OK"),
        "payload": payload,
        "timestamp": time.time(),
    }
    EXECUTOR_CPU_TRACE.append(entry)
    return entry

def build_executor_quality_state(
    *,
    aprilweb_input=None,
    semantic=None,
    machine_request=None,
    machine_response=None,
    machine_scene=None,
    aprilweb_output=None,
):
    return {
        "input_seen": aprilweb_input is not None,
        "semantic_seen": semantic is not None,
        "request_seen": machine_request is not None,
        "response_seen": machine_response is not None,
        "scene_seen": machine_scene is not None,
        "output_seen": aprilweb_output is not None,
        "quality_route_complete": all([
            aprilweb_input is not None,
            machine_request is not None,
            machine_response is not None,
            machine_scene is not None,
        ]),
    }



def build_executor_cpu_snapshot(
    *,
    user_input=None,
    machine_request=None,
    machine_response=None,
    machine_scene=None,
    semantic=None,
    cognition=None,
    response_decision=None,
):
    """
    Single executor awareness object.
    This is diagnostic state only.
    No Provider/OpenAI calls are allowed here.
    """
    return {
        "cpu": True,
        "input_received": user_input is not None,
        "machine_request_ready": machine_request is not None,
        "machine_response_ready": machine_response is not None,
        "scene_ready": machine_scene is not None,
        "semantic_ready": semantic is not None,
        "cognition_ready": cognition is not None,
        "decision_ready": response_decision is not None,
    }




def executor_cpu_begin(user_input):

    executor_cpu_enter_stage('executor_cpu_begin')
    executor_cpu_leave_stage('executor_cpu_begin')
    return executor_cpu_checkpoint(
        "APRILWEB_INPUT",
        text=user_input,
    )

def executor_cpu_after_semantic(semantic):

    executor_cpu_enter_stage('executor_cpu_after_semantic')
    executor_cpu_leave_stage('executor_cpu_after_semantic')
    return executor_cpu_checkpoint(
        "SEMANTIC_READY",
        intent=semantic.get("intent"),
        render_intent=semantic.get("render_intent"),
    )

def executor_cpu_after_request(machine_request):

    executor_cpu_enter_stage('executor_cpu_after_request')
    executor_cpu_leave_stage('executor_cpu_after_request')
    return executor_cpu_checkpoint(
        "MACHINE_REQUEST_READY",
        trace=getattr(machine_request,"trace_id",None),
        goal=getattr(machine_request,"goal",None),
    )

def executor_cpu_after_response(machine_response):

    executor_cpu_enter_stage('executor_cpu_after_response')
    executor_cpu_leave_stage('executor_cpu_after_response')
    return executor_cpu_checkpoint(
        "MACHINE_RESPONSE_READY",
        has_answer=bool(getattr(machine_response,"answer",None)),
        has_blocks=bool(getattr(machine_response,"render_blocks",[])),
    )

def executor_cpu_after_scene(machine_scene):

    executor_cpu_enter_stage('executor_cpu_after_scene')
    executor_cpu_leave_stage('executor_cpu_after_scene')
    return executor_cpu_checkpoint(
        "SCENE_READY",
        block_count=len(getattr(machine_scene,"blocks",[]) or []),
    )





APRIL_CPU_REGISTRY = {
    "semantic": {
        "role": "Semantic Analysis",
        "input": "UserText",
        "output": "SemanticState",
        "next": "rooms",
    },
    "rooms": {
        "role": "Domain Processing",
        "input": "MachineRequest",
        "output": "MachineResponse",
        "next": "provider",
    },
    "provider": {
        "role": "LLM Provider",
        "input": "MachineRequest",
        "output": "MachineResponse",
        "next": "executor_reflection",
    },
    "executor_reflection": {
        "role": "CPU Reflection",
        "input": "MachineResponse",
        "output": "MachineScene",
        "next": "bot_ru",
    },
    "bot_ru": {
        "role": "Machine→Human Translation",
        "input": "MachineScene",
        "output": "SceneContract",
        "next": "checkout_server",
    },
    "checkout_server": {
        "role": "Transport",
        "input": "SceneContract",
        "output": "GatewayTransport",
        "next": "aprilweb",
    },
    "aprilweb": {
        "role": "Renderer",
        "input": "GatewayTransport",
        "output": "VisualScene",
        "next": None,
    },
}

def executor_cpu_expected(stage):
    return APRIL_CPU_REGISTRY.get(stage, {})


EXECUTOR_CPU_ROUTE = {
    "aprilweb_input": None,
    "semantic": None,
    "machine_request": None,
    "provider_request": None,
    "provider_response": None,
    "machine_response": None,
    "reflection": None,
    "machine_scene": None,
    "aprilweb_output": None,
}


# ===== XSCRUTER X002 CORE =====

def executor_cpu_sync(stage, value):
    """
    Canonical CPU synchronization point.
    Updates route, verifies stage and records a checkpoint.
    """
    executor_cpu_update(stage, value)
    executor_cpu_verify_stage(stage, value)
    return value

def executor_cpu_route_snapshot():
    return {
        "route": EXECUTOR_CPU_ROUTE.copy(),
        "health": executor_cpu_health(),
        "session": EXECUTOR_CPU_SESSION,
    }

# ===== END XSCRUTER X002 CORE =====

def executor_cpu_update(stage, value):
    if stage in EXECUTOR_CPU_ROUTE:
        EXECUTOR_CPU_ROUTE[stage] = value
    executor_cpu_checkpoint(stage, updated=True)
    return EXECUTOR_CPU_ROUTE


def executor_cpu_verify_stage(stage, value):
    """
    CPU contract verification.
    Does not execute subsystem logic.
    Only validates that the expected output exists.
    """
    reg = executor_cpu_expected(stage)
    ok = value is not None
    executor_cpu_checkpoint(
        stage,
        status="OK" if ok else "FAIL",
        verified=ok,
        expected_output=reg.get("output"),
    )
    return ok

def executor_cpu_finalize_report():
    """
    Produce one consolidated execution report for the entire route.
    """
    return {
        "executor_role": "APRIL_CPU",
        "registry": APRIL_CPU_REGISTRY,
        "trace": EXECUTOR_CPU_TRACE,
        "health": executor_cpu_health(),
        "route": EXECUTOR_CPU_ROUTE,
    }


def executor_cpu_health():
    return {
        "known_stages": sum(v is not None for v in EXECUTOR_CPU_ROUTE.values()),
        "total_stages": len(EXECUTOR_CPU_ROUTE),
        "complete": all(v is not None for v in EXECUTOR_CPU_ROUTE.values()),
    }



def executor_cpu_cycle(
    *,
    aprilweb_input=None,
    semantic=None,
    cognition=None,
    machine_request=None,
    provider_request=None,
    provider_response=None,
    machine_response=None,
    reflection=None,
    machine_scene=None,
    aprilweb_output=None,
):
    """Central CPU synchronization point.
    It never changes routing or calls Provider/OpenAI.
    It only maintains a complete awareness of the lifecycle.
    """

    executor_cpu_update("aprilweb_input", aprilweb_input)
    executor_cpu_update("semantic", semantic)
    executor_cpu_update("machine_request", machine_request)
    executor_cpu_update("provider_request", provider_request)
    executor_cpu_update("provider_response", provider_response)
    executor_cpu_update("machine_response", machine_response)
    executor_cpu_update("reflection", reflection)
    executor_cpu_update("machine_scene", machine_scene)
    executor_cpu_update("aprilweb_output", aprilweb_output)

    return {
        "route": EXECUTOR_CPU_ROUTE.copy(),
        "health": executor_cpu_health(),
        "trace_size": len(EXECUTOR_CPU_TRACE),
        "executor_role": "APRIL_CPU"
    }





EXECUTOR_CPU_SESSION = {
    "id": None,
    "stages": {},
    "started_at": None,
}

def executor_cpu_enter_stage(stage):
    import time
    EXECUTOR_CPU_SESSION["stages"].setdefault(stage,{})
    EXECUTOR_CPU_SESSION["stages"][stage]["status"]="running"
    EXECUTOR_CPU_SESSION["stages"][stage]["started_at"]=time.time()

def executor_cpu_leave_stage(stage):
    import time
    s=EXECUTOR_CPU_SESSION["stages"].setdefault(stage,{})
    s["finished_at"]=time.time()
    s["status"]="success"
    if "started_at" in s:
        s["duration"]=s["finished_at"]-s["started_at"]

def executor_cpu_fail_stage(stage,error):
    import time
    s=EXECUTOR_CPU_SESSION["stages"].setdefault(stage,{})
    s["finished_at"]=time.time()
    s["status"]="failed"
    s["error"]=str(error)

def executor_cpu_execution_report():
    return EXECUTOR_CPU_SESSION




def executor_cpu_build_presentation_plan(machine_response):
    """
    Inspect MachineResponse and prepare presentation hints
    without calling Provider/OpenAI.
    """
    plan = {"representation":"text","blocks":[]}

    artifacts = getattr(machine_response, "artifacts", []) or []
    for art in artifacts:
        data = getattr(art, "data", {}) if hasattr(art, "data") else {}
        if isinstance(data, dict):
            if "multiplication_table" in data or "table_data" in data:
                plan["representation"]="table"
                plan["blocks"].append("table")
            if "graph_data" in data:
                plan["representation"]="graph"
                plan["blocks"].append("graph")
            if "formula" in data:
                plan["blocks"].append("formula")

    machine_response.executor_presentation_plan = plan
    return machine_response


def executor_cpu_build_cognitive_context(*, semantic, cognition, response_decision, state, machine_response):
    """Internal CPU-only cognitive integration.
    Never produces user-visible text and never calls Provider/OpenAI.
    """
    reflection = {
        "dialog": state.get("dialog", []),
        "memory_timeline": state.get("memory_timeline", {}),
        "active_visual_scene": state.get("active_visual_scene", {}),
        "visual_summary": state.get("visual_summary", {}),
        "trajectory": state.get("scene_state", {}).get("trajectory"),
        "goal_hierarchy": state.get("goal_hierarchy", {}),
        "dynamic_focus": cognition.get("dynamic_focus", {}),
        "open_loops": cognition.get("open_loops", {}),
        "preferred_representation": response_decision.get("preferred_representation"),
        "internal_only": True,
        "human_visible": False,
    }
    setattr(machine_response, "executor_cognitive_context", reflection)
    return machine_response


def executor_cpu_build_executor_decision(*, semantic, cognition, response_decision, state, machine_response):
    """CPU-only decision layer. Produces machine decision, never user text."""
    ctx=getattr(machine_response,"executor_cognitive_context",{}) or {}
    decision={
        "topic_mode":"continuation" if ctx.get("trajectory") else "new_topic",
        "use_visual_memory":bool(ctx.get("active_visual_scene")),
        "use_memory_timeline":bool(ctx.get("memory_timeline")),
        "continue_scene":bool(ctx.get("active_visual_scene")),
        "representation":response_decision.get("preferred_representation")
            or semantic.get("preferred_representation")
            or "text",
        "internal_only":True,
        "human_visible":False,
    }
    setattr(machine_response,"executor_decision",decision)
    return machine_response



def executor_cpu_integrate_presentation(machine_response):
    """
    Stage 3 - Presentation Integration.
    Final CPU-only alignment between executor_decision and
    executor_presentation_plan before MachineScene creation.
    """
    decision = getattr(machine_response, "executor_decision", {}) or {}
    plan = getattr(machine_response, "executor_presentation_plan", {}) or {}

    preferred = (
        decision.get("preferred_representation")
        or plan.get("representation")
        or "text"
    )

    plan["representation"] = preferred
    plan["executor_integrated"] = True
    plan["internal_only"] = True
    plan["human_visible"] = False

    machine_response.executor_presentation_plan = plan
    machine_response.executor_presentation_integrated = True
    return machine_response

def executor_cpu_reflect(
    *,
    semantic,
    cognition,
    response_decision,
    state,
    machine_response,
):
    """
    Executor-owned decision layer.
    No Provider/OpenAI calls.
    Decides how the response should be represented before Scene creation.
    """
    machine_response = executor_cpu_build_cognitive_context(
        semantic=semantic,
        cognition=cognition,
        response_decision=response_decision,
        state=state,
        machine_response=machine_response,
    )
    machine_response = executor_cpu_build_executor_decision(
        semantic=semantic,
        cognition=cognition,
        response_decision=response_decision,
        state=state,
        machine_response=machine_response,
    )
    machine_response = executor_cpu_build_presentation_plan(machine_response)
    machine_response = executor_cpu_integrate_presentation(machine_response)
    machine_response = executor_cpu_materialize_blocks(machine_response)
    machine_response = executor_cpu_attach_artifact_payloads(machine_response)

    planner = {
        "goal": semantic.get("intent"),
        "representation": (
            response_decision.get("preferred_representation")
            or semantic.get("preferred_representation")
            or "text"
        ),
        "memory_active": bool(state.get("memory_timeline")),
        "visual_active": bool(state.get("active_visual_scene")),
        "dialog_focus": cognition.get("dynamic_focus", {}),
    }

    decision = getattr(machine_response,"executor_decision",{}) or {}
    if decision.get("representation"):
        planner["representation"] = decision["representation"]
    planner["presentation_plan"] = getattr(machine_response,"executor_presentation_plan",{})
    setattr(machine_response, "executor_planner", planner)
    setattr(machine_response, "executor_cpu_verified", True)
    return machine_response




EXECUTOR_CPU_OBJECTS = {
    "machine_request": {},
    "machine_response": {},
    "machine_scene": {},
}

def executor_cpu_mark_object(name, obj, owner):
    if obj is None:
        return
    EXECUTOR_CPU_OBJECTS[name] = {
        "owner": owner,
        "object_type": type(obj).__name__,
        "object_id": id(obj),
    }

def executor_cpu_lineage_report():
    return {
        "session": EXECUTOR_CPU_SESSION,
        "objects": EXECUTOR_CPU_OBJECTS,
    }




def executor_cpu_sync_scene(machine_response, machine_scene):
    """
    Ensure MachineScene inherits CPU-generated render blocks.
    Does not generate new knowledge or call Provider.
    """
    response_blocks = list(getattr(machine_response, "render_blocks", []) or [])

    scene_blocks = getattr(machine_scene, "render_blocks", None)
    if scene_blocks is None:
        setattr(machine_scene, "render_blocks", [])

    machine_scene.render_blocks = response_blocks
    machine_scene.blocks = machine_scene.render_blocks

    machine_scene.executor_cpu_scene_sync = {
        "synced": True,
        "response_blocks": len(response_blocks),
        "scene_blocks": len(getattr(machine_scene, "render_blocks", []) or []),
    }
    return machine_scene

def executor_cpu_finalize_scene(machine_response, machine_scene):
    """CPU becomes the final approval point before AprilWeb.
    It does not rebuild the scene; it validates and annotates it.
    """
    planner=getattr(machine_response,"executor_planner",{}) or {}
    verification={
        "approved": True,
        "representation": planner.get("representation","text"),
        "goal": planner.get("goal"),
        "has_blocks": bool(getattr(machine_scene,"blocks",[])),
        "block_count": len(getattr(machine_scene,"blocks",[]) or []),
    }
    verification["executor_decision"] = getattr(machine_response, "executor_decision", {})
    machine_scene.executor_cpu=verification
    machine_scene.executor_cpu_verified=True
    machine_scene.executor_decision = getattr(machine_response, "executor_decision", {})
    return machine_scene



def executor_cpu_validate_completeness(machine_response, machine_scene):
    """Validate that the response representation matches the CPU plan.
    This stage never calls Provider/OpenAI and never creates a new route.
    """
    planner = getattr(machine_response, "executor_planner", {}) or {}
    rep = planner.get("representation", "text")

    blocks = list(getattr(machine_scene, "blocks", []) or [])
    block_types = {
        b.get("type") for b in blocks
        if isinstance(b, dict) and "type" in b
    }

    completeness = {
        "representation": rep,
        "representation_present": rep in block_types if rep != "text" else True,
        "block_types": sorted(block_types),
        "approved": True,
    }

    machine_scene.executor_cpu_completeness = completeness
    return machine_scene




EXECUTOR_CPU_ROUTE_GUARD = []

def executor_cpu_verify_identity(name, obj):
    if obj is None:
        return True
    current=id(obj)
    known=EXECUTOR_CPU_OBJECTS.get(name,{})
    previous=known.get("object_id")
    ok=(previous is None or previous==current)
    EXECUTOR_CPU_ROUTE_GUARD.append({
        "object":name,
        "previous":previous,
        "current":current,
        "stable":ok,
    })
    return ok

def executor_cpu_route_guard_report():
    return {
        "objects":EXECUTOR_CPU_OBJECTS,
        "route_guard":EXECUTOR_CPU_ROUTE_GUARD,
    }



EXECUTOR_CPU_PAYLOAD_TRACE=[]

def executor_cpu_capture_payload(stage, obj):
    if obj is None:
        return
    entry={
        "stage": stage,
        "answer": bool(getattr(obj,"answer",None)),
        "summary": bool(getattr(obj,"summary",None)),
        "content": bool(getattr(obj,"content",None)),
        "artifacts": len(getattr(obj,"artifacts",[]) or []),
        "render_blocks": len(getattr(obj,"render_blocks",[]) or []),
    }
    EXECUTOR_CPU_PAYLOAD_TRACE.append(entry)
    return entry

def executor_cpu_payload_report():
    return EXECUTOR_CPU_PAYLOAD_TRACE


def executor_cpu_register_room(cpu_log, room_name, score=None,
                               executed=False, accepted=False):
    if cpu_log is None:
        cpu_log=[]
    cpu_log.append({
        "room": room_name,
        "score": score,
        "executed": executed,
        "accepted": accepted,
    })
    return cpu_log

def executor_cpu_attach_room_report(machine_scene, room_report):
    machine_scene.executor_room_report = room_report
    return machine_scene


# X006 REVIEW PATCH
# TODO:
# - Preserve canonical MachineResponse after Provider.
# - Prevent normalization from overwriting answer/content.
# - Ensure MachineScene is built only from canonical MachineResponse.
# - Fail fast if SceneContract loses answer/content.

# X005 placeholder for canonical MachineResponse guard


# ==========================================================
# X013 SINGLE SPACE EXPERIMENT
# ==========================================================
def executor_cpu_build_canonical_space(  # LEGACY_DEPRECATEDmachine_response):
    scene = build_machine_scene(machine_response)
    blocks = list(getattr(scene, "render_blocks", None) or getattr(scene, "blocks", []) or [])
    return {
        "machine_response": machine_response,
        "machine_scene": scene,
        "answer": getattr(machine_response, "answer", None),
        "content": getattr(machine_response, "content", None),
        "summary": getattr(machine_response, "summary", None),
        "render_blocks": blocks,
        "scene_contract": True,
    }


# ==========================================================
# X014 SINGLE SPACE ROUTER
# ==========================================================
def executor_cpu_space_to_scene_contract(  # LEGACY_DEPRECATEDspace):
    """Build a SceneContract directly from the canonical space."""
    return {
        "scene_contract": True,
        "machine_scene": space.get("machine_scene"),
        "render_blocks": list(space.get("render_blocks") or []),
        "answer": space.get("answer"),
        "content": space.get("content"),
        "summary": space.get("summary"),
    }

# Next implementation step:
# Replace intermediate payload construction with:
# canonical_space -> executor_cpu_space_to_scene_contract()


# ==========================================================
# X015 SINGLE SPACE STAGE 3
# ==========================================================

def executor_cpu_finalize_space(space):
    """Normalize the canonical space before transport."""
    space = dict(space)

    if not space.get("content") and space.get("answer"):
        space["content"] = space["answer"]

    if not space.get("summary") and space.get("content"):
        space["summary"] = space["content"]

    if space.get("machine_scene") is not None and not space.get("render_blocks"):
        scene = space["machine_scene"]
        space["render_blocks"] = list(
            getattr(scene, "render_blocks", None) or
            getattr(scene, "blocks", []) or []
        )

    space["canonical_space"] = True
    return space

# Planned migration:
# MachineResponse
#      ↓
# executor_cpu_build_canonical_space()
#      ↓
# executor_cpu_finalize_space()
#      ↓
# executor_cpu_space_to_scene_contract()


# ==========================================================
# X016 SINGLE SPACE STAGE 4
# ==========================================================

def executor_cpu_execute_canonical_space(  # LEGACY_DEPRECATEDmachine_response):
    """Experimental unified execution path.

    Builds one canonical space, normalizes it and derives the
    SceneContract from that single object.
    """
    space = executor_cpu_build_canonical_space(machine_response)
    space = executor_cpu_finalize_space(space)
    contract = executor_cpu_space_to_scene_contract(space)

    contract["canonical_space"] = True
    contract["executor_route"] = "single_space_cpu"

    return contract

# Planned integration:
# Provider
#   -> MachineResponse
#   -> executor_cpu_execute_canonical_space()
#   -> Checkout
#   -> AprilWeb


# ==========================================================
# X018 CPU SINGLE SPACE CORE
# ==========================================================
def executor_cpu_build_single_space(machine_response):
    """Canonical CPU object. All downstream structures derive from this space."""
    scene = build_machine_scene(machine_response)

    blocks = list(getattr(scene, "render_blocks", None) or getattr(scene, "blocks", []) or [])

    answer = getattr(machine_response, "answer", None)
    content = getattr(machine_response, "content", None) or answer
    summary = getattr(machine_response, "summary", None) or content

    return {
        "canonical_space": True,
        "machine_response": machine_response,
        "machine_scene": scene,
        "answer": answer,
        "content": content,
        "summary": summary,
        "render_blocks": blocks,
        "scene_contract": {
            "machine_scene": scene,
            "render_blocks": blocks,
            "answer": answer,
            "content": content,
            "summary": summary,
        },
    }

# Planned migration:
# collect_machine_contract()
#      ↓
# merge_machine_responses()
#      ↓
# executor_cpu_build_single_space()
#      ↓
# Checkout / AprilWeb


# ==========================================================
# X019 SINGLE SPACE CLEAN ROUTE
# Transitional cleanup plan:
#  - CPU owns one Canonical Space.
#  - SceneContract is derived only from Canonical Space.
#  - No parallel payload ownership.
# ==========================================================

def executor_cpu_finalize_transport(machine_response):
    """Return the final transport object from the canonical CPU space."""
    space = executor_cpu_build_single_space(machine_response)
    return space["scene_contract"]

# DEPRECATION NOTICE
# Legacy helper chain should be removed after validation:
#   executor_cpu_build_canonical_space()
#   executor_cpu_finalize_space()
#   executor_cpu_space_to_scene_contract()
#   executor_cpu_execute_canonical_space()
#
# Target route:
# MachineResponse
#      ↓
# executor_cpu_build_single_space()
#      ↓
# executor_cpu_finalize_transport()
#      ↓
# Checkout


# ==========================================================
# X021 CLEANUP STATUS
# Active route:
# MachineResponse
#   -> executor_cpu_build_single_space()
#   -> executor_cpu_finalize_transport()
#   -> Checkout
#
# Remaining legacy build_checkout_scene_contract() call sites
# should be removed after validation.
# ==========================================================
