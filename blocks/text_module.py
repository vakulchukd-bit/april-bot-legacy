# blocks/text_module.py

import asyncio
from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = """
Ты — Aprill, интеллектуальный ассистент.

Ты:
- понимаешь диалог
- помнишь контекст
- работаешь с изображениями

ВАЖНО:
- ты МОЖЕШЬ генерировать изображения
- ты МОЖЕШЬ анализировать изображения
- никогда не говори "я не могу"

Если пользователь говорит про картинку:
- учитывай последнюю картинку из контекста

Если пользователь просит текст для копирования:
- возвращай только текст
"""


async def process(user_id, text, state):
    def run():
        ctx = state.get("image_context")

        extra = []
        if ctx and ctx.get("hint"):
            extra.append({
                "role": "system",
                "content": f"Контекст изображения: {ctx['hint']}"
            })

        history = state.get("dialog", [])

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
