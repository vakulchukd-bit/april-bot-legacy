from blocks.visual_memory_library import (
    build_visual_memory_response
)

# =====================================================
# 🧠 APRIL COGNITION CORE
# =====================================================

# =====================================================
# 🔥 NORMALIZATION HELPERS
# =====================================================

def _clamp(
    value,
    minimum=0.0,
    maximum=1.0
):

    if value < minimum:
        return minimum

    if value > maximum:
        return maximum

    return value


def _increase(
    cognition: dict,
    key: str,
    amount: float
):

    cognition[key] = _clamp(
        cognition.get(
            key,
            0.0
        ) + amount
    )


def _decrease(
    cognition: dict,
    key: str,
    amount: float
):

    cognition[key] = _clamp(
        cognition.get(
            key,
            0.0
        ) - amount
    )


def _contains_any(
    text: str,
    words: list
):

    return any(
        w in text
        for w in words
    )


# =====================================================
# 🔥 SIGNAL LIBRARY
# =====================================================

ACTION_WORDS = [

    "сделай",
    "создай",
    "нарисуй",
    "покажи",
    "запусти",
    "построй",
    "сгенерируй",
    "исправь",
    "переделай",
    "апгрейд",
    "улучши"
]

VISUAL_WORDS = [

    "картинка",
    "изображение",
    "фото",
    "визуально",
    "схема",
    "чертеж",
    "пример",
    "референс",
    "атмосфера",
    "дизайн"
]

DIALOG_WORDS = [

    "объясни",
    "почему",
    "как",
    "расскажи",
    "что значит",
    "в чем проблема"
]

HELP_WORDS = [

    "помоги",
    "подскажи",
    "не знаю",
    "посоветуй",
    "как лучше"
]

CONFUSION_WORDS = [

    "не понимаю",
    "запутался",
    "сложно",
    "не получается",
    "не знаю",
    "непонятно"
]

FRUSTRATION_WORDS = [

    "уже",
    "хватит",
    "давай уже",
    "сколько можно",
    "надоело"
]

LEADERSHIP_WORDS = [

    "вот",
    "примерно",
    "как здесь",
    "в таком стиле",
    "вот это",
    "ближе",
    "идея",
    "направление"
]

EXPLORATION_WORDS = [

    "посмотрим",
    "подумаем",
    "может",
    "примерно",
    "атмосфера",
    "идея",
    "вариант",
    "настроение"
]

TRAVEL_WORDS = [

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
    "где находится",

    # 🔥 WEB / REALTIME
    "погода",
    "температура",
    "weather",
    "курс валют",
    "новости",
    "сейчас в",
    "что происходит",
    "какая погода"
]

# =====================================================
# 🔥 CENTRAL STABILITY MODEL
# =====================================================

def stabilize_cognition_state(
    cognition: dict
):

    stability = cognition.get(
        "scene_stability",
        0.5
    )

    noise = cognition.get(
        "internal_noise",
        0.0
    )

    overload = cognition.get(
        "signal_overload",
        0.0
    )

    fatigue = cognition.get(
        "dialog_fatigue",
        0.0
    )

    frustration = cognition.get(
        "is_frustrated",
        0.0
    )

    active_flow_strength = cognition.get(
        "active_flow_strength",
        0.0
    )

    if active_flow_strength >= 0.5:

        stability += 0.25

        noise -= 0.2

        overload -= 0.15

    if fatigue >= 0.7:

        noise += 0.15

        cognition[
            "reduce_talking"
        ] = True

    if frustration >= 0.7:

        cognition[
            "assistant_should_slow_down"
        ] = True

        noise += 0.1

    if cognition.get(
        "exploration_mode"
    ):

        cognition[
            "prefer_execution"
        ] = False

        cognition[
            "generation_should_wait"
        ] = True

    cognition[
        "scene_stability"
    ] = _clamp(
        stability
    )

    cognition[
        "internal_noise"
    ] = _clamp(
        noise
    )

    cognition[
        "signal_overload"
    ] = _clamp(
        overload
    )

    return cognition


# =====================================================
# 🔥 VISUAL MODE ROUTER
# =====================================================

