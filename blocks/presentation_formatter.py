# blocks/presentation_formatter.py

# =====================================================
# 🧠 APRIL PRESENTATION FORMATTER
# =====================================================

"""
APRIL SPACE PRESENTATION LAYER

Этот слой отвечает ТОЛЬКО за presentation/render preparation.

Он НЕ:
- принимает решения вместо April;
- НЕ роутит комнаты;
- НЕ ломает renderer payload;
- НЕ форматирует code/graph/formula payload;
- НЕ мутирует scene objects;
- НЕ строит fake markdown chaos.

Он ДЕЛАЕТ:
- calm formatting;
- scene-safe cleanup;
- renderer-safe delivery;
- multimodal preparation;
- clean link handling;
- stable message presentation;
- readable visual structure.

APRIL PRINCIPLES:
- renderer-first
- scene-safe
- payload-safe
- no mutation
- no decoration spam
- no markdown chaos
- no telegram formatting legacy
"""

import re
import json


# =====================================================
# 🔥 LOG
# =====================================================

FORMAT_PATCH_LOG = []


def safe_format_log(msg):

    try:

        print("PRESENTATION:", msg)

        FORMAT_PATCH_LOG.append(msg)

    except:
        pass


# =====================================================
# 🔥 SAFE NORMALIZE
# =====================================================

def normalize_text_payload(value):

    if value is None:
        return ""

    if isinstance(value, str):
        return value

    try:
        return str(value)

    except:
        return ""


# =====================================================
# 🔥 SAFE JSON CHECK
# =====================================================

def looks_like_json(text):

    text = normalize_text_payload(text).strip()

    if not text:
        return False

    if not (
        text.startswith("{")
        or text.startswith("[")
    ):
        return False

    try:

        json.loads(text)

        return True

    except:
        return False


# =====================================================
# 🔥 PAYLOAD DETECTION
# =====================================================

def is_renderer_payload(text):

    text = normalize_text_payload(text)

    if not text:
        return False

    t = text.lower()

    checks = [

        # =============================================
        # GRAPH
        # =============================================

        "[[graph:",
        "\"type\": \"graph\"",
        "\"type\":\"graph\"",

        # =============================================
        # FORMULA
        # =============================================

        "[[formula",
        "\"type\": \"formula\"",
        "\"type\":\"formula\"",

        # =============================================
        # DIAGRAM
        # =============================================

        "[[diagram",
        "\"type\": \"diagram\"",
        "\"type\":\"diagram\"",

        # =============================================
        # SCENE
        # =============================================

        "[[scene",
        "\"scene\":",
        "\"blocks\":",

        # =============================================
        # SVG / HTML
        # =============================================

        "<svg",
        "<canvas",
        "```html",
        "```svg",

        # =============================================
        # IMAGE
        # =============================================

        "data:image",

        # =============================================
        # TABLE
        # =============================================

        "\"type\": \"table\"",
        "\"type\":\"table\""
    ]

    return any(
        x in t
        for x in checks
    )


# =====================================================
# 🔥 CODE DETECTION
# =====================================================

def is_code_payload(text):

    text = normalize_text_payload(text)

    if not text:
        return False

    checks = [

        "```",

        "import ",
        "from ",

        "const ",
        "let ",
        "var ",

        "function ",
        "async function",

        "class ",

        "export default",

        "return (",

        "def ",
        "async def",

        "console.log(",

        "<div",
        "</div>"
    ]

    return any(
        x in text
        for x in checks
    )


# =====================================================
# 🔥 FORMULA DETECTION
# =====================================================

def is_formula_payload(text):

    text = normalize_text_payload(text)

    if not text:
        return False

    t = text.lower()

    checks = [

        "y=",
        "y =",

        "f(x)",

        "sin(",
        "cos(",
        "tan(",

        "^2",
        "^3",

        "$$"
    ]

    return any(
        x in t
        for x in checks
    )


# =====================================================
# 🔥 LINK EXTRACTION
# =====================================================

URL_REGEX = r"https?://[^\s\)\]\}\"\'<>]+"


