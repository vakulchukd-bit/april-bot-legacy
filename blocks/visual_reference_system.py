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
        "atmosphere": _text(source.get("atmosphere")),
        "continuity_weight": _clamp(source.get("continuity_weight", 0.65)),
        "render_block_types": list(source.get("render_block_types") or [])[:8],
        "scene_id": _text(source.get("scene_id")),
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

    scene_reference_text = " ".join(
        part for part in (
            scene.get("scene_type", ""),
            scene.get("summary", ""),
            " ".join(scene.get("objects", [])[:4]),
            str(scene.get("current_request", "")),
        ) if part
    ).strip()
    context_similarity = 0.0
    if scene.get("exists") and scene_reference_text:
        context_similarity = float(
            QUANTUM_EMBEDDING_ENGINE.similarity(text, scene_reference_text)["score"]
        )

    dialogue_contract = semantic.get("dialogue_contract", {}) if isinstance(semantic.get("dialogue_contract"), dict) else {}
    continuation_signal = bool(
        dialogue_contract.get("continuation")
        or dialogue_contract.get("reference_to_previous")
        or semantic.get("continuation")
    )
    explicit_reference = bool(
        dialogue_contract.get("reference_to_previous")
        or dialogue_contract.get("dialog_act") in {
            "continuation", "reference", "reformulation", "correction"
        }
    )

    scene_relevant = bool(
        scene.get("exists")
        and continuation_signal
        and (explicit_reference or context_similarity >= 0.46)
    )
    if not continuation_signal:
        scene_relevant = False

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
        "visual_is_supportive": True,
        "trajectory_aligned": True,
        "dialogue_centered": True,
        "semantic_inheritance": scene_relevant,
        "provider_calls": 0,
        "decision_owner": DECISION_OWNER,
        "renderer_selection": "delegated",
        "generation_selection": "delegated",
        "machine_only": True,
    }
