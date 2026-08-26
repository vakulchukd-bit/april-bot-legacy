# ================================================================
# APRIL SEMANTIC CORE — QUANTUM EVIDENCE ENGINE v2 — UNIFIED PRODUCTION SIGNAL
# ================================================================
"""
Role:
    Semantic evidence / signal fusion layer.

This module does NOT own routing, execution, provider calls, or renderer
selection. It produces one machine-readable evidence packet for the
Quantum Processor through the existing semantic pipeline.

Design law:
    current request + dialogue + memory + scene + modality signals
    -> evidence vectors -> Quantum Processor

No parallel route. No provider call. No renderer trigger.
"""

from blocks.interpretation_layer import interpret_request
import math
import re

APRIL_FILE_ID = "APRIL_SEMANTIC_CORE"
SEMANTIC_ENGINE_VERSION = "quantum_evidence_v4_dialogue_vector_unified_production_signal"
SEMANTIC_MACHINE_CHANNEL = {
    "type": "semantic_core",
    "mode": "quantum_evidence_unified",
    "version": SEMANTIC_ENGINE_VERSION,
    "isolated": True,
    "continuity_safe": True,
    "renderer_safe": True,
    "web_safe": True,
}

SEMANTIC_ENGINE_LOG = []
MAX_SEMANTIC_LOGS = 120

def safe_semantic_log(msg):
    try:
        print("SEMANTIC CORE:", msg)
        SEMANTIC_ENGINE_LOG.append(str(msg))
        if len(SEMANTIC_ENGINE_LOG) > MAX_SEMANTIC_LOGS:
            del SEMANTIC_ENGINE_LOG[:-MAX_SEMANTIC_LOGS]
    except Exception:
        pass

safe_semantic_log("QUANTUM SEMANTIC CORE INITIALIZED")

def clamp(value, minimum=0.0, maximum=1.0):
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0
    return max(minimum, min(maximum, value))

def contains_any(text, words):
    text = (text or "").lower()
    return any(word in text for word in words)

def safe_probability(value, boost=0.0):
    return clamp((value or 0.0) + boost)

# ----------------------------------------------------------------
# Evidence vocabulary. These are evidence sources, not commands.
# ----------------------------------------------------------------
# Legacy lexical trigger vocabularies are intentionally removed from the
# decision path. These projections are derived only from the Interpretation
# matrix and its capability/representation measurements.
RENDERER_WORDS = ()
IMAGE_WORDS = ()
VISUAL_WORDS = ()
EXECUTION_WORDS = ()
DISCUSSION_WORDS = ()
REFLECTION_WORDS = ()
SPACE_WORDS = ()
GRAPH_WORDS = ()
TABLE_WORDS = ()
LINK_WORDS = ()
MATH_WORDS = ()

REPRESENTATION_NEGATIONS = {}
REPRESENTATION_POSITIVES = {}

CONTINUATION_WORDS = ()
REFERENCE_WORDS = ()

DOMAIN_WORDS = {
    "biology": ("биология","генетика","эволюция","клетка","организм","экология","бактерии","днк","животные","растения"),
    "chemistry": ("химия","реакция","молекула","атом","вещество"),
    "physics": ("физика","энергия","сила","ускорение","электричество"),
    "engineering": ("инженерия","конструкция","механизм","система","проектирование"),
    "it": ("программирование","алгоритм","сервер","код","разработка"),
    "literature": ("литература","роман","поэзия","писатель","произведение"),
    "politics": ("политика","государство","выборы","правительство"),
    "news": ("новости","события","последние новости"),
    "social": ("общество","социум","социальный"),
    "web": ("сайт","интернет","поиск","веб"),
}

def _matrix_score(interpreted, family, label):
    profile = interpreted.get("quantum_interpretation_evidence") if isinstance(interpreted, dict) else {}
    if isinstance(profile, dict):
        scores = profile.get(f"{family}_scores")
        if isinstance(scores, dict):
            try:
                return clamp(scores.get(label, 0.0))
            except Exception:
                pass
    scores = interpreted.get(f"{family}_scores") if isinstance(interpreted, dict) else {}
    if isinstance(scores, dict):
        return clamp(scores.get(label, 0.0))
    return 0.0

def detect_renderer_probability(text, interpreted=None):
    reps = interpreted.get("quantum_representation_measurement", {}) if isinstance(interpreted, dict) else {}
    measurements = reps.get("measurements") if isinstance(reps, dict) else []
    if isinstance(measurements, dict):
        values = [
            float(value or 0.0)
            for key, value in measurements.items()
            if str(key).lower() != "text"
        ]
    elif isinstance(measurements, list):
        values = [
            float(item.get("score", 0.0) or 0.0)
            for item in measurements
            if isinstance(item, dict) and item.get("type") != "text"
        ]
    else:
        values = []
    return clamp(max(values, default=0.0))

def detect_image_generation_probability(text, interpreted=None):
    return _matrix_score(interpreted or {}, "representation", "image")

def detect_visual_probability(text, interpreted=None):
    return detect_renderer_probability(text, interpreted)

