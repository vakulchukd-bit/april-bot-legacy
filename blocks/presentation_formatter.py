# blocks/presentation_formatter.py

# =====================================================
# 🧠 APRIL PRESENTATION FORMATTER
# =====================================================

"""
Presentation layer April.

Этот модуль:

- НЕ меняет personality;
- НЕ отвечает вместо April;
- НЕ ломает trajectory;
- НЕ превращает ответы в UI-кашу.

Он:

- улучшает readability;
- делает ответы визуально приятнее;
- добавляет лёгкую структуру;
- помогает удерживать внимание;
- делает ответы более "живыми".

Работает как formatting capability самой April.

APRIL PRESENTATION PRINCIPLES:

- renderer-first;
- calm formatting;
- lightweight visuality;
- no token inflation;
- no formatting loops;
- no renderer corruption;
- no fake UI decoration;
- no destructive payload mutation;
- scene-safe formatting;
- multimodal-safe presentation.
"""

import re
import json


# =====================================================
# 🔥 SAFE FORMAT PATCH
# =====================================================

FORMAT_PATCH_LOG = []


def safe_format_log(msg):

    try:

        print("FORMAT PATCH:", msg)

        FORMAT_PATCH_LOG.append(msg)

    except:
        pass


# =====================================================
# 🔥 SAFE TYPE NORMALIZATION
# =====================================================

def normalize_text_payload(text):

    if text is None:
        return ""

    if isinstance(text, str):
        return text

    try:

        return str(text)

    except:

        return ""


# =====================================================
# 🔥 STRUCTURE DETECTION
# =====================================================

def is_structured_payload(
    text
):

    if isinstance(
        text,
        (dict, list)
    ):

        return True

    text = normalize_text_payload(text)

    if not text:
        return False

    stripped = text.strip()

    if (
        stripped.startswith("{")
        and stripped.endswith("}")
    ):

        try:

            json.loads(stripped)

            return True

        except:
            pass

    if (
        stripped.startswith("[")
        and stripped.endswith("]")
    ):

        try:

            json.loads(stripped)

            return True

        except:
            pass

    return False


# =====================================================
# 🔥 SCENE PAYLOAD DETECTION
# =====================================================

def is_scene_payload(
    text: str
):

    text = normalize_text_payload(text)

    if not text:
        return False

    t = text.lower()

    scene_checks = [

        "\"scene\":",
        "\"blocks\":",
        "\"renderer\":",
        "\"layout\":",

        "[[scene",
        "[[layout",
        "[[block",
        "[[grid",

        "<scene",
        "<layout",

        "scene_objects",
        "primitive_scene"
    ]

    return any(
        x in t
        for x in scene_checks
    )


# =====================================================
# 🔥 RENDERER PAYLOAD DETECTION
# =====================================================

def is_renderer_payload(
    text: str
):

    text = normalize_text_payload(text)

    if not text:
        return False

    t = text.lower().strip()

    renderer_checks = [

        "[[graph:",
        "[[formula",
        "[[diagram",
        "[[scene",
        "[[grid",

        "<svg",
        "<canvas",

        "\"type\": \"graph\"",
        "\"type\":\"graph\"",

        "\"type\": \"formula\"",
        "\"type\":\"formula\"",

        "\"graph\":",
        "\"diagram\":",
        "\"formula\":",

        "data:image",

        "desmos.com",

        "```html",
        "```svg"
    ]

    return any(
        x in t
        for x in renderer_checks
    )


# =====================================================
# 🔥 WEB / UI DETECTION
# =====================================================

def is_web_render_context(
    user_text: str
):

    t = (
        user_text or ""
    ).lower()

    web_words = [

        "график",
        "diagram",
        "диаграм",
        "chart",
        "canvas",
        "render",
        "ui",
        "интерфейс",
        "картин",
        "image",
        "визуал",
        "нарисуй",
        "сгенерируй",
        "plot",
        "desmos",
        "scene",
        "layout",
        "formula",
        "таблица",
        "renderer"
    ]

    return any(
        x in t
        for x in web_words
    )


def looks_like_visual_payload(
    text: str
):

    text = normalize_text_payload(text)

    t = text.lower()

    checks = [

        "```html",
        "<svg",
        "<canvas",
        "desmos.com",
        "\"type\": \"graph\"",
        "\"type\":\"graph\"",
        "\"graph\":",
        "\"diagram\":",
        "\"image_url\":",
        "data:image",
        "[[formula]]",
        "[[graph]]",
        "[[diagram]]",
        "[[scene]]",
        "[[grid]]"
    ]

    return any(
        x in t
        for x in checks
    )


