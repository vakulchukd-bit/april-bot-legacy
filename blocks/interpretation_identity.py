"""Per-turn interpretation identity.

Interpretation belongs to the processor turn, not to the authenticated user.
It is intentionally separate from April ID, dialog_id and message_id.
"""
from __future__ import annotations

import uuid
from typing import Any


def new_interpretation_id(flow_id: Any = "") -> str:
    token = str(flow_id or "").strip()
    suffix = uuid.uuid4().hex[:16]
    return f"int_{token[:20]}_{suffix}" if token else f"int_{suffix}"


def build_interpretation_identity(
    *,
    interpretation_id: Any = "",
    flow_id: Any = "",
    dialog_id: Any = "",
) -> dict[str, str]:
    value = str(interpretation_id or "").strip() or new_interpretation_id(flow_id)
    return {
        "interpretation_id": value,
        "flow_id": str(flow_id or "").strip(),
        "dialog_id": str(dialog_id or "").strip(),
    }
