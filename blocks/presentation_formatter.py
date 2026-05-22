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
"""

import re

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
# 🔥 WEB / UI DETECTION
# =====================================================

def is_web_render_context(user_text: str):

    t = (user_text or "").lower()

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
        "desmos"
    ]

    return any(
        x in t
        for x in web_words
    )


def looks_like_visual_payload(text: str):

    t = (text or "").lower()

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
        "data:image"
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
# 🌐 PLATFORM DETECTION
# =====================================================


def detect_platform_label(url: str):

    url = (url or "").lower()

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

def build_link_card(url: str):

    url = (url or "").strip()

    if not url:
        return ""

    lower = url.lower()

    if "desmos.com" in lower:
        return "📈 Открыть график"

    if "youtube.com" in lower or "youtu.be" in lower:
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

def extract_urls(text: str):

    text = text or ""

    pattern = r"https?://[^\s]+"

    return re.findall(
        pattern,
        text
    )


# =====================================================
# 🔥 CRITICAL CONTENT DETECTION
# =====================================================

def is_code_content(text: str):

    if not isinstance(text, str):
        return False

    if not text:
        return False

    checks = [
        "```",
        "<!DOCTYPE html>",
        "<html",
        "def ",
        "import ",
        "class "
    ]

    return any(
        x in text
        for x in checks
    )


def is_realtime_content(text: str):

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


def already_formatted(text: str):

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

    if already_formatted(text):
        return text

    urls = extract_urls(text)

    if not urls:
        return text

    for url in urls:

        if f"]({url})" in text:
            continue

        if "\n" + url in text:
            continue

        card = build_link_card(url)

        text = text.replace(
            url,
            card
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

def apply_light_formatting(text: str):

    sections = split_into_sections(text)

    if not sections:
        return text

    result = []

    for section in sections:
        result.append(section.strip())

    return "\n\n".join(result)


# =====================================================
# 🧠 VISUAL ENRICHMENT
# =====================================================

def apply_visual_enrichment(text: str):

    text = (text or "").strip()

    if not text:
        return text

    emoji = detect_primary_emoji(text)

    return f"{emoji} {text}"


# =====================================================
# 🧠 MINI CARD FORMAT
# =====================================================

def build_mini_card(title: str, content: str):

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
    response_decision: dict,
    user_text: str = ""
):

    semantic = semantic or {}
    cognition = cognition or {}
    response_decision = response_decision or {}

    text = (text or "").strip()

    if not text:
        return text

    # =================================================
    # 🔥 WEB VISUAL PROTECTION
    # =================================================

    if is_web_render_context(user_text):

        if looks_like_visual_payload(text):

            safe_format_log(
                "WEB VISUAL PAYLOAD BYPASS"
            )

            return text

    if is_code_content(text):

        safe_format_log(
            "CODE CONTENT SKIPPED"
        )

        return text

    if is_realtime_content(text):

        safe_format_log(
            "REALTIME CONTENT LIGHT MODE"
        )

        return apply_light_formatting(text)

    if already_formatted(text):

        safe_format_log(
            "DOUBLE FORMAT BLOCKED"
        )

        return text

    text = beautify_links(text)

    if cognition.get("reduce_talking"):
        return apply_visual_enrichment(text)

    if semantic.get("goal_stage") == "execution":
        return apply_visual_enrichment(
            apply_light_formatting(text)
        )

    if cognition.get("exploration_mode"):
        return apply_visual_enrichment(
            apply_light_formatting(text)
        )

    if response_decision.get("should_offer_reference"):
        return apply_visual_enrichment(
            apply_light_formatting(text)
        )

    return apply_visual_enrichment(
        apply_light_formatting(text)
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

    text = (text or "").strip()

    if not text:
        return text

    semantic = semantic or {}
    cognition = cognition or {}
    response_decision = response_decision or {}

    emotional_mode = any([
        cognition.get("emotional_mode"),
        cognition.get("reflection_mode"),
        cognition.get("relationship_mode"),
        cognition.get("support_mode"),
        cognition.get("conversation_mode")
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

            line_lower = line.lower().strip()

            blocked = False

            for robotic in robotic_lines:

                if robotic in line_lower:

                    blocked = True

                    safe_format_log(
                        f"APRIL VOICE REMOVED: {line}"
                    )

                    break

            if not blocked:
                cleaned_lines.append(line)

        text = "\n".join(
            cleaned_lines
        ).strip()

    replacements = {
        "⚠️": "✨",
        "ошибка": "небольшая проблема",
        "невозможно": "пока не получается",
        "не удалось": "не получилось"
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

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

    if not text:
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
    response_decision = response_decision or {}
    visual_reference = visual_reference or {}

    final_text = response or text

    if not final_text:
        return final_text

    return beautify_response(
        final_text,
        semantic,
        cognition,
        response_decision,
        user_text
    )
