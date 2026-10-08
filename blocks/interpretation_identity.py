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
    # These markers describe an OUTPUT ACTION, not an input object.
    # Merely mentioning "картинка", "файл", "python" or "код" must never
    # request generation/production by itself.
    "image": {
        "draw", "drawing", "generate image", "generate a picture", "create image",
        "create an image", "create a picture", "make an image", "make a picture",
        "нарисуй", "нарисовать", "сгенерируй", "создай изображение", "создай картинку",
        "сделай картинку", "сделай изображение", "изобрази", "создай фото",
    },
    "file": {
        "create file", "make a file", "export file", "download file", "save to file",
        "создай файл", "сделай файл", "выдай файл", "создай документ", "сделай документ",
        "сохрани в файл", "экспортируй файл", "подготовь файл",
    },
    "link": {
        "give me a link", "send a link", "show link", "open link", "дай ссылку",
        "отправь ссылку", "покажи ссылку", "пришли ссылку", "ссылка на сайт",
    },
    "code": {
        "write code", "show code", "generate code", "provide code", "fix code",
        "write python", "write a script", "create a script", "дай код", "напиши код",
        "покажи код", "сгенерируй код", "исправь код", "напиши скрипт", "создай скрипт",
    },
    "formula": {
        "write formula", "show formula", "solve equation", "write an equation",
        "напиши формулу", "покажи формулу", "реши уравнение", "запиши уравнение",
    },
    "diagram": {
        "create diagram", "draw diagram", "show diagram", "создай диаграмму",
        "нарисуй диаграмму", "построй диаграмму", "сделай диаграмму", "создай схему",
        "нарисуй схему", "сделай схему",
    },
    "table": {
        "create table", "make a table", "show table", "build a table",
        "создай таблицу", "сделай таблицу", "построй таблицу", "покажи таблицу",
    },
}

_IMAGE_MODIFICATION_MARKERS = {
    "edit image", "edit the image", "modify image", "change image", "alter image",
    "edit photo", "modify photo", "change photo", "замени на фото", "измени фото",
    "измени картинку", "измени изображение", "отредактируй фото", "отредактируй картинку",
    "добавь на фото", "убери с фото", "замени на картинке", "измени на картинке",
}


def _contains_marker(text: str, marker: str) -> bool:
    low = _text(text).lower()
    phrase = _text(marker).lower()
    if not low or not phrase:
        return False
    # Phrase markers are deliberately explicit. Input nouns such as "файл",
    # "картинка", "python" and "код" are NOT output requests.
    if " " not in phrase:
        return bool(re.search(rf"(?<![\w\u0080-\uffff]){re.escape(phrase)}(?![\w\u0080-\uffff])", low))
    return phrase in low


def _detect_image_modification(text: str) -> bool:
    low = _text(text).lower()
    return any(_contains_marker(low, marker) for marker in _IMAGE_MODIFICATION_MARKERS)


def _detect_requested_outputs(text: str) -> list[str]:
    result: list[str] = []
    low = _text(text).lower()
    for output, markers in _OUTPUT_MARKERS.items():
        if any(_contains_marker(low, marker) for marker in markers):
            result.append(output)

    # A plain image/photo mention is input context, not an output request.
    # Image editing is an explicit generation operation.
    if _detect_image_modification(low) and "image" not in result:
        result.append("image")

    if not result:
        result.append("text")
    elif "text" not in result:
        result.insert(0, "text")
    return result


def _detect_task(
    text: str,
    *,
    has_image: bool,
    has_voice: bool,
    has_file: bool,
    wants_image: bool,
) -> str:
    low = _text(text).lower()
    if wants_image:
        return "generate_image"

    explicit_visual_analysis = any(
        token in low
        for token in (
            "analyze", "analyse", "what is", "what's in", "describe", "опиши",
            "проанализ", "что на", "что изображено", "что видно", "что здесь",
            "что на фото", "что на картинке", "что на изображении",
        )
    )

    if has_image and has_file:
        # One user request can describe all supplied inputs together. Do not
        # turn either attachment into an output operation.
        return "analyze_input"
    if has_image:
        return "analyze_image"
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
            "explicit_generation_request": wants_image,
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
