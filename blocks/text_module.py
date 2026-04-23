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

        # ===== КОНТЕКСТ МИРА (ОСТАВИЛИ, НО БЕЗ ПЕРЕГРУЗА) =====
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

        # ===== КОНТЕКСТ ИЗОБРАЖЕНИЯ (МИНИМАЛЬНЫЙ) =====
        if ctx and ctx.get("hint"):
            messages.append({
                "role": "system",
                "content": f"Ранее обсуждалось изображение: {ctx['hint']}"
            })

        # ===== ИСТОРИЯ (НЕ БОЛЕЕ 6 СООБЩЕНИЙ) =====
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
