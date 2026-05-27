from blocks.visual_memory_library import (
    build_visual_memory_response
)

# =====================================================
# 🧠 APRIL COGNITION CORE
# =====================================================

"""
APRIL COGNITION CORE

NEW PRINCIPLES:

- compact cognition
- machine-readable orchestration
- low-noise state transfer
- continuity compression
- renderer-first cognition
- executor-friendly signals
- no emotional flag explosion
- semantic continuity over prose cognition

COGNITION IS NOW:

NOT:
- giant emotional state blob
- prose-like orchestration
- duplicated semantic flags

BUT:
- compact machine state
- executor-readable orchestration
- continuity transport layer
"""

# =====================================================
# 🔥 HELPERS
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


def _contains_any(
    text,
    words
):

    return any(
        w in text
        for w in words
    )


def _safe_lower(text):

    try:
        return str(text).lower().strip()
    except:
        return ""


# =====================================================
# 🔥 COMPACT SIGNALS
# =====================================================

ACTION_WORDS = [

    "сделай",
    "создай",
    "исправь",
    "покажи",
    "построй",
    "сгенерируй",
    "нарисуй"
]

HELP_WORDS = [

    "помоги",
    "объясни",
    "не понимаю",
    "подскажи"
]

VISUAL_WORDS = [

    "график",
    "формула",
    "таблица",
    "схема",
    "картинка",
    "изображение",
    "скрин",
    "фото"
]

RENDER_WORDS = [

    "график",
    "формула",
    "таблица",
    "renderer",
    "scene",
    "canvas",
    "diagram",
    "layout"
]

WEB_WORDS = [

    "погода",
    "карта",
    "маршрут",
    "рейс",
    "курс валют",
    "новости"
]

EXPLORATION_WORDS = [

    "примерно",
    "идея",
    "вариант",
    "может",
    "как думаешь",
    "референс",
    "атмосфера"
]

CONTINUATION_WORDS = [

    "да",
    "ага",
    "дальше",
    "продолжай",
    "вот",
    "не то",
    "уже лучше",
    "примерно",
    "так"
]


# =====================================================
# 🔥 CONTINUITY
# =====================================================

def build_continuity_state(
    text,
    dialog,
    active_flow,
    state
):

    t = _safe_lower(text)

    continuity = {

        "mode": "none",

        "strength": 0.0,

        "visual": False,

        "scene": False,

        "continuation": False,

        "active_flow": None
    }

    if active_flow:

        continuity[
            "continuation"
        ] = True

        continuity[
            "active_flow"
        ] = active_flow.get(
            "type"
        )

        continuity[
            "strength"
        ] += 0.45

    active_visual_scene = state.get(
        "active_visual_scene"
    )

    if active_visual_scene:

        visual_words = [

            "это",
            "этот",
            "эта",
            "слева",
            "справа",
            "цвет",
            "объект",
            "картинка",
            "фото",
            "здесь"
        ]

        if (

            _contains_any(
                t,
                visual_words
            )

            or len(t) <= 60
        ):

            continuity[
                "visual"
            ] = True

            continuity[
                "scene"
            ] = True

            continuity[
                "continuation"
            ] = True

            continuity[
                "mode"
            ] = "visual_scene"

            continuity[
                "strength"
            ] += 0.45

    if _contains_any(
        t,
        CONTINUATION_WORDS
    ):

        continuity[
            "continuation"
        ] = True

        continuity[
            "strength"
        ] += 0.25

    continuity[
        "strength"
    ] = _clamp(
        continuity[
            "strength"
        ]
    )

    return continuity


# =====================================================
# 🔥 RENDER DETECTION
# =====================================================

def detect_render_state(
    text
):

    t = _safe_lower(text)

    render = {

        "active": False,

        "type": None,

        "priority": 0.0
    }

    if not _contains_any(
        t,
        RENDER_WORDS
    ):

        return render

    render[
        "active"
    ] = True

    render[
        "priority"
    ] = 0.92

    if (

        "график" in t
        or "y=" in t
        or "sin(" in t
        or "cos(" in t
    ):

        render["type"] = "graph"

    elif (

        "формула" in t
        or "уравнение" in t
    ):

        render["type"] = "formula"

    elif (

        "таблица" in t
        or "grid" in t
    ):

        render["type"] = "table"

    elif (

        "схема" in t
        or "diagram" in t
    ):

        render["type"] = "diagram"

    else:

        render["type"] = "scene"

    return render


# =====================================================
# 🔥 EXECUTION STATE
# =====================================================

