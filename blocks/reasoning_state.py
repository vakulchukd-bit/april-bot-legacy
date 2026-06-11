# =====================================================
# 🧠 APRIL REASONING STATE
# =====================================================

"""
APRIL_FILE_ID: APRIL_REASONING_STATE

ROLE:
trajectory_reasoning_layer

PURPOSE:
- lightweight reasoning state
- continuity stabilization
- trajectory preservation
- execution readiness tracking
- scene continuity support
- reflection minimization

INPUT:
- user_text
- semantic_state
- scene_state
- dialog_state
- active_flow

OUTPUT:
- reasoning_state
- trajectory_state
- execution_readiness
- continuity_snapshot

DEPENDENCIES:
- semantic_core
- cognition
- scene_state
- active_flow
- executor
- excrouter

GOLDEN RULE:
Reasoning tracks direction.
Cognition decides.
"""

print("🧠 APRIL REASONING STATE LOADED")


# =====================================================
# 🔥 PATCH LOG
# =====================================================

REASONING_PATCH_LOG = []


def reasoning_log(msg):

    try:

        print(
            "APRIL REASONING:",
            msg
        )

        REASONING_PATCH_LOG.append(
            str(msg)
        )

    except Exception:
        pass


# =====================================================
# 🔥 ENTRY / EXIT
# =====================================================

def reasoning_enter(
    text
):

    reasoning_log(

        f"ENTER REASONING: "
        f"{str(text)[:80]}"
    )

    return {

        "reasoning_active": True,

        "continuity_safe": True,

        "trajectory_tracking": True
    }


def reasoning_exit(
    reasoning_state
):

    reasoning_log(
        "EXIT REASONING"
    )

    return {

        "reasoning_complete": True,

        "trajectory_active":

            reasoning_state.get(
                "trajectory_active",
                False
            ),

        "execution_ready":

            reasoning_state.get(
                "execution_ready",
                False
            )
    }


# =====================================================
# 🔥 FUTURE PLACEHOLDER
# =====================================================

def reasoning_future(
    *args,
    **kwargs
):

    return None


# =====================================================
# 🔥 MAIN REASONING STATE
# =====================================================

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

    reasoning_enter(
        text
    )

    semantic = semantic or {}

    state = state or {}

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

    active_scene = state.get(
        "active_scene",
        {}
    )

    visual_continuity = state.get(
        "visual_continuity_summary",
        {}
    )

    focus_snapshot = state.get(
        "focus_snapshot",
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
        # =====================================================

        "input": text,

        "conversation_alive": True,

        "reasoning_id":
            "APRIL_REASONING_STATE",

        # =================================================
        # 🔥 TRAJECTORY
        # =====================================================

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
        # =====================================================

        "scene_goal":
            scene_goal,

        "scene_trajectory":
            scene_trajectory,

        "scene_direction":
            scene_direction,

        "scene_continuity":
            scene_continuity,

        "active_scene":
            active_scene,

        "visual_continuity":
            visual_continuity,

        "focus_snapshot":
            focus_snapshot,

        "scene_awareness":
            True,

        # =================================================
        # 🔥 EXECUTION
        # =====================================================

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
        # =====================================================

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
        # =====================================================

        "last_user":
            last_user,

        "last_assistant":
            last_assistant,

        # =================================================
        # 🔥 INTERNAL MACHINE MODES
        # =====================================================

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
            "minimal",

        # =================================================
        # 🔥 APRIL WEB STABILIZATION
        # =====================================================

        "web_ready": True,

        "machine_context_safe": True,

        "renderer_safe": True,

        "provider_safe": True,

        "continuity_safe": True
    }

    reasoning_exit(
        reasoning
    )

    return reasoning


# =====================================================
# 🧠 DYNAMIC FOCUS REASONING UPGRADE
# =====================================================

def build_reasoning_focus_state(state):

    focus = state.get("dynamic_focus", {})

    return {
        "active_focus":
            focus.get("primary_focus"),

        "secondary_focus":
            focus.get("secondary_focus"),

        "focus_strength":
            focus.get("focus_strength", 0.0)
    }
