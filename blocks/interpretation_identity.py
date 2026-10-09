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
        "создай файл", "сделай файл", "выдай файл", "выдай исправленный файл",
        "выдай новый файл", "сохрани исправленный файл", "пришли файл с кодом",
        "создай документ", "сделай документ", "сохрани в файл", "экспортируй файл", "подготовь файл",
        "выдай улучшенный файл", "выдай файл с улучшенным кодом", "создай файл с исправленным кодом",
        "сформируй файл с исправленным кодом", "сохрани исправленный код в файл",
        "файл с улучшенным кодом", "дай файл с кодом", "пришли исправленный код файлом",
    },
    "link": {
        "give me a link", "send a link", "show link", "open link", "дай ссылку",
        "отправь ссылку", "покажи ссылку", "пришли ссылку", "ссылка на сайт",
    },
    "code": {
        "write code", "show code", "generate code", "provide code", "fix code",
        "write python", "write a script", "create a script", "дай код", "напиши код",
        "покажи код", "сгенерируй код", "исправь код", "исправь этот код", "улучши код",
        "улучши этот код", "улучшить код", "оптимизируй код", "перепиши код", "обнови код",
        "исправь скрипт", "перепиши скрипт", "исправь файл с кодом", "выдай исправленный код",
        "выдай новый код", "выдай новый файл с кодом", "напиши скрипт", "создай скрипт",
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



_HISTORY_MARKERS = (
    "о чем мы говорили", "о чём мы говорили", "о чем говорили", "о чём говорили",
    "что мы обсуждали", "что обсуждали", "какие темы", "напомни темы",
    "напомни о чем", "напомни о чём", "история диалога", "история разговора",
    "наши темы", "о чем шла речь", "о чём шла речь",
)
_HISTORY_COUNTS = {
    "один": 1, "одну": 1, "два": 2, "две": 2, "три": 3, "четыре": 4,
    "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10,
}


def _is_history_request(text: str) -> bool:
    low = _text(text).lower().replace("ё", "е")
    return any(marker.replace("ё", "е") in low for marker in _HISTORY_MARKERS)


def _history_count(text: str) -> int:
    low = _text(text).lower().replace("ё", "е")
    match = re.search(r"\b(10|[1-9])\b", low)
    if match:
        return max(1, min(10, int(match.group(1))))
    for word, count in _HISTORY_COUNTS.items():
        if re.search(rf"\b{word}\b", low):
            return count
    return 7


def _select_history_topics(memory: dict[str, Any]) -> list[dict[str, Any]]:
    topics = memory.get("history_topics")
    return [
        dict(item)
        for item in topics
        if isinstance(item, dict)
    ][:10] if isinstance(topics, list) else []


def _select_continuation_pairs(memory: dict[str, Any]) -> list[dict[str, Any]]:
    relation = _text(memory.get("relation")).upper()
    pairs = memory.get("selected_pairs")
    if relation != "CONTINUE" or not isinstance(pairs, list):
        return []
    return [
        dict(item)
        for item in pairs
        if isinstance(item, dict)
    ][:6]


def _split_request_sequence(text: str) -> list[str]:
    """Split explicit multi-part requests without rewriting their wording."""
    source = _text(text)
    if not source:
        return []

    # Numbered/list lines are reliable boundaries; keep the original wording.
    lines = [line.strip() for line in source.splitlines() if line.strip()]
    parts: list[str] = []
    for line in lines or [source]:
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)]|[a-zA-Z][.)])\s*", "", line).strip()
        if not line:
            continue
        # Several direct questions in one paragraph are independent steps.
        question_parts = [piece.strip() for piece in re.split(r"(?<=[?？])\s+", line) if piece.strip()]
        if len(question_parts) > 1:
            parts.extend(question_parts)
        else:
            parts.append(line)

    # A single unnumbered line with semicolon-separated imperatives is also a
    # useful task sequence; avoid splitting ordinary prose on commas.
    if len(parts) == 1 and parts[0].count(";") >= 2:
        parts = [piece.strip() for piece in parts[0].split(";") if piece.strip()]
    # Stable de-duplication prevents a repeated line from generating duplicate work.
    result: list[str] = []
    seen: set[str] = set()
    for part in parts:
        key = re.sub(r"\s+", " ", part).casefold()
        if key and key not in seen:
            seen.add(key)
            result.append(part)
    return result or [source]


