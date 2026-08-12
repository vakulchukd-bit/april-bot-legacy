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
RENDERER_WORDS = (
    "график","графика","функция","формула","уравнение","таблица",
    "сетка","layout","diagram","схема","line","стрелка","plot","chart",
    "y=","f(x)","sin(","cos(","tan("
)
IMAGE_WORDS = (
    "создай изображение","сгенерируй изображение","нарисуй картинку",
    "создай арт","draw image","generate image"
)
VISUAL_WORDS = (
    "пример","визуально","референс","атмосфера","концепт","дизайн",
    "стиль","схема","чертеж","layout"
)
EXECUTION_WORDS = ("сделай","создай","выполни","отправь","построй","покажи")
DISCUSSION_WORDS = (
    "давай обсудим","как думаешь","что думаешь","поговорим","обсудим",
    "подскажи","посоветуй","объясни","расскажи","помоги понять",
    "можешь показать","интересно","хочу понять","какой лучше"
)
REFLECTION_WORDS = ("почему","объясни","рассуждай","размышляй","как ты пришла")
SPACE_WORDS = ("пространство","scene","renderer","блок","галерея","график")
GRAPH_WORDS = ("график","построй график","функция","plot","chart")
TABLE_WORDS = ("таблица","таблицу","таблич","периодическая","менделеева","значения")
LINK_WORDS = ("источник","ссылка","документация")
MATH_WORDS = ("математика","формула","уравнение","интеграл","производная")
CONTINUATION_WORDS = (
    "продолжай","дальше","продолжение","о чём мы говорили","о чем мы говорили",
    "помнишь","вспомни","продолжи","это","этот","эта","этом","него","неё","ее","его"
)
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

def _weighted_probability(text, vocabulary, weight):
    t=(text or "").lower()
    hits=sum(1 for word in vocabulary if word in t)
    return clamp(hits * weight)

def detect_renderer_probability(text):
    return _weighted_probability(text, RENDERER_WORDS, 0.12)

def detect_image_generation_probability(text):
    return _weighted_probability(text, IMAGE_WORDS, 0.25)

def detect_visual_probability(text):
    return _weighted_probability(text, VISUAL_WORDS, 0.10)

def detect_execution_probability(text):
    return _weighted_probability(text, EXECUTION_WORDS, 0.12)

def detect_discussion_probability(text):
    return _weighted_probability(text, DISCUSSION_WORDS, 0.18)

def detect_reflection_probability(text):
    return _weighted_probability(text, REFLECTION_WORDS, 0.15)

def detect_space_discussion_probability(text):
    return _weighted_probability(text, SPACE_WORDS, 0.12)

def detect_representation_request(text):
    t=(text or "").lower()
    if any(w in t for w in GRAPH_WORDS): return "graph"
    if any(w in t for w in TABLE_WORDS): return "table"
    if any(w in t for w in LINK_WORDS): return "link"
    if any(w in t for w in ("диаграмма","diagram","схема")): return "diagram"
    if any(w in t for w in ("формула","уравнение","formula")): return "formula"
    return None

def detect_graph_action(text):
    t=(text or "").lower()
    if "почему" in t: return "explain"
    if "исправ" in t: return "fix"
    if "анализ" in t: return "analyze"
    if "сравни" in t: return "compare"
    if "построй" in t or "нарисуй" in t: return "build"
    return "unknown"

def detect_domain_candidates(text):
    t=(text or "").lower()
    return [domain for domain, words in DOMAIN_WORDS.items()
            if any(word in t for word in words)]

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
        "active_visual_scene": state.get("active_visual_scene"),
        "active_flow": active_flow,
        "dialog_state": dialog_state,
        "history_depth": len(history),
    }

