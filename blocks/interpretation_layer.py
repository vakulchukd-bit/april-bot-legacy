"""APRIL Interpretation Layer — FAST compatibility engine.

Design goals:
- one interpretation owner;
- no heavy NLP/embedding libraries on the hot path;
- preserve public compatibility symbols used by Executor, StateManager,
  ContextSystem, VisualReferenceSystem and SemanticCore;
- preserve NEW/CONTINUE/RECALL semantics;
- preserve semantic fields consumed downstream;
- visual routing is evidence-based and does not replace code/graph/text routing.

Heavy semantic packages are intentionally optional and are not imported here.
"""
from __future__ import annotations

import hashlib
import re
import threading
import time
from copy import deepcopy
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from rapidfuzz import fuzz as _fuzz
except Exception:
    _fuzz = None

RESPONSE_COMPLEXITY_LOW = "LOW"
RESPONSE_COMPLEXITY_MEDIUM = "MEDIUM"
RESPONSE_COMPLEXITY_HIGH = "HIGH"
DECISION_OWNER = "QUANTUM_PROCESSOR"
TRANSPORT_NAME = "transport_state"
INTERPRETATION_ENGINE_VERSION = "april_fast_interpretation_v1_2026_10"
SEMANTIC_MODEL_NAME = "rapidfuzz-arc-light"
NLI_MODEL_NAME = "disabled_on_hot_path"
SPACY_MODEL_NAME = "disabled_on_hot_path"
APRIL_FAST_SEMANTIC_MODE = True
APRIL_ENABLE_HEAVY_HOTPATH = False

REPRESENTATIONS = (
    "text", "code", "graph", "diagram", "formula", "table", "image",
    "gallery", "link", "file", "audio", "video", "action", "scene",
    "memory", "visual_context",
)
OPERATIONS = (
    "answer", "explain", "build", "create", "modify", "present",
    "calculate", "analyze", "compare", "list", "retrieve", "read",
    "transform", "visualize",
)
GOALS = (
    "understand", "create", "transform", "visualize", "retrieve",
    "compare", "organize", "present", "solve", "inspect",
)

_WORD_RE = re.compile(r"[\w№%+\-*/=().:,А-Яа-яЁёІіЇїЄєҐґ]+", re.UNICODE)


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_lower(value: Any) -> str:
    return normalize_text(value).lower()


def contains_any(text: Any, words: Iterable[str]) -> bool:
    value = normalize_lower(text)
    return any(normalize_lower(w) in value for w in words)


def _tokens(text: Any) -> List[str]:
    return [x.lower() for x in _WORD_RE.findall(normalize_text(text))]


def _similarity(a: Any, b: Any) -> float:
    left, right = normalize_lower(a), normalize_lower(b)
    if not left or not right:
        return 0.0
    if _fuzz is not None:
        try:
            return max(_fuzz.ratio(left, right) / 100.0, _fuzz.token_set_ratio(left, right) / 100.0)
        except Exception:
            pass
    return SequenceMatcher(None, left, right).ratio()


def _overlap(a: Any, b: Any) -> float:
    aa, bb = set(_tokens(a)), set(_tokens(b))
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / max(1, len(aa | bb))


def _compact(value: Any, limit: int = 1200) -> Any:
    if isinstance(value, str):
        value = normalize_text(value)
        return value[:limit]
    if isinstance(value, dict):
        return {str(k): _compact(v, 600) for k, v in list(value.items())[:32] if v not in (None, "", [], {})}
    if isinstance(value, (list, tuple)):
        return [_compact(v, 600) for v in list(value)[:32]]
    return value


@dataclass
class SemanticEvidence:
    text: str
    representation: str = "text"
    operation: str = "answer"
    object: str = "text"
    goal: str = "understand"
    topic: str = ""
    entity: str = ""
    confidence: float = 0.0
    source: str = "fast_matrix"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class _FastSemanticEncoder:
    """Small compatibility encoder; no model download and no background worker."""
    VERSION = "fast-token-affinity-v2"

    def similarities(self, current: str, candidates: Sequence[str] | str) -> Dict[str, float]:
        if isinstance(candidates, str):
            candidates = [candidates]
        return {str(c): round(_similarity(current, c), 6) for c in candidates if normalize_text(c)}

    def encode(self, text: str) -> List[float]:
        tokens = _tokens(text)
        if not tokens:
            return [0.0] * 8
        buckets = [0.0] * 8
        for token in tokens:
            digest = hashlib.blake2s(token.encode("utf-8"), digest_size=2).digest()
            idx = int.from_bytes(digest, "big") % len(buckets)
            buckets[idx] += 1.0
        total = sum(buckets) or 1.0
        return [round(x / total, 6) for x in buckets]


_SHARED_ENCODER = _FastSemanticEncoder()
_CACHE_LOCK = threading.RLock()
_PROFILE_CACHE: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
_PAIR_CACHE: Dict[str, List[Dict[str, Any]]] = {}


def get_shared_semantic_encoder():
    return _SHARED_ENCODER


def invalidate_pair_cache(user_id: str = "") -> None:
    with _CACHE_LOCK:
        if user_id:
            _PAIR_CACHE.pop(str(user_id), None)
        else:
            _PAIR_CACHE.clear()


class QuantumContextUnderstandingEngine:
    VERSION = "FAST-CONTEXT-V3"
    def fast_semantic_profile(self, text: str, active_topic: str = "", **kwargs) -> Dict[str, Any]:
        return _profile(text, active_topic=active_topic)
    def turn_measurement(self, text: str, **kwargs) -> Dict[str, Any]:
        p = _profile(text, active_topic=kwargs.get("active_topic", ""))
        return {"representation": p["representation"], "operation": p["operation"], "goal": p["goal"], "confidence": p["confidence"], "source": "fast_matrix"}


class QuantumInterpretationEngine(QuantumContextUnderstandingEngine):
    VERSION = "FAST-INTERPRETATION-V5"
    def similarities(self, current: str, candidates: Sequence[str] | str) -> Dict[str, float]:
        return _SHARED_ENCODER.similarities(current, candidates)
    def fast_semantic_profile(self, text: str, active_topic: str = "", **kwargs):
        return _profile(text, active_topic=active_topic)


QUANTUM_INTERPRETATION_ENGINE = QuantumInterpretationEngine()
QUANTUM_FAST_SEMANTIC = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_LINGUISTIC_ENGINE = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_EMBEDDING_ENGINE = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_INTENT_ENGINE = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_EVIDENCE_FUSION = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_DIALOGUE_ENGINE = QUANTUM_INTERPRETATION_ENGINE
QuantumFastSemanticEngine = QuantumInterpretationEngine
QuantumLinguisticEngine = QuantumInterpretationEngine
QuantumEmbeddingEngine = QuantumInterpretationEngine
QuantumIntentEngine = QuantumInterpretationEngine
QuantumEvidenceFusionEngine = QuantumInterpretationEngine
QuantumDialogueEngine = QuantumInterpretationEngine
QuantumSceneInterpretationMatrix = QuantumInterpretationEngine


