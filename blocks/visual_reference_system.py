"""
APRIL — VISUAL REFERENCE SYSTEM / QUANTUM VISUAL EVIDENCE V1

Role:
    Visual continuity and reference evidence provider.

Important:
    An active visual scene is context, not a command to reuse it.
    Final renderer/generation decisions belong to QUANTUM_PROCESSOR.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable

from blocks.interpretation_layer import QUANTUM_EMBEDDING_ENGINE


APRIL_FILE_ID = "APRIL_VISUAL_REFERENCE_QUANTUM_V1"
DECISION_OWNER = "QUANTUM_PROCESSOR"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _low(value: Any) -> str:
    return _text(value).lower()


def _contains(text: Any, values: Iterable[str]) -> bool:
    value = _low(text)
    return any(item in value for item in values)


def _clamp(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except Exception:
        return 0.0


def build_scene_snapshot(active_visual_scene: Any, active_scene_contract: Any = None) -> Dict[str, Any]:
    source = active_visual_scene if isinstance(active_visual_scene, dict) and active_visual_scene else (
        active_scene_contract if isinstance(active_scene_contract, dict) else {}
    )
    if not source:
        return {"exists": False}
    return {
        "exists": True,
        "scene_type": _text(source.get("scene_type") or source.get("active_scene")),
        "objects": list(source.get("objects") or [])[:8],
        "summary": _text(
            source.get("summary")
            or source.get("current_request")
            or source.get("answer")
        )[:900],
        "current_request": _text(source.get("current_request"))[:1200],
        "previous_scene_id": _text(source.get("previous_scene_id")),
        "atmosphere": _text(source.get("atmosphere")),
        "continuity_weight": _clamp(source.get("continuity_weight", 0.65)),
        "render_block_types": list(source.get("render_block_types") or [])[:8],
        "render_blocks": [
            dict(x) for x in list(source.get("render_blocks") or [])[:8]
            if isinstance(x, dict)
        ],
        "presentation_signals": [
            dict(x) for x in list(source.get("presentation_signals") or [])[:8]
            if isinstance(x, dict)
        ],
        "scene_id": _text(source.get("scene_id")),
        "semantic_state": dict(source.get("semantic_state") or {}) if isinstance(source.get("semantic_state"), dict) else {},
        "renderer_state": dict(source.get("renderer_state") or {}) if isinstance(source.get("renderer_state"), dict) else {},
    }


def build_scene_references(scene_snapshot: Dict[str, Any]) -> list[Dict[str, Any]]:
    if not scene_snapshot.get("exists"):
        return []
    refs: list[Dict[str, Any]] = []
    scene_type = scene_snapshot.get("scene_type")
    atmosphere = scene_snapshot.get("atmosphere")
    if scene_type:
        refs.append({"type": "scene", "title": scene_type, "weight": 0.70})
    if atmosphere:
        refs.append({"type": "atmosphere", "title": atmosphere, "weight": 0.60})
    for obj in scene_snapshot.get("objects", [])[:4]:
        refs.append({"type": "object", "title": _text(obj), "weight": 0.40})

    for block in scene_snapshot.get("render_blocks", [])[:6]:
        btype = _low(
            block.get("type")
            or block.get("artifact_type")
            or block.get("representation")
        )
        if btype and btype not in {"text", "markdown"}:
            payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
            refs.append({
                "type": "structured_visual",
                "title": _text(block.get("title") or payload.get("title") or btype),
                "representation": btype,
                "block_id": _text(block.get("block_id")),
                "payload": dict(payload),
                "weight": 0.75,
            })
    return refs


def detect_visual_context(
    semantic: Dict[str, Any],
    cognition: Dict[str, Any],
    reasoning: Dict[str, Any],
    state: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "scene_active": bool(state.get("active_visual_scene")),
        "renderer_signal": bool(
            semantic.get("visual_continuity")
            or semantic.get("render_intent")
            or semantic.get("prefer_renderer")
            or cognition.get("prefer_renderer")
            or cognition.get("renderer_space_active")
        ),
        "continuity_signal": bool(
            cognition.get("needs_continuation")
            or cognition.get("trajectory_locked")
            or semantic.get("continuation")
        ),
        "exploration_signal": bool(
            semantic.get("dialog_state") == "exploration"
            or cognition.get("needs_guidance")
        ),
        "dialogue_priority": bool(reasoning.get("unresolved_intent")),
    }


def build_visual_reference(
    semantic: Dict[str, Any],
    cognition: Dict[str, Any],
    text: str,
    state: Dict[str, Any],
) -> Dict[str, Any]:
    semantic = semantic if isinstance(semantic, dict) else {}
    cognition = cognition if isinstance(cognition, dict) else {}
    state = state if isinstance(state, dict) else {}
    reasoning = state.get("reasoning") if isinstance(state.get("reasoning"), dict) else {}

    scene = build_scene_snapshot(
        state.get("active_visual_scene"),
        state.get("active_scene_contract"),
    )
    signals = detect_visual_context(semantic, cognition, reasoning, state)
    refs = build_scene_references(scene)

    dialogue_contract = (
        semantic.get("dialogue_contract")
        if isinstance(semantic.get("dialogue_contract"), dict)
        else {}
    )
    scene_semantics = (
        semantic.get("scene_semantic_state")
        if isinstance(semantic.get("scene_semantic_state"), dict)
        else {}
    )
    scene_relation = (
        semantic.get("dialogue_relation")
        if isinstance(semantic.get("dialogue_relation"), dict)
        else {}
    )
    measurement = (
        semantic.get("quantum_dialogue_measurement")
        if isinstance(semantic.get("quantum_dialogue_measurement"), dict)
        else {}
    )
    measured_dialogue = (
        measurement.get("dialogue", {})
        if isinstance(measurement, dict)
        else {}
    )

    continuation_signal = bool(
        dialogue_contract.get("continuation")
        or dialogue_contract.get("reference_to_previous")
        or semantic.get("continuation")
        or scene_relation.get("continuation")
        or scene_relation.get("same_scene")
        or measured_dialogue.get("continuation_score", 0.0) >= 0.72
    )
    explicit_reference = bool(
        dialogue_contract.get("reference_to_previous")
        or dialogue_contract.get("dialog_act") in {
            "continuation", "reference", "reformulation", "correction"
        }
        or measured_dialogue.get("label") in {
            "continuation", "reference", "reformulation", "correction"
        }
    )

    context_dependency = _low(
        semantic.get("context_dependency")
        or dialogue_contract.get("context_dependency")
    )
    new_topic_guard = context_dependency in {"independent", "new_topic", "memory_query"}

    # A measured new/independent topic immediately releases the stored visual
    # scene from the current response context. The scene remains in 7D memory.
    if new_topic_guard and not continuation_signal and not explicit_reference:
        return {
            "enabled": bool(signals["renderer_signal"] or signals["exploration_signal"]),
            "memory_available": bool(scene.get("exists")),
            "memory_relevant": False,
            "mode": "new_topic",
            "references": [],
            "scene_snapshot": {"exists": False},
            "signals": signals,
            "context_similarity": 0.0,
            "continuation_signal": False,
            "explicit_reference": False,
            "reuse_pressure": 0.0,
            "visual_continuity": False,
            "reference_priority": False,
            "lightweight_mode": True,
            "should_generate": False,
            "generation_allowed": False,
            "suppress_generation": True,
            "visual_should_not_interrupt": True,
            "visual_is_supportive": False,
            "trajectory_aligned": True,
            "dialogue_centered": True,
            "context_dependency": context_dependency,
            "new_topic_guard": True,
            "semantic_inheritance": False,
            "provider_calls": 0,
            "decision_owner": DECISION_OWNER,
            "renderer_selection": "delegated",
            "generation_selection": "delegated",
            "machine_only": True,
        }

    # For a genuine continuation/reference, consume the semantic measurement
    # already produced by Interpretation when it is present. Otherwise make
    # one shared batch embedding measurement here.
    context_similarity = _clamp(
        max(
            float(scene_relation.get("confidence", 0.0) or 0.0),
            float(scene_relation.get("vector_similarity", 0.0) or 0.0),
            float(scene_relation.get("profile_similarity", 0.0) or 0.0),
        )
    )
    if scene.get("exists") and scene.get("summary") and context_similarity < 0.35:
        existing_measurement = (
            measurement.get("context_vectors", {})
            if isinstance(measurement, dict)
            else {}
        )
        measured_scene_score = (
            existing_measurement.get("active_visual_scene", {}).get("score")
            if isinstance(existing_measurement.get("active_visual_scene"), dict)
            else None
        )
        if measured_scene_score is not None:
            context_similarity = max(context_similarity, _clamp(measured_scene_score))
        else:
            scene_reference_text = " ".join(
                part for part in (
                    scene.get("scene_type", ""),
                    scene.get("summary", ""),
                    " ".join(scene.get("objects", [])[:4]),
                    scene.get("current_request", ""),
                ) if part
            ).strip()
            if scene_reference_text:
                context_similarity = max(
                    context_similarity,
                    float(
                        QUANTUM_EMBEDDING_ENGINE.similarities(
                            text,
                            [scene_reference_text],
                        ).get(scene_reference_text, 0.0)
                    ),
                )

    scene_relevant = bool(
        scene.get("exists")
        and not new_topic_guard
        and continuation_signal
        and (explicit_reference or context_similarity >= 0.46)
    )

    reuse_pressure = _clamp(
        0.55 * context_similarity
        + 0.25 * scene.get("continuity_weight", 0.65)
        + 0.20 * float(explicit_reference)
    ) if scene_relevant else 0.0

    return {
        "enabled": bool(scene_relevant or signals["renderer_signal"] or signals["exploration_signal"]),
        "memory_available": bool(scene.get("exists")),
        "memory_relevant": scene_relevant,
        "mode": "visual_evidence" if scene_relevant else (
            "context_support" if scene.get("exists") else None
        ),
        "references": refs if scene_relevant else [],
        "scene_snapshot": scene if scene_relevant else {"exists": False},
        "signals": signals,
        "context_similarity": context_similarity,
        "continuation_signal": continuation_signal,
        "explicit_reference": explicit_reference,
        "reuse_pressure": reuse_pressure,
        "visual_continuity": scene_relevant,
        "reference_priority": scene_relevant and reuse_pressure >= 0.55,
        "lightweight_mode": True,
        "should_generate": False,
        "generation_allowed": False,
        "suppress_generation": True,
        "visual_should_not_interrupt": True,
        "visual_is_supportive": scene_relevant,
        "trajectory_aligned": True,
        "dialogue_centered": True,
        "context_dependency": context_dependency or "unresolved",
        "new_topic_guard": new_topic_guard,
        "semantic_inheritance": scene_relevant,
        "scene_semantic_state": scene_semantics if scene_relevant else {},
        "scene_relation": scene_relation,
        "provider_calls": 0,
        "decision_owner": DECISION_OWNER,
        "renderer_selection": "delegated",
        "generation_selection": "delegated",
        "machine_only": True,
    }

