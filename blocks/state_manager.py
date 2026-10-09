"""APRIL state manager — DB-backed dialogue search and live route state.

Persistent dialogue data belongs to storage.py.  This module is the processor-side
memory/search engine: it hydrates the live 12h window from PostgreSQL, ranks the
best USER↔APRIL pairs, decides CONTINUE/NEW candidates, and exposes the result to
the Interpretation Identity layer.  It never owns a second database.
"""
from __future__ import annotations

from copy import deepcopy
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
    """Build a compact topic map from the whole retained dialogue window.

    The map is derived from persisted USER↔APRIL pairs; it does not create a
    second memory store.  Consecutive pairs are grouped by explicit NEW
    relations or strong semantic continuity, then deduplicated.
    """
    if not rows:
        return []

    ordered = sorted(
        [r for r in rows if isinstance(r, dict)],
        key=lambda r: (float(r.get("created_at") or 0), int(r.get("turn_index") or 0)),
    )
    groups: list[dict[str, Any]] = []

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

            # A clearly referential short follow-up can preserve a topic even
            # when the sentence itself has little lexical overlap.
            if not same_as_prev and not modality_changed and _looks_like_referential_followup(str(row.get("user_text") or "")):
                same_as_prev = True

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
            })
        else:
            g = groups[-1]
            g["end_turn"] = int(row.get("turn_index") or g["end_turn"])
            g["last_at"] = float(row.get("created_at") or g["last_at"])
            g["last_question"] = _text(row.get("user_text"))[:180] or g["last_question"]
            g["modalities"] = sorted(set(g.get("modalities") or []) | _row_modalities(row))
            g["pair_count"] = int(g.get("pair_count") or 0) + 1

    # Deduplicate adjacent/near-duplicate topic labels without losing the
    # newest occurrence.
    deduped: list[dict[str, Any]] = []
    for item in groups:
        found = None
        for prev in reversed(deduped[-3:]):
            similarity = fuzz.token_set_ratio(
                str(item.get("topic") or "").lower(),
                str(prev.get("topic") or "").lower(),
            ) / 100.0
            if similarity >= 0.78:
                found = prev
                break
        if found is not None:
            if float(item.get("last_at") or 0) >= float(found.get("last_at") or 0):
                found.update({
                    "end_turn": item.get("end_turn"),
                    "last_at": item.get("last_at"),
                    "last_question": item.get("last_question"),
                    "message_id": item.get("message_id"),
                    "pair_count": int(found.get("pair_count") or 0) + int(item.get("pair_count") or 0),
                })
        else:
            deduped.append(item)

    deduped.sort(key=lambda x: float(x.get("last_at") or 0), reverse=True)
    visible = []
    for idx, item in enumerate(deduped[:10], 1):
        visible.append({
            "number": idx,
            "topic": _text(item.get("topic"))[:120],
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
        "attachment_evidence": attachment_evidence[:1800],
    }


def _compact_pair(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "turn": item.get("turn_index"),
        "user": _text(item.get("user") or item.get("user_text"))[:240],
        "april": _text(item.get("april") or item.get("april_text"))[:300],
        "topic": _text(item.get("topic"))[:100],
        "score": item.get("score"),
        "same_dialog": bool(item.get("same_dialog")),
        "message_id": _text(item.get("message_id")),
        "attachment_evidence": (_text(item.get("attachment_evidence")) or _row_attachment_evidence(item))[:1800],
    }


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
    """Search the retained authenticated dialogue with hybrid semantic retrieval.

    The result is deliberately structured for Interpretation Identity:
    - lexical + semantic token matching;
    - attachment/domain compatibility;
    - exact authenticated dialog continuity;
    - explicit referential follow-up detection;
    - neighboring turns;
    - whole-window topic index for history questions.
    """
    uid = _uid(user_id)
    state = hydrate(uid)
    all_rows = list(state.get("dialogue_pairs") or [])
    reference_followup = _looks_like_referential_followup(query)
    history_request = _is_history_request(query)
    new_topic_request = _looks_like_new_topic(query)

    # Search the complete active dialogue, not merely its last turn.  Keep
    # ordinary continuation scoped to the requested conversation; only explicit
    # history requests may span the user's retained conversations.
    if history_request:
        rows = all_rows
    elif dialog_id or conversation_id:
        rows = [
            row for row in all_rows
            if isinstance(row, dict) and (
                (dialog_id and _text(row.get("dialog_id")) == _text(dialog_id))
                or (conversation_id and _text(row.get("conversation_id")) == _text(conversation_id))
            )
        ]
    else:
        rows = all_rows
    query_modalities = {
        modality for modality, enabled in (
            ("image", bool(has_image)),
            ("file", bool(has_file)),
            ("voice", bool(has_voice)),
        ) if enabled
    }

    matches = [
        _candidate_score(
            query,
            row,
            dialog_id=str(dialog_id or ""),
            reference_followup=reference_followup,
            query_modalities=query_modalities,
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

    latest_same_dialog = max(
        (item for item in matches if bool(item.get("same_dialog"))),
        key=lambda item: (float(item.get("created_at") or 0.0), int(item.get("turn_index") or 0)),
        default=None,
    )
    best = matches[0] if matches else None

    # Strong continuity rules come before generic fuzzy similarity. A short
    # referential request belongs to the same authenticated dialog whenever a
    # previous turn exists, even when lexical overlap is almost zero.
    same_dialog_exists = bool(latest_same_dialog)
    marker = _continuation_marker(query)
    same_dialog_semantic = bool(
        best
        and (
            (
                best.get("same_dialog")
                and (
                    float(best.get("entity_overlap") or 0.0) >= 0.18
                    or float(best.get("context") or 0.0) >= 0.16
                    or float(best.get("semantic") or 0.0) >= 0.52
                )
            )
            or float(best.get("entity_overlap") or 0.0) >= 0.28
        )
    )
    short_contextual = (
        len(_tokens(query)) <= 12
        and _text(query).lower().startswith(("а ", "и ", "ну ", "так "))
        and (
            reference_followup
            or marker
            or len(_semantic_tokens(query)) == 0
        )
    )
    continuation = False

    has_new_attachment = bool(query_modalities)
    explicit_attachment_followup = has_new_attachment and reference_followup
    if history_request:
        continuation = False
    elif new_topic_request:
        continuation = False
    elif has_new_attachment and not explicit_attachment_followup:
        continuation = False
    elif latest_same_dialog and reference_followup:
        continuation = True
    elif latest_same_dialog and (marker or short_contextual) and len(_tokens(query)) <= 14:
        continuation = True
    elif same_dialog_semantic:
        continuation = True
    elif best and float(best.get("score") or 0.0) >= 0.60:
        continuation = True

    relation = "CONTINUE" if continuation else "NEW"

    # For a continuation, preserve an anchor turn plus nearby turns around it.
    selected_for_context: list[dict[str, Any]] = []
    if relation == "CONTINUE" and rows:
        anchor = best
        if reference_followup and latest_same_dialog:
            # Pure pronoun/follow-up queries have no reliable lexical subject;
            # resolve them to the latest turn in the authenticated dialogue.
            if float(best.get("entity_overlap") or 0.0) < 0.18 and not _looks_like_asset_reference(query):
                anchor = latest_same_dialog
        if anchor:
            anchor_msg = _text(anchor.get("message_id"))
            same_rows = [m for m in matches if bool(m.get("same_dialog"))]
            # Keep the anchor first, then relevant semantic matches.
            ordered = [anchor] + [
                m for m in matches
                if _text(m.get("message_id")) and _text(m.get("message_id")) != anchor_msg
            ]
            seen = set()
            for item in ordered:
                mid = _text(item.get("message_id"))
                key = mid or f"{item.get('created_at')}|{item.get('turn_index')}"
                if key in seen:
                    continue
                seen.add(key)
                selected_for_context.append(_compact_pair(item))
                if len(selected_for_context) >= 6:
                    break

            # If the anchor is not recent enough, add its immediate temporal
            # neighbors from the same dialog so the chain is understandable.
            if anchor_msg:
                all_same = [
                    r for r in rows
                    if _text(r.get("dialog_id")) == _text(anchor.get("dialog_id"))
                ]
                all_same.sort(key=lambda r: (float(r.get("created_at") or 0), int(r.get("turn_index") or 0)))
                pos = next((i for i, r in enumerate(all_same) if _text(r.get("message_id")) == anchor_msg), None)
                if pos is not None:
                    neighbors = all_same[max(0, pos-1):min(len(all_same), pos+2)]
                    existing_ids = {_text(x.get("message_id")) for x in selected_for_context}
                    for row in neighbors:
                        if _text(row.get("message_id")) not in existing_ids:
                            selected_for_context.append(_compact_pair(
                                _candidate_score(
                                    query,
                                    row,
                                    dialog_id=str(dialog_id or ""),
                                    reference_followup=reference_followup,
                                    query_modalities=query_modalities,
                                )
                            ))
        reason = (
            "same_dialog_referential"
            if reference_followup and latest_same_dialog
            else "same_dialog_contextual"
            if latest_same_dialog and (marker or short_contextual)
            else "semantic_memory_match"
        )
        anchor_for_relation = anchor if 'anchor' in locals() else (latest_same_dialog or best or {})
        active_topic = (
            anchor_for_relation.get("topic")
            or (selected_for_context[0].get("topic") if selected_for_context else "")
            or _text(query)[:140]
        )
    else:
        selected_for_context = []
        reason = "history_request" if history_request else "new_request"
        active_topic = _text(query)[:140]

    topics = _build_topic_index(rows)
    history_limit = _history_topic_limit(query, 7)
    history_topics = topics[:history_limit] if history_request else []
    topic_index = topics[:5]

    # Markdown is a presentation aid for the Provider; structured JSON fields
    # remain authoritative.
    topic_table_lines = ["| # | Тема | Последний запрос | Ходы |", "|---:|---|---|---:|"]
    for item in (history_topics or topics[:min(3, len(topics))]):
        topic_table_lines.append(
            f"| {item['number']} | {str(item['topic']).replace('|', '/')} | "
            f"{str(item['last_question']).replace('|', '/')} | {item['turns']} |"
        )
    topic_table_md = "\n".join(topic_table_lines)

    result = {
        "engine": "state_manager_dialogue_search_v4_asset_recall",
        "authenticated": True,
        "window_hours": DIALOGUE_WINDOW_HOURS,
        "dialog_id": str(dialog_id or ""),
        "conversation_id": str(conversation_id or ""),
        "query": str(query or ""),
        "total_pairs": len(rows),
        "candidate_count": len(matches),
        "relation": relation,
        "reason": reason,
        "relation_confidence": round(float(best["score"]) if best else (0.60 if latest_same_dialog and reference_followup else 0.0), 6),
        "continuation_marker": marker,
        "referential_followup": reference_followup,
        "history_request": history_request,
        "requested_topic_count": history_limit,
        "active_topic": active_topic,
        # Keep the same semantic anchor used to build selected_pairs.  Returning
        # latest_same_dialog unconditionally made later unrelated turns replace an
        # older image/file anchor needed for follow-up questions.
        "anchor": _compact_pair(
            (anchor if relation == "CONTINUE" and isinstance(locals().get("anchor"), dict) else None)
            or latest_same_dialog
            or best
        ) if (relation == "CONTINUE" and (locals().get("anchor") or latest_same_dialog or best)) else {},
        "matches": matches[:max(1, int(limit or 12))] if matches else [],
        "selected": selected_for_context[:6],
        "history_topics": history_topics,
        "topic_index": topic_index,
        "known_topic_count": len(topics),
        "topic_table_markdown": topic_table_md,
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
    limit: int = 12,
    has_image: bool = False,
    has_file: bool = False,
    has_voice: bool = False,
) -> dict[str, Any]:
    """One processor-facing call: hydrate + search + continuation decision."""
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
    return {
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
