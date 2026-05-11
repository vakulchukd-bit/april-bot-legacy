# =====================================================
# 🧠 APRIL AUTHORITY SYSTEM
# =====================================================

"""
April Supreme Cognitive Authority

FINAL INTELLIGENCE LAYER

Этот модуль:
- является финальной cognitive authority;
- удерживает user intention;
- удерживает trajectory;
- валидирует completion;
- контролирует capability routing;
- перепроверяет executor;
- имеет override authority;
- анализирует usefulness;
- анализирует continuity;
- анализирует visual obligations;
- анализирует screenshot flow;
- анализирует dialog psychology;
- управляет capability orchestration.

Executor:
НЕ является финальной инстанцией.

Rooms:
НЕ являются финальной инстанцией.

Semantic:
НЕ является финальной инстанцией.

Final authority принадлежит April.
"""

# =====================================================
# 🔥 CAPABILITY REGISTRY
# =====================================================

APRIL_CAPABILITIES = {

    # =================================================
    # CORE
    # =================================================

    "text": True,

    "reasoning": True,

    "guidance": True,

    "conversation": True,

    "continuation": True,

    "memory": True,

    "psychology": True,

    # =================================================
    # VISUAL
    # =================================================

    "image_generation": True,

    "image_edit": True,

    "image_analysis": True,

    "visual_guidance": True,

    "diagram_analysis": True,

    "diagram_generation": True,

    "graph_generation": True,

    "screenshot_analysis": True,

    "screenshot_guidance": True,

    # =================================================
    # WEB
    # =================================================

    "web": True,

    "web_search": True,

    "external_knowledge": True,

    "references": True,

    # =================================================
    # SCIENCE
    # =================================================

    "science": True,

    "math": True,

    "geometry": True,

    "graphs": True,

    "engineering": True,

    "code": True,

    # =================================================
    # EXECUTION
    # =================================================

    "execution": True,

    "capability_override": True,

    "room_override": True,

    "executor_override": True,

    "direct_capability_access": True
}

# =====================================================
# 🔥 TRUST STATE
# =====================================================

DEFAULT_TRUST_LEVELS = {

    "text": 1.0,

    "image_generation": 1.0,

    "image_edit": 1.0,

    "image_analysis": 1.0,

    "visual_guidance": 1.0,

    "science": 1.0,

    "graphs": 1.0,

    "web": 1.0,

    "code": 1.0,

    "executor": 1.0
}

# =====================================================
# 🔥 AUTHORITY STATE
# =====================================================

def build_authority_state():

    return {

        # =================================================
        # AUTHORITY
        # =================================================

        "authority_active": True,

        "override_allowed": True,

        "direct_capability_access": True,

        "executor_override_allowed": True,

        "room_override_allowed": True,

        "final_validation": True,

        # =================================================
        # COGNITION
        # =================================================

        "completion_validation": True,

        "trajectory_tracking": True,

        "dialog_psychology_tracking": True,

        "visual_completion_tracking": True,

        "capability_mismatch_detection": True,

        "continuation_tracking": True,

        "usefulness_analysis": True,

        "response_repair": True,

        # =================================================
        # TRUST
        # =================================================

        "trust_levels":
            DEFAULT_TRUST_LEVELS.copy(),

        # =================================================
        # MEMORY
        # =================================================

        "last_override": None,

        "last_success": None,

        "last_failure": None,

        "last_capability": None,

        "last_user_goal": None,

        "last_visual_request": None,

        "last_execution_path": None
    }

# =====================================================
# 🔥 INTENTION CONFIDENCE
# =====================================================

