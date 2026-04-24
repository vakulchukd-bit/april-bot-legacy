import asyncio
from openai import OpenAI

from storage import get_user_plan

client = OpenAI()

# 🔥 SYSTEM PROMPT
SYSTEM_PROMPT = """
Ты — Aprill, умный и живой ассистент.

Пиши как человек, а не как робот.

Правила:
- не используй канцелярит
- пиши естественно и понятно
- избегай шаблонных фраз

ВАЖНО:
- если не можешь — честно скажи
- НИКОГДА не выдумывай результат
- ВСЕГДА старайся помочь, даже если не можешь сделать напрямую

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


# ===== ENERGY =====
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
        return "Отвечай понятно и живо."
    if energy == "HIGH":
        return "Отвечай глубже, но без перегруза."
    return ""


# ===== UX =====
def get_formatting_prompt(plan, energy):
    if plan == "free":
        return "Пиши просто."
    if plan == "lite":
        return "Пиши живо, с абзацами."
    if plan == "premium":
        return (
            "Пиши как живой человек.\n"
            "- легко читаемо\n"
            "- без шаблонов\n"
            "- можно эмоции\n\n"
            "Если текст клиенту:\n"
            "- добавляй уверенность\n"
            "- показывай выгоду"
        )
    return ""


# ===== ПРОДАЖА =====
def is_sales_text(text):
    triggers = ["клиент", "продай", "убеди", "сомневается", "покуп", "заказ"]
    return any(w in text.lower() for w in triggers)


# ===== ССЫЛКИ (🔥 ГЛАВНЫЙ ФИКС) =====
def enhance_link_behavior(text):
    t = text.lower()

    if "ссылка" in t or "link" in t:
        if "http" not in t:
            return text + (
                "\n\nИспользуй пример ссылки: https://example.com\n"
                "Можешь встроить её в текст и оформить красиво."
            )

    return text


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

        # 🔥 ФИКС ССЫЛОК
        text_fixed = enhance_link_behavior(text)

        plan = get_user_plan(user_id)
        limit = get_history_limit(plan)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # ENERGY
        ep = get_energy_prompt(energy)
        if ep:
            messages.append({"role": "system", "content": ep})

        # UX
        fp = get_formatting_prompt(plan, energy)
        if fp:
            messages.append({"role": "system", "content": fp})

        # ПРОДАЖА
        if is_sales_text(text_fixed):
            messages.append({
                "role": "system",
                "content": (
                    "Пиши убедительно:\n"
                    "- показывай ценность\n"
                    "- убирай сомнения\n"
                    "- мягко веди к действию"
                )
            })

        # ЧЕСТНОСТЬ
        messages.append({
            "role": "system",
            "content": "Не выдумывай. Если не можешь — предложи альтернативу."
        })

        # CONTEXT
        try:
            from blocks.context_system import build_context_text
            world = build_context_text(state)
            if world:
                messages.append({"role": "system", "content": trim_text(world)})
        except:
            pass

        # IMAGE
        if ctx and ctx.get("hint"):
            messages.append({
                "role": "system",
                "content": trim_text(f"Контекст: {ctx['hint']}")
            })

        # HISTORY
        safe_history = [
            {"role": m["role"], "content": trim_text(m.get("content", ""))}
            for m in history[-limit:]
        ]

        messages.extend(trim_messages(safe_history))

        # USER
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
