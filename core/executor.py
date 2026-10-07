"""APRIL canonical processor.

Canonical route:
    authenticated WebReal Web request
        -> bot.py
        -> this processor
        -> provider_router (one provider call, English internal semantic layer)
        -> SceneContract
        -> bot.py
        -> WebReal Web

The processor owns dialogue persistence and sequence state. It does not import
legacy room modules or any removed interpretation/presentation files.
"""
from __future__ import annotations

from typing import Any
import re
import time
import uuid

from blocks.C_ARTIFACT_CONTRACT import (
    MachineRequest,
    MachineResponse,
    MachineScene,
    build_scene_contract,
)
from blocks.provider_router import generate_text
from blocks.state_manager import (
    get_state,
    hydrate,
    begin_new_topic,
    continue_topic,
    set_language,
    set_relation,
    append_pair,
    get_dialogue_pairs,
)


PROCESSOR_VERSION = "april_processor_12h_canonical_v3"
CANONICAL_ROUTE = "/api/v1/chat"
TRANSLATION_ROUTE_VERSION = "botru_translation_v1"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _detect_language(text: str, requested: str = "") -> str:
    requested = _text(requested).lower()
    if requested and requested not in {"auto", "default"}:
        return requested

    value = text.lower()
    if re.search(r"[а-яёіїєґ]", value):
        return "uk" if re.search(r"[іїєґ]", value) else "ru"
    if re.search(r"[\u3040-\u30ff]", text):
        return "ja"
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"
    if re.search(r"[\uac00-\ud7af]", text):
        return "ko"
    if re.search(r"[\u0600-\u06ff]", text):
        return "ar"
    if re.search(r"[\u0900-\u097f]", text):
        return "hi"
    if re.search(r"[\u0370-\u03ff]", text):
        return "el"
    if re.search(r"[\u0400-\u04ff]", text):
        return "ru"
    return "en"


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[\w\u0080-\uffff]+", text.lower())
        if len(token) > 1
    }


def _context_score(current: str, previous: dict[str, Any], language: str) -> float:
    current_tokens = _tokens(current)
    if not current_tokens:
        return 0.0

    previous_language = _text(previous.get("language")).lower()
    if previous_language == language:
        previous_text = (
            f"{previous.get('user_text') or ''} "
            f"{previous.get('april_text') or ''}"
        )
    else:
        previous_text = (
            f"{previous.get('user_text_en') or ''} "
            f"{previous.get('april_text_en') or ''}"
        )

    previous_tokens = _tokens(previous_text)
    if not previous_tokens:
        return 0.0
    return len(current_tokens & previous_tokens) / max(1, len(current_tokens))


_CONTINUATION_MARKERS = (
    # RU / UK
    "это", "этот", "эта", "эту", "они", "он", "она", "там", "здесь",
    "так", "такой", "такая", "такое", "также", "дальше", "ещё", "еще",
    "продолж", "и как", "а что", "а если", "а сколько", "и сколько",
    "а где", "и где", "а когда", "и когда", "чем это", "почему это",
    "це", "цей", "ця", "цю", "вони", "він", "вона", "там", "тут",
    "так", "такий", "така", "таке", "далі", "ще", "продовж",
    # EN
    "this", "that", "it", "they", "there", "here", "then", "also",
    "continue", "more", "next", "again", "what about", "and how",
    # ES / PT
    "esto", "esta", "este", "eso", "esa", "ellos", "ellas", "ahí",
    "aquí", "entonces", "también", "continúa", "continuar", "más",
    "isso", "isto", "este", "esta", "eles", "elas", "aqui", "ali",
    "então", "também", "continuar", "mais",
    # FR / IT
    "ceci", "cela", "cette", "cet", "ils", "elles", "ici", "là",
    "alors", "aussi", "continuer", "encore",
    "questo", "questa", "quello", "quella", "loro", "qui", "lì",
    "allora", "anche", "continuare", "ancora",
    # DE / PL
    "dies", "diese", "dieser", "das", "sie", "dort", "hier", "dann",
    "auch", "weiter", "noch", "mehr",
    "to", "ten", "ta", "tę", "oni", "one", "tam", "tutaj", "dalej",
    "jeszcze", "więcej", "kontynuuj",
)


def _has_continuation_marker(text: str) -> bool:
    lower = _text(text).lower()
    if not lower:
        return False
    return any(
        lower == marker
        or lower.startswith(f"{marker} ")
        or f" {marker} " in lower
        for marker in _CONTINUATION_MARKERS
    )


