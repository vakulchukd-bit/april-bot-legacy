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

# 🔥 GPT routing (мягкий)
from openai import OpenAI
client = OpenAI()


# ===== GPT helper =====
def gpt_decide_action(text: str) -> str:
    try:
        r = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {
                    "role": "system",
                    "content": (
                        "Определи тип запроса.\n"
                        "Ответь одним словом:\n"
                        "text / image / edit / analyze\n"
                        "Без объяснений."
                    )
                },
                {"role": "user", "content": text}
            ]
        )

        decision = r.output_text.lower().strip()

        if "image" in decision:
            return "image"
        if "edit" in decision:
            return "edit"
        if "analyze" in decision:
            return "analyze"

        return "text"

    except:
        return "text"


def detect_task_type(text: str) -> str:
    t = text.lower().strip()

    if any(x in t for x in ["+", "-", "*", "/", "="]):
        return "math"

    if t.startswith("/"):
        return "command"

    return "chat"


def is_time_request(text: str) -> bool:
    t = text.lower()

    return (
        "который час" in t or
        "сколько времени" in t or
        "какое сейчас время" in t or
        "покажи время" in t
    )


def is_text_refinement(text: str) -> bool:
    t = text.lower().strip()

    markers = [
        "еще короче", "ещё короче",
        "сократи", "укороти",
        "поконкретнее", "подробнее", "уточни",
        "сделай короче", "сделай её короче", "сделай это короче"
    ]

    return any(m in t for m in markers)


def update_last_action(state, text):
    last = state.get("last_action")

    if not last or last.get("status") != "pending":
        return

    t = text.lower()

    if any(x in t for x in ["добавь", "еще", "ещё", "измени", "переделай"]):
        last["status"] = "refined"
        return

    if any(x in t for x in ["не так", "не то", "плохо", "неправильно", "ошибка"]):
        last["status"] = "conflict"
        return

    last["status"] = "accepted"


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

    # ===== DEBUG =====
    if text == "/exp":
        data = load_experience()
        user_data = data.get(str(user_id), {})

        return {
            "type": "text",
            "data": f"🧠 Опыт:\n{user_data}"
        }

    # ===== GPT decision =====
    gpt_action = gpt_decide_action(text)

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

    # ===== ТЕКСТ (если GPT сказал text ИЛИ старый intent) =====
    if intent == "question" or gpt_action == "text":

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

        return {
            "type": "text",
            "data": result["content"]
        }

    # ===== ROOMS (если GPT считает что это действие) =====
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
