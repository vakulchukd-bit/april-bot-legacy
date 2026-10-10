"""APRIL canonical bot.ru gateway.

There is exactly one public chat route: POST /api/v1/chat.
Bot.ru owns the transport/input normalization boundary. It accepts text, voice,
screenshot/image and file content in the same authenticated envelope and passes
the normalized envelope to Exkrutor.
No separate botru_transport/translation route or file exists.
"""
from __future__ import annotations

import asyncio
import hashlib
import base64
import json
import os
import re
import traceback
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from blocks.input_reader import parse_json_payload, parse_multipart_payload
from blocks.voice_reader import transcribe_voice_bytes
from core.executor import execute
from storage import init_db, load_dialogue_pairs

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
    original = _text(data.get("text") or data.get("message") or data.get("content"))
    _apr_timing_log("request_identity", identity_started, user_key=_apr_diag_ref(uid),
        dialog_key=_apr_diag_ref(identity.get("dialog_id")), message_key=_apr_diag_ref(identity.get("message_id")),
        flow_key=_apr_diag_ref(identity.get("flow_id")), input_chars=len(original), attachment_count=len(attachments or []))
    conversation_id = identity["conversation_id"]
    dialog_id = identity["dialog_id"]
    message_id = identity["message_id"]
    if not uid:
        return _error("user_id required", 400)
    if not conversation_id and not dialog_id:
        return _error("conversation_id or dialog_id required", 400)

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
                    prior_pairs = load_dialogue_pairs(uid, limit=24)
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

        # Attachments are passed directly through this request's unified route.
        # Persistent binary sidecars have been removed; dialogue continuity is
        # sourced only from dialogue_memory.
        _apr_timing_log(
            "input_asset_sidecar_skipped", user_key=_apr_diag_ref(uid),
            current_request_assets=len(attachments or []),
            persistence_disabled=True, source="dialogue_memory_only",
        )

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

        executor_started = time.perf_counter()
        result = asyncio.run(execute(
            uid,
            text=original,
            internal_text=internal_text,
            display_language=language,
            flow_id=_text(data.get("flow_id")),
            conversation_id=conversation_id or dialog_id,
            dialog_id=dialog_id,
            message_id=message_id,
            interpretation_id=_text(data.get("interpretation_id")),
            visual_context=visual_context,
            attachments=attachment_meta,
            file_inputs=file_inputs,
            file_contents=text_file_contents,
            translation=translation,
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
    answer_started = time.perf_counter()
    status, payload = _handle_payload(
        routed_data,
        attachments,
        voice_transcript=transcript,
    )
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


class AprilHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "AprilBotRU/3.0"

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
        self._send_json(200, {"success": True, "service": "april-bot", "canonical_route": CANONICAL_CHAT_ROUTE, "route_version": CANONICAL_ROUTE_VERSION})

    def do_POST(self) -> None:
        if self.path == "/frontend_log":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 0 or length > 64 * 1024:
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
            _apr_timing_log("http_request_parse", parse_started, body_bytes=length,
                content_type=content_type.split(";", 1)[0], attachment_count=len(attachments or []),
                input_chars=len(_text(data.get("text") or data.get("message") or data.get("content"))) if isinstance(data, dict) else 0)
            if _voice_attachment(attachments) is not None:
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
                self.send_header("Transfer-Encoding", "chunked")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
                self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()

                def write_event(event: dict[str, Any]) -> None:
                    chunk = (json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
                    self.wfile.write(f"{len(chunk):X}\r\n".encode("ascii"))
                    self.wfile.write(chunk)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()

                try:
                    _handle_voice_stream(data, attachments, write_event)
                except Exception as exc:
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
                    self.wfile.write(b"0\r\n\r\n")
                    self.wfile.flush()
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
