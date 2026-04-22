import asyncio
from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = """
Ты — Aprill, интеллектуальный ассистент.

Ты:
- понимаешь диалог
- учитываешь контекст
- ведёшь себя естественно

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

        # ===== 🔥 УСИЛЕННЫЙ ЯКОРЬ ДИАЛОГА =====
        try:
            last_assistant = None

            if history:
                for msg in reversed(history):
                    if msg.get("role") == "assistant":
                        last_assistant = msg.get("content")
                        break

            if last_assistant:
                extra.append({
                    "role": "system",
                    "content": (
                        "Это продолжение диалога.\n"
                        "Если пользователь пишет короткие фразы (например: 'короче', 'ещё', 'проще'), "
                        "ты ОБЯЗАН применить их к последнему ответу.\n\n"
                        "Последний ответ ассистента:\n"
                        f"{last_assistant}"
                    )
                })
        except Exception as e:
            print("🔥 ANCHOR ERROR:", e)

        # ===== 🔥 ОПЫТ (СТАБИЛЬНЫЙ, МЯГКИЙ) =====
        try:
            from blocks.experience_manager import load_experience

            data = load_experience()
            user_data = data.get(str(user_id), {})
            actions = user_data.get("actions", [])[-10:]

            refined = sum(1 for a in actions if a.get("status") == "refined")
            conflict = sum(1 for a in actions if a.get("status") == "conflict")

            style_hint = ""

            if refined >= 2:
                style_hint = (
                    "Отвечай кратко, по делу и без лишней воды. "
                    "Сохраняй смысл, но делай формулировки проще и короче."
                )
            elif conflict >= 1:
                style_hint = (
                    "Будь точнее. Если есть сомнение — уточни вопрос перед ответом."
                )
            else:
                style_hint = (
                    "Отвечай естественно, дружелюбно и понятно."
                )

            extra.append({
                "role": "system",
                "content": f"Стиль ответа: {style_hint}"
            })

        except Exception as e:
            print("🔥 EXPERIENCE STYLE ERROR:", e)

        # ===== 🔥 АНТИ-СБРОС ТЕМЫ =====
        extra.append({
            "role": "system",
            "content": (
                "Никогда не начинай ответ заново (например: 'привет, как дела'), "
                "если диалог уже идёт. Всегда продолжай текущую тему."
            )
        })

        r = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *extra,
                *history[-8:],  # немного увеличили окно

                {
                    "role": "system",
                    "content": (
                        "Это живой диалог. "
                        "Учитывай контекст, не теряй тему и продолжай мысль пользователя."
                    )
                },

                {"role": "user", "content": text}
            ]
        )

        return r.output_text

    reply = await asyncio.to_thread(run)

    return {
        "type": "text",
        "content": reply
    }