def detect_execution_state(
    text
):

    t = _safe_lower(text)

    state = {

        "execute": False,

        "pressure": 0.0,

        "mode": "talk"
    }

    if _contains_any(
        t,
        ACTION_WORDS
    ):

        state[
            "execute"
        ] = True

        state[
            "pressure"
        ] = 0.82

        state[
            "mode"
        ] = "execute"

    elif _contains_any(
        t,
        EXPLORATION_WORDS
    ):

        state[
            "execute"
        ] = False

        state[
            "pressure"
        ] = 0.25

        state[
            "mode"
        ] = "exploration"

    return state


# =====================================================
# 🔥 MAIN ANALYZER
# =====================================================

def analyze_cognition(
    text: str,
    state: dict,
    semantic: dict,
    reasoning: dict
):

    t = _safe_lower(text)

    state = state or {}
    semantic = semantic or {}
    reasoning = reasoning or {}

    dialog = state.get(
        "dialog",
        []
    )

    active_flow = state.get(
        "active_flow"
    )

    continuity = build_continuity_state(

        t,
        dialog,
        active_flow,
        state
    )

    render = detect_render_state(
        t
    )

    execution = detect_execution_state(
        t
    )

    visual_memory = build_visual_memory_response(
        text
    )

    cognition = {

        # =================================================
        # 🔥 CORE MODES
        # =====================================================

        "mode": execution.get(
            "mode",
            "talk"
        ),

        "continuity_mode": continuity.get(
            "mode",
            "none"
        ),

        "render_mode": render.get(
            "type"
        ),

        # =================================================
        # 🔥 EXECUTOR SIGNALS
        # =====================================================

        "prefer_execution":
            execution.get(
                "execute",
                False
            ),

        "prefer_renderer":
            render.get(
                "active",
                False
            ),

        "renderer_space_active":
            render.get(
                "active",
                False
            ),

        "internet_context_needed":

            _contains_any(
                t,
                WEB_WORDS
            ),

        # =================================================
        # 🔥 CONTINUITY
        # =====================================================

        "needs_continuation":

            continuity.get(
                "continuation",
                False
            ),

        "trajectory_locked":

            continuity.get(
                "strength",
                0.0
            ) >= 0.55,

        "continuity_strength":

            continuity.get(
                "strength",
                0.0
            ),

        "active_flow":

            continuity.get(
                "active_flow"
            ),

        # =================================================
        # 🔥 HUMAN STATE
        # =====================================================

        "needs_guidance":

            _contains_any(
                t,
                HELP_WORDS
            ),

        "exploration_mode":

            execution.get(
                "mode"
            ) == "exploration",

        "prefer_visual":

            _contains_any(
                t,
                VISUAL_WORDS
            ),

        # =================================================
        # 🔥 EXECUTION
        # =====================================================

        "execution_pressure":

            execution.get(
                "pressure",
                0.0
            ),

        "execution_confidence":

            0.88

            if execution.get(
                "execute"
            )

            else 0.45,

        # =================================================
        # 🔥 RENDER
        # =====================================================

        "render_priority":

            render.get(
                "priority",
                0.0
            ),

        "render_type":

            render.get(
                "type"
            ),

        # =================================================
        # 🔥 STABILITY
        # =====================================================

        "scene_stability": 0.88,

        "internal_noise": 0.08,

        "signal_overload": 0.05,

        # =================================================
        # 🔥 MACHINE FLAGS
        # =====================================================

        "machine_state": {

            "renderer":
                render.get(
                    "active",
                    False
                ),

            "continuation":
                continuity.get(
                    "continuation",
                    False
                ),

            "visual":
                continuity.get(
                    "visual",
                    False
                ),

            "execution":
                execution.get(
                    "execute",
                    False
                )
        },

        # =================================================
        # 🔥 MEMORY
        # =====================================================

        "visual_memory":
            visual_memory
    }

    # =================================================
    # 🔥 REASONING INHERITANCE
    # =====================================================

    if reasoning.get(
        "continuation"
    ):

        cognition[
            "needs_continuation"
        ] = True

        cognition[
            "trajectory_locked"
        ] = True

        cognition[
            "continuity_strength"
        ] = max(

            cognition[
                "continuity_strength"
            ],

            0.72
        )

    # =================================================
    # 🔥 RENDER PRIORITY
    # =====================================================

    if cognition.get(
        "prefer_renderer"
    ):

        cognition[
            "prefer_visual"
        ] = False

        cognition[
            "prefer_execution"
        ] = True

        cognition[
            "execution_pressure"
        ] = max(

            cognition[
                "execution_pressure"
            ],

            0.82
        )

    # =================================================
    # 🔥 FINAL NORMALIZATION
    # =====================================================

    float_keys = [

        "execution_pressure",
        "execution_confidence",
        "render_priority",
        "scene_stability",
        "internal_noise",
        "signal_overload",
        "continuity_strength"
    ]

    for key in float_keys:

        cognition[key] = _clamp(
            cognition.get(
                key,
                0.0
            )
        )

    return cognition
