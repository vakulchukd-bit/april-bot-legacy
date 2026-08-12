"""
APRIL — EXPERIENCE EVIDENCE CORE / QUANTUM V1

Role:
    Short-lived experience signal extraction.

Not:
    - long-term memory authority
    - router
    - executor
    - provider
    - renderer

The canonical owner of final interpretation remains QUANTUM_PROCESSOR.
This module only extracts compact, JSON-safe experience evidence.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable


APRIL_FILE_ID = "APRIL_EXPERIENCE_EVIDENCE_QUANTUM_V1"
DECISION_OWNER = "QUANTUM_PROCESSOR"

EXPERIENCE_INPUT_CHANNEL = {
    "channel": "experience_evidence_input",
    "isolated": True,
}
EXPERIENCE_OUTPUT_CHANNEL = {
    "channel": "experience_evidence_output",
    "isolated": True,
}

ACTION_WORDS = (
    "сделай", "создай", "исправь", "покажи", "нарисуй",
    "построй", "реши", "вычисли", "добавь", "убери",
)
REFERENCE_WORDS = (
    "это", "этот", "эта", "тот", "там", "здесь", "выше",
    "ниже", "раньше", "предыдущ", "продолжи", "дальше",
)
CONFUSION_WORDS = (
    "не понимаю", "не получается", "ошибка", "не работает",
    "запутался", "не уверен",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _low(value: Any) -> str:
    return _text(value).lower()


def _contains(text: Any, values: Iterable[str]) -> bool:
    value = _low(text)
    return any(item in value for item in values)


def _clamp(value: Any, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        number = float(value)
    except Exception:
        number = lo
    return max(lo, min(hi, number))



def build_experience_evidence(
    text: str,
    state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    state = state if isinstance(state, dict) else {}
    dialog = state.get("dialog") if isinstance(state.get("dialog"), list) else []
    active_flow = state.get("active_flow") if isinstance(state.get("active_flow"), dict) else {}

    normalized = _low(text)
    recent = dialog[-6:]
    previous_user = ""
    for item in reversed(recent):
        if not isinstance(item, dict):
            continue
        if _low(item.get("role")) in {"user", "human"}:
            candidate = _text(item.get("content"))
            if candidate and candidate != text:
                previous_user = candidate
                break

    current_words = set(re.findall(r"\w+", normalized, flags=re.UNICODE))
    previous_words = set(re.findall(r"\w+", _low(previous_user), flags=re.UNICODE))
    overlap = len(current_words & previous_words) / max(1, len(current_words | previous_words))

    recent_user_turns = [
        _text(x.get("content"))
        for x in recent
        if isinstance(x, dict) and _low(x.get("role")) in {"user", "human"}
    ][-4:]

    return {
        "version": "quantum_experience_v2",
        "current_request": _text(text),
        "active_flow": active_flow,
        "signals": {
            "action_pressure": 1.0 if _contains(text, ACTION_WORDS) else 0.0,
            "reference_pressure": 1.0 if _contains(text, REFERENCE_WORDS) else 0.0,
            "confusion_pressure": 1.0 if _contains(text, CONFUSION_WORDS) else 0.0,
            "history_available": bool(dialog),
            "history_overlap": _clamp(overlap),
            "active_flow": bool(active_flow),
            "flow_type": active_flow.get("type"),
            "short_turn": bool(normalized and len(normalized.split()) <= 8),
        },
        "recent_user_turns": recent_user_turns,
        "temporary_only": True,
        "machine_only": True,
        "decision_owner": DECISION_OWNER,
        "provider_calls": 0,
        "route_selection": "delegated",
        "renderer_selection": "delegated",
        "execution_selection": "delegated",
    }


def get_experience_signal(
    text: str,
    state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Compatibility entrypoint used by the executor."""
    return build_experience_evidence(text, state)


def build_experience_snapshot(
    user_id: Any,
    state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """JSON-safe per-user snapshot; never stores runtime objects."""
    state = state if isinstance(state, dict) else {}
    return {
        "user_id": str(user_id),
        "active_flow_type": (
            state.get("active_flow", {}).get("type")
            if isinstance(state.get("active_flow"), dict)
            else None
        ),
        "dialog_length": len(state.get("dialog", [])) if isinstance(state.get("dialog"), list) else 0,
        "temporary_only": True,
        "machine_only": True,
        "decision_owner": DECISION_OWNER,
    }
