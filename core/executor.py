from blocks.response_mode import detect_response_mode
from blocks.text_module import process as text_process

from core.interpreter import interpret

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


def detect_task_type(text: str) -> str:
    t = text.lower().strip()

    if any(x in t for x in ["+", "-", "*", "/", "="]):
        return "math"

    if t.startswith("/"):
        return "command"

    return "chat"


async def execute(user_id, text, chat_id, run_with_typing):
    state = get_state(user_id)
    mode = get_mode(user_id)

    ctx = get_image_context(user_id) or state.get("image_context")
    anchor = get_anchor(user_id)

    interpret_data = interpret(text, state, anchor, ctx)
    intent = interpret_data["intent"]

    if mode == "engineering" and not text.startswith("/"):
        if text.lower() == "/analiz":
            return {"type": "text", "data": "📥 Жду код..."}
        return {"type": "admin_report", "data": analyze_code(text)}

    t = text.lower().strip()

    # ===== БЫСТРЫЕ ОТВЕТЫ =====
    if t == "привет":
        return {"type": "text", "data": "Привет 🙂"}

    if t == "2+2":
        return {"type": "text", "data": "4"}

    # ===== ВРЕМЯ =====
    if "время" in t or "час" in t:
        time_str = state.get("time_str")
        weekday = state.get("weekday")
        date_str = state.get("date_str")

        if time_str:
            return {
                "type": "text",
                "data": f"Сейчас {time_str} • {weekday}, {date_str} (Europe/Kyiv)"
            }

    # ===== 🚀 ГЕНЕРАЦИЯ С УЧЁТОМ КОНТЕКСТА =====
    if intent == "generate_image":
        if anchor:
            text = f"{anchor['current']}\n\n{text}"

    # ===== 🚫 НЕ ГЕНЕРИМ ПОВЕРХ ФОТО =====
    if ctx and ctx.get("path") and intent == "generate_image":
        return {
            "type": "text",
            "data": "У тебя уже есть изображение 📷\n\nХочешь изменить его или создать новое?"
        }

    # ===== ROOMS =====
    context = {
        "chat_id": chat_id,
        "state": state,
        "image": ctx,
        "anchor": anchor,
        "mode": mode,
        "intent": intent
    }

    for room in ROOMS:
        try:
            if room.can_handle(text, context):
                result = await room.handle(user_id, text, context, run_with_typing)
                if result:
                    return result
        except Exception as e:
            print(f"🔥 ROOM ERROR [{room.name}]:", e)

    # ===== УСИЛЕНИЕ =====
    if intent == "describe_image" and ctx:
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

    return {
        "type": "text",
        "data": result["content"]
    }
