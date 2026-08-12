"""
APRIL — COGNITION CORE / QUANTUM EVIDENCE V1

Role:
    Cognitive evidence provider for the Quantum Processor.

This module does NOT own:
    - routing
    - provider selection/calls
    - renderer selection
    - room selection
    - response generation
    - frontend rendering

It produces one compact cognition packet from:
    current request + dialogue + active flow + semantic evidence +
    visual continuity + memory/goal state.

Decision owner:
    QUANTUM_PROCESSOR
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from blocks.visual_memory_library import build_visual_memory_response
except Exception:
    build_visual_memory_response = None


APRIL_FILE_ID = "APRIL_COGNITION_QUANTUM_V1"
ROOM = "COGNITION_ROOM"
DECISION_OWNER = "QUANTUM_PROCESSOR"

COGNITION_TASK_CHANNEL = {
    "channel": "cognition_machine_task_channel",
    "isolated": True,
}
COGNITION_RESPONSE_CHANNEL = {
    "channel": "cognition_machine_response_channel",
    "isolated": True,
}

ACTION_WORDS = ("сделай", "создай", "исправь", "апгрейд", "улучши", "покажи")
VISUAL_WORDS = ("картинка", "схема", "график", "формула", "таблица", "пространство", "сцена")
HELP_WORDS = ("помоги", "подскажи", "не понимаю", "объясни")
RENDER_WORDS = ("график", "формула", "таблица", "renderer", "scene", "canvas")
TRAVEL_WORDS = ("где находится", "как добраться", "погода", "карта", "рейс")
META_WORDS = ("system prompt", "prompt leak", "roleplay assistant", "ты ии", "как chatgpt")
EXPLANATION_WORDS = ("объясни", "почему", "разбери", "расскажи", "как работает", "что означает", "анализ")
CONFUSION_WORDS = ("не понимаю", "запутался", "не получается", "ошибка", "не работает")
VISUAL_OBJECT_WORDS = (
    "объект", "предмет", "элемент", "человек", "мужчина", "женщина",
    "кот", "собака", "машина", "дом", "дерево",
)
VISUAL_ATTRIBUTE_WORDS = ("цвет", "цвета", "какого цвета", "размер", "форма", "выглядит")
VISUAL_ACTION_WORDS = ("делает", "занимается", "смотрит", "держит", "идет", "сидит", "стоит")
FOCUS_INTENT_WORDS = ("сделай", "исправь", "апгрейд", "анализ", "проверь", "найди", "объясни")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _low(value: Any) -> str:
    return _text(value).lower()


def _clamp(value: Any, minimum: float = 0.0, maximum: float = 1.0) -> float:
    try:
        number = float(value)
    except Exception:
        number = minimum
    return max(minimum, min(maximum, number))


def _contains(text: Any, words) -> bool:
    value = _low(text)
    return any(word in value for word in words)


def _increase(state: Dict[str, Any], key: str, amount: float) -> None:
    state[key] = _clamp(state.get(key, 0.0) + amount)


def _decrease(state: Dict[str, Any], key: str, amount: float) -> None:
    state[key] = _clamp(state.get(key, 0.0) - amount)


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def APRIL_LOG_IN(room: str = ROOM, metadata: Optional[Dict[str, Any]] = None) -> None:
    try:
        print({"type": "APRIL_LOG_IN", "room": room, "file": APRIL_FILE_ID, "metadata": metadata or {}})
    except Exception:
        pass


def APRIL_LOG_OUT(room: str = ROOM, metadata: Optional[Dict[str, Any]] = None) -> None:
    try:
        print({"type": "APRIL_LOG_OUT", "room": room, "file": APRIL_FILE_ID, "metadata": metadata or {}})
    except Exception:
        pass


def build_cognition_telemetry() -> Dict[str, Any]:
    return {
        "file_id": APRIL_FILE_ID,
        "room": ROOM,
        "continuity_safe": True,
        "trajectory_tracking": True,
        "render_detection": True,
        "dialog_analysis": True,
        "executor_connected": True,
        "decision_owner": DECISION_OWNER,
        "provider_calls": 0,
        "parallel_route": False,
    }


def detect_meta_ai_behavior(text: str) -> bool:
    return _contains(text, META_WORDS)


def build_dialog_continuity(dialog: List[Dict[str, Any]]) -> Dict[str, Any]:
    recent = list(dialog or [])[-12:]
    users = [m for m in recent if _low(m.get("role")) == "user"]

    requests: List[str] = []
    unresolved: List[str] = []
    uncertainty = 0.0
    reflection = False

    for message in users[-5:]:
        content = _text(message.get("content"))
        if not content:
            continue
        requests.append(content[:280])
        lowered = content.lower()

        if "?" in content or any(x in lowered for x in ("как", "почему", "что")):
            unresolved.append(content[:280])
        if any(x in lowered for x in ("не понимаю", "сложно", "запутался", "не уверен")):
            uncertainty += 0.25
        if any(x in lowered for x in ("думаю", "мне кажется", "как думаешь")):
            reflection = True

    return {
        "active_topics": [],
        "unresolved_questions": unresolved[-5:],
        "recent_user_requests": requests[-5:],
        "conversation_stage": "active",
        "multi_topic": len(users) >= 2,
        "user_waiting_answer": bool(unresolved),
        "dialog_momentum": _clamp(len(requests) * 0.12),
        "human_depth": _clamp(0.2 if reflection else 0.0),
        "user_uncertainty": _clamp(uncertainty),
        "user_reflection": reflection,
    }


def stabilize_trajectory(cognition: Dict[str, Any], active_flow: Any) -> Dict[str, Any]:
    if not active_flow:
        return cognition
    cognition.update({
        "needs_continuation": True,
        "trajectory_locked": True,
        "protects_user_trajectory": True,
        "dialogue_still_alive": True,
        "active_flow_strength": 0.85,
        "response_should_continue_naturally": True,
        "response_should_preserve_context": True,
    })
    _increase(cognition, "trajectory_confidence", 0.3)
    return cognition


def detect_render_intent(text: str) -> Dict[str, Any]:
    score = 0.85 if _contains(text, RENDER_WORDS) else 0.0
    return {"render_score": _clamp(score), "prefer_renderer": score >= 0.6}


def build_visual_mode(cognition: Dict[str, Any], visual_memory: Dict[str, Any]) -> Dict[str, Any]:
    enabled = bool(_dict(visual_memory).get("atmosphere"))
    return {
        "enabled": enabled,
        "reference_priority": enabled,
        "lightweight": enabled,
        "renderer_mode": False,
    }


def stabilize_dialog_behavior(cognition: Dict[str, Any]) -> Dict[str, Any]:
    if cognition.get("understands_user_goal"):
        cognition.update({
            "prefer_execution": True,
            "assistant_should_follow": True,
            "avoid_meta_behavior": True,
            "avoid_personality_overflow": True,
            "avoid_system_prompt_leakage": True,
            "avoid_self_reference": True,
            "response_should_focus_on_goal": True,
            "response_should_stay_grounded": True,
            "response_should_feel_human": True,
            "response_should_flow_naturally": True,
        })
        _decrease(cognition, "internal_noise", 0.2)
        _decrease(cognition, "signal_overload", 0.15)
    return cognition


def stabilize_cognition_state(cognition: Dict[str, Any]) -> Dict[str, Any]:
    strength = cognition.get("active_flow_strength", 0.0)
    if strength >= 0.5:
        cognition["scene_stability"] = _clamp(cognition.get("scene_stability", 0.5) + 0.25)
        cognition["internal_noise"] = _clamp(cognition.get("internal_noise", 0.0) - 0.2)
        cognition["signal_overload"] = _clamp(cognition.get("signal_overload", 0.0) - 0.15)
    return cognition


def build_visual_focus_analysis(text: str) -> Dict[str, bool]:
    value = _low(text)
    return {
        "visual_focus_request": _contains(value, ("этот", "эта", "это", "справа", "слева", "объект", "предмет")),
        "visual_attribute_request": _contains(value, VISUAL_ATTRIBUTE_WORDS),
        "visual_action_request": _contains(value, VISUAL_ACTION_WORDS),
        "visual_object_reference": _contains(value, VISUAL_OBJECT_WORDS),
    }


def build_visual_scene_bridge(state: Dict[str, Any]) -> Dict[str, Any]:
    scene = _dict(state.get("active_visual_scene"))
    anchor = _dict(scene.get("memory_anchor"))
    return {
        "scene_active": bool(scene),
        "scene_type": scene.get("scene_type"),
        "semantic_focus": scene.get("semantic_focus"),
        "visual_topic": anchor.get("topic"),
        "visual_object": anchor.get("object"),
        "visual_intent": anchor.get("intent"),
    }


def build_representation_understanding(text: str) -> Dict[str, Any]:
    value = _low(text)
    subject = "text"
    if "формул" in value:
        subject = "formula"
    elif "график" in value:
        subject = "graph"
    elif "таблиц" in value:
        subject = "table"

    mode = "discussion"
    if _contains(value, EXPLANATION_WORDS):
        mode = "explanation"
    elif _contains(value, ("построй", "нарисуй", "создай")):
        mode = "construction"

    return {
        "subject_type": subject,
        "interaction_mode": mode,
        "renderer_required": mode == "construction" and subject in {"formula", "graph", "table"},
        "renderer_candidate": subject != "text",
        "prefer_text_explanation": mode == "explanation",
    }


def build_dynamic_focus(text: str, continuity: Dict[str, Any]) -> Dict[str, Any]:
    requests = continuity.get("recent_user_requests", [])
    primary = requests[-1] if requests else _text(text)[:120]
    secondary = requests[-2] if len(requests) >= 2 else None
    return {
        "primary_focus": primary,
        "secondary_focus": secondary,
        "focus_strength": 0.85 if primary else 0.25,
    }


def build_goal_hierarchy(text: str, active_flow: Any) -> Dict[str, Any]:
    flow = _dict(active_flow)
    return {
        "strategic_goal": flow.get("trajectory"),
        "active_goal": _text(text)[:180],
        "local_task": _text(text)[:120],
    }


def build_open_loops(continuity: Dict[str, Any]) -> Dict[str, Any]:
    unresolved = continuity.get("unresolved_questions", [])
    return {
        "unfinished_tasks": unresolved[-5:],
        "open_loops_count": len(unresolved),
        "has_open_loops": bool(unresolved),
    }


def build_memory_signals(text: str, continuity: Dict[str, Any]) -> Dict[str, Any]:
    relevance = 0.8 if continuity.get("user_waiting_answer") else 0.5
    return {
        "memory_priority": _clamp(relevance),
        "memory_relevance": _clamp(relevance),
        "memory_weight": _clamp(relevance + 0.1),
        "forget_candidate": relevance < 0.35,
    }


def build_abcde_focus(text: str, continuity: Dict[str, Any], visual_focus: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    value = _text(text)
    visual = bool(visual_focus and any(visual_focus.values()))
    words = [w for w in value.split() if len(w) > 3]
    obj = words[-1][:80] if words else None
    intent = "action" if _contains(value, FOCUS_INTENT_WORDS) else "discussion"
    return {
        "topic": value[:120],
        "scene": "visual" if visual else "dialog",
        "object": obj,
        "focus": value[:120],
        "intent": intent,
        "focus_strength": 1.0 if continuity.get("user_waiting_answer") else 0.85,
    }


def build_focus_memory_priority(abcde: Dict[str, Any], continuity: Dict[str, Any]) -> float:
    weight = float(abcde.get("focus_strength", 0.5))
    if continuity.get("user_waiting_answer"):
        weight += 0.15
    return _clamp(weight)


def build_task_understanding(text: str, continuity: Dict[str, Any], visual_scene_bridge: Dict[str, Any]) -> Dict[str, Any]:
    value = _low(text)
    goal = "discussion"
    if "ошиб" in value:
        goal = "fix_error"
    elif "график" in value:
        goal = "build_graph"
    elif "формул" in value:
        goal = "work_with_formula"
    elif "таблиц" in value:
        goal = "build_table"
    elif "скрин" in value or "изображ" in value:
        goal = "analyze_visual"

    missing: List[str] = []
    if goal == "fix_error":
        missing.append("error_context")
    if goal == "build_graph":
        missing.append("formula")
    if goal == "analyze_visual" and not visual_scene_bridge.get("scene_active"):
        missing.append("image")

    return {
        "user_goal": goal,
        "goal_known": goal != "discussion",
        "missing_information": missing,
        "task_complete": not missing,
    }


def build_user_confusion(text: str) -> float:
    return _clamp(sum(0.25 for word in CONFUSION_WORDS if word in _low(text)))


def build_assistant_next_step(task_understanding: Dict[str, Any]) -> str:
    missing = task_understanding.get("missing_information", [])
    if "image" in missing:
        return "request_image"
    if "formula" in missing:
        return "request_formula"
    if "error_context" in missing:
        return "request_error_details"
    return "ready_to_help"


def build_scene_relation(text: str, active_scene: Any, dynamic_focus: Dict[str, Any]) -> Dict[str, Any]:
    value = _low(text)
    previous = _low(dynamic_focus.get("primary_focus"))
    continued = bool(previous and any(token in value for token in previous.split()[:3]))
    return {
        "continue_scene": continued,
        "temporary_branch": False,
        "return_to_previous_scene": False,
        "new_scene": not continued,
        "scene_confidence": 0.9 if continued else 0.5,
    }


def build_unified_scene_state_legacy(active_scene, dynamic_focus, goal_hierarchy, open_loops, memory_signals):
    return {
        "active_scene": active_scene or {},
        "dynamic_focus": dynamic_focus or {},
        "goal_hierarchy": goal_hierarchy or {},
        "open_loops": open_loops or [],
        "memory_signals": memory_signals or {},
    }


def build_cognitive_memory_bridge(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "focus_state": state.get("focus_state", {}),
        "memory_timeline": state.get("memory_timeline", {}),
        "memory_cycle": state.get("memory_cycle", {}),
        "dynamic_focus": state.get("dynamic_focus", {}),
        "goal_hierarchy": state.get("goal_hierarchy", {}),
        "open_loops": state.get("open_loops", []),
        "memory_signals": state.get("memory_signals", {}),
    }


def build_timeline_awareness(state: Dict[str, Any]) -> Dict[str, Any]:
    timeline = _dict(state.get("memory_timeline"))
    cycle = _dict(state.get("memory_cycle"))
    return {
        "utc_enabled": bool(cycle),
        "current_memory_day": cycle.get("current_day", "day_0"),
        "timeline_available": bool(timeline),
        "day0_active": bool(timeline.get("day_0")),
        "day1_available": bool(timeline.get("day_1")),
    }


def build_focus_evolution_v2(abcde_focus: Dict[str, Any], focus_state: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(abcde_focus or {})
    focus_state = _dict(focus_state)
    for key in ("priority_score", "intent_freshness", "active_topic"):
        if key in focus_state:
            merged[key] = focus_state[key]
    return merged


def build_executor_guidance(task_understanding, goal_hierarchy, memory_signals, timeline_awareness):
    return {
        "primary_goal": goal_hierarchy.get("active_goal"),
        "task_type": task_understanding.get("user_goal"),
        "goal_known": task_understanding.get("goal_known"),
        "memory_priority": memory_signals.get("memory_priority", 0.5),
        "utc_memory_active": timeline_awareness.get("utc_enabled", False),
        "executor_should_preserve_continuity": True,
        "executor_should_use_memory": True,
        "decision_owner": DECISION_OWNER,
    }


def build_contribution_state(artifacts: Any) -> Dict[str, List[Any]]:
    aggregated = {
        "scene_contributions": [],
        "focus_contributions": [],
        "memory_contributions": [],
        "trajectory_hints": [],
        "scene_hints": [],
    }
    for artifact in artifacts or []:
        context = _dict(_dict(artifact).get("context"))
        for key in aggregated:
            values = context.get(key, [])
            if isinstance(values, list):
                aggregated[key].extend(values)
    return aggregated


def build_contribution_cognition_bridge(artifacts: Any) -> Dict[str, Any]:
    state = build_contribution_state(artifacts)
    return {
        "contribution_state": state,
        "scene_contribution_count": len(state["scene_contributions"]),
        "focus_contribution_count": len(state["focus_contributions"]),
        "memory_contribution_count": len(state["memory_contributions"]),
        "contribution_pipeline_active": True,
    }


def analyze_cognition(text: str, state: dict, semantic: dict, reasoning: dict) -> Dict[str, Any]:
    """
    Produce cognition evidence only.

    The Quantum Processor receives this packet and performs the final fusion.
    """
    state = state if isinstance(state, dict) else {}
    semantic = semantic if isinstance(semantic, dict) else {}
    reasoning = reasoning if isinstance(reasoning, dict) else {}
    text = _text(text)
    lowered = text.lower()

    dialog = state.get("dialog", []) or []
    active_flow = state.get("active_flow")
    active_scene = state.get("active_scene", {}) or {}
    visual_continuity = state.get("visual_continuity_summary", {}) or {}

    continuity = build_dialog_continuity(dialog)
    visual_memory = (
        build_visual_memory_response(text)
        if callable(build_visual_memory_response)
        else {}
    )
    visual_mode = build_visual_mode({}, _dict(visual_memory))
    render_analysis = detect_render_intent(text)
    visual_focus = build_visual_focus_analysis(text)
    representation = build_representation_understanding(text)
    visual_scene_bridge = build_visual_scene_bridge(state)

    abcde = build_abcde_focus(text, continuity, visual_focus)
    if visual_scene_bridge.get("scene_active") and not abcde.get("object"):
        abcde["object"] = visual_scene_bridge.get("visual_object")

    dynamic_focus = {
        "primary_focus": abcde.get("focus"),
        "secondary_focus": abcde.get("object"),
        "focus_strength": abcde.get("focus_strength", 0.5),
        "abcde": abcde,
    }
    goal_hierarchy = build_goal_hierarchy(text, active_flow)
    task = build_task_understanding(text, continuity, visual_scene_bridge)
    confusion = build_user_confusion(text)
    next_step = build_assistant_next_step(task)
    open_loops = build_open_loops(continuity)
    memory = build_memory_signals(text, continuity)

    if visual_scene_bridge.get("scene_active"):
        memory.update({
            "visual_priority": 1.0,
            "visual_scene_alive": True,
            "memory_weight": _clamp(memory.get("memory_weight", 0.5) + 0.2),
        })

    wants_action = 0.8 if _contains(text, ACTION_WORDS) else 0.0
    wants_help = 0.8 if _contains(text, HELP_WORDS) else 0.0
    wants_visual = 0.8 if _contains(text, VISUAL_WORDS) else 0.0

    cognition = {
        "wants_action": wants_action,
        "wants_help": wants_help,
        "wants_visual": wants_visual,
        "wants_dialog": 0.0,
        "execution_pressure": 0.0,
        "scene_stability": 0.72,
        "internal_noise": 0.08,
        "signal_overload": 0.05,
        "prefer_execution": False,
        "prefer_visual": wants_visual >= 0.5,
        "prefer_renderer": render_analysis["prefer_renderer"],
        "renderer_space_active": render_analysis["prefer_renderer"],
        "needs_guidance": wants_help >= 0.5,
        "needs_continuation": False,
        "trajectory_locked": False,
        "trajectory_confidence": 0.0,
        "dialogue_still_alive": True,
        "response_should_feel_human": True,
        "response_should_flow_naturally": True,
        "response_should_continue_naturally": False,
        "response_should_reduce_robotic_tone": True,
        "tracks_multiple_topics": continuity["multi_topic"],
        "should_answer_in_order": False,
        "preserve_question_order": False,
        "avoid_topic_loss": True,
        "continuity_state": continuity,
        "visual_memory": visual_memory,
        "visual_mode": visual_mode,
        "machine_task_channel": COGNITION_TASK_CHANNEL,
        "machine_response_channel": COGNITION_RESPONSE_CHANNEL,
        "telemetry": build_cognition_telemetry(),
        "visual_focus": visual_focus,
        "visual_scene_bridge": visual_scene_bridge,
        "representation_understanding": representation,
        "focus_recommendation": dynamic_focus,
        "goal_analysis": goal_hierarchy,
        "loop_analysis": open_loops,
        "memory_analysis": memory,
        "active_scene": active_scene,
        "visual_continuity": visual_continuity,
        "scene_cognition_active": True,
        "task_understanding": task,
        "user_confusion": confusion,
        "assistant_next_step": next_step,
        "guidance_priority": confusion >= 0.5,
        "scene_confidence": 1.0 if visual_scene_bridge.get("scene_active") else 0.45,
    }

    if detect_meta_ai_behavior(text):
        cognition["assistant_restraint"] = 0.85
        _decrease(cognition, "internal_noise", 0.25)

    if _contains(text, TRAVEL_WORDS):
        cognition["internet_context_needed"] = True

    cognition = stabilize_trajectory(cognition, active_flow)

    if reasoning.get("continuation"):
        cognition["needs_continuation"] = True
    if reasoning.get("user_waiting_action"):
        cognition["prefer_execution"] = True

    cognition["understands_user_goal"] = bool(
        task.get("goal_known") or wants_action >= 0.5 or wants_help >= 0.5 or wants_visual >= 0.5
    )

    cognition = stabilize_dialog_behavior(cognition)
    cognition = stabilize_cognition_state(cognition)

    # Canonical evidence metadata: no final route/renderer/room decision here.
    cognition.update({
        "quantum_evidence": {
            "current_request": text,
            "dialogue": continuity,
            "focus": dynamic_focus,
            "goal": goal_hierarchy,
            "memory": memory,
            "visual": visual_scene_bridge,
            "representation": representation,
            "reasoning": reasoning,
        },
        "decision_owner": DECISION_OWNER,
        "provider_calls": 0,
        "parallel_route": False,
        "renderer_selection": "delegated",
        "room_selection": "delegated",
        "route_selection": "delegated",
        "factory_order": {},
    })

    # Keep compatibility fields, but explicitly mark them as soft evidence.
    cognition["soft_renderer_hint"] = render_analysis["prefer_renderer"]
    cognition["soft_visual_hint"] = wants_visual >= 0.5
    cognition["soft_execution_hint"] = wants_action >= 0.5
    cognition["soft_travel_hint"] = _contains(text, TRAVEL_WORDS)

    for key, value in list(cognition.items()):
        if isinstance(value, float):
            cognition[key] = _clamp(value)

    if isinstance(state, dict):
        state["cognition"] = cognition

    return cognition
