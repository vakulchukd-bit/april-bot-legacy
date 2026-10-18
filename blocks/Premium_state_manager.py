"""April Premium Stat Manager: canonical Premium access, PostgreSQL adapter, and 24-hour dialogue understanding.

This is the single Premium manager module. It uses the existing users and dialogue_memory
tables, validates the active Premium subscription, loads/saves the canonical dialogue
pairs, and provides the Premium state/search/continuation engine. Free storage and route
implementations are not copied or modified here.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Any

import psycopg2
from rapidfuzz import fuzz
from storage import get_conn, is_authenticated_user as _is_authenticated_user, now, cleanup_dialogue_memory_utc as _cleanup_dialogue_memory_utc
from blocks.Premium_interpretation_identity import extract_temporal_window, extract_topic_count_bounds, intersect_retention_window





PREMIUM_MEMORY_WINDOW_HOURS = 24
PREMIUM_MEMORY_WINDOW_SECONDS = PREMIUM_MEMORY_WINDOW_HOURS * 3600


def init_db() -> None:
    """Validate the canonical schema without starting/changing Free cleanup.

    bot.py remains responsible for calling storage.init_db() during service startup.
    """
    conn = get_conn()
    if not conn:
        raise RuntimeError("DATABASE_URL_NOT_CONFIGURED")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM users LIMIT 0")
            cur.execute("SELECT 1 FROM dialogue_memory LIMIT 0")
    except Exception as exc:
        raise RuntimeError("CANONICAL_STORAGE_NOT_INITIALIZED") from exc
    finally:
        conn.close()


def is_authenticated_user(user_id: Any) -> bool:
    return _is_authenticated_user(user_id)


def _active_premium_cursor(cur, uid: str, at: datetime) -> bool:
    cur.execute(
        "SELECT user_id, email, provider, plan, subscription_until FROM users WHERE user_id = %s",
        (uid,),
    )
    row = cur.fetchone()
    if not isinstance(row, dict):
        return False
    return bool(
        str(row.get("user_id") or "").strip()
        and str(row.get("email") or "").strip()
        and str(row.get("provider") or "").strip()
        and str(row.get("plan") or "free").strip().lower() == "premium"
        and float(row.get("subscription_until") or 0) > at.timestamp()
    )


def _as_utc(value: float | int | datetime | None) -> datetime:
    if value is None:
        return now()
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromtimestamp(float(value), tz=timezone.utc)


def load_dialogue_pairs(
    user_id: Any,
    *,
    limit: int = 0,
    timestamp: float | int | datetime | None = None,
) -> list[dict[str, Any]]:
    """Load only this active Premium user's USER↔APRIL pairs from the last 24 hours."""
    uid = str(user_id or "").strip()
    if not uid or not is_authenticated_user(uid):
        return []
    current = _as_utc(timestamp)
    conn = get_conn()
    if not conn:
        return []
    try:
        with conn.cursor() as cur:
            if not _active_premium_cursor(cur, uid, current):
                return []
            cur.execute(
                """
                SELECT id, user_id, created_at, retention_hours, turn_index, user_text, april_text,
                       user_text_en, april_text_en, language, relation, dialog_id,
                       conversation_id, message_id, interpretation_id,
                       structured_request, structured_response
                FROM dialogue_memory
                WHERE user_id = %s
                  AND created_at <= %s
                  AND created_at + (GREATEST(12, LEAST(24, COALESCE(retention_hours, 12))) * INTERVAL '1 hour') > %s
                ORDER BY created_at ASC, turn_index ASC, id ASC
                """,
                (uid, current, current),
            )
            rows = [dict(row) for row in cur.fetchall()]
            for row in rows:
                created = row.get("created_at")
                if isinstance(created, datetime):
                    row["created_at"] = created.astimezone(timezone.utc).timestamp()
            if limit and len(rows) > int(limit):
                rows = rows[-int(limit):]
            return rows
    except psycopg2.errors.UndefinedTable:
        return []
    finally:
        conn.close()


def save_dialogue_pair(
    user_id: Any,
    user_text: str,
    april_text: str,
    *,
    created_at: float | int | datetime | None = None,
    turn_index: int = 0,
    user_en: str = "",
    april_en: str = "",
    language: str = "en",
    relation: str = "NEW",
    dialog_id: str = "",
    conversation_id: str = "",
    message_id: str = "",
    interpretation_id: str = "",
    structured_request: dict[str, Any] | None = None,
    structured_response: dict[str, Any] | None = None,
) -> bool:
    """Persist one pair only for the authenticated user with active Premium."""
    uid = str(user_id or "").strip()
    user_value = str(user_text or "").strip()
    april_value = str(april_text or "").strip()
    if not uid or not user_value or not april_value:
        return False
    dt = _as_utc(created_at)
    # Run the canonical expiry path first so any file sidecars are removed together
    # with their expired dialogue rows. The asset store is Premium-only and is not
    # a second memory database.
    try:
        _cleanup_dialogue_memory_utc(user_id=uid)
    except Exception:
        pass
    conn = get_conn()
    if not conn:
        return False
    try:
        with conn:
            with conn.cursor() as cur:
                # Entitlement is checked against server time, never the client-supplied
                # message timestamp. The latter is only the record's display/retention origin.
                save_now = now()
                if not _active_premium_cursor(cur, uid, save_now):
                    return False
                # Expired rows were removed by the canonical cleanup path above;
                # do not bypass its file-sidecar cleanup with a direct DELETE here.
                pair_hash = hashlib.sha256(
                    f"{uid}|{int(dt.timestamp() * 1000)}|{int(turn_index)}|{user_value}|{april_value}".encode("utf-8")
                ).hexdigest()
                cur.execute(
                    """
                    INSERT INTO dialogue_memory
                      (user_id, created_at, retention_hours, turn_index, user_text, april_text,
                       user_text_en, april_text_en, language, relation, pair_hash,
                       dialog_id, conversation_id, message_id, interpretation_id,
                       structured_request, structured_response)
                    VALUES (%s, %s, 24, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
                    ON CONFLICT (pair_hash) DO UPDATE SET
                      user_text_en = EXCLUDED.user_text_en,
                      april_text_en = EXCLUDED.april_text_en,
                      structured_request = EXCLUDED.structured_request,
                      structured_response = EXCLUDED.structured_response,
                      interpretation_id = EXCLUDED.interpretation_id
                    """,
                    (
                        uid, dt, int(turn_index or 0), user_value, april_value,
                        str(user_en or user_value), str(april_en or april_value),
                        str(language or "en"), str(relation or "NEW"), pair_hash,
                        str(dialog_id or ""), str(conversation_id or ""),
                        str(message_id or ""), str(interpretation_id or ""),
                        json.dumps(structured_request or {}, ensure_ascii=False, default=str),
                        json.dumps(structured_response or {}, ensure_ascii=False, default=str),
                    ),
                )
                # A write invalidates the process-local hydration snapshot. The next
                # turn must see this canonical row, while multi-part searches inside
                # the current request can still reuse the unchanged snapshot.
                with _LOCK:
                    _HYDRATED_AT.pop(uid, None)
                return True
    except psycopg2.errors.UndefinedTable:
        return False
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Premium dialogue state/search engine (merged from the former state manager)
# ---------------------------------------------------------------------------
DIALOGUE_WINDOW_HOURS = PREMIUM_MEMORY_WINDOW_HOURS
DIALOGUE_WINDOW_SECONDS = PREMIUM_MEMORY_WINDOW_SECONDS

_LOCK = threading.RLock()
_STATES: dict[str, dict[str, Any]] = {}
# A short process-local snapshot avoids re-reading and re-hydrating the same full
# 24-hour history for every clause in one compound request. It is not a second
# persistence layer: PostgreSQL dialogue_memory remains canonical, and writes
# invalidate this snapshot immediately.
_HYDRATE_CACHE_SECONDS = 30.0
_HYDRATED_AT: dict[str, float] = {}


def _apr_timing_log(stage: str, started: float | None = None, **fields: Any) -> None:
    """Low-overhead diagnostic timing; logging must never affect the request path."""
    try:
        payload = {"component": "premium_state_manager", "stage": stage}
        if started is not None:
            payload["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
        payload.update(fields)
        print("[APRIL_TIMING] " + json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str), flush=True)
    except Exception:
        pass

def _apr_diag_ref(value: Any) -> str:
    """One-way short reference for joining logs without exposing raw user IDs."""
    try:
        raw = str(value or "").strip()
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10] if raw else ""
    except Exception:
        return ""


_CONTINUATION_MARKERS = {
    "this", "that", "it", "these", "those", "continue", "more",
    "again", "also", "and how", "what about", "потом", "дальше",
    "это", "тот", "так", "ещё", "еще", "продолжи", "а дальше",
    "про него", "про неё", "про нее", "про них", "про него еще",
    "про неё еще", "про нее еще", "что еще", "что ещё",
}

_HISTORY_MARKERS = (
    "о чем мы говорили",
    "о чём мы говорили",
    "о чем говорили",
    "о чём говорили",
    "что мы обсуждали",
    "что обсуждали",
    "какие темы мы обсуждали",
    "какие темы обсуждали",
    "напомни темы",
    "напомни о чем",
    "напомни, о чем",
    "напомни о чём",
    "напомни, о чём",
    "история диалога",
    "история разговора",
    "наши темы",
    "что было в диалоге",
    "о чем шла речь",
    "о чём шла речь",
)

_NEW_TOPIC_MARKERS = (
    "новая тема",
    "другая тема",
    "другой вопрос",
    "теперь о",
    "теперь про",
    "перейдем к",
    "перейдём к",
    "забудь это",
    "не про это",
)


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


def _text(value: Any) -> str:
    return str(value or "").strip()


def _uid(user_id: Any) -> str:
    value = str(user_id or "").strip()
    if not value:
        raise ValueError("USER_ID_REQUIRED")
    return value


