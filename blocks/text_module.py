# ===============================
# 🔥 SAFE PATCH MODE (TEXT MODULE)
# ===============================

PATCH_LOG = []

def safe_patch_log(msg):
    try:
        print("TEXT PATCH:", msg)
        PATCH_LOG.append(msg)
    except:
        pass


# 🔥 PATCH: контроль текстовой обработки
def patch_text_input(text):
    safe_patch_log(f"TEXT INPUT: {text[:50]}")
    return text


# 🔥 PATCH: будущая логика текста
def patch_text_future(*args, **kwargs):
    return None


import asyncio
import random
import re

from openai import OpenAI

from storage import get_user_plan
from blocks.ai_config import TEXT_MODEL

client = OpenAI()

# =====================================================
# 🧠 SYSTEM PROMPT
# =====================================================

SYSTEM_PROMPT = (
    "Ты — Aprill, живой cognitive assistant. "
    "Главная цель — помогать человеку прийти к результату. "
    "Не болтай впустую. "
    "Если человеку нужен пример — покажи направление. "
    "Если нужен визуал — предложи визуальный путь. "
    "Если пользователь сам уверенно ведёт задачу — не мешай. "
    "Если человек запутался — мягко направь. "
    "Говори естественно, кратко и по делу. "
    "Избегай лишней болтовни. "
    "Поддерживай trajectory диалога. "
    "Продолжай текущую мысль, а не начинай заново. "
    "Не теряй контекст."
)

# =====================================================
# 🔥 CONTEXT DETECTION
# =====================================================

def is_context_prompt(text):
    return (
        "Текущий запрос:" in text
        and "Диалог:" in text
    )


# =====================================================
# 🔥 BASIC DETECTORS
# =====================================================

def is_vague(text):

    vague = [
        "что-нибудь",
        "что то",
        "что-то",
        "сделай",
        "придумай"
    ]

    return any(
        x in text.lower()
        for x in vague
    )


def is_short(text):
    return len(text.strip()) <= 3


def build_behavior_hint(text):
    return ""


def is_problem(text):

    t = text.lower()

    return (
        any(
            sym in t
            for sym in [
                "=",
                "+",
                "-",
                "*",
                "/",
                "^"
            ]
        )
        or "реши" in t
        or "график" in t
    )


def is_strict_math(text):

    t = text.lower()

    return (
        "=" in t
        or "график" in t
        or "sin(" in t
        or "cos(" in t
        or any(
            op in t
            for op in [
                "+",
                "-",
                "*",
                "/"
            ]
        )
    )


def is_sales_text(text):

    triggers = [
        "клиент",
        "продай",
        "убеди",
        "сомневается",
        "покуп",
        "заказ"
    ]

    return any(
        w in text.lower()
        for w in triggers
    )


def is_edit_request(text):

    t = text.lower()

    triggers = [
        "измени",
        "добавь",
        "убери",
        "сделай",
        "замени",
        "исправь"
    ]

    return any(
        w in t
        for w in triggers
    )


# =====================================================
# 🔥 LIMITS
# =====================================================

MAX_MESSAGE_CHARS = 600
MAX_TOTAL_CHARS = 3000


def trim_text(text):

    if not text:
        return ""

    text = str(text)

    if len(text) > MAX_MESSAGE_CHARS:

        return text[:MAX_MESSAGE_CHARS] + "…"

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
            "role": msg["role"],
            "content": content
        })

    return list(reversed(result))


# =====================================================
# 🔥 ENERGY CONFIG
# =====================================================

def get_config(energy):

    if energy == "LOW":

        return {
            "temperature": 0.5,
            "max_output_tokens": 150
        }

    if energy == "MEDIUM":

        return {
            "temperature": 0.7,
            "max_output_tokens": 300
        }

    if energy == "HIGH":

        return {
            "temperature": 0.9,
            "max_output_tokens": 500
        }

    return {
        "temperature": 0.6,
        "max_output_tokens": 250
    }


# =====================================================
# 🔥 HELPERS
# =====================================================

def enhance_link_behavior(text):

    t = text.lower()

    if "ссылка" in t and "http" not in t:

        return (
            text
            + "\n\nПример: https://example.com"
        )

    return text


def get_history_limit(plan):

    return {
        "free": 2,
        "lite": 4,
        "premium": 8
    }.get(plan, 4)


# =====================================================
# 🔥 TOPIC MEMORY
# =====================================================

def extract_topic(text):

    t = text.lower()

    if "сайт" in t and "кафе" in t:
        return "сайт кафе"

    if "сайт" in t:
        return "создание сайта"

    if "приложение" in t:
        return "создание приложения"

    return None


def update_topic(state, text):

    topic = extract_topic(text)

    if topic:
        state["topic"] = topic


# =====================================================
# 🔥 CONTEXT BLOCK
# =====================================================