def _interpret(
    current: str,
    pairs: list[dict[str, Any]],
    state: dict[str, Any],
    language: str,
) -> dict[str, Any]:
    """Deterministic relation gate; no second model call and no legacy router."""
    last = pairs[-1] if pairs else {}
    score = _context_score(current, last, language) if last else 0.0
    marker = _has_continuation_marker(current)

    relation = (
        "CONTINUE"
        if last and (score >= 0.16 or marker)
        else "NEW"
    )

    topic = _text((state.get("active_sequence") or {}).get("topic"))
    if relation == "NEW":
        topic = current[:120]

    return {
        "dialogue_relation": relation,
        "relation_confidence": round(
            min(0.99, 0.55 + score * 0.35 + (0.09 if marker else 0.0)),
            3,
        ),
        "relation_reason": (
            "recent lexical continuity"
            if score >= 0.16
            else "continuation marker"
            if marker
            else "new request"
        ),
        "canonical_topic": topic,
        "selected_memory_index": (
            len(pairs) - 1 if relation == "CONTINUE" and pairs else -1
        ),
    }


def _compact_chain(rows: list[dict[str, Any]], limit: int = 4) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    for idx, row in enumerate(rows[-limit:], 1):
        chain.append(
            {
                "position": idx,
                "language": _text(row.get("language") or "en"),
                "user_en": _text(row.get("user_text_en")),
                "april_en": _text(row.get("april_text_en")),
                "user": _text(row.get("user_text")),
                "april": _text(row.get("april_text")),
            }
        )
    return chain


def _build_context_plan(
    current: str,
    pairs: list[dict[str, Any]],
    interpretation: dict[str, Any],
) -> dict[str, Any]:
    relation = interpretation["dialogue_relation"]
    selected = pairs[-4:] if relation == "CONTINUE" else []
    candidate = pairs[-1:] if relation == "NEW" and pairs else []

    return {
        "relation": relation,
        "context_mode": (
            "selected_12h_chain"
            if selected
            else "recent_context_candidate"
            if candidate
            else "current_request_only"
        ),
        "resolved_request_en": "",
        "current_request": current,
        "dialogue_chain": _compact_chain(selected, 4),
        "recent_context_candidate": _compact_chain(candidate, 1),
        "translation": {
            "version": TRANSLATION_ROUTE_VERSION,
            "internal_language": "en",
            "stage": "provider_single_call",
        },
    }


def _scene_from_response(
    request: MachineRequest,
    response: MachineResponse,
    flow_id: str,
    interpretation: dict[str, Any],
    sequence: dict[str, Any],
    translation: dict[str, Any],
) -> dict[str, Any]:
    scene = MachineScene(
        scene_id=str(uuid.uuid4()),
        turn_id=str(uuid.uuid4()),
        flow_id=flow_id,
        topic_group=interpretation.get("canonical_topic", ""),
        continuation=interpretation.get("dialogue_relation") == "CONTINUE",
        user_id=request.fiber.identity.user_id,
        conversation_id=str(request.conversation.get("conversation_id") or ""),
        dialogue_sequence_id=str(sequence.get("sequence_id") or ""),
        sequence_turn_index=int(sequence.get("turn_index") or 0),
        active_task={},
        dialogue_state={
            "relation": interpretation.get("dialogue_relation"),
            "topic": interpretation.get("canonical_topic", ""),
            "reason": interpretation.get("relation_reason", ""),
        },
        dialogue_development={
            "relation_confidence": interpretation.get("relation_confidence", 0),
        },
        result_event={
            "status": "complete",
            "provider_calls": 1,
            "canonical_route": CANONICAL_ROUTE,
        },
        blocks=list(response.render_blocks or []),
        metadata={
            **dict(response.metadata or {}),
            "user_id": request.fiber.identity.user_id,
            "translation": translation,
            "canonical_route": CANONICAL_ROUTE,
        },
    )
    contract = build_scene_contract(scene)
    return {
        "answer": response.answer,
        "content": response.content or response.answer,
        "summary": response.summary,
        "render_blocks": contract.render_blocks,
        "scene_contract": contract.__dict__,
    }


