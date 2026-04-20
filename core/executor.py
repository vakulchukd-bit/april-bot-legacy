from blocks.router_system import decide_action
from blocks.response_mode import detect_response_mode
from blocks.image_module import process as image_generate, retry_process
from blocks.image_edit_module import process as image_edit
from blocks.text_module import process as text_process

from blocks.intent_system import detect_intent

from blocks.state_manager import (
    get_state,
    get_image_context,
    get_awaiting,
    set_awaiting,
    set_last_prompt
)

from blocks.anchor_system import get_anchor, update_anchor
from blocks.image_system import analyze_image
from blocks.mode_manager import get_mode, set_mode, clear_mode

from blocks.context_system import build_context_text


async def execute(user_id, text, chat_id, run_with_typing):
    state = get_state(user_id)
    mode = get_mode(user_id)

    intent = detect_intent(text)

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

        if not ctx or not ctx["path"]:
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

    # ===== ROUTER =====
    decision = decide_action(text, state["dialog"])
    action = decision["action"]

    mode_response = detect_response_mode(text)

    # ===== IMAGE GENERATE =====
    if action == "image":
        clear_mode(user_id)

        result = await run_with_typing(
            chat_id,
            image_generate(user_id, text, state)
        )

        if result.get("type") == "image":
            return {
                "type": "image",
                "data": result["data"]
            }

        if result.get("type") == "retry_notice":
            return {
                "type": "retry",
                "data": result["data"],
                "retry": True,
                "text": text
            }

        return {
            "type": "text",
            "data": "⚠️ Ошибка генерации изображения"
        }

    # ===== IMAGE EDIT =====
    if mode == "image_edit" or get_awaiting(user_id):
        set_mode(user_id, "image_edit")
        set_awaiting(user_id, False)

        ctx = get_image_context(user_id)
        if not ctx or not ctx["path"]:
            clear_mode(user_id)
            return {
                "type": "text",
                "data": "❌ Нет изображения"
            }

        if not ctx["hint"]:
            try:
                ctx["hint"] = await analyze_image(ctx["path"])
            except:
                ctx["hint"] = "изображение"

        anchor = get_anchor(user_id)
        base = anchor["current"] if anchor else ctx["hint"]

        new_prompt = base + ", IMPORTANT: " + text

        result = await run_with_typing(
            chat_id,
            image_edit(user_id, ctx["path"], new_prompt)
        )

        if result.get("type") == "error":
            clear_mode(user_id)
            return {
                "type": "text",
                "data": "⚠️ Ошибка редактирования изображения"
            }

        set_last_prompt(user_id, new_prompt)
        update_anchor(user_id, new_prompt)

        clear_mode(user_id)  # 🔥 ВОТ ГЛАВНЫЙ ФИКС

        return {
            "type": "image",
            "data": result["data"]
        }

    # ===== TEXT =====
    clear_mode(user_id)

    anchor = get_anchor(user_id)
    if anchor:
        text = f"Контекст: {anchor['current']}\n\n{text}"

    context = build_context_text()
    text = f"{context}\n\n{text}"

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
