"""April Interpretation Identity + request interpretation layer.

This is the single semantic-structuring layer between Exkrutor and the Provider.
It binds the authenticated identity and converts every input modality into one
machine-readable interpretation without creating another route.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import time
from difflib import SequenceMatcher
from typing import Any
from uuid import uuid4
import re


# Identity and command semantics live in this existing interpreter module.
def is_april_identity_question(value: Any) -> bool:
    text = str(value or "").lower().replace("ё", "е").strip()
    if not text:
        return False
    subject = r"(?:април\w*|aprill?\b|ты\b|тебя\b|твой\b|твоя\b|вас\b|вы\b|your\b|you\b|yourself\b)"
    authorship = r"(?:создател\w*|создал\w*|создан\w*|разработчик\w*|разработал\w*|разработан\w*|автор\w*|основател\w*|основал\w*|придумал\w*|производител\w*|произвел\w*|сделал\w*|сделан\w*|built\b|made\b|created\b|developed\b|creator\b|developer\b|manufacturer\b|author\b|founder\b)"
    patterns = (
        rf"\bкто\s+(?:именно\s+)?(?:тебя|вас)\s+(?:{authorship})",
        rf"\bкто\s+(?:именно\s+)?(?:твой|ваш)\s+{authorship}",
        rf"\bкто\s+(?:именно\s+)?(?:является\s+)?{authorship}\s+(?:(?:проекта|продукта|системы)\s+)?(?:април\w*|aprill?)\b",
        rf"\bкто\s+{authorship}\s+(?:ты|тебя|вас)\b",
        rf"\bкто\s+{authorship}\s+(?:проект\s+)?(?:април\w*|aprill?)\b",
        rf"\b{authorship}\s+(?:април\w*|aprill?)\b",
        rf"\bкто\s+(?:создал|разработал|сделал|придумал|основал|автор)\s+(?:(?:проект|продукт|систему)\s+)?(?:април\w*|aprill?)\b",
        rf"\bкем\s+(?:создан\w*|разработан\w*|сделан\w*)\s+(?:(?:проект|продукт|система)\s+)?(?:април\w*|aprill?)\b",
        rf"\b(?:чья|чей|кому\s+принадлежит)\s+(?:април\w*|aprill?)\b",
        r"\bкто\s+(?:стоит\s+за|владелец\s+(?:проекта\s+)?)\s+(?:проектом?\s+)?(?:април\w*|aprill?)\b",
        rf"\bwho\s+(?:created|made|built|developed|authored|owns?)\s+(?:you|yourself|april)\b",
        rf"\bwho\s+is\s+your\s+(?:creator|developer|manufacturer|author)\b",
        rf"\b(?:creator|developer|manufacturer|author)\s+of\s+(?:you|april)\b",
    )
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

def is_bare_visual_command(value: Any) -> bool:
    text = str(value or "").lower().replace("ё", "е").strip(" \t\r\n.,!?;:")
    if not text:
        return False
    return bool(re.fullmatch(
        r"(?:(?:ну|давай|пожалуйста|мне|нам|тут|здесь|просто|тогда)\s+)*"
        r"(?:нарисуй(?:те)?|нарисовать|изобрази(?:те)?|изобразить|покажи(?:те)?|показать|"
        r"отобрази(?:те)?|визуализируй(?:те)?|draw|show|depict|sketch|illustrate|visualize|visualise)"
        r"(?:\s+(?:мне|нам|пожалуйста|тут|здесь|ну|давай))*",
        text, re.IGNORECASE,
    ))

def is_current_user_name_question(value: Any) -> bool:
    text = str(value or "").lower().replace("ё", "е").strip()
    if not text:
        return False
    return bool(re.search(
        r"(?:\bкак\s+меня\s+зовут\b|\bкак\s+мое\s+имя\b|\bкакое\s+у\s+меня\s+имя\b|"
        r"\bкакое\s+имя\s+(?:указано|стоит)\s+(?:у\s+меня\s+)?(?:в\s+)?(?:настройках|профиле)\b|"
        r"\bмое\s+(?:отображаемое\s+)?имя\b|\bназови\s+мое\s+имя\b|"
        r"\bты\s+знаешь\s+(?:как\s+меня\s+зовут|мое\s+имя)\b|\bкак\s+ты\s+меня\s+называешь\b|"
        r"\bwhat\s+is\s+my\s+name\b)",
        text, re.IGNORECASE,
    ))




def _apr_timing_log(stage: str, started: float | None = None, **fields: Any) -> None:
    """Low-overhead diagnostic timing; logging must never affect the request path."""
    try:
        payload = {"component": "interpretation", "stage": stage}
        if started is not None:
            payload["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
        payload.update(fields)
        print("[APRIL_TIMING] " + json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str), flush=True)
    except Exception:
        pass

def _apr_diag_ref(value: Any) -> str:
    """One-way short reference for joining logs without exposing raw user IDs."""
    try:
        raw = str(value or "").strip()
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10] if raw else ""
    except Exception:
        return ""

def _text(value: Any) -> str:
    return str(value or "").strip()
# Provider refusals are kept as context inside the existing dialogue thread.
# This helper inspects only the small, already-selected same-dialogue pairs;
# it does not scan unrelated history or create a second memory.
_DIALOGUE_LIMITATION_MARKERS = (
    "не могу выполнить эту часть запроса", "не могу выполнить этот запрос",
    "не могу помочь с этим запросом", "не могу создать это содержимое",
    "не могу сгенерировать это", "не могу предоставить это",
    "не могу допомогти з цим запитом", "не можу виконати цей запит",
    "не можу створити такий вміст", "i can't help with that request",
    "i cannot help with that request", "i can't assist with this request",
    "i cannot assist with this request", "i can't create that content",
    "i cannot create that content", "i can't generate that content",
    "i cannot generate that content", "in this form", "under these rules",
    "content policy", "safety policy", "copyright restrictions", "privacy rules",
    "ограничения безопасности", "правила безопасности", "авторских прав",
    "конфиденциальности", "правилами безопасности", "обмеження безпеки",
    "авторських прав", "конфіденційності",
)

def _recent_dialogue_limitations(selected_pairs: Any) -> dict[str, Any]:
    """Compact record of recent refusal/explanation events from ranked dialog pairs."""
    if not isinstance(selected_pairs, list):
        return {"has_recent_limitation": False, "count": 0, "events": []}
    events: list[dict[str, str]] = []
    for pair in selected_pairs[:5]:
        if not isinstance(pair, dict):
            continue
        user_text = _text(
            pair.get("source_user_text") or pair.get("user") or pair.get("user_text")
            or pair.get("request") or pair.get("question")
        )
        april_text = _text(
            pair.get("source_april_text") or pair.get("april") or pair.get("april_text")
            or pair.get("assistant") or pair.get("assistant_text") or pair.get("answer")
            or pair.get("response")
        )
        if not april_text:
            continue
        low = april_text.lower().replace("ё", "е").replace("’", "'")
        explicit_limiter = any(marker in low for marker in _DIALOGUE_LIMITATION_MARKERS)
        refusal_language = bool(re.search(
            r"(?:\bне могу\b|\bне смогу\b|\bне вправе\b|\bне можу\b|"
            r"\bi can't\b|\bi cannot\b|\bi won't\b|\bi will not\b|"
            r"\bje ne peux pas\b)", low, re.I
        ))
        contextual_path = any(marker in low for marker in (
            "другой допустимый вариант", "можем изменить", "сохраним основную цель",
            "в таком виде", "допустимый вариант", "allowed alternative",
            "adjust the request", "preserve your main goal", "another version",
            "збережімо вашу основну мету", "прийнятний варіант",
        ))
        if explicit_limiter or (refusal_language and contextual_path):
            events.append({
                "user_request": user_text[:240],
                "april_explanation": april_text[:300],
            })
        if len(events) >= 3:
            break
    return {
        "has_recent_limitation": bool(events),
        "count": len(events),
        "events": events,
        "instruction": (
            "Treat these as prior events in the same dialogue. Do not repeat a canned refusal; "
            "explain the actual limitation naturally and offer a genuinely allowed next step. "
            "Never bypass the underlying restriction."
        ) if events else "",
    }


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
    identity_started = time.perf_counter()
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
    _apr_timing_log("identity_create", identity_started, user_key=_apr_diag_ref(resolved_april_id),
        dialog_key=_apr_diag_ref(resolved_dialog_id), message_key=_apr_diag_ref(resolved_message_id))
    return result


# Output intent is resolved from an action, its target and dialogue context.

# Direct edit/retouch verbs mean the user wants to change an existing image.
# In the Free chain this is a restricted operation, not a reason to call the generator.
_IMAGE_MODIFICATION_MARKERS = {
    "edit image", "edit the image", "modify image", "change image", "alter image",
    "edit photo", "modify photo", "change photo", "retouch photo", "enhance photo",
    "improve the image", "improve photo", "remove object from photo", "change the background",
    "измени фото", "измени фотографию", "изменить фотографию", "измени картинку",
    "измени изображение", "изменить изображение", "отредактируй фото",
    "отредактируй фотографию", "отредактируй картинку", "улучши фото",
    "улучши фотографию", "улучши картинку", "улучши изображение", "обработай фото",
    "обработай фотографию", "ретушируй фото", "сделай ретушь",
}

# These phrases imply compositing only when an existing/source image is available.
# Without an image, a request such as "нарисуй на фото кота" means create a new picture.
_IMAGE_COMPOSITING_MARKERS = {
    "draw on the photo", "draw on the image", "add to the photo", "add to the image",
    "place on the photo", "put on the photo", "remove from the photo", "replace in the photo",
    "нарисуй на фото", "нарисовать на фото", "нарисуй на фотографии", "нарисуй на картинке",
    "нарисуй на изображении", "добавь на фото", "добавить на фото", "добавь на фотографии",
    "добавь на картинке", "добавь на изображении", "помести на фото", "помести на картинку",
    "убери с фото", "убери с фотографии", "убери с картинки", "замени на фото",
    "замени на фотографии", "замени на картинке", "измени на картинке",
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


def _detect_contextual_image_edit(text: str) -> bool:
    """Recognize image annotation by its action and target, without requiring 'edit image'."""
    low = _text(text).lower().replace("ё", "е")
    action = re.search(
        r"(?:добав\w*|дорис\w*|нанес\w*|постав\w*|укаж\w*|покаж\w*|помет\w*|отмет\w*|"
        r"выдел\w*|обвед\w*|подсвет\w*|передел\w*|исправ\w*|поправ\w*|перерис\w*|"
        r"измени\w*|поменя\w*|отредактир\w*|редактир\w*|обработ\w*|ретуш\w*|улучш\w*|"
        r"сдела\w*|убер\w*|замен\w*|встав\w*|сотри\w*|скрой\w*|"
        r"хочу\w*|хотел\w*|хотела|мне\s+нужно|мне\s+надо|пусть|чтобы|"
        r"add|draw|mark|point|annotate|highlight|redo|revise|change|edit|modify|i\s+want|i(?:'d|\s+would)\s+like)", low, re.IGNORECASE)
    target = re.search(
        r"(?:стрелк\w*|указател\w*|маркер\w*|кнопк\w*|место\s+(?:нажатия|клик\w*)|куда\s+нажать|"
        r"галочк\w*|цвет\w*|красн\w*|зелен\w*|фон\w*|надпис\w*|текст\w*|"
        r"шляп\w*|шапк\w*|очк\w*|одежд\w*|предмет\w*|объект\w*|детал\w*|элемент\w*|"
        r"фот\w*|картинк\w*|изображени\w*|син\w*|темн\w*|светл\w*|"
        r"шарф\w*|галстук\w*|сумк\w*|обув\w*|прическ\w*|волос\w*|бород\w*|крыл\w*|"
        r"кот\w*|собак\w*|arrow|pointer|marker|button|click|red|green|highlight|circle|outline|"
        r"hat|cap|glasses|clothes|scarf|tie|bag|shoes|hair|beard|wings|object|person)",
        low, re.IGNORECASE)
    visual_reference = re.search(
        r"(?:на\s+(?:ней|нем|него|нее|неё|этом|этой|эту|фото|фотографии|картинке|изображении)|"
        r"в\s+(?:ней|нем|него|нее|неё|этой|этом)|к\s+(?:ней|нему|этой\s+фотографии|этой\s+картинке|картинке|фото|изображению)|"
        r"(?:ее|её|его|нее|неё|этот\s+объект|эта\s+картинка)|"
        r"on\s+(?:it|there|the\s+image|the\s+photo)|in\s+(?:it|there)|to\s+(?:it|the\s+image|the\s+photo))",
        low, re.IGNORECASE)
    return bool(action and (target or visual_reference))


def _detect_image_modification(text: str, *, has_existing_image_reference: bool = False) -> bool:
    """Detect a request to alter an existing raster image or photo.

    In Free, raster edits remain restricted instead of being silently converted
    into new image generation. Vector diagrams and SVG overlays use their own
    editable SceneContract route and are not classified as photo edits.
    """
    low = _text(text).lower().replace("ё", "е")
    if not low:
        return False
    if _detect_diagram_overlay_request(low) or _detect_structured_diagram_modification_request(low):
        return False
    # "Нарисуй картинку к заставке" is a new-image deliverable, not an edit of
    # a missing source image. This direct-object rule intentionally does not
    # swallow ambiguous "нарисуй на этой картинке" instructions.
    direct_new_image = bool(re.search(
        r"(?<![\w\u0080-\uffff])(?:нарис\w*|изобраз\w*|созда\w*|сгенерир\w*|draw|create|generate)\b\s+"
        r"(?:(?:мне|нам|a|an|the|new|нов\w*|бел\w*|черн\w*|красив\w*|прост\w*|маленьк\w*|больш\w*)\s+){0,3}"
        r"(?:фото\b|фотограф\w*|фотк\w*|картинк\w*|изображени\w*|иллюстрац\w*|\bimage\b|\bpicture\b|\bphoto\b)",
        low, re.IGNORECASE,
    ))
    if direct_new_image:
        return False
    how_to_question = bool(re.search(
        r"^\s*(?:как\s+(?:(?:мне|можно|самому|самой)\s+)?(?:редактир|измен|улучш|обработ|ретуш|поменя)"
        r"|как\s+делать\s+ретуш|объясни\w*\s*,?\s*как\b|расскажи\w*\s*,?\s*как\b"
        r"|how\s+(?:do\s+i|can\s+i|to)\s+(?:edit|change|improve|enhance|retouch|modify)"
        r"|what\s+is\s+the\s+best\s+way\s+to\s+(?:edit|change|improve|enhance|retouch))",
        low,
        flags=re.IGNORECASE,
    ))
    if _is_attachment_tutorial_request(low) or how_to_question:
        return False

    # A concrete object placement on an already identified photo is an edit.
    # In Free it will still be handled by the existing Premium restriction lane;
    # it must not be re-labelled as a request to create a new picture.
    explicit_existing_source = bool(re.search(
        r"(?:на\s+(?:это\s+|эту\s+|этой\s+|мою\s+)?фот\w*|"
        r"(?:фото|фотограф\w*|фотк\w*)\s+с\s+(?:монет\w*|купюр\w*|деньг\w*|человеком|машин\w*|надпис\w*)|"
        r"(?:присланн\w*|прикрепл\w*|загруженн\w*|предыдущ\w*)\s+(?:фото|фотограф\w*|картинк\w*|изображени\w*))",
        low, re.IGNORECASE,
    ))
    composite_detector = globals().get("_detect_image_compositing_request")
    if has_existing_image_reference and explicit_existing_source and callable(composite_detector) and composite_detector(low):
        return True

    if any(_contains_marker(low, marker.replace("ё", "е")) for marker in _IMAGE_MODIFICATION_MARKERS):
        return True

    # `фотку`, `фотке`, `фотографии` and related colloquial/inflected forms must
    # match the same source-image concept; limiting this to `фото` missed the
    # exact phrasing observed in production logs ("измени эту фотку").
    image_noun = (
        r"(?:фот\w*|картинк\w*|изображени\w*|photo(?:graph)?s?|images?|pictures?)"
    )
    # Direct forms like "измени именно ту фотографию" are missed by simple
    # substring markers because polite/reference words are inserted between the
    # verb and the image noun. Keep this pattern limited to actual edit verbs.
    direct_edit = r"(?:edit|modify|change|alter|retouch|enhance|improve|измени\w*|поменя\w*|отредактир\w*|обработ\w*|ретуш\w*|улучш\w*|передел\w*)"
    image_reference_words = r"(?:(?:the|this|that|same|exact|мне|нам|ту|эту|этот|эта|это|эти|той|такую|такой|эту\s+самую|ту\s+самую|именно|саму|самую|присланную|загруженную|прикрепл[её]нную|мою|твою)\s+){0,5}"
    if re.search(
        rf"(?<![\w\u0080-\uffff]){direct_edit}\b\s+{image_reference_words}{image_noun}\b",
        low,
        flags=re.IGNORECASE,
    ):
        return True

    # Natural object-first phrasing must also count as an edit: "изменить тон на
    # картинке", "поменяй яркость на фото", "change the colour in this image".
    # This shared detector is used by both the interpreter and the Free quota
    # preflight, preventing the same source image from being charged twice.
    edit_object = r"(?:тон|цвет\w*|оттен\w*|яркост\w*|контраст\w*|фон\w*|свет\w*|насыщенн\w*|резкост\w*|качество|детал\w*|tone|colour|color|brightness|contrast|background|lighting|saturation|sharpness)"
    change_verbs = r"(?:измени\w*|поменя\w*|скорректиру\w*|отредактиру\w*|улучши\w*|обработа\w*|change\w*|adjust\w*|modify\w*|edit\w*|improve\w*)"
    image_surface = r"(?:картинк\w*|фот\w*|изображени\w*|снимк\w*|image\w*|picture\w*|photo\w*)"
    if has_existing_image_reference and re.search(
        rf"\b{change_verbs}\b.{{0,55}}\b{edit_object}\b.{{0,35}}\b(?:на|в|of|in|on)\s+(?:эт\w*\s+|this\s+|the\s+)?{image_surface}\b",
        low, re.IGNORECASE | re.DOTALL,
    ):
        return True
    if has_existing_image_reference and re.search(
        rf"\b(?:make|сделай|сделать)\b.{{0,45}}\b{image_surface}\b.{{0,35}}\b(?:тепл\w*|холодн\w*|ярче|темнее|светлее|warmer|cooler|brighter|darker|lighter)\b",
        low, re.IGNORECASE | re.DOTALL,
    ):
        return True

    # Also catch object-level changes explicitly tied to a source supplied by
    # the user, e.g. "добавь мячик к той фотографии, что я тебе прислал".
    # Requiring both a sent/uploaded-source reference and an edit action avoids
    # restricting ordinary image creation based on a casual image mention.
    sent_source = bool(re.search(
        rf"\b{image_noun}\b.{{0,120}}\b(?:котор\w*|что|которую)\b.{{0,40}}"
        r"\b(?:я\s+)?(?:тебе\s+)?(?:прислал\w*|отправил\w*|загрузил\w*|прикрепил\w*|передал\w*|sent|uploaded|attached|shared)\b"
        r"|\b(?:именно\s+)?(?:ту|эту|ту\s+самую|эту\s+самую)\s+"
        rf"{image_noun}\b.{{0,120}}\b(?:я\s+)?(?:тебе\s+)?(?:прислал\w*|отправил\w*|загрузил\w*|прикрепил\w*|sent|uploaded|attached|shared)\b",
        low,
        flags=re.IGNORECASE,
    ))
    edit_action = bool(re.search(
        r"\b(?:edit\w*|modify\w*|change\w*|alter\w*|retouch\w*|enhance\w*|improve\w*|"
        r"измени\w*|поменя\w*|отредактир\w*|обработ\w*|ретуш\w*|улучш\w*|передел\w*|"
        r"добав\w*|убер\w*|замен\w*|встав\w*)\b",
        low,
        flags=re.IGNORECASE,
    ))
    return sent_source and edit_action


def _detect_image_compositing_request(text: str) -> bool:
    """Detect object placement/removal wording, interpreted as edit only with a source image."""
    low = _text(text).lower().replace("ё", "е")
    if any(_contains_marker(low, marker.replace("ё", "е")) for marker in _IMAGE_COMPOSITING_MARKERS):
        return True
    # Object nouns often occur between the verb and "на фото" ("добавь кота на фото").
    # Recognize that natural word order without classifying it as editing when no image exists.
    object_placement = re.search(
        r"(?:\b(?:add|put|place|draw|insert|remove|replace)\w*\b.{0,70}\b(?:to|on|in|from)\s+(?:the\s+)?(?:photo|photograph|image|picture)\b)"
        r"|(?:\b(?:добав\w*|нарис\w*|гарис\w*|помест\w*|размест\w*|убер\w*|замен\w*|встав\w*)\b.{0,70}\b(?:на|в|с)\s+(?:этом\s+|этой\s+|это\s+|эту\s+|той\s+|такой\s+)?(?:фот\w*|картинк\w*|изображени\w*))"
        r"|(?:\b(?:на|в|с)\s+(?:этот\s+|этой\s+|эту\s+|это\s+|той\s+|такой\s+)?(?:фот\w*|картинк\w*|изображени\w*).{0,70}\b(?:добав\w*|нарис\w*|помест\w*|размест\w*|убер\w*|замен\w*|встав\w*)\b)",
        low,
        flags=re.IGNORECASE,
    )
    return bool(object_placement)


def _detect_diagram_overlay_request(text: Any) -> bool:
    """Treat annotations over a screenshot/photo as a vector diagram overlay.

    The source image remains an input for visual grounding. Only the overlay is
    produced as SVG/diagram, so a pointer, label, highlight or measurement never
    starts the paid raster-image generator.
    """
    low = _text(text).lower().replace("ё", "е")
    if not low:
        return False
    source_reference = bool(re.search(
        r"(?:на|поверх|по|в|к|над)\s+(?:(?:этом|этой|эту|этот|моем|моей|мою|"
        r"загруженн\w*|прикрепленн\w*|присланн\w*|предыдущ\w*|"
        r"this|that|the|my|uploaded|attached)\s+)?"
        r"(?:скриншот\w*|снимк\w*|фот\w*|фотограф\w*|картинк\w*|"
        r"изображени\w*|screenshot\w*|screen\s*shot\w*|image\w*|photo\w*|picture\w*)",
        low, re.IGNORECASE,
    ))
    if not source_reference:
        return False
    annotation_target = bool(re.search(
        r"(?:стрелк\w*|указател\w*|маркер\w*|метк\w*|кнопк\w*|элемент\w*|"
        r"подпис\w*|надпис\w*|"
        r"номер\w*|обводк\w*|контур\w*|рамк\w*|круж\w*|круг\w*|"
        r"выделенн\w*|подсветк\w*|линия\w*|границ\w*|област\w*|"
        r"координат\w*|размер\w*|измерен\w*|выноск\w*|"
        r"arrow\w*|pointer\w*|marker\w*|label\w*|caption\w*|number\w*|"
        r"outline\w*|circle\w*|highlight\w*|border\w*|callout\w*|measurement\w*)",
        low, re.IGNORECASE,
    ))
    annotation_action = bool(re.search(
        r"(?:нарис\w*|дорис\w*|добав\w*|нанес\w*|постав\w*|укаж\w*|помет\w*|"
        r"отмет\w*|выдел\w*|обвед\w*|подсвет\w*|подпиш\w*|обознач\w*|"
        r"покаж\w*|установ\w*|draw\w*|add\w*|place\w*|put\w*|mark\w*|"
        r"annotat\w*|highlight\w*|outline\w*|label\w*|point\w*)",
        low, re.IGNORECASE,
    ))
    return annotation_target and annotation_action


def _detect_structured_diagram_modification_request(text: Any) -> bool:
    """Recognize revisions to a vector diagram as diagram work, not photo edits."""
    low = _text(text).lower().replace("ё", "е")
    if not low:
        return False
    diagram_edit_actions = (
        r"исправь(?:те)?|исправить|поправь(?:те)?|поправить|измени(?:те)?|изменить|"
        r"переделай(?:те)?|переделать|перерисуй(?:те)?|перерисовать|"
        r"отредактируй(?:те)?|отредактировать|редактируй(?:те)?|редактировать|"
        r"обнови(?:те)?|обновить|переставь(?:те)?|переставить|перемести(?:те)?|переместить|"
        r"сдвинь(?:те)?|сдвинуть|добавь(?:те)?|добавить|убери(?:те)?|убрать|удали(?:те)?|"
        r"удалить|замени(?:те)?|заменить|fix|correct|revise|redraw|edit|modify|change|update|move|add|remove|replace"
    )
    target_matches = list(re.finditer(_OUTPUT_TARGETS["diagram"], low, re.I))
    action_matches = list(re.finditer(
        rf"(?<![\w\u0080-\uffff])(?:{diagram_edit_actions})(?![\w\u0080-\uffff])",
        low, re.I,
    ))
    for action in action_matches:
        if _OUTPUT_NEGATION_PREFIX.search(low[max(0, action.start() - 96):action.start()].rstrip(" ,:—-\t")):
            continue
        if _OUTPUT_EXPLANATION_PREFIX.search(low[max(0, action.start() - 96):action.start()].rstrip(" ,:—-\t")):
            continue
        for target in target_matches:
            if abs(target.start() - action.end()) <= 120 or abs(action.start() - target.end()) <= 70:
                between = low[min(action.end(), target.end()):max(action.start(), target.start())]
                if not re.search(r"(?:[.!?;]|\b(?:что\s+такое|как\s+именно|how\s+to)\b)", between, re.I):
                    return True
    return False

def _detect_image_generation_request(text: str) -> bool:
    """Return True only for an explicitly requested raster-image deliverable.

    A generic drawing verb ("нарисуй кота", "draw a cat") is not an image
    generation authorization. It is routed to the structured diagram renderer.
    Raster generation requires an addressed image/photo/picture/illustration
    target or an explicit image-output desire.
    """
    low = _text(text).lower().replace("ё", "е")
    if not low or _is_attachment_tutorial_request(low):
        return False
    # Markups on user-provided or referenced screenshots/photos are SVG overlays.
    if _detect_diagram_overlay_request(low):
        return False
    if _detect_image_modification(low):
        return False

    image_target = _OUTPUT_TARGETS["image"]
    return bool(
        _OUTPUT_DESIRE_PATTERNS["image"].search(low)
        or _has_output_action_for_target(low, image_target)
    )


def _detect_diagram_drawing_request(text: Any) -> bool:
    """Recognize ordinary object drawings as editable vector diagrams."""
    low = _text(text).lower().replace("ё", "е")
    if not low or _detect_image_generation_request(low):
        return False
    if _detect_diagram_overlay_request(low):
        return True
    if _has_output_action_for_target(low, _OUTPUT_TARGETS["diagram"]):
        return True

    drawing_action = (
        r"нарис\w*|изобраз\w*|рисуй\w*|рисова\w*|draw\w*|depict\w*|"
        r"sketch\w*|paint\w*|illustrat\w*"
    )
    for segment in _output_segments(low):
        match = re.search(
            rf"(?<![\w\u0080-\uffff])(?:{drawing_action})(?![\w\u0080-\uffff])",
            segment, re.I,
        )
        if not match or not _output_action_is_requested(segment, match):
            continue
        tail = segment[match.end():].strip(" ,:—-\t")
        tail = re.sub(
            r"^(?:(?:мне|нам|пожалуйста|мне\s+пожалуйста|please|me|us|for\s+me|a|an|the)\s+)+",
            "", tail, flags=re.I,
        )
        subject = re.match(r"([\w\u0080-\uffff-]+(?:\s+[\w\u0080-\uffff-]+){0,5})", tail, re.U)
        if not subject:
            continue
        subject_text = subject.group(1)
        if re.match(
            r"(?:красиво|аккуратно|наглядно|понятно|примерно|как-нибудь|"
            r"как\s+именно|что|чтобы|beautifully|nicely|clearly|how|what)\b",
            subject_text, re.I,
        ):
            continue
        return True
    return False

def _detect_explicit_portrait_generation_request(text: str) -> bool:
    """Compatibility wrapper; portraits are handled by the image intent resolver."""
    low = _text(text).lower().replace("ё", "е")
    if not low or _detect_image_modification(low):
        return False
    return _has_output_action_for_target(low, _OUTPUT_TARGETS["image"])

def _is_feedback_control_help_request(text: Any) -> bool:
    """Detect a request to locate/use feedback controls below an April reply.

    Mentions of photos, graphs or code in an explanatory example must not turn
    the answer into a media-generation task. The helper requires both a feedback
    target and an interaction/location question, and rejects a separate explicit
    artifact-creation instruction.
    """
    low = _text(text).lower().replace("ё", "е")
    feedback_target = bool(re.search(
        r"(?:отблагодар\w*|поблагодар\w*|спасибо.{0,35}(?:кноп|нажат|найт|где|куда)|"
        r"пожалова\w*|жалоб\w*|feedback\s+(?:button|control)|report\s+(?:button|response|answer)|"
        r"thank(?:s|ing)?\s+(?:button|the\s+answer|the\s+response)|thumbs?\s*(?:up|down))",
        low, re.IGNORECASE,
    ))
    interaction_question = bool(re.search(
        r"(?:куда.{0,35}нажат\w*|что\s+нажат\w*|где.{0,70}(?:кноп\w*|наход\w*|располож\w*|это)|"
        r"(?:кноп\w*|функци\w*).{0,70}(?:где|куда|наж|наход|располож)|"
        r"(?:отблагодар\w*|поблагодар\w*|пожалова\w*|жалоб\w*).{0,70}(?:куда|где|наж|кноп)|"
        r"покажи.{0,70}(?:где|куда|наж|путь|стрелк)|расскажи.{0,70}(?:где|куда|наж)|"
        r"как.{0,30}(?:это|так|сделать|поблагодар)|расскажи.{0,35}покажи|"
        r"where.{0,70}(?:click|button|find|located)|how\s+(?:do\s+i|to).{0,60}(?:thank|report|click)|"
        r"where\s+(?:is|are)\s+(?:the\s+)?(?:thank|report|feedback))",
        low, re.IGNORECASE | re.DOTALL,
    ))
    explicit_artifact_creation = bool(re.search(
        r"(?:\b(?:создай|сгенерир\w*|построй|нарисуй|напиши|выдай|исправь|create|generate|build|draw|write|fix)\b"
        r".{0,65}\b(?:график\w*|диаграмм\w*|код\w*|скрипт\w*|картинк\w*|изображени\w*|фото\w*|"
        r"graph|chart|code|script|image|photo|picture)\b)",
        low, re.IGNORECASE | re.DOTALL,
    ))
    return feedback_target and interaction_question and not explicit_artifact_creation


def _is_video_workflow_help_request(text: Any) -> bool:
    """Treat video-creation how-to questions as explanation, not production."""
    low = _text(text).lower().replace("ё", "е")
    if not low or not re.search(r"(?:виде\w*|ролик\w*|video\w*|clip\w*|animation\w*)", low, re.I):
        return False
    workflow_action = bool(re.search(
        r"(?:созда\w*|сгенерир\w*|сдела\w*|смонтир\w*|анимир\w*|"
        r"create|generate|make|edit|animate|use|пользова\w*|использова\w*)",
        low, re.I,
    ))
    help_frame = bool(re.search(
        r"(?:где|куда|как|почему|подскажи\w*|покажи\w*|объясни\w*|расскажи\w*|"
        r"where|how|why|show\s+me|tell\s+me|help\s+me)",
        low, re.I,
    ))
    return workflow_action and help_frame


def _is_video_workflow_navigation(text: Any) -> bool:
    """Recognize questions about a video tool's controls or location."""
    low = _text(text).lower().replace("ё", "е")
    if not low or not re.search(r"(?:виде\w*|ролик\w*|video\w*|clip\w*|animation\w*)", low, re.I):
        return False
    ui_target = bool(re.search(
        r"(?:кноп\w*|меню|интерфейс\w*|генератор\w*|панел\w*|пол\w*|промпт\w*|prompt\w*|"
        r"наж\w*|клик\w*|загруз\w*|встав\w*|откры\w*|найт\w*|перейт\w*|зайт\w*|"
        r"button\w*|menu|interface|generator|panel|field|click|upload|insert|prompt|open|find|navigate)",
        low, re.I,
    ))
    help_frame = bool(re.search(
        r"(?:где|куда|как|почему|подскажи\w*|покажи\w*|объясни\w*|расскажи\w*|"
        r"where|how|why|show\s+me|tell\s+me|help\s+me)",
        low, re.I,
    ))
    return ui_target and help_frame

def _has_direct_video_generation_action(text: Any) -> bool:
    """Recognize an actual request to produce/animate a video, not find its UI."""
    low = _text(text).lower().replace("ё", "е")
    video = r"(?:виде\w*|ролик\w*|video\w*|clip\w*|animation\w*|анимаци\w*)"
    action = r"(?:сгенерируй(?:те)?|сгенерировать|создай(?:те)?|создать|сделай(?:те)?|сделать|смонтируй(?:те)?|смонтировать|анимируй(?:те)?|анимировать|produce|generate|create|make|render|animate|compose)"
    return _has_output_action_for_target(low, video, action_pattern=action)


def _explicit_video_output_intent(
    text: Any, attachments: Any = None, *, allow_edit: bool = True,
) -> tuple[bool, list[str]]:
    """Resolve C_VIDEO intent without turning UI guidance into video generation."""
    source = _text(text)
    if not source:
        return False, []
    low = source.lower().replace("ё", "е")
    # Instructions about finding a control or learning how to create a video are
    # explanatory/navigation tasks. Only an independent production action may
    # override that interpretation.
    how_to = bool(re.search(
        r"(?:^|[.!?;]\s*|\b)(?:как\s+(?:мне\s+)?|объясни\w*\s*,?\s*как\s+|расскажи\w*\s*,?\s*как\s+|"
        r"how\s+(?:do\s+i|to|can\s+i)\s+)(?:созда\w*|сгенерир\w*|сдела\w*|смонтир\w*|анимир\w*|create|make|generate|edit|animate)",
        low, re.I,
    ))
    video_workflow_help = _is_video_workflow_help_request(source)
    video_workflow_navigation = _is_video_workflow_navigation(source)
    navigation_help = (
        video_workflow_navigation
        or _is_feedback_control_help_request(source)
        or _is_site_navigation_request(source)
    )
    direct_video_action = _has_direct_video_generation_action(source)
    if (video_workflow_help and not direct_video_action) or ((how_to or navigation_help) and not direct_video_action):
        return False, []
    try:
        from blocks.C_VIDEO import classify_video_request, explicit_video_companion_outputs
        plan = classify_video_request(source, attachments or [])
        action = _text(plan.get("action")).lower()
        if action == "generate" and (not navigation_help or direct_video_action):
            return True, explicit_video_companion_outputs(source)
        if allow_edit and action == "edit" and not navigation_help:
            return True, explicit_video_companion_outputs(source)
    except Exception:
        # A direct production request remains typed as video. The executor's
        # shared C_VIDEO plan is still the final execution gate.
        return (True, []) if direct_video_action and not how_to else (False, [])
    return False, []

