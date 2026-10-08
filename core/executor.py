"""APRIL canonical Exkrutor processor.

Only /api/v1/chat reaches this processor. Bot.ru owns translation and input
normalization; Exkrutor owns identity binding, 12h DB memory, continuation/new
topic decision, C_ARTIFACT room selection metadata, provider execution and the
SceneContract returned to RenderMessage.
"""
from __future__ import annotations

from typing import Any
import re
import time
import uuid

from blocks.C_ARTIFACT_CONTRACT import MachineRequest, MachineResponse, MachineScene, build_scene_contract, list_registered_rooms
from blocks.dialog_identity import resolve_dialog_identity
from blocks.interpretation_identity import build_interpretation_identity
from blocks.provider_router import generate_text
from storage import load_dialogue_pairs, save_dialogue_pair, search_dialogue_memory

PROCESSOR_VERSION = "april_exkrutor_single_route_v5"
CANONICAL_ROUTE = "/api/v1/chat"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _tokens(text: str) -> set[str]:
    return {x for x in re.findall(r"[\w\u0080-\uffff]+", _text(text).lower()) if len(x) > 1}


def _score(current: str, previous: dict[str, Any]) -> float:
    a = _tokens(current)
    b = _tokens("%s %s" % (previous.get("user_text_en") or "", previous.get("april_text_en") or ""))
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, len(a))


