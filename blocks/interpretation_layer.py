"""
APRIL INTERPRETATION LAYER — QUANTUM MATRIX ENGINE

Single semantic engine for:
input -> matrix interpretation -> evidence packet -> QUANTUM_PROCESSOR
      -> existing provider/rooms -> C_ARTIFACT_CONTRACT -> April Web

The interpretation layer never owns routing, providers, renderers, room execution,
or final response generation. Public compatibility helpers remain available so
downstream imports can continue using the same single route.
"""

from __future__ import annotations

import os
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:  # pragma: no cover
    TfidfVectorizer = None
    cosine_similarity = None

try:
    import spacy
except Exception:  # pragma: no cover
    spacy = None
try:
    import stanza
    from stanza.pipeline.multilingual import MultilingualPipeline
    from spacy.language import Language
except Exception:  # pragma: no cover
    stanza = None
    MultilingualPipeline = Any
    Language = Any

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    SentenceTransformer = None

try:
    from transformers import pipeline as hf_pipeline
except Exception:  # pragma: no cover
    hf_pipeline = None


# ---------------------------------------------------------------------------
# Canonical constants
# ---------------------------------------------------------------------------

RESPONSE_COMPLEXITY_LOW = "LOW"
RESPONSE_COMPLEXITY_MEDIUM = "MEDIUM"
RESPONSE_COMPLEXITY_HIGH = "HIGH"

DECISION_OWNER = "QUANTUM_PROCESSOR"
TRANSPORT_NAME = "transport_state"

