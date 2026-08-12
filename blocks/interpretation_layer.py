"""
APRIL_INTERPRETATION_LAYER — QUANTUM EVIDENCE V1

Role:
    semantic evidence / context fusion layer.

Rule:
    Interpretation does not own routing, provider calls, renderer selection,
    room execution, or final response generation. It prepares one evidence
    packet for the Quantum Processor.

Single route:
    input -> interpretation evidence -> Quantum Processor -> provider/rooms
            -> C_ARTIFACT_CONTRACT -> April Web

Compatibility:
    Public helper names from the previous layer are retained so downstream
    imports do not need a parallel route.
"""

import time

# ---------------------------------------------------------------------------
# Canonical semantic vocabulary
# ---------------------------------------------------------------------------

LIGHTWEIGHT_VISUAL_WORDS = (
    "покажи", "визуализируй", "иллюстрация", "пример", "схема",
)
RENDERER_WORDS = (
    "renderer", "scene", "graph", "plot", "chart", "diagram", "table",
    "formula", "график", "таблица", "формула", "схема", "диаграмма",
)
MATH_WORDS = ("математика", "формула", "уравнение", "интеграл", "производная")
WEB_WORDS = ("поиск", "найди", "интернет", "сайт", "веб")
CODE_WORDS = ("python", "javascript", "typescript", "код", "программирование")
CONTINUATION_WORDS = ("продолжай", "продолжить", "дальше", "продолжение")
EXPLORATION_WORDS = ("исследуй", "сравни", "проанализируй", "разбери")
EXPLICIT_IMAGE_WORDS = ("нарисуй", "создай изображение", "сгенерируй изображение")
INFORMATIONAL_WORDS = ("что", "почему", "как", "объясни")

DISCUSSION_WORDS = (
    "поговорим", "обсудим", "как думаешь", "мнение",
    "рассуждение", "рассуждаем", "объясни", "почему",
)
ACTION_WORDS = (
    "создай", "сделай", "построй", "отрендери", "нарисуй",
    "покажи", "сгенерируй", "напиши", "реши", "найди",
)

DOMAIN_WORDS = {
    "biology": ("биология", "генетика", "эволюция", "клетка", "организм",
                "экология", "бактерии", "днк", "животные", "растения"),
    "chemistry": ("химия", "реакция", "молекула", "атом", "вещество"),
    "physics": ("физика", "энергия", "сила", "ускорение", "электричество"),
    "engineering": ("инженерия", "конструкция", "механизм", "проектирование"),
    "it": ("программирование", "алгоритм", "сервер", "код", "разработка"),
    "literature": ("литература", "роман", "поэзия", "писатель", "произведение"),
    "politics": ("политика", "государство", "выборы", "правительство"),
    "news": ("новости", "события", "последние новости"),
    "social": ("общество", "социум", "социальный"),
    "web": ("сайт", "интернет", "поиск", "веб"),
}

DOMAIN_ROOM_MAP = {name: [name] for name in DOMAIN_WORDS}

RESPONSE_COMPLEXITY_LOW = "LOW"
RESPONSE_COMPLEXITY_MEDIUM = "MEDIUM"
RESPONSE_COMPLEXITY_HIGH = "HIGH"

PATCH_LOG = []
MAX_PATCH_LOGS = 120


# ---------------------------------------------------------------------------
# Basic utilities
# ---------------------------------------------------------------------------

def ensure_semantic_constants():
    """Compatibility no-op: constants are now canonical module data."""
    return True


def safe_patch_log(message):
    try:
        PATCH_LOG.append({
            "timestamp": time.time(),
            "message": str(message),
            "file_id": "APRIL_INTERPRETATION_LAYER",
            "machine_only": True,
        })
        if len(PATCH_LOG) > MAX_PATCH_LOGS:
            del PATCH_LOG[:-MAX_PATCH_LOGS]
    except Exception:
        pass


def normalize_text(text):
    return str(text or "").strip()


def normalize_lower(text):
    return normalize_text(text).lower()


def contains_any(text, words):
    value = normalize_lower(text)
    return any(word in value for word in words)


def _semantic_evidence_stub(kind, text):
    table = {
        "legacy": WEB_WORDS, "renderer": RENDERER_WORDS, "code": CODE_WORDS,
        "information": INFORMATIONAL_WORDS, "continuation": CONTINUATION_WORDS,
        "exploration": EXPLORATION_WORDS, "image": EXPLICIT_IMAGE_WORDS,
        "math": MATH_WORDS, "web": WEB_WORDS,
    }
    return contains_any(text, table.get(kind, ()))


