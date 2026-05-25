# =====================================================
# 🧠 APRIL SUPREME AUTHORITY SYSTEM
# =====================================================

"""
APRIL FINAL COGNITIVE AUTHORITY

UNIFIED EXECUTIVE INTELLIGENCE LAYER

Authority layer теперь:
- stabilizer;
- validator;
- trajectory protector;
- calm orchestration guard;
- capability verifier.

Authority больше НЕ:
- aggressive override layer;
- recursive retry source;
- forced generation trigger;
- chaos escalation system.

APRIL AUTHORITY PRINCIPLES:

1. continuation before override
2. renderer before generation
3. usefulness before capability
4. calm execution
5. anti-recursive behavior
6. no hidden escalation
7. no forced personality leakage
"""

# =====================================================
# 🔥 CAPABILITY REGISTRY
# =====================================================

APRIL_CAPABILITIES = {

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
    # =====================================================

    "renderer_space": True,

    "scene_rendering": True,

    "graph_generation": True,

    "graph_analysis": True,

    "diagram_generation": True,

    "diagram_analysis": True,

    "formula_rendering": True,

    "table_rendering": True,

    "primitive_scene_objects": True,

    "visual_guidance": True,

    "visual_continuity": True,

    "screenshot_analysis": True,

    "image_analysis": True,

    # =================================================
    # HEAVY VISUAL
    # =====================================================

    "image_generation": True,

    "image_edit": True,

    # =================================================
    # KNOWLEDGE
    # =====================================================

    "web_search": True,

    "external_knowledge": True,

    "references": True,

    "live_information": True,

    # =================================================
    # SCIENCE
    # =====================================================

    "science": True,

    "math": True,

    "geometry": True,

    "engineering": True,

    "code": True,

    # =================================================
    # AUTHORITY
    # =====================================================

    "override": True,

    "executor_override": True,

    "room_override": True,

    "capability_override": True,

    "direct_capability_access": True,

    "completion_validation": True,

    "result_validation": True,

    "usefulness_validation": True,

    # =================================================
    # SAFETY
    # =====================================================

    "anti_loop_protection": True,

    "anti_escalation": True,

    "anti_personality_leak": True,

    "anti_recursive_generation": True
}

# =====================================================
# 🔥 TRUST LEVELS
# =====================================================

DEFAULT_TRUST_LEVELS = {

    "executor": 1.0,

    "text": 1.0,

    "science": 1.0,

    "renderer_space": 1.0,

    "image_analysis": 1.0,

    "web": 1.0,

    "code": 1.0,

    # =================================================
    # 🔥 HEAVY VISUAL
    # =====================================================

    "image_generation": 0.82,

    "image_edit": 0.82
}

# =====================================================
# 🔥 HELPERS
# =====================================================

def clamp(
    value,
    minimum=0.0,
    maximum=1.0
):

    if value < minimum:
        return minimum

    if value > maximum:
        return maximum

    return value


def safe_output(
    result
):

    if not result:
        return ""

    return str(
        result.get(
            "data",
            ""
        )
    ).strip()


def is_renderer_result(
    result
):

    if not result:
        return False

    result_type = result.get(
        "type",
        "text"
    )

    if result_type in [

        "graph",
        "diagram",
        "formula",
        "table",
        "scene"
    ]:

        return True

    output = safe_output(
        result
    ).lower()

    renderer_patterns = [

        "[[graph",
        "[[diagram",
        "[[formula",
        "<svg",
        "<canvas"
    ]

    return any(
        x in output
        for x in renderer_patterns
    )


def contains_system_leak(
    output
):

    if not output:
        return False

    lowered = output.lower()

    leak_patterns = [

        "personality_active",
        "response_decision",
        "execution_pressure",
        "cognition",
        "semantic",
        "internal_noise",
        "assistant_restraint",
        "trajectory_tracking",
        "continuity tracking",
        "system prompt",
        "ты calm mobile-first ai assistant"
    ]

    hits = 0

    for pattern in leak_patterns:

        if pattern in lowered:
            hits += 1

    return hits >= 2


# =====================================================
# 🔥 AUTHORITY STATE
# =====================================================

