# blocks/presentation_formatter.py

# =====================================================
# 🧠 APRIL PRESENTATION FORMATTER
# =====================================================

"""
APRIL SPACE PRESENTATION LAYER

Renderer-first presentation architecture.

Этот слой:

✅ НЕ ломает renderer payload
✅ НЕ мутирует scene objects
✅ НЕ трогает graph/formula/code payload
✅ НЕ дублирует renderer logic
✅ НЕ создает markdown chaos
✅ НЕ делает telegram formatting spam

Он делает:

- clean text presentation
- calm readability
- safe link extraction
- stable multimodal formatting
- renderer-safe delivery
- clean TXT preparation

APRIL PRINCIPLES:
- renderer-first
- scene-safe
- payload-safe
- no duplication
- no markdown chaos
- no telegram legacy
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
# 🔥 NORMALIZE
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
# 🔥 JSON DETECTION
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
# 🔥 RENDERER PAYLOAD
# =====================================================

def is_renderer_payload(text):

    text = normalize_text_payload(text)

    if not text:
        return False

    t = text.lower()

    checks = [

        # graph
        "[[graph:",
        "\"type\":\"graph\"",
        "\"type\": \"graph\"",

        # formula
        "[[formula",
        "\"type\":\"formula\"",
        "\"type\": \"formula\"",

        # diagram
        "[[diagram",

        # scene
        "\"scene\":",
        "\"blocks\":",
        "[[scene",

        # html/svg
        "<svg",
        "<canvas",
        "```html",
        "```svg",

        # image
        "data:image",

        # tables
        "\"type\":\"table\"",
        "\"type\": \"table\""
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
# 🔥 URL EXTRACTION
# =====================================================

URL_REGEX = r"https?://[^\s\)\]\}\"\'<>]+"


def extract_urls(text):

    text = normalize_text_payload(text)

    raw_urls = re.findall(
        URL_REGEX,
        text
    )

    result = []

    for url in raw_urls:

        clean = clean_url(url)

        if clean and clean not in result:

            result.append(clean)

    return result


# =====================================================
# 🔥 URL CLEANER
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
# 🔥 MARKDOWN CLEANUP
# =====================================================

def cleanup_markdown(text):

    text = normalize_text_payload(text)

    if not text:
        return ""

    # remove telegram markdown chaos
    text = text.replace("**", "")
    text = text.replace("__", "")

    # normalize spaces
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
# 🔥 REMOVE RAW URLS
# =====================================================

def remove_urls_from_text(
    text,
    urls
):

    result = text

    for url in urls:

        result = result.replace(
            url,
            ""
        )

    result = re.sub(
        r"\n{3,}",
        "\n\n",
        result
    )

    return result.strip()


# =====================================================
# 🔥 SCENE LINK BUILDER
# =====================================================

def build_scene_link_blocks(text):

    text = normalize_text_payload(text)

    if not text:
        return None

    urls = extract_urls(text)

    if not urls:
        return None

    clean_urls = []

    for url in urls:

        safe_url = clean_url(url)

        if (
            safe_url
            and safe_url not in clean_urls
        ):

            clean_urls.append(
                safe_url
            )

    if not clean_urls:
        return None

    clean_text = remove_urls_from_text(
        text,
        clean_urls
    )

    clean_text = cleanup_markdown(
        clean_text
    )

    scene = []

    if clean_text:

        scene.append({

            "type": "markdown",

            "content": clean_text
        })

    for url in clean_urls:

        scene.append({

            "type": "link",

            "url": url
        })

    return {

        "type": "scene",

        "blocks": scene
    }


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
# 🔥 BYPASS RULES
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

    if looks_like_json(text):

        safe_format_log(
            "JSON BYPASS"
        )

        return True

    if is_renderer_payload(text):

        safe_format_log(
            "RENDERER BYPASS"
        )

        return True

    if is_code_payload(text):

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
    # 🔥 SCENE LINK MODE
    # =============================================

    scene_links = build_scene_link_blocks(
        text
    )

    if scene_links:

        return scene_links

    # =============================================
    # LIGHT FORMAT
    # =============================================

    text = apply_light_formatting(
        text
    )

    # =============================================
    # VISUAL ENRICHMENT
    # =============================================

    text = apply_visual_enrichment(
        text
    )

    return text.strip()


# =====================================================
# 🔥 FINAL VOICE
# =====================================================

def apply_april_final_voice(text):

    if isinstance(text, dict):
        return text

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

    if isinstance(text, dict):
        return text

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

    return formatted


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

    # =============================================
    # 🔥 SAFE SCENE PASS
    # =============================================

    if isinstance(final_text, dict):

        return final_text

    final_text = normalize_text_payload(
        final_text
    )

    if not final_text:
        return ""

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
