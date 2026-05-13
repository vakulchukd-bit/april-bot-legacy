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
        # 🧠 SCENE COMPLETION
        # =================================================

        "scene_completion_required": False,

        "scene_practical_goal_alive": False,

        "scene_has_multiple_meanings": False,

        "scene_needs_enrichment": False,

        "scene_completion_confidence": 0.0,

        "should_expand_reasoning": False,

        "should_preserve_scene_layers": True,

        "should_allow_tool_enrichment": False,

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

        "response_requires_psychology_check": True,

        # =================================================
        # 🔥 DEEPHUB STABILIZATION
        # =================================================

        "high_ambiguity_detected": False,

        "response_requires_clarification": False,

        "exploration_generation_mix": False
    }

    # =====================================================
    # 🔥 APRIL MASTER AUTHORITY
    # =====================================================

    result["visual_obligation"] = False

    result["forced_room"] = None

    result["forced_action"] = None

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

    wants_dialog = cognition.get(
        "wants_dialog",
        0.0
    )

    wants_help = cognition.get(
        "wants_help",
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
    # 🧠 SCENE COMPLETION ANALYSIS
    # =====================================================

    practical_goal_alive = False

    if (
        wants_result >= 0.45
        or wants_help >= 0.45
        or execution_pressure >= 0.45
        or cognition.get(
            "internet_context_needed"
        )
    ):

        practical_goal_alive = True

    result[
        "scene_practical_goal_alive"
    ] = practical_goal_alive

    multiple_meanings = 0

    if wants_dialog >= 0.4:
        multiple_meanings += 1

    if wants_result >= 0.4:
        multiple_meanings += 1

    if wants_visual >= 0.4:
        multiple_meanings += 1

    if wants_help >= 0.4:
        multiple_meanings += 1

    if multiple_meanings >= 2:

        result[
            "scene_has_multiple_meanings"
        ] = True

    # =====================================================
    # 🧠 SCENE CONTINUITY PROTECTION
    # =====================================================

    if (

        result[
            "scene_has_multiple_meanings"
        ]

        or practical_goal_alive

        or unresolved_intent
    ):

        result[
            "scene_completion_required"
        ] = True

        result[
            "dialogue_still_alive"
        ] = True

        result[
            "goal_completed"
        ] = False

    # =====================================================
    # 🧠 ENRICHMENT POSSIBILITY
    # =====================================================

    if (

        practical_goal_alive

        and not cognition.get(
            "exploration_mode"
        )

        and ambiguity < 0.7
    ):

        result[
            "scene_needs_enrichment"
        ] = True

        result[
            "should_allow_tool_enrichment"
        ] = True

    # =====================================================
    # 🔥 APRIL GLOBAL DECISION
    # =====================================================

    if (

        not cognition.get(
            "internet_context_needed"
        )

        and not cognition.get(
            "web_support_required"
        )

        and (

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
        )
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
        or cognition.get(
            "wants_result",
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

        # 🔥 DeepHub stabilization:
        # exploration больше НЕ запрещает generation

        result[
            "exploration_generation_mix"
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

        # 🔥 DeepHub:
        # ожидание пользователя больше
        # НЕ убивает generation pipeline

        result[
            "response_requires_clarification"
        ] = True

    if assistant_restraint >= 0.7:

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
    # 🧠 SCENE COMPLETION PRESSURE
    # =====================================================

    if (

        result[
            "scene_completion_required"
        ]

        and result[
            "understands_user_goal"
        ]
    ):

        result[
            "scene_completion_confidence"
        ] = 0.82

        result[
            "should_expand_reasoning"
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

    if result[
        "should_wait_for_user"
    ]:

        result[
            "final_action"
        ] = "wait"

    elif result[
        "should_offer_reference"
    ]:

        result[
            "final_action"
        ] = "reference"

    elif result[
        "should_generate"
    ]:

        result[
            "final_action"
        ] = "generate"

    elif result[
        "should_execute"
    ]:

        result[
            "final_action"
        ] = "execute"

    elif result[
        "should_guide"
    ]:

        result[
            "final_action"
        ] = "guide"

    else:

        result[
            "final_action"
        ] = "talk"

    # =====================================================
    # 🧠 PREMATURE SCENE CLOSURE PROTECTION
    # =====================================================

    if (

        result[
            "final_action"
        ] == "talk"

        and result[
            "scene_practical_goal_alive"
        ]

        and result[
            "should_allow_tool_enrichment"
        ]
    ):

        result[
            "dialogue_still_alive"
        ] = True

        result[
            "goal_completed"
        ] = False

        result[
            "should_expand_reasoning"
        ] = True

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
        "avoid_heavy_generation"
    ]:

        if cognition.get(
            "exploration_mode"
        ):

            result[
                "exploration_generation_mix"
            ] = True

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

        # 🔥 DeepHub stabilization:
        # ambiguity больше НЕ ломает execution

        result[
            "high_ambiguity_detected"
        ] = True

        result[
            "response_requires_clarification"
        ] = True

        result[
            "scene_completion_confidence"
        ] *= 0.82

    return result
