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
"""

import re


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
    # =================================================

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
# 🧠 KEYWORD EMOJI DETECTION
# =====================================================

def detect_primary_emoji(text: str):

    t = (text or "").lower()

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

def beautify_links(text: str):

    text = text or ""

    for pattern, replacement in PLATFORM_LABELS:

        text = re.sub(
            pattern,
            replacement,
            text
        )

    return text


# =====================================================
# 🧠 SECTION SPLITTER
# =====================================================

def split_into_sections(text: str):

    text = (text or "").strip()

    if not text:
        return []

    parts = []

    for block in text.split("\n"):

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

    text = (text or "").strip()

    if not text:
        return text

    emoji = detect_primary_emoji(
        text
    )

    return (
        f"{emoji} "
        + text
    )


# =====================================================
# 🧠 MINI CARD FORMAT
# =====================================================

def build_mini_card(
    title: str,
    content: str
):

    title = (title or "").strip()
    content = (content or "").strip()

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
    response_decision: dict
):

    semantic = semantic or {}
    cognition = cognition or {}
    response_decision = response_decision or {}

    text = (text or "").strip()

    if not text:
        return text

    text = beautify_links(text)

    # =================================================
    # 🔥 REDUCE TALKING MODE
    # =================================================

    if cognition.get(
        "reduce_talking"
    ):

        return apply_visual_enrichment(
            text
        )

    # =================================================
    # 🔥 EXECUTION MODE
    # =================================================

    if semantic.get(
        "goal_stage"
    ) == "execution":

        return apply_visual_enrichment(
            apply_light_formatting(
                text
            )
        )

    # =================================================
    # 🔥 EXPLORATION MODE
    # =================================================

    if cognition.get(
        "exploration_mode"
    ):

        return apply_visual_enrichment(
            apply_light_formatting(
                text
            )
        )

    # =================================================
    # 🔥 VISUAL GUIDANCE
    # =================================================

    if response_decision.get(
        "should_offer_reference"
    ):

        return apply_visual_enrichment(
            apply_light_formatting(
                text
            )
        )

    # =================================================
    # 🔥 DEFAULT
    # =================================================

    return apply_visual_enrichment(
        apply_light_formatting(
            text
        )
    )


# =====================================================
# 🧠 RESPONSE BEAUTIFIER
# =====================================================

def beautify_response(
    text: str,
    semantic: dict,
    cognition: dict,
    response_decision: dict
):

    if not text:
        return text

    formatted = build_smart_presentation(
        text,
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
    response_decision = response_decision or {}
    visual_reference = visual_reference or {}

    final_text = response or text

    if not final_text:
        return final_text

    return beautify_response(
        final_text,
        semantic,
        cognition,
        response_decision
    )