SEMANTIC_MODEL_NAME = os.getenv(
    "APRIL_SENTENCE_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
NLI_MODEL_NAME = os.getenv(
    "APRIL_ZERO_SHOT_MODEL",
    "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
)
SPACY_MODEL_NAME = os.getenv("APRIL_SPACY_MODEL", "xx_ent_wiki_sm")

APRIL_FAST_SEMANTIC_MODE = (
    os.getenv("APRIL_FAST_SEMANTIC_MODE", "1").strip().lower()
    in {"1", "true", "yes", "on"}
)
APRIL_ENABLE_HEAVY_HOTPATH = (
    os.getenv("APRIL_ENABLE_HEAVY_HOTPATH", "0").strip().lower()
    in {"1", "true", "yes", "on"}
)

DIALOGUE_LABELS = (
    "identity", "greeting", "question", "request", "reformulation",
    "continuation", "correction", "reference", "affirmation",
    "rejection", "new_topic", "statement", "independent", "memory_query",
)

REPRESENTATION_HYPOTHESES = {
    "text": "the user wants a normal textual answer",
    "table": "the user wants the information represented as a table",
    "graph": "the user wants the information represented as a graph or chart",
    "diagram": "the user wants a schematic or diagram with connected elements",
    "formula": "the user wants a mathematical formula or mathematical notation",
    "image": "the user wants an image or generated picture",
    "gallery": "the user wants multiple images or a gallery",
    "code": "the user wants executable source code",
    "link": "the user wants a link or web resource",
}

SEMANTIC_TURN_PROTOTYPES = {
    "identity": "пользователь спрашивает кто ты как тебя зовут представься назови себя; the user asks who you are or what your name is",
    "greeting": "пользователь приветствует ассистента начинает непринужденный разговор; the user is greeting the assistant",
    "question": "пользователь задаёт вопрос просит ответ или разъяснение сколько равен вычисли посчитай значение; the user asks a question requiring an answer or calculation",
    "request": "пользователь просит выполнить задачу сделать действие создать результат; the user asks the assistant to perform a task",
    "continuation": "пользователь продолжает текущую мысль, задаёт следующий уточняющий вопрос, говорит теперь, а теперь, дальше, на этом, по нему, по ней, просит развить, объяснить дальше, проверить вывод, добавить деталь, продолжить уже начатый результат; the user continues the current reasoning thread with a follow-up, clarification, extension, or refinement",
    "reformulation": "пользователь переформулирует предыдущий запрос, просит показать это иначе, уточняет формулировку, просит переделать или дополнить уже полученный результат; the user reformulates or refines an existing result",
    "correction": "пользователь исправляет предыдущий результат, добавляет условие, меняет параметр или уточняет деталь уже обсуждаемой задачи; the user corrects, extends, or changes a detail of the preceding task",
    "reference": "пользователь явно ссылается на уже показанное, созданное или сказанное, использует местоимение или указание на объект, этот, эту, это, него, неё, нему, просит изменить добавить отметить в нём или в ней; the user explicitly refers to a previously shown or discussed object",
    "artifact_reference": "пользователь спрашивает о содержимом, свойствах или результате уже созданного или показанного артефакта, что было нарисовано, какие элементы получились, что находится в предыдущем результате, просит перечислить или объяснить уже созданный объект; the user asks about the contents, properties, or result of an artifact that was already created or shown",
    "memory_query": "пользователь просит вспомнить что он ранее спрашивал, какой вопрос задавал, о чем говорили, какой был прошлый вопрос или тема; the user asks to recall what they previously asked or discussed",
    "affirmation": "пользователь подтверждает согласие принимает предыдущий результат; the user confirms the preceding result",
    "rejection": "пользователь отклоняет предыдущий результат или предлагает другой вариант; the user rejects the preceding result",
    "new_topic": "пользователь начинает новую тему не связанную с предыдущим обсуждением; the user starts a new topic",
    "statement": "пользователь сообщает утверждение факт или мысль; the user makes a statement",
    "independent": "самостоятельный запрос не зависящий от предыдущих сообщений; the request is self contained and independent",
}

REPRESENTATION_HYPOTHESES = {
    "text": "обычный текстовый ответ объяснение рассказ описание; the user wants a normal textual answer",
    "table": "таблица таблицу табличный формат строки столбцы колонки; information represented as a table",
    "graph": "график графика chart plot graph кривая кривые функция; information represented as a graph or chart",
    "diagram": "схема чертёж технический чертёж рисунок построение геометрическая фигура треугольник квадрат круг окружность вершины стороны углы длина сантиметр см соединение элементов блоки связи последовательность процесса подключение проводов источник питания выключатель лампа электрическая цепь; a technical or geometric drawing, construction diagram, schematic, wiring diagram, connected structure, or process diagram",
    "formula": "формула уравнение математическое выражение математическая запись равенство обозначение величин степени корни E mc2; a mathematical formula, equation, notation, or quantitative relationship",
    "image": "изображение картинка рисунок иллюстрация создать изображение фотография; an image or generated picture",
    "gallery": "несколько изображений много картинок подборка галерея набор карточек сравнение изображений; multiple images, a gallery, or an image collection",
    "code": "код программный код функция программа реализация python; executable source code or software implementation",
    "link": "ссылка адрес сайта веб ресурс открыть ресурс интернет источник; a link or web resource",
}


DOMAIN_HYPOTHESES = {
    "biology": "биология живые организмы клетки генетика животные растения; biology living organisms genetics",
    "chemistry": "химия вещества реакции молекулы атомы химические процессы; chemistry substances reactions molecules",
    "physics": "физика энергия сила движение скорость масса поля; physics energy forces motion",
    "engineering": "инженерия конструкции проектирование система устройство архитектура; engineering design construction",
    "it": "программирование компьютер software код алгоритм приложение система; computing programming software",
    "literature": "литература писатель поэзия роман стихотворение произведение; literature writing poetry authors",
    "politics": "политика государство правительство выборы закон; politics government",
    "news": "новости текущие события последние события; current events news",
    "social": "общество социальные темы люди отношения; society social topics",
    "web": "интернет сайт веб поиск онлайн ресурс страница; web search online resource",
}


CAPABILITY_HYPOTHESES = {
    "exploration": "анализ сравнение исследование изучение разбор выводы; analysis comparison investigation",
    "web": "поиск в интернете онлайн ресурс сайт веб информация; web search online resource",
    "code": "код программирование программная реализация функция python; programming code implementation",
    "information": "объяснение информация фактический ответ что означает разъяснение; explanation factual answer",
    "discussion": "обсуждение мнение рассуждение позиция аргументы; discussion opinion reasoning",
    "space": "пространство сцена композиция визуальная структура расположение элементов; spatial scene composition",
}


SCENE_MATRIX_LABELS = (
    "text", "table", "graph", "diagram", "formula", "image", "gallery", "code", "link",
)
SCENE_MATRIX_FEATURES = (
    "dialogue", "representation", "domain", "capability",
    "continuity", "context", "modality",
)

# One scene matrix: rows=scenes, columns=evidence families.
_SCENE_WEIGHTS = (
    (0.12, 0.55, 0.03, 0.20, 0.04, 0.03, 0.03),
    (0.08, 0.62, 0.03, 0.20, 0.02, 0.03, 0.02),
    (0.04, 0.68, 0.05, 0.16, 0.02, 0.03, 0.02),
    (0.04, 0.62, 0.06, 0.20, 0.02, 0.04, 0.02),
    (0.03, 0.70, 0.07, 0.16, 0.01, 0.02, 0.01),
    (0.03, 0.72, 0.03, 0.17, 0.01, 0.02, 0.02),
    (0.03, 0.74, 0.03, 0.16, 0.01, 0.02, 0.01),
    (0.02, 0.70, 0.03, 0.22, 0.01, 0.01, 0.01),
    (0.02, 0.66, 0.05, 0.22, 0.01, 0.03, 0.01),
)

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


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Unified Quantum Interpretation Engine v3
# ---------------------------------------------------------------------------

REPRESENTATION_UNIVERSE = (
    "text", "table", "graph", "diagram", "formula", "image", "gallery",
    "code", "link", "audio", "video", "file", "action", "scene",
    "memory", "visual_context",
)
STRUCTURED_REPRESENTATIONS = tuple(x for x in REPRESENTATION_UNIVERSE if x != "text")

OPERATION_HYPOTHESES = {
    "answer": "ответить объяснить рассказать сообщить дать информацию",
    "build": "создать построить сформировать нарисовать начертить изобразить результат",
    "present": "показать отобразить продемонстрировать вывести представить результат",

    "compare": "сравнить сопоставить различия сходства",
    "modify": "изменить исправить обновить переделать дополнить",
    "retrieve": "найти получить ресурс источник ссылку документ",
    "calculate": "посчитать вычислить рассчитать решить",
    "analyze": "проанализировать разобрать исследовать проверить",
    "explain": "объяснить разъяснить пояснить растолковать как работает почему смысл принцип",
    "summarize": "суммировать сократить основные пункты",
    "list": "перечислить список варианты",
}
OBJECT_HYPOTHESES = {
    "graph": "график plot chart curve series числовая визуализация",
    "diagram": "схема чертёж технический чертёж построение геометрическая фигура треугольник квадрат круг окружность вершины стороны углы длина сантиметр см блоки связи соединения проводка электрическая цепь процесс",
    "table": "таблица строки столбцы колонки структурированные данные сравнение",
    "formula": "формула уравнение математическое выражение notation",
    "link": "ссылка URL адрес сайта веб ресурс источник",
    "code": "код программа функция скрипт",
    "image": "изображение картинка рисунок иллюстрация фотография портрет художественная картинка",
    "gallery": "галерея подборка несколько изображений",
    "file": "файл документ вложение",
    "audio": "аудио звук голос запись",
    "video": "видео ролик запись",
    "text": "текст обычный ответ объяснение описание",
    "action": "действие интерактивная операция",
}
GOAL_HYPOTHESES = {
    "visualize": "увидеть визуально показать наглядно кривые схему",
    "organize": "структурировать упорядочить данные строки столбцы",
    "present": "представить вывести отобразить результат",
    "understand": "понять разобраться объяснение смысл",
    "obtain": "получить ресурс ссылку файл",
    "transform": "изменить преобразовать результат",
    "decide": "выбрать сопоставить варианты",
}

# Visual schema is a semantic subtype of an already-resolved representation.
# It is evidence only: it never routes by keyword and never owns renderer choice.
VISUAL_SCHEMA_HYPOTHESES = {
    "text_schema": "текстовая схема ASCII схема текстовая блок-схема последовательность шагов стрелки пункты обозначения узлы связи в тексте; textual schematic or ASCII-style text schema using characters and arrows",
    "function": "mathematical function equation dependency f(x) y of x curve coordinate plot; mathematical function against an axis",
    "series": "ряд данных последовательность измерений значения изменение динамика тренд временной ряд развитие по оси; ordered measurements or changing values",
    "timeline": "временная шкала хронология история периоды эпохи эры события даты раньше позже начало конец продолжительность последовательность во времени развитие существование вымирание; temporal history chronology eras periods dates and events",
    "scatter": "paired observations numeric variables relationship correlation distribution individual points; relationship between two numeric variables",
    "network": "entities connected by relationships nodes edges topology dependencies connections; network of related entities",
    "matrix": "rows columns cells heatmap two dimensional array intensities crossing dimensions; matrix or heatmap",
    "categorical": "категории группы сравнение ранжирование дискретные значения подписи количество по категориям; categorical comparison",
}

REPRESENTATION_ALIASES = {
    "chart":"graph","plot":"graph","schematic":"diagram","flowchart":"diagram",
    "math":"formula","equation":"formula","url":"link","link_card":"link","media":"gallery",
}

def _clean_representation(value: Any) -> str:
    value = str(value or "").strip().lower()
    value = REPRESENTATION_ALIASES.get(value, value)
    return value if value in REPRESENTATION_UNIVERSE else ""

class QuantumInterpretationEngine:
    """
    One semantic engine. It measures evidence, resolves the user's task and
    freezes one production interpretation. Evidence never becomes a renderer
    command by itself. No lexical routing, no domain/capability gates and no
    silent renderer fallback.
    """
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cache = {}
        self._cache_limit = 256
        self._vectorizer = None
        self._prototype_matrix = None
        self._prototype_index = {}
        self._semantic_encoder = None
        self._compile_matrix()

    @staticmethod
    def normalize(text: Any) -> str:
        return re.sub(r"\s+", " ", str(text or "").strip())

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+", str(text or "").lower())

    def _compile_matrix(self):
        families = (
            ("dialogue", SEMANTIC_TURN_PROTOTYPES),
            ("representation", REPRESENTATION_HYPOTHESES),
            ("domain", DOMAIN_HYPOTHESES),
            ("capability", CAPABILITY_HYPOTHESES),
            ("operation", OPERATION_HYPOTHESES),
            ("object", OBJECT_HYPOTHESES),
            ("goal", GOAL_HYPOTHESES),
            ("visual_schema", VISUAL_SCHEMA_HYPOTHESES),
        )
        docs = []
        for family, vocab in families:
            for label, description in vocab.items():
                self._prototype_index[f"{family}:{label}"] = len(docs)
                docs.append(description)
        if TfidfVectorizer is not None and docs:
            self._vectorizer = TfidfVectorizer(
                analyzer="char_wb", ngram_range=(3,5),
                lowercase=True, sublinear_tf=True
            )
            self._prototype_matrix = self._vectorizer.fit_transform(docs)

        if APRIL_ENABLE_HEAVY_HOTPATH and SentenceTransformer is not None:
            try:
                self._semantic_encoder = SentenceTransformer(SEMANTIC_MODEL_NAME)
            except Exception:
                self._semantic_encoder = None

    @staticmethod
    def _semantic_focus_text(text: str) -> str:
        lines = []
        for line in str(text or "").splitlines():
            s = line.strip()
            if not s:
                continue
            nums = re.findall(r"[-+]?\\d+(?:[.,]\\d+)?", s)
            if len(nums) >= 2 and re.search(r"(?:—|–|-|:)", s):
                continue
            lines.append(s)
        return " ".join(lines)

    def _negated_representation_labels(self, text: str) -> set[str]:
        source = self.normalize(text).lower()
        negated = set()
        matches = re.findall(r"(?:не|not)\s+(?:как|as)\s+([^.;!?]+)", source)
        if not matches:
            return negated
        negated_text = " ".join(matches)
        negated_tokens = {
            token for token in self._tokens(negated_text)
            if len(token) >= 4
        }
        if not negated_tokens:
            return negated
        for label, hypothesis in REPRESENTATION_HYPOTHESES.items():
            hypothesis_tokens = {
                token for token in self._tokens(hypothesis)
                if len(token) >= 4 and not token.isascii()
            }
            if hypothesis_tokens & negated_tokens:
                negated.add(label)
        return negated

    def _family_scores(self, text, family, vocab):
        text = self.normalize(text)
        if not text:
            return {k:0.0 for k in vocab}

        if self._semantic_encoder is not None:
            try:
                q = self._semantic_encoder.encode([text], normalize_embeddings=True)[0]
                d = self._semantic_encoder.encode(
                    list(vocab.values()), normalize_embeddings=True
                )
                vals = ((d @ q) + 1.0) / 2.0
                return {k:max(0.0,min(1.0,float(v))) for k,v in zip(vocab,vals)}
            except Exception:
                pass

        if self._vectorizer is not None and self._prototype_matrix is not None and cosine_similarity is not None:
            q = self._vectorizer.transform([text])
            result = {}
            for label in vocab:
                idx = self._prototype_index[f"{family}:{label}"]
                similarity_value = cosine_similarity(q, self._prototype_matrix[idx])
                # cosine_similarity returns a 2-D array for sparse row/row input.
                # Extract the single scalar explicitly instead of coercing the
                # whole ndarray to float.
                score = float(similarity_value[0, 0])
                result[label] = max(0.0, min(1.0, score))
            return result

        # Evidence-only degraded measurement. It can rank hypotheses but it
        # cannot create or suppress production representation.
        tokens = set(self._tokens(text))
        result = {}
        for label, description in vocab.items():
            words = set(self._tokens(description))
            result[label] = min(1.0, len(tokens & words)/max(2.0,len(words)*0.2))
        return result

    @staticmethod
    def _semantic_request_features(
        text: str,
        scores: dict[str, dict[str, float]] | None = None,
    ) -> dict[str, float | bool]:
        """Collapse semantic families into a task-vector feature set.

        No word/phrase trigger table is used.  The feature set is derived only
        from the already-measured semantic families, so equivalent phrasings
        converge on the same task representation.
        """
        measured = scores if isinstance(scores, dict) else {}
        rep_scores = measured.get("representation", {}) if isinstance(measured.get("representation"), dict) else {}
        op_scores = measured.get("operation", {}) if isinstance(measured.get("operation"), dict) else {}
        obj_scores = measured.get("object", {}) if isinstance(measured.get("object"), dict) else {}
        goal_scores = measured.get("goal", {}) if isinstance(measured.get("goal"), dict) else {}
        dial_scores = measured.get("dialogue", {}) if isinstance(measured.get("dialogue"), dict) else {}

        def best(mapping: dict[str, float], default: str) -> tuple[str, float]:
            if not mapping:
                return default, 0.0
            key, value = max(mapping.items(), key=lambda item: float(item[1] or 0.0))
            return str(key), float(value or 0.0)

        best_rep, best_rep_score = best(rep_scores, "text")
        best_op, best_op_score = best(op_scores, "answer")
        best_obj, best_obj_score = best(obj_scores, "text")
        best_goal, best_goal_score = best(goal_scores, "understand")
        best_dialogue, best_dialogue_score = best(dial_scores, "statement")

        structured_rep = best_rep in {
            "diagram", "graph", "formula", "image", "gallery", "table",
            "code", "link", "audio", "video", "file", "action", "scene",
            "memory", "visual_context",
        }
        visual_rep = best_rep in {"diagram", "image", "gallery", "graph"}
        visual_object = best_obj in {"diagram", "image", "gallery", "graph"}
        visual_operation = best_op in {"build", "modify", "present"}
        visual_goal = best_goal in {"visualize", "transform", "present"}
        memory_query = best_dialogue == "memory_query"
        visual_schema_scores = measured.get("visual_schema", {}) if isinstance(measured.get("visual_schema"), dict) else {}
        text_schema_score = float(visual_schema_scores.get("text_schema", 0.0) or 0.0)
        ascii_schema_advisory = bool(
            best_rep == "text"
            and text_schema_score >= 0.10
            and best_op in {"answer", "build", "present", "explain", "list"}
        )

        followup_dialogue = best_dialogue in {
            "continuation", "reformulation", "correction", "reference",
            "artifact_reference", "affirmation", "rejection",
        }
        # A task is self-contained only when the semantic dialogue classifier does
        # not describe it as a follow-up/reference and the current semantic task
        # itself supplies an operation plus an object/structured representation.
        self_contained = bool(
            not followup_dialogue
            and not memory_query
            and best_op in {
                "build", "modify", "present", "compare", "calculate",
                "analyze", "retrieve", "list", "explain",
            }
            and (best_obj != "text" or structured_rep)
        )

        return {
            "visual_action": bool(visual_operation and (visual_rep or visual_object)),
            "explain_action": bool(best_op == "explain"),
            "geometry_object": bool(
                best_obj == "diagram"
                and best_obj_score >= 0.08
            ),
            "construction_context": bool(
                best_rep == "diagram"
                and best_rep_score >= 0.08
            ),
            "visual_construction": bool(
                visual_rep
                and visual_operation
                and (visual_object or best_rep_score >= 0.16)
                and (visual_goal or best_goal_score >= 0.08)
            ),
            "ascii_schema_advisory": ascii_schema_advisory,
            "ascii_schema_score": text_schema_score,
            "self_contained": self_contained,
            "memory_query": memory_query,
            "semantic_best_representation": best_rep,
            "semantic_best_operation": best_op,
            "semantic_best_object": best_obj,
            "semantic_best_goal": best_goal,
            "semantic_best_dialogue": best_dialogue,
            "semantic_best_dialogue_score": best_dialogue_score,
        }

    @staticmethod
    def _scene_semantic_text(scene: dict | None) -> str:
        """Build a compact semantic view of the active rendered scene.

        This is local evidence only. It serializes existing scene metadata and
        structured render-block payloads; it does not choose a renderer or call
        a provider.
        """
        if not isinstance(scene, dict):
            return ""
        parts = [
            scene.get("topic"),
            scene.get("summary"),
            scene.get("user_request"),
            scene.get("current_request"),
            scene.get("april_answer"),
            scene.get("answer"),
        ]
        for block in scene.get("render_blocks") or []:
            if not isinstance(block, dict):
                continue
            parts.extend([
                block.get("type"),
                block.get("artifact_type"),
                block.get("representation"),
                block.get("renderer"),
                block.get("title"),
                block.get("label"),
                block.get("content"),
                block.get("text"),
            ])
            payload = block.get("payload")
            if isinstance(payload, dict):
                # Payload is already part of the active scene. Keep only a compact
                # textual projection so visual facts can participate in semantic
                # similarity without copying the entire artifact into the prompt.
                parts.append(
                    re.sub(r"\\s+", " ", str(payload))[:1800]
                )
        return re.sub(r"\\s+", " ", " ".join(
            str(x) for x in parts if x not in (None, "", [], {})
        )).strip()[:5000]

    def _context_scores(self,text,previous_assistant,previous_user,active_topic,active_goal):
        vals = {
            "previous_assistant":previous_assistant,
            "previous_user":previous_user,
            "active_topic":active_topic,
            "active_goal":active_goal,
        }
        return {
            k:self.similarity(text,v)["score"] if self.normalize(v) else 0.0
            for k,v in vals.items()
        }

    def _dialogue_relation_engine(
        self,
        text: str,
        *,
        previous_assistant: str = "",
        previous_user: str = "",
        active_topic: str = "",
        active_goal: str = "",
        previous_scene: dict | None = None,
    ) -> dict:
        """Resolve topic continuity and request dependency from semantic evidence.

        Topic similarity and request dependency are separate dimensions.  The
        dialogue classifier decides the discourse act; current-task semantic
        completeness prevents topical similarity from becoming a false
        continuation.  No lexical trigger map is used.
        """
        current = self.normalize(text)
        prev_a = self.normalize(previous_assistant)
        prev_u = self.normalize(previous_user)
        topic = self.normalize(active_topic)
        goal = self.normalize(active_goal)
        scene = previous_scene if isinstance(previous_scene, dict) else {}
        scene_topic = self.normalize(scene.get("topic"))

        sims = {
            "previous_assistant": self.similarity(current, prev_a)["score"] if prev_a else 0.0,
            "previous_user": self.similarity(current, prev_u)["score"] if prev_u else 0.0,
            "active_topic": self.similarity(current, topic)["score"] if topic else 0.0,
            "active_goal": self.similarity(current, goal)["score"] if goal else 0.0,
            "previous_scene_topic": self.similarity(current, scene_topic)["score"] if scene_topic else 0.0,
        }
        dialogue_scores = self._family_scores(current, "dialogue", SEMANTIC_TURN_PROTOTYPES)
        dialogue_rank = sorted(
            dialogue_scores.items(),
            key=lambda item: float(item[1] or 0.0),
            reverse=True,
        )
        dialogue_best = dialogue_rank[0][0] if dialogue_rank else "statement"
        dialogue_best_score = float(dialogue_rank[0][1]) if dialogue_rank else 0.0

        features = self._semantic_request_features(
            current,
            {
                "representation": self._family_scores(current, "representation", REPRESENTATION_HYPOTHESES),
                "operation": self._family_scores(current, "operation", OPERATION_HYPOTHESES),
                "object": self._family_scores(current, "object", OBJECT_HYPOTHESES),
                "goal": self._family_scores(current, "goal", GOAL_HYPOTHESES),
                "dialogue": dialogue_scores,
            },
        )

        followup_labels = {"continuation", "reformulation", "correction", "reference", "artifact_reference", "affirmation", "rejection"}
        dialogue_followup = max(
            (float(dialogue_scores.get(label, 0.0) or 0.0) for label in followup_labels),
            default=0.0,
        )
        reference_evidence = max(
            float(dialogue_scores.get("reference", 0.0) or 0.0),
            float(dialogue_scores.get("artifact_reference", 0.0) or 0.0),
        )
        artifact_reference_evidence = float(
            dialogue_scores.get("artifact_reference", 0.0) or 0.0
        )
        memory_evidence = float(dialogue_scores.get("memory_query", 0.0) or 0.0)
        continuation_evidence = max(
            float(dialogue_scores.get("continuation", 0.0) or 0.0),
            float(dialogue_scores.get("reformulation", 0.0) or 0.0),
            float(dialogue_scores.get("correction", 0.0) or 0.0),
        )

        topic_affinity = max(
            sims["active_topic"],
            sims["previous_scene_topic"],
            sims["previous_user"] * 0.92,
        )
        answer_affinity = sims["previous_assistant"]
        request_affinity = sims["previous_user"]
        goal_affinity = sims["active_goal"]
        relation_strength = max(topic_affinity, answer_affinity, request_affinity, goal_affinity)

        has_context = bool(prev_a or prev_u or topic or scene_topic)
        current_self_contained = bool(features.get("self_contained"))
        semantic_reference = bool(
            dialogue_best == "reference"
            and has_context
            and not current_self_contained
        )
        semantic_memory_query = bool(dialogue_best == "memory_query" and has_context)

        # A dialogue classifier is authoritative for discourse act.  Similarity
        # only supplies topical context and never upgrades an independent task.
        if not has_context:
            relation = "MEMORY_QUERY" if dialogue_best == "memory_query" else "NEW_TOPIC"
            topic_relation = relation
        elif semantic_memory_query:
            relation = "MEMORY_QUERY"
            topic_relation = "SAME_TOPIC"
        elif semantic_reference:
            relation = "CONTINUE_TOPIC"
            topic_relation = "SAME_TOPIC"
        elif dialogue_best in {"continuation", "reformulation", "correction"} and not current_self_contained:
            relation = "CONTINUE_TOPIC"
            topic_relation = "SAME_TOPIC"
        elif current_self_contained:
            relation = (
                "SAME_TOPIC"
                if topic_affinity >= 0.18 or request_affinity >= 0.42
                else "INDEPENDENT"
            )
            topic_relation = relation
        elif dialogue_best in {"affirmation", "rejection"} and has_context:
            relation = "SAME_TOPIC"
            topic_relation = "SAME_TOPIC"
        elif relation_strength >= 0.48:
            relation = "SAME_TOPIC"
            topic_relation = "SAME_TOPIC"
        else:
            relation = "NEW_TOPIC"
            topic_relation = "NEW_TOPIC"

        # A direct question about the currently rendered artifact is a semantic
        # artifact reference even when the dialogue classifier ranks it as a
        # generic question. The evidence comes from the existing structured
        # scene + semantic task vector, not from a word/phrase trigger list.
        scene_reference_similarity = 0.0
        visual_reference_candidate = False
        scene_has_rendered_artifact = bool(
            scene and any(
                isinstance(block, dict)
                and _clean_representation(
                    block.get("type")
                    or block.get("artifact_type")
                    or block.get("representation")
                ) in {
                    "diagram", "graph", "image", "gallery", "table",
                    "formula", "code", "link", "audio", "video", "file",
                }
                for block in (scene.get("render_blocks") or [])
            )
        )
        if scene_has_rendered_artifact and (
            not current_self_contained or artifact_reference_evidence >= 0.06
        ):
            scene_text = self._scene_semantic_text(scene)
            if scene_text:
                scene_similarity_result = self.similarity(current, scene_text)
                scene_reference_similarity = float(
                    scene_similarity_result.get("score", 0.0) or 0.0
                )
            semantic_best_rep = str(features.get("semantic_best_representation") or "").lower()
            semantic_best_obj = str(features.get("semantic_best_object") or "").lower()
            semantic_best_op = str(features.get("semantic_best_operation") or "").lower()
            visual_task = (
                semantic_best_rep in {"diagram", "graph", "image", "gallery", "table", "formula"}
                or semantic_best_obj in {"diagram", "graph", "image", "gallery", "table", "formula"}
                or features.get("visual_action")
                or features.get("geometry_object")
            )
            artifact_question = (
                artifact_reference_evidence >= 0.06
            )
            answer_about_artifact = semantic_best_op in {
                "answer", "list", "analyze", "explain", "compare", "present", "build"
            }
            visual_reference_candidate = bool(
                answer_about_artifact
                and visual_task
                and artifact_question
                and scene_reference_similarity >= 0.16
            )

        if visual_reference_candidate:
            relation = "ARTIFACT_REFERENCE"
            topic_relation = "SAME_TOPIC"
            subtype = "REFERENCE_OR_DEVELOPMENT"
            semantic_reference = True
        elif relation == "MEMORY_QUERY":
            subtype = "MEMORY_QUERY"
        elif relation == "CONTINUE_TOPIC":
            subtype = "REFERENCE_OR_DEVELOPMENT" if semantic_reference else "DEVELOPMENT"
        elif relation == "SAME_TOPIC":
            subtype = "NEW_TASK_SAME_TOPIC"
        else:
            subtype = relation

        previous_text = " ".join(x for x in (prev_a, prev_u, topic) if x)
        previous_tokens = {t for t in self._tokens(previous_text) if len(t) >= 3}
        current_tokens = [t for t in self._tokens(current) if len(t) >= 3]
        shared_tokens, new_tokens = [], []
        for token in current_tokens:
            target = shared_tokens if token in previous_tokens else new_tokens
            if token not in target:
                target.append(token)

        previous_render_types = list(scene.get("render_block_types") or [])
        previous_block_ids = [
            str(x.get("block_id"))
            for x in (scene.get("render_blocks") or [])
            if isinstance(x, dict) and x.get("block_id")
        ]

        dependency_score = max(
            0.92 if semantic_reference else 0.0,
            0.88 if semantic_memory_query and not current_self_contained else 0.0,
            continuation_evidence if not current_self_contained else 0.0,
            0.30 * answer_affinity + 0.24 * topic_affinity + 0.20 * dialogue_followup,
        )
        if current_self_contained and relation not in {"MEMORY_QUERY", "CONTINUE_TOPIC"}:
            dependency_score = 0.0

        continuation_score = dependency_score if relation in {"CONTINUE_TOPIC", "MEMORY_QUERY"} else 0.0
        independent_score = 1.0 - dependency_score

        request_dependency = (
            "reference" if semantic_reference
            else "memory_query" if semantic_memory_query
            else "continuation" if relation == "CONTINUE_TOPIC"
            else "same_topic" if relation == "SAME_TOPIC"
            else "independent"
        )

        return {
            "relation": relation,
            "topic_relation": topic_relation,
            "request_relation": (
                "ARTIFACT_REFERENCE" if semantic_reference
                else "MEMORY_QUERY" if semantic_memory_query
                else relation
            ),
            "request_dependency": request_dependency,
            "request_dependency_score": float(max(0.0, min(1.0, dependency_score))),
            "current_request_complete": current_self_contained,
            "continuation_score": float(max(0.0, min(1.0, continuation_score))),
            "independent_score": float(max(0.0, min(1.0, independent_score))),
            "relation_strength": float(max(0.0, min(1.0, relation_strength))),
            "subtype": subtype,
            "scores": {
                **sims,
                "dialogue_followup": dialogue_followup,
                "reference_evidence": reference_evidence,
                "memory_query_evidence": memory_evidence,
                "structural_followup": dependency_score,
            },
            "active_topic": topic,
            "active_goal": goal,
            "previous_user_turn": prev_u,
            "previous_april_turn": prev_a,
            "shared_tokens": shared_tokens[:40],
            "new_tokens": new_tokens[:40],
            "delta_mode": "extend" if relation in {"CONTINUE_TOPIC", "MEMORY_QUERY"} else "start",
            "avoid_repeat": True,
            "reuse_existing_scene": relation in {"CONTINUE_TOPIC", "MEMORY_QUERY"} and bool(scene.get("scene_id")),
            "previous_scene_id": scene.get("scene_id") if relation in {"CONTINUE_TOPIC", "MEMORY_QUERY"} else "",
            "previous_render_types": previous_render_types,
            "previous_block_ids": previous_block_ids,
            "explicit_reference": semantic_reference,
            "anaphoric": semantic_reference,
            "source": "quantum_dialogue_vector_v6_semantic",
            "decision_owner": DECISION_OWNER,
            "trigger_independent": False,
            "semantic_dialogue_label": dialogue_best,
            "semantic_dialogue_confidence": dialogue_best_score,
            "visual_reference_candidate": bool(visual_reference_candidate),
            "visual_scene_similarity": float(max(0.0, min(1.0, scene_reference_similarity))),
            "artifact_reference_evidence": bool(visual_reference_candidate),
            "artifact_reference_semantic_score": float(max(0.0, min(1.0, artifact_reference_evidence))),
        }

    def _linguistic(self,text):
        tokens=self._tokens(text)
        return {
            "language":None,"tokens":tokens,"lemmas":tokens,"pos":[],
            "dependencies":[],"entities":[],"sentences":[text] if text else [],
            "source":"quantum_matrix","engine":"quantum_interpretation_engine_v3"
        }

    def similarity(self,text_a,text_b):
        left,right=self.normalize(text_a),self.normalize(text_b)
        if not left or not right:
            return {"score":0.0,"source":"unresolved_semantic_similarity","measured":False,"cached":False}
        if self._semantic_encoder is not None:
            try:
                v=self._semantic_encoder.encode([left,right],normalize_embeddings=True)
                return {"score":max(0.0,min(1.0,float(v[0]@v[1]))),
                        "source":"sentence_transformer","measured":True,"cached":False}
            except Exception:
                pass
        if self._vectorizer is not None and cosine_similarity is not None:
            try:
                v=self._vectorizer.transform([left,right])
                return {"score":max(0.0,min(1.0,float(cosine_similarity(v[0],v[1])[0][0]))),
                        "source":"quantum_matrix_tfidf","measured":True,"cached":False}
            except Exception:
                pass
        return {"score":0.0,"source":"unresolved_semantic_similarity","measured":False,"cached":False}

    def similarities(self,text,candidates):
        return {self.normalize(c):self.similarity(text,c)["score"] for c in candidates if self.normalize(c)}

    def prewarm_static(self,candidates):
        return len({self.normalize(x) for x in candidates if self.normalize(x)})

    def _history(self,history):
        last_a=last_u=""; reply_to=None
        for item in reversed(history if isinstance(history,list) else []):
            if not isinstance(item,dict): continue
            metadata=item.get("metadata") if isinstance(item.get("metadata"),dict) else {}
            content=self.normalize(item.get("content") or item.get("text") or item.get("answer") or "")
            if (metadata.get("internal_context") or metadata.get("internal_turn")
                    or metadata.get("source") in {"internal_visual", "internal_visual_analysis", "passive_visual_helper"}
                    or content.startswith("VISUAL_ANALYSIS:")):
                continue
            role=str(item.get("role") or "").lower()
            if not last_a:
                obj=item.get("april") if isinstance(item.get("april"),dict) else item
                if role in {"assistant","april","bot"} or isinstance(item.get("april"),dict):
                    last_a=self.normalize(obj.get("answer") or obj.get("content") or obj.get("summary"))
                    reply_to=item.get("turn_id")
            if not last_u:
                obj=item.get("user") if isinstance(item.get("user"),dict) else item
                if role in {"user","human"} or isinstance(item.get("user"),dict):
                    last_u=self.normalize(obj.get("text") or obj.get("content") or obj.get("answer"))
            if last_a and last_u: break
        return last_a,last_u,reply_to

    def measure(self,text,*,previous_assistant="",previous_user="",active_topic="",active_goal="",modalities=None):
        text=self.normalize(text)
        key=(text,self.normalize(previous_assistant),self.normalize(previous_user),
             self.normalize(active_topic),self.normalize(active_goal),
             tuple(sorted((modalities or {}).keys())))
        with self._lock:
            if key in self._cache: return self._cache[key]
        focus_text = self._semantic_focus_text(text)
        scores={
            "dialogue":self._family_scores(text,"dialogue",SEMANTIC_TURN_PROTOTYPES),
            "representation":self._family_scores(focus_text or text,"representation",REPRESENTATION_HYPOTHESES),
            "domain":self._family_scores(text,"domain",DOMAIN_HYPOTHESES),
            "capability":self._family_scores(text,"capability",CAPABILITY_HYPOTHESES),
            "operation":self._family_scores(text,"operation",OPERATION_HYPOTHESES),
            "object":self._family_scores(focus_text or text,"object",OBJECT_HYPOTHESES),
            "goal":self._family_scores(text,"goal",GOAL_HYPOTHESES),
            "visual_schema":self._family_scores(text,"visual_schema",VISUAL_SCHEMA_HYPOTHESES),
        }
        for label in self._negated_representation_labels(text):
            if label in scores["representation"]:
                scores["representation"][label] *= 0.05
            if label in scores["object"]:
                scores["object"][label] *= 0.05

        # Structural semantic enrichment for visual construction. This keeps the
        # matrix probabilistic while making equivalent phrasings converge on the
        # same task vector instead of depending on the exact verb "покажи" versus
        # "изобрази".
        request_features = self._semantic_request_features(text, scores)
        if (
            request_features["visual_construction"]
            and not self._negated_representation_labels(text)
        ):
            # Semantic-family agreement is the only enrichment source.  There is
            # no phrase table and no renderer trigger.
            scores["representation"]["diagram"] = max(
                scores["representation"].get("diagram", 0.0),
                float(scores["representation"].get("diagram", 0.0) or 0.0),
            )
            scores["operation"]["build"] = max(
                scores["operation"].get("build", 0.0),
                float(scores["operation"].get("present", 0.0) or 0.0),
            )
            scores["goal"]["visualize"] = max(
                scores["goal"].get("visualize", 0.0),
                float(scores["goal"].get("transform", 0.0) or 0.0),
            )
            request_features = self._semantic_request_features(text, scores)

        ctx=self._context_scores(text,previous_assistant,previous_user,active_topic,active_goal)
        def rank(d):
            return sorted(d.items(),key=lambda x:x[1],reverse=True)
        rep=rank(scores["representation"]); ops=rank(scores["operation"])
        objs=rank(scores["object"]); goals=rank(scores["goal"]); dial=rank(scores["dialogue"])
        profile={
            "dialogue_scores":scores["dialogue"],"dialogue_best":dial[0][0] if dial else "independent",
            "dialogue_confidence":float(dial[0][1]) if dial else 0.0,
            "dialogue_margin":float(dial[0][1]-dial[1][1]) if len(dial)>1 else 0.0,
            "representation_scores":scores["representation"],
            "domain_scores":scores["domain"],"capability_scores":scores["capability"],
            "operation_scores":scores["operation"],"object_scores":scores["object"],"goal_scores":scores["goal"],
            "visual_schema_scores":scores["visual_schema"],
            "request_features":request_features,
            "context_scores":ctx,
            "best_representation":rep[0][0] if rep else "text",
            "best_representation_score":float(rep[0][1]) if rep else 0.0,
            "representation_margin":float(rep[0][1]-rep[1][1]) if len(rep)>1 else (float(rep[0][1]) if rep else 0.0),
            "best_operation":ops[0][0] if ops else "answer",
            "best_object":objs[0][0] if objs else "text",
            "best_goal":goals[0][0] if goals else "understand",
            "source":"quantum_matrix_semantic_measurement_v3",
            "identity_request":bool(dial and dial[0][0]=="identity" and dial[0][1]>=0.12),
            "fast_social":bool(dial and dial[0][0] in {"identity","greeting"} and dial[0][1]>=0.18),
        }
        with self._lock:
            self._cache[key]=profile
            if len(self._cache)>self._cache_limit: self._cache.pop(next(iter(self._cache)))
        return profile

    def _resolve_production(self,text,profile,explicit):
        # Canonical upstream interpretation may lock one representation.
        explicit_values=[_clean_representation(x) for x in (explicit or [])]
        explicit_values=[x for x in explicit_values if x]
        if len(explicit_values)==1:
            return explicit_values[0],"explicit_current_request",True

        rep=dict(profile.get("representation_scores") or {})
        obj=dict(profile.get("object_scores") or {})
        op=dict(profile.get("operation_scores") or {})
        goal=dict(profile.get("goal_scores") or {})
        features=dict(profile.get("request_features") or {})

        def rank(items):
            return sorted(items.items(), key=lambda x: float(x[1]), reverse=True)

        rep_rank=rank(rep); obj_rank=rank(obj); op_rank=rank(op); goal_rank=rank(goal)
        best_rep=rep_rank[0][0] if rep_rank else "text"
        best_rep_score=float(rep.get(best_rep,0.0))
        second_rep_score=float(rep_rank[1][1]) if len(rep_rank)>1 else 0.0
        best_obj=obj_rank[0][0] if obj_rank else "text"
        best_obj_score=float(obj.get(best_obj,0.0))
        best_op=op_rank[0][0] if op_rank else "answer"
        best_op_score=float(op.get(best_op,0.0))
        best_goal=goal_rank[0][0] if goal_rank else "understand"
        best_goal_score=float(goal.get(best_goal,0.0))

        # A textual/ASCII schema is an optional format advisory for the TEXT
        # block. It must win only when the semantic matrix itself identifies a
        # textual-schema intent and the request has not already been resolved
        # to a different structured representation.
        visual_schema_scores = dict(profile.get("visual_schema_scores") or {})
        text_schema_score = float(visual_schema_scores.get("text_schema", 0.0) or 0.0)
        diagram_score = float(visual_schema_scores.get("diagram", 0.0) or 0.0)
        text_schema_format_intent = bool(
            text_schema_score >= 0.15
            and text_schema_score >= diagram_score + 0.04
            and best_op in {"build", "present", "answer", "explain", "list", "modify"}
        )
        if (
            text_schema_format_intent
            and best_rep in {"text", "diagram"}
            and best_obj in {"text", "diagram"}
        ):
            return "text", "semantic_text_schema_format_advisory", True

        compatible_ops={
            "graph":{"build","modify","present","calculate","analyze","list","explain"},
            "diagram":{"build","modify","present","explain"},
            "table":{"build","modify","present","compare","list","explain"},
            "formula":{"build","modify","present","calculate","explain","answer"},
            "link":{"retrieve","present","answer"},
            "code":{"build","modify","present","explain"},
            "image":{"build","modify","present"},
            "gallery":{"build","present"},
            "file":{"retrieve","present"},
            "audio":{"build","present"},
            "video":{"build","present"},
            "action":{"build","modify","present"},
            "scene":{"build","modify","present"},
            "memory":{"retrieve","answer","present"},
            "visual_context":{"answer","analyze","explain"},
        }
        aligned = best_op in compatible_ops.get(best_rep,set())

        # Strong structural interpretation for a self-contained visual construction.
        # This is intentionally a task-vector rule: operation + object/constraint
        # evidence must agree before a structured representation is locked.
        if features.get("visual_construction") and not self._negated_representation_labels(text):
            return "diagram", "semantic_visual_construction", True

        if best_rep != "text" and aligned:
            rep_margin = best_rep_score - second_rep_score
            object_agreement = best_obj == best_rep and best_obj_score >= 0.05
            representation_clear = (
                best_rep_score >= 0.10 and
                (rep_margin >= 0.015 or best_rep_score >= 0.22)
            )
            if representation_clear and (object_agreement or best_rep_score >= 0.16):
                return best_rep,"task_object_goal_resolution",True

            production_ops = {"build", "modify", "present"}
            production_signal = max(float(op.get(name,0.0) or 0.0) for name in production_ops)
            production_goal = max(float(goal.get(name,0.0) or 0.0) for name in {"visualize","transform","present","organize"})
            object_alignment = best_obj == best_rep and best_obj_score >= 0.10
            representation_dominance = best_rep_score >= max(0.09, float(rep.get("text",0.0) or 0.0) + 0.025)
            structured_task = (
                best_rep != "text"
                and object_alignment
                and representation_dominance
                and (production_signal >= 0.055 or (aligned and best_op_score >= 0.08))
                and (production_goal >= 0.035 or best_rep_score >= 0.14)
            )
            if structured_task:
                return best_rep,"semantic_task_vector_resolution",True
            if aligned and best_rep_score >= 0.10 and best_op_score >= 0.08:
                return best_rep,"operation_representation_resolution",True

        return "text","unresolved",False

    def dialogue(self,text,previous_assistant="",previous_user="",active_goal="",active_topic="",previous_scene=None):
        p=self.measure(text,previous_assistant=previous_assistant,previous_user=previous_user,
                       active_goal=active_goal,active_topic=active_topic)
        vector=self._dialogue_relation_engine(
            text,
            previous_assistant=previous_assistant,
            previous_user=previous_user,
            active_goal=active_goal,
            active_topic=active_topic,
            previous_scene=previous_scene,
        )
        d=p["dialogue_scores"]
        return {
            "dialogue":{
                "label":p["dialogue_best"],
                "confidence":p["dialogue_confidence"],
                "continuation_score":vector["continuation_score"],
                "reference_score":max(
                    vector["scores"].get("previous_assistant",0.0),
                    vector["scores"].get("previous_scene_topic",0.0),
                ),
                "topic_score":max(
                    vector["scores"].get("active_topic",0.0),
                    vector["scores"].get("previous_scene_topic",0.0),
                ),
                "goal_score":vector["scores"].get("active_goal",0.0),
            },
            "linguistic":self._linguistic(text),
            "continuation":vector["relation"]=="CONTINUE_TOPIC",
            "reference_to_previous":bool(vector.get("request_relation") == "ARTIFACT_REFERENCE"),
            "dialogue_relation":vector,
            "identity_request":p["identity_request"],
            "nli":{"labels":list(d),"scores":list(d.values()),"source":"quantum_matrix"},
            "decision_owner":DECISION_OWNER,"evidence_only":True,
            "engine":"quantum_dialogue_vector_engine_v4",
        }

    def representations(self,text,context=""):
        p=self.measure(text,active_topic=context)
        return {
            "nli":{"labels":list(p["representation_scores"]),"scores":list(p["representation_scores"].values()),"source":"quantum_matrix"},
            "measurements":[{"type":k,"score":float(v),"source":"quantum_matrix"}
                            for k,v in sorted(p["representation_scores"].items(),key=lambda x:x[1],reverse=True)],
            "context_similarity":{"score":p["context_scores"].get("active_topic",0.0),"source":"quantum_matrix"},
            "decision_owner":DECISION_OWNER,"evidence_only":True,
            "engine":"quantum_representation_matrix_view_v3"
        }

    def domains(self,text):
        p=self.measure(text)
        return {"measurements":[{"domain":k,"score":float(v)}
                                for k,v in sorted(p["domain_scores"].items(),key=lambda x:x[1],reverse=True)],
                "decision_owner":DECISION_OWNER,"evidence_only":True,
                "engine":"quantum_domain_matrix_view_v3"}

    def _scene_matrix(self,p):
        reps=p["representation_scores"]
        labels=list(SCENE_MATRIX_LABELS)
        vals=[float(reps.get(x,0.0)) for x in labels]
        top=max(vals) if vals else 0.0
        scores=[v/top if top>0 else 0.0 for v in vals]
        ranked=sorted(zip(labels,scores),key=lambda x:x[1],reverse=True)
        return {
            "labels":[x[0] for x in ranked],"scores":[round(float(x[1]),6) for x in ranked],
            "best_scene":ranked[0][0] if ranked else "text",
            "best_score":round(float(ranked[0][1] if ranked else 0.0),6),
            "margin":round(float((ranked[0][1]-ranked[1][1]) if len(ranked)>1 else 0.0),6),
            "feature_order":list(SCENE_MATRIX_FEATURES),"matrix_shape":[len(labels),len(SCENE_MATRIX_FEATURES)],
            "evidence_only":True,"engine":"quantum_matrix_v3","decision_owner":DECISION_OWNER
        }

    @classmethod
    def _reference_resolution(
        cls,
        text: str,
        previous_assistant: str,
        previous_user: str = "",
        semantic_profile: dict[str, Any] | None = None,
        reference_authorized: bool = False,
    ) -> dict:
        """Resolve an already-authorized semantic reference generically.

        Authorization comes from the canonical dialogue vector.  This method
        extracts a candidate antecedent from the immediately previous exchange;
        it does not classify the current turn using word triggers.
        """
        current = cls.normalize(text)
        prev = cls.normalize(previous_assistant)
        if not current or not prev or not reference_authorized:
            return {
                "present": False, "target": "", "candidates": [], "confidence": 0.0,
                "source": "semantic_entity_reference", "anaphoric": False,
                "short_followup": False, "resolved": False,
            }

        profile = semantic_profile if isinstance(semantic_profile, dict) else {}
        candidates: list[str] = []

        # Generic entity extraction from the authoritative previous USER↔APRIL
        # pair. This is content extraction, not request classification.
        patterns = (
            r"\b(?:[А-ЯЁA-Z][а-яёa-z]+(?:\s+[А-ЯЁA-Z][а-яёa-z]+){1,4})\b",
            r"\b[А-ЯЁA-Z][а-яёa-z]{2,}\b",
        )
        stop = {
            "Это", "Он", "Она", "Они", "Когда", "Куда",
            "Построй", "Покажи", "Создай", "Изобрази",
            "Нарисуй", "Чертёж", "Чертеж", "Готов",
            "имеет", "имеют", "стороны", "сторон", "длина",
            "длины", "сантиметр", "сантиметры",
        }
        for source in (previous_user, prev):
            for pattern in patterns:
                for match in re.findall(pattern, source):
                    value = cls.normalize(match).strip('.,:;()[]{}<>—-"')
                    if value and value not in stop and value not in candidates:
                        candidates.append(value)
                    if len(candidates) >= 16:
                        break
                if len(candidates) >= 16:
                    break

        if len(candidates) < 16:
            ignored = {
                "покажи", "показать", "изобрази", "изобразить", "создай", "создать",
                "построй", "построить", "начерти", "начертить", "нарисуй", "нарисовать",
                "чертёж", "чертеж", "чертежа", "чертёже", "сторона", "сторонами", "стороны",
                "это", "этот", "эта", "эти", "его", "ее", "её", "их",
            }
            for token in cls._tokens(previous_user.lower()):
                if len(token) >= 4 and token not in ignored and token not in {x.lower() for x in candidates}:
                    candidates.append(token)
                if len(candidates) >= 16:
                    break

        target = max(
            candidates,
            key=lambda value: (
                1 if any(token.isalpha() for token in cls._tokens(value)) else 0,
                len(value.split()),
                len(value),
            ),
            default="",
        )
        confidence = 0.96 if target else 0.0

        return {
            "present": bool(target),
            "target": target,
            "candidates": candidates[:12],
            "confidence": confidence,
            "source": "semantic_entity_reference",
            "anaphoric": True,
            "short_followup": len(cls._tokens(current)) <= 8,
            "resolved": bool(target),
            "semantic_reference_authorized": True,
            "semantic_profile": {
                "best_dialogue": cls.normalize(profile.get("dialogue_best")),
                "best_representation": cls.normalize(profile.get("best_representation")),
            },
        }

    def _resolve_scene_context(self,text,state,continuation,reference,memory=False,active_topic=""):
        if not isinstance(state,dict) or not (continuation or reference or memory): return {}
        scene=state.get("current_visual_scene") or state.get("active_visual_scene")
        if not isinstance(scene,dict) or not scene.get("scene_id"): return {}
        return {
            "relation":"current_scene","confidence":1.0,"scene_id":scene.get("scene_id"),
            "turn_id":scene.get("turn_id"),"topic":self.normalize(scene.get("topic")),
            "user_request":self.normalize(scene.get("user_request") or scene.get("current_request")),
            "answer":self.normalize(scene.get("april_answer") or scene.get("answer") or scene.get("content")),
            "summary":self.normalize(scene.get("summary")),
            "render_block_types":list(scene.get("render_block_types") or []),
            "presentation_types":list(scene.get("presentation_types") or []),
            "render_blocks":list(scene.get("render_blocks") or []),
            "presentation_signals":list(scene.get("presentation_signals") or []),
            "semantic_state":scene.get("semantic_state") if isinstance(scene.get("semantic_state"),dict) else {},
            "supported_payloads":list(scene.get("supported_payloads") or []),
            "renderer_state":scene.get("renderer_state") if isinstance(scene.get("renderer_state"),dict) else {},
            "semantic_source":"interpretation_scene_resolution_v3","evidence_only":True
        }

    def interpret(self,text,cognition=None,semantic=None,history=None,state=None):
        text=self.normalize(text)
        if not text: return None
        cognition=cognition if isinstance(cognition,dict) else {}
        semantic=semantic if isinstance(semantic,dict) else {}
        state=state if isinstance(state,dict) else {}
        history=history if isinstance(history,list) else []
        last_a,last_u,reply_to=self._history(history)
        active_topic=self.normalize(state.get("active_topic") or state.get("current_topic") or semantic.get("active_topic") or cognition.get("active_topic"))
        active_goal=self.normalize(state.get("active_goal") or state.get("current_goal") or semantic.get("active_goal") or cognition.get("active_goal"))
        p=self.measure(text,previous_assistant=last_a,previous_user=last_u,active_topic=active_topic,active_goal=active_goal)
        previous_scene = state.get("current_visual_scene") or state.get("active_visual_scene")
        if not isinstance(previous_scene, dict):
            previous_scene = {}
        # Internal visual/tool scenes are not dialog anchors.
        try:
            scene_topic = self.normalize(previous_scene.get("topic") or previous_scene.get("user_request"))
            scene_meta = previous_scene.get("metadata") if isinstance(previous_scene.get("metadata"), dict) else {}
            internal_scene = bool(
                previous_scene.get("internal_context")
                or previous_scene.get("internal_turn")
                or scene_meta.get("internal_context")
                or scene_topic.startswith("VISUAL_ANALYSIS:")
            )
            if internal_scene:
                previous_scene = {}
        except Exception:
            pass
        dialogue_packet = self.dialogue(
            text,
            previous_assistant=last_a,
            previous_user=last_u,
            active_goal=active_goal,
            active_topic=active_topic,
            previous_scene=previous_scene,
        )
        d=dialogue_packet["dialogue"]
        dialogue_vector=dialogue_packet.get("dialogue_relation", {})
        explicit=(semantic.get("required_representations") or cognition.get("required_representations") or [])
        production,source,locked=self._resolve_production(text,p,explicit)
        continuation=bool(
            dialogue_packet.get("continuation")
            or dialogue_vector.get("relation") == "CONTINUE_TOPIC"
        )
        # A short continuation question does not acquire a structured renderer
        # merely because the representation matrix found a weak candidate.
        # Structured output must be supported by the current turn's operation,
        # object and goal evidence (or an explicit upstream representation).
        if production != "text" and not explicit:
            op = str(p.get("best_operation") or "").lower()
            obj = str(p.get("best_object") or "").lower()
            goal = str(p.get("best_goal") or "").lower()
            obj_score = float(p.get("object_scores", {}).get(production, 0.0) or 0.0)
            current_visual_intent = (
                locked
                or (
                    op in {"build", "modify", "present", "explain"}
                    and obj == production
                    and obj_score >= 0.10
                    and goal in {"visualize", "transform", "present", "organize"}
                )
            )
            # `locked` means the representation was already resolved from the
            # complete semantic task vector. Never demote such a decision merely
            # because another semantic family (for example explanation) ranked
            # slightly higher. This is a semantic contract, not a word trigger.
            if not current_visual_intent:
                production = "text"
                source = "current_turn_representation_not_established"
                locked = False
        # A semantically resolved continuation of a visual scene keeps the same
        # output representation. The previous structured artifact is evidence of
        # the object being modified; no lexical renderer trigger is used.
        if continuation and production == "text" and isinstance(previous_scene, dict):
            prior_types = [
                _clean_representation(x)
                for x in (previous_scene.get("render_block_types") or [])
            ]
            if not prior_types:
                prior_types = [
                    _clean_representation(
                        block.get("type")
                        or block.get("artifact_type")
                        or block.get("representation")
                    )
                    for block in (previous_scene.get("render_blocks") or [])
                    if isinstance(block, dict)
                ]
            prior_structured = [x for x in prior_types if x in STRUCTURED_REPRESENTATIONS]
            operation = p.get("best_operation")
            dialogue_label = self.normalize(dialogue_vector.get("semantic_dialogue_label")).lower()
            if prior_structured and operation in {"modify", "build", "present", "list", "analyze"}:
                production = prior_structured[0]
                source = "semantic_continuity_preserve_representation"
                locked = True
            elif prior_structured and dialogue_label in {"continuation", "reformulation", "correction", "reference"}:
                production = prior_structured[0]
                source = "semantic_continuity_preserve_representation"
                locked = True

        reference=bool(
            dialogue_vector.get("request_relation") == "ARTIFACT_REFERENCE"
            or dialogue_vector.get("reference_to_previous")
        )
        memory=bool(
            p["dialogue_best"] == "memory_query"
            or dialogue_vector.get("request_relation") == "MEMORY_QUERY"
        )
        semantic_profile_for_reference = {
            **p,
            "dialogue_best": p.get("dialogue_best"),
        }
        reference_resolution = self._reference_resolution(
            text,
            last_a,
            last_u,
            semantic_profile=semantic_profile_for_reference,
            reference_authorized=reference,
        )
        explicit_reference = bool(dialogue_vector.get("request_relation") == "ARTIFACT_REFERENCE")
        if reference_resolution.get("resolved") and reference_resolution.get("target") and explicit_reference:
            reference = True
            continuation = True
            dialogue_vector["reference_resolution"] = reference_resolution
            dialogue_vector["resolved_reference"] = reference_resolution.get("target")
            # An explicit artifact reference can inherit the previous structured
            # representation even when the current sentence omits its modality.
            if production == "text" and isinstance(previous_scene, dict):
                prior_types = [_clean_representation(x) for x in (previous_scene.get("render_block_types") or [])]
                if not prior_types:
                    prior_types = [_clean_representation(
                        block.get("type") or block.get("artifact_type") or block.get("representation")
                    ) for block in (previous_scene.get("render_blocks") or []) if isinstance(block, dict)]
                prior_structured = [x for x in prior_types if x in STRUCTURED_REPRESENTATIONS]
                if prior_structured:
                    production = prior_structured[0]
                    source = "reference_reuse_existing_representation"
                    locked = True

        # A resolved artifact reference is normally an information request about
        # the existing result, not a request to render that result again. Keep
        # the provider-facing output textual unless the current semantic task
        # explicitly requires a new/modified structured artifact.
        artifact_reference_answer = bool(
            reference
            and dialogue_vector.get("artifact_reference_evidence")
            and str(p.get("best_operation") or "").lower() in {
                "answer", "list", "analyze", "explain", "retrieve", "build"
            }
        )
        if artifact_reference_answer:
            production = "text"
            source = "artifact_reference_answer"
            locked = True
            dialogue_vector["artifact_reference_answer"] = True
        resolved_scene=self._resolve_scene_context(
            text,
            state,
            continuation,
            reference,
            memory=memory,
            active_topic=active_topic,
        )
        resolved_reference = reference_resolution.get("target") or ""
        resolved_request = text
        if resolved_reference and (continuation or reference):
            # Structural discourse resolution: make the provider-facing request
            # explicit without hard-coded topic/entity rules.
            resolved_request = (
                f"{text}\n\nContextual referent resolved from the immediately previous human exchange: "
                f"{resolved_reference}. Answer the current request about that referent without asking the user to repeat it."
            )
        if reference_resolution.get("resolved") and reference_resolution.get("target"):
            resolved_scene = dict(resolved_scene or {})
            resolved_scene["reference_target"] = reference_resolution.get("target")
            resolved_scene["reference_resolution"] = dict(reference_resolution)
        evidence=[{"label":k,"score":float(v),"source":"quantum_matrix","positive":True,"details":{}}
                  for k,v in sorted(p["representation_scores"].items(),key=lambda x:x[1],reverse=True) if float(v)>=0.20]
        domains=[k for k,v in p["domain_scores"].items() if float(v)>=0.20]
        matrix=self._scene_matrix(p)
        visual_schema_scores = dict(p.get("visual_schema_scores") or {})
        visual_schema_rank = sorted(visual_schema_scores.items(), key=lambda item: float(item[1]), reverse=True)
        visual_schema = visual_schema_rank[0][0] if visual_schema_rank else ""
        visual_schema_confidence = float(visual_schema_rank[0][1]) if visual_schema_rank else 0.0
        text_schema_score = float(
            p.get("request_features", {}).get("ascii_schema_score", 0.0) or 0.0
        )
        ascii_schema_advisory = bool(
            production == "text"
            and text_schema_score >= 0.15
            and p.get("best_operation") in {"build", "present", "answer", "explain", "list", "modify"}
        )
        semantic_task={
            "operation":p["best_operation"],"object":p["best_object"],"goal":p["best_goal"],
            "representation":production,
            "visual_schema":visual_schema,
            "visual_schema_confidence":visual_schema_confidence,
            "ascii_schema_advisory": ascii_schema_advisory,
            "ascii_schema_score": float(p.get("request_features", {}).get("ascii_schema_score", 0.0) or 0.0),
            "operation_scores":p["operation_scores"],"object_scores":p["object_scores"],"goal_scores":p["goal_scores"]
        }
        presentation={
            "version":"quantum_interpretation_transport_v3","decision_owner":DECISION_OWNER,
            "single_route":True,"production_representation":production,
            "signals":[{
                "type":production,"renderer":"semantic_signal","engine":"semantic_interpretation",
                "source":"QUANTUM_INTERPRETATION_ENGINE","evidence_only":True
            }]
        }
        if ascii_schema_advisory:
            presentation["format_advisory"] = {
                "format": "ascii",
                "scope": "text_block",
                "mode": "optional",
                "reason": "semantic_text_schema_request",
            }
        result=build_result(text)
        result.update({
            "type":p["dialogue_best"],"subtype":production,"scene_type":production,
            "normalized":text,"required_domains":domains,"candidate_domains":domains,
            "required_representations":[production],"candidate_representations":[production],
            "requested_representations":[production],"requested_representation":production,
            "production_representation":production,"production_representation_locked":locked,
            "production_representation_source":source,
            "production_representation_confidence":max(
                p["representation_scores"].get(production,0.0),
                p["object_scores"].get(production,0.0),
                p["goal_scores"].get("visualize" if production in {"graph","diagram","image","gallery"} else "present",0.0)
            ),
            "representation_evidence":evidence,
            "quantum_representation_measurement":{
                "measurements":evidence,"production_representation":production,
                "production_representation_locked":locked,"scene_matrix":matrix
            },
            "semantic_task":semantic_task,
            "ascii_schema_advisory": ascii_schema_advisory,
            "resolved_scene":resolved_scene,
            "reference_resolution":reference_resolution,
            "presentation_transport":presentation,"presentation_signal":presentation,
            "presentation_signals":presentation["signals"],
            "dialogue_vector": {
                **dict(dialogue_vector or {}),
                "reference_resolution": reference_resolution,
                "resolved_reference": resolved_reference,
                "resolved_request": resolved_request,
            },
            "dialogue_delta": {
                "mode": dialogue_vector.get("delta_mode"),
                "shared_tokens": dialogue_vector.get("shared_tokens", []),
                "new_tokens": dialogue_vector.get("new_tokens", []),
                "avoid_repeat": True,
            },
            "render_continuity": {
                "mode": "extend" if continuation else "start",
                "avoid_repeat": True,
                "reuse_existing_scene": bool(dialogue_vector.get("reuse_existing_scene")),
                "previous_scene_id": dialogue_vector.get("previous_scene_id", ""),
                "previous_render_types": dialogue_vector.get("previous_render_types", []),
                "previous_block_ids": dialogue_vector.get("previous_block_ids", []),
            },
            "dialogue_contract":{
                "dialog_act":d["label"],"current_request":text,"continuation":continuation,
                "reference_to_previous":reference,"previous_april_turn":last_a,
                "previous_user_turn":last_u,"reply_to":reply_to,"active_goal":active_goal,
                "active_topic":active_topic,
                "reference_resolution":reference_resolution,
                "resolved_reference":resolved_reference,
                "artifact_reference_evidence": bool(
                    dialogue_vector.get("artifact_reference_evidence")
                ),
                "artifact_reference_answer": bool(
                    dialogue_vector.get("artifact_reference_answer")
                ),
                "visual_scene_similarity": float(
                    dialogue_vector.get("visual_scene_similarity", 0.0) or 0.0
                ),
                "resolved_request":resolved_request,
                "context_dependency":"memory_query" if memory else "continuation" if continuation else "reference" if reference else "independent",
                "relation": dialogue_vector.get("relation", "NEW_TOPIC"),
                "subtype": dialogue_vector.get("subtype", "NEW_TOPIC"),
                "avoid_repeat": True,
                "canonical":True,"version":"quantum_dialogue_field_v4"
            },
            "context_resolution":{
                "depends_on_previous_dialogue":bool(continuation or reference or memory),
                "resolved_scene":resolved_scene,"active_topic":active_topic,"active_goal":active_goal
            },
            "semantic_profile":{
                "active_topic":active_topic,"active_goal":active_goal,
                "previous_april_turn":last_a,"representation_scores":p["representation_scores"],
                "domain_scores":p["domain_scores"],"capability_scores":p["capability_scores"],
                "operation_scores":p["operation_scores"],"object_scores":p["object_scores"],
                "goal_scores":p["goal_scores"],"context_scores":p["context_scores"],
                "semantic_task":semantic_task,"engine":"quantum_interpretation_engine_v3"
            },
            "quantum_interpretation_field":{
                "linguistic":self._linguistic(text),"dialogue":d,"representation":evidence,
                "domain":[{"domain":k,"score":float(v)} for k,v in p["domain_scores"].items()],
                "context_vectors":p["context_scores"],"semantic_task":semantic_task,
                "production":presentation,"profile":p,"scene_matrix":matrix,
                "decision_owner":DECISION_OWNER,"evidence_only":True,"engine":"quantum_interpretation_engine_v3"
            },
            "quantum_matrix":matrix,"matrix_scene":matrix["best_scene"],
            "matrix_confidence":matrix["best_score"],"decision_owner":DECISION_OWNER,
            "routing_owner":DECISION_OWNER,"renderer_owner":DECISION_OWNER,"provider_calls":0,
            "canonical_transport":TRANSPORT_NAME,"semantic_authority":True,
            "semantic_decision_source":source,"representation_resolution":"task_object_goal",
            "legacy_keyword_matching":False,"avoid_trigger_execution":True,
            "machine_only":True,"single_route":True,"renderer_intent":production!="text",
            "render_intent":production!="text","prefer_renderer":production!="text",
            "renderer_scene_object":production!="text","visual_routing":production in {"graph","diagram","image","gallery"},
            "possible_capability":"renderer" if production!="text" else None,"possible_output":production,
            "possible_scene_type":production,"current_representation":production,
            "unresolved_intent":not locked,"memory_query":memory,
            "continuation":d["continuation_score"],"continuation_target":last_a or active_topic,
            "dialogue_relation": dialogue_vector.get("relation", "NEW_TOPIC"),
            "dialogue_subtype": dialogue_vector.get("subtype", "NEW_TOPIC"),
            "visual_schema": visual_schema,
            "visual_schema_confidence": visual_schema_confidence,
            "required_capabilities":["semantic_interpretation","dialogue_context"],
            "required_outputs":[production],"requested_outputs":[production],
            "response_mode":"structured" if production!="text" else "talk","renderer_first":production!="text",
            "discussion_mode":p["capability_scores"].get("discussion",0.0)>=0.60,
            "space_discussion":p["capability_scores"].get("space",0.0)>=0.60,
            "exploration":p["capability_scores"].get("exploration",0.0),
            "web_context":p["capability_scores"].get("web",0.0),
            "explicit_image_generation":p["representation_scores"].get("image",0.0),
            "lightweight_visual":production in {"graph","diagram","image","gallery"},
            "contains_object":bool(text),
            "contains_explanation":p["capability_scores"].get("information",0.0)>=0.60,
            "contains_analysis":p["capability_scores"].get("exploration",0.0)>=0.60,
            "content_role":"explanation" if p["capability_scores"].get("information",0.0)>=0.60
                           else "analysis" if p["capability_scores"].get("exploration",0.0)>=0.60 else None,
            "artifact_contract":{"contract":"scene_artifact","transport":TRANSPORT_NAME,
                                "scene_type":production,"representation":[production],"decision_owner":DECISION_OWNER},
            "semantic_engine_diagnostics":{
                "engine":"quantum_interpretation_engine_v4","domain_representation_gates":False,
                "capability_representation_gates":False,"lexical_routing":False,
                "token_overlap_context":False,"production_resolution":"task_object_goal",
                "single_route":True,"decision_owner":DECISION_OWNER
            },
        })
        result["evidence"]={"representation":evidence,
                            "domain":[{"domain":k,"score":float(v)} for k,v in p["domain_scores"].items()],
                            "math":p["representation_scores"].get("formula",0.0),
                            "code":p["representation_scores"].get("code",0.0),
                            "web":p["capability_scores"].get("web",0.0),
                            "image":p["representation_scores"].get("image",0.0),
                            "continuation":d["continuation_score"],
                            "exploration":p["capability_scores"].get("exploration",0.0),
                            "information":p["capability_scores"].get("information",0.0),
                            "dialogue":result["dialogue_contract"]}
        result["interpretation_state"]=synchronize_interpretation_context(build_interpretation_state(),result)
        result["transport_state"]=export_transport_state(result["interpretation_state"],result)
        result["transport_diagnostics"]=build_transport_diagnostics(result)
        bridge_machine_response(result,result["transport_state"])
        result["estimated_action_count"]=0
        result["response_complexity"]=None
        result["factory_targets"]=[]
        result["factory_order"]={"owner":DECISION_OWNER,"status":"evidence_only"}
        result["scene_strategy"]={"scene_strategy":"evidence_only","preferred_blocks":[production],"decision_owner":DECISION_OWNER}
        return result

    def fast_semantic_profile(self,text,previous_assistant="",previous_user="",active_topic="",active_goal=""):
        return self.measure(text,previous_assistant=previous_assistant,previous_user=previous_user,active_topic=active_topic,active_goal=active_goal)

    def turn_measurement(self,text,previous_assistant="",previous_user="",active_goal="",active_topic=""):
        p=self.measure(text,previous_assistant=previous_assistant,previous_user=previous_user,active_goal=active_goal,active_topic=active_topic)
        return {"linguistic":self._linguistic(text),
                "dialogue_nli":{"labels":list(p["dialogue_scores"]),"scores":list(p["dialogue_scores"].values()),"source":"quantum_matrix"},
                "representation_nli":{"labels":list(p["representation_scores"]),"scores":list(p["representation_scores"].values()),"source":"quantum_matrix"},
                "domain_nli":{"labels":list(p["domain_scores"]),"scores":list(p["domain_scores"].values()),"source":"quantum_matrix"},
                "capability_nli":{"labels":list(p["capability_scores"]),"scores":list(p["capability_scores"].values()),"source":"quantum_matrix"},
                "embeddings":dict(p["context_scores"]),"decision_owner":DECISION_OWNER,"evidence_only":True,
                "engine":"quantum_interpretation_turn_engine_v3"}

    def classify(self,text,hypotheses):
        p=self.measure(text); merged={}
        for fam in ("dialogue","representation","domain","capability","operation","object","goal"):
            merged.update(p.get(f"{fam}_scores",{}))
        ranked=sorted(((h,float(merged.get(h,0.0))) for h in hypotheses),key=lambda x:x[1],reverse=True)
        return {"labels":[x[0] for x in ranked],"scores":[x[1] for x in ranked],"source":"quantum_matrix"}

# Global representation universe remains visible to compatibility helpers.


@dataclass
class SemanticEvidence:
    label: str
    score: float
    source: str
    positive: bool = True
    details: Dict[str, Any] | None = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "score": max(0.0, min(1.0, float(self.score))),
            "source": self.source,
            "positive": bool(self.positive),
            "details": self.details or {},
        }


