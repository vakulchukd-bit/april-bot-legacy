# ================================================================
# APRIL SEMANTIC CORE — QUANTUM EVIDENCE ENGINE v1
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
SEMANTIC_MACHINE_CHANNEL = {
    "type": "semantic_core",
    "mode": "quantum_evidence",
    "isolated": True,
    "continuity_safe": True,
    "renderer_safe": True,
    "web_safe": True,
}

SEMANTIC_PATCH_LOG = []
MAX_SEMANTIC_LOGS = 120

def safe_semantic_log(msg):
    try:
        print("SEMANTIC CORE:", msg)
        SEMANTIC_PATCH_LOG.append(str(msg))
        if len(SEMANTIC_PATCH_LOG) > MAX_SEMANTIC_LOGS:
            del SEMANTIC_PATCH_LOG[:-MAX_SEMANTIC_LOGS]
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
    values = [
        float(item.get("score", 0.0) or 0.0)
        for item in measurements if isinstance(item, dict) and item.get("type") != "text"
    ]
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


def detect_representation_constraints(text, interpreted=None):
    interpreted = interpreted if isinstance(interpreted, dict) else {}
    positive = []
    negative = []
    scores = {}

    raw_scores = interpreted.get("representation_scores")
    if not isinstance(raw_scores, dict):
        evidence = interpreted.get("representation_evidence") or []
        raw_scores = {
            str(item.get("label") or "").lower(): float(item.get("score", 0.0) or 0.0)
            for item in evidence if isinstance(item, dict)
        }

    explicit = list(interpreted.get("required_representations") or [])
    if not explicit:
        explicit = list(interpreted.get("candidate_representations") or [])

    for name in explicit:
        name = str(name or "").lower().strip()
        if name in REPRESENTATION_UNIVERSE and name != "text" and name not in negative:
            positive.append(name)
            scores[name] = max(scores.get(name, 0.0), float(raw_scores.get(name, 0.0) or 0.0))

    # Keep a matrix candidate only when it is separated from text strongly
    # enough to be a current-turn representation signal.
    text_score = float(raw_scores.get("text", 0.0) or 0.0)
    for name, value in raw_scores.items():
        name = str(name).lower().strip()
        value = float(value or 0.0)
        if (name in REPRESENTATION_UNIVERSE and name != "text"
                and value >= 0.20 and value - text_score >= 0.08):
            if name not in positive:
                positive.append(name)
            scores[name] = max(scores.get(name, 0.0), value)

    return {
        "positive": list(dict.fromkeys(positive)),
        "negative": list(dict.fromkeys(negative)),
        "scores": scores,
        "current_request_authoritative": True,
        "source": "quantum_matrix",
    }

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

REPRESENTATION_UNIVERSE = (
    "text", "table", "graph", "diagram", "formula",
    "gallery", "link", "code", "image",
)

