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


# ===== 🔥 НОВОЕ: СТРУКТУРА СЦЕНЫ =====
def extract_scene_object(text: str):
    t = text.lower()

    scene = ""
    obj = ""
    color = ""

    colors = ["красный", "синий", "зелёный", "жёлтый", "чёрный", "белый"]

    for c in colors:
        if c in t:
            color = c
            break

    if "треугольник" in t:
        obj = "треугольник"
    elif "круг" in t:
        obj = "круг"
    elif "ромб" in t:
        obj = "ромб"
    elif "квадрат" in t:
        obj = "квадрат"

    # сцена (всё после "на")
    if "на" in t:
        idx = t.find("на")
        scene = text[idx:]

    return scene.strip(), obj, color


def build_prompt(state):
    data = state.get("image_struct", {})

    scene = data.get("scene", "")
    obj = data.get("object", "")
    color = data.get("color", "")

    return f"{color} {obj} {scene}".strip()


# ===== БАЗОВЫЕ ФУНКЦИИ =====
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


# ===== ОСНОВНАЯ ЛОГИКА =====
async def execute(user_id, text, chat_id, run_with_typing):
    state = get_state(user_id)
    mode = get_mode(user_id)

    update_last_action(state, text)
    commit_last_action(user_id, state)

    intent = detect_intent(text)

    if is_followup(text):
        intent = "question"

    t = text.lower().strip()

    # ===== 🔥 ОБНОВЛЕНИЕ СТРУКТУРЫ ПРИ УТОЧНЕНИЯХ =====
    if is_followup(text) and not is_confirmation(text) and not is_rejection(text):
        data = state.get("image_struct", {})

        if "синий" in t:
            data["color"] = "синий"
        elif "зелёный" in t:
            data["color"] = "зелёный"
        elif "красный" in t:
            data["color"] = "красный"
        elif "жёлтый" in t:
            data["color"] = "жёлтый"

        state["image_struct"] = data

    # ===== 🔥 ПОДТВЕРЖДЕНИЕ =====
    last = state.get("last_action")

    if is_confirmation(text) and last and last.get("type") == "image":
        final_prompt = build_prompt(state)

        if final_prompt:
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
                    if room.can_handle(final_prompt, context):
                        result = await room.handle(
                            user_id,
                            final_prompt,
                            context,
                            run_with_typing
                        )

                        if result:
                            return result

                except Exception as e:
                    print(f"🔥 ROOM ERROR [scene system]:", e)

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

        # ===== 🔥 СОХРАНЯЕМ СЦЕНУ =====
        scene, obj, color = extract_scene_object(text)

        state["image_struct"] = {
            "scene": scene,
            "object": obj,
            "color": color
        }

        state["last_action"] = {
            "type": "image" if ("изображ" in text or "картин" in text) else "text",
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
                    if result.get("type") == "image":
                        state["last_action"] = {
                            "type": "image",
                            "intent": "generate",
                            "status": "pending"
                        }

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
