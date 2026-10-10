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
import base64
import hashlib
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
    build_question_sequence,
    interpret_request_semantics,
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
    update_dialogue_asset_analysis,
)


PROCESSOR_VERSION = "april_exkrutor_single_route_v9_per_question_search"
CANONICAL_ROUTE = "/api/v1/chat"


def _apr_timing_log(stage: str, started: float | None = None, **fields: Any) -> None:
    """Low-overhead diagnostic timing; logging must never affect the request path."""
    try:
        payload = {"component": "executor", "stage": stage}
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


def _text(value: Any) -> str:
    return str(value or "").strip()


def _compact_question_search(
    context: dict[str, Any],
    query: str = "",
    semantics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bounded per-question retrieval context for the existing Provider sequence."""
    if not isinstance(context, dict):
        return {"status": "unavailable", "relation": "NEW", "context": []}

    def compact_pair(item: Any) -> dict[str, Any]:
        if not isinstance(item, dict):
            return {}
        sections = []
        for section in (item.get("sections") or [])[:4]:
            if not isinstance(section, dict):
                continue
            sections.append({
                "heading": _text(section.get("heading"))[:80],
                "summary": _text(section.get("summary"))[:150],
                "order": section.get("order"),
                "message_id": _text(section.get("message_id"))[:120],
            })
        return {
            "topic": _text(item.get("topic"))[:100],
            "user": _text(item.get("user"))[:180],
            "april": _text(item.get("april"))[:240],
            "sections": sections,
            "message_id": _text(item.get("message_id"))[:120],
            "same_dialog": bool(item.get("same_dialog")),
        }

    anchor = context.get("anchor") if isinstance(context.get("anchor"), dict) else {}
    section = context.get("selected_section") if isinstance(context.get("selected_section"), dict) else {}
    pairs = [compact_pair(item) for item in (context.get("selected_pairs") or [])[:2]]
    pairs = [item for item in pairs if item]
    pending = context.get("pending_clarification") if isinstance(context.get("pending_clarification"), dict) else {}
    options = []
    for item in (pending.get("options") or [])[:3]:
        if not isinstance(item, dict):
            continue
        options.append({
            "topic": _text(item.get("topic"))[:90],
            "heading": _text(item.get("heading"))[:90],
            "summary": _text(item.get("summary"))[:140],
            "message_id": _text(item.get("message_id"))[:120],
        })
    semantics = dict(semantics or {})
    history_request = bool(context.get("history_request") or semantics.get("history_request"))
    topic_index = []
    if history_request:
        topic_index = [
            {
                "number": item.get("number"),
                "topic": _text(item.get("topic"))[:100],
                "summary": _text(item.get("summary"))[:160],
                "last_question": _text(item.get("last_question"))[:100],
                "message_id": _text(item.get("message_id"))[:120],
            }
            for item in (context.get("topic_index") or [])[:4] if isinstance(item, dict)
        ]
    history_topics = [
        {
            "number": item.get("number"),
            "topic": _text(item.get("topic"))[:100],
            "summary": _text(item.get("summary"))[:160],
            "last_question": _text(item.get("last_question"))[:100],
            "message_id": _text(item.get("message_id"))[:120],
        }
        for item in (context.get("history_topics") or [])[:4] if isinstance(item, dict)
    ] if history_request else []
    return {
        "status": "ready",
        "relation": _text(context.get("relation") or "NEW").upper(),
        "history_request": history_request,
        "semantic_intent": _text(semantics.get("primary_intent") or ("HISTORY_RECALL" if history_request else "NEW_INFORMATION")),
        "search_direction": _text(semantics.get("direction") or ("SEARCH_DIALOGUE_HISTORY" if history_request else "ANSWER_NEW_REQUEST")),
        "time_scope": _text(semantics.get("time_scope") or "UNSPECIFIED"),
        "history_topics": history_topics,
        "topic_index": topic_index,
        "confidence": round(float(context.get("relation_confidence") or 0.0), 4),
        "reason": _text(context.get("reason"))[:80],
        "topic": (_text(context.get("active_topic")) or _text(query))[:120],
        "anchor": {
            "topic": _text(anchor.get("topic"))[:100],
            "user": _text(anchor.get("user"))[:180],
            "april": _text(anchor.get("april"))[:240],
            "message_id": _text(anchor.get("message_id"))[:120],
        } if anchor else {},
        "selected_section": {
            "topic": _text(section.get("topic"))[:100],
            "heading": _text(section.get("heading"))[:90],
            "summary": _text(section.get("summary"))[:180],
            "order": section.get("order"),
            "message_id": _text(section.get("message_id"))[:120],
        } if section else {},
        "selected_pairs": pairs,
        "clarification_needed": bool(context.get("clarification_needed")),
        "clarification_prompt": _text(context.get("clarification_prompt"))[:280],
        "clarification_options": options,
    }


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
    if intent.get("wants_graph"):
        required_capabilities.extend(["graph", "series", "data_visualization"])

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
            "memory_search_engine": "state_manager_topic_section_search_v5_clarification",
        },
        result_event={
            "status": "complete",
            "provider_calls": 0 if bool((response.metadata or {}).get("local_clarification")) else 1,
            "provider_retries": 0,
            "provider_output_limit": "model_native_no_application_cap",
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


def _explicit_prior_asset_reference(value: Any) -> bool:
    low = _text(value).lower().replace("ё", "е")
    markers = (
        "предыдущее фото", "предыдущую картинку", "предыдущем фото", "прошлое фото",
        "раньше присылал", "которое я присылал", "который я присылал", "которую я присылал",
        "то фото", "та картинка", "тот файл", "предыдущий файл", "предыдущий код",
        "сравни с", "сравни это", "сравни с предыдущ", "вернись к фото", "вернись к файлу",
        "на той картинке", "на предыдущей картинке", "на старой картинке",
        "that image", "previous image", "previous photo", "the earlier file",
        "the file i sent", "the image i sent", "compare with", "compare to previous",
    )
    return any(marker.replace("ё", "е") in low for marker in markers)


def _requires_original_asset(value: Any, kind: str, cached_summary: str) -> bool:
    """Decide whether a follow-up needs original bytes rather than its sidecar.

    A cached summary is the default continuity representation. Original bytes are
    reattached only when the user explicitly references an earlier asset or asks
    for exact extraction/verification/editing that a summary cannot safely supply.
    This gate does not decide whether to generate an image; Interpretation owns
    that decision independently.
    """
    text = _text(value).lower().replace("ё", "е")
    if not cached_summary or _explicit_prior_asset_reference(text):
        return True

    exact_read_markers = (
        "что написано", "что там написано", "прочитай текст", "прочти текст",
        "прочитай номер", "какой номер", "номер документа", "текст на фото",
        "текст на изображении", "перепиши текст", "проверь данные на",
        "приблизь", "увеличь фрагмент", "разбери мелкий текст",
        "read the text", "what does it say", "extract the text", "read the number",
        "zoom in", "verify the details", "transcribe the image", "ocr this",
        "по этому фото", "по этой фотографии", "по этой картинке", "на основе фото",
        "на основе этой картинки", "используй фото как референс", "используй картинку как референс",
        "сделай вариант по фото", "как на этой фотографии", "отредактируй изображение",
    )
    if any(marker in text for marker in exact_read_markers):
        return True

    if str(kind or "").lower() in {"file", "text_file"}:
        source_edit_markers = (
            "исправь код", "исправь файл", "измени файл", "обнови код",
            "улучши код", "оптимизируй код", "перепиши код", "улучши файл",
            "найди ошибку в", "покажи полный код", "разбери строку",
            "исправь этот скрипт", "refactor the code", "fix the code",
            "improve the code", "optimize the code", "rewrite the code",
            "edit the file", "patch the source", "show the full source",
            "trace the bug in",
        )
        if any(marker in text for marker in source_edit_markers):
            return True

    return False


def _source_code_from_block(block: dict[str, Any]) -> tuple[str, str, str] | None:
    language = _text(block.get("language") or block.get("lang") or "text").lower()
    filename = _text(block.get("filename") or "")
    code = _text(block.get("code") or block.get("content") or block.get("text"))
    if not code:
        return None
    # Accept a single fenced block while preserving internal source lines.
    match = re.fullmatch(r"```[\w.+-]*\s*\n(.*?)\n```", code, flags=re.S)
    if match:
        code = match.group(1)
    extensions = {
        "python": "py", "py": "py", "javascript": "js", "js": "js",
        "typescript": "ts", "ts": "ts", "tsx": "tsx", "jsx": "jsx",
        "json": "json", "sql": "sql", "bash": "sh", "shell": "sh",
        "html": "html", "css": "css", "yaml": "yml", "toml": "toml",
        "markdown": "md", "md": "md", "text": "txt",
    }
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else extensions.get(language, "txt")
    allowed_exts = {"py", "js", "ts", "tsx", "jsx", "json", "sql", "sh", "html", "css", "yml", "toml", "md", "txt"}
    if ext not in allowed_exts:
        ext = extensions.get(language, "txt")
    return code, language, ext


def _persist_asset_analysis_summaries(
    uid: str,
    identity: dict[str, str],
    attachment_index: list[dict[str, Any]],
    memory_record: Any,
) -> int:
    """Persist provider-grounded attachment summaries beside exact source bytes."""
    if not isinstance(memory_record, dict):
        return 0

    allowed: list[dict[str, str]] = []
    for item in attachment_index:
        if not isinstance(item, dict):
            continue
        role = _text(item.get("asset_role") or "user_input")
        kind = _text(item.get("kind")).lower()
        if role != "user_input" or kind not in {"image", "text_file", "file"}:
            continue
        if not bool(item.get("source_bytes_attached", True)):
            continue
        filename = os.path.basename(_text(item.get("filename")))[:240]
        message_id = _text(item.get("asset_message_id") or identity.get("message_id"))
        if filename and message_id:
            allowed.append({"filename": filename, "kind": kind, "message_id": message_id, "role": role})

    # De-duplicate index entries contributed by both metadata and content readers.
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in allowed:
        key = (item["message_id"], item["filename"], item["kind"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    allowed = deduped
    if not allowed:
        return 0

    raw_summaries = memory_record.get("attachment_summaries")
    summaries = [dict(item) for item in raw_summaries if isinstance(item, dict)] if isinstance(raw_summaries, list) else []

    # Compatibility with providers that return the established memory fields but
    # omit per-asset records: only use a fallback when one-to-one attribution is
    # unambiguous. Never copy a composite answer onto every attached file.
    if not summaries:
        images = [item for item in allowed if item["kind"] == "image"]
        files = [item for item in allowed if item["kind"] in {"file", "text_file"}]
        observations = memory_record.get("visual_observations")
        if len(images) == 1 and isinstance(observations, list) and observations:
            summaries.append({
                **images[0],
                "asset_message_id": images[0]["message_id"],
                "summary": "; ".join(_text(item) for item in observations if _text(item))[:1200],
            })
        file_purpose = _text(memory_record.get("file_purpose"))
        if len(files) == 1 and file_purpose:
            symbols = memory_record.get("code_symbols")
            symbol_text = ", ".join(_text(item) for item in symbols[:8] if _text(item)) if isinstance(symbols, list) else ""
            summaries.append({
                **files[0],
                "asset_message_id": files[0]["message_id"],
                "summary": (file_purpose + (f" Key elements: {symbol_text}" if symbol_text else ""))[:1200],
            })

    changed = 0
    for summary_item in summaries[:12]:
        filename = os.path.basename(_text(summary_item.get("filename")))[:240]
        kind = _text(summary_item.get("kind")).lower()
        summary_text = _text(summary_item.get("summary"))[:1200]
        details = summary_item.get("key_details")
        if not isinstance(details, list):
            details = []
        requested_message_id = _text(summary_item.get("asset_message_id") or summary_item.get("message_id"))
        if requested_message_id in {"current", "this_message"}:
            requested_message_id = _text(identity.get("message_id"))
        candidates = [
            item for item in allowed
            if item["filename"] == filename
            and (not kind or item["kind"] == kind)
            and (not requested_message_id or item["message_id"] == requested_message_id)
        ]
        if not candidates and not requested_message_id and filename:
            candidates = [item for item in allowed if item["filename"] == filename and (not kind or item["kind"] == kind)]
        if len(candidates) != 1:
            continue
        target = candidates[0]
        if target["role"] != "user_input" or not summary_text:
            continue
        if update_dialogue_asset_analysis(
            uid,
            dialog_id=identity["dialog_id"],
            conversation_id=identity["conversation_id"],
            message_id=target["message_id"],
            filename=target["filename"],
            kind=target["kind"],
            summary=summary_text,
            key_details=details,
        ):
            changed += 1

    if changed:
        print(
            "STATE: DIALOGUE ASSET ANALYSIS UPDATED "
            + json.dumps({"count": changed, "source": "provider_attachment_summaries"}, ensure_ascii=False),
            flush=True,
        )
    return changed


def _restore_selected_assets(
    uid: str,
    identity: dict[str, str],
    dialogue_context: dict[str, Any],
    visual_context: list[dict[str, Any]],
    attachments: list[dict[str, Any]],
    file_inputs: list[dict[str, Any]],
    file_contents: list[dict[str, Any]],
    current_request: str = "",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Restore sidecars for the selected authenticated turn and original bytes on demand.

    Current uploads take precedence. A known older asset is represented by its
    semantic sidecar for ordinary continuity; original bytes are reattached only
    when precise inspection, editing, comparison, or an uncached first analysis is
    required.
    """
    has_current_asset = bool(visual_context or file_inputs or file_contents)
    if has_current_asset and not _explicit_prior_asset_reference(current_request):
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
            limit=4,
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
        asset_metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
        source_type = _text(asset_metadata.get("source_type") or kind)
        asset_role = _text(asset_metadata.get("asset_role") or ("april_output" if source_type in {"generated_image", "april_output", "generated_file"} else "user_input"))
        analysis_summary = _text(asset_metadata.get("analysis_summary"))[:1200]
        analysis_key_details = asset_metadata.get("analysis_key_details")
        if not isinstance(analysis_key_details, list):
            analysis_key_details = []
        analysis_key_details = [_text(item)[:220] for item in analysis_key_details if _text(item)][:8]
        restore_original = _requires_original_asset(current_request, kind, analysis_summary)
        common = {
            "filename": filename,
            "content_type": mime_type,
            "mime_type": mime_type,
            "kind": kind,
            "size_bytes": int(asset.get("size_bytes") or len(raw)),
            "source_type": source_type,
            "asset_role": asset_role,
            "output_type": _text(asset_metadata.get("output_type")),
            "provider_readable": True,
            "recalled_from_memory": True,
            "asset_message_id": _text(asset.get("message_id")),
            "analysis_summary": analysis_summary,
            "analysis_key_details": analysis_key_details,
            "requires_original_analysis": restore_original,
        }
        attachments.append(common)
        restored_meta.append({k: common[k] for k in ("filename", "mime_type", "kind", "asset_role", "output_type", "asset_message_id", "analysis_summary", "analysis_key_details")})

        # Recalled assets with a valid sidecar normally enter the dialogue as
        # semantic context only. Reattach the original bytes for precise reads,
        # explicit references, modifications, or when no sidecar exists yet.
        if not restore_original:
            continue

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
                "asset_role": asset_role,
                "output_type": common["output_type"],
                "analysis_summary": analysis_summary,
                "analysis_key_details": analysis_key_details,
                "requires_original_analysis": True,
            })
        elif kind == "text_file":
            # Re-decode the preserved original bytes instead of trusting the
            # text_content sidecar: older versions stored only the first 18k
            # characters there, so preferring it would keep old assets clipped
            # even after the input-reader limit is raised.
            decoded_source = _decode_saved_text(raw)
            text_value = decoded_source or _text(asset.get("text_content"))
            source_chars = len(text_value)
            reader_truncated = source_chars > 48000
            file_contents.append({
                "filename": filename,
                "mime_type": mime_type or "text/plain",
                "content": text_value[:48000],
                "size_bytes": len(raw),
                "reader_truncated": reader_truncated,
                "source_chars": source_chars,
                "recalled_from_memory": True,
                "asset_message_id": common["asset_message_id"],
                "asset_role": asset_role,
                "output_type": common["output_type"],
                "analysis_summary": analysis_summary,
                "analysis_key_details": analysis_key_details,
                "requires_original_analysis": True,
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
                "asset_role": asset_role,
                "output_type": common["output_type"],
                "analysis_summary": analysis_summary,
                "analysis_key_details": analysis_key_details,
                "requires_original_analysis": True,
            })
    if restored_meta:
        # Do not place OCR or semantic details from documents into operational
        # logs. The returned metadata still carries the sidecar into Provider.
        log_assets = [
            {
                "filename": item.get("filename"),
                "kind": item.get("kind"),
                "asset_role": item.get("asset_role"),
                "asset_message_id": item.get("asset_message_id"),
                "analysis_cached": bool(item.get("analysis_summary")),
            }
            for item in restored_meta
        ]
        print(
            "STATE: DIALOGUE ASSETS RESTORED "
            + json.dumps({"count": len(restored_meta), "assets": log_assets}, ensure_ascii=False),
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
    pipeline_started = time.perf_counter()
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
    db_started = time.perf_counter()
    init_db()
    _apr_timing_log("db_bootstrap", db_started, user_key=_apr_diag_ref(uid))

    require_auth = str(os.getenv("APRIL_REQUIRE_AUTH", "1")).lower() not in {"0", "false", "no"}
    auth_started = time.perf_counter()
    if require_auth and not is_authenticated_user(uid):
        raise ValueError("AUTHENTICATED_USER_REQUIRED")
    _apr_timing_log("auth_check", auth_started, user_key=_apr_diag_ref(uid), required=require_auth)

    identity_started = time.perf_counter()
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
    _apr_timing_log(
        "identity_bind", identity_started, user_key=_apr_diag_ref(uid),
        dialog_key=_apr_diag_ref(identity.get("dialog_id")),
        message_key=_apr_diag_ref(identity.get("message_id")),
        flow_key=_apr_diag_ref(identity.get("flow_id")),
    )

    # First infer the overall semantic direction, intent, time scope and memory
    # need; only then split the request into ordered questions. The classifier is
    # local/deterministic and does not add an API call or replace the existing splitter.
    memory_started = time.perf_counter()
    semantic_started = time.perf_counter()
    semantic_interpretation = interpret_request_semantics(original or current_text)
    _apr_timing_log(
        "semantic_preinterpretation", semantic_started,
        user_key=_apr_diag_ref(uid),
        dialog_key=_apr_diag_ref(identity.get("dialog_id")),
        message_key=_apr_diag_ref(identity.get("message_id")),
        semantic_intent=semantic_interpretation.get("primary_intent"),
        search_direction=semantic_interpretation.get("direction"),
        time_scope=semantic_interpretation.get("time_scope"),
        topic_reference=semantic_interpretation.get("topic_reference"),
        requires_memory=bool(semantic_interpretation.get("requires_memory")),
        history_request=bool(semantic_interpretation.get("history_request")),
        intent_score=semantic_interpretation.get("intent_score"),
        intent_features=semantic_interpretation.get("features"),
        reason=semantic_interpretation.get("reason"),
    )
    question_sequence = build_question_sequence(
        original or current_text, parent_interpretation=semantic_interpretation
    )
    normalized_semantics = interpret_request_semantics(current_text)
    normalized_sequence = build_question_sequence(
        current_text, parent_interpretation=normalized_semantics
    )
    _apr_timing_log(
        "question_decomposition_result",
        user_key=_apr_diag_ref(uid),
        dialog_key=_apr_diag_ref(identity.get("dialog_id")),
        message_key=_apr_diag_ref(identity.get("message_id")),
        question_count=len(question_sequence),
        questions=[{
            "step_index": item.get("step_index"),
            "request_key": _apr_diag_ref(item.get("request")),
            "semantic_intent": item.get("semantic_intent"),
            "search_direction": item.get("search_direction"),
            "time_scope": item.get("time_scope"),
            "history_request": bool(item.get("history_request")),
            "reason": item.get("semantic_reason"),
        } for item in question_sequence],
    )
    has_voice_input = any(_text(item.get("kind")).lower() == "voice" for item in attachments)
    search_kwargs = {
        "dialog_id": identity["dialog_id"],
        "conversation_id": identity["conversation_id"],
        "limit": 12,
        "has_image": bool(visual_context),
        "has_file": bool(file_inputs or file_contents),
        "has_voice": has_voice_input,
    }
    question_contexts: list[dict[str, Any]] = []

    if len(question_sequence) <= 1:
        single_semantics = {
            "schema": "april_request_semantics_v1",
            "primary_intent": semantic_interpretation.get("primary_intent"),
            "direction": semantic_interpretation.get("direction"),
            "time_scope": semantic_interpretation.get("time_scope"),
            "topic_reference": semantic_interpretation.get("topic_reference"),
            "requires_memory": semantic_interpretation.get("requires_memory"),
            "history_request": semantic_interpretation.get("history_request"),
            "search_scope": semantic_interpretation.get("search_scope"),
            "relation_hint": semantic_interpretation.get("relation_hint"),
            "reason": semantic_interpretation.get("reason"),
            "features": semantic_interpretation.get("features", {}),
        }
        dialogue_context = prepare_dialogue_context(
            uid, current_text, query_interpretation=single_semantics, **search_kwargs
        )
        if question_sequence:
            question_sequence[0]["dialogue_search"] = _compact_question_search(
                dialogue_context, current_text, single_semantics
            )
        _apr_timing_log(
            "request_question_search", memory_started,
            user_key=_apr_diag_ref(uid),
            dialog_key=_apr_diag_ref(identity.get("dialog_id")),
            message_key=_apr_diag_ref(identity.get("message_id")),
            step_index=question_sequence[0].get("step_index") if question_sequence else 1,
            query_key=_apr_diag_ref(current_text),
            semantic_intent=single_semantics.get("primary_intent"),
            search_direction=single_semantics.get("direction"),
            history_request=bool(dialogue_context.get("history_request")),
            relation=dialogue_context.get("relation"),
            candidates=len(dialogue_context.get("candidates") or []),
            selected_pairs=len(dialogue_context.get("selected_pairs") or []),
            topic_index_count=len(dialogue_context.get("topic_index") or []),
            status="ok",
        )
    else:
        aligned_normalized = len(normalized_sequence) == len(question_sequence)
        for index, question_item in enumerate(question_sequence):
            search_query = (
                _text(normalized_sequence[index].get("request"))
                if aligned_normalized else _text(question_item.get("request"))
            )
            try:
                task_semantics = {
                    "schema": "april_request_semantics_v1",
                    "primary_intent": question_item.get("semantic_intent", "NEW_INFORMATION"),
                    "direction": question_item.get("search_direction", "ANSWER_NEW_REQUEST"),
                    "time_scope": question_item.get("time_scope", "UNSPECIFIED"),
                    "topic_reference": question_item.get("topic_reference", "UNSPECIFIED"),
                    "requires_memory": question_item.get("requires_memory", False),
                    "history_request": question_item.get("history_request", False),
                    "search_scope": "ALL_DIALOGUE_HISTORY" if question_item.get("history_request") else (
                        "TOPIC_OR_ACTIVE_CONTEXT" if question_item.get("requires_memory") else "CURRENT_DIALOGUE"
                    ),
                    "relation_hint": "HISTORY_LOOKUP" if question_item.get("history_request") else "CONTINUE" if question_item.get("requires_memory") else "NEW",
                    "reason": question_item.get("semantic_reason", ""),
                    "features": {},
                    "parent_context_dependency": bool(question_item.get("parent_context_dependency")),
                    "parent_intent": question_item.get("parent_intent", ""),
                }
                task_context = prepare_dialogue_context(
                    uid, search_query, query_interpretation=task_semantics, **search_kwargs
                )
                task_search = _compact_question_search(task_context, search_query, task_semantics)
            except Exception as exc:
                # A task-search failure must not discard the whole user request.
                # Keep order/identity and allow other tasks to proceed independently.
                task_context = {}
                task_search = {
                    "status": "search_error",
                    "relation": "NEW",
                    "confidence": 0.0,
                    "reason": type(exc).__name__,
                    "topic": "",
                    "anchor": {},
                    "selected_section": {},
                    "selected_pairs": [],
                    "clarification_needed": False,
                    "clarification_prompt": "",
                    "clarification_options": [],
                }
            question_item["dialogue_search"] = task_search
            question_item["search_query"] = search_query[:500]
            question_contexts.append(task_context)
            _apr_timing_log(
                "request_question_search", memory_started,
                user_key=_apr_diag_ref(uid),
                dialog_key=_apr_diag_ref(identity.get("dialog_id")),
                message_key=_apr_diag_ref(identity.get("message_id")),
                step_index=question_item.get("step_index"),
                query_key=_apr_diag_ref(search_query),
                relation=task_search.get("relation"),
                candidates=len(task_context.get("candidates") or []) if isinstance(task_context, dict) else 0,
                selected_pairs=len(task_context.get("selected_pairs") or []) if isinstance(task_context, dict) else 0,
                clarification_needed=bool(task_search.get("clarification_needed")),
                status=task_search.get("status"),
                semantic_intent=task_semantics.get("primary_intent"),
                search_direction=task_semantics.get("direction"),
                history_request=bool(task_context.get("history_request")) if isinstance(task_context, dict) else False,
                topic_index_count=len(task_context.get("topic_index") or []) if isinstance(task_context, dict) else 0,
            )

        # Preserve the established top-level route contract by using the first
        # ordered task as the legacy turn anchor. All other per-task relation and
        # history results travel in REQUEST_SEQUENCE; no second dialogue is made.
        dialogue_context = dict(question_contexts[0] if question_contexts else {})
        # Keep the legacy first-question anchor, but do not lose history topics when
        # a history-recall item appears later in a compound request.
        history_context = next((ctx for ctx in question_contexts if isinstance(ctx, dict) and ctx.get("history_request")), None)
        if history_context:
            dialogue_context["history_available_for_request"] = True
            dialogue_context["history_topics"] = list(history_context.get("history_topics") or [])
            dialogue_context["topic_index"] = list(history_context.get("topic_index") or dialogue_context.get("topic_index") or [])
            dialogue_context["known_topic_count"] = max(
                int(dialogue_context.get("known_topic_count") or 0),
                int(history_context.get("known_topic_count") or 0),
            )
            dialogue_context["requested_topic_count"] = int(history_context.get("requested_topic_count") or 7)
            dialogue_context["topic_table_markdown"] = _text(history_context.get("topic_table_markdown") or dialogue_context.get("topic_table_markdown"))
        if not dialogue_context:
            # Do not fall back to a whole-message retrieval if one per-question
            # search failed. That could accidentally replace the first task's
            # relation with a mixed CONTINUE/NEW decision. Keep the canonical
            # request alive with an empty, correctly-shaped memory context.
            dialogue_context = {
                "window_hours": 12,
                "relation": "NEW",
                "relation_confidence": 0.0,
                "reason": "per_question_search_unavailable",
                "active_topic": _text(question_sequence[0].get("request")) if question_sequence else current_text,
                "selected_pairs": [],
                "candidates": [],
                "history_topics": [],
                "topic_index": [],
                "known_topic_count": 0,
                "history_request": False,
                "requested_topic_count": 7,
                "topic_table_markdown": "",
                "anchor": {},
                "selected_section": {},
                "clarification_needed": False,
                "clarification_prompt": "",
                "pending_clarification": {},
                "clarification_resolution": {},
                "search": {"relation": "NEW", "total_pairs": 0, "candidate_count": 0},
            }
        # A local stop for one ambiguous subtask would hide every other task. In a
        # compound request, pass the ambiguity within its task entry so Provider can
        # answer the clear tasks and ask only about the unresolved part.
        dialogue_context["clarification_needed"] = False
        dialogue_context["clarification_prompt"] = ""
        dialogue_context["pending_clarification"] = {}
        dialogue_context["request_sequence_count"] = len(question_sequence)

    search_result = dialogue_context.get("search") if isinstance(dialogue_context.get("search"), dict) else {}
    anchor = dialogue_context.get("anchor") if isinstance(dialogue_context.get("anchor"), dict) else {}
    selected_pairs = dialogue_context.get("selected_pairs") or []
    _apr_timing_log(
        "dialogue_context_ready", memory_started, user_key=_apr_diag_ref(uid),
        dialog_key=_apr_diag_ref(identity.get("dialog_id")),
        message_key=_apr_diag_ref(identity.get("message_id")),
        relation=dialogue_context.get("relation"), reason=dialogue_context.get("reason"),
        question_count=len(question_sequence),
        total_pairs=search_result.get("total_pairs"), candidates=search_result.get("candidate_count", len(dialogue_context.get("candidates") or [])),
        selected_pairs=len(selected_pairs), selected_message_keys=[_apr_diag_ref(x.get("message_id")) for x in selected_pairs if isinstance(x, dict) and x.get("message_id")],
        anchor_message_key=_apr_diag_ref(anchor.get("message_id")), topic_index_count=len(dialogue_context.get("topic_index") or []),
    )

    # A follow-up may refer to an image/file from earlier in this conversation.
    # Rehydrate only the assets attached to State Manager's selected anchor/pairs;
    # do not mix older files into NEW requests or when a fresh attachment exists.
    restore_started = time.perf_counter()
    if bool(dialogue_context.get("clarification_needed")):
        # Clarification must be quick and must not restore/load unrelated assets.
        restored_assets = []
    else:
        asset_context = dialogue_context
        if len(question_sequence) > 1:
            for question_item, task_context in zip(question_sequence, question_contexts):
                if (
                    isinstance(task_context, dict)
                    and _text(task_context.get("relation")).upper() == "CONTINUE"
                    and _explicit_prior_asset_reference(question_item.get("request"))
                ):
                    asset_context = task_context
                    break
        visual_context, attachments, file_inputs, file_contents, restored_assets = _restore_selected_assets(
            uid, identity, asset_context, visual_context, attachments, file_inputs, file_contents,
            current_request=current_text,
        )
    _apr_timing_log(
        "selected_asset_restore", restore_started, user_key=_apr_diag_ref(uid),
        restored_assets=len(restored_assets or []), visual_items=len(visual_context or []),
        file_inputs=len(file_inputs or []), file_contents=len(file_contents or []),
    )

    interpretation_started = time.perf_counter()
    interpretation = build_interpretation(
        current_request=current_text,
        original_request=original,
        display_language=display_language,
        memory=dialogue_context,
        attachments=attachments or [],
        visual_context=visual_context or [],
        identity=identity,
        semantic_interpretation=semantic_interpretation,
    )
    request_structure = interpretation.setdefault("request_structure", {})
    request_structure["question_sequence"] = question_sequence
    request_structure["answer_sequence_in_order"] = True
    request_structure["question_search_engine"] = "state_manager_per_question_semantic_v2"
    request_structure["semantic_interpretation"] = semantic_interpretation
    request_structure["semantic_interpretation_version"] = "april_request_semantics_v1"
    request_structure["question_search_count"] = len(question_sequence)
    request_structure["question_relations"] = [
        {
            "step_index": item.get("step_index"),
            "relation": (item.get("dialogue_search") or {}).get("relation", "NEW"),
            "topic": (item.get("dialogue_search") or {}).get("topic", ""),
            "confidence": (item.get("dialogue_search") or {}).get("confidence", 0.0),
        }
        for item in question_sequence
    ]
    _apr_timing_log(
        "interpretation_ready", interpretation_started,
        relation=(interpretation.get("dialogue") or {}).get("relation"),
        task=(interpretation.get("intent") or {}).get("task"),
        requested_outputs=(interpretation.get("intent") or {}).get("requested_outputs"),
        question_sequence_count=len(((interpretation.get("request_structure") or {}).get("question_sequence") or [])),
        semantic_intent=semantic_interpretation.get("primary_intent"),
        search_direction=semantic_interpretation.get("direction"),
        history_request=bool(semantic_interpretation.get("history_request")),
    )

    selected_rooms = _select_rooms(interpretation)
    render_plan = _renderer_plan(interpretation, selected_rooms)

    identity["flow_id"] = _text(identity["flow_id"])
    request_build_started = time.perf_counter()
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
            "selected_section": dialogue_context.get("selected_section") or {},
            "clarification_needed": bool(dialogue_context.get("clarification_needed")),
            "pending_clarification": dialogue_context.get("pending_clarification") or {},
            "clarification_resolution": dialogue_context.get("clarification_resolution") or {},
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
                "selected_section": dialogue_context.get("selected_section") or {},
                "clarification_needed": bool(dialogue_context.get("clarification_needed")),
                "pending_clarification": dialogue_context.get("pending_clarification") or {},
                "clarification_resolution": dialogue_context.get("clarification_resolution") or {},
                "history_topics": dialogue_context.get("history_topics") or [],
                "topic_index": dialogue_context.get("topic_index") or [],
                "known_topic_count": int(dialogue_context.get("known_topic_count") or 0),
                "history_request": bool(dialogue_context.get("history_request")),
                "requested_topic_count": int(dialogue_context.get("requested_topic_count") or 7),
                "topic_table_markdown": dialogue_context.get("topic_table_markdown") or "",
                "anchor": dialogue_context.get("anchor") or {},
                "restored_assets": restored_assets,
                # Always carry the literal current request in the structured chain.
                # This field is active as a topic switch only for NEW dialogue.
                "new_dialogue_request": original or current_text,
                "new_dialogue_active": (
                    dialogue_context["relation"] == "NEW"
                    and not dialogue_context.get("history_request")
                ),
                "context": {
                    "active_topic": dialogue_context["active_topic"],
                    "reason": dialogue_context["reason"],
                    "confidence": dialogue_context["relation_confidence"],
                    "anchor_topic": (dialogue_context.get("anchor") or {}).get("topic", ""),
                },
                "mcdowell": {
                    "always": True,
                    "required": True,
                    "role": "presentation_and_render_layout",
                },
                "katex": {
                    "required_for_math": True,
                    "renderer": "FormulaRenderer",
                },
                "provider_policy": {
                    "output_limit": "model_native_no_application_cap",
                    "provider_calls_per_turn": 0 if dialogue_context.get("clarification_needed") else 1,
                    "local_clarification_allowed": True,
                    "retry_count": 0,
                    "question_sequence_required": True,
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
            "katex_required_for_math": True,
            "provider_calls_per_turn": 0 if dialogue_context.get("clarification_needed") else 1,
            "provider_retry_count": 0,
            "local_clarification_allowed": True,
            "input_modalities": (interpretation.get("input") or {}).get("modalities", []),
        },
    )
    _apr_timing_log("machine_request_build", request_build_started,
        relation=dialogue_context.get("relation"), selected_pairs=len(dialogue_context.get("selected_pairs") or []),
        candidates=len(dialogue_context.get("candidates") or []), input_chars=len(current_text),
        request_id_key=_apr_diag_ref(getattr(request, "request_id", "")))
    request.fiber.identity.user_id = uid
    # Search index is deliberately separate from binary storage. It contains a
    # bounded source preview, exact filenames/roles and the message ID used to
    # restore original bytes. The original bytes remain in dialogue_assets.
    request_metadata_started = time.perf_counter()
    attachment_index: list[dict[str, Any]] = []
    for item in (attachments or []):
        if not isinstance(item, dict):
            continue
        attachment_index.append({
            "filename": _text(item.get("filename"))[:200],
            "kind": _text(item.get("kind") or "file"),
            "mime_type": _text(item.get("mime_type") or item.get("content_type"))[:100],
            "asset_role": _text(item.get("asset_role") or "user_input"),
            "asset_message_id": _text(item.get("asset_message_id") or identity["message_id"]),
            "source_type": _text(item.get("source_type"))[:100],
            "analysis_summary": _text(item.get("analysis_summary"))[:1200],
            "analysis_key_details": item.get("analysis_key_details") if isinstance(item.get("analysis_key_details"), list) else [],
            "recalled_from_memory": bool(item.get("recalled_from_memory")),
            "requires_original_analysis": bool(item.get("requires_original_analysis")),
            "source_bytes_attached": (
                bool(item.get("requires_original_analysis"))
                if item.get("recalled_from_memory")
                else (_text(item.get("kind")).lower() in {"image", "text_file"} or bool(item.get("provider_readable", True)))
            ),
        })
    for item in (file_contents or []):
        if not isinstance(item, dict):
            continue
        attachment_index.append({
            "filename": _text(item.get("filename") or "file")[:200],
            "kind": "text_file",
            "mime_type": _text(item.get("mime_type") or "text/plain")[:100],
            "asset_role": _text(item.get("asset_role") or "user_input"),
            "asset_message_id": _text(item.get("asset_message_id") or identity["message_id"]),
            "content_preview": _text(item.get("content"))[:4500],
            "reader_truncated": bool(item.get("reader_truncated", False)),
            "source_chars": int(item.get("source_chars") or len(_text(item.get("content")))),
            "summary": _text(item.get("analysis_summary"))[:1200],
            "analysis_summary": _text(item.get("analysis_summary"))[:1200],
            "analysis_key_details": item.get("analysis_key_details") if isinstance(item.get("analysis_key_details"), list) else [],
            "recalled_from_memory": bool(item.get("recalled_from_memory")),
            "requires_original_analysis": bool(item.get("requires_original_analysis", True)),
            "source_bytes_attached": True,
        })
    for item in (visual_context or []):
        if not isinstance(item, dict):
            continue
        attachment_index.append({
            "filename": _text(item.get("filename") or "image")[:200],
            "kind": "image",
            "mime_type": _text(item.get("mime_type") or "image/*")[:100],
            "asset_role": _text(item.get("asset_role") or "user_input"),
            "asset_message_id": _text(item.get("asset_message_id") or identity["message_id"]),
            "source_type": _text(item.get("source_type") or "image")[:100],
            "analysis_summary": _text(item.get("analysis_summary"))[:1200],
            "analysis_key_details": item.get("analysis_key_details") if isinstance(item.get("analysis_key_details"), list) else [],
            "recalled_from_memory": bool(item.get("recalled_from_memory")),
            "requires_original_analysis": bool(item.get("requires_original_analysis")),
            "source_bytes_attached": not bool(item.get("recalled_from_memory")) or bool(item.get("requires_original_analysis")),
        })
    unique_index: list[dict[str, Any]] = []
    index_by_asset_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for item in attachment_index:
        asset_key = (
            _text(item.get("asset_message_id")),
            _text(item.get("filename")),
            _text(item.get("asset_role")),
            _text(item.get("kind")),
        )
        existing = index_by_asset_key.get(asset_key)
        if existing is None:
            existing = dict(item)
            index_by_asset_key[asset_key] = existing
            unique_index.append(existing)
        else:
            # Merge rather than discard the richer text-file entry: attachment
            # metadata is appended before the decoded text preview by design.
            for key, value in item.items():
                if value not in (None, "", [], {}):
                    existing[key] = value
    attachment_index = unique_index[:12]
    attachment_refs = [
        {key: item.get(key) for key in ("filename", "kind", "mime_type", "asset_role", "asset_message_id", "source_type", "size_bytes") if item.get(key) is not None}
        for item in attachment_index
    ]

    request.metadata = {
        "identity": identity,
        "interpretation": interpretation,
        "attachments": attachments or [],
        "attachment_index": attachment_index,
        # Raw file_data is request-scoped only. It is consumed by Provider and
        # is deliberately excluded from structured_request/DB persistence below.
        "file_inputs": [
            {
                "filename": _text(item.get("filename") or "file"),
                "mime_type": _text(item.get("mime_type") or "application/octet-stream"),
                "size_bytes": int(item.get("size_bytes") or 0),
                "file_data": _text(item.get("file_data")),
                "asset_role": _text(item.get("asset_role") or "user_input"),
                "asset_message_id": _text(item.get("asset_message_id")),
                "analysis_summary": _text(item.get("analysis_summary"))[:1200],
                "analysis_key_details": item.get("analysis_key_details") if isinstance(item.get("analysis_key_details"), list) else [],
            }
            for item in file_inputs
        ],
        "file_contents": [
            {
                "filename": _text(item.get("filename") or "file"),
                "mime_type": _text(item.get("mime_type") or "text/plain"),
                "size_bytes": int(item.get("size_bytes") or 0),
                "content": _text(item.get("content")),
                "reader_truncated": bool(item.get("reader_truncated", False)),
                "source_chars": int(item.get("source_chars") or len(_text(item.get("content")))),
                "asset_role": _text(item.get("asset_role") or "user_input"),
                "asset_message_id": _text(item.get("asset_message_id")),
                "analysis_summary": _text(item.get("analysis_summary"))[:1200],
                "analysis_key_details": item.get("analysis_key_details") if isinstance(item.get("analysis_key_details"), list) else [],
            }
            for item in file_contents
        ],
        "translation": translation or {},
    }
    _apr_timing_log("request_metadata_ready", request_metadata_started,
        attachment_index_count=len(attachment_index), visual_items=len(visual_context or []),
        file_inputs_count=len(file_inputs or []), file_contents_count=len(file_contents or []),
        file_content_chars=sum(len(_text(x.get("content"))) for x in (file_contents or []) if isinstance(x, dict)))

    provider_started = time.perf_counter()
    if bool(dialogue_context.get("clarification_needed")):
        # This is a deterministic UI-facing clarification, not a provider fallback.
        # The original request and options are persisted in dialogue_memory_record,
        # so the user's next reply resolves this exact question without losing intent.
        clarification_answer = _text(dialogue_context.get("clarification_prompt"))
        pending = dict(dialogue_context.get("pending_clarification") or {})
        if not clarification_answer:
            clarification_answer = "Уточните, пожалуйста, какой именно раздел продолжить. Исходный запрос сохранён."
        topic_name = _text(pending.get("active_topic") or dialogue_context.get("active_topic")) or "Тема диалога"
        memory_record = {
            "topic": topic_name[:140],
            "summary": "Ожидается уточнение выбранного раздела; исходный запрос сохранён без потери намерения пользователя.",
            "sections": [],
            "entities": [],
            "pending_clarification": pending,
        }
        provider_packet = {"machine_response": {
            "answer": clarification_answer,
            "content": clarification_answer,
            "summary": "Уточнение раздела для продолжения диалога.",
            "render_blocks": [{
                "type": "text",
                "renderer": get_web_renderer_registration("text").get("renderer", "MessageTextBlock"),
                "viewer": get_web_renderer_registration("text").get("viewer", "MessageTextBlock"),
                "content": clarification_answer,
            }],
            "artifacts": [],
            "metadata": {
                "identity": identity,
                "dialogue_memory_record": memory_record,
                "local_clarification": True,
                "provider_calls": 0,
            },
            "internal_answer_en": clarification_answer,
        }}
        provider_ms = 0.0
        _apr_timing_log("local_clarification_ready", provider_started,
            options=len(pending.get("options") or []), active_topic=topic_name,
            original_request_chars=len(_text(pending.get("original_request"))))
    else:
        provider_packet = await generate_text(request)
        provider_ms = round((time.perf_counter() - provider_started) * 1000, 1)
    provider_machine = provider_packet.get("machine_response") if isinstance(provider_packet, dict) else {}
    provider_machine = provider_machine if isinstance(provider_machine, dict) else {}
    provider_meta_for_log = provider_machine.get("metadata") if isinstance(provider_machine.get("metadata"), dict) else {}
    _apr_timing_log("provider_wait_complete", provider_started,
        request_id_key=_apr_diag_ref(getattr(request, "request_id", "")), provider_ms=provider_ms,
        answer_chars=len(_text(provider_machine.get("answer") or provider_machine.get("content"))),
        render_blocks=len(provider_machine.get("render_blocks") or []), artifacts=len(provider_machine.get("artifacts") or []),
        input_tokens=(provider_meta_for_log.get("usage") or {}).get("input_tokens"),
        output_tokens=(provider_meta_for_log.get("usage") or {}).get("output_tokens"),
        provider_fallback=bool(provider_meta_for_log.get("provider_fallback")),
        local_clarification=bool(provider_meta_for_log.get("local_clarification")))

    raw = provider_packet.get("machine_response") if isinstance(provider_packet, dict) else None
    if not isinstance(raw, dict):
        raise RuntimeError("PROVIDER_CONTRACT_MISSING")

    provider_metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    asset_summary_started = time.perf_counter()
    _persist_asset_analysis_summaries(
        uid,
        identity,
        attachment_index,
        provider_metadata.get("dialogue_memory_record"),
    )
    _apr_timing_log("asset_summary_persist", asset_summary_started, attachment_index_count=len(attachment_index))

    response_package_started = time.perf_counter()
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
    _apr_timing_log("response_package_ready", response_package_started, answer_chars=len(answer),
        raw_render_blocks=len(raw_blocks), raw_artifacts=len(raw_artifacts),
        packaged_blocks=len(packaged.get("render_blocks") or []), packaged_artifacts=len(packaged.get("artifacts") or []))

    image_result = None
    if (interpretation.get("intent") or {}).get("wants_image"):
        image_started = time.perf_counter()
        image_result = await _generate_image_artifact(
            interpretation,
            raw,
            identity,
        )
        _apr_timing_log("image_generation", image_started, succeeded=bool(image_result))
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
            "local_clarification": bool(provider_metadata.get("local_clarification")),
            "dialogue_memory_record": (
                raw.get("metadata", {}).get("dialogue_memory_record", {})
                if isinstance(raw.get("metadata"), dict) else {}
            ),
            "provider_fallback": bool(provider_metadata.get("provider_fallback")),
            "provider_error_code": _text(provider_metadata.get("provider_error_code")),
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

    scene_started = time.perf_counter()
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
    _apr_timing_log("scene_contract_build", scene_started,
        render_blocks=len(response.render_blocks or []), answer_chars=len(response.answer or ""))

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
            "asset_role": _text(item.get("asset_role") or "user_input"),
            "asset_message_id": _text(item.get("asset_message_id") or identity["message_id"]),
            "output_type": _text(item.get("output_type")),
        })
    safe_visual_context["items"] = safe_visual_items
    safe_visual_context["has_input_images"] = bool(safe_visual_items)

    output_asset_persist_started = time.perf_counter()
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
                metadata={"source_type": "generated_image", "asset_role": "april_output", "output_type": "image", "paired_message_id": identity["message_id"], "interpretation_id": identity["interpretation_id"], "generator": "C_APRIL_IMAGES_GENERATOR"},
            )

    # Save code/file output as a separately versioned asset paired to this turn.
    # A visible CodeBlock remains in SceneContract; this binary/text asset lets
    # later CONTINUE requests retrieve the exact source rather than its summary.
    output_asset_refs: list[dict[str, Any]] = []
    requested_outputs = set(str(x).lower() for x in (interpretation.get("intent") or {}).get("requested_outputs", []))
    should_persist_code = bool((interpretation.get("intent") or {}).get("wants_code") or (interpretation.get("intent") or {}).get("wants_file"))
    if should_persist_code:
        code_blocks = [block for block in normalized_blocks if isinstance(block, dict) and str(block.get("type") or "").lower() == "code"]
        seen_source_hashes: set[str] = set()
        import hashlib
        for block_index, block in enumerate(code_blocks[:4], 1):
            extracted = _source_code_from_block(block)
            if not extracted:
                continue
            code_text, language, extension = extracted
            code_bytes = code_text.encode("utf-8")
            source_hash = hashlib.sha256(code_bytes).hexdigest()
            if source_hash in seen_source_hashes:
                continue
            seen_source_hashes.add(source_hash)
            filename = _text(block.get("filename")) or f"april-output-{identity['message_id'][-10:]}-{block_index}.{extension}"
            saved_output = save_dialogue_asset(
                uid,
                dialog_id=identity["dialog_id"],
                conversation_id=identity["conversation_id"],
                message_id=identity["message_id"],
                filename=filename,
                mime_type="text/x-python" if extension == "py" else "text/plain",
                kind="text_file",
                content=code_bytes,
                text_content=code_text,
                turn_index=turn_index,
                metadata={
                    "source_type": "april_output_code", "asset_role": "april_output",
                    "output_type": "code", "language": language, "extension": extension,
                    "paired_message_id": identity["message_id"],
                    "interpretation_id": identity["interpretation_id"],
                    "source_input_assets": attachment_refs[:8],
                },
            )
            if saved_output:
                output_asset_refs.append({"filename": filename, "kind": "text_file", "asset_role": "april_output", "output_type": "code", "message_id": identity["message_id"], "sha256": source_hash, "language": language})

        # Persist explicit file artifacts as actual bytes/text, not only as a
        # caption in JSONB. Do not duplicate an already-saved CodeBlock.
        for artifact_index, artifact in enumerate((raw_artifacts or [])[:6], 1):
            if not isinstance(artifact, dict):
                continue
            artifact_type = _text(artifact.get("type") or artifact.get("artifact_type")).lower()
            if artifact_type not in {"file", "document", "text_file", "code_file"}:
                continue
            filename = _text(artifact.get("filename") or artifact.get("name") or f"april-output-{identity['message_id'][-10:]}-{artifact_index}.txt")
            mime = _text(artifact.get("mime_type") or artifact.get("content_type") or "text/plain")
            body_value = artifact.get("content") or artifact.get("text") or artifact.get("code")
            file_bytes = b""
            text_content = ""
            if isinstance(body_value, str) and body_value.strip():
                text_content = body_value
                file_bytes = body_value.encode("utf-8")
            encoded = artifact.get("file_base64") or artifact.get("base64") or artifact.get("b64_json")
            data_uri = artifact.get("data_uri") or artifact.get("file_data_uri")
            try:
                if isinstance(data_uri, str) and data_uri.startswith("data:") and ";base64," in data_uri:
                    header, b64 = data_uri.split(",", 1)
                    file_bytes = base64.b64decode(b64, validate=True)
                    mime = header[5:].split(";", 1)[0] or mime
                    if mime.startswith("text/"):
                        text_content = file_bytes.decode("utf-8", errors="replace")
                elif isinstance(encoded, str) and encoded:
                    file_bytes = base64.b64decode(encoded, validate=True)
                    if mime.startswith("text/"):
                        text_content = file_bytes.decode("utf-8", errors="replace")
            except Exception:
                file_bytes = b""
            if not file_bytes or len(file_bytes) > 10 * 1024 * 1024:
                continue
            source_hash = hashlib.sha256(file_bytes).hexdigest()
            if source_hash in seen_source_hashes:
                continue
            saved_output = save_dialogue_asset(
                uid,
                dialog_id=identity["dialog_id"], conversation_id=identity["conversation_id"],
                message_id=identity["message_id"], filename=filename, mime_type=mime,
                kind="text_file" if mime.startswith("text/") else "file", content=file_bytes,
                text_content=text_content, turn_index=turn_index,
                metadata={"source_type": "april_output_file", "asset_role": "april_output",
                          "output_type": "file", "paired_message_id": identity["message_id"],
                          "interpretation_id": identity["interpretation_id"], "source_input_assets": attachment_refs[:8]},
            )
            if saved_output:
                output_asset_refs.append({"filename": filename, "kind": "text_file" if mime.startswith("text/") else "file", "asset_role": "april_output", "output_type": "file", "message_id": identity["message_id"], "sha256": source_hash})

    _apr_timing_log("output_asset_persist", output_asset_persist_started,
        generated_asset_saved=generated_asset_saved, output_asset_refs=len(output_asset_refs))

    # Make the current Scene carry asset pointers and retrieval evidence as well
    # as the renderer blocks; no data URI or private file bytes enter the Scene.
    scene_contract = result.get("scene_contract") if isinstance(result.get("scene_contract"), dict) else {}
    scene_meta = scene_contract.get("metadata") if isinstance(scene_contract.get("metadata"), dict) else {}
    scene_meta["dialogue_assets"] = {
        "user_inputs": attachment_refs,
        "april_outputs": output_asset_refs,
        "pairing": {"user_id": uid, "dialog_id": identity["dialog_id"], "conversation_id": identity["conversation_id"], "message_id": identity["message_id"], "interpretation_id": identity["interpretation_id"]},
    }
    scene_contract["metadata"] = scene_meta
    result["scene_contract"] = scene_contract

    structured_request = _strip_inline_binary({
        "request_id": request.request_id,
        "goal": request.goal,
        "intent": dict(request.intent),
        "conversation": dict(request.conversation),
        "memory": dict(request.memory),
        "visual_context": safe_visual_context,
        "attachments": list(attachments or []),
        "attachment_index": attachment_index,
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
        "asset_refs": {
            "source_inputs": attachment_refs,
            "april_outputs": output_asset_refs + ([{"filename": f"april-generated-{identity['message_id']}.png", "kind": "image", "asset_role": "april_output", "output_type": "image", "message_id": identity["message_id"]}] if generated_asset_saved else []),
        },
        "dialogue_memory_record": (response.metadata or {}).get("dialogue_memory_record", {}),
    })

    pair_save_started = time.perf_counter()
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
    pair_save_ms = round((time.perf_counter() - pair_save_started) * 1000, 1)
    _apr_timing_log("dialogue_pair_persist", saved=bool(saved), elapsed_ms=pair_save_ms,
        answer_chars=len(answer), structured_request_fields=len(structured_request),
        structured_response_fields=len(structured_response), render_blocks=len(response.render_blocks or []),
        artifacts=len(response.artifacts or []))

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
            "dialogue_asset_refs": {"source_inputs": attachment_refs, "april_outputs": output_asset_refs},
            "interpretation": interpretation,
            "route": result.get("scene_contract", {}).get("metadata", {}).get("route", {}),
        }
    )
    _apr_timing_log("execute_total", pipeline_started, user_key=_apr_diag_ref(uid),
        dialog_key=_apr_diag_ref(identity.get("dialog_id")), message_key=_apr_diag_ref(identity.get("message_id")),
        relation=dialogue_context.get("relation"), answer_chars=len(answer), saved=bool(saved),
        provider_ms=provider_ms, restored_assets=len(restored_assets or []))
    return result


__all__ = ["execute", "PROCESSOR_VERSION", "CANONICAL_ROUTE"]
