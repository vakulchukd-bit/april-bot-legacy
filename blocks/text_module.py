# blocks/text_module.py

import asyncio
from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = "Ты — Aprill, интеллектуальный ассистент."


async def process(user_id, text, state):
    def run():
        history = state.get("dialog", [])

        r = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
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
