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


# ===== ВОПРОС =====
def is_question(text: str) -> bool:
    t = text.lower()

    if "?" in t:
        return True

    question_words = [
        "что", "кто", "как", "почему",
        "зачем", "можешь", "умеешь", "если", "а ты"
    ]

    return any(x in t for x in question_words)


# ===== ПОДТВЕРЖДЕНИЕ =====
def is_confirm(text: str) -> bool:
    t = text.lower().strip()

    if len(t.split()) <= 3:
        if any(x in t for x in [
            "да", "давай", "делай", "ок",
            "хорошо", "поехали", "начинай"
        ]):
            return True

    if any(x in t for x in [
        "я хочу", "я бы хотел", "сделай",
        "давай сделаем", "сгенерируй", "создай"
    ]):
        return True

    return False


# ===== ГОТОВНОСТЬ =====
def is_ready_to_generate(state, text, anchor):
    if state.get("last_prompt"):
        return True

    if anchor and len(anchor.get("current", "").split()) > 3:
        return True

    if len(text.split()) > 4:
        return True

    return False


async def execute(user_id, text, chat_id, run_with_typing):
    state = get_state(user_id)
    mode = get_mode(user_id)

    ctx = get_image_context(user_id) or state.get("image_context")
    anchor = get_anchor(user_id)

    interpret_data = interpret(text, state, anchor, ctx)
    intent = interpret_data["intent"]

    t = text.lower().strip()

    question = is_question(text)
    confirm = is_confirm(text)

    # ===== БЛОК ВОПРОСОВ =====
    if intent == "generate_image" and question and not confirm:
        intent = "question"

    # ===== ФИКСАЦИЯ НАМЕРЕНИЯ =====
    if intent in ["generate_image", "edit_image"] and not question:
        state["pending_action"] = intent

        if anchor:
            state["last_prompt"] = anchor["current"]
        else:
            state["last_prompt"] = text

    # ===== ПОДТВЕРЖДЕНИЕ =====
    if state.get("pending_action") and confirm:
        intent = state["pending_action"]

    # ===== СБРОС =====
    if intent not in ["generate_image", "edit_image"]:
        if state.get("pending_action") and not confirm:
            state["pending_action"] = None

    # ===== ENGINEERING =====
    if mode == "engineering" and not text.startswith("/"):
        if text.lower() == "/analiz":
            return {"type": "text", "data": "📥 Жду код..."}
        return {"type": "admin_report", "data": analyze_code(text)}

    # ===== ПРОСТОЕ =====
    if t == "привет":
        return {"type": "text", "data": "Привет 🙂"}

    if t == "2+2":
        return {"type": "text", "data": "4"}

    # ===== ВРЕМЯ (ТОЛЬКО ЯВНО) =====
    if ("время" in t or "час" in t) and len(t.split()) <= 5:
        time_str = state.get("time_str")
        weekday = state.get("weekday")
        date_str = state.get("date_str")

        if time_str:
            return {
                "type": "text",
                "data": f"Сейчас {time_str} • {weekday}, {date_str} (Europe/Kyiv)"
            }

    # ===== ЗАЩИТА =====
    if ctx and ctx.get("path") and intent == "generate_image":
        return {
            "type": "text",
            "data": "У тебя уже есть изображение 📷\n\nХочешь изменить его или создать новое?"
        }

    # =========================================================
    # 🔥 ГЛАВНЫЙ ФИКС — ГАРАНТИЯ ГЕНЕРАЦИИ
    # =========================================================
    if intent == "generate_image":

        ready = is_ready_to_generate(state, text, anchor)

        if not ready and not confirm:
            return {
                "type": "text",
                "data": "Опиши, какую именно картинку ты хочешь 🙂"
            }

        context = {
            "chat_id": chat_id,
            "state": state,
            "image": ctx,
            "anchor": anchor,
            "mode": mode,
            "intent": "generate_image"
        }

        for room in ROOMS:
            if room.name == "image_generate":

                result = await room.handle(user_id, text, context, run_with_typing)

                # ❗ КРИТИЧНО: НЕТ ФОЛБЭКА В TEXT
                if not result:
                    return {
                        "type": "text",
                        "data": "⚠️ Генерация не сработала. Попробуй ещё раз."
                    }

                return result

    # ===== ОБЫЧНЫЕ КОМНАТЫ =====
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

    # ===== TEXT =====
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
