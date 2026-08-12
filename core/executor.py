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

from blocks.semantic_core import analyze as semantic_analyze
from blocks.reasoning_state import build_reasoning_state
from blocks.cognitive_core import analyze_cognition
from blocks.response_decision import build_response_decision
from blocks.visual_reference_system import build_visual_reference
from blocks.state_manager import get_state, update_dialog_context
from blocks.C_ARTIFACT_CONTRACT import MachineRequest, MachineResponse, build_machine_scene, build_scene_contract
from blocks.provider_router import generate_text
from blocks.energy_manager import (build_quantum_acceleration_profile, apply_quantum_acceleration, validate_quantum_acceleration)

PROCESSOR_VERSION = "april_quantum_processor_balanced_v6_energy_accelerated"
SINGLE_ROUTE = True
PROVIDER_CALLS = 1
OUTPUT_TOKENS = {"LOW": 2000, "MEDIUM": 5000, "HIGH": 8000}


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


def _field(sources: tuple[dict, ...], names: tuple[str, ...]) -> Any:
    for src in sources:
        if not isinstance(src, dict):
            continue
        for name in names:
            if src.get(name) not in (None, "", [], {}):
                return src[name]
    return ""


def _dialogue_evidence(text: str, semantic: dict, cognition: dict, decision: dict, state: dict) -> dict[str, float]:
    """Build independent evidence dimensions; no single trigger decides the state."""
    dialog = state.get("dialog", []) if isinstance(state, dict) else []
    last = dialog[-1] if dialog and isinstance(dialog[-1], dict) else {}
    previous_user = _s(last.get("user"))
    previous_april = _s((last.get("april") or {}).get("answer")) if isinstance(last.get("april"), dict) else ""
    low = text.lower()
    words = _tokens(text)
    prev_words = _tokens(previous_user)
    chars = set(low.replace(" ", ""))
    prev_chars = set(previous_user.lower().replace(" ", ""))
    explicit = bool(re.search(r"\b(таблиц|граф|диаграм|формул|код|ссылк|изображ|картин|галере|файл)\w*", low))
    continuation_words = bool(re.search(r"\b(да|нет|это|так|тогда|а|и|ещё|еще|почему|как|теперь|продолжи|исправь|дальше)\b", low))
    deictic = bool(re.search(r"\b(этот|эта|это|тот|та|выше|ниже|здесь|там|он|она|оно|они)\b", low))
    code_marks = sum(low.count(x) for x in ("```", "=>", "{", "}", "def ", "class "))
    formula_marks = sum(low.count(x) for x in ("=", "^", "√", "∑", "∫", "π"))
    semantic_flags = sum(bool(semantic.get(k)) for k in ("continuation", "same_topic", "render_intent", "math_intent", "artifact_reference", "visual_generation_needed", "multi_step"))
    cognition_flags = sum(bool(cognition.get(k)) for k in ("continuation", "same_topic", "artifact_reference", "complexity", "reasoning_needed", "tool_needed"))
    decision_flags = sum(bool(decision.get(k)) for k in ("continuation", "same_topic", "reflection_mode", "analysis_mode", "explanation_mode", "render_intent"))
    relation = _overlap(text, previous_user)
    answer_relation = _overlap(text, previous_april)
    same_topic = max(relation, float(bool(semantic.get("same_topic") or decision.get("same_topic"))))
    continuation = max(float(continuation_words), float(bool(semantic.get("continuation") or cognition.get("continuation") or decision.get("continuation"))))
    artifact = max(float(explicit and bool(dialog)), float(bool(semantic.get("artifact_reference") or decision.get("artifact_reference"))))
    history = float(bool(dialog))
    return {
        "history": history, "topic_overlap": relation, "answer_overlap": answer_relation,
        "word_overlap": len(words & prev_words) / max(1, len(words)),
        "char_overlap": len(chars & prev_chars) / max(1, len(chars | prev_chars)),
        "question": float("?" in text), "exclamation": float("!" in text),
        "short_turn": float(0 < len(words) <= 8), "long_turn": float(len(words) > 80),
        "continuation": continuation, "same_topic": same_topic, "artifact": artifact,
        "deictic": float(deictic), "explicit_output": float(explicit),
        "code_density": min(1.0, code_marks / 5), "formula_density": min(1.0, formula_marks / 5),
        "numeric_density": min(1.0, sum(c.isdigit() for c in text) / max(1, len(text))),
        "list_density": min(1.0, (text.count("\n-") + text.count("\n1.") + text.count(";")) / 4),
        "semantic_strength": min(1.0, semantic_flags / 7), "cognition_strength": min(1.0, cognition_flags / 6),
        "decision_strength": min(1.0, decision_flags / 6),
        "goal_present": float(bool(_field((decision, cognition, semantic, state), ("active_goal", "goal", "resolved_request")))),
        "topic_present": float(bool(_field((semantic, decision, state), ("active_topic", "topic", "current_topic")))),
        "visual_present": float(bool(state.get("active_visual_scene") or state.get("visual_summary"))),
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

def _requested_outputs(text: str, semantic: dict, cognition: dict, decision: dict) -> list[str]:
    """Use semantic state only; never inspect user wording for renderer triggers."""
    names: list[str] = []
    aliases = {
        "markdown": "text",
        "renderer_scene": "diagram",
        "visual": "graph",
        "image_generate": "image",
    }
    for src in (semantic, cognition, decision):
        if not isinstance(src, dict):
            continue
        for key in (
            "requested_outputs",
            "required_outputs",
            "required_representations",
            "candidate_representations",
            "requested_representation",
            "preferred_representation",
        ):
            value = src.get(key)
            vals = [value] if isinstance(value, str) else list(value or []) if isinstance(value, (list, tuple, set)) else []
            for value in vals:
                name = aliases.get(_s(value).lower(), _s(value).lower())
                if name and name not in names:
                    names.append(name)

    # The Processor may also receive an already structured artifact/room intent.
    # Read only structured fields, never the raw user's words.
    for src in (semantic, cognition, decision):
        if not isinstance(src, dict):
            continue
        artifact = src.get("artifact_types") or src.get("render_types") or src.get("representations")
        vals = [artifact] if isinstance(artifact, str) else list(artifact or []) if isinstance(artifact, (list, tuple, set)) else []
        for value in vals:
            name = aliases.get(_s(value).lower(), _s(value).lower())
            if name and name not in names:
                names.append(name)

    return names or ["text"]

def _representation_consensus(outputs: list[str], semantic: dict, decision: dict) -> tuple[str, dict[str, float]]:
    candidates = ["text", "table", "graph", "diagram", "formula", "code", "gallery", "image", "link"]
    raw = {x: -1.0 for x in candidates}
    for x in outputs:
        if x in raw:
            raw[x] += 4.0
    preferred = _s(decision.get("preferred_representation") or semantic.get("preferred_representation")).lower()
    if preferred in raw:
        raw[preferred] += 2.0
    if semantic.get("math_intent"):
        raw["formula"] += 2.5
    if semantic.get("render_intent"):
        raw["text"] += .5
    p = _norm(raw)
    return max(p, key=p.get), p


def _complexity(semantic: dict, cognition: dict, decision: dict, text: str) -> str:
    """Select 2k/5k/8k by structured task evidence, not keyword triggers."""
    explicit = _s(
        semantic.get("response_complexity")
        or cognition.get("response_complexity")
        or decision.get("response_complexity")
    ).upper()
    if explicit in OUTPUT_TOKENS:
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

    complexity_score = 0
    complexity_score += max(0, parts - 1)
    complexity_score += max(0, len(outputs) - 1)
    complexity_score += max(0, len(artifacts) - 1)
    complexity_score += min(2, len(domains))
    complexity_score += int(bool(cognition.get("multi_step") or cognition.get("requires_planning")))
    complexity_score += int(bool(decision.get("multi_step") or decision.get("requires_planning")))

    if complexity_score >= 5:
        return "HIGH"
    if complexity_score >= 2:
        return "MEDIUM"
    return "LOW"

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
    outputs = _requested_outputs(text, semantic, cognition, decision)
    measured_output, representation_state = _representation_consensus(outputs, semantic, decision)

    topic = _s(_field((semantic, decision, state), ("active_topic", "topic", "current_topic")))
    goal = _s(_field((decision, cognition, semantic), ("active_goal", "resolved_request", "goal"))) or text

    complexity = _complexity(semantic, cognition, decision, text)

    # Keep the current request intact; only add compact context when the
    # processor concluded that the turn depends on prior state.
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

    # Canonical dialogue contract consumed by provider_router._select_context_fields.
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

    # Preserve the provider's cost-balanced packing model:
    # provider_router is responsible for final <=900-token packing.
    request_metadata = {
        "processor_version": PROCESSOR_VERSION,
        "single_route": True,
        "provider_calls_per_request": 1,
        "context_mode": mode,
        "dialogue_coherence": round(coherence, 4),
    }

    # Keep user/flow identity in metadata for Provider duplicate/in-flight guard
    # without creating another route.
    if isinstance(state, dict):
        active_flow = state.get("active_flow") if isinstance(state.get("active_flow"), dict) else {}
        flow_id = state.get("flow_id") or active_flow.get("flow_id")
        if flow_id:
            request_metadata["flow_id"] = flow_id

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
        },
        metadata=request_metadata,
    )

    request.response_complexity = complexity
    request.response_output_tokens = OUTPUT_TOKENS[complexity]
    request.max_output_tokens = OUTPUT_TOKENS[complexity]
    request.quantum_state = {
        "dialogue": dialogue_state,
        "representation": representation_state,
        "measured_output": measured_output,
        "evidence_channels": len(evidence),
        "coherence": round(coherence, 4),
    }
    request.dialogue_contract = dialogue_contract
    request.single_route = True
    request.provider_calls_allowed = 1

    return request

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


