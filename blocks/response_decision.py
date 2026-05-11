# =====================================================
# 🧠 APRIL RESPONSE DECISION SYSTEM
# =====================================================

def build_response_decision(
    semantic: dict,
    cognition: dict,
    visual_reference: dict,
    state: dict
):

    semantic = semantic or {}
    cognition = cognition or {}
    visual_reference = visual_reference or {}
    state = state or {}

    active_flow = state.get(
        "active_flow"
    )

    reasoning = state.get(
        "reasoning",
        {}
    )

    # =====================================================
    # 🧠 BASE
    # =====================================================

    result = {

        # =================================================
        # FINAL MODES
        # =================================================

        "should_execute": False,
        "should_generate": False,
        "should_guide": False,
        "should_offer_reference": False,
        "should_continue_trajectory": False,

        # =================================================
        # DIALOG CONTROL
        # =================================================

        "should_reduce_talking": False,
        "should_wait_for_user": False,
        "should_follow_user": False,

        # =================================================
        # VISUAL CONTROL
        # =================================================

        "prefer_lightweight_visual": False,
        "avoid_heavy_generation": False,

        # =================================================
        # RESPONSE STRATEGY
        # =================================================

        "response_mode": "balanced",

        # =================================================
        # FINAL DECISION
        # =================================================

        "final_action": "talk",

        # =================================================
        # 🧠 PERSONALITY AUTHORITY
        # =================================================

        "personality_active": True,

        "personality_mode": "adaptive",

        "trajectory_protection": True,

        "human_continuity": True,

        "awareness_active": True,

        "understands_user_direction": False,

        "understands_user_goal": False,

        "protects_user_intent": True,

        "assistant_restraint": 0.0,

        "assistant_presence": 1.0,

        "avoid_trigger_behavior": True,

        "avoid_forced_generation": True,

        "avoid_unnecessary_talking": True,

        "avoid_room_conflicts": True,

        "maintain_psychology": True,

        "maintain_dialog_continuity": True,

        "maintain_goal_trajectory": True,

        "maintain_emotional_flow": True,

        "execution_allowed": False,

        "generation_allowed": False,

        "guidance_allowed": False,

        # =================================================
        # 🧠 POST ACTION REASONING
        # =================================================

        "dialogue_still_alive": True,

        "goal_completed": False,

        "needs_reflection": True,

        "needs_post_action_analysis": True,

        "should_recheck_user_state": True,

        "should_preserve_meaning": True,

        "capability_is_not_final": True,

        "trajectory_before_capability": True,

        "response_requires_usefulness_check": True,

        "response_requires_context_check": True,

        "response_requires_psychology_check": True
    }
    # =====================================================
    # 🔥 APRIL MASTER AUTHORITY
    # =====================================================

    result["visual_obligation"] = False

    result["forced_room"] = None

    result["forced_action"] = None


    # =====================================================
    # 🔥 APRIL GLOBAL DECISION
    # =====================================================

    if (

        cognition.get(
            "prefer_visual"
        )

        or cognition.get(
            "wants_visual",
            0.0
        ) >= 0.45

        or cognition.get(
            "visual_imagination",
            0.0
        ) >= 0.45

        or cognition.get(
            "wants_result",
            0.0
        ) >= 0.72
    ):

        result["final_action"] = (
            "generate"
        )

        result["forced_action"] = (
            "generate"
        )

        result["forced_room"] = (
            "image_generate"
        )

        result["visual_obligation"] = True

        result["should_generate"] = True

        result["generation_allowed"] = True

    # =====================================================
    # 🔥 EXECUTION PRESSURE
    # =====================================================

    execution_pressure = cognition.get(
        "execution_pressure",
        0.0
    )

    wants_result = cognition.get(
        "wants_result",
        0.0
    )

    wants_visual = cognition.get(
        "wants_visual",
        0.0
    )

    dialog_fatigue = cognition.get(
        "dialog_fatigue",
        0.0
    )

    assistant_restraint = cognition.get(
        "assistant_restraint",
        0.0
    )

    unresolved_intent = semantic.get(
        "unresolved_intent",
        True
    )

    ambiguity = semantic.get(
        "ambiguity_level",
        0.0
    )

    goal_stage = semantic.get(
        "goal_stage",
        "exploration"
    )

    # =====================================================
    # 🔥 UNDERSTANDING USER
    # =====================================================

    if cognition.get(
        "user_leads_direction"
    ):

        result[
            "understands_user_direction"
        ] = True

        result[
            "should_follow_user"
        ] = True

    if (
        cognition.get(
            "wants_action",
            0.0
        ) >= 0.5
        or cognition.get(
            "wants_help",
            0.0
        ) >= 0.5
        or cognition.get(
            "wants_visual",
            0.0
        ) >= 0.5
    ):

        result[
            "understands_user_goal"
        ] = True

    # =====================================================
    # 🔥 CONTINUATION
    # =====================================================

    if cognition.get(
        "needs_continuation"
    ):

        result[
            "should_continue_trajectory"
        ] = True

    if active_flow:

        result[
            "maintain_goal_trajectory"
        ] = True

        result[
            "dialogue_still_alive"
        ] = True

    # =====================================================
    # 🔥 REDUCE TALKING
    # =====================================================

    if cognition.get(
        "reduce_talking"
    ):

        result[
            "should_reduce_talking"
        ] = True

    if dialog_fatigue >= 0.7:

        result[
            "response_mode"
        ] = "compact"

    # =====================================================
    # 🔥 GUIDANCE
    # =====================================================

    if cognition.get(
        "needs_guidance"
    ):

        result[
            "should_guide"
        ] = True

        result[
            "guidance_allowed"
        ] = True

        result[
            "response_mode"
        ] = "guide"

    # =====================================================
    # 🔥 VISUAL REFERENCE MODE
    # =====================================================

    if cognition.get(
        "prefer_reference_over_generation"
    ):

        result[
            "should_offer_reference"
        ] = True

        result[
            "prefer_lightweight_visual"
        ] = True

        result[
            "avoid_heavy_generation"
        ] = True

    # =====================================================
    # 🔥 VISUAL REFERENCE SYSTEM
    # =====================================================

    if visual_reference.get(
        "enabled"
    ):

        result[
            "prefer_lightweight_visual"
        ] = True

    if visual_reference.get(
        "lightweight_mode"
    ):

        result[
            "prefer_lightweight_visual"
        ] = True

        result[
            "avoid_heavy_generation"
        ] = True

    # =====================================================
    # 🔥 RESTRAINT
    # =====================================================

    result[
        "assistant_restraint"
    ] = assistant_restraint

    if cognition.get(
        "generation_should_wait"
    ):

        result[
            "should_wait_for_user"
        ] = True

        result[
            "avoid_forced_generation"
        ] = True

    # =====================================================
    # 🔥 EXPLORATION MODE
    # =====================================================

    if cognition.get(
        "exploration_mode"
    ):

        result[
            "response_mode"
        ] = "exploration"

        result[
            "final_action"
        ] = "guide"

        result[
            "should_guide"
        ] = True

        result[
            "guidance_allowed"
        ] = True

        result[
            "avoid_heavy_generation"
        ] = True

    # =====================================================
    # 🔥 EXECUTION AUTHORITY
    # =====================================================

    should_execute = False

    if semantic.get(
        "should_execute"
    ):

        should_execute = True

    if (
        execution_pressure >= 0.75
        and ambiguity < 0.45
    ):

        should_execute = True

    if (
        wants_result >= 0.8
        and ambiguity < 0.45
    ):

        should_execute = True

    # =====================================================
    # 🔥 USER LEADS → EXECUTION RESTRAINT
    # =====================================================

    if cognition.get(
        "user_leads_direction"
    ):

        if cognition.get(
            "exploration_mode"
        ):

            should_execute = False

    # =====================================================
    # 🔥 UNRESOLVED INTENT PROTECTION
    # =====================================================

    if unresolved_intent:

        result[
            "dialogue_still_alive"
        ] = True

        result[
            "goal_completed"
        ] = False

    # =====================================================
    # 🔥 FINAL EXECUTION
    # =====================================================

    if should_execute:

        result[
            "should_execute"
        ] = True

        result[
            "execution_allowed"
        ] = True

    # =====================================================
    # 🔥 GENERATION CONTROL
    # =====================================================

    should_generate = False

    if visual_reference.get(
        "should_generate"
    ):

        should_generate = True

    if (
        wants_visual >= 0.85
        and wants_result >= 0.75
        and not cognition.get(
            "prefer_reference_over_generation"
        )
        and ambiguity < 0.4
    ):

        should_generate = True

    # =====================================================
    # 🔥 RESTRAINT SUPPRESSION
    # =====================================================

    if result[
        "should_wait_for_user"
    ]:

        should_generate = False

    if assistant_restraint >= 0.7:

        should_generate = False

    if cognition.get(
        "exploration_mode"
    ):

        should_generate = False

    # =====================================================
    # 🔥 FINAL GENERATION
    # =====================================================

    if should_generate:

        result[
            "should_generate"
        ] = True

        result[
            "generation_allowed"
        ] = True

    # =====================================================
    # 🔥 POST ACTION ANALYSIS
    # =====================================================

    if result[
        "should_generate"
    ] or result[
        "should_execute"
    ]:

        result[
            "needs_post_action_analysis"
        ] = True

        result[
            "dialogue_still_alive"
        ] = True

        result[
            "goal_completed"
        ] = False

    # =====================================================
    # 🔥 RESPONSE PRIORITY SYSTEM
    # =====================================================

    # =================================================
    # 1. WAIT
    # =====================================================

    if result[
        "should_wait_for_user"
    ]:

        result[
            "final_action"
        ] = "wait"

    # =================================================
    # 2. REFERENCE
    # =====================================================

    elif result[
        "should_offer_reference"
    ]:

        result[
            "final_action"
        ] = "reference"

    # =================================================
    # 3. GENERATE
    # =====================================================

    elif result[
        "should_generate"
    ]:

        result[
            "final_action"
        ] = "generate"

    # =================================================
    # 4. EXECUTE
    # =====================================================

    elif result[
        "should_execute"
    ]:

        result[
            "final_action"
        ] = "execute"

    # =================================================
    # 5. GUIDE
    # =====================================================

    elif result[
        "should_guide"
    ]:

        result[
            "final_action"
        ] = "guide"

    # =================================================
    # 6. TALK
    # =====================================================

    else:

        result[
            "final_action"
        ] = "talk"

    # =====================================================
    # 🔥 RESPONSE STYLE CONTROL
    # =====================================================

    if result[
        "final_action"
    ] == "execute":

        result[
            "response_mode"
        ] = "execution"

    elif result[
        "final_action"
    ] == "generate":

        result[
            "response_mode"
        ] = "visual_generation"

    elif result[
        "final_action"
    ] == "reference":

        result[
            "response_mode"
        ] = "visual_guidance"

    elif result[
        "final_action"
    ] == "guide":

        result[
            "response_mode"
        ] = "human_guidance"

    # =====================================================
    # 🔥 HUMANITY STABILIZATION
    # =====================================================

    if cognition.get(
        "is_frustrated",
        0.0
    ) >= 0.7:

        result[
            "assistant_presence"
        ] -= 0.15

        result[
            "should_reduce_talking"
        ] = True

    # =====================================================
    # 🔥 TRAJECTORY STABILIZATION
    # =====================================================

    if goal_stage == "exploration":

        result[
            "goal_completed"
        ] = False

        result[
            "dialogue_still_alive"
        ] = True

        result[
            "should_continue_trajectory"
        ] = True

    # =====================================================
    # 🔥 FINAL SAFETY
    # =====================================================

    if result[
        "should_wait_for_user"
    ]:

        result[
            "should_generate"
        ] = False

    if result[
        "avoid_heavy_generation"
    ]:

        if cognition.get(
            "exploration_mode"
        ):

            result[
                "should_generate"
            ] = False

    # =====================================================
    # 🔥 CAPABILITY SAFETY
    # =====================================================

    if (
        result["final_action"] in [
            "generate",
            "execute"
        ]
        and ambiguity >= 0.45
    ):

        result[
            "final_action"
        ] = "guide"

        result[
            "response_mode"
        ] = "human_guidance"

        result[
            "should_generate"
        ] = False

        result[
            "should_execute"
        ] = False

    return result
