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

    ambiguity_level = semantic.get(
        "ambiguity_level",
        0.0
    )

    dialog_semantic_state = semantic.get(
        "dialog_state",
        "exploration"
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
        execution_pressure >= 0.72
    )

    dialog_overextended = (
        dialog_depth >= 10
        and conversation_value <= 0.5
    )

    high_confidence_execution = (
        capability_confidence >= 0.82
        and should_execute
    )

    # =================================================
    # 🔥 DIALOG CONTINUITY
    # =================================================

    unresolved_intent = True

    if (
        should_execute
        and ambiguity_level <= 0.25
        and execution_pressure >= 0.9
    ):

        unresolved_intent = False

    trajectory_active = True

    if dialog_depth <= 1:

        trajectory_active = False

    # =================================================
    # 🔥 REFLECTION STATE
    # =================================================

    needs_reflection = True

    if (
        should_execute
        and execution_pressure >= 0.9
        and ambiguity_level <= 0.2
    ):

        needs_reflection = False

    # =================================================
    # 🔥 POST RESPONSE AWARENESS
    # =================================================

    response_may_be_incomplete = False

    if (
        ambiguity_level >= 0.4
        or dialog_semantic_state == "exploration"
        or continuation
    ):

        response_may_be_incomplete = True

    # =================================================
    # 🔥 CAPABILITY SELF AWARENESS
    # =================================================

    capability_awareness = {

        "understands_capabilities": True,

        "capabilities_are_personal": True,

        "capabilities_are_supportive": True,

        "capabilities_should_follow_dialogue": True,

        "capabilities_should_not_interrupt":
            True,

        "visual_support_available": True,

        "execution_available": True,

        "guidance_available": True,

        "analysis_available": True,

        "continuation_priority": True
    }

    # =================================================
    # 🔥 INTERNAL DIALOGUE MONITOR
    # =================================================

    internal_monitor = {

        "enabled": True,

        "tracks_dialog_state": True,

        "tracks_user_direction": True,

        "tracks_trajectory": True,

        "tracks_unresolved_expectation": True,

        "tracks_response_usefulness": True,

        "tracks_psychological_continuity": True,

        "tracks_capability_relevance": True,

        "tracks_post_response_effect": True,

        "maintains_conversation_presence": True
    }

    # =================================================
    # 🔥 RESPONSE REFLECTION
    # =================================================

    reflection = {

        "enabled": True,

        "response_should_be_evaluated": True,

        "helpfulness_unknown": True,

        "trajectory_must_continue": True,

        "dialogue_not_finished": True,

        "avoid_premature_completion": True,

        "maintain_psychological_presence": True
    }

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

        "trajectory_active":
            trajectory_active,

        "trajectory_locked":
            continuation,

        "trajectory_priority": 1.0,

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
        # 🔥 DIALOG STATE
        # =================================================

        "dialog_state":
            dialog_semantic_state,

        "conversation_alive": True,

        "unresolved_intent":
            unresolved_intent,

        "response_may_be_incomplete":
            response_may_be_incomplete,

        "needs_reflection":
            needs_reflection,

        "preserve_continuity": True,

        "preserve_psychology": True,

        "preserve_trajectory": True,

        # =================================================
        # 🔥 STATE
        # =================================================

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
            high_confidence_execution,

        # =================================================
        # 🔥 INTERNAL MONITORING
        # =================================================

        "internal_monitor":
            internal_monitor,

        # =================================================
        # 🔥 REFLECTION
        # =================================================

        "reflection":
            reflection,

        # =================================================
        # 🔥 CAPABILITY AWARENESS
        # =================================================

        "capability_awareness":
            capability_awareness
    }

    return reasoning
