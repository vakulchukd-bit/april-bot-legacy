"""April Quantum Processor — balanced single-route executor.

This is a quantum-inspired processor, not a physical quantum computer.
It evaluates many independent evidence channels, fuses them multiplicatively,
then collapses them to ONE dialogue state, ONE request and ONE scene contract.
There is exactly one Provider call per user turn.
"""
from __future__ import annotations

import math
import re
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
from blocks.state_manager import get_state, update_dialog_context
from blocks.C_ARTIFACT_CONTRACT import MachineRequest, MachineResponse, build_machine_scene, build_scene_contract
from blocks.provider_router import generate_text
from blocks.energy_manager import (build_quantum_acceleration_profile, apply_quantum_acceleration, validate_quantum_acceleration)

PROCESSOR_VERSION = "april_quantum_processor_quantum64_v17_semantic_fusion_no_triggers"
SINGLE_ROUTE = True
PROVIDER_CALLS = 1
OUTPUT_MIN_TOKENS = 1
OUTPUT_MAX_TOKENS = 8000


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

def _overlap(a: Any, b: Any) -> float:
    x, y = _tokens(a), _tokens(b)
    return len(x & y) / max(1, len(x | y))

def _clamp(x: float) -> float:
    return max(0.001, min(0.999, float(x)))

def _norm(scores: dict[str, float]) -> dict[str, float]:
    m = max(scores.values()) if scores else 1.0
    ex = {k: math.exp(v - m) for k, v in scores.items()}
    z = sum(ex.values()) or 1.0
    return {k: ex[k] / z for k in scores}

def _bool_signal(*values: Any) -> float:
    return 1.0 if any(bool(v) for v in values) else 0.0

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
) -> dict[str, float]:
    """
    Semantic dialogue measurement.

    IMPORTANT:
      - no word list decides continuation;
      - no renderer keyword decides the dialogue state;
      - previous-turn relation comes from semantic vectors + NLI;
      - the processor only fuses the measured evidence.
    """
    dialog = state.get("dialog", []) if isinstance(state, dict) else []
    last = dialog[-1] if dialog and isinstance(dialog[-1], dict) else {}

    previous_user = _s(last.get("user"))
    previous_april = ""
    if isinstance(last.get("april"), dict):
        previous_april = _s(
            last["april"].get("answer")
            or last["april"].get("content")
            or last["april"].get("summary")
        )

    active_topic = _s(
        semantic.get("active_topic")
        or decision.get("active_topic")
        or state.get("active_topic")
        or state.get("topic")
    )

    # Real semantic measurement from the interpretation-layer engines.
    measured = QUANTUM_DIALOGUE_ENGINE.classify(
        text=text,
        previous_assistant=previous_april,
        previous_user=previous_user,
        active_goal=_s(
            semantic.get("active_goal")
            or decision.get("active_goal")
            or state.get("active_goal")
        ),
        active_topic=active_topic,
    )

    dialogue = measured.get("dialogue", {}) if isinstance(measured, dict) else {}
    continuation_score = _bounded01(dialogue.get("continuation_score", 0.0))
    reference_score = _bounded01(dialogue.get("reference_score", 0.0))
    nli_confidence = _bounded01(dialogue.get("confidence", 0.0))

    # Semantic evidence supplied by semantic_core/cognition/decision is allowed
    # to strengthen the measured state, but never to override it by a word.
    same_topic = max(
        _bounded01(measured.get("topic_similarity", {}).get("score", 0.0)),
        _bounded01(semantic.get("same_topic_score", 0.0)),
        _bounded01(cognition.get("same_topic_score", 0.0)),
        _bounded01(decision.get("same_topic_score", 0.0)),
    )
    artifact_reference = max(
        _bounded01(measured.get("previous_similarity", {}).get("score", 0.0)),
        _bounded01(semantic.get("artifact_reference_score", 0.0)),
        _bounded01(cognition.get("artifact_reference_score", 0.0)),
        _bounded01(decision.get("artifact_reference_score", 0.0)),
    )

    # Structural complexity is measured from payload shape, not from trigger
    # words. It is only used as evidence for the quantum budget.
    words = _tokens(text)
    list_density = min(
        1.0,
        (
            text.count("\n-")
            + text.count("\n*")
            + text.count("\n1.")
            + text.count(";")
        ) / 4.0,
    )
    code_density = min(
        1.0,
        sum(text.count(marker) for marker in ("```", "=>", "{", "}")) / 5.0,
    )
    formula_density = min(
        1.0,
        sum(text.count(marker) for marker in ("=", "^", "√", "∑", "∫", "π")) / 5.0,
    )
    numeric_density = min(
        1.0,
        sum(char.isdigit() for char in text) / max(1, len(text)),
    )

    # Explicit semantic representation evidence comes from NLI, not keywords.
    representation_measurement = QUANTUM_EVIDENCE_FUSION.representations(
        text=text,
        context=active_topic or previous_april,
    )
    nli_labels = representation_measurement.get("nli", {}).get("labels", [])
    nli_scores = representation_measurement.get("nli", {}).get("scores", [])
    rep_scores = {
        _s(label).lower(): _bounded01(score)
        for label, score in zip(nli_labels, nli_scores)
    }
    representation_strength = max(rep_scores.values(), default=0.0)

    return {
        "history": float(bool(dialog)),
        "topic_overlap": same_topic,
        "answer_overlap": reference_score,
        "word_overlap": same_topic,
        "char_overlap": same_topic,
        "question": float(text.rstrip().endswith("?")),
        "exclamation": float(text.rstrip().endswith("!")),
        "short_turn": float(0 < len(words) <= 8),
        "long_turn": float(len(words) > 80),
        "continuation": continuation_score,
        "same_topic": same_topic,
        "artifact": artifact_reference,
        "deictic": reference_score,
        "explicit_output": representation_strength,
        "code_density": code_density,
        "formula_density": formula_density,
        "numeric_density": numeric_density,
        "list_density": list_density,
        "semantic_strength": nli_confidence,
        "cognition_strength": _bounded01(
            float(bool(cognition.get("reasoning_needed")))
            + float(bool(cognition.get("multi_step")))
            + float(bool(cognition.get("requires_planning")))
        ),
        "decision_strength": _bounded01(
            float(bool(decision.get("render_intent")))
            + float(bool(decision.get("analysis_mode")))
            + float(bool(decision.get("explanation_mode")))
        ),
        "goal_present": float(bool(
            semantic.get("active_goal")
            or cognition.get("active_goal")
            or decision.get("active_goal")
            or state.get("active_goal")
        )),
        "topic_present": float(bool(active_topic)),
        "visual_present": float(bool(
            state.get("active_visual_scene")
            or state.get("visual_summary")
            or semantic.get("visual_context")
        )),
        "nli_confidence": nli_confidence,
        "representation_strength": representation_strength,
        "dialogue_label": _s(
            measured.get("dialog_act") or dialogue.get("label")
        ),
    }


