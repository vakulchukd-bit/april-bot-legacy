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
import math
import threading
import time
import json
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


SEMANTIC_TURN_PROTOTYPES = {
    "identity": "пользователь спрашивает кто ты как тебя зовут представься назови себя; the user asks who you are or what your name is",
    "greeting": "пользователь приветствует ассистента начинает непринужденный разговор; the user is greeting the assistant",
    "question": "пользователь задаёт обычный содержательный вопрос просит объяснение ответ или расчёт что такое почему как работает сколько равен вычисли посчитай значение; the user asks for an answer or explanation",
    "request": "пользователь просит выполнить задачу сделать действие создать результат; the user asks the assistant to perform a task",
    "continuation": "пользователь хочет продолжить предыдущую тему развить предыдущий ответ; the user wants to continue the preceding task",
    "reformulation": "пользователь просит переделать переформулировать переработать предыдущий результат; the user asks to rework previous content",
    "correction": "пользователь исправляет изменяет уточняет предыдущую инструкцию; the user corrects or modifies a previous instruction",
    "reference": "пользователь ссылается на ранее обсуждённое или созданное; the user refers back to previous material",
    "memory_query": "пользователь просит вспомнить предыдущий разговор, восстановить прошлую тему, назвать ранее обсуждавшийся вопрос, вернуться к прошлому сообщению или теме; the user explicitly asks to recall prior conversation",
    "affirmation": "пользователь подтверждает согласие принимает предыдущий результат; the user confirms the preceding result",
    "rejection": "пользователь отклоняет предыдущий результат или предлагает другой вариант; the user rejects the preceding result",
    "new_topic": "пользователь начинает новую тему не связанную с предыдущим обсуждением; the user starts a new topic",
    "statement": "пользователь сообщает утверждение факт или мысль; the user makes a statement",
    "independent": "самостоятельный запрос не зависящий от предыдущих сообщений; the request is self contained and independent",
}

