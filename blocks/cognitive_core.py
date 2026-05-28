# =========================================================
# 🧠 APRIL COGNITION STABILIZATION CORE
# =========================================================

"""
APRIL COGNITION STABILIZATION CORE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ROLE IN APRIL:
This file is the cognitive interpretation
and behavioral stabilization layer of April.

This helper core analyzes:
- user intent
- dialog continuity
- user pressure
- trajectory state
- render needs
- human interaction flow

It helps Executor understand:
HOW April should think,
focus,
continue,
and respond.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 WHAT THIS FILE IS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file IS:
- cognition stabilization layer
- continuity analyzer
- dialog flow analyzer
- render intent detector
- human interaction analyzer
- trajectory stabilization helper
- behavioral cognition helper

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 WHAT THIS FILE IS NOT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file is NOT:
- Executor
- orchestration engine
- router
- frontend renderer
- governance system
- memory authority
- personality narrator
- Telegram logic
- response formatter

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 APRIL ARCHITECTURE POSITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BotRoot
 ↓
Executor
 ↓
Cognition Stabilization Core (THIS FILE)
 ↓
Execution Rooms

Executor routes.
This file helps Executor understand:
- user state
- continuity
- trajectory
- render needs
- behavioral pacing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 GOLDEN MACHINE CHANNEL RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file uses TWO isolated channels.

1. COGNITION TASK CHANNEL
Executor → Cognition Core

2. COGNITION RESPONSE CHANNEL
Cognition Core → Executor

Human-facing responses NEVER mix
with cognition analysis structures.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 GOLDEN APRIL RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. continuity before fragmentation
2. cognition before generation
3. renderer before heavy visuals
4. human understanding before performance
5. dialog trajectory protection
6. anti-chaos cognition
7. no internal leakage
8. no cognitive narration
9. no duplicated orchestration
10. Web-space first

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 IMPORTANT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DO NOT RE-ADD:
- Telegram logic
- frontend rendering
- orchestration duplication
- governance duplication
- personality narration
- analytics logic
- routing logic
- execution logic

This file must remain:
- cognitive
- lightweight
- continuity-focused
- Executor-compatible
- behaviorally stable
"""

# =========================================================
# 🧠 IMPORTS
# =========================================================

from blocks.visual_memory_library import (
    build_visual_memory_response
)

# =========================================================
# 🧠 MACHINE CHANNELS
# =========================================================

COGNITION_TASK_CHANNEL = {

    "channel":
        "cognition_machine_task_channel",

    "isolated":
        True
}

COGNITION_RESPONSE_CHANNEL = {

    "channel":
        "cognition_machine_response_channel",

    "isolated":
        True
}

# =========================================================
# 🧠 SAFE HELPERS
# =========================================================

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

# =========================================================
# 🧠 SEMANTIC SIGNALS
# =========================================================

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
    "сцена"
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

# =========================================================
# 🧠 META AI SUPPRESSION
# =========================================================

def detect_meta_ai_behavior(
    text: str
):

    """
    Prevents meta-AI loops
    and system-trigger behavior.
    """

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

# =========================================================
# 🧠 DIALOG CONTINUITY
# =========================================================

def build_dialog_continuity(
    dialog: list
):

    """
    Builds lightweight continuity state
    for Executor trajectory stabilization.
    """

    continuity = {

        "active_topics": [],
        "unresolved_questions": [],
        "recent_user_requests": [],

        "conversation_stage":
            "active",

        "multi_topic":
            False,

        "user_waiting_answer":
            False,

        "dialog_momentum":
            0.0,

        "human_depth":
            0.0,

        "user_uncertainty":
            0.0,

        "user_reflection":
            False
    }

    if not dialog:
        return continuity

    recent_messages = dialog[-12:]

    user_messages = [

        x for x in recent_messages
        if x.get("role") == "user"
    ]

    if len(user_messages) >= 2:

        continuity[
            "multi_topic"
        ] = True

    recent_requests = []
    unresolved = []

    for message in user_messages[-5:]:

        content = str(
            message.get(
                "content",
                ""
            )
        ).strip()

        if not content:
            continue

        recent_requests.append(
            content[:280]
        )

        lowered = content.lower()

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
        # 🧠 HUMAN DEPTH
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

    return continuity

# =========================================================
# 🧠 TRAJECTORY STABILIZATION
# =========================================================

def stabilize_trajectory(
    cognition: dict,
    active_flow
):

    """
    Preserves user trajectory continuity.
    """

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

    _increase(
        cognition,
        "trajectory_confidence",
        0.3
    )

    return cognition

# =========================================================
# 🧠 RENDER DETECTION
# =========================================================

def detect_render_intent(
    text: str
):

    """
    Detects renderer-space requests.
    """

    t = text.lower()

    render_score = 0.0

    if _contains_any(
        t,
        RENDER_WORDS
    ):

        render_score += 0.85

    return {

        "render_score":
            _clamp(render_score),

        "prefer_renderer":
            render_score >= 0.6
    }

# =========================================================
# 🧠 VISUAL MODE
# =========================================================

def build_visual_mode(
    cognition: dict,
    visual_memory: dict
):

    """
    Lightweight visual continuity mode.
    """

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

