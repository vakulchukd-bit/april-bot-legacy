"""APRIL canonical WebReal Web gateway.

Canonical route:
    WebReal Web
        -> /api/chat
        -> bot.py (bot.ru translation boundary)
        -> core.executor
        -> State Manager (rolling 12h dialogue)
        -> C_ARTIFACT_CONTRACT (MachineRequest)
        -> provider_router -> OpenAI
        -> core.executor -> C_ARTIFACT_CONTRACT (SceneContract)
        -> bot.py (bot.ru output boundary)
        -> WebReal Web

Only the existing bot.py gateway is used; no botru.py, Flask route, legacy alias,
or restored compatibility module is introduced.
"""
from __future__ import annotations

import asyncio
import json
import os
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from core.executor import execute


HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "10000"))
MAX_BODY_BYTES = int(os.getenv("APRIL_MAX_HTTP_BODY_BYTES", "1048576"))
CANONICAL_CHAT_ROUTE = "/api/v1/chat"
WEB_GATEWAY_ROUTE = "/api/chat"
CANONICAL_ROUTE_VERSION = "april_webreal_botru_scene_v1"


def _text(value: Any) -> str:
    return str(value or "").strip()


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
        "internal_language": "en",
        "display_language": result.get("display_language", "en"),
        "translation": result.get(
            "translation",
            {
                "input_language": result.get("display_language", "en"),
                "internal_language": "en",
                "mode": "provider_internal",
            },
        ),
        "type": "text",
        "content": result.get("content") or answer,
        "answer": answer,
        "summary": result.get("summary", ""),
        "blocks": blocks,
        "render_blocks": blocks,
        "scene_contract": scene,
        "flow_id": result.get("flow_id"),
        "provider_context_authority": "PROCESSOR",
        "web_delivery": {
            "version": CANONICAL_ROUTE_VERSION,
            "transport": "SceneContract",
            "single_visible_stream": True,
            "scene_contract": scene,
            "render_blocks": blocks,
            "route": [
                "WebReal Web /api/chat",
                "bot.py (bot.ru IN)",
                "core.executor",
                "State Manager 12h",
                "C_ARTIFACT_CONTRACT REQUEST",
                "provider_router -> OpenAI",
                "core.executor",
                "C_ARTIFACT_CONTRACT SceneContract",
                "bot.py (bot.ru OUT)",
                "WebReal Web",
            ],
        },
    }


def _error(message: str, status: int = 500) -> tuple[int, dict[str, Any]]:
    return status, {
        "success": False,
        "error": _text(message) or "INTERNAL_ERROR",
        "canonical_route": CANONICAL_CHAT_ROUTE,
    }


def _handle_payload(data: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    uid = _text(data.get("user_id"))
    text = _text(data.get("text") or data.get("message") or data.get("content"))

    if not uid:
        return _error("user_id required", 400)
    if not text:
        return _error("text required", 400)

    try:
        result = asyncio.run(
            execute(
                uid,
                text=text,
                flow_id=_text(data.get("flow_id")),
                conversation_id=_text(data.get("conversation_id")),
                display_language=_text(
                    data.get("language")
                    or data.get("display_language")
                    or "auto"
                ),
            )
        )
        if not isinstance(result, dict):
            return _error("PROCESSOR_INVALID_RESULT", 500)
        return 200, _payload(result)
    except Exception as exc:
        traceback.print_exc()
        return _error(str(exc), 500)


class AprilHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "AprilGateway/2.0"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization, X-Requested-With",
        )
        self.send_header(
            "Access-Control-Allow-Methods",
            "POST, OPTIONS, GET",
        )
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self._send_json(204, {})

    def do_GET(self) -> None:
        self._send_json(
            200,
            {
                "success": True,
                "service": "april-bot",
                "status": "ok",
                "canonical_route": CANONICAL_CHAT_ROUTE,
                "route_version": CANONICAL_ROUTE_VERSION,
            },
        )

    def do_POST(self) -> None:
        if self.path != CANONICAL_CHAT_ROUTE:
            self._send_json(
                404,
                {
                    "success": False,
                    "error": "NOT_FOUND",
                    "route": self.path,
                    "canonical_route": CANONICAL_CHAT_ROUTE,
                },
            )
            return

        try:
            raw_length = self.headers.get("Content-Length", "0")
            length = int(raw_length)
            if length < 0 or length > MAX_BODY_BYTES:
                self._send_json(
                    413,
                    {
                        "success": False,
                        "error": "REQUEST_BODY_TOO_LARGE",
                        "canonical_route": CANONICAL_CHAT_ROUTE,
                    },
                )
                return

            raw = self.rfile.read(length)
            try:
                data = json.loads(raw.decode("utf-8") or "{}")
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(
                    400,
                    {
                        "success": False,
                        "error": "INVALID_JSON",
                        "canonical_route": CANONICAL_CHAT_ROUTE,
                    },
                )
                return

            if not isinstance(data, dict):
                self._send_json(
                    400,
                    {
                        "success": False,
                        "error": "JSON_OBJECT_REQUIRED",
                        "canonical_route": CANONICAL_CHAT_ROUTE,
                    },
                )
                return

            status, payload = _handle_payload(data)
            self._send_json(status, payload)

        except Exception as exc:
            traceback.print_exc()
            self._send_json(
                500,
                {
                    "success": False,
                    "error": str(exc),
                    "canonical_route": CANONICAL_CHAT_ROUTE,
                },
            )

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[APRIL] {self.address_string()} - {fmt % args}", flush=True)


def create_server() -> ThreadingHTTPServer:
    return ThreadingHTTPServer((HOST, PORT), AprilHandler)


def main() -> None:
    server = create_server()
    print(
        f"[APRIL] HTTP gateway listening on {HOST}:{PORT}; "
        f"canonical route={CANONICAL_CHAT_ROUTE}",
        flush=True,
    )
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