def _canonicalize(user_id: str, response: MachineResponse, state: dict, semantic: dict, cognition: dict, decision: dict, request: MachineRequest) -> dict:
    answer = _s(response.answer) or _s(response.content) or _s(response.response)
    response.answer = answer
    response.content = answer
    if not response.summary:
        response.summary = answer[:500]
    response.metadata = dict(response.metadata or {})
    response.metadata.update({"processor_version": PROCESSOR_VERSION, "single_route": True, "provider_calls_per_request": 1})
    response.quantum_state = request.quantum_state
    response.conversation_space = {"current_turn": {"user": _s(request.conversation.get("current_request")), "april": {"answer": answer, "render_blocks": response.render_blocks}}}
    response.executor_semantic = semantic
    response.executor_cognition = cognition
    response.executor_response_decision = decision
    # Preserve provider-owned render signals before the canonical Factory projection.
    scene = build_machine_scene(response)
    provider_blocks = list(getattr(response, "render_blocks", []) or [])
    if provider_blocks:
        try:
            scene.blocks = provider_blocks
            scene.contract.blocks = provider_blocks
            scene.contract.render_blocks = list(provider_blocks)
        except Exception:
            pass
    contract = build_scene_contract(scene)
    # Factory/SceneContract is authoritative; no second renderer path exists.
    update_dialog_context(user_id, semantic)
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
        "single_route": True,
        "provider_calls_per_request": 1,
        "quantum_state": request.quantum_state,
        "energy_acceleration": request.metadata.get("energy_acceleration", {}),
    }


