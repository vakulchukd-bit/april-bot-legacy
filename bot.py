"""APRIL canonical bot.ru gateway.

There is exactly one public chat route: POST /api/v1/chat.
Bot.ru owns the input translation boundary. It accepts text, voice, image/
screenshot and file content in the same authenticated envelope, normalizes the
user request to internal English, and passes the envelope to Exkrutor.
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
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from blocks.input_reader import parse_json_payload, parse_multipart_payload
from blocks.voice_reader import validate_voice
from core.executor import execute
from blocks.provider_router import transcribe_voice

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "10000"))
MAX_BODY_BYTES = int(os.getenv("APRIL_MAX_HTTP_BODY_BYTES", str(25 * 1024 * 1024)))
CANONICAL_CHAT_ROUTE = "/api/v1/chat"
CANONICAL_ROUTE_VERSION = "april_web_botru_exkrutor_v1"
TRANSLATION_VERSION = "botru_embedded_translation_v1"
TRANSLATOR_MODEL = os.getenv("APRIL_TRANSLATOR_MODEL", os.getenv("APRIL_OPENAI_MODEL", "gpt-5.6-luna"))


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


def _openai_translate_to_en(text: str) -> str:
    """Translate/normalize one user request inside bot.ru.

    This is the only translation boundary. It returns concise English semantic
    text; it does not answer the user and does not create another chat route.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY_NOT_CONFIGURED")
    payload = {
        "model": TRANSLATOR_MODEL,
        "input": [
            {
                "role": "system",
                "content": (
                    "You are April bot.ru input translator. Convert the user's request "
                    "from any language into concise, faithful English semantic text. "
                    "Do not answer it. Preserve names, numbers, code, URLs, file names "
                    "and explicit visual requirements. Return JSON only: "
                    '{"text_en":"..."}'
                ),
            },
            {"role": "user", "content": text},
        ],
        "max_output_tokens": 900,
    }
    req = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=90) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"BOTRU_TRANSLATION_HTTP_{exc.code}: {detail[:500]}") from exc
    except URLError as exc:
        raise RuntimeError(f"BOTRU_TRANSLATION_NETWORK_ERROR: {exc.reason}") from exc

    data = json.loads(raw)
    output = _text(data.get("output_text"))
    if not output:
        chunks: list[str] = []
        for item in data.get("output") or []:
            for content in item.get("content") or []:
                if isinstance(content, dict) and isinstance(content.get("text"), str):
                    chunks.append(content["text"])
        output = "\n".join(chunks).strip()
    try:
        parsed = json.loads(output)
        translated = _text(parsed.get("text_en"))
    except Exception:
        translated = output.strip().strip("`")
    if not translated:
        raise RuntimeError("BOTRU_TRANSLATION_EMPTY")
    return translated


def _translate_input(text: str, language: str) -> tuple[str, dict[str, Any]]:
    original = _text(text)
    if not original:
        return "", {
            "version": TRANSLATION_VERSION,
            "source_language": language,
            "internal_language": "en",
            "translated": False,
        }
    if language == "en":
        return original, {
            "version": TRANSLATION_VERSION,
            "source_language": "en",
            "internal_language": "en",
            "translated": False,
            "stage": "bot.ru",
        }
    translated = _openai_translate_to_en(original)
    return translated, {
        "version": TRANSLATION_VERSION,
        "source_language": language,
        "internal_language": "en",
        "translated": True,
        "stage": "bot.ru",
    }


def _decode_inline_file(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    raw = _text(value)
    if raw.startswith("data:") and "," in raw:
        raw = raw.split(",", 1)[1]
    return base64.b64decode(raw) if raw else b""


def _prepare_attachments(data: dict[str, Any], attachments: list[Any]) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    """Return extra text, visual inputs and normalized attachment metadata."""
    extra_text: list[str] = []
    visual: list[dict[str, Any]] = []
    meta: list[dict[str, Any]] = []

    for att in attachments:
        item = getattr(att, "metadata", {}) or {}
        kind = str(getattr(att, "kind", "file") or "file")
        filename = _text(getattr(att, "filename", "file"))
        meta.append({
            "filename": filename,
            "content_type": _text(getattr(att, "content_type", "")),
            "kind": kind,
            "size_bytes": int(getattr(att, "size_bytes", 0) or 0),
        })
        if kind == "voice":
            meta[-1]["kind"] = "voice"
            raw_voice = getattr(att, "data", b"") or item.get("data") or b""
            if raw_voice:
                suffix = os.path.splitext(filename)[1] or ".webm"
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                try:
                    tmp.write(raw_voice)
                    tmp.close()
                    transcript = asyncio.run(transcribe_voice(tmp.name))
                finally:
                    try:
                        os.unlink(tmp.name)
                    except OSError:
                        pass
                if transcript:
                    extra_text.append(f"VOICE {filename}:\n{transcript}")
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
                })
    return "\n\n".join(extra_text), visual, meta


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


def _handle_payload(data: dict[str, Any], attachments: list[Any] | None = None) -> tuple[int, dict[str, Any]]:
    uid = _text(data.get("user_id") or data.get("april_id"))
    original = _text(data.get("text") or data.get("message") or data.get("content"))
    conversation_id = _text(data.get("conversation_id"))
    dialog_id = _text(data.get("dialog_id") or conversation_id)
    message_id = _text(data.get("message_id")) or f"msg_{uuid.uuid4().hex}"
    if not uid:
        return _error("user_id required", 400)
    if not conversation_id and not dialog_id:
        return _error("conversation_id or dialog_id required", 400)

    attachments = attachments or []
    try:
        extra_text, visual_context, attachment_meta = _prepare_attachments(data, attachments)
        if extra_text:
            original = (original + "\n\n" + extra_text).strip()

        if not original and not visual_context:
            return _error("text, voice, image or file required", 400)

        language = _detect_language(original, data.get("language") or data.get("display_language"))
        internal_text, translation = _translate_input(original, language) if original else ("", {
            "version": TRANSLATION_VERSION,
            "source_language": language,
            "internal_language": "en",
            "translated": False,
            "stage": "bot.ru",
        })

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
            translation=translation,
        ))
        return 200, _payload(result)
    except Exception as exc:
        traceback.print_exc()
        return _error(str(exc), 500)


def _error(message: str, status: int = 500) -> tuple[int, dict[str, Any]]:
    return status, {"success": False, "error": _text(message) or "INTERNAL_ERROR", "canonical_route": CANONICAL_CHAT_ROUTE}


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
    server = create_server()
    print(f"[APRIL] bot.ru listening on {HOST}:{PORT}; canonical route={CANONICAL_CHAT_ROUTE}", flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
