"""APRIL quantum-inspired local energy accelerator.

Hybrid classical control layer for the existing Quantum Processor.
It performs local state evaluation only: no Provider call, no new route,
no renderer routing, no user-state sharing. It preserves the 900-token
Provider input ceiling and the existing 2k/5k/8k output policy.
"""
from __future__ import annotations

import hashlib
import math
from typing import Any

from storage import get_user_plan
from blocks.tariffs_config import ADMIN_ID

ENERGY_CORE_VERSION = "april_quantum_energy_accelerator_v3"
ENERGY_LEVELS = {"free": "LOW", "lite": "MEDIUM", "premium": "HIGH"}
OUTPUT_TOKENS = {"LOW": 2000, "MEDIUM": 5000, "HIGH": 8000}
PROVIDER_INPUT_TOKEN_BUDGET = 900
ENERGY_TASK_CHANNEL = {"channel": "energy_policy_task_channel", "isolated": True}
ENERGY_RESPONSE_CHANNEL = {"channel": "energy_policy_response_channel", "isolated": True}
LEVEL_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}

EXECUTION_PROFILES = {
    "LOW": {"context_depth": "minimal", "local_passes": 1, "heavy_generation": False},
    "MEDIUM": {"context_depth": "balanced", "local_passes": 2, "heavy_generation": False},
    "HIGH": {"context_depth": "extended", "local_passes": 3, "heavy_generation": True},
}

CHANNEL_WEIGHTS = {
    "task": 0.16, "context": 0.13, "representation": 0.12,
    "reasoning": 0.13, "visual": 0.08, "continuity": 0.10,
    "artifact": 0.10, "dialogue": 0.08,
    "semantic": 0.05, "cognition": 0.03, "decision": 0.02,
}

STATES = ("DIRECT", "CONTEXTUAL", "REASONING", "VISUAL", "COMPOSITE")


def _s(v: Any) -> str:
    return str(v or "").strip()


def _b(v: Any) -> float:
    return 1.0 if bool(v) else 0.0


def _clamp(v: Any) -> float:
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return 0.0


def _count(v: Any) -> int:
    return len(v) if isinstance(v, (dict, list, tuple, set)) else int(v not in (None, "", []))


def _uniq(v: Any) -> list[str]:
    if isinstance(v, str):
        v = [v]
    return list(dict.fromkeys(_s(x) for x in (v or []) if _s(x)))


def _softmax(scores: dict[str, float], temperature: float = 1.0) -> dict[str, float]:
    if not scores:
        return {}
    temperature = max(0.15, float(temperature))
    peak = max(scores.values())
    e = {k: math.exp((v - peak) / temperature) for k, v in scores.items()}
    z = sum(e.values()) or 1.0
    return {k: v / z for k, v in e.items()}


def _entropy(p: dict[str, float]) -> float:
    if not p:
        return 0.0
    h = -sum(v * math.log(max(v, 1e-12)) for v in p.values() if v > 0)
    return _clamp(h / math.log(max(2, len(p))))


def _geom(values: dict[str, float], weights: dict[str, float]) -> float:
    logv = sum(w * math.log(0.10 + 0.90 * _clamp(values.get(k, 0.0)))
              for k, w in weights.items())
    return _clamp((math.exp(logv) - 0.10) / 0.90)


def _cap_level(requested: str, entitlement: str) -> str:
    requested = requested if requested in LEVEL_ORDER else "LOW"
    entitlement = entitlement if entitlement in LEVEL_ORDER else "LOW"
    return requested if LEVEL_ORDER[requested] <= LEVEL_ORDER[entitlement] else entitlement


def log_energy_input(user_id: Any, flow_id: str = "") -> dict:
    return {
        "file_id": "APRIL_ENERGY_POLICY_CORE",
        "event": "energy_input",
        "channel": ENERGY_TASK_CHANNEL,
        "user_id": str(user_id),
        "flow_id": _s(flow_id),
        "machine_only": True,
    }


