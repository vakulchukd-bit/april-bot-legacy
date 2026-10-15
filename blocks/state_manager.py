"""APRIL state manager — DB-backed dialogue search and live route state.

Persistent dialogue data belongs to storage.py.  This module is the processor-side
memory/search engine: it hydrates the live 12h window from PostgreSQL, ranks the
best USER↔APRIL pairs, decides CONTINUE/NEW candidates, and exposes the result to
the Interpretation Identity layer.  It never owns a second database.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import re
import json
import math
import threading
import time
import uuid
from typing import Any

from rapidfuzz import fuzz

DIALOGUE_WINDOW_HOURS = 12
DIALOGUE_WINDOW_SECONDS = DIALOGUE_WINDOW_HOURS * 3600

_LOCK = threading.RLock()
_STATES: dict[str, dict[str, Any]] = {}


def _apr_timing_log(stage: str, started: float | None = None, **fields: Any) -> None:
    """Low-overhead diagnostic timing; logging must never affect the request path."""
    try:
        payload = {"component": "state_manager", "stage": stage}
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


def hydrate(
    user_id: Any,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Refresh in-memory state from the canonical PostgreSQL dialogue store."""
    hydrate_started = time.perf_counter()
    uid = _uid(user_id)
    load_started = time.perf_counter()
    load_source = "provided_rows" if rows is not None else "postgres_load_dialogue_pairs"
    if rows is None:
        from storage import load_dialogue_pairs
        rows = load_dialogue_pairs(uid, limit=0)
    _apr_timing_log("history_rows_loaded", load_started, user_key=_apr_diag_ref(uid),
        source=load_source, rows_loaded=len(rows or []))

    state = get_state(uid)
    with _LOCK:
        state["dialogue_pairs"] = [
            deepcopy(row) for row in (rows or []) if isinstance(row, dict)
        ]
        _prune(state)
        state["last_activity"] = time.time()
        state["updated_at"] = state["last_activity"]
        _apr_timing_log("hydrate_complete", hydrate_started, user_key=_apr_diag_ref(uid),
            retained_pairs=len(state.get("dialogue_pairs") or []))
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
    state = hydrate(user_id) if refresh else get_state(user_id)
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
    """Append one persisted pair and enforce the pair's saved lifetime."""
    state = get_state(user_id)
    item = deepcopy(row or {})
    item.setdefault("created_at", time.time())
    item.setdefault("retention_hours", 12)
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
    stamp = time.time()
    return [
        deepcopy(row)
        for row in pairs
        if isinstance(row, dict)
        and _row_is_live(row, stamp, DIALOGUE_WINDOW_HOURS)
    ]


def _row_is_live(row: dict[str, Any], stamp: float, fallback_hours: int) -> bool:
    """Use lifetime captured when the pair was saved; legacy rows default to 12h."""
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
    "сделай", "вычисли", "рассчитай", "сравни", "найди", "проверь", "проанализируй", "приведи",
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
}
_CONTEXT_REFERENCE_TERMS = {
    "это", "этого", "этой", "этом", "эти", "этих", "тот", "та", "те", "того",
    "данный", "данная", "данное", "такие", "такой", "такую", "такого", "них", "их",
    "него", "нее", "неё", "ней", "ним", "previous", "earlier", "these", "those",
    "this", "that", "same", "them", "it", "дальше", "ещё", "еще",
}

def _subject_family(token: Any) -> str:
    value = _text(token).lower().replace("ё", "е")
    return value[:5] if len(value) >= 5 else value