# Output nouns are typed targets, not triggers. They select a renderer only when
# connected to an actual user action or an expressed desire for that deliverable.
_OUTPUT_TARGETS = {
    "image": r"(?:picture\w*|image\w*|illustration\w*|photo\w*|photograph\w*|portrait\w*|artwork\w*|"
             r"картинк\w*|изображени\w*|иллюстраци\w*|фот\w*|портрет\w*|рисунок\w*|постер\w*|обложк\w*|макет\w*|логотип\w*|logo\w*)",
    "diagram": r"(?:diagram\w*|schematic\w*|blueprint\w*|flowchart\w*|workflow\w*|architecture\w*|mind\s*map\w*|"
               r"схем\w*|диаграмм\w*|блок[- ]схем\w*|черт[её]ж\w*|креслен\w*|архитектур\w*|процесс\w*|интеллект[- ]?карт\w*|"
               r"(?:map|карта|карту|карты|картой|маршрутн\w*\s+карт\w*)|"
               r"геометрическ\w*\s+фигур\w*|треугольник\w*|квадрат\w*|прямоугольник\w*|"
               r"параллелограмм\w*|ромб\w*|трапец\w*|многоугольник\w*|окружност\w*|круг\w*|"
               r"эллипс\w*|сфер\w*|шар\w*|куб\w*|пирамид\w*|конус\w*|цилиндр\w*|"
               r"точк\w*|отрез\w*|угол\w*|вектор\w*|стрелк\w*|указател\w*|маркер\w*|метк\w*|"
               r"подпис\w*|выноск\w*|рамк\w*|област\w*|границ\w*|сетка\w*|контур\w*)",
    "graph": r"(?:graph\w*|chart\w*|plot\w*|curve\w*|график\w*|гистограмм\w*|"
             r"парабол\w*|гипербол\w*|волнов\w*\s+(?:график\w*|функци\w*)|поверхност\w*\s+график\w*)",
    "table": r"(?:table\w*|таблиц\w*|spreadsheet\w*|электронн\w*\s+таблиц\w*)",
    "formula": r"(?:formula\w*|equation\w*|формул\w*|уравнен\w*|выражен\w*)",
    "code": r"(?:code\w*|script\w*|код\w*|скрипт\w*|программ\w*\s+текст\w*)",
    "file": r"(?:file\w*|document\w*|attachment\w*|файл\w*|документ\w*|вложени\w*|xlsx|csv|pdf|docx|excel)",
    "link": r"(?:link\w*|url\w*|ссылк\w*|веб[- ]?ссылк\w*|url[- ]?адрес\w*)",
    "copy": r"(?:copy\s*[- ]?block|copyable\s+block|копи[- ]?блок|блок\w*\s+для\s+копирован\w*|текст\w*\s+блок\w*\s+с\s+кнопк\w*\s+копирован\w*)",
}

_OUTPUT_ACTIONS = (
    r"создай(?:те)?|создавай(?:те)?|создать|создавать|"
    r"сгенерируй(?:те)?|сгенерировать|сделай(?:те)?|сделать|"
    r"нарисуй(?:те)?|нарисовать|изобрази(?:те)?|изобразить|рисуй(?:те)?|рисовать|"
    r"покажи(?:те)?|показать|отобрази(?:те)?|отобразить|"
    r"визуализируй(?:те)?|визуализировать|построй(?:те)?|построить|"
    r"составь(?:те)?|составить|сформируй(?:те)?|сформировать|"
    r"напиши(?:те)?|написать|выдай(?:те)?|выдать|выведи(?:те)?|вывести|"
    r"предоставь(?:те)?|предоставить|пришли(?:те)?|прислать|отправь(?:те)?|отправить|"
    r"подготовь(?:те)?|подготовить|экспортируй(?:те)?|экспортировать|"
    r"сохрани(?:те)?|сохранить|скачай(?:те)?|скачать|дай(?:те)?|дать|"
    r"собери(?:те)?|собрать|побудуй(?:те)?|побудувати|"
    r"запиши(?:те)?|записать|реши(?:те)?|решить|получи(?:те)?|получить|"
    r"представь(?:те)?|представить|"
    r"create|generate|make|draw|illustrate|paint|sketch|show|display|render|"
    r"build|plot|write|provide|send|prepare|export|save|download|produce|"
    r"compose|animate|solve|derive|list|attach"
)
_OUTPUT_IMPERATIVE = re.compile(
    r"(?:создай(?:те)?|создавай(?:те)?|сгенерируй(?:те)?|сделай(?:те)?|нарисуй(?:те)?|"
    r"изобрази(?:те)?|рисуй(?:те)?|покажи(?:те)?|отобрази(?:те)?|визуализируй(?:те)?|"
    r"построй(?:те)?|составь(?:те)?|сформируй(?:те)?|напиши(?:те)?|выдай(?:те)?|"
    r"выведи(?:те)?|предоставь(?:те)?|пришли(?:те)?|отправь(?:те)?|подготовь(?:те)?|"
    r"экспортируй(?:те)?|сохрани(?:те)?|скачай(?:те)?|дай(?:те)?|собери(?:те)?|"
    r"create|generate|make|draw|illustrate|paint|sketch|show|display|render|build|plot|"
    r"write|provide|send|prepare|export|save|download|produce|compose|animate|solve|derive|list|attach)",
    re.I,
)

_OUTPUT_REQUEST_CUE = re.compile(
    r"(?:хочу(?:\s+получить)?|хотел(?:а|ось)?\s+бы|мне\s+(?:нужно|надо|нужен|нужна|нужны)|"
    r"нам\s+(?:нужно|надо|нужен|нужна|нужны)|давай(?:те)?|можешь(?:\s+ли)?(?:\s+ты)?|"
    r"можете(?:\s+ли)?|не\s+мог(?:ла|ли)?\s+бы|пожалуйста|please|could\s+you|can\s+you|"
    r"i\s+(?:want|need|would\s+like)|i'd\s+like|we\s+need|let's|lets|"
    r"would\s+you|will\s+you)",
    re.I,
)

_OUTPUT_EXPLANATION_PREFIX = re.compile(
    r"(?:(?:^|[,;:]\s*|\b(?:и|а)\s+)(?:как|каким\s+образом|почему|зачем|где|куда|когда|"
    r"чтобы|объясни\w*|расскажи\w*|подскажи\w*|инструкци\w*|how|where|when|why|to)"
    r"(?:\s+[\w\u0080-\uffff-]+){0,8}|"
    r"(?:покажи\w*|подскажи\w*|объясни\w*|расскажи\w*|show\s+me|tell\s+me)"
    r"\s+(?:как|где|куда|how|where)\b(?:\s+[\w\u0080-\uffff-]+){0,10})\s*$",
    re.I,
)
_OUTPUT_NEGATION_PREFIX = re.compile(
    r"(?:не|ни|не\s+надо|не\s+нужно|не\s+хочу|не\s+просил(?:а)?|нельзя|"
    r"don't|do\s+not|not|never|no\s+need\s+to)\s*$",
    re.I,
)

_OUTPUT_DESIRE_PATTERNS = {
    kind: re.compile(
        r"(?:хочу(?:\s+получить)?|хотел(?:а|ось)?\s+бы|мне\s+(?:нужно|надо|нужен|нужна|нужны)|"
        r"нам\s+(?:нужно|надо|нужен|нужна|нужны)|i\s+(?:want|need)|i'd\s+like|we\s+need)"
        r"\s+(?:(?:нов\w*|готов\w*|отдельн\w*|прост\w*|подробн\w*|красив\w*|"
        r"new|full|complete|simple|detailed|separate)\s+){0,3}"
        + rf"(?:{pattern})",
        re.I,
    )
    for kind, pattern in _OUTPUT_TARGETS.items()
}


def _output_segments(text: Any) -> list[str]:
    """Split only hard clause boundaries; retain ordinary coordinated requests."""
    source = _text(text).lower().replace("ё", "е")
    return [part.strip() for part in re.split(r"[.!?;\n]+", source) if part.strip()]


def _is_inside_quotes(text: str, position: int) -> bool:
    pairs = (("«", "»"), ("“", "”"), ('"', '"'), ("'", "'"), ("‘", "’"))
    for left, right in pairs:
        before = text[:position]
        if before.count(left) > before.count(right):
            return True
    return False


def _output_action_is_requested(
    segment: str,
    match: re.Match[str],
    *,
    target_before: bool = False,
) -> bool:
    """Separate a concrete deliverable instruction from explanation/hypothesis."""
    if _is_inside_quotes(segment, match.start()):
        return False
    before = segment[max(0, match.start() - 96):match.start()]
    before_clean = before.rstrip(" ,:—-\t")
    if _OUTPUT_NEGATION_PREFIX.search(before_clean):
        return False
    verb = match.group(0).lower()
    imperative = bool(_OUTPUT_IMPERATIVE.fullmatch(verb))
    request_cue = bool(_OUTPUT_REQUEST_CUE.search(before_clean))
    infinitive = bool(re.search(r"(?:ть|ти)$", verb, re.I))
    hypothetical = bool(re.search(
        r"(?:если\s+бы|что\s+если|представь\w*\s*,?\s*если|if\s+we|what\s+if|suppose\s+we)\s*$",
        before_clean, re.I,
    ))
    if hypothetical or _OUTPUT_EXPLANATION_PREFIX.search(before_clean):
        return False
    if imperative or request_cue:
        return True
    if target_before:
        # Compact inverted requests: "таблицу построить", "график показать".
        return True
    if infinitive and re.match(r"^\s*(?:мне\s+|нам\s+|please\s+|to\s+)?$", before, re.I):
        # A bare infinitive at the beginning of a message is a compact task.
        return True
    if re.search(r"(?:помоги\w*|помогите\w*|help\s+me)\s*$", before_clean, re.I):
        return True
    return False


def _has_output_action_for_target(
    text: Any,
    target_pattern: str,
    *,
    action_pattern: str = _OUTPUT_ACTIONS,
) -> bool:
    """Match a renderer target to its own requested action in the same clause."""
    for segment in _output_segments(text):
        target_matches = list(re.finditer(target_pattern, segment, re.I))
        action_matches = list(re.finditer(rf"(?<![\w\u0080-\uffff])(?:{action_pattern})(?![\w\u0080-\uffff])", segment, re.I))
        for action_match in action_matches:
            for target_match in target_matches:
                target_before = target_match.end() <= action_match.start()
                if not _output_action_is_requested(segment, action_match, target_before=target_before):
                    continue
                if abs(target_match.start() - action_match.end()) <= 120 or abs(action_match.start() - target_match.end()) <= 70:
                    # Do not bind a target in a separate subordinate how-to clause
                    # to an unrelated verb at the beginning of the sentence.
                    between = segment[min(action_match.end(), target_match.end()):max(action_match.start(), target_match.start())]
                    if re.search(r"(?:[.!?;]|\b(?:что\s+такое|как\s+именно|how\s+to)\b)", between, re.I):
                        continue
                    return True
        if _OUTPUT_DESIRE_PATTERNS.get("image") and _OUTPUT_DESIRE_PATTERNS.get("image").search(segment):
            pass
    return False


def _infer_text_output_actions(text: Any) -> list[str]:
    low = _text(text).lower().replace("ё", "е")
    outputs: list[str] = []
    # A distinct copy block is a special presentation request, not a synonym for
    # ordinary copy support on code blocks.
    if _OUTPUT_DESIRE_PATTERNS["copy"].search(low) or _has_output_action_for_target(low, _OUTPUT_TARGETS["copy"]):
        outputs.append("copy")
    for kind in ("code", "formula", "table", "graph", "diagram", "file", "link"):
        if _OUTPUT_DESIRE_PATTERNS[kind].search(low) or _has_output_action_for_target(low, _OUTPUT_TARGETS[kind]):
            outputs.append(kind)
    # Data visualisation is a graph request when the verb asks to visualise/plot
    # the data, but an ordinary request to show data can still remain textual or
    # use a separately named table renderer.
    data_visualisation = bool(
        re.search(r"(?:визуализир\w*|визуализац\w*|plot(?:ting)?|chart(?:ing)?|graph(?:ing)?)", low, re.I)
        and re.search(r"(?:данн\w*|data(?:set)?s?)", low, re.I)
    )
    if data_visualisation and "graph" not in outputs:
        outputs.append("graph")
    if (
        _detect_diagram_drawing_request(low)
        or _detect_structured_diagram_modification_request(low)
    ) and "diagram" not in outputs:
        outputs.append("diagram")
    if _detect_image_generation_request(low) and "image" not in outputs:
        outputs.append("image")
    return outputs


def _detect_link_request(text: str) -> bool:
    """Compatibility detector backed by action/target semantics."""
    return _has_output_action_for_target(text, _OUTPUT_TARGETS["link"]) or bool(
        _OUTPUT_DESIRE_PATTERNS["link"].search(_text(text).lower())
    )


def _has_direct_non_ui_output_action(text: Any) -> bool:
    low = _text(text).lower().replace("ё", "е")
    if _has_direct_video_generation_action(low):
        return True
    return bool(_infer_text_output_actions(low))


def _detect_requested_outputs(text: str) -> list[str]:
    """Resolve current-turn deliverables; mentions and explanations stay textual."""
    low = _text(text).lower().replace("ё", "е")
    if not low or is_april_identity_question(low) or is_current_user_name_question(low) or is_bare_visual_command(low):
        return ["text"]
    video_workflow_help = _is_video_workflow_help_request(low)
    if video_workflow_help and not _has_direct_video_generation_action(low):
        return ["text"]

    navigation = _is_site_navigation_request(low)
    feedback_help = _is_feedback_control_help_request(low)
    independent_output = _has_direct_non_ui_output_action(low)

    # Route guidance may itself need a simple explanatory diagram, but media
    # nouns inside a UI question are not independent render requests.
    if feedback_help and not independent_output:
        return ["text", "diagram"]
    if navigation and not independent_output:
        if re.search(r"(?:стрелк\w*|путь|карту|схем\w*|пошаг\w*|по\s+шагам|step[- ]by[- ]step|click[- ]by[- ]click)", low, re.I):
            return ["text", "diagram"]
        return ["text"]

    video_requested, video_companions = _explicit_video_output_intent(low)
    if video_requested:
        return list(dict.fromkeys(["text", "video", *video_companions]))

    result = _infer_text_output_actions(low)
    if not result:
        return ["text"]
    return ["text", *[kind for kind in result if kind != "text"]]


def _dialogue_assistant_texts(memory: Any) -> list[str]:
    """Read only already-selected same-dialogue assistant turns and anchors."""
    if not isinstance(memory, dict):
        return []
    texts: list[str] = []
    pair_sources = []
    for key in ("selected_pairs", "pairs", "recent_exchanges", "continuation_context"):
        value = memory.get(key)
        if isinstance(value, list):
            pair_sources.extend(value)
    for pair in reversed(pair_sources[-6:]):
        if not isinstance(pair, dict):
            continue
        value = next((pair.get(key) for key in (
            "source_april_text", "april", "april_text", "assistant", "assistant_text", "answer", "response"
        ) if _text(pair.get(key))), "")
        if value:
            texts.append(_text(value))
    for key in ("latest_assistant_anchor", "last_turn_link", "anchor"):
        item = memory.get(key)
        if isinstance(item, dict):
            value = next((item.get(name) for name in (
                "assistant_text", "april_text", "answer", "response", "text", "content", "summary", "message"
            ) if _text(item.get(name))), "")
            if value:
                texts.insert(0, _text(value))
    # Preserve order while removing duplicate anchor/pair copies.
    unique: list[str] = []
    seen: set[str] = set()
    for value in texts:
        key = value.strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(key)
    return unique[:5]


def _is_affirmative_offer_reply(text: Any) -> bool:
    low = _text(text).lower().replace("ё", "е").strip()
    if not low or len(low) > 80:
        return False
    # Do not treat a joke, correction or a new independent question as consent.
    if re.search(r"(?:шучу|шутка|не\s+надо|не\s+делай|не\s+создавай|почему|как\s+ты|я\s+имел|я\s+имела|joking|just\s+kidding|don't)", low, re.I):
        return False
    return bool(re.fullmatch(
        r"(?:да|ага|угу|конечно|хорошо|ладно|давай|давайте|поехали|делай|сделай|создавай|"
        r"можно|верно|именно|yes|yeah|yep|sure|okay|ok|go\s+ahead|do\s+it|let's\s+do\s+it)"
        r"(?:\s*[,!?.…]\s*(?:давай|делай|сделай|создавай|поехали|yes|sure|go\s+ahead|do\s+it))?\s*[.!?…]*",
        low, re.I,
    ))


def _dialogue_offered_outputs(text: Any, memory: Any) -> list[str]:
    """Carry an offered renderer forward only after a clear user acceptance."""
    if not _is_affirmative_offer_reply(text):
        return []
    assistant_texts = _dialogue_assistant_texts(memory)
    if not assistant_texts:
        return []
    for assistant_text in assistant_texts[:3]:
        offer_cue = bool(re.search(
            r"(?:могу\w*|можем\w*|хочешь\w*|хотите\w*|если\s+хочешь|если\s+нужно|"
            r"готов\w*\s+(?:сделать|создать|нарисовать|показать)|would\s+you\s+like|i\s+can|i\s+could|"
            r"shall\s+i|want\s+me\s+to|can\s+do\s+that)",
            assistant_text.lower().replace("ё", "е"), re.I,
        ))
        if not offer_cue:
            continue
        offered = _detect_requested_outputs(assistant_text)
        renderers = [kind for kind in offered if kind not in {"text", "copy"}]
        if not renderers:
            # An assistant's explicit offer is written in declarative form
            # ("I can create a diagram"), not as an imperative. Normalize only
            # that offer construction into the equivalent task wording, then
            # send it through the same action/target resolver used for users.
            offer_as_task = re.sub(
                r"\b(?:я\s+)?(?:могу|можем|готов(?:а|ы)?|мог\s+бы|могла\s+бы|"
                r"i\s+can|i\s+could|we\s+can|we\s+could|shall\s+i)\s+"
                r"(?=(?:созда\w*|сгенерир\w*|сдела\w*|нарис\w*|изобраз\w*|"
                r"постро\w*|состав\w*|сформир\w*|напиш\w*|подготов\w*|"
                r"create|generate|make|draw|build|plot|write|prepare|render|animate)\b)",
                "",
                assistant_text.lower().replace("ё", "е"),
                flags=re.I,
            )
            offered = _detect_requested_outputs(offer_as_task)
            renderers = [kind for kind in offered if kind not in {"text", "copy"}]
        if renderers:
            return ["text", *renderers]
    return []


def _enhance_requested_outputs(
    text: str,
    explicit_outputs: list[str],
    *,
    dialogue_context: Any = None,
) -> list[str]:
    """Resolve outputs from the request and, when confirmed, the active dialogue."""
    resolved = _detect_requested_outputs(text)
    if resolved == ["text"] and _is_active_diagram_revision_followup(text, dialogue_context):
        resolved = ["text", "diagram"]
    if resolved == ["text"]:
        offered = _dialogue_offered_outputs(text, dialogue_context)
        if offered:
            resolved = offered
    # The direct resolver is authoritative; keep this argument for compatibility
    # with existing executor callers and older question-sequence builders.
    if not resolved:
        resolved = ["text"]
    return list(dict.fromkeys(["text", *[x for x in resolved if x != "text"]]))

def _file_delivery_mode(text: Any, requested_outputs: Any = None) -> str:
    """Return file_only only for an explicit no-inline/file-only instruction."""
    low = _text(text).lower().replace("ё", "е")
    requested = {str(item).strip().lower() for item in (requested_outputs or []) if str(item).strip()}
    if "file" not in requested:
        return "with_inline"
    explicit_both = bool(re.search(
        r"(?:\b(?:и\s+рядом|рядом\s+с|вместе\s+с|также\s+покажи|покажи\s+и|выведи\s+и|и\s+(?:покажи|выведи|отобрази).{0,35}в\s+чат\w*|оба\s+вариант|таблиц\w*.{0,45}и.{0,35}файл)\b|\b(?:both|alongside|also\s+show|show\s+both|table\s+and\s+file|code\s+and\s+file)\b)",
        low, re.I | re.S,
    ))
    explicit_only = bool(re.search(
        r"(?:только\s+(?:в\s+)?(?:[\w-]+\s+){0,5}файл\w*|только\s+файлом|лишь\s+файл\w*|без\s+(?:большого\s+)?вывод\w*\s+(?:в\s+)?чат\w*|не\s+вывод\w*.{0,35}чат\w*|\bfile\s+only\b|\bonly\s+(?:as\s+)?a?\s*file\b|without\s+(?:showing|displaying)\s+(?:the\s+)?(?:full\s+)?(?:code|table|content)\s+in\s+chat|just\s+the\s+file)",
        low, re.I | re.S,
    ))
    file_as_primary = bool(re.search(
        r"(?:\b(?:пришли|пришлите|дай|дайте|выдай|выдайте|сохрани|сохранить|экспортируй|экспортировать|скачай|скачать|отправь|отправить|сформируй|сформировать)\b.{0,90}(?:\bв\s+файл\w*|\bфайлом\b|\bxlsx\b|\bcsv\b|\bpdf\b|\bdocx\b)|\b(?:send|give|export|download|save|deliver)\b.{0,90}(?:\bas\s+(?:a\s+)?file|\bfile\b|\bxlsx\b|\bcsv\b|\bpdf\b|\bdocx\b)|(?:таблиц\w*|код\w*|скрипт\w*|текст\w*).{0,65}(?:\bв\s+(?:отдельн\w*\s+)?файл\w*|\bв\s+(?:формат\w*\s+)?(?:xlsx|excel|csv|pdf|docx)\b|\bas\s+(?:a\s+)?file\b|\bfile\b|\bxlsx\b|\bcsv\b|\bpdf\b|\bdocx\b))",
        low, re.I | re.S,
    ))
    # When a user asks for source code AND a file, keep both representations:
    # CodeBlock is the inline copyable source and FileDeliveryBlock is the saved
    # download. Only an unambiguous "file only / do not show code in chat" request
    # may hide the inline CodeBlock.
    code_plus_file = {"code", "file"}.issubset(requested)
    file_only = explicit_only or (file_as_primary and not explicit_both and not code_plus_file)
    return "file_only" if file_only else "with_inline"

def _legacy_enhance_requested_outputs(text: str, explicit_outputs: list[str]) -> list[str]:
    """Compatibility alias for legacy integrations; use the semantic resolver."""
    return _enhance_requested_outputs(text, explicit_outputs)

def _graph_representation_policy(text: str, *, allow_data_driven_3d: bool = False) -> dict[str, Any]:
    """Choose the intended graph family before Provider builds its render payload.

    Interpretation owns chart intent; renderers only validate/render the structured
    data. Ordinary one-dependent-variable trends stay 2D. Three-dimensional output
    requires an explicit 3D request or genuine structured XYZ/surface/object data.
    """
    low = _text(text).lower().replace("ё", "е")

    explicit_3d = bool(re.search(
        r"(?:\b3\s*[- ]?d\b|\bthree[- ]dimensional\b|\b3d\s+(?:graph|plot|scene|model|projection|visuali[sz]ation)\b|"
        r"тр[её]хмерн\w*|\b3д\b|в\s+3д|в\s+тр[её]хмерн\w*|тр[её]хмерн\w*\s+проекц)",
        low,
    ))

    explicit_bar = bool(re.search(
        r"(?:\bbar\s+chart\b|\bcolumn\s+chart\b|\bstacked\s+bar\b|столбчат\w*\s+(?:диаграмм\w*|график\w*)|"
        r"гистограмм\w*)",
        low,
    ))
    explicit_line = bool(re.search(
        r"(?:\bline\s+(?:chart|graph)\b|линейн\w*\s+(?:график\w*|диаграмм\w*))",
        low,
    ))
    trend_or_time = bool(re.search(
        r"(?:\bgrowth\b|\bgrowing\b|\btrend\b|\bover\s+time\b|\btime\s+series\b|\bdaily\b|\bweekly\b|\bmonthly\b|\byearly\b|"
        r"рост\w*|увелич\w*|сниж\w*|динамик\w*|изменен\w*|за\s+недел\w*|по\s+дням|по\s+датам|по\s+месяц\w*|по\s+год\w*|"
        r"в\s+течени\w*\s+(?:дня|недел\w*|месяц\w*|года)|временн\w*\s+ряд)",
        low,
    ))
    categorical_comparison = bool(re.search(
        r"(?:\bcompare\b|\bcomparison\b|\bby\s+category\b|\bby\s+country\b|\bby\s+product\b|\bcategories\b|"
        r"сравни\w*|сравнен\w*|по\s+категори\w*|по\s+странам|по\s+стране|по\s+товарам|по\s+продукт\w*|категори\w*|"
        r"распределен\w*|дол\w*\s+категори\w*)",
        low,
    ))
    structured_3d_signal = bool(re.search(
        r"(?:\bxyz\b|координат\w*\s*(?:x\s*[,; ]+\s*y\s*[,; ]+\s*z|x\s*y\s*z)|"
        r"\bz\s*=\s*f\s*\(\s*x\s*[,;]\s*y\s*\)|"
        r"\bz\s*=\s*[^\n;]*(?:\bx\b[^\n;]*\by\b|\by\b[^\n;]*\bx\b)|"
        r"\b(?:surface\s+grid|surface\s+function|3d\s+data|spatial\s+coordinates)\b|"
        r"функци\w*\s+(?:двух|2)\s+перемен\w*|поверхност\w*\s+(?:график\w*|функци\w*)|"
        r"трехмерн\w*\s+данн\w*|пространствен\w*\s+координат\w*)",
        low,
    ))

    if explicit_3d:
        if re.search(r"(?:\bsphere\w*\b|\bcube\w*\b|\bpyramid\w*\b|\bcone\w*\b|\bcylinder\w*\b|\bobject\s+scene\b|\b3d\s+scene\b|сфер\w*|шар\w*|куб\w*|пирамид\w*|конус\w*|цилиндр\w*|объект\w*\s+сцен\w*|пространствен\w*\s+объект)", low):
            representation = "scene3d"
        elif re.search(r"(?:\bscatter\b|\bxyz\b|\bcoordinates\b|\bpoint\s+cloud\b|координат\w*|облак\w*\s+точек|пространствен\w*\s+точк)", low):
            representation = "scatter3d"
        else:
            # A 3D function/surface is the natural choice for explicit requests
            # such as an exponential function in 3D; the provider must supply z=f(x,y).
            representation = "surface3d"
        fallback = "bar" if explicit_bar or categorical_comparison else "line"
        return {
            "mode": "explicit_3d",
            "preferred_representation": representation,
            "fallback_representation": fallback,
            "allowed_2d_representations": ["line", "bar"],
            "allow_3d_for_explicit_request": True,
            "allow_3d_when_structured_data_exists": True,
            "require_real_third_dimension": True,
            "decision_reason": "explicit_3d_request",
        }

    if structured_3d_signal:
        if re.search(r"(?:\bxyz\b|координат\w*\s*(?:x\s*[,; ]+\s*y\s*[,; ]+\s*z)|облак\w*\s+точек|точечн\w*\s+облак\w*|scatter)", low):
            representation = "scatter3d"
        elif re.search(r"(?:сфер\w*|куб\w*|пространствен\w*\s+объект)", low):
            representation = "scene3d"
        else:
            representation = "surface3d"
        fallback = "bar" if explicit_bar or categorical_comparison else "line"
        return {
            "mode": "structured_3d_data",
            "preferred_representation": representation,
            "fallback_representation": fallback,
            "allowed_2d_representations": ["line", "bar"],
            "allow_3d_for_explicit_request": False,
            "allow_3d_when_structured_data_exists": True,
            "require_real_third_dimension": True,
            "decision_reason": "structured_3d_data_signal",
        }

    if explicit_bar:
        preferred = "bar"
        reason = "explicit_bar_request"
    elif explicit_line:
        preferred = "line"
        reason = "explicit_line_request"
    elif categorical_comparison:
        preferred = "bar"
        reason = "categorical_comparison"
    elif trend_or_time:
        preferred = "line"
        reason = "ordered_trend_or_explicit_line"
    else:
        # Generic graph requests remain 2D by default; Provider may switch between
        # line and bar when the actual returned data clearly favors one.
        preferred = "line"
        reason = "safe_2d_default"

    return {
        "mode": "adaptive_2d",
        "preferred_representation": preferred,
        "fallback_representation": preferred,
        "allowed_2d_representations": ["line", "bar"],
        "allow_3d_for_explicit_request": False,
        "allow_3d_when_structured_data_exists": bool(allow_data_driven_3d),
        "source_data_attachment_detected": bool(allow_data_driven_3d),
        "require_real_third_dimension": True,
        "decision_reason": "structured_source_attachment" if allow_data_driven_3d else reason,
    }


def _infer_routing_capabilities(text: str) -> list[str]:
    """Map obvious subject matter to registered C-ARTIFACT room capabilities."""
    low = _text(text).lower().replace("ё", "е")
    capabilities: list[str] = []
    rules = [
        (
            r"(?:\bwhere\s+do\s+i\s+(?:click|go|find|open)\b|\bhow\s+do\s+i\s+(?:navigate|get\s+to|open|return)\b|"
            r"\bhelp\s+me\s+(?:navigate|find|open)\b|\buser\s+interface\b|\bsite\s+navigation\b|\bmenu\b|\bsettings\b|"
            r"where.*(?:button|section|page|screen)|how.*(?:click|open|find)|"
            r"where.*(?:наж|кнопк|раздел|страниц|экран|перейти|вернут)|куда.*(?:наж|перейти|откры|зайти)|"
            r"как.*(?:найти|откры|перейти|вернут|выйти|купить|продлить)|помог.*(?:найти|перейти|откры|вернут)|"
            r"где.*(?:наход|кнопк|раздел|страниц|настройк)|интерфейс|навигац|меню|настройк|личн.*кабинет|"
            r"профил.*пользователя|потерял.*(?:страниц|раздел|чат)|запутал.*(?:сайт|раздел|настройк))",
            ("site_navigation", "april_site_help", "user_guidance", "interface_help", "april_site_navigation", "user_interface_help", "account_guidance"),
        ),
        (r"(?:\bbiology\b|\bdna\b|\bgene\w*\b|\bprotein\w*\b|\bcell\w*\b|\bevolution\b|биолог\w*|днк|ген\w*|белок\w*|клетк\w*|эволюц\w*|организм\w*)", ("biology", "research", "knowledge")),
        (r"(?:\bpython\b|\btypescript\b|\bjavascript\b|\bapi\b|\bgit\b|\bdatabase\b|\bserver\b|\bdeploy\w*\b|\bsoftware\b|\bcode\b|\bpostgres(?:ql)?\b|\bsqlite\b|\bmysql\b|\bredis\b|\bkubernetes\b|программ\w*|код\w*|разработ\w*|баз\w*\s+данн\w*|сервер\w*|депло\w*|репозитор\w*)", ("software", "code", "git", "analysis")),
        (r"(?:\bliterature\b|\bnovel\b|\bpoem\b|\bpoetry\b|\bauthor\b|\bbook\b|литератур\w*|роман\w*|поэм\w*|стих\w*|автор\w*|книг\w*)", ("literature", "authors", "literary_analysis")),
        (r"(?:\btrigonometry\b|\bsin\b|\bcos\b|\btan\b|\bcot\b|тригонометр\w*|синус\w*|косинус\w*|тангенс\w*)", ("trigonometry", "calculation", "geometry")),
        (r"(?:\bmathematics\b|\bcalculate\b|\bcalculation\b|\bsolve\s+(?:for|the)\b|\bequation\b|\bexponential\b|\bfunction\b|математ\w*|вычисл\w*|посчитай\w*|уравнен\w*|экспонент\w*|функци\w*|числов\w*|производн\w*|интеграл\w*)", ("mathematics", "calculation", "reasoning", "function", "mathematical_function")),
        (r"(?:\bnews\b|\blatest\s+(?:events|news)\b|\bcurrent\s+events\b|новост\w*|последн\w*\s+событи\w*|актуальн\w*\s+событи\w*)", ("news", "current_events")),
        (r"(?:\bpolitic\w*\b|\belection\w*\b|\bgovernment\b|\bparliament\b|политик\w*|выбор\w*|правительств\w*|парламент\w*|президент\w*)", ("politics", "current_events")),
        (r"(?:\bsocial\s+(?:behavior|relations|issues)\b|\bsociety\b|\bcommunication\b|социолог\w*|социальн\w*|общественн\w*\s+отношен\w*|общение\w*|коммуникац\w*)", ("social", "communication")),
        (r"(?:\b(?:utc|time\s+zone|timezone|current\s+time|date\s+and\s+time)\b|часов\w*\s+пояс\w*|время\s+в\s+[а-яa-z]|текуще\w*\s+время|дата\s+и\s+время)", ("utc", "time", "datetime")),
    ]
    for pattern, values in rules:
        if re.search(pattern, low):
            capabilities.extend(values)
    if _infer_april_ui_semantics(text):
        capabilities.extend(("site_navigation", "april_site_help", "user_guidance", "interface_help", "april_site_navigation", "user_interface_help", "account_guidance"))
    return list(dict.fromkeys(capabilities))


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
        # The requested image supplements a compound answer; it must not replace
        # an explanation, code sample, table or diagram with an image-only response.
        asks_for_explanation = bool(re.search(
            r"(?:расскаж\w*|объясн\w*|напиш\w*|опиш\w*|привед\w*|перечисл\w*|сравн\w*|разбер\w*|проанализир\w*|"
            r"\btell\b|\bexplain\b|\bwrite\b|\bdescribe\b|\blist\b|\bcompare\b|\banaly[sz]e\b)",
            low,
            re.IGNORECASE,
        ))
        asks_for_other_renderer = bool(re.search(
            r"(?:таблиц\w*|\btable\b|график\w*|диаграмм\w*|схем\w*|черт[её]ж\w*|"
            r"формул\w*|уравнен\w*|код\w*|\bcode\b|ссылк\w*|\blink\b|презентац\w*|\breport\b|\bexamples?\b|пример\w*)",
            low,
            re.IGNORECASE,
        ))
        if not asks_for_explanation and not asks_for_other_renderer:
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
    'о чем мы говорили',
    'о чём мы говорили',
    'что мы обсуждали',
    'какие темы мы обсуждали',
    'история диалога',
    'история разговора',
    'про що ми говорили',
    'що ми обговорювали',
    'які теми ми обговорювали',
    'історія діалогу',
    'історія розмови',
    'what did we talk about',
    'what did we discuss',
    'conversation history',
    'topics we discussed',
    'remind me what we discussed',
    'de qué hablamos',
    'de que hablamos',
    'qué discutimos',
    'que discutimos',
    'historial de conversación',
    'historial de conversacion',
    'recuérdame los temas',
    'recuerdame los temas',
    'worüber haben wir gesprochen',
    'woruber haben wir gesprochen',
    'was haben wir besprochen',
    'gesprächsverlauf',
    'gesprachsverlauf',
    'de quoi avons-nous parlé',
    'de quoi avons nous parlé',
    'historique de conversation',
    'rappelle-moi les sujets',
    'di cosa abbiamo parlato',
    'di cosa abbiamo discusso',
    'cronologia della conversazione',
    'o czym rozmawialiśmy',
    'o czym rozmawialismy',
    'co omawialiśmy',
    'co omawialismy',
    'historia rozmowy',
    'sobre o que conversamos',
    'sobre o que falamos',
    'o que discutimos',
    'histórico da conversa',
    'historico da conversa',
    'waar hebben we over gesproken',
    'wat hebben we besproken',
    'gespreksgeschiedenis',
)

