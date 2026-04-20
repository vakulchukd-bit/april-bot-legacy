# core/executor.py

from blocks.router_system import decide_action
from blocks.response_mode import detect_response_mode
from blocks.image_module import process as image_process
from blocks.text_module import process as text_process
from blocks.state_manager import (
    get_state,
    get_image_context,
    get_awaiting,
    set_awaiting,
    set_last_prompt
)
from blocks.anchor_system import get_anchor, update_anchor
from blocks.image_system import analyze_image


async def execute(user_id, text, chat_id, run_with_typing):
    state = get_state(user_id)

    # ===== 🧠 ПРОВЕРКА: РЕДАКТИРОВАНИЕ =====
    if get_awaiting(user_id):
        set_awaiting(user_id, False)

        ctx = get_image_context(user_id)
        if not ctx:
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
            image_process(user_id, new_prompt, {})
        )

        set_last_prompt(user_id, new_prompt)
        update_anchor(user_id, new_prompt)

        return {
            "type": "image",
            "data": result["data"],
            "edit": True
        }

    # ===== 🧠 ОБЫЧНАЯ ЛОГИКА =====
    decision = decide_action(text, state["dialog"])
    action = decision["action"]

    mode = detect_response_mode(text)

    # ===== IMAGE (НОВАЯ) =====
    if action == "image":
        result = await run_with_typing(
            chat_id,
            image_process(user_id, text, state)
        )

        return {
            "type": "image",
            "data": result["data"],
            "edit": False
        }

    # ===== TEXT =====
    anchor = get_anchor(user_id)
    if anchor:
        text = f"Контекст: {anchor['current']}\n\n{text}"

    result = await run_with_typing(
        chat_id,
        text_process(user_id, text, state)
    )

    reply = result["content"]

    if mode == "copy":
        clean = reply.replace("```", "").strip()
        reply = f"```text\n{clean}\n```"

    return {
        "type": "text",
        "data": reply
    }