def log_energy_output(user_id: Any, energy: str, flow_id: str = "") -> dict:
    return {
        "file_id": "APRIL_ENERGY_POLICY_CORE",
        "event": "energy_output",
        "channel": ENERGY_RESPONSE_CHANNEL,
        "user_id": str(user_id),
        "flow_id": _s(flow_id),
        "energy": energy,
        "machine_only": True,
    }


def get_energy(user_id: Any) -> str:
    log_energy_input(user_id)
    energy = "HIGH" if user_id == ADMIN_ID else ENERGY_LEVELS.get(get_user_plan(user_id), "LOW")
    log_energy_output(user_id, energy)
    return energy


def build_energy_execution_profile(user_id: Any) -> dict:
    energy = get_energy(user_id)
    return {
        "channel": ENERGY_RESPONSE_CHANNEL,
        "file_id": ENERGY_CORE_VERSION,
        "energy": energy,
        "execution_profile": dict(EXECUTION_PROFILES[energy]),
        "machine_only": True,
    }


def _channels(semantic: dict, cognition: dict, decision: dict, state: dict,
              outputs: list, visual: dict) -> dict[str, float]:
    s, c, d, st = semantic, cognition, decision, state
    parts = s.get("task_parts") or s.get("subtasks") or s.get("requested_tasks") or []
    domains = s.get("required_domains") or s.get("required_competencies") or []
    complexity = max(
        _clamp(s.get("complexity_score")),
        _clamp(c.get("complexity_score")),
        _clamp(d.get("complexity_score")),
    )
    return {
        "task": _clamp(0.35 * min(1, _count(parts) / 5) + 0.25 * min(1, _count(domains) / 4) + 0.40 * complexity),
        "context": _clamp(0.45 * _b(st.get("dialog")) + 0.25 * _b(st.get("active_topic") or st.get("current_topic")) + 0.30 * _b(st.get("active_goal") or st.get("goal"))),
        "representation": _clamp(0.70 * min(1, len(_uniq(outputs)) / 4) + 0.30 * _b(s.get("render_intent") or d.get("render_intent"))),
        "reasoning": _clamp(0.35 * _b(c.get("reasoning_needed")) + 0.25 * _b(c.get("requires_planning")) + 0.20 * _b(d.get("analysis_mode")) + 0.20 * _b(d.get("reflection_mode"))),
        "visual": _clamp(0.40 * _b(visual) + 0.30 * _b(st.get("active_visual_scene")) + 0.30 * _b(st.get("visual_summary"))),
        "continuity": _clamp(0.45 * _b(s.get("continuation")) + 0.30 * _b(c.get("same_topic")) + 0.25 * _b(d.get("same_topic"))),
        "artifact": _clamp(0.40 * _b(s.get("artifact_reference")) + 0.30 * _b(d.get("artifact_reference")) + 0.30 * _b(s.get("required_artifacts") or s.get("artifact_types"))),
        "dialogue": _clamp(0.40 * _b(s.get("dialog_act") or s.get("dialogue_act")) + 0.30 * _b(d.get("dialog_act") or d.get("dialogue_act")) + 0.30 * _b(c.get("dialog_act") or c.get("dialogue_act"))),
        "semantic": _clamp(0.50 * _b(s) + 0.50 * complexity),
        "cognition": _clamp(0.50 * _b(c) + 0.50 * _b(c.get("reasoning_needed") or c.get("multi_step"))),
        "decision": _clamp(0.50 * _b(d) + 0.50 * _b(d.get("analysis_mode") or d.get("multi_step"))),
    }


def _candidate_states(ch: dict[str, float]) -> dict[str, float]:
    return {
        "DIRECT": _clamp(1 - .55*ch["context"] - .45*ch["reasoning"] - .35*ch["representation"]),
        "CONTEXTUAL": _clamp(.45*ch["context"] + .35*ch["continuity"] + .20*ch["dialogue"]),
        "REASONING": _clamp(.55*ch["reasoning"] + .25*ch["task"] + .20*ch["cognition"]),
        "VISUAL": _clamp(.60*ch["visual"] + .25*ch["representation"] + .15*ch["artifact"]),
        "COMPOSITE": _clamp(.35*ch["task"] + .25*ch["context"] + .20*ch["reasoning"] + .10*ch["representation"] + .10*ch["artifact"]),
    }


