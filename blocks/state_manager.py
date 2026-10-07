"""APRIL 12-hour dialogue state manager.

State manager owns only the live authenticated dialogue window and semantic
sequence. Database reads/writes are deliberately owned by the processor.
"""
from __future__ import annotations

from copy import deepcopy
import threading
import time
import uuid
from typing import Any

DIALOGUE_WINDOW_HOURS = 12
DIALOGUE_WINDOW_SECONDS = DIALOGUE_WINDOW_HOURS * 3600
_LOCK = threading.RLock()
_STATES: dict[str, dict[str, Any]] = {}


def _new_sequence() -> dict[str, Any]:
    return {
        "sequence_id": f"seq-{uuid.uuid4().hex[:20]}",
        "turn_index": 0,
        "topic": "",
        "task": {},
        "updated_at": time.time(),
    }


def _new_state(uid: str) -> dict[str, Any]:
    now = time.time()
    return {
        "user_id": uid,
        "dialogue_pairs": [],
        "active_sequence": _new_sequence(),
        "language": "en",
        "last_relation_state": {},
        "last_activity": now,
        "updated_at": now,
    }


def _uid(user_id: Any) -> str:
    value = str(user_id or "").strip()
    if not value:
        raise ValueError("USER_ID_REQUIRED")
    return value


def get_state(user_id: Any) -> dict[str, Any]:
    uid = _uid(user_id)
    with _LOCK:
        state = _STATES.get(uid)
        if state is None:
            state = _new_state(uid)
            _STATES[uid] = state
        return state


def hydrate(user_id: Any, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Replace the in-memory 12h window from processor-loaded DB rows."""
    state = get_state(user_id)
    now = time.time()
    clean: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        created = float(row.get("created_at") or now)
        if now - created <= DIALOGUE_WINDOW_SECONDS:
            clean.append(deepcopy(row))
    clean.sort(key=lambda x: (float(x.get("created_at") or 0), int(x.get("turn_index") or 0)))
    with _LOCK:
        state["dialogue_pairs"] = clean
        state["last_activity"] = now
        state["updated_at"] = now
        return state


def refresh_state(user_id: Any, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return hydrate(user_id, rows) if rows is not None else get_state(user_id)


def set_language(user_id: Any, language: str) -> None:
    state = get_state(user_id)
    state["language"] = str(language or "en").strip().lower() or "en"
    state["updated_at"] = time.time()


def get_language(user_id: Any) -> str:
    return str(get_state(user_id).get("language") or "en")


def get_dialogue_pairs(user_id: Any) -> list[dict[str, Any]]:
    return deepcopy(get_state(user_id).get("dialogue_pairs") or [])


def get_active_sequence(user_id: Any) -> dict[str, Any]:
    return deepcopy(get_state(user_id).get("active_sequence") or _new_sequence())


def begin_new_topic(user_id: Any, topic: str = "", task: dict[str, Any] | None = None) -> dict[str, Any]:
    state = get_state(user_id)
    sequence = _new_sequence()
    sequence["topic"] = str(topic or "").strip()
    sequence["task"] = deepcopy(task or {})
    state["active_sequence"] = sequence
    state["updated_at"] = time.time()
    return deepcopy(sequence)


def continue_topic(user_id: Any, topic: str = "", task: dict[str, Any] | None = None) -> dict[str, Any]:
    state = get_state(user_id)
    sequence = state.get("active_sequence") or _new_sequence()
    sequence["turn_index"] = int(sequence.get("turn_index") or 0) + 1
    if topic:
        sequence["topic"] = str(topic).strip()
    if task:
        sequence["task"] = deepcopy(task)
    sequence["updated_at"] = time.time()
    state["active_sequence"] = sequence
    state["updated_at"] = time.time()
    return deepcopy(sequence)


def append_pair(user_id: Any, row: dict[str, Any]) -> dict[str, Any]:
    """Append one already-persisted pair and enforce the rolling 12h window."""
    state = get_state(user_id)
    item = deepcopy(row or {})
    item.setdefault("created_at", time.time())
    with _LOCK:
        pairs = [x for x in state.get("dialogue_pairs", []) if isinstance(x, dict)]
        pairs.append(item)
        cutoff = time.time() - DIALOGUE_WINDOW_SECONDS
        pairs = [x for x in pairs if float(x.get("created_at") or 0) >= cutoff]
        pairs.sort(key=lambda x: (float(x.get("created_at") or 0), int(x.get("turn_index") or 0)))
        state["dialogue_pairs"] = pairs
        state["last_activity"] = time.time()
        state["updated_at"] = time.time()
        return deepcopy(state)


def set_relation(user_id: Any, relation: str, **metadata: Any) -> None:
    state = get_state(user_id)
    state["last_relation_state"] = {"relation": str(relation or "NEW").upper(), **metadata}
    state["updated_at"] = time.time()


def initialize() -> None:
    """Compatibility hook. DB initialization belongs to the processor."""
    return None


__all__ = [
    "DIALOGUE_WINDOW_HOURS", "DIALOGUE_WINDOW_SECONDS", "get_state", "hydrate",
    "refresh_state", "set_language", "get_language", "get_dialogue_pairs",
    "get_active_sequence", "begin_new_topic", "continue_topic", "append_pair",
    "set_relation", "initialize",
]
