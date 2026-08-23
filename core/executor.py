"""April Quantum Processor — balanced single-route executor.

This is a quantum-inspired processor, not a physical quantum computer.
It evaluates many independent evidence channels, fuses them multiplicatively,
then collapses them to ONE dialogue state, ONE request and ONE scene contract.
There is exactly one Provider call per user turn.
"""
from __future__ import annotations

import ast
import json
import re
import hashlib
from copy import deepcopy
from typing import Any

from blocks.context_system import build_deephub_context, build_executor_context_packet
from blocks.interpretation_layer import (
    interpret_request,
    build_processor_execution_context,
    QUANTUM_EVIDENCE_FUSION,
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
from blocks.state_manager import get_state, update_dialog_context, update_scene_context, query_dynamic_memory
from blocks.C_ARTIFACT_CONTRACT import MachineRequest, MachineResponse, build_machine_scene, build_scene_contract
from blocks.provider_router import generate_text
from blocks.energy_manager import (build_quantum_acceleration_profile, apply_quantum_acceleration, validate_quantum_acceleration)
from blocks.april_personality import APRIL_IDENTITY

PROCESSOR_VERSION = "april_quantum_processor_quantum64_v26_user_scoped_scene_presentation_matrix"
SINGLE_ROUTE = True
PROVIDER_CALLS = 1
OUTPUT_MIN_TOKENS = 1
OUTPUT_MAX_TOKENS = 8000

# Canonical structural dimensions of the single processor matrix.
# These are fixed engine dimensions, not routing triggers or score thresholds.
QUANTUM_CORE_COUNT = 8
QUANTUM_LANE_COUNT = 8
QUANTUM_CORES = tuple(f"core_{i+1}" for i in range(QUANTUM_CORE_COUNT))
QUANTUM_LANES = tuple(f"lane_{i+1}" for i in range(QUANTUM_LANE_COUNT))

def _quantum_snapshot(value: Any, _active: set[int] | None = None) -> Any:
    """
    Convert runtime evidence into a detached, JSON-safe snapshot.

    Quantum evidence may contain shared references because multiple engines
    contribute the same dicts. Shared references are fine; live back-references
    are not. This helper detaches every branch so the persisted user state
    cannot become a self-referential object graph.
    """
    active = _active if _active is not None else set()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    oid = id(value)
    if oid in active:
        return {"__cycle__": True}
    if isinstance(value, dict):
        active.add(oid)
        try:
            result = {
                str(k): _quantum_snapshot(v, active)
                for k, v in value.items()
            }
        finally:
            active.remove(oid)
        return result
    if isinstance(value, (list, tuple, set)):
        active.add(oid)
        try:
            result = [_quantum_snapshot(v, active) for v in value]
        finally:
            active.remove(oid)
        return result
    # Runtime objects are not allowed into canonical state/evidence.
    return _s(value)

def _s(v: Any) -> str:
    return str(v or "").strip()

def _clip(v: Any, n: int = 900) -> str:
    s = _s(v)
    return s if len(s) <= n else s[-n:]

def _tokens(v: Any) -> set[str]:
    return set(re.findall(r"[\wА-Яа-яЁё]+", _s(v).lower()))

def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}

def _as_list(value: Any) -> list:
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return []

def _unique_strings(values: Any) -> list[str]:
    result: list[str] = []
    for value in _as_list(values):
        value = _s(value).lower()
        if value and value not in result:
            result.append(value)
    return result


def _user_scope(state: dict, user_id: Any) -> dict:
    """Canonical identity scope carried through the one route and scene contract."""
    uid = _s(user_id)
    if not uid:
        raise RuntimeError("Quantum release blocked: authenticated user_id missing")

    conversation_id = _s(
        state.get("conversation_id")
        or state.get("memory_scope", {}).get("conversation_id")
        or ""
    )
    if not conversation_id:
        conversation_id = f"april-{hashlib.sha256(uid.encode("utf-8")).hexdigest()[:24]}"
        state["conversation_id"] = conversation_id

    scope = {
        "user_id": uid,
        "conversation_id": conversation_id,
        "identity_bound": True,
        "scope_version": "USER_SCOPED_SCENE_V1",
    }
    state["memory_scope"] = dict(scope)
    return scope

def _merge_evidence_fields(target: dict, sources: tuple[dict, ...]) -> dict:
    """
    Merge only machine evidence into the canonical semantic packet.

    Current request and authoritative semantic fields are never replaced.
    Multi-valued representation/capability evidence is unioned. Scalar
    signals are retained under quantum_evidence_sources so no room can
    overwrite another room's signal.
    """
    target = _as_dict(target)
    representations: list[str] = []
    domains: list[str] = []
    capabilities: list[str] = []
    candidates: list[dict] = []

    for source in sources:
        source = _as_dict(source)
        for key in (
            "required_representations", "candidate_representations",
            "requested_outputs", "required_outputs", "render_types",
            "artifact_types", "representations",
        ):
            for value in _as_list(source.get(key)):
                name = _s(value).lower()
                if name and name not in representations:
                    representations.append(name)
        for key in ("required_domains", "candidate_domains", "required_competencies"):
            for value in _as_list(source.get(key)):
                name = _s(value).lower()
                if name and name not in domains:
                    domains.append(name)
        for key in ("required_capabilities", "available_tools"):
            for value in _as_list(source.get(key)):
                name = _s(value).lower()
                if name and name not in capabilities:
                    capabilities.append(name)
        for item in _as_list(source.get("candidate_signals")):
            if isinstance(item, dict):
                candidates.append(dict(item))

    if representations:
        target["required_representations"] = _unique_strings(
            _as_list(target.get("required_representations")) + representations
        )
        target["candidate_representations"] = _unique_strings(
            _as_list(target.get("candidate_representations")) + representations
        )
    if domains:
        target["required_domains"] = _unique_strings(
            _as_list(target.get("required_domains")) + domains
        )
        target["candidate_domains"] = _unique_strings(
            _as_list(target.get("candidate_domains")) + domains
        )
    if capabilities:
        target["required_capabilities"] = _unique_strings(
            _as_list(target.get("required_capabilities")) + capabilities
        )

    target["quantum_candidate_signals"] = candidates
    return target

def _build_quantum_field(
    *,
    user_id: Any,
    text: str,
    state: dict,
    context: dict,
    interpretation: dict,
    semantic: dict,
    cognition: dict,
    intent: dict,
    intent_ai: dict,
    resolver: dict,
    router: dict,
    router_system: dict,
    decision: dict,
    experience: dict,
    experience_manager: dict,
    goal: dict,
    visual_reference: dict,
) -> dict:
    """Build the one canonical evidence field for Quantum collapse."""
    return {
        "version": PROCESSOR_VERSION,
        "user_id": _s(user_id),
        "current_request": _s(text),
        "current_request_authoritative": True,
        "decision_owner": "QUANTUM_PROCESSOR",
        "identity_scope": _quantum_snapshot(state.get("memory_scope", {})),
        "single_route": True,
        "provider_calls": 0,
        "parallel_route": False,
        "sources": {
            "context_system": _quantum_snapshot(_as_dict(context)),
            "interpretation_layer": _quantum_snapshot(_as_dict(interpretation)),
            "semantic_core": _quantum_snapshot(_as_dict(semantic)),
            "cognitive_core": _quantum_snapshot(_as_dict(cognition)),
            "intent_system": _quantum_snapshot(_as_dict(intent)),
            "intent_ai": _quantum_snapshot(_as_dict(intent_ai)),
            "intent_resolver": _quantum_snapshot(_as_dict(resolver)),
            "router": _quantum_snapshot(_as_dict(router)),
            "router_system": _quantum_snapshot(_as_dict(router_system)),
            "response_decision": _quantum_snapshot(_as_dict(decision)),
            "experience": _quantum_snapshot(_as_dict(experience)),
            "experience_manager": _quantum_snapshot(_as_dict(experience_manager)),
            "goal_engine": _quantum_snapshot(_as_dict(goal)),
            "visual_reference_system": _quantum_snapshot(_as_dict(visual_reference)),
        },
        "evidence_channels": 14,
        "representations": _unique_strings(
            _as_list(semantic.get("required_representations"))
            + _as_list(interpretation.get("required_representations"))
            + _as_list(intent.get("renderer_subtype"))
            + _as_list(decision.get("required_representations"))
        ),
        "candidate_signals": _quantum_snapshot(
            _as_list(intent.get("candidate_signals"))
            + _as_list(intent_ai.get("quantum_evidence", {}).get("candidates"))
            + _as_list(router.get("quantum_evidence", {}).get("signals"))
            + _as_list(router_system.get("candidate_signals"))
        ),
        "semantic_engines": {
            "dialogue": _quantum_snapshot(
                semantic.get("quantum_dialogue_measurement", {})
            ),
            "representation": _quantum_snapshot(
                semantic.get("quantum_representation_measurement", {})
            ),
            "representation_candidates": _quantum_snapshot(
                semantic.get("quantum_representation_candidates", [])
            ),
            "decision_owner": "QUANTUM_PROCESSOR",
            "word_trigger_routing": False,
            "fallback_semantics": False,
        },
        "trajectory": _quantum_snapshot({
            "resolver": _as_dict(resolver),
            "active_flow": _as_dict(state.get("active_flow")),
            "context": _as_dict(context.get("quantum_evidence")),
        }),
        "arbitration": {
            "dialogue": "processor",
            "representation": "processor",
            "room": "delegated",
            "renderer": "delegated",
            "execution": "delegated",
        },
    }

def _field(sources: tuple[dict, ...], names: tuple[str, ...]) -> Any:
    for src in sources:
        if not isinstance(src, dict):
            continue
        for name in names:
            if src.get(name) not in (None, "", [], {}):
                return src[name]
    return ""