def extract_urls(text):

    text = normalize_text_payload(text)

    return re.findall(
        URL_REGEX,
        text
    )


# =====================================================
# 🔥 CLEAN URL
# =====================================================

def clean_url(url):

    url = normalize_text_payload(url).strip()

    if not url:
        return ""

    trailing = [

        ".",
        ",",
        ";",
        ":",
        "\"",
        "'",
        ")",
        "]",
        "}",
        ">"
    ]

    while (
        url
        and url[-1] in trailing
    ):

        url = url[:-1]

    return url.strip()


# =====================================================
# 🔥 URL LABEL
# =====================================================

def detect_platform_label(url):

    u = (
        url or ""
    ).lower()

    if "github.com" in u:
        return "💻 GitHub"

    if "youtube.com" in u:
        return "▶️ YouTube"

    if "youtu.be" in u:
        return "▶️ YouTube"

    if "reddit.com" in u:
        return "👽 Reddit"

    if "t.me" in u:
        return "📨 Telegram"

    return "🔗 Link"


# =====================================================
# 🔥 MARKDOWN CLEANER
# =====================================================

def cleanup_markdown(text):

    text = normalize_text_payload(text)

    if not text:
        return ""

    # =============================================
    # REMOVE TELEGRAM LEGACY
    # =============================================

    text = text.replace(
        "**",
        ""
    )

    text = text.replace(
        "__",
        ""
    )

    text = text.replace(
        "`",
        "`"
    )

    # =============================================
    # REMOVE DUPLICATE EMPTY LINES
    # =============================================

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    # =============================================
    # REMOVE HUGE SPACES
    # =============================================

    text = re.sub(
        r"[ ]{2,}",
        " ",
        text
    )

    return text.strip()


# =====================================================
# 🔥 SECTION SPLITTER
# =====================================================

def split_into_sections(text):

    text = normalize_text_payload(text)

    if not text:
        return []

    if is_renderer_payload(text):
        return [text]

    if is_code_payload(text):
        return [text]

    blocks = re.split(
        r"\n{2,}",
        text
    )

    result = []

    for block in blocks:

        cleaned = block.strip()

        if cleaned:

            result.append(
                cleaned
            )

    return result


# =====================================================
# 🔥 LINK BLOCKS
# =====================================================

def build_safe_link_blocks(text):

    text = normalize_text_payload(text)

    if not text:
        return ""

    urls = extract_urls(text)

    if not urls:

        return cleanup_markdown(
            text
        )

    clean_urls = []

    for url in urls:

        safe_url = clean_url(url)

        if safe_url:

            clean_urls.append(
                safe_url
            )

    # =============================================
    # REMOVE URLS FROM TEXT
    # =============================================

    result_text = text

    for url in urls:

        result_text = result_text.replace(
            url,
            ""
        )

    result_text = cleanup_markdown(
        result_text
    )

    sections = split_into_sections(
        result_text
    )

    final = []

    for section in sections:

        final.append(
            section
        )

    # =============================================
    # APPEND LINKS CLEANLY
    # =============================================

    used = set()

    for url in clean_urls:

        if url in used:
            continue

        used.add(url)

        label = detect_platform_label(
            url
        )

        final.append(

            f"{label} ↗\n{url}"
        )

    return "\n\n".join(
        final
    ).strip()


# =====================================================
# 🔥 EMOJI DETECTION
# =====================================================

def detect_primary_emoji(text):

    t = (
        text or ""
    ).lower()

    checks = [

        (
            ["код", "python", "react"],
            "💻"
        ),

        (
            ["график", "формула"],
            "📈"
        ),

        (
            ["идея", "концепция"],
            "💡"
        ),

        (
            ["ссылка", "github"],
            "🔗"
        ),

        (
            ["ошибка", "warning"],
            "⚠️"
        )
    ]

    for words, emoji in checks:

        for word in words:

            if word in t:
                return emoji

    return "✨"


# =====================================================
# 🔥 VISUAL ENRICHMENT
# =====================================================