async def execute(
    user_id: str,
    chat_id: Any = None,
    text: str = "",
    *,
    internal_text: str = "",
    display_language: str = "auto",
    flow_id: str = "",
    conversation_id: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    uid = _text(user_id)
    original_text = _text(text)
    request_text = _text(internal_text or original_text)

    if not uid:
        raise ValueError("USER_ID_REQUIRED")
    if not request_text:
        raise ValueError("EMPTY_REQUEST")

    # The live 12-hour dialogue belongs only to State Manager.
    # No PostgreSQL/storage module participates in the canonical chat route.
    language = _detect_language(original_text or request_text, display_language)
    state = hydrate(uid)
    set_language(uid, language)
    pairs = get_dialogue_pairs(uid)

    interpretation = _interpret(
        request_text,
        pairs,
        state,
        language,
    )
    relation = interpretation["dialogue_relation"]
    topic = interpretation.get("canonical_topic", "")

    if relation == "CONTINUE":
        sequence = continue_topic(uid, topic=topic)
    else:
        sequence = begin_new_topic(uid, topic=topic)

    plan = _build_context_plan(request_text, pairs, interpretation)
    flow = _text(flow_id) or str(uuid.uuid4())

    translation = {
        "version": TRANSLATION_ROUTE_VERSION,
        "input_language": language,
        "internal_language": "en",
        "output_language": language,
        "mode": "provider_internal_single_call",
    }

    request = MachineRequest(
        request_id=flow,
        goal="answer_user_request",
        intent=interpretation,
        conversation={
            "conversation_id": _text(conversation_id),
            "current_request": request_text,
            "resolved_request": request_text,
            "display_language": language,
        },
        memory={
            "window_hours": 12,
            "pair_count": len(pairs),
        },
        requested_outputs=["text"],
        routing={
            "single_route": True,
            "canonical_route": CANONICAL_ROUTE,
            "processor_version": PROCESSOR_VERSION,
            "flow_id": flow,
            "translation_route": translation,
            "provider_context_plan": plan,
        },
        constraints={
            "display_language": language,
            "provider_output_language": language,
            "internal_language": "en",
            "no_legacy_route": True,
        },
    )
    request.fiber.identity.user_id = uid

    started = time.perf_counter()
    provider = await generate_text(request)
    provider_ms = round((time.perf_counter() - started) * 1000, 1)

    raw = provider.get("machine_response") if isinstance(provider, dict) else None
    if not isinstance(raw, dict):
        raise RuntimeError("PROVIDER_CONTRACT_MISSING")

    metadata = dict(raw.get("metadata") or {})
    internal_request_en = _text(metadata.get("internal_request_en"))
    internal_answer_en = _text(metadata.get("internal_answer_en"))
    answer = _text(raw.get("answer") or raw.get("content"))
    if not answer:
        raise RuntimeError("CANONICAL_ANSWER_MISSING")

    translation.update(
        {
            "translated_input_en": bool(internal_request_en),
            "translated_answer_en": bool(internal_answer_en),
            "source": "provider",
        }
    )

    response = MachineResponse(
        answer=answer,
        content=_text(raw.get("content") or answer),
        summary=_text(raw.get("summary") or answer[:180]),
        render_blocks=list(raw.get("render_blocks") or []),
        metadata={
            **metadata,
            "provider_ms": provider_ms,
            "translation": translation,
        },
        artifacts=list(raw.get("artifacts") or []),
    )

    result = _scene_from_response(
        request,
        response,
        flow,
        interpretation,
        sequence,
        translation,
    )

    append_pair(
        uid,
        {
            "created_at": time.time(),
            "turn_index": int(sequence.get("turn_index") or 0),
            "user_text": original_text or request_text,
            "april_text": answer,
            "user_text_en": internal_request_en,
            "april_text_en": internal_answer_en,
            "language": language,
            "relation": relation,
        },
    )
    saved = True

    set_relation(
        uid,
        relation,
        topic=topic,
        selected_index=interpretation.get("selected_memory_index", -1),
    )

    result.update(
        {
            "flow_id": flow,
            "processor_version": PROCESSOR_VERSION,
            "provider_calls_per_request": 1,
            "provider_context_plan": plan,
            "provider_context_authority": "PROCESSOR",
            "display_language": language,
            "internal_language": "en",
            "translation": translation,
            "memory_window_hours": 12,
            "memory_pair_count": len(get_state(uid).get("dialogue_pairs") or []),
            "memory_saved": saved,
        }
    )
    return result