def _dialogue_evidence(
    text: str,
    semantic: dict,
    cognition: dict,
    decision: dict,
    state: dict,
) -> dict:
    """Read the already-measured dialogue contract without local trigger rules or score thresholds.

    The Executor does not score the dialog itself. It accepts the semantic engines'
    structured interpretation and only materializes one canonical state.
    """
    dialog = state.get("dialog", []) if isinstance(state, dict) else []
    previous_user = ""
    previous_april = ""
    last_turn_id = None

    for item in reversed(dialog):
        if not isinstance(item, dict):
            continue
        role = _s(item.get("role")).lower()
        if not previous_april:
            if role in {"assistant", "april"}:
                previous_april = _s(
                    item.get("content")
                    or item.get("answer")
                )
                last_turn_id = item.get("turn_id")
            elif isinstance(item.get("april"), dict):
                previous_april = _s(
                    item["april"].get("answer")
                    or item["april"].get("content")
                )
                last_turn_id = item.get("turn_id")
        if not previous_user:
            if role == "user":
                previous_user = _s(item.get("content"))
            elif item.get("user"):
                previous_user = _s(item.get("user"))
        if previous_user and previous_april:
            break

    # Web-only canonical route may not have a hot dialog list yet. The current
    # USER↔APRIL scene is therefore the authoritative immediate history fallback.
    current_scene = state.get("current_visual_scene") or state.get("active_visual_scene")
    if isinstance(current_scene, dict):
        if not previous_user:
            previous_user = _s(
                current_scene.get("user_request")
                or current_scene.get("current_request")
            )
        if not previous_april:
            previous_april = _s(
                current_scene.get("april_answer")
                or current_scene.get("answer")
                or current_scene.get("summary")
            )
        if not last_turn_id:
            last_turn_id = current_scene.get("turn_id")

    interpretation_packet = _as_dict(semantic.get("quantum_interpretation_evidence"))
    dialogue_contract = _as_dict(interpretation_packet.get("dialogue_contract"))
    if not dialogue_contract:
        dialogue_contract = _as_dict(
            semantic.get("dialogue_context_field")
        )

    mode = _s(
        dialogue_contract.get("context_mode")
        or dialogue_contract.get("dialogue_state")
        or semantic.get("dialogue_state")
        or decision.get("dialogue_state")
    ).upper()

    if mode not in {
        "INDEPENDENT",
        "NEW_TOPIC",
        "SAME_TOPIC",
        "CONTINUATION",
        "ARTIFACT_REFERENCE",
        "MEMORY_QUERY",
    }:
        mode = (
            "MEMORY_QUERY" if dialogue_contract.get("dialog_act") == "memory_query"
            else "CONTINUATION" if bool(dialogue_contract.get("continuation"))
            else "INDEPENDENT"
        )

    active_topic = _s(
        dialogue_contract.get("active_topic")
        or semantic.get("active_topic")
        or decision.get("active_topic")
        or state.get("active_topic")
        or state.get("topic")
    )
    active_goal = _s(
        dialogue_contract.get("active_goal")
        or semantic.get("active_goal")
        or cognition.get("active_goal")
        or decision.get("active_goal")
        or state.get("active_goal")
    )

    context_dependency = bool(
        dialogue_contract.get("context_dependency")
        and _s(dialogue_contract.get("context_dependency")).lower() not in {"independent", "none", "false", "0"}
    )
    continuation = bool(dialogue_contract.get("continuation"))
    reference_to_previous = bool(dialogue_contract.get("reference_to_previous"))

    if context_dependency:
        if _s(dialogue_contract.get("dialog_act")).lower() == "memory_query":
            mode = "MEMORY_QUERY"
        elif reference_to_previous:
            mode = "ARTIFACT_REFERENCE" if mode == "ARTIFACT_REFERENCE" else "CONTINUATION"
        elif continuation:
            mode = "CONTINUATION"
        elif mode == "INDEPENDENT":
            mode = "SAME_TOPIC"

    if not dialog and mode not in {"INDEPENDENT", "MEMORY_QUERY"}:
        mode = "INDEPENDENT"
        context_dependency = False
        continuation = False
        reference_to_previous = False

    return {
        "mode": mode,
        "previous_user": previous_user,
        "previous_april": previous_april,
        "last_turn_id": last_turn_id,
        "active_topic": active_topic,
        "active_goal": active_goal,
        "context_dependency": context_dependency,
        "continuation": continuation,
        "reference_to_previous": reference_to_previous,
        "dialog_act": _s(
            dialogue_contract.get("dialog_act")
            or semantic.get("dialog_act")
            or decision.get("dialog_act")
            or "statement"
        ),
        "reply_to": _s(
            dialogue_contract.get("reply_to")
            or dialogue_contract.get("previous_turn_id")
        ),
    }


def _collapse_dialogue(e: dict[str, Any]) -> tuple[str, dict[str, float], float]:
    """Compatibility bridge: no local score collapse; semantic engines own the state."""
    mode = _s(e.get("mode")).upper() or "INDEPENDENT"
    states = {
        "INDEPENDENT": 1.0 if mode == "INDEPENDENT" else 0.0,
        "NEW_TOPIC": 1.0 if mode == "NEW_TOPIC" else 0.0,
        "SAME_TOPIC": 1.0 if mode == "SAME_TOPIC" else 0.0,
        "CONTINUATION": 1.0 if mode == "CONTINUATION" else 0.0,
        "ARTIFACT_REFERENCE": 1.0 if mode == "ARTIFACT_REFERENCE" else 0.0,
        "MEMORY_QUERY": 1.0 if mode == "MEMORY_QUERY" else 0.0,
    }
    return mode, states, 1.0


def _representation_constraints(*sources: dict) -> dict:
    """Merge explicit representation constraints without local scoring or triggers."""
    positive: list[str] = []
    negative: list[str] = []

    for src in sources:
        if not isinstance(src, dict):
            continue
        constraints = src.get("representation_constraints")
        if isinstance(constraints, dict):
            for key, target in (("positive", positive), ("negative", negative)):
                values = constraints.get(key) or []
                if isinstance(values, str):
                    values = [values]
                for value in values:
                    name = _s(value).lower()
                    if name and name not in target:
                        target.append(name)

        preferred = _s(src.get("preferred_representation")).lower()
        if preferred and preferred not in positive:
            positive.append(preferred)

        authority = _s(src.get("representation_authority")).lower()
        if authority and authority not in {"", "adaptive"} and authority not in positive:
            positive.append(authority)

    blocked = set(negative)
    positive = [item for item in positive if item not in blocked]

    return {
        "positive": positive,
        "negative": negative,
        "blocked": sorted(blocked),
        "current_request_authoritative": True,
    }

def _representation_audit(
    requested_outputs: list[str],
    measured_output: str,
    constraints: dict,
) -> dict:
    requested = list(dict.fromkeys(requested_outputs or []))
    blocked = set(constraints.get("negative", []) or [])
    return {
        "requested_outputs": requested,
        "preferred_representation": measured_output,
        "blocked_outputs": sorted(blocked),
        "multi_output": len(requested) > 1,
        "table_requested": "table" in requested,
        "graph_requested": "graph" in requested,
        "code_requested": "code" in requested,
        "representation_gap": bool(requested and not set(requested).issubset(blocked | set(requested))),
        "canonical": True,
    }


def _requested_outputs(
    text: str,
    semantic: dict,
    cognition: dict,
    decision: dict,
    *,
    independent_turn: bool = False,
) -> list[str]:
    """Preserve the processor's measured representation plan; no trigger/score routing."""
    constraints = _representation_constraints(semantic, cognition, decision)
    blocked = set(constraints["negative"])
    names: list[str] = []

    def add(value: Any) -> None:
        values = [value] if isinstance(value, str) else list(value) if isinstance(value, (list, tuple, set)) else []
        for raw in values:
            name = _s(raw).lower()
            aliases = {
                "markdown": "text",
                "renderer_scene": "diagram",
                "visual": "graph",
                "image_generate": "image",
            }
            name = aliases.get(name, name)
            if name and name not in blocked and name not in names:
                names.append(name)

    # Explicit current-turn outputs are authoritative.
    for src in (decision, semantic):
        if not isinstance(src, dict):
            continue
        add(src.get("requested_outputs"))
        add(src.get("required_outputs"))

    # Explicit structured constraints come next.
    add(constraints["positive"])

    # For independent turns, stale inherited output plans are deliberately not
    # reused; current semantic/decision output evidence remains authoritative.
    if not names:
        for src in (semantic, cognition, decision):
            if not isinstance(src, dict):
                continue
            for key in (
                "required_representations",
                "requested_representations",
                "candidate_representations",
                "artifact_types",
                "render_types",
                "representations",
            ):
                add(src.get(key))
        add(src.get("preferred_representation") if isinstance(src, dict) else "")

    if "text" not in names:
        names.insert(0, "text")

    # Preserve the current plan as a full multi-output set; never collapse it to
    # one representation.
    return names or ["text"]


def _representation_consensus(
    outputs: list[str],
    semantic: dict,
    decision: dict,
) -> tuple[str, dict[str, Any]]:
    """Select the declared preferred representation without local scoring."""
    plan = list(dict.fromkeys(outputs or ["text"]))
    preferred = _s(
        decision.get("preferred_representation")
        or semantic.get("preferred_representation")
        or (plan[0] if plan else "text")
    ).lower()
    if preferred not in plan:
        preferred = plan[0] if plan else "text"

    return preferred, {
        "outputs": plan,
        "preferred": preferred,
        "selection_method": "declared_semantic_plan",
        "scoring": False,
        "triggers": False,
    }


def _complexity(
    semantic: dict,
    cognition: dict,
    decision: dict,
    text: str,
) -> str:
    """Carry the semantic complexity declaration without local score tiers."""
    explicit = _s(
        semantic.get("response_complexity")
        or cognition.get("response_complexity")
        or decision.get("response_complexity")
    ).upper()
    return explicit if explicit in {"LOW", "MEDIUM", "HIGH"} else "ADAPTIVE"

