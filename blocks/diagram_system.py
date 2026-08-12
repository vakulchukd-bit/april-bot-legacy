# ==================== 🟢 BLOCK: DIAGRAM SYSTEM ====================

# =====================================================
# 🧠 APRIL DIAGRAM SYSTEM
# =====================================================

"""
APRIL SPATIAL / DIAGRAM MACHINE SERVICE

APRIL_FILE_ID:
APRIL_DIAGRAM_SYSTEM_CORE

ROLE:
SPATIAL_SEMANTIC_SERVICE

INPUT:
MACHINE_REQUEST
EXECUTOR_CONTEXT
SCENE_CONTEXT

OUTPUT:
SPATIAL_ANALYSIS
DIAGRAM_SEMANTICS
RENDERER_CANDIDATE_STATE
SPATIAL_RENDER_PROMPT

LOGIC:
- spatial semantic understanding
- geometry interpretation
- renderer candidate detection
- engineering semantic analysis
- scene relation understanding
- diagram continuity support

THIS FILE IS:
- semantic helper core
- renderer-space assistant
- spatial cognition helper
- engineering semantic bridge

THIS FILE IS NOT:
- orchestration engine
- renderer authority
- frontend formatter
- telegram trigger layer
- cognition override system

GOLDEN APRIL RULES:
- renderer-first
- semantic-before-trigger
- continuity-safe
- no orchestration duplication
- no renderer chaos
- no system leakage
"""

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

DIAGRAM_TASK_CHANNEL = {

    "channel":
        "diagram_machine_task_channel",

    "isolated":
        True
}

DIAGRAM_RESPONSE_CHANNEL = {

    "channel":
        "diagram_machine_response_channel",

    "isolated":
        True
}

# =====================================================
# 🔥 ANALYZER LOGGING
# =====================================================

def log_diagram_input(

    text,
    context=None
):

    """
    INPUT MACHINE TRACE

    Used by:
    - analyzer
    - admin diagnostics
    - renderer tracing
    - execution observability
    """

    return {

        "file_id":
            "APRIL_DIAGRAM_SYSTEM_CORE",

        "event":
            "diagram_input",

        "channel":
            DIAGRAM_TASK_CHANNEL,

        "text_length":
            len(text or ""),

        "context":
            context or {},

        "machine_only":
            True
    }


def log_diagram_output(
    analysis
):

    """
    OUTPUT MACHINE TRACE

    Used by:
    - analyzer
    - renderer diagnostics
    - semantic observability
    - execution tracing
    """

    return {

        "file_id":
            "APRIL_DIAGRAM_SYSTEM_CORE",

        "event":
            "diagram_output",

        "channel":
            DIAGRAM_RESPONSE_CHANNEL,

        "renderer_candidate":
            analysis.get(
                "renderer_candidate",
                False
            ),

        "spatial_score":
            analysis.get(
                "spatial_score",
                0.0
            ),

        "machine_only":
            True
    }

# =====================================================
# 🔥 HELPERS
# =====================================================

def normalize_text(text):

    return (
        text or ""
    ).strip().lower()


def contains_any(
    text,
    words
):

    return any(
        w in text
        for w in words
    )

# =====================================================
# 🔥 SPATIAL SIGNALS
# =====================================================

SPATIAL_OBJECTS = [

    "треугольник",
    "квадрат",
    "прямоугольник",
    "круг",
    "ромб",
    "линия",
    "стрелка",
    "вектор",
    "куб",
    "сфера",
    "цилиндр",
    "конус",
    "пирамида",
    "параллелепипед"
]

SPATIAL_RELATIONS = [

    "между",
    "внутри",
    "слева",
    "справа",
    "сверху",
    "снизу",
    "соединить",
    "расположить",
    "структура",
    "связь",
    "отношение",
    "координаты"
]

STRUCTURE_SIGNALS = [

    "схема",
    "диаграмма",
    "чертеж",
    "чертёж",
    "план",
    "layout",
    "blueprint",
    "architecture",
    "структура",
    "конструкция"
]

ENGINEERING_SIGNALS = [

    "размер",
    "масштаб",
    "ось",
    "угол",
    "радиус",
    "диаметр",
    "инженер",
    "геометр",
    "проекция"
]

# =====================================================
# 🔥 LEGACY TEXT ANALYSIS (backward compatibility)
# =====================================================


def analyze_diagram_request(machine_request: dict):
    """Preferred Executor entrypoint."""
    machine_request = machine_request or {}
    semantic = machine_request.get("semantic", {})
    reps = semantic.get("required_representations", []) or []
    return {
        "spatial_intent": bool(semantic.get("spatial")),
        "diagram_intent": "diagram" in reps,
        "engineering_intent": bool(semantic.get("engineering")),
        "structure_intent": bool(semantic.get("structure")),
        "renderer_candidate": "diagram" in reps,
        "scene_candidate": True,
        "geometry_detected": bool(semantic.get("geometry")),
        "spatial_score": 1.0 if "diagram" in reps else 0.0,
        "machine_channel": DIAGRAM_RESPONSE_CHANNEL,
        "machine_only": True
    }

