# ============================================================
# APRIL — QUANTUM CONTEXT COORDINATION SYSTEM V8
# ============================================================
"""
ROLE:
    Context evidence provider for the Quantum Processor.

ARCHITECTURAL LAW:
    This module does NOT decide intent, renderer, room, answer, or route.
    It extracts and compresses context evidence from the existing user
    state and hands one canonical context packet to the Quantum Processor.

SINGLE ROUTE:
    user input -> context evidence -> Quantum Processor
                -> MachineRequest -> Provider -> MachineResponse
                -> C-Artifact -> Factory -> SceneContract -> April Web

NO:
    second memory
    second router
    second executor
    renderer selection
    provider calls
    Telegram transport

The module keeps the existing public function names for compatibility.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional


FILE_ID = "APRIL_SCENE_CONTEXT_COORDINATION_SYSTEM"
ROOM = "CONTEXT_ROOM"
VERSION = "QUANTUM_CONTEXT_V8"

LOW_VALUE_MESSAGES = {
    "ок", "ага", "понял", "да", "ясно", "угу",
    "привет", "здравствуй", "как дела", "ты как",
    "как ты", "понятно", "спасибо", "нет", "хорошо",
}

CONTEXT_STOPWORDS = {
    "и", "а", "но", "или", "да", "же", "ли", "не", "ни",
    "что", "это", "этот", "эта", "эти", "тот", "та", "те",
    "как", "так", "про", "для", "при", "из", "на", "в", "во",
    "с", "со", "к", "у", "о", "об", "по", "до", "от", "за",
    "мне", "меня", "ты", "тебя", "я", "мы", "вы", "он", "она",
    "они", "его", "ее", "её", "их", "мой", "моя", "мое", "моё",
    "можешь", "можно", "нужно", "надо", "есть", "был", "была",
    "быть", "будет", "расскажи", "покажи", "скажи", "дай",
    "пожалуйста", "привет", "здравствуйте",
}

REFERENCE_MARKERS = {
    "помнишь", "вернемся", "вернёмся", "продолжим",
    "предыдущ", "прошлый", "прошлая", "прошлое", "прошлые",
    "тот", "та", "те", "его", "ее", "её", "это", "такой",
    "такая", "как раньше", "как тогда", "дальше", "снова",
    "повтори", "перепиши", "продолжи", "таблицу", "график",
    "формулу",
}

MAX_RELEVANT_MESSAGES = 20
MAX_DIALOG_SCAN = 40
MAX_PASSIVE_MEMORY = 10
MAX_SUMMARY_LENGTH = 1200
MAX_USER_MEMORY = 140
MAX_BOT_MEMORY = 180
MAX_IMAGE_HINT = 180
MAX_MATH_EXPR = 120
MAX_GOAL_LENGTH = 300


def APRIL_LOG_IN(room: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    try:
        print({"type": "APRIL_LOG_IN", "room": room, "file": FILE_ID,
               "version": VERSION, "metadata": metadata or {}})
    except Exception:
        pass


def APRIL_LOG_OUT(room: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    try:
        print({"type": "APRIL_LOG_OUT", "room": room, "file": FILE_ID,
               "version": VERSION, "metadata": metadata or {}})
    except Exception:
        pass


def normalize_text(text: Any) -> str:
    return str(text or "").strip()


def normalize_lower(text: Any) -> str:
    return normalize_text(text).lower()


def safe_slice(value: Any, limit: int) -> str:
    return normalize_text(value)[:max(0, int(limit))]


def contains_any(text: Any, words: Iterable[str]) -> bool:
    value = normalize_lower(text)
    return any(word in value for word in words)


def _tokens(value: Any) -> set[str]:
    words = re.findall(r"[a-zа-яё0-9]{4,}", normalize_lower(value))
    return {w for w in words if w not in CONTEXT_STOPWORDS}


def _is_low_information(text: Any) -> bool:
    value = normalize_lower(text)
    return not value or value in LOW_VALUE_MESSAGES or not _tokens(value)


def _is_reference(text: Any) -> bool:
    value = normalize_lower(text)
    return any(marker in value for marker in REFERENCE_MARKERS)


def _overlap(a: Any, b: Any) -> float:
    aa, bb = _tokens(a), _tokens(b)
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / max(1, min(len(aa), len(bb)))


def _state_dict(state: Any) -> Dict[str, Any]:
    return state if isinstance(state, dict) else {}


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def build_scene_focus_snapshot(state: Dict[str, Any]) -> Dict[str, Any]:
    scene = _dict(state.get("active_scene") or state.get("scene_state"))
    return {
        "goal": scene.get("active_goal") or scene.get("goal", ""),
        "topic": scene.get("active_topic") or scene.get("trajectory", ""),
        "visual": scene.get("visual_summary", ""),
        "last_visual_event": scene.get("last_visual_event", ""),
    }


def build_context_telemetry() -> Dict[str, Any]:
    return {
        "file_id": FILE_ID,
        "room": ROOM,
        "version": VERSION,
        "role": "CONTEXT_EVIDENCE_PROVIDER",
        "continuity_safe": True,
        "trajectory_sync": True,
        "renderer_continuity": True,
        "machine_context_active": True,
        "quantum_processor_owner": True,
        "decision_owner": "QUANTUM_PROCESSOR",
        "provider_calls": 0,
        "renderer_selection": "delegated",
    }


INPUT_MACHINE_CHANNEL = {
    "source": "executor",
    "type": "machine_context_input",
    "isolated": True,
}
OUTPUT_MACHINE_CHANNEL = {
    "target": "executor_rooms",
    "type": "machine_context_output",
    "isolated": True,
}


def build_machine_context_payload(
    trajectory: Any = None,
    scene_state: Optional[Dict[str, Any]] = None,
    active_flow: Optional[Dict[str, Any]] = None,
    visual_scene: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    scene = _dict(scene_state)
    return {
        "trajectory": trajectory,
        "scene_state": scene,
        "active_flow": _dict(active_flow),
        "visual_scene": _dict(visual_scene),
        "visual_focus": _dict(scene.get("visual_focus")),
        "machine_only": True,
        "human_visible": False,
        "context_role": "EVIDENCE_ONLY",
        "decision_owner": "QUANTUM_PROCESSOR",
        "telemetry": build_context_telemetry(),
    }


def _scene_topic(scene_state: Any) -> str:
    scene = _dict(scene_state)
    return normalize_text(
        scene.get("trajectory")
        or scene.get("active_topic")
        or ""
    )


def detect_topic_shift(
    text: Any,
    active_flow: Optional[Dict[str, Any]],
    scene_state: Optional[Dict[str, Any]],
) -> bool:
    current = normalize_text(text)
    if not current or _is_low_information(current) or _is_reference(current):
        return False
    topic = _scene_topic(scene_state)
    return bool(topic and _overlap(current, topic) == 0.0)


def archive_completed_flow(state: Dict[str, Any], active_flow: Optional[Dict[str, Any]]) -> None:
    if not active_flow:
        return
    memory = state.setdefault("passive_memory", [])
    flow_type = active_flow.get("type", "unknown")
    original = safe_slice(active_flow.get("original", ""), 120)
    trajectory = normalize_text(active_flow.get("trajectory"))
    item = f"[{flow_type}] {original}"
    if trajectory:
        item += f" :: {trajectory}"
    if item not in memory:
        memory.append(item)
    state["passive_memory"] = memory[-MAX_PASSIVE_MEMORY:]


def build_scene_block(scene_state: Optional[Dict[str, Any]]) -> str:
    scene = _dict(scene_state)
    lines: List[str] = []
    if scene.get("trajectory"):
        lines.append(f"Trajectory: {scene['trajectory']}")
    if scene.get("goal"):
        lines.append(f"Goal: {safe_slice(scene['goal'], MAX_GOAL_LENGTH)}")
    if scene.get("active_room"):
        lines.append(f"Room: {scene['active_room']}")
    if scene.get("orchestration_mode"):
        lines.append(f"Orchestration: {scene['orchestration_mode']}")
    if scene.get("continuity_mode"):
        lines.append(f"Continuity: {scene['continuity_mode']}")
    return "\nSCENE STATE:\n" + "\n".join(lines) if lines else ""


def build_visual_scene_block(active_visual_scene: Optional[Dict[str, Any]]) -> str:
    scene = _dict(active_visual_scene)
    if not scene:
        return ""
    lines = ["\nVISUAL CONTINUITY:"]
    if scene.get("scene_type"):
        lines.append(f"Scene: {scene['scene_type']}")
    if scene.get("summary"):
        lines.append(f"Summary: {safe_slice(scene['summary'], 300)}")
    objects = scene.get("objects") or []
    if objects:
        lines.append("Objects: " + ", ".join(map(str, objects[:20])))
    if scene.get("events_count") is not None:
        lines.append(f"Events: {scene['events_count']}")
    if scene.get("package"):
        lines.append(f"Package: {scene['package']}")
    if scene.get("last_event"):
        lines.append(f"Last Event: {safe_slice(scene['last_event'], 120)}")
    return "\n".join(lines)


def build_visual_focus_block(state: Dict[str, Any]) -> str:
    focus = _dict(state.get("visual_focus"))
    if not focus:
        return ""
    lines = ["\nACTIVE VISUAL FOCUS:"]
    if focus.get("focused_object"):
        lines.append(f"Focused Object: {focus['focused_object']}")
    if focus.get("question_type"):
        lines.append(f"Question Type: {focus['question_type']}")
    if focus.get("confidence") is not None:
        lines.append(f"Confidence: {focus['confidence']}")
    return "\n".join(lines)


def build_visual_summary_block(state: Dict[str, Any]) -> str:
    summary = _dict(state.get("visual_summary"))
    if not summary:
        return ""
    lines = ["\nVISUAL SUMMARY:"]
    if summary.get("scene_events_count") is not None:
        lines.append(f"Events: {summary['scene_events_count']}")
    if summary.get("package"):
        lines.append(f"Package: {summary['package']}")
    if summary.get("last_event"):
        lines.append(f"Last Event: {safe_slice(summary['last_event'], 120)}")
    return "\n".join(lines)


def build_visual_memory_block(state: Dict[str, Any]) -> str:
    timeline = _dict(state.get("memory_timeline"))
    memory = _dict(timeline.get("day_0")).get("visual_scenes", [])
    return f"\nVISUAL MEMORY:\nSnapshots: {len(memory)}" if memory else ""


def build_memory_timeline_block(state: Dict[str, Any]) -> str:
    timeline = _dict(state.get("memory_timeline"))
    if not timeline:
        return ""
    lines = ["\nMEMORY RECALL:"]
    day0, day1 = _dict(timeline.get("day_0")), _dict(timeline.get("day_1"))
    if day0:
        lines.append("Today Memory Active")
    if day1:
        lines.append("Yesterday Memory Available")
    return "\n".join(lines)


def build_base_context() -> str:
    return """