def _build_question_sequence(text: str) -> list[dict[str, Any]]:
    """Describe the user's requested steps and their Web artifact types."""
    sequence: list[dict[str, Any]] = []
    for index, item in enumerate(_split_request_sequence(text), start=1):
        outputs = _detect_requested_outputs(item)
        sequence.append({
            "step_index": index,
            "request": item,
            "output_types": outputs or ["text"],
            "answer_in_order": True,
        })
    return sequence


_CODE_MODIFICATION_MARKERS = (
    "исправь код", "исправь этот код", "улучши код", "улучши этот код",
    "улучшить код", "оптимизируй код", "перепиши код", "обнови код",
    "исправь скрипт", "перепиши скрипт", "fix this code", "improve this code",
    "refactor this code", "optimize this code", "rewrite this code",
)

def _is_code_modification_request(text: str) -> bool:
    low = _text(text).lower().replace("ё", "е")
    return any(marker.replace("ё", "е") in low for marker in _CODE_MODIFICATION_MARKERS)


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
    restored_assets = [
        dict(item) for item in (memory.get("restored_assets") or [])
        if isinstance(item, dict)
    ]
    restored_kinds = {str(item.get("kind") or "").lower() for item in restored_assets}
    has_image = "image" in kinds or "image" in restored_kinds or bool(visual_context)
    has_voice = "voice" in kinds
    has_file = bool(kinds & {"file", "text_file"}) or bool(restored_kinds & {"file", "text_file"})
    # Distinguish an asset's presence in dialogue memory from actual source bytes
    # available for a fresh inspection. A cached sidecar is enough for normal
    # continuity, and must not trigger repeated image/file analysis by itself.
    has_original_image = any(
        not bool(item.get("recalled_from_memory")) or bool(item.get("requires_original_analysis"))
        for item in visual_context
    )
    has_original_file = any(
        _text(item.get("kind")).lower() in {"file", "text_file"}
        and (not bool(item.get("recalled_from_memory")) or bool(item.get("requires_original_analysis")))
        for item in attachments
    )

    requested_outputs = _detect_requested_outputs(original or text)
    wants_image = "image" in requested_outputs
    wants_file = "file" in requested_outputs
    wants_links = "link" in requested_outputs

    relation = _text(memory.get("relation") or "NEW").upper()
    selected_pairs = _select_continuation_pairs(memory)
    history_request = bool(memory.get("history_request")) or _is_history_request(original or text)
    history_count = max(1, min(10, int(memory.get("requested_topic_count") or _history_count(original or text) or 7)))
    history_topics = _select_history_topics(memory)[:history_count]

    # Referential questions such as "а про него еще?" are resolved by the
    # State Manager anchor, not by guessing from the current sentence.
    continuation_anchor = dict(memory.get("anchor") or {}) if isinstance(memory.get("anchor"), dict) else {}
    identity_data = dict(identity or {})
    current_identity = {
        "user_id": _text(identity_data.get("user_id") or identity_data.get("april_id")),
        "conversation_id": _text(identity_data.get("conversation_id")),
        "dialog_id": _text(identity_data.get("dialog_id")),
        "message_id": _text(identity_data.get("message_id")),
        "flow_id": _text(identity_data.get("flow_id")),
        "interpretation_id": _text(identity_data.get("interpretation_id")),
    }
    asset_slot = "continuation_context" if relation == "CONTINUE" else "new_dialogue_request"
    asset_task_map: list[dict[str, Any]] = []
    for item in attachments:
        asset_task_map.append({
            "filename": _text(item.get("filename"))[:240],
            "kind": _text(item.get("kind") or "file").lower(),
            "asset_role": _text(item.get("asset_role") or "user_input"),
            "asset_message_id": _text(item.get("asset_message_id") or current_identity.get("message_id")),
            "context_slot": asset_slot,
            "analysis_summary": _text(item.get("analysis_summary"))[:1200],
            "original_required": bool(item.get("requires_original_analysis", not bool(item.get("recalled_from_memory")))),
        })
    for item in visual_context:
        asset_task_map.append({
            "filename": _text(item.get("filename") or "image")[:240],
            "kind": "image",
            "asset_role": _text(item.get("asset_role") or "user_input"),
            "asset_message_id": _text(item.get("asset_message_id") or current_identity.get("message_id")),
            "context_slot": asset_slot,
            "analysis_summary": _text(item.get("analysis_summary"))[:1200],
            "original_required": bool(item.get("requires_original_analysis", not bool(item.get("recalled_from_memory")))),
        })
    # bot.ru presents image metadata and decoded image data separately. Merge
    # those views into one semantic asset entry per original source.
    unique_asset_task_map: list[dict[str, Any]] = []
    seen_asset_keys: set[tuple[str, str, str, str]] = set()
    for asset in asset_task_map:
        key = (
            _text(asset.get("asset_message_id")),
            _text(asset.get("filename")),
            _text(asset.get("kind")),
            _text(asset.get("asset_role")),
        )
        if key in seen_asset_keys:
            continue
        seen_asset_keys.add(key)
        unique_asset_task_map.append(asset)
    asset_task_map = unique_asset_task_map

    task = _detect_task(
        original or text,
        has_image=has_original_image,
        has_voice=has_voice,
        has_file=has_original_file,
        wants_image=wants_image,
    )
    # A modification verb requests a code edit; merely asking what a code file
    # does remains analyze_file and never silently becomes code generation.
    if _is_code_modification_request(original or text) and has_file:
        task = "modify_code"

    if has_original_image and task == "answer_request":
        task = "analyze_image"

    return {
        "schema": "april_interpretation_v2",
        "identity": current_identity,
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
            "history_request": history_request,
            "history_count": history_count if history_request else 0,
        },
        "dialogue": {
            "relation": relation,
            "is_new_dialogue": relation != "CONTINUE",
            "continuation_context": {
                "active_topic": _text(memory.get("active_topic")),
                "reason": _text(memory.get("reason")),
                "confidence": float(memory.get("relation_confidence") or 0.0),
                "selected_pairs": selected_pairs,
                "anchor": continuation_anchor,
                "history_topics": history_topics,
                "known_topic_count": int(memory.get("known_topic_count") or len(history_topics)),
                "restored_assets": [
                    {
                        "filename": _text(item.get("filename"))[:160],
                        "kind": _text(item.get("kind")),
                        "mime_type": _text(item.get("mime_type")),
                        "asset_message_id": _text(item.get("asset_message_id")),
                    }
                    for item in restored_assets[:4]
                ],
            },
            # Keep the exact current request present on every turn. The active flag
            # controls topic switching; a CONTINUE request is not reclassified as NEW.
            "new_dialogue": {
                "request": original or text,
                "active": relation != "CONTINUE" and not history_request,
                "needs_independent_resolution": relation != "CONTINUE" and not history_request,
            },
        },
        "visual": {
            "items": visual_context,
            "analysis_required": has_original_image,
            "generation_required": wants_image,
            "input_source": "current_upload" if any(not item.get("recalled_from_memory") for item in visual_context) else ("dialogue_memory" if has_image else "none"),
            "remembered_assets": [item for item in restored_assets if _text(item.get("kind")).lower() == "image"][:4],
            "generator": "C_APRIL_IMAGES_GENERATOR" if wants_image else "",
            "image_model": "gpt-image-2" if wants_image else "",
        },
        "files": {
            "items": attachments,
            "analysis_required": has_original_file,
            "remembered_assets": [item for item in restored_assets if _text(item.get("kind")).lower() in {"file", "text_file"}][:4],
        },
        "request_structure": {
            "context_always_present": True,
            "user_goal": text,
            "memory_context": selected_pairs,
            "history_request": history_request,
            "history_count": history_count if history_request else 0,
            "history_topics": history_topics,
            "topic_table_markdown": _text(memory.get("topic_table_markdown")),
            "new_dialogue_request": original or text,
            "new_dialogue_active": relation != "CONTINUE" and not history_request,
            "continuation_context": selected_pairs if relation == "CONTINUE" else [],
            "asset_task_map": asset_task_map,
            "question_sequence": _build_question_sequence(original or text),
            "answer_sequence_in_order": True,
            "presentation_contract": {
                "mcdowell_required": True,
                "katex_required_for_math": True,
                "scene_contract_required": True,
            },
            "improvement_policy": "Improve the requested result while preserving unaffected behavior; do not invent missing source content.",
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
