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

# Active semantic working window.
# IMPORTANT: this is a sliding context window, NOT a memory deletion limit.
# Full authenticated 12h dialogue remains available in memory.
ACTIVE_DIALOGUE_WINDOW_PAIRS = 15

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

# Semantic values that can never own a topic/entity slot.
# They are discourse commands, grammatical pointers or generic placeholders.
# Keeping this list centralized prevents "Расскажи", "Так", "text", etc. from
# becoming persistent semantic entities when a turn is actually a continuation.
_DF_GENERIC_ENTITY_LABELS = {
    "так", "ну", "и", "а", "да", "нет", "это", "этот", "эта", "эту", "того", "той",
    "тот", "та", "те", "он", "она", "оно", "они", "его", "ее", "её", "их", "них",
    "расскажи", "раскажи", "скажи", "объясни", "покажи",
    "им", "ими", "что", "кто", "как", "где", "когда", "почему", "зачем",
    "можешь", "можно", "нужно", "надо", "давай", "расскажи", "скажи", "объясни",
    "покажи", "сделай", "создай", "построй", "проверь", "найди", "опиши",
    "напиши", "выдай", "укажи", "выбери", "ответь", "определи", "text",
    "image", "картинка", "изображение", "сцена", "схема", "график", "таблица",
    "формула", "код", "ссылка",
}

_DF_DISCOURSE_PREFIXES = (
    "так", "ну", "ага", "да", "хорошо", "ладно",
)

_DF_RELATION_DEFINITIONS = {
    "NEW": "NEW = новый самостоятельный смысловой предмет/диалоговая ветвь, введённый текущим запросом.",
    "CONTINUE": "CONTINUE = последовательное смысловое продолжение текущей диалоговой ветви; активный предмет сохраняется, а ссылка/уточнение добавляются к нему.",
    "RECALL": "RECALL = явный запрос вернуться к ранее сохранённому диалогу/ветви; историческая память выбирается только по явному указанию пользователя.",
}

def _df_is_generic_entity(value: Any) -> bool:
    low = _df_low(value)
    if not low:
        return True
    if low in _DF_GENERIC_ENTITY_LABELS:
        return True
    # Composite command labels such as "расскажи и что" are also not entities.
    toks = [t for t in re.findall(r"[a-zа-яёіїєґ0-9]+", low) if t]
    if toks and all(t in _DF_GENERIC_ENTITY_LABELS for t in toks):
        return True
    return False

def _df_strip_discourse_prefix(text: Any) -> str:
    value = _df_low(text)
    for _ in range(3):
        old = value
        value = re.sub(
            r"^(?:так|ну|ага|да|хорошо|ладно)\s*[,;:\-—]?\s+",
            "",
            value,
        )
        if value == old:
            break
    return value

