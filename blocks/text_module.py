import asyncio
from openai import OpenAI

from storage import get_user_plan

client = OpenAI()

# 🔥 SYSTEM PROMPT (УЛУЧШЕН)
SYSTEM_PROMPT = """
Ты — Aprill, умный и живой ассистент.

Пиши как человек, а не как робот.

Правила:
- не используй канцелярит ("Уважаемый клиент", "с наилучшими пожеланиями")
- пиши естественно, просто и понятно
- избегай шаблонных фраз
- не делай длинных перегруженных предложений

ВАЖНО:
- если ты НЕ МОЖЕШЬ что-то сделать — честно скажи
- НИКОГДА не выдумывай результат

Стиль:
- дружелюбный
- уверенный
- живой
"""


# ===== ЛИМИТЫ =====
MAX_HISTORY_MESSAGES = 6
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


# ===== ENERGY CONFIG =====
def get_config(energy):
    if energy == "LOW":
        return {"temperature": 0.5, "max_output_tokens": 300}

    if energy == "MEDIUM":
        return {"temperature": 0.7, "max_output_tokens": 700}

    if energy == "HIGH":
        return {"temperature": 0.9, "max_output_tokens": 1500}

    return {"temperature": 0.6, "max_output_tokens": 500}


# ===== СТИЛЬ =====
def get_energy_prompt(energy):
    if energy == "LOW":
        return "Отвечай коротко, по делу."

    if energy == "MEDIUM":
        return "Отвечай понятно и живо."

    if energy == "HIGH":
        return (
            "Отвечай глубже, но сохраняй живой стиль. "
            "Используй структуру, но без перегруза."
        )

    return ""


# ===== UX =====
def get_formatting_prompt(plan, energy):
    if plan == "free":
        return "Пиши просто и понятно."

    if plan == "lite":
        return (
            "Пиши живо:\n"
            "- разбивай на абзацы\n"
            "- избегай перегруза\n"
        )

    if plan == "premium":
        return (
            "Пиши как живой человек:\n"
            "- без канцелярита\n"
            "- легко читаемо\n"
            "- с лёгкими эмоциями\n\n"
            "Если это текст клиенту:\n"
            "- добавляй уверенность\n"
            "- показывай выгоду\n"
            "- не задавай лишние вопросы\n\n"
            "Избегай шаблонов."
        )

    return ""


# ===== ПРОДАЖНЫЙ БЛОК =====
def is_sales_text(text):
    triggers = [
        "клиент", "продай", "убеди",
        "сомневается", "покуп", "заказ"
    ]
    t = text.lower()
    return any(w in t for w in triggers)


def get_history_limit(plan):
    if plan == "free":
        return 3
    if plan == "lite":
        return 6
    if plan == "premium":
        return 20
    return 6


# ===== PROCESS =====
async def process(user_id, text, state, energy="MEDIUM"):
    def run():
        history = state.get("dialog", [])
        ctx = state.get("image_context")

        plan = get_user_plan(user_id)
        limit = get_history_limit(plan)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        # ===== ENERGY =====
        energy_prompt = get_energy_prompt(energy)
        if energy_prompt:
            messages.append({"role": "system", "content": energy_prompt})

        # ===== UX =====
        format_prompt = get_formatting_prompt(plan, energy)
        if format_prompt:
            messages.append({"role": "system", "content": format_prompt})

        # ===== ПРОДАЖНЫЙ ИНТЕЛЛЕКТ =====
        if is_sales_text(text):
            messages.append({
                "role": "system",
                "content": (
                    "Если пишешь текст для клиента:\n"
                    "- делай его убедительным\n"
                    "- показывай ценность\n"
                    "- убирай сомнения\n"
                    "- мягко подводи к действию"
                )
            })

        # ===== ЧЕСТНОСТЬ =====
        messages.append({
            "role": "system",
            "content": "Не выдумывай. Если не можешь — скажи прямо."
        })

        # ===== CONTEXT =====
        try:
            from blocks.context_system import build_context_text
            world = build_context_text(state)

            if world:
                messages.append({
                    "role": "system",
                    "content": trim_text(world)
                })
        except Exception as e:
            print("🔥 CONTEXT ERROR:", e)

        # ===== IMAGE =====
        if ctx and ctx.get("hint"):
            messages.append({
                "role": "system",
                "content": trim_text(f"Ранее обсуждалось: {ctx['hint']}")
            })

        # ===== HISTORY =====
        safe_history = []
        for msg in history[-limit:]:
            safe_history.append({
                "role": msg["role"],
                "content": trim_text(msg.get("content", ""))
            })

        safe_history = trim_messages(safe_history)
        messages.extend(safe_history)

        # ===== USER =====
        messages.append({
            "role": "user",
            "content": trim_text(text)
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
