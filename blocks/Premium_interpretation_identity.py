"""April Premium Interpretation Identity + request interpretation layer.

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
        payload = {"component": "premium_interpretation", "stage": stage}
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
        "ссылки на ресурсы", "ссылка на ресурс", "ссылки на источники",
        "ссылки на сайты", "ресурсы с описанием", "ссылки с описанием",
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


def _detect_image_generation_request(text: str) -> bool:
    """Detect a picture as the requested output, not a picture used as context.

    This intentionally checks the first visual object after the action. For
    example, "нарисуй картинку со схемой" is an image-generation request, while
    "нарисуй схему на картинке" remains a structured diagram request.
    """
    low = _text(text).lower().replace("ё", "е")
    if not low:
        return False
    if _detect_image_modification(low):
        return True

    action = r"(?:draw|show|display|create|make|generate|render|нарис\w*|покаж\w*|показ\w*|отобраз\w*|созда\w*|сдела\w*|сгенерир\w*|изобраз\w*)"
    image_noun = r"(?:picture|image|illustration|photo|картинк\w*|изображени\w*|иллюстраци\w*|фотк\w*|фото\b|фотограф\w*|снимк\w*)"
    # Permit polite words and ordinary modifiers, but do not skip a preceding
    # explicit schema/graph/table noun to reinterpret its object as an image.
    filler = r"(?:(?!(?:схем\w*|диаграмм\w*|график\w*|таблиц\w*|черт[её]ж\w*)\b)[\w-]+\s+)"
    forward = rf"(?<![\w\u0080-\uffff]){action}\b\s+(?:{filler}){{0,4}}{image_noun}"
    # Support inverted Russian requests such as "картинку нарисуй". The
    # accusative/nominative object forms deliberately exclude "на картинке".
    reverse = rf"(?<![\w\u0080-\uffff]){image_noun}\s+(?:мне\s+|нам\s+)?{action}\b"

    # Composite requests commonly put an explicit renderer first and the image
    # second: "покажи таблицу и его фотку". The earlier object-order guard kept
    # this from becoming an image request at all. Preserve both outputs instead
    # of making the table and photo mutually exclusive.
    structured_noun = r"(?:\btable\b|таблиц\w*|\bgraph\b|\bchart\b|график\w*|диаграмм\w*|схем\w*|примеры|\bexamples?\b)"
    coordinated_after = rf"(?<![\w\u0080-\uffff]){action}\b.{{0,100}}{structured_noun}.{{0,48}}(?:и|and|plus|а также).{{0,28}}{image_noun}"

    # In a follow-up, people frequently omit the verb because the operation is
    # obvious from the preceding turn: "А фотку его и таблица каличная — сделай
    # красивей". Accept this elliptical image target only when it is coordinated
    # with another requested output and an actual edit/beautify action.
    photo_noun = r"(?:фотк\w*|фото\b|фотограф\w*|снимк\w*|picture\w*|photo\w*|image\w*)"
    possessive = r"(?:его|ее|её|их|мой|моя|мое|мои|наш|наша|наше|наши|his|her|their|my|our)"
    coordinated_before = rf"(?<![\w\u0080-\uffff])(?:а\s+|и\s+|еще\s+|ещё\s+|also\s+)?{photo_noun}\s+(?:{possessive}\s+)?(?:.{0,48})?(?:и|and|а также).{{0,60}}(?:таблиц\w*|\btable\b|график\w*|диаграмм\w*).{{0,60}}(?:сдела\w*|улучш\w*|исправ\w*|оформ\w*|красив\w*|make\b|improve\b|beautif\w*)"
    return bool(
        re.search(forward, low, flags=re.IGNORECASE)
        or re.search(reverse, low, flags=re.IGNORECASE)
        or re.search(coordinated_after, low, flags=re.IGNORECASE)
        or re.search(coordinated_before, low, flags=re.IGNORECASE)
    )


def _detect_link_request(text: str) -> bool:
    """Recognize explicit plural/resource link requests without mistaking recall for generation."""
    low = _text(text).lower().replace("ё", "е")
    if not low:
        return False
    action = r"(?:дай\w*|покаж\w*|показ\w*|пришл\w*|отправ\w*|найд\w*|подбер\w*|привед\w*|собер\w*|объясн\w*|опиш\w*|give|show|send|share|find|provide|list|explain|describe)"
    link_noun = r"(?:ссылк\w*|веб-?ссылк\w*|url-?адрес\w*|\burls?\b|\blinks?\b)"
    resource_noun = r"(?:ресурс\w*|источник\w*|сайт\w*|resource\w*|source\w*|website\w*)"
    action_request = re.search(rf"(?<![\w\u0080-\uffff]){action}\b.{{0,72}}{link_noun}", low, re.IGNORECASE)
    noun_request = re.search(rf"{link_noun}.{{0,36}}{resource_noun}|{resource_noun}.{{0,36}}{link_noun}", low, re.IGNORECASE)
    resource_explanation = re.search(rf"{resource_noun}.{{0,44}}(?:с\s+описани\w*|что\s+объясня\w*|куда\s+вед\w*|explain\w*|describe\w*)", low, re.IGNORECASE)
    return bool(action_request or noun_request or resource_explanation)


def _has_drawable_subject(text: str) -> bool:
    """True when a visual verb has a concrete drawable object, not just style words."""
    low = _text(text).lower().replace("ё", "е")
    drawable_objects = (
        r"(?:\bcat\b|\bdog\b|\bperson\b|\bportrait\b|\blandscape\b|\bhouse\b|"
        r"\btree\b|\bflower\b|\bcar\b|\bship\b|\bplanet\b|\bdinosaur\w*\b|"
        r"\bduck\b|\bmap\b|\bavatar\b|\bcharacter\b|\bobject\b|\bmodel\b|"
        r"кот\w*|собак\w*|человек\w*|портрет\w*|пейзаж\w*|дом\w*|дерев\w*|цвет\w*|"
        r"машин\w*|корабл\w*|планет\w*|динозавр\w*|утк\w*|карт\w*|аватар\w*|"
        r"персонаж\w*|объект\w*|макет\w*|модель\w*|предмет\w*|иллюстрац\w*)"
    )
    return bool(re.search(drawable_objects, low, flags=re.IGNORECASE))


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
    explicit_link_request = _detect_link_request(low)
    if explicit_link_request and "link" not in result:
        result.append("link")
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

    Image output is inferred only by the object-aware request detector, never by a
    generic style verb alone; this does not invent data or external-source URLs.
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
        r"\b(?:function|exponential|exponent|equation|derivative|integral|sin|cos|tan|cot|formula)\b"
        r"|(?:функци\w*|экспонент\w*|уравнен\w*|производн\w*|интеграл\w*|синус\w*|косинус\w*|тангенс\w*|тригонометр\w*|формул\w*|теорем\w*)",
        low,
    ))
    formula_cue = bool(re.search(
        r"(?:формул\w*|уравнен\w*|formula\w*|equation\w*|mass[- ]energy)", low
    ))
    application_cue = bool(re.search(
        r"(?:пример\w*|где\s+примен\w*|применен\w*|использован\w*|област\w*\s+применен\w*|"
        r"application\w*|use\s+cases?|used\s+in|examples?)", low
    ))
    appearance_cue = bool(re.search(
        r"(?:как\s+(?:он|она|они)\s+выгляд\w*|как\s+выгляд\w*|внешност\w*|портрет\w*|"
        r"what\s+(?:did|does)\s+.{0,60}\s+look\s+like|appearance|portrait)", low
    ))

    # Semantic contract: formula language requests a FormulaRenderer, applications/examples
    # request a populated TableBlock, and an explicit appearance question requests an
    # illustrative image. These cues are independent and cumulative, not exclusive.
    if formula_cue and "formula" not in outputs:
        outputs.append("formula")
    if application_cue and "table" not in outputs:
        outputs.append("table")
    if appearance_cue and "image" not in outputs:
        outputs.append("image")

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
        r"(?<![\w\u0080-\uffff])(?:draw(?:ing)?|show|display|create|make|render|visuali[sz]e|"
        r"нарис\w*|покаж\w*|отобраз\w*|изобраз\w*|постро\w*|побуд\w*|созда\w*|сдела\w*|визуализир\w*)(?![\w\u0080-\uffff])",
        low,
    ))
    explicit_diagram_intent = bool(re.search(
        r"(?:\b(?:diagram|schematic|blueprint|technical drawing|engineering drawing|flowchart)\b|"
        r"диаграмм\w*|схем\w*|чертеж\w*|креслен\w*|блок[- ]схем\w*)",
        low,
    ))
    explicit_graph_intent = bool(re.search(
        r"(?:\b(?:graph|chart|plot|3d graph)\b|график\w*|график\s+функци\w*|"
        r"постро\w*\s+(?:график|поверхност))",
        low,
    ))
    if visual_action and explicit_diagram_intent and not explicit_image_request and "diagram" not in outputs:
        outputs.append("diagram")
    if (
        visual_action
        and not explicit_diagram_intent
        and not explicit_graph_intent
        and "image" not in outputs
        and not any(kind in outputs for kind in ("diagram", "graph", "table", "formula", "code", "file", "link"))
        and _has_drawable_subject(low)
    ):
        outputs.append("image")
    if explicit_image_request:
        outputs = [kind for kind in outputs if kind != "diagram"]
        if "image" not in outputs:
            outputs.append("image")

    # A request for pictures/illustrations of experiments asks for a separate,
    # explanatory schematic. It must not be swallowed by the final portrait/image.
    experiment_visuals = bool(re.search(
        r"(?:(?:картинк\w*|изображени\w*|иллюстраци\w*|picture\w*|image\w*|illustration\w*)"
        r".{0,48}(?:опыт\w*|эксперимент\w*|experiment\w*)|"
        r"(?:опыт\w*|эксперимент\w*|experiment\w*).{0,48}"
        r"(?:картинк\w*|изображени\w*|иллюстраци\w*|picture\w*|image\w*|illustration\w*))",
        low, re.IGNORECASE,
    ))
    if experiment_visuals and "diagram" not in outputs:
        outputs.append("diagram")

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
        # Image output is additive in a compound request. Do not let one photo
        # request replace a biography/explanation/table/diagram with an image-only task.
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
    "о чем мы говорили", "о чём мы говорили", "о чем говорили", "о чём говорили",
    "что мы обсуждали", "что обсуждали", "какие темы", "напомни темы",
    "напомни о чем", "напомни о чём", "история диалога", "история разговора",
    "наши темы", "о чем шла речь", "о чём шла речь",
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
    "recall_action": ("напом", "вспом", "припомн", "помни", "восстанов", "remember", "recall", "remind", "summariz", "перескаж", "перечисл"),
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
    "recall_action": ("напомни", "напомнить", "вспомни", "вспомнить", "припомни", "помнишь", "помниш", "помнить", "вспоминаешь", "восстанови", "summarize", "remember", "recall"),
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
    # Request-management verbs are not topic entities. Excluding their common
    # inflections prevents short clauses like “можешь перенести эти данные?”
    # from becoming a fake topic named “можес/перенес”.
    "давай", "можешь", "можес", "может", "могу", "можно", "можете", "сможешь",
    "работать", "работаем", "работай", "перенеси", "перенести", "перенос",
    "окей", "okay", "пожалуйста", "please", "хочу", "хочешь", "нужно", "надо",
    "вчера", "сегодня", "позавчера", "утром", "вечером", "ночью", "днем", "днём",
    "час", "часа", "часов", "минут", "неделю", "недели", "месяце", "годе",
    "последних", "последние", "раньше", "недавно", "сегодняшний", "октября", "января",
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
    # Short English feedback/questions are discourse markers, not topic names.
    "what", "mean", "hate", "nice", "good", "okay", "thanks", "thank", "agree",
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
    "работ", "перенес", "перенос", "можеш", "может", "могу", "давай",
    "хотел", "хочет", "хочеш", "сможет", "сможеш", "попрос", "пожалуй",
    "вчера", "сегодня", "позавчера", "утром", "вечером", "ночью", "недавно", "последн",
    "придум", "предложи", "почем", "почему", "зачем", "открыл", "изобрел", "изобрёл",
    "доказал", "обосновал", "считал", "называл", "формул", "график", "таблиц",
    "диаграмм", "уравнен", "данн", "значен",
    # Short interpersonal reactions must not be misread as named topic entities.
    "спасибо", "спасиб", "благодар", "классн", "крут", "отлич", "прекрас", "здоров",
    "молодц", "понят", "непон", "понял", "поняла", "соглас", "правил", "верн", "точн",
    "именно", "ладн", "опять", "ужас", "нрав", "бесит", "раздраж", "разочар",
    "передел", "перепиш", "исправ", "улучш", "поправ", "отнюд", "ошиб", "мимо",
    "получ", "виду", "смысл", "лучше",
    # English conversational reactions are not external topic entities.
    "thank", "thanks", "appreci", "great", "brilliant", "nice", "perfect",
    "wonderful", "excellent", "awesome", "good", "wrong", "misunderstood",
    "understand", "disagree", "agree", "hate", "frustrat", "annoy", "irritat",
    "revise", "rewrite", "improve", "redo", "fix", "correct", "mean", "what",
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
        # Normalize common inflected/topic-level variants before short stemming.
        token = {
            "стихи": "стих", "стиха": "стих", "стихом": "стих", "стихе": "стих",
            "стихотворение": "стих", "стихотворения": "стих", "стихотворению": "стих",
            "стихотворением": "стих", "стихотворении": "стих", "стихотворений": "стих",
            "поэтический": "поэзия", "поэтическая": "поэзия", "поэтическое": "поэзия",
        }.get(token, token)
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


def _has_explicit_topic_switch(text: str) -> bool:
    """Recognize explicit user-directed branch changes without relying on topic nouns alone."""
    low = _text(text).lower().replace("ё", "е").strip()
    if not low:
        return False
    explicit_switch = re.search(
        r"(?:^|[.!?;:\n]\s*)(?:новая\s+тема|другая\s+тема|другой\s+вопрос|"
        r"перейд[её]м\s+к(?:\s+новой\s+теме)?|"
        r"давай(?:те)?\s+(?:сменим|сменить)\s+тему|"
        r"switch\s+to\s+(?:a\s+)?new\s+topic|new\s+topic|"
        r"let['’]?s\s+change\s+the\s+topic)(?:\b|\s*[:—-])",
        low,
        flags=re.IGNORECASE,
    )
    if explicit_switch:
        return True
    # “Теперь про X” is a branch change when X is explicitly named. Do not
    # interpret an ordinary continuation preface (“а теперь объясни это”) as one.
    return bool(re.search(
        r"(?:^|[.!?;:]\s*)теперь\s+(?:о|про|об|обо)\s+"
        r"(?!него\b|неё\b|нее\b|ней\b|ним\b|нем\b|нём\b|них\b|"
        r"мне\b|нас\b|это\b|этого\b|этой\b|этот\b|этом\b|эту\b|эти\b|"
        r"him\b|her\b|them\b|it\b|this\b|that\b|those\b|these\b)[а-яa-z0-9]",
        low,
        flags=re.IGNORECASE,
    ))


def _has_explicit_topic_introduction(text: str) -> bool:
    """Return true when a request explicitly introduces a subject instead of only referring back.

    A named-content request such as “continue further; tell me about Ramanujan's life”
    must not be classified as a continuation merely because the preface contains “continue”.
    Pure anaphoric phrases such as “tell me about him/that” remain continuations.
    """
    low = _text(text).lower().replace("ё", "е")
    if _has_explicit_topic_switch(low):
        return True
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


def _looks_like_next_step_followup(text: str) -> bool:
    """Recognise compact next-step questions as dialogue follow-ups, not new subjects.

    This is intentionally limited to short, subjectless wording. A self-contained
    question that names a separate subject still follows the regular NEW path.
    """
    low, tokens = _semantic_normalize(text)
    if not low or len(tokens) > 9:
        return False
    pattern = (
        r"(?:(?:ну|хорошо|ладно|окей|ок|давай|тогда|так)\s+)?"
        r"(?:(?:а|и)\s+)?"
        r"(?:"
        r"следующ\w*\s+шаг"
        r"|какой\s+(?:будет\s+)?следующ\w*\s+шаг"
        r"|что\s+(?:нам\s+)?делать\s+дальше"
        r"|что\s+(?:будет\s+)?дальше"
        r"|what\s+(?:is\s+)?next(?:\s+step)?"
        r"|what\s+is\s+the\s+next\s+step"
        r"|what'?s\s+(?:the\s+)?next\s+step"
        r"|what\s+comes\s+next"
        r"|next\s+step"
        r")"
    )
    return bool(re.fullmatch(pattern, low))


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



def _looks_like_topic_reference_fragment(
    text: str,
    *,
    explicit_topic_introduction: bool = False,
) -> bool:
    """Recognise a short topic pointer that should search memory before treating it as new.

    Examples include “про стих”, “я про Premium”, and “я имел в виду тот график”.
    A concrete instruction such as “расскажи про Эйнштейна” is not a fragment and
    keeps the normal new-information path. The state manager still decides whether
    a real matching memory entry exists; this helper only asks it to look.
    """
    low, tokens = _semantic_normalize(text)
    if not low or len(tokens) > 10 or explicit_topic_introduction:
        return False
    if _detect_requested_outputs(text) != ["text"]:
        return False
    # Requests with an independent action are tasks, not bare topic pointers.
    action = re.search(
        r"\b(?:расскажи|расскажите|объясни|объясните|напиши|напишите|опиши|опишите|"
        r"покажи|построй|создай|сделай|вычисли|сравни|найди|проверь|проанализируй|"
        r"продолжи|перечисли|нарисуй|tell|describe|explain|write|show|build|create|"
        r"make|calculate|compare|find|check|analyze|continue)\b",
        low,
    )
    # A self-correction is a memory pointer even when it names the intended topic.
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
    pointer = re.match(
        r"^(?:(?:а|и|ну|так|нет|не)\s+)?(?:(?:я|мы)\s+)?(?:именно\s+)?"
        r"(?:про|об|обо|насч[её]т|относительно|по\s+поводу|about|regarding)\s+\S+",
        low,
    )
    return bool(pointer)

def _detect_previous_answer_recheck(text: str) -> bool:
    """Detect a challenge/check of April's earlier response, including long turns.

    This is intentionally narrower than ordinary disagreement detection: it needs
    a prior-answer/action reference plus a challenge, verification or explanation
    cue, so a self-contained question on a new subject does not become a repair.
    """
    low = _text(text).lower().replace("ё", "е")
    if not low:
        return False

    assistant_action = r"(?:назвал\w*|назвала\w*|назвали|сказал\w*|сказала\w*|сказали|ответил\w*|ответила\w*|ответили|написал\w*|написала\w*|написали|выбрал\w*|выбрала\w*|выбрали|решил\w*|решила\w*|решили|сделал\w*|сделала\w*|сделали|предложил\w*|предложила\w*|выдал\w*|выдала\w*|назван\w*|ответ\w*|написан\w*|chosen|said|answered|wrote|picked|selected|did)"
    challenge = r"(?:почему|зачем|как\s+так|должн\w*|следовал\w*|надо\s+было|нужно\s+было|вместо|хотя|ошиб\w*|неправил\w*|неверн\w*|проверь\w*|перепроверь\w*|сверь\w*|объясни\w*|поясни\w*|разбер\w*|проверь\s+что|why|how\s+come|should\s+have|instead|although|wrong|mistake|check|verify|explain|review)"

    # Direct second-person reference to something April actually said/did.
    direct_action = bool(re.search(
        rf"\b(?:ты|вы|you)\s+(?:же\s+|ведь\s+|вообще\s+)?{assistant_action}\b",
        low,
        flags=re.IGNORECASE,
    ))
    direct_why = bool(re.search(
        rf"\b(?:почему|зачем|how\s+come|why)\s+(?:ты|вы|you)\s+.{0,80}{assistant_action}\b",
        low,
        flags=re.IGNORECASE,
    ))
    assistant_mistake = bool(re.search(
        r"\b(?:ты|вы|you)\s+(?:ошиб\w*|перепутал\w*|неправил\w*|неверн\w*|got\s+it\s+wrong|made\s+a\s+mistake)\b",
        low,
        flags=re.IGNORECASE,
    ))
    verification_target = bool(re.search(
        rf"\b(?:проверь\w*|перепроверь\w*|сверь\w*|проверь\s+еще\s+раз|check|verify|review)\b.{{0,100}}(?:что\s+)?(?:ты|вы|you)?\s*{assistant_action}\b",
        low,
        flags=re.IGNORECASE,
    ))
    prior_answer_pointer = bool(re.search(
        r"(?:предыдущ\w*\s+ответ|прошл\w*\s+ответ|что\s+ты\s+(?:сказал\w*|сказала|написал\w*|написала|назвал\w*|назвала|ответил\w*|ответила)|"
        r"то,?\s+что\s+ты\s+(?:сказал\w*|сказала|написал\w*|написала|назвал\w*|назвала|ответил\w*|ответила)|"
        r"previous\s+answer|what\s+you\s+(?:said|wrote|answered|called|named|selected))",
        low,
        flags=re.IGNORECASE,
    ))
    obligation_contrast = bool(re.search(
        rf"\b(?:ты|вы|you)\s+(?:должн\w*|следовал\w*|should\s+have)\b.{{0,100}}(?:а\s+ты|но\s+ты|хотя|вместо|but\s+you|instead)\b.{{0,70}}{assistant_action}\b",
        low,
        flags=re.IGNORECASE,
    ))
    cue = bool(re.search(challenge, low, flags=re.IGNORECASE))
    # Asking for the value April just named/wrote is recall of the assistant's own
    # output even without an explicit accusation or correction cue.
    compact_value_recall = bool(re.search(
        r"\b(?:какое|какой|какая|какую|что|which|what)\b.{0,70}"
        r"\b(?:числ\w*|букв\w*|слов\w*|вариант\w*|номер\w*|ответ\w*|number|letter|word|option|answer)\b.{0,55}"
        r"\b(?:ты|вы|you)\s+(?:назвал\w*|назвала|назвали|сказал\w*|сказала|сказали|"
        r"написал\w*|написала|написали|ответил\w*|ответила|ответили|выбрал\w*|выбрала|выбрали)\b",
        low, flags=re.IGNORECASE,
    ))
    direct_value_recall = bool(re.search(
        r"\b(?:что\s+ты\s+(?:назвал\w*|сказал\w*|написал\w*|ответил\w*)|"
        r"(?:какое|какой|какая|какую)\s+(?:именно\s+)?(?:числ\w*|букв\w*|слов\w*|номер\w*)\s+(?:ты|вы)\b)",
        low, flags=re.IGNORECASE,
    ))

    return bool(
        direct_why
        or obligation_contrast
        or assistant_mistake
        or verification_target
        or compact_value_recall
        or direct_value_recall
        or (prior_answer_pointer and cue)
        or (direct_action and cue)
    )


def _is_repair_followup_clause(text: str) -> bool:
    """Recognize a clause that continues a repair already established upstream."""
    low = _text(text).lower().replace("ё", "е").strip(" \t\r\n,;:.-")
    if not low:
        return False
    if _detect_previous_answer_recheck(low):
        return True

    # A connective must not turn a fully independent new task into a repair just
    # because it begins with "то есть" or "объясни". Keep object-bearing commands
    # only when their object clearly points back to the current exchange.
    standalone_command = re.match(
        r"^(?:(?:то\s+есть|ведь|а\s+значит|и\s+значит)\s*[,;:]?\s*)?"
        r"(?:расскажи\w*|расскажите|опиши\w*|опишите|создай\w*|создайте|"
        r"напиши\w*|напишите|покажи\w*|покажите|построй\w*|постройте|"
        r"реши\w*|решите|объясни\w*|объясните|поясни\w*|поясните|разъясни\w*|"
        r"проверь\w*|перепроверь\w*|сверь\w*|уточни\w*|дай\s+мне|tell\s+me\s+about|"
        r"explain|clarify|verify|check|describe|create|write|show|solve|что\s+такое|what\s+is)"
        r"\s+(?:(?:про|о|об|насчет|about|для)\s+)?([\w\u0080-\uffff-]+)",
        low,
        flags=re.IGNORECASE,
    )
    if standalone_command:
        pointed_back = bool(re.search(
            r"(?:\b(?:это|этот|эта|эту|этого|эти|тот|та|ту|предыдущ\w*|прошл\w*|"
            r"ответ\w*|сказанн\w*|названн\w*|ошиб\w*|правил\w*|услов\w*|"
            r"игр\w*|ход\w*|букв\w*|город\w*|задач\w*|формул\w*|уравнен\w*|"
            r"график\w*|таблиц\w*|этот\s+текст|this|that|previous|last|answer|mistake|rule|move|letter|city|task|formula|equation)\b)",
            low,
            flags=re.IGNORECASE,
        ))
        if not pointed_back:
            return False
    if re.match(
        r"^(?:ведь|то\s+есть|а\s+значит|и\s+значит|но\s+ведь|"
        r"я\s+(?:что-то\s+)?(?:запутал\w*|не\s+понима\w*|не\s+понял\w*)|"
        r"объясни\w*|поясни\w*|разъясни\w*|проверь\w*|перепроверь\w*|"
        r"уточни\w*|разбер\w*|в\s+чем\s+ошиб\w*|в\s+ч[её]м\s+ошиб\w*|"
        r"почему\s+так|как\s+так|why\s+is\s+that|explain\b|check\b|clarify\b)",
        low,
        flags=re.IGNORECASE,
    ):
        return True
    tokens = [t for t in re.findall(r"[\w\u0080-\uffff]+", low) if len(t) > 1]
    return bool(
        len(tokens) <= 4
        and any(token.startswith(("объясни", "объясните", "поясни", "поясните", "разъясни", "проверь", "перепроверь", "уточни", "уточните", "explain", "check", "clarify")) for token in tokens)
    )


def _infer_dialogue_act_profile(
    text: str,
    *,
    interrogative: bool,
    context_dependent_question: bool,
    answer_followup: bool,
    continuation_action: bool,
    explicit_topic_introduction: bool,
    topic_reference_fragment: bool = False,
) -> dict[str, Any]:
    """Classify conversational intent without turning reaction wording into a topic.

    All sentiment/reaction signals are advisory. They only bind to the active
    exchange when the message does not clearly introduce a self-contained new task.
    """
    low, tokens = _semantic_normalize(text)
    if not tokens:
        return {
            "speech_act": "EMPTY", "communicative_act": "EMPTY",
            "pragmatic_intent": "NONE", "message_function": "EMPTY",
            "context_dependent_reaction": False, "topic_reference_fragment": False,
            "tone": "NEUTRAL", "recommended_response_action": "ANSWER_NORMALLY",
            "pragmatic_features": {},
        }

    token_set = set(tokens)
    signature = _context_signature(text)
    previous_answer_reference = _detect_previous_answer_recheck(text)
    factual_verification_request = bool(re.search(
        r"(?:проверь\w*|перепроверь\w*|сверь\w*|check\s+(?:the\s+)?(?:previous\s+)?answer|verify\s+(?:the\s+)?answer|review\s+(?:what\s+you\s+said|the\s+previous\s+answer))",
        low, flags=re.IGNORECASE,
    ))
    subjects = signature.get("subject_terms") if isinstance(signature, dict) else []
    output_forms = signature.get("output_forms") if isinstance(signature, dict) else []
    non_topical_roots = (
        "понят", "спаси", "благодар", "хорош", "ладн", "молод", "отлич", "здоров",
        "прекрас", "классн", "крут", "соглас", "правиль", "точн", "верн", "ага", "угу",
        "да", "нет", "неа", "отнюд", "подро", "подроб", "поясн", "объясн", "уточн", "разъясн",
        "расшифр", "докаж", "обоснуй", "обоснуйте", "имел", "имела", "имели", "виду",
        "друго", "смысл", "так", "это", "получ", "непон", "понял", "поняла", "нрав",
        "ужас", "бесит", "раздраж", "разочар", "передел", "перепиш", "исправ", "улучш",
        "поправ", "ошиб", "мимо", "передум", "неверн", "неправил", "именн", "прави",
        "согла", "опять", "лучше",
    )
    meaningful_subjects = [
        _text(term) for term in (subjects or [])
        if _text(term) and not any(_text(term).startswith(root) for root in non_topical_roots)
    ]
    numeric_anchors = signature.get("numeric_anchors") if isinstance(signature.get("numeric_anchors"), list) else []
    has_independent_payload = bool(meaningful_subjects or output_forms or numeric_anchors)
    short = len(tokens) <= 9
    has_deictic_reference = bool(token_set & {
        "это", "этот", "эта", "эту", "этого", "этой", "этом", "эти", "тот", "та", "ту",
        "того", "он", "она", "оно", "они", "его", "ее", "её", "ей", "ему", "им", "их",
        "него", "нее", "неё", "ней", "ним", "нем", "нём", "них",
        "it", "this", "that", "he", "she", "they", "him", "her", "them",
    })

    agreement_terms = {
        "да", "ага", "угу", "ок", "окей", "ладно", "хорошо", "верно", "точно", "именно",
        "правильно", "согласен", "согласна", "согласны", "конечно", "yes", "yeah", "yep",
        "ok", "okay", "right", "exactly", "correct", "agreed",
    }
    rejection_terms = {
        "нет", "неа", "неверно", "неправильно", "ошибка", "мимо", "отнюдь",
        "no", "nope", "wrong", "incorrect",
    }
    gratitude_terms = (
        "спасибо", "спасибки", "благодарю", "благодарен", "благодарна", "очень признателен",
        "ценю это", "thanks", "thank you", "many thanks", "appreciate it",
    )
    positive_terms = (
        "классно", "круто", "отлично", "здорово", "прекрасно", "замечательно", "молодец",
        "хорошо получилось", "вот это хорошо", "супер", "great", "brilliant", "well done",
        "looks good", "nice work", "perfect",
    )
    dissatisfaction_terms = (
        "не нравится", "не устраивает", "не то", "не так", "неправильно", "мимо", "ужасно",
        "раздражает", "бесит", "не то что я просил", "не то что я просила",
        "ты не поняла", "ты не понял", "вы не поняли", "опять не понял", "опять не поняла",
        "не понимаешь меня", "ты меня не понимаешь", "не то имел в виду", "не то имела в виду",
        "not what i asked", "you misunderstood", "you did not understand", "i don't understand", "i do not understand",
        "you don't understand me", "you do not understand me", "i hate this", "i hate it", "this is annoying",
        "i'm frustrated", "im frustrated", "doesn't work", "does not work",
    )
    revision_terms = (
        "переделай", "переделать", "перепиши", "переписать", "исправь", "поправь", "улучши",
        "сделай иначе", "попробуй иначе", "по другому", "по-другому", "заново", "с нуля",
        "можно лучше", "можно было лучше", "а можно лучше", "давай лучше", "надо лучше",
        "redo", "revise", "rewrite", "fix that", "make it better", "could be better", "try again", "do it differently",
    )
    correction_terms = (
        "не так", "не то", "не это", "не совсем", "я имел в виду", "я имел ввиду",
        "я имела в виду", "я имела ввиду", "я про другое", "не об этом", "не об этом речь",
        "поправка", "уточню", "я не про", "я не об", "не про это спрашивал",
        "не про это спрашивала", "я не это спрашивал", "я не это спрашивала",
        "not that", "not what i meant", "i meant", "that's not right",
    )
    clarification_terms = (
        "поясни", "поясните", "уточни", "уточните", "разъясни", "разъясните",
        "что ты имеешь в виду", "что вы имеете в виду", "в каком смысле", "подробнее",
        "расшифруй", "clarify", "what do you mean", "elaborate",
    )
    explanation_terms = (
        "объясни", "объясните", "докажи", "докажите", "обоснуй", "обоснуйте", "почему",
        "как это работает", "как это получается", "explain", "prove", "why does", "why is", "how does",
    )
    has_phrase = lambda phrases: any(phrase in low for phrase in phrases)
    gratitude = short and has_phrase(gratitude_terms)
    positive_evaluation = short and has_phrase(positive_terms)
    dissatisfaction = has_phrase(dissatisfaction_terms)
    revision_request = has_phrase(revision_terms) and short
    acknowledgement = short and any(
        token in agreement_terms or token.startswith(("соглас", "правиль", "точн")) for token in tokens
    ) and not any(token in rejection_terms or token in {"не", "никак", "ни"} for token in tokens)
    negation = short and (
        any(token in rejection_terms for token in tokens)
        or ("не" in token_set and bool(token_set & {"так", "то", "это", "совсем", "согласен", "согласна", "верно", "правильно"}))
        or bool(re.search(r"\b(?:не\s+соглас\w*|не\s+так|не\s+то|не\s+это|я\s+не\s+это|i\s+(?:do\s+not|don\s+t)\s+agree|not\s+really|no\s+way)\b", low))
    )
    correction = previous_answer_reference or has_phrase(correction_terms) or dissatisfaction or (
        negation and bool(token_set & {"это", "то", "так", "другое", "имел", "имела", "виду"})
    )
    clarification = has_phrase(clarification_terms)
    explanation_request = has_phrase(explanation_terms) or (interrogative and bool(token_set & {"почему", "как", "зачем", "why", "how"}))
    own_topic_or_output = explicit_topic_introduction or (has_independent_payload and not topic_reference_fragment)
    correction_of_active = bool(
        not explicit_topic_introduction
        and (
            previous_answer_reference
            or (
                short and (correction or dissatisfaction or revision_request)
                and ((not meaningful_subjects and not numeric_anchors) or has_deictic_reference or topic_reference_fragment or bool(re.search(
                    r"\b(?:я\s+имел\w*\s+в\s*(?:виду|ввиду)|я\s+имела\w*\s+в\s*(?:виду|ввиду)|я\s+не\s+про\b|не\s+про\s+.+\s+спрашивал\w*|не\s+про\s+.+\s+спрашивала\w*|ты\s+не\s+понял\w*|ты\s+меня\s+не\s+понима\w*)\b",
                    low,
                )))
            )
        )
    )
    context_dependent_reaction = bool(
        not explicit_topic_introduction
        and (
            (acknowledgement and len(tokens) <= 5 and not has_independent_payload)
            or (gratitude and not has_independent_payload)
            or (positive_evaluation and not has_independent_payload)
            or correction_of_active
            or previous_answer_reference
            or (negation and (not has_independent_payload or has_deictic_reference))
            or ((clarification or explanation_request) and short and not has_independent_payload)
            # Short anaphoric fragments such as “теперь о нём подробнее” point
            # back to the current exchange even without a question mark or a fixed
            # continuation verb. A named independent subject still bypasses this.
            or (has_deictic_reference and short and not has_independent_payload)
            or topic_reference_fragment
        )
    )

    if correction_of_active or correction:
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
    elif context_dependent_question or has_deictic_reference or topic_reference_fragment:
        speech_act = "REFERENTIAL_CONTINUATION"
    elif continuation_action:
        speech_act = "CONTINUATION_REQUEST"
    elif interrogative:
        speech_act = "INFORMATION_QUESTION"
    else:
        speech_act = "STATEMENT_OR_REQUEST"

    if correction_of_active or revision_request:
        communicative_act = "REVISE_PREVIOUS_RESPONSE"
        recommended_response_action = (
            "RECHECK_PREVIOUS_RESPONSE_AND_CORRECT_IF_NEEDED"
            if previous_answer_reference or factual_verification_request
            else "REPAIR_OR_IMPROVE_PREVIOUS_RESPONSE"
        )
        tone = "DISSATISFIED" if dissatisfaction or negation else "CORRECTIVE"
    elif gratitude:
        communicative_act = "APPRECIATION_AND_CONTINUE"
        recommended_response_action = "ACKNOWLEDGE_BRIEFLY_AND_CONTINUE_NATURALLY"
        tone = "GRATEFUL"
    elif positive_evaluation or acknowledgement:
        communicative_act = "ACKNOWLEDGEMENT_OR_POSITIVE_FEEDBACK"
        recommended_response_action = "ACKNOWLEDGE_BRIEFLY_AND_CONTINUE_NATURALLY"
        tone = "POSITIVE"
    elif negation or dissatisfaction:
        communicative_act = "RESPOND_TO_DISAGREEMENT"
        recommended_response_action = "RECHECK_PREVIOUS_RESPONSE_AND_CORRECT_IF_NEEDED"
        tone = "DISSATISFIED"
    elif clarification:
        communicative_act = "CLARIFICATION"
        recommended_response_action = "CLARIFY_THE_PREVIOUS_POINT"
        tone = "CURIOUS_OR_UNCERTAIN"
    elif context_dependent_question or answer_followup or topic_reference_fragment:
        communicative_act = "CONTINUE_ACTIVE_DIALOGUE"
        recommended_response_action = "ANSWER_FROM_THE_RELEVANT_DIALOGUE_CONTEXT"
        tone = "NEUTRAL"
    else:
        communicative_act = "NEW_OR_STANDALONE"
        recommended_response_action = "ANSWER_NORMALLY"
        tone = "NEUTRAL"

    return {
        "speech_act": speech_act,
        "communicative_act": communicative_act,
        "pragmatic_intent": speech_act.lower(),
        "message_function": communicative_act.lower(),
        "context_dependent_reaction": context_dependent_reaction,
        "topic_reference_fragment": bool(topic_reference_fragment),
        "previous_answer_reference": bool(previous_answer_reference),
        "active_branch_repair": bool(not explicit_topic_introduction and (correction_of_active or previous_answer_reference)),
        "factual_verification_request": bool(factual_verification_request),
        "tone": tone,
        "recommended_response_action": (
            "ACKNOWLEDGE_COMPLETED_RESULT_WITHOUT_REPEATING"
            if acknowledgement and len(tokens) <= 2 and not has_independent_payload
            else recommended_response_action
        ),
        "pragmatic_features": {
            "acknowledgement_or_agreement": bool(acknowledgement),
            "bare_acknowledgement": bool(acknowledgement and len(tokens) <= 2 and not has_independent_payload),
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
            "topic_reference_fragment": bool(topic_reference_fragment),
            "has_independent_payload": bool(has_independent_payload),
            "previous_answer_reference": bool(previous_answer_reference),
            "active_branch_repair": bool(not explicit_topic_introduction and (correction_of_active or previous_answer_reference)),
            "factual_verification_request": bool(factual_verification_request),
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
            "time_window": extract_temporal_window(""),
            "requested_topic_count": 10, "minimum_topic_count": 5,
            "intent_score": 0, "features": {}, "reason": "empty_request",
        }

    dialogue_action = _semantic_group_hit(tokens, "dialogue_action")
    recall_action = _semantic_group_hit(tokens, "recall_action")
    decision_action = _semantic_group_hit(tokens, "decision_action") or (
        "пришли" in token_set and bool(token_set & {"к", "чему", "выводу"})
    ) or "к чему мы пришли" in low or "what did we conclude" in low
    plan_action = _semantic_group_hit(tokens, "plan_action")
    continuation_action = _semantic_group_hit(tokens, "continuation_action")
    explicit_topic_switch = _has_explicit_topic_switch(source)
    explicit_topic_introduction = _has_explicit_topic_introduction(source)
    answer_followup = _looks_like_previous_answer_followup(source)
    past_reference = _semantic_group_hit(tokens, "past_reference")
    future_reference = _semantic_group_hit(tokens, "future_reference")
    today_reference = _semantic_group_hit(tokens, "today_reference")
    recent_reference = _semantic_group_hit(tokens, "recent_reference")
    # Explicit dates, ranges and rolling durations are parsed once into a UTC
    # interval. The state manager intersects that interval with Premium's retained
    # 24-hour window; a time phrase is metadata, not a standalone history trigger.
    time_window = extract_temporal_window(source)
    has_explicit_time_window = bool(time_window.get("has_constraint"))
    minimum_topic_count, requested_topic_count = extract_topic_count_bounds(source, default=10)
    history_reference_words = bool(re.search(
        r"\b(?:тем\w*|топик\w*|диалог\w*|разговор\w*|перепис\w*|говорил\w*|"
        r"обсужд\w*|истори\w*|запрос\w*|topics?|conversations?|chats?|discussion\w*|history)\b",
        low, re.IGNORECASE,
    ))
    explicit_topic_inventory = bool(re.search(
        r"(?:последн\w*\s+тем\w*|какие\s+тем\w*|список\s+тем\w*|"
        r"тем\w*.{0,28}(?:из\s+истори\w*|мы\s+обсужда\w*|мы\s+говорил\w*)|"
        r"(?:покаж\w*|перечисл\w*|вывед\w*|напомн\w*|найт\w*|найд\w*|ищ\w*|search|find|locate|list|show|summariz\w*).{0,36}"
        r"(?:тем\w*|topics?|history|conversations?))",
        low, re.IGNORECASE,
    ))
    # Identify an unnamed time-scoped overview separately from a lookup for a
    # particular subject. Strip discourse/time words first, so "physics ... 2h ago"
    # remains targeted while "what did we discuss 2h ago" becomes an inventory.
    subject_probe = low
    subject_probe = re.sub(
        r"\b(?:\d{1,3}\s*(?:секунд\w*|сек\.?|минут\w*|мин\.?|час\w*|годин\w*|дн\w*|доба\w*|день|дня|дней|days?|hours?|hrs?|minutes?|mins?|seconds?)\s+назад|"
        r"(?:хоть\s+|около\s+|примерно\s+|в\s+районе\s+)?час(?:а)?\s+назад|пол\s*часа\s+назад|"
        r"за\s+последн\w*\s+\d+\s*(?:час\w*|минут\w*|дн\w*)|"
        r"последн\w*\s+тем\w*|какие\s+тем\w*|список\s+тем\w*)\b",
        " ", subject_probe, flags=re.IGNORECASE,
    )
    generic_history_words = {
        "о", "об", "чем", "чём", "что", "мы", "наш", "наши", "нас", "нам", "говорили", "говорил",
        "обсуждали", "обсуждали", "разговаривали", "помнишь", "помниш", "помним", "помни", "вспомни",
        "напомни", "напомнить", "последние", "последних", "тема", "темы", "тему", "тем", "тематик",
        "история", "истории", "историю", "истории", "диалог", "диалога", "диалоге", "разговор", "разговора",
        "час", "часа", "часов", "минут", "минуты", "минуту", "дней", "дня", "день", "назад", "хоть",
        "примерно", "около", "последний", "последнюю", "последнего", "сейчас", "сегодня", "вчера",
        "утра", "утром", "ранку", "вечера", "вечером", "вечора", "дня", "днем", "днём", "ночью", "ночі",
        "найти", "найди", "ищи", "можешь", "пожалуйста", "темы", "диалоги", "разговоры",
        "последн", "только", "покажи", "показать", "выведи", "перечисли", "напомни", "дай", "мне",
        "the", "what", "were", "we", "did", "do", "our", "about", "talking", "talked", "discuss", "discussed",
        "conversation", "conversations", "history", "topic", "topics", "list", "show", "me", "last", "hour", "hours", "ago",
    }
    subject_tokens = [token for token in re.findall(r"[\w\u0080-\uffff]+", subject_probe.lower())
                      if len(token) > 2 and token not in generic_history_words and not token.isdigit()]
    time_scoped_overview = bool(
        has_explicit_time_window and history_reference_words and not subject_tokens
    )
    history_inventory_request = bool(explicit_topic_inventory or time_scoped_overview)

    self_reference = bool(token_set & {"мы", "нас", "нам", "наш", "наша", "наши", "наше", "we", "our", "us"}) or any(
        token.startswith(("наш", "наша", "наши")) for token in tokens
    )
    # “с тобой” is a dialog reference, but do not let any generic preposition “с” trigger it.
    self_reference = self_reference or ("тобой" in token_set and "с" in token_set)
    self_reference = self_reference or bool(token_set & {"будем", "будете", "планируем", "собираемся", "we'll", "lets"})
    interrogative = bool(token_set & {"что", "чем", "чего", "какие", "какая", "какой", "кто", "где", "когда", "почему", "как", "зачем", "which", "what", "who", "where", "when", "why", "how"}) or "?" in source or "？" in source
    imperative_recall = bool(token_set & {"напомни", "вспомни", "перечисли", "перескажи", "восстанови", "найди", "вернись", "покажи", "remind", "recall", "remember", "summarize"})
    temporal_past = past_reference or today_reference or recent_reference or bool(token_set & {"вчера", "сегодня", "утром", "вечером", "yesterday", "today"})
    temporal_future = future_reference or bool(token_set & {"завтра", "будем", "буду", "будущем", "tomorrow", "will"})
    # A question about how to apply/improve the current dialogue mechanism is not
    # automatically a request to search old history. Earlier, self_reference alone
    # ("we/our") plus a dialogue/decision word was enough to set HISTORY_LOOKUP;
    # this routed operational follow-ups to the history-topic fallback when Provider
    # returned no answer. Require an actual recollection signal for these two paths.
    explicit_discussion_recall = bool(re.search(
        r"(?:\b(?:что|о\s+чем|про\s+что|какие\s+темы|какой\s+вопрос|какие\s+вопросы)\b"
        r".{0,65}\b(?:обсуждал\w*|говорил\w*|рассматривал\w*|упоминал\w*|затрагивал\w*)\b|"
        r"\b(?:что\s+было|о\s+чем\s+мы\s+говорили|what\s+did\s+we\s+discuss|"
        r"what\s+have\s+we\s+discussed|what\s+were\s+we\s+discussing|"
        r"what\s+did\s+we\s+talk\s+about|what\s+were\s+we\s+talking|"
        r"what\s+happened\s+in\s+our\s+conversation)\b)",
        low, re.IGNORECASE,
    ))
    explicit_prior_decision_recall = bool(re.search(
        r"\b(?:что|какое|какие|к\s+чему)\b.{0,55}\b"
        r"(?:решил\w*|договорил\w*|выбрал\w*|принял\w*|постановил\w*|согласовал\w*|пришл\w*)\b|"
        r"\b(?:предыдущ\w*|прошл\w*|раньше|ранее|до\s+этого|в\s+прошлый\s+раз)\b.{0,45}\b"
        r"(?:решени\w*|вывод\w*|выбор\w*|договоренност\w*|договорённост\w*)\b|"
        r"\b(?:what|which)\b.{0,65}\b(?:did\s+we\s+(?:decid\w*|agree\w*|choos\w*|select\w*|conclud\w*|settle\w*|make)|"
        r"have\s+we\s+(?:decid\w*|agree\w*|chosen|selected|conclud\w*)|"
        r"we\s+(?:decid\w*|agree\w*|chose|selected|conclud\w*))\b|"
        r"\b(?:previous|prior|earlier|last)\s+(?:decision|conclusion|choice)\b",
        low, re.IGNORECASE,
    ))
    explicit_dialogue_recall = bool(
        explicit_discussion_recall
        or (self_reference and (temporal_past or recall_action))
        or any(term in low for term in (
            "что обсуждали", "что было в диалоге", "что было в разговоре",
            "what did we discuss", "what were we talking", "what happened in our conversation",
        ))
    )
    explicit_discussion_question = dialogue_action and interrogative and explicit_dialogue_recall
    decision_recall = (decision_action or explicit_prior_decision_recall) and (interrogative or recall_action or explicit_prior_decision_recall) and (
        recall_action or temporal_past or explicit_prior_decision_recall
    )
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
        # Inventory requests are history retrieval even when they omit “remember”,
        # “we discussed”, or another fixed recall marker: e.g. “list topics from
        # 14:00 to 16:00” or “show 5–10 conversations from the last 4 hours”.
        or history_inventory_request
    ) and not future_topic_question

    context_dependent_question = (
        _looks_like_context_dependent_question(
            source, interrogative=interrogative,
            explicit_topic_introduction=explicit_topic_introduction,
        )
        or (
            _looks_like_next_step_followup(source)
            and not explicit_topic_introduction
        )
    )
    topic_reference_fragment = _looks_like_topic_reference_fragment(
        source, explicit_topic_introduction=explicit_topic_introduction,
    )
    dialogue_act_profile = _infer_dialogue_act_profile(
        source,
        interrogative=interrogative,
        context_dependent_question=context_dependent_question,
        answer_followup=answer_followup,
        continuation_action=continuation_action,
        explicit_topic_introduction=explicit_topic_introduction,
        topic_reference_fragment=topic_reference_fragment,
    )
    context_dependent_reaction = bool(dialogue_act_profile.get("context_dependent_reaction"))
    active_branch_repair = bool(dialogue_act_profile.get("active_branch_repair"))
    previous_answer_reference = bool(dialogue_act_profile.get("previous_answer_reference"))
    factual_verification_request = bool(dialogue_act_profile.get("factual_verification_request"))

    if explicit_topic_switch and not history_recall:
        # Explicitly changing branch overrides reaction/anaphora cues in the same
        # wording. The state manager may still retrieve evidence, but must not keep
        # the current hot branch active merely because an earlier answer is named.
        primary_intent = "NEW_INFORMATION"
        direction = "ANSWER_NEW_REQUEST"
        topic_reference = "UNSPECIFIED"
        time_scope = "UNSPECIFIED"
        requires_memory = False
        history_request = False
        search_scope = "CURRENT_DIALOGUE"
        intent_score = 0
        relation_hint = "NEW"
        reason = "explicit_topic_switch"
    elif history_recall and (not active_branch_repair or history_reference_words or history_inventory_request or has_explicit_time_window or today_reference or recent_reference):
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
        elif history_inventory_request or any(term in low for term in ("кратко", "содержание", "перечисли", "какие темы", "список тем", "summarize", "list topics")):
            primary_intent = "HISTORY_SUMMARY"
            direction = "SEARCH_AND_SUMMARIZE_HISTORY"
            topic_reference = "DIALOGUE_HISTORY"
            reason = "time_bounded_topic_inventory" if history_inventory_request else "summary_or_topic_list_requested"
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
        time_scope = (
            "EXPLICIT_TIME_WINDOW" if has_explicit_time_window else
            ("TODAY" if today_reference else ("RECENT_WINDOW" if recent_reference else ("PAST_DIALOGUE" if past_reference else ("FUTURE_PLAN_CONTEXT" if temporal_future else "AVAILABLE_HISTORY"))))
        )
    elif context_dependent_reaction or topic_reference_fragment:
        # Reactions and terse topic pointers request a memory-assisted interpretation.
        # The state manager must still verify a real match; this is not a forced relation.
        primary_intent = "TOPIC_CONTINUATION"
        direction = "SEARCH_ACTIVE_OR_REFERENCED_TOPIC"
        topic_reference = "TOPIC_FRAGMENT" if topic_reference_fragment else "PREVIOUS_OR_ACTIVE_TOPIC"
        time_scope = "ACTIVE_DIALOGUE"
        requires_memory = True
        history_request = False
        search_scope = "TOPIC_OR_ACTIVE_CONTEXT"
        intent_score = 4 if topic_reference_fragment else 3
        relation_hint = "CONTINUE"
        reason = (
            "short_topic_pointer_requires_history_match" if topic_reference_fragment
            else "active_branch_previous_answer_recheck" if active_branch_repair
            else "context_dependent_reaction_to_previous_response"
        )
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
    elif (continuation_action or (any(token in token_set for token in {
        "это", "этого", "этой", "этом", "эти", "этих", "этими", "этим",
        "тот", "та", "ту", "те", "тех", "такие", "таких", "такими",
        "там", "дальше", "прежнему", "прежней", "ранее", "предыдущий",
    }) and not temporal_future)) and not explicit_topic_introduction:
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
        "topic_reference_fragment": bool(topic_reference_fragment),
        "previous_answer_reference": bool(previous_answer_reference),
        "active_branch_repair": bool(active_branch_repair),
        "factual_verification_request": bool(factual_verification_request),
        "explicit_topic_switch": bool(explicit_topic_switch),
        "self_reference": bool(self_reference),
        "past_reference": bool(past_reference),
        "today_reference": bool(today_reference),
        "recent_reference": bool(recent_reference),
        "future_reference": bool(temporal_future),
        "interrogative": bool(interrogative),
    }
    return {
        "schema": "april_request_semantics_v1",
        "primary_intent": primary_intent,
        "direction": direction,
        "time_scope": time_scope,
        "time_window": time_window,
        "has_explicit_time_window": has_explicit_time_window,
        "requested_topic_count": requested_topic_count,
        "minimum_topic_count": minimum_topic_count,
        "history_inventory_request": history_inventory_request,
        "topic_reference": topic_reference,
        "requires_memory": bool(requires_memory),
        "history_request": bool(history_request),
        "search_scope": search_scope,
        "relation_hint": relation_hint,
        "intent_score": int(intent_score),
        "speech_act": dialogue_act_profile.get("speech_act"),
        "communicative_act": dialogue_act_profile.get("communicative_act"),
        "previous_answer_reference": bool(previous_answer_reference),
        "active_branch_repair": bool(active_branch_repair),
        "factual_verification_request": bool(factual_verification_request),
        "explicit_topic_switch": bool(explicit_topic_switch),
        "pragmatic_intent": dialogue_act_profile.get("pragmatic_intent"),
        "message_function": dialogue_act_profile.get("message_function"),
        "pragmatic_features": dialogue_act_profile.get("pragmatic_features", {}),
        "tone": dialogue_act_profile.get("tone", "NEUTRAL"),
        "recommended_response_action": dialogue_act_profile.get("recommended_response_action", "ANSWER_NORMALLY"),
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
    """Return the upper bound for list requests such as “от 5 до 10 тем”."""
    _, maximum = extract_topic_count_bounds(text, default=10)
    return max(1, min(10, int(maximum or 10)))


def _history_count_minimum(text: str) -> int:
    minimum, _ = extract_topic_count_bounds(text, default=10)
    return max(1, min(10, int(minimum or 5)))


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
    contextual_history_match = bool(memory.get("contextual_history_match"))
    pairs = memory.get("selected_pairs")
    # HISTORY_RECALL and named-topic semantic matches can both remain relation=NEW.
    # Relation controls active-topic state, not whether grounded user history can be
    # attached to answer this request.
    if (relation != "CONTINUE" and not history_request and not contextual_history_match) or not isinstance(pairs, list):
        return []
    limit = 6 if history_request else 2
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

    # A recognized multi-render presentation (for example formulas + biography +
    # experiment illustrations + sources + a final portrait) is one user task.
    # Keep its coordinated clauses together so dependent phrases are not sent to
    # State Manager as fake standalone questions. All other requests retain the
    # established conjunction-based question splitting.
    presentation_bundle = len(build_presentation_sequence(source)) >= 2

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
        conjunction_boundary = "" if presentation_bundle else (
            r"|\s+(?:и|а также|а|and|also)\s+(?=" + question_lead + r"\b)"
        )
        boundary_pattern = re.compile(
            # In a multi-render presentation, clauses like "ссылки на ресурсы с
            # описанием, куда они ведут и что объясняют" remain in one request.
            r"(?<=[?？])\s+|(?<=[.!])\s+(?=" + _TASK_OR_QUESTION_START + r")"
            + conjunction_boundary,
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
    # Modal openers (“Можешь…”, “Можно…”, ASR typo “Можес…”, “Could you…”) are
    # the beginning of the following task, not independent tasks. Merge them before
    # semantic search so one user sentence performs one memory lookup rather than
    # burning time on an empty-prefix search.
    if len(cleaned) > 1 and re.fullmatch(
        r"(?:можешь|можете|можес|может|можно|сможешь|сможете|пожалуйста|давай|давайте|окей|okay|"
        r"could\s+you|can\s+you|please)[,.!?…\s]*",
        cleaned[0], flags=re.IGNORECASE,
    ):
        cleaned = [f"{cleaned[0].strip(' ,.!?…')} {cleaned[1]}".strip()] + cleaned[2:]
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


def build_presentation_sequence(text: str) -> list[dict[str, Any]]:
    """Create an ordered deliverable manifest for a single multi-part Premium answer.

    This is a presentation plan, not a set of independent dialogue-memory searches.
    It preserves requested sections/renderers and moves an explicitly requested
    final portrait/image to the final slot.
    """
    source = _text(text)
    low = source.lower().replace("ё", "е")
    if not source:
        return []

    candidates: list[dict[str, Any]] = []
    detectors = [
        ("formulas", r"(?:формул\w*|уравнен\w*|formula\w*|equation\w*)", ["text", "formula"]),
        ("biography", r"(?:истори\w*\s+(?:его\s+|ее\s+|её\s+)?жизн\w*|биограф\w*|history\s+of\s+(?:his|her|their)\s+life|biography)", ["text"]),
        ("experiments", r"(?:опыт\w*|эксперимент\w*|experiment\w*)", ["text", "diagram"]),
        ("resources", r"(?:ссылк\w*|ресурс\w*|источник\w*|website\w*|resource\w*|source\w*|\burls?\b|\blinks?\b)", ["text", "link"]),
    ]
    for section, pattern, output_types in detectors:
        match = re.search(pattern, low, re.IGNORECASE)
        if match:
            candidates.append({
                "section": section,
                "title": {
                    "formulas": "Формулы и пояснения",
                    "biography": "История жизни",
                    "experiments": "Иллюстрации опытов",
                    "resources": "Ресурсы и ссылки",
                }[section],
                "source_position": match.start(),
                "output_types": output_types,
                "final_output": False,
            })

    final_portrait = bool(re.search(
        r"(?:в\s+конце|напоследок|в\s+завершени\w*|at\s+the\s+end|finally)"
        r"[\s\S]{0,140}?(?:покаж\w*|изобраз\w*|представ\w*|show|display|present)"
        r"[\s\S]{0,90}?(?:изображени\w*|картинк\w*|портрет\w*|фото\b|image\w*|picture\w*|portrait\w*)",
        low, re.IGNORECASE,
    ))
    if final_portrait:
        candidates.append({
            "section": "final_portrait",
            "title": "Итоговый портрет",
            "source_position": len(source) + 1,
            "output_types": ["image"],
            "final_output": True,
        })

    candidates.sort(key=lambda item: (bool(item.get("final_output")), int(item.get("source_position") or 0)))
    if len(candidates) <= 1:
        return []
    sequence = []
    for index, item in enumerate(candidates, start=1):
        sequence.append({
            "step_index": index,
            "section": item["section"],
            "title": item["title"],
            "output_types": list(item["output_types"]),
            "final_output": bool(item["final_output"]),
        })
    return sequence


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
    parent_pragmatic = parent.get("pragmatic_features") if isinstance(parent.get("pragmatic_features"), dict) else {}
    parent_explicit_topic_switch = bool(parent.get("explicit_topic_switch") or _has_explicit_topic_switch(text))
    parent_repair = bool(
        not parent_explicit_topic_switch
        and (parent.get("active_branch_repair") or parent_pragmatic.get("active_branch_repair"))
    )
    parent_outputs = _enhance_requested_outputs(text, _detect_requested_outputs(text))
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
        # When a single turn is split into clauses, an ellipsis such as "his photo
        # and the table is ugly—make it prettier" can leave the visual noun in one
        # child and the operation in the next. Bind the turn-level renderer intent to
        # the child that actually names that visual object; do not attach it to a
        # generic style-only child such as "make it prettier".
        item_low = item.lower().replace("ё", "е")
        output_object_patterns = {
            "image": r"(?:фотк\w*|фото\b|фотограф\w*|снимк\w*|картинк\w*|изображени\w*|иллюстрац\w*|\bphoto\w*|\bimage\w*|\bpicture\w*)",
            "table": r"(?:таблиц\w*|\btable\b)",
            "graph": r"(?:график\w*|диаграмм\w*|\bgraph\b|\bchart\b|\bplot\b)",
            "diagram": r"(?:схем\w*|чертеж\w*|диаграмм\w*|\bdiagram\b|\bflowchart\b|\bschematic\b)",
            "formula": r"(?:формул\w*|уравнен\w*|\bformula\b|\bequation\b|\blatex\b)",
            "code": r"(?:код\w*|скрипт\w*|\bcode\b|\bscript\b)",
            "link": r"(?:ссылк\w*|\blink\b|\burl\b)",
            "file": r"(?:файл\w*|документ\w*|\bfile\b|\bdocument\b)",
        }
        for parent_output in parent_outputs:
            pattern = output_object_patterns.get(parent_output)
            if pattern and parent_output not in outputs and re.search(pattern, item_low, flags=re.IGNORECASE):
                outputs.append(parent_output)
        if "text" not in outputs:
            outputs.insert(0, "text")
        item_semantics = interpret_request_semantics(item)
        if parent_explicit_topic_switch:
            item_semantics["explicit_topic_switch"] = True
            item_semantics["active_branch_repair"] = False
            item_semantics.setdefault("features", {})["active_branch_repair"] = False
            item_semantics["features"]["explicit_topic_switch"] = True
            item_semantics.setdefault("pragmatic_features", {})["active_branch_repair"] = False
        repair_linked_clause = bool(
            parent_repair
            and not _has_explicit_topic_introduction(item)
            and (
                _detect_previous_answer_recheck(item)
                or _is_repair_followup_clause(item)
            )
        )
        if repair_linked_clause:
            child_pragmatic = item_semantics.get("pragmatic_features") if isinstance(item_semantics.get("pragmatic_features"), dict) else {}
            child_features = item_semantics.get("features") if isinstance(item_semantics.get("features"), dict) else {}
            item_semantics.update({
                "primary_intent": "TOPIC_CONTINUATION",
                "direction": "SEARCH_ACTIVE_OR_REFERENCED_TOPIC",
                "topic_reference": "PREVIOUS_ASSISTANT_ANSWER",
                "time_scope": "ACTIVE_DIALOGUE",
                "requires_memory": True,
                "history_request": False,
                "search_scope": "TOPIC_OR_ACTIVE_CONTEXT",
                "relation_hint": "CONTINUE",
                "reason": "repair_clause_inherits_active_branch",
                "speech_act": item_semantics.get("speech_act") or "CORRECTION_OR_REVISION",
                "communicative_act": "REVISE_PREVIOUS_RESPONSE",
                "pragmatic_intent": "correction_or_revision",
                "message_function": "revise_previous_response",
                "tone": "CORRECTIVE",
                "recommended_response_action": "RECHECK_PREVIOUS_RESPONSE_AND_CORRECT_IF_NEEDED",
                "previous_answer_reference": True,
                "active_branch_repair": True,
                "factual_verification_request": bool(
                    item_semantics.get("factual_verification_request")
                    or parent.get("factual_verification_request")
                    or parent_pragmatic.get("factual_verification_request")
                ),
                "pragmatic_features": {
                    **child_pragmatic,
                    "previous_answer_reference": True,
                    "active_branch_repair": True,
                    "factual_verification_request": bool(
                        child_pragmatic.get("factual_verification_request")
                        or parent.get("factual_verification_request")
                        or parent_pragmatic.get("factual_verification_request")
                    ),
                },
                "features": {
                    **child_features,
                    "context_dependent_reaction": True,
                    "previous_answer_reference": True,
                    "active_branch_repair": True,
                    "factual_verification_request": bool(
                        child_features.get("factual_verification_request")
                        or parent.get("factual_verification_request")
                        or parent_pragmatic.get("factual_verification_request")
                    ),
                },
                "parent_context_dependency": True,
                "parent_intent": parent.get("primary_intent", "TOPIC_CONTINUATION"),
            })
        parent_window = parent.get("time_window") if isinstance(parent.get("time_window"), dict) else {}
        if parent_window.get("has_constraint") and not (item_semantics.get("time_window") or {}).get("has_constraint"):
            item_semantics["time_window"] = parent_window
            item_semantics["has_explicit_time_window"] = True
            item_semantics["time_scope"] = parent.get("time_scope", "EXPLICIT_TIME_WINDOW")
        if parent.get("history_request") and not item_introduces_subject:
            # A decomposed clause can omit the temporal/history words that made the
            # whole request unambiguous. Preserve that parent context for dependent
            # follow-ups without forcing it onto a separately introduced new subject.
            _, inherited_tokens = _semantic_normalize(item)
            inherited_set = set(inherited_tokens)
            context_words = {
                "это", "этого", "этой", "этом", "них", "ним", "нему", "истории",
                "темы", "диалоги", "обсуждение", "список", "сводка", "выводы", "итоги",
                "topics", "history", "conversations", "summary", "them", "those", "these",
            }
            if item_semantics.get("history_request") or item_semantics.get("requires_memory") or inherited_set.intersection(context_words) or len(inherited_set) <= 5:
                item_semantics["history_request"] = True
                item_semantics["requires_memory"] = True
                item_semantics["search_scope"] = "ALL_DIALOGUE_HISTORY"
                item_semantics["relation_hint"] = "HISTORY_LOOKUP"
                item_semantics["primary_intent"] = "HISTORY_SUMMARY" if parent.get("primary_intent") == "HISTORY_SUMMARY" else item_semantics.get("primary_intent", "HISTORY_RECALL")
                item_semantics["direction"] = "SEARCH_AND_SUMMARIZE_HISTORY" if item_semantics["primary_intent"] == "HISTORY_SUMMARY" else "SEARCH_DIALOGUE_HISTORY"
                item_semantics["reason"] = "parent_history_context_inherited"
                item_semantics["requested_topic_count"] = parent.get("requested_topic_count", _history_count(text))
                item_semantics["minimum_topic_count"] = parent.get("minimum_topic_count", _history_count_minimum(text))
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
            "time_window": item_semantics.get("time_window") if isinstance(item_semantics.get("time_window"), dict) else {},
            "has_explicit_time_window": bool(item_semantics.get("has_explicit_time_window")),
            "requested_topic_count": max(1, min(10, int(item_semantics.get("requested_topic_count") or _history_count(item)))) if item_semantics.get("history_request") else 0,
            "minimum_topic_count": max(1, min(10, int(item_semantics.get("minimum_topic_count") or _history_count_minimum(item)))) if item_semantics.get("history_request") else 0,
            "topic_reference": item_semantics.get("topic_reference", "UNSPECIFIED"),
            "requires_memory": bool(item_semantics.get("requires_memory")),
            "history_request": bool(item_semantics.get("history_request")),
            "semantic_reason": item_semantics.get("reason", ""),
            "speech_act": item_semantics.get("speech_act", "STATEMENT_OR_REQUEST"),
            "communicative_act": item_semantics.get("communicative_act", "NEW_OR_STANDALONE"),
            "pragmatic_intent": item_semantics.get("pragmatic_intent", ""),
            "message_function": item_semantics.get("message_function", ""),
            "tone": item_semantics.get("tone", "NEUTRAL"),
            "recommended_response_action": item_semantics.get("recommended_response_action", "ANSWER_NORMALLY"),
            "pragmatic_features": item_semantics.get("pragmatic_features", {}),
            "features": item_semantics.get("features", {}),
            "previous_answer_reference": bool(item_semantics.get("previous_answer_reference")),
            "active_branch_repair": bool(item_semantics.get("active_branch_repair") or repair_linked_clause),
            "factual_verification_request": bool(item_semantics.get("factual_verification_request")),
            "explicit_topic_switch": bool(parent_explicit_topic_switch or item_semantics.get("explicit_topic_switch")),
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

    # Derive output requirements both from the complete user turn and from each
    # explicitly separated sub-request. This prevents an image/table/graph request
    # from disappearing when the splitter assigns it to a child clause.
    question_sequence = build_question_sequence(
        original or text,
        parent_interpretation=request_semantics,
    )
    presentation_sequence = build_presentation_sequence(original or text)
    detected_outputs = _detect_requested_outputs(original or text)
    requested_outputs = _enhance_requested_outputs(original or text, detected_outputs)
    for sequence_item in question_sequence:
        if not isinstance(sequence_item, dict):
            continue
        for output_type in sequence_item.get("output_types") or []:
            normalized_output = _text(output_type).lower()
            if normalized_output and normalized_output not in requested_outputs:
                requested_outputs.append(normalized_output)
    if "text" not in requested_outputs:
        requested_outputs.insert(0, "text")
    routing_capabilities = _infer_routing_capabilities(original or text)
    wants_image = "image" in requested_outputs
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
    history_count = max(1, min(10, int(memory.get("requested_topic_count") or request_semantics.get("requested_topic_count") or _history_count(original or text) or 10)))
    history_count_minimum = max(1, min(history_count, int(memory.get("minimum_topic_count") or request_semantics.get("minimum_topic_count") or _history_count_minimum(original or text) or min(5, history_count))))
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
            "adaptive_visual_policy": True,
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
            "history_count_minimum": history_count_minimum if history_request else 0,
            "time_window": request_semantics.get("time_window") if history_request else {},
            "semantic_intent": _text(request_semantics.get("primary_intent") or "NEW_INFORMATION"),
            "search_direction": _text(request_semantics.get("direction") or "ANSWER_NEW_REQUEST"),
            "semantic_reason": _text(request_semantics.get("reason")),
        },
        "dialogue": {
            "relation": relation,
            "is_new_dialogue": relation != "CONTINUE",
            "interaction_profile": {
                "speech_act": _text(request_semantics.get("speech_act") or "STATEMENT_OR_REQUEST"),
                "communicative_act": _text(request_semantics.get("communicative_act") or "NEW_OR_STANDALONE"),
                "tone": _text(request_semantics.get("tone") or "NEUTRAL"),
                "recommended_response_action": _text(request_semantics.get("recommended_response_action") or "ANSWER_NORMALLY"),
                "context_dependent_reaction": bool(request_semantics.get("features", {}).get("context_dependent_reaction")) if isinstance(request_semantics.get("features"), dict) else False,
                "active_branch_repair": bool(request_semantics.get("active_branch_repair")),
                "previous_answer_reference": bool(request_semantics.get("previous_answer_reference")),
                "factual_verification_request": bool(request_semantics.get("factual_verification_request")),
                "explicit_topic_switch": bool(request_semantics.get("explicit_topic_switch")),
            },
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
            "continuation_context": selected_pairs if (relation == "CONTINUE" or history_request or bool(memory.get("contextual_history_match"))) else [],
            "selected_section": dict(memory.get("selected_section") or {}),
            "clarification_needed": bool(memory.get("clarification_needed")),
            "pending_clarification": dict(memory.get("pending_clarification") or {}),
            "clarification_resolution": dict(memory.get("clarification_resolution") or {}),
            "topic_index": [dict(item) for item in (memory.get("topic_index") or []) if isinstance(item, dict)][:10],
            "asset_task_map": asset_task_map,
            "question_sequence": question_sequence,
            "presentation_sequence": presentation_sequence,
            "answer_sequence_in_order": True,
            "premium_render_budget": {
                "total_output_tokens": 12000,
                "render_payload_tokens": 4800,
                "explanation_and_answer_tokens": 7200,
                "visual_share_percent": 40,
                "text_share_percent": 60,
                "render_budget_included_in_total": True,
                "renderer_selection": "explicit_request_then_semantic_value",
                "scene_order": "interleave_explanation_and_visual_by_step_index",
            },
            "presentation_contract": {
                "mcdowell_required": True,
                "katex_required_for_math": True,
                "scene_contract_required": True,
                "single_scene_contract": True,
                "renderer_signal_source": "C_ARTIFACT_CONTRACT",
            },
            "rendering_guidance": [
                "Always preserve a complete explanatory text answer and answer every REQUEST_SEQUENCE item in order.",
                "When PRESENTATION_SEQUENCE exists, use it as the ordered checklist of deliverable sections and renderer types within this single request; it does not trigger separate memory retrievals.",
                "Interleave each section's text and typed renderer by its step_index. Keep final_output=true sections last, after every earlier section and renderer.",
                "Premium output ceiling is exactly 12000 tokens per complete answer attempt; target 7200 tokens for explanatory text (60%) and 4800 for concrete visual/render payloads (40%), both inside the same total. Do not fill the cap for its own sake.",
                "Interleave each request step's explanatory text with its own formula/table/diagram/graph/image render blocks using step_index; do not group all visuals at the end.",
                "Use a structured table for a clear comparison when the answer has comparable attributes. A table payload must contain real headers/columns and at least one populated row; do not emit empty TableBlock shells or put a whole list of values into one cell when each item can be a row/cell.",
                "For composite requests, preserve every requested output independently (for example, table AND photograph/image); never treat one renderer as replacing another.",
                "For substantial explanations, choose a useful additional table, diagram, graph, formula, code block, grounded link, or image when it materially improves understanding; never invent data or label a generated illustration as an authentic photograph.",
                "Use a diagram only for explicit schema/diagram/blueprint/technical-drawing intent or workflows/architecture/sequences. Ordinary requests to draw/create/show a picture or illustration must use C_APRIL_IMAGES_GENERATOR (Images 2.0), unless the request explicitly asks for a diagram, blueprint, technical drawing, or graph. Emit a concrete payload.svg, drawing elements, geometry, or nodes/edges; do not only describe the intended drawing.",
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
            "semantic_interpretation_version": "april_request_semantics_v4_active_branch_repair",
            "dialogue_communication": {
                "principle": "Respond to the user's conversational move, not only to the literal words.",
                "speech_act": _text(request_semantics.get("speech_act") or "STATEMENT_OR_REQUEST"),
                "communicative_act": _text(request_semantics.get("communicative_act") or "NEW_OR_STANDALONE"),
                "tone": _text(request_semantics.get("tone") or "NEUTRAL"),
                "recommended_response_action": _text(request_semantics.get("recommended_response_action") or "ANSWER_NORMALLY"),
                "active_branch_repair": bool(request_semantics.get("active_branch_repair")),
                "previous_answer_reference": bool(request_semantics.get("previous_answer_reference")),
                "factual_verification_request": bool(request_semantics.get("factual_verification_request")),
                "explicit_topic_switch": bool(request_semantics.get("explicit_topic_switch")),
                "instructions": [
                    "When context says CONTINUE and evidence is present, continue the conversation naturally from the relevant prior point; do not restart the subject or recite internal search metadata.",
                    "Mention past discussion in ordinary conversational language only when it helps answer the user or the user asks what was discussed.",
                    "Treat gratitude and positive feedback briefly and naturally, then continue only when the user also gave a next step.",
                    "Treat disagreement, dissatisfaction, or a revision request as feedback on the previous answer when supported by context; re-check the previous answer and correct/improve it instead of defending it blindly.",
                    "When active_branch_repair or previous_answer_reference is true, compare the current challenge with the selected canonical USER↔APRIL source turns; report what April actually said separately from what should have been said, and do not advance the active task until the correction is addressed.",
                    "Use only selected dialogue-memory evidence for claims about what was previously said. If the requested time range has no entries, state that honestly and offer nearby retained entries as nearby, not as matches inside the requested range.",
                    "Before saying a prior value or answer is unavailable, inspect ACTIVE_WORK_BRANCH.last_assistant_answer, recent_steps.april_text, DIALOGUE_ANCHOR, and selected CONTINUATION_CONTEXT pairs. A value omitted from a summary is not missing when the exact assistant turn is present.",
                    "For an explicit question about what April said, named, wrote, calculated, selected, or answered, verify April's own prior output independently from whether that output was factually correct. Apply the same evidence check to the active exchange and matching past-dialogue records.",
                    "A topic pointer is a retrieval hint, not proof that a memory exists. If no matching prior record is found, answer as a new request or ask a concise clarification instead of inventing continuity.",
                ],
            },
        },
    }
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
    "build_presentation_sequence",
    "interpret_request_semantics",
    "assert_same_identity",
]


# Temporal parsing is embedded here to keep Premium logic inside existing modules.
from datetime import datetime, time as datetime_time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_DEFAULT_TIMEZONE = "Europe/Kyiv"

_WEEKDAY_NAMES = {
    "понедельник": 0, "понедельника": 0, "понедельнику": 0, "понедельнике": 0,
    "понеділок": 0, "понеділка": 0, "понеділку": 0, "monday": 0,
    "вторник": 1, "вторника": 1, "вторнику": 1, "вівторок": 1, "вівторка": 1, "вівторку": 1, "tuesday": 1,
    "среда": 2, "среду": 2, "среды": 2, "среде": 2, "середа": 2, "середу": 2, "середи": 2, "середі": 2, "wednesday": 2,
    "четверг": 3, "четверга": 3, "четвергу": 3, "четверге": 3, "четвер": 3, "четверга": 3, "четвергу": 3, "thursday": 3,
    "пятница": 4, "пятницу": 4, "пятницы": 4, "пятнице": 4, "п’ятниця": 4, "п’ятницю": 4, "пятниця": 4, "пятницю": 4, "friday": 4,
    "суббота": 5, "субботу": 5, "субботы": 5, "субботе": 5, "субота": 5, "суботу": 5, "суботи": 5, "saturday": 5,
    "воскресенье": 6, "воскресенья": 6, "воскресенью": 6, "неділя": 6, "неділю": 6, "неділі": 6, "sunday": 6,
}


def _weekday_reference(low: str) -> tuple[int, re.Match[str]] | None:
    """Return a weekday only when wording marks it as a temporal reference.

    A bare subject word like “пятницы” in a request to format a calendar is not a
    time filter. Phrases such as “в пятницу”, “за прошлую среду”, and “last Monday” are.
    """
    names = "|".join(sorted((re.escape(name) for name in _WEEKDAY_NAMES), key=len, reverse=True))
    pattern = re.compile(
        rf"\b(?:в|во|за|на|по|с|от|from|on|last|this|past|previous|"
        rf"прошл\w*|предыдущ\w*|последн\w*|эт\w*|минул\w*)"
        rf"(?:\s+(?:прошл\w*|предыдущ\w*|последн\w*|эт\w*|минул\w*|this|last|previous))?"
        rf"\s+(?P<weekday>{names})\b"
    )
    match = pattern.search(low)
    if not match:
        return None
    return _WEEKDAY_NAMES[match.group("weekday")], match


_MONTHS = {
    "января": 1, "январь": 1, "січня": 1, "січень": 1, "january": 1, "jan": 1,
    "февраля": 2, "февраль": 2, "лютого": 2, "лютий": 2, "february": 2, "feb": 2,
    "марта": 3, "март": 3, "березня": 3, "березень": 3, "march": 3, "mar": 3,
    "апреля": 4, "апрель": 4, "квітня": 4, "квітень": 4, "april": 4, "apr": 4,
    "мая": 5, "май": 5, "травня": 5, "травень": 5, "may": 5,
    "июня": 6, "июнь": 6, "червня": 6, "червень": 6, "june": 6, "jun": 6,
    "июля": 7, "июль": 7, "липня": 7, "липень": 7, "july": 7, "jul": 7,
    "августа": 8, "август": 8, "серпня": 8, "серпень": 8, "august": 8, "aug": 8,
    "сентября": 9, "сентябрь": 9, "вересня": 9, "вересень": 9, "september": 9, "sep": 9,
    "октября": 10, "октябрь": 10, "жовтня": 10, "жовтень": 10, "october": 10, "oct": 10,
    "ноября": 11, "ноябрь": 11, "листопада": 11, "листопад": 11, "november": 11, "nov": 11,
    "декабря": 12, "декабрь": 12, "грудня": 12, "грудень": 12, "december": 12, "dec": 12,
}


def _tz(name: str | None = None):
    try:
        return ZoneInfo(name or _DEFAULT_TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError):
        return timezone.utc


def _reference_local(reference_ts: float | int | None, timezone_name: str | None) -> datetime:
    zone = _tz(timezone_name)
    if reference_ts is None:
        return datetime.now(zone)
    return datetime.fromtimestamp(float(reference_ts), tz=zone)


def _local_epoch(value: datetime) -> float:
    return value.astimezone(timezone.utc).timestamp()


def _result(start: datetime, end: datetime, *, source: str, timezone_name: str | None,
            reference: datetime) -> dict[str, Any]:
    zone = _tz(timezone_name)
    if start.tzinfo is None:
        start = start.replace(tzinfo=zone)
    if end.tzinfo is None:
        end = end.replace(tzinfo=zone)
    start_utc = start.astimezone(timezone.utc)
    end_utc = end.astimezone(timezone.utc)
    if end_utc < start_utc:
        return _empty(timezone_name, reference)
    return {
        "has_constraint": True,
        "start_at": start_utc.timestamp(),
        "end_at": end_utc.timestamp(),
        "start_utc": start_utc.isoformat(),
        "end_utc": end_utc.isoformat(),
        "start_local": start.astimezone(zone).isoformat(),
        "end_local": end.astimezone(zone).isoformat(),
        "timezone": getattr(zone, "key", "UTC"),
        "source": source,
        "label": f"{start.astimezone(zone).strftime('%Y-%m-%d %H:%M')} — {end.astimezone(zone).strftime('%Y-%m-%d %H:%M')}",
        "reference_at": _local_epoch(reference),
    }


def _empty(timezone_name: str | None, reference: datetime) -> dict[str, Any]:
    zone = _tz(timezone_name)
    return {
        "has_constraint": False,
        "start_at": None,
        "end_at": None,
        "start_utc": "",
        "end_utc": "",
        "start_local": "",
        "end_local": "",
        "timezone": getattr(zone, "key", "UTC"),
        "source": "none",
        "label": "",
        "reference_at": _local_epoch(reference),
    }


def _parse_date(value: str, reference: datetime) -> datetime | None:
    raw = value.strip().lower().replace("ё", "е")
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%y", "%d/%m/%y"):
        try:
            d = datetime.strptime(raw, fmt).date()
            return datetime.combine(d, datetime_time.min, tzinfo=reference.tzinfo)
        except ValueError:
            continue
    # Day/month without a year uses the reference year; a year boundary is fixed
    # by the range parser if the resulting end precedes the start.
    for fmt in ("%d.%m", "%d/%m", "%d-%m"):
        try:
            d = datetime.strptime(raw, fmt).date().replace(year=reference.year)
            return datetime.combine(d, datetime_time.min, tzinfo=reference.tzinfo)
        except ValueError:
            continue
    return None


def _relative_clock_date(low: str, reference: datetime, zone: Any) -> datetime.date:
    """Resolve a date modifier used alongside a clock range or a single clock."""
    if re.search(r"\b(?:позавчера|the day before yesterday)\b", low):
        return (reference - timedelta(days=2)).date()
    if re.search(r"\b(?:вчера|yesterday)\b", low):
        return (reference - timedelta(days=1)).date()
    if re.search(r"\b(?:сегодня|today)\b", low):
        return reference.date()
    weekday = _weekday_reference(low)
    if weekday is not None:
        named_weekday, _ = weekday
        days_back = (reference.weekday() - named_weekday) % 7
        if days_back == 0 and re.search(r"\b(?:прошл\w*|предыдущ\w*|last|previous)\b", low):
            days_back = 7
        return (reference - timedelta(days=days_back)).date()
    return reference.date()


def extract_temporal_window(
    text: Any,
    *,
    reference_ts: float | int | None = None,
    timezone_name: str | None = None,
) -> dict[str, Any]:
    """Parse explicit time/date bounds from a user request.

    Supported examples include “за последние 3 часа”, “с 14:00 до 16:30”,
    “между 9 и 11 часами”, “вчера утром”, “с 14.10.2026 по 15.10.2026”,
    “с 14 по 15 октября”, “сегодня”, and weekday references. Unspecified time means
    no temporal filter; callers must not interpret that as an empty interval.
    """
    source_text = str(text or "").strip()
    low = re.sub(r"\s+", " ", source_text.lower().replace("ё", "е").replace("’", "'").replace("ʼ", "'")).strip()
    reference = _reference_local(reference_ts, timezone_name)
    zone = _tz(timezone_name)
    if not low:
        return _empty(timezone_name, reference)

    ago = re.search(
        r"\b(\d{1,3})\s*(секунд\w*|сек\.?|минут\w*|мин\.?|час\w*|годин\w*|дн\w*|доба\w*|день|дня|дней|days?|hours?|hrs?|minutes?|mins?|seconds?)\s+назад\b",
        low,
    )
    if ago:
        amount, unit = max(1, int(ago.group(1))), ago.group(2)
        delta = timedelta(seconds=amount) if unit.startswith(("сек", "second", "sec")) else timedelta(minutes=amount) if unit.startswith(("мин", "minute", "min")) else timedelta(hours=amount) if unit.startswith(("час", "годин", "hour", "hr")) else timedelta(days=amount)
        # "N hours ago" names a point in time, not the full interval from then
        # until now. Search a small neighborhood around that point. Rolling
        # phrases such as "last N hours" are handled by the separate duration rule.
        center = reference - delta
        radius = timedelta(minutes=10) if unit.startswith(("сек", "second", "sec", "мин", "minute", "min")) else timedelta(minutes=30) if unit.startswith(("час", "годин", "hour", "hr")) else timedelta(minutes=90)
        return _result(center - radius, center + radius, source="relative_ago_point", timezone_name=timezone_name, reference=reference)

    # Common conversational equivalents: "an hour ago", "two hours ago",
    # including filler words and spelled-out Russian numerals.
    if re.search(r"\bпол\s*часа\s+назад\b", low):
        center = reference - timedelta(minutes=30)
        return _result(center - timedelta(minutes=15), center + timedelta(minutes=15), source="relative_ago_point", timezone_name=timezone_name, reference=reference)
    word_ago = re.search(
        r"\b(один|одна|одно|одну|два|две|двух|три|тр[её]х|четыре|четыр[её]х|"
        r"пять|пяти|шесть|шести|семь|семи|восемь|восьми|девять|девяти|десять|десяти)\s+"
        r"(час\w*|годин\w*|hour\w*|hr\w*|минут\w*|minute\w*|min\w*|день|дня|дней|дн\w*)\s+назад\b",
        low,
    )
    if word_ago:
        number_words = {
            "один": 1, "одна": 1, "одно": 1, "одну": 1, "два": 2, "две": 2, "двух": 2,
            "три": 3, "трех": 3, "трёх": 3, "четыре": 4, "четырех": 4, "четырёх": 4,
            "пять": 5, "пяти": 5, "шесть": 6, "шести": 6, "семь": 7, "семи": 7,
            "восемь": 8, "восьми": 8, "девять": 9, "девяти": 9, "десять": 10, "десяти": 10,
        }
        amount = number_words.get(word_ago.group(1), 1)
        unit = word_ago.group(2)
        delta = timedelta(minutes=amount) if unit.startswith(("минут", "minute", "min")) else timedelta(days=amount) if unit.startswith(("день", "дня", "дней", "дн")) else timedelta(hours=amount)
        center = reference - delta
        radius = timedelta(minutes=10) if unit.startswith(("минут", "minute", "min")) else timedelta(minutes=90) if unit.startswith(("день", "дня", "дней", "дн")) else timedelta(minutes=30)
        return _result(center - radius, center + radius, source="relative_ago_point", timezone_name=timezone_name, reference=reference)
    if re.search(r"\b(?:около\s+|примерно\s+|хоть\s+|в\s+районе\s+)?час(?:а)?\s+назад\b", low):
        center = reference - timedelta(hours=1)
        return _result(center - timedelta(minutes=30), center + timedelta(minutes=30), source="relative_ago_point", timezone_name=timezone_name, reference=reference)

    # Spoken-number rolling durations: “за последние пять часов”, “за три дня”.
    # Keep this separate from “пять часов назад”, which is a point-in-time query.
    word_duration = re.search(
        r"\b(?:за\s+|в\s+течение\s+(?:последн\w*\s+)?|последн\w*\s+|past\s+|last\s+)"
        r"(один|одна|одно|одну|два|две|двух|три|трех|трёх|четыре|четырех|четырёх|"
        r"пять|пяти|шесть|шести|семь|семи|восемь|восьми|девять|девяти|десять|десяти)\s+"
        r"(секунд\w*|минут\w*|час\w*|годин\w*|дн\w*|день|дня|дней|доба\w*|days?|hours?|minutes?)\b",
        low,
    )
    if word_duration:
        number_words = {
            "один": 1, "одна": 1, "одно": 1, "одну": 1,
            "два": 2, "две": 2, "двух": 2, "три": 3, "трех": 3, "трёх": 3,
            "четыре": 4, "четырех": 4, "четырёх": 4, "пять": 5, "пяти": 5,
            "шесть": 6, "шести": 6, "семь": 7, "семи": 7, "восемь": 8,
            "восьми": 8, "девять": 9, "девяти": 9, "десять": 10, "десяти": 10,
        }
        amount = number_words[word_duration.group(1)]
        unit = word_duration.group(2)
        if unit.startswith(("секунд",)):
            delta = timedelta(seconds=amount)
        elif unit.startswith("минут") or unit.startswith("minute"):
            delta = timedelta(minutes=amount)
        elif unit.startswith(("час", "годин", "hour")):
            delta = timedelta(hours=amount)
        else:
            delta = timedelta(days=amount)
        return _result(reference - delta, reference, source="relative_duration_spoken_number", timezone_name=timezone_name, reference=reference)

    # Relative rolling durations, including intervals longer than the 24-hour
    # product retention window (the state manager intersects both windows).
    rel = re.search(
        r"\b(?:за\s+|в\s+течение\s+(?:последн\w*\s+)?|последн\w*\s+|past\s+|last\s+)"
        r"(\d{1,3})\s*(секунд\w*|сек\.?|минут\w*|мин\.?|час\w*|годин\w*|дн\w*|доба\w*|день|дня|дней|days?|hours?|hrs?|minutes?|mins?|seconds?)\b",
        low,
    )
    if rel:
        amount = max(1, int(rel.group(1)))
        unit = rel.group(2)
        if unit.startswith(("сек", "second", "sec")):
            delta = timedelta(seconds=amount)
        elif unit.startswith(("мин", "minute", "min")):
            delta = timedelta(minutes=amount)
        elif unit.startswith(("час", "годин", "hour", "hr")):
            delta = timedelta(hours=amount)
        else:
            delta = timedelta(days=amount)
        return _result(reference - delta, reference, source="relative_duration", timezone_name=timezone_name, reference=reference)
    if re.search(r"\b(?:последний час|за час|за последний час|последний 1 час|last hour|past hour)\b", low):
        return _result(reference - timedelta(hours=1), reference, source="relative_duration", timezone_name=timezone_name, reference=reference)
    if re.search(r"\b(?:полчаса|пол\s+часа|half an hour|last 30 minutes)\b", low):
        return _result(reference - timedelta(minutes=30), reference, source="relative_duration", timezone_name=timezone_name, reference=reference)

    # Natural durations without a number, and “N units ago” wording.
    named_duration = re.search(
        r"\b(?:за\s+|в\s+течение\s+|последн\w*\s+|past\s+|last\s+)?"
        r"(сутки|суток|день|дня|неделю|недели|месяц|месяца|год|года|day|week|month|year)\b",
        low,
    )
    if named_duration and re.search(r"\b(?:за|последн\w*|прошл\w*|past|last|в\s+течение)\b", low):
        unit = named_duration.group(1)
        days = 1 if unit in {"сутки", "суток", "день", "дня", "day"} else 7 if unit in {"неделю", "недели", "week"} else 30 if unit in {"месяц", "месяца", "month"} else 365
        return _result(reference - timedelta(days=days), reference, source="named_duration", timezone_name=timezone_name, reference=reference)
    if re.search(r"\b(?:с\s+начала\s+дня|с\s+начала\s+сегодня|since\s+start\s+of\s+day)\b", low):
        start = datetime.combine(reference.date(), datetime_time.min, tzinfo=zone)
        return _result(start, reference, source="day_start", timezone_name=timezone_name, reference=reference)

    # Explicit date-time bounds preserve the clock supplied on each endpoint,
    # e.g. “с 14.10.2026 15:00 до 15.10.2026 18:30”.
    date_pat = r"(?:\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?)"
    datetime_range = re.search(
        rf"\b(?:с|з|із|від|от|from)\s*({date_pat})\s+(?:в\s*)?(\d{{1,2}}):(\d{{2}})\s*"
        rf"(?:по|до|[-–—]|to|through)\s*({date_pat})\s+(?:в\s*)?(\d{{1,2}}):(\d{{2}})\b",
        low,
    )
    if datetime_range:
        start_date = _parse_date(datetime_range.group(1), reference)
        end_date = _parse_date(datetime_range.group(4), reference)
        sh, sm, eh, em = (int(datetime_range.group(i)) for i in (2, 3, 5, 6))
        if start_date and end_date and all((h <= 23 and m <= 59) for h, m in ((sh, sm), (eh, em))):
            start = datetime.combine(start_date.date(), datetime_time(sh, sm), tzinfo=zone)
            end = datetime.combine(end_date.date(), datetime_time(eh, em), tzinfo=zone)
            return _result(start, end, source="explicit_datetime_range", timezone_name=timezone_name, reference=reference)

    # Explicit ISO / numeric date ranges. End dates are inclusive; make the
    # interval's end exclusive by advancing to midnight after the final day.
    date_range = re.search(rf"\b(?:с|з|із|від|от|from)\s*({date_pat})\s*(?:по|до|[-–—]|to|through)\s*({date_pat})\b", low)
    if date_range:
        start = _parse_date(date_range.group(1), reference)
        end = _parse_date(date_range.group(2), reference)
        if start and end:
            if end < start and not re.search(r"\d{4}", date_range.group(2)):
                end = end.replace(year=end.year + 1)
            end += timedelta(days=1)
            return _result(start, end, source="explicit_date_range", timezone_name=timezone_name, reference=reference)

    # Month-name ranges allow the month to be stated on each endpoint, including
    # cross-month bounds such as “с 28 сентября по 3 октября 2026”.
    month_pattern = "|".join(sorted((re.escape(m) for m in _MONTHS), key=len, reverse=True))
    month_first_range = re.search(
        rf"\b(?:from|between)\s+({month_pattern})\s+(\d{{1,2}})(?:,?\s+(\d{{4}}))?\s+"
        rf"(?:to|through|[-–—])\s+({month_pattern})\s+(\d{{1,2}})(?:,?\s+(\d{{4}}))?\b",
        low,
    )
    if month_first_range:
        month1, day1 = _MONTHS[month_first_range.group(1)], int(month_first_range.group(2))
        month2, day2 = _MONTHS[month_first_range.group(4)], int(month_first_range.group(5))
        inferred_year = int(month_first_range.group(6) or reference.year)
        year1 = int(month_first_range.group(3) or inferred_year)
        year2 = int(month_first_range.group(6) or year1)
        try:
            start = datetime(year1, month1, day1, tzinfo=zone)
            end_start = datetime(year2, month2, day2, tzinfo=zone)
            if end_start < start and not month_first_range.group(6):
                end_start = end_start.replace(year=end_start.year + 1)
            return _result(start, end_start + timedelta(days=1), source="month_name_range", timezone_name=timezone_name, reference=reference)
        except ValueError:
            pass

    month_to_month = re.search(
        rf"\b(?:с|з|із|від|от|from)\s*(\d{{1,2}})\s+({month_pattern})(?:\s+(\d{{4}}))?\s*"
        rf"(?:по|до|[-–—]|to|through)\s*(\d{{1,2}})\s+({month_pattern})(?:\s+(\d{{4}}))?\b",
        low,
    )
    if month_to_month:
        day1, month1 = int(month_to_month.group(1)), _MONTHS[month_to_month.group(2)]
        inferred_year = int(month_to_month.group(6) or reference.year)
        year1 = int(month_to_month.group(3) or inferred_year)
        day2, month2 = int(month_to_month.group(4)), _MONTHS[month_to_month.group(5)]
        year2 = int(month_to_month.group(6) or year1)
        try:
            start = datetime(year1, month1, day1, tzinfo=zone)
            end_start = datetime(year2, month2, day2, tzinfo=zone)
            if end_start < start and not month_to_month.group(6):
                end_start = end_start.replace(year=end_start.year + 1)
            return _result(start, end_start + timedelta(days=1), source="month_name_range", timezone_name=timezone_name, reference=reference)
        except ValueError:
            pass

    # Compact Russian/English ranges: “с 14 по 15 октября [2026]”.
    month_range = re.search(
        rf"\b(?:с|з|із|від|от|from)\s*(\d{{1,2}})\s*(?:по|до|[-–—]|to|through)\s*(\d{{1,2}})\s+({month_pattern})(?:\s+(\d{{4}}))?\b",
        low,
    )
    if month_range:
        first_day, last_day = int(month_range.group(1)), int(month_range.group(2))
        month = _MONTHS[month_range.group(3)]
        year = int(month_range.group(4) or reference.year)
        try:
            start = datetime(year, month, first_day, tzinfo=zone)
            end = datetime(year, month, last_day, tzinfo=zone) + timedelta(days=1)
            if end < start and not month_range.group(4):
                start = start.replace(year=year - 1)
                end = end.replace(year=year - 1)
            return _result(start, end, source="month_name_range", timezone_name=timezone_name, reference=reference)
        except ValueError:
            pass

    # If a specific date accompanies a clock range, use that date instead of
    # silently interpreting the clock range as today.
    clock_date = _relative_clock_date(low, reference, zone)
    explicit_iso_for_clock = re.search(r"(?<!\d)(\d{4}-\d{1,2}-\d{1,2})(?!\d)", low)
    explicit_num_for_clock = re.search(r"(?<!\d)(\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?)(?!\d)", low)
    if explicit_num_for_clock and re.fullmatch(r"\d{1,2}-\d{1,2}", explicit_num_for_clock.group(1)):
        short_pair = explicit_num_for_clock.group(0)
        pair_end = explicit_num_for_clock.end()
        following = low[pair_end:pair_end + 20]
        if re.match(r"\s*(?:утра|ранку|вечера|вечора|дня|днем|ночью|ночі|час\w*|годин\w*)\b", following):
            explicit_num_for_clock = None
    explicit_month_for_clock = re.search(rf"\b(\d{{1,2}})\s+({month_pattern})(?:\s+(\d{{4}}))?\b", low)
    clock_date_start = _parse_date(explicit_iso_for_clock.group(1), reference) if explicit_iso_for_clock else (
        _parse_date(explicit_num_for_clock.group(1), reference) if explicit_num_for_clock else None
    )
    if clock_date_start is None and explicit_month_for_clock:
        try:
            clock_date_start = datetime(
                int(explicit_month_for_clock.group(3) or reference.year),
                _MONTHS[explicit_month_for_clock.group(2)], int(explicit_month_for_clock.group(1)),
                tzinfo=zone,
            )
        except ValueError:
            clock_date_start = None
    if clock_date_start is not None:
        clock_date = clock_date_start.date()

    # Clock range. Bare numeric ranges such as “от 5 до 10 тем” are not times;
    # require HH:MM, a time-of-day marker, or an hour-unit word.
    clock_range = re.search(
        r"\b(?:с|от|между|from|between)\s*(\d{1,2})(?::(\d{2}))?\s*"
        r"(?:до|по|и|[-–—]|to|and)\s*(\d{1,2})(?::(\d{2}))?",
        low,
    )
    if clock_range:
        matched = clock_range.group(0)
        after = low[clock_range.end():clock_range.end() + 30]
        before = low[max(0, clock_range.start() - 20):clock_range.start()]
        has_clock_colon = ":" in matched
        has_time_word = bool(re.search(r"\b(?:час\w*|годин\w*|утра|ранку|дня|вечера|вечор\w*|ночью|ночі|am|pm|o'clock|hours?)\b", before + " " + after))
        # A nearby word such as “темы” must not cancel a clear clock marker;
        # bare numeric ranges like “от 5 до 10 тем” still have no time word.
        if has_clock_colon or has_time_word:
            h1, m1 = int(clock_range.group(1)), int(clock_range.group(2) or 0)
            h2, m2 = int(clock_range.group(3)), int(clock_range.group(4) or 0)
            daypart_text = f"{before} {after}"
            is_pm = bool(re.search(r"\b(?:вечера|вечером|вечора|вечор\w*|дня|днем|днём|пополудни|afternoon|evening|pm)\b", daypart_text))
            is_morning = bool(re.search(r"\b(?:утра|утром|ранку|morning|am)\b", daypart_text))
            is_night = bool(re.search(r"\b(?:ночью|ночі|night)\b", daypart_text))
            if is_pm:
                h1 = h1 + 12 if 1 <= h1 <= 11 else h1
                h2 = h2 + 12 if 1 <= h2 <= 11 else h2
            elif is_morning and not is_night:
                h1 = 0 if h1 == 12 else h1
                h2 = 0 if h2 == 12 else h2
            if h1 <= 23 and h2 <= 23 and m1 <= 59 and m2 <= 59:
                start = datetime.combine(clock_date, datetime_time(h1, m1), tzinfo=zone)
                end = datetime.combine(clock_date, datetime_time(h2, m2), tzinfo=zone)
                if end <= start:
                    end += timedelta(days=1)
                return _result(start, end, source="clock_range", timezone_name=timezone_name, reference=reference)

    # A single date; date ranges were handled above so this cannot swallow one end.
    iso_date = re.search(r"(?<!\d)(\d{4}-\d{1,2}-\d{1,2})(?!\d)", low)
    numeric_date = re.search(r"(?<!\d)(\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?)(?!\d)", low)
    month_date = re.search(rf"\b(\d{{1,2}})\s+({month_pattern})(?:\s+(\d{{4}}))?\b", low)
    date_start = _parse_date(iso_date.group(1), reference) if iso_date else (_parse_date(numeric_date.group(1), reference) if numeric_date else None)
    if month_date:
        try:
            date_start = datetime(
                int(month_date.group(3) or reference.year), _MONTHS[month_date.group(2)],
                int(month_date.group(1)), tzinfo=zone,
            )
        except ValueError:
            pass
    if date_start:
        return _result(date_start, date_start + timedelta(days=1), source="explicit_date", timezone_name=timezone_name, reference=reference)

    # Weekday ranges such as “с понедельника по пятницу”. A bare weekday noun
    # elsewhere in the user request is not treated as a temporal filter.
    weekday_names = "|".join(sorted((re.escape(name) for name in _WEEKDAY_NAMES), key=len, reverse=True))
    weekday_range = re.search(
        rf"\b(?:с|от|from)\s+(?:(?:прошл\w*|предыдущ\w*|эт\w*|last|previous|this)\s+)?"
        rf"(?P<start>{weekday_names})\s+(?:по|до|[-–—]|to|through)\s+"
        rf"(?:(?:прошл\w*|предыдущ\w*|эт\w*|last|previous|this)\s+)?"
        rf"(?P<end>{weekday_names})\b",
        low,
    )
    if weekday_range:
        start_day = _WEEKDAY_NAMES[weekday_range.group("start")]
        end_day = _WEEKDAY_NAMES[weekday_range.group("end")]
        week_start = reference.date() - timedelta(days=reference.weekday())
        if re.search(r"\b(?:прошл\w*|предыдущ\w*|last|previous)\b", weekday_range.group(0)):
            week_start -= timedelta(days=7)
        start_date = week_start + timedelta(days=start_day)
        end_date = week_start + timedelta(days=end_day)
        if end_date < start_date:
            end_date += timedelta(days=7)
        start = datetime.combine(start_date, datetime_time.min, tzinfo=zone)
        end = datetime.combine(end_date + timedelta(days=1), datetime_time.min, tzinfo=zone)
        return _result(start, end, source="weekday_range", timezone_name=timezone_name, reference=reference)

    # Day-relative expressions, with optional part-of-day restrictions.
    day_offset = 0
    if re.search(r"\b(?:позавчера|the day before yesterday)\b", low):
        day_offset = -2
    elif re.search(r"\b(?:вчера|yesterday)\b", low):
        day_offset = -1
    elif re.search(r"\b(?:сегодня|сегодняшн\w*|today)\b", low):
        day_offset = 0
    else:
        # Weekday names mean the most recent matching local day (today if named
        # weekday equals today), which is useful for “what did we discuss Monday?”.
        weekday_match = _weekday_reference(low)
        if weekday_match is not None:
            weekday, _ = weekday_match
            days_back = (reference.weekday() - weekday) % 7
            if days_back == 0 and re.search(r"\b(?:прошл\w*|предыдущ\w*|last|previous)\b", low):
                days_back = 7
            day_offset = -days_back
        else:
            day_offset = None

    if day_offset is not None:
        day = (reference + timedelta(days=day_offset)).date()
        start = datetime.combine(day, datetime_time.min, tzinfo=zone)
        end = start + timedelta(days=1)
        part = None
        if re.search(r"\b(?:утром|утра|ранку|morning|morning time)\b", low):
            part = (5, 12)
        elif re.search(r"\b(?:днем|днём|дня|пополудни|afternoon|noon)\b", low):
            part = (12, 17)
        elif re.search(r"\b(?:вечером|вечера|вечор\w*|evening)\b", low):
            part = (17, 22)
        elif re.search(r"\b(?:ночью|ночі|ночью|night|overnight)\b", low):
            start = datetime.combine(day, datetime_time(22, 0), tzinfo=zone)
            end = start + timedelta(hours=7)
            return _result(start, end, source="day_part", timezone_name=timezone_name, reference=reference)
        if part:
            start = datetime.combine(day, datetime_time(part[0], 0), tzinfo=zone)
            end = datetime.combine(day, datetime_time(part[1], 0), tzinfo=zone)
            return _result(start, end, source="day_part", timezone_name=timezone_name, reference=reference)
        # Bare yesterday/today/weekday bounds are whole local days.
        if day_offset != 0 or re.search(r"\b(?:сегодня|today)\b", low):
            return _result(start, end, source="relative_day", timezone_name=timezone_name, reference=reference)

    # Explicit clock plus approximate language, without a range.
    single_clock = re.search(r"\b(?:в|около|around|at)\s*(\d{1,2}):(\d{2})\b", low)
    if single_clock:
        h, m = int(single_clock.group(1)), int(single_clock.group(2))
        if h <= 23 and m <= 59:
            centre = datetime.combine(clock_date, datetime_time(h, m), tzinfo=zone)
            return _result(centre - timedelta(minutes=30), centre + timedelta(minutes=30), source="approximate_clock", timezone_name=timezone_name, reference=reference)

    return _empty(timezone_name, reference)


def intersect_retention_window(window: dict[str, Any], *, now_ts: float, retention_seconds: int) -> dict[str, Any]:
    """Intersect a parsed range with the product's retained-memory interval."""
    if not isinstance(window, dict) or not window.get("has_constraint"):
        return {"applied": False, "empty": False, "start_at": None, "end_at": None, "source": "none"}
    try:
        start = float(window["start_at"])
        end = float(window["end_at"])
    except (KeyError, TypeError, ValueError):
        return {"applied": False, "empty": False, "start_at": None, "end_at": None, "source": "invalid"}
    clipped_start = max(start, float(now_ts) - max(1, int(retention_seconds)))
    clipped_end = min(end, float(now_ts))
    return {
        "applied": True,
        "empty": clipped_end <= clipped_start,
        "start_at": clipped_start,
        "end_at": clipped_end,
        "source": str(window.get("source") or "explicit"),
        "label": str(window.get("label") or ""),
        "timezone": str(window.get("timezone") or _DEFAULT_TIMEZONE),
        "requested_start_at": start,
        "requested_end_at": end,
    }

