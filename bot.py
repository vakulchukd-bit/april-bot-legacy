"""APRIL web gateway using only modules present in the current ZIP."""
from __future__ import annotations

import asyncio
import os
import traceback
from flask import Flask, jsonify, request
from flask_cors import CORS

from core.executor import execute

app = Flask(__name__)
CORS(app)


def _text(value):
    return str(value or "").strip()


def _payload(result: dict) -> dict:
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


def _handle():
    data = request.get_json(silent=True) or {}
    uid = _text(data.get("user_id"))
    text = _text(data.get("text") or data.get("message"))
    if not uid:
        return jsonify({"success": False, "error": "user_id required"}), 400
    if not text:
        return jsonify({"success": False, "error": "text required"}), 400

    result = asyncio.run(execute(
        uid,
        text=text,
        flow_id=_text(data.get("flow_id")),
        conversation_id=_text(data.get("conversation_id")),
        display_language=_text(data.get("language") or data.get("display_language") or "en"),
    ))
    return jsonify(_payload(result))


@app.post("/chat")
def chat():
    try:
        return _handle()
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(exc)}), 500


@app.post("/api/v1/chat")
def api_chat():
    try:
        return _handle()
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")), debug=False, use_reloader=False)
