"""
APRIL — LIGHT UNIFIED INTERPRETATION LAYER

Single lightweight semantic dependency: rapidfuzz.
The layer owns interpretation/evidence only. Routing, providers, execution and
rendering stay outside this module.

ARC = Adaptive Relation Compression: current request -> active sequence ->
semantic relation -> compact provider-safe context.
"""
from __future__ import annotations

import hashlib
import re
import threading
import time
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Iterable

from rapidfuzz import fuzz

RESPONSE_COMPLEXITY_LOW = "LOW"
RESPONSE_COMPLEXITY_MEDIUM = "MEDIUM"
RESPONSE_COMPLEXITY_HIGH = "HIGH"
DECISION_OWNER = "QUANTUM_PROCESSOR"
TRANSPORT_NAME = "transport_state"
_DIALOGUE_ALPHABET_RU = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
DIALOGUE_WINDOW_HOURS = 12
USER_CONTENT_RETENTION_SECONDS = DIALOGUE_WINDOW_HOURS * 3600
PROVIDER_INPUT_HARD_BUDGET = 900
PROVIDER_INPUT_SOFT_TARGET_NEW = 850
PROVIDER_INPUT_SOFT_TARGET_CONTINUE = 820
PROVIDER_INPUT_SOFT_TARGET_RECALL = 800
PROVIDER_CONTEXT_PLAN_VERSION = "provider_context_plan_v2_dependency_first"
SEMANTIC_ANCHOR_VERSION = "semantic_anchor_v2_arc"
LIVE_CONTINUITY_SCORE_THRESHOLD = 0.24
LIVE_WINDOW_RECOVERY_SCORE_THRESHOLD = 0.30

DIALOGUE_LABELS = (
    "identity", "greeting", "question", "request", "continuation",
    "reformulation", "correction", "reference", "affirmation", "rejection",
    "new_topic", "statement", "independent", "memory_query",
)

REPRESENTATION_HYPOTHESES = {
    "text": "обычный текстовый ответ объяснение рассказ описание",
    "table": "таблица строки колонки сравнение параметры",
    "graph": "график диаграмма визуализация числовых данных",
    "diagram": "схема диаграмма связей блоков структура процесса",
    "formula": "формула уравнение математическое выражение",
    "image": "изображение картинка рисунок иллюстрация фотография",
    "gallery": "несколько изображений подборка галерея",
    "code": "код программирование функция программа python",
    "link": "ссылка адрес сайта веб ресурс",
}
DIALOGUE_PROTOTYPES = {
    "identity": "кто ты как тебя зовут представься",
    "greeting": "привет здравствуй доброе утро как дела",
    "question": "вопрос ответ что такое почему сколько как",
    "request": "сделай дай скажи расскажи покажи выполни задача",
    "continuation": "продолжай продолжим дальше следующее теперь ещё",
    "reformulation": "перепиши переделай переформулируй измени ответ",
    "correction": "исправь я не это имел в виду не спрашивал уточняю",
    "reference": "это тот предыдущий ответ как раньше вернись к",
    "affirmation": "да верно правильно точно хорошо согласен",
    "rejection": "нет неверно неправильно не то",
    "new_topic": "новая тема другой предмет сменим тему теперь поговорим",
    "statement": "я сообщаю рассказываю утверждение факт",
    "independent": "самостоятельный отдельный запрос",
    "memory_query": "вспомни что я спрашивал о чем говорили предыдущий диалог память",
}
DOMAIN_HYPOTHESES = {
    "biology": "биология клетки животные растения генетика организм",
    "chemistry": "химия вещества реакции молекулы атомы",
    "physics": "физика сила энергия движение скорость масса поле",
    "engineering": "инженерия конструкция проектирование устройство система",
    "it": "программирование компьютер код алгоритм приложение",
    "literature": "литература писатель роман поэзия стихотворение",
    "politics": "политика государство правительство выборы закон",
    "news": "новости текущие события",
    "social": "общество люди отношения социальные темы",
    "web": "интернет сайт поиск веб ресурс",
}
CAPABILITY_HYPOTHESES = {
    "exploration": "анализ сравнение исследование изучение разбор",
    "web": "поиск интернет сайт веб информация",
    "code": "код программирование программная реализация",
    "information": "объяснение информация ответ разъяснение",
    "discussion": "обсуждение мнение рассуждение аргументы",
    "space": "пространство сцена композиция расположение визуальная структура",
}
SCENE_MATRIX_LABELS = ("text", "table", "graph", "diagram", "formula", "image", "gallery", "code", "link")
SCENE_MATRIX_FEATURES = ("dialogue", "representation", "domain", "capability", "continuity", "context", "modality")
SCENE_MATRIX_CAPABILITY = {
    "text": "information", "table": "information", "graph": "exploration",
    "diagram": "space", "formula": "information", "image": "space",
    "gallery": "space", "code": "code", "link": "web",
}
SCENE_MATRIX_DOMAIN_BIAS = {
    "biology": {"graph": .08, "table": .06, "diagram": .08},
    "chemistry": {"formula": .10, "table": .05, "diagram": .05},
    "physics": {"graph": .09, "formula": .09, "diagram": .05},
    "engineering": {"diagram": .10, "graph": .06, "table": .04},
    "it": {"code": .10, "diagram": .06, "table": .04},
    "literature": {"text": .08},
    "politics": {"table": .06, "graph": .06},
    "news": {"link": .05, "table": .05, "graph": .05},
    "social": {"table": .04, "graph": .04},
    "web": {"link": .10},
}
_SCENE_WEIGHTS = (
    (.12,.55,.03,.20,.04,.03,.03), (.08,.62,.03,.20,.02,.03,.02),
    (.04,.68,.05,.16,.02,.03,.02), (.04,.62,.06,.20,.02,.04,.02),
    (.03,.70,.07,.16,.01,.02,.01), (.03,.72,.03,.17,.01,.02,.02),
    (.03,.74,.03,.16,.01,.02,.01), (.02,.70,.03,.22,.01,.01,.01),
    (.02,.66,.05,.22,.01,.03,.01),
)
OBLIGATION_SCHEMA_VERSION = "april_dialogue_obligation_v1"
INTERPRETATION_ROUTE = (
    "dialogue_profile", "semantic_evidence_engine", "dialogue_cognition_matrix",
    "semantic_dialogue_graph", "scene_profile", "artifact_contract",
    "executor_preparation_contract",
)
SEMANTIC_EVIDENCE_PRIORITY = (
    "current_request", "active_goal", "dialogue_history", "voice_context",
    "vision_context", "gallery_context", "file_context", "semantic_profile",
)
LEGACY_TRIGGER_FLAGS = ()
CANONICAL_SEMANTIC_RUNTIME = {
    "transport": TRANSPORT_NAME, "reasoning": "arc_light",
    "legacy_trigger_execution": False, "single_scene": True,
    "single_processor": True, "single_executor": True,
}
SEMANTIC_INTERPRETATION_CORE = {
    "decision_source": DECISION_OWNER, "routing": "processor_owned",
    "scene_contract": "artifact_first", "executor_contract": "advisory_only",
    "history_model": "active_12h_sequence", "compression": "ARC",
}


def _obligation_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())

def extract_dialogue_obligations(text: str) -> list[dict[str, Any]]:
    value = _obligation_text(text)
    if not value:
        return []
    hits = []
    if re.search(r"\b(?:буду|будем|дальше буду|обязательно|нужно будет|следом)\b", value.lower()):
        hits.append({"schema": OBLIGATION_SCHEMA_VERSION, "kind": "future_commitment", "text": value[:500], "status": "open"})
    return hits

def merge_dialogue_obligations(*sources: Any) -> list[dict[str, Any]]:
    out = []
    seen = set()
    for source in sources:
        items = source if isinstance(source, list) else [source]
        for item in items:
            if not isinstance(item, dict):
                continue
            key = (_obligation_text(item.get("kind")), _obligation_text(item.get("text")))
            if key in seen or not key[1]:
                continue
            seen.add(key); out.append(deepcopy(item))
    return out[-32:]

def mark_obligation_status(obligations: Any, *, trigger: str, text: str = "") -> list[dict[str, Any]]:
    result = merge_dialogue_obligations([], obligations)
    needle = _obligation_text(trigger).lower()
    for item in result:
        if needle and needle in _obligation_text(item.get("text")).lower():
            item["status"] = "fulfilled"
    return result

@dataclass
class SemanticEvidence:
    label: str
    score: float
    source: str
    positive: bool = True
    details: Dict[str, Any] | None = None
    def as_dict(self) -> Dict[str, Any]:
        return {"label": self.label, "score": max(0.0, min(1.0, float(self.score))), "source": self.source, "positive": bool(self.positive), "details": self.details or {}}



class QuantumInterpretationEngine:
    """Single lightweight interpretation engine backed by rapidfuzz."""
    VERSION = "APRIL-ARC-LIGHT-1"
    def __init__(self) -> None:
        self._lock = threading.RLock(); self._cache = {}; self._cache_limit = 512

    @staticmethod
    def normalize(text: Any) -> str:
        return re.sub(r"\s+", " ", str(text or "").strip())

    @staticmethod
    def _tokens(text: Any) -> list[str]:
        return re.findall(r"[a-zа-яёіїєґ0-9_]+", QuantumInterpretationEngine.normalize(text).lower())

    @classmethod
    def _similarity_value(cls, a: Any, b: Any) -> float:
        aa, bb = cls.normalize(a), cls.normalize(b)
        if not aa or not bb: return 0.0
        ts = fuzz.token_set_ratio(aa, bb) / 100.0
        pr = fuzz.partial_ratio(aa, bb) / 100.0
        return round(max(ts * .72 + pr * .28, ts), 6)

    def similarity(self, text_a: str, text_b: str) -> dict[str, Any]:
        score = self._similarity_value(text_a, text_b)
        return {"score": score, "source": "rapidfuzz_arc", "measured": bool(score), "cached": False}

    def similarities(self, text: str, candidates: Sequence[str]) -> dict[str, float]:
        return {self.normalize(c): self._similarity_value(text, c) for c in candidates if self.normalize(c)}

    def prewarm_static(self, candidates: Sequence[str]) -> int:
        return len({self.normalize(x) for x in candidates if self.normalize(x)})

    def _history(self, history: Any) -> tuple[str, str, Any]:
        last_a = last_u = ""; reply = None
        turns = history if isinstance(history, list) else []
        for item in reversed(turns):
            if not isinstance(item, dict): continue
            role = self.normalize(item.get("role")).lower()
            if not last_a and role in {"assistant","april","bot"}:
                last_a = self.normalize(item.get("answer") or item.get("content") or item.get("summary") or item.get("text")); reply = item.get("turn_id")
            if not last_u and role in {"user","human"}:
                last_u = self.normalize(item.get("content") or item.get("text") or item.get("answer"))
            if last_a and last_u: break
        return last_a, last_u, reply

    def _family_scores(self, text: str, prototypes: dict[str, str]) -> dict[str, float]:
        if not text: return {k: 0.0 for k in prototypes}
        return {k: self._similarity_value(text, v) for k, v in prototypes.items()}

    def _context_scores(self, text: str, previous_assistant: str = "", previous_user: str = "", active_topic: str = "", active_goal: str = "") -> dict[str, float]:
        return {
            "previous_assistant": self._similarity_value(text, previous_assistant),
            "previous_user": self._similarity_value(text, previous_user),
            "active_topic": self._similarity_value(text, active_topic),
            "active_goal": self._similarity_value(text, active_goal),
        }

    def _linguistic(self, text: str) -> dict[str, Any]:
        tokens = self._tokens(text)
        return {"language": None, "tokens": tokens, "lemmas": tokens, "pos": [], "dependencies": [], "entities": [], "sentences": [text] if text else [], "source": "arc_light", "engine": self.VERSION}

    def scene_matrix(self, *, dialogue: dict[str,float], representation: dict[str,float], domain: dict[str,float], capability: dict[str,float], context: dict[str,float], modalities: dict[str,Any] | None = None, explicit_representations: Sequence[str] = ()) -> dict[str,Any]:
        vector = [
            max((dialogue.get(x,0.0) for x in ("continuation","reference","question","request")), default=0.0),
            max(representation.values(), default=0.0), max(domain.values(), default=0.0),
            max(capability.values(), default=0.0), max(context.values(), default=0.0),
            max(context.get("active_topic",0.0), context.get("active_goal",0.0), 0.0),
            min(1.0, sum(v not in (None,"",{},[]) for v in (modalities or {}).values())/3.0),
        ]
        raw = []
        for row in _SCENE_WEIGHTS:
            raw.append(sum(a*b for a,b in zip(row, vector)))
        for scene in SCENE_MATRIX_LABELS:
            raw[SCENE_MATRIX_LABELS.index(scene)] += .34 * float(representation.get(scene,0.0))
            raw[SCENE_MATRIX_LABELS.index(scene)] += .10 * float(capability.get(SCENE_MATRIX_CAPABILITY[scene],0.0))
        for domain_name, bias_map in SCENE_MATRIX_DOMAIN_BIAS.items():
            ds = float(domain.get(domain_name,0.0))
            for scene,bias in bias_map.items(): raw[SCENE_MATRIX_LABELS.index(scene)] += ds*bias
        for scene in explicit_representations:
            if scene in SCENE_MATRIX_LABELS: raw[SCENE_MATRIX_LABELS.index(scene)] += .45
        mx = max(raw, default=0.0); scores = [x/mx if mx else 0.0 for x in raw]
        ranked = sorted(zip(SCENE_MATRIX_LABELS,scores), key=lambda x:x[1], reverse=True)
        return {"labels":[x[0] for x in ranked],"scores":[round(float(x[1]),6) for x in ranked],"best_scene":ranked[0][0],"best_score":round(float(ranked[0][1]),6),"margin":round(float(ranked[0][1]-(ranked[1][1] if len(ranked)>1 else 0.0)),6),"feature_order":list(SCENE_MATRIX_FEATURES),"feature_vector":[round(x,6) for x in vector],"matrix_shape":[len(_SCENE_WEIGHTS),len(SCENE_MATRIX_FEATURES)],"explicit_representations":list(explicit_representations),"engine":"arc_light","mode":"fuzzy_evidence_fusion","decision_owner":DECISION_OWNER,"evidence_only":True}

    def measure(self, text: str, *, previous_assistant: str = "", previous_user: str = "", active_topic: str = "", active_goal: str = "", modalities: dict[str,Any] | None = None) -> dict[str,Any]:
        text = self.normalize(text); key = (text, previous_assistant, previous_user, active_topic, active_goal)
        with self._lock:
            if key in self._cache: return deepcopy(self._cache[key])
        dialogue = self._family_scores(text, DIALOGUE_PROTOTYPES)
        representation = self._family_scores(text, REPRESENTATION_HYPOTHESES)
        domain = self._family_scores(text, DOMAIN_HYPOTHESES)
        capability = self._family_scores(text, CAPABILITY_HYPOTHESES)
        context = self._context_scores(text, previous_assistant, previous_user, active_topic, active_goal)
        dialogue_ranked = sorted(dialogue.items(), key=lambda x:x[1], reverse=True)
        rep_ranked = sorted(representation.items(), key=lambda x:x[1], reverse=True)
        best_dialogue, best_d = dialogue_ranked[0] if dialogue_ranked else ("question",0.0)
        best_rep, rep_d = rep_ranked[0] if rep_ranked else ("text",0.0)
        explicit_reps = [k for k,v in sorted(representation.items(), key=lambda x:x[1], reverse=True) if k != "text" and v >= .58 and v >= representation.get("text",0.0)+.06]
        scene = self.scene_matrix(dialogue=dialogue, representation=representation, domain=domain, capability=capability, context=context, modalities=modalities, explicit_representations=explicit_reps)
        profile = {"dialogue_scores": dialogue,"representation_scores": representation,"domain_scores": domain,"capability_scores": capability,"context_scores": context,"dialogue_best":best_dialogue,"dialogue_confidence":float(best_d),"best_representation":best_rep,"best_representation_score":float(rep_d),"representation_margin":float(rep_d-(rep_ranked[1][1] if len(rep_ranked)>1 else 0.0)),"explicit_representations":explicit_reps,"identity_request":dialogue.get("identity",0.0)>=max(.55, dialogue.get("continuation",0.0)),"fast_social":best_dialogue in {"identity","greeting"} and len(text.split())<=24,"scene_matrix":scene,"source":"arc_light_fuzzy"}
        with self._lock:
            self._cache[key]=deepcopy(profile)
            if len(self._cache)>self._cache_limit: self._cache.pop(next(iter(self._cache)))
        return profile

    def fast_semantic_profile(self, text: str, previous_assistant: str = "", previous_user: str = "", active_topic: str = "", active_goal: str = "") -> dict[str,Any]:
        return self.measure(text, previous_assistant=previous_assistant, previous_user=previous_user, active_topic=active_topic, active_goal=active_goal)

    def turn_measurement(self, text: str, previous_assistant: str = "", previous_user: str = "", active_goal: str = "", active_topic: str = "") -> dict[str,Any]:
        p=self.measure(text, previous_assistant=previous_assistant, previous_user=previous_user, active_topic=active_topic, active_goal=active_goal)
        return {"linguistic":self._linguistic(text),"dialogue_nli":{"labels":list(p["dialogue_scores"]),"scores":list(p["dialogue_scores"].values()),"source":"arc_light"},"representation_nli":{"labels":list(p["representation_scores"]),"scores":list(p["representation_scores"].values()),"source":"arc_light"},"domain_nli":{"labels":list(p["domain_scores"]),"scores":list(p["domain_scores"].values()),"source":"arc_light"},"capability_nli":{"labels":list(p["capability_scores"]),"scores":list(p["capability_scores"].values()),"source":"arc_light"},"embeddings":dict(p["context_scores"]),"decision_owner":DECISION_OWNER,"evidence_only":True,"engine":"arc_light_turn_engine"}

    def dialogue(self, text: str, previous_assistant: str = "", previous_user: str = "", active_goal: str = "", active_topic: str = "", open_task: dict[str,Any] | None = None) -> dict[str,Any]:
        p=self.measure(text, previous_assistant=previous_assistant, previous_user=previous_user, active_topic=active_topic, active_goal=active_goal); d=p["dialogue_scores"]; c=p["context_scores"]; best=p["dialogue_best"]
        continuation_score=max(d.get("continuation",0.0), .76*c.get("previous_assistant",0.0), .62*c.get("previous_user",0.0), .70*c.get("active_topic",0.0))
        reference_score=max(d.get("reference",0.0), .84*c.get("previous_assistant",0.0), .66*c.get("previous_user",0.0), .72*c.get("active_topic",0.0), d.get("memory_query",0.0))
        task = open_task if isinstance(open_task,dict) else {}
        task_signal = bool(task and (task.get("active") or task.get("status") == "open"))
        if task_signal and any(x in best for x in ("continuation","reference","correction","reformulation")): continuation_score=max(continuation_score,.90)
        continuation=bool(previous_assistant and (best in {"continuation","reformulation","correction","reference","affirmation","rejection"} or continuation_score>=.66 or task_signal and len(text.split())<=12))
        return {"dialogue":{"label":best,"confidence":float(max(d.values(),default=0.0)),"continuation_score":float(continuation_score),"reference_score":float(reference_score),"topic_score":float(c.get("active_topic",0.0)),"goal_score":float(c.get("active_goal",0.0))},"linguistic":self._linguistic(text),"continuation":continuation,"reference_to_previous":bool(previous_assistant and reference_score>=.60),"identity_request":bool(p["identity_request"]),"nli":{"labels":list(d),"scores":list(d.values()),"source":"arc_light"},"decision_owner":DECISION_OWNER,"evidence_only":True,"engine":"arc_light_dialogue_engine"}

    def representations(self, text: str, context: str = "") -> dict[str,Any]:
        p=self.measure(text, active_topic=context); return {"nli":{"labels":list(p["representation_scores"]),"scores":list(p["representation_scores"].values()),"source":"arc_light"},"measurements":[{"type":k,"score":float(v),"source":"arc_light"} for k,v in sorted(p["representation_scores"].items(), key=lambda x:x[1], reverse=True)],"context_similarity":{"score":float(p["context_scores"].get("active_topic",0.0)),"source":"arc_light"},"decision_owner":DECISION_OWNER,"evidence_only":True,"engine":"arc_light_representation_engine"}

    def domains(self, text: str) -> dict[str,Any]:
        p=self.measure(text); return {"measurements":[{"domain":k,"score":float(v)} for k,v in sorted(p["domain_scores"].items(), key=lambda x:x[1], reverse=True)],"decision_owner":DECISION_OWNER,"evidence_only":True,"engine":"arc_light_domain_engine"}

    def classify(self, text: str, hypotheses: Sequence[str]) -> dict[str,Any]:
        p=self.measure(text); all_scores={**p["dialogue_scores"],**p["representation_scores"],**p["domain_scores"],**p["capability_scores"]}; ranked=sorted(((str(x),float(all_scores.get(x,0.0))) for x in hypotheses), key=lambda x:x[1], reverse=True); return {"labels":[x[0] for x in ranked],"scores":[x[1] for x in ranked],"source":"arc_light"}

    def _resolve_scene_context(self, text: str, state: dict[str,Any], *, continuation: bool, reference: bool, active_topic: str = "") -> dict[str,Any]:
        if not isinstance(state,dict) or not (continuation or reference): return {}
        scene = state.get("current_visual_scene") or state.get("active_visual_scene")
        if not isinstance(scene,dict): return {}
        hay=" ".join(str(scene.get(k) or "") for k in ("topic","user_request","summary","april_answer"))
        score=1.0 if continuation else self._similarity_value(text, hay)
        return {"relation":"current_scene","confidence":round(score,6),"scene_id":str(scene.get("scene_id") or ""),"turn_id":scene.get("turn_id"),"topic":self.normalize(scene.get("topic")),"user_request":self.normalize(scene.get("user_request") or scene.get("current_request")),"answer":self.normalize(scene.get("april_answer") or scene.get("answer") or scene.get("content")),"summary":self.normalize(scene.get("summary")),"render_block_types":list(scene.get("render_block_types") or []),"presentation_types":list(scene.get("presentation_types") or []),"renderer_state":scene.get("renderer_state") if isinstance(scene.get("renderer_state"),dict) else {},"semantic_source":"arc_light_scene_resolution","evidence_only":True}

    def interpret(self, text: str, cognition: dict|None=None, semantic: dict|None=None, history: list|None=None, state: dict|None=None) -> dict[str,Any] | None:
        fn=globals().get("_df_interpret_live_turn")
        if callable(fn): return fn(text, history=history or [], state=state or {})
        return self.measure(text)


