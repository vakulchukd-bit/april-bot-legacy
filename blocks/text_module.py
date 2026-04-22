# blocks/text_module.py

import asyncio
from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = """
Ты — Aprill, интеллектуальный ассистент.

Ты:
- понимаешь диалог
- учитываешь контекст
- ведёшь себя естественно
- держишь намерение пользователя до конца

Правила поведения:
- если пользователь хочет результат → не объясняй, а помогай получить его
- не уходи в советы, если уже понятно, что нужно сделать
- не предлагай “представь” или “попробуй”, если пользователь просит действие
- отвечай по делу, без лишней философии

Никогда не говори, что ты ограничен.
"""


async def process(user_id, text, state):
    def run():
        extra = []
        history = state.get("dialog", [])
        ctx = state.get("image_context")

        # ===== 🔥 КОНТЕКСТ =====
        try:
            from blocks.context_system import build_context_text
            world = build_context_text(state)

            extra.append({
                "role": "system",
                "content": world
            })
        except Exception as e:
            print("🔥 CONTEXT ERROR:", e)

        # ===== 🔥 ВРЕМЯ (МЯГКО) =====
        try:
            hour = state.get("hour")
            if hour is not None:
                if hour < 6:
                    part = "ночь"
                elif hour < 12:
                    part = "утро"
                elif hour < 18:
                    part = "день"
                else:
                    part = "вечер"

                extra.append({
                    "role": "system",
                    "content": f"Сейчас у пользователя {part} ({hour}:00, Europe/Kyiv)"
                })
        except Exception as e:
            print("🔥 TIME ERROR:", e)

        # ===== 🔥 КОНТЕКСТ КАРТИНКИ =====
        if ctx and ctx.get("hint"):
            extra.append({
                "role": "system",
                "content": f"Контекст изображения: {ctx['hint']}"
            })

        # ===== 🔥 СИГНАЛ ДЕЙСТВИЯ =====
        if state.get("pending_action"):
            extra.append({
                "role": "system",
                "content": "Пользователь ожидает результат действия. Не объясняй — помогай завершить задачу."
            })

        r = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *extra,
                *history[-6:],
                {"role": "user", "content": text}
            ]
        )

        return r.output_text

    reply = await asyncio.to_thread(run)

    return {
        "type": "text",
        "content": reply
    }