# =====================================================
# 🔥 EMOJI MAP
# =====================================================

EMOJI_MAP = {

    "travel": "🌍",
    "city": "🏙️",
    "nature": "🌿",
    "history": "🏛️",
    "food": "🍽️",
    "science": "🧠",
    "warning": "⚠️",
    "idea": "💡",
    "guide": "🧭",
    "visual": "🖼️",
    "music": "🎵",
    "technology": "⚙️",
    "news": "📰",
    "success": "✅",
    "rest": "🏖️",
    "map": "🗺️",

    "youtube": "▶️",
    "telegram": "📨",
    "instagram": "📸",
    "facebook": "📘",
    "twitter": "𝕏",
    "x": "𝕏",
    "github": "💻",
    "wikipedia": "📚",
    "linkedin": "💼",
    "reddit": "👽",
    "tiktok": "🎬",
    "discord": "🎮",
    "website": "🔗"
}


# =====================================================
# 🌐 PLATFORM DETECTION
# =====================================================

def detect_platform_label(
    url: str
):

    url = (
        url or ""
    ).lower()

    if "youtube.com" in url:
        return "▶️ Видео"

    if "youtu.be" in url:
        return "▶️ Видео"

    if "github.com" in url:
        return "💻 GitHub"

    if "reddit.com" in url:
        return "👽 Reddit"

    if "t.me" in url:
        return "📨 Telegram"

    return "🔗 Ссылка"


# =====================================================
# 🌐 EXTRACT URLS
# =====================================================

def extract_urls(
    text: str
):

    text = normalize_text_payload(text)

    pattern = r"https?://[^\s]+"

    return re.findall(
        pattern,
        text
    )


# =====================================================
# 🧠 SAFE MARKDOWN CLEANER
# =====================================================

