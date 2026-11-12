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


_OUTPUT_MARKERS = {
    # These markers describe an OUTPUT ACTION, not an input object.
    # Merely mentioning "картинка", "файл", "python" or "код" must never
    # request generation/production by itself.
    "image": {
        # Image generation is explicit only when the request asks for a picture,
        # image, illustration or photo. Generic drawing verbs are deliberately
        # excluded: simple shapes and objects belong to the structured diagram
        # route and must not spend an Images Generator call.
        "generate image", "generate an image", "generate a picture", "create image",
        "create an image", "create a picture", "make an image", "make a picture",
        "draw a picture", "draw the picture", "draw an image", "draw the image",
        "draw picture", "draw image", "show a picture", "show an image",
        "show me a picture", "show me an image", "create an illustration",
        "draw an illustration", "generate an illustration",
        "нарисуй картинку", "нарисуй изображение", "нарисуй иллюстрацию",
        "нарисовать картинку", "нарисовать изображение", "нарисовать иллюстрацию",
        "покажи картинку", "покажи изображение", "покажи иллюстрацию",
        "создай изображение", "создай картинку", "создай иллюстрацию",
        "сделай картинку", "сделай изображение", "сделай иллюстрацию",
        "сгенерируй изображение", "сгенерируй картинку", "сгенерируй иллюстрацию",
        "изобрази картинку", "изобрази изображение", "создай фото", "сделай фото",
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
        "write formula", "show formula", "draw formula", "display formula", "derive formula",
        "solve equation", "write an equation", "draw an equation", "show equation",
        "напиши формулу", "покажи формулу", "нарисуй формулу", "нарисовать формулу",
        "изобрази формулу", "отобрази формулу", "выведи формулу", "запиши формулу",
        "реши уравнение", "запиши уравнение", "нарисуй уравнение", "покажи уравнение",
    },
    "diagram": {
        "create diagram", "draw diagram", "show diagram", "создай диаграмму",
        "нарисуй диаграмму", "построй диаграмму", "сделай диаграмму", "создай схему",
        "нарисуй схему", "сделай схему",
    },
    "graph": {
        "plot a graph", "build a graph", "make a graph", "show a graph", "create a chart",
        "show a chart", "plot the data", "построй график", "покажи график",
        "создай график", "сделай график", "нарисуй график", "график функции",
        "построй диаграмму данных", "визуализируй данные",
    },
    "table": {
        "create table", "make a table", "show table", "build a table",
        "создай таблицу", "создайте таблицу", "создать таблицу", "сделай таблицу", "сделайте таблицу", "сделать таблицу",
        "построй таблицу", "постройте таблицу", "построить таблицу", "покажи таблицу", "покажите таблицу", "показать таблицу",
        "створи таблицю", "створіть таблицю", "побудуй таблицю", "побудуйте таблицю",
    },
}

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
    "измени диаграмму", "изменить диаграмму", "измени схему", "изменить схему",
    "измени чертеж", "изменить чертеж", "переделай диаграмму", "переделай схему",
    "modify the diagram", "change the diagram", "edit the diagram",
    "modify the chart", "change the chart", "edit the chart",
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
    """Detect a request to alter an existing image or diagram.

    In Free, detected edits are restricted instead of being silently converted
    into new image generation. Ordinary new-image and new-diagram requests use
    their existing routes.
    """
    low = _text(text).lower().replace("ё", "е")
    if not low:
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
        r"(?:фот\w*|картинк\w*|изображени\w*|photo(?:graph)?s?|images?|pictures?|"
        r"диаграмм\w*|схем\w*|черт[её]ж\w*|chart\w*|diagram\w*|sketch\w*)"
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