REPRESENTATION_HYPOTHESES = {
    "text": "обычный текстовый ответ объяснение рассказ описание; the user wants a normal textual answer",
    "table": "таблица таблицу структурированные строки колонки сравнение параметров; information represented as a table",
    "graph": "график графика диаграмма данных визуализация числовых значений; information represented as a graph or chart",
    "diagram": "схема диаграмма связей блоков структура процесса; a schematic or diagram with connected elements",
    "formula": "формула уравнение математическое выражение математическая запись; a mathematical formula or notation",
    "image": "изображение картинка рисунок иллюстрация создать изображение; an image or generated picture",
    "gallery": "несколько изображений подборка галерея сравнение изображений; multiple images or a gallery",
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
# Quantum scene-state engine
# ---------------------------------------------------------------------------

SCENE_REQUEST_PROTOTYPES = {
    "proposal": "предложить предложи дать дай вариант пример рекомендацию формулу идею решение совет",
    "explanation": "объяснить рассказать пояснить разъяснить что такое почему как работает",
    "execution": "сделать создать построить вычислить рассчитать решить выполнить показать результат",
    "modification": "изменить исправить переделать заменить добавить убрать переработать",
    "comparison": "сравнить сопоставить отличие разница сравнение против",
    "recall": "вспомнить восстановить прошлый вопрос о чем говорили что обсуждали ранее",
    "continuation": "продолжить дальше следующий шаг развить текущую задачу",
}

SCENE_OPERATION_PROTOTYPES = {
    "square_root": "квадратный корень корень sqrt извлечение корня",
    "calculation": "вычисление расчет посчитать значение арифметика",
    "graph_build": "построение графика график функции координатная плоскость построить",
    "formula_definition": "формула уравнение математическое выражение запись",
    "table_build": "таблица строки колонки структурированные данные",
    "comparison": "сравнение сопоставление различия параметры",
    "explanation": "объяснение описание смысл причина принцип",
    "code_implementation": "программный код функция реализация алгоритм",
    "image_generation": "изображение картинка рисунок иллюстрация генерация",
    "link_retrieval": "ссылка сайт источник веб ресурс",
    "diagram_build": "схема диаграмма блоки связи структура",
}

SCENE_OPERATION_OUTPUT = {
    "graph_build": "graph",
    "table_build": "table",
    "diagram_build": "diagram",
    "image_generation": "image",
    "code_implementation": "code",
    "link_retrieval": "link",
}

# Semantic compatibility matrices. These are learned-logic priors over concepts,
# not phrase triggers: operation/role/representation relations are measured by
# the same interpretation engine and resolved into one production representation.
OPERATION_REPRESENTATION_MATRIX = {
    "square_root": {"formula": 1.00, "text": 0.72, "table": 0.18, "graph": 0.05},
    "calculation": {"text": 0.90, "formula": 0.72, "table": 0.30, "graph": 0.18},
    "graph_build": {"graph": 1.00, "formula": 0.82, "text": 0.48, "table": 0.18},
    "formula_definition": {"formula": 1.00, "text": 0.70, "graph": 0.16},
    "table_build": {"table": 1.00, "text": 0.60, "graph": 0.18},
    "comparison": {"text": 0.86, "table": 0.78, "graph": 0.54, "formula": 0.28},
    "explanation": {"text": 1.00, "formula": 0.30, "table": 0.22, "diagram": 0.18},
    "code_implementation": {"code": 1.00, "text": 0.45, "diagram": 0.15},
    "image_generation": {"image": 1.00, "gallery": 0.72, "text": 0.25},
    "link_retrieval": {"link": 1.00, "text": 0.45},
    "diagram_build": {"diagram": 1.00, "graph": 0.52, "text": 0.28},
}

ROLE_OPERATION_REPRESENTATION_MATRIX = {
    ("proposal", "graph_build"): {"formula": 1.00, "graph": 0.34, "text": 0.78},
    ("proposal", "square_root"): {"formula": 1.00, "text": 0.76},
    ("proposal", "table_build"): {"table": 1.00, "text": 0.72},
    ("explanation", "graph_build"): {"formula": 0.92, "text": 0.88, "graph": 0.20},
    ("explanation", "square_root"): {"formula": 0.92, "text": 0.95},
    ("question", "square_root"): {"text": 1.00, "formula": 0.78},
    ("execution", "graph_build"): {"graph": 1.00, "formula": 0.40, "text": 0.30},
    ("execution", "table_build"): {"table": 1.00, "text": 0.30},
    ("execution", "diagram_build"): {"diagram": 1.00, "text": 0.30},
    ("execution", "image_generation"): {"image": 1.00, "gallery": 0.60},
    ("execution", "code_implementation"): {"code": 1.00, "text": 0.25},
    ("execution", "link_retrieval"): {"link": 1.00, "text": 0.25},
    ("modification", "graph_build"): {"graph": 0.92, "text": 0.42},
    ("modification", "square_root"): {"text": 1.00, "formula": 0.38},
}

ROLE_REPRESENTATION_MATRIX = {
    "question": {"text": 1.00, "formula": 0.72, "table": 0.24, "graph": 0.18},
    "proposal": {"text": 0.82, "formula": 0.82, "table": 0.45, "graph": 0.42},
    "explanation": {"text": 1.00, "formula": 0.34, "table": 0.28, "diagram": 0.22},
    "execution": {"text": 0.70, "graph": 0.80, "table": 0.80, "formula": 0.50, "image": 0.80, "gallery": 0.70, "diagram": 0.80, "code": 0.80, "link": 0.80},
    "modification": {"text": 0.72, "formula": 0.60, "graph": 0.78, "table": 0.78, "image": 0.72, "gallery": 0.70, "diagram": 0.76, "code": 0.76, "link": 0.72},
    "comparison": {"text": 0.86, "table": 0.78, "graph": 0.54, "formula": 0.28},
    "recall": {"text": 1.00, "table": 0.20, "graph": 0.15, "formula": 0.15},
    "continuation": {"text": 0.78, "formula": 0.45, "table": 0.50, "graph": 0.55, "diagram": 0.50, "image": 0.50, "code": 0.50, "link": 0.45},
    "reformulation": {"text": 0.92, "formula": 0.45, "table": 0.52, "graph": 0.52},
    "correction": {"text": 0.92, "formula": 0.48, "table": 0.52, "graph": 0.50},
}

SCENE_REPRESENTATION_PROTOTYPES = {
    "text": "текстовый ответ объяснение рассказ описание",
    "formula": "формула уравнение математическое выражение",
    "graph": "график графическое представление функция координаты",
    "table": "таблица строки колонки структурированные данные",
    "diagram": "схема диаграмма блоки связи структура",
    "image": "изображение картинка рисунок фотография",
    "gallery": "галерея несколько изображений подборка",
    "code": "код программа исходный код функция",
    "link": "ссылка сайт веб ресурс источник адрес",
}

# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

class QuantumInterpretationEngine:
    """One engine: linguistic evidence + semantic matrix + context fusion."""

    # Runtime states are explicit so readiness never means "the object exists".
    # MATRIX_READY means the local quantum matrix is compiled. SEMANTIC_READY
    # means the sentence encoder has actually been loaded and can be used.
    RUNTIME_INITIALIZING = "INITIALIZING"
    RUNTIME_MATRIX_READY = "MATRIX_READY"
    RUNTIME_SEMANTIC_READY = "SEMANTIC_READY"
    RUNTIME_FAILED = "FAILED"

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._runtime_condition = threading.Condition(self._lock)
        self._runtime_thread: threading.Thread | None = None
        self._runtime_error: str | None = None
        self._runtime_started_at: float | None = None
        self._runtime_finished_at: float | None = None
        self._cache: dict[tuple, dict[str, Any]] = {}
        self._cache_limit = 256
        self._vectorizer = None
        self._prototype_matrix = None
        self._prototype_index: dict[str, list[int]] = {}
        self._semantic_encoder = None
        self._semantic_prototype_embeddings = None
        self._semantic_prototype_labels: list[tuple[str, str]] = []
        self._context_embedding_cache: dict[str, Any] = {}
        self._nli = None
        self._runtime_ready = False
        self._heavy_ready = False
        self._matrix_ready = False
        self._compile_matrix()
        self._runtime_state = (
            self.RUNTIME_MATRIX_READY if self._matrix_ready
            else self.RUNTIME_FAILED
        )

    def runtime_status(self) -> dict[str, Any]:
        """Return the real state of this one interpretation engine.

        No status is inferred from object construction.  SEMANTIC_READY is set
        only after SentenceTransformer has successfully loaded.
        """
        with self._lock:
            return {
                "state": self._runtime_state,
                "runtime_ready": bool(self._runtime_ready),
                "matrix_ready": bool(self._matrix_ready),
                "semantic_ready": bool(self._heavy_ready and self._semantic_encoder is not None),
                "model": SEMANTIC_MODEL_NAME,
                "started_at": self._runtime_started_at,
                "finished_at": self._runtime_finished_at,
                "error": self._runtime_error,
                "engine": "quantum_interpretation_engine",
                "single_route": True,
                "decision_owner": DECISION_OWNER,
            }

    def wait_for_semantic_runtime(self, timeout: float | None = None) -> bool:
        """Wait for the existing semantic runtime to finish initialization."""
        with self._runtime_condition:
            if self._heavy_ready and self._semantic_encoder is not None:
                return True
            thread = self._runtime_thread
            if thread is None:
                return False
            self._runtime_condition.wait_for(
                lambda: self._heavy_ready
                or self._runtime_state == self.RUNTIME_FAILED,
                timeout=timeout,
            )
            return bool(self._heavy_ready and self._semantic_encoder is not None)

    def start_semantic_runtime(self, *, background: bool = True) -> dict[str, Any]:
        """Start the existing sentence-semantic runtime exactly once.

        The runtime is part of QuantumInterpretationEngine itself; this method
        does not introduce a second interpreter or a parallel route.
        """
        with self._runtime_condition:
            if self._heavy_ready and self._semantic_encoder is not None:
                self._runtime_state = self.RUNTIME_SEMANTIC_READY
                self._runtime_ready = True
                return self.runtime_status()

            if SentenceTransformer is None:
                # The local matrix is already a complete installed measurement
                # engine. Keep its readiness explicit rather than pretending a
                # missing optional dependency loaded successfully.
                self._runtime_state = (
                    self.RUNTIME_MATRIX_READY if self._matrix_ready
                    else self.RUNTIME_FAILED
                )
                self._runtime_ready = bool(self._matrix_ready)
                self._runtime_error = (
                    "sentence_transformers is unavailable; "
                    "semantic encoder was not started"
                )
                self._runtime_condition.notify_all()
                return self.runtime_status()

            if self._runtime_thread is not None and self._runtime_thread.is_alive():
                if not background:
                    # Never hold the condition while joining.
                    thread = self._runtime_thread
                else:
                    return self.runtime_status()

            else:
                self._runtime_state = self.RUNTIME_INITIALIZING
                self._runtime_ready = False
                self._runtime_error = None
                self._runtime_started_at = time.perf_counter()
                thread = threading.Thread(
                    target=self._load_semantic_runtime,
                    name="april-quantum-semantic-runtime",
                    daemon=True,
                )
                self._runtime_thread = thread
                thread.start()
                if background:
                    return self.runtime_status()

        # Synchronous callers wait outside the lock.
        self.wait_for_semantic_runtime(timeout=None)
        return self.runtime_status()

    def _load_semantic_runtime(self) -> None:
        encoder = None
        error = None
        try:
            # Model construction is intentionally outside the request path.
            encoder = SentenceTransformer(SEMANTIC_MODEL_NAME)
            # Compile the same canonical hypothesis matrix once. The hot path
            # encodes only the current request after this point.
            if encoder is not None and self._prototype_docs:
                self._semantic_prototype_embeddings = encoder.encode(
                    self._prototype_docs,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                )
                self._semantic_prototype_labels = list(self._prototype_keys)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

        with self._runtime_condition:
            self._semantic_encoder = encoder
            self._heavy_ready = encoder is not None
            self._runtime_finished_at = time.perf_counter()
            if self._heavy_ready:
                self._runtime_state = self.RUNTIME_SEMANTIC_READY
                self._runtime_ready = True
                self._runtime_error = None
            else:
                self._runtime_state = (
                    self.RUNTIME_MATRIX_READY if self._matrix_ready
                    else self.RUNTIME_FAILED
                )
                self._runtime_ready = bool(self._matrix_ready)
                self._runtime_error = error or "semantic encoder failed to initialize"
            self._runtime_condition.notify_all()

    # ----------------------------- primitives -----------------------------

    @staticmethod
    def normalize(text: Any) -> str:
        return re.sub(r"\s+", " ", str(text or "").strip())

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+", text.lower())


    def _compile_matrix(self) -> None:
        """Compile one canonical hypothesis matrix.

        All semantic families live in the same matrix and are measured once per
        request. Scene role, operation and representation are evidence dimensions
        of the same engine, not a second interpreter.
        """
        docs: list[str] = []
        families = (
            ("dialogue", SEMANTIC_TURN_PROTOTYPES),
            ("representation", REPRESENTATION_HYPOTHESES),
            ("domain", DOMAIN_HYPOTHESES),
            ("capability", CAPABILITY_HYPOTHESES),
            ("request_role", SCENE_REQUEST_PROTOTYPES),
            ("operation", SCENE_OPERATION_PROTOTYPES),
            ("scene_representation", SCENE_REPRESENTATION_PROTOTYPES),
        )
        self._matrix_families = {
            family: dict(vocab) for family, vocab in families
        }
        self._prototype_keys: list[tuple[str, str]] = []
        self._prototype_docs: list[str] = []
        self._family_indices: dict[str, list[int]] = {}
        for family, vocab in families:
            indices: list[int] = []
            for label, description in vocab.items():
                idx = len(docs)
                self._prototype_keys.append((family, label))
                self._prototype_docs.append(description)
                self._family_indices.setdefault(family, []).append(idx)
                indices.append(idx)
                docs.append(description)
        if TfidfVectorizer is not None and docs:
            self._vectorizer = TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(3, 5),
                lowercase=True,
                sublinear_tf=True,
                min_df=1,
            )
            self._prototype_matrix = self._vectorizer.fit_transform(docs)
        self._matrix_ready = bool(
            self._vectorizer is not None and self._prototype_matrix is not None
        )

    def _ensure_cognitive_runtime(self) -> None:
        """Ensure the one semantic runtime is initialized before semantic use.

        Startup may prewarm this runtime in the background. If a request arrives
        before it finishes, the request waits for the same runtime instead of
        creating a second encoder or silently inventing another route.
        """
        with self._lock:
            ready = self._heavy_ready and self._semantic_encoder is not None
            thread = self._runtime_thread

        if ready:
            return

        if thread is None:
            # Compatibility callers can still invoke measurement directly.
            # Start the same existing runtime synchronously; no parallel engine.
            self.start_semantic_runtime(background=False)
            return

        self.wait_for_semantic_runtime(timeout=None)

    def _encode(self, texts: Sequence[str]):
        values = [self.normalize(x) for x in texts if self.normalize(x)]
        if not values:
            return None
        self._ensure_cognitive_runtime()
        encoder = self._semantic_encoder
        if encoder is None:
            return None
        try:
            return encoder.encode(values, normalize_embeddings=True, convert_to_numpy=True)
        except Exception:
            return None


    def _semantic_scores(self, text: str) -> dict[str, dict[str, float]] | None:
        """Measure the single semantic matrix without re-encoding prototypes.

        Prototype embeddings are compiled once during runtime initialization.
        Each request encodes only its own text, then compares against the cached
        matrix. This preserves the same semantic engine while removing the
        repeated N*prototype model work from the request hot path.
        """
        families = self._matrix_families
        encoder = self._semantic_encoder
        prototypes = self._semantic_prototype_embeddings
        labels = self._semantic_prototype_labels or list(self._prototype_keys)
        if not families or encoder is None or prototypes is None:
            return None
        value = self.normalize(text)
        if not value:
            return {
                family: {label: 0.0 for label in vocab}
                for family, vocab in families.items()
            }
        try:
            q = encoder.encode(
                [value],
                normalize_embeddings=True,
                convert_to_numpy=True,
            )[0]
            raw = (prototypes @ q).tolist()
        except Exception:
            return None

        out = {
            family: {label: 0.0 for label in vocab}
            for family, vocab in families.items()
        }
        temperature = 0.18
        cursor = 0
        for family, vocab in families.items():
            family_labels = list(vocab)
            values = [float(raw[cursor + i]) for i in range(len(family_labels))]
            cursor += len(family_labels)
            if not values:
                continue
            peak = max(values)
            exps = [math.exp((value - peak) / temperature) for value in values]
            total = sum(exps) or 1.0
            for label, value_exp in zip(family_labels, exps):
                out[family][label] = float(value_exp / total)
        return out


    def _tfidf_scores(self, text: str) -> dict[str, dict[str, float]]:
        """Return one normalized semantic matrix for all evidence families.

        The local TF-IDF matrix is the deterministic measurement engine when a
        sentence encoder is unavailable. Each hypothesis family still competes
        internally, so a single weak representation cannot activate many
        unrelated renderers at once.
        """
        families = self._matrix_families
        if not text:
            return {
                name: {key: 0.0 for key in values}
                for name, values in families.items()
            }

        semantic = self._semantic_scores(text)
        if semantic is not None:
            return semantic

        if (
            self._vectorizer is None
            or self._prototype_matrix is None
            or cosine_similarity is None
        ):
            return {
                name: {key: 0.0 for key in values}
                for name, values in families.items()
            }

        q = self._vectorizer.transform([text])
        sim = cosine_similarity(q, self._prototype_matrix)[0]
        out: dict[str, dict[str, float]] = {}
        temperature = 0.08
        for family, values in families.items():
            indices = self._family_indices.get(family, [])
            raw = [float(sim[idx]) for idx in indices]
            if not raw:
                out[family] = {key: 0.0 for key in values}
                continue
            peak = max(raw)
            exps = [math.exp((value - peak) / temperature) for value in raw]
            total = sum(exps) or 1.0
            out[family] = {
                label: float(exp_value / total)
                for label, exp_value in zip(values, exps)
            }
        return out

    def _context_scores(
        self,
        text: str,
        previous_assistant: str,
        previous_user: str,
        active_topic: str,
        active_goal: str,
    ) -> dict[str, float]:
        values = {
            "previous_assistant": previous_assistant,
            "previous_user": previous_user,
            "active_topic": active_topic,
            "active_goal": active_goal,
        }
        if not self.normalize(text):
            return {key: 0.0 for key in values}

        encoder = self._semantic_encoder
        if encoder is not None:
            try:
                q = encoder.encode(
                    [self.normalize(text)],
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                )[0]
                result: dict[str, float] = {}
                for key, value in values.items():
                    normalized = self.normalize(value)
                    if not normalized:
                        result[key] = 0.0
                        continue
                    cached_vec = self._context_embedding_cache.get(normalized)
                    if cached_vec is None:
                        cached_vec = encoder.encode(
                            [normalized],
                            normalize_embeddings=True,
                            convert_to_numpy=True,
                        )[0]
                        self._context_embedding_cache[normalized] = cached_vec
                        if len(self._context_embedding_cache) > 128:
                            self._context_embedding_cache.pop(next(iter(self._context_embedding_cache)))
                    score = float(cached_vec @ q)
                    result[key] = max(0.0, min(1.0, score * 0.5 + 0.5))
                return result
            except Exception:
                pass

        return {
            key: self.similarity(text, value)["score"] if self.normalize(value) else 0.0
            for key, value in values.items()
        }


    def _linguistic(self, text: str) -> dict[str, Any]:
        tokens = self._tokens(text)
        return {
            "language": None,
            "tokens": tokens,
            "lemmas": tokens,
            "pos": [],
            "dependencies": [],
            "entities": [],
            "sentences": [text] if text else [],
            "source": "quantum_matrix_lightweight",
            "engine": "quantum_interpretation_engine",
        }


    def _scores(self, text: str, family: str) -> dict[str, float]:
        """Compatibility view into the canonical matrix measurement.

        No independent vectorizer or interpreter is created here.
        """
        measured = self._tfidf_scores(self.normalize(text))
        return dict(measured.get(family, {}))

    @staticmethod
    def _anaphora_features(text: str) -> dict[str, Any]:
        """Measure grammatical reference pressure, not routing triggers."""
        tokens = re.findall(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ]+", str(text or "").lower())
        # Pronoun classes are linguistic structure: they indicate that the
        # current utterance may depend on an antecedent already present in the
        # previous scene. They never select a renderer or provider.
        pronoun_forms = {
            "он","она","они","его","ее","её","их","ему","ей","это","этот","эта","эти",
            "этого","этой","того","та","те","них","ней","ним","ними","тот",
            "he","she","they","it","his","her","their","this","that","these","those",
        }
        hits=[t for t in tokens if t in pronoun_forms]
        return {
            "count": len(hits),
            "density": min(1.0, len(hits)/max(1.0, len(tokens))),
            "forms": hits[:8],
        }

    @staticmethod
    def _numbers(text: str) -> list[str]:
        return re.findall(r"(?<!\w)[+-]?\d+(?:[.,]\d+)?(?!\w)", text)

    @staticmethod
    def _entities(text: str) -> list[str]:
        """Extract structural named candidates without using them as triggers."""
        value = str(text or "")
        tokens = re.findall(r"\b[А-ЯЁ][а-яё]{2,}\b", value)
        # Do not count a sentence-initial capitalized token as an entity by
        # itself. Names/objects appearing after the first position remain evidence.
        out = []
        for token in tokens:
            if not out and value.lstrip().startswith(token):
                continue
            if token not in out:
                out.append(token)
        return out[:12]

    @staticmethod
    def _representation_mentions(text: str) -> list[tuple[str, int]]:
        tokens = re.findall(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ]+", text.lower())
        lexemes = {
            "formula": {"формула", "формулу", "формулы", "уравнение", "выражение"},
            "graph": {"график", "графика", "графики", "графический"},
            "table": {"таблица", "таблицу", "таблицы"},
            "diagram": {"схема", "схему", "диаграмма", "диаграмму"},
            "image": {"изображение", "изображение", "картинка", "картинку", "рисунок", "рисунок", "фото", "фотографию"},
            "gallery": {"галерея", "галерею", "галереи", "подборка", "подборку"},
            "code": {"код", "программа", "скрипт"},
            "link": {"ссылка", "ссылку", "ссылки", "сайт", "источник"},
        }
        out = []
        for index, token in enumerate(tokens):
            for representation, words in lexemes.items():
                if token in words:
                    out.append((representation, index))
        return out



    def build_scene_state(
        self,
        text: str,
        *,
        answer: str = "",
        previous: dict[str, Any] | None = None,
        profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized = self.normalize(text)
        answer = self.normalize(answer)
        combined = " ".join(x for x in (normalized, answer) if x)
        previous = previous if isinstance(previous, dict) else {}
        profile = profile or self.measure(normalized)

        role_scores = profile.get("request_role_scores", {})
        operation_scores = profile.get("operation_scores", {})

        def best(values: dict[str, float], default: str = ""):
            ordered = sorted(values.items(), key=lambda x: x[1], reverse=True)
            if not ordered:
                return default, 0.0
            return ordered[0][0], float(ordered[0][1])

        role, role_conf = best(role_scores, "question")
        operation, operation_conf = best(operation_scores, "")
        requested_representation = str(
            profile.get("resolved_representation") or "text"
        )
        explicit_representation = bool(
            profile.get("resolved_representation_locked")
            and requested_representation != "text"
        )

        previous_operation = str(previous.get("operation") or "")
        previous_representation = str(
            previous.get("requested_representation")
            or previous.get("representation")
            or ""
        )
        previous_role = str(previous.get("request_role") or "")
        previous_numbers = list(previous.get("numbers") or [])
        numbers = self._numbers(normalized)

        short_turn = bool(previous and len(normalized.split()) <= max(
            6, int(len(str(previous.get("text") or "").split()) * 0.55)
        ))
        inherited_operation = False
        inherited_representation = False

        if previous and short_turn:
            if operation_conf < 0.34 and previous_operation:
                operation = previous_operation
                operation_conf = max(operation_conf, 0.78)
                inherited_operation = True
            if requested_representation == "text" and previous_representation:
                requested_representation = previous_representation
                explicit_representation = previous_representation != "text"
                inherited_representation = True

        operation_output = SCENE_OPERATION_OUTPUT.get(operation)
        if (
            operation_output
            and role in {"execution", "modification"}
            and operation_conf >= 0.40
        ):
            requested_representation = operation_output
            explicit_representation = True

        parameter_change = bool(
            previous and previous_numbers and numbers and previous_numbers != numbers
        )

        # A short parameter update normally asks for the updated result of the
        # active operation. It does not independently request a new renderer.
        if parameter_change and role in {"modification", "correction", "question", "continuation"}:
            if not profile.get("explicit_representations"):
                requested_representation = "text"
                explicit_representation = False

        phase = role
        if inherited_operation or inherited_representation:
            phase = "continuation" if role not in {"modification", "comparison"} else role

        return {
            "request_role": role,
            "request_role_confidence": round(role_conf, 6),
            "task_phase": phase,
            "operation": operation,
            "operation_confidence": round(operation_conf, 6),
            "requested_representation": requested_representation or "text",
            "representation_confidence": round(
                float(profile.get("resolved_representation_confidence", 0.0)), 6
            ),
            "explicit_representation": explicit_representation,
            "inherited_operation": inherited_operation,
            "inherited_representation": inherited_representation,
            "previous_operation": previous_operation,
            "previous_representation": previous_representation,
            "previous_request_role": previous_role,
            "numbers": numbers,
            "previous_numbers": previous_numbers,
            "parameter_change": parameter_change,
            "anaphora": self._anaphora_features(normalized),
            "entities": self._entities(normalized),
            "text": normalized,
            "answer": answer,
            "combined": combined,
            "dialogue_profile": dict(profile.get("dialogue_scores", {})),
            "representation_profile": dict(profile.get("representation_scores", {})),
            "representation_measurements": dict(profile.get("representation_measurements", {})),
            "domain_profile": dict(profile.get("domain_scores", {})),
            "capability_profile": dict(profile.get("capability_scores", {})),
            "scene_matrix": dict(profile.get("scene_matrix", {})),
            "source": "quantum_interpretation_engine",
        }

    def _feature_vector(
        self,
        dialogue: dict[str, float],
        representation: dict[str, float],
        domain: dict[str, float],
        capability: dict[str, float],
        context: dict[str, float],
        modalities: dict[str, Any],
    ) -> list[float]:
        dialogue_v = max(
            [dialogue.get(x, 0.0) for x in ("continuation", "reference", "question", "request")]
            or [0.0]
        )
        representation_v = max(representation.values(), default=0.0)
        domain_v = max(domain.values(), default=0.0)
        capability_v = max(capability.values(), default=0.0)
        continuity_v = max(context.values(), default=0.0)
        context_v = max(
            context.get("active_topic", 0.0),
            context.get("active_goal", 0.0),
            0.0,
        )
        modality_count = sum(
            v not in (None, "", {}, []) for v in (modalities or {}).values()
        )
        modality_v = min(1.0, modality_count / 3.0)
        return [
            float(dialogue_v), float(representation_v), float(domain_v),
            float(capability_v), float(continuity_v), float(context_v),
            float(modality_v),
        ]

    def scene_matrix(
        self,
        *,
        dialogue: dict[str, float],
        representation: dict[str, float],
        domain: dict[str, float],
        capability: dict[str, float],
        context: dict[str, float],
        modalities: dict[str, Any] | None = None,
        explicit_representations: Sequence[str] = (),
    ) -> dict[str, Any]:
        vector = self._feature_vector(
            dialogue, representation, domain, capability, context, modalities or {}
        )

        raw = []
        for row in _SCENE_WEIGHTS:
            raw.append(sum(a * b for a, b in zip(row, vector)))

        for scene in SCENE_MATRIX_LABELS:
            raw[SCENE_MATRIX_LABELS.index(scene)] += (
                0.34 * float(representation.get(scene, 0.0))
            )
            raw[SCENE_MATRIX_LABELS.index(scene)] += (
                0.10 * float(capability.get(SCENE_MATRIX_CAPABILITY[scene], 0.0))
            )

        for domain_name, bias_map in SCENE_MATRIX_DOMAIN_BIAS.items():
            ds = float(domain.get(domain_name, 0.0))
            for scene, bias in bias_map.items():
                raw[SCENE_MATRIX_LABELS.index(scene)] += ds * bias

        for scene in explicit_representations:
            if scene in SCENE_MATRIX_LABELS:
                raw[SCENE_MATRIX_LABELS.index(scene)] += 0.45

        maximum = max(raw, default=0.0)
        scores = [x / maximum if maximum > 0 else 0.0 for x in raw]
        ranked = sorted(
            zip(SCENE_MATRIX_LABELS, scores),
            key=lambda x: x[1],
            reverse=True,
        )
        best, best_score = ranked[0]
        second = ranked[1][1] if len(ranked) > 1 else 0.0
        return {
            "labels": [x[0] for x in ranked],
            "scores": [round(float(x[1]), 6) for x in ranked],
            "best_scene": best,
            "best_score": round(float(best_score), 6),
            "margin": round(float(best_score - second), 6),
            "feature_order": list(SCENE_MATRIX_FEATURES),
            "feature_vector": [round(x, 6) for x in vector],
            "matrix_shape": [len(_SCENE_WEIGHTS), len(SCENE_MATRIX_FEATURES)],
            "explicit_representations": list(explicit_representations),
            "engine": "quantum_matrix",
            "mode": "vectorized_evidence_fusion",
            "decision_owner": DECISION_OWNER,
            "evidence_only": True,
        }

    # ------------------------------ measurement ---------------------------



    def _resolve_production_representation(
        self,
        representation_scores: dict[str, float],
        *,
        request_role: str,
        operation: str,
        operation_confidence: float,
        operation_margin: float,
        context: dict[str, float],
        previous_representation: str = "",
        parameter_change: bool = False,
    ) -> dict[str, Any]:
        """Resolve one production representation from the single semantic field."""
        candidates = {
            key: float(value)
            for key, value in representation_scores.items()
            if key in SCENE_MATRIX_LABELS
        }
        scored: dict[str, float] = {}
        op_matrix = OPERATION_REPRESENTATION_MATRIX.get(operation, {})
        role_matrix = ROLE_REPRESENTATION_MATRIX.get(request_role, {})
        phase_matrix = ROLE_OPERATION_REPRESENTATION_MATRIX.get(
            (request_role, operation), {}
        )

        if request_role in {"proposal", "explanation", "question"}:
            operation_weight = 0.11
        elif request_role in {"execution", "modification", "continuation"}:
            operation_weight = 0.30
        else:
            operation_weight = 0.18

        for rep, evidence in candidates.items():
            score = 0.46 * evidence
            score += operation_weight * float(op_matrix.get(rep, 0.0)) * min(
                1.0, operation_confidence * 1.20
            )
            score += 0.20 * float(role_matrix.get(rep, 0.0))
            score += 0.28 * float(phase_matrix.get(rep, 0.0))
            score += 0.03 * float(context.get("active_goal", 0.0) or 0.0)
            score += 0.03 * float(context.get("active_topic", 0.0) or 0.0)
            if previous_representation == rep:
                score += 0.08
            scored[rep] = score

        if not scored:
            return {
                "representation": "text",
                "confidence": 0.0,
                "margin": 0.0,
                "scores": {"text": 1.0},
                "evidence": {},
                "locked": False,
            }

        ranked = sorted(scored.items(), key=lambda x: x[1], reverse=True)
        best, best_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        margin = best_score - second_score

        inherited = bool(previous_representation and best == previous_representation)
        lock = bool(
            best != "text"
            and best_score >= 0.34
            and margin >= 0.08
            and (
                operation_confidence >= 0.30
                or request_role in {"proposal", "execution", "modification", "explanation"}
                or inherited
            )
        )

        if request_role in {"question", "explanation"} and best != "formula":
            lock = False
        if request_role == "explanation" and best == "formula":
            lock = bool(
                best_score >= 0.42
                and margin >= 0.10
                and float(op_matrix.get("formula", 0.0)) >= 0.85
            )

        return {
            "representation": best if lock else "text",
            "confidence": round(float(best_score), 6),
            "margin": round(float(margin), 6),
            "scores": {
                k: round(float(v), 6)
                for k, v in sorted(scored.items(), key=lambda x: x[1], reverse=True)
            },
            "evidence": dict(representation_scores),
            "locked": lock,
        }

    def measure(
        self,
        text: str,
        *,
        previous_assistant: str = "",
        previous_user: str = "",
        active_topic: str = "",
        active_goal: str = "",
        modalities: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        text = self.normalize(text)
        key = (
            text,
            self.normalize(previous_assistant),
            self.normalize(previous_user),
            self.normalize(active_topic),
            self.normalize(active_goal),
            tuple(sorted((modalities or {}).keys())),
        )
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                return cached

        families = self._tfidf_scores(text)
        context = self._context_scores(
            text, previous_assistant, previous_user, active_topic, active_goal
        )

        dialogue = families["dialogue"]
        representation_measurements = families["representation"]
        domain = families["domain"]
        capability = families["capability"]
        request_role = families["request_role"]
        operation = families["operation"]

        def ranked(values: dict[str, float]):
            ordered = sorted(values.items(), key=lambda x: x[1], reverse=True)
            best = ordered[0][0] if ordered else ""
            score = float(ordered[0][1]) if ordered else 0.0
            margin = score - (float(ordered[1][1]) if len(ordered) > 1 else 0.0)
            return ordered, best, score, margin

        dialogue_ranked, best_dialogue, dialogue_score, dialogue_margin = ranked(dialogue)
        role_ranked, best_role, role_score, role_margin = ranked(request_role)
        op_ranked, best_operation, operation_score, operation_margin = ranked(operation)
        _, best_representation_measurement, rep_score, rep_margin = ranked(representation_measurements)

        resolved = self._resolve_production_representation(
            representation_measurements,
            request_role=best_role,
            operation=best_operation,
            operation_confidence=operation_score,
            operation_margin=operation_margin,
            context=context,
            previous_representation="",
        )
        production_representation = str(resolved["representation"])

        # Expose one canonical production representation while retaining the
        # complete matrix under diagnostics for analysis. Downstream renderers
        # therefore cannot mistake evidence for multiple production commands.
        canonical_representation_scores = {
            label: (1.0 if label == production_representation else 0.0)
            for label in representation_measurements
        }
        identity_request = (
            best_dialogue == "identity"
            and dialogue_score >= 0.40
            and dialogue_margin >= 0.08
        )
        fast_social = (
            best_dialogue in {"identity", "greeting"}
            and dialogue_score >= 0.45
            and dialogue_margin >= 0.10
            and len(text.split()) <= 24
        )

        # Matrix scene remains an evidence diagnostic; it never grants renderer
        # execution rights.
        scene = self.scene_matrix(
            dialogue=dialogue,
            representation=canonical_representation_scores,
            domain=domain,
            capability=capability,
            context=context,
            modalities=modalities,
            explicit_representations=(
                [production_representation]
                if resolved["locked"] and production_representation != "text"
                else []
            ),
        )

        profile = {
            "dialogue_scores": dict(dialogue),
            "dialogue_best": best_dialogue,
            "dialogue_confidence": float(dialogue_score),
            "dialogue_margin": float(dialogue_margin),
            "representation_scores": canonical_representation_scores,
            "representation_measurements": dict(representation_measurements),
            "resolved_representation": production_representation,
            "resolved_representation_confidence": float(resolved["confidence"]),
            "resolved_representation_margin": float(resolved["margin"]),
            "resolved_representation_locked": bool(resolved["locked"]),
            "domain_scores": dict(domain),
            "capability_scores": dict(capability),
            "context_scores": dict(context),
            "best_representation": production_representation,
            "best_representation_score": float(resolved["confidence"]),
            "representation_margin": float(resolved["margin"]),
            "explicit_representations": (
                [production_representation]
                if resolved["locked"] and production_representation != "text"
                else []
            ),
            "request_role_scores": dict(request_role),
            "request_role_best": best_role,
            "request_role_confidence": float(role_score),
            "request_role_margin": float(role_margin),
            "operation_scores": dict(operation),
            "operation_best": best_operation,
            "operation_confidence": float(operation_score),
            "operation_margin": float(operation_margin),
            "identity_request": bool(identity_request),
            "fast_social": bool(fast_social or identity_request),
            "scene_matrix": scene,
            "source": "quantum_interpretation_engine",
        }

        with self._lock:
            self._cache[key] = profile
            if len(self._cache) > self._cache_limit:
                self._cache.pop(next(iter(self._cache)))
        return profile

    def _history(self, history: Any) -> tuple[str, str, Any]:
        turns = history if isinstance(history, list) else []
        last_assistant = ""
        last_user = ""
        reply_to = None
        for item in reversed(turns):
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").lower()
            if not last_assistant:
                if isinstance(item.get("april"), dict):
                    obj = item["april"]
                    last_assistant = self.normalize(
                        obj.get("answer") or obj.get("content") or obj.get("summary")
                    )
                    reply_to = item.get("turn_id")
                elif role in {"assistant", "april", "bot"}:
                    last_assistant = self.normalize(
                        item.get("answer") or item.get("content") or item.get("summary")
                    )
                    reply_to = item.get("turn_id")
            if not last_user:
                if isinstance(item.get("user"), dict):
                    obj = item["user"]
                    last_user = self.normalize(
                        obj.get("text") or obj.get("content") or obj.get("answer")
                    )
                elif role in {"user", "human"}:
                    last_user = self.normalize(item.get("content") or item.get("text"))
            if last_assistant and last_user:
                break
        return last_assistant, last_user, reply_to

    def fast_semantic_profile(
        self, text: str, previous_assistant: str = "", previous_user: str = "",
        active_topic: str = "", active_goal: str = ""
    ) -> dict[str, Any]:
        return self.measure(
            text,
            previous_assistant=previous_assistant,
            previous_user=previous_user,
            active_topic=active_topic,
            active_goal=active_goal,
        )

    def turn_measurement(
        self, text: str, previous_assistant: str = "",
        previous_user: str = "", active_goal: str = "", active_topic: str = ""
    ) -> dict[str, Any]:
        profile = self.measure(
            text,
            previous_assistant=previous_assistant,
            previous_user=previous_user,
            active_topic=active_topic,
            active_goal=active_goal,
        )
        return {
            "linguistic": self._linguistic(self.normalize(text)),
            "dialogue_nli": {
                "labels": list(profile["dialogue_scores"]),
                "scores": list(profile["dialogue_scores"].values()),
                "source": "quantum_matrix",
            },
            "representation_nli": {
                "labels": [REPRESENTATION_HYPOTHESES[x] for x in profile["representation_scores"]],
                "scores": list(profile["representation_scores"].values()),
                "source": "quantum_matrix",
            },
            "domain_nli": {
                "labels": [DOMAIN_HYPOTHESES[x] for x in profile["domain_scores"]],
                "scores": list(profile["domain_scores"].values()),
                "source": "quantum_matrix",
            },
            "capability_nli": {
                "labels": [CAPABILITY_HYPOTHESES[x] for x in profile["capability_scores"]],
                "scores": list(profile["capability_scores"].values()),
                "source": "quantum_matrix",
            },
            "embeddings": dict(profile["context_scores"]),
            "decision_owner": DECISION_OWNER,
            "evidence_only": True,
            "engine": "quantum_interpretation_turn_engine",
        }

    def classify(self, text: str, hypotheses: Sequence[str]) -> dict[str, Any]:
        profile = self.measure(text)
        labels = list(hypotheses)
        family_map = {
            "dialogue": profile["dialogue_scores"],
            "representation": profile["representation_scores"],
            "domain": profile["domain_scores"],
            "capability": profile["capability_scores"],
        }
        scores: dict[str, float] = {}
        for family in family_map.values():
            scores.update({str(k): float(v) for k, v in family.items()})
        ranked = sorted(
            ((label, scores.get(label, 0.0)) for label in labels),
            key=lambda x: x[1], reverse=True,
        )
        return {
            "labels": [x[0] for x in ranked],
            "scores": [x[1] for x in ranked],
            "source": "quantum_matrix",
        }

    def _vector_similarity_pair(self, text_a: str, text_b: str) -> float:
        a = self.normalize(text_a)
        b = self.normalize(text_b)
        if not a or not b or TfidfVectorizer is None or cosine_similarity is None:
            return 0.0
        try:
            vectorizer = TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 5),
                lowercase=True,
                sublinear_tf=True,
                min_df=1,
            )
            matrix = vectorizer.fit_transform([a, b])
            return float(max(0.0, min(1.0, cosine_similarity(matrix[0:1], matrix[1:2])[0][0])))
        except Exception:
            return 0.0

    def similarity(self, text_a: str, text_b: str) -> dict[str, Any]:
        a = self.normalize(text_a)
        b = self.normalize(text_b)
        if not a or not b:
            return {"score": 0.0, "source": "quantum_matrix", "measured": False, "cached": False}
        vector_score = self._vector_similarity_pair(a, b)
        token_a = set(self._tokens(a))
        token_b = set(self._tokens(b))
        token_score = (
            len(token_a & token_b) / max(1.0, min(len(token_a), len(token_b)))
            if token_a and token_b else 0.0
        )
        # The lexical component is only a stabilizer. Character-space semantics
        # is the primary measurement so short paraphrases do not collapse to 0.
        score = max(0.0, min(1.0, 0.82 * vector_score + 0.18 * token_score))
        return {
            "score": float(score),
            "vector_score": float(vector_score),
            "token_score": float(token_score),
            "source": "quantum_cognitive_semantic_engine",
            "measured": True,
            "cached": False,
        }


    # ------------------------ dynamic scene semantics -----------------------
    def _scene_numbers(self, text: str) -> list[str]:
        return re.findall(r"(?<!\w)[+-]?\d+(?:[.,]\d+)?(?!\w)", self.normalize(text))

    def _scene_entities(self, text: str) -> list[str]:
        # Entity extraction is structural: capitalized names and quoted spans.
        # The first capitalized token is excluded when it is merely sentence
        # capitalization, while named spans elsewhere remain semantic evidence.
        value = self.normalize(text)
        quoted = re.findall(r"[\"«](.+?)[\"»]", value)
        names = re.findall(r"\b[А-ЯЁ][а-яё]{2,}\b", value)
        first_word = (value.split() or [""])[0].strip(".,!?;:()[]{}")
        out = []
        for token in quoted + names:
            token = self.normalize(token)
            if not token:
                continue
            if token == first_word and not quoted:
                continue
            if token not in out:
                out.append(token)
        return out[:12]

    def _scene_content_vector(self, text: str) -> dict[str, Any]:
        normalized = self.normalize(text)
        vectorizer = getattr(self, "_scene_vectorizer", None)
        matrix = getattr(self, "_scene_vector_matrix", None)
        if vectorizer is None:
            vectorizer = TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 5),
                lowercase=True,
                sublinear_tf=True,
                min_df=1,
            ) if TfidfVectorizer is not None else None
            self._scene_vectorizer = vectorizer
            self._scene_vector_matrix = None

        if vectorizer is None or not normalized:
            return {"norm": normalized, "vector": None}

        try:
            # Fit on a minimal stable semantic basis, then transform current
            # state text. This is a true vector-space measurement, not routing.
            basis = [
                "continuation reference previous same topic same operation",
                "new independent request new subject",
                "change parameter value preserve operation",
                "ask explain calculate compare modify previous result",
            ]
            if matrix is None:
                self._scene_vector_matrix = vectorizer.fit_transform(basis)
            q = vectorizer.transform([normalized])
            return {"norm": normalized, "vector": q}
        except Exception:
            return {"norm": normalized, "vector": None}

    def _scene_vector_similarity(self, a: str, b: str) -> float:
        if not a or not b or cosine_similarity is None:
            return 0.0
        try:
            va = self._scene_content_vector(a).get("vector")
            vb = self._scene_content_vector(b).get("vector")
            if va is None or vb is None:
                return 0.0
            # Rebuild over the same fitted vocabulary with both strings.
            vec = TfidfVectorizer(
                analyzer="char_wb", ngram_range=(2, 5),
                lowercase=True, sublinear_tf=True, min_df=1
            )
            mx = vec.fit_transform([a, b])
            return float(max(0.0, min(1.0, cosine_similarity(mx[0], mx[1])[0][0])))
        except Exception:
            return 0.0

    def build_scene_semantic_state(
        self,
        text: str,
        *,
        answer: str = "",
        profile: dict[str, Any] | None = None,
        previous: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        profile = profile or self.measure(text)
        normalized = self.normalize(text)
        answer = self.normalize(answer)
        combined = " ".join(x for x in (normalized, answer) if x)
        numbers = self._scene_numbers(normalized)
        entities = self._scene_entities(normalized)
        semantic_identity = self.build_scene_state(
            normalized,
            answer=answer,
            previous=previous,
            profile=profile,
        )
        semantic_identity.update({
            "version": "QUANTUM-INTERPRETATION-MATRIX-V4",
            "text": normalized,
            "answer": answer,
            "combined": combined,
            "numbers": numbers,
            "entities": entities,
            "dialogue_profile": dict(profile.get("dialogue_scores", {})),
            "representation_profile": dict(profile.get("representation_scores", {})),
            "domain_profile": dict(profile.get("domain_scores", {})),
            "capability_profile": dict(profile.get("capability_scores", {})),
            "scene_matrix": dict(profile.get("scene_matrix", {})),
            "semantic_vector_source": "quantum_hybrid_semantic_engine",
            "turn_features": {
                "length": len(normalized.split()),
                "number_count": len(numbers),
                "entity_count": len(entities),
            },
        })
        return semantic_identity

    def relate_scene_semantics(
        self,
        current: dict[str, Any],
        previous: dict[str, Any] | None,
        *,
        reference_to_previous: bool = False,
        continuation_score: float = 0.0,
    ) -> dict[str, Any]:
        if not isinstance(current,dict) or not isinstance(previous,dict):
            return {"same_scene":False,"continuation":False,"reference_to_previous":False,
                    "confidence":0.0,"relation":"independent","parameter_change":False,
                    "state_transfer":{},"engine":"quantum_interpretation_engine.scene_relation"}

        current_text=self.normalize(current.get("combined") or current.get("text"))
        previous_text=self.normalize(previous.get("combined") or previous.get("text"))
        vector_similarity=self.similarity(current_text,previous_text)["score"] if current_text and previous_text else 0.0

        prev_operation=self.normalize(previous.get("operation"))
        curr_operation=self.normalize(current.get("operation"))
        prev_rep=self.normalize(previous.get("requested_representation") or previous.get("representation"))
        curr_rep=self.normalize(current.get("requested_representation") or current.get("representation"))
        operation_same=bool(prev_operation and curr_operation and prev_operation==curr_operation)
        representation_same=bool(prev_rep and curr_rep and prev_rep==curr_rep)

        prev_numbers=list(previous.get("numbers") or [])
        curr_numbers=list(current.get("numbers") or [])
        parameter_change=bool(prev_numbers and curr_numbers and prev_numbers!=curr_numbers)
        prev_entities={str(x).strip().lower() for x in (previous.get("entities") or []) if str(x).strip()}
        curr_entities={str(x).strip().lower() for x in (current.get("entities") or []) if str(x).strip()}
        entity_overlap=(len(prev_entities & curr_entities)/max(1,len(prev_entities|curr_entities))) if (prev_entities or curr_entities) else 0.0
        anaphora=current.get("anaphora") if isinstance(current.get("anaphora"),dict) else {}
        anaphora_score=float(anaphora.get("density",0.0) or 0.0)

        phase_now=self.normalize(current.get("task_phase"))
        phase_prev=self.normalize(previous.get("task_phase"))
        phase_relation=self.similarity(phase_now,phase_prev)["score"] if phase_now and phase_prev else 0.0

        profile_components=[]
        for key in ("dialogue_profile","representation_profile","domain_profile","capability_profile"):
            a=previous.get(key,{}) if isinstance(previous.get(key),dict) else {}
            b=current.get(key,{}) if isinstance(current.get(key),dict) else {}
            keys=sorted(set(a)|set(b))
            if keys:
                va=[float(a.get(k,0.0) or 0.0) for k in keys]; vb=[float(b.get(k,0.0) or 0.0) for k in keys]
                na=math.sqrt(sum(x*x for x in va)); nb=math.sqrt(sum(y*y for y in vb))
                if na and nb: profile_components.append(max(0.0,min(1.0,sum(x*y for x,y in zip(va,vb))/(na*nb))))
        profile_similarity=sum(profile_components)/len(profile_components) if profile_components else 0.0

        compactness=1.0/(1.0+abs(len(current_text.split())-len(previous_text.split()))) if previous_text else 0.0
        semantic_continuity=(
            0.32*vector_similarity +
            0.22*profile_similarity +
            0.14*float(operation_same) +
            0.08*float(representation_same) +
            0.08*phase_relation +
            0.06*entity_overlap +
            0.06*anaphora_score +
            0.04*compactness
        )
        semantic_continuity=max(0.0,min(1.0,0.70*semantic_continuity+0.30*float(continuation_score or 0.0)))

        # Relation is selected from competing semantic states. No phrase list or
        # renderer threshold decides it. Parameter change is structural evidence.
        scores={
            "independent": max(0.0,1.0-semantic_continuity),
            "reference": 0.20*semantic_continuity+0.34*anaphora_score+0.22*(1.0 if reference_to_previous else 0.0)+0.24*entity_overlap,
            "continuation": 0.44*semantic_continuity+0.22*(1.0 if operation_same else 0.0)+0.18*phase_relation+0.16*compactness,
            "parameter_update": 0.52*semantic_continuity+0.28*(1.0 if parameter_change else 0.0)+0.20*(1.0 if operation_same or prev_operation else 0.0),
        }
        relation=max(scores,key=scores.get)
        confidence=float(scores[relation])
        if relation=="parameter_update" and not parameter_change:
            # Without a structural parameter delta, continuation/reference is
            # the semantically honest state.
            relation=max((k for k in scores if k!="parameter_update"),key=scores.get)
            confidence=float(scores[relation])

        inherited_operation=prev_operation if (not curr_operation and prev_operation) else curr_operation
        inherited_rep=prev_rep if (not curr_rep and prev_rep) else curr_rep
        return {
            "same_scene": relation!="independent",
            "continuation": relation in {"continuation","parameter_update"},
            "reference_to_previous": bool(reference_to_previous or relation in {"continuation","parameter_update","reference"}),
            "confidence": round(confidence,6),
            "relation": relation,
            "relation_scores": {k:round(float(v),6) for k,v in scores.items()},
            "parameter_change": parameter_change,
            "previous_numbers": prev_numbers,
            "current_numbers": curr_numbers,
            "vector_similarity": round(float(vector_similarity),6),
            "profile_similarity": round(float(profile_similarity),6),
            "phase_similarity": round(float(phase_relation),6),
            "entity_overlap": round(float(entity_overlap),6),
            "anaphora_score": round(float(anaphora_score),6),
            "state_transfer": {
                "operation": inherited_operation,
                "representation": inherited_rep,
                "previous_numbers": prev_numbers,
                "current_numbers": curr_numbers,
                "parameter_change": parameter_change,
                "operation_same": operation_same,
                "representation_same": representation_same,
                "task_phase": current.get("task_phase") or previous.get("task_phase"),
                "entity_continuity": entity_overlap,
            },
            "engine":"quantum_interpretation_engine.scene_relation",
            "decision_owner":DECISION_OWNER,
            "evidence_only":True,
        }

    def similarities(self, text: str, candidates: Sequence[str]) -> dict[str, float]:
        query = self.normalize(text)
        unique = []
        seen = set()
        for candidate in candidates:
            value = self.normalize(candidate)
            if value and value not in seen:
                seen.add(value)
                unique.append(value)
        if not query or not unique:
            return {}
        if TfidfVectorizer is None or cosine_similarity is None:
            return {
                value: self.similarity(query, value)["score"]
                for value in unique
            }
        try:
            vectorizer = TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 5),
                lowercase=True,
                sublinear_tf=True,
                min_df=1,
            )
            matrix = vectorizer.fit_transform([query, *unique])
            sims = cosine_similarity(matrix[0:1], matrix[1:])[0]
            return {
                value: float(max(0.0, min(1.0, score)))
                for value, score in zip(unique, sims)
            }
        except Exception:
            return {
                value: self.similarity(query, value)["score"]
                for value in unique
            }

    def prewarm_static(self, candidates: Sequence[str]) -> int:
        return len({self.normalize(x) for x in candidates if self.normalize(x)})

    def resolve_context_relation(
        self,
        current_text: str,
        *,
        previous_scene: dict[str, Any] | None = None,
        history: Sequence[dict[str, Any]] | None = None,
        active_topic: str = "",
    ) -> dict[str, Any]:
        """Resolve the current request to one of three semantic context states.

        NEW_TOPIC:
            self-contained request with no justified dependency on a prior scene.

        PREVIOUS_SCENE:
            implicit continuation/reference to the immediate previous completed scene.

        HISTORICAL_SCENE:
            explicit request to bring back an older scene from the available history.

        The resolver produces evidence and a source turn, but does not route to a
        provider or renderer.
        """
        current = self.normalize(current_text)
        previous_scene = previous_scene if isinstance(previous_scene, dict) else {}
        turns = [t for t in (history or []) if isinstance(t, dict)]

        prev_user = self.normalize(
            previous_scene.get("user_request")
            or previous_scene.get("text")
            or previous_scene.get("user")
        )
        prev_answer = self.normalize(
            previous_scene.get("april_answer")
            or previous_scene.get("answer")
            or (previous_scene.get("semantic_state") or {}).get("answer")
        )
        prev_summary = self.normalize(previous_scene.get("summary"))
        prev_scene_id = previous_scene.get("scene_id")

        linguistic = self._anaphora_features(current)
        previous_result_relation = self.similarity(
            current,
            "previous result previous answer this result divide multiply add subtract"
        )["score"]
        explicit_memory_relation = self.similarity(
            current,
            "remember earlier previous conversation old topic we discussed before bring back that scene"
        )["score"]
        current_prev_similarity = (
            self.similarity(current, " ".join(x for x in (prev_user, prev_answer, prev_summary) if x))["score"]
            if (prev_user or prev_answer or prev_summary) else 0.0
        )

        # Explicit historical retrieval is a structural intent: the request
        # refers to an earlier conversation/scene, not merely to the last turn.
        historical_score = max(
            explicit_memory_relation,
            float(linguistic.get("density", 0.0)) * 0.55,
        )

        # Immediate continuation is driven by relation to the completed scene
        # and anaphoric dependence. The current scene remains highest priority.
        immediate_score = max(
            current_prev_similarity,
            previous_result_relation,
            float(linguistic.get("density", 0.0)) * 0.80,
        )

        # If the user explicitly names an older topic/entity found in history,
        # select the best historical turn while avoiding automatic recall.
        historical_match = None
        historical_match_score = 0.0
        if turns:
            for turn in turns[:-1]:  # exclude the immediate tail; current scene is handled above
                user_obj = turn.get("user") if isinstance(turn.get("user"), dict) else {}
                april_obj = turn.get("april") if isinstance(turn.get("april"), dict) else {}
                candidate_text = self.normalize(
                    " ".join(
                        x for x in (
                            user_obj.get("text") or user_obj.get("content") or turn.get("text"),
                            april_obj.get("answer") or april_obj.get("content"),
                            turn.get("summary"),
                        ) if x
                    )
                )
                if not candidate_text:
                    continue
                score = self.similarity(current, candidate_text)["score"]
                if score > historical_match_score:
                    historical_match_score = score
                    historical_match = turn

        # Explicitly old-topic requests need a stronger historical match than a
        # generic continuation. A vague "tell me something" remains NEW_TOPIC.
        if historical_score >= 0.52 and historical_match is not None and historical_match_score >= 0.42:
            state = "HISTORICAL_SCENE"
            source = historical_match
            confidence = max(historical_score, historical_match_score)
        elif previous_scene and immediate_score >= 0.42:
            state = "PREVIOUS_SCENE"
            source = previous_scene
            confidence = immediate_score
        else:
            state = "NEW_TOPIC"
            source = None
            confidence = max(0.0, 1.0 - max(immediate_score, historical_score))

        return {
            "state": state,
            "confidence": round(float(min(1.0, confidence)), 6),
            "immediate_score": round(float(immediate_score), 6),
            "historical_score": round(float(historical_score), 6),
            "historical_match_score": round(float(historical_match_score), 6),
            "previous_scene_id": prev_scene_id,
            "historical_turn_id": (
                (historical_match or {}).get("turn_id")
                if historical_match is not None else None
            ),
            "source_scene": source,
            "previous_result": prev_answer,
            "previous_summary": prev_summary,
            "anaphora": linguistic,
            "engine": "quantum_interpretation_engine.context_relation",
            "decision_owner": DECISION_OWNER,
            "evidence_only": True,
        }

    def dialogue(
        self, text: str, previous_assistant: str = "", previous_user: str = "",
        active_goal: str = "", active_topic: str = "",
        previous_scene_semantics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        profile = self.measure(
            text, previous_assistant=previous_assistant,
            previous_user=previous_user,
            active_topic=active_topic, active_goal=active_goal,
        )
        dialogue = profile["dialogue_scores"]
        best = profile["dialogue_best"]
        assistant_relation = profile["context_scores"].get("previous_assistant", 0.0)
        user_relation = profile["context_scores"].get("previous_user", 0.0)
        topic_relation = profile["context_scores"].get("active_topic", 0.0)

        previous_scene = previous_scene_semantics if isinstance(previous_scene_semantics, dict) else {}
        if not previous_scene and (previous_user or previous_assistant):
            previous_scene = self.build_scene_semantic_state(
                previous_user or previous_assistant,
                answer=previous_assistant,
                profile=self.measure(previous_user or previous_assistant, previous_assistant=previous_assistant),
                previous={},
            )
        current_scene_semantics = self.build_scene_semantic_state(
            text,
            answer=previous_assistant if previous_assistant else "",
            profile=profile,
            previous=previous_scene,
        )

        continuation_score = max(
            float(dialogue.get("continuation", 0.0) or 0.0),
            0.72 * assistant_relation,
            0.58 * user_relation,
            0.64 * topic_relation,
        )
        reference_score = max(
            dialogue.get("reference", 0.0), 0.86 * assistant_relation,
            0.62 * user_relation, 0.70 * topic_relation,
        )
        semantic_relation_probe = self.relate_scene_semantics(
            current_scene_semantics,
            previous_scene,
            reference_to_previous=bool(previous_assistant),
            continuation_score=max(continuation_score, reference_score),
        ) if previous_scene else {}
        if semantic_relation_probe.get("relation") in {"continuation", "parameter_update", "reference"}:
            continuation_score = max(continuation_score, float(semantic_relation_probe.get("confidence", 0.0)) * 0.92)
            reference_score = max(reference_score, float(semantic_relation_probe.get("confidence", 0.0)) * 0.96)

        memory_query_score = float(dialogue.get("memory_query", 0.0) or 0.0)
        reference_score = max(reference_score, memory_query_score)
        if best == "memory_query":
            semantic_relation_probe = {
                **(semantic_relation_probe or {}),
                "same_scene": False,
                "continuation": False,
                "reference_to_previous": bool(previous_assistant),
                "confidence": max(float(memory_query_score), 0.70 if previous_assistant else 0.0),
                "relation": "memory_query",
                "engine": "quantum_interpretation_engine.scene_relation",
                "decision_owner": DECISION_OWNER,
                "evidence_only": True,
            }

        if previous_assistant or previous_user:
            if profile.get("dialogue_best") == "identity" or dialogue.get("identity", 0.0) >= 0.12:
                reference_score = max(reference_score, 0.72)
                continuation_score = max(continuation_score, 0.62)

        scene_relation_preview = (
            self.relate_scene_semantics(
                current_scene_semantics,
                previous_scene,
                reference_to_previous=bool(previous_assistant and reference_score >= 0.60),
                continuation_score=continuation_score,
            )
            if previous_scene else {}
        )
        continuation_score = max(
            continuation_score,
            float(scene_relation_preview.get("confidence", 0.0) or 0.0),
        )
        reference_score = max(
            reference_score,
            0.72 * float(scene_relation_preview.get("confidence", 0.0) or 0.0)
            if scene_relation_preview.get("same_scene") else 0.0,
        )

        continuation = bool(
            previous_assistant
            and best != "memory_query"
            and (best in {
                "continuation", "reformulation", "correction",
                "reference", "affirmation", "rejection",
            } or continuation_score >= 0.72)
        )

        relation = self.relate_scene_semantics(
            current_scene_semantics,
            previous_scene_semantics,
            reference_to_previous=bool(previous_assistant and reference_score >= 0.60),
            continuation_score=continuation_score,
        ) if previous_scene_semantics else {
            "same_scene": bool(continuation or reference_score >= 0.60),
            "continuation": continuation,
            "reference_to_previous": bool(previous_assistant and reference_score >= 0.60),
            "confidence": float(max(continuation_score, reference_score)),
            "relation": "continuation" if continuation else ("reference" if reference_score >= 0.60 else "independent"),
            "parameter_change": False,
            "engine": "quantum_scene_relation_engine",
            "evidence_only": True,
        }
        # Memory recall is a retrieval operation, not a continuation of the
        # active visual scene. Preserve the distinction for the Processor.
        if best == "memory_query":
            relation = {
                **relation,
                "same_scene": False,
                "continuation": False,
                "reference_to_previous": bool(previous_assistant),
                "confidence": max(float(relation.get("confidence", 0.0) or 0.0), 0.70 if previous_assistant else 0.0),
                "relation": "memory_query",
                "engine": "quantum_interpretation_engine.scene_relation",
                "decision_owner": DECISION_OWNER,
                "evidence_only": True,
            }

        continuation = bool(continuation or relation.get("continuation"))
        reference_to_previous = bool(
            previous_assistant and (reference_score >= 0.60 or relation.get("reference_to_previous"))
        )
        return {
            "dialogue": {
                "label": best,
                "confidence": float(profile["dialogue_confidence"]),
                "continuation_score": float(continuation_score),
                "reference_score": float(reference_score),
                "anaphora_score": 0.0,
                "topic_score": float(profile["context_scores"].get("active_topic", 0.0)),
                "goal_score": float(profile["context_scores"].get("active_goal", 0.0)),
            },
            "linguistic": self._linguistic(self.normalize(text)),
            "continuation": continuation,
            "reference_to_previous": reference_to_previous,
            "relation": relation,
            "scene_semantic_state": current_scene_semantics,
            "identity_request": bool(profile["identity_request"]),
            "nli": {
                "labels": list(profile["dialogue_scores"]),
                "scores": list(profile["dialogue_scores"].values()),
                "source": "quantum_matrix",
            },
            "decision_owner": DECISION_OWNER,
            "evidence_only": True,
            "engine": "quantum_dialogue_matrix_view",
        }

    def representations(self, text: str, context: str = "") -> dict[str, Any]:
        profile = self.measure(text, active_topic=context)
        return {
            "nli": {
                "labels": [REPRESENTATION_HYPOTHESES[x] for x in profile["representation_scores"]],
                "scores": list(profile["representation_scores"].values()),
                "source": "quantum_matrix",
            },
            "measurements": [
                {"type": k, "score": float(v), "source": "quantum_matrix"}
                for k, v in sorted(profile["representation_scores"].items(), key=lambda x: x[1], reverse=True)
            ],
            "context_similarity": {
                "score": float(profile["context_scores"].get("active_topic", 0.0)),
                "source": "quantum_matrix",
            },
            "decision_owner": DECISION_OWNER,
            "evidence_only": True,
            "engine": "quantum_representation_matrix_view",
        }

    def domains(self, text: str) -> dict[str, Any]:
        profile = self.measure(text)
        return {
            "measurements": [
                {"domain": k, "score": float(v)}
                for k, v in sorted(profile["domain_scores"].items(), key=lambda x: x[1], reverse=True)
            ],
            "decision_owner": DECISION_OWNER,
            "evidence_only": True,
            "engine": "quantum_domain_matrix_view",
        }

    def interpret(
        self, text: str, cognition: dict | None = None, semantic: dict | None = None,
        history: list | None = None, state: dict | None = None,
    ) -> dict[str, Any] | None:
        text = self.normalize(text)
        if not text:
            return None
        cognition = cognition if isinstance(cognition, dict) else {}
        semantic = semantic if isinstance(semantic, dict) else {}
        state = state if isinstance(state, dict) else {}
        history = history if isinstance(history, list) else []

        last_assistant, last_user, reply_to = self._history(history)
        active_topic = self.normalize(
            state.get("active_topic") or state.get("current_topic")
            or semantic.get("active_topic") or semantic.get("current_topic")
            or cognition.get("active_topic") or cognition.get("current_topic")
        )
        active_goal = self.normalize(
            state.get("active_goal") or state.get("current_goal")
            or semantic.get("active_goal") or cognition.get("active_goal")
            or cognition.get("current_goal")
        )

        started = time.perf_counter()
        profile = self.measure(
            text,
            previous_assistant=last_assistant,
            previous_user=last_user,
            active_topic=active_topic,
            active_goal=active_goal,
            modalities={
                "voice": semantic.get("voice_context") or cognition.get("voice_context"),
                "vision": semantic.get("vision_context") or cognition.get("vision_context"),
                "gallery": semantic.get("gallery_context") or cognition.get("gallery_context"),
                "files": semantic.get("file_context") or cognition.get("file_context"),
            },
        )
        matrix = profile["scene_matrix"]
        previous_scene_semantics = {}
        current_scene = state.get("current_visual_scene") or state.get("active_visual_scene")
        if isinstance(current_scene, dict):
            previous_scene_semantics = (
                current_scene.get("semantic_state")
                if isinstance(current_scene.get("semantic_state"), dict)
                else {}
            )
        context_relation = self.resolve_context_relation(
            text,
            previous_scene=current_scene if isinstance(current_scene, dict) else None,
            history=history,
            active_topic=active_topic,
        )
        dialogue_result = self.dialogue(
            text, previous_assistant=last_assistant, previous_user=last_user,
            active_goal=active_goal, active_topic=active_topic,
            previous_scene_semantics=previous_scene_semantics,
        )
        dialogue = dialogue_result["dialogue"]
        scene_semantic_state = dialogue_result.get("scene_semantic_state", {})

        explicit_required = [
            str(x).lower()
            for x in (
                semantic.get("required_representations", []) or []
            ) + (
                cognition.get("required_representations", []) or []
            )
            if str(x).strip()
        ]
        required_representations = list(dict.fromkeys(
            explicit_required
            if explicit_required
            else (
                [str(scene_semantic_state.get("requested_representation")).lower()]
                if scene_semantic_state.get("explicit_representation")
                and scene_semantic_state.get("requested_representation") not in {None, "", "text"}
                else []
            )
        ))

        # The scene-state engine owns the semantic role of a representation.
        # A contextual mention (for example, "formula for a graph") does not
        # automatically make the graph renderer current. The current task phase
        # and requested artifact determine the representation evidence.
        scene_representation = str(
            scene_semantic_state.get("requested_representation") or ""
        ).strip().lower()
        scene_rep_conf = float(
            scene_semantic_state.get("representation_confidence", 0.0) or 0.0
        )
        scene_rep_explicit = bool(scene_semantic_state.get("explicit_representation"))
        if scene_representation and (
            scene_rep_explicit or scene_semantic_state.get("inherited_representation")
        ):
            required_representations = [scene_representation]

        candidate_domains = [
            k for k, v in profile["domain_scores"].items() if float(v) >= 0.45
        ]
        required_domains = list(
            semantic.get("required_domains", []) or candidate_domains
        )

        continuation = bool(
            last_assistant and (
                bool(dialogue_result.get("continuation"))
                or dialogue["label"] in {
                    "continuation", "reformulation", "correction",
                    "reference", "affirmation", "rejection",
                }
                or dialogue["continuation_score"] >= 0.72
                or bool(dialogue_result.get("relation", {}).get("continuation"))
            )
        )
        memory_query = dialogue["label"] == "memory_query"
        reference = bool(
            last_assistant and (
                bool(dialogue_result.get("reference_to_previous"))
                or dialogue["reference_score"] >= 0.60
                or memory_query
                or bool(dialogue_result.get("relation", {}).get("reference_to_previous"))
            )
        )
        topic_shift = bool(
            active_topic and not continuation and not reference
            and profile["context_scores"].get("active_topic", 0.0) < 0.35
        )

        # Scene type is an execution decision only when the representation
        # matrix has produced an explicit current-turn representation.
        # Otherwise every ordinary answer stays a text scene; a raw matrix
        # winner (table/gallery/etc.) is evidence, not a trigger.
        scene_type = required_representations[0] if required_representations else "text"
        if scene_semantic_state.get("task_phase") in {"proposal", "explanation"} and scene_representation:
            scene_type = scene_representation
        representation_scores = profile["representation_scores"]
        capability = profile["capability_scores"]

        representation_measurements = dict(
            profile.get("representation_measurements", representation_scores)
        )
        canonical_representation = str(
            scene_semantic_state.get("requested_representation") or "text"
        )
        representation_evidence = [
            SemanticEvidence(
                canonical_representation,
                1.0,
                "quantum_matrix_resolved",
                details={
                    "production": True,
                    "matrix_measurements": representation_measurements,
                },
            ).as_dict()
        ]
        dialogue_contract = {
            "dialog_act": dialogue["label"],
            "current_request": text,
            "resolved_request": (
                f"Continue the previous task naturally.\\n"
                f"Previous assistant response: {last_assistant}\\n"
                f"Current user instruction: {text}"
                if continuation else text
            ),
            "continuation": continuation,
            "reference_to_previous": reference,
            "previous_april_turn": last_assistant,
            "previous_user_turn": last_user,
            "reply_to": reply_to,
            "active_goal": active_goal,
            "active_topic": active_topic,
            "topic_shift": topic_shift,
            "confidence": dialogue["confidence"],
            "canonical": True,
            "version": "quantum_matrix_v1",
        }
        domain_evidence = [
            {"domain": k, "score": float(v)}
            for k, v in sorted(
                profile["domain_scores"].items(), key=lambda x: x[1], reverse=True
            ) if float(v) >= 0.20
        ]

        result = build_result(text)
        result.update({
            "type": profile["dialogue_best"],
            "subtype": scene_type,
            "scene_type": scene_type,
            "candidate_domains": candidate_domains,
            "required_domains": required_domains,
            "domain_confidence": {
                k: round(float(v), 4) for k, v in profile["domain_scores"].items()
            },
            "candidate_representations": list(required_representations),
            "required_representations": required_representations,
            "memory_query": bool(memory_query),
            "representation_evidence": [
                SemanticEvidence(k, float(v), "quantum_matrix").as_dict()
                for k, v in sorted(
                    representation_scores.items(), key=lambda x: x[1], reverse=True
                )
                if float(v) >= 0.02
            ],
            "production_representation": (
                required_representations[0]
                if len(required_representations) == 1
                else "text"
            ),
            "production_representation_locked": bool(
                len(required_representations) == 1
            ),
            "semantic_profile": {
                "active_topic": active_topic,
                "active_goal": active_goal,
                "previous_april_turn": last_assistant,
                "dialogue_history": history[-8:],
                "representation_scores": dict(profile.get("representation_scores", {})),
                "representation_measurements": dict(profile.get("representation_measurements", {})),
                "domain_scores": dict(profile["domain_scores"]),
                "capability_scores": dict(capability),
                "context_scores": dict(profile["context_scores"]),
                "scene_matrix": matrix,
                "engine": "quantum_interpretation_engine",
            },
            "scene_profile": {
                "scene_type": scene_type,
                "dialogue_mode": "semantic_unified",
                "matrix_confidence": matrix["best_score"],
                "matrix_margin": matrix["margin"],
                "task_phase": scene_semantic_state.get("task_phase"),
                "operation": scene_semantic_state.get("operation"),
                "requested_representation": scene_representation or "text",
                "decision_owner": DECISION_OWNER,
            },
            "scene_semantic_state": scene_semantic_state,
            "artifact_contract": {
                "contract": "scene_artifact",
                "transport": TRANSPORT_NAME,
                "scene_type": scene_type,
                "representation": required_representations or [scene_type],
                "semantic_profile_ref": "semantic_profile",
                "decision_owner": DECISION_OWNER,
            },
            "dialogue_relation": dialogue_result.get("relation", {}),
            "context_relation": context_relation,
            "dialogue_contract": {
                "dialog_act": dialogue["label"],
                "current_request": text,
                "resolved_request": (
                    f"Continue the previous task naturally.\n"
                    f"Previous assistant response: {last_assistant}\n"
                    f"Current user instruction: {text}"
                    if continuation else text
                ),
                "continuation": continuation,
                "reference_to_previous": reference,
                "previous_april_turn": last_assistant,
                "previous_user_turn": last_user,
                "reply_to": reply_to,
                "active_goal": active_goal,
                "active_topic": active_topic,
                "topic_shift": topic_shift,
                "confidence": dialogue["confidence"],
                "canonical": True,
                "version": "quantum_matrix_v2",
                "scene_relation": dialogue_result.get("relation", {}),
                "continuation_confidence": float(dialogue_result.get("relation", {}).get("confidence", dialogue["continuation_score"])),
            },
            "dialog_act": dialogue["label"],
            "continuation": float(dialogue["continuation_score"]),
            "continuation_target": last_assistant or active_topic,
            "active_goal": active_goal,
            "active_topic": active_topic,
            "resolved_request": text,
            "context_resolution": {
                "depends_on_previous_dialogue": bool(continuation or reference),
                "previous_user_turn": last_user,
                "previous_assistant_turn": last_assistant,
                "active_topic": active_topic,
                "active_goal": active_goal,
                "relation": context_relation.get("state", "NEW_TOPIC").lower(),
                "context_relation": context_relation,
            },
            "reply_to": reply_to,
            "required_capabilities": [
                "semantic_interpretation", "dialogue_context",
                *( ["memory_retrieval"] if memory_query else [] ),
                *(["representation_evidence"] if required_representations else []),
            ],
            "context_dependency": (
                "historical_scene" if context_relation.get("state") == "HISTORICAL_SCENE" else
                "previous_scene" if context_relation.get("state") == "PREVIOUS_SCENE" else
                "memory_query" if memory_query else
                "new_topic"
            ),
            "context_policy": {
                "current_request": True,
                "dialogue_vector": continuation or reference or memory_query,
                "previous_turn": bool(reply_to),
                "memory_retrieval": bool(memory_query),
                "active_goal": bool(active_goal),
                "full_history": True,
                "semantic_similarity": True,
                "nli_intent": "refinement_only",
                "linguistic_structure": True,
            },
            "quantum_interpretation_field": {
                "linguistic": self._linguistic(text),
                "dialogue": dialogue_contract,
                "representation": representation_evidence,
                "domain": [
                    {"domain": k, "score": float(v)}
                    for k, v in sorted(
                        profile["domain_scores"].items(), key=lambda x: x[1], reverse=True
                    ) if float(v) >= 0.20
                ],
                "context_vectors": profile["context_scores"],
                "profile": profile,
                "scene_matrix": matrix,
                "scene_semantic_state": scene_semantic_state,
                "context_relation": context_relation,
                "decision_owner": DECISION_OWNER,
                "evidence_only": True,
                "engine": "quantum_interpretation_engine",
            },
            "quantum_representation_measurement": {
                "resolved": canonical_representation,
                "production": True,
                "measurements": dict(
                    profile.get("representation_measurements", representation_scores)
                ),
                "scene_matrix": matrix,
            },
            "evidence": {
                "domain": domain_evidence,
                "representation": representation_evidence,
                "math": float(representation_scores.get("formula", 0.0)),
                "code": float(representation_scores.get("code", 0.0)),
                "web": float(capability.get("web", 0.0)),
                "image": float(representation_scores.get("image", 0.0)),
                "continuation": float(dialogue["continuation_score"]),
                "exploration": float(capability.get("exploration", 0.0)),
                "information": float(capability.get("information", 0.0)),
                "linguistic": self._linguistic(text),
                "dialogue": dialogue_contract,
                "context_vectors": profile["context_scores"],
                "cognition": dict(cognition),
                "semantic": dict(semantic),
            },
            "quantum_matrix": matrix,
            "matrix_scene": matrix["best_scene"],
            "matrix_confidence": matrix["best_score"],
            "decision_owner": DECISION_OWNER,
            "routing_owner": DECISION_OWNER,
            "renderer_owner": DECISION_OWNER,
            "provider_calls": 0,
            "canonical_transport": TRANSPORT_NAME,
            "semantic_authority": True,
            "semantic_decision_source": "quantum_cognitive_scene_state",
            "cognitive_scene_state": scene_semantic_state,
            "representation_resolution": "processor_selection",
            "legacy_keyword_matching": False,
            "avoid_trigger_execution": True,
            "machine_only": True,
            "single_route": True,
            "measurement_ms": round((time.perf_counter() - started) * 1000.0, 3),
            "semantic_runtime": self.runtime_status(),
        })

        result["memory_query"] = bool(memory_query)
        result["discussion_mode"] = float(capability.get("discussion", 0.0)) >= 0.60
        result["space_discussion"] = float(capability.get("space", 0.0)) >= 0.60
        result["exploration"] = float(capability.get("exploration", 0.0))
        result["web_context"] = float(capability.get("web", 0.0))
        result["explicit_image_generation"] = float(representation_scores.get("image", 0.0))
        result["lightweight_visual"] = max(
            float(representation_scores.get("graph", 0.0)),
            float(representation_scores.get("diagram", 0.0)),
            float(representation_scores.get("image", 0.0)),
        ) >= 0.72
        result["contains_object"] = bool(text)
        result["contains_explanation"] = float(capability.get("information", 0.0)) >= 0.60
        result["contains_analysis"] = float(capability.get("exploration", 0.0)) >= 0.60
        result["content_role"] = (
            "explanation" if result["contains_explanation"]
            else "analysis" if result["contains_analysis"] else None
        )

        result["estimated_action_count"] = estimate_action_count(result)
        result["response_complexity"] = determine_response_complexity(result)
        result["factory_order"] = build_factory_order(result)
        result["scene_strategy"] = build_scene_strategy(result)
        result["interpretation_state"] = synchronize_interpretation_context(
            build_interpretation_state(), result
        )
        result["transport_state"] = export_transport_state(
            result["interpretation_state"], result
        )
        result["interpretation_state"]["diagnostics"]["matrix"] = matrix
        result["transport_diagnostics"] = build_transport_diagnostics(result)
        result["semantic_engine_diagnostics"] = {
            "engine": "quantum_interpretation_engine",
            "matrix_shape": matrix["matrix_shape"],
            "matrix_features": matrix["feature_order"],
            "single_measurement": True,
            "single_route": True,
            "fallback_mode": False,
            "substring_routing": False,
            "renderer_selection_owner": DECISION_OWNER,
            "provider_calls": 0,
        }
        propagate_canonical_response(result, result["transport_state"])
        bridge_machine_response(result, result["transport_state"])
        validate_response_complexity(result)
        return result


# ---------------------------------------------------------------------------
# Canonical result / transport helpers
# ---------------------------------------------------------------------------

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
    state["artifacts"]["contract"] = result.get("artifact_contract")
    state["executor"]["contract"] = result.get("executor_preparation_contract")
    return state


def export_transport_state(state: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    state = ensure_transport_defaults(state)
    for field, (section, key) in INTERPRETATION_TRANSPORT_FIELDS.items():
        if field in result:
            state[section][key] = result[field]
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


def bridge_machine_response(result: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    machine = state.setdefault("machine_response", {})
    scene = state.setdefault("scene_contract", {})
    content = machine.get("content") or result.get("normalized") or result.get(
        "assistant_response", ""
    )
    machine["content"] = content
    scene.update({"content": content, "answer": content, "summary": content})
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
QUANTUM_SCENE_STATE_ENGINE = QUANTUM_INTERPRETATION_ENGINE

# Public class aliases preserve import names without reinstating parallel engines.
QuantumFastSemanticEngine = QuantumInterpretationEngine
QuantumLinguisticEngine = QuantumInterpretationEngine
QuantumEmbeddingEngine = QuantumInterpretationEngine
QuantumIntentEngine = QuantumInterpretationEngine
QuantumEvidenceFusionEngine = QuantumInterpretationEngine
QuantumDialogueEngine = QuantumInterpretationEngine
QuantumSceneInterpretationMatrix = QuantumInterpretationEngine


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


# ---------------------------------------------------------------------------
# Deep-model API compatibility
# ---------------------------------------------------------------------------

def _runtime_ready_guard() -> dict[str, Any]:
    return QUANTUM_INTERPRETATION_ENGINE.runtime_status()


def _ensure_semantic_runtime() -> None:
    QUANTUM_INTERPRETATION_ENGINE.start_semantic_runtime(background=False)


def preload_semantic_runtime() -> dict[str, Any]:
    """Preload the canonical semantic runtime before user traffic."""
    return QUANTUM_INTERPRETATION_ENGINE.start_semantic_runtime(background=False)


def start_semantic_accelerator() -> dict[str, Any]:
    """Start the canonical semantic runtime in the background."""
    return QUANTUM_INTERPRETATION_ENGINE.start_semantic_runtime(background=True)


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

# Canonical module initialization: start the already-created interpretation
# engine only after its public startup entrypoint has been defined.
# No parallel engine, provider, memory, or route is created.
start_semantic_accelerator()
