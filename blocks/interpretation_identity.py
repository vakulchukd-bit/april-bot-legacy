"""Canonical interpretation identity for April's single chat route.

The interpretation identity is metadata only. It binds one interpretation to the
already-authenticated April user, conversation/dialogue sequence and message.
It does not create another route or another context store.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4


def _text(value: Any) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class InterpretationIdentity:
    interpretation_id: str
    dialog_id: str
    conversation_id: str
    message_id: str
    april_id: str

    @classmethod
    def create(
        cls,
        *,
        april_id: Any,
        conversation_id: Any,
        dialog_id: Any,
        message_id: Any,
        interpretation_id: Any = None,
    ) -> "InterpretationIdentity":
        normalized = {
            "april_id": _text(april_id),
            "conversation_id": _text(conversation_id),
            "dialog_id": _text(dialog_id),
            "message_id": _text(message_id),
        }
        for name, value in normalized.items():
            if not value:
                raise ValueError(f"{name} is required")

        return cls(
            interpretation_id=_text(interpretation_id) or f"interp_{uuid4().hex}",
            dialog_id=normalized["dialog_id"],
            conversation_id=normalized["conversation_id"],
            message_id=normalized["message_id"],
            april_id=normalized["april_id"],
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "interpretation_id": self.interpretation_id,
            "dialog_id": self.dialog_id,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
            "april_id": self.april_id,
        }


def build_interpretation_identity(
    *,
    april_id: Any = "",
    conversation_id: Any = "",
    dialog_id: Any = "",
    message_id: Any = "",
    interpretation_id: Any = "",
    flow_id: Any = "",
    user_id: Any = "",
) -> dict[str, str]:
    """Build the canonical interpretation identity from the current route identity.

    ``flow_id`` is accepted as route metadata and is intentionally not embedded
    into the interpretation id. ``user_id`` is accepted as a compatibility alias
    for the authenticated April id used by the canonical envelope.
    """
    resolved_april_id = _text(april_id or user_id)
    resolved_dialog_id = _text(dialog_id or conversation_id)
    resolved_conversation_id = _text(conversation_id or resolved_dialog_id)
    resolved_message_id = _text(message_id)
    if not resolved_message_id:
        raise ValueError("message_id is required")

    identity = InterpretationIdentity.create(
        april_id=resolved_april_id,
        conversation_id=resolved_conversation_id,
        dialog_id=resolved_dialog_id,
        message_id=resolved_message_id,
        interpretation_id=interpretation_id,
    )
    result = identity.as_dict()
    if _text(flow_id):
        result["flow_id"] = _text(flow_id)
    return result
