import asyncio
from openai import OpenAI

from storage import get_user_plan

client = OpenAI()

# 🔥 УЖАТЫЙ SYSTEM (вместо 700 токенов → ~80)
SYSTEM_PROMPT = (
    "Ты — Aprill, живой собеседник.\n"
    "Не ассистент, а человек в диалоге.\n\n"
    "Говори естественно, без шаблонов и канцелярита.\n"
    "Веди мысль, не задавай лишних вопросов.\n"
    "Если начал — продолжай и усиливай.\n"
    "Не предлагай списки, если запрос размытый — выбери направление и развивай его.\n"
    "Создавай ощущение живого общения."
)

# ===== 🔥 ПОВЕДЕНИЕ =====
def is_vague(text):
    vague = ["что-нибудь", "что то", "что-то", "сделай", "придумай"]
    return any(x in text.lower() for x in vague)


def is_short(text):
    return len(text.strip()) <= 3


def build_behavior_hint(text):
    t = text.lower()

    if is_short(t):
        return "Ответь живо, естественно."

    if is_vague(t):
        return (
            "Запрос размытый.\n"
            "Выбери направление и начни его развивать."
        )

    return ""


def build_variation_guard():
    return (
        "Не повторяйся.\n"
        "Пиши каждый раз немного по-разному."
    )


def is_problem(text):
    t = text.lower()
    return any(sym in t for sym in ["=", "+", "-", "*", "/", "^"]) or "реши" in t or "график" in t


MAX_MESSAGE_CHARS = 2000
MAX_TOTAL_CHARS = 12000


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
        return {"temperature": 0.5, "max_output_tokens": 300}
    if energy == "MEDIUM":
        return {"temperature": 0.7, "max_output_tokens": 700}
    if energy == "HIGH":
        return {"temperature": 0.9, "max_output_tokens": 1500}
    return {"temperature": 0.6, "max_output_tokens": 500}


def get_energy_prompt(energy):
    if energy == "LOW":
        return "Отвечай коротко."
    if energy == "MEDIUM":
        return "Отвечай понятно."
    if energy == "HIGH":
        return "Отвечай глубже."
    return ""


def get_formatting_prompt(plan, energy):
    if plan == "free":
        return "Пиши просто."
    if plan == "lite":
        return "Пиши живо."
    if plan == "premium":
        return "Пиши как человек."
    return ""


def is_sales_text(text):
    triggers = ["клиент", "продай", "убеди", "сомневается", "покуп", "заказ"]
    return any(w in text.lower() for w in triggers)


def enhance_link_behavior(text):
    t = text.lower()

    if "ссылка" in t or "link" in t:
        if "http" not in t:
            return text + "\n\nПример: https://example.com"

    return text


def get_history_limit(plan):
    if plan == "free":
        return 3
    if plan == "lite":
        return 6
    if plan == "premium":
        return 20
    return 6


async def process(user_id, text, state, energy="MEDIUM"):
    def run():
        history = state.get("dialog", [])
        ctx = state.get("image_context")

        text_fixed = enhance_link_behavior(text)

        plan = get_user_plan(user_id)
        limit = get_history_limit(plan)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if is_problem(text_fixed):
            messages.append({
                "role": "system",
                "content": "Это задача. Реши и объясни."
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

        if is_sales_text(text_fixed):
            messages.append({
                "role": "system",
                "content": "Говори уверенно."
            })

        try:
            from blocks.context_system import build_context_text
            world = build_context_text(state)
            if world:
                messages.append({"role": "system", "content": trim_text(world)})
        except:
            pass

        if ctx and ctx.get("hint"):
            messages.append({
                "role": "system",
                "content": trim_text(f"Контекст: {ctx['hint']}")
            })

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
            model="gpt-4o-mini",
            input=messages,
            temperature=config["temperature"],
            max_output_tokens=config["max_output_tokens"]
        )

        return r.output_text

    reply = await asyncio.to_thread(run)

    return {
        "type": "text",
        "content": reply
    }
