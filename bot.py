"""APRIL canonical bot.ru gateway.

There is exactly one public chat route: POST /api/v1/chat.
Bot.ru owns the transport/input normalization boundary. It accepts text, voice,
screenshot/image and file content in the same authenticated envelope and passes
the normalized envelope to Exkrutor.
No separate botru_transport/translation route or file exists.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import hashlib
import hmac
import base64
import json
import os
import re
import traceback
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

from blocks.input_reader import parse_json_payload, parse_multipart_payload
from blocks.voice_reader import transcribe_voice_bytes
from core.executor import execute as execute_free
from core.Premium_executor import execute as execute_premium
from blocks.state_manager import (
    get_dialogue_pairs as get_free_dialogue_pairs,
    _topic_label as _free_topic_label,
    _row_subject_tokens as _free_row_subject_tokens,
    _subject_overlap as _free_subject_overlap,
    _topic_query_overlap as _free_topic_query_overlap,
)
from blocks.Premium_state_manager import (
    get_dialogue_pairs as get_premium_dialogue_pairs,
    _topic_label as _premium_topic_label,
    _row_subject_tokens as _premium_row_subject_tokens,
    _subject_overlap as _premium_subject_overlap,
    _topic_query_overlap as _premium_topic_query_overlap,
)
from storage import (
    activate_test_premium, find_or_create_user, get_user_plan,
    get_user_subscription_status, init_db, is_authenticated_user, resolve_user_id,
    delete_april_account, load_dialogue_history_index, load_dialogue_history_details,
    get_admin_user_telemetry, touch_user_activity,
    get_premium_support_status, get_premium_support_message_detail,
    mark_premium_support_message_read, send_premium_support_message,
    list_premium_support_messages, reply_premium_support_message,
)

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "10000"))
MAX_BODY_BYTES = int(os.getenv("APRIL_MAX_HTTP_BODY_BYTES", str(25 * 1024 * 1024)))
CANONICAL_CHAT_ROUTE = "/api/v1/chat"
CANONICAL_ROUTE_VERSION = "april_web_botru_exkrutor_v1"
INPUT_NORMALIZATION_VERSION = "botru_input_normalization_v2"


def _apr_timing_log(stage: str, started: float | None = None, **fields: Any) -> None:
    """Low-overhead diagnostic timing; logging must never affect the request path."""
    try:
        payload = {"component": "botru", "stage": stage}
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


def _resolve_user_utc_offset_minutes(data: dict[str, Any]) -> int | None:
    """Return a client UTC offset only when supplied explicitly or encoded in ISO time."""
    try:
        explicit = data.get("user_utc_offset_minutes")
        if explicit is not None and str(explicit).strip() != "":
            offset = int(float(explicit))
            if -14 * 60 <= offset <= 14 * 60:
                return offset
    except (TypeError, ValueError, OverflowError):
        pass
    raw = _text(data.get("message_timestamp"))
    match = re.search(r"([+-])(\d{2}):(\d{2})$", raw)
    if not match or raw.endswith("Z"):
        return None
    try:
        hours, minutes = int(match.group(2)), int(match.group(3))
        if hours > 14 or minutes > 59:
            return None
        offset = hours * 60 + minutes
        return offset if match.group(1) == "+" else -offset
    except (TypeError, ValueError, OverflowError):
        return None


def _resolve_message_timestamp(value: Any) -> tuple[datetime, str]:
    """Accept a browser send-time only when it is close to server receipt time.

    This preserves the user's actual local send moment for restored history while
    preventing arbitrary client timestamps from extending or shortening retention.
    """
    current = datetime.now(timezone.utc)
    raw = _text(value)
    if raw:
        try:
            parsed = datetime.fromisoformat(raw[:-1] + "+00:00" if raw.endswith("Z") else raw)
            parsed = parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
            if abs((current - parsed).total_seconds()) <= 300:
                return parsed, "client_send_time"
        except (TypeError, ValueError, OverflowError):
            pass
    return current, "server_received_time"


def _get_dialogue_pairs_for_plan(
    user_id: str,
    *,
    plan: str,
    refresh: bool = False,
    limit: int = 0,
) -> list[dict[str, Any]]:
    """Read the same canonical memory table through the selected plan's engine."""
    reader = get_premium_dialogue_pairs if _text(plan).lower() == "premium" else get_free_dialogue_pairs
    return reader(user_id, refresh=refresh, limit=limit)


def _detect_language(text: str, requested: str = "") -> str:
    requested = _text(requested).lower().replace("_", "-")
    if requested and requested not in {"auto", "default"}:
        # Accept browser locale tags (ru-RU, uk-UA, en-US) while keeping the
        # provider language contract stable and short.
        language = requested.split("-", 1)[0]
        if language in {"ru", "uk", "en", "ja", "zh", "ko", "ar", "hi", "el"}:
            return language
        return language or "en"
    value = text or ""
    low = value.lower()
    if re.search(r"[іїєґ]", low):
        return "uk"
    if re.search(r"[а-яё]", low):
        return "ru"
    if re.search(r"[\u3040-\u30ff]", value):
        return "ja"
    if re.search(r"[\u4e00-\u9fff]", value):
        return "zh"
    if re.search(r"[\uac00-\ud7af]", value):
        return "ko"
    if re.search(r"[\u0600-\u06ff]", value):
        return "ar"
    if re.search(r"[\u0900-\u097f]", value):
        return "hi"
    if re.search(r"[\u0370-\u03ff]", value):
        return "el"
    return "en"



