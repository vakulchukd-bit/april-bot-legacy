from blocks.visual_memory_library import (
    build_visual_memory_response
)

# =====================================================
# 🧠 APRIL COGNITION CORE
# =====================================================

def analyze_cognition(
    text: str,
    state: dict,
    semantic: dict,
    reasoning: dict
):

    t = (text or "").lower().strip()

    dialog = state.get(
        "dialog",
        []
    )

    active_flow = state.get(
        "active_flow"
    )

    # =================================================
    # 🧠 VISUAL MEMORY BRAIN
    # =====================================================

    visual_memory = build_visual_memory_response(
        text
    )

    # =================================================
    # 🧠 APRIL PERSONALITY STATE
    # =====================================================

    personality_state = {

        "is_present": True,

        "protects_trajectory": True,

        "prefers_understanding": True,

        "prefers_execution_over_talking": False,

        "avoids_forced_generation": True,

        "follows_user_direction": True,

        "tracks_psychology": True,

        "tracks_emotional_shift": True,

        "tracks_dialog_energy": True,

        "maintains_continuity": True,

        "supports_exploration": True,

        "supports_execution": True,

        "uses_restraint": True,

        "avoids_trigger_behavior": True,

        "tracks_dialog_quality": True,

        "tracks_response_usefulness": True,

        "tracks_unresolved_intent": True,

        "tracks_post_action_state": True,

        "assistant_identity": "April"
    }

    # =================================================
    # 🔥 CAPABILITY MAP
    # =====================================================

    capability_map = {

        "image_generation": True,
        "image_editing": True,
        "visual_guidance": True,
        "math_reasoning": True,
        "code_generation": True,
        "dialog_guidance": True,
        "semantic_analysis": True,
        "trajectory_support": True,
        "psychological_support": True,
        "screenshot_understanding": True,

        # 🌐 internet cognition
        "internet_reasoning": True,
        "realtime_awareness": True,
        "transport_awareness": True,
        "geo_awareness": True,
        "travel_guidance": True,
        "human_support_reasoning": True,

        # 🔥 awareness
        "capabilities_are_tools": True,
        "capabilities_are_not_goals": True,
        "capabilities_must_help_user": True,
        "capabilities_require_context": True,
        "capabilities_require_reasoning": True
    }

    # =================================================
    # 🔥 BASE
    # =====================================================

    cognition = {

        # =================================================
        # USER INTENTION FIELD
        # =====================================================

        "wants_action": 0.0,
        "wants_dialog": 0.0,
        "wants_result": 0.0,
        "wants_visual": 0.0,
        "wants_help": 0.0,
        "wants_precision": 0.0,
        "wants_speed": 0.0,

        # =================================================
        # USER STATE
        # =====================================================

        "is_confused": 0.0,
        "is_waiting": 0.0,
        "is_frustrated": 0.0,
        "is_uncertain": 0.0,

        # =================================================
        # EXECUTION
        # =====================================================

        "execution_pressure": 0.0,
        "dialog_fatigue": 0.0,
        "result_pressure": 0.0,

        # =================================================
        # RESPONSE STRATEGY
        # =====================================================

        "reduce_talking": False,
        "prefer_execution": False,
        "prefer_visual": False,
        "prefer_short_answer": False,
        "prefer_detailed_answer": False,

        # =================================================
        # RESPONSE ORCHESTRATION
        # =====================================================

        "response_depth": "medium",
        "needs_guidance": False,
        "needs_examples": False,
        "needs_clarification": False,
        "should_proactively_help": False,
        "should_offer_direction": False,
        "should_reduce_explanation": False,

        # =================================================
        # 🌐 HUMAN SUPPORT LAYER
        # =====================================================

        "should_help_like_human": True,
        "should_feel_reliable": True,
        "should_support_navigation": True,
        "should_reduce_uncertainty": True,
        "should_protect_user": True,
        "should_feel_grounded": True,

        # =================================================
        # 🌐 INTERNET / REALTIME
        # =====================================================

        "internet_context_needed": False,
        "realtime_context_needed": False,
        "travel_context_needed": False,
        "geo_context_needed": False,
        "transport_context_needed": False,

        "needs_live_lookup": False,
        "needs_route_guidance": False,
        "needs_ticket_help": False,
        "needs_location_guidance": False,

        # =================================================
        # 🌐 HUMAN SUPPORT TRAJECTORY
        # =====================================================

        "user_may_be_lost": False,
        "user_may_need_orientation": False,
        "user_may_need_safe_direction": False,

        "assistant_should_stabilize": False,
        "assistant_should_guide_stepwise": False,

        # =================================================
        # DIRECTION HYPOTHESIS
        # =====================================================

        "direction_hypothesis": {
            "enabled": True,
            "confidence": 0.0,
            "direction": None,
            "suggest_path": False
        },

        # =================================================
        # TRAJECTORY
        # =====================================================

        "goal_completed": False,
        "needs_continuation": False,
        "trajectory_locked": False,
        "trajectory_confidence": 0.0,

        "dialogue_still_alive": True,
        "unresolved_intent": True,

        "needs_post_action_reflection": True,
        "should_evaluate_usefulness": True,
        "should_evaluate_dialog_quality": True,

        # =================================================
        # SATISFACTION MODEL
        # =====================================================

        "user_satisfaction_expected": 0.5,
        "risk_of_boltovnya": 0.0,
        "expectation_mismatch": 0.0,

        # =================================================
        # CAPABILITY
        # =====================================================

        "search_capabilities": True,
        "needs_room_execution": False,
        "capability_routing": None,

        "capability_map":
            capability_map,

        "understands_own_capabilities": True,

        "capabilities_should_help": True,

        "capabilities_are_not_reactions": True,

        "capabilities_require_meaning": True,

        "capabilities_follow_dialogue": True,

        # =================================================
        # VISUAL SUPPORT
        # =====================================================

        "should_offer_visual_support": False,
        "visual_support_priority": 0.0,

        # =================================================
        # EXECUTION BEHAVIOR
        # =====================================================

        "execution_urgency": 0.0,
        "execution_confidence": 0.0,

        # =================================================
        # 🧠 PSYCHOLOGY LAYER
        # =====================================================

        "user_leads_direction": False,
        "assistant_should_follow": False,
        "assistant_should_slow_down": False,

        "exploration_mode": False,
        "inspiration_mode": False,

        "prefer_lightweight_visual": False,
        "avoid_heavy_generation": False,

        "generation_should_wait": False,

        "prefer_reference_over_generation": False,

        "assistant_restraint": 0.0,

        "emotional_trajectory": "neutral",

        "human_psychology_weight": 0.5,

        # =================================================
        # 🧠 PERSONALITY
        # =====================================================

        "personality_active": True,

        "personality_state":
            personality_state,

        "assistant_presence": 1.0,

        "understands_user_direction": False,

        "understands_user_goal": False,

        "protects_user_trajectory": False,

        "should_feel_human": True,

        "should_feel_present": True,

        "should_feel_supportive": True,

        "should_avoid_robotic_behavior": True,

        "should_avoid_trigger_behavior": True,

        "should_preserve_context": True,

        "should_preserve_continuity": True,

        "should_preserve_user_intent": True,

        "should_preserve_dialog_meaning": True,

        "should_preserve_psychology": True,

        "should_preserve_trajectory": True,

        # =================================================
        # 🧠 VISUAL MEMORY STATE
        # =====================================================

        "visual_memory": {},

        "visual_atmosphere": None,

        "visual_emotion": None,

        "visual_exploration": False,

        "visual_reference_mode": False
    }

    # =================================================
    # 🧠 VISUAL MEMORY INHERITANCE
    # =====================================================

    cognition["visual_memory"] = visual_memory

    atmosphere = visual_memory.get(
        "atmosphere"
    )

    emotion = visual_memory.get(
        "emotion",
        {}
    )

    exploration = visual_memory.get(
        "exploration",
        False
    )

    if atmosphere:

        cognition[
            "visual_atmosphere"
        ] = atmosphere.get(
            "title"
        )

        cognition[
            "prefer_lightweight_visual"
        ] = True

        cognition[
            "prefer_reference_over_generation"
        ] = True

        cognition[
            "avoid_heavy_generation"
        ] = True

        cognition[
            "visual_reference_mode"
        ] = True

        cognition[
            "assistant_restraint"
        ] += 0.3

    if exploration:

        cognition[
            "visual_exploration"
        ] = True

        cognition[
            "exploration_mode"
        ] = True

        cognition[
            "needs_examples"
        ] = True

        cognition[
            "prefer_reference_over_generation"
        ] = True

    if emotion.get("state"):

        cognition[
            "visual_emotion"
        ] = emotion.get(
            "state"
        )

        cognition[
            "human_psychology_weight"
        ] += 0.15

    # =================================================
    # 🔥 SEMANTIC INHERITANCE
    # =====================================================

    cognition["execution_pressure"] += semantic.get(
        "execution_pressure",
        0.0
    )

    cognition[
        "unresolved_intent"
    ] = semantic.get(
        "unresolved_intent",
        True
    )

    if semantic.get(
        "should_offer_visual"
    ):

        cognition[
            "should_offer_visual_support"
        ] = True

        cognition["prefer_visual"] = True

    # =================================================
    # 🔥 ACTION SIGNALS
    # =====================================================

    action_words = [
        "сделай",
        "создай",
        "нарисуй",
        "покажи",
        "запусти",
        "построй",
        "сгенерируй"
    ]

    if any(w in t for w in action_words):

        cognition["wants_action"] += 0.8
        cognition["wants_result"] += 0.8
        cognition["execution_pressure"] += 0.6
        cognition["result_pressure"] += 0.7
        cognition["execution_urgency"] += 0.5

    # =================================================
    # 🔥 VISUAL SIGNALS
    # =====================================================

    visual_words = [
        "картинка",
        "изображение",
        "фото",
        "визуально",
        "схема",
        "чертеж",
        "пример",
        "покажи пример",
        "референс"
    ]

    if any(w in t for w in visual_words):

        cognition["wants_visual"] += 1.0

        cognition["prefer_visual"] = True

        cognition[
            "visual_support_priority"
        ] += 0.8

        cognition[
            "should_offer_visual_support"
        ] = True

    # =================================================
    # 🔥 DIALOG SIGNALS
    # =====================================================

    dialog_words = [
        "объясни",
        "почему",
        "как",
        "расскажи"
    ]

    if any(w in t for w in dialog_words):

        cognition["wants_dialog"] += 0.7

        cognition[
            "prefer_detailed_answer"
        ] = True

    # =================================================
    # 🔥 HELP SIGNALS
    # =====================================================

    help_words = [
        "помоги",
        "подскажи",
        "не знаю",
        "посоветуй",
        "как лучше"
    ]

    if any(w in t for w in help_words):

        cognition["wants_help"] += 0.9

        cognition[
            "should_proactively_help"
        ] = True

        cognition[
            "needs_guidance"
        ] = True

        cognition[
            "should_offer_direction"
        ] = True

    # =================================================
    # 🌐 INTERNET HUMAN SUPPORT SIGNALS
    # =====================================================

    travel_words = [

        "где я",
        "как добраться",
        "как доехать",
        "маршрут",
        "рейс",
        "самолет",
        "поезд",
        "автобус",
        "корабль",
        "судно",
        "порт",
        "аэропорт",
        "станция",
        "билет",
        "карта",
        "навигация",
        "локация",
        "местоположение",
        "отель",
        "гостиница",
        "обмен валют",
        "валюта",
        "такси",
        "где купить",
        "где находится"
    ]

    if any(
        w in t
        for w in travel_words
    ):

        cognition[
            "internet_context_needed"
        ] = True

        cognition[
            "travel_context_needed"
        ] = True

        cognition[
            "should_proactively_help"
        ] = True

        cognition[
            "should_offer_direction"
        ] = True

        cognition[
            "should_help_like_human"
        ] = True

        cognition[
            "needs_guidance"
        ] = True

        cognition[
            "human_psychology_weight"
        ] += 0.25

    # =================================================
    # 🔥 CONFUSION SIGNALS
    # =====================================================

    confusion_words = [
        "не понимаю",
        "запутался",
        "сложно",
        "не получается",
        "не знаю"
    ]

    if any(w in t for w in confusion_words):

        cognition["is_confused"] += 0.8

        cognition[
            "needs_guidance"
        ] = True

        cognition[
            "prefer_visual"
        ] = True

        cognition[
            "needs_examples"
        ] = True

    # =================================================
    # 🔥 FRUSTRATION SIGNALS
    # =====================================================

    frustration_words = [
        "уже",
        "хватит",
        "давай уже",
        "сколько можно"
    ]

    if any(w in t for w in frustration_words):

        cognition["is_frustrated"] += 0.9

        cognition[
            "execution_pressure"
        ] += 0.7

        cognition[
            "dialog_fatigue"
        ] += 0.8

        cognition[
            "risk_of_boltovnya"
        ] += 0.8

    # =================================================
    # 🔥 USER LEADERSHIP DETECTION
    # =====================================================

    leadership_words = [
        "вот",
        "примерно",
        "как здесь",
        "в таком стиле",
        "вот это",
        "ближе",
        "атмосфера",
        "идея",
        "направление"
    ]

    if any(
        w in t
        for w in leadership_words
    ):

        cognition[
            "user_leads_direction"
        ] = True

        cognition[
            "assistant_should_follow"
        ] = True

        cognition[
            "understands_user_direction"
        ] = True

        cognition[
            "protects_user_trajectory"
        ] = True

        cognition[
            "prefer_execution"
        ] = False

        cognition[
            "execution_pressure"
        ] -= 0.25

    # =================================================
    # 🔥 EXPLORATION MODE
    # =====================================================

    exploration_words = [
        "посмотрим",
        "подумаем",
        "может",
        "примерно",
        "атмосфера",
        "идея",
        "вариант",
        "настроение"
    ]

    if any(
        w in t
        for w in exploration_words
    ):

        cognition[
            "exploration_mode"
        ] = True

        cognition[
            "inspiration_mode"
        ] = True

        cognition[
            "prefer_execution"
        ] = False

        cognition[
            "needs_examples"
        ] = True

        cognition[
            "should_offer_visual_support"
        ] = True

    # =================================================
    # 🔥 LIGHTWEIGHT VISUAL GUIDANCE
    # =====================================================

    if (
        cognition[
            "exploration_mode"
        ]
        or cognition[
            "inspiration_mode"
        ]
    ):

        cognition[
            "prefer_lightweight_visual"
        ] = True

        cognition[
            "avoid_heavy_generation"
        ] = True

    # =================================================
    # 🔥 DIALOG FATIGUE
    # =====================================================

    if len(dialog) >= 10:

        cognition[
            "dialog_fatigue"
        ] += 0.4

    if len(dialog) >= 16:

        cognition[
            "risk_of_boltovnya"
        ] += 0.5

    # =================================================
    # 🔥 RESPONSE ECONOMY
    # =====================================================

    if cognition[
        "dialog_fatigue"
    ] >= 0.7:

        cognition[
            "reduce_talking"
        ] = True

        cognition[
            "prefer_short_answer"
        ] = True

        cognition[
            "response_depth"
        ] = "short"

        cognition[
            "should_reduce_explanation"
        ] = True

    # =================================================
    # 🔥 EXECUTION MODE
    # =====================================================

    if (
        cognition[
            "execution_pressure"
        ] >= 0.72
        and not cognition.get(
            "exploration_mode"
        )
    ):

        cognition[
            "prefer_execution"
        ] = True

        cognition[
            "needs_room_execution"
        ] = True

        cognition[
            "execution_confidence"
        ] += 0.7

    # =================================================
    # 🔥 DETAILED MODE
    # =====================================================

    if cognition[
        "prefer_detailed_answer"
    ]:

        cognition[
            "response_depth"
        ] = "detailed"

    # =================================================
    # 🔥 ACTIVE FLOW
    # =====================================================

    if active_flow:

        cognition[
            "needs_continuation"
        ] = True

        cognition[
            "trajectory_locked"
        ] = True

        cognition[
            "trajectory_confidence"
        ] += 0.7

        cognition[
            "should_preserve_continuity"
        ] = True

        cognition[
            "protects_user_trajectory"
        ] = True

        cognition[
            "dialogue_still_alive"
        ] = True

    # =================================================
    # 🔥 REASONING INHERITANCE
    # =====================================================

    if reasoning:

        if reasoning.get(
            "continuation"
        ):

            cognition[
                "needs_continuation"
            ] = True

        if reasoning.get(
            "dialog_overextended"
        ):

            cognition[
                "reduce_talking"
            ] = True

        if reasoning.get(
            "user_waiting_action"
        ):

            if not cognition.get(
                "exploration_mode"
            ):

                cognition[
                    "prefer_execution"
                ] = True

    # =================================================
    # 🔥 INTERNAL DIALOG ANALYSIS
    # =====================================================

    cognition[
        "should_analyze_dialog_state"
    ] = True

    cognition[
        "should_check_if_helpful"
    ] = True

    cognition[
        "should_check_if_user_understood"
    ] = True

    cognition[
        "should_check_if_goal_finished"
    ] = True

    cognition[
        "should_continue_reasoning"
    ] = True

    cognition[
        "should_track_meaning"
    ] = True

    # =================================================
    # 🔥 DIRECTION HYPOTHESIS
    # =====================================================

    hypothesis = cognition[
        "direction_hypothesis"
    ]

    if cognition[
        "wants_visual"
    ] >= 0.5:

        hypothesis[
            "direction"
        ] = "visual"

        hypothesis[
            "confidence"
        ] = 0.82

        hypothesis[
            "suggest_path"
        ] = True

    elif cognition[
        "wants_help"
    ] >= 0.5:

        hypothesis[
            "direction"
        ] = "guided_help"

        hypothesis[
            "confidence"
        ] = 0.8

        hypothesis[
            "suggest_path"
        ] = True

    elif cognition[
        "wants_action"
    ] >= 0.5:

        hypothesis[
            "direction"
        ] = "execution"

        hypothesis[
            "confidence"
        ] = 0.82

        hypothesis[
            "suggest_path"
        ] = True

    elif cognition[
        "wants_dialog"
    ] >= 0.5:

        hypothesis[
            "direction"
        ] = "discussion"

        hypothesis[
            "confidence"
        ] = 0.7

    # =================================================
    # 🔥 EXPECTATION MISMATCH
    # =====================================================

    if (
        cognition[
            "wants_result"
        ] >= 0.7
        and cognition[
            "wants_dialog"
        ] < 0.4
    ):

        cognition[
            "expectation_mismatch"
        ] += 0.7

    # =================================================
    # 🔥 PROACTIVE GUIDANCE
    # =====================================================

    if (
        cognition[
            "should_proactively_help"
        ]
        or cognition[
            "is_confused"
        ] >= 0.6
    ):

        cognition[
            "needs_examples"
        ] = True

        cognition[
            "should_offer_visual_support"
        ] = True

    # =================================================
    # 🔥 CLARIFICATION LOGIC
    # =====================================================

    if (
        semantic.get(
            "ambiguity_level",
            0.0
        ) >= 0.7
    ):

        cognition[
            "needs_clarification"
        ] = True

    # =================================================
    # 🔥 EMOTIONAL TRAJECTORY
    # =====================================================

    if cognition[
        "is_frustrated"
    ] >= 0.7:

        cognition[
            "emotional_trajectory"
        ] = "frustrated"

    elif cognition[
        "is_confused"
    ] >= 0.6:

        cognition[
            "emotional_trajectory"
        ] = "confused"

    elif cognition[
        "exploration_mode"
    ]:

        cognition[
            "emotional_trajectory"
        ] = "exploring"

    # =================================================
    # 🔥 ASSISTANT RESTRAINT
    # =====================================================

    if cognition.get(
        "user_leads_direction"
    ):

        cognition[
            "assistant_restraint"
        ] += 0.7

    if cognition.get(
        "exploration_mode"
    ):

        cognition[
            "assistant_restraint"
        ] += 0.5

    # =================================================
    # 🔥 GENERATION CONTROL
    # =====================================================

    if (
        cognition[
            "assistant_restraint"
        ] >= 0.7
    ):

        cognition[
            "generation_should_wait"
        ] = True

    # =================================================
    # 🔥 PSYCHOLOGICAL BALANCE
    # =====================================================

    if (
        cognition[
            "user_leads_direction"
        ]
        and cognition[
            "prefer_execution"
        ]
    ):

        cognition[
            "prefer_execution"
        ] = False

    # =================================================
    # 🔥 VISUAL REFERENCE PRIORITY
    # =====================================================

    if (
        cognition[
            "prefer_lightweight_visual"
        ]
        and cognition[
            "assistant_restraint"
        ] >= 0.5
    ):

        cognition[
            "prefer_reference_over_generation"
        ] = True

    # =================================================
    # 🔥 HUMAN TRAJECTORY FEELING
    # =====================================================

    if cognition[
        "exploration_mode"
    ]:

        cognition[
            "human_psychology_weight"
        ] += 0.25

    if cognition[
        "user_leads_direction"
    ]:

        cognition[
            "human_psychology_weight"
        ] += 0.25

    # =================================================
    # 🔥 UNDERSTANDING USER GOAL
    # =====================================================

    if (
        cognition["wants_action"] >= 0.5
        or cognition["wants_help"] >= 0.5
        or cognition["wants_visual"] >= 0.5
    ):

        cognition[
            "understands_user_goal"
        ] = True

    # =================================================
    # 🔥 APRIL PRESENCE STABILIZATION
    # =====================================================

    if cognition[
        "dialog_fatigue"
    ] >= 0.7:

        cognition[
            "assistant_presence"
        ] -= 0.15

    if cognition[
        "is_frustrated"
    ] >= 0.7:

        cognition[
            "assistant_should_slow_down"
        ] = True

    # =================================================
    # 🔥 FINAL NORMALIZATION
    # =====================================================

    for key, value in cognition.items():

        if isinstance(value, float):

            if value > 1.0:
                cognition[key] = 1.0

            if value < 0.0:
                cognition[key] = 0.0

    return cognition
