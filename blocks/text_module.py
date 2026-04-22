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

ВАЖНО:
- не повторяй один и тот же список возможностей
- не отвечай шаблонно
- если уже объяснял — не дублируй
- отвечай как человек, а не как инструкция
- веди диалог дальше (предлагай, уточняй, вовлекай)

Никогда не говори, что ты ограничен.
"""


# ===== 🔥 ПРОВЕРКА: УЖЕ ОБЪЯСНЯЛИ ИЛИ НЕТ =====
def already_explained(history):
    if not history:
        return False

    last = " ".join([m.get("content", "") for m in history[-4:]]).lower()

    keywords = [
        "я умею",
        "могу создавать",
        "могу изменять",
        "умею делать"
    ]

    return any(k in last for k in keywords)


# ===== 🔥 МЯГКИЙ ПОВЕДЕНЧЕСКИЙ ХИНТ =====
def adapt_behavior(text, history):
    t = text.lower()

    if "умеешь" in t or "можешь" in t:
        if already_explained(history):
            return "ответь кратко, по-дружески и не повторяй список"
        else:
            return "ответь кратко и естественно, без списков"

    return None


async def process(user_id, text, state):
    def run():
        extra = []
        history = state.get("dialog", [])
        ctx = state.get("image_context")

        # ===== 🔥 КОНТЕКСТ (без циклов) =====
        try:
            from blocks.context_system import build_context_text
            world = build_context_text(state)

            extra.append({
                "role": "system",
                "content": world
            })
        except Exception as e:
            print("🔥 CONTEXT ERROR:", e)

        # ===== 🔥 ВРЕМЯ =====
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
                    "content": f"Текущее время пользователя: {hour}:00 ({part}, Europe/Kyiv)"
                })
        except Exception as e:
            print("🔥 TIME ERROR:", e)

        # ===== 🔥 КОНТЕКСТ КАРТИНКИ =====
        if ctx and ctx.get("hint"):
            extra.append({
                "role": "system",
                "content": f"Контекст изображения: {ctx['hint']}"
            })

        # ===== 🔥 ПОВЕДЕНИЕ (НОВЫЙ СЛОЙ, БЕЗ ЛОМКИ) =====
        try:
            hint = adapt_behavior(text, history)
            if hint:
                extra.append({
                    "role": "system",
                    "content": hint
                })
        except Exception as e:
            print("🔥 BEHAVIOR ERROR:", e)

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