def _collapse_dialogue(e: dict[str, float]) -> tuple[str, dict[str, float], float]:
    """Fuse 24 evidence dimensions across 5 competing states, then collapse once."""
    W = {
        "INDEPENDENT": {"history":-1.4,"topic_overlap":-1.8,"answer_overlap":-1.4,"word_overlap":-1.0,"question":.4,"short_turn":-.4,"continuation":-2.0,"same_topic":-1.8,"artifact":-1.8,"deictic":-1.2,"explicit_output":.5,"semantic_strength":-.2,"cognition_strength":-.2,"decision_strength":-.2,"goal_present":-.3,"topic_present":-.5},
        "NEW_TOPIC": {"history":.4,"topic_overlap":-2.0,"answer_overlap":-1.4,"word_overlap":-1.0,"question":.5,"long_turn":.8,"continuation":-1.6,"same_topic":-1.5,"artifact":-1.0,"deictic":-.8,"explicit_output":.5,"semantic_strength":.2,"goal_present":.3},
        "SAME_TOPIC": {"history":1.0,"topic_overlap":3.0,"answer_overlap":1.8,"word_overlap":2.2,"char_overlap":1.2,"question":.3,"continuation":1.0,"same_topic":3.2,"artifact":1.2,"deictic":1.0,"topic_present":1.5},
        "CONTINUATION": {"history":1.2,"topic_overlap":1.5,"answer_overlap":2.8,"word_overlap":2.0,"question":.8,"short_turn":1.2,"continuation":4.0,"same_topic":2.0,"artifact":1.5,"deictic":1.4,"semantic_strength":1.0,"decision_strength":1.0},
        "ARTIFACT_REFERENCE": {"history":1.0,"topic_overlap":1.2,"answer_overlap":2.0,"word_overlap":1.2,"question":.4,"short_turn":.8,"continuation":1.8,"same_topic":1.4,"artifact":5.0,"deictic":3.0,"explicit_output":2.0,"visual_present":1.5},
    }
    raw = {}
    for state, weights in W.items():
        score = math.log(.2)
        for feature, weight in weights.items():
            score += weight * e.get(feature, 0.0)
        raw[state] = score
    p = _norm(raw)
    measured = max(p, key=p.get)
    return measured, p, p[measured]