def evaluate_intention_confidence(

    semantic,
    cognition,
    response_decision

):

    semantic = semantic or {}
    cognition = cognition or {}
    response_decision = response_decision or {}

    confidence = 0.0

    # =================================================
    # RESULT DESIRE
    # =================================================

    confidence += cognition.get(
        "wants_result",
        0.0
    ) * 0.25

    confidence += cognition.get(
        "wants_visual",
        0.0
    ) * 0.25

    confidence += cognition.get(
        "wants_help",
        0.0
    ) * 0.15

    # =================================================
    # USER LEADS
    # =================================================

    if cognition.get(
        "user_leads_direction"
    ):

        confidence += 0.15

    # =================================================
    # EXECUTION
    # =================================================

    if semantic.get(
        "should_execute"
    ):

        confidence += 0.2

    # =================================================
    # AMBIGUITY
    # =================================================

    ambiguity = semantic.get(
        "ambiguity_level",
        0.0
    )

    confidence -= ambiguity * 0.45

    return max(
        0.0,
        min(confidence, 1.0)
    )

# =====================================================
# 🔥 VISUAL OBLIGATION
# =====================================================

def is_visual_obligatory(

    semantic,
    cognition

):

    semantic = semantic or {}
    cognition = cognition or {}

    if cognition.get(
        "wants_visual",
        0.0
    ) >= 0.72:

        ambiguity = semantic.get(
            "ambiguity_level",
            0.0
        )

        if ambiguity <= 0.45:

            return True

    return False

# =====================================================
# 🔥 COMPLETION ANALYSIS
# =====================================================

def analyze_completion(

    result,
    semantic,
    cognition

):

    semantic = semantic or {}
    cognition = cognition or {}

    if not result:

        return {

            "completed": False,

            "reason":
                "empty_result"
        }

    result_type = result.get(
        "type",
        "text"
    )

    output = str(
        result.get(
            "data",
            ""
        )
    ).strip()

    lowered = output.lower()

    # =================================================
    # EMPTY
    # =================================================

    if len(output) <= 5:

        return {

            "completed": False,

            "reason":
                "empty_output"
        }

    # =================================================
    # REFUSAL
    # =================================================

    refusal_patterns = [

        "я не могу",

        "я не умею",

        "не поддерживается",

        "представь себе",

        "не имею возможности"
    ]

    for pattern in refusal_patterns:

        if pattern in lowered:

            return {

                "completed": False,

                "reason":
                    "refusal"
            }

    # =================================================
    # VISUAL COMPLETION
    # =================================================

    if is_visual_obligatory(

        semantic,
        cognition

    ):

        if result_type not in [

            "image",
            "image_task",
            "graph",
            "diagram"
        ]:

            return {

                "completed": False,

                "reason":
                    "visual_missing"
            }

    # =================================================
    # EXECUTION COMPLETION
    # =================================================

    if semantic.get(
        "should_execute"
    ):

        if result_type == "text":

            if cognition.get(
                "wants_result",
                0.0
            ) >= 0.7:

                if len(output) < 20:

                    return {

                        "completed": False,

                        "reason":
                            "weak_execution"
                    }

    return {

        "completed": True,

        "reason":
            "success"
    }

# =====================================================
# 🔥 CAPABILITY MISMATCH
# =====================================================

def detect_capability_mismatch(

    result,
    semantic,
    cognition

):

    semantic = semantic or {}
    cognition = cognition or {}

    if not result:

        return True

    result_type = result.get(
        "type",
        "text"
    )

    # =================================================
    # VISUAL MISMATCH
    # =================================================

    if cognition.get(
        "wants_visual",
        0.0
    ) >= 0.7:

        if result_type == "text":

            return True

    # =================================================
    # EXECUTION MISMATCH
    # =================================================

    if semantic.get(
        "should_execute"
    ):

        if result_type == "text":

            if cognition.get(
                "wants_result",
                0.0
            ) >= 0.75:

                return True

    return False

# =====================================================
# 🔥 TRAJECTORY VALIDATION
# =====================================================

def validate_trajectory(

    semantic,
    cognition,
    state

):

    semantic = semantic or {}
    cognition = cognition or {}
    state = state or {}

    active_flow = state.get(
        "active_flow"
    )

    if not active_flow:

        return True

    flow_type = active_flow.get(
        "type"
    )

    continuation_target = semantic.get(
        "continuation_target"
    )

    if continuation_target:

        if continuation_target != flow_type:

            return False

    return True

