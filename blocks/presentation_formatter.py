# blocks/presentation_formatter.py

# =====================================================
# 🧠 APRIL PRESENTATION FORMATTER
# =====================================================

"""
APRIL SPACE PRESENTATION LAYER

CLEAN TEXT-ONLY PIPELINE.

Этот слой теперь:

✅ НЕ строит scene payload
✅ НЕ создает link blocks
✅ НЕ работает с graph payload
✅ НЕ работает с formula payload
✅ НЕ мутирует renderer objects
✅ НЕ занимается multimedia rendering
✅ НЕ вмешивается в message renderer
✅ НЕ ломает future BASIC scene system

Он делает только:

- safe text cleanup
- calm readability
- stable text formatting
- safe plain-text preparation

Renderer / scene / links / graphs:
→ полностью вынесены из этого слоя.
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
# 🔥 MARKDOWN CLEANUP
# =====================================================

def cleanup_markdown(text):

    text = normalize_text_payload(text)

    if not text:
        return ""

    # =============================================
    # REMOVE TELEGRAM LEGACY
    # =============================================

    text = text.replace("**", "")
    text = text.replace("__", "")

    # =============================================
    # NORMALIZE EMPTY LINES
    # =============================================

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    # =============================================
    # NORMALIZE SPACES
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
            ["идея", "концепция"],
            "💡"
        ),

        (
            ["ошибка", "warning"],
            "⚠️"
        ),

        (
            ["новость", "обновление"],
            "📰"
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

    if is_code_payload(text):
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

    if isinstance(text, dict):
        return True

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
    # CODE
    # =============================================

    if is_code_payload(text):

        safe_format_log(
            "CODE BYPASS"
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

    # =============================================
    # CLEANUP
    # =============================================

    text = cleanup_markdown(
        text
    )

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
    # SAFE PASS
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