def _is_attachment_tutorial_request(text: Any) -> bool:
    """Recognize instructions for attaching a source image to the chat."""
    low = _text(text).lower().replace("ё", "е")
    has_howto = bool(re.search(r"(?:как|расскажи|объясни|подскажи|покажи|how\s+to|explain\s+how|show\s+me\s+how)", low))
    has_attach = bool(re.search(r"(?:добав\w*|прикреп\w*|загруз\w*|выбрат\w*|attach\w*|upload\w*|add\w*|select\w*)", low))
    has_media = bool(re.search(r"(?:картинк\w*|изображени\w*|фото\b|фотограф\w*|снимк\w*|picture\w*|image\w*|photo\w*)", low))
    in_chat = bool(re.search(r"(?:в\s+(?:тво[её]м\s+)?(?:пространств\w*|чат\w*|переписк\w*)|чтобы\s+(?:ты|април\w*)\s+(?:увид\w*|получил\w*|прочитал\w*)|in\s+(?:the\s+)?chat|so\s+(?:you|april)\s+can\s+(?:see|read))", low))
    edits_existing = bool(re.search(r"(?:добав\w*.{0,55}\b(?:евро|гривн|надпис|стрелк|сумм)\b|на\s+(?:эту\s+|этой\s+|эту\s+)?(?:фот\w*|картинк\w*|изображени\w*)|(?:редактир\w*|измени\w*|дорисуй|убери)\s+(?:это\s+)?(?:фото|картинк|изображени))", low, re.I | re.S))
    return has_howto and has_attach and has_media and in_chat and not edits_existing


_SITE_NAVIGATION_REQUEST_RE = re.compile(
    r"(?:\bгде\b.{0,90}\b(?:вход|кнопк|ссылк|раздел|страниц|находится|расположен|открыть|посмотреть|найти|зайти)\b|"
    r"\bкуда\b.{0,45}\b(?:зайти|нажать|перейти|открыть)\b|"
    r"\bкак\b.{0,85}\b(?:попасть|пройти|добраться|зайти|открыть|перейти|найти|просмотреть|пользоваться|воспользоваться)\b|"
    r"(?:покажи|подскажи|объясни|расскажи).{0,75}(?:куда|путь|интерфейс|меню|как\s+(?:попасть|пройти|зайти|открыть|перейти|найти)|на\s+картинк|на\s+изображен|по\s+шагам)|"
    r"проведи.{0,55}(?:интерфейс|сайт|раздел)|"
    r"(?:where\s+(?:is|can\s+i|do\s+i)|how\s+do\s+i\s+(?:open|find|navigate)|show\s+me\s+where)"
    r")",
    re.IGNORECASE | re.DOTALL,
)
_SITE_NAVIGATION_TARGET_RE = re.compile(
    r"(?:сообществ|community|истори\w*\s+диалог|saved\s+dialogues?|history|"
    r"кабинет|профил|настройк|settings|account|help\s+center|справк|support|поддержк|"
    r"тариф|premium|памят|удален\w*\s+аккаунт|privacy\s+policy|terms\s+of\s+service|"
    r"отблагодар\w*|поблагодар\w*|пожалова\w*|жалоб\w*|feedback|report\s+(?:button|response|answer)|thank(?:s|ing)?\s+button|"
    r"кнопк\w*|значок|иконк\w*|квадрат|скрепк\w*|метл\w*|микрофон|стрелк\w*|"
    r"язык\w*|language|имя\s+в\s+чате|display\s+name|april\s*id|premium\s*id|current\s+plan|"
    r"invite\s+friend|add\s+friend|search\s+friends|добав\w*\s+друг|поиск\s+друз|"
    r"заявк\w*\s+в\s+поддержк|обращен\w*\s+в\s+поддержк|support\s+ticket|"
    r"message\s+april|поле\s+сообщен|рабоч\w*\s+поле|clear\s+workspace|"
    r"чат|ответ\s+april|сообщен\w*\s+april|график\w*|таблиц\w*|код\w*|изображен\w*|файл\w*)",
    re.IGNORECASE,
)

_UI_CONTROL_EXPLANATION_RE = re.compile(
    r"(?:что\s+(?:делает|значит|показывает|это\s+за)|зачем\s+(?:нужна|нужен|нужно)|для\s+чего|"
    r"объясни(?:те)?|расскажи(?:те)?|what\s+(?:does|is)|what\s+is\s+it\s+for)",
    re.IGNORECASE,
)
_UI_CONTROL_TROUBLE_RE = re.compile(
    r"(?:не\s+(?:нажимается|работает|реагирует|открывается|срабатывает|активируется)|"
    r"не\s+могу\s+(?:нажать|открыть|перейти|отправить)|"
    r"кнопк\w*.{0,45}(?:неактивн|серая|серый|заблокир|не\s+работ|не\s+реагир)|"
    r"(?:disabled|not\s+clickable|doesn't\s+work|does\s+not\s+respond|button\s+is\s+grey))",
    re.IGNORECASE | re.DOTALL,
)


def _infer_april_ui_semantics(value: Any) -> dict[str, Any]:
    """Resolve a user-facing April UI request into a route and exact control family."""
    source = _text(value).strip()
    low = source.lower().replace("ё", "е")
    if not low or _has_direct_non_ui_output_action(low):
        return {}

    action = "GUIDE_UI_ACTION"
    target = "verified_site_map"
    route = "/"
    guidance_mode = "step_by_step"
    function_ids: list[str] = []
    related_targets: list[str] = []
    screen_id = "chat_home"

    # Video how-to questions are a navigation task in the chat composer, not a
    # request to generate a video. Keep direct creation verbs on the media path.
    video_noun = bool(re.search(r"(?:\bvideo\b|\bvideos\b|\bclip\b|\bclips\b|видео\w*|ролик\w*)", low, re.I))
    direct_video_creation = bool(re.search(
        r"^\s*(?:создай(?:те)?|сгенерируй(?:те)?|сгенерировать|оживи(?:те)?|анимируй(?:те)?|generate|create|make)\b.{0,45}(?:\bvideo\b|\bclip\b|виде\w*|ролик\w*)",
        low, re.I,
    ))
    video_howto = video_noun and not direct_video_creation and bool(re.search(
        r"(?:как\b|подскажи|помоги|объясни|расскажи|можно\s+ли|куда\s+нажать|how\b|help\s+me|show\s+me|can\s+i|where\s+do\s+i)",
        low, re.I,
    ))

    if video_howto:
        action, target, route, guidance_mode = "GUIDE_ATTACH_IMAGE", "chat.paperclip_picker", "/", "step_by_step"
        function_ids = ["chat_attach_file", "chat_attachment_picker_controls", "chat_text_send"]
        screen_id = "chat_home"
    elif _is_video_workflow_navigation(source) and not _has_direct_video_generation_action(source):
        action, target, route, guidance_mode = "GUIDE_ATTACH_IMAGE", "chat.paperclip_picker", "/", "step_by_step"
        function_ids = ["chat_attach_file", "chat_attachment_picker_controls", "chat_text_send"]
        screen_id = "chat_home"
    elif _is_attachment_tutorial_request(source):
        action, target, route, guidance_mode = "GUIDE_ATTACH_IMAGE", "chat.paperclip_picker", "/", "step_by_step"
        function_ids = ["chat_attach_file", "chat_attachment_picker_controls", "chat_text_send"]
        screen_id = "chat_home"
    elif re.search(r"(?:поддержк\w*|support).{0,65}(?:истори\w*|предыдущ\w*|прошл\w*|тикет\w*|обращен\w*)|(?:истори\w*|предыдущ\w*|прошл\w*|откры\w*).{0,65}(?:поддержк\w*|support|тикет\w*|обращен\w*)", low, re.I):
        target, route, screen_id = "support.thread", "/insights?room=support", "support_room"
        function_ids = ["support_thread_select", "support_history_view"]
    elif re.search(r"(?:поддержк\w*|support).{0,65}(?:скриншот\w*|снимок\s+экрана)|(?:скриншот\w*|снимок\s+экрана).{0,65}(?:поддержк\w*|support)", low, re.I):
        target, route, screen_id = "support.attach_screenshot", "/insights?room=support", "support_room"
        function_ids = ["support_attach_screenshot", "support_new_request"]
    elif re.search(r"(?:заявк\w*|обращен\w*|тикет\w*|ticket).{0,50}(?:поддержк\w*|support)|(?:поддержк\w*|support).{0,60}(?:заявк\w*|обращен\w*|тикет\w*|ticket)", low, re.I):
        target, route, screen_id = "support.request", "/insights?room=support", "support_room"
        function_ids = ["support_new_request", "support_send_ticket"]
    elif re.search(r"(?:сменить|изменить|поменять|выбрать|настроить).{0,40}(?:язык|language)|(?:язык|language).{0,40}(?:сменить|изменить|поменять|выбрать)", low, re.I):
        target, route, screen_id = "profile.language", "/settings", "settings_profile"
        function_ids = ["settings_language"]
    elif re.search(r"(?:истори\w*\s+диалог|истори\w*\s+бесед|saved\s+dialogues?|conversation\s+history|history\s+page)", low, re.I):
        action, target, route, screen_id = "EXPLAIN_UI_ROUTE", "dialogue_history", "/history", "history_list"
        function_ids = ["history_resume"]
    elif re.search(r"(?:добав\w*.{0,35}друг|найти\w*.{0,35}(?:друг|пользоват)|поиск\w*.{0,35}(?:друз|участник)|add\s+friend|search\s+friends)", low, re.I):
        target, route, screen_id = "community.friends", "/space", "community_feed"
        function_ids = ["community_search_members", "community_friend_manage"]
    elif re.search(r"(?:приглас\w*.{0,35}друг|invite\s+(?:a\s+)?friend)", low, re.I):
        target, route, screen_id = "community.invite", "/space", "community_feed"
        function_ids = ["community_invite_friend", "community_invite"]
    elif re.search(r"(?:community|сообществ\w*).{0,65}(?:ник\w*|nickname|личн\w* профил)|(?:ник\w*|nickname|личн\w* профил).{0,65}(?:community|сообществ\w*)", low, re.I):
        target, route, screen_id = "community.personal_profile", "/space", "community_feed"
        function_ids = ["community_personal_profile", "community_profile_toggle"]
    elif re.search(r"(?:community|сообществ\w*).{0,75}(?:удал\w*|пожалова\w*|жалоб\w*|report|delete).{0,45}(?:пост\w*|сообщен\w*|публикац\w*)|(?:удал\w*|пожалова\w*|жалоб\w*|report|delete).{0,45}(?:пост\w*|сообщен\w*|публикац\w*).{0,65}(?:community|сообществ\w*)", low, re.I):
        target, route, screen_id = "community.post_actions", "/space", "community_feed"
        function_ids = ["community_post_actions", "community_delete_post", "community_report_post"]
    elif re.search(r"(?:созда\w*|написа\w*|опубликова\w*|размест\w*|post|publish).{0,55}(?:пост\w*|сообщен\w*|публикац\w*).{0,55}(?:community|сообществ\w*)|(?:community|сообществ\w*).{0,55}(?:созда\w*|написа\w*|опубликова\w*|размест\w*|post|publish)", low, re.I):
        target, route, screen_id = "community.public_post", "/space", "community_feed"
        function_ids = ["community_public_post"]
    elif re.search(r"(?:личн\w*\s+чат|приватн\w*\s+чат|private\s+chat|direct\s+message)", low, re.I):
        target, route, screen_id = "community.private_chat", "/space", "community_feed"
        function_ids = ["community_private_chat", "direct_chat_controls"]
    elif re.search(r"(?:метл\w*|clear\s+workspace|очист\w*.{0,40}(?:чат|рабоч\w*\s+пол\w*|видим\w*\s+сообщен)|очистить\s+чат)", low, re.I):
        target, route, screen_id = "chat.clear_workspace", "/", "chat_home"
        function_ids = ["chat_clear_workspace"]
    elif re.search(r"(?:скрепк\w*|прикреп\w*|вложен\w*|attach\s+(?:a\s+)?file|paperclip|upload\s+(?:a\s+)?file)", low, re.I):
        action, target, route, screen_id = "GUIDE_ATTACH_IMAGE", "chat.paperclip_picker", "/", "chat_home"
        function_ids = ["chat_attach_file", "chat_attachment_picker_controls"]
    elif re.search(r"(?:микрофон|голос\w*|voice\s+(?:input|message))", low, re.I):
        target, route, screen_id = "chat.voice_input", "/", "chat_home"
        function_ids = ["chat_voice_input"]
    elif re.search(r"(?:создать|отправить|написать|подать).{0,50}(?:заявк\w*|обращен\w*|тикет\w*)", low, re.I) and re.search(r"(?:поддержк\w*|support)", low, re.I):
        target, route, screen_id = "support.request", "/insights?room=support", "support_room"
        function_ids = ["support_new_request", "support_send_ticket"]
    elif re.search(r"(?:имя\s+в\s+чате|отображаем\w*\s+имя|display\s*name|поменять\s+имя|изменить\s+имя)", low, re.I):
        target, route, screen_id = "profile.display_name", "/settings", "settings_profile"
        function_ids = ["settings_display_name"]
    elif re.search(r"(?:april\s*id|premium\s*id|идентификатор\w*)", low, re.I):
        target, route, screen_id = "profile.identifiers", "/settings", "settings_profile"
        function_ids = ["settings_copy_ids"]
    elif re.search(r"(?:выйти\s+из\s+(?:аккаунт\w*|учетн\w*\s+запис\w*)|выход\s+из\s+аккаунт\w*|log\s*out|sign\s*out)", low, re.I):
        target, route, screen_id = "profile.logout", "/settings", "settings_profile"
        function_ids = ["settings_logout"]
    elif re.search(r"(?:купить|оплатить|продлить|пакет\w*|premium|премиум|тариф\w*)", low, re.I) and re.search(r"(?:april|април|у\s+тебя|в\s+приложени\w*|где|как)", low, re.I):
        target, route, screen_id = "profile.plan", "/settings", "settings_profile"
        function_ids = ["settings_plan_payment", "settings_premium_packages"]
    elif re.search(r"(?:настройк\w*|профил\w*|личн\w*\s+кабинет|settings|profile)", low, re.I):
        action, target, route, screen_id = "EXPLAIN_UI_ROUTE", "profile.settings", "/settings", "settings_profile"
        function_ids = ["settings_language", "settings_display_name", "settings_plan_payment"]
    elif re.search(r"(?:поддержк\w*|contact\s+support|support\s+page)", low, re.I):
        action, target, route, screen_id = "EXPLAIN_UI_ROUTE", "support.request", "/insights?room=support", "support_room"
        function_ids = ["support_new_request", "support_send_ticket", "support_history_view"]
    elif re.search(r"(?:help\s*&\s*information|справк\w*|центр\s+помощи|how\s+to\s+use)", low, re.I):
        action, target, route, screen_id = "EXPLAIN_UI_ROUTE", "april.help_information", "/aprill", "help_information"
        function_ids = ["help_article_navigation", "help_topic_cards", "help_topic_back_controls"]
    elif re.search(r"(?:удал\w*.{0,35}аккаунт|delete\s+(?:my\s+)?account)", low, re.I):
        action, target, route, screen_id = "EXPLAIN_UI_ROUTE", "account.delete", "/account-deletion", "account_deletion"
        function_ids = ["account_delete", "account_deletion_controls"]
    elif re.search(r"(?:privacy\s+policy|конфиденциальност\w*)", low, re.I):
        action, target, route, screen_id = "EXPLAIN_UI_ROUTE", "legal.privacy", "/privacy-policy", "privacy_policy"
        function_ids = ["help_static_legal_pages"]
    elif re.search(r"(?:terms\s+of\s+service|услови\w*\s+использован)", low, re.I):
        action, target, route, screen_id = "EXPLAIN_UI_ROUTE", "legal.terms", "/terms-of-service", "terms_of_service"
        function_ids = ["help_static_legal_pages"]
    elif re.search(r"(?:зел\w*.{0,25}(?:стрелк\w*|кнопк\w*)|опубликов\w*.{0,40}сообществ|share.{0,30}community)", low, re.I):
        target, route, screen_id = "response.share_to_community", "/", "chat_home"
        function_ids = ["assistant_response_share"]
    elif re.search(r"(?:жалоб\w*|пожалова\w*|спасибо\s+под\s+ответ|report\s+(?:answer|response)|thank\s+button)", low, re.I):
        target, route, screen_id = "response.feedback", "/", "chat_home"
        function_ids = ["response_feedback"]
    elif re.search(r"(?:график\w*|graph).{0,50}(?:кнопк\w*|ракурс|масштаб|показать\s+данн)|(?:кнопк\w*|ракурс|масштаб).{0,50}(?:график\w*|graph)", low, re.I):
        target, route, screen_id = "rendered_graph.controls", "/", "render_graph"
        function_ids = ["rendered_graph_controls"]
    elif re.search(r"(?:таблиц\w*|table).{0,50}(?:скача\w*|сортир\w*|копир\w*)", low, re.I):
        target, route, screen_id = "render.table", "/", "render_table"
        function_ids = ["render_table_controls"]
    elif re.search(r"(?:код\w*|code).{0,50}(?:копир\w*|скача\w*)", low, re.I):
        target, route, screen_id = "render.code", "/", "render_code"
        function_ids = ["render_code_copy"]
    elif re.search(r"(?:откры\w*|развер\w*|увелич\w*|на\s+весь\s+экран|fullscreen|full\s*screen).{0,45}(?:изображен\w*|картинк\w*|фото|image|picture)|(?:изображен\w*|картинк\w*|фото|image|picture).{0,45}(?:на\s+весь\s+экран|fullscreen|full\s*screen)", low, re.I):
        target, route, screen_id = "render.gallery", "/", "render_gallery"
        function_ids = ["render_gallery_controls", "rendered_artifact_menu"]
    elif re.search(r"(?:откры\w*|развер\w*|увелич\w*|закры\w*|open|expand|close).{0,45}(?:svg|схем\w*|диаграмм\w*|diagram)", low, re.I):
        target, route, screen_id = "render.diagram", "/", "render_diagram_link_video"
        function_ids = ["render_diagram_expand"]
    elif re.search(r"(?:откры\w*|перейти\s+по|нажать|open|follow).{0,45}(?:ссылк\w*|link|linkcard)", low, re.I):
        target, route, screen_id = "render.link", "/", "render_diagram_link_video"
        function_ids = ["render_link_open"]
    elif re.search(r"(?:скача\w*|сохран\w*|поделит\w*|download|save|share).{0,40}(?:изображен\w*|картинк\w*|фото|image|picture)", low, re.I):
        target, route, screen_id = "render.gallery", "/", "render_gallery"
        function_ids = ["render_gallery_controls", "rendered_artifact_menu"]

    troubleshooting = bool(_UI_CONTROL_TROUBLE_RE.search(low)) and bool(re.search(
        r"(?:кнопк\w*|значок|иконк\w*|квадрат|переключател|скрепк\w*|метл\w*|микрофон|стрелк\w*|button|icon|toggle)", low, re.I,
    ))
    if troubleshooting:
        guidance_mode = "troubleshoot"
        if function_ids:
            action = "GUIDE_UI_ACTION"
        elif target == "verified_site_map":
            action, target, route, screen_id = "GUIDE_UI_ACTION", "chat.ui_control_troubleshooting", "unspecified", "unknown_ui_context"
            related_targets = ["chat.ui_control_troubleshooting"]

    explicit_overview = bool(re.search(
        r"(?:полна\w*|весь|все|всю|кажд\w*|карт\w*|структур\w*|обзор\w*|перечисл\w*).{0,80}(?:интерфейс\w*|сайт\w*|экран\w*|страниц\w*|раздел\w*|функци\w*)|"
        r"(?:full|complete|entire|whole|overview|site\s+map).{0,80}(?:april\s+)?(?:interface|site|website|screens?|pages?|navigation|ui)", low, re.I,
    ))
    # "На весь экран" means expand one rendered item, not a full-site overview.
    if re.search(r"(?:на\s+весь\s+экран|full\s*screen|fullscreen)", low, re.I) and re.search(
        r"(?:откры\w*|развер\w*|увелич\w*|open|expand|zoom).{0,55}(?:изображен\w*|картинк\w*|фото|svg|схем\w*|диаграмм\w*|график\w*|image|picture|diagram|graph)",
        low, re.I,
    ):
        explicit_overview = False
    if explicit_overview:
        action, target, route, guidance_mode = "EXPLAIN_UI_ROUTE", "verified_site_map", "/", "overview"
        function_ids = []
        screen_id = "complete_site_inventory"

    has_explicit_ui_target = bool(_SITE_NAVIGATION_TARGET_RE.search(low))
    should_route = bool(
        _is_attachment_tutorial_request(source)
        or (_is_video_workflow_navigation(source) and not _has_direct_video_generation_action(source))
        or explicit_overview
        or bool(function_ids)
        or troubleshooting
        or (_UI_CONTROL_EXPLANATION_RE.search(low) and has_explicit_ui_target)
        or _SITE_NAVIGATION_REQUEST_RE.search(low)
        or any(term in low for term in ("метла", "скрепка", "микрофон", "язык интерфейса", "current plan"))
    )
    if not should_route:
        return {}
    if function_ids and not related_targets:
        related_targets = [target]
    return {
        "schema": "april.site_navigation_semantics.v1",
        "domain": "april_ui",
        "action": action,
        "target": target,
        "user_goal": source[:1000],
        "ui_navigation": {
            "target": target,
            "targets": related_targets or [target],
            "route": route,
            "starting_route": route,
            "screen_id": screen_id,
            "guidance_mode": guidance_mode,
            "candidate_function_ids": function_ids,
            "required_steps": True,
            "expected_result_required": True,
            "ask_for_screenshot_when_unresolved": guidance_mode == "troubleshoot",
            "current_screen_unresolved": screen_id == "unknown_ui_context",
        },
        "confidence": 0.99 if function_ids or explicit_overview else 0.88,
        "source": "interpretation_ui_intent_rules_v1",
    }


def _is_site_navigation_request(text: Any) -> bool:
    """True for April UI walkthroughs, control explanations and safe troubleshooting."""
    source = _text(text).strip()
    if not source:
        return False
    low = source.lower().replace("ё", "е")
    if _is_attachment_tutorial_request(source):
        return True
    if _is_video_workflow_navigation(source) and not _has_direct_video_generation_action(source):
        return True
    if _has_direct_non_ui_output_action(low):
        return False
    # A typed route/control result is more reliable than the broad lexical gate.
    # _infer_april_ui_semantics does not call this function, so this is not recursive.
    if _infer_april_ui_semantics(source):
        return True
    if _UI_CONTROL_TROUBLE_RE.search(low) and re.search(
        r"(?:кнопк\w*|значок|иконк\w*|квадрат|переключател|скрепк\w*|метл\w*|микрофон|стрелк\w*|button|icon|toggle)", low, re.I,
    ):
        return True
    if _UI_CONTROL_EXPLANATION_RE.search(low) and _SITE_NAVIGATION_TARGET_RE.search(low):
        return True
    if not _SITE_NAVIGATION_TARGET_RE.search(low):
        return False
    return bool(_SITE_NAVIGATION_REQUEST_RE.search(low) or re.search(r"(?:язык\w*|скрепк\w*|метл\w*|микрофон)", low, re.I))


_HISTORY_COUNTS = {
    "один": 1, "одну": 1, "два": 2, "две": 2, "три": 3, "четыре": 4,
    "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10,
}


def _semantic_normalize(text: Any) -> tuple[str, list[str]]:
    """Normalize user wording for intent analysis without rewriting the request."""
    low = _text(text).lower().replace("ё", "е")
    low = re.sub(r"[^\w\u0080-\uffff]+", " ", low, flags=re.UNICODE)
    low = re.sub(r"\s+", " ", low).strip()
    return low, [token for token in low.split(" ") if token]


_SEMANTIC_ROOTS = {
    "dialogue_action": ("говор", "обсужд", "разговар", "разговор", "обща", "общен", "перепис", "упомин", "затраг", "диалог", "реч", "dialogue", "conversation", "discuss", "talk", "talked", "talking", "chat", "communicat", "speech"),
    "recall_action": ("напом", "вспом", "припомн", "восстанов", "remember", "recall", "remind", "summariz", "перескаж", "перечисл"),
    "decision_action": ("решил", "решен", "вывод", "итог", "договор", "результат", "concluded", "decided", "decision", "outcome"),
    "plan_action": ("план", "заплан", "собира", "намер", "предусмотр", "planned", "plan", "schedule"),
    "continuation_action": ("продолж", "продовж", "вернись", "повер", "возвращ", "останов", "resume", "continue", "continu", "sigamos", "volvamos", "fortsetz", "weiter", "poursuiv", "repren", "riprend", "kontynu", "wroc", "wróc", "voltem", "doorgaan", "verder", "herneem", "return to"),
    "past_reference": ("предыдущ", "прошл", "раньше", "ранее", "истори", "прошедш", "yesterday", "previous", "earlier", "before", "history"),
    "future_reference": ("завтра", "будущ", "следующ", "потом", "дальнейш", "tomorrow", "future", "next"),
    "today_reference": ("сегодня", "сегодн", "сегодняшн", "утром", "вечером", "today", "this morning", "tonight"),
    "recent_reference": ("недавн", "последн", "сейчас", "недавно", "за день", "recent", "lately", "last few", "last 12"),
}

_SEMANTIC_FUZZY_FORMS = {
    "dialogue_action": ("говорили", "говорил", "обсуждали", "обсудили", "разговаривали", "общались", "переписывались", "общение", "разговор", "discussed", "discussion", "talked", "talking", "conversation", "communicate"),
    "recall_action": ("напомни", "напомнить", "вспомни", "вспомнить", "припомни", "восстанови", "summarize", "remember", "recall"),
    "decision_action": ("решили", "решились", "выводы", "итоги", "договорились", "результаты", "decided", "concluded"),
    "plan_action": ("планировали", "запланировали", "собирались", "намеревались", "planned", "schedule"),
    "past_reference": ("предыдущий", "предыдущем", "прошлый", "прошлом", "раньше", "yesterday", "previous", "earlier"),
    "future_reference": ("завтра", "будущее", "следующий", "следующим", "tomorrow", "future", "next"),
    "today_reference": ("сегодня", "сегодняшний", "сегодняшнего", "утром", "вечером", "today", "tonight"),
}


def _semantic_group_hit(tokens: list[str], group: str) -> bool:
    roots = _SEMANTIC_ROOTS.get(group, ())
    for token in tokens:
        if any(
            (token == root) or (len(root) >= 5 and token.startswith(root))
            for root in roots if " " not in root
        ):
            return True
    forms = _SEMANTIC_FUZZY_FORMS.get(group, ())
    for token in tokens:
        if len(token) < 5:
            continue
        for form in forms:
            if abs(len(token) - len(form)) > 2:
                continue
            if SequenceMatcher(None, token, form).ratio() >= 0.83:
                return True
    return False


_CONTEXT_SIGNATURE_GENERIC = {
    # Operations, presentation forms, units and generic data words are not subjects.
    # Participant pronouns and discourse-management wording describe the relation
    # between turns, not a new external subject. Keep them in the full request for
    # semantic interpretation, but exclude them from the topical signature.
    "я", "меня", "мне", "мной", "мой", "моя", "мое", "моё", "мои", "моих", "моему",
    "ты", "тебя", "тебе", "тобой", "твой", "твоя", "твое", "твоё", "твои", "твоих",
    "мы", "нас", "нам", "нами", "наш", "наша", "наше", "наши", "вы", "вас", "вам",
    "i", "me", "my", "mine", "myself", "you", "your", "yours", "yourself", "we", "us", "our", "ours",
    "имя", "имени", "именем", "зовут", "называют", "называюсь", "называешься",
    "помнить", "помню", "помнишь", "помнил", "помнила", "помним", "запомнить", "запомни",
    "напомнить", "напомнил", "напомнила", "напомни", "вспомнить", "вспомни",
    "потерял", "потеряла", "потеряли", "забыл", "забыла", "забыли", "контекст", "контексте",
    "случилось", "произошло", "произошел", "произошёл", "произошла", "диалог", "разговор", "беседа",
    "напиши", "написать", "напишите", "опиши", "описать", "опишите", "расскажи", "расскажите",
    "объясни", "объяснить", "объясните", "поясни", "пояснить", "покажи", "построй", "создай",
    "решил", "решила", "решили", "научно", "пошагово", "решать",
    "сделай", "вычисли", "рассчитай", "сравни", "найди", "проверь", "проанализируй", "приведи",
    "перечисли", "продолжи", "продолжим", "дальше", "далее", "есть", "какие", "какая", "какой",
    "должен", "должна", "должно", "должны", "был", "была", "были", "нет",
    "покажи", "показать", "покажите", "построй", "построить", "постройте",
    "сделай", "сделать", "сделайте", "создай", "создать", "исправь", "исправить",
    "данные", "данных", "значение", "значения", "число", "числа", "точка", "точки",
    "график", "графика", "графике", "диаграмма", "диаграммы", "таблица", "таблицу",
    "таблице", "формула", "формулы", "цена", "цены", "цену", "цене", "стоимость",
    "рост", "роста", "растет", "растёт", "падение", "падения", "изменение",
    "начинался", "начинались", "начинается", "начинаются", "начало", "сначала",
    "заканчивался", "заканчивались", "конец", "поменяй", "поменять", "изменить",
    "день", "дня", "дней", "днями", "неделя", "неделю", "недели", "месяц",
    "месяца", "месяцев", "год", "года", "грн", "руб", "рубль", "рубля",
    "доллар", "доллара", "долларов", "евро", "по", "для", "этот", "эта", "эти",
    "это", "тот", "та", "те", "такой", "такую", "такие", "данный", "данная",
    "данное", "данные", "мои", "мне", "теперь", "также", "ещё", "еще", "и", "а",
    "the", "this", "that", "these", "those", "show", "build", "create", "make",
    "fix", "correct", "data", "value", "values", "chart", "graph", "table",
    "formula", "price", "cost", "growth", "fall", "day", "days", "week", "weeks",
    "month", "months", "year", "years", "uah", "uah.", "usd", "dollar", "dollars",
}
_CONTEXT_SIGNATURE_REFERENCES = {
    "это", "этого", "этой", "этом", "эту", "этот", "эта", "эти", "этих",
    "тот", "та", "ту", "те", "того", "той", "тех", "данный", "данная", "данное",
    "он", "она", "оно", "они", "его", "ее", "ему", "ей", "им", "них", "их",
    "него", "нее", "ней", "ним", "those", "these", "that", "this", "it", "he",
    "she", "they", "him", "her", "them", "its", "same", "previous", "earlier",
    "еще", "ещё", "дальше",
}
_CONTEXT_OUTPUT_TERMS = {
    "graph": {"graph", "chart", "plot", "график", "диаграмм"},
    "table": {"table", "таблиц"},
    "formula": {"formula", "формул", "уравнен"},
    "image": {"image", "picture", "photo", "картинк", "изображен", "фото"},
}

_CONTEXT_SIGNATURE_DISCOURSE_ROOTS = (
    "называ", "зовут", "помн", "запом", "напом", "вспом", "потер", "забыл",
    "контекст", "случил", "произош", "диалог", "разговор", "бесед", "обращ",
    "напиш", "опиш", "расскаж", "объясн", "поясн", "покаж", "постро", "созда",
    "сдела", "вычисл", "рассчит", "сравн", "найд", "проверь", "проанализ", "привед",
    "перечисл", "продолж", "дальш", "должн", "каки", "был",
    "придум", "предложи", "почем", "почему", "зачем", "открыл", "изобрел", "изобрёл",
    "доказал", "обосновал", "считал", "называл", "формул", "график", "таблиц",
    "диаграмм", "уравнен", "данн", "значен",
)

_PARTICIPANT_SPEAKER_WORDS = {
    "я", "меня", "мне", "мной", "мой", "моя", "мое", "моё", "мои", "мой", "моего", "моей", "моей",
    "i", "me", "my", "mine", "myself", "мені", "мій", "моя", "моє", "мої",
}
_PARTICIPANT_INTERLOCUTOR_WORDS = {
    "ты", "тебя", "тебе", "тобой", "твой", "твоя", "твое", "твоё", "твои", "твоего", "твоей",
    "you", "your", "yours", "yourself", "тобі", "тебе", "твій", "твоя", "твоє", "твої",
}
_PARTICIPANT_SHARED_WORDS = {"мы", "нас", "нам", "нами", "наш", "наша", "наше", "наши", "we", "us", "our", "ours"}


def _is_context_signature_generic(token: str) -> bool:
    if token in _CONTEXT_SIGNATURE_GENERIC:
        return True
    return any(len(root) >= 5 and token.startswith(root) for root in _CONTEXT_SIGNATURE_DISCOURSE_ROOTS)


def _participant_reference_profile(tokens: list[str]) -> dict[str, bool]:
    token_set = set(tokens)
    speaker = bool(token_set & _PARTICIPANT_SPEAKER_WORDS)
    interlocutor = bool(token_set & _PARTICIPANT_INTERLOCUTOR_WORDS)
    shared = bool(token_set & _PARTICIPANT_SHARED_WORDS)
    return {
        "speaker_reference": speaker,
        "interlocutor_reference": interlocutor,
        "shared_reference": shared,
        "single_participant_reference": bool(speaker) != bool(interlocutor),
    }


