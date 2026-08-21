"""
APRIL — RESPONSE DECISION QUANTUM V1

Role:
    Response-decision evidence/fusion layer.

The Quantum Processor owns the canonical decision.
This module:
    - fuses semantic/cognition/visual/scene signals;
    - preserves trajectory and dialogue continuity;
    - evaluates representation candidates;
    - packages one canonical machine decision.

It does NOT:
    - call providers;
    - create a parallel route;
    - render frontend output;
    - mutate presentation payloads;
    - hard-code one renderer per keyword.

Compatibility:
    build_response_decision(...) remains the public entry point.
"""

from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional


APRIL_FILE_ID = "APRIL_RESPONSE_DECISION_QUANTUM_V1"
DECISION_OWNER = "QUANTUM_PROCESSOR"
ROUTE_ID = "APRIL_SINGLE_ROUTE"

DECISION_MODES = ("talk", "guide", "execute", "render", "generate", "clarify", "correct")

INPUT_MACHINE_CHANNEL = {
    "source": "executor_core",
    "target": "response_decision",
    "mode": "machine_input",
    "isolated": True,
}
OUTPUT_MACHINE_CHANNEL = {
    "source": "response_decision",
    "target": "rooms_router",
    "mode": "machine_output",
    "isolated": True,
}

DECISION_PATCH_LOG: List[str] = []


def decision_log(msg: Any) -> None:
    try:
        DECISION_PATCH_LOG.append(str(msg))
        print("APRIL DECISION:", msg)
    except Exception:
        pass


def decision_enter() -> Dict[str, Any]:
    decision_log("ENTER DECISION LAYER")
    return {
        "decision_active": True,
        "machine_isolation": True,
        "trajectory_safe": True,
        "decision_owner": DECISION_OWNER,
    }


def decision_exit(result: Dict[str, Any]) -> Dict[str, Any]:
    decision_log(f"EXIT DECISION: {result.get('final_action')}")
    return {
        "decision_complete": True,
        "final_action": result.get("final_action"),
        "response_mode": result.get("response_mode"),
    }


def decision_future(*args, **kwargs):
    return None


def _d(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _b(value: Any) -> bool:
    return bool(value)


def _s(value: Any) -> str:
    return str(value or "").strip()

def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _clamp(value: Any, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, _f(value)))


def _unique(values: Iterable[Any]) -> List[Any]:
    result = []
    seen = set()
    for value in values:
        key = repr(value)
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _representation_set(semantic: Dict[str, Any], representation: Dict[str, Any]) -> List[str]:
    values = []
    for key in ("required_representations", "candidate_representations"):
        raw = semantic.get(key, [])
        if isinstance(raw, (list, tuple, set)):
            values.extend(raw)
    for key in ("requested_representation", "current_representation"):
        if semantic.get(key):
            values.append(semantic[key])
    if representation.get("subject_type") and representation["subject_type"] != "text":
        values.append(representation["subject_type"])
    return _unique(values)


def _representation_signals(semantic: Dict[str, Any], cognition: Dict[str, Any]) -> Dict[str, Any]:
    representation = _d(cognition.get("representation_understanding"))
    constraints = _d(
        semantic.get("representation_constraints")
        or _d(semantic.get("semantic_evidence")).get("representation_constraints")
    )
    blocked = {_s(x).lower() for x in (constraints.get("negative", []) or []) if _s(x)}

    posterior = semantic.get("representation_posteriors")
    if not isinstance(posterior, dict):
        posterior = {}

    weights = {
        _s(key).lower(): _clamp(value)
        for key, value in posterior.items()
        if _s(key)
    }

    current_positive = []
    for source in (
        constraints.get("positive", []),
        semantic.get("requested_representations", []),
        semantic.get("required_representations", []),
    ):
        values = [source] if isinstance(source, str) else list(source or []) if isinstance(source, (list, tuple, set)) else []
        for value in values:
            name = _s(value).lower()
            if name and name not in blocked and name not in current_positive:
                current_positive.append(name)

    for item in current_positive:
        if item not in weights:
            weights[item] = 0.0
        weights[item] += 0.35

    if not weights:
        weights = {"text": 1.0}

    # Canonical presentation rule: a structured renderer must have positive
    # evidence from the CURRENT request. Relative posterior mass is not enough
    # to manufacture a table/link/graph for an unrelated question.
    explicit_outputs = [
        name for name in current_positive
        if name not in blocked and name != "text"
    ]
    requested_outputs = ["text", *dict.fromkeys(explicit_outputs)]
    if not explicit_outputs:
        requested_outputs = ["text"]

    candidates = [x for x in _representation_set(semantic, representation) if x not in blocked]
    for item in current_positive:
        if item not in candidates:
            candidates.append(item)

    return {
        "requested": next((x for x in requested_outputs if x != "text"), requested_outputs[0]),
        "requested_outputs": requested_outputs,
        "candidates": candidates,
        "blocked": sorted(blocked),
        "weights": weights,
        "posterior": posterior,
        "text_explanation": _b(representation.get("prefer_text_explanation")),
        "interaction_mode": representation.get("interaction_mode"),
        "current_request_authoritative": True,
        "source": "quantum_representation_evidence",
    }

