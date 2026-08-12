"""
APRIL — GOAL ENGINE / QUANTUM GOAL EVIDENCE V1

Role:
    Extract goal and trajectory evidence.

No final route, room, renderer, or execution authority.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional


APRIL_FILE_ID = "APRIL_GOAL_ENGINE_QUANTUM_V1"
DECISION_OWNER = "QUANTUM_PROCESSOR"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _low(value: Any) -> str:
    return _text(value).lower()


def _contains(text: Any, words: Iterable[str]) -> bool:
    value = _low(text)
    return any(word in value for word in words)


def _clamp(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except Exception:
        return 0.0


def build_goal_evidence(
    text: str,
    state: Dict[str, Any] | None = None,
    semantic: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    state = state if isinstance(state, dict) else {}
    semantic = semantic if isinstance(semantic, dict) else {}

    active_flow = state.get("active_flow") if isinstance(state.get("active_flow"), dict) else {}
    scene = state.get("scene_state") if isinstance(state.get("scene_state"), dict) else {}

    goal = _text(
        semantic.get("goal")
        or semantic.get("active_goal")
        or scene.get("goal")
        or ""
    )

    if not goal:
        goal = _text(text)

    exploration = _contains(
        text,
        ("пример", "примерно", "идея", "вариант", "атмосфера", "как думаешь"),
    )
    explicit_execution = _contains(
        text,
        ("сделай", "создай", "построй", "реши", "исправь", "вычисли"),
    )

    return {
        "goal": goal[:500],
        "active_goal": goal[:500],
        "trajectory": _text(
            scene.get("trajectory")
            or active_flow.get("type")
            or semantic.get("trajectory")
            or ""
        )[:300],
        "signals": {
            "exploration": float(exploration),
            "explicit_execution": float(explicit_execution),
            "continuation": float(bool(active_flow)),
            "ambiguity": _clamp(semantic.get("ambiguity_level", 0.0)),
        },
        "goal_should_persist": True,
        "goal_completed": False,
        "execution_decision": "delegated",
        "decision_owner": DECISION_OWNER,
        "provider_calls": 0,
        "machine_only": True,
    }


def detect_goal(
    text: str,
    state: Dict[str, Any],
    semantic: Dict[str, Any],
) -> Dict[str, Any]:
    """Compatibility entrypoint; enriches semantic with evidence only."""
    evidence = build_goal_evidence(text, state, semantic)
    semantic = semantic if isinstance(semantic, dict) else {}
    semantic["goal_evidence"] = evidence
    semantic["goal_continuity_active"] = True
    semantic["goal_persistence_mode"] = "evidence_only"
    semantic["decision_owner"] = DECISION_OWNER
    return semantic


def build_goal_snapshot(
    state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    state = state if isinstance(state, dict) else {}
    scene = state.get("scene_state") if isinstance(state.get("scene_state"), dict) else {}
    flow = state.get("active_flow") if isinstance(state.get("active_flow"), dict) else {}
    return {
        "goal": _text(scene.get("goal") or flow.get("type") or ""),
        "trajectory": _text(scene.get("trajectory") or ""),
        "active_flow_type": flow.get("type"),
        "machine_only": True,
        "decision_owner": DECISION_OWNER,
    }