def apply_visual_enrichment(text):

    text = normalize_text_payload(text)

    if not text:
        return ""

    if is_renderer_payload(text):
        return text

    if is_code_payload(text):
        return text

    if is_formula_payload(text):
        return text

    if len(text) <= 60:
        return text

    emoji = detect_primary_emoji(
        text
    )

    if text.startswith(emoji):
        return text

    return f"{emoji} {text}"


# =====================================================
# 🔥 BYPASS
# =====================================================

def should_skip_formatting(

    text,
    semantic=None,
    response_decision=None
):

    semantic = semantic or {}
    response_decision = (
        response_decision or {}
    )

    text = normalize_text_payload(text)

    if not text:
        return True

    # =============================================
    # JSON
    # =============================================

    if looks_like_json(text):

        safe_format_log(
            "JSON BYPASS"
        )

        return True

    # =============================================
    # RENDERER
    # =============================================

    if is_renderer_payload(text):

        safe_format_log(
            "RENDERER BYPASS"
        )

        return True

    # =============================================
    # CODE
    # =============================================

    if is_code_payload(text):

        safe_format_log(
            "CODE BYPASS"
        )

        return True

    # =============================================
    # FORMULA
    # =============================================

    if is_formula_payload(text):

        safe_format_log(
            "FORMULA BYPASS"
        )

        return True

    # =============================================
    # SEMANTIC RENDER
    # =============================================

    if semantic.get(
        "render_intent"
    ):

        safe_format_log(
            "SEMANTIC RENDER BYPASS"
        )

        return True

    if response_decision.get(
        "should_render"
    ):

        safe_format_log(
            "RESPONSE RENDER BYPASS"
        )

        return True

    return False


# =====================================================
# 🔥 LIGHT FORMAT
# =====================================================

def apply_light_formatting(text):

    sections = split_into_sections(
        text
    )

    return "\n\n".join(
        sections
    ).strip()


# =====================================================
# 🔥 SMART PRESENTATION
# =====================================================

def build_smart_presentation(

    text,
    semantic=None,
    cognition=None,
    response_decision=None,
    user_text=""
):

    semantic = semantic or {}
    cognition = cognition or {}
    response_decision = (
        response_decision or {}
    )

    text = normalize_text_payload(text)

    if not text:
        return ""

    if should_skip_formatting(

        text,
        semantic,
        response_decision
    ):

        return text

    # =============================================
    # CLEAN LINKS
    # =============================================

    text = build_safe_link_blocks(
        text
    )

    # =============================================
    # LIGHT FORMAT
    # =============================================

    text = apply_light_formatting(
        text
    )

    # =============================================
    # VISUAL ENRICH
    # =============================================

    text = apply_visual_enrichment(
        text
    )

    return text.strip()


# =====================================================
# 🔥 FINAL VOICE ALIGNMENT
# =====================================================

def apply_april_final_voice(text):

    text = normalize_text_payload(text)

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# =====================================================
# 🔥 BEAUTIFIER
# =====================================================

def beautify_response(

    text,
    semantic=None,
    cognition=None,
    response_decision=None,
    user_text=""
):

    semantic = semantic or {}
    cognition = cognition or {}
    response_decision = (
        response_decision or {}
    )

    text = normalize_text_payload(text)

    if not text:
        return ""

    if should_skip_formatting(

        text,
        semantic,
        response_decision
    ):

        return text

    formatted = build_smart_presentation(

        text,
        semantic,
        cognition,
        response_decision,
        user_text
    )

    formatted = apply_april_final_voice(
        formatted
    )

    return formatted.strip()


# =====================================================
# 🔥 MAIN PUBLIC API
# =====================================================

def format_response_presentation(

    text="",
    response="",
    semantic=None,
    cognition=None,
    response_decision=None,
    user_text="",
    visual_reference=None
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
        return ""

    # =============================================
    # FINAL SAFE BYPASS
    # =============================================

    if should_skip_formatting(

        final_text,
        semantic,
        response_decision
    ):

        safe_format_log(
            "FINAL BYPASS"
        )

        return final_text

    return beautify_response(

        final_text,
        semantic,
        cognition,
        response_decision,
        user_text
    )