# Lightweight semantic vocabularies. They are evidence, never final routing by themselves.
_CODE = ("код", "python", "питон", "пайтон", "скрипт", "программа", "программирование", "javascript", "typescript", "sql", "функция в коде")
_GRAPH = ("график", "графика функции", "plot", "диаграмма функции", "ось x", "ось y", "координат")
_DIAGRAM = ("схема", "диаграмма", "блок-схема", "структурная схема", "геометрическая фигура", "параллелограмм", "треугольник", "круг")
_TABLE = ("таблица", "таблицу", "таблиц", "табличку", "строки и столбцы", "сравнительную таблицу")
_FORMULA = ("формула", "формулу", "формул", "уравнение", "уравнен", "реши x", "вычисли", "посчитай", "математическое выражение")
_LINK = ("ссылка", "ссылку", "ссылке", "адрес сайта", "url", "официальный сайт")
_IMAGE = ("картинка", "изображение", "фото", "фотография", "фотореалистично", "реалистично", "как живой", "как настоящая фотография")
_VISUAL_ACTION = ("нарисуй", "нарисовать", "рисунок", "изобрази", "изобразить", "создай картинку", "сделай картинку", "покажи")
_COMPLEX_VISUAL = ("как на фотографии", "как живой", "как живого", "картинку", "изображение", "фотография", "фото", "фотореалистично", "реалистичная фотография", "фотореализм", "киношный", "кинематографичный", "детализированная картинка", "обложка", "портрет", "постер")
_RECALL = ("вспомни", "вернись к", "из того", "предыдущий", "раньше", "как мы делали", "тот код", "ту картинку", "предыдущую картинку")
_NEW = ("новый вопрос", "другая тема", "начнем заново", "начнём заново", "забудь предыдущ")
_CONTINUE = ("теперь", "а теперь", "добавь", "исправь", "измени", "продолжи", "ещё", "еще", "где", "почему", "как правильно", "сделай")


def _score_vocab(text: str, vocab: Sequence[str]) -> float:
    value = normalize_lower(text)
    score = 0.0
    for item in vocab:
        if item in value:
            score += 0.18 if len(item) > 4 else 0.10
    return min(1.0, score)


def _visual_tier(text: str, previous_scene: Optional[Dict[str, Any]] = None) -> str:
    value = normalize_lower(text)
    complex_now = _score_vocab(value, _COMPLEX_VISUAL) >= 0.10
    explicit_image = _score_vocab(value, _IMAGE) >= 0.10
    visual_action = _score_vocab(value, _VISUAL_ACTION) >= 0.10
    prior_mode = normalize_lower((previous_scene or {}).get("visual_generation_tier"))
    prior_repr = normalize_lower((previous_scene or {}).get("representation"))
    if prior_mode == "complex" or prior_repr == "image":
        if visual_action or not value:
            return "complex"
    if complex_now or (explicit_image and visual_action):
        return "complex"
    if visual_action:
        return "light"
    return "none"


