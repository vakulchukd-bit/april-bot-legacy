
# =====================================================
# APRIL EXECUTOR SUPER - CANONICAL SINGLE ROUTE
# =====================================================

from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from blocks.semantic_core import analyze as semantic_analyze
from blocks.reasoning_state import build_reasoning_state
from blocks.cognitive_core import analyze_cognition
from blocks.response_decision import build_response_decision
from blocks.visual_reference_system import build_visual_reference
from blocks.state_manager import (
    get_state,
    build_visual_memory_bridge,
    update_dialog_context,
)
from blocks.rooms_registry import ROOMS, registry_parent_dispatch
from blocks.C_ARTIFACT_CONTRACT import (
    MachineRequest,
    MachineResponse,
    MachineScene,
    UniversalArtifactContract,
    build_machine_scene,
    build_scene_contract,
)
from blocks.provider_router import generate_text
from blocks.presentation_formatter import format_response_presentation  # noqa: F401
from blocks.energy_manager import get_energy  # noqa: F401
from blocks.experience import update_experience, load_experience  # noqa: F401

# =====================================================
# ROUTE FLAGS
# =====================================================

TASK_CHANNEL = {
    "type": "machine_task_channel",
    "isolated": True,
    "human_access": False,
}

RESPONSE_CHANNEL = {
    "type": "machine_response_channel",
    "isolated": True,
    "human_access": False,
}

EXECUTOR_ROUTE_VERSION = "super_single_canonical_route_v1"
PROCESSOR_APRIL_NAME = "Процессор April"
PROCESSOR_APRIL_VERSION = "april_super_processor_v1"
PROCESSOR_APRIL_ROUTE = "single_canonical_stream"
PROCESSOR_APRIL_PASSES = ("pass1_canonical", "pass2_enrich", "pass3_scene")
PROCESSOR_APRIL_NO_FALLBACKS = True

EXECUTOR_CPU_ENABLED = True
EXECUTOR_LEGACY_TEXT_ROUTE = False
EXECUTOR_FIBER_CANONICAL = True
EXECUTOR_SEQUENTIAL_CANONICAL_ENRICHMENT = True
APRIL_CPU_TRACE_ENABLED = False

FOLLOWUP_CONTEXT_CHAR_LIMIT = 280
FOLLOWUP_CONTEXT_WORD_LIMIT = 5

CPU_EXECUTION_JOURNAL: list[dict[str, Any]] = []
CPU_STAGE_REGISTRY: list[dict[str, Any]] = []
EXECUTOR_CPU_SESSION: Dict[str, Any] = {}
EXECUTOR_CPU_OBJECTS = {
    "machine_request": {},
    "machine_response": {},
    "machine_scene": {},
}

# =====================================================
# SMALL HELPERS
# =====================================================

def normalize_text(text: Any) -> str:
    return (text or "").strip() if isinstance(text, str) else str(text or "").strip()


def _executor_value_is_empty(value: Any) -> bool:
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


def _executor_best_text(*values: Any) -> str:
    for value in values:
        if _executor_value_is_empty(value):
            continue
        text = value.strip() if isinstance(value, str) else str(value).strip()
        if text:
            return text
    return ""


def _clip_text(value: Any, limit: int = 4000) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[-limit:]


def _compact_timeline(timeline: Any, max_items: int = 14) -> list:
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


def _compact_memory_bundle(memory_bundle: Any):
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


def _compact_conversation_space(conversation_space: Any):
    if not isinstance(conversation_space, dict):
        return conversation_space
    compacted = dict(conversation_space)
    compacted["timeline"] = _compact_timeline(conversation_space.get("timeline", []), max_items=14)
    compacted["dialog"] = _compact_timeline(conversation_space.get("dialog", []), max_items=14)
    compacted["memory_timeline"] = _compact_memory_bundle(conversation_space.get("memory_timeline", {}))
    compacted["memory_summary"] = _clip_text(conversation_space.get("memory_summary", ""), 3000)
    return compacted


def _looks_like_formula_text(value: Any) -> bool:
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


def _executor_looks_like_internal_room_payload(text: Any) -> bool:
    if not isinstance(text, str):
        return False
    payload = text.lower()
    return (
        "domain" in payload
        and "topic" in payload
        and "capabilities" in payload
        and ("engineering" in payload or "analysis" in payload)
    )


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def track_room(name: str):
    return


def track_trajectory(name: str):
    return


def track_modality(name: str):
    return


# =====================================================
# TRACE / DIAGNOSTICS
# =====================================================

def executor_provider_stage_log(stage: str, payload: Any = None) -> None:
    try:
        if isinstance(payload, dict):
            info = {}
            for k, v in payload.items():
                if isinstance(v, str):
                    info[k] = f"<str:{len(v)}>"
                elif isinstance(v, (list, dict)):
                    info[k] = f"<{type(v).__name__}:{len(v)}>"
                else:
                    info[k] = v
        else:
            info = payload
        print(f"[EXECUTOR:{stage}] {info}")
    except Exception:
        pass


def cpu_stage_record(stage: str, status: str, details: Optional[dict] = None):
    entry = {
        "stage": stage,
        "status": status,
        "details": details or {},
        "timestamp": time.time(),
    }
    CPU_STAGE_REGISTRY.append(entry)
    return entry


def cpu_stage_snapshot():
    return list(CPU_STAGE_REGISTRY)


def cpu_trace_begin(stage: str, payload: Optional[dict] = None):
    if not APRIL_CPU_TRACE_ENABLED:
        return
    cpu_stage_record(stage, "BEGIN", payload or {})
    CPU_EXECUTION_JOURNAL.append({"stage": stage, "status": "BEGIN", "payload": payload or {}, "timestamp": time.time()})


def cpu_trace_success(stage: str, payload: Optional[dict] = None):
    if not APRIL_CPU_TRACE_ENABLED:
        return
    cpu_stage_record(stage, "SUCCESS", payload or {})
    CPU_EXECUTION_JOURNAL.append({"stage": stage, "status": "SUCCESS", "payload": payload or {}, "timestamp": time.time()})


def cpu_trace_error(stage: str, error: Any):
    if not APRIL_CPU_TRACE_ENABLED:
        return
    cpu_stage_record(stage, "ERROR", {"error": str(error)})
    CPU_EXECUTION_JOURNAL.append({"stage": stage, "status": "ERROR", "error": str(error), "timestamp": time.time()})


def cpu_execution_journal():
    return list(CPU_EXECUTION_JOURNAL)


def executor_cpu_mark_object(name: str, obj: Any, owner: str):
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


# =====================================================
# PAYLOAD MATERIALIZATION
# =====================================================