async def execute(user_id, chat_id=None, text="", run_with_activity=None, **kwargs):
    """One route: analyze → ensemble-collapse → MachineRequest → Provider → SceneContract."""
    state = get_state(user_id)
    state = state if isinstance(state, dict) else {}
    active_flow = state.get("active_flow")
    active_flow = active_flow if isinstance(active_flow, dict) else {}
    dialog_state = state.get("scene_state")
    dialog_state = dialog_state if isinstance(dialog_state, dict) else {}
    semantic = semantic_analyze(
        text=text,
        state=state,
        history=state.get("dialog", []),
        active_flow=active_flow,
        dialog_state=dialog_state,
    )
    reasoning = build_reasoning_state(text=text, semantic=semantic, state=state)
    cognition = analyze_cognition(text=text, semantic=semantic, reasoning=reasoning, state=state)
    visual = build_visual_reference(semantic=semantic, cognition=cognition, text=text, state=state)
    decision = build_response_decision(semantic=semantic, cognition=cognition, state=state, visual_reference=visual)
    request = _make_request(text, semantic, cognition, decision, state, visual)

    # Local quantum-inspired acceleration: structured evidence is fused before
    # the existing single Provider call. It cannot create a second route or
    # increase Provider entitlement beyond the user's plan.
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

    provider_result = await generate_text(
        request,
        max_output_tokens=request.response_output_tokens,
    )
    response = _response(provider_result)
    return _canonicalize(user_id, response, state, semantic, cognition, decision, request)
