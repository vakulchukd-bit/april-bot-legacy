# =====================================================
# 🧠 APRIL SUPREME AUTHORITY SYSTEM
# =====================================================

"""
APRIL FINAL COGNITIVE AUTHORITY

UNIFIED EXECUTIVE INTELLIGENCE LAYER

Этот модуль:
- удерживает intention пользователя;
- удерживает continuity;
- анализирует trajectory;
- валидирует completion;
- контролирует executor;
- контролирует rooms;
- контролирует usefulness;
- анализирует satisfaction;
- анализирует visual obligations;
- анализирует capability mismatch;
- управляет capability routing;
- выбирает лучший capability path;
- имеет override authority;
- может force execution;
- может force capability;
- может force visual;
- может force web;
- может force graph;
- может force image generation;
- может force screenshot analysis;
- удерживает human dialog flow;
- удерживает visual continuity;
- удерживает psychological continuity;
- удерживает completion responsibility.

Final authority:
принадлежит April.
"""

# =====================================================
# 🔥 CAPABILITY REGISTRY
# =====================================================

APRIL_CAPABILITIES = {

    # =================================================
    # CORE
    # =================================================

    "conversation": True,

    "continuation": True,

    "trajectory_tracking": True,

    "dialog_analysis": True,

    "psychology": True,

    "memory": True,

    "reasoning": True,

    "guidance": True,

    "execution": True,

    # =================================================
    # VISUAL
    # =================================================

    "image_generation": True,

    "image_edit": True,

    "image_analysis": True,

    "visual_guidance": True,

    "diagram_generation": True,

    "diagram_analysis": True,

    "graph_generation": True,

    "graph_analysis": True,

    "screenshot_analysis": True,

    "visual_hinting": True,

    "visual_continuity": True,

    # =================================================
    # KNOWLEDGE
    # =================================================

    "web_search": True,

    "external_knowledge": True,

    "references": True,

    "live_information": True,

    # =================================================
    # SCIENCE
    # =================================================

    "science": True,

    "math": True,

    "geometry": True,

    "engineering": True,

    "code": True,

    # =================================================
    # AUTHORITY
    # =================================================

    "override": True,

    "executor_override": True,

    "room_override": True,

    "capability_override": True,

    "direct_capability_access": True,

    "completion_validation": True,

    "result_validation": True,

    "usefulness_validation": True
}

# =====================================================
# 🔥 TRUST LEVELS
# =====================================================

DEFAULT_TRUST_LEVELS = {

    "executor": 1.0,

    "text": 1.0,

    "image_generation": 1.0,

    "image_edit": 1.0,

    "image_analysis": 1.0,

    "science": 1.0,

    "graphs": 1.0,

    "web": 1.0,

    "code": 1.0
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

        "executor_override_allowed": True,

        "room_override_allowed": True,

        "direct_capability_access": True,

        "final_validation": True,

        # =================================================
        # COGNITION
        # =================================================

        "trajectory_tracking": True,

        "completion_tracking": True,

        "visual_tracking": True,

        "dialog_tracking": True,

        "continuation_tracking": True,

        "psychology_tracking": True,

        "usefulness_tracking": True,

        "satisfaction_tracking": True,

        "humanity_tracking": True,

        # =================================================
        # EXECUTION
        # =================================================

        "can_force_execution": True,

        "can_force_visual": True,

        "can_force_web": True,

        "can_force_graph": True,

        "can_force_image_generation": True,

        "can_force_image_edit": True,

        "can_force_screenshot_analysis": True,

        "can_force_reasoning": True,

        # =================================================
        # MEMORY
        # =================================================

        "trust_levels":
            DEFAULT_TRUST_LEVELS.copy(),

        "last_override": None,

        "last_completion": None,

        "last_failure": None,

        "last_success": None,

        "last_capability": None,

        "last_user_goal": None,

        "last_visual_request": None,

        "last_dialog_mode": None
    }

# =====================================================
# 🔥 INTENTION ANALYSIS
# =====================================================

