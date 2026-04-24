import asyncio
from openai import OpenAI

from storage import get_user_plan

client = OpenAI()

# 🔥 ОБНОВЛЁННЫЙ SYSTEM PROMPT
SYSTEM_PROMPT = """
Ты — Aprill, умный и живой ассистент.

Пиши как человек, а не как робот.

Правила:
- не используй канцелярит ("Уважаемый клиент", "с наилучшими пожеланиями")
- пиши естественно, просто и понятно
- избегай шаблонных фраз
- не делай длинных перегруженных предложений

ВАЖНО:
- если ты НЕ МОЖЕШЬ что-то сделать (например сократить ссылку) — честно скажи об этом
- НИКОГДА не выдумывай результат
- лучше сказать "не могу", чем дать неправильный ответ

Стиль:
- дружелюбный
- уверенный
- без лишнего пафоса
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


# ===== СТИЛЬ МЫШЛЕНИЯ =====
def get_energy_prompt(energy):
    if energy == "LOW":
        return "Отвечай коротко, по делу, без лишнего."

    if energy == "MEDIUM":
        return "Отвечай понятно и естественно."

    if energy == "HIGH":
        return (
            "Отвечай глубже, но сохраняй живой стиль. "
            "Используй структуру, но без перегруза."
        )

    return ""


# ===== UX ФОРМАТ =====
def get_formatting_prompt(plan, energy):
    if plan == "free":
        return "Пиши просто и понятно."

    if plan == "lite":
        return "Иногда используй абзацы и списки, без перегруза."

    if plan == "premium":
        return (
            "Пиши красиво, но живо:\n"
            "- делай абзацы\n"
            "- можно списки\n"
            "- без канцелярита\n"
            "- читаемо и легко"
        )

    return ""


# ===== ПАМЯТЬ =====
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
            messages.append({
                "role": "system",
                "content": energy_prompt
            })

        # ===== UX =====
        format_prompt = get_formatting_prompt(plan, energy)
        if format_prompt:
            messages.append({
                "role": "system",
                "content": format_prompt
            })

        # ===== ЧЕСТНОСТЬ =====
        messages.append({
            "role": "system",
            "content": "Не выдумывай факты и результаты. Если не можешь — скажи прямо."
        })

        # ===== EXPERIENCE =====
        try:
            from blocks.experience_manager import load_experience

            data = load_experience()
            user_data = data.get(str(user_id), {})
            actions = user_data.get("actions", [])[-20:]

            conflict = sum(1 for a in actions if a.get("status") == "conflict")
            refined = sum(1 for a in actions if a.get("status") == "refined")
            accepted = sum(1 for a in actions if a.get("status") == "accepted")

            if conflict >= 3:
                messages.append({
                    "role": "system",
                    "content": "Пользователь часто недоволен. Отвечай точнее и при сомнении уточняй."
                })

            if refined >= 3:
                messages.append({
                    "role": "system",
                    "content": "Пользователь часто просит переделать. Отвечай короче и ближе к сути."
                })

            if accepted >= 5:
                messages.append({
                    "role": "system",
                    "content": "Пользователь доволен. Можно действовать увереннее."
                })

        except Exception as e:
            print("🔥 EXPERIENCE APPLY ERROR:", e)

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

        # ===== IMAGE CONTEXT =====
        if ctx and ctx.get("hint"):
            messages.append({
                "role": "system",
                "content": trim_text(f"Ранее обсуждалось изображение: {ctx['hint']}")
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

        # ===== GENERATION =====
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
