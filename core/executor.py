


# ==========================================================
# X025 OPTIMIZATION PASS
# Executor target:
# MachineRequest -> Rooms -> MachineResponse
# -> SingleSpace -> SceneContract -> Checkout
# Legacy path scheduled for removal after validation.
# ==========================================================


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
        unified_machine_scene = executor_cpu_scene_pipeline(unified_machine_response)
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
    # Canonical scene assembly.
    # Prefer MachineScene blocks and only fall back to legacy
    # artifact conversion when MachineScene has no renderable blocks.
    # Canonical hand-off object for checkout_server.
    # Executor exposes one Scene Contract without rebuilding it.
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
    # Single executor awareness object.
    # This is diagnostic state only.
    # No Provider/OpenAI calls are allowed here.
    # Canonical CPU synchronization point.
    # Updates route, verifies stage and records a checkpoint.
    # CPU contract verification.
    # Does not execute subsystem logic.
    # Only validates that the expected output exists.
    # Produce one consolidated execution report for the entire route.
    # It never changes routing or calls Provider/OpenAI.
    # It only maintains a complete awareness of the lifecycle.
    # Inspect MachineResponse and prepare presentation hints
    # without calling Provider/OpenAI.
    # Never produces user-visible text and never calls Provider/OpenAI.
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





# ==========================================================
# X024 UNIFIED SCENE PIPELINE
# ==========================================================
def executor_cpu_scene_pipeline(machine_response):
    # Ensure MachineScene inherits CPU-generated render blocks.
    # Does not generate new knowledge or call Provider.
    # It does not rebuild the scene; it validates and annotates it.
    # This stage never calls Provider/OpenAI and never creates a new route.
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
    return {
        'transport_contract':'scene_first',
        'provider_contract':'fiber_v3',
        'answer': getattr(machine_response,'answer',None),
        'content': getattr(machine_response,'content',None),
        'summary': getattr(machine_response,'summary',None),
        'machine_response': machine_response,
        'scene_contract': True,
        'render_blocks': list(getattr(machine_response,'render_blocks',[]) or []),
    }


# ==========================================================
# PUBLIC EXECUTOR ENTRY (X029)
# Temporary compatibility facade for bot.py / checkout_server.py
# ==========================================================

async def execute(
    user_id,
    chat_id=None,
    text="",
    run_with_activity=None,
    **kwargs,
):
    chat_id = chat_id or user_id
    state = get_state(user_id)
    semantic = semantic_analyze(text)
    reasoning = build_reasoning_state(text=text, semantic=semantic, state=state)
    cognition = analyze_cognition(
        text=text,
        semantic=semantic,
        reasoning=reasoning,
        state=state,
    )
    visual_reference = build_visual_reference(
        semantic=semantic,
        cognition=cognition,
        text=text,
        state=state,
    )

    response_decision = build_response_decision(
        semantic=semantic,
        cognition=cognition,
        state=state,
        visual_reference=visual_reference,
    )
    task_type = detect_task_type(
        semantic,
        cognition,
        state,
    )
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
        text=text,
    )
    context["machine_request"] = MachineRequest(
        text=text,
        context=context,
    )
    return await execute_rooms(
        user_id=user_id,
        text=text,
        context=context,
        semantic=semantic,
        cognition=cognition,
        response_decision=response_decision,
        state=state,
        run_with_activity=run_with_activity,
    )
