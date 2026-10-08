"""Canonical identity normalization for the single April /api/v1/chat route."""
from __future__ import annotations
import uuid
from typing import Any

def _text(value: Any) -> str:
    return str(value or "").strip()

def new_dialog_id() -> str:
    return f"dlg_{uuid.uuid4().hex}"

def new_message_id() -> str:
    return f"msg_{uuid.uuid4().hex}"

def resolve_dialog_identity(payload: dict[str, Any], *, user_id: str, flow_id: str = "") -> dict[str, str]:
    uid = _text(user_id)
    if not uid:
        raise ValueError("USER_ID_REQUIRED")
    dialog_id = _text(payload.get("dialog_id") or payload.get("conversation_id") or payload.get("dialogue_id"))
    conversation_id = _text(payload.get("conversation_id") or dialog_id)
    if not dialog_id:
        dialog_id = new_dialog_id()
    if not conversation_id:
        conversation_id = dialog_id
    return {
        "user_id": uid,
        "dialog_id": dialog_id,
        "conversation_id": conversation_id,
        "message_id": _text(payload.get("message_id")) or new_message_id(),
        "flow_id": _text(flow_id or payload.get("flow_id")) or f"flow_{uuid.uuid4().hex}",
    }