def _interpret(current_en: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    last = rows[-1] if rows else {}
    score = _score(current_en, last) if last else 0.0
    low = _text(current_en).lower()
    marker = any(low == m or low.startswith(m + " ") for m in ("this", "that", "it", "continue", "more", "again", "also", "and how", "what about"))
    relation = "CONTINUE" if last and (score >= 0.16 or marker) else "NEW"
    topic = _text(last.get("user_text_en"))[:160] if relation == "CONTINUE" else _text(current_en)[:160]
    return {
        "dialogue_relation": relation,
        "relation_confidence": round(min(0.99, 0.55 + score * 0.35 + (0.09 if marker else 0.0)), 3),
        "relation_reason": "recent lexical continuity" if score >= 0.16 else "continuation marker" if marker else "new request",
        "canonical_topic": topic,
        "selected_memory_index": len(rows) - 1 if relation == "CONTINUE" and rows else -1,
    }


def _rooms_for_request(text: str) -> list[dict[str, Any]]:
    low = _text(text).lower()
    result = []
    for room in list_registered_rooms():
        caps = set(room.capabilities)
        if room.room_id.lower() in low or any(cap.replace("_", " ") in low for cap in caps):
            result.append({"room": room.room_id, "module": room.module, "capabilities": list(room.capabilities), "artifact_type": room.artifact_type, "is_engine": room.is_engine})
    return result


def _context_plan(current_en: str, rows: list[dict[str, Any]], interpretation: dict[str, Any]) -> dict[str, Any]:
    selected = rows[-4:] if interpretation["dialogue_relation"] == "CONTINUE" else []
    chain = [{"position": i + 1, "user_en": _text(r.get("user_text_en")), "april_en": _text(r.get("april_text_en"))} for i, r in enumerate(selected)]
    return {
        "relation": interpretation["dialogue_relation"],
        "current_request_en": current_en,
        "dialogue_chain": chain,
        "recent_context_candidate": [],
        "window_hours": 12,
    }


def _scene(request: MachineRequest, response: MachineResponse, identity: dict[str, str], interpretation: dict[str, Any], turn_index: int, translation: dict[str, Any]) -> dict[str, Any]:
    scene = MachineScene(
        scene_id=str(uuid.uuid4()),
        turn_id=identity["message_id"] or str(uuid.uuid4()),
        flow_id=identity["flow_id"],
        topic_group=interpretation.get("canonical_topic", ""),
        continuation=interpretation.get("dialogue_relation") == "CONTINUE",
        user_id=identity["user_id"],
        conversation_id=identity["conversation_id"],
        dialogue_sequence_id=identity["dialog_id"],
        sequence_turn_index=turn_index,
        active_task={},
        dialogue_state={"relation": interpretation.get("dialogue_relation"), "topic": interpretation.get("canonical_topic", ""), "reason": interpretation.get("relation_reason", "")},
        dialogue_development={"relation_confidence": interpretation.get("relation_confidence", 0), "interpretation_id": identity["interpretation_id"]},
        result_event={"status": "complete", "provider_calls": 1, "canonical_route": CANONICAL_ROUTE},
        blocks=list(response.render_blocks or []),
        metadata={**dict(response.metadata or {}), "identity": identity, "translation": translation, "canonical_route": CANONICAL_ROUTE},
    )
    contract = build_scene_contract(scene)
    contract.authenticated_scope = {"user_id": identity["user_id"], "conversation_id": identity["conversation_id"], "dialog_id": identity["dialog_id"], "message_id": identity["message_id"], "interpretation_id": identity["interpretation_id"]}
    return {"answer": response.answer, "content": response.content or response.answer, "summary": response.summary, "render_blocks": contract.render_blocks, "scene_contract": contract.__dict__}


async def execute(user_id: str, chat_id: Any = None, text: str = "", *, internal_text: str = "", display_language: str = "auto", flow_id: str = "", conversation_id: str = "", dialog_id: str = "", message_id: str = "", interpretation_id: str = "", visual_context: list[dict[str, Any]] | None = None, attachments: list[dict[str, Any]] | None = None, translation: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    uid = _text(user_id)
    original = _text(text)
    current_en = _text(internal_text or original)
    if not uid:
        raise ValueError("USER_ID_REQUIRED")
    if not current_en and not visual_context:
        raise ValueError("EMPTY_REQUEST")

    payload_identity = {
        "dialog_id": dialog_id or conversation_id,
        "conversation_id": conversation_id or dialog_id,
        "message_id": message_id,
        "flow_id": flow_id,
    }
    identity = resolve_dialog_identity(payload_identity, user_id=uid, flow_id=flow_id)
    interp = build_interpretation_identity(
        april_id=identity["user_id"],
        conversation_id=identity["conversation_id"],
        dialog_id=identity["dialog_id"],
        message_id=identity["message_id"],
        interpretation_id=interpretation_id,
        flow_id=identity["flow_id"],
    )
    identity["interpretation_id"] = interp["interpretation_id"]
    rows = load_dialogue_pairs(uid, limit=0)
    memory_search = search_dialogue_memory(uid, current_en, limit=8) if current_en else {"matches": []}
    interpretation = _interpret(current_en, rows)
    turn_index = max([int(r.get("turn_index") or 0) for r in rows], default=-1) + 1
    if interpretation["dialogue_relation"] == "NEW":
        turn_index = 0

    plan = _context_plan(current_en, rows, interpretation)
    selected_rooms = _rooms_for_request(current_en)
    translation_meta = dict(translation or {})
    translation_meta.setdefault("internal_language", "en")

    request = MachineRequest(
        request_id=identity["flow_id"] or str(uuid.uuid4()),
        goal="answer_user_request",
        intent={**interpretation, "interpretation_id": identity["interpretation_id"]},
        conversation={"conversation_id": identity["conversation_id"], "dialog_id": identity["dialog_id"], "message_id": identity["message_id"], "current_request": original, "resolved_request": current_en, "display_language": display_language},
        memory={"window_hours": 12, "pair_count": len(rows), "search": memory_search},
        visual_context={"items": visual_context or []},
        available_tools=[r.room_id for r in list_registered_rooms()],
        requested_outputs=["text", "scene"],
        required_competencies=[cap for r in selected_rooms for cap in r["capabilities"]],
        routing={"single_route": True, "canonical_route": CANONICAL_ROUTE, "processor_version": PROCESSOR_VERSION, "flow_id": identity["flow_id"], "dialog_id": identity["dialog_id"], "interpretation_id": identity["interpretation_id"], "selected_rooms": selected_rooms, "provider_context_plan": plan},
        constraints={"display_language": display_language, "provider_output_language": display_language, "internal_language": "en", "no_legacy_route": True},
    )
    request.fiber.identity.user_id = uid
    request.metadata = {"identity": identity, "translation": translation_meta, "attachments": attachments or []}

    started = time.perf_counter()
    provider = await generate_text(request)
    provider_ms = round((time.perf_counter() - started) * 1000, 1)
    raw = provider.get("machine_response") if isinstance(provider, dict) else None
    if not isinstance(raw, dict):
        raise RuntimeError("PROVIDER_CONTRACT_MISSING")
    answer = _text(raw.get("answer") or raw.get("content"))
    if not answer:
        raise RuntimeError("CANONICAL_ANSWER_MISSING")
    metadata = dict(raw.get("metadata") or {})
    metadata.update({"provider_ms": provider_ms, "identity": identity, "selected_rooms": selected_rooms})
    response = MachineResponse(answer=answer, content=_text(raw.get("content") or answer), summary=_text(raw.get("summary") or answer[:180]), render_blocks=list(raw.get("render_blocks") or []), metadata=metadata, artifacts=list(raw.get("artifacts") or []))
    result = _scene(request, response, identity, interpretation, turn_index, translation_meta)

    saved = save_dialogue_pair(uid, original or current_en, answer, turn_index=turn_index, user_en=current_en, april_en=_text(metadata.get("internal_answer_en")) or answer, language=display_language, relation=interpretation["dialogue_relation"], dialog_id=identity["dialog_id"], conversation_id=identity["conversation_id"], message_id=identity["message_id"], interpretation_id=identity["interpretation_id"])
    result.update({"april_id": uid, "conversation_id": identity["conversation_id"], "dialog_id": identity["dialog_id"], "message_id": identity["message_id"], "interpretation_id": identity["interpretation_id"], "flow_id": identity["flow_id"], "processor_version": PROCESSOR_VERSION, "display_language": display_language, "internal_language": "en", "translation": translation_meta, "memory_window_hours": 12, "memory_pair_count": len(load_dialogue_pairs(uid, limit=0)), "memory_saved": saved})
    return result
