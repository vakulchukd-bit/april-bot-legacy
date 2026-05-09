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

    # =================================================
    # 🔥 BASE
    # =================================================

    cognition = {

        # =================================================
        # USER INTENTION FIELD
        # =================================================

        "wants_action": 0.0,
        "wants_dialog": 0.0,
        "wants_result": 0.0,
        "wants_visual": 0.0,
        "wants_help": 0.0,
        "wants_precision": 0.0,
        "wants_speed": 0.0,

        # =================================================
        # USER STATE
        # =================================================

        "is_confused": 0.0,
        "is_waiting": 0.0,
        "is_frustrated": 0.0,
        "is_uncertain": 0.0,

        # =================================================
        # EXECUTION
        # =================================================

        "execution_pressure": 0.0,
        "dialog_fatigue": 0.0,
        "result_pressure": 0.0,

        # =================================================
        # RESPONSE STRATEGY
        # =================================================

        "reduce_talking": False,
        "prefer_execution": False,
        "prefer_visual": False,
        "prefer_short_answer": False,
        "prefer_detailed_answer": False,

        # =================================================
        # RESPONSE ORCHESTRATION
        # =================================================

        "response_depth": "medium",
        "needs_guidance": False,
        "needs_examples": False,
        "needs_clarification": False,
        "should_proactively_help": False,
        "should_offer_direction": False,
        "should_reduce_explanation": False,

        # =================================================
        # DIRECTION HYPOTHESIS
        # =================================================

        "direction_hypothesis": {
            "enabled": True,
            "confidence": 0.0,
            "direction": None,
            "suggest_path": False
        },

        # =================================================
        # TRAJECTORY
        # =================================================

        "goal_completed": False,
        "needs_continuation": False,
        "trajectory_locked": False,
        "trajectory_confidence": 0.0,

        # =================================================
        # SATISFACTION MODEL
        # =================================================

        "user_satisfaction_expected": 0.5,
        "risk_of_bolтовня": 0.0,
        "expectation_mismatch": 0.0,

        # =================================================
        # CAPABILITY
        # =================================================

        "search_capabilities": True,
        "needs_room_execution": False,
        "capability_routing": None,

        # =================================================
        # VISUAL SUPPORT
        # =================================================

        "should_offer_visual_support": False,
        "visual_support_priority": 0.0,

        # =================================================
        # EXECUTION BEHAVIOR
        # =================================================

        "execution_urgency": 0.0,
        "execution_confidence": 0.0,

        # =================================================
        # 🧠 PSYCHOLOGY LAYER
        # =================================================

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

        "human_psychology_weight": 0.5
    }

    # =================================================
    # 🔥 SEMANTIC INHERITANCE
    # =================================================

    cognition["execution_pressure"] += semantic.get(
        "execution_pressure",
        0.0
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
    # =================================================

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
        cognition["execution_pressure"] += 0.7
        cognition["result_pressure"] += 0.7
        cognition["execution_urgency"] += 0.6

    # =================================================
    # 🔥 VISUAL SIGNALS
    # =================================================

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
        cognition["visual_support_priority"] += 0.8

        cognition[
            "should_offer_visual_support"
        ] = True

    # =================================================
    # 🔥 DIALOG SIGNALS
    # =================================================

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
    # =================================================

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
    # 🔥 CONFUSION SIGNALS
    # =================================================

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
    # =================================================

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
        ] += 0.9

        cognition[
            "dialog_fatigue"
        ] += 0.8

        cognition[
            "risk_of_bolтовня"
        ] += 0.8

    # =================================================
    # 🔥 USER LEADERSHIP DETECTION
    # =================================================

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
            "prefer_execution"
        ] = False

        cognition[
            "execution_pressure"
        ] -= 0.25

    # =================================================
    # 🔥 EXPLORATION MODE
    # =================================================

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
    # =================================================

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
    # =================================================

    if len(dialog) >= 10:

        cognition[
            "dialog_fatigue"
        ] += 0.4

    if len(dialog) >= 16:

        cognition[
            "risk_of_bolтовня"
        ] += 0.5

    # =================================================
    # 🔥 RESPONSE ECONOMY
    # =================================================

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
    # =================================================

    if cognition[
        "execution_pressure"
    ] >= 0.7:

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
    # =================================================

    if cognition[
        "prefer_detailed_answer"
    ]:

        cognition[
            "response_depth"
        ] = "detailed"

    # =================================================
    # 🔥 ACTIVE FLOW
    # =================================================

    active_flow = state.get(
        "active_flow"
    )

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

    # =================================================
    # 🔥 DIRECTION HYPOTHESIS
    # =================================================

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
        ] = 0.85

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
        ] = 0.85

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
    # =================================================

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
    # =================================================

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
    # =================================================

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
    # =================================================

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
    # =================================================

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
    # =================================================

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
    # =================================================

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
    # =================================================

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
    # =================================================

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
    # 🔥 FINAL NORMALIZATION
    # =================================================

    for key, value in cognition.items():

        if isinstance(value, float):

            if value > 1.0:
                cognition[key] = 1.0

            if value < 0.0:
                cognition[key] = 0.0

    return cognition
