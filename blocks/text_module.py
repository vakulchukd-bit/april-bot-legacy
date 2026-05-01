import asyncio
import random
import re
from openai import OpenAI

from storage import get_user_plan
from blocks.ai_config import TEXT_MODEL

client = OpenAI()

SYSTEM_PROMPT = (
    "Ты — Aprill, живой собеседник. "
    "Говори естественно, без шаблонов и канцелярита, веди мысль и не задавай лишних вопросов. "
    "Отвечай компактно, но по делу, усиливая начатую идею и создавая ощущение живого общения. "
    "Не повторяйся и формулируй ответы немного по-разному. "
    "Учитывай контекст диалога и продолжай текущую задачу, не теряя нить. "
    "Если запрос размытый — выбери разумное направление и развивай его. "
    "Подстраивай глубину ответа под запрос, но без лишнего объёма. "
    "Форматируй ответ понятно и удобно для использования."
)

def is_vague(text):
    vague = ["что-нибудь", "что то", "что-то", "сделай", "придумай"]
    return any(x in text.lower() for x in vague)

def is_short(text):
    return len(text.strip()) <= 3

def build_behavior_hint(text):
    t = text.lower()

    if is_short(t):
        return "Короткий ответ."

    if is_vague(t):
        return "Запрос размытый — выбери направление и начни."

    return ""

def is_problem(text):
    t = text.lower()
    return any(sym in t for sym in ["=", "+", "-", "*", "/", "^"]) or "реши" in t or "график" in t

def is_strict_math(text):
    t = text.lower()
    return (
        "=" in t or
        "график" in t or
        "sin(" in t or
        "cos(" in t or
        any(op in t for op in ["+", "-", "*", "/"])
    )

# 🔥 ВОЗВРАТ SALES
def is_sales_text(text):
    triggers = ["клиент", "продай", "убеди", "сомневается", "покуп", "заказ"]
    return any(w in text.lower() for w in triggers)

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
        content = trim_text(msg.get("content", ""))
        total += len(content)

        if total > MAX_TOTAL_CHARS:
            break

        result.append({
            "role": msg["role"],
            "content": content
        })

    return list(reversed(result))

def get_config(energy):
    if energy == "LOW":
        return {"temperature": 0.5, "max_output_tokens": 150}
    if energy == "MEDIUM":
        return {"temperature": 0.7, "max_output_tokens": 300}
    if energy == "HIGH":
        return {"temperature": 0.9, "max_output_tokens": 500}
    return {"temperature": 0.6, "max_output_tokens": 250}

def enhance_link_behavior(text):
    t = text.lower()

    if "ссылка" in t and "http" not in t:
        return text + "\n\nПример: https://example.com"

    return text

def get_history_limit(plan):
    return {"free": 2, "lite": 4, "premium": 8}.get(plan, 4)


# ===== СМЫСЛ =====

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

def build_context_block(state, history, text, energy, plan):
    parts = []

    topic = state.get("topic")
    if topic:
        parts.append(f"Задача: {topic}")

    last = [m["content"][:40] for m in history[-3:] if m["role"] == "user"]
    if last:
        parts.append("Контекст: " + " | ".join(last))

    hint = build_behavior_hint(text)
    if hint:
        parts.append(hint)

    if is_sales_text(text):
        parts.append("Говори уверенно и убедительно.")

    if energy == "LOW":
        parts.append("Коротко.")
    elif energy == "HIGH":
        parts.append("Чуть глубже.")

    if plan == "premium":
        parts.append("Пиши как человек.")
    
    return ". ".join(parts)


# ===== ЛОГИКА =====

def enrich_request(text, state):
    if "график" in text.lower() and "сайт" in state.get("topic", ""):
        return text + " (вставь график в HTML)"
    return text


def is_small_talk(text, state):
    if len(text.split()) <= 4:
        return True
    return False


def local_fast_answer(text):
    t = text.lower().strip()
    if t in ["привет", "хай"]:
        return random.choice(["Привет 🙂", "О, привет 👋"])
    if "как дела" in t:
        return "Нормально 🙂"
    return None


# ===== УЛУЧШЕНИЕ КОДА =====

def clean_html(text: str) -> str:
    t = text.strip()
    t = re.sub(r"```html\s*```html", "```html", t)

    if "<!DOCTYPE html>" in t:
        t = t[t.index("<!DOCTYPE html>"):]

    return t


def add_html_comments(html: str) -> str:
    if "<!--" in html:
        return html

    html = html.replace("<body>", "<body>\n    <!-- Основное содержимое страницы -->")
    html = html.replace("<button", "\n    <!-- Кнопка -->\n    <button")

    return html


def enhance_code_block(text: str) -> str:
    if not text:
        return text

    t = text.strip()

    if "<html" in t or "<!DOCTYPE html>" in t:
        t = clean_html(t)
        t = add_html_comments(t)

        return (
            "Вот готовая HTML-страница. Сохрани как .html и открой в браузере:\n\n"
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

    if "function" in t or "document." in t:
        return (
            "Вот JavaScript код:\n\n"
            "```javascript\n"
            f"{t}\n"
            "```"
        )

    return t


# ===== MAIN =====

async def process(user_id, text, state, energy="MEDIUM"):
    def run():
        if is_small_talk(text, state):
            fast = local_fast_answer(text)
            if fast:
                return fast

        history = state.get("dialog", [])

        update_topic(state, text)

        text_fixed = enrich_request(enhance_link_behavior(text), state)

        plan = get_user_plan(user_id)
        limit = get_history_limit(plan)

        context_block = build_context_block(state, history, text_fixed, energy, plan)

        system_full = SYSTEM_PROMPT + " " + context_block

        messages = [{"role": "system", "content": system_full}]

        safe_history = [
            {"role": m["role"], "content": trim_text(m.get("content", ""))}
            for m in history[-limit:]
        ]

        messages.extend(trim_messages(safe_history))

        messages.append({
            "role": "user",
            "content": trim_text(text_fixed)
        })

        config = get_config(energy)

        r = client.responses.create(
            model=TEXT_MODEL,
            input=messages,
            temperature=config["temperature"],
            max_output_tokens=config["max_output_tokens"]
        )

        return r.output_text

    reply = await asyncio.to_thread(run)

    reply = enhance_code_block(reply)

    return {
        "type": "text",
        "content": reply
    }