def build_result(text: str) -> dict[str, Any]:
    return {
        "type": "text",
        "subtype": None,
        "scene_type": None,
        "normalized": text,
        "content_role": None,
        "contains_object": bool(text),
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
        "decision_owner": DECISION_OWNER,
        "routing_owner": DECISION_OWNER,
        "renderer_owner": DECISION_OWNER,
        "provider_calls": 0,
        "single_route": True,
    }


def estimate_action_count(result: dict[str, Any]) -> int:
    reps = set(result.get("required_representations", []) or [])
    domains = set(result.get("required_domains", []) or [])
    count = len(reps) + len(domains)
    count += int(bool(result.get("contains_analysis") or result.get("contains_explanation")))
    count += 2 if result.get("explicit_image_generation") else 0
    return max(1, count)


def determine_response_complexity(result: dict[str, Any]) -> str:
    actions = estimate_action_count(result)
    if actions <= 1:
        return RESPONSE_COMPLEXITY_LOW
    if actions <= 3:
        return RESPONSE_COMPLEXITY_MEDIUM
    return RESPONSE_COMPLEXITY_HIGH


def build_factory_order(result: dict[str, Any]) -> dict[str, Any]:
    domains = list(result.get("required_domains", []) or [])
    return {
        "intent": result.get("type"),
        "goal": result.get("subtype"),
        "required_domains": domains,
        "required_rooms": list(domains),
        "required_artifacts": list(result.get("required_representations", []) or []),
        "quality_target": 0.95,
        "owner": DECISION_OWNER,
        "status": "evidence_only",
    }