def _prune(state: dict[str, Any], now_value: float | None = None) -> None:
    stamp = float(now_value if now_value is not None else time.time())
    pairs = [
        deepcopy(row)
        for row in (state.get("dialogue_pairs") or [])
        if isinstance(row, dict)
            and _row_is_live(row, stamp, DIALOGUE_WINDOW_HOURS)
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



def purge_user_state(user_ids: Any) -> int:
    """Remove process-local Premium dialogue snapshots for the supplied identities."""
    if isinstance(user_ids, (str, bytes)):
        values = [str(user_ids).strip()]
    else:
        try:
            values = [str(value or "").strip() for value in user_ids]
        except TypeError:
            values = [str(user_ids or "").strip()]
    removed = 0
    with _LOCK:
        for uid in set(value for value in values if value):
            if _STATES.pop(uid, None) is not None:
                removed += 1
            if _HYDRATED_AT.pop(uid, None) is not None:
                removed += 1
    return removed


def hydrate(
    user_id: Any,
    rows: list[dict[str, Any]] | None = None,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Refresh in-memory state from the canonical PostgreSQL dialogue store."""
    hydrate_started = time.perf_counter()
    uid = _uid(user_id)
    cache_now = time.time()
    if rows is None and not force:
        with _LOCK:
            cached_state = _STATES.get(uid)
            cached_at = float(_HYDRATED_AT.get(uid) or 0.0)
            if cached_state is not None and cached_at and cache_now - cached_at <= _HYDRATE_CACHE_SECONDS:
                # Filter expired rows cheaply without cloning the potentially large
                # structured_response payloads. Nothing in the current search mutates
                # the payload contents except derived topic annotations.
                cached_state["dialogue_pairs"] = [
                    row for row in (cached_state.get("dialogue_pairs") or [])
                    if isinstance(row, dict) and _row_is_live(row, cache_now, DIALOGUE_WINDOW_HOURS)
                ]
                _apr_timing_log(
                    "hydrate_cache_hit", hydrate_started,
                    user_key=_apr_diag_ref(uid), retained_pairs=len(cached_state["dialogue_pairs"]),
                    cache_age_ms=round((cache_now - cached_at) * 1000, 2),
                )
                return cached_state
    load_started = time.perf_counter()
    load_source = "provided_rows" if rows is not None else "postgres_load_dialogue_pairs"
    if rows is None:
        rows = load_dialogue_pairs(uid, limit=0)
    _apr_timing_log("history_rows_loaded", load_started, user_key=_apr_diag_ref(uid),
        source=load_source, rows_loaded=len(rows or []))

    # Avoid get_state() here: it prunes/deep-copies the previous payload before
    # hydrate immediately overwrites it, then a second prune deep-copies the large
    # structured responses again. Premium history can contain image/table payloads;
    # copy each newly-loaded row once and prune without another full payload clone.
    stamp = time.time()
    live_rows = [
        deepcopy(row) for row in (rows or [])
        if isinstance(row, dict) and _row_is_live(row, stamp, DIALOGUE_WINDOW_HOURS)
    ]
    live_rows.sort(key=lambda x: (float(x.get("created_at") or 0), int(x.get("turn_index") or 0)))
    with _LOCK:
        state = _STATES.get(uid)
        if state is None:
            state = _new_state(uid)
            _STATES[uid] = state
        state["dialogue_pairs"] = live_rows
        state["last_activity"] = stamp
        state["updated_at"] = stamp
        _HYDRATED_AT[uid] = stamp
        _apr_timing_log("hydrate_complete", hydrate_started, user_key=_apr_diag_ref(uid),
            retained_pairs=len(live_rows))
        return state


def refresh_state(
    user_id: Any,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return hydrate(user_id, rows, force=True)


def set_language(user_id: Any, language: str) -> None:
    state = get_state(user_id)
    state["language"] = str(language or "en").strip().lower() or "en"
    state["updated_at"] = time.time()


def get_language(user_id: Any) -> str:
    return str(get_state(user_id).get("language") or "en")


def get_dialogue_pairs(
    user_id: Any,
    *,
    refresh: bool = False,
    limit: int = 0,
) -> list[dict[str, Any]]:
    """Return dialogue pairs through State Manager, optionally refreshing canonical DB state.

    The storage adapter is called only by ``hydrate``; persistent history reads
    therefore use the single ``dialogue_memory`` source and share this layer's
    authenticated-user and UTC-window policy. ``limit`` returns the most recent
    pairs while preserving chronological order.
    """
    state = hydrate(user_id, force=True) if refresh else get_state(user_id)
    pairs = deepcopy(state.get("dialogue_pairs") or [])
    if limit and len(pairs) > int(limit):
        pairs = pairs[-int(limit):]
    return pairs


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
    """Append one already-persisted pair and enforce the rolling 24h window."""
    state = get_state(user_id)
    item = deepcopy(row or {})
    item.setdefault("created_at", time.time())
    item.setdefault("retention_hours", 24)
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
        _HYDRATED_AT.pop(_uid(user_id), None)
        return deepcopy(state)


def _prune_copy(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stamp = time.time()
    return [
        deepcopy(row)
        for row in pairs
        if isinstance(row, dict)
        and _row_is_live(row, stamp, DIALOGUE_WINDOW_HOURS)
    ]


def _row_is_live(row: dict[str, Any], stamp: float, fallback_hours: int) -> bool:
    """Honor the lifetime saved for this pair; legacy rows default to 12h."""
    try:
        created = float(row.get("created_at") or 0)
        raw_hours = row.get("retention_hours")
        hours = int(raw_hours) if raw_hours is not None else 12
        hours = 24 if hours >= 24 else 12
        return bool(created > 0 and created <= stamp and stamp < created + hours * 3600)
    except (TypeError, ValueError, OverflowError):
        return False


def set_relation(user_id: Any, relation: str, **metadata: Any) -> None:
    state = get_state(user_id)
    state["last_relation_state"] = {
        "relation": str(relation or "NEW").upper(),
        **metadata,
    }
    state["updated_at"] = time.time()



_SEMANTIC_ALIASES = {
    # Russian inflections and common near-synonyms that matter in visual follow-ups.
    "кошка": "кот", "кошки": "кот", "кошку": "кот", "кошкой": "кот",
    "кошечка": "кот", "кошечки": "кот", "кошечку": "кот", "кошечкой": "кот",
    "котик": "кот", "котика": "кот", "котиком": "кот", "котики": "кот",
    "котенок": "кот", "котенка": "кот", "котенку": "кот", "котенком": "кот",
    "цвета": "цвет", "цветом": "цвет", "цвете": "цвет", "цвету": "цвет",
    "окрас": "цвет", "окраса": "цвет", "окрасом": "цвет",
    "породы": "порода", "породой": "порода", "породе": "порода",
    "фотографии": "фото", "фотографию": "фото", "фотографией": "фото",
    # Participant-name wording is a semantic alias, so "Как меня зовут?" can
    # match persisted summaries phrased as "Имя пользователя: …".
    "зовут": "имя", "имени": "имя", "именем": "имя", "имена": "имя", "именах": "имя",
    "называюсь": "имя", "называешься": "имя", "называют": "имя",
    # Keep common literary-topic variants on one retrieval concept.
    "стихи": "стих", "стиха": "стих", "стиху": "стих", "стихом": "стих", "стихе": "стих",
    "стихотворение": "стих", "стихотворения": "стих", "стихотворению": "стих",
    "стихотворением": "стих", "стихотворении": "стих", "стихотворений": "стих",
    "поэма": "поэм", "поэмы": "поэм", "поэме": "поэм", "поэмой": "поэм",
}

_STOP_WORDS = {
    "и", "а", "но", "или", "ли", "же", "да", "нет", "ну", "вот", "как",
    "в", "во", "на", "по", "к", "ко", "с", "со", "у", "из", "от", "до",
    "за", "для", "о", "об", "про", "при", "без", "не", "ни", "что",
    "это", "этот", "эта", "эти", "тот", "та", "те", "так", "там", "тут",
    "я", "ты", "мы", "вы", "он", "она", "они", "его", "ее", "её", "их",
    "мне", "тебе", "ему", "ей", "им", "ним", "ней", "него", "нее", "неё",
    "них", "меня", "тебя", "вас", "нас", "уже", "еще", "ещё", "тоже",
    "был", "была", "были", "было", "быть", "есть", "можно", "можешь",
    "скажи", "расскажи", "напомни", "покажи", "дай", "сделай", "сделать",
}

_HISTORY_COUNT_WORDS = {
    "один": 1, "одну": 1,
    "два": 2, "две": 2,
    "три": 3, "четыре": 4,
    "пять": 5, "шесть": 6, "семь": 7,
    "восемь": 8, "девять": 9, "десять": 10,
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _tokens(value: Any) -> set[str]:
    return {
        token
        for token in re.findall(r"[\w\u0080-\uffff]+", str(value or "").lower().replace("ё", "е"))
        if len(token) > 1
    }


def _semantic_tokens(value: Any) -> set[str]:
    normalized = set()
    for token in _tokens(value):
        token = _SEMANTIC_ALIASES.get(token, token)
        if token not in _STOP_WORDS and len(token) > 2:
            normalized.add(token)
    return normalized


# These are task vocabulary rather than subject identity. Removing them from the
# subject signature prevents different datasets (oil, bananas, cabbage, etc.) from
# being merged just because they all discuss prices, tables or graphs.
_CONTEXT_GENERIC_TERMS = {
    # Dialog participant references, self-corrections and memory operations are
    # conversational relations, not topical entities. Their words remain available
    # to retrieval; only the subject-conflict calculation ignores them.
    "я", "меня", "мне", "мной", "мой", "моя", "мое", "моё", "мои", "моих", "моему",
    "ты", "тебя", "тебе", "тобой", "твой", "твоя", "твое", "твоё", "твои", "твоих",
    "мы", "нас", "нам", "нами", "наш", "наша", "наше", "наши", "вы", "вас", "вам",
    "i", "me", "my", "mine", "myself", "you", "your", "yours", "yourself", "we", "us", "our", "ours",
    "имя", "имени", "именем", "зовут", "называют", "называюсь", "называешься",
    "помнить", "помню", "помнишь", "помнил", "помнила", "помним", "запомнить", "запомни",
    "напомнить", "напомнил", "напомнила", "напомни", "вспомнить", "вспомни",
    "потерял", "потеряла", "потеряли", "забыл", "забыла", "забыли", "контекст", "контексте",
    "случилось", "произошло", "произошел", "произошёл", "произошла", "диалог", "разговор", "беседа",
    "напиши", "написать", "напишите", "опиши", "описать", "опишите", "расскажи", "расскажите",
    "объясни", "объяснить", "объясните", "поясни", "пояснить", "покажи", "построй", "создай",
    "решил", "решила", "решили", "научно", "пошагово", "решать",
    "давай", "можешь", "может", "могу", "можно", "можем", "хочу", "хочешь", "нужно", "надо",
    "окей", "okay", "хорошо", "пожалуйста", "please", "работать", "работаем", "работай",
    "перенеси", "перенести", "перенос", "сделай", "вычисли", "рассчитай", "сравни", "найди", "проверь", "проанализируй", "приведи",
    "перечисли", "продолжи", "продолжим", "дальше", "далее", "есть", "какие", "какая", "какой",
    "должен", "должна", "должно", "должны", "был", "была", "были", "нет",
    "покажи", "показать", "покажите", "построй", "построить", "постройте", "сделай",
    "сделать", "сделайте", "создай", "создать", "создайте", "исправь", "исправить",
    "данные", "данных", "значение", "значения", "число", "числа", "точка", "точки",
    "график", "графика", "графике", "диаграмма", "диаграммы", "таблица", "таблицу",
    "таблице", "формула", "формулы", "уравнение", "цена", "цены", "цену", "цене",
    "стоимость", "стоимости", "рост", "роста", "падение", "падения", "изменение",
    "изменения", "динамика", "динамики", "начинался", "начинались", "начинается",
    "начинаются", "начало", "сначала", "заканчивался", "заканчивались", "конец",
    "поменяй", "поменять", "изменить", "день", "дня", "дней", "днями", "неделя",
    "неделю", "недели", "месяц", "месяца", "месяцев", "год", "года", "грн", "руб",
    "рубль", "рубля", "рублей", "доллар", "доллара", "долларов", "евро", "пункт",
    "пункта", "строка", "строки", "колонка", "колонки", "линейный", "линейная",
    "столбчатый", "условный", "условная", "равномерно", "равномерный", "пример",
    "примера", "теперь", "снова", "далее", "также", "верно", "правильный",
    "the", "this", "that", "these", "those", "show", "build", "create", "make",
    "fix", "correct", "data", "value", "values", "point", "points", "chart", "graph",
    "table", "formula", "equation", "price", "prices", "cost", "growth", "fall",
    "change", "day", "days", "week", "weeks", "month", "months", "year", "years",
    "uah", "usd", "dollar", "dollars", "rubles", "ruble", "euro", "linear", "bar",
    # Pure conversational reactions should not become topical entities or conflicts.
    "спасибо", "спасиб", "благодарю", "благодарен", "благодарна", "классно", "круто",
    "отлично", "прекрасно", "здорово", "молодец", "именно", "понятно", "ладно",
    "согласен", "согласна", "правильно", "верно", "точно", "нравится", "ужасно",
    "раздражает", "бесит", "переделай", "перепиши", "исправь", "улучши", "поправь",
    "поняла", "понял", "получилось", "отнюдь", "мимо", "ошибка", "виду", "смысл",
}
_CONTEXT_REFERENCE_TERMS = {
    "это", "этого", "этой", "этом", "эту", "этот", "эта", "эти", "этих",
    "тот", "та", "ту", "те", "того", "той", "тех", "данный", "данная", "данное",
    "он", "она", "оно", "они", "его", "ее", "ему", "ей", "им", "их", "них",
    "него", "нее", "неё", "ней", "ним", "previous", "earlier", "these", "those",
    "this", "that", "same", "them", "it", "he", "she", "they", "him", "her", "its",
    "дальше", "ещё", "еще",
}

def _subject_family(token: Any) -> str:
    value = _text(token).lower().replace("ё", "е")
    return value[:5] if len(value) >= 5 else value

_CONTEXT_NON_TOPICAL_ROOTS = (
    "называ", "зовут", "помн", "запом", "напом", "вспом", "потер", "забыл",
    "контекст", "случил", "произош", "диалог", "разговор", "бесед", "обращ",
    "напиш", "опиш", "расскаж", "объясн", "поясн", "покаж", "постро", "созда",
    "сдела", "вычисл", "рассчит", "сравн", "найд", "проверь", "проанализ", "привед",
    "перечисл", "продолж", "дальш", "должн", "каки", "был", "работ", "перенес", "перенос",
    "можеш", "может", "могу", "давай", "хочет", "хотел", "сможет", "сможешь", "просит", "попрос",
    "формул", "график", "таблиц", "диаграмм", "уравнен", "данн", "значен",
    "придум", "предложи", "почем", "почему", "зачем", "открыл", "изобрел", "изобрёл",
    "доказал", "обосновал", "считал", "называл",
    # Provenance questions describe an action/source, not a new topic.
    "слиз", "скопир", "скач", "источник", "автор", "напис", "придум",
    "плагиат", "нет", "нета",
)

_PARTICIPANT_SPEAKER_WORDS = {
    "я", "меня", "мне", "мной", "мой", "моя", "мое", "моё", "мои", "моего", "моей",
    "i", "me", "my", "mine", "myself", "мені", "мій", "моя", "моє", "мої",
}
_PARTICIPANT_INTERLOCUTOR_WORDS = {
    "ты", "тебя", "тебе", "тобой", "твой", "твоя", "твое", "твоё", "твои", "твоего", "твоей",
    "you", "your", "yours", "yourself", "тобі", "твоїй", "твій", "твоє", "твої",
}


def _is_non_topical_subject_term(token: str) -> bool:
    if token in _CONTEXT_GENERIC_TERMS:
        return True
    return any(len(root) >= 5 and token.startswith(root) for root in _CONTEXT_NON_TOPICAL_ROOTS)


def _contains_named_value(text: Any) -> bool:
    """Detect a likely proper-name value without treating sentence starts as names."""
    value = _text(text)
    for match in re.finditer(r"(?<![\w])[А-ЯЁA-Z][а-яёa-z]{2,}(?![\w])", value):
        prefix = value[:match.start()].rstrip()
        # Sentence-initial capitalization is not evidence of a name; capitalized
        # words after a comma, colon or a relational phrase may be.
        if not prefix or re.search(r"[.!?…]\s*$", prefix):
            continue
        return True
    return False


def _participant_alignment(query: str, row: dict[str, Any]) -> int:
    """Return factual evidence for the person referred to by a subjectless query.

    Only a stored turn that actually contains a likely name value on the appropriate
    participant side is preferred. A previous answer that merely says the name is
    missing therefore cannot outrank a turn that records the name itself.
    """
    if _subject_tokens(query):
        return 0
    q_tokens = _tokens(query)
    q_speaker = bool(q_tokens & _PARTICIPANT_SPEAKER_WORDS)
    q_interlocutor = bool(q_tokens & _PARTICIPANT_INTERLOCUTOR_WORDS)
    if q_speaker == q_interlocutor:
        return 0

    user_text = _text(row.get("user_text") or row.get("user_text_en"))
    april_text = _text(row.get("april_text") or row.get("april_text_en"))
    memory_summary = _compact_memory_summary(row)
    all_tokens = _semantic_tokens(" ".join((
        user_text, _text(row.get("user_text_en")), april_text,
        _text(row.get("april_text_en")), memory_summary, _row_attachment_evidence(row),
    )))
    query_tokens = _semantic_tokens(query)
    if not query_tokens or not _concept_overlap(query_tokens, all_tokens):
        return 0

    user_tokens = _tokens(user_text)
    april_tokens = _tokens(april_text)
    user_has_value = _contains_named_value(user_text)
    april_has_value = _contains_named_value(april_text)
    user_speaker = bool(user_tokens & _PARTICIPANT_SPEAKER_WORDS)
    user_interlocutor = bool(user_tokens & _PARTICIPANT_INTERLOCUTOR_WORDS)
    april_speaker = bool(april_tokens & _PARTICIPANT_SPEAKER_WORDS)
    april_interlocutor = bool(april_tokens & _PARTICIPANT_INTERLOCUTOR_WORDS)

    if q_speaker:
        # The user's first-person statements and April's second-person answers both
        # describe the authenticated user. A name-less deferral is not a fact source.
        supports_target = (user_speaker and user_has_value) or (april_interlocutor and april_has_value)
    else:
        # User's second-person questions and April's first-person answers describe April.
        supports_target = (user_interlocutor and user_has_value) or (april_speaker and april_has_value)
    return 1 if supports_target else 0


def _subject_tokens(value: Any) -> set[str]:
    """Approximate subject/entity signature, excluding task, format and unit words."""
    result = set()
    for token in _semantic_tokens(value):
        if token.isdigit() or _is_non_topical_subject_term(token) or len(token) < 4:
            continue
        family = _subject_family(token)
        if family and not _is_non_topical_subject_term(family):
            result.add(family)
    return result

def _row_subject_text(row: dict[str, Any]) -> str:
    """Prefer the user's original task and persisted request intent over generated prose."""
    request = _parse_json(row.get("structured_request"))
    request_structure = request.get("request_structure") if isinstance(request.get("request_structure"), dict) else {}
    request_intent = request.get("intent") if isinstance(request.get("intent"), dict) else {}
    dialogue = request.get("dialogue") if isinstance(request.get("dialogue"), dict) else {}
    continuation = dialogue.get("continuation_context") if isinstance(dialogue.get("continuation_context"), dict) else {}
    response = _parse_json(row.get("structured_response"))
    memory_record = response.get("dialogue_memory_record")
    if not isinstance(memory_record, dict):
        metadata = response.get("metadata") if isinstance(response.get("metadata"), dict) else {}
        memory_record = metadata.get("dialogue_memory_record") if isinstance(metadata.get("dialogue_memory_record"), dict) else {}
    values = (
        row.get("user_text"), row.get("user_text_en"),
        request_structure.get("user_goal"), request_structure.get("task_goal"),
        request_intent.get("user_goal"), continuation.get("active_topic"),
        memory_record.get("topic"), row.get("memory_summary"),
    )
    return " ".join(_text(item) for item in values if _text(item))

def _row_subject_tokens(row: dict[str, Any]) -> set[str]:
    return _subject_tokens(_row_subject_text(row))

def _subject_overlap(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return round(_concept_overlap(left, right), 6)

def _subject_conflicts(query_subjects: set[str], row_subjects: set[str]) -> bool:
    # Missing subject evidence is neutral; two populated but disjoint signatures
    # indicate different contexts, even if the task vocabulary is almost identical.
    return bool(query_subjects and row_subjects and _subject_overlap(query_subjects, row_subjects) < 0.20)

def _numeric_anchors(value: Any) -> set[str]:
    found = set()
    for match in re.finditer(r"(?<![\w])\d+(?:[.,]\d+)?(?![\w])", _text(value)):
        try:
            number = float(match.group(0).replace(",", "."))
        except (TypeError, ValueError):
            continue
        found.add(f"{number:.6f}".rstrip("0").rstrip("."))
    return found

def _query_numeric_overlap(query: str, row: dict[str, Any], query_subjects: set[str]) -> float:
    query_numbers = _numeric_anchors(query)
    if not query_numbers:
        return 0.0
    # Compare with the original user request, not generated table row labels like Day 5.
    source_text = " ".join((_text(row.get("user_text")), _text(row.get("user_text_en"))))
    source_numbers = _numeric_anchors(source_text)
    if not source_numbers:
        return 0.0
    # Numbers alone are weak evidence; they contribute only within a compatible subject.
    row_subjects = _row_subject_tokens(row)
    if _subject_conflicts(query_subjects, row_subjects):
        return 0.0
    return len(query_numbers & source_numbers) / max(1, len(query_numbers))


def _source_data_alignment(row: dict[str, Any], protected_data: dict[str, Any] | None = None) -> float:
    """Measure whether a row's value-bearing output preserves numbers from the user's source request.

    This is provenance evidence, not a claim that every derived answer is correct. It helps
    choose the original data-defining turn over a newer format-conversion response when a
    follow-up says 'these data' without repeating the values.
    """
    source_text = " ".join((_text(row.get("user_text")), _text(row.get("user_text_en"))))
    source_numbers = _numeric_anchors(source_text)
    if len(source_numbers) < 2:
        return 0.0
    protected = protected_data if isinstance(protected_data, dict) else _protected_structured_data_from_row(row)
    # Score the typed payload only, not generated prose: an answer can repeat the
    # correct values in its explanation while the actual table/graph is wrong.
    items = protected.get("items") if isinstance(protected.get("items"), list) else []
    typed_values = [item.get("data") for item in items if isinstance(item, dict) and isinstance(item.get("data"), dict)]
    output_numbers = _numeric_anchors(json.dumps(typed_values, ensure_ascii=False, default=str))
    if not output_numbers:
        return 0.0
    return round(len(source_numbers & output_numbers) / max(1, len(source_numbers)), 6)

def _structured_data_richness(payload: Any) -> int:
    if not isinstance(payload, dict):
        return 0
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    richness = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        data = item.get("data") if isinstance(item.get("data"), dict) else {}
        encoded = json.dumps(data, ensure_ascii=False, default=str)
        # A schema declaration without values is much less useful than retained points/rows.
        has_values = any(key in data for key in ("payload", "spec", "points", "data_points", "series", "datasets", "rows", "matrix", "x_values", "y_values"))
        richness += (8 if has_values else 1) + min(24, len(encoded) // 120)
    return richness

def _query_context_signature(query: str, interpretation: dict[str, Any] | None = None) -> dict[str, Any]:
    interpretation = interpretation if isinstance(interpretation, dict) else {}
    supplied = interpretation.get("context_signature")
    if isinstance(supplied, dict):
        terms = supplied.get("subject_terms")
        if isinstance(terms, list):
            cleaned_terms = {
                _subject_family(item)
                for item in terms
                if _text(item) and not _is_non_topical_subject_term(_text(item).lower().replace("ё", "е"))
            }
            return {
                **supplied,
                "subject_terms": sorted(term for term in cleaned_terms if not _is_non_topical_subject_term(term)),
                "has_explicit_subject": bool(cleaned_terms),
            }
    subjects = _subject_tokens(query)
    refs = _semantic_tokens(query) & _CONTEXT_REFERENCE_TERMS
    return {
        "subject_terms": sorted(subjects)[:12],
        "has_explicit_subject": bool(subjects),
        "reference_strength": round(min(1.0, len(refs) / max(2.0, len(_tokens(query)) * 0.35)), 3),
        "reference_terms": sorted(refs)[:8],
        "output_forms": [],
        "numeric_anchors": sorted(_numeric_anchors(query))[:8],
    }


def _user_operation_profile(
    query: str,
    interpretation: dict[str, Any] | None,
    *,
    history_request: bool = False,
    new_topic_request: bool = False,
    is_correction: bool = False,
    is_short_acknowledgement: bool = False,
) -> dict[str, Any]:
    """Describe the user's discourse operation separately from topic identity.

    This is an additive interpretation layer. It deliberately reuses the existing
    semantic/pragmatic labels and does not alter tone classification or response
    style; it only tells retrieval whether the message is operating on the current
    branch, asking for a source, or opening an independent request.
    """
    profile = interpretation if isinstance(interpretation, dict) else {}
    pragmatic = profile.get("pragmatic_features") if isinstance(profile.get("pragmatic_features"), dict) else {}
    intent = _text(profile.get("primary_intent")).upper()
    direction = _text(profile.get("direction")).upper()
    topic_reference = _text(profile.get("topic_reference")).upper()
    speech_act = _text(profile.get("speech_act")).upper()
    communicative_act = _text(profile.get("communicative_act")).upper()
    relation_hint = _text(profile.get("relation_hint")).upper()

    if history_request:
        operation = "RETRIEVE_DIALOGUE_SOURCE"
        evidence = "history_request"
    elif new_topic_request:
        operation = "OPEN_NEW_TOPIC"
        evidence = "explicit_topic_switch"
    elif speech_act in {"NEGATION_OR_DISAGREEMENT", "FRUSTRATION_OR_DISSATISFACTION"} or communicative_act == "RESPOND_TO_DISAGREEMENT":
        # Keep emotional disagreement distinct from a factual correction operation.
        # The original tone label is preserved independently below.
        operation = "DISAGREE_OR_EXPRESS_DISSATISFACTION"
        evidence = "pragmatic_disagreement"
    elif is_correction or speech_act in {"CORRECTION_OR_REVISION", "REVISION_REQUEST"} or bool(
        profile.get("active_branch_repair")
        or pragmatic.get("active_branch_repair")
        or profile.get("previous_answer_reference")
        or pragmatic.get("previous_answer_reference")
        or profile.get("factual_verification_request")
        or pragmatic.get("factual_verification_request")
    ):
        operation = "CORRECT_OR_VERIFY_PREVIOUS_TURN"
        evidence = "correction_or_previous_answer_reference"
    elif communicative_act == "CLARIFICATION" or speech_act == "CLARIFICATION_REQUEST":
        operation = "CLARIFY_PREVIOUS_POINT"
        evidence = "clarification_act"
    elif speech_act in {"AGREEMENT_OR_ACKNOWLEDGEMENT", "POSITIVE_EVALUATION", "GRATITUDE_OR_APPRECIATION"} or is_short_acknowledgement:
        operation = "REACT_TO_PREVIOUS_TURN"
        evidence = "acknowledgement_or_evaluation"
    elif profile.get("parent_context_dependency") and (profile.get("requires_memory") or relation_hint == "CONTINUE"):
        operation = "APPLY_NEW_OPERATION_TO_ACTIVE_BRANCH"
        evidence = "parent_context_dependency"
    elif (
        intent == "TOPIC_CONTINUATION"
        or relation_hint == "CONTINUE"
        or direction in {"RESUME_OR_RETRIEVE_ACTIVE_TOPIC", "SEARCH_ACTIVE_OR_REFERENCED_TOPIC"}
        or topic_reference in {"PREVIOUS_OR_ACTIVE_TOPIC", "PREVIOUS_ASSISTANT_ANSWER", "TOPIC_FRAGMENT"}
    ):
        operation = "DEVELOP_ACTIVE_BRANCH"
        evidence = "semantic_continuation_intent"
    elif speech_act in {"EXPLANATION_REQUEST", "REFERENTIAL_CONTINUATION", "CONTINUATION_REQUEST"}:
        operation = "EXPLAIN_OR_EXTEND_CURRENT_POINT"
        evidence = "dialogue_act"
    elif intent == "NEW_INFORMATION":
        operation = "REQUEST_NEW_INFORMATION"
        evidence = "new_information_intent"
    elif _text(query).strip():
        operation = "GENERAL_REQUEST_OR_STATEMENT"
        evidence = "fallback"
    else:
        operation = "EMPTY_INPUT"
        evidence = "empty_query"

    return {
        "type": operation,
        "evidence": evidence,
        "semantic_intent": intent or "UNSPECIFIED",
        "direction": direction or "UNSPECIFIED",
        "topic_reference": topic_reference or "UNSPECIFIED",
        "relation_hint": relation_hint or "UNSPECIFIED",
        "speech_act": speech_act or "UNSPECIFIED",
        "communicative_act": communicative_act or "UNSPECIFIED",
        # Keep the upstream tone visible and untouched. This field is descriptive,
        # never a replacement for the original emotional/pragmatic interpretation.
        "tone": _text(profile.get("tone") or "NEUTRAL").upper(),
    }


# Premium has one canonical dialogue store.  These helpers mark ongoing work
# inside the existing structured_response JSONB rather than creating a second
# task/session table.  The marker is deliberately descriptive and bounded.
_WORK_ACTION_RE = re.compile(
    r"(?:созда\w*|придум\w*|загадай\w*|загадыва\w*|сгенер\w*|нарис\w*|реш\w*|рассчит\w*|"
    r"напиш\w*|допиш\w*|перепиш\w*|исправ\w*|почин\w*|отлад\w*|"
    r"реализ\w*|разработ\w*|постро\w*|состав\w*|улучш\w*|редактир\w*|"
    r"передел\w*|добав\w*|продолж\w*|проверь\w*|спроектир\w*|анимир\w*|"
    r"сделай\w*|собери\w*|провед\w*|игра\w*|играем|поигра\w*|"
    r"build\w*|create\w*|generate\w*|draw\w*|solve\w*|calculate\w*|"
    r"write\w*|implement\w*|debug\w*|fix\w*|edit\w*|redesign\w*|"
    r"improve\w*|continue\w*|modify\w*|play\w*)",
    re.IGNORECASE,
)
_WORK_OBJECT_RE = re.compile(
    r"(?:задач\w*|пример\w*|загадк\w*|головолом\w*|riddle\w*|puzzle\w*|quiz\w*|решени\w*|уравнен\w*|формул\w*|код\w*|скрипт\w*|"
    r"функци\w*|проект\w*|схем\w*|диаграм\w*|график\w*|таблиц\w*|"
    r"картин\w*|изображен\w*|визуал\w*|эффект\w*|анимац\w*|макет\w*|"
    r"документ\w*|файл\w*|программ\w*|игр\w*|правил\w*|ход\w*|квест\w*|"
    r"сценар\w*|модел\w*|прототип\w*|задач\w*|example\w*|problem\w*|"
    r"code\w*|script\w*|function\w*|project\w*|diagram\w*|chart\w*|"
    r"image\w*|picture\w*|effect\w*|animation\w*|game\w*|equation\w*|formula\w*)",
    re.IGNORECASE,
)
_ACTIVE_CHOICE_RE = re.compile(
    r"(?:выбирай|выбери(?:те)?|выберите действие|твой ход|ваш ход|"
    r"какой вариант|выбери один|ответь цифрой|пришли номер|"
    r"choose (?:one|an option)|your move|your turn|pick (?:one|an option)|"
    r"select (?:one|an option)|вариант\s*[:：]?\s*[1-9]|\b[1-9]\s*[,/и]\s*[1-9])",
    re.IGNORECASE,
)
_CHOICE_REPLY_RE = re.compile(
    r"(?:^\s*(?:вариант|option|пункт|номер)\s*[1-9]\b|"
    r"\b(?:я\s+)?(?:выбираю|выбрал|выбрала|беру|выберу|choose|pick|select)\s+"
    r"(?:(?:вариант|option|пункт|номер)\s*)?[1-9]\b)",
    re.IGNORECASE,
)
_SINGLE_SCALAR_REPLY_RE = re.compile(
    r"^\s*(?:[+-]?(?:\d+(?:[.,]\d+)?|[.,]\d+)|[A-Za-zА-Яа-яЁё])\s*[.!)]?\s*$",
    re.IGNORECASE,
)


def _is_single_scalar_reply(value: Any) -> bool:
    """Recognize one standalone numeric value or one Latin/Cyrillic letter."""
    return bool(_SINGLE_SCALAR_REPLY_RE.fullmatch(_text(value)))

_INTERACTIVE_ACTION_RE = re.compile(
    r"(?:\bя\s+)?(?:крич\w*|зову\w*|говор\w*|спрашива\w*|иду\w*|пош[её]л\w*|"
    r"заш[её]л\w*|приш[еёо]л\w*|приш\w*\s+за\b|вхожу\w*|захожу\w*|откр\w*|подход\w*|беру\w*|ищу\w*|"
    r"осматрива\w*|трога\w*|нажима\w*|выбира\w*|выбрал\w*|выбираю\w*|"
    r"поднима\w*|спуска\w*|атакую\w*|бегу\w*|использую\w*|"
    r"i\s+(?:shout|call|say|ask|go|enter|open|take|look|inspect|choose|press|use)\w*)",
    re.IGNORECASE,
)
_BRANCH_OPERATION_RE = re.compile(
    r"(?:продолж\w*|дальше|следующ\w*|"
    r"добав\w*\s+(?:к|в|туда)|исправ\w*|передел\w*|допиш\w*|перепиш\w*|"
    r"измени\w*|улучши\w*|сохрани\w*|покажи\w*\s+(?:ещ[её]|снова|его|её|это)|"
    r"на\s+основе\s+(?:этого|этой|него)|к\s+(?:нему|ней|этому|этой)|"
    r"continue\w*|next\b|"
    r"revise\w*|edit\w*|fix\w*|add\w*\s+(?:to|into)|change\w*)",
    re.IGNORECASE,
)


def _response_and_request_records(row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    request = _parse_json(row.get("structured_request"))
    response = _parse_json(row.get("structured_response"))
    metadata = response.get("metadata") if isinstance(response.get("metadata"), dict) else {}
    memory_record = response.get("dialogue_memory_record")
    if not isinstance(memory_record, dict):
        memory_record = metadata.get("dialogue_memory_record") if isinstance(metadata.get("dialogue_memory_record"), dict) else {}
    return request, response, memory_record if isinstance(memory_record, dict) else {}


def _assistant_expects_user_input(answer_text: str) -> bool:
    """Return whether the latest assistant turn visibly leaves an input/action open.

    This is recomputed from the saved answer because older task markers may carry a
    stale ``expects_choice`` value after the assistant has moved to a new step.
    A numbered list on its own is not enough; there must be an invitation/question.
    """
    text = _text(answer_text)
    if not text:
        return False
    if _ACTIVE_CHOICE_RE.search(text):
        return True
    # A direct question at the end of April's turn leaves the dialogue open.
    # This is important for generated follow-ups such as “Следующий вопрос:
    # какая самая большая планета?”: the next one-word answer is not a new topic.
    if re.search(r"[?？](?:[\"'»”\)\]]*)\s*$", text):
        return True
    low = text.lower().replace("ё", "е")
    # Assistant turns often invite an answer through an imperative rather than a
    # question mark (for example, “Назови цвет предмета…”). Treat these as an open
    # input slot too; otherwise a one-word answer such as “Белый” is misrouted as
    # a new topic and the active task's rules disappear from the next prompt.
    invitation = bool(re.search(
        r"(?:выбери(?:те)?|выбирай|что\s+выберешь|какой\s+(?:вариант|пункт|ход)|"
        r"твой\s+ход|ваш\s+ход|твоя\s+очередь|теперь\s+ты|теперь\s+ваш\s+ход|"
        r"ответь(?:те)?|напиши(?:те)?|пришли(?:те)?|загрузи(?:те)?|покажи(?:те)?|"
        r"укажи(?:те)?|сообщи(?:те)?|скажи(?:те)?(?:\s+мне)?|"
        r"назови(?:те)?|опиши(?:те)?|перечисли(?:те)?|оцени(?:те)?|уточни(?:те)?|"
        r"подтверди(?:те)?|определи(?:те)?|вычисли(?:те)?|сравни(?:те)?|"
        r"расскажи(?:те)?|объясни(?:те)?|поясни(?:те)?|представь(?:те)?|"
        r"пусть\s+(?:все\s+)?(?:игроки|участники)\s+отвеча\w*|"
        r"(?:игроки|участники)\s+отвеча\w*|"
        r"choose|pick\s+(?:one|an option)|your\s+turn|your\s+move|send\s+me|provide\s+the|"
        r"name\s+(?:the|a)\b|describe\b|list\b|rate\b|specify\b|tell\s+me\b)",
        low,
    ))
    # Common labeled alternatives (А/Б/В or A/B/C) count only if the answer
    # actually asks the user to choose/respond, not when they are merely explained.
    alternatives = bool(re.search(
        r"(?:^|\n)\s*(?:[А-ЯA-C])\s*[.)—:：-].{0,160}"
        r"(?:\n\s*(?:[А-ЯA-C])\s*[.)—:：-].{0,160}){1,}", text, re.IGNORECASE
    ))
    return invitation and (alternatives or "?" in text or "？" in text or len(text) < 220)


def _looks_like_new_work_root_request(query: str, branch: dict[str, Any] | None = None) -> bool:
    """Recognize a self-contained request that starts a new piece of work.

    Deliberately uses action + object semantics, not game/task-specific triggers.
    Requests explicitly operating on an existing artifact remain continuations.
    """
    text = _text(query)
    if len(text) < 10:
        return False
    low = text.lower().replace("ё", "е")
    root_action = bool(re.search(
        r"(?:созда\w*|придум\w*|загадай\w*|загадыва\w*|сгенер\w*|нарис\w*|реш\w*|рассчит\w*|напиш\w*|"
        r"разработ\w*|спроектир\w*|постро\w*|состав\w*|провед\w*|поигра\w*|"
        r"давай\s+(?:сыграем|поиграем)|build\w*|create\w*|generate\w*|draw\w*|"
        r"solve\w*|calculate\w*|write\w*|implement\w*|design\w*|play\s+(?:a\s+)?(?:new\s+)?game)",
        low,
    ))
    if not root_action or not _WORK_OBJECT_RE.search(low):
        return False
    explicit_new = bool(re.search(
        r"(?:нов\w*|друг\w*|отдельн\w*|с\s+нуля|заново|сначала|another|new|from\s+scratch)", low
    ))
    references_existing_artifact = bool(re.search(
        r"(?:эт(?:от|а|о|у)\s+(?:код\w*|скрипт\w*|проект\w*|задач\w*|решени\w*|"
        r"игр\w*|картин\w*|изображен\w*|файл\w*|схем\w*|диаграмм?\w*|график\w*|"
        r"пример\w*|загадк\w*|головолом\w*)|на\s+основе\s+(?:этого|этой|него|нее|неё)|"
        r"в\s+этом\s+(?:коде|проекте|файле|графике)|по\s+этой\s+(?:задаче|схеме|картинке))",
        low,
    ))
    continuation_operation = bool(re.search(
        r"(?:продолж\w*|допиш\w*|следующ\w*|добав\w*|исправ\w*|передел\w*|"
        r"перепиш\w*|измени\w*|улучши|отредактир\w*|расшир\w*|доработ\w*|"
        r"continue\w*|append\w*|extend\w*|next\b|revise\w*|edit\w*|fix\w*|add\w*|modify\w*)",
        low,
    ))
    branch_text = " ".join((
        _text(branch.get("topic")) if isinstance(branch, dict) else "",
        _text(branch.get("goal")) if isinstance(branch, dict) else "",
        _text(branch.get("state_summary")) if isinstance(branch, dict) else "",
    ))
    branch_overlap = _topic_query_overlap(text, branch_text) if branch_text else 0.0
    # A generic word such as "поиграем" or "продолжение" must not make an
    # independent request inherit an older game/task just because the same
    # sentence also contains "active task". Compare the current subject with the
    # saved branch before allowing generic continuation wording to veto a new root.
    branch_subject_conflict = bool(
        branch_text
        and _subject_conflicts(_subject_tokens(text), _subject_tokens(branch_text))
    )
    explicit_named_branch_operation = bool(re.search(
        r"\b(?:продолж\w*|продолжим|вернемся|вернёмся)\s+(?:к\s+)?(?:эт\w*\s+)?"
        r"(?:игр\w*|задач\w*|загадк\w*|головолом\w*|квест\w*|сценар\w*|"
        r"код\w*|скрипт\w*|проект\w*|формул\w*|схем\w*|диаграм\w*|файл\w*)\b|"
        r"\b(?:в\s+эт\w*\s+игр\w*|следующ\w*\s+(?:ход|загадк|пункт)\w*)\b",
        low,
    ))
    implicit_continuation = bool(re.search(
        r"(?:продолжени\w*\s+(?:кода|задач\w*|игр\w*|схем\w*|истори\w*)|"
        r"next\s+(?:step|part|move)|continue\s+the)", low
    ))
    if not explicit_new and (
        references_existing_artifact
        or explicit_named_branch_operation
        or (
            (continuation_operation or implicit_continuation)
            and branch_overlap >= 0.12
            and not (root_action and branch_subject_conflict)
        )
    ):
        return False
    # Root verbs such as “invent”, “draw”, “solve”, or “write” plus an explicit
    # work object define a new brief unless the sentence says to continue/edit an
    # already referenced artifact. “In this chat” is not itself such a reference.
    return True


def _looks_like_answer_verification(query: str) -> bool:
    """Detect requests to evaluate an earlier user answer against its source task."""
    low = _text(query).lower().replace("ё", "е")
    asks_verdict = bool(re.search(
        r"(?:угад\w*|правильн\w*\s+(?:ли\s+)?(?:ответ\w*|сказ\w*|выбрал\w*|решил\w*)|"
        r"неправильн\w*\s+(?:сказ\w*|ответ\w*|решил\w*)|верн\w*\s+ли\s+(?:мой\s+)?ответ|"
        r"мой\s+ответ|если\s+я\s+(?:ошиб\w*|не\s+прав|не\s+угад\w*)|"
        r"tell\s+me\s+if\s+i\s+(?:was\s+wrong|got\s+it\s+right)|did\s+i\s+guess\s+right)", low
    ))
    refers_to_source_or_conditions = bool(re.search(
        r"(?:услови\w*|загад\w*|вопрос\w*|пример\w*|задач\w*|решени\w*|расчет\w*|расчёт\w*|"
        r"правил\w*|то\s+что\s+я\s+(?:сказ\w*|ответ\w*|выбрал\w*)|"
        r"как\s+ты\s+(?:задава\w*|спрашива\w*|предлож\w*|объясн\w*)|"
        r"original\s+(?:question|task|riddle)|conditions|rules)", low
    ))
    return asks_verdict and refers_to_source_or_conditions


def _infer_active_work_branch(row: dict[str, Any]) -> dict[str, Any]:
    """Recognize saved, still-actionable work from canonical pair content.

    Explicit markers win. The heuristic fallback intentionally recognizes old
    Premium rows saved before this version, so deploying the patch does not require
    clearing history or migrating PostgreSQL columns.
    """
    if not isinstance(row, dict):
        return {}
    request, response, memory_record = _response_and_request_records(row)
    metadata = response.get("metadata") if isinstance(response.get("metadata"), dict) else {}
    marker = response.get("active_work_branch")
    if not isinstance(marker, dict):
        marker = metadata.get("active_work_branch")
    if not isinstance(marker, dict):
        marker = memory_record.get("active_work_branch")
    if isinstance(marker, dict) and marker.get("active"):
        # These are per-request routing diagnostics, not durable task state.
        # Old versions may have persisted them as true, so never trust them here.
        profile = dict(marker)
        profile.pop("matched_this_turn", None)
        profile.pop("match_reason", None)
        profile.pop("candidate_message_id", None)
        saved_answer = _text(row.get("april_text") or row.get("april"))
        saved_user = _text(row.get("user_text") or row.get("user"))
        if saved_user:
            profile.setdefault("last_user_text", saved_user[:500])
        if saved_answer:
            # A one-character/numeric move can be the complete assistant turn;
            # preserve its exact text separately from a lossy semantic summary.
            profile["last_assistant_answer"] = saved_answer[:900]
            profile["expects_choice"] = bool(
                _assistant_expects_user_input(saved_answer)
                or (_text(profile.get("kind")) == "interactive_game" and _is_single_scalar_reply(saved_answer))
            )
        return profile

    intent_root = request.get("intent") if isinstance(request.get("intent"), dict) else {}
    intent = intent_root.get("intent") if isinstance(intent_root.get("intent"), dict) else intent_root
    requested_outputs = request.get("requested_outputs")
    if not isinstance(requested_outputs, list):
        requested_outputs = intent.get("requested_outputs") if isinstance(intent.get("requested_outputs"), list) else []
    output_names = {str(item or "").strip().lower() for item in requested_outputs}
    render_blocks = response.get("render_blocks") if isinstance(response.get("render_blocks"), list) else []
    artifacts = response.get("artifacts") if isinstance(response.get("artifacts"), list) else []
    rendered_types = {
        str(item.get("type") or item.get("artifact_type") or "").strip().lower()
        for item in render_blocks + artifacts if isinstance(item, dict)
    }
    user_text = _text(row.get("user_text") or row.get("user"))
    answer_text = _text(row.get("april_text") or row.get("april"))
    summary = _text(memory_record.get("summary") or response.get("summary") or row.get("memory_summary"))
    topic = _text(memory_record.get("topic") or request.get("goal") or user_text)[:240]
    all_text = " ".join((user_text, topic, summary, answer_text[:1800])).lower().replace("ё", "е")
    user_low = user_text.lower().replace("ё", "е")
    answer_low = answer_text.lower().replace("ё", "е")

    wants_code = bool(intent.get("wants_code") or "code" in output_names or "python" in output_names or "source_code" in output_names)
    wants_visual = bool(intent.get("wants_image") or intent.get("wants_graph") or output_names & {
        "image", "gallery", "graph", "diagram", "chart", "formula", "table", "file", "code", "document"
    } or rendered_types & {"image", "graph", "diagram", "chart", "formula", "table", "code", "file", "document"})
    game_signal = bool(re.search(r"(?:\bигр\w*|\bигрок\w*|\bквест\w*|\bбашн\w*|\bключ\w*|\bсердц\w*|\bхранител\w*|\bправил\w*|\bход\w*|\bgame\w*|\bquest\w*|\btower\w*|\bkey\w*|\byour turn\b|\bтвой ход\b)", all_text))
    scalar_game_move = bool(
        game_signal
        and re.search(r"(?:\bигр\w*|\bgame\w*|\bход\w*|\byour turn\b)", user_low, re.IGNORECASE)
        and _is_single_scalar_reply(answer_text)
    )
    expects_choice = bool(_assistant_expects_user_input(answer_text) or scalar_game_move)
    interaction_state = bool(game_signal and (
        expects_choice
        or _INTERACTIVE_ACTION_RE.search(answer_text)
        or _INTERACTIVE_ACTION_RE.search(user_low)
        or re.search(r"(?:начат\w*\s+(?:нов\w*\s+)?(?:совместн\w*\s+)?(?:пошагов\w*\s+)?игр|продолжен\w*\s+игр|твой ход|your turn|choose|выбирай)", answer_low)
        or _WORK_ACTION_RE.search(user_low)
    ))
    # April may create the active next step itself by asking a question or
    # explicitly inviting a response. Keep that branch even when the user did not
    # originate a formal task and the subject words in the reply are very short.
    interactive_dialogue_state = bool(expects_choice and not interaction_state)
    task_action = bool(_WORK_ACTION_RE.search(user_low))
    task_object = bool(_WORK_OBJECT_RE.search(user_low))
    explicit_artifact = wants_code or wants_visual
    active = bool(explicit_artifact or interaction_state or interactive_dialogue_state or (task_action and task_object))
    if not active:
        return {}

    if interaction_state:
        kind = "interactive_game"
    elif wants_code or rendered_types & {"code", "file"} or re.search(r"(?:код\w*|скрипт\w*|программ\w*|source code|python)", all_text):
        kind = "code_or_software_task"
    elif re.search(r"(?:картин\w*|изображен\w*|рису\w*|визуал\w*|эффект\w*|анимац\w*|image\w*|picture\w*)", all_text):
        kind = "visual_creation_or_editing"
    elif re.search(r"(?:задач\w*|пример\w*|загадк\w*|головолом\w*|riddle\w*|puzzle\w*|quiz\w*|решени\w*|уравнен\w*|формул\w*|математ\w*|расчет\w*|расчёт\w*|solve\w*|equation\w*)", all_text):
        kind = "problem_solving"
    elif re.search(r"(?:схем\w*|диаграм\w*|график\w*|таблиц\w*|документ\w*|план\w*|макет\w*|diagram\w*|chart\w*)", all_text):
        kind = "structured_artifact"
    elif interactive_dialogue_state:
        kind = "interactive_dialogue"
    else:
        kind = "active_task"

    message_id = _text(row.get("message_id"))[:120]
    return {
        "active": True,
        "priority": "HOT_TASK_FIRST",
        "work_id": _text(marker.get("work_id") if isinstance(marker, dict) else "") or ("work:" + message_id if message_id else "work:active"),
        "kind": _text(marker.get("kind") if isinstance(marker, dict) else "") or kind,
        "topic": _text((marker.get("topic") if isinstance(marker, dict) else "") or topic or user_text)[:240],
        "goal": _text((marker.get("goal") if isinstance(marker, dict) else "") or user_text)[:500],
        "state_summary": _text((marker.get("state_summary") if isinstance(marker, dict) else "") or summary or answer_text)[:800],
        "last_action": _text((marker.get("last_action") if isinstance(marker, dict) else "") or user_text)[:240],
        "expects_choice": bool((marker.get("expects_choice") if isinstance(marker, dict) else False) or expects_choice),
        "last_user_text": user_text[:500],
        "last_assistant_answer": answer_text[:900],
        "recent_steps": [{"message_id": message_id, "user_text": user_text[:500], "april_text": answer_text[:900], "topic": topic[:180]}],
        "source_message_id": _text((marker.get("source_message_id") if isinstance(marker, dict) else "") or message_id)[:120],
        "origin_message_id": _text((marker.get("origin_message_id") if isinstance(marker, dict) else "") or message_id)[:120],
        "dialog_id": _text(row.get("dialog_id"))[:120],
        "conversation_id": _text(row.get("conversation_id"))[:120],
        "updated_at": row.get("created_at"),
    }


_WORK_ROOT_ACTION_RE = re.compile(
    r"(?:созда\w*|придум\w*|загадай\w*|загадыва\w*|сгенер\w*|нарис\w*|реш\w*|"
    r"рассчит\w*|напиш\w*|разработ\w*|спроектир\w*|постро\w*|состав\w*|"
    r"провед\w*|изучи\w*|объясни\w*|проанализируй\w*|расшифруй\w*|вычисли\w*|"
    r"проверь\w*|найди\w*|определи\w*|опиши\w*|сравни\w*|разбери\w*|игра\w*|поигра\w*|"
    r"build\w*|create\w*|generate\w*|draw\w*|solve\w*|calculate\w*|write\w*|"
    r"implement\w*|design\w*|analy[sz]e\w*|explain\w*|inspect\w*|decode\w*|play\w*)",
    re.IGNORECASE,
)


def _is_active_work_root_candidate(row: dict[str, Any], profile: dict[str, Any], expected_kind: str) -> bool:
    """Find the task's original specification when upgrading legacy rows in place."""
    if not isinstance(row, dict) or not isinstance(profile, dict) or profile.get("kind") != expected_kind:
        return False
    user_text = _text(row.get("user_text") or row.get("user"))
    answer_text = _text(row.get("april_text") or row.get("april"))
    user_low = user_text.lower().replace("ё", "е")
    answer_low = answer_text.lower().replace("ё", "е")
    # Preserve the stronger title/structure check for an explicitly named game,
    # while also recognizing other structured roots (riddles, exercises, code, etc.)
    # even when their saved marker was misclassified as an interactive scene.
    user_starts_game = bool(re.search(
        r"(?:нов\w*\s+игр\w*|созда\w*\s+игр\w*|придум\w*\s+игр\w*|"
        r"перепиш\w*.{0,90}игр\w*|поигра\w*.{0,70}вместе|давай.{0,50}игр\w*)",
        user_low,
    ))
    answer_starts_game = bool(re.search(
        r"(?:начн[её]м.{0,60}нов\w*\s+игр\w*|начат\w*.{0,50}игр\w*|"
        r"нов\w*\s+игр\w*|игр\w*\s*[«\"]|игроки\s*:|цель\s*:|правила\s*:)",
        answer_low,
    ))
    user_has_object = bool(_WORK_OBJECT_RE.search(user_low))
    user_has_root_action = bool(_WORK_ROOT_ACTION_RE.search(user_low))
    answer_has_source = bool(answer_text.strip())
    explicit_structured_root = bool(
        user_has_root_action and user_has_object and answer_has_source
        and (
            answer_starts_game
            or profile.get("expects_choice")
            or _ACTIVE_CHOICE_RE.search(answer_text)
            or "?" in answer_text
            or "？" in answer_text
        )
    )
    if expected_kind == "interactive_game":
        return bool(
            user_starts_game and (answer_starts_game or bool(profile.get("expects_choice")))
            or explicit_structured_root
        )
    if expected_kind == "interactive_dialogue":
        # Only the turn that originated the open question is a root. A later
        # continuation may also end with a question, but its saved marker points
        # to the original message and must not replace that origin during recovery.
        profile_origin = _text(profile.get("origin_message_id"))
        row_id = _text(row.get("message_id"))
        same_root = not profile_origin or not row_id or profile_origin == row_id
        return bool(answer_has_source and same_root and _assistant_expects_user_input(answer_text))

    # Prefer an original creation/solution request over a later small edit.
    return bool(user_has_root_action and user_has_object and answer_has_source)


def _hot_work_followup_candidate(
    query: str,
    branch: dict[str, Any] | None,
    branch_row: dict[str, Any] | None,
    *,
    history_request: bool = False,
    new_topic_request: bool = False,
    has_attachment: bool = False,
    reference_followup: bool = False,
) -> tuple[bool, str]:
    """Test the hot-task lane before generic historical ranking.

    It accepts choice replies and in-task actions that classic intent detection may
    label NEW, while refusing to hijack a clearly independent question.
    """
    text = _text(query).strip()
    if not text or not isinstance(branch, dict) or not branch.get("active") or not isinstance(branch_row, dict):
        return False, "no_active_work_branch"
    if history_request or new_topic_request:
        return False, "explicit_history_or_new_topic_switch"
    low = text.lower().replace("ё", "е")
    if _looks_like_new_work_root_request(text, branch):
        return False, "self_contained_new_work_root"
    tokens = _tokens(text)
    semantic_tokens = _semantic_tokens(text)
    pending_user_input = bool(
        branch.get("expects_choice")
        or _assistant_expects_user_input(_text(branch_row.get("april_text") or branch_row.get("april")))
    )
    topic = _text(branch.get("topic"))
    branch_text = " ".join((
        topic, _text(branch.get("goal")), _text(branch.get("state_summary")),
        _text(branch_row.get("user_text") or branch_row.get("user")),
        _text(branch_row.get("april_text") or branch_row.get("april")),
    ))
    is_choice = bool(re.fullmatch(
        r"\s*(?:(?:вариант|option|пункт|номер|выбираю|выбираю вариант)\s*)?\d{1,4}(?:[.,]\d+)?(?:\s*(?:вариант|option))?\s*[.!)]?\s*",
        low,
    ) or re.fullmatch(r"\s*(?:вариант|option)\s*\d{1,4}\s*[.!)]?\s*", low))
    is_single_scalar = _is_single_scalar_reply(low)
    if is_single_scalar and (pending_user_input or _text(branch.get("kind")) == "interactive_game"):
        return True, "single_scalar_reply_to_active_task"
    if is_choice and (pending_user_input or _text(branch.get("kind")) == "interactive_game"):
        # A bare numbered reply is unambiguous. For interactive games it remains
        # a plausible move even when legacy assistant text did not expose a formal
        # choice marker.
        return True, "choice_reply_to_open_active_task"

    has_operation = bool(_BRANCH_OPERATION_RE.search(low))
    has_reference = bool(reference_followup or re.search(
        r"(?:это|этот|эта|эту|его|ее|её|нему|ней|туда|такой|такая|"
        r"продолж\w*|дальше|следующ\w*|вариант|на основе|в этой|в этом|"
        r"the same|that one|this one|continue|next step)", low
    ))
    q_subjects = _subject_tokens(text)
    branch_subjects = _subject_tokens(branch_text)
    subject_conflict = _subject_conflicts(q_subjects, branch_subjects)
    # Option/turn vocabulary is weak topical evidence by itself. Remove it before
    # checking whether a complete question introduces a genuinely different subject.
    independent_subjects = q_subjects - {"вариа", "вариант", "пункт", "номер", "выбор", "ход", "оптион"}
    independent_subject_conflict = _subject_conflicts(independent_subjects, branch_subjects)
    query_overlap = max(
        _topic_query_overlap(text, branch_text),
        _fuzzy_token_overlap(semantic_tokens, _semantic_tokens(branch_text)) if semantic_tokens else 0.0,
    )
    standalone_prefix = bool(re.match(
        r"\s*(?:что\s+такое|кто\s+такой|кто\s+такая|расскажи\s+о|объясни|"
        r"сколько(?:\s+будет)?|какая\s+погода|what\s+is|who\s+is|"
        r"tell\s+me\s+about|how\s+much|calculate)\b",
        low,
    ))
    standalone_question_shape = bool(
        "?" in text or "？" in text or standalone_prefix
    )
    # A standalone factual question may contain only one semantic noun after
    # stop-word removal (“Расскажи о фотосинтезе?”). Do not treat it as a short
    # game answer merely because the active game is waiting for a reply.
    enough_independent_content = bool(
        len(semantic_tokens) >= 2
        or (standalone_prefix and bool(q_subjects))
    )
    independent_question = bool(
        enough_independent_content
        and standalone_question_shape
        and (independent_subject_conflict or query_overlap < 0.12)
        and (not has_reference or independent_subject_conflict)
        and not (has_operation and re.search(r"(?:добав\w*|исправ\w*|передел\w*|продолж\w*|допиш\w*|перепиш\w*|улучш\w*)", low))
    )
    if independent_question:
        return False, "self_contained_independent_question"
    # Do not match a broad assistant-side cue such as “твой ход” inside a factual
    # question. Only a bare choice or an actual user selection statement is decisive.
    if pending_user_input and (
        _CHOICE_REPLY_RE.search(low)
        or len(tokens) <= 5 and re.search(
            r"(?:не\s+зна\w*|сдаюсь|сдаюс|не\s+получ\w*|не\s+могу\s+выбрат\w*|"
            r"i\s+don't\s+know|i\s+give\s+up|not\s+sure)", low
        )
    ):
        return True, "reply_to_pending_user_input"
    # An interactive scene is a live state machine: first-person actions are moves,
    # not unrelated entities, even when morphology prevents lexical overlap. This
    # check follows the independent-question guard so “why did someone open a door?”
    # cannot hijack a running scene.
    if _text(branch.get("kind")) == "interactive_game" and len(tokens) <= 12 and _INTERACTIVE_ACTION_RE.search(low) and not standalone_question_shape:
        return True, "interactive_task_action"
    # A newly supplied image/file can be the source material for the current task
    # (e.g. edit this picture, fix this file). It should not disable hot-branch
    # matching by itself; however, an unreferenced attachment must not hijack the
    # previous task merely because one exists.
    if has_attachment and not (
        reference_followup or has_reference or has_operation
        or _ACTIVE_CHOICE_RE.search(low) or is_choice
    ):
        return False, "unreferenced_new_attachment"
    if has_operation and (has_reference or len(tokens) <= 8):
        return True, "operation_on_active_work_branch"
    if subject_conflict and not has_reference and len(semantic_tokens) >= 5:
        return False, "clear_subject_switch"
    if query_overlap >= 0.16:
        return True, "active_work_topic_alignment"
    if len(tokens) <= 5 and (reference_followup or branch.get("expects_choice")):
        return True, "underspecified_reply_to_active_task"
    return False, "no_active_work_match"


def build_active_work_branch_record(
    *,
    user_text: str,
    april_text: str,
    summary: str = "",
    topic: str = "",
    message_id: str = "",
    dialog_id: str = "",
    conversation_id: str = "",
    relation: str = "NEW",
    inherited_branch: dict[str, Any] | None = None,
    intent: dict[str, Any] | None = None,
    requested_outputs: list[Any] | None = None,
    render_blocks: list[Any] | None = None,
    artifacts: list[Any] | None = None,
) -> dict[str, Any]:
    """Persist the hot-work marker alongside the existing USER↔APRIL pair."""
    inherited = dict(inherited_branch or {}) if isinstance(inherited_branch, dict) else {}
    relation_value = _text(relation).upper()
    answer_low = _text(april_text).lower().replace("ё", "е")
    expects_choice = _assistant_expects_user_input(answer_low)
    def _step_record(step_message_id: str, step_user: str, step_april: str, step_topic: str = "") -> dict[str, str]:
        return {
            "message_id": _text(step_message_id)[:120],
            "user_text": _text(step_user)[:900],
            "april_text": _text(step_april)[:1800],
            "topic": _text(step_topic)[:180],
        }

    if relation_value == "CONTINUE" and inherited.get("active"):
        record = dict(inherited)
        # Keep only durable state in PostgreSQL. Matching status belongs to the
        # current request and must be recomputed on every incoming turn.
        record.pop("matched_this_turn", None)
        record.pop("match_reason", None)
        record.pop("candidate_message_id", None)
        prior_steps = inherited.get("recent_steps")
        if not isinstance(prior_steps, list):
            prior_steps = []
        recent_steps = [
            _step_record(
                _text(item.get("message_id")), _text(item.get("user_text")),
                _text(item.get("april_text")), _text(item.get("topic")),
            )
            for item in prior_steps if isinstance(item, dict)
        ]
        current_step = _step_record(message_id, user_text, april_text, topic)
        if current_step["message_id"] and not any(
            item.get("message_id") == current_step["message_id"] for item in recent_steps
        ):
            recent_steps.append(current_step)
        record.update({
            "active": True,
            "priority": "HOT_TASK_FIRST",
            "last_action": _text(user_text)[:240],
            "state_summary": _text(summary or april_text)[:800],
            "expects_choice": bool(
                expects_choice
                or (_text(inherited.get("kind")) == "interactive_game" and _is_single_scalar_reply(april_text))
            ),
            "last_user_text": _text(user_text)[:500],
            "last_assistant_answer": _text(april_text)[:900],
            "source_message_id": _text(inherited.get("source_message_id") or inherited.get("origin_message_id") or message_id)[:120],
            "origin_message_id": _text(inherited.get("origin_message_id") or inherited.get("source_message_id") or message_id)[:120],
            "last_message_id": _text(message_id)[:120],
            "recent_steps": recent_steps[-3:],
            "dialog_id": _text(dialog_id or inherited.get("dialog_id"))[:120],
            "conversation_id": _text(conversation_id or inherited.get("conversation_id"))[:120],
        })
        return record

    fake_row = {
        "user_text": _text(user_text),
        "april_text": _text(april_text),
        "memory_summary": _text(summary),
        "message_id": _text(message_id),
        "dialog_id": _text(dialog_id),
        "conversation_id": _text(conversation_id),
        "structured_request": {
            "intent": intent if isinstance(intent, dict) else {},
            "requested_outputs": list(requested_outputs or []),
        },
        "structured_response": {
            "summary": _text(summary),
            "dialogue_memory_record": {"topic": _text(topic), "summary": _text(summary)},
            "render_blocks": list(render_blocks or []),
            "artifacts": list(artifacts or []),
        },
    }
    inferred = _infer_active_work_branch(fake_row)
    if not inferred:
        return {}
    inferred.update({
        "active": True,
        "priority": "HOT_TASK_FIRST",
        "work_id": "work:" + (_text(message_id)[:120] or uuid.uuid4().hex[:12]),
        "origin_message_id": _text(message_id)[:120],
        "source_message_id": _text(message_id)[:120],
        "last_message_id": _text(message_id)[:120],
        "dialog_id": _text(dialog_id)[:120],
        "conversation_id": _text(conversation_id)[:120],
        "last_action": _text(user_text)[:240],
        "state_summary": _text(summary or april_text)[:800],
        "expects_choice": bool(
            expects_choice or inferred.get("expects_choice")
            or (_text(inferred.get("kind")) == "interactive_game" and _is_single_scalar_reply(april_text))
        ),
        "last_user_text": _text(user_text)[:500],
        "last_assistant_answer": _text(april_text)[:900],
        # A compact rolling trace preserves the most recent user/assistant steps
        # alongside the immutable origin row. The full root is still restored from
        # dialogue_memory by origin_message_id; this is not a second task database.
        "recent_steps": [_step_record(message_id, user_text, april_text, topic)],
    })
    return inferred


def _has_semantic_active_branch_intent(
    interpretation: dict[str, Any] | None,
    *,
    history_request: bool,
    new_topic_request: bool,
    has_attachment: bool,
    reference_followup: bool,
) -> bool:
    """Trust explicit upstream continuation semantics over a later lexical veto.

    This does not force every NEW into CONTINUE. History lookups, explicit topic
    switches, and unrelated new attachments retain their existing precedence.
    """
    if history_request or new_topic_request:
        return False
    if has_attachment and not reference_followup:
        return False
    profile = interpretation if isinstance(interpretation, dict) else {}
    intent = _text(profile.get("primary_intent")).upper()
    direction = _text(profile.get("direction")).upper()
    topic_reference = _text(profile.get("topic_reference")).upper()
    relation_hint = _text(profile.get("relation_hint")).upper()
    requires_memory = bool(profile.get("requires_memory"))
    parent_context_dependency = bool(profile.get("parent_context_dependency"))
    explicit_active_topic_reference = bool(
        intent == "TOPIC_CONTINUATION"
        and (
            requires_memory
            or relation_hint == "CONTINUE"
            or direction in {"RESUME_OR_RETRIEVE_ACTIVE_TOPIC", "SEARCH_ACTIVE_OR_REFERENCED_TOPIC"}
            or topic_reference in {"PREVIOUS_OR_ACTIVE_TOPIC", "PREVIOUS_ASSISTANT_ANSWER", "TOPIC_FRAGMENT"}
        )
    )
    operation_on_active_branch = bool(
        parent_context_dependency and (requires_memory or relation_hint == "CONTINUE")
    )
    return bool(explicit_active_topic_reference or operation_on_active_branch)


def _hot_branch_followup_candidate(
    query: str,
    interpretation: dict[str, Any] | None,
    latest_row: dict[str, Any] | None,
    *,
    query_subjects: set[str] | None = None,
    reference_followup: bool = False,
    marker: bool = False,
    conversation_id: str = "",
    has_attachment: bool = False,
    history_request: bool = False,
    new_topic_request: bool = False,
) -> bool:
    """Conservatively test whether an underspecified turn may continue the hot branch.

    This is an advisory gate, not a word-trigger or a persistent anchor. It uses
    the existing interpretation metadata, topical evidence and recency of the
    authenticated active dialogue. A clear new request, history lookup, attachment
    task or a message with its own output/data specification bypasses this check.
    """
    text = _text(query)
    if not text or not isinstance(latest_row, dict):
        return False
    if history_request or new_topic_request or has_attachment:
        return False

    profile = interpretation if isinstance(interpretation, dict) else {}
    signature = profile.get("context_signature") if isinstance(profile.get("context_signature"), dict) else {}
    features = profile.get("features") if isinstance(profile.get("features"), dict) else {}
    subjects = set(query_subjects or _subject_tokens(text))
    tokens = _tokens(text)
    output_forms = signature.get("output_forms") if isinstance(signature.get("output_forms"), list) else []
    numeric_anchors = signature.get("numeric_anchors") if isinstance(signature.get("numeric_anchors"), list) else []
    has_question = bool(features.get("interrogative")) or "?" in text or "？" in text

    # Respect an upstream semantic/pragmatic classification when one is supplied;
    # older callers do not provide these optional fields, so the rest stays safe.
    pragmatic_value = " ".join(_text(profile.get(key)) for key in (
        "speech_act", "communicative_act", "pragmatic_intent", "message_function",
    )).lower().replace("ё", "е")
    pragmatic_followup = any(term in pragmatic_value for term in (
        "reaction", "acknowledg", "agreement", "disagreement", "negation",
        "emotion", "evaluation", "referential", "ellipsis", "continuation",
        "gratitude", "appreciation", "positive", "frustration", "dissatisfaction",
        "revision", "correction", "revise_previous", "respond_to_disagreement",
        "реакц", "подтвержд", "несоглас", "отрицан", "эмоц", "оценк",
        "благодар", "признатель", "раздраж", "недоволь", "передел", "исправ",
        "отсылк", "эллипсис", "продолж",
    ))

    # A short fragment with no requested output, data or self-contained question
    # is only a *candidate* for the active branch, not proof of continuation.
    # More than one independent subject usually signals a separately named topic.
    structurally_underspecified = (
        len(tokens) <= 5
        and len(subjects) <= 1
        and not output_forms
        and not numeric_anchors
        and not has_question
    )
    if not (reference_followup or marker or pragmatic_followup or structurally_underspecified):
        return False

    # Direct semantic/referential evidence is stronger than recency. Reuse the same
    # scoring vocabulary as the normal search instead of introducing phrase triggers.
    scoring_row = dict(latest_row)
    scoring_row.setdefault("user_text", _text(latest_row.get("user")))
    scoring_row.setdefault("user_text_en", _text(latest_row.get("user_en")))
    scoring_row.setdefault("april_text", _text(latest_row.get("april")))
    scoring_row.setdefault("april_text_en", _text(latest_row.get("april_en")))
    candidate = _candidate_score(
        text, scoring_row,
        dialog_id=_text(latest_row.get("dialog_id")),
        conversation_id=conversation_id,
        reference_followup=reference_followup,
    )
    semantic_fit = max(
        float(candidate.get("context") or 0),
        float(candidate.get("entity_overlap") or 0),
        float(candidate.get("answer_overlap") or 0),
        float(candidate.get("user_overlap") or 0),
        float(candidate.get("subject_overlap") or 0),
    )
    if reference_followup or marker or pragmatic_followup:
        return not bool(candidate.get("subject_mismatch")) and (semantic_fit > 0.0 or structurally_underspecified)
    if not structurally_underspecified:
        return False

    # Recency is a soft fallback for a human reaction/fragment immediately after an
    # exchange. It decays quickly so a later standalone phrase cannot stay attached
    # to a completed task merely because that task is still in the 24-hour memory.
    try:
        created_at = float(latest_row.get("created_at") or 0.0)
    except (TypeError, ValueError):
        created_at = 0.0
    age_seconds = max(0.0, time.time() - created_at) if created_at else float("inf")
    proximity = math.exp(-age_seconds / 240.0) if math.isfinite(age_seconds) else 0.0
    assistant_text = _text(
        latest_row.get("april_text") or latest_row.get("april_text_en")
        or latest_row.get("april") or latest_row.get("april_en")
    )
    open_question = "?" in assistant_text or "？" in assistant_text
    # An unanswered assistant question is a strong discourse link even after a pause.
    if open_question and len(tokens) <= 8:
        return True
    return semantic_fit >= 0.18 or proximity >= 0.58


def _continuation_marker(query: str) -> bool:
    low = _text(query).lower().replace("ё", "е")
    if not low:
        return False
    return any(
        low == marker.replace("ё", "е") or low.startswith(marker.replace("ё", "е") + " ")
        or f" {marker.replace('ё', 'е')} " in f" {low} "
        for marker in _CONTINUATION_MARKERS
    )


def _is_history_request(query: str) -> bool:
    low = _text(query).lower().replace("ё", "е")
    if not low:
        return False
    if any(marker.replace("ё", "е") in low for marker in _HISTORY_MARKERS):
        return True
    # Keep direct/legacy callers on the same intent logic as Exkrutor. The import
    # is lazy to avoid changing module initialization order.
    try:
        from blocks.Premium_interpretation_identity import interpret_request_semantics
        return bool(interpret_request_semantics(query).get("history_request"))
    except Exception:
        return False


def _history_topic_limit(query: str, default: int = 10) -> int:
    """Use the requested upper bound; “from 5 to 10 topics” means up to ten."""
    _, maximum = extract_topic_count_bounds(query, default=default)
    return max(1, min(10, int(maximum or default)))


def _history_topic_minimum(query: str, default: int = 5) -> int:
    minimum, _ = extract_topic_count_bounds(query, default=10)
    return max(1, min(10, int(minimum or default)))


def _domain_terms(text: str) -> set[str]:
    low = str(text or "").lower().replace("ё", "е")
    groups = {
        "code": {"code", "python", "javascript", "bug", "api", "railway", "github", "код", "ошибка"},
        "image": {"image", "picture", "photo", "screenshot", "рисунок", "картинка", "скриншот", "фото"},
        "math": {"math", "formula", "equation", "graph", "таблица", "формула", "график", "математика", "теорема"},
        "web": {"web", "link", "url", "site", "сайт", "ссылка"},
        "file": {"file", "document", "pdf", "файл", "документ"},
        "voice": {"voice", "audio", "голос", "аудио"},
    }
    result: set[str] = set()
    for domain, terms in groups.items():
        if any(term in low for term in terms):
            result.add(domain)
    return result


def _looks_like_referential_followup(query: str) -> bool:
    low = _text(query).lower().replace("ё", "е")
    if not low:
        return False

    phrase_markers = (
        "с кем", "с ним", "с ней", "с ними", "у него", "у нее", "у неe",
        "у неё", "его", "ее", "её", "него", "нее", "неё", "ним", "ней",
        "про него", "про нее", "про неё", "про них",
        "что потом", "что дальше", "а дальше", "и дальше", "подробнее",
        "расскажи больше", "продолжи", "продолжай", "что насчёт", "что насчет",
        "а дальше", "а что еще", "а что ещё", "что потом",
        "как он", "как она", "что он", "что она", "где он", "где она",
        "кто был", "что с ним", "что с ней",
        "что еще", "что ещё", "а что еще", "а что ещё",
        # Explicit references to a previously supplied asset, even when the
        # current turn contains no new file/image bytes.
        "в этом файле", "в данном файле", "в прикрепленном файле",
        "в прикреплённом файле", "в файле который я прислал",
        "в файле, который я прислал", "на этой картинке", "на картинке",
        "на этом фото", "на этой фотографии", "на изображении",
        "тот файл", "этот файл", "тот код", "этот код", "тот скриншот",
        "эту картинку", "эту фотографию", "картинку, которую я прислал",
        "файл, который я присылал", "изображение, которое я прислал",
        "какого цвета", "какой цвет", "какая порода", "какой породы",
        "какого вида", "какого размера", "какой окрас", "какого окраса",
        "предыдущее фото", "предыдущим фото", "предыдущую картинку", "предыдущей картинке",
        "предыдущий файл", "предыдущий код", "прошлое фото", "прошлый файл",
        "сравни с", "сравни это", "сравни с предыдущ", "сравни с прошлым",
        "вернись к картинке", "вернись к фото", "вернись к файлу",
        "проверь еще раз", "проверь ещё раз", "перепроверь", "посмотри еще раз",
        "посмотри ещё раз", "я же скидывал картинку", "я скидывал фото",
    )
    # Match single words as tokens, not substrings inside unrelated words. The
    # previous substring test treated fragments such as "та", "ей" or "него"
    # inside ordinary nouns as a dialogue reference and forced CONTINUE.
    for marker in phrase_markers:
        marker = marker.replace("ё", "е").strip()
        if not marker:
            continue
        if re.search(r"\s", marker):
            if marker in low:
                return True
        elif re.search(rf"(?<![\w\u0080-\uffff]){re.escape(marker)}(?![\w\u0080-\uffff])", low):
            return True

    tokens = _tokens(low)
    reference_tokens = {
        "он", "она", "оно", "они", "его", "ее", "её", "их", "ему", "ей", "им",
        "ним", "ней", "него", "нее", "неё", "них", "это", "тот", "та", "ту", "эта",
        "этот", "эту", "этого", "этой", "этом", "эти", "этих", "так", "данный", "данная",
        "this", "that", "these", "those", "it", "he", "she", "they", "him", "her", "them",
    }
    if len(tokens) <= 12 and bool(tokens & reference_tokens):
        return True
    # Subjectless short questions are ellipses when the object is recoverable from the active turn.
    question_words = {"кто", "что", "чем", "чего", "какой", "какая", "какие", "где", "когда", "почему", "зачем", "как", "who", "what", "where", "when", "why", "how"}
    if len(tokens) <= 5 and bool(tokens & question_words) and not _subject_tokens(low):
        return True
    return False


def _looks_like_asset_reference(query: str) -> bool:
    """Detect an explicit mention of a prior image/file/code artifact.

    Such requests must anchor to the best matching asset turn, not blindly to
    the immediately preceding unrelated turn.
    """
    low = _text(query).lower().replace("ё", "е")
    markers = (
        "фото", "картинк", "изображен", "скриншот", "файл", "код", "скрипт",
        "photo", "picture", "image", "screenshot", "file", "code", "script",
        "предыдущ", "прошл", "сравни", "вернись к",
    )
    return any(marker in low for marker in markers)


def _looks_like_new_topic(query: str) -> bool:
    low = _text(query).lower().replace("ё", "е")
    return any(marker.replace("ё", "е") in low for marker in _NEW_TOPIC_MARKERS)


def _concept_overlap(query_tokens: set[str], candidate_tokens: set[str]) -> float:
    if not query_tokens:
        return 0.0
    matched = 0
    for q in query_tokens:
        if q in candidate_tokens:
            matched += 1
            continue
        if len(q) >= 5 and any(
            len(c) >= 5 and (q[:5] == c[:5] or q.startswith(c[:6]) or c.startswith(q[:6]))
            for c in candidate_tokens
        ):
            matched += 1
    return matched / max(1, len(query_tokens))



def _explicit_entity_overlap(query: str, row: dict[str, Any]) -> float:
    """Measure overlap of meaningful subject terms, excluding pronouns and fillers."""
    q = _semantic_tokens(query)
    candidate = _semantic_tokens(
        " ".join(
            _text(row.get(name))
            for name in ("user_text", "april_text", "user_text_en", "april_text_en")
        )
    )
    return _concept_overlap(q, candidate)


def _parse_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}



def _is_failed_provider_row(row: dict[str, Any]) -> bool:
    """A timeout/error bubble is not a completed assistant answer for continuity."""
    response = _parse_json(row.get("structured_response"))
    metadata = response.get("metadata") if isinstance(response.get("metadata"), dict) else {}
    if metadata.get("provider_fallback") or metadata.get("provider_error_code"):
        return True

    # Exclude legacy fallback turns created before provider_fallback metadata
    # was persisted. Keep the rows in storage, but never use them as dialogue facts.
    answer = _text(row.get("april_text") or row.get("april_text_en")).strip().lower()
    legacy_failure_markers = (
        "модель не вернула завершённый ответ за один запрос",
        "модель не вернула завершенный ответ за один запрос",
        "не удалось завершить ответ модели за один запрос",
        "не удалось завершить ответ модели в этом запросе",
        "the model did not return a complete response in one provider call",
        "the model could not complete this response in one provider call",
        "модель не повернула завершеної відповіді за один запит",
        "не вдалося завершити відповідь моделі в цьому запиті",
    )
    return any(answer.startswith(marker) for marker in legacy_failure_markers)


def _row_modalities(row: dict[str, Any]) -> set[str]:
    """Recover persisted input modalities without storing a second memory copy."""
    result: set[str] = set()
    structured = _parse_json(row.get("structured_request"))
    if not structured:
        return result
    interpretation = structured.get("intent") if isinstance(structured.get("intent"), dict) else {}
    input_data = interpretation.get("input") if isinstance(interpretation, dict) else {}
    if isinstance(input_data, dict):
        for modality in input_data.get("modalities") or []:
            if str(modality):
                result.add(str(modality).lower())
        if input_data.get("has_image"):
            result.add("image")
        if input_data.get("has_file"):
            result.add("file")
        if input_data.get("has_voice"):
            result.add("voice")
    for item in structured.get("attachments") or []:
        if isinstance(item, dict):
            kind = _text(item.get("kind") or item.get("source_type")).lower()
            if kind:
                result.add("text_file" if kind == "text_file" else kind)
    visual = structured.get("visual_context")
    if isinstance(visual, dict) and visual.get("has_input_images"):
        result.add("image")
    if structured.get("file_contents"):
        result.add("file")
    attachment_index = structured.get("attachment_index")
    if isinstance(attachment_index, list):
        for item in attachment_index:
            if isinstance(item, dict):
                kind = _text(item.get("kind")).lower()
                if kind in {"file", "text_file"}:
                    result.add("file")
                elif kind == "image":
                    result.add("image")
    return result


def _topic_label(row: dict[str, Any]) -> str:
    structured = _parse_json(row.get("structured_request"))
    dialogue = structured.get("dialogue") if isinstance(structured.get("dialogue"), dict) else {}
    cont = dialogue.get("continuation_context") if isinstance(dialogue.get("continuation_context"), dict) else {}
    response = _parse_json(row.get("structured_response"))
    response_meta = response.get("metadata") if isinstance(response.get("metadata"), dict) else {}
    memory_record = response.get("dialogue_memory_record") or response_meta.get("dialogue_memory_record") or {}
    if not isinstance(memory_record, dict):
        memory_record = {}
    attachment_index = structured.get("attachment_index") if isinstance(structured.get("attachment_index"), list) else []
    first_attachment = next((x for x in attachment_index if isinstance(x, dict)), {})
    for value in (
        memory_record.get("topic"),
        (f"Файл {first_attachment.get('filename')}: {first_attachment.get('summary') or first_attachment.get('content_preview', '')[:90]}" if first_attachment.get("filename") else ""),
        cont.get("active_topic"),
        structured.get("request_structure", {}).get("user_goal") if isinstance(structured.get("request_structure"), dict) else "",
        row.get("user_text"),
        row.get("user_text_en"),
    ):
        value = _text(value)
        if value:
            return re.sub(r"\s+", " ", value)[:140]
    return "Безымянная тема"


def _topic_tokens(label: str) -> set[str]:
    return _semantic_tokens(label)


def _merge_compact_summaries(existing: Any, incoming: Any, limit: int = 640) -> str:
    """Accumulate distinct grounded summary fragments instead of replacing history with the last turn."""
    old = re.sub(r"\s+", " ", _text(existing)).strip()
    new = re.sub(r"\s+", " ", _text(incoming)).strip()
    if not old:
        return new[:limit]
    if not new or new.casefold() in old.casefold():
        return old[:limit]
    if old.casefold() in new.casefold():
        return new[:limit]
    # Split on sentence boundaries where possible; preserve chronology and avoid repeats.
    fragments: list[str] = []
    for source in (old, new):
        for part in re.split(r"(?<=[.!?])\s+|\s*\|\s*", source):
            part = part.strip(" ;,.")
            if part and not any(part.casefold() == prior.casefold() for prior in fragments):
                fragments.append(part)
    result = "; ".join(fragments)
    return result[:limit].rstrip(" ;,")


def _build_topic_index(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build a 24-hour topic/section index from the canonical persisted pairs.

    The index is derived from the existing PostgreSQL dialogue rows; it is not a
    second memory store. Each section keeps its short McDowell summary and the
    exact message that owns that summary, so later turns can retrieve one section.
    """
    if not rows:
        return []

    ordered = sorted(
        [row for row in rows if isinstance(row, dict) and not _row_is_pending_clarification(row)],
        key=lambda row: (float(row.get("created_at") or 0), int(row.get("turn_index") or 0)),
    )
    groups: list[dict[str, Any]] = []

    def merge_sections(existing: list[dict[str, Any]], incoming: list[dict[str, Any]], message_id: str) -> list[dict[str, Any]]:
        merged = [dict(section) for section in existing if isinstance(section, dict)]
        positions = {re.sub(r"\s+", " ", _text(x.get("heading")).casefold()): i for i, x in enumerate(merged)}
        for section in incoming:
            if not isinstance(section, dict):
                continue
            heading = _text(section.get("heading"))[:180]
            if not heading:
                continue
            key = re.sub(r"\s+", " ", heading.casefold())
            item = {
                "heading": heading,
                "summary": re.sub(r"\s+", " ", _text(section.get("summary")))[:360],
                "order": int(section.get("order") or len(merged) + 1),
                "message_id": _text(section.get("message_id") or message_id),
            }
            for hierarchy_key in ("section_id", "parent_id", "parent_heading", "parent_section_id"):
                if _text(section.get(hierarchy_key)):
                    item[hierarchy_key] = _text(section.get(hierarchy_key))[:180]
            if key in positions:
                # Keep a stable section identity and accumulate new information;
                # do not erase useful details merely because the last answer was short.
                pos = positions[key]
                previous = merged[pos]
                item["order"] = previous.get("order") or item["order"]
                item["summary"] = _merge_compact_summaries(previous.get("summary"), item.get("summary"), 480)
                for hierarchy_key in ("section_id", "parent_id", "parent_heading", "parent_section_id"):
                    if not item.get(hierarchy_key) and previous.get(hierarchy_key):
                        item[hierarchy_key] = previous[hierarchy_key]
                merged[pos] = item
            else:
                positions[key] = len(merged)
                merged.append(item)
        return sorted(merged, key=lambda x: int(x.get("order") or 0))[:12]

    for row in ordered:
        label = _topic_label(row)
        tokens = _topic_tokens(label)
        relation = _text(row.get("relation") or "NEW").upper()
        same_as_prev = False
        if groups:
            prev = groups[-1]
            similarity = fuzz.token_set_ratio(label.lower(), str(prev.get("topic") or "").lower()) / 100.0
            current_modalities = _row_modalities(row)
            previous_modalities = set(prev.get("modalities") or [])
            modality_changed = bool(current_modalities and previous_modalities and current_modalities.isdisjoint(previous_modalities))
            current_subjects = _row_subject_tokens(row)
            previous_subjects = set(prev.get("subject_terms") or [])
            subject_conflict = _subject_conflicts(current_subjects, previous_subjects)
            same_as_prev = relation != "NEW" and similarity >= 0.28 and not modality_changed and not subject_conflict
            if (not same_as_prev and not modality_changed and not subject_conflict
                    and _looks_like_referential_followup(str(row.get("user_text") or ""))):
                same_as_prev = True

        row_sections = _dialogue_section_map(row)
        if not groups or not same_as_prev:
            groups.append({
                "topic": label,
                "topic_tokens": sorted(tokens),
                "subject_terms": sorted(_row_subject_tokens(row)),
                "start_turn": int(row.get("turn_index") or 0),
                "end_turn": int(row.get("turn_index") or 0),
                "first_at": float(row.get("created_at") or 0),
                "last_at": float(row.get("created_at") or 0),
                "last_question": _text(row.get("user_text"))[:360],
                "message_id": _text(row.get("message_id")),
                "origin_message_id": _text(row.get("message_id")),
                "origin_turn": int(row.get("turn_index") or 0),
                "message_ids": [_text(row.get("message_id"))] if _text(row.get("message_id")) else [],
                "dialog_id": _text(row.get("dialog_id")),
                "conversation_id": _text(row.get("conversation_id")),
                "modalities": sorted(_row_modalities(row)),
                "pair_count": 1,
                "summary": _compact_memory_summary(row),
                "sections": merge_sections([], row_sections, _text(row.get("message_id"))),
            })
        else:
            group = groups[-1]
            group["end_turn"] = int(row.get("turn_index") or group["end_turn"])
            group["last_at"] = float(row.get("created_at") or group["last_at"])
            group["last_question"] = _text(row.get("user_text"))[:360] or group["last_question"]
            group["modalities"] = sorted(set(group.get("modalities") or []) | _row_modalities(row))
            group["pair_count"] = int(group.get("pair_count") or 0) + 1
            group["message_id"] = _text(row.get("message_id")) or group.get("message_id")
            row_message_id = _text(row.get("message_id"))
            if row_message_id and row_message_id not in (group.get("message_ids") or []):
                group.setdefault("message_ids", []).append(row_message_id)
            group["summary"] = _merge_compact_summaries(group.get("summary"), _compact_memory_summary(row), 640)
            group["sections"] = merge_sections(group.get("sections") or [], row_sections, _text(row.get("message_id")))

    deduped: list[dict[str, Any]] = []
    for item in groups:
        found = None
        for prev in reversed(deduped[-3:]):
            similarity = fuzz.token_set_ratio(str(item.get("topic") or "").lower(), str(prev.get("topic") or "").lower()) / 100.0
            subject_conflict = _subject_conflicts(set(item.get("subject_terms") or []), set(prev.get("subject_terms") or []))
            if similarity >= 0.78 and not subject_conflict:
                found = prev
                break
        if found is not None:
            if float(item.get("last_at") or 0) >= float(found.get("last_at") or 0):
                found.update({
                    "end_turn": item.get("end_turn"), "last_at": item.get("last_at"),
                    "last_question": item.get("last_question"), "message_id": item.get("message_id"),
                    "summary": _merge_compact_summaries(found.get("summary"), item.get("summary"), 640),
                    "subject_terms": sorted(set(found.get("subject_terms") or []) | set(item.get("subject_terms") or [])),
                    "sections": merge_sections(found.get("sections") or [], item.get("sections") or [], _text(item.get("message_id"))),
                    "pair_count": int(found.get("pair_count") or 0) + int(item.get("pair_count") or 0),
                    "message_ids": list(dict.fromkeys((found.get("message_ids") or []) + (item.get("message_ids") or []))),
                })
        else:
            deduped.append(item)

    deduped.sort(key=lambda item: float(item.get("last_at") or 0), reverse=True)
    visible = []
    for idx, item in enumerate(deduped[:30], 1):
        origin_message_id = _text(item.get("origin_message_id") or item.get("message_id"))
        topic_id_seed = f"{origin_message_id}|{_text(item.get('topic')).casefold()}|{item.get('first_at', 0)}"
        topic_id = "topic-" + hashlib.sha256(topic_id_seed.encode("utf-8")).hexdigest()[:16]
        sections = []
        for section in (item.get("sections") or [])[:10]:
            if not isinstance(section, dict):
                continue
            normalized_section = dict(section)
            normalized_section["topic_id"] = topic_id
            normalized_section["topic_origin_message_id"] = origin_message_id
            normalized_section["source_message_id"] = _text(section.get("message_id"))
            sections.append(normalized_section)
        visible.append({
            "number": idx,
            "topic_id": topic_id,
            "topic": _text(item.get("topic"))[:240],
            "summary": _text(item.get("summary"))[:440],
            "sections": sections,
            "turns": f"{item.get('start_turn', 0)}-{item.get('end_turn', 0)}",
            "last_question": _text(item.get("last_question"))[:280],
            "pair_count": int(item.get("pair_count") or 0),
            "first_at": item.get("first_at"),
            "last_at": item.get("last_at"),
            "origin_message_id": origin_message_id,
            "origin_turn": int(item.get("origin_turn") or item.get("start_turn") or 0),
            "message_ids": list(dict.fromkeys(_text(x) for x in (item.get("message_ids") or []) if _text(x)))[:40],
            "message_id": _text(item.get("message_id")),
            "dialog_id": _text(item.get("dialog_id")),
            "conversation_id": _text(item.get("conversation_id")),
        })
    return visible

def _row_attachment_evidence(row: dict[str, Any]) -> str:
    """Compact, searchable evidence retained with a USER↔APRIL pair.

    Original binary payloads are not persisted in a sidecar table. This index
    retrieves bounded filenames, source snippets and Provider-grounded summaries
    stored inside dialogue_memory's structured request/response fields.
    """
    req = _parse_json(row.get("structured_request"))
    resp = _parse_json(row.get("structured_response"))
    chunks: list[str] = []
    index = req.get("attachment_index")
    if isinstance(index, list):
        for item in index[:6]:
            if not isinstance(item, dict):
                continue
            chunks.extend([
                _text(item.get("filename")), _text(item.get("kind")),
                _text(item.get("mime_type")), _text(item.get("content_preview"))[:7000],
                _text(item.get("summary"))[:1600],
            ])
    for item in req.get("attachments") or []:
        if isinstance(item, dict):
            chunks.extend([_text(item.get("filename")), _text(item.get("kind")), _text(item.get("source_type"))])
    record = resp.get("dialogue_memory_record")
    if not isinstance(record, dict):
        metadata = resp.get("metadata") if isinstance(resp.get("metadata"), dict) else {}
        record = metadata.get("dialogue_memory_record") if isinstance(metadata.get("dialogue_memory_record"), dict) else {}
    chunks.extend([_text(record.get("topic")), _text(record.get("summary"))[:2800]])
    # Include a bounded excerpt of the exact code/document output generated by
    # April. This makes later requests about a function/symbol retrieve the pair
    # that owns the output asset, without putting raw binary into JSONB.
    for block in resp.get("render_blocks") or []:
        if not isinstance(block, dict) or _text(block.get("type")).lower() != "code":
            continue
        chunks.extend([_text(block.get("filename")), _text(block.get("language")), _text(block.get("code") or block.get("content"))[:7000]])
    asset_refs = resp.get("asset_refs") if isinstance(resp.get("asset_refs"), dict) else {}
    for item in asset_refs.get("april_outputs") or []:
        if isinstance(item, dict):
            chunks.extend([_text(item.get("filename")), _text(item.get("output_type")), _text(item.get("language"))])
    for key in ("entities", "visual_observations", "code_symbols", "file_purpose"):
        value = record.get(key)
        if isinstance(value, list):
            chunks.extend(_text(part)[:800] for part in value[:12])
        elif value:
            chunks.append(_text(value)[:1800])
    return " ".join(part for part in chunks if part)[:18000]



# Exact structured values preserved separately from compressible dialogue prose.
_PROTECTED_STRUCTURED_TYPE_ALIASES = {
    "graph": "graph", "graph_data": "graph", "chart": "graph", "plot": "graph",
    "table": "table", "table_data": "table",
    "formula": "formula", "formula_data": "formula", "equation": "formula",
    "math": "formula", "latex": "formula", "physics_formula": "formula",
    "chemistry_formula": "formula", "biology_formula": "formula",
    "solution": "solution", "math_solution": "solution", "problem_solution": "solution",
    "worked_solution": "solution", "solution_steps": "solution",
}

_PROTECTED_DATA_KEYS = {
    "graph": {
        "points", "data_points", "series", "datasets", "traces", "x_values", "y_values",
        "x_axis", "y_axis", "labels", "categories",
    },
    "table": {"rows", "columns", "headers", "matrix", "cell_roles", "cells", "row_labels", "column_labels"},
    "formula": {"latex", "latex_formulas", "formula", "formulas", "equation", "equations", "expression", "expressions"},
    "solution": {
        "solution_steps", "derivation", "calculations", "given_values", "known_values",
        "unknowns", "variables", "parameters", "result",
    },
}


def _protected_structured_kind(value: Any) -> str:
    """Classify data from renderer/schema metadata, never from user wording."""
    if not isinstance(value, dict):
        return ""
    tags = []
    for key in ("type", "artifact_type", "representation", "payload_type", "kind", "output_type"):
        tag = _text(value.get(key)).lower().replace("-", "_").replace(" ", "_")
        if tag:
            tags.append(tag)

    renderer_map = {
        "graphblock": "graph", "graphrenderer": "graph",
        "tableblock": "table", "tablerenderer": "table",
        "formularenderer": "formula", "formulablock": "formula",
        "mathsolutionblock": "solution", "problemsolutionblock": "solution",
    }
    for key in ("renderer", "viewer"):
        renderer = _text(value.get(key)).lower().replace("_", "").replace("-", "").replace(" ", "")
        if renderer in renderer_map:
            return renderer_map[renderer]
    for tag in tags:
        if tag in _PROTECTED_STRUCTURED_TYPE_ALIASES:
            return _PROTECTED_STRUCTURED_TYPE_ALIASES[tag]

    payload = value.get("payload") if isinstance(value.get("payload"), dict) else value
    keys = {str(key).lower() for key in payload} if isinstance(payload, dict) else set()
    if keys.intersection({"rows", "columns", "headers", "matrix", "cell_roles", "cells"}):
        return "table"
    if keys.intersection({"series", "datasets", "traces", "points", "data_points", "x_values", "y_values", "x_axis", "y_axis"}):
        return "graph"
    if keys.intersection({"latex", "latex_formulas", "formula", "formulas", "equation", "equations", "expression", "expressions"}):
        return "formula"
    # Do not classify an arbitrary object with a generic `steps` field as maths.
    if keys.intersection({"solution_steps", "derivation", "calculations", "given_values", "known_values", "unknowns"}):
        return "solution"
    return ""


def _protected_node_richness(kind: str, node: dict[str, Any]) -> int:
    """Prefer the source representation that actually contains values over its UI envelope."""
    wanted = _PROTECTED_DATA_KEYS.get(kind, set())
    richness = 0
    stack: list[Any] = [node]
    depth = 0
    while stack and depth < 50000:
        current = stack.pop()
        depth += 1
        if isinstance(current, dict):
            for key, child in current.items():
                key_norm = str(key).lower()
                if key_norm in wanted:
                    richness += 10
                    if isinstance(child, (list, dict, str)):
                        richness += min(1000, len(child))
                if isinstance(child, (dict, list)):
                    stack.append(child)
        elif isinstance(current, list):
            stack.extend(current)
    return richness



def _protected_node_payload(kind: str, node: dict[str, Any]) -> dict[str, Any]:
    """Strip renderer/UI envelopes while keeping exact data, labels, units and axes."""
    category = {
        "type": kind,
        "renderer": _text(node.get("renderer") or node.get("viewer"))[:80],
    }
    for key in ("title", "name", "label", "unit", "units", "x_axis_label", "y_axis_label"):
        if node.get(key) not in (None, "", [], {}):
            category[key] = deepcopy(node[key])

    # Canonical render blocks carry the exact machine values in `payload`.
    payload = node.get("payload") if isinstance(node.get("payload"), dict) else {}
    if not payload:
        signal = node.get("render_signal") if isinstance(node.get("render_signal"), dict) else {}
        if isinstance(signal.get("payload"), dict):
            payload = signal["payload"]
    if payload and _protected_node_richness(kind, payload):
        category["payload"] = deepcopy(payload)
        return category

    # Some room artifacts store data under `spec`; retain it when it holds values.
    spec = node.get("spec") if isinstance(node.get("spec"), dict) else {}
    if spec and _protected_node_richness(kind, spec):
        category["spec"] = deepcopy(spec)
        return category

    # Legacy direct blocks place typed values at the top level. Drop renderer
    # envelopes and duplicated prose, but keep every remaining field verbatim.
    envelope_keys = {
        "render_signal", "signal", "presentation", "scene_contract",
        "provider_payload", "canonical_provider_payload", "executor_generated",
        "text_companion_required", "complexity", "layout", "priority",
        "artifact_id", "source_room", "content", "text", "answer", "summary",
        "description", "metadata", "metrics", "trace", "diagnostics",
    }
    for key, value in node.items():
        if key in envelope_keys or key in {"type", "artifact_type", "renderer", "viewer"}:
            continue
        if value not in (None, "", [], {}):
            category[key] = deepcopy(value)
    return category

def _protected_structured_data_from_row(row: dict[str, Any]) -> dict[str, Any]:
    """Extract exact typed structures and their owning answer, avoiding duplicate envelopes."""
    response = _parse_json(row.get("structured_response"))
    if not response:
        return {}

    def collect_typed_nodes(value: Any, source_field: str, path: tuple[Any, ...] = (), depth: int = 0) -> list[dict[str, Any]]:
        if depth > 12:
            return []
        found: list[dict[str, Any]] = []
        if isinstance(value, list):
            for index, child in enumerate(value):
                found.extend(collect_typed_nodes(child, source_field, path + (index,), depth + 1))
            return found
        if not isinstance(value, dict):
            return found

        kind = _protected_structured_kind(value)
        if kind:
            serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
            found.append({
                "kind": kind,
                "source_field": source_field,
                "index": list(path),
                "data": deepcopy(value),
                "_fingerprint": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
                "_richness": _protected_node_richness(kind, value),
            })
            # Keep the complete typed node as one object; do not split its arrays.
            return found

        for key, child in value.items():
            if isinstance(child, (dict, list)):
                found.extend(collect_typed_nodes(child, source_field, path + (key,), depth + 1))
        return found

    field_candidates: dict[str, list[dict[str, Any]]] = {}
    for field_name in ("render_blocks", "artifacts", "scene_contract"):
        raw = response.get(field_name)
        if isinstance(raw, (dict, list)):
            field_candidates[field_name] = collect_typed_nodes(raw, field_name)

    # Renderer blocks are the primary contract. Artifacts/scene_contract are used
    # only when they contain a richer payload for a given type or that type is absent.
    field_priority = {"render_blocks": 0, "artifacts": 1, "scene_contract": 2}
    kinds = {
        item["kind"]
        for values in field_candidates.values()
        for item in values
    }
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for kind in ("graph", "table", "formula", "solution"):
        if kind not in kinds:
            continue
        candidates_by_field = {
            name: [item for item in values if item["kind"] == kind]
            for name, values in field_candidates.items()
        }
        candidates_by_field = {name: values for name, values in candidates_by_field.items() if values}
        if not candidates_by_field:
            continue

        def field_score(entry: tuple[str, list[dict[str, Any]]]) -> tuple[int, int, int]:
            name, values = entry
            return (
                sum(int(item.get("_richness") or 0) for item in values),
                len(values),
                -field_priority.get(name, 99),
            )

        best_field, best_nodes = max(candidates_by_field.items(), key=field_score)
        # Retain every distinct typed structure in the best source field, but
        # omit lower-level copies of the same renderer payload in wrapper fields.
        for item in best_nodes:
            fingerprint = f"{kind}:{item['_fingerprint']}"
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            items.append({
                "kind": kind,
                "source_field": best_field,
                "index": item["index"],
                "data": _protected_node_payload(kind, item["data"]),
            })

    if not items:
        # Older text-only responses can still be protected when the persisted
        # request schema declares a structured output; the exact answer is kept below.
        request = _parse_json(row.get("structured_request"))
        routing = request.get("routing") if isinstance(request.get("routing"), dict) else {}
        request_intent = request.get("intent") if isinstance(request.get("intent"), dict) else {}
        nested_intent = request_intent.get("intent") if isinstance(request_intent.get("intent"), dict) else {}
        declared: set[str] = set()
        output_values: list[Any] = []
        for container in (request, request_intent, nested_intent):
            for field_name in ("requested_outputs", "required_artifacts"):
                values = container.get(field_name)
                if isinstance(values, list):
                    output_values.extend(values)
        output_aliases = {
            "graph": "graph", "chart": "graph", "plot": "graph",
            "table": "table", "formula": "formula", "equation": "formula",
            "math_solution": "solution", "problem_solution": "solution",
            "worked_solution": "solution", "solution": "solution",
        }
        for output in output_values:
            normalized = _text(output).lower().replace("-", "_").replace(" ", "_")
            if normalized in output_aliases:
                declared.add(output_aliases[normalized])
        for flag, kind in (("wants_graph", "graph"), ("wants_table", "table"), ("wants_formula", "formula")):
            if bool(nested_intent.get(flag) or request_intent.get(flag)):
                declared.add(kind)
        rooms = routing.get("selected_rooms") if isinstance(routing.get("selected_rooms"), list) else []
        for room in rooms:
            if not isinstance(room, dict):
                continue
            room_id = _text(room.get("room") or room.get("room_id")).upper()
            artifact_type = _text(room.get("artifact_type")).lower()
            if room_id in {"MATHEMATICS_ROOM", "C_MATHEMATICS_ROOM"}:
                declared.add("solution")
            elif room_id in {"FORMULA_ROOM", "C_FORMULA_ROOM"} or artifact_type == "formula":
                declared.add("formula")
        for kind in ("graph", "table", "formula", "solution"):
            if kind in declared:
                items.append({
                    "kind": kind,
                    "source_field": "structured_request_schema",
                    "index": len(items),
                    "data": {"type": kind, "source_room_plan": True},
                })

    if not items:
        return {}
    payload = {
        "schema": "april_protected_structured_data_v1",
        "source_message_id": _text(row.get("message_id")),
        "items": items,
        # The answer binds values to labels/axes and preserves verbal solution steps
        # when a legacy renderer stored only a presentation envelope.
        "source_answer": str(response.get("answer") or response.get("content") or row.get("april_text") or row.get("april") or ""),
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    payload["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload



def _candidate_score(
    query: str,
    row: dict[str, Any],
    *,
    dialog_id: str = "",
    conversation_id: str = "",
    now_ts: float | None = None,
    reference_followup: bool = False,
    query_modalities: set[str] | None = None,
) -> dict[str, Any]:
    q = str(query or "").strip().lower()
    user = str(row.get("user_text") or "")
    april = str(row.get("april_text") or "")
    user_en = str(row.get("user_text_en") or "")
    april_en = str(row.get("april_text_en") or "")

    query_tokens = _semantic_tokens(q)
    user_tokens = _semantic_tokens(user)
    answer_tokens = _semantic_tokens(april)
    attachment_evidence = _row_attachment_evidence(row)
    memory_summary = _compact_memory_summary(row)
    candidate_text = " ".join(x for x in (user, user_en, april, april_en, memory_summary, attachment_evidence) if x)
    candidate_tokens = _semantic_tokens(candidate_text)

    lexical = fuzz.token_set_ratio(
        " ".join(sorted(query_tokens)),
        " ".join(sorted(candidate_tokens)),
    ) / 100.0 if query_tokens and candidate_tokens else 0.0
    overlap = _concept_overlap(query_tokens, candidate_tokens)
    partial = (
        fuzz.partial_ratio(q, candidate_text) / 100.0
        if q and overlap > 0.0 else 0.0
    )

    row_modalities = _row_modalities(row)
    requested_modalities = set(query_modalities or set())
    modality_match = (
        len(requested_modalities & row_modalities) / max(1, len(requested_modalities))
        if requested_modalities else 0.0
    )
    answer_overlap = _concept_overlap(query_tokens, answer_tokens)
    user_overlap = _concept_overlap(query_tokens, user_tokens)
    entity_overlap = _explicit_entity_overlap(query, row)
    query_subjects = _subject_tokens(query)
    row_subjects = _row_subject_tokens(row)
    subject_overlap = _subject_overlap(query_subjects, row_subjects)
    subject_mismatch = _subject_conflicts(query_subjects, row_subjects)
    numeric_anchor_overlap = _query_numeric_overlap(query, row, query_subjects)
    protected_data = _protected_structured_data_from_row(row)
    if protected_data and _text(row.get("topic_id")):
        # Preserve the exact originating message while binding the payload to the
        # topic and time range where it entered the dialogue.
        protected_data["topic_id"] = _text(row.get("topic_id"))
        protected_data["topic_origin_message_id"] = _text(row.get("topic_origin_message_id"))
        protected_data["source_message_id"] = _text(row.get("message_id"))
        protected_data["topic_origin_at"] = row.get("topic_origin_at")
    data_richness = _structured_data_richness(protected_data)
    source_data_alignment = _source_data_alignment(row, protected_data=protected_data) if data_richness else 0.0

    q_domains = _domain_terms(q)
    c_domains = _domain_terms(candidate_text)
    direction = (
        len(q_domains & c_domains) / max(1, len(q_domains))
        if q_domains else 0.0
    )

    stamp = now_ts if now_ts is not None else time.time()
    created = float(row.get("created_at") or 0.0)
    age = max(0.0, stamp - created)
    recency = max(0.0, 1.0 - age / DIALOGUE_WINDOW_SECONDS)

    row_dialog = _text(row.get("dialog_id"))
    row_conversation = _text(row.get("conversation_id"))
    exact_dialog = bool(dialog_id and row_dialog and row_dialog == dialog_id)
    exact_conversation = bool(conversation_id and row_conversation and row_conversation == conversation_id)
    same_active_context = exact_dialog or exact_conversation

    score = (
        lexical * 0.12
        + partial * 0.04
        + overlap * 0.26
        + entity_overlap * 0.20
        + answer_overlap * 0.08
        + user_overlap * 0.04
        + direction * 0.04
        + modality_match * 0.08
        + recency * 0.05
        + (0.09 if exact_dialog else (0.06 if exact_conversation else 0.0))
    )
    if reference_followup and same_active_context:
        score += 0.20
    if exact_dialog and int(row.get("turn_index") or 0) == max(
        [int(x.get("turn_index") or 0) for x in _STATES.get(_text(row.get("user_id")), {}).get("dialogue_pairs", []) if isinstance(x, dict)],
        default=int(row.get("turn_index") or 0),
    ):
        score += 0.03

    # Context consistency outranks generic lexical similarity. Explicitly disjoint
    # subjects are penalized; an aligned subject, original numeric constraint and
    # value-bearing artifact are positive provenance signals.
    if query_subjects and row_subjects:
        score += 0.07 * subject_overlap
        if subject_mismatch:
            score -= 0.30
    score += 0.22 * numeric_anchor_overlap
    # A source request whose supplied values survive into its structured output is
    # more authoritative than a newer conversion answer that merely repeats the topic.
    score += 0.12 * source_data_alignment
    if reference_followup and data_richness:
        score += min(0.08, 0.015 * data_richness)

    return {
        "score": round(max(0.0, min(1.0, float(score))), 6),
        "semantic": round(lexical, 6),
        "context": round(overlap, 6),
        "answer_overlap": round(answer_overlap, 6),
        "user_overlap": round(user_overlap, 6),
        "entity_overlap": round(entity_overlap, 6),
        "subject_terms": sorted(row_subjects)[:12],
        "subject_overlap": round(subject_overlap, 6),
        "subject_mismatch": bool(subject_mismatch),
        "participant_alignment": _participant_alignment(query, row),
        "numeric_anchor_overlap": round(numeric_anchor_overlap, 6),
        "source_data_alignment": round(source_data_alignment, 6),
        "structured_data_richness": int(data_richness),
        "modality_match": round(modality_match, 6),
        "row_modalities": sorted(row_modalities),
        "direction": round(direction, 6),
        "recency": round(recency, 6),
        # Treat a stable conversation_id as active scope when dialog_id rotates.
        "same_dialog": same_active_context,
        "exact_dialog": exact_dialog,
        "same_conversation": exact_conversation,
        "turn_index": int(row.get("turn_index") or 0),
        "created_at": created,
        "user": user,
        "user_en": user_en,
        "april": april,
        "april_en": april_en,
        "message_id": str(row.get("message_id") or ""),
        "dialog_id": row_dialog,
        "conversation_id": str(row.get("conversation_id") or ""),
        "interpretation_id": str(row.get("interpretation_id") or ""),
        "topic": _topic_label(row),
        "topic_id": _text(row.get("topic_id")),
        "topic_origin_message_id": _text(row.get("topic_origin_message_id")),
        "topic_origin_at": row.get("topic_origin_at"),
        "topic_last_at": row.get("topic_last_at"),
        "topic_summary": _text(row.get("topic_summary"))[:440],
        "sections": _dialogue_section_map(row),
        "is_pending_clarification": _row_is_pending_clarification(row),
        "memory_summary": _compact_memory_summary(row),
        "attachment_evidence": attachment_evidence[:3600],
        "protected_structured_data": protected_data,
    }


def _dialogue_section_map(row: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    """Read McDowell's persisted section index, with a legacy-answer fallback."""
    direct_sections = row.get("sections")
    response = _parse_json(row.get("structured_response"))
    metadata = response.get("metadata") if isinstance(response.get("metadata"), dict) else {}
    record = response.get("dialogue_memory_record")
    if not isinstance(record, dict):
        record = metadata.get("dialogue_memory_record") if isinstance(metadata.get("dialogue_memory_record"), dict) else {}
    # A pending clarification is a control turn, not new explanatory content.
    # Do not turn its numbered choices into false McDowell memory sections.
    if isinstance(record, dict) and isinstance(record.get("pending_clarification"), dict) and record["pending_clarification"].get("active"):
        return []
    raw_sections = direct_sections if isinstance(direct_sections, list) else (record.get("sections") if isinstance(record, dict) else None)
    sections: list[dict[str, Any]] = []
    if isinstance(raw_sections, list):
        for item in raw_sections[:limit]:
            if not isinstance(item, dict):
                continue
            heading = _text(item.get("heading") or item.get("title"))[:180]
            summary = re.sub(r"\s+", " ", _text(item.get("summary")))[:280]
            if heading:
                try:
                    order = int(item.get("order") or len(sections) + 1)
                except (TypeError, ValueError):
                    order = len(sections) + 1
                section_row = {"heading": heading, "summary": summary, "order": order}
                parent_heading = _text(item.get("parent_heading") or item.get("parent_section"))[:180]
                parent_id = _text(item.get("parent_id") or item.get("parent_section_id"))[:120]
                section_id = _text(item.get("section_id") or item.get("id"))[:120]
                if parent_heading:
                    section_row["parent_heading"] = parent_heading
                if parent_id:
                    section_row["parent_id"] = parent_id
                if section_id:
                    section_row["section_id"] = section_id
                sections.append(section_row)
    if sections:
        return sections

    # Compatibility for stored turns created before the McDowell section index existed.
    answer = _text(response.get("answer") or response.get("content") or row.get("april_text") or row.get("april"))
    lines = answer.splitlines()
    found: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        match = re.match(r"^\s*#{1,4}\s+(.+?)\s*#*\s*$", line.strip())
        if match and match.group(1).strip():
            found.append((idx, match.group(1).strip()[:180]))
    for pos, (idx, heading) in enumerate(found[:limit]):
        end = found[pos + 1][0] if pos + 1 < len(found) else len(lines)
        body = re.sub(r"\s+", " ", " ".join(x.strip() for x in lines[idx + 1:end] if x.strip()))
        sections.append({"heading": heading, "summary": body[:280], "order": pos + 1})
    if sections:
        return sections

    # Old stored answers sometimes contain separated paragraphs but no Markdown
    # headings. Create compact paragraph labels so CONTINUE does not fall back to
    # sending the opening 300 characters as a substitute for a topic map.
    paragraphs = [
        re.sub(r"\s+", " ", part).strip()
        for part in re.split(r"\n\s*\n", answer)
        if part.strip()
    ]
    for paragraph in paragraphs[:limit]:
        plain = re.sub(r"^[#>*\-\d.)\s]+", "", paragraph).strip()
        labelled = re.match(r"^([^:—–]{3,65})\s*[:—–]\s*(.+)$", plain)
        if labelled:
            heading, summary = labelled.group(1).strip(), labelled.group(2).strip()
        else:
            words = plain.split()
            heading = " ".join(words[:6]).strip(" ,.;:—–")
            if len(words) > 6:
                heading += "…"
            summary = plain
        if heading:
            sections.append({"heading": heading[:180], "summary": summary[:280], "order": len(sections) + 1})
    return sections


def _compact_memory_summary(row: dict[str, Any]) -> str:
    direct = _text(row.get("memory_summary"))
    if direct:
        return re.sub(r"\s+", " ", direct)[:440]
    response = _parse_json(row.get("structured_response"))
    metadata = response.get("metadata") if isinstance(response.get("metadata"), dict) else {}
    record = response.get("dialogue_memory_record")
    if not isinstance(record, dict):
        record = metadata.get("dialogue_memory_record") if isinstance(metadata.get("dialogue_memory_record"), dict) else {}
    summary = _text(record.get("summary")) if isinstance(record, dict) else ""
    if not summary:
        summary = _text(response.get("summary"))
    if not summary:
        summary = _text(row.get("april_text"))
    return re.sub(r"\s+", " ", summary)[:440]


def _temporal_neighbor(item: dict[str, Any], side: str) -> dict[str, Any]:
    """Create a small, factual descriptor for the closest retained pair near a time gap."""
    try:
        created_at = float(item.get("created_at") or 0.0)
    except (TypeError, ValueError):
        created_at = 0.0
    try:
        at_label = datetime.fromtimestamp(created_at, tz=timezone.utc).astimezone(
            ZoneInfo("Europe/Kyiv")
        ).strftime("%d.%m.%Y %H:%M") if created_at > 0 else "время неизвестно"
    except (TypeError, ValueError, OverflowError, OSError):
        at_label = "время неизвестно"
    topic = _topic_label(item) or _text(item.get("user_text") or item.get("user"))[:120] or "Тема без названия"
    user_text = _text(item.get("user") or item.get("user_text"))[:220]
    summary = _compact_memory_summary(item)[:300]
    return {
        "side": side,
        "created_at": created_at or None,
        "time_label": at_label,
        "topic": topic[:180],
        "user": user_text,
        "summary": summary,
        "message_id": _text(item.get("message_id"))[:120],
    }


def _compact_pair(item: dict[str, Any]) -> dict[str, Any]:
    sections = _dialogue_section_map(item)
    # Do not feed the previous long explanation back into the next prompt. Retain
    # a compact summary plus McDowell's ordered section index instead.
    outline = _compact_memory_summary(item)
    if not outline:
        outline = _text(item.get("april") or item.get("april_text"))[:360]
    modalities = set(item.get("row_modalities") or [])
    has_asset = bool(modalities & {"image", "file", "text_file", "voice"})
    evidence = (_text(item.get("attachment_evidence")) or _row_attachment_evidence(item))[:1800] if has_asset else ""
    topic_id = _text(item.get("topic_id"))
    origin_message_id = _text(item.get("topic_origin_message_id") or item.get("origin_message_id") or item.get("message_id"))
    source_message_id = _text(item.get("message_id"))
    for section in sections:
        if isinstance(section, dict):
            section["topic_id"] = topic_id
            section["topic_origin_message_id"] = origin_message_id
            section["source_message_id"] = _text(section.get("message_id") or source_message_id)
    return {
        "turn": item.get("turn_index"),
        "user": _text(item.get("user") or item.get("user_text"))[:360],
        "april": outline[:440],
        "topic": _text(item.get("topic"))[:200],
        "topic_id": _text(item.get("topic_id")),
        "topic_origin_message_id": _text(item.get("topic_origin_message_id")),
        "origin_message_id": origin_message_id,
        "topic_origin_at": item.get("topic_origin_at"),
        "topic_last_at": item.get("topic_last_at"),
        "source_message_id": _text(item.get("message_id")),
        "sections": sections,
        "score": item.get("score"),
        "same_dialog": bool(item.get("same_dialog")),
        "message_id": _text(item.get("message_id")),
        "attachment_evidence": evidence,
        "context_binding": {
            "subject_terms": list(item.get("subject_terms") or [])[:12],
            "numeric_anchor_overlap": float(item.get("numeric_anchor_overlap") or 0),
            "source_data_alignment": float(item.get("source_data_alignment") or 0),
            "subject_overlap": float(item.get("subject_overlap") or 0),
            "has_value_bearing_structure": int(item.get("structured_data_richness") or 0) >= 8,
        },
        "protected_structured_data": deepcopy(item.get("protected_structured_data"))
        if isinstance(item.get("protected_structured_data"), dict) else {},
    }



_SECTION_QUERY_NOISE = {
    "подробней", "подробнее", "расскажи", "объясни", "поясни", "продолжи", "продолжай",
    "расширь", "разверни", "дальше", "еще", "ещё", "больше", "поподробнее", "именно",
    "хочу", "можно", "покажи", "скажи", "please", "more", "detail", "details", "explain",
    "elaborate", "continue", "expand", "about", "that", "this", "its", "her", "his",
    "часть", "раздел", "пункт",
}
_SECTION_TOPIC_NOISE = _SECTION_QUERY_NOISE | {
    "применение", "применении", "применения", "применению", "работает", "работе",
    "про", "нее", "неё", "ее", "её", "это", "тот", "та", "эта", "этот",
    "имел", "имела", "имели", "ввиду", "виду", "говорил", "говорила", "подразумевал",
    "имелввиду", "значил", "имею", "нет", "actually", "meant", "mean",
}

# Words that express the act/time of recalling history, not the topic being recalled.
# Keeping this separate from the general stop-word list prevents names and subject nouns
# from being removed when selecting relevant memories.
_HISTORY_QUERY_NOISE = _SECTION_TOPIC_NOISE | {
    "говорил", "говорила", "говорили", "говорились", "общались", "обсуждали",
    "обсуждение", "обсуждении", "разговор", "разговора", "разговоре", "речь",
    "история", "истории", "диалог", "диалога", "диалоге", "общение", "общения",
    "сегодня", "вчера", "позавчера", "сейчас", "раньше", "тогда", "недавно",
    "прошлый", "прошлая", "прошлое", "прошлую", "предыдущий", "предыдущая",
    "предыдущее", "предыдущую", "напомни", "вспомни", "помнишь", "помним",
    "вспомнить", "напомнить", "сказать", "расскажи", "расскажите", "кратко",
    "краткий", "содержание", "содержании", "тема", "темы", "тему", "вопрос",
    "вопросе", "вопросы", "какие", "какую", "какой", "какое", "что", "чем",
    # Demonstratives in questions such as “что такое гравитация?” are grammar,
    # not the requested subject. Leaving “такое” here let it falsely match a
    # historical topic and inject that unrelated pair into a NEW request.
    "такое", "такой", "такая", "такие", "такого", "такую", "таком", "таким", "таких", "такова", "таков",
    "мы", "нам", "наше", "наши", "наш", "нашу", "мне", "мои", "мой",
    "последних", "последние", "час", "часа", "часов", "минут", "минуты", "дней", "дня", "недели",
    "назад", "хоть", "примерно", "около", "время", "времени", "помни", "помниш", "помнишь", "вспоминаешь",
    "list", "topic", "topics", "show", "history", "conversation", "conversations", "talked", "talking", "discuss", "discussed",
    "тем", "темами", "темах", "топик", "топика", "топики", "топиков", "диалогов", "разговоров", "обсуждении", "обсуждение",
    "сегодняшний", "утром", "вечером", "ночью", "период", "периода", "время", "времени",
    "октября", "ноября", "декабря", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "monday", "tuesday", "wednesday", "thursday", "friday",
    "saturday", "sunday", "hours", "hour", "minutes", "minute", "yesterday", "today", "last",
}
_SECTION_REQUEST_MARKERS = (
    "подроб", "применен", "раздел", "пункт", "часть", "расскажи больше", "объясни подробнее",
    "углуб", "как это работает", "почему это", "more detail", "application", "section", "subsection",
    "part of", "expand on", "elaborate on",
)


def _fuzzy_token_overlap(query_tokens: set[str], candidate_tokens: set[str]) -> float:
    """Token overlap tolerant of inflection and one or two typing errors."""
    if not query_tokens:
        return 0.0
    matched = 0
    candidate_list = list(candidate_tokens)
    for query_token in query_tokens:
        if query_token in candidate_tokens or any(
            len(candidate) >= 5 and len(query_token) >= 5
            and (query_token[:5] == candidate[:5] or query_token.startswith(candidate[:6]) or candidate.startswith(query_token[:6]))
            for candidate in candidate_list
        ):
            matched += 1
            continue
        if len(query_token) >= 5 and any(
            len(candidate) >= 5 and (
                fuzz.ratio(query_token, candidate) >= 76
                # Compare the first five characters as well as the full inflected
                # form. This tolerates one leading typo plus a Russian case ending
                # (e.g. "ыизику" -> "физика") without dropping the topic entirely.
                or fuzz.ratio(query_token[:5], candidate[:5]) >= 76
            )
            for candidate in candidate_list
        ):
            matched += 1
    return matched / max(1, len(query_tokens))


def _history_topic_overlap(query_tokens: set[str], candidate_tokens: set[str]) -> float:
    """Strict overlap for selecting a past *topic*, distinct from typo-tolerant pair search.

    The general fuzzy matcher tolerates one edit in the first five letters. That
    is useful for a direct typo like “ыизика” -> “физика”, but it can also make
    unrelated words such as “гравитация” and “правила” look like a topic match.
    History-topic selection therefore requires a shared morphological prefix or
    a strong whole-token match before it counts a subject as found.
    """
    if not query_tokens or not candidate_tokens:
        return 0.0
    matched = 0
    candidates = list(candidate_tokens)
    for query_token in query_tokens:
        if query_token in candidate_tokens or any(
            len(candidate) >= 5 and len(query_token) >= 5
            and (query_token[:5] == candidate[:5]
                 or query_token.startswith(candidate[:6])
                 or candidate.startswith(query_token[:6]))
            for candidate in candidates
        ):
            matched += 1
            continue
        if len(query_token) >= 6 and any(
            len(candidate) >= 6 and fuzz.ratio(query_token, candidate) >= 82
            for candidate in candidates
        ):
            matched += 1
    return matched / max(1, len(query_tokens))


def _topic_query_overlap(query: str, topic: str) -> float:
    """Overlap only on topic-bearing words, not generic continuation vocabulary."""
    query_tokens = _semantic_tokens(query) - _SECTION_TOPIC_NOISE - _CONTEXT_GENERIC_TERMS
    topic_tokens = _topic_tokens(topic)
    return _fuzzy_token_overlap(query_tokens, topic_tokens) if query_tokens else 0.0


def _history_query_topic_tokens(query: str) -> set[str]:
    """Extract subject-bearing words from a history request, excluding recall wording and times."""
    return {
        token for token in (_semantic_tokens(query) - _HISTORY_QUERY_NOISE)
        if not token.isdigit() and len(token) > 2
    }


def _history_topic_text(item: dict[str, Any]) -> str:
    sections = item.get("sections") if isinstance(item.get("sections"), list) else []
    section_text = " ".join(
        f"{_text(section.get('heading'))} {_text(section.get('summary'))}"
        for section in sections if isinstance(section, dict)
    )
    return " ".join((
        _text(item.get("topic")), _text(item.get("summary")),
        _text(item.get("last_question")), section_text,
    ))


def _rank_history_topics(query: str, topics: list[dict[str, Any]], limit: int, *, fallback: bool = True) -> list[dict[str, Any]]:
    """Prefer matching topics for a subject-specific recall; keep recency order for broad recall."""
    bounded = [dict(item) for item in topics if isinstance(item, dict)]
    tokens = _history_query_topic_tokens(query)
    if not tokens:
        return bounded[:max(1, min(10, int(limit or 10)))] if fallback else []
    ranked: list[tuple[float, float, dict[str, Any]]] = []
    for item in bounded:
        candidate_tokens = _semantic_tokens(_history_topic_text(item))
        overlap = _history_topic_overlap(tokens, candidate_tokens)
        if overlap <= 0:
            continue
        phrase = fuzz.token_set_ratio(" ".join(sorted(tokens)), " ".join(sorted(candidate_tokens))) / 100.0 if candidate_tokens else 0.0
        score = 0.78 * overlap + 0.22 * phrase
        ranked.append((score, float(item.get("last_at") or 0), item))
    if not ranked:
        # Broad history overview may fall back to recent topics; a normal request
        # must not receive unrelated topics merely because no semantic match exists.
        return bounded[:max(1, min(10, int(limit or 10)))] if fallback else []
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [dict(item) for _, _, item in ranked[:max(1, min(10, int(limit or 10)))]]


def _select_history_context_pairs(
    query: str,
    matches: list[dict[str, Any]],
    topic_index: list[dict[str, Any]],
    all_rows: list[dict[str, Any]],
    *,
    requested_topic_count: int = 10,
) -> tuple[list[dict[str, Any]], str, int]:
    """Select grounded pairs for history recall even though its relation remains NEW."""
    tokens = _history_query_topic_tokens(query)
    eligible = [item for item in matches if isinstance(item, dict) and not item.get("is_pending_clarification")]
    selected: list[dict[str, Any]] = []
    method = "topic_index_overview"
    matched_count = 0

    if tokens:
        method = "subject_ranked_pairs"
        ranked: list[tuple[float, float, dict[str, Any]]] = []
        for item in eligible:
            section_text = " ".join(
                f"{_text(section.get('heading'))} {_text(section.get('summary'))}"
                for section in (item.get("sections") or []) if isinstance(section, dict)
            )
            candidate_text = " ".join((
                _text(item.get("topic")), _text(item.get("user")), _text(item.get("user_en")),
                _text(item.get("april")), _text(item.get("april_en")),
                _text(item.get("memory_summary")), section_text,
            ))
            overlap = _fuzzy_token_overlap(tokens, _semantic_tokens(candidate_text))
            if overlap <= 0:
                continue
            # Subject overlap must dominate generic recency/current-dialog bonuses.
            relevance = 0.78 * overlap + 0.17 * float(item.get("entity_overlap") or 0) + 0.05 * float(item.get("score") or 0)
            ranked.append((relevance, float(item.get("created_at") or 0), item))
        matched_count = len(ranked)
        ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
        # Return up to four evidence pairs for the named topic; deduplicate exact message IDs.
        seen_ids: set[str] = set()
        for _, _, item in ranked:
            message_id = _text(item.get("message_id"))
            if message_id and message_id in seen_ids:
                continue
            if message_id:
                seen_ids.add(message_id)
            selected.append(_compact_pair(item))
            if len(selected) >= 4:
                break

        if not selected:
            # Secondary bridge: a topic-index entry may identify the matching turn
            # even if the old row's text/translation fields differ from the new query.
            topic_ranked = _rank_history_topics(query, topic_index, 4)
            row_by_id = {_text(row.get("message_id")): row for row in all_rows if _text(row.get("message_id"))}
            for topic in topic_ranked:
                row = row_by_id.get(_text(topic.get("message_id")))
                if row:
                    selected.append(_compact_pair(_candidate_score(query, row, dialog_id="")))
                    if len(selected) >= 3:
                        break
            if selected:
                method = "subject_topic_index_fallback"
    else:
        # Broad recall: use representatives of the latest distinct topics, not
        # arbitrary pairs with high recency-weighted similarity to the word 'today'.
        row_by_id = {_text(row.get("message_id")): row for row in all_rows if _text(row.get("message_id"))}
        for topic in topic_index[:min(4, max(1, requested_topic_count))]:
            row = row_by_id.get(_text(topic.get("message_id")))
            if row is None:
                continue
            selected.append(_compact_pair(_candidate_score(query, row, dialog_id="")))
        if not selected:
            selected = [_compact_pair(item) for item in eligible[:min(3, max(1, requested_topic_count))]]

    return selected, method, matched_count


def _section_match_score(query: str, section: dict[str, Any]) -> float:
    heading = _text(section.get("heading") or section.get("title"))
    summary = _text(section.get("summary"))
    q_tokens = _semantic_tokens(query) - _SECTION_QUERY_NOISE
    c_tokens = _semantic_tokens(heading + " " + summary)
    if not q_tokens or not c_tokens:
        return 0.0
    q_text = " ".join(sorted(q_tokens))
    h_text = " ".join(sorted(_semantic_tokens(heading)))
    c_text = " ".join(sorted(c_tokens))
    overlap = _fuzzy_token_overlap(q_tokens, c_tokens)
    heading_overlap = _fuzzy_token_overlap(q_tokens, _semantic_tokens(heading))
    fuzzy_all = fuzz.token_set_ratio(q_text, c_text) / 100.0 if q_text and c_text else 0.0
    fuzzy_heading = fuzz.token_set_ratio(q_text, h_text) / 100.0 if q_text and h_text else 0.0
    return round(min(1.0, 0.32 * fuzzy_all + 0.28 * fuzzy_heading + 0.28 * overlap + 0.12 * heading_overlap), 6)


def _looks_like_topic_correction(query: str) -> bool:
    low = _text(query).lower().replace("ё", "е")
    markers = (
        "я имел в виду", "я имел ввиду", "я имела в виду", "я имела ввиду",
        "нет, я имел", "нет я имел", "нет, я имела", "нет я имела",
        "я говорил о", "я говорила о", "я имел в виду именно", "я про ",
        "я имел в виду тему", "i meant", "i mean", "what i meant was",
    )
    return any(marker in low for marker in markers)


def _is_section_request(query: str) -> bool:
    low = _text(query).lower().replace("ё", "е")
    return any(marker.replace("ё", "е") in low for marker in _SECTION_REQUEST_MARKERS)


def _is_generic_section_pointer(query: str) -> bool:
    """True when the user asks for a section by broad reference, not its name."""
    if not _is_section_request(query):
        return False
    meaningful = _semantic_tokens(query) - _SECTION_TOPIC_NOISE
    return not meaningful


def _is_application_related_section(section: dict[str, Any]) -> bool:
    """Identify application/use/practice sections for broad 'its application' asks."""
    text = (_text(section.get("heading")) + " " + _text(section.get("summary"))).lower().replace("ё", "е")
    markers = (
        "примен", "использ", "практическ", "прикладн", "приложен", "реализ",
        "application", "use case", "practical", "applied", "implementation",
    )
    return any(marker in text for marker in markers)


def _memory_record_from_row(row: dict[str, Any]) -> dict[str, Any]:
    response = _parse_json(row.get("structured_response"))
    record = response.get("dialogue_memory_record")
    if not isinstance(record, dict):
        metadata = response.get("metadata") if isinstance(response.get("metadata"), dict) else {}
        record = metadata.get("dialogue_memory_record") if isinstance(metadata.get("dialogue_memory_record"), dict) else {}
    return record if isinstance(record, dict) else {}


def _row_is_pending_clarification(row: dict[str, Any]) -> bool:
    record = _memory_record_from_row(row)
    pending = record.get("pending_clarification")
    return bool(isinstance(pending, dict) and pending.get("active"))


def _latest_pending_clarification(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Read pending clarification from the newest saved assistant turn only."""
    ordered = sorted(
        [row for row in rows if isinstance(row, dict)],
        key=lambda row: (float(row.get("created_at") or 0), int(row.get("turn_index") or 0)),
        reverse=True,
    )
    if not ordered:
        return {}
    record = _memory_record_from_row(ordered[0])
    pending = record.get("pending_clarification")
    if isinstance(pending, dict) and pending.get("active") and isinstance(pending.get("options"), list):
        return deepcopy(pending)
    return {}


_CLARIFICATION_REJECTION_MARKERS = (
    "это не то", "не то", "не те темы", "это не те темы", "не тот раздел",
    "не тот пункт", "я не это имел", "я не это имела", "я имел в виду другое",
    "я имела в виду другое", "не это имел в виду", "не это имела в виду",
    "я имел ввиду другое", "я имела ввиду другое", "не то имел в виду",
    "не то имела в виду", "i meant something else", "not those topics", "not that section",
)

_CLARIFICATION_META_NOISE = _SECTION_TOPIC_NOISE | {
    "нет", "не", "то", "те", "тот", "раз", "правильно", "неправильно", "значит",
    "имел", "имела", "ввиду", "имею", "хотел", "хотела", "говорил", "говорила",
    "другое", "именно", "this", "that", "wrong", "mean", "meant", "topic", "topics",
}


def _looks_like_clarification_rejection(query: str) -> bool:
    low = _text(query).lower().replace("ё", "е")
    return any(marker.replace("ё", "е") in low for marker in _CLARIFICATION_REJECTION_MARKERS)


def _clarification_target_text(query: str) -> str:
    """Remove conversational correction framing while preserving the user's topic words."""
    value = re.sub(r"\s+", " ", _text(query)).strip(" \t\r\n.,;:!?—–-")
    # Remove a numbered choice prefix, but not a number explicitly introduced as a section.
    value = re.sub(r"^\s*(?:да[, ]*)?([1-9])\s*[.)\-:]\s*", "", value, flags=re.I)
    value = re.sub(r"^\s*(?:нет[, ]*)?(?:это не то|это не те темы|не те темы|не тот раздел|не тот пункт)[, :—–-]*", "", value, flags=re.I)
    value = re.sub(r"^\s*(?:нет[, ]*)?(?:я имел|я имела|я хотел|я хотела)\s+(?:в виду|ввиду)?[, :—–-]*", "", value, flags=re.I)
    value = re.sub(r"\b(?:я имел|я имела|я хотел|я хотела)\s+(?:в виду|ввиду)\b", " ", value, flags=re.I)
    value = re.sub(r"\b(?:я про|я говорил о|я говорила о)\b", " ", value, flags=re.I)
    value = re.sub(r"\b(?:это не то|это не те темы|не те темы|не тот раздел|не тот пункт|не это|это другое)\b", " ", value, flags=re.I)
    value = re.sub(r"^\s*(?:нет|да|извини|возможно)[, :—–-]+", "", value, flags=re.I)
    return re.sub(r"\s+", " ", value).strip(" \t\r\n.,;:!?—–-")


def _option_similarity(query: str, item: dict[str, Any]) -> float:
    target = _clarification_target_text(query)
    q_tokens = _semantic_tokens(target) - _CLARIFICATION_META_NOISE
    label = " ".join(_text(item.get(k)) for k in ("topic", "heading", "summary"))
    label_tokens = _semantic_tokens(label) - _CLARIFICATION_META_NOISE
    if not q_tokens or not label_tokens:
        return 0.0
    overlap = _fuzzy_token_overlap(q_tokens, label_tokens)
    fuzz_score = fuzz.token_set_ratio(" ".join(sorted(q_tokens)), " ".join(sorted(label_tokens))) / 100.0
    return round(0.58 * overlap + 0.42 * fuzz_score, 6)


def _match_clarification_option(query: str, pending: dict[str, Any]) -> dict[str, Any]:
    """Resolve numbers, partial titles or free-form replies without trapping the user."""
    options = [item for item in (pending.get("options") or []) if isinstance(item, dict)]
    if not options:
        return {}
    low = _text(query).lower().replace("ё", "е")
    number = re.match(r"^\s*(?:да[, ]*)?(?:(?:вариант|пункт|раздел|номер)\s*(?:№\s*)?)?([1-9])(?:\s*вариант)?\s*[.!)]?\s*$", low)
    if number:
        index = int(number.group(1)) - 1
        return dict(options[index]) if index < len(options) else {}
    ordinal_map = {"первый": 1, "первую": 1, "первое": 1, "первого": 1, "второй": 2, "вторую": 2, "второе": 2, "второго": 2, "третий": 3, "третью": 3, "третье": 3, "третьего": 3, "первый вариант": 1, "второй вариант": 2, "третий вариант": 3, "first": 1, "second": 2, "third": 3}
    normalized_choice = re.sub(r"^(?:да|ок|хорошо|ага)[, ]+", "", low.strip())
    for phrase, index in ordinal_map.items():
        if normalized_choice == phrase and index <= len(options):
            return dict(options[index - 1])

    # A user often writes both the menu number and the section name. Accept the
    # number only when the words following it also identify that same option.
    prefixed = re.match(r"^\s*(?:да[, ]*)?([1-9])\s+(?!вариант)(.+)$", low)
    if prefixed:
        index = int(prefixed.group(1)) - 1
        if index < len(options):
            target_score = _option_similarity(prefixed.group(2), options[index])
            if target_score >= 0.26:
                return dict(options[index])

    scored = sorted(
        ((_option_similarity(low, item), dict(item)) for item in options),
        key=lambda entry: entry[0], reverse=True,
    )
    if not scored:
        return {}
    second = scored[1][0] if len(scored) > 1 else 0.0
    return scored[0][1] if scored[0][0] >= 0.43 and scored[0][0] - second >= 0.08 else {}


def _explicit_section_number(query: str) -> int | None:
    """Read section numbers in natural Russian/English word order, including inflections."""
    low = _clarification_target_text(query).lower().replace("ё", "е")
    patterns = (
        r"\b(?:раздел\w*|пункт\w*|част\w*|подраздел\w*|тема\w*|section|subsection|part|item)\s*(?:№\s*)?(\d{1,2})\b",
        r"\b(\d{1,2})\s*(?:-?й\s*)?(?:раздел\w*|пункт\w*|част\w*|подраздел\w*|тема\w*|section|subsection|part|item)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, low)
        if match:
            try:
                return int(match.group(1))
            except (TypeError, ValueError):
                return None
    # A compact request such as "6 как атомы соединяются" is also a numbered pointer.
    match = re.match(r"^\s*(\d{1,2})\s+(?=(?:как|что|почему|зачем|about|how|what|why)\b)", low)
    return int(match.group(1)) if match else None


def _rank_sections_across_history(query: str, rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    """Search all authenticated 24-hour turns, including stored section headings and summaries."""
    target = _clarification_target_text(query)
    explicit_order = _explicit_section_number(target)
    # Remove the ordinal marker from text similarity; it is matched as a separate
    # structural field below so section 8 cannot be mistaken for section 5 or 6.
    target = re.sub(r"\b(?:раздел\w*|пункт\w*|част\w*|подраздел\w*|тема\w*|section|subsection|part|item)\s*(?:№\s*)?\d{1,2}\b", " ", target, flags=re.I)
    target = re.sub(r"\b\d{1,2}\s*(?:-?й\s*)?(?:раздел\w*|пункт\w*|част\w*|подраздел\w*|тема\w*|section|subsection|part|item)\b", " ", target, flags=re.I)
    if explicit_order is None:
        leading = re.match(r"^\s*(\d{1,2})\s+(?=(?:как|что|почему|зачем|about|how|what|why)\b)", target, flags=re.I)
        if leading:
            explicit_order = int(leading.group(1))
            target = re.sub(r"^\s*\d{1,2}\s+", "", target)
    query_tokens = _semantic_tokens(target) - _CLARIFICATION_META_NOISE
    if not query_tokens and explicit_order is None:
        return []

    ranked: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict) or _row_is_pending_clarification(row):
            continue
        topic = _topic_label(row)
        topic_overlap = _topic_query_overlap(target, topic)
        if explicit_order is not None and not query_tokens:
            sections = [
                {
                    "topic": topic,
                    "heading": _text(section.get("heading"))[:180],
                    "summary": _text(section.get("summary"))[:360],
                    "order": section.get("order"),
                    "message_id": _text(section.get("message_id") or row.get("message_id")),
                    "dialog_id": _text(row.get("dialog_id")),
                    "conversation_id": _text(row.get("conversation_id")),
                    "score": 1.0,
                }
                for section in _dialogue_section_map(row)
                if int(section.get("order") or 0) == explicit_order
            ]
        else:
            sections = _rank_sections_for_row(target, row)
        if sections:
            for section in sections:
                score = 0.78 * float(section.get("score") or 0) + 0.20 * topic_overlap
                order_matches = explicit_order is not None and int(section.get("order") or 0) == explicit_order
                if order_matches:
                    score = min(1.0, score + (0.28 if topic_overlap >= 0.20 else 0.20))
                elif explicit_order is not None:
                    # Penalize mismatched section numbers, rather than quietly
                    # ranking a nearby heading as if it were the requested one.
                    score *= 0.35
                section["score"] = round(score, 6)
                section["topic_overlap"] = round(topic_overlap, 6)
                ranked.append(section)
        # Keep a topic-level route for legacy turns whose answer has no headings.
        summary = _compact_memory_summary(row)
        topic_score = 0.72 * topic_overlap + 0.28 * _fuzzy_token_overlap(
            query_tokens, _semantic_tokens(topic + " " + summary)
        ) if query_tokens else 0.0
        if topic_score >= 0.28:
            ranked.append({
                "topic": topic,
                "heading": topic,
                "summary": summary[:360],
                "order": 0,
                "message_id": _text(row.get("message_id")),
                "dialog_id": _text(row.get("dialog_id")),
                "conversation_id": _text(row.get("conversation_id")),
                "score": round(topic_score, 6),
                "topic_overlap": round(topic_overlap, 6),
            })
    ranked.sort(key=lambda item: (float(item.get("score") or 0), float(item.get("topic_overlap") or 0)), reverse=True)
    # Deduplicate same section from overlapping legacy rows while preserving rank.
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in ranked:
        key = (_text(item.get("message_id")), _text(item.get("heading")).casefold(), _text(item.get("topic")).casefold())
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
        if len(output) >= limit:
            break
    return output


def _clarification_prompt(original_request: str, options: list[dict[str, Any]], language: str = "ru") -> str:
    options = [item for item in options[:3] if isinstance(item, dict)]
    if not options:
        if language == "uk":
            return "Можливо, я не так зрозуміла номер або назву розділу й не хочу підміняти його схожою темою. Нагадай, будь ласка, кілька слів із заголовка або про що там ішлося — я ще раз перевірю історію."
        if language == "en":
            return "I may have misread the section number or title, and I don't want to substitute a similar topic. Could you share a few words from its heading or what it covered? I'll check the history again."
        return "Похоже, я могла неверно определить номер или название раздела и не хочу подменять его похожей темой. Напомни, пожалуйста, пару слов из заголовка или о чём там шла речь — я ещё раз проверю историю."
    topics = {_text(item.get("topic")) for item in options if _text(item.get("topic"))}
    shared_topic = next(iter(topics)) if len(topics) == 1 else ""
    topic_caption = f" в теме «{shared_topic[:90]}»" if shared_topic and shared_topic.casefold() not in {"тема диалога", "безымянная тема"} else ""
    labels = []
    for index, item in enumerate(options, 1):
        heading = _text(item.get("heading") or item.get("topic"))
        summary = _text(item.get("summary"))
        label = heading[:180]
        if summary and summary.casefold() != heading.casefold():
            label += " — " + summary[:95]
        labels.append(f"{index}. {label[:190]}")
    choices = "\n".join(labels)
    request = _text(original_request)[:130]
    if language == "uk":
        lead = f"Хочу продовжити твій запит «{request}»{topic_caption} і не вибрати схожий, але не той розділ. Я знайшла кілька близьких варіантів:"
        tail = "\nМожеш назвати номер або описати своїми словами — я звірю це з історією."
    elif language == "en":
        lead = f'I want to continue “{request}”{topic_caption} without picking the wrong section. I found a few close matches:'
        tail = "\nReply with a number or describe it in your own words, and I will check the history."
    else:
        lead = f"Хочу продолжить твой запрос «{request}»{topic_caption} и не выбрать похожий, но не тот раздел. Нашла несколько близких вариантов:"
        tail = "\nМожешь назвать номер или описать своими словами — я сверю это с историей."
    return lead + ("\n" + choices if choices else "") + tail


def _rank_sections_for_row(query: str, row: dict[str, Any]) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    row_sections = _dialogue_section_map(row)
    for section in row_sections:
        score = _section_match_score(query, section)
        if score <= 0:
            continue
        ranked.append({
            "topic": _topic_label(row),
            "heading": _text(section.get("heading"))[:180],
            "summary": _text(section.get("summary"))[:360],
            "order": section.get("order"),
            "message_id": _text(section.get("message_id") or row.get("message_id")),
            "dialog_id": _text(row.get("dialog_id")),
            "conversation_id": _text(row.get("conversation_id")),
            "score": score,
        })
    ranked.sort(key=lambda item: (float(item.get("score") or 0), -int(item.get("order") or 0)), reverse=True)
    return ranked

def search_dialogue_context(
    user_id: Any,
    query: str,
    *,
    dialog_id: str = "",
    conversation_id: str = "",
    resume_message_id: str = "",
    limit: int = 12,
    has_image: bool = False,
    has_file: bool = False,
    has_voice: bool = False,
    query_interpretation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Find the smallest reliable continuation point in the authenticated 24h memory.

    Retrieval hierarchy: topic -> USER↔APRIL pair -> McDowell section. Only the
    selected pair/section is passed forward. An unclear choice yields a local
    clarification state that persists the original request and can be resumed.
    """
    search_started = time.perf_counter()
    uid = _uid(user_id)
    state = hydrate(uid)
    all_rows = [row for row in (state.get("dialogue_pairs") or []) if isinstance(row, dict) and not _is_failed_provider_row(row)]
    # Keep this authenticated, already-pruned Premium 24h set for honest nearest-neighbor
    # lookup if an explicitly requested time interval contains no saved dialogue pairs.
    retained_rows = list(all_rows)
    resume_key = _text(resume_message_id)
    reference_followup = _looks_like_referential_followup(query)
    query_interpretation = dict(query_interpretation or {})
    history_request = bool(query_interpretation.get("history_request")) or _is_history_request(query)
    new_topic_request = _looks_like_new_topic(query) or bool(query_interpretation.get("explicit_topic_switch"))
    interpreted_direction = _text(query_interpretation.get("direction"))
    interpreted_intent = _text(query_interpretation.get("primary_intent"))
    topic_reference_fragment = _text(query_interpretation.get("topic_reference")) == "TOPIC_FRAGMENT"
    context_signature = _query_context_signature(query, query_interpretation)
    pragmatic_features = query_interpretation.get("pragmatic_features") if isinstance(query_interpretation.get("pragmatic_features"), dict) else {}
    speech_act = _text(query_interpretation.get("speech_act")).upper()
    communicative_act = _text(query_interpretation.get("communicative_act")).upper()
    is_correction = bool(
        pragmatic_features.get("correction")
        or pragmatic_features.get("active_branch_repair")
        or pragmatic_features.get("previous_answer_reference")
        or pragmatic_features.get("factual_verification_request")
        or query_interpretation.get("active_branch_repair")
        or query_interpretation.get("previous_answer_reference")
        or query_interpretation.get("factual_verification_request")
        or speech_act in {"CORRECTION_OR_REVISION", "FRUSTRATION_OR_DISSATISFACTION", "NEGATION_OR_DISAGREEMENT"}
        or communicative_act in {"REVISE_PREVIOUS_RESPONSE", "RESPOND_TO_DISAGREEMENT"}
        or _looks_like_topic_correction(query)
        or _looks_like_answer_verification(query)
    )
    is_short_acknowledgement = bool(
        pragmatic_features.get("acknowledgement_or_agreement")
        and len(_tokens(query)) <= 3
        and not pragmatic_features.get("has_independent_payload")
        and not history_request
        and not new_topic_request
    )
    # In a correction, a rejected entity ("not Mendeleev") is not the intended
    # search subject. If the user supplies a positive replacement ("I mean math"),
    # resolve subjects from that replacement clause only.
    subject_query = query
    low_subject_query = _text(query).lower().replace("ё", "е")
    positive_replacement = re.search(r"\b(?:я\s+про|я\s+имел\w*\s+в\s+виду|я\s+имела\w*\s+в\s+виду|именно)\s+(.+)$", low_subject_query)
    if is_correction and positive_replacement:
        subject_query = positive_replacement.group(1)
    elif is_correction and re.search(r"\bне\s+про\s+[^,.;!?]+(?:\s+(?:спрашивал|спрашивала|говорил|говорила|имел|имела)\b|$)", low_subject_query):
        subject_query = ""
    supplied_subjects = context_signature.get("subject_terms")
    query_subjects = set(_subject_tokens(subject_query)) if subject_query != query else (
        set(supplied_subjects) if isinstance(supplied_subjects, list) else _subject_tokens(query)
    )
    # Referential questions about an object's origin are continuations, not a new
    # "internet/source" topic. The grammar/predicate terms are excluded above; this
    # fallback prevents morphology/typos from creating a false subject conflict.
    if reference_followup and not positive_replacement and not is_correction:
        low = _text(query).lower().replace("ё", "е")
        if re.search(r"\b(?:его|ее|её|это|этот|эта|эту)\b", low) and re.search(r"\b(?:придум\w*|слиз\w*|скопир\w*|напис\w*|взял\w*|взяла\w*)\b", low):
            query_subjects = set()

    # Resolve a text-specified period into an actual filter over the authenticated
    # Premium memory. This preserves the 24-hour product retention cap and uses
    # local civil time for “today/morning/14:00”, with timestamps normalized to UTC.
    search_now_ts = time.time()
    parsed_window = query_interpretation.get("time_window") if isinstance(query_interpretation.get("time_window"), dict) else {}
    if not parsed_window.get("has_constraint") or not isinstance(parsed_window.get("start_at"), (int, float)) or not isinstance(parsed_window.get("end_at"), (int, float)):
        parsed_window = extract_temporal_window(query, reference_ts=search_now_ts)
    should_apply_time_filter = bool(
        parsed_window.get("has_constraint")
        and not resume_key
        and (
            history_request
            or bool(query_interpretation.get("requires_memory"))
            or bool(query_interpretation.get("history_inventory_request"))
            or interpreted_intent in {"HISTORY_RECALL", "HISTORY_SEARCH", "HISTORY_SUMMARY", "TOPIC_CONTINUATION", "PRIOR_DECISION_RECALL", "PLAN_RECALL"}
        )
    )
    time_filter = intersect_retention_window(
        parsed_window, now_ts=search_now_ts, retention_seconds=DIALOGUE_WINDOW_SECONDS
    ) if should_apply_time_filter else {
        "applied": False, "empty": False, "start_at": None, "end_at": None, "source": "none"
    }
    if time_filter.get("applied"):
        time_filter["matched_rows"] = 0
        time_filter["neighbors"] = {"before": None, "after": None}
        time_filter["retention_hours"] = DIALOGUE_WINDOW_HOURS
        if time_filter.get("empty"):
            # Distinguish old requests from future times: both have no searchable rows,
            # but only the former is outside Premium's retained 24-hour window.
            requested_start = float(time_filter.get("requested_start_at") or parsed_window.get("start_at") or 0.0)
            requested_end = float(time_filter.get("requested_end_at") or parsed_window.get("end_at") or 0.0)
            retention_start = search_now_ts - DIALOGUE_WINDOW_SECONDS
            if requested_start > search_now_ts:
                time_filter["empty_reason"] = "future_period"
            elif requested_end <= retention_start:
                time_filter["empty_reason"] = "outside_retention"
            else:
                time_filter["empty_reason"] = "no_past_overlap"
            all_rows = []
            time_filter["outside_retention_window"] = time_filter["empty_reason"] == "outside_retention"
            # Even when the requested interval does not overlap retained history,
            # provide the closest *available* record on either side. This never
            # widens the Premium window: candidates still come only from retained_rows.
            before_rows = [row for row in retained_rows if float(row.get("created_at") or 0.0) < requested_start]
            after_rows = [row for row in retained_rows if float(row.get("created_at") or 0.0) >= requested_end]
            before_row = max(before_rows, key=lambda row: float(row.get("created_at") or 0.0), default=None)
            after_row = min(after_rows, key=lambda row: float(row.get("created_at") or 0.0), default=None)
            time_filter["neighbors"] = {
                "before": _temporal_neighbor(before_row, "before") if before_row else None,
                "after": _temporal_neighbor(after_row, "after") if after_row else None,
            }
        else:
            lower = float(time_filter["start_at"])
            upper = float(time_filter["end_at"])
            all_rows = [
                row for row in retained_rows
                if lower <= float(row.get("created_at") or 0.0) < upper
            ]
            time_filter["matched_rows"] = len(all_rows)
            time_filter["outside_retention_window"] = False
            if not all_rows:
                # Exact interval is empty: return the nearest retained record on each
                # side as clearly labelled neighbors, never as matches inside the range.
                before_rows = [row for row in retained_rows if float(row.get("created_at") or 0.0) < lower]
                after_rows = [row for row in retained_rows if float(row.get("created_at") or 0.0) >= upper]
                before_row = max(before_rows, key=lambda row: float(row.get("created_at") or 0.0), default=None)
                after_row = min(after_rows, key=lambda row: float(row.get("created_at") or 0.0), default=None)
                time_filter["neighbors"] = {
                    "before": _temporal_neighbor(before_row, "before") if before_row else None,
                    "after": _temporal_neighbor(after_row, "after") if after_row else None,
                }
    resume_anchor_row = next((row for row in all_rows if (
        _text(row.get("message_id")) == resume_key
        or (resume_key.startswith("legacy-memory-") and resume_key == f"legacy-memory-{_text(row.get('id'))}")
    )), None) if resume_key else None
    _apr_timing_log(
        "memory_intent_received",
        user_key=_apr_diag_ref(uid),
        dialog_key=_apr_diag_ref(dialog_id),
        query_key=_apr_diag_ref(query),
        history_request=history_request,
        semantic_intent=interpreted_intent,
        resume_anchor_requested=bool(resume_key),
        resume_anchor_found=bool(resume_anchor_row),
        search_direction=interpreted_direction,
        time_scope=_text(query_interpretation.get("time_scope")),
        search_scope=_text(query_interpretation.get("search_scope")),
        temporal_filter_requested=bool(parsed_window.get("has_constraint")),
        temporal_filter_applied=bool(time_filter.get("applied")),
        temporal_filter_source=_text(time_filter.get("source")),
        temporal_rows_after_filter=len(all_rows),
        temporal_match_count=time_filter.get("matched_rows"),
        temporal_neighbor_sides=sum(1 for side in (time_filter.get("neighbors") or {}).values() if isinstance(side, dict)),
        temporal_outside_retention=bool(time_filter.get("outside_retention_window")),
    )

    scope_started = time.perf_counter()
    if history_request:
        scoped_rows = list(all_rows)
    elif dialog_id or conversation_id:
        scoped_rows = [row for row in all_rows if (
            (dialog_id and _text(row.get("dialog_id")) == _text(dialog_id))
            or (conversation_id and _text(row.get("conversation_id")) == _text(conversation_id))
        )]
    else:
        scoped_rows = list(all_rows)

    # Search the whole user's 24-hour window for a distinctly named old topic,
    # but do not let generic words such as "применение" switch the active topic.
    topic_bearing = _semantic_tokens(subject_query if is_correction and subject_query != query else query) - _SECTION_QUERY_NOISE - _CONTEXT_GENERIC_TERMS
    # A pure correction such as "I wasn't asking about Mendeleev" rejects that
    # entity; searching the archive for the rejected name would repeat the mistake.
    if is_correction and not subject_query.strip():
        topic_bearing = set()
    if reference_followup and not query_subjects and re.search(
        r"\b(?:придум\w*|слиз\w*|скопир\w*|напис\w*|взял\w*|взяла\w*)\b",
        _text(query).lower().replace("ё", "е"),
    ):
        # A referential authorship/source question has no new topical entity.
        # Do not launch a cross-history named-topic search for its predicates.
        topic_bearing = set()
    named_rows: list[tuple[float, dict[str, Any]]] = []
    if not history_request and topic_bearing:
        scoped_ids = {_text(row.get("message_id")) for row in scoped_rows}
        for row in all_rows:
            if _row_is_pending_clarification(row):
                continue
            mid = _text(row.get("message_id"))
            if mid and mid in scoped_ids:
                continue
            row_subjects = _row_subject_tokens(row)
            subject_overlap = _subject_overlap(query_subjects, row_subjects)
            if _subject_conflicts(query_subjects, row_subjects):
                continue
            searchable_topic = " ".join((_topic_label(row), _row_subject_text(row)))
            overlap = _topic_query_overlap(query, searchable_topic)
            if overlap >= 0.50 or (query_subjects and subject_overlap >= 0.60):
                # Subject alignment is useful only when there is also meaningful
                # task/topic overlap; it must not pull a different old task solely
                # because the same product noun appears in it.
                named_rows.append((max(overlap, subject_overlap * 0.72), row))
        named_rows.sort(key=lambda item: (item[0], float(item[1].get("created_at") or 0)), reverse=True)
        for _, row in named_rows[:6]:
            scoped_rows.append(row)

    # Keep rows unique if the same record was found by both the current-dialog
    # scope and the cross-window named-topic search.
    unique_rows: list[dict[str, Any]] = []
    seen_rows: set[str] = set()
    for row in scoped_rows:
        key = _text(row.get("message_id")) or f"{row.get('created_at')}|{row.get('turn_index')}"
        if key not in seen_rows:
            seen_rows.add(key)
            unique_rows.append(row)
    rows = unique_rows
    _apr_timing_log("memory_scope", scope_started, user_key=_apr_diag_ref(uid),
        dialog_key=_apr_diag_ref(dialog_id), conversation_key=_apr_diag_ref(conversation_id),
        rows_in_window=len(all_rows), rows_in_scope=len(rows), history_request=history_request, query_chars=len(str(query or "")))

    query_modalities = {modality for modality, enabled in (
        ("image", bool(has_image)), ("file", bool(has_file)), ("voice", bool(has_voice)),
    ) if enabled}
    pending_clarification = _latest_pending_clarification([row for row in rows if not dialog_id or _text(row.get("dialog_id")) == _text(dialog_id)])
    pending_option: dict[str, Any] = {}
    pending_resolved = False
    if pending_clarification and not new_topic_request:
        pending_option = _match_clarification_option(query, pending_clarification)
        pending_resolved = bool(pending_option)
        # A free-form correction can resolve the question when it clearly names
        # exactly one offered topic/section; ambiguous replies keep the same pending
        # original request rather than becoming the new active topic.

    candidate_started = time.perf_counter()
    matches = [_candidate_score(query, row, dialog_id=str(dialog_id or ""), conversation_id=str(conversation_id or ""), reference_followup=reference_followup, query_modalities=query_modalities)
               for row in rows]
    # For participant-centered, subjectless questions, first rank factual evidence
    # written from the relevant speaker perspective; use the existing relevance and
    # recency ordering for all other turns. No fixed score gate is introduced.
    matches.sort(key=lambda item: (
        int(bool((is_correction or is_short_acknowledgement) and item.get("same_dialog"))),
        int(item.get("participant_alignment") or 0) if not query_subjects else 0,
        float(item["score"]), float(item["recency"]), int(item["turn_index"])
    ), reverse=True)
    _apr_timing_log("candidate_score_rank", candidate_started, candidates_scored=len(rows), matches=len(matches))

    # Build the index once and share it between topic ranking, pair selection and Provider.
    topics = _build_topic_index(all_rows)
    requested_limit = query_interpretation.get("requested_topic_count")
    history_limit = max(1, min(10, int(requested_limit or _history_topic_limit(query, 10))))
    history_minimum = max(1, min(history_limit, int(
        query_interpretation.get("minimum_topic_count") or _history_topic_minimum(query, 5)
    )))

    # Bind every pair and value-bearing structured asset to the topic in which it
    # originated. Exact message ids remain the source of truth; topic ids are an
    # index identity and never replace source provenance.
    topic_by_message_id: dict[str, dict[str, Any]] = {}
    for topic in topics:
        for source_id in list(topic.get("message_ids") or []) + [topic.get("message_id"), topic.get("origin_message_id")]:
            normalized_id = _text(source_id)
            if normalized_id:
                topic_by_message_id[normalized_id] = topic
    for row in all_rows:
        topic = topic_by_message_id.get(_text(row.get("message_id")))
        if not topic:
            continue
        row["topic_id"] = _text(topic.get("topic_id"))
        row["topic_origin_message_id"] = _text(topic.get("origin_message_id"))
        row["topic_origin_at"] = topic.get("first_at")
        row["topic_last_at"] = topic.get("last_at")
        row["topic_summary"] = _text(topic.get("summary"))[:440]
    for match in matches:
        topic = topic_by_message_id.get(_text(match.get("message_id")))
        if not topic:
            continue
        match.update({
            "topic_id": _text(topic.get("topic_id")),
            "topic_origin_message_id": _text(topic.get("origin_message_id")),
            "topic_origin_at": topic.get("first_at"),
            "topic_last_at": topic.get("last_at"),
            "topic_summary": _text(topic.get("summary"))[:440],
        })
        for section in match.get("sections") or []:
            if isinstance(section, dict):
                section["topic_id"] = _text(topic.get("topic_id"))
                section["topic_origin_message_id"] = _text(topic.get("origin_message_id"))
        protected = match.get("protected_structured_data")
        if isinstance(protected, dict) and protected:
            protected["topic_id"] = _text(topic.get("topic_id"))
            protected["topic_origin_message_id"] = _text(topic.get("origin_message_id"))
            protected["source_message_id"] = _text(match.get("message_id"))
            protected["topic_origin_at"] = topic.get("first_at")

    # History recall may show up to ten distinct topics; normal requests receive
    # only semantically matching topics. Broad history requests fall back to
    # recency ordering after the explicit temporal filter has narrowed the rows.
    history_query_tokens = _history_query_topic_tokens(query)
    broad_history_overview = bool(
        history_request and (
            query_interpretation.get("history_inventory_request")
            or _text(query_interpretation.get("primary_intent")).upper() == "HISTORY_SUMMARY"
            or not history_query_tokens
        )
    )
    topic_index = _rank_history_topics(query, topics, 10, fallback=broad_history_overview)
    history_topics = _rank_history_topics(query, topics, history_limit, fallback=broad_history_overview) if history_request else []

    latest_same_dialog = max((item for item in matches if bool(item.get("same_dialog"))),
        key=lambda item: (float(item.get("created_at") or 0), int(item.get("turn_index") or 0)), default=None)
    # Search an ongoing task branch before generic topic ranking. The marker lives
    # in structured_response JSONB; the inference fallback recognizes legacy rows
    # written before the marker existed. Explicit time/history queries bypass it.
    active_work_pair: dict[str, Any] | None = None
    active_work_branch: dict[str, Any] = {}
    active_work_row_index = -1
    active_work_has_marker = False
    if not history_request and not time_filter.get("applied") and not resume_key:
        scoped_work_rows = [
            row for row in all_rows
            if isinstance(row, dict)
            and not _row_is_pending_clarification(row)
            and (
                (_text(dialog_id) and _text(row.get("dialog_id")) == _text(dialog_id))
                or (_text(conversation_id) and _text(row.get("conversation_id")) == _text(conversation_id))
            )
        ]
        scoped_work_rows.sort(
            key=lambda row: (float(row.get("created_at") or 0), int(row.get("turn_index") or 0)),
            reverse=True,
        )
        for work_index, work_row in enumerate(scoped_work_rows):
            work_profile = _infer_active_work_branch(work_row)
            if work_profile.get("active"):
                active_work_pair = work_row
                active_work_branch = dict(work_profile)
                active_work_row_index = work_index
                _, response_record, memory_record = _response_and_request_records(work_row)
                response_meta = response_record.get("metadata") if isinstance(response_record.get("metadata"), dict) else {}
                persisted_marker = response_record.get("active_work_branch")
                if not isinstance(persisted_marker, dict):
                    persisted_marker = response_meta.get("active_work_branch")
                if not isinstance(persisted_marker, dict):
                    persisted_marker = memory_record.get("active_work_branch")
                active_work_has_marker = bool(isinstance(persisted_marker, dict) and persisted_marker.get("active"))
                active_work_branch.setdefault("source_message_id", _text(work_row.get("message_id")))
                active_work_branch.setdefault("origin_message_id", _text(work_row.get("message_id")))
                active_work_branch["candidate_message_id"] = _text(work_row.get("message_id"))[:120]
                break
        # Upgrade old rows without a task marker: locate the nearest preceding
        # task-start row of the same kind, without crossing into an older unrelated
        # game. Persist this origin on the next accepted continuation.
        if active_work_pair and active_work_branch and not active_work_has_marker:
            expected_kind = _text(active_work_branch.get("kind"))
            for origin_row in scoped_work_rows[active_work_row_index + 1:]:
                origin_profile = _infer_active_work_branch(origin_row)
                if _is_active_work_root_candidate(origin_row, origin_profile, expected_kind):
                    origin_id = _text(origin_row.get("message_id"))
                    if origin_id:
                        active_work_branch["origin_message_id"] = origin_id[:120]
                        root_topic = _text(origin_profile.get("topic"))
                        root_answer = _text(origin_row.get("april_text") or origin_row.get("april"))
                        if expected_kind == "interactive_game":
                            titled_game = re.search(r"\b(?:игра|game)\s*[«\"]([^»\"]{2,100})[»\"]", root_answer, re.IGNORECASE)
                            if titled_game:
                                root_topic = _text(titled_game.group(1))
                        if root_topic:
                            active_work_branch["topic"] = root_topic[:240]
                        root_goal = _text(origin_profile.get("goal"))
                        if root_goal:
                            active_work_branch["goal"] = root_goal[:500]
                    break
        # A marker may exist and still have a corrupted origin (for example, a new
        # “create a game” request was saved as a continuation of the prior game).
        # Validate the saved root and prefer the nearest newer root specification
        # when the marker's origin predates a distinct self-contained work request.
        if active_work_pair and active_work_branch and active_work_has_marker:
            expected_kind = _text(active_work_branch.get("kind"))
            current_origin_id = _text(active_work_branch.get("origin_message_id"))
            origin_index = next((i for i, row in enumerate(scoped_work_rows)
                                 if _text(row.get("message_id")) == current_origin_id), -1)
            origin_row = scoped_work_rows[origin_index] if origin_index >= 0 else None
            origin_profile = _infer_active_work_branch(origin_row) if origin_row else {}
            origin_valid = bool(
                origin_row and _is_active_work_root_candidate(origin_row, origin_profile, expected_kind)
            )
            recovered_root = None
            for root_row in scoped_work_rows[active_work_row_index + 1:]:
                root_profile = _infer_active_work_branch(root_row)
                if not _is_active_work_root_candidate(root_row, root_profile, expected_kind):
                    continue
                root_id = _text(root_row.get("message_id"))
                root_index = next((i for i, row in enumerate(scoped_work_rows)
                                   if _text(row.get("message_id")) == root_id), -1)
                # The list is newest-first: a smaller index is newer than the old
                # origin. Recover if the origin is invalid or a newer root intervened.
                if root_id and (not origin_valid or (origin_index >= 0 and root_index < origin_index)):
                    recovered_root = root_row
                    break
            if recovered_root is not None:
                root_id = _text(recovered_root.get("message_id"))
                root_profile = _infer_active_work_branch(recovered_root)
                root_user = _text(recovered_root.get("user_text") or recovered_root.get("user"))
                root_answer = _text(recovered_root.get("april_text") or recovered_root.get("april"))
                root_topic = _topic_label(recovered_root) or root_user
                if expected_kind == "interactive_game":
                    titled_game = re.search(r"\b(?:игра|game)\s*[«\"]([^»\"]{2,100})[»\"]", root_answer, re.IGNORECASE)
                    if titled_game:
                        root_topic = _text(titled_game.group(1))
                active_work_branch["origin_message_id"] = root_id[:120]
                active_work_branch["work_id"] = "work:" + root_id[:120]
                active_work_branch["source_message_id"] = root_id[:120]
                if root_topic:
                    active_work_branch["topic"] = root_topic[:240]
                if root_user:
                    active_work_branch["goal"] = root_user[:500]
                active_work_branch["origin_recovered"] = True
    best = matches[0] if matches else None
    active_subjects = set(latest_same_dialog.get("subject_terms") or []) if latest_same_dialog else set()
    active_subject_conflict = _subject_conflicts(query_subjects, active_subjects)
    # Anaphora inside a complete message (for example, "Расскажи об Эйнштейне
    # ... где применяются его открытия") refers to the subject named in that same
    # message, not necessarily to the previous turn. A sufficiently detailed,
    # self-contained request with a conflicting subject must therefore switch topic
    # even if the generic referential-follow-up detector sees a pronoun such as "его".
    self_contained_subject_switch = bool(
        active_subject_conflict
        and query_subjects
        # A named new entity plus its own pronoun/clause is self-contained even
        # when the sentence is short (“Расскажи про Коперника и как он выглядел”).
        # Requiring four lexical tokens alone let “он” suppress the topic switch.
        and (len(_semantic_tokens(query)) >= 4 or _contains_named_value(query))
        and not history_request
        and not new_topic_request
    )
    semantic_subject_switch = bool(
        active_subject_conflict
        and (interpreted_intent == "NEW_INFORMATION" or self_contained_subject_switch)
        and (self_contained_subject_switch or (not reference_followup and not _continuation_marker(query)))
        and not history_request
        and not new_topic_request
    )
    candidate_match_by_id = {
        _text(item.get("message_id")): item for item in matches if _text(item.get("message_id"))
    }
    explicit_topic_hits = []
    seen_topic_hit_ids: set[str] = set()
    for row in all_rows:
        if _row_is_pending_clarification(row):
            continue
        row_subjects = _row_subject_tokens(row)
        subject_overlap = _subject_overlap(query_subjects, row_subjects)
        if _subject_conflicts(query_subjects, row_subjects):
            continue
        searchable_topic = " ".join((_topic_label(row), _row_subject_text(row)))
        overlap = _topic_query_overlap(query, searchable_topic)
        topic_hit = overlap >= 0.50 or (query_subjects and subject_overlap >= 0.60 and (reference_followup or _looks_like_topic_correction(query)))
        mid = _text(row.get("message_id")) or f"{row.get('created_at')}|{row.get('turn_index')}"
        if topic_hit and mid not in seen_topic_hit_ids:
            seen_topic_hit_ids.add(mid)
            # Prefer a compatible row with exact original values/typed data over a
            # generic text-only derivative, without making old data win by age alone.
            candidate_match = candidate_match_by_id.get(mid) or {}
            source_alignment = (
                float(candidate_match.get("source_data_alignment") or 0)
                if mid in candidate_match_by_id else _source_data_alignment(row)
            )
            row_rank = (
                float(candidate_match.get("score") or 0)
                + 0.30 * max(overlap, subject_overlap * 0.72)
                + min(0.08, 0.012 * _structured_data_richness(_protected_structured_data_from_row(row)))
                + (0.32 * source_alignment)
            )
            explicit_topic_hits.append((row_rank, row))
    explicit_topic_hits.sort(key=lambda item: (item[0], float(item[1].get("created_at") or 0)), reverse=True)
    topic_pointer_match = bool(topic_reference_fragment and explicit_topic_hits)
    # A successfully matched topic pointer explicitly refers to that prior topic,
    # even when the latest turn is about something else. Preserve the raw switch
    # diagnostic, but don't let the latest topic veto the user's resolved pointer.
    decision_subject_switch = bool(semantic_subject_switch and not topic_pointer_match and not is_correction and not is_short_acknowledgement)
    repair_active_branch = bool((is_correction or is_short_acknowledgement) and latest_same_dialog and not new_topic_request and not history_request)
    has_new_attachment = bool(query_modalities)
    explicit_attachment_followup = has_new_attachment and reference_followup
    user_operation = _user_operation_profile(
        query, query_interpretation,
        history_request=history_request,
        new_topic_request=new_topic_request,
        is_correction=is_correction,
        is_short_acknowledgement=is_short_acknowledgement,
    )
    semantic_active_branch_intent = bool(
        latest_same_dialog
        and _has_semantic_active_branch_intent(
            query_interpretation,
            history_request=history_request,
            new_topic_request=new_topic_request,
            has_attachment=has_new_attachment,
            reference_followup=reference_followup,
        )
    )

    # Treat the ranked match as contextual when it contains actual semantic evidence,
    # rather than requiring a fixed hand-chosen score cutoff. Subject conflict remains
    # the safeguard against pulling an unrelated topic into a self-contained request.
    same_dialog_semantic = bool(best and not best.get("subject_mismatch") and (
        (best.get("same_dialog") and any(
            float(best.get(field) or 0) > 0
            for field in ("entity_overlap", "context", "semantic", "answer_overlap", "user_overlap", "subject_overlap")
        )) or float(best.get("entity_overlap") or 0) > 0
    ))
    marker = _continuation_marker(query)
    short_contextual = len(_tokens(query)) <= 12 and _text(query).lower().startswith(("а ", "и ", "ну ", "так ")) and (
        reference_followup or marker or len(_semantic_tokens(query)) == 0
    )
    hot_branch_candidate = _hot_branch_followup_candidate(
        query, query_interpretation, latest_same_dialog,
        query_subjects=query_subjects, reference_followup=reference_followup,
        marker=marker, conversation_id=str(conversation_id or ""), has_attachment=bool(query_modalities),
        history_request=history_request, new_topic_request=new_topic_request,
    )
    new_work_root_request = _looks_like_new_work_root_request(query, active_work_branch)
    hot_work_followup, hot_work_match_reason = _hot_work_followup_candidate(
        query, active_work_branch, active_work_pair,
        history_request=history_request,
        new_topic_request=new_topic_request,
        has_attachment=bool(query_modalities & {"image", "file"}),
        reference_followup=reference_followup,
    )

    # A task marker may outlive a later, explicitly NEW topic. Do not let a bare
    # option number or generic “continue” jump back to that stale task. A named
    # reference to the older task (e.g. “продолжи игру”) is still allowed to
    # reactivate it, preserving deliberate returns to prior work.
    if hot_work_followup and active_work_pair and active_work_row_index > 0:
        newer_topic_barrier = next((
            row for row in scoped_work_rows[:active_work_row_index]
            if _text(row.get("relation") or "NEW").upper() == "NEW"
        ), None)
        if newer_topic_barrier is not None:
            branch_text = " ".join((
                _text(active_work_branch.get("topic")),
                _text(active_work_branch.get("goal")),
                _text(active_work_branch.get("state_summary")),
                _text(active_work_pair.get("user_text") or active_work_pair.get("user")),
                _text(active_work_pair.get("april_text") or active_work_pair.get("april")),
            ))
            query_branch_overlap = _topic_query_overlap(query, branch_text)
            query_subjects_for_branch = _subject_tokens(query)
            branch_subjects_for_branch = _subject_tokens(branch_text)
            query_branch_subject_overlap = _subject_overlap(
                query_subjects_for_branch, branch_subjects_for_branch
            ) if query_subjects_for_branch else 0.0
            explicit_older_branch_reference = bool(
                query_branch_overlap >= 0.28
                or query_branch_subject_overlap >= 0.50
            )
            if not explicit_older_branch_reference:
                hot_work_followup = False
                hot_work_match_reason = "superseded_by_newer_topic_without_explicit_reference"
                # Keep this older marker in storage, but do not pass it to the
                # current Provider request as if it were still the active task.
                active_work_branch = {}
                active_work_pair = None
                active_work_row_index = -1
                active_work_has_marker = False

    if new_work_root_request:
        hot_work_followup = False
        hot_work_match_reason = "self_contained_new_work_root"
        hot_branch_candidate = False
        semantic_active_branch_intent = False
        repair_active_branch = False
        # A fresh self-contained brief must not inherit an old task through the
        # generic topic index merely because it shares words such as “game”, “code”,
        # or “problem”. History remains stored and searchable on a later explicit
        # recall request; it is simply not sent as context for this new work root.
        topic_index = []
        topic_table_md = ""
    if hot_work_followup:
        # Keep the raw subject-conflict diagnostic, but do not let an imperfect
        # lexical stem veto a choice or an action within a saved work state.
        decision_subject_switch = False
        hot_branch_candidate = True

    # A request to judge an earlier answer must be compared with the task source,
    # not automatically answered from the most recent turn. First estimate whether
    # the active task actually contains the requested topic; if not, search the full
    # retained history for stronger source/condition evidence.
    historical_task_override = False
    historical_task_source_id = ""
    historical_task_anchor: dict[str, Any] | None = None
    answer_verification_request = _looks_like_answer_verification(query)
    if (
        answer_verification_request
        and active_work_pair
        and active_work_branch
        and not pending_clarification
        and not history_request
        and not new_work_root_request
    ):
        active_origin_id = _text(active_work_branch.get("origin_message_id"))
        active_source = " ".join((
            _text(active_work_branch.get("topic")),
            _text(active_work_branch.get("goal")),
            _text(active_work_branch.get("origin_message_id")),
        ))
        active_fit = _topic_query_overlap(query, active_source)
        historical_options = []
        for source_row in all_rows:
            source_id = _text(source_row.get("message_id"))
            if not source_id or source_id in {
                _text(active_work_pair.get("message_id")), active_origin_id,
            }:
                continue
            source_topic = " ".join((
                _topic_label(source_row), _row_subject_text(source_row),
                _compact_memory_summary(source_row),
                _text(source_row.get("user_text") or source_row.get("user")),
                _text(source_row.get("april_text") or source_row.get("april")),
            ))
            topic_fit = _topic_query_overlap(query, source_topic)
            if topic_fit < 0.18 or topic_fit < active_fit + 0.10:
                continue
            scored_source = candidate_match_by_id.get(source_id) or _candidate_score(
                query, source_row,
                dialog_id=str(dialog_id or ""),
                conversation_id=str(conversation_id or ""),
                reference_followup=True,
                query_modalities=query_modalities,
            )
            # Topic/condition overlap dominates generic turn similarity; the latter
            # only breaks ties between two candidates that mention the requested task.
            score = topic_fit + 0.05 * float(scored_source.get("score") or 0)
            historical_options.append((score, topic_fit, source_row, scored_source))
        if historical_options:
            historical_options.sort(key=lambda item: (
                item[0], item[1], float(item[2].get("created_at") or 0),
                int(item[2].get("turn_index") or 0),
            ), reverse=True)
            _, best_historical_fit, historical_row, historical_candidate = historical_options[0]
            if best_historical_fit >= active_fit + 0.10:
                historical_task_override = True
                historical_task_source_id = _text(historical_row.get("message_id"))
                historical_task_anchor = historical_candidate

                # Reactivate the source selected from history. Without this step the
                # answer may be grounded correctly once, but the next turn snaps back
                # to the newer task. Keep this state inside the existing dialogue row.
                historical_profile = _infer_active_work_branch(historical_row)
                if not historical_profile.get("active"):
                    historical_user = _text(historical_row.get("user_text") or historical_row.get("user"))
                    historical_answer = _text(historical_row.get("april_text") or historical_row.get("april"))
                    historical_kind = "problem_solving" if re.search(
                        r"(?:загадк|головолом|riddle|puzzle|quiz|задач|пример|решени|уравнен|формул)",
                        " ".join((historical_user, historical_answer)).lower(),
                    ) else "active_task"
                    historical_profile = {
                        "active": True, "priority": "HOT_TASK_FIRST", "kind": historical_kind,
                        "work_id": "work:" + historical_task_source_id,
                        "topic": _topic_label(historical_row) or historical_user[:240],
                        "goal": historical_user[:500],
                        "state_summary": _text(historical_row.get("memory_summary") or historical_answer)[:800],
                        "last_action": historical_user[:240],
                        "expects_choice": _assistant_expects_user_input(historical_answer),
                        "source_message_id": historical_task_source_id,
                        "origin_message_id": historical_task_source_id,
                        "last_message_id": historical_task_source_id,
                        "dialog_id": _text(historical_row.get("dialog_id")),
                        "conversation_id": _text(historical_row.get("conversation_id")),
                    }
                historical_kind = _text(historical_profile.get("kind") or "active_task")
                historical_origin_id = _text(historical_profile.get("origin_message_id"))
                historical_origin_row = next((row for row in all_rows if _text(row.get("message_id")) == historical_origin_id), None)
                historical_origin_profile = _infer_active_work_branch(historical_origin_row) if historical_origin_row else {}
                historical_origin_valid = bool(
                    historical_origin_row
                    and _is_active_work_root_candidate(historical_origin_row, historical_origin_profile, historical_kind)
                )
                if not historical_origin_valid:
                    historical_index = next((i for i, row in enumerate(scoped_work_rows)
                                              if _text(row.get("message_id")) == historical_task_source_id), -1)
                    recovered_historical_root = None
                    if historical_index >= 0:
                        for root_row in scoped_work_rows[historical_index + 1:]:
                            root_profile = _infer_active_work_branch(root_row)
                            if _is_active_work_root_candidate(root_row, root_profile, historical_kind):
                                root_id = _text(root_row.get("message_id"))
                                root_text = " ".join((_topic_label(root_row), _row_subject_text(root_row)))
                                if root_id and _topic_query_overlap(query, root_text) >= 0.12:
                                    recovered_historical_root = root_row
                                    break
                    if recovered_historical_root is not None:
                        historical_origin_id = _text(recovered_historical_root.get("message_id"))
                        historical_root_user = _text(recovered_historical_root.get("user_text") or recovered_historical_root.get("user"))
                        historical_root_topic = _topic_label(recovered_historical_root) or historical_root_user
                        if historical_root_topic:
                            historical_profile["topic"] = historical_root_topic[:240]
                        if historical_root_user:
                            historical_profile["goal"] = historical_root_user[:500]
                    else:
                        historical_origin_id = historical_task_source_id
                historical_profile.update({
                    "active": True,
                    "priority": "HOT_TASK_FIRST",
                    "work_id": "work:" + historical_origin_id,
                    "origin_message_id": historical_origin_id,
                    "source_message_id": historical_origin_id,
                    "last_message_id": historical_task_source_id,
                    "last_action": _text(historical_row.get("user_text") or historical_row.get("user"))[:240],
                    "state_summary": _text(historical_row.get("memory_summary") or historical_row.get("april_text") or historical_row.get("april"))[:800],
                    "dialog_id": _text(historical_row.get("dialog_id")),
                    "conversation_id": _text(historical_row.get("conversation_id")),
                })
                active_work_pair = historical_row
                active_work_branch = historical_profile
                hot_work_followup = True
                hot_work_match_reason = "historical_task_reactivated"
                hot_branch_candidate = True
                semantic_active_branch_intent = True
                decision_subject_switch = False
                repair_active_branch = False
    # A bare topic pointer such as “про стих” may continue only when the 24-hour
    # database search found a matching source topic. Do not let recency attach it
    # to an unrelated latest turn just because its wording is short.
    if topic_reference_fragment and not topic_pointer_match:
        hot_branch_candidate = False
    continuation = False
    if pending_clarification and not new_topic_request:
        continuation = True
    elif history_request or new_topic_request or new_work_root_request:
        continuation = False
    elif hot_work_followup:
        # A confirmed in-task choice/action outranks the generic attachment gate.
        # This allows voice replies and linked image/file edits to continue a saved
        # task, while _hot_work_followup_candidate rejects unreferenced attachments.
        continuation = True
    elif has_new_attachment and not explicit_attachment_followup:
        continuation = False
    elif _is_section_request(query) and _explicit_section_number(query) is not None and rows:
        # A numbered section reference is a history pointer even when it contains
        # no topic nouns (e.g. "пункт 8"). Search memory instead of classifying it NEW.
        continuation = True
    elif (
        latest_same_dialog
        and bool(query_interpretation.get("requires_memory"))
        and _text(query_interpretation.get("topic_reference")) == "PREVIOUS_ASSISTANT_ANSWER"
    ):
        continuation = True
    elif semantic_active_branch_intent and not decision_subject_switch:
        # A context-dependent interpretation may suggest continuation, but an
        # independently named, conflicting subject wins unless a grounded topic
        # pointer or correction already resolved it to the prior branch.
        continuation = True
    elif repair_active_branch:
        # Corrections and bare acknowledgements are discourse moves attached to the
        # active exchange. Do not let a rejected entity or a lexical score pull them
        # into an unrelated older topic.
        continuation = True
    elif hot_branch_candidate and not decision_subject_switch:
        # Only ambiguous turns that pass the hot-branch relevance check may continue
        # by default. Missing subject words alone are not enough to force CONTINUE.
        continuation = True
    elif latest_same_dialog and reference_followup and not decision_subject_switch:
        continuation = True
    elif latest_same_dialog and marker and len(_tokens(query)) <= 14 and not decision_subject_switch:
        continuation = True
    elif explicit_topic_hits and not decision_subject_switch and (
        reference_followup or _is_section_request(query) or _looks_like_topic_correction(query) or topic_reference_fragment
    ):
        continuation = True
    elif same_dialog_semantic and not decision_subject_switch and not (topic_reference_fragment and not topic_pointer_match):
        continuation = True
    relation = "CONTINUE" if continuation else "NEW"

    # A detailed, self-contained NEW_INFORMATION request must not inherit a
    # previous turn merely because lexical ranking found the same entity.  This
    # is especially important when pronouns ("его", "она", "как он выглядел")
    # refer to the subject introduced inside the current message itself.
    low_query = _text(query).lower().replace("ё", "е")
    explicit_prior_pointer = bool(re.search(
        r"(?:\bподробнее\b|\bрасскажи\s+(?:мне\s+)?больше\b|\bпродолж\w*\b|"
        r"\bдальше\b|\bеще\b|\bпредыдущ\w*\b|\bпрошл\w*\b|\bпрежн\w*\b|"
        r"\bверни\w*\b|\bвосстанови\w*\b|\bповтори\w*\b|\bсохранен\w*\b|"
        r"\bвернись\s+к\b|\bкак\s+(?:мы\s+)?обсуждали\b|"
        r"\bиз\s+истории\b|\bкак\s+раньше\b|\bкак\s+выше\b|\bвыше\b|"
        r"\bпо\s+этим\b|\bпо\s+прежним\s+значени\w*\b|\bпо\s+старым\s+значени\w*\b|"
        r"\bте\s+же\b|\bэту\s+таблиц\w*\b|\bэта\s+таблиц\w*\b|"
        r"\bэтот\s+график\b|\bэтот\s+уравнен\w*\b|\bэту\s+формул\w*\b|"
        r"\bэту\s+задач\w*\b)",
        low_query,
    ))
    self_contained_new_information = bool(
        interpreted_intent == "NEW_INFORMATION"
        and not bool(query_interpretation.get("requires_memory"))
        and not history_request
        and not resume_anchor_row
        and not pending_clarification
        and not new_topic_request
        and not query_modalities
        and len(_semantic_tokens(query)) >= 4
        and len(low_query) >= 28
        and not marker
        and not _is_section_request(query)
        and not _looks_like_topic_correction(query)
        and not repair_active_branch
        and not semantic_active_branch_intent
        and not explicit_prior_pointer
        and not hot_work_followup
        and (bool(query_subjects) or not reference_followup)
    )
    if self_contained_new_information:
        # Search results remain available for diagnostics/ranking, but are not a
        # valid dialogue continuation and must not be forwarded to the Provider.
        relation = "NEW"
        continuation = False

    # A repair is anchored to evidence in the current dialog, not to an older
    # cross-history topic that happens to share a named entity. Compare both USER
    # and APRIL sides so the challenged answer can still be found when the user's
    # message does not repeat the answer's subject; otherwise use the latest turn.
    anchor: dict[str, Any] | None = None
    if historical_task_override and historical_task_anchor:
        anchor = historical_task_anchor
    elif hot_work_followup and active_work_pair:
        # The work branch is chosen before generic score ordering. A high lexical
        # score from an older topic must not replace the active task's live state.
        active_work_id = _text(active_work_pair.get("message_id"))
        anchor = candidate_match_by_id.get(active_work_id)
        if anchor is None:
            anchor = _candidate_score(
                query, active_work_pair,
                dialog_id=str(dialog_id or ""),
                conversation_id=str(conversation_id or ""),
                reference_followup=True,
                query_modalities=query_modalities,
            )
    elif repair_active_branch and latest_same_dialog:
        repair_candidates = []
        for candidate in matches:
            if not candidate.get("same_dialog"):
                continue
            candidate_text = " ".join((
                _text(candidate.get("topic")),
                _text(candidate.get("user") or candidate.get("user_text")),
                _text(candidate.get("april") or candidate.get("april_text")),
            ))
            lexical_fit = _topic_query_overlap(query, candidate_text)
            semantic_fit = max(
                float(candidate.get("context") or 0),
                float(candidate.get("entity_overlap") or 0),
                float(candidate.get("answer_overlap") or 0),
                float(candidate.get("user_overlap") or 0),
                float(candidate.get("subject_overlap") or 0),
            )
            # A correction may name entities that were absent from the user's last
            # message but present in April's answer (e.g. Paris after Constantinople).
            # Compare both sides of the canonical pair; do not discard the exact
            # challenged answer just because it conflicts with a newer unrelated turn.
            row_subjects = set(_row_subject_tokens(candidate))
            subject_evidence = _subject_overlap(query_subjects, row_subjects) if query_subjects else 0.0
            evidence_fit = max(lexical_fit, semantic_fit, subject_evidence)
            if evidence_fit > 0.0:
                repair_candidates.append((
                    evidence_fit, subject_evidence, semantic_fit,
                    float(candidate.get("created_at") or 0), candidate,
                ))
        if query_subjects and repair_candidates:
            repair_candidates.sort(key=lambda entry: (entry[0], entry[1], entry[2], entry[3]), reverse=True)
            # Use same-dialog evidence only when it really mentions the challenge;
            # otherwise remain on the newest active exchange instead of a weak hit.
            if repair_candidates[0][0] >= 0.16 and (
                repair_candidates[0][1] >= 0.10 or repair_candidates[0][0] >= 0.34
            ):
                anchor = repair_candidates[0][4]
        if anchor is None:
            anchor = latest_same_dialog
    forced_section: dict[str, Any] = {}
    clarification_resolution: dict[str, Any] = {}
    clarification_needed = False
    clarification_options: list[dict[str, Any]] = []
    pending_for_next_turn: dict[str, Any] = {}

    pending_rejected = bool(pending_clarification and _looks_like_clarification_rejection(query))
    if pending_clarification and (not new_topic_request or pending_rejected):
        original_pending_request = _text(pending_clarification.get("original_request"))
        if pending_resolved and not pending_rejected:
            # Number/title choice matched the offered clarification. An explicit
            # rejection always bypasses the offered list and starts a wider search. Preserve the
            # initial request and continue from the exact stored section.
            forced_section = dict(pending_option)
            clarification_resolution = {
                "status": "resolved_from_options",
                "original_request": original_pending_request,
                "clarification_reply": _text(query)[:480],
                "selected_section": forced_section,
            }
            source_id = _text(forced_section.get("message_id"))
            source_row = next((row for row in all_rows if _text(row.get("message_id")) == source_id), None)
            if source_row is not None:
                anchor = _candidate_score(
                    original_pending_request or query, source_row,
                    dialog_id=str(dialog_id or ""), reference_followup=True,
                    query_modalities=query_modalities,
                )
            relation = "CONTINUE"
        else:
            # Never re-emit an unresolved prompt verbatim. Treat the user's
            # reply as a search hint and search every stored topic/section in the
            # authenticated 24-hour window, not just the three offered choices.
            recovery_query = _clarification_target_text(query)
            recovered = _rank_sections_across_history(recovery_query, all_rows, limit=16)
            top = recovered[0] if recovered else {}
            second_score = float(recovered[1].get("score") or 0) if len(recovered) > 1 else 0.0
            top_score = float(top.get("score") or 0)
            recovered_topic = _text(top.get("topic"))
            top_is_section = bool(_text(top.get("heading")) and _text(top.get("heading")).casefold() != recovered_topic.casefold())
            clear_match = bool(
                top
                and top_score >= (0.43 if top_is_section else 0.47)
                and (len(recovered) == 1 or top_score - second_score >= 0.055
                     or float(top.get("topic_overlap") or 0) >= 0.72)
            )

            if clear_match:
                forced_section = dict(top)
                clarification_resolution = {
                    "status": "resolved_by_history_search",
                    "original_request": original_pending_request,
                    "clarification_reply": _text(query)[:480],
                    "search_query": recovery_query[:360],
                    "selected_section": forced_section,
                }
                source_id = _text(forced_section.get("message_id"))
                source_row = next((row for row in all_rows if _text(row.get("message_id")) == source_id), None)
                if source_row is not None:
                    anchor = _candidate_score(
                        recovery_query or original_pending_request or query, source_row,
                        dialog_id=str(dialog_id or ""), reference_followup=True,
                        query_modalities=query_modalities,
                    )
                relation = "CONTINUE"
            else:
                # Dismiss stale menu state. A failed match becomes a normal
                # conversational turn with a gentle recovery instruction; a later
                # user hint is searched from scratch rather than trapped here.
                target_tokens = _semantic_tokens(recovery_query) - _CLARIFICATION_META_NOISE
                status = "topic_not_found" if pending_rejected and len(target_tokens) >= 2 else "needs_more_detail"
                clarification_resolution = {
                    "status": status,
                    "original_request": original_pending_request,
                    "clarification_reply": _text(query)[:480],
                    "search_query": recovery_query[:360],
                    "selected_section": {},
                }
                non_pending_same_dialog = [
                    item for item in matches
                    if item.get("same_dialog") and not item.get("is_pending_clarification")
                ]
                fallback_match = max(
                    non_pending_same_dialog,
                    key=lambda item: (float(item.get("created_at") or 0), int(item.get("turn_index") or 0)),
                    default=None,
                )
                if fallback_match is not None:
                    anchor = fallback_match
                relation = "CONTINUE"
        # Any reply to a pending clarification is now either resolved, searched
        # globally, or handed back to normal dialogue. It must not create another
        # local clarification from the old options.
    elif relation == "CONTINUE" and rows:
        if repair_active_branch and latest_same_dialog:
            if anchor is None:
                anchor = latest_same_dialog
        elif not query_subjects and latest_same_dialog:
            # For an underspecified turn, prefer role-aligned evidence when available.
            # Otherwise compare the actual topical evidence with the active turn; if
            # neither gives a clear relative preference, stay on the active turn.
            role_aligned = best if best and int(best.get("participant_alignment") or 0) > 0 else None
            if role_aligned:
                anchor = role_aligned
            else:
                def _context_evidence(item: dict[str, Any] | None) -> float:
                    if not isinstance(item, dict):
                        return 0.0
                    return max(
                        float(item.get("context") or 0),
                        float(item.get("entity_overlap") or 0),
                        float(item.get("user_overlap") or 0),
                        float(item.get("answer_overlap") or 0),
                        float(item.get("subject_overlap") or 0),
                        float(item.get("direction") or 0),
                        float(item.get("numeric_anchor_overlap") or 0),
                    )
                best_evidence = _context_evidence(best)
                active_evidence = _context_evidence(latest_same_dialog)
                if best and best_evidence > active_evidence:
                    anchor = best
                else:
                    anchor = latest_same_dialog
        elif explicit_topic_hits and topic_pointer_match:
            chosen_global = explicit_topic_hits[0][1]
            anchor = _candidate_score(query, chosen_global, dialog_id=str(dialog_id or ""), conversation_id=str(conversation_id or ""), reference_followup=reference_followup, query_modalities=query_modalities)
        elif semantic_active_branch_intent and latest_same_dialog:
            # Active-branch continuation prefers a source from this same dialogue.
            # Use a stronger matching same-dialog row when present; otherwise keep
            # the latest active exchange rather than a weak unrelated archive hit.
            same_dialog_candidates = [
                item for item in matches
                if item.get("same_dialog") and not item.get("is_pending_clarification")
                and not item.get("subject_mismatch")
            ]
            same_dialog_best = max(
                same_dialog_candidates,
                key=lambda item: (float(item.get("score") or 0), float(item.get("created_at") or 0), int(item.get("turn_index") or 0)),
                default=None,
            )
            anchor = same_dialog_best or latest_same_dialog
        elif explicit_topic_hits:
            chosen_global = explicit_topic_hits[0][1]
            anchor = _candidate_score(query, chosen_global, dialog_id=str(dialog_id or ""), conversation_id=str(conversation_id or ""), reference_followup=reference_followup, query_modalities=query_modalities)
        elif latest_same_dialog and (reference_followup or marker or short_contextual or _is_section_request(query)):
            topic_overlap_best = max((_topic_query_overlap(query, item.get("topic", "")) for item in matches if item.get("same_dialog")), default=0.0)
            if topic_overlap_best < 0.50:
                anchor = latest_same_dialog
        if anchor is None:
            anchor = best
    else:
        anchor = best if relation == "NEW" else None

    active_topic = (
        _text(query)[:140]
        if new_work_root_request
        else _text((anchor or {}).get("topic")) or _text((latest_same_dialog or {}).get("topic")) or _text(query)[:140]
    )

    selected_for_context: list[dict[str, Any]] = []
    history_selection_method = "not_history_request"
    history_matched_count = 0
    contextual_history_match = False
    if history_request:
        selected_for_context, history_selection_method, history_matched_count = _select_history_context_pairs(
            query, matches, topic_index, all_rows, requested_topic_count=history_limit
        )
        _apr_timing_log(
            "history_pair_selection",
            user_key=_apr_diag_ref(uid), dialog_key=_apr_diag_ref(dialog_id),
            query_key=_apr_diag_ref(query), topic_signal_count=len(_history_query_topic_tokens(query)),
            candidate_match_count=history_matched_count, selected_pairs=len(selected_for_context),
            selection_method=history_selection_method, topic_index_count=len(topic_index),
        )
    elif relation == "CONTINUE":
        if hot_work_followup and active_work_pair:
            # Hot-work selection is a separate first lane: never append a fuzzy
            # neighbor from an older unrelated task (e.g. a previous game).
            anchor_id = _text(active_work_pair.get("message_id"))
            anchor = candidate_match_by_id.get(anchor_id) or anchor or _candidate_score(
                query, active_work_pair, dialog_id=str(dialog_id or ""),
                conversation_id=str(conversation_id or ""), reference_followup=True,
                query_modalities=query_modalities,
            )
            selected_for_context = []
            selected_work_ids: set[str] = set()

            def _append_work_source(source_row: dict[str, Any], candidate: dict[str, Any] | None = None) -> None:
                if not isinstance(source_row, dict):
                    return
                source_id = _text(source_row.get("message_id"))
                if not source_id or source_id in selected_work_ids:
                    return
                compact = _compact_pair(candidate or _candidate_score(
                    query, source_row, dialog_id=str(dialog_id or ""),
                    conversation_id=str(conversation_id or ""), reference_followup=True,
                    query_modalities=query_modalities,
                ))
                raw_user = _text(source_row.get("user_text") or source_row.get("user"))
                raw_april = _text(source_row.get("april_text") or source_row.get("april"))
                if raw_user or raw_april:
                    compact.update({
                        "preserve_source_text": True,
                        "active_work_source": True,
                        "source_user_text": raw_user[:1800],
                        "source_april_text": raw_april[:5200],
                        "source_user_text_chars": len(raw_user),
                        "source_april_text_chars": len(raw_april),
                        "source_user_text_complete": len(raw_user) <= 1800,
                        "source_april_text_complete": len(raw_april) <= 5200,
                        "source_content_complete": len(raw_user) <= 1800 and len(raw_april) <= 5200,
                        "source_text_origin": "dialogue_memory_active_work",
                    })
                selected_for_context.append(compact)
                selected_work_ids.add(source_id)

            # Preserve the whole logical work unit in a bounded form: original
            # specification first, selected intermediate turns next, and the live
            # state last. A task may introduce its actual puzzle/rules in a middle
            # turn, so root + latest alone is not enough for verification requests.
            origin_id = _text(active_work_branch.get("origin_message_id"))
            origin_row = next((
                row for row in all_rows
                if isinstance(row, dict) and _text(row.get("message_id")) == origin_id
            ), None) if origin_id else None
            if origin_row:
                _append_work_source(origin_row)

            # Resolve the task's bounded trace using persisted branch identity when
            # available. For older rows without consistent markers, use only the
            # interval between the active pair and its recovered root, never the
            # entire history; this prevents nearby unrelated topics from leaking in.
            pair_id = _text(active_work_pair.get("message_id"))
            pair_pos = next((i for i, row in enumerate(all_rows)
                             if isinstance(row, dict) and _text(row.get("message_id")) == pair_id), -1)
            origin_pos = next((i for i, row in enumerate(all_rows)
                               if isinstance(row, dict) and _text(row.get("message_id")) == origin_id), -1)
            trace_rows: list[tuple[float, int, dict[str, Any], dict[str, Any] | None]] = []
            work_id = _text(active_work_branch.get("work_id"))
            branch_description = " ".join((
                _text(active_work_branch.get("topic")),
                _text(active_work_branch.get("goal")),
                _text(active_work_branch.get("state_summary")),
            ))
            bounded_indices: set[int] = set()
            if pair_pos >= 0 and origin_pos > pair_pos:
                bounded_indices.update(range(pair_pos + 1, origin_pos))

            for row_index, trace_row in enumerate(all_rows):
                if not isinstance(trace_row, dict):
                    continue
                trace_id = _text(trace_row.get("message_id"))
                if not trace_id or trace_id in selected_work_ids or trace_id in {pair_id, origin_id}:
                    continue
                if _row_is_pending_clarification(trace_row):
                    continue
                # Do not include a neighboring conversation/dialogue just because
                # its words match. Missing identifiers are tolerated for old rows.
                active_dialog = _text(active_work_pair.get("dialog_id"))
                trace_dialog = _text(trace_row.get("dialog_id"))
                active_conversation = _text(active_work_pair.get("conversation_id"))
                trace_conversation = _text(trace_row.get("conversation_id"))
                if active_dialog and trace_dialog and active_dialog != trace_dialog:
                    continue
                if active_conversation and trace_conversation and active_conversation != trace_conversation:
                    continue

                _, trace_response, trace_memory = _response_and_request_records(trace_row)
                trace_meta = trace_response.get("metadata") if isinstance(trace_response.get("metadata"), dict) else {}
                trace_marker = trace_response.get("active_work_branch")
                if not isinstance(trace_marker, dict):
                    trace_marker = trace_meta.get("active_work_branch")
                if not isinstance(trace_marker, dict):
                    trace_marker = trace_memory.get("active_work_branch")
                trace_marker = trace_marker if isinstance(trace_marker, dict) else {}
                marker_same_work = bool(
                    trace_marker.get("active") and (
                        (origin_id and _text(trace_marker.get("origin_message_id")) == origin_id)
                        or (work_id and _text(trace_marker.get("work_id")) == work_id)
                    )
                )
                in_root_interval = row_index in bounded_indices
                if not marker_same_work and not in_root_interval:
                    continue

                trace_user = _text(trace_row.get("user_text") or trace_row.get("user"))
                trace_answer = _text(trace_row.get("april_text") or trace_row.get("april"))
                trace_text = " ".join((trace_user, trace_answer, _topic_label(trace_row)))
                # A distinct self-contained work root marks a boundary. Do not
                # smuggle another task into this trace just because it sits between
                # a stale marker and the recovered origin; only retain such a row
                # when its own marker proves it is the same task.
                trace_profile = _infer_active_work_branch(trace_row)
                distinct_root = bool(
                    trace_id != origin_id
                    and _is_active_work_root_candidate(
                        trace_row, trace_profile, _text(active_work_branch.get("kind"))
                    )
                )
                if distinct_root:
                    # If this row is itself a self-contained root other than the
                    # selected origin, treat it as a hard task boundary even when
                    # an older/corrupt marker says it belongs to the same work.
                    continue
                query_fit = _topic_query_overlap(query, trace_text)
                branch_fit = _topic_query_overlap(trace_text, branch_description)
                # Keep useful intermediate evidence, especially a question or set
                # of alternatives that the user is now asking April to evaluate.
                score = (0.70 * query_fit) + (0.22 * branch_fit) + (0.08 if marker_same_work else 0.0)
                if marker_same_work or query_fit >= 0.08 or branch_fit >= 0.16:
                    candidate = candidate_match_by_id.get(trace_id)
                    trace_rows.append((score, row_index, trace_row, candidate))

            # Always retain one recent turn from the same task, then add the two
            # strongest query-relevant turns. This captures intermediate conditions
            # while keeping token use bounded and avoiding a history-wide prompt.
            trace_rows.sort(key=lambda item: item[1])  # newest-first, as all_rows is
            chosen_trace: dict[str, tuple[float, int, dict[str, Any], dict[str, Any] | None]] = {}
            if trace_rows:
                recent = trace_rows[0]
                chosen_trace[_text(recent[2].get("message_id"))] = recent
            for item in sorted(trace_rows, key=lambda entry: (entry[0], -entry[1]), reverse=True):
                chosen_trace[_text(item[2].get("message_id"))] = item
                if len(chosen_trace) >= 3:
                    break
            # Reverse to chronological order between root and live state.
            chronological_trace = sorted(chosen_trace.values(), key=lambda item: item[1], reverse=True)
            for _, _, trace_row, candidate in chronological_trace:
                _append_work_source(trace_row, candidate)

            # Keep the most recent state as the final context item even when the
            # answer-verification logic selected a prior source row as its anchor.
            _append_work_source(active_work_pair, anchor)
            history_selection_method = (
                "hot_work_branch_root_trace_and_state" if len(selected_for_context) > 2
                else "hot_work_branch_state_and_origin" if len(selected_for_context) > 1
                else "hot_work_branch_state"
            )
        elif repair_active_branch:
            # A correction needs factual evidence, not only the selected topic summary.
            # Start from the best matching answer and add a small same-branch window.
            dialog_candidates = [
                item for item in matches
                if item.get("same_dialog")
                and _text(item.get("dialog_id")) == _text(dialog_id)
                and not item.get("is_pending_clarification")
            ]
            dialog_candidates.sort(key=lambda item: (
                float(item.get("created_at") or 0), int(item.get("turn_index") or 0)
            ))
            anchor_id = _text((anchor or {}).get("message_id"))
            anchor_topic_id = _text((anchor or {}).get("topic_id"))
            anchor_topic_text = _text((anchor or {}).get("topic"))
            anchor_position = next((i for i, item in enumerate(dialog_candidates)
                                    if _text(item.get("message_id")) == anchor_id), -1)

            evidence_items: list[dict[str, Any]] = []
            if anchor:
                evidence_items.append(anchor)

            # Exact topic identity is the strongest neighborhood signal. For older
            # rows without topic IDs, combine semantic overlap with nearby turns in
            # the active exchange. Keep the set bounded so repair does not lock the
            # conversation onto a whole historical branch.
            related_candidates = []
            anchor_subjects = set((anchor or {}).get("subject_terms") or [])
            for item in dialog_candidates:
                item_id = _text(item.get("message_id"))
                if not item_id or item_id == anchor_id:
                    continue
                item_topic_id = _text(item.get("topic_id"))
                item_topic_text = _text(item.get("topic"))
                topic_similarity = (
                    fuzz.token_set_ratio(anchor_topic_text.casefold(), item_topic_text.casefold()) / 100.0
                    if anchor_topic_text and item_topic_text else 0.0
                )
                subject_similarity = _subject_overlap(anchor_subjects, set(item.get("subject_terms") or []))
                query_overlap = _topic_query_overlap(query, " ".join((
                    item_topic_text, _text(item.get("user") or item.get("user_text")),
                    _text(item.get("april") or item.get("april_text")),
                )))
                same_topic_id = bool(anchor_topic_id and item_topic_id and anchor_topic_id == item_topic_id)
                # Time adjacency alone is not evidence of belonging to this task:
                # an unrelated self-contained turn may sit between two related turns.
                # Keep a conflicting row only when topic identity/text or query evidence
                # independently links it back to the repair target.
                if item.get("subject_mismatch") and not same_topic_id and topic_similarity < 0.48 and query_overlap < 0.16:
                    continue
                is_neighbor = False
                if anchor_position >= 0:
                    item_position = next((i for i, candidate in enumerate(dialog_candidates)
                                          if _text(candidate.get("message_id")) == item_id), -1000)
                    if abs(item_position - anchor_position) <= 2:
                        try:
                            delta = abs(float(item.get("created_at") or 0) - float((anchor or {}).get("created_at") or 0))
                        except (TypeError, ValueError):
                            delta = float("inf")
                        is_neighbor = delta <= 20 * 60
                if same_topic_id or topic_similarity >= 0.48 or subject_similarity >= 0.42 or query_overlap >= 0.16 or is_neighbor:
                    relevance = (
                        1.0 * int(same_topic_id)
                        + 0.65 * topic_similarity
                        + 0.55 * subject_similarity
                        + 0.55 * query_overlap
                        + 0.18 * int(is_neighbor)
                    )
                    related_candidates.append((relevance, float(item.get("created_at") or 0), item))
            related_candidates.sort(key=lambda entry: (entry[0], entry[1]), reverse=True)
            for _score, _created_at, item in related_candidates:
                if _text(item.get("message_id")) not in {_text(x.get("message_id")) for x in evidence_items}:
                    evidence_items.append(item)
                if len(evidence_items) >= 4:
                    break

            # If a selected answer directly matches the user's named correction,
            # retain its exact canonical text as evidence (bounded, with completeness
            # flags). A summary alone must not replace what April actually said.
            evidence_items = evidence_items[:4]
            evidence_items.sort(key=lambda item: (
                float(item.get("created_at") or 0), int(item.get("turn_index") or 0)
            ))
            preserve_budget = 3
            for item in evidence_items:
                pair = _compact_pair(item)
                source_user = _text(item.get("user_text") or item.get("user"))
                source_april = _text(item.get("april_text") or item.get("april"))
                if preserve_budget > 0 and source_user and source_april:
                    # These are source excerpts, not summaries. Truncation is explicit.
                    user_cap, april_cap = 1800, 5200
                    pair.update({
                        "preserve_source_text": True,
                        "source_user_text": source_user[:user_cap],
                        "source_april_text": source_april[:april_cap],
                        "source_user_text_chars": len(source_user),
                        "source_april_text_chars": len(source_april),
                        "source_user_text_complete": len(source_user) <= user_cap,
                        "source_april_text_complete": len(source_april) <= april_cap,
                        "source_content_complete": len(source_user) <= user_cap and len(source_april) <= april_cap,
                        "source_text_origin": "dialogue_memory",
                    })
                    preserve_budget -= 1
                selected_for_context.append(pair)
            history_selection_method = "active_branch_repair_evidence"
        else:
            if anchor:
                selected_for_context.append(_compact_pair(anchor))
            # At most one corroborating pair; never forward a pile of unrelated turns.
            anchor_subjects = set((anchor or {}).get("subject_terms") or [])
            anchor_has_values = bool(int((anchor or {}).get("structured_data_richness") or 0) >= 8)
            related_candidates = []
            # A role-aligned factual record is sufficient for a participant-centered
            # lookup. Do not dilute it with neighboring turns that may only report a
            # prior failure to recall that fact (e.g. "I don't see your name").
            related_context_candidates = [] if int((anchor or {}).get("participant_alignment") or 0) > 0 else matches
            for item in related_context_candidates:
                if item.get("is_pending_clarification"):
                    continue
                if not item.get("message_id") or _text(item.get("message_id")) == _text((anchor or {}).get("message_id")):
                    continue
                if bool(query_subjects and item.get("subject_mismatch")):
                    continue
                if bool(item.get("same_dialog")) is False and _text(item.get("dialog_id")) != _text(dialog_id):
                    continue
                topic_similarity = fuzz.token_set_ratio(
                    _text((anchor or {}).get("topic")).casefold(), _text(item.get("topic")).casefold()
                ) / 100.0 if _text((anchor or {}).get("topic")) and _text(item.get("topic")) else 0.0
                item_subjects = set(item.get("subject_terms") or [])
                subject_similarity = _subject_overlap(anchor_subjects, item_subjects)
                structured_richness = int(item.get("structured_data_richness") or 0)
                item_source_alignment = float(item.get("source_data_alignment") or 0)
                # Once the anchor contains the user's original constraints and matching
                # structured values, do not attach a later value-bearing derivative whose
                # own request supplied no numbers. It may represent a mistaken reformatting
                # and otherwise reintroduce the very values the active source corrected.
                if (
                    anchor_has_values
                    and float((anchor or {}).get("source_data_alignment") or 0) >= 0.60
                    and structured_richness >= 8
                    and item_source_alignment < 0.20
                    and int(item.get("turn_index") or 0) > int((anchor or {}).get("turn_index") or 0)
                ):
                    continue
                same_context = (topic_similarity >= 0.65 or subject_similarity >= 0.60
                                or _topic_query_overlap(query, _text(item.get("topic"))) >= 0.50)
                if reference_followup and anchor_subjects and item_subjects and subject_similarity >= 0.60:
                    same_context = True
                if same_context:
                    # If the anchor is a text-only derivative, prefer its nearest source
                    # with the original structured values; otherwise retain relevance rank.
                    provenance_bonus = 0.10 if (not anchor_has_values and structured_richness >= 8) else 0.0
                    related_candidates.append((float(item.get("score") or 0) + provenance_bonus, item))
            if related_candidates:
                related_candidates.sort(key=lambda pair: pair[0], reverse=True)
                selected_for_context.append(_compact_pair(related_candidates[0][1]))

    # A NEW request may still name a topic retained from an earlier dialogue.
    # Keep relation=NEW (no forced continuation), but pass one grounded pair when
    # the topic index confirms a strong topical match.
    if relation == "NEW" and not history_request and not selected_for_context and topic_index and not new_work_root_request:
        lookup_tokens = _history_query_topic_tokens(query)
        top_topic = topic_index[0]
        topic_tokens = _semantic_tokens(_history_topic_text(top_topic))
        topic_overlap = _history_topic_overlap(lookup_tokens, topic_tokens) if lookup_tokens else 0.0
        has_distinctive_query = len(lookup_tokens) >= 2 or any(len(token) >= 7 for token in lookup_tokens)
        if topic_overlap >= 0.50 and (has_distinctive_query or topic_reference_fragment):
            topic_message_id = _text(top_topic.get("message_id"))
            source_row = next((row for row in all_rows if _text(row.get("message_id")) == topic_message_id), None)
            if source_row is not None:
                matched_pair = _candidate_score(
                    query, source_row, dialog_id=str(dialog_id or ""), conversation_id=str(conversation_id or ""),
                    reference_followup=True, query_modalities=query_modalities,
                )
                selected_for_context = [_compact_pair(matched_pair)]
                contextual_history_match = True
                history_selection_method = "semantic_topic_index_match"

    selected_section: dict[str, Any] = {}
    section_anchor_overridden = False
    if forced_section:
        selected_section = dict(forced_section)
    else:
        topic_correction = _looks_like_topic_correction(query) and bool(explicit_topic_hits)
        previous_user_request = _text((latest_same_dialog or {}).get("user")) if topic_correction else ""
        section_query = previous_user_request if previous_user_request and _is_section_request(previous_user_request) else query
        should_select_section = _is_section_request(section_query)
        if relation == "CONTINUE" and anchor and should_select_section:
            # Search the section index of the chosen anchor first; on a correction,
            # keep the user's previous task and only replace the mistaken topic.
            anchor_id = _text(anchor.get("message_id"))
            source_row = next((row for row in all_rows if _text(row.get("message_id")) == anchor_id), None)
            ranked_sections = _rank_sections_for_row(section_query, source_row) if source_row else []
            requested_section_number = _explicit_section_number(section_query)
            if requested_section_number is not None:
                # Section numbers are structural identifiers. Search the active
                # answer first, then the full 24-hour user history; never suggest
                # a nearby numbered section when the requested number is absent.
                exact_local = [item for item in ranked_sections if int(item.get("order") or 0) == requested_section_number]
                if not exact_local and source_row:
                    exact_local = [
                        {
                            "topic": _topic_label(source_row),
                            "heading": _text(section.get("heading"))[:180],
                            "summary": _text(section.get("summary"))[:360],
                            "order": section.get("order"),
                            "message_id": _text(section.get("message_id") or source_row.get("message_id")),
                            "dialog_id": _text(source_row.get("dialog_id")),
                            "conversation_id": _text(source_row.get("conversation_id")),
                            "score": 1.0,
                        }
                        for section in _dialogue_section_map(source_row)
                        if int(section.get("order") or 0) == requested_section_number
                    ]
                if exact_local:
                    ranked_sections = exact_local
                    if len(exact_local) == 1:
                        # Exact section number inside the selected source is a
                        # stronger signal than fuzzy lexical similarity.
                        selected_section = dict(exact_local[0])
                    else:
                        clarification_needed = True
                        clarification_options = exact_local[:3]
                        pending_for_next_turn = {
                            "active": True,
                            "original_request": _text(section_query)[:500],
                            "active_topic": active_topic[:140],
                            "requested_section_number": requested_section_number,
                            "options": [dict(item) for item in clarification_options],
                        }
                else:
                    global_ranked = _rank_sections_across_history(section_query, all_rows, limit=20)
                    exact_global = [item for item in global_ranked if int(item.get("order") or 0) == requested_section_number]
                    if exact_global:
                        top_global = exact_global[0]
                        second_global = float(exact_global[1].get("score") or 0) if len(exact_global) > 1 else 0.0
                        top_global_score = float(top_global.get("score") or 0)
                        global_is_clear = top_global_score >= 0.40 and (
                            len(exact_global) == 1 or top_global_score - second_global >= 0.055
                        )
                        if global_is_clear:
                            selected_section = dict(top_global)
                            forced_section = dict(top_global)
                            target_id = _text(top_global.get("message_id"))
                            target_row = next((row for row in all_rows if _text(row.get("message_id")) == target_id), None)
                            if target_row is not None:
                                anchor = _candidate_score(
                                    section_query, target_row, dialog_id=str(dialog_id or ""),
                                    reference_followup=True, query_modalities=query_modalities,
                                )
                                section_anchor_overridden = True
                        else:
                            clarification_needed = True
                            clarification_options = exact_global[:3]
                    else:
                        # No indexed item has this number. Ask an open, human
                        # follow-up rather than listing unrelated fuzzy matches.
                        clarification_needed = True
                        clarification_options = []
                    if clarification_needed:
                        pending_for_next_turn = {
                            "active": True,
                            "original_request": _text(section_query)[:500],
                            "active_topic": active_topic[:140],
                            "requested_section_number": requested_section_number,
                            "options": [dict(item) for item in clarification_options],
                        }
                    ranked_sections = []
            generic_pointer = _is_generic_section_pointer(section_query)
            if requested_section_number is not None and (selected_section or clarification_needed):
                # The explicit numbered-search branch above owns this request.
                pass
            elif generic_pointer and source_row:
                # A broad phrase such as "подробнее о её применении" does not
                # identify one specific subsection. Prefer sections explicitly
                # about applications/usage; ask locally when several exist.
                source_sections = _dialogue_section_map(source_row)
                application_sections = [item for item in source_sections if _is_application_related_section(item)]
                choice_sections = application_sections or source_sections
                choice_records = [
                    {
                        "topic": _topic_label(source_row),
                        "heading": _text(item.get("heading"))[:180],
                        "summary": _text(item.get("summary"))[:360],
                        "order": item.get("order"),
                        "message_id": _text(item.get("message_id") or source_row.get("message_id")),
                        "dialog_id": _text(source_row.get("dialog_id")),
                        "conversation_id": _text(source_row.get("conversation_id")),
                        "score": 1.0 if application_sections else 0.0,
                    }
                    for item in choice_sections
                ][:8]
                if len(choice_records) >= 2:
                    clarification_needed = True
                    clarification_options = choice_records[:3]
                elif len(choice_records) == 1:
                    selected_section = choice_records[0]
                elif ranked_sections:
                    # Legacy answers may have no formal section index; use the
                    # fuzzy-ranked sections only if a clear winner exists.
                    top = ranked_sections[0]
                    second_score = float(ranked_sections[1].get("score") or 0) if len(ranked_sections) > 1 else 0.0
                    if float(top.get("score") or 0) >= 0.49 and (len(ranked_sections) == 1 or float(top.get("score") or 0) - second_score >= 0.09):
                        selected_section = top
                    else:
                        clarification_needed = True
                        clarification_options = ranked_sections[:3]
                if clarification_needed:
                    pending_for_next_turn = {
                        "active": True,
                        "original_request": _text(section_query)[:500],
                        "active_topic": active_topic[:140],
                        "options": [dict(item) for item in clarification_options],
                    }
            elif ranked_sections:
                top = ranked_sections[0]
                second_score = float(ranked_sections[1].get("score") or 0) if len(ranked_sections) > 1 else 0.0
                if float(top.get("score") or 0) >= 0.49 and (len(ranked_sections) == 1 or float(top.get("score") or 0) - second_score >= 0.09):
                    selected_section = top
                    if topic_correction and previous_user_request:
                        clarification_resolution = {
                            "original_request": previous_user_request[:500],
                            "clarification_reply": _text(query)[:480],
                            "selected_section": selected_section,
                        }
                elif len(ranked_sections) >= 2 and float(top.get("score") or 0) >= 0.34:
                    clarification_needed = True
                    clarification_options = ranked_sections[:3]
                    pending_for_next_turn = {
                        "active": True,
                        "original_request": _text(section_query)[:500],
                        "active_topic": active_topic[:140],
                        "options": [dict(item) for item in clarification_options],
                    }
            if clarification_needed:
                language = _text(next((row.get("language") for row in all_rows if _text(row.get("message_id")) == anchor_id), "ru")).lower().split("-", 1)[0]
                prompt_text = _clarification_prompt(section_query, clarification_options, language if language in {"ru", "uk", "en"} else "ru")
                pending_for_next_turn["prompt"] = prompt_text

    if resume_anchor_row:
        # A deliberate History-card click is authoritative for this turn. Preserve
        # the exact clicked message as the anchor, then attach only rows belonging
        # to its topic vector. A broad dialog_id may cover the entire 24-hour window
        # and must never be treated as proof that every row is relevant.
        anchor = _candidate_score(
            query,
            resume_anchor_row,
            dialog_id=str(dialog_id or resume_anchor_row.get("dialog_id") or ""),
            reference_followup=True,
            query_modalities=query_modalities,
        )
        relation = "CONTINUE"
        active_topic = _text(anchor.get("topic")) or _topic_label(resume_anchor_row) or active_topic
        selected_for_context = [_compact_pair(anchor)]
        anchor_subjects = set(anchor.get("subject_terms") or _row_subject_tokens(resume_anchor_row))
        anchor_topic = _text(anchor.get("topic")) or _topic_label(resume_anchor_row)
        related_vector = []
        anchor_message_id = _text(anchor.get("message_id"))
        # Re-score the 24-hour memory against the selected topic itself, not only
        # against the next short user input (which may be just "continue" or "draw").
        for candidate_row in all_rows:
            candidate_message_id = _text(candidate_row.get("message_id"))
            if not candidate_message_id or candidate_message_id == anchor_message_id or _row_is_pending_clarification(candidate_row):
                continue
            item = _candidate_score(
                anchor_topic,
                candidate_row,
                dialog_id=str(dialog_id or resume_anchor_row.get("dialog_id") or ""),
                reference_followup=True,
                query_modalities=query_modalities,
            )
            item_subjects = set(item.get("subject_terms") or _row_subject_tokens(candidate_row))
            subject_similarity = _subject_overlap(anchor_subjects, item_subjects)
            item_topic = _text(item.get("topic")) or _topic_label(candidate_row)
            topic_similarity = fuzz.token_set_ratio(anchor_topic.casefold(), item_topic.casefold()) / 100.0 if anchor_topic and item_topic else 0.0
            query_similarity = _topic_query_overlap(anchor_topic, item_topic) if anchor_topic and item_topic else 0.0
            similarity = max(topic_similarity, subject_similarity, query_similarity)
            if topic_similarity >= 0.45 or query_similarity >= 0.35 or subject_similarity >= 0.30:
                related_vector.append((similarity, float(candidate_row.get("created_at") or 0), item))
        related_vector.sort(key=lambda value: (value[0], value[1]), reverse=True)
        for _score, _created_at, item in related_vector[:3]:
            selected_for_context.append(_compact_pair(item))
        _apr_timing_log(
            "history_resume_vector",
            user_key=_apr_diag_ref(uid),
            dialog_key=_apr_diag_ref(dialog_id),
            anchor_message_key=_apr_diag_ref(anchor_message_id),
            vector_candidates=len(related_vector),
            selected_pairs=len(selected_for_context),
            selection_method="topic_vector" if len(selected_for_context) > 1 else "selected_pair_anchor",
        )
        selected_section = {}
        # This is a message anchor, not a forced section; do not reset the vector
        # selection below. The resume key remains active until the first accepted turn.
        section_anchor_overridden = False
        clarification_needed = False
        clarification_options = []
        pending_for_next_turn = {}
        clarification_resolution = {}
        # Keep the chosen pair first in the candidate list while leaving the
        # remaining 24-hour candidates available for normal cross-topic recall.
        matches = [anchor] + [item for item in matches if _text(item.get("message_id")) != anchor_message_id]

    if section_anchor_overridden and anchor:
        active_topic = _text(anchor.get("topic")) or active_topic
        selected_for_context = [_compact_pair(anchor)]

    def _attach_topic_provenance(record: Any) -> Any:
        """Bind a selected pair/section to the topic and source message it came from."""
        if not isinstance(record, dict):
            return record
        source_id = _text(record.get("source_message_id") or record.get("message_id"))
        matching_topic = None
        matching_section = None
        for topic in topic_index:
            if not isinstance(topic, dict):
                continue
            topic_message_ids = {_text(item) for item in (topic.get("message_ids") or []) if _text(item)}
            topic_message_ids.update({_text(topic.get("message_id")), _text(topic.get("origin_message_id"))})
            section_match = next((section for section in (topic.get("sections") or [])
                                  if isinstance(section, dict) and source_id and source_id in {
                                      _text(section.get("source_message_id")), _text(section.get("message_id"))
                                  }), None)
            if (source_id and source_id in topic_message_ids) or section_match:
                matching_topic, matching_section = topic, section_match
                break
        if matching_topic:
            topic_id_value = _text(matching_topic.get("topic_id"))
            origin_id_value = _text(matching_topic.get("origin_message_id"))
            if topic_id_value and not _text(record.get("topic_id")):
                record["topic_id"] = topic_id_value
            # _compact_pair historically defaulted origin_message_id to the current
            # message. Replace that fallback when the topic index knows the true root.
            if origin_id_value and (not _text(record.get("origin_message_id")) or _text(record.get("origin_message_id")) == source_id):
                record["origin_message_id"] = origin_id_value
            if origin_id_value and (not _text(record.get("topic_origin_message_id")) or _text(record.get("topic_origin_message_id")) == source_id):
                record["topic_origin_message_id"] = origin_id_value
            if matching_topic.get("origin_turn") is not None and record.get("origin_turn") in (None, "", 0):
                record["origin_turn"] = matching_topic.get("origin_turn")
            if source_id and not _text(record.get("source_message_id")):
                record["source_message_id"] = source_id
            if matching_section:
                record.setdefault("section_heading", matching_section.get("heading"))
                record.setdefault("section_summary", matching_section.get("summary"))
                record.setdefault("section_order", matching_section.get("order"))
        nested_sections = record.get("sections")
        if isinstance(nested_sections, list):
            for section in nested_sections:
                if not isinstance(section, dict):
                    continue
                section_source = _text(section.get("source_message_id") or section.get("message_id"))
                for topic in topic_index:
                    if not isinstance(topic, dict):
                        continue
                    found = next((source for source in (topic.get("sections") or [])
                                  if isinstance(source, dict) and section_source and section_source in {
                                      _text(source.get("source_message_id")), _text(source.get("message_id"))
                                  }), None)
                    if found:
                        if not _text(section.get("topic_id")):
                            section["topic_id"] = topic.get("topic_id")
                        if not _text(section.get("topic_origin_message_id")):
                            section["topic_origin_message_id"] = topic.get("origin_message_id")
                        if not _text(section.get("source_message_id")):
                            section["source_message_id"] = section_source
                        if not _text(section.get("heading")):
                            section["heading"] = found.get("heading")
                        if not _text(section.get("summary")):
                            section["summary"] = found.get("summary")
                        break
        return record

    for selected_pair in selected_for_context:
        _attach_topic_provenance(selected_pair)
    _attach_topic_provenance(selected_section)

    # Keep the actual PostgreSQL source pair for a selected poem/verse or other
    # authored text when the user is referring to that branch. Compact summaries
    # are useful for search, but cannot replace the source when discussing wording,
    # reactions, edits, or whether a text was preserved correctly.
    preserve_text_request = bool(re.search(
        r"(?:стих\w*|поэм\w*|сонет\w*|лирик\w*|текст\w*|строк\w*|"
        r"дословн\w*|целиком|полностью|повтори|перечитай|как ты написал|что ты написал|"
        r"poem\w*|poetr\w*|verse\w*|sonnet\w*|the text|word for word|verbatim|full text)",
        _text(query).lower().replace("ё", "е"),
    ))
    source_sensitive_acts = {
        "REFERENTIAL_CONTINUATION", "EXPLANATION_REQUEST", "CLARIFICATION_REQUEST",
        "CORRECTION_OR_REVISION", "FRUSTRATION_OR_DISSATISFACTION", "REVISION_REQUEST",
        "INFORMATION_QUESTION", "CONTINUATION_REQUEST",
    }
    needs_textual_evidence = bool(
        preserve_text_request or topic_reference_fragment or reference_followup
        or _text(query_interpretation.get("speech_act")).upper() in source_sensitive_acts
    )
    if (
        relation == "CONTINUE" or contextual_history_match
        or (history_request and (preserve_text_request or topic_reference_fragment or reference_followup))
    ) and needs_textual_evidence:
        source_by_id = {
            _text(row.get("message_id")): row for row in all_rows
            if isinstance(row, dict) and _text(row.get("message_id"))
        }
        for selected_pair in selected_for_context[:2]:
            if not isinstance(selected_pair, dict):
                continue
            source_id = _text(selected_pair.get("source_message_id") or selected_pair.get("message_id"))
            source = source_by_id.get(source_id)
            if not source:
                continue
            topic_and_text = " ".join((
                _text(selected_pair.get("topic")),
                _text(source.get("user_text") or source.get("user")),
                _text(source.get("april_text") or source.get("april")),
            )).lower().replace("ё", "е")
            is_authored_text = bool(re.search(
                r"(?:стих\w*|поэм\w*|сонет\w*|лирик\w*|рифм\w*|куплет\w*|"
                r"poem\w*|poetr\w*|verse\w*|sonnet\w*|lyrics)", topic_and_text
            ))
            # Require both a real selected DB source and a textual reference in
            # either the query or that source. This is not a global history dump.
            if not is_authored_text:
                continue
            raw_user = _text(source.get("user_text") or source.get("user"))
            raw_april = _text(source.get("april_text") or source.get("april"))
            selected_pair["preserve_source_text"] = True
            selected_pair["source_user_text"] = raw_user[:1800]
            selected_pair["source_april_text"] = raw_april[:5200]
            selected_pair["source_user_text_chars"] = len(raw_user)
            selected_pair["source_april_text_chars"] = len(raw_april)
            selected_pair["source_user_text_complete"] = len(raw_user) <= 1800
            selected_pair["source_april_text_complete"] = len(raw_april) <= 5200
            selected_pair["source_content_complete"] = len(raw_user) <= 1800 and len(raw_april) <= 5200
            selected_pair["source_text_origin"] = "dialogue_memory"
    if clarification_options:
        clarification_options = [_attach_topic_provenance(dict(option)) for option in clarification_options]

    def _topic_time_label(value: Any) -> str:
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc).astimezone(ZoneInfo("Europe/Kyiv")).strftime("%d.%m.%Y %H:%M")
        except (TypeError, ValueError, OverflowError, OSError):
            return "—"

    topic_table_lines = [
        "| # | Тема | Описание | Последний запрос | Обновлено (Киев) | Источник | Ходы |",
        "|---:|---|---|---|---|---|---:|",
    ]
    topic_table_source = history_topics if history_request and history_topics else topic_index[:min(3, len(topic_index))]
    for item in topic_table_source[:history_limit if history_request else 3]:
        topic = str(item.get("topic") or "—").replace("|", "/").replace("\n", " ")
        summary = str(item.get("summary") or "—").replace("|", "/").replace("\n", " ")[:180]
        last_question = str(item.get("last_question") or "—").replace("|", "/").replace("\n", " ")[:140]
        last_at = _topic_time_label(item.get("last_at"))
        origin_turn = item.get("origin_turn") or "—"
        topic_table_lines.append(
            f"| {item.get('number', '—')} | {topic} | {summary} | {last_question} | {last_at} | ход {origin_turn} | {item.get('turns', '—')} |"
        )
    topic_table_md = "\n".join(topic_table_lines)

    anchor_payload = _compact_pair(anchor) if relation == "CONTINUE" and anchor else {}
    _attach_topic_provenance(anchor_payload)
    # Source retrieval is tracked independently from the dialogue relation: a new
    # operation may still retrieve a named historical source, and a continuation
    # should cite only the branch-specific records actually selected above.
    if history_request:
        source_retrieval_strategy = "DIALOGUE_HISTORY_SEARCH"
    elif selected_section:
        source_retrieval_strategy = "EXACT_SOURCE_SECTION"
    elif relation == "CONTINUE" and hot_work_followup:
        source_retrieval_strategy = "HOT_WORK_BRANCH_SOURCE"
    elif relation == "CONTINUE" and semantic_active_branch_intent:
        source_retrieval_strategy = "ACTIVE_BRANCH_SOURCE"
    elif relation == "CONTINUE" and selected_for_context:
        source_retrieval_strategy = "RELEVANT_DIALOGUE_SOURCE"
    elif contextual_history_match and selected_for_context:
        source_retrieval_strategy = "NAMED_HISTORY_SOURCE_WITH_NEW_OPERATION"
    elif selected_for_context:
        source_retrieval_strategy = "RANKED_MEMORY_SOURCE"
    else:
        source_retrieval_strategy = "CURRENT_REQUEST_NO_MEMORY_SOURCE"

    active_branch_descriptor = {
        "status": "NONE" if new_work_root_request else ("ACTIVE" if relation == "CONTINUE" and latest_same_dialog else ("AVAILABLE" if latest_same_dialog else "NONE")),
        "topic": _text(query)[:240] if new_work_root_request else _text((anchor or {}).get("topic") or (latest_same_dialog or {}).get("topic"))[:240],
        "message_id": "" if new_work_root_request else _text((anchor or {}).get("message_id") or (latest_same_dialog or {}).get("message_id"))[:120],
        "dialog_id": "" if new_work_root_request else _text((anchor or {}).get("dialog_id") or (latest_same_dialog or {}).get("dialog_id"))[:120],
        "topic_id": "" if new_work_root_request else _text((anchor or {}).get("topic_id") or (latest_same_dialog or {}).get("topic_id"))[:100],
        "topic_origin_message_id": "" if new_work_root_request else _text((anchor or {}).get("topic_origin_message_id") or (latest_same_dialog or {}).get("topic_origin_message_id"))[:120],
        "semantic_intent_match": bool(semantic_active_branch_intent),
        "subject_conflict_detected": bool(active_subject_conflict),
        "branch_preserved": bool(not new_work_root_request and relation == "CONTINUE" and latest_same_dialog),
        "hot_work_match": bool(hot_work_followup),
        "hot_work_match_reason": _text(hot_work_match_reason)[:80],
        "work_kind": _text(active_work_branch.get("kind"))[:60],
        "work_id": _text(active_work_branch.get("work_id"))[:120] if hot_work_followup else "",
    }
    source_retrieval_descriptor = {
        "strategy": source_retrieval_strategy,
        "method": _text(history_selection_method or "unspecified")[:100],
        "anchor_message_id": _text((anchor or {}).get("message_id"))[:120],
        "selected_message_ids": [
            _text(item.get("message_id"))[:120]
            for item in selected_for_context[:5]
            if isinstance(item, dict) and _text(item.get("message_id"))
        ],
        "contextual_history_match": bool(contextual_history_match),
        "source_count": len(selected_for_context),
    }

    result = {
        "engine": "premium_state_manager_topic_section_search_v12_task_root_and_source_verification",
        "authenticated": True,
        "window_hours": DIALOGUE_WINDOW_HOURS,
        "dialog_id": str(dialog_id or ""),
        "conversation_id": str(conversation_id or ""),
        "query": str(query or ""),
        "context_signature": context_signature,
        "active_subject_conflict": bool(active_subject_conflict),
        "semantic_subject_switch": bool(semantic_subject_switch),
        "decision_subject_switch": bool(decision_subject_switch),
        "topic_reference_fragment": bool(topic_reference_fragment),
        "topic_pointer_match": bool(topic_pointer_match),
        "self_contained_subject_switch": bool(self_contained_subject_switch),
        "total_pairs": len(rows),
        "candidate_count": len(matches),
        "relation": relation,
        "active_branch_repair": bool(repair_active_branch),
        "active_branch": active_branch_descriptor,
        "active_work_branch": ({
            **active_work_branch,
            "active": True,
            "matched_this_turn": bool(hot_work_followup),
            "match_reason": _text(hot_work_match_reason)[:80],
            "candidate_message_id": _text(active_work_pair.get("message_id"))[:120] if active_work_pair else "",
            "priority": "HOT_TASK_FIRST",
        } if active_work_branch and relation == "CONTINUE" and not new_work_root_request else {}),
        "hot_work_followup": bool(hot_work_followup),
        "hot_work_match_reason": _text(hot_work_match_reason)[:80],
        "new_work_root_request": bool(new_work_root_request),
        "historical_task_override": bool(historical_task_override),
        "historical_task_source_id": _text(historical_task_source_id),
        "user_operation": user_operation,
        "source_retrieval": source_retrieval_descriptor,
        "previous_answer_reference": bool(pragmatic_features.get("previous_answer_reference") or query_interpretation.get("previous_answer_reference")),
        "factual_verification_request": bool(pragmatic_features.get("factual_verification_request") or query_interpretation.get("factual_verification_request")),
        "explicit_topic_switch": bool(query_interpretation.get("explicit_topic_switch")),
        "reason": (
            "explicit_history_resume" if resume_anchor_row
            else "clarification_resolved" if clarification_resolution and _text(clarification_resolution.get("status")).startswith("resolved")
            else "clarification_researched" if clarification_resolution
            else "clarification_pending" if clarification_needed
            else "history_request" if history_request
            else "hot_work_branch_first" if hot_work_followup
            else "semantic_history_match" if contextual_history_match
            else "self_contained_new_information" if self_contained_new_information
            else "active_branch_repair_evidence" if relation == "CONTINUE" and anchor and repair_active_branch
            else "semantic_active_branch_intent" if relation == "CONTINUE" and semantic_active_branch_intent
            else "named_topic_match" if explicit_topic_hits and relation == "CONTINUE"
            else "hot_branch_ambiguous_followup" if relation == "CONTINUE" and anchor and hot_branch_candidate
            else "underspecified_turn_context" if relation == "CONTINUE" and anchor and not query_subjects
            else "active_topic_default" if relation == "CONTINUE" and anchor
            else "new_request" if relation == "NEW"
            else "semantic_memory_match"
        ),
        "relation_confidence": 1.0 if resume_anchor_row else round(float((anchor or best or {}).get("score") or (0.60 if relation == "CONTINUE" else 0.0)), 6),
        "continuation_marker": marker,
        "referential_followup": reference_followup,
        "history_request": history_request,
        "contextual_history_match": contextual_history_match,
        "matched_topic_count": len(topic_index) if (history_request or contextual_history_match or relation == "CONTINUE") else 0,
        "requested_topic_count": history_limit,
        "minimum_topic_count": history_minimum if history_request else 0,
        "time_window": parsed_window if parsed_window.get("has_constraint") else {},
        "time_filter": time_filter,
        "active_topic": active_topic,
        "anchor": anchor_payload,
        "matches": matches[:max(1, int(limit or 12))] if matches else [],
        "selected": selected_for_context[:4 if (history_request or resume_anchor_row or repair_active_branch) else 2],
        "history_topics": history_topics,
        "topic_index": topic_index,
        "known_topic_count": len(topics),
        "topic_table_markdown": topic_table_md,
        "selected_section": selected_section,
        "clarification_needed": clarification_needed,
        "clarification_prompt": _text(pending_for_next_turn.get("prompt")) if clarification_needed else "",
        "pending_clarification": pending_for_next_turn if clarification_needed else {},
        "clarification_resolution": clarification_resolution,
    }
    with _LOCK:
        state["last_memory_search"] = deepcopy(result)
        state["last_relation_state"] = {"relation": relation, "reason": result["reason"], "confidence": result["relation_confidence"], "active_topic": active_topic}
        state["updated_at"] = time.time()
    _apr_timing_log("memory_search_total", search_started, user_key=_apr_diag_ref(uid),
        dialog_key=_apr_diag_ref(dialog_id), conversation_key=_apr_diag_ref(conversation_id),
        relation=relation, reason=result["reason"], total_pairs=len(rows), candidates=len(matches),
        selected_pairs=len(selected_for_context), topic_index_count=len(topic_index),
        user_operation=_text(user_operation.get("type")),
        semantic_active_branch_intent=bool(semantic_active_branch_intent),
        active_branch_preserved=bool(active_branch_descriptor.get("branch_preserved")),
        source_retrieval_strategy=source_retrieval_strategy,
        temporal_filter_applied=bool(time_filter.get("applied")),
        temporal_filter_empty=bool(time_filter.get("empty")),
        temporal_range_start=(time_filter.get("requested_start_at") if time_filter.get("empty") else time_filter.get("start_at")),
        temporal_range_end=(time_filter.get("requested_end_at") if time_filter.get("empty") else time_filter.get("end_at")),
        temporal_empty_reason=_text(time_filter.get("empty_reason")),
        temporal_neighbor_sides=sum(1 for side in (time_filter.get("neighbors") or {}).values() if isinstance(side, dict)),
        contextual_history_match=contextual_history_match, history_selection_method=history_selection_method,
        dialogue_act=speech_act or communicative_act or "UNSPECIFIED",
        active_branch_repair=bool(repair_active_branch),
        previous_answer_reference=bool(pragmatic_features.get("previous_answer_reference") or query_interpretation.get("previous_answer_reference")),
        factual_verification_request=bool(pragmatic_features.get("factual_verification_request") or query_interpretation.get("factual_verification_request")),
        active_repair_evidence_count=len(selected_for_context) if repair_active_branch else 0,
        active_repair_selection_method=history_selection_method if repair_active_branch else "",
        short_acknowledgement=bool(is_short_acknowledgement),
        selected_section_heading=_text(selected_section.get("heading")), clarification_needed=clarification_needed,
        clarification_status=_text(clarification_resolution.get("status")),
        selected_message_keys=[_apr_diag_ref(x.get("message_id")) for x in selected_for_context if isinstance(x, dict) and x.get("message_id")],
        anchor_message_key=_apr_diag_ref((result.get("anchor") or {}).get("message_id") if isinstance(result.get("anchor"), dict) else ""),
        resume_anchor_requested=bool(resume_key), resume_anchor_found=bool(resume_anchor_row),
        query_subject_terms=sorted(query_subjects)[:10], active_subject_conflict=bool(active_subject_conflict),
        semantic_subject_switch=bool(semantic_subject_switch),
        self_contained_new_information=bool(self_contained_new_information),
        hot_branch_candidate=bool(hot_branch_candidate),
        hot_work_followup=bool(hot_work_followup),
        hot_work_match_reason=_text(hot_work_match_reason),
        active_work_kind=_text(active_work_branch.get("kind")),
        active_work_message_key=_apr_diag_ref(active_work_pair.get("message_id") if active_work_pair else ""),
        active_work_origin_key=_apr_diag_ref(active_work_branch.get("origin_message_id")),
        top_candidate_alignment=[{
            "message_key": _apr_diag_ref(x.get("message_id")), "score": x.get("score"),
            "subject_overlap": x.get("subject_overlap"), "subject_mismatch": x.get("subject_mismatch"),
            "participant_alignment": x.get("participant_alignment"),
            "numeric_anchor_overlap": x.get("numeric_anchor_overlap"),
            "source_data_alignment": x.get("source_data_alignment"),
            "structured_data_richness": x.get("structured_data_richness"),
        } for x in matches[:3]])
    return result

def prepare_dialogue_context(
    user_id: Any,
    query: str,
    *,
    dialog_id: str = "",
    conversation_id: str = "",
    resume_message_id: str = "",
    limit: int = 12,
    has_image: bool = False,
    has_file: bool = False,
    has_voice: bool = False,
    query_interpretation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One processor-facing call: hydrate + search + continuation decision."""
    prepare_started = time.perf_counter()
    context = search_dialogue_context(
        user_id,
        query,
        dialog_id=dialog_id,
        conversation_id=conversation_id,
        resume_message_id=resume_message_id,
        limit=limit,
        has_image=has_image,
        has_file=has_file,
        has_voice=has_voice,
        query_interpretation=query_interpretation,
    )
    result = {
        "window_hours": DIALOGUE_WINDOW_HOURS,
        "relation": context["relation"],
        "relation_confidence": context["relation_confidence"],
        "active_branch_repair": bool(context.get("active_branch_repair")),
        "active_branch": deepcopy(context.get("active_branch") or {}),
        "active_work_branch": deepcopy(context.get("active_work_branch") or {}),
        "hot_work_followup": bool(context.get("hot_work_followup")),
        "hot_work_match_reason": _text(context.get("hot_work_match_reason"))[:80],
        "user_operation": deepcopy(context.get("user_operation") or {}),
        "source_retrieval": deepcopy(context.get("source_retrieval") or {}),
        "previous_answer_reference": bool(context.get("previous_answer_reference")),
        "factual_verification_request": bool(context.get("factual_verification_request")),
        "explicit_topic_switch": bool(context.get("explicit_topic_switch")),
        "reason": context["reason"],
        "active_topic": context["active_topic"],
        "selected_pairs": deepcopy(context["selected"]),
        "candidates": deepcopy(context["matches"]),
        "history_topics": deepcopy(context.get("history_topics") or []),
        "topic_index": deepcopy(context.get("topic_index") or []),
        "known_topic_count": int(context.get("known_topic_count") or 0),
        "history_request": bool(context.get("history_request")),
        "contextual_history_match": bool(context.get("contextual_history_match")),
        "matched_topic_count": int(context.get("matched_topic_count") or 0),
        "requested_topic_count": int(context.get("requested_topic_count") or 10),
        "minimum_topic_count": int(context.get("minimum_topic_count") or 0),
        "time_window": deepcopy(context.get("time_window") or {}),
        "time_filter": deepcopy(context.get("time_filter") or {}),
        "topic_table_markdown": _text(context.get("topic_table_markdown")),
        "anchor": deepcopy(context.get("anchor") or {}),
        "selected_section": deepcopy(context.get("selected_section") or {}),
        "clarification_needed": bool(context.get("clarification_needed")),
        "clarification_prompt": _text(context.get("clarification_prompt")),
        "pending_clarification": deepcopy(context.get("pending_clarification") or {}),
        "clarification_resolution": deepcopy(context.get("clarification_resolution") or {}),
        "search": deepcopy(context),
    }
    _apr_timing_log("prepare_dialogue_context_total", prepare_started,
        relation=result.get("relation"), candidates=len(result.get("candidates") or []),
        selected_pairs=len(result.get("selected_pairs") or []), topic_index_count=len(result.get("topic_index") or []))
    return result


def initialize() -> None:
    """Compatibility hook. PostgreSQL initialization belongs to the processor."""
    return None


__all__ = [
    # Premium storage/access functions
    "PREMIUM_MEMORY_WINDOW_HOURS",
    "PREMIUM_MEMORY_WINDOW_SECONDS",
    "init_db",
    "is_authenticated_user",
    "load_dialogue_pairs",
    "save_dialogue_pair",
    # Premium dialogue state/search functions
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
    "build_active_work_branch_record",
    "initialize",
]
