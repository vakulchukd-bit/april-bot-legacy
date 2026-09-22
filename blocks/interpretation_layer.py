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


# ---------------------------------------------------------------------------
# Canonical presentation/synchronization contract
# ---------------------------------------------------------------------------
# These structures are semantic/advisory only.  They do not dispatch renderers.
# The Executor remains the owner of SceneContract construction and RenderMessage
# remains the owner of actual visualization.

WEB_SUPPORTED_PAYLOADS = (
    "action", "audio", "code", "diagram", "file", "formula", "gallery",
    "graph", "image", "link", "markdown", "memory", "scene", "table",
    "text", "video", "visual_context",
)

PRESENTATION_RENDERERS = {
    "text": "MessageTextBlock",
    "code": "CodeBlock",
    "graph": "GraphBlock",
    "diagram": "GalleryBlock",
    "image": "GalleryBlock",
    "gallery": "GalleryBlock",
    "link": "LinkCard",
    "table": "TableBlock",
    "formula": "MessageTextBlock",
    "file": "LinkCard",
    "audio": "MessageTextBlock",
    "video": "MessageTextBlock",
    "action": "MessageTextBlock",
    "scene": "GalleryBlock",
    "memory": "MessageTextBlock",
    "visual_context": "GalleryBlock",
}

PRESENTATION_LABELS = {
    "text": "textual answer",
    "code": "executable code",
    "graph": "graph/chart",
    "diagram": "diagram or geometric construction",
    "image": "image",
    "gallery": "image gallery",
    "link": "link cards",
    "table": "table",
    "formula": "mathematical notation",
    "file": "file/resource",
    "audio": "audio",
    "video": "video",
    "action": "interactive action",
    "scene": "visual scene",
    "memory": "memory explanation",
    "visual_context": "visual context",
}

PRESENTATION_SCENE_PROFILES = {
    "text": ("explanation", "message", "human-readable answer"),
    "code": (
        "code_example", "message_intro -> code -> message_explanation",
        "source code plus implementation context",
    ),
    "graph": (
        "data_visualization", "message_intro -> graph -> message_explanation",
        "series, axes, labels, units and requested ranges",
    ),
    "diagram": (
        "diagram_or_construction", "message_intro -> gallery_diagram -> message_explanation",
        "nodes/shapes/relations/dimensions and construction facts",
    ),
    "image": (
        "image", "message_intro -> gallery_image -> message_explanation",
        "generated or selected image with visual context",
    ),
    "gallery": (
        "image_collection", "message_intro -> gallery -> message_explanation",
        "ordered image collection with per-image meaning",
    ),
    "link": (
        "resource_links", "message_intro -> link_cards -> message_explanation",
        "URL, title and short purpose for each resource",
    ),
    "table": (
        "structured_data", "message_intro -> table -> message_explanation",
        "rows, columns, headers, units and values",
    ),
    "formula": (
        "mathematical_explanation", "message_intro -> message_formula -> message_explanation",
        "formula plus variable definitions and interpretation",
    ),
    "file": (
        "resource_file", "message_intro -> link_or_file -> message_explanation",
        "resource identity and purpose",
    ),
    "audio": (
        "audio", "message_intro -> audio_resource -> message_explanation",
        "audio resource metadata and purpose",
    ),
    "video": (
        "video", "message_intro -> video_resource -> message_explanation",
        "video resource metadata and purpose",
    ),
    "action": (
        "interactive_action", "message_intro -> action -> message_explanation",
        "action target, parameters and expected result",
    ),
    "scene": (
        "composite_visual_scene", "message_intro -> visual_scene -> message_explanation",
        "scene objects, spatial relations and visual semantics",
    ),
    "memory": (
        "memory_explanation", "message_intro -> message_explanation",
        "resolved prior context",
    ),
    "visual_context": (
        "visual_analysis", "message_intro -> gallery_context -> message_explanation",
        "visual evidence and interpretation",
    ),
}

_STRUCTURED_PRESENTATIONS = frozenset(
    x for x in WEB_SUPPORTED_PAYLOADS if x not in {"text", "markdown", "memory", "visual_context"}
)

_REPRESENTATION_ALIASES = {
    "chart": "graph", "plot": "graph", "график": "graph", "графики": "graph",
    "schematic": "diagram", "flowchart": "diagram", "схема": "diagram", "чертеж": "diagram",
    "чертёж": "diagram", "math": "formula", "equation": "formula",
    "url": "link", "link_card": "link", "media": "gallery",
}


def _presentation_representation(value: Any) -> str:
    value = _clean_text(value).lower()
    value = _REPRESENTATION_ALIASES.get(value, value)
    return value if value in WEB_SUPPORTED_PAYLOADS else ""


def _ordered_unique(values: Any) -> list[str]:
    out: list[str] = []
    for value in values if isinstance(values, (list, tuple, set)) else []:
        rep = _presentation_representation(value)
        if rep and rep not in out:
            out.append(rep)
    return out


def _current_turn_representation_mentions(text: Any) -> list[str]:
    """Extract explicit output-format evidence from the current turn only.

    This is intentionally limited to representation semantics.  It never decides
    dialogue relation, topic, room, or renderer dispatch.
    """
    low = _clean_text(text).lower()
    if not low:
        return []

    patterns = (
        ("code", r"\b(?:код|python|пайтон|скрипт)\b"),
        ("graph", r"\b(?:график(?:а|и)?|plot|chart)\b|\b(?:крив(?:ую|ая|ой))\b"),
        ("table", r"\bтаблиц\w*\b|\bтабличк\w*\b"),
        ("diagram", r"\b(?:схем\w*|чертеж\w*|чертёж\w*|блок[- ]?схем\w*)\b"),
        ("formula", r"\b(?:формул\w*|уравнени\w*)\b"),
        ("image", r"\b(?:изображени\w*|картинк\w*|фото|портрет\w*)\b"),
        ("gallery", r"\bгалере\w*\b"),
        ("link", r"\b(?:ссылк\w*|url|link)\b|https?://"),
        ("file", r"\bфайл\w*\b"),
        ("audio", r"\bауди\w*\b"),
        ("video", r"\b(?:видео|video)\b"),
        ("scene", r"\b(?:сцен\w*|визуальн\w* сцен\w*)\b"),
    )
    hits = []
    for rep, pattern in patterns:
        m = re.search(pattern, low, flags=re.I)
        if m:
            hits.append((m.start(), rep))
    hits.sort(key=lambda item: item[0])
    return [rep for _, rep in hits]


def _explicit_current_representations(text: Any) -> list[str]:
    mentions = _current_turn_representation_mentions(text)
    # Imperative drawing language is visual evidence, but its final type depends
    # on any explicit object noun.  A bare "нарисуй" therefore does not force image.
    low = _clean_text(text).lower()
    if not mentions and re.search(r"\b(?:нарисуй|изобрази|draw|show the graph|plot)\b", low):
        if re.search(r"\b(?:график|plot|chart)\b", low):
            mentions.append("graph")
        elif re.search(r"\b(?:схем\w*|чертеж\w*|чертёж\w*)\b", low):
            mentions.append("diagram")
        elif re.search(r"\b(?:картинк\w*|изображени\w*|портрет\w*|draw)\b", low):
            mentions.append("image")
    return list(dict.fromkeys(mentions))