def _representation_posteriors(
    text: str,
    signals: dict,
    interpreted: dict,
    constraints: dict,
) -> tuple[dict[str, float], list[str], list[str]]:
    """
    Build a smooth posterior over representations.

    Lexical matches are only one evidence source. Current interpretation,
    continuation context, and prior rendered types contribute as independent
    signals. No renderer is selected by a single keyword.
    """
    scores = {name: 0.10 for name in REPRESENTATION_UNIVERSE}
    low = (text or "").lower()

    # Current request evidence.
    positive = [str(x).lower() for x in (constraints.get("positive") or [])]
    negative = {str(x).lower() for x in (constraints.get("negative") or [])}
    for name in positive:
        if name in scores:
            scores[name] += 2.20

    # Interpretation is a separate evidence source, not a renderer command.
    for name in (
        *(interpreted.get("required_representations") or []),
        *(interpreted.get("candidate_representations") or []),
    ):
        key = str(name).lower()
        if key in scores:
            scores[key] += 0.90

    dialogue_contract = interpreted.get("dialogue_contract") if isinstance(interpreted.get("dialogue_contract"), dict) else {}
    continuity = bool(
        dialogue_contract.get("continuation")
        or dialogue_contract.get("reference_to_previous")
    )
    current_scene = str(interpreted.get("scene_type") or "").lower()
    previous_types = set()
    visual = signals.get("active_visual_scene") if isinstance(signals, dict) else {}
    if isinstance(visual, dict):
        previous_types.update(str(x).lower() for x in (
            visual.get("render_block_types") or visual.get("block_types") or []
        ))
    if continuity and current_scene in previous_types and current_scene != "text":
        scores[current_scene] += 0.75

    # Negative constraints suppress stale candidates smoothly.
    for name in negative:
        if name in scores:
            scores[name] = 0.0

    # Text is the human-visible channel when another representation exists.
    if any(v > 0.30 for k, v in scores.items() if k != "text"):
        scores["text"] += 0.55

    # Softmax gives a continuous posterior over the same evidence field.
    temperature = 0.85
    exp_values = {}
    for key, value in scores.items():
        exp_values[key] = math.exp(max(-20.0, min(20.0, value / temperature)))
    total = sum(exp_values.values()) or 1.0
    posterior = {key: exp_values[key] / total for key in scores}

    top = sorted(posterior, key=posterior.get, reverse=True)
    # Keep the posterior complete, but promote only materially supported
    # candidates. The selection is relative to the current posterior, not a
    # renderer-specific trigger.
    top_mass = posterior[top[0]] if top else 0.0
    selected = [
        key for key in top[:4]
        if posterior[key] >= max(0.12, top_mass * 0.34)
        and key not in negative
    ]

    if not selected:
        selected = ["text"]


    return posterior, selected, sorted(negative)

