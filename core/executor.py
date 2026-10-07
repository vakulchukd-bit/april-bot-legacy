"""APRIL canonical processor.

Route: authenticated request -> processor/context -> provider -> SceneContract -> Web.
The processor owns persistence policy. StateManager owns only the live 12h window.
"""
from __future__ import annotations

from typing import Any
import re
import time
import uuid

from blocks.C_ARTIFACT_CONTRACT import MachineRequest, MachineResponse, MachineScene, build_scene_contract
from blocks.provider_router import generate_text
from blocks.state_manager import (
    get_state, hydrate, begin_new_topic, continue_topic, append_pair, set_language, set_relation,
)
from storage import init_db, load_dialogue_pairs, save_dialogue_pair

PROCESSOR_VERSION = "april_processor_12h_state_v2"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _detect_language(text: str, requested: str = "") -> str:
    requested = _text(requested).lower()
    if requested and requested not in {"auto", "default"}:
        return requested
    if re.search(r"[а-яёіїєґ]", text.lower()):
        return "uk" if re.search(r"[іїєґ]", text.lower()) else "ru"
    if re.search(r"[\u3040-\u30ff]", text): return "ja"
    if re.search(r"[\u4e00-\u9fff]", text): return "zh"
    if re.search(r"[\uac00-\ud7af]", text): return "ko"
    if re.search(r"[\u0600-\u06ff]", text): return "ar"
    if re.search(r"[\u0900-\u097f]", text): return "hi"
    return "en"


def _tokens(text: str) -> set[str]:
    return {x for x in re.findall(r"[\w\u0400-\u04ff]+", text.lower()) if len(x) > 2}


def _context_score(current: str, previous: dict[str, Any]) -> float:
    cur = _tokens(current)
    old = _tokens(f"{previous.get('user_text') or ''} {previous.get('april_text') or ''}")
    if not cur or not old:
        return 0.0
    return len(cur & old) / max(1, len(cur))


def _interpret(current: str, pairs: list[dict[str, Any]], state: dict[str, Any]) -> dict[str, Any]:
    """Small deterministic continuation detector; no extra model call."""
    last = pairs[-1] if pairs else {}
    score = _context_score(current, last) if last else 0.0
    lower = current.lower()
    continuation_markers = (
        "это", "этот", "эта", "эту", "они", "он", "она", "там", "здесь", "тогда",
        "продолж", "дальше", "ещё", "так", "а если", "и как", "а что", "почему",
        "this", "that", "it", "they", "continue", "more", "then", "what about",
    )
    marker = any(lower.startswith(x) or f" {x} " in lower for x in continuation_markers)
    relation = "CONTINUE" if last and (score >= 0.16 or marker) else "NEW"
    topic = str((state.get("active_sequence") or {}).get("topic") or "").strip()
    if relation == "NEW":
        topic = current[:120]
    return {
        "dialogue_relation": relation,
        "relation_confidence": round(min(0.99, 0.55 + score * 0.45), 3),
        "relation_reason": "recent lexical continuity" if relation == "CONTINUE" else "new request",
        "canonical_topic": topic,
        "selected_memory_index": len(pairs) - 1 if relation == "CONTINUE" and pairs else -1,
    }


def _build_context_plan(current: str, pairs: list[dict[str, Any]], interpretation: dict[str, Any]) -> dict[str, Any]:
    relation = interpretation["dialogue_relation"]
    selected = pairs[-4:] if relation == "CONTINUE" else []
    chain = []
    for idx, row in enumerate(selected, 1):
        chain.append({
            "position": idx,
            "user_en": row.get("user_text_en") or row.get("user_text") or "",
            "april_en": row.get("april_text_en") or row.get("april_text") or "",
        })
    return {
        "relation": relation,
        "context_mode": "selected_12h_chain" if chain else "current_request_only",
        "resolved_request_en": current,
        "dialogue_chain": chain,
    }


