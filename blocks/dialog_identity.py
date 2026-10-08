"""Canonical identity handling for the single April /api/v1/chat route.

This module does not route requests.  It creates one immutable identity tuple and
provides a processor-side guard for matching the final response to that request.
"""
from __future__ import annotations
import uuid
from typing import Any


def _text(value: Any) -> str:
    return str(value or "").strip()


def new_dialog_id() -> str:
    return f"dlg_{uuid.uuid4().hex}"


def new_message_id() -> str:
    return f"msg_{uuid.uuid4().hex}"


def resolve_dialog_identity(
    payload: dict[str, Any],
    *,
    user_id: str,
    flow_id: str = "",
) -> dict[str, str]:
    uid = _text(user_id)
    if not uid:
        raise ValueError("USER_ID_REQUIRED")

    dialog_id = _text(
        payload.get("dialog_id")
        or payload.get("conversation_id")
        or payload.get("dialogue_id")
    )
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
        "interpretation_id": _text(payload.get("interpretation_id")),
    }


def assert_identity_match(
    expected: dict[str, Any],
    actual: dict[str, Any] | None,
) -> None:
    """Raise before Web delivery when response identity does not match the request."""
    if not isinstance(actual, dict):
        raise ValueError("RESPONSE_IDENTITY_MISSING")

    aliases = {
        "user_id": ("user_id", "april_id"),
        "conversation_id": ("conversation_id",),
        "dialog_id": ("dialog_id", "dialogue_sequence_id"),
        "message_id": ("message_id", "turn_id"),
        "flow_id": ("flow_id",),
        "interpretation_id": ("interpretation_id",),
    }

    for field, actual_keys in aliases.items():
        expected_value = _text(expected.get(field))
        if not expected_value:
            continue
        actual_value = ""
        for key in actual_keys:
            actual_value = _text(actual.get(key))
            if actual_value:
                break
        if not actual_value:
            continue
        if expected_value != actual_value:
            raise ValueError(f"IDENTITY_MISMATCH:{field}")


__all__ = [
    "new_dialog_id",
    "new_message_id",
    "resolve_dialog_identity",
    "assert_identity_match",
]
