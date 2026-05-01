import asyncio
import random
import re
from openai import OpenAI

from storage import get_user_plan
from blocks.ai_config import TEXT_MODEL

client = OpenAI()

SYSTEM_PROMPT = (
    "Ты — Aprill, живой собеседник.\n"
    "Не ассистент, а человек в диалоге.\n\n"
    "Говори естественно, без шаблонов и канцелярита.\n"
    "Веди мысль, не задавай лишних вопросов.\n"
    "Отвечай компактно, без лишних абзацев.\n"
    "Если начал — продолжай и усиливай.\n"
    "Создавай ощущение живого общения."
)

def is_vague(text):
    vague = ["что-нибудь", "что то", "что-то", "сделай", "придумай"]
    return any(x in text.lower() for x in vague)

def is_short(text):
    return len(text.strip()) <= 3

def build_behavior_hint(text):
    t = text.lower()

    if is_short(t):
        return "Ответь живо и очень коротко."

    if is_vague(t):
        return (
            "Запрос размытый.\n"
            "Выбери направление и начни его развивать."
        )

    return ""

def build_variation_guard():
    return "Не повторяйся. Пиши каждый раз немного по-разному."

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

def get_energy_prompt(energy):
    if energy == "LOW":
        return "Отвечай коротко и по делу."
    if energy == "MEDIUM":
        return "Отвечай понятно и без лишнего."
    if energy == "HIGH":
        return "Отвечай глубже, но без увеличения объема."
    return ""

def get_formatting_prompt(plan, energy):
    if plan == "free":
        return "Пиши просто и кратко."
    if plan == "lite":
        return "Пиши живо и компактно."
    if plan == "premium":
        return "Пиши как человек, но без лишней длины."
    return ""

def enhance_link_behavior(text):
    t = text.lower()

    if "ссылка" in t or "link" in t:
        if "http" not in t:
            return text + "\n\nПример: https://example.com"

    return text

def get_history_limit(plan):
    if plan == "free":
        return 2
    if plan == "lite":
        return 4
    if plan == "premium":
        return 8
    return 4


# ===============================
# 🔥 СМЫСЛОВАЯ ПАМЯТЬ (УСИЛЕНА)
# ===============================
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


def get_topic_prompt(state):
    topic = state.get("topic")
    if topic:
        return f"Текущая задача: {topic}. Продолжай строго в этом контексте."
    return None


def build_light_context(history):
    if not history:
        return ""

    last = history[-5:]

    summary = []
    for msg in last:
        if msg["role"] == "user":
            summary.append(msg["content"][:60])

    if not summary:
        return ""

    return "Контекст диалога: " + " | ".join(summary[-3:])


# ===============================
# 🔥 СВЯЗКА ЗАДАЧ
# ===============================
def enrich_request(text, state):
    t = text.lower()
    topic = state.get("topic", "")

    if "график" in t and "сайт" in topic:
        return text + " (вставь график прямо в HTML страницу)"

    return text


def is_small_talk(text, state):
    t = text.lower().strip()
    words = t.split()

    if state.get("dialog"):
        if len(words) <= 2:
            return False

    if len(words) <= 4:
        return True

    return False


def local_fast_answer(text):
    t = text.lower().strip()

    if t in ["привет", "хай"]:
        return random.choice(["Привет 🙂", "О, привет 👋"])

    if "как дела" in t:
        return "Нормально 🙂"

    return None


def enhance_code_block(text: str) -> str:
    if not text:
        return text

    t = text.strip()

    if "<html" in t or "<!doctype html" in t:
        return (
            "Вот готовая HTML-страница:\n\n"
            "```html\n"
            f"{t}\n"
            "```"
        )

    if "def " in t or "import " in t:
        return (
            "```python\n"
            f"{t}\n"
            "```"
        )

    return t


async def process(user_id, text, state, energy="MEDIUM"):
    def run():
        if is_small_talk(text, state):
            fast = local_fast_answer(text)
            if fast:
                return fast

        history = state.get("dialog", [])

        # 🔥 обновляем тему
        update_topic(state, text)

        text_fixed = enhance_link_behavior(text)
        text_fixed = enrich_request(text_fixed, state)

        plan = get_user_plan(user_id)
        limit = get_history_limit(plan)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # 🔥 ЯКОРЬ
        topic_prompt = get_topic_prompt(state)
        if topic_prompt:
            messages.append({"role": "system", "content": topic_prompt})

        # 🔥 старый контекст оставлен
        context_summary = build_light_context(history)
        if context_summary:
            messages.append({"role": "system", "content": context_summary})

        if is_problem(text_fixed):
            messages.append({
                "role": "system",
                "content": "Это математическая задача. Реши максимально кратко."
            })

        if is_strict_math(text_fixed):
            messages.append({
                "role": "system",
                "content": "Ответ короткий."
            })

        behavior = build_behavior_hint(text_fixed)
        if behavior:
            messages.append({"role": "system", "content": behavior})

        messages.append({"role": "system", "content": build_variation_guard()})

        ep = get_energy_prompt(energy)
        if ep:
            messages.append({"role": "system", "content": ep})

        fp = get_formatting_prompt(plan, energy)
        if fp:
            messages.append({"role": "system", "content": fp})

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
