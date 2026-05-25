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

    # =================================================
    # 🌐 INTERNET
    # =====================================================

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
# 🧠 PLATFORM LABELS
# =====================================================

PLATFORM_LABELS = [

    (
        r"https?://(www\.)?youtube\.com/[^\s]+",
        "▶️ YouTube"
    ),

    (
        r"https?://youtu\.be/[^\s]+",
        "▶️ YouTube"
    ),

    (
        r"https?://t\.me/[^\s]+",
        "📨 Telegram"
    ),

    (
        r"https?://(www\.)?instagram\.com/[^\s]+",
        "📸 Instagram"
    ),

    (
        r"https?://(www\.)?facebook\.com/[^\s]+",
        "📘 Facebook"
    ),

    (
        r"https?://(www\.)?twitter\.com/[^\s]+",
        "𝕏 Twitter"
    ),

    (
        r"https?://(www\.)?x\.com/[^\s]+",
        "𝕏 X"
    ),

    (
        r"https?://(www\.)?github\.com/[^\s]+",
        "💻 GitHub"
    ),

    (
        r"https?://(www\.)?wikipedia\.org/[^\s]+",
        "📚 Wikipedia"
    ),

    (
        r"https?://(www\.)?linkedin\.com/[^\s]+",
        "💼 LinkedIn"
    ),

    (
        r"https?://(www\.)?reddit\.com/[^\s]+",
        "👽 Reddit"
    ),

    (
        r"https?://(www\.)?tiktok\.com/[^\s]+",
        "🎬 TikTok"
    ),

    (
        r"https?://(www\.)?discord\.gg/[^\s]+",
        "🎮 Discord"
    )
]


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
        return "▶️ YouTube"

    if "youtu.be" in url:
        return "▶️ YouTube"

    if "t.me" in url:
        return "📨 Telegram"

    if "instagram.com" in url:
        return "📸 Instagram"

    if "facebook.com" in url:
        return "📘 Facebook"

    if "twitter.com" in url:
        return "𝕏 Twitter"

    if "x.com" in url:
        return "𝕏 X"

    if "github.com" in url:
        return "💻 GitHub"

    if "reddit.com" in url:
        return "👽 Reddit"

    if "linkedin.com" in url:
        return "💼 LinkedIn"

    if "tiktok.com" in url:
        return "🎬 TikTok"

    if "discord.gg" in url:
        return "🎮 Discord"

    return "🔗 Website"


# =====================================================
# 🌐 LINK CARD FORMATTER
# =====================================================