def _quantum_64_field(
    text: str,
    semantic: dict,
    cognition: dict,
    decision: dict,
) -> dict:
    """Build a 64-lane structural measurement field without score weighting or triggers."""
    outputs = list(dict.fromkeys(
        _as_list(
            semantic.get("requested_outputs")
            or semantic.get("required_outputs")
            or decision.get("requested_outputs")
        )
    ))
    artifacts = _as_list(
        semantic.get("required_artifacts")
        or decision.get("required_artifacts")
    )
    domains = _as_list(
        semantic.get("required_domains")
        or semantic.get("required_competencies")
        or cognition.get("required_domains")
    )
    parts = max(1, len(
        semantic.get("task_parts")
        or semantic.get("subtasks")
        or semantic.get("requested_tasks")
        or []
    ))
    word_count = len(_tokens(text))

    field = {
        "meaning": {
            "request_length": word_count,
            "has_context": bool(semantic.get("active_topic") or semantic.get("context")),
            "has_goal": bool(semantic.get("active_goal") or decision.get("active_goal")),
            "semantic_state": _s(semantic.get("dialogue_state") or semantic.get("dialog_act")),
            "declared_complexity": _complexity(semantic, cognition, decision, text),
            "measured": True,
            "source": "semantic_engines",
            "scoring": False,
            "triggering": False,
        },
        "intent": {
            "intent": _s(semantic.get("intent") or decision.get("intent")),
            "dialogue_state": _s(semantic.get("dialogue_state")),
            "dialog_act": _s(semantic.get("dialog_act") or decision.get("dialog_act")),
            "goal_present": bool(decision.get("active_goal") or semantic.get("active_goal")),
            "measured": True,
            "scoring": False,
            "triggering": False,
        },
        "context": {
            "history_present": bool(semantic.get("history_present")),
            "continuation": bool(semantic.get("continuation")),
            "reference_to_previous": bool(semantic.get("reference_to_previous")),
            "context_dependency": bool(semantic.get("context_dependency")),
            "topic": _s(semantic.get("active_topic") or decision.get("active_topic")),
            "goal": _s(semantic.get("active_goal") or decision.get("active_goal")),
            "measured": True,
            "scoring": False,
            "triggering": False,
        },
        "structure": {
            "requested_outputs": outputs,
            "artifact_types": list(dict.fromkeys(map(_s, artifacts))),
            "domains": list(dict.fromkeys(map(_s, domains))),
            "task_parts": parts,
            "word_count": word_count,
            "measured": True,
            "scoring": False,
            "triggering": False,
        },
        "evidence": {
            "semantic_evidence_present": bool(semantic),
            "cognition_evidence_present": bool(cognition),
            "decision_evidence_present": bool(decision),
            "measured": True,
            "scoring": False,
            "triggering": False,
        },
        "representation": {
            "requested_outputs": outputs or ["text"],
            "preferred": _s(
                decision.get("preferred_representation")
                or semantic.get("preferred_representation")
                or "text"
            ),
            "constraints": _representation_constraints(semantic, cognition, decision),
            "measured": True,
            "scoring": False,
            "triggering": False,
        },
        "economy": {
            "input_text_chars": len(text),
            "word_count": word_count,
            "requested_output_count": len(outputs),
            "artifact_count": len(artifacts),
            "domain_count": len(domains),
            "measured": True,
            "scoring": False,
            "triggering": False,
        },
        "completion": {
            "requested_output_count": len(outputs),
            "artifact_count": len(artifacts),
            "task_parts": parts,
            "measured": True,
            "scoring": False,
            "triggering": False,
        },
    }

    return {
        "cores": field,
        "core_count": QUANTUM_CORE_COUNT,
        "lane_count": QUANTUM_LANE_COUNT,
        "signal_count": QUANTUM_CORE_COUNT * QUANTUM_LANE_COUNT,
        "measurement_mode": "structural_no_trigger_no_score",
        "request_word_count": word_count,
        "requested_output_count": len(outputs),
        "artifact_count": len(artifacts),
        "domain_count": len(domains),
        "task_parts": parts,
        "scoring": False,
        "triggering": False,
    }


def _quantum_budget_from_64(
    field: dict,
    *,
    minimum: int = OUTPUT_MIN_TOKENS,
    maximum: int = OUTPUT_MAX_TOKENS,
) -> int:
    """Estimate output capacity from explicit structural workload, not scores."""
    cores = field.get("cores", {}) if isinstance(field, dict) else {}
    economy = cores.get("economy", {}) if isinstance(cores, dict) else {}
    structure = cores.get("structure", {}) if isinstance(cores, dict) else {}
    completion = cores.get("completion", {}) if isinstance(cores, dict) else {}

    word_count = max(1, int(economy.get("word_count", field.get("request_word_count", 1)) or 1))
    output_count = max(1, int(
        economy.get("requested_output_count", field.get("requested_output_count", 1)) or 1
    ))
    artifact_count = max(0, int(
        economy.get("artifact_count", field.get("artifact_count", 0)) or 0
    ))
    domain_count = max(0, int(
        economy.get("domain_count", field.get("domain_count", 0)) or 0
    ))
    parts = max(1, int(
        structure.get("task_parts", field.get("task_parts", 1)) or 1
    ))

    # Capacity is a direct structural measurement:
    # text length + number of requested outputs + artifacts + domains + task parts.
    # There are no tiers, triggers, weights, probabilities, or score cutoffs.
    budget = (
        96
        + (word_count * 3)
        + (output_count * 640)
        + (artifact_count * 480)
        + (domain_count * 160)
        + (parts * 320)
    )

    # Extra representation reserve is proportional to actual declared
    # structured outputs, not to a score.
    structured_outputs = sum(
        1 for item in _as_list(structure.get("requested_outputs"))
        if _s(item).lower() not in {"", "text", "markdown"}
    )
    budget += structured_outputs * 720

    return int(max(minimum, min(maximum, budget)))


def _adaptive_output_budget(
    text: str,
    semantic: dict,
    cognition: dict,
    decision: dict,
) -> int:
    """Continuous structural capacity calculation with no trigger/scoring logic."""
    field = _quantum_64_field(text, semantic, cognition, decision)
    return _quantum_budget_from_64(field)

def _compact_context(text: str, state: dict, mode: str, topic: str, goal: str) -> dict:
    dialog = state.get("dialog", []) if isinstance(state, dict) else []
    recent = []
    for turn in dialog[-8:]:
        if not isinstance(turn, dict):
            continue
        role = _s(turn.get("role")).lower()
        if role == "user":
            recent.append({
                "user": _clip(turn.get("content"), 450),
                "april": "",
            })
        elif role in {"assistant", "april"}:
            recent.append({
                "user": "",
                "april": _clip(
                    turn.get("content")
                    or turn.get("answer")
                    or turn.get("summary"),
                    700,
                ),
            })
        else:
            recent.append({
                "user": _clip(turn.get("user"), 450),
                "april": _clip(
                    (turn.get("april") or {}).get("answer")
                    if isinstance(turn.get("april"), dict)
                    else turn.get("april") or turn.get("content", ""),
                    700,
                ),
            })
    data = {"current_request": text, "context_mode": mode}
    if mode != "INDEPENDENT":
        if topic: data["active_topic"] = _clip(topic, 300)
        if goal: data["active_goal"] = _clip(goal, 500)
        data["recent_dialogue"] = recent
    if mode == "ARTIFACT_REFERENCE":
        visual = None
        if isinstance(state.get("active_scene_contract"), dict):
            visual = state.get("active_scene_contract")
        if not visual:
            visual = state.get("active_visual_scene") or state.get("visual_summary")
        if visual:
            data["visual_context"] = _clip(visual, 900)
    return data



def _build_processor_control_plane(
    *,
    text: str,
    semantic: dict,
    cognition: dict,
    decision: dict,
    state: dict,
    dynamic_memory: dict | None = None,
) -> dict:
    """
    Build ONE authoritative post-interpretation control plane.

    Authority:
      dialogue/context -> canonical Interpretation dialogue_contract
      representation   -> current semantic/decision plan
      capabilities     -> semantic/cognition union
      memory           -> already queried dynamic memory
      presentation     -> produced only after Provider response

    Other engines contribute evidence; this function collapses their compatible
    signals into one executable state. It does not invent a second route,
    trigger map, or score-based arbitration.
    """
    evidence = _dialogue_evidence(text, semantic, cognition, decision, state)
    interpretation_packet = _as_dict(semantic.get("quantum_interpretation_evidence"))
    canonical_dialogue = _as_dict(
        interpretation_packet.get("dialogue_contract")
        or semantic.get("dialogue_context_field")
    )

    mode = _s(evidence.get("mode")).upper() or "INDEPENDENT"
    continuation = bool(evidence.get("continuation"))
    reference_to_previous = bool(evidence.get("reference_to_previous"))
    context_dependency = bool(evidence.get("context_dependency"))

    resolved_scene = _as_dict(canonical_dialogue.get("resolved_scene"))
    relation = _s(resolved_scene.get("relation"))
    if not relation:
        relation = (
            "current_scene"
            if continuation or reference_to_previous
            else "new_topic"
            if mode == "NEW_TOPIC"
            else "independent"
        )

    outputs = _requested_outputs(
        text,
        semantic,
        cognition,
        decision,
        independent_turn=(mode == "INDEPENDENT"),
    )
    preferred, representation_state = _representation_consensus(
        outputs, semantic, decision
    )
    constraints = _representation_constraints(semantic, cognition, decision)

    topic = _s(
        canonical_dialogue.get("active_topic")
        or _field((semantic, decision, state), ("active_topic", "topic", "current_topic"))
    )
    goal = _s(
        canonical_dialogue.get("active_goal")
        or _field((decision, cognition, semantic), ("active_goal", "resolved_request", "goal"))
    ) or text

    capabilities: list[str] = []
    for source in (semantic, cognition):
        for key in ("required_capabilities", "required_domains", "available_tools"):
            values = source.get(key, []) if isinstance(source, dict) else []
            for value in _as_list(values):
                value = _s(value)
                if value and value not in capabilities:
                    capabilities.append(value)

    control = {
        "version": "QUANTUM_CONTROL_PLANE_V1",
        "authority": {
            "dialogue": "interpretation",
            "representation": "semantic_decision",
            "capabilities": "semantic_cognition",
            "memory": "state_manager",
            "production": "executor_specialized_engines",
            "presentation": "executor_presentation_matrix",
            "rendering": "april_web",
        },
        "mode": mode,
        "relation": relation,
        "continuation": continuation,
        "reference_to_previous": reference_to_previous,
        "context_dependency": context_dependency,
        "resolved_scene": resolved_scene,
        "active_topic": topic,
        "active_goal": goal,
        "dialogue_evidence": evidence,
        "requested_outputs": outputs,
        "preferred_representation": preferred,
        "representation_state": representation_state,
        "representation_constraints": constraints,
        "capabilities": capabilities[:12],
        "dynamic_memory": dynamic_memory if isinstance(dynamic_memory, dict) else {},
        "single_route": True,
        "provider_calls": 1,
        "triggers": False,
        "score_routing": False,
    }

    state["_quantum_control_plane"] = _quantum_snapshot(control)
    semantic["quantum_control_plane"] = _quantum_snapshot(control)
    return control


