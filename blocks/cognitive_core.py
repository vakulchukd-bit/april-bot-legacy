# =========================================================
# 🧠 APRIL COGNITION STABILIZATION CORE
# =========================================================

"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APRIL FILE ID
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

APRIL_FILE_ID:
APRIL_COGNITION_STABILIZATION_CORE

ROLE:
COGNITION_AND_TRAJECTORY_STABILIZER

ROOM:
COGNITION_ROOM

INPUT:
USER_TEXT
STATE
SEMANTIC_PAYLOAD
REASONING_PAYLOAD
ACTIVE_FLOW
VISUAL_MEMORY

OUTPUT:
COGNITION_STATE
TRAJECTORY_ANALYSIS
CONTINUITY_ANALYSIS
RENDER_INTENT_ANALYSIS
ANALYZER_TELEMETRY

DEPENDENCIES:
EXECUTOR
VISUAL_MEMORY_LIBRARY
CONTINUITY_SYSTEM
ANALYZER_SYSTEM

CRITICAL:
TRUE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 GOLDEN RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file NEVER:
- orchestrates execution
- routes providers
- renders frontend
- formats responses

This file ONLY:
- stabilizes cognition
- analyzes trajectory
- protects continuity
- detects render intent
- stabilizes dialog behavior

This file ALSO:
- builds dynamic focus
- tracks open loops
- analyzes memory relevance
- stabilizes user goals
- prepares memory signals
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
# 🔥 APRIL TRACE LOGS
# =========================================================

def APRIL_LOG_IN(
    room,
    metadata=None
):

    try:

        print({

            "type":
                "APRIL_LOG_IN",

            "room":
                room,

            "file":
                "APRIL_COGNITION_STABILIZATION_CORE",

            "metadata":
                metadata or {}
        })

    except Exception:
        pass


def APRIL_LOG_OUT(
    room,
    metadata=None
):

    try:

        print({

            "type":
                "APRIL_LOG_OUT",

            "room":
                room,

            "file":
                "APRIL_COGNITION_STABILIZATION_CORE",

            "metadata":
                metadata or {}
        })

    except Exception:
        pass

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
# 🧠 ANALYZER TELEMETRY
# =========================================================

def build_cognition_telemetry():

    APRIL_LOG_IN(

        "COGNITION_ROOM",

        {
            "action":
                "build_cognition_telemetry"
        }
    )

    payload = {

        "file_id":
            "APRIL_COGNITION_STABILIZATION_CORE",

        "room":
            "COGNITION_ROOM",

        "continuity_safe":
            True,

        "trajectory_tracking":
            True,

        "render_detection":
            True,

        "dialog_analysis":
            True,

        "executor_connected":
            True
    }

    APRIL_LOG_OUT(

        "COGNITION_ROOM",

        {
            "telemetry":
                "ready"
        }
    )

    return payload

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

    APRIL_LOG_IN(

        "COGNITION_ROOM",

        {
            "action":
                "detect_meta_ai_behavior"
        }
    )

    t = (text or "").lower()

    meta_words = [

        "system prompt",
        "prompt leak",
        "roleplay assistant",
        "ты ии",
        "как chatgpt"
    ]

    result = any(
        x in t
        for x in meta_words
    )

    APRIL_LOG_OUT(

        "COGNITION_ROOM",

        {
            "meta_detected":
                result
        }
    )

    return result

# =========================================================
# 🧠 DIALOG CONTINUITY
# =========================================================

def build_dialog_continuity(
    dialog: list
):

    APRIL_LOG_IN(

        "COGNITION_ROOM",

        {
            "action":
                "build_dialog_continuity"
        }
    )

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

        APRIL_LOG_OUT(

            "COGNITION_ROOM",

            {
                "continuity":
                    "empty_dialog"
            }
        )

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

    APRIL_LOG_OUT(

        "COGNITION_ROOM",

        {
            "continuity":
                "built"
        }
    )

    return continuity

