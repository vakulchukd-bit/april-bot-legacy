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

import os
import re
import hashlib
import threading
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

import spacy
import stanza
from spacy.language import Language
from sentence_transformers import SentenceTransformer
from stanza.pipeline.multilingual import MultilingualPipeline
from transformers import pipeline as hf_pipeline
from sklearn.metrics.pairwise import cosine_similarity

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

# ---------------------------------------------------------------------------
# Quantum Interpretation Engine
#
# One specialized room. One engine stack. One output evidence field.
#
# No renderer routing, no provider calls, no fallback semantics, no substring
# trigger ownership. The Quantum Processor remains the final decision owner.
# ---------------------------------------------------------------------------

SEMANTIC_MODEL_NAME = os.getenv(
    "APRIL_SENTENCE_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
NLI_MODEL_NAME = os.getenv(
    "APRIL_ZERO_SHOT_MODEL",
    "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
)
SPACY_MODEL_NAME = os.getenv("APRIL_SPACY_MODEL", "xx_ent_wiki_sm")

# Real engines are required. Missing packages/models are deployment errors.

# Heavy semantic models are created through one runtime gate instead of during
# Python import. This keeps deployment import-safe while all required engines
# remain mandatory for semantic work.
SPACY_NLP: Language | None = None
STANZA_NLP: MultilingualPipeline | None = None
SEMANTIC_ENCODER: SentenceTransformer | None = None
DIALOGUE_NLI: Any = None
_SEMANTIC_RUNTIME_READY = False

# Canonical Stanza runtime state. Resources are provisioned once into the
# configured model directory; live requests never perform resource checks
# unless the runtime has not been initialized yet.
STANZA_RESOURCE_DIR = Path(
    os.getenv(
        "APRIL_STANZA_RESOURCES_DIR",
        os.getenv(
            "STANZA_RESOURCES_DIR",
            str(Path.home() / "stanza_resources"),
        ),
    )
).expanduser()
STANZA_BOOTSTRAP_LANGS = tuple(
    lang.strip().lower()
    for lang in os.getenv("APRIL_STANZA_LANGS", "ru").split(",")
    if lang.strip()
)
STANZA_RESOURCES_FILE = STANZA_RESOURCE_DIR / "resources.json"
# Keep the semantic accelerator focused on the annotations actually consumed
# by QuantumLinguisticEngine. MWT is language/package dependent and was the
# direct cause of the Railway crash ("mwt, default"). Dependency parsing is
# not required for dialogue-signal measurement, so it is intentionally kept
# out of the bootstrap path as well.
STANZA_LANGUAGE_PROCESSORS = os.getenv(
    "APRIL_STANZA_PROCESSORS",
    "tokenize,pos,lemma",
)
STANZA_LANGID_MODEL_FILE = STANZA_RESOURCE_DIR / "multilingual" / "langid" / "ud.pt"
# Language weights are warmed only for the configured fast path. Additional
# languages remain explicit configuration, not automatic deployment work.
STANZA_PREWARM_LANGS = tuple(
    lang.strip().lower()
    for lang in os.getenv("APRIL_STANZA_PREWARM_LANGS", "ru").split(",")
    if lang.strip() and lang.strip().lower() in STANZA_BOOTSTRAP_LANGS
)
_STANZA_BOOTSTRAP_ATTEMPTED = False
_SEMANTIC_RUNTIME_LOCK = threading.RLock()
_SEMANTIC_ACCELERATOR_STARTED = False
_SEMANTIC_ACCELERATOR_ERROR: Exception | None = None

# Canonical quantum snapshot helper.
# Downstream diagnostics must receive plain transport-safe data only.
# It never invokes a model and therefore cannot add latency to the route.
def _quantum_snapshot(value: Any, *, _depth: int = 0, _max_depth: int = 8) -> Any:
    """Return a transport-safe immutable-ish snapshot of quantum evidence.

    The interpretation layer may contain nested dictionaries/lists and numeric
    model outputs. Diagnostics and MachineResponse must never receive live
    model objects, custom classes, sets, or other runtime references.
    """
    if _depth >= _max_depth:
        return "<max-depth>"

    if value is None or isinstance(value, (str, bool, int, float)):
        return value

    if isinstance(value, dict):
        return {
            str(key): _quantum_snapshot(
                item,
                _depth=_depth + 1,
                _max_depth=_max_depth,
            )
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _quantum_snapshot(
                item,
                _depth=_depth + 1,
                _max_depth=_max_depth,
            )
            for item in value
        ]

    if isinstance(value, set):
        return [
            _quantum_snapshot(
                item,
                _depth=_depth + 1,
                _max_depth=_max_depth,
            )
            for item in sorted(value, key=lambda item: str(item))
        ]

    # Last-resort compatibility representation. This branch is diagnostic-only
    # and is deliberately non-executing: it cannot affect routing or providers.
    return str(value)


# Canonical Quantum Measurement runtime.
# One turn -> one semantic field. Repeated callers consume the cached field.
_QUANTUM_MEASUREMENT_CACHE: dict[tuple, Dict[str, Any]] = {}
_QUANTUM_MEASUREMENT_CACHE_LIMIT = 96
_QUANTUM_HYPOTHESIS_EMBEDDINGS: dict[str, Any] = {}
_QUANTUM_HYPOTHESIS_INDEX_READY = False
_QUANTUM_HYPOTHESIS_INDEX_LOCK = threading.RLock()
_QUANTUM_RUNTIME_METRICS = {
    "measurements": 0,
    "cache_hits": 0,
    "nli_refinements": 0,
    "nli_full_passes": 0,
    "last_elapsed_ms": 0.0,
    "last_stage_ms": {},
}


def _stanza_lang_ready(lang: str) -> bool:
    root = STANZA_RESOURCE_DIR / lang
    required = (
        root / "tokenize",
        root / "pos",
        root / "lemma",
    )
    return root.is_dir() and all(path.exists() for path in required)


def _stanza_resources_ready() -> bool:
    """Validate the actual files MultilingualPipeline will open."""
    if not STANZA_RESOURCES_FILE.is_file() or STANZA_RESOURCES_FILE.stat().st_size <= 0:
        return False

    # A resources.json alone is insufficient. The previous deployment had the
    # manifest but not multilingual/langid/ud.pt, which caused the empty bubble
    # and HTTP 500 during the first semantic request.
    if not STANZA_LANGID_MODEL_FILE.is_file() or STANZA_LANGID_MODEL_FILE.stat().st_size <= 0:
        return False

    return all(_stanza_lang_ready(lang) for lang in STANZA_BOOTSTRAP_LANGS)


def _provision_stanza_resources() -> None:
    """Prepare all mandatory Stanza files once, never during normal turns."""
    global _STANZA_BOOTSTRAP_ATTEMPTED

    with _SEMANTIC_RUNTIME_LOCK:
        if _stanza_resources_ready():
            return
        _STANZA_BOOTSTRAP_ATTEMPTED = True
        STANZA_RESOURCE_DIR.mkdir(parents=True, exist_ok=True)

        try:
            # IMPORTANT: resources.json is not the readiness signal. Explicitly
            # provision the multilingual langid model required by MultilingualPipeline.
            stanza.download(
                lang="multilingual",
                model_dir=str(STANZA_RESOURCE_DIR),
                processors="langid",
                logging_level="WARN",
            )

            for language in STANZA_BOOTSTRAP_LANGS:
                if not _stanza_lang_ready(language):
                    # Do not request MWT globally. Stanza documents MWT as
                    # language-dependent; requesting it for every language
                    # makes the default package lookup fail when one language
                    # has no MWT model in the installed resources manifest.
                    stanza.download(
                        lang=language,
                        model_dir=str(STANZA_RESOURCE_DIR),
                        processors=STANZA_LANGUAGE_PROCESSORS,
                        logging_level="WARN",
                    )

            if not _stanza_resources_ready():
                raise RuntimeError(
                    "STANZA_RESOURCE_BOOTSTRAP_INCOMPLETE: "
                    f"langid={STANZA_LANGID_MODEL_FILE}; "
                    f"resources={STANZA_RESOURCES_FILE}; "
                    f"languages={STANZA_BOOTSTRAP_LANGS}"
                )
        except Exception:
            # A transient Hub/network error must not poison the process forever.
            _STANZA_BOOTSTRAP_ATTEMPTED = False
            raise


def _prewarm_stanza_language_cache(pipeline: MultilingualPipeline, languages: Sequence[str]) -> None:
    """Warm only the explicitly configured hot-language cache.

    MultilingualPipeline already owns the runtime cache. Warming every
    provisioned language makes deployment unnecessarily expensive, so the
    quantum accelerator warms only STANZA_PREWARM_LANGS.
    """
    if pipeline is None:
        raise RuntimeError("Stanza multilingual pipeline is not initialized")

    samples = {
        "ru": "Это служебный прогрев русского семантического контура.",
        "uk": "Це службовий прогрів українського семантичного контуру.",
        "en": "This is a semantic runtime warmup sentence.",
    }

    warmed = []
    for language in languages:
        code = str(language or "").strip().lower()
        if not code:
            continue
        sample = samples.get(code, "Semantic runtime warmup.")
        pipeline([sample])
        warmed.append(code)

    print(
        f"⚡ STANZA LANGUAGE CACHE READY: {','.join(warmed) if warmed else 'lazy-mode'}",
        flush=True,
    )


def _ensure_semantic_runtime() -> None:
    global SPACY_NLP, STANZA_NLP, SEMANTIC_ENCODER, DIALOGUE_NLI, _SEMANTIC_RUNTIME_READY
    if _SEMANTIC_RUNTIME_READY:
        return

    with _SEMANTIC_RUNTIME_LOCK:
        if _SEMANTIC_RUNTIME_READY:
            return

        started = time.perf_counter()
        try:
            SPACY_NLP = spacy.load(SPACY_MODEL_NAME)
            # Keep only the entity component for this room. Linguistic
            # token/lemma/POS work is already provided by Stanza.
            if getattr(SPACY_NLP, "pipe_names", None):
                for pipe_name in list(SPACY_NLP.pipe_names):
                    if pipe_name != "ner":
                        try:
                            SPACY_NLP.disable_pipe(pipe_name)
                        except Exception:
                            pass

            if not _stanza_resources_ready():
                _provision_stanza_resources()

            lang_subset = list(STANZA_BOOTSTRAP_LANGS)
            lang_configs = {
                lang: {"processors": STANZA_LANGUAGE_PROCESSORS}
                for lang in lang_subset
            }

            STANZA_NLP = MultilingualPipeline(
                model_dir=str(STANZA_RESOURCE_DIR),
                max_cache_size=12,
                download_method=None,
                lang_id_config={"langid_lang_subset": lang_subset} if lang_subset else None,
                lang_configs=lang_configs or None,
            )

            _prewarm_stanza_language_cache(STANZA_NLP, STANZA_PREWARM_LANGS)

            SEMANTIC_ENCODER = SentenceTransformer(SEMANTIC_MODEL_NAME)
            DIALOGUE_NLI = hf_pipeline(
                "zero-shot-classification",
                model=NLI_MODEL_NAME,
            )
        except Exception:
            STANZA_NLP = None
            SEMANTIC_ENCODER = None
            DIALOGUE_NLI = None
            raise

        _SEMANTIC_RUNTIME_READY = True
        os.environ["APRIL_STANZA_RUNTIME_READY"] = "1"
        elapsed = time.perf_counter() - started
        print(
            f"⚡ SEMANTIC ACCELERATOR READY: runtime_preloaded=1 elapsed={elapsed:.2f}s",
            flush=True,
        )


def preload_semantic_runtime() -> None:
    """Prewarm the complete semantic stack before the first user request."""
    _ensure_semantic_runtime()


def start_semantic_accelerator() -> None:
    """Start one background prewarm worker for the existing semantic route."""
    global _SEMANTIC_ACCELERATOR_STARTED, _SEMANTIC_ACCELERATOR_ERROR
    if _SEMANTIC_ACCELERATOR_STARTED:
        return

    _SEMANTIC_ACCELERATOR_STARTED = True

    def _worker() -> None:
        global _SEMANTIC_ACCELERATOR_ERROR
        try:
            print("⚡ SEMANTIC ACCELERATOR: PREWARM START", flush=True)
            preload_semantic_runtime()
        except Exception as exc:
            _SEMANTIC_ACCELERATOR_ERROR = exc
            print(
                f"⚡ SEMANTIC ACCELERATOR ERROR: {type(exc).__name__}: {exc}",
                flush=True,
            )

    threading.Thread(
        target=_worker,
        name="april-semantic-accelerator",
        daemon=True,
    ).start()


# Start the accelerator without blocking module import. This prevents a
# missing/downloadable semantic model from crashing bot.py before Flask/Railway
# can finish booting. If a request arrives first, _ensure_semantic_runtime()
# still owns the same single runtime gate and waits for the shared lock.
start_semantic_accelerator()

DIALOGUE_LABELS = (
    "question",
    "request",
    "reformulation",
    "continuation",
    "correction",
    "reference",
    "affirmation",
    "rejection",
    "new_topic",
    "statement",
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

DOMAIN_HYPOTHESES = {
    "biology": "the request is primarily about biology or living organisms",
    "chemistry": "the request is primarily about chemistry or chemical substances",
    "physics": "the request is primarily about physics",
    "engineering": "the request is primarily about engineering or design",
    "it": "the request is primarily about computing, programming, or software",
    "literature": "the request is primarily about literature or writing",
    "politics": "the request is primarily about politics or government",
    "news": "the request is primarily about current events or news",
    "social": "the request is primarily about society or social topics",
    "web": "the request is primarily about finding or using web resources",
}

# Capability hypotheses are evidence labels, not routing decisions.
# They are consumed by the Quantum Processor as one semantic evidence family.
CAPABILITY_HYPOTHESES = {
    "exploration": "the user wants analysis, comparison, investigation, or deeper examination",
    "web": "the user wants web search, an online resource, or information from the internet",
    "code": "the user wants programming code or a software implementation",
    "information": "the user wants an explanation, factual answer, or clarification",
    "discussion": "the user wants a discussion, opinion, or reasoning about a topic",
    "space": "the user is discussing spatial arrangement, scene layout, or visual composition",
}

NLI_HYPOTHESIS_FAMILIES = {
    "dialogue": DIALOGUE_LABELS,
    "representation": tuple(REPRESENTATION_HYPOTHESES.values()),
    "domain": tuple(DOMAIN_HYPOTHESES.values()),
    "capability": tuple(CAPABILITY_HYPOTHESES.values()),
}

QUANTUM_PREFILTER_TOP_K = {
    "dialogue": 3,
    "representation": 2,
    "domain": 2,
    "capability": 2,
}
QUANTUM_REFINEMENT_MARGIN = 0.08
QUANTUM_REFINEMENT_SCORE = 0.54


def _prototype_key(family: str, hypothesis: str) -> str:
    return f"{family}::{hypothesis}"


def _ensure_hypothesis_index() -> None:
    """Build one reusable multilingual semantic index for NLI candidates."""
    global _QUANTUM_HYPOTHESIS_INDEX_READY
    if _QUANTUM_HYPOTHESIS_INDEX_READY:
        return

    with _QUANTUM_HYPOTHESIS_INDEX_LOCK:
        if _QUANTUM_HYPOTHESIS_INDEX_READY:
            return
        _embedding_runtime_guard()
        labels = [
            (family, hypothesis)
            for family, hypotheses in NLI_HYPOTHESIS_FAMILIES.items()
            for hypothesis in hypotheses
        ]
        vectors = SEMANTIC_ENCODER.encode(
            [hypothesis for _, hypothesis in labels],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        _QUANTUM_HYPOTHESIS_EMBEDDINGS.clear()
        for (family, hypothesis), vector in zip(labels, vectors):
            _QUANTUM_HYPOTHESIS_EMBEDDINGS[_prototype_key(family, hypothesis)] = vector
        _QUANTUM_HYPOTHESIS_INDEX_READY = True


def _semantic_prefilter(
    text: str,
    families: Dict[str, Sequence[str]],
) -> tuple[list[str], Dict[str, Any]]:
    """Select a compact semantic candidate field before expensive NLI.

    This is vector retrieval, not lexical triggering. The full hypothesis
    library stays available; only the highest semantic candidates are sent to
    the NLI refinement stage.
    """
    _ensure_hypothesis_index()
    query = normalize_text(text)
    if not query:
        return [], {"families": {}, "mode": "empty"}

    query_vec = SEMANTIC_ENCODER.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )[0]

    selected: list[str] = []
    family_meta: Dict[str, Any] = {}

    for family, hypotheses in families.items():
        scored = []
        for hypothesis in hypotheses:
            vector = _QUANTUM_HYPOTHESIS_EMBEDDINGS[_prototype_key(family, hypothesis)]
            score = float(vector @ query_vec)
            scored.append((hypothesis, max(0.0, min(1.0, score))))

        scored.sort(key=lambda item: item[1], reverse=True)
        top_k = max(1, int(QUANTUM_PREFILTER_TOP_K.get(family, 2)))
        top = scored[:top_k]

        margin = 0.0
        if len(scored) > 1:
            margin = scored[0][1] - scored[1][1]

        # Low-confidence families get a slightly wider NLI refinement field,
        # but never the whole library unless the semantic margin is extremely
        # weak. This preserves accuracy without forcing every request through
        # the full 35-ish hypothesis set.
        if margin < QUANTUM_REFINEMENT_MARGIN or (top and top[0][1] < QUANTUM_REFINEMENT_SCORE):
            widened = scored[: min(len(scored), top_k + 2)]
        else:
            widened = top

        family_meta[family] = {
            "vector_candidates": [
                {"label": label, "score": round(score, 6)}
                for label, score in widened
            ],
            "top_score": round(scored[0][1], 6) if scored else 0.0,
            "margin": round(margin, 6),
            "candidate_count": len(widened),
        }
        selected.extend(label for label, _ in widened)

    return list(dict.fromkeys(selected)), {
        "families": family_meta,
        "mode": "semantic_prefilter",
        "candidate_count": len(selected),
    }


def _split_nli_families(result: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Split one NLI measurement into the canonical evidence families."""
    labels = list(result.get("labels") or [])
    scores = [float(x) for x in (result.get("scores") or [])]
    score_map = {label: score for label, score in zip(labels, scores)}
    families = {}
    for family, hypotheses in NLI_HYPOTHESIS_FAMILIES.items():
        family_scores = [
            (hypothesis, score_map[hypothesis])
            for hypothesis in hypotheses
            if hypothesis in score_map
        ]
        family_scores.sort(key=lambda item: item[1], reverse=True)
        families[family] = {
            "labels": [label for label, _ in family_scores],
            "scores": [score for _, score in family_scores],
            "source": "transformers_nli",
            "batched": True,
        }
    return families


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
            "score": float(max(0.0, min(1.0, self.score))),
            "source": self.source,
            "positive": bool(self.positive),
            "details": self.details or {},
        }


def _runtime_ready_guard() -> None:
    _ensure_semantic_runtime()
    if not _SEMANTIC_RUNTIME_READY or STANZA_NLP is None or SEMANTIC_ENCODER is None or DIALOGUE_NLI is None:
        raise RuntimeError("Quantum Interpretation semantic runtime is not ready")


def _embedding_runtime_guard() -> None:
    """Load only the shared embedding engine when vector evidence is needed."""
    global SEMANTIC_ENCODER
    if SEMANTIC_ENCODER is not None:
        return
    with _SEMANTIC_RUNTIME_LOCK:
        if SEMANTIC_ENCODER is not None:
            return
        started = time.perf_counter()
        SEMANTIC_ENCODER = SentenceTransformer(SEMANTIC_MODEL_NAME)
        elapsed = time.perf_counter() - started
        print(
            f"⚡ SEMANTIC EMBEDDING ENGINE READY: shared=1 elapsed={elapsed:.2f}s",
            flush=True,
        )


def get_shared_semantic_encoder() -> SentenceTransformer:
    """Return the one shared sentence-transformer engine for all rooms."""
    _embedding_runtime_guard()
    assert SEMANTIC_ENCODER is not None
    return SEMANTIC_ENCODER


class QuantumLinguisticEngine:
    """
    Dedicated linguistic engine.

    Stanza performs multilingual neural sentence/token processing, POS and
    lemma analysis. spaCy supplies entity analysis using the already installed
    multilingual NER model. Dependency fields are retained in the canonical
    evidence shape and remain empty when dependency parsing is not provisioned.
    """

    def analyze(self, text: str) -> Dict[str, Any]:
        _runtime_ready_guard()
        if not text or not text.strip():
            return {
                "language": None,
                "tokens": [],
                "lemmas": [],
                "pos": [],
                "dependencies": [],
                "entities": [],
                "sentences": [],
                "source": "stanza+spacy",
            }

        docs = STANZA_NLP([text])
        doc = docs[0] if isinstance(docs, list) else docs

        sentences: list[str] = []
        tokens: list[str] = []
        lemmas: list[str] = []
        pos: list[str] = []
        dependencies: list[dict[str, Any]] = []

        for sentence in doc.sentences:
            sentences.append(sentence.text)
            for word in sentence.words:
                tokens.append(word.text)
                lemmas.append((word.lemma or word.text).lower())
                pos.append(word.upos or "")
                head_text = ""
                if word.head:
                    index = int(word.head) - 1
                    if 0 <= index < len(sentence.words):
                        head_text = sentence.words[index].text
                dependencies.append({
                    "text": word.text,
                    "lemma": word.lemma or word.text,
                    "upos": word.upos,
                    "xpos": word.xpos,
                    "feats": word.feats,
                    "head": head_text,
                    "deprel": getattr(word, "deprel", None),
                })

        ner_doc = SPACY_NLP(text)
        entities = [
            {
                "text": entity.text,
                "label": entity.label_,
                "start": entity.start_char,
                "end": entity.end_char,
            }
            for entity in ner_doc.ents
        ]

        return {
            "language": getattr(doc, "lang", None),
            "tokens": tokens,
            "lemmas": lemmas,
            "pos": pos,
            "dependencies": dependencies,
            "entities": entities,
            "sentences": sentences,
            "source": "stanza+spacy",
            "engine": "quantum_linguistic_engine",
        }


class QuantumEmbeddingEngine:
    """Semantic vector engine for request/history/topic/goal comparison."""

    def __init__(self):
        self._pair_cache: dict[tuple[str, str], float] = {}
        self._batch_cache: dict[tuple[str, tuple[str, ...]], Dict[str, float]] = {}
        self._cache_limit = 256

    def _remember_pair(self, key: tuple[str, str], score: float) -> None:
        self._pair_cache[key] = score
        if len(self._pair_cache) > self._cache_limit:
            self._pair_cache.pop(next(iter(self._pair_cache)))

    def similarity(self, text_a: str, text_b: str) -> Dict[str, Any]:
        _embedding_runtime_guard()
        text_a = normalize_text(text_a)
        text_b = normalize_text(text_b)
        if not text_a or not text_b:
            return {
                "score": 0.0,
                "source": "sentence_transformers",
                "measured": False,
            }

        key = (text_a, text_b)
        if key in self._pair_cache:
            return {
                "score": self._pair_cache[key],
                "source": "sentence_transformers",
                "measured": True,
                "cached": True,
            }

        vectors = SEMANTIC_ENCODER.encode(
            [text_a, text_b],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        score = float(
            cosine_similarity(
                vectors[0].reshape(1, -1),
                vectors[1].reshape(1, -1),
            )[0][0]
        )
        score = max(0.0, min(1.0, score))
        self._remember_pair(key, score)
        return {
            "score": score,
            "source": "sentence_transformers",
            "measured": True,
            "cached": False,
        }

    def similarities(self, text: str, candidates: Sequence[str]) -> Dict[str, float]:
        """Batch semantic comparison used by one interpretation turn.

        Results are cached by the exact semantic pair set so the same turn does
        not repeatedly encode identical context fields.
        """
        _embedding_runtime_guard()
        text = normalize_text(text)
        unique = []
        seen = set()
        for candidate in candidates:
            candidate = normalize_text(candidate)
            if candidate and candidate not in seen:
                seen.add(candidate)
                unique.append(candidate)

        if not text or not unique:
            return {candidate: 0.0 for candidate in unique}

        key = (text, tuple(unique))
        cached = self._batch_cache.get(key)
        if cached is not None:
            return dict(cached)

        vectors = SEMANTIC_ENCODER.encode(
            [text, *unique],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        scores = cosine_similarity(
            vectors[0].reshape(1, -1),
            vectors[1:],
        )[0]
        result = {
            candidate: max(0.0, min(1.0, float(score)))
            for candidate, score in zip(unique, scores)
        }
        self._batch_cache[key] = result
        if len(self._batch_cache) > self._cache_limit:
            self._batch_cache.pop(next(iter(self._batch_cache)))
        for candidate, score in result.items():
            self._remember_pair((text, candidate), score)
        return result


class QuantumIntentEngine:
    """NLI refinement engine fed by semantic candidate retrieval."""

    def classify(
        self,
        text: str,
        hypotheses: Sequence[str],
        *,
        family_map: Dict[str, Sequence[str]] | None = None,
    ) -> Dict[str, Any]:
        _runtime_ready_guard()
        requested = list(hypotheses)
        prefilter = {"mode": "explicit", "candidate_count": len(requested)}
        if family_map:
            requested, prefilter = _semantic_prefilter(text, family_map)

        # Keep the NLI call strictly semantic. No word list controls routing.
        result = DIALOGUE_NLI(
            text,
            candidate_labels=list(requested),
            multi_label=True,
        )

        used_full_library = len(requested) >= len(
            tuple(dict.fromkeys(x for values in NLI_HYPOTHESIS_FAMILIES.values() for x in values))
        )
        _QUANTUM_RUNTIME_METRICS["nli_refinements"] += 1
        if used_full_library:
            _QUANTUM_RUNTIME_METRICS["nli_full_passes"] += 1

        return {
            "labels": list(result["labels"]),
            "scores": [float(score) for score in result["scores"]],
            "source": "transformers_nli",
            "semantic_prefilter": prefilter,
            "candidate_count": len(requested),
            "full_hypothesis_library": used_full_library,
        }


class QuantumEvidenceFusionEngine:
    """
    Single-turn semantic measurement engine.

    Each turn performs one linguistic pass, one batched embedding pass, and
    one cached NLI measurement per semantic family. Public helper methods read
    from the same turn cache instead of re-running heavy models.
    """

    def __init__(self):
        self.linguistic = QuantumLinguisticEngine()
        self.embedding = QuantumEmbeddingEngine()
        self.intent = QuantumIntentEngine()
        self._turn_cache: dict[tuple, Dict[str, Any]] = {}
        self._linguistic_cache: dict[str, Dict[str, Any]] = {}
        self._nli_cache: dict[str, Dict[str, Any]] = {}
        self._cache_limit = 96

    @staticmethod
    def _best_label(result: Dict[str, Any]) -> tuple[str, float]:
        labels = result.get("labels") or []
        scores = result.get("scores") or []
        if not labels:
            return "statement", 0.0
        return str(labels[0]), float(scores[0])

    def turn_measurement(
        self,
        text: str,
        previous_assistant: str = "",
        previous_user: str = "",
        active_goal: str = "",
        active_topic: str = "",
    ) -> Dict[str, Any]:
        started = time.perf_counter()
        key = (
            str(text or "").strip(),
            str(previous_assistant or "").strip(),
            str(active_goal or "").strip(),
            str(active_topic or "").strip(),
        )
        cached = self._turn_cache.get(key)
        if cached is not None:
            _QUANTUM_RUNTIME_METRICS["cache_hits"] += 1
            return cached

        normalized_turn_text = str(text or "").strip()
        stage_times: Dict[str, float] = {}

        stage = time.perf_counter()
        linguistic = self._linguistic_cache.get(normalized_turn_text)
        if linguistic is None:
            linguistic = self.linguistic.analyze(normalized_turn_text)
            self._linguistic_cache[normalized_turn_text] = linguistic
        stage_times["linguistic_ms"] = round((time.perf_counter() - stage) * 1000.0, 3)

        stage = time.perf_counter()
        nli_bundle = self._nli_cache.get(normalized_turn_text)
        nli_metadata: Dict[str, Any] = {}
        if nli_bundle is None:
            combined_hypotheses = tuple(
                dict.fromkeys(
                    hypothesis
                    for family in NLI_HYPOTHESIS_FAMILIES.values()
                    for hypothesis in family
                )
            )
            family_map = {
                family: tuple(hypotheses)
                for family, hypotheses in NLI_HYPOTHESIS_FAMILIES.items()
                if any(hypothesis in combined_hypotheses for hypothesis in hypotheses)
            }
            combined_nli = self.intent.classify(
                normalized_turn_text,
                combined_hypotheses,
                family_map=family_map,
            )
            split = _split_nli_families(combined_nli)
            nli_metadata = {
                "semantic_prefilter": combined_nli.get("semantic_prefilter", {}),
                "candidate_count": combined_nli.get("candidate_count", len(combined_hypotheses)),
                "full_hypothesis_library": bool(combined_nli.get("full_hypothesis_library")),
            }
            nli_bundle = {
                "dialogue_nli": split["dialogue"],
                "representation_nli": split["representation"],
                "domain_nli": split["domain"],
                "capability_nli": split["capability"],
                "combined_nli": combined_nli,
            }
            self._nli_cache[normalized_turn_text] = nli_bundle
        stage_times["nli_ms"] = round((time.perf_counter() - stage) * 1000.0, 3)

        dialogue_nli = nli_bundle["dialogue_nli"]
        representation_nli = nli_bundle["representation_nli"]
        domain_nli = nli_bundle["domain_nli"]
        capability_nli = nli_bundle["capability_nli"]

        stage = time.perf_counter()
        embedding_map = self.embedding.similarities(
            text,
            [v for v in (previous_assistant, active_topic, active_goal) if v],
        )
        stage_times["embedding_ms"] = round((time.perf_counter() - stage) * 1000.0, 3)

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        _QUANTUM_RUNTIME_METRICS["measurements"] += 1
        _QUANTUM_RUNTIME_METRICS["last_elapsed_ms"] = round(elapsed_ms, 3)
        _QUANTUM_RUNTIME_METRICS["last_stage_ms"] = dict(stage_times)

        result = {
            "linguistic": linguistic,
            "dialogue_nli": dialogue_nli,
            "representation_nli": representation_nli,
            "domain_nli": domain_nli,
            "capability_nli": capability_nli,
            "embeddings": {
                "previous_assistant": embedding_map.get(previous_assistant, 0.0),
                "active_topic": embedding_map.get(active_topic, 0.0),
                "active_goal": embedding_map.get(active_goal, 0.0),
            },
            "nli_metadata": nli_metadata,
            "timing": {
                "elapsed_ms": round(elapsed_ms, 3),
                "stages": stage_times,
            },
            "decision_owner": "QUANTUM_PROCESSOR",
            "evidence_only": True,
            "engine": "quantum_interpretation_turn_engine_v2",
        }
        self._turn_cache[key] = result
        if len(self._turn_cache) > self._cache_limit:
            self._turn_cache.pop(next(iter(self._turn_cache)))
        return result

    def dialogue(
        self,
        text: str,
        previous_assistant: str = "",
        previous_user: str = "",
        active_goal: str = "",
        active_topic: str = "",
    ) -> Dict[str, Any]:
        turn = self.turn_measurement(text, previous_assistant, previous_user, active_goal, active_topic)
        label, confidence = self._best_label(turn["dialogue_nli"])
        return {
            "dialogue": {
                "label": label,
                "confidence": confidence,
                "continuation_score": turn["embeddings"]["previous_assistant"],
                "reference_score": turn["embeddings"]["previous_assistant"],
                "topic_score": turn["embeddings"]["active_topic"],
                "goal_score": turn["embeddings"]["active_goal"],
            },
            "linguistic": turn["linguistic"],
            "nli": turn["dialogue_nli"],
            "previous_similarity": {"score": turn["embeddings"]["previous_assistant"], "source": "sentence_transformers"},
            "topic_similarity": {"score": turn["embeddings"]["active_topic"], "source": "sentence_transformers"},
            "goal_similarity": {"score": turn["embeddings"]["active_goal"], "source": "sentence_transformers"},
            "decision_owner": "QUANTUM_PROCESSOR",
            "evidence_only": True,
            "engine": "quantum_dialogue_engine",
        }

    def representations(self, text: str, context: str = "") -> Dict[str, Any]:
        turn = self.turn_measurement(text, active_topic=context)
        nli = turn["representation_nli"]
        reverse_map = {value: key for key, value in REPRESENTATION_HYPOTHESES.items()}
        measurements = [
            {"type": reverse_map[label], "score": float(score), "source": "transformers_nli"}
            for label, score in zip(nli["labels"], nli["scores"])
            if label in reverse_map
        ]
        return {
            "nli": nli,
            "measurements": measurements,
            "context_similarity": {"score": turn["embeddings"]["active_topic"], "source": "sentence_transformers"},
            "decision_owner": "QUANTUM_PROCESSOR",
            "evidence_only": True,
            "engine": "quantum_representation_engine",
        }

    def domains(self, text: str) -> Dict[str, Any]:
        turn = self.turn_measurement(text)
        nli = turn["domain_nli"]
        reverse_map = {value: key for key, value in DOMAIN_HYPOTHESES.items()}
        measurements = [
            {"domain": reverse_map[label], "score": float(score), "source": "transformers_nli"}
            for label, score in zip(nli["labels"], nli["scores"])
            if label in reverse_map
        ]
        return {
            "nli": nli,
            "measurements": measurements,
            "decision_owner": "QUANTUM_PROCESSOR",
            "evidence_only": True,
            "engine": "quantum_domain_engine",
        }



QUANTUM_LINGUISTIC_ENGINE = QuantumLinguisticEngine()
QUANTUM_EMBEDDING_ENGINE = QuantumEmbeddingEngine()
QUANTUM_INTENT_ENGINE = QuantumIntentEngine()
QUANTUM_EVIDENCE_FUSION = QuantumEvidenceFusionEngine()


def normalize_text(text: Any) -> str:
    return str(text or "").strip()


def normalize_lower(text: Any) -> str:
    return normalize_text(text).lower()


def contains_any(text: str, words: Sequence[str]) -> bool:
    """
    Compatibility evidence helper.

    This is token/lemma evidence only. It cannot select a route or renderer.
    """
    analysis = QUANTUM_EVIDENCE_FUSION.turn_measurement(text)["linguistic"]
    wanted = {normalize_lower(word) for word in words}
    return bool(
        set(analysis["lemmas"]) & wanted
        or {normalize_lower(word) for word in analysis["tokens"]} & wanted
    )


def _semantic_evidence_stub(kind: str, text: str) -> bool:
    return contains_any(text, (kind,))


def detect_domain_candidates(text: str):
    measurements = QUANTUM_EVIDENCE_FUSION.domains(text).get("measurements", [])
    return [
        item["domain"]
        for item in measurements
        if float(item["score"]) >= 0.45
    ]


def build_domain_confidence(text: str):
    measurements = QUANTUM_EVIDENCE_FUSION.domains(text).get("measurements", [])
    return {
        item["domain"]: round(float(item["score"]), 4)
        for item in measurements
        if float(item["score"]) >= 0.20
    }


def _capability_scores(text: str) -> Dict[str, float]:
    turn = QUANTUM_EVIDENCE_FUSION.turn_measurement(text)
    reverse_map = {value: key for key, value in CAPABILITY_HYPOTHESES.items()}
    nli = turn["capability_nli"]
    return {
        reverse_map[label]: float(score)
        for label, score in zip(nli["labels"], nli["scores"])
        if label in reverse_map
    }



def measure_representation_evidence(text: str) -> List[Dict[str, Any]]:
    result = QUANTUM_EVIDENCE_FUSION.representations(text)
    return [
        SemanticEvidence(
            label=item["type"],
            score=item["score"],
            source=item["source"],
            details={
                "decision_owner": "QUANTUM_PROCESSOR",
                "evidence_only": True,
                "context_similarity": result["context_similarity"]["score"],
            },
        ).as_dict()
        for item in result["measurements"]
    ]


def detect_representation_candidates(text: str):
    return [
        item["label"]
        for item in measure_representation_evidence(text)
        if float(item["score"]) >= 0.45
    ]


def semantic_evidence_math(text: str) -> float:
    scores = {
        item["label"]: float(item["score"])
        for item in measure_representation_evidence(text)
    }
    return scores.get("formula", 0.0)


def semantic_evidence_renderer(text: str) -> float:
    measurements = measure_representation_evidence(text)
    return max((float(item["score"]) for item in measurements), default=0.0)


def semantic_evidence_image(text: str) -> float:
    scores = {
        item["label"]: float(item["score"])
        for item in measure_representation_evidence(text)
    }
    return scores.get("image", 0.0)


def semantic_evidence_exploration(text: str) -> float:
    return _capability_scores(text).get("exploration", 0.0)


def semantic_evidence_continuation(text: str, previous_assistant: str = "") -> float:
    result = QUANTUM_DIALOGUE_ENGINE.classify(
        text=text,
        previous_assistant=previous_assistant,
    )
    return float(result.get("dialogue", {}).get("continuation_score", 0.0))


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
    scores = {
        item["label"]: float(item["score"])
        for item in measure_representation_evidence(text)
    }
    return max(
        scores.get("image", 0.0),
        scores.get("diagram", 0.0),
        scores.get("graph", 0.0),
    )


def detect_scene_type(text: str, cognition=None):
    cognition = cognition if isinstance(cognition, dict) else {}
    required = [str(x).lower() for x in cognition.get("required_representations", ()) or ()]
    if required:
        return required[0]
    candidates = detect_representation_candidates(text)
    return candidates[0] if candidates else None


def _dialogue_signal_contract(
    text: str,
    history: list,
    state: dict,
    semantic: dict,
    cognition: dict | None = None,
) -> Dict[str, Any]:
    last_assistant = ""
    last_user = ""
    last_turn_id = None
    for item in reversed(history):
        if not isinstance(item, dict):
            continue
        if not last_assistant and isinstance(item.get("april"), dict):
            last_assistant = normalize_text(
                item["april"].get("answer")
                or item["april"].get("content")
                or item["april"].get("summary")
            )
            last_turn_id = item.get("turn_id")
        if not last_user and item.get("user"):
            last_user = normalize_text(item.get("user"))
        if last_assistant:
            break

    cognition = cognition if isinstance(cognition, dict) else {}

    active_goal = normalize_text(
        state.get("active_goal")
        or state.get("current_goal")
        or semantic.get("active_goal")
        or cognition.get("active_goal")
        or cognition.get("current_goal")
    )
    active_topic = normalize_text(
        state.get("active_topic")
        or state.get("current_topic")
        or semantic.get("current_topic")
        or cognition.get("active_topic")
        or cognition.get("current_topic")
    )

    measured = QUANTUM_EVIDENCE_FUSION.dialogue(
        text=text,
        previous_assistant=last_assistant,
        previous_user=last_user,
        active_goal=active_goal,
        active_topic=active_topic,
    )
    dialogue = measured["dialogue"]
    label = str(dialogue["label"])
    previous_score = float(dialogue["continuation_score"])
    reference_score = float(dialogue["reference_score"])
    topic_score = float(dialogue["topic_score"])
    goal_score = float(dialogue["goal_score"])

    continuation = bool(
        last_assistant
        and (
            label in {
                "continuation",
                "reformulation",
                "correction",
                "reference",
                "affirmation",
                "rejection",
            }
            or previous_score >= 0.72
        )
    )

    topic_shift = bool(
        active_topic and not continuation and topic_score < 0.35
    )

    return {
        "dialog_act": label,
        "current_request": text,
        "continuation": continuation,
        "reference_to_previous": bool(last_assistant and reference_score >= 0.60),
        "previous_april_turn": last_assistant,
        "previous_user_turn": last_user,
        "reply_to": last_turn_id,
        "active_goal": active_goal,
        "active_topic": active_topic,
        "topic_score": topic_score,
        "goal_score": goal_score,
        "continuation_score": previous_score,
        "reference_score": reference_score,
        "topic_shift": topic_shift,
        "history_available": bool(history),
        "turn_count": len(history),
        "semantic_measurement": measured,
        "confidence": float(dialogue["confidence"]),
        "decision_owner": "QUANTUM_PROCESSOR",
        "evidence_only": True,
        "canonical": True,
    }


def semantic_packet_score(dialogue_result: Dict[str, Any], key: str) -> float:
    embeddings = dialogue_result.get("semantic_measurement", {}).get("embeddings", {})
    return float(embeddings.get(key, 0.0) or 0.0)


def _semantic_context_packet(
    text: str,
    history: list,
    state: dict,
    semantic: dict,
    cognition: dict,
) -> Dict[str, Any]:
    dialogue = _dialogue_signal_contract(text, history, state, semantic)

    previous_answer = dialogue["previous_april_turn"]
    active_topic = dialogue["active_topic"]
    active_goal = dialogue["active_goal"]

    representation = QUANTUM_EVIDENCE_FUSION.representations(
        text,
        context=previous_answer or active_topic,
    )

    linguistic = QUANTUM_EVIDENCE_FUSION.turn_measurement(
        text=text,
        previous_assistant=previous_answer,
        active_topic=active_topic,
        active_goal=active_goal,
    )["linguistic"]

    return {
        "linguistic": linguistic,
        "dialogue": dialogue,
        "representation": representation,
        "domain": QUANTUM_EVIDENCE_FUSION.domains(text),
        "context_vectors": {
            "previous_answer": {
                "score": float(semantic_packet_score(dialogue, "previous_assistant")),
                "source": "sentence_transformers",
                "measured": bool(previous_answer),
            },
            "active_topic": {
                "score": float(semantic_packet_score(dialogue, "active_topic")),
                "source": "sentence_transformers",
                "measured": bool(active_topic),
            },
            "active_goal": {
                "score": float(semantic_packet_score(dialogue, "active_goal")),
                "source": "sentence_transformers",
                "measured": bool(active_goal),
            },
        },
        "decision_owner": "QUANTUM_PROCESSOR",
        "engine": "quantum_interpretation_engine",
        "evidence_only": True,
    }


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
    return semantic_evidence_information(text) >= 0.60


def detect_analysis_content(text):
    return semantic_evidence_exploration(text) >= 0.60


def detect_legend_content(text):
    representation = {
        item["label"]: float(item["score"])
        for item in measure_representation_evidence(text)
    }
    return max(
        representation.get("graph", 0.0),
        representation.get("table", 0.0),
        representation.get("diagram", 0.0),
    ) >= 0.60


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
# Quantum dialogue understanding engine

class QuantumDialogueEngine:
    """Real semantic dialogue understanding: NLP + vectors + NLI + context."""

    def classify(
        self,
        text: str,
        previous_assistant: str = "",
        previous_user: str = "",
        active_goal: str = "",
        active_topic: str = "",
    ) -> Dict[str, Any]:
        evidence = QUANTUM_EVIDENCE_FUSION.dialogue(
            text, previous_assistant, active_goal, active_topic
        )
        dialog = evidence["dialogue"]
        continuation = bool(
            previous_assistant and (
                dialog["label"] in {
                    "continuation", "reformulation", "correction",
                    "reference", "affirmation", "rejection",
                } or dialog["continuation_score"] >= 0.72
            )
        )
        return {
            **evidence,
            "dialog_act": dialog["label"],
            "confidence": float(dialog["confidence"]),
            "continuation": continuation,
            "reference_to_previous": bool(
                previous_assistant and dialog["reference_score"] >= 0.60
            ),
            "representation_decision": None,
            "decision_owner": "QUANTUM_PROCESSOR",
            "evidence_only": True,
        }


QUANTUM_DIALOGUE_ENGINE = QuantumDialogueEngine()

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

    previous_assistant = last_assistant[1] if last_assistant else ""
    active_goal = (
        state.get("active_goal") or state.get("current_goal") or
        (state.get("goal_hierarchy") or {}).get("active_goal") or
        semantic.get("active_goal") or semantic.get("goal") or ""
    )
    active_topic = (
        state.get("active_topic") or state.get("current_topic") or state.get("topic") or
        semantic.get("current_topic") or semantic.get("topic") or ""
    )

    measured = QUANTUM_DIALOGUE_ENGINE.classify(
        text=text,
        previous_assistant=previous_assistant,
        previous_user=last_user[1] if last_user else "",
        active_goal=active_goal,
        active_topic=active_topic,
    )

    reply_to = (
        last_assistant[2].get("turn_id")
        if last_assistant and isinstance(last_assistant[2], dict)
        else None
    )

    continuation = bool(measured.get("continuation"))
    dialog_act = measured.get("dialog_act") or "statement"

    if continuation and previous_assistant:
        resolved_request = (
            f"Continue the previous task naturally. "
            f"Previous assistant response: {previous_assistant}\n"
            f"Current user instruction: {text}"
        )
    else:
        resolved_request = text

    capabilities = []
    capability_measurement = (
        measured.get("semantic_measurement", {}).get("capability_nli", {})
        if isinstance(measured.get("semantic_measurement"), dict)
        else {}
    )
    capability_labels = capability_measurement.get("labels") or []
    capability_scores = capability_measurement.get("scores") or []
    capability_map = {
        label: float(score)
        for label, score in zip(capability_labels, capability_scores)
    }
    representation_signal = semantic.get("candidate_representations") or []
    if representation_signal:
        capabilities.append("structured_rendering")
    if capability_map and max(capability_map.get(label, 0.0) for label in capability_map) >= 0.60:
        if capability_map.get(CAPABILITY_HYPOTHESES["exploration"], 0.0) >= 0.60:
            capabilities.append("analysis")
    if measured.get("reference_to_previous"):
        capabilities.append("dialogue_continuity")

    return {
        "dialog_act": dialog_act,
        "current_request": text,
        "resolved_request": resolved_request,
        "continuation": continuation,
        "reply_to": reply_to,
        "previous_april_turn": previous_assistant,
        "previous_user_turn": last_user[1] if last_user else "",
        "active_goal": active_goal,
        "active_topic": active_topic,
        "topic_shift": bool(
            active_topic and
            not measured.get("reference_to_previous") and
            measured.get("topic_similarity", {}).get("score", 0.0) < 0.35
        ),
        "required_capabilities": list(dict.fromkeys(capabilities)),
        "confidence": float(measured.get("confidence", 0.0)),
        "history_available": bool(turns),
        "turn_count": len(turns),
        "semantic_measurement": measured,
        "canonical": True,
        "version": "dialogue_v4_quantum_semantic_fusion",
    }


def _base_interpret_request(text, cognition=None, semantic=None, history=None, state=None):
    text = normalize_text(text)
    if not text:
        return None

    cognition = cognition if isinstance(cognition, dict) else {}
    semantic = semantic if isinstance(semantic, dict) else {}
    history = history if isinstance(history, list) else []
    state = state if isinstance(state, dict) else {}

    result = build_result(text)

    semantic_packet = _semantic_context_packet(
        text=text,
        history=history,
        state=state,
        semantic=semantic,
        cognition=cognition,
    )

    domains = [
        item["domain"]
        for item in semantic_packet["domain"].get("measurements", [])
        if float(item["score"]) >= 0.45
    ]
    representation_evidence = [
        item for item in measure_representation_evidence(text)
    ]
    semantic_candidates = [
        item["label"]
        for item in representation_evidence
        if float(item["score"]) >= 0.45
    ]

    explicit_required = [
        str(x).lower()
        for x in (
            (semantic.get("required_representations", []) or [])
            + (cognition.get("required_representations", []) or [])
        )
        if str(x).strip()
    ]

    result["semantic_profile"] = build_semantic_dialog_profile(
        text,
        cognition,
        semantic,
        dialogue_history=history,
    )
    result["scene_profile"] = build_scene_construction_profile(result["semantic_profile"])
    result["artifact_contract"] = build_scene_artifact_contract(
        result["semantic_profile"],
        result["scene_profile"],
    )

    result["candidate_domains"] = domains
    result["required_domains"] = list(
        semantic.get("required_domains", []) or domains
    )
    result["domain_confidence"] = build_domain_confidence(text)
    result["candidate_representations"] = semantic_candidates
    result["representation_evidence"] = representation_evidence
    result["required_representations"] = explicit_required
    result["scene_type"] = explicit_required[0] if explicit_required else None

    result["discussion_mode"] = detect_discussion_mode(text)
    result["space_discussion"] = detect_space_discussion(text)
    result["exploration"] = semantic_evidence_exploration(text)
    result["continuation"] = float(
        semantic_packet["dialogue"].get("continuation_score", 0.0)
    )
    result["web_context"] = semantic_evidence_web(text)
    result["explicit_image_generation"] = semantic_evidence_image(text)
    result["lightweight_visual"] = detect_lightweight_visual(text)

    result["contains_object"] = bool(text)
    result["contains_explanation"] = semantic_evidence_information(text) >= 0.60
    result["contains_analysis"] = result["exploration"] >= 0.60
    result["contains_legend"] = False
    if result["contains_explanation"]:
        result["content_role"] = "explanation"
    elif result["contains_analysis"]:
        result["content_role"] = "analysis"

    result["evidence"] = {
        "domain": semantic_packet["domain"],
        "representation": representation_evidence,
        "math": semantic_evidence_math(text),
        "code": semantic_evidence_code(text),
        "web": result["web_context"],
        "image": result["explicit_image_generation"],
        "continuation": result["continuation"],
        "exploration": result["exploration"],
        "information": semantic_evidence_information(text),
        "linguistic": semantic_packet["linguistic"],
        "dialogue": semantic_packet["dialogue"],
        "context_vectors": semantic_packet["context_vectors"],
        "cognition": dict(cognition),
        "semantic": dict(semantic),
    }

    result["quantum_interpretation_field"] = semantic_packet
    result["quantum_representation_measurement"] = semantic_packet.get("representation", {})
    result["factory_order"] = build_factory_order(result)
    result["scene_strategy"] = build_scene_strategy(result)
    result["estimated_action_count"] = estimate_action_count(result)
    result["response_complexity"] = determine_response_complexity(result)

    # Interpretation only emits evidence. Quantum Processor decides.
    result["semantic_authority"] = True
    result["decision_source"] = "QUANTUM_PROCESSOR"
    result["semantic_decision_source"] = "quantum_evidence_fusion"
    result["representation_resolution"] = "processor_selection"
    result["legacy_keyword_matching"] = False
    result["avoid_trigger_execution"] = True
    result["factory_order"]["status"] = "evidence_only"

    return result


def _interpretation_cache_signature(
    text: str,
    cognition: Any,
    semantic: Any,
    history: Any,
    state: Any,
) -> tuple:
    history = history if isinstance(history, list) else []
    state = state if isinstance(state, dict) else {}
    semantic = semantic if isinstance(semantic, dict) else {}
    cognition = cognition if isinstance(cognition, dict) else {}

    last_assistant = ""
    last_user = ""
    for item in reversed(history[-8:]):
        if not isinstance(item, dict):
            continue
        if not last_assistant and isinstance(item.get("april"), dict):
            last_assistant = normalize_text(
                item["april"].get("answer")
                or item["april"].get("content")
                or item["april"].get("summary")
            )
        if not last_user and item.get("user"):
            last_user = normalize_text(item.get("user"))
        if last_assistant and last_user:
            break

    context_fields = (
        state.get("active_goal"),
        state.get("current_goal"),
        state.get("active_topic"),
        state.get("current_topic"),
        semantic.get("active_goal"),
        semantic.get("current_topic"),
        cognition.get("active_goal"),
        cognition.get("active_topic"),
    )
    return (
        normalize_text(text),
        last_assistant,
        last_user,
        *tuple(normalize_text(value) for value in context_fields),
    )


def _remember_interpretation(signature: tuple, result: Dict[str, Any]) -> None:
    _QUANTUM_MEASUREMENT_CACHE[signature] = result
    if len(_QUANTUM_MEASUREMENT_CACHE) > _QUANTUM_MEASUREMENT_CACHE_LIMIT:
        _QUANTUM_MEASUREMENT_CACHE.pop(next(iter(_QUANTUM_MEASUREMENT_CACHE)))


def interpret_request(text, cognition=None, semantic=None, history=None, state=None):
    started = time.perf_counter()
    signature = _interpretation_cache_signature(
        text, cognition, semantic, history, state
    )
    cached = _QUANTUM_MEASUREMENT_CACHE.get(signature)
    if cached is not None:
        _QUANTUM_RUNTIME_METRICS["cache_hits"] += 1
        cached_copy = dict(cached)
        diagnostics = dict(cached_copy.get("semantic_engine_diagnostics", {}))
        diagnostics["cache_hit"] = True
        diagnostics["cache_signature"] = hashlib.sha1(
            repr(signature).encode("utf-8")
        ).hexdigest()[:16]
        diagnostics["last_call_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
        cached_copy["semantic_engine_diagnostics"] = diagnostics
        return cached_copy

    result = _base_interpret_request(
        text,
        cognition=cognition,
        semantic=semantic,
        history=history,
        state=state,
    )
    if result is None:
        return None

    contract = _dialogue_signal_contract(
        text,
        history or [],
        state or {},
        result,
        cognition or {},
    )

    # Canonical public measurements for every downstream consumer.
    result["dialogue_contract"] = contract
    result["quantum_dialogue_measurement"] = _quantum_snapshot(
        contract.get("semantic_measurement", {})
    )
    result["quantum_representation_measurement"] = _quantum_snapshot(
        result.get("quantum_representation_measurement", {})
    )
    result["quantum_representation_candidates"] = _quantum_snapshot(
        result.get("candidate_representations", [])
    )

    result["dialog_act"] = contract["dialog_act"]
    result["continuation"] = bool(contract["continuation"])
    result["continuation_target"] = (
        contract["previous_april_turn"]
        or contract["active_topic"]
    )
    result["active_goal"] = contract["active_goal"]
    result["active_topic"] = contract["active_topic"]
    result["resolved_request"] = (
        text
        if not contract["continuation"]
        else (
            "Continue the previous task naturally.\n"
            f"Previous assistant response: {contract['previous_april_turn']}\n"
            f"Current user instruction: {text}"
        )
    )
    result["reply_to"] = contract["reply_to"]
    result["required_capabilities"] = [
        "semantic_interpretation",
        "dialogue_context",
    ]
    if result.get("candidate_representations"):
        result["required_capabilities"].append("representation_evidence")

    result["dialogue_understanding"] = contract
    result["context_dependency"] = (
        "continuation" if contract.get("continuation")
        else "reference" if contract.get("reference_to_previous")
        else "new_topic" if contract.get("topic_shift")
        else "independent"
    )
    result["context_policy"] = {
        "current_request": True,
        "dialogue_vector": bool(
            contract.get("continuation")
            or contract.get("reference_to_previous")
        ),
        "previous_turn": bool(contract.get("reply_to")),
        "active_goal": bool(contract.get("active_goal")),
        "full_history": True,
        "semantic_similarity": True,
        "nli_intent": True,
        "linguistic_structure": True,
    }

    result["canonical_transport"] = "transport_state"
    result["decision_owner"] = "QUANTUM_PROCESSOR"
    result["routing_owner"] = "QUANTUM_PROCESSOR"
    result["renderer_owner"] = "QUANTUM_PROCESSOR"
    result["provider_calls"] = 0
    result["avoid_trigger_execution"] = True
    result["unresolved_intent"] = False

    result = validate_response_complexity(result)
    state_out = build_interpretation_state()
    state_out = synchronize_interpretation_context(state_out, result)
    state_out = export_transport_state(state_out, result)
    result["transport_state"] = state_out
    result["primary_contract"] = "transport_state"

    runtime_metrics = dict(_QUANTUM_RUNTIME_METRICS)
    runtime_metrics["interpret_request_elapsed_ms"] = round(
        (time.perf_counter() - started) * 1000.0, 3
    )
    result["semantic_engine_diagnostics"] = {
        "engines": [
            "stanza_multilingual_linguistic",
            "spacy_ner",
            "sentence_transformers_embedding",
            "transformers_nli_refinement",
            "quantum_evidence_fusion",
        ],
        "engine_mode": "required",
        "stanza_bootstrap_languages": list(STANZA_BOOTSTRAP_LANGS),
        "stanza_prewarm_languages": list(STANZA_PREWARM_LANGS),
        "fallback_mode": False,
        "substring_routing": False,
        "candidate_to_required_promotion": False,
        "renderer_selection_owner": "QUANTUM_PROCESSOR",
        "single_route": True,
        "cache_hit": False,
        "measurement_version": "quantum_measurement_v2",
        "runtime_metrics": runtime_metrics,
    }
    result["interpretation_state"] = state_out
    result["transport_diagnostics"] = build_transport_diagnostics(result)
    result = propagate_canonical_response(result, state_out)
    result = bridge_machine_response(result, state_out)

    result["quantum_measurement"] = {
        "version": "quantum_measurement_v2",
        "current_request": text,
        "evidence": _quantum_snapshot(result.get("quantum_interpretation_field", {})),
        "dialogue": _quantum_snapshot(result.get("quantum_dialogue_measurement", {})),
        "representation": _quantum_snapshot(result.get("quantum_representation_measurement", {})),
        "context_dependency": result.get("context_dependency"),
        "timing": _quantum_snapshot(
            result.get("quantum_dialogue_measurement", {}).get("timing", {})
            if isinstance(result.get("quantum_dialogue_measurement"), dict)
            else {}
        ),
        "decision_owner": "QUANTUM_PROCESSOR",
        "evidence_only": True,
    }

    _remember_interpretation(signature, result)
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
        "profile_version": "quantum_interpretation_engine_v3",
    }


def build_scene_construction_profile(semantic_profile):
    return {
        "requires_scene_builder": False,
        "scene_type": "dialogue",
        "dialogue_mode": "semantic_unified",
        "context_source": "evidence_packet",
        "decision_owner": "QUANTUM_PROCESSOR",
        "profile_version": "quantum_interpretation_engine_v3",
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
        "profile_version": "quantum_interpretation_engine_v3",
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
        "profile_version": "quantum_interpretation_engine_v3",
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
        "profile_version": "quantum_interpretation_engine_v3",
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
        "profile_version": "quantum_interpretation_engine_v3",
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
        "profile_version": "quantum_interpretation_engine_v3",
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
        "profile_version": "quantum_interpretation_engine_v3",
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
        "profile_version": "quantum_interpretation_engine_v3",
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
        "profile_version": "quantum_interpretation_engine_v3",
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
        "profile_version": "quantum_interpretation_engine_v3",
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
        "profile_version": "quantum_interpretation_engine_v3",
    }


def build_processor_execution_context(runtime_state):
    fused = fuse_semantic_inputs(runtime_state or {})
    return {
        "transport": "transport_state",
        "semantic_context": fused,
        "executor_context": fused,
        "processor_context": fused,
        "decision_owner": "QUANTUM_PROCESSOR",
        "profile_version": "quantum_interpretation_engine_v3",
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


# ---------------------------------------------------------------------------
# Runtime diagnostics / canonical engine access
# ---------------------------------------------------------------------------

def get_quantum_interpretation_runtime_metrics() -> Dict[str, Any]:
    return {
        "runtime_ready": bool(_SEMANTIC_RUNTIME_READY),
        "accelerator_started": bool(_SEMANTIC_ACCELERATOR_STARTED),
        "accelerator_error": (
            f"{type(_SEMANTIC_ACCELERATOR_ERROR).__name__}: {_SEMANTIC_ACCELERATOR_ERROR}"
            if _SEMANTIC_ACCELERATOR_ERROR else None
        ),
        "measurements": int(_QUANTUM_RUNTIME_METRICS.get("measurements", 0)),
        "cache_hits": int(_QUANTUM_RUNTIME_METRICS.get("cache_hits", 0)),
        "nli_refinements": int(_QUANTUM_RUNTIME_METRICS.get("nli_refinements", 0)),
        "nli_full_passes": int(_QUANTUM_RUNTIME_METRICS.get("nli_full_passes", 0)),
        "last_elapsed_ms": float(_QUANTUM_RUNTIME_METRICS.get("last_elapsed_ms", 0.0)),
        "last_stage_ms": dict(_QUANTUM_RUNTIME_METRICS.get("last_stage_ms", {})),
        "measurement_cache_size": len(_QUANTUM_MEASUREMENT_CACHE),
        "turn_cache_size": len(QUANTUM_EVIDENCE_FUSION._turn_cache),
        "nli_cache_size": len(QUANTUM_EVIDENCE_FUSION._nli_cache),
        "hypothesis_index_ready": bool(_QUANTUM_HYPOTHESIS_INDEX_READY),
    }


def clear_quantum_interpretation_caches() -> None:
    _QUANTUM_MEASUREMENT_CACHE.clear()
    QUANTUM_EVIDENCE_FUSION._turn_cache.clear()
    QUANTUM_EVIDENCE_FUSION._linguistic_cache.clear()
    QUANTUM_EVIDENCE_FUSION._nli_cache.clear()
    QUANTUM_EVIDENCE_FUSION.embedding._pair_cache.clear()
    QUANTUM_EVIDENCE_FUSION.embedding._batch_cache.clear()
    QUANTUM_EVIDENCE_FUSION._cache_limit = 96
