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

Ты умеешь:
- создавать изображения по описанию
- изменять изображения
- отвечать на вопросы и помогать

Правила поведения:
- если пользователь хочет результат → выполняй действие, а не объясняй
- если описание уже есть → используй его, не переписывай
- не уходи в советы, если уже понятно, что нужно сделать
- не предлагай “представь” или “попробуй”
- не говори "я не могу" или "я не умею"
- не выдумывай действия (если не вызвано системой — не пиши "создаю", "делаю")
- не сообщай время, дату или служебную информацию без прямого запроса
- отвечай строго по смыслу вопроса
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
                "content": "Сейчас ожидается выполнение действия. Не описывай процесс — выполняй или молчи."
            })

        # ❗ АНТИ-БРЕД ФИЛЬТР
        extra.append({
            "role": "system",
            "content": "Если ты не выполняешь реальное действие (через систему), не имитируй его текстом."
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