def detect_execution_probability(text, interpreted=None):
    return _matrix_score(interpreted or {}, "capability", "exploration")

def detect_discussion_probability(text, interpreted=None):
    return _matrix_score(interpreted or {}, "capability", "discussion")

def detect_reflection_probability(text, interpreted=None):
    return _matrix_score(interpreted or {}, "capability", "information")

def detect_space_discussion_probability(text, interpreted=None):
    return _matrix_score(interpreted or {}, "capability", "space")

def detect_representation_request(text, interpreted=None):
    constraints = detect_representation_constraints(text, interpreted)
    positive = constraints.get("positive", [])
    return positive[0] if positive else None

def detect_graph_action(text, interpreted=None):
    profile = interpreted if isinstance(interpreted, dict) else {}
    requested = profile.get("requested_representation") or profile.get("preferred_representation")
    return "build" if requested == "graph" else "unknown"

def detect_domain_candidates(text, interpreted=None):
    candidates = []
    src = interpreted if isinstance(interpreted, dict) else {}
    values = src.get("candidate_domains") or src.get("required_domains") or []
    for domain in values:
        if str(domain) not in candidates:
            candidates.append(str(domain))
    return candidates


def _clean_representation(value):
    value = str(value or "").strip().lower()
    aliases = {
        "chart": "graph",
        "plot": "graph",
        "diagram": "diagram",
        "schematic": "diagram",
        "flowchart": "diagram",
        "math": "formula",
        "equation": "formula",
        "url": "link",
        "link_card": "link",
        "media": "gallery",
    }
    value = aliases.get(value, value)
    return value if value in REPRESENTATION_UNIVERSE else ""


def _representation_scores(interpreted):
    interpreted = interpreted if isinstance(interpreted, dict) else {}
    raw = interpreted.get("representation_scores")
    if isinstance(raw, dict):
        return {
            _clean_representation(k): clamp(v)
            for k, v in raw.items()
            if _clean_representation(k)
        }

    evidence = interpreted.get("representation_evidence") or []
    scores = {}
    for item in evidence:
        if not isinstance(item, dict):
            continue
        name = _clean_representation(item.get("label"))
        if name:
            scores[name] = max(scores.get(name, 0.0), clamp(item.get("score", 0.0)))
    return scores


def _locked_production_representation(interpreted):
    """
    Read only fields that are explicitly production-level.

    Evidence/candidate fields are deliberately excluded. This is the
    boundary that prevents an upstream measurement such as
    ['image', 'table'] from becoming a multi-render production command.
    """
    interpreted = interpreted if isinstance(interpreted, dict) else {}

    # Canonical interpretation transport has priority over evidence fields.
    # The latest Interpretation Engine exposes the selected production signal
    # separately from its complete measurement field.
    for container_key, label in (
        ("presentation_signals", "presentation_signals.resolved"),
        ("quantum_representation_measurement", "quantum_representation_measurement.resolved"),
        ("quantum_interpretation_evidence", "quantum_interpretation_evidence.resolved_representation"),
    ):
        container = interpreted.get(container_key)
        if isinstance(container, dict):
            for key in ("resolved", "production_representation", "resolved_representation"):
                value = _clean_representation(container.get(key))
                if value:
                    return value, f"{label}.{key}"

    for key in (
        "production_representation",
        "resolved_representation",
        "requested_representation",
        "preferred_representation",
    ):
        value = _clean_representation(interpreted.get(key))
        if value:
            return value, key

    locked = interpreted.get("production_representation_locked")
    if locked:
        values = interpreted.get("required_representations") or interpreted.get(
            "requested_representations"
        ) or []
        cleaned = [_clean_representation(v) for v in values]
        cleaned = [v for v in cleaned if v]
        if len(cleaned) == 1:
            return cleaned[0], "locked_required_representations"

    # A single explicit requested representation is safe. Multiple values
    # remain evidence unless an explicit multi-output lock exists.
    values = interpreted.get("requested_representations") or []
    cleaned = [_clean_representation(v) for v in values]
    cleaned = [v for v in cleaned if v]
    if len(cleaned) == 1:
        return cleaned[0], "single_requested_representation"

    # scene_type is a semantic interpretation field, not a lexical trigger.
    scene = _clean_representation(interpreted.get("scene_type"))
    if scene and scene != "text":
        return scene, "scene_type"

    return "", "unresolved"


def _evidence_candidates(interpreted):
    """
    Return evidence candidates without granting them production authority.
    """
    scores = _representation_scores(interpreted)
    names = []

    for item in interpreted.get("candidate_representations") or []:
        name = _clean_representation(item)
        if name and name not in names:
            names.append(name)

    for item in interpreted.get("required_representations") or []:
        name = _clean_representation(item)
        if name and name not in names:
            names.append(name)

    for name, score in scores.items():
        if name != "text" and score >= 0.20 and name not in names:
            names.append(name)

    return names, scores