def build_authority_state():

    return {

        # =================================================
        # AUTHORITY
        # =====================================================

        "authority_active": True,

        "override_allowed": True,

        "executor_override_allowed": True,

        "room_override_allowed": True,

        "direct_capability_access": True,

        "final_validation": True,

        # =================================================
        # COGNITION
        # =====================================================

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
        # =====================================================

        "can_force_execution": True,

        "can_force_visual": False,

        "can_force_web": True,

        "can_force_graph": True,

        "can_force_image_generation": False,

        "can_force_image_edit": False,

        "can_force_screenshot_analysis": True,

        "can_force_reasoning": True,

        # =================================================
        # SAFETY
        # =====================================================

        "anti_recursive_retry": True,

        "anti_escalation": True,

        "anti_hidden_generation": True,

        "anti_system_leak": True,

        # =================================================
        # MEMORY
        # =====================================================

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

    # =================================================
    # 🔥 RENDERER-FIRST
    # =====================================================

    if semantic.get(
        "render_intent"
    ):

        return True

    if semantic.get(
        "prefer_renderer"
    ):

        return True

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

    output = safe_output(
        result
    )

    lowered = output.lower()

    # =================================================
    # EMPTY
    # =====================================================

    if len(output) <= 5:

        return {

            "completed": False,

            "reason":
                "empty_output"
        }

    # =================================================
    # SYSTEM LEAK
    # =====================================================

    if contains_system_leak(
        output
    ):

        return {

            "completed": False,

            "reason":
                "system_leak"
        }

    # =================================================
    # REFUSAL
    # =====================================================

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
    # =====================================================

    if is_visual_obligatory(

        semantic,
        cognition

    ):

        renderer_allowed = is_renderer_result(
            result
        )

        visual_allowed = result_type in [

            "image",
            "image_task",
            "graph",
            "diagram",
            "scene"
        ]

        if not renderer_allowed and not visual_allowed:

            return {

                "completed": False,

                "reason":
                    "visual_missing"
            }

    # =================================================
    # EXECUTION
    # =====================================================

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
    # 🔥 RENDERER-FIRST
    # =====================================================

    if semantic.get(
        "prefer_renderer"
    ):

        return "renderer_space"

    if semantic.get(
        "render_intent"
    ):

        return "renderer_space"

    # =================================================
    # VISUAL
    # =====================================================

    if cognition.get(
        "wants_visual",
        0.0
    ) >= 0.72:

        if semantic.get(
            "explicit_image_generation_only"
        ):

            if state.get("image"):

                return "image_edit"

            return "image_generation"

        return "renderer_space"

    # =================================================
    # WEB
    # =====================================================

    if semantic.get(
        "internet_context_needed"
    ):

        return "web"

    # =================================================
    # GRAPH
    # =====================================================

    continuation_target = semantic.get(
        "continuation_target"
    )

    if continuation_target == "math":

        return "science"

    # =================================================
    # EXECUTION
    # =====================================================

    if semantic.get(
        "should_execute"
    ):

        return "execution"

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

    output = safe_output(
        result
    )

    lowered = output.lower()

    if len(output) < 15:

        usefulness -= 0.4

    if "не могу" in lowered:

        usefulness -= 0.5

    if contains_system_leak(
        output
    ):

        usefulness -= 0.7

    # =================================================
    # 🔥 RENDERER-FIRST
    # =====================================================

    if semantic.get(
        "prefer_renderer"
    ):

        if result.get(
            "type"
        ) == "text":

            usefulness -= 0.45

    # =================================================
    # 🔥 HEAVY IMAGE PENALTY
    # =====================================================

    if (

        cognition.get(
            "wants_visual",
            0.0
        ) >= 0.7

        and not semantic.get(
            "explicit_image_generation_only"
        )
    ):

        if result.get(
            "type"
        ) == "image":

            usefulness -= 0.25

    return clamp(
        usefulness
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

    semantic = semantic or {}
    cognition = cognition or {}

    valid = validate_final_response(

        result,
        semantic,
        cognition,
        state
    )

    if not valid:

        return True

    # =================================================
    # 🔥 RENDERER-FIRST
    # =====================================================

    if semantic.get(
        "prefer_renderer"
    ):

        if result.get(
            "type"
        ) == "image":

            return True

    # =================================================
    # 🔥 VISUAL OBLIGATION
    # =====================================================

    if is_visual_obligatory(

        semantic,
        cognition

    ):

        result_type = result.get(
            "type"
        )

        if result_type == "text":

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
        # =====================================================

        "override": override,

        "allow_response":
            not override,

        # =================================================
        # COMPLETION
        # =====================================================

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
        # =====================================================

        "usefulness":
            usefulness,

        "visual_obligation":
            is_visual_obligatory(

                semantic,
                cognition
            ),

        # =================================================
        # EXECUTION
        # =====================================================

        "best_capability":
            capability_path,

        "should_force_execution":
            override,

        "should_retry":
            override,

        "should_change_room":
            override,

        # =================================================
        # 🔥 RENDERER-FIRST
        # =====================================================

        "should_force_renderer":
            capability_path == "renderer_space",

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
        # SAFETY
        # =====================================================

        "avoid_recursive_retry": True,

        "avoid_hidden_generation": True,

        "avoid_personality_leak": True,

        "avoid_system_prompt_exposure": True,

        # =================================================
        # HUMAN FLOW
        # =====================================================

        "maintain_humanity": True,

        "maintain_continuity": True,

        "maintain_psychology": True,

        "maintain_visual_quality": True,

        "maintain_user_goal": True,

        "maintain_dialog_flow": True,

        # =================================================
        # FINAL
        # =====================================================

        "authority_confident": True
    }
