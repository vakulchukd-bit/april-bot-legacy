# ==================== 🟢 BLOCK: DIAGRAM SYSTEM ====================

# =====================================================
# 🧠 APRIL DIAGRAM SYSTEM
# =====================================================

"""
APRIL SPATIAL / DIAGRAM UNDERSTANDING

Этот слой:

✅ помогает executor понимать
   spatial / structural intent

✅ помогает renderer-space

✅ помогает scene orchestration

✅ понимает:
- geometry
- relations
- structure
- layouts
- diagrams
- technical schemes
- blueprint logic

✅ работает как semantic helper

❌ НЕ force-trigger layer
❌ НЕ telegram-style detector
❌ НЕ final renderer authority
❌ НЕ payload formatter
❌ НЕ output layer

Главная задача:
semantic spatial understanding,
а не поиск слов.
"""

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
# 🔥 SEMANTIC ANALYSIS
# =====================================================

def analyze_diagram_semantics(
    text
):

    t = normalize_text(text)

    analysis = {

        "spatial_intent": False,

        "diagram_intent": False,

        "engineering_intent": False,

        "structure_intent": False,

        "renderer_candidate": False,

        "scene_candidate": False,

        "geometry_detected": False,

        "spatial_score": 0.0
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

    return analysis


# =====================================================
# 🔥 LEGACY COMPATIBILITY
# =====================================================

def is_diagram_request(
    text: str
) -> bool:

    """
    Legacy compatibility bridge.

    НЕ trigger routing.

    Используется только как
    soft semantic compatibility layer
    для старых systems.
    """

    analysis = analyze_diagram_semantics(
        text
    )

    return analysis.get(
        "renderer_candidate",
        False
    )


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

    if hidden_context:

        return (

            f"{style}\n\n"

            f"{hidden_context}\n\n"

            f"{text}"
        )

    return (

        f"{style}\n\n"

        f"{text}"
    )