def detect_representation_constraints(text, interpreted=None):
    """
    Produce representation *evidence*, not renderer commands.

    This function intentionally never marks a multi-value candidate set as
    authoritative. Production authority is resolved once, later, by
    _resolve_production_representation().
    """
    interpreted = interpreted if isinstance(interpreted, dict) else {}
    candidates, scores = _evidence_candidates(interpreted)
    production, source = _locked_production_representation(interpreted)

    negative = []
    constraints = interpreted.get("representation_constraints")
    if isinstance(constraints, dict):
        for item in constraints.get("negative") or []:
            name = _clean_representation(item)
            if name:
                negative.append(name)

    return {
        "positive": list(candidates),
        "negative": list(dict.fromkeys(negative)),
        "scores": scores,
        "production_representation": production,
        "production_source": source,
        "current_request_authoritative": bool(production),
        "source": "quantum_matrix_evidence",
    }


def _semantic_request_shape(interpreted):
    """
    Recover a production representation only from semantic interpretation
    fields. No lexical renderer trigger is introduced here.

    This is intentionally conservative: when the interpretation does not
    establish a production representation, the result remains unresolved and
    the downstream Quantum Processor retains authority.
    """
    interpreted = interpreted if isinstance(interpreted, dict) else {}

    # Strongest semantic fields first.
    for key in (
        "resolved_request",
        "operation",
        "task_phase",
        "content_role",
    ):
        value = interpreted.get(key)
        if isinstance(value, dict):
            for nested in (
                "representation", "resolved_representation",
                "requested_representation", "output_representation",
                "scene_type", "operation",
            ):
                rep = _clean_representation(value.get(nested))
                if rep and rep != "text":
                    return rep, f"{key}.{nested}"

    for key in ("resolved_request", "operation", "task_phase", "content_role"):
        rep = _clean_representation(interpreted.get(key))
        if rep and rep != "text":
            return rep, key

    scene_state = interpreted.get("scene_semantic_state")
    if isinstance(scene_state, dict):
        for key in (
            "production_representation",
            "resolved_representation",
            "requested_representation",
            "scene_type",
            "representation",
        ):
            rep = _clean_representation(scene_state.get(key))
            if rep and rep != "text":
                return rep, f"scene_semantic_state.{key}"

    return "", "unresolved"


def _resolve_production_representation(interpreted, constraints):
    """
    Resolve exactly one production representation.

    Priority:
      1) explicit production/resolved/requested signal;
      2) semantic scene/operation fields;
      3) a single high-confidence evidence candidate with a clear margin;
      4) text.

    Multiple unconfirmed candidates are never forwarded as production
    representations.
    """
    interpreted = interpreted if isinstance(interpreted, dict) else {}
    production, source = _locked_production_representation(interpreted)
    if production:
        return production, source, True

    semantic_rep, semantic_source = _semantic_request_shape(interpreted)
    if semantic_rep:
        return semantic_rep, semantic_source, True

    scores = dict(constraints.get("scores") or {})
    text_score = float(scores.get("text", 0.0) or 0.0)
    candidates = [
        (name, float(score or 0.0))
        for name, score in scores.items()
        if name in STRUCTURED_REPRESENTATIONS
        and name not in set(constraints.get("negative") or [])
    ]
    candidates.sort(key=lambda item: item[1], reverse=True)

    if candidates:
        best, best_score = candidates[0]
        second = candidates[1][1] if len(candidates) > 1 else 0.0
        if best_score >= 0.80 and best_score - max(second, text_score) >= 0.16:
            return best, "single_strong_evidence", True

    return "text", "unresolved_default", False

def build_artifact_bundle():
    return {"domain":"general","primary":[],"secondary":[]}

def enrich_artifact_bundle(bundle, semantic_result):
    if semantic_result.get("contains_object"):
        bundle["primary"].append("artifact")
    if semantic_result.get("contains_explanation"):
        bundle["secondary"].append("explanation")
    if semantic_result.get("contains_analysis"):
        bundle["secondary"].append("analysis")
    if semantic_result.get("contains_legend"):
        bundle["secondary"].append("legend")
    return bundle