_CONTEXT_NON_TOPICAL_ROOTS = (
    "называ", "зовут", "помн", "запом", "напом", "вспом", "потер", "забыл",
    "контекст", "случил", "произош", "диалог", "разговор", "бесед", "обращ",
    "напиш", "опиш", "расскаж", "объясн", "поясн", "покаж", "постро", "созда",
    "сдела", "вычисл", "рассчит", "сравн", "найд", "проверь", "проанализ", "привед",
    "перечисл", "продолж", "дальш", "должн", "каки", "был",
    "формул", "график", "таблиц", "диаграмм", "уравнен", "данн", "значен",
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


def _hot_branch_followup_candidate(
    query: str,
    interpretation: dict[str, Any] | None,
    latest_row: dict[str, Any] | None,
    *,
    query_subjects: set[str] | None = None,
    reference_followup: bool = False,
    marker: bool = False,
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
        "реакц", "подтвержд", "несоглас", "отрицан", "эмоц", "оценк",
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
    # to a completed task merely because that task is still in the 12-hour memory.
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
        from blocks.interpretation_identity import interpret_request_semantics
        return bool(interpret_request_semantics(query).get("history_request"))
    except Exception:
        return False


def _history_topic_limit(query: str, default: int = 7) -> int:
    low = _text(query).lower().replace("ё", "е")
    match = re.search(r"\b(10|[1-9])\b", low)
    if match:
        return max(1, min(10, int(match.group(1))))
    for word, count in _HISTORY_COUNT_WORDS.items():
        if re.search(rf"\b{word}\b", low):
            return count
    return default


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
        "он", "она", "они", "его", "ее", "её", "их", "ему", "ей", "им",
        "ним", "ней", "него", "нее", "неё", "них", "это", "тот", "та",
        "эта", "этот", "эти", "так", "данный", "данная",
    }
    return len(tokens) <= 10 and bool(tokens & reference_tokens)


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


def _build_topic_index(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build a 12-hour topic/section index from the canonical persisted pairs.

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
            heading = _text(section.get("heading"))[:90]
            if not heading:
                continue
            key = re.sub(r"\s+", " ", heading.casefold())
            item = {
                "heading": heading,
                "summary": re.sub(r"\s+", " ", _text(section.get("summary")))[:180],
                "order": int(section.get("order") or len(merged) + 1),
                "message_id": _text(section.get("message_id") or message_id),
            }
            if key in positions:
                # Update the meaning with the newest grounded description but keep
                # the stable heading position from the original explanation.
                pos = positions[key]
                item["order"] = merged[pos].get("order") or item["order"]
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
                "last_question": _text(row.get("user_text"))[:180],
                "message_id": _text(row.get("message_id")),
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
            group["last_question"] = _text(row.get("user_text"))[:180] or group["last_question"]
            group["modalities"] = sorted(set(group.get("modalities") or []) | _row_modalities(row))
            group["pair_count"] = int(group.get("pair_count") or 0) + 1
            group["message_id"] = _text(row.get("message_id")) or group.get("message_id")
            group["summary"] = _compact_memory_summary(row) or group.get("summary", "")
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
                    "summary": item.get("summary") or found.get("summary"),
                    "subject_terms": sorted(set(found.get("subject_terms") or []) | set(item.get("subject_terms") or [])),
                    "sections": merge_sections(found.get("sections") or [], item.get("sections") or [], _text(item.get("message_id"))),
                    "pair_count": int(found.get("pair_count") or 0) + int(item.get("pair_count") or 0),
                })
        else:
            deduped.append(item)

    deduped.sort(key=lambda item: float(item.get("last_at") or 0), reverse=True)
    visible = []
    for idx, item in enumerate(deduped[:30], 1):
        visible.append({
            "number": idx,
            "topic": _text(item.get("topic"))[:120],
            "summary": _text(item.get("summary"))[:220],
            "sections": [dict(section) for section in (item.get("sections") or [])[:10] if isinstance(section, dict)],
            "turns": f"{item.get('start_turn', 0)}-{item.get('end_turn', 0)}",
            "last_question": _text(item.get("last_question"))[:140],
            "pair_count": int(item.get("pair_count") or 0),
            "last_at": item.get("last_at"),
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
                _text(item.get("mime_type")), _text(item.get("content_preview"))[:3500],
                _text(item.get("summary"))[:800],
            ])
    for item in req.get("attachments") or []:
        if isinstance(item, dict):
            chunks.extend([_text(item.get("filename")), _text(item.get("kind")), _text(item.get("source_type"))])
    record = resp.get("dialogue_memory_record")
    if not isinstance(record, dict):
        metadata = resp.get("metadata") if isinstance(resp.get("metadata"), dict) else {}
        record = metadata.get("dialogue_memory_record") if isinstance(metadata.get("dialogue_memory_record"), dict) else {}
    chunks.extend([_text(record.get("topic")), _text(record.get("summary"))[:1400]])
    # Include a bounded excerpt of the exact code/document output generated by
    # April. This makes later requests about a function/symbol retrieve the pair
    # that owns the output asset, without putting raw binary into JSONB.
    for block in resp.get("render_blocks") or []:
        if not isinstance(block, dict) or _text(block.get("type")).lower() != "code":
            continue
        chunks.extend([_text(block.get("filename")), _text(block.get("language")), _text(block.get("code") or block.get("content"))[:3500]])
    asset_refs = resp.get("asset_refs") if isinstance(resp.get("asset_refs"), dict) else {}
    for item in asset_refs.get("april_outputs") or []:
        if isinstance(item, dict):
            chunks.extend([_text(item.get("filename")), _text(item.get("output_type")), _text(item.get("language"))])
    for key in ("entities", "visual_observations", "code_symbols", "file_purpose"):
        value = record.get(key)
        if isinstance(value, list):
            chunks.extend(_text(part)[:400] for part in value[:12])
        elif value:
            chunks.append(_text(value)[:900])
    return " ".join(part for part in chunks if part)[:9000]



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
    exact_dialog = bool(dialog_id and row_dialog and row_dialog == dialog_id)

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
        + (0.09 if exact_dialog else 0.0)
    )
    if reference_followup and exact_dialog:
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
        "same_dialog": exact_dialog,
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
        "sections": _dialogue_section_map(row),
        "is_pending_clarification": _row_is_pending_clarification(row),
        "memory_summary": _compact_memory_summary(row),
        "attachment_evidence": attachment_evidence[:1800],
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
            heading = _text(item.get("heading") or item.get("title"))[:90]
            summary = re.sub(r"\s+", " ", _text(item.get("summary")))[:140]
            if heading:
                try:
                    order = int(item.get("order") or len(sections) + 1)
                except (TypeError, ValueError):
                    order = len(sections) + 1
                sections.append({"heading": heading, "summary": summary, "order": order})
    if sections:
        return sections

    # Compatibility for stored turns created before the McDowell section index existed.
    answer = _text(response.get("answer") or response.get("content") or row.get("april_text") or row.get("april"))
    lines = answer.splitlines()
    found: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        match = re.match(r"^\s*#{1,4}\s+(.+?)\s*#*\s*$", line.strip())
        if match and match.group(1).strip():
            found.append((idx, match.group(1).strip()[:90]))
    for pos, (idx, heading) in enumerate(found[:limit]):
        end = found[pos + 1][0] if pos + 1 < len(found) else len(lines)
        body = re.sub(r"\s+", " ", " ".join(x.strip() for x in lines[idx + 1:end] if x.strip()))
        sections.append({"heading": heading, "summary": body[:140], "order": pos + 1})
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
            sections.append({"heading": heading[:90], "summary": summary[:140], "order": len(sections) + 1})
    return sections


