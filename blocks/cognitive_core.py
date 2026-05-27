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
# 🔥 CONTINUITY HELPERS
# =====================================================

def build_dialog_continuity(
    dialog: list
):

    continuity = {

        "active_topics": [],
        "unresolved_questions": [],
        "recent_user_requests": [],
        "conversation_stage": "active",

        "multi_topic": False,
        "user_waiting_answer": False,

        # 🔥 HUMAN CONTINUITY
        "dialog_momentum": 0.0,
        "human_depth": 0.0,
        "user_uncertainty": 0.0,
        "user_reflection": False,

        # 🔥 SCENE CONTINUITY
        "scene_continuation_possible": False,
        "recent_visual_reference": False,
        "soft_scene_memory": [],
        "continuation_priority": 0.0,
        "dialogue_should_continue": False,
        "scene_transition_detected": False,
        "return_to_previous_topic_possible": False
    }

    if not dialog:
        return continuity

    recent_messages = dialog[-15:]

    user_messages = [

        x for x in recent_messages
        if x.get("role") == "user"
    ]

    assistant_messages = [

        x for x in recent_messages
        if x.get("role") == "assistant"
    ]

    if len(user_messages) >= 2:

        continuity[
            "multi_topic"
        ] = True

    recent_requests = []
    unresolved = []

    visual_words = [

        "скрин",
        "скриншот",
        "фото",
        "картинка",
        "изображение",
        "на фото",
        "на скрине",
        "это",
        "тут",
        "здесь",
        "смотри"
    ]

    continuation_words = [

        "а тут",
        "а здесь",
        "теперь",
        "еще",
        "сейчас",
        "вот",
        "дальше",
        "продолжение",
        "снова",
        "еще один"
    ]

    soft_scene_memory = []

    for message in user_messages[-6:]:

        content = str(
            message.get(
                "content",
                ""
            )
        ).strip()

        if not content:
            continue

        lowered = content.lower()

        recent_requests.append(
            content[:280]
        )

        if (
            "?" in content
            or "как" in lowered
            or "почему" in lowered
            or "что" in lowered
        ):

            unresolved.append(
                content[:280]
            )

        # =================================================
        # 🔥 HUMAN UNDERSTANDING
        # =====================================================

        if (
            "не понимаю" in lowered
            or "сложно" in lowered
            or "запутался" in lowered
            or "не уверен" in lowered
        ):

            continuity[
                "user_uncertainty"
            ] += 0.25

        if (
            "думаю" in lowered
            or "мне кажется" in lowered
            or "как думаешь" in lowered
        ):

            continuity[
                "user_reflection"
            ] = True

            continuity[
                "human_depth"
            ] += 0.2

        continuity[
            "dialog_momentum"
        ] += 0.12

        # =================================================
        # 🔥 VISUAL CONTINUITY
        # =====================================================

        if _contains_any(
            lowered,
            visual_words
        ):

            continuity[
                "recent_visual_reference"
            ] = True

            continuity[
                "scene_continuation_possible"
            ] = True

            continuity[
                "dialogue_should_continue"
            ] = True

            continuity[
                "continuation_priority"
            ] += 0.22

            soft_scene_memory.append(
                content[:120]
            )

        if _contains_any(
            lowered,
            continuation_words
        ):

            continuity[
                "scene_continuation_possible"
            ] = True

            continuity[
                "dialogue_should_continue"
            ] = True

            continuity[
                "continuation_priority"
            ] += 0.18

    # =====================================================
    # 🔥 SOFT RETURN TO PREVIOUS TOPIC
    # =====================================================

    if len(recent_requests) >= 3:

        continuity[
            "return_to_previous_topic_possible"
        ] = True

    continuity[
        "soft_scene_memory"
    ] = soft_scene_memory[-5:]

    continuity[
        "recent_user_requests"
    ] = recent_requests[-5:]

    continuity[
        "unresolved_questions"
    ] = unresolved[-5:]

    if unresolved:

        continuity[
            "user_waiting_answer"
        ] = True

    continuity[
        "dialog_momentum"
    ] = _clamp(
        continuity[
            "dialog_momentum"
        ]
    )

    continuity[
        "human_depth"
    ] = _clamp(
        continuity[
            "human_depth"
        ]
    )

    continuity[
        "user_uncertainty"
    ] = _clamp(
        continuity[
            "user_uncertainty"
        ]
    )

    continuity[
        "continuation_priority"
    ] = _clamp(
        continuity[
            "continuation_priority"
        ]
    )

    return continuity