def _make_request(
    text: str,
    semantic: dict,
    cognition: dict,
    decision: dict,
    state: dict,
    visual: dict,
    control: dict | None = None,
) -> MachineRequest:
    """Create the single canonical MachineRequest from the processor control plane."""
    scope = _user_scope(state, state.get("_request_user_id") or state.get("user_id"))
    control = control or _build_processor_control_plane(
        text=text,
        semantic=semantic,
        cognition=cognition,
        decision=decision,
        state=state,
        dynamic_memory=_as_dict(semantic.get("quantum_dynamic_memory_evidence")),
    )

    evidence = _as_dict(control.get("dialogue_evidence"))
    mode = _s(control.get("mode")).upper() or "INDEPENDENT"
    dialogue_state = {
        name: 1.0 if mode == name else 0.0
        for name in (
            "INDEPENDENT",
            "NEW_TOPIC",
            "SAME_TOPIC",
            "CONTINUATION",
            "ARTIFACT_REFERENCE",
            "MEMORY_QUERY",
        )
    }
    coherence = 1.0

    dialogue_contract_source = _as_dict(
        _as_dict(semantic.get("quantum_interpretation_evidence")).get("dialogue_contract")
    )
    dialogue_contract = {
        "dialog_act": _s(
            dialogue_contract_source.get("dialog_act")
            or _field((semantic, decision, cognition), ("dialog_act", "dialogue_act"))
        ) or "statement",
        "continuation": bool(control.get("continuation")),
        "reference_to_previous": bool(control.get("reference_to_previous")),
        "context_dependency": (
            _s(dialogue_contract_source.get("context_dependency"))
            or ("continuation" if mode == "CONTINUATION"
                else "reference" if mode == "ARTIFACT_REFERENCE"
                else "independent" if mode == "INDEPENDENT"
                else "topic")
        ),
        "reply_to": _s(
            _field((dialogue_contract_source, semantic, decision), ("reply_to", "previous_turn_id"))
        ),
        "active_goal": _s(dialogue_contract_source.get("active_goal"))
            or _s(control.get("active_goal")),
        "active_topic": _s(dialogue_contract_source.get("active_topic"))
            or _s(control.get("active_topic")),
        "resolved_scene": _as_dict(dialogue_contract_source.get("resolved_scene")),
        "current_request": _s(text),
    }

    context = _compact_context(
        text,
        state,
        mode,
        _s(control.get("active_topic")),
        _s(control.get("active_goal")),
    )

    dynamic_memory_evidence = _as_dict(control.get("dynamic_memory"))
    complexity = _complexity(semantic, cognition, decision, text)
    quantum_budget_field = _quantum_64_field(text, semantic, cognition, decision)
    response_budget = _quantum_budget_from_64(quantum_budget_field)

    representation_constraints = _as_dict(control.get("representation_constraints"))
    requested_outputs = list(control.get("requested_outputs") or ["text"])
    measured_output = _s(control.get("preferred_representation")) or "text"

    representation_audit = _representation_audit(
        requested_outputs=requested_outputs,
        measured_output=measured_output,
        constraints=representation_constraints,
    )

    request_metadata = {
        "processor_version": PROCESSOR_VERSION,
        "assistant_identity": deepcopy(APRIL_IDENTITY),
        "assistant_identity_name": APRIL_IDENTITY.get("name", "April"),
        "identity_request": bool(semantic.get("identity_request")),
        "single_route": True,
        "provider_calls_per_request": 1,
        "context_mode": mode,
        "dialogue_coherence": round(coherence, 4),
        "identity_scope": deepcopy(scope),
        "control_plane_version": control.get("version"),
    }

    if isinstance(state, dict):
        active_flow = state.get("active_flow") if isinstance(state.get("active_flow"), dict) else {}
        flow_id = state.get("flow_id") or active_flow.get("flow_id")
        if flow_id:
            request_metadata["flow_id"] = flow_id

    request = MachineRequest(
        goal=_s(control.get("active_goal")) or text,
        intent={
            "type": _s(semantic.get("intent")) or (
                "self_identification" if semantic.get("identity_request") else "dialogue"
            ),
            "normalized_text": _s(text),
            "dialogue_state": mode,
            "coherence": round(coherence, 4),
            "dialog_act": dialogue_contract["dialog_act"],
        },
        conversation={
            "current_request": _s(text),
            "dialogue_contract": dialogue_contract,
            "context_mode": mode,
            "context_dependency": bool(control.get("context_dependency")),
            "resolved_request": _s(
                dialogue_contract_source.get("resolved_request") or text
            ),
            "previous_user_turn": _s(dialogue_contract_source.get("previous_user_turn")),
            "previous_april_turn": _s(dialogue_contract_source.get("previous_april_turn")),
            "resolved_scene": _as_dict(dialogue_contract_source.get("resolved_scene")),
            **(
                {
                    "active_topic": _clip(_s(control.get("active_topic")), 300),
                    "active_goal": _clip(_s(control.get("active_goal")), 500),
                }
                if mode != "INDEPENDENT"
                else {}
            ),
            **(
                {"recent_dialogue": context.get("recent_dialogue", [])}
                if mode in {
                    "CONTINUATION",
                    "SAME_TOPIC",
                    "ARTIFACT_REFERENCE",
                    "MEMORY_QUERY",
                } or bool(control.get("context_dependency"))
                else {}
            ),
        },
        memory=(
            {
                "active_topic": _clip(_s(control.get("active_topic")), 300),
                "active_goal": _clip(_s(control.get("active_goal")), 500),
                "retrieval_mode": "memory_query" if mode == "MEMORY_QUERY" else "semantic",
                "dynamic_memory": (
                    dynamic_memory_evidence
                    if mode in {
                        "CONTINUATION",
                        "SAME_TOPIC",
                        "ARTIFACT_REFERENCE",
                        "MEMORY_QUERY",
                    } or bool(control.get("reference_to_previous"))
                    else {"available": bool(dynamic_memory_evidence.get("matches"))}
                ),
            }
            if mode != "INDEPENDENT"
            else {
                "active_scene_id": _s(
                    _as_dict(state.get("current_visual_scene")).get("scene_id")
                )
            }
        ),
        visual_context=(
            visual if mode == "ARTIFACT_REFERENCE" and isinstance(visual, dict)
            else {}
        ),
        available_tools=list(control.get("capabilities") or []),
        requested_outputs=requested_outputs,
        required_competencies=list(control.get("capabilities") or []),
        required_artifacts=requested_outputs,
        routing={
            "single_route": True,
            "processor": PROCESSOR_VERSION,
            "measured_state": mode,
            "identity_scope": deepcopy(scope),
        },
        constraints={
            "one_provider_call": True,
            "one_visible_answer": True,
            "canonical_scene": True,
            "dialogue_coherence": round(coherence, 4),
            "quantum_state": {
                "dialogue": dialogue_state,
                "representation": control.get("representation_state", {}),
                "measured_output": measured_output,
            },
            "provider_input_token_budget": 900,
            "provider_context_strategy": "provider_router_semantic_field_selection",
            "current_request_must_remain_intact": True,
            "identity_scope": deepcopy(scope),
            "representation_plan": {
                "requested_outputs": requested_outputs,
                "preferred_representation": measured_output,
                "constraints": representation_constraints,
                "audit": representation_audit,
                "current_request_authoritative": True,
            },
            "metadata": request_metadata,
        },
    )

    request.response_complexity = complexity
    request.response_output_tokens = response_budget
    request.max_output_tokens = response_budget
    request.quantum_state = {
        "dialogue": dialogue_state,
        "representation": control.get("representation_state", {}),
        "measured_output": measured_output,
        "context_dependency": bool(control.get("context_dependency")),
        "reference_to_previous": bool(control.get("reference_to_previous")),
        "continuation": bool(control.get("continuation")),
        "evidence_channels": len(evidence),
        "coherence": round(coherence, 4),
        "response_budget": response_budget,
        "response_budget_min": OUTPUT_MIN_TOKENS,
        "response_budget_max": OUTPUT_MAX_TOKENS,
        "response_budget_mode": "continuous_64_signal_scale",
        "quantum_cores": QUANTUM_CORE_COUNT,
        "quantum_lanes": QUANTUM_LANE_COUNT,
        "quantum_signal_count": QUANTUM_CORE_COUNT * QUANTUM_LANE_COUNT,
        "quantum_budget_field": quantum_budget_field,
        "response_budget_logical": True,
        "response_budget_compression_ceiling": OUTPUT_MAX_TOKENS,
        "control_plane": _quantum_snapshot(control),
    }
    request.dialogue_contract = dialogue_contract
    request.response_decision = decision
    request.single_route = True
    request.provider_calls_allowed = 1

    request.constraints["metadata"].update({
        "processor_version": PROCESSOR_VERSION,
        "single_route": True,
        "provider_calls_per_request": 1,
        "context_mode": mode,
        "dialogue_coherence": round(coherence, 4),
        "response_budget": response_budget,
        "response_budget_min": OUTPUT_MIN_TOKENS,
        "response_budget_max": OUTPUT_MAX_TOKENS,
        "response_budget_mode": "continuous_64_signal_scale",
        "quantum_cores": QUANTUM_CORE_COUNT,
        "quantum_lanes": QUANTUM_LANE_COUNT,
        "quantum_signal_count": QUANTUM_CORE_COUNT * QUANTUM_LANE_COUNT,
        "quantum_budget_field": quantum_budget_field,
        "requested_outputs": requested_outputs,
        "identity_scope": deepcopy(scope),
        "control_plane": _quantum_snapshot(control),
        "representation_plan": _quantum_snapshot(
            request.constraints.get("representation_plan", {})
        ),
    })
    return request


def _request_metadata(request: MachineRequest) -> dict:
    constraints = getattr(request, "constraints", {})
    if not isinstance(constraints, dict):
        constraints = {}
    metadata = constraints.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    return metadata


def _repair_machine_json_escapes(text: str) -> str:
    """Repair only invalid JSON backslashes while preserving real JSON escapes.

    Provider responses sometimes contain JSON-shaped envelopes with LaTeX such
    as ``\\( ... \\sqrt{...} \\)``. Those backslashes are valid payload text but
    are not valid JSON escapes unless doubled for the JSON parser. This engine
    normalizes the transport encoding only; it does not alter the decoded human
    answer.
    """
    # JSON permits only these one-character escapes plus \\uXXXX. Any other
    # backslash is payload text and must be escaped before json.loads().
    return re.sub(r'\\\\(?!["\\\\/bfnrtu])', r'\\\\\\\\', text)


def _decode_json_envelope(value: Any, *, max_depth: int = 5) -> Any:
    """Recursively unwrap serialized machine envelopes without creating a route.

    The decoder accepts:
      * normal JSON,
      * JSON-shaped Provider payloads containing LaTeX backslashes,
      * Python-literal style dicts using single quotes.

    The repair is transport-level only. It never rewrites the decoded answer.
    """
    current = value
    for _ in range(max_depth):
        if isinstance(current, MachineResponse):
            current = {
                name: getattr(current, name)
                for name in current.__dataclass_fields__
            }
            continue
        if not isinstance(current, str):
            break

        text = current.strip()
        if not (text.startswith("{") and text.endswith("}")):
            break

        parsed = None

        # 1. Canonical JSON first.
        try:
            candidate = json.loads(text)
            if isinstance(candidate, dict):
                parsed = candidate
        except Exception:
            pass

        # 2. Relaxed transport JSON: preserve LaTeX backslashes as payload.
        if parsed is None:
            repaired = _repair_machine_json_escapes(text)
            try:
                candidate = json.loads(repaired)
                if isinstance(candidate, dict):
                    parsed = candidate
            except Exception:
                pass

            # 3. Legacy Python-literal envelopes. Parse the repaired form so
            # invalid LaTeX escapes cannot emit SyntaxWarning during eval.
            if parsed is None:
                try:
                    candidate = ast.literal_eval(repaired)
                    if isinstance(candidate, dict):
                        parsed = candidate
                except Exception:
                    pass

        if parsed is None:
            break
        current = parsed

    return current


