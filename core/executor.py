from blocks.response_mode import detect_response_mode
from blocks.text_module import process as text_process

from blocks.intent_system import detect_intent

from blocks.state_manager import (
    get_state,
    get_image_context
)

from blocks.anchor_system import get_anchor
from blocks.image_system import analyze_image
from blocks.mode_manager import get_mode, clear_mode

from blocks.context_system import build_context_text

# 🔥 НОВОЕ — КОМНАТЫ
from blocks.rooms_registry import ROOMS


async def execute(user_id, text, chat_id, run_with_typing):
    state = get_state(user_id)
    mode = get_mode(user_id)

    intent = detect_intent(text)

    # ===== 🔥 ФИКС: НОРМАЛЬНОЕ ВРЕМЯ =====
    lower_text = text.lower()
    if "время" in lower_text or "час" in lower_text:
        time_str = state.get("time_str")
        weekday = state.get("weekday")
        date_str = state.get("date_str")

        if time_str:
            return {
                "type": "text",
                "data": f"Сейчас {time_str} • {weekday}, {date_str} (Europe/Kyiv)"
            }
    # ===== КОНЕЦ =====

    # ===== MEMORY =====
    if intent == "memory":
        anchor = get_anchor(user_id)

        if not anchor:
            return {
                "type": "text",
                "data": "🤔 Я пока ничего не запомнил"
            }

        return {
            "type": "text",
            "data": f"🧠 Последний контекст:\n{anchor['current']}"
        }

    # ===== ANALYZE =====
    if intent == "analyze":
        ctx = get_image_context(user_id)

        if not ctx:
            ctx = state.get("image_context")

        if not ctx or not ctx.get("path"):
            return {
                "type": "text",
                "data": "❌ Нет изображения для анализа"
            }

        try:
            hint = await analyze_image(ctx["path"])
        except:
            hint = "не удалось определить"

        return {
            "type": "text",
            "data": f"📷 На изображении: {hint}"
        }

    # ===== КОНТЕКСТ =====
    ctx = get_image_context(user_id)

    if not ctx:
        ctx = state.get("image_context")

    anchor = get_anchor(user_id)

    context = {
        "chat_id": chat_id,
        "state": state,
        "image": ctx,
        "anchor": anchor,
        "mode": mode
    }

    mode_response = detect_response_mode(text)

    # ===== КОМНАТЫ =====
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

    # ===== TEXT =====
    clear_mode(user_id)

    # 🔥 КАРТИНКА
    if ctx and ctx.get("path"):
        try:
            hint = await analyze_image(ctx["path"])
            text = f"На изображении: {hint}\n\n{text}"
        except:
            pass

    if anchor:
        text = f"Контекст: {anchor['current']}\n\n{text}"

    # ===== 🔥 НОВЫЙ КОНТЕКСТ ВРЕМЕНИ =====
    try:
        time_str = state.get("time_str")

        if time_str:
            time_context = f"Текущее время пользователя: {time_str} (Europe/Kyiv)"
            text = f"{time_context}\n\n{text}"

    except Exception as e:
        print("🔥 TIME ERROR:", e)

    # ===== КОНТЕКСТ МИРА =====
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

    return {
        "type": "text",
        "data": reply
    }