def _state_signals(state, active_flow, dialog_state, history):
    cognition = state.get("cognition", {}) if isinstance(state, dict) else {}
    last_april = last_user = ""
    for item in reversed(history if isinstance(history, list) else []):
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").lower()
        if not last_april:
            obj = item.get("april") if isinstance(item.get("april"), dict) else item
            if role in {"assistant","april","bot"} or isinstance(item.get("april"), dict):
                last_april = str(obj.get("answer") or obj.get("content") or obj.get("summary") or obj.get("text") or "").strip()
        if not last_user:
            obj = item.get("user") if isinstance(item.get("user"), dict) else item
            if role in {"user","human"} or isinstance(item.get("user"), dict):
                last_user = str(obj.get("content") or obj.get("text") or obj.get("answer") or "").strip()
        if last_april and last_user:
            break
    current_scene = state.get("current_visual_scene") or state.get("active_visual_scene")
    dialog_act = str(
        (dialog_state.get("dialog_act") if isinstance(dialog_state, dict) else "")
        or ""
    ).strip().lower()
    allow_scene_as_previous = dialog_act not in {"memory_query", "new_topic", "independent"}
    if isinstance(current_scene, dict) and allow_scene_as_previous:
        if not last_user:
            last_user = str(
                current_scene.get("user_request")
                or current_scene.get("current_request")
                or ""
            ).strip()
        if not last_april:
            last_april = str(
                current_scene.get("april_answer")
                or current_scene.get("answer")
                or current_scene.get("summary")
                or ""
            ).strip()

    return {
        "focus": cognition.get("dynamic_focus", {}),
        "goal": cognition.get("goal_hierarchy", {}),
        "open_loops": cognition.get("open_loops", {}),
        "memory_signals": cognition.get("memory_signals", {}),
        "visual_topic_registry": state.get("visual_topic_registry", []),
        "task_context_storage": state.get("task_context_storage", []),
        "continuity_context_storage": state.get("continuity_context_storage", []),
        "memory_anchor_storage": state.get("memory_anchor_storage", []),
        "active_topic_slot": state.get("active_topic_slot", "A"),
        "active_visual_scene": current_scene,
        "active_flow": active_flow,
        "dialog_state": dialog_state,
        "history_depth": len(history),
        "last_april_turn": last_april or state.get("last_april_turn", ""),
        "last_user_turn": last_user or state.get("last_user_turn", ""),
        "current_scene_user_request": (
            current_scene.get("user_request") if isinstance(current_scene, dict) else ""
        ),
        "current_scene_april_answer": (
            current_scene.get("april_answer") if isinstance(current_scene, dict) else ""
        ),
    }

# Canonical production representations known by the Quantum Processor/Web
# contract.  Evidence may contain many candidates; production emits one
# representation unless the upstream interpretation explicitly locks a
# multi-output request.
REPRESENTATION_UNIVERSE = (
    "text", "table", "graph", "diagram", "formula",
    "gallery", "link", "code", "image",
    "audio", "video", "file", "action", "scene",
    "memory", "visual_context",
)

STRUCTURED_REPRESENTATIONS = tuple(
    name for name in REPRESENTATION_UNIVERSE if name != "text"
)

def _representation_posteriors(
    text: str,
    signals: dict,
    interpreted: dict,
    constraints: dict,
) -> tuple[dict[str, float], list[str], list[str]]:
    """
    Build an evidence posterior.

    The posterior is diagnostic. It is never itself a production renderer
    command. This keeps the Semantic Core useful for evidence fusion while
    preventing broad priors from creating multiple render outputs.
    """
    scores = {name: 0.10 for name in REPRESENTATION_UNIVERSE}
    for name, value in (constraints.get("scores") or {}).items():
        if name in scores:
            scores[name] = max(scores[name], clamp(value))

    # Continuity is allowed to support an already interpreted representation,
    # but never invents one from a previous scene.
    dialogue_contract = (
        interpreted.get("dialogue_contract")
        if isinstance(interpreted.get("dialogue_contract"), dict) else {}
    )
    continuity = bool(
        dialogue_contract.get("continuation")
        or dialogue_contract.get("reference_to_previous")
    )
    current_scene = _clean_representation(interpreted.get("scene_type"))
    visual = signals.get("active_visual_scene") if isinstance(signals, dict) else {}
    previous_types = set()
    if isinstance(visual, dict):
        previous_types.update(
            _clean_representation(x)
            for x in (visual.get("render_block_types") or visual.get("block_types") or [])
        )
    if continuity and current_scene in previous_types and current_scene != "text":
        scores[current_scene] = min(1.0, scores[current_scene] + 0.20)

    for name in constraints.get("negative") or []:
        if name in scores:
            scores[name] = 0.0

    temperature = 0.85
    exp_values = {
        key: math.exp(max(-20.0, min(20.0, value / temperature)))
        for key, value in scores.items()
    }
    total = sum(exp_values.values()) or 1.0
    posterior = {key: exp_values[key] / total for key in scores}

    top = sorted(posterior, key=posterior.get, reverse=True)
    selected = [
        key for key in top[:4]
        if posterior[key] >= 0.12
        and key not in set(constraints.get("negative") or [])
    ]
    return posterior, selected or ["text"], sorted(constraints.get("negative") or [])