# ---------------------------------------------------------------------------
# Semantic evidence — no final routing decisions
# ---------------------------------------------------------------------------

def detect_domain_candidates(text):
    value = normalize_lower(text)
    return [domain for domain, words in DOMAIN_WORDS.items()
            if any(word in value for word in words)]


def detect_representation_candidates(text):
    value = normalize_lower(text)
    checks = (
        (("график", "graph", "plot", "chart"), "graph"),
        (("таблица", "table"), "table"),
        (("схема", "diagram", "диаграмма"), "diagram"),
        (("формула", "уравнение", "formula"), "formula"),
    )
    return [name for words, name in checks if any(x in value for x in words)]


def detect_discussion_mode(text):
    return contains_any(text, DISCUSSION_WORDS)


def detect_space_discussion(text):
    value = normalize_lower(text)
    return (
        contains_any(value, ("пространство", "scene", "renderer", "render", "блок"))
        and detect_discussion_mode(value)
    )


def semantic_evidence_math(text):
    return contains_any(text, MATH_WORDS)


def semantic_evidence_renderer(text):
    value = normalize_lower(text)
    return bool(detect_representation_candidates(value)) and (
        contains_any(value, ACTION_WORDS) or
        contains_any(value, ("построй", "отобрази", "покажи"))
    )


def detect_lightweight_visual(text):
    return contains_any(text, LIGHTWEIGHT_VISUAL_WORDS)


def semantic_evidence_image(text):
    return contains_any(text, EXPLICIT_IMAGE_WORDS)


def semantic_evidence_exploration(text):
    return contains_any(text, EXPLORATION_WORDS)


def semantic_evidence_continuation(text):
    return contains_any(text, CONTINUATION_WORDS)


def semantic_evidence_web(text):
    return contains_any(text, WEB_WORDS)


def semantic_evidence_code(text):
    return contains_any(text, CODE_WORDS)


def semantic_evidence_information(text):
    return contains_any(text, INFORMATIONAL_WORDS)


def detect_scene_type(text, cognition=None):
    """Return a representation *candidate*, never a routing command."""
    cognition = cognition if isinstance(cognition, dict) else {}
    reps = detect_representation_candidates(text)
    for preferred in cognition.get("required_representations", ()) or ():
        if preferred in reps:
            return preferred
    return reps[0] if reps else None


def build_domain_confidence(text):
    return {domain: 0.85 for domain in detect_domain_candidates(text)}


# ---------------------------------------------------------------------------
# Evidence packet
# ---------------------------------------------------------------------------

def build_result(text):
    return {
        "type": "text",
        "subtype": None,
        "scene_type": None,
        "normalized": text,
        "content_role": None,
        "contains_object": False,
        "contains_explanation": False,
        "contains_analysis": False,
        "contains_legend": False,
        "scene_composition_ready": True,
        "renderer_intent": False,
        "discussion_mode": False,
        "space_discussion": False,
        "lightweight_visual": False,
        "exploration": False,
        "continuation": False,
        "web_context": False,
        "explicit_image_generation": False,
        "cognition_assisted": True,
        "continuity_aware": True,
        "scene_aware": True,
        "supports_executor": True,
        "prefer_renderer": False,
        "prefer_guidance": False,
        "prefer_execution": False,
        "prefer_continuation": False,
        "active_topic_slot": None,
        "topic_continuity": False,
        "avoid_force_generation": True,
        "avoid_hidden_escalation": True,
        "avoid_telegram_behavior": True,
        "avoid_trigger_execution": True,
        "provider_safe": True,
        "renderer_first": False,
        "machine_only": True,
        "semantic_bridge": True,
        "orchestration_safe": True,
        "continuity_preserved": True,
        "required_domains": [],
        "candidate_domains": [],
        "required_representations": [],
        "candidate_representations": [],
        "domain_confidence": {},
        "response_complexity": None,
        "estimated_action_count": 0,
        "decision_owner": "QUANTUM_PROCESSOR",
        "routing_owner": "QUANTUM_PROCESSOR",
        "renderer_owner": "QUANTUM_PROCESSOR",
        "provider_calls": 0,
    }


def detect_explanation_content(text):
    return contains_any(text, (
        "объясни", "объяснение", "пояснение", "расшифровка",
        "что означает", "что значит",
    ))


def detect_analysis_content(text):
    return contains_any(text, ("анализ", "вывод", "заключение", "интерпретация"))


def detect_legend_content(text):
    return contains_any(text, ("обозначение", "обозначения", "легенда", "расшифровка"))


def detect_object_content(text):
    return bool(normalize_text(text))