def _context_signature(text: Any) -> dict[str, Any]:
    """Build an advisory subject/action signature without routing on fixed phrases.

    The signature separates topical content from discourse relations. Pronouns and
    references to remembering/the current conversation remain in the original request
    but do not masquerade as external subject changes.
    """
    _, tokens = _semantic_normalize(text)
    token_set = set(tokens)
    subjects = set()
    for token in tokens:
        if not token or token.isdigit() or _is_context_signature_generic(token):
            continue
        if len(token) < 4:
            continue
        # A small morphological stem keeps inflected Russian nouns aligned.
        subjects.add(token[:5] if len(token) >= 5 else token)
    reference_hits = token_set & _CONTEXT_SIGNATURE_REFERENCES
    # Output form is metadata only; it does not decide whether memory is reused.
    output_forms = []
    for name, terms in _CONTEXT_OUTPUT_TERMS.items():
        if any(token == term or (len(term) >= 5 and token.startswith(term)) for token in tokens for term in terms):
            output_forms.append(name)
    numbers = []
    for match in re.finditer(r"(?<![\w])\d+(?:[.,]\d+)?(?![\w])", _text(text)):
        value = match.group(0).replace(",", ".")
        if value not in numbers:
            numbers.append(value)
        if len(numbers) >= 8:
            break
    return {
        "subject_terms": sorted(subjects)[:12],
        "has_explicit_subject": bool(subjects),
        "reference_strength": round(min(1.0, len(reference_hits) / max(2.0, len(token_set) * 0.35)), 3),
        "reference_terms": sorted(reference_hits)[:8],
        "participant_references": _participant_reference_profile(tokens),
        "output_forms": output_forms,
        "numeric_anchors": numbers,
    }


def _has_explicit_topic_introduction(text: str) -> bool:
    """Return true when a request explicitly introduces a subject instead of only referring back.

    A named-content request such as “continue further; tell me about Ramanujan's life”
    must not be classified as a continuation merely because the preface contains “continue”.
    Pure anaphoric phrases such as “tell me about him/that” remain continuations.
    """
    low = _text(text).lower().replace("ё", "е")
    pattern = re.compile(
        r"\b(?:рас{1,2}каж\w*|рас{1,2}каз\w*|рассказать|напиши(?:те)?|написать|опиши(?:те)?|описать|"
        r"объясни(?:те)?|объяснить|изложи(?:те)?|представь(?:те)?|дай|покажи(?:те)?|"
        r"tell|describe|explain|write|give)\b"
        r".{0,100}?\b(?:про|об|обо|о|about|on)\s+"
        r"(?!его\b|её\b|ее\b|него\b|нее\b|ней\b|ним\b|них\b|ему\b|ей\b|"
        r"их\b|это\b|этом\b|эту\b|эти\b|тот\b|та\b|те\b|таком\b|такое\b|"
        r"him\b|her\b|them\b|it\b|that\b|this\b|those\b|these\b)"
        r"[а-яa-z0-9]",
        flags=re.IGNORECASE | re.DOTALL,
    )
    if pattern.search(low):
        return True
    # Explicitly requested deliverables introduce a new subject even when the
    # user adds anaphoric wording such as "пришли мне это в файле" afterwards.
    # This prevents a new table/app/code task from inheriting an unrelated hot branch.
    creation_action = bool(re.search(
        r"\b(?:сделай|создай|составь|напиши|построй|сгенерируй|подготовь|разработай|" 
        r"приведи|перечисли|make|create|build|generate|write|prepare|produce)\b", low,
    ))
    deliverable = bool(re.search(
        r"\b(?:таблиц\w*|спис\w*|код\w*|файл\w*|приложен\w*|сайт\w*|" 
        r"график\w*|диаграмм\w*|формул\w*|стихотворен\w*|текст\w*|отчет\w*|" 
        r"менделеев\w*|periodic\s+table|table|list|code|file|app|website|graph|chart|diagram|formula)\b",
        low,
    ))
    has_subject_detail = len([token for token in re.findall(r"[a-zа-я0-9]+", low) if len(token) > 3]) >= 5
    return bool(creation_action and deliverable and has_subject_detail)


def _is_short_continuation_preface(text: str) -> bool:
    """Identify a brief praise/transition fragment that is not a standalone task."""
    low, tokens = _semantic_normalize(text)
    if len(tokens) > 8 or not tokens or "?" in low:
        return False
    has_continue = any(root in low for root in (
        "продолж", "дальше", "continue", "resume", "продолжим", "продолжать",
    ))
    has_acknowledgement = any(token.startswith((
        "молод", "хорош", "отлич", "спасибо", "great", "good", "well", "thanks",
    )) for token in tokens)
    return has_continue and (has_acknowledgement or set(tokens).issubset({
        "теперь", "дальше", "продолжим", "продолжать", "продолжай", "далее", "now", "continue", "further",
    })) and not _has_explicit_topic_introduction(text)


def _looks_like_previous_answer_followup(text: str) -> bool:
    """Recognise explanation requests whose object is the answer just given.

    This is deliberately conservative: an explicit new subject is not treated as
    a previous-answer reference. These cues allow memory retrieval without relying
    on a literal "remember/history" trigger.
    """
    low = _text(text).lower().replace("ё", "е")
    if not low:
        return False

    # A message can name its subject and still be an explicit return to an older
    # branch. Keep such a request whole: splitting "continue the math overview,
    # where did we stop, and expand it" into separate clauses can discard the
    # named topic before memory retrieval reaches the Provider.
    explicit_prior_topic_pointer = bool(re.search(
        r"\b(?:на\s+ч[её]м\s+мы\s+остановил\w*|где\s+мы\s+остановил\w*|"
        r"к\s+чему\s+мы\s+пришл\w*|как\s+мы\s+обсуждал\w*|"
        r"что\s+мы\s+обсуждал\w*|как\s+раньше\s+обсуждал\w*|"
        r"вернись\s+к\s+(?:предыдущ\w*|прежн\w*|обсужд\w*)|"
        r"как\s+(?:ты\s+)?хотел\w*,?\s+чтобы\s+мы\s+продолжил\w*)\b",
        low,
    ))
    explicit_resume_action = bool(re.search(
        r"\b(?:продолж\w*|развей\w*|разверни\w*|возобнови\w*|вернись\s+к)\b",
        low,
    ))
    if explicit_prior_topic_pointer and explicit_resume_action:
        return True

    # Elliptical artifact follow-ups such as "где остальные таблицы/графики?" refer
    # to the deliverables just discussed, even though they name a renderer.
    remaining_artifact_followup = bool(re.search(
        r"\b(?:где\s+)?(?:остал[ьт]н\w*|оставш\w*|остаточн\w*|друг\w*)\s+(?:таблиц\w*|график\w*|диаграмм\w*|блок\w*|файл\w*|материал\w*|вариант\w*)\b|"
        r"\bгде\s+(?:остал[ьт]н\w*|оставш\w*|остаточн\w*|друг\w*)\b|\bа\s+(?:остал[ьт]н\w*|оставш\w*|остаточн\w*)\b",
        low,
    ))
    if remaining_artifact_followup:
        return True

    patterns = (
        r"\bкак\s+(?:ты|вы)\s+(?:решил\w*|посчитал\w*|вычислил\w*|рассчитал\w*|"
        r"получил\w*|вывел\w*|доказал\w*|обосновал\w*)\b",
        r"\bкак\s+получил\w*\s+(?:этот\s+|такой\s+)?результат\b",
        r"\bпочему\s+(?:ты|вы)\s+(?:так|это)\b",
        r"\b(?:explain|walk\s+me\s+through)\s+(?:that|this|it|the\s+result)\b",
    )
    if any(re.search(pattern, low) for pattern in patterns):
        return True
    # A standalone qualifier may refer to the previous answer, but an explicitly
    # supplied new object must be answered independently.
    explicit_subject = re.search(
        r"\b(?:математик\w*|экспонент\w*|функци\w*|уравнен\w*|формул\w*|"
        r"задач\w*|пример\w*|числ\w*|график\w*|таблиц\w*|физик\w*|"
        r"истор\w*|коперник\w*|эйнштейн\w*|photosynthesis|equation|formula|"
        r"function|exponent|example|problem|number|graph|table|physics)\b",
        low,
    )
    if explicit_subject:
        return False
    # Very short qualifier-only follow-ups have no explicit object of their own.
    tokens = _semantic_normalize(low)[1]
    qualifier_only = re.fullmatch(
        r"\s*(?:а\s+)?(?:объясни|объясните|поясни|поясните|распиши|разбери|"
        r"докажи|покажи|explain|elaborate)\s+(?:мне\s+)?"
        r"(?:это|так|научно|пошагово|подробнее|почему|как|scientifically|step\s+by\s+step)\s*[.!?]*\s*",
        low,
    )
    standalone_qualifier = bool(re.fullmatch(
        r"\s*(?:а\s+|и\s+|ну\s+)?(?:подробнее|детальнее|подробней|"
        r"более\s+подробно|more|more\s+detail|in\s+more\s+detail)\s*[?!…]*\s*",
        low,
        flags=re.IGNORECASE,
    ))
    return standalone_qualifier or bool(qualifier_only and len(tokens) <= 5)




def _looks_like_topic_reference_fragment(
    text: str,
    *,
    explicit_topic_introduction: bool = False,
) -> bool:
    """Recognise a short, explicit pointer to a topic that may exist in memory.

    This is a retrieval hint only. State Manager must verify a real matching
    branch and must return to a new topic when no match exists.
    """
    low, tokens = _semantic_normalize(text)
    if not low or len(tokens) > 10 or explicit_topic_introduction:
        return False
    if re.fullmatch(
        r"(?:привет|здравствуй\w*|здравствуйте|доброе утро|добрый день|добрый вечер|hello|hi|hey|thanks|thank you)",
        low,
    ):
        return False
    if _detect_requested_outputs(text) != ["text"]:
        return False

    # "Кто такой X?" / "Что такое X?" is a complete factual question, not
    # an answer fragment or an instruction to search prior dialogue.
    if re.match(
        r"^\s*(?:а\s+)?(?:кто\s+так(?:ой|ая|ое|ие)|что\s+такое|"
        r"что\s+(?:значит|означает)|кто\s+был)\s+\S+",
        low,
        flags=re.IGNORECASE,
    ):
        return False

    action = re.search(
        r"\b(?:расскажи|расскажите|объясни|объясните|напиши|напишите|опиши|опишите|"
        r"покажи|построй|создай|сделай|вычисли|сравни|найди|проверь|проанализируй|"
        r"продолжи|продолжай|продолжим|перечисли|нарисуй|развивай|раскрой|разверни|"
        r"углуби|расширь|дополни|tell|describe|explain|write|show|build|create|"
        r"make|calculate|compare|find|check|analyze|continue|develop|expand|elaborate)\b",
        low,
    )
    correction_pointer = bool(re.search(
        r"\b(?:я\s+)?(?:имел|имела|имели)\s+в\s+виду\b|"
        r"\bя\s+говорю\s+про\b|\bя\s+именно\s+про\b|"
        r"\bне\s+это\s+имел\w*\s+в\s+виду\b",
        low,
    ))
    if correction_pointer:
        return True
    if action:
        return False
    if re.match(
        r"^(?:(?:а|и|ну|так|нет|не)\s+)?(?:(?:я|мы)\s+)?(?:именно\s+)?"
        r"(?:про|об|обо|насч[её]т|относительно|по\s+поводу|about|regarding)\s+\S+",
        low,
    ):
        return True

    bare_topic_noise = {
        "а", "и", "ну", "так", "да", "нет", "ок", "окей", "спасибо", "пожалуйста",
        "дальше", "далее", "продолжай", "продолжим", "еще", "ещё", "подробнее",
        "что", "чем", "где", "когда", "почему", "как", "зачем", "кто", "какой", "какая",
        "тема", "темы", "тему", "вопрос", "вопросы", "расскажи", "объясни", "покажи",
        "сделай", "создай", "найди", "проверь", "help", "thanks", "please", "continue", "more",
    }
    if len(tokens) <= 4 and not re.search(r"[?!？]", _text(text)) and not action:
        signature = _context_signature(text)
        subjects = signature.get("subject_terms") if isinstance(signature, dict) else []
        meaningful = {token for token in tokens if token not in bare_topic_noise}
        if subjects and meaningful:
            return True
    return False


def _looks_like_context_dependent_question(
    text: str,
    *,
    interrogative: bool,
    explicit_topic_introduction: bool = False,
) -> bool:
    """Recognise a question whose omitted object is supplied by the active dialogue.

    This is an intent feature, not a command-word trigger. A demonstrative/pronoun
    ("кто её придумал?", "who invented this?") creates a backward reference; a very
    short subjectless question ("почему так?", "кто предложил?") is an ellipsis
    candidate. A self-contained named subject remains a new-information request.
    """
    if not interrogative or explicit_topic_introduction:
        return False
    low, tokens = _semantic_normalize(text)
    if not tokens:
        return False
    token_set = set(tokens)
    anaphoric_terms = {
        "он", "она", "оно", "они", "его", "ее", "ему", "ей", "им", "их",
        "нее", "него", "ней", "ним", "них", "это", "этот", "эта", "эту",
        "этого", "этой", "этом", "эти", "этих", "тот", "та", "ту", "того",
        "той", "тех", "this", "that", "these", "those", "it", "he", "she",
        "they", "him", "her", "them", "its", "same", "former", "latter",
    }
    # Bound the signal to ordinary follow-up sized questions; a long request with a
    # pronoun and a new explicit subject should be resolved by normal decomposition.
    if token_set & anaphoric_terms and len(tokens) <= 18:
        return True
    if len(tokens) <= 5:
        signature = _context_signature(text)
        subjects = signature.get("subject_terms") if isinstance(signature, dict) else []
        return not bool(subjects)
    return False


def _infer_dialogue_act_profile(
    text: str,
    *,
    interrogative: bool,
    context_dependent_question: bool,
    answer_followup: bool,
    continuation_action: bool,
    explicit_topic_introduction: bool,
) -> dict[str, Any]:
    """Describe the user's speech act without treating keywords as topic switches.

    The profile is advisory metadata for active-dialogue retrieval. A short bare
    agreement/rejection can refer to the immediately preceding turn; a message
    that introduces its own subject or deliverable must remain a new request.
    """
    low, tokens = _semantic_normalize(text)
    if not tokens:
        return {
            "speech_act": "EMPTY", "communicative_act": "EMPTY",
            "pragmatic_intent": "NONE", "message_function": "EMPTY",
            "context_dependent_reaction": False,
            "pragmatic_features": {},
        }

    token_set = set(tokens)
    signature = _context_signature(text)
    subjects = signature.get("subject_terms") if isinstance(signature, dict) else []
    output_forms = signature.get("output_forms") if isinstance(signature, dict) else []
    # The context-signature layer is intentionally permissive. Filter conversational
    # fillers here so words like "понятно", "ладно" or "объясни" are not mistaken
    # for a newly introduced topic.
    non_topical_roots = (
        "понят", "спаси", "хорош", "ладн", "молод", "отлич", "соглас",
        "правиль", "точн", "верн", "ага", "угу", "да", "нет", "неа",
        "отнюд", "подро", "подроб", "поясн", "объясн", "уточн", "разъясн",
        "расшифр", "докаж", "обоснуй", "обоснуйте", "имел", "имела",
        "виду", "друго", "смысл", "так", "это",
    )
    meaningful_subjects = [
        _text(term) for term in (subjects or [])
        if _text(term) and not any(_text(term).startswith(root) for root in non_topical_roots)
    ]
    has_independent_payload = bool(meaningful_subjects or output_forms or signature.get("numeric_anchors"))
    short = len(tokens) <= 7

    agreement_terms = {
        "да", "ага", "угу", "ок", "окей", "ладно", "хорошо", "верно", "точно",
        "именно", "правильно", "согласен", "согласна", "согласны", "конечно",
        "yes", "yeah", "yep", "ok", "okay", "right", "exactly", "correct", "agreed",
    }
    rejection_terms = {
        "нет", "неа", "неверно", "неправильно", "ошибка", "мимо", "отнюдь",
        "no", "nope", "wrong", "incorrect",
    }
    gratitude_terms = (
        "спасибо", "спасибки", "благодарю", "благодарен", "благодарна",
        "признателен", "признательна", "ценю это", "thanks", "thank you",
        "many thanks", "appreciate it",
    )
    positive_terms = (
        "отлично", "хорошо получилось", "вот это хорошо", "здорово", "прекрасно",
        "замечательно", "молодец", "классно", "круто", "супер", "great",
        "brilliant", "well done", "looks good", "nice work", "perfect",
    )
    dissatisfaction_terms = (
        "не нравится", "не устраивает", "ужасно", "раздражает", "бесит",
        "ты не понял", "ты не поняла", "ты меня не понимаешь", "опять не понял",
        "not what i asked", "you misunderstood", "you mixed it up", "this is annoying",
    )
    revision_terms = (
        "переделай", "перепиши", "исправь", "поправь", "улучши", "сделай иначе",
        "попробуй иначе", "заново", "redo", "revise", "rewrite", "fix that", "try again",
    )
    correction_terms = (
        "не так", "не то", "не это", "не совсем", "я имел в виду", "я имела в виду",
        "я про другое", "не об этом", "не об этом речь", "поправка", "уточню",
        "not that", "not what i meant", "i meant", "that's not right",
    )
    clarification_terms = (
        "поясни", "поясните", "уточни", "уточните", "разъясни", "разъясните",
        "что ты имеешь в виду", "что вы имеете в виду", "в каком смысле",
        "подробнее", "расшифруй", "clarify", "what do you mean", "elaborate",
    )
    explanation_terms = (
        "объясни", "объясните", "докажи", "докажите", "обоснуй", "обоснуйте",
        "почему", "как это работает", "как это получается", "explain", "prove",
        "why does", "why is", "how does",
    )
    waiting_acknowledgement = bool(re.fullmatch(
        r"\s*(?:ну\s*)?(?:жду|ожидаю|жду\s+ответа|жду\s+результат\w*|ну\s+и\s+что|долго\??|ну\??|и\??|wait(?:ing)?|i\s*wait|still\s+waiting|waiting\s+for\s+(?:it|the\s+result|the\s+image))\s*[.!?…]*\s*",
        low, re.IGNORECASE,
    ))
    acknowledgement = short and (waiting_acknowledgement or any(
        token in agreement_terms or any(token.startswith(root) for root in ("соглас", "правиль", "точн"))
        for token in tokens
    )) and not any(token in rejection_terms or token in {"не", "никак", "ни"} for token in tokens)
    negation = short and (
        any(token in rejection_terms for token in tokens)
        or ("не" in token_set and bool(token_set & {"так", "то", "это", "совсем", "согласен", "согласна", "верно", "правильно"}))
        or bool(re.search(r"\b(?:не\s+соглас\w*|не\s+так|не\s+то|не\s+это|я\s+не\s+это)\b", low))
    )
    has_phrase = lambda phrases: any(phrase in low for phrase in phrases)
    gratitude = short and has_phrase(gratitude_terms)
    positive_evaluation = short and has_phrase(positive_terms)
    misunderstanding_reference = bool(re.search(
        r"(?:\bумудрил\w*.{0,40}непоня\w*|"
        r"\bты\b.{0,55}\b(?:непоня\w*|не\s+поня\w*|не\s+понима\w*|не\s+уловил\w*|не\s+прочитал\w*|не\s+услышал\w*)|"
        r"\bкак\b.{0,45}\b(?:умудрил\w*|смог\w*|мог\w*)\b.{0,35}непоня\w*)",
        low, re.I | re.S,
    ))
    joke_retraction = bool(short and re.search(
        r"(?:\b(?:я|мы)\s+(?:просто\s+)?(?:шучу|пошутил\w*|пошутила|пошутили)|"
        r"\b(?:это\s+(?:была|просто)\s+)?шутк\w*|"
        r"\b(?:i(?:'m|\s+am)\s+(?:just\s+)?joking|just\s+kidding|i\s+was\s+joking)\b)",
        low, re.I,
    ))
    dissatisfaction = has_phrase(dissatisfaction_terms) or misunderstanding_reference
    revision_request = short and has_phrase(revision_terms)
    correction = any(term in low for term in correction_terms) or dissatisfaction or revision_request or (
        negation and bool(token_set & {"это", "то", "так", "другое", "имел", "имела", "виду"})
    )
    clarification = any(term in low for term in clarification_terms)
    explanation_request = any(term in low for term in explanation_terms) or (interrogative and bool(token_set & {"почему", "как", "зачем", "why", "how"}))
    has_deictic_reference = bool(token_set & {
        "это", "этот", "эта", "эту", "этого", "этой", "этом", "эти", "тот", "та",
        "ту", "того", "той", "он", "она", "оно", "они", "его", "ее", "ей", "ему",
        "им", "их", "it", "this", "that", "he", "she", "they", "him", "her", "them",
    })
    own_topic_or_output = (
        (explicit_topic_introduction or has_independent_payload)
        and not misunderstanding_reference
        and not joke_retraction
    )
    context_dependent_reaction = bool(
        not own_topic_or_output
        and not explicit_topic_introduction
        and (
            (acknowledgement and len(tokens) <= 4)
            or waiting_acknowledgement
            or gratitude
            or positive_evaluation
            or dissatisfaction
            or joke_retraction
            or revision_request
            or negation
            or correction
            or ((clarification or explanation_request) and short and not context_dependent_question)
        )
    )

    if correction:
        speech_act = "CORRECTION_OR_REVISION"
    elif dissatisfaction:
        speech_act = "FRUSTRATION_OR_DISSATISFACTION"
    elif joke_retraction:
        speech_act = "JOKE_OR_PLAYFUL_RETRACTION"
    elif revision_request:
        speech_act = "REVISION_REQUEST"
    elif negation:
        speech_act = "NEGATION_OR_DISAGREEMENT"
    elif gratitude:
        speech_act = "GRATITUDE_OR_APPRECIATION"
    elif positive_evaluation:
        speech_act = "POSITIVE_EVALUATION"
    elif acknowledgement:
        speech_act = "AGREEMENT_OR_ACKNOWLEDGEMENT"
    elif clarification:
        speech_act = "CLARIFICATION_REQUEST"
    elif explanation_request or answer_followup:
        speech_act = "EXPLANATION_REQUEST"
    elif context_dependent_question or has_deictic_reference:
        speech_act = "REFERENTIAL_CONTINUATION"
    elif continuation_action:
        speech_act = "CONTINUATION_REQUEST"
    elif interrogative:
        speech_act = "INFORMATION_QUESTION"
    else:
        speech_act = "STATEMENT_OR_REQUEST"

    if correction or revision_request:
        communicative_act = "REVISE_PREVIOUS_RESPONSE"
    elif gratitude:
        communicative_act = "APPRECIATION_AND_CONTINUE"
    elif positive_evaluation or acknowledgement:
        communicative_act = "ACKNOWLEDGEMENT_OR_POSITIVE_FEEDBACK"
    elif joke_retraction:
        communicative_act = "CONTEXTUAL_JOKE_OR_RETRACTION"
    elif context_dependent_reaction or context_dependent_question or answer_followup:
        communicative_act = "CONTINUATION"
    elif negation or dissatisfaction:
        communicative_act = "RESPOND_TO_DISAGREEMENT"
    elif clarification:
        communicative_act = "CLARIFICATION"
    elif explanation_request:
        communicative_act = "EXPLANATION"
    elif continuation_action:
        communicative_act = "CONTINUATION"
    else:
        communicative_act = "NEW_OR_STANDALONE"

    return {
        "speech_act": speech_act,
        "communicative_act": communicative_act,
        "pragmatic_intent": speech_act.lower(),
        "message_function": communicative_act.lower(),
        "context_dependent_reaction": context_dependent_reaction,
        "recommended_response_action": (
            "ACKNOWLEDGE_COMPLETED_RESULT_WITHOUT_REPEATING"
            if (gratitude or (acknowledgement and len(tokens) <= 2)) and not has_independent_payload
            else "REPAIR_OR_IMPROVE_PREVIOUS_RESPONSE" if correction or revision_request
            else "RECHECK_PREVIOUS_RESPONSE_AND_CORRECT_IF_NEEDED" if negation or dissatisfaction
            else "ACKNOWLEDGE_CONTEXTUAL_JOKE" if joke_retraction
            else "ACKNOWLEDGE_BRIEFLY_AND_CONTINUE_NATURALLY" if positive_evaluation or acknowledgement
            else "ANSWER_NORMALLY"
        ),
        "tone": "GRATEFUL" if gratitude else "POSITIVE" if positive_evaluation or acknowledgement else "PLAYFUL" if joke_retraction else "DISSATISFIED" if dissatisfaction or negation else "CORRECTIVE" if correction or revision_request else "NEUTRAL",
        "pragmatic_features": {
            "acknowledgement_or_agreement": bool(acknowledgement),
            "waiting_acknowledgement": bool(waiting_acknowledgement),
            "negation_or_disagreement": bool(negation),
            "correction": bool(correction),
            "gratitude": bool(gratitude),
            "positive_evaluation": bool(positive_evaluation),
            "frustration_or_dissatisfaction": bool(dissatisfaction),
            "revision_request": bool(revision_request),
            "clarification_request": bool(clarification),
            "explanation_request": bool(explanation_request),
            "continuation_request": bool(continuation_action),
            "deictic_reference": bool(has_deictic_reference),
            "has_independent_payload": bool(has_independent_payload),
            "misunderstanding_reference": bool(misunderstanding_reference),
            "joke_or_playful_retraction": bool(joke_retraction),
        },
    }




def _is_immediate_previous_message_reference(text: Any) -> bool:
    """True when the user points to the immediately preceding turn, not archive history."""
    low = _text(text).lower().replace("ё", "е")
    if not low:
        return False
    direct_pointer = bool(re.search(
        r"\b(?:предыдущ(?:ем|ему|его|ей|ую)\s+(?:моем\s+)?сообщени\w*|"
        r"предыдущ(?:ем|его|ей)\s+(?:моем\s+)?запрос\w*|"
        r"мое\s+предыдущее\s+сообщени\w*|мой\s+предыдущий\s+вопрос|"
        r"последн(?:ем|ее|его)\s+моем\s+сообщени\w*|"
        r"только\s+что\s+(?:я\s+)?(?:написал\w*|спросил\w*)|"
        r"in\s+my\s+previous\s+message|my\s+last\s+(?:message|question)|"
        r"the\s+message\s+i\s+just\s+sent)\b",
        low, re.IGNORECASE,
    ))
    asks_to_resolve = bool(re.search(
        r"\b(?:о\s+чем|про\s+что|что|какой\s+вопрос|what|which)\b", low
    )) or "?" in low
    return direct_pointer and asks_to_resolve