def _signal_fusion(text, signals, interpreted):
    """Fuse independent evidence without collapsing it into a renderer trigger."""
    representation_constraints = detect_representation_constraints(text, interpreted)
    posterior, selected, blocked = _representation_posteriors(
        text,
        signals,
        interpreted,
        representation_constraints,
    )

    requested = next((x for x in selected if x != "text"), selected[0] if selected else "text")
    renderer = detect_renderer_probability(text, interpreted)
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
    active_scene = bool(signals["active_visual_scene"])
    goal = bool(signals["goal"])
    memory = bool(signals["memory_signals"])

    current_nontext = [
        name for name in (interpreted.get("required_representations") or interpreted.get("candidate_representations") or [])
        if str(name).lower() not in {"", "text"}
    ]
    structured_mass = max(
        (posterior.get(str(name).lower(), 0.0) for name in current_nontext),
        default=0.0,
    )

    render_score = clamp(
        structured_mass * 0.85
        + renderer * 0.15
        if current_nontext else 0.0
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
        "requested_representation": requested,
        "requested_representations": list(selected),
        "required_representations": list(selected),
        "representation_constraints": {
            **representation_constraints,
            "negative": blocked,
        },
        "representation_posteriors": posterior,
        "representation_consensus": {
            "selected": list(selected),
            "confidence": posterior.get(requested, 0.0),
            "entropy": -sum(
                p * math.log(max(p, 1e-12))
                for p in posterior.values()
            ),
        },
        "candidate_domains": detect_domain_candidates(text, interpreted),
        "evidence_count": sum(bool(x) for x in (
            selected, continuity, active_scene, goal, memory, discussion, reflection
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
        "candidate_representations","scene_type"
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

    result["requested_representation"]=fusion["requested_representation"]
    result["representation_posteriors"]=fusion["representation_posteriors"]
    result["representation_consensus"]=fusion["representation_consensus"]
    result["candidate_domains"]=list(dict.fromkeys(
        result.get("candidate_domains",[])+fusion["candidate_domains"]
    ))
    result["required_domains"]=list(dict.fromkeys(
        result.get("required_domains",[])+fusion["candidate_domains"]
    ))

    blocked = set(fusion["representation_constraints"].get("negative", []))
    current_positive = list(fusion["requested_representations"])
    reps = [x for x in fusion["required_representations"] if x not in blocked]
    result["required_representations"]=list(reps)
    result["candidate_representations"]=list(reps)
    result["requested_representations"]=list(current_positive)
    # Representation authority: a new-topic request without explicit,
    # semantically strong representation evidence remains text. This prevents
    # broad NLI priors from inventing graphs/diagrams for ordinary requests.
    dialog_contract = interpreted.get("dialogue_contract", {}) if isinstance(interpreted, dict) else {}
    continuation = bool(
        dialog_contract.get("continuation")
        or interpreted.get("continuation")
    )
    rep_scores = {
        str(item.get("label")).lower(): float(item.get("score", 0.0))
        for item in (interpreted.get("representation_evidence") or [])
        if isinstance(item, dict)
    }
    text_score = rep_scores.get("text", 0.0)
    strong_representation = [
        name for name in (
            "table", "graph", "diagram", "formula",
            "image", "gallery", "code", "link"
        )
        if (
            rep_scores.get(name, 0.0) >= 0.80
            and (rep_scores.get(name, 0.0) - text_score) >= 0.16
        )
    ]
    explicit_current = bool(current_positive)
    if not explicit_current and not continuation and not strong_representation:
        result["required_representations"] = ["text"]
        result["candidate_representations"] = ["text"]
        result["requested_representations"] = ["text"]
        result["requested_outputs"] = ["text"]
        result["required_outputs"] = ["text"]
        result["requested_representation"] = "text"
        result["representation_authority"] = "text"
        result["representation_consensus"] = {
            **result.get("representation_consensus", {}),
            "selected": ["text"],
            "decision_reason": "new_topic_without_strong_representation_evidence",
        }

    result["representation_constraints"]=fusion["representation_constraints"]

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
    # These are evidence flags only. The processor owns the final choice.
    result["render_intent"]=bool(any(
        name != "text" for name in result["required_representations"]
    ))
    result["prefer_renderer"]=result["render_intent"]
    result["renderer_scene_object"]=bool(
        any(name != "text" for name in result["required_representations"])
    )
    result["visual_routing"]=bool(
        any(name in {"graph", "diagram", "gallery", "image"} for name in result["required_representations"])
    )
    result["possible_capability"]="renderer" if requested else None
    result["possible_output"]=requested
    result["possible_scene_type"]=requested
    result["current_representation"]=requested or "text"
    result["unresolved_intent"]=not bool(requested or interpreted.get("dialog_act"))

    if "image" in result["required_representations"] and fusion["image"] > 0.0:
        result["visual_generation_needed"]=True
        result["explicit_image_generation_only"]=True
        result["possible_output"]="image"
        result["possible_capability"]="image_generation"

    result["should_execute"]=False  # execution authority remains downstream
    result["response_mode"]="structured" if any(str(x).lower() != "text" for x in current_positive) else "talk"
    result["renderer_first"]=bool(current_positive)
    result["semantic_evidence"]={
        "fusion":fusion,
        "source_signals":signals,
        "interpretation":interpreted,
        "representation_constraints":current_representation,
        "current_request_authoritative":True,
        "requested_outputs": list(current_positive),
        "representation_posteriors": dict(fusion["representation_posteriors"]),
        "multi_output": len(current_positive) > 1,
        "decision_owner":"QUANTUM_PROCESSOR",
    }

    # No semantic-core room order: only capabilities/evidence leave this layer.
    result["factory_targets"]=[]
    for item in result["required_representations"]:
        if item not in result["factory_targets"]:
            result["factory_targets"].append(item)
    if result["required_domains"]:
        result["factory_targets"].extend(
            d for d in result["required_domains"] if d not in result["factory_targets"]
        )

    artifact=build_artifact_bundle()
    artifact=enrich_artifact_bundle(artifact,result)
    artifact.update({
        "required_domains":result["required_domains"],
        "candidate_domains":result["candidate_domains"],
        "required_representations":result["required_representations"],
        "candidate_representations":result["candidate_representations"],
        "requested_representation":requested,
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
        f"EVIDENCE | reps={result['required_representations']} "
        f"domains={result['required_domains']} "
        f"renderer={result['renderer_probability']:.2f}"
    )
    return result
