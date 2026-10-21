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
        "write formula", "show formula", "solve equation", "write an equation",
        "напиши формулу", "покажи формулу", "реши уравнение", "запиши уравнение",
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


def _detect_image_modification(text: str) -> bool:
    """Detect a request to alter an existing image or diagram.

    In Free, detected edits are restricted instead of being silently converted
    into new image generation. Ordinary new-image and new-diagram requests use
    their existing routes.
    """
    low = _text(text).lower().replace("ё", "е")
    if not low:
        return False
    how_to_question = bool(re.search(
        r"^\s*(?:как\s+(?:(?:мне|можно|самому|самой)\s+)?(?:редактир|измен|улучш|обработ|ретуш|поменя)"
        r"|как\s+делать\s+ретуш|объясни\w*\s*,?\s*как\b|расскажи\w*\s*,?\s*как\b"
        r"|how\s+(?:do\s+i|can\s+i|to)\s+(?:edit|change|improve|enhance|retouch|modify)"
        r"|what\s+is\s+the\s+best\s+way\s+to\s+(?:edit|change|improve|enhance|retouch))",
        low,
        flags=re.IGNORECASE,
    ))
    if how_to_question:
        return False

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

    This intentionally checks the first visual object after the action. For
    example, "нарисуй картинку со схемой" is an image-generation request, while
    "нарисуй схему на картинке" remains a structured diagram request.
    """
    low = _text(text).lower().replace("ё", "е")
    if not low:
        return False
    # Explicit editing is not image generation in the Free chain. The caller will
    # issue a Premium-limit explanation and suppress all image artifacts.
    if _detect_image_modification(low):
        return False

    # "Draw on the picture this parallelogram with dimensions" refers to a
    # structured geometry drawing, not to a raster picture whose subject is an
    # image. The surface wording ("на картинке") must not outrank the requested
    # technical object. Keep this guard narrow so "нарисуй кота на картинке"
    # and other genuine image/compositing requests retain their existing route.
    structured_drawing_subject = bool(re.search(
        r"(?:параллелограмм\w*|треугольн\w*|квадрат\w*|прямоугольн\w*|ромб\w*|"
        r"трапец\w*|многоугольн\w*|окружност\w*|\bpolygon\b|\btriangle\b|"
        r"\bsquare\b|\brectangle\b|\bparallelogram\b|\brhombus\b|"
        r"\btrapezoid\b|\bgraph\b|\bfunction\b|\bequation\b|"
        r"геометр\w*\s+фигур\w*|черт[её]ж\w*|схем\w*|диаграмм\w*|график\w*|"
        r"функци\w*|уравнен\w*|координат\w*|формул\w*|"
        r"с\s+(?:произвольн\w*\s+)?размер\w*|размер\w*\s+(?:кажд\w*\s+)?сторон\w*)",
        low,
        flags=re.IGNORECASE,
    ))
    drawing_on_image_surface = bool(re.search(
        r"(?:нарис\w*|гарис\w*|draw|render|постро\w*|покаж\w*)\b.{0,35}"
        r"\b(?:на|в)\s+(?:(?:этой|этот|эту|той|тои|такой|таком)\s+)?"
        r"(?:картинк\w*|изображени\w*|фот\w*)",
        low,
        flags=re.IGNORECASE,
    ))
    if structured_drawing_subject and drawing_on_image_surface:
        return False

    action = r"(?:draw|show|display|create|make|generate|render|add|place|put|remove|replace|нарис\w*|гарис\w*|рисуй\w*|покаж\w*|отобраз\w*|созда\w*|сдела\w*|сгенерир\w*|изобраз\w*|добав\w*|помест\w*|размест\w*|убер\w*|замен\w*)"
    image_noun = r"(?:picture|image|illustration|photo|photograph|картинк(?:у|а|и|е)\b|изображени(?:е|я|и|и\s+на)\b|иллюстраци(?:ю|я|и)\b|фот\w*)"
    # Permit polite words and ordinary modifiers, but do not skip a preceding
    # explicit schema/graph/table noun to reinterpret its object as an image.
    filler = r"(?:(?!(?:схем\w*|диаграмм\w*|график\w*|таблиц\w*|черт[её]ж\w*)\b)[\w-]+\s+)"
    forward = rf"(?<![\w\u0080-\uffff]){action}\b\s+(?:{filler}){{0,4}}{image_noun}"
    # Support inverted Russian requests such as "картинку нарисуй". The
    # accusative/nominative object forms deliberately exclude "на картинке".
    reverse = rf"(?<![\w\u0080-\uffff]){image_noun}\s+(?:мне\s+|нам\s+)?{action}\b"
    return bool(re.search(forward, low, flags=re.IGNORECASE) or re.search(reverse, low, flags=re.IGNORECASE))


def _detect_requested_outputs(text: str) -> list[str]:
    result: list[str] = []
    low = _text(text).lower()
    for output, markers in _OUTPUT_MARKERS.items():
        if any(_contains_marker(low, marker) for marker in markers):
            result.append(output)

    # A plain image/photo mention is input context, not an output request.
    # The object-order-aware detector captures explicit image requests even
    # when users insert "мне", an adjective, or other polite filler.
    explicit_image_request = _detect_image_generation_request(low)
    if explicit_image_request and "image" not in result:
        result.append("image")
    if explicit_image_request:
        # The requested output is the picture itself. Do not also classify
        # words describing the picture (e.g. "картинку со схемой") as a
        # separate schematic artifact. A scheme named before "на картинке"
        # does not enter this branch and keeps the diagram route.
        result = [kind for kind in result if kind != "diagram"]

    # Common compound requests say "build a table and graph" only once. Recognize
    # the chart noun together with an explicit construction/visualization verb.
    has_graph_noun = bool(re.search(
        r"\b(?:graph|chart|plot|график|графика|графики|графиков)\b|(?:столбчат\w*|линейн\w*)\s+(?:диаграмм\w*|график\w*)|\bbar\s+chart\b",
        low,
    ))
    has_graph_action = bool(re.search(
        # Stem matching catches inflected forms like "построим", "построила",
        # and polite/imperative variants without depending on exact endings.
        r"\b(?:build|create|show|draw|plot|make|visualize|visualise|постро\w*|созда\w*|покаж\w*|нарис\w*|сдела\w*|визуализир\w*|побуд\w*)\b",
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


def _enhance_requested_outputs(text: str, explicit_outputs: list[str]) -> list[str]:
    """Add only high-confidence structured views implied by the user's task.

    This never infers image generation, invented data, or external-source URLs.
    """
    low = _text(text).lower().replace("ё", "е")
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
        r"покаж\w*|отобраз\w*|постро\w*|созда\w*|сдела\w*|подготов\w*|сформир\w*|"
        r"состав\w*|вывед\w*|представ\w*|нарис\w*)"
    )
    table_request = bool(
        re.search(table_action + r".{0,60}" + table_noun, low, flags=re.IGNORECASE)
        or re.search(table_noun + r".{0,60}" + table_action, low, flags=re.IGNORECASE)
    )
    if table_request and "table" not in outputs:
        outputs.append("table")

    # Semantic drawing policy: ordinary requests to draw/create/show a picture
    # go to Images Generator. Diagram is reserved for explicit schematic,
    # blueprint, technical drawing, or measured-drawing intent. Graphs remain
    # a separate mathematical/data visualization route.
    visual_action = bool(re.search(
        r"(?<![\w\u0080-\uffff])(?:draw(?:ing)?|show|display|create|make|render|visuali[sz]e|add|place|put|remove|replace|"
        r"нарис\w*|гарис\w*|рисуй\w*|покаж\w*|отобраз\w*|изобраз\w*|постро\w*|побуд\w*|созда\w*|сдела\w*|визуализир\w*|добав\w*|помест\w*|размест\w*|убер\w*|замен\w*|объясни\w*|поясни\w*)(?![\w\u0080-\uffff])",
        low,
    ))
    # Geometry, measured figures and mathematical constructions are structured
    # diagrams by default. This is intentionally independent of the renderer:
    # the SceneContract still decides how the concrete diagram payload is shown.
    explicit_diagram_intent = bool(re.search(
        r"(?:\b(?:diagram|schematic|blueprint|technical drawing|engineering drawing|flowchart|"
        r"geometry|geometric figure|triangle|square|rectangle|circle|point|segment|angle|polygon|"
        r"radius|diameter|perimeter|area|dimension|dimensions|measurement|vector)\b|"
        r"диаграмм\w*|схем\w*|чертеж\w*|чертёж\w*|креслен\w*|блок[- ]схем\w*|"
        r"геометр\w*|(?:математич\w*|геометрическ\w*)\s+фигур\w*|точк\w*|отрез\w*|"
        r"треугольн\w*|квадрат\w*|прямоугольн\w*|параллелограмм\w*|ромб\w*|трапец\w*|многоугольн\w*|"
        r"окружност\w*|круг\w*|эллипс\w*|угол\w*|вектор\w*|координат\w*|"
        r"сторон\w*|радиус\w*|диаметр\w*|периметр\w*|площад\w*|размер\w*|"
        r"измерен\w*|черт[её]ж\w*|стрелк\w*|размерн\w*\s+лини\w*)",
        low,
    ))
    explicit_graph_intent = bool(re.search(
        r"(?:\b(?:graph|chart|plot|3d graph)\b|график\w*|график\s+функци\w*|"
        r"постро\w*\s+(?:график|поверхност))",
        low,
    ))
    visual_explanation_intent = bool(re.search(
        r"(?:наглядн\w*|с\s+помощью\s+(?:стрелок|фигур|схем)|стрелк\w*|"
        r"визуальн\w*\s+объясн|объясни\w*.{0,35}(?:схем\w*|диаграмм\w*|фигур\w*))",
        low,
    ))
    if (visual_action and explicit_diagram_intent or visual_explanation_intent) and not explicit_image_request and "diagram" not in outputs:
        outputs.append("diagram")
    if (
        visual_action
        and not explicit_diagram_intent
        and not explicit_graph_intent
        and "image" not in outputs
        and not any(kind in outputs for kind in ("diagram", "graph", "table", "formula", "code", "file", "link"))
    ):
        outputs.append("image")
    if explicit_image_request:
        outputs = [kind for kind in outputs if kind != "diagram"]
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
        if re.search(r"(?:\bsphere\w*\b|\bcube\w*\b|\bobject\s+scene\b|\b3d\s+scene\b|сфер\w*|куб\w*|объект\w*\s+сцен\w*|пространствен\w*\s+объект)", low):
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
    "последняя тема", "последнюю тему", "последний диалог", "последний разговор",
    "в последнее время", "за последнее время", "назови последнюю тему",
    "последние диалоги", "первые диалоги", "последние сообщения",
    "список диалогов", "список тем", "покажи историю", "истории диалогов",
)
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
    "continuation_action": ("продолж", "вернись", "возвращ", "останов", "resume", "continue", "return to"),
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
    return bool(pattern.search(low))


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
    return bool(qualifier_only and len(tokens) <= 5)


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
        "отнюд", "подроб", "поясн", "объясн", "уточн", "разъясн",
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
    acknowledgement = short and any(
        token in agreement_terms or any(token.startswith(root) for root in ("соглас", "правиль", "точн"))
        for token in tokens
    ) and not any(token in rejection_terms or token in {"не", "никак", "ни"} for token in tokens)
    negation = short and (
        any(token in rejection_terms for token in tokens)
        or ("не" in token_set and bool(token_set & {"так", "то", "это", "совсем", "согласен", "согласна", "верно", "правильно"}))
        or bool(re.search(r"\b(?:не\s+соглас\w*|не\s+так|не\s+то|не\s+это|я\s+не\s+это)\b", low))
    )
    correction = any(term in low for term in correction_terms) or (
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
            or negation
            or correction
            or ((clarification or explanation_request) and short and not context_dependent_question)
        )
    )

    if correction:
        speech_act = "CORRECTION"
    elif negation:
        speech_act = "NEGATION_OR_DISAGREEMENT"
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

    if context_dependent_reaction or context_dependent_question or answer_followup:
        communicative_act = "CONTINUATION"
    elif acknowledgement:
        communicative_act = "ACKNOWLEDGEMENT"
    elif negation or correction:
        communicative_act = "RESPONSE_OR_CORRECTION"
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
        "pragmatic_features": {
            "acknowledgement_or_agreement": bool(acknowledgement),
            "negation_or_disagreement": bool(negation),
            "correction": bool(correction),
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
    continuation_action = _semantic_group_hit(tokens, "continuation_action")
    explicit_topic_introduction = _has_explicit_topic_introduction(source)
    answer_followup = _looks_like_previous_answer_followup(source)
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
    temporal_past = past_reference or today_reference or recent_reference or bool(token_set & {"вчера", "сегодня", "утром", "вечером", "yesterday", "today"})
    temporal_future = future_reference or bool(token_set & {"завтра", "будем", "буду", "будущем", "tomorrow", "will"})
    explicit_time_reference = bool(re.search(
        r"\b(?:(?:\d+|один|одна|одно|одну|два|две|пару|три|четыре|пять|полчаса|полторы?)\s*(?:-|–|—|до)?\s*)?(?:минут\w*|мин\b|час\w*|ч\b|дн\w*|сутк\w*|полчаса)\s*(?:назад|тому назад)\b|\b(?:в|около|примерно в)\s*\d{1,2}[:.]\d{2}\b",
        low,
    ))
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
    ) and not future_topic_question

    context_dependent_question = _looks_like_context_dependent_question(
        source, interrogative=interrogative,
        explicit_topic_introduction=explicit_topic_introduction,
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

    if history_recall:
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

    # A compact feature vector makes routing inspectable; values are deterministic
    # feature activations, not neural embeddings or calibrated probabilities.
    features = {
        "dialogue_action": bool(dialogue_action),
        "recall_action": bool(recall_action),
        "decision_action": bool(decision_action),
        "plan_action": bool(plan_action),
        "continuation_action": bool(continuation_action),
        "answer_followup": bool(answer_followup),
        "context_dependent_question": bool(context_dependent_question),
        "context_dependent_reaction": bool(context_dependent_reaction),
        "self_reference": bool(self_reference),
        "past_reference": bool(past_reference),
        "today_reference": bool(today_reference),
        "recent_reference": bool(recent_reference),
        "future_reference": bool(temporal_future),
        "interrogative": bool(interrogative),
    }
    return {
        "schema": "april_request_semantics_v1",
        "method": "rules_fuzzy_lexical_v1",
        "primary_intent": primary_intent,
        "direction": direction,
        "time_scope": time_scope,
        "topic_reference": topic_reference,
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
        "features": features,
        "reason": reason,
        "context_signature": _context_signature(source),
    }


def _is_history_request(text: str) -> bool:
    low = _text(text).lower().replace("ё", "е")
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
        limit = 5
    elif _text(memory.get("history_selection_method")) == "named_topic_section_vector":
        limit = max(2, min(3, int(memory.get("continuation_context_limit") or 3)))
    else:
        limit = 2
    return [dict(item) for item in pairs if isinstance(item, dict)][:limit]


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


def _split_request_sequence(text: str) -> list[str]:
    """Find ordered questions/tasks without rewriting or de-duplicating user text.

    Boundaries are conservative: list markers, explicit question marks, semicolons,
    a new imperative/action clause, or a clear second interrogative clause. Ordinary
    commas and coordinated noun phrases are otherwise preserved.
    """
    source = _text(text)
    if not source:
        return []
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
        sequence.append({
            "step_index": index,
            "request": item,
            "output_types": outputs or ["text"],
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


def build_interpretation(
    *,
    current_request: str,
    original_request: str = "",
    display_language: str = "auto",
    memory: dict[str, Any] | None = None,
    attachments: list[dict[str, Any]] | None = None,
    visual_context: list[dict[str, Any]] | None = None,
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
    routing_capabilities = _infer_routing_capabilities(request_text)

    # Keep edit restrictions separate from permitted creation. A new picture
    # described in the current dialogue remains a normal Free generation; a
    # request to alter an existing photo/diagram is Premium-only and must not
    # be rerouted into a replacement generation.
    image_modification_requested = _detect_image_modification(request_text)
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
    image_edit_restricted = bool(
        image_modification_requested
        or (has_user_source_image and compositing_requested and not structured_diagram_noun)
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
    wants_file = "file" in requested_outputs
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
            "continuation_context": {
                "active_topic": _text(memory.get("active_topic")),
                "reason": _text(memory.get("reason")),
                "confidence": float(memory.get("relation_confidence") or 0.0),
                "selected_pairs": selected_pairs,
                "anchor": continuation_anchor,
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
                "In Free, an explicit request to alter an existing image, photo, diagram, chart, or drawing is Premium-only: return a concise, soft localized limitation, do not ask the user to upload the image again, and do not generate a replacement image or diagram. Never set free_image_recreation to enable a generation for an edit request. Ordinary new image generation and ordinary new diagrams remain enabled.",
                "Use a formula renderer for mathematical notation; use a graph only when a function or grounded numeric data can define it.",
                "For graph requests, follow intent.graph_policy: trends/time-ordered values use line; categorical comparisons use bar; choose only among those 2D types unless explicit 3D intent or real 3D source data supports 3D.",
                "Never turn 2D x/y data into a 3D chart by inventing a zero z-axis; true 3D requires explicit XYZ values, a real surface grid/function of x and y, or structured spatial objects.",
                "Use code, link, file, image, and gallery renderers only when the response contains matching valid payloads and the request/context supports them.",
                "Never invent numeric data, URLs, files, or images just to fill a renderer.",
                "Every structured artifact must carry an explicit renderer type and its payload through the canonical SceneContract.",
            ],
            "improvement_policy": "Improve the requested result while preserving unaffected behavior; do not invent missing source content.",
            "output_plan": requested_outputs,
            "semantic_interpretation": request_semantics,
            "semantic_interpretation_version": "april_request_semantics_v1",
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