def build_factory_order(result):
    domains = result.get("required_domains", []) or []
    return {
        "intent": result.get("type"),
        "goal": result.get("subtype"),
        "required_domains": domains,
        "required_rooms": [room for d in domains for room in DOMAIN_ROOM_MAP.get(d, [])],
        "required_artifacts": [],
        "quality_target": 0.95,
        "owner": "QUANTUM_PROCESSOR",
        "status": "evidence_only",
    }


def build_scene_strategy(result):
    reps = result.get("required_representations", []) or []
    role = result.get("content_role")
    return {
        "scene_strategy": "evidence_only",
        "preferred_blocks": list(reps),
        "content_role": role,
        "scene_priority": "normal",
        "scene_contribution_mode": True,
        "scene_builder_profile": "processor_selected",
        "decision_owner": "QUANTUM_PROCESSOR",
    }


def estimate_action_count(result):
    if not isinstance(result, dict):
        return 0
    reps = set(result.get("required_representations", []) or [])
    domains = set(result.get("required_domains", []) or [])
    count = len(reps) + len(domains)
    count += int(bool(result.get("contains_analysis") or result.get("contains_explanation")))
    count += 2 if result.get("explicit_image_generation") else 0
    return max(1, count)


def determine_response_complexity(result):
    actions = estimate_action_count(result)
    if actions <= 1:
        return RESPONSE_COMPLEXITY_LOW
    if actions <= 3:
        return RESPONSE_COMPLEXITY_MEDIUM
    return RESPONSE_COMPLEXITY_HIGH


# ---------------------------------------------------------------------------
# Canonical dialogue contract
# ---------------------------------------------------------------------------

def _dialog_turn_text(turn, role=None):
    if not isinstance(turn, dict):
        return ""
    if isinstance(turn.get("content"), str):
        return turn["content"].strip()
    if role and isinstance(turn.get(role), dict):
        obj = turn[role]
        return str(obj.get("text") or obj.get("content") or obj.get("answer") or "").strip()
    for key in ("text", "answer", "content", "response", "message"):
        if isinstance(turn.get(key), str) and turn[key].strip():
            return turn[key].strip()
    return ""


def _dialog_history_pairs(history):
    if not isinstance(history, list):
        return []
    pairs = []
    for item in history:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").lower()
        if role in {"user", "human"}:
            pairs.append(("user", _dialog_turn_text(item), item))
        elif role in {"assistant", "april", "bot"}:
            pairs.append(("assistant", _dialog_turn_text(item), item))
        else:
            if isinstance(item.get("user"), dict):
                pairs.append(("user", _dialog_turn_text(item, "user"), item))
            if isinstance(item.get("april"), dict):
                pairs.append(("assistant", _dialog_turn_text(item, "april"), item))
    return [(r, t, raw) for r, t, raw in pairs if t]


