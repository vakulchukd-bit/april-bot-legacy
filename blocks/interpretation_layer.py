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
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------------------------------------------------------------
# Canonical semantic vocabulary
# ---------------------------------------------------------------------------


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

# Production hot-path policy:
# Free/simple turns use a local TF-IDF semantic sketch (no model download,
# no Stanza, no sentence-transformer inference, no NLI). Heavy semantic models
# remain available behind an explicit opt-in for future higher tiers/diagnostics.
APRIL_FAST_SEMANTIC_MODE = (
    str(os.getenv("APRIL_FAST_SEMANTIC_MODE", "1")).strip().lower()
    in {"1", "true", "yes", "on"}
)
APRIL_ENABLE_HEAVY_HOTPATH = (
    str(os.getenv("APRIL_ENABLE_HEAVY_HOTPATH", "0")).strip().lower()
    in {"1", "true", "yes", "on"}
)


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
    for lang in os.getenv("APRIL_STANZA_LANGS", "ru,en,uk").split(",")
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
_STANZA_BOOTSTRAP_ATTEMPTED = False
_SEMANTIC_RUNTIME_LOCK = threading.RLock()
_SEMANTIC_ACCELERATOR_STARTED = False
_SEMANTIC_ACCELERATOR_ERROR: Exception | None = None


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


def _ensure_semantic_runtime() -> None:
    global SPACY_NLP, STANZA_NLP, SEMANTIC_ENCODER, DIALOGUE_NLI, _SEMANTIC_RUNTIME_READY
    if _SEMANTIC_RUNTIME_READY:
        return

    with _SEMANTIC_RUNTIME_LOCK:
        if _SEMANTIC_RUNTIME_READY:
            return

        started = time.perf_counter()
        try:
            if APRIL_FAST_SEMANTIC_MODE and not APRIL_ENABLE_HEAVY_HOTPATH:
                # The local semantic sketch is already initialized at import
                # time and is the normal production hot path.
                SPACY_NLP = None
                STANZA_NLP = None
                SEMANTIC_ENCODER = None
                DIALOGUE_NLI = None
                _SEMANTIC_RUNTIME_READY = True
                os.environ["APRIL_STANZA_RUNTIME_READY"] = "0"
                elapsed = time.perf_counter() - started
                print(
                    f"⚡ SEMANTIC ACCELERATOR READY: fast_local=1 elapsed={elapsed:.4f}s",
                    flush=True,
                )
                return
            deep_enabled = (
                str(os.getenv("APRIL_DEEP_LINGUISTICS", "0")).strip().lower() in {"1", "true", "yes", "on"}
                and str(os.getenv("APRIL_ALLOW_DEEP_LINGUISTICS", "0")).strip().lower() in {"1", "true", "yes", "on"}
            )
            if deep_enabled:
                SPACY_NLP = spacy.load(SPACY_MODEL_NAME)
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
            else:
                SPACY_NLP = None
                STANZA_NLP = None

            SEMANTIC_ENCODER = SentenceTransformer(SEMANTIC_MODEL_NAME)
            # Prewarm static semantic prototypes when module declarations are
            # already available. A late first-turn guard covers import races.
            embedding_engine = globals().get("QUANTUM_EMBEDDING_ENGINE")
            proto_turns = globals().get("SEMANTIC_TURN_PROTOTYPES")
            proto_reps = globals().get("REPRESENTATION_HYPOTHESES")
            proto_domains = globals().get("DOMAIN_HYPOTHESES")
            proto_caps = globals().get("CAPABILITY_HYPOTHESES")
            if embedding_engine is not None and all(
                isinstance(value, dict) for value in (proto_turns, proto_reps, proto_domains, proto_caps)
            ):
                embedding_engine.prewarm_static([
                    *proto_turns.values(),
                    *proto_reps.values(),
                    *proto_domains.values(),
                    *proto_caps.values(),
                ])
            # NLI is intentionally NOT loaded during the accelerator prewarm.
            # It is a refinement engine and is loaded only when the fast
            # measurement marks a turn as genuinely ambiguous.
            DIALOGUE_NLI = None
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

APRIL_DEEP_LINGUISTICS_ENABLED = (
    str(os.getenv("APRIL_DEEP_LINGUISTICS", "0")).strip().lower() in {"1", "true", "yes", "on"}
    and str(os.getenv("APRIL_ALLOW_DEEP_LINGUISTICS", "0")).strip().lower() in {"1", "true", "yes", "on"}
)

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