def build_link_card(
    url: str
):

    url = (
        url or ""
    ).strip()

    if not url:
        return ""

    lower = url.lower()

    if "desmos.com" in lower:
        return "📈 Открыть график"

    if (
        "youtube.com" in lower
        or "youtu.be" in lower
    ):

        return "▶️ Смотреть видео"

    if "github.com" in lower:
        return "💻 Открыть GitHub"

    if "wikipedia.org" in lower:
        return "📚 Читать статью"

    if "reddit.com" in lower:
        return "👽 Открыть обсуждение"

    if "instagram.com" in lower:
        return "📸 Открыть Instagram"

    if "t.me" in lower:
        return "📨 Открыть Telegram"

    return "🔗 Открыть ссылку"


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
        "▶️ YouTube:",
        "📨 Telegram:",
        "💻 GitHub:"
    ]

    return any(
        x in text
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

    # =================================================
    # 🔥 STRUCTURE SAFETY
    # =====================================================

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

    # =================================================
    # 🔥 RENDERER SAFETY
    # =====================================================

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

    # =================================================
    # 🔥 CODE SAFETY
    # =====================================================

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

    # =================================================
    # 🔥 RENDERER-FIRST
    # =====================================================

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

    if is_web_render_context(
        user_text
    ):

        if looks_like_visual_payload(
            text
        ):

            safe_format_log(
                "WEB RENDER BYPASS"
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
# 🧠 LINK BEAUTIFIER
# =====================================================

def beautify_links(
    text: str
):

    text = normalize_text_payload(text)

    if already_formatted(
        text
    ):

        return text

    urls = extract_urls(
        text
    )

    if not urls:
        return text

    for url in urls:

        if f"]({url})" in text:
            continue

        # =================================================
        # 🔥 SAFE LINK WRAPPING
        # =====================================================

        card = build_link_card(
            url
        )

        wrapped = (
            f"{card} ({url})"
        )

        text = text.replace(
            url,
            wrapped
        )

    return text


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

    # =================================================
    # 🔥 STRUCTURE SAFETY
    # =====================================================

    if is_scene_payload(text):
        return [text]

    if is_renderer_payload(text):
        return [text]

    if is_code_content(text):
        return [text]

    parts = []

    # =================================================
    # 🔥 SAFE SECTION SPLIT
    # =====================================================

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

    # =================================================
    # 🔥 HARD SAFETY
    # =====================================================

    if is_renderer_payload(text):
        return text

    if is_scene_payload(text):
        return text

    if is_code_content(text):
        return text

    if is_formula_payload(text):
        return text

    # =================================================
    # 🔥 ANTI-OVERDECORATION
    # =====================================================

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
# 🧠 MINI CARD FORMAT
# =====================================================

def build_mini_card(
    title: str,
    content: str
):

    title = (
        title or ""
    ).strip()

    content = (
        content or ""
    ).strip()

    if not content:
        return ""

    return (
        f"━━━ {title} ━━━\n"
        f"{content}"
    )


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

    # =================================================
    # 🔥 CRITICAL BYPASS
    # =====================================================

    if should_skip_formatting(

        text,
        user_text,
        semantic,
        response_decision
    ):

        return text

    # =================================================
    # 🔥 REALTIME
    # =====================================================

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
    # 🔥 DOUBLE FORMAT PROTECTION
    # =====================================================

    if already_formatted(
        text
    ):

        safe_format_log(
            "DOUBLE FORMAT BLOCKED"
        )

        return text

    # =================================================
    # 🔥 LIGHT LINK BEAUTIFY
    # =====================================================

    #text = beautify_links(
        #text
    #)

    # =================================================
    # 🔥 RESPONSE MODES
    # =====================================================

    if cognition.get(
        "reduce_talking"
    ):

        return apply_visual_enrichment(
            text
        )

    if semantic.get(
        "goal_stage"
    ) == "execution":

        return apply_visual_enrichment(

            apply_light_formatting(
                text
            )
        )

    if cognition.get(
        "exploration_mode"
    ):

        return apply_visual_enrichment(

            apply_light_formatting(
                text
            )
        )

    if response_decision.get(
        "should_offer_reference"
    ):

        return apply_visual_enrichment(

            apply_light_formatting(
                text
            )
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

    semantic = semantic or {}
    cognition = cognition or {}
    response_decision = (
        response_decision or {}
    )

    # =================================================
    # 🔥 HARD SAFETY
    # =====================================================

    if should_skip_formatting(

        text,
        "",
        semantic,
        response_decision
    ):

        return text

    emotional_mode = any([

        cognition.get(
            "emotional_mode"
        ),

        cognition.get(
            "reflection_mode"
        ),

        cognition.get(
            "relationship_mode"
        ),

        cognition.get(
            "support_mode"
        ),

        cognition.get(
            "conversation_mode"
        )
    ])

    robotic_lines = [

        "ничего подтверждённого найти не удалось",
        "подтверждённой информации не найдено",
        "информация не подтверждена",
        "не удалось подтвердить",
        "данные отсутствуют",
        "достоверной информации нет"
    ]

    if emotional_mode:

        cleaned_lines = []

        for line in text.split("\n"):

            line_lower = (
                line.lower().strip()
            )

            blocked = False

            for robotic in robotic_lines:

                if robotic in line_lower:

                    blocked = True

                    safe_format_log(

                        f"APRIL VOICE REMOVED: "
                        f"{line}"
                    )

                    break

            if not blocked:

                cleaned_lines.append(
                    line
                )

        text = "\n".join(
            cleaned_lines
        ).strip()

    # =================================================
    # 🔥 SAFE CLEANUP ONLY
    # =====================================================

    duplicate_system_phrases = [

        "⚠️ ⚠️",
        "✨ ✨",
        "не получилось не получилось"
    ]

    for phrase in duplicate_system_phrases:

        while phrase in text:

            text = text.replace(
                phrase,
                phrase.split()[0]
            )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    # =================================================
    # 🔥 DESTRUCTIVE REPLACEMENTS REMOVED
    # =====================================================

    # REMOVED:
    # "ошибка" -> ...
    # "невозможно" -> ...
    # "не удалось" -> ...

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

    # =================================================
    # 🔥 HARD RENDERER EXIT
    # =====================================================

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
    visual_reference = (
        visual_reference or {}
    )

    final_text = response or text

    final_text = normalize_text_payload(
        final_text
    )

    if not final_text:
        return final_text

    # =================================================
    # 🔥 FINAL RENDERER SAFETY
    # =====================================================

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
