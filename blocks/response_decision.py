# =====================================================
# 🧠 RESPONSE DECISION SYSTEM
# =====================================================

def build_response_decision(
    semantic: dict,
    cognition: dict,
    visual_reference: dict,
    state: dict
):

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

        "final_action": "talk"
    }

    # =====================================================
    # 🔥 EXECUTION
    # =====================================================

    if semantic.get(
        "should_execute"
    ):

        result[
            "should_execute"
        ] = True

    # =====================================================
    # 🔥 GENERATION
    # =====================================================

    if visual_reference.get(
        "should_generate"
    ):

        result[
            "should_generate"
        ] = True

        result[
            "final_action"
        ] = "generate"

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
            "response_mode"
        ] = "guide"

    # =====================================================
    # 🔥 TRAJECTORY
    # =====================================================

    if cognition.get(
        "needs_continuation"
    ):

        result[
            "should_continue_trajectory"
        ] = True

    # =====================================================
    # 🔥 USER LEADS
    # =====================================================

    if cognition.get(
        "user_leads_direction"
    ):

        result[
            "should_follow_user"
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

        result[
            "final_action"
        ] = "reference"

    # =====================================================
    # 🔥 RESTRAINT
    # =====================================================

    if cognition.get(
        "generation_should_wait"
    ):

        result[
            "should_wait_for_user"
        ] = True

        result[
            "should_generate"
        ] = False

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

    # =====================================================
    # 🔥 FINAL SAFETY
    # =====================================================

    if result[
        "should_wait_for_user"
    ]:

        result[
            "should_generate"
        ] = False

    return result
