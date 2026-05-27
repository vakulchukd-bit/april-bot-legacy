def build_reasoning_state(
    text: str,
    state: dict,
    semantic: dict = None
):

    """
    APRIL LIGHTWEIGHT REASONING STATE

    Новый reasoning:

    - меньше token pressure
    - меньше recursive reflection
    - меньше semantic duplication
    - меньше dialog rebuild

    Главная задача:
    удерживать trajectory,
    continuity,
    scene direction
    и execution readiness.

    Reasoning больше НЕ:
    - giant semantic snapshot
    - second cognition layer
    - self-analysis engine
    - over-monitoring system
    """

    semantic = semantic or {}

    # =================================================
    # 🔥 STATE
    # =================================================

    dialog = state.get(
        "dialog",
        []
    )

    active_flow = state.get(
        "active_flow"
    )

    scene_state = state.get(
        "scene_state",
        {}
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

    scene_direction = scene_state.get(
        "confirmed_direction"
    )

    scene_continuity = scene_state.get(
        "continuity",
        True
    )

    # =================================================
    # 🔥 LIGHTWEIGHT SEMANTIC
    # =================================================

    continuation = semantic.get(
        "continuation",
        False
    )

    continuation_target = semantic.get(
        "continuation_target"
    )

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

    ambiguity_level = semantic.get(
        "ambiguity_level",
        0.0
    )

    capability_confidence = semantic.get(
        "capability_confidence",
        0.5
    )

    conversation_value = semantic.get(
        "conversation_value",
        1.0
    )

    # =================================================
    # 🔥 DIALOG DEPTH
    # =================================================

    dialog_depth = len(dialog)

    # =================================================
    # 🔥 LAST USER
    # =================================================

    last_user = None

    for msg in reversed(dialog[-5:]):

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

    for msg in reversed(dialog[-4:]):

        if msg.get("role") == "assistant":

            last_assistant = (
                msg.get("content")
                or ""
            )

            break

    # =================================================
    # 🔥 TRAJECTORY
    # =================================================

    trajectory_active = bool(

        active_flow
        or scene_trajectory
    )

    trajectory_locked = bool(

        continuation
        or scene_continuity
    )

    # =================================================
    # 🔥 EXECUTION READINESS
    # =================================================

    high_confidence_execution = (

        should_execute

        and execution_pressure >= 0.82

        and ambiguity_level <= 0.25

        and capability_confidence >= 0.8
    )

    # =================================================
    # 🔥 REFLECTION CONTROL
    # =================================================

    needs_reflection = True

    if high_confidence_execution:

        needs_reflection = False

    if trajectory_active:

        needs_reflection = False

    # =================================================
    # 🔥 DIALOG HEALTH
    # =================================================

    dialog_overextended = (

        dialog_depth >= 12

        and conversation_value <= 0.45
    )

    unresolved_intent = not (

        should_execute

        and ambiguity_level <= 0.25

        and execution_pressure >= 0.82
    )

    # =================================================
    # 🔥 MACHINE STATE
    # =================================================

    reasoning = {

        # =================================================
        # 🔥 CORE
        # =================================================

        "input": text,

        "conversation_alive": True,

        # =================================================
        # 🔥 TRAJECTORY
        # =================================================

        "trajectory_active":
            trajectory_active,

        "trajectory_locked":
            trajectory_locked,

        "continuation":
            continuation,

        "continuation_target":
            continuation_target,

        "preserve_trajectory": True,

        "preserve_continuity": True,

        # =================================================
        # 🔥 SCENE
        # =================================================

        "scene_goal":
            scene_goal,

        "scene_trajectory":
            scene_trajectory,

        "scene_direction":
            scene_direction,

        "scene_continuity":
            scene_continuity,

        # =================================================
        # 🔥 EXECUTION
        # =================================================

        "should_execute":
            should_execute,

        "execution_pressure":
            execution_pressure,

        "execution_ready":
            high_confidence_execution,

        "response_mode":
            response_mode,

        "goal_stage":
            goal_stage,

        # =================================================
        # 🔥 STABILIZATION
        # =================================================

        "needs_reflection":
            needs_reflection,

        "unresolved_intent":
            unresolved_intent,

        "dialog_overextended":
            dialog_overextended,

        "avoid_recursive_analysis":
            True,

        "avoid_context_rebuild":
            True,

        "avoid_overthinking":
            True,

        # =================================================
        # 🔥 MEMORY
        # =================================================

        "last_user":
            last_user,

        "last_assistant":
            last_assistant,

        # =================================================
        # 🔥 INTERNAL MACHINE MODES
        # =================================================

        "state_mode":
            "trajectory_reasoning",

        "continuity_mode":
            "active",

        "reasoning_style":
            "lightweight",

        "scene_priority":
            True,

        "dialog_priority":
            False,

        "reflection_mode":
            "minimal"
    }

    return reasoning
