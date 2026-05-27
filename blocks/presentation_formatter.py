# blocks/presentation_formatter.py

# =====================================================
# 🧠 APRIL PRESENTATION FORMATTER
# =====================================================

"""
APRIL SPACE PRESENTATION LAYER

SAFE HYBRID PRESENTATION PIPELINE.

Этот слой теперь:

✅ НЕ ломает renderer payload
✅ НЕ сериализует scene objects в text
✅ НЕ flatten'ит multimodal blocks
✅ НЕ уничтожает graph/formula/code payload
✅ НЕ вмешивается в renderer execution
✅ НЕ мутирует artifact objects
✅ НЕ ломает future spatial architecture

Он делает только:

- safe text cleanup
- calm readability
- stable text formatting
- continuity-aware presentation
- semantic pacing
- response ordering stabilization
- formatting ONLY text fragments

Renderer / graph / formula / code / links:
→ проходят через слой БЕЗ уничтожения структуры.
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
# 🔥 SAFE PAYLOAD DETECTION
# =====================================================

def is_renderer_payload(value):

    if not isinstance(value, (dict, list)):
        return False

    # =================================================
    # 🔥 DIRECT TYPE
    # =====================================================

    if isinstance(value, dict):

        payload_type = value.get(
            "type"
        )

        if payload_type in [

            "graph",
            "formula",
            "code",
            "table",
            "diagram",
            "layout",
            "link",
            "renderer",
            "scene",
            "visual",
            "artifact",
            "message_block"
        ]:

            return True

    # =================================================
    # 🔥 LIST OF BLOCKS
    # =====================================================

    if isinstance(value, list):

        for item in value:

            if isinstance(item, dict):

                item_type = item.get(
                    "type"
                )

                if item_type in [

                    "graph",
                    "formula",
                    "code",
                    "table",
                    "diagram",
                    "layout",
                    "link",
                    "renderer",
                    "scene",
                    "visual",
                    "artifact",
                    "message_block"
                ]:

                    return True

    return False


# =====================================================
# 🔥 NORMALIZE
# =====================================================

def normalize_text_payload(value):

    # =================================================
    # 🔥 KEEP RENDERER OBJECTS ALIVE
    # =====================================================

    if is_renderer_payload(value):

        safe_format_log(
            "RENDERER PAYLOAD PRESERVED"
        )

        return value

    if value is None:
        return ""

    if isinstance(value, str):
        return value

    # =================================================
    # 🔥 SAFE NON-TEXT
    # =====================================================

    if isinstance(value, (dict, list)):

        safe_format_log(
            "NON-TEXT PAYLOAD PRESERVED"
        )

        return value

    try:
        return str(value)

    except:
        return ""


# =====================================================
# 🔥 SAFE CONTAINS
# =====================================================

def contains_any(
    text,
    words
):

    return any(
        w in text
        for w in words
    )


# =====================================================
# 🔥 JSON DETECTION
# =====================================================

def looks_like_json(text):

    if not isinstance(text, str):
        return False

    text = text.strip()

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

    if not isinstance(text, str):
        return False

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

    if not isinstance(text, str):
        return text

    if not text:
        return ""

    text = text.replace("**", "")
    text = text.replace("__", "")

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

    if not isinstance(text, str):
        return [text]

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
# 🔥 CONTINUITY DETECTION
# =====================================================

def detect_multi_topic(
    cognition=None
):

    cognition = cognition or {}

    return cognition.get(
        "tracks_multiple_topics",
        False
    )


def detect_order_preservation(
    cognition=None
):

    cognition = cognition or {}

    return cognition.get(
        "preserve_question_order",
        False
    )


def detect_dialogue_alive(
    cognition=None
):

    cognition = cognition or {}

    return cognition.get(
        "dialogue_still_alive",
        False
    )


# =====================================================
# 🔥 SEMANTIC PACING
# =====================================================

def stabilize_semantic_flow(
    text,
    cognition=None
):

    cognition = cognition or {}

    # =================================================
    # 🔥 PRESERVE PAYLOADS
    # =====================================================

    if not isinstance(text, str):
        return text

    if not text:
        return ""

    sections = split_into_sections(
        text
    )

    if not sections:
        return text

    stabilized = []

    for section in sections:

        cleaned = section.strip()

        if not cleaned:
            continue

        cleaned = re.sub(
            r"\n{2,}",
            "\n",
            cleaned
        )

        stabilized.append(
            cleaned
        )

    return "\n\n".join(
        stabilized
    ).strip()


# =====================================================
# 🔥 ORDER STABILIZATION
# =====================================================

def preserve_response_order(
    text,
    cognition=None
):

    cognition = cognition or {}

    if not isinstance(text, str):
        return text

    if not text:
        return ""

    if not detect_order_preservation(
        cognition
    ):

        return text

    sections = split_into_sections(
        text
    )

    if not sections:
        return text

    ordered = []

    for section in sections:

        cleaned = section.strip()

        if cleaned:

            ordered.append(
                cleaned
            )

    return "\n\n".join(
        ordered
    ).strip()


# =====================================================
# 🔥 EMOJI DETECTION
# =====================================================

def detect_primary_emoji(text):

    if not isinstance(text, str):
        return None

    t = text.lower()

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

def apply_visual_enrichment(

    text,
    cognition=None
):

    cognition = cognition or {}

    # =================================================
    # 🔥 PRESERVE NON-TEXT
    # =====================================================

    if not isinstance(text, str):
        return text

    if not text:
        return ""

    if is_code_payload(text):
        return text

    if len(text) <= 60:
        return text

    restraint = cognition.get(
        "assistant_restraint",
        0.4
    )

    if restraint >= 0.7:
        return text

    emoji = detect_primary_emoji(
        text
    )

    if not emoji:
        return text

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

    # =================================================
    # 🔥 KEEP PAYLOADS SAFE
    # =====================================================

    if is_renderer_payload(text):

        safe_format_log(
            "RENDERER BYPASS"
        )

        return True

    if isinstance(text, (dict, list)):

        safe_format_log(
            "OBJECT BYPASS"
        )

        return True

    if not isinstance(text, str):
        return True

    if not text:
        return True

    if looks_like_json(text):

        safe_format_log(
            "JSON BYPASS"
        )

        return True

    if is_code_payload(text):

        safe_format_log(
            "CODE BYPASS"
        )

        return True

    return False


# =====================================================
# 🔥 LIGHT FORMAT
# =====================================================

def apply_light_formatting(

    text,
    cognition=None
):

    cognition = cognition or {}

    if not isinstance(text, str):
        return text

    sections = split_into_sections(
        text
    )

    if not sections:
        return text

    return "\n\n".join(
        sections
    ).strip()


# =====================================================
# 🔥 CONTINUITY VOICE
# =====================================================

def stabilize_dialogue_presence(
    text,
    cognition=None
):

    cognition = cognition or {}

    if not isinstance(text, str):
        return text

    if not text:
        return ""

    return text.strip()


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

    # =================================================
    # 🔥 KEEP PAYLOADS SAFE
    # =====================================================

    if should_skip_formatting(

        text,
        semantic,
        response_decision
    ):

        return text

    text = cleanup_markdown(
        text
    )

    text = stabilize_semantic_flow(
        text,
        cognition
    )

    text = preserve_response_order(
        text,
        cognition
    )

    text = apply_light_formatting(
        text,
        cognition
    )

    text = stabilize_dialogue_presence(
        text,
        cognition
    )

    text = apply_visual_enrichment(
        text,
        cognition
    )

    return text.strip()


# =====================================================
# 🔥 FINAL VOICE
# =====================================================

def apply_april_final_voice(

    text,
    cognition=None
):

    cognition = cognition or {}

    # =================================================
    # 🔥 KEEP PAYLOADS SAFE
    # =====================================================

    if not isinstance(text, str):
        return text

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

    # =================================================
    # 🔥 KEEP PAYLOADS SAFE
    # =====================================================

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
        formatted,
        cognition
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

    # =================================================
    # 🔥 PRESERVE RENDERER PAYLOAD
    # =====================================================

    if is_renderer_payload(final_text):

        safe_format_log(
            "FINAL RENDERER PAYLOAD PRESERVED"
        )

        return final_text

    # =================================================
    # 🔥 SAFE NORMALIZATION
    # =====================================================

    final_text = normalize_text_payload(
        final_text
    )

    # =================================================
    # 🔥 PAYLOAD SAFE
    # =====================================================

    if not isinstance(final_text, str):

        safe_format_log(
            "FINAL OBJECT PRESERVED"
        )

        return final_text

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