def _clean_text_value(value: Any) -> str:
    """Return only the final human-readable text from a Provider field."""
    current = _decode_json_envelope(value)

    if isinstance(current, dict):
        for key in ("answer", "content", "response", "text", "message", "final_text"):
            if current.get(key) not in (None, "", [], {}):
                nested = _decode_json_envelope(current.get(key))
                if isinstance(nested, str):
                    return nested.strip()
                if isinstance(nested, dict):
                    resolved = _clean_text_value(nested)
                    if resolved:
                        return resolved
        return ""

    return _s(current)


def _clean_render_blocks(blocks: Any) -> list[dict]:
    """Preserve all structured blocks while unwrapping accidental JSON text blocks."""
    result: list[dict] = []
    queue = list(blocks or []) if isinstance(blocks, (list, tuple)) else []
    while queue:
        block = queue.pop(0)
        if not isinstance(block, dict):
            continue

        btype = _s(
            block.get("type")
            or block.get("artifact_type")
            or block.get("representation")
        ).lower()

        content = block.get("content")
        decoded_content = _decode_json_envelope(content)
        if isinstance(decoded_content, dict) and any(
            key in decoded_content
            for key in ("answer", "content", "summary", "render_blocks", "artifacts")
        ):
            nested_answer = _clean_text_value(decoded_content.get("answer") or decoded_content.get("content"))
            if nested_answer:
                clean_block = dict(block)
                clean_block["content"] = nested_answer
                clean_block["text"] = nested_answer
                result.append(clean_block)
            nested_blocks = decoded_content.get("render_blocks")
            if isinstance(nested_blocks, list):
                queue = list(nested_blocks) + queue
            continue

        clean_block = dict(block)
        if btype in {"text", "markdown"}:
            clean_text = _clean_text_value(
                block.get("content")
                or block.get("text")
                or block.get("value")
            )
            if clean_text:
                clean_block["content"] = clean_text
                clean_block["text"] = clean_text
        result.append(clean_block)

    return result


def _decode_provider_payload(value: Any) -> dict:
    """Fully decode the Provider envelope while preserving every structured field.

    The Provider may return:
      1) a dict,
      2) a MachineResponse dataclass,
      3) a JSON string containing either,
      4) an answer/content field that itself contains another JSON envelope.

    Nested canonical fields must WIN over the outer serialized wrapper.  We
    therefore merge metadata first and canonical inner fields second, instead
    of letting the raw outer ``answer`` overwrite the decoded answer.
    """
    decoded = _decode_json_envelope(value)
    if isinstance(decoded, MachineResponse):
        decoded = {
            name: getattr(decoded, name)
            for name in decoded.__dataclass_fields__
        }

    if not isinstance(decoded, dict):
        return {"answer": _clean_text_value(decoded)}

    def merge_nested(base: dict, nested: dict, source_key: str) -> dict:
        # Preserve every unrelated outer field, but let decoded inner fields
        # own answer/content/summary/render/artifact semantics.
        outer = {k: v for k, v in base.items() if k != source_key}
        merged = {**outer, **nested}

        # When the inner envelope omitted a machine field, retain the outer one.
        for key in (
            "render_blocks", "blocks", "artifacts", "artifacts_payload",
            "scene", "scene_plan", "renderer_state", "metadata",
            "active_scene", "supported_payloads", "links", "graph", "formula",
            "table", "gallery", "layout", "visual",
        ):
            if key not in nested and key in base:
                merged[key] = base[key]
        return merged

    payload = dict(decoded)

    # First unwrap explicit nested machine_response envelopes.
    embedded = _decode_json_envelope(payload.get("machine_response"))
    if isinstance(embedded, dict):
        payload = merge_nested(payload, embedded, "machine_response")

    # Repeatedly unwrap a canonical answer/content/response envelope until the
    # visible fields are no longer machine JSON.  Inner canonical fields win.
    for _ in range(4):
        changed = False
        for key in ("answer", "content", "response", "payload", "data"):
            nested = _decode_json_envelope(payload.get(key))
            if isinstance(nested, dict) and any(
                k in nested
                for k in (
                    "answer", "content", "response", "summary",
                    "render_blocks", "artifacts", "machine_response"
                )
            ):
                payload = merge_nested(payload, nested, key)
                changed = True
                break
        if not changed:
            break

    payload["render_blocks"] = _clean_render_blocks(
        payload.get("render_blocks") or payload.get("blocks") or []
    )
    if isinstance(payload.get("summary"), str):
        payload["summary"] = _clean_text_value(payload.get("summary"))

    # Canonical human fields are always flattened to plain text here.
    answer = (
        _clean_text_value(payload.get("answer"))
        or _clean_text_value(payload.get("content"))
        or _clean_text_value(payload.get("response"))
    )
    if answer:
        payload["answer"] = answer
        payload["content"] = answer

    return payload