# Semantic prototypes are evidence, not triggers. They are compared by the
# shared embedding engine and cached, so wording can vary without adding
# phrase lists to the routing layer.
SEMANTIC_TURN_PROTOTYPES = {
    "identity": (
        "The user is asking who the assistant is, what it is called, what role it has, "
        "or what capabilities it provides."
    ),
    "greeting": (
        "The user is opening a casual conversation with the assistant or greeting it."
    ),
    "continuation": (
        "The user wants to continue or extend the immediately preceding discussion."
    ),
    "reference": (
        "The user is referring back to something previously discussed or previously produced."
    ),
    "independent": (
        "The user is asking a self-contained request that can be answered without previous turns."
    ),
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


class QuantumFastSemanticEngine:
    """CPU-light semantic sketch used by the production hot path.

    It is NOT keyword routing and contains no phrase triggers. A fixed set of
    semantic prototype statements is vectorized once, then the current request
    is compared by character n-gram TF-IDF cosine similarity. This keeps the
    interpretation layer deterministic and sub-second on ordinary CPU-only
    deployments while preserving the existing evidence/processor ownership.
    """

    def __init__(self) -> None:
        self.char_vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            lowercase=True,
            sublinear_tf=True,
        )
        self.word_vectorizer = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            lowercase=True,
            sublinear_tf=True,
        )
        self.dialogue = {
            "identity": [
                "пользователь спрашивает кто такой помощник, как его зовут, какую роль он выполняет и что он умеет",
                "пользователь хочет узнать имя ассистента и его возможности",
                "the user asks who the assistant is, its name, role, or capabilities",
            ],
            "greeting": [
                "пользователь приветствует ассистента и начинает разговор",
                "пользователь открывает непринужденный диалог с помощником",
                "the user is greeting the assistant or opening a casual conversation",
            ],
            "continuation": [
                "пользователь хочет продолжить предыдущую тему или развить предыдущий ответ",
                "пользователь просит вернуться к обсуждению и продолжить его",
                "the user wants to continue or extend the preceding discussion",
            ],
            "reference": [
                "пользователь ссылается на то что уже было обсуждено или создано",
                "пользователь просит использовать ранее сказанное или предыдущий результат",
                "the user refers to something previously discussed or produced",
            ],
            "independent": [
                "пользователь задает самостоятельный вопрос который не зависит от предыдущих сообщений",
                "запрос можно ответить без старого контекста",
                "the user asks a self contained request independent of earlier turns",
            ],
        }
        self.representations = {
            "text": [
                "пользователь хочет обычный текстовый ответ и объяснение",
                "пользователь просит рассказать объяснить или описать без специального формата",
                "the user wants a normal textual answer",
            ],
            "table": [
                "пользователь хочет представить информацию в виде таблицы",
                "пользователь просит структурированную таблицу критериев значений или сравнения",
                "the user wants the information represented as a table",
            ],
            "graph": [
                "пользователь хочет график диаграмму данных или визуализацию числовых значений",
                "пользователь просит построить график по данным",
                "the user wants a graph or chart",
            ],
            "diagram": [
                "пользователь хочет схему диаграмму связей или блоков",
                "пользователь просит показать структуру процесса или связей",
                "the user wants a diagram or schematic",
            ],
            "formula": [
                "пользователь хочет математическую формулу уравнение или математическую запись",
                "пользователь просит показать математическое выражение",
                "the user wants a mathematical formula",
            ],
            "image": [
                "пользователь хочет изображение картинку или созданную иллюстрацию",
                "пользователь просит создать изображение",
                "the user wants an image",
            ],
            "gallery": [
                "пользователь хочет несколько изображений или галерею",
                "пользователь просит подборку изображений",
                "the user wants a gallery",
            ],
            "code": [
                "пользователь хочет исходный программный код реализацию или пример кода",
                "пользователь просит написать программу или функцию",
                "the user wants executable source code",
            ],
            "link": [
                "пользователь хочет ссылку адрес сайта или веб ресурс",
                "пользователь просит открыть или дать интернет ресурс",
                "the user wants a link or web resource",
            ],
        }
        self.domains = {
            "biology": ["запрос о биологии живых организмах клетках генетике", "biology living organisms genetics"],
            "chemistry": ["запрос о химии веществах реакциях молекулах", "chemistry substances reactions molecules"],
            "physics": ["запрос о физике энергии силе движении", "physics energy forces motion"],
            "engineering": ["запрос об инженерии конструкции проектировании", "engineering design construction"],
            "it": ["запрос о программировании компьютерах программном обеспечении", "computing programming software"],
            "literature": ["запрос о литературе писателе поэзии произведениях", "literature writing poetry authors"],
            "politics": ["запрос о политике государстве правительстве", "politics government"],
            "news": ["запрос о текущих событиях последних новостях", "current events news"],
            "social": ["запрос об обществе социальных темах", "society social topics"],
            "web": ["запрос на интернет ресурс поиск сайте", "web search online resource"],
        }
        self.capabilities = {
            "exploration": ["пользователь хочет анализ сравнение исследование", "analysis comparison investigation"],
            "web": ["пользователь хочет поиск в интернете или онлайн ресурс", "web search online resource"],
            "code": ["пользователь хочет код программную реализацию", "programming code implementation"],
            "information": ["пользователь хочет объяснение фактический ответ разъяснение", "explanation factual answer clarification"],
            "discussion": ["пользователь хочет обсуждение мнение рассуждение", "discussion opinion reasoning"],
            "space": ["пользователь обсуждает пространство сцену композицию", "spatial scene visual composition"],
        }

        docs = []
        self._families: dict[str, dict[str, list[int]]] = {}
        for family_name, family in (
            ("dialogue", self.dialogue),
            ("representation", self.representations),
            ("domain", self.domains),
            ("capability", self.capabilities),
        ):
            positions: dict[str, list[int]] = {}
            for label, variants in family.items():
                positions[label] = []
                for text in variants:
                    positions[label].append(len(docs))
                    docs.append(text)
            self._families[family_name] = positions
        self._char_matrix = self.char_vectorizer.fit_transform(docs)
        self._word_matrix = self.word_vectorizer.fit_transform(docs)
        self._cache: dict[tuple, dict[str, Any]] = {}
        self._cache_limit = 256

    @staticmethod
    def _family_scores(char_row, word_row, positions: dict[str, list[int]], labels: list[str]) -> dict[str, float]:
        scores: dict[str, float] = {}
        for label in labels:
            idxs = positions[label]
            if not idxs:
                scores[label] = 0.0
                continue
            char_score = max(float(char_row[idx]) for idx in idxs)
            word_score = max(float(word_row[idx]) for idx in idxs)
            scores[label] = max(0.0, min(1.0, 0.6 * char_score + 0.4 * word_score))
        return scores

    def measure(
        self,
        text: str,
        previous_assistant: str = "",
        active_topic: str = "",
        active_goal: str = "",
    ) -> dict[str, Any]:
        query = normalize_text(text)
        key = (
            query,
            normalize_text(previous_assistant),
            normalize_text(active_topic),
            normalize_text(active_goal),
        )
        cached = self._cache.get(key)
        if cached is not None:
            return dict(cached)

        char_query = self.char_vectorizer.transform([query])
        word_query = self.word_vectorizer.transform([query])
        char_scores_all = cosine_similarity(char_query, self._char_matrix)[0]
        word_scores_all = cosine_similarity(word_query, self._word_matrix)[0]

        dialogue_scores = self._family_scores(
            char_scores_all,
            word_scores_all,
            self._families["dialogue"],
            list(self.dialogue),
        )
        representation_scores = self._family_scores(
            char_scores_all,
            word_scores_all,
            self._families["representation"],
            list(self.representations),
        )
        domain_scores = self._family_scores(
            char_scores_all,
            word_scores_all,
            self._families["domain"],
            list(self.domains),
        )
        capability_scores = self._family_scores(
            char_scores_all,
            word_scores_all,
            self._families["capability"],
            list(self.capabilities),
        )

        dialogue_ranked = sorted(dialogue_scores.items(), key=lambda item: item[1], reverse=True)
        best_dialogue, best_dialogue_score = dialogue_ranked[0]
        dialogue_margin = (
            best_dialogue_score - dialogue_ranked[1][1]
            if len(dialogue_ranked) > 1 else best_dialogue_score
        )

        # Context similarity is calculated with the same fixed vector space;
        # historical content never becomes a routing decision by itself.
        contexts = {}
        for label, value in (
            ("previous_assistant", previous_assistant),
            ("active_topic", active_topic),
            ("active_goal", active_goal),
        ):
            value = normalize_text(value)
            if value:
                cvec = self.char_vectorizer.transform([value])
                wvec = self.word_vectorizer.transform([value])
                cscore = float(cosine_similarity(char_query, cvec)[0][0])
                wscore = float(cosine_similarity(word_query, wvec)[0][0])
                contexts[label] = 0.6 * cscore + 0.4 * wscore
            else:
                contexts[label] = 0.0

        rep_ranked = sorted(representation_scores.items(), key=lambda item: item[1], reverse=True)
        best_representation, best_rep_score = rep_ranked[0]
        rep_margin = (
            best_rep_score - rep_ranked[1][1]
            if len(rep_ranked) > 1 else best_rep_score
        )
        # Uncertain representation measurements collapse safely to text.
        if best_representation != "text" and (
            best_rep_score < 0.18 or rep_margin < 0.05
        ):
            best_representation = "text"
            best_rep_score = representation_scores.get("text", 0.0)

        identity_score = dialogue_scores.get("identity", 0.0)
        continuation_score = dialogue_scores.get("continuation", 0.0)
        reference_score = dialogue_scores.get("reference", 0.0)
        greeting_score = dialogue_scores.get("greeting", 0.0)
        independent_score = dialogue_scores.get("independent", 0.0)

        identity_request = (
            identity_score >= 0.12
            and identity_score >= continuation_score + 0.03
            and identity_score >= reference_score + 0.03
        )
        fast_social = (
            best_dialogue in {"identity", "greeting"}
            and best_dialogue_score >= 0.12
            and dialogue_margin >= 0.035
            and len(query.split()) <= 24
        )

        profile = {
            "needs_refinement": False,
            "identity_score": float(identity_score),
            "greeting_score": float(greeting_score),
            "continuation_score": float(continuation_score),
            "reference_score": float(reference_score),
            "independent_score": float(independent_score),
            "dialogue_best": best_dialogue,
            "dialogue_confidence": float(best_dialogue_score),
            "dialogue_margin": float(dialogue_margin),
            "representation_scores": representation_scores,
            "domain_scores": domain_scores,
            "capability_scores": capability_scores,
            "best_representation": best_representation,
            "best_representation_score": float(best_rep_score),
            "explicit_representations": [
                name for name, score in representation_scores.items()
                if name != "text" and float(score) >= 0.45 and float(score) - representation_scores.get("text", 0.0) >= 0.08
            ],
            "context_scores": contexts,
            "identity_request": bool(identity_request),
            "fast_social": bool(fast_social or identity_request),
            "source": "local_tfidf_semantic_sketch",
            "dialogue_nli": {
                "labels": list(DIALOGUE_LABELS),
                "scores": [dialogue_scores.get(label, 0.0) for label in DIALOGUE_LABELS],
                "source": "local_tfidf_semantic_sketch",
            },
            "representation_nli": {
                "labels": [REPRESENTATION_HYPOTHESES.get(name, name) for name in representation_scores],
                "scores": [float(representation_scores[name]) for name in representation_scores],
                "source": "local_tfidf_semantic_sketch",
            },
            "domain_nli": {
                "labels": [DOMAIN_HYPOTHESES.get(name, name) for name in domain_scores],
                "scores": [float(domain_scores[name]) for name in domain_scores],
                "source": "local_tfidf_semantic_sketch",
            },
            "capability_nli": {
                "labels": [CAPABILITY_HYPOTHESES.get(name, name) for name in capability_scores],
                "scores": [float(capability_scores[name]) for name in capability_scores],
                "source": "local_tfidf_semantic_sketch",
            },
        }
        self._cache[key] = dict(profile)
        if len(self._cache) > self._cache_limit:
            self._cache.pop(next(iter(self._cache)))
        return profile