def _decode_inline_file(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    raw = _text(value)
    if raw.startswith("data:") and "," in raw:
        raw = raw.split(",", 1)[1]
    return base64.b64decode(raw) if raw else b""


def _prepare_attachments(
    data: dict[str, Any],
    attachments: list[Any],
    *,
    voice_transcript: str = "",
) -> tuple[
    str,
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """Separate user instruction from attachment contents on one canonical route."""
    semantic_text: list[str] = []
    visual: list[dict[str, Any]] = []
    meta: list[dict[str, Any]] = []
    provider_files: list[dict[str, Any]] = []
    text_file_contents: list[dict[str, Any]] = []

    for att in attachments:
        item = getattr(att, "metadata", {}) or {}
        kind = str(getattr(att, "kind", "file") or "file")
        filename = _text(getattr(att, "filename", "file"))
        content_type = _text(getattr(att, "content_type", ""))
        size_bytes = int(getattr(att, "size_bytes", 0) or 0)
        meta.append({
            "filename": filename,
            "content_type": content_type,
            "kind": kind,
            "size_bytes": size_bytes,
            "source_type": item.get("source_type", kind),
            "asset_role": "user_input",
            "provider_readable": bool(item.get("provider_readable", kind in {"image", "text_file", "voice"})),
        })

        if kind == "voice":
            raw_voice = getattr(att, "data", b"") or item.get("data") or b""
            transcript = _text(voice_transcript)
            if not transcript and raw_voice:
                transcript = transcribe_voice_bytes(
                    raw_voice,
                    filename=filename or "voice.webm",
                    content_type=content_type,
                )
            if transcript:
                # Transcript is the semantic input; the original audio remains
                # represented by attachment metadata.
                semantic_text.append(transcript)

        elif kind == "text_file":
            text = _text(item.get("text"))
            if text:
                # File contents are evidence for the Provider, never part of
                # CURRENT_REQUEST. This prevents words such as "image",
                # "python" and "code" inside a file from changing intent.
                text_file_contents.append({
                    "filename": filename or "file",
                    "mime_type": content_type or item.get("mime_type") or "text/plain",
                    "content": text,
                    "size_bytes": size_bytes,
                    "reader_truncated": bool(item.get("truncated")),
                    "source_chars": int(item.get("source_chars") or len(text)),
                    "asset_role": "user_input",
                })

        elif kind == "image":
            uri = _text(item.get("data_uri"))
            if uri:
                visual.append({
                    "type": "input_image",
                    "image_url": uri,
                    "filename": filename,
                    "source_type": item.get("source_type", "image"),
                    "mime_type": content_type,
                    "asset_role": "user_input",
                })

        elif kind == "file":
            uri = _text(item.get("data_uri"))
            if uri:
                # Raw file bytes are transported to Provider separately from
                # persistent attachment metadata so PostgreSQL never becomes a
                # binary-file store.
                provider_files.append({
                    "type": "input_file",
                    "filename": filename or "file",
                    "file_data": uri,
                    "mime_type": content_type or item.get("mime_type") or "application/octet-stream",
                    "size_bytes": size_bytes,
                    "asset_role": "user_input",
                })

    return "\n\n".join(semantic_text), visual, meta, provider_files, text_file_contents


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    scene = result.get("scene_contract") or {}
    # SceneContract is the only rendering authority. Prefer its complete block
    # sequence even when a legacy top-level mirror is stale or shorter; this
    # prevents a generated image/diagram signal from disappearing at bot.ru.
    scene_blocks = scene.get("render_blocks") if isinstance(scene, dict) else None
    legacy_blocks = result.get("render_blocks")
    blocks = scene_blocks if isinstance(scene_blocks, list) and scene_blocks else (
        legacy_blocks if isinstance(legacy_blocks, list) else []
    )
    answer = _text(result.get("answer") or result.get("content"))
    if not answer:
        raise RuntimeError("CANONICAL_ANSWER_MISSING")
    return {
        "success": True,
        "canonical_route": CANONICAL_CHAT_ROUTE,
        "route_version": CANONICAL_ROUTE_VERSION,
        "single_route": True,
        "answer": answer,
        "content": result.get("content") or answer,
        "summary": result.get("summary", ""),
        "display_language": result.get("display_language", "en"),
        "internal_language": "en",
        "translation": result.get("translation", {}),
        "blocks": blocks,
        "render_blocks": blocks,
        "scene_contract": scene,
        "artifacts": result.get("artifacts", []),
        # Safe input metadata is returned so the Web can preserve the exact
        # filename/type/size in the user message. Raw bytes/data URIs are never
        # returned in the response. input_reader remains the sole reader for
        # documents/files; image_reader is used only for image/screenshot input.
        "attachments": result.get("attachments", []),
        "interpretation": result.get("interpretation", {}),
        "route": result.get("route", {}),
        "april_id": result.get("april_id"),
        "conversation_id": result.get("conversation_id"),
        "dialog_id": result.get("dialog_id"),
        "message_id": result.get("message_id"),
        "interpretation_id": result.get("interpretation_id"),
        "flow_id": result.get("flow_id"),
        "web_delivery": {
            "transport": "SceneContract",
            "renderer": "RenderMessage",
            "route": ["Web /api/v1/chat", "bot.ru", "Exkrutor", "SceneContract", "RenderMessage", "bot.ru", "Web"],
        },
    }


def _handle_payload(
    data: dict[str, Any],
    attachments: list[Any] | None = None,
    *,
    voice_transcript: str = "",
) -> tuple[int, dict[str, Any]]:
    pipeline_started = time.perf_counter()
    identity_started = time.perf_counter()
    identity = _canonical_identity(data)
    uid = identity["user_id"]
    message_created_at, timestamp_source = _resolve_message_timestamp(data.get("message_timestamp"))
    user_utc_offset_minutes = _resolve_user_utc_offset_minutes(data)
    original = _text(data.get("text") or data.get("message") or data.get("content"))
    _apr_timing_log("request_identity", identity_started, user_key=_apr_diag_ref(uid),
        dialog_key=_apr_diag_ref(identity.get("dialog_id")), message_key=_apr_diag_ref(identity.get("message_id")),
        flow_key=_apr_diag_ref(identity.get("flow_id")), input_chars=len(original), attachment_count=len(attachments or []))
    _apr_timing_log("message_timestamp_resolved", user_key=_apr_diag_ref(uid), source=timestamp_source,
                    message_key=_apr_diag_ref(identity.get("message_id")))
    conversation_id = identity["conversation_id"]
    dialog_id = identity["dialog_id"]
    message_id = identity["message_id"]
    if not uid:
        return _error("user_id required", 400)
    if not conversation_id and not dialog_id:
        return _error("conversation_id or dialog_id required", 400)

    # Plan is server-authoritative: derive the execution branch only from the
    # authenticated account's active entitlement in PostgreSQL, never from JSON.
    plan_started = time.perf_counter()
    active_plan = _text(get_user_plan(uid)).lower() or "free"
    is_premium = active_plan == "premium"
    _apr_timing_log(
        "plan_entitlement_resolved",
        plan_started,
        user_key=_apr_diag_ref(uid),
        active_plan=active_plan,
        processor="premium" if is_premium else "free",
    )

    attachments = attachments or []
    input_normalization_started = time.perf_counter()
    try:
        semantic_text, visual_context, attachment_meta, file_inputs, text_file_contents = _prepare_attachments(
            data, attachments, voice_transcript=voice_transcript
        )
        if semantic_text:
            original = (original + "\n\n" + semantic_text).strip()
        _apr_timing_log("input_normalization", input_normalization_started, user_key=_apr_diag_ref(uid),
            input_chars=len(original), semantic_attachment_chars=len(semantic_text),
            attachment_meta_count=len(attachment_meta), image_count=len(visual_context),
            file_input_count=len(file_inputs), text_file_count=len(text_file_contents),
            text_file_chars=sum(len(_text(x.get("content"))) for x in text_file_contents if isinstance(x, dict)))

        # Reject unreadable/empty uploads before synthesizing an instruction.  An
        # attachment-only message is valid only when the Reader produced actual
        # visual/file input for the Provider.
        if not original and not visual_context and not file_inputs and not text_file_contents:
            if attachment_meta:
                return _error("file is not readable by the Provider", 400)
            return _error("text, voice, image or file required", 400)

        # An attachment-only message is a valid user request.  Give Interpretation
        # an explicit neutral analysis task without mixing in the attachment bytes.
        if not original and attachment_meta:
            requested_language = _text(data.get("language") or data.get("display_language")).lower().replace("_", "-")
            if requested_language in {"auto", "default"}:
                requested_language = ""
            if not requested_language:
                # Use the last saved language for this exact authenticated dialog.
                # This keeps an image-only upload in Russian/Ukrainian chats localised.
                try:
                    prior_pairs = _get_dialogue_pairs_for_plan(uid, plan=active_plan, refresh=True, limit=24)
                    for prior in reversed(prior_pairs):
                        if (
                            _text(prior.get("dialog_id")) == (dialog_id or conversation_id)
                            and _text(prior.get("conversation_id")) == (conversation_id or dialog_id)
                            and _text(prior.get("language"))
                        ):
                            requested_language = _text(prior.get("language")).lower()
                            break
                except Exception:
                    pass
            kinds = {str(item.get("kind") or "").lower() for item in attachment_meta}
            has_image = "image" in kinds
            has_file = bool(kinds & {"file", "text_file"})
            if has_image and has_file:
                defaults = {
                    "ru": (
                        "Разбери все вложения как одну задачу: кратко опиши каждое фото и файл отдельно, "
                        "затем объясни их связь только там, где она подтверждается содержимым."
                    ),
                    "uk": (
                        "Розглянь усі вкладення як одне завдання: коротко опиши кожне фото й файл окремо, "
                        "потім поясни їхній зв’язок лише там, де це підтверджується вмістом."
                    ),
                    "en": (
                        "Treat all attachments as one task: briefly describe each image and file separately, "
                        "then explain their relationship only where supported by the contents."
                    ),
                }
            elif has_image:
                defaults = {
                    "ru": "Опиши содержимое прикреплённого изображения.",
                    "uk": "Опиши вміст прикріпленого зображення.",
                    "en": "Describe the attached image.",
                }
            else:
                defaults = {
                    "ru": "Прочитай прикреплённый файл и кратко объясни его содержимое.",
                    "uk": "Прочитай прикріплений файл і коротко поясни його вміст.",
                    "en": "Read the attached file and briefly explain its contents.",
                }
            language_key = requested_language.replace("_", "-").split("-", 1)[0] if requested_language else ""
            original = defaults[language_key] if language_key in defaults else defaults["en"]

        # Current attachments remain request-scoped and are passed directly to Exkrutor.
        # Persistent dialogue history and its searchable attachment evidence are saved
        # with the USER↔APRIL pair in dialogue_memory; no binary sidecar table is used.
        _apr_timing_log("input_attachment_forwarding", None, user_key=_apr_diag_ref(uid),
            attachment_count=len(attachments or []), visual_items=len(visual_context),
            file_inputs=len(file_inputs), file_contents=len(text_file_contents))

        language = _detect_language(
            original or voice_transcript,
            data.get("language") or data.get("display_language"),
        )
        # bot.ru is transport/input normalization only.  The semantic structure is
        # created by the Interpretation layer after Exkrutor's memory search.
        internal_text = original
        translation = {
            "version": INPUT_NORMALIZATION_VERSION,
            "source_language": language,
            "internal_language": "same_as_input",
            "translated": False,
            "stage": "bot.ru",
        }

        # The display name is a user preference supplied by April Web. The
        # authenticated account ID above remains authoritative and is never
        # taken from this field.
        user_display_name = _text(
            data.get("display_name") or data.get("user_display_name") or data.get("name")
        )[:80]

        executor_started = time.perf_counter()
        selected_executor = execute_premium if is_premium else execute_free
        selected_executor_name = "Premium_executor" if is_premium else "executor"
        _apr_timing_log(
            "processor_selected",
            user_key=_apr_diag_ref(uid),
            active_plan=active_plan,
            processor=selected_executor_name,
            canonical_route=CANONICAL_CHAT_ROUTE,
        )
        result = asyncio.run(selected_executor(
            uid,
            text=original,
            internal_text=internal_text,
            display_language=language,
            flow_id=_text(data.get("flow_id")),
            conversation_id=conversation_id or dialog_id,
            dialog_id=dialog_id,
            message_id=message_id,
            resume_message_id=_text(data.get("resume_message_id")),
            interpretation_id=_text(data.get("interpretation_id")),
            visual_context=visual_context,
            attachments=attachment_meta,
            file_inputs=file_inputs,
            file_contents=text_file_contents,
            translation=translation,
            user_display_name=user_display_name,
            message_created_at=message_created_at,
            user_utc_offset_minutes=user_utc_offset_minutes,
        ))
        _apr_timing_log("executor_returned", executor_started, user_key=_apr_diag_ref(uid),
            message_key=_apr_diag_ref(message_id), result_type=type(result).__name__,
            answer_chars=len(_text(result.get("answer") or result.get("content"))) if isinstance(result, dict) else 0)
        if isinstance(result, dict):
            result["attachments"] = [
                {
                    "filename": _text(item.get("filename") or "file"),
                    "content_type": _text(item.get("content_type") or item.get("mime_type") or "application/octet-stream"),
                    "kind": _text(item.get("kind") or "file"),
                    "size_bytes": int(item.get("size_bytes") or 0),
                    "source_type": _text(item.get("source_type") or item.get("kind") or "file"),
                    "provider_readable": bool(item.get("provider_readable", False)),
                }
                for item in attachment_meta
            ]
        payload_started = time.perf_counter()
        response_payload = _payload(result)
        _apr_timing_log("http_payload_build", payload_started,
            answer_chars=len(_text(response_payload.get("answer"))),
            render_blocks=len(response_payload.get("render_blocks") or []),
            artifacts=len(response_payload.get("artifacts") or []))
        _apr_timing_log("handle_payload_total", pipeline_started, user_key=_apr_diag_ref(uid),
            message_key=_apr_diag_ref(message_id), status=200)
        return 200, response_payload
    except Exception as exc:
        traceback.print_exc()
        return _error(str(exc), 500)


def _error(message: str, status: int = 500) -> tuple[int, dict[str, Any]]:
    return status, {"success": False, "error": _text(message) or "INTERNAL_ERROR", "canonical_route": CANONICAL_CHAT_ROUTE}


def _voice_attachment(attachments: list[Any]) -> Any | None:
    for att in attachments:
        if str(getattr(att, "kind", "") or "").lower() == "voice":
            return att
    return None


def _transcribe_attachment(att: Any) -> str:
    """Delegate transcription to the existing Voice block."""
    raw_voice = getattr(att, "data", b"") or b""
    if not raw_voice:
        raise ValueError("VOICE_EMPTY")
    return transcribe_voice_bytes(
        raw_voice,
        filename=_text(getattr(att, "filename", "voice.webm")) or "voice.webm",
        content_type=_text(getattr(att, "content_type", "")),
    )


def _canonical_identity(data: dict[str, Any]) -> dict[str, str]:
    """Create one identity tuple and reuse it for transcript + final answer."""
    conversation_id = _text(data.get("conversation_id") or data.get("dialog_id"))
    dialog_id = _text(data.get("dialog_id") or conversation_id)
    message_id = _text(data.get("message_id")) or f"msg_{uuid.uuid4().hex}"
    flow_id = _text(data.get("flow_id")) or f"flow_{uuid.uuid4().hex}"
    return {
        "user_id": _text(data.get("user_id") or data.get("april_id")),
        "conversation_id": conversation_id,
        "dialog_id": dialog_id,
        "message_id": message_id,
        "interpretation_id": _text(data.get("interpretation_id")) or f"interp_{uuid.uuid4().hex}",
        "flow_id": flow_id,
    }


def _handle_voice_stream(
    data: dict[str, Any],
    attachments: list[Any],
    write_event: Any,
) -> None:
    voice = _voice_attachment(attachments)
    if voice is None:
        status, payload = _handle_payload(data, attachments)
        write_event({"type": "answer", "status": status, "data": payload})
        return

    identity = _canonical_identity(data)
    if not identity["user_id"]:
        raise ValueError("USER_ID_REQUIRED")
    if not identity["conversation_id"] and not identity["dialog_id"]:
        raise ValueError("conversation_id or dialog_id required")

    routed_data = dict(data)
    routed_data.update(identity)

    # Voice block -> existing Provider transcription. Track this separately from
    # the answer pipeline so production logs show exactly where time is spent.
    voice_started = time.perf_counter()
    transcript = _transcribe_attachment(voice)
    transcribe_ms = round((time.perf_counter() - voice_started) * 1000, 1)
    print(
        f"[APRIL_VOICE] stage=transcript_ready elapsed_ms={transcribe_ms} "
        f"transcript_chars={len(transcript or '')}",
        flush=True,
    )
    if not transcript:
        raise ValueError("VOICE_EMPTY_TRANSCRIPT")

    # First event on the same POST /api/v1/chat connection.
    write_event({
        "type": "transcript",
        "success": True,
        "text": transcript,
        "canonical_route": CANONICAL_CHAT_ROUTE,
        "april_id": identity["user_id"],
        "user_id": identity["user_id"],
        "conversation_id": identity["conversation_id"],
        "dialog_id": identity["dialog_id"],
        "message_id": identity["message_id"],
        "interpretation_id": identity["interpretation_id"],
        "flow_id": identity["flow_id"],
    })

    # Continue on the same canonical route; no second Web request is created.
    # The canonical pipeline can take longer than an intermediary's idle-stream
    # timeout (especially when Images 2.0 is involved). Run it in one worker and
    # emit JSON progress frames while it works so the client/proxy sees activity.
    # The frontend intentionally ignores unknown event types and still consumes
    # the same final {type:"answer"} SceneContract payload.
    answer_started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="april-voice-answer") as pool:
        pending = pool.submit(
            _handle_payload,
            routed_data,
            attachments,
            voice_transcript=transcript,
        )
        while True:
            try:
                status, payload = pending.result(timeout=6.0)
                break
            except FutureTimeoutError:
                write_event({
                    "type": "progress",
                    "stage": "processing",
                    "canonical_route": CANONICAL_CHAT_ROUTE,
                    "flow_id": identity["flow_id"],
                })
    answer_ms = round((time.perf_counter() - answer_started) * 1000, 1)
    scene_contract = payload.get("scene_contract") if isinstance(payload, dict) else {}
    scene_metadata = scene_contract.get("metadata") if isinstance(scene_contract, dict) else {}
    provider_ms = scene_metadata.get("provider_ms") if isinstance(scene_metadata, dict) else None
    print(
        f"[APRIL_VOICE] stage=answer_ready elapsed_ms={answer_ms} "
        f"provider_ms={provider_ms if provider_ms is not None else 'unknown'} "
        f"total_ms={round((time.perf_counter() - voice_started) * 1000, 1)} "
        f"http_status={status}",
        flush=True,
    )
    write_event({"type": "answer", "status": status, "data": payload})


def _history_json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError):
            return {}
    return {}