def interpret_request_semantics(text: str) -> dict[str, Any]:
    """Infer request intent and retrieval direction before splitting into tasks.

    This is a deterministic, typo-tolerant semantic feature layer, not a claim of
    embedding-model confidence. Existing task splitting and memory ranking remain
    intact; this profile supplies intent hints and auditable reasons.
    """
    source = _text(text)
    if is_april_identity_question(source) or is_current_user_name_question(source) or is_bare_visual_command(source):
        identity_question = is_april_identity_question(source)
        user_name_question = is_current_user_name_question(source)
        identity_topic = "APRIL_PROJECT_IDENTITY" if identity_question else ("CURRENT_USER_PROFILE" if user_name_question else "UNSPECIFIED")
        identity_reason = ("independent_april_project_identity_question" if identity_question else ("authenticated_user_name_question" if user_name_question else "bare_visual_command_needs_subject"))
        return {
            "schema": "april_request_semantics_v1", "method": "april_identity_isolated_v1",
            "primary_intent": "NEW_INFORMATION", "direction": "ANSWER_NEW_REQUEST",
            "time_scope": "UNSPECIFIED", "topic_reference": identity_topic,
            "topic_reference_fragment": False, "requires_memory": False,
            "history_request": False, "search_scope": "CURRENT_DIALOGUE", "relation_hint": "NEW",
            "intent_score": 0, "speech_act": "QUESTION", "communicative_act": "INFORMATION_REQUEST",
            "pragmatic_intent": "INFORMATION_REQUEST", "message_function": "ASK_ABOUT_APRIL_IDENTITY" if identity_question else ("ASK_CURRENT_USER_NAME" if user_name_question else "BARE_VISUAL_COMMAND_NEEDS_OBJECT"),
            "pragmatic_features": {"context_dependent_question": False, "answer_followup": False, "previous_answer_reference": False, "active_branch_repair": False, "has_independent_payload": True, "explicit_topic_switch": True},
            "tone": "NEUTRAL", "recommended_response_action": "ANSWER_NORMALLY",
            "features": {"context_dependent_question": False, "context_dependent_reaction": False, "answer_followup": False, "past_reference": False, "explicit_topic_switch": True, "has_independent_payload": True},
            "reason": identity_reason,
            "context_signature": identity_topic,
            "retrieval_profile": {"mode": "NEW_TOPIC", "primary_intent": "NEW_INFORMATION", "direction": "ANSWER_NEW_REQUEST", "topic_reference": identity_topic, "prefer_active_branch": False, "prefer_named_history": False, "previous_answer_reference": False, "active_branch_repair": False, "avoid_cross_topic_injection": True, "coverage_policy": "answer_new_request"},
            "explicit_topic_switch": True,
        }
    low, tokens = _semantic_normalize(source)
    token_set = set(tokens)
    if not low:
        return {
            "schema": "april_request_semantics_v1", "method": "rules_fuzzy_lexical_v1",
            "primary_intent": "NEW_INFORMATION", "direction": "ANSWER_NEW_REQUEST",
            "time_scope": "UNSPECIFIED", "topic_reference": "UNSPECIFIED",
            "requires_memory": False, "history_request": False, "search_scope": "CURRENT_DIALOGUE",
            "intent_score": 0, "features": {}, "reason": "empty_request",
        }

    dialogue_action = _semantic_group_hit(tokens, "dialogue_action")
    recall_action = _semantic_group_hit(tokens, "recall_action")
    decision_action = _semantic_group_hit(tokens, "decision_action") or (
        "пришли" in token_set and bool(token_set & {"к", "чему", "выводу"})
    ) or "к чему мы пришли" in low or "what did we conclude" in low
    plan_action = _semantic_group_hit(tokens, "plan_action")
    continuation_action = _semantic_group_hit(tokens, "continuation_action") or any(phrase in low for phrase in (
        "продолжай", "продолжим", "давай продолжим", "продовжуй", "продовжимо", "давай продовжимо",
        "resume this", "let us continue", "let's continue", "continue this", "keep going",
        "continua", "continuemos", "sigamos", "volvamos",
        "mach weiter", "machen wir weiter", "setzen wir fort", "weiter so",
        "reprenons", "continuons", "poursuivons", "on continue",
        "continuiamo", "riprendiamo", "andiamo avanti",
        "kontynuuj", "kontynuujmy", "wróćmy", "wrocmy", "dalej z tym",
        "vamos continuar", "continuemos", "voltemos", "continue a partir daqui",
        "ga door", "laten we doorgaan", "verdergaan", "gaan we verder",
    ))
    explicit_topic_introduction = _has_explicit_topic_introduction(source)
    explicit_output_action = _has_direct_non_ui_output_action(source)
    if explicit_output_action:
        explicit_topic_introduction = True
    answer_followup = _looks_like_previous_answer_followup(source)
    # A compound reissue request naming several renderers (for example,
    # "выдай четверостишие в коде, copy-блоке, графике и таблице") is very
    # likely tied to an already-produced deliverable. Route it through the
    # active-branch matcher first; if no matching saved branch exists, State
    # Manager still downgrades it to a new request. A single renderer request
    # remains eligible for fresh generation.
    artifact_replay_action = bool(re.search(
        r"(?:выдай\w*|выведи\w*|покажи\w*|верни\w*|повтори\w*|отдай\w*|"
        r"предоставь\w*|скопируй\w*|retrieve|reissue|return|show|give me)",
        low,
    ))
    artifact_renderer_mentions = sum(bool(re.search(pattern, low)) for pattern in (
        r"код\w*|скрипт\w*|\bcode\b", r"копи\w*|copy\b",
        r"график\w*|диаграмм\w*|\bgraph\b|\bchart\b",
        r"таблиц\w*|\btable\b", r"формул\w*|\bformula\b",
    ))
    artifact_replay_cue = artifact_replay_action and artifact_renderer_mentions >= 2
    past_reference = _semantic_group_hit(tokens, "past_reference")
    future_reference = _semantic_group_hit(tokens, "future_reference")
    today_reference = _semantic_group_hit(tokens, "today_reference")
    recent_reference = _semantic_group_hit(tokens, "recent_reference")

    self_reference = bool(token_set & {"мы", "нас", "нам", "наш", "наша", "наши", "наше", "we", "our", "us"}) or any(
        token.startswith(("наш", "наша", "наши")) for token in tokens
    )
    # “с тобой” is a dialog reference, but do not let any generic preposition “с” trigger it.
    self_reference = self_reference or ("тобой" in token_set and "с" in token_set)
    self_reference = self_reference or bool(token_set & {"будем", "будете", "планируем", "собираемся", "we'll", "lets"})
    interrogative = bool(token_set & {"что", "чем", "чего", "какие", "какая", "какой", "кто", "где", "когда", "почему", "как", "зачем", "which", "what", "who", "where", "when", "why", "how"}) or "?" in source or "？" in source
    imperative_recall = bool(token_set & {
        "напомни", "вспомни", "перечисли", "перескажи", "восстанови", "найди",
        "вернись", "покажи", "покажите", "скажи", "скажите", "назови", "назовите",
        "выведи", "дай", "дайте", "remind", "recall", "remember", "summarize", "list",
    })
    temporal_future = future_reference or bool(token_set & {"завтра", "будем", "буду", "будущем", "tomorrow", "will"})
    explicit_time_reference = bool(re.search(
        r"\b(?:(?:\d+|один|одна|одно|одну|два|две|пару|пара|несколько|нескольких|три|четыре|пять|полчаса|полторы?)\s*(?:-|–|—|до)?\s*)?(?:секунд\w*|сек\.?|seconds?|secs?|минут\w*|мин\b|час\w*|ч\b|дн\w*|сутк\w*|полчаса)\s*(?:назад|тому назад|ago)\b|\b(?:в|около|примерно в)\s*\d{1,2}[:.]\d{2}\b",
        low,
    ))
    temporal_past = (
        past_reference or today_reference or recent_reference or explicit_time_reference
        or bool(token_set & {"вчера", "сегодня", "утром", "вечером", "недавно", "только", "что", "yesterday", "today", "recently"})
        or "только что" in low or "just now" in low
    )
    explicit_last_topic_reference = any(marker.replace("ё", "е") in low for marker in _HISTORY_MARKERS if "последн" in marker or "последнее время" in marker or "за последнее время" in marker)
    # A natural Russian question often omits its grammatical subject:
    # "Какие темы и обсуждали?" still asks to retrieve previous dialogue.
    asks_about_discussed_topics = bool(
        dialogue_action and interrogative and re.search(r"\bтем\w*\b", low)
    )
    # List requests have a different shape from "remind me": for example,
    # "в истории 16 диалогов скажи последние 5" or "покажи первые диалоги".
    # Require a history object plus ordinal/count language and a listing cue.
    history_listing_request = bool(
        re.search(r"\b(?:диалог\w*|разговор\w*|переписк\w*|сообщен\w*|истори\w*|тем\w*)\b", low)
        and re.search(
            r"\b(?:последн\w*|перв\w*|стар\w*|ранн\w*|давн\w*|\d+|один|одну|два|две|три|четыре|пять|шесть|семь|восемь|девять|десять)\b",
            low,
        )
        and bool(token_set & {
            "покажи", "покажите", "скажи", "скажите", "назови", "назовите", "дай",
            "дайте", "выведи", "перечисли", "перечислите", "найди", "найдите",
            "истории", "диалогов", "диалоги", "темы", "сообщений", "что", "какие", "какой", "сколько",
        })
    )
    # A declarative phrase can still point to a previous dialogue branch:
    # “мы же говорили об этом недавно”. Treat it as a history retrieval cue.
    implicit_past_dialogue_pointer = bool(
        dialogue_action and self_reference and temporal_past and not temporal_future
    )
    explicit_discussion_question = (dialogue_action and interrogative and (
        self_reference or temporal_past or recall_action or explicit_time_reference or any(term in low for term in (
            "о чем", "про что", "что обсуждали", "что было в диалоге", "что было в разговоре",
            "what did we discuss", "what were we talking", "what happened in our conversation",
        ))
    )) or asks_about_discussed_topics or history_listing_request or (explicit_time_reference and (interrogative or dialogue_action or self_reference)) or explicit_last_topic_reference
    decision_recall = decision_action and (interrogative or recall_action) and (self_reference or temporal_past or dialogue_action or past_reference)
    plan_past_form = any(token.startswith(root) for token in tokens for root in ("заплан", "планировали", "планировал", "собирались", "собирался", "намеревались"))
    plan_recall = plan_action and (interrogative or recall_action or imperative_recall) and (
        recall_action or past_reference or plan_past_form or (self_reference and not temporal_future)
    )
    future_topic_question = (
        temporal_future and dialogue_action and interrogative
        and bool(token_set & {"будем", "буду", "будете", "будут", "will", "планируем", "собираемся"})
        and not (recall_action or past_reference or decision_action or plan_past_form)
    )
    history_recall = (
        explicit_discussion_question
        or (recall_action and (dialogue_action or self_reference or past_reference or today_reference or recent_reference or decision_action or plan_action))
        or decision_recall
        or plan_recall
        or (past_reference and (dialogue_action or decision_action or plan_action) and (interrogative or imperative_recall))
        or implicit_past_dialogue_pointer
    ) and not future_topic_question
    # A history noun or phrase fragment is not a retrieval command by itself.
    # The history decision above requires a recall operation, dialogue-question
    # shape, or an explicit inventory/time request; complaints about April's
    # previous answer therefore remain answer-feedback turns.

    # A bare invitation to talk is a social opener, not a reference to an old
    # work branch. Treat it as a fresh conversational turn unless it explicitly
    # asks to resume a named/previous subject (handled by the history signals).
    # This prevents "Пообщаемся" from reopening a stale file/artifact branch.
    social_conversation_opener = bool(re.fullmatch(
        r"\s*(?:(?:ну\s+)?давай(?:те)?\s+)?"
        r"(?:пообщаемся|пообщаться|поговорим|поговорить|поболтаем|поболтать|"
        r"общаться|беседовать|поговори(?:те)?\s+со\s+мной|"
        r"let(?:'|’)s\s+talk|talk\s+with\s+me|chat\s+with\s+me)"
        r"[.!?…\s]*",
        low,
        flags=re.IGNORECASE,
    )) and not history_recall and not explicit_topic_introduction
    context_dependent_question = _looks_like_context_dependent_question(
        source, interrogative=interrogative,
        explicit_topic_introduction=explicit_topic_introduction,
    )
    topic_reference_fragment = (
        False if social_conversation_opener else
        _looks_like_topic_reference_fragment(
            source, explicit_topic_introduction=explicit_topic_introduction,
        )
    )
    dialogue_act_profile = _infer_dialogue_act_profile(
        source,
        interrogative=interrogative,
        context_dependent_question=context_dependent_question,
        answer_followup=answer_followup,
        continuation_action=continuation_action,
        explicit_topic_introduction=explicit_topic_introduction,
    )
    dialogue_pragmatic_features = dialogue_act_profile.get("pragmatic_features") or {}
    if dialogue_pragmatic_features.get("joke_or_playful_retraction"):
        topic_reference_fragment = False
    context_dependent_reaction = bool(dialogue_act_profile.get("context_dependent_reaction"))

    if social_conversation_opener:
        primary_intent = "NEW_INFORMATION"
        direction = "ANSWER_NEW_REQUEST"
        topic_reference = "UNSPECIFIED"
        time_scope = "UNSPECIFIED"
        requires_memory = False
        history_request = False
        search_scope = "CURRENT_DIALOGUE"
        intent_score = 0
        relation_hint = "NEW"
        reason = "standalone_social_conversation_opener"
    elif history_recall:
        requires_memory = True
        history_request = True
        search_scope = "ALL_DIALOGUE_HISTORY"
        intent_score = 2 * int(dialogue_action) + 2 * int(recall_action) + 2 * int(decision_action) + 2 * int(plan_action) + int(self_reference) + int(temporal_past) + int(temporal_future) + int(interrogative)
        if decision_recall and not plan_action:
            primary_intent = "PRIOR_DECISION_RECALL"
            direction = "SEARCH_PRIOR_DECISIONS"
            topic_reference = "PRIOR_DECISION"
            reason = "decision_terms_with_dialogue_or_time_reference"
        elif plan_recall:
            primary_intent = "PLAN_RECALL"
            direction = "SEARCH_PRIOR_PLANS"
            topic_reference = "PRIOR_PLAN"
            reason = "plan_terms_with_prior_or_future_context"
        elif any(term in low for term in ("кратко", "содержание", "перечисли", "какие темы", "список тем", "summarize", "list topics")):
            primary_intent = "HISTORY_SUMMARY"
            direction = "SEARCH_AND_SUMMARIZE_HISTORY"
            topic_reference = "DIALOGUE_HISTORY"
            reason = "summary_or_topic_list_requested"
        elif any(term in low for term in ("конкрет", "фрагмент", "найди", "где мы", "какое сообщение", "find the part", "specific message")):
            primary_intent = "HISTORY_SEARCH"
            direction = "SEARCH_DIALOGUE_HISTORY"
            topic_reference = "DIALOGUE_HISTORY"
            reason = "specific_prior_fragment_requested"
        else:
            primary_intent = "HISTORY_RECALL"
            direction = "SEARCH_DIALOGUE_HISTORY"
            topic_reference = "TODAY_DIALOGUE" if today_reference else ("PREVIOUS_DIALOGUE" if past_reference or recent_reference else "DIALOGUE_HISTORY")
            reason = "dialogue_reference_detected_semantically"
        relation_hint = "HISTORY_LOOKUP"
        time_scope = "TODAY" if today_reference else ("RECENT_WINDOW" if recent_reference else ("PAST_DIALOGUE" if past_reference else ("FUTURE_PLAN_CONTEXT" if temporal_future else "AVAILABLE_HISTORY")))
    elif topic_reference_fragment:
        primary_intent = "TOPIC_CONTINUATION"
        direction = "SEARCH_ACTIVE_OR_REFERENCED_TOPIC"
        topic_reference = "TOPIC_FRAGMENT"
        time_scope = "ACTIVE_DIALOGUE"
        requires_memory = True
        history_request = False
        search_scope = "TOPIC_OR_ACTIVE_CONTEXT"
        intent_score = 4
        relation_hint = "CONTINUE"
        reason = "short_topic_pointer_requires_history_match"
    elif context_dependent_reaction:
        # Bare agreement/disagreement belongs to the active turn unless it
        # introduces an independent subject or concrete deliverable.
        primary_intent = "TOPIC_CONTINUATION"
        direction = "RESUME_OR_RETRIEVE_ACTIVE_TOPIC"
        topic_reference = "PREVIOUS_OR_ACTIVE_TOPIC"
        time_scope = "ACTIVE_DIALOGUE"
        requires_memory = True
        history_request = False
        search_scope = "TOPIC_OR_ACTIVE_CONTEXT"
        intent_score = 3
        relation_hint = "CONTINUE"
        reason = "context_dependent_agreement_or_rejection"
    elif context_dependent_question:
        primary_intent = "TOPIC_CONTINUATION"
        direction = "RESUME_OR_RETRIEVE_ACTIVE_TOPIC"
        topic_reference = "PREVIOUS_OR_ACTIVE_TOPIC"
        time_scope = "ACTIVE_DIALOGUE"
        requires_memory = True
        history_request = False
        search_scope = "TOPIC_OR_ACTIVE_CONTEXT"
        intent_score = 3 + int(interrogative)
        relation_hint = "CONTINUE"
        reason = "anaphoric_or_elliptical_question"
    elif answer_followup:
        primary_intent = "TOPIC_CONTINUATION"
        direction = "RESUME_OR_RETRIEVE_ACTIVE_TOPIC"
        topic_reference = "PREVIOUS_ASSISTANT_ANSWER"
        time_scope = "ACTIVE_DIALOGUE"
        requires_memory = True
        history_request = False
        search_scope = "TOPIC_OR_ACTIVE_CONTEXT"
        intent_score = 3 + int(interrogative)
        relation_hint = "CONTINUE"
        reason = "previous_answer_explanation_followup"
    elif artifact_replay_cue and not explicit_topic_introduction:
        primary_intent = "TOPIC_CONTINUATION"
        direction = "SEARCH_ACTIVE_OR_REFERENCED_TOPIC"
        topic_reference = "PREVIOUS_ASSISTANT_ARTIFACT"
        time_scope = "ACTIVE_DIALOGUE"
        requires_memory = True
        history_request = False
        search_scope = "TOPIC_OR_ACTIVE_CONTEXT"
        intent_score = 5 + artifact_renderer_mentions
        relation_hint = "CONTINUE"
        reason = "multi_renderer_artifact_reissue_requires_selected_branch"
    elif (continuation_action or (any(token in token_set for token in {"это", "этого", "этом", "тот", "та", "ту", "там", "дальше", "прежнему", "прежней"}) and not temporal_future)) and not explicit_topic_introduction:
        primary_intent = "TOPIC_CONTINUATION"
        direction = "RESUME_OR_RETRIEVE_ACTIVE_TOPIC"
        topic_reference = "PREVIOUS_OR_ACTIVE_TOPIC"
        time_scope = "ACTIVE_DIALOGUE"
        requires_memory = True
        history_request = False
        search_scope = "TOPIC_OR_ACTIVE_CONTEXT"
        intent_score = 2 + int(self_reference) + int(continuation_action)
        relation_hint = "CONTINUE"
        reason = "continuation_or_anaphoric_reference"
    elif temporal_future and (plan_action or dialogue_action or bool(token_set & {"что", "как", "лучше", "нужно", "надо", "будем", "сделать", "план", "should", "tomorrow"})):
        future_dialogue_topic = bool(dialogue_action and self_reference)
        primary_intent = "FUTURE_TOPIC_PLANNING" if future_dialogue_topic else "FUTURE_PLANNING"
        direction = "RETRIEVE_OR_PLAN_FUTURE_TOPICS" if future_dialogue_topic else "PLAN_OR_ANSWER_FUTURE_QUESTION"
        topic_reference = "FUTURE_TOPIC"
        time_scope = "FUTURE"
        # A future-topic question tied to “our discussion” still needs the active
        # dialogue context, but it must not be mistaken for recall of past history.
        requires_memory = future_dialogue_topic
        history_request = False
        search_scope = "TOPIC_OR_ACTIVE_CONTEXT" if future_dialogue_topic else "CURRENT_DIALOGUE"
        intent_score = 1 + int(temporal_future) + int(plan_action) + int(future_dialogue_topic)
        relation_hint = "CONTINUE" if future_dialogue_topic else "NEW"
        reason = "future_topic_tied_to_active_dialogue" if future_dialogue_topic else "future_question_without_prior_plan_recall"
    else:
        primary_intent = "NEW_INFORMATION"
        direction = "ANSWER_NEW_REQUEST"
        topic_reference = "UNSPECIFIED"
        time_scope = "UNSPECIFIED"
        requires_memory = False
        history_request = False
        search_scope = "CURRENT_DIALOGUE"
        intent_score = 0
        relation_hint = "NEW"
        reason = "explicit_topic_introduction_overrides_continuation" if explicit_topic_introduction and (continuation_action or any(token in token_set for token in {"дальше", "прежнему", "прежней", "resume", "continue"})) else "no_prior_dialogue_intent_detected"

    # UI navigation can mention “история диалога”, but it is not a request to retrieve prior conversation content.
    site_navigation_request = _is_site_navigation_request(source) or _is_feedback_control_help_request(source)
    if site_navigation_request:
        primary_intent = "NEW_INFORMATION"
        direction = "ANSWER_NEW_REQUEST"
        topic_reference = "SITE_NAVIGATION"
        time_scope = "UNSPECIFIED"
        requires_memory = False
        history_request = False
        search_scope = "CURRENT_DIALOGUE"
        intent_score = 0
        relation_hint = "NEW"
        reason = "site_navigation_request_overrides_history_keyword"

    # A compact feature vector makes routing inspectable; values are deterministic
    # feature activations, not neural embeddings or calibrated probabilities.
    features = {
        "dialogue_action": bool(dialogue_action),
        "recall_action": bool(recall_action),
        "decision_action": bool(decision_action),
        "plan_action": bool(plan_action),
        "continuation_action": bool(continuation_action),
        "answer_followup": bool(answer_followup),
        "topic_reference_fragment": bool(topic_reference_fragment),
        "context_dependent_question": bool(context_dependent_question),
        "context_dependent_reaction": bool(context_dependent_reaction),
        "self_reference": bool(self_reference),
        "past_reference": bool(past_reference),
        "today_reference": bool(today_reference),
        "recent_reference": bool(recent_reference),
        "explicit_time_reference": bool(explicit_time_reference),
        "implicit_past_dialogue_pointer": bool(implicit_past_dialogue_pointer),
        "future_reference": bool(temporal_future),
        "interrogative": bool(interrogative),
        "site_navigation_request": bool(site_navigation_request),
        "social_conversation_opener": bool(social_conversation_opener),
    }
    context_signature = _context_signature(source)
    intent_upper = _text(primary_intent).upper()
    retrieval_profile = {
        "mode": "HISTORY_LOOKUP" if history_request else ("ACTIVE_TOPIC_CONTINUATION" if requires_memory and not explicit_topic_introduction and intent_upper in {"TOPIC_CONTINUATION", "PREVIOUS_ANSWER_FOLLOWUP", "PRIOR_DECISION_RECALL", "PLAN_RECALL"} else "NEW_TOPIC"),
        "primary_intent": intent_upper or "NEW_INFORMATION",
        "direction": _text(direction),
        "topic_reference": _text(topic_reference),
        "prefer_active_branch": bool(requires_memory and not history_request and not explicit_topic_introduction),
        "prefer_named_history": bool(history_request or topic_reference in {"TOPIC_FRAGMENT", "PREVIOUS_OR_ACTIVE_TOPIC", "PREVIOUS_ASSISTANT_ANSWER"}),
        "previous_answer_reference": bool((dialogue_act_profile.get("pragmatic_features") or {}).get("previous_answer_reference") or answer_followup),
        "active_branch_repair": bool((dialogue_act_profile.get("pragmatic_features") or {}).get("active_branch_repair")),
        "avoid_cross_topic_injection": True,
        "coverage_policy": "recall_requested_history" if history_request else ("continue_uncovered_sections" if requires_memory and not explicit_topic_introduction else "answer_new_request"),
    }
    return {
        "schema": "april_request_semantics_v1",
        "method": "rules_fuzzy_lexical_v1",
        "primary_intent": primary_intent,
        "direction": direction,
        "time_scope": time_scope,
        "topic_reference": topic_reference,
        "topic_reference_fragment": bool(topic_reference_fragment),
        "requires_memory": bool(requires_memory),
        "history_request": bool(history_request),
        "search_scope": search_scope,
        "relation_hint": relation_hint,
        "intent_score": int(intent_score),
        "speech_act": dialogue_act_profile.get("speech_act"),
        "communicative_act": dialogue_act_profile.get("communicative_act"),
        "pragmatic_intent": dialogue_act_profile.get("pragmatic_intent"),
        "message_function": dialogue_act_profile.get("message_function"),
        "pragmatic_features": dialogue_act_profile.get("pragmatic_features", {}),
        "tone": dialogue_act_profile.get("tone", "NEUTRAL"),
        "recommended_response_action": dialogue_act_profile.get("recommended_response_action", "ANSWER_NORMALLY"),
        "features": features,
        "reason": reason,
        "context_signature": context_signature,
        "retrieval_profile": retrieval_profile,
    }


def _is_history_request(text: str) -> bool:
    low = _text(text).lower().replace("ё", "е")
    if _is_site_navigation_request(text):
        return False
    if any(marker.replace("ё", "е") in low for marker in _HISTORY_MARKERS):
        return True
    try:
        return bool(interpret_request_semantics(text).get("history_request"))
    except Exception:
        return False


def _history_count(text: str) -> int:
    low = _text(text).lower().replace("ё", "е")
    # Only count a requested result list, not numbers belonging to an age/time
    # phrase ("два часа назад") or an inventory statement ("в истории 16 диалогов").
    number_pattern = r"(10|[1-5])"
    unit_pattern = r"(?:диалог\w*|разговор\w*|сообщен\w*|тем\w*|пункт\w*|раздел\w*)"
    match = re.search(rf"\bпоследн\w*\s+(?:из\s+)?{number_pattern}\b", low)
    if not match:
        match = re.search(rf"\b{number_pattern}\s+(?:последн\w*\s+)?{unit_pattern}\b", low)
    if match:
        return max(1, min(5, int(match.group(1))))
    for word, count in _HISTORY_COUNTS.items():
        word_pattern = re.escape(word)
        if re.search(rf"\bпоследн\w*\s+(?:из\s+)?{word_pattern}\b", low) or re.search(
            rf"\b{word_pattern}\s+(?:последн\w*\s+)?{unit_pattern}\b", low
        ):
            return max(1, min(5, count))
    return 5


def _select_history_topics(memory: dict[str, Any]) -> list[dict[str, Any]]:
    topics = memory.get("history_topics")
    return [
        dict(item)
        for item in topics
        if isinstance(item, dict)
    ][:10] if isinstance(topics, list) else []


def _select_continuation_pairs(memory: dict[str, Any]) -> list[dict[str, Any]]:
    relation = _text(memory.get("relation")).upper()
    history_request = bool(memory.get("history_request"))
    pairs = memory.get("selected_pairs")
    # HISTORY_RECALL intentionally remains relation=NEW, but its selected evidence
    # must still reach the Provider. Relation controls topic continuation, not whether
    # authenticated history evidence may be attached to the current request.
    if (relation != "CONTINUE" and not history_request) or not isinstance(pairs, list):
        return []
    if history_request:
        if _text(memory.get("history_selection_method")) == "named_topic_section_vector":
            limit = max(2, min(3, int(memory.get("continuation_context_limit") or 3)))
        else:
            limit = 5
        newest_first = False  # History search is ranked evidence, not a live thread.
    else:
        # State Manager returns a live branch in chronological order. Preserve the
        # whole selected branch (up to ten pairs) and, most importantly, take its
        # newest tail. Taking pairs[:2] here silently forwarded the oldest turns of
        # the branch and discarded the latest USER↔APRIL exchange.
        try:
            requested_limit = int(memory.get("continuation_context_limit") or 10)
        except (TypeError, ValueError):
            requested_limit = 10
        limit = max(2, min(10, requested_limit))
        newest_first = True
    valid_pairs = [dict(item) for item in pairs if isinstance(item, dict)]
    return valid_pairs[-limit:] if newest_first else valid_pairs[:limit]


_TASK_START_VERBS = (
    # Russian / Ukrainian task starts. Keep this list action-oriented so a noun
    # phrase such as "график Эйнштейна" is not accidentally split by itself.
    "расскажи", "расскажите", "рассказать", "объясни", "объясните", "объяснить", "поясни", "поясните",
    "покажи", "покажите", "показать", "сравни", "сравните", "сравнить", "вычисли", "вычислите", "вычислить",
    "посчитай", "посчитайте", "посчитать", "рассчитай", "рассчитайте", "рассчитать", "построй", "постройте", "построить",
    "создай", "создайте", "создать", "составь", "составьте", "составить", "найди", "найдите", "найти", "продолжи", "продолжите", "продолжить",
    "перечисли", "перечислите", "опиши", "опишите", "проанализируй", "проанализируйте",
    "напиши", "напишите", "проверь", "проверьте", "уточни", "уточните",
    "приведи", "приведите", "подбери", "подберите", "выведи", "выведите",
    "нарисуй", "нарисуйте", "нарисовать", "визуализируй", "визуализируйте", "визуализировать", "дай", "дайте", "дать",
    "сделай", "сделайте", "сделать", "определи", "определите", "определить", "расширь", "расширьте", "расширить",
    "перечисли", "перечислите", "перечислить", "опиши", "опишите", "описать", "проанализируй", "проанализируйте", "проанализировать",
    "напиши", "напишите", "написать", "проверь", "проверьте", "проверить", "приведи", "приведите", "привести", "подбери", "подберите", "подобрать",
    "розкажи", "розкажіть", "поясни", "поясніть", "порівняй", "порівняйте", "обчисли", "побудуй", "побудуйте", "створи", "створіть", "склади", "знайди", "знайдіть", "перевір", "перевірте", "намалюй", "намалюйте", "продовжи", "продовжіть",
    "continue", "explain", "describe", "compare", "calculate", "compute", "build",
    "create", "find", "list", "analyze", "analyse", "write", "check", "show",
    "draw", "plot", "visualize", "visualise", "give", "make", "define", "summarize",
)
_TASK_START_WORDS = "|".join(re.escape(verb) for verb in sorted(_TASK_START_VERBS, key=len, reverse=True))
_TASK_CONNECTORS = r"(?:(?:и|а также|а потом|и потом|а теперь|и еще|и ещё|а еще|а ещё|и дополнительно|затем|потом|также|отдельно|после этого|кроме того|and then|then|also|additionally)\s+)?"
_TASK_CONNECTORS_TEXT = r"(?:и|а также|а потом|и потом|а теперь|и еще|и ещё|а еще|а ещё|и дополнительно|затем|потом|также|отдельно|после этого|кроме того|and then|then|also|additionally)"
_TASK_START_PATTERN = re.compile(
    r"\s+" + _TASK_CONNECTORS + r"(?=(?:" + _TASK_START_WORDS + r")\b)",
    flags=re.IGNORECASE,
)
_LEADING_TASK_CONNECTOR = re.compile(
    r"^" + _TASK_CONNECTORS_TEXT + r"\s+(?=(?:" + _TASK_START_WORDS + r")\b)",
    flags=re.IGNORECASE,
)
_TASK_OR_QUESTION_START = _TASK_CONNECTORS + r"(?:" + _TASK_START_WORDS + r"|что|кто|где|когда|почему|как|какой|какая|какие|чем|сколько|зачем|what|who|where|when|why|how|which|how\s+many)\b"



def _split_explicit_tasks(text: str) -> list[str]:
    """Split clear task starts without separating an object from its inverted verb.

    Russian often places the object before the imperative ("таблицу покажи",
    "картинку нарисуй"). Treating that verb as a new task loses the object and
    can accidentally route a table request to Images Generator.
    """
    source = _LEADING_TASK_CONNECTOR.sub("", str(text or "").strip(), count=1)
    if not source:
        return []

    object_before_verb = re.compile(
        r"(?:таблиц\w*|картинк\w*|изображен\w*|иллюстрац\w*|фотографи\w*|фото|"
        r"диаграмм\w*|схем\w*|черт[её]ж\w*|график\w*|формул\w*|уравнен\w*|код)\s*$",
        flags=re.IGNORECASE,
    )
    explicit_connectors = re.compile(
        r"^(?:и|а также|а потом|и потом|а теперь|и еще|и ещё|а еще|а ещё|и дополнительно|"
        r"затем|потом|также|отдельно|после этого|кроме того|and then|then|also|additionally)\s*",
        flags=re.IGNORECASE,
    )

    pieces: list[str] = []
    last_end = 0
    for match in _TASK_START_PATTERN.finditer(source):
        prefix = source[last_end:match.start()].strip()
        boundary = match.group(0).strip()
        has_connector = bool(explicit_connectors.match(boundary))
        if prefix and not has_connector and object_before_verb.search(prefix):
            # Keep object + inverted imperative in one semantic clause.
            continue
        if prefix:
            pieces.append(prefix)
        last_end = match.end()

    tail = source[last_end:].strip()
    if tail:
        pieces.append(tail)
    return pieces or [source]


def _has_explicit_independent_task_boundaries(text: str) -> bool:
    """Return True only for unmistakable multi-request separators, not workflow verbs."""
    source = _text(text)
    if not source:
        return False
    if ";" in source or "；" in source:
        return True
    if len(re.findall(r"[?？]", source)) >= 2:
        return True
    lines = [line.strip() for line in source.splitlines() if line.strip()]
    if len(lines) >= 2 and sum(bool(re.match(r"^(?:[-*•]|\d+[.)]|[a-zA-Z][.)])\s+", line)) for line in lines) >= 2:
        return True
    return False


def _build_action_contract_for_step(request: str, semantics: dict[str, Any], outputs: list[str], index: int) -> dict[str, Any]:
    """Bind each sub-request to a concrete user goal, target, inputs and completion check."""
    low = _text(request).lower().replace("ё", "е")
    sem = semantics if isinstance(semantics, dict) else {}
    output_names = [str(x).lower().replace("-", "_") for x in (outputs or ["text"])]
    attach_help = _is_attachment_tutorial_request(request)
    ui_instruction_detector = globals().get("_is_ui_instruction_request")
    ui_semantics = _infer_april_ui_semantics(request)
    ui_help = bool(ui_semantics) or _is_site_navigation_request(request) or (callable(ui_instruction_detector) and bool(ui_instruction_detector(request))) or attach_help
    composite_detector = globals().get("_detect_image_compositing_request")
    image_edit = _detect_image_modification(request) or (
        callable(composite_detector) and bool(composite_detector(request))
        and bool(re.search(r"(?:на\s+(?:это\s+|эту\s+|этой\s+|мою\s+)?фот\w*|фото\s+с\s+монет\w*|присланн\w*\s+фото)", low, re.I))
    )
    image_generation = _detect_image_generation_request(request)
    history_detector = globals().get("_is_history_request")
    history_action_phrase = bool(re.search(
        r"(?:во\s+сколько\s+(?:времени\s+)?мы\s+(?:говорил\w*|обсуждал\w*|разговаривал\w*)|"
        r"когда\s+мы\s+(?:говорил\w*|обсуждал\w*|разговаривал\w*)|"
        r"(?:что|о\s+чем|о\s+чём)\s+мы\s+(?:сегодня\s+|вчера\s+|раньше\s+)?(?:говорил\w*|обсуждал\w*)|"
        r"найди\w*.{0,45}(?:разговор|диалог|обсуждени|истори)|"
        r"(?:истори\w*\s+диалог\w*|saved\s+dialogues?|conversation\s+history))",
        low, re.I | re.S,
    ))
    history = bool(sem.get("history_request") or sem.get("primary_intent") in {"HISTORY_RECALL", "HISTORY_SUMMARY", "PRIOR_DECISION_RECALL"} or history_action_phrase or (callable(history_detector) and history_detector(request)))
    if attach_help:
        action, domain, target = "GUIDE_ATTACH_IMAGE", "april_ui", "chat.paperclip_picker"
        must_not = ["не запускать генерацию или редактирование вместо инструкции", "не утверждать, что фото прикреплено до появления вложения и отправки сообщения"]
        success = ["пользователь понимает, где скрепка", "пользователь различает Камера, Изображения и Файлы", "объяснено, что после выбора надо вернуться в чат и нажать отправку"]
        outputs = list(outputs or ["text"])
        explicit_ui_diagram = bool(re.search(r"(?:схем\w*|диаграмм\w*|flowchart|diagram)", low, re.I)) or "diagram" in output_names
        if not explicit_ui_diagram:
            outputs = [kind for kind in outputs if str(kind).lower() != "diagram"] or ["text"]
        source_requirement = "инструкция основана на проверенном маршруте и контролах IT Room; исходный файл для объяснения не требуется"
    elif ui_help:
        action = _text(ui_semantics.get("action") or "EXPLAIN_UI_ROUTE").upper()
        domain = "april_ui"
        target = _text(ui_semantics.get("target") or "verified_site_map")
        guidance_mode = _text((ui_semantics.get("ui_navigation") or {}).get("guidance_mode") or "step_by_step")
        must_not = [
            "не придумывать кнопку, раздел, URL, подпись или тариф",
            "не утверждать, что April нажала кнопку, отправила форму, изменила настройку или завершила оплату",
            "не выдавать структуру исходников за актуальный скриншот production-экрана",
            "не советовать многократно нажимать платёжные, публикационные или необратимые кнопки",
        ]
        success = [
            "назвать точный стартовый экран и подтверждённый относительный маршрут",
            "определить конкретную функцию/элемент управления и его видимый ориентир",
            "дать последовательные короткие шаги нажатий и ввода",
            "описать ожидаемое изменение экрана и следующий шаг пользователя",
            "указать только относящиеся к действию ограничения доступа и безопасный возврат",
        ]
        if guidance_mode == "troubleshoot":
            success.extend(["определить, что именно не нажимается", "проверить обязательные поля/disabled-состояние/перекрывающий диалог", "при недостатке данных запросить скриншот текущего экрана"])
        source_requirement = "APRIL_SITE_MAP + APRIL_UI_FUNCTION_CATALOG + APRIL_UI_SCREEN_REGISTRY; приоритет точного целевого action и control ID"
        ui_semantics = dict(ui_semantics)
        ui_semantics.setdefault("ui_navigation", {})
        ui_semantics["ui_navigation"] = dict(ui_semantics.get("ui_navigation") or {})
        ui_semantics["ui_navigation"].setdefault("guidance_mode", guidance_mode)
    elif history:
        action, domain, target = "SEARCH_DIALOGUE_HISTORY", "dialogue_history", "dialogue_memory"
        must_not = ["не подменять названную тему другой похожей темой", "не сообщать время без подходящей записи или достоверной отметки времени", "при отсутствии точного совпадения явно сказать об этом и предложить ближайшие подтверждённые совпадения"]
        success = ["сначала сопоставить явную тему и временное окно", "вернуть только подтверждённые записи", "сохранить связь с текущим вопросом"]
        source_requirement = "тема пользователя и/или указанное время должны совпасть с записью истории"
    elif image_edit:
        action, domain, target = "EDIT_EXISTING_IMAGE", "image", "explicit_source_image"
        must_not = ["не подменять исходное фото новой картинкой", "не использовать последнюю генерацию вместо указанного исходника"]
        success = ["привязать задачу к конкретному источнику", "при отсутствии доступного оригинала попросить прикрепить именно его", "сохранить изображение результата и связать его с этой задачей"]
        source_requirement = "конкретное прикреплённое или найденное в той же ветке исходное изображение; не выбирать по принципу самого свежего"
    elif image_generation:
        action, domain, target = "GENERATE_NEW_IMAGE", "image", "new_image_output"
        must_not = ["не выдавать текстовое описание за созданный файл", "не смешивать с просьбой редактировать существующий источник"]
        success = ["созданный результат предъявлен как изображение", "результат и исходный запрос связаны в истории"]
        source_requirement = "новое изображение явно запрошено пользователем"
    elif any(name in output_names for name in ("code", "table", "graph", "diagram", "formula", "file", "link")):
        action, domain, target = "BUILD_REQUESTED_ARTIFACT", "artifact", "requested_output_types"
        must_not = ["не заменять запрошенный рендер одним текстовым обещанием", "сохранить все явно запрошенные типы результата"]
        success = ["выполнены все запрошенные типы вывода", "сохранён порядок шагов"]
        source_requirement = "входные данные и ограничения из этого шага"
    elif sem.get("active_branch_repair") or sem.get("previous_answer_reference"):
        action, domain, target = "REPAIR_PREVIOUS_ANSWER", "dialogue", "referenced_previous_answer"
        must_not = ["не повторять прежний ответ без исправления", "не менять тему без просьбы пользователя"]
        success = ["уточнено, что именно исправляется", "исправленный ответ продолжает прежнюю задачу"]
        source_requirement = "предыдущий ответ и связанная активная ветка"
    else:
        action, domain, target = "ANSWER_DIRECTLY", "general", "current_request"
        must_not = ["не притягивать несвязанные старые темы", "не терять числа, отрицания, ограничения и указанные объекты"]
        success = ["получен прямой ответ на текущий шаг", "непрерывный смысл запроса сохранён"]
        source_requirement = "текущий текст запроса; история только при явной ссылке или подтверждённой зависимости"
    result = {
        "step_index": int(index), "domain": domain, "action": action, "target": target,
        "output_types": list(outputs or ["text"]),
        "source_requirement": source_requirement, "depends_on_previous": bool(sem.get("parent_context_dependency") or sem.get("inherits_current_request_subject")),
        "must_not": must_not, "success_criteria": success,
    }
    if ui_help:
        result["ui_navigation"] = dict(ui_semantics.get("ui_navigation") or {})
        result["site_navigation_semantics"] = ui_semantics
    return result


def _has_explicit_independent_non_ui_action(text: Any) -> bool:
    """Detect a clearly separate artifact/calculation action inside a UI-help turn.

    Words such as “image”, “graph”, or “code” alone are examples/references,
    not deliverables. Require an action verb tied to a concrete output or task.
    """
    low = _text(text).lower().replace("ё", "е")
    return bool(re.search(
        r"(?:\b(?:напиши|создай|сгенерируй|построй|нарисуй|исправь|перепиши|оптимизируй|выдай|"
        r"посчитай|рассчитай|переведи|проанализируй|сравни|write|create|generate|plot|draw|fix|rewrite|"
        r"optimize|calculate|translate|analyze|compare)\b.{0,90}\b(?:код\w*|скрипт\w*|график\w*|диаграмм\w*|таблиц\w*|"
        r"картинк\w*|изображени\w*|фотографи\w*|\bфото\b|формул\w*|уравнен\w*|файл\w*|"
        r"\bcode\b|\bscript\b|\bgraph\b|\bchart\b|\btable\b|\bimage\b|\bphoto\b|"
        r"\bformula\b|\bequation\b|\bfile\b))",
        low, re.IGNORECASE | re.DOTALL,
    ))