# =========================================================
# 🧠 TRAJECTORY STABILIZATION
# =========================================================

def stabilize_trajectory(
    cognition: dict,
    active_flow
):

    APRIL_LOG_IN(

        "COGNITION_ROOM",

        {
            "action":
                "stabilize_trajectory"
        }
    )

    if not active_flow:

        APRIL_LOG_OUT(

            "COGNITION_ROOM",

            {
                "trajectory":
                    "inactive"
            }
        )

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

    APRIL_LOG_OUT(

        "COGNITION_ROOM",

        {
            "trajectory":
                "stabilized"
        }
    )

    return cognition

# =========================================================
# 🧠 RENDER DETECTION
# =========================================================

def detect_render_intent(
    text: str
):

    APRIL_LOG_IN(

        "COGNITION_ROOM",

        {
            "action":
                "detect_render_intent"
        }
    )

    t = text.lower()

    render_score = 0.0

    if _contains_any(
        t,
        RENDER_WORDS
    ):

        render_score += 0.85

    payload = {

        "render_score":
            _clamp(render_score),

        "prefer_renderer":
            render_score >= 0.6
    }

    APRIL_LOG_OUT(

        "COGNITION_ROOM",

        {
            "render_score":
                payload["render_score"]
        }
    )

    return payload

# =========================================================
# 🧠 VISUAL MODE
# =========================================================

def build_visual_mode(
    cognition: dict,
    visual_memory: dict
):

    APRIL_LOG_IN(

        "COGNITION_ROOM",

        {
            "action":
                "build_visual_mode"
        }
    )

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

    APRIL_LOG_OUT(

        "COGNITION_ROOM",

        {
            "visual_mode":
                mode["enabled"]
        }
    )

    return mode

# =========================================================
# 🧠 DIALOG STABILIZATION
# =========================================================

def stabilize_dialog_behavior(
    cognition: dict
):

    APRIL_LOG_IN(

        "COGNITION_ROOM",

        {
            "action":
                "stabilize_dialog_behavior"
        }
    )

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

    APRIL_LOG_OUT(

        "COGNITION_ROOM",

        {
            "dialog":
                "stabilized"
        }
    )

    return cognition

# =========================================================
# 🧠 COGNITION STABILITY
# =========================================================

def stabilize_cognition_state(
    cognition: dict
):

    APRIL_LOG_IN(

        "COGNITION_ROOM",

        {
            "action":
                "stabilize_cognition_state"
        }
    )

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

    APRIL_LOG_OUT(

        "COGNITION_ROOM",

        {
            "stability":
                cognition["scene_stability"]
        }
    )

    return cognition


# =========================================================
# 🧠 VISUAL FOCUS ANALYSIS
# =========================================================

VISUAL_OBJECT_WORDS = [
    "объект","предмет","элемент","человек",
    "мужчина","женщина","кот","собака",
    "машина","дом","дерево"
]

VISUAL_ATTRIBUTE_WORDS = [
    "цвет","цвета","какого цвета",
    "размер","форма","выглядит"
]

VISUAL_ACTION_WORDS = [
    "делает","занимается","смотрит",
    "держит","идет","сидит","стоит"
]

def build_visual_focus_analysis(text):

    t = (text or "").lower()

    return {
        "visual_focus_request":
            any(x in t for x in ["этот","эта","это","справа","слева","объект","предмет"]),
        "visual_attribute_request":
            any(x in t for x in VISUAL_ATTRIBUTE_WORDS),
        "visual_action_request":
            any(x in t for x in VISUAL_ACTION_WORDS),
        "visual_object_reference":
            any(x in t for x in VISUAL_OBJECT_WORDS)
    }


# =========================================================
# 🧠 CORE ANALYZER
# =========================================================

