def build_reasoning_state(
    text: str,
    state: dict,
    semantic: dict = None
):

    """
    DeepHub Reasoning State

    Главная задача:
    reasoning больше НЕ должен
    заново пересчитывать весь диалог.

    Теперь reasoning:
    - читает scene_state;
    - удерживает continuity;
    - стабилизирует trajectory;
    - уменьшает overthinking;
    - уменьшает reflection loops;
    - уменьшает dialog dependence.
    """

    semantic = semantic or {}

    # =================================================
    # 🔥 STATE
    # =================================================

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

    scene_state = state.get(
        "scene_state",
        {}
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
    # 🔥 SCENE
    # =================================================

    scene_goal = scene_state.get(
        "goal"
    )

    scene_trajectory = scene_state.get(
        "trajectory"
    )

    scene_continuity = scene_state.get(
        "continuity",
        True
    )

    scene_direction = scene_state.get(
        "confirmed_direction"
    )

    visual_mode = scene_state.get(
        "visual_mode",
        False
    )

    execution_mode = scene_state.get(
        "execution_mode",
        False
    )

    # =================================================
    # 🔥 LAST USER
    # =================================================

    last_user = None

    for msg in reversed(dialog[-8:]):

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

    for msg in reversed(dialog[-6:]):

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
    # 🔥 EXECUTION
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
    # 🔥 CONTINUATION
    # =================================================

    continuation = semantic.get(
        "continuation",
        False
    )

    continuation_target = semantic.get(
        "continuation_target"
    )

    # =================================================
    # 🔥 STABILIZED FLAGS
    # =================================================

    user_waiting_action = (
        execution_pressure >= 0.72
    )

    dialog_overextended = (

        dialog_depth >= 12

        and conversation_value <= 0.45
    )

    high_confidence_execution = (

        capability_confidence >= 0.82

        and should_execute
    )

    # =================================================
    # 🔥 TRAJECTORY
    # =================================================

    trajectory_active = False

    if (
        active_flow
        or scene_trajectory
    ):

        trajectory_active = True

    trajectory_locked = False

    if (
        continuation
        or scene_continuity
    ):

        trajectory_locked = True

    # =================================================
    # 🔥 UNRESOLVED INTENT
    # =================================================

    unresolved_intent = True

    if (

        should_execute

        and ambiguity_level <= 0.25

        and execution_pressure >= 0.85
    ):

        unresolved_intent = False

    # =================================================
    # 🔥 REFLECTION CONTROL
    # =================================================

    needs_reflection = True

    # =================================================
    # 🔥 DEEPHUB FIX
    # =================================================
    # меньше повторного self-analysis
    # меньше loops
    # меньше перегрева cognition

    if (

        should_execute

        and execution_pressure >= 0.82

        and ambiguity_level <= 0.3
    ):

        needs_reflection = False

    if scene_trajectory:

        needs_reflection = False

    # =================================================
    # 🔥 RESPONSE COMPLETENESS
    # =================================================

    response_may_be_incomplete = False

    if (

        ambiguity_level >= 0.45

        or continuation
    ):

        response_may_be_incomplete = True

    # =================================================
    # 🔥 CAPABILITY AWARENESS
    # =================================================

    capability_awareness = {

        "understands_capabilities": True,

        "capabilities_are_personal": True,

        "capabilities_are_supportive": True,

        "capabilities_follow_scene": True,

        "capabilities_follow_trajectory":
            True,

        "visual_support_available": True,

        "execution_available": True,

        "guidance_available": True,

        "analysis_available": True,

        "continuation_priority": True,

        # =================================================
        # 🔥 DEEPHUB
        # =================================================

        "scene_is_primary": True,

        "dialog_is_secondary": True,

        "avoid_duplicate_analysis": True
    }

    # =================================================
    # 🔥 INTERNAL MONITOR
    # =================================================

    internal_monitor = {

        "enabled": True,

        "tracks_scene": True,

        "tracks_dialog_state": True,

        "tracks_user_direction": True,

        "tracks_trajectory": True,

        "tracks_continuity": True,

        "tracks_unresolved_expectation":
            True,

        "tracks_response_usefulness":
            True,

        "tracks_psychological_continuity":
            True,

        "tracks_capability_relevance":
            True,

        "maintains_conversation_presence":
            True,

        # =================================================
        # 🔥 DEEPHUB
        # =================================================

        "avoid_overthinking": True,

        "avoid_recursive_analysis": True,

        "avoid_rebuilding_context": True
    }

    # =================================================
    # 🔥 REFLECTION
    # =================================================

    reflection = {

        "enabled": needs_reflection,

        "response_should_be_evaluated":
            needs_reflection,

        "helpfulness_unknown":
            needs_reflection,

        "trajectory_must_continue":
            trajectory_active,

        "dialogue_not_finished":
            trajectory_active,

        "avoid_premature_completion":
            True,

        "maintain_psychological_presence":
            True,

        # =================================================
        # 🔥 DEEPHUB
        # =================================================

        "avoid_overreflection": True,

        "avoid_analysis_loops": True
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
        # 🔥 SCENE
        # =================================================

        "scene_state": scene_state,

        "scene_goal": scene_goal,

        "scene_trajectory":
            scene_trajectory,

        "scene_direction":
            scene_direction,

        "scene_continuity":
            scene_continuity,

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
            trajectory_locked,

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
        # 🔥 QUALITY
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
        # 🔥 MEMORY
        # =================================================

        "image_context": image_context,

        "last_math": last_math,

        "last_code": last_code,

        "last_user": last_user,

        "last_assistant":
            last_assistant,

        # =================================================
        # 🔥 FLAGS
        # =================================================

        "user_waiting_action":
            user_waiting_action,

        "high_confidence_execution":
            high_confidence_execution,

        "visual_mode":
            visual_mode,

        "execution_mode":
            execution_mode,

        # =================================================
        # 🔥 INTERNAL
        # =================================================

        "internal_monitor":
            internal_monitor,

        "reflection":
            reflection,

        "capability_awareness":
            capability_awareness
    }

    return reasoning
