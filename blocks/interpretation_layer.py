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
from pathlib import Path
from typing import Any


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

        return getattr(_FallbackInterpretationEngine(), name)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        module = _load_canonical_engine_module()
        if module is not None:
            engine = getattr(module, "QUANTUM_INTERPRETATION_ENGINE", None)
            if callable(engine):
                return engine(*args, **kwargs)
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

    result = _FALLBACK_ENGINE.interpret(
        text,
        cognition=cognition,
        semantic=semantic,
        history=history,
        state=state,
    )
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
            "2026-09-21-lazy-engine-current-turn-fence-v2",
    }

    if name in fallback_public:
        return fallback_public[name]

    if hasattr(_FALLBACK_ENGINE, name):
        return getattr(_FALLBACK_ENGINE, name)

    raise AttributeError(
        f"module {_THIS_MODULE!r} has no attribute {name!r}"
    )


INTERPRETATION_COMPATIBILITY_VERSION = (
    "2026-09-21-lazy-engine-current-turn-fence-v2"
)
INTERPRETATION_REQUEST_OPERAND_POLICY = "CURRENT_USER_TURN_ONLY"
INTERPRETATION_HISTORICAL_MEMORY_POLICY = "EVIDENCE_ONLY"

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