def analyze_user_intention(

    semantic,
    cognition,
    state

):

    semantic = semantic or {}
    cognition = cognition or {}
    state = state or {}

    return {

        "wants_result":
            cognition.get(
                "wants_result",
                0.0
            ),

        "wants_visual":
            cognition.get(
                "wants_visual",
                0.0
            ),

        "needs_execution":
            semantic.get(
                "should_execute",
                False
            ),

        "ambiguity":
            semantic.get(
                "ambiguity_level",
                0.0
            ),

        "goal_stage":
            semantic.get(
                "goal_stage",
                "exploration"
            ),

        "continuation_target":
            semantic.get(
                "continuation_target"
            ),

        "active_flow":
            state.get(
                "active_flow"
            )
    }

# =====================================================
# 🔥 VISUAL OBLIGATION
# =====================================================

def is_visual_obligatory(

    semantic,
    cognition

):

    semantic = semantic or {}
    cognition = cognition or {}
    continuation_target = semantic.get(
        "continuation_target"
)

if continuation_target == "math":

    return True

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

        "не умею",

        "не поддерживается",

        "представь себе",

        "нет возможности"
    ]

    for pattern in refusal_patterns:

        if pattern in lowered:

            return {

                "completed": False,

                "reason":
                    "refusal"
            }

    # =================================================
    # VISUAL
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
    # EXECUTION
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
# 🔥 CAPABILITY PATH
# =====================================================

def choose_best_capability_path(

    semantic,
    cognition,
    state

):

    semantic = semantic or {}
    cognition = cognition or {}
    state = state or {}

    # =================================================
    # VISUAL
    # =================================================

    if cognition.get(
        "wants_visual",
        0.0
    ) >= 0.72:

        if state.get("image"):

            return "image_edit"

        return "image_generation"

    # =================================================
    # WEB
    # =================================================

    if semantic.get(
        "needs_external_information"
    ):

        return "web"

    # =================================================
    # GRAPH
    # =================================================

    continuation_target = semantic.get(
        "continuation_target"
    )

    if continuation_target == "math":

        return "science"

    # =================================================
    # EXECUTION
    # =================================================

    if semantic.get(
        "should_execute"
    ):

        return "execution"

    # =================================================
    # DEFAULT
    # =================================================

    return "text"

# =====================================================
# 🔥 USEFULNESS
# =====================================================

def evaluate_usefulness(

    result,
    semantic,
    cognition

):

    if not result:

        return 0.0

    usefulness = 1.0

    output = str(
        result.get(
            "data",
            ""
        )
    )

    if len(output) < 15:

        usefulness -= 0.4

    if "не могу" in output.lower():

        usefulness -= 0.5

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

    usefulness = evaluate_usefulness(

        result,
        semantic,
        cognition
    )

    if usefulness < 0.45:

        return False

    return True

# =====================================================
# 🔥 OVERRIDE
# =====================================================

def should_override(

    result,
    semantic,
    cognition,
    state=None

):

    valid = validate_final_response(

        result,
        semantic,
        cognition,
        state
    )

    if not valid:

        return True

    if is_visual_obligatory(

        semantic,
        cognition

    ):

        if result.get(
            "type"
        ) == "text":

            return True

    return False

# =====================================================
# 🔥 EXECUTIVE DECISION
# =====================================================

def build_authority_decision(

    result,
    semantic,
    cognition,
    response_decision,
    state=None

):

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

    override = should_override(

        result,
        semantic,
        cognition,
        state
    )

    capability_path = (

        choose_best_capability_path(

            semantic,
            cognition,
            state or {}
        )
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

        "visual_obligation":
            is_visual_obligatory(

                semantic,
                cognition
            ),

        # =================================================
        # EXECUTION
        # =================================================

        "best_capability":
            capability_path,

        "should_force_execution":
            override,

        "should_retry":
            override,

        "should_change_room":
            override,

        "should_force_visual":
            capability_path in [

                "image_generation",
                "image_edit"
            ],

        "should_force_web":
            capability_path == "web",

        "should_force_science":
            capability_path == "science",

        # =================================================
        # HUMAN FLOW
        # =================================================

        "maintain_humanity": True,

        "maintain_continuity": True,

        "maintain_psychology": True,

        "maintain_visual_quality": True,

        "maintain_user_goal": True,

        "maintain_dialog_flow": True,

        # =================================================
        # FINAL
        # =================================================

        "authority_confident": True
    }
