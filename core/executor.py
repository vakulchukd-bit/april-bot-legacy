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

from blocks.image_module import process as image_generate


# ===== 🔥 СТРУКТУРА СЦЕНЫ =====
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
    elif "звезда" in t:
        obj = "звезда"
    elif "шестиугольник" in t or "гексагон" in t:
        obj = "шестиугольник"
    elif "прямоугольник" in t:
        obj = "прямоугольник"
    elif "овал" in t:
        obj = "овал"

    if "на" in t:
        idx = t.find("на")
        scene = text[idx:]

    return scene.strip(), obj, color


def build_prompt(state):
    data = state.get("image_struct", {})
    return f"{data.get('color','')} {data.get('object','')} {data.get('scene','')}".strip()


# ===== БАЗОВЫЕ =====
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
    if not last or last.get("status") == "pending":
        return
    update_experience(user_id, state)


# ===== ОСНОВА =====
async def execute(user_id, text, chat_id, run_with_typing):
    state = get_state(user_id)
    mode = get_mode(user_id)

    update_last_action(state, text)
    commit_last_action(user_id, state)

    intent = detect_intent(text)

    if is_followup(text):
        intent = "question"

    t = text.lower().strip()

    # ===== 🔥 ГЛАВНЫЙ ФИКС: ПЕРЕСБОРКА STATE =====
    if is_followup(text) and not is_confirmation(text) and not is_rejection(text):

        old = state.get("image_struct", {})

        new_scene, new_obj, new_color = extract_scene_object(text)

        updated = {
            "scene": new_scene or old.get("scene", ""),
            "object": new_obj or old.get("object", ""),
            "color": new_color or old.get("color", "")
        }

        state["image_struct"] = updated

    # ===== 🔥 SNAPSHOT =====
    last = state.get("last_action")

    if is_confirmation(text) and last and last.get("type") == "image":

        final_struct = state.get("image_struct", {}).copy()
        final_prompt = build_prompt({"image_struct": final_struct})

        if final_prompt:
            clean_state = {
                "image_struct": final_struct
            }

            result = await run_with_typing(
                chat_id,
                image_generate(user_id, final_prompt, clean_state)
            )

            if result:
                state["last_action"] = None
                state["image_context"] = None
                state["last_render_struct"] = final_struct
                return result

    # ===== DEBUG =====
    if text == "/exp":
        data = load_experience()
        return {
            "type": "text",
            "data": f"🧠 Опыт:\n{data.get(str(user_id), {})}"
        }

    # ===== ENGINEERING =====
    if mode == "engineering" and not text.startswith("/"):
        if text.lower() == "/analiz":
            return {"type": "text", "data": "📥 Жду код..."}
        return {"type": "admin_report", "data": analyze_code(text)}

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

        text = f"{build_context_text()}\n\n{text}"

        result = await run_with_typing(
            chat_id,
            text_process(user_id, text, state)
        )

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

        return {"type": "text", "data": result["content"]}

    # ===== ROOMS =====
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
                result = await room.handle(user_id, text, context, run_with_typing)

                if result and result.get("type") == "image":
                    state["last_action"] = {
                        "type": "image",
                        "intent": "generate",
                        "status": "pending"
                    }

                if result:
                    return result

        except Exception as e:
            print(f"🔥 ROOM ERROR [{room.name}]:", e)

    result = await run_with_typing(
        chat_id,
        text_process(user_id, text, state)
    )

    return {"type": "text", "data": result["content"]}
