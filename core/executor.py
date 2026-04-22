from blocks.response_mode import detect_response_mode
from blocks.text_module import process as text_process

from blocks.intent_system import detect_intent

from blocks.state_manager import (
    get_state,
    get_image_context
)

from blocks.anchor_system import get_anchor
from blocks.image_system import analyze_image
from blocks.mode_manager import get_mode

from blocks.context_system import build_context_text

from blocks.rooms_registry import ROOMS
from blocks.engineering_system import analyze_code

from blocks.experience_manager import update_experience, load_experience

from openai import OpenAI
client = OpenAI()


# ===== 🔥 УМНАЯ ОЦЕНКА =====
def smart_evaluate(user_text: str, last_assistant_text: str) -> str:
    try:
        r = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {
                    "role": "system",
                    "content": (
                        "Оцени реакцию пользователя на ответ ассистента.\n"
                        "Ответь одним словом:\n"
                        "accepted / refined / conflict\n\n"
                        "accepted — пользователь продолжает тему или согласен\n"
                        "refined — уточняет, хочет лучше/короче/подробнее\n"
                        "conflict — ассистент ошибся, пользователь исправляет или недоволен\n\n"
                        "Без объяснений."
                    )
                },
                {
                    "role": "user",
                    "content": f"Ответ ассистента:\n{last_assistant_text}\n\nСообщение пользователя:\n{user_text}"
                }
            ]
        )

        result = r.output_text.lower().strip()

        if "conflict" in result:
            return "conflict"
        if "refined" in result:
            return "refined"

        return "accepted"

    except:
        return "accepted"


# ===== 🔥 ЗАЩИТА ОТ ЛОЖНЫХ ДЕЙСТВИЙ =====
def is_followup(text: str) -> bool:
    t = text.lower().strip()

    markers = [
        "сделай", "ещё", "еще",
        "короче", "подробнее",
        "объясни проще",
        "не это имел в виду",
        "я про другое",
        "уточни"
    ]

    return any(m in t for m in markers)


# ===== ОБНОВЛЕНИЕ СТАТУСА =====
def update_last_action(state, text):
    last = state.get("last_action")

    if not last or last.get("status") != "pending":
        return

    history = state.get("dialog", [])

    last_assistant = None
    for msg in reversed(history):
        if msg.get("role") == "assistant":
            last_assistant = msg.get("content")
            break

    if not last_assistant:
        last["status"] = "accepted"
        return

    status = smart_evaluate(text, last_assistant)

    last["status"] = status


def commit_last_action(user_id, state):
    last = state.get("last_action")

    if not last:
        return

    if last.get("status") == "pending":
        return

    update_experience(user_id, state)


async def execute(user_id, text, chat_id, run_with_typing):
    state = get_state(user_id)
    mode = get_mode(user_id)

    update_last_action(state, text)
    commit_last_action(user_id, state)

    intent = detect_intent(text)

    # ===== 🔥 ФИКС: уточнения всегда текст =====
    if is_followup(text):
        intent = "question"

    # ===== DEBUG =====
    if text == "/exp":
        data = load_experience()
        user_data = data.get(str(user_id), {})

        return {
            "type": "text",
            "data": f"🧠 Опыт:\n{user_data}"
        }

    # ===== ENGINEERING =====
    if mode == "engineering" and not text.startswith("/"):
        if text.lower() == "/analiz":
            return {"type": "text", "data": "📥 Жду код..."}

        report = analyze_code(text)
        return {"type": "admin_report", "data": report}

    t = text.lower().strip()

    if t == "привет":
        return {"type": "text", "data": "Привет 🙂"}

    if t == "2+2":
        return {"type": "text", "data": "4"}

    # ===== ВОПРОСЫ =====
    if intent == "question":

        ctx = get_image_context(user_id) or state.get("image_context")
        anchor = get_anchor(user_id)

        if ctx and ctx.get("path"):
            try:
                hint = await analyze_image(ctx["path"])
                text = f"На изображении: {hint}\n\n{text}"
            except:
                pass

        if anchor:
            text = f"Контекст: {anchor['current']}\n\n{text}"

        world = build_context_text()
        text = f"{world}\n\n{text}"

        result = await run_with_typing(
            chat_id,
            text_process(user_id, text, state)
        )

        state["last_action"] = {
            "type": "text",
            "intent": "answer",
            "status": "pending"
        }

        return {
            "type": "text",
            "data": result["content"]
        }

    # ===== CONTEXT =====
    ctx = get_image_context(user_id) or state.get("image_context")
    anchor = get_anchor(user_id)

    context = {
        "chat_id": chat_id,
        "state": state,
        "image": ctx,
        "anchor": anchor,
        "mode": mode,
        "task_type": "chat"
    }

    for room in ROOMS:
        try:
            if room.can_handle(text, context):
                result = await room.handle(
                    user_id,
                    text,
                    context,
                    run_with_typing
                )

                if result:
                    return result

        except Exception as e:
            print(f"🔥 ROOM ERROR [{room.name}]:", e)

    # ===== FALLBACK =====
    result = await run_with_typing(
        chat_id,
        text_process(user_id, text, state)
    )

    return {
        "type": "text",
        "data": result["content"]
    }
