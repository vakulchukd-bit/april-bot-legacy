"""APRIL BotRU web-facing gateway.

Web is not modified by this package. This backend keeps the canonical /chat and
/api/v1/chat routes and returns the same SceneContract-based response shape.
"""
from __future__ import annotations
import asyncio, json, os, traceback
from flask import Flask, jsonify, request
from flask_cors import CORS

from bot_ru import process_request
from blocks.state_manager import initialize

app=Flask(__name__)
CORS(app)
initialize()

BOT_ROUTER_ROLE="BOT_RU_MULTILINGUAL_GATEWAY"
BOT_ROUTER_PROVIDER_CALLS="SINGLE_INTERNAL_PROVIDER_ROUTE_PLUS_TRANSLATION_GATEWAY"

def _text(v):
    return str(v or "").strip()

def _payload(result):
    scene=result.get("scene_contract") or {}
    return {
        "success":True,
        "canonical_route":"/api/v1/chat",
        "single_route":True,
        "router_role":BOT_ROUTER_ROLE,
        "internal_language":"en",
        "display_language":result.get("display_language","en"),
        "type":"text",
        "content":result.get("content",""),
        "answer":result.get("answer",""),
        "summary":result.get("summary",""),
        "blocks":result.get("render_blocks") or scene.get("render_blocks") or [],
        "render_blocks":result.get("render_blocks") or scene.get("render_blocks") or [],
        "scene_contract":scene,
        "flow_id":result.get("flow_id"),
        "provider_context_authority":"INTERPRETATION",
        "gateway_transport":scene,
        "web_delivery":{
            "version":"april_web_scene_signal_v1",
            "transport":"SceneContract",
            "single_visible_stream":True,
            "scene_contract":scene,
            "render_blocks":result.get("render_blocks") or scene.get("render_blocks") or [],
        },
    }

def _handle():
    data=request.get_json(silent=True) or {}
    uid=_text(data.get("user_id"))
    text=_text(data.get("text") or data.get("message"))
    if not uid: return jsonify({"success":False,"error":"user_id required"}),400
    if not text: return jsonify({"success":False,"error":"text required"}),400

    flow_id=_text(data.get("flow_id"))
    conversation_id=_text(data.get("conversation_id"))
    result=asyncio.run(process_request(
        uid,text,flow_id=flow_id,conversation_id=conversation_id
    ))
    return jsonify(_payload(result))

@app.post("/chat")
def chat():
    try: return _handle()
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"success":False,"error":str(exc)}),500

@app.post("/api/v1/chat")
def api_chat():
    try: return _handle()
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"success":False,"error":str(exc)}),500

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","10000")),debug=False,use_reloader=False)
