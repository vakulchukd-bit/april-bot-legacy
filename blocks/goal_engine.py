def detect_goal(
    text: str,
    state: dict,
    semantic: dict
):

    semantic = semantic or {}

    t = text.lower().strip()

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
    # 🔥 SEMANTIC VALUES
    # =================================================

    execution_pressure = semantic.get(
        "execution_pressure",
        0.0
    )

    capability_confidence = semantic.get(
        "capability_confidence",
        0.5
    )

    should_execute = semantic.get(
        "should_execute",
        False
    )

    semantic_room = semantic.get(
        "room"
    )

    semantic_intent = semantic.get(
        "intent"
    )

    # =================================================
    # 🔥 EXECUTION ESCALATION
    # =================================================

    if (
        should_execute
        and capability_confidence >= 0.7
    ):

        semantic["goal"] = "execution"

        semantic["response_mode"] = "execute"

        semantic["goal_stage"] = "execution"

    # =================================================
    # 🔥 ACTIVE FLOW
    # =================================================

    if active:

        flow_type = active.get(
            "type"
        )

        # =================================================
        # 🖼 IMAGE TRAJECTORY
        # =================================================

        if flow_type == "image":

            # 🔥 semantic image authority
            if semantic_room in [
                "image_generate",
                "image_edit"
            ]:

                semantic["goal"] = (
                    "continue_image"
                )

                semantic["continuation"] = True

                semantic[
                    "continuation_target"
                ] = "image"

                return semantic

            # 🔥 unresolved image continuation
            if (
                execution_pressure >= 0.45
                or len(t) <= 50
            ):

                semantic.update({

                    "goal":
                        "continue_image",

                    "room":
                        "image_edit",

                    "intent":
                        "image_edit",

                    "confidence":
                        max(
                            semantic.get(
                                "confidence",
                                0.5
                            ),
                            0.85
                        ),

                    "continuation":
                        True,

                    "continuation_target":
                        "image",

                    "goal_stage":
                        "execution",

                    "response_mode":
                        "execute",

                    "should_execute":
                        True
                })

                return semantic

        # =================================================
        # 📈 MATH TRAJECTORY
        # =================================================

        if flow_type == "math":

            if semantic_room == "science":

                semantic["goal"] = (
                    "continue_math"
                )

                semantic["continuation"] = True

                semantic[
                    "continuation_target"
                ] = "math"

                return semantic

            if (
                execution_pressure >= 0.4
                or len(t) <= 50
            ):

                semantic.update({

                    "goal":
                        "continue_math",

                    "room":
                        "science",

                    "intent":
                        "math",

                    "confidence":
                        max(
                            semantic.get(
                                "confidence",
                                0.5
                            ),
                            0.85
                        ),

                    "continuation":
                        True,

                    "continuation_target":
                        "math",

                    "goal_stage":
                        "execution",

                    "response_mode":
                        "execute",

                    "should_execute":
                        True
                })

                return semantic

    # =================================================
    # 🔥 DIALOG FATIGUE
    # =================================================

    if len(dialog) >= 12:

        semantic["conversation_value"] = min(
            semantic.get(
                "conversation_value",
                1.0
            ),
            0.4
        )

        if (
            semantic.get(
                "execution_pressure",
                0.0
            ) >= 0.45
        ):

            semantic["response_mode"] = (
                "execute"
            )

            semantic["should_execute"] = True

    # =================================================
    # 🔥 DEFAULT
    # =================================================

    return semantic