def stabilize_multi_topic_dialog(
    cognition: dict,
    continuity: dict
):

    if continuity.get(
        "multi_topic"
    ):

        cognition[
            "tracks_multiple_topics"
        ] = True

        cognition[
            "should_answer_in_order"
        ] = True

        cognition[
            "preserve_question_order"
        ] = True

        cognition[
            "avoid_topic_loss"
        ] = True

        cognition[
            "should_merge_contexts"
        ] = True

        cognition[
            "dialogue_still_alive"
        ] = True

        _increase(
            cognition,
            "trajectory_confidence",
            0.25
        )

    if continuity.get(
        "user_waiting_answer"
    ):

        cognition[
            "user_waiting_answer"
        ] = True

        cognition[
            "prefer_execution"
        ] = True

        cognition[
            "response_should_focus_on_goal"
        ] = True

        _increase(
            cognition,
            "execution_confidence",
            0.2
        )

    # =================================================
    # 🔥 HUMAN CONTINUITY
    # =====================================================

    if continuity.get(
        "human_depth",
        0.0
    ) >= 0.2:

        cognition[
            "response_should_feel_human"
        ] = True

        cognition[
            "response_should_continue_naturally"
        ] = True

        cognition[
            "should_preserve_dialog_momentum"
        ] = True

    if continuity.get(
        "user_uncertainty",
        0.0
    ) >= 0.2:

        cognition[
            "should_reduce_pressure"
        ] = True

        cognition[
            "should_help_calmly"
        ] = True

        cognition[
            "response_should_feel_safe"
        ] = True

    # =================================================
    # 🔥 SCENE CONTINUITY
    # =====================================================

    if continuity.get(
        "scene_continuation_possible"
    ):

        cognition[
            "needs_continuation"
        ] = True

        cognition[
            "dialogue_still_alive"
        ] = True

        cognition[
            "response_should_continue_naturally"
        ] = True

        cognition[
            "response_should_preserve_context"
        ] = True

        cognition[
            "response_should_not_restart_scene"
        ] = True

        cognition[
            "response_should_respect_previous_scene"
        ] = True

        cognition[
            "scene_memory_active"
        ] = True

        cognition[
            "should_preserve_scene_direction"
        ] = True

        cognition[
            "soft_scene_continuation"
        ] = True

        cognition[
            "avoid_day_surka_behavior"
        ] = True

        _increase(
            cognition,
            "trajectory_confidence",
            0.3
        )

    return cognition


# =====================================================
# 🔥 SAFE DIALOG HELPERS
# =====================================================

def detect_meta_ai_behavior(
    text: str
):

    t = (text or "").lower()

    meta_words = [

        "system prompt",
        "prompt leak",
        "roleplay assistant",
        "ты ии",
        "как chatgpt"
    ]

    return any(
        x in t
        for x in meta_words
    )


