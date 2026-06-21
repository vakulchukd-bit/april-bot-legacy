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
# 🧠 VISUAL SCENE BRIDGE
# =========================================================

def build_visual_scene_bridge(state):

    active_visual_scene = state.get(
        "active_visual_scene"
    ) or {}

    return {

        "scene_active":
            bool(active_visual_scene),

        "scene_type":
            active_visual_scene.get(
                "scene_type"
            ),

        "semantic_focus":
            active_visual_scene.get(
                "semantic_focus"
            ),

        "visual_topic":
            active_visual_scene.get(
                "memory_anchor",
                {}
            ).get(
                "topic"
            ),

        "visual_object":
            active_visual_scene.get(
                "memory_anchor",
                {}
            ).get(
                "object"
            ),

        "visual_intent":
            active_visual_scene.get(
                "memory_anchor",
                {}
            ).get(
                "intent"
            )
    }



# =========================================================
# 🧠 REPRESENTATION UNDERSTANDING LAYER
# =========================================================

EXPLANATION_WORDS = [
    "объясни","почему","разбери","расскажи",
    "как работает","что означает","анализ"
]

def build_representation_understanding(text):

    t = (text or "").lower()

    subject_type = "text"

    if "формул" in t:
        subject_type = "formula"
    elif "график" in t:
        subject_type = "graph"
    elif "таблиц" in t:
        subject_type = "table"

    interaction_mode = "discussion"

    if any(x in t for x in EXPLANATION_WORDS):
        interaction_mode = "explanation"
    elif any(x in t for x in ["построй","нарисуй","создай"]):
        interaction_mode = "construction"

    renderer_required = (
        interaction_mode == "construction"
        and subject_type in ["formula","graph","table"]
    )

    return {
        "subject_type": subject_type,
        "interaction_mode": interaction_mode,
        "renderer_required": renderer_required,
        "renderer_candidate": subject_type != "text",
        "prefer_text_explanation":
            interaction_mode == "explanation"
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

    active_scene = state.get(
        "active_scene",
        {}
    )

    visual_continuity = state.get(
        "visual_continuity_summary",
        {}
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

    representation_understanding = (
        build_representation_understanding(text)
    )

    # =========================================================
    # 🧠 GOLDEN MEMORY BUILD
    # =========================================================

    visual_scene_bridge = build_visual_scene_bridge(
        state
    )

    abcde_focus = build_abcde_focus(
        text,
        continuity,
        visual_focus
    )

    if visual_scene_bridge.get(
        "scene_active"
    ):

        if (
            not abcde_focus.get(
                "object"
            )
        ):

            abcde_focus[
                "object"
            ] = visual_scene_bridge.get(
                "visual_object"
            )

    dynamic_focus = {

        "primary_focus":
            abcde_focus.get(
                "focus"
            ),

        "secondary_focus":
            abcde_focus.get(
                "object"
            ),

        "focus_strength":
            abcde_focus.get(
                "focus_strength",
                0.5
            ),

        "abcde":
            abcde_focus
    }

    goal_hierarchy = build_goal_hierarchy(
        text,
        active_flow
    )

    task_understanding = build_task_understanding(
        text,
        continuity,
        visual_scene_bridge
    )

    user_confusion = build_user_confusion(
        text
    )

    assistant_next_step = build_assistant_next_step(
        task_understanding
    )

    open_loops = build_open_loops(
        continuity
    )

    memory_signals = build_memory_signals(
        text,
        continuity
    )

    if visual_scene_bridge.get(
        "scene_active"
    ):

        memory_signals[
            "visual_priority"
        ] = 1.0

        memory_signals[
            "visual_scene_alive"
        ] = True

        memory_signals[
            "memory_weight"
        ] = min(
            memory_signals.get(
                "memory_weight",
                0.5
            ) + 0.2,
            1.0
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

        "visual_scene_bridge":
            visual_scene_bridge,

        "representation_understanding":
            representation_understanding,

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
            memory_signals,

        "active_scene":
            active_scene,

        "visual_continuity":
            visual_continuity,

        "scene_cognition_active":
            True,

        "task_understanding":
            task_understanding,

        "user_confusion":
            user_confusion,

        "assistant_next_step":
            assistant_next_step,

        "guidance_priority":
            user_confusion >= 0.5,

        "scene_confidence":
            1.0 if visual_scene_bridge.get("scene_active") else 0.45
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


# =========================================================
# 🧠 APRIL FOCUS EVOLUTION UPGRADE
# =========================================================

FOCUS_INTENT_WORDS = [
    "сделай","исправь","апгрейд","анализ","проверь","найди","объясни"
]

def build_abcde_focus(text, continuity, visual_focus=None):

    t = (text or "").strip()

    topic = t[:120]

    scene = "dialog"

    if visual_focus and any(visual_focus.values()):
        scene = "visual"

    obj = None

    words = [w for w in t.split() if len(w) > 3]

    if words:
        obj = words[-1][:80]

    intent = "discussion"

    if any(x in t.lower() for x in FOCUS_INTENT_WORDS):
        intent = "action"

    focus_strength = 0.85

    if continuity.get("user_waiting_answer"):
        focus_strength = 1.0

    return {
        "topic": topic,
        "scene": scene,
        "object": obj,
        "focus": topic,
        "intent": intent,
        "focus_strength": focus_strength
    }


def build_focus_memory_priority(abcde, continuity):

    weight = abcde.get("focus_strength", 0.5)

    if continuity.get("user_waiting_answer"):
        weight += 0.15

    return min(weight, 1.0)



# =========================================================
# 🧠 ASSISTANT TASK UNDERSTANDING UPGRADE
# =========================================================

def build_task_understanding(text, continuity, visual_scene_bridge):

    t = (text or "").lower()

    goal = "discussion"

    if "ошиб" in t:
        goal = "fix_error"
    elif "график" in t:
        goal = "build_graph"
    elif "формул" in t:
        goal = "work_with_formula"
    elif "таблиц" in t:
        goal = "build_table"
    elif "скрин" in t or "изображ" in t:
        goal = "analyze_visual"

    missing_information = []

    if goal == "fix_error":
        missing_information.append("error_context")

    if goal == "build_graph":
        missing_information.append("formula")

    if goal == "analyze_visual" and not visual_scene_bridge.get("scene_active"):
        missing_information.append("image")

    return {
        "user_goal": goal,
        "goal_known": goal != "discussion",
        "missing_information": missing_information,
        "task_complete": len(missing_information) == 0
    }


def build_user_confusion(text):

    t = (text or "").lower()

    confusion_words = [
        "не понимаю",
        "запутался",
        "не получается",
        "ошибка",
        "не работает"
    ]

    score = 0.0

    for word in confusion_words:
        if word in t:
            score += 0.25

    return min(score, 1.0)


def build_assistant_next_step(task_understanding):

    missing = task_understanding.get(
        "missing_information",
        []
    )

    if "image" in missing:
        return "request_image"

    if "formula" in missing:
        return "request_formula"

    if "error_context" in missing:
        return "request_error_details"

    return "ready_to_help"


# APRIL PATCH V3
# assistant_next_step is INTERNAL ONLY.
# Never return to user directly.


# =========================================================
# 🧠 SCENE RELATION ENGINE
# =========================================================

def build_scene_relation(text, active_scene, dynamic_focus):

    text = (text or "").lower()

    relation = {
        "continue_scene": False,
        "temporary_branch": False,
        "return_to_previous_scene": False,
        "new_scene": False,
        "scene_confidence": 0.5
    }

    previous_focus = str(
        dynamic_focus.get("primary_focus", "")
    ).lower()

    if previous_focus and any(
        token in text for token in previous_focus.split()[:3]
    ):
        relation["continue_scene"] = True
        relation["scene_confidence"] = 0.9
    else:
        relation["new_scene"] = True

    return relation


# =========================================================
# 🧠 UNIFIED SCENE COGNITION BRIDGE
# =========================================================

def build_unified_scene_state(
    active_scene,
    dynamic_focus,
    goal_hierarchy,
    open_loops,
    memory_signals
):
    return {
        "active_scene": active_scene or {},
        "dynamic_focus": dynamic_focus or {},
        "goal_hierarchy": goal_hierarchy or {},
        "open_loops": open_loops or [],
        "memory_signals": memory_signals or {}
    }



# =========================================================
# 🧠 APRIL COGNITIVE MEMORY V2 UPGRADE
# =========================================================

def build_cognitive_memory_bridge(state):

    return {

        "focus_state":
            state.get("focus_state", {}),

        "memory_timeline":
            state.get("memory_timeline", {}),

        "memory_cycle":
            state.get("memory_cycle", {}),

        "dynamic_focus":
            state.get("dynamic_focus", {}),

        "goal_hierarchy":
            state.get("goal_hierarchy", {}),

        "open_loops":
            state.get("open_loops", []),

        "memory_signals":
            state.get("memory_signals", {})
    }


def build_timeline_awareness(state):

    timeline = state.get(
        "memory_timeline",
        {}
    )

    cycle = state.get(
        "memory_cycle",
        {}
    )

    return {

        "utc_enabled":
            bool(cycle),

        "current_memory_day":
            cycle.get(
                "current_day",
                "day_0"
            ),

        "timeline_available":
            bool(timeline),

        "day0_active":
            bool(
                timeline.get(
                    "day_0"
                )
            ),

        "day1_available":
            bool(
                timeline.get(
                    "day_1"
                )
            )
    }


def build_focus_evolution_v2(
    abcde_focus,
    focus_state
):

    merged = dict(
        abcde_focus or {}
    )

    if not focus_state:
        return merged

    merged["priority_score"] = (
        focus_state.get(
            "priority_score",
            0
        )
    )

    merged["intent_freshness"] = (
        focus_state.get(
            "intent_freshness",
            0
        )
    )

    merged["active_topic"] = (
        focus_state.get(
            "active_topic"
        )
    )

    return merged


def build_executor_guidance(

    task_understanding,
    goal_hierarchy,
    memory_signals,
    timeline_awareness

):

    return {

        "primary_goal":
            goal_hierarchy.get(
                "active_goal"
            ),

        "task_type":
            task_understanding.get(
                "user_goal"
            ),

        "goal_known":
            task_understanding.get(
                "goal_known"
            ),

        "memory_priority":
            memory_signals.get(
                "memory_priority",
                0.5
            ),

        "utc_memory_active":
            timeline_awareness.get(
                "utc_enabled",
                False
            ),

        "executor_should_preserve_continuity":
            True,

        "executor_should_use_memory":
            True
    }



# =========================================================
# 🧠 CONTRIBUTION AGGREGATOR LAYER
# =========================================================

def build_contribution_state(artifacts):

    aggregated = {

        "scene_contributions": [],
        "focus_contributions": [],
        "memory_contributions": [],
        "trajectory_hints": [],
        "scene_hints": []

    }

    if not artifacts:
        return aggregated

    for artifact in artifacts:

        try:

            context = artifact.get("context", {})

            aggregated["scene_contributions"].extend(
                context.get(
                    "scene_contributions",
                    []
                )
            )

            aggregated["focus_contributions"].extend(
                context.get(
                    "focus_contributions",
                    []
                )
            )

            aggregated["memory_contributions"].extend(
                context.get(
                    "memory_contributions",
                    []
                )
            )

            aggregated["trajectory_hints"].extend(
                context.get(
                    "trajectory_hints",
                    []
                )
            )

            aggregated["scene_hints"].extend(
                context.get(
                    "scene_hints",
                    []
                )
            )

        except Exception:
            continue

    return aggregated


# =========================================================
# 🧠 CONTRIBUTION → COGNITION BRIDGE
# =========================================================

def build_contribution_cognition_bridge(artifacts):

    contribution_state = build_contribution_state(
        artifacts
    )

    return {

        "contribution_state":
            contribution_state,

        "scene_contribution_count":
            len(
                contribution_state.get(
                    "scene_contributions",
                    []
                )
            ),

        "focus_contribution_count":
            len(
                contribution_state.get(
                    "focus_contributions",
                    []
                )
            ),

        "memory_contribution_count":
            len(
                contribution_state.get(
                    "memory_contributions",
                    []
                )
            ),

        "contribution_pipeline_active":
            True
    }
