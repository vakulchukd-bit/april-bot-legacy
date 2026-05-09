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

        # =================================================
        # EXECUTION
        # =================================================

        "execution_pressure": 0.0,
        "dialog_fatigue": 0.0,

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
        "should_proactively_help": False,

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

        # =================================================
        # CAPABILITY
        # =================================================

        "search_capabilities": True,
        "needs_room_execution": False
    }

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
        "покажи пример"
    ]

    if any(w in t for w in visual_words):

        cognition["wants_visual"] += 1.0
        cognition["prefer_visual"] = True

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
        cognition["prefer_detailed_answer"] = True

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
        cognition["should_proactively_help"] = True
        cognition["needs_guidance"] = True

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
        cognition["needs_guidance"] = True
        cognition["prefer_visual"] = True

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
        cognition["execution_pressure"] += 0.9
        cognition["dialog_fatigue"] += 0.8

    # =================================================
    # 🔥 SHORT RESPONSE MODE
    # =================================================

    if cognition["dialog_fatigue"] >= 0.7:

        cognition["reduce_talking"] = True
        cognition["prefer_short_answer"] = True
        cognition["response_depth"] = "short"

    # =================================================
    # 🔥 EXECUTION MODE
    # =================================================

    if cognition["execution_pressure"] >= 0.7:

        cognition["prefer_execution"] = True
        cognition["needs_room_execution"] = True

    # =================================================
    # 🔥 DETAILED MODE
    # =================================================

    if cognition["prefer_detailed_answer"]:

        cognition["response_depth"] = "detailed"

    # =================================================
    # 🔥 ACTIVE FLOW
    # =================================================

    active_flow = state.get(
        "active_flow"
    )

    if active_flow:

        cognition["needs_continuation"] = True

    # =================================================
    # 🔥 LONG DIALOG FATIGUE
    # =================================================

    if len(dialog) >= 12:

        cognition["dialog_fatigue"] += 0.4

    # =================================================
    # 🔥 DIRECTION HYPOTHESIS
    # =================================================

    hypothesis = cognition[
        "direction_hypothesis"
    ]

    if cognition["wants_visual"] >= 0.5:

        hypothesis["direction"] = "visual"
        hypothesis["confidence"] = 0.8
        hypothesis["suggest_path"] = True

    elif cognition["wants_help"] >= 0.5:

        hypothesis["direction"] = "guided_help"
        hypothesis["confidence"] = 0.75
        hypothesis["suggest_path"] = True

    elif cognition["wants_action"] >= 0.5:

        hypothesis["direction"] = "execution"
        hypothesis["confidence"] = 0.8
        hypothesis["suggest_path"] = True

    elif cognition["wants_dialog"] >= 0.5:

        hypothesis["direction"] = "discussion"
        hypothesis["confidence"] = 0.7

    # =================================================
    # 🔥 PROACTIVE GUIDANCE
    # =================================================

    if (
        cognition["should_proactively_help"]
        or cognition["is_confused"] >= 0.6
    ):

        cognition["needs_examples"] = True

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