def _detect_image_generation_request(text: str) -> bool:
    """Detect a picture as the requested output, not a picture used as context.

    Explicit image-surface wording ("on a picture/photo/image") wins over a
    generic diagram interpretation. A bare drawing verb remains semantic and
    can route to geometry, a diagram, a graph, or image generation by subject.
    """
    low = _text(text).lower().replace("ё", "е")
    if not low:
        return False
    # How-to-upload requests are interface guidance, never new raster outputs.
    if _is_attachment_tutorial_request(low):
        return False
    # Explicit editing is not image generation in the Free chain. The caller will
    # issue a Premium-limit explanation and suppress all image artifacts.
    if _detect_image_modification(low):
        return False

    # Explicitly asking to render the subject *on a picture/photo/image* means
    # raster image generation. Existing-image edits have already been excluded
    # above; without a source image this is still a new image request.

    action = r"(?:draw|show|display|create|make|generate|render|add|place|put|remove|replace|нарис\w*|гарис\w*|рисуй\w*|покаж\w*|отобраз\w*|созда\w*|сдела\w*|сгенерир\w*|изобраз\w*|добав\w*|помест\w*|размест\w*|убер\w*|замен\w*)"
    image_noun = r"(?:picture|image|illustration|photo|photograph|картинк(?:у|а|и|е)\b|изображени(?:е|я|и|и\s+на)\b|иллюстраци(?:ю|я|и)\b|фот\w*)"
    # Explicitly placing any requested subject on an image surface is an image
    # request even if the subject itself is a diagram, formula, or chart.
    explicit_surface = re.search(
        rf"(?<![\w\u0080-\uffff]){action}\b.{{0,90}}?\b(?:on|in|onto|на|в)\s+"
        r"(?:(?:the|this|that|этой|этот|эту|этом|такой|таком|той|тои)\s+)?"
        r"(?:picture|image|illustration|photo|photograph|картинк\w*|изображени\w*|иллюстраци\w*|фот\w*)",
        low, flags=re.IGNORECASE,
    )
    if explicit_surface:
        return True
    # Permit polite words and ordinary modifiers, but do not skip a preceding
    # explicit schema/graph/table noun to reinterpret its object as an image.
    filler = r"(?:(?!(?:схем\w*|диаграмм\w*|график\w*|таблиц\w*|черт[её]ж\w*)\b)[\w-]+\s+)"
    forward = rf"(?<![\w\u0080-\uffff]){action}\b\s+(?:{filler}){{0,4}}{image_noun}"
    # Support inverted Russian requests such as "картинку нарисуй". The
    # accusative/nominative object forms deliberately exclude "на картинке".
    reverse = rf"(?<![\w\u0080-\uffff]){image_noun}\s+(?:мне\s+|нам\s+)?{action}\b"
    return bool(re.search(forward, low, flags=re.IGNORECASE) or re.search(reverse, low, flags=re.IGNORECASE))



def _detect_explicit_portrait_generation_request(text: str) -> bool:
    """Only treat portrait/photo as output when user asks to create or show one."""
    low = _text(text).lower().replace("ё", "е")
    if not low or _detect_image_modification(low):
        return False
    action = r"(?:сгенерир\w*|созда\w*|нарис\w*|изобраз\w*|покаж\w*|отобраз\w*|generate|create|draw|render|show|make)"
    subject = r"(?:портрет\w*|portrait\w*|фотограф\w*|фото\b|photo\w*|снимок\w*)"
    return bool(re.search(rf"\b{action}\b.{{0,100}}\b{subject}\b", low, re.IGNORECASE))


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