def build_scene_strategy(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "scene_strategy": "evidence_only",
        "preferred_blocks": list(result.get("required_representations", []) or []),
        "content_role": result.get("content_role"),
        "scene_priority": "normal",
        "scene_contribution_mode": True,
        "scene_builder_profile": "processor_selected",
        "decision_owner": DECISION_OWNER,
    }


def build_interpretation_state() -> dict[str, dict[str, Any]]:
    return {
        "dialogue": {},
        "evidence": {},
        "cognition": {},
        "scene": {},
        "artifacts": {},
        "executor": {},
        "diagnostics": {},
    }


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
INTERPRETATION_ENTRYPOINT = TRANSPORT_NAME
INTERPRETATION_STATE_TEMPLATE = build_interpretation_state()


def safe_result_get(result: Any, key: str, default: Any = None) -> Any:
    if not isinstance(result, dict):
        return default
    value = result.get(key, default)
    return default if value is None else value


def ensure_transport_defaults(state: dict[str, Any] | None) -> dict[str, Any]:
    state = state or {}
    for key in ("dialogue", "scene", "executor", "artifacts", "diagnostics"):
        state.setdefault(key, {})
    return state


def synchronize_interpretation_context(
    state: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    state = ensure_transport_defaults(state)
    state["dialogue"]["profile"] = result.get("semantic_profile")
    state["dialogue"]["contract"] = result.get("dialogue_contract")
    state["evidence"]["engine"] = result.get("quantum_interpretation_field")
    state["scene"]["profile"] = result.get("scene_profile")
    state["scene"]["matrix"] = result.get("quantum_matrix")
    state["scene"]["resolved"] = result.get("resolved_scene")
    state["scene"]["presentation"] = result.get("presentation_transport")
    state["artifacts"]["contract"] = result.get("artifact_contract")
    state["executor"]["contract"] = result.get("executor_preparation_contract")
    return state


def export_transport_state(state: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    state = ensure_transport_defaults(state)
    for field, (section, key) in INTERPRETATION_TRANSPORT_FIELDS.items():
        if field in result:
            state[section][key] = result[field]
    state.setdefault("presentation", {})
    state["presentation"]["transport"] = result.get("presentation_transport")
    state["presentation"]["signals"] = list(result.get("presentation_signals") or [])
    state["diagnostics"]["route"] = [
        {"node": node, "status": "evidence", "payload": result.get(node)}
        for node in INTERPRETATION_ROUTE
    ]
    return state


def resolve_interpretation_payload(result: dict[str, Any]) -> dict[str, Any]:
    return result.get(TRANSPORT_NAME, {}) if isinstance(result, dict) else {}


def propagate_canonical_response(result: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    transport = state.setdefault("transport", {})
    response = transport.setdefault("response", {})
    response["content"] = safe_result_get(result, "normalized") or safe_result_get(
        result, "assistant_response", ""
    )
    return result



def _quantum_scene_projection(scene: dict[str, Any] | None) -> dict[str, Any]:
    scene = scene if isinstance(scene, dict) else {}
    return {
        "scene_id": scene.get("scene_id"),
        "turn_id": scene.get("turn_id"),
        "relation": scene.get("relation"),
        "topic": scene.get("topic"),
        "user_request": scene.get("user_request"),
        "answer": scene.get("answer"),
        "summary": scene.get("summary"),
        "semantic_state": scene.get("semantic_state") or {},
        "render_blocks": scene.get("render_blocks") or [],
        "presentation_signals": scene.get("presentation_signals") or [],
        "presentation_types": scene.get("presentation_types") or [],
        "renderer_state": scene.get("renderer_state") or {},
    }


def bridge_machine_response(result: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    machine = state.setdefault("machine_response", {})
    scene = state.setdefault("scene_contract", {})
    content = machine.get("content") or result.get("normalized") or result.get(
        "assistant_response", ""
    )
    machine["content"] = content
    scene.update({"content": content, "answer": content, "summary": content})
    if isinstance(result.get("resolved_scene"), dict):
        scene["resolved_scene"] = _quantum_scene_projection(result.get("resolved_scene"))
    if isinstance(result.get("presentation_transport"), dict):
        scene["presentation_transport"] = result.get("presentation_transport")
    result["machine_response"] = machine
    result["scene_contract"] = scene
    return result


def validate_response_complexity(result: dict[str, Any]) -> dict[str, Any]:
    complexity = result.get("response_complexity") or RESPONSE_COMPLEXITY_LOW
    result["response_complexity"] = complexity
    result["estimated_action_count"] = result.get("estimated_action_count") or 0
    result["semantic_response_complexity"] = complexity
    result["machine_response_complexity"] = complexity
    return result


def export_response_complexity(result: dict[str, Any]) -> dict[str, Any]:
    return {
        key: result.get(key)
        for key in (
            "response_complexity",
            "estimated_action_count",
            "semantic_response_complexity",
            "machine_response_complexity",
        )
    }


def build_transport_diagnostics(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "has_transport": bool(result.get(TRANSPORT_NAME)),
        "has_machine_response": bool(result.get("machine_response")),
        "has_scene_contract": bool(result.get("scene_contract")),
        "normalized": bool(result.get("normalized")),
        "decision_owner": result.get("decision_owner"),
        "provider_calls": result.get("provider_calls", 0),
    }


def build_interpretation_route(state: dict[str, Any], result: dict[str, Any]):
    state = export_transport_state(state, result)
    return state["diagnostics"]["route"]


# ---------------------------------------------------------------------------
# Compatibility helpers: all point into the one engine.
# ---------------------------------------------------------------------------

QUANTUM_INTERPRETATION_ENGINE = QuantumInterpretationEngine()

# Compatibility singleton names intentionally reference the same engine object.
QUANTUM_FAST_SEMANTIC = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_LINGUISTIC_ENGINE = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_EMBEDDING_ENGINE = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_INTENT_ENGINE = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_EVIDENCE_FUSION = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_DIALOGUE_ENGINE = QUANTUM_INTERPRETATION_ENGINE

# Public class aliases preserve import names without reinstating parallel engines.
QuantumFastSemanticEngine = QuantumInterpretationEngine
QuantumLinguisticEngine = QuantumInterpretationEngine
QuantumEmbeddingEngine = QuantumInterpretationEngine
QuantumIntentEngine = QuantumInterpretationEngine
QuantumEvidenceFusionEngine = QuantumInterpretationEngine
QuantumDialogueEngine = QuantumInterpretationEngine
QuantumSceneInterpretationMatrix = QuantumInterpretationEngine


# ---------------------------------------------------------------------------
# Visual + Dialogue Memory Understanding Engine
# ---------------------------------------------------------------------------
class QuantumMemoryUnderstandingEngine:
    """Parallel analysis of dialogue memory and visual-response memory.

    Evidence-only: it never routes, selects, rewrites, or creates renderer
    signals. It reconstructs relevant prior visual context for the existing
    Quantum Processor so the next response can be a new artifact carrying the
    meaning/schema of the previous visual response.
    """

    VERSION = "QUANTUM-MEMORY-UNDERSTANDING-V1"
    MAX_DIALOG_TURNS = 6
    MAX_VISUAL_BLOCKS = 4
    MAX_VISUAL_HISTORY = 4

    @staticmethod
    def _text(value):
        return str(value or "").strip()

    @staticmethod
    def _compact(value, depth=0):
        if depth > 3 or value in (None, "", [], {}):
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            out = {}
            for key, item in list(value.items())[:24]:
                compacted = QuantumMemoryUnderstandingEngine._compact(item, depth + 1)
                if compacted not in (None, "", [], {}):
                    out[str(key)] = compacted
            return out
        if isinstance(value, (list, tuple)):
            out = []
            for item in list(value)[:24]:
                compacted = QuantumMemoryUnderstandingEngine._compact(item, depth + 1)
                if compacted not in (None, "", [], {}):
                    out.append(compacted)
            return out
        return str(value)

    @classmethod
    def _dialogue_text(cls, history):
        result = []
        if not isinstance(history, list):
            return result
        for item in history[-cls.MAX_DIALOG_TURNS:]:
            if not isinstance(item, dict):
                continue
            role = cls._text(item.get("role")).lower()
            content = cls._text(item.get("content") or item.get("text") or item.get("answer"))
            if role and content:
                result.append(f"{role}: {content}")
        return result

    @classmethod
    def _visual_candidates(cls, visual_context):
        if not isinstance(visual_context, dict):
            return []
        candidates = []
        active = visual_context.get("active_visual_scene")
        if isinstance(active, dict):
            candidates.append(active)
        history = visual_context.get("visual_scene_history") or []
        if isinstance(history, list):
            candidates.extend(x for x in history[-cls.MAX_VISUAL_HISTORY:] if isinstance(x, dict))
        result, seen = [], set()
        for scene in candidates:
            sid = cls._text(scene.get("scene_id") or scene.get("id"))
            key = sid or str(sorted((str(k), str(v)) for k, v in list(scene.items())[:8]))
            if key in seen:
                continue
            seen.add(key)
            result.append(scene)
        return result

    @classmethod
    def _extract_visual_schema(cls, scene):
        blocks = scene.get("render_blocks") or scene.get("blocks") or []
        structured = []
        if isinstance(blocks, list):
            for block in blocks[:cls.MAX_VISUAL_BLOCKS]:
                if not isinstance(block, dict):
                    continue
                kind = cls._text(block.get("type") or block.get("artifact_type") or block.get("representation")).lower()
                if not kind or kind in {"text", "markdown"}:
                    continue
                payload = block.get("payload")
                if not isinstance(payload, dict):
                    artifact = block.get("artifact")
                    payload = artifact.get("payload") if isinstance(artifact, dict) else None
                if not isinstance(payload, dict):
                    candidate = block.get(kind)
                    payload = candidate if isinstance(candidate, dict) else {}
                structured.append({
                    "type": kind,
                    "renderer": cls._text(block.get("renderer")),
                    "viewer": cls._text(block.get("viewer")),
                    "block_id": cls._text(block.get("block_id")),
                    "payload": cls._compact(payload),
                })
        return {
            "scene_id": cls._text(scene.get("scene_id") or scene.get("id")),
            "topic": cls._text(scene.get("topic") or scene.get("user_request") or scene.get("current_request")),
            "user_request": cls._text(scene.get("user_request") or scene.get("current_request")),
            "answer": cls._text(scene.get("april_answer") or scene.get("answer") or scene.get("content")),
            "summary": cls._text(scene.get("summary")),
            "render_block_types": [cls._text(x).lower() for x in (scene.get("render_block_types") or []) if cls._text(x)],
            "presentation_types": [cls._text(x).lower() for x in (scene.get("presentation_types") or []) if cls._text(x)],
            "render_blocks": structured,
            "semantic_state": cls._compact(scene.get("semantic_state") or {}),
        }

    def analyze(self, current_request, *, dialogue_memory=None, visual_memory=None,
                interpretation=None, dynamic_memory=None):
        current_request = self._text(current_request)
        dialogue_memory = dialogue_memory if isinstance(dialogue_memory, dict) else {}
        visual_memory = visual_memory if isinstance(visual_memory, dict) else {}
        interpretation = interpretation if isinstance(interpretation, dict) else {}
        dynamic_memory = dynamic_memory if isinstance(dynamic_memory, dict) else {}

        dialogue_vector = interpretation.get("dialogue_vector") if isinstance(interpretation.get("dialogue_vector"), dict) else {}
        dialogue_contract = interpretation.get("dialogue_contract") if isinstance(interpretation.get("dialogue_contract"), dict) else {}
        relation = self._text(dialogue_vector.get("relation") or dialogue_contract.get("relation")).upper()
        continuation = bool(dialogue_vector.get("continuation") or dialogue_contract.get("continuation") or relation in {"CONTINUE_TOPIC", "CONTINUATION"})
        reference = bool(dialogue_vector.get("reference_to_previous") or dialogue_contract.get("reference_to_previous") or relation == "ARTIFACT_REFERENCE")

        candidates = self._visual_candidates(visual_memory)
        schemas = [self._extract_visual_schema(scene) for scene in candidates]
        active_schema = schemas[0] if schemas else {}
        current_rep = self._text(interpretation.get("production_representation") or interpretation.get("requested_representation") or interpretation.get("scene_type")).lower()
        prior_types = set(active_schema.get("render_block_types") or [])

        compare = [active_schema[k] for k in ("topic", "user_request", "answer") if active_schema.get(k)]
        similarity = QUANTUM_EMBEDDING_ENGINE.similarities(current_request, compare) if compare else {}
        relevance = max((float(similarity.get(value, 0.0)) for value in compare), default=0.0)
        related_visual = bool(active_schema and (continuation or reference or current_rep in prior_types or relevance >= 0.35))
        selected = active_schema if related_visual else {}

        prior_data = []
        for block in (selected.get("render_blocks") or [])[:self.MAX_VISUAL_BLOCKS]:
            if isinstance(block, dict) and isinstance(block.get("payload"), dict):
                prior_data.append({
                    "type": block.get("type"),
                    "renderer": block.get("renderer"),
                    "block_id": block.get("block_id"),
                    "payload": block.get("payload"),
                })

        return {
            "engine": self.VERSION,
            "version": self.VERSION,
            "decision_owner": DECISION_OWNER,
            "evidence_only": True,
            "lexical_triggers": False,
            "score_routing": False,
            "parallel_memory_channels": True,
            "dialogue_memory": {
                "history_present": bool(self._dialogue_text(dialogue_memory.get("history"))),
                "recent_turns": self._dialogue_text(dialogue_memory.get("history")),
                "active_topic": self._text(dialogue_contract.get("active_topic") or interpretation.get("active_topic")),
                "active_goal": self._text(dialogue_contract.get("active_goal") or interpretation.get("active_goal")),
                "relation": relation,
                "continuation": continuation,
                "reference_to_previous": reference,
            },
            "visual_memory": {
                "available": bool(active_schema),
                "related": related_visual,
                "relevance": round(relevance, 6),
                "selected_scene_id": selected.get("scene_id") if selected else "",
                "schema": selected,
                "prior_render_types": sorted(prior_types),
                "prior_structured_blocks": prior_data,
            },
            "memory_reconstruction": {
                "current_request": current_request,
                "dialogue_meaning": self._text(dialogue_contract.get("resolved_request") or dialogue_contract.get("current_request") or current_request),
                "visual_reference": "previous_visual_response" if related_visual else "none",
                "semantic_link": "continuation" if continuation else "reference" if reference else "independent",
                "context_available": bool(dialogue_memory.get("history") or active_schema or dynamic_memory.get("matches")),
                "relevant_dynamic_memory_count": len(dynamic_memory.get("matches") or []),
            },
            "generation_intent": {
                "requested_representation": current_rep or None,
                "create_new_visual_artifact": bool(related_visual and current_rep in STRUCTURED_REPRESENTATIONS),
                "preserve_meaning_from_previous_visual": bool(related_visual),
            },
        }


QUANTUM_MEMORY_UNDERSTANDING_ENGINE = QuantumMemoryUnderstandingEngine()


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
        "profile_version": "quantum_matrix_v2",
    }


def build_scene_construction_profile(semantic_profile):
    return {
        "requires_scene_builder": False,
        "scene_type": "dialogue",
        "dialogue_mode": "semantic_unified",
        "context_source": "quantum_matrix",
        "decision_owner": DECISION_OWNER,
        "profile_version": "quantum_matrix_v2",
    }


def build_scene_artifact_contract(semantic_profile, scene_profile):
    return {
        "contract": "scene_artifact",
        "transport": TRANSPORT_NAME,
        "semantic_profile": semantic_profile or {},
        "scene_profile": scene_profile or {},
        "representation": "processor_decides",
        "profile_version": "quantum_matrix_v2",
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
        "profile_version": "quantum_matrix_v2",
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
        "profile_version": "quantum_matrix_v2",
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
        "profile_version": "quantum_matrix_v2",
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
        "profile_version": "quantum_matrix_v2",
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
        "profile_version": "quantum_matrix_v2",
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
        "profile_version": "quantum_matrix_v2",
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
        "profile_version": "quantum_matrix_v2",
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
        "profile_version": "quantum_matrix_v2",
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
        "profile_version": "quantum_matrix_v2",
    }


def build_processor_execution_context(runtime_state):
    fused = fuse_semantic_inputs(runtime_state or {})
    return {
        "transport": TRANSPORT_NAME,
        "semantic_context": fused,
        "executor_context": fused,
        "processor_context": fused,
        "decision_owner": DECISION_OWNER,
        "profile_version": "quantum_matrix_v2",
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


# ---------------------------------------------------------------------------
# Deep-model API compatibility
# ---------------------------------------------------------------------------

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


def _stanza_lang_ready(lang: str) -> bool:
    return False


def _stanza_resources_ready() -> bool:
    return False


def _provision_stanza_resources() -> None:
    return None