def _math_structure_profile(value: Any) -> dict:
    """Measure mathematical structure using notation/relations, not words."""
    source = _s(value)
    if not source:
        return {"present": False, "confidence": 0.0, "ranges": [], "notation": [], "operator_density": 0.0}

    ranges: list[dict] = []
    notation: list[str] = []
    occupied: list[tuple[int, int]] = []

    def add_range(start: int, end: int, source_name: str, *, kind: str = "formula") -> None:
        start = max(0, int(start))
        end = min(len(source), int(end))
        while end > start and source[end - 1].isspace():
            end -= 1
        while start < end and source[start].isspace():
            start += 1
        if end <= start:
            return
        if any(start < b and end > a for a, b in occupied):
            return
        occupied.append((start, end))
        ranges.append({
            "start": start,
            "end": end,
            "kind": kind,
            "renderer": "mcdowell",
            "engine": "katex",
            "source": source_name,
        })
        notation.append(source_name)

    # Explicit math delimiters are structural and authoritative.
    delimiter_patterns = (
        (r"\\\((.+?)\\\)", "inline_latex"),
        (r"\\\[(.+?)\\\]", "display_latex"),
        (r"\$\$(.+?)\$\$", "display_dollar"),
        (r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", "inline_dollar"),
    )
    for pattern, label in delimiter_patterns:
        for match in re.finditer(pattern, source, flags=re.DOTALL):
            add_range(*match.span(), label)

    # Raw TeX is structural mathematics even when the Provider omitted
    # explicit $...$ / \( ... \) delimiters.  We recognize complete
    # operator-connected atom chains rather than isolated commands, so the
    # presentation engine receives one coherent formula span.
    frac_atom = r"\\(?:frac|dfrac|tfrac)\s*\{[^{}\n]{1,120}\}\s*\{[^{}\n]{1,120}\}"
    sqrt_atom = r"\\(?:sqrt)\s*\{[^{}\n]{1,120}\}"
    command_atom = r"\\(?:operatorname|mathrm|text)\s*\{[^{}\n]{1,80}\}"
    raw_tex_atom = rf"(?:[-+]?\d+(?:[.,]\d+)?|[A-Za-zΑ-Ωα-ω]\w*|{frac_atom}|{sqrt_atom}|{command_atom})"
    raw_tex_operator = r"(?:\\(?:cdot|times|div|pm|mp|approx|leq|geq|neq|sim|cong|simeq)|[+\-*/=<>×÷≈≤≥≠±])"
    raw_tex_chain = re.compile(
        rf"(?P<expr>{raw_tex_atom}(?:\s*{raw_tex_operator}\s*{raw_tex_atom})+)"
    )
    for match in raw_tex_chain.finditer(source):
        add_range(*match.span("expr"), "raw_tex_structure")

    # Standalone TeX fraction/radical structures are also renderable when they
    # are not part of a longer operator chain.
    standalone_raw_tex = re.compile(
        rf"(?:{frac_atom}|{sqrt_atom})(?:\s*{raw_tex_operator}\s*(?:{frac_atom}|{sqrt_atom}|[-+]?\d+(?:[.,]\d+)?|[A-Za-zΑ-Ωα-ω]\w*))*"
    )
    for match in standalone_raw_tex.finditer(source):
        add_range(*match.span(), "raw_tex_structure")

    ranges.sort(key=lambda item: (item["start"], item["end"]))
    merged: list[dict] = []
    for item in ranges:
        if not merged or item["start"] >= merged[-1]["end"]:
            merged.append(item)
        elif item["end"] > merged[-1]["end"]:
            merged[-1]["end"] = item["end"]
            if item.get("source") not in notation:
                notation.append(item.get("source", "structural"))

    operator_count = len(re.findall(r"[=≈≃≅≤≥±·×÷/*^_√∛∜]", source))
    numeric_count = len(re.findall(r"\d", source))
    density = (operator_count + min(numeric_count, 12)) / max(len(source), 1)
    structural_strength = 0.0
    if merged:
        structural_strength = min(1.0, 0.50 + 0.12 * min(len(merged), 3) + min(0.22, density * 7.0))

    return {
        "present": bool(merged),
        "confidence": round(structural_strength, 6),
        "ranges": merged,
        "notation": sorted(set(x for x in notation if x)),
        "operator_density": round(density, 6),
        "measurement_mode": "structural_notation_matrix",
        "lexical_triggers": False,
    }


def _presentation_latex(fragment: str) -> str:
    """Convert structurally recognized notation to KaTeX-compatible source.

    The original payload is never changed. This value belongs only to the
    presentation contract consumed by the Web renderer.
    """
    text = _s(fragment)
    if not text:
        return ""

    # Existing TeX delimiters are already renderer-ready.
    if text.startswith("\\(") and text.endswith("\\)"):
        return text[2:-2].strip()
    if text.startswith("\\[") and text.endswith("\\]"):
        return text[2:-2].strip()
    if text.startswith("$$") and text.endswith("$$"):
        return text[2:-2].strip()
    if text.startswith("$") and text.endswith("$"):
        return text[1:-1].strip()

    value = text
    # Raw Provider TeX may arrive without explicit delimiters.  Preserve the
    # commands exactly; only normalize presentation whitespace/HTML-dangerous
    # line breaks are avoided here.  This value belongs to the Web presentation
    # contract, never to the human answer itself.
    value = re.sub(r"\\begin\{(?:equation|align|gather)\*?\}", "", value)
    value = re.sub(r"\\end\{(?:equation|align|gather)\*?\}", "", value)
    # Structural symbol normalization only; no lexical/domain mapping.
    value = value.replace("≈", r"\approx")
    value = value.replace("≃", r"\simeq")
    value = value.replace("≅", r"\cong")
    value = value.replace("≤", r"\leq")
    value = value.replace("≥", r"\geq")
    value = value.replace("±", r"\pm")
    value = value.replace("×", r"\times")
    value = value.replace("÷", r"\div")

    # Convert simple Unicode radicals structurally, including radicals on
    # both sides of a relation. Examples: √35, 2√7, √(x+1).
    import re as _re
    value = _re.sub(
        r"√\s*\(([^()]{1,96})\)",
        lambda m: r"\sqrt{" + m.group(1).strip() + "}",
        value,
    )
    value = _re.sub(
        r"√\s*([A-Za-zΑ-Ωα-ω0-9_.]+)",
        lambda m: r"\sqrt{" + m.group(1).strip() + "}",
        value,
    )
    value = _re.sub(
        r"∛\s*\(([^()]{1,96})\)",
        lambda m: r"\sqrt[3]{" + m.group(1).strip() + "}",
        value,
    )
    value = _re.sub(
        r"∛\s*([A-Za-zΑ-Ωα-ω0-9_.]+)",
        lambda m: r"\sqrt[3]{" + m.group(1).strip() + "}",
        value,
    )
    value = _re.sub(
        r"∜\s*\(([^()]{1,96})\)",
        lambda m: r"\sqrt[4]{" + m.group(1).strip() + "}",
        value,
    )
    value = _re.sub(
        r"∜\s*([A-Za-zΑ-Ωα-ω0-9_.]+)",
        lambda m: r"\sqrt[4]{" + m.group(1).strip() + "}",
        value,
    )
    return value


def _presentation_segments(content: Any) -> dict:
    """Create one canonical presentation contract from the original payload.

    The processor never rewrites the payload. It only measures source ranges
    and emits renderer metadata for the same content. No lexical trigger list
    participates in this contract.
    """
    source = _s(content)
    profile = _math_structure_profile(source)
    ranges = profile.get("ranges", []) if isinstance(profile, dict) else []

    if not source:
        return {"mode": "text", "spans": [], "segments": [], "analysis": profile}

    if not ranges:
        return {
            "mode": "text",
            "spans": [],
            "segments": [{
                "kind": "text",
                "start": 0,
                "end": len(source),
                "role": "text",
                "renderer": "mcdowell",
                "engine": "markdown",
            }],
            "analysis": profile,
        }

    spans: list[dict] = []
    segments: list[dict] = []
    cursor = 0
    for item in sorted(ranges, key=lambda x: (x["start"], x["end"])):
        start = max(0, int(item["start"]))
        end = min(len(source), int(item["end"]))
        if end <= start:
            continue

        if start > cursor:
            segments.append({
                "kind": "text",
                "start": cursor,
                "end": start,
                "role": "text",
                "renderer": "mcdowell",
                "engine": "markdown",
            })

        original = source[start:end]
        latex = _presentation_latex(original)
        span = {
            "start": start,
            "end": end,
            "role": "formula",
            "renderer": "mcdowell",
            "engine": "katex",
            "latex": latex,
            "value": original,
            "display": False,
        }
        spans.append(span)
        segments.append({
            "kind": "formula",
            "start": start,
            "end": end,
            "role": "formula",
            "renderer": "mcdowell",
            "engine": "katex",
            "latex": latex,
            "value": original,
            "display": False,
            "preserve_payload": True,
        })
        cursor = end

    if cursor < len(source):
        segments.append({
            "kind": "text",
            "start": cursor,
            "end": len(source),
            "role": "text",
            "renderer": "mcdowell",
            "engine": "markdown",
        })

    return {
        "mode": "mixed",
        "spans": spans,
        "segments": segments,
        "analysis": profile,
        "renderer": "mcdowell",
        "math_engine": "katex",
        "payload_preserved": True,
    }


def _presentation_signal_for_block(block: dict) -> dict:
    """Build the single canonical presentation signal consumed by RenderMessage."""
    source = dict(block or {})
    btype = _s(
        source.get("type")
        or source.get("artifact_type")
        or source.get("representation")
    ).lower()
    representation = _s(
        source.get("representation")
        or source.get("presentation")
    ).lower()

    kind = btype or representation or "text"
    signal: dict[str, Any] = {
        "version": "presentation_signal_v3",
        "kind": kind,
        "renderer": "",
        "engine": "",
        "preserve_payload": True,
        "payload_unchanged": True,
    }

    if kind in {"text", "markdown"}:
        content = source.get("content") or source.get("text") or source.get("value") or ""
        segmented = _presentation_segments(content)
        signal.update({
            "kind": "mixed" if segmented.get("mode") == "mixed" else "text",
            "renderer": "mcdowell",
            "engine": "presentation_matrix",
            "text_engine": "mcdowell",
            "formula_engine": "katex",
            "presentation": segmented,
            "spans": segmented.get("spans", []),
            "segments": segmented.get("segments", []),
            "analysis": segmented.get("analysis", {}),
            "delegated_segments": bool(segmented.get("mode") == "mixed"),
        })
    elif kind == "formula":
        signal.update({
            "kind": "formula",
            "renderer": "mcdowell",
            "engine": "katex",
            "math_mode": "display",
            "presentation": {
                "enabled": True,
                "mode": "formula",
                "renderer": "mcdowell",
                "math_engine": "katex",
                "formulas": [{
                    "value": source.get("content") or source.get("text") or source.get("value") or "",
                    "latex": _presentation_latex(source.get("content") or source.get("text") or source.get("value") or ""),
                    "display": True,
                }],
            },
        })
    elif kind == "table":
        signal.update({
            "kind": "table",
            "renderer": "table",
            "engine": "table",
            "cell_text_engine": "mcdowell",
            "cell_math_engine": "katex",
        })
    elif kind in {"graph", "plot", "chart"}:
        signal.update({
            "kind": "graph",
            "renderer": "graph",
            "engine": "graph",
            "label_text_engine": "mcdowell",
            "label_math_engine": "katex",
        })
    elif kind == "code":
        signal.update({"kind": "code", "renderer": "code", "engine": "syntax"})
    elif kind == "link":
        signal.update({
            "kind": "link",
            "renderer": "link",
            "engine": "link_card",
            "description_engine": "mcdowell",
        })
    elif kind in {"gallery", "image", "media"}:
        signal.update({
            "kind": "gallery",
            "renderer": "gallery",
            "engine": "media",
            "caption_engine": "mcdowell",
        })
    elif kind in {"diagram", "scene", "layout", "visual"}:
        signal.update({
            "kind": "diagram",
            "renderer": "graph",
            "engine": "diagram",
            "label_text_engine": "mcdowell",
            "label_math_engine": "katex",
        })
    else:
        signal.update({
            "kind": kind,
            "renderer": "mcdowell",
            "engine": "markdown",
            "inline_math_engine": "katex",
        })

    # The existing canonical route consumes this field directly in RenderMessage.
    # Do not create a second parallel signal field.
    explicit_signal = source.get("presentation")
    if isinstance(explicit_signal, dict):
        preserved = dict(signal.get("presentation") or {})
        preserved.update(_quantum_snapshot(explicit_signal))
        signal["presentation"] = preserved

    return signal


def _attach_presentation_signals(blocks: Any) -> list[dict]:
    enriched: list[dict] = []
    for block in blocks if isinstance(blocks, list) else []:
        if not isinstance(block, dict):
            continue
        clean = dict(block)
        presentation = _presentation_signal_for_block(clean)
        clean["presentation"] = presentation
        enriched.append(clean)
    return enriched

def _ensure_presentation_signals(blocks: Any) -> list[dict]:
    """Attach presentation exactly once while preserving already-built signals."""
    result: list[dict] = []
    for block in blocks if isinstance(blocks, list) else []:
        if not isinstance(block, dict):
            continue
        clean = dict(block)
        existing = clean.get("presentation")
        if isinstance(existing, dict) and existing.get("version") == "presentation_signal_v3":
            result.append(clean)
        else:
            clean["presentation"] = _presentation_signal_for_block(clean)
            result.append(clean)
    return result

def _response(value: Any, request: MachineRequest | None = None) -> MachineResponse:
    """Single in-place Provider response analysis and canonical separation."""
    payload = _decode_provider_payload(value)
    fields = MachineResponse.__dataclass_fields__
    allowed = {k: v for k, v in payload.items() if k in fields}

    answer = (
        _clean_text_value(payload.get("answer"))
        or _clean_text_value(payload.get("content"))
        or _clean_text_value(payload.get("response"))
    )

    blocks = _attach_presentation_signals(_clean_render_blocks(payload.get("render_blocks") or []))
    if not answer:
        for block in blocks:
            if not isinstance(block, dict):
                continue
            btype = _s(block.get("type") or block.get("artifact_type")).lower()
            if btype in {"text", "markdown"}:
                answer = _clean_text_value(
                    block.get("content")
                    or block.get("text")
                    or block.get("value")
                )
                if answer:
                    break

    if answer:
        allowed["answer"] = answer
        allowed["content"] = answer

    artifacts = list(allowed.get("artifacts") or [])
    artifacts_payload = list(allowed.get("artifacts_payload") or [])

    visible_text = any(
        isinstance(block, dict)
        and _s(block.get("type") or block.get("artifact_type")).lower() in {"text", "markdown"}
        and bool(_clean_text_value(
            block.get("content") or block.get("text") or block.get("value")
        ))
        for block in blocks
    )
    if answer and not visible_text:
        blocks.insert(0, {
            "type": "text",
            "artifact_type": "text",
            "content": answer,
            "text": answer,
            "renderer": "TextBlock",
            "viewer": "TextBlock",
            "scene_contract": True,
            "source": "quantum_processor",
        })
    allowed["render_blocks"] = blocks

    metadata = dict(allowed.get("metadata") or {}) if isinstance(allowed.get("metadata"), dict) else {}
    extras = {
        k: v for k, v in payload.items()
        if k not in fields and k not in {"processor_input", "provider_source_request"}
    }
    if extras:
        metadata["provider_extras"] = _quantum_snapshot(extras)

    block_types = []
    for block in blocks:
        if isinstance(block, dict):
            btype = _s(
                block.get("type")
                or block.get("artifact_type")
                or block.get("representation")
            ).lower()
            if btype and btype not in block_types:
                block_types.append(btype)

    metadata["quantum_matrix"] = {
        "owner": "QUANTUM_PROCESSOR",
        "version": PROCESSOR_VERSION,
        "answer_present": bool(answer),
        "summary_present": bool(_clean_text_value(payload.get("summary"))),
        "requested_outputs": list(getattr(request, "requested_outputs", []) or []) if request else [],
        "block_types": block_types,
        "render_block_count": len(blocks),
        "artifact_count": len(artifacts) + len(artifacts_payload),
        "information_preserved": True,
        "machine_fields_transport_only": True,
        "scoring": False,
        "triggers": False,
    }
    metadata["visible_answer_guaranteed"] = bool(answer)
    metadata["artifact_preservation"] = True
    metadata["single_route"] = True
    allowed["metadata"] = metadata

    return MachineResponse(**allowed)


def _canonicalize(
    user_id: str,
    response: MachineResponse,
    state: dict,
    semantic: dict,
    cognition: dict,
    decision: dict,
    request: MachineRequest,
) -> dict:
    answer = _clean_text_value(
        response.answer
    ) or _clean_text_value(
        response.content
    ) or _clean_text_value(
        response.response
    )

    if not answer:
        raise RuntimeError("Quantum canonicalization blocked: empty MachineResponse answer")

    # Final human-field invariant: SceneContract.answer/content can only contain
    # plain human text, never the serialized MachineResponse envelope.
    decoded_answer = _decode_json_envelope(answer)
    if isinstance(decoded_answer, dict):
        answer = _clean_text_value(decoded_answer)
    answer = _s(answer)
    if not answer:
        raise RuntimeError("Quantum canonicalization blocked: decoded answer is empty")

    response.answer = answer
    response.content = answer

    # Summary remains a memory/context field supplied by the Provider or an
    # upstream semantic engine. The Executor never fabricates a summary from
    # the visible answer.
    response.summary = _clean_text_value(response.summary)

    response.render_blocks = _ensure_presentation_signals(
        _clean_render_blocks(list(getattr(response, "render_blocks", []) or []))
    )

    scope = _user_scope(state, user_id)
    response.metadata = dict(response.metadata or {})
    response.metadata.update({
        "processor_version": PROCESSOR_VERSION,
        "single_route": True,
        "provider_calls_per_request": 1,
        "visible_answer_guaranteed": True,
        "artifact_preservation": True,
        "trigger_routing": False,
        "score_routing": False,
        "identity_scope": deepcopy(scope),
    })
    response.quantum_state = request.quantum_state
    response.conversation_space = {
        "identity_scope": deepcopy(scope),
        "current_turn": {
            "user": _s(request.conversation.get("current_request")),
            "april": {
                "answer": answer,
                "render_blocks": response.render_blocks,
                "artifacts": list(getattr(response, "artifacts", []) or []),
                "summary": response.summary,
            },
        }
    }
    response.executor_semantic = semantic
    response.executor_cognition = cognition
    response.executor_response_decision = decision

    if not any(
        isinstance(block, dict)
        and _s(block.get("type") or block.get("artifact_type")).lower() in {"text", "markdown"}
        and bool(_clean_text_value(block.get("content") or block.get("text") or block.get("value")))
        for block in response.render_blocks
    ):
        response.render_blocks.insert(0, {
            "type": "text",
            "artifact_type": "text",
            "content": answer,
            "text": answer,
            "renderer": "TextBlock",
            "viewer": "TextBlock",
            "scene_contract": True,
            "source": "quantum_processor",
            "signal": _presentation_signal_for_block({"type": "text"}),
        })

    scene = build_machine_scene(response)
    provider_blocks = list(getattr(response, "render_blocks", []) or [])

    try:
        scene.blocks = provider_blocks
        scene.contract.blocks = provider_blocks
        scene.contract.render_blocks = list(provider_blocks)
        scene.contract.metadata = dict(scene.contract.metadata or {})
        scene.contract.metadata["identity_scope"] = deepcopy(scope)
        scene.contract.metadata["renderer_state"] = {
            "active_scene": scene.contract.active_scene,
            "block_types": [
                _s(
                    block.get("type")
                    or block.get("artifact_type")
                    or block.get("representation")
                ).lower()
                for block in provider_blocks
                if isinstance(block, dict)
            ],
            "continuation": bool(request.quantum_state.get("continuation")),
            "decision_owner": "QUANTUM_PROCESSOR",
            "single_route": True,
        }

        if hasattr(scene.contract, "supported_payloads"):
            supported = list(getattr(scene.contract, "supported_payloads", []) or [])
            for artifact in list(getattr(response, "artifacts", []) or []):
                if artifact not in supported:
                    supported.append(artifact)
            scene.contract.supported_payloads = supported
    except Exception:
        pass

    contract = build_scene_contract(scene)

    # SceneContract is the release boundary: force the canonical human answer
    # into answer/content, keep summary isolated, and keep every renderer block.
    try:
        contract.answer = answer
        contract.content = answer
        contract.summary = response.summary
        contract.render_blocks = list(provider_blocks)
        contract.blocks = list(provider_blocks)
    except Exception:
        pass

    render_blocks = list(getattr(contract, "render_blocks", []) or [])
    if not render_blocks:
        render_blocks = provider_blocks
        try:
            contract.render_blocks = render_blocks
        except Exception:
            pass

    update_dialog_context(user_id, semantic)
    update_scene_context(
        user_id,
        contract,
        current_request=_s(request.conversation.get("current_request")),
        answer=answer,
    )
    request_meta = _request_metadata(request)

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
        "render_blocks": render_blocks,
        "artifacts": list(getattr(response, "artifacts", []) or []),
        "single_route": True,
        "provider_calls_per_request": 1,
        "quantum_state": request.quantum_state,
        "energy_acceleration": request_meta.get("energy_acceleration", {}),
        "visible_answer_guaranteed": True,
        "artifact_preservation": True,
        "identity_scope": deepcopy(scope),
    }