def _history_item(row: dict[str, Any]) -> dict[str, Any]:
    request_data = _history_json_dict(row.get("structured_request"))
    response_data = _history_json_dict(row.get("structured_response"))
    intent = request_data.get("intent") if isinstance(request_data.get("intent"), dict) else {}
    goal = _text(request_data.get("goal") or intent.get("user_goal") or intent.get("goal"))
    user_text = _text(row.get("user_text"))
    created_at_value = row.get("created_at") or 0.0
    created_at = float(created_at_value.timestamp()) if hasattr(created_at_value, "timestamp") else float(created_at_value)
    stable_memory_key = _text(row.get("message_id")) or f"legacy-memory-{_text(row.get('id'))}"
    return {
        "id": stable_memory_key,
        # Legacy rows without a message_id still receive a deterministic lookup
        # key based on their existing dialogue_memory primary key.
        "message_id": stable_memory_key,
        "user_id": _text(row.get("user_id")),
        "dialog_id": _text(row.get("dialog_id")),
        "conversation_id": _text(row.get("conversation_id")),
        "title": (goal or user_text or "Сохранённый диалог").strip()[:140],
        "user_text": user_text,
        "april_text": _text(row.get("april_text")),
        "created_at": created_at,
        "turn_index": int(row.get("turn_index") or 0),
        "structured_response": response_data,
    }