QUANTUM_INTERPRETATION_ENGINE = QuantumInterpretationEngine()
QUANTUM_FAST_SEMANTIC = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_LINGUISTIC_ENGINE = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_EMBEDDING_ENGINE = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_INTENT_ENGINE = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_EVIDENCE_FUSION = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_DIALOGUE_ENGINE = QUANTUM_INTERPRETATION_ENGINE

# Compatibility API: the shared runtime is now the lightweight ARC engine itself.
SEMANTIC_MODEL_NAME = "rapidfuzz-arc-light"

def get_shared_semantic_encoder():
    return QUANTUM_INTERPRETATION_ENGINE

def _runtime_ready_guard() -> None:
    return None

def _ensure_semantic_runtime() -> None:
    return None

def preload_semantic_runtime() -> None:
    return None

def start_semantic_accelerator() -> None:
    return None

def _ensure_nli_runtime() -> None:
    return None

def _lightweight_linguistic(text: str) -> Dict[str, Any]:
    return QUANTUM_INTERPRETATION_ENGINE._linguistic(normalize_text(text))

QuantumFastSemanticEngine = QuantumInterpretationEngine
QuantumLinguisticEngine = QuantumInterpretationEngine
QuantumEmbeddingEngine = QuantumInterpretationEngine
QuantumIntentEngine = QuantumInterpretationEngine
QuantumEvidenceFusionEngine = QuantumInterpretationEngine
QuantumDialogueEngine = QuantumInterpretationEngine
QuantumSceneInterpretationMatrix = QuantumInterpretationEngine

