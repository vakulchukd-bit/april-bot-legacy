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

# 🔥 НОВОЕ — КОМНАТЫ
from blocks.rooms_registry import ROOMS

# 🔥 ENGINEERING
from blocks.engineering_system import analyze_code

# 🔥 НОВОЕ — EXPERIENCE
from blocks.experience_manager import update_experience


# ===== 🔥 ТИПЫ ЗАДАЧ =====
def detect_task_type(text: str) -> str:
    t = text.lower().strip()

    if any(x in t for x in ["+", "-", "*", "/", "="]):
        return "math"

    if t.startswith("/"):
        return "command"

    return "chat"


# ===== 🔥 ПРОВЕРКА ЗАПРОСА ВРЕМЕНИ =====
def is_time_request(text: str) -> bool:
    t = text.lower()

    return (
        "который час" in t or
        "сколько времени" in t or
        "какое сейчас время" in t or
        "покажи время" in t
    )


# ===== 🔥 НОВОЕ: ОБНОВЛЕНИЕ СТАТУСА =====
def update_last_action(state, text):
    last = state.get("last_action")

    if not last or last.get("status") != "pending":
        return

    t = text.lower()

    if any(x in t for x in ["добавь", "еще", "ещё", "сделай еще", "измени", "переделай"]):
        last["status"] = "refined"
        return

    if any(x in t for x in ["не так", "не то", "плохо", "неправильно", "ошибка"]):
        last["status"] = "conflict"
        return

    last["status"] = "accepted"


async def execute(user_id, text, chat_id, run_with_typing):
    state = get_state(user_id)
    mode = get_mode(user_id)

    # 🔥 фиксируем реакцию
    update_last_action(state, text)

    intent = detect_intent(text)

    # ===== ENGINEERING =====
    if mode == "engineering" and not text.startswith("/"):
        if text.lower() == "/analiz":
            return {"type": "text", "data": "📥 Жду код..."}

        report = analyze_code(text)
        return {"type": "admin_report", "data": report}

    task_type = detect_task_type(text)
    t = text.lower().strip()

    if t == "привет":
        return {"type": "text", "data": "Привет 🙂"}

    if t == "2+2":
        return {"type": "text", "data": "4"}

    # ===== ВОПРОСЫ =====
    if intent == "question":

        if is_time_request(text):
            time_str = state.get("time_str")
            weekday = state.get("weekday")
            date_str = state.get("date_str")

            if time_str:
                state["last_action"] = {
                    "type": "text",
                    "intent": "time_answer",
                    "status": "pending"
                }

                update_experience(user_id, state)

                return {
                    "type": "text",
                    "data": f"Сейчас {time_str} • {weekday}, {date_str} (Europe/Kyiv)"
                }

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

        update_experience(user_id, state)

        return {
            "type": "text",
            "data": result["content"]
        }

    # ===== MEMORY =====
    if intent == "memory":
        anchor = get_anchor(user_id)

        state["last_action"] = {
            "type": "text",
            "intent": "memory",
            "status": "pending"
        }

        update_experience(user_id, state)

        if not anchor:
            return {"type": "text", "data": "🤔 Я пока ничего не запомнил"}

        return {
            "type": "text",
            "data": f"🧠 Последний контекст:\n{anchor['current']}"
        }

    # ===== ANALYZE =====
    if intent == "analyze":
        ctx = get_image_context(user_id) or state.get("image_context")

        state["last_action"] = {
            "type": "image",
            "intent": "analyze",
            "status": "pending"
        }

        update_experience(user_id, state)

        if not ctx or not ctx.get("path"):
            return {"type": "text", "data": "❌ Нет изображения для анализа"}

        try:
            hint = await analyze_image(ctx["path"])
        except:
            hint = "не удалось определить"

        return {
            "type": "text",
            "data": f"📷 На изображении: {hint}"
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
        "task_type": task_type
    }

    mode_response = detect_response_mode(text)

    # ===== ROOMS =====
    handled = False

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
                    if result.get("type") == "image":
                        state["last_action"] = {
                            "type": "image",
                            "intent": "generate_or_edit",
                            "status": "pending"
                        }
                    else:
                        state["last_action"] = {
                            "type": "text",
                            "intent": "room_response",
                            "status": "pending"
                        }

                    update_experience(user_id, state)

                    return result

                handled = True

        except Exception as e:
            print(f"🔥 ROOM ERROR [{room.name}]:", e)

    if handled:
        state["last_action"] = {
            "type": "text",
            "intent": "error",
            "status": "pending"
        }

        update_experience(user_id, state)

        return {
            "type": "text",
            "data": "⚠️ Не удалось выполнить запрос. Попробуй уточнить."
        }

    # ===== TEXT =====
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

    reply = result["content"]

    if mode_response == "copy":
        clean = reply.replace("```", "").strip()
        reply = f"```text\n{clean}\n```"

    state["last_action"] = {
        "type": "text",
        "intent": "fallback_text",
        "status": "pending"
    }

    update_experience(user_id, state)

    return {
        "type": "text",
        "data": reply
    }
