"""Canonical dialog identity helpers.

The Web is the authority for authenticated identity and should send dialog_id,
conversation_id, message_id and flow_id. The backend only normalizes aliases and
creates a fallback dialog_id when an older client omitted it.
"""
from __future__ import annotations

import uuid
from typing import Any


def _text(value: Any) -> str:
    return str(value or "").strip()


def new_dialog_id() -> str:
    return f"dlg_{uuid.uuid4().hex}"


def resolve_dialog_identity(
    payload: dict[str, Any],
    *,
    user_id: str,
    flow_id: str = "",
) -> dict[str, str]:
    dialog_id = _text(
        payload.get("dialog_id")
        or payload.get("conversation_id")
        or payload.get("dialogue_id")
    )
    conversation_id = _text(
        payload.get("conversation_id") or dialog_id
    )

    # Fallback is compatibility-only. The Web remains the preferred source.
    if not dialog_id:
        dialog_id = new_dialog_id()
    if not conversation_id:
        conversation_id = dialog_id

    return {
        "user_id": _text(user_id),
        "dialog_id": dialog_id,
        "conversation_id": conversation_id,
        "message_id": _text(payload.get("message_id")),
        "flow_id": _text(flow_id or payload.get("flow_id")),
    }