_df_new_topic_markers = (
    "новая тема", "другая тема", "отдельная тема", "сменим тему", "перейдем к", "перейдём к",
    "давай теперь про", "давай теперь о", "а теперь про", "а теперь о", "теперь поговорим о",
    "кстати про", "кстати о", "хочу обсудить другую тему",
    "хочу предложить тебе игру", "хочу предложить игру", "давай сыграем",
    "начнем игру", "начнём игру", "давай поиграем",
)
_df_recall_markers = (
    "вернемся к", "вернёмся к", "вернись к", "вернись к теме", "вернись к разговору",
    "вспомни", "помнишь", "напомни", "что мы обсуждали", "о чем мы говорили",
    "о чём мы говорили", "о чем мы разговаривали", "о чём мы разговаривали",
    "про что мы говорили", "про что мы разговаривали", "что мы обсуждали",
    "что я спрашивал", "что я спрашивала", "что я просил", "что я просила",
    "какие темы мы обсуждали", "что было в нашем диалоге", "что было в нашем разговоре",
    "что мы тут обсуждали", "что мы здесь обсуждали", "о чем мы тут говорили",
    "о чём мы тут говорили", "что ты помнишь из нашего разговора",
)
_df_feedback_markers = (
    "мне нравится", "мне очень нравится", "мне понравилось", "мне очень понравилось",
    "понравилось", "нравится", "классно", "классная", "классный", "прикольно",
    "красиво", "отлично", "супер", "прекрасно", "здорово", "забавно",
    "круто", "огонь", "молодец", "спасибо", "благодарю",
)
_df_feedback_negative_markers = (
    "не нравится", "не понравилось", "плохо", "ужасно", "некрасиво",
    "не то", "не очень", "неудачно",
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
_df_deictic = re.compile(r"\b(?:это|этот|эта|эту|этого|этой|этим|он|она|оно|они|их|них|им|ими|обоих|обеих|его|ее|её|тот|та|те|там|здесь|выше|ниже|дальше|следующ(?:ий|ая|ее|ие|его|ую|им|ими)?|свой|свою|своего)\b", re.I)
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
    """Recognize a genuine request to recall the conversation as a whole.

    Memory recall is a semantic operation, not an entity/topic trigger. Natural
    formulations such as ``Расскажи о чем мы разговаривали`` must resolve to
    RECALL before subject extraction can manufacture a topic from the tail
    ``чем мы разговаривали``.
    """
    low = _df_low(text)
    if not low:
        return False

    if any(marker in low for marker in _df_recall_markers):
        return True

    conversational_recall = bool(re.search(
        r"^(?:расскажи|скажи|напомни|покажи|перечисли|выдай|вспомни)?\s*"
        r"(?:о\s+ч[её]м|про\s+что|что)\s+мы\s+"
        r"(?:тут\s+|здесь\s+)?(?:говорили|разговаривали|обсуждали|обсудили|обсуждаем)\b",
        low,
    ))
    if conversational_recall:
        return True

    summary_recall = bool(re.search(
        r"^(?:расскажи|скажи|напомни|покажи|перечисли|выдай)?\s*"
        r"(?:что\s+было|что\s+мы\s+делали|что\s+ты\s+помнишь|"
        r"какие\s+темы\s+(?:мы\s+)?(?:обсуждали|говорили))",
        low,
    ))
    if summary_recall:
        return True

    term_hits = sum(1 for term in _df_memory_scope_terms if term in low)
    action_hits = sum(1 for verb in _df_memory_scope_actions if re.search(rf"\b{re.escape(verb)}\b", low))
    explicit_window = bool(re.search(r"\b(?:двенадцат|12)[- ]?(?:час|ч)\w*\b", low))
    return bool(term_hits >= 1 and action_hits >= 1) or bool(explicit_window and term_hits >= 1 and action_hits >= 1)


def _df_explicit_recall(text: str) -> bool:
    return _df_memory_scope_request(text)


def _df_feedback_probe(
    text: str,
    *,
    canonical_turn: dict[str, Any] | None = None,
    previous_april: str = "",
) -> dict[str, Any]:
    """Detect a reaction to the immediately preceding canonical assistant action."""
    low = _df_low(text)
    canonical = canonical_turn if isinstance(canonical_turn, dict) else {}
    positive = any(x in low for x in _df_feedback_markers)
    negative = any(x in low for x in _df_feedback_negative_markers)
    if _df_explicit_recall(text) or not ((positive or negative) and (canonical or previous_april or len(_df_tokens(low)) <= 8)):
        return {"feedback": False, "sentiment": "", "target": {}, "reason": ""}
    scene = canonical.get("visual_scene") if isinstance(canonical.get("visual_scene"), dict) else {}
    topic = _df_text(canonical.get("topic") or canonical.get("canonical_topic") or scene.get("topic"), 220)
    entities = [_df_text(x, 180) for x in (canonical.get("entities") or []) if _df_text(x, 180)]
    target = {
        "type": "LAST_ASSISTANT_ACTION",
        "turn_id": _df_text(canonical.get("turn_id"), 120),
        "scene_id": _df_text(canonical.get("visual_scene_id") or scene.get("scene_id") or canonical.get("scene_id"), 160),
        "operation": _df_text(canonical.get("operation") or scene.get("operation"), 80),
        "topic": topic,
        "entities": entities[:4],
    }
    return {
        "feedback": True,
        "sentiment": "negative" if negative and not positive else "positive",
        "target": target,
        "reason": "user_reaction_to_previous_assistant_action",
    }


def _df_extract_subject(text: str) -> str:
    """Extract a real semantic subject; discourse commands never become entities."""
    value = _df_text(text, 1000)
    if not value:
        return ""
    low = _df_strip_discourse_prefix(value)

    # Conversation-memory questions are meta requests, never semantic subjects.
    if _df_memory_scope_request(low):
        return ""

    # Visual deictic requests ("эту сцену", "эту картинку") contain no new
    # semantic subject. The referenced result is resolved by the link engine.
    if re.match(
        r"^(?:а\s+)?(?:нарисуй|изобрази|сгенерируй|создай|покажи)\b.*\b"
        r"(?:эту|этот|это|такую|такой|тот|та)\s+"
        r"(?:сцену|картинку|изображение|рисунок|фото)\b",
        low,
    ):
        return ""

    # Visual plural deictics are references, not semantic operands.
    if re.match(r"^(?:а\s+)?(?:нарисуй|изобрази|сгенерируй|создай)\s+(?:их|них|обоих|обеих)\b", low):
        return ""

    quoted = re.search(r'[«"]([^»"]{2,180})[»"]', value)
    if quoted:
        candidate = _df_normalize_subject(quoted.group(1))
        return "" if _df_is_generic_entity(candidate) else candidate

    question_patterns = (
        r"^(?:продолжаем|продолжим|дальше|теперь)\s+что\s+такое\s+(.+)$",
        r"^что\s+такое\s+(.+)$",
        r"^(?:продолжаем|продолжим|дальше|теперь)\s+кто\s+такой\s+(.+)$",
        r"^кто\s+такой\s+(.+)$",
        r"^кто\s+(?:такая|такое|такие)\s+(.+)$",
        r"^кто\s+это\s+(.+)$",
        # Natural conversational form: "Расскажи кто такой Марти".
        r"^(?:расскажи|раскажи|скажи|объясни|покажи)\s+(?:кто\s+такой|кто\s+это|что\s+такое)\s+(.+)$",
    )
    for pattern in question_patterns:
        match = re.match(pattern, low, re.IGNORECASE)
        if match:
            candidate = _df_normalize_subject(match.group(1).strip(" .,!?:;—-\n"))
            if candidate and not _df_is_generic_entity(candidate):
                return _df_text(candidate, 180)

    # Command heads may be preceded by discourse words ("так", "ну", "да").
    command_heads = (
        r"назови", r"скажи", r"дай", r"выдай", r"укажи", r"выбери",
        r"напиши", r"приведи", r"расскажи", r"объясни", r"покажи",
        r"проверь", r"найди", r"опиши", r"создай", r"нарисуй", r"изобрази", r"сгенерируй",
        r"построй", r"рассчитай", r"посчитай", r"ответь", r"определи",
    )
    head = "(?:" + "|".join(command_heads) + ")"
    match = re.match(rf"^(?:а\s+)?{head}\s+(.+)$", low, re.IGNORECASE)
    if match:
        candidate = match.group(1).strip(" .,!?:;—-\n")
        candidate = re.sub(r"^(?:мне|меня|для\s+меня)\s+", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(
            r"^(?:про|об|о|насчет|насчёт|касаемо)\s+",
            "",
            candidate,
            flags=re.IGNORECASE,
        )
        candidate = re.sub(
            r"\s+(?:прописью|словами|подробно|кратко|пожалуйста|сейчас)$",
            "",
            candidate,
            flags=re.IGNORECASE,
        ).strip(" .,!?:;—-\n")
        if candidate:
            candidate = _df_normalize_subject(candidate)
            if not _df_is_generic_entity(candidate):
                return _df_text(candidate, 180)

    about = re.search(r"\b(?:про|об|о|насчет|насчёт|касаемо)\s+(.{2,180})", low)
    if about:
        candidate = about.group(1).strip(" .,!?:;—-\n")
        candidate = re.sub(
            r"\s+(?:расскажи|расскажите|объясни|объясните|покажи|покажите|напиши|опиши)$",
            "",
            candidate,
            flags=re.IGNORECASE,
        ).strip()
        if candidate and not _df_is_generic_entity(candidate):
            return _df_text(_df_normalize_subject(candidate), 180)

    # Proper names are useful only when they are genuine names, not discourse
    # words introduced by a command (e.g. "Так нарисуй...").
    ignored = {
        "теперь", "сейчас", "потом", "пожалуйста", "апрель", "я", "ты", "мы", "вы",
        "назови", "скажи", "расскажи", "кто", "что", "почему", "зачем", "как", "где",
        "когда", "сколько", "какой", "какая", "какое", "какие", "можешь", "можно",
        "нужно", "надо", "давай", *set(_DF_DISCOURSE_PREFIXES),
    }
    proper = re.findall(r"\b[А-ЯЁ][а-яё-]{2,}(?:\s+[А-ЯЁ][а-яё-]{2,}){0,2}\b", value)
    for candidate in reversed(proper):
        parts = candidate.split()
        if parts and parts[0].lower() not in ignored and not _df_is_generic_entity(candidate):
            return _df_text(candidate, 180)

    return ""

def _df_visual_reference_entity(
    text: str,
    previous_user: str = "",
    previous_april: str = "",
    state: dict[str, Any] | None = None,
) -> str:
    """Compatibility view over the semantic-link resolver."""
    link = _df_resolve_semantic_reference(
        text,
        state=state,
        active_topic="",
        active_entity="",
        visual_generation_memory=None,
    )
    target = link.get("target") if isinstance(link, dict) else {}
    return _df_text(
        target.get("entity")
        or target.get("subject")
        or "",
        220,
    )

def _df_canonical_subject_from_turn(canonical: dict[str, Any]) -> str:
    """Recover the real subject when legacy writers stored command words as entity."""
    if not isinstance(canonical, dict):
        return ""
    anchor = canonical.get("semantic_anchor")
    if isinstance(anchor, dict):
        for key in ("primary_entity", "topic_root", "active_focus"):
            value = _df_text(anchor.get(key), 220)
            if value and not _df_is_generic_entity(value):
                return _df_normalize_subject(value)

    # Never trust generic canonical entity mirrors.
    active = _df_text(canonical.get("active_entity"), 220)
    if active and not _df_is_generic_entity(active):
        return _df_normalize_subject(active)

    entities = [
        _df_normalize_subject(_df_text(x, 180))
        for x in (canonical.get("entities") or [])
        if _df_text(x, 180) and not _df_is_generic_entity(x)
    ]
    if entities:
        return entities[0]

    # The actual assistant/OpenAI answer is the strongest recovery source when
    # legacy canonical fields contain a command word such as "Раскажи" or a
    # visual-command tail such as "на картинке как она выглядит".
    answer = _df_text(canonical.get("april_answer") or canonical.get("summary"), 2200)
    if answer:
        proper = re.findall(
            r"\b[А-ЯЁ][а-яё-]{2,}(?:\s+[А-ЯЁ][а-яё-]{2,}){0,2}\b"
            r"|\b[A-Z][A-Za-z0-9-]{2,}(?:\s+[A-Z][A-Za-z0-9-]{2,}){0,2}\b",
            answer,
        )
        for candidate in proper:
            if not _df_is_generic_entity(candidate):
                return _df_normalize_subject(candidate)

    for source in (
        canonical.get("user_request"),
        canonical.get("request"),
        canonical.get("current_request"),
    ):
        candidate = _df_extract_subject(_df_text(source, 1000))
        if candidate and not _df_is_generic_entity(candidate):
            return candidate
    return ""


def _df_compact_semantic_answer(value: Any, limit: int = 1600) -> str:
    """Keep the previous OpenAI answer as semantic evidence for continuation."""
    text = _df_text(value, limit)
    if not text:
        return ""
    # Normalize whitespace without changing the answer's meaning.
    return re.sub(r"\s+", " ", text).strip()[:limit]


def _df_build_semantic_chain_context(
    *,
    previous_user: str,
    previous_april: str,
    current_user: str,
    active_topic: str,
    active_entity: str,
    relation: str,
    turn_relation: str,
    canonical_turn: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the canonical semantic chain used for the next OpenAI interpretation.

    The previous user question and the actual previous assistant/OpenAI answer are
    the semantic definition of the current entity/branch. The entity label remains
    only a compact anchor and can never replace the answer content.
    """
    canonical_turn = canonical_turn if isinstance(canonical_turn, dict) else {}
    if relation not in {"CONTINUE", "RECALL"}:
        entity = _df_text(active_entity or active_topic, 220)
        if _df_is_generic_entity(entity):
            entity = ""
        return {
            "version": "semantic_chain_v1",
            "available": False,
            "entity_definition": {
                "entity": entity,
                "topic": _df_text(active_topic, 220),
                "definition_source": "current_turn_only",
                "previous_user_question": "",
                "previous_openai_answer": "",
                "current_user_question": _df_text(current_user, 1200),
                "relation": relation,
                "turn_relation": turn_relation,
            },
            "previous_user_question": "",
            "previous_openai_answer": "",
            "current_user_question": _df_text(current_user, 1200),
            "chain": [{"role": "user", "content": _df_text(current_user, 1200)}],
            "continuation_instruction": "Не наследовать смысл предыдущего диалога: это новый смысловой предмет.",
            "provider_context_priority": "current_turn_only",
        }

    prev_q = _df_text(
        previous_user
        or canonical_turn.get("user_request")
        or canonical_turn.get("question")
        or canonical_turn.get("request"),
        1200,
    )
    prev_a = _df_compact_semantic_answer(
        previous_april
        or canonical_turn.get("april_answer")
        or canonical_turn.get("semantic_answer")
        or canonical_turn.get("answer")
        or canonical_turn.get("summary"),
        1600,
    )
    current_q = _df_text(current_user, 1200)
    entity = _df_text(active_entity or active_topic, 220)
    if _df_is_generic_entity(entity):
        entity = ""

    # This text is intentionally bounded: it is semantic evidence, not a second
    # full history. The model gets the exact order: user question -> answer -> next question.
    semantic_definition = {
        "entity": entity,
        "topic": _df_text(active_topic, 220),
        "definition_source": "previous_user_question_plus_openai_answer",
        "previous_user_question": prev_q,
        "previous_openai_answer": prev_a,
        "current_user_question": current_q,
        "relation": relation,
        "turn_relation": turn_relation,
    }

    chain = []
    if prev_q:
        chain.append({"role": "user", "content": prev_q})
    if prev_a:
        chain.append({"role": "assistant", "content": prev_a})
    chain.append({"role": "user", "content": current_q})

    return {
        "version": "semantic_chain_v2_dialogue_memory",
        "available": bool(prev_q or prev_a),
        "entity_definition": semantic_definition,
        "previous_user_question": prev_q,
        "previous_openai_answer": prev_a,
        "current_user_question": current_q,
        "chain": chain,
        "continuation_instruction": (
            "Интерпретируй текущий вопрос как продолжение только если его смысл связан "
            "с предыдущим вопросом и предыдущим ответом. Не создавай сущность из слов "
            "команды/дискурса. Смысл предыдущего ответа важнее названия entity. "
            "При RECALL сначала восстанови смысл последних диалоговых пар, затем кратко "
            "назови обсуждавшиеся темы и предложи продолжить выбранную тему."
        ),
        "provider_context_priority": "previous_answer_then_previous_question_then_active_memory_window_then_entity",
    }


def _df_build_openai_continuation_request(
    semantic_chain: dict[str, Any],
    *,
    relation: str,
) -> dict[str, Any]:
    """Return a provider-ready structured request for semantic continuation."""
    if not isinstance(semantic_chain, dict) or relation not in {"CONTINUE", "RECALL"}:
        return {}
    chain = list(semantic_chain.get("chain") or [])
    return {
        "version": "openai_semantic_continuation_request_v2_dialogue_memory",
        "mode": "CONTINUE_SEMANTIC_CHAIN" if relation == "CONTINUE" else "RECALL_DIALOGUE_MEMORY",
        "relation": relation,
        "messages": chain,
        "semantic_entity_definition": deepcopy(semantic_chain.get("entity_definition") or {}),
        "instruction": _df_text(semantic_chain.get("continuation_instruction"), 900),
        "memory_recall": {
            "enabled": relation == "RECALL",
            "use_latest_authenticated_15_pairs": relation == "RECALL",
            "operation": "summarize_recent_dialogue_then_offer_resume" if relation == "RECALL" else "continue_current_branch",
        },
        "do_not": [
            "do_not_reselect_memory_branch",
            "do_not_treat_command_words_as_entities",
            "do_not_replace_previous_answer_with_entity_label",
            "do_not_answer_an_old_question_instead_of_current_question",
            "do_not_claim_no_context_when_authenticated_dialogue_window_is_available",
        ],
        "answer_source_priority": [
            "active_memory_recall_window",
            "previous_openai_answer",
            "previous_user_question",
            "semantic_entity_definition.entity",
            "active_sequence_digest",
        ],
    }

def _df_resolve_semantic_reference(
    text: str,
    *,
    state: dict[str, Any] | None = None,
    active_topic: str = "",
    active_entity: str = "",
    visual_generation_memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Resolve deictic/elliptical language to a prior semantic result.

    The current utterance never becomes its own entity merely because it starts
    with a discourse word such as "так". Explicit new-topic markers still win.
    Visual references resolve to the latest authenticated visual result; generic
    pronouns resolve to the active semantic subject.
    """
    state = state if isinstance(state, dict) else {}
    low = _df_low(text)
    stripped = _df_strip_discourse_prefix(text)
    visual_ref = bool(re.search(
        r"\b(?:эту|этот|это|такую|такой|такие|ту|тот|та)\s+"
        r"(?:сцену|картинку|изображение|рисунок|фото|сцену)\b",
        low,
    )) or bool(re.search(
        r"\b(?:как\s+на\s+(?:картинке|изображении)|на\s+(?:ней|нём|нем)|эт[oa]й?\s+картин)\b",
        low,
    ))
    pronoun_ref = bool(re.search(
        r"\b(?:его|её|ее|их|них|ему|ей|им|ими|обоих|обеих|он|она|оно|они|этого|этим|этой|этому)\b",
        low,
    ))

    explicit_new = _df_strong_topic_boundary(text) or _df_explicit_recall(text)
    if explicit_new:
        return {}

    canonical = state.get("canonical_dialogue_turn") if isinstance(state.get("canonical_dialogue_turn"), dict) else {}
    canonical_subject = _df_canonical_subject_from_turn(canonical)

    # Visual result is a higher-order semantic object than a guessed entity.
    memory = visual_generation_memory if isinstance(visual_generation_memory, dict) else {}
    if visual_ref:
        prompt = _df_text(memory.get("generation_prompt"), 20000)
        scene_id = _df_text(memory.get("scene_id"), 120)
        request_anchor = _df_text(memory.get("request_anchor"), 1000)
        # If the fast path has no prompt, inspect the current/last successful
        # visual scene. These are semantic-result records, not arbitrary history.
        if not prompt:
            scene_candidates = [
                canonical.get("visual_scene"),
                state.get("current_visual_scene"),
                state.get("active_visual_scene"),
                state.get("last_successful_visual_scene"),
            ]
            scene = next(
                (x for x in scene_candidates if isinstance(x, dict)),
                {},
            )
            prompt = _df_text(
                scene.get("generation_prompt")
                or scene.get("image_prompt")
                or scene.get("prompt")
                or scene.get("semantic_generation_prompt"),
                20000,
            )
            scene_id = scene_id or _df_text(scene.get("scene_id"), 120)
            request_anchor = request_anchor or _df_text(
                scene.get("user_request") or scene.get("request_anchor") or scene.get("summary"),
                1000,
            )
        entity = canonical_subject or _df_text(active_entity, 220) or _df_text(active_topic, 220)
        return {
            "resolved": bool(prompt or scene_id or entity),
            "kind": "visual_result",
            "source": "latest_authenticated_visual_result",
            "reference_phrase": _df_text(text, 600),
            "target": {
                "entity": entity if not _df_is_generic_entity(entity) else "",
                "subject": entity if not _df_is_generic_entity(entity) else "",
                "scene_id": scene_id,
                "request_anchor": request_anchor,
                "generation_prompt": prompt,
            },
        }

    if pronoun_ref:
        entity = (
            canonical_subject
            or (_df_text(active_entity, 220) if not _df_is_generic_entity(active_entity) else "")
            or (_df_text(active_topic, 220) if not _df_is_generic_entity(active_topic) else "")
        )
        if entity:
            return {
                "resolved": True,
                "kind": "semantic_entity",
                "source": "latest_canonical_subject",
                "reference_phrase": _df_text(text, 600),
                "target": {"entity": entity, "subject": entity},
            }

    # Elliptical "дальше/продолжи/так нарисуй..." without an explicit noun:
    # preserve the active subject rather than inventing one.
    if stripped and (
        stripped in {"дальше", "продолжай", "продолжим", "продолжить", "далее"}
        or re.match(r"^(?:нарисуй|изобрази|создай|сгенерируй|покажи)\s+(?:еще|ещё|также|такую же)", stripped)
    ):
        entity = canonical_subject or (_df_text(active_entity, 220) if not _df_is_generic_entity(active_entity) else "")
        if entity:
            return {
                "resolved": True,
                "kind": "semantic_entity",
                "source": "active_sequence_subject",
                "reference_phrase": _df_text(text, 600),
                "target": {"entity": entity, "subject": entity},
            }
    return {}

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
    """Read the latest canonical pair; never scan the 12-hour archive on hot path."""
    state = state if isinstance(state, dict) else {}
    canonical = state.get("canonical_dialogue_turn")
    if isinstance(canonical, dict):
        user = _df_text(canonical.get("user_request"), 1200)
        april = _df_text(canonical.get("april_answer"), 2200)
        if user or april:
            return user, april
    anchor = state.get("dialogue_memory_anchor")
    if isinstance(anchor, dict):
        user = _df_text(anchor.get("user_request"), 1200)
        april = _df_text(anchor.get("april_answer"), 2200)
        if user or april:
            return user, april
    if isinstance(history, list):
        last_user = last_april = ""
        for item in reversed(history[-6:]):
            if not isinstance(item, dict):
                continue
            role = _df_low(item.get("role"))
            if not last_april and role in {"assistant", "april", "bot"}:
                last_april = _df_text(item.get("answer") or item.get("content") or item.get("summary") or item.get("text"), 2200)
            if not last_user and role in {"user", "human"}:
                last_user = _df_text(item.get("content") or item.get("text") or item.get("answer"), 1200)
            if last_user and last_april:
                return last_user, last_april
    seq = state.get("active_dialogue_sequence") if isinstance(state.get("active_dialogue_sequence"), dict) else {}
    return (
        _df_text(seq.get("last_user_request") or state.get("last_user_turn"), 1200),
        _df_text(seq.get("last_april_answer") or state.get("last_april_turn"), 2200),
    )

def _df_compact_active_sequence_digest(
    state: dict[str, Any],
    canonical_turn: dict[str, Any],
    sequence_id: str = "",
) -> dict[str, Any]:
    """Build the active dialogue digest from canonical state only."""
    state = state if isinstance(state, dict) else {}
    canonical_turn = canonical_turn if isinstance(canonical_turn, dict) else {}
    seq = state.get("active_dialogue_sequence") if isinstance(state.get("active_dialogue_sequence"), dict) else {}
    sid = _df_text(sequence_id or canonical_turn.get("sequence_id") or seq.get("sequence_id"), 80)
    tid = _df_text(canonical_turn.get("task_id") or seq.get("task_id"), 100)
    topic = _df_text(canonical_turn.get("topic") or canonical_turn.get("canonical_topic") or seq.get("topic"), 220)
    entities = [_df_text(x, 120) for x in (canonical_turn.get("entities") or []) if _df_text(x, 120)]
    entity = _df_text(canonical_turn.get("active_entity") or " и ".join(entities[:4]), 220)
    user = _df_text(canonical_turn.get("user_request") or seq.get("last_user_request"), 260)
    april = _df_text(canonical_turn.get("april_answer") or seq.get("last_april_answer"), 420)
    count = int(canonical_turn.get("sequence_turn_index") or seq.get("turn_count") or 0)
    row = {"turn": count, "task_id": tid, "user": user, "april": april, "topic": topic, "relation": _df_text(canonical_turn.get("relation") or canonical_turn.get("dialogue_relation"), 40).upper()}
    return {
        "version": "compact_canonical_digest_v2", "source": "canonical_dialogue_turn",
        "sequence_id": sid, "task_id": tid, "dialogue_window_hours": DIALOGUE_WINDOW_HOURS,
        "history_scope": "active_canonical_turn", "sequence_turn_count": count, "turn_count": count,
        "window_record_count": 1 if (user or april) else 0, "task_turn_count": 1 if tid and (user or april) else 0,
        "root_topic": topic, "current_topic": topic, "current_task_topic": topic, "current_focus": entity or topic,
        "last_user": user, "last_april": april, "previous_user": "", "previous_april": "",
        "last_result": deepcopy(canonical_turn.get("last_result") or {}), "answer_basis": deepcopy(canonical_turn.get("answer_basis") or {}),
        "dialogue_rules": deepcopy(seq.get("dialogue_rules") or {}), "topic_path": [topic] if topic else [],
        "recent_trajectory": [row] if (user or april) else [], "task_trajectory": [], "task_summaries": [],
        "coverage": "canonical_only", "window_complete": bool(sid), "other_branches_included": False, "full_history_included": False,
    }


def _df_active_sequence_digest(
    state: dict[str, Any],
    history: list[Any],
    sequence_id: str,
    *,
    limit: int = ACTIVE_DIALOGUE_WINDOW_PAIRS,
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
    target_count = max(1, min(int(limit or ACTIVE_DIALOGUE_WINDOW_PAIRS), ACTIVE_DIALOGUE_WINDOW_PAIRS))
    seen_rows = set()

    # The memory archive itself remains time-bounded elsewhere. On the hot path
    # we walk it backwards and materialize only the newest target_count pairs for
    # this authenticated sequence. This preserves response speed as the 12h archive
    # grows while keeping the working window dynamically sliding.
    day_indexes = sorted(
        (
            int(key.split("_", 1)[1])
            for key in timeline.keys()
            if isinstance(key, str) and key.startswith("day_") and key.split("_", 1)[1].isdigit()
        ),
        reverse=True,
    )
    for day_index in day_indexes:
        day = timeline.get(f"day_{day_index}")
        if not isinstance(day, dict):
            continue
        pairs = day.get("dialog_pairs", [])
        if not isinstance(pairs, list):
            continue
        for raw in reversed(pairs):
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
            row = {
                "sequence_turn_index": turn_index,
                "task_response_number": int(raw.get("task_response_number") or raw.get("response_count") or 0),
                "task_id": _df_text(raw.get("task_id"), 100),
                "created_at": created_at,
                "topic": _df_text(raw.get("sequence_topic") or raw.get("topic") or raw.get("canonical_topic"), 220),
                "user": _df_text(raw.get("user_request") or raw.get("user_meaning") or raw.get("user"), 260),
                "april": _df_text(raw.get("april_answer") or raw.get("april_meaning") or raw.get("answer") or raw.get("answer_summary"), 420),
                "relation": _df_text(raw.get("dialogue_relation") or raw.get("relation"), 40).upper(),
            }
            signature = (row["sequence_turn_index"], row["task_id"], row["user"], row["april"])
            if signature in seen_rows:
                continue
            seen_rows.add(signature)
            rows.append(row)
            if len(rows) >= target_count:
                break
        if len(rows) >= target_count:
            break

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

    # The complete 12h sequence remains in `rows`/`task_rows`.
    # Only the active semantic working view slides across the most recent
    # 15 pairs. No historical pair is deleted here.
    active_window_size = max(
        1,
        min(
            int(limit or ACTIVE_DIALOGUE_WINDOW_PAIRS),
            ACTIVE_DIALOGUE_WINDOW_PAIRS,
        ),
    )
    recent = rows[-active_window_size:]
    recent_task = task_rows[-active_window_size:]
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

    # Canonical post-Provider turn is the active semantic snapshot. Historical
    # task rows remain available in task_summaries, but their topics cannot leak
    # into current_topic/current_focus/current_task_topic.
    canonical = state.get("canonical_dialogue_turn") if isinstance(state.get("canonical_dialogue_turn"), dict) else {}
    canonical_topic = _df_text(canonical.get("topic"), 220)
    canonical_entity = _df_text(canonical.get("active_entity"), 220)
    canonical_user = _df_text(canonical.get("user_request"), 260)
    canonical_april = _df_text(canonical.get("april_answer"), 420)
    canonical_task_id = _df_text(canonical.get("task_id"), 100)
    if canonical_topic:
        root_topic = canonical_topic
        latest_topic = canonical_topic
        task_topic = canonical_topic
    if canonical_entity:
        task_entity = canonical_entity
    if canonical_task_id:
        tid = canonical_task_id
    if canonical_user:
        last_user = canonical_user
    if canonical_april:
        last_april = canonical_april

    return {
        "version": "active_sequence_digest_v5_12h_sequence_window",
        "source": "authenticated_active_sequence",
        "sequence_id": sid,
        "task_id": tid,
        "conversation_id": conversation_id,
        "user_id": user_id,
        "dialogue_window_hours": 12,
        "history_scope": "authenticated_12h_dialogue_sequence",
        "active_semantic_window_pairs": ACTIVE_DIALOGUE_WINDOW_PAIRS,
        "active_semantic_window_mode": "sliding",
        "sequence_turn_count": max(int(seq.get("turn_count") or 0), int((last_row or {}).get("sequence_turn_index") or 0)),
        "turn_count": max(int(seq.get("turn_count") or 0), int((last_row or {}).get("sequence_turn_index") or 0)),
        # Full live 12h records, not the 15-pair active view.
        "window_record_count": len(rows),

        # Explicit sliding semantic window used by downstream interpretation.
        "active_window_pair_limit": ACTIVE_DIALOGUE_WINDOW_PAIRS,
        "active_window_record_count": len(recent),
        "active_window_start_turn": (
            int(recent[0].get("sequence_turn_index") or 0)
            if recent else 0
        ),
        "active_window_end_turn": (
            int(recent[-1].get("sequence_turn_index") or 0)
            if recent else 0
        ),
        "active_window_sliding": True,
        "active_window_does_not_delete_history": True,

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
        "full_12h_memory_record_count": len(rows),
        "memory_retention_is_independent_of_active_window": True,
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
    """Return the real current semantic topic, never a stored command placeholder."""
    seq = state.get("active_dialogue_sequence") if isinstance(state.get("active_dialogue_sequence"), dict) else {}
    active_ctx = state.get("active_dialogue_context") if isinstance(state.get("active_dialogue_context"), dict) else {}
    anchor = state.get("dialogue_memory_anchor") if isinstance(state.get("dialogue_memory_anchor"), dict) else {}
    canonical = state.get("canonical_dialogue_turn") if isinstance(state.get("canonical_dialogue_turn"), dict) else {}
    for value in (
        canonical.get("topic"),
        anchor.get("topic"),
        active_ctx.get("topic"),
        seq.get("topic"),
        state.get("april_active_topic"),
        state.get("active_topic"),
        state.get("current_topic"),
    ):
        value = _df_text(value, 220)
        if value and not _df_is_generic_entity(value):
            return _df_normalize_subject(value)

    derived = _df_canonical_subject_from_turn(canonical)
    return derived if derived and not _df_is_generic_entity(derived) else ""

def _df_entity_from_state(state: dict[str, Any]) -> str:
    """Return the current semantic subject without legacy command words."""
    canonical = state.get("canonical_dialogue_turn") if isinstance(state.get("canonical_dialogue_turn"), dict) else {}
    derived = _df_canonical_subject_from_turn(canonical)
    if derived and not _df_is_generic_entity(derived):
        return derived
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
    feedback_probe: dict[str, Any] | None = None,
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

    explicit_new_boundary = _df_strong_topic_boundary(text)
    explicit_recall = _df_explicit_recall(text)
    # A declared new topic always starts a new branch. RECALL is only for a
    # request whose semantic purpose is to return to conversation memory.
    if explicit_new_boundary:
        return "NEW", "EXPLICIT_TOPIC_BOUNDARY"
    if explicit_recall:
        return "RECALL", "REFERENCE_OLD_TOPIC"

    feedback_probe = feedback_probe if isinstance(feedback_probe, dict) else {}
    if feedback_probe.get("feedback"):
        return "CONTINUE", "USER_FEEDBACK"

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
    semantic_link = semantic.get("reference_link") if isinstance(semantic.get("reference_link"), dict) else {}
    semantic_link_resolved = bool(semantic_link.get("resolved"))

    if _df_dialogue_repair_request(text):
        return "CONTINUE", "DIALOGUE_REPAIR"

    # A resolved semantic link is stronger than the generic lexical subject
    # (e.g. "Так" in "Так нарисуй на картинке эту сцену").
    # It means "act on the immediately referenced result", not "start a topic
    # named Так". Explicit NEW/RECALL boundaries were already handled above.
    if semantic_link_resolved:
        kind = _df_text(semantic_link.get("kind"), 80)
        if kind == "visual_result":
            return "CONTINUE", "VISUAL_REFERENCE_FOLLOWUP"
        return "CONTINUE", "SEMANTIC_REFERENCE_FOLLOWUP"

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
    if _df_is_generic_entity(current_subject):
        current_subject = ""
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
        # A complete self-contained subject outranks a stale interactive task.
        # This prevents "О Есенине расскажи" from being treated as an answer
        # to an unrelated question such as "Как тебя зовут?".
        fresh_subject = bool(current_subject)
        fresh_subject_match = bool(
            fresh_subject
            and subject_overlap < 0.20
            and not direct_reference
            and not deictic
        )
        if not fresh_subject_match:
            if task_probe.get("answer_to_active_task"):
                return "CONTINUE", "ACTIVE_TASK_ANSWER"
            if live_input_role == "followup_question_to_active_task":
                return "CONTINUE", "ACTIVE_TASK_FOLLOWUP_QUESTION"

    # A clear operand with no live-branch reference starts a new task even if an
    # older interactive question is still open. This is intentionally local and
    # avoids sending extra context to the Provider.
    if (
        current_subject
        and subject_overlap < 0.20
        and not direct_reference
        and not deictic
        and not _df_memory_scope_request(text)
    ):
        return "NEW", "SELF_CONTAINED_SUBJECT"

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

        # Structural dialogue rule: an utterance that has no independently
        # resolved subject remains inside the authenticated live branch. This is
        # intentionally semantic and not a vocabulary trigger: the same rule
        # works for natural inflections and new wording (e.g. "а в чём сюжет",
        # "а где это происходило", "почему так получилось").
        if (
            seq.get("sequence_id")
            and not _df_strong_topic_boundary(text)
            and not _df_explicit_recall(text)
            and not _df_extract_subject(text)
        ):
            return "CONTINUE", "SUBJECTLESS_LIVE_BRANCH"

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
    feedback_probe: dict[str, Any] | None = None,
    reference_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    low = _df_low(text)
    feedback_probe = feedback_probe if isinstance(feedback_probe, dict) else {}
    reference_context = reference_context if isinstance(reference_context, dict) else {}
    explicit_subject = _df_normalize_subject(_df_extract_subject(text))
    reference_target = reference_context.get("target") if isinstance(reference_context.get("target"), dict) else {}
    reference_entity = _df_text(
        reference_target.get("entity") or reference_target.get("subject"),
        220,
    )
    if _df_is_generic_entity(reference_entity):
        reference_entity = ""
    clean_active_entity = "" if _df_is_generic_entity(active_entity) else _df_text(active_entity, 180)
    clean_active_topic = "" if _df_is_generic_entity(active_topic) else _df_text(active_topic, 220)
    entity = explicit_subject or reference_entity or clean_active_entity

    if feedback_probe.get("feedback"):
        target = feedback_probe.get("target") if isinstance(feedback_probe.get("target"), dict) else {}
        target_entities = [x for x in (target.get("entities") or []) if x]
        return {
            "topic": _df_text(target.get("topic") or active_topic, 220),
            "entity": _df_text(" и ".join(target_entities) or active_entity, 180),
            "operation": "feedback", "goal": "acknowledge_user_reaction", "representation": "text",
            "semantic_request": _df_text(text, 1200), "explicit_subject": "",
            "reference_entity": _df_text(" и ".join(target_entities) or active_entity, 180),
            "feedback": deepcopy(feedback_probe),
        }

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
        # Memory recall is a meta-operation over the authenticated dialogue; it
        # must not overwrite the live topic with the phrase "диалоговая память".
        # Keep the active semantic identity alongside the recall operation so the
        # next ordinary turn can continue the same branch without a synthetic
        # topic/task being created.
        return {
            "topic": clean_active_topic or "диалоговая память",
            "entity": clean_active_entity,
            "operation": operation,
            "goal": goal,
            "representation": representation,
            "semantic_request": _df_text(text, 1200),
            "explicit_subject": "",
            "memory_recall": True,
            "memory_recall_scope": "authenticated_12h_active_sequence",
        }

    # A concrete subject in the current request is authoritative during
    # interpretation. Only an elliptical turn inherits the active topic/entity.
    if explicit_subject:
        topic = explicit_subject
        entity = explicit_subject
    elif reference_entity:
        topic = reference_entity
        entity = reference_entity
    elif relation in {"CONTINUE", "RECALL"} and clean_active_topic:
        topic = clean_active_topic
        entity = clean_active_entity
    else:
        topic = clean_active_topic or entity or _df_text(text, 180)

    if turn_relation in {"DIALOGUE_REPAIR", "DIALOGUE_RULE_UPDATE"}:
        topic = active_topic or topic
        entity = active_entity or ""
    elif turn_relation == "BRANCH_COMPARISON" and explicit_subject:
        topic = explicit_subject
        entity = explicit_subject

    semantic_request = _df_text(text, 1200)
    return {
        "topic": _df_text(topic, 220),
        "entity": "" if _df_is_generic_entity(entity) else _df_text(entity, 180),
        "operation": operation,
        "goal": goal,
        "representation": representation,
        "semantic_request": semantic_request,
        "explicit_subject": explicit_subject,
        "reference_link": deepcopy(reference_context) if reference_context else {},
        "semantic_relation_definition": _DF_RELATION_DEFINITIONS.get(
            relation, ""
        ),
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
    semantic_chain: dict[str, Any] | None = None,
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
    semantic_chain = semantic_chain if isinstance(semantic_chain, dict) else {}
    base = {
        "version": _df_provider_plan_version,
        "relation": relation,
        "turn_relation": turn_relation,
        "current_user_request": current_request,
        "current_request_authoritative": True,
        "context_selection_done_before_provider": True,
        "provider_must_not_reselect_context": True,
        "provider_continuation_contract": "Use SEMANTIC_CONTINUATION_CHAIN as the ordered semantic input when relation=CONTINUE/RECALL.",
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
                    "relation_definition": semantic.get("relation_definition") or _DF_RELATION_DEFINITIONS.get(relation, ""),
                    "semantic_link": deepcopy(semantic.get("semantic_link") or {}),
                    "semantic_chain": deepcopy(semantic_chain),
                    "entity_definition": deepcopy(semantic_chain.get("entity_definition") or {}),
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

    if relation in {"CONTINUE", "RECALL"}:
        # The active dialogue memory is authoritative for both live continuation
        # and explicit memory recall. Rendering/routing never selects context.
        # The current branch digest outranks topic-word similarity. It is the
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
        if semantic_chain.get("available"):
            base["required_context"].insert(3, {
                "key": "SEMANTIC_CONTINUATION_CHAIN",
                "priority": 0.998,
                "value": deepcopy(semantic_chain),
            })
        visual_memory_ref = semantic.get("previous_visual_generation_memory")
        if isinstance(visual_memory_ref, dict) and visual_memory_ref.get("available"):
            # Use only a compact excerpt in Provider context. The complete
            # generator prompt remains in the authenticated 12-hour pair.
            base["required_context"].insert(
                3,
                {
                    "key": "VISUAL_GENERATION_MEMORY",
                    "priority": 0.99,
                    "value": {
                        "available": True,
                        "source": "authenticated_dialogue_12h",
                        "full_prompt_available_in_history": True,
                        "request": _df_text(visual_memory_ref.get("user_request"), 600),
                        "prompt_excerpt": _df_text(
                            visual_memory_ref.get("prompt_excerpt"), 1200
                        ),
                        "scene_id": _df_text(visual_memory_ref.get("scene_id"), 120),
                        "semantic_reference": deepcopy(
                            semantic.get("semantic_link") or {}
                        ),
                        "dialogue_sequence_id": _df_text(
                            visual_memory_ref.get("dialogue_sequence_id"), 100
                        ),
                    },
                },
            )
        if task:
            base["required_context"].insert(
                5 if semantic_chain.get("available") and visual_memory_ref and visual_memory_ref.get("available") else 4,
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

    if relation == "RECALL" and active_sequence_digest:
        compact_recall_window = []
        for row in list(active_sequence_digest.get("recent_trajectory") or [])[-ACTIVE_DIALOGUE_WINDOW_PAIRS:]:
            if not isinstance(row, dict):
                continue
            compact_recall_window.append({
                "turn": int(row.get("turn") or 0),
                "topic": _df_text(row.get("topic"), 80),
                "user": _df_text(row.get("user"), 120),
                "april": _df_text(row.get("april"), 180),
                "relation": _df_text(row.get("relation"), 24),
            })
        base["required_context"].insert(0, {
            "key": "MEMORY_RECALL_CONTEXT",
            "priority": 1.0,
            "value": {
                "mode": "BROAD_DIALOGUE_RECALL" if not related_branches else "BRANCH_DIALOGUE_RECALL",
                "authenticated": True,
                "sequence_id": _df_text(active_sequence_digest.get("sequence_id") or sequence_id, 80),
                "window_hours": DIALOGUE_WINDOW_HOURS,
                "pair_limit": ACTIVE_DIALOGUE_WINDOW_PAIRS,
                "pairs": compact_recall_window[-ACTIVE_DIALOGUE_WINDOW_PAIRS:],
                "topics": list(active_sequence_digest.get("topic_path") or [])[-12:],
                "instruction": (
                    "Используй эти пары как фактическую память разговора. Определи "
                    "реально обсуждавшиеся темы, кратко напомни их пользователю и "
                    "предложи выбрать/продолжить одну из них. Не говори, что контекста "
                    "нет, если пары присутствуют. Не создавай новую тему из запроса "
                    "о памяти."
                ),
            },
        })

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
                    "priority": 0.999,
                    "value": deepcopy(active_sequence_digest),
                }
            )
            base["new_topic_minimal_context"] = False
        if semantic_chain.get("available"):
            base["required_context"].append({
                "key": "SEMANTIC_CONTINUATION_CHAIN",
                "priority": 0.998,
                "value": deepcopy(semantic_chain),
            })
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



def _df_latest_visual_generation_memory_fast(
    state: dict[str, Any],
    canonical_turn: dict[str, Any] | None,
) -> dict[str, Any]:
    """Read visual-generation memory from canonical state without scanning history."""
    canonical = canonical_turn if isinstance(canonical_turn, dict) else {}
    owners = [canonical]
    if isinstance(state, dict) and isinstance(state.get("dialogue_memory_anchor"), dict):
        owners.append(state.get("dialogue_memory_anchor"))
    for owner in owners:
        memory = owner.get("visual_generation_memory") if isinstance(owner, dict) else {}
        if isinstance(memory, dict) and _df_text(memory.get("generation_prompt"), 8):
            return deepcopy(memory)
    scene = canonical.get("visual_scene") if isinstance(canonical.get("visual_scene"), dict) else {}
    if not scene and isinstance(state, dict) and isinstance(state.get("last_successful_visual_scene"), dict):
        scene = state.get("last_successful_visual_scene")
    memory = scene.get("visual_generation_memory") if isinstance(scene, dict) else {}
    return deepcopy(memory) if isinstance(memory, dict) and _df_text(memory.get("generation_prompt"), 8) else {}


def _df_latest_visual_generation_memory(
    state: dict[str, Any],
    *,
    user_id: str = "",
    conversation_id: str = "",
    sequence_id: str = "",
) -> dict[str, Any]:
    """Read the latest full visual-generation envelope from authenticated 12h memory.

    The full generator prompt is deliberately kept in StateManager's existing
    ``day_0.dialog_pairs`` archive. Interpretation reads it only after the
    current authenticated scope is known; no second storage path is introduced.
    """
    if not isinstance(state, dict):
        return {}

    timeline = state.get("memory_timeline")
    day0 = timeline.get("day_0") if isinstance(timeline, dict) else {}
    pairs = day0.get("dialog_pairs") if isinstance(day0, dict) else []
    if not isinstance(pairs, list):
        return {}

    uid = _df_text(user_id or state.get("user_id") or (state.get("memory_scope") or {}).get("user_id"), 120)
    cid = _df_text(
        conversation_id
        or state.get("conversation_id")
        or (state.get("memory_scope") or {}).get("conversation_id"),
        120,
    )
    sid = _df_text(sequence_id, 100)
    now = time.time()

    for pair in reversed(pairs):
        if not isinstance(pair, dict):
            continue
        if uid and _df_text(pair.get("user_id"), 120) != uid:
            continue
        if cid and _df_text(pair.get("conversation_id"), 120) != cid:
            continue

        pair_sequence_id = _df_text(
            pair.get("dialogue_sequence_id") or pair.get("sequence_id"),
            100,
        )
        if sid and pair_sequence_id and pair_sequence_id != sid:
            continue

        created_at = pair.get("created_at")
        try:
            age = max(0.0, now - float(created_at))
        except (TypeError, ValueError):
            age = 0.0
        if age > USER_CONTENT_RETENTION_SECONDS:
            continue

        memory = pair.get("visual_generation_memory")
        if not isinstance(memory, dict):
            continue
        generation_prompt = _df_text(memory.get("generation_prompt"), 20000)
        if not generation_prompt:
            continue

        result = deepcopy(memory)
        # Authenticated pair scope is authoritative over any generator metadata.
        result["user_id"] = uid
        result["conversation_id"] = cid
        result["dialogue_sequence_id"] = pair_sequence_id or _df_text(
            memory.get("dialogue_sequence_id"), 100
        )
        result["history_created_at"] = float(created_at) if created_at is not None else now
        result["history_expires_after_hours"] = DIALOGUE_WINDOW_HOURS
        return result

    return {}


def _df_visual_generation_memory_reference(memory: dict[str, Any]) -> dict[str, Any]:
    """Build a provider-safe reference while keeping the full prompt in 12h memory."""
    if not isinstance(memory, dict):
        return {}
    prompt = _df_text(memory.get("generation_prompt"), 20000)
    if not prompt:
        return {}

    # The excerpt is evidence for relation/continuity only. The full prompt stays
    # in the authenticated memory archive and is never injected into the Image API.
    excerpt = prompt[:1200]
    return {
        "version": "visual_generation_memory_ref_v1",
        "available": True,
        "full_prompt_available_in_history": True,
        "memory_kind": "visual_generation_prompt",
        "source": "authenticated_dialogue_12h",
        "user_request": _df_text(memory.get("request_anchor"), 600),
        "prompt_excerpt": excerpt,
        "prompt_chars": len(prompt),
        "image_model_prompt_chars": int(memory.get("image_model_prompt_chars") or 0),
        "scene_id": _df_text(memory.get("scene_id"), 120),
        "turn_id": _df_text(memory.get("turn_id"), 120),
        "dialogue_sequence_id": _df_text(memory.get("dialogue_sequence_id"), 100),
        "expires_after_hours": DIALOGUE_WINDOW_HOURS,
    }


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
    canonical_turn = state.get("canonical_dialogue_turn") if isinstance(state.get("canonical_dialogue_turn"), dict) else {}
    canonical_derived_subject = _df_canonical_subject_from_turn(canonical_turn)
    canonical_topic_raw = _df_text(canonical_turn.get("topic"), 220)
    active_topic = (
        canonical_derived_subject
        if _df_is_generic_entity(canonical_topic_raw)
        else canonical_topic_raw
    ) or _df_topic_from_state(state)
    canonical_entities = canonical_turn.get("entities") if isinstance(canonical_turn.get("entities"), list) else []
    canonical_entity_raw = _df_text(canonical_turn.get("active_entity"), 220)
    active_entity = (
        canonical_entity_raw
        if canonical_entity_raw and not _df_is_generic_entity(canonical_entity_raw)
        else _df_text(" и ".join(str(x) for x in canonical_entities[:4] if not _df_is_generic_entity(x)), 220)
        or canonical_derived_subject
        or _df_entity_from_state(state)
    )
    active_context = state.get("active_dialogue_context") if isinstance(state.get("active_dialogue_context"), dict) else {}
    prior_task = _df_active_task(state)
    context_task = active_context.get("task") if isinstance(active_context.get("task"), dict) else {}
    context_task_id = _df_text(active_context.get("task_id") or context_task.get("task_id"), 100)
    prior_task_id = _df_text(prior_task.get("task_id"), 100) if isinstance(prior_task, dict) else ""
    if context_task and (not prior_task or not prior_task_id or not context_task_id or prior_task_id == context_task_id):
        prior_task = deepcopy(context_task)

    # A completed canonical turn owns the current branch. A task from an older
    # turn in the same 12h sequence is historical and cannot become the subject
    # of a new pronoun/reference just because it remains in task_registry.
    canonical_task_id = _df_text(canonical_turn.get("task_id"), 100)
    if canonical_task_id:
        candidate_task_id = _df_text(prior_task.get("task_id"), 100) if isinstance(prior_task, dict) else ""
        if candidate_task_id and candidate_task_id != canonical_task_id:
            prior_task = {}
        context_task_id = canonical_task_id

    active_seq_id = _df_text(seq.get("sequence_id"), 80)
    active_task_id = _df_text(
        canonical_turn.get("task_id")
        or seq.get("task_id")
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
    # 1) Canonical hot-path memory. Full 12h traversal is RECALL-only.
    # ------------------------------------------------------------------
    explicit_recall = _df_explicit_recall(current)
    visual_requested = bool(_df_render_probe(current).get("requested"))
    visual_generation_memory = _df_latest_visual_generation_memory_fast(state, canonical_turn)
    if not visual_generation_memory and not canonical_turn and visual_requested:
        visual_generation_memory = _df_latest_visual_generation_memory(
            state, user_id=user_id, conversation_id=conversation_id, sequence_id=active_seq_id,
        )
    visual_generation_memory_ref = _df_visual_generation_memory_reference(visual_generation_memory)
    # Ordinary continuation uses the same authenticated sliding window as RECALL.
    # The window is read-only context: it does not delete or replace the 12h archive.
    active_sequence_digest = _df_active_sequence_digest(
        state, history, active_seq_id,
        limit=ACTIVE_DIALOGUE_WINDOW_PAIRS,
        task_id=active_task_id,
    )
    if not active_sequence_digest.get("sequence_id"):
        active_sequence_digest = _df_compact_active_sequence_digest(
            state, canonical_turn, active_seq_id
        )
    digest_topic = _df_text(active_sequence_digest.get("current_topic"), 220)
    # The digest contains historical branch/task mirrors. Once a completed
    # post-Provider canonical turn exists, it is authoritative and the digest
    # must not overwrite it with an older task topic.
    if not canonical_turn and digest_topic and _df_low(digest_topic) not in {
        "если", "это", "такое", "такой", "так", "пронумеруй", "выдай", "проверь",
    }:
        active_topic = digest_topic

    # ------------------------------------------------------------------
    # 2) Cheap evidence probes. They cannot own relation or routing.
    # ------------------------------------------------------------------
    render_probe = _df_render_probe(current)
    task_probe = _df_task_probe(current, prior_task, active_topic, previous_april=previous_april)

    # Semantic links resolve before relation selection. A visual request may point
    # to the immediately preceding visual result ("эту сцену", "эту картинку"),
    # while ordinary pronouns bind to the current semantic subject.
    semantic_reference = _df_resolve_semantic_reference(
        current,
        state=state,
        active_topic=active_topic,
        active_entity=active_entity,
        visual_generation_memory=visual_generation_memory,
    )
    visual_ref_entity = ""
    if semantic_reference.get("resolved"):
        target = semantic_reference.get("target") if isinstance(semantic_reference.get("target"), dict) else {}
        resolved_ref_entity = _df_text(target.get("entity") or target.get("subject"), 220)
        if (
            _df_text(semantic_reference.get("kind"), 80) == "visual_result"
            and resolved_ref_entity
            and not _df_is_generic_entity(resolved_ref_entity)
        ):
            visual_ref_entity = resolved_ref_entity
            active_entity = resolved_ref_entity
            active_topic = resolved_ref_entity

    dialogue_probe = _df_dialogue_bigunok(
        current,
        previous_user,
        previous_april,
        active_topic,
        active_entity,
        task_probe,
    )
    feedback_probe = _df_feedback_probe(current, canonical_turn=canonical_turn, previous_april=previous_april)
    branches = (
        _df_branch_index(state, seq, active_topic, active_entity)
        if explicit_recall or _df_comparison_request(current)
        else {}
    )

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
    explicit_new_boundary = _df_strong_topic_boundary(current)
    explicit_recall = _df_explicit_recall(current)

    provisional_relation = (
        "NEW"
        if explicit_new_boundary
        else "RECALL"
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
        feedback_probe=feedback_probe,
        reference_context=semantic_reference,
    )
    if visual_ref_entity:
        # For a deictic image-edit request ("его/её/этого человека") the
        # resolved visual entity is authoritative. Do not let the generic
        # request parser turn phrases such as "на картинке его в профиль" into
        # the entity or let a stale interactive task win later.
        semantic["reference_entity"] = visual_ref_entity
        semantic["entity"] = visual_ref_entity
        semantic["topic"] = visual_ref_entity
        semantic["explicit_subject"] = ""

    # ------------------------------------------------------------------
    # 4) Now resolve the dialogue relation from the contextual understanding.
    # ------------------------------------------------------------------
    relation, turn_relation = _df_resolve_relation(
        current, state, previous_april, active_topic, active_entity, task_probe, dialogue_probe,
        feedback_probe=feedback_probe, semantic=semantic, sequence_digest=active_sequence_digest, branches=branches,
    )
    if semantic_reference.get("resolved") and relation != "RECALL":
        # The reference is an action on a prior result, not a new semantic topic.
        relation = "CONTINUE"
        turn_relation = (
            "VISUAL_REFERENCE_FOLLOWUP"
            if _df_text(semantic_reference.get("kind"), 80) == "visual_result"
            else "SEMANTIC_REFERENCE_FOLLOWUP"
        )
        target = semantic_reference.get("target") if isinstance(semantic_reference.get("target"), dict) else {}
        resolved_entity = _df_text(target.get("entity") or target.get("subject"), 220)
        if resolved_entity and not _df_is_generic_entity(resolved_entity):
            semantic["topic"] = resolved_entity
            semantic["entity"] = resolved_entity
            semantic["reference_entity"] = resolved_entity
        semantic["reference_link"] = deepcopy(semantic_reference)
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

    if turn_relation == "USER_FEEDBACK":
        # Feedback belongs to the last canonical assistant action. Never create a
        # new task/topic or consult an older branch for a short reaction.
        semantic["topic"] = _df_text(semantic.get("topic") or active_topic, 220)
        semantic["entity"] = _df_text(semantic.get("entity") or active_entity, 180)
        semantic["explicit_subject"] = ""
        semantic["feedback"] = deepcopy(feedback_probe)
        task = {}
        active_task_id = _df_text(canonical_turn.get("task_id") or seq.get("task_id") or "", 100)

    if turn_relation in {"DIALOGUE_REPAIR", "DIALOGUE_RULE_UPDATE"}:
        # Repair and presentation-rule changes belong to the existing dialogue
        # branch. Neither utterance is allowed to become a new topic/entity.
        semantic["topic"] = active_topic
        semantic["entity"] = active_entity
        semantic["explicit_subject"] = ""

    # A visual-reference follow-up continues the authenticated conversation,
    # but it is a new task action attached to the referenced visual entity.
    # Keep the outer dialogue relation as CONTINUE while ensuring the task fed
    # to Provider is no longer the stale interactive question branch.
    if visual_ref_entity:
        relation = "CONTINUE" if relation != "RECALL" else relation
        turn_relation = "VISUAL_REFERENCE_FOLLOWUP"
        semantic["reference_entity"] = visual_ref_entity
        semantic["entity"] = visual_ref_entity
        semantic["topic"] = visual_ref_entity
        semantic["explicit_subject"] = ""
        active_entity = visual_ref_entity
        active_topic = visual_ref_entity

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
            if _df_is_generic_entity(semantic["topic"]):
                semantic["topic"] = ""
            active_topic = semantic["topic"]
            active_entity = _df_normalize_subject(
                semantic.get("entity")
                or _df_extract_subject(current)
            )
            if _df_is_generic_entity(active_entity):
                active_entity = ""
            semantic["entity"] = active_entity
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

        semantic_entity = semantic.get("entity")
        if _df_is_generic_entity(semantic_entity):
            semantic_entity = ""
        semantic["entity"] = _df_text(
            active_entity if not _df_is_generic_entity(active_entity) else semantic_entity,
            180,
        )
        if _df_is_generic_entity(semantic.get("topic")):
            semantic["topic"] = active_topic if not _df_is_generic_entity(active_topic) else ""
        else:
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

    # RECALL may have selected a different sequence. Resolve the visual memory
    # against the final branch identity before building Provider context.
    visual_generation_memory = _df_latest_visual_generation_memory(
        state,
        user_id=user_id,
        conversation_id=conversation_id,
        sequence_id=sequence_id,
    ) or visual_generation_memory
    visual_generation_memory_ref = _df_visual_generation_memory_reference(
        visual_generation_memory
    )
    if visual_generation_memory_ref and relation in {"CONTINUE", "RECALL"}:
        semantic["previous_visual_generation_memory"] = deepcopy(
            visual_generation_memory_ref
        )

    # ------------------------------------------------------------------
    # 6) Response task/development planning.
    # ------------------------------------------------------------------
    live_role = _df_text(task_probe.get("live_input_role") or "current_turn", 80)
    if visual_ref_entity:
        # It remains a continuation of the same authenticated conversation, but
        # it is not an answer to the stale interactive question. The Provider
        # must see a visual-reference action instead of inheriting that task.
        live_role = "visual_reference_followup"
        turn_relation = "VISUAL_REFERENCE_FOLLOWUP"
        task_probe = dict(task_probe)
        task_probe["live_input_role"] = live_role
        task_probe["answer_to_active_task"] = False
        task_probe["task_action"] = True
    if relation == "CONTINUE" and not visual_ref_entity and live_role in {"answer_to_active_question", "followup_question_to_active_task"}:
        # The user's answer is payload for the existing task, not a new entity.
        # Preserve the task's semantic identity and carry the answer separately.
        semantic["topic"] = _df_text(prior_task.get("topic") or active_topic or semantic.get("topic"), 220)
        semantic["entity"] = _df_text(prior_task.get("entity") or active_entity or "", 180)
        if live_role == "answer_to_active_question":
            semantic["candidate_answer"] = current
    if relation == "RECALL":
        # Broad memory recall is not a new dialogue task. A specifically recalled
        # branch may carry its historical task; otherwise keep task state empty.
        recalled_task = selected_branch.get("active_task") if isinstance(selected_branch, dict) else None
        task = deepcopy(recalled_task) if isinstance(recalled_task, dict) and recalled_task else {}
    else:
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
        else "summarize_recent_dialogue_and_offer_resume"
    )
    if relation == "RECALL":
        development["memory_recall"] = {
            "broad": not bool(selected_branch),
            "pair_limit": ACTIVE_DIALOGUE_WINDOW_PAIRS,
            "window_hours": DIALOGUE_WINDOW_HOURS,
            "authenticated_sequence_required": True,
        }
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
    semantic["relation_definition"] = _DF_RELATION_DEFINITIONS.get(relation, "")
    semantic["memory_recall"] = {
        "requested": relation == "RECALL",
        "broad_conversation_recall": relation == "RECALL" and not bool(selected_branch),
        "active_window_pairs": ACTIVE_DIALOGUE_WINDOW_PAIRS if relation == "RECALL" else 0,
        "window_hours": DIALOGUE_WINDOW_HOURS if relation == "RECALL" else 0,
    }
    semantic["semantic_link"] = deepcopy(semantic_reference) if semantic_reference.get("resolved") else {}
    semantic["semantic_link_required_action"] = (
        "APPLY_TO_PREVIOUS_RESULT"
        if semantic_reference.get("resolved")
        else "NONE"
    )

    # The previous OpenAI answer + previous user question define the meaning of
    # the live entity. This is the canonical hand-off packet for the next model
    # call; entity is only an anchor, never the primary semantic payload.
    semantic_chain = _df_build_semantic_chain_context(
        previous_user=previous_user,
        previous_april=previous_april,
        current_user=current,
        active_topic=active_topic,
        active_entity=active_entity,
        relation=relation,
        turn_relation=turn_relation,
        canonical_turn=canonical_turn,
    )
    semantic["semantic_chain"] = deepcopy(semantic_chain)
    semantic["entity_definition"] = deepcopy(semantic_chain.get("entity_definition") or {})

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
        semantic_chain=semantic_chain,
    )
    openai_continuation_request = _df_build_openai_continuation_request(
        semantic_chain, relation=relation
    )
    if openai_continuation_request:
        provider_plan["openai_continuation_request"] = deepcopy(openai_continuation_request)

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
        "entity_definition": deepcopy(semantic.get("entity_definition") or {}),
        "semantic_chain": deepcopy(semantic.get("semantic_chain") or {}),
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
        "relation_definition": _DF_RELATION_DEFINITIONS.get(relation, ""),
        "semantic_link": deepcopy(semantic.get("semantic_link") or {}),
        "entity_definition": deepcopy(semantic.get("entity_definition") or {}),
        "semantic_chain": deepcopy(semantic.get("semantic_chain") or {}),
        "openai_continuation_request": deepcopy(openai_continuation_request),
        "previous_visual_generation_memory": deepcopy(
            visual_generation_memory_ref
        ) if relation in {"CONTINUE", "RECALL"} and visual_generation_memory_ref else {},
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
            "previous_visual_generation_memory": deepcopy(
                visual_generation_memory_ref
            ) if relation in {"CONTINUE", "RECALL"} and visual_generation_memory_ref else {},
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
        "feedback": deepcopy(feedback_probe) if feedback_probe.get("feedback") else {},
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
        "memory_recall": deepcopy(semantic.get("memory_recall") or {}),
        "semantic_chain": deepcopy(semantic.get("semantic_chain") or {}),
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
            "entity_definition",
            "semantic_chain",
            "openai_continuation_request",
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
        "resolved_request": (
            current
            + (f"\nVISUAL_REFERENCE_ENTITIES: {visual_ref_entity}" if visual_ref_entity else "")
        ),
        "visual_generation_request": (
            (
                f"{current}\nREF_VISUAL_RESULT_PROMPT: "
                f"{_df_text((semantic_reference.get('target') or {}).get('generation_prompt'), 20000)}"
            )
            if (
                semantic_reference.get("resolved")
                and _df_text(semantic_reference.get("kind"), 80) == "visual_result"
                and _df_text((semantic_reference.get("target") or {}).get("generation_prompt"), 8)
            )
            else (
                f"{current}. Применить предыдущий визуальный результат: {visual_ref_entity}."
                if visual_ref_entity
                else current
            )
        ),
        "semantic_request": semantic.get("semantic_request") or current,
        "semantic_frame": semantic_frame,
        "previous_visual_generation_memory": deepcopy(
            visual_generation_memory_ref
        ) if relation in {"CONTINUE", "RECALL"} and visual_generation_memory_ref else {},
        "semantic_understanding": {
            "topic": semantic.get("topic"),
            "entity": semantic.get("entity"),
            "operation": semantic.get("operation"),
            "goal": semantic.get("goal"),
            "representation": semantic.get("representation"),
            "relation": relation,
            "relation_definition": semantic.get("relation_definition") or _DF_RELATION_DEFINITIONS.get(relation, ""),
            "semantic_link": deepcopy(semantic.get("semantic_link") or {}),
            "entity_definition": deepcopy(semantic.get("entity_definition") or {}),
            "semantic_chain": deepcopy(semantic.get("semantic_chain") or {}),
        },
        "entity_definition": deepcopy(semantic.get("entity_definition") or {}),
        "semantic_chain": deepcopy(semantic.get("semantic_chain") or {}),
        "openai_continuation_request": deepcopy(openai_continuation_request),
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
        "relation_definition": semantic.get("relation_definition") or _DF_RELATION_DEFINITIONS.get(relation, ""),
        "semantic_link": deepcopy(semantic.get("semantic_link") or {}),
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


# ============================================================================
# TEST-ONLY REGRESSION: 15-pair SLIDING ACTIVE WINDOW
# ============================================================================

def _test_sliding_window(rows: list[dict[str, Any]], limit: int = ACTIVE_DIALOGUE_WINDOW_PAIRS) -> dict[str, Any]:
    """
    Pure test helper reproducing the exact active-window rule used by
    _df_active_sequence_digest:
      full rows survive;
      recent view contains at most 15 latest pairs;
      moving from 15 -> 16 rotates the window by one.
    """
    full = list(rows)
    size = max(1, min(int(limit or ACTIVE_DIALOGUE_WINDOW_PAIRS), ACTIVE_DIALOGUE_WINDOW_PAIRS))
    active = full[-size:]

    return {
        "full_count": len(full),
        "active_count": len(active),
        "active_first_turn": active[0]["sequence_turn_index"] if active else 0,
        "active_last_turn": active[-1]["sequence_turn_index"] if active else 0,
        "oldest_full_turn": full[0]["sequence_turn_index"] if full else 0,
        "latest_full_turn": full[-1]["sequence_turn_index"] if full else 0,
        "history_deleted": False,
        "sliding": True,
    }


def run_active_window15_regression() -> dict[str, Any]:
    rows = [
        {
            "sequence_turn_index": i,
            "user": f"user-{i}",
            "april": f"april-{i}",
        }
        for i in range(1, 21)
    ]

    checks = []
    for count in (1, 3, 15, 16, 20):
        result = _test_sliding_window(
            rows[:count]
        )
        expected_active = min(
            count,
            ACTIVE_DIALOGUE_WINDOW_PAIRS,
        )
        expected_first = (
            max(1, count - ACTIVE_DIALOGUE_WINDOW_PAIRS + 1)
            if count
            else 0
        )
        checks.append({
            "full_count": result["full_count"],
            "active_count": result["active_count"],
            "expected_active_count": expected_active,
            "active_first_turn": result["active_first_turn"],
            "expected_first_turn": expected_first,
            "history_deleted": result["history_deleted"],
            "passed": (
                result["active_count"] == expected_active
                and result["active_first_turn"] == expected_first
                and result["history_deleted"] is False
            ),
        })

    return {
        "engine": "active_dialogue_window_sliding_v1",
        "window_pairs": ACTIVE_DIALOGUE_WINDOW_PAIRS,
        "retention_hours": DIALOGUE_WINDOW_HOURS,
        "all_passed": all(
            x["passed"]
            for x in checks
        ),
        "checks": checks,
    }



# ============================================================================
# PRODUCTION PROCESSOR / EXECUTE BRIDGE
# IMPORTANT: this section is appended to the current semantic-chain runtime.
# It restores the public execute() contract consumed by bot.py without replacing
# the current semantic-link / semantic-answer interpretation code above.
# ============================================================================

import asyncio
import json
from dataclasses import asdict, is_dataclass
from typing import Awaitable, Callable, Optional

from blocks.C_ARTIFACT_CONTRACT import (
    MachineRequest,
    MachineResponse,
    build_machine_scene,
    build_scene_contract,
    build_scene_signal,
    BaseArtifact,
    create_artifact,
    create_diagram_artifact,
    build_room_route_contract,
    _artifact_canonical_render_blocks,
)
from blocks.april_personality import APRIL_IDENTITY
from blocks.provider_router import generate_text
from blocks.reasoning_state import build_turn_synchronization_snapshot
from blocks.goal_engine import build_goal_evidence, evaluate_goal_progress
from blocks.response_decision import build_completion_decision
from blocks.state_manager import get_state, update_scene_context, build_dialogue_memory_bridge
from blocks.presentation_formatter import canonical_payload_for_block, validate_render_block_payload
from blocks.rooms_registry import registry_route_machine_request

PROCESSOR_VERSION = "april_sequential_processor_v2_context_first_scene"
PROCESSOR_MODE = "ACTIVE_BRANCH_MEMORY_CONTEXT_UNDERSTANDING_RELATION_RESPONSE_RENDER_PROVIDER_SCENE"

_RENDERER_REGISTRY = {
    "text": "MessageTextBlock",
    "markdown": "MessageTextBlock",
    "formula": "FormulaRenderer",
    "code": "CodeBlock",
    "graph": "GraphBlock",
    "table": "TableBlock",
    "diagram": "DiagramRenderer",
    "image": "GalleryBlock",
    "gallery": "GalleryBlock",
    "link": "LinkCard",
    "file": "LinkCard",
}

_STRUCTURED_TYPES = {"code", "graph", "table", "diagram", "image", "gallery", "formula", "link"}

_PERSIST_TASKS: Dict[str, asyncio.Task] = {}


def _consume_persist_result(task: asyncio.Task) -> None:
    try:
        task.result()
    except BaseException as exc:
        if not isinstance(exc, asyncio.CancelledError):
            print("⚠️ APRIL BACKGROUND PERSIST:", exc)



def _text(value: Any) -> str:
    return str(value or "").strip()


def _as_dict(value: Any) -> Dict[str, Any]:
    """Safely normalize mapping-like semantic payloads to a dict.

    Executor calls this helper in several canonical request builders. The
    deployed path previously referenced it without defining it, causing every
    chat request reaching ProcessorScene.prepare() to fail with NameError.
    """
    if isinstance(value, dict):
        return value
    if is_dataclass(value) and not isinstance(value, type):
        try:
            converted = asdict(value)
            return converted if isinstance(converted, dict) else {}
        except Exception:
            return {}
    if hasattr(value, "items"):
        try:
            return dict(value.items())
        except Exception:
            return {}
    return {}


def _person_entity_from_answer(text: str) -> str:
    """Legacy compatibility stub; entity extraction is removed from production."""
    return ""

def _tokens(value: str) -> List[str]:
    return re.findall(r"[a-zа-яё0-9_]+", value.lower())


def _compact_task_state(value: Any) -> Any:
    """Compact task state without truncating the semantic Q&A trajectory.

    Generic scene compaction is intentionally small, but an interactive task
    is a state machine: its accumulated questions/answers are the evidence
    needed for a later solve/guess turn. Keep the bounded task history intact.
    """
    return _compact(value, depth=0, max_depth=6, max_items=16)


def _compact(value: Any, depth: int = 0, max_depth: int = 3, max_items: int = 6) -> Any:
    if depth > max_depth:
        return None
    if value in (None, "", [], {}):
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key, item in list(value.items())[:16]:
            cleaned = _compact(item, depth + 1, max_depth, max_items)
            if cleaned not in (None, "", [], {}):
                out[str(key)] = cleaned
        return out
    if isinstance(value, (list, tuple, set)):
        out = []
        for item in list(value)[:max_items]:
            cleaned = _compact(item, depth + 1, max_depth, max_items)
            if cleaned not in (None, "", [], {}):
                out.append(cleaned)
        return out
    return _text(value)


def _stable_id(prefix: str, payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"



def _provider_artifact_to_block(artifact: Any) -> Dict[str, Any]:
    """Convert a Provider artifact envelope into one canonical render block."""
    if not isinstance(artifact, dict):
        return {}

    kind = _text(
        artifact.get("type")
        or artifact.get("artifact_type")
        or artifact.get("kind")
        or artifact.get("representation")
    ).lower()
    kind = {
        "chart": "graph",
        "plot": "graph",
        "picture": "image",
        "photo": "image",
    }.get(kind, kind)
    if not kind:
        return {}

    payload = artifact.get("payload") if isinstance(artifact.get("payload"), dict) else {}
    data = artifact.get("data") if isinstance(artifact.get("data"), dict) else {}
    if not payload and data:
        payload = dict(data)

    if kind == "image" and isinstance(payload, dict):
        direct = (
            payload.get("src")
            or payload.get("url")
            or payload.get("image")
            or payload.get("image_data_uri")
        )
        if direct:
            payload.setdefault("src", direct)
            payload.setdefault("url", direct)
            payload.setdefault("image", direct)

    if not payload and kind in {"text", "markdown"}:
        content = _text(artifact.get("content") or artifact.get("text"))
        if content:
            return {
                "type": kind,
                "content": content,
                "text": content,
                "renderer": "MessageTextBlock",
                "viewer": "MessageTextBlock",
                "scene_contract": True,
                "human_visible": True,
            }

    if not payload:
        return {}

    renderer = _RENDERER_REGISTRY.get(kind, "MessageTextBlock")
    return {
        "type": kind,
        "artifact_type": kind,
        "payload": payload,
        "renderer": renderer,
        "viewer": renderer,
        "scene_contract": True,
        "human_visible": True,
        "block_id": _stable_id(f"provider-{kind}", payload),
    }


def _bridge_provider_artifacts(machine_response: dict) -> dict:
    """
    Bridge structured Provider output into render_blocks before SceneContract.

    Provider/Executor owns transport normalization; Web/RenderMessage remains the
    renderer owner. This path never invents content and only promotes payloads
    already returned by Provider.
    """
    if not isinstance(machine_response, dict):
        return machine_response

    existing = machine_response.get("render_blocks")
    existing = list(existing) if isinstance(existing, list) else []
    candidates: list[dict[str, Any]] = []

    scene = machine_response.get("scene")
    if isinstance(scene, dict):
        scene_blocks = scene.get("render_blocks") or scene.get("blocks") or []
        if isinstance(scene_blocks, list):
            candidates.extend(x for x in scene_blocks if isinstance(x, dict))

    for key in ("artifacts", "artifacts_payload"):
        values = machine_response.get(key)
        if isinstance(values, list):
            candidates.extend(x for x in values if isinstance(x, dict))

    # Provider may return a graph/chart as a top-level structured field while
    # emitting only its text companion in render_blocks. Promote that exact
    # payload into the canonical graph block BEFORE Room Register dispatch.
    # This is transport normalization only: no new provider call, no semantic
    # reinterpretation and no scene rebuild.
    top_level_structured = (
        ("graph", "graph"),
        ("chart", "graph"),
        ("plot", "graph"),
        ("table", "table"),
        ("formula", "formula"),
        ("diagram", "diagram"),
        ("image", "image"),
        ("gallery", "gallery"),
    )
    existing_candidate_types = {
        _text(item.get("type") or item.get("artifact_type") or item.get("representation")).lower()
        for item in existing
        if isinstance(item, dict)
    }
    existing_candidate_types.update(
        _text(item.get("type") or item.get("artifact_type") or item.get("representation")).lower()
        for item in candidates
        if isinstance(item, dict)
    )
    for source_key, canonical_kind in top_level_structured:
        value = machine_response.get(source_key)
        if value in (None, "", [], {}):
            continue
        if canonical_kind in existing_candidate_types:
            continue
        payload = value if isinstance(value, dict) else {source_key: value}
        candidates.append({
            "type": canonical_kind,
            "artifact_type": canonical_kind,
            "payload": payload,
            "renderer": _RENDERER_REGISTRY.get(canonical_kind, "MessageTextBlock"),
            "viewer": _RENDERER_REGISTRY.get(canonical_kind, "MessageTextBlock"),
            "scene_contract": True,
            "human_visible": True,
            "post_provider_resolved": True,
            "provider_source_field": source_key,
            "block_id": _stable_id(f"provider-{canonical_kind}", payload),
        })
        existing_candidate_types.add(canonical_kind)

    metadata = dict(machine_response.get("metadata") or {})
    for artifact in candidates:
        spec = artifact.get("image_generation_spec") if isinstance(artifact, dict) else None
        if isinstance(spec, dict) and "image_generation_spec" not in metadata:
            metadata["image_generation_spec"] = spec
    if metadata:
        machine_response["metadata"] = metadata

    seen = {
        json.dumps(
            {
                "type": _text(block.get("type")).lower(),
                "payload": block.get("payload", {}),
                "content": block.get("content", ""),
            },
            ensure_ascii=False,
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        )
        for block in existing
        if isinstance(block, dict)
    }

    bridged = list(existing)
    for candidate in candidates:
        block = (
            candidate
            if candidate.get("type") and (
                candidate.get("payload") or candidate.get("content") or candidate.get("renderer")
            )
            else _provider_artifact_to_block(candidate)
        )
        if not block:
            continue
        sig = json.dumps(
            {
                "type": _text(block.get("type")).lower(),
                "payload": block.get("payload", {}),
                "content": block.get("content", ""),
            },
            ensure_ascii=False,
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        )
        if sig not in seen:
            seen.add(sig)
            bridged.append(block)

    machine_response["render_blocks"] = bridged
    return machine_response


def _visual_hydration_key(block: Any) -> str:
    """Return a semantic key for image/diagram carriers of the same artifact.

    Provider responses can legally expose one visual artifact both in
    ``scene.render_blocks`` and in ``artifacts``.  Those are transport carriers,
    not two visible scene nodes.  The key intentionally ignores renderer/UI
    metadata and keeps only the visual payload identity.
    """
    if not isinstance(block, dict):
        return ""
    kind = _text(
        block.get("type") or block.get("artifact_type") or block.get("representation")
    ).lower()
    if kind not in {"image", "diagram"}:
        return ""

    payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
    if kind == "image":
        images = payload.get("images")
        if isinstance(images, list) and images:
            sources = []
            for item in images:
                if isinstance(item, dict):
                    source = (
                        item.get("src")
                        or item.get("url")
                        or item.get("image")
                        or item.get("image_data_uri")
                        or item.get("image_base64")
                    )
                    if source:
                        sources.append(str(source))
            if sources:
                return "image:" + hashlib.sha1(
                    json.dumps(sources, ensure_ascii=False, sort_keys=True).encode("utf-8")
                ).hexdigest()[:20]
        direct = (
            payload.get("src")
            or payload.get("url")
            or payload.get("image")
            or payload.get("image_data_uri")
            or payload.get("image_base64")
        )
        if direct:
            return "image:" + hashlib.sha1(str(direct).encode("utf-8")).hexdigest()[:20]
        return ""

    raw_nodes = payload.get("nodes") or payload.get("components") or payload.get("vertices") or []
    raw_edges = payload.get("edges") or payload.get("connections") or payload.get("relations") or payload.get("segments") or []

    nodes = []
    for node in raw_nodes if isinstance(raw_nodes, list) else []:
        if isinstance(node, dict):
            nodes.append({
                "id": str(node.get("id") or node.get("node_id") or node.get("name") or node.get("label") or ""),
                "label": str(node.get("label") or node.get("name") or node.get("title") or ""),
            })
        else:
            nodes.append({"id": str(node), "label": str(node)})

    edges = []
    for edge in raw_edges if isinstance(raw_edges, list) else []:
        if isinstance(edge, (list, tuple)) and len(edge) >= 2:
            source, target = edge[0], edge[1]
            label = ""
        elif isinstance(edge, dict):
            source = edge.get("from") or edge.get("source") or edge.get("start")
            target = edge.get("to") or edge.get("target") or edge.get("end")
            label = edge.get("label") or ""
        else:
            continue
        if source and target:
            edges.append({
                "from": str(source),
                "to": str(target),
                "label": str(label),
            })

    semantic = {
        "svg": payload.get("svg") or payload.get("svg_payload"),
        "nodes": nodes,
        "edges": edges,
        "geometry": payload.get("geometry"),
        "elements": payload.get("elements"),
        "points": payload.get("points"),
        "shapes": payload.get("shapes"),
    }
    if not any(value not in (None, "", [], {}) for value in semantic.values()):
        return ""
    return "diagram:" + hashlib.sha1(
        json.dumps(semantic, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:20]


def _hydrate_scene_artifacts(response: MachineResponse, request: MachineRequest) -> None:
    """Promote every concrete structured render block into the canonical artifact route.

    Image and diagram used to stop at ``render_blocks`` while graph/table could
    already participate in the artifact contract.  This bridge makes the
    artifact lifecycle uniform without changing the representation selected by
    Interpretation or the concrete Web renderer.
    """
    existing: list[BaseArtifact] = [
        item for item in list(getattr(response, "artifacts", []) or [])
        if isinstance(item, BaseArtifact)
    ]
    known_ids = {
        str(getattr(getattr(item, "metadata", None), "artifact_id", "") or "")
        for item in existing
    }

    room_for_type = {
        "image": "APRIL_IMAGES_GENERATION",
        "gallery": "C_GALLERY_ROOM",
        "diagram": "C_DIAGRAM_ROOM",
        "graph": "C_GRAPH_ROOM",
        "table": "C_TABLE_ROOM",
        "code": "C_FUNCTION_ROOM",
        "link": "C_LINK_ROOM",
        "formula": "C_FORMULA_ROOM",
    }

    hydrated_blocks: list[dict[str, Any]] = []
    seen_hydration_keys: set[str] = set()
    for raw in list(getattr(response, "render_blocks", []) or []):
        if not isinstance(raw, dict):
            continue
        kind = _text(raw.get("type") or raw.get("artifact_type") or raw.get("representation")).lower()
        if kind not in {"image", "diagram"}:
            continue

        payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}
        if kind == "image":
            has_source = any(payload.get(k) for k in ("src", "url", "image", "image_data_uri", "image_base64")) or bool(payload.get("images"))
            if not has_source:
                continue
        elif kind == "diagram":
            has_structure = any(
                payload.get(k) not in (None, "", [], {})
                for k in ("nodes", "edges", "geometry", "elements", "points", "segments", "svg", "svg_payload", "shapes")
            )
            if not has_structure:
                continue
        else:
            # Existing routes have their own structured validators; here we only
            # hydrate blocks that already contain meaningful payload data.
            if not payload and kind not in {"formula", "link"}:
                continue

        hydration_key = _visual_hydration_key(raw)
        if hydration_key and hydration_key in seen_hydration_keys:
            continue
        if hydration_key:
            seen_hydration_keys.add(hydration_key)

        try:
            if kind == "diagram":
                identity_payload = dict(payload)
                if raw.get("renderer") and identity_payload.get("renderer") is None:
                    identity_payload["renderer"] = raw.get("renderer")
                if raw.get("viewer") and identity_payload.get("viewer") is None:
                    identity_payload["viewer"] = raw.get("viewer")
                response_identity = {
                    "scene_id": getattr(response, "scene_id", ""),
                    "turn_id": getattr(response, "turn_id", ""),
                    "flow_id": getattr(response, "flow_id", ""),
                    "topic_group": getattr(response, "topic_group", ""),
                    "continuation": getattr(response, "continuation", False),
                }
                for key in ("scene_id", "turn_id", "flow_id", "topic_group", "continuation", "block_id", "render_id"):
                    candidate = raw.get(key) if raw.get(key) is not None else response_identity.get(key)
                    if candidate is not None and identity_payload.get(key) is None:
                        identity_payload[key] = candidate
                artifact = create_diagram_artifact(
                    semantic=raw.get("semantic") if isinstance(raw.get("semantic"), dict) else {},
                    payload=identity_payload,
                )
            else:
                data = {
                    "payload": payload,
                    "title": raw.get("title") or payload.get("title") or "",
                    "description": raw.get("description") or payload.get("description") or "",
                    "renderer": raw.get("renderer"),
                    "viewer": raw.get("viewer"),
                    "presentation": raw.get("presentation") if isinstance(raw.get("presentation"), dict) else {},
                    "scene_id": raw.get("scene_id") or getattr(response, "scene_id", ""),
                    "turn_id": raw.get("turn_id") or getattr(response, "turn_id", ""),
                    "flow_id": raw.get("flow_id") or getattr(response, "flow_id", ""),
                    "topic_group": raw.get("topic_group") or getattr(response, "topic_group", ""),
                    "continuation": raw.get("continuation") if raw.get("continuation") is not None else getattr(response, "continuation", False),
                    "block_id": raw.get("block_id"),
                    "render_id": raw.get("render_id"),
                    "human_visible": True,
                    "machine_only": False,
                }
                artifact = create_artifact(
                    artifact_type=kind,
                    room_source=room_for_type.get(kind, "C_ARTIFACT_CONTRACT"),
                    data=data,
                )

            artifact_id = str(getattr(getattr(artifact, "metadata", None), "artifact_id", "") or "")
            if artifact_id and artifact_id not in known_ids:
                existing.append(artifact)
                known_ids.add(artifact_id)
            elif not artifact_id:
                existing.append(artifact)

            # Re-project through the exact same canonical artifact->render-block
            # formatter used by every other room. This is the unification point.
            for block in _artifact_canonical_render_blocks(artifact):
                block = dict(block)
                if raw.get("scene_id") and not block.get("scene_id"):
                    block["scene_id"] = raw.get("scene_id")
                if raw.get("turn_id") and not block.get("turn_id"):
                    block["turn_id"] = raw.get("turn_id")
                if raw.get("flow_id") and not block.get("flow_id"):
                    block["flow_id"] = raw.get("flow_id")
                hydrated_blocks.append(block)
        except Exception as exc:
            print("⚠️ APRIL ARTIFACT HYDRATION:", kind, exc)

    if existing:
        response.artifacts = existing
        response.artifacts_payload = [
            deepcopy(getattr(item, "data", {}) or {}) for item in existing
        ]

    if hydrated_blocks:
        existing_signatures = {
            json.dumps({
                "type": _text(block.get("type")).lower(),
                "payload": block.get("payload", {}),
                "content": block.get("content", ""),
            }, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
            for block in list(response.render_blocks or []) if isinstance(block, dict)
        }
        merged = [
            block for block in list(response.render_blocks or [])
            if isinstance(block, dict)
            and _text(block.get("type") or block.get("artifact_type")).lower() not in {"image", "diagram"}
        ]
        for block in hydrated_blocks:
            sig = json.dumps({
                "type": _text(block.get("type")).lower(),
                "payload": block.get("payload", {}),
                "content": block.get("content", ""),
            }, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
            if sig not in existing_signatures:
                existing_signatures.add(sig)
                merged.append(block)
        for idx, block in enumerate(merged):
            block["sequence_index"] = idx
        response.render_blocks = merged


def _state_artifact_type(state: dict) -> str:
    artifact = state.get("last_artifact")
    if isinstance(artifact, dict):
        return _text(artifact.get("type") or artifact.get("artifact_type")).lower()
    scene = state.get("current_visual_scene")
    if isinstance(scene, dict):
        types = scene.get("render_block_types") or []
        if isinstance(types, list):
            for item in types:
                kind = _text(item).lower()
                if kind in _STRUCTURED_TYPES:
                    return kind
    return ""


class SequentialInterpretation:
    """Compatibility adapter; semantic interpretation owns dialogue relation."""

    def __init__(self) -> None:
        self.semantic_result: Dict[str, Any] = {}

    def dialogue(self, request: str, state: dict) -> Dict[str, Any]:
        """Read the single authoritative interpretation result.

        Executor does not reinterpret the turn and does not choose a second
        relation. It only projects the canonical runtime packet into the
        compatibility shape expected by the existing ProcessorScene code.
        """
        state = state if isinstance(state, dict) else {}
        history = state.get("dialog") if isinstance(state.get("dialog"), list) else []
        if not history and isinstance(state.get("dialogue_history"), list):
            history = state.get("dialogue_history")
        semantic_result = interpret_request(request, history=history, state=state)
        if not isinstance(semantic_result, dict):
            raise RuntimeError("INTERPRETATION_RETURNED_NO_PACKET")
        self.semantic_result = semantic_result

        contract = semantic_result.get("dialogue_contract") if isinstance(semantic_result.get("dialogue_contract"), dict) else {}
        vector = semantic_result.get("dialogue_vector") if isinstance(semantic_result.get("dialogue_vector"), dict) else {}
        workspace = semantic_result.get("cognitive_workspace") if isinstance(semantic_result.get("cognitive_workspace"), dict) else {}
        # Canonical dialogue state is the Interpretation three-way relation.
        # Topic-level evidence (NEW_TOPIC/SAME_TOPIC/CONTINUE_TOPIC/INDEPENDENT)
        # is never allowed to crash the production route. Keep it as evidence and
        # normalize only the execution state consumed by the existing processor.
        relation = _text(
            contract.get("three_way_relation")
            or semantic_result.get("three_way_relation")
            or vector.get("three_way_relation")
            or contract.get("relation")
            or vector.get("relation")
            or "NEW"
        ).upper()
        relation_alias = {
            "NEW_TOPIC": "NEW",
            "INDEPENDENT": "NEW",
            "SAME_TOPIC": "NEW",
            "CONTINUE_TOPIC": "CONTINUE",
            "CONTINUATION": "CONTINUE",
            "MEMORY_QUERY": "RECALL",
        }
        relation = relation_alias.get(relation, relation)
        if relation not in {"NEW", "CONTINUE", "RECALL"}:
            # Never turn an interpretation vocabulary mismatch into an empty Web
            # response. Fall back to the explicit continuation/reference flags
            # already owned by Interpretation.
            relation = (
                "RECALL" if bool(contract.get("reference_to_previous") or semantic_result.get("reference_to_previous"))
                else "CONTINUE" if bool(contract.get("continuation") or semantic_result.get("continuation"))
                else "NEW"
            )
        task_state = (
            semantic_result.get("interactive_task_state")
            if isinstance(semantic_result.get("interactive_task_state"), dict)
            else contract.get("interactive_task_state")
            if isinstance(contract.get("interactive_task_state"), dict)
            else {}
        )
        task_memory = semantic_result.get("task_memory") if isinstance(semantic_result.get("task_memory"), dict) else {}
        development = semantic_result.get("dialogue_development") if isinstance(semantic_result.get("dialogue_development"), dict) else {}
        return {
            "relation": relation,
            "continuation": relation == "CONTINUE",
            "reference": relation == "RECALL" or bool(contract.get("reference_to_previous")),
            "dependency": _text(contract.get("context_dependency") or ("recall" if relation == "RECALL" else "continuation" if relation == "CONTINUE" else "independent")),
            "anchor": "live_branch" if relation == "CONTINUE" else "recalled_branch" if relation == "RECALL" else "none",
            "pending_resolved": bool(semantic_result.get("pending_resolved")),
            "resolved_request": _text(semantic_result.get("resolved_request") or request),
            "resolved_reference": _text(semantic_result.get("resolved_reference") or ""),
            "resolved_entity": "",
            "resolved_entity_source": "disabled_pair_context",
            "active_entity": "",
            "continuation_content_analysis": semantic_result.get("continuation_content_analysis") if isinstance(semantic_result.get("continuation_content_analysis"), dict) else {},
            "dialogue_strategy": semantic_result.get("dialogue_strategy") if isinstance(semantic_result.get("dialogue_strategy"), dict) else {},
            "dialogue_development": _compact(development, max_depth=6, max_items=12),
            "continuation_authority": "INTERPRETATION_RUNTIME",
            "previous_user_turn": _text(contract.get("previous_user_turn") or vector.get("previous_user_turn") or ((semantic_result.get("provider_context_plan") or {}).get("required_context") or [{}])[0].get("value",{}).get("previous_user_turn") if isinstance(semantic_result.get("provider_context_plan"), dict) else ""),
            "previous_april_turn": _text(contract.get("previous_april_turn") or vector.get("previous_april_turn") or ""),
            "selected_memory_index": semantic_result.get("selected_memory_index", -1),
            "selected_memory_operand": vector.get("selected_memory_operand") or contract.get("selected_memory_operand") or {},
            "pair_first_match": deepcopy(semantic_result.get("pair_first_match") or {}),
            "response_formulation": deepcopy(semantic_result.get("response_formulation") or semantic_result.get("openai_request_formulation") or {}),
            "context_mode": _text(semantic_result.get("context_mode") or contract.get("context_mode") or ""),
            "dialogue_memory_window": deepcopy(semantic_result.get("dialogue_memory_window") or []),
            "dialogue_context_pairs": deepcopy(semantic_result.get("dialogue_context_pairs") or []),
            "trajectory": vector.get("trajectory") if isinstance(vector.get("trajectory"), dict) else {},
            "canonical_topic": _text(vector.get("canonical_topic") or contract.get("canonical_topic") or workspace.get("active_topic")),
            "active_task": task_state,
            "open_task": task_state,
            "interactive_task_state": task_state,
            "task_memory": task_memory,
            "task_relation": semantic_result.get("task_relation") or contract.get("task_relation") or {},
            "task_transition": contract.get("task_transition") or {},
            "task_action": bool(contract.get("task_action")),
            "sequence_id": _text(vector.get("sequence_id") or contract.get("sequence_id") or workspace.get("sequence_id")),
            "conversation_continuation": relation == "CONTINUE",
            "semantic_continuation": relation == "CONTINUE",
            "task_continuation": bool(task_state),
            "task_id": _text(vector.get("task_id") or contract.get("task_id") or task_state.get("task_id")),
            "target_task_id": _text(vector.get("target_task_id") or contract.get("target_task_id") or task_state.get("task_id")),
            "dialogue_rules": deepcopy(vector.get("dialogue_rules") or contract.get("dialogue_rules") or task_state.get("dialogue_rules") or {}),
            "response_sequence": deepcopy(vector.get("response_sequence") or contract.get("response_sequence") or {}),
            "previous_result": deepcopy(vector.get("previous_result") or contract.get("previous_result") or task_state.get("last_result") or {}),
            "answer_basis": deepcopy(vector.get("answer_basis") or contract.get("answer_basis") or task_state.get("last_answer_basis") or {}),
            "target_sequence_id": _text(vector.get("target_sequence_id") or contract.get("target_sequence_id") or vector.get("sequence_id") or contract.get("sequence_id")),
            "semantic_result": semantic_result,
        }

    def intent(self, request: str, state: dict, dialogue: Dict[str, Any]) -> Dict[str, Any]:
        """Compatibility projection only. Interpretation owns all decisions."""
        semantic_result = dialogue.get("semantic_result") if isinstance(dialogue.get("semantic_result"), dict) else self.semantic_result
        if not isinstance(semantic_result, dict):
            raise RuntimeError("INTERPRETATION_RESULT_MISSING")
        render_plan = semantic_result.get("render_plan") if isinstance(semantic_result.get("render_plan"), dict) else {}
        control = semantic_result.get("interpretation_control") if isinstance(semantic_result.get("interpretation_control"), dict) else {}
        representation = _text(semantic_result.get("representation") or semantic_result.get("production_representation") or render_plan.get("representation") or "text").lower()
        operation = _text(semantic_result.get("operation") or (semantic_result.get("semantic_task") or {}).get("operation") or "answer")
        goal = _text(semantic_result.get("goal") or (semantic_result.get("semantic_task") or {}).get("goal") or "answer")
        visual_generation_request = _text(semantic_result.get("visual_generation_request") or "")
        visual_generation_route = _text(semantic_result.get("visual_generation_route") or "")
        visual_generation_tier = _text(semantic_result.get("visual_generation_tier") or "")
        requested = [_text(x).lower() for x in (semantic_result.get("requested_outputs") or [representation]) if _text(x).strip()]
        if representation in {"image","gallery"}:
            requested=[representation]
        attrs={
            "visual_production_mode": visual_generation_route or ("image_generation" if representation in {"image","gallery"} else representation),
            "visual_generation_route": visual_generation_route,
            "visual_generation_tier": visual_generation_tier,
            "artifact_reference":bool(render_plan.get("artifact_reference")),
            "dialogue_relation":_text(dialogue.get("relation") or semantic_result.get("relation") or "NEW"),
            "sequence_id":_text(dialogue.get("sequence_id") or ""),
            "task":_compact(dialogue.get("active_task") or {}, max_depth=5, max_items=10),
        }
        intent=self._make_intent(operation, representation, representation, goal, "", attrs)
        intent.update({
            "requested_outputs":requested or [representation],
            "visual_generation_request":visual_generation_request,
            "production_representation_locked":True,
            "render_authorized":bool(render_plan.get("authorized") or representation in {"image","gallery","formula","diagram","graph","table","code","link","audio","video","file"}),
            "render_mode":_text(render_plan.get("mode") or control.get("render_mode") or ("IMAGE_GENERATION" if representation in {"image","gallery"} else representation.upper())),
            "interpretation_control":_compact(control, max_depth=4, max_items=12),
            "semantic_understanding":_compact(semantic_result.get("semantic_understanding") or {}, max_depth=5, max_items=10),
            "semantic_request":_text(semantic_result.get("semantic_request") or request),
            "semantic_result":semantic_result,
            "topic":"",
            "object":representation,
            "resolved_entity":"",
            "active_entity":"",
        })
        return intent

    @staticmethod
    def _make_intent(operation: str, object_name: str, representation: str, goal: str, topic: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "operation": _text(operation) or "answer",
            "object": _text(object_name) or representation,
            "representation": _text(representation) or "text",
            "goal": _text(goal) or "answer",
            "topic": _text(topic),
            "attributes": attributes,
        }

    @staticmethod
    def _representation(text: str) -> str:
        # This is only the Executor's compatibility view after semantic
        # interpretation.  Specific structured forms outrank the generic
        # "draw/create" modality, so "нарисуй это в схеме" remains a diagram
        # rather than collapsing to image.
        if re.search(r"\b(код|python|пайтон|скрипт)\b", text):
            return "code"
        if re.search(r"\b(ссыл\w*|url|link)\b", text):
            return "link"
        if re.search(r"\b(формул\w*|уравнени\w*)\b", text):
            return "formula"
        if re.search(r"\b(график|графика|кривую|кривая)\b", text):
            return "graph"
        if re.search(r"\b(таблиц\w*|табличк\w*)\b", text):
            return "table"
        if re.search(r"\b(схем\w*|блок-схем\w*)\b", text):
            return "diagram"
        if re.search(r"\b(нарисуй|изобрази|сгенерируй|создай)\b", text) or "картинк" in text or "изображени" in text or "портрет" in text:
            return "image"
        return "text"

    @staticmethod
    def _operation(text: str, representation: str) -> str:
        if representation == "link":
            return "retrieve"
        if any(w in text for w in ("измени", "исправь", "переделай", "добавь", "убери")):
            return "modify"
        if representation in _STRUCTURED_TYPES:
            return "build"
        if any(w in text for w in ("объясни", "расскажи", "почему", "что такое")):
            return "explain"
        return "answer"

    @staticmethod
    def _goal(operation: str, representation: str) -> str:
        if operation == "retrieve":
            return "obtain"
        if representation in _STRUCTURED_TYPES:
            return "present"
        if operation == "explain":
            return "understand"
        return "answer"

    @staticmethod
    def _object(text: str, representation: str) -> str:
        if representation == "link" and ("telegram" in text or "телеграм" in text):
            return "telegram_link"
        return {
            "code": "source_code",
            "image": "illustration",
            "graph": "graph",
            "table": "table",
            "diagram": "diagram",
            "formula": "formula",
            "link": "link",
        }.get(representation, "text")

    @staticmethod
    def _telegram_kind(text: str) -> str:
        if "канал" in text:
            return "channel"
        if "чат" in text:
            return "chat"
        if "пользователь" in text or "аккаунт" in text:
            return "user"
        if "официаль" in text:
            return "official"
        return "unspecified"

    @staticmethod
    def _telegram_target_present(text: str) -> bool:
        if re.search(r"https?://t\.me/[a-z0-9_]+", text):
            return True
        if re.search(r"@[a-z0-9_]{4,}", text):
            return True
        generic = {"дай", "ссылку", "на", "telegram", "телеграм"}
        return bool(set(_tokens(text)) - generic)


def _resolve_post_provider_render_blocks(machine_response: dict, request: MachineRequest) -> dict:
    """Resolve renderer blocks after Provider and before SceneContract.

    The request's frozen requested_outputs is the authority for representation.
    Provider structured payloads are preserved; no renderer is inferred from prose.
    """
    if not isinstance(machine_response, dict):
        return machine_response
    blocks = [dict(x) for x in (machine_response.get("render_blocks") or []) if isinstance(x, dict)]
    existing_types = {str(x.get("type") or x.get("artifact_type") or "").strip().lower() for x in blocks}
    requested = {str(x).strip().lower() for x in (request.requested_outputs or []) if str(x).strip()}
    renderer_map = {
        "formula": "FormulaRenderer",
        "graph": "GraphBlock",
        "table": "TableBlock",
        "diagram": "DiagramBlock",
        "image": "GalleryBlock",
        "gallery": "GalleryBlock",
        "code": "CodeBlock",
        "link": "LinkCard",
    }
    for kind, renderer in renderer_map.items():
        if kind not in requested or kind in existing_types or kind not in machine_response:
            continue
        value = machine_response.get(kind)
        if value in (None, "", [], {}):
            continue
        payload = value if isinstance(value, dict) else {kind: value}
        block = {
            "type": kind,
            "artifact_type": kind,
            "payload": payload,
            "renderer": renderer,
            "viewer": renderer,
            "scene_contract": True,
            "human_visible": True,
            "post_provider_resolved": True,
            "block_id": _stable_id(f"post-provider-{kind}", payload),
        }
        canonical = canonical_payload_for_block(block)
        if canonical:
            block["payload"] = canonical
        blocks.append(block)
        existing_types.add(kind)
    machine_response["render_blocks"] = blocks
    metadata = machine_response.setdefault("metadata", {})
    metadata["post_provider_render_resolution"] = {
        "stage": "AFTER_PROVIDER",
        "authority": "EXECUTOR_SCENE_CONTRACT",
        "requested_outputs": sorted(requested),
        "resolved_block_types": [
            str(x.get("type") or x.get("artifact_type") or "").lower()
            for x in blocks if isinstance(x, dict)
        ],
    }
    return machine_response


class ProcessorScene:
    def __init__(self, state: dict, user_id: str, request: str):
        self.state = state
        self.user_id = _text(user_id)
        self.request = _text(request)
        self.interpreter = SequentialInterpretation()
        self._render_omissions: list[dict[str, Any]] = []

    def prepare(self) -> MachineRequest:
        # Snapshot the operand before interpretation can update the live scene.
        # Artifact-continuation requests must resolve against the previous
        # successful visual result, never against the scene being constructed for
        # the current turn.
        prior_visual_scene = (
            dict(self.state.get("active_visual_scene"))
            if isinstance(self.state.get("active_visual_scene"), dict)
            else dict(self.state.get("current_visual_scene"))
            if isinstance(self.state.get("current_visual_scene"), dict)
            else {}
        )
        dialogue = self.interpreter.dialogue(self.request, self.state)
        intent = self.interpreter.intent(self.request, self.state, dialogue)

        # The semantic result/workspace is produced by Interpretation and must be
        # available before task ownership is resolved below.  Keep this binding
        # local to prepare() so the fast path never references it before assignment.
        semantic_result = (
            dialogue.get("semantic_result")
            if isinstance(dialogue.get("semantic_result"), dict)
            else {}
        )
        cognitive_workspace = (
            semantic_result.get("cognitive_workspace")
            if isinstance(semantic_result.get("cognitive_workspace"), dict)
            else {}
        )

        # Dialogue development is produced by Interpretation and must be bound
        # before it is inserted into the provider context/contract below.  The
        # previous revision referenced this name without defining it inside
        # prepare(), causing every web chat turn to fail with NameError.
        dialogue_development = (
            semantic_result.get("dialogue_development")
            if isinstance(semantic_result.get("dialogue_development"), dict)
            else {}
        )
        if not dialogue_development and cognitive_workspace:
            workspace_development = cognitive_workspace.get("dialogue_development")
            dialogue_development = (
                workspace_development
                if isinstance(workspace_development, dict)
                else {}
            )

        provider_context_plan = (
            semantic_result.get("provider_context_plan")
            if isinstance(semantic_result.get("provider_context_plan"), dict)
            else (
                cognitive_workspace.get("provider_context_plan")
                if isinstance(cognitive_workspace.get("provider_context_plan"), dict)
                else {}
            )
        )
        # Current request is immutable across the handoff. Derived semantic/request text
        # is a separate field and can never replace the raw authenticated user turn.
        if cognitive_workspace:
            cognitive_workspace["current_user_request"] = self.request
            cognitive_workspace["current_request_raw"] = self.request

        # Interpretation owns the dialogue relation. Executor records the decision
        # but never upgrades NEW -> CONTINUE merely because the representation is structured.
        # A new graph/table/image request is allowed to start a new semantic branch.
        interpretation_relation_audit = {
            "interpretation_relation": _text(dialogue.get("relation") or "NEW"),
            "interpretation_turn_relation": _text(
                dialogue.get("semantic_result", {}).get("turn_relation")
            ) if isinstance(dialogue.get("semantic_result"), dict) else "",
            "relation_overridden": False,
            "authority": "INTERPRETATION",
        }

        # Final semantic handoff: once the Processor has a resolved representation,
        # Interpretation remains the authority for render authorization.  This
        # closes the old gap where the representation was correctly resolved to
        # image/diagram/table but interpretation_control was empty, so Provider
        # was instructed to return text only.
        resolved_control = intent.get("interpretation_control") if isinstance(intent.get("interpretation_control"), dict) else {}
        relation = dialogue["relation"]

        requested_outputs = ["text"]
        required_artifacts: List[str] = []
        representation = intent["representation"]
        authorized_outputs = [
            _text(x).lower() for x in (intent.get("requested_outputs") or [])
            if _text(x).strip()
        ]
        if representation in {"image", "gallery"}:
            requested_outputs = [representation]
        elif bool(intent.get("render_authorized")) and authorized_outputs:
            for item in authorized_outputs:
                if item != "text" and item in _STRUCTURED_TYPES and item not in requested_outputs:
                    requested_outputs.append(item)

        # The current Interpretation representation is authoritative for the
        # current turn.  A stale requested_outputs list may come from an older
        # scene (for example graph/diagram left in dialogue memory) and must not
        # be allowed to suppress the current image/diagram artifact.
        if representation in _STRUCTURED_TYPES and representation not in requested_outputs:
            requested_outputs.append(representation)

        if representation in _STRUCTURED_TYPES and representation in requested_outputs:
            required_artifacts.append(representation)

        if intent["attributes"].get("telegram_pending"):
            # The answer is a clarification; the representation remains text
            # for this turn and pending state is persisted for the next turn.
            requested_outputs = ["text"]
            required_artifacts = []

        semantic_task_state = dialogue.get("interactive_task_state") if isinstance(dialogue.get("interactive_task_state"), dict) else {}
        active_sequence = self.state.get("active_dialogue_sequence") if isinstance(self.state.get("active_dialogue_sequence"), dict) else {}
        active_sequence_id = _text(active_sequence.get("sequence_id"))
        semantic_task_sequence_id = _text(semantic_task_state.get("sequence_id") or semantic_task_state.get("active_sequence_id"))
        task_sequence_ok = (
            not active_sequence_id
            or not semantic_task_sequence_id
            or semantic_task_sequence_id == active_sequence_id
        )
        if not task_sequence_ok:
            semantic_task_state = {}

        task_continuation = bool(cognitive_workspace.get("task_continuation")) if cognitive_workspace else bool(
            dialogue.get("task_continuation")
            or dialogue.get("task_action")
        )
        # Executor consumes only the task selected by Interpretation for the
        # authenticated active branch. Never resurrect a global/legacy task.
        active_task = semantic_task_state if task_continuation else {}
        pending_task = self.state.get("april_pending_task") if isinstance(self.state.get("april_pending_task"), dict) else {}
        pending_sequence_id = _text(pending_task.get("sequence_id") or pending_task.get("active_sequence_id"))
        if active_sequence_id and pending_sequence_id and pending_sequence_id != active_sequence_id:
            pending_task = {}
        if relation not in {"CONTINUE", "RECALL"} and not bool(dialogue.get("pending_resolved")):
            pending_task = {}

        resolved_request = _text(dialogue.get("resolved_request") or self.request)
        if dialogue["pending_resolved"] and pending_task and not dialogue.get("resolved_request"):
            base_topic = _text(pending_task.get("topic") or pending_task.get("representation"))
            resolved_request = f"Продолжение задания: {base_topic}. Ответ пользователя: {self.request}"

        history_lookup_mode = bool(
            dialogue.get("history_lookup")
            or _text(dialogue.get("context_mode")).upper() == "HISTORY_LOOKUP"
            or _text(semantic_result.get("context_mode")).upper() == "HISTORY_LOOKUP"
        )
        if relation == "CONTINUE":
            # Interpretation has already matched the authenticated 12h window.
            # Do not query memory again here. Carry only the 1..4 pairs selected
            # by the pair-first interpreter into the execution snapshot.
            selected_pairs = [
                dict(x) for x in (
                    dialogue.get("selected_context_pairs")
                    or dialogue.get("context_pairs")
                    or []
                )
                if isinstance(x, dict)
            ][:4]
            selected_pair = (
                dict(dialogue.get("selected_memory_operand"))
                if isinstance(dialogue.get("selected_memory_operand"), dict)
                else {}
            )
            if selected_pair and not selected_pairs:
                selected_pairs = [selected_pair]

            dialogue_memory = {
                "relation": "CONTINUE",
                "current_turn_only": False,
                "selection_source": "INTERPRETATION_PAIR_FIRST",
                "selected_sequence_id": _text(
                    dialogue.get("target_sequence_id")
                    or dialogue.get("sequence_id")
                ),
                "selected_records": selected_pairs,
                "dialogue_pairs": selected_pairs,
                "selected_pair_count": len(selected_pairs),
            }

            # Preserve the exact visual operand when it belongs to one of the
            # selected authenticated pairs. The image bytes/path are still attached
            # by the existing visual route, but no full 12h memory is forwarded.
            for pair in selected_pairs:
                visual = pair.get("visual_attachment")
                if isinstance(visual, dict) and visual:
                    dialogue_memory["visual_reference"] = dict(visual)
                    break

            dialogue_memory["history_lookup"] = False
            dialogue_memory["current_relation"] = relation

        elif history_lookup_mode:
            # A history-recall request is the one explicit exception where selected
            # history must be reconstructed. Keep it bounded and separate from the
            # ordinary CONTINUE route.
            dialogue_memory = build_dialogue_memory_bridge(
                self.user_id,
                query=self.request,
                limit=8,
                relation="RECALL",
                target_sequence_id=_text(
                    dialogue.get("target_sequence_id")
                    or dialogue.get("sequence_id")
                ),
                target_task_id=_text(
                    dialogue.get("target_task_id")
                    or (dialogue.get("active_task") or {}).get("task_id")
                    or semantic_result.get("task_id")
                ),
            )
            dialogue_memory["retrieval_mode"] = "HISTORY_LOOKUP"
            dialogue_memory["history_lookup"] = True
            dialogue_memory["current_relation"] = "NEW"

        else:
            dialogue_memory = {
                "relation": "NEW",
                "current_turn_only": True,
                "selection_source": "INTERPRETATION_PAIR_FIRST",
                "selected_sequence_id": _text(dialogue.get("sequence_id")),
                "selected_records": [],
                "dialogue_pairs": [],
                "history_lookup": False,
            }


        continuation_analysis = semantic_result.get("continuation_content_analysis") if isinstance(semantic_result.get("continuation_content_analysis"), dict) else {}
        dialogue_strategy = semantic_result.get("dialogue_strategy") if isinstance(semantic_result.get("dialogue_strategy"), dict) else {}
        resolved_entity = _text(
            cognitive_workspace.get("active_entity")
            or semantic_result.get("resolved_entity")
            or continuation_analysis.get("active_entity")
            or dialogue.get("resolved_reference")
            or self.state.get("april_active_entity")
        )

        # The semantic task is authoritative whenever an interactive task exists.
        # A replacement/new-task request may be NEW at the scene level but still
        # carries the newly created task frame to the provider.
        semantic_task_active = bool(
            isinstance(active_task, dict) and active_task.get("active")
        )
        turn_active_task = active_task if semantic_task_active else {
            "operation": intent.get("operation"),
            "object": intent.get("object"),
            "representation": intent.get("representation"),
            "goal": intent.get("goal"),
            "topic": dialogue.get("canonical_topic") or intent.get("topic") or intent.get("object"),
        }

        render_mode = _text(intent.get("render_mode") or "TEXT_ONLY").upper()
        selected_artifact = semantic_result.get("target_artifact") if isinstance(semantic_result.get("target_artifact"), dict) else {}
        selected_artifact = dict(selected_artifact)
        live_visual_scene = prior_visual_scene or (
            self.state.get("active_visual_scene")
            if isinstance(self.state.get("active_visual_scene"), dict)
            else self.state.get("current_visual_scene")
            if isinstance(self.state.get("current_visual_scene"), dict)
            else {}
        )
        artifact_context_only = (
            render_mode == "ARTIFACT_CONTINUATION"
            and bool(intent.get("render_authorized"))
        )

        # A visual artifact created earlier in the same authenticated 12-hour
        # dialogue is a real dialogue operand, not merely UI state. Keep its
        # renderer-neutral attachment alongside the semantic pair trajectory so
        # a follow-up such as "какими цветами он разукрашен" can reach the same
        # Provider/OpenAI route with the exact image.
        visual_reference_context = {}
        if relation == "CONTINUE" and isinstance(dialogue_memory.get("visual_reference"), dict):
            visual_reference_context = _compact(
                {
                    **dialogue_memory.get("visual_reference"),
                    "mode": "DIALOGUE_VISUAL_REFERENCE",
                    "dialogue_relation": relation,
                    "authenticated_user_id": self.user_id,
                    "sequence_id": _text(dialogue_memory.get("selected_sequence_id") or dialogue.get("sequence_id")),
                },
                max_depth=5,
                max_items=20,
            )

        # The visual reference is an operand selected from the authenticated
        # pair memory. Keep only compact metadata in the textual provider plan;
        # the actual image bytes/URL are attached separately by Provider in the
        # same OpenAI request.
        if visual_reference_context and isinstance(provider_context_plan, dict):
            required = provider_context_plan.setdefault("required_context", [])
            if not any(
                isinstance(item, dict) and _text(item.get("key")).upper() == "VISUAL_REFERENCE"
                for item in required
            ):
                required.append({
                    "key": "VISUAL_REFERENCE",
                    "priority": 0.995,
                    "value": {
                        "mode": "inspect_attached_visual_operand",
                        "scene_id": visual_reference_context.get("scene_id"),
                        "artifact_id": visual_reference_context.get("artifact_id"),
                        "source_turn": visual_reference_context.get("source_turn"),
                        "description": visual_reference_context.get("description") or "",
                    },
                })

        # The active visual scene is the canonical fallback operand when
        # Interpretation identified an artifact continuation but did not attach
        # a separate target_artifact object.  This keeps the operand inside the
        # same dialogue/SceneContract instead of inventing a second visual route.
        if artifact_context_only and not selected_artifact and live_visual_scene:
            visual_blocks = [
                block for block in (live_visual_scene.get("render_blocks") or live_visual_scene.get("blocks") or [])
                if isinstance(block, dict)
                and _text(block.get("type") or block.get("artifact_type") or "").lower() in _STRUCTURED_TYPES
            ]
            if visual_blocks:
                selected_artifact = {
                    "scene_id": live_visual_scene.get("scene_id"),
                    "type": _text(visual_blocks[-1].get("type") or visual_blocks[-1].get("artifact_type")),
                    "render_block": _compact(visual_blocks[-1], max_depth=6, max_items=10),
                    "source": "active_visual_scene",
                }

        selected_artifact_block = selected_artifact.get("render_block") if isinstance(selected_artifact.get("render_block"), dict) else {}
        artifact_visual_context = {}
        if artifact_context_only:
            artifact_visual_context = {
                "relation": relation,
                "mode": "ARTIFACT_CONTINUATION",
                "selected_artifact": _compact(selected_artifact, max_depth=4, max_items=6),
                "render_block": _compact(selected_artifact_block, max_depth=5, max_items=8),
            }
            if live_visual_scene:
                compact_scene = {
                    "scene_id": live_visual_scene.get("scene_id"),
                    "topic": live_visual_scene.get("topic"),
                    "render_block_types": live_visual_scene.get("render_block_types") or [],
                    "render_blocks": [
                        _compact(block, max_depth=5, max_items=8)
                        for block in (live_visual_scene.get("render_blocks") or live_visual_scene.get("blocks") or [])[:2]
                        if isinstance(block, dict)
                        and _text(block.get("type") or block.get("artifact_type") or "").lower() in _STRUCTURED_TYPES
                    ],
                }
                artifact_visual_context["active_visual_scene"] = compact_scene

        semantic_frame = dict(semantic_result.get("semantic_frame") or {})
        workspace_frame = (cognitive_workspace.get("semantic_frame")
                           if isinstance(cognitive_workspace.get("semantic_frame"), dict)
                           else {})
        semantic_frame.update({
            "topic": _text(
                workspace_frame.get("topic")
                or cognitive_workspace.get("active_topic")
                or intent.get("topic")
                or semantic_frame.get("topic")
                or representation
            ),
            "operation": _text(
                cognitive_workspace.get("operation")
                or workspace_frame.get("operation")
                or intent.get("operation")
                or semantic_frame.get("operation")
                or "answer"
            ),
            "goal": _text(
                cognitive_workspace.get("goal")
                or workspace_frame.get("goal")
                or intent.get("goal")
                or semantic_frame.get("goal")
                or "answer"
            ),
            "representation": _text(
                cognitive_workspace.get("representation")
                or workspace_frame.get("representation")
                or representation
                or semantic_frame.get("representation")
                or "text"
            ).lower(),
            "entity": _text(
                cognitive_workspace.get("active_entity")
                or workspace_frame.get("entity")
                or intent.get("object")
                or semantic_frame.get("entity")
            ),
            "relation": _text(
                cognitive_workspace.get("relation")
                or workspace_frame.get("relation")
                or dialogue.get("relation")
                or semantic_frame.get("relation")
                or "NEW"
            ).upper(),
        })
        semantic_result["semantic_frame"] = semantic_frame

        turn_sync = build_turn_synchronization_snapshot(self.request, self.state, semantic_result)
        goal_evidence = build_goal_evidence(self.request, self.state, semantic_result)
        closure_readiness = build_completion_decision(
            {
                **goal_evidence,
                "goal_completed": False,
                "closure": {
                    **(goal_evidence.get("closure") if isinstance(goal_evidence.get("closure"), dict) else {}),
                    "allowed_now": False,
                },
            },
            semantic_result,
        )

        visual_generation_request = _text(
            semantic_result.get("visual_generation_request")
            or dialogue.get("visual_generation_request")
            or ""
        ) if representation in {"image", "gallery"} else ""

        context = {
            "relation": relation,
            "continuation": bool(dialogue["continuation"]),
            "reference": bool(dialogue["reference"]),
            "dependency": dialogue["dependency"],
            "anchor": dialogue["anchor"],
            "active_task": _compact_task_state(turn_active_task),
            "interactive_task_state": _compact_task_state(
                dialogue.get("interactive_task_state") or active_task
            ),
            "task_memory": _compact_task_state(
                dialogue.get("task_memory") or {}
            ),
            "task_relation": _compact(dialogue.get("task_relation") or {}),
            "task_transition": _compact(dialogue.get("task_transition") or {}),
            "task_action": bool(dialogue.get("task_action")),
            "pending_task": _compact(pending_task),
            "active_entity": resolved_entity,
            "provider_context_plan": _compact(provider_context_plan, max_depth=7, max_items=14),
            "provider_context_authority": "INTERPRETATION",
            "interpretation_relation_audit": interpretation_relation_audit,
            "current_user_request": self.request,
            "visual_generation_request": visual_generation_request,
            "visual_reference_context": visual_reference_context,
            "semantic_request": _text(
                semantic_result.get("semantic_request")
                or _as_dict(semantic_result.get("semantic_understanding")).get("provider", {}).get("semantic_request")
                or resolved_request
            ),
            "semantic_understanding": _compact(semantic_result.get("semantic_understanding") or {}, max_depth=5, max_items=10),
            "continuation_content_analysis": _compact(continuation_analysis, max_depth=4, max_items=8),
            "dialogue_strategy": _compact(dialogue_strategy, max_depth=3, max_items=8),
            "live_scene": _compact(
                semantic_result.get("live_scene")
                or self.state.get("live_dialogue_scene")
                or self.state.get("scene_state")
                or {},
                max_depth=5,
                max_items=12,
            ),
            "dialogue_vector": _compact(
                semantic_result.get("dialogue_vector") or {},
                max_depth=5,
                max_items=12,
            ),
            "last_user_turn": _compact(self.state.get("last_user_turn", "")),
            "last_april_turn": _compact(self.state.get("last_april_turn", "")),
            "canonical_topic": _compact(dialogue.get("canonical_topic")),
            "dialogue_development": _compact(dialogue_development, max_depth=6, max_items=12),
            "sequence_id": _text(dialogue.get("sequence_id")),
            "target_sequence_id": _text(
                dialogue.get("sequence_id") or dialogue.get("target_sequence_id")
            ),
            "resolved_reference": _compact(dialogue.get("resolved_reference")),
            "selected_memory_index": dialogue.get("selected_memory_index", -1),
            "selected_memory_operand": _compact(dialogue.get("selected_memory_operand") or {}),
            "dialogue_trajectory": _compact(dialogue.get("trajectory") or {}),
            "active_dialogue_sequence": _compact(
                dialogue_memory.get("active_sequence") or {}
                if relation in {"CONTINUE", "RECALL"} and not artifact_context_only else {},
                max_depth=3,
                max_items=6,
            ),
            "active_dialogue_context": _compact(
                dialogue_memory.get("active_dialogue_context") or {},
                max_depth=6,
                max_items=12,
            ),
            "active_sequence_digest": _compact(
                dialogue_memory.get("active_sequence_digest") or {},
                max_depth=6,
                max_items=10,
            ),
            "active_sequence_turn_count": int(
                dialogue_memory.get("active_sequence_turn_count", 0) or 0
            ),
            "authenticated_dialogue_pair_count": len(
                dialogue_memory.get("dialogue_pairs") or dialogue_memory.get("active_sequence_turns") or []
            ),
            "dialogue_window_memory": _compact(
                dialogue_memory if relation in {"CONTINUE", "RECALL"} and not artifact_context_only else {
                    "window_hours": 12,
                    "turn_count_window": dialogue_memory.get("turn_count_window", 0),
                    "evidence_only": True,
                    "retrieval_mode": "artifact" if artifact_context_only else "none",
                    "selected_artifact": selected_artifact if artifact_context_only else {},
                },
                max_depth=5,
                max_items=6,
            ),
        }

        visual_mode = _text(intent["attributes"].get("visual_production_mode"))
        if not visual_mode:
            visual_mode = "text"


        # For a proven artifact continuation, the previous artifact is the
        # operand. A live sequence may contain a newer unrelated turn, so its
        # full conversational turns are intentionally withheld from Provider.

        # One continuous response budget for every representation.
        # The processor must not predict answer length from the renderer.
        # OpenAI may use any amount up to the canonical 8000-token ceiling;
        # the complete result is then passed to SceneContract and Web.
        output_budget = 8000

        dialogue_contract = {
            "version": "april_dialogue_contract_v3_context_first_branch_digest",
            "relation": relation,
            "continuation": bool(dialogue["continuation"]),
            "reference_to_previous": bool(dialogue["reference"]),
            "context_dependency": dialogue["dependency"],
            "active_task": _compact_task_state(turn_active_task),
            "open_task": _compact_task_state(dialogue.get("open_task") or active_task),
            "interactive_task_state": _compact_task_state(dialogue.get("interactive_task_state") or active_task),
            "active_sequence_digest": _compact(
                dialogue_memory.get("active_sequence_digest") or {},
                max_depth=6,
                max_items=10,
            ),
            "active_sequence_turn_count": int(
                dialogue_memory.get("active_sequence_turn_count", 0) or 0
            ),
            "authenticated_pair_trajectory": _compact(
                dialogue_memory.get("dialogue_pairs") or [],
                max_depth=3,
                max_items=5,
            ) if relation in {"CONTINUE", "RECALL"} else [],
            "visual_reference_context": visual_reference_context,
            "task_memory": _compact(dialogue.get("task_memory") or {}),
            "task_relation": _compact(dialogue.get("task_relation") or {}),
            "task_transition": _compact(dialogue.get("task_transition") or {}),
            "task_action": bool(dialogue.get("task_action")),
            "pending_task": _compact(pending_task),
            "active_entity": resolved_entity,
            "semantic_frame": _compact(semantic_result.get("semantic_frame") or {}, max_depth=3, max_items=8),
            "turn_sync": _compact(turn_sync, max_depth=4, max_items=10),
            "closure_policy": closure_readiness,
            "semantic_request": _text(
                semantic_result.get("semantic_request")
                or _as_dict(semantic_result.get("semantic_understanding")).get("provider", {}).get("semantic_request")
                or resolved_request
            ),
            "semantic_understanding": _compact(semantic_result.get("semantic_understanding") or {}, max_depth=5, max_items=10),
            "continuation_content_analysis": _compact(continuation_analysis, max_depth=4, max_items=8),
            "dialogue_strategy": _compact(dialogue_strategy, max_depth=3, max_items=8),
            "dialogue_development": _compact(dialogue_development, max_depth=6, max_items=12),
            "resolved_request": resolved_request,
            "canonical_topic": _compact(dialogue.get("canonical_topic")),
            "sequence_id": _text(dialogue.get("sequence_id")),
            "task_id": _text(dialogue.get("task_id") or (dialogue.get("active_task") or {}).get("task_id")),
            "target_task_id": _text(dialogue.get("target_task_id") or (dialogue.get("active_task") or {}).get("task_id")),
            "target_sequence_id": _text(dialogue.get("sequence_id") or dialogue.get("target_sequence_id")),
            "sequence_turn_index": int((dialogue_memory.get("active_sequence") or {}).get("turn_count", 0) or 0) + (1 if relation in {"NEW", "CONTINUE", "RECALL"} else 0),
            "dialogue_rules": _compact(dialogue.get("dialogue_rules") or {}, max_depth=3, max_items=8),
            "response_sequence": _compact(dialogue.get("response_sequence") or {}, max_depth=3, max_items=8),
            "previous_result": _compact(dialogue.get("previous_result") or {}, max_depth=4, max_items=8),
            "answer_basis": _compact(dialogue.get("answer_basis") or {}, max_depth=4, max_items=8),
            "resolved_reference": _compact(dialogue.get("resolved_reference")),
            "selected_memory_index": dialogue.get("selected_memory_index", -1),
            "selected_memory_operand": _compact(dialogue.get("selected_memory_operand") or {}),
            "visual_reference_context": visual_reference_context,
            "trajectory": _compact(dialogue.get("trajectory") or {}),
            "selected_artifact": _compact(selected_artifact, max_depth=5, max_items=6) if artifact_context_only else {},
            "active_dialogue_sequence": _compact(
                dialogue_memory.get("active_sequence") or {}
                if relation in {"CONTINUE", "RECALL"} and not artifact_context_only else {},
                max_depth=4,
                max_items=6,
            ),
            "dialogue_window_turns": _compact(
                dialogue_memory.get("active_sequence_turns") or []
                if relation == "CONTINUE" and not artifact_context_only else [],
                max_depth=5,
                max_items=6,
            ),
            "relevant_window_turns": _compact(
                dialogue_memory.get("relevant_window_turns") or []
                if relation == "RECALL" else [],
                max_depth=5,
                max_items=4,
            ),
            "semantic_authority": True,
            "current_user_request": self.request,
            "provider_context_plan": _compact(provider_context_plan, max_depth=7, max_items=14),
            "provider_context_authority": "INTERPRETATION",
            "provider_must_not_reselect_context": True,
        }

        memory_packet = {
            "mode": (
                "artifact_context" if artifact_context_only
                else "active_sequence" if relation == "CONTINUE"
                else "selected_window_thread" if relation == "RECALL"
                else "current_turn_only"
            ),
            "active_topic": _compact(dialogue.get("canonical_topic")) if relation != "NEW" else "",
            "active_goal": _compact(intent.get("goal")) if relation != "NEW" else "",
            "active_task": _compact_task_state(turn_active_task) if semantic_task_active else {},
            "task_id": _text(dialogue.get("task_id") or (turn_active_task or {}).get("task_id")),
            "dialogue_rules": _compact(dialogue.get("dialogue_rules") or (turn_active_task or {}).get("dialogue_rules") or {}, max_depth=3, max_items=8),
            "response_sequence": _compact(dialogue.get("response_sequence") or {}, max_depth=3, max_items=8),
            "previous_result": _compact(dialogue.get("previous_result") or (turn_active_task or {}).get("last_result") or {}, max_depth=4, max_items=8),
            "answer_basis": _compact(dialogue.get("answer_basis") or (turn_active_task or {}).get("last_answer_basis") or {}, max_depth=4, max_items=8),
            "active_dialogue_context": _compact(
                dialogue_memory.get("active_dialogue_context") or {},
                max_depth=6,
                max_items=12,
            ),
            "interactive_task_state": _compact_task_state(dialogue.get("interactive_task_state") or active_task) if semantic_task_active else {},
            "task_memory": _compact_task_state(dialogue.get("task_memory") or {}) if semantic_task_active else {},
            "task_relation": _compact(dialogue.get("task_relation") or {}) if semantic_task_active else {},
            "semantic_request": _text(
                semantic_result.get("semantic_request")
                or _as_dict(semantic_result.get("semantic_understanding")).get("provider", {}).get("semantic_request")
                or resolved_request
            ),
            "semantic_understanding": _compact(semantic_result.get("semantic_understanding") or {}, max_depth=5, max_items=10),
            "pending_task": _compact(pending_task) if pending_task else {},
            "last_artifact_type": _state_artifact_type(self.state) if relation == "CONTINUE" and render_mode == "ARTIFACT_CONTINUATION" else "",
            "selected_artifact": _compact(selected_artifact, max_depth=5, max_items=6) if artifact_context_only else {},
            "visual_reference_context": visual_reference_context,
            "dialogue_sequence": _compact(
                dialogue_memory.get("active_sequence") or {}
            ) if relation in {"CONTINUE", "RECALL"} and not artifact_context_only else {},
            "active_sequence_digest": _compact(
                dialogue_memory.get("active_sequence_digest") or {}
            ) if relation in {"CONTINUE", "RECALL"} and not artifact_context_only else {},
            "active_sequence_turn_count": int(
                dialogue_memory.get("active_sequence_turn_count", 0) or 0
            ),
            "dialogue_memory": _compact(dialogue_memory) if relation in {"CONTINUE", "RECALL"} and not artifact_context_only else {
                "window_hours": 12,
                "turn_count_window": dialogue_memory.get("turn_count_window", 0),
                "evidence_only": True,
                "retrieval_mode": "artifact" if artifact_context_only else "none",
                "selected_artifact": _compact(selected_artifact, max_depth=5, max_items=6) if artifact_context_only else {},
            },
            "interpretation_control": _compact(semantic_result.get("interpretation_control") or {}, max_depth=3, max_items=8),
            "window_hours": 12,
            "authenticated_user_scope": {
                "user_id": self.user_id,
                "conversation_id": dialogue_memory.get("conversation_id"),
            },
            "provider_context_plan": _compact(provider_context_plan, max_depth=7, max_items=14),
            "provider_context_authority": "INTERPRETATION",
            "current_user_request": self.request,
        }

        request = MachineRequest(
            goal=intent["goal"],
            intent={
                "type": representation,
                "operation": intent["operation"],
                "object": intent["object"],
                "goal": intent["goal"],
                "normalized_text": self.request,
                "resolved_request": resolved_request,
                "semantic_request": _text(
                    semantic_result.get("semantic_request")
                    or _as_dict(semantic_result.get("semantic_understanding")).get("provider", {}).get("semantic_request")
                    or resolved_request
                ),
                "visual_generation_request": visual_generation_request,
                "semantic_frame": _compact(semantic_result.get("semantic_frame") or {}, max_depth=3, max_items=8),
                "semantic_understanding": _compact(semantic_result.get("semantic_understanding") or {}, max_depth=5, max_items=10),
                "attributes": _compact(intent.get("attributes") or {}),
            },
            conversation={
                "current_request": self.request,
                "resolved_request": resolved_request,
                "dialogue_contract": dialogue_contract,
                "turn_meaning": context,
                "active_task": _compact_task_state(turn_active_task),
                "pending_task": _compact(pending_task),
                "live_scene": _compact(
                    semantic_result.get("live_scene")
                    or context.get("live_scene")
                    or self.state.get("live_dialogue_scene")
                    or {},
                    max_depth=5,
                    max_items=12,
                ),
                "dialogue_vector": _compact(
                    semantic_result.get("dialogue_vector")
                    or context.get("dialogue_vector")
                    or {},
                    max_depth=5,
                    max_items=12,
                ),
                "semantic_frame": _compact(semantic_result.get("semantic_frame") or {}, max_depth=3, max_items=8),
                "turn_sync": _compact(turn_sync, max_depth=4, max_items=10),
                "scene_blueprint": _compact(semantic_result.get("scene_blueprint") or {}, max_depth=5, max_items=16),
                "cognitive_workspace": _compact(cognitive_workspace, max_depth=5, max_items=14),
                "provider_context_plan": _compact(provider_context_plan, max_depth=7, max_items=14),
                "provider_context_authority": "INTERPRETATION",
                "current_user_request": self.request,
                "visual_generation_request": visual_generation_request,
                "user_id": self.user_id,
                "conversation_id": dialogue_memory.get("conversation_id"),
            },
            memory=memory_packet,
            visual_context=(
                visual_reference_context
                if visual_reference_context and not artifact_visual_context
                else {
                    **(visual_reference_context or {}),
                    **(artifact_visual_context or {}),
                }
            ),
            requested_outputs=requested_outputs,
            required_artifacts=required_artifacts,
            required_competencies=[intent["operation"], representation],
            routing={
                "decision_owner": "QUANTUM_PROCESSOR",
                "route": (
                    "artifact_room"
                    if representation in {"image", "gallery"}
                    else "provider"
                ),
                "single_route": True,
                "engine": (
                    "processor->openai->c_artifact->rooms_registry->room->scene"
                    if representation in {"image", "gallery"}
                    else "processor->openai->scene"
                ),
            },
            constraints={
                "one_provider_call": True,
                "provider_input_token_budget": 900,
                "provider_hard_input_budget": provider_context_plan.get("hard_budget_tokens", 900),
                "provider_soft_input_target": provider_context_plan.get("soft_target_tokens"),
                "provider_context_plan": _compact(provider_context_plan, max_depth=7, max_items=14),
                "provider_context_authority": "INTERPRETATION",
                "provider_must_not_reselect_context": True,
                "cognitive_context_plan": _compact(cognitive_workspace, max_depth=5, max_items=14),
                "metadata": {
                    "identity_scope": {
                        "user_id": self.user_id,
                        "conversation_id": dialogue_memory.get("conversation_id"),
                        "dialogue_sequence_id": _text(dialogue.get("sequence_id")),
                    },
                    "visual_production_mode": visual_mode,
                    "visual_generation_route": _text(semantic_result.get("visual_generation_route") or ""),
                    "visual_generation_tier": _text(semantic_result.get("visual_generation_tier") or ""),
                    "semantic_request": _text(
                        semantic_result.get("semantic_request")
                        or _as_dict(semantic_result.get("semantic_understanding")).get("provider", {}).get("semantic_request")
                        or resolved_request
                    ),
                    "visual_generation_request": visual_generation_request,
                    "semantic_understanding": _compact(semantic_result.get("semantic_understanding") or {}, max_depth=5, max_items=10),
                    "dialogue_relation": relation,
                    "semantic_frame": _compact(semantic_result.get("semantic_frame") or {}, max_depth=3, max_items=8),
                    "turn_sync": _compact(turn_sync, max_depth=4, max_items=10),
                    "closure_policy": closure_readiness,
                    "fast_path": True,
                    "do_not_reinterpret": True,
                    "interpretation_control": _compact(intent.get("interpretation_control") or semantic_result.get("interpretation_control") or {}, max_depth=4, max_items=10),
                    "render_authorized": bool(intent.get("render_authorized")),
                    "render_mode": _text(intent.get("render_mode") or "TEXT_ONLY"),
                    "artifact_context_only": artifact_context_only,
                    "selected_artifact": _compact(selected_artifact, max_depth=5, max_items=6) if artifact_context_only else {},
                },
                "representation_plan": {
                    "representation": representation,
                    "visual_production_mode": visual_mode,
                    "visual_generation_route": _text(semantic_result.get("visual_generation_route") or ""),
                    "visual_generation_tier": _text(semantic_result.get("visual_generation_tier") or ""),
                    "renderer": _RENDERER_REGISTRY.get(representation, "MessageTextBlock"),
                    "requested_outputs": list(requested_outputs),
                    "authorized": bool(intent.get("render_authorized")),
                    "render_mode": _text(intent.get("render_mode") or "TEXT_ONLY"),
                    "artifact_context_only": artifact_context_only,
                },
                "scene_composition": requested_outputs,
            },
        )
        setattr(request, "dialogue_contract", dialogue_contract)
        # Keep the Interpretation-authored Provider plan as a direct attribute as
        # well as its existing conversation/constraints copies. This is a transport
        # invariant: later normalization must never lose the frozen plan because of
        # a serializer/compaction boundary.
        setattr(request, "provider_context_plan", deepcopy(provider_context_plan))
        setattr(request, "turn_meaning", context)
        setattr(request, "response_output_tokens", output_budget)
        setattr(request, "quantum_state", {
            "version": "april_processor_v2_semantic_trajectory",
            "relation": relation,
            "continuation": bool(dialogue["continuation"]),
            "reference": bool(dialogue["reference"]),
            "dependency": dialogue["dependency"],
            "resolved_request": resolved_request,
            "canonical_topic": dialogue.get("canonical_topic", ""),
            "resolved_reference": dialogue.get("resolved_reference", ""),
            "selected_memory_index": dialogue.get("selected_memory_index", -1),
            "selected_memory_operand": _compact(dialogue.get("selected_memory_operand") or {}),
            "trajectory": _compact(dialogue.get("trajectory") or {}),
            "sequence_id": _text(dialogue.get("sequence_id")),
            "task_id": _text(dialogue.get("task_id") or (dialogue.get("active_task") or {}).get("task_id")),
            "target_task_id": _text(dialogue.get("target_task_id") or (dialogue.get("active_task") or {}).get("task_id")),
            "dialogue_rules": deepcopy(dialogue.get("dialogue_rules") or {}),
            "response_sequence": deepcopy(dialogue.get("response_sequence") or {}),
            "previous_result": deepcopy(dialogue.get("previous_result") or {}),
            "answer_basis": deepcopy(dialogue.get("answer_basis") or {}),
            "active_entity": resolved_entity,
            "continuation_content_analysis": _compact(continuation_analysis, max_depth=4, max_items=8),
            "dialogue_strategy": _compact(dialogue_strategy, max_depth=3, max_items=8),
            "sequence_continuation_authorized": bool(dialogue.get("sequence_continuation_authorized")),
            "interpretation_control": _compact(intent.get("interpretation_control") or semantic_result.get("interpretation_control") or {}, max_depth=4, max_items=10),
            "cognitive_workspace_version": _text(cognitive_workspace.get("version")),
            "cognitive_workspace_protected": list(cognitive_workspace.get("protected_context") or [])[:12],
            "cognitive_workspace_excluded": list(cognitive_workspace.get("excluded_context") or [])[:8],
            "provider_context_plan_version": _text(provider_context_plan.get("version")),
            "provider_context_required": [
                _text(x.get("key") or x.get("name"))
                for x in list(provider_context_plan.get("required_context") or [])[:16]
                if isinstance(x, dict)
            ],
            "provider_context_optional": [
                _text(x.get("key") or x.get("name"))
                for x in list(provider_context_plan.get("optional_context") or [])[:16]
                if isinstance(x, dict)
            ],
            "provider_context_excluded": [
                _text(x.get("key") or x.get("name"))
                for x in list(provider_context_plan.get("excluded_context") or [])[:16]
                if isinstance(x, dict)
            ],
            "provider_context_authority": "INTERPRETATION",
            "provider_must_not_reselect_context": True,
            "current_user_request": self.request,
            "render_authorized": bool(intent.get("render_authorized")),
            "render_mode": _text(intent.get("render_mode") or "TEXT_ONLY"),
            "provider_calls": 1,
            "single_route": True,
            "interpretation_owned_by": "QUANTUM_PROCESSOR",
        })

        return request

    def build_scene(self, request: MachineRequest, provider_contract: dict) -> tuple[MachineResponse, Any, Any]:
        machine_payload = provider_contract.get("machine_response") if isinstance(provider_contract, dict) else {}
        if not isinstance(machine_payload, dict):
            raise RuntimeError("PROVIDER_MACHINE_RESPONSE_MISSING")

        # Provider has completed. Resolve structured outputs only now, immediately
        # before canonical SceneContract construction.
        machine_payload = _resolve_post_provider_render_blocks(machine_payload, request)
        self._render_omissions = []
        provider_blocks = machine_payload.get("render_blocks") or []
        provider_artifacts = machine_payload.get("artifacts") or []
        blocks = self._canonicalize_blocks(provider_blocks, request)
        answer = _text(machine_payload.get("answer") or machine_payload.get("content"))
        if not answer:
            # Structured output may legitimately carry the visible result without
            # a narrative answer.  Preserve the SceneContract invariant by deriving
            # a minimal carrier from already-authorized blocks; never emit an empty
            # assistant bubble and never re-run semantic interpretation here.
            for block in list(blocks or []):
                if not isinstance(block, dict):
                    continue
                kind = _text(
                    block.get("type") or block.get("artifact_type") or block.get("representation")
                ).lower()
                if kind in {"text", "markdown"}:
                    candidate = _text(block.get("content") or block.get("text") or block.get("answer"))
                    if candidate:
                        answer = candidate
                        break
            if not answer:
                structured_kinds = {
                    _text(
                        block.get("type") or block.get("artifact_type") or block.get("representation")
                    ).lower()
                    for block in list(blocks or [])
                    if isinstance(block, dict)
                }
                if structured_kinds - {"text", "markdown"}:
                    answer = "Готово — результат подготовлен."
            if not answer:
                raise RuntimeError("EMPTY_PROVIDER_ANSWER")

        # Transport invariant: a human-visible answer must never be represented
        # by an empty text block. Some provider payloads contain a valid answer
        # at the MachineResponse level but an empty/partial companion text block.
        # Hydrate that canonical block from the already-validated answer instead
        # of letting the Web create an empty assistant bubble.
        text_like_types = {"text", "markdown"}
        text_block_found = False
        hydrated_blocks = []
        for block in list(blocks or []):
            item = dict(block) if isinstance(block, dict) else {}
            kind = _text(
                item.get("type") or item.get("artifact_type") or item.get("representation") or ""
            ).lower()
            if kind in text_like_types:
                content = _text(item.get("content") or item.get("text") or item.get("answer"))
                if not content:
                    item["type"] = "text"
                    item["renderer"] = "MessageTextBlock"
                    item["viewer"] = "MessageTextBlock"
                    item["content"] = answer
                    item["text"] = answer
                    item["human_visible"] = True
                    item["scene_contract"] = True
                    item["text_recovered_from_answer"] = True
                    item["recovery_reason"] = "provider_text_block_empty_but_machine_answer_present"
                text_block_found = True
            hydrated_blocks.append(item)

        blocks = hydrated_blocks

        # When text is part of the processor-owned output plan, guarantee one
        # visible text carrier even if the provider emitted only structured blocks.
        expected_outputs = {
            _text(x).lower() for x in list(request.requested_outputs or [])
            if _text(x)
        }
        if answer and "text" in expected_outputs and not text_block_found:
            blocks.insert(0, self._text_block(answer))

        if not blocks:
            blocks = [self._text_block(answer)]

        # The scene is composed once below. No renderer-specific side route is
        # allowed to strip blocks after canonicalization. A truly text-only
        # request simply arrives with one text block.

        artifact_objects = [
            item for item in list(machine_payload.get("artifact_objects") or [])
            if isinstance(item, BaseArtifact)
        ]
        response = MachineResponse(
            answer=answer,
            content=_text(machine_payload.get("content") or answer),
            response=_text(machine_payload.get("response") or answer),
            summary=_text(machine_payload.get("summary") or answer),
            explanation=_text(machine_payload.get("explanation")),
            confidence=float(machine_payload.get("confidence") or 1.0),
            render_blocks=blocks,
            artifacts_payload=list(machine_payload.get("artifacts") or []),
            artifacts=artifact_objects,
            scene=dict(machine_payload.get("scene") or {}),
            scene_blueprint=dict(machine_payload.get("scene_blueprint") or {}),
            scene_plan=list(machine_payload.get("scene_plan") or request.requested_outputs or ["text"]),
            render_priority=list(machine_payload.get("render_priority") or request.requested_outputs or ["text"]),
            metadata=dict(machine_payload.get("metadata") or {}),
            continuation=bool(request.quantum_state.get("continuation")),
        )
        response.scene_id = f"{request.request_id}:scene"
        response.turn_id = str(self.state.get("april_turn_id", 0) + 1)
        response.flow_id = str(request.request_id)
        response.topic_group = _text(request.intent.get("object") or request.intent.get("type"))
        response.metadata.update({
            "provider_transport_counts": {
                "provider_render_blocks_received": len(provider_blocks) if isinstance(provider_blocks, list) else 0,
                "provider_artifacts_received": len(provider_artifacts) if isinstance(provider_artifacts, list) else 0,
                "scene_render_blocks_after_canonicalization": len(blocks),
            },
            "render_omissions": list(self._render_omissions)[:24],
            "processor_version": PROCESSOR_VERSION,
            "decision_owner": "QUANTUM_PROCESSOR",
            "canonical_representation": request.intent.get("type"),
            "dialogue_relation": request.dialogue_contract.get("relation"),
            "continuation": bool(request.quantum_state.get("continuation")),
            "single_route": True,
            "provider_calls": 1,
            "fast_path": True,
            "web_signal_source": "SCENE_CONTRACT",
            "user_id": self.user_id,
            "conversation_id": _text(request.memory.get("authenticated_user_scope", {}).get("conversation_id")),
            "dialogue_sequence_id": _text(request.dialogue_contract.get("sequence_id")),
            "task_id": _text(request.dialogue_contract.get("task_id")),
            "sequence_turn_index": int(request.dialogue_contract.get("sequence_turn_index") or 0),
            "dialogue_rules": deepcopy(request.dialogue_contract.get("dialogue_rules") or {}),
            "response_sequence": deepcopy(request.dialogue_contract.get("response_sequence") or {}),
            "identity_scope": {
                "user_id": self.user_id,
                "conversation_id": _text(request.memory.get("authenticated_user_scope", {}).get("conversation_id")),
                "dialogue_sequence_id": _text(request.dialogue_contract.get("sequence_id")),
            },
            "active_task": _compact_task_state(request.dialogue_contract.get("active_task") or {}),
            "interactive_task_state": _compact_task_state(request.dialogue_contract.get("interactive_task_state") or {}),
            "dialogue_state": {
                "relation": request.dialogue_contract.get("relation"),
                "continuation": bool(request.dialogue_contract.get("continuation")),
                "sequence_id": _text(request.dialogue_contract.get("sequence_id")),
                "resolved_request": request.dialogue_contract.get("resolved_request"),
            },
            "semantic_scene_state": {
                "relation": request.dialogue_contract.get("relation"),
                "continuation": bool(request.quantum_state.get("continuation")),
                "resolved_request": request.intent.get("resolved_request"),
                "representation": request.intent.get("type"),
                "active_task": _compact(request.conversation.get("active_task")),
            },
        })

        _hydrate_scene_artifacts(response, request)

        scene = build_machine_scene(response)
        scene.contract = build_scene_contract(scene)
        contract = scene.contract

        # build_scene_contract already produced the canonical v3.1 signal.
        # Never downgrade it to an older Web signal or rebuild the scene here.
        contract.metadata = dict(contract.metadata or {})
        contract.metadata["processor_interpretation"] = {
            "relation": request.dialogue_contract.get("relation"),
            "representation": request.intent.get("type"),
            "operation": request.intent.get("operation"),
            "goal": request.intent.get("goal"),
            "resolved_request": request.intent.get("resolved_request"),
        }
        contract.metadata["web_delivery"] = {
            "version": "scene_contract_v3_1",
            "source": "C_ARTIFACT_CONTRACT.build_scene_contract",
            "render_blocks_canonical": True,
            "renderer_reinterpretation": False,
            "duplicate_rebuild": False,
            "single_visible_stream": True,
            "identity_bound": True,
        }
        contract.signal = build_scene_signal(contract)
        contract.blocks = list(contract.render_blocks)
        return response, scene, contract

    @staticmethod
    def _text_block(answer: str) -> Dict[str, Any]:
        return {
            "type": "text",
            "content": answer,
            "text": answer,
            "renderer": "MessageTextBlock",
            "viewer": "MessageTextBlock",
            "scene_contract": True,
            "human_visible": True,
        }

    def _canonicalize_blocks(self, raw_blocks: Sequence[Any], request: MachineRequest) -> List[Dict[str, Any]]:
        expected = {str(x).lower() for x in request.requested_outputs}
        representation_plan = request.constraints.get("representation_plan", {}) if isinstance(request.constraints, dict) else {}
        if isinstance(representation_plan, dict):
            expected.update(str(x).lower() for x in (representation_plan.get("requested_outputs") or []))
        result: List[Dict[str, Any]] = []
        seen = set()
        structured = set(_STRUCTURED_TYPES) | {"audio", "video", "action", "file", "visual_context", "scene"}
        for raw in raw_blocks:
            if not isinstance(raw, dict):
                continue
            block = dict(raw)
            kind = _text(block.get("type") or block.get("artifact_type") or block.get("representation")).lower()
            if not kind:
                continue
            # Do not discard a valid provider artifact merely because a stale
            # requested_outputs list omitted one member of the already-built
            # composite scene. Only reject an unplanned structured block.
            if kind not in expected and kind not in {"text", "markdown"}:
                provider_plan = {str(x).lower() for x in (raw.get("scene_plan") or [])} if isinstance(raw.get("scene_plan"), list) else set()
                scene_plan = request.conversation.get("scene_blueprint") if isinstance(request.conversation.get("scene_blueprint"), dict) else {}
                blueprint_reps = {str(x).lower() for x in (scene_plan.get("representations") or [])}
                if kind not in provider_plan and kind not in blueprint_reps:
                    continue

            canonical_payload = canonical_payload_for_block(block)
            block["type"] = kind
            block["renderer"] = _RENDERER_REGISTRY.get(kind, block.get("renderer") or "MessageTextBlock")
            block["viewer"] = block.get("viewer") or block["renderer"]
            if canonical_payload:
                block["payload"] = canonical_payload
            elif kind in structured:
                self._render_omissions.append({
                    "type": kind,
                    "reason": "missing_canonical_payload",
                    "block_id": _text(block.get("block_id") or block.get("id")),
                })
                continue

            if kind in structured:
                valid, reason = validate_render_block_payload(kind, block)
                if not valid:
                    self._render_omissions.append({
                        "type": kind,
                        "reason": reason,
                        "block_id": _text(block.get("block_id") or block.get("id")),
                    })
                    continue

            block["scene_contract"] = True
            block["block_id"] = block.get("block_id") or _stable_id(f"scene-{kind}", block.get("payload") or block.get("content"))
            sig = json.dumps({"type": kind, "payload": block.get("payload", {}), "content": block.get("content", "")}, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
            if sig in seen:
                continue
            seen.add(sig)
            block["sequence_index"] = len(result)
            result.append(block)
        return result



def _normalize_interactive_task(value: Any) -> dict[str, Any]:
    """Normalize the cross-layer interactive task state without owning routing."""
    if not isinstance(value, dict):
        return {}

    nested = value.get("interactive_task_state") or value.get("open_task") or value.get("active_task")
    merged = dict(value)
    if isinstance(nested, dict):
        merged.update(nested)

    active = bool(
        merged.get("active")
        or merged.get("open")
        or merged.get("pending_input")
        or merged.get("status") in {"open", "active", "answer_received", "assistant_turn", "suspended", "paused", "completed"}
        or merged.get("kind") in {"game", "riddle", "question", "choice", "task", "topic_task", "dialogue_task"}
        or merged.get("task_id")
    )
    if not active:
        return {}

    task = {
        "active": True,
        "status": _text(merged.get("status") or "open").lower(),
        "kind": _text(merged.get("kind") or merged.get("type") or "task").lower(),
        "role": _text(merged.get("role") or merged.get("task_role")),
        "phase": _text(merged.get("phase") or merged.get("task_phase")),
        "prompt": _text(merged.get("prompt") or merged.get("task_prompt") or merged.get("question")),
        "last_question": _text(merged.get("last_question") or merged.get("question")),
        "expected_input_type": _text(merged.get("expected_input_type") or merged.get("input_type") or "answer"),
        "target": _text(merged.get("target") or merged.get("target_entity")),
        "secret_target": _text(
            merged.get("secret_target")
            or merged.get("hidden_target")
            or merged.get("private_target")
        ),
        "candidate_answer": _text(merged.get("candidate_answer") or merged.get("answer_candidate")),
        "last_user_answer": _text(merged.get("last_user_answer") or merged.get("user_answer")),
        "last_answered_question": _text(merged.get("last_answered_question")),
        "last_user_action": _text(merged.get("last_user_action")),
        "last_input_role": _text(merged.get("last_input_role")),
        "last_input_confidence": float(merged.get("last_input_confidence") or 0.0),
        "known_clues": list(merged.get("known_clues") or [])[-12:],
        "qa_history": list(merged.get("qa_history") or merged.get("turns") or [])[-12:],
        "turns": list(merged.get("qa_history") or merged.get("turns") or [])[-12:],
        "awaiting_user": bool(
            merged.get("awaiting_user")
            or merged.get("awaiting_input")
            or merged.get("expected_input_type") in {"answer", "user_answer"}
        ),
        "completed": bool(merged.get("completed")),
        "task_id": _text(merged.get("task_id")),
        "topic": _text(merged.get("topic") or merged.get("canonical_topic")),
        "goal": _text(merged.get("goal") or merged.get("task_goal")),
        "sequence_id": _text(merged.get("sequence_id") or merged.get("active_sequence_id")),
        "dialogue_rules": deepcopy(merged.get("dialogue_rules") or {}),
        "response_sequence": deepcopy(merged.get("response_sequence") or {}),
        "last_result": deepcopy(merged.get("last_result") or {}),
        "last_answer_basis": deepcopy(merged.get("last_answer_basis") or merged.get("answer_basis") or {}),
        "result_history": list(merged.get("result_history") or merged.get("completed_results") or [])[-30:],
        "response_count": int(merged.get("response_count") or merged.get("task_response_count") or 0),
        "task_response_count": int(merged.get("task_response_count") or merged.get("response_count") or 0),
        "last_user_request": _text(merged.get("last_user_request")),
        "last_april_answer": _text(merged.get("last_april_answer") or merged.get("last_answer")),
        "objective": _text(merged.get("objective") or merged.get("task_objective")),
        "instruction": _text(merged.get("instruction") or merged.get("task_instruction")),
        "created_at": float(merged.get("created_at") or merged.get("task_definition_at") or 0.0),
        "updated_at": float(merged.get("updated_at") or merged.get("last_turn_at") or merged.get("created_at") or 0.0),
        "scene_id": _text(merged.get("scene_id") or merged.get("source_scene_id")),
        "task_revision": int(merged.get("task_revision") or 0),
        "source": _text(merged.get("source") or "executor_task_bridge"),
        "replacement_requested": bool(merged.get("replacement_requested")),
        "reset_memory": bool(merged.get("reset_memory")),
    }
    return task


def _provider_task_state(response: MachineResponse) -> dict[str, Any]:
    metadata = response.metadata if isinstance(response.metadata, dict) else {}
    candidates = [
        metadata.get("dialogue_task_state"),
        metadata.get("interactive_task_state"),
        metadata.get("open_task"),
        metadata.get("task_state"),
    ]
    scene = response.scene if isinstance(response.scene, dict) else {}
    candidates.extend([
        scene.get("interactive_task_state"),
        scene.get("open_task"),
        scene.get("task_state"),
    ])
    for value in candidates:
        task = _normalize_interactive_task(value)
        if task:
            return task
    return {}


def _advance_task_from_answer(
    task: dict[str, Any],
    request_text: str,
    answer: str,
    *,
    response_sequence: dict[str, Any] | None = None,
    dialogue_rules: dict[str, Any] | None = None,
    previous_result: dict[str, Any] | None = None,
    answer_basis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Project the provider result into task state without owning the canonical commit.

    StateManager is the single writer of USER↔APRIL result history and counters.
    Executor must never create a second pair or increment the task counter again.
    """
    normalized = _normalize_interactive_task(task)
    if not normalized:
        return {}
    merged = dict(normalized)
    if isinstance(response_sequence, dict) and response_sequence:
        merged["response_sequence"] = deepcopy(response_sequence)
    if isinstance(dialogue_rules, dict) and dialogue_rules:
        merged["dialogue_rules"] = deepcopy(dialogue_rules)
    if isinstance(previous_result, dict) and previous_result:
        merged["previous_result"] = deepcopy(previous_result)
    if isinstance(answer_basis, dict) and answer_basis:
        merged["previous_answer_basis"] = deepcopy(answer_basis)

    answer_text = _text(answer)
    # Provider status may close a task, but the actual answer/result is committed
    # by StateManager so the task counter can advance exactly once.
    lower_answer = answer_text.lower()
    if "угадал" in lower_answer and "не угадал" not in lower_answer:
        merged["completed"] = True
        merged["status"] = "completed"
        merged["phase"] = "completed"
        merged["awaiting_user"] = False
    elif "?" in answer_text or "？" in answer_text:
        merged["last_question"] = answer_text
        merged["prompt"] = answer_text
        merged["phase"] = "awaiting_user_answer"
        merged["status"] = "open"
        merged["expected_input_type"] = "answer"
        merged["awaiting_user"] = True

    # Preserve canonical state supplied by Interpretation. Do not replace task_id,
    # sequence_id or counters with anything invented by the Provider.
    if _text(task.get("task_id")):
        merged["task_id"] = _text(task.get("task_id"))
    if _text(task.get("sequence_id")):
        merged["sequence_id"] = _text(task.get("sequence_id"))
    merged["source"] = "executor_provider_projection"
    return merged


_DIALOGUE_ALPHABET_RU = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"


def _apply_dialogue_output_contract(machine_payload: dict[str, Any], dialogue_contract: dict[str, Any]) -> dict[str, Any]:
    """Remove legacy visible dialogue markers; never generate new ones.

    Dialogue branch labels and response paths belong to internal 12h memory only.
    Text/markdown blocks are sanitized while structured multimedia blocks are left intact.
    """
    if not isinstance(machine_payload, dict):
        return machine_payload

    def strip_legacy_prefixes(value: Any) -> str:
        text_value = _text(value).strip()
        for _ in range(6):
            updated = re.sub(r'^\s*\d+\s*[.)—:-]\s*', '', text_value)
            updated = re.sub(r'^\s*[А-ЯЁ]\s*[.)—:-]\s*', '', updated, flags=re.IGNORECASE)
            if updated == text_value:
                break
            text_value = updated
        return text_value.strip()

    for field in ('answer', 'content', 'response'):
        if field in machine_payload and machine_payload.get(field):
            machine_payload[field] = strip_legacy_prefixes(machine_payload[field])

    blocks = machine_payload.get('render_blocks')
    if isinstance(blocks, list):
        for block in blocks:
            if not isinstance(block, dict):
                continue
            kind = _text(block.get('type') or block.get('artifact_type') or block.get('representation')).lower()
            if kind not in {'', 'text', 'markdown'}:
                continue
            for field in ('content', 'text', 'answer'):
                if field in block and block.get(field):
                    block[field] = strip_legacy_prefixes(block[field])

    meta = machine_payload.get('metadata') if isinstance(machine_payload.get('metadata'), dict) else {}
    meta['dialogue_output_contract'] = {
        'enforced': True,
        'visible': False,
        'internal_only': True,
        'marker': '',
        'source': 'internal_branch_memory_sanitizer',
    }
    machine_payload['metadata'] = meta
    return machine_payload

def _set_live_state(state: dict, request: MachineRequest, response: MachineResponse, contract: Any) -> None:
    dialogue = request.dialogue_contract or {}
    relation = _text(dialogue.get("relation")).upper() or "NEW"
    representation = _text(request.intent.get("type")).lower() or "text"
    operation = _text(request.intent.get("operation")) or "answer"
    goal = _text(request.intent.get("goal")) or "answer"
    topic = _text(dialogue.get("canonical_topic") or request.intent.get("object") or representation)

    state["april_turn_id"] = int(state.get("april_turn_id") or 0) + 1
    state["last_user_turn"] = request.conversation.get("current_request", "")
    state["last_april_turn"] = response.answer
    state["april_active_topic"] = topic
    state["april_active_goal"] = goal

    # Interactive task state has its own ownership. It must survive provider
    # execution and must never be replaced by the generic topic task.
    request_task = _normalize_interactive_task(
        dialogue.get("interactive_task_state")
        or dialogue.get("open_task")
        or dialogue.get("active_task")
    )
    response_task = _provider_task_state(response)
    task = dict(request_task)
    if response_task:
        # Only merge provider lifecycle fields. Interpretation owns task identity,
        # sequence and counters; Provider cannot overwrite them.
        for key in ("status", "phase", "awaiting_user", "completed", "last_question", "prompt", "expected_input_type"):
            if key in response_task:
                task[key] = response_task[key]

    if task:
        task = _advance_task_from_answer(
            task,
            request.conversation.get("current_request", ""),
            response.answer,
            response_sequence=dialogue.get("response_sequence") if isinstance(dialogue.get("response_sequence"), dict) else {},
            dialogue_rules=dialogue.get("dialogue_rules") if isinstance(dialogue.get("dialogue_rules"), dict) else {},
            previous_result=dialogue.get("previous_result") if isinstance(dialogue.get("previous_result"), dict) else {},
            answer_basis=dialogue.get("answer_basis") if isinstance(dialogue.get("answer_basis"), dict) else {},
        )
        state["interactive_task_state"] = _compact(task, max_depth=5, max_items=16)
        state["open_task"] = _compact(task, max_depth=5, max_items=16)
        state["active_task"] = _compact(task, max_depth=5, max_items=16)
        # `april_active_task` remains the compatibility mirror, but it mirrors
        # the semantic task rather than rebuilding one from topic/object.
        state["april_active_task"] = _compact(task, max_depth=5, max_items=16)
    else:
        # Only replace the compatibility task when no interactive task exists.
        state["april_active_task"] = {
            "operation": operation,
            "object": topic,
            "representation": representation,
            "goal": goal,
            "topic": topic,
        }
        state["interactive_task_state"] = {}
        state["open_task"] = {}
        state["active_task"] = {}

    # Generic active entity is a discourse entity, not a hidden secret target.
    entity = _person_entity_from_answer(response.answer)
    if not entity:
        entity = _text(
            dialogue.get("active_entity")
            or dialogue.get("resolved_entity")
            or dialogue.get("resolved_reference")
        )
    state["april_active_entity"] = entity

    attrs = dict(request.intent.get("attributes") or {})
    if attrs.get("telegram_pending"):
        state["april_pending_task"] = {
            "active": True,
            "expected_input_type": "telegram_target_kind",
            "question": attrs.get("pending_question") or "Какой Telegram нужен: официальный канал, чат или пользовательский аккаунт?",
            "source_turn_id": state["april_turn_id"],
            "representation": "link",
            "operation": "retrieve",
            "object": "telegram_link",
            "goal": "obtain",
            "topic": "telegram_link",
        }
    elif relation == "CONTINUE" and state.get("april_pending_task"):
        state["april_pending_task"] = None
    else:
        state["april_pending_task"] = None

    blocks = list(getattr(contract, "render_blocks", []) or [])
    if blocks:
        state["last_artifact"] = {
            "type": _text(blocks[-1].get("type") or "text").lower(),
            "block_id": _text(blocks[-1].get("block_id")),
            "payload": _compact(blocks[-1].get("payload") or {}),
        }

    state["dialogue_vector"] = {
        **dict(state.get("dialogue_vector") or {}),
        **dict(dialogue),
        "three_way_relation": relation,
        "sequence_id": dialogue.get("sequence_id"),
        "target_sequence_id": dialogue.get("sequence_id") or dialogue.get("target_sequence_id"),
        "sequence_continuation_authorized": bool(dialogue.get("continuation")),
        "current_turn_authority": True,
        "historical_memory_is_evidence_only": True,
        "interactive_task_state": _compact_task_state(task) if task else {},
        "task_memory": _compact({
            "role": task.get("role"),
            "phase": task.get("phase"),
            "last_question": task.get("last_question"),
            "last_answered_question": task.get("last_answered_question"),
            "last_input_role": task.get("last_input_role"),
            "last_input_confidence": task.get("last_input_confidence"),
            "known_clues": task.get("known_clues"),
            "qa_history": task.get("qa_history"),
            "candidate_answer": task.get("candidate_answer"),
        }, max_depth=5, max_items=16) if task else {},
        "dialogue_development": _compact(dialogue.get("dialogue_development") if isinstance(dialogue, dict) else {}, max_depth=6, max_items=12),
    }

    state["dialogue_resolution"] = {
        "authoritative": True,
        "relation": "CONTINUE" if relation == "CONTINUE" else "RECALL" if relation == "RECALL" else "NEW",
        "continuation": bool(dialogue.get("continuation")),
        "reference": bool(dialogue.get("reference_to_previous")),
        "context_dependency": dialogue.get("context_dependency"),
        "resolved_request": dialogue.get("resolved_request"),
        "resolved_reference": dialogue.get("resolved_reference", ""),
        "selected_memory_index": dialogue.get("selected_memory_index", -1),
        "selected_memory_operand": dialogue.get("selected_memory_operand") or {},
        "trajectory": dialogue.get("trajectory") or {},
        "interactive_task_state": _compact_task_state(task) if task else {},
        "source": "semantic_interpretation_layer",
    }

    provider_plan = (
        request.conversation.get("provider_context_plan")
        if isinstance(request.conversation, dict)
        and isinstance(request.conversation.get("provider_context_plan"), dict)
        else {}
    )
    state["interpretation_provider_context_plan"] = _compact(provider_plan, max_depth=7, max_items=14)
    state["provider_context_authority"] = "INTERPRETATION"

    state["april_live_context"] = {
        "version": "april_live_context_v3_provider_context",
        "relation": relation,
        "active_topic": topic,
        "active_goal": goal,
        "active_task": _compact(state.get("april_active_task")),
        "interactive_task_state": _compact_task_state(task) if task else {},
        "pending_task": _compact(state.get("april_pending_task")),
        "last_user_turn": _text(state.get("last_user_turn")),
        "last_april_turn": _text(state.get("last_april_turn")),
        "active_entity": _text(state.get("april_active_entity")),
        "dialogue_strategy": _compact(dialogue.get("dialogue_strategy") if isinstance(dialogue, dict) else {}),
        "continuation_content_analysis": _compact(dialogue.get("continuation_content_analysis") if isinstance(dialogue, dict) else {}),
        "dialogue_development": _compact(dialogue.get("dialogue_development") if isinstance(dialogue, dict) else {}, max_depth=6, max_items=12),
        "scene_id": _text(getattr(contract, "scene_id", "")),
        "render_types": [_text(b.get("type")).lower() for b in blocks if isinstance(b, dict)],
        "current_user_request": _text(request.conversation.get("current_request")),
        "provider_context_plan": _compact(provider_plan, max_depth=7, max_items=14),
        "provider_context_authority": "INTERPRETATION",
    }



async def _visual_input_context(path: str, request_text: str, state: dict) -> Dict[str, Any]:
    if not path:
        return {}
    try:
        from blocks.image_system import scan_image
        packet = await asyncio.to_thread(
            scan_image,
            path,
            user_request=request_text,
            state=state,
        )
        return _compact(packet, max_depth=3, max_items=4) or {}
    except Exception as exc:
        print("⚠️ APRIL VISUAL INPUT:", exc)
        return {"error": "visual_scan_failed"}


async def _route_image_through_room_registry(
    response: MachineResponse,
    request: MachineRequest,
    state: dict,
    user_id: str,
    chat_id=None,
    run_with_activity: Optional[Callable[..., Awaitable[Any]]] = None,
) -> None:
    """Route an image request through C-ARTIFACT -> Room Register.

    Interpretation owns the representation and dialogue continuity. Provider
    remains a single semantic call. The Room Register then executes the already
    authorized image task; concrete raster production stays below the room in
    C_APRIL_IMAGES_GENERATOR. Executor only merges the room result into the
    canonical SceneContract stream.
    """
    constraints = request.constraints if isinstance(request.constraints, dict) else {}
    plan = constraints.get("representation_plan")
    plan = plan if isinstance(plan, dict) else {}

    # MachineRequest uses ``intent.type`` as the canonical representation field.
    # Keep ``representation`` as a compatibility fallback because some older
    # semantic envelopes only expose ``representation``.
    representation = _text(
        request.intent.get("type")
        or request.intent.get("representation")
    ).lower()
    requested_outputs = {
        _text(x).lower()
        for x in (request.requested_outputs or [])
        if _text(x)
    }
    requested_outputs.update(
        _text(x).lower()
        for x in (plan.get("requested_outputs") or [])
        if _text(x)
    )

    # Interpretation owns the primary representation. A structured diagram
    # may carry "image" as an auxiliary presentation hint, but that must NOT
    # launch the raster image-generation room and steal the turn from
    # C_DIAGRAM_ROOM. Only an image/gallery interpretation may enter the
    # image-generation route.
    visual_requested = representation in {"image", "gallery"}
    if not visual_requested:
        print(
            "🧭 IMAGE ROUTE DECISION:",
            {
                "visual_requested": False,
                "representation": representation,
                "requested_outputs": sorted(requested_outputs),
                "flow_id": str(request.request_id),
            },
        )
        return

    metadata = dict(response.metadata or {})
    print(
        "🧭 IMAGE ROUTE DECISION:",
        {
            "visual_requested": True,
            "representation": representation,
            "requested_outputs": sorted(requested_outputs),
            "visual_production_mode": _text(plan.get("visual_production_mode")),
            "flow_id": str(request.request_id),
            "user_id": str(user_id or ""),
        },
    )

    def _concrete_image_payload(payload: dict[str, Any]) -> bool:
        if not isinstance(payload, dict):
            return False
        direct = (
            payload.get("src")
            or payload.get("url")
            or payload.get("image")
            or payload.get("image_data_uri")
            or payload.get("image_base64")
        )
        if direct:
            return True
        images = payload.get("images")
        if isinstance(images, list):
            for item in images:
                if isinstance(item, str) and item.strip():
                    return True
                if isinstance(item, dict):
                    if any(
                        item.get(key)
                        for key in (
                            "src", "url", "image", "image_url",
                            "image_data_uri", "image_base64"
                        )
                    ):
                        return True
        return False

    # A true concrete image is already a valid artifact result. Preserve it and
    # do not run a second image operation.
    concrete_provider_image = False
    for block in list(response.render_blocks or []):
        if not isinstance(block, dict):
            continue
        kind = _text(
            block.get("type")
            or block.get("artifact_type")
            or block.get("representation")
        ).lower()
        if kind not in {"image", "gallery"}:
            continue
        payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
        if _concrete_image_payload(payload):
            concrete_provider_image = True
            break

    if concrete_provider_image:
        metadata.update({
            "image_generation_status": "provider_artifact_preserved",
            "renderer_route": "INTERPRETATION→PROVIDER→C_ARTIFACT→ROOM_REGISTER→ROOM→C_ARTIFACT→SCENE_CONTRACT→WEB",
            "room_route_status": "not_needed_provider_artifact",
        })
        response.metadata = metadata
        return

    provider_metadata = dict(response.metadata or {})
    provider_answer = _text(
        response.answer or response.content or response.response
    )

    conversation = request.conversation if isinstance(request.conversation, dict) else {}
    dialogue_contract = conversation.get("dialogue_contract")
    dialogue_contract = dialogue_contract if isinstance(dialogue_contract, dict) else {}

    route_contract = build_room_route_contract(
        request,
        origin="executor",
        destination="rooms_registry",
        pipeline_stage="artifact_route",
        context={
            "current_user_request": _text(conversation.get("current_request") or request.intent.get("normalized_text")),
            "visual_generation_request": _text(request.intent.get("visual_generation_request") or conversation.get("visual_generation_request")),
            "resolved_request": _text(conversation.get("resolved_request") or request.intent.get("resolved_request")),
            "semantic_request": _text(request.intent.get("semantic_request") or request.intent.get("resolved_request")),
            "dialogue_contract": deepcopy(dialogue_contract),
            "dialogue_vector": deepcopy(conversation.get("dialogue_vector") or {}),
            "semantic_frame": deepcopy(conversation.get("semantic_frame") or {}),
            "visual_context": deepcopy(request.visual_context or {}),
            "provider_metadata": deepcopy(provider_metadata),
            "provider_answer": provider_answer,
        },
        metadata={
            "request_id": str(request.request_id),
            "representation": representation,
            "route": "C_ARTIFACT→ROOM_REGISTER→ROOM",
        },
    )

    try:
        room_response = await registry_route_machine_request(
            request,
            route_contract,
            user_id=_text(user_id),
            chat_id=chat_id,
            state=state,
            provider_response=response,
            run=run_with_activity,
        )
    except Exception as exc:
        metadata.update({
            "image_generation_status": "failed",
            "image_generation_error": str(exc),
            "room_route_status": "dispatch_error",
            "renderer_route": "INTERPRETATION→PROVIDER→C_ARTIFACT→ROOM_REGISTER→ROOM→C_ARTIFACT→SCENE_CONTRACT→WEB",
        })
        response.metadata = metadata
        print("⚠️ APRIL IMAGE ROOM ROUTE:", exc)
        return

    room_blocks = [
        dict(block)
        for block in list(getattr(room_response, "render_blocks", []) or [])
        if isinstance(block, dict)
    ]
    room_artifacts = [
        artifact
        for artifact in list(getattr(room_response, "artifacts", []) or [])
        if isinstance(artifact, BaseArtifact)
    ]
    room_metadata = dict(getattr(room_response, "metadata", {}) or {})
    print(
        "🧭 IMAGE ROOM RESULT:",
        {
            "flow_id": str(request.request_id),
            "room_route_status": _text(room_metadata.get("room_route_status")),
            "image_generation_status": _text(room_metadata.get("image_generation_status")),
            "render_blocks": len(room_blocks),
            "artifacts": len(room_artifacts),
        },
    )

    # If the room did not produce a concrete artifact, keep the provider text and
    # diagnostics intact rather than inventing a visual block.
    concrete_room_blocks = []
    for block in room_blocks:
        kind = _text(
            block.get("type")
            or block.get("artifact_type")
            or block.get("representation")
        ).lower()
        if kind in {"image", "gallery"}:
            payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
            if _concrete_image_payload(payload):
                concrete_room_blocks.append(block)

    if concrete_room_blocks:
        preserved = []
        for block in list(response.render_blocks or []):
            if not isinstance(block, dict):
                continue
            kind = _text(
                block.get("type")
                or block.get("artifact_type")
                or block.get("representation")
            ).lower()
            if kind not in {"image", "gallery"}:
                preserved.append(block)
                continue
            payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
            if _concrete_image_payload(payload):
                preserved.append(block)

        existing_signatures = {
            json.dumps(
                {
                    "type": _text(block.get("type")).lower(),
                    "payload": block.get("payload", {}),
                    "content": block.get("content", ""),
                },
                ensure_ascii=False,
                sort_keys=True,
                default=str,
                separators=(",", ":"),
            )
            for block in preserved
        }

        response.render_blocks = preserved
        for block in concrete_room_blocks:
            sig = json.dumps(
                {
                    "type": _text(block.get("type")).lower(),
                    "payload": block.get("payload", {}),
                    "content": block.get("content", ""),
                },
                ensure_ascii=False,
                sort_keys=True,
                default=str,
                separators=(",", ":"),
            )
            if sig not in existing_signatures:
                existing_signatures.add(sig)
                response.render_blocks.append(block)

    if room_artifacts:
        existing_artifacts = [
            artifact
            for artifact in list(response.artifacts or [])
            if isinstance(artifact, BaseArtifact)
        ]
        known_ids = {
            _text(getattr(getattr(item, "metadata", None), "artifact_id", ""))
            for item in existing_artifacts
        }
        for artifact in room_artifacts:
            artifact_id = _text(
                getattr(getattr(artifact, "metadata", None), "artifact_id", "")
            )
            if not artifact_id or artifact_id not in known_ids:
                existing_artifacts.append(artifact)
                if artifact_id:
                    known_ids.add(artifact_id)
        response.artifacts = existing_artifacts
        response.artifacts_payload = [
            deepcopy(getattr(item, "data", {}) or {})
            for item in existing_artifacts
        ]

    route_status = _text(
        room_metadata.get("room_route_status")
        or ("completed" if concrete_room_blocks else "no_artifact")
    )

    metadata.update(room_metadata)
    metadata.update({
        "image_generation_status": (
            "success" if concrete_room_blocks else
            room_metadata.get("image_generation_status") or "not_materialized"
        ),
        "image_generation_engine": (
            room_metadata.get("image_generation_engine")
            or ("C_APRIL_IMAGES_GENERATOR" if concrete_room_blocks else "")
        ),
        "room_route_status": route_status,
        "room_route": room_metadata.get("room_route") or "rooms_registry.image_generate",
        "artifact_route": "C_ARTIFACT_CONTRACT",
        "renderer_route": "INTERPRETATION→PROVIDER→C_ARTIFACT→ROOM_REGISTER→ROOM→C_ARTIFACT→SCENE_CONTRACT→WEB",
        "provider_calls_added": 0,
        "room_artifact_count": len(room_artifacts),
        "room_render_block_count": len(concrete_room_blocks),
    })
    response.metadata = metadata

    # Keep the canonical generation spec in StateManager so a later visual
    # continuation can resolve against the same dialogue sequence/artifact.
    spec = provider_metadata.get("image_generation_spec")
    if not isinstance(spec, dict):
        specs = provider_metadata.get("image_generation_specs")
        if isinstance(specs, list):
            spec = next((item for item in specs if isinstance(item, dict)), None)
    if isinstance(spec, dict):
        state["image_generation_spec"] = deepcopy(spec)
        state["last_image_generation_route"] = (
            "INTERPRETATION→C_ARTIFACT→ROOM_REGISTER→image_generate→C_APRIL_IMAGES_GENERATOR"
        )

def _merge_room_route_into_response(target: MachineResponse, routed: MachineResponse) -> None:
    """Merge canonical C-room artifacts/blocks without replacing Provider text."""
    if routed is None:
        return

    # Preserve actual BaseArtifact instances for SceneContract composition.
    existing_artifact_ids = {
        str(getattr(getattr(a, "metadata", None), "artifact_id", "") or "")
        for a in list(getattr(target, "artifacts", []) or [])
        if isinstance(a, BaseArtifact)
    }
    for artifact in list(getattr(routed, "artifacts", []) or []):
        if isinstance(artifact, BaseArtifact):
            artifact_id = str(getattr(getattr(artifact, "metadata", None), "artifact_id", "") or "")
            if artifact_id and artifact_id in existing_artifact_ids:
                continue
            target.artifacts.append(artifact)
            if artifact_id:
                existing_artifact_ids.add(artifact_id)

    existing_blocks = list(getattr(target, "render_blocks", []) or [])
    routed_blocks = [
        dict(raw) for raw in list(getattr(routed, "render_blocks", []) or [])
        if isinstance(raw, dict)
    ]
    # The room result is the authoritative C-ARTIFACT projection. Replace the
    # provider's provisional block of the same semantic type instead of showing
    # the same graph/table/formula/code twice.
    routed_types = {
        _text(b.get("type") or b.get("artifact_type")).lower()
        for b in routed_blocks
        if _text(b.get("type") or b.get("artifact_type"))
    }
    if routed_types:
        existing_blocks = [
            b for b in existing_blocks
            if not isinstance(b, dict)
            or _text(b.get("type") or b.get("artifact_type")).lower() not in routed_types
        ]

    seen = {
        (
            _text(b.get("type") or b.get("artifact_type")),
            json.dumps(b.get("payload") or {}, ensure_ascii=False, sort_keys=True, default=str),
        )
        for b in existing_blocks
        if isinstance(b, dict)
    }
    for raw in routed_blocks:
        if not isinstance(raw, dict):
            continue
        block = dict(raw)
        kind = _text(block.get("type") or block.get("artifact_type")).lower()
        payload = canonical_payload_for_block(block)
        if payload:
            block["payload"] = payload
        key = (
            kind,
            json.dumps(block.get("payload") or {}, ensure_ascii=False, sort_keys=True, default=str),
        )
        if key in seen:
            continue
        seen.add(key)
        existing_blocks.append(block)
    target.render_blocks = existing_blocks

    merged_metadata = dict(getattr(target, "metadata", {}) or {})
    merged_metadata.update(dict(getattr(routed, "metadata", {}) or {}))
    merged_metadata["canonical_renderer_route"] = (
        "INTERPRETATION→C_ARTIFACT→ROOM_REGISTER→C_ROOM→"
        "C_ARTIFACT→SCENE_CONTRACT→WEB"
    )
    target.metadata = merged_metadata


async def _route_structured_outputs_through_room_registry(
    response: MachineResponse,
    request: MachineRequest,
    state: dict,
    user_id: str,
    chat_id=None,
    run_with_activity: Optional[Callable[..., Awaitable[Any]]] = None,
) -> None:
    """Route all non-image structured outputs through one C-ARTIFACT/Register call."""
    requested = []
    for value in list(getattr(request, "requested_outputs", []) or []):
        kind = _text(value).lower()
        if kind in {"", "text", "markdown"}:
            continue
        if kind == "image_generate":
            kind = "image"
        if kind not in requested:
            requested.append(kind)

    representation = _text((getattr(request, "intent", {}) or {}).get("type")).lower()
    if representation and representation not in {"text", "markdown", "image", "gallery"} and representation not in requested:
        requested.insert(0, representation)

    non_image = [
        kind for kind in requested
        if kind in {"formula", "graph", "table", "diagram", "code", "link"}
    ]
    if not non_image:
        return

    route_contract = build_room_route_contract(
        request,
        origin="executor",
        destination="rooms_registry",
        pipeline_stage="artifact_route",
        context={
            "provider_render_blocks": list(getattr(response, "render_blocks", []) or []),
            "structured_outputs": list(non_image),
            "route_mode": "canonical_structured",
        },
        metadata={
            "canonical_route": "INTERPRETATION→C_ARTIFACT→ROOM_REGISTER→C_ROOM",
            "renderer_route": "C_ARTIFACT→SCENE_CONTRACT→WEB",
            "representation_authority": "INTERPRETATION",
        },
    )

    routed = await registry_route_machine_request(
        request,
        route_contract,
        user_id=user_id,
        target_representations=non_image,
        chat_id=chat_id,
        state=state,
        provider_response=response,
        run=run_with_activity,
    )
    _merge_room_route_into_response(response, routed)


async def execute(user_id, chat_id=None, text="", run_with_activity: Optional[Callable[..., Awaitable[Any]]] = None, **kwargs):
    request_text = _text(text)
    if not request_text:
        raise ValueError("EMPTY_REQUEST")

    state = get_state(user_id)
    if not isinstance(state, dict):
        raise RuntimeError("STATE_UNAVAILABLE")

    processor = ProcessorScene(state, _text(user_id), request_text)
    request = processor.prepare()

    # Web creates a per-turn flow_id before submitting /api/v1/chat. Reuse that
    # exact id as the MachineRequest id so image-generation status polling,
    # SceneContract flow_id, and the generator all refer to the same turn.
    incoming_flow_id = _text(kwargs.get("flow_id"))
    if incoming_flow_id:
        request.request_id = incoming_flow_id
        if isinstance(request.routing, dict):
            request.routing["flow_id"] = incoming_flow_id
        if isinstance(request.conversation, dict):
            request.conversation["flow_id"] = incoming_flow_id
        print("🧭 APRIL FLOW ID BOUND:", incoming_flow_id)

    visual_input_path = _text(kwargs.get("visual_input_path"))
    if visual_input_path:
        request.visual_context = await _visual_input_context(visual_input_path, request_text, state)
        request.conversation["visual_input_present"] = True
    else:
        request.visual_context = {}

    print("🧬 APRIL EXECUTOR BUILD:", PROCESSOR_VERSION)
    print("🧭 APRIL FLOW:", "INPUT → ACTIVE_BRANCH_MEMORY → CONTEXTUAL_UNDERSTANDING → DIALOGUE_RELATION → RESPONSE_DEVELOPMENT → RENDER_PLAN → OPENAI → C_ARTIFACT → ROOM → SCENE → WEB")
    print("🧠 APRIL INTERPRETATION:", _compact(request.intent))
    print("🧠 APRIL DIALOGUE:", _compact(request.dialogue_contract))

    requested_outputs = {
        _text(value).lower()
        for value in list(request.requested_outputs or [])
        if _text(value)
    }
    started = time.perf_counter()
    if run_with_activity:
        try:
            activity_result = run_with_activity()
            if hasattr(activity_result, "__await__"):
                await activity_result
        except Exception:
            pass

    # Exactly one provider call. generate_text remains the owner of the OpenAI
    # transport and now offloads its synchronous SDK call from the event loop.
    provider_contract = await generate_text(request)
    provider_ms = round((time.perf_counter() - started) * 1000, 1)

    # Provider returns the image plan; the local image engine materializes it
    # before the processor creates the final SceneContract. No second provider.
    # Do not gate this handoff on the provider envelope shape: the Interpreter
    # request is already authoritative about the representation, and Provider
    # intentionally emits only the semantic image plan in image-generation mode.
    machine_preview = (
        provider_contract.get("machine_response")
        if isinstance(provider_contract, dict)
        else {}
    )
    if not isinstance(machine_preview, dict):
        machine_preview = {}

    machine_preview = _bridge_provider_artifacts(machine_preview)
    machine_preview = _apply_dialogue_output_contract(
        machine_preview,
        request.dialogue_contract if isinstance(request.dialogue_contract, dict) else {},
    )
    preview_response = MachineResponse(
        answer=_text(machine_preview.get("answer")),
        content=_text(machine_preview.get("content")),
        response=_text(machine_preview.get("response")),
        summary=_text(machine_preview.get("summary")),
        confidence=float(machine_preview.get("confidence") or 1.0),
        render_blocks=list(machine_preview.get("render_blocks") or []),
        artifacts_payload=list(machine_preview.get("artifacts_payload") or machine_preview.get("artifacts") or []),
        scene=dict(machine_preview.get("scene") or {}),
        metadata=dict(machine_preview.get("metadata") or {}),
    )

    # Machine-only evidence produced by C_APRIL_IMAGES_GENERATOR. It is committed
    # later by the same canonical state writer as the USER↔APRIL turn.
    dialogue_visual_generation_memory: dict[str, Any] = {}

    # The image route is decided from the current MachineRequest, not from the
    # provider's human-facing text block. This is what guarantees that a real
    # image request reaches Room Register even when Provider returns text only.
    await _route_image_through_room_registry(
        preview_response,
        request,
        state,
        _text(user_id),
        chat_id=chat_id,
        run_with_activity=run_with_activity,
    )

    if isinstance(preview_response.metadata, dict):
        candidate_visual_memory = preview_response.metadata.pop(
            "_dialogue_visual_generation_memory",
            None,
        )
        if isinstance(candidate_visual_memory, dict) and candidate_visual_memory.get("generation_prompt"):
            # The public Scene/Web metadata must never carry the large prompt.
            # Keep one internal copy for the canonical 12-hour dialogue writer.
            dialogue_visual_generation_memory = deepcopy(candidate_visual_memory)

    # Every non-image structured representation follows the same canonical
    # C-ARTIFACT -> Room Register -> C-room route before SceneContract.
    await _route_structured_outputs_through_room_registry(
        preview_response,
        request,
        state,
        _text(user_id),
        chat_id=chat_id,
        run_with_activity=run_with_activity,
    )

    machine_preview["render_blocks"] = list(preview_response.render_blocks or [])
    machine_preview["artifacts"] = list(preview_response.artifacts_payload or machine_preview.get("artifacts") or [])
    # Internal-only object channel: keep the real C-ARTIFACT instances until
    # build_scene() constructs the final SceneContract. The public transport
    # still uses artifacts_payload; these objects are never JSON serialized.
    machine_preview["artifact_objects"] = [
        item for item in list(getattr(preview_response, "artifacts", []) or [])
        if isinstance(item, BaseArtifact)
    ]
    machine_preview["artifacts_payload"] = list(preview_response.artifacts_payload or [])
    machine_preview["metadata"] = dict(preview_response.metadata or {})
    if isinstance(provider_contract, dict):
        provider_contract["machine_response"] = machine_preview

    # ASCII is not a supported presentation route. If a model emits an ASCII
    # drawing despite the canonical output contract, suppress that payload before
    # SceneContract so it can never pollute the Web answer. The image/structured
    # room route remains the only visual producer.
    if isinstance(preview_response, MachineResponse):
        raw_answer = _text(preview_response.answer or preview_response.content or preview_response.response)
        lines = [line.strip() for line in raw_answer.splitlines() if line.strip()]
        drawing_chars = sum(len(re.findall(r"[\\/_|+=\-]{3,}", line)) for line in lines)
        ascii_like = bool(
            len(lines) >= 3
            and drawing_chars >= 3
            and sum(ch.isalpha() for ch in raw_answer) < max(8, len(raw_answer) * 0.35)
        ) or bool(re.search(r"```(?:ascii|text|txt)?\s*\n", raw_answer, flags=re.I))
        if ascii_like:
            preview_response.answer = ""
            preview_response.content = ""
            preview_response.response = ""
            preview_response.summary = ""
            preview_response.metadata = dict(preview_response.metadata or {})
            preview_response.metadata["ascii_suppressed"] = True

    response, scene, contract = processor.build_scene(request, provider_contract)
    response.metadata["timing"] = {"provider_ms": provider_ms}

    # Post-result goal analysis is read-only. It decides only whether a difficult
    # completed turn deserves a natural synthesis; ordinary turns remain plain.
    semantic_for_goal = {
        "semantic_frame": request.intent.get("semantic_frame") if isinstance(request.intent, dict) else {},
        "dialogue_contract": request.dialogue_contract or {},
        "active_goal": request.intent.get("goal") if isinstance(request.intent, dict) else "",
        "active_topic": (request.dialogue_contract or {}).get("canonical_topic"),
        "visual_production_mode": ((request.constraints or {}).get("representation_plan") or {}).get("visual_production_mode"),
        "interactive_task_state": (request.dialogue_contract or {}).get("interactive_task_state") or {},
    }
    goal_progress = evaluate_goal_progress(
        request_text,
        state,
        semantic_for_goal,
        response={
            "answer": response.answer,
            "content": response.content,
            "render_blocks": list(getattr(response, "render_blocks", []) or []),
        },
    )
    completion_decision = build_completion_decision(goal_progress, semantic_for_goal)
    response.metadata["goal_progress"] = goal_progress
    response.metadata["completion_decision"] = completion_decision

    # Keep milestone information in the same state used by dialogue interpretation.
    # This is not a trigger route: it is durable semantic evidence for a later turn.
    if bool(goal_progress.get("goal_completed") or goal_progress.get("structured_result")):
        response_scene_id = _text(getattr(contract, "scene_id", ""))
        semantic_frame = request.dialogue_contract.get("semantic_frame") if isinstance(request.dialogue_contract, dict) else {}
        state["dialogue_result_event"] = {
            "turn_id": int(state.get("april_turn_id") or 0) + 1,
            "scene_id": response_scene_id,
            "topic": _text(goal_progress.get("topic") or (request.dialogue_contract or {}).get("canonical_topic")),
            "goal": _text(goal_progress.get("goal") or (request.intent or {}).get("goal")),
            "representation": _text(semantic_frame.get("representation") if isinstance(semantic_frame, dict) else ""),
            "summary": _text(response.answer)[:900],
            "completed": True,
            "created_at": time.time(),
        }

    _set_live_state(state, request, response, contract)

    # One state/scene persistence call. `update_scene_context` is the canonical
    # memory writer; no semantic matrix or second persistence pass is called.
    try:
        update_scene_context(
            user_id,
            contract,
            current_request=request_text,
            answer=response.answer,
            provider_result=provider_contract,
            visual_generation_memory=dialogue_visual_generation_memory,
            internal_context=bool(kwargs.get("internal_context", False)),
            # The canonical state is updated synchronously in memory, but the
            # database write is intentionally moved out of the HTTP critical path.
            persist=False,
        )
        response.metadata["dialogue_committed"] = True
        response.metadata["dialogue_commit_stage"] = "POST_PROVIDER_SCENE_IN_MEMORY_BEFORE_DELIVERY"
        response.metadata["dialogue_persistence"] = "background_after_delivery_commit"
    except Exception as exc:
        print("⚠️ APRIL SCENE MEMORY WRITE:", exc)

    print("✅ APRIL WEB SCENE:", {
        "scene_id": _text(getattr(contract, "scene_id", "")),
        "relation": _text(request.dialogue_contract.get("relation")),
        "blocks": [_text(b.get("type")).lower() for b in list(getattr(contract, "render_blocks", []) or []) if isinstance(b, dict)],
        "provider_ms": provider_ms,
    })

    return {
        "transport_contract": "scene_first",
        "provider_contract": "fiber_v6_quantum",
        "machine_request": request,
        "machine_response": response,
        "machine_scene": scene,
        "scene_contract": contract,
        "answer": response.answer,
        "content": response.content,
        "summary": response.summary,
        "render_blocks": list(getattr(contract, "render_blocks", []) or []),
        "artifacts": list(getattr(response, "artifacts_payload", []) or []),
        "single_route": True,
        "provider_calls_per_request": 1,
        "quantum_state": getattr(request, "quantum_state", {}),
        "provider_context_plan": (request.conversation or {}).get("provider_context_plan", {}),
        "provider_context_authority": "INTERPRETATION",
        "visible_answer_guaranteed": True,
        "artifact_preservation": True,
        "web_delivery": {
            "version": "april_web_scene_signal_v1",
            "target": "AprilWeb",
            "transport": "SceneContract",
            "single_visible_stream": True,
            "scene_contract": contract,
            "render_blocks": list(getattr(contract, "render_blocks", []) or []),
        },
    }


# ============================================================================
# CANONICAL INTERPRETER BRIDGE — 2026-10-04
# ============================================================================
# Executor keeps its compatibility implementation for historical imports, but
# production turns must use the pair-first interpretation owned by
# blocks.interpretation_layer. This prevents the duplicate legacy interpreter
# from recreating topic/entity memory decisions.
from blocks.interpretation_layer import interpret_request as _PAIR_FIRST_INTERPRET_REQUEST


def interpret_request(text, cognition=None, semantic=None, history=None, state=None):
    return _PAIR_FIRST_INTERPRET_REQUEST(
        text,
        cognition=cognition,
        semantic=semantic,
        history=history or [],
        state=state or {},
    )


# ---------------------------------------------------------------------------
# Canonical pair-first intent sanitization. Memory does not expose entities.
# ---------------------------------------------------------------------------
