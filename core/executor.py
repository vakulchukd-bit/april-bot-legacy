

import traceback
import time
import re

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

from blocks.state_manager import (

    get_state,

    add_dialog,

    update_memory_summary,

    get_active_flow,

    build_visual_memory_bridge,
    update_dialog_context
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

from blocks.provider_router import generate_text

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



def _executor_value_is_empty(value):
    if value is None:
        return True
    if value == "":
        return True
    if value == []:
        return True
    if value == {}:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False

def _executor_best_text(*values):
    for value in values:
        if _executor_value_is_empty(value):
            continue
        if isinstance(value, str):
            text = value.strip()
        else:
            text = str(value).strip()
        if text:
            return text
    return ""

def _executor_preserve_canonical_text(machine_response, scene_contract=None, scene=None):
    if machine_response is None:
        return machine_response

    answer = _executor_best_text(
        getattr(machine_response, "answer", ""),
        getattr(machine_response, "content", ""),
        getattr(machine_response, "summary", ""),
    )

    if scene_contract is not None:
        if isinstance(scene_contract, dict):
            answer = _executor_best_text(
                answer,
                scene_contract.get("answer"),
                scene_contract.get("content"),
                scene_contract.get("summary"),
            )
        else:
            answer = _executor_best_text(
                answer,
                getattr(scene_contract, "answer", ""),
                getattr(scene_contract, "content", ""),
                getattr(scene_contract, "summary", ""),
            )

    if scene is not None and not answer:
        if isinstance(scene, dict):
            answer = _executor_best_text(
                scene.get("answer"),
                scene.get("content"),
                scene.get("summary"),
            )
        else:
            answer = _executor_best_text(
                getattr(scene, "answer", ""),
                getattr(scene, "content", ""),
                getattr(scene, "summary", ""),
            )

    if answer:
        if _executor_value_is_empty(getattr(machine_response, "answer", None)):
            machine_response.answer = answer
        if _executor_value_is_empty(getattr(machine_response, "content", None)):
            machine_response.content = answer
        if _executor_value_is_empty(getattr(machine_response, "summary", None)):
            machine_response.summary = answer

        blocks = list(getattr(machine_response, "render_blocks", []) or [])
        if not blocks:
            blocks = [{
                "type": "text",
                "content": answer,
                "renderer": "TextBlock",
                "viewer": "TextBlock",
                "priority": 0,
            }]
        machine_response.render_blocks = blocks

    return machine_response

def _clip_text(value, limit=4000):
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[-limit:]

def _compact_timeline(timeline, max_items=14):
    if not isinstance(timeline, list):
        return []
    if len(timeline) <= max_items:
        return timeline

    head = []
    if timeline and isinstance(timeline[0], dict) and timeline[0].get("role") == "system":
        head = [timeline[0]]
        timeline = timeline[1:]
        max_items = max(1, max_items - 1)

    return head + timeline[-max_items:]

def _compact_memory_bundle(memory_bundle):
    if not isinstance(memory_bundle, dict):
        return memory_bundle

    compacted = {}
    for key, value in memory_bundle.items():
        if isinstance(value, str):
            compacted[key] = _clip_text(value, 3000)
        elif isinstance(value, dict):
            compacted[key] = _compact_memory_bundle(value)
        elif isinstance(value, list):
            compacted[key] = value[-12:]
        else:
            compacted[key] = value
    return compacted

def _compact_conversation_space(conversation_space):
    if not isinstance(conversation_space, dict):
        return conversation_space

    compacted = dict(conversation_space)
    compacted["timeline"] = _compact_timeline(conversation_space.get("timeline", []), max_items=14)
    compacted["dialog"] = _compact_timeline(conversation_space.get("dialog", []), max_items=14)
    compacted["memory_timeline"] = _compact_memory_bundle(conversation_space.get("memory_timeline", {}))
    compacted["memory_summary"] = _clip_text(conversation_space.get("memory_summary", ""), 3000)
    return compacted

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

def _looks_like_formula_text(value):
    if not isinstance(value, str):
        return False

    text = value.strip()
    if not text:
        return False

    compact = text.replace(" ", "")
    if len(compact) > 120:
        return False

    formula_chars = sum(ch in compact for ch in "=^_±×/*√π∑∫²³⁴⁵⁶⁷⁸⁹⁰")
    if "=" in compact and formula_chars >= 1:
        return True

    if re.fullmatch(r"[A-Za-zА-Яа-я0-9\s\+\-\=\^\*\/\(\)\[\]\{\}\.,:;×√π²³⁴⁵⁶⁷⁸⁹⁰]+", text):
        return "=" in text or "^" in text

    return False

def _canonicalize_formula_blocks(machine_response, semantic=None, response_decision=None):
    semantic = semantic or {}
    response_decision = response_decision or {}

    preferred = (
        response_decision.get("preferred_representation")
        or semantic.get("preferred_representation")
        or ""
    )

    render_blocks = list(getattr(machine_response, "render_blocks", []) or [])
    answer = getattr(machine_response, "answer", "") or ""
    content = getattr(machine_response, "content", "") or ""
    summary = getattr(machine_response, "summary", "") or ""

    should_force_formula = (
        preferred == "formula"
        or semantic.get("math_intent")
        or semantic.get("formula_intent")
        or semantic.get("render_intent")
        or "formula" in normalize_text(getattr(machine_response, "goal", "")).lower()
        or "формул" in normalize_text(getattr(machine_response, "goal", "")).lower()
    )

    if not render_blocks:
        candidate = answer or content or summary
        if candidate and (_looks_like_formula_text(candidate) or should_force_formula):
            render_blocks = [{
                "type": "formula",
                "content": candidate.strip() if isinstance(candidate, str) else candidate,
                "renderer": "FormulaBlock",
                "viewer": "FormulaBlock",
                "priority": 100,
            }]
    else:
        normalized = []
        for block in render_blocks:
            if not isinstance(block, dict):
                normalized.append(block)
                continue

            block_type = str(block.get("type", "text") or "text")
            block_content = block.get("content")
            if (
                block_type in ("text", "markdown")
                and (
                    should_force_formula
                    or _looks_like_formula_text(block_content if isinstance(block_content, str) else "")
                    or _looks_like_formula_text(answer)
                    or _looks_like_formula_text(content)
                    or _looks_like_formula_text(summary)
                )
            ):
                block = dict(block)
                block["type"] = "formula"
                block["renderer"] = "FormulaBlock"
                block["viewer"] = "FormulaBlock"
                block.setdefault("priority", 100)
            normalized.append(block)

        render_blocks = normalized

    machine_response.render_blocks = render_blocks
    return machine_response

def track_room(name):
    return

def track_trajectory(name):
    return

def track_modality(name):
    return

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

        "conversation_space": _compact_conversation_space(conversation_space),
        "canonical_space": _compact_conversation_space(conversation_space),

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

def executor_cpu_register_room(report, room_name, **kwargs):
    entry={"room": room_name}
    entry.update(kwargs)
    report.append(entry)
    return report

def _extract_machine_response(result):
    """Stage 1 Executor: preserve Provider semantic fields without collapsing them."""
    if isinstance(result, MachineResponse):
        return result
    if not isinstance(result, dict):
        return None

    mr=result.get("machine_response", result)
    if isinstance(mr, MachineResponse):
        return mr
    if not isinstance(mr, dict):
        return None

    response=MachineResponse()

    for field in vars(response).keys():
        if field in mr:
            try:
                setattr(response, field, mr[field])
            except Exception:
                pass

    if not getattr(response,"answer",None):
        response.answer=mr.get("answer","")
    if not getattr(response,"content",None):
        response.content=mr.get("content","")
    if not getattr(response,"summary",None):
        response.summary=mr.get("summary","")

    return response

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
    
    machine_request = context.get("machine_request")
    if machine_request is None:
        raise RuntimeError("MachineRequest missing from executor context")

    room_results = []
    room_execution_report = []
    machine_response = None

    for room in ROOMS:
        try:
            result = await room.handle(
                user_id=user_id,
                text=text,
                context=machine_request,
                run=run_with_activity,
            )

            if isinstance(result, dict):

                mr = result.get("machine_response")

                if isinstance(mr, dict):
                    pass
                elif isinstance(mr, MachineResponse):
                    pass

            extracted = _extract_machine_response(result)

            if extracted is None and isinstance(result, dict):
                mr = result.get("machine_response")
                if isinstance(mr, dict):
                    extracted = MachineResponse()
                    for k, v in mr.items():
                        try:
                            setattr(extracted, k, v)
                        except Exception:
                            pass

            if extracted is not None:
                room_results.append({
                    "room": getattr(room, "name", "unknown"),
                    "machine_response": extracted,
                })
                executor_cpu_register_room(
                    room_execution_report,
                    getattr(room, "name", "unknown"),
                    status="ok",
                )
                if machine_response is None:
                    machine_response = extracted
                continue

        except Exception as exc:
            room_execution_report.append({"room": getattr(room,"name","unknown"), "status":"error","error":str(exc)})
            continue

    if machine_response is None:
        raise RuntimeError("No MachineResponse produced")

    if not getattr(machine_response, "answer", "") and not getattr(machine_response, "content", "") and not getattr(machine_response, "summary", "") and not list(getattr(machine_response, "render_blocks", []) or []):
        machine_response.answer = "Не удалось сформировать ответ: слишком большой контекст или пустой результат."
        machine_response.content = machine_response.answer
        machine_response.summary = "Пустой результат после обработки запроса."
        machine_response.render_blocks = [{
            "type": "text",
            "content": machine_response.answer,
            "renderer": "TextBlock",
            "viewer": "TextBlock",
            "priority": 0,
        }]

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

    _canonical_answer = getattr(machine_response, "answer", "")
    _canonical_content = getattr(machine_response, "content", "")
    _canonical_summary = getattr(machine_response, "summary", "")

    machine_response = executor_cpu_normalize_answer(machine_response)

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
    reflected_machine_response = machine_response

    registry_result = registry_parent_dispatch(
        machine_request,
        room_results,
    )

    machine_response = reflected_machine_response

    if registry_result is not None:
        for _field in (
            "contributions",
            "registry_diagnostics",
            "artifacts",
            "render_blocks",
            "metadata",
        ):
            try:
                value = getattr(registry_result, _field, None)
                if value not in (None, "", [], {}):
                    setattr(machine_response, _field, value)
            except Exception:
                pass

        for _field in ("answer","content","summary"):
            try:
                current = getattr(machine_response, _field, "")
                incoming = getattr(registry_result, _field, "")
                if (not current) and incoming:
                    setattr(machine_response, _field, incoming)
            except Exception:
                pass

    machine_response = executor_cpu_normalize_answer(machine_response)

    if not getattr(machine_response, "answer", "") and _canonical_answer:
        machine_response.answer = _canonical_answer
    if not getattr(machine_response, "content", "") and _canonical_content:
        machine_response.content = _canonical_content
    if not getattr(machine_response, "summary", "") and _canonical_summary:
        machine_response.summary = _canonical_summary

    if (not list(getattr(machine_response, "render_blocks", []) or [])
        and getattr(machine_response, "answer", "")):
        machine_response.render_blocks=[{
            "type":"text",
            "content":machine_response.answer,
            "renderer":"TextBlock",
            "viewer":"TextBlock",
            "priority":0,
        }]

    executor_cpu_transport_diag('AFTER_REFLECT', machine_response)

    setattr(machine_response, "provider_transport_verified", True)
    setattr(machine_response, "provider_contract_version", "fiber_v3_stage2")

    diagnostics = (
        getattr(machine_response, "contributions", {})
        .get("registry_diagnostics", {})
    )

    if False:
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

def is_canonical_scene(scene):
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
    """Stage 3: transport only.

    Executor never creates, restores or synthesizes render_blocks.
    Provider is the single owner of render_blocks.
    """

    render_blocks = list(
        getattr(machine_response, "render_blocks", []) or []
    )

    machine_response.render_blocks = render_blocks
    return machine_response

def executor_cpu_attach_artifact_payloads(machine_response):
    artifacts = list(getattr(machine_response, "artifacts", []) or [])
    render_blocks = list(getattr(machine_response, "render_blocks", []) or [])

    artifact_index = {}

    for artifact in artifacts:
        artifact_type = (
            getattr(artifact, "artifact_type", None)
            or getattr(artifact, "type", None)
        )
        payload = getattr(artifact, "data", None)
        if artifact_type and payload is not None:
            artifact_index[artifact_type] = payload

    for block in render_blocks:
        if not isinstance(block, dict):
            continue

        provider_payload = artifact_index.get(block.get("type"))
        if provider_payload is None:
            continue

        block["payload"] = provider_payload
        block["provider_payload"] = True
        block["canonical_provider_payload"] = True
        block["executor_generated"] = False

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

EXECUTOR_ROUTE_VERSION="fiber_scene_v2"
EXECUTOR_LEGACY_TEXT_ROUTE=False

EXECUTOR_FIBER_CANONICAL = True

EXECUTOR_CPU_ENABLED = True

APRIL_CPU_TRACE_ENABLED=False
CPU_EXECUTION_JOURNAL=[]

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

EXECUTOR_CPU_TRACE = []
EXECUTOR_CPU_SESSION = {}

def executor_cpu_checkpoint(stage, **payload):
    return payload.get("machine_response")

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
    """Stage 2: preserve semantic fields; only fill missing canonical values."""
    answer=getattr(machine_response,"answer",None)
    content=getattr(machine_response,"content",None)
    summary=getattr(machine_response,"summary",None)

    fallback=None
    if not (answer or content or summary):
        for block in list(getattr(machine_response,"render_blocks",[]) or []):
            if isinstance(block,dict):
                fallback=block.get("content") or block.get("text")
                if fallback:
                    break

    if fallback:
        if not answer:
            machine_response.answer=fallback
        if not content:
            machine_response.content=fallback
        if not summary:
            machine_response.summary=fallback

    return machine_response

def executor_cpu_build_presentation_plan(machine_response):
    """Stage 2: determine presentation from artifact types only."""
    plan = {
        "representation": "text",
        "blocks": [],
        "artifact_types": [],
        "provider_owned": True,
    }

    artifacts = list(getattr(machine_response, "artifacts", []) or [])

    for artifact in artifacts:
        artifact_type = (
            getattr(artifact, "artifact_type", None)
            or getattr(artifact, "type", None)
            or "text"
        )

        if artifact_type not in plan["artifact_types"]:
            plan["artifact_types"].append(artifact_type)

        if artifact_type not in plan["blocks"]:
            plan["blocks"].append(artifact_type)

    priority = [
        "graph",
        "table",
        "formula",
        "gallery",
        "diagram",
        "link",
        "code",
        "text",
    ]

    for rep in priority:
        if rep in plan["artifact_types"]:
            plan["representation"] = rep
            break

    machine_response.executor_presentation_plan = plan
    return machine_response

def executor_cpu_transport_verification(machine_response):
    """
    Final verification before Scene pipeline.
    Preserves the single canonical MachineResponse.
    """
    report = {
        "verified": True,
        "single_route": True,
        "provider_reentry": False,
        "openai_reentry": False,
        "render_blocks": len(getattr(machine_response, "render_blocks", []) or []),
        "artifacts": len(getattr(machine_response, "artifacts", []) or []),
    }

    for field in ("answer", "content", "summary"):
        if getattr(machine_response, field, None) is None:
            setattr(machine_response, field, "")

    machine_response.executor_transport_verification = report
    return machine_response

def executor_cpu_memory_fusion(machine_response):
    """
    Fuse dynamic memory, visual memory and dialog trajectory into
    one canonical executor state. No new routes are created.
    """
    cs=getattr(machine_response,"conversation_space",{}) or {}

    dialog_vector={
        "timeline": cs.get("timeline",[]),
        "memory_timeline": cs.get("memory_timeline",{}),
        "visual_summary": cs.get("visual_summary",{}),
        "active_visual_scene": cs.get("active_visual_scene",{}),
        "goal_hierarchy": cs.get("goal_hierarchy",{}),
        "focus": cs.get("focus",{}),
        "semantic": cs.get("semantic",{}),
        "response_decision": cs.get("response_decision",{}),
        "vector_version":"executor_test5",
        "single_route":True,
    }

    setattr(machine_response,"dialog_vector",dialog_vector)

    plan=getattr(machine_response,"executor_presentation_plan",{}) or {}
    plan["dialog_vector"]=True
    plan["memory_fusion"]=True
    plan["visual_continuity"]=bool(dialog_vector["active_visual_scene"])
    plan["dynamic_memory"]=bool(dialog_vector["memory_timeline"])
    machine_response.executor_presentation_plan=plan
    return machine_response

def executor_cpu_scene_intelligence(machine_response):
    """
    Final executor intelligence pass.
    Combines dialog vector, memory fusion and scene planning
    without changing the canonical Fiber route.
    """
    dialog_vector=getattr(machine_response,"dialog_vector",{}) or {}
    planner=getattr(machine_response,"executor_presentation_plan",{}) or {}

    scene_profile={
        "dialog_continuity": bool(dialog_vector.get("timeline")),
        "memory_continuity": bool(dialog_vector.get("memory_timeline")),
        "visual_continuity": bool(dialog_vector.get("active_visual_scene")),
        "goal_continuity": bool(dialog_vector.get("goal_hierarchy")),
        "focus_continuity": bool(dialog_vector.get("focus")),
        "scene_strategy":"single_scene_contract",
        "fiber_route":"single",
        "executor_generated":True,
    }

    planner["scene_profile"]=scene_profile
    planner["scene_intelligence"]=True
    machine_response.executor_presentation_plan=planner
    machine_response.executor_scene_profile=scene_profile
    return machine_response

def executor_cpu_synthetic_verification(machine_response):
    """
    Detect internally inconsistent executor state without
    changing the canonical Fiber route.
    """
    report = {
        "single_route": True,
        "synthetic_detected": False,
        "issues": [],
    }

    dv = getattr(machine_response, "dialog_vector", {}) or {}
    plan = getattr(machine_response, "executor_presentation_plan", {}) or {}

    if plan.get("memory_fusion") and not dv:
        report["synthetic_detected"] = True
        report["issues"].append("presentation_plan references dialog_vector but dialog_vector is missing")

    rb = list(getattr(machine_response, "render_blocks", []) or [])
    if not rb:
        report["synthetic_detected"] = True
        report["issues"].append("no render_blocks before SceneContract")

    ans = getattr(machine_response, "answer", "") or ""
    if not ans:
        report["synthetic_detected"] = True
        report["issues"].append("empty canonical answer")

    machine_response.executor_synthetic_report = report
    return machine_response

def executor_cpu_user_alignment(machine_response):
    """Strengthen planning using the current conversation space.
    Does not introduce new routes or objects.
    """
    cs = getattr(machine_response, "conversation_space", {}) or {}
    planner = getattr(machine_response, "executor_presentation_plan", {}) or {}

    alignment = {
        "user_goal": cs.get("response_decision", {}).get("goal"),
        "focus": cs.get("focus", {}),
        "last_user_turn": cs.get("last_user_turn"),
        "dialog_depth": len(cs.get("timeline", [])),
        "memory_available": bool(cs.get("memory_timeline")),
        "visual_available": bool(cs.get("active_visual_scene")),
        "single_route": True,
        "executor_generated": True,
    }

    planner["user_alignment"] = alignment
    planner["adaptive"] = True
    machine_response.executor_presentation_plan = planner
    machine_response.executor_user_alignment = alignment
    return machine_response

def executor_cpu_pipeline(machine_response):
    machine_response = executor_cpu_transport_verification(machine_response)
    machine_response = executor_cpu_memory_fusion(machine_response)
    machine_response = executor_cpu_scene_intelligence(machine_response)
    machine_response = executor_cpu_user_alignment(machine_response)
    machine_response = executor_cpu_synthetic_verification(machine_response)
    machine_response = executor_cpu_materialize_blocks(machine_response)
    machine_response = _canonicalize_formula_blocks(machine_response)
    machine_response = executor_cpu_attach_artifact_payloads(machine_response)
    machine_response = executor_cpu_normalize_answer(machine_response)
    return machine_response

def executor_cpu_finalize(machine_response):
    """
    Canonical final CPU pass.
    Executes the unified pipeline once and removes transient
    executor fields before SceneContract generation.
    """
    machine_response = executor_cpu_pipeline(machine_response)

    transient = [
        "executor_cognitive_context",
        "executor_scene_profile",
        "executor_user_alignment",
    ]
    for name in transient:
        if hasattr(machine_response, name):
            try:
                delattr(machine_response, name)
            except Exception:
                pass

    setattr(machine_response, "executor_finalized", True)
    setattr(machine_response, "executor_pipeline_version", "TEST10_FINAL")
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
    machine_response = executor_cpu_memory_fusion(machine_response)
    machine_response = executor_cpu_scene_intelligence(machine_response)
    machine_response = executor_cpu_user_alignment(machine_response)
    machine_response = executor_cpu_synthetic_verification(machine_response)
    machine_response = executor_cpu_materialize_blocks(machine_response)
    machine_response = _canonicalize_formula_blocks(
        machine_response,
        semantic=semantic,
        response_decision=response_decision,
    )
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

def executor_cpu_transport_diag(stage, machine_response=None, scene_contract=None):
    try:
        if machine_response is not None:
            print(
                f"[EXECUTOR][{stage}] "
                f"answer={len(getattr(machine_response,'answer','') or '')} "
                f"content={len(getattr(machine_response,'content','') or '')} "
                f"summary={len(getattr(machine_response,'summary','') or '')} "
                f"blocks={len(getattr(machine_response,'render_blocks',[]) or [])} "
                f"artifacts={len(getattr(machine_response,'artifacts',[]) or [])}"
            )
        if scene_contract is not None:
            blocks = getattr(scene_contract, 'render_blocks', None)
            if blocks is None and isinstance(scene_contract, dict):
                blocks = scene_contract.get('render_blocks', [])
            print(f"[EXECUTOR][{stage}] scene_contract_blocks={len(blocks or [])}")
    except Exception as exc:
        print(f"[EXECUTOR][{stage}] diag_error={exc}")

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
            value.setdefault("provider_original_answer", getattr(machine_response, "provider_original_answer", ""))
            value.setdefault("provider_original_content", getattr(machine_response, "provider_original_content", ""))

        if field == "render_blocks":
            scene_value = getattr(scene_contract, field, None)
            if _executor_value_is_empty(value) and not _executor_value_is_empty(scene_value):
                value = scene_value
            elif _executor_value_is_empty(value) and hasattr(scene, field):
                scene_value = getattr(scene, field)
                if not _executor_value_is_empty(scene_value):
                    value = scene_value

        if _executor_value_is_empty(value) and hasattr(scene, field):
            scene_value = getattr(scene, field)
            if not _executor_value_is_empty(scene_value):
                value = scene_value

        if field == "render_blocks" and _executor_value_is_empty(value):
            value = getattr(scene_contract, field, value)

        try:
            setattr(scene_contract, field, value)
        except Exception:
            if isinstance(scene_contract, dict):
                scene_contract[field] = value

    return scene_contract


def executor_cpu_scene_pipeline(machine_response):
    executor_cpu_transport_diag('BEFORE_BUILD_MACHINE_SCENE', machine_response)
    machine_response = executor_cpu_normalize_answer(machine_response)

    scene = build_machine_scene(machine_response)
    try:
        setattr(scene, "conversation_space",
                getattr(machine_response, "conversation_space", None))
    except Exception:
        pass

    conversation_space = getattr(machine_response, "conversation_space", {}) or {}

    blocks = list(getattr(scene, "render_blocks", None) or getattr(scene, "blocks", []) or [])
    if not blocks:
        blocks = list(getattr(machine_response, "render_blocks", []) or [])

    try:
        setattr(scene, "timeline", conversation_space.get("timeline", []))
        setattr(scene, "last_user_turn", conversation_space.get("last_user_turn"))
        setattr(scene, "last_april_turn", conversation_space.get("last_april_turn"))
        setattr(scene, "active_goal", conversation_space.get("response_decision", {}).get("goal"))
    except Exception:
        pass

    current_turn = conversation_space.get("current_turn", {})
    april_turn = current_turn.get("april") or {}

    scene_contract = build_scene_contract(scene)
    executor_cpu_transport_diag('AFTER_BUILD_SCENE_CONTRACT', machine_response, scene_contract)

    scene_contract = executor_cpu_sync_scene_contract(scene_contract, machine_response, scene)

    # Final safety pass: keep the richest text before returning the scene packet.
    machine_response = _executor_preserve_canonical_text(
        machine_response,
        scene_contract=scene_contract,
        scene=scene,
    )
    scene_contract = executor_cpu_sync_scene_contract(scene_contract, machine_response, scene)

    # If the scene still did not materialize blocks, seed a text block from the canonical answer.
    if not blocks:
        blocks = list(getattr(scene_contract, "render_blocks", []) or [])
    if not blocks:
        blocks = list(getattr(machine_response, "render_blocks", []) or [])
    if not blocks:
        best_text = _executor_best_text(
            getattr(machine_response, "answer", ""),
            getattr(machine_response, "content", ""),
            getattr(machine_response, "summary", ""),
            getattr(scene_contract, "answer", "") if not isinstance(scene_contract, dict) else scene_contract.get("answer"),
            getattr(scene_contract, "content", "") if not isinstance(scene_contract, dict) else scene_contract.get("content"),
            getattr(scene_contract, "summary", "") if not isinstance(scene_contract, dict) else scene_contract.get("summary"),
        )
        if best_text:
            blocks = [{
                "type": "text",
                "content": best_text,
                "renderer": "TextBlock",
                "viewer": "TextBlock",
                "priority": 0,
            }]

    try:
        if isinstance(scene_contract, dict):
            scene_contract.setdefault("answer", getattr(machine_response, "answer", ""))
            scene_contract.setdefault("content", getattr(machine_response, "content", ""))
            scene_contract.setdefault("summary", getattr(machine_response, "summary", ""))
            scene_contract.setdefault("render_blocks", blocks)
        else:
            setattr(scene_contract, "answer", getattr(machine_response, "answer", ""))
            setattr(scene_contract, "content", getattr(machine_response, "content", ""))
            setattr(scene_contract, "summary", getattr(machine_response, "summary", ""))
            setattr(scene_contract, "render_blocks", blocks)
    except Exception:
        pass

    executor_cpu_transport_diag('AFTER_SYNC_SCENE_CONTRACT', machine_response, scene_contract)

    return {
        "canonical_space": True,
        "machine_response": machine_response,
        "machine_scene": scene,
        "answer": getattr(machine_response, "answer", None),
        "content": getattr(machine_response, "content", None),
        "summary": getattr(machine_response, "summary", None),
        "render_blocks": blocks,
        "scene_contract": scene_contract,  # canonical factory contract
        "scene_runtime": {
            "conversation_space": conversation_space,
            "current_turn": conversation_space.get("current_turn"),
            "timeline": conversation_space.get("timeline", []),
            "last_user_turn": conversation_space.get("last_user_turn"),
            "last_april_turn": conversation_space.get("last_april_turn"),
            "machine_scene": scene,
            "render_blocks": blocks,
            "answer": getattr(machine_response, "answer", None),
            "content": getattr(machine_response, "content", None),
            "summary": getattr(machine_response, "summary", None),
            "modalities": conversation_space.get("modalities", {}),
            "dialog": conversation_space.get("dialog", []),
            "goal_hierarchy": conversation_space.get("goal_hierarchy", {}),
            "focus": conversation_space.get("focus", {}),
        },
    }


def executor_cpu_finalize_transport(machine_response):
    executor_cpu_transport_diag('TRANSPORT_ENTRY', machine_response)
    machine_response = executor_cpu_normalize_answer(machine_response)
    scene = executor_cpu_scene_pipeline(machine_response)
    conversation_space = getattr(machine_response, "conversation_space", None)

    executor_cpu_transport_diag('FINAL_TRANSPORT', machine_response, scene.get('scene_contract'))

    scene_contract = scene.get("scene_contract")
    scene_answer = _executor_best_text(
        getattr(machine_response, "answer", ""),
        scene.get("answer"),
        getattr(scene_contract, "answer", "") if scene_contract is not None and not isinstance(scene_contract, dict) else (scene_contract or {}).get("answer") if isinstance(scene_contract, dict) else "",
        getattr(machine_response, "provider_original_answer", ""),
    )
    scene_content = _executor_best_text(
        getattr(machine_response, "content", ""),
        scene.get("content"),
        getattr(scene_contract, "content", "") if scene_contract is not None and not isinstance(scene_contract, dict) else (scene_contract or {}).get("content") if isinstance(scene_contract, dict) else "",
        scene_answer,
    )
    scene_summary = _executor_best_text(
        getattr(machine_response, "summary", ""),
        scene.get("summary"),
        getattr(scene_contract, "summary", "") if scene_contract is not None and not isinstance(scene_contract, dict) else (scene_contract or {}).get("summary") if isinstance(scene_contract, dict) else "",
        scene_answer,
    )

    if not scene_answer:
        scene_answer = getattr(machine_response, "answer", None)
    if not scene_content:
        scene_content = getattr(machine_response, "content", None)
    if not scene_summary:
        scene_summary = getattr(machine_response, "summary", None)

    return {
        "transport_contract": "scene_first",
        "provider_contract": "fiber_v3",
        "conversation_space": conversation_space,
        "machine_response": machine_response,
        "machine_scene": scene.get("machine_scene"),
        "scene_contract": scene_contract,
        "current_turn": conversation_space.get("current_turn") if conversation_space else None,
        "answer": scene_answer,
        "content": scene_content,
        "summary": scene_summary,
        "render_blocks": scene.get("render_blocks", []),
    }


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

def executor_cpu_sync_factory_bridge(factory_register):
    """Bind CPU and Artifact Factory into one execution route."""
    executor_cpu_register_factory_hooks(factory_register)
    cpu_trace_success("FACTORY_BRIDGE_REGISTERED",{
        "single_route":True
    })

def executor_provider_stage_log(stage, payload=None):
    try:
        info={}
        if isinstance(payload, dict):
            for k,v in payload.items():
                if isinstance(v,str):
                    info[k]=f"<str:{len(v)}>"
                elif isinstance(v,(list,dict)):
                    info[k]=f"<{type(v).__name__}:{len(v)}>"
                else:
                    info[k]=v
        else:
            info=payload
        print(f"[EXECUTOR:{stage}] {info}")
    except Exception:
        pass

async def execute(
    user_id,
    chat_id=None,
    text="",
    run_with_activity=None,  # legacy compatibility, scheduled for removal
    **kwargs,
):
    chat_id = chat_id or user_id
    cpu_trace_begin("EXECUTE", {"user_id": user_id})
    state = get_state(user_id)
    semantic = semantic_analyze(
        text=text,
        state=state,
        history=state.get("dialog", []),
        active_flow=state.get("active_flow", {}),
        dialog_state=state.get("scene_state", {}),
    )
    update_dialog_context(user_id, semantic)
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
    conversation_space = context.get("conversation_space") or {}
    current_turn = conversation_space.get("current_turn", {})

    if "factory_hook_registration" in kwargs:
        executor_cpu_sync_factory_bridge(kwargs["factory_hook_registration"])

    machine_memory = {
        "memory_summary": _clip_text(state.get("memory_summary"), 3000),
        "active_flow": state.get("active_flow"),
        "memory_timeline": _compact_memory_bundle(conversation_space.get("memory_timeline", {})),
        "goal_hierarchy": state.get("goal_hierarchy", {}),
        "focus": state.get("focus", state.get("focus_state", {})),
        "visual_summary": _compact_memory_bundle(conversation_space.get("visual_summary", {})),
    }

    machine_conversation = {
        "timeline": _compact_timeline(conversation_space.get("timeline", []), max_items=14),
        "last_user_turn": current_turn.get("user", {}).get("text", text),
        "last_april_turn": conversation_space.get("last_april_turn"),
        "active_visual_scene": conversation_space.get("active_visual_scene", {}),
    }

    executor_provider_stage_log("PROVIDER_REQUEST", {"goal":text,"timeline":len(machine_conversation.get("timeline",[])),"memory":len(machine_memory)})
    context["machine_request"] = MachineRequest(
        goal=current_turn.get("user", {}).get("text", text),
        intent=semantic,
        memory=machine_memory,
        visual_context={
            "visual_reference": visual_reference,
            "active_visual_scene": conversation_space.get("active_visual_scene", {}),
            "visual_summary": conversation_space.get("visual_summary", {}),
        },
        conversation=machine_conversation,
    )
    context["executor_state"] = state
    context["executor_conversation_space"] = conversation_space

    setattr(context["machine_request"], "current_turn", current_turn)

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
    executor_provider_stage_log("PROVIDER_RESPONSE", {"has_machine_response":isinstance(result,dict) and "machine_response" in result,"has_scene_contract":isinstance(result,dict) and "scene_contract" in result,"render_blocks":len((result.get("render_blocks") if isinstance(result,dict) else []) or [])})
    result = executor_cpu_factory_bridge(result)
    result = executor_cpu_gateway_dispatch(result)
    cpu_trace_success("EXECUTE")
    return result
