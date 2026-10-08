"""APRIL canonical Exkrutor processor.

Processor responsibilities:
1. accept one normalized request from bot.ru;
2. bind authenticated user/turn identity;
3. synchronize the 12h dialogue state from PostgreSQL through state_manager;
4. run the state-manager search/rerank engine;
5. build the single Interpretation structure;
6. ask C_ARTIFACT_CONTRACT for the rooms/renderers required by that interpretation;
7. make one structured Provider/Luna call;
8. optionally hand an image generation spec to the existing C_APRIL_IMAGES_GENERATOR;
9. build one SceneContract and verify identity before Web delivery;
10. persist the final USER↔APRIL pair.

No alternate route, room register or second memory store is created here.
"""
from __future__ import annotations

from typing import Any
import json
import os
import re
import time
import uuid

from blocks.C_ARTIFACT_CONTRACT import (
    MachineRequest,
    MachineResponse,
    MachineScene,
    build_scene_contract,
    get_web_renderer_registration,
    list_registered_rooms,
)
from blocks.dialog_identity import resolve_dialog_identity, assert_identity_match
from blocks.interpretation_identity import (
    build_interpretation_identity,
    build_interpretation,
)
from blocks.provider_router import generate_text
from blocks.state_manager import prepare_dialogue_context
from blocks.text_module import package_provider_response
from storage import (
    init_db,
    is_authenticated_user,
    load_dialogue_assets,
    save_dialogue_asset,
    save_dialogue_pair,
)


PROCESSOR_VERSION = "april_exkrutor_single_route_v7_dialogue_assets"
CANONICAL_ROUTE = "/api/v1/chat"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _identity_tuple(identity: dict[str, Any]) -> dict[str, str]:
    return {
        "user_id": _text(identity.get("user_id")),
        "conversation_id": _text(identity.get("conversation_id")),
        "dialog_id": _text(identity.get("dialog_id")),
        "message_id": _text(identity.get("message_id")),
        "flow_id": _text(identity.get("flow_id")),
        "interpretation_id": _text(identity.get("interpretation_id")),
    }


def _select_rooms(interpretation: dict[str, Any]) -> list[dict[str, Any]]:
    """Select registered rooms/engines only from C_ARTIFACT_CONTRACT."""
    intent = interpretation.get("intent") or {}
    input_data = interpretation.get("input") or {}
    selected: list[dict[str, Any]] = []

    required_capabilities: list[str] = []
    if intent.get("wants_image"):
        required_capabilities.extend(["image_generation", "png", "gallery"])
    if intent.get("wants_links"):
        required_capabilities.extend(["link", "url", "preview", "web"])
    if intent.get("wants_code"):
        required_capabilities.extend(["software", "code", "analysis"])
    if intent.get("wants_formula"):
        required_capabilities.extend(["formula", "latex", "math"])
    if intent.get("wants_diagram"):
        required_capabilities.extend(["diagram", "geometry"])
    if intent.get("wants_table"):
        required_capabilities.extend(["table", "structured_data", "tabular"])

    # Domain hints from the current request are additive, never authoritative over
    # the Interpretation decision.
    required_capabilities.extend(
        str(x) for x in interpretation.get("routing_capabilities", []) if str(x)
    )

    seen: set[str] = set()
    for room in list_registered_rooms():
        if not room.enabled or room.room_id in seen:
            continue
        caps = set(room.capabilities)
        if caps.intersection(required_capabilities):
            selected.append(
                {
                    "room": room.room_id,
                    "module": room.module,
                    "capabilities": list(room.capabilities),
                    "artifact_type": room.artifact_type,
                    "room_type": room.room_type,
                    "is_engine": room.is_engine,
                }
            )
            seen.add(room.room_id)

    # Text is always a legal primary output. C-ARTIFACT remains the renderer
    # authority even when no specialized room was selected.
    if not selected:
        selected = [
            {
                "room": room.room_id,
                "module": room.module,
                "capabilities": list(room.capabilities),
                "artifact_type": room.artifact_type,
                "room_type": room.room_type,
                "is_engine": room.is_engine,
            }
            for room in list_registered_rooms(include_engines=False)
            if room.room_id in {"it", "WEB_ROOM"}
        ][:1]

    # For image generation, keep the generator first and gallery renderer second.
    if intent.get("wants_image"):
        ordered: list[dict[str, Any]] = []
        for preferred in ("APRIL_IMAGES_GENERATION", "GALLERY_ROOM"):
            for item in selected:
                if item["room"] == preferred and item not in ordered:
                    ordered.append(item)
        selected = ordered + [
            item for item in selected if item not in ordered
        ]

    return selected


