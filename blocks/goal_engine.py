# =====================================================
# 🧠 APRIL GOAL & TRAJECTORY STABILIZATION CORE
# =====================================================

"""
APRIL GOAL STABILIZATION CORE

APRIL_FILE_ID:
APRIL_GOAL_TRAJECTORY_STABILIZATION_CORE

ROLE:
GOAL_CONTINUITY_COORDINATOR

INPUT:
USER_TEXT
STATE
SEMANTIC_CONTEXT

OUTPUT:
GOAL_STATE
TRAJECTORY_STATE
CONTINUATION_STATE
EXECUTION_DECISION

THIS FILE IS:
- goal stabilization layer
- trajectory continuity helper
- execution pacing system
- semantic continuation coordinator
- dialog flow protector

THIS FILE IS NOT:
- executor
- orchestration authority
- renderer engine
- response formatter
- cognition narrator
- memory authority

GOLDEN APRIL PRINCIPLES:
- continuation before escalation
- execution only on confidence
- preserve trajectory
- lightweight continuity
- no forced execution
- calm semantic routing
"""

# =====================================================
# 🔥 FILE ID
# =====================================================

APRIL_FILE_ID = (
    "APRIL_GOAL_TRAJECTORY_STABILIZATION_CORE"
)

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

GOAL_TASK_CHANNEL = {

    "channel":
        "goal_machine_task_channel",

    "isolated":
        True
}

GOAL_RESPONSE_CHANNEL = {

    "channel":
        "goal_machine_response_channel",

    "isolated":
        True
}

# =====================================================
# 🔥 MACHINE LOGGING
# =====================================================

def build_goal_input_log():

    return {

        "file_id":
            APRIL_FILE_ID,

        "event":
            "goal_input",

        "channel":
            GOAL_TASK_CHANNEL,

        "machine_only":
            True
    }


def build_goal_output_log(
    goal,
    mode
):

    return {

        "file_id":
            APRIL_FILE_ID,

        "event":
            "goal_output",

        "goal":
            goal,

        "response_mode":
            mode,

        "channel":
            GOAL_RESPONSE_CHANNEL,

        "machine_only":
            True
    }

# =====================================================
# 🔥 MAIN GOAL DETECTION
# =====================================================

def detect_goal(

    text: str,
    state: dict,
    semantic: dict
):

    """
    Main trajectory stabilization layer.

    Responsible ONLY for:
    - goal continuity
    - semantic pacing
    - execution escalation control
    - trajectory preservation
    """

    build_goal_input_log()

    semantic = semantic or {}

    t = text.lower().strip()

    active = state.get(
        "active_flow"
    )

    scene_state = state.get("scene_state", {})

    active_scene = state.get(
        "active_scene",
        {}
    )

    visual_continuity = state.get(
        "visual_continuity_summary",
        {}
    )

    dialog = state.get(
        "dialog",
        []
    )

    last_user = None

    # =================================================
    # 🔥 LAST USER MESSAGE
    # =====================================================

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
    # =====================================================

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
    # =====================================================

    semantic["trajectory_active"] = True

    semantic["goal_persistent"] = True

    semantic["goal_completed"] = False

    semantic["conversation_alive"] = True

    semantic["unresolved_intent"] = True

    semantic["preserve_flow"] = True

    semantic["preserve_trajectory"] = True

    semantic["response_requires_reflection"] = True

    semantic["goal_machine_channel"] = (
        GOAL_RESPONSE_CHANNEL
    )

    semantic["goal_stabilization_active"] = True

    # =================================================
    # 🔥 EXPLORATION PROTECTION
    # =====================================================

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
    # =====================================================

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
    # =====================================================

    if active:

        flow_type = active.get(
            "type"
        )

        semantic["continuation"] = True

        semantic["trajectory_active"] = True

        semantic["preserve_flow"] = True

        # =================================================
        # 🖼 IMAGE TRAJECTORY
        # =====================================================

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

                build_goal_output_log(
                    "continue_image",
                    semantic.get(
                        "response_mode",
                        "guide"
                    )
                )

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

                # 🔥 explicit edit escalates
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

                build_goal_output_log(
                    "continue_image",
                    semantic.get(
                        "response_mode",
                        "guide"
                    )
                )

                return semantic

        # =================================================
        # 📈 MATH TRAJECTORY
        # =====================================================

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

                build_goal_output_log(
                    "continue_math",
                    semantic.get(
                        "response_mode",
                        "guide"
                    )
                )

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

                build_goal_output_log(
                    "continue_math",
                    semantic.get(
                        "response_mode",
                        "guide"
                    )
                )

                return semantic

    # =================================================
    # 🔥 DIALOG FATIGUE
    # =====================================================

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
    # =====================================================

    if dialog_state == "exploration":

        semantic["goal_completed"] = False

        semantic["conversation_alive"] = True

        semantic["unresolved_intent"] = True

    # =================================================
    # 🔥 FINAL SAFETY
    # =====================================================

    if semantic.get(
        "capability_should_wait"
    ):

        semantic["should_execute"] = False

        semantic["response_mode"] = "guide"

    semantic["scene_state_goal"] = scene_state.get("goal")

    semantic["active_scene_goal"] = semantic["scene_state_goal"]

    semantic["visual_goal"] = (
        visual_continuity.get("active_goal")
    )

    semantic["goal_continuity_active"] = True

    semantic["goal_persistence_mode"] = (
        "scene_first"
    )

    # =================================================
    # 🔥 OUTPUT LOG
    # =====================================================

    build_goal_output_log(

        semantic.get(
            "goal",
            "unknown"
        ),

        semantic.get(
            "response_mode",
            "guide"
        )
    )

    # =================================================
    # 🔥 DEFAULT
    # =====================================================

    return semantic