def stabilize_dialog_behavior(
    cognition: dict
):

    if cognition.get(
        "understands_user_goal"
    ):

        cognition[
            "prefer_execution"
        ] = True

        cognition[
            "assistant_should_follow"
        ] = True

        cognition[
            "avoid_meta_behavior"
        ] = True

        cognition[
            "avoid_personality_overflow"
        ] = True

        cognition[
            "avoid_system_prompt_leakage"
        ] = True

        cognition[
            "avoid_self_reference"
        ] = True

        cognition[
            "avoid_ai_monologue"
        ] = True

        cognition[
            "prefer_user_request_over_style"
        ] = True

        cognition[
            "response_should_focus_on_goal"
        ] = True

        cognition[
            "response_should_avoid_internal_language"
        ] = True

        cognition[
            "response_should_stay_grounded"
        ] = True

        cognition[
            "assistant_presence"
        ] = min(
            cognition.get(
                "assistant_presence",
                1.0
            ),
            0.72
        )

        cognition[
            "assistant_restraint"
        ] = max(
            cognition.get(
                "assistant_restraint",
                0.0
            ),
            0.35
        )

        # =================================================
        # 🔥 NATURAL HUMAN FLOW
        # =====================================================

        cognition[
            "response_should_feel_alive"
        ] = True

        cognition[
            "response_should_flow_naturally"
        ] = True

        cognition[
            "response_should_maintain_continuity"
        ] = True

        cognition[
            "response_should_feel_human"
        ] = True

        cognition[
            "response_should_help_gently"
        ] = True

        cognition[
            "response_should_reduce_robotic_tone"
        ] = True

        cognition[
            "response_should_adapt_pacing"
        ] = True

        cognition[
            "response_should_respect_user_state"
        ] = True

        cognition[
            "response_should_continue_scene"
        ] = True

        cognition[
            "response_should_detect_scene_shift"
        ] = True

        cognition[
            "response_should_support_return_to_topic"
        ] = True

        cognition[
            "response_should_keep_soft_memory"
        ] = True

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

    return cognition


# =====================================================
# 🔥 SEMANTIC SIGNALS
# =====================================================

ACTION_WORDS = [

    "сделай",
    "создай",
    "исправь",
    "апгрейд",
    "улучши",
    "покажи"
]

VISUAL_WORDS = [

    "картинка",
    "схема",
    "график",
    "формула",
    "таблица",
    "пространство",
    "сцена",
    "скрин",
    "скриншот",
    "фото"
]

HELP_WORDS = [

    "помоги",
    "подскажи",
    "не понимаю",
    "объясни"
]

RENDER_WORDS = [

    "график",
    "формула",
    "таблица",
    "renderer",
    "scene",
    "canvas"
]

TRAVEL_WORDS = [

    "где находится",
    "как добраться",
    "погода",
    "карта",
    "рейс"
]


# =====================================================
# 🔥 RENDER DETECTION
# =====================================================

def detect_render_intent(
    text: str
):

    t = text.lower()

    render_score = 0.0

    if _contains_any(
        t,
        RENDER_WORDS
    ):

        render_score += 0.85

    return {

        "render_score": _clamp(
            render_score
        ),

        "prefer_renderer":
            render_score >= 0.6
    }


# =====================================================
# 🔥 COGNITION STABILITY
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

    active_flow_strength = cognition.get(
        "active_flow_strength",
        0.0
    )

    if active_flow_strength >= 0.5:

        stability += 0.25

        noise -= 0.2

        overload -= 0.15

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
# 🔥 VISUAL MODE
# =====================================================