def _validate_quantum_release(request: MachineRequest) -> None:
    constraints = getattr(request, "constraints", {})
    if not isinstance(constraints, dict):
        raise RuntimeError("Quantum release blocked: constraints missing")

    if constraints.get("one_provider_call") is not True:
        raise RuntimeError("Quantum release blocked: one_provider_call invariant failed")

    if constraints.get("provider_input_token_budget") != 900:
        raise RuntimeError("Quantum release blocked: provider input budget invariant failed")

    response_budget = getattr(request, "response_output_tokens", 0)
    if not isinstance(response_budget, int) or not (OUTPUT_MIN_TOKENS <= response_budget <= OUTPUT_MAX_TOKENS):
        raise RuntimeError("Quantum release blocked: adaptive response budget invariant failed")

    if getattr(request, "provider_calls_allowed", 1) != 1:
        raise RuntimeError("Quantum release blocked: provider call count invariant failed")

    if getattr(request, "single_route", True) is not True:
        raise RuntimeError("Quantum release blocked: single_route invariant failed")

    metadata = constraints.get("metadata")
    if not isinstance(metadata, dict):
        raise RuntimeError("Quantum release blocked: metadata bridge missing")
    identity_scope = metadata.get("identity_scope")
    if not isinstance(identity_scope, dict) or not identity_scope.get("user_id"):
        raise RuntimeError("Quantum release blocked: identity scope missing")

