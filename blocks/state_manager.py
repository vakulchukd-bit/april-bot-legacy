"""APRIL state manager — DB-backed dialogue search and live route state.

Persistent dialogue data belongs to storage.py.  This module is the processor-side
memory/search engine: it hydrates the live 12h window from PostgreSQL, ranks the
best USER↔APRIL pairs, decides CONTINUE/NEW candidates, and exposes the result to
the Interpretation Identity layer.  It never owns a second database.
"""
from __future__ import annotations

from copy import deepcopy
import re
import threading
import time
import uuid
from typing import Any

from rapidfuzz import fuzz

DIALOGUE_WINDOW_HOURS = 12
DIALOGUE_WINDOW_SECONDS = DIALOGUE_WINDOW_HOURS * 3600

_LOCK = threading.RLock()
_STATES: dict[str, dict[str, Any]] = {}


_CONTINUATION_MARKERS = {
    "this", "that", "it", "these", "those", "continue", "more",
    "again", "also", "and how", "what about", "потом", "дальше",
    "это", "тот", "так", "ещё", "еще", "продолжи", "а дальше",
}


def _new_sequence() -> dict[str, Any]:
    return {
        "sequence_id": f"seq-{uuid.uuid4().hex[:20]}",
        "turn_index": 0,
        "topic": "",
        "task": {},
        "updated_at": time.time(),
    }


def _new_state(uid: str) -> dict[str, Any]:
    stamp = time.time()
    return {
        "user_id": uid,
        "dialogue_pairs": [],
        "active_sequence": _new_sequence(),
        "language": "en",
        "last_relation_state": {},
        "last_memory_search": {},
        "last_activity": stamp,
        "updated_at": stamp,
    }


def _uid(user_id: Any) -> str:
    value = str(user_id or "").strip()
    if not value:
        raise ValueError("USER_ID_REQUIRED")
    return value


def _prune(state: dict[str, Any], now_value: float | None = None) -> None:
    stamp = float(now_value if now_value is not None else time.time())
    cutoff = stamp - DIALOGUE_WINDOW_SECONDS
    pairs = [
        deepcopy(row)
        for row in (state.get("dialogue_pairs") or [])
        if isinstance(row, dict)
        and float(row.get("created_at") or 0) >= cutoff
    ]
    pairs.sort(
        key=lambda x: (
            float(x.get("created_at") or 0),
            int(x.get("turn_index") or 0),
        )
    )
    state["dialogue_pairs"] = pairs


def get_state(user_id: Any) -> dict[str, Any]:
    uid = _uid(user_id)
    with _LOCK:
        state = _STATES.get(uid)
        if state is None:
            state = _new_state(uid)
            _STATES[uid] = state
        _prune(state)
        state["updated_at"] = time.time()
        return state