def _split_request_sequence(text: str) -> list[str]:
    """Find ordered questions/tasks without rewriting or de-duplicating user text.

    Boundaries are conservative: list markers, explicit question marks, semicolons,
    a new imperative/action clause, or a clear second interrogative clause. Ordinary
    commas and coordinated noun phrases are otherwise preserved.
    """
    source = _text(text)
    if not source:
        return []
    # Spoken requests often start with an address to April ("Эй, Прил,").
    # Keep the vocative attached to the actual instruction; splitting it into a
    # separate TOPIC_CONTINUATION creates an empty memory search and can detach
    # the current task from its immediately preceding answer.
    if re.match(
        r"^\s*(?:(?:эй|hey|hi|hello|привет|здравствуй|слушай|послушай)\b[\s,!:—-]*)?"
        r"(?:април\w*|прил\w*|april)\b\s*[,!:—-]*\s+",
        source, re.IGNORECASE,
    ):
        return [source]
    # A leading how-to question or an explicit negative instruction is one
    # semantic unit. Splitting it at a comma can detach the infinitive from its
    # explanation/negation and falsely authorize an artifact or raster output.
    if len(_output_segments(source)) == 1 and re.match(
        r"^\s*(?:как\b|каким\s+образом\b|почему\b|зачем\b|где\b|куда\b|"
        r"когда\b|объясни\w*\b|расскажи\w*\b|подскажи\w*\b|"
        r"how\b|why\b|where\b|when\b|what\b|"
        r"не\b|ни\b|не\s+надо\b|не\s+нужно\b|не\s+хочу\b|"
        r"don't\b|do\s+not\b|never\b)",
        source, re.IGNORECASE,
    ):
        return [source]
    if _is_feedback_control_help_request(source):
        return [source]
    # Keep several route questions together as one navigation workflow. A separate
    # explicit artifact/calculation action is still split by the normal task path.
    if (_infer_april_ui_semantics(source) or _is_site_navigation_request(source)) and not _has_explicit_independent_non_ui_action(source):
        return [source]
    if _looks_like_previous_answer_followup(source):
        return [source]

    # A detailed 3D-scene prompt is one artifact task with many constraints, not
    # a collection of independent questions. Keep its formula, object counts,
    # geometry, axes, colours and interaction requirements bound together so the
    # Provider receives one coherent scene specification and memory is searched
    # once. Independent requests remain split by the established path below.
    parent_outputs = _detect_requested_outputs(source)
    starts_visual_build = bool(re.match(
        r"^\s*(?:построй(?:те)?|создай(?:те)?|покажи(?:те)?|сделай(?:те)?|нарисуй(?:те)?|визуализируй(?:те)?|побудуй(?:те)?|створи(?:те)?|build|create|show|make|draw|visuali[sz]e|plot)\b",
        source,
        flags=re.IGNORECASE,
    ))
    has_3d_scene_language = bool(re.search(
        r"(?:\b3\s*[- ]?d\b|\bthree[- ]dimensional\b|тр[её]хмерн\w*|3d[- ]?(?:поверхност|сцен|модел|визуализац))",
        source,
        flags=re.IGNORECASE,
    ))
    has_visual_artifact_noun = bool(re.search(
        r"(?:график\w*|диаграмм\w*|\bgraph\b|\bchart\b|\bplot\b|поверхност\w*|сфер\w*|куб\w*|треугольн\w*|воронк\w*|волн\w*|\bsurface\w*|\bsphere(?:s)?\b|\bcube(?:s)?\b|\bfunnel(?:s)?\b|\bmesh(?:es)?\b)",
        source,
        flags=re.IGNORECASE,
    ))
    only_graph_artifact_outputs = set(parent_outputs).issubset({"text", "graph"})
    if starts_visual_build and "graph" in parent_outputs and only_graph_artifact_outputs and (has_3d_scene_language or has_visual_artifact_noun) and not re.search(r"[?？]\s+\S", source):
        return [source]

    lines = [line.strip() for line in source.splitlines() if line.strip()] or [source]
    parts: list[str] = []
    for line in lines:
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)]|[a-zA-Z][.)])\s*", "", line).strip()
        if not line:
            continue
        # If the line itself is a question, a second interrogative clause after a
        # comma is a safe boundary. Do not apply this to commands like “напомни,
        # что ...”, where the second clause is the command's complement.
        question_lead = r"(?:что|кто|где|когда|почему|как|какой|какая|какие|чем|сколько|зачем|к\s+чему|о\s+чем|про\s+что|what|who|where|when|why|how|which)"
        if re.match(r"^" + question_lead + r"\b", line, flags=re.IGNORECASE):
            line = re.sub(r",\s+(?=" + question_lead + r"\b)", "; ", line, flags=re.IGNORECASE)
        # Question marks are strong boundaries. Also split sentence periods only
        # when the next sentence visibly starts another task/question, avoiding
        # ordinary explanatory sentences and most abbreviation false positives.
        boundary_pattern = re.compile(
            r"(?<=[?？])\s+|(?<=[.!])\s+(?=" + _TASK_OR_QUESTION_START + r")"
            r"|\s+(?:и|а также|а|and|also)\s+(?=" + question_lead + r"\b)",
            flags=re.IGNORECASE,
        )
        questions = [piece.strip() for piece in boundary_pattern.split(line) if piece.strip()]
        for question in questions or [line]:
            # A semicolon is an explicit task boundary even when there are only
            # two parts (one separator).
            semicolon_parts = [piece.strip() for piece in re.split(r"\s*;\s*", question) if piece.strip()]
            for part in semicolon_parts or [question]:
                parts.extend(_split_explicit_tasks(part) or [part])

    # Never collapse repeated steps: repetition can be intentional, and the output
    # sequence must stay one-to-one with the user's requested order.
    cleaned = [re.sub(r"\s+", " ", part).strip() for part in parts if part.strip()]
    if (len(cleaned) > 1 and _is_short_continuation_preface(cleaned[0])
            and _has_explicit_topic_introduction(cleaned[1])):
        # “Good, continue further” is a transition, not a retrieval task, when the
        # same message immediately introduces a different named subject.
        cleaned = cleaned[1:]
    if len(cleaned) > 24:
        # Keep every request, but combine the tail into one final ordered unit to
        # bound per-turn memory searches and prevent unbounded preprocessing time.
        cleaned = cleaned[:23] + ["; ".join(cleaned[23:])]
    return cleaned or [source]