def _detect_requested_outputs(text: str) -> list[str]:
    result: list[str] = []
    low = _text(text).lower()
    if is_april_identity_question(low):
        return ["text"]
    if _is_feedback_control_help_request(low):
        # A route diagram is useful for "where do I click?"; photo/graph/code
        # words in the same sentence are examples of earlier answers, not deliverables.
        return ["text", "diagram"]
    if _is_site_navigation_request(low) and re.search(
        r"(?:стрелк\w*|покажи.{0,70}(?:путь|карту|схем|меню|интерфейс|куда\s+нажать|нажат\w*)|карта\s+сайт\w*|схем\w*.{0,35}(?:переход|кноп|страниц)|пошаг\w*|по\s+шагам|последовательност\w*.{0,35}(?:нажат|переход|действ)|step[- ]by[- ]step|click[- ]by[- ]click)",
        low, re.IGNORECASE | re.DOTALL,
    ) and not re.search(
        r"(?:\b(?:создай|сгенерир\w*|построй|нарисуй|напиши|выдай|исправь|create|generate|build|draw|write|fix)\b"
        r".{0,65}\b(?:график\w*|диаграмм\w*|код\w*|скрипт\w*|картинк\w*|изображени\w*|фото\w*|graph|chart|code|script|image|photo|picture)\b)",
        low, re.IGNORECASE | re.DOTALL,
    ):
        return ["text", "diagram"]

    for output, markers in _OUTPUT_MARKERS.items():
        if any(_contains_marker(low, marker) for marker in markers):
            result.append(output)
    # A copy renderer is intentional only when the user asks for a distinct
    # plain-text block/button; ordinary code blocks already have copy support.
    if re.search(r"(?:блок\w*\s+(?:для|под)\s+копирован\w*|блок\w*\s+с\s+кнопк\w*\s+копирован\w*|текст\w*.{0,35}блок\w*.{0,25}копирован\w*|(?:в\s+)?блок\w*\s+(?:копи|копирован\w*)|копи\s*[-–—]?\s*блок|copyable\s+(?:text\s+)?block|copy\s+block|text\s+block\s+with\s+(?:a\s+)?copy\s+button|block\s+with\s+(?:a\s+)?copy\s+button|блок\w*\s+для\s+копіюван\w*|блок\w*.{0,30}копіюван\w*)", low, re.I):
        if "copy" not in result:
            result.append("copy")
    # Explicit requests to receive or export a deliverable as a file. A bare
    # mention of a file remains context; an action plus a file format/noun is required.
    file_delivery_request = bool(re.search(
        r"(?:\b(?:пришл\w*|присла\w*|дай\w*|выдай\w*|прилож\w*|прикреп\w*|сохран\w*|экспортир\w*|скача\w*|отправ\w*|сформир\w*|сдела\w*|созда\w*|сгенерир\w*|напиш\w*|подготов\w*)\b.{0,120}\b(?:файл\w*|файлом|xlsx|excel|csv|pdf|docx)\b|"
        r"\b(?:файл\w*|файлом|xlsx|excel|csv|pdf|docx)\b.{0,100}\b(?:для\s+скачиван\w*|скача\w*|скачиван\w*)\b|"
        r"\b(?:send|give|export|download|save|deliver|create|generate|write|attach)\w*\b.{0,120}\b(?:file|xlsx|csv|pdf|docx|excel)\b|(?:таблиц\w*|код\w*|скрипт\w*|текст\w*).{0,80}(?:\bв\s+(?:отдельн\w*\s+)?файл\w*|\bфайлом\b|\bв\s+(?:формат\w*\s+)?(?:xlsx|excel|csv|pdf|docx)\b|\bfile\b|\bxlsx\b|\bcsv\b|\bpdf\b|\bdocx\b))",
        low, re.I | re.S,
    ))
    if file_delivery_request and "file" not in result:
        result.append("file")

    # A plain image/photo mention is input context, not an output request.
    # The object-order-aware detector captures explicit image requests even
    # when users insert "мне", an adjective, or other polite filler.
    explicit_image_request = _detect_image_generation_request(low)
    explicit_portrait_request = _detect_explicit_portrait_generation_request(low)
    if (explicit_image_request or explicit_portrait_request) and "image" not in result:
        result.append("image")
    if explicit_image_request:
        # The requested output is the picture itself. Do not also classify
        # words describing the picture (e.g. "картинку со схемой") as a
        # separate diagram, graph, formula, or table artifact.
        result = [kind for kind in result if kind not in {"diagram", "graph", "formula", "table"}]

    # Catch compound/hyphenated programming requests such as "Python-код" even when
    # the exact phrase is absent from the phrase table. A code noun alone is not enough.
    has_code_noun = bool(re.search(
        r"(?:\b(?:python|javascript|typescript|java|rust|go|c\+\+|c#)\s*[-–— ]\s*код\w*|"
        r"\b(?:код\w*|скрипт\w*|code|script)\b)",
        low, re.IGNORECASE,
    ))
    has_code_action = bool(re.search(
        r"\b(?:напиш\w*|созда\w*|сгенерир\w*|покаж\w*|дай\w*|выдай\w*|исправ\w*|перепиш\w*|"
        r"оптимизир\w*|улучш\w*|рефактор\w*|write|create|generate|show|give|provide|fix|rewrite|refactor|optimi[sz]e)\b",
        low, re.IGNORECASE,
    ))
    if has_code_noun and has_code_action and "code" not in result:
        result.append("code")

    # Common compound requests say "build a table and graph" only once. Recognize
    # the chart noun together with an explicit construction/visualization verb.
    has_graph_noun = bool(re.search(
        r"\b(?:graph|chart|plot|график|графика|графики|графиков)\b|(?:столбчат\w*|линейн\w*)\s+(?:диаграмм\w*|график\w*)|\bbar\s+chart\b",
        low,
    ))
    has_graph_action = bool(re.search(
        # Stem matching catches inflected forms like "построим", "построила",
        # and polite/imperative variants without depending on exact endings.
        r"\b(?:build|create|show|draw|plot|make|visualize|visualise|постро\w*|созда\w*|покаж\w*|нарис\w*|сдела\w*|визуализир\w*|побуд\w*|выдай\w*|отдай\w*|верни\w*|предостав\w*|вывед\w*)\b",
        low,
    ))
    if has_graph_noun and has_graph_action and "graph" not in result:
        result.append("graph")

    # A 3D visualization can be requested without the word "graph/chart".
    # Treat an explicit create/build/show action plus 3D + visualization/scene/model
    # terminology as a graph artifact request, not as a text-only explanation.
    has_3d_marker = bool(re.search(
        r"(?:\b3\s*[- ]?d\b|\bthree[- ]dimensional\b|\b3d\s+(?:graph|plot|scene|model|visuali[sz]ation)\b|тр[её]хмерн\w*)",
        low,
    ))
    has_visual_noun = bool(re.search(
        r"(?:visuali[sz]ation|visualisation|visualization|3d[- ]?scene|3d[- ]?model|\bscene\b|\bmodel\b|визуализац\w*|\bсцен\w*|\bмодел\w*|поверхност\w*|сфер\w*|куб\w*|треугольн\w*|воронк\w*|волн\w*|\bmesh(?:es)?\b|\bsphere(?:s)?\b|\bcube(?:s)?\b|\btriangle(?:s)?\b|\bfunnel(?:s)?\b|\bsurface\w*|\bplot\b|\bchart\b|\bgraph\b|график\w*|диаграмм\w*)",
        low,
    ))
    if has_3d_marker and has_graph_action and has_visual_noun and "graph" not in result:
        result.append("graph")

    if not result:
        result.append("text")
    elif "text" not in result:
        result.insert(0, "text")
    return result



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