def build_visual_mode(
    cognition: dict,
    visual_memory: dict
):

    mode = {

        "enabled": False,

        "reference_priority": False,

        "lightweight": False,

        "heavy_generation_allowed": True,

        "exploration": False,

        "emotion": None,

        "atmosphere": None
    }

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

        mode[
            "enabled"
        ] = True

        mode[
            "reference_priority"
        ] = True

        mode[
            "lightweight"
        ] = True

        mode[
            "heavy_generation_allowed"
        ] = False

        mode[
            "atmosphere"
        ] = atmosphere.get(
            "title"
        )

    if exploration:

        mode[
            "exploration"
        ] = True

        mode[
            "reference_priority"
        ] = True

    if emotion.get(
        "state"
    ):

        mode[
            "emotion"
        ] = emotion.get(
            "state"
        )

    return mode


# =====================================================
# 🔥 RESPONSE ECONOMY ENGINE
# =====================================================

def apply_response_economy(
    cognition: dict
):

    pressure = cognition.get(
        "execution_pressure",
        0.0
    )

    fatigue = cognition.get(
        "dialog_fatigue",
        0.0
    )

    overload = cognition.get(
        "signal_overload",
        0.0
    )

    if (
        fatigue >= 0.7
        or overload >= 0.7
    ):

        cognition[
            "reduce_talking"
        ] = True

        cognition[
            "prefer_short_answer"
        ] = True

        cognition[
            "response_depth"
        ] = "short"

    elif pressure >= 0.7:

        cognition[
            "response_depth"
        ] = "focused"

    return cognition


# =====================================================
# 🔥 TRAJECTORY ENGINE
# =====================================================

def stabilize_trajectory(
    cognition: dict,
    active_flow
):

    if not active_flow:
        return cognition

    cognition[
        "needs_continuation"
    ] = True

    cognition[
        "trajectory_locked"
    ] = True

    cognition[
        "protects_user_trajectory"
    ] = True

    cognition[
        "dialogue_still_alive"
    ] = True

    cognition[
        "should_preserve_continuity"
    ] = True

    cognition[
        "active_flow_strength"
    ] = 0.85

    _increase(
        cognition,
        "trajectory_confidence",
        0.3
    )

    _decrease(
        cognition,
        "internal_noise",
        0.15
    )

    return cognition


# =====================================================
# 🔥 CORE ANALYZER
# =====================================================