def _signal_fusion(text, signals, interpreted):
    """Fuse independent evidence; never collapse it into a route decision."""
    requested = detect_representation_request(text)
    renderer = detect_renderer_probability(text)
    image = detect_image_generation_probability(text)
    visual = detect_visual_probability(text)
    execution = detect_execution_probability(text)
    discussion = detect_discussion_probability(text)
    reflection = detect_reflection_probability(text)

    history = signals["history_depth"]
    continuity = bool(signals["continuity_context_storage"] or interpreted.get("continuation"))
    active_scene = bool(signals["active_visual_scene"])
    goal = bool(signals["goal"])
    memory = bool(signals["memory_signals"])

    # Evidence aggregation is deliberately capped. One keyword cannot dominate
    # a context containing stronger contradictory signals.
    render_score = clamp(renderer * 0.45 + (0.35 if requested else 0.0)
                         + (0.10 if active_scene else 0.0)
                         + (0.10 if interpreted.get("prefer_renderer") else 0.0))
    continuity_score = clamp(
        (0.35 if continuity else 0.0) +
        (0.20 if history else 0.0) +
        (0.20 if goal else 0.0) +
        (0.15 if memory else 0.0) +
        (0.10 if active_scene else 0.0)
    )
    execution_score = clamp(
        execution * 0.45 +
        render_score * 0.20 +
        (0.20 if requested else 0.0) +
        (0.10 if interpreted.get("dialogue_act") == "request" else 0.0) +
        (0.05 if goal else 0.0)
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
        "candidate_domains": detect_domain_candidates(text),
        "evidence_count": sum(bool(x) for x in (
            requested, continuity, active_scene, goal, memory, discussion, reflection
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
        "conversation_vector": signals,
        "semantic_state": {"conversation_vector": signals},
        "factory_targets": [],
        "factory_order": {},
        "decision_owner": "QUANTUM_PROCESSOR",
        "route_owner": "EXISTING_SINGLE_ROUTE",
        "provider_calls": 0,
    }

def analyze(text: str, state: dict=None, history: list=None,
            active_flow: dict=None, dialog_state: dict=None):
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
    interpreted=interpret_request(
        text,
        cognition=cognition,
        semantic={},
        history=history,
        state=state,
    ) or {}

    fusion=_signal_fusion(text, signals, interpreted)
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
        "required_domains","candidate_domains","required_representations",
        "candidate_representations","scene_type"
    ):
        if key in interpreted:
            result[key]=interpreted[key]

    result["requested_representation"]=fusion["requested_representation"]
    result["candidate_domains"]=list(dict.fromkeys(
        result.get("candidate_domains",[])+fusion["candidate_domains"]
    ))
    result["required_domains"]=list(dict.fromkeys(
        result.get("required_domains",[])+fusion["candidate_domains"]
    ))

    reps=[]
    for rep in (
        result.get("required_representations",[]) +
        result.get("candidate_representations",[])
    ):
        if rep not in reps: reps.append(rep)
    if fusion["requested_representation"] and fusion["requested_representation"] not in reps:
        reps.append(fusion["requested_representation"])
    result["required_representations"]=reps
    result["candidate_representations"]=list(reps)

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

    requested=fusion["requested_representation"]
    # These are evidence flags only. The processor owns the final choice.
    result["render_intent"]=bool(requested or fusion["renderer"] >= 0.45)
    result["prefer_renderer"]=result["render_intent"]
    result["renderer_scene_object"]=bool(requested)
    result["visual_routing"]=bool(fusion["visual"] >= 0.30 or requested)
    result["possible_capability"]="renderer" if requested else None
    result["possible_output"]=requested
    result["possible_scene_type"]=requested
    result["current_representation"]=requested or "text"
    result["unresolved_intent"]=not bool(requested or interpreted.get("dialog_act"))

    if fusion["image"] >= 0.45:
        result["visual_generation_needed"]=True
        result["explicit_image_generation_only"]=True
        result["possible_output"]="image"
        result["possible_capability"]="image_generation"

    result["should_execute"]=False  # execution authority remains downstream
    result["response_mode"]="structured" if requested else "talk"
    result["renderer_first"]=bool(requested)
    result["semantic_evidence"]={
        "fusion":fusion,
        "source_signals":signals,
        "interpretation":interpreted,
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