def build_question_sequence(
    text: str,
    *,
    parent_interpretation: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Split a request only after intent pre-analysis; preserve intent per part.

    Existing splitting rules remain, with narrow support for coordinated questions.
    Added semantic fields are advisory and backward-compatible, allowing State
    Manager to choose retrieval scope before each question is searched.
    """
    sequence: list[dict[str, Any]] = []
    parent = dict(parent_interpretation or interpret_request_semantics(text))
    if _is_immediate_previous_message_reference(text):
        # This is a pointer to the immediately preceding USER↔APRIL exchange.
        # Keep the complete utterance intact; splitting it creates empty child
        # searches and loses the referent before State Manager can bind it.
        outputs = _enhance_requested_outputs(text, _detect_requested_outputs(text))
        return [{
            "step_index": 1, "request": _text(text),
            "output_types": outputs or ["text"], "answer_in_order": True,
            "semantic_intent": parent.get("primary_intent", "HISTORY_RECALL"),
            "search_direction": parent.get("direction", "SEARCH_DIALOGUE_HISTORY"),
            "time_scope": "IMMEDIATE_PREVIOUS_EXCHANGE",
            "topic_reference": "IMMEDIATE_PREVIOUS_USER_MESSAGE",
            "requires_memory": True, "history_request": True,
            "semantic_reason": "immediate_previous_message_reference_atomic",
            "parent_context_dependency": True,
            "context_signature": "IMMEDIATE_PREVIOUS_EXCHANGE",
            "action_contract": {
                "action": "ANSWER_FROM_IMMEDIATE_PREVIOUS_EXCHANGE",
                "output_types": outputs or ["text"],
                "must_not": ["не подменять предыдущий запрос архивным поиском", "не придумывать тему при отсутствии пары"],
            },
        }]
    pieces = _split_request_sequence(text)
    parent_introduces_subject = _has_explicit_topic_introduction(text)
    subject_intro_seen = False
    for index, item in enumerate(pieces, start=1):
        item_introduces_subject = _has_explicit_topic_introduction(item)
        item_has_anaphor = bool(re.search(
            r"\b(?:его|её|ее|он|она|они|ним|нему|него|ней|них|ему|ей|их|him|her|them|he|she|his|their)\b",
            item.lower().replace("ё", "е"), flags=re.IGNORECASE,
        ))
        inherits_current_request_subject = bool(
            parent_introduces_subject
            and index > 1
            and item_has_anaphor
            and not item_introduces_subject
            and (subject_intro_seen or _has_explicit_topic_introduction(" ".join(pieces[:index - 1])))
        )
        # Per-question output signals must use the same semantic enhancement as
        # the turn-level contract. Without this, INTERPRETATION could request a
        # diagram while REQUEST_SEQUENCE still tells Provider to return text only.
        outputs = _enhance_requested_outputs(item, _detect_requested_outputs(item))
        item_semantics = interpret_request_semantics(item)
        if (
            parent.get("requires_memory")
            and parent.get("topic_reference") == "PREVIOUS_ASSISTANT_ANSWER"
            and not item_introduces_subject
        ):
            item_semantics = {
                **item_semantics,
                "primary_intent": "TOPIC_CONTINUATION",
                "direction": "RESUME_OR_RETRIEVE_ACTIVE_TOPIC",
                "topic_reference": "PREVIOUS_ASSISTANT_ANSWER",
                "time_scope": parent.get("time_scope", "ACTIVE_DIALOGUE"),
                "requires_memory": True,
                "history_request": False,
                "search_scope": "TOPIC_OR_ACTIVE_CONTEXT",
                "relation_hint": "CONTINUE",
                "parent_context_dependency": True,
                "parent_intent": parent.get("primary_intent", "TOPIC_CONTINUATION"),
                "reason": "answer_followup_clause_inherited_parent_context",
            }
        # Restore omitted subjects in compact follow-on questions from the parent
        # intent: “... and what decisions did we reach?” is a prior-decision query
        # even when the child clause itself omits “we discussed this earlier”.
        _, item_tokens = _semantic_normalize(item)
        item_token_set = set(item_tokens)
        child_is_interrogative = bool(item_token_set & {"что", "какие", "какая", "какой", "к", "чему", "what", "which"}) or "?" in item or "？" in item
        child_has_decision = _semantic_group_hit(item_tokens, "decision_action") or (
            "пришли" in item_token_set and bool(item_token_set & {"к", "чему", "выводу"})
        )
        if parent.get("requires_memory") and child_is_interrogative and child_has_decision:
            item_semantics = {
                **item_semantics,
                "primary_intent": "PRIOR_DECISION_RECALL",
                "direction": "SEARCH_PRIOR_DECISIONS",
                "topic_reference": "PRIOR_DECISION",
                "time_scope": parent.get("time_scope", "AVAILABLE_HISTORY"),
                "requires_memory": True,
                "history_request": bool(parent.get("history_request")),
                "search_scope": parent.get("search_scope", "ALL_DIALOGUE_HISTORY"),
                "parent_context_dependency": True,
                "parent_intent": parent.get("primary_intent", "HISTORY_RECALL"),
                "reason": "decision_question_inherited_parent_history_context",
            }
        # A child task may need the parent context as source material (for
        # example, “remind me what we discussed and make a table of conclusions”).
        # Do not propagate history into a short but independent question such as
        # “what is photosynthesis?”; require an explicit referential/content cue.
        item_outputs = outputs or ["text"]
        has_independent_output_action = any(output != "text" for output in item_outputs)
        child_context_reference = bool(item_token_set & {
            "это", "этого", "этой", "этом", "тот", "та", "ту", "те", "эти", "их", "него", "нее", "неё",
            "там", "дальше", "прежнему", "прежней", "предыдущего", "предыдущей", "сказанного",
            "список", "перечень", "сводка", "содержание", "выводы", "решения", "итоги", "результаты",
            "topics", "summary", "conclusions", "decisions", "results", "list",
        }) or any(term in _text(item).lower().replace("ё", "е") for term in (
            "на основе", "по итогам", "из этого", "из обсуждения", "по предыдущему", "по сказанному",
        ))
        parent_context_dependency = bool(
            parent.get("requires_memory")
            and item_semantics.get("primary_intent") == "NEW_INFORMATION"
            and (child_context_reference or (has_independent_output_action and child_has_decision))
        )
        if parent_context_dependency:
            item_semantics = {
                **item_semantics,
                "requires_memory": True,
                "history_request": bool(parent.get("history_request")),
                "search_scope": parent.get("search_scope", "TOPIC_OR_ACTIVE_CONTEXT"),
                "parent_context_dependency": True,
                "parent_intent": parent.get("primary_intent", "NEW_INFORMATION"),
                "reason": "child_action_uses_parent_context",
            }
        action_contract = _build_action_contract_for_step(item, item_semantics, outputs or ["text"], index)
        sequence.append({
            "step_index": index,
            "request": item,
            "output_types": action_contract.get("output_types") or outputs or ["text"],
            "answer_in_order": True,
            "semantic_intent": item_semantics.get("primary_intent", "NEW_INFORMATION"),
            "search_direction": item_semantics.get("direction", "ANSWER_NEW_REQUEST"),
            "time_scope": item_semantics.get("time_scope", "UNSPECIFIED"),
            "topic_reference": item_semantics.get("topic_reference", "UNSPECIFIED"),
            "requires_memory": bool(item_semantics.get("requires_memory")),
            "history_request": bool(item_semantics.get("history_request")),
            "semantic_reason": item_semantics.get("reason", ""),
            "context_signature": item_semantics.get("context_signature") or _context_signature(item),
            "parent_context_dependency": bool(item_semantics.get("parent_context_dependency")),
            "parent_intent": item_semantics.get("parent_intent", ""),
            "introduces_current_request_subject": item_introduces_subject,
            "inherits_current_request_subject": inherits_current_request_subject,
            "action_contract": action_contract,
        })
        if item_introduces_subject:
            subject_intro_seen = True
    return sequence


def _build_question_sequence(text: str) -> list[dict[str, Any]]:
    """Compatibility alias for existing interpretation callers."""
    return build_question_sequence(text)


_CODE_MODIFICATION_MARKERS = (
    "исправь код", "исправь этот код", "улучши код", "улучши этот код",
    "улучшить код", "оптимизируй код", "перепиши код", "обнови код",
    "исправь скрипт", "перепиши скрипт", "fix this code", "improve this code",
    "refactor this code", "optimize this code", "rewrite this code",
)

def _is_code_modification_request(text: str) -> bool:
    low = _text(text).lower().replace("ё", "е")
    return any(marker.replace("ё", "е") in low for marker in _CODE_MODIFICATION_MARKERS)


def _prior_free_image_edit_notice_count(memory: dict[str, Any]) -> int:
    """Count prior replies that actually refused an image edit in Free.

    A note that merely says generated images are new and source photos remain
    unchanged is not a refusal, and must not make the next edit attempt sound
    like a repeated warning.
    """
    if not isinstance(memory, dict):
        return 0
    pairs: list[Any] = []
    seen_pairs: set[str] = set()
    # Check candidates too: a follow-up insistence may be classified as NEW,
    # leaving the last assistant refusal outside selected_pairs.
    for source_name in ("selected_pairs", "candidates"):
        source = memory.get(source_name)
        if not isinstance(source, list):
            continue
        for pair in source[:12]:
            try:
                fingerprint = json.dumps(pair, ensure_ascii=False, sort_keys=True, default=str)
            except Exception:
                fingerprint = str(pair)
            if fingerprint in seen_pairs:
                continue
            seen_pairs.add(fingerprint)
            pairs.append(pair)
    notice_markers = (
        "редактирование изображений доступно только в premium",
        "редактирование и улучшение изображений доступно только в premium",
        "изменение изображений доступно только в premium",
        "image editing is available only in premium",
        "editing and enhancing images is available only in premium",
        "редагування зображень доступне тільки в premium",
        "редагування зображень доступне лише в premium",
        "la retouche d’image est disponible uniquement avec premium",
        "la modification des images est disponible uniquement avec premium",
    )
    refusal_markers = (
        "не могу изменить", "не могу изменять", "не могу изменять уже создан",
        "не могу редактировать", "не могу изменить уже создан",
        "не могу отредактировать", "не могу изменить фото", "не могу изменить диаграм",
        "cannot edit", "can't edit", "cannot modify", "can't modify", "unable to edit",
        "не можу змінити", "не можу змінювати", "не можу редагувати",
        "impossible de modifier", "je ne peux pas modifier", "mais pas modifier",
    )
    count = 0
    for pair in pairs:
        try:
            rendered = json.dumps(pair, ensure_ascii=False, default=str).lower().replace("ё", "е")
        except Exception:
            rendered = str(pair).lower().replace("ё", "е")
        has_premium_notice = (
            any(marker.replace("ё", "е") in rendered for marker in notice_markers)
            or bool(re.search(r"редактир\w*.{0,80}доступн\w*.{0,30}premium", rendered))
            or bool(re.search(r"(?:editing|edit|modification).{0,80}available.{0,30}premium", rendered))
            or bool(re.search(r"premium.{0,30}(?:editing|edit|modification)", rendered))
        )
        if has_premium_notice and any(marker.replace("ё", "е") in rendered for marker in refusal_markers):
            count += 1
    return min(count, 5)


def _active_branch_has_diagram_artifact(memory: dict[str, Any]) -> bool:
    """Check the selected same-dialogue branch for a stored vector diagram."""
    if not isinstance(memory, dict) or _text(memory.get("relation")).upper() != "CONTINUE":
        return False
    collections: list[Any] = [memory.get("active_branch_artifact_index")]
    for pair in _select_continuation_pairs(memory):
        if not isinstance(pair, dict):
            continue
        collections.extend((
            pair.get("assistant_artifact_index"),
            (pair.get("branch_digest") or {}).get("artifact_refs") if isinstance(pair.get("branch_digest"), dict) else None,
            (pair.get("dialogue_state") or {}).get("source_artifact_index") if isinstance(pair.get("dialogue_state"), dict) else None,
        ))
        previous_request = _text(
            pair.get("source_user_text") or pair.get("user_text") or pair.get("user")
            or pair.get("request") or pair.get("question")
        )
        if previous_request and "diagram" in _detect_requested_outputs(previous_request):
            return True
    for collection in collections:
        if not isinstance(collection, list):
            continue
        for artifact in collection:
            if not isinstance(artifact, dict):
                continue
            descriptor = " ".join(
                _text(artifact.get(key)) for key in (
                    "kind", "type", "artifact_type", "output_type", "renderer",
                    "viewer", "representation", "mime_type",
                )
            ).lower().replace("_", "").replace("-", "")
            if any(marker in descriptor for marker in (
                "diagram", "flowchart", "schematic", "svgblock", "navigationmap",
            )):
                return True
    return False


def _is_active_diagram_revision_followup(text: Any, memory: Any) -> bool:
    """Carry the diagram renderer through an elliptical correction of its branch."""
    low = _text(text).lower().replace("ё", "е")
    if not low or not isinstance(memory, dict):
        return False
    if not _active_branch_has_diagram_artifact(memory):
        return False
    return bool(re.match(
        r"^\s*(?:(?:ну|а|и|теперь|тогда|давай|пожалуйста)\s+)*"
        r"(?:поправ\w*|исправ\w*|передел\w*|перерис\w*|измен\w*|"
        r"обнов\w*|добав\w*|убер\w*|перемест\w*|перестав\w*|сдвин\w*|"
        r"correct\w*|fix\w*|revise\w*|redraw\w*|update\w*|change\w*|"
        r"move\w*|add\w*|remove\w*)\b",
        low, re.IGNORECASE,
    ))


def _active_branch_has_code_request(memory: dict[str, Any]) -> bool:
    """Return True only when selected same-dialogue evidence contains a code task."""
    if _text(memory.get("relation")).upper() != "CONTINUE":
        return False
    pairs = _select_continuation_pairs(memory)
    for pair in reversed(pairs):
        if not isinstance(pair, dict):
            continue
        prior_user_text = _text(
            pair.get("source_user_text") or pair.get("user_text") or pair.get("user_message")
            or pair.get("user") or pair.get("request") or pair.get("question")
        )
        if prior_user_text and "code" in _detect_requested_outputs(prior_user_text):
            return True
    return False


def _is_file_delivery_followup(text: str) -> bool:
    """Identify a correction/ellipsis that asks for the file from the active task."""
    low = _text(text).lower().replace("ё", "е")
    return bool(
        "file" in _detect_requested_outputs(low)
        and re.search(
            r"(?:\bя\s+же\b|\bведь\b|\bуже\b|\bповторн\w*\b|\bеще\s+раз\b|"
            r"\bв\s+файл\w*\b|\bфайлом\b|\bсам\s+файл\w*\b|"
            r"\bпришл\w*\b.{0,55}\bфайл\w*\b|\bприсла\w*\b.{0,55}\bфайл\w*\b)",
            low, re.I | re.S,
        )
    )



def _assistant_open_question_profile(answer_text: Any) -> dict[str, Any]:
    """Extract the response slots left open by April's latest answer.

    Questions are treated as discourse slots, not keyword/game triggers. Keep
    several slots because a natural answer can ask the user more than one thing.
    The final slot remains the default when the user gives one compact reply.
    """
    answer = _text(answer_text)
    if not answer:
        return {}

    question_matches = list(re.finditer(r"([^.!?\n]{1,260}[?？])", answer))
    question_texts = [_text(match.group(1)) for match in question_matches[-4:]]
    invitation = re.search(
        r"\b(?:выбери(?:те)?|выбирай|ответь(?:те)?|напиши(?:те)?|пришли(?:те)?|"
        r"загрузи(?:те)?|покажи(?:те)?|укажи(?:те)?|скажи(?:те)?|назови(?:те)?|"
        r"опиши(?:те)?|перечисли(?:те)?|подтверди(?:те)?|уточни(?:те)?|"
        r"choose|pick\s+(?:one|an option)|your\s+turn|your\s+move|send\s+me|"
        r"specify|describe|name\s+(?:the|a)\b|tell\s+me)\b",
        answer, re.IGNORECASE,
    )
    if not question_texts and not invitation:
        return {}

    def classify(question: str, fallback_text: str = "") -> dict[str, Any]:
        low = (question or fallback_text).lower().replace("ё", "е")
        if re.search(
            r"\b(?:как\s+(?:у\s+тебя\s+)?дела|как\s+ты|как\s+поживаешь|"
            r"как\s+сам(?:а)?|как\s+себя\s+чувствуешь|how\s+are\s+you|"
            r"how(?:'|’)s\s+it\s+going|how\s+are\s+things)\b",
            low,
        ):
            kind = "SOCIAL_STATUS"
        elif re.search(r"\b(?:что\s+это|кто\s+это|что\s+за\s+\w+|what\s+is\s+it|who\s+is\s+it)\b", low):
            kind = "IDENTIFICATION"
        elif re.search(
            r"\b(?:или\s+нет|правильно\s+ли|верно\s+ли|угадал\s+ли|согласен\s+ли|"
            r"согласна\s+ли|согласны\s+ли|ты\s+согласен|вы\s+согласны|"
            r"все\s+(?:понятно|понятно\s+ли)|всё\s+(?:понятно|понятно\s+ли)|"
            r"тебе\s+(?:понятно|подходит|удобно|нравится)|вам\s+(?:понятно|подходит|удобно)|"
            r"ты\s+(?:готов|готова|хочешь|согласен|согласна)|вы\s+(?:готовы|хотите|согласны)|"
            r"do\s+you\s+agree|is\s+that\s+correct|did\s+i\s+get\s+it\s+right|"
            r"does\s+that\s+work|are\s+you\s+ready|is\s+it\s+okay|would\s+you\s+like)\b",
            low,
        ):
            kind = "CONFIRMATION"
        elif re.search(r"\b(?:какой|какая|какое|который|какие|что\s+из|which|what\s+option|choose)\b", low):
            kind = "CHOICE_OR_ATTRIBUTE"
        elif question:
            kind = "OPEN_ANSWER"
        else:
            kind = "USER_INPUT_REQUEST"
        # An inspectable discourse vector records what kind of response the
        # assistant's question is waiting for. It is a structured feature vector,
        # not a fabricated neural embedding or a confidence score.
        dimensions = {
            "status_response": 0.0,
            "entity_or_concept_answer": 0.0,
            "yes_no_confirmation": 0.0,
            "option_selection": 0.0,
            "free_response": 0.0,
        }
        vector_key = {
            "SOCIAL_STATUS": "status_response",
            "IDENTIFICATION": "entity_or_concept_answer",
            "CONFIRMATION": "yes_no_confirmation",
            "CHOICE_OR_ATTRIBUTE": "option_selection",
            "OPEN_ANSWER": "free_response",
            "USER_INPUT_REQUEST": "free_response",
        }.get(kind, "free_response")
        dimensions[vector_key] = 1.0
        return {
            "kind": kind,
            "question": question[:280],
            "expects_user_input": True,
            "semantic_vector": dimensions,
        }

    slots = [classify(question) for question in question_texts]
    if not slots and invitation:
        slots = [classify("", answer)]
    if not slots:
        return {}
    latest = dict(slots[-1])
    latest.update({
        "expects_user_input": True,
        "questions": slots,
        "invitation": _text(invitation.group(0))[:80] if invitation else "",
    })
    return latest


def _reply_to_open_question_profile(user_text: Any, slot: dict[str, Any]) -> dict[str, Any]:
    """Match one or more user answer clauses to April's pending question slots.

    The matcher follows conversational acts and expected answer shape. It does
    not require repeated subject words, game vocabulary, or a similarity score.
    It can preserve several answers plus an appended request/question in one turn.
    """
    source = _text(user_text)
    if not source or not isinstance(slot, dict) or not slot.get("expects_user_input"):
        return {"matched": False}
    low = source.lower().replace("ё", "е")
    if re.search(r"^\s*(?:кто\s+так(?:ой|ая|ое)|что\s+такое|что\s+(?:значит|означает)|what\s+is|who\s+is)\s+\S+", low):
        return {"matched": False, "reason": "self_contained_definition_question"}
    slots = slot.get("questions") if isinstance(slot.get("questions"), list) else [slot]
    slots = [item for item in slots if isinstance(item, dict) and item.get("expects_user_input")]
    if not slots:
        slots = [slot]

    def social_status_answer(value: str) -> tuple[bool, str]:
        match = re.search(
            r"^\s*(?:(?:ну|да|ага|угу|тоже|у\s+меня|а\s+у\s+меня|я|все|всё)\s+){0,4}"
            r"(?:все\s+хорошо|всё\s+хорошо|так\s+себе|не\s+плохо|более-менее|"
            r"хорош\w*|отлич\w*|прекрас\w*|замечательн\w*|норм\w*|неплох\w*|"
            r"супер|класс\w*|плох\w*|ужас\w*|паршив\w*|тяжел\w*|устал\w*|устала\w*|"
            r"занят\w*|бодр\w*|нічог\w*|добре|чудов\w*|гарн\w*|нормальн\w*|"
            r"good|fine|great|well|okay|ok|not\s+bad|bad|tired|busy)\b",
            value.lower().replace("ё", "е"), re.IGNORECASE,
        )
        return bool(match), _text(value[:match.end()]).strip(" ,;—:-") if match else ""

    def yes_no_answer(value: str) -> tuple[bool, str]:
        match = re.match(
            r"^\s*(?:да|нет|ага|угу|конечно|верно|точно|правильно|неверно|согласен|согласна|"
            r"согласны|не\s+согласен|не\s+согласна|yes|no|yeah|nope|correct|right|agree)\b",
            value.lower().replace("ё", "е"), re.IGNORECASE,
        )
        return bool(match), _text(value[:match.end()]).strip(" ,;—:-") if match else ""

    instruction_start = re.compile(
        r"^\s*(?:привет|здравствуй|доброе\s+утро|добрый\s+день|добрый\s+вечер|hello|hi|"
        r"почему|зачем|как\s+ты|а\s+ты|а\s+вы|что\s+думаешь|как\s+думаешь|"
        r"давай(?:те)?|(?:а\s+)?хочу|(?:а\s+)?можешь|(?:а\s+)?можно|(?:а\s+)?нужно|"
        r"помоги(?:те)?|пообщаемся|поговорим|обсудим|"
        r"расскажи|объясни|создай|сделай|найди|проверь|покажи|сравни|подготовь|"
        r"перечисли|напиши|построй|вычисли|сгенерируй|измени|исправь|"
        r"давай\s+(?:создадим|сделаем|найдем|найдём)|why|how\s+are\s+you|"
        r"tell\s+me|explain|create|make|find|check|show|compare|prepare|write|build|generate)\b",
        re.IGNORECASE,
    )
    imperative_start = re.compile(
        r"^\s*(?:расскажи|объясни|создай|сделай|найди|проверь|покажи|сравни|подготовь|"
        r"перечисли|напиши|построй|вычисли|сгенерируй|измени|исправь|"
        r"давай\s+(?:создадим|сделаем|найдем|найдём)|create|make|tell|explain|show|"
        r"find|check|compare|prepare|write|build|generate|edit)\b",
        re.IGNORECASE,
    )
    topic_switch_start = re.compile(
        r"^\s*(?:новая\s+тема|другая\s+тема|другую\s+тему|другой\s+вопрос|"
        r"перейдем\s+к|перейдём\s+к|switch\s+topics|new\s+topic)\b",
        re.IGNORECASE,
    )
    topic_switch_any = re.compile(
        r"\b(?:новая\s+тема|другая\s+тема|другую\s+тему|другой\s+вопрос|"
        r"перейдем\s+к|перейдём\s+к|switch\s+topics|new\s+topic)\b",
        re.IGNORECASE,
    )
    filler_only = re.compile(r"^\s*(?:ответ|ответь|вот|например|ну|то\s+есть|answer|for\s+example)\s*$", re.IGNORECASE)

    # Preserve segment order. Punctuation and an appended imperative can divide
    # answers from one another without requiring the user to write a new message.
    split_pattern = re.compile(
        r"[,;—:]|[?？]|(?<!\d)\.(?!\d)(?=\s|$)|"
        r"(?=\b(?:а\s+теперь|давай(?:те)?|теперь|и\s+еще|и\s+ещё|"
        r"а\s+(?:ты|вы|что|как|почему|зачем|если|когда|где|можно|можешь|хочу)|"
        r"и\s+(?:что|как|почему|зачем|где|когда)|"
        r"новая\s+тема|другая\s+тема|другую\s+тему|другой\s+вопрос|switch\s+topics|new\s+topic|"
        r"and\s+now|now|also)\b)|"
        r"(?=\b(?:хочу|можешь|можно|нужно|помоги(?:те)?|пообщаемся|поговорим|обсудим)\b)|"
        r"(?=\b(?:создай(?:те)?|сделай(?:те)?|расскажи(?:те)?|объясни(?:те)?|"
        r"покажи(?:те)?|найди(?:те)?|проверь(?:те)?|сравни(?:те)?|перечисли(?:те)?|"
        r"подготовь(?:те)?|напиши(?:те)?|построй(?:те)?|вычисли(?:те)?|сгенерируй(?:те)?|"
        r"измени(?:те)?|исправь(?:те)?|create|make|tell|explain|show|find|check|compare|"
        r"prepare|write|build|generate|edit)\b)",
        re.IGNORECASE,
    )
    chunks: list[str] = []
    cursor = 0
    for boundary in split_pattern.finditer(source):
        part = _text(source[cursor:boundary.start()]).strip(" ,;—:-")
        if part:
            chunks.append(part)
        cursor = boundary.end()
    final_part = _text(source[cursor:]).strip(" ,;—:-")
    if final_part:
        chunks.append(final_part)
    if not chunks:
        chunks = [source.strip()]

    answered_indices: set[int] = set()
    answer_records: list[dict[str, Any]] = []
    remainder_parts: list[str] = []

    for chunk in chunks:
        if not chunk or filler_only.fullmatch(chunk):
            continue
        if topic_switch_start.match(chunk):
            remainder_parts.append(chunk)
            continue
        if instruction_start.match(chunk):
            remainder_parts.append(chunk)
            continue
        social_match, social_clause = social_status_answer(chunk)
        yes_match, yes_clause = yes_no_answer(chunk)
        selected_index = -1
        selected_kind = ""
        selected_clause = ""

        # Typed replies are mapped by their discourse act, even if another
        # question appeared later in April's answer.
        if social_match:
            selected_index = next((i for i, item in enumerate(slots)
                                   if i not in answered_indices and _text(item.get("kind")) == "SOCIAL_STATUS"), -1)
            selected_kind = "SOCIAL_STATUS"
            selected_clause = social_clause
        elif yes_match:
            selected_index = next((i for i, item in enumerate(slots)
                                   if i not in answered_indices and _text(item.get("kind")) == "CONFIRMATION"), -1)
            selected_kind = "CONFIRMATION"
            selected_clause = yes_clause
        else:
            # A question/request is a second conversational move, not an answer.
            if instruction_start.match(chunk) or re.match(
                r"^\s*(?:(?:и|а)\s+)?(?:что|кто|как|почему|зачем|где|когда|what|who|how|why|where|when)\b",
                chunk.lower().replace("ё", "е"), re.IGNORECASE,
            ):
                remainder_parts.append(chunk)
                continue
            # General entity, option or open-answer clauses are matched to the
            # earliest still-unanswered compatible slot. This lets a turn answer
            # both "How are you?" and a second independent open question.
            selected_index = next((i for i, item in enumerate(slots)
                                   if i not in answered_indices and _text(item.get("kind")) in {
                                       "IDENTIFICATION", "CHOICE_OR_ATTRIBUTE", "OPEN_ANSWER", "USER_INPUT_REQUEST"
                                   }), -1)
            if selected_index >= 0:
                selected_kind = _text(slots[selected_index].get("kind")) or "OPEN_ANSWER"
                selected_clause = chunk

        if selected_index >= 0 and selected_clause:
            answered_indices.add(selected_index)
            answer_records.append({
                "question_index": selected_index,
                "kind": selected_kind,
                "question": _text(slots[selected_index].get("question"))[:220],
                "reply_clause": selected_clause[:180],
            })
        else:
            remainder_parts.append(chunk)

    if not answer_records:
        return {"matched": False, "reason": "reply_not_aligned_to_open_slot"}

    # Remove conversational filler from the appended text; keep every substantive
    # new move for April to answer after acknowledging the response(s).
    remainder = " ".join(part for part in remainder_parts if part and not filler_only.fullmatch(part)).strip()
    remainder_terms = set(_semantic_normalize(remainder)[1])
    remainder_is_question = bool(re.search(
        r"[?？]|\b(?:а\s+(?:ты|вы|что|как|почему|зачем)|и\s+(?:что|как|почему|зачем)|что\s+думаешь|как\s+думаешь|"
        r"why|how\s+about|what\s+do\s+you)\b", remainder, re.IGNORECASE,
    ))
    # The splitter consumes '?' as a clause boundary. Restore it on a retained
    # question so the Provider sees the user's actual interrogative move, not
    # merely the words that happened to follow the answer.
    if remainder_is_question and remainder and not re.search(r"[?？]\s*$", remainder):
        remainder = remainder.rstrip(" .!…") + "?"
    remainder_is_imperative = bool(imperative_start.match(remainder))
    remainder_is_topic_switch = bool(topic_switch_any.search(remainder))
    remainder_is_request = bool(
        remainder_is_imperative
        or re.search(
            r"\b(?:давай(?:те)?|хочу|можешь|можно|нужно|помоги|помогите|пообщаемся|поговорим|обсудим|"
            r"придумай|предложи|составь|подготовь|сделай|создай|найди|покажи|"
            r"расскажи|объясни|проверь|сравни|build|create|help|could\s+you|can\s+you)\b",
            remainder, re.IGNORECASE,
        )
    )
    meaningful_remainder = bool(remainder_terms or remainder_is_question or remainder_is_request or remainder_is_topic_switch)
    mixed = bool(remainder and meaningful_remainder)
    reciprocal_question = bool(re.search(
        r"\b(?:а\s+ты|а\s+вы|ты\s+как\s+думаешь|вы\s+как\s+думаете|"
        r"что\s+ты\s+думаешь|what\s+do\s+you\s+think|and\s+you)\b",
        remainder, re.IGNORECASE,
    ))
    reply_vector = {
        "status_response": 0.0,
        "entity_or_concept_answer": 0.0,
        "yes_no_confirmation": 0.0,
        "option_selection": 0.0,
        "free_response": 0.0,
        "reciprocal_question": 1.0 if reciprocal_question else 0.0,
        "followup_question": 1.0 if remainder_is_question else 0.0,
        "new_request": 1.0 if mixed and remainder_is_request else 0.0,
    }
    kind_dimensions = {
        "SOCIAL_STATUS": "status_response",
        "IDENTIFICATION": "entity_or_concept_answer",
        "CONFIRMATION": "yes_no_confirmation",
        "CHOICE_OR_ATTRIBUTE": "option_selection",
        "OPEN_ANSWER": "free_response",
        "USER_INPUT_REQUEST": "free_response",
    }
    for record in answer_records:
        dimension = kind_dimensions.get(record["kind"], "free_response")
        reply_vector[dimension] = 1.0
    move_vector = {
        "answer_to_april_question": 1.0,
        "new_request": 1.0 if mixed and remainder_is_request else 0.0,
        "reciprocal_question": 1.0 if reciprocal_question else 0.0,
        "followup_question": 1.0 if remainder_is_question else 0.0,
        "topic_switch": 1.0 if remainder_is_topic_switch else 0.0,
    }
    reply_clauses = [record["reply_clause"] for record in answer_records]
    answer_kinds = list(dict.fromkeys(record["kind"] for record in answer_records))
    combined_kind = answer_kinds[0] if len(answer_kinds) == 1 else "MULTIPLE_RESPONSE"
    return {
        "matched": True,
        "kind": combined_kind,
        "question_index": answer_records[-1]["question_index"],
        "answered_question_indices": [record["question_index"] for record in answer_records],
        "reply_clause": "; ".join(reply_clauses)[:240],
        "reply_clauses": answer_records[:4],
        "reply_semantic_vector": reply_vector,
        "dialogue_move_vector": move_vector,
        "remainder_request": remainder[:420] if mixed else "",
        "mixed_reply_and_new_request": mixed,
        "explicit_topic_switch_after_answer": remainder_is_topic_switch,
        "reason": "multiple_open_questions_answered" if len(answer_records) > 1 else (
            "answer_clause_followed_by_new_request" if mixed else "answer_to_open_question"
        ),
    }

def interpret_request_in_context(
    text: Any,
    latest_exchange: dict[str, Any] | None,
    semantic_interpretation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Interpret a new turn against the latest USER↔APRIL exchange first.

    This is a local, deterministic discourse pass: it makes no model/API call and
    does not perform memory retrieval. It enriches the request interpretation with
    evidence from the last saved user turn and April answer, leaving the raw request
    untouched. State Manager decides whether a matched older branch is needed only
    after this latest-exchange pass.
    """
    source = _text(text)
    profile = dict(semantic_interpretation or interpret_request_semantics(source) or {})
    if is_april_identity_question(source) or is_current_user_name_question(source) or is_bare_visual_command(source):
        identity_question = is_april_identity_question(source)
        user_name_question = is_current_user_name_question(source)
        identity_topic = "APRIL_PROJECT_IDENTITY" if identity_question else ("CURRENT_USER_PROFILE" if user_name_question else "UNSPECIFIED")
        identity_reason = ("independent_april_project_identity_question" if identity_question else ("authenticated_user_name_question" if user_name_question else "bare_visual_command_needs_subject"))
        profile.update({
            "primary_intent": "NEW_INFORMATION", "direction": "ANSWER_NEW_REQUEST",
            "topic_reference": identity_topic, "requires_memory": False,
            "history_request": False, "search_scope": "CURRENT_DIALOGUE", "relation_hint": "NEW",
            "explicit_topic_switch": True, "explicit_topic_introduction": True,
            "previous_answer_reference": False, "active_branch_repair": False,
            "reason": identity_reason,
            "latest_exchange_analysis": {
                "available": bool(latest_exchange), "linked": False,
                "reason": "explicit_april_identity_question_is_independent_of_previous_topic" if identity_question else ("current_user_name_question_uses_authenticated_profile" if user_name_question else "bare_visual_command_waits_for_object"),
                "has_independent_payload": True,
            },
            "features": {**(profile.get("features") if isinstance(profile.get("features"), dict) else {}),
                         "context_dependent_question": False, "context_dependent_reaction": False,
                         "answer_followup": False, "explicit_topic_switch": True,
                         "has_independent_payload": True},
        })
        return profile
    row = latest_exchange if isinstance(latest_exchange, dict) else {}
    previous_user = _text(
        row.get("user_text") or row.get("user") or row.get("user_request")
        or row.get("request") or row.get("question")
    )
    previous_answer = _text(
        row.get("april_text") or row.get("april") or row.get("assistant_last_message")
        or row.get("assistant_answer") or row.get("answer") or row.get("april_summary")
    )
    if not (previous_user or previous_answer) or not source.strip():
        profile.setdefault("latest_exchange_analysis", {
            "available": bool(previous_user or previous_answer),
            "linked": False,
            "reason": "no_latest_exchange_or_empty_request",
        })
        return profile

    # Read the question April actually left open before judging the new user turn.
    # This catches answers such as a one-word guess and mixed social reply + request.
    open_question = _assistant_open_question_profile(previous_answer)
    open_question_reply = _reply_to_open_question_profile(source, open_question)
    reply_to_open_question = bool(open_question_reply.get("matched"))
    secondary_topic_switch = bool(
        reply_to_open_question and open_question_reply.get("explicit_topic_switch_after_answer")
    )
    if secondary_topic_switch:
        profile["explicit_topic_switch"] = False
        profile["explicit_topic_introduction"] = False
        profile["secondary_topic_switch"] = True
        feature_map = dict(profile.get("features") or {})
        feature_map["explicit_topic_switch"] = False
        feature_map["secondary_topic_switch_after_answer"] = True
        profile["features"] = feature_map
        pragmatic_map = dict(profile.get("pragmatic_features") or {})
        pragmatic_map["secondary_topic_switch_after_answer"] = True
        profile["pragmatic_features"] = pragmatic_map

    low, current_tokens_list = _semantic_normalize(source)
    previous_user_tokens = set(_semantic_normalize(previous_user)[1])
    previous_answer_tokens = set(_semantic_normalize(previous_answer[:9000])[1])
    current_tokens = set(current_tokens_list)

    # Function words and pronouns are not enough to connect two different tasks.
    # Retain content nouns, verbs and a separately measured shared speech-act term.
    neutral = {
        "я", "меня", "мне", "мной", "мой", "моя", "мое", "моё", "мои",
        "ты", "тебя", "тебе", "тобой", "твой", "твоя", "твое", "твоё", "твои",
        "мы", "нас", "нам", "нами", "наш", "наша", "наше", "наши", "вы", "вас", "вам",
        "и", "а", "но", "да", "нет", "ну", "так", "это", "этот", "эта", "эти", "того", "этого",
        "для", "при", "про", "что", "чем", "чего", "как", "где", "когда", "почему", "зачем",
        "мне", "моя", "свой", "своя", "свои", "своего", "своей", "своем", "своём",
        "the", "a", "an", "i", "me", "my", "you", "your", "we", "our", "us",
        "and", "or", "but", "what", "which", "how", "where", "when", "why", "for", "to", "of", "in", "on",
    }
    dialogue_verbs = (
        "сказ", "говор", "спрос", "ответ", "благодар", "спасиб", "поблагодар",
        "повтор", "переповтор", "пересказ", "объясн", "уточн", "поясн",
        "said", "tell", "asked", "answered", "thank", "repeat", "restate", "explain",
    )

    def content_terms(tokens: set[str]) -> set[str]:
        result = set()
        for token in tokens:
            if token in neutral or len(token) < 3:
                continue
            if any(token.startswith(root) for root in dialogue_verbs):
                continue
            if _is_context_signature_generic(token):
                # Interpersonal terms (gratitude/praise) are retained separately
                # below because they can identify what the user is referring to.
                continue
            result.add(token[:6] if len(token) > 6 else token)
        return result

    current_content = content_terms(current_tokens)
    prior_user_content = content_terms(previous_user_tokens)
    prior_answer_content = content_terms(previous_answer_tokens)

    def overlap(current: set[str], previous: set[str]) -> tuple[float, int]:
        if not current or not previous:
            return 0.0, 0
        common = 0
        for item in current:
            if item in previous or any(
                len(other) >= 4 and len(item) >= 4
                and (item.startswith(other[:5]) or other.startswith(item[:5]))
                for other in previous
            ):
                common += 1
        # Measure how much of the CURRENT request is explained by the prior
        # turn. Dividing by the smaller set made a new request look like a match
        # whenever it reused two generic terms from an older, shorter question.
        return common / max(1, len(current)), common

    user_overlap, user_common = overlap(current_content, prior_user_content)
    answer_overlap, answer_common = overlap(current_content, prior_answer_content)
    quoted_spans = re.findall(r"[\"'«“](.{1,100}?)[\"'»”]", source)
    quoted_terms = set()
    for quoted_span in quoted_spans:
        quoted_terms.update(_semantic_normalize(quoted_span)[1])
    quoted_user_matches = quoted_terms & previous_user_tokens
    if quoted_user_matches:
        user_overlap = max(user_overlap, 0.30)
        user_common += len(quoted_user_matches)

    pragmatic = profile.get("pragmatic_features") if isinstance(profile.get("pragmatic_features"), dict) else {}
    act_profile = profile.get("dialogue_act_profile") if isinstance(profile.get("dialogue_act_profile"), dict) else {}
    act_pragmatic = act_profile.get("pragmatic_features") if isinstance(act_profile.get("pragmatic_features"), dict) else {}
    features = profile.get("features") if isinstance(profile.get("features"), dict) else {}
    # Merge both known shapes: Free and Premium have evolved independently over time.
    signals = dict(act_pragmatic)
    signals.update(pragmatic)

    # Social/pragmatic intent comes from the interpretation layer's speech-act
    # profile. This pass only binds that act to the latest saved exchange.
    gratitude = bool(signals.get("gratitude"))
    positive = bool(signals.get("positive_evaluation"))
    acknowledgement = bool(signals.get("acknowledgement_or_agreement") or signals.get("waiting_acknowledgement"))
    disagreement = bool(signals.get("negation_or_disagreement") or signals.get("correction"))
    dissatisfaction = bool(signals.get("frustration_or_dissatisfaction") or signals.get("revision_request"))
    contextual_question = bool(
        profile.get("context_dependent_question")
        or signals.get("context_dependent_question")
        or features.get("context_dependent_question")
    )
    contextual_reaction = bool(
        profile.get("context_dependent_reaction")
        or signals.get("context_dependent_reaction")
        or features.get("context_dependent_reaction")
    )
    previous_answer_reference = bool(
        profile.get("previous_answer_reference")
        or profile.get("active_branch_repair")
        or features.get("previous_answer_reference")
        or features.get("active_branch_repair")
        or signals.get("previous_answer_reference")
        or signals.get("active_branch_repair")
    )
    explicit_switch = bool(profile.get("explicit_topic_switch") or profile.get("explicit_topic_introduction"))

    # A complaint about April repeating/restating history mentions the same words
    # as a recall request, but its communicative act is correction of the last answer.
    assistant_repetition_feedback = bool(
        re.search(r"\b(?:ты|вы|you)\b.{0,110}\b(?:повтор\w*|переповтор\w*|пересказ\w*|повторя\w*|repeat\w*|restate\w*)\b", low, re.I | re.S)
        and re.search(r"\b(?:истори\w*|диалог\w*|разговор\w*|переписк\w*|history|conversation|chat)\b", low, re.I)
        and re.search(r"\b(?:зачем|почему|опять|снова|постоянно|why|again|always)\b", low, re.I)
    )
    if assistant_repetition_feedback:
        profile["history_request"] = False
        profile["history_recall"] = False
        profile["requires_memory"] = True
        profile["search_scope"] = "LATEST_EXCHANGE"
        profile["primary_intent"] = "TOPIC_CONTINUATION"
        profile["direction"] = "RECHECK_PREVIOUS_ANSWER"
        profile["topic_reference"] = "PREVIOUS_ASSISTANT_ANSWER"
        profile["time_scope"] = "ACTIVE_DIALOGUE"
        profile["relation_hint"] = "CONTINUE"
        profile["active_branch_repair"] = True
        profile["previous_answer_reference"] = True
        profile["reason"] = "assistant_response_feedback_not_history_recall"
        signals.update({
            "correction": True,
            "frustration_or_dissatisfaction": True,
            "active_branch_repair": True,
            "previous_answer_reference": True,
            "context_dependent_reaction": True,
        })
        disagreement = True
        dissatisfaction = True
        contextual_reaction = True

    # A self-contained new request wins unless it is demonstrably tied to the
    # immediately preceding exchange. Short social acts are context-bound when
    # they carry no independent subject/deliverable of their own.
    signature = _context_signature(source)
    output_forms = signature.get("output_forms") if isinstance(signature.get("output_forms"), list) else []
    numeric_anchors = signature.get("numeric_anchors") if isinstance(signature.get("numeric_anchors"), list) else []
    has_independent_payload = bool(
        signals.get("has_independent_payload")
        or output_forms
        or numeric_anchors
        or (len(current_content) >= 2 and not (gratitude or positive or acknowledgement or disagreement))
    )
    short_social_only = bool(
        (gratitude or positive or acknowledgement or disagreement or dissatisfaction)
        and not output_forms and not numeric_anchors
        and not bool(profile.get("interrogative"))
        and len(current_content) <= 1
    )
    continuation_action = bool(
        signals.get("continuation_action")
        or signals.get("answer_followup")
        or features.get("continuation_action")
        or features.get("answer_followup")
        or _text(profile.get("primary_intent")).upper() in {"TOPIC_CONTINUATION", "PREVIOUS_ANSWER_FOLLOWUP"}
    )
    short_continuation_action = bool(
        continuation_action and not has_independent_payload
        and len(current_tokens_list) <= 7
        and not output_forms and not numeric_anchors
        and not explicit_switch
    )
    # A lexical match is evidence only when it covers most of the new request.
    # One shared noun/action must not drag a separately specified request into
    # the previous branch (for example, a new product named in the same sentence).
    linked_by_user_turn = bool(user_common and user_overlap >= 0.75)
    linked_by_answer = bool(answer_common and answer_overlap >= 0.75)
    explicit_context_signal = bool(
        contextual_reaction or previous_answer_reference
        or features.get("answer_followup") or features.get("topic_reference_fragment")
        or features.get("strong_anaphoric_reference")
    )
    # A second-person reference plus an elliptical question can address April's
    # immediately preceding answer. Self-possessives such as "свой кабинет" do not.
    direct_april_reference = bool(
        contextual_question and re.search(
            r"\b(?:у\s+тебя\s+же|ты\s+же|твоя|твой|твое|твоё|твои|"
            r"you\s+have\s+that|your\s+(?:button|answer|message|option))\b",
            low, re.IGNORECASE,
        )
    )
    explicit_context_signal = bool(explicit_context_signal or direct_april_reference)
    latest_exchange_link = bool(
        not profile.get("history_request")
        and not explicit_switch
        and (
            short_social_only
            or short_continuation_action
            or reply_to_open_question
            or assistant_repetition_feedback
            or linked_by_user_turn
            or linked_by_answer
            or (explicit_context_signal and (
                not has_independent_payload or linked_by_user_turn or linked_by_answer
                or direct_april_reference
                or features.get("strong_anaphoric_reference")
                or features.get("previous_answer_reference")
                or previous_answer_reference
            ))
        )
    )

    analysis = {
        "available": True,
        "linked": latest_exchange_link,
        "route": "LATEST_EXCHANGE_FIRST" if latest_exchange_link else "CHECK_FOR_PRIOR_BRANCH_OR_NEW_TOPIC",
        "reason": (
            "assistant_response_feedback" if assistant_repetition_feedback else
            _text(open_question_reply.get("reason")) if reply_to_open_question else
            "social_or_pragmatic_reaction" if short_social_only else
            "short_continuation_action" if short_continuation_action else
            "semantic_link_to_previous_user_turn" if linked_by_user_turn else
            "semantic_link_to_previous_april_answer" if linked_by_answer else
            "explicit_april_reference_to_latest_exchange" if latest_exchange_link and direct_april_reference else
            "contextual_reference_validated_against_latest_exchange" if latest_exchange_link else
            "self_contained_or_unmatched_request"
        ),
        "user_turn_overlap": round(user_overlap, 3),
        "answer_overlap": round(answer_overlap, 3),
        "user_shared_terms": user_common,
        "answer_shared_terms": answer_common,
        "social_act": bool(gratitude or positive or acknowledgement or disagreement or dissatisfaction),
        "has_independent_payload": has_independent_payload,
        "reply_to_open_question": reply_to_open_question,
        "open_question_kind": _text(
            open_question_reply.get("kind") if reply_to_open_question else open_question.get("kind")
        ),
        "open_question_text": _text(
            (open_question.get("questions") or [])[int(open_question_reply.get("question_index") or 0)].get("question")
            if reply_to_open_question and isinstance(open_question.get("questions"), list)
            and open_question.get("questions") and 0 <= int(open_question_reply.get("question_index") or 0) < len(open_question.get("questions"))
            else open_question.get("question")
        )[:220],
        "answered_question_index": int(open_question_reply.get("question_index", -1)) if reply_to_open_question else -1,
        "answered_question_indices": list(open_question_reply.get("answered_question_indices") or [])[:4],
        "reply_clauses": list(open_question_reply.get("reply_clauses") or [])[:4],
        "open_question_slots": [
            {
                "kind": _text(item.get("kind"))[:40],
                "question": _text(item.get("question"))[:220],
                "expects_user_input": bool(item.get("expects_user_input")),
                "semantic_vector": dict(item.get("semantic_vector") or {}),
            }
            for item in (open_question.get("questions") or [])[:4]
            if isinstance(item, dict)
        ],
        "reply_clause": _text(open_question_reply.get("reply_clause"))[:180],
        "reply_semantic_vector": dict(open_question_reply.get("reply_semantic_vector") or {}),
        "dialogue_move_vector": dict(open_question_reply.get("dialogue_move_vector") or {}),
        "remainder_request": _text(open_question_reply.get("remainder_request"))[:360],
        "mixed_reply_and_new_request": bool(open_question_reply.get("mixed_reply_and_new_request")),
        "secondary_topic_switch": secondary_topic_switch,
    }
    profile["latest_exchange_analysis"] = analysis

    if latest_exchange_link:
        profile["history_request"] = False
        profile["history_recall"] = False
        profile["requires_memory"] = True
        profile["search_scope"] = "LATEST_EXCHANGE"
        profile["primary_intent"] = "TOPIC_CONTINUATION"
        profile["direction"] = "RESOLVE_AGAINST_LATEST_EXCHANGE"
        profile["topic_reference"] = "PREVIOUS_ASSISTANT_ANSWER"
        profile["time_scope"] = "ACTIVE_DIALOGUE"
        profile["relation_hint"] = "CONTINUE"
        profile["previous_answer_reference"] = True
        profile["reason"] = analysis["reason"]
        features = dict(features)
        features.update({
            "latest_exchange_link": True,
            "previous_answer_reference": True,
            "context_dependent_reaction": bool(short_social_only or short_continuation_action or reply_to_open_question or contextual_reaction or assistant_repetition_feedback),
            "context_dependent_question": bool(contextual_question or linked_by_user_turn or linked_by_answer or reply_to_open_question),
            "reply_to_open_question": reply_to_open_question,
            "mixed_reply_and_new_request": bool(open_question_reply.get("mixed_reply_and_new_request")),
            "active_branch_repair": bool(assistant_repetition_feedback or disagreement or dissatisfaction),
        })
        profile["features"] = features
        signals.update({
            "latest_exchange_link": True,
            "previous_answer_reference": True,
            "context_dependent_reaction": bool(short_social_only or reply_to_open_question or contextual_reaction or assistant_repetition_feedback),
            "context_dependent_question": bool(contextual_question or linked_by_user_turn or linked_by_answer or reply_to_open_question),
            "reply_to_open_question": reply_to_open_question,
            "mixed_reply_and_new_request": bool(open_question_reply.get("mixed_reply_and_new_request")),
            "active_branch_repair": bool(assistant_repetition_feedback or disagreement or dissatisfaction),
        })
        profile["pragmatic_features"] = signals
        profile["context_dependent_reaction"] = bool(short_social_only or short_continuation_action or reply_to_open_question or contextual_reaction or assistant_repetition_feedback)
        profile["reply_to_open_question"] = reply_to_open_question
        profile["open_question_reply"] = dict(open_question_reply)
        profile["open_question_profile"] = dict(open_question)
        profile["previous_answer_reference"] = True
        profile["active_branch_repair"] = bool(assistant_repetition_feedback or disagreement or dissatisfaction or profile.get("active_branch_repair"))
        profile["dialogue_act"] = profile.get("dialogue_act") or profile.get("speech_act") or "REFERENTIAL_CONTINUATION"
    elif (
        _text(profile.get("primary_intent")).upper() in {"TOPIC_CONTINUATION", "ACTIVE_BRANCH_REPAIR"}
        and has_independent_payload
        and not explicit_context_signal
        and not profile.get("history_request")
        and not explicit_switch
        and not assistant_repetition_feedback
    ):
        # The interpreter inferred continuity from generic question wording, but
        # the current turn has its own subject/deliverable and no verified link to
        # the latest exchange. Let State Manager start a clean topic rather than
        # searching the archive just because a word looked referential.
        profile["primary_intent"] = "NEW_INFORMATION"
        profile["direction"] = "ANSWER_NEW_REQUEST"
        profile["topic_reference"] = "UNSPECIFIED"
        profile["time_scope"] = "UNSPECIFIED"
        profile["requires_memory"] = False
        profile["history_request"] = False
        profile["search_scope"] = "CURRENT_DIALOGUE"
        profile["relation_hint"] = "NEW"
        profile["reason"] = "self_contained_request_without_latest_exchange_link"

    return profile



def interpret_request_across_recent_exchanges(
    text: Any,
    recent_exchanges: Any,
    semantic_interpretation: dict[str, Any] | None = None,
    *,
    window_size: int = 10,
) -> dict[str, Any]:
    """Resolve an incoming turn against the last 5–10 USER↔APRIL exchanges.

    The newest answer is evaluated first. If it does not explain a named or
    referential request, the same request is compared with earlier answers in
    the current dialogue window before the archive router is allowed to run.
    The returned profile keeps both the real latest answer and the matched
    recent-branch anchor; no old pair is silently substituted for the latest one.
    """
    source = _text(text)
    rows = [dict(item) for item in (recent_exchanges or []) if isinstance(item, dict)]
    rows.sort(key=lambda item: (float(item.get("created_at") or 0.0), int(item.get("turn_index") or 0)))
    rows = rows[-max(5, min(10, int(window_size or 10))):]
    supplied_profile = dict(semantic_interpretation or {})
    original_profile = supplied_profile.get("_recent_exchange_original_semantics")
    base = dict(original_profile) if isinstance(original_profile, dict) else supplied_profile
    if not base:
        base = dict(interpret_request_semantics(source) or {})
    source_low = source.lower().replace("ё", "е")
    social_conversation_opener = bool(re.fullmatch(
        r"\s*(?:(?:ну\s+)?давай(?:те)?\s+)?"
        r"(?:пообщаемся|пообщаться|поговорим|поговорить|поболтаем|поболтать|"
        r"общаться|беседовать|поговори(?:те)?\s+со\s+мной|"
        r"let(?:'|’)s\s+talk|talk\s+with\s+me|chat\s+with\s+me)"
        r"[.!?…\s]*",
        source_low,
        flags=re.IGNORECASE,
    )) and not bool(base.get("history_request"))
    if not rows or not source.strip():
        fallback = interpret_request_in_context(source, rows[-1] if rows else None, base)
        fallback["_recent_exchange_original_semantics"] = dict(base)
        return fallback

    latest_row = rows[-1]
    latest_profile = interpret_request_in_context(source, latest_row, base)
    latest_analysis = dict(latest_profile.get("latest_exchange_analysis") or {})
    explicit_history = bool(base.get("history_request") or latest_profile.get("history_request"))
    if social_conversation_opener and not explicit_history:
        # Keep a plain social invitation independent of any stale saved topic,
        # including when the latest answer itself was a capacity fallback.
        latest_profile = dict(base)
        latest_profile.update({
            "primary_intent": "NEW_INFORMATION",
            "direction": "ANSWER_NEW_REQUEST",
            "topic_reference": "UNSPECIFIED",
            "time_scope": "UNSPECIFIED",
            "requires_memory": False,
            "history_request": False,
            "search_scope": "CURRENT_DIALOGUE",
            "relation_hint": "NEW",
            "reason": "standalone_social_conversation_opener",
        })
        latest_analysis = {
            "available": bool(rows),
            "linked": False,
            "reason": "standalone_social_opener_new_topic",
            "route": "NEW_TOPIC",
            "actual_latest_exchange_id": _text(latest_row.get("message_id"))[:120],
        }
        latest_profile["latest_exchange_analysis"] = latest_analysis
    # An explicit topic-change phrase appended AFTER a matched answer is a
    # second move, not a reason to discard the answer to April's pending question.
    secondary_topic_switch = bool(latest_analysis.get("secondary_topic_switch"))
    explicit_switch = bool(
        not secondary_topic_switch and (
            base.get("explicit_topic_switch") or base.get("explicit_topic_introduction")
            or latest_profile.get("explicit_topic_switch")
        )
    )
    explicit_conversation_repair = bool(re.search(
        r"\bя\s+(?:же\s+)?(?:спросил|спрашивал)\s*(?:[,;:—-]\s*)?"
        r"(?:мы\s+)?(?:пообщаемся|пообщаться|общаться|поговорим|поговорить|"
        r"поболтаем|поболтать)\b|"
        r"\bя\s+(?:же\s+)?(?:не\s+это\s+спрашивал|не\s+об\s+этом\s+спрашивал)\b|"
        r"\bя\s+(?:же\s+)?просил\s+(?:просто\s+)?(?:пообщаться|поговорить)\b",
        source_low,
    )) and len(_semantic_normalize(source)[1]) <= 18
    standalone_action = bool(
        _context_signature(source).get("subject_terms")
        and re.search(
            r"\b(?:расскажи|расскажите|объясни|объясните|напиши|напишите|опиши|опишите|"
            r"покажи|создай|сделай|построй|вычисли|сравни|найди|проверь|проанализируй|"
            r"перечисли|нарисуй|рассчитай|tell|describe|explain|write|show|create|build|"
            r"make|calculate|compare|find|check|analyze)\b",
            source_low,
        )
        and not re.search(
            r"\b(?:подробнее|продолж\w*|предыдущ\w*|прошл\w*|вернись|восстанови|"
            r"эта\s+таблиц\w*|этот\s+график|эту\s+формул\w*|из\s+истории)\b",
            source_low,
        )
        and not explicit_history
        and not explicit_switch
    )

    def _analysis_score(analysis: dict[str, Any], recency_rank: int) -> tuple[float, int, float]:
        answer = float(analysis.get("answer_overlap") or 0.0)
        user = float(analysis.get("user_turn_overlap") or 0.0)
        subject = float(analysis.get("assistant_answer_subject_overlap") or analysis.get("subject_overlap") or 0.0)
        # Semantic linkage is the gate; these values only rank already-linked
        # candidates. A small recency tie-breaker favours the closest exchange.
        return (answer * 0.52 + user * 0.28 + subject * 0.20, recency_rank, answer)

    evaluated: list[tuple[tuple[float, int, float], dict[str, Any], dict[str, Any]]] = []
    for index, row in enumerate(rows):
        if social_conversation_opener:
            break
        candidate_profile = latest_profile if index == len(rows) - 1 else interpret_request_in_context(source, row, base)
        analysis = candidate_profile.get("latest_exchange_analysis")
        analysis = dict(analysis) if isinstance(analysis, dict) else {}
        analysis.update({
            "message_id": _text(row.get("message_id"))[:120],
            "topic_id": _text(row.get("topic_id") or row.get("selected_topic_id"))[:120],
            "branch_id": _text(row.get("branch_id") or row.get("work_id"))[:120],
            "same_dialog": True,
            "window_position": index + 1,
        })
        if analysis.get("linked"):
            evaluated.append((_analysis_score(analysis, index), row, candidate_profile))

    # The latest exchange always wins when it already explains the request.
    # Otherwise the best linked exchange in the preceding 9 turns may restore
    # the active branch. Explicit history/time requests retain their own route.
    chosen_row = latest_row if latest_analysis.get("linked") else None
    chosen_profile = latest_profile if chosen_row else None
    chosen_analysis = latest_analysis if chosen_row else {}
    if explicit_conversation_repair and not explicit_history and not explicit_switch:
        # The user is correcting the conversational move, not opening a topic.
        # Attach it to the actual latest exchange even when lexical overlap is low.
        chosen_row = latest_row
        chosen_profile = latest_profile
        chosen_analysis = dict(latest_analysis)
        chosen_analysis.update({
            "linked": True,
            "reason": "explicit_user_correction_to_latest_conversational_exchange",
            "route": "LATEST_EXCHANGE_FIRST",
            "implicit_continuation": True,
        })
    if (not chosen_row and not explicit_history and not explicit_switch and not standalone_action
            and not social_conversation_opener and evaluated):
        evaluated.sort(key=lambda item: item[0], reverse=True)
        _, chosen_row, chosen_profile = evaluated[0]
        chosen_analysis = dict((chosen_profile or {}).get("latest_exchange_analysis") or {})

    # A genuinely elliptical turn (no new subject/payload, but a contextual
    # speech act or deictic/continuation signal) belongs to April's last answer
    # even if lexical overlap is zero. This is the core implicit-continuation rule.
    features = base.get("features") if isinstance(base.get("features"), dict) else {}
    pragmatic = base.get("pragmatic_features") if isinstance(base.get("pragmatic_features"), dict) else {}
    tokens = _semantic_normalize(source)[1]
    contextual_signal = any(bool(source_map.get(key)) for source_map in (features, pragmatic, base) for key in (
        "context_dependent_question", "context_dependent_reaction", "answer_followup",
        "continuation_action", "topic_reference_fragment", "strong_anaphoric_reference",
        "previous_answer_reference", "active_branch_repair", "deictic_reference",
        "clarification_request", "explanation_request",
    ))
    no_named_subject = not _context_signature(source).get("subject_terms")
    implicit_latest = bool(
        not chosen_row and not explicit_history and not explicit_switch and not standalone_action
        and not social_conversation_opener
        and len(tokens) <= 18 and no_named_subject and contextual_signal
    )
    if implicit_latest:
        chosen_row = latest_row
        chosen_profile = latest_profile
        chosen_analysis = dict(latest_analysis)
        chosen_analysis.update({
            "linked": True,
            "reason": "implicit_elliptical_turn_attached_to_latest_april_answer",
            "route": "LATEST_EXCHANGE_FIRST",
            "implicit_continuation": True,
            "matched_recent_exchange_id": _text(latest_row.get("message_id"))[:120],
        })

    window = []
    for index, row in enumerate(rows):
        user_text = _text(row.get("user_text") or row.get("user") or row.get("user_request"))
        answer_text = _text(row.get("april_text") or row.get("april") or row.get("assistant_last_message"))
        window.append({
            "message_id": _text(row.get("message_id"))[:120],
            "topic_id": _text(row.get("topic_id") or row.get("selected_topic_id"))[:120],
            "branch_id": _text(row.get("branch_id") or row.get("work_id"))[:120],
            "turn_index": int(row.get("turn_index") or 0),
            "created_at": row.get("created_at"),
            "user_request": user_text[:1200],
            "april_answer": answer_text[:2400],
            "artifact_count": sum(len(row.get(key) or []) for key in ("render_blocks", "artifacts", "assistant_artifact_index", "artifact_index") if isinstance(row.get(key), list)),
        })

    result = dict(chosen_profile or latest_profile)
    if chosen_row:
        chosen_id = _text(chosen_row.get("message_id"))[:120]
        actual_latest_id = _text(latest_row.get("message_id"))[:120]
        chosen_analysis = dict(chosen_analysis)
        chosen_analysis.update({
            "available": True,
            "linked": True,
            "route": "LATEST_EXCHANGE_FIRST" if chosen_id == actual_latest_id else "RECENT_BRANCH_EXCHANGE_MATCH",
            "matched_recent_exchange_id": chosen_id,
            "matched_recent_exchange_position": int(chosen_analysis.get("window_position") or len(rows)),
            "actual_latest_exchange_id": actual_latest_id,
            "recent_exchange_count": len(rows),
            "recent_exchange_window": window,
            "matched_older_exchange": chosen_id != actual_latest_id,
        })
        result["latest_exchange_analysis"] = chosen_analysis
        result["recent_branch_anchor"] = {
            "message_id": chosen_id,
            "topic_id": _text(chosen_row.get("topic_id") or chosen_row.get("selected_topic_id"))[:120],
            "branch_id": _text(chosen_row.get("branch_id") or chosen_row.get("work_id"))[:120],
            "same_dialog": True,
            "user": _text(chosen_row.get("user_text") or chosen_row.get("user"))[:1200],
            "april": _text(chosen_row.get("april_text") or chosen_row.get("april"))[:480],
            "assistant_last_message": _text(chosen_row.get("april_text") or chosen_row.get("april") or chosen_row.get("assistant_last_message"))[:5200],
        }
        result.update({
            "history_request": False,
            "history_recall": False,
            "requires_memory": True,
            "search_scope": "RECENT_DIALOGUE_BRANCH",
            "primary_intent": "TOPIC_CONTINUATION",
            "direction": "RESOLVE_AGAINST_RECENT_BRANCH",
            "topic_reference": "PREVIOUS_OR_ACTIVE_TOPIC",
            "time_scope": "ACTIVE_DIALOGUE",
            "relation_hint": "CONTINUE",
            "previous_answer_reference": True,
            "recent_branch_match": True,
            "reason": _text(chosen_analysis.get("reason") or "recent_branch_exchange_match"),
        })
        result_features = dict(result.get("features") or {})
        result_features.update({"recent_branch_match": True, "previous_answer_reference": True})
        result["features"] = result_features
        result_pragmatic = dict(result.get("pragmatic_features") or {})
        result_pragmatic.update({"recent_branch_match": True, "previous_answer_reference": True})
        result["pragmatic_features"] = result_pragmatic
    else:
        analysis = dict(latest_analysis)
        analysis.update({
            "recent_exchange_count": len(rows),
            "recent_exchange_window": window,
            "matched_recent_exchange_id": "",
            "matched_older_exchange": False,
        })
        result["latest_exchange_analysis"] = analysis
        result["recent_branch_match"] = False
    result["_recent_exchange_original_semantics"] = dict(base)
    return result

def enforce_history_retrieval_route(
    dialogue_context: dict[str, Any] | None,
    semantic_interpretation: dict[str, Any] | None,
    *,
    explicit_history_request: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Carry explicit archive retrieval across Executor → Interpretation → Provider."""
    context = dict(dialogue_context) if isinstance(dialogue_context, dict) else {}
    semantics = dict(semantic_interpretation) if isinstance(semantic_interpretation, dict) else {}
    if not explicit_history_request:
        return context, semantics

    context["history_request"] = True
    if _text(context.get("relation")).upper() == "CONTINUE":
        context["relation"] = "NEW"
    semantics["history_request"] = True
    semantics["requires_memory"] = True
    if _text(semantics.get("primary_intent")).upper() not in {
        "HISTORY_RECALL", "HISTORY_SUMMARY", "PRIOR_DECISION_RECALL"
    }:
        semantics["primary_intent"] = "HISTORY_RECALL"
    if _text(semantics.get("direction")).upper() not in {
        "SEARCH_DIALOGUE_HISTORY", "SEARCH_AND_SUMMARIZE_HISTORY"
    }:
        semantics["direction"] = "SEARCH_DIALOGUE_HISTORY"
    semantics["search_scope"] = "ALL_DIALOGUE_HISTORY"
    semantics["relation_hint"] = "HISTORY_LOOKUP"
    if not context.get("topic_index") and context.get("history_topics"):
        context["topic_index"] = list(context.get("history_topics") or [])
    return context, semantics


def should_sync_active_dialogue_branch(
    *,
    explicit_history_request: bool,
    explicit_topic_switch: bool,
    transition_class: str,
    same_dialog: bool,
) -> bool:
    """Keep archive retrieval separate from active-branch continuation."""
    if explicit_history_request or explicit_topic_switch:
        return False
    classification = _text(transition_class).upper()
    return bool(
        classification == "TOPIC_CONTINUATION"
        or (classification == "HISTORICAL_TOPIC_REACTIVATION" and same_dialog)
    )


def analyze_dialogue_transition(
    current_request: Any,
    dialogue_context: dict[str, Any] | None = None,
    semantic_interpretation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Synchronous local pre-response audit for Free dialogue continuity.

    This compares the literal new turn with April's latest saved answer first,
    then with the State Manager's selected authenticated history pair. It makes
    no model/API call and never exposes private chain-of-thought.
    """
    request = _text(current_request)
    context = dialogue_context if isinstance(dialogue_context, dict) else {}
    semantics = semantic_interpretation if isinstance(semantic_interpretation, dict) else {}
    relation = _text(context.get("relation") or "NEW").upper()
    history_request = bool(context.get("history_request") or semantics.get("history_request"))
    latest = context.get("latest_assistant_anchor") if isinstance(context.get("latest_assistant_anchor"), dict) else {}
    anchor = context.get("anchor") if isinstance(context.get("anchor"), dict) else {}
    selected = context.get("selected_pairs") if isinstance(context.get("selected_pairs"), list) else []
    latest_relation = context.get("latest_answer_relation") if isinstance(context.get("latest_answer_relation"), dict) else {}
    last_turn_link = context.get("last_turn_link") if isinstance(context.get("last_turn_link"), dict) else {}
    latest_answer_match = bool(latest_relation.get("matched") or last_turn_link.get("latest_answer_match"))
    history_method = _text(context.get("history_selection_method"))
    anchor_message_id = _text(anchor.get("message_id"))
    latest_message_id = _text(latest.get("message_id"))
    # Same-dialog topic-vector expansion is an active thread, not a historical
    # reactivation. Explicit history requests and genuinely older/cross-dialog
    # sources remain historical.
    historical_match = bool(
        context.get("contextual_history_match")
        and not latest_answer_match
        and (
            history_request
            or history_method in {"named_topic_section_vector", "semantic_topic_index_match", "temporal_window", "temporal_nearest_fallback"}
            # A matching source from another dialog is historical even when the
            # new dialog has no saved assistant turn yet (latest_message_id="").
            or bool(anchor_message_id and not anchor.get("same_dialog"))
            # A named topic-vector hit may be an older branch in this same chat.
            # The latest message remains the primary vector; a different selected
            # message is historical reactivation even when both share dialog_id.
            or bool(anchor_message_id and latest_message_id and anchor_message_id != latest_message_id)
        )
    )
    explicit_switch = bool(
        semantics.get("explicit_topic_switch")
        or semantics.get("explicit_topic_introduction")
        or _has_explicit_topic_introduction(request)
        and relation == "NEW"
        and not history_request
    )

    if history_request:
        # An explicit history-inventory/recall request is intentional and may
        # choose an older retained branch even when the latest answer also matches.
        source_pair = anchor or next((item for item in selected if isinstance(item, dict)), {})
        source_kind = "AUTHENTICATED_HISTORICAL_BRANCH" if source_pair else "HISTORY_LOOKUP_NO_MATCH"
    elif latest_answer_match and latest:
        # The latest actual April answer is the primary discourse vector. This
        # signal must win even when State Manager's coarse relation says NEW.
        source_pair = latest
        source_kind = "LATEST_APRIL_ANSWER_AND_ACTIVE_BRANCH"
    elif historical_match:
        source_pair = anchor or next((item for item in selected if isinstance(item, dict)), {})
        source_kind = "AUTHENTICATED_HISTORICAL_BRANCH" if source_pair else "HISTORY_LOOKUP_NO_MATCH"
    elif relation == "CONTINUE" and latest and (not anchor_message_id or anchor_message_id == latest_message_id):
        source_pair = latest
        source_kind = "LATEST_APRIL_ANSWER_AND_ACTIVE_BRANCH"
    elif relation == "CONTINUE" and anchor:
        source_pair = anchor
        source_kind = "SELECTED_ACTIVE_TOPIC_BRANCH"
    else:
        source_pair = {}
        source_kind = "NEW_TOPIC"

    previous_user = _text(
        source_pair.get("user_request") or source_pair.get("user")
        or source_pair.get("user_text")
    )[:700]
    previous_answer = _text(
        source_pair.get("assistant_last_message") or source_pair.get("april")
        or source_pair.get("april_text") or source_pair.get("april_summary")
    )[:5200]
    previous_summary = _text(source_pair.get("april_summary")) or previous_answer[:460]
    source_message_id = _text(source_pair.get("message_id") or source_pair.get("source_message_id"))[:120]
    source_topic_id = _text(source_pair.get("topic_id") or source_pair.get("selected_topic_id"))[:120]
    source_branch_id = _text(source_pair.get("branch_id") or source_pair.get("active_branch_id"))[:120]
    same_dialog = bool(source_pair.get("same_dialog", source_kind == "LATEST_APRIL_ANSWER_AND_ACTIVE_BRANCH"))

    previous_signature = _context_signature(" ".join((previous_user, previous_answer)))
    current_signature = _context_signature(request)
    previous_terms = set(previous_signature.get("subject_terms") or [])
    current_terms = set(current_signature.get("subject_terms") or [])
    subject_overlap = (
        len(previous_terms & current_terms) / max(1, len(previous_terms | current_terms))
        if previous_terms and current_terms else 0.0
    )
    latest_answer_expects_input = bool(
        latest_relation.get("expects_user_input")
        or last_turn_link.get("previous_answer_expects_user_input")
    )
    references_previous = bool(
        semantics.get("previous_answer_reference")
        or semantics.get("active_branch_repair")
        or semantics.get("requires_memory")
        or semantics.get("relation_hint") == "CONTINUE"
        or current_signature.get("reference_strength", 0) >= 0.18
        or latest_answer_match
        or (latest_answer_expects_input and len(request.split()) <= 7)
    )

    section_headings: list[str] = []
    for section in (source_pair.get("sections") or [])[:12]:
        if isinstance(section, dict):
            heading = _text(section.get("heading") or section.get("h"))
            if heading and heading.casefold() not in {value.casefold() for value in section_headings}:
                section_headings.append(heading[:100])
    if not section_headings and previous_answer:
        for heading in re.findall(r"(?m)^\s{0,3}#{1,4}\s+(.+)$", previous_answer):
            heading = _text(heading)
            if heading and heading.casefold() not in {value.casefold() for value in section_headings}:
                section_headings.append(heading[:100])
            if len(section_headings) >= 10:
                break

    if explicit_switch:
        classification = "NEW_TOPIC"
        strategy = "ANSWER_NEW_TOPIC"
    elif historical_match or (history_request and source_message_id):
        classification = "HISTORICAL_TOPIC_REACTIVATION"
        strategy = "RESUME_HISTORICAL_BRANCH"
    elif (relation == "CONTINUE" or latest_answer_match) and source_message_id and same_dialog:
        # A verified latest-answer match is sufficient to continue the active
        # dialogue even if a separate semantic layer labelled the request NEW.
        classification = "TOPIC_CONTINUATION"
        strategy = "CONTINUE_WITH_NEW_INFORMATION"
    elif historical_match and source_message_id:
        classification = "HISTORICAL_TOPIC_REACTIVATION"
        strategy = "RESUME_HISTORICAL_BRANCH"
    elif references_previous and source_message_id and (subject_overlap >= 0.12 or not current_terms):
        classification = "HISTORICAL_TOPIC_REACTIVATION" if not same_dialog else "TOPIC_CONTINUATION"
        strategy = "RESUME_HISTORICAL_BRANCH" if classification == "HISTORICAL_TOPIC_REACTIVATION" else "CONTINUE_WITH_NEW_INFORMATION"
    else:
        classification = "NEW_TOPIC"
        strategy = "ANSWER_NEW_TOPIC"

    if classification == "NEW_TOPIC":
        recap = "Новая тема: отвечать на текущий запрос самостоятельно, не переносить посторонний контекст."
    else:
        recap = "До этого: " + (previous_user[:180] if previous_user else "в выбранной ветке")
        if previous_summary:
            recap += "; April ответила: " + previous_summary[:420]
        if classification == "HISTORICAL_TOPIC_REACTIVATION":
            recap += "; пользователь возвращается к ранее обсуждавшейся ветке."
        else:
            recap += "; продолжить с незакрытого или запрошенного шага, не повторяя завершённое."
    recap = recap[:900]

    task_count = semantics.get("task_count") or semantics.get("request_count") or 1
    try:
        task_count = max(1, min(20, int(task_count)))
    except (TypeError, ValueError):
        task_count = 1

    transition = {
        "schema": "april_dialogue_transition_v1",
        "classification": classification,
        "response_strategy": strategy,
        "source_relation": relation,
        "source_kind": source_kind,
        "confidence": round(min(1.0, 0.42 + (0.22 if source_message_id else 0.0) + (0.20 if latest_answer_match else 0.0) + min(0.16, subject_overlap * 0.32)), 3),
        "previous_exchange": {
            "message_id": source_message_id,
            "topic_id": source_topic_id,
            "branch_id": source_branch_id,
            "same_dialog": same_dialog,
            "user_request": previous_user[:360],
            "april_answer_summary": previous_summary[:460],
            "april_answer_excerpt": previous_answer[:1800],
            "answered_sections": section_headings[:10],
        },
        "current_request": {
            "text": request[:700],
            "references_previous_answer": references_previous,
            "explicit_topic_switch": explicit_switch,
            "subject_terms": list(current_signature.get("subject_terms") or [])[:10],
        },
        "alignment": {
            "subject_overlap": round(subject_overlap, 3),
            "latest_answer_match": latest_answer_match,
            "latest_answer_subject_overlap": round(float(latest_relation.get("answer_subject_overlap") or 0.0), 3),
            "latest_answer_expects_user_input": latest_answer_expects_input,
            "history_match": historical_match,
        },
        "pre_response_analysis": {
            "sequence": [
                "COUNT_AND_CLASSIFY_CURRENT_REQUEST_TASKS",
                "COMPARE_CURRENT_REQUEST_WITH_LATEST_APRIL_ANSWER_AND_ACTIVE_BRANCH",
                "CHECK_IF_PREVIOUS_ANSWER_EXPECTS_USER_INPUT_OR_CONFIRMATION",
                "IF_NO_RELIABLE_CURRENT_BRANCH_MATCH_SEARCH_AUTHENTICATED_HISTORY_BY_TOPIC_AND_TIME",
                "RESTORE_ONLY_THE_MATCHED_HISTORY_BRANCH_AND_RELEVANT_SOURCE_ASSETS",
                "DISTINGUISH_TOPIC_CONTINUATION_HISTORY_RECALL_CORRECTION_AND_NEW_TOPIC",
                "ANSWER_ONLY_AFTER_SOURCE_AND_TASK_ALIGNMENT_CHECK",
            ],
            "analysis_mode": "SYNCHRONOUS_LOCAL_NO_EXTRA_MODEL_CALL",
            "request_task_count": task_count,
            "request_vector": _text(semantics.get("primary_intent") or semantics.get("intent") or "UNRESOLVED")[:80],
            "selected_source_message_id": source_message_id,
            "selected_topic_id": source_topic_id,
            "selected_branch_id": source_branch_id,
            "current_branch_selected": bool(classification == "TOPIC_CONTINUATION" and source_message_id),
            "latest_answer_is_primary_discourse_vector": bool(classification == "TOPIC_CONTINUATION" and source_message_id),
            "latest_answer_expects_user_input": latest_answer_expects_input,
            "latest_answer_match": latest_answer_match,
            "history_branch_selected": bool(classification == "HISTORICAL_TOPIC_REACTIVATION" and source_message_id),
            "must_not_inherit_unrelated_assets": classification == "NEW_TOPIC",
        },
        "continuation_summary": recap,
        "response_rules": {
            "begin_with_brief_context_summary": classification in {"TOPIC_CONTINUATION", "HISTORICAL_TOPIC_REACTIVATION"},
            "do_not_repeat_completed_sections": True,
            "develop_only_requested_or_unfinished_parts": True,
            "preserve_topic_branch_and_origin_ids": classification in {"TOPIC_CONTINUATION", "HISTORICAL_TOPIC_REACTIVATION"},
            "new_topic_must_not_inherit_unrelated_assets": classification == "NEW_TOPIC",
        },
    }
    return transition


def build_interpretation(
    *,
    current_request: str,
    original_request: str = "",
    display_language: str = "auto",
    memory: dict[str, Any] | None = None,
    attachments: list[dict[str, Any]] | None = None,
    visual_context: list[dict[str, Any]] | None = None,
    source_image_reference_available: bool = False,
    restrict_image_edits: bool = True,
    identity: dict[str, str] | None = None,
    semantic_interpretation: dict[str, Any] | None = None,
    question_sequence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create the structured request that the Provider is allowed to answer."""
    interpretation_started = time.perf_counter()
    text = _text(current_request)
    original = _text(original_request or current_request)
    memory = dict(memory or {})
    request_semantics = dict(semantic_interpretation or interpret_request_semantics(original or text))
    attachments = [dict(x) for x in (attachments or []) if isinstance(x, dict)]
    visual_context = [dict(x) for x in (visual_context or []) if isinstance(x, dict)]

    kinds = {str(item.get("kind") or "").lower() for item in attachments}
    restored_assets = [
        dict(item) for item in (memory.get("restored_assets") or [])
        if isinstance(item, dict)
    ]
    restored_kinds = {str(item.get("kind") or "").lower() for item in restored_assets}
    has_image = "image" in kinds or "image" in restored_kinds or bool(visual_context)
    output_asset_roles = {"april_output", "assistant_output", "generated", "generated_image", "april_generated"}

    def _is_user_source_image(item: dict[str, Any]) -> bool:
        kind = _text(item.get("kind") or item.get("mime_type") or item.get("content_type")).lower()
        item_type = _text(item.get("type")).lower()
        is_image = (
            kind == "image"
            or kind.startswith("image/")
            or item_type in {"input_image", "image"}
            or bool(item.get("image_url"))
        )
        if not is_image:
            return False
        role = _text(item.get("asset_role") or "user_input").lower()
        source_type = _text(item.get("source_type") or "").lower()
        return role not in output_asset_roles and source_type not in output_asset_roles

    has_user_source_image = any(
        _is_user_source_image(item)
        for item in [*attachments, *restored_assets, *visual_context]
        if isinstance(item, dict)
    )
    # A referenced image may be a user upload OR a picture April generated in
    # the active dialogue. Keep user-source identity separate for re-analysis,
    # but allow contextual edit intent to resolve against either image origin.
    def _is_existing_image(item: dict[str, Any]) -> bool:
        kind = _text(item.get("kind") or item.get("mime_type") or item.get("content_type")).lower()
        item_type = _text(item.get("type")).lower()
        return bool(
            kind == "image" or kind.startswith("image/")
            or item_type in {"input_image", "image", "generated_image"}
            or item.get("image_url") or item.get("src") or item.get("image_data_uri")
        )

    has_existing_image_reference = bool(source_image_reference_available) or any(
        _is_existing_image(item)
        for item in [*attachments, *restored_assets, *visual_context]
        if isinstance(item, dict)
    )
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

    request_text = original or text
    detected_outputs = _detect_requested_outputs(request_text)
    requested_outputs = _enhance_requested_outputs(
        request_text, detected_outputs, dialogue_context=memory
    )
    video_output_requested, video_companions = _explicit_video_output_intent(
        request_text, attachments, allow_edit=False,
    )
    if video_output_requested:
        # The source-aware pass is important for Premium edits: an uploaded
        # video plus a direct edit command is an output task, while a how-to
        # question remains non-billable and does not select C_VIDEO.
        requested_outputs = list(dict.fromkeys(["text", "video", *video_companions]))
    # A correction such as "I asked you to send it as a file" is elliptical.
    # Recover the code output only from the matched active branch selected by
    # State Manager; never scan unrelated history or infer a new code task.
    if (
        "file" in requested_outputs
        and "code" not in requested_outputs
        and _is_file_delivery_followup(request_text)
        and _active_branch_has_code_request(memory)
    ):
        requested_outputs.append("code")
    routing_capabilities = _infer_routing_capabilities(request_text)
    site_navigation_semantics = _infer_april_ui_semantics(request_text)
    if site_navigation_semantics:
        for capability in ("site_navigation", "april_site_help", "user_guidance", "interface_help", "april_site_navigation", "user_interface_help", "account_guidance"):
            if capability not in routing_capabilities:
                routing_capabilities.append(capability)

    # Keep edit restrictions separate from permitted creation. A new picture
    # described in the current dialogue remains a normal Free generation. An edit
    # request is restricted by default; the executor may authorize this exact edit
    # only after reserving one referral-bonus unit from the Free bonus bucket.
    diagram_overlay_requested = _detect_diagram_overlay_request(request_text)
    diagram_revision_followup = _is_active_diagram_revision_followup(request_text, memory)
    structured_diagram_modification_requested = _detect_structured_diagram_modification_request(request_text)
    image_modification_requested = bool(
        _detect_image_modification(
            request_text, has_existing_image_reference=has_existing_image_reference
        )
        and not diagram_overlay_requested
        and not structured_diagram_modification_requested
    )
    compositing_requested = _detect_image_compositing_request(request_text)
    # A geometry/technical drawing stays a structured diagram even if the
    # wording says "on the picture" or the dialogue contains an earlier image.
    # Explicitly changing an existing photo/diagram is still restricted, while
    # independently creating a new SVG/geometry artifact remains available.
    structured_diagram_noun = bool(re.search(
        r"(?:схем\w*|диаграмм\w*|черт[её]ж\w*|геометрическ\w*\s+фигур\w*|"
        r"треугольн\w*|квадрат\w*|прямоугольн\w*|параллелограмм\w*|ромб\w*|"
        r"трапец\w*|многоугольн\w*|окружност\w*|график\w*|"
        r"размер\w*\s+(?:кажд\w*\s+)?сторон\w*|размер\w*|измерен\w*)",
        request_text.lower().replace("ё", "е"),
    ) or diagram_overlay_requested or diagram_revision_followup or structured_diagram_modification_requested)
    contextual_source_edit = bool(
        has_existing_image_reference
        and _detect_contextual_image_edit(request_text)
        and not diagram_overlay_requested
        and not structured_diagram_modification_requested
    )
    image_edit_restricted = bool(
        restrict_image_edits
        and (
            image_modification_requested
            or contextual_source_edit
            or (has_user_source_image and compositing_requested and not structured_diagram_noun)
        )
    )
    # Kept as an explicit false compatibility field for older prompt and
    # executor code. Free never converts an edit request into a new image.
    free_image_recreation = False
    image_edit_prior_attempts = _prior_free_image_edit_notice_count(memory) if image_edit_restricted else 0
    wants_image = "image" in requested_outputs
    if image_edit_restricted:
        wants_image = False
        requested_outputs = [kind for kind in requested_outputs if kind not in {"image", "gallery", "generated_image"}]
        if "text" not in requested_outputs:
            requested_outputs.insert(0, "text")
    wants_links = "link" in requested_outputs
    structured_data_extensions = {".csv", ".tsv", ".json", ".xlsx", ".xls", ".ods", ".parquet"}
    data_source_attached = any(
        str(item.get("kind") or "").lower() in {"file", "text_file"}
        and str(item.get("asset_role") or "user_input").lower() not in {"april_output", "assistant_output", "generated"}
        and ("." + str(item.get("filename") or "").lower().rsplit(".", 1)[-1]) in structured_data_extensions
        for item in attachments
    )
    graph_policy = _graph_representation_policy(
        original or text,
        allow_data_driven_3d=data_source_attached,
    ) if "graph" in requested_outputs else {}

    relation = _text(memory.get("relation") or "NEW").upper()
    selected_pairs = _select_continuation_pairs(memory)

    # "Where are the remaining tables/materials?" is a replay request for the
    # selected branch's saved deliverables. Recover renderer kinds from its
    # authenticated artifact index rather than asking the model to guess which
    # outputs existed or generating substitute content.
    remaining_artifact_request = bool(re.search(
        r"\b(?:где\s+)?(?:остал[ьт]н\w*|оставш\w*|остаточн\w*|друг\w*)\s+(?:таблиц\w*|график\w*|диаграмм\w*|блок\w*|файл\w*|материал\w*|вариант\w*)\b|"
        r"\bгде\s+(?:остал[ьт]н\w*|оставш\w*|остаточн\w*)\b|"
        r"\bа\s+(?:остал[ьт]н\w*|оставш\w*|остаточн\w*)\b",
        request_text.lower().replace("ё", "е"),
    ))
    if remaining_artifact_request and (relation == "CONTINUE" or bool(memory.get("contextual_history_match"))):
        renderer_map = (
            (r"table|tableblock|таблиц", "table"),
            (r"graph|chart|plot|graphblock|график", "graph"),
            (r"diagram|diagramblock|схем|диаграмм|чертеж", "diagram"),
            (r"code|codeblock|script|скрипт|код", "code"),
            (r"formula|math|formulablock|формул", "formula"),
            (r"copy|copyblock|копи|копирован", "copy"),
        )
        for pair in selected_pairs:
            if not isinstance(pair, dict):
                continue
            for artifact in (pair.get("assistant_artifact_index") or []):
                if not isinstance(artifact, dict):
                    continue
                descriptor = " ".join(
                    _text(artifact.get(key)) for key in
                    ("kind", "type", "artifact_type", "output_type", "renderer", "viewer", "representation")
                ).lower().replace("ё", "е")
                for pattern, output_kind in renderer_map:
                    if re.search(pattern, descriptor) and output_kind not in requested_outputs:
                        requested_outputs.append(output_kind)
        # Do not infer a new image-generation request from historical image
        # assets; those remain handled by the selected asset restoration path.
        requested_outputs = ["text", *[kind for kind in requested_outputs if kind != "text"]]

    wants_file = "file" in requested_outputs
    file_delivery_mode = _file_delivery_mode(original or text, requested_outputs)
    wants_copy = "copy" in requested_outputs
    history_request = (
        bool(memory.get("history_request"))
        or bool(request_semantics.get("history_request"))
        or _is_history_request(original or text)
    )
    history_count = max(1, min(5, int(memory.get("requested_topic_count") or _history_count(original or text) or 5)))
    history_topics = _select_history_topics(memory)[:history_count]

    # Referential questions such as "а про него еще?" are resolved by the
    # State Manager anchor, not by guessing from the current sentence.
    continuation_anchor = dict(memory.get("anchor") or {}) if isinstance(memory.get("anchor"), dict) else {}
    identity_data = dict(identity or {})
    current_identity = {
        "user_id": _text(identity_data.get("user_id") or identity_data.get("april_id")),
        # Keep the authenticated Settings profile name in the identity card.
        # The previous whitelist copied only technical IDs and silently dropped
        # display_name before Provider could build AUTHENTICATED_IDENTITY.
        "display_name": _text(
            identity_data.get("display_name")
            or identity_data.get("user_display_name")
            or identity_data.get("name")
        )[:80],
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

    # The executor may have decomposed the turn before State Manager supplied
    # same-dialogue context. Re-resolve the per-step render contract now, without
    # allowing unrelated historical turns to introduce new deliverables.
    resolved_question_sequence = [
        dict(item) for item in (question_sequence or _build_question_sequence(original or text))
        if isinstance(item, dict)
    ]
    if len(resolved_question_sequence) == 1:
        step = resolved_question_sequence[0]
        step_request = _text(step.get("request") or original or text)
        step_outputs = _enhance_requested_outputs(
            step_request, list(step.get("output_types") or []), dialogue_context=memory
        )
        step["output_types"] = step_outputs
        step_semantics = interpret_request_semantics(step_request)
        step["action_contract"] = _build_action_contract_for_step(
            step_request, step_semantics, step_outputs, int(step.get("step_index") or 1)
        )
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
    if image_edit_restricted:
        task = "image_edit_restricted"

    # An existing/remembered image must not override an explicit request for a
    # structured geometry or graph artifact. In particular, do not turn
    # "draw this parallelogram on the picture" into image analysis or raster
    # generation simply because image context exists in the conversation.
    structured_visual_output = bool(
        structured_diagram_noun
        and ("diagram" in requested_outputs or "graph" in requested_outputs)
        and not image_modification_requested
        and not free_image_recreation
    )
    if structured_visual_output:
        task = "answer_request"
    elif has_original_image and task == "answer_request":
        task = "analyze_image"

    result = {
        "schema": "april_interpretation_v2",
        "identity": current_identity,
        # Executor uses this additive hint to select registered domain rooms.
        # These hints never override identity, memory, or explicit task intent.
        "routing_capabilities": routing_capabilities,
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
            "wants_video": "video" in requested_outputs,
            "wants_image": wants_image,
            "explicit_generation_request": wants_image,
            "image_edit_restricted": image_edit_restricted,
            "free_image_recreation": free_image_recreation,
            "image_edit_prior_attempts": image_edit_prior_attempts,
            "wants_file": wants_file,
            "wants_copy": wants_copy,
            "file_delivery_mode": file_delivery_mode,
            "wants_links": wants_links,
            "wants_code": "code" in requested_outputs,
            "wants_formula": "formula" in requested_outputs,
            "wants_diagram": "diagram" in requested_outputs,
            "wants_graph": "graph" in requested_outputs,
            "graph_policy": graph_policy,
            "wants_table": "table" in requested_outputs,
            "history_request": history_request,
            "history_count": history_count if history_request else 0,
            "semantic_intent": _text(request_semantics.get("primary_intent") or "NEW_INFORMATION"),
            "search_direction": _text(request_semantics.get("direction") or "ANSWER_NEW_REQUEST"),
            "semantic_reason": _text(request_semantics.get("reason")),
        },
        "dialogue": {
            "relation": relation,
            "is_new_dialogue": relation != "CONTINUE",
            "recent_limitations": _recent_dialogue_limitations(selected_pairs),
            "continuation_context": {
                "active_topic": _text(memory.get("active_topic")),
                "reason": _text(memory.get("reason")),
                "confidence": float(memory.get("relation_confidence") or 0.0),
                "selected_pairs": selected_pairs,
                "anchor": continuation_anchor,
                "latest_assistant_anchor": dict(memory.get("latest_assistant_anchor") or {}),
                "latest_answer_relation": dict(memory.get("latest_answer_relation") or {}),
                "last_turn_link": dict(memory.get("last_turn_link") or {}),
                "dialogue_transition_analysis": dict(memory.get("dialogue_transition_analysis") or {}),
                "selected_section": dict(memory.get("selected_section") or {}),
                "clarification_needed": bool(memory.get("clarification_needed")),
                "pending_clarification": dict(memory.get("pending_clarification") or {}),
                "clarification_resolution": dict(memory.get("clarification_resolution") or {}),
                "history_topics": history_topics,
                "history_time_search": dict(memory.get("history_time_search") or {}),
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
            "history_time_search": dict(memory.get("history_time_search") or {}),
            "topic_table_markdown": _text(memory.get("topic_table_markdown")),
            "new_dialogue_request": original or text,
            "new_dialogue_active": relation != "CONTINUE" and not history_request,
            "continuation_context": selected_pairs if (relation == "CONTINUE" or history_request or bool(memory.get("contextual_history_match"))) else [],
            "selected_section": dict(memory.get("selected_section") or {}),
            "clarification_needed": bool(memory.get("clarification_needed")),
            "pending_clarification": dict(memory.get("pending_clarification") or {}),
            "clarification_resolution": dict(memory.get("clarification_resolution") or {}),
            "topic_index": [dict(item) for item in (memory.get("topic_index") or []) if isinstance(item, dict)][:10],
            "asset_task_map": asset_task_map,
            "question_sequence": resolved_question_sequence,
            "site_navigation_semantics": site_navigation_semantics,
            "answer_sequence_in_order": True,
            "presentation_contract": {
                "mcdowell_required": True,
                "katex_required_for_math": True,
                "scene_contract_required": True,
                "single_scene_contract": True,
                "renderer_signal_source": "C_ARTIFACT_CONTRACT",
            },
            "rendering_guidance": [
                "Always preserve a concise explanatory text answer.",
                "Use a structured table for a clear comparison when the answer has comparable attributes.",
                "Use a diagram for explicit schemas, workflows, arrows, geometry, mathematical figures, points, segments, angles, dimensions, measurements, construction drawings, blueprints, and technical drawings. Keep their exact labels, lengths, units, and angle values in the concrete diagram payload; never switch these requests to raster image generation.",
                "Use C_APRIL_IMAGES_GENERATOR (Images 2.0) for new artistic/scenic/photorealistic images and complex illustrations. New images requested from the current dialogue are allowed in Free and must not receive an unsolicited package/plan disclaimer. A structured math/technical drawing such as 'нарисуй схему на картинке' must remain a diagram request.",
                "In Free, editing an existing raster photo/image remains restricted unless the executor has explicitly authorized and reserved one referral bonus operation for this exact image edit. Native SVG/diagram/map/chart revisions and vector annotations over a screenshot/photo are not raster edits: continue the matched diagram branch and render the revision through C_DIAGRAM_ROOM inside the same SceneContract, preserving source labels and geometry. Do not call the image generator for those vector revisions. Never use free_image_recreation to bypass raster edit restrictions.",
                "Use a formula renderer for mathematical notation; use a graph only when a function or grounded numeric data can define it.",
                "For graph requests, follow intent.graph_policy: trends/time-ordered values use line; categorical comparisons use bar; choose only among those 2D types unless explicit 3D intent or real 3D source data supports 3D.",
                "Never turn 2D x/y data into a 3D chart by inventing a zero z-axis; true 3D requires explicit XYZ values, a real surface grid/function of x and y, or structured spatial objects.",
                "Use code, link, file, image, and gallery renderers only when the response contains matching valid payloads and the request/context supports them.",
                "Use CopyBlock only when the user explicitly asks for a separate copyable plain-text block or a block with a copy button; do not replace CodeBlock, which remains the renderer for actual source code.",
                "When intent.file_delivery_mode is file_only, return the deliverable through FileDeliveryBlock and keep the chat response to a short localized file notice; do not repeat the full code or table inline. When the user asks for both a visual result and a file, preserve both blocks in this same SceneContract.",
                "Never invent numeric data, URLs, files, or images just to fill a renderer.",
                "Every structured artifact must carry an explicit renderer type and its payload through the canonical SceneContract.",
            ],
            "improvement_policy": "Improve the requested result while preserving unaffected behavior; do not invent missing source content.",
            "output_plan": requested_outputs,
            "semantic_interpretation": request_semantics,
            "semantic_interpretation_version": "april_request_semantics_v1",
            "last_turn_link": dict(memory.get("last_turn_link") or {}),
            "dialogue_transition_analysis": dict(memory.get("dialogue_transition_analysis") or {}),
            "dialogue_transition_analysis_version": "april_dialogue_transition_v1",
        },
    }
    if site_navigation_semantics:
        result["site_navigation_semantics"] = site_navigation_semantics
        # A local site-help target is a deterministic lookup request, not a browser
        # action: the downstream IT Room reads the map and explains the route.
        result["site_navigation_help"] = True
    if image_edit_restricted:
        sequence_items = ((result.get("request_structure") or {}).get("question_sequence") or [])
        for sequence_item in sequence_items:
            if not isinstance(sequence_item, dict):
                continue
            item_outputs = sequence_item.get("output_types")
            if not isinstance(item_outputs, list):
                item_outputs = ["text"]
            item_outputs = [kind for kind in item_outputs if str(kind).lower() not in {"image", "gallery", "generated_image"}]
            if "text" not in item_outputs:
                item_outputs.insert(0, "text")
            sequence_item["output_types"] = item_outputs
        render_plan = result.get("request_structure", {}).get("output_plan")
        if isinstance(render_plan, list):
            result["request_structure"]["output_plan"] = [
                kind for kind in render_plan if str(kind).lower() not in {"image", "gallery", "generated_image"}
            ] or ["text"]

    _apr_timing_log("build_interpretation", interpretation_started,
        relation=relation, task=task, requested_outputs=requested_outputs,
        input_chars=len(text), selected_pairs=len(selected_pairs), history_topics=len(history_topics),
        question_sequence_count=len((result.get("request_structure") or {}).get("question_sequence") or []),
        semantic_intent=request_semantics.get("primary_intent"),
        search_direction=request_semantics.get("direction"),
        history_request=bool(request_semantics.get("history_request")),
        attachment_task_count=len(asset_task_map),
        selected_section=_text((memory.get("selected_section") or {}).get("heading")),
        clarification_needed=bool(memory.get("clarification_needed")),
        clarification_resolved=bool(memory.get("clarification_resolution")))
    return result


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
    "build_question_sequence",
    "interpret_request_semantics",
    "assert_same_identity",
]