def build_visual_mode(
    cognition: dict,
    visual_memory: dict
):

    mode = {

        "enabled": False,
        "reference_priority": False,
        "lightweight": False,
        "renderer_mode": False
    }

    atmosphere = visual_memory.get(
        "atmosphere"
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

    return mode


# =====================================================
# 🔥 TRAJECTORY
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
        "active_flow_strength"
    ] = 0.85

    cognition[
        "response_should_continue_naturally"
    ] = True

    cognition[
        "response_should_preserve_context"
    ] = True

    cognition[
        "response_should_continue_scene"
    ] = True

    cognition[
        "response_should_not_restart_scene"
    ] = True

    _increase(
        cognition,
        "trajectory_confidence",
        0.3
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

    continuity = build_dialog_continuity(
        dialog
    )

    visual_memory = build_visual_memory_response(
        text
    )

    visual_mode = build_visual_mode(
        {},
        visual_memory
    )

    render_analysis = detect_render_intent(
        t
    )

    cognition = {

        "wants_action": 0.0,
        "wants_help": 0.0,
        "wants_visual": 0.0,
        "wants_dialog": 0.0,

        "execution_pressure": 0.0,

        "scene_stability": 0.72,
        "internal_noise": 0.08,
        "signal_overload": 0.05,

        "prefer_execution": False,
        "prefer_visual": False,
        "prefer_renderer": False,

        "renderer_space_active": False,

        "needs_guidance": False,
        "needs_examples": False,
        "needs_continuation": False,

        "trajectory_locked": False,
        "trajectory_confidence": 0.0,

        "dialogue_still_alive": True,

        "assistant_presence": 0.72,
        "assistant_restraint": 0.4,

        "understands_user_goal": False,
        "assistant_should_follow": False,

        "response_should_focus_on_goal": True,
        "response_should_stay_grounded": True,

        # 🔥 HUMAN CONTINUITY
        "response_should_feel_alive": False,
        "response_should_flow_naturally": False,
        "response_should_feel_human": False,
        "response_should_continue_naturally": False,
        "response_should_help_gently": False,
        "response_should_reduce_robotic_tone": True,
        "response_should_adapt_pacing": False,
        "response_should_preserve_context": False,

        # 🔥 SCENE CONTINUITY
        "response_should_continue_scene": False,
        "response_should_not_restart_scene": False,
        "response_should_support_return_to_topic": False,
        "response_should_detect_scene_shift": True,
        "response_should_keep_soft_memory": True,
        "soft_scene_continuation": False,

        "tracks_multiple_topics": False,
        "should_answer_in_order": False,
        "preserve_question_order": False,
        "avoid_topic_loss": True,

        "user_waiting_answer": False,

        "continuity_state":
            continuity,

        "visual_memory":
            visual_memory,

        "visual_mode":
            visual_mode
    }

    # =================================================
    # 🔥 META SUPPRESSION
    # =====================================================

    if detect_meta_ai_behavior(t):

        cognition[
            "assistant_restraint"
        ] = 0.85

        cognition[
            "prefer_execution"
        ] = True

        _decrease(
            cognition,
            "internal_noise",
            0.25
        )

    # =================================================
    # 🔥 ACTION UNDERSTANDING
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

        cognition[
            "prefer_execution"
        ] = True

    # =================================================
    # 🔥 HELP UNDERSTANDING
    # =====================================================

    if _contains_any(
        t,
        HELP_WORDS
    ):

        _increase(
            cognition,
            "wants_help",
            0.8
        )

        cognition[
            "needs_guidance"
        ] = True

        cognition[
            "response_should_help_gently"
        ] = True

    # =================================================
    # 🔥 VISUAL UNDERSTANDING
    # =====================================================

    if _contains_any(
        t,
        VISUAL_WORDS
    ):

        _increase(
            cognition,
            "wants_visual",
            0.8
        )

        cognition[
            "prefer_visual"
        ] = True

    # =================================================
    # 🔥 RENDER UNDERSTANDING
    # =====================================================

    if render_analysis.get(
        "prefer_renderer"
    ):

        cognition[
            "prefer_renderer"
        ] = True

        cognition[
            "renderer_space_active"
        ] = True

        cognition[
            "prefer_visual"
        ] = False

    # =================================================
    # 🔥 WEB CONTEXT
    # =====================================================

    if _contains_any(
        t,
        TRAVEL_WORDS
    ):

        cognition[
            "internet_context_needed"
        ] = True

    # =================================================
    # 🔥 CONTINUITY
    # =====================================================

    cognition = stabilize_trajectory(
        cognition,
        active_flow
    )

    cognition = stabilize_multi_topic_dialog(
        cognition,
        continuity
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

            cognition[
                "response_should_continue_scene"
            ] = True

        if reasoning.get(
            "user_waiting_action"
        ):

            cognition[
                "prefer_execution"
            ] = True

    # =================================================
    # 🔥 USER GOAL UNDERSTANDING
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
            "user_waiting_answer"
        ]
    ):

        cognition[
            "understands_user_goal"
        ] = True

    cognition = stabilize_dialog_behavior(
        cognition
    )

    cognition = stabilize_cognition_state(
        cognition
    )

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