def _canonical_dialogue_contract(text, history=None, state=None, semantic=None):
    text = normalize_text(text)
    history = history if isinstance(history, list) else []
    state = state if isinstance(state, dict) else {}
    semantic = semantic if isinstance(semantic, dict) else {}
    turns = _dialog_history_pairs(history)

    last_assistant = next((x for x in reversed(turns) if x[0] == "assistant"), None)
    last_user = next((x for x in reversed(turns) if x[0] == "user" and x[1] != text), None)
    low = text.lower()

    if low in {"да", "ага", "угу", "ок", "окей", "хорошо", "давай", "верно", "точно"}:
        act = "affirmation"
    elif low in {"нет", "не надо", "не хочу", "отмена", "отмени", "не то"}:
        act = "rejection"
    elif low in CONTINUATION_WORDS:
        act = "continuation"
    elif any(x in low for x in ("я имел в виду", "я имела в виду", "не это", "точнее", "исправь", "поправь")):
        act = "correction"
    elif "?" in text or low.startswith(("кто ", "что ", "как ", "почему ", "зачем ", "где ", "когда ", "сколько ")):
        act = "question"
    elif low.startswith(ACTION_WORDS):
        act = "request"
    else:
        act = "statement"

    previous_assistant = last_assistant[1] if last_assistant else ""
    reply_to = (
        last_assistant[2].get("turn_id")
        if last_assistant and isinstance(last_assistant[2], dict)
        else None
    )

    is_continuation = act in {"affirmation", "rejection", "continuation", "correction"}
    if not is_continuation and previous_assistant and len(text.split()) <= 6:
        if any(x in low for x in ("это", "этот", "эта", "этом", "него", "неё", "ее", "его", "там", "так")):
            is_continuation, act = True, "reference"

    active_goal = (
        state.get("active_goal") or state.get("current_goal") or
        (state.get("goal_hierarchy") or {}).get("active_goal") or
        semantic.get("active_goal") or semantic.get("goal") or ""
    )
    active_topic = (
        state.get("active_topic") or state.get("current_topic") or state.get("topic") or
        semantic.get("current_topic") or semantic.get("topic") or ""
    )

    if not is_continuation and act in {"request", "question", "statement"} and len(text.split()) > 1:
        resolved_goal = text
    else:
        resolved_goal = active_goal or (last_user[1] if last_user else text)

    capabilities = []
    if any(x in low for x in ("код", "программ", "нейросет", "бот", "приложение")):
        capabilities += ["software", "architecture", "dialogue"]
    if detect_representation_candidates(low):
        capabilities.append("structured_rendering")
    if any(x in low for x in ("проанализ", "сравни", "почему", "разбери", "объясни")):
        capabilities.append("analysis")

    return {
        "dialog_act": act,
        "current_request": text,
        "resolved_request": (
            f"Continue the previous task naturally. User said: {text}"
            if is_continuation and previous_assistant else text
        ),
        "continuation": is_continuation,
        "reply_to": reply_to,
        "previous_april_turn": previous_assistant,
        "previous_user_turn": last_user[1] if last_user else "",
        "active_goal": resolved_goal,
        "active_topic": active_topic,
        "topic_shift": bool(active_topic and text and active_topic.lower() not in low and not is_continuation),
        "required_capabilities": list(dict.fromkeys(capabilities)),
        "confidence": 0.96 if act in {"affirmation", "rejection", "continuation"} and previous_assistant else 0.78,
        "history_available": bool(turns),
        "turn_count": len(turns),
        "canonical": True,
        "version": "dialogue_v3_quantum_evidence",
    }


# ---------------------------------------------------------------------------
# Main interpretation: evidence only
# ---------------------------------------------------------------------------

def _base_interpret_request(text, cognition=None, semantic=None, history=None, state=None):
    text = normalize_text(text)
    if not text:
        safe_patch_log("EMPTY REQUEST")
        return None

    cognition = cognition if isinstance(cognition, dict) else {}
    semantic = semantic if isinstance(semantic, dict) else {}
    result = build_result(text)
    low = text.lower()

    # Context is evidence. Current request remains authoritative.
    result["semantic_profile"] = build_semantic_dialog_profile(text, cognition, semantic)
    result["scene_profile"] = build_scene_construction_profile(result["semantic_profile"])
    result["artifact_contract"] = build_scene_artifact_contract(
        result["semantic_profile"], result["scene_profile"]
    )

    domains = detect_domain_candidates(text)
    reps = detect_representation_candidates(text)
    for rep in (semantic.get("required_representations", []) or []) + (cognition.get("required_representations", []) or []):
        if rep not in reps:
            reps.append(rep)

    result["candidate_domains"] = domains
    result["required_domains"] = domains
    result["domain_confidence"] = build_domain_confidence(text)
    result["candidate_representations"] = reps
    result["required_representations"] = reps
    result["scene_type"] = detect_scene_type(text, cognition)

    result["discussion_mode"] = detect_discussion_mode(text)
    result["space_discussion"] = detect_space_discussion(text)
    result["exploration"] = semantic_evidence_exploration(text) or bool(cognition.get("exploration_mode"))
    result["continuation"] = semantic_evidence_continuation(text) or bool(cognition.get("needs_continuation"))
    result["web_context"] = semantic_evidence_web(text) or bool(cognition.get("internet_context_needed"))
    result["explicit_image_generation"] = semantic_evidence_image(text)
    result["lightweight_visual"] = detect_lightweight_visual(text) or bool(cognition.get("visual_reference_mode"))

    result["contains_object"] = detect_object_content(text)
    result["contains_explanation"] = detect_explanation_content(text)
    result["contains_analysis"] = detect_analysis_content(text)
    result["contains_legend"] = detect_legend_content(text)
    if result["contains_explanation"]:
        result["content_role"] = "explanation"
    elif result["contains_analysis"]:
        result["content_role"] = "analysis"
    elif result["contains_legend"]:
        result["content_role"] = "legend"

    # These are observations, not route commands.
    result["evidence"] = {
        "domain": domains,
        "representation": reps,
        "math": semantic_evidence_math(text),
        "code": semantic_evidence_code(text),
        "web": result["web_context"],
        "image": result["explicit_image_generation"],
        "continuation": result["continuation"],
        "exploration": result["exploration"],
        "information": semantic_evidence_information(text),
        "cognition": dict(cognition),
        "semantic": dict(semantic),
    }

    result["factory_order"] = build_factory_order(result)
    result["scene_strategy"] = build_scene_strategy(result)
    result["estimated_action_count"] = estimate_action_count(result)
    result["response_complexity"] = determine_response_complexity(result)

    # No representation is promoted to an execution type here.
    result["semantic_authority"] = True
    result["decision_source"] = "QUANTUM_PROCESSOR"
    result["semantic_decision_source"] = "evidence_fusion"
    result["representation_resolution"] = "processor_selection"
    result["legacy_keyword_matching"] = None
    result["factory_order"]["status"] = "evidence_only"

    return result


