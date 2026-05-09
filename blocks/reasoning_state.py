def build_reasoning_state(
    text: str,
    state: dict,
    semantic: dict = None
):

    dialog = state.get(
        "dialog",
        []
    )

    summary = state.get(
        "memory_summary",
        ""
    )

    active_flow = state.get(
        "active_flow"
    )

    dialog_state = state.get(
        "dialog_state",
        {}
    )

    image_context = state.get(
        "image_context"
    )

    last_math = state.get(
        "last_math"
    )

    last_code = state.get(
        "last_code"
    )

    # =================================================
    # 🔥 LAST USER
    # =================================================

    last_user = None

    for msg in reversed(dialog):

        if msg.get("role") == "user":

            content = (
                msg.get("content")
                or ""
            ).strip()

            if content != text:

                last_user = content
                break

    # =================================================
    # 🔥 LAST ASSISTANT
    # =================================================

    last_assistant = None

    for msg in reversed(dialog):

        if msg.get("role") == "assistant":

            last_assistant = (
                msg.get("content")
                or ""
            )

            break

    # =================================================
    # 🔥 BUILD
    # =================================================

    reasoning = {

        "input": text,

        "semantic": semantic or {},

        "summary": summary,

        "active_flow": active_flow,

        "dialog_state": dialog_state,

        "image_context": image_context,

        "last_math": last_math,

        "last_code": last_code,

        "last_user": last_user,

        "last_assistant": last_assistant,
    }

    return reasoning