def build_scene_blueprint(
    *,
    text: str,
    requested_outputs: Sequence[str] = (),
    scene_composition: Sequence[Any] = (),
    production_representation: str = "text",
    active_topic: str = "",
    active_goal: str = "",
    subject: str = "",
    semantic_summary: str = "",
    dialogue: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a renderer-neutral scene blueprint for Semantic Core.

    This helper contains no routing and no renderer selection. It preserves the
    Interpretation decision as a compact semantic scene description.
    """
    reps: list[str] = []
    for value in list(requested_outputs or ()) + list(scene_composition or ()) + [production_representation]:
        if isinstance(value, dict):
            value = value.get("type") or value.get("representation") or value.get("kind")
        value = str(value or "").strip().lower()
        if value and value not in reps:
            reps.append(value)
    if not reps:
        reps = ["text"]

    preferred = str(production_representation or "text").strip().lower() or reps[0]
    if preferred not in reps:
        reps.insert(0, preferred)

    dialogue = dialogue if isinstance(dialogue, dict) else {}
    live_scene = dialogue.get("live_scene") if isinstance(dialogue.get("live_scene"), dict) else {}

    return {
        "version": "live_scene_blueprint_v1",
        "scene_kind": "composite" if len(reps) > 1 else reps[0],
        "representations": reps,
        "preferred_representation": preferred,
        "active_topic": str(active_topic or live_scene.get("topic") or "").strip(),
        "active_goal": str(active_goal or live_scene.get("goal") or "").strip(),
        "subject": str(subject or "").strip(),
        "semantic_summary": str(semantic_summary or text or "").strip()[:1800],
        "dialogue": {
            "relation": str(
                dialogue.get("three_way_relation")
                or dialogue.get("relation")
                or "NEW"
            ).strip().upper(),
            "continuation": bool(dialogue.get("continuation")),
            "reference_to_previous": bool(dialogue.get("reference_to_previous")),
            "scene_id": str(
                dialogue.get("scene_id")
                or live_scene.get("scene_id")
                or ""
            ).strip(),
            "canonical_topic": str(
                dialogue.get("canonical_topic")
                or active_topic
                or live_scene.get("topic")
                or ""
            ).strip(),
        },
        "composition": [dict(x) if isinstance(x, dict) else str(x) for x in list(scene_composition or ())[:16]],
        "ownership": {
            "interpretation_owner": "INTERPRETATION_LAYER",
            "semantic_owner": "SEMANTIC_CORE",
            "renderer_owner": "PROCESSOR_SELECTED",
        },
        "renderer_neutral": True,
    }


def normalize_text(text: Any) -> str:
    return QUANTUM_INTERPRETATION_ENGINE.normalize(text)


def normalize_lower(text: Any) -> str:
    return normalize_text(text).lower()


def contains_any(text: str, words: Sequence[str]) -> bool:
    tokens = set(QUANTUM_INTERPRETATION_ENGINE._tokens(normalize_text(text)))
    return bool(tokens & {normalize_lower(x) for x in words})


def _semantic_evidence_stub(kind: str, text: str) -> bool:
    return contains_any(text, (kind,))


def detect_domain_candidates(text: str):
    return [
        x["domain"] for x in QUANTUM_INTERPRETATION_ENGINE.domains(text)["measurements"]
        if float(x["score"]) >= 0.45
    ]


def build_domain_confidence(text: str):
    return {
        x["domain"]: round(float(x["score"]), 4)
        for x in QUANTUM_INTERPRETATION_ENGINE.domains(text)["measurements"]
        if float(x["score"]) >= 0.20
    }


def _capability_scores(text: str) -> dict[str, float]:
    return QUANTUM_INTERPRETATION_ENGINE.measure(text)["capability_scores"]


def measure_representation_evidence(text: str) -> list[dict[str, Any]]:
    return [
        SemanticEvidence(x["type"], float(x["score"]), "quantum_matrix").as_dict()
        for x in QUANTUM_INTERPRETATION_ENGINE.representations(text)["measurements"]
    ]


def detect_representation_candidates(text: str):
    return [
        x["label"] for x in measure_representation_evidence(text)
        if float(x["score"]) >= 0.45
    ]


def semantic_evidence_math(text: str) -> float:
    return QUANTUM_INTERPRETATION_ENGINE.measure(text)["representation_scores"].get("formula", 0.0)


def semantic_evidence_renderer(text: str) -> float:
    return max(
        QUANTUM_INTERPRETATION_ENGINE.measure(text)["representation_scores"].values(),
        default=0.0,
    )


def semantic_evidence_image(text: str) -> float:
    return QUANTUM_INTERPRETATION_ENGINE.measure(text)["representation_scores"].get("image", 0.0)


def semantic_evidence_exploration(text: str) -> float:
    return _capability_scores(text).get("exploration", 0.0)


def semantic_evidence_continuation(text: str, previous_assistant: str = "") -> float:
    return QUANTUM_INTERPRETATION_ENGINE.dialogue(
        text, previous_assistant=previous_assistant
    )["dialogue"]["continuation_score"]


def semantic_evidence_web(text: str) -> float:
    return _capability_scores(text).get("web", 0.0)


def semantic_evidence_code(text: str) -> float:
    return _capability_scores(text).get("code", 0.0)


def semantic_evidence_information(text: str) -> float:
    return _capability_scores(text).get("information", 0.0)


def detect_discussion_mode(text: str) -> float:
    return _capability_scores(text).get("discussion", 0.0)


def detect_space_discussion(text: str) -> float:
    return _capability_scores(text).get("space", 0.0)


def detect_lightweight_visual(text: str) -> float:
    scores = QUANTUM_INTERPRETATION_ENGINE.measure(text)["representation_scores"]
    return max(scores.get("image", 0.0), scores.get("diagram", 0.0), scores.get("graph", 0.0))


def detect_scene_type(text: str, cognition=None):
    cognition = cognition if isinstance(cognition, dict) else {}
    required = [str(x).lower() for x in cognition.get("required_representations", ()) or ()]
    return required[0] if required else QUANTUM_INTERPRETATION_ENGINE.measure(text)["scene_matrix"]["best_scene"]


def _is_micro_social_turn(text: Any) -> bool:
    p = QUANTUM_INTERPRETATION_ENGINE.measure(normalize_text(text))
    return bool(p["fast_social"] and len(normalize_text(text).split()) <= 24)


def _semantic_identity_request(text: Any) -> bool:
    return bool(QUANTUM_INTERPRETATION_ENGINE.measure(normalize_text(text))["identity_request"])


def _dialogue_signal_contract(
    text: str, history: list, state: dict, semantic: dict, cognition: dict | None = None,
    precomputed_profile: dict[str, Any] | None = None,
):
    cognition = cognition if isinstance(cognition, dict) else {}
    state = state if isinstance(state, dict) else {}
    semantic = semantic if isinstance(semantic, dict) else {}
    previous_assistant, previous_user, reply_to = QUANTUM_INTERPRETATION_ENGINE._history(history)
    active_goal = normalize_text(
        state.get("active_goal") or state.get("current_goal")
        or semantic.get("active_goal") or cognition.get("active_goal")
    )
    active_topic = normalize_text(
        state.get("active_topic") or state.get("current_topic")
        or semantic.get("current_topic") or cognition.get("active_topic")
    )
    measured = QUANTUM_INTERPRETATION_ENGINE.dialogue(
        text, previous_assistant=previous_assistant, previous_user=previous_user,
        active_goal=active_goal, active_topic=active_topic,
    )
    d = measured["dialogue"]
    continuation = bool(
        previous_assistant and (
            d["label"] in {"continuation", "reformulation", "correction", "reference", "affirmation", "rejection"}
            or d["continuation_score"] >= 0.72
        )
    )
    return {
        "dialog_act": d["label"],
        "current_request": text,
        "continuation": continuation,
        "reference_to_previous": bool(previous_assistant and d["reference_score"] >= 0.60),
        "previous_april_turn": previous_assistant,
        "previous_user_turn": previous_user,
        "reply_to": reply_to,
        "active_goal": active_goal,
        "active_topic": active_topic,
        "topic_score": d["topic_score"],
        "goal_score": d["goal_score"],
        "continuation_score": d["continuation_score"],
        "reference_score": d["reference_score"],
        "topic_shift": bool(active_topic and not continuation and d["topic_score"] < 0.35),
        "history_available": bool(history),
        "turn_count": len(history),
        "semantic_measurement": measured,
        "confidence": d["confidence"],
        "decision_owner": DECISION_OWNER,
        "evidence_only": True,
        "canonical": True,
    }


def _semantic_context_packet(
    text: str, history: list, state: dict, semantic: dict, cognition: dict
) -> dict[str, Any]:
    result = QUANTUM_INTERPRETATION_ENGINE.interpret(
        text, cognition=cognition, semantic=semantic, history=history, state=state
    )
    return result.get("quantum_interpretation_field", {})


def _base_interpret_request(
    text, cognition=None, semantic=None, history=None, state=None
):
    return interpret_request(text, cognition, semantic, history, state)


# ---------------------------------------------------------------------------
# Canonical interpretation entrypoint
# ---------------------------------------------------------------------------

def interpret_request(
    text, cognition=None, semantic=None, history=None, state=None
):
    return QUANTUM_INTERPRETATION_ENGINE.interpret(
        text,
        cognition=cognition,
        semantic=semantic,
        history=history,
        state=state,
    )


# ---------------------------------------------------------------------------
# Compatibility builders retained as thin views, not separate engines.
# ---------------------------------------------------------------------------

def build_semantic_dialog_profile(
    text, cognition=None, semantic=None, assistant_response=None,
    dialogue_history=None, vision_context=None
):
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
        "profile_version": "quantum_matrix_v1",
    }


def build_scene_construction_profile(semantic_profile):
    return {
        "requires_scene_builder": False,
        "scene_type": "dialogue",
        "dialogue_mode": "semantic_unified",
        "context_source": "quantum_matrix",
        "decision_owner": DECISION_OWNER,
        "profile_version": "quantum_matrix_v1",
    }


def build_scene_artifact_contract(semantic_profile, scene_profile):
    return {
        "contract": "scene_artifact",
        "transport": TRANSPORT_NAME,
        "semantic_profile": semantic_profile or {},
        "scene_profile": scene_profile or {},
        "representation": "processor_decides",
        "profile_version": "quantum_matrix_v1",
    }


def build_unified_scene_context(
    semantic_profile, scene_profile, artifact_contract,
    voice_context=None, vision_context=None, gallery_context=None, file_context=None,
    assistant_response=None, dialogue_history=None, memory_state=None
):
    return {
        "semantic_profile": semantic_profile or {},
        "scene_profile": scene_profile or {},
        "artifact_contract": artifact_contract or {},
        "voice_context": voice_context or {},
        "vision_context": vision_context or {},
        "gallery_context": gallery_context or {},
        "file_context": file_context or {},
        "assistant_response": assistant_response,
        "dialogue_history": dialogue_history or [],
        "active_goal": (semantic_profile or {}).get("active_goal"),
        "active_scene": (scene_profile or {}).get("scene_type", "dialogue"),
        "memory_state": memory_state or {},
        "continuity_state": {
            "single_route": True,
            "transport": TRANSPORT_NAME,
            "scene_contract": "canonical",
        },
        "profile_version": "quantum_matrix_v1",
    }


def build_scene_execution_plan(
    semantic_profile, scene_profile, artifact_contract, unified_scene_context=None
):
    context = unified_scene_context or build_unified_scene_context(
        semantic_profile, scene_profile, artifact_contract
    )
    return {
        "transport": TRANSPORT_NAME,
        "scene_contract": "canonical",
        "scene_context": context,
        "scene_type": (scene_profile or {}).get("scene_type", "dialogue"),
        "representation": "processor_decides",
        "execution_mode": "single_quantum_matrix_pipeline",
        "decision_owner": DECISION_OWNER,
        "profile_version": "quantum_matrix_v1",
    }


def build_unified_interpretation_state(scene_context, processor_state=None):
    return {
        "transport": TRANSPORT_NAME,
        "scene_context": scene_context or {},
        "processor_state": processor_state or {},
        "dialogue_vector": (scene_context or {}).get("dialogue_history", []),
        "assistant_response": (scene_context or {}).get("assistant_response"),
        "voice_context": (scene_context or {}).get("voice_context", {}),
        "vision_context": (scene_context or {}).get("vision_context", {}),
        "gallery_context": (scene_context or {}).get("gallery_context", {}),
        "file_context": (scene_context or {}).get("file_context", {}),
        "active_goal": (scene_context or {}).get("active_goal"),
        "active_scene": (scene_context or {}).get("active_scene"),
        "executor_mode": "single_scene_contract",
        "profile_version": "quantum_matrix_v1",
    }


def build_semantic_processor_state(interpretation_state, execution_plan=None):
    state = interpretation_state or {}
    return {
        "transport": TRANSPORT_NAME,
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
        "profile_version": "quantum_matrix_v1",
    }


def build_dialogue_understanding_core(processor_state, executor_state=None):
    inputs = (processor_state or {}).get("semantic_inputs", {})
    return {
        "transport": TRANSPORT_NAME,
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
        "profile_version": "quantum_matrix_v1",
    }


def optimize_dialogue_understanding(dialogue_core):
    return {
        "transport": TRANSPORT_NAME,
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
        "profile_version": "quantum_matrix_v1",
    }


def build_semantic_interpretation_contract(dialogue_optimization):
    return {
        "transport": TRANSPORT_NAME,
        "semantic_contract": {
            "mode": "canonical_semantic",
            "single_scene": True,
            "single_dialogue": True,
            "single_processor": True,
            "single_executor": True,
        },
        "dialogue_optimization": dialogue_optimization or {},
        "reasoning_policy": {
            "current_request_authoritative": True,
            "multimodal_fusion": True,
            "multi_evidence": True,
            "trigger_independent": True,
            "scene_continuity": True,
        },
        "profile_version": "quantum_matrix_v1",
    }


def build_canonical_semantic_runtime(semantic_contract, processor_state, dialogue_core):
    dialogue = (dialogue_core or {}).get("dialogue_understanding", {})
    return {
        "transport": TRANSPORT_NAME,
        "scene": dialogue.get("scene_understanding", {}),
        "dialogue": dialogue,
        "processor": processor_state or {},
        "reasoning_policy": (semantic_contract or {}).get("reasoning_policy", {}),
        "continuity_vector": {
            "history": dialogue.get("dialogue_history", []),
            "assistant": dialogue.get("assistant_response"),
            "goal": dialogue.get("scene_understanding", {}).get("active_goal"),
        },
        "compatibility": {
            "enabled": False,
            "trigger_execution": False,
            "keyword_matching": False,
        },
        "profile_version": "quantum_matrix_v1",
    }


def fuse_semantic_inputs(runtime_state):
    runtime_state = runtime_state or {}
    inputs = dict(runtime_state.get("input_sources", {}))
    continuity = runtime_state.get("continuity_vector", {})
    return {
        "transport": TRANSPORT_NAME,
        "scene": runtime_state.get("scene", {}),
        "goal": continuity.get("goal"),
        "history": continuity.get("history", []),
        "assistant_response": continuity.get("assistant"),
        "modalities": {k: inputs.get(k) for k in ("text", "voice", "images", "gallery", "files")},
        "semantic_state": {
            "single_route": True,
            "multimodal_fusion": True,
            "legacy_trigger_enabled": False,
            "context_complete": True,
        },
        "available_modalities": [k for k, v in inputs.items() if v not in (None, {}, [], "")],
        "profile_version": "quantum_matrix_v1",
    }


def build_processor_execution_context(runtime_state):
    fused = fuse_semantic_inputs(runtime_state or {})
    return {
        "transport": TRANSPORT_NAME,
        "semantic_context": fused,
        "executor_context": fused,
        "processor_context": fused,
        "decision_owner": DECISION_OWNER,
        "profile_version": "quantum_matrix_v1",
    }


SEMANTIC_EVIDENCE_PRIORITY = (
    "current_request", "active_goal", "dialogue_history",
    "voice_context", "vision_context", "gallery_context",
    "file_context", "semantic_profile",
)
LEGACY_TRIGGER_FLAGS = ()
CANONICAL_SEMANTIC_RUNTIME = {
    "transport": TRANSPORT_NAME,
    "reasoning": "quantum_matrix",
    "legacy_trigger_execution": False,
    "single_scene": True,
    "single_processor": True,
    "single_executor": True,
}
SEMANTIC_INTERPRETATION_CORE = {
    "decision_source": DECISION_OWNER,
    "routing": "processor_owned",
    "legacy_mode": "isolated",
    "scene_contract": "artifact_first",
    "executor_contract": "advisory_only",
    "history_model": "evidence_based",
    "confidence_policy": "multi_evidence",
}
SEMANTIC_PIPELINE = INTERPRETATION_ROUTE


# ============================================================================
# DIALOGUE-FIRST RUNTIME — INTEGRATED INTO THIS EXISTING FILE
# ============================================================================
# There is intentionally NO blocks.dialogue_runtime module.  This code lives
# in the production interpretation layer so the existing project topology is
# unchanged. Bigunoks are evidence probes only.

_df_version = "april_integrated_dialogue_first_v2_dynamic_branch_graph"
_df_provider_plan_version = "april_provider_handoff_v1"

_df_structured = {"image", "gallery", "diagram", "graph", "table", "formula", "code", "link"}
_df_confirm = {"да", "ага", "верно", "правильно", "точно", "именно", "хорошо", "угу"}
_df_reject = {"нет", "не", "неверно", "неправильно", "неа"}
_df_short_filler = {"ну", "так", "теперь", "дальше", "и", "а", "это", "понятно"}
_df_stop = {
    "и", "а", "но", "да", "нет", "ну", "так", "же", "ли", "же", "я", "ты", "мне", "тебе",
    "меня", "тебя", "мы", "вы", "они", "он", "она", "оно", "это", "этот", "эта", "эту", "тот",
    "что", "как", "почему", "зачем", "какой", "какая", "какое", "какие", "сколько", "можешь",
    "можешь", "можно", "хочу", "хотел", "хотела", "нужно", "надо", "давай", "расскажи", "скажи",
    "объясни", "покажи", "сделай", "создай", "построй", "проверь", "предложить", "предлагаю", "игру",
    "в", "на", "по", "про", "об", "о", "к", "у", "из", "с", "со", "для", "уже", "ещё", "еще",
}

_df_new_topic_markers = (
    "новая тема", "другая тема", "отдельная тема", "сменим тему", "перейдем к", "перейдём к",
    "давай теперь про", "давай теперь о", "а теперь про", "а теперь о", "теперь поговорим о",
    "кстати про", "кстати о", "хочу обсудить другую тему",
    "хочу предложить тебе игру", "хочу предложить игру", "давай сыграем",
    "начнем игру", "начнём игру", "давай поиграем",
)
_df_recall_markers = (
    "вернемся к", "вернёмся к", "вернись к", "вернись к теме", "вернись к разговору",
    "вспомни", "помнишь", "что мы обсуждали", "о чем мы говорили", "о чём мы говорили",
    "что я спрашивал", "что я спрашивала", "что я просил", "что я просила",
)
_df_memory_scope_terms = {
    "памят", "контекст", "диалог", "диалоги", "разговор", "разговоры",
    "истори", "обсужд", "сесс", "ветк", "последовательн",
}
_df_memory_scope_actions = {
    "проверь", "проверить", "посмотри", "посмотреть", "покажи", "показать",
    "расскажи", "рассказать", "выдай", "выдать", "перечисли", "перечислить",
    "вспомни", "вспомнить", "сориентируйся", "сориентироваться",
}
_df_deictic = re.compile(r"\b(?:это|этот|эта|эту|этого|этой|этим|он|она|оно|они|его|ее|её|тот|та|те|там|здесь|выше|ниже|дальше|следующ(?:ий|ая|ее|ие|его|ую|им|ими)?|свой|свою|своего)\b", re.I)
_df_explicit_result = (
    "как ты угадал", "как ты угадала", "почему ты угадал", "почему ты угадала",
    "правильный ответ", "объясни свой ответ", "объясни твой ответ", "объясни свой правильный ответ",
    "объясни твой правильный ответ", "объясни мой ответ", "твои вычисления", "по какой формуле",
    "какую формулу ты применил", "какую формулу ты применил", "о чем я просил", "о чём я просил",
    "что ты должна была", "что ты должен был",
)

_df_render_patterns = (
    ("image", r"(?:картинк|изображени|нарисуй|изобрази|сгенерируй|портрет|фото|рисунок)"),
    ("diagram", r"(?:схем|блок[- ]?схем)"),
    ("graph", r"(?:график|графика|кривую|кривая|диаграмм)"),
    ("table", r"(?:таблиц|табличк)"),
    ("formula", r"(?:формул|уравнен|математическ)"),
    ("code", r"(?:код|python|пайтон|скрипт)"),
    ("link", r"(?:ссылк|url|link)"),
)

_df_commands = (
    "расскажи", "скажи", "объясни", "покажи", "нарисуй", "изобрази", "создай", "сгенерируй",
    "сделай", "построй", "проверь", "опиши", "сравни", "найди", "выведи", "подскажи", "дай",
    "предложи", "разработай", "исправь", "сформулируй", "составь", "перепиши", "переделай", "угадай",
    "отгадай", "разгадай",
)


def _df_text(value: Any, limit: int = 2400) -> str:
    s = str(value or "").strip()
    return s[:limit]


def _df_low(value: Any) -> str:
    return re.sub(r"\s+", " ", _df_text(value).lower()).strip()


def _df_tokens(value: Any) -> list[str]:
    words = re.findall(r"[a-zа-яё0-9][a-zа-яё0-9_-]{2,}", _df_low(value))
    return [w for w in words if w not in _df_stop]


def _df_overlap(a: Any, b: Any) -> float:
    aa, bb = set(_df_tokens(a)), set(_df_tokens(b))
    if not aa or not bb:
        return 0.0
    return round(len(aa & bb) / max(1, min(len(aa), len(bb))), 6)


def _df_explicit_new(text: str, active_topic: str = "", active_entity: str = "") -> bool:
    low = _df_low(text)
    if any(m in low for m in _df_new_topic_markers):
        return True
    # Game/task handoff is a real topic boundary, but the previous branch is kept
    # in the branch index and remains recallable.
    if re.search(r"\b(?:хочу\s+предложить(?:\s+тебе)?\s+игр(?:у|а)|давай\s+(?:сыграем|поиграем)|начн(?:ем|ём)\s+игр(?:у|а))\b", low):
        return True
    # A command naming a different concrete subject opens a branch.  A pronoun
    # such as "это/этом" is deliberately excluded: it is a live-dialogue reference.
    m = re.match(r"^(?:а\s+)?(?:расскажи|скажи|объясни|покажи|проверь|найди|сравни)\b.*?\b(?:про|об|о)\s+(.+)$", low)
    if m:
        subject = _df_normalize_subject(m.group(1).strip(" .,!?:;—-"))
        if subject and not _df_deictic.search(subject):
            current = {_df_low(active_topic), _df_low(active_entity)} - {""}
            if _df_low(subject) not in current and not any(_df_low(c) and _df_low(c) in _df_low(subject) for c in current):
                return True
    return False


def _df_memory_scope_request(text: str) -> bool:
    """Detect a request to inspect the active conversation memory itself.

    This is semantic evidence, not a route selector: relation handling remains
    responsible for deciding RECALL, and StateManager remains responsible for
    materializing the authenticated 12-hour window.
    """
    low = _df_low(text)
    if any(marker in low for marker in _df_recall_markers):
        return True
    term_hits = sum(1 for term in _df_memory_scope_terms if term in low)
    action_hits = sum(1 for verb in _df_memory_scope_actions if re.search(rf"\b{re.escape(verb)}\b", low))
    explicit_window = bool(re.search(r"\b(?:двенадцат|12)[- ]?(?:час|ч)\w*\b", low))
    return bool((term_hits >= 2 and action_hits >= 1) or (explicit_window and term_hits >= 1 and action_hits >= 1))


def _df_explicit_recall(text: str) -> bool:
    return _df_memory_scope_request(text)


def _df_extract_subject(text: str) -> str:
    """Extract the semantic operand without inventing a topic from sentence tails."""
    value = _df_text(text, 1000)
    if not value:
        return ""
    low = _df_low(value)

    quoted = re.search(r'[«"]([^»"]{2,180})[»"]', value)
    if quoted:
        return _df_text(quoted.group(1), 180)

    question_patterns = (
        r"^(?:продолжаем|продолжим|дальше|теперь)\s+что\s+такое\s+(.+)$",
        r"^что\s+такое\s+(.+)$",
        r"^(?:продолжаем|продолжим|дальше|теперь)\s+кто\s+такой\s+(.+)$",
        r"^кто\s+такой\s+(.+)$",
        r"^кто\s+(?:такая|такое|такие)\s+(.+)$",
        r"^кто\s+это\s+(.+)$",
    )
    for pattern in question_patterns:
        match = re.match(pattern, low, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip(" .,!?:;—-\n")
            if candidate:
                return _df_text(candidate, 180)

    # Generic request frames are used only to locate the current operand. They
    # never decide relation/routing on their own.
    command_heads = (
        r"назови", r"скажи", r"дай", r"выдай", r"укажи", r"выбери",
        r"напиши", r"приведи", r"расскажи", r"объясни", r"покажи",
        r"проверь", r"найди", r"опиши", r"создай", r"построй", r"рассчитай",
        r"посчитай", r"ответь", r"определи",
    )
    head = "(?:" + "|".join(command_heads) + ")"
    match = re.match(rf"^(?:а\s+)?{head}\s+(.+)$", low, re.IGNORECASE)
    if match:
        candidate = match.group(1).strip(" .,!?:;—-\n")
        candidate = re.sub(
            r"\s+(?:прописью|словами|подробно|кратко|пожалуйста|сейчас)$",
            "",
            candidate,
            flags=re.IGNORECASE,
        ).strip(" .,!?:;—-\n")
        if candidate:
            return _df_text(candidate, 180)

    about = re.search(r"\b(?:про|об|о|насчет|насчёт|касаемо)\s+(.{2,180})", low)
    if about:
        candidate = about.group(1).strip(" .,!?:;—-\n")
        if candidate and candidate not in {"это", "этом", "этого", "него", "неё", "нее"}:
            return _df_text(candidate, 180)

    # Pure discourse/deictic heads are not semantic entities. They acquire
    # meaning from the live sequence only after relation resolution.
    reference_only = {
        "следующее", "следующий", "следующая", "следующее", "следующие",
        "дальше", "продолжай", "продолжить", "продолжение", "ещё", "еще",
        "теперь", "потом", "далее", "сейчас", "овечай", "отвечай",
    }
    if low.strip(" .,!?:;—-\n") in reference_only:
        return ""

    # Proper-name mentions are semantic entities, not hardcoded entity lists.
    ignored = {
        "теперь", "сейчас", "потом", "пожалуйста", "апрель", "я", "ты", "мы", "вы",
        "назови", "скажи", "расскажи", "кто", "что", "почему", "зачем", "как", "где",
        "когда", "сколько", "какой", "какая", "какое", "какие", "можешь", "можно",
        "нужно", "надо", "давай",
    }
    proper = re.findall(r"\b[А-ЯЁ][а-яё-]{2,}(?:\s+[А-ЯЁ][а-яё-]{2,}){0,2}\b", value)
    for candidate in reversed(proper):
        parts = candidate.split()
        if parts and parts[0].lower() not in ignored:
            return _df_text(candidate, 180)

    return ""

def _df_normalize_subject(value: str) -> str:
    low = _df_low(value)
    aliases = {
        "пончики": "пончик",
        "пончиков": "пончик",
        "пончика": "пончик",
        "илона маска": "илон маск",
        "яблоки": "яблоко",
        "яблок": "яблоко",
        "угадайки": "игра в угадайки",
        "угадайка": "игра в угадайки",
    }
    return aliases.get(low, _df_text(value, 180))


def _df_extract_previous(history: list[Any], state: dict[str, Any]) -> tuple[str, str]:
    """Return the real immediately preceding USER↔APRIL pair for this session.

    Task-local state is a secondary source. The parent authenticated sequence is
    authoritative for discourse order, so a task switch cannot make the previous
    turn disappear from interpretation.
    """
    seq = state.get("active_dialogue_sequence") if isinstance(state.get("active_dialogue_sequence"), dict) else {}
    sequence_id = _df_text(seq.get("sequence_id"), 120)
    user_id = _df_text(state.get("user_id") or (state.get("memory_scope") or {}).get("user_id"), 120)
    conversation_id = _df_text(state.get("conversation_id") or (state.get("memory_scope") or {}).get("conversation_id"), 160)

    candidates: list[tuple[int, float, str, str]] = []
    timeline = state.get("memory_timeline") if isinstance(state.get("memory_timeline"), dict) else {}
    now = time.time()
    for day in timeline.values():
        if not isinstance(day, dict):
            continue
        for raw in day.get("dialog_pairs", []):
            if not isinstance(raw, dict):
                continue
            if sequence_id and _df_text(raw.get("sequence_id"), 120) != sequence_id:
                continue
            if user_id and _df_text(raw.get("user_id"), 120) not in {"", user_id}:
                continue
            if conversation_id and _df_text(raw.get("conversation_id"), 160) not in {"", conversation_id}:
                continue
            try:
                created_at = float(raw.get("created_at") or raw.get("timestamp") or 0.0)
            except (TypeError, ValueError):
                created_at = 0.0
            if created_at and now - created_at >= USER_CONTENT_RETENTION_SECONDS:
                continue
            try:
                turn_index = int(raw.get("sequence_turn_index") or 0)
            except (TypeError, ValueError):
                turn_index = 0
            user = _df_text(raw.get("user_request") or raw.get("user_meaning") or raw.get("user"), 1200)
            april = _df_text(raw.get("april_answer") or raw.get("april_meaning") or raw.get("answer") or raw.get("answer_summary"), 2200)
            if user or april:
                candidates.append((turn_index, created_at, user, april))

    if candidates:
        candidates.sort(key=lambda item: (item[0], item[1]))
        _turn, _created, user, april = candidates[-1]
        if user or april:
            return user, april

    # Sequence head is the next-best source when pair archival was delayed.
    seq_user = _df_text(seq.get("last_user_request") or state.get("last_user_turn"), 1200)
    seq_april = _df_text(seq.get("last_april_answer") or state.get("last_april_turn"), 2200)
    if seq_user or seq_april:
        return seq_user, seq_april

    # Only now use task-local/legacy context as a compatibility fallback.
    active_context = state.get("active_dialogue_context") if isinstance(state.get("active_dialogue_context"), dict) else {}
    last_result = active_context.get("last_completed_result") if isinstance(active_context.get("last_completed_result"), dict) else {}
    if last_result:
        return (
            _df_text(last_result.get("user_request") or last_result.get("current_request"), 1200),
            _df_text(last_result.get("assistant_answer") or last_result.get("april_answer"), 2200),
        )

    prev_user = ""
    prev_april = ""
    for item in reversed(history if isinstance(history, list) else []):
        if not isinstance(item, dict):
            continue
        user = item.get("user") if isinstance(item.get("user"), dict) else {}
        apr = item.get("april") if isinstance(item.get("april"), dict) else {}
        if not prev_user:
            prev_user = _df_text(
                user.get("text") or user.get("content") or item.get("text")
                or (item.get("role") == "user" and item.get("content")),
                1200,
            )
        if not prev_april:
            prev_april = _df_text(
                apr.get("answer") or apr.get("content") or item.get("answer")
                or (item.get("role") in {"assistant", "april", "bot"} and item.get("content")),
                2200,
            )
        if prev_user and prev_april:
            break
    return prev_user, prev_april

def _df_active_sequence_digest(
    state: dict[str, Any],
    history: list[Any],
    sequence_id: str,
    *,
    limit: int = 8,
    task_id: str = "",
) -> dict[str, Any]:
    """Build the semantic digest of the authenticated 12-hour parent sequence.

    The parent sequence contains multiple topic/task branches. Task-local state
    remains available separately, but it is never allowed to hide the sequence
    trajectory from Interpretation.
    """
    seq = state.get("active_dialogue_sequence") if isinstance(state.get("active_dialogue_sequence"), dict) else {}
    sid = _df_text(sequence_id or seq.get("sequence_id"), 120)
    tid = _df_text(task_id or seq.get("task_id") or state.get("active_dialogue_task_id"), 100)
    conversation_id = _df_text(state.get("conversation_id") or (state.get("memory_scope") or {}).get("conversation_id"), 160)
    user_id = _df_text(state.get("user_id") or (state.get("memory_scope") or {}).get("user_id"), 120)

    registry = seq.get("task_registry") if isinstance(seq.get("task_registry"), dict) else {}
    top_registry = state.get("dialogue_task_registry") if isinstance(state.get("dialogue_task_registry"), dict) else {}
    task_record = deepcopy(registry.get(tid) or top_registry.get(tid) or {}) if tid else {}

    rows: list[dict[str, Any]] = []
    timeline = state.get("memory_timeline") if isinstance(state.get("memory_timeline"), dict) else {}
    now = time.time()
    for day in timeline.values():
        if not isinstance(day, dict):
            continue
        for raw in day.get("dialog_pairs", []):
            if not isinstance(raw, dict):
                continue
            raw_sid = _df_text(raw.get("sequence_id"), 120)
            if not sid or raw_sid != sid:
                continue
            raw_user_id = _df_text(raw.get("user_id"), 120)
            if user_id and raw_user_id and raw_user_id != user_id:
                continue
            raw_conversation = _df_text(raw.get("conversation_id"), 160)
            if conversation_id and raw_conversation and raw_conversation != conversation_id:
                continue
            try:
                created_at = float(raw.get("created_at") or raw.get("timestamp") or 0.0)
            except (TypeError, ValueError):
                created_at = 0.0
            if created_at and now - created_at >= USER_CONTENT_RETENTION_SECONDS:
                continue
            try:
                turn_index = int(raw.get("sequence_turn_index") or 0)
            except (TypeError, ValueError):
                turn_index = 0
            rows.append({
                "sequence_turn_index": turn_index,
                "task_response_number": int(raw.get("task_response_number") or raw.get("response_count") or 0),
                "task_id": _df_text(raw.get("task_id"), 100),
                "created_at": created_at,
                "topic": _df_text(raw.get("sequence_topic") or raw.get("topic") or raw.get("canonical_topic"), 220),
                "user": _df_text(raw.get("user_request") or raw.get("user_meaning") or raw.get("user"), 260),
                "april": _df_text(raw.get("april_answer") or raw.get("april_meaning") or raw.get("answer") or raw.get("answer_summary"), 420),
                "relation": _df_text(raw.get("dialogue_relation") or raw.get("relation"), 40).upper(),
            })

    # Legacy recovery: history can still contain the current sequence even when
    # the durable pair archive was not populated by an older writer.
    if not rows and isinstance(history, list) and sid:
        for item in history:
            if not isinstance(item, dict):
                continue
            item_sid = _df_text(item.get("sequence_id") or item.get("dialogue_sequence_id"), 120)
            if item_sid and item_sid != sid:
                continue
            user = item.get("user") if isinstance(item.get("user"), dict) else {}
            april = item.get("april") if isinstance(item.get("april"), dict) else {}
            user_text = _df_text(user.get("text") or user.get("content") or item.get("user_request") or item.get("content"), 260)
            april_text = _df_text(april.get("answer") or april.get("content") or item.get("april_answer") or item.get("answer"), 420)
            if user_text or april_text:
                rows.append({
                    "sequence_turn_index": int(item.get("sequence_turn_index") or item.get("turn_id") or len(rows) + 1),
                    "task_response_number": int(item.get("task_response_number") or 0),
                    "task_id": _df_text(item.get("task_id"), 100),
                    "created_at": float(item.get("created_at") or 0.0),
                    "topic": _df_text(item.get("sequence_topic") or item.get("topic"), 220),
                    "user": user_text,
                    "april": april_text,
                    "relation": _df_text(item.get("dialogue_relation") or item.get("relation"), 40).upper(),
                })

    rows.sort(key=lambda item: (item.get("sequence_turn_index", 0), item.get("created_at", 0.0)))
    unique_rows = []
    seen = set()
    for row in rows:
        sig = (row.get("task_id"), row.get("sequence_turn_index"), row.get("user"), row.get("april"))
        if sig in seen:
            continue
        seen.add(sig)
        unique_rows.append(row)
    rows = unique_rows

    task_rows = [row for row in rows if tid and str(row.get("task_id") or "") == tid]
    if not task_rows and isinstance(task_record.get("last_result"), dict):
        last = task_record["last_result"]
        task_rows = [{
            "sequence_turn_index": int(last.get("sequence_turn_index") or seq.get("turn_count") or 0),
            "task_response_number": int(last.get("task_response_number") or task_record.get("response_count") or 0),
            "task_id": tid,
            "created_at": float(last.get("created_at") or task_record.get("last_turn_at") or 0.0),
            "topic": _df_text(task_record.get("topic"), 220),
            "user": _df_text(last.get("user_request") or task_record.get("last_user_request"), 260),
            "april": _df_text(last.get("april_answer") or task_record.get("last_april_answer"), 420),
            "relation": _df_text(last.get("relation") or "CONTINUE", 40).upper(),
        }]

    def compact(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "turn": int(row.get("sequence_turn_index") or 0),
            "task_response_number": int(row.get("task_response_number") or 0),
            "task_id": _df_text(row.get("task_id"), 100),
            "user": _df_text(row.get("user"), 220),
            "april": _df_text(row.get("april"), 360),
            "topic": _df_text(row.get("topic"), 180),
            "relation": _df_text(row.get("relation"), 40),
        }

    recent = rows[-max(1, min(int(limit or 8), 12)):]
    recent_task = task_rows[-max(1, min(int(limit or 8), 12)):]
    topics: list[str] = []
    for row in rows:
        topic = _df_text(row.get("topic"), 220)
        if topic and topic not in topics:
            topics.append(topic)

    last_row = rows[-1] if rows else {}
    previous_row = rows[-2] if len(rows) >= 2 else {}
    root_topic = topics[0] if topics else _df_text(seq.get("topic"), 220)
    latest_topic = _df_text(last_row.get("topic"), 220)
    task_topic = _df_text(
        task_record.get("topic")
        or (task_rows[-1].get("topic") if task_rows else ""),
        220,
    )
    task_entity_raw = _df_text(task_record.get("entity") or task_record.get("active_entity"), 180)
    task_entity = "" if _df_low(task_entity_raw) in {
        "если", "это", "такое", "такой", "такие", "кто", "что", "где",
        "когда", "почему", "как", "пронумеруй", "выдай", "проверь", "так",
        "следующее", "дальше", "отвечай", "овечай",
    } else task_entity_raw
    task_result = deepcopy(task_record.get("last_result") or {})

    task_summaries: list[dict[str, Any]] = []
    merged_tasks: dict[str, Any] = {}
    if isinstance(top_registry, dict):
        merged_tasks.update(top_registry)
    if isinstance(registry, dict):
        merged_tasks.update(registry)
    for raw_tid, raw_task in merged_tasks.items():
        if not isinstance(raw_task, dict):
            continue
        if str(raw_task.get("sequence_id") or sid) != sid:
            continue
        tid_value = _df_text(raw_task.get("task_id") or raw_tid, 100)
        task_topic_value = _df_text(raw_task.get("topic"), 180)
        if not task_topic_value:
            matching = [row for row in rows if str(row.get("task_id") or "") == tid_value]
            task_topic_value = _df_text(matching[-1].get("topic") if matching else "", 180)
        if task_topic_value:
            task_summaries.append({
                "task_id": tid_value,
                "topic": task_topic_value,
                "turn_count": int(raw_task.get("response_count") or raw_task.get("turn_count") or 0),
                "status": _df_text(raw_task.get("status") or "open", 40),
            })
    task_summaries.sort(key=lambda item: (str(item.get("topic") or ""), str(item.get("task_id") or "")))
    task_basis = deepcopy(task_record.get("last_answer_basis") or task_record.get("answer_basis") or {})
    task_rules = deepcopy(task_record.get("dialogue_rules") or {})
    task_response_count = int(task_record.get("response_count") or task_record.get("task_response_count") or 0)

    return {
        "version": "active_sequence_digest_v5_12h_sequence_window",
        "source": "authenticated_active_sequence",
        "sequence_id": sid,
        "task_id": tid,
        "conversation_id": conversation_id,
        "user_id": user_id,
        "dialogue_window_hours": 12,
        "history_scope": "authenticated_12h_dialogue_sequence",
        "sequence_turn_count": max(int(seq.get("turn_count") or 0), int((last_row or {}).get("sequence_turn_index") or 0)),
        "turn_count": max(int(seq.get("turn_count") or 0), int((last_row or {}).get("sequence_turn_index") or 0)),
        "window_record_count": len(rows),
        "task_turn_count": len(task_rows),
        "task_response_count": task_response_count,
        "root_topic": root_topic,
        "current_topic": _df_text(latest_topic or (topics[-1] if topics else "") or seq.get("topic") or root_topic, 220),
        "current_task_topic": task_topic,
        "current_focus": task_entity or _df_text((last_row or {}).get("user"), 220) or _df_text(seq.get("active_entity"), 180),
        "last_user": _df_text((last_row or {}).get("user") or seq.get("last_user_request"), 260),
        "last_april": _df_text((last_row or {}).get("april") or seq.get("last_april_answer"), 420),
        "previous_user": _df_text((previous_row or {}).get("user"), 260),
        "previous_april": _df_text((previous_row or {}).get("april"), 420),
        "last_result": task_result,
        "answer_basis": task_basis,
        "dialogue_rules": task_rules,
        "topic_path": topics[-12:],
        "recent_trajectory": [compact(x) for x in recent if x.get("user") or x.get("april")],
        "task_trajectory": [compact(x) for x in recent_task if x.get("user") or x.get("april")],
        "task_summaries": task_summaries[-12:],
        "coverage": "authenticated_sequence_window",
        "window_complete": bool(sid),
        "other_branches_included": len({str(row.get("task_id") or "") for row in rows if row.get("task_id")}) > 1,
        "full_history_included": False,
    }

def _df_strong_topic_boundary(text: str) -> bool:
    """Detect discourse-level topic switching, not generic word triggers."""
    low = _df_low(text)
    strong = (
        "новая тема",
        "другая тема",
        "отдельная тема",
        "сменим тему",
        "перейдем к",
        "перейдём к",
        "давай теперь про",
        "давай теперь о",
        "а теперь про",
        "а теперь о",
        "теперь поговорим о",
        "хочу обсудить другую тему",
        "хочу поговорить о другой теме",
    )
    return any(marker in low for marker in strong)


def _df_is_self_contained_new_topic(
    text: str,
    semantic: dict[str, Any] | None,
    *,
    active_topic: str,
    active_entity: str,
    task_probe: dict[str, Any],
    sequence_digest: dict[str, Any],
) -> bool:
    """
    Identify a genuinely new subject without turning short replies into NEW.

    A lexical subject is insufficient. A new branch requires a reasonably
    self-contained utterance naming a different subject and not behaving like
    a response/reference to the active branch.
    """
    semantic = semantic if isinstance(semantic, dict) else {}
    words = _df_tokens(text)
    if _df_strong_topic_boundary(text):
        return True
    if len(words) < 2 and "?" not in text and "？" not in text:
        return False
    # An active task protects terse answers, but it must not prevent an explicit,
    # self-contained request to discuss a different subject. Pronouns such as
    # "его" inside a sentence that explicitly names a new subject are local
    # references and must not suppress the topic switch.
    subject = _df_normalize_subject(
        _df_text(semantic.get("explicit_subject"), 220)
    )
    if not subject:
        subject = _df_normalize_subject(_df_extract_subject(text))
    if not subject:
        return False
    if bool(_df_deictic.search(_df_low(text))) and subject in {"это", "это", "он", "она", "они", "его", "ее", "её", "них", "такое"}:
        return False

    branch_text = " ".join([
        _df_text(active_topic, 220),
        _df_text(active_entity, 220),
        _df_text(sequence_digest.get("root_topic"), 220),
        " ".join(_df_text(x, 180) for x in sequence_digest.get("topic_path", [])[-3:]),
        _df_text(sequence_digest.get("last_user"), 180),
        _df_text(sequence_digest.get("last_april"), 220),
    ])
    if not branch_text.strip():
        return True

    overlap_subject = _df_overlap(subject, branch_text)
    overlap_turn = max(
        _df_overlap(text, active_topic),
        _df_overlap(text, active_entity),
        _df_overlap(text, sequence_digest.get("last_user")),
        _df_overlap(text, sequence_digest.get("last_april")),
    )
    if max(overlap_subject, overlap_turn) >= 0.20:
        return False

    # Self-contained requests/questions with an explicitly named distinct
    # subject are the main non-explicit path to NEW.
    low = _df_low(text)
    command_shape = bool(re.match(
        r"^(?:а\s+)?(?:назови|дай|выдай|укажи|выбери|расскажи|скажи|объясни|покажи|проверь|найди|"
        r"сравни|напиши|создай|построй|опиши|рассчитай|посчитай|ответь|"
        r"кто\s+такой|что\s+такое|кто\s+это|какой(?:\s|$)|какая(?:\s|$)|"
        r"какое(?:\s|$)|какие(?:\s|$))",
        low,
    ))
    about_shape = bool(re.search(r"\b(?:про|об|о|насчет|насчёт|касаемо)\b", low))
    question_shape = "?" in text or "？" in text

    return bool(
        subject
        and (
            command_shape
            or about_shape
            or question_shape
        )
    )


def _df_active_task(state: dict[str, Any]) -> dict[str, Any]:
    sequence = state.get("active_dialogue_sequence") if isinstance(state.get("active_dialogue_sequence"), dict) else {}
    sequence_id = _df_text(sequence.get("sequence_id"), 80)
    active_task_id = _df_text(
        sequence.get("task_id")
        or state.get("active_dialogue_task_id")
        or "",
        100,
    )

    registry = sequence.get("task_registry") if isinstance(sequence.get("task_registry"), dict) else {}
    if not registry and isinstance(state.get("dialogue_task_registry"), dict):
        registry = state.get("dialogue_task_registry")
    if active_task_id and isinstance(registry.get(active_task_id), dict):
        task = deepcopy(registry[active_task_id])
        task["task_id"] = active_task_id
        task["sequence_id"] = sequence_id
        return task

    candidates = (
        sequence.get("active_task"),
        sequence.get("interactive_task_state"),
        sequence.get("open_task"),
        sequence.get("task_state"),
        state.get("interactive_task_state"),
        state.get("active_task"),
        state.get("april_active_task"),
    )
    for candidate in candidates:
        if not isinstance(candidate, dict) or not candidate:
            continue
        candidate_id = _df_text(candidate.get("task_id") or active_task_id, 100)
        candidate_seq = _df_text(candidate.get("sequence_id") or candidate.get("active_sequence_id"), 80)
        if sequence_id and candidate_seq and candidate_seq != sequence_id:
            continue
        if candidate.get("active") or candidate.get("task_id") or candidate.get("status") in {"open", "active", "suspended", "completed", "paused"}:
            result = deepcopy(candidate)
            if candidate_id:
                result["task_id"] = candidate_id
            if sequence_id:
                result["sequence_id"] = sequence_id
            return result
    return {}


def _df_topic_from_state(state: dict[str, Any]) -> str:
    seq = state.get("active_dialogue_sequence") if isinstance(state.get("active_dialogue_sequence"), dict) else {}
    active_ctx = state.get("active_dialogue_context") if isinstance(state.get("active_dialogue_context"), dict) else {}
    active_task = _df_active_task(state)
    for value in (
        active_task.get("topic"),
        active_ctx.get("topic"),
        seq.get("topic"),
        state.get("april_active_topic"),
        state.get("active_topic"),
        state.get("current_topic"),
    ):
        if _df_text(value):
            return _df_text(value, 220)
    return ""


def _df_entity_from_state(state: dict[str, Any]) -> str:
    active_task = _df_active_task(state)
    active_ctx = state.get("active_dialogue_context") if isinstance(state.get("active_dialogue_context"), dict) else {}
    for value in (
        active_task.get("entity"),
        active_task.get("active_entity"),
        active_ctx.get("active_entity"),
        state.get("april_active_entity"),
        state.get("active_entity"),
        state.get("current_object"),
        state.get("focus_state", {}).get("active_object") if isinstance(state.get("focus_state"), dict) else "",
    ):
        if _df_text(value) and _df_low(value) not in {
            "text", "вопрос", "ответ", "контекст", "контекст я же загадывал", "игра",
            "если", "то", "это", "этот", "эта", "такое", "такой", "такие",
            "кто", "что", "где", "когда", "почему", "как", "потом",
        }:
            return _df_text(value, 180)
    return ""


def _df_branch_index(state: dict[str, Any], active_seq: dict[str, Any], active_topic: str, active_entity: str) -> dict[str, Any]:
    old = state.get("dialogue_branch_index") if isinstance(state.get("dialogue_branch_index"), dict) else {}
    current_id = _df_text(active_seq.get("sequence_id"), 80)
    active_task_id = _df_text(
        active_seq.get("task_id")
        or state.get("active_dialogue_task_id")
        or "",
        100,
    )
    branches = []
    seen = set()
    for branch in list(old.get("branches") or []):
        if not isinstance(branch, dict):
            continue
        seq_id = _df_text(branch.get("sequence_id") or branch.get("branch_id"), 80)
        task_id = _df_text(branch.get("task_id"), 100)
        if not seq_id or (current_id and seq_id != current_id):
            continue
        key = task_id or branch.get("branch_id") or seq_id
        if key in seen:
            continue
        seen.add(key)
        branch_copy = deepcopy(branch)
        if not _df_text(branch_copy.get("branch_label"), 4):
            branch_copy["branch_label"] = _df_branch_label_for(list(old.get("branches") or []), _df_text(branch_copy.get("branch_id") or branch_copy.get("task_id"), 120))
        branches.append(branch_copy)

    registry = active_seq.get("task_registry") if isinstance(active_seq.get("task_registry"), dict) else {}
    top_registry = state.get("dialogue_task_registry") if isinstance(state.get("dialogue_task_registry"), dict) else {}
    merged_registry = dict(top_registry)
    merged_registry.update(registry)
    for task_id, task in merged_registry.items():
        if not isinstance(task, dict):
            continue
        if str(task.get("sequence_id") or current_id) != current_id:
            continue
        task_id = str(task.get("task_id") or task_id)
        if task_id in seen:
            continue
        branches.append({
            "branch_id": f"{current_id}:{task_id}",
            "sequence_id": current_id,
            "task_id": task_id,
            "topic": _df_text(task.get("topic") or active_topic, 220),
            "canonical_entity": _df_text(task.get("entity") or task.get("active_entity") or active_entity, 180),
            "goal": _df_text(task.get("goal") or "answer", 120),
            "turn_count": int(task.get("response_count") or task.get("turn_count") or 0),
            "last_user_request": _df_text(task.get("last_user_request"), 600),
            "last_april_answer": _df_text(task.get("last_april_answer") or task.get("last_answer"), 900),
            "last_turn_at": task.get("last_turn_at") or task.get("updated_at"),
            "last_result": deepcopy(task.get("last_result") or {}),
            "answer_basis": deepcopy(task.get("last_answer_basis") or task.get("answer_basis") or {}),
            "dialogue_rules": deepcopy(task.get("dialogue_rules") or active_seq.get("dialogue_rules") or {}),
            "active_task": deepcopy(task),
            "active": task_id == active_task_id,
        })
        seen.add(task_id)

    if current_id and not branches:
        branches.append({
            "branch_id": f"{current_id}:{active_task_id}" if active_task_id else current_id,
            "sequence_id": current_id,
            "task_id": active_task_id,
            "topic": _df_text(active_seq.get("topic") or active_topic, 220),
            "canonical_entity": _df_text(active_entity, 180),
            "goal": _df_text(active_seq.get("goal") or "answer", 120),
            "last_user_request": _df_text(active_seq.get("last_user_request"), 600),
            "last_april_answer": _df_text(active_seq.get("last_april_answer"), 900),
            "last_turn_at": active_seq.get("last_turn_at"),
            "active_task": deepcopy(active_seq.get("active_task") or {}),
            "active": True,
        })

    # Normalize stable internal A/B/C labels once per branch graph.
    for idx, branch in enumerate(sorted(branches, key=lambda b: (float(b.get("started_at") or b.get("last_turn_at") or 0.0), str(b.get("task_id") or b.get("branch_id") or "")))):
        if not _df_text(branch.get("branch_label"), 4):
            branch["branch_label"] = _INTERNAL_BRANCH_ALPHABET_RU[min(idx, len(_INTERNAL_BRANCH_ALPHABET_RU) - 1)]
        branch["internal_only"] = True

    return {
        "version": "dialogue_branch_index_v4_dynamic_branches",
        "active_sequence_id": current_id,
        "target_sequence_id": current_id,
        "target_task_id": active_task_id,
        "target_branch_id": f"{current_id}:{active_task_id}" if current_id and active_task_id else current_id,
        "branches": branches[-32:],
    }


def _df_render_probe(text: str) -> dict[str, Any]:
    low = _df_low(text)
    reps: list[str] = []
    for rep, pattern in _df_render_patterns:
        if re.search(pattern, low):
            reps.append(rep)
    # Specific representations outrank generic image language.
    order = ["code", "formula", "table", "graph", "diagram", "image", "link"]
    reps = sorted(set(reps), key=lambda x: order.index(x))
    explicit = bool(reps)
    return {
        "requested": reps,
        "explicit": explicit,
        "evidence": "render_words" if explicit else "text_default",
        "visual_reference": bool(_df_deictic.search(low) and any(r in low for r in ("картинк", "изображени", "схем", "график", "таблиц", "формул"))),
    }


def _df_live_task_answer_probe(text: str, active_task: dict[str, Any], previous_april: str = "") -> dict[str, Any]:
    """Bind a user turn to an open question before topic/new-branch heuristics."""
    task = active_task if isinstance(active_task, dict) else {}
    phase = _df_low(task.get("phase"))
    expected = _df_low(task.get("expected_input_type") or task.get("input_type"))
    awaiting = bool(
        task.get("awaiting_user")
        or task.get("awaiting_input")
        or phase in {"awaiting_user_answer", "awaiting_input", "awaiting_answer"}
        or expected in {"answer", "user_answer", "text_answer", "choice", "selection"}
    )
    question = _df_text(task.get("last_question") or task.get("prompt") or task.get("question"), 900)
    question_source = "active_task" if question else ""
    # Normal conversational questions are also live context even when no
    # interactive task object was created for that turn. This keeps an ordinary
    # chat exchange alive instead of requiring every question to become a task.
    if not question and _df_text(previous_april).rstrip().endswith(("?", "？")):
        question = _df_text(previous_april, 900)
        question_source = "last_april_question"
        awaiting = True
    if not question or not awaiting:
        return {"active": False, "question": question, "question_source": question_source, "score": 0.0, "input_role": "current_turn", "answer_candidate": False}

    low = _df_low(text)
    words = _df_tokens(text)
    stripped = low.strip(" .,!?:;-—")
    question_words = {"кто", "что", "почему", "зачем", "как", "где", "когда", "сколько", "какой", "какая", "какое", "какие", "можешь", "можно"}
    is_question = bool("?" in text or "？" in text or stripped in question_words)
    command_shape = bool(re.match(
        r"^(?:(?:а\s+)?теперь\s+|а\s+)?(?:расскажи|скажи|объясни|покажи|проверь|найди|сравни|напиши|создай|построй|опиши|рассчитай|посчитай|ответь|дай|выдай|укажи)\b",
        low,
    ))
    if _df_strong_topic_boundary(text) or _df_explicit_recall(text):
        return {"active": True, "question": question, "question_source": question_source, "score": 0.0, "input_role": "current_turn", "answer_candidate": False, "escaped_by": "boundary_or_recall"}

    if command_shape or (is_question and len(words) >= 2):
        return {"active": True, "question": question, "question_source": question_source, "score": 0.0, "input_role": "current_turn", "answer_candidate": False, "escaped_by": "self_contained_question_or_command"}

    if is_question:
        return {"active": True, "question": question, "question_source": question_source, "score": 0.88, "input_role": "followup_question_to_active_task", "answer_candidate": False, "escaped_by": "short_live_question"}

    score = 0.99 if len(words) <= 3 else 0.96 if len(words) <= 8 else 0.90 if len(words) <= 16 else 0.78
    return {"active": True, "question": question, "question_source": question_source, "score": score, "input_role": "answer_to_active_question", "answer_candidate": True, "escaped_by": ""}


def _df_task_probe(text: str, active_task: dict[str, Any], active_topic: str, previous_april: str = "") -> dict[str, Any]:
    low = _df_low(text)
    current_game_topic = any(x in low for x in ("угадай", "отгадай", "разгадай", "игру", "игра"))
    game_topic = current_game_topic or "угадай" in _df_low(active_topic)
    donut_task = "пончик" in low or "пончики" in low
    # Do not treat a generic request for a formula as analysis of a previous task.
    # That lexical hit previously made unrelated science questions inherit the
    # active riddle/game relation. Task analysis requires explicit discourse cues.
    answer_analysis = any(x in low for x in (
        "как ты угадал", "почему ты угадал", "правильный ответ", "твои вычисления",
        "как получил ответ", "почему ответ такой",
    ))

    # A user may redefine the operating rule of an already active dialogue without
    # changing its subject. Treat explicit procedural language as a task definition
    # so the rule becomes the new canonical objective rather than inheriting a stale
    # task prompt from the previous turn.
    # Presentation rules are handled by _df_dialogue_rules and do not create tasks.
    task_definition = bool(
        any(x in low for x in (
            "условия игры", "правила игры", "давай сыграем", "сыграем в игру",
            "начнем игру", "начнём игру",
        ))
        and len(_df_tokens(low)) >= 4
    )

    active_task_topic = _df_text(active_task.get("topic") or active_task.get("canonical_topic"))
    compatible_persisted_task = bool(
        active_task.get("active")
        and (not active_topic or not active_task_topic
             or _df_overlap(active_topic, active_task_topic) >= 0.25
             or active_topic.lower() in active_task_topic.lower()
             or active_task_topic.lower() in active_topic.lower())
    )
    live_answer = _df_live_task_answer_probe(text, active_task, previous_april=previous_april)
    active = bool(
        game_topic
        or task_definition
        or compatible_persisted_task
        or live_answer.get("answer_candidate")
        or live_answer.get("input_role") == "followup_question_to_active_task"
    )
    handoff = current_game_topic and (donut_task or any(x in low for x in ("я загад", "задавай вопросы", "наводящие вопросы")))
    task_action = (
        handoff or answer_analysis or task_definition
        or bool(live_answer.get("answer_candidate"))
        or live_answer.get("input_role") == "followup_question_to_active_task"
        or (compatible_persisted_task and any(x in low for x in ("угадать", "угадай", "отгадать", "ответь")))
    )
    return {
        "active": active,
        "current_game_topic": current_game_topic,
        "task_definition": task_definition,
        "kind": _df_text(
            "dialogue_task" if task_definition and not game_topic else active_task.get("kind") or ("game" if game_topic else ""),
            80,
        ).lower(),
        "role": _df_text(active_task.get("role") or ("april_guesses_user_object" if handoff else ""), 100),
        "handoff": handoff,
        "task_action": task_action,
        "answer_analysis": answer_analysis,
        "topic": (
            _df_text(active_topic, 180) if task_definition and active_topic
            else "игра в угадайки" if current_game_topic and any(x in low for x in ("угадай", "отгадай", "разгадай"))
            else _df_text(active_task.get("topic"), 180) if compatible_persisted_task
            else ""
        ),
        "objective": _df_text(text, 1200) if task_definition else _df_text(active_task.get("objective"), 1200) if compatible_persisted_task else "",
        "live_question": _df_text(live_answer.get("question"), 900),
        "live_question_source": _df_text(live_answer.get("question_source") or "", 40),
        "live_question_score": float(live_answer.get("score", 0.0) or 0.0),
        "live_input_role": _df_text(live_answer.get("input_role") or "current_turn", 80),
        "answer_to_active_task": bool(live_answer.get("answer_candidate")),
        "live_task_active": bool(live_answer.get("active")),
    }


def _df_dialogue_bigunok(text: str, previous_user: str, previous_april: str, active_topic: str, active_entity: str, task: dict[str, Any]) -> dict[str, Any]:
    low = _df_low(text)
    short = len(_df_tokens(low)) <= 3
    confirmation = low.strip(" .,!?:;-—") in _df_confirm
    rejection = low.strip(" .,!?:;-—") in _df_reject
    deictic = bool(_df_deictic.search(low))
    direct_reference = any(x in low for x in _df_explicit_result)
    topic_overlap = max(_df_overlap(low, active_topic), _df_overlap(low, active_entity), _df_overlap(low, previous_user), _df_overlap(low, previous_april))
    dialogue_rule_signal = bool(
        re.search(r"\b(?:отвечай|овечай|нумеруй|номеруй|помечай|ставь)\b", low)
        and re.search(r"\b(?:букв|алфавит|цифр|номер)\w*\b", low)
    )
    continuation_verb = bool(re.search(
        r"^(?:дальше|продолжай(?:те)?|продолжим|продолжить|следующ(?:ий|ая|ее|ие)|ещ(?:е|ё)|далее)$",
        low.strip(" .,!?:;-—"),
    ))
    semantic_signal = (
        0.97 if direct_reference else
        0.95 if dialogue_rule_signal else
        0.94 if task.get("task_action") else
        0.93 if (confirmation or rejection) and previous_april else
        0.88 if (deictic or continuation_verb) and previous_april else
        0.76 if topic_overlap >= 0.34 else
        0.0
    )
    return {
        "short": short,
        "confirmation": confirmation,
        "rejection": rejection,
        "deictic": deictic,
        "direct_reference": direct_reference,
        "continuation_verb": continuation_verb,
        "dialogue_rule_signal": dialogue_rule_signal,
        "topic_overlap": topic_overlap,
        "semantic_signal": semantic_signal,
        "has_live_pair": bool(previous_user or previous_april),
    }


def _df_new_sequence_id(user_id: str, conversation_id: str, text: str) -> str:
    """Create a stable parent conversation sequence for the current 12h window.

    Topic changes inside the same authenticated conversation must not create new
    sequence identities; tasks are the children of this sequence.
    """
    bucket = int(time.time() // (12 * 60 * 60))
    raw = f"{user_id}|{conversation_id}|dialogue-sequence-v3|{bucket}"
    return "seq-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _df_dialogue_rules(
    text: str,
    prior: dict[str, Any] | None = None,
    previous_april: str = "",
) -> dict[str, Any]:
    """Store user presentation preferences as internal metadata only.

    These rules never own topic, task or branch selection and never cause the
    executor/provider to prefix a human-visible answer.
    """
    prior = prior if isinstance(prior, dict) else {}
    previous = prior.get("dialogue_rules") if isinstance(prior.get("dialogue_rules"), dict) else {}
    low = _df_low(text)

    disable = any(x in low for x in (
        "не нумеруй", "не ставь номер", "без нумерации", "перестань нумеровать",
    ))
    if disable:
        return {
            "enabled": False,
            "visible": False,
            "internal_only": True,
            "updated": True,
            "source": "dialogue_rule_update",
        }

    answer_target = any(x in low for x in (
        "каждый свой ответ", "каждый ответ", "каждого ответа",
        "каждый свой", "каждого своего ответа",
    ))
    ordering = any(x in low for x in (
        "последовательн", "нумеровать", "номеровать", "нумеруй", "номеруй",
        "ставить цифру", "ставь цифру", "помечать цифрой", "помечала цифрой",
        "ставить букву", "ставь букву", "помечать буквой", "по алфавиту",
        "начиная с а", "начиная с 1", "с буквы а",
    ))
    explicit_rule = bool(answer_target and ordering)
    if not explicit_rule:
        kept = dict(previous)
        kept.pop("updated", None)
        kept.pop("updated_at", None)
        if kept:
            kept["visible"] = False
            kept["internal_only"] = True
            # next_marker is intentionally removed: visible presentation must not
            # be driven by the previous answer text.
            kept.pop("next_marker", None)
        return kept

    alphabetic = any(x in low for x in (
        "ставить букву", "ставь букву", "помечать буквой", "по алфавиту",
        "начиная с а", "с буквы а",
    ))
    numeric = any(x in low for x in (
        "ставить цифру", "ставь цифру", "помечать цифрой", "помечала цифрой",
        "цифрой", "цифру", "нумеровать", "номеровать", "начиная с 1",
    ))
    mode = "alphabetic" if alphabetic and not numeric else "numeric" if numeric and not alphabetic else "alphabetic" if alphabetic else "numeric"
    return {
        "enabled": True,
        "visible": False,
        "internal_only": True,
        "scope": "dialogue",
        "mode": mode,
        "start": 1,
        "source_instruction": _df_text(text, 1200),
        "until_explicit_end": bool(
            any(x in low for x in ("пока я не скажу", "до тех пор", "подведём итоги", "подведем итоги"))
            or previous.get("until_explicit_end")
        ),
        "updated": True,
        "updated_at": time.time(),
    }


# ---------------------------------------------------------------------------
# Dynamic 12h dialogue branch graph — internal metadata only.
# ---------------------------------------------------------------------------
_INTERNAL_BRANCH_ALPHABET_RU = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"


def _df_dialogue_repair_request(text: str) -> bool:
    low = _df_low(text)
    return any(re.search(pattern, low) for pattern in (
        r"не\s*понял.*(?:о\s+ком|кого|что).*(?:спрашивал|спрашива(?:л|ю))",
        r"я\s+не\s*(?:это|то)\s+спрашивал",
        r"(?:нет|не),?\s*я\s+не\s*(?:про\s+это|об\s+этом|о\s+том|это)\b.*(?:спрашива(?:л|ю)|имел\s+в\s+виду)",
        r"я\s+не\s+(?:спрашивал|спрашиваю|спрашивала)\b",
        r"ты\s+не\s+то\s+(?:ответил|ответила|сказал|сказала)",
        r"я\s+спрашивал\s+про",
        r"я\s+имел\s+в\s+виду",
    ))


def _df_comparison_request(text: str) -> bool:
    low = _df_low(text)
    return bool(re.search(
        r"(?:что\s+общего|сравни(?:ть)?|разниц[аы]|отлич(?:ие|ия|ается|аются)|похож(?:и|есть)|между\s+.+\s+и\b)",
        low,
    ))


def _df_stem_token(value: Any) -> str:
    token = _df_low(value).strip(".,!?;:()[]{}«\"'—-_")
    if not token:
        return ""
    for suffix in (
        "иями", "ами", "ями", "ого", "ему", "ому", "ыми", "ими",
        "ов", "ев", "ам", "ям", "ах", "ях", "ом", "ем", "ою", "ею",
        "ий", "ый", "ой", "ая", "яя", "ое", "ее", "ые", "ие",
        "ую", "юю", "а", "я", "у", "ю", "ы", "и", "е",
    ):
        if token.endswith(suffix) and len(token) - len(suffix) >= 5:
            return token[:-len(suffix)]
    return token


def _df_branch_mention_score(text: str, branch: dict[str, Any]) -> float:
    q = {_df_stem_token(t) for t in _df_tokens(text)} - {""}
    entity_text = " ".join(
        _df_text(x, 220) for x in (
            branch.get("canonical_entity"), branch.get("entity"), branch.get("topic"),
        ) if _df_text(x)
    )
    c = {_df_stem_token(t) for t in _df_tokens(entity_text)} - {""}
    if not q or not c:
        return 0.0
    exact = len(q & c) / max(1, len(c))
    fuzzy = sum(
        1 for qt in q if len(qt) >= 5 and any(qt == ct or qt[:5] == ct[:5] for ct in c if len(ct) >= 5)
    ) / max(1, len(c))
    return round(max(exact, fuzzy), 6)


def _df_find_branch_mentions(text: str, branches: dict[str, Any]) -> list[dict[str, Any]]:
    scored = []
    for branch in list(branches.get("branches") or []):
        if not isinstance(branch, dict):
            continue
        score = _df_branch_mention_score(text, branch)
        if score >= 0.75:
            item = deepcopy(branch)
            item["mention_score"] = score
            scored.append(item)
    scored.sort(key=lambda b: (
        float(b.get("mention_score") or 0.0),
        1 if b.get("active") else 0,
        float(b.get("last_turn_at") or b.get("started_at") or 0.0),
    ), reverse=True)
    return scored[:6]


def _df_branch_label_for(branches: list[dict[str, Any]], branch_id: str) -> str:
    ordered = sorted(
        [b for b in branches if isinstance(b, dict)],
        key=lambda b: (
            float(b.get("started_at") or b.get("last_turn_at") or 0.0),
            str(b.get("task_id") or b.get("branch_id") or ""),
        ),
    )
    for idx, branch in enumerate(ordered):
        if str(branch.get("branch_id") or branch.get("task_id") or "") == str(branch_id or ""):
            return _INTERNAL_BRANCH_ALPHABET_RU[min(idx, len(_INTERNAL_BRANCH_ALPHABET_RU) - 1)]
        stored = str(branch.get("branch_label") or "").strip()
        if stored and str(branch.get("task_id") or "") == str(branch_id or ""):
            return stored[:4]
    return _INTERNAL_BRANCH_ALPHABET_RU[min(len(ordered), len(_INTERNAL_BRANCH_ALPHABET_RU) - 1)] if ordered else "А"


def _df_internal_response_path(branch_label: str, response_count: int) -> str:
    branch = _df_text(branch_label, 4).upper() or "А"
    idx = max(0, int(response_count or 0))
    answer = _INTERNAL_BRANCH_ALPHABET_RU[min(idx, len(_INTERNAL_BRANCH_ALPHABET_RU) - 1)]
    return f"{branch}.{answer}"


def _df_identity_question(text: str) -> bool:
    low = _df_low(text)
    return bool(re.match(
        r"^(?:ты\s+кто|кто\s+ты|как\s+тебя\s+зовут|что\s+ты\s+умеешь|что\s+ты\s+можешь)\b",
        low,
    ))


def _df_comparison_branch_context(
    text: str,
    active_branch: dict[str, Any],
    mentioned: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates = list(mentioned)
    if isinstance(active_branch, dict) and active_branch:
        candidates.append(active_branch)
    linked = []
    seen = set()
    for branch in candidates:
        if not isinstance(branch, dict):
            continue
        bid = _df_text(branch.get("branch_id") or branch.get("task_id"), 120)
        if not bid or bid in seen:
            continue
        seen.add(bid)
        linked.append({
            "branch_id": bid,
            "task_id": _df_text(branch.get("task_id"), 100),
            "branch_label": _df_text(branch.get("branch_label"), 4),
            "topic": _df_text(branch.get("topic") or branch.get("canonical_entity"), 140),
            "entity": _df_text(branch.get("canonical_entity") or branch.get("entity"), 120),
            "last_user_request": _df_text(branch.get("last_user_request"), 180),
            "last_april_answer": _df_text(branch.get("last_april_answer"), 260),
        })
    return linked[:4]

def _df_resolve_relation(
    text: str,
    state: dict[str, Any],
    previous_april: str,
    active_topic: str,
    active_entity: str,
    task_probe: dict[str, Any],
    dialogue_probe: dict[str, Any],
    *,
    semantic: dict[str, Any] | None = None,
    sequence_digest: dict[str, Any] | None = None,
    branches: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Resolve the current turn against the live 12-hour dialogue sequence.

    The parent sequence supplies evidence; it never vetoes a self-contained new
    request. A task is a branch, not the conversation itself.
    """
    semantic = semantic if isinstance(semantic, dict) else {}
    sequence_digest = sequence_digest if isinstance(sequence_digest, dict) else {}
    branches = branches if isinstance(branches, dict) else {}

    explicit_recall = _df_explicit_recall(text)
    if explicit_recall:
        return "RECALL", "REFERENCE_OLD_TOPIC"

    seq = state.get("active_dialogue_sequence") if isinstance(state.get("active_dialogue_sequence"), dict) else {}
    has_live = bool(
        _df_text(seq.get("sequence_id"), 120)
        or sequence_digest.get("sequence_id")
        or active_topic
        or previous_april
    )
    if not has_live:
        return "NEW", "NEW_TOPIC"

    low = _df_low(text)
    words = _df_tokens(text)
    short_turn = len(words) <= 8
    confirmation = bool(dialogue_probe.get("confirmation"))
    rejection = bool(dialogue_probe.get("rejection"))
    deictic = bool(dialogue_probe.get("deictic"))
    direct_reference = bool(dialogue_probe.get("direct_reference"))
    task_action = bool(task_probe.get("task_action"))

    if _df_dialogue_repair_request(text):
        return "CONTINUE", "DIALOGUE_REPAIR"

    mentioned = _df_find_branch_mentions(text, branches)
    active_task_id = _df_text(seq.get("task_id") or state.get("active_dialogue_task_id"), 100)
    distinct_old = [
        b for b in mentioned
        if _df_text(b.get("task_id"), 100) and _df_text(b.get("task_id"), 100) != active_task_id
    ]
    comparison = _df_comparison_request(text)
    if not _df_strong_topic_boundary(text) and comparison:
        if len(mentioned) >= 2 or (len(mentioned) == 1 and (distinct_old or deictic)):
            return "NEW", "BRANCH_COMPARISON"
    if not _df_strong_topic_boundary(text) and distinct_old:
        return "RECALL", "AUTO_BRANCH_RETURN"

    sequence_topics = [
        _df_text(sequence_digest.get("root_topic"), 220),
        _df_text(sequence_digest.get("current_topic"), 220),
        _df_text(sequence_digest.get("current_task_topic"), 220),
        *[_df_text(x, 220) for x in sequence_digest.get("topic_path", [])[-6:]],
    ]
    trajectory_items = list(sequence_digest.get("recent_trajectory") or []) + list(sequence_digest.get("task_trajectory") or [])
    trajectory_overlap = 0.0
    for item in trajectory_items[-12:]:
        if not isinstance(item, dict):
            continue
        for field in ("user", "april", "topic"):
            value = item.get(field)
            if value:
                trajectory_overlap = max(trajectory_overlap, _df_overlap(low, value))

    contextual_overlap = max(
        float(dialogue_probe.get("topic_overlap", 0.0) or 0.0),
        *[_df_overlap(low, topic) for topic in sequence_topics if topic],
        float(_df_overlap(low, sequence_digest.get("last_user")) or 0.0),
        float(_df_overlap(low, sequence_digest.get("last_april")) or 0.0),
        float(_df_overlap(low, active_entity) or 0.0),
        trajectory_overlap,
    ) if sequence_topics or active_entity or trajectory_items else float(dialogue_probe.get("topic_overlap", 0.0) or 0.0)

    current_subject = _df_normalize_subject(
        _df_text(semantic.get("explicit_subject") or _df_extract_subject(text), 220)
    )
    active_subjects = [
        _df_text(active_entity, 220),
        _df_text(active_topic, 220),
        _df_text(sequence_digest.get("current_task_topic"), 220),
    ]
    subject_overlap = max(
        (_df_overlap(current_subject, candidate) for candidate in active_subjects if candidate),
        default=0.0,
    ) if current_subject else 0.0

    live_input_role = _df_text(task_probe.get("live_input_role"), 80)
    live_task_question = _df_text(task_probe.get("live_question"), 900)
    live_task_active = bool(task_probe.get("live_task_active") and live_task_question)
    if live_task_active and not _df_strong_topic_boundary(text) and not _df_explicit_recall(text):
        if task_probe.get("answer_to_active_task"):
            return "CONTINUE", "ACTIVE_TASK_ANSWER"
        if live_input_role == "followup_question_to_active_task":
            return "CONTINUE", "ACTIVE_TASK_FOLLOWUP_QUESTION"

    question_subject = _df_extract_subject(text)
    identity_question = _df_identity_question(text)
    standalone_question = bool(
        identity_question
        or (
            question_subject
            and re.match(
                r"^(?:(?:продолжаем|продолжим|дальше|теперь)\s+)?(?:что\s+такое|кто\s+такой|кто\s+(?:такая|такое|такие)|кто\s+это)\b",
                low,
            )
        )
    )

    # A complete question with its own subject is independent unless that subject
    # actually matches the current live branch. This is the key distinction that
    # prevents "океан/пустыня/Пушкин" from inheriting an old subject.
    if standalone_question:
        if subject_overlap >= 0.20 or direct_reference or deictic:
            return "CONTINUE", "ACTIVE_SUBJECT_FOLLOWUP"
        return "NEW", "SELF_CONTAINED_QUESTION"

    # The same rule applies to complete imperative requests with an extracted
    # operand. They can start a new task while remaining in the parent 12h session.
    command_with_subject = bool(
        current_subject
        and re.match(
            r"^(?:а\s+)?(?:назови|скажи|дай|выдай|укажи|выбери|расскажи|объясни|покажи|проверь|найди|напиши|создай|построй|опиши|рассчитай|посчитай|ответь|определи)\b",
            low,
        )
    )
    if command_with_subject:
        if subject_overlap >= 0.20 or direct_reference or deictic:
            return "CONTINUE", "ACTIVE_SUBJECT_FOLLOWUP"
        return "NEW", "SELF_CONTAINED_COMMAND"

    sequence_rules = (
        state.get("active_dialogue_sequence", {}).get("dialogue_rules", {})
        if isinstance(state.get("active_dialogue_sequence"), dict)
        else {}
    )
    rule_update = _df_dialogue_rules(text, {"dialogue_rules": sequence_rules})
    if rule_update.get("updated"):
        return "CONTINUE", "DIALOGUE_RULE_UPDATE"

    # Elliptical turns stay on the live branch when the utterance is clearly a
    # discourse continuation or a dialogue-rule update. Mere task existence is
    # not enough.
    if dialogue_probe.get("semantic_signal", 0.0) >= 0.95 and (dialogue_probe.get("confirmation") or dialogue_probe.get("rejection") or dialogue_probe.get("direct_reference")):
        return "CONTINUE", "DIALOGUE_DISCOURSE_FOLLOWUP"
    if dialogue_probe.get("semantic_signal", 0.0) >= 0.95 and re.search(r"\b(?:букв|алфавит|цифр|номер)\w*\b", low) and re.search(r"\b(?:отвечай|овечай|нумеруй|номеруй|помечай|ставь)\b", low):
        return "CONTINUE", "DIALOGUE_RULE_UPDATE"

    if short_turn:
        if confirmation or rejection or deictic or direct_reference or task_action or dialogue_probe.get("continuation_verb"):
            return "CONTINUE", "CONTEXTUAL_SHORT_FOLLOWUP"
        if contextual_overlap >= 0.12:
            return "CONTINUE", "ACTIVE_BRANCH_AFFINITY"
        if low in _df_confirm | _df_reject | _df_short_filler:
            return "CONTINUE", "DISCOURSE_CONTINUATION"
        return "NEW", "UNRELATED_SHORT_TURN"

    if task_action:
        return "CONTINUE", "TASK_ACTION"
    if direct_reference or deictic:
        return "CONTINUE", "CONTEXTUAL_REFERENCE"
    if contextual_overlap >= 0.18 and not _df_strong_topic_boundary(text):
        return "CONTINUE", "ACTIVE_BRANCH_AFFINITY"
    if _df_strong_topic_boundary(text):
        return "NEW", "EXPLICIT_TOPIC_BOUNDARY"

    if _df_is_self_contained_new_topic(
        text,
        semantic,
        active_topic=active_topic,
        active_entity=active_entity,
        task_probe=task_probe,
        sequence_digest=sequence_digest,
    ):
        return "NEW", "SELF_CONTAINED_NEW_SUBJECT"

    return "CONTINUE", "LIVE_BRANCH_CONTEXTUAL_DEFAULT"

def _df_understand(
    text: str,
    relation: str,
    turn_relation: str,
    active_topic: str,
    active_entity: str,
    task_probe: dict[str, Any],
    render_probe: dict[str, Any],
) -> dict[str, Any]:
    low = _df_low(text)
    explicit_subject = _df_normalize_subject(_df_extract_subject(text))
    entity = explicit_subject or active_entity

    operation = "answer"
    goal = "answer"
    if _df_memory_scope_request(text):
        operation, goal = "recall", "memory_recall"
    elif any(x in low for x in ("объясни", "объяснить", "почему", "разъясни", "как ты")):
        operation, goal = "explain", "understand"
    elif render_probe["requested"]:
        operation, goal = (
            ("modify", "present")
            if any(x in low for x in ("измени", "переделай", "добавь", "убери"))
            else ("build", "present")
        )
    elif any(x in low for x in ("проверь", "проанализируй", "разбери", "анализируй")):
        operation, goal = "analyze", "diagnose_or_analyze"
    elif any(x in low for x in ("угадай", "отгадай", "разгадай")) or task_probe.get("handoff"):
        operation, goal = "answer", "guess"

    representation = render_probe["requested"][0] if render_probe["requested"] else "text"

    if _df_memory_scope_request(text):
        return {
            "topic": "диалоговая память",
            "entity": "",
            "operation": operation,
            "goal": goal,
            "representation": representation,
            "semantic_request": _df_text(text, 1200),
            "explicit_subject": "",
        }

    # A concrete subject in the current request is authoritative during
    # interpretation. Only an elliptical turn inherits the active topic/entity.
    if explicit_subject:
        topic = explicit_subject
        entity = explicit_subject
    elif relation in {"CONTINUE", "RECALL"} and active_topic:
        topic = active_topic
    else:
        topic = active_topic or entity or _df_text(text, 180)

    if turn_relation in {"DIALOGUE_REPAIR", "DIALOGUE_RULE_UPDATE"}:
        topic = active_topic or topic
        entity = active_entity or ""
    elif turn_relation == "BRANCH_COMPARISON" and explicit_subject:
        topic = explicit_subject
        entity = explicit_subject

    semantic_request = _df_text(text, 1200)
    return {
        "topic": _df_text(topic, 220),
        "entity": _df_text(entity, 180),
        "operation": operation,
        "goal": goal,
        "representation": representation,
        "semantic_request": semantic_request,
        "explicit_subject": explicit_subject,
    }

def _df_task_state(
    text: str, relation: str, task_probe: dict[str, Any], prior: dict[str, Any],
    topic: str, entity: str, sequence_id: str, active_context: dict[str, Any] | None = None
) -> dict[str, Any]:
    active_context = active_context if isinstance(active_context, dict) else {}
    prior = prior if isinstance(prior, dict) else {}
    context_task = active_context.get("task") if isinstance(active_context.get("task"), dict) else {}

    # NEW always creates an explicit task record. This replaces the old behavior
    # where ordinary new subjects had no task state at all.
    if relation == "NEW":
        raw = f"{sequence_id}|{topic}|{time.time_ns()}|task"
        task_id = "task-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]
        task = {
            "active": True,
            "status": "open",
            "kind": "dialogue_task" if task_probe.get("current_game_topic") or task_probe.get("task_definition") else "topic_task",
            "role": task_probe.get("role") or "",
            "phase": "active",
            "topic": _df_text(topic or task_probe.get("topic"), 220),
            "entity": _df_text(entity, 180),
            "goal": _df_text(task_probe.get("task_definition") and "follow_user_rules" or task_probe.get("answer_analysis") and "understand" or "answer", 160),
            "objective": _df_text(task_probe.get("objective") or text, 1200),
            "instruction": _df_text(text, 1200) if task_probe.get("task_definition") else "",
            "task_id": task_id,
            "sequence_id": sequence_id,
            "response_count": 0,
            "task_response_count": 0,
            "turn_count": 0,
            "created_at": time.time(),
            "updated_at": time.time(),
            "last_user_request": _df_text(text, 1200),
            "last_april_answer": "",
            "last_result": {},
            "last_answer_basis": {},
            "result_history": [],
            "qa_history": [],
            "turns": [],
            "completed_results": [],
            "completed": False,
            "awaiting_user": True,
            "task_revision": 1,
        }
        return task

    # RECALL must use the branch selected by Interpretation, never the previous
    # active task. CONTINUE stays on the active branch.
    task = deepcopy(prior if relation == "RECALL" else (context_task or prior))
    if not task:
        return {}
    if sequence_id:
        task["sequence_id"] = sequence_id
    if not task.get("task_id"):
        raw = f"{sequence_id}|{task.get('topic') or topic}|legacy-task"
        task["task_id"] = "task-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]
    task["topic"] = _df_text(task.get("topic") or topic, 220)
    task["entity"] = _df_text(
        task.get("entity")
        if task_probe.get("answer_to_active_task") or task_probe.get("live_input_role") == "followup_question_to_active_task"
        else (entity or task.get("entity")),
        180,
    )
    if task_probe.get("task_definition"):
        task["objective"] = _df_text(task_probe.get("objective") or text, 1200)
        task["instruction"] = _df_text(text, 1200)
        task["goal"] = "follow_user_rules"
        task["updated_at"] = time.time()
    elif task_probe.get("answer_analysis"):
        task["goal"] = "understand"
    task["last_user_request"] = _df_text(text, 1200)
    if task_probe.get("answer_to_active_task"):
        task["last_user_answer"] = _df_text(text, 1200)
        task["last_answered_question"] = _df_text(task_probe.get("live_question"), 900)
        task["last_input_role"] = "answer_to_active_question"
        task["last_input_confidence"] = float(task_probe.get("live_question_score", 0.0) or 0.0)
    elif task_probe.get("live_input_role") == "followup_question_to_active_task":
        task["last_user_action"] = _df_text(text, 1200)
        task["last_input_role"] = "followup_question_to_active_task"
    task["task_revision"] = int(task.get("task_revision") or 0) + 1
    task["active"] = True
    task.setdefault("status", "open")
    task.setdefault("phase", "active")
    task.setdefault("response_count", int(task.get("task_response_count") or 0))
    task["task_response_count"] = int(task.get("response_count") or 0)
    return task


def _df_render_plan(text: str, relation: str, semantic: dict[str, Any], render_probe: dict[str, Any]) -> dict[str, Any]:
    requested = list(render_probe.get("requested") or [])
    # A representation belongs to this turn only. Never inherit a stale renderer.
    authorized = bool(requested)
    mode = requested[0] if requested else "TEXT_ONLY"
    return {
        "version": "render_plan_v1",
        "authorized": authorized,
        "requested_outputs": ["text"] + [x for x in requested if x != "text"],
        "representation": semantic.get("representation") or "text",
        "mode": mode,
        "artifact_reference": bool(authorized and render_probe.get("visual_reference") and relation == "CONTINUE"),
        "single_route": True,
        "renderer": {
            "image": "APRIL_IMAGES_GENERATION", "gallery": "APRIL_IMAGES_GENERATION", "diagram": "DiagramBlock",
            "graph": "GraphBlock", "table": "TableBlock", "formula": "FormulaBlock", "code": "CodeBlock", "link": "LinkBlock", "text": "MessageTextBlock",
        }.get(semantic.get("representation") or "text", "MessageTextBlock"),
    }


def _df_development(relation: str, sequence_id: str, active_topic: str, active_entity: str, goal: str, current_request: str, previous_april: str, task: dict[str, Any], render_plan: dict[str, Any]) -> dict[str, Any]:
    task = task if isinstance(task, dict) else {}
    previous_result = deepcopy(task.get("last_result") or {})
    previous_basis = deepcopy(task.get("last_answer_basis") or task.get("answer_basis") or {})
    result_history = deepcopy(task.get("result_history") or [])
    result_history = result_history[-3:] if isinstance(result_history, list) else []
    return {
        "version": "dialogue_development_v2_task_result_continuity",
        "relation": relation,
        "same_dialogue": relation in {"CONTINUE", "RECALL"},
        "sequence_id": sequence_id,
        "task_id": _df_text(task.get("task_id"), 100),
        "active_topic": active_topic,
        "active_goal": goal,
        "active_entity": active_entity,
        "current_request": current_request,
        "previous_result": previous_result or previous_april,
        "previous_answer_basis": previous_basis,
        "recent_task_results": result_history,
        "task_response_count": int(task.get("response_count") or task.get("task_response_count") or 0),
        "task_status": _df_text(task.get("status") or "open", 40),
        "task_completed": bool(task.get("completed") or str(task.get("status") or "").lower() == "completed"),
        "latest_result_event": {},
        "open_loops": [],
        "pending_obligations": [],
        "ready_obligations": [],
        "user_needs_guidance": False,
        "initiative_policy": "resume_or_answer_current_request",
        "next_logical_step": (
            "resume_task_from_last_result"
            if previous_result and not task.get("completed")
            else "summarize_completed_task_or_answer_current_request"
            if task.get("completed")
            else "answer_current_request"
        ),
        "continuation_anchor": "task_result" if relation in {"CONTINUE", "RECALL"} else "current_turn",
        "visual_continuity": bool(render_plan.get("artifact_reference")),
        "active_task": deepcopy(task),
    }


def _df_provider_plan(
    current_request: str,
    relation: str,
    turn_relation: str,
    semantic: dict[str, Any],
    task: dict[str, Any],
    previous_user: str,
    previous_april: str,
    sequence_id: str,
    render_plan: dict[str, Any],
    development: dict[str, Any],
    selected_memory: dict[str, Any],
    active_sequence_digest: dict[str, Any] | None = None,
    active_dialogue_context: dict[str, Any] | None = None,
    dialogue_rules: dict[str, Any] | None = None,
    related_branches: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Build the final Provider context after semantic understanding is complete.

    The Provider receives a prepared semantic packet. It never chooses the
    dialogue branch or searches memory on its own.
    """
    active_sequence_digest = (
        active_sequence_digest
        if isinstance(active_sequence_digest, dict)
        else {}
    )
    active_dialogue_context = (
        active_dialogue_context
        if isinstance(active_dialogue_context, dict)
        else {}
    )
    dialogue_rules = (
        dialogue_rules
        if isinstance(dialogue_rules, dict)
        else deepcopy(active_dialogue_context.get("dialogue_rules") or {})
    )
    related_branches = [deepcopy(x) for x in (related_branches or []) if isinstance(x, dict)][:4]
    base = {
        "version": _df_provider_plan_version,
        "relation": relation,
        "turn_relation": turn_relation,
        "current_user_request": current_request,
        "current_request_authoritative": True,
        "context_selection_done_before_provider": True,
        "provider_must_not_reselect_context": True,
        "hard_budget_tokens": 900,
        "soft_target_tokens": 820,
        "new_topic_minimal_context": relation == "NEW",
        "required_context": [
            {
                "key": "SEMANTIC_CORE",
                "priority": 1.0,
                "value": {
                    "topic": semantic.get("topic"),
                    "entity": semantic.get("entity"),
                    "operation": semantic.get("operation"),
                    "goal": semantic.get("goal"),
                    "representation": semantic.get("representation"),
                    "turn_relation": turn_relation,
                    "branch_label": semantic.get("branch_label") or "",
                    "branch_type": semantic.get("branch_type") or "topic",
                    "internal_response_path": semantic.get("internal_response_path") or "",
                },
            },
            {
                "key": "OUTPUT_CONTRACT",
                "priority": 0.99,
                "value": {
                    "representation": semantic.get("representation"),
                    "requested_outputs": render_plan.get("requested_outputs"),
                    "render_authorized": render_plan.get("authorized"),
                    "render_mode": render_plan.get("mode"),
                },
            },
            {
                "key": "DIALOGUE_RULES",
                "priority": 1.0,
                "value": deepcopy(dialogue_rules),
            },
            {
                "key": "RESPONSE_SEQUENCE",
                "priority": 1.0,
                "value": {
                    "sequence_id": sequence_id,
                    "task_id": task.get("task_id"),
                    "sequence_turn_index": int(active_sequence_digest.get("turn_count") or active_dialogue_context.get("response_sequence", {}).get("sequence_turn_index") or 0) + 1,
                    "output_rule": deepcopy(dialogue_rules),
                },
            },
            {
                "key": "TASK_RESULT_STATE",
                "priority": 1.0,
                "value": {
                    "task_id": task.get("task_id"),
                    "sequence_id": sequence_id,
                    "status": task.get("status") or "open",
                    "completed": bool(task.get("completed") or str(task.get("status") or "").lower() == "completed"),
                    "task_response_count": int(task.get("response_count") or task.get("task_response_count") or 0),
                    "previous_result": deepcopy(task.get("last_result") or active_dialogue_context.get("last_completed_result") or {}),
                    "answer_basis": deepcopy(task.get("last_answer_basis") or task.get("answer_basis") or {}),
                    "recent_results": deepcopy((task.get("result_history") or [])[-3:]),
                },
            },
        ],
        "optional_context": [],
        "excluded_context": [
            "FULL_HISTORY",
            "OTHER_TOPIC_BRANCHES",
            "UNRELATED_WINDOW_MEMORY",
            "STALE_GLOBAL_ENTITY",
        ],
    }

    if relation == "CONTINUE":
        # The active branch digest outranks topic-word similarity. It is the
        # compact picture that lets the model understand an elliptical turn.
        base["required_context"].insert(
            0,
            {
                "key": "ACTIVE_DIALOGUE_CONTEXT",
                "priority": 1.0,
                "value": {
                    "objective": active_dialogue_context.get("objective"),
                    "task": active_dialogue_context.get("task") or task,
                    "intent": active_dialogue_context.get("intent"),
                    "goal": active_dialogue_context.get("goal") or task.get("goal"),
                    "topic": active_dialogue_context.get("topic"),
                    "active_entity": active_dialogue_context.get("active_entity"),
                    "completed_results": list(active_dialogue_context.get("completed_results") or [])[-12:],
                    "last_completed_result": active_dialogue_context.get("last_completed_result") or {},
                    "sequence_id": active_dialogue_context.get("sequence_id") or sequence_id,
                },
            },
        )
        base["required_context"].insert(
            1,
            {
                "key": "ACTIVE_DIALOGUE_TRAJECTORY",
                "priority": 0.999,
                "value": active_sequence_digest,
            },
        )
        base["required_context"].insert(
            2,
            {
                "key": "DIALOGUE_ANCHOR",
                "priority": 0.995,
                "value": {
                    "previous_user_turn": previous_user,
                    "previous_april_turn": previous_april,
                    "topic": semantic.get("topic"),
                    "entity": semantic.get("entity"),
                    "turn_relation": turn_relation,
                    "sequence_id": sequence_id,
                    "current_turn_role": _df_text(semantic.get("current_turn_role") or "current_turn", 80),
                    "answer_to_active_task": bool(semantic.get("answer_to_active_task")),
                    "active_question": _df_text(semantic.get("active_question"), 900),
                },
            },
        )
        if task:
            base["required_context"].insert(
                4,
                {
                    "key": "ACTIVE_TASK",
                    "priority": 0.99,
                    "value": {
                        "kind": task.get("kind"),
                        "role": task.get("role"),
                        "phase": task.get("phase"),
                        "topic": task.get("topic"),
                        "goal": task.get("goal"),
                        "last_question": task.get("last_question"),
                        "last_user_answer": task.get("last_user_answer"),
                        "candidate_answer": _df_text(semantic.get("candidate_answer") or "", 1200),
                        "current_turn_role": _df_text(semantic.get("current_turn_role") or "current_turn", 80),
                        "answer_to_active_task": bool(semantic.get("answer_to_active_task")),
                    },
                },
            )
        base["required_context"].append(
            {
                "key": "DIALOGUE_DEVELOPMENT",
                "priority": 0.9,
                "value": development,
            }
        )

    if related_branches:
        base["required_context"].append({
            "key": "RELATED_TOPIC_BRANCHES",
            "priority": 0.98,
            "value": related_branches,
        })

    if relation == "RECALL":
        if active_sequence_digest:
            base["required_context"].append(
                {
                    "key": "ACTIVE_DIALOGUE_TRAJECTORY",
                    "priority": 0.995,
                    "value": deepcopy(active_sequence_digest),
                }
            )
            base["new_topic_minimal_context"] = False
        if selected_memory:
            base["required_context"].append(
                {
                    "key": "MEMORY_RECALL",
                    "priority": 0.9,
                    "value": [{
                        **deepcopy(selected_memory),
                        "resume_instruction": "Коротко напомни предыдущий предмет только настолько, насколько это помогает текущему вопросу, затем сразу продолжи текущий запрос. Не называй внутреннюю ветку, номер или путь.",
                    }],
                }
            )
            base["new_topic_minimal_context"] = False

    return base


def _df_select_recalled_branch(text: str, state: dict[str, Any], branches: dict[str, Any]) -> dict[str, Any]:
    low = _df_low(text)
    candidates = [b for b in list(branches.get("branches") or []) if isinstance(b, dict)]
    if not candidates:
        return {}

    # Explicit ordinal task recall: "первая задача", "ко второй", etc.
    ordinals = {
        "первая": 1, "первой": 1, "первую": 1,
        "вторая": 2, "второй": 2, "вторую": 2,
        "третья": 3, "третьей": 3, "третью": 3,
        "четвертая": 4, "четвертой": 4, "четвертую": 4,
        "пятая": 5, "пятой": 5, "пятую": 5,
    }
    ordered = sorted(
        candidates,
        key=lambda b: (float(b.get("started_at") or 0.0), str(b.get("task_id") or b.get("branch_id") or "")),
    )
    for word, number in ordinals.items():
        if word in low and ("задач" in low or "тем" in low or "ветк" in low):
            if 1 <= number <= len(ordered):
                return deepcopy(ordered[number - 1])
    m = re.search(r"(?:задач[аеу]?|ветк[аеу]?|тем[аеу]?)\s*(?:номер|№)?\s*(\d+)", low)
    if m:
        number = int(m.group(1))
        if 1 <= number <= len(ordered):
            return deepcopy(ordered[number - 1])

    mentioned = _df_find_branch_mentions(text, branches)
    if mentioned:
        return deepcopy(mentioned[0])

    def recall_overlap(query_text: str, candidate_text: str) -> float:
        exact = _df_overlap(query_text, candidate_text)
        q_tokens = _df_tokens(query_text)
        c_tokens = _df_tokens(candidate_text)
        if not q_tokens or not c_tokens:
            return exact
        fuzzy_hits = 0
        for qt in q_tokens:
            if any(qt == ct or (len(qt) >= 5 and len(ct) >= 5 and qt[:5] == ct[:5]) for ct in c_tokens):
                fuzzy_hits += 1
        fuzzy = fuzzy_hits / max(1, len(q_tokens))
        return max(exact, round(fuzzy, 6))

    scored = []
    for branch in candidates:
        hay = " ".join(
            _df_text(x) for x in (
                branch.get("topic"), branch.get("canonical_entity"),
                branch.get("last_user_request"), branch.get("last_april_answer"),
            )
        )
        score = recall_overlap(low, hay)
        scored.append((score, branch))
    scored.sort(key=lambda x: (x[0], 1 if x[1].get("active") else 0), reverse=True)
    return deepcopy(scored[0][1]) if scored and scored[0][0] >= 0.12 else {}


def _df_interpret_live_turn(
    text: str,
    *,
    history: list[Any] | None = None,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Canonical production interpretation pipeline.

    Order:
        1. receive current turn
        2. inspect authenticated active-branch memory
        3. build compact branch picture
        4. contextually understand the current turn
        5. resolve CONTINUE / NEW / RECALL
        6. build response/development intent
        7. build render plan
        8. build the frozen Provider context
        9. hand off to Executor/SceneContract

    Relation resolution is deliberately late. Rendering is never used to decide
    whether a user changed topic.
    """
    started = time.perf_counter()
    state = state if isinstance(state, dict) else {}
    history = history if isinstance(history, list) else []
    current = _df_text(text, 2400)
    identity_question = _df_identity_question(current)

    seq = (
        state.get("active_dialogue_sequence")
        if isinstance(state.get("active_dialogue_sequence"), dict)
        else {}
    )
    previous_user, previous_april = _df_extract_previous(history, state)
    active_topic = _df_topic_from_state(state)
    active_entity = _df_entity_from_state(state)
    active_context = state.get("active_dialogue_context") if isinstance(state.get("active_dialogue_context"), dict) else {}
    prior_task = _df_active_task(state)
    context_task = active_context.get("task") if isinstance(active_context.get("task"), dict) else {}
    context_task_id = _df_text(active_context.get("task_id") or context_task.get("task_id"), 100)
    prior_task_id = _df_text(prior_task.get("task_id"), 100) if isinstance(prior_task, dict) else ""
    if context_task and (not prior_task or not prior_task_id or not context_task_id or prior_task_id == context_task_id):
        prior_task = deepcopy(context_task)
    active_seq_id = _df_text(seq.get("sequence_id"), 80)
    active_task_id = _df_text(
        seq.get("task_id")
        or state.get("active_dialogue_task_id")
        or prior_task.get("task_id")
        or "",
        100,
    )
    conversation_id = _df_text(
        state.get("conversation_id")
        or (state.get("memory_scope") or {}).get("conversation_id"),
        120,
    )
    user_id = _df_text(
        state.get("user_id")
        or (state.get("memory_scope") or {}).get("user_id"),
        120,
    )

    # ------------------------------------------------------------------
    # 1) Active-session memory first.
    # ------------------------------------------------------------------
    active_sequence_digest = _df_active_sequence_digest(
        state,
        history,
        active_seq_id,
        limit=6,
        task_id=active_task_id,
    )
    digest_topic = _df_text(active_sequence_digest.get("current_topic"), 220)
    if digest_topic and _df_low(digest_topic) not in {
        "если", "это", "такое", "такой", "так", "пронумеруй", "выдай", "проверь",
    }:
        active_topic = digest_topic

    # ------------------------------------------------------------------
    # 2) Cheap evidence probes. They cannot own relation or routing.
    # ------------------------------------------------------------------
    render_probe = _df_render_probe(current)
    task_probe = _df_task_probe(current, prior_task, active_topic, previous_april=previous_april)
    dialogue_probe = _df_dialogue_bigunok(
        current,
        previous_user,
        previous_april,
        active_topic,
        active_entity,
        task_probe,
    )
    branches = _df_branch_index(state, seq, active_topic, active_entity)

    # ------------------------------------------------------------------
    # 3) Contextual understanding BEFORE relation resolution.
    #
    # A live branch is the working context. NEW is only provisional when there
    # is no live branch. This is what lets "да", "возможно", "дальше", numbers,
    # names and other elliptical human replies acquire meaning from the branch.
    # ------------------------------------------------------------------
    has_live_branch = bool(
        active_sequence_digest.get("sequence_id")
        or active_seq_id
        or active_topic
        or previous_april
    )
    explicit_recall = _df_explicit_recall(current)

    provisional_relation = (
        "RECALL"
        if explicit_recall
        else "CONTINUE"
        if has_live_branch
        else "NEW"
    )
    provisional_turn_relation = (
        "REFERENCE_OLD_TOPIC"
        if provisional_relation == "RECALL"
        else "CONTEXTUAL_UNDERSTANDING"
    )

    semantic = _df_understand(
        current,
        provisional_relation,
        provisional_turn_relation,
        active_topic,
        active_entity,
        task_probe,
        render_probe,
    )

    # ------------------------------------------------------------------
    # 4) Now resolve the dialogue relation from the contextual understanding.
    # ------------------------------------------------------------------
    relation, turn_relation = _df_resolve_relation(
        current, state, previous_april, active_topic, active_entity, task_probe, dialogue_probe,
        semantic=semantic, sequence_digest=active_sequence_digest, branches=branches,
    )
    topic_affinity = 0.0
    semantic_topic = _df_low(semantic.get("topic") or "")
    prior_task_topic = _df_low(
        (prior_task.get("topic") if isinstance(prior_task, dict) else "")
        or active_topic
        or (active_sequence_digest.get("root_topic") if isinstance(active_sequence_digest, dict) else "")
    )
    prior_task_entity = _df_low(
        (prior_task.get("entity") if isinstance(prior_task, dict) else "")
        or active_entity
        or (active_sequence_digest.get("current_focus") if isinstance(active_sequence_digest, dict) else "")
    )
    if semantic_topic and prior_task_topic:
        topic_affinity = max(topic_affinity, _df_overlap(semantic_topic, prior_task_topic))
    if semantic_topic and prior_task_entity:
        topic_affinity = max(topic_affinity, _df_overlap(semantic_topic, prior_task_entity))

    if not explicit_recall and not bool(task_probe.get("answer_to_active_task")) and _df_is_self_contained_new_topic(
        current, semantic, active_topic=active_topic, active_entity=active_entity,
        task_probe=task_probe, sequence_digest=active_sequence_digest,
    ) and topic_affinity < 0.28:
        relation, turn_relation = "NEW", "SELF_CONTAINED_NEW_SUBJECT"

    selected_branch: dict[str, Any] = {}
    branch_mentions = _df_find_branch_mentions(current, branches)
    active_branch = next((b for b in (branches.get("branches") or []) if isinstance(b, dict) and _df_text(b.get("task_id"), 100) == active_task_id), {})
    linked_branches: list[dict[str, Any]] = []
    if turn_relation == "BRANCH_COMPARISON":
        linked_branches = _df_comparison_branch_context(current, active_branch, branch_mentions)
        names = []
        for item in linked_branches:
            name = _df_text(item.get("entity") or item.get("topic"), 120)
            if name and name.lower() not in {x.lower() for x in names}:
                names.append(name)
        if names:
            semantic["topic"] = " и ".join(names[:3])
            semantic["entity"] = " и ".join(names[:3])

    # A recall request is allowed to select one older branch. Nothing else may
    # silently switch branches.
    if relation == "RECALL":
        # Broad memory introspection ("проверь 12-часовую память", "что ты
        # помнишь из предыдущих диалогов") asks for the window as a whole.
        # Only an explicitly identifiable subject/ordinal returns to one branch.
        if not _df_memory_scope_request(current):
            selected_branch = _df_select_recalled_branch(
                current,
                state,
                branches,
            )
        if selected_branch.get("sequence_id"):
            active_seq_id = _df_text(
                selected_branch.get("sequence_id"),
                80,
            )
            active_task_id = _df_text(selected_branch.get("task_id"), 100)
            active_topic = _df_text(
                selected_branch.get("topic")
                or active_topic,
                220,
            )
            active_entity = _df_text(
                selected_branch.get("canonical_entity")
                or active_entity,
                180,
            )
            previous_user = _df_text(
                selected_branch.get("last_user_request")
                or previous_user,
            )
            previous_april = _df_text(
                selected_branch.get("last_april_answer")
                or previous_april,
            )
            # Rebuild the digest for the branch explicitly selected by RECALL.
            active_sequence_digest = _df_active_sequence_digest(
                state,
                history,
                active_seq_id,
                limit=6,
                task_id=active_task_id,
            )

            recalled_task = selected_branch.get("active_task")
            if isinstance(recalled_task, dict) and recalled_task:
                prior_task = deepcopy(recalled_task)

            # Re-understand against the recalled branch, not the old active branch.
            semantic = _df_understand(
                current,
                "CONTINUE",
                "REFERENCE_OLD_TOPIC",
                active_topic,
                active_entity,
                _df_task_probe(current, prior_task, active_topic, previous_april=previous_april),
                render_probe,
            )

    if turn_relation in {"DIALOGUE_REPAIR", "DIALOGUE_RULE_UPDATE"}:
        # Repair and presentation-rule changes belong to the existing dialogue
        # branch. Neither utterance is allowed to become a new topic/entity.
        semantic["topic"] = active_topic
        semantic["entity"] = active_entity
        semantic["explicit_subject"] = ""

    # ------------------------------------------------------------------
    # 5) Apply the final relation to semantic identity.
    # ------------------------------------------------------------------
    explicit_entity = _df_normalize_subject(
        _df_text(semantic.get("explicit_subject"))
    )

    if relation == "NEW":
        if turn_relation == "BRANCH_COMPARISON" and linked_branches:
            comparison_names = []
            for item in linked_branches:
                name = _df_normalize_subject(_df_text(item.get("entity") or item.get("topic"), 120))
                if name and name.lower() not in {x.lower() for x in comparison_names}:
                    comparison_names.append(name)
            semantic["topic"] = " и ".join(comparison_names[:3]) or _df_normalize_subject(current)
            semantic["entity"] = semantic["topic"]
            active_topic = semantic["topic"]
            active_entity = semantic["entity"]
        else:
            new_topic = (
                "апрель: идентичность и возможности"
                if identity_question
                else semantic.get("explicit_subject")
                or semantic.get("entity")
                or _df_extract_subject(current)
                or current
            )
            semantic["topic"] = _df_normalize_subject(new_topic)
            active_topic = semantic["topic"]
            active_entity = _df_normalize_subject(
                semantic.get("entity")
                or _df_extract_subject(current)
            )
        branch_digest_for_provider: dict[str, Any] = {}
    else:
        # CONTINUE/RECALL preserve the live/recalled conversational identity.
        # A concrete operand may refine the active entity without replacing the
        # branch. Generic sentence tails never become the entity.
        live_reference_text = " ".join(
            [
                _df_text(active_topic, 220),
                _df_text(active_entity, 220),
                _df_text(active_sequence_digest.get("current_task_topic"), 220),
                _df_text(active_sequence_digest.get("last_user"), 220),
                _df_text(active_sequence_digest.get("last_april"), 260),
            ]
            + [
                _df_text(x.get("user"), 220)
                for x in list(active_sequence_digest.get("recent_trajectory") or [])[-6:]
                if isinstance(x, dict)
            ]
        )
        if explicit_entity and _df_overlap(explicit_entity, live_reference_text) >= 0.20:
            active_entity = explicit_entity
        elif not active_entity and semantic.get("entity") and not _df_low(semantic.get("entity")) in {"если", "это", "такое", "такой", "следующее", "дальше", "отвечай", "овечай"}:
            active_entity = _df_text(semantic.get("entity"), 180)

        semantic["entity"] = active_entity or ("" if relation == "RECALL" else ("" if _df_low(semantic.get("entity")) in {"если", "это", "такое", "такой", "следующее", "дальше", "отвечай", "овечай", "пронумеруй", "выдай", "проверь", "так"} else semantic.get("entity")))
        semantic["topic"] = semantic.get("topic") or active_topic
        branch_digest_for_provider = deepcopy(active_sequence_digest)

    # Broad RECALL is the 12-hour conversation itself. A specific branch is only
    # selected when the user identified one; otherwise keep the live sequence
    # digest so the Provider can summarize the requested memory window.
    if relation == "RECALL" and selected_branch.get("sequence_id"):
        branch_digest_for_provider = deepcopy(active_sequence_digest)

    if active_seq_id:
        # NEW is a new task inside the same authenticated dialogue sequence.
        sequence_id = active_seq_id
    else:
        sequence_id = _df_new_sequence_id(user_id, conversation_id, current)

    # ------------------------------------------------------------------
    # 6) Response task/development planning.
    # ------------------------------------------------------------------
    live_role = _df_text(task_probe.get("live_input_role") or "current_turn", 80)
    if relation == "CONTINUE" and live_role in {"answer_to_active_question", "followup_question_to_active_task"}:
        # The user's answer is payload for the existing task, not a new entity.
        # Preserve the task's semantic identity and carry the answer separately.
        semantic["topic"] = _df_text(prior_task.get("topic") or active_topic or semantic.get("topic"), 220)
        semantic["entity"] = _df_text(prior_task.get("entity") or active_entity or "", 180)
        if live_role == "answer_to_active_question":
            semantic["candidate_answer"] = current
    task = _df_task_state(
        current,
        relation,
        task_probe,
        prior_task,
        semantic.get("topic") or active_topic,
        semantic.get("entity") or active_entity,
        sequence_id,
        active_context,
    )
    if task and turn_relation == "BRANCH_COMPARISON":
        task["branch_type"] = "comparison"
        task["linked_branch_ids"] = [
            _df_text(x.get("branch_id") or x.get("task_id"), 120)
            for x in linked_branches
            if _df_text(x.get("branch_id") or x.get("task_id"), 120)
        ]
        task["linked_branches"] = deepcopy(linked_branches)
    active_task_id = _df_text(task.get("task_id"), 100) if task else active_task_id
    if turn_relation == "DIALOGUE_RULE_UPDATE":
        # Rule changes are presentation-only. They must not become a task turn,
        # alter the topic, or consume task-local response state.
        task = {}
        active_task_id = _df_text(
            seq.get("task_id") or active_task_id,
            100,
        )

    sequence_rule_seed = {
        "dialogue_rules": deepcopy(
            seq.get("dialogue_rules")
            or (active_context.get("dialogue_rules") if isinstance(active_context, dict) else {})
            or {}
        )
    }
    dialogue_rules = _df_dialogue_rules(
        current,
        sequence_rule_seed,
        previous_april=previous_april,
    )
    dialogue_rules.pop("updated", None)
    dialogue_rules.pop("updated_at", None)
    dialogue_rules["visible"] = False
    dialogue_rules["internal_only"] = True
    dialogue_rules.pop("next_marker", None)

    # Stable A/B/C branch identity is derived from the branch graph, never from
    # task response counters. The response path is useful only to memory/debugging.
    target_branch_id = _df_text(
        selected_branch.get("branch_id") if selected_branch else "",
        120,
    ) or (f"{sequence_id}:{active_task_id}" if active_task_id else sequence_id)
    branch_label = _df_text(selected_branch.get("branch_label") if selected_branch else "", 4)
    if not branch_label:
        branch_label = _df_branch_label_for(branches.get("branches") or [], target_branch_id)
    if turn_relation == "BRANCH_COMPARISON":
        branch_label = _df_branch_label_for(branches.get("branches") or [], target_branch_id) if target_branch_id else branch_label
    if task:
        task["branch_label"] = branch_label
        task["internal_only"] = True
        task["internal_response_path"] = _df_internal_response_path(
            branch_label, int(task.get("response_count") or task.get("task_response_count") or 0)
        )
        task["next_internal_response_path"] = _df_internal_response_path(
            branch_label, int(task.get("response_count") or task.get("task_response_count") or 0) + 1
        )

    development = _df_development(
        relation,
        sequence_id,
        semantic.get("topic") or active_topic,
        semantic.get("entity") or active_entity,
        semantic.get("goal") or "answer",
        current,
        previous_april,
        task,
        {},  # render plan is attached after semantic response planning
    )

    # ------------------------------------------------------------------
    # 7) Render determination happens only after dialogue understanding/relation.
    # ------------------------------------------------------------------
    render_plan = _df_render_plan(
        current,
        relation,
        semantic,
        render_probe,
    )
    development["render_plan"] = deepcopy(render_plan)
    development["next_logical_step"] = (
        "answer_current_request"
        if relation != "RECALL"
        else "answer_recalled_branch_request"
    )
    development["active_sequence_digest_version"] = (
        branch_digest_for_provider.get("version")
        if branch_digest_for_provider
        else ""
    )

    selected_memory = selected_branch if relation == "RECALL" else {}

    # Freeze the human-turn relationship into the semantic packet before the
    # Provider plan is built. These fields describe the live exchange, not an
    # internal branch/counter, and prevent a short answer from reaching the model
    # as an apparently standalone request.
    semantic["current_turn_role"] = _df_text(
        task_probe.get("live_input_role") or "current_turn", 80
    )
    semantic["answer_to_active_task"] = bool(task_probe.get("answer_to_active_task"))
    semantic["active_question"] = _df_text(task_probe.get("live_question"), 900)
    semantic["active_question_source"] = _df_text(
        task_probe.get("live_question_source") or "", 40
    )

    # ------------------------------------------------------------------
    # 8) Provider context is frozen here. Provider cannot select memory/branch.
    # ------------------------------------------------------------------
    provider_plan = _df_provider_plan(
        current,
        relation,
        turn_relation,
        semantic,
        task,
        previous_user,
        previous_april,
        sequence_id,
        render_plan,
        development,
        selected_memory,
        branch_digest_for_provider,
        active_context,
        dialogue_rules=dialogue_rules,
        related_branches=linked_branches,
    )

    branch_index = deepcopy(branches)
    if relation == "NEW" and sequence_id:
        branch_index["target_sequence_id"] = sequence_id
        branch_index["target_task_id"] = active_task_id
        branch_index["target_branch_id"] = f"{sequence_id}:{active_task_id}" if active_task_id else sequence_id
        branch_index["target_branch"] = {
            "branch_id": f"{sequence_id}:{active_task_id}" if active_task_id else sequence_id,
            "sequence_id": sequence_id,
            "task_id": active_task_id,
            "topic": _df_text(
                semantic.get("topic"),
                220,
            ),
            "canonical_entity": _df_text(
                semantic.get("entity"),
                180,
            ),
            "goal": _df_text(
                semantic.get("goal") or "answer",
                120,
            ),
            "branch_label": branch_label,
            "branch_type": "comparison" if turn_relation == "BRANCH_COMPARISON" else "topic",
            "linked_branch_ids": deepcopy(task.get("linked_branch_ids") or []) if isinstance(task, dict) else [],
            "internal_only": True,
            "active": True,
        }
        branch_index["resolution_mode"] = "NEW_TASK"
    elif relation == "RECALL" and selected_branch:
        branch_index["target_sequence_id"] = _df_text(
            selected_branch.get("sequence_id"),
            80,
        )
        branch_index["target_task_id"] = _df_text(selected_branch.get("task_id") or "", 100)
        active_task_id = _df_text(selected_branch.get("task_id") or active_task_id, 100)
        branch_index["target_branch_id"] = _df_text(
            selected_branch.get("branch_id")
            or (f"{selected_branch.get('sequence_id')}:{active_task_id}" if active_task_id else selected_branch.get("sequence_id")),
            120,
        )
        branch_index["target_branch"] = deepcopy(selected_branch)
        branch_index["resolution_mode"] = "RESUME_BRANCH"
    else:
        branch_index["resolution_mode"] = "ACTIVE_BRANCH"
    branch_index["active_sequence_id"] = sequence_id
    branch_index["target_task_id"] = active_task_id

    continuity_evidence = {
        "version": "dialogue_continuity_evidence_v1",
        "live_branch_exists": has_live_branch,
        "active_sequence_id": _df_text(
            active_sequence_digest.get("sequence_id")
            or active_seq_id,
            80,
        ),
        "branch_turn_count": int(
            active_sequence_digest.get("turn_count") or 0
        ),
        "short_turn": bool(dialogue_probe.get("short")),
        "confirmation": bool(dialogue_probe.get("confirmation")),
        "rejection": bool(dialogue_probe.get("rejection")),
        "deictic_reference": bool(dialogue_probe.get("deictic")),
        "direct_reference": bool(dialogue_probe.get("direct_reference")),
        "task_active": bool(task_probe.get("active")),
        "contextual_overlap": round(
            max(
                float(dialogue_probe.get("topic_overlap", 0.0) or 0.0),
                float(_df_overlap(current, active_sequence_digest.get("root_topic")) or 0.0),
                float(_df_overlap(current, active_sequence_digest.get("last_april")) or 0.0),
            ),
            6,
        ),
        "strong_topic_boundary": _df_strong_topic_boundary(current),
        "decision": relation,
        "decision_reason": turn_relation,
    }

    semantic_anchor = {
        "version": "semantic_anchor_v4_task_scoped",
        "branch_id": f"{sequence_id}:{active_task_id}" if active_task_id else sequence_id,
        "sequence_id": sequence_id,
        "task_id": active_task_id,
        "relation": relation,
        "turn_relation": turn_relation,
        "topic_root": _df_text(
            semantic.get("topic"),
            220,
        ),
        "active_focus": _df_text(
            active_sequence_digest.get("current_focus")
            or current,
            500,
        ),
        "primary_entity": _df_text(
            semantic.get("entity"),
            180,
        ),
        "reference_target": _df_text(
            selected_branch.get("canonical_entity")
            if selected_branch
            else "",
            180,
        ),
        "operation": _df_text(
            semantic.get("operation") or "answer",
            80,
        ),
        "goal": _df_text(
            semantic.get("goal") or "answer",
            100,
        ),
        "source": "contextual_dialogue_interpretation",
    }

    dialogue_contract = {
        "version": "april_dialogue_contract_v4_context_first",
        "relation": relation,
        "continuation": relation == "CONTINUE",
        "reference_to_previous": (
            relation == "RECALL"
            or dialogue_probe.get("direct_reference")
            or dialogue_probe.get("deictic")
        ),
        "context_dependency": (
            "active_dialogue_sequence"
            if relation == "CONTINUE"
            else "recalled_dialogue_sequence"
            if relation == "RECALL"
            else "current_turn_only"
        ),
        "turn_relation": turn_relation,
        "presentation_only": turn_relation == "DIALOGUE_RULE_UPDATE",
        "sequence_id": sequence_id,
        "task_id": active_task_id,
        "branch_label": branch_label,
        "internal_response_path": _df_internal_response_path(
            branch_label, int(task.get("response_count") or task.get("task_response_count") or 0)
        ),
        "target_task_id": _df_text(branch_index.get("target_task_id") or active_task_id, 100),
        "target_sequence_id": _df_text(
            branch_index.get("target_sequence_id")
            or sequence_id,
            80,
        ),
        "target_branch_id": _df_text(
            branch_index.get("target_branch_id"),
            80,
        ),
        "target_branch": deepcopy(
            branch_index.get("target_branch") or {}
        ),
        "canonical_topic": _df_text(
            semantic.get("topic"),
            220,
        ),
        "active_entity": _df_text(
            semantic.get("entity"),
            180,
        ),
        "resolved_entity": _df_text(
            semantic.get("entity"),
            180,
        ),
        "resolved_entity_source": (
            "recalled_dialogue"
            if relation == "RECALL"
            else "live_dialogue"
            if relation == "CONTINUE"
            else "current_turn"
        ),
        "resolved_request": current,
        "semantic_request": semantic.get("semantic_request") or current,
        "current_turn_role": _df_text(task_probe.get("live_input_role") or "current_turn", 80),
        "answer_to_active_task": bool(task_probe.get("answer_to_active_task")),
        "candidate_answer": _df_text(current, 1200) if task_probe.get("answer_to_active_task") else "",
        "active_question": _df_text(task_probe.get("live_question"), 900),
        "active_question_source": _df_text(task_probe.get("live_question_source") or "", 40),
        "selected_memory_index": -1,
        "selected_memory_operand": {},
        "selected_memory_record": {},
        "reference": relation == "RECALL",
        "active_task": deepcopy(task),
        "open_task": deepcopy(task),
        "interactive_task_state": deepcopy(task),
        "dialogue_rules": deepcopy(dialogue_rules),
        "dialogue_output_rule": deepcopy(dialogue_rules),
        "response_sequence": {
            "sequence_id": sequence_id,
            "task_id": active_task_id,
            "sequence_turn_index": int(active_sequence_digest.get("turn_count") or seq.get("turn_count") or 0) + 1,
            "branch_label": branch_label,
            "internal_response_path": _df_internal_response_path(
                branch_label, int(task.get("response_count") or task.get("task_response_count") or 0)
            ),
            "output_rule": {"visible": False, "internal_only": True},
        },
        "previous_result": deepcopy(task.get("last_result") or {}),
        "answer_basis": deepcopy(task.get("last_answer_basis") or task.get("answer_basis") or {}),
        "task_memory": {
            "qa_history": list(task.get("qa_history") or [])[-8:]
        } if task else {},
        "task_relation": {
            "handoff": task_probe.get("handoff"),
            "analysis": task_probe.get("answer_analysis"),
            "input_role": _df_text(task_probe.get("live_input_role") or "current_turn", 80),
            "answer_to_active_task": bool(task_probe.get("answer_to_active_task")),
            "active_question": _df_text(task_probe.get("live_question"), 900),
            "active_question_source": _df_text(task_probe.get("live_question_source") or "", 40),
            "active_question_score": float(task_probe.get("live_question_score", 0.0) or 0.0),
        },
        "task_action": bool(task_probe.get("task_action")),
        "task_transition": {
            "replace_task": bool(task_probe.get("handoff"))
        },
        "pending_resolved": False,
        "dialogue_development": development,
        "dialogue_strategy": {
            "mode": "context_first",
            "next_action": development.get("next_logical_step"),
        },
        "semantic_anchor": deepcopy(semantic_anchor),
        "active_sequence_digest": deepcopy(
            branch_digest_for_provider
        ),
        "linked_branches": deepcopy(linked_branches),
        "continuity_evidence": deepcopy(continuity_evidence),
        "dialogue_vector": {
            "version": "dialogue_vector_v4",
            "relation": relation,
            "three_way_relation": relation,
            "turn_relation": turn_relation,
            "continuation": relation == "CONTINUE",
            "conversation_continuation": relation == "CONTINUE",
            "canonical_topic": _df_text(
                semantic.get("topic"),
                220,
            ),
            "active_entity": _df_text(
                semantic.get("entity"),
                180,
            ),
            "branch_type": "comparison" if turn_relation == "BRANCH_COMPARISON" else "topic",
            "linked_branch_ids": [
                _df_text(x.get("branch_id") or x.get("task_id"), 120)
                for x in linked_branches
                if _df_text(x.get("branch_id") or x.get("task_id"), 120)
            ],
            "linked_branches": deepcopy(linked_branches),
            "sequence_id": sequence_id,
            "task_id": active_task_id,
            "active_task": deepcopy(task),
            "open_task": deepcopy(task),
            "interactive_task_state": deepcopy(task),
            "branch_label": branch_label,
            "internal_response_path": _df_internal_response_path(
                branch_label, int(task.get("response_count") or task.get("task_response_count") or 0)
            ),
            "target_task_id": _df_text(branch_index.get("target_task_id") or active_task_id, 100),
            "response_sequence": {
                "sequence_turn_index": int(active_sequence_digest.get("turn_count") or seq.get("turn_count") or 0) + 1,
                "branch_label": branch_label,
                "internal_response_path": _df_internal_response_path(
                    branch_label, int(task.get("response_count") or task.get("task_response_count") or 0)
                ),
                "output_rule": {"visible": False, "internal_only": True},
            },
            "dialogue_rules": deepcopy(dialogue_rules),
            "dialogue_output_rule": deepcopy(dialogue_rules),
            "previous_result": deepcopy(task.get("last_result") or {}),
            "answer_basis": deepcopy(task.get("last_answer_basis") or task.get("answer_basis") or {}),
            "target_sequence_id": _df_text(
                branch_index.get("target_sequence_id")
                or sequence_id,
                80,
            ),
            "target_branch_id": _df_text(
                branch_index.get("target_branch_id"),
                80,
            ),
            "target_branch": deepcopy(
                branch_index.get("target_branch") or {}
            ),
            "trajectory": {
                "root_topic": _df_text(
                    active_sequence_digest.get("root_topic")
                    or semantic.get("topic"),
                    220,
                ),
                "current_topic": _df_text(
                    semantic.get("topic"),
                    220,
                ),
                "turn_count": int(
                    active_sequence_digest.get("turn_count") or 0
                ),
            },
            "active_sequence_digest": deepcopy(
                branch_digest_for_provider
            ),
            "semantic_anchor": deepcopy(semantic_anchor),
            "branch_index": deepcopy(branch_index),
        },
    }

    semantic_frame = {
        "topic": semantic.get("topic"),
        "current_turn_role": _df_text(task_probe.get("live_input_role") or "current_turn", 80),
        "answer_to_active_task": bool(task_probe.get("answer_to_active_task")),
        "candidate_answer": _df_text(current, 1200) if task_probe.get("answer_to_active_task") else "",
        "active_question": _df_text(task_probe.get("live_question"), 900),
        "operation": semantic.get("operation"),
        "goal": semantic.get("goal"),
        "representation": semantic.get("representation"),
        "entity": semantic.get("entity"),
        "relation": relation,
        "understanding_stage": "complete_before_relation",
    }

    cognitive_workspace = {
        "version": "dialogue_workspace_v2_context_first",
        "relation": relation,
        "topic": semantic.get("topic"),
        "active_topic": semantic.get("topic"),
        "active_entity": semantic.get("entity"),
        "operation": semantic.get("operation"),
        "goal": semantic.get("goal"),
        "representation": semantic.get("representation"),
        "current_request": current,
        "resolved_request": current,
        "sequence_id": sequence_id,
        "task_continuation": bool(task) and relation in {"CONTINUE", "RECALL"},
        "active_task_context": deepcopy(task) if bool(task) else {},
        "task_id": active_task_id,
        "dialogue_rules": deepcopy(dialogue_rules),
        "dialogue_output_rule": deepcopy(dialogue_rules),
        "response_sequence": deepcopy(dialogue_contract.get("response_sequence") or {}),
        "semantic_frame": deepcopy(semantic_frame),
        "dialogue_development": deepcopy(development),
        "provider_context_plan": deepcopy(provider_plan),
        "active_sequence_digest": deepcopy(
            branch_digest_for_provider
        ),
        "continuity_evidence": deepcopy(continuity_evidence),
        "output_contract": deepcopy(render_plan),
        "protected_context": [
            "current_request",
            "dialogue_relation",
            "active_dialogue_trajectory",
            "active_task",
            "active_entity",
            "DIALOGUE_RULES",
            "RESPONSE_SEQUENCE",
            "TASK_RESULT_STATE",
            "render_plan",
        ],
        "excluded_context": [
            "full_history",
            "other_topic_branches",
            "unrelated_window_memory",
            "stale_global_entity",
        ],
    }

    result = {
        "runtime_version": _df_version,
        "type": semantic.get("representation") or "text",
        "operation": semantic.get("operation") or "answer",
        "object": semantic.get("entity") or semantic.get("representation") or "text",
        "goal": semantic.get("goal") or "answer",
        "representation": semantic.get("representation") or "text",
        "normalized_text": current,
        "canonical_user_request": current,
        "resolved_request": current,
        "semantic_request": semantic.get("semantic_request") or current,
        "semantic_frame": semantic_frame,
        "semantic_understanding": {
            "topic": semantic.get("topic"),
            "entity": semantic.get("entity"),
            "operation": semantic.get("operation"),
            "goal": semantic.get("goal"),
            "representation": semantic.get("representation"),
        },
        "dialogue_contract": dialogue_contract,
        "dialogue_relation": {
            **deepcopy(dialogue_contract),
            "source": "context_first_interpretation",
        },
        "semantic_anchor": deepcopy(semantic_anchor),
        "dialogue_vector": deepcopy(dialogue_contract["dialogue_vector"]),
        "three_way_relation": relation,
        "dialogue_subtype": turn_relation,
        "continuation": relation == "CONTINUE",
        "reference_to_previous": bool(
            dialogue_contract.get("reference_to_previous")
        ),
        "context_dependency": dialogue_contract["context_dependency"],
        "canonical_topic": semantic.get("topic"),
        "active_topic": semantic.get("topic"),
        "resolved_entity": semantic.get("entity"),
        "resolved_reference": _df_text(
            selected_branch.get("canonical_entity")
            if selected_branch
            else "",
            180,
        ),
        "interactive_task_state": deepcopy(task),
        "open_task": deepcopy(task),
        "task_id": active_task_id,
        "dialogue_rules": deepcopy(dialogue_rules),
        "dialogue_output_rule": deepcopy(dialogue_rules),
        "response_sequence": deepcopy(dialogue_contract.get("response_sequence") or {}),
        "previous_result": deepcopy(task.get("last_result") or {}),
        "answer_basis": deepcopy(task.get("last_answer_basis") or task.get("answer_basis") or {}),
        "task_memory": deepcopy(
            dialogue_contract.get("task_memory") or {}
        ),
        "task_relation": deepcopy(
            dialogue_contract.get("task_relation") or {}
        ),
        "current_turn_role": _df_text(task_probe.get("live_input_role") or "current_turn", 80),
        "answer_to_active_task": bool(task_probe.get("answer_to_active_task")),
        "active_question": _df_text(task_probe.get("live_question"), 900),
        "requested_outputs": list(
            render_plan.get("requested_outputs") or ["text"]
        ),
        "render_plan": deepcopy(render_plan),
        "interpretation_control": {
            "version": "interpretation_control_v3_context_first",
            "relation": relation,
            "render_authorized": bool(render_plan.get("authorized")),
            "render_mode": render_plan.get("mode"),
            "render_representations": list(
                render_plan.get("requested_outputs") or []
            ),
            "artifact_reference": bool(
                render_plan.get("artifact_reference")
            ),
            "operation": semantic.get("operation"),
            "representation": semantic.get("representation"),
        },
        "dialogue_development": development,
        "branch_label": branch_label,
        "internal_response_path": _df_internal_response_path(
            branch_label, int(task.get("response_count") or task.get("task_response_count") or 0)
        ),
        "linked_branches": deepcopy(linked_branches),
        "dialogue_branch_index": branch_index,
        "active_sequence_digest": deepcopy(
            branch_digest_for_provider
        ),
        "continuity_evidence": continuity_evidence,
        "cognitive_workspace": cognitive_workspace,
        "provider_context_plan": provider_plan,
        "continuation_content_analysis": {
            "active_entity": semantic.get("entity"),
            "active_topic": semantic.get("topic"),
            "same_branch": relation == "CONTINUE",
            "active_sequence_turn_count": int(
                active_sequence_digest.get("turn_count") or 0
            ),
            "task_id": active_task_id,
            "source": "contextual_dialogue_understanding",
        },
        "dialogue_strategy": {
            "mode": "context_first",
            "next_action": development.get("next_logical_step"),
        },
        "bigunoks": {
            "dialogue": dialogue_probe,
            "task": task_probe,
            "render": render_probe,
            "reference": {
                "deictic": dialogue_probe.get("deictic"),
                "direct": dialogue_probe.get("direct_reference"),
            },
            "role": "evidence_only",
        },
        "stage_order": [
            "REQUEST_RECEIPT",
            "ACTIVE_BRANCH_MEMORY",
            "CONTEXTUAL_UNDERSTANDING",
            "DIALOGUE_RELATION_RESOLUTION",
            "RESPONSE_DEVELOPMENT",
            "RENDER_PLAN",
            "PROVIDER_HANDOFF",
            "SCENE_CONTRACT",
        ],
        "provider_context_authority": "INTERPRETATION",
        "provider_must_not_reselect_context": True,
        "decision_owner": "INTERPRETATION_RUNTIME",
        "elapsed_ms": round(
            (time.perf_counter() - started) * 1000,
            3,
        ),
    }
    return result

# Canonical public entrypoint: one interpretation owner for production turns.
def interpret_request(
    text, cognition=None, semantic=None, history=None, state=None
):
    return _df_interpret_live_turn(text, history=history or [], state=state or {})

# Compatibility names for callers that used the previous public helpers.
DIALOGUE_FIRST_RUNTIME_VERSION = _df_version
DIALOGUE_FIRST_DECISION_OWNER = "INTERPRETATION_RUNTIME"