def interpret_request(text, cognition=None, semantic=None, history=None, state=None):
    result = _base_interpret_request(
        text, cognition=cognition, semantic=semantic, history=history, state=state
    )
    if result is None:
        return None

    contract = _canonical_dialogue_contract(
        text, history=history or [], state=state or {}, semantic=result
    )
    result["dialogue_contract"] = contract
    result["dialog_act"] = contract["dialog_act"]
    result["continuation"] = bool(contract["continuation"])
    result["continuation_target"] = contract["previous_april_turn"] or contract["active_topic"]
    result["active_goal"] = contract["active_goal"]
    result["active_topic"] = contract["active_topic"]
    result["resolved_request"] = contract["resolved_request"]
    result["reply_to"] = contract["reply_to"]
    result["required_capabilities"] = contract["required_capabilities"]
    result["dialogue_understanding"] = contract
    result["context_dependency"] = (
        "continuation" if contract.get("continuation")
        else "reference" if contract.get("dialog_act") == "reference"
        else "new_topic" if contract.get("topic_shift")
        else "independent"
    )
    result["context_policy"] = {
        "current_request": True,
        "dialogue_vector": bool(contract.get("continuation") or contract.get("dialog_act") == "reference"),
        "previous_turn": bool(contract.get("reply_to") or contract.get("previous_april_turn")),
        "active_goal": bool(contract.get("active_goal") and contract.get("continuation")),
        "full_history": False,
    }

    # Canonical transport contract: one packet, one owner, no fallback route.
    result["canonical_transport"] = "transport_state"
    result["decision_owner"] = "QUANTUM_PROCESSOR"
    result["routing_owner"] = "QUANTUM_PROCESSOR"
    result["renderer_owner"] = "QUANTUM_PROCESSOR"
    result["provider_calls"] = 0
    result["avoid_trigger_execution"] = True
    result["unresolved_intent"] = False if contract["dialog_act"] in {
        "affirmation", "rejection", "continuation"
    } else False

    result = validate_response_complexity(result)
    state_out = build_interpretation_state()
    state_out = synchronize_interpretation_context(state_out, result)
    state_out = export_transport_state(state_out, result)
    result["transport_state"] = state_out
    result["primary_contract"] = "transport_state"
    result["interpretation_state"] = state_out
    result["transport_diagnostics"] = build_transport_diagnostics(result)
    result = propagate_canonical_response(result, state_out)
    result = bridge_machine_response(result, state_out)
    safe_patch_log(
        f"INTERPRETATION EVIDENCE | domains={result['required_domains']} "
        f"representations={result['required_representations']} "
        f"complexity={result['response_complexity']}"
    )
    return result


# ---------------------------------------------------------------------------
# Canonical transport / compatibility helpers
# ---------------------------------------------------------------------------

INTERPRETATION_ENTRYPOINT = "transport_state"
INTERPRETATION_TRANSPORT_FIELDS = {
    "dialogue_profile": ("dialogue", "profile"),
    "semantic_evidence_engine": ("evidence", "engine"),
    "dialogue_cognition_matrix": ("cognition", "matrix"),
    "semantic_dialogue_graph": ("dialogue", "graph"),
    "scene_profile": ("scene", "profile"),
    "artifact_contract": ("artifacts", "contract"),
    "executor_preparation_contract": ("executor", "contract"),
}
INTERPRETATION_ROUTE = tuple(INTERPRETATION_TRANSPORT_FIELDS)
INTERPRETATION_CONTEXT_SCHEMA = {
    "state": "interpretation_state",
    "dialogue": "semantic_profile",
    "evidence": "semantic_evidence_engine",
    "scene": "scene_profile",
    "artifact": "artifact_contract",
    "executor": "executor_preparation_contract",
}
INTERPRETATION_STATE_TEMPLATE = {
    "dialogue": {}, "evidence": {}, "cognition": {}, "scene": {},
    "artifacts": {}, "executor": {}, "diagnostics": {},
}


