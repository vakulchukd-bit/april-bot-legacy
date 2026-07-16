


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
    ROOMS,
    registry_parent_dispatch,
)

from blocks.C_ARTIFACT_CONTRACT import (
    MachineRequest,
    MachineResponse,
    MachineScene,
    UniversalArtifactContract,
    build_machine_scene,
    build_scene_contract,
)



# Legacy provider import (CPU should not call Provider directly)
# TODO(Stage5): Provider must be called outside CPU coordinator
from blocks.provider_router import generate_text

# 🧠 PRESENTATION

# Legacy presentation layer (scheduled for removal from CPU)
# TODO(Stage5): move Presentation Layer out of CPU
from blocks.presentation_formatter import (
    format_response_presentation
)


# TODO(Stage5): move Energy service behind CPU interface
from blocks.energy_manager import (
    get_energy
)

# TODO(Stage5): move Experience service behind CPU interface
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
    return


    if not name:
        return

    EMAPS[
        "active_rooms"
    ].add(name)

def track_trajectory(name):
    return


    if not name:
        return

    EMAPS[
        "active_trajectories"
    ].add(name)

def track_modality(name):
    return


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
    state,
    conversation_space=None,
):

    # conversation_space may not exist yet during the early
    # executor stages. Fall back to state-only user space.
    user_space = build_executor_user_space(
        state,
        conversation_space=conversation_space,
    )

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


