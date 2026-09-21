# -*- coding: utf-8 -*-
"""
APRIL — interpretation_layer compatibility + current-turn boundary
==================================================================

Deploy target:
    blocks/interpretation_layer.py

What this file fixes:
1. It NEVER imports a hard-coded
   ``blocks.April_interpretation_layer_dialogue_synced`` at module import time.
   That exact dependency caused the Railway crash on 2026-09-21.
2. It preserves the public ``interpret_request`` API expected by executor.py.
3. It lazily discovers an existing canonical Quantum interpretation engine.
4. It keeps the current user turn authoritative for provider-facing request text.
5. It blocks accidental CONTINUE state for a self-contained current request when
   there is no explicit reference/anaphora/pending-input evidence.
6. It prevents stale structured representation from silently upgrading a plain
   informational request.
7. If no canonical engine file is present in the deployed package, the service
   remains importable and returns a conservative TEXT interpretation instead of
   crashing the entire Railway container.

Important:
- No second semantic engine is created when a canonical engine is available.
- Historical dialogue remains evidence; it is not injected into
  ``resolved_request`` unless the canonical engine explicitly needs it.
"""

from __future__ import annotations

import importlib
import re
import hashlib
import time
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

try:
    from rapidfuzz import fuzz as _rapidfuzz
except Exception:
    _rapidfuzz = None

try:
    from nltk.stem.snowball import SnowballStemmer
    _RUSSIAN_STEMMER = SnowballStemmer("russian")
    _ENGLISH_STEMMER = SnowballStemmer("english")
except Exception:
    _RUSSIAN_STEMMER = None
    _ENGLISH_STEMMER = None


# ---------------------------------------------------------------------------
# Runtime discovery
# ---------------------------------------------------------------------------

_THIS_MODULE = __name__
_THIS_FILE = Path(__file__).resolve()
_PACKAGE_NAME = __package__ or "blocks"
_PACKAGE_DIR = _THIS_FILE.parent

# Deterministic candidates used by this project over time.
# The CURRENT file is deliberately excluded to avoid recursive import.
_KNOWN_ENGINE_MODULES = (
    "blocks.blocks_interpretation_layer",
    "blocks.interpretation_layer_v2",
    "blocks.interpretation_layer_dialogue_semantic_boundary_fixed_v3",
    "blocks.interpretation_layer_dialogue_fixed",
    "blocks.interpretation_layer_dialogue_sequential_order_fixed_v10",
    "blocks.interpretation_layer_dialogue_sequential_order_fixed_v5",
    "blocks.interpretation_layer_quantum_matrix_final",
    "blocks.interpretation_layer_quantum_matrix_context_engine",
    "blocks.interpretation_layer_upgraded",
    "blocks.Qvantium_interpretation_layer_context_v1",
    "blocks.interpretation_layer_original",
)

_ENGINE_MODULE: Any = None
_ENGINE_OBJECT: Any = None
_ENGINE_LOAD_ATTEMPTED = False
_ENGINE_LOAD_ERRORS: list[str] = []


def _module_has_canonical_engine(module: Any) -> bool:
    """Return True only for a module exposing the project's real engine."""
    engine = getattr(module, "QUANTUM_INTERPRETATION_ENGINE", None)
    return engine is not None and callable(getattr(engine, "interpret", None))


def _safe_module_name_from_path(path: Path) -> str:
    return f"{_PACKAGE_NAME}.{path.stem}"


def _discover_source_candidates() -> list[str]:
    """
    Discover canonical engine files without importing arbitrary project modules.

    A file becomes a candidate only when its source contains the canonical engine
    class/object markers. This keeps discovery deterministic and avoids executing
    unrelated modules just to find a name.
    """
    found: list[str] = []

    try:
        for path in sorted(_PACKAGE_DIR.glob("*.py")):
            if path.resolve() == _THIS_FILE:
                continue

            stem = path.stem
            low = stem.lower()

            if low.startswith("_"):
                continue

            # Exclude obvious patcher/temp files.
            if any(
                marker in low
                for marker in (
                    "repair",
                    "patched",
                    "patch",
                    "tmp",
                    "backup",
                    "test",
                )
            ):
                continue

            try:
                source = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            if (
                "QUANTUM_INTERPRETATION_ENGINE" in source
                and "QuantumInterpretationEngine" in source
                and ".interpret(" in source
            ):
                found.append(_safe_module_name_from_path(path))
    except Exception:
        pass

    return found


def _load_canonical_engine_module() -> Any:
    """
    Lazily resolve the real canonical interpretation module.

    Crucially this function is NOT executed at module import time. The Railway
    crash happened because the previous wrapper imported a nonexistent module
    before executor.py could even load.
    """
    global _ENGINE_MODULE, _ENGINE_OBJECT, _ENGINE_LOAD_ATTEMPTED

    if _ENGINE_LOAD_ATTEMPTED:
        return _ENGINE_MODULE

    _ENGINE_LOAD_ATTEMPTED = True

    candidates: list[str] = []
    seen: set[str] = set()

    for name in _KNOWN_ENGINE_MODULES:
        if name == _THIS_MODULE or name in seen:
            continue
        seen.add(name)
        candidates.append(name)

    for name in _discover_source_candidates():
        if name == _THIS_MODULE or name in seen:
            continue
        seen.add(name)
        candidates.append(name)

    for module_name in candidates:
        try:
            module = importlib.import_module(module_name)

            if _module_has_canonical_engine(module):
                _ENGINE_MODULE = module
                _ENGINE_OBJECT = module.QUANTUM_INTERPRETATION_ENGINE
                return module

        except Exception as exc:
            _ENGINE_LOAD_ERRORS.append(
                f"{module_name}: {type(exc).__name__}: {exc}"
            )

    return None


# ---------------------------------------------------------------------------
# Lazy compatibility proxy
# ---------------------------------------------------------------------------

class _LazyEngineProxy:
    """
    Compatibility object for code that accesses
    ``interpretation_layer.QUANTUM_INTERPRETATION_ENGINE`` directly.
    """

    def __getattr__(self, name: str) -> Any:
        module = _load_canonical_engine_module()
        if module is not None:
            engine = getattr(module, "QUANTUM_INTERPRETATION_ENGINE", None)
            if engine is not None:
                return getattr(engine, name)

        local_engine = globals().get("_LOCAL_INTERPRETATION_ENGINE")
        if local_engine is not None and hasattr(local_engine, name):
            return getattr(local_engine, name)

        return getattr(_FallbackInterpretationEngine(), name)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        module = _load_canonical_engine_module()
        if module is not None:
            engine = getattr(module, "QUANTUM_INTERPRETATION_ENGINE", None)
            if callable(engine):
                return engine(*args, **kwargs)

        local_engine = globals().get("_LOCAL_INTERPRETATION_ENGINE")
        if callable(getattr(local_engine, "interpret", None)):
            return local_engine.interpret(*args, **kwargs)

        return _FallbackInterpretationEngine()(*args, **kwargs)


QUANTUM_INTERPRETATION_ENGINE = _LazyEngineProxy()


# ---------------------------------------------------------------------------
# Current-turn safety fence
# ---------------------------------------------------------------------------