def _history_index_payload(user_id: str) -> tuple[int, dict[str, Any]]:
    """Serve the history screen's lightweight list without loading scene JSON."""
    if not user_id:
        return 400, {"success": False, "error": "USER_ID_REQUIRED"}
    started = time.perf_counter()
    try:
        snapshot = load_dialogue_history_index(user_id)
        if snapshot is None:
            return 503, {"success": False, "error": "HISTORY_UNAVAILABLE"}
        if not snapshot.get("authenticated"):
            return 401, {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}
        rows = snapshot.get("rows") if isinstance(snapshot.get("rows"), list) else []
        history = []
        for row in reversed(rows):
            if not isinstance(row, dict):
                continue
            history.append({key: row.get(key) for key in (
                "id", "message_id", "dialog_id", "conversation_id", "title",
                "topic_label", "relation", "user_text", "april_text", "created_at", "turn_index"
            )})
        _apr_timing_log(
            "history_index_loaded",
            started,
            user_key=_apr_diag_ref(snapshot.get("user_id") or user_id),
            plan=str(snapshot.get("plan") or "free"),
            count=len(history),
            payload_mode="lightweight_index",
        )
        return 200, {
            "success": True,
            "user_id": str(snapshot.get("user_id") or user_id),
            "window_hours": 24 if int(snapshot.get("window_hours") or 12) == 24 else 12,
            "count": len(history),
            "history": history,
            "canonical_route": CANONICAL_CHAT_ROUTE,
        }
    except Exception as exc:
        print(f"[APRIL_HISTORY] INDEX_READ_ERROR type={type(exc).__name__}", flush=True)
        return 503, {"success": False, "error": "HISTORY_UNAVAILABLE"}


