# -*- coding: utf-8 -*-
"""
APRIL — canonical interpretation compatibility bridge
======================================================

This file must live at:
    blocks/interpretation_layer.py

It restores the public `interpret_request` entry point expected by
`core/executor.py` and places the current-turn authority fence at the
module boundary.

The heavy semantic engine remains in:
    blocks/April_interpretation_layer_dialogue_synced.py

No second semantic engine is created here.
"""

from __future__ import annotations

import importlib
import re
from copy import deepcopy
from typing import Any


_BASE_MODULE_NAME = (
    f"{__package__}.April_interpretation_layer_dialogue_synced"
    if __package__
    else "April_interpretation_layer_dialogue_synced"
)

_base = importlib.import_module(_BASE_MODULE_NAME)

# Re-export the complete public surface of the canonical engine.
for _name in dir(_base):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_base, _name)


# ---------------------------------------------------------------------------
# Current-turn authority / contaminated request protection
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
)


def _clean_current_text(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text


def _has_internal_prompt_material(value: Any) -> bool:
    text = str(value or "")
    return any(marker in text for marker in _INTERNAL_PROMPT_MARKERS)


def _seq_payload(result: dict[str, Any]) -> dict[str, Any]:
    vector = result.get("dialogue_vector")
    if not isinstance(vector, dict):
        return {}
    sequential = vector.get("sequential_dialogue")
    if isinstance(sequential, dict):
        return sequential
    return {}


def _trajectory_payload(result: dict[str, Any]) -> dict[str, Any]:
    vector = result.get("dialogue_vector")
    if not isinstance(vector, dict):
        return {}
    trajectory = vector.get("trajectory")
    if isinstance(trajectory, dict):
        return trajectory
    sequential = vector.get("sequential_dialogue")
    if isinstance(sequential, dict):
        trajectory = sequential.get("trajectory")
        if isinstance(trajectory, dict):
            return trajectory
    return {}


def _current_turn_is_independent(result: dict[str, Any]) -> bool:
    """
    Detect the exact failure shape seen in the 2026-09-21 Railway log:

        CONTINUE
        self_contained=True
        explicit_reference=False
        grammatical_anaphora=False
        pending_input=False
        explicit_task=False

    In that shape, the current user message owns the turn.
    """
    sequential = _seq_payload(result)
    trajectory = _trajectory_payload(result)

    relation = str(
        sequential.get("relation")
        or result.get("dialogue_relation")
        or result.get("relation")
        or ""
    ).upper()

    self_contained = bool(
        trajectory.get("self_contained")
        or sequential.get("self_contained")
        or result.get("self_contained")
    )

    explicit_reference = bool(
        trajectory.get("explicit_reference")
        or sequential.get("explicit_reference")
        or result.get("reference_to_previous")
    )

    grammatical_anaphora = bool(
        trajectory.get("grammatical_anaphora")
        or sequential.get("grammatical_anaphora")
    )

    pending_input = bool(
        trajectory.get("pending_input")
        or sequential.get("pending_input")
    )

    explicit_task = bool(
        trajectory.get("explicit_task")
        or sequential.get("explicit_task")
    )

    no_reference_evidence = not (
        explicit_reference
        or grammatical_anaphora
        or pending_input
        or explicit_task
    )

    return bool(
        relation in {"CONTINUE", "CONTINUE_TOPIC"}
        and self_contained
        and no_reference_evidence
    )


def _explicit_current_structured_request(text: str) -> bool:
    """
    Only direct current-turn wording can authorize a structured representation.

    This is deliberately narrow: historical renderer state never counts as
    authorization.
    """
    low = _clean_current_text(text).lower()

    direct_groups = (
        # visual
        "нарисуй", "изобрази", "покажи схему", "покажи график",
        "построй график", "построй диаграмму", "сделай диаграмму",
        "нарисовать", "изображение",
        # mathematical structure
        "формул", "формулу", "уравнен", "график функции",
        "таблиц", "таблицу",
        # code / structured output
        "код", "python", "json", "markdown",
        "ссылк", "видео", "аудио", "файл",
        # explicit English requests
        "draw ", "plot ", "chart ", "diagram ", "table ", "formula ",
        "equation ", "show a graph", "show the graph",
    )

    return any(token in low for token in direct_groups)


def _force_text_representation_for_plain_information(
    result: dict[str, Any],
    current_text: str,
) -> None:
    """
    When the semantic layer accidentally inherited a structured representation
    from an unrelated previous turn, erase that stale representation before the
    result crosses the interpretation boundary.

    This does not touch genuinely structured current-turn requests.
    """
    if _explicit_current_structured_request(current_text):
        return

    # This is a plain information/explanation request when the current turn does
    # not explicitly request a structured artifact. Historical structured state
    # must not upgrade it.
    text_like_operations = {
        "answer", "explain", "analyze", "retrieve", "summarize",
        "list", "present", "",
    }

    operation = str(
        result.get("operation")
        or result.get("active_operation")
        or result.get("best_operation")
        or ""
    ).lower()

    production = str(
        result.get("representation")
        or result.get("production")
        or result.get("subtype")
        or result.get("scene_type")
        or ""
    ).lower()

    # Do not reinterpret a genuinely explicit current structured request.
    # For plain informational requests, stale structured output is unsafe.
    if operation in text_like_operations or not operation:
        stale_structured = production in {
            "formula", "graph", "diagram", "image", "gallery", "table",
            "code", "link", "audio", "video", "file", "action", "scene",
            "memory", "visual_context",
        }
        if stale_structured:
            result["representation"] = "text"
            result["production"] = "text"
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
                result["presentation"] = presentation


def _repair_result(result: Any, current_text: str) -> Any:
    if not isinstance(result, dict):
        return result

    text = _clean_current_text(current_text)
    if not text:
        return result

    # ---------------------------------------------------------------
    # 1. Absolute request-operand rule:
    #    internal continuation prose must never leave this module.
    # ---------------------------------------------------------------
    resolved = result.get("resolved_request")
    if _has_internal_prompt_material(resolved):
        result["resolved_request"] = text
        result["request_operand"] = text
        result["request_operand_source"] = "current_user_turn"
        result["request_operand_sanitized"] = True
    else:
        # Even for a clean result, keep the canonical operand equal to the
        # current user request. Historical context belongs in structured fields.
        result["resolved_request"] = text
        result["request_operand"] = text
        result["request_operand_source"] = "current_user_turn"

    # ---------------------------------------------------------------
    # 2. Exact Railway regression: false CONTINUE on a self-contained turn.
    # ---------------------------------------------------------------
    independent = _current_turn_is_independent(result)

    if independent:
        result["continuation"] = False
        result["reference_to_previous"] = False
        result["context_dependency"] = "independent"
        result["dialogue_relation"] = "NEW"
        result["relation"] = "NEW_TOPIC"
        result["resolved_reference"] = ""
        result["continuation_target"] = ""
        result["reply_to"] = result.get("reply_to") if not result.get("reply_to") else ""
        result["history_dependent_task"] = False

        vector = result.get("dialogue_vector")
        if isinstance(vector, dict):
            vector = dict(vector)
            vector.update({
                "relation": "NEW_TOPIC",
                "topic_relation": "NEW_TOPIC",
                "request_relation": "NEW_TOPIC",
                "request_dependency": "independent",
                "continuation": False,
                "reference_to_previous": False,
                "three_way_relation": "NEW",
                "selected_memory_operand": {},
                "selected_memory_index": -1,
                "resolved_reference": "",
                "resolved_request": text,
                "request_operand": text,
                "request_operand_source": "current_user_turn",
                "historical_memory_is_evidence_only": True,
                "current_turn_authority": True,
                "forced_new_topic": True,
                "forced_new_topic_reason": (
                    "self_contained_without_reference_evidence"
                ),
            })

            sequential = vector.get("sequential_dialogue")
            if isinstance(sequential, dict):
                sequential = dict(sequential)
                sequential["relation"] = "NEW"
                sequential["subtype"] = "NEW_TOPIC"
                sequential["selected_pair"] = {}
                sequential["selected_memory_index"] = -1
                sequential["resolved_reference"] = ""
                sequential["confidence"] = max(
                    float(sequential.get("confidence", 0.0) or 0.0),
                    0.50,
                )
                vector["sequential_dialogue"] = sequential

            result["dialogue_vector"] = vector

        # Historical scene must remain evidence only, not the new scene.
        result["previous_scene_id"] = ""
        result["reuse_existing_scene"] = False
        result["render_continuity"] = {
            "relation": "NEW",
            "reuse_existing_scene": False,
            "reuse_recalled_memory": False,
            "selected_memory_index": -1,
            "previous_scene_id": "",
            "previous_render_types": [],
            "avoid_repeat": True,
        }

    # ---------------------------------------------------------------
    # 3. Never carry a stale renderer into a plain informational turn.
    # ---------------------------------------------------------------
    if independent:
        _force_text_representation_for_plain_information(result, text)

    # ---------------------------------------------------------------
    # 4. Structured historical context is still retained as evidence,
    #    but not encoded into the provider-facing request.
    # ---------------------------------------------------------------
    if independent:
        result["semantic_ownership"] = {
            "relation": "NEW_TOPIC",
            "owner": "current_request",
            "current_turn_authoritative": True,
            "stale_state_topic_ignored": True,
            "historical_memory_is_evidence_only": True,
            "request_operand_is_current_only": True,
        }

    return result


# ---------------------------------------------------------------------------
# Public API required by executor.py
# ---------------------------------------------------------------------------

def interpret_request(
    text,
    cognition=None,
    semantic=None,
    history=None,
    state=None,
):
    """
    Canonical compatibility entry point.

    All semantic work remains owned by the existing Quantum interpretation
    engine. This wrapper only enforces the current-turn boundary immediately
    after the engine returns.
    """
    result = _base.QUANTUM_INTERPRETATION_ENGINE.interpret(
        text,
        cognition=cognition,
        semantic=semantic,
        history=history,
        state=state,
    )
    return _repair_result(result, text)


# Public aliases expected by older callers.
_base_interpret_request = interpret_request


def build_semantic_dialog_profile(
    text,
    cognition=None,
    semantic=None,
    assistant_response=None,
    dialogue_history=None,
    vision_context=None,
):
    return {
        "input_text": text,
        "assistant_response": assistant_response,
        "dialogue_history": dialogue_history or [],
        "vision_context": vision_context or {},
        "active_goal": (cognition or {}).get("active_goal")
            or (semantic or {}).get("active_goal"),
        "active_topic": (cognition or {}).get("active_topic_slot")
            or (semantic or {}).get("current_topic"),
        "semantic_state": semantic or {},
        "requires_scene_builder": False,
        "profile_version": "quantum_matrix_compat_v1",
    }


def build_scene_construction_profile(semantic_profile):
    return {
        "requires_scene_builder": False,
        "scene_type": "dialogue",
        "dialogue_mode": "semantic_unified",
        "context_source": "quantum_matrix",
        "decision_owner": globals().get("DECISION_OWNER", "QUANTUM_INTERPRETATION"),
        "profile_version": "quantum_matrix_compat_v1",
    }


def build_scene_artifact_contract(semantic_profile, scene_profile):
    return {
        "contract": "scene_artifact",
        "transport": globals().get("TRANSPORT_NAME", "INTERPRETATION_TRANSPORT"),
        "semantic_profile": semantic_profile or {},
        "scene_profile": scene_profile or {},
        "representation": "processor_decides",
        "profile_version": "quantum_matrix_compat_v1",
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
            "transport": globals().get("TRANSPORT_NAME", "INTERPRETATION_TRANSPORT"),
            "scene_contract": "canonical",
        },
        "profile_version": "quantum_matrix_compat_v1",
    }


# Explicit compatibility marker for deploy diagnostics.
INTERPRETATION_COMPATIBILITY_VERSION = "2026-09-21-current-turn-boundary-v1"
INTERPRETATION_REQUEST_OPERAND_POLICY = "CURRENT_USER_TURN_ONLY"
INTERPRETATION_HISTORICAL_MEMORY_POLICY = "EVIDENCE_ONLY"


__all__ = [
    name
    for name in globals()
    if not name.startswith("_")
    and name not in {"importlib", "re", "deepcopy", "Any"}
]
