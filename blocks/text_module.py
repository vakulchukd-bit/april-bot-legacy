# =====================================================
# 🧠 APRIL TEXT MODULE
# =====================================================

# =====================================================
# 🔥 SAFE PATCH MODE
# =====================================================

PATCH_LOG = []

def safe_patch_log(msg):
    try:
        print("TEXT PATCH:", msg)
        PATCH_LOG.append(msg)
    except:
        pass


def patch_text_input(text):
    safe_patch_log(f"TEXT INPUT: {text[:80]}")
    return text


def patch_text_future(*args, **kwargs):
    return None


# =====================================================
# 🔥 IMPORTS
# =====================================================

import asyncio
import random
import re
import traceback
import time

from storage import get_user_plan
from blocks.ai_config import TEXT_MODEL
from blocks.provider_router import (
    generate_text
)

# =====================================================
# 🧠 EXTERNAL KNOWLEDGE
# =====================================================

from blocks.external_knowledge_provider import (

    should_use_external_knowledge,

    fetch_external_knowledge,

    enrich_with_external_knowledge
)

# =====================================================
# 🧠 PRESENTATION FORMATTER
# =====================================================

from blocks.presentation_formatter import (
    beautify_response
)

# =====================================================
# 🧠 SYSTEM PROMPT
# =====================================================

SYSTEM_PROMPT = (
    "Ты — April. "

    "Ты calm mobile-first AI assistant. "

    "Ты удерживаешь continuity диалога, "
    "понимаешь trajectory общения "
    "и помогаешь человеку спокойно "
    "и понятно. "

    "Не отвечай механически. "
    "Не перегружай пользователя. "
    "Не используй лишние объяснения. "

    "Ты умеешь помогать с: "
    "текстом, reasoning, кодом, "
    "математикой, изображениями, "
    "скриншотами, OCR, "
    "повседневными вопросами "
    "и визуальными сценами. "

    "Если пользователь продолжает "
    "обсуждать изображение — "
    "сохраняй visual continuity. "

    "Renderer-space важнее "
    "heavy image generation. "

    "Не создавай изображения "
    "без прямого запроса. "

    "Говори естественно. "
    "Человечно. "
    "Кратко и полезно."
)

# =====================================================
# 🔥 LIMITS
# =====================================================

MAX_MESSAGE_CHARS = 700
MAX_TOTAL_CHARS = 3200

# =====================================================
# 🔥 INTERNAL LEAK PROTECTION
# =====================================================

SYSTEM_LEAK_PATTERNS = [

    "ты calm mobile-first ai assistant",
    "renderer-space важнее",
    "heavy image generation",
    "trajectory общения",
    "не отвечай механически",
    "говори естественно",
    "personality_active",
    "response_decision",
    "execution_pressure",
    "cognition",
    "semantic",
    "system_prompt",
    "assistant_restraint",
    "continuity диалога",
    "visual continuity",
    "апril presentation principles",
    "capability_map",
    "reasoning_state",
    "trajectory protection",
    "response_mode",
    "internal_noise",
    "signal_overload",
    "active_flow_strength"
]