def _amplify(p: dict[str, float], rounds: int) -> dict[str, float]:
    p = dict(p)
    for _ in range(max(1, rounds)):
        p = {k: max(1e-9, v * v) for k, v in p.items()}
        z = sum(p.values()) or 1.0
        p = {k: v / z for k, v in p.items()}
    return p


def _coherence(ch: dict[str, float], p: dict[str, float]) -> float:
    vals = list(ch.values())
    mean = sum(vals) / max(1, len(vals))
    variance = sum((v - mean) ** 2 for v in vals) / max(1, len(vals))
    ordered = sorted(p.values(), reverse=True)
    margin = ordered[0] - (ordered[1] if len(ordered) > 1 else 0.0)
    return _clamp(0.72 * (1 - math.sqrt(variance)) + 0.28 * margin)


def build_quantum_acceleration_profile(
    user_id: Any,
    *,
    flow_id: str = "",
    semantic: dict | None = None,
    cognition: dict | None = None,
    decision: dict | None = None,
    state: dict | None = None,
    outputs: list | None = None,
    visual: dict | None = None,
) -> dict:
    """Local hybrid-control pass: factorize -> amplify -> measure -> allocate."""
    entitlement = get_energy(user_id)
    s, c, d, st, out, vis = semantic or {}, cognition or {}, decision or {}, state or {}, outputs or [], visual or {}
    ch = _channels(s, c, d, st, out, vis)

    groups = {
        "task": _geom(
            {k: ch[k] for k in ("task", "semantic", "cognition")},
            {"task": .5, "semantic": .3, "cognition": .2},
        ),
        "dialogue": _geom(
            {k: ch[k] for k in ("context", "continuity", "dialogue")},
            {"context": .45, "continuity": .35, "dialogue": .20},
        ),
        "presentation": _geom(
            {k: ch[k] for k in ("representation", "visual", "artifact")},
            {"representation": .45, "visual": .30, "artifact": .25},
        ),
        "reasoning": _geom(
            {"reasoning": ch["reasoning"], "decision": ch["decision"]},
            {"reasoning": .65, "decision": .35},
        ),
    }
    demand = _geom(groups, {"task": .30, "dialogue": .25, "presentation": .20, "reasoning": .25})

    raw = _candidate_states(ch)
    probability = _softmax(raw, temperature=max(.35, .90 - .45 * demand))
    rounds = 1 if demand < .45 else 2
    measured = _amplify(probability, rounds)
    entropy = _entropy(measured)
    selected = max(measured, key=measured.get)
    coherence = _coherence(ch, measured)

    base_passes = EXECUTION_PROFILES[entitlement]["local_passes"]
    local_passes = min(base_passes, 3 if entropy >= .78 or demand >= .78 else 2 if entropy >= .45 or demand >= .45 else 1)

    fingerprint = hashlib.sha256(
        f"{user_id}|{flow_id}|{entitlement}|{selected}|{round(demand,5)}|{round(coherence,5)}|{round(entropy,5)}".encode()
    ).hexdigest()[:16]

    return {
        "file_id": ENERGY_CORE_VERSION,
        "channel": ENERGY_RESPONSE_CHANNEL,
        "user_id": str(user_id),
        "flow_id": _s(flow_id),
        "entitlement_energy": entitlement,
        "selected_state": selected,
        "local_acceleration": selected,
        "demand": round(demand, 5),
        "coherence": round(coherence, 5),
        "entropy": round(entropy, 5),
        "signal_vector": {k: round(v, 5) for k, v in ch.items()},
        "factorized_groups": {k: round(v, 5) for k, v in groups.items()},
        "state_probabilities": {k: round(v, 5) for k, v in measured.items()},
        "amplification_rounds": rounds,
        "local_passes": local_passes,
        "local_parallel_evaluators": len(ch),
        "provider_input_token_budget": PROVIDER_INPUT_TOKEN_BUDGET,
        "provider_output_token_budget": OUTPUT_TOKENS[entitlement],
        "provider_calls_allowed": 1,
        "render_preservation": True,
        "scene_contract_required": True,
        "single_route": True,
        "request_intact": True,
        "request_fingerprint": fingerprint,
        "machine_only": True,
    }