def _representation_scores(text: str, previous_scene: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
    scores = {name: 0.0 for name in REPRESENTATIONS}
    scores["code"] = _score_vocab(text, _CODE)
    scores["graph"] = _score_vocab(text, _GRAPH)
    scores["diagram"] = _score_vocab(text, _DIAGRAM)
    scores["table"] = _score_vocab(text, _TABLE)
    scores["formula"] = _score_vocab(text, _FORMULA)
    scores["link"] = _score_vocab(text, _LINK)
    image = _score_vocab(text, _IMAGE)
    visual_action = _score_vocab(text, _VISUAL_ACTION)
    tier = _visual_tier(text, previous_scene)
    scores["image"] = min(1.0, image + (0.25 if tier == "complex" else 0.0))
    if tier == "light":
        scores["diagram"] = max(scores["diagram"], 0.20)
    scores["text"] = max(0.12, 0.35 - max(scores.values()) * 0.25)
    return scores


def _best(scores: Dict[str, float], default: str) -> Tuple[str, float]:
    if not scores:
        return default, 0.0
    key = max(scores, key=scores.get)
    return key, float(scores.get(key, 0.0))


def _operation(text: str, representation: str) -> str:
    value = normalize_lower(text)
    if representation == "code": return "build" if contains_any(value, ("напиши", "создай", "сделай", "код", "программа")) else "explain"
    if representation in {"image", "diagram", "graph", "table", "formula"}:
        if contains_any(value, ("исправь", "измени", "добавь", "переделай")): return "modify"
        if contains_any(value, ("объясни", "что означает", "почему")): return "explain"
        return "build"
    if representation == "link": return "retrieve"
    if contains_any(value, ("объясни", "расскажи", "что это", "почему", "как работает")): return "explain"
    if contains_any(value, ("сравни", "сравнение")): return "compare"
    if contains_any(value, ("найди", "где", "какой сайт", "ссылка")): return "retrieve"
    return "answer"


def _goal(text: str, operation: str, representation: str) -> str:
    if representation in {"graph", "diagram", "image"}: return "visualize"
    if representation == "code": return "transform" if operation in {"build", "modify"} else "understand"
    if representation == "link": return "retrieve"
    if operation == "compare": return "compare"
    if operation in {"build", "create", "modify"}: return "create"
    if operation == "retrieve": return "retrieve"
    if representation == "formula": return "solve"
    return "understand"


def _subject(text: str, representation: str) -> str:
    value = normalize_text(text)
    prefixes = (
        "ок теперь", "а теперь", "пожалуйста", "пожалуй", "теперь", "смотри",
        "напиши", "нарисуй", "создай", "сделай", "построй", "объясни", "расскажи",
    )
    low = value.lower()
    for prefix in prefixes:
        if low.startswith(prefix):
            value = value[len(prefix):].strip(" ,:—-\t")
            low = value.lower()
    if not value:
        return representation
    return value[:360]


def _topic(text: str, representation: str) -> str:
    subject = _subject(text, representation)
    return subject or representation


def _profile(text: str, active_topic: str = "", previous_scene: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    scores = _representation_scores(text, previous_scene)
    representation, rep_score = _best(scores, "text")
    tier = _visual_tier(text, previous_scene)
    value = normalize_lower(text)
    if representation == "text" and _score_vocab(text, _GRAPH) >= 0.10 and contains_any(value, ("построй", "построить", "добавь", "покажи", "график")):
        representation, rep_score = "graph", max(scores.get("graph", 0.0), 0.24)
    elif representation == "text" and _score_vocab(text, _TABLE) >= 0.10 and contains_any(value, ("таблиц", "строк", "столбц", "сравни")):
        representation, rep_score = "table", max(scores.get("table", 0.0), 0.24)
    elif representation == "text" and _score_vocab(text, _FORMULA) >= 0.10 and contains_any(value, ("формул", "уравнен", "реши", "вычисли", "посчитай")):
        representation, rep_score = "formula", max(scores.get("formula", 0.0), 0.24)
    elif representation == "text" and _score_vocab(text, _LINK) >= 0.10 and contains_any(value, ("ссылк", "адрес сайта", "официальный сайт", "url")):
        representation, rep_score = "link", max(scores.get("link", 0.0), 0.24)
    if representation == "text" and tier == "complex":
        representation, rep_score = "image", max(scores.get("image", 0.0), 0.20)
    elif representation == "text" and tier == "light":
        representation, rep_score = "diagram", max(scores.get("diagram", 0.0), 0.20)
    elif representation == "text" and _score_vocab(text, _CODE) >= 0.03:
        generic_python_question = contains_any(text, ("что такое python", "что такое питон", "что такое программирование"))
        if not generic_python_question:
            representation, rep_score = "code", _score_vocab(text, _CODE)
    operation = _operation(text, representation)
    goal = _goal(text, operation, representation)
    subject = _subject(text, representation)
    confidence = min(0.99, 0.35 + rep_score * 0.55 + (0.10 if subject else 0.0))
    if active_topic:
        confidence = min(0.99, confidence + 0.05 * _overlap(text, active_topic))
    return {
        "representation": representation, "representation_scores": scores,
        "operation": operation, "operation_scores": {operation: confidence},
        "goal": goal, "goal_scores": {goal: confidence},
        "object": representation, "object_scores": {representation: confidence},
        "topic": _topic(text, representation), "entity": subject,
        "confidence": round(confidence, 6),
        "request_features": {
            "code_request": representation == "code",
            "visual_action": _score_vocab(text, _VISUAL_ACTION) >= 0.10,
            "visual_construction": representation in {"diagram", "graph", "formula"},
            "image_request": representation == "image",
            "complex_visual": _visual_tier(text, previous_scene) == "complex",
        },
        "source": "fast_matrix",
    }


def _history_pairs(history: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    pairs: List[Dict[str, Any]] = []
    pending = None
    for item in history or []:
        if not isinstance(item, dict): continue
        role = normalize_lower(item.get("role"))
        content = normalize_text(item.get("content") or item.get("text") or item.get("answer") or item.get("result"))
        if not content: continue
        if role in {"user", "human"}:
            pending = content
        elif role in {"assistant", "april", "bot"} and pending:
            pairs.append({"user": pending, "assistant": content, "result": content})
            pending = None
    return pairs[-15:]


def _relation(text: str, pairs: Sequence[Dict[str, Any]], active_topic: str = "", previous_scene: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    value = normalize_lower(text)
    if contains_any(value, _NEW):
        relation = "NEW"
    elif contains_any(value, _RECALL):
        relation = "RECALL"
    elif pairs or active_topic or previous_scene:
        last = pairs[-1] if pairs else {}
        score = max(_similarity(value, last.get("user", "")), _similarity(value, active_topic))
        relation = "CONTINUE" if score >= 0.16 or contains_any(value, _CONTINUE) else "NEW"
    else:
        relation = "NEW"
    return {
        "relation": relation,
        "continuation": relation == "CONTINUE",
        "reference": relation in {"CONTINUE", "RECALL"},
        "score": round(max(_similarity(value, active_topic), 0.18 if relation == "CONTINUE" else 0.0), 6),
    }


def _semantic_chain(text: str, profile: Dict[str, Any], relation: Dict[str, Any], previous_scene: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "current_request": normalize_text(text),
        "operation": profile["operation"],
        "object": profile["object"],
        "goal": profile["goal"],
        "representation": profile["representation"],
        "relation": relation["relation"],
        "previous_scene_present": bool(previous_scene),
        "visual_generation_tier": _visual_tier(text, previous_scene),
    }


def _visual_plan(text: str, profile: Dict[str, Any], previous_scene: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    tier = _visual_tier(text, previous_scene)
    representation = profile["representation"]
    if tier == "complex":
        route = "C_APRIL_IMAGES_GENERATOR"
        mode = "image_generation"
        semantic_request = normalize_text(text)
    elif tier == "light":
        route = "C_DIAGRAM_ROOM"
        mode = "light_visual"
        semantic_request = normalize_text(text)
    elif representation in {"graph", "diagram", "formula", "table"}:
        route = "structured_renderer"
        mode = representation
        semantic_request = normalize_text(text)
    else:
        route = "none"
        mode = "none"
        semantic_request = ""
    return {
        "visual_requested": tier != "none" or representation in {"graph", "diagram", "formula", "table"},
        "visual_generation_route": route,
        "visual_generation_tier": tier,
        "visual_production_mode": mode,
        "visual_generation_request": semantic_request,
        "renderer_intent": route != "none",
    }


def _provider_plan(text: str, result: Dict[str, Any]) -> Dict[str, Any]:
    semantic = {
        "topic": result.get("topic"), "entity": result.get("entity"),
        "operation": result.get("operation"), "goal": result.get("goal"),
        "representation": result.get("representation"),
        "relation": result.get("relation"),
        "semantic_request": result.get("semantic_request"),
        "resolved_request": result.get("resolved_request"),
        "visual_generation_request": result.get("visual_generation_request", ""),
        "visual_generation_tier": result.get("visual_generation_tier", "none"),
    }
    return {
        "version": "fast_provider_handoff_v1",
        "provider_context_authority": "INTERPRETATION",
        "provider_must_not_reselect_context": True,
        "required": ["RESPONSE_FORMULATION", "SEMANTIC_CORE", "OUTPUT_CONTRACT"],
        "SEMANTIC_CORE": semantic,
        "OUTPUT_CONTRACT": {
            "representation": result.get("representation"),
            "requested_outputs": [result.get("representation", "text")] if result.get("representation") != "text" else ["text"],
            "visual_generation_request": result.get("visual_generation_request", ""),
        },
        "RESPONSE_FORMULATION": {
            "action": result.get("operation"),
            "goal": result.get("goal"),
            "current_request": normalize_text(text),
        },
    }


def build_result(**kwargs) -> Dict[str, Any]:
    return dict(kwargs)


def safe_result_get(result: Any, key: str, default: Any = None) -> Any:
    return result.get(key, default) if isinstance(result, dict) else default


def ensure_transport_defaults(result: Dict[str, Any]) -> Dict[str, Any]:
    result.setdefault("transport", TRANSPORT_NAME)
    result.setdefault("decision_owner", DECISION_OWNER)
    result.setdefault("single_route", True)
    result.setdefault("legacy_trigger_execution", False)
    return result


def synchronize_interpretation_context(result: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    return ensure_transport_defaults(result)


def export_transport_state(result: Dict[str, Any]) -> Dict[str, Any]:
    return deepcopy(result)


def resolve_interpretation_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    return ensure_transport_defaults(result)


def propagate_canonical_response(result: Dict[str, Any], response: Any = None) -> Dict[str, Any]:
    if response is not None:
        result["provider_response"] = response
    return result


def determine_response_complexity(text: str, result: Optional[Dict[str, Any]] = None) -> str:
    value = normalize_text(text)
    length = len(value)
    if result and result.get("representation") in {"code", "image", "graph", "diagram"}:
        return RESPONSE_COMPLEXITY_MEDIUM if length > 80 else RESPONSE_COMPLEXITY_LOW
    return RESPONSE_COMPLEXITY_HIGH if length > 900 else RESPONSE_COMPLEXITY_MEDIUM if length > 250 else RESPONSE_COMPLEXITY_LOW


def estimate_action_count(result: Dict[str, Any]) -> int:
    count = 1
    if result.get("representation") != "text": count += 1
    if result.get("relation") in {"CONTINUE", "RECALL"}: count += 1
    return count


def build_factory_order(result: Dict[str, Any]) -> List[str]:
    order = ["interpretation", "provider", "artifact", "scene", "web"]
    if result.get("representation") == "image": order.insert(2, "C_APRIL_IMAGES_GENERATOR")
    return order


def build_scene_strategy(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "representation": result.get("representation", "text"),
        "single_scene": True,
        "renderer_intent": bool(result.get("renderer_intent")),
        "visual_generation_tier": result.get("visual_generation_tier", "none"),
    }


def build_interpretation_state(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "semantic": deepcopy(result),
        "scene_strategy": build_scene_strategy(result),
        "provider_context_plan": deepcopy(result.get("provider_context_plan", {})),
    }


def build_semantic_dialog_profile(text: str, **kwargs) -> Dict[str, Any]:
    p = _profile(text, kwargs.get("active_topic", ""), kwargs.get("previous_scene"))
    return {"topic": p["topic"], "entity": p["entity"], "operation": p["operation"], "goal": p["goal"], "representation": p["representation"], "confidence": p["confidence"]}


def build_scene_construction_profile(text: str, **kwargs) -> Dict[str, Any]:
    p = _profile(text, kwargs.get("active_topic", ""), kwargs.get("previous_scene"))
    return {"scene_type": p["representation"], "operation": p["operation"], "goal": p["goal"], "visual_generation_tier": _visual_tier(text, kwargs.get("previous_scene"))}


def build_scene_artifact_contract(text: str, **kwargs) -> Dict[str, Any]:
    p = _profile(text, kwargs.get("active_topic", ""), kwargs.get("previous_scene"))
    return {"contract": "scene_artifact", "scene_type": p["representation"], "source": "interpretation", "single_route": True}


def build_unified_scene_context(text: str, **kwargs) -> Dict[str, Any]:
    return build_scene_artifact_contract(text, **kwargs)


def build_scene_execution_plan(text: str, **kwargs) -> Dict[str, Any]:
    p = _profile(text, kwargs.get("active_topic", ""), kwargs.get("previous_scene"))
    return {"operation": p["operation"], "representation": p["representation"], "goal": p["goal"], "route": _visual_plan(text, p, kwargs.get("previous_scene"))["visual_generation_route"]}


def build_unified_interpretation_state(text: str, **kwargs) -> Dict[str, Any]:
    return interpret_request(text, **kwargs)


def build_semantic_processor_state(text: str, **kwargs) -> Dict[str, Any]:
    return interpret_request(text, **kwargs)


def build_dialogue_understanding_core(text: str, **kwargs) -> Dict[str, Any]:
    return interpret_request(text, **kwargs)


def optimize_dialogue_understanding(text: str, **kwargs) -> Dict[str, Any]:
    return interpret_request(text, **kwargs)


def build_semantic_interpretation_contract(text: str, **kwargs) -> Dict[str, Any]:
    return interpret_request(text, **kwargs)


def build_canonical_semantic_runtime(text: str, **kwargs) -> Dict[str, Any]:
    return interpret_request(text, **kwargs)


def fuse_semantic_inputs(text: str, **kwargs) -> Dict[str, Any]:
    return interpret_request(text, **kwargs)


def build_processor_execution_context(text: str, **kwargs) -> Dict[str, Any]:
    result = interpret_request(text, **kwargs)
    return {"semantic": result, "provider_context_plan": result.get("provider_context_plan", {}), "single_route": True}


def build_transport_diagnostics(result: Dict[str, Any]) -> Dict[str, Any]:
    return {"engine": INTERPRETATION_ENGINE_VERSION, "legacy_trigger_execution": False, "decision_owner": DECISION_OWNER, "representation": result.get("representation"), "visual_generation_tier": result.get("visual_generation_tier", "none")}


def export_response_complexity(result: Dict[str, Any]) -> Dict[str, Any]:
    return {"complexity": determine_response_complexity(result.get("semantic_request", ""), result), "action_count": estimate_action_count(result)}


def validate_response_complexity(result: Dict[str, Any]) -> bool:
    return isinstance(result, dict) and bool(result.get("representation"))


def build_interpretation_route(result: Dict[str, Any]) -> Dict[str, Any]:
    return {"owner": DECISION_OWNER, "representation": result.get("representation"), "route": result.get("visual_generation_route", "none"), "single_route": True}


def detect_domain_candidates(text: str) -> List[Dict[str, Any]]:
    domains = {
        "it": ("python", "код", "программа", "сервер", "бот"),
        "mathematics": ("формула", "уравнение", "график", "функция"),
        "web": ("сайт", "ссылка", "url", "домен"),
        "engineering": ("схема", "деталь", "размер", "механизм"),
        "science": ("физика", "химия", "биология"),
    }
    out=[]
    for name, words in domains.items():
        score=_score_vocab(text, words)
        if score: out.append({"domain":name,"score":round(score,6)})
    return sorted(out,key=lambda x:x["score"],reverse=True)


def build_domain_confidence(text: str) -> Dict[str, float]:
    return {x["domain"]:x["score"] for x in detect_domain_candidates(text)}


def _capability_scores(text: str) -> Dict[str, float]:
    p=_profile(text)
    return {"text":p["representation_scores"].get("text",0.0), "visual":max(p["representation_scores"].get(x,0.0) for x in ("image","graph","diagram")), "code":p["representation_scores"].get("code",0.0)}


def measure_representation_evidence(text: str, **kwargs) -> Dict[str, Any]:
    return _profile(text, kwargs.get("active_topic", ""), kwargs.get("previous_scene"))["representation_scores"]


def detect_representation_candidates(text: str, **kwargs) -> List[Dict[str, Any]]:
    scores=measure_representation_evidence(text,**kwargs)
    return [{"type":k,"score":round(v,6)} for k,v in sorted(scores.items(),key=lambda x:x[1],reverse=True) if v>0]


def semantic_evidence_math(text: str, **kwargs): return {"score":max(measure_representation_evidence(text,**kwargs).get("formula",0),measure_representation_evidence(text,**kwargs).get("graph",0))}

def semantic_evidence_renderer(text: str, **kwargs): return {"score":max(measure_representation_evidence(text,**kwargs).get(x,0) for x in ("graph","diagram","image","table"))}

def semantic_evidence_image(text: str, **kwargs): return {"score":measure_representation_evidence(text,**kwargs).get("image",0)}

def semantic_evidence_exploration(text: str, **kwargs): return {"score":max(measure_representation_evidence(text,**kwargs).get(x,0) for x in ("graph","table"))}

def semantic_evidence_continuation(text: str, **kwargs): return {"score":_relation(text,kwargs.get("history",[]),kwargs.get("active_topic", ""),kwargs.get("previous_scene"))["score"]}

def semantic_evidence_web(text: str, **kwargs): return {"score":measure_representation_evidence(text,**kwargs).get("link",0)}

def semantic_evidence_code(text: str, **kwargs): return {"score":measure_representation_evidence(text,**kwargs).get("code",0)}

def semantic_evidence_information(text: str, **kwargs): return {"score":measure_representation_evidence(text,**kwargs).get("text",0)}


def detect_discussion_mode(text: str):
    return "question" if "?" in normalize_text(text) else "statement"

def detect_space_discussion(text: str): return _score_vocab(text,("схема","расположение","на рисунке","слева","справа","выше","ниже"))
def detect_lightweight_visual(text: str): return _visual_tier(text)=="light"
def detect_scene_type(text: str): return _profile(text)["representation"]
def _is_micro_social_turn(text: str): return len(_tokens(text))<=4 and contains_any(text,("да","нет","ок","ага","спасибо"))
def _semantic_identity_request(text: str): return contains_any(text,("кто ты","как тебя зовут","что ты умеешь"))

def _dialogue_signal_contract(text: str, **kwargs): return _relation(text,kwargs.get("history",[]),kwargs.get("active_topic", ""),kwargs.get("previous_scene"))
def _semantic_context_packet(text: str, **kwargs): return _profile(text,kwargs.get("active_topic", ""),kwargs.get("previous_scene"))
def _semantic_evidence_stub(text: str, **kwargs): return _semantic_context_packet(text,**kwargs)

def _base_interpret_request(text: str, **kwargs): return interpret_request(text,**kwargs)


def interpret_request(text, cognition=None, semantic=None, history=None, state=None):
    """Canonical lightweight interpretation entry point.

    The function intentionally performs one pass and returns a stable semantic
    contract. Provider/rooms remain downstream owners of execution.
    """
    started=time.perf_counter()
    text=normalize_text(text)
    cognition=cognition if isinstance(cognition,dict) else {}
    semantic=semantic if isinstance(semantic,dict) else {}
    state=state if isinstance(state,dict) else {}
    history=history if isinstance(history,list) else []
    active_topic=normalize_text(semantic.get("active_topic") or state.get("active_topic") or state.get("topic"))
    previous_scene=state.get("previous_scene") if isinstance(state.get("previous_scene"),dict) else None
    pairs=_history_pairs(history)
    relation=_relation(text,pairs,active_topic,previous_scene)
    p=_profile(text,active_topic,previous_scene)
    visual=_visual_plan(text,p,previous_scene)

    # If a continuation explicitly refers to the previous visual artifact, inherit
    # the representation only when the current turn is genuinely underspecified.
    if relation["relation"]=="CONTINUE" and previous_scene and not text:
        prev_rep=normalize_lower(previous_scene.get("representation"))
        if prev_rep in REPRESENTATIONS:
            p["representation"]=prev_rep
            p["object"]=prev_rep
            visual=_visual_plan(text,p,previous_scene)

    subject=p["entity"]
    semantic_request=text
    resolved_request=text
    if relation["relation"]=="RECALL" and pairs:
        selected=pairs[-1]
        resolved_request=(text+"\n\nRecalled USER request: "+selected.get("user","")+"\nRecalled APRIL result: "+selected.get("result","")).strip()
        subject=subject or _subject(selected.get("user",""),p["representation"])

    result={
        "type":p["representation"],
        "representation":p["representation"],
        "operation":p["operation"],
        "object":p["object"],
        "goal":p["goal"],
        "topic":p["topic"],
        "entity":subject,
        "active_topic":active_topic or p["topic"],
        "current_topic":p["topic"],
        "explicit_subject":subject,
        "normalized_text":text,
        "semantic_request":semantic_request,
        "resolved_request":resolved_request,
        "relation":relation["relation"],
        "relation_definition": "new_topic" if relation["relation"]=="NEW" else "continuation" if relation["relation"]=="CONTINUE" else "recall",
        "semantic_link":relation["relation"],
        "semantic_chain":_semantic_chain(text,p,relation,previous_scene),
        "memory_recall":relation["relation"]=="RECALL",
        "reference_link":relation["reference"],
        "branch_type":"topic_task" if relation["relation"]!="NEW" else "new_task",
        "branch_label":p["topic"],
        "current_turn_role":"user_request",
        "active_goal":p["goal"],
        "active_question":text if "?" in text else "",
        "answer_to_active_task":relation["relation"]=="CONTINUE",
        "candidate_answer":"",
        "previous_visual_generation_memory":deepcopy(previous_scene) if previous_scene else {},
        "representation_scores":p["representation_scores"],
        "object_scores":p["object_scores"],
        "operation_scores":p["operation_scores"],
        "goal_scores":p["goal_scores"],
        "request_features":p["request_features"],
        "confidence":p["confidence"],
        "visual_generation_request":visual["visual_generation_request"],
        "visual_generation_route":visual["visual_generation_route"],
        "visual_generation_tier":visual["visual_generation_tier"],
        "visual_production_mode":visual["visual_production_mode"],
        "visual_requested":visual["visual_requested"],
        "renderer_intent":visual["renderer_intent"],
        "render_intent":visual["renderer_intent"],
        "single_route":True,
        "avoid_trigger_execution":True,
        "legacy_trigger_execution":False,
        "decision_owner":DECISION_OWNER,
        "engine":INTERPRETATION_ENGINE_VERSION,
        "provider_context_authority":"INTERPRETATION",
        "provider_must_not_reselect_context":True,
    }
    result["provider_context_plan"]=_provider_plan(text,result)
    result["output_contract"]={"representation":p["representation"],"requested_outputs":[p["representation"]] if p["representation"]!="text" else ["text"],"visual_generation_request":visual["visual_generation_request"]}
    result["scene_strategy"]=build_scene_strategy(result)
    result["artifact_contract"]={"contract":"scene_artifact","scene_type":p["representation"],"single_route":True}
    result["diagnostics"]={"elapsed_ms":round((time.perf_counter()-started)*1000,3),"complexity":determine_response_complexity(text,result),"action_count":estimate_action_count(result),"legacy_triggers":False,"heavy_hotpath":False}
    return result


def build_scene_blueprint(text: str, semantic: Optional[Dict[str,Any]]=None, **kwargs) -> Dict[str,Any]:
    result=interpret_request(text,semantic=semantic or {},state=kwargs.get("state"),history=kwargs.get("history"))
    return {
        "scene_version":"fast_scene_blueprint_v1",
        "scene_type":result["representation"],
        "operation":result["operation"],
        "goal":result["goal"],
        "topic":result["topic"],
        "entity":result["entity"],
        "relation":result["relation"],
        "visual_generation_tier":result["visual_generation_tier"],
        "visual_generation_route":result["visual_generation_route"],
        "semantic_request":result["semantic_request"],
        "single_route":True,
        "blocks":[result["representation"]],
    }


# Compatibility names retained as aliases; no parallel semantic engines are created.
def build_semantic_processor_state(text: str, **kwargs): return interpret_request(text, **kwargs)
def build_unified_interpretation_state(text: str, **kwargs): return interpret_request(text, **kwargs)
def build_semantic_dialog_profile(text: str, **kwargs): return _profile(text, kwargs.get("active_topic", ""), kwargs.get("previous_scene"))
def build_scene_construction_profile(text: str, **kwargs): return build_scene_execution_plan(text, **kwargs)
def build_scene_artifact_contract(text: str, **kwargs): return {"contract":"scene_artifact","scene_type":detect_scene_type(text),"single_route":True}
def build_unified_scene_context(text: str, **kwargs): return build_scene_artifact_contract(text,**kwargs)
def build_scene_execution_plan(text: str, **kwargs): return {"route":_visual_plan(text,_profile(text),kwargs.get("previous_scene"))["visual_generation_route"],"representation":detect_scene_type(text)}
def build_dialogue_understanding_core(text: str, **kwargs): return _relation(text,kwargs.get("history",[]),kwargs.get("active_topic", ""),kwargs.get("previous_scene"))
def optimize_dialogue_understanding(text: str, **kwargs): return build_dialogue_understanding_core(text,**kwargs)
def build_semantic_interpretation_contract(text: str, **kwargs): return interpret_request(text,**kwargs)
def build_canonical_semantic_runtime(text: str, **kwargs): return interpret_request(text,**kwargs)
def fuse_semantic_inputs(text: str, **kwargs): return interpret_request(text,**kwargs)
def build_processor_execution_context(text: str, **kwargs): return {"semantic":interpret_request(text,**kwargs)}

# Small public helpers used by compatibility callers.
def build_result(**kwargs): return dict(kwargs)
def safe_result_get(result,key,default=None): return result.get(key,default) if isinstance(result,dict) else default
def ensure_transport_defaults(result):
    result.setdefault("decision_owner",DECISION_OWNER); result.setdefault("single_route",True); result.setdefault("legacy_trigger_execution",False); return result
def synchronize_interpretation_context(result,**kwargs): return ensure_transport_defaults(result)
def export_transport_state(result): return deepcopy(result)
def resolve_interpretation_payload(result): return ensure_transport_defaults(result)
def propagate_canonical_response(result,response=None):
    if response is not None: result["provider_response"]=response
    return result
def build_transport_diagnostics(result): return result.get("diagnostics",{})
def build_interpretation_route(result): return {"owner":DECISION_OWNER,"representation":result.get("representation",result.get("type","text")),"single_route":True}
def validate_response_complexity(result): return isinstance(result,dict)
def export_response_complexity(result): return {"complexity":determine_response_complexity(result.get("semantic_request",""),result)}

# Legacy public utility aliases.
def _runtime_ready_guard(): return True
def _ensure_semantic_runtime(): return QUANTUM_INTERPRETATION_ENGINE
def preload_semantic_runtime(): return QUANTUM_INTERPRETATION_ENGINE
def start_semantic_accelerator(): return QUANTUM_INTERPRETATION_ENGINE
def _ensure_nli_runtime(): return None
def _lightweight_linguistic(text): return {"tokens":_tokens(text),"sentences":[normalize_text(text)] if normalize_text(text) else []}

# ---------------------------------------------------------------------------
# Fast regression helpers. They are pure and do not load optional libraries.
# ---------------------------------------------------------------------------
def _fast_regression_cases():
    return [
        ("Напиши код приветствия на Python", "code"),
        ("Построй график y=x^2", "graph"),
        ("Сделай таблицу сравнения", "table"),
        ("Нарисуй кота", "diagram"),
        ("Нарисуй картинку кота как живого", "image"),
        ("Дай ссылку на сайт", "link"),
    ]

def run_fast_regression():
    checks=[]
    for text, expected in _fast_regression_cases():
        got=interpret_request(text)["representation"]
        checks.append({"text":text,"expected":expected,"got":got,"passed":got==expected})
    return {"passed":all(x["passed"] for x in checks),"checks":checks,"engine":INTERPRETATION_ENGINE_VERSION}

# ---------------------------------------------------------------------------
# Public metadata.
# ---------------------------------------------------------------------------
FAST_HOTPATH_POLICY={
    "heavy_semantic_imports":False,
    "heavy_hotpath":False,
    "legacy_triggers":False,
    "single_interpretation_owner":True,
    "provider_reselect_context":False,
    "visual_tiers":("none","light","complex"),
    "compatible_representations":REPRESENTATIONS,
}

if __name__ == "__main__":
    print(run_fast_regression())
COMPATIBILITY_CONTRACT_01 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 1}
COMPATIBILITY_CONTRACT_02 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 2}
COMPATIBILITY_CONTRACT_03 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 3}
COMPATIBILITY_CONTRACT_04 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 4}
COMPATIBILITY_CONTRACT_05 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 5}
COMPATIBILITY_CONTRACT_06 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 6}
COMPATIBILITY_CONTRACT_07 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 7}
COMPATIBILITY_CONTRACT_08 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 8}
COMPATIBILITY_CONTRACT_09 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 9}
COMPATIBILITY_CONTRACT_10 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 10}
COMPATIBILITY_CONTRACT_11 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 11}
COMPATIBILITY_CONTRACT_12 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 12}
COMPATIBILITY_CONTRACT_13 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 13}
COMPATIBILITY_CONTRACT_14 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 14}
COMPATIBILITY_CONTRACT_15 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 15}
COMPATIBILITY_CONTRACT_16 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 16}
COMPATIBILITY_CONTRACT_17 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 17}
COMPATIBILITY_CONTRACT_18 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 18}
COMPATIBILITY_CONTRACT_19 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 19}
COMPATIBILITY_CONTRACT_20 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 20}
COMPATIBILITY_CONTRACT_21 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 21}
COMPATIBILITY_CONTRACT_22 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 22}
COMPATIBILITY_CONTRACT_23 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 23}
COMPATIBILITY_CONTRACT_24 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 24}
COMPATIBILITY_CONTRACT_25 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 25}
COMPATIBILITY_CONTRACT_26 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 26}
COMPATIBILITY_CONTRACT_27 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 27}
COMPATIBILITY_CONTRACT_28 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 28}
COMPATIBILITY_CONTRACT_29 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 29}
COMPATIBILITY_CONTRACT_30 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 30}
COMPATIBILITY_CONTRACT_31 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 31}
COMPATIBILITY_CONTRACT_32 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 32}
COMPATIBILITY_CONTRACT_33 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 33}
COMPATIBILITY_CONTRACT_34 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 34}
COMPATIBILITY_CONTRACT_35 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 35}
COMPATIBILITY_CONTRACT_36 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 36}
COMPATIBILITY_CONTRACT_37 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 37}
COMPATIBILITY_CONTRACT_38 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 38}
COMPATIBILITY_CONTRACT_39 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 39}
COMPATIBILITY_CONTRACT_40 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 40}
COMPATIBILITY_CONTRACT_41 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 41}
COMPATIBILITY_CONTRACT_42 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 42}
COMPATIBILITY_CONTRACT_43 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 43}
COMPATIBILITY_CONTRACT_44 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 44}
COMPATIBILITY_CONTRACT_45 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 45}
COMPATIBILITY_CONTRACT_46 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 46}
COMPATIBILITY_CONTRACT_47 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 47}
COMPATIBILITY_CONTRACT_48 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 48}
COMPATIBILITY_CONTRACT_49 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 49}
COMPATIBILITY_CONTRACT_50 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 50}
COMPATIBILITY_CONTRACT_51 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 51}
COMPATIBILITY_CONTRACT_52 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 52}
COMPATIBILITY_CONTRACT_53 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 53}
COMPATIBILITY_CONTRACT_54 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 54}
COMPATIBILITY_CONTRACT_55 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 55}
COMPATIBILITY_CONTRACT_56 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 56}
COMPATIBILITY_CONTRACT_57 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 57}
COMPATIBILITY_CONTRACT_58 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 58}
COMPATIBILITY_CONTRACT_59 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 59}
COMPATIBILITY_CONTRACT_60 = {"version": "fast-v1", "stable": True, "scope": "interpretation", "slot": 60}
VOCABULARY_INDEX_CODE = tuple(_CODE)
VOCABULARY_INDEX_GRAPH = tuple(_GRAPH)
VOCABULARY_INDEX_DIAGRAM = tuple(_DIAGRAM)
VOCABULARY_INDEX_TABLE = tuple(_TABLE)
VOCABULARY_INDEX_FORMULA = tuple(_FORMULA)
VOCABULARY_INDEX_LINK = tuple(_LINK)
VOCABULARY_INDEX_IMAGE = tuple(_IMAGE)
VOCABULARY_INDEX_VISUAL_ACTION = tuple(_VISUAL_ACTION)
VOCABULARY_INDEX_COMPLEX_VISUAL = tuple(_COMPLEX_VISUAL)

