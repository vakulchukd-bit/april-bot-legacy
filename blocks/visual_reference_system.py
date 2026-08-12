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


def build_scene_snapshot(active_visual_scene: Any) -> Dict[str, Any]:
    if not isinstance(active_visual_scene, dict) or not active_visual_scene:
        return {"exists": False}
    return {
        "exists": True,
        "scene_type": _text(active_visual_scene.get("scene_type")),
        "objects": list(active_visual_scene.get("objects") or [])[:8],
        "summary": _text(active_visual_scene.get("summary"))[:600],
        "atmosphere": _text(active_visual_scene.get("atmosphere"))[:240],
        "continuity_weight": _clamp(active_visual_scene.get("continuity_weight", 0.0)),
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

    scene = build_scene_snapshot(state.get("active_visual_scene"))
    signals = detect_visual_context(semantic, cognition, reasoning, state)
    refs = build_scene_references(scene)

    explicit_generation = _contains(
        text,
        ("создай изображение", "сгенерируй изображение", "нарисуй картинку"),
    )
    unrelated_textual_request = not _contains(
        text,
        ("картин", "изображ", "референс", "схем", "график", "диаграм", "визуал"),
    )

    # Visual memory is retained, but it participates in the current turn only
    # when the dialogue evidence makes it relevant. An old active scene is not
    # itself evidence that the new request should be rendered visually.
    sem_reps = {
        str(x).lower()
        for x in (
            semantic.get("required_representations")
            or semantic.get("requested_representations")
            or []
        )
    }
    visual_representation = bool(
        sem_reps.intersection({"graph", "diagram", "gallery", "image"})
        or semantic.get("visual_routing")
        or semantic.get("explicit_image_generation_only")
    )
    relevant_continuation = bool(
        signals["continuity_signal"]
        and (
            semantic.get("context_visual_followup")
            or semantic.get("requested_representation") in {"graph", "diagram", "gallery", "image"}
            or semantic.get("artifact_reference")
        )
    )
    scene_relevant = bool(scene.get("exists") and (visual_representation or relevant_continuation))

    reuse_pressure = 0.0
    if scene_relevant:
        reuse_pressure += scene.get("continuity_weight", 0.0)
    if relevant_continuation:
        reuse_pressure += 0.25
    reuse_pressure = _clamp(reuse_pressure)

    if explicit_generation and unrelated_textual_request:
        reuse_pressure = 0.0
        scene_relevant = False

    return {
        "enabled": bool(scene_relevant or signals["renderer_signal"] or signals["exploration_signal"]),
        "memory_available": bool(scene.get("exists")),
        "memory_relevant": scene_relevant,
        "mode": (
            "visual_evidence"
            if scene_relevant or signals["renderer_signal"]
            else "context_support"
            if scene.get("exists")
            else None
        ),
        "references": refs,
        "scene_snapshot": scene,
        "signals": signals,
        "reuse_pressure": reuse_pressure,
        "visual_continuity": bool(signals["continuity_signal"]),
        "reference_priority": scene_relevant and reuse_pressure >= 0.55,
        "lightweight_mode": not explicit_generation,
        "should_generate": False,
        "generation_allowed": False,
        "suppress_generation": True,
        "visual_should_not_interrupt": True,
        "visual_is_supportive": True,
        "trajectory_aligned": True,
        "dialogue_centered": True,
        "semantic_inheritance": True,
        "provider_calls": 0,
        "decision_owner": DECISION_OWNER,
        "renderer_selection": "delegated",
        "generation_selection": "delegated",
        "machine_only": True,
    }
