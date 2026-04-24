import asyncio
from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = """
Ты — Aprill, интеллектуальный ассистент.

Ты:
- понимаешь диалог
- отвечаешь естественно и по делу
- не усложняешь без причины

Если пользователь говорит про изображение — 
кратко опиши, что понял, и предложи сгенерировать.

Никогда не генерируй без подтверждения.
"""


# 🔥 ЛИМИТЫ
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


# 🔥 ДОБАВИЛИ ENERGY
def get_config(energy):
    if energy == "LOW":
        return {"temperature": 0.5, "max_output_tokens": 300}

    if energy == "MEDIUM":
        return {"temperature": 0.7, "max_output_tokens": 700}

    if energy == "HIGH":
        return {"temperature": 0.9, "max_output_tokens": 1500}

    return {"temperature": 0.6, "max_output_tokens": 500}


# 🔥 ДОБАВИЛИ energy параметр
async def process(user_id, text, state, energy="MEDIUM"):
    def run():
        history = state.get("dialog", [])
        ctx = state.get("image_context")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

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
                    "content": "Пользователь доволен. Можно действовать увереннее и меньше уточнять."
                })

        except Exception as e:
            print("🔥 EXPERIENCE APPLY ERROR:", e)

        # ===== WORLD CONTEXT =====
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
        for msg in history[-MAX_HISTORY_MESSAGES:]:
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

        # 🔥 применяем ENERGY
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