QUANTUM_FAST_SEMANTIC = QuantumFastSemanticEngine()


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
    # Fast semantic mode does not require a heavyweight neural encoder.
    if APRIL_FAST_SEMANTIC_MODE and not APRIL_ENABLE_HEAVY_HOTPATH:
        if not _SEMANTIC_RUNTIME_READY:
            raise RuntimeError("Quantum Interpretation fast semantic runtime is not ready")
        return
    if not _SEMANTIC_RUNTIME_READY or SEMANTIC_ENCODER is None:
        raise RuntimeError("Quantum Interpretation semantic runtime is not ready")


_NLI_RUNTIME_LOCK = threading.RLock()
_NLI_RUNTIME_READY = False
_NLI_RUNTIME_ERROR: Exception | None = None

def _ensure_nli_runtime() -> None:
    """Lazy-load the expensive NLI model only for genuinely ambiguous turns."""
    global DIALOGUE_NLI, _NLI_RUNTIME_READY, _NLI_RUNTIME_ERROR
    if _NLI_RUNTIME_READY and DIALOGUE_NLI is not None:
        return
    with _NLI_RUNTIME_LOCK:
        if _NLI_RUNTIME_READY and DIALOGUE_NLI is not None:
            return
        started = time.perf_counter()
        try:
            DIALOGUE_NLI = hf_pipeline(
                "zero-shot-classification",
                model=NLI_MODEL_NAME,
            )
            _NLI_RUNTIME_READY = True
            _NLI_RUNTIME_ERROR = None
            print(f"⚡ NLI REFINEMENT READY: elapsed={time.perf_counter()-started:.3f}s")
        except Exception as exc:
            _NLI_RUNTIME_ERROR = exc
            DIALOGUE_NLI = None
            raise



def _lightweight_linguistic(text: str) -> Dict[str, Any]:
    """Zero-model linguistic pass for very short social turns."""
    value = normalize_text(text)
    tokens = re.findall(r"[A-Za-zА-Яа-яЁё0-9_]+", value)
    lemmas = [token.lower() for token in tokens]
    return {
        "language": None,
        "tokens": tokens,
        "lemmas": lemmas,
        "pos": [],
        "dependencies": [],
        "entities": [],
        "sentences": [value] if value else [],
        "source": "lightweight_micro_turn",
        "engine": "quantum_linguistic_engine",
        "runtime_bypass": True,
    }


