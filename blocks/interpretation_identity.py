"""April Interpretation Identity + request interpretation layer.

This is the single semantic-structuring layer between Exkrutor and the Provider.
It binds the authenticated identity and converts every input modality into one
machine-readable interpretation without creating another route.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4
import re


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
    """Build the canonical interpretation identity from route identity."""
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


_OUTPUT_MARKERS = {
    "image": {
        "image", "picture", "photo", "draw", "drawing", "illustration",
        "картин", "рисунк", "изображен", "фото", "нарисуй", "сгенерируй",
    },
    "file": {
        "file", "document", "pdf", "docx", "xlsx", "csv", "файл",
        "документ", "отправь файл", "сохрани",
    },
    "link": {
        "link", "url", "website", "site", "ссылк", "сайт", "страниц",
    },
    "code": {
        "code", "python", "javascript", "typescript", "api", "bug", "код",
        "скрипт", "программ",
    },
    "formula": {
        "formula", "equation", "latex", "формул", "уравнен", "latex",
    },
    "diagram": {
        "diagram", "scheme", "chart", "схем", "диаграм", "график",
    },
    "table": {
        "table", "таблиц", "spreadsheet",
    },
}


def _contains_marker(text: str, marker: str) -> bool:
    low = text.lower()
    return marker in low if len(marker) > 4 else bool(
        re.search(rf"\b{re.escape(marker)}\b", low)
    )


def _detect_requested_outputs(text: str) -> list[str]:
    result: list[str] = []
    low = text.lower()
    for output, markers in _OUTPUT_MARKERS.items():
        if any(_contains_marker(low, marker) for marker in markers):
            result.append(output)
    if not result:
        result.append("text")
    elif "text" not in result:
        result.insert(0, "text")
    return result


def _detect_task(text: str, *, has_image: bool, has_voice: bool, has_file: bool, wants_image: bool) -> str:
    low = _text(text).lower()
    if wants_image:
        return "generate_image"
    if has_image and any(
        token in low for token in ("analyze", "analyse", "what is", "describe", "проанализ", "что на", "опиши")
    ):
        return "analyze_image"
    if has_voice:
        return "answer_transcribed_voice"
    if has_file:
        return "analyze_file"
    return "answer_request"


def _select_continuation_pairs(memory: dict[str, Any]) -> list[dict[str, Any]]:
    relation = _text(memory.get("relation")).upper()
    pairs = memory.get("selected_pairs")
    if relation != "CONTINUE" or not isinstance(pairs, list):
        return []
    return [
        dict(item)
        for item in pairs
        if isinstance(item, dict)
    ][:4]


def build_interpretation(
    *,
    current_request: str,
    original_request: str = "",
    display_language: str = "auto",
    memory: dict[str, Any] | None = None,
    attachments: list[dict[str, Any]] | None = None,
    visual_context: list[dict[str, Any]] | None = None,
    identity: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create the structured request that the Provider is allowed to answer."""
    text = _text(current_request)
    original = _text(original_request or current_request)
    memory = dict(memory or {})
    attachments = [dict(x) for x in (attachments or []) if isinstance(x, dict)]
    visual_context = [dict(x) for x in (visual_context or []) if isinstance(x, dict)]

    kinds = {str(item.get("kind") or "").lower() for item in attachments}
    has_image = "image" in kinds or bool(visual_context)
    has_voice = "voice" in kinds
    has_file = bool(kinds & {"file", "text_file"})

    requested_outputs = _detect_requested_outputs(original or text)
    wants_image = "image" in requested_outputs
    wants_file = "file" in requested_outputs
    wants_links = "link" in requested_outputs

    relation = _text(memory.get("relation") or "NEW").upper()
    selected_pairs = _select_continuation_pairs(memory)

    task = _detect_task(
        original or text,
        has_image=has_image,
        has_voice=has_voice,
        has_file=has_file,
        wants_image=wants_image,
    )

    if has_image and task == "answer_request":
        task = "analyze_image"

    return {
        "schema": "april_interpretation_v2",
        "identity": dict(identity or {}),
        "input": {
            "original_request": original,
            "normalized_request": text,
            "display_language": _text(display_language or "auto") or "auto",
            "modalities": sorted(
                modality
                for modality in (
                    "voice" if has_voice else "",
                    "image" if has_image else "",
                    "file" if has_file else "",
                    "text" if text else "",
                )
                if modality
            ),
            "has_voice": has_voice,
            "has_image": has_image,
            "has_file": has_file,
        },
        "intent": {
            "task": task,
            "requested_outputs": requested_outputs,
            "wants_image": wants_image,
            "wants_file": wants_file,
            "wants_links": wants_links,
            "wants_code": "code" in requested_outputs,
            "wants_formula": "formula" in requested_outputs,
            "wants_diagram": "diagram" in requested_outputs,
            "wants_table": "table" in requested_outputs,
        },
        "dialogue": {
            "relation": relation,
            "is_new_dialogue": relation != "CONTINUE",
            "continuation_context": {
                "active_topic": _text(memory.get("active_topic")),
                "reason": _text(memory.get("reason")),
                "confidence": float(memory.get("relation_confidence") or 0.0),
                "selected_pairs": selected_pairs,
            },
            "new_dialogue": {} if relation == "CONTINUE" else {
                "request": text,
                "needs_independent_resolution": True,
            },
        },
        "visual": {
            "items": visual_context,
            "analysis_required": has_image,
            "generation_required": wants_image,
            "generator": "C_APRIL_IMAGES_GENERATOR" if wants_image else "",
            "image_model": "gpt-image-2" if wants_image else "",
        },
        "files": {
            "items": attachments,
            "analysis_required": has_file,
        },
        "request_structure": {
            "context_always_present": True,
            "user_goal": text,
            "memory_context": selected_pairs,
            "new_dialogue_request": text if relation == "NEW" else "",
            "output_plan": requested_outputs,
        },
    }


def assert_same_identity(expected: dict[str, Any], actual: dict[str, Any]) -> None:
    """Processor guard: reject a provider/scene response bound to another user/turn."""
    fields = (
        ("user_id", "user_id"),
        ("conversation_id", "conversation_id"),
        ("dialog_id", "dialog_id"),
        ("message_id", "message_id"),
        ("flow_id", "flow_id"),
    )
    for left, right in fields:
        ev = _text(expected.get(left) or (expected.get("april_id") if left == "user_id" else ""))
        av = _text(actual.get(right))
        if ev and av and ev != av:
            raise ValueError(f"IDENTITY_MISMATCH:{left}")


__all__ = [
    "InterpretationIdentity",
    "build_interpretation_identity",
    "build_interpretation",
    "assert_same_identity",
]
