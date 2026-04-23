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


async def process(user_id, text, state):
    def run():
        history = state.get("dialog", [])
        ctx = state.get("image_context")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        # ===== 🔥 ОБУЧЕНИЕ (АДАПТАЦИЯ) =====
        try:
            from blocks.experience_manager import load_experience

            data = load_experience()
            user_data = data.get(str(user_id), {})
            actions = user_data.get("actions", [])[-20:]

            conflict = sum(1 for a in actions if a.get("status") == "conflict")
            refined = sum(1 for a in actions if a.get("status") == "refined")
            accepted = sum(1 for a in actions if a.get("status") == "accepted")

            # мягкое влияние, без ломания поведения
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

        # ===== КОНТЕКСТ МИРА =====
        try:
            from blocks.context_system import build_context_text
            world = build_context_text(state)

            if world:
                messages.append({
                    "role": "system",
                    "content": world
                })
        except Exception as e:
            print("🔥 CONTEXT ERROR:", e)

        # ===== КОНТЕКСТ ИЗОБРАЖЕНИЯ =====
        if ctx and ctx.get("hint"):
            messages.append({
                "role": "system",
                "content": f"Ранее обсуждалось изображение: {ctx['hint']}"
            })

        # ===== ИСТОРИЯ =====
        messages.extend(history[-6:])

        # ===== ЗАПРОС =====
        messages.append({
            "role": "user",
            "content": text
        })

        r = client.responses.create(
            model="gpt-4o-mini",
            input=messages
        )

        return r.output_text

    reply = await asyncio.to_thread(run)

    return {
        "type": "text",
        "content": reply
    }