def hydrate(
    user_id: Any,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Refresh in-memory state from the canonical PostgreSQL dialogue store."""
    uid = _uid(user_id)
    if rows is None:
        from storage import load_dialogue_pairs
        rows = load_dialogue_pairs(uid, limit=0)

    state = get_state(uid)
    with _LOCK:
        state["dialogue_pairs"] = [
            deepcopy(row) for row in (rows or []) if isinstance(row, dict)
        ]
        _prune(state)
        state["last_activity"] = time.time()
        state["updated_at"] = state["last_activity"]
        return state


def refresh_state(
    user_id: Any,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return hydrate(user_id, rows)


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


def begin_new_topic(
    user_id: Any,
    topic: str = "",
    task: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = get_state(user_id)
    sequence = _new_sequence()
    sequence["topic"] = str(topic or "").strip()
    sequence["task"] = deepcopy(task or {})
    state["active_sequence"] = sequence
    state["updated_at"] = time.time()
    return deepcopy(sequence)


def continue_topic(
    user_id: Any,
    topic: str = "",
    task: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
        pairs = [
            x for x in state.get("dialogue_pairs", [])
            if isinstance(x, dict)
        ]
        pairs.append(item)
        _prune(
            {"dialogue_pairs": pairs},
            time.time(),
        )
        state["dialogue_pairs"] = sorted(
            [deepcopy(x) for x in _prune_copy(pairs)],
            key=lambda x: (
                float(x.get("created_at") or 0),
                int(x.get("turn_index") or 0),
            ),
        )
        state["last_activity"] = time.time()
        state["updated_at"] = time.time()
        return deepcopy(state)


def _prune_copy(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cutoff = time.time() - DIALOGUE_WINDOW_SECONDS
    return [
        deepcopy(row)
        for row in pairs
        if isinstance(row, dict)
        and float(row.get("created_at") or 0) >= cutoff
    ]


def set_relation(user_id: Any, relation: str, **metadata: Any) -> None:
    state = get_state(user_id)
    state["last_relation_state"] = {
        "relation": str(relation or "NEW").upper(),
        **metadata,
    }
    state["updated_at"] = time.time()


def _tokens(value: Any) -> set[str]:
    return {
        token
        for token in re.findall(
            r"[\w\u0080-\uffff]+",
            str(value or "").lower(),
        )
        if len(token) > 1
    }


def _continuation_marker(query: str) -> bool:
    low = str(query or "").strip().lower()
    if not low:
        return False
    return any(
        low == marker or low.startswith(marker + " ")
        for marker in _CONTINUATION_MARKERS
    )


def _domain_terms(text: str) -> set[str]:
    low = str(text or "").lower()
    groups = {
        "code": {"code", "python", "javascript", "bug", "api", "railway", "github", "код", "ошибка"},
        "image": {"image", "picture", "photo", "screenshot", "рисунок", "картинка", "скриншот"},
        "math": {"math", "formula", "equation", "graph", "таблица", "формула", "график", "математика"},
        "web": {"web", "link", "url", "site", "сайт", "ссылка"},
        "file": {"file", "document", "pdf", "файл", "документ"},
        "voice": {"voice", "audio", "голос", "аудио"},
    }
    result: set[str] = set()
    for domain, terms in groups.items():
        if low and any(term in low for term in terms):
            result.add(domain)
    return result


def _candidate_score(
    query: str,
    row: dict[str, Any],
    *,
    dialog_id: str = "",
    now_ts: float | None = None,
) -> dict[str, Any]:
    q = str(query or "").strip().lower()
    user = str(row.get("user_text") or "")
    april = str(row.get("april_text") or "")
    user_en = str(row.get("user_text_en") or "")
    april_en = str(row.get("april_text_en") or "")

    query_tokens = _tokens(q)
    semantic_text = " ".join(x for x in (user, user_en, april, april_en) if x).lower()
    candidate_tokens = _tokens(semantic_text)

    lexical = fuzz.token_set_ratio(q, semantic_text) / 100.0 if q else 0.0
    partial = fuzz.partial_ratio(q, semantic_text) / 100.0 if q else 0.0
    overlap = (
        len(query_tokens & candidate_tokens) / max(1, len(query_tokens))
        if query_tokens else 0.0
    )

    q_domains = _domain_terms(q)
    c_domains = _domain_terms(semantic_text)
    direction = (
        len(q_domains & c_domains) / max(1, len(q_domains))
        if q_domains else 0.0
    )

    stamp = now_ts if now_ts is not None else time.time()
    created = float(row.get("created_at") or 0.0)
    age = max(0.0, stamp - created)
    recency = max(0.0, 1.0 - age / DIALOGUE_WINDOW_SECONDS)

    exact_dialog = bool(
        dialog_id
        and str(row.get("dialog_id") or "").strip()
        and str(row.get("dialog_id") or "").strip() == dialog_id
    )

    score = (
        lexical * 0.34
        + partial * 0.18
        + overlap * 0.26
        + direction * 0.12
        + recency * 0.05
        + (0.05 if exact_dialog else 0.0)
    )

    return {
        "score": round(min(1.0, float(score)), 6),
        "semantic": round(lexical, 6),
        "context": round(overlap, 6),
        "direction": round(direction, 6),
        "recency": round(recency, 6),
        "same_dialog": exact_dialog,
        "turn_index": int(row.get("turn_index") or 0),
        "created_at": created,
        "user": user,
        "user_en": user_en,
        "april": april,
        "april_en": april_en,
        "message_id": str(row.get("message_id") or ""),
        "dialog_id": str(row.get("dialog_id") or ""),
        "conversation_id": str(row.get("conversation_id") or ""),
        "interpretation_id": str(row.get("interpretation_id") or ""),
    }


def search_dialogue_context(
    user_id: Any,
    query: str,
    *,
    dialog_id: str = "",
    conversation_id: str = "",
    limit: int = 8,
) -> dict[str, Any]:
    """Search PostgreSQL dialogue pairs and return ranked context for interpretation.

    PostgreSQL remains storage only.  Ranking and compatibility are performed here
    so Interpretation Identity receives already-structured candidates.
    """
    uid = _uid(user_id)
    state = hydrate(uid)
    rows = list(state.get("dialogue_pairs") or [])
    matches = [
        _candidate_score(
            query,
            row,
            dialog_id=str(dialog_id or ""),
        )
        for row in rows
    ]
    matches.sort(
        key=lambda item: (
            float(item["score"]),
            float(item["recency"]),
            int(item["turn_index"]),
        ),
        reverse=True,
    )
    selected = matches[: max(1, int(limit or 8))] if matches else []

    best = selected[0] if selected else None
    marker = _continuation_marker(query)
    continuation = bool(
        best
        and (
            float(best["score"]) >= 0.52
            or (
                marker
                and float(best["score"]) >= 0.22
            )
            or (
                bool(best.get("same_dialog"))
                and float(best["score"]) >= 0.35
            )
        )
    )
    relation = "CONTINUE" if continuation else "NEW"

    if relation == "CONTINUE" and selected:
        selected_for_context = selected[:4]
        reason = "memory_match"
        active_topic = (
            selected_for_context[0].get("user_en")
            or selected_for_context[0].get("user")
            or ""
        )[:180]
    else:
        selected_for_context = []
        reason = "new_request"
        active_topic = str(query or "").strip()[:180]

    result = {
        "engine": "state_manager_dialogue_search_v2",
        "authenticated": True,
        "window_hours": DIALOGUE_WINDOW_HOURS,
        "dialog_id": str(dialog_id or ""),
        "conversation_id": str(conversation_id or ""),
        "query": str(query or ""),
        "total_pairs": len(rows),
        "candidate_count": len(matches),
        "relation": relation,
        "reason": reason,
        "relation_confidence": round(
            float(best["score"]) if best else 0.0,
            6,
        ),
        "continuation_marker": marker,
        "active_topic": active_topic,
        "matches": selected,
        "selected": selected_for_context,
    }

    with _LOCK:
        state["last_memory_search"] = deepcopy(result)
        state["last_relation_state"] = {
            "relation": relation,
            "reason": reason,
            "confidence": result["relation_confidence"],
            "active_topic": active_topic,
        }
        state["updated_at"] = time.time()

    return result


def prepare_dialogue_context(
    user_id: Any,
    query: str,
    *,
    dialog_id: str = "",
    conversation_id: str = "",
    limit: int = 8,
) -> dict[str, Any]:
    """One processor-facing call: hydrate + search + continuation decision."""
    context = search_dialogue_context(
        user_id,
        query,
        dialog_id=dialog_id,
        conversation_id=conversation_id,
        limit=limit,
    )
    return {
        "window_hours": DIALOGUE_WINDOW_HOURS,
        "relation": context["relation"],
        "relation_confidence": context["relation_confidence"],
        "reason": context["reason"],
        "active_topic": context["active_topic"],
        "selected_pairs": deepcopy(context["selected"]),
        "candidates": deepcopy(context["matches"]),
        "search": deepcopy(context),
    }


def initialize() -> None:
    """Compatibility hook. PostgreSQL initialization belongs to the processor."""
    return None


__all__ = [
    "DIALOGUE_WINDOW_HOURS",
    "DIALOGUE_WINDOW_SECONDS",
    "get_state",
    "hydrate",
    "refresh_state",
    "set_language",
    "get_language",
    "get_dialogue_pairs",
    "get_active_sequence",
    "begin_new_topic",
    "continue_topic",
    "append_pair",
    "set_relation",
    "search_dialogue_context",
    "prepare_dialogue_context",
    "initialize",
]
