# core/executor.py

from blocks.router_system import decide_action
from blocks.response_mode import detect_response_mode
from blocks.image_module import process as image_process
from blocks.text_module import process as text_process
from blocks.state_manager import get_state
from blocks.anchor_system import get_anchor


async def execute(user_id, text, chat_id, run_with_typing):
    state = get_state(user_id)

    decision = decide_action(text, state["dialog"])
    action = decision["action"]

    mode = detect_response_mode(text)

    # ===== IMAGE =====
    if action == "image":
        result = await run_with_typing(
            chat_id,
            image_process(user_id, text, state)
        )

        return {
            "type": "image",
            "data": result["data"]
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
