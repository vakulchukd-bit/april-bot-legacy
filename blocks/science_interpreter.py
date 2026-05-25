# =====================================================
# 🧠 APRIL SCIENCE INTERPRETER
# =====================================================

"""
APRIL SCIENCE INTERPRETER

Renderer-first spatial interpretation layer.

=====================================================

OLD SYSTEM PROBLEMS:

- trigger-based;
- Telegram-era routing;
- python-eval thinking;
- graph as text;
- hardcoded functions;
- fallback corruption;
- no scene understanding;
- no renderer-space awareness.

=====================================================

NEW APRIL PRINCIPLES:

1. April understands intent
2. renderer builds space
3. graph is spatial object
4. formula is scene object
5. no trigger hallucinations
6. no python eval logic
7. no forced regex intelligence
8. multimodal-safe architecture
9. renderer-first orchestration
10. spatial continuity before text

=====================================================

THIS MODULE DOES NOT:

- solve math;
- execute python;
- generate images;
- build matplotlib;
- use eval();
- use numpy expressions.

=====================================================

THIS MODULE DOES:

- interpret spatial-science intent;
- organize renderer payloads;
- normalize graph expressions;
- prepare scene-compatible objects;
- preserve April Space continuity.
"""

import re


# =====================================================
# 🔥 SAFE NORMALIZATION
# =====================================================

def normalize_text(
    text
):

    if text is None:
        return ""

    return str(text).strip()


# =====================================================
# 🔥 SAFE LOWER
# =====================================================

def normalize_lower(
    text
):

    return normalize_text(
        text
    ).lower()


# =====================================================
# 🔥 SPATIAL KEYWORDS
# =====================================================

SPATIAL_KEYWORDS = [

    "график",
    "графика",
    "нарисуй",
    "построй",
    "диаграмма",
    "схема",
    "таблица",
    "формула",
    "функция",
    "координаты",
    "ось",
    "линия",
    "кривая",
    "plot",
    "graph",
    "chart",
    "diagram",
    "function"
]


# =====================================================
# 🔥 FORMULA NORMALIZER
# =====================================================

def normalize_graph_expression(
    text: str
):

    text = normalize_text(
        text
    )

    if not text:
        return None

    # =================================================
    # 🔥 SAFE CLEANUP
    # =====================================================

    expr = text

    expr = expr.replace(
        "×",
        "*"
    )

    expr = expr.replace(
        "−",
        "-"
    )

    expr = expr.replace(
        "–",
        "-"
    )

    expr = expr.replace(
        "^",
        "**"
    )

    expr = expr.replace(
        "y =",
        ""
    )

    expr = expr.replace(
        "y=",
        ""
    )

    expr = expr.strip()

    # =================================================
    # 🔥 SAFE HUMAN NORMALIZATION
    # =====================================================

    expr = re.sub(
        r"(\d)x",
        r"\1*x",
        expr
    )

    expr = re.sub(
        r"(\d)\(",
        r"\1*(",
        expr
    )

    expr = re.sub(
        r"x\(",
        r"x*(",
        expr
    )

    # =================================================
    # 🔥 BASIC SAFETY
    # =====================================================

    allowed = re.fullmatch(
        r"[0-9xX\+\-\*\/\.\(\)\s_a-zA-Z]+",
        expr
    )

    if not allowed:
        return None

    return expr


# =====================================================
# 🔥 DETECT RENDER INTENT
# =====================================================

def has_spatial_intent(
    text: str
):

    t = normalize_lower(text)

    return any(
        word in t
        for word in SPATIAL_KEYWORDS
    )


# =====================================================
# 🔥 GRAPH DETECTION
# =====================================================

def detect_graph_expression(
    text: str
):

    text = normalize_text(
        text
    )

    if not text:
        return None

    # =================================================
    # 🔥 y =
    # =====================================================

    y_match = re.search(
        r"y\s*=\s*([^\n]+)",
        text,
        re.IGNORECASE
    )

    if y_match:

        return normalize_graph_expression(
            y_match.group(1)
        )

    # =================================================
    # 🔥 f(x)
    # =====================================================

    fx_match = re.search(
        r"f\(x\)\s*=\s*([^\n]+)",
        text,
        re.IGNORECASE
    )

    if fx_match:

        return normalize_graph_expression(
            fx_match.group(1)
        )

    return None


# =====================================================
# 🔥 GRAPH PAYLOAD
# =====================================================

def build_graph_payload(
    expression: str
):

    return {

        # =================================================
        # 🔥 CORE
        # =====================================================

        "type": "graph",

        "graph": expression,

        # =================================================
        # 🔥 RENDERER SPACE
        # =====================================================

        "renderer": "april_graph",

        "renderer_mode": "spatial",

        "scene_type": "graph_space",

        "spatial_object": True,

        "scene_ready": True,

        "layout_safe": True,

        # =================================================
        # 🔥 APRIL SPACE
        # =====================================================

        "renderer_first": True,

        "provider_safe": True,

        "lightweight_render": True,

        "avoid_generation": True,

        # =================================================
        # 🔥 UI
        # =====================================================

        "title": "GRAPH",

        "show_formula": True
    }


# =====================================================
# 🔥 FORMULA PAYLOAD
# =====================================================

def build_formula_payload(
    formula: str
):

    return {

        "type": "formula",

        "formula": formula,

        "renderer": "april_formula",

        "renderer_mode": "spatial",

        "scene_type": "formula_space",

        "spatial_object": True,

        "scene_ready": True,

        "renderer_first": True,

        "lightweight_render": True,

        "avoid_generation": True
    }


# =====================================================
# 🔥 TABLE PAYLOAD
# =====================================================

def build_table_payload():

    return {

        "type": "table",

        "renderer": "april_table",

        "renderer_mode": "spatial",

        "scene_type": "table_space",

        "spatial_object": True,

        "scene_ready": True,

        "renderer_first": True,

        "lightweight_render": True,

        "avoid_generation": True
    }


# =====================================================
# 🔥 MAIN INTERPRETER
# =====================================================

def interpret_graph_request(
    text: str
):

    """
    Main April science interpreter.

    IMPORTANT:

    This is NOT:
    - math solving;
    - trigger matching;
    - python execution.

    This IS:
    - spatial intent interpretation;
    - renderer-scene preparation.
    """

    text = normalize_text(
        text
    )

    if not text:
        return None

    # =================================================
    # 🔥 SPATIAL CHECK
    # =====================================================

    if not has_spatial_intent(
        text
    ):

        return None

    lower = normalize_lower(
        text
    )

    # =================================================
    # 🔥 TABLE SPACE
    # =====================================================

    if (
        "таблица" in lower
        or "table" in lower
    ):

        return build_table_payload()

    # =================================================
    # 🔥 GRAPH SPACE
    # =====================================================

    graph_expr = detect_graph_expression(
        text
    )

    if graph_expr:

        return build_graph_payload(
            graph_expr
        )

    # =================================================
    # 🔥 FORMULA SPACE
    # =====================================================

    if (
        "формула" in lower
        or "formula" in lower
    ):

        formula = detect_graph_expression(
            text
        )

        if formula:

            return build_formula_payload(
                formula
            )

    # =================================================
    # 🔥 SAFE FALLBACK
    # =====================================================

    return {

        "type": "renderer_scene",

        "renderer": "april_scene",

        "renderer_mode": "spatial",

        "scene_type": "generic_visual_space",

        "spatial_object": True,

        "scene_ready": True,

        "renderer_first": True,

        "lightweight_render": True,

        "avoid_generation": True,

        "content": text
    }