def _representation_constraints(*sources: dict) -> dict:
    """
    Canonical representation constraints.

    Positive evidence can add a requested representation.
    Negative evidence blocks a representation from stale candidates.
    The processor never invents a renderer just because a keyword appears;
    it reconciles structured constraints already produced by the evidence
    layers and preserves the complete multi-output plan.
    """
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
            # Preferred is evidence, not authority; consensus still decides.
            positive.append(preferred)

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
) -> list[str]:
    """
    Produce the canonical multi-output request.

    Priority:
      1. explicit structured positive/negative representation constraints;
      2. requested outputs from Decision/Semantic;
      3. compatible representation candidates.

    No renderer is selected by a single keyword or by an old visual scene.
    """
    constraints = _representation_constraints(semantic, cognition, decision)
    blocked = set(constraints["negative"])
    names: list[str] = []

    def add(value: Any) -> None:
        if isinstance(value, str):
            values = [value]
        elif isinstance(value, (list, tuple, set)):
            values = list(value)
        else:
            values = []
        for value in values:
            name = _s(value).lower()
            aliases = {
                "markdown": "text",
                "renderer_scene": "diagram",
                "visual": "graph",
                "image_generate": "image",
                # Formula transport is rendered by TextBlock/KaTeX in the
                # current Web architecture; no FormulaBlock is required.
                "formula": "text",
            }
            name = aliases.get(name, name)
            if name and name not in blocked and name not in names:
                names.append(name)

    for src in (decision, semantic):
        if not isinstance(src, dict):
            continue
        add(src.get("requested_outputs"))
        add(src.get("required_outputs"))

    # Positive structured constraints are strong evidence, but do not replace
    # outputs already present in the canonical plan.
    add(constraints["positive"])

    # Candidate representations are added only when they are not explicitly
    # blocked and the evidence layer has not supplied a concrete plan yet.
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

    # NLI/vector candidates are semantic evidence, not lexical triggers.
    if not names:
        for candidate in _as_list(semantic.get("quantum_representation_candidates")):
            if not isinstance(candidate, dict):
                continue
            if _bounded01(candidate.get("score", 0.0)) >= 0.45:
                add(candidate.get("type"))

    if any(name != "text" for name in names) and "text" not in names:
        names.insert(0, "text")

    return names or ["text"]


def _representation_consensus(
    outputs: list[str],
    semantic: dict,
    decision: dict,
) -> tuple[str, dict[str, float]]:
    """
    Quantum-inspired representation measurement.

    Multiple candidates coexist. Current-request negative evidence suppresses
    stale alternatives. One preferred representation is measured, while the
    complete output plan remains in request.requested_outputs.
    """
    candidates = ["text", "table", "graph", "diagram", "formula", "code", "gallery", "image", "link"]
    raw = {x: -1.0 for x in candidates}

    for x in outputs:
        if x in raw:
            raw[x] += 4.0

    preferred = _s(
        decision.get("preferred_representation")
        or semantic.get("preferred_representation")
    ).lower()
    if preferred in raw:
        raw[preferred] += 1.5

    constraints = semantic.get("representation_constraints", {})
    if isinstance(constraints, dict):
        for blocked in constraints.get("negative", []) or []:
            blocked = _s(blocked).lower()
            if blocked in raw:
                raw[blocked] = -8.0
        for positive in constraints.get("positive", []) or []:
            positive = _s(positive).lower()
            if positive in raw:
                raw[positive] += 2.5

    p = _norm(raw)
    return max(p, key=p.get), p


def _complexity(semantic: dict, cognition: dict, decision: dict, text: str) -> str:
    """Descriptive complexity label only; never selects an output budget."""
    explicit = _s(
        semantic.get("response_complexity")
        or cognition.get("response_complexity")
        or decision.get("response_complexity")
    ).upper()
    if explicit in {"LOW", "MEDIUM", "HIGH"}:
        return explicit

    parts = max(
        1,
        len(
            semantic.get("task_parts") or
            semantic.get("subtasks") or
            semantic.get("requested_tasks") or
            []
        ),
    )
    outputs = semantic.get("requested_outputs") or semantic.get("required_outputs") or []
    artifacts = semantic.get("required_artifacts") or []
    domains = semantic.get("required_domains") or semantic.get("required_competencies") or []
    score = (
        max(0, parts - 1)
        + max(0, len(outputs) - 1)
        + max(0, len(artifacts) - 1)
        + min(2, len(domains))
        + int(bool(cognition.get("multi_step") or cognition.get("requires_planning")))
        + int(bool(decision.get("multi_step") or decision.get("requires_planning")))
    )
    if score >= 5:
        return "HIGH"
    if score >= 2:
        return "MEDIUM"
    return "LOW"



# ---------------------------------------------------------------------------
# 8-core × 8-lane quantum-inspired budget field (64 signals)
# ---------------------------------------------------------------------------

QUANTUM_CORES = (
    "meaning", "intent", "context", "structure",
    "evidence", "representation", "economy", "completion",
)
QUANTUM_LANES = (
    "relevance", "density", "complexity", "dependency",
    "structure", "continuity", "sufficiency", "confidence",
)