async def execute(user_id, chat_id=None, text="", run_with_activity=None, **kwargs):
    """
    ONE ROUTE / UNIFIED MATRIX PROCESSOR / ONE COLLAPSE / ONE PROVIDER CALL.

    The ten quantumized modules are not ten routes. They are ten independent
    evidence lenses feeding one processor field. The processor arbitrates the
    combined field, creates one MachineRequest, then uses the existing Provider
    path once and the existing C-Artifact/SceneContract path once.
    """
    state = get_state(user_id)
    state = state if isinstance(state, dict) else {}
    state["user_id"] = _s(user_id)
    scope = _user_scope(state, user_id)
    state["_request_user_id"] = _s(user_id)
    history = state.get("dialog", []) if isinstance(state.get("dialog"), list) else []
    active_flow = state.get("active_flow") if isinstance(state.get("active_flow"), dict) else {}
    dialog_state = state.get("scene_state") if isinstance(state.get("scene_state"), dict) else {}

    build_deephub_context(user_id, text, state)
    context_packet = state.get("_executor_context_packet")
    if not isinstance(context_packet, dict):
        context_packet = build_executor_context_packet(state)
    context_evidence = state.get("_machine_context", {}).get("quantum_evidence", {})
    if not isinstance(context_evidence, dict):
        context_evidence = {}

    active_flow = state.get("active_flow") if isinstance(state.get("active_flow"), dict) else {}
    dialog_state = state.get("scene_state") if isinstance(state.get("scene_state"), dict) else {}
    history = state.get("dialog", []) if isinstance(state.get("dialog"), list) else []

    # One canonical heavy Interpretation pass per turn. Semantic Core reuses
    # the same evidence packet instead of re-running Stanza/NLI.
    interpretation = interpret_request(
        text,
        cognition=state.get("cognition", {}) if isinstance(state.get("cognition"), dict) else {},
        semantic={},
        history=history,
        state=state,
    ) or {}

    # Freeze canonical interpretation measurements for downstream engines.
    field = interpretation.get("quantum_interpretation_field", {})
    if isinstance(field, dict):
        dialogue_field = field.get("dialogue")
        representation_field = field.get("representation")
        if isinstance(dialogue_field, dict) and isinstance(
            dialogue_field.get("semantic_measurement"), dict
        ):
            interpretation["quantum_dialogue_measurement"] = dialogue_field["semantic_measurement"]
        if isinstance(representation_field, dict):
            interpretation["quantum_representation_measurement"] = representation_field

    semantic = semantic_analyze(
        text=text,
        state=state,
        history=history,
        active_flow=active_flow,
        dialog_state=dialog_state,
        interpreted=interpretation,
    ) or {}

    reasoning = build_reasoning_state(text=text, semantic=semantic, state=state)
    cognition = analyze_cognition(
        text=text, semantic=semantic, reasoning=reasoning, state=state
    ) or {}

    interpretation["cognition"] = _quantum_snapshot(cognition)

    _merge_evidence_fields(semantic, (interpretation,))
    semantic["quantum_interpretation_evidence"] = interpretation
    if isinstance(interpretation.get("quantum_representation_measurement"), dict):
        semantic["quantum_representation_measurement"] = _quantum_snapshot(
            interpretation["quantum_representation_measurement"]
        )
    if isinstance(interpretation.get("quantum_dialogue_measurement"), dict):
        semantic["quantum_dialogue_measurement"] = _quantum_snapshot(
            interpretation["quantum_dialogue_measurement"]
        )

    intent = detect_intent(text, state) or {}
    intent_ai = await detect_intent_ai(text, state)
    intent_ai = intent_ai if isinstance(intent_ai, dict) else {}
    resolver = resolve_input(history, state) or {}
    focus_intent = build_focus_intent_state(text, state) or {}

    intent_ai["provider_calls"] = 0
    intent_ai["decision_owner"] = "QUANTUM_PROCESSOR"

    _merge_evidence_fields(semantic, (intent, intent_ai, resolver))
    semantic["quantum_intent_evidence"] = {
        "intent_system": intent,
        "intent_ai": intent_ai,
        "intent_resolver": resolver,
        "focus": focus_intent,
    }

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
    router_hint = await route_request(text, router_context)
    router_evidence = semantic.get("quantum_router_evidence", {})
    if not isinstance(router_evidence, dict):
        router_evidence = {}

    router_system = decide_action(text, history) or {}

    _merge_evidence_fields(semantic, (router_evidence, router_system))
    semantic["quantum_router_evidence"] = {
        "router": router_evidence,
        "router_system": router_system,
        "compatibility_hint": router_hint,
    }

    visual = build_visual_reference(
        semantic=semantic, cognition=cognition, text=text, state=state
    ) or {}

    # -------------------------------------------------------------
    # FOUR NEW QUANTUM EVIDENCE LENSES
    # These do not own routing or memory. They only contribute compact,
    # JSON-safe evidence to the single processor field.
    # -------------------------------------------------------------
    experience = build_experience_evidence(
        text=text,
        state=state,
    ) or {}

    experience_manager_state = get_experience(
        user_id
    ) or {}

    # The experience manager is a short-lived per-user signal source.
    # Only the latest compact state is admitted to the quantum field.
    experience_manager_evidence = {
        "user_id": _s(experience_manager_state.get("user_id") or user_id),
        "latest": _quantum_snapshot(
            experience_manager_state.get("latest", {})
        ),
        "has_experience": bool(experience_manager_state.get("events")),
        "temporary": True,
        "machine_only": True,
        "decision_owner": "QUANTUM_PROCESSOR",
        "provider_calls": 0,
    }

    goal_evidence = build_goal_evidence(
        text=text,
        state=state,
        semantic=semantic,
    ) or {}

    decision = build_response_decision(
        semantic=semantic,
        cognition=cognition,
        state=state,
        visual_reference=visual,
    ) or {}

    # One authoritative control plane for dialogue, representation, memory relation,
    # capability delegation, and single-route ownership. Individual engines remain
    # evidence sources; downstream code consumes this collapsed state.
    control_plane = _build_processor_control_plane(
        text=text,
        semantic=semantic,
        cognition=cognition,
        decision=decision,
        state=state,
        dynamic_memory=dynamic_memory,
    )
    state["_turn_dialogue_relation"] = {
        "relation": _s(control_plane.get("relation")),
        "scene_id": _s(_as_dict(control_plane.get("resolved_scene")).get("scene_id")),
        "continuation": bool(control_plane.get("continuation")),
        "reference_to_previous": bool(control_plane.get("reference_to_previous")),
        "same_scene": bool(
            control_plane.get("relation") == "current_scene"
            and _as_dict(control_plane.get("resolved_scene")).get("scene_id")
        ),
        "context_dependency": bool(control_plane.get("context_dependency")),
    }

    processor_context = build_processor_execution_context({
        "state": state,
        "context": context_evidence,
        "semantic": semantic,
        "cognition": cognition,
        "interpretation": interpretation,
        "intent": intent,
        "intent_ai": intent_ai,
        "resolver": resolver,
        "router": router_evidence,
        "router_system": router_system,
        "decision": decision,
        "experience": experience,
        "experience_manager": experience_manager_evidence,
        "goal": goal_evidence,
        "visual_reference": visual,
        "dynamic_memory": dynamic_memory,
        "control_plane": control_plane,
    })

    quantum_field = _build_quantum_field(
        user_id=user_id,
        text=text,
        state=state,
        context=context_evidence,
        interpretation=interpretation,
        semantic=semantic,
        cognition=cognition,
        intent=intent,
        intent_ai=intent_ai,
        resolver={**resolver, "focus": focus_intent},
        router=router_evidence,
        router_system=router_system,
        decision=decision,
        experience=experience,
        experience_manager=experience_manager_evidence,
        goal=goal_evidence,
        visual_reference=visual,
    )

    detached_quantum_field = _quantum_snapshot(quantum_field)
    state["_quantum_evidence_field"] = detached_quantum_field
    state["_quantum_processor_context"] = _quantum_snapshot(processor_context)
    semantic["quantum_evidence_field"] = _quantum_snapshot(quantum_field)
    semantic["processor_context"] = _quantum_snapshot(processor_context)
    semantic["decision_owner"] = "QUANTUM_PROCESSOR"
    semantic["provider_calls"] = 0
    semantic["parallel_route"] = False
    semantic["quantum_processor_version"] = PROCESSOR_VERSION
    semantic["semantic_decision_owner"] = "QUANTUM_PROCESSOR"

    request = _make_request(text, semantic, cognition, decision, state, visual, control=control_plane)
    request.quantum_state["evidence_channels"] = 14
    request.quantum_state["evidence_field"] = quantum_field
    request_meta = _request_metadata(request)
    request_meta.update({
        "dynamic_memory_available": bool(dynamic_memory.get("matches")),
        "dynamic_memory_match_count": len(dynamic_memory.get("matches") or []),
        "quantum_evidence_channels": 14,
        "quantum_evidence_field_version": PROCESSOR_VERSION,
        "provider_calls_per_request": 1,
        "single_route": True,
        "requested_outputs": list(request.requested_outputs),
        "representation_plan": _quantum_snapshot(
            request.constraints.get("representation_plan", {})
        ),
        "representation_audit": _quantum_snapshot(
            request.constraints.get("representation_plan", {}).get("audit", {})
        ),
        "processor_context": processor_context,
    })
    request.constraints["metadata"] = request_meta

    energy_profile = build_quantum_acceleration_profile(
        user_id,
        flow_id=(state.get("flow_id") if isinstance(state, dict) else "") or "",
        semantic=semantic,
        cognition=cognition,
        decision=decision,
        state=state,
        outputs=request.requested_outputs,
        visual=visual,
    )
    request = apply_quantum_acceleration(request, energy_profile)
    acceleration_check = validate_quantum_acceleration(request, energy_profile)
    if not acceleration_check.get("ok"):
        raise RuntimeError("Quantum energy acceleration invariant failed")

    _validate_quantum_release(request)

    representation_plan = request.constraints.get("representation_plan", {})
    requested_outputs = list(getattr(request, "requested_outputs", []) or [])
    if representation_plan.get("current_request_authoritative") is not True:
        raise RuntimeError("Quantum release blocked: representation authority invariant failed")
    blocked_outputs = set(
        (representation_plan.get("constraints") or {}).get("negative", []) or []
    )
    if any(output in blocked_outputs for output in requested_outputs):
        raise RuntimeError("Quantum release blocked: contradictory representation plan")

    # Final quantum release audit: 14 evidence lenses, one request, one provider.
    #
    # IMPORTANT:
    # The 64-signal budget field is owned by the MachineRequest created by
    # _make_request(). It must never be read from execute()'s local scope,
    # because that would make the processor depend on a variable that only
    # exists inside _make_request(). Reading the canonical field from the
    # request keeps the budget calculation single-source and preserves the
    # single-route processor invariant.
    quantum_budget_field = (
        getattr(request, "quantum_state", {}) or {}
    ).get("quantum_budget_field", {})
    if not isinstance(quantum_budget_field, dict):
        raise RuntimeError("Quantum release blocked: canonical 64-signal budget field missing")

    # Final quantum release audit: 14 evidence lenses, one request, one provider.
    request.constraints.setdefault("metadata", {})["quantum_release_audit"] = {
        "evidence_channels": 14,
        "decision_owner": "QUANTUM_PROCESSOR",
        "single_route": True,
        "provider_calls": 1,
        "response_budget": getattr(request, "response_output_tokens", 0),
        "response_budget_range": [OUTPUT_MIN_TOKENS, OUTPUT_MAX_TOKENS],
        "response_budget_canonical": True,
        "quantum_cores": 8,
        "quantum_lanes_per_core": 8,
        "quantum_signal_count": 64,
        "response_budget_mode": "continuous_64_signal_scale",
        "input_budget": 900,
        "input_budget_mode": "logical_compaction",
        "quantum_semantic_engines": [
            "spacy_linguistic",
            "sentence_transformers_embedding",
            "transformers_nli",
            "context_vector_fusion",
        ],
        "word_trigger_routing": False,
        "fallback_semantics": False,
        "quantum_budget_field": quantum_budget_field,
        "experience": True,
        "experience_manager": True,
        "goal_engine": True,
        "visual_reference_system": True,
        "control_plane_version": control_plane.get("version"),
        "control_plane_single_route": bool(control_plane.get("single_route")),
    }

    provider_result = await generate_text(
        request,
        max_output_tokens=request.response_output_tokens,
    )
    response = _response(provider_result, request)

    # Canonical presentation audit: proves the processor actually emitted
    # renderer signals before the SceneContract release boundary.
    presentation_blocks = []
    for block in list(getattr(response, "render_blocks", []) or []):
        if isinstance(block, dict):
            presentation = block.get("presentation")
            if isinstance(presentation, dict):
                presentation_blocks.append({
                    "type": _s(block.get("type") or block.get("artifact_type") or "text"),
                    "kind": _s(presentation.get("kind")),
                    "renderer": _s(presentation.get("renderer")),
                    "engine": _s(presentation.get("engine")),
                    "spans": len(presentation.get("spans") or []),
                    "segments": len(presentation.get("segments") or []),
                    "math_engine": _s(presentation.get("math_engine") or presentation.get("formula_engine")),
                    "payload_unchanged": bool(presentation.get("payload_unchanged", False)),
                })
    request.constraints.setdefault("metadata", {})["presentation_matrix_audit"] = {
        "version": "presentation_signal_v3",
        "decision_owner": "QUANTUM_PROCESSOR",
        "blocks": presentation_blocks,
        "signal_count": len(presentation_blocks),
        "payload_preserved": True,
    }

    request.constraints.setdefault("metadata", {})["visible_answer_audit"] = {
        "answer_present": bool(_s(response.answer) or _s(response.content) or _s(response.response)),
        "render_blocks_before_canonicalize": len(getattr(response, "render_blocks", []) or []),
        "artifacts_preserved": len(getattr(response, "artifacts", []) or []),
        "text_block_guaranteed": any(
            isinstance(block, dict)
            and _s(block.get("type") or block.get("artifact_type")).lower() in {"text", "markdown"}
            for block in getattr(response, "render_blocks", []) or []
        ),
    }

    return _canonicalize(user_id, response, state, semantic, cognition, decision, request)