def analyze_cognition(
    text: str,
    state: dict,
    semantic: dict,
    reasoning: dict
):

    t = (
        text or ""
    ).lower().strip()

    dialog = state.get(
        "dialog",
        []
    )

    active_flow = state.get(
        "active_flow"
    )

    visual_memory = build_visual_memory_response(
        text
    )

    visual_mode = build_visual_mode(
        {},
        visual_memory
    )

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

        "internet_reasoning": True,
        "realtime_awareness": True,
        "transport_awareness": True,
        "geo_awareness": True,
        "travel_guidance": True,
        "human_support_reasoning": True,

        "capabilities_are_tools": True,
        "capabilities_are_not_goals": True,
        "capabilities_must_help_user": True,
        "capabilities_require_context": True,
        "capabilities_require_reasoning": True
    }

    cognition = {

        "wants_action": 0.0,
        "wants_dialog": 0.0,
        "wants_result": 0.0,
        "wants_visual": 0.0,
        "wants_help": 0.0,
        "wants_precision": 0.0,
        "wants_speed": 0.0,

        "is_confused": 0.0,
        "is_waiting": 0.0,
        "is_frustrated": 0.0,
        "is_uncertain": 0.0,

        "execution_pressure": 0.0,
        "dialog_fatigue": 0.0,
        "result_pressure": 0.0,

        "scene_stability": 0.7,
        "internal_noise": 0.15,
        "signal_overload": 0.1,
        "active_flow_strength": 0.0,

        "reduce_talking": False,
        "prefer_execution": False,
        "prefer_visual": False,
        "prefer_short_answer": False,
        "prefer_detailed_answer": False,

        "response_depth": "medium",

        "needs_guidance": False,
        "needs_examples": False,
        "needs_clarification": False,

        "should_offer_direction": False,
        "should_proactively_help": False,
        "should_reduce_explanation": False,

        "goal_completed": False,
        "needs_continuation": False,
        "trajectory_locked": False,
        "trajectory_confidence": 0.0,

        "dialogue_still_alive": True,
        "unresolved_intent": True,

        "visual_memory": visual_memory,
        "visual_mode": visual_mode,

        "visual_reference_mode":
            visual_mode.get(
                "reference_priority"
            ),

        "visual_exploration":
            visual_mode.get(
                "exploration"
            ),

        "visual_emotion":
            visual_mode.get(
                "emotion"
            ),

        "visual_atmosphere":
            visual_mode.get(
                "atmosphere"
            ),

        "personality_active": True,

        "personality_state":
            personality_state,

        "assistant_presence": 1.0,

        "assistant_restraint": 0.0,

        "human_psychology_weight": 0.5,

        "should_help_like_human": True,
        "should_feel_reliable": True,
        "should_feel_grounded": True,
        "should_protect_user": True,

        "execution_urgency": 0.0,
        "execution_confidence": 0.0,

        "exploration_mode": False,
        "inspiration_mode": False,

        "generation_should_wait": False,

        # =================================================
        # 🌐 INTERNET / WEB
        # =================================================

        "internet_context_needed": False,
        "travel_context_needed": False,

        "web_support_allowed": True,
        "web_support_preferred": False,
        "web_support_required": False,
        "web_support_used": False,
        "web_support_confidence": 0.0,

        "internet_answer_possible": False,
        "internet_answer_missing": False,

        "web_support_as_fallback": True,
        "web_support_should_not_dominate": True,

        "understands_user_direction": False,
        "understands_user_goal": False,
        "protects_user_trajectory": False,

        "user_leads_direction": False,
        "assistant_should_follow": False,
        "assistant_should_slow_down": False,

        "search_capabilities": True,

        "capability_map":
            capability_map,

        "direction_hypothesis": {

            "enabled": True,

            "confidence": 0.0,

            "direction": None,

            "suggest_path": False
        }
    }

    _increase(
        cognition,
        "execution_pressure",
        semantic.get(
            "execution_pressure",
            0.0
        )
    )

    cognition[
        "unresolved_intent"
    ] = semantic.get(
        "unresolved_intent",
        True
    )

    # =================================================
    # 🔥 ACTION SIGNALS
    # =====================================================

    if _contains_any(
        t,
        ACTION_WORDS
    ):

        _increase(
            cognition,
            "wants_action",
            0.8
        )

        _increase(
            cognition,
            "wants_result",
            0.8
        )

        _increase(
            cognition,
            "execution_pressure",
            0.55
        )

        _increase(
            cognition,
            "result_pressure",
            0.6
        )

        _increase(
            cognition,
            "execution_urgency",
            0.45
        )

    # =================================================
    # 🔥 VISUAL SIGNALS
    # =====================================================

    if _contains_any(
        t,
        VISUAL_WORDS
    ):

        _increase(
            cognition,
            "wants_visual",
            0.9
        )

        cognition[
            "prefer_visual"
        ] = True

        cognition[
            "needs_examples"
        ] = True

    # =================================================
    # 🔥 DIALOG SIGNALS
    # =====================================================

    if _contains_any(
        t,
        DIALOG_WORDS
    ):

        _increase(
            cognition,
            "wants_dialog",
            0.7
        )

        cognition[
            "prefer_detailed_answer"
        ] = True

    # =================================================
    # 🔥 HELP SIGNALS
    # =====================================================

    if _contains_any(
        t,
        HELP_WORDS
    ):

        _increase(
            cognition,
            "wants_help",
            0.85
        )

        cognition[
            "needs_guidance"
        ] = True

        cognition[
            "should_offer_direction"
        ] = True

        cognition[
            "should_proactively_help"
        ] = True

    # =================================================
    # 🔥 CONFUSION SIGNALS
    # =====================================================

    if _contains_any(
        t,
        CONFUSION_WORDS
    ):

        _increase(
            cognition,
            "is_confused",
            0.8
        )

        cognition[
            "needs_guidance"
        ] = True

        cognition[
            "needs_examples"
        ] = True

        cognition[
            "prefer_visual"
        ] = True

    # =================================================
    # 🔥 FRUSTRATION SIGNALS
    # =====================================================

    if _contains_any(
        t,
        FRUSTRATION_WORDS
    ):

        _increase(
            cognition,
            "is_frustrated",
            0.85
        )

        _increase(
            cognition,
            "dialog_fatigue",
            0.7
        )

        _increase(
            cognition,
            "signal_overload",
            0.5
        )

    # =================================================
    # 🔥 LEADERSHIP DETECTION
    # =====================================================

    if _contains_any(
        t,
        LEADERSHIP_WORDS
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
            "assistant_restraint"
        ] = 0.7

        cognition[
            "prefer_execution"
        ] = False

    # =================================================
    # 🔥 EXPLORATION MODE
    # =====================================================

    if _contains_any(
        t,
        EXPLORATION_WORDS
    ):

        cognition[
            "exploration_mode"
        ] = True

        cognition[
            "inspiration_mode"
        ] = True

        cognition[
            "needs_examples"
        ] = True

        cognition[
            "generation_should_wait"
        ] = True

        _increase(
            cognition,
            "human_psychology_weight",
            0.2
        )

    # =================================================
    # 🌐 WEB / REALTIME SUPPORT
    # =====================================================

    if _contains_any(
        t,
        TRAVEL_WORDS
    ):

        cognition[
            "internet_context_needed"
        ] = True

        cognition[
            "travel_context_needed"
        ] = True

        cognition[
            "web_support_preferred"
        ] = True

        cognition[
            "internet_answer_possible"
        ] = True

        cognition[
            "web_support_confidence"
        ] = 0.72

        cognition[
            "needs_guidance"
        ] = True

        cognition[
            "should_offer_direction"
        ] = True

    # =================================================
    # 🔥 DIALOG FATIGUE
    # =====================================================

    if len(dialog) >= 10:

        _increase(
            cognition,
            "dialog_fatigue",
            0.35
        )

    if len(dialog) >= 16:

        _increase(
            cognition,
            "signal_overload",
            0.4
        )

    cognition = stabilize_trajectory(
        cognition,
        active_flow
    )

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

            _increase(
                cognition,
                "dialog_fatigue",
                0.25
            )

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
    # 🔥 EXECUTION MODE
    # =====================================================

    if (
        cognition[
            "execution_pressure"
        ] >= 0.72
        and not cognition[
            "exploration_mode"
        ]
    ):

        cognition[
            "prefer_execution"
        ] = True

        _increase(
            cognition,
            "execution_confidence",
            0.7
        )

    # =================================================
    # 🔥 WEB FALLBACK STABILIZATION
    # =====================================================

    if (

        cognition.get(
            "internet_context_needed"
        )

        and not cognition.get(
            "prefer_visual"
        )

        and not cognition.get(
            "exploration_mode"
        )
    ):

        cognition[
            "web_support_required"
        ] = True

        cognition[
            "internet_answer_possible"
        ] = True

        cognition[
            "generation_should_wait"
        ] = True

        cognition[
            "prefer_execution"
        ] = False

        _decrease(
            cognition,
            "execution_pressure",
            0.15
        )

        _decrease(
            cognition,
            "wants_visual",
            0.25
        )

        _decrease(
            cognition,
            "signal_overload",
            0.1
        )

    # =================================================
    # 🔥 UNDERSTANDING GOAL
    # =====================================================

    if (

        cognition[
            "wants_action"
        ] >= 0.5

        or cognition[
            "wants_help"
        ] >= 0.5

        or cognition[
            "wants_visual"
        ] >= 0.5

        or cognition[
            "internet_context_needed"
        ]
    ):

        cognition[
            "understands_user_goal"
        ] = True

    # =================================================
    # 🔥 EXECUTION CONFIDENCE RESTORE
    # =====================================================

    if (
        cognition.get(
            "understands_user_goal"
        )
        and not cognition.get(
            "needs_clarification"
        )
    ):

        cognition[
            "prefer_execution"
        ] = True

        cognition[
            "assistant_should_follow"
        ] = True

        cognition[
            "should_offer_direction"
        ] = False

        cognition[
            "execution_confidence"
        ] = max(
            cognition.get(
                "execution_confidence",
                0.0
            ),
            0.82
        )

        cognition[
            "assistant_restraint"
        ] = min(
            cognition.get(
                "assistant_restraint",
                0.0
            ),
            0.25
        )

        _decrease(
            cognition,
            "internal_noise",
            0.2
        )

        _decrease(
            cognition,
            "signal_overload",
            0.15
        )

    # =================================================
    # 🔥 CLARIFICATION
    # =====================================================

    if semantic.get(
        "ambiguity_level",
        0.0
    ) >= 0.7:

        cognition[
            "needs_clarification"
        ] = True

    cognition = apply_response_economy(
        cognition
    )

    cognition = stabilize_cognition_state(
        cognition
    )

    # =================================================
    # 🔥 DIRECTION HYPOTHESIS
    # =====================================================

    hypothesis = cognition[
        "direction_hypothesis"
    ]

    if cognition[
        "internet_context_needed"
    ]:

        hypothesis[
            "direction"
        ] = "web_support"

        hypothesis[
            "confidence"
        ] = 0.82

        hypothesis[
            "suggest_path"
        ] = True

    elif cognition[
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
    # 🔥 FINAL NORMALIZATION
    # =====================================================

    for key, value in cognition.items():

        if isinstance(
            value,
            float
        ):

            cognition[key] = _clamp(
                value
            )

    return cognition