def _bounded01(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except Exception:
        return 0.0

def _quantum_64_field(
    text: str,
    semantic: dict,
    cognition: dict,
    decision: dict,
) -> dict:
    """Evaluate 8 semantic cores × 8 lanes; no lane selects a fixed tier."""
    words = _tokens(text)
    request_density = _bounded01(len(words) / 120.0)
    outputs = _as_list(
        semantic.get("requested_outputs")
        or semantic.get("required_outputs")
        or decision.get("requested_outputs")
    )
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
    continuation = _bounded01(bool(
        semantic.get("continuation")
        or cognition.get("continuation")
        or decision.get("continuation")
    ))
    structured = _bounded01(
        (len(outputs) + len(artifacts)) / 6.0
    )
    dependency = _bounded01(
        len(domains) / 8.0
    )
    context_strength = _bounded01(
        bool(semantic.get("same_topic") or semantic.get("artifact_reference")
             or cognition.get("same_topic") or decision.get("same_topic"))
    )
    planning = _bounded01(bool(
        cognition.get("multi_step") or cognition.get("requires_planning")
        or decision.get("multi_step") or decision.get("requires_planning")
    ))
    renderer_density = _bounded01(
        sum(1 for item in outputs if _s(item).lower() in {
            "table","graph","diagram","gallery","image","code","formula","link"
        }) / 4.0
    )
    # Scope is a representation-size signal, not a renderer trigger. It
    # measures how much material the request is asking the provider to carry.
    # Scope is measured from semantic structure and payload density only.
    # No lexical scope list is allowed to change the budget.
    semantic_scope = _bounded01(
        0.45 * _bounded01(len(outputs) / 6.0)
        + 0.25 * _bounded01(len(artifacts) / 6.0)
        + 0.15 * _bounded01(len(domains) / 8.0)
        + 0.15 * _bounded01(parts / 8.0)
    )
    lexical_free_scope = _bounded01(
        0.45 * semantic_scope
        + 0.25 * request_density
        + 0.15 * _bounded01(sum(c.isdigit() for c in text) / 12.0)
        + 0.15 * _bounded01(len(words) / 24.0)
    )
    scope_density = lexical_free_scope

    base = {
        "meaning":      (request_density, 0.60, 0.35, 0.30, 0.45, context_strength, 0.60, 0.70),
        "intent":       (0.65, 0.45, 0.45, 0.40, 0.50, continuation, 0.65, 0.70),
        "context":      (0.45, 0.35, 0.30, context_strength, 0.35, continuation, 0.55, 0.65),
        "structure":    (structured, 0.60, 0.55, 0.35, renderer_density, continuation, 0.70, 0.72),
        "evidence":     (request_density, 0.55, 0.50, dependency, 0.40, context_strength, 0.62, 0.68),
        "representation": (structured, renderer_density, 0.58, 0.40, renderer_density, continuation, 0.72, 0.74),
        "economy":      (1.0-request_density, 0.40, 0.30, 0.25, 0.30, 0.20, 0.78, 0.76),
        "completion":   (request_density, 0.55, 0.50, 0.35, 0.55, continuation, 0.82, 0.80),
    }

    # Small contextual refinements from already computed processor evidence.
    base["structure"] = tuple(min(1.0, x + (0.08 if parts > 1 else 0.0))
                               if i == 4 else x
                               for i, x in enumerate(base["structure"]))
    base["completion"] = tuple(min(1.0, x + (0.08 if parts > 1 else 0.0))
                                if i in (2,4,6) else x
                                for i, x in enumerate(base["completion"]))
    base["economy"] = tuple(max(0.0, x - (0.08 if structured > 0.66 else 0.0))
                             if i == 0 else x
                             for i, x in enumerate(base["economy"]))

    field = {}
    for core, values in base.items():
        field[core] = {lane: _bounded01(values[i]) for i, lane in enumerate(QUANTUM_LANES)}

    # Fused confidence = agreement among all 64 lanes, not a fixed tier.
    values=[v for core in field.values() for v in core.values()]
    mean=sum(values)/len(values)
    variance=sum((v-mean)**2 for v in values)/len(values)
    agreement=max(0.0, 1.0-math.sqrt(variance))
    return {
        "cores": field,
        "core_count": len(QUANTUM_CORES),
        "lane_count": len(QUANTUM_LANES),
        "signal_count": len(QUANTUM_CORES)*len(QUANTUM_LANES),
        "mean_need": mean,
        "agreement": agreement,
        "structured_density": structured,
        "request_density": request_density,
        "continuation": continuation,
        "planning": planning,
        "renderer_density": renderer_density,
        "output_count": len(outputs),
        "artifact_count": len(artifacts),
        "parts": parts,
        "scope_density": scope_density,
    }

def _quantum_budget_from_64(
    field: dict,
    *,
    minimum: int = OUTPUT_MIN_TOKENS,
    maximum: int = OUTPUT_MAX_TOKENS,
) -> int:
    """Collapse 64 continuous evidence signals into the minimum sufficient budget."""
    mean_need = _bounded01(field.get("mean_need", 0.0))
    agreement = _bounded01(field.get("agreement", 0.0))
    structured = _bounded01(field.get("structured_density", 0.0))
    request_density = _bounded01(field.get("request_density", 0.0))
    continuation = _bounded01(field.get("continuation", 0.0))
    planning = _bounded01(field.get("planning", 0.0))
    renderer_density = _bounded01(field.get("renderer_density", 0.0))
    output_count = max(0, int(field.get("output_count", 0) or 0))
    artifact_count = max(0, int(field.get("artifact_count", 0) or 0))
    parts = max(1, int(field.get("parts", 1) or 1))
    scope_density = _bounded01(field.get("scope_density", 0.0))

    # Economy is deliberately part of the decision, but structured output has
    # a real serialization cost. The processor therefore estimates the minimum
    # sufficient payload continuously instead of using entitlement tiers.
    informational_need = (
        0.22 * mean_need
        + 0.20 * structured
        + 0.18 * renderer_density
        + 0.14 * request_density
        + 0.08 * continuation
        + 0.06 * planning
        + 0.06 * (1.0 - agreement)
        + 0.03 * _bounded01(output_count / 4.0)
        + 0.03 * _bounded01(artifact_count / 4.0)
    )
    need = _bounded01(informational_need)

    # Continuous base frontier: short/simple answers stay small, while dense
    # requests move smoothly toward the 8000-token ceiling.
    shaped = need ** 1.90
    budget = minimum + (maximum - minimum) * shaped

    # Structured payload reserve. This is not renderer routing and not a fixed
    # tier: it is a continuous serialization-capacity estimate derived from the
    # already measured representation plan. Larger tables/scenes can therefore
    # receive more room without forcing every request to 8k.
    if structured > 0.0:
        representation_need = (
            0.52 * structured
            + 0.28 * renderer_density
            + 0.10 * _bounded01(output_count / 4.0)
            + 0.10 * _bounded01(parts / 6.0)
            + 0.18 * scope_density
        )
        reserve = (maximum - minimum) * (0.50 * _bounded01(representation_need) ** 1.15)
        scope_reserve = (maximum - minimum) * (0.55 * scope_density ** 1.12)
        budget = max(budget, minimum + reserve + scope_reserve)

    # Never exceed the canonical processor envelope. If the logical payload
    # would require more than 8000, the provider receives 8000 and the machine
    # prompt instructs it to compact the representation rather than truncate it.
    return int(round(max(minimum, min(maximum, budget))))

def _adaptive_output_budget(
    text: str,
    semantic: dict,
    cognition: dict,
    decision: dict,
) -> int:
    """Continuous 1..8000 budget produced by the 64-signal processor field."""
    field = _quantum_64_field(text, semantic, cognition, decision)
    return _quantum_budget_from_64(field)


def _compact_context(text: str, state: dict, mode: str, topic: str, goal: str) -> dict:
    dialog = state.get("dialog", []) if isinstance(state, dict) else []
    recent = []
    for turn in dialog[-4:]:
        if not isinstance(turn, dict):
            continue
        recent.append({"user": _clip(turn.get("user"), 450), "april": _clip((turn.get("april") or {}).get("answer") if isinstance(turn.get("april"), dict) else "", 700)})
    data = {"current_request": text, "context_mode": mode}
    if mode != "INDEPENDENT":
        if topic: data["active_topic"] = _clip(topic, 300)
        if goal: data["active_goal"] = _clip(goal, 500)
        data["recent_dialogue"] = recent
    if mode == "ARTIFACT_REFERENCE":
        visual = state.get("active_visual_scene") or state.get("visual_summary")
        if visual: data["visual_context"] = _clip(visual, 700)
    return data

def _make_request(text: str, semantic: dict, cognition: dict, decision: dict, state: dict, visual: dict) -> MachineRequest:
    evidence = _dialogue_evidence(text, semantic, cognition, decision, state)
    mode, dialogue_state, coherence = _collapse_dialogue(evidence)
    # Real semantic representation measurement. This is NLI/vector evidence,
    # never a word-trigger map.
    representation_measurement = QUANTUM_EVIDENCE_FUSION.representations(
        text=text,
        context=_s(
            semantic.get("active_topic")
            or decision.get("active_topic")
            or state.get("active_topic")
        ),
    )
    semantic["quantum_representation_measurement"] = _quantum_snapshot(
        representation_measurement
    )

    # Preserve high-confidence semantic candidates for the processor collapse.
    measured_labels = representation_measurement.get("nli", {}).get("labels", [])
    measured_scores = representation_measurement.get("nli", {}).get("scores", [])
    semantic_candidates = [
        {
            "type": _s(label).lower(),
            "score": float(score),
            "source": "quantum_nli",
        }
        for label, score in zip(measured_labels, measured_scores)
    ]
    semantic["quantum_representation_candidates"] = semantic_candidates

    # Only semantically measured candidates above the evidence threshold enter
    # the representation plan when no structured output was already supplied.
    if not (
        semantic.get("requested_outputs")
        or semantic.get("required_outputs")
        or decision.get("requested_outputs")
        or decision.get("required_outputs")
    ):
        semantic["candidate_representations"] = [
            item["type"]
            for item in semantic_candidates
            if item["score"] >= 0.45
        ]

    outputs = _requested_outputs(text, semantic, cognition, decision)
    measured_output, representation_state = _representation_consensus(
        outputs, semantic, decision
    )

    topic = _s(_field((semantic, decision, state), ("active_topic", "topic", "current_topic")))
    goal = _s(_field((decision, cognition, semantic), ("active_goal", "resolved_request", "goal"))) or text

    complexity = _complexity(semantic, cognition, decision, text)
    quantum_budget_field = _quantum_64_field(text, semantic, cognition, decision)
    response_budget = _quantum_budget_from_64(quantum_budget_field)

    representation_constraints = _representation_constraints(
        semantic, cognition, decision
    )
    context = _compact_context(text, state, mode, topic, goal)

    capabilities = []
    for src in (semantic, cognition):
        for key in ("required_capabilities", "required_domains", "available_tools"):
            values = src.get(key, []) if isinstance(src, dict) else []
            if isinstance(values, str):
                values = [values]
            for value in values:
                value = _s(value)
                if value and value not in capabilities:
                    capabilities.append(value)

    dialogue_contract = {
        "dialog_act": _s(
            _field((semantic, decision, cognition), ("dialog_act", "dialogue_act"))
        ) or "statement",
        "continuation": bool(
            _field((semantic, decision, cognition), ("continuation", "followup", "follow_up"))
        ) or mode == "CONTINUATION",
        "reply_to": _s(_field((semantic, decision), ("reply_to", "previous_turn_id"))),
        "active_goal": goal if mode != "INDEPENDENT" else "",
        "active_topic": topic if mode != "INDEPENDENT" else "",
    }

    request_metadata = {
        "processor_version": PROCESSOR_VERSION,
        "single_route": True,
        "provider_calls_per_request": 1,
        "context_mode": mode,
        "dialogue_coherence": round(coherence, 4),
    }

    if isinstance(state, dict):
        active_flow = state.get("active_flow") if isinstance(state.get("active_flow"), dict) else {}
        flow_id = state.get("flow_id") or active_flow.get("flow_id")
        if flow_id:
            request_metadata["flow_id"] = flow_id

    representation_audit = _representation_audit(
        requested_outputs=outputs,
        measured_output=measured_output,
        constraints=representation_constraints,
    )

    request = MachineRequest(
        goal=goal,
        intent={
            "type": _s(semantic.get("intent")) or "dialogue",
            "normalized_text": _s(text),
            "dialogue_state": mode,
            "coherence": round(coherence, 4),
            "dialog_act": dialogue_contract["dialog_act"],
        },
        conversation={
            "current_request": _s(text),
            "dialogue_contract": dialogue_contract,
            "context_mode": mode,
            **(
                {
                    "active_topic": _clip(topic, 300),
                    "active_goal": _clip(goal, 500),
                }
                if mode != "INDEPENDENT"
                else {}
            ),
            **(
                {"recent_dialogue": context.get("recent_dialogue", [])}
                if mode in {"CONTINUATION", "SAME_TOPIC", "ARTIFACT_REFERENCE"}
                else {}
            ),
        },
        memory=(
            {"active_topic": _clip(topic, 300), "active_goal": _clip(goal, 500)}
            if mode != "INDEPENDENT" and (topic or goal)
            else {}
        ),
        visual_context=(
            visual if mode == "ARTIFACT_REFERENCE" and isinstance(visual, dict)
            else {}
        ),
        available_tools=capabilities[:12],
        requested_outputs=outputs,
        required_competencies=capabilities[:12],
        required_artifacts=outputs,
        routing={
            "single_route": True,
            "processor": PROCESSOR_VERSION,
            "measured_state": mode,
        },
        constraints={
            **{
                "one_provider_call": True,
                "one_visible_answer": True,
                "canonical_scene": True,
                "dialogue_coherence": round(coherence, 4),
                "quantum_state": {
                    "dialogue": dialogue_state,
                    "representation": representation_state,
                    "measured_output": measured_output,
                },
                "provider_input_token_budget": 900,
                "provider_context_strategy": "provider_router_semantic_field_selection",
                "current_request_must_remain_intact": True,
                "representation_plan": {
                    "requested_outputs": list(outputs),
                    "preferred_representation": measured_output,
                    "constraints": representation_constraints,
                    "audit": representation_audit,
                    "current_request_authoritative": True,
                },
            },
            "metadata": request_metadata,
        },
    )

    request.response_complexity = complexity
    request.response_output_tokens = response_budget
    request.max_output_tokens = response_budget
    request.quantum_state = {
        "dialogue": dialogue_state,
        "representation": representation_state,
        "measured_output": measured_output,
        "evidence_channels": len(evidence),
        "coherence": round(coherence, 4),
        "response_budget": response_budget,
        "response_budget_min": OUTPUT_MIN_TOKENS,
        "response_budget_max": OUTPUT_MAX_TOKENS,
        "response_budget_mode": "continuous_64_signal_scale",
        "quantum_cores": 8,
        "quantum_lanes_per_core": 8,
        "quantum_signal_count": 64,
        "quantum_budget_field": quantum_budget_field,
        "response_budget_logical": True,
        "response_budget_compression_ceiling": OUTPUT_MAX_TOKENS,
    }
    request.dialogue_contract = dialogue_contract
    request.response_decision = decision
    request.single_route = True
    request.provider_calls_allowed = 1

    # Canonical contract bridge: MachineRequest currently exposes metadata
    # through constraints["metadata"], not as an __init__ field.
    request.constraints.setdefault("metadata", {})
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
        "quantum_cores": 8,
        "quantum_lanes_per_core": 8,
        "quantum_signal_count": 64,
        "quantum_budget_field": quantum_budget_field,
        "requested_outputs": list(outputs),
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

def _response(value: Any) -> MachineResponse:
    if isinstance(value, MachineResponse):
        return value
    if isinstance(value, dict):
        value = value.get("machine_response", value)
        if isinstance(value, MachineResponse):
            return value
        allowed = {k: v for k, v in value.items() if k in MachineResponse.__dataclass_fields__}
        return MachineResponse(**allowed)
    raise RuntimeError("Provider returned no canonical MachineResponse")

def _ensure_visible_answer_block(response: MachineResponse) -> list[dict]:
    """
    Canonical visible-answer invariant.

    Provider may return structured artifacts/render blocks without a dedicated
    visible text block. April Web still needs a canonical human-visible block.
    This helper preserves every provider block and artifact, adding exactly one
    TextBlock only when the answer is not already represented as visible text.
    """
    answer = _s(
        getattr(response, "answer", "")
        or getattr(response, "content", "")
        or getattr(response, "response", "")
    )
    original = list(getattr(response, "render_blocks", []) or [])

    if not answer:
        return original

    def block_text(block: Any) -> str:
        if not isinstance(block, dict):
            return ""
        for key in ("content", "text", "answer", "message", "value"):
            value = block.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    # A dedicated text block containing the canonical answer already exists.
    for block in original:
        if not isinstance(block, dict):
            continue
        block_type = _s(
            block.get("type") or block.get("artifact_type") or ""
        ).lower()
        if block_type in {"text", "markdown"} and block_text(block):
            return original

    visible_text_block = {
        "type": "text",
        "artifact_type": "text",
        "content": answer,
        "text": answer,
        "renderer": "TextBlock",
        "viewer": "TextBlock",
        "scene_contract": True,
        "source": "quantum_processor_canonical_answer",
    }

    # Preserve provider structured blocks exactly as received.
    return [visible_text_block, *original]


def _canonicalize(
    user_id: str,
    response: MachineResponse,
    state: dict,
    semantic: dict,
    cognition: dict,
    decision: dict,
    request: MachineRequest,
) -> dict:
    answer = _s(response.answer) or _s(response.content) or _s(response.response)
    if not answer:
        raise RuntimeError("Quantum canonicalization blocked: empty MachineResponse answer")

    response.answer = answer
    response.content = answer
    if not response.summary:
        response.summary = answer[:500]

    # Critical invariant:
    # answer must survive independently of structured artifacts/renderers.
    response.render_blocks = _ensure_visible_answer_block(response)

    response.metadata = dict(response.metadata or {})
    response.metadata.update({
        "processor_version": PROCESSOR_VERSION,
        "single_route": True,
        "provider_calls_per_request": 1,
        "visible_answer_guaranteed": True,
        "visible_answer_block_type": "text",
        "artifact_preservation": True,
    })
    response.quantum_state = request.quantum_state
    response.conversation_space = {
        "current_turn": {
            "user": _s(request.conversation.get("current_request")),
            "april": {
                "answer": answer,
                "render_blocks": response.render_blocks,
                "artifacts": list(getattr(response, "artifacts", []) or []),
            },
        }
    }
    response.executor_semantic = semantic
    response.executor_cognition = cognition
    response.executor_response_decision = decision

    # Build the canonical scene only after the visible answer invariant exists.
    scene = build_machine_scene(response)
    provider_blocks = list(getattr(response, "render_blocks", []) or [])

    # Never discard artifacts; only synchronize the canonical visible/render
    # block list with the already-preserved MachineResponse.
    try:
        scene.blocks = provider_blocks
        scene.contract.blocks = provider_blocks
        scene.contract.render_blocks = list(provider_blocks)

        if hasattr(scene.contract, "supported_payloads"):
            supported = list(getattr(scene.contract, "supported_payloads", []) or [])
            for artifact in list(getattr(response, "artifacts", []) or []):
                if artifact not in supported:
                    supported.append(artifact)
            scene.contract.supported_payloads = supported
    except Exception:
        # Scene contract builders may expose immutable dataclasses in some
        # deployments; MachineResponse remains canonical regardless.
        pass

    contract = build_scene_contract(scene)
    update_dialog_context(user_id, semantic)
    request_meta = _request_metadata(request)

    # Final transport audit: text must be visible, artifacts must survive.
    render_blocks = list(getattr(contract, "render_blocks", []) or [])
    if not render_blocks:
        render_blocks = list(provider_blocks)
    if not render_blocks:
        raise RuntimeError("Quantum canonicalization blocked: no render blocks")

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

async def execute(user_id, chat_id=None, text="", run_with_activity=None, **kwargs):
    """
    ONE ROUTE / TEN EVIDENCE ENGINES / ONE COLLAPSE / ONE PROVIDER CALL.

    The ten quantumized modules are not ten routes. They are ten independent
    evidence lenses feeding one processor field. The processor arbitrates the
    combined field, creates one MachineRequest, then uses the existing Provider
    path once and the existing C-Artifact/SceneContract path once.
    """
    state = get_state(user_id)
    state = state if isinstance(state, dict) else {}
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

    semantic = semantic_analyze(
        text=text,
        state=state,
        history=history,
        active_flow=active_flow,
        dialog_state=dialog_state,
    ) or {}

    reasoning = build_reasoning_state(text=text, semantic=semantic, state=state)
    cognition = analyze_cognition(
        text=text, semantic=semantic, reasoning=reasoning, state=state
    ) or {}

    interpretation = interpret_request(
        text,
        cognition=cognition,
        semantic=semantic,
        history=history,
        state=state,
    ) or {}

    _merge_evidence_fields(semantic, (interpretation,))
    semantic["quantum_interpretation_evidence"] = interpretation

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

    semantic["quantum_experience_evidence"] = _quantum_snapshot(experience)
    semantic["quantum_goal_evidence"] = _quantum_snapshot(goal_evidence)
    semantic["quantum_visual_reference_evidence"] = _quantum_snapshot(visual)
    semantic["quantum_experience_manager_evidence"] = _quantum_snapshot(
        experience_manager_evidence
    )

    # One semantic dialogue measurement for this turn. It is reused by the
    # processor collapse; no second lexical interpretation path is introduced.
    previous_turn = history[-1] if history and isinstance(history[-1], dict) else {}
    previous_april = ""
    if isinstance(previous_turn.get("april"), dict):
        previous_april = _s(
            previous_turn["april"].get("answer")
            or previous_turn["april"].get("content")
            or previous_turn["april"].get("summary")
        )
    semantic["quantum_dialogue_measurement"] = _quantum_snapshot(
        QUANTUM_DIALOGUE_ENGINE.classify(
            text=text,
            previous_assistant=previous_april,
            previous_user=_s(previous_turn.get("user")),
            active_goal=_s(
                semantic.get("active_goal")
                or cognition.get("active_goal")
                or decision.get("active_goal")
            ),
            active_topic=_s(
                semantic.get("active_topic")
                or decision.get("active_topic")
                or state.get("active_topic")
            ),
        )
    )

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

    request = _make_request(text, semantic, cognition, decision, state, visual)
    request.quantum_state["evidence_channels"] = 14
    request.quantum_state["evidence_field"] = quantum_field
    request_meta = _request_metadata(request)
    request_meta.update({
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
    }

    provider_result = await generate_text(
        request,
        max_output_tokens=request.response_output_tokens,
    )
    response = _response(provider_result)

    # The Provider may legitimately return structured artifacts without a
    # standalone visible text block. Canonicalize once here so Web never sees
    # an artifact-only SceneContract for an answer that exists.
    response.render_blocks = _ensure_visible_answer_block(response)
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
