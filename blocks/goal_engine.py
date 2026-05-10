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

    ambiguity_level = semantic.get(
        "ambiguity_level",
        0.0
    )

    dialog_state = semantic.get(
        "dialog_state",
        "exploration"
    )

    # =================================================
    # 🔥 TRAJECTORY DEFAULT
    # =================================================

    semantic["trajectory_active"] = True

    semantic["goal_persistent"] = True

    semantic["goal_completed"] = False

    semantic["conversation_alive"] = True

    semantic["unresolved_intent"] = True

    semantic["preserve_flow"] = True

    semantic["preserve_trajectory"] = True

    semantic["response_requires_reflection"] = True

    # =================================================
    # 🔥 EXPLORATION PROTECTION
    # =================================================

    exploration_words = [
        "примерно",
        "идея",
        "вариант",
        "что умеешь",
        "как думаешь",
        "посмотрим",
        "подумаем",
        "референс",
        "атмосфера"
    ]

    exploration_detected = any(
        w in t
        for w in exploration_words
    )

    if exploration_detected:

        semantic["goal"] = "exploration"

        semantic["goal_stage"] = "exploration"

        semantic["response_mode"] = "guide"

        semantic["should_execute"] = False

        semantic["goal_completed"] = False

        semantic["unresolved_intent"] = True

        semantic["conversation_alive"] = True

        semantic["capability_should_wait"] = True

    # =================================================
    # 🔥 EXECUTION ESCALATION
    # =================================================

    if (
        should_execute
        and capability_confidence >= 0.72
        and ambiguity_level < 0.45
        and not semantic.get(
            "capability_should_wait",
            False
        )
    ):

        semantic["goal"] = "execution"

        semantic["response_mode"] = "execute"

        semantic["goal_stage"] = "execution"

        semantic["goal_completed"] = False

        semantic["unresolved_intent"] = True

    # =================================================
    # 🔥 ACTIVE FLOW
    # =================================================

    if active:

        flow_type = active.get(
            "type"
        )

        semantic["continuation"] = True

        semantic["trajectory_active"] = True

        semantic["preserve_flow"] = True

        # =================================================
        # 🖼 IMAGE TRAJECTORY
        # =================================================

        if flow_type == "image":

            # 🔥 image continuation authority
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

                semantic[
                    "goal_completed"
                ] = False

                semantic[
                    "unresolved_intent"
                ] = True

                semantic[
                    "conversation_alive"
                ] = True

                return semantic

            # 🔥 lightweight continuation
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
                            0.82
                        ),

                    "continuation":
                        True,

                    "continuation_target":
                        "image",

                    "goal_stage":
                        "continuation",

                    "response_mode":
                        "guide",

                    "should_execute":
                        False,

                    "goal_completed":
                        False,

                    "conversation_alive":
                        True,

                    "unresolved_intent":
                        True
                })

                # 🔥 only explicit edit escalates
                explicit_edit_words = [
                    "измени",
                    "убери",
                    "добавь",
                    "замени"
                ]

                if any(
                    w in t
                    for w in explicit_edit_words
                ):

                    semantic[
                        "response_mode"
                    ] = "execute"

                    semantic[
                        "should_execute"
                    ] = True

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

                semantic[
                    "goal_completed"
                ] = False

                semantic[
                    "unresolved_intent"
                ] = True

                semantic[
                    "conversation_alive"
                ] = True

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
                            0.82
                        ),

                    "continuation":
                        True,

                    "continuation_target":
                        "math",

                    "goal_stage":
                        "continuation",

                    "response_mode":
                        "guide",

                    "should_execute":
                        False,

                    "goal_completed":
                        False,

                    "conversation_alive":
                        True,

                    "unresolved_intent":
                        True
                })

                # 🔥 explicit math execution only
                explicit_math_words = [
                    "реши",
                    "посчитай",
                    "построй",
                    "вычисли"
                ]

                if any(
                    w in t
                    for w in explicit_math_words
                ):

                    semantic[
                        "response_mode"
                    ] = "execute"

                    semantic[
                        "should_execute"
                    ] = True

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
            0.45
        )

        # 🔥 fatigue больше НЕ форсит execution
        semantic["response_economy"] = (
            "minimal"
        )

        semantic["preserve_flow"] = True

    # =================================================
    # 🔥 GOAL STABILITY
    # =================================================

    if dialog_state == "exploration":

        semantic["goal_completed"] = False

        semantic["conversation_alive"] = True

        semantic["unresolved_intent"] = True

    # =================================================
    # 🔥 FINAL SAFETY
    # =================================================

    if semantic.get(
        "capability_should_wait"
    ):

        semantic["should_execute"] = False

        semantic["response_mode"] = "guide"

    # =================================================
    # 🔥 DEFAULT
    # =================================================

    return semantic
