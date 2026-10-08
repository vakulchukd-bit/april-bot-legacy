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


# Output intent is deliberately separated from INPUT modalities.
# Words such as "картинка", "фото", "файл" describe an attached object;
# they are NOT generation commands.
_GENERATION_MARKERS = (
    "сгенерируй", "сгенерировать", "генерируй", "нарисуй", "нарисовать",
    "создай изображение", "создать изображение", "сделай картинку",
    "сделать картинку", "создай картинку", "создать картинку",
    "измени фото", "изменить фото", "отредактируй фото", "редактируй фото",
    "edit image", "edit photo", "generate image", "create an image",
    "draw an image", "make a picture",
)
_FILE_OUTPUT_MARKERS = (
    "создай файл", "создать файл", "сделай файл", "сделать файл",
    "сохрани в файл", "экспортируй в файл", "send me the file", "save as",
)
_LINK_OUTPUT_MARKERS = ("дай ссылку", "пришли ссылку", "ссылка на", "url", "link")
_CODE_OUTPUT_MARKERS = (
    "напиши код", "написать код", "исправь код", "исправить код",
    "покажи код", "покажи полный код", "сделай код", "write code", "fix the code",
)
_FORMULA_OUTPUT_MARKERS = ("напиши формулу", "выведи формулу", "реши уравнение", "latex")
_DIAGRAM_OUTPUT_MARKERS = ("нарисуй схему", "создай диаграмму", "построй график", "сделай график")
_TABLE_OUTPUT_MARKERS = ("сделай таблицу", "создай таблицу", "выведи таблицу")


def _has_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    low = _text(text).lower()
    return any(phrase in low for phrase in phrases)


def _detect_requested_outputs(text: str) -> list[str]:
    """Detect requested OUTPUTS only; attachment nouns never imply generation."""
    value = _text(text)
    result = ["text"]
    if _has_phrase(value, _GENERATION_MARKERS):
        result.append("image")
    if _has_phrase(value, _FILE_OUTPUT_MARKERS):
        result.append("file")
    if _has_phrase(value, _LINK_OUTPUT_MARKERS):
        result.append("link")
    if _has_phrase(value, _CODE_OUTPUT_MARKERS):
        result.append("code")
    if _has_phrase(value, _FORMULA_OUTPUT_MARKERS):
        result.append("formula")
    if _has_phrase(value, _DIAGRAM_OUTPUT_MARKERS):
        result.append("diagram")
    if _has_phrase(value, _TABLE_OUTPUT_MARKERS):
        result.append("table")
    return list(dict.fromkeys(result))


def _detect_task(
    text: str,
    *,
    has_image: bool,
    has_voice: bool,
    has_file: bool,
    wants_image: bool,
    wants_code: bool,
) -> str:
    low = _text(text).lower()
    if wants_image:
        return "generate_image"
    if has_image and any(token in low for token in (
        "analyze", "analyse", "what is", "describe", "что на", "опиши",
        "что изображено", "кто на фото", "что видно", "какого цвета", "какой породы",
    )):
        return "analyze_image"
    if has_file and wants_code:
        return "analyze_file_and_code"
    if has_file:
        return "analyze_file"
    if has_voice:
        return "answer_transcribed_voice"
    return "answer_request"


def _select_continuation_pairs(memory: dict[str, Any]) -> list[dict[str, Any]]:
    relation = _text(memory.get("relation")).upper()
    pairs = memory.get("selected_pairs")
    if relation != "CONTINUE" or not isinstance(pairs, list):
        return []
    return [dict(item) for item in pairs if isinstance(item, dict)][:4]


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
    """Build a multimodal interpretation without mixing attachment content into the request."""
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
    wants_code = "code" in requested_outputs
    wants_formula = "formula" in requested_outputs
    wants_diagram = "diagram" in requested_outputs
    wants_table = "table" in requested_outputs

    relation = _text(memory.get("relation") or "NEW").upper()
    selected_pairs = _select_continuation_pairs(memory)
    task = _detect_task(
        original or text,
        has_image=has_image,
        has_voice=has_voice,
        has_file=has_file,
        wants_image=wants_image,
        wants_code=wants_code,
    )
    if has_image and not wants_image and task == "answer_request":
        task = "analyze_image"

    # When the user sends only an attachment, the attachment is input context;
    # it is never promoted to a generation request.
    return {
        "schema": "april_interpretation_v3",
        "identity": dict(identity or {}),
        "input": {
            "original_request": original,
            "normalized_request": text,
            "display_language": _text(display_language or "auto") or "auto",
            "modalities": sorted(modality for modality in (
                "voice" if has_voice else "",
                "image" if has_image else "",
                "file" if has_file else "",
                "text" if text else "",
            ) if modality),
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
            "wants_code": wants_code,
            "wants_formula": wants_formula,
            "wants_diagram": wants_diagram,
            "wants_table": wants_table,
            "generation_authorized": wants_image,
        },
        "dialogue": {
            "relation": relation,
            "is_new_dialogue": relation != "CONTINUE",
            "continuation_context": {
                "active_topic": _text(memory.get("active_topic")),
                "reason": _text(memory.get("reason")),
                "confidence": float(memory.get("relation_confidence") or 0.0),
                "selected_pairs": selected_pairs,
                "context_facts": list(memory.get("context_facts") or [])[:12],
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
            "generation_gate": {
                "authorized": wants_image,
                "reason": "explicit_user_generation_request" if wants_image else "no_generation_request",
            },
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