def apply_quantum_acceleration(request: Any, profile: dict) -> Any:
    """Attach local accelerator state; do not replace processor decisions."""
    if request is None:
        return request

    entitlement = _s(profile.get("entitlement_energy")).upper() or "LOW"
    requested = _s(getattr(request, "response_complexity", "")).upper() or "LOW"
    effective = _cap_level(requested, entitlement)

    request.response_complexity = effective
    request.response_output_tokens = OUTPUT_TOKENS[effective]
    request.max_output_tokens = OUTPUT_TOKENS[effective]

    request.constraints = dict(getattr(request, "constraints", {}) or {})
    request.constraints.update({
        "provider_input_token_budget": PROVIDER_INPUT_TOKEN_BUDGET,
        "one_provider_call": True,
        "one_visible_answer": True,
        "canonical_scene": True,
        "quantum_acceleration": True,
        "request_intact": True,
        "local_passes": int(profile.get("local_passes", 1)),
        "state_entropy": profile.get("entropy", 0.0),
        "state_coherence": profile.get("coherence", 0.0),
    })

    request.metadata = dict(getattr(request, "metadata", {}) or {})
    request.metadata["energy_acceleration"] = {
        "version": ENERGY_CORE_VERSION,
        "entitlement_energy": entitlement,
        "requested_complexity": requested,
        "effective_complexity": effective,
        "selected_state": profile.get("selected_state", "DIRECT"),
        "demand": profile.get("demand", 0.0),
        "coherence": profile.get("coherence", 0.0),
        "entropy": profile.get("entropy", 0.0),
        "local_passes": profile.get("local_passes", 1),
        "provider_calls_allowed": 1,
        "provider_input_token_budget": PROVIDER_INPUT_TOKEN_BUDGET,
        "render_preservation": True,
    }
    request.quantum_state = dict(getattr(request, "quantum_state", {}) or {})
    request.quantum_state.update({
        "energy": entitlement,
        "accelerator_state": profile.get("selected_state", "DIRECT"),
        "compute_demand": profile.get("demand", 0.0),
        "state_entropy": profile.get("entropy", 0.0),
        "state_coherence": profile.get("coherence", 0.0),
        "amplification_rounds": profile.get("amplification_rounds", 1),
        "local_passes": profile.get("local_passes", 1),
        "energy_fingerprint": profile.get("request_fingerprint", ""),
    })
    request.single_route = True
    request.provider_calls_allowed = 1
    return request


def validate_quantum_acceleration(request: Any, profile: dict) -> dict:
    constraints = getattr(request, "constraints", {}) or {}
    effective = _s(getattr(request, "response_complexity", ""))
    return {
        "ok": bool(
            profile.get("machine_only") is True
            and constraints.get("one_provider_call") is True
            and constraints.get("canonical_scene") is True
            and constraints.get("request_intact") is True
            and effective in OUTPUT_TOKENS
        ),
        "single_route": True,
        "provider_calls_allowed": 1,
        "provider_input_token_budget": PROVIDER_INPUT_TOKEN_BUDGET,
        "provider_output_token_budget": profile.get("provider_output_token_budget"),
        "entitlement_energy": profile.get("entitlement_energy", "LOW"),
        "effective_complexity": effective,
        "local_passes": profile.get("local_passes", 1),
        "state_entropy": profile.get("entropy", 0.0),
        "state_coherence": profile.get("coherence", 0.0),
    }


__all__ = [
    "ENERGY_CORE_VERSION", "ENERGY_LEVELS", "EXECUTION_PROFILES",
    "OUTPUT_TOKENS", "PROVIDER_INPUT_TOKEN_BUDGET", "get_energy",
    "build_energy_execution_profile", "build_quantum_acceleration_profile",
    "apply_quantum_acceleration", "validate_quantum_acceleration",
]