def analyze_diagram_semantics(
    text
):

    log_diagram_input(text)

    t = normalize_text(text)

    analysis = {

        "spatial_intent": False,

        "diagram_intent": False,

        "engineering_intent": False,

        "structure_intent": False,

        "renderer_candidate": False,

        "scene_candidate": False,

        "geometry_detected": False,

        "spatial_score": 0.0,

        "machine_channel":
            DIAGRAM_RESPONSE_CHANNEL
    }

    score = 0.0

    # =================================================
    # 🔥 STRUCTURE
    # =====================================================

    if contains_any(
        t,
        STRUCTURE_SIGNALS
    ):

        analysis[
            "structure_intent"
        ] = True

        analysis[
            "diagram_intent"
        ] = True

        score += 0.45

    # =================================================
    # 🔥 GEOMETRY
    # =====================================================

    if contains_any(
        t,
        SPATIAL_OBJECTS
    ):

        analysis[
            "geometry_detected"
        ] = True

        analysis[
            "spatial_intent"
        ] = True

        score += 0.35

    # =================================================
    # 🔥 RELATIONS
    # =====================================================

    if contains_any(
        t,
        SPATIAL_RELATIONS
    ):

        analysis[
            "spatial_intent"
        ] = True

        analysis[
            "scene_candidate"
        ] = True

        score += 0.25

    # =================================================
    # 🔥 ENGINEERING
    # =====================================================

    if contains_any(
        t,
        ENGINEERING_SIGNALS
    ):

        analysis[
            "engineering_intent"
        ] = True

        analysis[
            "diagram_intent"
        ] = True

        score += 0.35

    # =================================================
    # 🔥 FINAL
    # =====================================================

    analysis[
        "spatial_score"
    ] = min(score, 1.0)

    if score >= 0.45:

        analysis[
            "renderer_candidate"
        ] = True

    log_diagram_output(analysis)

    return analysis

# =====================================================
# 🔥 LEGACY COMPATIBILITY
# =====================================================

# LEGACY COMPATIBILITY ONLY
def is_diagram_request(
    text: str
) -> bool:

    """
    Deprecated compatibility bridge. Executor should provide machine context.

    НЕ trigger routing.

    Используется только как
    soft semantic compatibility layer
    для старых systems.
    """

    # Legacy bridge: use only explicitly supplied machine context.
    # No hidden/global state is consulted.
    hidden_context = locals().get("hidden_context")
    if isinstance(hidden_context, dict) and hidden_context.get("semantic"):
        analysis = analyze_diagram_request(hidden_context)
    else:
        analysis = analyze_diagram_semantics(text)

    return analysis.get(
        "renderer_candidate",
        False
    )

# =====================================================
# 🔥 FACTORY SEMANTIC ADAPTER
# =====================================================

DIAGRAM_ROOM_ID = "C_DIAGRAM_ROOM"
DIAGRAM_ARTIFACT_TYPE = "diagram"
DIAGRAM_RENDERER = "DiagramBlock"


def build_diagram_factory_signal(machine_request: dict) -> dict:
    '''Convert processor-provided semantic state into the factory's canonical
    diagram signal. This function does not select routes or call renderers.'''
    request = machine_request or {}
    analysis = analyze_diagram_request(request)
    return {
        "artifact_type": DIAGRAM_ARTIFACT_TYPE,
        "room_source": DIAGRAM_ROOM_ID,
        "renderer": DIAGRAM_RENDERER,
        "viewer": DIAGRAM_RENDERER,
        "semantic": analysis,
        "spatial": {
            "geometry": bool(analysis.get("geometry_detected")),
            "relations": bool(analysis.get("spatial_intent")),
            "engineering": bool(analysis.get("engineering_intent")),
            "structure": bool(analysis.get("structure_intent")),
        },
        "machine_only": True,
    }

# =====================================================
# 🔥 DIAGRAM PROMPT
# =====================================================

def build_diagram_prompt(
    text,
    hidden_context=None
):

    """
    Semantic diagram prompt.

    Prompt строится
    через spatial understanding,
    а не trigger words.
    """

    analysis = analyze_diagram_semantics(
        text
    )

    style_parts = [

        "technical drawing",
        "blueprint",
        "schematic",
        "clean geometry",
        "precise lines",
        "engineering style",
        "minimalistic",
        "white background",
        "black lines"
    ]

    # =================================================
    # 🔥 ENGINEERING
    # =====================================================

    if analysis.get(
        "engineering_intent"
    ):

        style_parts.extend([

            "dimensional drawing",
            "technical precision",
            "mechanical layout"
        ])

    # =================================================
    # 🔥 SPATIAL
    # =====================================================

    if analysis.get(
        "spatial_intent"
    ):

        style_parts.extend([

            "spatial relations",
            "structured composition",
            "object positioning"
        ])

    # =================================================
    # 🔥 GEOMETRY
    # =====================================================

    if analysis.get(
        "geometry_detected"
    ):

        style_parts.extend([

            "geometric construction",
            "mathematical precision"
        ])

    style = ", ".join(style_parts)

    payload = (

        f"{style}\n\n"

        f"{text}"
    )

    if hidden_context:

        payload = (

            f"{style}\n\n"

            f"{hidden_context}\n\n"

            f"{text}"
        )

    return {

        "channel":
            DIAGRAM_RESPONSE_CHANNEL,

        "file_id":
            "APRIL_DIAGRAM_SYSTEM_CORE",

        "renderer_safe":
            True,

        "prompt":
            payload,

        "machine_only":
            True
    }
