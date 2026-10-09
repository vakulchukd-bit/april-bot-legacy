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
    return any(marker.replace("ё", "е") in low for marker in _HISTORY_MARKERS)


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
    if any(marker in low for marker in phrase_markers):
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
            same_as_prev = relation != "NEW" and similarity >= 0.28 and not modality_changed
            if not same_as_prev and not modality_changed and _looks_like_referential_followup(str(row.get("user_text") or "")):
                same_as_prev = True

        row_sections = _dialogue_section_map(row)
        if not groups or not same_as_prev:
            groups.append({
                "topic": label,
                "topic_tokens": sorted(tokens),
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
            if similarity >= 0.78:
                found = prev
                break
        if found is not None:
            if float(item.get("last_at") or 0) >= float(found.get("last_at") or 0):
                found.update({
                    "end_turn": item.get("end_turn"), "last_at": item.get("last_at"),
                    "last_question": item.get("last_question"), "message_id": item.get("message_id"),
                    "summary": item.get("summary") or found.get("summary"),
                    "sections": merge_sections(found.get("sections") or [], item.get("sections") or [], _text(item.get("message_id"))),
                    "pair_count": int(found.get("pair_count") or 0) + int(item.get("pair_count") or 0),
                })
        else:
            deduped.append(item)

    deduped.sort(key=lambda item: float(item.get("last_at") or 0), reverse=True)
    visible = []
    for idx, item in enumerate(deduped[:12], 1):
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

    Raw file/image bytes stay in dialogue_assets; this index contains only
    bounded filenames, source snippets and the provider's grounded summary.
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
    candidate_text = " ".join(x for x in (user, user_en, april, april_en, attachment_evidence) if x)
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

    return {
        "score": round(min(1.0, float(score)), 6),
        "semantic": round(lexical, 6),
        "context": round(overlap, 6),
        "answer_overlap": round(answer_overlap, 6),
        "user_overlap": round(user_overlap, 6),
        "entity_overlap": round(entity_overlap, 6),
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


def _match_clarification_option(query: str, pending: dict[str, Any]) -> dict[str, Any]:
    """Resolve a short choice without another model call; ties remain unresolved."""
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

    scored: list[tuple[float, dict[str, Any]]] = []
    query_tokens = _semantic_tokens(low)
    for item in options:
        label = " ".join(_text(item.get(k)) for k in ("topic", "heading", "summary"))
        label_tokens = _semantic_tokens(label)
        overlap = _concept_overlap(query_tokens, label_tokens) if query_tokens else 0.0
        fuzz_score = fuzz.token_set_ratio(" ".join(sorted(query_tokens)), " ".join(sorted(label_tokens))) / 100.0 if query_tokens and label_tokens else 0.0
        score = 0.55 * overlap + 0.45 * fuzz_score
        scored.append((score, dict(item)))
    scored.sort(key=lambda entry: entry[0], reverse=True)
    if not scored:
        return {}
    second = scored[1][0] if len(scored) > 1 else 0.0
    return scored[0][1] if scored[0][0] >= 0.52 and scored[0][0] - second >= 0.12 else {}


def _clarification_prompt(original_request: str, options: list[dict[str, Any]], language: str = "ru") -> str:
    labels = []
    for index, item in enumerate(options[:3], 1):
        topic = _text(item.get("topic"))
        heading = _text(item.get("heading"))
        label = f"{topic} — {heading}" if topic and topic.casefold() != heading.casefold() else (heading or topic)
        labels.append(f"{index}. {label[:130]}")
    choices = "\n".join(labels)
    if language == "uk":
        lead = f"Щоб продовжити саме ваш запит «{_text(original_request)[:180]}», уточніть, який розділ ви маєте на увазі:"
        tail = "\nВідповідайте номером або назвою. Початковий запит збережено."
    elif language == "en":
        lead = f'To continue your request “{_text(original_request)[:180]}”, which section do you mean?'
        tail = "\nReply with the number or section name. Your original request is preserved."
    else:
        lead = f"Чтобы продолжить именно ваш запрос «{_text(original_request)[:180]}», уточните, какой раздел вы имеете в виду:"
        tail = "\nОтветьте номером или названием. Исходный запрос сохранён."
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
    limit: int = 12,
    has_image: bool = False,
    has_file: bool = False,
    has_voice: bool = False,
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
    reference_followup = _looks_like_referential_followup(query)
    history_request = _is_history_request(query)
    new_topic_request = _looks_like_new_topic(query)

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
    topic_bearing = _semantic_tokens(query) - _SECTION_QUERY_NOISE
    named_rows: list[tuple[float, dict[str, Any]]] = []
    if not history_request and topic_bearing:
        scoped_ids = {_text(row.get("message_id")) for row in scoped_rows}
        for row in all_rows:
            if _row_is_pending_clarification(row):
                continue
            mid = _text(row.get("message_id"))
            if mid and mid in scoped_ids:
                continue
            overlap = _topic_query_overlap(query, _topic_label(row))
            if overlap >= 0.50:
                named_rows.append((overlap, row))
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
    matches.sort(key=lambda item: (float(item["score"]), float(item["recency"]), int(item["turn_index"])), reverse=True)
    _apr_timing_log("candidate_score_rank", candidate_started, candidates_scored=len(rows), matches=len(matches))

    latest_same_dialog = max((item for item in matches if bool(item.get("same_dialog"))),
        key=lambda item: (float(item.get("created_at") or 0), int(item.get("turn_index") or 0)), default=None)
    best = matches[0] if matches else None
    explicit_topic_hits = []
    seen_topic_hit_ids: set[str] = set()
    for row in all_rows:
        if _row_is_pending_clarification(row):
            continue
        overlap = _topic_query_overlap(query, _topic_label(row))
        mid = _text(row.get("message_id")) or f"{row.get('created_at')}|{row.get('turn_index')}"
        if overlap >= 0.50 and mid not in seen_topic_hit_ids:
            seen_topic_hit_ids.add(mid)
            explicit_topic_hits.append((overlap, row))
    explicit_topic_hits.sort(key=lambda item: (item[0], float(item[1].get("created_at") or 0)), reverse=True)

    same_dialog_semantic = bool(best and (
        (best.get("same_dialog") and (
            float(best.get("entity_overlap") or 0) >= 0.18
            or float(best.get("context") or 0) >= 0.16
            or float(best.get("semantic") or 0) >= 0.52
        )) or float(best.get("entity_overlap") or 0) >= 0.28
    ))
    marker = _continuation_marker(query)
    short_contextual = len(_tokens(query)) <= 12 and _text(query).lower().startswith(("а ", "и ", "ну ", "так ")) and (
        reference_followup or marker or len(_semantic_tokens(query)) == 0
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
    elif latest_same_dialog and reference_followup:
        continuation = True
    elif latest_same_dialog and (marker or short_contextual) and len(_tokens(query)) <= 14:
        continuation = True
    elif explicit_topic_hits and (reference_followup or _is_section_request(query) or _looks_like_topic_correction(query)):
        continuation = True
    elif same_dialog_semantic:
        continuation = True
    elif best and float(best.get("score") or 0) >= 0.60:
        continuation = True
    relation = "CONTINUE" if continuation else "NEW"

    # Resolve the anchor. Short referential requests with no explicit topic always
    # begin at the latest active turn; section ranking happens inside that topic.
    anchor: dict[str, Any] | None = None
    forced_section: dict[str, Any] = {}
    clarification_resolution: dict[str, Any] = {}
    clarification_needed = False
    clarification_options: list[dict[str, Any]] = []
    pending_for_next_turn: dict[str, Any] = {}

    if pending_clarification and not new_topic_request:
        if pending_resolved:
            forced_section = dict(pending_option)
            original_pending_request = _text(pending_clarification.get("original_request"))
            clarification_resolution = {
                "original_request": original_pending_request,
                "clarification_reply": _text(query)[:240],
                "selected_section": forced_section,
            }
            source_id = _text(forced_section.get("message_id"))
            source_row = next((row for row in all_rows if _text(row.get("message_id")) == source_id), None)
            if source_row is not None:
                anchor = _candidate_score(original_pending_request or query, source_row, dialog_id=str(dialog_id or ""), reference_followup=True, query_modalities=query_modalities)
            relation = "CONTINUE"
        else:
            clarification_needed = True
            pending_for_next_turn = dict(pending_clarification)
            clarification_options = [dict(x) for x in (pending_clarification.get("options") or []) if isinstance(x, dict)][:3]
            prompt_text = _text(pending_clarification.get("prompt")) or _clarification_prompt(_text(pending_clarification.get("original_request")) or query, clarification_options)
            pending_for_next_turn["prompt"] = prompt_text
            source_id = _text((clarification_options[0] if clarification_options else {}).get("message_id"))
            source_row = next((row for row in all_rows if _text(row.get("message_id")) == source_id), None)
            if source_row is not None:
                anchor = _candidate_score(_text(pending_clarification.get("original_request")) or query, source_row, dialog_id=str(dialog_id or ""), reference_followup=True)
            relation = "CONTINUE"
    elif relation == "CONTINUE" and rows:
        if explicit_topic_hits:
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
    if relation == "CONTINUE":
        if anchor:
            selected_for_context.append(_compact_pair(anchor))
        # At most one corroborating pair; never forward a pile of unrelated turns.
        for item in matches:
            if item.get("is_pending_clarification"):
                continue
            if not item.get("message_id") or _text(item.get("message_id")) == _text((anchor or {}).get("message_id")):
                continue
            if selected_for_context and len(selected_for_context) >= 2:
                break
            topic_similarity = fuzz.token_set_ratio(
                _text((anchor or {}).get("topic")).casefold(), _text(item.get("topic")).casefold()
            ) / 100.0 if _text((anchor or {}).get("topic")) and _text(item.get("topic")) else 0.0
            if _topic_query_overlap(query, _text(item.get("topic"))) >= 0.50 or topic_similarity >= 0.65:
                selected_for_context.append(_compact_pair(item))
                break

    selected_section: dict[str, Any] = {}
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
            generic_pointer = _is_generic_section_pointer(section_query)
            if generic_pointer and source_row:
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

    topics = _build_topic_index(all_rows)
    history_limit = _history_topic_limit(query, 7)
    history_topics = topics[:history_limit] if history_request else []
    topic_index = topics[:10]
    topic_table_lines = ["| # | Тема | Последний запрос | Ходы |", "|---:|---|---|---:|"]
    for item in (history_topics or topic_index[:min(3, len(topic_index))]):
        topic_table_lines.append(f"| {item['number']} | {str(item['topic']).replace('|', '/')} | {str(item['last_question']).replace('|', '/')} | {item['turns']} |")
    topic_table_md = "\n".join(topic_table_lines)

    result = {
        "engine": "state_manager_topic_section_search_v5_clarification",
        "authenticated": True,
        "window_hours": DIALOGUE_WINDOW_HOURS,
        "dialog_id": str(dialog_id or ""),
        "conversation_id": str(conversation_id or ""),
        "query": str(query or ""),
        "total_pairs": len(rows),
        "candidate_count": len(matches),
        "relation": relation,
        "reason": "clarification_resolved" if clarification_resolution else "clarification_pending" if clarification_needed else ("history_request" if history_request else "named_topic_match" if explicit_topic_hits else "active_topic_default" if relation == "CONTINUE" and anchor else "new_request" if relation == "NEW" else "semantic_memory_match"),
        "relation_confidence": round(float((anchor or best or {}).get("score") or (0.60 if relation == "CONTINUE" else 0.0)), 6),
        "continuation_marker": marker,
        "referential_followup": reference_followup,
        "history_request": history_request,
        "requested_topic_count": history_limit,
        "active_topic": active_topic,
        "anchor": _compact_pair(anchor) if relation == "CONTINUE" and anchor else {},
        "matches": matches[:max(1, int(limit or 12))] if matches else [],
        "selected": selected_for_context[:2],
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
        selected_section_heading=_text(selected_section.get("heading")), clarification_needed=clarification_needed,
        selected_message_keys=[_apr_diag_ref(x.get("message_id")) for x in selected_for_context if isinstance(x, dict) and x.get("message_id")],
        anchor_message_key=_apr_diag_ref((result.get("anchor") or {}).get("message_id") if isinstance(result.get("anchor"), dict) else ""))
    return result

def prepare_dialogue_context(
    user_id: Any,
    query: str,
    *,
    dialog_id: str = "",
    conversation_id: str = "",
    limit: int = 12,
    has_image: bool = False,
    has_file: bool = False,
    has_voice: bool = False,
) -> dict[str, Any]:
    """One processor-facing call: hydrate + search + continuation decision."""
    prepare_started = time.perf_counter()
    context = search_dialogue_context(
        user_id,
        query,
        dialog_id=dialog_id,
        conversation_id=conversation_id,
        limit=limit,
        has_image=has_image,
        has_file=has_file,
        has_voice=has_voice,
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