# =========================================================
# 🧠 DIALOG STABILIZATION
# =========================================================

def stabilize_dialog_behavior(
    cognition: dict
):

    """
    Prevents:
    - robotic responses
    - meta leakage
    - personality overflow
    - fragmented behavior
    """

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
            "response_should_focus_on_goal"
        ] = True

        cognition[
            "response_should_stay_grounded"
        ] = True

        cognition[
            "response_should_feel_human"
        ] = True

        cognition[
            "response_should_flow_naturally"
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

# =========================================================
# 🧠 COGNITION STABILITY
# =========================================================

def stabilize_cognition_state(
    cognition: dict
):

    """
    Reduces cognition chaos
    during long dialog flows.
    """

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
    ] = _clamp(stability)

    cognition[
        "internal_noise"
    ] = _clamp(noise)

    cognition[
        "signal_overload"
    ] = _clamp(overload)

    return cognition

# =========================================================
# 🧠 CORE ANALYZER
# =========================================================

def analyze_cognition(

    text: str,
    state: dict,
    semantic: dict,
    reasoning: dict
):

    """
    Main cognition analysis layer.

    Executor uses this helper to understand:
    - user state
    - continuity
    - render needs
    - pacing
    - trajectory
    """

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

        # =================================================
        # 🧠 USER INTENT
        # =====================================================

        "wants_action":
            0.0,

        "wants_help":
            0.0,

        "wants_visual":
            0.0,

        "wants_dialog":
            0.0,

        # =================================================
        # 🧠 STABILITY
        # =====================================================

        "execution_pressure":
            0.0,

        "scene_stability":
            0.72,

        "internal_noise":
            0.08,

        "signal_overload":
            0.05,

        # =================================================
        # 🧠 EXECUTION
        # =====================================================

        "prefer_execution":
            False,

        "prefer_visual":
            False,

        "prefer_renderer":
            False,

        "renderer_space_active":
            False,

        # =================================================
        # 🧠 CONTINUITY
        # =====================================================

        "needs_guidance":
            False,

        "needs_continuation":
            False,

        "trajectory_locked":
            False,

        "trajectory_confidence":
            0.0,

        "dialogue_still_alive":
            True,

        # =================================================
        # 🧠 HUMAN FLOW
        # =====================================================

        "response_should_feel_human":
            False,

        "response_should_flow_naturally":
            False,

        "response_should_continue_naturally":
            False,

        "response_should_reduce_robotic_tone":
            True,

        # =================================================
        # 🧠 DIALOG
        # =====================================================

        "tracks_multiple_topics":
            False,

        "should_answer_in_order":
            False,

        "preserve_question_order":
            False,

        "avoid_topic_loss":
            True,

        # =================================================
        # 🧠 MEMORY
        # =====================================================

        "continuity_state":
            continuity,

        "visual_memory":
            visual_memory,

        "visual_mode":
            visual_mode,

        # =================================================
        # 🧠 CHANNELS
        # =====================================================

        "machine_task_channel":
            COGNITION_TASK_CHANNEL,

        "machine_response_channel":
            COGNITION_RESPONSE_CHANNEL
    }

    # =====================================================
    # 🧠 META SUPPRESSION
    # =====================================================

    if detect_meta_ai_behavior(t):

        cognition[
            "prefer_execution"
        ] = True

        cognition[
            "assistant_restraint"
        ] = 0.85

        _decrease(
            cognition,
            "internal_noise",
            0.25
        )

    # =====================================================
    # 🧠 ACTION UNDERSTANDING
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

    # =====================================================
    # 🧠 HELP UNDERSTANDING
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

    # =====================================================
    # 🧠 VISUAL UNDERSTANDING
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

    # =====================================================
    # 🧠 RENDER UNDERSTANDING
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

    # =====================================================
    # 🧠 WEB CONTEXT
    # =====================================================

    if _contains_any(
        t,
        TRAVEL_WORDS
    ):

        cognition[
            "internet_context_needed"
        ] = True

    # =====================================================
    # 🧠 CONTINUITY
    # =====================================================

    cognition = stabilize_trajectory(
        cognition,
        active_flow
    )

    # =====================================================
    # 🧠 REASONING INHERITANCE
    # =====================================================

    if reasoning:

        if reasoning.get(
            "continuation"
        ):

            cognition[
                "needs_continuation"
            ] = True

        if reasoning.get(
            "user_waiting_action"
        ):

            cognition[
                "prefer_execution"
            ] = True

    # =====================================================
    # 🧠 GOAL UNDERSTANDING
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

    ):

        cognition[
            "understands_user_goal"
        ] = True

    # =====================================================
    # 🧠 STABILIZATION
    # =====================================================

    cognition = stabilize_dialog_behavior(
        cognition
    )

    cognition = stabilize_cognition_state(
        cognition
    )

    # =====================================================
    # 🧠 FINAL NORMALIZATION
    # =====================================================

    for key, value in cognition.items():

        if isinstance(
            value,
            float
        ):

            cognition[key] = _clamp(
                value
            )

    # =====================================================
    # 🧠 FINAL
    # =====================================================

    return cognition