def _compact_memory_summary(row: dict[str, Any]) -> str:
    direct = _text(row.get("memory_summary"))
    if direct:
        return re.sub(r"\s+", " ", direct)[:220]
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
    return re.sub(r"\s+", " ", summary)[:220]


def _compact_pair(item: dict[str, Any]) -> dict[str, Any]:
    sections = _dialogue_section_map(item)
    # Do not feed the previous long explanation back into the next prompt. Retain
    # a compact summary plus McDowell's ordered section index instead.
    outline = _compact_memory_summary(item)
    if not outline:
        outline = _text(item.get("april") or item.get("april_text"))[:180]
    modalities = set(item.get("row_modalities") or [])
    has_asset = bool(modalities & {"image", "file", "text_file", "voice"})
    evidence = (_text(item.get("attachment_evidence")) or _row_attachment_evidence(item))[:900] if has_asset else ""
    return {
        "turn": item.get("turn_index"),
        "user": _text(item.get("user") or item.get("user_text"))[:180],
        "april": outline[:220],
        "topic": _text(item.get("topic"))[:100],
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
    "мы", "нам", "наше", "наши", "наш", "нашу", "мне", "мои", "мой",
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
        if len(query_token) >= 5 and any(fuzz.ratio(query_token, candidate) >= 76 for candidate in candidate_list if len(candidate) >= 5):
            matched += 1
    return matched / max(1, len(query_tokens))


def _topic_query_overlap(query: str, topic: str) -> float:
    """Overlap only on topic-bearing words, not generic continuation vocabulary."""
    query_tokens = _semantic_tokens(query) - _SECTION_TOPIC_NOISE
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
        return bounded[:max(1, min(10, int(limit or 7)))] if fallback else []
    ranked: list[tuple[float, float, dict[str, Any]]] = []
    for item in bounded:
        candidate_tokens = _semantic_tokens(_history_topic_text(item))
        overlap = _fuzzy_token_overlap(tokens, candidate_tokens)
        if overlap <= 0:
            continue
        phrase = fuzz.token_set_ratio(" ".join(sorted(tokens)), " ".join(sorted(candidate_tokens))) / 100.0 if candidate_tokens else 0.0
        score = 0.78 * overlap + 0.22 * phrase
        ranked.append((score, float(item.get("last_at") or 0), item))
    if not ranked:
        # Broad history overview may fall back to recent topics; a normal request
        # must not receive unrelated topics merely because no semantic match exists.
        return bounded[:max(1, min(10, int(limit or 7)))] if fallback else []
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [dict(item) for _, _, item in ranked[:max(1, min(10, int(limit or 7)))]]


def _select_history_context_pairs(
    query: str,
    matches: list[dict[str, Any]],
    topic_index: list[dict[str, Any]],
    all_rows: list[dict[str, Any]],
    *,
    requested_topic_count: int = 7,
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
    """Search all authenticated 12-hour turns, including stored section headings and summaries."""
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
                    "heading": _text(section.get("heading"))[:90],
                    "summary": _text(section.get("summary"))[:180],
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
                "summary": summary[:180],
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
        label = heading[:90]
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
            "heading": _text(section.get("heading"))[:90],
            "summary": _text(section.get("summary"))[:180],
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
    """Find the smallest reliable continuation point in the authenticated 12h memory.

    Retrieval hierarchy: topic -> USER↔APRIL pair -> McDowell section. Only the
    selected pair/section is passed forward. An unclear choice yields a local
    clarification state that persists the original request and can be resumed.
    """
    search_started = time.perf_counter()
    uid = _uid(user_id)
    state = hydrate(uid)
    all_rows = [row for row in (state.get("dialogue_pairs") or []) if isinstance(row, dict) and not _is_failed_provider_row(row)]
    resume_key = _text(resume_message_id)
    resume_anchor_row = next((row for row in all_rows if (
        _text(row.get("message_id")) == resume_key
        or (resume_key.startswith("legacy-memory-") and resume_key == f"legacy-memory-{_text(row.get('id'))}")
    )), None) if resume_key else None
    reference_followup = _looks_like_referential_followup(query)
    query_interpretation = dict(query_interpretation or {})
    history_request = bool(query_interpretation.get("history_request")) or _is_history_request(query)
    new_topic_request = _looks_like_new_topic(query)
    interpreted_direction = _text(query_interpretation.get("direction"))
    interpreted_intent = _text(query_interpretation.get("primary_intent"))
    context_signature = _query_context_signature(query, query_interpretation)
    query_subjects = set(context_signature.get("subject_terms") or _subject_tokens(query))
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

    # Search the whole user's 12-hour window for a distinctly named old topic,
    # but do not let generic words such as "применение" switch the active topic.
    topic_bearing = _semantic_tokens(query) - _SECTION_QUERY_NOISE - _CONTEXT_GENERIC_TERMS
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
    matches = [_candidate_score(query, row, dialog_id=str(dialog_id or ""), reference_followup=reference_followup, query_modalities=query_modalities)
               for row in rows]
    # For participant-centered, subjectless questions, first rank factual evidence
    # written from the relevant speaker perspective; use the existing relevance and
    # recency ordering for all other turns. No fixed score gate is introduced.
    matches.sort(key=lambda item: (
        int(item.get("participant_alignment") or 0) if not query_subjects else 0,
        float(item["score"]), float(item["recency"]), int(item["turn_index"])
    ), reverse=True)
    _apr_timing_log("candidate_score_rank", candidate_started, candidates_scored=len(rows), matches=len(matches))

    # Build the index once and share it between topic ranking, pair selection and Provider.
    topics = _build_topic_index(all_rows)
    history_limit = _history_topic_limit(query, 7)
    # History recall may show an overview; normal requests receive only semantically matched topics.
    topic_index = _rank_history_topics(query, topics, 10, fallback=history_request)
    history_topics = _rank_history_topics(query, topics, history_limit) if history_request else []

    latest_same_dialog = max((item for item in matches if bool(item.get("same_dialog"))),
        key=lambda item: (float(item.get("created_at") or 0), int(item.get("turn_index") or 0)), default=None)
    best = matches[0] if matches else None
    active_subjects = set(latest_same_dialog.get("subject_terms") or []) if latest_same_dialog else set()
    active_subject_conflict = _subject_conflicts(query_subjects, active_subjects)
    # A named subject change in a self-contained new request is a new task even
    # when old and new requests share the same verbs/output format. Referential
    # corrections remain eligible for retrieval from the matching older context.
    # An explicitly named subject in a self-contained request wins over nearby
    # anaphora ("Раскажи про Коперника ... как он выглядел"). A pronoun inside
    # the same request must not drag an unrelated old pair into the context.
    self_contained_subject_switch = bool(
        active_subject_conflict
        and query_subjects
        and len(_semantic_tokens(query)) >= 4
        and interpreted_intent == "NEW_INFORMATION"
        and not history_request
        and not new_topic_request
    )
    semantic_subject_switch = bool(
        active_subject_conflict
        and (self_contained_subject_switch or (
            interpreted_intent == "NEW_INFORMATION"
            and not reference_followup
            and not _continuation_marker(query)
        ))
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
        marker=marker, has_attachment=bool(query_modalities),
        history_request=history_request, new_topic_request=new_topic_request,
    )
    continuation = False
    has_new_attachment = bool(query_modalities)
    explicit_attachment_followup = has_new_attachment and reference_followup
    if pending_clarification and not new_topic_request:
        continuation = True
    elif history_request or new_topic_request:
        continuation = False
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
    elif hot_branch_candidate and not semantic_subject_switch:
        # Only ambiguous turns that pass the hot-branch relevance check may continue
        # by default. Missing subject words alone are not enough to force CONTINUE.
        continuation = True
    elif latest_same_dialog and reference_followup and not semantic_subject_switch:
        continuation = True
    elif latest_same_dialog and marker and len(_tokens(query)) <= 14 and not semantic_subject_switch:
        continuation = True
    elif explicit_topic_hits and (reference_followup or _is_section_request(query) or _looks_like_topic_correction(query)):
        continuation = True
    elif same_dialog_semantic and not semantic_subject_switch:
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
        and not explicit_prior_pointer
        and (bool(query_subjects) or not reference_followup)
    )
    if self_contained_new_information:
        # Search results remain available for diagnostics/ranking, but are not a
        # valid dialogue continuation and must not be forwarded to the Provider.
        relation = "NEW"
        continuation = False

    # Resolve the anchor. Short referential requests with no explicit topic always
    # begin at the latest active turn; section ranking happens inside that topic.
    anchor: dict[str, Any] | None = None
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
                "clarification_reply": _text(query)[:240],
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
            # authenticated 12-hour window, not just the three offered choices.
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
                    "clarification_reply": _text(query)[:240],
                    "search_query": recovery_query[:180],
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
                    "clarification_reply": _text(query)[:240],
                    "search_query": recovery_query[:180],
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
        if not query_subjects and latest_same_dialog:
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
        elif explicit_topic_hits:
            chosen_global = explicit_topic_hits[0][1]
            anchor = _candidate_score(query, chosen_global, dialog_id=str(dialog_id or ""), reference_followup=reference_followup, query_modalities=query_modalities)
        elif latest_same_dialog and (reference_followup or marker or short_contextual or _is_section_request(query)):
            topic_overlap_best = max((_topic_query_overlap(query, item.get("topic", "")) for item in matches if item.get("same_dialog")), default=0.0)
            if topic_overlap_best < 0.50:
                anchor = latest_same_dialog
        if anchor is None:
            anchor = best
    else:
        anchor = best if relation == "NEW" else None

    active_topic = _text((anchor or {}).get("topic")) or _text((latest_same_dialog or {}).get("topic")) or _text(query)[:140]

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
    if relation == "NEW" and not history_request and not selected_for_context and topic_index:
        lookup_tokens = _history_query_topic_tokens(query)
        top_topic = topic_index[0]
        topic_tokens = _semantic_tokens(_history_topic_text(top_topic))
        topic_overlap = _fuzzy_token_overlap(lookup_tokens, topic_tokens) if lookup_tokens else 0.0
        has_distinctive_query = len(lookup_tokens) >= 2 or any(len(token) >= 7 for token in lookup_tokens)
        if topic_overlap >= 0.50 and has_distinctive_query:
            topic_message_id = _text(top_topic.get("message_id"))
            source_row = next((row for row in all_rows if _text(row.get("message_id")) == topic_message_id), None)
            if source_row is not None:
                matched_pair = _candidate_score(
                    query, source_row, dialog_id=str(dialog_id or ""),
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
                # answer first, then the full 12-hour user history; never suggest
                # a nearby numbered section when the requested number is absent.
                exact_local = [item for item in ranked_sections if int(item.get("order") or 0) == requested_section_number]
                if not exact_local and source_row:
                    exact_local = [
                        {
                            "topic": _topic_label(source_row),
                            "heading": _text(section.get("heading"))[:90],
                            "summary": _text(section.get("summary"))[:180],
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
                        "heading": _text(item.get("heading"))[:90],
                        "summary": _text(item.get("summary"))[:180],
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
                            "clarification_reply": _text(query)[:240],
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
        # to its topic vector. A broad dialog_id may cover the entire 12-hour window
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
        # Re-score the 12-hour memory against the selected topic itself, not only
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
        # remaining 12-hour candidates available for normal cross-topic recall.
        matches = [anchor] + [item for item in matches if _text(item.get("message_id")) != anchor_message_id]

    if section_anchor_overridden and anchor:
        active_topic = _text(anchor.get("topic")) or active_topic
        selected_for_context = [_compact_pair(anchor)]

    topic_table_lines = ["| # | Тема | Последний запрос | Ходы |", "|---:|---|---|---:|"]
    for item in (history_topics or topic_index[:min(3, len(topic_index))]):
        topic_table_lines.append(f"| {item['number']} | {str(item['topic']).replace('|', '/')} | {str(item['last_question']).replace('|', '/')} | {item['turns']} |")
    topic_table_md = "\n".join(topic_table_lines)

    result = {
        "engine": "state_manager_topic_section_search_v8_semantic_history_handoff",
        "authenticated": True,
        "window_hours": DIALOGUE_WINDOW_HOURS,
        "dialog_id": str(dialog_id or ""),
        "conversation_id": str(conversation_id or ""),
        "query": str(query or ""),
        "context_signature": context_signature,
        "active_subject_conflict": bool(active_subject_conflict),
        "semantic_subject_switch": bool(semantic_subject_switch),
        "self_contained_new_information": bool(self_contained_new_information),
        "total_pairs": len(rows),
        "candidate_count": len(matches),
        "relation": relation,
        "reason": (
            "explicit_history_resume" if resume_anchor_row
            else "clarification_resolved" if clarification_resolution and _text(clarification_resolution.get("status")).startswith("resolved")
            else "clarification_researched" if clarification_resolution
            else "clarification_pending" if clarification_needed
            else "history_request" if history_request
            else "semantic_history_match" if contextual_history_match
            else "self_contained_new_information" if self_contained_new_information
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
        "active_topic": active_topic,
        "anchor": _compact_pair(anchor) if relation == "CONTINUE" and anchor else {},
        "matches": matches[:max(1, int(limit or 12))] if matches else [],
        "selected": selected_for_context[:4 if (history_request or resume_anchor_row) else 2],
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
        contextual_history_match=contextual_history_match, history_selection_method=history_selection_method,
        selected_section_heading=_text(selected_section.get("heading")), clarification_needed=clarification_needed,
        clarification_status=_text(clarification_resolution.get("status")),
        selected_message_keys=[_apr_diag_ref(x.get("message_id")) for x in selected_for_context if isinstance(x, dict) and x.get("message_id")],
        anchor_message_key=_apr_diag_ref((result.get("anchor") or {}).get("message_id") if isinstance(result.get("anchor"), dict) else ""),
        resume_anchor_requested=bool(resume_key), resume_anchor_found=bool(resume_anchor_row),
        query_subject_terms=sorted(query_subjects)[:10], active_subject_conflict=bool(active_subject_conflict),
        semantic_subject_switch=bool(semantic_subject_switch),
        self_contained_new_information=bool(self_contained_new_information),
        hot_branch_candidate=bool(hot_branch_candidate),
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
        "requested_topic_count": int(context.get("requested_topic_count") or 7),
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