def _signal_fusion(text, signals, interpreted):
    """
    Unified Semantic Core engine.

    Evidence is fused here, but production representation is resolved exactly
    once. The Quantum Processor remains the final execution authority.
    """
    constraints = detect_representation_constraints(text, interpreted)
    production, production_source, production_confident = (
        _resolve_production_representation(interpreted, constraints)
    )
    posterior, evidence_selected, blocked = _representation_posteriors(
        text, signals, interpreted, constraints
    )

    # Evidence candidates remain visible for diagnostics, but only one
    # production representation crosses the semantic->processor boundary.
    selected = [production]

    renderer_measurement = detect_renderer_probability(text, interpreted)
    image = detect_image_generation_probability(text, interpreted)
    visual = detect_visual_probability(text, interpreted)
    execution = detect_execution_probability(text, interpreted)
    discussion = detect_discussion_probability(text, interpreted)
    reflection = detect_reflection_probability(text, interpreted)

    history = signals["history_depth"]
    continuity = bool(
        signals["continuity_context_storage"]
        or interpreted.get("continuation")
        or interpreted.get("dialog_act") == "reference"
    )
    goal = bool(signals["goal"])
    memory = bool(signals["memory_signals"])

    structured_mass = (
        posterior.get(production, 0.0) if production != "text" else 0.0
    )

    if production != "text" and production_confident:
        # A canonical production signal is already resolved upstream. Its
        # confidence must not be re-downgraded by the evidence posterior.
        render_score = 1.0
    else:
        render_score = clamp(
            structured_mass * 0.85 + renderer_measurement * 0.15
            if production != "text" else 0.0
        )
    continuity_score = clamp(
        (0.30 if continuity else 0.0)
        + (0.20 if history else 0.0)
        + (0.20 if goal else 0.0)
        + (0.15 if memory else 0.0)
        + (0.15 if interpreted.get("dialogue_contract", {}).get("continuation") else 0.0)
    )
    execution_score = clamp(
        execution * 0.45
        + render_score * 0.20
        + structured_mass * 0.20
        + (0.10 if interpreted.get("dialogue_act") == "request" else 0.0)
        + (0.05 if goal else 0.0)
    )

    return {
        "renderer": render_score,
        "image": image,
        "visual": visual,
        "execution": execution_score,
        "discussion": discussion,
        "reflection": reflection,
        "continuity": continuity_score,
        "requested_representation": production,
        "requested_representations": list(selected),
        "required_representations": list(selected),
        "production_representation": production,
        "production_representation_source": production_source,
        "production_representation_confident": production_confident,
        "evidence_representations": list(dict.fromkeys(evidence_selected)),
        "representation_constraints": {
            **constraints,
            "negative": blocked,
        },
        "representation_posteriors": posterior,
        "representation_consensus": {
            "selected": list(selected),
            "evidence_candidates": list(dict.fromkeys(evidence_selected)),
            "production_representation": production,
            "production_confidence": posterior.get(production, 0.0),
            "production_source": production_source,
            "production_locked": production_confident,
            "entropy": -sum(
                p * math.log(max(p, 1e-12))
                for p in posterior.values()
            ),
        },
        "candidate_domains": detect_domain_candidates(text, interpreted),
        "evidence_count": sum(bool(x) for x in (
            evidence_selected, continuity, goal, memory, discussion, reflection
        )),
    }


def _base_result(text, signals):
    return {
        "machine_channel": SEMANTIC_MACHINE_CHANNEL,
        "semantic_core_active": True,
        "web_safe": True,
        "renderer_safe": True,
        "provider_safe": True,
        "semantic_role": "evidence_fusion_only",
        "semantic_authority": False,
        "semantic_machine_layer": True,
        "semantic_probability_based": True,
        "semantic_executor_expected": True,
        "intent": "text",
        "confidence": 0.0,
        "normalized_text": text,
        "render_intent": False,
        "prefer_renderer": False,
        "renderer_scene_object": False,
        "renderer_lightweight": True,
        "renderer_priority": 0.0,
        "prefer_local_rendering": False,
        "visual_generation_needed": False,
        "explicit_image_generation_only": False,
        "avoid_image_generation_fallback": True,
        "should_execute": False,
        "execution_pressure": 0.0,
        "execution_readiness": 0.0,
        "response_mode": "talk",
        "response_economy": "balanced",
        "provider_safe_mode": True,
        "provider_aware": True,
        "renderer_first": False,
        "anti_trigger_behavior": True,
        "anti_room_wars": True,
        "anti_hidden_escalation": True,
        "trajectory_active": bool(signals["active_flow"] or signals["continuity_context_storage"]),
        "trajectory_strength": 0.5,
        "preserve_flow": True,
        "conversation_alive": True,
        "current_topic": None,
        "current_object": None,
        "current_representation": "text",
        "requested_representation": None,
        "content_role": None,
        "contains_object": False,
        "contains_explanation": False,
        "contains_analysis": False,
        "contains_legend": False,
        "scene_composition_ready": False,
        "same_task": False,
        "representation_shift": False,
        "context_visual_followup": False,
        "unresolved_intent": True,
        "visual_continuity": bool(signals["active_visual_scene"]),
        "visual_routing": False,
        "active_visual_scene_detected": bool(signals["active_visual_scene"]),
        "scene_reference_detected": False,
        "possible_room": None,
        "possible_output": None,
        "possible_scene_type": None,
        "possible_capability": None,
        "required_domains": [],
        "candidate_domains": [],
        "required_representations": [],
        "candidate_representations": [],
        "requested_outputs": ["text"],
        "required_outputs": ["text"],
        "conversation_vector": signals,
        "semantic_state": {"conversation_vector": signals},
        "factory_targets": [],
        "factory_order": {},
        "decision_owner": "QUANTUM_PROCESSOR",
        "route_owner": "EXISTING_SINGLE_ROUTE",
        "provider_calls": 0,
    }