_INTERNAL_PROMPT_MARKERS = (
    "The current request is a semantic continuation of the immediately preceding",
    "The current request recalls an older authenticated USER↔APRIL result.",
    "The current calculation is history-dependent.",
    "Previous USER request:",
    "Previous APRIL answer:",
    "Recalled USER request:",
    "Recalled APRIL result:",
    "Resolved semantic referent:",
    "Use this referent as the object of the current request",
    "Use the resolved historical results as the operands for the current task",
    "Contextual referent resolved from the immediately previous human exchange:",
)


def _clean_text(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\r\n?", "\n", text)
    return text


def _contains_internal_prompt_material(value: Any) -> bool:
    text = str(value or "")
    return any(marker in text for marker in _INTERNAL_PROMPT_MARKERS)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _dialogue_vector(result: dict[str, Any]) -> dict[str, Any]:
    vector = result.get("dialogue_vector")
    return _as_dict(vector)


def _nested_sequential(result: dict[str, Any]) -> dict[str, Any]:
    vector = _dialogue_vector(result)
    return _as_dict(vector.get("sequential_dialogue"))


def _self_contained_without_reference(result: dict[str, Any]) -> bool:
    """
    Exact protection for the regression seen in the Railway test:

        relation=CONTINUE
        self_contained=True
        explicit_reference=False
        grammatical_anaphora=False
        pending_input=False
        explicit_task=False

    A genuine explicit continuation/reference is left untouched.
    """
    vector = _dialogue_vector(result)
    sequential = _nested_sequential(result)

    candidates = (result, vector, sequential)

    relation = ""
    for source in candidates:
        relation = str(
            source.get("relation")
            or source.get("request_relation")
            or source.get("dialogue_relation")
            or ""
        ).upper()
        if relation:
            break

    if relation not in {"CONTINUE", "CONTINUE_TOPIC"}:
        return False

    # A semantic continuation can be fully self-contained (for example,
    # "Что ещё интересного про него можно узнать?").  The old Railway fence
    # treated that shape as a forced NEW turn.  The canonical local engine now
    # marks such turns explicitly, so the safety fence must respect that proof.
    if any(bool(source.get("sequence_continuation_authorized")) for source in candidates):
        return False

    def _flag(*names: str) -> bool:
        return any(bool(source.get(name)) for source in candidates for name in names)

    self_contained = _flag("self_contained", "current_request_complete")

    explicit_reference = _flag(
        "explicit_reference",
        "reference_to_previous",
        "reference",
        "artifact_reference_evidence",
    )

    grammatical_anaphora = _flag(
        "grammatical_anaphora",
        "anaphora",
    )

    pending_input = _flag(
        "pending_input",
        "requires_previous_input",
    )

    explicit_task = _flag(
        "explicit_task",
        "task_explicit",
    )

    # If a field named current_request_complete exists, False means incomplete.
    complete_fields = [
        source.get("current_request_complete")
        for source in candidates
        if "current_request_complete" in source
    ]
    if complete_fields:
        self_contained = self_contained or any(
            value is True for value in complete_fields
        )

    return bool(
        self_contained
        and not explicit_reference
        and not grammatical_anaphora
        and not pending_input
        and not explicit_task
    )


def _explicit_structured_request(text: str) -> bool:
    """
    Narrow current-turn check. This is NOT a command router; it only prevents
    inherited renderer state from leaking into a plain informational request.
    """
    low = _clean_text(text).lower()

    tokens = (
        "нарисуй",
        "изобрази",
        "покажи схему",
        "покажи график",
        "построй график",
        "построй диаграмму",
        "сделай диаграмму",
        "нарисовать",
        "изображение",
        "формулу",
        "формул",
        "уравнение",
        "график функции",
        "таблицу",
        "таблица",
        "код",
        "python",
        "json",
        "markdown",
        "ссылку",
        "видео",
        "аудио",
        "файл",
        "draw ",
        "plot ",
        "chart ",
        "diagram ",
        "table ",
        "formula ",
        "equation ",
        "show the graph",
    )

    return any(token in low for token in tokens)


def _sanitize_provider_facing_fields(result: dict[str, Any], current_text: str) -> None:
    """
    Internal historical prose belongs in structured evidence fields, not in the
    provider-facing request operand.
    """
    current = _clean_text(current_text)

    provider_fields = (
        "resolved_request",
        "provider_request",
        "request_operand",
        "prompt",
        "current_request",
    )

    for key in provider_fields:
        if key not in result:
            continue

        value = result.get(key)
        if _contains_internal_prompt_material(value):
            result[key] = current

    # `resolved_request` is the canonical operand used by the project's
    # interpretation/provider bridge. Keep it bound to this user turn.
    result["resolved_request"] = current
    result["request_operand"] = current
    result["request_operand_source"] = "current_user_turn"
    result["request_operand_sanitized"] = True


def _force_new_turn_state(result: dict[str, Any], current_text: str) -> None:
    """
    Neutralize the exact false-CONTINUE shape without deleting the engine's
    actual historical evidence.
    """
    current = _clean_text(current_text)

    result["continuation"] = False
    result["reference_to_previous"] = False
    result["dialogue_relation"] = "NEW"
    result["relation"] = "NEW_TOPIC"
    result["request_dependency"] = "independent"
    result["context_dependency"] = "independent"
    result["resolved_reference"] = ""
    result["history_dependent_task"] = False
    result["current_turn_authority"] = True
    result["historical_memory_is_evidence_only"] = True

    vector = _dialogue_vector(result)
    if vector:
        vector.update(
            {
                "relation": "NEW_TOPIC",
                "topic_relation": "NEW_TOPIC",
                "request_relation": "NEW_TOPIC",
                "request_dependency": "independent",
                "continuation": False,
                "reference_to_previous": False,
                "three_way_relation": "NEW",
                "resolved_reference": "",
                "resolved_request": current,
                "request_operand": current,
                "request_operand_source": "current_user_turn",
                "current_turn_authority": True,
                "historical_memory_is_evidence_only": True,
                "forced_new_topic": True,
                "forced_new_topic_reason": (
                    "self_contained_without_reference_evidence"
                ),
            }
        )

        sequential = _as_dict(vector.get("sequential_dialogue"))
        if sequential:
            sequential.update(
                {
                    "relation": "NEW",
                    "subtype": "NEW_TOPIC",
                    "continuation": False,
                    "reference": False,
                    "selected_pair": {},
                    "resolved_reference": "",
                }
            )
            vector["sequential_dialogue"] = sequential

        result["dialogue_vector"] = vector


def _remove_stale_structured_representation(
    result: dict[str, Any],
    current_text: str,
) -> None:
    """
    Do not let an old formula/graph/diagram/image state turn a plain information
    request into a structured scene.

    This changes only explicit representation hints at the interpretation
    boundary; it does not touch canonical historical evidence.
    """
    if _explicit_structured_request(current_text):
        return

    structured = {
        "formula",
        "graph",
        "diagram",
        "image",
        "gallery",
        "table",
        "code",
        "link",
        "audio",
        "video",
        "file",
        "scene",
        "memory",
        "visual_context",
    }

    operation = str(
        result.get("operation")
        or result.get("best_operation")
        or result.get("active_operation")
        or ""
    ).lower()

    representation = str(
        result.get("production")
        or result.get("representation")
        or result.get("subtype")
        or result.get("scene_type")
        or ""
    ).lower()

    # Only scrub stale structured state for answer/explain/retrieve/list style
    # operations, or where the engine exposes no operation at all.
    text_operations = {
        "",
        "answer",
        "explain",
        "retrieve",
        "list",
        "analyze",
        "present",
    }

    if representation in structured and operation in text_operations:
        result["production"] = "text"
        result["representation"] = "text"
        result["subtype"] = "text"
        result["scene_type"] = "text"
        result["visual_production_mode"] = "text"
        result["requested_representations"] = ["text"]
        result["requested_outputs"] = ["text"]

        presentation = result.get("presentation")
        if isinstance(presentation, dict):
            presentation = dict(presentation)
            presentation["production_representation"] = "text"
            presentation["signals"] = []
            presentation["recommendations"] = []
            presentation["scene_plan"] = []
            presentation["stale_context_cannot_upgrade_current_representation"] = True
            result["presentation"] = presentation


def _repair_interpretation_result(
    result: Any,
    current_text: str,
) -> Any:
    if not isinstance(result, dict):
        return result

    current = _clean_text(current_text)

    # Never allow an internal prompt to be carried as the user request.
    _sanitize_provider_facing_fields(result, current)

    # Exact Railway regression fence.
    if _self_contained_without_reference(result):
        _force_new_turn_state(result, current)

    # Plain informational turns cannot inherit an unrelated old renderer.
    _remove_stale_structured_representation(result, current)

    result["interpretation_compatibility"] = {
        "version": "2026-09-21-lazy-engine-current-turn-fence-v2",
        "canonical_engine_discovery": bool(
            _load_canonical_engine_module() is not None
        ),
        "current_turn_authoritative": True,
        "provider_request_current_turn_only": True,
        "historical_memory_evidence_only": True,
        "false_continue_fence": True,
        "stale_representation_fence": True,
    }

    return result



# ---------------------------------------------------------------------------
# Built-in seven-day dialogue interpretation engine
# ---------------------------------------------------------------------------

_DIALOGUE_STOPWORDS = {
    "и", "а", "но", "или", "же", "ли", "не", "ни", "что", "это",
    "этот", "эта", "эти", "тот", "та", "те", "как", "так", "про",
    "для", "при", "из", "на", "в", "во", "с", "со", "к", "у", "о",
    "об", "по", "до", "от", "за", "мне", "меня", "ты", "тебя", "я",
    "мы", "вы", "он", "она", "оно", "они", "его", "ее", "её", "их",
    "мой", "моя", "мое", "моё", "можешь", "можно", "нужно", "надо",
    "есть", "был", "была", "быть", "будет", "расскажи", "рассказать",
    "рассказать", "скажи", "покажи", "дай", "пожалуйста", "теперь",
    "ещё", "еще", "дальше", "снова", "уточни", "объясни", "интересного",
    "интересные", "интересный", "факт", "факты", "рассказывать",
    "можешь", "могу", "мог", "можно", "хочу",
}

_REFERENCE_WORDS = {
    "помнишь", "вернемся", "вернёмся", "вернуться", "возвращаясь",
    "предыдущ", "прошлый", "прошлая", "прошлое", "прошлые",
    "дальше", "продолжи", "продолжим", "снова", "как", "раньше",
    "тогда", "него", "нему", "ним", "ему", "ей", "ее", "её", "ней",
    "неё", "ним", "ими", "он", "она", "это",
}

_EXPLICIT_NEW_MARKERS = (
    "новая тема", "другая тема", "сменим тему", "перейдем к другой теме",
    "перейдём к другой теме", "забудь эту тему", "начнем новую тему",
    "начнём новую тему",
)

_FOLLOWUP_MARKERS = (
    "ещё", "еще", "дальше", "теперь", "продолжи", "продолжим",
    "уточни", "объясни", "расскажи", "покажи", "почему", "как",
)

_REFERENCE_PHRASES = (
    "про него", "про нее", "про неё", "про него же", "про неё же",
    "о нем", "о нём", "о ней", "его компания", "ее компания", "её компания",
    "как раньше", "как тогда", "вернемся", "вернёмся", "помнишь",
)

class QuantumEmbeddingEngine:
    """
    Lightweight shared semantic field for the existing architecture.

    This is deliberately dependency-light: it uses stemmed lexical overlap,
    token-set similarity and character similarity.  It is exposed under the
    project's existing QUANTUM_EMBEDDING_ENGINE name so State Manager and the
    visual-reference layer share exactly one measurement implementation.
    """

    VERSION = "quantum_shared_semantic_field_v1"

    @staticmethod
    def _stem(token: str) -> str:
        value = str(token or "").lower()
        if not value:
            return ""
        try:
            if re.search(r"[а-яё]", value) and _RUSSIAN_STEMMER is not None:
                return _RUSSIAN_STEMMER.stem(value)
            if _ENGLISH_STEMMER is not None:
                return _ENGLISH_STEMMER.stem(value)
        except Exception:
            pass
        return value

    @classmethod
    def tokens(cls, value: Any) -> set[str]:
        raw = re.findall(r"[a-zа-яё0-9]{3,}", _clean_text(value).lower())
        return {
            stem
            for item in raw
            if item not in _DIALOGUE_STOPWORDS
            for stem in [cls._stem(item)]
            if stem
        }

    @classmethod
    def similarity(cls, left: Any, right: Any) -> float:
        a = cls.tokens(left)
        b = cls.tokens(right)
        if not a or not b:
            return 0.0
        overlap = len(a & b) / max(1.0, min(len(a), len(b)))
        union = len(a | b)
        jaccard = len(a & b) / max(1.0, union)

        raw_left = _clean_text(left).lower()
        raw_right = _clean_text(right).lower()
        if _rapidfuzz is not None:
            fuzzy = float(_rapidfuzz.token_set_ratio(raw_left, raw_right)) / 100.0
        else:
            fuzzy = SequenceMatcher(None, raw_left, raw_right).ratio()

        return max(0.0, min(1.0, 0.48 * overlap + 0.22 * jaccard + 0.30 * fuzzy))

    def similarities(self, query: Any, candidates: list[Any]) -> dict[str, float]:
        q = _clean_text(query)
        return {
            _clean_text(candidate): round(self.similarity(q, candidate), 6)
            for candidate in candidates
            if _clean_text(candidate)
        }

    def encode(self, value: Any) -> set[str]:
        return self.tokens(value)

    def turn_measurement(
        self,
        current: Any,
        previous_user: Any = "",
        previous_april: Any = "",
        active_topic: Any = "",
        active_goal: Any = "",
    ) -> dict[str, Any]:
        """Return one shared semantic measurement used by context/memory layers."""
        current_text = _clean_text(current)
        candidates = {
            "previous_user": self.similarity(current_text, previous_user),
            "previous_april": self.similarity(current_text, previous_april),
            "active_topic": self.similarity(current_text, active_topic),
            "active_goal": self.similarity(current_text, active_goal),
        }
        continuation_score = max(
            candidates["previous_user"],
            candidates["previous_april"],
            candidates["active_topic"],
        )
        reference_score = 1.0 if _is_reference_turn(current_text) else 0.0
        independent_score = max(
            0.0,
            min(1.0, 1.0 - max(candidates["active_topic"], candidates["previous_user"])),
        )
        return {
            "version": self.VERSION,
            "dialogue": {
                "continuation_score": round(continuation_score, 6),
                "reference_score": round(reference_score, 6),
                "independent_score": round(independent_score, 6),
                "topic_score": round(candidates["active_topic"], 6),
                "previous_user_score": round(candidates["previous_user"], 6),
                "previous_april_score": round(candidates["previous_april"], 6),
                "active_goal_score": round(candidates["active_goal"], 6),
            },
        }

    def fast_semantic_profile(self, current: Any, **kwargs: Any) -> dict[str, Any]:
        return self.turn_measurement(
            current,
            previous_user=kwargs.get("previous_user") or "",
            previous_april=kwargs.get("previous_april") or "",
            active_topic=kwargs.get("active_topic") or "",
            active_goal=kwargs.get("active_goal") or "",
        )


QUANTUM_EMBEDDING_ENGINE = QuantumEmbeddingEngine()


def get_shared_semantic_encoder():
    """Compatibility API: one shared measurement object, no second model."""
    return QUANTUM_EMBEDDING_ENGINE


def _semantic_similarity(left: Any, right: Any) -> float:
    return QUANTUM_EMBEDDING_ENGINE.similarity(left, right)


def _dialogue_tokens(value: Any) -> set[str]:
    return QUANTUM_EMBEDDING_ENGINE.tokens(value)


def _extract_topic(value: Any) -> str:
    """
    Derive a compact topic anchor from the current user utterance.

    It is not a routing classifier.  The result is only the semantic anchor
    of a dialogue vector and is deliberately conservative.
    """
    text = _clean_text(value)
    if not text:
        return ""

    phrase = text
    # Prefer the object after an explicit discourse preposition when it exists.
    match = re.search(r"\b(?:про|об|о|насч[её]т|касательно)\b\s+(.+)$", text, re.I)
    if match:
        phrase = match.group(1)

    raw = re.findall(r"[A-Za-zА-Яа-яЁё0-9_-]{3,}", phrase)
    kept = []
    for item in raw:
        low = item.lower().strip("_-")
        if low in _DIALOGUE_STOPWORDS:
            continue
        if low in {"расскажи", "рассказать", "скажи", "покажи", "можешь",
                   "можно", "нужно", "надо", "теперь", "дальше", "ещё",
                   "еще", "про", "это", "такое", "такой", "какой", "какая",
                   "какие", "кто", "что", "почему", "зачем", "как"}:
            continue
        kept.append(item)

    if not kept:
        # Fall back to the whole turn when it contains no extracted object.
        kept = [
            item for item in raw
            if item.lower() not in _DIALOGUE_STOPWORDS
        ]

    return " ".join(kept[:8]).strip()[:300]


def _is_reference_turn(text: Any) -> bool:
    low = _clean_text(text).lower()
    if any(phrase in low for phrase in _REFERENCE_PHRASES):
        return True
    # Possessive/reflexive forms resolve an entity from the active vector even
    # when the sentence is otherwise self-contained: "его карьера", "её
    # компания", "о нём", "он родился". This is discourse continuity, not a
    # request to retrieve an unrelated old topic.
    if re.search(
        r"\b(?:его|ее|её|него|нему|ним|ему|ей|ней|неё|он|она|они)\b",
        low,
    ):
        return True
    tokens = set(re.findall(r"[a-zа-яё]+", low))
    return bool(tokens & {
        "помнишь", "предыдущ", "прошлый", "прошлая", "прошлое", "раньше",
        "тогда", "продолжи", "продолжим",
    })


def _explicit_new_topic(text: Any) -> bool:
    low = _clean_text(text).lower()
    return any(marker in low for marker in _EXPLICIT_NEW_MARKERS)


def _explicit_memory_recall(text: Any) -> bool:
    low = _clean_text(text).lower()
    markers = (
        "вернемся", "вернёмся", "вернись", "вернись к",
        "помнишь", "предыдущ", "прошлый", "прошлая", "прошлое",
        "раньше", "как тогда", "как раньше", "возвращаясь к",
    )
    return any(marker in low for marker in markers)


def _collect_7d_dialogue(state: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(state, dict):
        return []

    scope = state.get("memory_scope") if isinstance(state.get("memory_scope"), dict) else {}
    user_id = str(scope.get("user_id") or state.get("user_id") or "").strip()
    conversation_id = str(
        scope.get("conversation_id") or state.get("conversation_id") or ""
    ).strip()

    timeline = state.get("memory_timeline")
    if not isinstance(timeline, dict):
        return []

    now = time.time()
    ttl = 7 * 24 * 60 * 60
    records: list[dict[str, Any]] = []

    for day_index in range(7):
        day = timeline.get(f"day_{day_index}")
        if not isinstance(day, dict):
            continue
        for item in day.get("dialog_pairs") or []:
            if not isinstance(item, dict):
                continue
            if user_id and item.get("user_id") and str(item.get("user_id")) != user_id:
                continue
            if conversation_id and item.get("conversation_id") and str(item.get("conversation_id")) != conversation_id:
                continue
            created = item.get("created_at") or item.get("timestamp") or 0
            try:
                created = float(created)
            except Exception:
                created = 0.0
            if created and now - created >= ttl:
                continue

            record = dict(item)
            record["day_index"] = day_index
            records.append(record)

    # Hot dialog is a compatibility source when the canonical pair ledger is
    # temporarily empty (e.g. the very first request after a restore).
    if not records:
        dialog = state.get("dialog") if isinstance(state.get("dialog"), list) else []
        user_turn = ""
        april_turn = ""
        for item in reversed(dialog[-12:]):
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").lower()
            content = _clean_text(
                item.get("content") or item.get("text") or item.get("answer")
            )
            if role in {"assistant", "april", "bot"} and not april_turn:
                april_turn = content
            elif role in {"user", "human"} and not user_turn:
                user_turn = content
            if user_turn and april_turn:
                break
        if user_turn:
            records.append({
                "record_type": "dialog_pair",
                "user_request": user_turn,
                "april_answer": april_turn,
                "user_meaning": user_turn,
                "april_meaning": april_turn,
                "created_at": now,
                "day_index": 0,
            })

    records.sort(
        key=lambda item: float(item.get("created_at") or item.get("timestamp") or 0.0)
    )
    return records


def _active_sequence(state: dict[str, Any], pairs: list[dict[str, Any]]) -> dict[str, Any]:
    active = state.get("active_dialogue_sequence")
    if isinstance(active, dict) and active.get("sequence_id"):
        return dict(active)

    for item in reversed(pairs):
        sequence_id = _clean_text(item.get("sequence_id"))
        if sequence_id:
            return {
                "sequence_id": sequence_id,
                "topic": _clean_text(item.get("topic") or item.get("user_meaning")),
                "user_id": _clean_text(item.get("user_id") or state.get("user_id")),
                "conversation_id": _clean_text(
                    item.get("conversation_id") or state.get("conversation_id")
                ),
                "turn_count": 0,
                "last_turn_at": item.get("created_at"),
                "restored": True,
            }

    last_user = _clean_text(state.get("last_user_turn"))
    if last_user:
        topic = _extract_topic(last_user) or last_user[:200]
        seed = (
            f"{state.get('user_id','')}|{state.get('conversation_id','')}|{topic}"
        )
        return {
            "sequence_id": "seq-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20],
            "topic": topic,
            "user_id": _clean_text(state.get("user_id")),
            "conversation_id": _clean_text(state.get("conversation_id")),
            "turn_count": 0,
            "last_turn_at": state.get("last_user_turn_at"),
            "restored": True,
        }

    return {}


def _sequence_pairs(pairs: list[dict[str, Any]], sequence_id: str) -> list[dict[str, Any]]:
    if not sequence_id:
        return []
    selected = [
        item for item in pairs
        if _clean_text(item.get("sequence_id")) == sequence_id
    ]
    selected.sort(
        key=lambda item: float(item.get("created_at") or item.get("timestamp") or 0.0)
    )
    return selected


def _new_vector_id(state: dict[str, Any], topic: str, text: str) -> str:
    raw = (
        f"{state.get('user_id','')}|{state.get('conversation_id','')}|"
        f"{time.time_ns()}|{topic}|{text}"
    )
    return "seq-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _best_historical_pair(
    current_text: str,
    pairs: list[dict[str, Any]],
    active_sequence_id: str,
) -> tuple[int, dict[str, Any], float]:
    best_index = -1
    best_record: dict[str, Any] = {}
    best_score = 0.0
    for index, record in enumerate(pairs):
        if _clean_text(record.get("sequence_id")) == active_sequence_id:
            continue
        source = " ".join(
            str(record.get(key) or "")
            for key in ("topic", "user_meaning", "april_meaning", "answer_summary")
        )
        score = _semantic_similarity(current_text, source)
        if score > best_score:
            best_index = index
            best_record = record
            best_score = score
    return best_index, best_record, best_score


class QuantumInterpretationEngine:
    """
    Canonical dialogue-vector interpreter for the deployed ZIP.

    Invariant:
      one authenticated user -> one active dialogue vector -> many turns.
      A new vector is created only when the current turn is strongly novel or
      the user explicitly asks to change topic.  The new vector then becomes
      the active sequence and future turns continue it until another vector
      transition is measured.
    """

    VERSION = "quantum_dialogue_interpretation_7d_v1"

    def _semantic_relation(
        self,
        text: str,
        state: dict[str, Any],
        history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        pairs = _collect_7d_dialogue(state)
        if history:
            # The provided history is a hot compatibility view, not a second
            # memory store.  Canonical seven-day pairs remain authoritative.
            if not pairs:
                pairs = [h for h in history if isinstance(h, dict)]

        active = _active_sequence(state, pairs)
        active_sequence_id = _clean_text(active.get("sequence_id"))
        active_topic = _clean_text(active.get("topic"))

        sequence_pairs = _sequence_pairs(pairs, active_sequence_id)
        latest = sequence_pairs[-1] if sequence_pairs else (pairs[-1] if pairs else {})
        latest_user = _clean_text(
            latest.get("user_request")
            or latest.get("user_meaning")
            or state.get("last_user_turn")
        )
        latest_april = _clean_text(
            latest.get("april_answer")
            or latest.get("april_meaning")
            or state.get("last_april_turn")
        )

        if not active_topic:
            active_topic = (
                _clean_text(latest.get("topic"))
                or _extract_topic(latest_user)
                or _extract_topic(text)
                or ""
            )

        reference = _is_reference_turn(text)
        explicit_new = _explicit_new_topic(text)
        current_topic = _extract_topic(text)

        topic_similarity = max(
            _semantic_similarity(text, active_topic),
            _semantic_similarity(current_topic, active_topic) if current_topic and active_topic else 0.0,
            _semantic_similarity(text, latest_user) if latest_user else 0.0,
            _semantic_similarity(text, latest_april) if latest_april else 0.0,
        )

        topic_novelty = _semantic_similarity(current_topic, active_topic) if (
            current_topic and active_topic
        ) else 0.0

        low = text.lower()
        explicit_object_change = bool(
            re.search(r"\b(?:про|об|о)\s+[A-Za-zА-Яа-яЁё][\w-]*(?:\s+[A-Za-zА-Яа-яЁё][\w-]*)?", text)
        )
        proper_nouns = [
            value for value in re.findall(r"\b[А-ЯЁA-Z][а-яёa-z-]{2,}\b", text)
            if value.lower() not in _DIALOGUE_STOPWORDS
        ]
        proper_novelty = bool(proper_nouns and topic_similarity < 0.44)

        # A historical recall is only meaningful when the utterance explicitly
        # points backward.  It does not force a new topic by itself.
        recall_index, recall_record, recall_score = _best_historical_pair(
            text, pairs, active_sequence_id
        )

        explicit_recall = _explicit_memory_recall(text)
        if explicit_new:
            relation = "NEW"
            reason = "explicit_new_topic"
            confidence = 0.99
        elif explicit_recall and recall_score >= 0.40 and recall_score > topic_similarity + 0.06 and recall_record:
            relation = "RECALL"
            reason = "explicit_memory_recall"
            confidence = max(0.72, min(0.97, recall_score))
        elif not active_sequence_id:
            relation = "NEW"
            reason = "no_active_dialogue_vector"
            confidence = 0.99
        elif (
            explicit_object_change
            and not reference
            and topic_novelty < 0.34
            and proper_novelty
        ):
            relation = "NEW"
            reason = "strong_new_subject"
            confidence = max(0.72, min(0.95, 1.0 - topic_novelty))
        elif (
            explicit_object_change
            and not reference
            and topic_novelty < 0.18
            and len(_dialogue_tokens(current_topic)) >= 1
            and topic_similarity < 0.30
        ):
            relation = "NEW"
            reason = "new_object_phrase"
            confidence = 0.86
        else:
            # Canonical default: an authenticated user's active sequence stays
            # alive.  A new vector requires explicit topic change or strong
            # semantic novelty evidence above.
            relation = "CONTINUE"
            reason = (
                "reference_to_active_vector"
                if reference
                else "active_vector_default_continuation"
            )
            confidence = max(0.62, min(0.96, 0.62 + 0.30 * topic_similarity))
            if any(marker in low for marker in _FOLLOWUP_MARKERS):
                confidence = max(confidence, 0.78)

        selected = {}
        selected_index = -1
        if relation == "RECALL" and recall_record:
            selected = dict(recall_record)
            selected_index = recall_index
        elif sequence_pairs:
            selected = dict(sequence_pairs[-1])
            selected_index = next(
                (
                    index
                    for index in range(len(pairs) - 1, -1, -1)
                    if isinstance(pairs[index], dict)
                    and (
                        (
                            selected.get("turn_key")
                            and pairs[index].get("turn_key") == selected.get("turn_key")
                        )
                        or (
                            selected.get("created_at")
                            and pairs[index].get("created_at") == selected.get("created_at")
                            and pairs[index].get("user_request") == selected.get("user_request")
                        )
                    )
                ),
                max(0, len(pairs) - 1),
            )
        elif latest:
            selected = dict(latest)
            selected_index = max(0, len(pairs) - 1)

        selected_sequence_id = _clean_text(selected.get("sequence_id") or active_sequence_id)
        selected_topic = _clean_text(
            selected.get("topic")
            or active_topic
            or current_topic
        )

        target_sequence_id = selected_sequence_id or active_sequence_id
        if relation == "NEW":
            target_sequence_id = _new_vector_id(
                state,
                current_topic or _extract_topic(text) or text[:180],
                text,
            )

        resolved_reference = ""
        if reference and selected:
            resolved_reference = _clean_text(
                selected.get("user_request")
                or selected.get("user_meaning")
                or selected.get("topic")
            )

        return {
            "relation": relation,
            "confidence": round(confidence, 6),
            "reason": reason,
            "active_sequence": active,
            "active_sequence_id": active_sequence_id,
            "target_sequence_id": target_sequence_id,
            "active_topic": active_topic,
            "target_topic": (
                current_topic
                if relation == "NEW"
                else selected_topic
                if relation == "RECALL"
                else active_topic or current_topic
            ),
            "current_topic": current_topic,
            "previous_user_turn": latest_user,
            "previous_april_turn": latest_april,
            "topic_similarity": round(topic_similarity, 6),
            "topic_novelty": round(topic_novelty, 6),
            "reference": reference,
            "explicit_recall": explicit_recall,
            "explicit_new": explicit_new,
            "selected_memory_index": selected_index,
            "selected_memory_operand": selected,
            "resolved_reference": resolved_reference,
            "sequence_pairs": sequence_pairs[-6:],
        }

    @staticmethod
    def _infer_representation(text: str) -> str:
        low = text.lower()
        if re.search(r"\b(код|python|пайтон|скрипт)\b", low):
            return "code"
        if re.search(r"\b(ссыл\w*|url|link)\b", low):
            return "link"
        if re.search(r"\b(нарисуй|изобрази|сгенерируй|создай)\b", low) or "картинк" in low or "изображени" in low or "портрет" in low:
            return "image"
        if re.search(r"\b(график|графика|кривую|кривая)\b", low):
            return "graph"
        if re.search(r"\b(таблиц\w*|табличк\w*)\b", low):
            return "table"
        if re.search(r"\b(схем\w*|блок-схем\w*)\b", low):
            return "diagram"
        if re.search(r"\b(формул\w*|уравнени\w*)\b", low):
            return "formula"
        return "text"

    @staticmethod
    def _operation(text: str, representation: str) -> str:
        low = text.lower()
        if representation == "link":
            return "retrieve"
        if any(word in low for word in ("измени", "исправь", "переделай", "добавь", "убери", "сделай")):
            return "modify"
        if representation in {"code", "graph", "table", "diagram", "image", "gallery", "formula"}:
            return "build"
        if any(word in low for word in ("объясни", "расскажи", "почему", "что такое", "кто такой", "кто это")):
            return "explain"
        return "answer"

    @staticmethod
    def _goal(operation: str, representation: str) -> str:
        if operation == "retrieve":
            return "obtain"
        if representation in {"code", "graph", "table", "diagram", "image", "gallery", "formula"}:
            return "present"
        if operation == "explain":
            return "understand"
        return "answer"

    @staticmethod
    def _object(text: str, representation: str, topic: str) -> str:
        if representation == "link" and ("telegram" in text.lower() or "телеграм" in text.lower()):
            return "telegram_link"
        if topic:
            return topic
        return {
            "code": "source_code",
            "image": "illustration",
            "graph": "graph",
            "table": "table",
            "diagram": "diagram",
            "formula": "formula",
            "link": "link",
        }.get(representation, "text")

    def interpret(
        self,
        text,
        cognition=None,
        semantic=None,
        history=None,
        state=None,
    ) -> dict[str, Any]:
        del cognition, semantic
        current = _clean_text(text)
        state = state if isinstance(state, dict) else {}
        history = history if isinstance(history, list) else []

        relation = self._semantic_relation(current, state, history)
        relation_name = relation["relation"]

        raw_representation = self._infer_representation(current)
        active_sequence = relation.get("active_sequence") or {}
        active_sequence_pairs = relation.get("sequence_pairs") or []

        active_representation = ""
        if active_sequence_pairs:
            last = active_sequence_pairs[-1]
            types = last.get("render_block_types") or last.get("requested_outputs") or []
            if isinstance(types, list):
                for item in types:
                    candidate = _clean_text(item).lower()
                    if candidate and candidate != "text":
                        active_representation = candidate
                        break
        if not active_representation:
            active_representation = _clean_text(
                (state.get("april_active_task") or {}).get("representation")
                if isinstance(state.get("april_active_task"), dict)
                else ""
            ).lower()

        representation = raw_representation
        if relation_name in {"CONTINUE", "RECALL"} and representation == "text" and active_representation:
            # Follow-up turns inherit the representation only when the current
            # user request did not explicitly select another representation.
            representation = active_representation

        operation = self._operation(current, representation)
        goal = self._goal(operation, representation)

        active_topic = _clean_text(relation.get("active_topic"))
        target_topic = _clean_text(relation.get("target_topic") or active_topic)
        if relation_name == "NEW":
            topic = _extract_topic(current) or target_topic or current[:180]
        elif relation_name == "RECALL":
            topic = target_topic or active_topic or _extract_topic(current)
        else:
            topic = active_topic or target_topic or _extract_topic(current)

        object_name = self._object(current, representation, topic)

        selected = relation.get("selected_memory_operand") or {}
        selected_user = _clean_text(
            selected.get("user_request") or selected.get("user_meaning")
        )
        selected_april = _clean_text(
            selected.get("april_answer") or selected.get("april_meaning") or selected.get("answer_summary")
        )

        sequence_id = _clean_text(relation.get("target_sequence_id"))
        request_relation = (
            "CONTINUE_TOPIC" if relation_name == "CONTINUE"
            else "ARTIFACT_REFERENCE" if relation_name == "RECALL" and relation.get("reference")
            else "MEMORY_QUERY" if relation_name == "RECALL"
            else "NEW_TOPIC"
        )
        context_dependency = (
            "continuation" if relation_name == "CONTINUE"
            else "recall" if relation_name == "RECALL"
            else "independent"
        )

        semantic_task = {
            "operation": operation,
            "object": object_name,
            "representation": representation,
            "goal": goal,
            "topic": topic,
        }

        dialogue_vector = {
            "version": self.VERSION,
            "relation": request_relation,
            "topic_relation": request_relation,
            "request_relation": request_relation,
            "request_dependency": context_dependency,
            "context_dependency": context_dependency,
            "continuation": relation_name == "CONTINUE",
            "reference_to_previous": bool(relation_name == "RECALL" or relation.get("reference")),
            "three_way_relation": relation_name,
            "three_way_confidence": relation["confidence"],
            "semantic_dialogue_label": (
                "continuation" if relation_name == "CONTINUE"
                else "recall" if relation_name == "RECALL"
                else "new"
            ),
            "confidence": relation["confidence"],
            "active_topic": active_topic,
            "canonical_topic": topic,
            "sequence_id": sequence_id,
            "target_sequence_id": sequence_id,
            "previous_user_turn": relation.get("previous_user_turn", ""),
            "previous_april_turn": relation.get("previous_april_turn", ""),
            "resolved_reference": relation.get("resolved_reference", ""),
            "selected_memory_index": relation.get("selected_memory_index", -1),
            "selected_memory_operand": selected,
            "topic_similarity": relation.get("topic_similarity", 0.0),
            "topic_novelty": relation.get("topic_novelty", 0.0),
            "sequence_continuation_authorized": relation_name == "CONTINUE",
            "current_turn_authority": True,
            "historical_memory_is_evidence_only": True,
            "sequential_dialogue": {
                "relation": relation_name,
                "subtype": request_relation,
                "continuation": relation_name == "CONTINUE",
                "reference": relation_name == "RECALL",
                "confidence": relation["confidence"],
                "selected_pair": selected,
                "selected_index": relation.get("selected_memory_index", -1),
                "sequence_id": sequence_id,
                "scores": {
                    "topic_similarity": relation.get("topic_similarity", 0.0),
                    "topic_novelty": relation.get("topic_novelty", 0.0),
                    "reference_semantics": 1.0 if relation.get("reference") else 0.0,
                },
            },
        }

        if relation_name == "CONTINUE":
            continuation_target = {
                "sequence_id": sequence_id,
                "topic": topic,
                "turns_considered": len(active_sequence_pairs),
            }
        else:
            continuation_target = {}

        requested_outputs = [representation if representation != "text" else "text"]
        scene_composition = list(requested_outputs)
        if representation != "text" and "text" not in scene_composition:
            scene_composition.insert(0, "text")

        return {
            "type": "text" if representation == "text" else representation,
            "subtype": representation,
            "scene_type": representation,
            "operation": operation,
            "best_operation": operation,
            "object": object_name,
            "best_object": object_name,
            "goal": goal,
            "best_goal": goal,
            "representation": representation,
            "production": representation,
            "visual_production_mode": (
                "image_generation" if representation == "image" and re.search(
                    r"\b(нарисуй|изобрази|сгенерируй|создай)\b", current.lower()
                ) else representation
            ),
            "resolved_request": current,
            "request_operand": current,
            "request_operand_source": "current_user_turn",
            "request_operand_sanitized": True,
            "current_request": current,
            "normalized": current,
            "normalized_text": current,
            "active_topic": topic,
            "active_goal": goal,
            "canonical_topic": topic,
            "continuation": relation_name == "CONTINUE",
            "reference_to_previous": bool(relation_name == "RECALL" or relation.get("reference")),
            "dialogue_relation": relation_name,
            "relation": request_relation,
            "request_relation": request_relation,
            "request_dependency": context_dependency,
            "context_dependency": context_dependency,
            "history_dependent_task": relation_name in {"CONTINUE", "RECALL"},
            "history_available": bool(relation.get("previous_user_turn") or relation.get("previous_april_turn") or relation.get("sequence_pairs")),
            "current_turn_complete": True,
            "current_request_complete": True,
            "explicit_task": bool(raw_representation != "text"),
            "sequence_continuation_authorized": relation_name == "CONTINUE",
            "continuation_target": continuation_target,
            "selected_memory_index": relation.get("selected_memory_index", -1),
            "selected_memory_operand": selected,
            "dialogue_reference": (
                {
                    "resolved": bool(relation.get("resolved_reference")),
                    "target": relation.get("resolved_reference", ""),
                    "confidence": relation["confidence"],
                    "anaphoric": bool(relation.get("reference")),
                }
                if relation_name == "RECALL"
                else {}
            ),
            "dialogue_delta": {
                "mode": "CONTINUE" if relation_name == "CONTINUE" else "NEW_VECTOR" if relation_name == "NEW" else "RECALL_VECTOR",
                "shared_tokens": sorted(_dialogue_tokens(current) & _dialogue_tokens(topic))[:12],
                "new_tokens": sorted(_dialogue_tokens(current) - _dialogue_tokens(topic))[:12],
            },
            "semantic_task": semantic_task,
            "requested_outputs": requested_outputs,
            "requested_representations": requested_outputs,
            "required_representations": requested_outputs,
            "candidate_representations": requested_outputs,
            "scene_composition": scene_composition,
            "dialogue_vector": dialogue_vector,
            "dialogue_contract": {
                "version": self.VERSION,
                "relation": relation_name,
                "continuation": relation_name == "CONTINUE",
                "reference_to_previous": bool(relation_name == "RECALL" or relation.get("reference")),
                "context_dependency": context_dependency,
                "dialog_act": (
                    "continuation" if relation_name == "CONTINUE"
                    else "memory_query" if relation_name == "RECALL"
                    else "request"
                ),
                "active_topic": topic,
                "active_goal": goal,
                "canonical_topic": topic,
                "sequence_id": sequence_id,
                "resolved_request": current,
                "resolved_reference": relation.get("resolved_reference", ""),
                "previous_user_turn": relation.get("previous_user_turn", ""),
                "previous_april_turn": relation.get("previous_april_turn", ""),
                "selected_memory_index": relation.get("selected_memory_index", -1),
                "selected_memory_operand": selected,
                "trajectory": {
                    "sequence_id": sequence_id,
                    "topic": topic,
                    "relation_reason": relation.get("reason"),
                    "topic_similarity": relation.get("topic_similarity", 0.0),
                },
                "semantic_authority": True,
            },
            "trajectory": {
                "sequence_id": sequence_id,
                "topic": topic,
                "relation_reason": relation.get("reason"),
                "topic_similarity": relation.get("topic_similarity", 0.0),
            },
            "render_continuity": {
                "relation": relation_name,
                "reuse_existing_scene": relation_name == "CONTINUE",
                "reuse_recalled_memory": relation_name == "RECALL",
                "selected_memory_index": relation.get("selected_memory_index", -1),
                "previous_scene_id": _clean_text(selected.get("visual_scene_id") or selected.get("scene_id")),
                "previous_render_types": list(selected.get("render_block_types") or []),
                "avoid_repeat": True,
            },
            "compatibility_version": self.VERSION,
        }



# One shared semantic namespace for the existing modules.
QUANTUM_EVIDENCE_FUSION = QUANTUM_EMBEDDING_ENGINE
_LOCAL_INTERPRETATION_ENGINE = QuantumInterpretationEngine()

# ---------------------------------------------------------------------------
# Conservative no-crash engine
# ---------------------------------------------------------------------------

class _FallbackInterpretationEngine:
    """
    Last-resort TEXT-only interpretation.

    It exists solely so a deployment with a missing canonical engine file does
    not crash during import. It does not invent a renderer or a second semantic
    route.
    """

    VERSION = "fallback-text-only-compat-v1"

    @staticmethod
    def interpret(
        text,
        cognition=None,
        semantic=None,
        history=None,
        state=None,
    ) -> dict[str, Any]:
        current = _clean_text(text)

        return {
            "type": "independent",
            "subtype": "text",
            "scene_type": "text",
            "operation": "answer",
            "best_operation": "answer",
            "object": "text",
            "best_object": "text",
            "goal": "understand",
            "best_goal": "understand",
            "representation": "text",
            "production": "text",
            "visual_production_mode": "text",
            "resolved_request": current,
            "request_operand": current,
            "request_operand_source": "current_user_turn",
            "request_operand_sanitized": True,
            "current_request": current,
            "normalized": current,
            "normalized_text": current,
            "continuation": False,
            "reference_to_previous": False,
            "dialogue_relation": "NEW",
            "relation": "NEW_TOPIC",
            "request_dependency": "independent",
            "context_dependency": "independent",
            "history_dependent_task": False,
            "requested_outputs": ["text"],
            "requested_representations": ["text"],
            "dialogue_vector": {
                "relation": "NEW_TOPIC",
                "topic_relation": "NEW_TOPIC",
                "request_relation": "NEW_TOPIC",
                "request_dependency": "independent",
                "continuation": False,
                "reference_to_previous": False,
                "three_way_relation": "NEW",
                "resolved_request": current,
                "request_operand": current,
                "request_operand_source": "current_user_turn",
                "historical_memory_is_evidence_only": True,
                "current_turn_authority": True,
                "sequential_dialogue": {
                    "relation": "NEW",
                    "subtype": "NEW_TOPIC",
                    "continuation": False,
                    "reference": False,
                    "selected_pair": {},
                },
            },
            "presentation": {
                "production_representation": "text",
                "signals": [],
                "recommendations": [],
                "scene_plan": [],
                "stale_context_cannot_upgrade_current_representation": True,
            },
            "fallback_interpretation_engine": True,
            "fallback_reason": "canonical_engine_module_not_deployed",
        }

    def measure(self, text: Any) -> dict[str, Any]:
        return {"text": _clean_text(text)}

    def dialogue(self, text: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "dialogue": {
                "label": "independent",
                "continuation_score": 0.0,
                "reference_score": 0.0,
                "confidence": 1.0,
                "topic_score": 0.0,
            }
        }


_FALLBACK_ENGINE = _FallbackInterpretationEngine()


# ---------------------------------------------------------------------------
# Public API expected by executor.py
# ---------------------------------------------------------------------------

def interpret_request(
    text,
    cognition=None,
    semantic=None,
    history=None,
    state=None,
):
    """
    Public compatibility entrypoint.

    Normal path:
        blocks.interpretation_layer
          -> lazily discovered canonical Quantum engine
          -> repair/safety fence

    Emergency path:
        missing canonical module
          -> conservative text-only result
    """
    module = _load_canonical_engine_module()

    if module is not None:
        engine = getattr(module, "QUANTUM_INTERPRETATION_ENGINE", None)
        if engine is not None and callable(getattr(engine, "interpret", None)):
            result = engine.interpret(
                text,
                cognition=cognition,
                semantic=semantic,
                history=history,
                state=state,
            )
            return _repair_interpretation_result(result, text)

    # The deployed ZIP currently contains no separate canonical interpretation
    # module, so the built-in seven-day engine is the canonical engine in this
    # package. The conservative text-only fallback remains as the final no-crash
    # path only if this engine itself fails unexpectedly.
    try:
        result = _LOCAL_INTERPRETATION_ENGINE.interpret(
            text,
            cognition=cognition,
            semantic=semantic,
            history=history,
            state=state,
        )
    except Exception as exc:
        result = _FALLBACK_ENGINE.interpret(
            text,
            cognition=cognition,
            semantic=semantic,
            history=history,
            state=state,
        )
        result["local_engine_error"] = f"{type(exc).__name__}: {exc}"
    return _repair_interpretation_result(result, text)


def _base_interpret_request(
    text,
    cognition=None,
    semantic=None,
    history=None,
    state=None,
):
    return interpret_request(
        text,
        cognition=cognition,
        semantic=semantic,
        history=history,
        state=state,
    )


# ---------------------------------------------------------------------------
# Compatibility builders retained as thin views
# ---------------------------------------------------------------------------

def build_semantic_dialog_profile(
    text,
    cognition=None,
    semantic=None,
    assistant_response=None,
    dialogue_history=None,
    vision_context=None,
):
    cognition = _as_dict(cognition)
    semantic = _as_dict(semantic)

    return {
        "input_text": _clean_text(text),
        "assistant_response": assistant_response,
        "dialogue_history": dialogue_history or [],
        "vision_context": vision_context or {},
        "active_goal": cognition.get("active_goal") or semantic.get("active_goal"),
        "active_topic": cognition.get("active_topic_slot")
        or semantic.get("current_topic"),
        "semantic_state": semantic,
        "requires_scene_builder": False,
        "profile_version": "current_turn_boundary_v2",
    }


def build_scene_construction_profile(semantic_profile):
    return {
        "requires_scene_builder": False,
        "scene_type": "dialogue",
        "dialogue_mode": "semantic_unified",
        "context_source": "quantum_matrix",
        "decision_owner": "QUANTUM_PROCESSOR",
        "profile_version": "current_turn_boundary_v2",
    }


def build_scene_artifact_contract(
    semantic_profile,
    scene_profile,
):
    return {
        "contract": "scene_artifact",
        "transport": "INTERPRETATION_TRANSPORT",
        "semantic_profile": semantic_profile or {},
        "scene_profile": scene_profile or {},
        "representation": "processor_decides",
        "profile_version": "current_turn_boundary_v2",
    }


def build_unified_scene_context(
    semantic_profile,
    scene_profile,
    artifact_contract,
    voice_context=None,
    vision_context=None,
    gallery_context=None,
    file_context=None,
    assistant_response=None,
    dialogue_history=None,
    memory_state=None,
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
            "transport": "INTERPRETATION_TRANSPORT",
            "scene_contract": "canonical",
        },
        "profile_version": "current_turn_boundary_v2",
    }


# ---------------------------------------------------------------------------
# Lazy module attribute delegation
# ---------------------------------------------------------------------------

def __getattr__(name: str) -> Any:
    """
    Preserve compatibility with legacy code importing helper symbols from this
    module. Nothing is resolved until that symbol is actually requested.
    """
    module = _load_canonical_engine_module()

    if module is not None and hasattr(module, name):
        return getattr(module, name)

    fallback_public = {
        "normalize_text": lambda value: _clean_text(value),
        "normalize_lower": lambda value: _clean_text(value).lower(),
        "DECISION_OWNER": "QUANTUM_PROCESSOR",
        "TRANSPORT_NAME": "INTERPRETATION_TRANSPORT",
        "INTERPRETATION_COMPATIBILITY_VERSION":
            "2026-09-21-lazy-engine-current-turn-fence-v3",
        "get_shared_semantic_encoder": get_shared_semantic_encoder,
        "QUANTUM_EMBEDDING_ENGINE": QUANTUM_EMBEDDING_ENGINE,
        "QUANTUM_EVIDENCE_FUSION": QUANTUM_EVIDENCE_FUSION,
    }

    if name in fallback_public:
        return fallback_public[name]

    if hasattr(_FALLBACK_ENGINE, name):
        return getattr(_FALLBACK_ENGINE, name)

    raise AttributeError(
        f"module {_THIS_MODULE!r} has no attribute {name!r}"
    )


INTERPRETATION_COMPATIBILITY_VERSION = (
    "2026-09-21-seven-day-dialogue-vector-v1"
)
INTERPRETATION_REQUEST_OPERAND_POLICY = "CURRENT_USER_TURN_ONLY"
INTERPRETATION_HISTORICAL_MEMORY_POLICY = "SEVEN_DAY_DIALOGUE_MEMORY_EVIDENCE"

__all__ = [
    "interpret_request",
    "_base_interpret_request",
    "build_semantic_dialog_profile",
    "build_scene_construction_profile",
    "build_scene_artifact_contract",
    "build_unified_scene_context",
    "QUANTUM_INTERPRETATION_ENGINE",
    "INTERPRETATION_COMPATIBILITY_VERSION",
    "INTERPRETATION_REQUEST_OPERAND_POLICY",
    "INTERPRETATION_HISTORICAL_MEMORY_POLICY",
]