def resolve_interpretation_payload(result):
    return result.get("transport_state", {}) if isinstance(result, dict) else {}


def export_transport_state(state, result):
    for field, (section, key) in INTERPRETATION_TRANSPORT_FIELDS.items():
        if field in result:
            state.setdefault(section, {})[key] = result[field]
    return state


def build_interpretation_route(state, result):
    route = [{
        "node": node,
        "status": "evidence",
        "payload": result.get(node),
    } for node in INTERPRETATION_ROUTE]
    state.setdefault("diagnostics", {})["route"] = route
    return route


def synchronize_interpretation_context(state, result):
    state.setdefault("dialogue", {})["profile"] = result.get("semantic_profile")
    state.setdefault("evidence", {})["engine"] = result.get("semantic_evidence_engine", result.get("evidence", {}))
    state.setdefault("scene", {})["profile"] = result.get("scene_profile")
    state.setdefault("artifacts", {})["contract"] = result.get("artifact_contract")
    state.setdefault("executor", {})["contract"] = result.get("executor_preparation_contract")
    return state


def build_interpretation_state():
    return {key: dict(value) for key, value in INTERPRETATION_STATE_TEMPLATE.items()}


def safe_result_get(result, key, default=None):
    if not isinstance(result, dict):
        return default
    value = result.get(key, default)
    return default if value is None else value


def ensure_transport_defaults(state):
    state = state or {}
    for key in ("dialogue", "scene", "executor", "artifacts", "diagnostics"):
        state.setdefault(key, {})
    return state


def propagate_canonical_response(result, state):
    transport = state.setdefault("transport", {})
    response = transport.setdefault("response", {})
    response["content"] = safe_result_get(result, "normalized") or safe_result_get(result, "assistant_response", "")
    return result


def bridge_machine_response(result, state):
    machine = state.setdefault("machine_response", {})
    scene = state.setdefault("scene_contract", {})
    content = machine.get("content") or result.get("normalized") or result.get("assistant_response") or ""
    machine["content"] = content
    scene.update({"content": content, "answer": content, "summary": content})
    result["machine_response"] = machine
    result["scene_contract"] = scene
    return result


def export_response_complexity(result):
    return {key: result.get(key) for key in (
        "response_complexity", "estimated_action_count",
        "semantic_response_complexity", "machine_response_complexity",
    )}


def validate_response_complexity(result):
    result["response_complexity"] = result.get("response_complexity") or RESPONSE_COMPLEXITY_LOW
    result["estimated_action_count"] = result.get("estimated_action_count") or 0
    result["semantic_response_complexity"] = result["response_complexity"]
    result["machine_response_complexity"] = result["response_complexity"]
    return result


def build_transport_diagnostics(result):
    return {
        "has_transport": bool(result.get("transport_state")),
        "has_machine_response": bool(result.get("machine_response")),
        "has_scene_contract": bool(result.get("scene_contract")),
        "normalized": bool(result.get("normalized")),
        "decision_owner": result.get("decision_owner"),
        "provider_calls": result.get("provider_calls", 0),
    }


# ---------------------------------------------------------------------------
# Semantic profile / scene / processor compatibility builders
# ---------------------------------------------------------------------------

def build_semantic_dialog_profile(text, cognition=None, semantic=None,
                                  assistant_response=None, dialogue_history=None,
                                  vision_context=None):
    cognition = cognition or {}
    semantic = semantic or {}
    return {
        "input_text": text,
        "assistant_response": assistant_response,
        "dialogue_history": dialogue_history or [],
        "vision_context": vision_context or {},
        "active_goal": cognition.get("active_goal") or semantic.get("active_goal"),
        "active_topic": cognition.get("active_topic_slot") or semantic.get("current_topic"),
        "semantic_state": semantic,
        "requires_scene_builder": False,
        "profile_version": "quantum_evidence_v1",
    }


def build_scene_construction_profile(semantic_profile):
    return {
        "requires_scene_builder": False,
        "scene_type": "dialogue",
        "dialogue_mode": "semantic_unified",
        "context_source": "evidence_packet",
        "decision_owner": "QUANTUM_PROCESSOR",
        "profile_version": "quantum_evidence_v1",
    }


def build_scene_artifact_contract(semantic_profile, scene_profile):
    return {
        "contract": "scene_artifact",
        "transport": "transport_state",
        "semantic_profile": semantic_profile or {},
        "scene_profile": scene_profile or {},
        "dialogue_history": (semantic_profile or {}).get("dialogue_history", []),
        "assistant_response": (semantic_profile or {}).get("assistant_response"),
        "active_goal": (semantic_profile or {}).get("active_goal"),
        "scene_type": (scene_profile or {}).get("scene_type", "dialogue"),
        "representation": "processor_decides",
        "profile_version": "quantum_evidence_v1",
    }


