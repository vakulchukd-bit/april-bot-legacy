"""
APRIL — INTENT RESOLVER / QUANTUM EVIDENCE V1

Role:
    Lightweight trajectory/continuity evidence layer.

The Resolver observes:
    dialogue history + current request + active flow + semantic context.

It does NOT own:
    - final intent;
    - execution;
    - room selection;
    - renderer selection;
    - provider selection;
    - route selection.

Final decision owner:
    QUANTUM_PROCESSOR

Single route:
    USER -> CONTEXT/SEMANTIC EVIDENCE -> QUANTUM PROCESSOR ->
    EXECUTOR/ARTIFACT -> SCENE CONTRACT -> APRIL WEB
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional


APRIL_FILE_ID = "APRIL_INTENT_RESOLVER_QUANTUM_V1"
DECISION_OWNER = "QUANTUM_PROCESSOR"

INPUT_MACHINE_CHANNEL = {
    "source": "executor_semantic_pipeline",
    "type": "intent_resolution_input",
    "isolated": True,
}

OUTPUT_MACHINE_CHANNEL = {
    "target": "executor_orchestration_pipeline",
    "type": "intent_resolution_output",
    "isolated": True,
}

INTENT_RESOLVER_LOGS: List[Dict[str, Any]] = []
MAX_INTENT_RESOLVER_LOGS = 120


def log_resolver_event(event: str, payload: Optional[Dict[str, Any]] = None) -> None:
    try:
        INTENT_RESOLVER_LOGS.append({
            "timestamp": time.time(),
            "event": event,
            "payload": payload or {},
            "file_id": APRIL_FILE_ID,
            "machine_only": True,
        })
        if len(INTENT_RESOLVER_LOGS) > MAX_INTENT_RESOLVER_LOGS:
            del INTENT_RESOLVER_LOGS[:-MAX_INTENT_RESOLVER_LOGS]
    except Exception:
        pass


def normalize(text: Any) -> str:
    return str(text or "").strip().lower()


def build_machine_task(text: str, mode: str = "generic") -> Dict[str, Any]:
    normalized = normalize(text)
    payload = {
        "raw": text,
        "normalized": normalized,
        "mode": mode,
        "semantic_ready": True,
        "continuation_safe": True,
        "machine_context": {
            "length": len(normalized),
            "contains_math": bool(re.search(
                r"(?:\d\s*[\+\-\*/]\s*\d|y\s*=|sin\s*\(|cos\s*\(|tan\s*\(|x\^)",
                normalized,
            )),
            "contains_visual": any(
                x in normalized
                for x in ("картин", "изображ", "фото", "схема", "график", "диаграм")
            ),
        },
        "machine_only": True,
        "decision_owner": DECISION_OWNER,
    }
    log_resolver_event("machine_task_created", {
        "mode": mode,
        "normalized": normalized[:80],
    })
    return payload


def is_explicit(text: str) -> bool:
    t = normalize(text)
    if not t:
        return False

    keywords = (
        "реши", "посчитай", "вычисли", "найди значение",
        "построй график", "реши уравнение", "вычисли выражение",
    )
    if any(word in t for word in keywords):
        return True

    patterns = (
        r"\d+\s*[\+\-\*/]\s*\d+",
        r"y\s*=",
        r"sin\s*\(",
        r"cos\s*\(",
        r"tan\s*\(",
        r"x\^",
    )
    return any(re.search(pattern, t) for pattern in patterns)


def is_reference(text: str) -> bool:
    t = normalize(text)
    words = (
        "да", "ок", "давай", "с этого", "начни", "поехали",
        "продолжай", "вот", "ага", "примерно", "ближе",
        "уже лучше", "не то", "дальше", "еще", "ещё",
    )
    if t in words:
        return True
    return len(t) <= 20 and any(x in t for x in words)


def contradicts(last: str, task: str = "") -> bool:
    t = normalize(last)
    triggers = (
        "не надо", "забудь", "отмена", "другое", "погоди",
        "стой", "остановись", "не это", "не то",
    )
    return bool(t and any(trigger in t for trigger in triggers))


def find_explicit_task(history: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not history:
        return None

    for msg in reversed(history[-10:]):
        text = msg.get("content", "")
        if is_explicit(text):
            log_resolver_event("explicit_task_restored")
            return build_machine_task(text, mode="explicit_task")
    return None


def _evidence(
    *,
    mode: str,
    text: str,
    confidence: float,
    source: str,
    context: Optional[Dict[str, Any]] = None,
    machine_task: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    result = {
        "mode": mode,
        "text": text,
        "confidence": max(0.0, min(1.0, confidence)),
        "source": source,
        "machine_context": context or {},
        "machine_only": True,
        "decision_owner": DECISION_OWNER,

        # These are descriptive evidence fields, not final commands.
        "execution_candidate": mode == "execute",
        "continuation_candidate": mode == "continuation",
        "dialogue_candidate": mode == "dialog",
        "trajectory_reset_candidate": bool(
            (context or {}).get("trajectory_reset")
        ),

        "route_selection": "delegated",
        "room_selection": "delegated",
        "renderer_selection": "delegated",
        "provider_selection": "delegated",
        "provider_calls": 0,
        "parallel_route": False,
    }

    if machine_task is not None:
        result["machine_task"] = machine_task

    result["quantum_evidence"] = {
        "current_request": text,
        "mode_signal": mode,
        "confidence": result["confidence"],
        "source": source,
        "context": result["machine_context"],
        "machine_task": machine_task or {},
        "decision_owner": DECISION_OWNER,
    }
    return result


def resolve_input(
    history: List[Dict[str, Any]],
    state: Optional[dict] = None,
) -> Dict[str, Any]:
    """
    Produce continuity/trajectory evidence.

    This function intentionally does not hard-route the request.
    A previous task is evidence, not permission to replace the current request.
    """
    log_resolver_event("resolver_started")
    state = state if isinstance(state, dict) else {}
    active_flow = state.get("active_flow") or {}

    if not history:
        return _evidence(
            mode="dialog",
            text="",
            confidence=0.0,
            source="empty",
            context={"empty_history": True},
        )

    last = str(history[-1].get("content", "") or "")
    task = find_explicit_task(history)
    t = normalize(last)

    # A cancellation/change signal resets trajectory evidence.
    if contradicts(last, task["raw"] if task else ""):
        log_resolver_event("trajectory_reset")
        return _evidence(
            mode="dialog",
            text=last,
            confidence=0.90,
            source="contradiction",
            context={
                "trajectory_reset": True,
                "current_request_authoritative": True,
            },
        )

    # Short continuation is evidence that the current active flow may matter.
    if is_reference(last):
        if active_flow:
            flow_type = active_flow.get("type")
            log_resolver_event("active_flow_continuation", {
                "flow_type": flow_type,
            })
            return _evidence(
                mode="continuation",
                text=last,
                confidence=0.82,
                source="active_flow",
                context={
                    "trajectory_active": True,
                    "flow_type": flow_type,
                    "preserve_current_scene_as_evidence": True,
                },
            )

        if task:
            log_resolver_event("semantic_restore_evidence")
            return _evidence(
                mode="continuation",
                text=last,
                confidence=0.62,
                source="reference_task",
                machine_task=task,
                context={
                    "semantic_restore_candidate": True,
                    "trajectory_resume_candidate": True,
                },
            )

        return _evidence(
            mode="dialog",
            text=last,
            confidence=0.55,
            source="reference_dialog",
            context={"light_continuation": True},
        )

    # Explicit execution is a strong signal, but not final authority.
    if is_explicit(last):
        log_resolver_event("explicit_execution_evidence")
        return _evidence(
            mode="execute",
            text=last,
            confidence=0.90,
            source="explicit",
            machine_task=build_machine_task(last, mode="execution"),
            context={
                "execution_candidate": True,
                "current_request_authoritative": True,
            },
        )

    # Active flow is retained as evidence only. It cannot overwrite a new
    # full request merely because a previous flow existed.
    if active_flow:
        flow_type = active_flow.get("type")
        if flow_type:
            log_resolver_event("active_flow_evidence", {
                "flow_type": flow_type,
            })
            return _evidence(
                mode="dialog",
                text=last,
                confidence=0.68,
                source="trajectory_evidence",
                context={
                    "trajectory_active": True,
                    "trajectory_locked": False,
                    "flow_type": flow_type,
                    "new_request_must_be_fused": True,
                },
            )

    # Historical task is a weak evidence signal, never a replacement command.
    if task:
        log_resolver_event("memory_task_evidence")
        return _evidence(
            mode="dialog",
            text=last,
            confidence=0.58,
            source="memory_task_evidence",
            machine_task=task,
            context={
                "semantic_memory_available": True,
                "trajectory_soft_resume_candidate": True,
                "current_request_preserved": True,
            },
        )

    log_resolver_event("default_dialog")
    return _evidence(
        mode="dialog",
        text=last,
        confidence=0.50,
        source="default",
        context={"dialog_safe": True},
    )


def detect_focus_shift(text: str, state: Optional[dict] = None) -> bool:
    state = state if isinstance(state, dict) else {}
    focus = state.get("dynamic_focus") or {}
    primary = normalize(focus.get("primary_focus", ""))
    current = normalize(text)

    if not primary:
        return False

    meaningful = [word for word in primary.split() if len(word) >= 4]
    if not meaningful:
        return False

    overlap = sum(1 for word in meaningful if word in current)
    return overlap == 0


def build_focus_intent_state(text: str, state: Optional[dict] = None) -> Dict[str, Any]:
    shifted = detect_focus_shift(text, state)
    return {
        "focus_shift_detected": shifted,
        "focus_priority": not shifted,
        "requires_focus_refresh": shifted,
        "decision_owner": DECISION_OWNER,
        "machine_only": True,
    }