APRIL MACHINE CONTEXT

ROLE:
- context evidence provider;
- continuity stabilizer;
- user-space coordinator.

QUANTUM RULES:
- current request is authoritative;
- context supplies evidence, never a final decision;
- no renderer is selected here;
- no room is selected here;
- no provider is called here;
- no parallel route is created;
- historical context may clarify but never replace the current request.
"""


def build_current_request(text: Any, scene_state: Optional[Dict[str, Any]] = None) -> str:
    return (
        "CURRENT REQUEST — AUTHORITATIVE:\n"
        f"{normalize_text(text)}\n"
        "RULE: current request has highest semantic priority."
    )


def stabilize_active_flow(state: Dict[str, Any], scene_state: Dict[str, Any]) -> None:
    flow = state.get("active_flow")
    if not isinstance(flow, dict):
        return
    trajectory = _scene_topic(scene_state)
    if trajectory:
        flow["trajectory"] = trajectory
        flow["scene_bound"] = True
        flow["continuity_priority"] = True


def _v7_clear_stale_scene(state: Dict[str, Any], current_text: str) -> bool:
    scene = _dict(state.get("scene_state"))
    focus = _dict(state.get("focus_state"))
    dynamic = _dict(state.get("dynamic_focus"))
    old_topic = normalize_text(
        scene.get("trajectory")
        or focus.get("active_topic")
        or focus.get("primary_focus")
        or dynamic.get("primary_focus")
        or ""
    )
    if not old_topic or _is_low_information(current_text) or _is_reference(current_text):
        return False
    if _overlap(current_text, old_topic) > 0:
        return False

    scene["previous_topic"] = old_topic
    scene["previous_scene"] = dict(scene)
    for key in (
        "trajectory", "goal", "active_topic",
        "active_room", "active_scene_id", "topic_signature"
    ):
        scene[key] = ""
    state["scene_state"] = scene
    state["focus_state"] = {}
    state["dynamic_focus"] = {}
    state["active_visual_scene"] = None
    state["visual_focus"] = {}
    state["visual_summary"] = {}
    return True


def detect_dialog_intent(current_text: Any, state: Dict[str, Any]) -> str:
    text = normalize_lower(current_text)
    topic = normalize_lower(_scene_topic(state.get("scene_state")))
    if topic and topic in text:
        return "CONTINUE_TOPIC"
    if any(x in text for x in ("помнишь", "вернем", "вернём", "как раньше", "как тогда")):
        return "RETURN_TO_TOPIC"
    if any(x in text for x in ("аналог", "сравни", "как в прошл")):
        return "COMPARE_WITH_PAST"
    if any(x in text for x in ("тот", "эта", "предыдущ", "прошл")):
        return "REFERENCE_OBJECT"
    return "NEW_TOPIC"


def should_include_archived_memory(current_text: Any, state: Dict[str, Any]) -> bool:
    intent = detect_dialog_intent(current_text, state)
    return intent != "NEW_TOPIC"


def build_context_focus_snapshot(text: Any, state: Dict[str, Any]) -> Dict[str, Any]:
    focus = _dict(state.get("focus_state") or state.get("dynamic_focus"))
    scene = _dict(state.get("scene_state"))
    return {
        "active_topic": (
            focus.get("active_topic")
            or focus.get("primary_focus")
            or scene.get("trajectory")
            or ""
        ),
        "secondary_topic": focus.get("secondary_focus", ""),
        "focus_strength": focus.get("focus_strength", 0.0),
        "current_request": safe_slice(text, 500),
        "context_policy": "CURRENT_REQUEST_FIRST",
    }


def detect_context_refresh_needed(text: Any, state: Dict[str, Any]) -> bool:
    focus = _dict(state.get("focus_state") or state.get("dynamic_focus"))
    active = normalize_lower(focus.get("primary_focus", ""))
    return bool(active and _overlap(text, active) == 0.0)


def build_dynamic_focus_block(state: Dict[str, Any]) -> str:
    focus = _dict(state.get("focus_state") or state.get("dynamic_focus"))
    if not focus:
        return ""
    lines = ["\nDYNAMIC FOCUS:"]
    if focus.get("primary_focus"):
        lines.append(f"Primary Focus: {focus['primary_focus']}")
    if focus.get("secondary_focus"):
        lines.append(f"Secondary Focus: {focus['secondary_focus']}")
    if focus.get("focus_strength") is not None:
        lines.append(f"Focus Strength: {focus['focus_strength']}")
    return "\n".join(lines)


def build_unified_focus_block(state: Dict[str, Any]) -> str:
    focus = _dict(state.get("focus_state"))
    if not focus:
        return build_dynamic_focus_block(state)
    lines = ["\nFOCUS STATE:"]
    for key, label in (
        ("active_topic", "Active Topic"),
        ("active_goal", "Active Goal"),
        ("priority_score", "Priority"),
        ("intent_freshness", "Intent Freshness"),
    ):
        if focus.get(key) is not None and focus.get(key) != "":
            lines.append(f"{label}: {focus[key]}")
    return "\n".join(lines)


def build_visual_anchors_block(state: Dict[str, Any]) -> str:
    scene = _dict(state.get("active_visual_scene"))
    focus = _dict(state.get("visual_focus"))
    lines = ["\nVISUAL ANCHORS:"]
    if focus.get("focused_object"):
        lines.append(f"Focused Object: {focus['focused_object']}")
    objects = scene.get("objects") or []
    if objects:
        lines.append("Scene Objects: " + ", ".join(map(str, objects[:10])))
    return "" if len(lines) == 1 else "\n".join(lines)


def build_focus_priority_score(
    lowered: str,
    dynamic_focus: Dict[str, Any],
    visual_focus: Dict[str, Any],
    trajectory: Any,
) -> int:
    score = 0
    primary = normalize_lower(dynamic_focus.get("primary_focus"))
    secondary = normalize_lower(dynamic_focus.get("secondary_focus"))
    focused = normalize_lower(visual_focus.get("focused_object"))
    trajectory = normalize_lower(trajectory)
    if primary and primary in lowered:
        score += 8
    if secondary and secondary in lowered:
        score += 4
    if focused and focused in lowered:
        score += 6
    if trajectory and trajectory in lowered:
        score += 6
    return score


def calculate_context_priority(
    lowered: str,
    dynamic_focus: Dict[str, Any],
    visual_focus: Dict[str, Any],
    trajectory: Any,
) -> int:
    return build_focus_priority_score(
        lowered, dynamic_focus, visual_focus, trajectory
    )


def calculate_context_priority_v2(
    lowered: str,
    dynamic_focus: Dict[str, Any],
    visual_focus: Dict[str, Any],
    trajectory: Any,
    focus_state: Optional[Dict[str, Any]] = None,
) -> int:
    focus_state = _dict(focus_state)
    return calculate_context_priority(
        lowered, dynamic_focus, visual_focus, trajectory
    ) + int(focus_state.get("priority_score", 0) or 0)


def build_relevant_dialog(
    dialog: Optional[List[Dict[str, Any]]],
    text: Any,
    active_flow: Optional[Dict[str, Any]],
    scene_state: Optional[Dict[str, Any]],
) -> str:
    current = normalize_text(text)
    scene = _dict(scene_state)
    topic = _scene_topic(scene)
    selected: List[tuple[int, str]] = []

    for reverse_index, msg in enumerate(reversed((dialog or [])[-MAX_DIALOG_SCAN:])):
        content = normalize_text(msg.get("content"))
        if not content:
            continue
        score = 0
        if reverse_index == 0:
            score += 12
        elif reverse_index < 3:
            score += 8
        elif reverse_index < 6:
            score += 4
        if _overlap(current, content) > 0:
            score += 8
        if topic and _overlap(topic, content) > 0:
            score += 6
        if _is_reference(current):
            score += 3
        if score >= 6:
            selected.append(
                (
                    reverse_index,
                    f"{msg.get('role', 'user')}: {safe_slice(content, 500)}",
                )
            )

    selected.sort(key=lambda x: x[0], reverse=True)
    values = [x[1] for x in selected[:MAX_RELEVANT_MESSAGES]]
    values.reverse()
    return "\n".join(values)


def build_active_dialog(state: Dict[str, Any], text: Any = "") -> str:
    dialog = state.get("dialog") or []
    return build_relevant_dialog(
        dialog[-10:],
        text,
        state.get("active_flow"),
        state.get("scene_state"),
    )


def build_dialog_focus_block(state: Dict[str, Any], current_text: Any) -> str:
    scene = _dict(state.get("scene_state"))
    focus = _dict(state.get("focus_state") or state.get("dynamic_focus"))
    intent = detect_dialog_intent(current_text, state)
    return (
        "\nDIALOG FOCUS:\n"
        f"Goal: {scene.get('goal', '')}\n"
        f"Topic: {scene.get('trajectory', '')}\n"
        f"Vector: {focus.get('primary_focus', scene.get('trajectory', ''))}\n"
        f"Direction: {intent}"
    )


def compute_dialog_focus(state: Dict[str, Any], current_text: Any) -> Dict[str, Any]:
    scene = _dict(state.get("scene_state"))
    focus = _dict(state.get("focus_state") or state.get("dynamic_focus"))
    intent = detect_dialog_intent(current_text, state)
    return {
        "active_goal": scene.get("goal", ""),
        "active_topic": scene.get("trajectory", ""),
        "focus_vector": focus.get("primary_focus", scene.get("trajectory", "")),
        "direction_vector": {
            "continue": intent == "CONTINUE_TOPIC",
            "return": intent == "RETURN_TO_TOPIC",
            "new_topic": intent == "NEW_TOPIC",
        },
    }


def build_context_memory_bridge(state: Dict[str, Any]) -> Dict[str, Any]:
    timeline = _dict(state.get("memory_timeline"))
    return {
        "focus_state": _dict(state.get("focus_state")),
        "memory_timeline": timeline,
        "memory_cycle": _dict(state.get("memory_cycle")),
        "dynamic_focus": _dict(state.get("dynamic_focus")),
        "goal_hierarchy": _dict(state.get("goal_hierarchy")),
        "open_loops": state.get("open_loops", []),
        "memory_signals": _dict(state.get("memory_signals")),
        "visual_summary": _dict(state.get("visual_summary")),
        "active_visual_scene": _dict(state.get("active_visual_scene")),
        "today_visual_memory": _dict(timeline.get("day_0")).get("visual_scenes", []),
    }


def build_user_space(state: Dict[str, Any]) -> Dict[str, Any]:
    scene = _dict(state.get("scene_state"))
    return {
        "active_scene": scene,
        "dialog": state.get("dialog", []),
        "current_request": state.get("current_request"),
        "dynamic_focus": _dict(state.get("focus_state") or state.get("dynamic_focus")),
        "goal_hierarchy": _dict(state.get("goal_hierarchy")),
        "active_flow": _dict(state.get("active_flow")),
        "memory_timeline": _dict(state.get("memory_timeline")),
        "visual_summary": _dict(state.get("visual_summary")),
        "memory_summary": state.get("memory_summary", ""),
        "renderer_state": _dict(state.get("renderer_state")),
        "workspace_state": {
            "visual_scene": _dict(state.get("active_visual_scene")),
            "visual_focus": _dict(state.get("visual_focus")),
            "execution_mode": state.get("execution_mode"),
            "visual_mode": state.get("visual_mode"),
        },
    }


def build_scene_contract(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "version": 2,
        "user_space": build_user_space(state),
        "scene": _dict(state.get("scene_state")),
        "renderer_state": _dict(state.get("renderer_state")),
        "context_role": "EVIDENCE_ONLY",
        "decision_owner": "QUANTUM_PROCESSOR",
    }


def build_workspace_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "active_scene": _dict(state.get("scene_state")),
        "visual_summary": _dict(state.get("visual_summary")),
        "memory_summary": state.get("memory_summary", ""),
        "memory_timeline": _dict(state.get("memory_timeline")),
        "focus_state": _dict(state.get("focus_state") or state.get("dynamic_focus")),
        "active_flow": _dict(state.get("active_flow")),
        "renderer_state": _dict(state.get("renderer_state")),
    }


def build_executor_context_packet(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_space": build_user_space(state),
        "workspace_summary": build_workspace_summary(state),
        "scene_contract": build_scene_contract(state),
        "context_role": "EVIDENCE_ONLY",
        "decision_owner": "QUANTUM_PROCESSOR",
    }


def build_memory_context_evidence(state: Dict[str, Any], text: Any) -> Dict[str, Any]:
    """Compact quantum input: memory is evidence, not a decision."""
    dialog = state.get("dialog") or []
    substantive = _v7_latest_substantive_user_message(dialog)
    return {
        "has_memory": bool(state.get("memory_summary") or substantive),
        "latest_substantive_user": safe_slice(substantive, 500),
        "memory_summary": safe_slice(state.get("memory_summary", ""), 800),
        "reference_request": _is_reference(text),
    }


def _v7_latest_substantive_user_message(dialog: List[Dict[str, Any]]) -> str:
    for msg in reversed(dialog):
        if normalize_lower(msg.get("role")) not in {"user", "human"}:
            continue
        content = normalize_text(msg.get("content"))
        if content and not _is_low_information(content):
            return content
    return ""


def build_quantum_context_evidence(
    user_id: Any,
    text: Any,
    state: Dict[str, Any],
) -> Dict[str, Any]:
    """Single compact evidence surface consumed by Quantum Processor."""
    scene = _dict(state.get("scene_state"))
    focus = _dict(state.get("focus_state") or state.get("dynamic_focus"))
    visual = _dict(state.get("active_visual_scene"))
    return {
        "version": VERSION,
        "user_id": str(user_id) if user_id is not None else "",
        "current_request": normalize_text(text),
        "current_request_authoritative": True,
        "scene": {
            "trajectory": scene.get("trajectory", ""),
            "goal": safe_slice(scene.get("goal", ""), MAX_GOAL_LENGTH),
            "active_room": scene.get("active_room", ""),
            "active_scene_id": scene.get("active_scene_id", ""),
        },
        "focus": {
            "primary": focus.get("primary_focus") or focus.get("active_topic", ""),
            "secondary": focus.get("secondary_focus", ""),
            "strength": focus.get("focus_strength", 0.0),
        },
        "visual": {
            "scene_type": visual.get("scene_type", ""),
            "summary": safe_slice(visual.get("summary", ""), 300),
            "objects": list(visual.get("objects") or [])[:10],
        },
        "dialog_intent_evidence": detect_dialog_intent(text, state),
        "memory": build_memory_context_evidence(state, text),
        "topic_shift_evidence": detect_topic_shift(
            text, state.get("active_flow"), scene
        ),
        "decision_owner": "QUANTUM_PROCESSOR",
        "renderer_owner": "QUANTUM_PROCESSOR",
        "route_owner": "QUANTUM_PROCESSOR",
        "provider_calls": 0,
    }


def build_context_text(user_id: Any, text: Any, state: Dict[str, Any]) -> str:
    """
    Canonical textual context for the existing Provider path.

    It is intentionally compact. The Quantum Processor receives the
    structured evidence packet separately through _executor_context_packet.
    """
    text = normalize_text(text)
    state["current_request"] = text

    shifted = _v7_clear_stale_scene(state, text)
    scene = _dict(state.get("scene_state"))
    flow = state.get("active_flow")

    if detect_topic_shift(text, flow, scene) and not _is_reference(text):
        if flow:
            archive_completed_flow(state, flow)
        state["active_flow"] = None
        flow = None

    stabilize_active_flow(state, scene)

    relevant = build_relevant_dialog(
        state.get("dialog", []),
        text,
        flow,
        scene,
    )

    blocks = [
        build_base_context(),
        build_current_request(text, scene),
        build_scene_block(scene),
        build_dynamic_focus_block(state),
        build_dialog_focus_block(state, text),
        build_visual_scene_block(state.get("active_visual_scene")),
        build_visual_focus_block(state),
        build_visual_summary_block(state),
        build_visual_memory_block(state),
        build_memory_timeline_block(state),
        "ACTIVE DIALOG:\n" + build_active_dialog(state, text),
        "RELEVANT DIALOG:\n" + relevant,
    ]

    image = _dict(state.get("image_context"))
    hint = image.get("hint") or image.get("prompt")
    if hint and (_is_reference(text) or _overlap(text, hint) > 0):
        blocks.append("\nIMAGE CONTEXT:\n" + safe_slice(hint, MAX_IMAGE_HINT))

    math = _dict(state.get("last_math"))
    if math.get("expr"):
        blocks.append("\nMATH CONTEXT:\n" + safe_slice(math["expr"], MAX_MATH_EXPR))

    if state.get("passive_memory") and should_include_archived_memory(text, state):
        blocks.append(
            "\nARCHIVED TRAJECTORIES (REFERENCE ONLY):\n"
            + "\n".join(state["passive_memory"][-4:])
        )

    summary = state.get("memory_summary")
    if summary and (_is_reference(text) or _overlap(text, summary) > 0):
        blocks.append(
            "\nMEMORY SUMMARY (REFERENCE ONLY):\n"
            + safe_slice(summary, 800)
        )

    return "\n\n".join(x for x in blocks if x)


def update_memory_summary(state: Dict[str, Any], user_text: Any, bot_reply: Any) -> None:
    user = normalize_text(user_text)
    reply = normalize_text(bot_reply)
    if _is_low_information(user) or len(user) <= 2:
        return
    chunk = f"{safe_slice(user, MAX_USER_MEMORY)} → {safe_slice(reply, MAX_BOT_MEMORY)}"
    trajectory = _scene_topic(state.get("scene_state"))
    if trajectory:
        chunk = f"[{trajectory}] {chunk}"
    old = normalize_text(state.get("memory_summary"))
    if chunk in old:
        return
    combined = (old + " | " + chunk).strip()
    state["memory_summary"] = combined[-MAX_SUMMARY_LENGTH:]


def synchronize_scene_state(state: Dict[str, Any]) -> None:
    scene = _dict(state.get("scene_state"))
    flow = state.get("active_flow")
    trajectory = scene.get("trajectory")
    if isinstance(flow, dict) and trajectory:
        flow["trajectory"] = trajectory
    if scene.get("execution_mode"):
        state["execution_mode"] = scene["execution_mode"]
    if scene.get("visual_mode"):
        state["visual_mode"] = scene["visual_mode"]


def build_deephub_context(user_id: Any, text: Any, state: Dict[str, Any]) -> str:
    """
    Canonical entrypoint. One route, one user-space state, one evidence packet.
    """
    if not isinstance(state, dict):
        state = {}

    text = normalize_text(text)
    state["current_request"] = text
    synchronize_scene_state(state)

    evidence = build_quantum_context_evidence(
        user_id, text, state
    )

    machine_payload = build_machine_context_payload(
        trajectory=_scene_topic(state.get("scene_state")),
        scene_state=state.get("scene_state"),
        active_flow=state.get("active_flow"),
        visual_scene=state.get("active_visual_scene"),
    )

    machine_payload["quantum_evidence"] = evidence
    state["_machine_context"] = machine_payload

    packet = build_executor_context_packet(state)
    packet["current_request"] = text
    packet["context_focus"] = build_context_focus_snapshot(text, state)
    packet["quantum_evidence"] = evidence
    packet["context_policy"] = "CURRENT_REQUEST_FIRST"
    packet["decision_owner"] = "QUANTUM_PROCESSOR"
    packet["provider_calls"] = 0
    state["_executor_context_packet"] = packet

    return build_context_text(user_id, text, state)


def build_context_telemetry_v2(state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    state = _dict(state)
    evidence = _dict(_dict(state.get("_executor_context_packet")).get("quantum_evidence"))
    return {
        **build_context_telemetry(),
        "current_request_present": bool(state.get("current_request")),
        "quantum_evidence_present": bool(evidence),
        "parallel_route": False,
        "telegram_transport": False,
    }


# Compatibility aliases used by older callers.
FOCUS_FIRST_MODE = True
MIN_KEYWORD_LENGTH = 4
MAX_IMAGE_HINT = MAX_IMAGE_HINT
MAX_MATH_EXPR = MAX_MATH_EXPR
MAX_GOAL_LENGTH = MAX_GOAL_LENGTH

# V7 compatibility helpers.
_v7_tokens = _tokens
_v7_is_reference = _is_reference
_v7_is_low_information = _is_low_information
_v7_topic_overlap = _overlap
_CONTEXT_STOPWORDS_V7 = CONTEXT_STOPWORDS
_REFERENCE_MARKERS_V7 = REFERENCE_MARKERS
_LOW_INFORMATION_V7 = LOW_VALUE_MESSAGES
_CONTEXT_STOPWORDS = CONTEXT_STOPWORDS