def build_unified_scene_context(semantic_profile, scene_profile, artifact_contract,
                                voice_context=None, vision_context=None,
                                gallery_context=None, file_context=None,
                                assistant_response=None, dialogue_history=None,
                                memory_state=None):
    return {
        "semantic_profile": semantic_profile or {},
        "scene_profile": scene_profile or {},
        "artifact_contract": artifact_contract or {},
        "voice_context": voice_context or {},
        "vision_context": vision_context or {},
        "gallery_context": gallery_context or {},
        "file_context": file_context or {},
        "assistant_response": assistant_response,
        "dialogue_history": dialogue_history or (semantic_profile or {}).get("dialogue_history", []),
        "active_goal": (semantic_profile or {}).get("active_goal"),
        "active_scene": (scene_profile or {}).get("scene_type", "dialogue"),
        "memory_state": memory_state or {},
        "continuity_state": {"single_route": True, "transport": "transport_state", "scene_contract": "canonical"},
        "profile_version": "quantum_evidence_v1",
    }


def build_scene_execution_plan(semantic_profile, scene_profile, artifact_contract, unified_scene_context=None):
    context = unified_scene_context or build_unified_scene_context(
        semantic_profile, scene_profile, artifact_contract
    )
    return {
        "transport": "transport_state",
        "scene_contract": "canonical",
        "scene_context": context,
        "scene_type": (scene_profile or {}).get("scene_type", "dialogue"),
        "representation": "processor_decides",
        "execution_mode": "single_semantic_pipeline",
        "decision_owner": "QUANTUM_PROCESSOR",
        "profile_version": "quantum_evidence_v1",
    }


def build_unified_interpretation_state(scene_context, processor_state=None):
    scene_context = scene_context or {}
    return {
        "transport": "transport_state",
        "scene_context": scene_context,
        "processor_state": processor_state or {},
        "dialogue_vector": scene_context.get("dialogue_history", []),
        "assistant_response": scene_context.get("assistant_response"),
        "voice_context": scene_context.get("voice_context", {}),
        "vision_context": scene_context.get("vision_context", {}),
        "gallery_context": scene_context.get("gallery_context", {}),
        "file_context": scene_context.get("file_context", {}),
        "active_goal": scene_context.get("active_goal"),
        "active_scene": scene_context.get("active_scene"),
        "executor_mode": "single_scene_contract",
        "profile_version": "quantum_evidence_v1",
    }


def build_semantic_processor_state(interpretation_state, execution_plan=None):
    state = interpretation_state or {}
    return {
        "transport": "transport_state",
        "processor_contract": "canonical",
        "interpretation_state": state,
        "execution_plan": execution_plan or {},
        "semantic_inputs": {
            "text": state.get("scene_context", {}).get("semantic_profile", {}).get("input_text"),
            "voice": state.get("voice_context", {}),
            "images": state.get("vision_context", {}),
            "gallery": state.get("gallery_context", {}),
            "files": state.get("file_context", {}),
            "assistant": state.get("assistant_response"),
            "history": state.get("dialogue_vector", []),
        },
        "scene_understanding": {
            "active_scene": state.get("active_scene"),
            "active_goal": state.get("active_goal"),
            "continuity": True,
            "single_route": True,
        },
        "profile_version": "quantum_evidence_v1",
    }


def build_dialogue_understanding_core(processor_state, executor_state=None):
    inputs = (processor_state or {}).get("semantic_inputs", {})
    return {
        "transport": "transport_state",
        "dialogue_understanding": {
            "user_text": inputs.get("text"),
            "voice": inputs.get("voice"),
            "images": inputs.get("images"),
            "gallery": inputs.get("gallery"),
            "files": inputs.get("files"),
            "assistant_response": inputs.get("assistant"),
            "dialogue_history": inputs.get("history", []),
            "scene_understanding": (processor_state or {}).get("scene_understanding", {}),
        },
        "processor_reasoning": {
            "single_scene": True,
            "history_aware": True,
            "response_context": True,
            "executor_shared_context": executor_state or {},
        },
        "profile_version": "quantum_evidence_v1",
    }


