from blocks.response_mode import detect_response_mode
from blocks.text_module import process as text_process

from blocks.intent_system import detect_intent

from blocks.state_manager import (
    get_state,
    get_image_context
)

from blocks.anchor_system import get_anchor
from blocks.mode_manager import get_mode

from blocks.context_system import build_context_text

from blocks.rooms_registry import ROOMS
from blocks.engineering_system import analyze_code

from blocks.experience_manager import load_experience

from blocks.image_module import process as image_generate


# ===== СТРУКТУРА =====
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


def build_prompt(struct):
    return f"{struct.get('color','')} {struct.get('object','')} {struct.get('scene','')}".strip()


# ===== ЛОГИКА =====
def is_followup(text: str):
    t = text.lower()
    return any(x in t for x in ["сделай", "измени", "добавь", "поменяй"])


def is_confirmation(text: str):
    t = text.lower().strip()

    positives = [
        "да", "ага", "ок", "окей", "давай",
        "хорошо", "ладно", "согласен",
        "делай", "поехали", "го",
        "запускай", "генерируй"
    ]

    return any(p in t for p in positives)


def is_rejection(text: str):
    t = text.lower().strip()
    return any(x in t for x in ["нет", "не", "не надо", "отмена"])


# ===== EXECUTE =====
async def execute(user_id, text, chat_id, run_with_typing):
    state = get_state(user_id)
    mode = get_mode(user_id)

    t = text.lower().strip()

    # ===== 1. ПОДТВЕРЖДЕНИЕ =====
    last = state.get("last_action")

    if is_confirmation(text) and last and last.get("type") == "image":

        final_struct = state.get("pending_render")

        if final_struct:
            final_prompt = build_prompt(final_struct)

            state["image_context"] = None

            result = await run_with_typing(
                chat_id,
                image_generate(user_id, final_prompt, {"image_struct": final_struct})
            )

            if result:
                state["pending_render"] = None
                state["last_action"] = None
                return result

    # ===== 2. ОТМЕНА =====
    if is_rejection(text) and state.get("pending_render"):
        state["pending_render"] = None
        state["last_action"] = None

        return {
            "type": "text",
            "data": "Ок, отменил 👍"
        }

    # ===== 3. ИЗМЕНЕНИЯ =====
    if is_followup(text):

        old = state.get("image_struct", {})

        new_scene, new_obj, new_color = extract_scene_object(text)

        updated = {
            "scene": new_scene or old.get("scene", ""),
            "object": new_obj or old.get("object", ""),
            "color": new_color or old.get("color", "")
        }

        state["image_struct"] = updated
        state["pending_render"] = updated.copy()

        state["last_action"] = {
            "type": "image",
            "intent": "modify",
            "status": "pending"
        }

        return {
            "type": "text",
            "data": f"Ок, делаю: {build_prompt(updated)}.\nПодтвердить?"
        }

    # ===== 4. НЕПОНЯТНЫЙ ОТВЕТ =====
    if state.get("pending_render"):
        return {
            "type": "text",
            "data": "Подтвердить генерацию? Напиши «да» или «нет» 🙂"
        }

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

    # ===== ВОПРОС =====
    intent = detect_intent(text)

    if intent == "question":

        anchor = get_anchor(user_id)

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

        state["pending_render"] = state["image_struct"].copy()

        state["last_action"] = {
            "type": "image",
            "intent": "create",
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
