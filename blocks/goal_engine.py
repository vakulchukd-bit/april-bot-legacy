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

    scene_semantics = semantic.get("scene_semantic_state")
    scene_semantics = scene_semantics if isinstance(scene_semantics, dict) else {}
    task_phase = _text(scene_semantics.get("task_phase"))
    operation = _text(scene_semantics.get("operation"))
    exploration = 1.0 if task_phase in {"proposal", "explanation"} else 0.0
    execution_mass = 1.0 if task_phase == "execution" else 0.0
    modification_mass = 1.0 if task_phase == "modification" else 0.0

    return {
        "goal": goal[:500],
        "active_goal": goal[:500],
        "trajectory": _text(
            scene.get("trajectory")
            or active_flow.get("type")
            or semantic.get("trajectory")
            or operation
            or ""
        )[:300],
        "task_phase": task_phase,
        "operation": operation,
        "requested_representation": _text(
            scene_semantics.get("requested_representation")
            or semantic.get("requested_representation")
            or ""
        ),
        "signals": {
            "exploration": float(exploration),
            "execution": float(execution_mass),
            "modification": float(modification_mass),
            "continuation": float(bool(active_flow) or bool(scene_semantics.get("inherited_operation"))),
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



def evaluate_goal_progress(
    text: str,
    state: Dict[str, Any] | None = None,
    semantic: Dict[str, Any] | None = None,
    *,
    response: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Read-only evaluation of goal completion and whether a difficult completed turn
    merits a natural synthesis. Full memory remains owned by the existing state system.
    """
    state = state if isinstance(state, dict) else {}
    semantic = semantic if isinstance(semantic, dict) else {}
    response = response if isinstance(response, dict) else {}

    contract = semantic.get("dialogue_contract") if isinstance(semantic.get("dialogue_contract"), dict) else {}
    task = semantic.get("interactive_task_state") if isinstance(semantic.get("interactive_task_state"), dict) else {}
    if not task:
        task = state.get("interactive_task_state") if isinstance(state.get("interactive_task_state"), dict) else {}

    answer = _text(response.get("answer") or response.get("content") or state.get("last_april_turn"))
    blocks = response.get("render_blocks") if isinstance(response.get("render_blocks"), list) else []
    reps = {
        _low(item.get("type") or item.get("artifact_type"))
        for item in blocks if isinstance(item, dict)
    }

    status = _low(task.get("status"))
    phase = _low(task.get("phase") or task.get("task_phase"))
    task_completed = bool(task.get("completed")) or status == "completed" or phase == "completed"
    has_result = bool(answer)
    structured_result = bool(reps & {"image", "diagram", "graph", "table", "formula", "code", "link", "file"})

    history = task.get("qa_history") if isinstance(task.get("qa_history"), list) else []
    turn_count = max(len(history), int(task.get("task_revision") or 0))
    revision_count = int(task.get("task_revision") or 0)
    kind = _low(task.get("kind"))

    complexity = 0.0
    complexity += min(0.30, turn_count * 0.06)
    complexity += min(0.25, revision_count * 0.08)
    if structured_result or _low(semantic.get("visual_production_mode")) in {"image_generation", "diagram", "graph", "table"}:
        complexity += 0.18
    if kind in {"logic_riddle", "riddle", "game", "problem", "research", "complex_task"}:
        complexity += 0.18
    if contract.get("continuation"):
        complexity += 0.08
    complexity = _clamp(complexity)

    completed = bool(task_completed and has_result)
    eligible_if_completed = bool(
        complexity >= 0.55
        and (turn_count >= 3 or revision_count >= 2 or structured_result or kind in {"logic_riddle", "complex_task", "research"})
    )
    closure_allowed = bool(completed and eligible_if_completed)

    frame = semantic.get("semantic_frame") if isinstance(semantic.get("semantic_frame"), dict) else {}
    topic = _text(
        frame.get("topic")
        or contract.get("canonical_topic")
        or semantic.get("active_topic")
        or state.get("april_active_topic")
        or task.get("topic")
        or semantic.get("normalized_text")
    )[:220]
    representation = _low(frame.get("representation") or semantic.get("visual_production_mode") or "text")
    achievement = "получен готовый результат"
    if representation in {"diagram", "graph", "table", "formula", "code", "image"}:
        achievement = f"получен готовый результат в формате {representation}"

    return {
        "version": "april_goal_progress_v2",
        "goal": _text(frame.get("goal") or contract.get("active_goal") or semantic.get("active_goal") or text)[:320],
        "topic": topic,
        "status": "achieved" if completed else "in_progress",
        "goal_completed": completed,
        "difficulty_score": complexity,
        "turn_count": turn_count,
        "revision_count": revision_count,
        "structured_result": structured_result,
        "closure": {
            "eligible_if_completed": eligible_if_completed,
            "allowed_now": closure_allowed,
            "topic": topic,
            "achievement": achievement,
            "instruction": (
                "Только при действительно трудном завершённом результате естественно назвать тему и сказать, чего удалось добиться вместе; не употреблять обезличенное 'задача решена' и не делать такой итог после обычных простых ответов."
            ),
        },
        "evidence_only": True,
    }
