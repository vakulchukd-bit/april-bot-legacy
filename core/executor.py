"""
April — Quant Test 1
Macro Quantum Matrix Processor.

Purpose
-------
A new processor core for April. This file is NOT an Executor wrapper and does
not import the legacy/current executor. It owns one unified route and delegates
work to the existing specialized engines.

Architecture
------------
INGEST -> MEASURE -> DELEGATE -> FEEDBACK -> COLLAPSE -> EXECUTE -> RELEASE

Macro matrix
------------
16 macro domains × 16 process lanes = 256 structural cells.

The matrix is structural, not a word-trigger router and not a score-based
classifier. Every engine contributes a typed evidence packet. The processor
is the only authority allowed to collapse those packets into one executable
MachineRequest.

Hard invariants
---------------
* no fallback path
* no second executor
* no second provider route
* one provider call per user turn
* one SceneContract release
* current request remains authoritative
* failures stop the route instead of bypassing it
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass, asdict
from typing import Any, Callable

from blocks.context_system import build_deephub_context, build_executor_context_packet
from blocks.interpretation_layer import (
    interpret_request,
    build_processor_execution_context,
    QUANTUM_DIALOGUE_ENGINE,
)
from blocks.semantic_core import analyze as semantic_analyze
from blocks.reasoning_state import build_reasoning_state
from blocks.cognitive_core import analyze_cognition
from blocks.response_decision import build_response_decision
from blocks.visual_reference_system import build_visual_reference
from blocks.experience import build_experience_evidence
from blocks.experience_manager import get_experience
from blocks.goal_engine import build_goal_evidence
from blocks.intent_system import detect_intent
from blocks.intent_ai import detect_intent_ai
from blocks.intent_resolver import resolve_input, build_focus_intent_state
from blocks.router import route_request
from blocks.router_system import decide_action
from blocks.state_manager import (
    get_state,
    update_dialog_context,
    update_scene_context,
    query_dynamic_memory,
    is_dialogue_visible_scene,
)
from blocks.C_ARTIFACT_CONTRACT import (
    MachineRequest,
    MachineResponse,
    build_machine_scene,
    build_scene_contract,
)
from blocks.provider_router import generate_text
from blocks.energy_manager import (
    build_quantum_acceleration_profile,
    apply_quantum_acceleration,
    validate_quantum_acceleration,
)
from blocks.april_personality import APRIL_IDENTITY


PROCESSOR_VERSION = "quant_test1_macro_quantum_matrix_16x16_v1"
SINGLE_ROUTE = True
PROVIDER_CALLS = 1
OUTPUT_MIN_TOKENS = 1
OUTPUT_MAX_TOKENS = 8000

MACRO_DOMAINS = (
    "context",
    "interpretation",
    "semantic",
    "cognition",
    "intent",
    "intent_ai",
    "resolver",
    "routing",
    "visual",
    "memory",
    "experience",
    "experience_manager",
    "goal",
    "decision",
    "energy",
    "presentation",
)

PROCESS_LANES = (
    "ingest",
    "normalize",
    "semantic_measurement",
    "dialogue_measurement",
    "memory_measurement",
    "intent_measurement",
    "representation_measurement",
    "capability_measurement",
    "visual_measurement",
    "delegation",
    "feedback",
    "arbitration",
    "budget",
    "provider",
    "artifact_contract",
    "render_release",
)

MACRO_SIGNAL_COUNT = len(MACRO_DOMAINS) * len(PROCESS_LANES)


@dataclass(frozen=True)
class QuantumSignal:
    signal_id: str
    domain: str
    lane: str
    source: str
    payload: dict[str, Any]
    request_id: str
    producer: str = "QUANTUM_PROCESSOR"
    immutable: bool = True


@dataclass(frozen=True)
class QuantumTask:
    task_id: str
    domain: str
    lane: str
    engine: str
    dependencies: tuple[str, ...] = ()


@dataclass
class QuantumTrace:
    request_id: str
    version: str
    stages: list[str]
    delegated_tasks: list[dict[str, Any]]
    signals: list[dict[str, Any]]
    feedback: list[dict[str, Any]]
    collapse: dict[str, Any]
    release: dict[str, Any]


def _s(value: Any) -> str:
    return str(value or "").strip()


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return list(value)
    if isinstance(value, str):
        return [value] if value else []
    return []


def _unique_strings(values: Any) -> list[str]:
    result: list[str] = []
    for value in _as_list(values):
        item = _s(value).lower()
        if item and item not in result:
            result.append(item)
    return result


def _snapshot(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _snapshot(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_snapshot(v) for v in value]
    return _s(value)


def _request_id(user_id: str, text: str) -> str:
    seed = f"{user_id}|{text}|{PROCESSOR_VERSION}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def _user_scope(state: dict[str, Any], user_id: str) -> dict[str, Any]:
    uid = _s(user_id)
    if not uid:
        raise RuntimeError("Quant Test 1: user_id is required")
    conversation_id = _s(state.get("conversation_id"))
    if not conversation_id:
        conversation_id = f"april-{hashlib.sha256(uid.encode('utf-8')).hexdigest()[:24]}"
        state["conversation_id"] = conversation_id
    scope = {
        "user_id": uid,
        "conversation_id": conversation_id,
        "identity_bound": True,
        "scope_version": "USER_SCOPED_SCENE_V1",
    }
    state["memory_scope"] = deepcopy(scope)
    return scope


def _new_signal(
    request_id: str,
    domain: str,
    lane: str,
    source: str,
    payload: dict[str, Any],
) -> QuantumSignal:
    if domain not in MACRO_DOMAINS:
        raise RuntimeError(f"Quant Test 1: unknown macro domain: {domain}")
    if lane not in PROCESS_LANES:
        raise RuntimeError(f"Quant Test 1: unknown process lane: {lane}")
    return QuantumSignal(
        signal_id=f"{request_id}:{domain}:{lane}",
        domain=domain,
        lane=lane,
        source=source,
        payload=_snapshot(payload),
        request_id=request_id,
    )


def _matrix_shell(request_id: str) -> dict[str, Any]:
    cells = {}
    for domain in MACRO_DOMAINS:
        cells[domain] = {}
        for lane in PROCESS_LANES:
            cells[domain][lane] = {
                "state": "EMPTY",
                "request_id": request_id,
            }
    return {
        "version": "QTM16X16",
        "dimensions": {
            "macro_domains": len(MACRO_DOMAINS),
            "process_lanes": len(PROCESS_LANES),
            "signal_cells": MACRO_SIGNAL_COUNT,
        },
        "cells": cells,
    }


def _record_cell(
    matrix: dict[str, Any],
    signal: QuantumSignal,
    *,
    state: str = "MEASURED",
) -> None:
    cell = matrix["cells"][signal.domain][signal.lane]
    cell.update({
        "state": state,
        "signal_id": signal.signal_id,
        "source": signal.source,
        "payload": signal.payload,
    })


def _latest_dialogue_pair(state: dict[str, Any]) -> tuple[str, str, Any]:
    scene = state.get("current_visual_scene")
    if isinstance(scene, dict):
        user = _s(scene.get("user_request") or scene.get("current_request"))
        answer = _s(scene.get("april_answer") or scene.get("answer"))
        if user and answer:
            return user, answer, scene.get("turn_id")
    dialog = state.get("dialog")
    if isinstance(dialog, list):
        for idx in range(len(dialog) - 2, -1, -1):
            left = _as_dict(dialog[idx])
            right = _as_dict(dialog[idx + 1])
            if _s(left.get("role")).lower() not in {"user", "human"}:
                continue
            if _s(right.get("role")).lower() not in {"assistant", "april", "bot"}:
                continue
            user = _s(left.get("content") or left.get("text"))
            answer = _s(right.get("content") or right.get("answer") or right.get("text"))
            if user and answer:
                return user, answer, right.get("turn_id") or left.get("turn_id")
    return _s(state.get("last_user_turn")), _s(state.get("last_april_turn")), None


def _continuity_measurement(
    text: str,
    state: dict[str, Any],
    history: list[Any],
) -> dict[str, Any]:
    previous_user, previous_april, turn_id = _latest_dialogue_pair(state)
    scene = state.get("current_visual_scene")
    active_topic = _s(
        (_as_dict(scene).get("topic") if isinstance(scene, dict) else "")
        or state.get("active_topic")
        or previous_user
    )
    active_goal = _s(state.get("active_goal"))
    measured = {}
    if previous_april:
        measured = QUANTUM_DIALOGUE_ENGINE.dialogue(
            text,
            previous_assistant=previous_april,
            previous_user=previous_user,
            active_goal=active_goal,
            active_topic=active_topic,
        ) or {}
    dialogue = _as_dict(measured.get("dialogue"))
    label = _s(dialogue.get("label")).lower()

    mapping = {
        "continuation": ("CONTINUATION", True, False),
        "reformulation": ("CONTINUATION", True, False),
        "correction": ("CONTINUATION", True, False),
        "reference": ("ARTIFACT_REFERENCE", True, True),
        "affirmation": ("SAME_TOPIC", True, False),
        "rejection": ("SAME_TOPIC", True, False),
        "memory_query": ("MEMORY_QUERY", True, False),
        "new_topic": ("NEW_TOPIC", False, False),
        "independent": ("INDEPENDENT", False, False),
    }
    mode, continuation, reference = mapping.get(label, ("INDEPENDENT", False, False))

    return {
        "engine": "QUANTUM_DIALOGUE_ENGINE",
        "mode": mode,
        "continuation": continuation,
        "reference_to_previous": reference,
        "previous_user": previous_user,
        "previous_april": previous_april,
        "turn_id": turn_id,
        "active_topic": active_topic,
        "active_goal": active_goal,
        "dialogue_measurement": _snapshot(measured),
        "source": "canonical_dialogue_engine",
        "lexical_triggers": False,
        "score_routing": False,
    }


def _materialize_response(value: Any) -> MachineResponse:
    if isinstance(value, MachineResponse):
        return value
    if not isinstance(value, dict):
        raise RuntimeError("Quant Test 1: Provider returned a non-object response")

    payload = dict(value)
    answer = _s(
        payload.get("answer")
        or payload.get("content")
        or payload.get("response")
        or payload.get("text")
    )
    if not answer:
        raise RuntimeError("Quant Test 1: Provider response has no answer")

    render_blocks = []
    raw_blocks = _as_list(payload.get("render_blocks") or payload.get("blocks"))
    for block in raw_blocks:
        if isinstance(block, dict):
            render_blocks.append(deepcopy(block))

    if not render_blocks:
        raise RuntimeError("Quant Test 1: Provider response has no canonical render_blocks")

    fields = MachineResponse.__dataclass_fields__
    allowed = {k: v for k, v in payload.items() if k in fields}
    allowed["answer"] = answer
    allowed["content"] = answer
    allowed["render_blocks"] = render_blocks
    allowed.setdefault("metadata", {})
    allowed["metadata"] = dict(allowed["metadata"] or {})
    return MachineResponse(**allowed)


def _requested_outputs(semantic: dict[str, Any], decision: dict[str, Any]) -> list[str]:
    names = []
    for source in (decision, semantic):
        for key in (
            "requested_outputs",
            "required_outputs",
            "required_representations",
            "requested_representations",
            "artifact_types",
            "render_types",
            "renderer_subtype",
        ):
            for value in _as_list(source.get(key)):
                item = _s(value).lower()
                if item in {"markdown", "text"}:
                    item = "text"
                if item in {"chart", "plot", "line_chart"}:
                    item = "graph"
                if item and item not in names:
                    names.append(item)
    return names or ["text"]


def _macro_budget(outputs: list[str], text: str, task_parts: int = 1) -> int:
    profiles = {
        "text": 500,
        "formula": 1300,
        "table": 1500,
        "graph": 1800,
        "diagram": 2100,
        "link": 900,
        "code": 1500,
        "gallery": 1700,
        "image": 1700,
        "audio": 1200,
        "video": 1400,
        "file": 1000,
        "action": 1000,
    }
    base = 550 + min(1600, len(text) * 7) + min(1800, max(1, task_parts) * 260)
    structured = sum(profiles.get(item, 900) for item in dict.fromkeys(outputs))
    return max(OUTPUT_MIN_TOKENS, min(OUTPUT_MAX_TOKENS, int(base + structured)))


def _build_tasks() -> tuple[QuantumTask, ...]:
    return (
        QuantumTask("t01", "context", "ingest", "context_system"),
        QuantumTask("t02", "interpretation", "semantic_measurement", "interpretation_layer"),
        QuantumTask("t03", "semantic", "semantic_measurement", "semantic_core"),
        QuantumTask("t04", "cognition", "semantic_measurement", "cognitive_core"),
        QuantumTask("t05", "intent", "intent_measurement", "intent_system"),
        QuantumTask("t06", "intent_ai", "intent_measurement", "intent_ai"),
        QuantumTask("t07", "resolver", "dialogue_measurement", "intent_resolver"),
        QuantumTask("t08", "routing", "delegation", "router"),
        QuantumTask("t09", "visual", "visual_measurement", "visual_reference_system"),
        QuantumTask("t10", "memory", "memory_measurement", "state_manager"),
        QuantumTask("t11", "experience", "feedback", "experience"),
        QuantumTask("t12", "experience_manager", "feedback", "experience_manager"),
        QuantumTask("t13", "goal", "feedback", "goal_engine"),
        QuantumTask("t14", "decision", "arbitration", "response_decision"),
        QuantumTask("t15", "energy", "budget", "energy_manager"),
        QuantumTask("t16", "presentation", "render_release", "presentation_matrix"),
    )


async def execute(
    user_id,
    chat_id=None,
    text="",
    run_with_activity=None,
    **kwargs,
):
    """
    Single public route.

    The processor itself owns the macro-matrix lifecycle. Existing April engines
    are invoked as specialized evidence producers. The final Provider and
    SceneContract path remain single and canonical.
    """
    uid = _s(user_id)
    request_text = _s(text)
    if not uid:
        raise RuntimeError("Quant Test 1: user_id missing")
    if not request_text:
        raise RuntimeError("Quant Test 1: empty request")

    state = get_state(uid)
    if not isinstance(state, dict):
        raise RuntimeError("Quant Test 1: state manager returned invalid state")
    state["user_id"] = uid
    state["_request_user_id"] = uid
    scope = _user_scope(state, uid)
    request_id = _request_id(uid, request_text)

    matrix = _matrix_shell(request_id)
    trace = QuantumTrace(
        request_id=request_id,
        version=PROCESSOR_VERSION,
        stages=["INGEST"],
        delegated_tasks=[],
        signals=[],
        feedback=[],
        collapse={},
        release={},
    )

    # ---------------------------
    # INGEST
    # ---------------------------
    history = state.get("dialog", []) if isinstance(state.get("dialog"), list) else []
    active_flow = state.get("active_flow") if isinstance(state.get("active_flow"), dict) else {}
    dialog_state = state.get("scene_state") if isinstance(state.get("scene_state"), dict) else {}

    build_deephub_context(uid, request_text, state)
    context_packet = state.get("_executor_context_packet")
    if not isinstance(context_packet, dict):
        context_packet = build_executor_context_packet(state)
    context_evidence = _as_dict(
        _as_dict(state.get("_machine_context")).get("quantum_evidence")
    )

    ingest_signal = _new_signal(
        request_id,
        "context",
        "ingest",
        "context_system",
        {
            "current_request": request_text,
            "context_packet": context_packet,
            "context_evidence": context_evidence,
            "identity_scope": scope,
            "single_route": True,
        },
    )
    trace.signals.append(asdict(ingest_signal))
    _record_cell(matrix, ingest_signal)
    trace.stages.append("MEASURE")

    # ---------------------------
    # MEASURE
    # ---------------------------
    interpretation = interpret_request(
        request_text,
        cognition=_as_dict(state.get("cognition")),
        semantic={},
        history=history,
        state=state,
    )
    if not isinstance(interpretation, dict):
        raise RuntimeError("Quant Test 1: interpretation engine returned invalid packet")

    reasoning = build_reasoning_state(
        text=request_text,
        semantic=interpretation,
        state=state,
    )

    semantic = semantic_analyze(
        text=request_text,
        state=state,
        history=history,
        active_flow=active_flow,
        dialog_state=dialog_state,
        interpreted=interpretation,
    )
    if not isinstance(semantic, dict):
        raise RuntimeError("Quant Test 1: semantic engine returned invalid packet")

    cognition = analyze_cognition(
        text=request_text,
        semantic=semantic,
        reasoning=reasoning,
        state=state,
    )
    if not isinstance(cognition, dict):
        raise RuntimeError("Quant Test 1: cognition engine returned invalid packet")

    intent = detect_intent(request_text, state)
    if not isinstance(intent, dict):
        raise RuntimeError("Quant Test 1: intent engine returned invalid packet")
    intent_ai = await detect_intent_ai(request_text, state)
    if not isinstance(intent_ai, dict):
        raise RuntimeError("Quant Test 1: intent_ai must return an object")

    resolver = resolve_input(history, state)
    if not isinstance(resolver, dict):
        raise RuntimeError("Quant Test 1: resolver returned invalid packet")
    focus_intent = build_focus_intent_state(request_text, state)
    if not isinstance(focus_intent, dict):
        raise RuntimeError("Quant Test 1: focus intent engine returned invalid packet")

    router_context = {
        "semantic": semantic,
        "cognition": cognition,
        "reasoning": reasoning,
        "response_decision": {},
        "visual_reference": {},
        "state": state,
        "quantum_evidence": {
            "context": context_evidence,
            "interpretation": interpretation,
            "intent": intent,
            "intent_ai": intent_ai,
            "resolver": resolver,
        },
    }
    router_hint = await route_request(request_text, router_context)
    if not isinstance(router_hint, dict):
        raise RuntimeError("Quant Test 1: router engine returned invalid packet")
    router_system = decide_action(request_text, history)
    if not isinstance(router_system, dict):
        raise RuntimeError("Quant Test 1: router_system returned invalid packet")

    visual = build_visual_reference(
        semantic=semantic,
        cognition=cognition,
        text=request_text,
        state=state,
    )
    if not isinstance(visual, dict):
        raise RuntimeError("Quant Test 1: visual reference engine returned invalid packet")

    experience = build_experience_evidence(
        text=request_text,
        state=state,
    )
    if not isinstance(experience, dict):
        raise RuntimeError("Quant Test 1: experience engine returned invalid packet")

    experience_state = get_experience(uid)
    if not isinstance(experience_state, dict):
        raise RuntimeError("Quant Test 1: experience manager returned invalid packet")
    experience_manager = {
        "user_id": _s(experience_state.get("user_id") or uid),
        "latest": _snapshot(experience_state.get("latest", {})),
        "has_experience": bool(experience_state.get("events")),
        "machine_only": True,
        "decision_owner": "QUANTUM_PROCESSOR",
    }

    goal = build_goal_evidence(
        text=request_text,
        state=state,
        semantic=semantic,
    )
    if not isinstance(goal, dict):
        raise RuntimeError("Quant Test 1: goal engine returned invalid packet")

    decision = build_response_decision(
        semantic=semantic,
        cognition=cognition,
        state=state,
        visual_reference=visual,
    )
    if not isinstance(decision, dict):
        raise RuntimeError("Quant Test 1: response decision engine returned invalid packet")

    dynamic_memory = query_dynamic_memory(
        uid,
        request_text,
        limit=8,
        retrieval_mode=(
            "memory_query"
            if _s(interpretation.get("dialog_act")).lower() == "memory_query"
            else "semantic"
        ),
    )
    if not isinstance(dynamic_memory, dict):
        raise RuntimeError("Quant Test 1: dynamic memory returned invalid packet")

    continuity = _continuity_measurement(
        request_text,
        state,
        history,
    )

    engine_outputs = {
        "context": context_evidence,
        "interpretation": interpretation,
        "semantic": semantic,
        "cognition": cognition,
        "intent": intent,
        "intent_ai": intent_ai,
        "resolver": {**resolver, "focus": focus_intent},
        "routing": {"router": router_hint, "router_system": router_system},
        "visual": visual,
        "memory": dynamic_memory,
        "experience": experience,
        "experience_manager": experience_manager,
        "goal": goal,
        "decision": decision,
    }

    for domain, payload in engine_outputs.items():
        lane = {
            "context": "normalize",
            "interpretation": "semantic_measurement",
            "semantic": "semantic_measurement",
            "cognition": "semantic_measurement",
            "intent": "intent_measurement",
            "intent_ai": "intent_measurement",
            "resolver": "dialogue_measurement",
            "routing": "delegation",
            "visual": "visual_measurement",
            "memory": "memory_measurement",
            "experience": "feedback",
            "experience_manager": "feedback",
            "goal": "feedback",
            "decision": "arbitration",
        }[domain]
        signal = _new_signal(
            request_id,
            domain,
            lane,
            domain,
            payload if isinstance(payload, dict) else {"value": payload},
        )
        trace.signals.append(asdict(signal))
        _record_cell(matrix, signal)

    continuity_signal = _new_signal(
        request_id,
        "semantic",
        "dialogue_measurement",
        "QUANTUM_DIALOGUE_ENGINE",
        continuity,
    )
    trace.signals.append(asdict(continuity_signal))
    _record_cell(matrix, continuity_signal)

    trace.stages.append("DELEGATE")

    # ---------------------------
    # DELEGATE
    # ---------------------------
    tasks = _build_tasks()
    for task in tasks:
        trace.delegated_tasks.append({
            "task_id": task.task_id,
            "domain": task.domain,
            "lane": task.lane,
            "engine": task.engine,
            "dependencies": list(task.dependencies),
        })
        matrix["cells"][task.domain][task.lane]["state"] = "DELEGATED"
        matrix["cells"][task.domain][task.lane]["engine"] = task.engine

    delegation_signal = _new_signal(
        request_id,
        "routing",
        "delegation",
        "QUANTUM_PROCESSOR",
        {
            "task_count": len(tasks),
            "engines": [task.engine for task in tasks],
            "single_route": True,
        },
    )
    trace.signals.append(asdict(delegation_signal))
    _record_cell(matrix, delegation_signal)

    trace.stages.append("FEEDBACK")

    # ---------------------------
    # FEEDBACK
    # ---------------------------
    required_domains = set(MACRO_DOMAINS[:14]) - {"presentation", "energy"}
    missing = sorted(domain for domain in required_domains if domain not in engine_outputs)
    if missing:
        raise RuntimeError(
            "Quant Test 1: feedback incomplete; missing evidence domains: "
            + ", ".join(missing)
        )

    contradiction_count = 0
    if continuity["mode"] in {"INDEPENDENT", "NEW_TOPIC"} and continuity["continuation"]:
        contradiction_count += 1
    if continuity["mode"] == "ARTIFACT_REFERENCE" and not continuity["reference_to_previous"]:
        contradiction_count += 1
    if contradiction_count:
        raise RuntimeError("Quant Test 1: dialogue feedback contradiction")

    feedback = {
        "evidence_domains": sorted(engine_outputs),
        "signal_count": len(trace.signals),
        "matrix_cells_measured": sum(
            1
            for domain in MACRO_DOMAINS
            for lane in PROCESS_LANES
            if matrix["cells"][domain][lane]["state"] in {"MEASURED", "DELEGATED"}
        ),
        "contradictions": contradiction_count,
        "provider_calls_so_far": 0,
        "single_route": True,
        "decision_owner": "QUANTUM_PROCESSOR",
    }
    trace.feedback.append(feedback)

    feedback_signal = _new_signal(
        request_id,
        "decision",
        "feedback",
        "QUANTUM_PROCESSOR",
        feedback,
    )
    trace.signals.append(asdict(feedback_signal))
    _record_cell(matrix, feedback_signal)

    trace.stages.append("COLLAPSE")

    # ---------------------------
    # COLLAPSE
    # ---------------------------
    outputs = _requested_outputs(semantic, decision)
    preferred = _s(
        decision.get("preferred_representation")
        or semantic.get("preferred_representation")
        or outputs[0]
    ).lower()
    if preferred not in outputs:
        preferred = outputs[0]

    mode = continuity["mode"]
    continuation = bool(continuity["continuation"])
    reference_to_previous = bool(continuity["reference_to_previous"])

    active_topic = _s(
        continuity.get("active_topic")
        or semantic.get("active_topic")
        or decision.get("active_topic")
        or request_text
    )
    active_goal = _s(
        continuity.get("active_goal")
        or decision.get("active_goal")
        or semantic.get("active_goal")
        or request_text
    )

    control_plane = {
        "version": "QTM_CONTROL_PLANE_V1",
        "decision_owner": "QUANTUM_PROCESSOR",
        "mode": mode,
        "relation": (
            "ARTIFACT_REFERENCE"
            if reference_to_previous
            else "CONTINUATION"
            if continuation
            else mode
        ),
        "continuation": continuation,
        "reference_to_previous": reference_to_previous,
        "context_dependency": continuation or reference_to_previous,
        "active_topic": active_topic,
        "active_goal": active_goal,
        "resolved_scene": (
            {
                "scene_id": _s(
                    _as_dict(state.get("current_visual_scene")).get("scene_id")
                    or _as_dict(state.get("active_visual_scene")).get("scene_id")
                ),
                "source": "QUANTUM_PROCESSOR",
            }
            if continuation or reference_to_previous
            else {}
        ),
        "requested_outputs": outputs,
        "preferred_representation": preferred,
        "capabilities": _unique_strings(
            _as_list(semantic.get("required_capabilities"))
            + _as_list(semantic.get("required_domains"))
            + _as_list(cognition.get("required_capabilities"))
            + _as_list(cognition.get("required_domains"))
        ),
        "dynamic_memory": _snapshot(dynamic_memory),
        "continuity_measurement": _snapshot(continuity),
        "single_route": True,
        "provider_calls": 1,
        "fallback": False,
    }

    trace.collapse = _snapshot(control_plane)

    collapse_signal = _new_signal(
        request_id,
        "decision",
        "arbitration",
        "QUANTUM_PROCESSOR",
        control_plane,
    )
    trace.signals.append(asdict(collapse_signal))
    _record_cell(matrix, collapse_signal)

    # ---------------------------
    # EXECUTE / canonical request
    # ---------------------------
    quantum_field = {
        "version": PROCESSOR_VERSION,
        "request_id": request_id,
        "macro_matrix": _snapshot(matrix),
        "signals": _snapshot(trace.signals),
        "engine_outputs": _snapshot(engine_outputs),
        "continuity": _snapshot(continuity),
        "control_plane": _snapshot(control_plane),
        "single_route": True,
        "provider_calls": 0,
        "decision_owner": "QUANTUM_PROCESSOR",
    }

    state["_quantum_macro_matrix"] = _snapshot(matrix)
    state["_quantum_processor_trace"] = _snapshot(asdict(trace))
    state["_quantum_evidence_field"] = _snapshot(quantum_field)

    processor_context = build_processor_execution_context({
        "state": state,
        "context": context_evidence,
        "semantic": semantic,
        "cognition": cognition,
        "interpretation": interpretation,
        "intent": intent,
        "intent_ai": intent_ai,
        "resolver": resolver,
        "router": router_hint,
        "router_system": router_system,
        "decision": decision,
        "experience": experience,
        "experience_manager": experience_manager,
        "goal": goal,
        "visual_reference": visual,
        "dynamic_memory": dynamic_memory,
        "memory_understanding": continuity,
        "control_plane": control_plane,
    })

    task_parts = len(
        _as_list(
            semantic.get("task_parts")
            or semantic.get("subtasks")
            or semantic.get("requested_tasks")
        )
    ) or 1
    response_budget = _macro_budget(outputs, request_text, task_parts)

    request = MachineRequest(
        goal=active_goal,
        intent={
            "type": _s(semantic.get("intent")) or "dialogue",
            "normalized_text": request_text,
            "dialogue_state": mode,
            "dialog_act": _s(semantic.get("dialog_act")) or "statement",
            "request_id": request_id,
        },
        conversation={
            "current_request": request_text,
            "context_mode": mode,
            "context_dependency": continuation or reference_to_previous,
            "previous_user_turn": continuity["previous_user"],
            "previous_april_turn": continuity["previous_april"],
            "resolved_scene": control_plane["resolved_scene"],
            "active_topic": active_topic if mode != "INDEPENDENT" else "",
            "active_goal": active_goal if mode != "INDEPENDENT" else "",
        },
        memory={
            "active_topic": active_topic,
            "active_goal": active_goal,
            "active_scene_id": _s(control_plane["resolved_scene"].get("scene_id")),
            "retrieval_mode": "memory_query" if mode == "MEMORY_QUERY" else "semantic",
            "dynamic_memory": _snapshot(dynamic_memory),
        },
        visual_context=(
            _snapshot(visual)
            if mode in {"CONTINUATION", "SAME_TOPIC", "ARTIFACT_REFERENCE", "MEMORY_QUERY"}
            else {}
        ),
        available_tools=list(control_plane["capabilities"]),
        requested_outputs=outputs,
        required_competencies=list(control_plane["capabilities"]),
        required_artifacts=outputs,
        routing={
            "single_route": True,
            "processor": PROCESSOR_VERSION,
            "request_id": request_id,
        },
        constraints={
            "one_provider_call": True,
            "one_visible_answer": True,
            "canonical_scene": True,
            "provider_input_token_budget": 900,
            "current_request_must_remain_intact": True,
            "identity_scope": deepcopy(scope),
            "macro_matrix": {
                "dimensions": [len(MACRO_DOMAINS), len(PROCESS_LANES)],
                "signal_cells": MACRO_SIGNAL_COUNT,
                "version": "QTM16X16",
            },
            "quantum_processor": {
                "version": PROCESSOR_VERSION,
                "request_id": request_id,
                "control_plane": _snapshot(control_plane),
                "processor_context": _snapshot(processor_context),
                "evidence_field": _snapshot(quantum_field),
            },
            "representation_plan": {
                "requested_outputs": outputs,
                "preferred_representation": preferred,
                "current_request_authoritative": True,
                "source": "QUANTUM_PROCESSOR",
            },
            "metadata": {
                "processor_version": PROCESSOR_VERSION,
                "request_id": request_id,
                "identity_scope": deepcopy(scope),
                "single_route": True,
                "provider_calls_per_request": 1,
            },
        },
    )

    request.response_complexity = _s(
        semantic.get("response_complexity")
        or cognition.get("response_complexity")
        or decision.get("response_complexity")
        or "ADAPTIVE"
    )
    request.response_output_tokens = response_budget
    request.max_output_tokens = response_budget
    request.quantum_state = {
        "version": PROCESSOR_VERSION,
        "request_id": request_id,
        "macro_matrix": {
            "macro_domains": len(MACRO_DOMAINS),
            "process_lanes": len(PROCESS_LANES),
            "signal_count": MACRO_SIGNAL_COUNT,
        },
        "evidence_channels": len(engine_outputs),
        "control_plane": _snapshot(control_plane),
        "continuity": _snapshot(continuity),
        "response_budget": response_budget,
        "single_route": True,
        "provider_calls_allowed": 1,
        "decision_owner": "QUANTUM_PROCESSOR",
    }
    request.dialogue_contract = {
        "continuation": continuation,
        "reference_to_previous": reference_to_previous,
        "context_dependency": "reference" if reference_to_previous else "continuation" if continuation else "independent",
        "previous_user_turn": continuity["previous_user"],
        "previous_april_turn": continuity["previous_april"],
        "active_topic": active_topic,
        "active_goal": active_goal,
        "current_request": request_text,
        "resolved_scene": control_plane["resolved_scene"],
    }
    request.response_decision = decision
    request.single_route = True
    request.provider_calls_allowed = 1

    energy_profile = build_quantum_acceleration_profile(
        uid,
        flow_id=_s(state.get("flow_id")),
        semantic=semantic,
        cognition=cognition,
        decision=decision,
        state=state,
        outputs=outputs,
        visual=visual,
    )
    request = apply_quantum_acceleration(request, energy_profile)
    acceleration_check = validate_quantum_acceleration(request, energy_profile)
    if not acceleration_check.get("ok"):
        raise RuntimeError("Quant Test 1: energy acceleration invariant failed")

    _validate_request(request)

    trace.stages.append("PROVIDER")

    # ---------------------------
    # ONE PROVIDER CALL
    # ---------------------------
    provider_result = await generate_text(
        request,
        max_output_tokens=request.response_output_tokens,
    )
    response = _materialize_response(provider_result)

    if not response.answer and not response.content:
        raise RuntimeError("Quant Test 1: empty Provider response")

    trace.stages.append("ARTIFACT_CONTRACT")

    # ---------------------------
    # SINGLE C-Artifact / SceneContract route
    # ---------------------------
    response.metadata = dict(response.metadata or {})
    response.metadata.update({
        "processor_version": PROCESSOR_VERSION,
        "request_id": request_id,
        "single_route": True,
        "provider_calls_per_request": 1,
        "decision_owner": "QUANTUM_PROCESSOR",
        "macro_matrix_signal_cells": MACRO_SIGNAL_COUNT,
        "quantum_trace": _snapshot(asdict(trace)),
    })

    scene = build_machine_scene(response)
    scene.blocks = list(getattr(response, "render_blocks", []) or [])
    scene.contract.blocks = list(getattr(response, "render_blocks", []) or [])
    contract = build_scene_contract(scene)

    answer = _s(response.answer or response.content)
    if not answer:
        raise RuntimeError("Quant Test 1: canonical answer release failed")

    try:
        contract.answer = answer
        contract.content = answer
        contract.summary = response.summary
        contract.render_blocks = list(getattr(response, "render_blocks", []) or [])
        contract.blocks = list(getattr(response, "render_blocks", []) or [])
    except Exception as exc:
        raise RuntimeError(
            "Quant Test 1: SceneContract canonical field assignment failed"
        ) from exc

    trace.release = {
        "scene_contract": True,
        "answer_present": True,
        "render_block_count": len(getattr(contract, "render_blocks", []) or []),
        "provider_calls": 1,
        "single_route": True,
    }

    release_signal = _new_signal(
        request_id,
        "presentation",
        "render_release",
        "SCENE_CONTRACT",
        trace.release,
    )
    trace.signals.append(asdict(release_signal))
    _record_cell(matrix, release_signal, state="RELEASED")

    trace.stages.append("RELEASE")

    # Persist final trace only after a successful release.
    state["_quantum_processor_trace"] = _snapshot(asdict(trace))
    state["_quantum_macro_matrix"] = _snapshot(matrix)

    update_dialog_context(uid, semantic)
    update_scene_context(
        uid,
        contract,
        current_request=request_text,
        answer=answer,
        internal_context=bool(kwargs.get("internal_context")),
    )

    return {
        "transport_contract": "scene_first",
        "provider_contract": "fiber_v3_quantum",
        "machine_request": request,
        "machine_response": response,
        "machine_scene": scene,
        "scene_contract": contract,
        "answer": answer,
        "content": answer,
        "summary": response.summary,
        "render_blocks": list(getattr(contract, "render_blocks", []) or []),
        "artifacts": list(getattr(response, "artifacts", []) or []),
        "single_route": True,
        "provider_calls_per_request": 1,
        "quantum_state": request.quantum_state,
        "energy_acceleration": request.constraints.get("energy_acceleration", {}),
        "identity_scope": deepcopy(scope),
        "quantum_trace": _snapshot(asdict(trace)),
        "quantum_macro_matrix": _snapshot(matrix),
        "processor_version": PROCESSOR_VERSION,
    }


def _validate_request(request: MachineRequest) -> None:
    constraints = _as_dict(getattr(request, "constraints", {}))
    if constraints.get("one_provider_call") is not True:
        raise RuntimeError("Quant Test 1: one_provider_call invariant failed")
    if constraints.get("provider_input_token_budget") != 900:
        raise RuntimeError("Quant Test 1: provider input budget invariant failed")
    if getattr(request, "provider_calls_allowed", 1) != 1:
        raise RuntimeError("Quant Test 1: provider call count invariant failed")
    if getattr(request, "single_route", True) is not True:
        raise RuntimeError("Quant Test 1: single route invariant failed")
    budget = getattr(request, "response_output_tokens", 0)
    if not isinstance(budget, int):
        raise RuntimeError("Quant Test 1: response budget is not integer")
    if not OUTPUT_MIN_TOKENS <= budget <= OUTPUT_MAX_TOKENS:
        raise RuntimeError("Quant Test 1: response budget range invariant failed")
    matrix = _as_dict(constraints.get("macro_matrix"))
    if matrix.get("signal_cells") != MACRO_SIGNAL_COUNT:
        raise RuntimeError("Quant Test 1: macro matrix invariant failed")
    metadata = _as_dict(constraints.get("metadata"))
    identity_scope = _as_dict(metadata.get("identity_scope"))
    if not identity_scope.get("user_id"):
        raise RuntimeError("Quant Test 1: identity scope invariant failed")


__all__ = [
    "PROCESSOR_VERSION",
    "MACRO_DOMAINS",
    "PROCESS_LANES",
    "MACRO_SIGNAL_COUNT",
    "QuantumSignal",
    "QuantumTask",
    "QuantumTrace",
    "execute",
]