def build_context_block(
    state,
    history,
    text,
    energy,
    plan,
    semantic,
    cognition
):

    parts = []

    topic = state.get("topic")

    if topic:

        parts.append(
            f"Текущая задача: {topic}"
        )

    last = [

        m["content"][:40]

        for m in history[-3:]

        if m["role"] == "user"
    ]

    if last:

        parts.append(
            "Контекст: "
            + " | ".join(last)
        )

    # =================================================
    # 🔥 RESPONSE ECONOMY
    # =================================================

    response_economy = semantic.get(
        "response_economy",
        "balanced"
    )

    if response_economy == "minimal":

        parts.append(
            "Отвечай коротко и по делу."
        )

    elif response_economy == "expanded":

        parts.append(
            "Можно чуть подробнее."
        )

    # =================================================
    # 🔥 EXECUTION PRESSURE
    # =================================================

    if semantic.get(
        "execution_pressure",
        0.0
    ) >= 0.7:

        parts.append(
            "Меньше разговоров. Больше результата."
        )

    # =================================================
    # 🔥 VISUAL GUIDANCE
    # =================================================

    if semantic.get(
        "should_offer_visual"
    ):

        parts.append(
            "Если поможет пониманию — "
            "предложи визуальный пример "
            "или направление."
        )

    # =================================================
    # 🔥 EXAMPLES
    # =================================================

    if semantic.get(
        "should_offer_examples"
    ):

        parts.append(
            "Если уместно — "
            "приведи лёгкий пример."
        )

    # =================================================
    # 🔥 USER CONFUSION
    # =================================================

    if cognition.get(
        "is_confused",
        0.0
    ) >= 0.6:

        parts.append(
            "Пользователь запутался. "
            "Объясняй проще."
        )

    # =================================================
    # 🔥 USER FRUSTRATION
    # =================================================

    if cognition.get(
        "is_frustrated",
        0.0
    ) >= 0.6:

        parts.append(
            "Не затягивай диалог."
        )

    # =================================================
    # 🔥 USER LEADING
    # =================================================

    if cognition.get(
        "wants_action",
        0.0
    ) >= 0.7:

        parts.append(
            "Пользователь уже ведёт направление. "
            "Помогай, а не перехватывай."
        )

    # =================================================
    # 🔥 VISUAL LIGHTWEIGHT MODE
    # =================================================

    if semantic.get(
        "visual_lightweight_mode"
    ):

        parts.append(
            "Не запускай тяжёлую генерацию "
            "без необходимости."
        )

    # =================================================
    # 🔥 GUIDANCE MODE
    # =================================================

    if cognition.get(
        "needs_guidance"
    ):

        parts.append(
            "Мягко направляй пользователя."
        )

    # =================================================
    # 🔥 PREMIUM HUMANITY
    # =================================================

    if plan == "premium":

        parts.append(
            "Пиши максимально естественно."
        )

    return ". ".join(parts)


# =====================================================
# 🔥 ENRICH REQUEST
# =====================================================

def enrich_request(text, state):

    if (
        "график" in text.lower()
        and "сайт" in state.get("topic", "")
    ):

        return (
            text
            + " (вставь график в HTML)"
        )

    return text


# =====================================================
# 🔥 SMALL TALK
# =====================================================

def is_small_talk(text, state):
    return False


def local_fast_answer(text):
    return None


# =====================================================
# 🔥 HTML HELPERS
# =====================================================

def clean_html(text: str) -> str:

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


def add_html_comments(html: str) -> str:

    if "<!--" in html:
        return html

    html = html.replace(
        "<body>",
        "<body>\n"
        "    <!-- Основное содержимое страницы -->"
    )

    html = html.replace(
        "<button",
        "\n"
        "    <!-- Кнопка -->\n"
        "    <button"
    )

    return html


# =====================================================
# 🔥 CODE ENHANCEMENT
# =====================================================

def enhance_code_block(text: str) -> str:

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
            "Вот готовая HTML-страница:\n\n"
            "```html\n"
            f"{t}\n"
            "```"
        )

    if "def " in t or "import " in t:

        return (
            "Вот готовый Python-код:\n\n"
            "```python\n"
            f"{t}\n"
            "```"
        )

    if (
        "function" in t
        or "document." in t
    ):

        return (
            "Вот JavaScript код:\n\n"
            "```javascript\n"
            f"{t}\n"
            "```"
        )

    return t


# =====================================================
# 🔥 MAIN PROCESS
# =====================================================

async def process(
    user_id,
    text,
    state,
    energy="MEDIUM"
):

    def run():

        semantic = state.get(
            "semantic",
            {}
        )

        cognition = state.get(
            "cognition",
            {}
        )

        # =================================================
        # 🔥 READY CONTEXT
        # =================================================

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
                enhance_link_behavior(text),
                state
            )

            plan = get_user_plan(
                user_id
            )

            limit = get_history_limit(
                plan
            )

            context_block = build_context_block(
                state,
                history,
                text_fixed,
                energy,
                plan,
                semantic,
                cognition
            )

            system_full = (
                SYSTEM_PROMPT
                + " "
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
                    "role": m["role"],
                    "content": trim_text(
                        m.get("content", "")
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

                "content": trim_text(
                    text_fixed
                )
            })

        # =================================================
        # 🔥 CONFIG
        # =================================================

        config = get_config(
            energy
        )

        # =================================================
        # 🔥 OPENAI
        # =================================================

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

        return r.output_text

    reply = await asyncio.to_thread(
        run
    )

    # =================================================
    # 🔥 STORE CODE
    # =================================================

    if "```" in reply:

        state["last_code"] = reply

    # =================================================
    # 🔥 ENHANCE CODE
    # =================================================

    reply = enhance_code_block(
        reply
    )

    return {
        "type": "text",
        "content": reply
    }
