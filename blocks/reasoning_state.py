def build_reasoning_state(
    text: str,
    state: dict,
    semantic: dict = None
):

    semantic = semantic or {}

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
    # 🔥 DIALOG DEPTH
    # =================================================

    dialog_depth = len(dialog)

    # =================================================
    # 🔥 EXECUTION STATE
    # =================================================

    execution_pressure = semantic.get(
        "execution_pressure",
        0.0
    )

    should_execute = semantic.get(
        "should_execute",
        False
    )

    response_mode = semantic.get(
        "response_mode",
        "talk"
    )

    goal_stage = semantic.get(
        "goal_stage",
        "exploration"
    )

    response_economy = semantic.get(
        "response_economy",
        "balanced"
    )

    capability_confidence = semantic.get(
        "capability_confidence",
        0.5
    )

    conversation_value = semantic.get(
        "conversation_value",
        1.0
    )

    attention_weight = semantic.get(
        "attention_weight",
        0.5
    )

    # =================================================
    # 🔥 CONTINUATION STATE
    # =================================================

    continuation = semantic.get(
        "continuation",
        False
    )

    continuation_target = semantic.get(
        "continuation_target"
    )

    # =================================================
    # 🔥 COGNITIVE FLAGS
    # =================================================

    user_waiting_action = (
        execution_pressure >= 0.7
    )

    dialog_overextended = (
        dialog_depth >= 10
        and conversation_value <= 0.5
    )

    high_confidence_execution = (
        capability_confidence >= 0.8
        and should_execute
    )

    # =================================================
    # 🔥 BUILD
    # =================================================

    reasoning = {

        # =================================================
        # 🔥 INPUT
        # =================================================

        "input": text,

        "summary": summary,

        # =================================================
        # 🔥 SEMANTIC
        # =================================================

        "semantic": semantic,

        # =================================================
        # 🔥 FLOW
        # =================================================

        "active_flow": active_flow,

        "continuation": continuation,

        "continuation_target":
            continuation_target,

        "goal_stage": goal_stage,

        # =================================================
        # 🔥 EXECUTION
        # =================================================

        "execution_pressure":
            execution_pressure,

        "should_execute":
            should_execute,

        "response_mode":
            response_mode,

        "response_economy":
            response_economy,

        "capability_confidence":
            capability_confidence,

        # =================================================
        # 🔥 DIALOG QUALITY
        # =================================================

        "conversation_value":
            conversation_value,

        "attention_weight":
            attention_weight,

        "dialog_depth":
            dialog_depth,

        "dialog_overextended":
            dialog_overextended,

        # =================================================
        # 🔥 STATE
        # =================================================

        "dialog_state": dialog_state,

        "image_context": image_context,

        "last_math": last_math,

        "last_code": last_code,

        # =================================================
        # 🔥 MEMORY
        # =================================================

        "last_user": last_user,

        "last_assistant": last_assistant,

        # =================================================
        # 🔥 COGNITIVE FLAGS
        # =================================================

        "user_waiting_action":
            user_waiting_action,

        "high_confidence_execution":
            high_confidence_execution
    }

    return reasoning