def cleanup_markdown(
    text: str
):

    text = normalize_text_payload(text)

    if not text:
        return text

    text = text.replace(
        "**",
        ""
    )

    text = text.replace(
        "__",
        ""
    )

    text = re.sub(
        r"([^]+)\][^)]+",
        r"\1",
        text
    )

    text = re.sub(
        r"|",
        "",
        text
    )

    text = re.sub(
        r"\s*$",
        "",
        text
    )

    text = re.sub(
        r"\s*$",
        "",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    text = re.sub(
        r"[ ]{2,}",
        " ",
        text
    )

    return text.strip()


# =====================================================
# 🌐 SAFE URL CLEANER
# =====================================================

def clean_url(
    url: str
):

    url = (
        url or ""
    ).strip()

    if not url:
        return ""

    trailing_symbols = [

        "\"",
        "'",
        ")",
        "]",
        "}",
        ">",
        ",",
        ";",
        ".",
        "*",
        "_"
    ]

    while (

        url
        and url[-1] in trailing_symbols

    ):

        url = url[:-1]

    return url.strip()


# =====================================================
# 🌐 SAFE LINK ORGANIZER
# =====================================================

def build_safe_link_blocks(
    text: str
):

    text = normalize_text_payload(
        text
    )

    if not text:
        return text

    urls = extract_urls(
        text
    )

    if not urls:
        return cleanup_markdown(
            text
        )

    cleaned_urls = []

    for url in urls:

        safe_url = clean_url(
            url
        )

        if safe_url:

            cleaned_urls.append(
                safe_url
            )

    result_text = text

    # =================================================
    # 🔥 REMOVE RAW URLS
    # =====================================================

    for old_url in urls:

        result_text = result_text.replace(
            old_url,
            ""
        )

    result_text = cleanup_markdown(
        result_text
    )

    # =================================================
    # 🔥 REMOVE DUPLICATE PLATFORM LINES
    # =====================================================

    duplicate_lines = [

        "💻 github ↗",
        "▶️ youtube ↗",
        "▶️ видео ↗",
        "👽 reddit ↗",
        "📨 telegram ↗"
    ]

    cleaned_lines = []

    for line in result_text.split("\n"):

        normalized = (
            line.strip().lower()
        )

        if normalized in duplicate_lines:
            continue

        cleaned_lines.append(
            line
        )

    result_text = "\n".join(
        cleaned_lines
    )

    result_text = re.sub(
        r"\n{3,}",
        "\n\n",
        result_text
    ).strip()

    # =================================================
    # 🔥 BUILD ORDERED BLOCKS
    # =====================================================

    sections = split_into_sections(
        result_text
    )

    final_blocks = []

    url_index = 0

    for section in sections:

        clean_section = (
            section.strip()
        )

        if clean_section:

            final_blocks.append(
                clean_section
            )

        if url_index < len(cleaned_urls):

            safe_url = cleaned_urls[
                url_index
            ]

            platform = detect_platform_label(
                safe_url
            )

            final_blocks.append(

                f"{platform} ↗\n"
                f"{safe_url}"
            )

            url_index += 1

    while url_index < len(cleaned_urls):

        safe_url = cleaned_urls[
            url_index
        ]

        platform = detect_platform_label(
            safe_url
        )

        final_blocks.append(

            f"{platform} ↗\n"
            f"{safe_url}"
        )

        url_index += 1

    return "\n\n".join(
        final_blocks
    ).strip()


# =====================================================
# 🔥 CRITICAL CONTENT DETECTION
# =====================================================

def is_code_content(
    text: str
):

    text = normalize_text_payload(text)

    if not text:
        return False

    checks = [

        "```",
        "<!DOCTYPE html>",
        "<html",
        "def ",
        "import ",
        "class ",
        "console.log(",
        "function(",
        "async def",
        "return {",
        "const ",
        "let ",
        "var "
    ]

    return any(
        x in text
        for x in checks
    )


def is_formula_payload(
    text: str
):

    text = normalize_text_payload(text)

    if not text:
        return False

    checks = [

        "y=",
        "sin(",
        "cos(",
        "tan(",
        "f(x)",
        "^2",
        "^3"
    ]

    return any(
        x in text
        for x in checks
    )


def is_realtime_content(
    text: str
):

    text = normalize_text_payload(text)

    if not text:
        return False

    t = text.lower()

    realtime_words = [

        "live",
        "realtime",
        "tracking",
        "маршрут",
        "координаты",
        "где находится",
        "рейс",
        "судно",
        "самолет",
        "поезд",
        "карта"
    ]

    return any(
        x in t
        for x in realtime_words
    )


def already_formatted(
    text: str
):

    text = normalize_text_payload(text)

    if not text:
        return False

    checks = [

        "━━━",
        "💻 github ↗",
        "▶️ видео ↗",
        "👽 reddit ↗"
    ]

    lowered = text.lower()

    return any(
        x in lowered
        for x in checks
    )


# =====================================================
# 🔥 RENDERER BLOCK PROTECTION
# =====================================================

def should_skip_formatting(
    text: str,
    user_text: str,
    semantic: dict,
    response_decision: dict
):

    semantic = semantic or {}
    response_decision = response_decision or {}

    text = normalize_text_payload(text)

    if not text:
        return True

    if is_structured_payload(text):

        safe_format_log(
            "STRUCTURED PAYLOAD BYPASS"
        )

        return True

    if is_scene_payload(text):

        safe_format_log(
            "SCENE PAYLOAD BYPASS"
        )

        return True

    if is_renderer_payload(text):

        safe_format_log(
            "RENDERER PAYLOAD BYPASS"
        )

        return True

    if looks_like_visual_payload(
        text
    ):

        safe_format_log(
            "VISUAL PAYLOAD BYPASS"
        )

        return True

    if is_code_content(text):

        safe_format_log(
            "CODE BYPASS"
        )

        return True

    if is_formula_payload(text):

        safe_format_log(
            "FORMULA BYPASS"
        )

        return True

    if semantic.get(
        "render_intent"
    ):

        safe_format_log(
            "RENDER INTENT BYPASS"
        )

        return True

    if response_decision.get(
        "should_render"
    ):

        safe_format_log(
            "RENDER RESPONSE BYPASS"
        )

        return True

    return False


# =====================================================
# 🧠 KEYWORD EMOJI DETECTION
# =====================================================

def detect_primary_emoji(
    text: str
):

    t = (
        text or ""
    ).lower()

    checks = [

        (
            ["город", "страна", "улица"],
            EMOJI_MAP["city"]
        ),

        (
            ["путешествие", "отдых"],
            EMOJI_MAP["travel"]
        ),

        (
            ["природа", "лес", "горы"],
            EMOJI_MAP["nature"]
        ),

        (
            ["история", "музей"],
            EMOJI_MAP["history"]
        ),

        (
            ["еда", "ресторан"],
            EMOJI_MAP["food"]
        ),

        (
            ["идея", "концепт"],
            EMOJI_MAP["idea"]
        ),

        (
            ["новости"],
            EMOJI_MAP["news"]
        ),

        (
            ["карта", "маршрут"],
            EMOJI_MAP["map"]
        )
    ]

    for words, emoji in checks:

        for word in words:

            if word in t:
                return emoji

    return "✨"


# =====================================================
# 🧠 SECTION SPLITTER
# =====================================================

def split_into_sections(
    text: str
):

    text = normalize_text_payload(text)

    text = text.strip()

    if not text:
        return []

    if is_scene_payload(text):
        return [text]

    if is_renderer_payload(text):
        return [text]

    if is_code_content(text):
        return [text]

    parts = []

    blocks = re.split(
        r"\n{2,}",
        text
    )

    for block in blocks:

        cleaned = block.strip()

        if cleaned:
            parts.append(cleaned)

    return parts


# =====================================================
# 🧠 LIGHT FORMAT
# =====================================================

def apply_light_formatting(
    text: str
):

    text = normalize_text_payload(text)

    sections = split_into_sections(
        text
    )

    if not sections:
        return text

    result = []

    for section in sections:

        result.append(
            section.strip()
        )

    return "\n\n".join(result)


# =====================================================
# 🧠 VISUAL ENRICHMENT
# =====================================================

def apply_visual_enrichment(
    text: str
):

    text = normalize_text_payload(text)

    text = text.strip()

    if not text:
        return text

    if is_renderer_payload(text):
        return text

    if is_scene_payload(text):
        return text

    if is_code_content(text):
        return text

    if is_formula_payload(text):
        return text

    if len(text) <= 80:
        return text

    if text.startswith((
        "```",
        "<",
        "[[",
        "{"
    )):

        return text

    emoji = detect_primary_emoji(
        text
    )

    if text.startswith(emoji):
        return text

    return f"{emoji} {text}"


# =====================================================
# 🧠 SMART PRESENTATION
# =====================================================

def build_smart_presentation(

    text: str,
    semantic: dict,
    cognition: dict,
    response_decision: dict,
    user_text: str = ""
):

    semantic = semantic or {}
    cognition = cognition or {}
    response_decision = (
        response_decision or {}
    )

    text = normalize_text_payload(text)
    text = text.strip()

    if not text:
        return text

    if should_skip_formatting(

        text,
        user_text,
        semantic,
        response_decision
    ):

        return text

    if is_realtime_content(
        text
    ):

        safe_format_log(
            "REALTIME LIGHT FORMAT"
        )

        return apply_light_formatting(
            text
        )

    # =================================================
    # 🔥 SAFE LINK ORGANIZATION
    # =====================================================

    text = build_safe_link_blocks(
        text
    )

    if cognition.get(
        "reduce_talking"
    ):

        return apply_visual_enrichment(
            text
        )

    return apply_visual_enrichment(

        apply_light_formatting(
            text
        )
    )


# =====================================================
# 🧠 APRIL FINAL VOICE ALIGNMENT
# =====================================================

def apply_april_final_voice(

    text: str,
    semantic: dict,
    cognition: dict,
    response_decision: dict
):

    text = normalize_text_payload(text)
    text = text.strip()

    if not text:
        return text

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# =====================================================
# 🧠 RESPONSE BEAUTIFIER
# =====================================================

def beautify_response(

    text: str,
    semantic: dict,
    cognition: dict,
    response_decision: dict,
    user_text: str = ""
):

    text = normalize_text_payload(text)

    if not text:
        return text

    if should_skip_formatting(

        text,
        user_text,
        semantic,
        response_decision
    ):

        safe_format_log(
            "FULL BEAUTIFY BYPASS"
        )

        return text

    formatted = build_smart_presentation(

        text,
        semantic,
        cognition,
        response_decision,
        user_text
    )

    formatted = apply_april_final_voice(

        formatted,
        semantic,
        cognition,
        response_decision
    )

    return formatted.strip()


# =====================================================
# 🧠 MAIN PUBLIC FORMATTER
# =====================================================

def format_response_presentation(

    text: str = "",
    response: str = "",
    semantic: dict = None,
    cognition: dict = None,
    response_decision: dict = None,
    user_text: str = "",
    visual_reference: dict = None
):

    semantic = semantic or {}
    cognition = cognition or {}
    response_decision = (
        response_decision or {}
    )

    final_text = response or text

    final_text = normalize_text_payload(
        final_text
    )

    if not final_text:
        return final_text

    if should_skip_formatting(

        final_text,
        user_text,
        semantic,
        response_decision
    ):

        safe_format_log(
            "FINAL FORMATTER BYPASS"
        )

        return final_text

    return beautify_response(

        final_text,
        semantic,
        cognition,
        response_decision,
        user_text
    )