def optimize_dialogue_understanding(dialogue_core):
    return {
        "transport": "transport_state",
        "dialogue_understanding": (dialogue_core or {}).get("dialogue_understanding", {}),
        "optimization": {
            "semantic_priority": ["current_request", "active_goal", "dialogue_history", "multimodal_context"],
            "multi_evidence": True,
            "response_continuity": True,
            "scene_consistency": True,
            "executor_alignment": True,
        },
        "canonical_reasoning": {
            "single_scene": True, "single_contract": True, "single_transport": True,
            "preserve_dialogue_vector": True,
        },
        "profile_version": "quantum_evidence_v1",
    }


def build_semantic_interpretation_contract(dialogue_optimization):
    return {
        "transport": "transport_state",
        "semantic_contract": {
            "mode": "canonical_semantic",
            "compatibility_isolated": True,
            "single_scene": True,
            "single_dialogue": True,
            "single_processor": True,
            "single_executor": True,
        },
        "disabled_legacy_flags": [],
        "dialogue_optimization": dialogue_optimization or {},
        "reasoning_policy": {
            "current_request_authoritative": True,
            "multimodal_fusion": True,
            "multi_evidence": True,
            "trigger_independent": True,
            "scene_continuity": True,
        },
        "profile_version": "quantum_evidence_v1",
    }


def build_canonical_semantic_runtime(semantic_contract, processor_state, dialogue_core):
    dialogue = (dialogue_core or {}).get("dialogue_understanding", {})
    return {
        "transport": "transport_state",
        "scene": dialogue.get("scene_understanding", {}),
        "dialogue": dialogue,
        "processor": processor_state or {},
        "reasoning_policy": (semantic_contract or {}).get("reasoning_policy", {}),
        "continuity_vector": {
            "history": dialogue.get("dialogue_history", []),
            "assistant": dialogue.get("assistant_response"),
            "goal": dialogue.get("scene_understanding", {}).get("active_goal"),
        },
        "compatibility": {"enabled": False, "trigger_execution": False, "keyword_matching": False},
        "input_sources": {
            key: value for key, value in {
                "text": dialogue.get("user_text"),
                "voice": dialogue.get("voice"),
                "images": dialogue.get("images"),
                "gallery": dialogue.get("gallery"),
                "files": dialogue.get("files"),
            }.items() if value not in (None, {}, [], "")
        },
        "profile_version": "quantum_evidence_v1",
    }


def fuse_semantic_inputs(runtime_state):
    runtime_state = runtime_state or {}
    inputs = dict(runtime_state.get("input_sources", {}))
    continuity = runtime_state.get("continuity_vector", {})
    return {
        "transport": "transport_state",
        "scene": runtime_state.get("scene", {}),
        "goal": continuity.get("goal"),
        "history": continuity.get("history", []),
        "assistant_response": continuity.get("assistant"),
        "modalities": {key: inputs.get(key) for key in ("text", "voice", "images", "gallery", "files")},
        "semantic_state": {
            "single_route": True,
            "multimodal_fusion": True,
            "legacy_trigger_enabled": False,
            "context_complete": True,
        },
        "available_modalities": [k for k, v in inputs.items() if v not in (None, {}, [], "")],
        "profile_version": "quantum_evidence_v1",
    }


def build_processor_execution_context(runtime_state):
    fused = fuse_semantic_inputs(runtime_state or {})
    return {
        "transport": "transport_state",
        "semantic_context": fused,
        "executor_context": fused,
        "processor_context": fused,
        "decision_owner": "QUANTUM_PROCESSOR",
        "profile_version": "quantum_evidence_v1",
    }


# Compatibility aliases used by older integrations.
SEMANTIC_EVIDENCE_PRIORITY = (
    "current_request", "active_goal", "dialogue_history",
    "voice_context", "vision_context", "gallery_context",
    "file_context", "semantic_profile",
)
LEGACY_TRIGGER_FLAGS = ()
CANONICAL_SEMANTIC_RUNTIME = {
    "transport": "transport_state",
    "reasoning": "semantic_evidence",
    "legacy_trigger_execution": False,
    "single_scene": True,
    "single_processor": True,
    "single_executor": True,
}
SEMANTIC_INTERPRETATION_CORE = {
    "decision_source": "QUANTUM_PROCESSOR",
    "routing": "processor_owned",
    "legacy_mode": "isolated",
    "scene_contract": "artifact_first",
    "executor_contract": "advisory_only",
    "history_model": "evidence_based",
    "confidence_policy": "multi_evidence",
}
SEMANTIC_PIPELINE = (
    "dialogue_profile", "semantic_evidence_engine", "dialogue_cognition_matrix",
    "semantic_dialogue_graph", "scene_profile", "artifact_contract",
    "executor_preparation_contract",
)