# =====================================================
# 🔥 USEFULNESS ANALYSIS
# =====================================================

def evaluate_usefulness(

    result,
    semantic,
    cognition

):

    if not result:

        return 0.0

    output = str(
        result.get(
            "data",
            ""
        )
    )

    usefulness = 1.0

    if len(output) < 15:

        usefulness -= 0.45

    if "не могу" in output.lower():

        usefulness -= 0.6

    if cognition.get(
        "wants_visual",
        0.0
    ) >= 0.7:

        if result.get(
            "type"
        ) == "text":

            usefulness -= 0.5

    return max(
        0.0,
        min(usefulness, 1.0)
    )

# =====================================================
# 🔥 FINAL VALIDATION
# =====================================================

def validate_final_response(

    result,
    semantic,
    cognition,
    state=None

):

    completion = analyze_completion(

        result,
        semantic,
        cognition
    )

    if not completion.get(
        "completed"
    ):

        return False

    mismatch = detect_capability_mismatch(

        result,
        semantic,
        cognition
    )

    if mismatch:

        return False

    trajectory_valid = validate_trajectory(

        semantic,
        cognition,
        state or {}
    )

    if not trajectory_valid:

        return False

    usefulness = evaluate_usefulness(

        result,
        semantic,
        cognition
    )

    if usefulness < 0.45:

        return False

    return True

# =====================================================
# 🔥 OVERRIDE DECISION
# =====================================================

def should_override(

    result,
    semantic,
    cognition,
    response_decision,
    state=None

):

    semantic = semantic or {}
    cognition = cognition or {}
    response_decision = (
        response_decision or {}
    )

    # =================================================
    # VALIDATION
    # =================================================

    valid = validate_final_response(

        result,
        semantic,
        cognition,
        state
    )

    if not valid:

        return True

    # =================================================
    # INTENTION CONFIDENCE
    # =================================================

    confidence = evaluate_intention_confidence(

        semantic,
        cognition,
        response_decision
    )

    if confidence >= 0.75:

        mismatch = (
            detect_capability_mismatch(

                result,
                semantic,
                cognition
            )
        )

        if mismatch:

            return True

    # =================================================
    # VISUAL OBLIGATION
    # =================================================

    if is_visual_obligatory(

        semantic,
        cognition

    ):

        if result.get("type") == "text":

            return True

    return False

# =====================================================
# 🔥 EXECUTIVE AUTHORITY
# =====================================================

def build_authority_decision(

    result,
    semantic,
    cognition,
    response_decision,
    state=None

):

    override = should_override(

        result,
        semantic,
        cognition,
        response_decision,
        state
    )

    completion = analyze_completion(

        result,
        semantic,
        cognition
    )

    usefulness = evaluate_usefulness(

        result,
        semantic,
        cognition
    )

    return {

        # =================================================
        # AUTHORITY
        # =================================================

        "override": override,

        "allow_response":
            not override,

        # =================================================
        # COMPLETION
        # =================================================

        "completed":
            completion.get(
                "completed",
                False
            ),

        "completion_reason":
            completion.get(
                "reason"
            ),

        # =================================================
        # ANALYSIS
        # =================================================

        "usefulness":
            usefulness,

        "trajectory_valid":
            validate_trajectory(

                semantic,
                cognition,
                state or {}
            ),

        "visual_obligation":
            is_visual_obligatory(

                semantic,
                cognition
            ),

        "capability_mismatch":
            detect_capability_mismatch(

                result,
                semantic,
                cognition
            ),

        # =================================================
        # EXECUTIVE
        # =================================================

        "should_retry_execution":
            override,

        "should_change_room":
            override,

        "should_force_capability":
            override,

        "authority_confident": True
    }