def _history_payload(user_id: str, message_id: str = "") -> tuple[int, dict[str, Any]]:
    """Restore a selected topic from lightweight candidates plus selected full payloads.

    Older versions forced the Premium/Free state manager to hydrate every retained
    row, including all JSONB scenes and image data, on every history click. Here the
    semantic match uses the lightweight history index, and full renderer data is read
    only for the topic pairs selected for display.
    """
    if not user_id:
        return 400, {"success": False, "error": "USER_ID_REQUIRED"}

    try:
        index_started = time.perf_counter()
        snapshot = load_dialogue_history_index(user_id)
        if snapshot is None:
            return 503, {"success": False, "error": "HISTORY_UNAVAILABLE"}
        if not snapshot.get("authenticated"):
            return 401, {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}

        active_plan = _text(snapshot.get("plan")).lower() or "free"
        is_premium = active_plan == "premium"
        window_hours = 24 if is_premium else 12
        topic_label = _premium_topic_label if is_premium else _free_topic_label
        row_subject_tokens = _premium_row_subject_tokens if is_premium else _free_row_subject_tokens
        subject_overlap = _premium_subject_overlap if is_premium else _free_subject_overlap
        topic_query_overlap = _premium_topic_query_overlap if is_premium else _free_topic_query_overlap
        light_rows = [row for row in (snapshot.get("rows") or []) if isinstance(row, dict)]
        _apr_timing_log(
            "history_restore_index_loaded",
            index_started,
            user_key=_apr_diag_ref(snapshot.get("user_id") or user_id),
            plan=active_plan,
            count=len(light_rows),
            payload_mode="lightweight_topic_match",
        )

        target_position = next((index for index, row in enumerate(light_rows) if _text(row.get("message_id")) == message_id), None)
        if target_position is None:
            return 404, {"success": False, "error": "HISTORY_ENTRY_NOT_FOUND"}
        target_row = light_rows[target_position]

        def match_row(row: dict[str, Any]) -> dict[str, Any]:
            # Keep the topic scalar from JSONB in the match text without hydrating
            # complete structured_request/structured_response objects.
            output = dict(row)
            topic = _text(row.get("topic_label") or row.get("title"))
            output["user_text"] = " ".join(part for part in (
                topic,
                _text(row.get("title")),
                _text(row.get("user_text")),
                _text(row.get("april_text")),
            ) if part)
            return output

        target_match_row = match_row(target_row)
        target_topic = _text(target_row.get("topic_label") or topic_label(target_match_row) or target_row.get("title") or target_row.get("user_text"))
        target_subjects = row_subject_tokens(target_match_row)
        candidates = []
        for row_position, row in enumerate(light_rows):
            candidate_id = _text(row.get("message_id"))
            if not candidate_id or candidate_id == message_id:
                continue
            # Keep Free's previous target + up to three prior pairs behavior;
            # Premium restores the wider topic thread in both directions.
            if not is_premium and row_position >= target_position:
                continue
            candidate_match_row = match_row(row)
            candidate_topic = _text(row.get("topic_label") or topic_label(candidate_match_row) or row.get("title") or row.get("user_text"))
            topic_score = topic_query_overlap(target_topic, candidate_topic)
            subject_score = subject_overlap(target_subjects, row_subject_tokens(candidate_match_row))
            score = max(topic_score, subject_score * 0.85)
            if topic_score >= 0.35 or subject_score >= 0.30:
                candidates.append((score, row))

        # Include every strongly related pair up to a practical mobile-rendering
        # ceiling. Do not use dialog_id as a boundary: it may span the whole memory
        # window and can otherwise bring back unrelated topics.
        candidates.sort(key=lambda value: (
            value[0],
            float(value[1].get("created_at") or 0),
            int(value[1].get("turn_index") or 0),
        ), reverse=True)
        MAX_RESTORE_PAIRS = 24 if is_premium else 4
        chosen_rows = [target_row] + [row for _score, row in candidates[:MAX_RESTORE_PAIRS - 1]]
        selected_ids = list(dict.fromkeys(_text(row.get("message_id")) for row in chosen_rows if _text(row.get("message_id"))))

        detail_started = time.perf_counter()
        full_rows = load_dialogue_history_details(user_id, selected_ids)
        full_by_id = {
            _text(row.get("message_id")) or f"legacy-memory-{_text(row.get('id'))}": row
            for row in full_rows if isinstance(row, dict)
        }
        ordered_ids = [message_id] + [
            _text(row.get("message_id")) for row in chosen_rows
            if _text(row.get("message_id")) and _text(row.get("message_id")) != message_id
        ]
        ordered_ids = list(dict.fromkeys(ordered_ids))
        selected_rows = [full_by_id[mid] for mid in ordered_ids if mid in full_by_id]
        selected_rows.sort(key=lambda row: (
            float(row.get("created_at") or 0),
            int(row.get("turn_index") or 0),
            _text(row.get("message_id")),
        ))
        if not any((_text(row.get("message_id")) or f"legacy-memory-{_text(row.get('id'))}") == message_id for row in selected_rows):
            return 404, {"success": False, "error": "HISTORY_ENTRY_NOT_FOUND"}

        _apr_timing_log(
            "history_restore_details_loaded",
            detail_started,
            user_key=_apr_diag_ref(user_id),
            target_key=_apr_diag_ref(message_id),
            selected_pairs=len(selected_rows),
            candidate_pairs=len(candidates),
            full_rows=len(full_rows),
        )

        full_records = []
        for row in selected_rows:
            item = _history_item(row)
            full_records.append((item, row))
        target_item = next((item for item, _row in full_records if item["message_id"] == message_id), None)
        if target_item is None:
            return 404, {"success": False, "error": "HISTORY_ENTRY_NOT_FOUND"}

        messages = []
        for item, _row in full_records:
            timestamp = item["created_at"]
            stamp_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp)) if timestamp else ""
            stamp_time = time.strftime("%H:%M", time.localtime(timestamp)) if timestamp else ""
            structured_response = item["structured_response"]
            scene_contract = structured_response.get("scene_contract") if isinstance(structured_response.get("scene_contract"), dict) else {}
            render_blocks = structured_response.get("render_blocks") if isinstance(structured_response.get("render_blocks"), list) else []
            if render_blocks and not scene_contract.get("render_blocks"):
                scene_contract = {**scene_contract, "render_blocks": render_blocks}
            user_id_value = item["message_id"] or f"memory-{item['turn_index']}"
            messages.append({
                "id": f"{user_id_value}:user",
                "role": "user",
                "content": item["user_text"],
                "time": stamp_time,
                "created_at": stamp_iso,
                "message_id": item["message_id"],
                "dialog_id": item["dialog_id"],
                "conversation_id": item["conversation_id"],
            })
            assistant_message = {
                "id": f"{user_id_value}:april",
                "role": "assistant",
                "content": _text(structured_response.get("answer") or structured_response.get("content") or item["april_text"]),
                "summary": _text(structured_response.get("summary")),
                "scene_contract": scene_contract,
                "render_blocks": render_blocks,
                "time": stamp_time,
                "created_at": stamp_iso,
                "message_id": item["message_id"],
                "dialog_id": item["dialog_id"],
                "conversation_id": item["conversation_id"],
            }
            # Preserve renderer/supporting data stored beside scene_contract. These
            # fields are often small references/state objects, not duplicate prose.
            for field in (
                "asset_refs", "visual_state", "workspace_state", "scene_events",
                "scene_vector", "active_scene", "renderer_state", "attachments",
                "images", "image", "file",
            ):
                value = structured_response.get(field)
                if value not in (None, "", [], {}):
                    assistant_message[field] = value
            messages.append(assistant_message)

        return 200, {
            "success": True,
            "user_id": user_id,
            "window_hours": window_hours,
            "target": {key: target_item[key] for key in (
                "id", "message_id", "dialog_id", "conversation_id", "title", "created_at"
            )},
            "messages": messages,
            "canonical_route": CANONICAL_CHAT_ROUTE,
        }
    except Exception as exc:
        print(f"[APRIL_HISTORY] READ_ERROR type={type(exc).__name__}", flush=True)
        return 503, {"success": False, "error": "HISTORY_UNAVAILABLE"}


class AprilHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "AprilBotRU/3.0"

    def _service_authorized(self) -> bool:
        expected = str(os.getenv("APRIL_WEB_TO_BOT_TOKEN", "")).strip()
        supplied = str(self.headers.get("X-April-Service-Token", "")).strip()
        authorized = len(expected) >= 32 and bool(supplied) and hmac.compare_digest(expected, supplied)
        if not authorized:
            # Never print the credential. Compare short one-way fingerprints
            # against APRIL_CANONICAL_AUTH_REJECTED in Vercel logs instead.
            def fingerprint(value: str) -> str:
                return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12] if value else "missing"
            print("[APRIL_AUTH_DIAG] " + json.dumps({
                "path": self.path.split("?", 1)[0],
                "expected_present": bool(expected),
                "expected_length": len(expected),
                "expected_fingerprint": fingerprint(expected),
                "supplied_present": bool(supplied),
                "supplied_length": len(supplied),
                "supplied_fingerprint": fingerprint(supplied),
                "match": False,
            }, separators=(",", ":")), flush=True)
        return authorized

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        # RFC 9110: a 204 response must not advertise/contain a JSON body.  The
        # previous Content-Length: 2 with no bytes desynchronised HTTP/1.1 keep-alive
        # connections; subsequent telemetry JSON was then parsed as a request line.
        body = b"" if status == 204 else json.dumps(
            payload, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if status != 204:
            self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self._send_json(204, {})

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.path == "/api/subscription/status":
            if not self._service_authorized():
                self.close_connection = True
                self._send_json(401, {"success": False, "error": "SERVICE_AUTH_REQUIRED"})
                return
            user_id = _text(self.headers.get("X-April-User-Id"))
            if not user_id:
                self._send_json(400, {"success": False, "error": "USER_ID_REQUIRED"})
                return
            if not _text(os.getenv("DATABASE_URL")):
                self._send_json(503, {"success": False, "error": "DATABASE_UNAVAILABLE"})
                return
            if not is_authenticated_user(user_id):
                self._send_json(401, {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"})
                return
            status = get_user_subscription_status(user_id)
            if not status:
                self._send_json(503, {"success": False, "error": "SUBSCRIPTION_STATUS_UNAVAILABLE"})
                return
            self._send_json(200, {"success": True, **status})
            return
        if parsed.path == CANONICAL_CHAT_ROUTE:
            query = parse_qs(parsed.query, keep_blank_values=False)
            mode = query.get("mode", [""])[0]
            if mode == "telemetry":
                if not self._service_authorized():
                    self._send_json(401, {"success": False, "error": "SERVICE_AUTH_REQUIRED"})
                    return
                supplied_admin_id = _text(self.headers.get("X-April-User-Id"))
                expected_admin_id = _text(os.getenv("APRIL_SUPERADMIN_APRIL_ID", "APR-WMBS-8W4Y"))
                if not supplied_admin_id or supplied_admin_id != expected_admin_id:
                    self._send_json(403, {"success": False, "error": "SUPERADMIN_REQUIRED"})
                    return
                telemetry = get_admin_user_telemetry()
                if not telemetry:
                    self._send_json(503, {"success": False, "error": "TELEMETRY_UNAVAILABLE"})
                    return
                self._send_json(200, {"success": True, **telemetry})
                return
            if mode == "support":
                if not self._service_authorized():
                    self.close_connection = True
                    self._send_json(401, {"success": False, "error": "SERVICE_AUTH_REQUIRED"})
                    return
                supplied_user_id = _text(self.headers.get("X-April-User-Id"))
                if not supplied_user_id:
                    self._send_json(400, {"success": False, "error": "USER_ID_REQUIRED"})
                    return
                if not _text(os.getenv("DATABASE_URL")):
                    self._send_json(503, {"success": False, "error": "DATABASE_UNAVAILABLE"})
                    return
                if not is_authenticated_user(supplied_user_id):
                    self._send_json(401, {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"})
                    return
                expected_admin_id = _text(os.getenv("APRIL_SUPERADMIN_APRIL_ID", "APR-WMBS-8W4Y"))
                is_admin = supplied_user_id == expected_admin_id
                requested_message_id = _text(query.get("message_id", [""])[0])
                if requested_message_id:
                    detail = get_premium_support_message_detail(
                        supplied_user_id, requested_message_id, is_admin=is_admin,
                    )
                    if not detail or detail.get("success") is not True:
                        error = _text((detail or {}).get("error") or "SUPPORT_MESSAGE_NOT_FOUND")
                        status_code = 503 if error in {"DATABASE_UNAVAILABLE", "SUPPORT_UNAVAILABLE"} else 404
                        self._send_json(status_code, detail or {"success": False, "error": error})
                        return
                    self._send_json(200, detail)
                    return
                if is_admin:
                    inbox = list_premium_support_messages(limit=10)
                    if not inbox:
                        self._send_json(503, {"success": False, "error": "SUPPORT_INBOX_UNAVAILABLE"})
                        return
                    self._send_json(200, inbox)
                    return
                status = get_premium_support_status(supplied_user_id)
                if not status:
                    self._send_json(503, {"success": False, "error": "SUPPORT_STATUS_UNAVAILABLE"})
                    return
                self._send_json(200, status)
                return
            if mode == "history":
                # Both layers authenticate: Web verifies NextAuth, Bot verifies
                # the service token and checks that the forwarded account exists.
                if not self._service_authorized():
                    self._send_json(401, {"success": False, "error": "SERVICE_AUTH_REQUIRED"})
                    return
                history_request_started = time.perf_counter()
                supplied_user_id = _text(self.headers.get("X-April-User-Id"))
                message_id = _text(self.headers.get("X-April-Message-Id"))
                # Listing uses a single lightweight indexed query. The full scene
                # payload and topic-vector retrieval are loaded only after a user
                # explicitly opens one saved entry.
                user_key = supplied_user_id
                if message_id:
                    user_id = resolve_user_id(supplied_user_id) or ""
                    user_key = user_id or supplied_user_id
                    status, payload = _history_payload(user_id, message_id)
                else:
                    status, payload = _history_index_payload(supplied_user_id)
                    user_key = str(payload.get("user_id") or supplied_user_id)
                _apr_timing_log("history_response", history_request_started,
                                user_key=_apr_diag_ref(user_key), status=status,
                                count=int(payload.get("count") or 0), message_count=len(payload.get("messages") or []),
                                mode="restore" if bool(message_id) else "index")
                self._send_json(status, payload)
                return
        if parsed.path == "/" or parsed.path == CANONICAL_CHAT_ROUTE:
            self._send_json(200, {"success": True, "service": "april-bot", "canonical_route": CANONICAL_CHAT_ROUTE, "route_version": CANONICAL_ROUTE_VERSION})
            return
        self._send_json(404, {"success": False, "error": "NOT_FOUND"})

    def do_POST(self) -> None:
        parsed = urlsplit(self.path)
        parsed_path = parsed.path
        if parsed_path == CANONICAL_CHAT_ROUTE and parse_qs(parsed.query, keep_blank_values=False).get("mode", [""])[0] == "support":
            if not self._service_authorized():
                self.close_connection = True
                self._send_json(401, {"success": False, "error": "SERVICE_AUTH_REQUIRED"})
                return
            user_id = _text(self.headers.get("X-April-User-Id"))
            if not user_id:
                self._send_json(400, {"success": False, "error": "USER_ID_REQUIRED"})
                return
            if not _text(os.getenv("DATABASE_URL")):
                self._send_json(503, {"success": False, "error": "DATABASE_UNAVAILABLE"})
                return
            if not is_authenticated_user(user_id):
                self._send_json(401, {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 0 or length > 1_000_000:
                    self.close_connection = True
                    self._send_json(413, {"success": False, "error": "REQUEST_BODY_TOO_LARGE"})
                    return
                raw = self.rfile.read(length) if length else b""
                body = json.loads(raw.decode("utf-8") or "{}") if raw else {}
                if not isinstance(body, dict):
                    self._send_json(400, {"success": False, "error": "INVALID_REQUEST"})
                    return
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                self._send_json(400, {"success": False, "error": "INVALID_JSON"})
                return

            action = _text(body.get("support_action")).lower()
            expected_admin_id = _text(os.getenv("APRIL_SUPERADMIN_APRIL_ID", "APR-WMBS-8W4Y"))
            if action == "mark_read":
                is_admin = user_id == expected_admin_id
                result = mark_premium_support_message_read(
                    user_id, body.get("message_id"), is_admin=is_admin,
                )
                if result.get("success") is True:
                    self._send_json(200, result)
                    return
                error = _text(result.get("error") or "SUPPORT_UNAVAILABLE")
                status = 404 if error in {"SUPPORT_MESSAGE_NOT_FOUND", "MESSAGE_ID_INVALID"} else 401 if error == "AUTHENTICATED_USER_REQUIRED" else 503 if error in {"DATABASE_UNAVAILABLE", "SUPPORT_UNAVAILABLE"} else 400
                self._send_json(status, result)
                return
            if action == "send":
                if user_id == expected_admin_id:
                    self._send_json(403, {"success": False, "error": "ADMIN_CANNOT_OPEN_SUPPORT_TICKET"})
                    return
                result = send_premium_support_message(user_id, body.get("message"), body.get("language"), body.get("attachment_data"), body.get("attachment_mime"))
                if result.get("success") is True:
                    self._send_json(200, result)
                    return
                error = _text(result.get("error") or "SUPPORT_UNAVAILABLE")
                status = 429 if error == "COOLDOWN_ACTIVE" else 403 if error == "PREMIUM_REQUIRED" else 401 if error == "AUTHENTICATED_USER_REQUIRED" else 503 if error in {"DATABASE_UNAVAILABLE", "SUPPORT_UNAVAILABLE", "SUPPORT_STATUS_UNAVAILABLE"} else 400
                self._send_json(status, result)
                return
            if action == "reply":
                if user_id != expected_admin_id:
                    self._send_json(403, {"success": False, "error": "SUPERADMIN_REQUIRED"})
                    return
                result = reply_premium_support_message(body.get("message_id"), body.get("reply"), user_id)
                if result.get("success") is True:
                    self._send_json(200, result)
                    return
                error = _text(result.get("error") or "SUPPORT_UNAVAILABLE")
                status = 403 if error == "SUPERADMIN_REQUIRED" else 404 if error == "SUPPORT_MESSAGE_NOT_FOUND" else 409 if error == "SUPPORT_MESSAGE_ALREADY_REPLIED" else 503 if error in {"DATABASE_UNAVAILABLE", "SUPPORT_UNAVAILABLE"} else 400
                self._send_json(status, result)
                return
            self._send_json(400, {"success": False, "error": "INVALID_SUPPORT_ACTION"})
            return

        if parsed_path == "/api/subscription/test-activate":
            if not self._service_authorized():
                self.close_connection = True
                self._send_json(401, {"success": False, "error": "SERVICE_AUTH_REQUIRED"})
                return
            user_id = _text(self.headers.get("X-April-User-Id"))
            if not user_id:
                self._send_json(400, {"success": False, "error": "USER_ID_REQUIRED"})
                return
            # Consume and validate the small bridge body; identity and access are
            # derived only from trusted headers + the authenticated DB row.
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 0 or length > 64 * 1024:
                    self.close_connection = True
                    self._send_json(413, {"success": False, "error": "REQUEST_BODY_TOO_LARGE"})
                    return
                raw = self.rfile.read(length)
                body = json.loads(raw.decode("utf-8") or "{}") if raw else {}
                if not isinstance(body, dict):
                    self._send_json(400, {"success": False, "error": "INVALID_REQUEST"})
                    return
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                self._send_json(400, {"success": False, "error": "INVALID_JSON"})
                return
            result = activate_test_premium(user_id, hours=24)
            if result.get("success"):
                # Confirm that the committed entitlement is immediately visible to
                # the exact same plan resolver used by /api/v1/chat. This verifies
                # that the next message is routed to Premium_executor, not Free.
                active_plan = _text(get_user_plan(user_id)).lower() or "free"
                if active_plan != "premium":
                    _apr_timing_log(
                        "subscription_test_activation_plan_verification_failed",
                        user_key=_apr_diag_ref(user_id),
                        active_plan=active_plan,
                    )
                    self._send_json(503, {"success": False, "error": "PREMIUM_ENTITLEMENT_NOT_VISIBLE"})
                    return
                _apr_timing_log(
                    "subscription_test_activation_success",
                    user_key=_apr_diag_ref(user_id),
                    premium_key=_apr_diag_ref(result.get("premium_id")),
                    active_plan=active_plan,
                    processor="Premium_executor",
                    remaining_seconds=result.get("remaining_seconds", 0),
                )
                self._send_json(200, result)
                return
            error = _text(result.get("error") or "PREMIUM_ACTIVATION_FAILED")
            status_code = 503 if error in {
                "DATABASE_UNAVAILABLE", "SUBSCRIPTION_STATUS_UNAVAILABLE", "PREMIUM_SCHEMA_MIGRATION_REQUIRED"
            } else 401 if error == "AUTHENTICATED_USER_REQUIRED" else 403 if error in {
                "PREMIUM_TEST_MODE_DISABLED", "PREMIUM_TEST_ALLOWLIST_EMPTY", "PREMIUM_TEST_USER_NOT_ALLOWED"
            } else 400
            _apr_timing_log("subscription_test_activation_failed", user_key=_apr_diag_ref(user_id), error=error)
            self._send_json(status_code, result)
            return

        # April account deletion bridge. This endpoint is server-to-server only:
        # the Web layer validates the current NextAuth session and forwards the
        # session's April ID with the private service token. No Google APIs are
        # called; only April's own PostgreSQL records are deleted.
        if parsed_path == "/api/account/delete":
            if not self._service_authorized():
                self.close_connection = True
                self._send_json(401, {"success": False, "error": "SERVICE_AUTH_REQUIRED"})
                return

            user_id = _text(self.headers.get("X-April-User-Id"))
            if not user_id:
                self._send_json(400, {"success": False, "error": "USER_ID_REQUIRED"})
                return
            if not _text(os.getenv("DATABASE_URL")):
                self._send_json(503, {"success": False, "error": "DATABASE_UNAVAILABLE"})
                return

            # Consume a small JSON body so the HTTP/1.1 connection stays in sync.
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 0 or length > 4096:
                    self.close_connection = True
                    self._send_json(413, {"success": False, "error": "REQUEST_BODY_TOO_LARGE"})
                    return
                raw = self.rfile.read(length) if length else b""
                body = json.loads(raw.decode("utf-8") or "{}") if raw else {}
                if not isinstance(body, dict):
                    self._send_json(400, {"success": False, "error": "INVALID_REQUEST"})
                    return
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                self._send_json(400, {"success": False, "error": "INVALID_JSON"})
                return

            result = delete_april_account(user_id)
            if result.get("success") is True:
                _apr_timing_log(
                    "account_delete_success",
                    user_key=_apr_diag_ref(user_id),
                    deleted_user_rows=int(result.get("deleted_user_rows") or 0),
                    deleted_dialogue_rows=int(result.get("deleted_dialogue_rows") or 0),
                    deleted_payment_rows=int(result.get("deleted_payment_rows") or 0),
                    checked_asset_owner_ids=int(result.get("checked_asset_owner_ids") or 0),
                    purged_dialogue_cache_entries=int(result.get("purged_dialogue_cache_entries") or 0),
                    external_identity="google_untouched",
                )
                self._send_json(200, {"success": True, "deleted": True})
                return

            error = _text(result.get("error") or "ACCOUNT_DELETE_FAILED")
            status_code = 503 if error in {"DATABASE_UNAVAILABLE", "ACCOUNT_DELETE_FAILED", "ACCOUNT_ASSETS_DELETE_FAILED"} else 404 if error == "ACCOUNT_NOT_FOUND" else 401 if error == "AUTHENTICATED_USER_REQUIRED" else 400
            _apr_timing_log("account_delete_failed", user_key=_apr_diag_ref(user_id), error=error)
            self._send_json(status_code, {"success": False, "error": error})
            return

        # Existing April Web authentication bridge. Keep account identity in the
        # canonical users table; never derive an April user ID from email.
        if self.path == "/api/users/find-or-create":
            if not self._service_authorized():
                self.close_connection = True
                self._send_json(401, {"success": False, "error": "REGISTRY_AUTH_REQUIRED"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 0 or length > 64 * 1024:
                    self._send_json(413, {"success": False, "error": "REQUEST_BODY_TOO_LARGE"})
                    return
                raw = self.rfile.read(length)
                try:
                    body = json.loads(raw.decode("utf-8") or "{}")
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self._send_json(400, {"success": False, "error": "INVALID_JSON"})
                    return
                if not isinstance(body, dict):
                    self._send_json(400, {"success": False, "error": "INVALID_REQUEST"})
                    return

                email = _text(body.get("email")).lower()
                provider = _text(body.get("provider")).lower()
                provider_user_id = _text(body.get("provider_user_id"))
                name = _text(body.get("name"))[:200]
                if (
                    body.get("email_verified") is not True
                    or not email or len(email) > 320 or "@" not in email
                    or provider != "google"
                    or not provider_user_id or len(provider_user_id) > 256
                ):
                    self._send_json(400, {"success": False, "error": "INVALID_VERIFIED_GOOGLE_IDENTITY"})
                    return

                user = find_or_create_user(
                    email=email,
                    name=name,
                    provider=provider,
                    provider_user_id=provider_user_id,
                )
                if not user:
                    self._send_json(503, {"success": False, "error": "USER_REGISTRY_UNAVAILABLE"})
                    return

                # The canonical April ID is also users.user_id in this schema.
                # Emit both camelCase and database field names for current clients.
                april_id = _text(user.get("april_id") or user.get("aprilUserId") or user.get("aprilId") or user.get("user_id"))
                user_id = _text(user.get("user_id") or april_id)
                if not april_id or not user_id:
                    self._send_json(500, {"success": False, "error": "USER_ID_NOT_AVAILABLE"})
                    return
                # Session/UI values are only a mirror of the database entitlement.
                # Expired or unknown plan values are always reported as Free. Keep
                # the separate Premium ID and millisecond expiry in both naming
                # conventions because NextAuth consumes this registry payload.
                active_plan = get_user_plan(user_id)
                premium_id = _text(user.get("premium_id")) or None
                until_seconds = float(user.get("subscription_until") or 0)
                subscription_until = (
                    int(until_seconds * 1000)
                    if active_plan in {"lite", "premium"} and until_seconds > 0
                    else None
                )
                payload_user = {
                    "user_id": user_id,
                    "april_id": april_id,
                    "aprilId": april_id,
                    "aprilUserId": april_id,
                    "email": _text(user.get("email") or email),
                    "name": _text(user.get("name") or name),
                    "provider": _text(user.get("provider") or provider),
                    "plan": active_plan,
                    "currentPlan": active_plan,
                    "premium_id": premium_id,
                    "premiumId": premium_id,
                    "subscription_until": subscription_until,
                    "subscriptionUntil": subscription_until,
                }
                self._send_json(200, {"success": True, "user": payload_user})
            except Exception as exc:
                print(f"[APRIL] USER_REGISTRY_ERROR: {type(exc).__name__}", flush=True)
                self._send_json(500, {"success": False, "error": "USER_REGISTRY_FAILED"})
            return

        if self.path == "/frontend_log":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 0 or length > 64 * 1024:
                    # Do not reuse a keep-alive connection while an oversized body
                    # remains unread; otherwise body bytes can be parsed as a new request.
                    self.close_connection = True
                    self._send_json(413, {"success": False, "error": "LOG_BODY_TOO_LARGE"})
                    return
                raw_log = self.rfile.read(length)
                try:
                    entry = json.loads(raw_log.decode("utf-8") or "{}")
                except Exception:
                    entry = {}
                if isinstance(entry, dict):
                    safe_entry = {
                        key: str(entry.get(key) or "")[:300]
                        for key in ("room", "stage", "status", "error_code", "route", "flow_id", "message_id")
                        if entry.get(key) is not None
                    }
                    print("[APRIL_FRONTEND] " + json.dumps(safe_entry, ensure_ascii=False), flush=True)
                self._send_json(204, {})
            except Exception as exc:
                print(f"[APRIL_FRONTEND] LOG ERROR: {type(exc).__name__}", flush=True)
                self._send_json(400, {"success": False, "error": "INVALID_FRONTEND_LOG"})
            return

        if self.path != CANONICAL_CHAT_ROUTE:
            self._send_json(404, {"success": False, "error": "NOT_FOUND", "canonical_route": CANONICAL_CHAT_ROUTE})
            return
        if not self._service_authorized():
            # The chat request body has not been consumed yet. Close this
            # keep-alive connection after replying so JSON bytes cannot be
            # misinterpreted as a new HTTP request line (spurious 400 errors).
            self.close_connection = True
            self._send_json(401, {"success": False, "error": "SERVICE_AUTH_REQUIRED", "canonical_route": CANONICAL_CHAT_ROUTE})
            return
        supplied_april_id = _text(self.headers.get("X-April-User-Id"))
        if not supplied_april_id:
            self._send_json(401, {"success": False, "error": "AUTHENTICATION_REQUIRED", "canonical_route": CANONICAL_CHAT_ROUTE})
            return
        if not is_authenticated_user(supplied_april_id):
            self._send_json(401, {"success": False, "error": "AUTHENTICATED_USER_REQUIRED", "canonical_route": CANONICAL_CHAT_ROUTE})
            return
        # `april_id` is the public account identifier; dialogue, plan and payment
        # tables are keyed by `users.user_id`. Normalize once at the only chat
        # ingress so the Free/Premium router and all linked stores share one key.
        canonical_user_id = resolve_user_id(supplied_april_id)
        if not canonical_user_id:
            self._send_json(503, {"success": False, "error": "USER_ID_RESOLUTION_FAILED", "canonical_route": CANONICAL_CHAT_ROUTE})
            return
        # Existing chat traffic is the lightweight activity signal; no new route or table is required.
        try:
            touch_user_activity(canonical_user_id)
        except Exception:
            pass
        http_started = time.perf_counter()
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > MAX_BODY_BYTES:
                self._send_json(413, {"success": False, "error": "REQUEST_BODY_TOO_LARGE", "canonical_route": CANONICAL_CHAT_ROUTE})
                return
            raw = self.rfile.read(length)
            content_type = self.headers.get("Content-Type", "application/json")
            parse_started = time.perf_counter()
            if content_type.lower().startswith("multipart/form-data"):
                data, attachments = parse_multipart_payload(raw, content_type=content_type)
            else:
                data, attachments = parse_json_payload(raw)
            if not isinstance(data, dict):
                self._send_json(400, {"success": False, "error": "INVALID_REQUEST", "canonical_route": CANONICAL_CHAT_ROUTE})
                return
            # Account ownership comes only from the authenticated Web session,
            # never from browser-controlled JSON or multipart form fields.
            data = dict(data)
            data["user_id"] = canonical_user_id
            data["april_id"] = supplied_april_id
            _apr_timing_log("http_request_parse", parse_started, body_bytes=length,
                content_type=content_type.split(";", 1)[0], attachment_count=len(attachments or []),
                input_chars=len(_text(data.get("text") or data.get("message") or data.get("content"))) if isinstance(data, dict) else 0)
            if _voice_attachment(attachments) is not None:
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
                self.send_header("Transfer-Encoding", "chunked")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()

                client_disconnected = False

                def write_event(event: dict[str, Any]) -> bool:
                    nonlocal client_disconnected
                    if client_disconnected:
                        return False
                    chunk = (json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
                    try:
                        self.wfile.write(f"{len(chunk):X}\r\n".encode("ascii"))
                        self.wfile.write(chunk)
                        self.wfile.write(b"\r\n")
                        self.wfile.flush()
                        return True
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError):
                        client_disconnected = True
                        print("[APRIL_VOICE] stage=client_disconnected during_ndjson_stream=true", flush=True)
                        return False

                try:
                    _handle_voice_stream(data, attachments, write_event)
                except Exception as exc:
                    if not client_disconnected:
                        traceback.print_exc()
                        write_event({
                            "type": "answer",
                            "status": 500,
                            "data": {
                                "success": False,
                                "error": _text(str(exc)) or "VOICE_FAILED",
                                "canonical_route": CANONICAL_CHAT_ROUTE,
                            },
                        })
                finally:
                    if not client_disconnected:
                        try:
                            self.wfile.write(b"0\r\n\r\n")
                            self.wfile.flush()
                        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError):
                            client_disconnected = True
                            print("[APRIL_VOICE] stage=client_disconnected while_closing_ndjson=true", flush=True)
                return

            handler_started = time.perf_counter()
            status, payload = _handle_payload(data, attachments)
            _apr_timing_log("http_handler_total", handler_started, http_elapsed_ms=round((time.perf_counter() - http_started) * 1000, 1),
                status=status, answer_chars=len(_text(payload.get("answer"))) if isinstance(payload, dict) else 0)
            send_started = time.perf_counter()
            self._send_json(status, payload)
            _apr_timing_log("http_response_send", send_started, status=status,
                serialized_answer_chars=len(_text(payload.get("answer"))) if isinstance(payload, dict) else 0)
        except Exception as exc:
            traceback.print_exc()
            self._send_json(500, {"success": False, "error": str(exc), "canonical_route": CANONICAL_CHAT_ROUTE})

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[APRIL] {self.address_string()} - {fmt % args}", flush=True)


def create_server() -> ThreadingHTTPServer:
    return ThreadingHTTPServer((HOST, PORT), AprilHandler)


def main() -> None:
    # Processor-side schema bootstrap must complete before the first chat request.
    init_db()
    server = create_server()
    print(f"[APRIL] bot.ru listening on {HOST}:{PORT}; canonical route={CANONICAL_CHAT_ROUTE}", flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
