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


# ===== 🔥 ЗАМЕНА ЦВЕТА (ГЛАВНЫЙ ФИКС) =====
def update_image_prompt(old_prompt: str, new_text: str) -> str:
    t = new_text.lower()

    color_map = {
        "красн": "красный",
        "син": "синий",
        "зелён": "зелёный",
        "желт": "жёлтый",
        "черн": "чёрный",
        "бел": "белый",
        "red": "red",
        "blue": "blue",
        "green": "green",
        "yellow": "yellow",
        "black": "black",
        "white": "white"
    }

    # ищем новый цвет
    new_color = None
    for key, val in color_map.items():
        if key in t:
            new_color = val
            break

    # если найден цвет → удаляем старые цвета и ставим новый
    if new_color:
        clean_prompt = old_prompt

        for key in color_map.keys():
            clean_prompt = clean_prompt.replace(key, "")

        # собираем нормальный prompt
        return f"{new_color} {clean_prompt}".strip()

    # если не цвет → дополняем
    return f"{old_prompt}, {new_text}"


def is_followup(text: str) -> bool:
    t = text.lower().strip()

    markers = [
        "сделай", "измени", "добавь", "убери",
        "замени", "поменяй",
        "ещё", "еще",
        "короче", "подробнее",
        "объясни проще",
        "не это имел в виду",
        "я про другое",
        "уточни"
    ]

    return any(m in t for m in markers)


def is_confirmation(text: str) -> bool:
    t = text.lower().strip()

    positives = [
        "да", "ага", "ок", "окей", "хорошо",
        "давай", "согласен", "подходит",
        "делай", "генерируй", "создавай"
    ]

    return any(t == p or t.startswith(p + " ") for p in positives)


def is_rejection(text: str) -> bool:
    t = text.lower().strip()
    return t in ["нет", "не", "не так", "не то"]


def update_last_action(state, text):
    last = state.get("last_action")

    if not last or last.get("status") != "pending":
        return

    t = text.lower()

    if any(x in t for x in ["добавь", "еще", "ещё", "измени", "переделай"]):
        last["status"] = "refined"
        return

    if any(x in t for x in ["не так", "не то", "плохо", "неправильно", "ошибка", "нет"]):
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

    if is_followup(text):
        intent = "question"

    t = text.lower().strip()

    # ===== 🔥 КОНТЕКСТ (ИСПРАВЛЕННЫЙ) =====
    if is_followup(text) and not is_confirmation(text) and not is_rejection(text):
        old = state.get("last_image_prompt")

        if old:
            state["last_image_prompt"] = update_image_prompt(old, text)
        else:
            state["last_image_prompt"] = text

    # ===== 🔥 "ДА" → ГЕНЕРАЦИЯ =====
    last = state.get("last_action")

    if is_confirmation(text) and last and last.get("type") == "image":
        last_prompt = state.get("last_image_prompt")

        if last_prompt:
            ctx = get_image_context(user_id) or state.get("image_context")

            context = {
                "chat_id": chat_id,
                "state": state,
                "image": ctx,
                "anchor": get_anchor(user_id),
                "mode": mode,
                "task_type": "chat"
            }

            for room in ROOMS:
                try:
                    if room.can_handle(last_prompt, context):
                        result = await room.handle(
                            user_id,
                            last_prompt,
                            context,
                            run_with_typing
                        )

                        if result:
                            return result

                except Exception as e:
                    print(f"🔥 ROOM ERROR [confirm final]:", e)

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
            "type": "image" if ("изображ" in text or "картин" in text) else "text",
            "intent": "answer",
            "status": "pending"
        }

        if state["last_action"]["type"] == "image":
            state["last_image_prompt"] = text

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
                    if result.get("type") == "image":
                        state["last_action"] = {
                            "type": "image",
                            "intent": "generate",
                            "status": "pending"
                        }
                        state["last_image_prompt"] = text

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