def _executor_payload_to_mapping(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value

    mapping: Dict[str, Any] = {}
    try:
        if hasattr(value, "__dict__"):
            mapping.update({k: v for k, v in vars(value).items() if not k.startswith("_")})
    except Exception:
        pass

    canonical_fields = (
        "answer", "content", "summary", "response", "explanation", "text",
        "message", "output", "output_text", "data",
        "scene", "artifacts", "render_blocks", "scene_plan", "render_priority", "metadata",
        "confidence", "provider", "provider_contract", "transport_contract",
        "provider_original_answer", "provider_original_content", "processor_input",
        "provider_source_request", "scene_contract", "scene_runtime", "conversation_space",
        "current_turn", "timeline", "dialog", "goal", "goal_hierarchy", "focus",
        "visual_reference", "visual_summary", "active_visual_scene",
        "executor_decision", "executor_presentation_plan", "executor_scene_profile",
        "provider_reference_context", "second_circle_context",
        "machine_response", "provider_response", "provider_payload", "payload",
        "result", "response_data", "contract",
    )
    for field in canonical_fields:
        try:
            if hasattr(value, field):
                mapping[field] = getattr(value, field)
        except Exception:
            continue
    return mapping


def _executor_has_meaningful_payload(machine_response: Any) -> bool:
    if machine_response is None:
        return False
    if isinstance(machine_response, MachineResponse):
        return bool(
            _executor_best_text(
                getattr(machine_response, "answer", ""),
                getattr(machine_response, "content", ""),
                getattr(machine_response, "summary", ""),
                getattr(machine_response, "response", ""),
                getattr(machine_response, "explanation", ""),
            )
            or list(getattr(machine_response, "render_blocks", []) or [])
            or list(getattr(machine_response, "artifacts", []) or [])
            or getattr(machine_response, "scene", None) not in (None, {}, [])
        )
    if isinstance(machine_response, dict):
        return bool(
            _executor_best_text(
                machine_response.get("answer"),
                machine_response.get("content"),
                machine_response.get("summary"),
                machine_response.get("response"),
                machine_response.get("explanation"),
                machine_response.get("text"),
                machine_response.get("message"),
                machine_response.get("output"),
                machine_response.get("output_text"),
            )
            or list(machine_response.get("render_blocks", []) or [])
            or list(machine_response.get("artifacts", []) or [])
            or machine_response.get("scene") not in (None, {}, [])
        )
    return bool(_executor_best_text(getattr(machine_response, "answer", ""), getattr(machine_response, "content", ""), getattr(machine_response, "summary", "")))


def _executor_block_signature(block: Any) -> tuple:
    if not isinstance(block, dict):
        return ("raw", type(block).__name__, _clip_text(str(block), 500))
    payload = block.get("payload")
    if isinstance(payload, (dict, list, tuple, set)):
        payload_sig = type(payload).__name__
    else:
        payload_sig = _clip_text(payload, 200)
    return (
        block.get("type"),
        block.get("signal"),
        block.get("renderer"),
        block.get("viewer"),
        block.get("label"),
        _clip_text(block.get("content"), 500),
        payload_sig,
        block.get("source_room"),
    )


def _executor_artifact_signature(artifact: Any) -> tuple:
    mapping = _executor_payload_to_mapping(artifact)
    if mapping:
        return (
            mapping.get("artifact_id") or mapping.get("id"),
            mapping.get("artifact_type") or mapping.get("type"),
            _clip_text(mapping.get("content"), 500),
            _clip_text(mapping.get("summary"), 300),
        )
    return ("raw", type(artifact).__name__, _clip_text(str(artifact), 500))


def _executor_room_name_from_item(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    return normalize_text(
        item.get("room")
        or item.get("room_name")
        or item.get("source_room")
        or item.get("name")
        or item.get("source")
    ).lower()


def _executor_is_canonical_room(room_name: str, room: Any = None) -> bool:
    room_name = normalize_text(room_name).lower()
    if room_name == "text":
        return True
    if room is not None:
        try:
            if normalize_text(getattr(room, "name", "")).lower() == "text":
                return True
            if normalize_text(getattr(room, "room_type", "")).lower() == "dialog":
                return True
        except Exception:
            pass
    return False


def _executor_materialize_machine_response(envelope: Any) -> Optional[MachineResponse]:
    """
    Direct unwrapping only. No nested search, no recovery tree scan, no parse fallback.
    """
    if envelope is None:
        return None
    if isinstance(envelope, MachineResponse):
        return envelope

    if isinstance(envelope, dict):
        nested = envelope.get("machine_response")
        if isinstance(nested, MachineResponse):
            return nested
        if isinstance(nested, dict):
            return _executor_payload_from_mapping_direct(nested)

        response = _executor_payload_from_mapping_direct(envelope)
        if _executor_has_meaningful_payload(response):
            return response

    if hasattr(envelope, "__dict__"):
        try:
            mapping = _executor_payload_to_mapping(envelope)
            response = _executor_payload_from_mapping_direct(mapping)
            if _executor_has_meaningful_payload(response):
                return response
        except Exception:
            pass

    return None


def _executor_payload_from_mapping_direct(mapping: Dict[str, Any]) -> MachineResponse:
    response = MachineResponse()
    if not isinstance(mapping, dict):
        return response

    direct_fields = (
        "answer", "content", "summary", "response", "explanation", "text",
        "message", "output", "output_text", "data", "scene", "artifacts",
        "render_blocks", "scene_plan", "render_priority", "metadata",
        "confidence", "provider", "provider_contract", "transport_contract",
        "provider_original_answer", "provider_original_content", "processor_input",
        "provider_source_request", "scene_contract", "scene_runtime", "conversation_space",
        "current_turn", "timeline", "dialog", "goal", "goal_hierarchy", "focus",
        "visual_reference", "visual_summary", "active_visual_scene",
        "executor_decision", "executor_presentation_plan", "executor_scene_profile",
        "provider_reference_context", "second_circle_context",
        "machine_response", "provider_response", "provider_payload", "payload",
        "result", "response_data", "contract",
    )
    for field in direct_fields:
        if field in mapping:
            try:
                setattr(response, field, mapping[field])
            except Exception:
                pass

    answer = _executor_best_text(
        mapping.get("answer"),
        mapping.get("content"),
        mapping.get("summary"),
        mapping.get("response"),
        mapping.get("explanation"),
        mapping.get("text"),
        mapping.get("message"),
        mapping.get("output"),
        mapping.get("output_text"),
        mapping.get("data"),
        mapping.get("provider_original_answer"),
        mapping.get("provider_original_content"),
    )
    if answer:
        response.answer = answer
    if _executor_value_is_empty(getattr(response, "content", None)) and answer:
        response.content = answer
    if _executor_value_is_empty(getattr(response, "summary", None)) and answer:
        response.summary = answer

    return response


def _extract_machine_response(result: Any):
    """
    Single route extraction only.
    """
    materialized = _executor_materialize_machine_response(result)
    if materialized is not None and _executor_has_meaningful_payload(materialized):
        return materialized
    return None


def _executor_response_score(value: Any) -> int:
    mapping = _executor_payload_to_mapping(value)
    if not isinstance(mapping, dict):
        return 0

    answer = _executor_best_text(mapping.get("answer", ""))
    content = _executor_best_text(mapping.get("content", ""))
    summary = _executor_best_text(mapping.get("summary", ""))
    response = _executor_best_text(mapping.get("response", ""))
    blocks = list(mapping.get("render_blocks", []) or [])
    artifacts = list(mapping.get("artifacts", []) or [])
    scene = mapping.get("scene", None)

    score = (
        len(answer) * 4
        + len(content) * 3
        + len(summary) * 2
        + len(response) * 2
        + len(blocks) * 150
        + len(artifacts) * 100
    )

    if scene not in (None, {}, []):
        score += 50
    if answer and content and summary:
        score += 40
    if any(key in mapping for key in ("provider_original_answer", "provider_original_content", "provider_source_request", "processor_input")):
        score += 20
    return score


# =====================================================
# CONVERSATION / CONTEXT
# =====================================================

def _executor_extract_turn_text(turn: Any, limit: int = 220) -> str:
    if not isinstance(turn, dict):
        return ""
    for key in ("summary", "content", "text", "answer", "response"):
        value = turn.get(key)
        if value:
            return _clip_text(value, limit)
    for nested_key in ("user", "april"):
        nested = turn.get(nested_key)
        if isinstance(nested, dict):
            extracted = _executor_extract_turn_text(nested, limit=limit)
            if extracted:
                return extracted
    return ""


def _executor_last_turn_text(dialog: Any, role: str, limit: int = 220) -> str:
    if not isinstance(dialog, list):
        return ""
    role = (role or "").strip().lower()
    for item in reversed(dialog):
        if not isinstance(item, dict):
            continue
        item_role = str(item.get("role") or item.get("speaker") or item.get("source") or "").strip().lower()
        if role and item_role != role:
            continue
        extracted = _executor_extract_turn_text(item, limit=limit)
        if extracted:
            return extracted
    return ""


def _executor_reference_context_is_needed(text: str, semantic: dict, cognition: dict, response_decision: dict, state: dict) -> bool:
    normalized = normalize_text(text)
    word_count = len(normalized.split())

    if not normalized:
        return False
    if response_decision.get("should_continue_trajectory"):
        return True
    if response_decision.get("discussion_mode"):
        return True
    if cognition.get("exploration_mode"):
        return True
    for key in ("followup_candidate", "continuation_candidate", "follow_up_candidate"):
        if semantic.get(key):
            return True
    if len(normalized) <= 24 or word_count <= 4:
        return True
    if state.get("dialog") and word_count <= FOLLOWUP_CONTEXT_WORD_LIMIT:
        return True
    return False


def _executor_build_reference_context(text: str, state: dict, semantic: dict, cognition: dict, response_decision: dict) -> str:
    if not _executor_reference_context_is_needed(text, semantic, cognition, response_decision, state):
        return ""

    active_topic = state.get("topic") or semantic.get("topic") or semantic.get("intent") or ""
    focus_source = cognition.get("dynamic_focus") or state.get("focus_state") or state.get("focus") or response_decision.get("goal") or ""
    dialog = state.get("dialog", []) or []
    last_user = _executor_last_turn_text(dialog, "user", limit=180)
    last_april = _executor_last_turn_text(dialog, "assistant", limit=180) or _executor_last_turn_text(dialog, "april", limit=180)

    pieces = []
    if active_topic:
        pieces.append(f"topic: {_clip_text(active_topic, 60)}")
    if focus_source:
        pieces.append(f"focus: {_clip_text(focus_source, 100)}")
    if last_user:
        pieces.append(f"last_user: {_clip_text(last_user, 120)}")
    if last_april:
        pieces.append(f"last_april_summary: {_clip_text(last_april, 120)}")

    if not pieces:
        return ""

    return _clip_text("REFERENCE CONTEXT (for understanding only; do not repeat):\n- " + "\n- ".join(pieces), FOLLOWUP_CONTEXT_CHAR_LIMIT * 2)


def _executor_split_multi_question_parts(text: Any) -> list[str]:
    if not isinstance(text, str):
        text = str(text or "")
    raw = text.strip()
    if not raw:
        return []

    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in raw.split("\n"):
        line = re.sub(r"^\s*[-*•\d]+[\)\.\:-]?\s*", "", line).strip()
        if line:
            lines.append(line)

    if not lines:
        return []

    candidates: list[str] = []
    for line in lines:
        if line.count("?") >= 1:
            parts = [p.strip() for p in re.split(r"(?<=\?)\s+", line) if p.strip()]
            if len(parts) > 1:
                candidates.extend(parts)
            else:
                candidates.append(line)
        elif any(sep in line for sep in (";", " и ", " and ", " then ", " потом ", " затем ")):
            parts = [p.strip() for p in re.split(r"\s*(?:;|\band\b|\bи\b|\bthen\b|\bпотом\b|\bзатем\b)\s*", line, flags=re.IGNORECASE) if p.strip()]
            if len(parts) > 1:
                candidates.extend(parts)
            else:
                candidates.append(line)
        else:
            candidates.append(line)

    cleaned: list[str] = []
    seen = set()
    for part in candidates:
        part = part.strip(" \t-–—")
        if not part:
            continue
        norm = re.sub(r"\s+", " ", part).strip().lower()
        if norm in seen:
            continue
        seen.add(norm)
        cleaned.append(part)

    return cleaned


def _executor_build_canonical_prompt_plan(
    text: Any,
    *,
    semantic: Optional[dict] = None,
    cognition: Optional[dict] = None,
    response_decision: Optional[dict] = None,
) -> dict:
    semantic = semantic or {}
    cognition = cognition or {}
    response_decision = response_decision or {}

    normalized_text = normalize_text(text)
    parts = _executor_split_multi_question_parts(normalized_text)

    if not parts and normalized_text:
        parts = [normalized_text]

    is_multi = len(parts) > 1

    mission = _executor_best_text(
        response_decision.get("goal"),
        semantic.get("intent"),
        semantic.get("topic"),
        normalized_text,
    )
    if not mission:
        mission = normalized_text

    topic = _executor_best_text(
        semantic.get("topic"),
        response_decision.get("goal"),
        cognition.get("dynamic_focus", {}).get("topic") if isinstance(cognition.get("dynamic_focus"), dict) else "",
    )

    tasks = []
    for idx, part in enumerate(parts, start=1):
        task_text = part.strip()
        if not task_text:
            continue
        tasks.append(f"{idx}. {task_text}")

    output_policy = (
        "Answer each task once."
        if is_multi
        else "Answer the request once."
    )

    return {
        "is_multi_question": is_multi,
        "mission": mission,
        "topic": topic,
        "tasks": tasks,
        "output_policy": output_policy,
        "original_text": normalized_text,
        "task_count": len(tasks),
    }


def _executor_format_canonical_prompt(plan: dict) -> str:
    if not isinstance(plan, dict):
        return normalize_text(plan)

    mission = normalize_text(plan.get("mission"))
    topic = normalize_text(plan.get("topic"))
    tasks = [normalize_text(item) for item in (plan.get("tasks") or []) if normalize_text(item)]

    if not mission and not tasks:
        return normalize_text(plan.get("original_text"))

    pieces = []
    if mission:
        pieces.append("MISSION")
        pieces.append(mission)

    if topic and topic.lower() != mission.lower():
        pieces.extend(["", "TOPIC", topic])

    if tasks:
        pieces.extend(["", "TASKS"])
        pieces.extend(tasks)

    pieces.extend([
        "",
        "OUTPUT",
        plan.get("output_policy") or "Answer once.",
        "Do not repeat the same fact in multiple sections.",
        "Keep each task answer distinct and in order.",
    ])

    return "\n".join(pieces).strip()


def build_conversation_space(state: dict, semantic: dict, cognition: dict, response_decision: dict, text: str, visual_reference: dict):
    timeline = state.get("dialog", [])
    if not isinstance(timeline, list) or not timeline:
        timeline = state.get("timeline", [])
    if not isinstance(timeline, list) or not timeline:
        dialog_state = state.get("dialog_state", {})
        if isinstance(dialog_state, dict):
            timeline = dialog_state.get("timeline", []) or []
    if not isinstance(timeline, list):
        timeline = []

    meta = state.get("meta", {}) if isinstance(state.get("meta", {}), dict) else {}
    focus_state = state.get("focus_state", state.get("dynamic_focus", {}))
    if not isinstance(focus_state, dict) or not focus_state:
        focus_state = state.get("focus_snapshot", {}) if isinstance(state.get("focus_snapshot", {}), dict) else {}

    active_topic = (
        state.get("active_topic")
        or state.get("topic")
        or state.get("current_topic")
        or (focus_state.get("topic") if isinstance(focus_state, dict) else None)
        or (state.get("dialog_state", {}).get("active_topic") if isinstance(state.get("dialog_state", {}), dict) else None)
        or semantic.get("topic")
        or response_decision.get("goal")
        or ""
    )

    last_user_turn = (
        state.get("last_user_turn")
        or meta.get("last_user_message")
        or (state.get("dialog_state", {}).get("last_user_turn") if isinstance(state.get("dialog_state", {}), dict) else None)
        or text
    )
    last_april_turn = (
        state.get("last_april_turn")
        or meta.get("last_bot_message")
        or (state.get("dialog_state", {}).get("last_april_turn") if isinstance(state.get("dialog_state", {}), dict) else None)
        or ""
    )

    return {
        "timeline": timeline,
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
        "modalities": {"text": bool(text), "voice": False, "image": False, "files": False},
        "last_user_turn": last_user_turn,
        "last_april_turn": last_april_turn,
        "active_topic": active_topic,
        "semantic": semantic,
        "cognition": cognition,
        "response_decision": response_decision,
        "goal_hierarchy": state.get("goal_hierarchy", {}),
        "focus": focus_state,
        "memory_timeline": state.get("memory_timeline", {}),
        "visual_summary": state.get("visual_summary", {}),
        "active_visual_scene": state.get("active_visual_scene", {}),
        "visual_reference": visual_reference,
    }


def build_executor_user_space(state: dict, conversation_space: Optional[dict] = None):
    conversation_space = conversation_space or {}
    dialog = conversation_space.get("timeline")
    if not isinstance(dialog, list) or not dialog:
        dialog = state.get("dialog", [])
    if not isinstance(dialog, list) or not dialog:
        dialog_state = state.get("dialog_state", {})
        if isinstance(dialog_state, dict):
            dialog = dialog_state.get("timeline", []) or []
    if not isinstance(dialog, list):
        dialog = []

    return {
        "scene": state.get("scene_state", {}),
        "workspace": state.get("workspace_state", {}),
        "dialog": dialog,
        "last_user_turn": conversation_space.get("last_user_turn") or state.get("last_user_turn"),
        "last_april_turn": conversation_space.get("last_april_turn") or state.get("last_april_turn"),
        "focus": state.get("focus_state", state.get("dynamic_focus", state.get("focus_snapshot", {}))),
        "goal_hierarchy": state.get("goal_hierarchy", {}),
        "active_flow": state.get("active_flow", {}),
        "memory_timeline": state.get("memory_timeline", {}),
        "visual_summary": state.get("visual_summary", {}),
        "visual_continuity_summary": state.get("visual_continuity_summary", {}),
        "active_visual_scene": state.get("active_visual_scene", {}),
        "renderer_state": state.get("renderer_state", {}),
        "task_resolution": state.get("task_resolution", {}),
    }


def build_executor_context(
    user_id: str,
    chat_id: str,
    state: dict,
    semantic: dict,
    reasoning: dict,
    cognition: dict,
    response_decision: dict,
    visual_reference: dict,
    task_type: str,
    text: str,
):
    user_space = build_executor_user_space(state)
    scene_state = user_space.get("scene", {})
    active_flow = user_space.get("active_flow", {})
    visual_continuity_summary = user_space.get("visual_continuity_summary", {})
    active_visual_scene = user_space.get("active_visual_scene", {})
    visual_memory_bridge = build_visual_memory_bridge(user_id)

    conversation_space = build_conversation_space(
        state=state,
        semantic=semantic,
        cognition=cognition,
        response_decision=response_decision,
        text=text,
        visual_reference=visual_reference,
    )

    return {
        "machine_channel": TASK_CHANNEL,
        "task_type": task_type,
        "executor_version": "april_cpu_v1",
        "user_id": user_id,
        "chat_id": chat_id,
        "semantic": semantic,
        "reasoning": reasoning,
        "cognition": cognition,
        "response_decision": response_decision,
        "executor_awareness": {
            "discussion_mode": response_decision.get("discussion_mode", False),
            "reflection_mode": response_decision.get("reflection_mode", False),
            "space_discussion": response_decision.get("space_discussion", False),
            "tool_discussion": response_decision.get("tool_discussion", False),
            "self_action_discussion": response_decision.get("self_action_discussion", False),
            "explanation_mode": response_decision.get("explanation_mode", False),
        },
        "visual_reference": visual_reference,
        "scene_state": scene_state,
        "active_flow": active_flow,
        "trajectory": scene_state.get("trajectory"),
        "continuity_mode": scene_state.get("continuity_mode"),
        "visual_continuity_summary": visual_continuity_summary,
        "active_visual_scene": active_visual_scene,
        "visual_memory_bridge": visual_memory_bridge,
        "visual_summary": visual_memory_bridge.get("visual_summary", {}),
        "today_visual_memory": visual_memory_bridge.get("today_visual_memory", []),
        "visual_goal": visual_continuity_summary.get("active_goal"),
        "machine_input": text,
        "platform": "agnostic",
        "state": state,
        "user_space": user_space,
        "conversation_space": _compact_conversation_space(conversation_space),
        "canonical_space": _compact_conversation_space(conversation_space),
        "memory_routing": {
            "focus_recommendation": cognition.get("focus_recommendation", cognition.get("dynamic_focus", {})),
            "goal_analysis": cognition.get("goal_analysis", cognition.get("goal_hierarchy", {})),
            "loop_analysis": cognition.get("loop_analysis", cognition.get("open_loops", {})),
            "memory_analysis": cognition.get("memory_analysis", cognition.get("memory_signals", {})),
        },
    }


def detect_task_type(semantic, cognition, state, conversation_space=None):
    user_space = build_executor_user_space(state, conversation_space=conversation_space)
    scene_state = user_space.get("scene", {})
    trajectory = scene_state.get("trajectory")
    if trajectory:
        track_trajectory(trajectory)

    if semantic.get("render_intent"):
        track_modality("renderer")
        return "renderer"
    if semantic.get("visual_generation_needed"):
        track_modality("image")
        return "image"
    if semantic.get("math_intent"):
        track_modality("math")
        return "math"
    return "text"


def _build_second_circle_machine_request(*, text: str, semantic: dict, provider_goal: str, provider_reference_context: str, second_circle_context: dict):
    intent_type = semantic.get("intent") or "dialogue"
    intent = {
        "type": intent_type if isinstance(intent_type, str) else str(intent_type),
        "normalized_text": normalize_text(text),
        "source": "executor_first_circle",
    }

    conversation_space = second_circle_context.get("conversation_space", {}) or {}
    machine_memory = second_circle_context.get("memory", {}) or {}
    machine_conversation = second_circle_context.get("conversation", {}) or {}
    visual_reference = second_circle_context.get("visual_reference", {}) or {}

    requested_outputs = list(dict.fromkeys(
        list(semantic.get("required_representations", []) or [])
        + list(semantic.get("candidate_representations", []) or [])
        + ([semantic.get("requested_representation")] if semantic.get("requested_representation") else [])
    ))
    required_artifacts = list(dict.fromkeys(
        list(requested_outputs)
        + list(semantic.get("required_domains", []) or [])
    ))

    machine_request = MachineRequest(
        goal=provider_goal,
        intent=intent,
        conversation=machine_conversation,
        memory=machine_memory,
        visual_context={
            "visual_reference": visual_reference,
            "visual_summary": machine_memory.get("visual_summary", {}),
            "active_visual_scene": conversation_space.get("active_visual_scene", {}),
            "scene_state": conversation_space.get("scene_state", {}),
            "trajectory": conversation_space.get("trajectory") or (conversation_space.get("scene_state", {}) or {}).get("trajectory"),
            "dialog_state": machine_memory.get("dialog_state", {}),
            "active_topic": machine_memory.get("active_topic", ""),
        },
        available_tools=list(second_circle_context.get("cognition", {}).get("available_tools", []) or []),
        requested_outputs=requested_outputs,
        required_competencies=list(dict.fromkeys(
            list(semantic.get("required_domains", []) or [])
            + list(semantic.get("candidate_domains", []) or [])
        )),
        required_artifacts=required_artifacts,
        routing={
            "provider_reference_context": provider_reference_context,
            "task_type": second_circle_context.get("task_type"),
        },
        constraints={
            "single_route": True,
            "preserve_dialog_continuity": True,
            "preserve_visual_continuity": True,
        },
    )
    try:
        setattr(machine_request, "provider_reference_context", provider_reference_context)
        setattr(machine_request, "first_circle_goal", provider_goal)
        setattr(machine_request, "first_circle_only", True)
        setattr(machine_request, "second_circle_context", second_circle_context)
        setattr(machine_request, "canonical_prompt_text", provider_goal)
        setattr(machine_request, "conversation_space", conversation_space)
    except Exception:
        pass
    return machine_request


def _executor_build_first_circle_goal(text: str, state: dict, semantic: dict, cognition: dict, response_decision: dict) -> Tuple[str, str]:
    canonical_plan = _executor_build_canonical_prompt_plan(
        text,
        semantic=semantic,
        cognition=cognition,
        response_decision=response_decision,
    )
    current_text = _executor_format_canonical_prompt(canonical_plan) or normalize_text(text)

    reference_context = _executor_build_reference_context(
        text=current_text,
        state=state,
        semantic=semantic,
        cognition=cognition,
        response_decision=response_decision,
    )

    if canonical_plan.get("is_multi_question"):
        extra = "Answer each task once. Do not repeat the same fact in multiple sections."
        if reference_context:
            reference_context = _clip_text(reference_context + "\n" + extra, FOLLOWUP_CONTEXT_CHAR_LIMIT * 2)
        else:
            reference_context = extra

    return current_text, reference_context


def _build_second_circle_context(
    *,
    state: dict,
    semantic: dict,
    reasoning: dict,
    cognition: dict,
    response_decision: dict,
    visual_reference: dict,
    task_type: str,
    text: str,
    conversation_space: dict,
    machine_memory: dict,
    machine_conversation: dict,
    reference_context: str,
):
    return {
        "state": state,
        "semantic": semantic,
        "reasoning": reasoning,
        "cognition": cognition,
        "response_decision": response_decision,
        "visual_reference": visual_reference,
        "task_type": task_type,
        "text": text,
        "conversation_space": conversation_space,
        "memory": machine_memory,
        "conversation": machine_conversation,
        "reference_context": reference_context,
        "provider_scope": {
            "goal_only": False,
            "memory_to_provider": True,
            "visual_to_provider": True,
            "conversation_to_provider": True,
        },
    }


# =====================================================
# VISIBLE BLOCK NORMALIZATION
# =====================================================

def _executor_infer_render_block_type(block: dict) -> str:
    if not isinstance(block, dict):
        return "text"
    candidates = [
        block.get("type"),
        block.get("renderer"),
        block.get("viewer"),
        block.get("artifact_type"),
        block.get("payload", {}).get("type") if isinstance(block.get("payload"), dict) else None,
        block.get("artifact", {}).get("type") if isinstance(block.get("artifact"), dict) else None,
    ]
    for candidate in candidates:
        text = normalize_text(candidate).lower()
        if text in {"table", "graph", "diagram", "formula", "gallery", "image", "link", "code", "markdown", "text"}:
            if text == "markdown":
                return "text"
            return text
        if "table" in text:
            return "table"
        if "graph" in text or "chart" in text:
            return "graph"
        if "diagram" in text or "schema" in text:
            return "diagram"
        if "formula" in text or "equation" in text:
            return "formula"
        if "gallery" in text or "carousel" in text:
            return "gallery"
        if "link" in text or "url" in text:
            return "link"
        if "code" in text:
            return "code"
        if "image" in text or "picture" in text:
            return "image"
    return normalize_text(block.get("type", "text")).lower() or "text"


def _executor_deduplicate_visible_render_blocks(blocks: Any, visible_text: str = "") -> list:
    if not isinstance(blocks, list):
        blocks = list(blocks or [])

    result = []
    seen_text = set()
    seen_struct = set()
    canonical_visible = normalize_text(visible_text)
    canonical_visible_norm = re.sub(r"\s+", " ", canonical_visible).strip().lower() if canonical_visible else ""

    for block in blocks:
        if not isinstance(block, dict):
            block = {"type": "machine_payload", "content": str(block), "renderer": "TextBlock", "viewer": "TextBlock", "priority": 0}

        block = dict(block)
        block_type = _executor_infer_render_block_type(block)
        content = block.get("content")
        content_text = normalize_text(content)
        content_norm = re.sub(r"\s+", " ", content_text).strip().lower() if content_text else ""

        # Preserve the renderer/viewer hints so downstream UI knows which block
        # should be rendered by which component.
        if block_type != "text":
            block["type"] = block_type

        if block_type in {"text", "markdown", "formula", "function"} and _executor_looks_like_internal_room_payload(content_text):
            continue

        if block_type in {"text", "markdown"}:
            key = (block_type, content_norm)
            if not content_norm:
                continue
            if key in seen_text:
                continue
            seen_text.add(key)
            result.append(block)
            continue

        sig = _executor_block_signature(block)
        if sig in seen_struct:
            continue
        seen_struct.add(sig)
        result.append(block)

    return result


def _executor_store_canonical_text_metadata(target: Any, *, answer: str, content: str, summary: str, original_answer: str = "", original_content: str = "") -> None:
    if target is None:
        return

    try:
        metadata = getattr(target, "metadata", None)
        if not isinstance(metadata, dict):
            metadata = {}
        if answer:
            metadata.setdefault("canonical_answer", answer)
        if content:
            metadata.setdefault("canonical_content", content)
        if summary:
            metadata.setdefault("canonical_summary", summary)
        if original_answer:
            metadata.setdefault("provider_original_answer", original_answer)
        if original_content:
            metadata.setdefault("provider_original_content", original_content)
        setattr(target, "metadata", metadata)
    except Exception:
        pass


def _executor_strip_duplicate_visible_fields(result: dict, visible_text: str, render_blocks: list) -> dict:
    if not isinstance(result, dict):
        return result

    canonical = visible_text or result.get("answer", "") or result.get("content", "") or result.get("summary", "")
    result["answer"] = canonical
    result["content"] = canonical
    result["summary"] = canonical
    result["render_blocks"] = render_blocks

    machine_response = result.get("machine_response")
    if machine_response is not None:
        try:
            canonical = visible_text or getattr(machine_response, "answer", "") or getattr(machine_response, "content", "") or getattr(machine_response, "summary", "")
            if hasattr(machine_response, "answer"):
                machine_response.answer = canonical
            if hasattr(machine_response, "content"):
                machine_response.content = canonical
            if hasattr(machine_response, "summary"):
                machine_response.summary = canonical
            if hasattr(machine_response, "render_blocks"):
                machine_response.render_blocks = render_blocks
        except Exception:
            pass

    scene_contract = result.get("scene_contract")
    if scene_contract is not None:
        try:
            if isinstance(scene_contract, dict):
                canonical = visible_text or scene_contract.get("answer", "") or scene_contract.get("content", "") or scene_contract.get("summary", "")
                scene_contract["answer"] = canonical
                scene_contract["content"] = canonical
                scene_contract["summary"] = canonical
                scene_contract["render_blocks"] = render_blocks
            else:
                canonical = visible_text or getattr(scene_contract, "answer", "") or getattr(scene_contract, "content", "") or getattr(scene_contract, "summary", "")
                setattr(scene_contract, "answer", canonical)
                setattr(scene_contract, "content", canonical)
                setattr(scene_contract, "summary", canonical)
                setattr(scene_contract, "render_blocks", render_blocks)
        except Exception:
            pass

    scene_runtime = result.get("scene_runtime")
    if isinstance(scene_runtime, dict):
        scene_runtime.setdefault("canonical_answer", visible_text)
        scene_runtime.setdefault("canonical_content", result.get("content", ""))
        scene_runtime.setdefault("canonical_summary", result.get("summary", ""))
        scene_runtime["render_blocks"] = render_blocks

    return result


# =====================================================
# SCENE PROJECTION
# =====================================================

def executor_cpu_normalize_answer(machine_response):
    """
    Preserve the canonical response as-is.
    No block-derived recovery, no alternate reconstruction.
    """
    if machine_response is None:
        return None

    for field in ("answer", "content", "summary"):
        if getattr(machine_response, field, None) is None:
            setattr(machine_response, field, "")
    return machine_response


def executor_cpu_transport_diag(stage: str, machine_response=None, scene_contract=None):
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
            blocks = getattr(scene_contract, "render_blocks", None)
            if blocks is None and isinstance(scene_contract, dict):
                blocks = scene_contract.get("render_blocks", [])
            print(f"[EXECUTOR][{stage}] scene_contract_blocks={len(blocks or [])}")
    except Exception as exc:
        print(f"[EXECUTOR][{stage}] diag_error={exc}")


def executor_cpu_attach_artifact_payloads(machine_response):
    artifacts = list(getattr(machine_response, "artifacts", []) or [])
    render_blocks = list(getattr(machine_response, "render_blocks", []) or [])
    artifact_index = {}
    for artifact in artifacts:
        artifact_type = getattr(artifact, "artifact_type", None) or getattr(artifact, "type", None)
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


def _canonicalize_formula_blocks(machine_response, semantic=None, response_decision=None):
    semantic = semantic or {}
    response_decision = response_decision or {}

    preferred = response_decision.get("preferred_representation") or semantic.get("preferred_representation") or ""

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


def executor_cpu_build_cognitive_context(*, semantic, cognition, response_decision, state, machine_response):
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
    ctx = getattr(machine_response, "executor_cognitive_context", {}) or {}
    continuation = bool(ctx.get("trajectory")) or bool(response_decision.get("should_continue_trajectory"))
    topic_mode = "continuation" if continuation else "new_topic"
    if not continuation and semantic.get("topic") and semantic.get("topic") == state.get("topic"):
        topic_mode = "same_topic"

    preferred_representation = (
        response_decision.get("preferred_representation")
        or semantic.get("preferred_representation")
        or semantic.get("requested_representation")
        or semantic.get("current_representation")
        or "text"
    )

    decision = {
        "topic_mode": topic_mode,
        "use_visual_memory": bool(ctx.get("active_visual_scene")),
        "use_memory_timeline": bool(ctx.get("memory_timeline")),
        "continue_scene": bool(ctx.get("active_visual_scene")),
        "preferred_representation": preferred_representation,
        "representation": preferred_representation,
        "history_match": bool(state.get("dialog") or state.get("dialog_state", {}).get("timeline")),
        "visual_match": bool(ctx.get("active_visual_scene")),
        "topic_relation": topic_mode,
        "continuation_probability": 0.8 if continuation else 0.2,
        "internal_only": True,
        "human_visible": False,
    }
    setattr(machine_response, "executor_decision", decision)
    return machine_response


def executor_cpu_build_presentation_plan(machine_response):
    decision = getattr(machine_response, "executor_decision", {}) or {}
    plan = {
        "representation": decision.get("preferred_representation") or "text",
        "blocks": [],
        "artifact_types": [],
        "provider_owned": True,
    }

    artifacts = list(getattr(machine_response, "artifacts", []) or [])
    for artifact in artifacts:
        artifact_type = getattr(artifact, "artifact_type", None) or getattr(artifact, "type", None) or "text"
        if artifact_type not in plan["artifact_types"]:
            plan["artifact_types"].append(artifact_type)
        if artifact_type not in plan["blocks"]:
            plan["blocks"].append(artifact_type)

    preferred = decision.get("preferred_representation")
    if preferred and preferred not in plan["artifact_types"]:
        plan["artifact_types"].insert(0, preferred)
    if preferred and preferred not in plan["blocks"]:
        plan["blocks"].insert(0, preferred)

    priority = ["graph", "table", "formula", "gallery", "diagram", "link", "code", "text"]
    for rep in priority:
        if rep in plan["artifact_types"]:
            plan["representation"] = rep
            break

    if preferred:
        plan["representation"] = preferred

    machine_response.executor_presentation_plan = plan
    return machine_response


def executor_cpu_integrate_presentation(machine_response):
    decision = getattr(machine_response, "executor_decision", {}) or {}
    plan = getattr(machine_response, "executor_presentation_plan", {}) or {}
    preferred = decision.get("preferred_representation") or plan.get("representation") or "text"
    plan["representation"] = preferred
    plan["executor_integrated"] = True
    plan["internal_only"] = True
    plan["human_visible"] = False
    machine_response.executor_presentation_plan = plan
    machine_response.executor_presentation_integrated = True
    return machine_response


def executor_cpu_memory_fusion(machine_response):
    cs = getattr(machine_response, "conversation_space", {}) or {}
    dialog_vector = {
        "timeline": cs.get("timeline", []),
        "memory_timeline": cs.get("memory_timeline", {}),
        "visual_summary": cs.get("visual_summary", {}),
        "active_visual_scene": cs.get("active_visual_scene", {}),
        "goal_hierarchy": cs.get("goal_hierarchy", {}),
        "focus": cs.get("focus", {}),
        "semantic": cs.get("semantic", {}),
        "response_decision": cs.get("response_decision", {}),
        "vector_version": "executor_super_v1",
        "single_route": True,
    }
    setattr(machine_response, "dialog_vector", dialog_vector)
    plan = getattr(machine_response, "executor_presentation_plan", {}) or {}
    plan["dialog_vector"] = True
    plan["memory_fusion"] = True
    plan["visual_continuity"] = bool(dialog_vector["active_visual_scene"])
    plan["dynamic_memory"] = bool(dialog_vector["memory_timeline"])
    machine_response.executor_presentation_plan = plan
    return machine_response


def executor_cpu_scene_intelligence(machine_response):
    dialog_vector = getattr(machine_response, "dialog_vector", {}) or {}
    planner = getattr(machine_response, "executor_presentation_plan", {}) or {}
    scene_profile = {
        "dialog_continuity": bool(dialog_vector.get("timeline")),
        "memory_continuity": bool(dialog_vector.get("memory_timeline")),
        "visual_continuity": bool(dialog_vector.get("active_visual_scene")),
        "goal_continuity": bool(dialog_vector.get("goal_hierarchy")),
        "focus_continuity": bool(dialog_vector.get("focus")),
        "scene_strategy": "single_scene_contract",
        "fiber_route": "single",
        "executor_generated": True,
    }
    planner["scene_profile"] = scene_profile
    planner["scene_intelligence"] = True
    machine_response.executor_presentation_plan = planner
    machine_response.executor_scene_profile = scene_profile
    return machine_response


def executor_cpu_synthetic_verification(machine_response):
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
    machine_response = executor_cpu_pipeline(machine_response)
    transient = ["executor_cognitive_context", "executor_scene_profile", "executor_user_alignment"]
    for name in transient:
        if hasattr(machine_response, name):
            try:
                delattr(machine_response, name)
            except Exception:
                pass
    setattr(machine_response, "executor_finalized", True)
    setattr(machine_response, "executor_pipeline_version", "FINAL")
    return machine_response


def executor_cpu_reflect(*, semantic, cognition, response_decision, state, machine_response):
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
    machine_response = _canonicalize_formula_blocks(machine_response, semantic=semantic, response_decision=response_decision)
    machine_response = executor_cpu_attach_artifact_payloads(machine_response)
    machine_response = executor_cpu_normalize_answer(machine_response)
    return machine_response


def executor_cpu_materialize_blocks(machine_response):
    render_blocks = list(getattr(machine_response, "render_blocks", []) or [])
    machine_response.render_blocks = render_blocks
    return machine_response


# =====================================================
# SCENE PIPELINE
# =====================================================

def executor_cpu_sync_scene_contract(scene_contract, machine_response, scene):
    if scene_contract is None:
        return scene_contract

    for field in ("answer", "content", "summary", "render_blocks", "artifacts", "metadata"):
        value = getattr(machine_response, field, None)

        if field == "metadata":
            value = _executor_payload_to_mapping(value)
            if not isinstance(value, dict):
                value = {}
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
    executor_cpu_transport_diag("BEFORE_BUILD_MACHINE_SCENE", machine_response)
    machine_response = executor_cpu_normalize_answer(machine_response)

    scene = build_machine_scene(machine_response)
    try:
        setattr(scene, "conversation_space", getattr(machine_response, "conversation_space", None))
    except Exception:
        pass

    conversation_space = getattr(machine_response, "conversation_space", {}) or {}
    try:
        setattr(scene, "timeline", conversation_space.get("timeline", []))
        setattr(scene, "last_user_turn", conversation_space.get("last_user_turn"))
        setattr(scene, "last_april_turn", conversation_space.get("last_april_turn"))
        setattr(scene, "active_goal", conversation_space.get("response_decision", {}).get("goal"))
    except Exception:
        pass

    scene_contract = build_scene_contract(scene)
    executor_cpu_transport_diag("AFTER_BUILD_SCENE_CONTRACT", machine_response, scene_contract)

    visible_text = _executor_best_text(
        getattr(machine_response, "answer", ""),
        getattr(machine_response, "content", ""),
        getattr(machine_response, "summary", ""),
    )

    blocks = list(getattr(machine_response, "render_blocks", []) or [])

    try:
        if isinstance(scene_contract, dict):
            scene_contract["answer"] = getattr(machine_response, "answer", "")
            scene_contract["content"] = getattr(machine_response, "content", "")
            scene_contract["summary"] = getattr(machine_response, "summary", "")
            scene_contract["render_blocks"] = blocks
        else:
            setattr(scene_contract, "answer", getattr(machine_response, "answer", ""))
            setattr(scene_contract, "content", getattr(machine_response, "content", ""))
            setattr(scene_contract, "summary", getattr(machine_response, "summary", ""))
            setattr(scene_contract, "render_blocks", blocks)
    except Exception:
        pass

    try:
        if isinstance(scene, dict):
            scene["answer"] = getattr(machine_response, "answer", "")
            scene["content"] = getattr(machine_response, "content", "")
            scene["summary"] = getattr(machine_response, "summary", "")
            scene["render_blocks"] = blocks
        else:
            setattr(scene, "answer", getattr(machine_response, "answer", ""))
            setattr(scene, "content", getattr(machine_response, "content", ""))
            setattr(scene, "summary", getattr(machine_response, "summary", ""))
            setattr(scene, "render_blocks", blocks)
    except Exception:
        pass

    executor_cpu_transport_diag("AFTER_SYNC_SCENE_CONTRACT", machine_response, scene_contract)

    return {
        "canonical_space": True,
        "machine_response": machine_response,
        "machine_scene": scene,
        "answer": getattr(machine_response, "answer", None),
        "content": getattr(machine_response, "content", None),
        "summary": getattr(machine_response, "summary", None),
        "render_blocks": blocks,
        "scene_contract": scene_contract,
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
    """
    Final processor pass:
    - keep the canonical answer untouched,
    - project exactly one visible route,
    - dedupe visible render blocks,
    - never rebuild from fallback branches.
    """
    executor_cpu_transport_diag("TRANSPORT_ENTRY", machine_response)
    machine_response = executor_cpu_normalize_answer(machine_response)
    machine_response = executor_cpu_materialize_blocks(machine_response)
    machine_response = executor_cpu_attach_artifact_payloads(machine_response)

    scene = executor_cpu_scene_pipeline(machine_response)
    conversation_space = getattr(machine_response, "conversation_space", None)
    scene_contract = scene.get("scene_contract")

    visible_text = _executor_best_text(
        getattr(machine_response, "answer", ""),
        getattr(machine_response, "content", ""),
        getattr(machine_response, "summary", ""),
    )

    semantic = getattr(machine_response, "executor_semantic", {}) or {}
    response_decision = getattr(machine_response, "executor_response_decision", {}) or {}

    scene_blocks = []
    if scene_contract is not None:
        if isinstance(scene_contract, dict):
            scene_blocks = list(scene_contract.get("render_blocks", []) or [])
        else:
            scene_blocks = list(getattr(scene_contract, "render_blocks", []) or [])

    source_blocks = list(getattr(machine_response, "render_blocks", []) or [])
    if scene_blocks:
        source_blocks = scene_blocks + [block for block in source_blocks if block not in scene_blocks]
    if not source_blocks:
        source_blocks = list(scene.get("render_blocks", []) or [])
    if not source_blocks and visible_text:
        source_blocks = [{
            "type": "text",
            "content": visible_text,
            "renderer": "TextBlock",
            "viewer": "TextBlock",
            "priority": 0,
            "source_room": "text",
        }]

    source_blocks = apply_representation_gate(source_blocks, response_decision=response_decision, semantic=semantic)
    blocks = _executor_deduplicate_visible_render_blocks(source_blocks, visible_text=visible_text)

    if visible_text:
        machine_response.answer = visible_text
        machine_response.content = visible_text
        machine_response.summary = visible_text

    _executor_store_canonical_text_metadata(
        machine_response,
        answer=visible_text,
        content=visible_text,
        summary=visible_text,
        original_answer=getattr(machine_response, "provider_original_answer", "") or "",
        original_content=getattr(machine_response, "provider_original_content", "") or "",
    )

    if scene_contract is not None:
        _executor_store_canonical_text_metadata(
            scene_contract,
            answer=visible_text,
            content=visible_text,
            summary=visible_text,
            original_answer=getattr(machine_response, "provider_original_answer", "") if machine_response is not None else "",
            original_content=getattr(machine_response, "provider_original_content", "") if machine_response is not None else "",
        )
        try:
            if isinstance(scene_contract, dict):
                scene_contract["answer"] = visible_text
                scene_contract["content"] = visible_text
                scene_contract["summary"] = visible_text
                scene_contract["render_blocks"] = blocks
            else:
                setattr(scene_contract, "answer", visible_text)
                setattr(scene_contract, "content", visible_text)
                setattr(scene_contract, "summary", visible_text)
                setattr(scene_contract, "render_blocks", blocks)
        except Exception:
            pass

    result = {
        "transport_contract": "scene_first",
        "provider_contract": "fiber_v3",
        "conversation_space": conversation_space,
        "machine_response": machine_response,
        "machine_scene": scene.get("machine_scene"),
        "scene_contract": scene_contract,
        "current_turn": conversation_space.get("current_turn") if conversation_space else None,
        "answer": visible_text,
        "content": visible_text,
        "summary": visible_text,
        "render_blocks": blocks,
    }

    _executor_strip_duplicate_visible_fields(result, visible_text, blocks)

    if isinstance(scene, dict):
        scene["answer"] = visible_text
        scene["content"] = visible_text
        scene["summary"] = visible_text
        scene["render_blocks"] = blocks

    executor_cpu_transport_diag("FINAL_TRANSPORT", machine_response, scene_contract)
    return result
# =====================================================
# ROOM SELECTION / MERGE
# =====================================================

def _executor_merge_room_results_into_canonical_response(
    base_response: MachineResponse,
    room_results: Any,
    canonical_room_name: str = "text",
):
    """
    Sequential enrichment only:
    - keep canonical text untouched;
    - merge support data;
    - append only non-duplicate helper blocks.
    """
    if base_response is None:
        base_response = MachineResponse()
    if not isinstance(base_response, MachineResponse):
        base_response = _executor_materialize_machine_response(base_response) or MachineResponse()

    room_results = list(room_results or [])
    existing_blocks = list(getattr(base_response, "render_blocks", []) or [])
    existing_artifacts = list(getattr(base_response, "artifacts", []) or [])
    existing_contributions = getattr(base_response, "contributions", None) or {}
    if not isinstance(existing_contributions, dict):
        existing_contributions = {}

    block_seen = {_executor_block_signature(block) for block in existing_blocks}
    artifact_seen = {_executor_artifact_signature(artifact) for artifact in existing_artifacts}

    for item in room_results:
        if not isinstance(item, dict):
            continue

        room_name = _executor_room_name_from_item(item)
        candidate = _executor_materialize_machine_response(item.get("machine_response"))
        if candidate is None:
            continue

        candidate_contributions = getattr(candidate, "contributions", None) or {}
        if isinstance(candidate_contributions, dict) and candidate_contributions:
            room_bucket = existing_contributions.setdefault("room_signals", {})
            room_key = room_name or getattr(candidate, "room_source", "") or f"room_{len(room_bucket) + 1}"
            room_bucket[room_key] = candidate_contributions
            for key, value in candidate_contributions.items():
                existing_contributions.setdefault(key, value)

        for artifact in list(getattr(candidate, "artifacts", []) or []):
            sig = _executor_artifact_signature(artifact)
            if sig in artifact_seen:
                continue
            existing_artifacts.append(artifact)
            artifact_seen.add(sig)

        for block in list(getattr(candidate, "render_blocks", []) or []):
            if not isinstance(block, dict):
                block = {
                    "type": "machine_payload",
                    "content": str(block),
                    "renderer": "TextBlock",
                    "viewer": "TextBlock",
                    "priority": 0,
                }
            block = dict(block)
            block.setdefault("source_room", room_name or getattr(candidate, "room_source", ""))
            block_type = normalize_text(block.get("type")).lower()

            if (
                room_name != canonical_room_name
                and block_type in {"text", "markdown", "formula", "function"}
                and _executor_looks_like_internal_room_payload(block.get("content"))
            ):
                continue

            sig = _executor_block_signature(block)
            if sig in block_seen:
                continue
            existing_blocks.append(block)
            block_seen.add(sig)

        for field in (
            "response",
            "explanation",
            "goal",
            "goal_hierarchy",
            "focus",
            "visual_reference",
            "visual_summary",
            "active_visual_scene",
            "metadata",
        ):
            if field == "metadata":
                candidate_metadata = getattr(candidate, "metadata", None)
                if isinstance(candidate_metadata, dict) and candidate_metadata:
                    base_metadata = getattr(base_response, "metadata", None)
                    if not isinstance(base_metadata, dict):
                        base_metadata = {}
                    for key, value in candidate_metadata.items():
                        base_metadata.setdefault(key, value)
                    try:
                        base_response.metadata = base_metadata
                    except Exception:
                        pass
                continue

            if _executor_value_is_empty(getattr(base_response, field, None)):
                value = getattr(candidate, field, None)
                if value not in (None, "", [], {}):
                    try:
                        setattr(base_response, field, value)
                    except Exception:
                        pass

    base_response.render_blocks = existing_blocks
    base_response.artifacts = existing_artifacts
    base_response.contributions = existing_contributions
    return base_response


def _executor_recover_room_response(machine_response, room_results, machine_request=None, text=None):
    """
    No recovery branches. The canonical response must already exist.
    """
    if machine_response is None:
        raise RuntimeError("Canonical MachineResponse is missing")
    return machine_response


# =====================================================
# ROOM EXECUTION
# =====================================================

def executor_cpu_register_room(report, room_name, **kwargs):
    entry = {"room": room_name}
    entry.update(kwargs)
    report.append(entry)
    return report


async def execute_rooms(user_id, text, context, semantic, cognition, response_decision, state, run_with_activity):
    machine_request = context.get("machine_request")
    if machine_request is None:
        raise RuntimeError("MachineRequest missing from executor context")

    room_results = []
    room_execution_report = []
    best_machine_response = None
    best_score = -1
    canonical_machine_response = None
    canonical_room_name = "text"

    for room in ROOMS:
        try:
            result = await room.handle(
                user_id=user_id,
                text=text,
                context=machine_request,
                run=run_with_activity,
            )

            extracted = _extract_machine_response(result)
            if extracted is None and isinstance(result, dict):
                mr = result.get("machine_response")
                if isinstance(mr, (dict, MachineResponse)):
                    extracted = _executor_materialize_machine_response(mr)
                    if extracted is None and isinstance(mr, dict):
                        extracted = _executor_payload_from_mapping_direct(mr)

            if extracted is not None:
                room_name = getattr(room, "name", "unknown")
                room_results.append({"room": room_name, "machine_response": extracted})
                executor_cpu_register_room(room_execution_report, room_name, status="ok")

                score = _executor_response_score(extracted)
                if best_machine_response is None or score > best_score:
                    best_machine_response = extracted
                    best_score = score

                if _executor_is_canonical_room(room_name, room):
                    if canonical_machine_response is None or _executor_has_meaningful_payload(extracted):
                        canonical_machine_response = extracted
                        canonical_room_name = room_name or canonical_room_name
                continue

        except Exception as exc:
            room_execution_report.append({"room": getattr(room, "name", "unknown"), "status": "error", "error": str(exc)})
            continue

    if canonical_machine_response is None:
        canonical_machine_response = best_machine_response

    if canonical_machine_response is None:
        raise RuntimeError("No MachineResponse produced")

    room_results = sorted(room_results, key=lambda item: _executor_response_score(item.get("machine_response")), reverse=True)

    machine_response = canonical_machine_response
    machine_response = _executor_recover_room_response(
        machine_response,
        room_results,
        machine_request=machine_request,
        text=text,
    )

    canonical_answer = _executor_best_text(
        getattr(machine_response, "answer", ""),
        getattr(machine_response, "content", ""),
        getattr(machine_response, "summary", ""),
    )
    canonical_content = _executor_best_text(
        getattr(machine_response, "content", ""),
        getattr(machine_response, "answer", ""),
        getattr(machine_response, "summary", ""),
    )
    canonical_summary = _executor_best_text(
        getattr(machine_response, "summary", ""),
        getattr(machine_response, "content", ""),
        getattr(machine_response, "answer", ""),
    )

    conversation_space = context.get("conversation_space") or {}
    current_turn = conversation_space.get("current_turn", {})
    april_turn = {
        "answer": getattr(machine_response, "answer", None),
        "summary": getattr(machine_response, "summary", None),
        "render_blocks": list(getattr(machine_response, "render_blocks", []) or []),
    }
    if "current_turn" in conversation_space and isinstance(conversation_space["current_turn"], dict):
        conversation_space["current_turn"]["april"] = april_turn
    conversation_space["last_april_turn"] = april_turn

    timeline = conversation_space.setdefault("timeline", [])
    if "current_turn" in conversation_space:
        timeline.append(conversation_space["current_turn"])
    conversation_space["dialog"] = timeline
    setattr(machine_response, "conversation_space", conversation_space)

    machine_response = executor_cpu_normalize_answer(machine_response)

    executor_cpu_transport_diag("BEFORE_REFLECT", machine_response)
    machine_response = executor_cpu_reflect(
        semantic=semantic,
        cognition=cognition,
        response_decision=response_decision,
        state=state,
        machine_response=machine_response,
    )

    setattr(machine_response, "room_execution_report", room_execution_report)
    if not room_results:
        room_results = [{"machine_response": machine_response}]
    reflected_machine_response = machine_response

    registry_result = registry_parent_dispatch(machine_request, room_results)
    machine_response = reflected_machine_response

    if registry_result is not None:
        try:
            registry_diagnostics = getattr(registry_result, "registry_diagnostics", None)
            if registry_diagnostics not in (None, "", [], {}):
                machine_response.registry_diagnostics = registry_diagnostics
        except Exception:
            pass

        try:
            merge_inputs = list(room_results)
            merge_inputs.append({"room": "registry", "machine_response": registry_result})
            machine_response = _executor_merge_room_results_into_canonical_response(
                machine_response,
                merge_inputs,
                canonical_room_name=canonical_room_name,
            )
        except Exception:
            pass

    machine_response = executor_cpu_normalize_answer(machine_response)

    if canonical_answer:
        machine_response.answer = canonical_answer
    if canonical_content:
        machine_response.content = canonical_content
    if canonical_summary:
        machine_response.summary = canonical_summary

    if not list(getattr(machine_response, "render_blocks", []) or []) and getattr(machine_response, "answer", ""):
        machine_response.render_blocks = [{
            "type": "text",
            "content": machine_response.answer,
            "renderer": "TextBlock",
            "viewer": "TextBlock",
            "priority": 0,
            "source_room": canonical_room_name,
        }]

    executor_cpu_transport_diag("AFTER_REFLECT", machine_response)
    setattr(machine_response, "provider_transport_verified", True)
    setattr(machine_response, "provider_contract_version", "fiber_v3_super")
    return executor_cpu_finalize_transport(machine_response)


# =====================================================
# HIGH-LEVEL EXECUTION
# =====================================================

def validate_machine_response(result):
    if not result:
        return False
    if isinstance(result, MachineResponse):
        return True
    if not isinstance(result, dict):
        return False

    blocked = ["traceback", "system prompt", "internal reasoning", "execution room", "cognitive state"]
    payload = str(result).lower()
    for word in blocked:
        if word in payload:
            return False
    return True


def detect_task_type(semantic, cognition, state, conversation_space=None):
    user_space = build_executor_user_space(state, conversation_space=conversation_space)
    scene_state = user_space.get("scene", {})
    trajectory = scene_state.get("trajectory")
    if trajectory:
        track_trajectory(trajectory)

    if semantic.get("render_intent"):
        track_modality("renderer")
        return "renderer"
    if semantic.get("visual_generation_needed"):
        track_modality("image")
        return "image"
    if semantic.get("math_intent"):
        track_modality("math")
        return "math"
    return "text"


def _build_executor_machine_memory(state: dict, conversation_space: dict) -> dict:
    scene_state = state.get("scene_state", {}) if isinstance(state.get("scene_state", {}), dict) else {}
    dialog_state = state.get("dialog_state", {}) if isinstance(state.get("dialog_state", {}), dict) else {}
    return {
        "memory_summary": _clip_text(state.get("memory_summary"), 3000),
        "active_flow": state.get("active_flow"),
        "memory_timeline": _compact_memory_bundle(conversation_space.get("memory_timeline", {})),
        "goal_hierarchy": state.get("goal_hierarchy", {}),
        "focus": state.get("focus_state", state.get("focus", {})),
        "active_topic": state.get("active_topic") or state.get("current_topic") or dialog_state.get("active_topic", ""),
        "current_topic": state.get("current_topic"),
        "current_object": state.get("current_object"),
        "last_user_turn": state.get("last_user_turn") or dialog_state.get("last_user_turn", ""),
        "last_april_turn": state.get("last_april_turn") or dialog_state.get("last_april_turn", ""),
        "trajectory": scene_state.get("trajectory", ""),
        "dialog_state": _compact_memory_bundle(dialog_state),
        "visual_summary": _compact_memory_bundle(conversation_space.get("visual_summary", {})),
    }


def _build_executor_machine_conversation(conversation_space: dict, text: str) -> dict:
    current_turn = conversation_space.get("current_turn", {})
    dialog_state = conversation_space.get("dialog_state", {}) if isinstance(conversation_space.get("dialog_state", {}), dict) else {}
    return {
        "timeline": _compact_timeline(conversation_space.get("timeline", []), max_items=14),
        "dialog": _compact_timeline(conversation_space.get("dialog", []), max_items=14),
        "last_user_turn": current_turn.get("user", {}).get("text", text),
        "last_april_turn": conversation_space.get("last_april_turn") or dialog_state.get("last_april_turn"),
        "active_topic": conversation_space.get("active_topic") or dialog_state.get("active_topic", ""),
        "focus": _compact_memory_bundle(conversation_space.get("focus", dialog_state.get("focus", {}))),
        "memory_summary": _clip_text(conversation_space.get("memory_summary", ""), 3000),
        "trajectory": conversation_space.get("trajectory") or (conversation_space.get("scene_state", {}) or {}).get("trajectory"),
        "active_visual_scene": conversation_space.get("active_visual_scene", {}),
        "scene_state": _compact_memory_bundle(conversation_space.get("scene_state", {})),
    }


async def execute(user_id, chat_id=None, text="", run_with_activity=None, **kwargs):
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
    cognition = analyze_cognition(text=text, semantic=semantic, reasoning=reasoning, state=state)
    visual_reference = build_visual_reference(semantic=semantic, cognition=cognition, text=text, state=state)

    response_decision = build_response_decision(
        semantic=semantic,
        cognition=cognition,
        state=state,
        visual_reference=visual_reference,
    )
    task_type = detect_task_type(semantic, cognition, state, conversation_space=None)

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

    machine_memory = _build_executor_machine_memory(state, conversation_space)
    machine_conversation = _build_executor_machine_conversation(conversation_space, text)

    provider_goal, provider_reference_context = _executor_build_first_circle_goal(
        text=text,
        state=state,
        semantic=semantic,
        cognition=cognition,
        response_decision=response_decision,
    )

    executor_provider_stage_log("PROVIDER_REQUEST", {"goal_len": len(provider_goal), "reference_context": bool(provider_reference_context)})

    second_circle_context = _build_second_circle_context(
        state=state,
        semantic=semantic,
        reasoning=reasoning,
        cognition=cognition,
        response_decision=response_decision,
        visual_reference=visual_reference,
        task_type=task_type,
        text=text,
        conversation_space=conversation_space,
        machine_memory=machine_memory,
        machine_conversation=machine_conversation,
        reference_context=provider_reference_context,
    )

    context["machine_request"] = _build_second_circle_machine_request(
        text=text,
        semantic=semantic,
        provider_goal=provider_goal,
        provider_reference_context=provider_reference_context,
        second_circle_context=second_circle_context,
    )
    context["executor_state"] = state
    context["executor_conversation_space"] = conversation_space
    context["second_circle_context"] = second_circle_context

    setattr(context["machine_request"], "current_turn", current_turn)

    if "factory_hook_registration" in kwargs:
        executor_cpu_sync_factory_bridge(kwargs["factory_hook_registration"])

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

    if isinstance(result, dict):
        machine_response = result.get("machine_response")
        if isinstance(machine_response, MachineResponse):
            result["machine_response"] = machine_response
            if _executor_value_is_empty(result.get("answer")):
                result["answer"] = getattr(machine_response, "answer", "")
            if _executor_value_is_empty(result.get("content")):
                result["content"] = getattr(machine_response, "content", "")
            if _executor_value_is_empty(result.get("summary")):
                result["summary"] = getattr(machine_response, "summary", "")
            if _executor_value_is_empty(result.get("render_blocks")):
                result["render_blocks"] = list(getattr(machine_response, "render_blocks", []) or [])

    executor_provider_stage_log(
        "PROVIDER_RESPONSE",
        {
            "has_machine_response": isinstance(result, dict) and "machine_response" in result,
            "has_scene_contract": isinstance(result, dict) and "scene_contract" in result,
            "render_blocks": len((result.get("render_blocks") if isinstance(result, dict) else []) or []),
        },
    )

    result = executor_cpu_factory_bridge(result)
    result = executor_cpu_gateway_dispatch(result)
    cpu_trace_success("EXECUTE")
    return result


# =====================================================
# FACTORY / GATEWAY HELPERS
# =====================================================

def executor_cpu_factory_bridge(machine_result):
    cpu_trace_begin("FACTORY_RETURN", {})
    if isinstance(machine_result, dict):
        cpu_trace_success("FACTORY_RETURN", {
            "has_scene_contract": "scene_contract" in machine_result,
            "has_machine_response": "machine_response" in machine_result,
            "has_machine_scene": "machine_scene" in machine_result,
        })
    return machine_result


def executor_cpu_gateway_dispatch(result):
    cpu_trace_success("CPU_GATEWAY_DISPATCH", {"scene_contract": isinstance(result, dict) and "scene_contract" in result})
    return result


def executor_cpu_register_factory_hooks(register_hook):
    register_hook(begin=cpu_trace_begin, success=cpu_trace_success, error=cpu_trace_error)


def executor_cpu_factory_event(stage, payload=None):
    cpu_trace_begin(stage, payload or {})


def executor_cpu_factory_complete(stage, payload=None):
    cpu_trace_success(stage, payload or {})


def executor_cpu_sync_factory_bridge(factory_register):
    executor_cpu_register_factory_hooks(factory_register)
    cpu_trace_success("FACTORY_BRIDGE_REGISTERED", {"single_route": True})


# =====================================================
# PRESENTATION / ARTIFACTS / UTILITIES
# =====================================================

def apply_representation_gate(blocks, response_decision=None, semantic=None):
    response_decision = response_decision or {}
    semantic = semantic or {}
    preferred = response_decision.get("preferred_representation") or semantic.get("preferred_representation")
    if not preferred:
        return blocks
    filtered = []
    for b in blocks:
        if not isinstance(b, dict):
            filtered.append(b)
            continue
        t = b.get("type")
        if t in ("graph", "formula", "table", "diagram", "gallery") and t != preferred:
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
        return {"type": "scene_contract", **result}
    return result


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
        "utc": ["utc"],
    }


def domain_room_bonus(room, semantic):
    required_domains = semantic.get("required_domains", [])
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
    factory_order = semantic.get("factory_order", {})
    return factory_order.get("required_rooms", [])


def build_scene_plan(response_decision, semantic=None):
    semantic = semantic or {}
    artifact_scene = response_decision.get("artifact_scene", [])
    artifact_bundle = response_decision.get("artifact_bundle", semantic.get("artifact_bundle", {}))
    primary = artifact_bundle.get("primary", [])
    secondary = artifact_bundle.get("secondary", [])
    scene_order = []
    scene_order.extend(primary)
    scene_order.extend(secondary)
    return {
        "goal": semantic.get("intent", "dialogue"),
        "primary_artifacts": primary,
        "secondary_artifacts": secondary,
        "artifact_scene": artifact_scene,
        "scene_order": scene_order,
        "composition_strategy": "artifact_first_scene_composition",
    }


def botru_translate_artifact(artifact: Any):
    if artifact is None:
        return {"type": "artifact", "content": ""}
    if hasattr(artifact, "data"):
        payload = artifact.data
        if isinstance(payload, dict):
            for field in [
                "answer", "response", "content", "text", "summary", "analysis",
                "description", "research_summary", "observation_report", "topic",
            ]:
                value = payload.get(field)
                if value:
                    return {"type": "artifact", "content": str(value), "artifact": payload}
            return {"type": "artifact", "content": str(payload), "artifact": payload}
    if isinstance(artifact, str):
        return {"type": "artifact", "content": artifact}
    if isinstance(artifact, dict):
        for field in [
            "content", "text", "summary", "analysis", "description",
            "research_summary", "observation_report", "topic",
        ]:
            value = artifact.get(field)
            if value:
                return {"type": "artifact", "content": str(value), "artifact": artifact}
        return {"type": "artifact", "content": str(artifact), "artifact": artifact}
    return {"type": "artifact", "content": str(artifact)}


def artifact_to_render_block(result: Any):
    if not isinstance(result, dict):
        return {"type": "machine_payload", "payload": result}
    result_type = result.get("type")
    if result_type != "artifact":
        return result
    artifact = result.get("artifact")
    translated = botru_translate_artifact(artifact)
    translated["machine_payload"] = True
    return translated


def build_task_resolution(cognition, response_decision, semantic, state):
    task = cognition.get("task_understanding", {})
    next_step = cognition.get("assistant_next_step", "ready_to_help")
    confusion = cognition.get("user_confusion", 0.0)
    clarification_required = response_decision.get("task_requires_clarification", False)

    resolution = {
        "mode": "execute",
        "next_step": next_step,
        "guidance_priority": False,
        "missing_information": task.get("missing_information", []),
    }

    if clarification_required:
        resolution["mode"] = "clarify"
        resolution["guidance_priority"] = True
    if confusion >= 0.5:
        resolution["guidance_priority"] = True
    return resolution


def build_guidance_response(task_resolution):
    step = task_resolution.get("next_step")
    messages = {
        "request_image": "Чтобы помочь точнее, пришли скриншот или изображение того, что ты видишь сейчас.",
        "request_formula": "Напиши формулу или опиши задачу своими словами. Если формулу не знаешь, я помогу её подобрать.",
        "request_error_details": "Покажи текст ошибки или пришли скриншот окна с ошибкой, и я проведу тебя дальше.",
    }
    if step not in messages:
        return None
    return {"type": "text", "data": messages[step]}


def validate_machine_response(result):
    if not result:
        return False
    if isinstance(result, MachineResponse):
        return True
    if not isinstance(result, dict):
        return False

    blocked = ["traceback", "system prompt", "internal reasoning", "execution room", "cognitive state"]
    payload = str(result).lower()
    for word in blocked:
        if word in payload:
            return False
    return True


# =====================================================
# PLACEHOLDERS / COMPATIBILITY ALIASES
# =====================================================

def executor_cpu_factory_return(result):
    return executor_cpu_factory_bridge(result)


def executor_cpu_finalize_result(machine_response):
    return executor_cpu_finalize(machine_response)


def executor_cpu_pipeline_compat(machine_response):
    return executor_cpu_pipeline(machine_response)


def executor_cpu_scene_contract(scene_contract, machine_response, scene):
    return executor_cpu_sync_scene_contract(scene_contract, machine_response, scene)
