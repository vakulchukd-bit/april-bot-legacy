"""APRIL canonical bot.ru gateway.

There is exactly one public chat route: POST /api/v1/chat.
Bot.ru owns the transport/input normalization boundary. It accepts text, voice,
screenshot/image and file content in the same authenticated envelope and passes
the normalized envelope to Exkrutor.
No separate botru_transport/translation route or file exists.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from blocks.input_reader import parse_json_payload, parse_multipart_payload
from blocks.voice_reader import transcribe_voice_bytes
from core.executor import execute
from storage import init_db

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "10000"))
MAX_BODY_BYTES = int(os.getenv("APRIL_MAX_HTTP_BODY_BYTES", str(25 * 1024 * 1024)))
CANONICAL_CHAT_ROUTE = "/api/v1/chat"
CANONICAL_ROUTE_VERSION = "april_web_botru_exkrutor_v1"
INPUT_NORMALIZATION_VERSION = "botru_input_normalization_v2"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _detect_language(text: str, requested: str = "") -> str:
    requested = _text(requested).lower()
    if requested and requested not in {"auto", "default"}:
        return requested
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
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return semantic text, visual inputs, safe attachment metadata and file inputs."""
    extra_text: list[str] = []
    visual: list[dict[str, Any]] = []
    meta: list[dict[str, Any]] = []
    provider_files: list[dict[str, Any]] = []

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
                extra_text.append(transcript)

        elif kind == "text_file":
            text = _text(item.get("text"))
            if text:
                extra_text.append(f"FILE {filename}:\n{text}")

        elif kind == "image":
            uri = _text(item.get("data_uri"))
            if uri:
                visual.append({
                    "type": "input_image",
                    "image_url": uri,
                    "filename": filename,
                    "source_type": item.get("source_type", "image"),
                    "mime_type": content_type,
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
                })

    return "\n\n".join(extra_text), visual, meta, provider_files


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    scene = result.get("scene_contract") or {}
    blocks = result.get("render_blocks") or scene.get("render_blocks") or []
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
    identity = _canonical_identity(data)
    uid = identity["user_id"]
    original = _text(data.get("text") or data.get("message") or data.get("content"))
    conversation_id = identity["conversation_id"]
    dialog_id = identity["dialog_id"]
    message_id = identity["message_id"]
    if not uid:
        return _error("user_id required", 400)
    if not conversation_id and not dialog_id:
        return _error("conversation_id or dialog_id required", 400)

    attachments = attachments or []
    try:
        extra_text, visual_context, attachment_meta, file_inputs = _prepare_attachments(
            data, attachments, voice_transcript=voice_transcript
        )
        if extra_text:
            original = (original + "\n\n" + extra_text).strip()

        if not original and not visual_context and not file_inputs:
            if attachment_meta:
                return _error("file is not readable by the Provider", 400)
            return _error("text, voice, image or file required", 400)

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
            translation=translation,
        ))
        return 200, _payload(result)
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

    # Voice block -> existing Provider transcription.
    transcript = _transcribe_attachment(voice)
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
    status, payload = _handle_payload(
        routed_data,
        attachments,
        voice_transcript=transcript,
    )
    write_event({"type": "answer", "status": status, "data": payload})


class AprilHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "AprilBotRU/3.0"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
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
        if self.path != CANONICAL_CHAT_ROUTE:
            self._send_json(404, {"success": False, "error": "NOT_FOUND", "canonical_route": CANONICAL_CHAT_ROUTE})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > MAX_BODY_BYTES:
                self._send_json(413, {"success": False, "error": "REQUEST_BODY_TOO_LARGE", "canonical_route": CANONICAL_CHAT_ROUTE})
                return
            raw = self.rfile.read(length)
            content_type = self.headers.get("Content-Type", "application/json")
            if content_type.lower().startswith("multipart/form-data"):
                data, attachments = parse_multipart_payload(raw, content_type=content_type)
            else:
                data, attachments = parse_json_payload(raw)
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

            status, payload = _handle_payload(data, attachments)
            self._send_json(status, payload)
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