class QuantumLinguisticEngine:
    """
    Dedicated linguistic engine.

    Stanza performs multilingual neural sentence/token processing, POS and
    lemma analysis. spaCy supplies entity analysis using the already installed
    multilingual NER model. Dependency fields are retained in the canonical
    evidence shape and remain empty when dependency parsing is not provisioned.
    """

    def analyze(self, text: str) -> Dict[str, Any]:
        normalized = normalize_text(text)
        # The production hot path is intentionally model-light. Deep Stanza
        # parsing is opt-in so a normal user turn can never wait for a lazy
        # language-package load on the request thread.
        if not APRIL_DEEP_LINGUISTICS_ENABLED:
            return _lightweight_linguistic(normalized)
        _runtime_ready_guard()
        if not normalized:
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
    """Low-latency semantic vector engine with static prototype prewarm.

    The production hot path encodes the current request once and reuses
    precomputed vectors for all static semantic prototypes. Dynamic topic/goal
    strings are encoded only when they are present.
    """

    def __init__(self):
        self._pair_cache: dict[tuple[str, str], float] = {}
        self._batch_cache: dict[tuple[str, tuple[str, ...]], Dict[str, float]] = {}
        self._query_vector_cache: dict[str, Any] = {}
        self._static_vectors: dict[str, Any] = {}
        self._cache_limit = 512

    def _remember(self, cache: dict, key, value, limit=None) -> None:
        cache[key] = value
        cap = int(limit or self._cache_limit)
        if len(cache) > cap:
            cache.pop(next(iter(cache)))

    def _remember_pair(self, key: tuple[str, str], score: float) -> None:
        self._remember(self._pair_cache, key, float(score))

    def prewarm_static(self, candidates: Sequence[str]) -> int:
        """Encode static semantic prototypes once during accelerator prewarm."""
        unique: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            value = normalize_text(candidate)
            if value and value not in seen:
                seen.add(value)
                unique.append(value)
        if not unique or SEMANTIC_ENCODER is None:
            return 0

        missing = [value for value in unique if value not in self._static_vectors]
        if not missing:
            return len(self._static_vectors)

        vectors = SEMANTIC_ENCODER.encode(
            missing,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        for candidate, vector in zip(missing, vectors):
            self._static_vectors[candidate] = vector
        return len(self._static_vectors)

    def _query_vector(self, text: str):
        value = normalize_text(text)
        cached = self._query_vector_cache.get(value)
        if cached is not None:
            return cached
        vector = SEMANTIC_ENCODER.encode(
            [value],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )[0]
        self._remember(self._query_vector_cache, value, vector, limit=256)
        return vector

    def similarity(self, text_a: str, text_b: str) -> Dict[str, Any]:
        text_a = normalize_text(text_a)
        text_b = normalize_text(text_b)
        if not text_a or not text_b:
            return {
                "score": 0.0,
                "source": "sentence_transformers",
                "measured": False,
            }

        key = (text_a, text_b)
        cached = self._pair_cache.get(key)
        if cached is not None:
            return {
                "score": float(cached),
                "source": "sentence_transformers",
                "measured": True,
                "cached": True,
            }

        _runtime_ready_guard()
        query_vector = self._query_vector(text_a)
        candidate_vector = self._static_vectors.get(text_b)
        if candidate_vector is None:
            candidate_vector = SEMANTIC_ENCODER.encode(
                [text_b],
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )[0]

        score = float(
            cosine_similarity(
                query_vector.reshape(1, -1),
                candidate_vector.reshape(1, -1),
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
        """Encode the request once; reuse prewarmed prototype vectors.

        In the production fast path, this delegates to the local semantic sketch
        instead of waking the heavyweight transformer encoder.
        """
        text = normalize_text(text)
        if APRIL_FAST_SEMANTIC_MODE and not APRIL_ENABLE_HEAVY_HOTPATH:
            fast_engine = globals().get("QUANTUM_FAST_SEMANTIC")
            if fast_engine is not None:
                scores = {}
                for candidate in candidates:
                    value = normalize_text(candidate)
                    if not value:
                        continue
                    score_map = fast_engine.measure(text)
                    # Dynamic candidates are compared to the same compact context
                    # space; if absent, retain a conservative zero instead of
                    # invoking the heavyweight encoder.
                    scores[value] = max(
                        score_map.get("context_scores", {}).values(), default=0.0
                    )
                return scores
        if not text:
            return {}

        unique: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            value = normalize_text(candidate)
            if value and value not in seen:
                seen.add(value)
                unique.append(value)

        if not unique:
            return {}

        key = (text, tuple(unique))
        cached = self._batch_cache.get(key)
        if cached is not None:
            return dict(cached)

        _runtime_ready_guard()
        if not self._static_vectors:
            static_vocab = []
            for vocab_name in (
                "SEMANTIC_TURN_PROTOTYPES",
                "REPRESENTATION_HYPOTHESES",
                "DOMAIN_HYPOTHESES",
                "CAPABILITY_HYPOTHESES",
            ):
                vocab = globals().get(vocab_name)
                if isinstance(vocab, dict):
                    static_vocab.extend(vocab.values())
            if static_vocab:
                self.prewarm_static(static_vocab)
        query_vector = self._query_vector(text)
        static_candidates = [candidate for candidate in unique if candidate in self._static_vectors]
        dynamic_candidates = [candidate for candidate in unique if candidate not in self._static_vectors]

        result: dict[str, float] = {}

        if static_candidates:
            matrix = [self._static_vectors[candidate] for candidate in static_candidates]
            scores = cosine_similarity(
                query_vector.reshape(1, -1),
                matrix,
            )[0]
            result.update(
                {
                    candidate: max(0.0, min(1.0, float(score)))
                    for candidate, score in zip(static_candidates, scores)
                }
            )

        if dynamic_candidates:
            vectors = SEMANTIC_ENCODER.encode(
                dynamic_candidates,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            scores = cosine_similarity(
                query_vector.reshape(1, -1),
                vectors,
            )[0]
            result.update(
                {
                    candidate: max(0.0, min(1.0, float(score)))
                    for candidate, score in zip(dynamic_candidates, scores)
                }
            )

        self._remember(self._batch_cache, key, dict(result))
        for candidate, score in result.items():
            self._remember_pair((text, candidate), score)
        return result


class QuantumIntentEngine:
    """NLI/zero-shot semantic engine. No keyword routing."""

    def classify(self, text: str, hypotheses: Sequence[str]) -> Dict[str, Any]:
        _runtime_ready_guard()
        _ensure_nli_runtime()
        if DIALOGUE_NLI is None:
            raise RuntimeError("NLI refinement runtime is unavailable")
        result = DIALOGUE_NLI(
            text,
            candidate_labels=list(hypotheses),
            multi_label=True,
        )
        return {
            "labels": list(result["labels"]),
            "scores": [float(score) for score in result["scores"]],
            "source": "transformers_nli",
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
        self.fast = QUANTUM_FAST_SEMANTIC
        self._turn_cache: dict[tuple, Dict[str, Any]] = {}
        self._linguistic_cache: dict[str, Dict[str, Any]] = {}
        self._nli_cache: dict[str, Dict[str, Any]] = {}
        self._cache_limit = 96

    def _remember(self, cache: dict, key: Any, value: Any, limit: int | None = None) -> None:
        cache[key] = value
        cap = int(limit or self._cache_limit)
        if len(cache) > cap:
            cache.pop(next(iter(cache)), None)

    def fast_semantic_profile(
        self,
        text: str,
        previous_assistant: str = "",
        active_topic: str = "",
        active_goal: str = "",
    ) -> Dict[str, Any]:
        return self.fast.measure(
            text,
            previous_assistant=previous_assistant,
            active_topic=active_topic,
            active_goal=active_goal,
        )

    @staticmethod
    def _best_label(result: Dict[str, Any]) -> tuple[str, float]:
        labels = result.get("labels") or []
        scores = result.get("scores") or []
        if not labels:
            return "statement", 0.0
        return str(labels[0]), float(scores[0])

    @staticmethod
    def _fast_family(labels: Sequence[str], positive: Sequence[str] = (), score: float = 0.86) -> Dict[str, Any]:
        positive_set = {str(x) for x in positive}
        scores = [float(score if label in positive_set else 0.03) for label in labels]
        ranked = sorted(zip(labels, scores), key=lambda item: item[1], reverse=True)
        return {
            "labels": [x[0] for x in ranked],
            "scores": [x[1] for x in ranked],
            "source": "fast_semantic_measurement",
        }

    def _fast_measurement(self, text: str, previous_assistant: str, active_topic: str, active_goal: str) -> Dict[str, Any]:
        """One cached semantic measurement for the entire turn."""
        normalized = normalize_text(text)
        key = (
            normalized,
            normalize_text(previous_assistant),
            normalize_text(active_topic),
            normalize_text(active_goal),
        )
        cached = self._turn_cache.get(("fast_profile", key))
        if cached is not None:
            return cached
        if APRIL_FAST_SEMANTIC_MODE and not APRIL_ENABLE_HEAVY_HOTPATH:
            result = self.fast.measure(
                normalized,
                previous_assistant=previous_assistant,
                active_topic=active_topic,
                active_goal=active_goal,
            )
            self._remember(self._turn_cache, ("fast_profile", key), result)
            return result

        prototype_items = list(SEMANTIC_TURN_PROTOTYPES.items())
        representation_items = list(REPRESENTATION_HYPOTHESES.items())
        domain_items = list(DOMAIN_HYPOTHESES.items())
        capability_items = list(CAPABILITY_HYPOTHESES.items())

        candidates = [
            *(value for _, value in prototype_items),
            *(value for _, value in representation_items),
            *(value for _, value in domain_items),
            *(value for _, value in capability_items),
            *(v for v in (active_topic, active_goal, previous_assistant) if v),
        ]
        scores = self.embedding.similarities(normalized, candidates)

        profile = {name: float(scores.get(value, 0.0)) for name, value in prototype_items}
        representation_scores = {
            name: float(scores.get(value, 0.0))
            for name, value in representation_items
        }
        domain_scores = {
            name: float(scores.get(value, 0.0))
            for name, value in domain_items
        }
        capability_scores = {
            name: float(scores.get(value, 0.0))
            for name, value in capability_items
        }

        context_scores = {
            "active_topic": float(scores.get(normalize_text(active_topic), 0.0)) if active_topic else 0.0,
            "active_goal": float(scores.get(normalize_text(active_goal), 0.0)) if active_goal else 0.0,
            "previous_assistant": float(scores.get(normalize_text(previous_assistant), 0.0)) if previous_assistant else 0.0,
        }

        dialogue_options = {
            "identity": profile["identity"],
            "greeting": profile["greeting"],
            "continuation": profile["continuation"],
            "reference": profile["reference"],
            "independent": profile["independent"],
        }
        best_dialogue = max(dialogue_options, key=dialogue_options.get)
        best_dialogue_score = float(dialogue_options[best_dialogue])
        sorted_dialogue = sorted(dialogue_options.values(), reverse=True)
        dialogue_margin = (
            sorted_dialogue[0] - sorted_dialogue[1]
            if len(sorted_dialogue) > 1 else sorted_dialogue[0]
        )

        explicit_representations = [
            name for name, score in representation_scores.items()
            if name != "text" and score >= 0.72
        ]
        best_representation = max(representation_scores, key=representation_scores.get)
        best_rep_score = float(representation_scores[best_representation])

        # Normal requests never wait for NLI. NLI is optional refinement only.
        enable_refinement = os.getenv("APRIL_ENABLE_NLI_REFINEMENT", "0").strip().lower() in {"1", "true", "yes"}
        needs_refinement = bool(
            enable_refinement
            and len(normalized.split()) > 80
            and best_dialogue_score < 0.62
            and dialogue_margin < 0.08
        )

        dialogue_positive = [best_dialogue] if best_dialogue in DIALOGUE_LABELS else ["statement"]
        dialogue_fast = self._fast_family(
            list(DIALOGUE_LABELS),
            dialogue_positive,
            max(0.55, best_dialogue_score),
        )

        rep_ranked = sorted(representation_scores, key=representation_scores.get, reverse=True)
        domain_ranked = sorted(domain_scores, key=domain_scores.get, reverse=True)
        capability_ranked = sorted(capability_scores, key=capability_scores.get, reverse=True)

        result = {
            "needs_refinement": needs_refinement,
            "identity_score": float(profile["identity"]),
            "greeting_score": float(profile["greeting"]),
            "continuation_score": float(profile["continuation"]),
            "reference_score": float(profile["reference"]),
            "independent_score": float(profile["independent"]),
            "dialogue_best": best_dialogue,
            "dialogue_confidence": best_dialogue_score,
            "dialogue_margin": float(dialogue_margin),
            "representation_scores": representation_scores,
            "domain_scores": domain_scores,
            "capability_scores": capability_scores,
            "best_representation": best_representation,
            "best_representation_score": best_rep_score,
            "explicit_representations": explicit_representations,
            "context_scores": context_scores,
            "identity_request": (
                profile["identity"] >= 0.56
                and profile["identity"] >= profile["greeting"] - 0.02
                and profile["identity"] >= profile["continuation"] - 0.03
                and profile["identity"] >= profile["reference"] - 0.03
            ),
            "fast_social": (
                max(profile["identity"], profile["greeting"], profile["independent"]) >= 0.58
                and len(normalized.split()) <= 24
                and best_representation == "text"
                and best_rep_score < 0.72
            ),
            "dialogue_nli": dialogue_fast,
            "representation_nli": {
                "labels": [REPRESENTATION_HYPOTHESES[name] for name in rep_ranked],
                "scores": [representation_scores[name] for name in rep_ranked],
                "source": "shared_embedding_prototypes",
            },
            "domain_nli": {
                "labels": [DOMAIN_HYPOTHESES[name] for name in domain_ranked],
                "scores": [domain_scores[name] for name in domain_ranked],
                "source": "shared_embedding_prototypes",
            },
            "capability_nli": {
                "labels": [CAPABILITY_HYPOTHESES[name] for name in capability_ranked],
                "scores": [capability_scores[name] for name in capability_ranked],
                "source": "shared_embedding_prototypes",
            },
            "source": "single_turn_shared_embedding",
        }
        self._remember(self._turn_cache, ("fast_profile", key), result)
        return result

    def turn_measurement(
        self,
        text: str,
        previous_assistant: str = "",
        previous_user: str = "",
        active_goal: str = "",
        active_topic: str = "",
    ) -> Dict[str, Any]:
        key = (
            str(text or "").strip(),
            str(previous_assistant or "").strip(),
            str(active_goal or "").strip(),
            str(active_topic or "").strip(),
        )
        cached = self._turn_cache.get(key)
        if cached is not None:
            return cached

        normalized_turn_text = str(text or "").strip()
        # Reuse lightweight linguistic evidence for the hot path. Deep Stanza is
        # deliberately not part of normal request latency.
        linguistic = self._linguistic_cache.get(normalized_turn_text)
        if linguistic is None:
            linguistic = _lightweight_linguistic(normalized_turn_text)
            self._linguistic_cache[normalized_turn_text] = linguistic

        fast = self._fast_measurement(
            normalized_turn_text,
            previous_assistant,
            active_topic,
            active_goal,
        )
        nli_bundle = self._nli_cache.get(normalized_turn_text)
        if nli_bundle is None and fast.get("needs_refinement"):
            started_nli = time.perf_counter()
            nli_bundle = {
                # One optional refinement family only; never four sequential
                # NLI passes on the request hot path.
                "dialogue_nli": self.intent.classify(normalized_turn_text, DIALOGUE_LABELS),
                "representation_nli": fast["representation_nli"],
                "domain_nli": fast["domain_nli"],
                "capability_nli": fast["capability_nli"],
                "elapsed_ms": (time.perf_counter() - started_nli) * 1000.0,
                "source": "nli_refinement",
            }
            self._nli_cache[normalized_turn_text] = nli_bundle

        if nli_bundle is None:
            nli_bundle = {
                "dialogue_nli": fast["dialogue_nli"],
                "representation_nli": fast["representation_nli"],
                "domain_nli": fast["domain_nli"],
                "capability_nli": fast["capability_nli"],
                "source": "embedding_hot_path",
                "elapsed_ms": 0.0,
            }

        dialogue_nli = nli_bundle["dialogue_nli"]
        representation_nli = nli_bundle["representation_nli"]
        domain_nli = nli_bundle["domain_nli"]
        capability_nli = nli_bundle["capability_nli"]

        if APRIL_FAST_SEMANTIC_MODE and not APRIL_ENABLE_HEAVY_HOTPATH:
            embedding_map = dict(fast.get("context_scores") or {})
        else:
            embedding_map = self.embedding.similarities(
                text,
                [v for v in (previous_assistant, active_topic, active_goal) if v],
            )

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
            "decision_owner": "QUANTUM_PROCESSOR",
            "evidence_only": True,
            "engine": "quantum_interpretation_turn_engine",
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


def _is_micro_social_turn(text: Any) -> bool:
    """Semantic fast-path gate; no lexical trigger list."""
    normalized = re.sub(r"\s+", " ", normalize_text(text)).strip()
    if not normalized or len(normalized.split()) > 24:
        return False
    profile = QUANTUM_EVIDENCE_FUSION._fast_measurement(
        normalized, "", "", ""
    )
    return bool(profile.get("fast_social"))


def _semantic_identity_request(text: Any) -> bool:
    normalized = normalize_text(text)
    if not normalized:
        return False
    profile = QUANTUM_EVIDENCE_FUSION._fast_measurement(
        normalized, "", "", ""
    )
    return bool(profile.get("identity_request"))


def _dialogue_signal_contract(
    text: str,
    history: list,
    state: dict,
    semantic: dict,
    cognition: dict | None = None,
    precomputed_profile: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    last_assistant = ""
    last_user = ""
    last_turn_id = None
    for item in reversed(history):
        if not isinstance(item, dict):
            continue
        # Accept both canonical paired records and the legacy role/content
        # hot-dialog representation produced by State Manager.
        if not last_assistant and isinstance(item.get("april"), dict):
            last_assistant = normalize_text(
                item["april"].get("answer")
                or item["april"].get("content")
                or item["april"].get("summary")
            )
            last_turn_id = item.get("turn_id")
        elif not last_assistant and str(item.get("role", "")).lower() in {"assistant", "april"}:
            last_assistant = normalize_text(
                item.get("content")
                or item.get("answer")
                or item.get("summary")
            )
            last_turn_id = item.get("turn_id")

        if not last_user and item.get("user"):
            last_user = normalize_text(item.get("user"))
        elif not last_user and str(item.get("role", "")).lower() == "user":
            last_user = normalize_text(item.get("content"))

        if last_assistant and last_user:
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

    profile = precomputed_profile or QUANTUM_EVIDENCE_FUSION._fast_measurement(
        text, last_assistant, active_topic, active_goal
    )
    fast_social = bool(profile.get("fast_social"))
    if fast_social:
        label = (
            "self_identification"
            if profile.get("identity_request")
            else (
                "statement"
                if profile.get("greeting_score", 0.0) >= profile.get("continuation_score", 0.0)
                else "question"
            )
        )
        context_scores = profile.get("context_scores", {}) or {}
        measured = {
            "dialogue": {
                "label": label,
                "continuation_score": float(profile.get("continuation_score", 0.0)),
                "reference_score": float(profile.get("reference_score", 0.0)),
                "topic_score": float(context_scores.get("active_topic", 0.0)),
                "goal_score": float(context_scores.get("active_goal", 0.0)),
                "confidence": float(profile.get("dialogue_confidence", 0.7)),
            },
            "source": "semantic_embedding_fast_path",
            "identity_request": bool(profile.get("identity_request")),
            "greeting_score": float(profile.get("greeting_score", 0.0)),
        }
    else:
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


def _semantic_context_packet(
    text: str,
    history: list,
    state: dict,
    semantic: dict,
    cognition: dict,
) -> Dict[str, Any]:
    """Build one canonical semantic packet with one fast measurement."""
    started = time.perf_counter()

    previous_answer = ""
    active_topic = normalize_text(
        state.get("active_topic")
        or state.get("current_topic")
        or semantic.get("current_topic")
        or cognition.get("active_topic")
        or cognition.get("current_topic")
    )
    active_goal = normalize_text(
        state.get("active_goal")
        or state.get("current_goal")
        or semantic.get("active_goal")
        or cognition.get("active_goal")
        or cognition.get("current_goal")
    )

    # Read only the most recent assistant turn; no full-history semantic scan.
    for item in reversed(history if isinstance(history, list) else []):
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").lower()
        if isinstance(item.get("april"), dict):
            previous_answer = normalize_text(
                item["april"].get("answer")
                or item["april"].get("content")
                or item["april"].get("summary")
            )
        elif role in {"assistant", "april", "bot"}:
            previous_answer = normalize_text(
                item.get("content")
                or item.get("answer")
                or item.get("summary")
            )
        if previous_answer:
            break

    profile = QUANTUM_EVIDENCE_FUSION._fast_measurement(
        text, previous_answer, active_topic, active_goal
    )

    fast_social = bool(profile.get("fast_social"))
    is_identity = bool(profile.get("identity_request"))
    context_scores = profile.get("context_scores", {}) or {}

    if fast_social:
        dialogue = _dialogue_signal_contract(
            text,
            history,
            state,
            semantic,
            cognition,
            precomputed_profile=profile,
        )
        representation = {
            "measurements": [{
                "type": "text",
                "score": 1.0,
                "source": "shared_embedding_fast_path",
                "nli": {
                    "labels": list(REPRESENTATION_HYPOTHESES.keys()),
                    "scores": [1.0 if name == "text" else 0.0 for name in REPRESENTATION_HYPOTHESES],
                    "source": "shared_embedding_fast_path",
                },
            }],
            "context_similarity": {"score": max(context_scores.values(), default=0.0), "source": "shared_embedding_fast_path"},
            "nli": {
                "labels": list(REPRESENTATION_HYPOTHESES.keys()),
                "scores": [1.0 if name == "text" else 0.0 for name in REPRESENTATION_HYPOTHESES],
                "source": "shared_embedding_fast_path",
            },
        }
        linguistic = _lightweight_linguistic(text)
        domain = {
            "measurements": [],
            "source": "shared_embedding_fast_path",
        }
        context_vectors = {
            "previous_answer": {"score": float(context_scores.get("previous_assistant", 0.0))},
            "active_topic": {"score": float(context_scores.get("active_topic", 0.0))},
            "active_goal": {"score": float(context_scores.get("active_goal", 0.0))},
        }
        return {
            "linguistic": linguistic,
            "dialogue": dialogue,
            "representation": representation,
            "domain": domain,
            "context_vectors": context_vectors,
            "identity_request": is_identity,
            "fast_path": True,
            "profile": profile,
            "decision_owner": "QUANTUM_PROCESSOR",
            "engine": "quantum_interpretation_engine",
            "evidence_only": True,
            "measurement_ms": round((time.perf_counter() - started) * 1000, 2),
        }

    # One shared measurement drives the evidence families.
    dialogue = _dialogue_signal_contract(
        text,
        history,
        state,
        semantic,
        cognition,
        precomputed_profile=profile,
    )
    representation_scores = profile.get("representation_scores", {}) or {}
    rep_ranked = sorted(representation_scores, key=representation_scores.get, reverse=True)
    representation = {
        "measurements": [
            {
                "type": name,
                "score": float(representation_scores.get(name, 0.0)),
                "source": "shared_embedding_fast_path",
                "nli": {
                    "labels": [REPRESENTATION_HYPOTHESES[n] for n in rep_ranked],
                    "scores": [float(representation_scores[n]) for n in rep_ranked],
                    "source": "shared_embedding_fast_path",
                },
            }
            for name in rep_ranked[:6]
        ],
        "context_similarity": {"score": max(context_scores.values(), default=0.0), "source": "shared_embedding_fast_path"},
        "nli": {
            "labels": [REPRESENTATION_HYPOTHESES[n] for n in rep_ranked],
            "scores": [float(representation_scores[n]) for n in rep_ranked],
            "source": "shared_embedding_fast_path",
        },
    }

    linguistic = _lightweight_linguistic(text)
    domain_ranked = sorted(
        (profile.get("domain_nli", {}) or {}).get("labels", []),
        key=lambda x: (profile.get("domain_nli", {}) or {}).get("scores", [0] * len((profile.get("domain_nli", {}) or {}).get("labels", [])))[
            (profile.get("domain_nli", {}) or {}).get("labels", []).index(x)
        ] if x in (profile.get("domain_nli", {}) or {}).get("labels", []) else 0,
        reverse=True,
    )
    domain_scores = profile.get("domain_scores", {}) or {}

    return {
        "linguistic": linguistic,
        "dialogue": dialogue,
        "representation": representation,
        "domain": {
            "measurements": [
                {"domain": name, "score": float(score)}
                for name, score in sorted(domain_scores.items(), key=lambda kv: kv[1], reverse=True)
                if float(score) >= 0.45
            ],
            "source": "shared_embedding_fast_path",
        },
        "context_vectors": {
            "previous_answer": {"score": float(context_scores.get("previous_assistant", 0.0))},
            "active_topic": {"score": float(context_scores.get("active_topic", 0.0))},
            "active_goal": {"score": float(context_scores.get("active_goal", 0.0))},
        },
        "identity_request": is_identity,
        "fast_path": False,
        "profile": profile,
        "decision_owner": "QUANTUM_PROCESSOR",
        "engine": "quantum_interpretation_engine",
        "evidence_only": True,
        "measurement_ms": round((time.perf_counter() - started) * 1000, 2),
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
    identity_request = bool(semantic.get("identity_request") or measured.get("identity_request"))

    if continuation and previous_assistant:
        resolved_request = (
            f"Continue the previous task naturally. "
            f"Previous assistant response: {previous_assistant}\n"
            f"Current user instruction: {text}"
        )
    else:
        resolved_request = text

    capabilities = []
    if semantic.get("candidate_representations"):
        capabilities.append("structured_rendering")
    if float(measured.get("analysis_score", 0.0)) >= 0.62:
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
        "identity_request": identity_request,
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

    profile = semantic_packet.get("profile", {}) if isinstance(semantic_packet.get("profile"), dict) else {}
    representation_scores = profile.get("representation_scores", {}) or {}
    domain_scores = profile.get("domain_scores", {}) or {}
    capability_scores = profile.get("capability_scores", {}) or {}

    if semantic_packet.get("fast_path"):
        domains = []
        representation_evidence = [{
            "label": "text",
            "score": 1.0,
            "source": "shared_embedding_fast_path",
            "details": {"decision_owner": "QUANTUM_PROCESSOR", "evidence_only": True},
        }]
    else:
        domains = [
            name for name, score in domain_scores.items()
            if float(score) >= 0.45
        ]
        representation_evidence = [
            {
                "label": name,
                "score": float(score),
                "source": "shared_embedding_fast_path",
                "details": {"decision_owner": "QUANTUM_PROCESSOR", "evidence_only": True},
            }
            for name, score in sorted(
                representation_scores.items(), key=lambda item: item[1], reverse=True
            )
            if float(score) >= 0.45
        ]

    semantic_candidates = [
        item["label"] for item in representation_evidence if float(item["score"]) >= 0.45
    ]

    explicit_required = [
        str(x).lower()
        for x in (
            (semantic.get("required_representations", []) or [])
            + (cognition.get("required_representations", []) or [])
        )
        if str(x).strip()
    ]

    result["semantic_profile"] = {
        "dialogue_history": history[-8:],
        "previous_april_turn": semantic_packet["dialogue"].get("previous_april_turn", ""),
        "active_topic": semantic_packet["dialogue"].get("active_topic", ""),
        "active_goal": semantic_packet["dialogue"].get("active_goal", ""),
        "identity_request": bool(semantic_packet.get("identity_request")),
        "fast_path": bool(semantic_packet.get("fast_path")),
        "representation_scores": representation_scores,
        "domain_scores": domain_scores,
        "capability_scores": capability_scores,
        "context_scores": profile.get("context_scores", {}),
        "engine": "quantum_interpretation_engine_v4",
    }
    result["scene_profile"] = build_scene_construction_profile(result["semantic_profile"])
    result["artifact_contract"] = build_scene_artifact_contract(
        result["semantic_profile"], result["scene_profile"]
    )

    result["candidate_domains"] = domains
    result["required_domains"] = list(
        semantic.get("required_domains", []) or domains
    )
    result["domain_confidence"] = {
        name: round(float(score), 4) for name, score in domain_scores.items()
    }
    result["candidate_representations"] = semantic_candidates
    result["representation_evidence"] = representation_evidence
    result["required_representations"] = explicit_required
    result["scene_type"] = explicit_required[0] if explicit_required else None

    # Capability evidence comes from the same single embedding measurement.
    result["discussion_mode"] = float(capability_scores.get("discussion", 0.0)) >= 0.60
    result["space_discussion"] = float(capability_scores.get("space", 0.0)) >= 0.60
    result["exploration"] = float(capability_scores.get("exploration", 0.0))
    result["continuation"] = float(
        semantic_packet["dialogue"].get("continuation_score", 0.0)
    )
    result["web_context"] = float(capability_scores.get("web", 0.0))
    result["explicit_image_generation"] = float(representation_scores.get("image", 0.0))
    result["lightweight_visual"] = max(
        float(representation_scores.get("graph", 0.0)),
        float(representation_scores.get("diagram", 0.0)),
        float(representation_scores.get("image", 0.0)),
    ) >= 0.72

    result["contains_object"] = bool(text)
    result["contains_explanation"] = float(capability_scores.get("information", 0.0)) >= 0.60
    result["contains_analysis"] = float(capability_scores.get("exploration", 0.0)) >= 0.60
    result["contains_legend"] = False
    if result["contains_explanation"]:
        result["content_role"] = "explanation"
    elif result["contains_analysis"]:
        result["content_role"] = "analysis"

    result["evidence"] = {
        "domain": semantic_packet["domain"],
        "representation": representation_evidence,
        "math": float(representation_scores.get("formula", 0.0)),
        "code": float(representation_scores.get("code", 0.0)),
        "web": result["web_context"],
        "image": result["explicit_image_generation"],
        "continuation": result["continuation"],
        "exploration": result["exploration"],
        "information": float(capability_scores.get("information", 0.0)),
        "linguistic": semantic_packet["linguistic"],
        "dialogue": semantic_packet["dialogue"],
        "context_vectors": semantic_packet["context_vectors"],
        "cognition": dict(cognition),
        "semantic": dict(semantic),
    }

    result["identity_request"] = bool(semantic_packet.get("identity_request"))
    result["fast_social"] = bool(semantic_packet.get("fast_path"))
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


def interpret_request(text, cognition=None, semantic=None, history=None, state=None):
    result = _base_interpret_request(
        text,
        cognition=cognition,
        semantic=semantic,
        history=history,
        state=state,
    )
    if result is None:
        return None

    contract = (
        result.get("quantum_interpretation_field", {}).get("dialogue")
        if isinstance(result.get("quantum_interpretation_field"), dict)
        else None
    )
    if not isinstance(contract, dict):
        contract = _dialogue_signal_contract(
            text,
            history or [],
            state or {},
            result,
            cognition or {},
        )

    result["dialogue_contract"] = contract
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
        "nli_intent": "refinement_only",
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
    result["semantic_engine_diagnostics"] = {
        "engines": [
            "stanza_multilingual_linguistic",
            "spacy_ner",
            "sentence_transformers_embedding",
            "transformers_nli_refinement",
            "quantum_fast_measurement",
            "quantum_evidence_fusion",
        ],
        "engine_mode": "required",
        "fallback_mode": False,
        "substring_routing": False,
        "candidate_to_required_promotion": False,
        "renderer_selection_owner": "QUANTUM_PROCESSOR",
        "single_route": True,
    }
    result["interpretation_state"] = state_out
    result["transport_diagnostics"] = build_transport_diagnostics(result)
    result = propagate_canonical_response(result, state_out)
    result = bridge_machine_response(result, state_out)

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
