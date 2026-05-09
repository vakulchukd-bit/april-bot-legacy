def detect_goal(
    text: str,
    state: dict,
    semantic: dict
):

    t = text.lower()

    active = state.get(
        "active_flow"
    )

    dialog = state.get(
        "dialog",
        []
    )

    last_user = None

    # =================================================
    # 🔥 LAST USER MESSAGE
    # =================================================

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
    # 🔥 ACTIVE FLOW
    # =================================================

    if active:

        flow_type = active.get(
            "type"
        )

        # =================================================
        # 🖼 IMAGE CONTINUATION
        # =================================================

        if flow_type == "image":

            semantic_room = semantic.get(
                "room"
            )

            semantic_intent = semantic.get(
                "intent"
            )

            # 🔥 semantic continuation
            if semantic_room in [
                "image_generate",
                "image_edit"
            ]:
                return semantic

            # 🔥 short continuation
            if len(t) <= 40:

                return {
                    "goal": "continue_image",
                    "room": "image_edit",
                    "intent": "image_edit",
                    "confidence": 0.85
                }

        # =================================================
        # 📈 MATH CONTINUATION
        # =================================================

        if flow_type == "math":

            semantic_room = semantic.get(
                "room"
            )

            if semantic_room == "science":
                return semantic

            if len(t) <= 40:

                return {
                    "goal": "continue_math",
                    "room": "science",
                    "intent": "math",
                    "confidence": 0.85
                }

    # =================================================
    # 🔥 SEMANTIC DEFAULT
    # =================================================

    return semantic