def _scene_from_response(request: MachineRequest, response: MachineResponse, flow_id: str, interpretation: dict[str, Any], sequence: dict[str, Any]) -> dict:
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
        dialogue_development={"relation_confidence": interpretation.get("relation_confidence", 0)},
        result_event={"status": "complete", "provider_calls": 1},
        blocks=list(response.render_blocks or []),
        metadata={**dict(response.metadata or {}), "user_id": request.fiber.identity.user_id},
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
    display_language: str = "en",
    flow_id: str = "",
    conversation_id: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    uid = _text(user_id)
    request_text = _text(internal_text or text)
    if not uid:
        raise ValueError("USER_ID_REQUIRED")
    if not request_text:
        raise ValueError("EMPTY_REQUEST")

    # Processor-owned DB lifecycle. Fail fast only when initialization is required;
    # existing storage functions still degrade safely when DB is unavailable.
    try:
        init_db()
    except Exception:
        pass

    rows = load_dialogue_pairs(uid, limit=0)
    state = hydrate(uid, rows)
    language = _detect_language(text or request_text, display_language)
    set_language(uid, language)
    pairs = state.get("dialogue_pairs") or []

    interpretation = _interpret(request_text, pairs, state)
    relation = interpretation["dialogue_relation"]
    topic = interpretation.get("canonical_topic", "")
    if relation == "CONTINUE":
        sequence = continue_topic(uid, topic=topic)
    else:
        sequence = begin_new_topic(uid, topic=topic)

    plan = _build_context_plan(request_text, pairs, interpretation)
    flow = _text(flow_id) or str(uuid.uuid4())
    request = MachineRequest(
        request_id=flow,
        goal="answer_user_request",
        intent=interpretation,
        conversation={
            "conversation_id": _text(conversation_id),
            "current_request": request_text,
            "resolved_request": request_text,
        },
        memory={"window_hours": 12, "pair_count": len(pairs)},
        requested_outputs=["text"],
        routing={"single_route": True, "processor_version": PROCESSOR_VERSION},
        constraints={"display_language": language, "provider_output_language": language},
    )
    request.fiber.identity.user_id = uid
    request.routing["flow_id"] = flow
    request.dialogue_contract = {"relation": relation, "sequence_id": sequence.get("sequence_id"), "turn_index": sequence.get("turn_index")} if hasattr(request, "dialogue_contract") else None
    request.provider_context_plan = plan if hasattr(request, "provider_context_plan") else None

    started = time.perf_counter()
    provider = await generate_text(request)
    provider_ms = round((time.perf_counter() - started) * 1000, 1)
    raw = provider.get("machine_response") if isinstance(provider, dict) else None
    if not isinstance(raw, dict):
        raise RuntimeError("PROVIDER_CONTRACT_MISSING")
    answer = _text(raw.get("answer") or raw.get("content"))
    if not answer:
        raise RuntimeError("CANONICAL_ANSWER_MISSING")

    response = MachineResponse(
        answer=answer,
        content=_text(raw.get("content") or answer),
        summary=_text(raw.get("summary") or answer[:180]),
        render_blocks=list(raw.get("render_blocks") or []),
        metadata={**dict(raw.get("metadata") or {}), "provider_ms": provider_ms},
        artifacts=list(raw.get("artifacts") or []),
    )

    result = _scene_from_response(request, response, flow, interpretation, sequence)

    # Persistence policy lives here; state_manager receives only the committed pair.
    saved = False
    try:
        saved = bool(save_dialogue_pair(
            uid,
            _text(text or request_text),
            answer,
            user_text_en=request_text,
            april_text_en=answer,
            language=language,
            relation=relation,
            turn_index=int(sequence.get("turn_index") or 0),
        ))
    finally:
        if saved:
            fresh = load_dialogue_pairs(uid, limit=0)
            hydrate(uid, fresh)
            append_pair(uid, {}) if False else None
    set_relation(uid, relation, topic=topic, selected_index=interpretation.get("selected_memory_index", -1))

    result.update({
        "flow_id": flow,
        "processor_version": PROCESSOR_VERSION,
        "provider_calls_per_request": 1,
        "provider_context_plan": plan,
        "provider_context_authority": "PROCESSOR",
        "display_language": language,
        "internal_language": "en",
        "memory_window_hours": 12,
        "memory_pair_count": len(get_state(uid).get("dialogue_pairs") or []),
        "memory_saved": saved,
    })
    return result