def _dialogue_context_matrix(text, signals, interpreted):
    prev_u, prev_a = str(signals.get("last_user_turn") or ""), str(signals.get("last_april_turn") or "")
    dc = interpreted.get("dialogue_contract") if isinstance(interpreted.get("dialogue_contract"), dict) else {}
    scene_relation = (
        interpreted.get("dialogue_relation")
        if isinstance(interpreted.get("dialogue_relation"), dict)
        else {}
    )
    reference_resolution = interpreted.get("dialogue_reference") if isinstance(interpreted.get("dialogue_reference"), dict) else {}
    if reference_resolution.get("resolved"):
        confidence = clamp(reference_resolution.get("confidence", 0.0))
        return {
            "context_dependency": True,
            "context_dependency_score": round(confidence, 4),
            "continuation": True,
            "continuation_score": round(confidence, 4),
            "reference_to_previous": True,
            "reference_score": round(confidence, 4),
            "dialog_act": "reference",
            "previous_user_turn": prev_u,
            "previous_april_turn": prev_a,
            "reference_resolution": reference_resolution,
            "active_topic": interpreted.get("active_topic") or reference_resolution.get("target"),
            "structured_continuity": True,
            "history_available": bool(prev_u or prev_a),
        }
    if scene_relation.get("same_scene"):
        confidence = clamp(scene_relation.get("confidence", 0.0))
        return {
            "context_dependency": True,
            "context_dependency_score": round(confidence, 4),
            "continuation": bool(scene_relation.get("continuation")),
            "continuation_score": round(confidence if scene_relation.get("continuation") else 0.0, 4),
            "reference_to_previous": bool(scene_relation.get("reference_to_previous")),
            "reference_score": round(confidence if scene_relation.get("reference_to_previous") else 0.0, 4),
            "dialog_act": (
                "continuation" if scene_relation.get("continuation")
                else "reference" if scene_relation.get("reference_to_previous")
                else dc.get("dialog_act", "request")
            ),
            "previous_user_turn": prev_u,
            "previous_april_turn": prev_a,
            "structured_continuity": True,
            "history_available": bool(prev_u or prev_a),
        }
    if str(dc.get("dialog_act") or "").lower() == "memory_query":
        return {
            "context_dependency": True,
            "context_dependency_score": 1.0,
            "continuation": False,
            "continuation_score": 0.0,
            "reference_to_previous": True,
            "reference_score": 1.0,
            "dialog_act": "memory_query",
            "previous_user_turn": prev_u,
            "previous_april_turn": prev_a,
            "structured_continuity": False,
            "history_available": bool(prev_u or prev_a),
        }
    total = max(1, len(str(text).split()))
    tokens = set(re.findall(r"[a-zа-яё0-9]{3,}", str(text).lower()))
    incomplete = 1.0 - min(1.0, len(tokens) / total)
    history = 1.0 if prev_u or prev_a else 0.0
    def overlap(a, b):
        aa = set(re.findall(r"[a-zа-яё0-9]{3,}", str(a).lower()))
        bb = set(re.findall(r"[a-zа-яё0-9]{3,}", str(b).lower()))
        return len(aa & bb) / max(1.0, min(len(aa), len(bb))) if aa and bb else 0.0
    affinity = max(overlap(text, prev_u), overlap(text, prev_a))
    visual = signals.get("active_visual_scene") if isinstance(signals, dict) else {}
    visual = visual if isinstance(visual, dict) else {}
    rep = str(interpreted.get("scene_type") or "").lower()
    previous_types = {str(x).lower() for x in (
        visual.get("render_block_types") or visual.get("block_types") or []
    )}
    structured = 1.0 if rep and rep != "text" and rep in previous_types else 0.0
    evidence = any(
        isinstance(x, dict) and str(x.get("label") or "").lower() == rep
        and float(x.get("score", 0.0) or 0.0) >= 0.24
        for x in (interpreted.get("representation_evidence") or [])
    )
    capitalized = len(re.findall(r"\b[А-ЯA-ZЁ][а-яa-zё-]{2,}\b", prev_a))
    entity_context = 1.0 if prev_a and incomplete >= 0.30 and capitalized >= 2 else 0.0
    dc = interpreted.get("dialogue_contract") if isinstance(interpreted.get("dialogue_contract"), dict) else {}
    semantic_rel = max(float(dc.get("continuation_score", 0.0) or 0.0),
                       float(dc.get("reference_score", 0.0) or 0.0))
    score = clamp(
        0.22*incomplete + 0.12*history + 0.18*structured +
        0.16*affinity + 0.16*evidence + 0.52*entity_context + 0.10*semantic_rel
    )
    if len(tokens) >= 2 and affinity < 0.05 and not structured and incomplete < 0.55:
        score = clamp(score - 0.14)
    depends = bool(history and score >= 0.53)
    reference = bool(depends and (structured or entity_context or float(dc.get("reference_score", 0.0) or 0.0) >= 0.5))
    continuation = bool(depends and not reference)
    return {
        "context_dependency": depends, "context_dependency_score": round(score, 4),
        "continuation": continuation, "continuation_score": round(score if continuation else 0.0, 4),
        "reference_to_previous": reference, "reference_score": round(score if reference else 0.0, 4),
        "dialog_act": "reference" if reference else "continuation" if continuation else dc.get("dialog_act", "request"),
        "previous_user_turn": prev_u, "previous_april_turn": prev_a,
        "structured_continuity": bool(structured), "history_available": bool(history),
    }