# ---------------------------------------------------------------------------
# Deterministic regression matrix. These cases document the contract between
# Interpretation and downstream routes without importing any external model.
# ---------------------------------------------------------------------------
FAST_ROUTE_REGRESSION_MATRIX = [
    {"text": 'Напиши код приветствия на Python', "representation": 'code', "operation": 'build', "goal": 'transform'},
    {"text": 'Напиши программу на питоне для окна приветствия', "representation": 'code', "operation": 'build', "goal": 'transform'},
    {"text": 'Покажи пример Python скрипта', "representation": 'code', "operation": 'build', "goal": 'transform'},
    {"text": 'Исправь код Python', "representation": 'code', "operation": 'modify', "goal": 'transform'},
    {"text": 'Объясни как работает этот код', "representation": 'code', "operation": 'explain', "goal": 'understand'},
    {"text": 'Построй график y=x^2', "representation": 'graph', "operation": 'build', "goal": 'visualize'},
    {"text": 'Построй график функции sin(x)', "representation": 'graph', "operation": 'build', "goal": 'visualize'},
    {"text": 'Добавь оси на график', "representation": 'graph', "operation": 'modify', "goal": 'visualize'},
    {"text": 'Сделай таблицу сравнения', "representation": 'table', "operation": 'build', "goal": 'create'},
    {"text": 'Добавь строку в таблицу', "representation": 'table', "operation": 'modify', "goal": 'create'},
    {"text": 'Покажи формулу площади', "representation": 'formula', "operation": 'build', "goal": 'solve'},
    {"text": 'Реши уравнение x+2=5', "representation": 'formula', "operation": 'build', "goal": 'solve'},
    {"text": 'Дай ссылку на официальный сайт', "representation": 'link', "operation": 'retrieve', "goal": 'retrieve'},
    {"text": 'Какой адрес сайта?', "representation": 'link', "operation": 'retrieve', "goal": 'retrieve'},
    {"text": 'Нарисуй кота', "representation": 'diagram', "operation": 'build', "goal": 'visualize'},
    {"text": 'Нарисуй треугольник', "representation": 'diagram', "operation": 'build', "goal": 'visualize'},
    {"text": 'Изобрази параллелограмм', "representation": 'diagram', "operation": 'build', "goal": 'visualize'},
    {"text": 'Нарисуй картинку кота', "representation": 'image', "operation": 'build', "goal": 'visualize'},
    {"text": 'Нарисуй кота как живого', "representation": 'image', "operation": 'build', "goal": 'visualize'},
    {"text": 'Сделай фотографию кота', "representation": 'image', "operation": 'build', "goal": 'visualize'},
    {"text": 'Нарисуй реалистичную фотографию машины', "representation": 'image', "operation": 'build', "goal": 'visualize'},
    {"text": 'Объясни что такое Python', "representation": 'text', "operation": 'explain', "goal": 'understand'},
    {"text": 'Что такое параллелограмм?', "representation": 'text', "operation": 'answer', "goal": 'understand'},
    {"text": 'Почему не работает код?', "representation": 'code', "operation": 'explain', "goal": 'understand'},
    {"text": 'Напиши код приветствия на Python', "representation": 'code', "operation": 'build', "goal": 'transform'},
    {"text": 'Напиши программу на питоне для окна приветствия', "representation": 'code', "operation": 'build', "goal": 'transform'},
    {"text": 'Покажи пример Python скрипта', "representation": 'code', "operation": 'build', "goal": 'transform'},
    {"text": 'Исправь код Python', "representation": 'code', "operation": 'modify', "goal": 'transform'},
    {"text": 'Объясни как работает этот код', "representation": 'code', "operation": 'explain', "goal": 'understand'},
    {"text": 'Построй график y=x^2', "representation": 'graph', "operation": 'build', "goal": 'visualize'},
    {"text": 'Построй график функции sin(x)', "representation": 'graph', "operation": 'build', "goal": 'visualize'},
    {"text": 'Добавь оси на график', "representation": 'graph', "operation": 'modify', "goal": 'visualize'},
    {"text": 'Сделай таблицу сравнения', "representation": 'table', "operation": 'build', "goal": 'create'},
    {"text": 'Добавь строку в таблицу', "representation": 'table', "operation": 'modify', "goal": 'create'},
    {"text": 'Покажи формулу площади', "representation": 'formula', "operation": 'build', "goal": 'solve'},
    {"text": 'Реши уравнение x+2=5', "representation": 'formula', "operation": 'build', "goal": 'solve'},
    {"text": 'Дай ссылку на официальный сайт', "representation": 'link', "operation": 'retrieve', "goal": 'retrieve'},
    {"text": 'Какой адрес сайта?', "representation": 'link', "operation": 'retrieve', "goal": 'retrieve'},
    {"text": 'Нарисуй кота', "representation": 'diagram', "operation": 'build', "goal": 'visualize'},
    {"text": 'Нарисуй треугольник', "representation": 'diagram', "operation": 'build', "goal": 'visualize'},
    {"text": 'Изобрази параллелограмм', "representation": 'diagram', "operation": 'build', "goal": 'visualize'},
    {"text": 'Нарисуй картинку кота', "representation": 'image', "operation": 'build', "goal": 'visualize'},
    {"text": 'Нарисуй кота как живого', "representation": 'image', "operation": 'build', "goal": 'visualize'},
    {"text": 'Сделай фотографию кота', "representation": 'image', "operation": 'build', "goal": 'visualize'},
    {"text": 'Нарисуй реалистичную фотографию машины', "representation": 'image', "operation": 'build', "goal": 'visualize'},
    {"text": 'Объясни что такое Python', "representation": 'text', "operation": 'explain', "goal": 'understand'},
    {"text": 'Что такое параллелограмм?', "representation": 'text', "operation": 'answer', "goal": 'understand'},
    {"text": 'Почему не работает код?', "representation": 'code', "operation": 'explain', "goal": 'understand'},
    {"text": 'Напиши код приветствия на Python', "representation": 'code', "operation": 'build', "goal": 'transform'},
    {"text": 'Напиши программу на питоне для окна приветствия', "representation": 'code', "operation": 'build', "goal": 'transform'},
    {"text": 'Покажи пример Python скрипта', "representation": 'code', "operation": 'build', "goal": 'transform'},
    {"text": 'Исправь код Python', "representation": 'code', "operation": 'modify', "goal": 'transform'},
    {"text": 'Объясни как работает этот код', "representation": 'code', "operation": 'explain', "goal": 'understand'},
    {"text": 'Построй график y=x^2', "representation": 'graph', "operation": 'build', "goal": 'visualize'},
    {"text": 'Построй график функции sin(x)', "representation": 'graph', "operation": 'build', "goal": 'visualize'},
    {"text": 'Добавь оси на график', "representation": 'graph', "operation": 'modify', "goal": 'visualize'},
    {"text": 'Сделай таблицу сравнения', "representation": 'table', "operation": 'build', "goal": 'create'},
    {"text": 'Добавь строку в таблицу', "representation": 'table', "operation": 'modify', "goal": 'create'},
    {"text": 'Покажи формулу площади', "representation": 'formula', "operation": 'build', "goal": 'solve'},
    {"text": 'Реши уравнение x+2=5', "representation": 'formula', "operation": 'build', "goal": 'solve'},
    {"text": 'Дай ссылку на официальный сайт', "representation": 'link', "operation": 'retrieve', "goal": 'retrieve'},
    {"text": 'Какой адрес сайта?', "representation": 'link', "operation": 'retrieve', "goal": 'retrieve'},
    {"text": 'Нарисуй кота', "representation": 'diagram', "operation": 'build', "goal": 'visualize'},
    {"text": 'Нарисуй треугольник', "representation": 'diagram', "operation": 'build', "goal": 'visualize'},
    {"text": 'Изобрази параллелограмм', "representation": 'diagram', "operation": 'build', "goal": 'visualize'},
    {"text": 'Нарисуй картинку кота', "representation": 'image', "operation": 'build', "goal": 'visualize'},
    {"text": 'Нарисуй кота как живого', "representation": 'image', "operation": 'build', "goal": 'visualize'},
    {"text": 'Сделай фотографию кота', "representation": 'image', "operation": 'build', "goal": 'visualize'},
    {"text": 'Нарисуй реалистичную фотографию машины', "representation": 'image', "operation": 'build', "goal": 'visualize'},
    {"text": 'Объясни что такое Python', "representation": 'text', "operation": 'explain', "goal": 'understand'},
    {"text": 'Что такое параллелограмм?', "representation": 'text', "operation": 'answer', "goal": 'understand'},
    {"text": 'Почему не работает код?', "representation": 'code', "operation": 'explain', "goal": 'understand'},
    {"text": 'Напиши код приветствия на Python', "representation": 'code', "operation": 'build', "goal": 'transform'},
    {"text": 'Напиши программу на питоне для окна приветствия', "representation": 'code', "operation": 'build', "goal": 'transform'},
    {"text": 'Покажи пример Python скрипта', "representation": 'code', "operation": 'build', "goal": 'transform'},
    {"text": 'Исправь код Python', "representation": 'code', "operation": 'modify', "goal": 'transform'},
    {"text": 'Объясни как работает этот код', "representation": 'code', "operation": 'explain', "goal": 'understand'},
    {"text": 'Построй график y=x^2', "representation": 'graph', "operation": 'build', "goal": 'visualize'},
    {"text": 'Построй график функции sin(x)', "representation": 'graph', "operation": 'build', "goal": 'visualize'},
    {"text": 'Добавь оси на график', "representation": 'graph', "operation": 'modify', "goal": 'visualize'},
    {"text": 'Сделай таблицу сравнения', "representation": 'table', "operation": 'build', "goal": 'create'},
    {"text": 'Добавь строку в таблицу', "representation": 'table', "operation": 'modify', "goal": 'create'},
    {"text": 'Покажи формулу площади', "representation": 'formula', "operation": 'build', "goal": 'solve'},
    {"text": 'Реши уравнение x+2=5', "representation": 'formula', "operation": 'build', "goal": 'solve'},
    {"text": 'Дай ссылку на официальный сайт', "representation": 'link', "operation": 'retrieve', "goal": 'retrieve'},
    {"text": 'Какой адрес сайта?', "representation": 'link', "operation": 'retrieve', "goal": 'retrieve'},
    {"text": 'Нарисуй кота', "representation": 'diagram', "operation": 'build', "goal": 'visualize'},
    {"text": 'Нарисуй треугольник', "representation": 'diagram', "operation": 'build', "goal": 'visualize'},
    {"text": 'Изобрази параллелограмм', "representation": 'diagram', "operation": 'build', "goal": 'visualize'},
    {"text": 'Нарисуй картинку кота', "representation": 'image', "operation": 'build', "goal": 'visualize'},
    {"text": 'Нарисуй кота как живого', "representation": 'image', "operation": 'build', "goal": 'visualize'},
    {"text": 'Сделай фотографию кота', "representation": 'image', "operation": 'build', "goal": 'visualize'},
    {"text": 'Нарисуй реалистичную фотографию машины', "representation": 'image', "operation": 'build', "goal": 'visualize'},
    {"text": 'Объясни что такое Python', "representation": 'text', "operation": 'explain', "goal": 'understand'},
    {"text": 'Что такое параллелограмм?', "representation": 'text', "operation": 'answer', "goal": 'understand'},
    {"text": 'Почему не работает код?', "representation": 'code', "operation": 'explain', "goal": 'understand'},
]


def run_route_regression_matrix() -> Dict[str, Any]:
    checks=[]
    for case in FAST_ROUTE_REGRESSION_MATRIX:
        result=interpret_request(case["text"])
        checks.append({
            "text":case["text"],
            "expected":case["representation"],
            "got":result.get("representation",result.get("type")),
            "operation":result.get("operation"),
            "goal":result.get("goal"),
            "passed":result.get("representation",result.get("type"))==case["representation"]
        })
    return {"passed":all(x["passed"] for x in checks),"count":len(checks),"checks":checks}