def _renderer_plan(
    interpretation: dict[str, Any],
    selected_rooms: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Ask C-ARTIFACT for concrete Web renderers; no local renderer map."""
    outputs = list((interpretation.get("intent") or {}).get("requested_outputs") or ["text"])
    plan: list[dict[str, Any]] = []
    seen: set[str] = set()

    for output in outputs:
        key = str(output or "text").strip().lower()
        if key in seen:
            continue
        seen.add(key)
        reg = get_web_renderer_registration(key)
        plan.append(
            {
                "output": key,
                "renderer": reg.get("renderer", ""),
                "viewer": reg.get("viewer", ""),
                "payload_keys": list(reg.get("payload_keys") or []),
                "presentation_engine": "McDowell",
                "source_rooms": [
                    item["room"]
                    for item in selected_rooms
                    if item.get("artifact_type") in {key, "gallery" if key == "image" else key}
                    or key in set(item.get("capabilities") or [])
                ],
            }
        )
    return plan


def _build_image_spec(
    raw: dict[str, Any],
    interpretation: dict[str, Any],
    identity: dict[str, str],
) -> dict[str, Any] | None:
    # Hard safety gate: attachment presence or Provider hallucination can never
    # authorize image generation. Only Interpretation may authorize it.
    if not bool((interpretation.get("intent") or {}).get("wants_image")):
        return None

    artifacts = raw.get("artifacts")
    if isinstance(artifacts, list):
        for item in artifacts:
            if not isinstance(item, dict):
                continue
            if str(item.get("type") or item.get("artifact_type") or "").lower() == "image":
                spec = item.get("spec") or item.get("render_spec")
                if isinstance(spec, dict):
                    clean = dict(spec)
                    clean.setdefault("schema", "april_image_spec_v1")
                    clean.setdefault("generator_signal", "C_APRIL_IMAGES_GENERATOR")
                    clean.setdefault("request_anchor", _text((interpretation.get("input") or {}).get("original_request")))
                    clean.setdefault("flow_id", identity["flow_id"])
                    clean.setdefault("turn_id", identity["message_id"])
                    clean.setdefault("user_id", identity["user_id"])
                    clean.setdefault("conversation_id", identity["conversation_id"])
                    clean.setdefault("dialogue_sequence_id", identity["dialog_id"])
                    clean.setdefault("dialogue_development", interpretation.get("dialogue") or {})
                    return clean

    direct = raw.get("image_spec")
    if isinstance(direct, dict):
        clean = dict(direct)
        clean.setdefault("schema", "april_image_spec_v1")
        clean.setdefault("generator_signal", "C_APRIL_IMAGES_GENERATOR")
        clean.setdefault("request_anchor", _text((interpretation.get("input") or {}).get("original_request")))
        clean.setdefault("flow_id", identity["flow_id"])
        clean.setdefault("turn_id", identity["message_id"])
        clean.setdefault("user_id", identity["user_id"])
        clean.setdefault("conversation_id", identity["conversation_id"])
        clean.setdefault("dialogue_sequence_id", identity["dialog_id"])
        return clean

    if (interpretation.get("intent") or {}).get("wants_image"):
        request_text = _text((interpretation.get("input") or {}).get("original_request"))
        if not request_text:
            return None
        return {
            "schema": "april_image_spec_v1",
            "prompt": request_text,
            "width": 512,
            "height": 512,
            "quality": "low",
            "visual_context": {},
            "openai_structured_visual_plan_raw": raw,
            "openai_structured_visual_plan_semantic": _text(
                raw.get("image_prompt")
                or raw.get("visual_prompt")
                or request_text
            ),
            "request_anchor": request_text,
            "generator_signal": "C_APRIL_IMAGES_GENERATOR",
            "flow_id": identity["flow_id"],
            "turn_id": identity["message_id"],
            "user_id": identity["user_id"],
            "conversation_id": identity["conversation_id"],
            "dialogue_sequence_id": identity["dialog_id"],
            "dialogue_development": interpretation.get("dialogue") or {},
        }

    return None


async def _generate_image_artifact(
    interpretation: dict[str, Any],
    raw: dict[str, Any],
    identity: dict[str, str],
) -> dict[str, Any] | None:
    spec = _build_image_spec(raw, interpretation, identity)
    if spec is None:
        return None

    from blocks.C_APRIL_IMAGES_GENERATOR import generate_from_spec

    return await generate_from_spec(spec, variant="processor_route")


def _build_scene(
    response: MachineResponse,
    identity: dict[str, str],
    interpretation: dict[str, Any],
    turn_index: int,
    route_meta: dict[str, Any],
) -> dict[str, Any]:
    scene = MachineScene(
        scene_id=str(uuid.uuid4()),
        turn_id=identity["message_id"],
        flow_id=identity["flow_id"],
        topic_group=_text(
            (interpretation.get("dialogue") or {}).get("continuation_context", {}).get("active_topic")
        ),
        continuation=(
            _text((interpretation.get("dialogue") or {}).get("relation")).upper()
            == "CONTINUE"
        ),
        user_id=identity["user_id"],
        conversation_id=identity["conversation_id"],
        dialogue_sequence_id=identity["dialog_id"],
        sequence_turn_index=turn_index,
        active_task=dict((interpretation.get("intent") or {})),
        dialogue_state=dict((interpretation.get("dialogue") or {})),
        dialogue_development={
            "interpretation_id": identity["interpretation_id"],
            "memory_search_engine": "state_manager_dialogue_search_v4_asset_recall",
        },
        result_event={
            "status": "complete",
            "provider_calls": 1,
            "canonical_route": CANONICAL_ROUTE,
        },
        blocks=list(response.render_blocks or []),
        metadata={
            **dict(response.metadata or {}),
            "identity": identity,
            "canonical_route": CANONICAL_ROUTE,
            "route": route_meta,
        },
    )
    contract = build_scene_contract(scene)
    contract.authenticated_scope = {
        "user_id": identity["user_id"],
        "conversation_id": identity["conversation_id"],
        "dialogue_sequence_id": identity["dialog_id"],
    }
    return {
        "answer": response.answer,
        "content": response.content or response.answer,
        "summary": response.summary,
        "render_blocks": contract.render_blocks,
        "scene_contract": contract.__dict__,
        "artifacts": list(response.artifacts or []),
    }


def _mime_data_uri(raw: bytes, mime_type: str) -> str:
    import base64
    return f"data:{mime_type or 'application/octet-stream'};base64," + base64.b64encode(raw).decode("ascii")


def _decode_saved_text(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _restore_selected_assets(
    uid: str,
    identity: dict[str, str],
    dialogue_context: dict[str, Any],
    visual_context: list[dict[str, Any]],
    attachments: list[dict[str, Any]],
    file_inputs: list[dict[str, Any]],
    file_contents: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Rehydrate bytes only for a selected CONTINUE anchor in this exact dialog."""
    if visual_context or file_inputs or file_contents:
        return visual_context, attachments, file_inputs, file_contents, []
    if _text(dialogue_context.get("relation")).upper() != "CONTINUE":
        return visual_context, attachments, file_inputs, file_contents, []

    selected = dialogue_context.get("selected_pairs") or []
    anchor = dialogue_context.get("anchor") or {}
    message_ids: list[str] = []
    if isinstance(anchor, dict) and _text(anchor.get("message_id")):
        message_ids.append(_text(anchor.get("message_id")))
    for item in selected:
        if isinstance(item, dict) and _text(item.get("message_id")):
            message_ids.append(_text(item.get("message_id")))
    # Restore the selected semantic anchor first and alone.  Only if that turn
    # had no saved asset, fall back through ranked dialogue pairs one at a time.
    # This prevents a later unrelated file from being sent alongside a cat photo.
    message_ids = list(dict.fromkeys(message_ids))[:8]
    rows = []
    for selected_message_id in message_ids:
        rows = load_dialogue_assets(
            uid,
            dialog_id=identity["dialog_id"],
            conversation_id=identity["conversation_id"],
            message_ids=[selected_message_id],
            limit=1,
        )
        if rows:
            break
    restored_meta: list[dict[str, Any]] = []
    import base64
    for asset in rows:
        raw = bytes(asset.get("content") or b"")
        if not raw:
            continue
        kind = _text(asset.get("kind")).lower()
        filename = _text(asset.get("filename") or "attachment")
        mime_type = _text(asset.get("mime_type") or "application/octet-stream")
        common = {
            "filename": filename,
            "content_type": mime_type,
            "mime_type": mime_type,
            "kind": kind,
            "size_bytes": int(asset.get("size_bytes") or len(raw)),
            "source_type": (asset.get("metadata") or {}).get("source_type") or kind,
            "provider_readable": True,
            "recalled_from_memory": True,
            "asset_message_id": _text(asset.get("message_id")),
        }
        attachments.append(common)
        restored_meta.append({k: common[k] for k in ("filename", "mime_type", "kind", "asset_message_id")})
        if kind == "image" or mime_type.startswith("image/"):
            data_uri = _mime_data_uri(raw, mime_type if mime_type.startswith("image/") else "image/png")
            visual_context.append({
                "type": "input_image",
                "image_url": data_uri,
                "filename": filename,
                "source_type": common["source_type"],
                "mime_type": mime_type,
                "recalled_from_memory": True,
                "asset_message_id": common["asset_message_id"],
            })
        elif kind == "text_file":
            text_value = _text(asset.get("text_content")) or _decode_saved_text(raw)
            file_contents.append({
                "filename": filename,
                "mime_type": mime_type or "text/plain",
                "content": text_value[:18000],
                "size_bytes": len(raw),
                "recalled_from_memory": True,
                "asset_message_id": common["asset_message_id"],
            })
        else:
            file_inputs.append({
                "type": "input_file",
                "filename": filename,
                "file_data": _mime_data_uri(raw, mime_type),
                "mime_type": mime_type,
                "size_bytes": len(raw),
                "recalled_from_memory": True,
                "asset_message_id": common["asset_message_id"],
            })
    if restored_meta:
        print(
            "STATE: DIALOGUE ASSETS RESTORED "
            + json.dumps({"count": len(restored_meta), "assets": restored_meta}, ensure_ascii=False),
            flush=True,
        )
    return visual_context, attachments, file_inputs, file_contents, restored_meta


def _image_payload_bytes(value: Any) -> tuple[bytes, str] | None:
    """Extract generated image bytes for binary asset persistence, if present."""
    import base64
    visited = 0
    stack = [value]
    while stack and visited < 500:
        visited += 1
        item = stack.pop()
        if isinstance(item, dict):
            for key in ("image_data_uri", "data_uri", "src", "url", "image"):
                candidate = item.get(key)
                if isinstance(candidate, str) and candidate.startswith("data:image/") and ";base64," in candidate:
                    header, encoded = candidate.split(",", 1)
                    mime = header[5:].split(";", 1)[0] or "image/png"
                    try:
                        raw = base64.b64decode(encoded, validate=True)
                        if raw:
                            return raw, mime
                    except Exception:
                        pass
            for key in ("image_base64", "base64", "b64_json"):
                candidate = item.get(key)
                if isinstance(candidate, str) and candidate:
                    try:
                        raw = base64.b64decode(candidate, validate=True)
                        if raw and raw.startswith(b"\x89PNG\r\n\x1a\n"):
                            return raw, "image/png"
                    except Exception:
                        pass
            stack.extend(v for v in item.values() if isinstance(v, (dict, list)))
        elif isinstance(item, list):
            stack.extend(v for v in item if isinstance(v, (dict, list)))
    return None


def _strip_inline_binary(value: Any) -> Any:
    """Keep JSONB memory compact; raw bytes live in dialogue_assets."""
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            low = str(key).lower()
            if low in {"image_base64", "image_data_uri", "data_uri", "file_data", "b64_json"}:
                continue
            if (
                low in {"image_url", "src", "url", "image"}
                and isinstance(item, str)
                and item.startswith("data:")
                and ";base64," in item
            ):
                continue
            cleaned[key] = _strip_inline_binary(item)
        return cleaned
    if isinstance(value, list):
        return [_strip_inline_binary(item) for item in value]
    if isinstance(value, str):
        # Also catch a data URI embedded in a larger JSON/text field, not only
        # values that consist solely of the URI.
        if value.startswith("data:") and ";base64," in value:
            return "[stored as dialogue asset]"
        return re.sub(
            r"data:[^,\s;]+(?:;[^,\s;]+)*;base64,[A-Za-z0-9+/=_-]+",
            "[stored as dialogue asset]",
            value,
        )
    return value


async def execute(
    user_id: str,
    chat_id: Any = None,
    text: str = "",
    *,
    internal_text: str = "",
    display_language: str = "auto",
    flow_id: str = "",
    conversation_id: str = "",
    dialog_id: str = "",
    message_id: str = "",
    interpretation_id: str = "",
    visual_context: list[dict[str, Any]] | None = None,
    attachments: list[dict[str, Any]] | None = None,
    file_inputs: list[dict[str, Any]] | None = None,
    file_contents: list[dict[str, Any]] | None = None,
    translation: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    uid = _text(user_id)
    original = _text(text)
    current_text = _text(internal_text or original)
    if not uid:
        raise ValueError("USER_ID_REQUIRED")
    file_inputs = [
        dict(item)
        for item in (file_inputs or [])
        if isinstance(item, dict)
        and _text(item.get("file_data"))
    ]
    file_contents = [
        dict(item)
        for item in (file_contents or [])
        if isinstance(item, dict) and _text(item.get("content"))
    ]
    visual_context = [dict(item) for item in (visual_context or []) if isinstance(item, dict)]
    attachments = [dict(item) for item in (attachments or []) if isinstance(item, dict)]
    if not current_text and not visual_context and not file_inputs and not file_contents:
        raise ValueError("EMPTY_REQUEST")

    # Processor owns DB bootstrap; harmless and idempotent after the first call.
    init_db()

    require_auth = str(os.getenv("APRIL_REQUIRE_AUTH", "1")).lower() not in {"0", "false", "no"}
    if require_auth and not is_authenticated_user(uid):
        raise ValueError("AUTHENTICATED_USER_REQUIRED")

    payload_identity = {
        "dialog_id": dialog_id or conversation_id,
        "conversation_id": conversation_id or dialog_id,
        "message_id": message_id,
        "flow_id": flow_id,
        "interpretation_id": interpretation_id,
    }
    identity = resolve_dialog_identity(
        payload_identity,
        user_id=uid,
        flow_id=flow_id,
    )
    identity["interpretation_id"] = (
        _text(interpretation_id)
        or build_interpretation_identity(
            april_id=identity["user_id"],
            conversation_id=identity["conversation_id"],
            dialog_id=identity["dialog_id"],
            message_id=identity["message_id"],
            flow_id=identity["flow_id"],
        )["interpretation_id"]
    )

    # 12h memory search is owned by state_manager; PostgreSQL is only storage.
    dialogue_context = prepare_dialogue_context(
        uid,
        current_text,
        dialog_id=identity["dialog_id"],
        conversation_id=identity["conversation_id"],
        limit=12,
        has_image=bool(visual_context),
        has_file=bool(file_inputs or file_contents),
        has_voice=any(
            _text(item.get("kind")).lower() == "voice"
            for item in attachments
        ),
    )

    # A follow-up may refer to an image/file from earlier in this conversation.
    # Rehydrate only the assets attached to State Manager's selected anchor/pairs;
    # do not mix older files into NEW requests or when a fresh attachment exists.
    visual_context, attachments, file_inputs, file_contents, restored_assets = _restore_selected_assets(
        uid, identity, dialogue_context, visual_context, attachments, file_inputs, file_contents
    )

    interpretation = build_interpretation(
        current_request=current_text,
        original_request=original,
        display_language=display_language,
        memory=dialogue_context,
        attachments=attachments or [],
        visual_context=visual_context or [],
        identity=identity,
    )

    selected_rooms = _select_rooms(interpretation)
    render_plan = _renderer_plan(interpretation, selected_rooms)

    identity["flow_id"] = _text(identity["flow_id"])
    request = MachineRequest(
        request_id=identity["flow_id"] or str(uuid.uuid4()),
        goal="answer_user_request",
        intent={
            **interpretation,
            "interpretation_id": identity["interpretation_id"],
        },
        conversation={
            "conversation_id": identity["conversation_id"],
            "dialog_id": identity["dialog_id"],
            "message_id": identity["message_id"],
            "current_request": original,
            "resolved_request": current_text,
            "display_language": display_language,
        },
        memory={
            "window_hours": 12,
            "relation": dialogue_context["relation"],
            "relation_confidence": dialogue_context["relation_confidence"],
            "selected_pairs": dialogue_context["selected_pairs"],
            "candidates": dialogue_context["candidates"],
            "history_topics": dialogue_context.get("history_topics") or [],
            "topic_index": dialogue_context.get("topic_index") or [],
            "known_topic_count": int(dialogue_context.get("known_topic_count") or 0),
            "history_request": bool(dialogue_context.get("history_request")),
            "requested_topic_count": int(dialogue_context.get("requested_topic_count") or 7),
            "topic_table_markdown": dialogue_context.get("topic_table_markdown") or "",
            "anchor": dialogue_context.get("anchor") or {},
            "restored_assets": restored_assets,
            "search": dialogue_context["search"],
        },
        visual_context={
            "items": visual_context or [],
            "has_input_images": bool(visual_context),
        },
        available_tools=[r.room_id for r in list_registered_rooms()],
        requested_outputs=list(
            (interpretation.get("intent") or {}).get("requested_outputs") or ["text"]
        ),
        required_competencies=[
            cap
            for room in selected_rooms
            for cap in room.get("capabilities", [])
        ],
        required_artifacts=list(
            (interpretation.get("intent") or {}).get("requested_outputs") or ["text"]
        ),
        routing={
            "single_route": True,
            "canonical_route": CANONICAL_ROUTE,
            "processor_version": PROCESSOR_VERSION,
            "flow_id": identity["flow_id"],
            "dialog_id": identity["dialog_id"],
            "conversation_id": identity["conversation_id"],
            "message_id": identity["message_id"],
            "interpretation_id": identity["interpretation_id"],
            "selected_rooms": selected_rooms,
            "render_plan": render_plan,
            "provider_context_plan": {
                "relation": dialogue_context["relation"],
                "current_request": current_text,
                "selected_dialogue_chain": dialogue_context["selected_pairs"],
                "history_topics": dialogue_context.get("history_topics") or [],
                "topic_index": dialogue_context.get("topic_index") or [],
                "known_topic_count": int(dialogue_context.get("known_topic_count") or 0),
                "history_request": bool(dialogue_context.get("history_request")),
                "requested_topic_count": int(dialogue_context.get("requested_topic_count") or 7),
                "topic_table_markdown": dialogue_context.get("topic_table_markdown") or "",
                "anchor": dialogue_context.get("anchor") or {},
                "restored_assets": restored_assets,
                "new_dialogue_request": (
                    current_text
                    if dialogue_context["relation"] == "NEW" and not dialogue_context.get("history_request")
                    else ""
                ),
                "context": {
                    "active_topic": dialogue_context["active_topic"],
                    "reason": dialogue_context["reason"],
                    "confidence": dialogue_context["relation_confidence"],
                    "anchor_topic": (dialogue_context.get("anchor") or {}).get("topic", ""),
                },
                "mcdowell": {
                    "always": True,
                    "role": "presentation_and_render_layout",
                },
            },
        },
        constraints={
            "display_language": display_language,
            "provider_output_language": display_language,
            "internal_language": "en",
            "single_route": True,
            "no_legacy_route": True,
            "structured_response": True,
            "context_always_present": True,
            "mcdowell_always_present": True,
            "input_modalities": (interpretation.get("input") or {}).get("modalities", []),
        },
    )
    request.fiber.identity.user_id = uid
    request.metadata = {
        "identity": identity,
        "interpretation": interpretation,
        "attachments": attachments or [],
        # Raw file_data is request-scoped only. It is consumed by Provider and
        # is deliberately excluded from structured_request/DB persistence below.
        "file_inputs": [
            {
                "filename": _text(item.get("filename") or "file"),
                "mime_type": _text(item.get("mime_type") or "application/octet-stream"),
                "size_bytes": int(item.get("size_bytes") or 0),
                "file_data": _text(item.get("file_data")),
            }
            for item in file_inputs
        ],
        "file_contents": [
            {
                "filename": _text(item.get("filename") or "file"),
                "mime_type": _text(item.get("mime_type") or "text/plain"),
                "size_bytes": int(item.get("size_bytes") or 0),
                "content": _text(item.get("content")),
            }
            for item in file_contents
        ],
        "translation": translation or {},
    }

    started = time.perf_counter()
    provider_packet = await generate_text(request)
    provider_ms = round((time.perf_counter() - started) * 1000, 1)

    raw = provider_packet.get("machine_response") if isinstance(provider_packet, dict) else None
    if not isinstance(raw, dict):
        raise RuntimeError("PROVIDER_CONTRACT_MISSING")

    answer = _text(raw.get("answer") or raw.get("content"))
    if not answer:
        raise RuntimeError("CANONICAL_ANSWER_MISSING")

    # The existing TextModule participates only as the canonical response
    # packaging/sanitization layer; it never creates a second Provider call.
    raw_blocks = [dict(x) for x in (raw.get("render_blocks") or []) if isinstance(x, dict)]
    raw_artifacts = [dict(x) for x in (raw.get("artifacts") or []) if isinstance(x, dict)]
    wants_image = bool((interpretation.get("intent") or {}).get("wants_image"))
    if not wants_image:
        raw_blocks = [
            block for block in raw_blocks
            if str(block.get("type") or "").lower() not in {"image", "gallery"}
        ]
        raw_artifacts = [
            artifact for artifact in raw_artifacts
            if str(artifact.get("type") or artifact.get("artifact_type") or "").lower() not in {"image", "generated_image"}
        ]

    packaged = package_provider_response(
        answer=answer,
        content=_text(raw.get("content") or answer),
        summary=_text(raw.get("summary") or answer[:180]),
        render_blocks=raw_blocks,
        artifacts=raw_artifacts,
    )

    image_result = None
    if (interpretation.get("intent") or {}).get("wants_image"):
        image_result = await _generate_image_artifact(
            interpretation,
            raw,
            identity,
        )
        if image_result:
            packaged["artifacts"].append(image_result.get("artifact") or image_result)
            image_block = {
                "type": "image",
                "renderer": get_web_renderer_registration("image").get("renderer", "GalleryBlock"),
                "viewer": get_web_renderer_registration("image").get("viewer", "GalleryBlock"),
                "content": "",
                "artifact": image_result.get("artifact") or {},
                "images": (image_result.get("artifact") or {}).get("images", []),
            }
            packaged["render_blocks"].append(image_block)

    normalized_blocks = list(packaged["render_blocks"] or [])
    if not normalized_blocks:
        normalized_blocks = [
            {
                "type": "text",
                "renderer": get_web_renderer_registration("text").get("renderer", "MessageTextBlock"),
                "viewer": get_web_renderer_registration("text").get("viewer", "MessageTextBlock"),
                "content": packaged["answer"],
            }
        ]

    response = MachineResponse(
        answer=packaged["answer"],
        content=packaged["content"],
        summary=packaged["summary"],
        render_blocks=normalized_blocks,
        artifacts=list(packaged["artifacts"]),
        metadata={
            "provider_ms": provider_ms,
            "identity": identity,
            "interpretation": interpretation,
            "selected_rooms": selected_rooms,
            "render_plan": render_plan,
            "image_generated": bool(image_result),
        },
    )

    # Provider responses do not get to change the authenticated identity.
    response_identity = {
        **identity,
        **dict(response.metadata.get("identity") or {}),
    }
    assert_identity_match(identity, response_identity)

    rows_for_turn = dialogue_context.get("candidates") or []
    turn_index = (
        max(
            [int(item.get("turn_index") or 0) for item in rows_for_turn],
            default=-1,
        )
        + 1
    )
    if _text(dialogue_context.get("relation")).upper() == "NEW":
        turn_index = 0

    result = _build_scene(
        response,
        identity,
        interpretation,
        turn_index,
        {
            "canonical_route": CANONICAL_ROUTE,
            "processor_version": PROCESSOR_VERSION,
            "stages": [
                "bot.ru",
                "input_reader",
                "state_manager_search",
                "interpretation_identity",
                "C_ARTIFACT_CONTRACT",
                "provider_luna",
                "C_APRIL_IMAGES_GENERATOR" if image_result else "",
                "SceneContract",
                "RenderMessage",
                "bot.ru",
                "Web",
            ],
        },
    )

    # Persist the complete structured turn after Provider/SceneContract.
    # PostgreSQL remains storage only; State Manager will search these fields
    # on the next request.
    safe_visual_context = dict(request.visual_context)
    safe_visual_items: list[dict[str, Any]] = []
    for item in (request.visual_context.get("items") or []) if isinstance(request.visual_context, dict) else []:
        if not isinstance(item, dict):
            continue
        safe_visual_items.append({
            "type": _text(item.get("type") or "input_image"),
            "filename": _text(item.get("filename") or "image"),
            "source_type": _text(item.get("source_type") or "image"),
            "mime_type": _text(item.get("mime_type") or "image/*"),
        })
    safe_visual_context["items"] = safe_visual_items
    safe_visual_context["has_input_images"] = bool(safe_visual_items)

    generated_asset_saved = False
    if image_result:
        # The generator returns validated raw bytes as well as a scene artifact.
        # Persist raw bytes first; artifact fields are the compatibility fallback.
        direct_image_bytes = image_result.get("image_bytes")
        direct_mime = _text(image_result.get("mime_type") or "image/png")
        if isinstance(direct_image_bytes, (bytes, bytearray)) and direct_image_bytes:
            generated_image = (bytes(direct_image_bytes), direct_mime)
        else:
            generated_image = _image_payload_bytes(image_result.get("artifact") or image_result)
        if generated_image:
            generated_bytes, generated_mime = generated_image
            generated_asset_saved = save_dialogue_asset(
                uid,
                dialog_id=identity["dialog_id"],
                conversation_id=identity["conversation_id"],
                message_id=identity["message_id"],
                filename=f"april-generated-{identity['message_id']}.png",
                mime_type=generated_mime,
                kind="image",
                content=generated_bytes,
                turn_index=turn_index,
                metadata={"source_type": "generated_image", "generator": "C_APRIL_IMAGES_GENERATOR"},
            )

    structured_request = _strip_inline_binary({
        "request_id": request.request_id,
        "goal": request.goal,
        "intent": dict(request.intent),
        "conversation": dict(request.conversation),
        "memory": dict(request.memory),
        "visual_context": safe_visual_context,
        "attachments": list(attachments or []),
        "available_tools": list(request.available_tools),
        "requested_outputs": list(request.requested_outputs),
        "required_competencies": list(request.required_competencies),
        "required_artifacts": list(request.required_artifacts),
        "routing": dict(request.routing),
        "constraints": dict(request.constraints),
    })
    structured_response = _strip_inline_binary({
        "answer": response.answer,
        "content": response.content,
        "summary": response.summary,
        "render_blocks": list(response.render_blocks or []),
        "artifacts": list(response.artifacts or []),
        "metadata": dict(response.metadata or {}),
        "scene_contract": result.get("scene_contract") or {},
        "generated_asset_saved": generated_asset_saved,
    })

    saved = save_dialogue_pair(
        uid,
        original or current_text,
        answer,
        turn_index=turn_index,
        user_en=current_text,
        april_en=_text(raw.get("internal_answer_en")) or answer,
        language=display_language,
        relation=_text(dialogue_context.get("relation") or "NEW"),
        dialog_id=identity["dialog_id"],
        conversation_id=identity["conversation_id"],
        message_id=identity["message_id"],
        interpretation_id=identity["interpretation_id"],
        structured_request=structured_request,
        structured_response=structured_response,
    )

    result.update(
        {
            "april_id": uid,
            "conversation_id": identity["conversation_id"],
            "dialog_id": identity["dialog_id"],
            "message_id": identity["message_id"],
            "interpretation_id": identity["interpretation_id"],
            "flow_id": identity["flow_id"],
            "processor_version": PROCESSOR_VERSION,
            "display_language": display_language,
            "internal_language": "en",
            "translation": translation or {},
            "memory_window_hours": 12,
            "memory_relation": dialogue_context.get("relation"),
            "memory_pair_count": int(dialogue_context.get("search", {}).get("total_pairs") or 0),
            "memory_selected_count": len(dialogue_context.get("selected_pairs") or []),
            "memory_saved": saved,
            "dialogue_assets_restored": restored_assets,
            "generated_asset_saved": generated_asset_saved,
            "interpretation": interpretation,
            "route": result.get("scene_contract", {}).get("metadata", {}).get("route", {}),
        }
    )
    return result


__all__ = ["execute", "PROCESSOR_VERSION", "CANONICAL_ROUTE"]