def _presentation_authority(
    result: dict[str, Any],
    current_text: str,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve when memory is allowed to participate in output modality.

    Current-turn representation is authoritative.  A prior visual modality can
    be reused only for an actual artifact/reference continuation in the selected
    authenticated sequence.  Generic seven-day recall never upgrades a new turn.
    """
    explicit = _explicit_current_representations(current_text)
    requested = _ordered_unique(result.get("requested_outputs"))
    requested += [x for x in _ordered_unique(result.get("requested_representations")) if x not in requested]

    relation = _clean_text(
        result.get("dialogue_relation")
        or result.get("relation")
        or _as_dict(result.get("dialogue_vector")).get("three_way_relation")
    ).upper()
    operation = _clean_text(
        result.get("operation") or result.get("best_operation") or result.get("active_operation")
    ).lower()
    artifact_ref = bool(
        result.get("artifact_reference")
        or result.get("artifact_noun_signal")
        or result.get("reference_to_previous") and result.get("resolved_reference_type") == "artifact"
    )

    prior_types: list[str] = []
    scene = result.get("resolved_scene") if isinstance(result.get("resolved_scene"), dict) else {}
    seq = result.get("active_sequence") if isinstance(result.get("active_sequence"), dict) else {}
    for source in (scene, seq, state.get("active_visual_scene") if isinstance(state, dict) else None):
        if not isinstance(source, dict):
            continue
        for item in source.get("render_block_types") or source.get("presentation_types") or []:
            rep = _presentation_representation(item)
            if rep and rep not in prior_types:
                prior_types.append(rep)

    explicit_structured = [x for x in explicit if x in _STRUCTURED_PRESENTATIONS]
    requested_structured = [x for x in requested if x in _STRUCTURED_PRESENTATIONS]
    if explicit_structured:
        return {
            "mode": "CURRENT_TURN",
            "authorized": True,
            "representations": explicit_structured,
            "source": "current_turn_explicit_representation",
            "relation": relation,
        }

    # The engine may already have a single current-turn structured request.
    if requested_structured and bool(result.get("explicit_task")):
        return {
            "mode": "CURRENT_TURN",
            "authorized": True,
            "representations": requested_structured,
            "source": "current_turn_explicit_task",
            "relation": relation,
        }

    # Only a real artifact continuation can inherit a prior render modality.
    if relation in {"CONTINUE", "RECALL", "CONTINUE_TOPIC"} and artifact_ref and prior_types:
        if operation in {"modify", "build", "present", "calculate", "analyze", "retrieve"} or re.search(
            r"\b(?:добавь|убери|измени|исправь|переделай|продли|продолжи|перерисуй|обнови|покажи)\b",
            _clean_text(current_text).lower(),
        ):
            return {
                "mode": "ARTIFACT_CONTINUATION",
                "authorized": True,
                "representations": [x for x in prior_types if x in _STRUCTURED_PRESENTATIONS],
                "source": "active_visual_scene_artifact_continuation",
                "relation": relation,
            }

    return {
        "mode": "TEXT_ONLY",
        "authorized": False,
        "representations": [],
        "source": "current_turn_text_no_structured_authority",
        "relation": relation,
    }


def _presentation_recommendations_from_reps(
    current_text: str,
    representations: list[str],
    *,
    production: str = "text",
    continuation: bool = False,
    previous_scene: dict[str, Any] | None = None,
    scores: dict[str, Any] | None = None,
    explicit: list[str] | None = None,
) -> list[dict[str, Any]]:
    scores = scores if isinstance(scores, dict) else {}
    explicit_set = set(explicit or [])
    reps = [x for x in _ordered_unique(representations) if x in WEB_SUPPORTED_PAYLOADS]
    if any(x != "text" for x in reps) and "text" not in reps:
        reps = ["text"] + reps
    if not reps:
        reps = ["text"]
    scene_id = _clean_text((previous_scene or {}).get("scene_id")) if isinstance(previous_scene, dict) else ""

    out: list[dict[str, Any]] = []
    for idx, label in enumerate(reps):
        renderer = PRESENTATION_RENDERERS.get(label, "MessageTextBlock")
        role, composition, payload = PRESENTATION_SCENE_PROFILES.get(
            label,
            ("explanation", "message", "human-readable answer"),
        )
        continuing_scene = bool(continuation and scene_id and label != "text")
        signal = {
            "version": "scene_presentation_signal_v3",
            "engine": "McDowell",
            "math_engine": "KaTeX",
            "kind": label,
            "renderer": renderer,
            "renderer_authority": "SCENE_CONTRACT",
            "owner": "QUANTUM_PROCESSOR",
            "source": "QUANTUM_INTERPRETATION_ENGINE",
            "evidence_only": True,
            "payload_unchanged": True,
            "layout_mode": "flow",
            "container": "adaptive_full_width",
            "scene_id": scene_id,
            "block_id": "",
            "render_id": "",
            "status": "planned",
        }
        out.append({
            "recommendation_id": f"semantic-presentation-{idx + 1}",
            "representation": label,
            "representation_label": PRESENTATION_LABELS.get(label, label),
            "renderer": renderer,
            "renderer_signal": signal,
            "semantic_basis": {
                "representation_score": float(scores.get(label, 0.0) or 0.0),
                "object_score": 0.0,
                "operation": "",
                "goal": "",
                "is_production_representation": label == production,
                "production_locked": label == production,
                "explicit_current_request": label in explicit_set,
            },
            "response_role": "supporting_explanation" if label == "text" else "primary_representation",
            "scene_recommendation": {
                "role": role,
                "order_hint": "representation" if label != "text" else "narrative",
                "composition": composition,
                "sequence": (
                    [
                        {"role": "introduction", "renderer": "MessageTextBlock", "content_role": "request_essence"},
                        {"role": "representation", "renderer": renderer, "type": label, "content_role": "specialized_result"},
                        {"role": "explanation", "renderer": "MessageTextBlock", "content_role": "result_explanation"},
                    ]
                    if label != "text"
                    else [{"role": "answer", "renderer": "MessageTextBlock", "content_role": "human_answer"}]
                ),
                "intro_via": "MessageTextBlock",
                "renderer": renderer,
                "explanation_via": "MessageTextBlock",
                "payload_expectation": payload,
                "scene_relation": "continue_existing_scene" if continuing_scene else "new_scene",
                "reuse_scene_id": scene_id if continuing_scene else "",
                "avoid_repeat": continuing_scene,
                "build_scene_after_semantic_understanding": True,
                "independent_scene_recommendation": True,
            },
            "text_guidance": {
                "introduction": "Briefly state the essence of the current user request and what this representation will show.",
                "explanation": "Explain the produced result, its main meaning and purpose after the specialized block.",
            },
            "advisory_only": True,
        })
    return out


def _restore_presentation_contract(
    result: dict[str, Any],
    current_text: str,
    state: dict[str, Any] | None = None,
) -> None:
    """Restore the semantic presentation contract without becoming a renderer."""
    if not isinstance(result, dict):
        return

    authority = _presentation_authority(result, current_text, state)
    explicit = _explicit_current_representations(current_text)

    current_requested = authority.get("representations") or []
    if authority.get("mode") == "CURRENT_TURN" and explicit:
        requested = explicit
    elif authority.get("mode") == "ARTIFACT_CONTINUATION":
        requested = list(current_requested)
    else:
        requested = []

    # A single production field may be trusted only when its source is current-turn
    # or an explicitly authorized artifact continuation.
    production = _presentation_representation(result.get("production") or result.get("representation"))
    if authority.get("mode") == "CURRENT_TURN" and explicit:
        # For compound requests the first explicitly named representation is
        # the primary production signal; the complete list remains requested.
        production = explicit[0] if explicit else production
    elif not production or production == "text":
        production = requested[0] if requested else "text"
    if production not in requested and production != "text" and authority.get("authorized"):
        requested.insert(0, production)

    if not requested:
        requested = ["text"]
        production = "text"

    result["production"] = production
    result["representation"] = production
    result["subtype"] = production
    result["scene_type"] = production
    result["requested_outputs"] = list(dict.fromkeys(requested))
    result["requested_representations"] = list(dict.fromkeys(requested))
    result["required_representations"] = list(dict.fromkeys(requested))
    result["candidate_representations"] = list(dict.fromkeys(requested))
    result["production_representation"] = production
    result["production_representation_locked"] = bool(authority.get("authorized"))
    result["production_representation_source"] = authority.get("source")
    result["supported_payloads"] = list(WEB_SUPPORTED_PAYLOADS)

    prev_scene = {}
    if authority.get("mode") == "ARTIFACT_CONTINUATION":
        prev_scene = (
            result.get("resolved_scene")
            if isinstance(result.get("resolved_scene"), dict)
            else {}
        )
        if not prev_scene and isinstance(state, dict):
            prev_scene = (
                state.get("active_visual_scene")
                if isinstance(state.get("active_visual_scene"), dict)
                else state.get("current_visual_scene")
                if isinstance(state.get("current_visual_scene"), dict)
                else {}
            )

    scene_representations = ["text"] + [x for x in requested if x != "text"]
    recommendations = _presentation_recommendations_from_reps(
        current_text,
        scene_representations,
        production=production,
        continuation=authority.get("mode") == "ARTIFACT_CONTINUATION",
        previous_scene=prev_scene,
        scores=result.get("representation_scores") if isinstance(result.get("representation_scores"), dict) else {},
        explicit=explicit,
    )
    scene_plan = [item["scene_recommendation"] for item in recommendations]
    signals = [item["renderer_signal"] for item in recommendations]

    old_presentation = result.get("presentation") if isinstance(result.get("presentation"), dict) else {}
    presentation = dict(old_presentation)
    presentation.update({
        "version": "quantum_interpretation_transport_v4",
        "decision_owner": "QUANTUM_PROCESSOR",
        "single_route": True,
        "production_representation": production,
        "recommendation_policy": {
            "generated_after_interpretation": True,
            "current_request_authoritative": True,
            "multiple_representations_allowed": True,
            "multiple_renderer_recommendations_allowed": True,
            "scene_recommendation_per_representation": True,
            "text_intro_renderer": "MessageTextBlock",
            "text_explanation_renderer": "MessageTextBlock",
            "stale_context_cannot_upgrade_current_representation": True,
        },
        "signals": signals,
        "recommendations": recommendations,
        "scene_plan": scene_plan,
    })

    result["presentation"] = presentation
    result["presentation_transport"] = presentation
    result["presentation_signal"] = presentation
    result["presentation_recommendations"] = recommendations
    result["presentation_signals"] = signals
    result["scene_recommendations"] = scene_plan
    result["scene_plan"] = scene_plan

    # `scene_composition` is the ordered semantic scene, not renderer output.
    result["scene_composition"] = [
        {
            "representation": item["representation"],
            "role": item["scene_recommendation"]["role"],
            "order": index,
            "renderer": item["renderer"],
            "scene_relation": item["scene_recommendation"]["scene_relation"],
        }
        for index, item in enumerate(recommendations)
    ]
    result["scene_graph"] = {
        "root": "current_request",
        "parts": result["scene_composition"],
        "representation_order": [x["representation"] for x in result["scene_composition"]],
        "semantic_source": "current_turn_presentation_sync",
    }

    prev_types = []
    if isinstance(prev_scene, dict):
        prev_types = _ordered_unique(prev_scene.get("render_block_types") or prev_scene.get("presentation_types"))
    result["render_continuity"] = {
        "relation": _clean_text(
            result.get("dialogue_relation")
            or result.get("relation")
            or _as_dict(result.get("dialogue_vector")).get("three_way_relation")
        ).upper() or "NEW",
        "reuse_existing_scene": authority.get("mode") == "ARTIFACT_CONTINUATION" and bool(prev_types),
        "reuse_recalled_memory": False,
        "selected_memory_index": result.get("selected_memory_index", -1),
        "previous_scene_id": _clean_text(prev_scene.get("scene_id")) if isinstance(prev_scene, dict) else "",
        "previous_render_types": prev_types,
        "avoid_repeat": True,
        "authority": authority.get("source"),
    }
    result["render_signal_inventory"] = [
        {
            "block_id": signal.get("block_id", ""),
            "type": signal.get("kind", "text"),
            "renderer": _clean_text(signal.get("renderer")).lower(),
            "fallback_renderer": "MessageTextBlock",
            "sequence_index": index,
            "signal_channel": "canonical_web_render_signal_v2",
            "status": "planned",
            "evidence_only": True,
        }
        for index, signal in enumerate(signals)
    ]
    result["presentation_sync"] = {
        "version": "presentation_sync_v1",
        "stage": "interpretation_post_semantic_pre_provider",
        "current_turn_authority": True,
        "memory_evidence_only": True,
        "authority_mode": authority.get("mode"),
        "authority_source": authority.get("source"),
        "relation": authority.get("relation"),
        "requested_outputs": list(dict.fromkeys(requested)),
        "renderer_contract": "advisory",
        "scene_contract_owner": "EXECUTOR",
        "web_renderer_owner": "RENDERMESSAGE",
        "compound_outputs_preserved": len([x for x in requested if x != "text"]) > 1,
    }


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
    state: dict[str, Any] | None = None,
) -> None:
    """Remove only genuinely stale visual modality.

    Current-turn structured requests and authorized artifact continuations are
    never downgraded.  Historical memory alone cannot upgrade a plain turn.
    """
    authority = _presentation_authority(result, current_text, state)
    if authority.get("authorized"):
        return

    structured = set(_STRUCTURED_PRESENTATIONS)
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

    text_operations = {"", "answer", "explain", "retrieve", "list", "analyze"}
    if representation in structured and operation in text_operations:
        result["production"] = "text"
        result["representation"] = "text"
        result["subtype"] = "text"
        result["scene_type"] = "text"
        result["visual_production_mode"] = "text"
        result["requested_representations"] = ["text"]
        result["requested_outputs"] = ["text"]
        result["required_representations"] = ["text"]
        result["candidate_representations"] = ["text"]
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
    state: dict[str, Any] | None = None,
) -> Any:
    if not isinstance(result, dict):
        return result

    current = _clean_text(current_text)

    # Never allow an internal prompt to be carried as the user request.
    _sanitize_provider_facing_fields(result, current)

    # Exact Railway regression fence.
    if _self_contained_without_reference(result):
        _force_new_turn_state(result, current)

    # For CONTINUE, the authenticated live sequence is the authority. Generic
    # seven-day recall remains evidence-only and may not replace the current
    # dialogue turn. This directly prevents stale operands such as an old
    # "Официальный" record from becoming the active conversational context.
    _apply_active_sequence_authority(result, state)

    relation = _clean_text(
        result.get("dialogue_relation")
        or result.get("relation")
        or (result.get("dialogue_vector") or {}).get("three_way_relation")
    ).upper()
    if relation in {"CONTINUE", "RECALL"}:
        continuation_analysis = _build_continuation_content_analysis(
            current,
            {
                "relation": relation,
                "reference": bool(result.get("reference_to_previous") or result.get("reference")),
                "active_sequence": (
                    result.get("active_sequence")
                    if isinstance(result.get("active_sequence"), dict)
                    else (state or {}).get("active_dialogue_sequence") if isinstance(state, dict) else {}
                ),
                "previous_user_turn": result.get("previous_user_turn"),
                "previous_april_turn": result.get("previous_april_turn"),
                "active_topic": result.get("active_topic") or result.get("canonical_topic"),
                "topic_similarity": result.get("topic_similarity", 0.0),
                "sequence_pairs": result.get("sequence_pairs") or [],
                "resolved_entity": result.get("resolved_entity") or "",
                "resolved_entity_source": result.get("resolved_entity_source") or "",
                "artifact_reference": bool(
                    result.get("artifact_reference")
                    or _as_dict(result.get("thread_choice")).get("artifact_signal")
                ),
                "artifact_noun_signal": bool(
                    result.get("artifact_noun_signal")
                    or _as_dict(result.get("thread_choice")).get("artifact_noun_signal")
                ),
                "target_sequence": (
                    result.get("target_sequence")
                    if isinstance(result.get("target_sequence"), dict)
                    else result.get("active_sequence")
                    if isinstance(result.get("active_sequence"), dict)
                    else {}
                ),
                "target_artifact": result.get("target_artifact") or {},
                "resolved_reference_type": result.get("resolved_reference_type") or "",
            },
            state=state,
            operation=_clean_text(result.get("operation") or result.get("best_operation")),
        )
        result["continuation_content_analysis"] = continuation_analysis
        result["artifact_reference"] = bool(
            continuation_analysis.get("artifact_reference")
            or continuation_analysis.get("artifact_noun_signal")
            or result.get("artifact_reference")
        )
        result["artifact_noun_signal"] = bool(
            continuation_analysis.get("artifact_noun_signal")
            or result.get("artifact_noun_signal")
        )
        result["resolved_reference_type"] = (
            "artifact"
            if result.get("artifact_reference")
            else "entity"
            if result.get("resolved_entity")
            else "none"
        )
        result["dialogue_strategy"] = {
            "mode": continuation_analysis.get("mode", "NONE"),
            "intent": continuation_analysis.get("intent", ""),
            "new_information_required": bool(continuation_analysis.get("new_information_required")),
            "conversational_posture": continuation_analysis.get("conversational_posture", "CONVERSE"),
            "next_direction": continuation_analysis.get("next_direction", "advance_the_current_thread_naturally"),
            "novelty_target": continuation_analysis.get("novelty_target", 0.0),
            "recap_ratio_max": continuation_analysis.get("recap_ratio_max", 1.0),
            "active_entity": continuation_analysis.get("active_entity", ""),
            "expertise_behavior": continuation_analysis.get("expertise_behavior", "answer_with_domain_appropriate_reasoning"),
            "source": "semantic_continuation_analysis",
        }
        result["resolved_entity"] = continuation_analysis.get("active_entity", "")
        result["resolved_entity_source"] = continuation_analysis.get("active_entity_source", "")
        result["resolved_reference_type"] = (
            "artifact"
            if continuation_analysis.get("artifact_reference")
            else "entity"
            if continuation_analysis.get("active_entity")
            else "none"
        )
        result["memory_resolution"] = {
            "engine": "QUANTUM-MEMORY-7D-V2",
            "window": "day_0..day_6",
            "source": "authenticated_user_memory",
            "authority": (
                "active_dialogue_sequence"
                if relation == "CONTINUE" and (
                    result.get("target_sequence_id") == result.get("active_sequence_id")
                )
                else "selected_dialogue_thread"
            ),
            "thread_transition": result.get("thread_transition", "ACTIVE"),
            "historical_memory_role": "evidence_only",
            "sequence_id": (
                result.get("target_sequence_id")
                or result.get("sequence_id")
                or ""
            ),
        }
        # A pronoun/reference may point to a child entity of the broader topic
        # (e.g. topic=Горбачёв, active entity=Раиса Горбачёва). Keep the broader
        # topic stable, but expose the resolved discourse entity to downstream
        # consumers as the current reference.
        if result.get("resolved_entity"):
            result["resolved_reference"] = result["resolved_entity"]

        vector = result.get("dialogue_vector")
        if isinstance(vector, dict):
            vector.update({
                "continuation_content_analysis": continuation_analysis,
                "dialogue_strategy": result["dialogue_strategy"],
                "resolved_entity": result.get("resolved_entity", ""),
                "resolved_entity_source": result.get("resolved_entity_source", ""),
                "resolved_reference_type": result.get("resolved_reference_type", "none"),
                "memory_resolution": result.get("memory_resolution", {}),
                "continuation_authority": result.get("continuation_authority", "active_dialogue_sequence"),
            })

        contract = result.get("dialogue_contract")
        if isinstance(contract, dict):
            contract.update({
                "continuation_content_analysis": continuation_analysis,
                "dialogue_strategy": result["dialogue_strategy"],
                "resolved_entity": result.get("resolved_entity", ""),
                "resolved_entity_source": result.get("resolved_entity_source", ""),
                "resolved_reference_type": result.get("resolved_reference_type", "none"),
                "memory_resolution": result.get("memory_resolution", {}),
                "continuation_authority": result.get("continuation_authority", "active_dialogue_sequence"),
                "previous_user_turn": continuation_analysis.get("previous_user_turn", contract.get("previous_user_turn", "")),
                "previous_april_turn": continuation_analysis.get("previous_answer", contract.get("previous_april_turn", "")),
            })

    # Representation safety runs after dialogue authority has been synchronized
    # so a legitimate artifact continuation cannot be mistaken for stale state.
    _remove_stale_structured_representation(result, current, state=state)

    # Restore the canonical semantic presentation contract.  This is advisory:
    # it feeds Provider/Executor context but never performs renderer dispatch.
    _restore_presentation_contract(result, current, state=state)

    result["interpretation_compatibility"] = {
        "version": "2026-09-22-dialogue-content-semantics-v4",
        "canonical_engine_discovery": bool(
            _load_canonical_engine_module() is not None
        ),
        "current_turn_authoritative": True,
        "provider_request_current_turn_only": True,
        "historical_memory_evidence_only": True,
        "false_continue_fence": True,
        "stale_representation_fence": True,
        "continuation_content_analysis": True,
        "active_sequence_authority": True,
        "semantic_dialogue_strategy": True,
        "presentation_contract_restored": True,
        "render_signal_inventory_restored": True,
        "compound_outputs_preserved": True,
        "memory_can_supply_visual_context": True,
        "artifact_continuation_can_reuse_prior_visual": True,
        "renderer_authority": "SCENE_CONTRACT",
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


# ---------------------------------------------------------------------------
# Continuation content semantics (no routing triggers)
# ---------------------------------------------------------------------------

_EXPAND_CUES = (
    "что ещё", "что еще", "а что еще", "а что ещё", "какие ещё",
    "какие еще", "что можешь ещё", "что можешь еще", "расскажи ещё",
    "расскажи еще", "добавь", "ещё факты", "еще факты", "интересного",
)
_DEEPEN_CUES = (
    "почему", "зачем", "как так", "как получилось", "как это произошло",
    "что именно", "подробнее", "подробней", "объясни подробнее",
    "в чём причина", "в чем причина",
)
_DISCUSS_CUES = (
    "как думаешь", "что думаешь", "мне кажется", "по-твоему", "по твоему",
    "согласен", "согласна", "правда ли", "можно ли считать", "обсудим",
    "поговорим", "я считаю", "мне кажется",
)
_SOLVE_CUES = (
    "что делать", "как исправить", "как решить", "помоги решить", "помоги разобраться",
    "разберись", "разберёмся", "разберемся", "как проверить", "как диагностировать",
    "в чём проблема", "в чем проблема", "не работает", "сломалось",
)
_CORRECT_CUES = (
    "исправь", "поправь", "я ошибся", "я ошиблась", "это неверно",
    "ты ошибся", "ты ошиблась", "исправление", "неправильно сказал",
    "неправильно написал", "неправильно понял",
)
_REACTION_CUES = (
    "жалко", "понятно", "ага", "да", "ясно", "ого", "круто", "интересно",
    "печально", "жаль", "понял", "понятно",
)


def _sentence_units(text: Any, limit: int = 8) -> list[str]:
    value = re.sub(r"\s+", " ", _clean_text(text)).strip()
    if not value:
        return []
    units = re.split(r"(?<=[.!?])\s+|\n+", value)
    result: list[str] = []
    for unit in units:
        unit = unit.strip(" \t\n-•")
        if not unit:
            continue
        if len(unit) > 260:
            unit = unit[:257].rstrip() + "..."
        if not any(_semantic_similarity(unit, prev) >= 0.88 for prev in result):
            result.append(unit)
        if len(result) >= limit:
            break
    return result


def _person_candidates(text: Any, limit: int = 10) -> list[str]:
    """Extract likely person-name spans while ignoring discourse pronouns/titles."""
    value = _clean_text(text)
    if not value:
        return []

    ignored = {
        "Его", "Её", "Ее", "Он", "Она", "Они", "Это", "Этот", "Эта", "Такие",
        "Михаил", "Михаила", "Сергей", "Сергеевич", "Президент", "Генеральный",
        "Советский", "Советская", "Россия", "СССР", "КПСС",
    }
    found: list[str] = []
    patterns = (
        r"\b(?:[А-ЯЁ][а-яё-]{2,}\s+){1,3}[А-ЯЁ][а-яё-]{2,}\b",
        r"\b[А-ЯЁ][а-яё-]{3,}\b",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, value):
            candidate = re.sub(r"\s+", " ", match.group(0)).strip(' ,.;:()"')
            if not candidate or candidate in ignored:
                continue
            words = candidate.split()
            if len(words) >= 2:
                # Reject obvious title-role phrases.
                if words[0] in {"Последний", "Единственный", "Лондонский", "Советский", "Российский", "Английский"}:
                    continue
                if candidate not in found:
                    found.append(candidate)
            elif len(words) == 1 and candidate not in ignored:
                found.append(candidate)
            if len(found) >= limit:
                return found
    return found


def _person_gender_hint(candidate: str) -> str:
    """Morphological hint for discourse reference resolution."""
    low = _clean_text(candidate).lower()
    words = low.split()
    first = words[0] if words else ""
    last = words[-1] if words else ""

    # Patronymics are stronger than surname morphology for Russian names.
    if any(re.search(r"(евич|ович|евич|ич)$", word) for word in words[1:]):
        return "masculine"
    if any(re.search(r"(вна|чна)$", word) for word in words[1:]):
        return "feminine"

    # Common first-name endings/sets used only as a local discourse hint.
    if first in {
        "михаил", "сергей", "иван", "александр", "дмитрий", "николай",
        "андрей", "владимир", "максим", "илон", "павел", "алексей",
        "юрий", "виктор", "олег", "евгений",
    }:
        return "masculine"
    if first in {
        "раиса", "мария", "анна", "елена", "ольга", "ирина", "наталья",
        "светлана", "евгения", "екатерина",
    }:
        return "feminine"

    if re.search(r"(вна|чна|ая)$", last):
        return "feminine"
    if re.search(r"(евич|ович|ич)$", last):
        return "masculine"
    if re.search(r"(ов|ев|ин|ский|цкий|ый|ий)$", last):
        return "masculine"

    return "unknown"


def _pronoun_profile(text: Any) -> str:
    low = _clean_text(text).lower()
    if re.search(r"\b(?:она|её|ее|ей|ней|неё|ею)\b", low):
        return "feminine"
    if re.search(r"\b(?:он|его|ему|ним|него|нему|нём|нем)\b", low):
        return "masculine"
    if re.search(r"\b(?:они|их|им|ними)\b", low):
        return "plural"
    if re.search(r"\b(?:это|этот|эта|эти|такой|такая|такие)\b", low):
        return "demonstrative"
    return "none"



# ---------------------------------------------------------------------------
# User-scoped seven-day memory integration / dialogue-thread routing
# ---------------------------------------------------------------------------

_REFERENCE_ARTIFACT_VERBS = (
    "продолжи", "продолжить", "продли", "продлить", "перепиши",
    "переделай", "переделать", "измени", "изменить", "добавь",
    "добавить", "убери", "убрать", "исправь", "исправить",
)

_ARTIFACT_NOUNS = (
    "стих", "стихотворение", "четверостишие", "текст", "ответ",
    "код", "скрипт", "таблица", "график", "диаграмма", "схема",
    "рисунок", "картинка", "изображение", "файл", "формула",
)

_EXPLICIT_SUBJECT_PATTERNS = (
    r"\b(?:про|об|о|насч[её]т|касательно)\s+(.+)$",
    r"\bчто\s+(?:ты\s+)?знаешь\s+(?:об|о|про)\s+(.+)$",
    r"\bрасскажи\s+(?:об|о|про)\s+(.+)$",
    r"\bкто\s+(?:такой|такая|это)\s+(.+)$",
)

def _memory_timestamp_live(record: Any, now: float | None = None) -> bool:
    if not isinstance(record, dict):
        return False
    now = float(now if now is not None else time.time())
    value = (
        record.get("created_at")
        or record.get("timestamp")
        or record.get("updated_at")
        or 0.0
    )
    try:
        ts = float(value)
    except (TypeError, ValueError):
        return False
    if ts <= 0:
        return True
    return (now - ts) < (7 * 24 * 60 * 60)


def _memory_engine_runtime(state: dict[str, Any]) -> dict[str, Any]:
    """
    Connect Interpretation Layer to the already-existing QUANTUM-MEMORY-7D-V2
    runtime. The import is lazy because State Manager itself imports the shared
    interpretation encoder.
    """
    if not isinstance(state, dict):
        return {}

    try:
        from blocks.state_manager import QUANTUM_MEMORY_ENGINE
        runtime = QUANTUM_MEMORY_ENGINE.ensure_runtime(state)
        return runtime if isinstance(runtime, dict) else state
    except Exception:
        # Interpretation remains usable in isolated tests/deployments.
        return state


def _build_user_memory_field(state: dict[str, Any]) -> dict[str, Any]:
    """
    Build one authenticated-user memory field for the interpretation pass.

    Order of evidence:
        current turn > selected active dialogue thread > day_0..day_6 pairs
        > A-E topic evidence > live summary evidence.

    This function only supplies memory evidence. It never decides a route.
    """
    state = _memory_engine_runtime(state)

    scope = _as_dict(state.get("memory_scope"))
    user_id = _clean_text(scope.get("user_id") or state.get("user_id"))
    conversation_id = _clean_text(
        scope.get("conversation_id") or state.get("conversation_id")
    )

    timeline = state.get("memory_timeline")
    timeline = timeline if isinstance(timeline, dict) else {}

    now = time.time()
    pairs: list[dict[str, Any]] = []
    topic_evidence: list[dict[str, Any]] = []

    for day_index in range(7):
        day = timeline.get(f"day_{day_index}")
        if not isinstance(day, dict):
            continue

        for slot in ("A", "B", "C", "D", "E"):
            for item in day.get(slot, []) or []:
                if not isinstance(item, dict):
                    continue
                topic = _clean_text(item.get("topic"))
                if topic:
                    topic_evidence.append({
                        "day_index": day_index,
                        "slot": slot,
                        "topic": topic[:300],
                        "score": item.get("score"),
                        "created_at": item.get("timestamp") or item.get("created_at"),
                        "source": "A_E_topic_memory",
                    })

        for item in day.get("dialog_pairs", []) or []:
            if not isinstance(item, dict):
                continue
            record_user = _clean_text(item.get("user_id"))
            if user_id and record_user and record_user != user_id:
                continue

            item_conversation = _clean_text(item.get("conversation_id"))
            if conversation_id and item_conversation and item_conversation != conversation_id:
                continue

            if not _memory_timestamp_live(item, now=now):
                continue

            pairs.append(dict(item))

    pairs.sort(
        key=lambda item: float(
            item.get("created_at")
            or item.get("timestamp")
            or item.get("updated_at")
            or 0.0
        )
    )

    active_sequence = _as_dict(state.get("active_dialogue_sequence"))
    active_id = _clean_text(active_sequence.get("sequence_id"))

    active_pairs = [
        item for item in pairs
        if active_id and _clean_text(item.get("sequence_id")) == active_id
    ]

    sequence_map: dict[str, dict[str, Any]] = {}
    for item in pairs:
        sid = _clean_text(item.get("sequence_id"))
        if not sid:
            continue

        profile = sequence_map.setdefault(
            sid,
            {
                "sequence_id": sid,
                "topic": _clean_text(
                    item.get("sequence_topic") or item.get("topic")
                ),
                "user_turns": [],
                "april_turns": [],
                "turns": [],
                "last_created_at": 0.0,
                "source": "seven_day_dialogue_memory",
            },
        )

        user_turn = _clean_text(
            item.get("user_request") or item.get("user_meaning")
        )
        april_turn = _clean_text(
            item.get("april_answer") or item.get("april_meaning")
        )
        if user_turn:
            profile["user_turns"].append(user_turn[:1200])
        if april_turn:
            profile["april_turns"].append(april_turn[:2200])
        profile["turns"].append(item)

        try:
            profile["last_created_at"] = max(
                profile["last_created_at"],
                float(
                    item.get("created_at")
                    or item.get("timestamp")
                    or 0.0
                ),
            )
        except (TypeError, ValueError):
            pass

    for profile in sequence_map.values():
        profile["user_turns"] = profile["user_turns"][-8:]
        profile["april_turns"] = profile["april_turns"][-8:]
        profile["turns"] = profile["turns"][-8:]
        profile["last_user_turn"] = (
            profile["user_turns"][-1] if profile["user_turns"] else ""
        )
        profile["last_april_answer"] = (
            profile["april_turns"][-1] if profile["april_turns"] else ""
        )

    summary = _clean_text(state.get("memory_summary"))
    summary_meta = _as_dict(state.get("memory_summary_meta"))
    if summary and summary_meta and not _memory_timestamp_live(summary_meta, now=now):
        summary = ""

    active_visual_scene = (
        state.get("active_visual_scene")
        if isinstance(state.get("active_visual_scene"), dict)
        else state.get("current_visual_scene")
        if isinstance(state.get("current_visual_scene"), dict)
        else {}
    )

    return {
        "version": "interpretation_user_memory_field_v2",
        "engine": "QUANTUM-MEMORY-7D-V2",
        "window": "day_0..day_6",
        "user_id": user_id,
        "conversation_id": conversation_id,
        "active_sequence": dict(active_sequence),
        "active_sequence_id": active_id,
        "active_sequence_pairs": active_pairs[-8:],
        "sequence_profiles": sequence_map,
        "dialog_pairs_7d": pairs[-24:],
        "topic_evidence_A_E": topic_evidence[-20:],
        "memory_summary_evidence": summary[:1400],
        "active_visual_scene": dict(active_visual_scene),
        "decision_owner": "QUANTUM_PROCESSOR",
        "evidence_only": True,
    }


def _sequence_profile_text(profile: dict[str, Any]) -> str:
    if not isinstance(profile, dict):
        return ""
    parts = [
        profile.get("topic"),
        *(profile.get("user_turns") or [])[-4:],
        *(profile.get("april_turns") or [])[-3:],
    ]
    return " ".join(str(x) for x in parts if x)


_REFERENCE_ONLY_SUBJECT_WORDS = {
    "него", "нему", "ним", "ней", "неё", "нее", "ее", "её", "ему", "ей",
    "он", "она", "они", "это", "этот", "эта", "эти",
    "известно", "интересного", "интересное", "интересный",
    "сказал", "сказала", "получился", "получилось", "получилась",
    "последнее", "последний", "особенно", "дальше", "ещё", "еще",
    "раньше", "тогда", "продолжи", "продолжим",
}


def _raw_subject_tokens(value: Any) -> list[str]:
    return [
        token.lower()
        for token in re.findall(r"\b[А-ЯЁа-яёA-Z-a-z0-9_-]{2,}\b", _clean_text(value))
    ]


def _is_concrete_subject_phrase(value: Any) -> bool:
    phrase = _clean_text(value)
    if not phrase:
        return False

    raw_tokens = _raw_subject_tokens(phrase)
    if not raw_tokens:
        return False

    # Do not let pronouns, discourse glue, or continuation words become a
    # "new topic". This check deliberately uses raw tokens, not the stemmed
    # shared semantic tokens.
    concrete = [
        token for token in raw_tokens
        if token not in _REFERENCE_ONLY_SUBJECT_WORDS
        and token not in _DIALOGUE_STOPWORDS
    ]
    return bool(concrete)


def _explicit_subject(text: Any) -> str:
    value = _clean_text(text)
    if not value:
        return ""

    for pattern in _EXPLICIT_SUBJECT_PATTERNS:
        match = re.search(pattern, value, flags=re.I)
        if match:
            candidate = _clean_text(match.group(1))
            if _is_concrete_subject_phrase(candidate):
                return candidate[:300]
            return ""

    # A turn containing a grammatical/anaphoric reference but no explicit
    # concrete named subject is not evidence of a topic switch. Examples:
    # "Как звали его жену?", "Что ещё про неё известно?",
    # "Сможешь его продлить?".
    if _pronoun_profile(value) != "none":
        return ""

    # Artifact follow-ups without a named subject are also not new topics.
    if _artifact_noun_signal(value) or _artifact_reference_signal(value):
        return ""

    # Only use the lexical topic fallback for genuinely self-contained turns.
    candidate = _extract_topic(value)
    return candidate[:300] if _is_concrete_subject_phrase(candidate) else ""


def _has_explicit_subject_signal(text: Any) -> bool:
    value = _clean_text(text)
    if not value:
        return False

    if _explicit_subject(value):
        return True

    # A single capitalized word at the start of a sentence (e.g. "Прикольный")
    # is not enough to establish a new named subject. Require a multi-token
    # proper-name shape to avoid turning ordinary adjectives into entities.
    proper = [
        token
        for token in re.findall(r"\b[А-ЯЁA-Z][а-яёa-z-]{2,}\b", value)
        if token.lower() not in _DIALOGUE_STOPWORDS
    ]
    return len(proper) >= 2


def _artifact_reference_signal(text: Any) -> bool:
    low = _clean_text(text).lower()
    has_pronoun = bool(
        re.search(
            r"\b(?:это|этот|эта|эти|его|ее|её|него|нему|ним|ему|ей|ней|неё|он|она|они)\b",
            low,
        )
    )
    has_artifact_verb = any(word in low for word in _REFERENCE_ARTIFACT_VERBS)
    has_artifact_noun = any(noun in low for noun in _ARTIFACT_NOUNS)
    return bool(has_pronoun and (has_artifact_verb or has_artifact_noun))



def _artifact_noun_signal(text: Any) -> bool:
    low = _clean_text(text).lower()
    return any(noun in low for noun in _ARTIFACT_NOUNS)


def _sequence_has_artifact_context(
    profile: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    profile = profile if isinstance(profile, dict) else {}
    active_sequence_state = (
        state.get("active_dialogue_sequence")
        if isinstance(state.get("active_dialogue_sequence"), dict)
        else {}
    )
    profile_sid = _clean_text(profile.get("sequence_id"))
    active_sid = _clean_text(active_sequence_state.get("sequence_id"))

    # The persisted active visual scene is allowed to enrich ONLY the live
    # active sequence. Historical sequences must derive their artifact state
    # from their own stored turns, otherwise a poem/image from the current
    # thread can falsely become the artifact of every old thread.
    active_scene = {}
    if profile_sid and active_sid and profile_sid == active_sid:
        active_scene = (
            state.get("active_visual_scene")
            if isinstance(state.get("active_visual_scene"), dict)
            else state.get("current_visual_scene")
            if isinstance(state.get("current_visual_scene"), dict)
            else {}
        )

    scene_answer = _clean_text(
        active_scene.get("april_answer")
        or active_scene.get("answer")
        or active_scene.get("summary")
    )
    scene_request = _clean_text(
        active_scene.get("user_request")
        or active_scene.get("current_request")
    )
    scene_types = active_scene.get("render_block_types") or []
    sequence_text = _sequence_profile_text(profile)

    artifact_kind = ""
    artifact_subject = ""

    if scene_answer or scene_request:
        low = f"{scene_request} {scene_answer}".lower()
        if any(word in low for word in ("стих", "стихотворение", "четверостишие")):
            artifact_kind = "poem"
            artifact_subject = _clean_text(
                active_scene.get("topic") or scene_request or "стих"
            )
        elif any(word in low for word in ("код", "python", "скрипт")):
            artifact_kind = "code"
            artifact_subject = _clean_text(
                active_scene.get("topic") or scene_request
            )
        elif any(
            word in low
            for word in ("таблиц", "график", "диаграм", "схем", "формул")
        ):
            artifact_kind = (
                "structured"
                if not scene_types
                else _clean_text(scene_types[0]).lower()
            )
            artifact_subject = _clean_text(
                active_scene.get("topic") or scene_request
            )

    if not artifact_kind:
        low_seq = sequence_text.lower()
        if any(
            word in low_seq
            for word in ("стих", "стихотворение", "четверостишие")
        ):
            artifact_kind = "poem"
            artifact_subject = _clean_text(profile.get("topic") or "стих")
        elif any(word in low_seq for word in ("код", "python", "скрипт")):
            artifact_kind = "code"
            artifact_subject = _clean_text(profile.get("topic") or "код")

    # A plain text dialogue scene is not automatically an artifact. Only an
    # explicitly identified artifact kind (poem/code/structured media) should
    # participate in pronoun→artifact resolution.
    return {
        "present": bool(artifact_kind),
        "kind": artifact_kind,
        "subject": artifact_subject or _clean_text(profile.get("topic")),
        "previous_answer": scene_answer,
        "previous_request": scene_request,
        "render_types": list(scene_types) if isinstance(scene_types, list) else [],
    }


def _choose_dialogue_thread(
    current_text: str,
    memory_field: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    Select active thread, an older user-owned thread, or a new thread before
    pronoun/entity resolution.

    This is semantic evidence fusion, not a direct keyword trigger.
    """
    active = _as_dict(memory_field.get("active_sequence"))
    active_id = _clean_text(active.get("sequence_id"))
    profiles = (
        memory_field.get("sequence_profiles")
        if isinstance(memory_field.get("sequence_profiles"), dict)
        else {}
    )
    active_profile = profiles.get(active_id, {}) if active_id else {}

    current_topic = _explicit_subject(current_text)
    subject_signal = _has_explicit_subject_signal(current_text)
    reference_signal = _is_reference_turn(current_text)
    artifact_signal = _artifact_reference_signal(current_text)
    artifact_noun_signal = _artifact_noun_signal(current_text)
    explicit_recall = _explicit_memory_recall(current_text)
    explicit_new = _explicit_new_topic(current_text)

    active_topic = _clean_text(
        active.get("topic")
        or active_profile.get("topic")
        or state.get("april_active_topic")
    )
    active_last_user = _clean_text(
        active.get("last_user_request")
        or active_profile.get("last_user_turn")
        or state.get("last_user_turn")
    )
    active_last_answer = _clean_text(
        active.get("last_april_answer")
        or active_profile.get("last_april_answer")
        or state.get("last_april_turn")
    )

    active_score = max(
        _semantic_similarity(current_text, active_topic),
        _semantic_similarity(current_topic, active_topic)
        if current_topic and active_topic else 0.0,
        _semantic_similarity(current_text, active_last_user)
        if active_last_user else 0.0,
        _semantic_similarity(current_text, active_last_answer)
        if active_last_answer else 0.0,
    )

    active_artifact = _sequence_has_artifact_context(active_profile, state)
    if artifact_signal and active_artifact.get("present"):
        active_score = max(active_score, 0.62)

    candidates = []
    for sid, profile in profiles.items():
        if sid == active_id:
            continue

        profile_text = _sequence_profile_text(profile)
        profile_topic = _clean_text(profile.get("topic"))
        score = max(
            _semantic_similarity(current_text, profile_topic),
            _semantic_similarity(current_text, profile_text),
            _semantic_similarity(current_topic, profile_topic)
            if current_topic and profile_topic else 0.0,
        )

        artifact = _sequence_has_artifact_context(profile, state)
        low = _clean_text(current_text).lower()

        if artifact.get("present"):
            if artifact.get("kind") == "poem":
                if any(word in low for word in ("стих", "стихотворение", "четверостишие")):
                    score = max(score, 0.82)
                elif artifact_signal:
                    # "его продлить" / "это продолжить" can refer to a stored
                    # poem even when the noun "стих" is omitted in the current turn.
                    score = max(score, 0.76)
            elif artifact.get("kind") == "code":
                if "код" in low or artifact_signal:
                    score = max(score, 0.78)
            elif artifact_signal and artifact_noun_signal:
                score = max(score, 0.72)

        candidates.append((score, sid, profile, artifact))

    candidates.sort(
        key=lambda item: (
            float(item[0]),
            float(item[2].get("last_created_at") or 0.0),
        ),
        reverse=True,
    )

    best_score = float(candidates[0][0]) if candidates else 0.0
    best_sid = candidates[0][1] if candidates else ""
    best_profile = candidates[0][2] if candidates else {}
    best_artifact = candidates[0][3] if candidates else {}

    # A short affirmative clarification can contain a concrete noun phrase
    # (e.g. "Да, именно про индийца...") while still being a continuation.
    # Require both an anaphoric/discourse marker and semantic support from the
    # immediately previous authentic answer, so this does not become a generic
    # keyword trigger for new topics.
    contextual_affirmation = bool(re.search(
        r"^(?:да|точно|верно|именно)\b.*\b(?:про|об|о)\b",
        _clean_text(current_text).lower(),
    ))
    immediate_answer_support = (
        _semantic_similarity(current_text, active_last_answer) >= 0.06
        if active_last_answer else False
    )
    if (
        not explicit_new
        and active_id
        and contextual_affirmation
        and reference_signal
        and immediate_answer_support
    ):
        relation = "CONTINUE"
        reason = "affirmative_contextual_continuation"
        confidence = max(0.76, min(0.96, 0.76 + active_score * 0.20))
    # Strong concrete subject means "new" unless the same user explicitly
    # points back to an older stored thread.
    elif explicit_new:
        relation = "NEW"
        reason = "explicit_new_topic"
        confidence = 0.99
    elif (
        subject_signal
        and current_topic
        and active_id
        and _semantic_similarity(current_topic, active_topic) < 0.34
        and active_score < 0.48
    ):
        if (
            best_sid
            and best_score >= 0.58
            and best_score > active_score + 0.16
            and explicit_recall
        ):
            relation = "RECALL"
            reason = "explicit_recall_to_older_user_sequence"
            confidence = min(0.96, 0.68 + best_score * 0.28)
        else:
            relation = "NEW"
            reason = "strong_new_subject_against_active_sequence"
            confidence = min(0.96, 0.70 + (1.0 - active_score) * 0.24)
    elif artifact_signal and active_artifact.get("present"):
        relation = "CONTINUE"
        reason = "reference_to_active_artifact"
        confidence = max(0.82, min(0.97, active_score + 0.15))
    elif artifact_signal and best_sid and best_artifact.get("present") and (
        best_score >= 0.70 and best_score > active_score + 0.12
    ):
        # Re-activating an older user-owned thread is still a continuation of
        # the user's dialogue. Keep "CONTINUE" as the conversational relation
        # and expose the thread switch separately so downstream stages do not
        # mistake "продли стих" for a memory-query operation.
        relation = "CONTINUE"
        reason = "reactivate_older_user_sequence_for_continuation"
        confidence = max(0.76, min(0.97, best_score))
    elif explicit_recall and best_sid and best_score >= 0.40:
        relation = "RECALL"
        reason = "explicit_memory_recall"
        confidence = max(0.72, min(0.97, best_score))
    elif (
        best_sid
        and best_score >= 0.58
        and best_score > active_score + 0.18
        and (
            reference_signal
            or artifact_signal
            or (
                artifact_noun_signal
                and not subject_signal
            )
        )
    ):
        relation = "CONTINUE"
        reason = "reactivate_older_matching_thread"
        confidence = max(0.68, min(0.95, best_score))
    elif not active_id:
        relation = "NEW"
        reason = "no_active_dialogue_sequence"
        confidence = 0.99
    elif reference_signal and not subject_signal:
        # Once the thread has been selected, a pronoun/anaphoric turn without a
        # concrete new subject is a continuation by discourse structure. The
        # current turn does not become a new topic merely because token
        # similarity is low.
        relation = "CONTINUE"
        reason = "anaphoric_continuation_on_selected_thread"
        confidence = max(0.80, min(0.96, 0.78 + active_score * 0.22))
    else:
        relation = "CONTINUE"
        reason = "active_sequence_semantic_continuation"
        confidence = max(0.62, min(0.96, 0.62 + active_score * 0.30))
        if reference_signal:
            confidence = max(confidence, 0.78)

    target_profile = active_profile
    target_sid = active_id
    if (
        best_sid
        and (
            relation == "RECALL"
            or reason.startswith("reactivate_")
        )
    ):
        target_profile = best_profile
        target_sid = best_sid

    return {
        "relation": relation,
        "reason": reason,
        "confidence": round(confidence, 6),
        "active_sequence": active,
        "active_profile": active_profile,
        "target_sequence": target_profile,
        "active_sequence_id": active_id,
        "target_sequence_id": target_sid,
        "active_topic": active_topic,
        "current_topic": current_topic,
        "active_score": round(active_score, 6),
        "best_historical_score": round(best_score, 6),
        "best_historical_sequence_id": best_sid,
        "reference_signal": reference_signal,
        "artifact_signal": artifact_signal,
        "artifact_noun_signal": artifact_noun_signal,
        "explicit_recall": explicit_recall,
        "explicit_new": explicit_new,
        "subject_signal": subject_signal,
        "active_artifact": active_artifact,
        "target_artifact": _sequence_has_artifact_context(target_profile, state),
        "memory_field_version": memory_field.get("version"),
    }


def _entity_from_relation_context(
    current_text: str,
    previous_answer: str,
    active_topic: str,
    state: dict[str, Any] | None = None,
    relation_context: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """
    Resolve discourse references only after the dialogue thread is selected.

    Reference targets may be people, artifacts, topics or the previous result.
    """
    state = state if isinstance(state, dict) else {}
    relation_context = (
        relation_context if isinstance(relation_context, dict) else {}
    )

    profile = _pronoun_profile(current_text)
    low = _clean_text(current_text).lower()

    target_profile = relation_context.get("target_sequence")
    target_profile = (
        target_profile if isinstance(target_profile, dict) else {}
    )

    target_answer = _clean_text(
        target_profile.get("last_april_answer")
        or previous_answer
        or state.get("last_april_turn")
    )
    target_user = _clean_text(
        target_profile.get("last_user_turn")
        or state.get("last_user_turn")
    )

    artifact = relation_context.get("target_artifact")
    artifact = artifact if isinstance(artifact, dict) else {}

    active_scene = (
        state.get("active_visual_scene")
        if isinstance(state.get("active_visual_scene"), dict)
        else state.get("current_visual_scene")
        if isinstance(state.get("current_visual_scene"), dict)
        else {}
    )

    scene_answer = _clean_text(
        artifact.get("previous_answer")
        or active_scene.get("april_answer")
        or active_scene.get("answer")
        or active_scene.get("summary")
    )
    scene_request = _clean_text(
        artifact.get("previous_request")
        or active_scene.get("user_request")
        or active_scene.get("current_request")
    )
    artifact_kind = _clean_text(artifact.get("kind")).lower()

    current_candidates = _person_candidates(current_text, limit=12)

    artifact_continuation = bool(
        (
            _artifact_reference_signal(current_text)
            or (
                bool(artifact.get("present"))
                and (
                    any(word in low for word in _REFERENCE_ARTIFACT_VERBS)
                    or _artifact_noun_signal(current_text)
                )
            )
        )
        and (
            artifact.get("present")
            or artifact_kind
            or any(noun in low for noun in _ARTIFACT_NOUNS)
        )
    )

    # "его продлить" / "это переделать" should resolve to the selected
    # artifact before any stale person candidate is considered.
    if artifact_continuation and (
        any(word in low for word in _REFERENCE_ARTIFACT_VERBS)
        or artifact_kind
        or any(noun in low for noun in _ARTIFACT_NOUNS)
    ):
        subject = _clean_text(
            artifact.get("subject")
            or scene_request
            or target_profile.get("topic")
            or active_topic
            or "предыдущий артефакт"
        )
        if artifact_kind == "poem" or any(
            word in f"{scene_request} {target_user}".lower()
            for word in ("стих", "стихотворение", "четверостишие")
        ):
            return subject or "стих", "active_dialogue_artifact"
        return subject or "предыдущий артефакт", "active_dialogue_artifact"

    # For anaphora we may need the entity established earlier in the selected
    # thread, not only the immediately previous answer. This matters for turns
    # such as "Как звали его жену?" where the latest answer mentions the wife
    # but the masculine owner was established one turn earlier.
    prior_thread_answers = []
    prior_thread_users = []
    for turn in (target_profile.get("turns") or [])[-6:]:
        if not isinstance(turn, dict):
            continue
        answer_turn = _clean_text(
            turn.get("april_answer")
            or turn.get("april_meaning")
            or turn.get("answer_summary")
        )
        user_turn = _clean_text(
            turn.get("user_request")
            or turn.get("user_meaning")
        )
        if answer_turn:
            prior_thread_answers.append(answer_turn)
        if user_turn:
            prior_thread_users.append(user_turn)

    previous_candidates = _person_candidates(target_answer, limit=12)
    for source in reversed(prior_thread_answers):
        for candidate in _person_candidates(source, limit=12):
            if candidate not in previous_candidates:
                previous_candidates.append(candidate)
                if len(previous_candidates) >= 16:
                    break
        if len(previous_candidates) >= 16:
            break

    user_candidates = _person_candidates(target_user, limit=8)
    for source in reversed(prior_thread_users):
        for candidate in _person_candidates(source, limit=8):
            if candidate not in user_candidates:
                user_candidates.append(candidate)
                if len(user_candidates) >= 12:
                    break
        if len(user_candidates) >= 12:
            break

    topic_candidates = _person_candidates(
        active_topic,
        limit=8,
    )

    def _best(candidates: list[str]) -> str:
        return max(
            candidates,
            key=lambda value: (len(value.split()), len(value)),
        ) if candidates else ""

    if profile == "masculine":
        # In "Как звали его жену?" the grammatical "его" points back to the
        # male owner/person, not to the queried female object. Prefer the
        # established male entity from the selected thread.
        if re.search(r"\b(?:жена|жену|супруга|супругу|дочь|мать)\b", low):
            matches = [
                c for c in previous_candidates
                if _person_gender_hint(c) == "masculine"
            ]
            if matches:
                return _best(matches), "selected_thread_person_candidate"
            matches = [
                c for c in topic_candidates
                if _person_gender_hint(c) == "masculine"
            ]
            if matches:
                return _best(matches), "active_topic_person_candidate"

        matches = [
            c for c in current_candidates
            if _person_gender_hint(c) == "masculine"
        ]
        if matches:
            return _best(matches), "current_turn_person_candidate"

        # Inflected Russian names such as "Илоне Маске" are often gender
        # ambiguous to a tiny local morphology table. When the name is present
        # in the current turn, it is safer to bind the pronoun to that current
        # name than to an older memory entity.
        if current_candidates:
            return _best(current_candidates), "current_turn_person_candidate"

        matches = [
            c for c in previous_candidates
            if _person_gender_hint(c) == "masculine"
        ]
        if matches:
            return _best(matches), "selected_thread_person_candidate"

        matches = [
            c for c in user_candidates
            if _person_gender_hint(c) == "masculine"
        ]
        if matches:
            return _best(matches), "selected_thread_user_person_candidate"

        matches = [
            c for c in topic_candidates
            if _person_gender_hint(c) == "masculine"
        ]
        if matches:
            return _best(matches), "active_topic_person_candidate"

        live_entity = _clean_text(state.get("april_active_entity"))
        if live_entity and _person_gender_hint(live_entity) == "masculine":
            return live_entity, "live_active_entity"

        return _clean_text(active_topic), "active_topic"

    if profile == "feminine":
        matches = [
            c for c in current_candidates
            if _person_gender_hint(c) == "feminine"
        ]
        if matches:
            return _best(matches), "current_turn_person_candidate"

        if current_candidates:
            return _best(current_candidates), "current_turn_person_candidate"

        matches = [
            c for c in previous_candidates
            if _person_gender_hint(c) == "feminine"
        ]
        if matches:
            return _best(matches), "selected_thread_person_candidate"

        matches = [
            c for c in user_candidates
            if _person_gender_hint(c) == "feminine"
        ]
        if matches:
            return _best(matches), "selected_thread_user_person_candidate"

        live_entity = _clean_text(state.get("april_active_entity"))
        if live_entity and _person_gender_hint(live_entity) == "feminine":
            return live_entity, "live_active_entity"

        return _clean_text(active_topic), "active_topic"

    if profile == "plural":
        if current_candidates:
            return _best(current_candidates), "current_turn_person_candidate"
        if previous_candidates:
            return _best(previous_candidates), "selected_thread_person_candidate"
        if user_candidates:
            return _best(user_candidates), "selected_thread_user_person_candidate"

    if profile == "demonstrative":
        if artifact.get("present") or scene_answer:
            return (
                _clean_text(
                    artifact.get("subject")
                    or scene_request
                    or active_topic
                    or "предыдущий результат"
                ),
                "active_dialogue_artifact",
            )
        if previous_candidates:
            return _best(previous_candidates), "selected_thread_person_candidate"

    if current_candidates:
        return _best(current_candidates), "current_turn_person_candidate"

    live_entity = _clean_text(state.get("april_active_entity"))
    if live_entity:
        return live_entity, "live_active_entity"

    if topic_candidates:
        return _best(topic_candidates), "active_topic_person_candidate"

    return _clean_text(active_topic), "active_topic"

def _infer_dialogue_mode(
    current_text: str,
    relation: str,
    operation: str = "",
    reference: bool = False,
    previous_answer: str = "",
    topic_similarity: float = 0.0,
) -> dict[str, Any]:
    """Infer a conversational response mode from semantics and dialogue state."""
    low = _clean_text(current_text).lower()
    if relation not in {"CONTINUE", "RECALL"}:
        return {
            "mode": "NEW",
            "intent": "independent_request",
            "new_information_required": False,
            "conversational_posture": "ANSWER",
            "next_direction": "answer_current_request",
            "novelty_target": 0.0,
            "recap_ratio_max": 1.0,
        }

    if any(cue in low for cue in _CORRECT_CUES):
        mode, intent, posture = "CORRECT", "correct_previous_content", "CLARIFY"
        next_direction = "identify_and_correct_the_specific_previous_claim"
        novelty = 0.55
        recap = 0.20
    elif any(cue in low for cue in _SOLVE_CUES) or operation in {"modify", "calculate"}:
        mode, intent, posture = "SOLVE", "solve_task", "COLLABORATE"
        next_direction = "diagnose_reason_and_move_to_the_next_actionable_step"
        novelty = 0.78
        recap = 0.12
    elif any(cue in low for cue in _DISCUSS_CUES):
        mode, intent, posture = "DISCUSS", "discuss_claim_or_interpretation", "DISCUSS"
        next_direction = "address_the_users_point_with_evidence_nuance_and_a_useful_follow_up"
        novelty = 0.72
        recap = 0.15
    elif any(cue in low for cue in _DEEPEN_CUES):
        mode, intent, posture = "DEEPEN", "deepen_understanding", "EXPLAIN"
        next_direction = "explain_the_underlying_cause_or_mechanism_without_repeating_the_summary"
        novelty = 0.78
        recap = 0.15
    elif any(cue in low for cue in _EXPAND_CUES):
        mode, intent, posture = "EXPAND", "request_additional_information", "INFORM"
        next_direction = "add_new_information_examples_or_angles_not_already_covered"
        novelty = 0.82
        recap = 0.12
    elif any(cue in low for cue in _REACTION_CUES) and len(_dialogue_tokens(current_text)) <= 4:
        mode, intent, posture = "REACT", "natural_user_reaction", "CONVERSE"
        next_direction = "respond_naturally_and_keep_the_dialogue_open_without_forcing_more_information"
        novelty = 0.35
        recap = 0.10
    elif reference or _pronoun_profile(current_text) != "none":
        mode, intent, posture = "CONTINUE_NATURAL", "continue_active_thread", "CONVERSE"
        next_direction = "answer_the_current_turn_using_the_live_active_entity_and_existing_context"
        novelty = 0.62
        recap = 0.15
    else:
        mode, intent, posture = "CONTINUE_NATURAL", "continue_active_thread", "CONVERSE"
        next_direction = "advance_the_current_thread_naturally"
        novelty = 0.58
        recap = 0.18

    # A highly similar current turn should not erase the expansion/deepening mode;
    # similarity is only a supporting signal, never the decision owner.
    return {
        "mode": mode,
        "intent": intent,
        "new_information_required": mode in {"EXPAND", "DEEPEN", "DISCUSS", "SOLVE"},
        "conversational_posture": posture,
        "next_direction": next_direction,
        "novelty_target": novelty,
        "recap_ratio_max": recap,
        "topic_similarity": round(float(topic_similarity or 0.0), 6),
        "reference_driven": bool(reference),
        "expertise_behavior": {
            "EXPAND": "provide_specific_new_information_and_useful_angles",
            "DEEPEN": "explain_mechanism_causality_and_distinctions",
            "DISCUSS": "separate_facts_from_interpretation_and_engage_with_alternatives",
            "SOLVE": "separate_observations_hypotheses_tests_and_next_action",
            "CORRECT": "locate_the_specific_claim_and_state_the_corrected_version",
            "REACT": "respond_humanly_and_only_extend_when_it_fits",
            "CONTINUE_NATURAL": "advance_the_thread_without_forcing_a_template",
        }.get(mode, "answer_with_domain_appropriate_reasoning"),
        "analysis_basis": "live_authenticated_dialogue_semantics",
    }


def _build_continuation_content_analysis(
    current_text: str,
    relation: dict[str, Any],
    state: dict[str, Any] | None = None,
    operation: str = "",
) -> dict[str, Any]:
    """Build a provider-ready delta from the selected dialogue thread."""
    relation_name = _clean_text(relation.get("relation")).upper()
    if relation_name not in {"CONTINUE", "RECALL"}:
        return {
            "version": "continuation_content_analysis_v3",
            "active": False,
            "mode": "NONE",
            "new_information_required": False,
        }

    target_sequence = (
        relation.get("target_sequence")
        if isinstance(relation.get("target_sequence"), dict)
        else relation.get("active_sequence")
        if isinstance(relation.get("active_sequence"), dict)
        else {}
    )

    previous_answer = _clean_text(
        target_sequence.get("last_april_answer")
        or relation.get("previous_april_turn")
        or (state or {}).get("last_april_turn")
    )
    previous_user = _clean_text(
        target_sequence.get("last_user_turn")
        or relation.get("previous_user_turn")
        or (state or {}).get("last_user_turn")
    )
    topic = _clean_text(
        target_sequence.get("topic")
        or relation.get("target_topic")
        or relation.get("active_topic")
    )

    entity = _clean_text(relation.get("resolved_entity"))
    entity_source = _clean_text(relation.get("resolved_entity_source"))
    target_artifact = (
        relation.get("target_artifact")
        if isinstance(relation.get("target_artifact"), dict)
        else {}
    )
    resolved_reference_type = _clean_text(
        relation.get("resolved_reference_type")
        or (
            "artifact"
            if target_artifact.get("present") and (
                relation.get("artifact_reference")
                or relation.get("reference")
                or entity_source == "active_dialogue_artifact"
            )
            else ""
        )
    )

    strategy = _infer_dialogue_mode(
        current_text,
        relation_name,
        operation=operation,
        reference=bool(
            relation.get("reference")
            or relation.get("artifact_reference")
        ),
        previous_answer=previous_answer,
        topic_similarity=float(relation.get("topic_similarity") or 0.0),
    )

    pairs = relation.get("sequence_pairs")
    pairs = pairs if isinstance(pairs, list) else []

    covered: list[str] = []
    seen = set()
    for pair in pairs[-8:]:
        if not isinstance(pair, dict):
            continue

        answer = _clean_text(
            pair.get("april_answer")
            or pair.get("april_meaning")
            or pair.get("answer_summary")
        )
        for sentence in _sentence_units(answer, limit=6):
            key = sentence.lower().strip()
            if not key or key in seen:
                continue
            seen.add(key)
            covered.append(sentence)
            if len(covered) >= 12:
                break
        if len(covered) >= 12:
            break

    if previous_answer and not covered:
        covered = _sentence_units(previous_answer, limit=8)

    recent_turns: list[dict[str, Any]] = []
    for pair in pairs[-6:]:
        if not isinstance(pair, dict):
            continue
        recent_turns.append({
            "user": _clean_text(
                pair.get("user_request") or pair.get("user_meaning")
            )[:220],
            "answer": _clean_text(
                pair.get("april_answer") or pair.get("april_meaning")
            )[:280],
        })

    current_coverage = 0.0
    if covered:
        current_coverage = max(
            _semantic_similarity(current_text, item)
            for item in covered
        )

    return {
        "version": "continuation_content_analysis_v3",
        "active": True,
        "mode": strategy["mode"],
        "intent": strategy.get("intent"),
        "new_information_required": bool(
            strategy["new_information_required"]
        ),
        "conversational_posture": strategy.get(
            "conversational_posture",
            "CONVERSE",
        ),
        "next_direction": strategy.get("next_direction"),
        "novelty_target": strategy["novelty_target"],
        "recap_ratio_max": strategy["recap_ratio_max"],
        "expertise_behavior": strategy.get("expertise_behavior"),
        "active_topic": topic,
        "active_entity": entity,
        "active_entity_source": entity_source,
        "resolved_reference_type": resolved_reference_type,
        "target_artifact": dict(target_artifact),
        "previous_user_turn": previous_user[:500],
        "previous_answer": previous_answer[:1800],
        "covered_content": covered,
        "covered_content_count": len(covered),
        "avoid_repeat_content": covered[:8],
        "recent_sequence_turns": recent_turns,
        "request_coverage_of_previous_content": round(
            float(current_coverage),
            6,
        ),
        "reference_signal": bool(
            relation.get("reference")
            or relation.get("artifact_reference")
        ),
        "artifact_reference": bool(relation.get("artifact_reference")),
        "artifact_noun_signal": bool(relation.get("artifact_noun_signal")),
        "user_turn_is_reaction": strategy["mode"] == "REACT",
        "source": "active_authenticated_dialogue_sequence",
        "memory_window": "day_0..day_6",
    }

def _apply_active_sequence_authority(
    result: dict[str, Any],
    state: dict[str, Any] | None,
) -> None:
    """Make the authenticated live sequence authoritative for CONTINUE turns."""
    if not isinstance(result, dict) or not isinstance(state, dict):
        return

    relation = _clean_text(
        result.get("dialogue_relation")
        or result.get("relation")
        or (result.get("dialogue_vector") or {}).get("three_way_relation")
    ).upper()
    if relation not in {"CONTINUE", "CONTINUE_TOPIC"}:
        return

    active = state.get("active_dialogue_sequence")
    if not isinstance(active, dict) or not active.get("sequence_id"):
        return

    active_id = _clean_text(active.get("sequence_id"))
    target_id = _clean_text(
        result.get("target_sequence_id")
        or (result.get("dialogue_vector") or {}).get("target_sequence_id")
        or active_id
    )
    # A CONTINUE can deliberately re-activate another user-owned thread. In
    # that case the selected target thread is authoritative for this turn and
    # must not be replaced by the older active sequence here.
    if active_id and target_id and target_id != active_id:
        return

    active_topic = _clean_text(active.get("topic") or state.get("april_active_topic"))
    last_user = _clean_text(active.get("last_user_request") or state.get("last_user_turn"))
    last_answer = _clean_text(active.get("last_april_answer") or state.get("last_april_turn"))

    # Never let an unrelated generic memory record become the active operand.
    result["sequence_id"] = active_id
    result["target_sequence_id"] = active_id
    result["active_topic"] = active_topic
    result["canonical_topic"] = active_topic or result.get("canonical_topic", "")
    result["previous_user_turn"] = last_user
    result["previous_april_turn"] = last_answer
    result["selected_memory_index"] = -1
    result["selected_memory_operand"] = {
        "source": "active_dialogue_sequence",
        "sequence_id": active_id,
        "sequence_topic": active_topic,
        "user_request": last_user,
        "april_answer": last_answer,
        "user_id": _clean_text(active.get("user_id") or state.get("user_id")),
        "conversation_id": _clean_text(active.get("conversation_id") or state.get("conversation_id")),
    }
    result["continuation_authority"] = "active_dialogue_sequence"
    result["historical_memory_is_evidence_only"] = True



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
        """
        Sequential semantic pass:
          1) scope authenticated user memory;
          2) choose active/older/new dialogue thread;
          3) resolve references inside that selected thread;
          4) expose the selected evidence downstream.
        """
        pairs = _collect_7d_dialogue(state)
        if history and not pairs:
            pairs = [h for h in history if isinstance(h, dict)]

        memory_field = _build_user_memory_field(state)
        if not memory_field.get("dialog_pairs_7d") and pairs:
            memory_field["dialog_pairs_7d"] = pairs[-24:]

        choice = _choose_dialogue_thread(text, memory_field, state)
        relation = choice["relation"]

        active = choice.get("active_sequence") or {}
        target_sequence = (
            choice.get("target_sequence")
            if isinstance(choice.get("target_sequence"), dict)
            else active
        )

        active_id = _clean_text(choice.get("active_sequence_id"))
        target_id = _clean_text(choice.get("target_sequence_id"))

        active_profile = choice.get("active_profile") or {}
        target_profile = target_sequence if isinstance(target_sequence, dict) else {}

        # A NEW topic has no prior-thread operand. The old active sequence may
        # influence the routing decision, but it must not leak into the
        # provider-facing conversational memory fields.
        if relation == "NEW":
            target_profile = {}

        latest_user = _clean_text(
            target_profile.get("last_user_turn")
            or target_profile.get("last_user_request")
            or active.get("last_user_request")
            or state.get("last_user_turn")
        )
        latest_april = _clean_text(
            target_profile.get("last_april_answer")
            or active.get("last_april_answer")
            or state.get("last_april_turn")
        )

        current_topic = _clean_text(choice.get("current_topic"))
        active_topic = _clean_text(choice.get("active_topic"))

        target_topic = _clean_text(
            target_profile.get("topic")
            or active_topic
            or current_topic
        )

        reference = bool(choice.get("reference_signal"))
        explicit_recall = bool(choice.get("explicit_recall"))
        explicit_new = bool(choice.get("explicit_new"))

        topic_similarity = max(
            _semantic_similarity(text, active_topic),
            _semantic_similarity(current_topic, active_topic)
            if current_topic and active_topic else 0.0,
            _semantic_similarity(text, latest_user) if latest_user else 0.0,
            _semantic_similarity(text, latest_april) if latest_april else 0.0,
        )

        selected = {}
        if relation == "RECALL":
            turns = target_profile.get("turns") or []
            if isinstance(turns, list) and turns:
                selected = dict(turns[-1])
        elif relation == "CONTINUE":
            if isinstance(target_profile, dict) and target_profile.get("turns"):
                turns = target_profile.get("turns") or []
                selected = dict(turns[-1]) if turns else {}
            elif target_profile.get("sequence_id"):
                selected = {
                    "sequence_id": target_profile.get("sequence_id"),
                    "sequence_topic": target_profile.get("topic"),
                    "user_request": target_profile.get("last_user_turn"),
                    "april_answer": target_profile.get("last_april_answer"),
                    "sequence_turn_index": len(target_profile.get("turns") or []),
                    "created_at": target_profile.get("last_created_at"),
                    "source": "selected_dialogue_thread",
                }
            elif active.get("sequence_id"):
                selected = {
                    "sequence_id": active.get("sequence_id"),
                    "sequence_topic": active.get("topic"),
                    "user_request": active.get("last_user_request"),
                    "april_answer": active.get("last_april_answer"),
                    "sequence_turn_index": active.get("turn_count"),
                    "created_at": active.get("last_turn_at"),
                    "source": "active_dialogue_sequence",
                }

        sequence_pairs = (
            target_profile.get("turns")
            if relation in {"RECALL", "CONTINUE"}
            else []
        )
        sequence_pairs = (
            sequence_pairs if isinstance(sequence_pairs, list) else []
        )

        if relation == "NEW":
            target_id = _new_vector_id(
                state,
                current_topic or _extract_topic(text) or text[:180],
                text,
            )

        selected_topic = _clean_text(
            selected.get("sequence_topic")
            or selected.get("topic")
            or target_topic
        )

        entity, entity_source = _entity_from_relation_context(
            text,
            latest_april,
            selected_topic,
            state=state,
            relation_context={
                **choice,
                "target_sequence": target_profile,
            },
        )

        resolved_reference = (
            entity
            if reference or choice.get("artifact_signal")
            else ""
        )
        target_artifact = choice.get("target_artifact") if isinstance(choice.get("target_artifact"), dict) else {}
        resolved_reference_type = ""
        if choice.get("artifact_signal") or (
            isinstance(target_artifact, dict) and target_artifact.get("present")
        ):
            if target_artifact.get("kind") == "poem":
                resolved_reference_type = "artifact"
            elif target_artifact.get("kind"):
                resolved_reference_type = "artifact"
        elif resolved_reference:
            resolved_reference_type = "entity"

        return {
            "relation": relation,
            "confidence": round(float(choice.get("confidence") or 0.0), 6),
            "reason": choice.get("reason"),
            "active_sequence": active,
            "target_sequence": target_profile,
            "active_sequence_id": active_id,
            "target_sequence_id": target_id,
            "thread_transition": (
                "REACTIVATED_OLDER"
                if relation == "CONTINUE"
                and target_id
                and active_id
                and target_id != active_id
                else "ACTIVE"
                if relation == "CONTINUE"
                else "NEW"
            ),
            "active_topic": active_topic,
            "target_topic": (
                current_topic
                if relation == "NEW"
                else selected_topic
                if relation in {"RECALL", "CONTINUE"}
                else active_topic or current_topic
            ),
            "current_topic": current_topic,
            "previous_user_turn": latest_user,
            "previous_april_turn": latest_april,
            "topic_similarity": round(float(topic_similarity or 0.0), 6),
            "topic_novelty": round(
                _semantic_similarity(current_topic, active_topic)
                if current_topic and active_topic else 0.0,
                6,
            ),
            "reference": reference,
            "explicit_recall": explicit_recall,
            "explicit_new": explicit_new,
            "artifact_reference": bool(
                choice.get("artifact_signal")
                or choice.get("artifact_noun_signal")
            ),
            "resolved_reference_type": resolved_reference_type,
            "target_artifact": target_artifact,
            "selected_memory_index": -1,
            "selected_memory_operand": selected,
            "resolved_reference": resolved_reference,
            "resolved_entity": entity,
            "resolved_entity_source": entity_source,
            "sequence_pairs": sequence_pairs[-8:],
            "memory_field": {
                "engine": memory_field.get("engine"),
                "window": memory_field.get("window"),
                "user_id": memory_field.get("user_id"),
                "conversation_id": memory_field.get("conversation_id"),
                "active_sequence_id": active_id,
                "target_sequence_id": target_id,
                "active_turns": len(
                    memory_field.get("active_sequence_pairs") or []
                ),
                "seven_day_turns": len(
                    memory_field.get("dialog_pairs_7d") or []
                ),
                "topic_evidence_A_E": (
                    memory_field.get("topic_evidence_A_E") or []
                )[-8:],
                "summary_available": bool(
                    memory_field.get("memory_summary_evidence")
                ),
                "summary_preview": _clean_text(
                    memory_field.get("memory_summary_evidence")
                )[:600],
                "a_e_topics_count": len(
                    memory_field.get("topic_evidence_A_E") or []
                ),
                "evidence_only": True,
            },
            "thread_choice": {
                "relation": relation,
                "reason": choice.get("reason"),
                "active_score": choice.get("active_score", 0.0),
                "best_historical_score": choice.get("best_historical_score", 0.0),
                "best_historical_sequence_id": choice.get(
                    "best_historical_sequence_id",
                    "",
                ),
                "reference_signal": reference,
                "artifact_signal": bool(choice.get("artifact_signal")),
                "artifact_noun_signal": bool(choice.get("artifact_noun_signal")),
                "subject_signal": bool(choice.get("subject_signal")),
                "target_sequence_id": target_id,
                "target_artifact": target_artifact,
                "resolved_reference_type": resolved_reference_type,
                "thread_transition": (
                    "REACTIVATED_OLDER"
                    if target_id and active_id and target_id != active_id
                    else "ACTIVE"
                ),
            },
        }

    @staticmethod
    def _infer_representation(text: str) -> str:
        low = text.lower()
        if re.search(r"\b(код|python|пайтон|скрипт)\b", low):
            return "code"
        if re.search(r"\b(ссыл\w*|url|link)\b", low):
            return "link"
        if re.search(r"\b(картинк\w*|изображени\w*|портрет\w*|фото)\b", low):
            return "image"
        if re.search(r"\b(нарисуй|изобрази|draw)\b", low):
            if re.search(r"\b(схем\w*|чертеж\w*|чертёж\w*)\b", low):
                return "diagram"
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
        current_explicit_reps = _explicit_current_representations(current)
        artifact_continuation = bool(
            relation_name in {"CONTINUE", "RECALL"}
            and (relation.get("artifact_reference") or relation.get("artifact_noun_signal"))
            and active_representation
            and (
                self._operation(current, active_representation) in {"modify", "build", "present", "calculate"}
                or bool(re.search(r"\b(?:добавь|убери|измени|исправь|переделай|продли|продолжи|перерисуй|обнови|покажи)\b", current.lower()))
            )
        )
        if representation == "text" and not current_explicit_reps and artifact_continuation:
            # Artifact continuation is the only case where the previous render
            # modality can become the current production modality.
            representation = active_representation

        operation = self._operation(current, representation)
        goal = self._goal(operation, representation)

        active_topic = _clean_text(relation.get("active_topic"))
        target_topic = _clean_text(relation.get("target_topic") or active_topic)
        if relation_name == "NEW":
            topic = _extract_topic(current) or target_topic or current[:180]
        elif relation_name in {"RECALL", "CONTINUE"}:
            # A CONTINUE may reactivate an older user-owned thread. In that case
            # the selected target thread, not the previously active topic, owns
            # the current topic/context.
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
        target_sequence_id = _clean_text(
            relation.get("target_sequence_id") or sequence_id
        )
        resolved_entity = _clean_text(
            relation.get("resolved_entity")
            or relation.get("resolved_reference")
            or ""
        )
        entity_source = _clean_text(
            relation.get("resolved_entity_source")
        )
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
            "artifact_reference": bool(
                relation.get("artifact_reference")
            ),
            "artifact_noun_signal": bool(
                relation.get("artifact_noun_signal")
            ),
            "resolved_entity": resolved_entity,
            "resolved_entity_source": entity_source,
            "resolved_reference_type": (
                "artifact" if relation.get("artifact_reference")
                else "entity" if resolved_entity
                else "none"
            ),
            "memory_engine": "QUANTUM-MEMORY-7D-V2",
            "memory_window": "day_0..day_6",
            "memory_resolution": relation.get("memory_field") or {},
            "thread_choice": relation.get("thread_choice") or {},
            "selected_memory_index": relation.get("selected_memory_index", -1),
            "selected_memory_operand": selected,
            "topic_similarity": relation.get("topic_similarity", 0.0),
            "topic_novelty": relation.get("topic_novelty", 0.0),
            "sequence_continuation_authorized": relation_name == "CONTINUE",
            "current_turn_authority": True,
            "historical_memory_is_evidence_only": True,
            "memory_engine": "QUANTUM-MEMORY-7D-V2",
            "memory_window": "day_0..day_6",
            "target_sequence_id": target_sequence_id,
            "resolved_entity": resolved_entity,
            "resolved_entity_source": entity_source,
            "resolved_reference_type": (
                "artifact" if relation.get("artifact_reference")
                else "entity" if resolved_entity
                else "none"
            ),
            "memory_resolution": relation.get("memory_field") or {},
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

        compound_representations = list(current_explicit_reps)
        if representation != "text" and representation not in compound_representations:
            compound_representations.insert(0, representation)
        if not compound_representations:
            compound_representations = [representation if representation != "text" else "text"]
        requested_outputs = list(dict.fromkeys(compound_representations))
        scene_composition = ["text"] + [x for x in requested_outputs if x != "text"]

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
            "active_sequence": relation.get("active_sequence") or {},
            "target_sequence": relation.get("target_sequence") or {},
            "active_sequence_id": _clean_text(relation.get("active_sequence_id")),
            "sequence_id": sequence_id,
            "target_sequence_id": target_sequence_id,
            "thread_transition": relation.get("thread_transition", "ACTIVE"),
            "resolved_entity": resolved_entity,
            "resolved_entity_source": entity_source,
            "resolved_reference_type": (
                "artifact" if relation.get("artifact_reference")
                else "entity" if resolved_entity
                else "none"
            ),
            "artifact_reference": bool(relation.get("artifact_reference")),
            "artifact_noun_signal": bool(relation.get("artifact_noun_signal")),
            "target_artifact": relation.get("target_artifact") or {},
            "thread_choice": relation.get("thread_choice") or {},
            "memory_resolution": relation.get("memory_field") or {},
            "target_sequence_id": target_sequence_id,
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
            "explicit_task": bool(current_explicit_reps or raw_representation != "text"),
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
                "target_sequence_id": target_sequence_id,
                "resolved_entity": resolved_entity,
                "resolved_entity_source": entity_source,
                "resolved_reference_type": (
                    "artifact" if relation.get("artifact_reference")
                    else "entity" if resolved_entity
                    else "none"
                ),
                "memory_engine": "QUANTUM-MEMORY-7D-V2",
                "memory_window": "day_0..day_6",
                "memory_resolution": relation.get("memory_field") or {},
                "thread_choice": relation.get("thread_choice") or {},
                "resolved_request": current,
                "resolved_reference": relation.get("resolved_reference", ""),
            "artifact_reference": bool(relation.get("artifact_reference")),
            "artifact_noun_signal": bool(relation.get("artifact_noun_signal")),
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
                "target_sequence_id": target_sequence_id,
                "topic": topic,
                "relation_reason": relation.get("reason"),
                "topic_similarity": relation.get("topic_similarity", 0.0),
                "thread_choice": relation.get("thread_choice") or {},
            },
            "memory_integration": {
                "engine": "QUANTUM-MEMORY-7D-V2",
                "window": "day_0..day_6",
                "user_scoped": True,
                "active_sequence_id": relation.get("active_sequence_id", ""),
                "target_sequence_id": target_sequence_id,
                "authority_order": [
                    "current_user_turn",
                    "selected_dialogue_thread",
                    "seven_day_user_memory",
                    "A_E_topic_memory",
                    "memory_summary_evidence",
                ],
                "summary_evidence_available": bool(
                    (relation.get("memory_field") or {}).get(
                        "summary_available"
                    )
                ),
                "evidence_only": True,
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
            "continuation_content_analysis": {
                "version": "continuation_content_analysis_v2",
                "active": False,
                "mode": "NONE",
                "new_information_required": False,
            },
            "dialogue_strategy": {
                "mode": "NEW",
                "intent": "independent_request",
                "new_information_required": False,
                "conversational_posture": "ANSWER",
                "next_direction": "answer_current_request",
                "source": "fallback",
            },
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
            return _repair_interpretation_result(result, text, state=state)

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
    return _repair_interpretation_result(result, text, state=state)


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
    "2026-09-22-seven-day-dialogue-vector-memory-presentation-sync-v1"
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