def sanitize_model_output(text):

    if not text:
        return ""

    text = str(text)

    lower = text.lower()

    leak_hits = 0

    for pattern in SYSTEM_LEAK_PATTERNS:

        if pattern in lower:
            leak_hits += 1

    # =================================================
    # 🔥 HARD LEAK DETECTION
    # =====================================================

    if leak_hits >= 2:

        safe_patch_log(
            "SYSTEM LEAK DETECTED"
        )

        return (
            "Похоже, ответ сформировался "
            "нестабильно. Попробуй "
            "переформулировать запрос."
        )

    # =================================================
    # 🔥 REMOVE RAW SYSTEM FRAGMENTS
    # =====================================================

    cleaned_lines = []

    blocked_prefixes = [

        "ты — april",
        "system:",
        "assistant:",
        "developer:",
        "personality:",
        "instructions:",
        "response_decision:",
        "semantic:",
        "cognition:"
    ]

    for line in text.split("\n"):

        stripped = line.strip().lower()

        blocked = False

        for prefix in blocked_prefixes:

            if stripped.startswith(prefix):

                blocked = True

                safe_patch_log(
                    f"REMOVED SYSTEM LINE: {line[:60]}"
                )

                break

        if not blocked:
            cleaned_lines.append(line)

    cleaned = "\n".join(
        cleaned_lines
    ).strip()

    # =================================================
    # 🔥 DUPLICATE META CLEANUP
    # =====================================================

    cleaned = re.sub(
        r"(говори естественно\.?\s*){2,}",
        "Говори естественно. ",
        cleaned,
        flags=re.IGNORECASE
    )

    cleaned = re.sub(
        r"(не отвечай механически\.?\s*){2,}",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    return cleaned.strip()


# =====================================================
# 🔥 DETECTORS
# =====================================================

def is_context_prompt(text):

    return (
        "Текущий запрос:" in text
        and "Диалог:" in text
    )


def is_short(text):

    return len(
        (text or "").strip()
    ) <= 3


def is_problem(text):

    t = text.lower()

    return (
        "=" in t
        or "реши" in t
        or "график" in t
        or "+" in t
        or "-" in t
        or "*" in t
        or "/" in t
    )


def is_strict_math(text):

    t = text.lower()

    return (
        "=" in t
        or "sin(" in t
        or "cos(" in t
        or "tan(" in t
        or "график" in t
    )


def is_sales_text(text):

    triggers = [
        "клиент",
        "продай",
        "убеди",
        "заказ",
        "покуп"
    ]

    t = text.lower()

    return any(
        x in t
        for x in triggers
    )


def is_edit_request(text):

    t = text.lower()

    triggers = [
        "измени",
        "добавь",
        "убери",
        "замени",
        "исправь"
    ]

    return any(
        x in t
        for x in triggers
    )


# =====================================================
# 🔥 TEXT LIMITERS
# =====================================================

def trim_text(text):

    if not text:
        return ""

    text = str(text)

    if len(text) > MAX_MESSAGE_CHARS:

        return (
            text[:MAX_MESSAGE_CHARS]
            + "…"
        )

    return text


def trim_messages(messages):

    total = 0

    result = []

    for msg in reversed(messages):

        content = trim_text(
            msg.get("content", "")
        )

        total += len(content)

        if total > MAX_TOTAL_CHARS:
            break

        result.append({

            "role":
                msg.get("role", "user"),

            "content":
                content
        })

    return list(
        reversed(result)
    )


# =====================================================
# 🔥 ENERGY CONFIG
# =====================================================

def get_config(energy):

    if energy == "LOW":

        return {
            "temperature": 0.5,
            "max_output_tokens": 180
        }

    if energy == "HIGH":

        return {
            "temperature": 0.85,
            "max_output_tokens": 650
        }

    return {
        "temperature": 0.7,
        "max_output_tokens": 350
    }


# =====================================================
# 🔥 HISTORY LIMIT
# =====================================================

def get_history_limit(plan):

    return {

        "free": 3,
        "lite": 5,
        "premium": 8

    }.get(plan, 5)


# =====================================================
# 🔥 TOPIC MEMORY
# =====================================================

def extract_topic(text):

    t = text.lower()

    if "сайт" in t and "кафе" in t:
        return "website_cafe"

    if "сайт" in t:
        return "website"

    if "бот" in t:
        return "bot"

    if "дизайн" in t:
        return "design"

    if "путешеств" in t:
        return "travel"

    if "город" in t:
        return "city"

    if "новост" in t:
        return "news"

    return None


def update_topic(state, text):

    topic = extract_topic(text)

    if topic:

        state["topic"] = topic


# =====================================================
# 🧠 LIGHT COGNITIVE STATE
# =====================================================

def build_cognitive_state(
    state,
    text,
    semantic,
    cognition,
    visual_reference,
    response_decision
):

    blocks = []

    active_flow = state.get(
        "active_flow"
    )

    if active_flow:

        flow_type = active_flow.get(
            "type"
        )

        if flow_type:

            blocks.append(
                f"Trajectory: {flow_type}"
            )

    user_state = []

    if cognition.get(
        "is_frustrated",
        0.0
    ) >= 0.6:

        user_state.append(
            "пользователь раздражён"
        )

    if cognition.get(
        "exploration_mode"
    ):

        user_state.append(
            "исследует идею"
        )

    if user_state:

        blocks.append(
            "Состояние: "
            + ", ".join(user_state)
        )

    behavior = []

    if response_decision.get(
        "should_reduce_talking"
    ):

        behavior.append(
            "отвечай кратко"
        )

    if response_decision.get(
        "should_continue_trajectory"
    ):

        behavior.append(
            "сохраняй continuity"
        )

    if semantic.get(
        "goal_stage"
    ) == "execution":

        behavior.append(
            "пользователь ждёт результат"
        )

    if behavior:

        blocks.append(
            "Поведение: "
            + ", ".join(behavior)
        )

    active_visual_scene = state.get(
        "active_visual_scene"
    )

    if active_visual_scene:

        scene_type = active_visual_scene.get(
            "scene_type",
            "unknown"
        )

        scene_objects = active_visual_scene.get(
            "objects",
            []
        )

        visual_lines = [

            "Активная visual scene.",

            f"Тип: {scene_type}"
        ]

        if scene_objects:

            visual_lines.append(

                "Objects: "
                + ", ".join(scene_objects[:8])
            )

        visual_lines.append(
            "Сохраняй visual continuity."
        )

        blocks.append(
            "\n".join(visual_lines)
        )

    summary = state.get(
        "memory_summary"
    )

    if summary:

        blocks.append(
            "Память: "
            + summary[-180:]
        )

    return "\n".join(blocks)


# =====================================================
# 🔥 LINK ENHANCEMENT
# =====================================================

def enhance_link_behavior(text):

    t = text.lower()

    if (
        "ссылка" in t
        and "http" not in t
    ):

        return (
            text
            + "\n\nПример: https://example.com"
        )

    return text


# =====================================================
# 🔥 REQUEST ENRICH
# =====================================================

def enrich_request(text, state):

    if (
        "график" in text.lower()
        and "сайт" in (
            state.get("topic") or ""
        )
    ):

        return (
            text
            + " (вставь график в HTML)"
        )

    return text


# =====================================================
# 🔥 HTML HELPERS
# =====================================================

def clean_html(text):

    t = text.strip()

    t = re.sub(
        r"```html\s*```html",
        "```html",
        t
    )

    if "<!DOCTYPE html>" in t:

        t = t[
            t.index("<!DOCTYPE html>"):
        ]

    return t


def add_html_comments(html):

    if "<!--" in html:
        return html

    html = html.replace(

        "<body>",

        "<body>\n"
        "    <!-- Основное содержимое -->"
    )

    return html


# =====================================================
# 🔥 CODE ENHANCE
# =====================================================

def enhance_code_block(text):

    if not text:
        return text

    t = text.strip()

    if (
        "<html" in t
        or "<!DOCTYPE html>" in t
    ):

        t = clean_html(t)

        t = add_html_comments(t)

        return (
            "```html\n"
            + t
            + "\n```"
        )

    if (
        "def " in t
        or "import " in t
    ):

        return (
            "```python\n"
            + t
            + "\n```"
        )

    return t


# =====================================================
# 🔥 LOOP PROTECTION
# =====================================================

def prevent_repeat_response(
    state,
    reply
):

    last = state.get(
        "last_reply"
    )

    if not last:
        return reply

    if last.strip() == reply.strip():

        return (
            reply
            + "\n\n(продолжаю мысль)"
        )

    return reply


# =====================================================
# 🧠 VISUAL BEAUTIFY
# =====================================================

def apply_visual_beautify(
    text,
    semantic,
    cognition
):

    if not text:
        return text

    # =================================================
    # 🔥 RENDERER SAFETY
    # =====================================================

    if any(
        x in text
        for x in [

            "[[graph",
            "[[formula",
            "[[diagram",
            "<svg",
            "<canvas"
        ]
    ):

        return text

    beautified = text

    if semantic.get(
        "topic_category"
    ) == "travel":

        beautified = (
            "🌍 "
            + beautified
        )

    if semantic.get(
        "topic_category"
    ) == "history":

        beautified = (
            "🏛 "
            + beautified
        )

    if semantic.get(
        "topic_category"
    ) == "technology":

        beautified = (
            "⚙️ "
            + beautified
        )

    return beautified


# =====================================================
# 🔥 MAIN PROCESS
# =====================================================

async def process(
    user_id,
    text,
    state,
    energy="MEDIUM"
):

    text = patch_text_input(
        text
    )

    try:

        semantic = state.get(
            "semantic",
            {}
        )

        cognition = state.get(
            "cognition",
            {}
        )

        visual_reference = state.get(
            "visual_reference",
            {}
        )

        response_decision = state.get(
            "response_decision",
            {}
        )

        if is_context_prompt(text):

            messages = [

                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },

                {
                    "role": "user",
                    "content": text
                }
            ]

        else:

            history = state.get(
                "dialog",
                []
            )

            update_topic(
                state,
                text
            )

            text_fixed = enrich_request(

                enhance_link_behavior(
                    text
                ),

                state
            )

            # =============================================
            # 🔥 ANTI-SYSTEM-INJECTION
            # =============================================

            text_fixed = sanitize_model_output(
                text_fixed
            )

            plan = get_user_plan(
                user_id
            )

            limit = get_history_limit(
                plan
            )

            cognitive_state = (
                build_cognitive_state(
                    state,
                    text_fixed,
                    semantic,
                    cognition,
                    visual_reference,
                    response_decision
                )
            )

            # =============================================
            # 🔥 SAFE SYSTEM STATE
            # =============================================

            safe_cognitive_state = trim_text(
                cognitive_state
            )

            system_full = (
                SYSTEM_PROMPT
                + "\n\n"
                + safe_cognitive_state
            )

            messages = [

                {
                    "role": "system",
                    "content": trim_text(
                        system_full
                    )
                }
            ]

            safe_history = []

            for m in history[-limit:]:

                content = sanitize_model_output(

                    trim_text(
                        m.get(
                            "content",
                            ""
                        )
                    )
                )

                if not content:
                    continue

                safe_history.append({

                    "role":
                        m.get("role"),

                    "content":
                        content
                })

            messages.extend(

                trim_messages(
                    safe_history
                )
            )

            messages.append({

                "role": "user",

                "content":
                    trim_text(
                        text_fixed
                    )
            })

        config = get_config(
            energy
        )

        # =============================================
        # 🔥 OPENAI TEXT-FIRST
        # =============================================

        output = await generate_text(

            messages=messages,

            temperature=config[
                "temperature"
            ],

            max_output_tokens=config[
                "max_output_tokens"
            ],

            model="gpt-4o-mini"
        )

        # =============================================
        # 🔥 OUTPUT SANITIZATION
        # =============================================

        output = sanitize_model_output(
            output
        )

        # =============================================
        # 🧠 EXTERNAL KNOWLEDGE
        # =============================================

        if should_use_external_knowledge(
            text,
            semantic,
            cognition,
            response_decision
        ):

            knowledge = fetch_external_knowledge(
                text,
                semantic,
                cognition
            )

            output = enrich_with_external_knowledge(
                output,
                knowledge
            )

        # =============================================
        # 🧠 RESPONSE STABILIZATION
        # =============================================

        if cognition.get(
            "user_leads_direction"
        ):

            if len(output) > 700:

                output = (
                    output[:700]
                    + "\n\n"
                    + "(не перегружаю ответ)"
                )

        if cognition.get(
            "exploration_mode"
        ):

            robotic_phrases = [

                "конечно",
                "давай разберём",
                "отличный вопрос",
                "я помогу"
            ]

            cleaned = output

            for phrase in robotic_phrases:

                cleaned = re.sub(
                    phrase,
                    "",
                    cleaned,
                    flags=re.IGNORECASE
                )

            output = cleaned.strip()

        if not output:

            output = (
                "⚠️ Пустой ответ."
            )

    except Exception as e:

        traceback.print_exc()

        output = (
            "⚠️ Ошибка текстового модуля: "
            + str(e)
        )

    if "```" in output:

        state["last_code"] = output

    reply = enhance_code_block(
        output
    )

    reply = prevent_repeat_response(
        state,
        reply
    )

    semantic = state.get(
        "semantic",
        {}
    )

    cognition = state.get(
        "cognition",
        {}
    )

    response_decision = state.get(
        "response_decision",
        {}
    )

    reply = beautify_response(
        reply,
        semantic,
        cognition,
        response_decision
    )

    reply = apply_visual_beautify(
        reply,
        semantic,
        cognition
    )

    # =================================================
    # 🔥 FINAL SAFETY CLEAN
    # =====================================================

    reply = sanitize_model_output(
        reply
    )

    state["last_reply"] = reply

    state["last_text_time"] = time.time()

    return {

        "type": "text",

        "content": reply
    }