def build_conversation_space(state, semantic, cognition, response_decision, text, visual_reference):
    """
    Canonical Conversation Space shared by MachineRequest, MachineResponse and MachineScene.
    Contains no rendering logic and performs no Provider/OpenAI calls.
    """
    return {
        "timeline": state.get("dialog", []),
        "current_turn": {
            "user": {
                "text": text,
                "voice": None,
                "image": None,
                "files": [],
                "timestamp": datetime.utcnow().isoformat(),
            },
            "april": None,
        },
        "modalities": {
            "text": bool(text),
            "voice": False,
            "image": False,
            "files": False,
        },
        "last_user_turn": text,
        "last_april_turn": state.get("last_april_turn"),
        "semantic": semantic,
        "cognition": cognition,
        "response_decision": response_decision,
        "goal_hierarchy": state.get("goal_hierarchy", {}),
        "focus": state.get("focus_state", state.get("dynamic_focus", {})),
        "memory_timeline": state.get("memory_timeline", {}),
        "visual_summary": state.get("visual_summary", {}),
        "active_visual_scene": state.get("active_visual_scene", {}),
        "visual_reference": visual_reference,
    }

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

    conversation_space = build_conversation_space(
        state=state,
        semantic=semantic,
        cognition=cognition,
        response_decision=response_decision,
        text=text,
        visual_reference=visual_reference,
    )

    return {


        "machine_channel":
            TASK_CHANNEL,

        "task_type":
            task_type,

        "executor_version":
            "april_cpu_v1",


        "user_id":
            user_id,

        # Legacy transport identifier
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


        "machine_input": text,
        "platform": "agnostic",


        "state":
            state,

        "user_space":
            user_space,

        "canonical_space": conversation_space,
        "conversation_space": conversation_space,

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


def build_executor_user_space(state, conversation_space=None):
    conversation_space = conversation_space or {}
    return {
        "scene": state.get("scene_state", {}),
        "workspace": state.get("workspace_state", {}),
        "dialog": conversation_space.get("timeline", state.get("dialog", [])),
        "last_user_turn": conversation_space.get("last_user_turn"),
        "last_april_turn": conversation_space.get("last_april_turn"),
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



def executor_cpu_register_room(report, room_name, **kwargs):
    entry={"room": room_name}
    entry.update(kwargs)
    report.append(entry)
    return report

async def execute_rooms(
    user_id,
    text,
    context,
    semantic,
    cognition,
    response_decision,
    state,
    run_with_activity,
):
    cpu_trace_begin("ROOM_EXECUTION", {"text": text})
    machine_request = context.get("machine_request")
    if machine_request is None:
        raise RuntimeError("MachineRequest missing from executor context")

    machine_response = None
    room_results = []
    room_execution_report = []

    for room in ROOMS:
        try:
            result = await room.handle(
                user_id=user_id,
                text=text,
                context=machine_request,
                run=run_with_activity,
            )

            if isinstance(result, MachineResponse):
                room_results.append({"room": getattr(room,"name","unknown"), "machine_response": result})
                room_execution_report.append({"room": getattr(room,"name","unknown"), "status":"ok"})
                if machine_response is None:
                    machine_response = result
                continue

            if isinstance(result, dict) and isinstance(result.get("machine_response"), MachineResponse):
                room_results.append({"room": getattr(room,"name","unknown"), "machine_response": result["machine_response"]})
                room_execution_report.append({"room": getattr(room,"name","unknown"), "status":"ok"})
                if machine_response is None:
                    machine_response = result["machine_response"]
                continue

        except Exception as exc:
            room_execution_report.append({"room": getattr(room,"name","unknown"), "status":"error","error":str(exc)})
            continue

    if machine_response is None:
        raise RuntimeError("No MachineResponse produced")

    conversation_space=context.get("conversation_space") or {}
    april_turn={
        "answer": getattr(machine_response,"answer",None),
        "summary": getattr(machine_response,"summary",None),
        "render_blocks": list(getattr(machine_response,"render_blocks",[]) or []),
    }
    conversation_space["current_turn"]["april"]=april_turn
    conversation_space["last_april_turn"]=april_turn

    timeline = conversation_space.setdefault("timeline", [])
    timeline.append(conversation_space["current_turn"])
    conversation_space["dialog"] = timeline
    setattr(machine_response, "conversation_space", conversation_space)

    executor_cpu_transport_diag('BEFORE_REFLECT', machine_response)
    machine_response = executor_cpu_reflect(
        semantic=semantic,
        cognition=cognition,
        response_decision=response_decision,
        state=state,
        machine_response=machine_response,
    )

    setattr(machine_response,"room_execution_report",room_execution_report)
    if not room_results:
        room_results=[{"machine_response":machine_response}]
    machine_response = registry_parent_dispatch(
        machine_request,
        room_results,
    )

    executor_cpu_transport_diag('AFTER_REFLECT', machine_response)

    setattr(machine_response, "provider_transport_verified", True)
    setattr(machine_response, "provider_contract_version", "fiber_v3_stage2")


    diagnostics = (
        getattr(machine_response, "contributions", {})
        .get("registry_diagnostics", {})
    )

    cpu_trace_success(
        "ROOM_EXECUTION",
        {
            "answer": getattr(machine_response, "answer", None),
            "artifacts": len(getattr(machine_response, "artifacts", []) or []),
            "diagnostics": diagnostics,
        },
    )

    return executor_cpu_finalize_transport(machine_response)

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

# ==========================================================
# APRIL CPU TRACE INFRASTRUCTURE (Stage 1)
# ==========================================================
APRIL_CPU_TRACE_ENABLED=False
CPU_EXECUTION_JOURNAL=[]



# ==========================================================
# APRIL CPU STAGE REGISTRY (Stage 5)
# ==========================================================

CPU_STAGE_REGISTRY=[]

def cpu_stage_record(stage,status,details=None):
    entry={
        "stage":stage,
        "status":status,
        "details":details or {},
        "timestamp":time.time(),
    }
    CPU_STAGE_REGISTRY.append(entry)
    return entry

def cpu_stage_snapshot():
    return list(CPU_STAGE_REGISTRY)

def cpu_trace_begin(stage,payload=None):
    if not APRIL_CPU_TRACE_ENABLED:
        return
    cpu_stage_record(stage,"BEGIN",payload or {})
    CPU_EXECUTION_JOURNAL.append({"stage":stage,"status":"BEGIN","payload":payload or {},"timestamp":time.time()})

def cpu_trace_success(stage,payload=None):
    if not APRIL_CPU_TRACE_ENABLED:
        return
    cpu_stage_record(stage,"SUCCESS",payload or {})
    CPU_EXECUTION_JOURNAL.append({"stage":stage,"status":"SUCCESS","payload":payload or {},"timestamp":time.time()})

def cpu_trace_error(stage,error):
    if not APRIL_CPU_TRACE_ENABLED:
        return
    cpu_stage_record(stage,"ERROR",{"error":str(error)})
    CPU_EXECUTION_JOURNAL.append({"stage":stage,"status":"ERROR","error":str(error),"timestamp":time.time()})

def cpu_execution_journal():
    return list(CPU_EXECUTION_JOURNAL)



# Legacy trace retained but disabled
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
    return payload.get("machine_response")
    # disabled legacy checkpoint
    ctx={}
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

def executor_cpu_build_cognitive_context(*, semantic, cognition, response_decision, state, machine_response):
    """Internal CPU-only cognitive integration.
    Never produces user-visible text and never calls Provider/OpenAI.
    """
    conversation_space = getattr(machine_response, "conversation_space", {}) or {}

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
        "conversation_space": conversation_space,
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





def executor_cpu_normalize_answer(machine_response):
    """Ensure canonical text fields always exist before Scene construction."""
    answer = getattr(machine_response, "answer", None)
    content = getattr(machine_response, "content", None)
    summary = getattr(machine_response, "summary", None)

    value = answer or content or summary

    if not value:
        for block in list(getattr(machine_response, "render_blocks", []) or []):
            if isinstance(block, dict):
                value = block.get("content") or block.get("text")
                if value:
                    break

    if not value:
        for art in list(getattr(machine_response, "artifacts", []) or []):
            data = getattr(art, "data", None)
            if isinstance(data, dict):
                value = (
                    data.get("answer")
                    or data.get("content")
                    or data.get("summary")
                    or data.get("text")
                )
                if value:
                    break

    value = value or ""

    machine_response.answer = value
    machine_response.content = value
    machine_response.summary = value
    return machine_response


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
    machine_response = executor_cpu_normalize_answer(machine_response)

    conversation_space = getattr(machine_response, "conversation_space", {}) or {}

    semantic = conversation_space.get("semantic", semantic)
    cognition = conversation_space.get("cognition", cognition)
    response_decision = conversation_space.get("response_decision", response_decision)

    planner = {
        "goal": semantic.get("intent"),
        "conversation_space": conversation_space,
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



def executor_cpu_transport_diag(stage, machine_response=None, scene_contract=None):
    try:
        print({
            "APRIL_EXECUTOR_STAGE": stage,
            "answer": getattr(machine_response, "answer", None),
            "content": getattr(machine_response, "content", None),
            "summary": getattr(machine_response, "summary", None),
            "render_blocks": len(getattr(machine_response, "render_blocks", []) or []),
            "has_scene_contract": scene_contract is not None,
        })
    except Exception as exc:
        print({"APRIL_EXECUTOR_STAGE": stage, "diag_error": str(exc)})


def executor_cpu_sync_scene_contract(scene_contract, machine_response, scene):
    """Synchronize canonical fields into SceneContract."""
    if scene_contract is None:
        return scene_contract

    for field in ("answer", "content", "summary", "render_blocks", "artifacts", "metadata"):
        value = getattr(machine_response, field, None)
        if field == "metadata":
            value = value or {}
            value.setdefault("answer", getattr(machine_response, "answer", ""))
            value.setdefault("content", getattr(machine_response, "content", ""))
            value.setdefault("summary", getattr(machine_response, "summary", ""))
        if value is None and hasattr(scene, field):
            value = getattr(scene, field)
        try:
            setattr(scene_contract, field, value)
        except Exception:
            if isinstance(scene_contract, dict):
                scene_contract[field] = value
    return scene_contract

def executor_cpu_scene_pipeline(machine_response):
    # Ensure MachineScene inherits CPU-generated render blocks.
    # Does not generate new knowledge or call Provider.
    # It does not rebuild the scene; it validates and annotates it.
    # This stage never calls Provider/OpenAI and never creates a new route.
    scene = build_machine_scene(machine_response)
    try:
        setattr(scene, "conversation_space",
                getattr(machine_response, "conversation_space", None))
    except Exception:
        pass

    conversation_space = getattr(machine_response, "conversation_space", {}) or {}

    blocks = list(getattr(scene, "render_blocks", None) or getattr(scene, "blocks", []) or [])

    try:
        setattr(scene, "timeline", conversation_space.get("timeline", []))
        setattr(scene, "last_user_turn", conversation_space.get("last_user_turn"))
        setattr(scene, "last_april_turn", conversation_space.get("last_april_turn"))
        setattr(scene, "active_goal", conversation_space.get("response_decision", {}).get("goal"))
    except Exception:
        pass

    current_turn = conversation_space.get("current_turn", {})
    april_turn = current_turn.get("april") or {}

    answer = april_turn.get("answer") or getattr(machine_response, "answer", None)
    content = getattr(machine_response, "content", None) or answer
    summary = april_turn.get("summary") or getattr(machine_response, "summary", None) or content

    scene_contract = build_scene_contract(scene)
    executor_cpu_transport_diag('AFTER_BUILD_SCENE_CONTRACT', machine_response, scene_contract)
    scene_contract = executor_cpu_sync_scene_contract(scene_contract, machine_response, scene)
    executor_cpu_transport_diag('AFTER_SYNC_SCENE_CONTRACT', machine_response, scene_contract)

    return {
        "canonical_space": True,
        "machine_response": machine_response,
        "machine_scene": scene,
        "answer": answer,
        "content": content,
        "summary": summary,
        "render_blocks": blocks,
        "scene_contract": scene_contract,  # canonical factory contract
        "scene_runtime": {
            "conversation_space": conversation_space,
            "current_turn": conversation_space.get("current_turn"),
            "timeline": conversation_space.get("timeline", []),
            "last_user_turn": conversation_space.get("last_user_turn"),
            "last_april_turn": conversation_space.get("last_april_turn"),
            "machine_scene": scene,
            "current_turn": current_turn,
            "render_blocks": blocks,
            "answer": answer,
            "content": content,
            "summary": summary,
            "modalities": conversation_space.get("modalities", {}),
            "dialog": conversation_space.get("dialog", []),
            "goal_hierarchy": conversation_space.get("goal_hierarchy", {}),
            "focus": conversation_space.get("focus", {}),
        },
    }

# Planned migration:
#      ↓
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
    scene = executor_cpu_scene_pipeline(machine_response)
    conversation_space = getattr(machine_response, "conversation_space", None)

    executor_cpu_transport_diag('FINAL_TRANSPORT', machine_response, scene.get('scene_contract'))
    return {
        "transport_contract": "scene_first",
        "provider_contract": "fiber_v3",
        "conversation_space": conversation_space,
        "machine_response": machine_response,
        "machine_scene": scene.get("machine_scene"),
        "scene_contract": scene.get("scene_contract"),
        "current_turn": conversation_space.get("current_turn") if conversation_space else None,
        "render_blocks": scene.get("render_blocks", []),
    }


# ==========================================================
# PUBLIC EXECUTOR ENTRY (X029)
# Temporary compatibility facade for bot.py / checkout_server.py
# ==========================================================



# ==========================================================
# APRIL CPU COORDINATION LAYER (Stage 3)
# ==========================================================

CPU_COORDINATION_POLICY = {
    "gateway":"checkout_server",
    "factory":"C_ARTIFACT_CONTRACT",
    "single_route":True,
    "trace_owner":"executor_cpu",
}



# ==========================================================
# APRIL CPU FACTORY BRIDGE (Stage 4)
# ==========================================================

def executor_cpu_factory_bridge(machine_result):
    """Single bridge between CPU and Artifact Factory output."""
    cpu_trace_begin("FACTORY_RETURN", {})
    if isinstance(machine_result, dict):
        cpu_trace_success("FACTORY_RETURN", {
            "has_scene_contract": "scene_contract" in machine_result,
            "has_machine_response": "machine_response" in machine_result,
            "has_machine_scene": "machine_scene" in machine_result,
        })
    return machine_result

def executor_cpu_gateway_dispatch(result):
    """Single exit point from CPU toward Gateway."""
    cpu_trace_success("CPU_GATEWAY_DISPATCH",{
        "scene_contract": isinstance(result,dict) and "scene_contract" in result
    })
    return result



# ==========================================================
# APRIL CPU <-> FACTORY HOOK BRIDGE (Stage 6)
# ==========================================================

def executor_cpu_register_factory_hooks(register_hook):
    """Attach CPU trace callbacks to Artifact Factory."""
    register_hook(
        begin=cpu_trace_begin,
        success=cpu_trace_success,
        error=cpu_trace_error,
    )

def executor_cpu_factory_event(stage, payload=None):
    cpu_trace_begin(stage, payload or {})

def executor_cpu_factory_complete(stage, payload=None):
    cpu_trace_success(stage, payload or {})



# ==========================================================
# APRIL CPU FACTORY SYNCHRONIZATION (Stage 7)
# ==========================================================

def executor_cpu_sync_factory_bridge(factory_register):
    """Bind CPU and Artifact Factory into one execution route."""
    executor_cpu_register_factory_hooks(factory_register)
    cpu_trace_success("FACTORY_BRIDGE_REGISTERED",{
        "single_route":True
    })

async def execute(
    user_id,
    chat_id=None,
    text="",
    run_with_activity=None,  # legacy compatibility, scheduled for removal
    **kwargs,
):
    chat_id = chat_id or user_id
    # CPU loads persistent state through the state service only.
    cpu_trace_begin("EXECUTE", {"user_id": user_id})
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
        conversation_space=None,
    )
    # Build canonical CPU context only once.
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
    # Canonical runtime state for every modality.
    conversation_space = context.get("conversation_space") or {}
    current_turn = conversation_space.get("current_turn", {})

    # Canonical CPU entry: build one MachineRequest from ConversationSpace
    # CPU owns exactly one MachineRequest for the whole execution.
    # Factory hooks are registered once CPU context exists.
    if "factory_hook_registration" in kwargs:
        executor_cpu_sync_factory_bridge(kwargs["factory_hook_registration"])

    context["machine_request"] = MachineRequest(
        goal=current_turn.get("user", {}).get("text", text),
        intent=semantic,
        memory=state,
        visual_context={"visual_reference": visual_reference},
        conversation=conversation_space,  # single shared user space
    )

    setattr(context["machine_request"], "current_turn", current_turn)

    # CPU delegates execution to Room Dispatcher
    # CPU ends here; domain execution belongs to Rooms.
    # After this point the CPU only supervises the execution lifecycle.
    result = await execute_rooms(
        user_id=user_id,
        text=text,
        context=context,
        semantic=semantic,
        cognition=cognition,
        response_decision=response_decision,
        state=state,
        run_with_activity=run_with_activity,
    )
    result = executor_cpu_factory_bridge(result)
    result = executor_cpu_gateway_dispatch(result)
    cpu_trace_success("EXECUTE")
    return result
