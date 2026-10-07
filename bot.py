"""APRIL HTTP gateway — dependency-light production entrypoint.

This file intentionally does not import Flask.  The previous deployment crashed
before April started because Railway launched app.py and Python reported
ModuleNotFoundError: flask.  The current April ZIP already contains bot.py, so
this gateway keeps the API routes in bot.py and uses Python's standard library
HTTP server.

API:
  POST /chat
  POST /api/v1/chat

JSON body:
  {"user_id":"...", "text":"...", "language":"...", "flow_id":"...",
   "conversation_id":"..."}
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


def _text(value: Any) -> str:
    return str(value or "").strip()


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    scene = result.get("scene_contract") or {}
    blocks = result.get("render_blocks") or scene.get("render_blocks") or []
    return {
        "success": True,
        "canonical_route": "/api/v1/chat",
        "single_route": True,
        "internal_language": "en",
        "display_language": result.get("display_language", "en"),
        "type": "text",
        "content": result.get("content", ""),
        "answer": result.get("answer", ""),
        "summary": result.get("summary", ""),
        "blocks": blocks,
        "render_blocks": blocks,
        "scene_contract": scene,
        "flow_id": result.get("flow_id"),
        "provider_context_authority": "PROCESSOR",
        "web_delivery": {
            "version": "april_web_scene_signal_v1",
            "transport": "SceneContract",
            "single_visible_stream": True,
            "scene_contract": scene,
            "render_blocks": blocks,
        },
    }


def _error(message: str, status: int = 500) -> tuple[int, dict[str, Any]]:
    return status, {
        "success": False,
        "error": _text(message) or "INTERNAL_ERROR",
    }


def _handle_payload(data: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    uid = _text(data.get("user_id"))
    text = _text(data.get("text") or data.get("message"))

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
                    or "en"
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
    server_version = "AprilGateway/1.0"

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
        # Railway health checks commonly use GET /.
        self._send_json(
            200,
            {
                "success": True,
                "service": "april-bot",
                "status": "ok",
            },
        )

    def do_POST(self) -> None:
        if self.path not in {"/chat", "/api/v1/chat"}:
            self._send_json(
                404,
                {
                    "success": False,
                    "error": "NOT_FOUND",
                    "route": self.path,
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
                    },
                )
                return

            if not isinstance(data, dict):
                self._send_json(
                    400,
                    {
                        "success": False,
                        "error": "JSON_OBJECT_REQUIRED",
                    },
                )
                return

            status, payload = _handle_payload(data)
            self._send_json(status, payload)

        except Exception as exc:
            traceback.print_exc()
            self._send_json(500, {"success": False, "error": str(exc)})

    def log_message(self, fmt: str, *args: Any) -> None:
        # Keep Railway logs useful without Flask's access-log formatting.
        print(f"[APRIL] {self.address_string()} - {fmt % args}", flush=True)


def create_server() -> ThreadingHTTPServer:
    return ThreadingHTTPServer((HOST, PORT), AprilHandler)


def main() -> None:
    server = create_server()
    print(f"[APRIL] HTTP gateway listening on {HOST}:{PORT}", flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