def analyze_cognition(

    text: str,
    state: dict,
    semantic: dict,
    reasoning: dict
):

    APRIL_LOG_IN(

        "COGNITION_ROOM",

        {
            "action":
                "analyze_cognition"
        }
    )

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

    visual_focus = build_visual_focus_analysis(
        t
    )

    # =========================================================
    # 🧠 GOLDEN MEMORY BUILD
    # =========================================================

    dynamic_focus = build_dynamic_focus(
        text,
        continuity
    )

    goal_hierarchy = build_goal_hierarchy(
        text,
        active_flow
    )

    open_loops = build_open_loops(
        continuity
    )

    memory_signals = build_memory_signals(
        text,
        continuity
    )


    cognition = {

        "wants_action":
            0.0,

        "wants_help":
            0.0,

        "wants_visual":
            0.0,

        "wants_dialog":
            0.0,

        "execution_pressure":
            0.0,

        "scene_stability":
            0.72,

        "internal_noise":
            0.08,

        "signal_overload":
            0.05,

        "prefer_execution":
            False,

        "prefer_visual":
            False,

        "prefer_renderer":
            False,

        "renderer_space_active":
            False,

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

        "response_should_feel_human":
            False,

        "response_should_flow_naturally":
            False,

        "response_should_continue_naturally":
            False,

        "response_should_reduce_robotic_tone":
            True,

        "tracks_multiple_topics":
            False,

        "should_answer_in_order":
            False,

        "preserve_question_order":
            False,

        "avoid_topic_loss":
            True,

        "continuity_state":
            continuity,

        "visual_memory":
            visual_memory,

        "visual_mode":
            visual_mode,

        "machine_task_channel":
            COGNITION_TASK_CHANNEL,

        "machine_response_channel":
            COGNITION_RESPONSE_CHANNEL,

        "telemetry":
            build_cognition_telemetry(),

        "visual_focus":
            visual_focus,

        # =====================================================
        # 🧠 GOLDEN MEMORY
        # =====================================================

        "dynamic_focus":
            dynamic_focus,

        "goal_hierarchy":
            goal_hierarchy,

        "open_loops":
            open_loops,

        "memory_signals":
            memory_signals
    }

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

    if _contains_any(
        t,
        TRAVEL_WORDS
    ):

        cognition[
            "internet_context_needed"
        ] = True

    cognition = stabilize_trajectory(
        cognition,
        active_flow
    )

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

    cognition = stabilize_dialog_behavior(
        cognition
    )

    cognition = stabilize_cognition_state(
        cognition
    )

    for key, value in cognition.items():

        if isinstance(
            value,
            float
        ):

            cognition[key] = _clamp(
                value
            )

    APRIL_LOG_OUT(

        "COGNITION_ROOM",

        {
            "analysis":
                "complete"
        }
    )

    return cognition


# =========================================================
# 🧠 GOLDEN MEMORY LAYER
# =========================================================

def build_dynamic_focus(text, continuity):
    requests = continuity.get("recent_user_requests", [])
    primary = requests[-1] if requests else (text or "")[:120]
    secondary = requests[-2] if len(requests) >= 2 else None
    return {
        "primary_focus": primary,
        "secondary_focus": secondary,
        "focus_strength": 0.85 if primary else 0.25
    }

def build_goal_hierarchy(text, active_flow):
    return {
        "strategic_goal": active_flow.get("trajectory") if isinstance(active_flow, dict) else None,
        "active_goal": (text or "")[:180],
        "local_task": (text or "")[:120]
    }

def build_open_loops(continuity):
    unresolved = continuity.get("unresolved_questions", [])
    return {
        "unfinished_tasks": unresolved[-5:],
        "open_loops_count": len(unresolved),
        "has_open_loops": bool(unresolved)
    }

def build_memory_signals(text, continuity):
    relevance = 0.5
    if continuity.get("user_waiting_answer"):
        relevance += 0.3
    return {
        "memory_priority": min(relevance, 1.0),
        "memory_relevance": min(relevance, 1.0),
        "memory_weight": min(relevance + 0.1, 1.0),
        "forget_candidate": relevance < 0.35
    }
