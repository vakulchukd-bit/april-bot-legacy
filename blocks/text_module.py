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

from openai import OpenAI

from storage import get_user_plan
from blocks.ai_config import TEXT_MODEL

client = OpenAI()

# =====================================================
# 🧠 SYSTEM PROMPT
# =====================================================

SYSTEM_PROMPT = (
    "Ты — Aprill. "
    "Ты не trigger-бот. "
    "Ты cognitive assistant. "

    "Главная задача — понимать trajectory человека "
    "и помогать ему прийти к результату. "

    "Не болтай впустую. "
    "Не перехватывай инициативу без необходимости. "
    "Не превращай любое подтверждение "
    "в автоматическое execution-действие. "

    "Если пользователь исследует идею — "
    "помогай исследовать. "

    "Если пользователь уже знает направление — "
    "следуй за ним. "

    "Если человек запутался — "
    "объясняй проще и мягче. "

    "Если нужен результат — "
    "не затягивай. "

    "Используй visual references "
    "как помощь мышлению, "
    "а не замену общения. "

    "Не теряй trajectory диалога. "
    "Продолжай мысль естественно. "

    "Не начинай разговор заново. "
    "Не ломай атмосферу. "
    "Не уходи в роботизированные ответы. "

    "Говори естественно. "
    "Кратко. "
    "Человечно. "
    "По делу."
)

# =====================================================
# 🔥 LIMITS
# =====================================================

MAX_MESSAGE_CHARS = 900
MAX_TOTAL_CHARS = 5000

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
            "temperature": 0.9,
            "max_output_tokens": 700
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
        "lite": 6,
        "premium": 12

    }.get(plan, 6)


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

    return None


def update_topic(state, text):

    topic = extract_topic(text)

    if topic:

        state["topic"] = topic


# =====================================================
# 🧠 RESPONSE DECISION HINT
# =====================================================

def build_response_decision_hint(
    response_decision
):

    if not response_decision:
        return ""

    hints = []

    if response_decision.get(
        "should_follow_user"
    ):

        hints.append(
            "Следуй за пользователем."
        )

    if response_decision.get(
        "should_reduce_talking"
    ):

        hints.append(
            "Отвечай короче."
        )

    if response_decision.get(
        "should_offer_reference"
    ):

        hints.append(
            "Лучше visual guidance, "
            "а не heavy generation."
        )

    if response_decision.get(
        "should_continue_trajectory"
    ):

        hints.append(
            "Продолжай trajectory."
        )

    return " ".join(hints)


# =====================================================
# 🧠 HUMANITY LAYER
# =====================================================

def build_human_layer(
    semantic,
    cognition,
    response_decision
):

    hints = []

    if cognition.get(
        "is_confused",
        0.0
    ) >= 0.6:

        hints.append(
            "Объясняй проще."
        )

    if cognition.get(
        "is_frustrated",
        0.0
    ) >= 0.6:

        hints.append(
            "Не растягивай."
        )

    if cognition.get(
        "user_leads_direction"
    ):

        hints.append(
            "Пользователь уже ведёт направление."
        )

    if cognition.get(
        "exploration_mode"
    ):

        hints.append(
            "Помогай исследовать идею."
        )

    if semantic.get(
        "goal_stage"
    ) == "execution":

        hints.append(
            "Пользователь ждёт результат."
        )

    decision_hint = (
        build_response_decision_hint(
            response_decision
        )
    )

    if decision_hint:

        hints.append(
            decision_hint
        )

    return " ".join(hints)


# =====================================================
# 🔥 VISUAL GUIDANCE
# =====================================================

def build_visual_hint(
    visual_reference
):

    if not visual_reference:
        return ""

    hints = []

    if visual_reference.get(
        "enabled"
    ):

        if visual_reference.get(
            "lightweight_mode"
        ):

            hints.append(
                "Используй лёгкие визуальные ориентиры."
            )

    if visual_reference.get(
        "guidance"
    ):

        hints.append(
            visual_reference.get(
                "guidance"
            )
        )

    return " ".join(hints)