def _continuity_signals(cognition: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    continuity = _d(cognition.get("continuity_state"))
    contract = _d(cognition.get("dialogue_contract"))
    loops = _d(cognition.get("loop_analysis"))
    focus = _d(cognition.get("focus_recommendation") or cognition.get("dynamic_focus"))
    memory = _d(cognition.get("memory_analysis") or cognition.get("memory_signals"))

    active_flow = state.get("active_flow")
    continuation = (
        _b(cognition.get("needs_continuation"))
        or _b(continuity.get("user_waiting_answer"))
        or _b(contract.get("continuation"))
        or _b(active_flow)
        or _b(loops.get("has_open_loops"))
    )

    return {
        "continuation": continuation,
        "active_flow": bool(active_flow),
        "open_loops": _b(loops.get("has_open_loops")),
        "memory_priority": _clamp(memory.get("memory_priority", 0.0)),
        "focus_locked": _b(focus.get("focus_locked")),
        "contract": contract,
    }


def _dialogue_signals(semantic: Dict[str, Any], cognition: Dict[str, Any]) -> Dict[str, Any]:
    flags = (
        "discussion_mode",
        "reflection_mode",
        "space_discussion",
        "tool_discussion",
        "self_action_discussion",
        "explanation_mode",
    )
    active = any(_b(semantic.get(k)) for k in flags)
    unresolved = semantic.get("unresolved_intent", True)
    return {
        "dialogue_active": active or bool(unresolved),
        "reflection": _b(semantic.get("reflection_mode")),
        "explanation": _b(semantic.get("explanation_mode")),
        "unresolved": bool(unresolved),
        "flags": {k: _b(semantic.get(k)) for k in flags},
    }


def _execution_score(semantic: Dict[str, Any], cognition: Dict[str, Any], ambiguity: float) -> float:
    explicit = _f(semantic.get("execution_pressure", cognition.get("execution_pressure", 0.0)))
    wants_result = _f(cognition.get("wants_result", semantic.get("wants_result", 0.0)))
    action = _f(cognition.get("wants_action", 0.0))
    scene_state = _d(semantic.get("scene_semantic_state"))
    task_phase = _s(scene_state.get("task_phase")).lower()
    scene_relation = _d(semantic.get("dialogue_relation"))
    phase_mass = {
        "execution": 0.92,
        "modification": 0.82,
        "comparison": 0.48,
        "proposal": 0.08,
        "explanation": 0.06,
        "recall": 0.02,
        "continuation": 0.58,
    }.get(task_phase, 0.0)
    relation_mass = _f(scene_relation.get("confidence", 0.0)) if scene_relation.get("same_scene") else 0.0
    base = max(explicit, wants_result, action, phase_mass * max(0.65, relation_mass))
    return _clamp(base * (1.0 - 0.55 * ambiguity))


def _render_score(
    semantic: Dict[str, Any],
    cognition: Dict[str, Any],
    representation: Dict[str, Any],
    dialogue: Dict[str, Any],
) -> float:
    score = 0.0
    if semantic.get("render_intent") or semantic.get("prefer_renderer") or semantic.get("renderer_request"):
        score += 0.55
    if cognition.get("prefer_renderer"):
        score += 0.20
    if representation.get("requested"):
        score += 0.25
    if representation.get("requested_outputs"):
        score += min(0.25, 0.10 * len(representation["requested_outputs"]))
    if representation.get("candidates"):
        score += 0.15
    if dialogue.get("explanation") and representation.get("text_explanation"):
        score -= 0.45
    return _clamp(score)


def _generation_score(semantic: Dict[str, Any], cognition: Dict[str, Any], ambiguity: float, render_score: float) -> float:
    if not semantic.get("visual_generation_needed"):
        return 0.0
    if not semantic.get("explicit_image_generation_only"):
        return 0.0
    if semantic.get("avoid_image_generation_fallback", True):
        return 0.0
    restraint = _f(cognition.get("assistant_restraint", 0.0))
    return _clamp(0.85 * (1.0 - ambiguity) * (1.0 - restraint) * (1.0 - render_score))


def _clarification_required(
    semantic: Dict[str, Any],
    cognition: Dict[str, Any],
    scene_has_visual: bool,
) -> tuple[bool, Optional[str]]:
    if semantic.get("needs_image") and not scene_has_visual:
        return True, "image"
    if semantic.get("needs_formula") and not semantic.get("formula_present"):
        return True, "formula"
    if semantic.get("needs_comparison") and not semantic.get("comparison_ready"):
        return True, "comparison_source"
    if _f(semantic.get("ambiguity_level", 0.0)) >= 0.85 and not semantic.get("requested_representation"):
        return True, "ambiguous_request"
    return False, None


def _artifact_scene(semantic: Dict[str, Any]) -> tuple[Dict[str, Any], List[Any]]:
    bundle = _d(semantic.get("artifact_bundle"))
    primary = bundle.get("primary", [])
    secondary = bundle.get("secondary", [])
    primary = primary if isinstance(primary, list) else []
    secondary = secondary if isinstance(secondary, list) else []
    return bundle, primary + secondary


def _canonical_action(
    *,
    semantic: Dict[str, Any],
    dialogue: Dict[str, Any],
    representation: Dict[str, Any],
    execution_score: float,
    render_score: float,
    generation_score: float,
    clarification: bool,
    cognition: Dict[str, Any],
) -> str:
    """Collapse continuous evidence into one action without thresholded renderer triggers."""
    if clarification:
        return "clarify"

    scene_state = _d(cognition.get("scene_semantic_state") or semantic.get("scene_semantic_state"))
    task_phase = _s(scene_state.get("task_phase")).lower()
    scene_relation = _d(semantic.get("dialogue_relation"))
    requested = [
        _s(x).lower()
        for x in (representation.get("requested_outputs") or [])
        if _s(x)
    ]
    explicit_structured = [name for name in requested if name != "text"]
    if not explicit_structured:
        return "talk"

    # Execution is a task phase, not a renderer trigger. When the current
    # semantic scene says the user has moved from proposal/explanation into
    # execution, the processor owns that phase transition and the selected
    # artifact remains the output of the same execution.
    if (
        task_phase in {"execution", "modification"}
        and scene_relation.get("same_scene")
        and execution_score >= 0.45
    ):
        return "execute"

    structured_mass = sum(
        _f(representation.get("weights", {}).get(name, 0.0))
        for name in explicit_structured
    )
    dialogue_explanation = bool(
        dialogue.get("explanation") and representation.get("text_explanation")
    )
    guidance = bool(
        _b(cognition.get("needs_guidance"))
        or _b(cognition.get("exploration_mode"))
    )

    # Four competing utilities. A renderer wins because of the fused
    # representation state, not because one word activated a renderer branch.
    utilities = {
        "talk": 0.32 + (0.18 if dialogue_explanation else 0.0) + (0.10 if guidance else 0.0),
        "render": 0.24 + render_score * 0.62 + structured_mass * 0.28,
        "execute": 0.20 + execution_score * 0.72,
        "generate": 0.12 + generation_score * 0.88,
        "guide": 0.18 + (0.35 if guidance else 0.0),
    }

    if requested and any(name != "text" for name in requested):
        utilities["render"] += 0.20

    # Never let non-explicit visual generation outrank the normal response.
    if not _b(cognition.get("explicit_visual_generation")):
        utilities["generate"] *= 0.35

    return max(utilities, key=utilities.get)


def build_response_decision(
    semantic: dict,
    cognition: dict,
    visual_reference: dict,
    state: dict,
) -> Dict[str, Any]:
    """
    Fuse the existing machine signals into ONE canonical decision packet.

    Final routing remains owned by the Quantum Processor. This function does
    not call a provider, room, renderer, or frontend.
    """
    decision_enter()

    semantic = _d(semantic)
    cognition = _d(cognition)
    visual_reference = _d(visual_reference)
    state = _d(state)
    scene_state = _d(
        cognition.get("scene_semantic_state")
        or semantic.get("scene_semantic_state")
    )

    representation = _representation_signals(semantic, cognition)
    continuity = _continuity_signals(cognition, state)
    dialogue = _dialogue_signals(semantic, cognition)

    ambiguity = _clamp(semantic.get("ambiguity_level", 0.0))
    scene_continuity = _d(state.get("visual_continuity_summary"))
    active_scene = _d(state.get("active_scene"))
    scene_has_visual = bool(visual_reference or scene_continuity or active_scene)

    clarification, missing = _clarification_required(
        semantic, cognition, scene_has_visual
    )

    execution_score = _execution_score(semantic, cognition, ambiguity)
    render_score = _render_score(semantic, cognition, representation, dialogue)
    generation_score = _generation_score(
        semantic, cognition, ambiguity, render_score
    )

    # Preserve explicit user direction as a strong negative signal against
    # autonomous execution when the cognition layer says the user is leading.
    if cognition.get("user_leads_direction") and cognition.get("exploration_mode"):
        execution_score *= 0.25

    # Continuation never creates a new route; it only protects trajectory.
    should_continue = continuity["continuation"]

    final_action = _canonical_action(
        semantic=semantic,
        dialogue=dialogue,
        representation=representation,
        execution_score=execution_score,
        render_score=render_score,
        generation_score=generation_score,
        clarification=clarification,
        cognition=cognition,
    )

    if final_action == "render":
        response_mode = "renderer_space"
    elif final_action == "generate":
        response_mode = "visual_generation"
    elif final_action == "execute":
        response_mode = "execution"
    elif final_action == "guide":
        response_mode = "guidance"
    elif final_action == "clarify":
        response_mode = "clarification"
    else:
        response_mode = "continuation" if should_continue else "balanced"

    # Artifact information is passed intact. No mutation or renderer rewrite.
    artifact_bundle, artifact_scene = _artifact_scene(semantic)

    required = semantic.get("required_representations", [])
    required = list(required) if isinstance(required, (list, tuple, set)) else []
    required.extend(representation.get("requested_outputs", []))

    blocked = set(representation.get("blocked", []))
    required = [x for x in required if x not in blocked]

    candidate = semantic.get("candidate_representations", [])
    candidate = list(candidate) if isinstance(candidate, (list, tuple, set)) else []
    candidate.extend(representation["candidates"])
    candidate = [x for x in candidate if x not in blocked]

    if required and "text" not in required:
        required.insert(0, "text")

    contract = _d(semantic.get("dialogue_contract"))
    active_goal = (
        contract.get("active_goal")
        or cognition.get("active_goal")
        or _d(cognition.get("goal_analysis")).get("active_goal")
    )
    active_topic = (
        contract.get("active_topic")
        or cognition.get("active_topic")
        or semantic.get("active_topic")
        or semantic.get("current_topic")
    )

    result = {
        "decision_id": APRIL_FILE_ID,
        "decision_owner": DECISION_OWNER,
        "route_id": ROUTE_ID,

        "machine_routing": {
            "input_channel": INPUT_MACHINE_CHANNEL,
            "output_channel": OUTPUT_MACHINE_CHANNEL,
            "routing_mode": "single_route_machine_logic",
            "human_layer_allowed": False,
            "renderer_safe": True,
            "presentation_mutation_allowed": False,
            "provider_calls": 0,
            "parallel_route": False,
        },

        "final_action": final_action,
        "response_mode": response_mode,

        "scores": {
            "execution": _clamp(execution_score),
            "render": _clamp(render_score),
            "generation": _clamp(generation_score),
            "ambiguity": ambiguity,
        },

        "decision_evidence": {
            "dialogue": dialogue,
            "continuity": continuity,
            "representation": representation,
            "scene_has_visual": scene_has_visual,
            "clarification": clarification,
            "missing_information_type": missing,
        },

        "should_execute": final_action == "execute",
        "execution_allowed": final_action == "execute",
        "should_render": final_action in {"render", "execute"},
        "render_allowed": final_action in {"render", "execute"},
        "renderer_first_mode": final_action == "render",
        "renderer_hard_lock": False,

        "should_generate": final_action == "generate",
        "generation_allowed": final_action == "generate",
        "avoid_heavy_generation": final_action != "generate",

        "should_guide": final_action == "guide",
        "guidance_allowed": final_action == "guide",

        "should_continue_trajectory": should_continue,
        "maintain_dialog_continuity": True,
        "maintain_goal_trajectory": True,

        "preferred_representation": representation["requested"],
        "requested_representation": representation["requested"],
        "requested_outputs": _unique(required),
        "required_outputs": _unique(required),
        "blocked_representations": sorted(blocked),
        "required_representations": _unique(required),
        "candidate_representations": _unique(candidate),

        "understands_user_goal": bool(
            cognition.get("understands_user_goal")
            or execution_score >= 0.5
            or render_score >= 0.5
        ),
        "understands_user_direction": _b(cognition.get("user_leads_direction")),
        "should_follow_user": _b(cognition.get("user_leads_direction")),

        "trajectory_protection": True,
        "human_continuity": True,
        "avoid_trigger_behavior": True,
        "avoid_overthinking": True,
        "avoid_recursive_analysis": True,
        "avoid_context_rebuild": True,

        "dialogue_still_alive": True,
        "goal_completed": False,
        "scene_practical_goal_alive": bool(execution_score >= 0.45),
        "scene_completion_required": bool(semantic.get("unresolved_intent", True)),

        "needs_reflection": ambiguity >= 0.45,
        "needs_post_action_analysis": final_action in {"execute", "render", "generate"},

        "high_ambiguity_detected": ambiguity >= 0.45,
        "response_requires_clarification": clarification,

        "block_image_generation_fallback": True,
        "allow_only_explicit_generation": True,
        "provider_safe_rendering": True,

        "web_space_ready": True,
        "botru_compatible": True,
        "renderer_payload_safe": True,
        "presentation_layer_separated": True,

        "decision_style": "quantum_evidence_fusion",
        "continuity_mode": "active",
        "reasoning_pressure": "balanced",
        "scene_priority": True,
        "dialog_priority": dialogue["dialogue_active"],

        "goal_stage": semantic.get("goal_stage", scene_state.get("task_phase", "exploration")),
        "task_phase": scene_state.get("task_phase"),
        "operation": scene_state.get("operation"),
        "requested_scene_representation": scene_state.get("requested_representation"),
        "memory_priority": continuity["memory_priority"],
        "focus_locked": continuity["focus_locked"],
        "has_open_loops": continuity["open_loops"],

        "active_scene": active_scene,
        "visual_continuity": scene_continuity,
        "scene_driven_response": True,
        "renderer_intelligence_enabled": True,

        "task_requires_clarification": clarification,
        "missing_information_type": missing,
        "scene_confidence": (
            0.35 if (not scene_has_visual and _f(cognition.get("wants_visual")) >= 0.5)
            else (0.5 if ambiguity >= 0.45 else 1.0)
        ),
        "scene_has_visual": scene_has_visual,
        "scene_has_active_objects": bool(active_scene),

        "internal_reasoning_only": bool(
            dialogue["reflection"]
            or dialogue["flags"].get("tool_discussion")
            or dialogue["flags"].get("self_action_discussion")
        ),
        "assistant_guidance_priority": clarification or final_action == "guide",

        "artifact_bundle": artifact_bundle,
        "artifact_scene": artifact_scene,
        "scene_composition_ready": bool(artifact_scene),

        # Canonical dialogue contract — one machine object, no second route.
        "dialogue_contract": contract,
        "dialog_act": contract.get("dialog_act", "statement"),
        "reply_to": contract.get("reply_to"),
        "active_goal": active_goal,
        "active_topic": active_topic,
        "resolved_request": contract.get("resolved_request")
            or semantic.get("normalized_text", ""),
        "response_goal": active_goal or semantic.get("normalized_text", ""),
        "response_strategy": (
            "continue_previous_turn"
            if contract.get("continuation")
            else "answer_current_request"
        ),
        "context_dependency": (
            contract.get("context_dependency")
            or semantic.get("context_dependency")
            or ("continuation" if contract.get("continuation") else "independent")
        ),
        "avoid_machine_echo": True,
        "avoid_duplicate_answer": True,
        "single_canonical_answer": True,

        # Quantum ownership: this layer supplies evidence, the processor owns
        # final arbitration across the whole factory.
        "quantum_evidence": {
            "current_request": semantic.get("normalized_text"),
            "representation": representation,
            "required_outputs": _unique(required),
            "blocked_representations": sorted(blocked),
            "dialogue": dialogue,
            "continuity": continuity,
            "scores": {
                "execution": execution_score,
                "render": render_score,
                "generation": generation_score,
                "ambiguity": ambiguity,
            },
        },
    }

    result["context_policy"] = semantic.get("context_policy", {
        "current_request": True,
        "dialogue_vector": continuity["continuation"],
        "previous_turn": bool(contract.get("reply_to") or contract.get("previous_april_turn")),
        "active_goal": bool(active_goal and continuity["continuation"]),
        "full_history": False,
    })

    decision_exit(result)
    return result


# Compatibility alias for integrations that used the internal name.
_base_build_response_decision = build_response_decision