def _enhance_requested_outputs(text: str, explicit_outputs: list[str]) -> list[str]:
    """Add only high-confidence structured views implied by the user's task.

    A room is never an output trigger: only the current semantic request selects
    renderers. Bare drawing imperatives ask for clarification, not fabricated art.
    """
    low = _text(text).lower().replace("ё", "е")
    if is_april_identity_question(low) or is_current_user_name_question(low) or is_bare_visual_command(low):
        return ["text"]
    outputs = list(dict.fromkeys(explicit_outputs or ["text"]))
    explicit_image_request = _detect_image_generation_request(low)

    comparison = bool(re.search(
        r"\b(?:compare|comparison|compare\s+with|versus|vs\.?|differences?\s+between|pros\s+and\s+cons)\b"
        r"|(?:сравни\w*|сравнен\w*|разниц\w*\s+между|отличи\w*|чем\s+отличает\w*|плюсы\s+и\s+минусы|преимуществ\w*\s+и\s+недостатк\w*)",
        low,
    ))
    workflow_or_architecture = bool(re.search(
        r"\b(?:workflow|workflows|pipeline|architecture|sequence|process\s+flow|flowchart|algorithm|steps\s+of|system\s+design)\b"
        r"|(?:архитектур\w*|последовательност\w*|алгоритм\w*|блок[- ]схем\w*|схем\w*\s+работ\w*|цепочк\w*\s+работ\w*|этап\w*\s+процесс\w*|как\s+устроен\w*|порядок\s+работ\w*)",
        low,
    ))
    mathematical_function = bool(re.search(
        r"\b(?:function|exponential|exponent|equation|derivative|integral|sin|cos|tan|cot)\b"
        r"|(?:функци\w*|экспонент\w*|уравнен\w*|производн\w*|интеграл\w*|синус\w*|косинус\w*|тангенс\w*|тригонометр\w*)",
        low,
    ))

    if comparison and "table" not in outputs:
        outputs.append("table")
    if workflow_or_architecture and not explicit_image_request and "diagram" not in outputs:
        outputs.append("diagram")

    # Table intent may use Russian inverted word order or an adjective between
    # the verb and noun ("таблицу покажи периодическую", "покажи периодическую
    # таблицу"). Detect the requested renderer before generic visual-action
    # inference, so "show the table" can never accidentally invoke Images 2.0.
    table_noun = r"(?:\btable\b|\bтаблиц\w*)"
    table_action = (
        r"(?:\b(?:show|display|build|create|make|prepare|construct|render|generate|draw|list|provide|present)\b|"
        r"покаж\w*|отобраз\w*|постро\w*|созда\w*|сдела\w*|подготов\w*|сформир\w*|выдай\w*|отдай\w*|верни\w*|предостав\w*|вывед\w*|"
        r"состав\w*|вывед\w*|представ\w*|нарис\w*)"
    )
    table_request = bool(
        re.search(table_action + r".{0,120}" + table_noun, low, flags=re.IGNORECASE | re.DOTALL)
        or re.search(table_noun + r".{0,120}" + table_action, low, flags=re.IGNORECASE | re.DOTALL)
    )
    # Voice transcripts and compound turns often put the table noun and action
    # in different clauses: "в таблице, вывел каждую ... выдай всю таблицу
    # Менделеева". Treat the requested view as cumulative, not as plain text.
    table_grid_request = bool(re.search(
        r"(?:периодическ\w*.{0,80}таблиц\w*|таблиц\w*.{0,80}(?:менделеев\w*|периодическ\w*)|"
        r"(?:всю|полную|все\s+118|все\s+элемент\w*).{0,45}таблиц\w*|"
        r"таблиц\w*.{0,80}(?:ячейк\w*|окошк\w*|порядков\w+\s+номер\w*|атомн\w+\s+номер\w*)|"
        r"(?:show|display|list|print|give|provide|build|create).{0,60}(?:periodic\s+table)|"
        r"(?:full\s+periodic\s+table).{0,50}(?:table|elements))",
        low, re.IGNORECASE | re.DOTALL,
    ))
    if (table_request or table_grid_request) and "table" not in outputs:
        outputs.append("table")

    # Semantic visual policy: generic drawing verbs do not imply raster image
    # generation. Formulae, geometry, diagrams, plots and 3D constructions use
    # typed renderers; Images Generator is reserved for explicit picture/photo/
    # illustration wording or unmistakable artistic/photorealistic intent.
    visual_action = bool(re.search(
        r"(?<![\w\u0080-\uffff])(?:draw(?:ing)?|show|display|create|make|render|visuali[sz]e|add|place|put|remove|replace|"
        r"нарис\w*|гарис\w*|рисуй\w*|покаж\w*|отобраз\w*|изобраз\w*|постро\w*|побуд\w*|созда(?!тель)\w*|сдела\w*|визуализир\w*|добав\w*|помест\w*|размест\w*|убер\w*|замен\w*|объясни\w*|поясни\w*|выдай\w*|отдай\w*|верни\w*|предостав\w*|вывед\w*)(?![\w\u0080-\uffff])",
        low,
    ))
    # Geometry, measured figures and mathematical constructions are structured
    # diagrams by default. This is intentionally independent of the renderer:
    # the SceneContract still decides how the concrete diagram payload is shown.
    explicit_diagram_intent = bool(re.search(
        r"(?:\b(?:diagram|schematic|blueprint|technical drawing|engineering drawing|flowchart|"
        r"geometry|geometric figure|triangle|square|rectangle|circle|point|segment|angle|polygon|"
        r"radius|diameter|perimeter|area|dimension|dimensions|measurement|vector|chessboard|chess board|grid|"
        r"sphere|cube|pyramid|cone|cylinder)\b|"
        r"диаграмм\w*|схем\w*|чертеж\w*|чертёж\w*|креслен\w*|блок[- ]схем\w*|"
        r"геометр\w*|(?:математич\w*|геометрическ\w*)\s+фигур\w*|точк\w*|отрез\w*|"
        r"треугольн\w*|квадрат\w*|прямоугольн\w*|параллелограмм\w*|ромб\w*|трапец\w*|многоугольн\w*|"
        r"окружност\w*|круг\w*|эллипс\w*|сфер\w*|шар\w*|куб\w*|пирамид\w*|конус\w*|цилиндр\w*|угол\w*|вектор\w*|координат\w*|"
        r"сторон\w*|радиус\w*|диаметр\w*|периметр\w*|площад\w*|размер\w*|"
        r"измерен\w*|черт[её]ж\w*|стрелк\w*|размерн\w*\s+лини\w*|"
        r"шахматн\w*\s+доск\w*|электрическ\w*\s+цеп\w*|сетка\w*|контур\w*)",
        low,
    ))
    explicit_graph_intent = bool(re.search(
        r"(?:\b(?:graph|chart|plot|3d graph|curve|surface plot)\b|график\w*|график\s+функци\w*|"
        r"парабол\w*|гипербол\w*|(?:волна|волн\w*|\bwave\b|\bwaves\b)(?:\s+(?:график\w*|функци\w*|поверхност\w*|эффект\w*))?|"
        r"волнов\w*\s+(?:график\w*|функци\w*|поверхност\w*)|"
        r"поверхност\w*\s+(?:график\w*|функци\w*|визуализац\w*)|"
        r"постро\w*\s+(?:график|поверхност))",
        low,
    ))
    visual_explanation_intent = bool(re.search(
        r"(?:наглядн\w*|с\s+помощью\s+(?:стрелок|фигур|схем)|стрелк\w*|"
        r"визуальн\w*\s+объясн|объясни\w*.{0,35}(?:схем\w*|диаграмм\w*|фигур\w*))",
        low,
    ))
    if (visual_action and explicit_diagram_intent or visual_explanation_intent) and not explicit_image_request and "diagram" not in outputs and "graph" not in outputs:
        outputs.append("diagram")

    # A formula/equation is a typed mathematical object even when the user says
    # "draw/show it" rather than "write the formula". Keep it out of Images 2.0.
    formula_noun = bool(re.search(r"(?:\bformula\b|\bequation\b|формул\w*|уравнен\w*)", low, re.I))
    formula_action = bool(re.search(
        r"(?:\b(?:write|show|draw|display|render|derive|solve|give|present)\w*\b|"
        r"напиш\w*|покаж\w*|нарис\w*|гарис\w*|запиш\w*|вывед\w*|получ\w*|реш\w*|представ\w*|отобраз\w*)",
        low, re.I,
    ))
    if formula_noun and formula_action and not explicit_image_request and "formula" not in outputs:
        outputs.append("formula")

    if visual_action and explicit_graph_intent and not explicit_image_request and "graph" not in outputs:
        outputs.append("graph")

    # A generic visual verb defaults to a structured diagram, not raster image
    # generation. Raster generation requires an explicit image/photo request or
    # clear artwork/photorealism intent; that intent remains compatible with the
    # explicit-image branch below.
    artistic_intent = bool(re.search(
        r"(?:photorealistic|photo[- ]realistic|oil painting|watercolor|watercolour|"
        r"digital painting|concept art|anime style|comic style|poster|album cover|"
        r"фотореалист\w*|акварел\w*|маслян\w*\s+живопис\w*|"
        r"цифров\w*\s+живопис\w*|концепт[- ]арт|стил\w*\s+аниме|"
        r"комиксн\w*\s+стил\w*|постер|обложк\w*|"
        r"ui\s+mockup|app\s+mockup|interface\s+design|user interface|screen design|smartphone mockup|"
        r"макет\w*\s+(?:интерфейс\w*|телефон\w*)|интерфейс\w*\s+приложен\w*|дизайн\w*\s+телефон\w*)",
        low, re.I,
    ))
    if (
        visual_action
        and not explicit_diagram_intent
        and not explicit_graph_intent
        and "image" not in outputs
        and not any(kind in outputs for kind in ("diagram", "graph", "table", "formula", "code", "file", "link", "copy"))
    ):
        outputs.append("image" if artistic_intent else "diagram")
    if explicit_image_request:
        outputs = [kind for kind in outputs if kind not in {"diagram", "graph", "formula", "table"}]
        if "image" not in outputs:
            outputs.append("image")
    # Formula view only for a clearly mathematical request. Graphs remain explicit
    # unless the request asks to plot/visualize data or a function.
    if mathematical_function and bool(re.search(
        r"(?:формул\w*|уравнен\w*|запиши\w*|реши\w*|formula|equation|derive|solve|write\s+the)"
        r"|(?:график\w*|построй\w*|визуализир\w*|plot\s+the|graph\s+of)", low
    )) and "formula" not in outputs and "graph" not in outputs:
        outputs.append("formula")

    if "text" not in outputs:
        outputs.insert(0, "text")
    return list(dict.fromkeys(outputs))


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
    r"отблагодар\w*|поблагодар\w*|пожалова\w*|жалоб\w*|feedback|report\s+(?:button|response|answer)|thank(?:s|ing)?\s+button)",
    re.IGNORECASE,
)