_TOPIC_NUMBER_WORDS = {
    "один": 1, "одну": 1, "одна": 1, "одного": 1,
    "два": 2, "две": 2, "двух": 2,
    "три": 3, "трех": 3, "трёх": 3,
    "четыре": 4, "четырех": 4, "четырёх": 4,
    "пять": 5, "пяти": 5, "шесть": 6, "шести": 6,
    "семь": 7, "семи": 7, "восемь": 8, "восьми": 8,
    "девять": 9, "девяти": 9, "десять": 10, "десяти": 10,
}


def extract_topic_count_bounds(text: Any, default: int = 10) -> tuple[int, int]:
    """Return (minimum, maximum) requested history topic count, clamped to 1–10."""
    low = re.sub(r"\s+", " ", str(text or "").lower().replace("ё", "е")).strip()
    topic_word = r"(?:тем\w*|топик\w*|диалог\w*|разговор\w*|topic\w*|conversation\w*)"
    # A numeric range is accepted only when it clearly modifies a topic/record count,
    # so date ranges and time ranges cannot be mistaken for “5–10 topics”.
    numeric_range = re.search(
        rf"\b(?:(?:от|from)\s*)?(\d{{1,2}})\s*(?:до|to|[-–—]|и|and)\s*(\d{{1,2}})\s*{topic_word}\b", low
    )
    if numeric_range:
        first, second = int(numeric_range.group(1)), int(numeric_range.group(2))
        if 1 <= first <= 10 and 1 <= second <= 10:
            return min(first, second), max(first, second)
    words = "|".join(sorted((re.escape(word) for word in _TOPIC_NUMBER_WORDS), key=len, reverse=True))
    word_range = re.search(
        rf"\b(?:от\s*)?({words})\s+(?:до|и)\s+({words})\s+{topic_word}\b", low
    )
    if word_range:
        first, second = _TOPIC_NUMBER_WORDS[word_range.group(1)], _TOPIC_NUMBER_WORDS[word_range.group(2)]
        return min(first, second), max(first, second)

    single = re.search(rf"\b(10|[1-9])\s*{topic_word}\b", low)
    if single:
        value = int(single.group(1))
        return value, value
    for word, value in _TOPIC_NUMBER_WORDS.items():
        if re.search(rf"\b{re.escape(word)}\s+{topic_word}\b", low):
            return value, value
    bounded = max(1, min(10, int(default or 10)))
    # General history overview: list at least five only when five distinct topics
    # exist, and never ask the model to fabricate entries when fewer are available.
    return min(5, bounded), bounded