def analyze(text: str, state: dict=None, history: list=None,
            active_flow: dict=None, dialog_state: dict=None,
            interpreted: dict=None):
    text=(text or "").strip()
    state=state if isinstance(state, dict) else {}
    history=history if isinstance(history, list) else []
    active_flow=active_flow if isinstance(active_flow, dict) else {}
    dialog_state=dialog_state if isinstance(dialog_state, dict) else {}

    if not text:
        safe_semantic_log("EMPTY INPUT")
        return None

    signals=_state_signals(state, active_flow, dialog_state, history)
    safe_semantic_log(f"INPUT: {text[:80]}")

    cognition=state.get("cognition", {})
    interpreted = interpreted if isinstance(interpreted, dict) else None
    if interpreted is None:
        interpreted=interpret_request(
            text,
            cognition=cognition,
            semantic={},
            history=history,
            state=state,
        ) or {}

    fusion=_signal_fusion(text, signals, interpreted)
    dialogue_context = _dialogue_context_matrix(text, signals, interpreted)
    current_representation = detect_representation_constraints(text, interpreted)
    result=_base_result(text, signals)

    result["intent"]=interpreted.get("type","text")
    result["normalized_text"]=interpreted.get("normalized",text)
    result["confidence"]=clamp(
        0.45 +
        0.15*bool(interpreted) +
        0.10*bool(fusion["candidate_domains"]) +
        0.10*bool(fusion["requested_representation"]) +
        0.10*bool(signals["history_depth"]) +
        0.10*bool(signals["goal"])
    )

    # Preserve the canonical interpretation contract as evidence.
    for key in (
        "dialogue_contract","dialog_act","active_goal","active_topic",
        "resolved_request","reply_to","required_capabilities",
        "history_available","continuation","continuation_target",
        "content_role","contains_object","contains_explanation",
        "contains_analysis","contains_legend","scene_composition_ready",
        "requested_representations","representation_constraints",
        "required_domains","candidate_domains","required_representations",
        "candidate_representations","scene_type","scene_semantic_state",
        "dialogue_relation","task_phase","operation",
        "production_representation","resolved_representation",
        "production_representation_locked","resolved_representation_locked",
        "representation_scores","representation_evidence",
        "presentation_signal_scores"
    ):
        if key in interpreted:
            result[key]=interpreted[key]

    dc = result.get("dialogue_contract")
    dc = dc if isinstance(dc, dict) else {}
    dc.update({
        "dialog_act": dialogue_context["dialog_act"],
        "continuation": dialogue_context["continuation"],
        "reference_to_previous": dialogue_context["reference_to_previous"],
        "context_dependency": dialogue_context["context_dependency"],
        "context_dependency_score": dialogue_context["context_dependency_score"],
        "continuation_score": dialogue_context["continuation_score"],
        "reference_score": dialogue_context["reference_score"],
        "previous_user_turn": dialogue_context["previous_user_turn"],
        "previous_april_turn": dialogue_context["previous_april_turn"],
        "canonical": True,
        "version": "quantum_dialogue_field_v2",
    })
    if str(dc.get("dialog_act") or "").lower() == "memory_query":
        dc.update({
            "dialog_act": "memory_query",
            "continuation": False,
            "reference_to_previous": True,
            "context_dependency": "memory_query",
            "context_dependency_score": 1.0,
            "continuation_score": 0.0,
            "reference_score": 1.0,
        })
    result["dialogue_contract"] = dc
    result["dialogue_context_field"] = dialogue_context
    result["scene_semantic_state"] = (
        interpreted.get("scene_semantic_state")
        if isinstance(interpreted.get("scene_semantic_state"), dict)
        else result.get("scene_semantic_state", {})
    )
    result["dialogue_relation"] = (
        interpreted.get("dialogue_relation")
        if isinstance(interpreted.get("dialogue_relation"), dict)
        else result.get("dialogue_relation", {})
    )
    result["dialogue_vector"] = interpreted.get("dialogue_vector", {})
    result["dialogue_delta"] = interpreted.get("dialogue_delta", {})
    result["render_continuity"] = interpreted.get("render_continuity", {})
    result["visual_schema"] = interpreted.get("visual_schema", "")
    result["visual_schema_confidence"] = interpreted.get("visual_schema_confidence", 0.0)
    result["visual_schema_scores"] = interpreted.get("visual_schema_scores", {})

    # Production representation is a single canonical signal. Evidence
    # candidates are preserved separately and never become renderer commands.
    result["requested_representation"] = fusion["requested_representation"]
    result["production_representation"] = fusion["production_representation"]
    result["production_representation_source"] = fusion["production_representation_source"]
    result["production_representation_confident"] = fusion["production_representation_confident"]
    result["representation_posteriors"] = fusion["representation_posteriors"]
    result["representation_consensus"] = fusion["representation_consensus"]

    result["candidate_domains"] = list(dict.fromkeys(
        result.get("candidate_domains", []) + fusion["candidate_domains"]
    ))
    result["required_domains"] = list(dict.fromkeys(
        result.get("required_domains", []) + fusion["candidate_domains"]
    ))

    blocked = set(fusion["representation_constraints"].get("negative", []))
    production = fusion["production_representation"]
    if production in blocked:
        production = "text"

    # Preserve evidence for diagnostics without promoting it.
    evidence_candidates = [
        x for x in fusion.get("evidence_representations", [])
        if x not in blocked
    ]

    result["required_representations"] = [production]
    result["candidate_representations"] = evidence_candidates or [production]
    result["requested_representations"] = [production]
    result["requested_outputs"] = [production]
    result["required_outputs"] = [production]
    result["requested_representation"] = production
    result["representation_authority"] = (
        "production_signal"
        if fusion["production_representation_confident"]
        else "quantum_processor"
    )
    result["representation_constraints"] = fusion["representation_constraints"]
    result["representation_evidence"] = evidence_candidates

    result.update({
        "renderer_probability":fusion["renderer"],
        "image_generation_probability":fusion["image"],
        "visual_probability":fusion["visual"],
        "execution_probability":fusion["execution"],
        "discussion_probability":fusion["discussion"],
        "reflection_probability":fusion["reflection"],
        "space_discussion_probability":detect_space_discussion_probability(text),
        "renderer_priority":fusion["renderer"],
        "execution_pressure":fusion["execution"],
        "execution_readiness":fusion["execution"],
        "trajectory_strength":clamp(
            result.get("trajectory_strength",0.5) + 0.25*fusion["continuity"]
        ),
    })

    requested = result.get("requested_representation") or fusion["requested_representation"]
    # Evidence is diagnostic. Only the single production representation
    # controls the downstream capability signal.
    result["render_intent"] = requested != "text"
    result["prefer_renderer"] = result["render_intent"]
    result["renderer_scene_object"] = requested != "text"
    result["visual_routing"] = requested in {"graph", "diagram", "gallery", "image"}
    result["possible_capability"]="renderer" if requested else None
    result["possible_output"]=requested
    result["possible_scene_type"]=requested
    result["current_representation"]=requested or "text"
    result["unresolved_intent"]=not bool(requested or interpreted.get("dialog_act"))

    if requested == "image" and fusion["image"] > 0.0:
        result["visual_generation_needed"] = True
        result["explicit_image_generation_only"] = True
        result["possible_output"] = "image"
        result["possible_capability"] = "image_generation"

    result["should_execute"]=False  # execution authority remains downstream
    result["response_mode"] = "structured" if requested != "text" else "talk"
    result["renderer_first"] = requested != "text"
    result["semantic_evidence"]={
        "fusion":fusion,
        "source_signals":signals,
        "interpretation":interpreted,
        "representation_constraints":current_representation,
        "current_request_authoritative":True,
        "requested_outputs": [requested],
        "evidence_representations": list(evidence_candidates),
        "representation_posteriors": dict(fusion["representation_posteriors"]),
        "multi_output": False,
        "decision_owner":"QUANTUM_PROCESSOR",
    }

    # No semantic-core room order: only capabilities/evidence leave this layer.
    result["factory_targets"] = [requested]
    if result["required_domains"]:
        result["factory_targets"].extend(
            d for d in result["required_domains"] if d not in result["factory_targets"]
        )

    artifact=build_artifact_bundle()
    artifact=enrich_artifact_bundle(artifact,result)
    artifact.update({
        "required_domains":result["required_domains"],
        "candidate_domains":result["candidate_domains"],
        "required_representations": result["required_representations"],
        "candidate_representations": result["candidate_representations"],
        "evidence_representations": list(evidence_candidates),
        "requested_representation": requested,
        "production_representation": requested,
        "decision_owner":"QUANTUM_PROCESSOR",
    })
    result["artifact_bundle"]=artifact

    # Preserve useful memory/context fields without making this layer authoritative.
    for key in (
        "dynamic_focus","goal_hierarchy","open_loops","memory_signals",
        "visual_topic_registry","task_context_storage",
        "continuity_context_storage","memory_anchor_storage","active_topic_slot"
    ):
        result[key]=signals.get(key, cognition.get(key) if isinstance(cognition,dict) else None)

    result["machine_packet"]={
        "transport":"transport_state",
        "evidence":result["semantic_evidence"],
        "capabilities":result["required_representations"],
        "domains":result["required_domains"],
        "decision_owner":"QUANTUM_PROCESSOR",
        "single_route":True,
    }

    safe_semantic_log(
        f"EVIDENCE | production={result['required_representations']} "
        f"evidence={result.get('representation_evidence', [])} "
        f"domains={result['required_domains']} "
        f"renderer={result['renderer_probability']:.2f}"
    )
    return result