def _is_site_navigation_request(text: Any) -> bool:
    """True for requests about where/how to use an April UI route, not history recall."""
    source = _text(text).strip()
    if not source:
        return False
    low = source.lower().replace("ё", "е")
    if _is_attachment_tutorial_request(source):
        return True
    if not _SITE_NAVIGATION_TARGET_RE.search(low):
        return False
    return bool(_SITE_NAVIGATION_REQUEST_RE.search(low))


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
    dissatisfaction = has_phrase(dissatisfaction_terms)
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
    own_topic_or_output = explicit_topic_introduction or has_independent_payload
    context_dependent_reaction = bool(
        not own_topic_or_output
        and not explicit_topic_introduction
        and (
            (acknowledgement and len(tokens) <= 4)
            or waiting_acknowledgement
            or gratitude
            or positive_evaluation
            or dissatisfaction
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
            else "ACKNOWLEDGE_BRIEFLY_AND_CONTINUE_NATURALLY" if positive_evaluation or acknowledgement
            else "ANSWER_NORMALLY"
        ),
        "tone": "GRATEFUL" if gratitude else "POSITIVE" if positive_evaluation or acknowledgement else "DISSATISFIED" if dissatisfaction or negation else "CORRECTIVE" if correction or revision_request else "NEUTRAL",
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
        },
    }


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
    ui_help = _is_site_navigation_request(request) or (callable(ui_instruction_detector) and bool(ui_instruction_detector(request))) or attach_help
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
        outputs = list(dict.fromkeys(["text", "diagram"]))
        source_requirement = "никакой исходный файл не требуется для инструкции"
    elif ui_help:
        action, domain, target = "EXPLAIN_UI_ROUTE", "april_ui", "verified_site_map"
        must_not = ["не придумывать кнопку, раздел, URL или тариф", "для страницы без реализации честно описать статус"]
        success = ["назвать стартовый экран и точную кнопку", "описать куда попадёт пользователь", "дать следующий шаг и безопасный путь назад"]
        source_requirement = "APRIL_SITE_MAP и проверенные UI blueprint-описания"
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
    return {
        "step_index": int(index), "domain": domain, "action": action, "target": target,
        "output_types": list(outputs or ["text"]),
        "source_requirement": source_requirement, "depends_on_previous": bool(sem.get("parent_context_dependency") or sem.get("inherits_current_request_subject")),
        "must_not": must_not, "success_criteria": success,
    }


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
    if _is_feedback_control_help_request(source):
        return [source]
    # Keep several route questions together as one navigation workflow. A separate
    # explicit artifact/calculation action is still split by the normal task path.
    if _is_site_navigation_request(source) and not _has_explicit_independent_non_ui_action(source):
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
            "context_dependent_reaction": bool(short_social_only or short_continuation_action or contextual_reaction or assistant_repetition_feedback),
            "context_dependent_question": bool(contextual_question or linked_by_user_turn or linked_by_answer),
            "active_branch_repair": bool(assistant_repetition_feedback or disagreement or dissatisfaction),
        })
        profile["features"] = features
        signals.update({
            "latest_exchange_link": True,
            "previous_answer_reference": True,
            "context_dependent_reaction": bool(short_social_only or contextual_reaction or assistant_repetition_feedback),
            "context_dependent_question": bool(contextual_question or linked_by_user_turn or linked_by_answer),
            "active_branch_repair": bool(assistant_repetition_feedback or disagreement or dissatisfaction),
        })
        profile["pragmatic_features"] = signals
        profile["context_dependent_reaction"] = bool(short_social_only or short_continuation_action or contextual_reaction or assistant_repetition_feedback)
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
    explicit_switch = bool(
        base.get("explicit_topic_switch") or base.get("explicit_topic_introduction")
        or latest_profile.get("explicit_topic_switch")
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
    requested_outputs = _enhance_requested_outputs(request_text, detected_outputs)
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

    # Keep edit restrictions separate from permitted creation. A new picture
    # described in the current dialogue remains a normal Free generation. An edit
    # request is restricted by default; the executor may authorize this exact edit
    # only after reserving one referral-bonus unit from the Free bonus bucket.
    image_modification_requested = _detect_image_modification(
        request_text, has_existing_image_reference=has_existing_image_reference
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
    ))
    contextual_source_edit = bool(has_existing_image_reference and _detect_contextual_image_edit(request_text))
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
            "question_sequence": _build_question_sequence(original or text),
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
                "In Free, an explicit request to alter an existing image, photo, diagram, chart, or drawing is restricted unless the executor has explicitly authorized and reserved one referral bonus operation for this exact request. When no such authorization is present, return a concise, soft localized limitation, do not ask the user to upload the image again, and do not generate a replacement image or diagram. Never set free_image_recreation to bypass this restriction. An executor-authorized referral bonus permits this one edit and consumes one bonus operation; ordinary new image generation and ordinary new diagrams remain enabled.",
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
