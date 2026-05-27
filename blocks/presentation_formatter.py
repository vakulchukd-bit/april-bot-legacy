# =====================================================
# 🧠 APRIL PRESENTATION FORMATTER
# =====================================================

"""
APRIL SPACE PRESENTATION LAYER

BEHAVIOR-AWARE SAFE PRESENTATION PIPELINE

Этот слой теперь:

✅ НЕ ломает renderer payload
✅ НЕ сериализует scene objects
✅ НЕ flatten'ит multimodal blocks
✅ НЕ уничтожает graph/formula/code payload
✅ НЕ вмешивается в renderer execution
✅ НЕ мутирует artifact objects
✅ НЕ ломает future spatial architecture

И теперь дополнительно:

✅ понимает behavioral field
✅ регулирует плотность ответа
✅ suppress robotic rhythm
✅ stabilizes latent guidance
✅ controls pacing
✅ reduces dialogue bloat
✅ preserves calm continuity

Этот слой НЕ:
- personality prompt;
- emotional inflator;
- chatbot beautifier;
- corporate formatter.

Он теперь:
- behavior-aware formatter;
- continuity pacing layer;
- semantic density stabilizer;
- latent guidance presenter.
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
# 🔥 SAFE HELPERS
# =====================================================

def clamp(
    value,
    minimum=0.0,
    maximum=1.0
):

    if value < minimum:
        return minimum

    if value > maximum:
        return maximum

    return value


# =====================================================
# 🔥 SAFE PAYLOAD DETECTION
# =====================================================

def is_renderer_payload(value):

    if not isinstance(value, (dict, list)):
        return False

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

    if is_renderer_payload(value):

        safe_format_log(
            "RENDERER PAYLOAD PRESERVED"
        )

        return value

    if value is None:
        return ""

    if isinstance(value, str):
        return value

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
# 🔥 BEHAVIOR EXTRACTION
# =====================================================

def extract_behavior_field(
    cognition=None
):

    cognition = cognition or {}

    behavior = cognition.get(
        "behavior_state",
        {}
    )

    return {

        "response_density":

            behavior.get(
                "response_density",
                0.5
            ),

        "initiative_level":

            behavior.get(
                "initiative_level",
                0.35
            ),

        "latent_guidance":

            behavior.get(
                "latent_guidance",
                0.6
            ),

        "robotic_suppression":

            behavior.get(
                "robotic_suppression",
                0.9
            ),

        "humanization":

            behavior.get(
                "humanization",
                0.6
            ),

        "exploration_support":

            behavior.get(
                "exploration_support",
                0.5
            )
    }


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
# 🔥 DIALOG BLOAT SUPPRESSION
# =====================================================

def suppress_dialog_bloat(
    text,
    behavior=None
):

    behavior = behavior or {}

    if not isinstance(text, str):
        return text

    density = behavior.get(
        "response_density",
        0.5
    )

    if density >= 0.55:
        return text

    replacements = {

        "Я думаю, что": "",
        "Мне кажется, что": "",
        "Стоит отметить, что": "",
        "Можно сказать, что": "",
        "Важно понимать, что": "",
        "Следует отметить, что": ""
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

    return text.strip()


# =====================================================
# 🔥 ROBOTIC SUPPRESSION
# =====================================================

def suppress_robotic_phrasing(
    text,
    behavior=None
):

    behavior = behavior or {}

    if not isinstance(text, str):
        return text

    suppression = behavior.get(
        "robotic_suppression",
        0.9
    )

    if suppression < 0.5:
        return text

    robotic = [

        "Конечно!",
        "Отличный вопрос!",
        "Давай разберемся.",
        "Я готов помочь.",
        "Чем еще помочь?",
        "Буду рад помочь.",
        "С удовольствием."
    ]

    for phrase in robotic:

        text = text.replace(
            phrase,
            ""
        )

    return text.strip()


# =====================================================
# 🔥 LATENT GUIDANCE
# =====================================================

def stabilize_latent_guidance(
    text,
    behavior=None
):

    behavior = behavior or {}

    if not isinstance(text, str):
        return text

    guidance = behavior.get(
        "latent_guidance",
        0.6
    )

    if guidance < 0.65:
        return text

    sections = split_into_sections(
        text
    )

    if not sections:
        return text

    final = []

    for section in sections:

        cleaned = section.strip()

        if not cleaned:
            continue

        cleaned = re.sub(
            r"\?$",
            ".",
            cleaned
        )

        final.append(
            cleaned
        )

    return "\n\n".join(final)


# =====================================================
# 🔥 SEMANTIC PACING
# =====================================================

def stabilize_semantic_flow(
    text,
    behavior=None
):

    behavior = behavior or {}

    if not isinstance(text, str):
        return text

    if not text:
        return ""

    sections = split_into_sections(
        text
    )

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

    return None


# =====================================================
# 🔥 VISUAL ENRICHMENT
# =====================================================

def apply_visual_enrichment(
    text,
    behavior=None
):

    behavior = behavior or {}

    if not isinstance(text, str):
        return text

    if not text:
        return ""

    if is_code_payload(text):
        return text

    initiative = behavior.get(
        "initiative_level",
        0.35
    )

    if initiative <= 0.25:
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
# 🔥 FINAL VOICE
# =====================================================

def apply_april_final_voice(
    text,
    behavior=None
):

    behavior = behavior or {}

    if not isinstance(text, str):
        return text

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

    behavior = extract_behavior_field(
        cognition
    )

    if should_skip_formatting(
        text,
        semantic,
        response_decision
    ):

        return text

    text = cleanup_markdown(
        text
    )

    text = suppress_robotic_phrasing(
        text,
        behavior
    )

    text = suppress_dialog_bloat(
        text,
        behavior
    )

    text = stabilize_latent_guidance(
        text,
        behavior
    )

    text = stabilize_semantic_flow(
        text,
        behavior
    )

    text = apply_visual_enrichment(
        text,
        behavior
    )

    text = apply_april_final_voice(
        text,
        behavior
    )

    return text


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

    if is_renderer_payload(final_text):

        safe_format_log(
            "FINAL RENDERER PAYLOAD PRESERVED"
        )

        return final_text

    final_text = normalize_text_payload(
        final_text
    )

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