# =====================================================
# 🧠 CONTEXT BLOCK
# =====================================================

def build_context_block(
    state,
    history,
    text,
    plan,
    semantic,
    cognition,
    visual_reference,
    response_decision
):

    parts = []

    topic = state.get(
        "topic"
    )

    if topic:

        parts.append(
            f"Текущая тема: {topic}"
        )

    # =================================================
    # 🔥 ACTIVE FLOW
    # =================================================

    active_flow = state.get(
        "active_flow"
    )

    if active_flow:

        flow_type = active_flow.get(
            "type"
        )

        if flow_type:

            parts.append(
                f"Текущий trajectory: {flow_type}"
            )

    # =================================================
    # 🔥 MEMORY SUMMARY
    # =================================================

    summary = state.get(
        "memory_summary"
    )

    if summary:

        parts.append(
            "Сжатая память: "
            + summary[-400:]
        )

    # =================================================
    # 🔥 RECENT USER CONTEXT
    # =================================================

    recent = []

    for msg in history[-4:]:

        if msg.get("role") == "user":

            recent.append(
                msg.get(
                    "content",
                    ""
                )[:80]
            )

    if recent:

        parts.append(
            "Недавний контекст: "
            + " | ".join(recent)
        )

    # =================================================
    # 🔥 HUMANITY
    # =================================================

    human_layer = build_human_layer(
        semantic,
        cognition,
        response_decision
    )

    if human_layer:

        parts.append(
            human_layer
        )

    # =================================================
    # 🔥 VISUAL
    # =================================================

    visual_hint = build_visual_hint(
        visual_reference
    )

    if visual_hint:

        parts.append(
            visual_hint
        )

    # =================================================
    # 🔥 PREMIUM
    # =================================================

    if plan == "premium":

        parts.append(
            "Максимально естественный стиль."
        )

    return ". ".join(parts)


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

    async def run():

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

            # =============================================
            # 🔥 READY CONTEXT
            # =============================================

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

                plan = get_user_plan(
                    user_id
                )

                limit = get_history_limit(
                    plan
                )

                context_block = (
                    build_context_block(

                        state,
                        history,
                        text_fixed,
                        plan,
                        semantic,
                        cognition,
                        visual_reference,
                        response_decision
                    )
                )

                system_full = (
                    SYSTEM_PROMPT
                    + "\n\n"
                    + context_block
                )

                messages = [

                    {
                        "role": "system",
                        "content": system_full
                    }
                ]

                safe_history = [

                    {
                        "role":
                            m.get("role"),

                        "content":
                            trim_text(
                                m.get(
                                    "content",
                                    ""
                                )
                            )
                    }

                    for m in history[-limit:]
                ]

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

            # =============================================
            # 🔥 CONFIG
            # =============================================

            config = get_config(
                energy
            )

            # =============================================
            # 🔥 OPENAI
            # =============================================

            r = client.responses.create(

                model=TEXT_MODEL,

                input=messages,

                temperature=config[
                    "temperature"
                ],

                max_output_tokens=config[
                    "max_output_tokens"
                ]
            )

            output = r.output_text

            if not output:

                output = (
                    "⚠️ Пустой ответ."
                )

            return output

        except Exception as e:

            traceback.print_exc()

            return (
                "⚠️ Ошибка текстового модуля: "
                + str(e)
            )

    # =================================================
    # 🔥 EXECUTION
    # =================================================

    reply = await asyncio.to_thread(
        lambda: asyncio.run(run())
    )

    # =================================================
    # 🔥 CODE STORE
    # =================================================

    if "```" in reply:

        state["last_code"] = reply

    # =================================================
    # 🔥 ENHANCE CODE
    # =================================================

    reply = enhance_code_block(
        reply
    )

    # =================================================
    # 🔥 LOOP PROTECTION
    # =================================================

    reply = prevent_repeat_response(
        state,
        reply
    )

    # =================================================
    # 🔥 SAVE LAST REPLY
    # =================================================

    state["last_reply"] = reply

    state["last_text_time"] = time.time()

    return {

        "type": "text",

        "content": reply
    }
