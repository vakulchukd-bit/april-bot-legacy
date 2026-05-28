# =====================================================
# 🧠 APRIL SCIENCE INTERPRETER
# =====================================================

"""
APRIL SCIENCE INTERPRETER

Lightweight renderer-first science interpreter.

GOALS:
- spatial intent understanding
- renderer-safe payloads
- continuity-safe graph/formula routing
- compact scene transport
- no eval
- no execution
- no payload inflation
- web-first orchestration
- machine-safe renderer bridge
"""

import re


# =====================================================
# 🔥 MACHINE IDENTITY
# =====================================================

APRIL_FILE_ID = "APRIL_SCIENCE_INTERPRETER"

SCIENCE_MACHINE_CHANNEL = {

    "type": "science_interpreter",

    "mode": "renderer_first",

    "isolated": True,

    "continuity_safe": True,

    "web_safe": True
}

# =====================================================
# 🔥 SHARED FLAGS
# =====================================================

RENDER_FLAGS = {

    "renderer_first": True,
    "lightweight_render": True,
    "avoid_generation": True,
    "continuity_safe": True,
    "scene_ready": True,
    "web_safe": True,
    "machine_safe": True
}

# =====================================================
# 🔥 LOGGING
# =====================================================

SCIENCE_PATCH_LOG = []

def safe_science_log(msg):

    try:

        print(
            "APRIL SCIENCE:",
            msg
        )

        SCIENCE_PATCH_LOG.append(
            str(msg)
        )

    except:
        pass

safe_science_log(
    "SCIENCE INTERPRETER INITIALIZED"
)

# =====================================================
# 🔥 NORMALIZATION
# =====================================================

def normalize_text(text):

    if text is None:
        return ""

    return str(text).strip()


def normalize_lower(text):

    return normalize_text(
        text
    ).lower()


def contains_any(text, words):

    return any(
        w in text
        for w in words
    )

# =====================================================
# 🔥 SIGNALS
# =====================================================

GRAPH_SIGNALS = [

    "график",
    "функция",
    "plot",
    "graph",
    "ось",
    "кривая",
    "y=",
    "f(x)"
]

FORMULA_SIGNALS = [

    "формула",
    "уравнение",
    "formula",
    "equation"
]

TABLE_SIGNALS = [

    "таблица",
    "compare",
    "сравнение",
    "table"
]

SCENE_SIGNALS = [

    "diagram",
    "layout",
    "scene",
    "canvas",
    "схема",
    "пространство"
]

# =====================================================
# 🔥 SPATIAL INTENT
# =====================================================

def has_spatial_intent(
    text,
    cognition=None
):

    cognition = cognition or {}

    if cognition.get(
        "prefer_renderer"
    ):

        return True

    if cognition.get(
        "renderer_space_active"
    ):

        return True

    lower = normalize_lower(
        text
    )

    all_signals = (

        GRAPH_SIGNALS
        + FORMULA_SIGNALS
        + TABLE_SIGNALS
        + SCENE_SIGNALS
    )

    return contains_any(
        lower,
        all_signals
    )

# =====================================================
# 🔥 GRAPH NORMALIZATION
# =====================================================

def normalize_graph_expression(
    expression
):

    if not expression:
        return None

    expr = normalize_text(
        expression
    )

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
        "y=",
        ""
    )

    expr = expr.replace(
        "y =",
        ""
    )

    expr = expr.strip()

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

    allowed = re.fullmatch(
        r"[0-9xX\+\-\*\/\.\(\)\s_a-zA-Z]+",
        expr
    )

    if not allowed:

        safe_science_log(
            "GRAPH EXPRESSION BLOCKED"
        )

        return None

    return expr

# =====================================================
# 🔥 GRAPH DETECTION
# =====================================================

def detect_graph_expression(
    text
):

    text = normalize_text(
        text
    )

    if not text:
        return None

    y_match = re.search(
        r"y\s*=\s*([^\n]+)",
        text,
        re.IGNORECASE
    )

    if y_match:

        return normalize_graph_expression(
            y_match.group(1)
        )

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
# 🔥 SCENE TYPE
# =====================================================

def detect_scene_type(
    text,
    cognition=None
):

    lower = normalize_lower(
        text
    )

    cognition = cognition or {}

    graph_expr = detect_graph_expression(
        text
    )

    if graph_expr:
        return "graph"

    if contains_any(
        lower,
        TABLE_SIGNALS
    ):

        return "table"

    if contains_any(
        lower,
        FORMULA_SIGNALS
    ):

        return "formula"

    if contains_any(
        lower,
        SCENE_SIGNALS
    ):

        return "scene"

    if cognition.get(
        "renderer_space_active"
    ):

        return "scene"

    return None

# =====================================================
# 🔥 PAYLOAD BUILDERS
# =====================================================

def build_graph_payload(
    expression
):

    payload = {

        "type": "graph",

        "graph": expression,

        "renderer": "graph",

        "scene_type": "graph",

        "machine_channel":
            SCIENCE_MACHINE_CHANNEL
    }

    payload.update(
        RENDER_FLAGS
    )

    return payload


def build_formula_payload(
    formula
):

    payload = {

        "type": "formula",

        "formula": formula,

        "renderer": "formula",

        "scene_type": "formula",

        "machine_channel":
            SCIENCE_MACHINE_CHANNEL
    }

    payload.update(
        RENDER_FLAGS
    )

    return payload


def build_table_payload():

    payload = {

        "type": "table",

        "renderer": "table",

        "scene_type": "table",

        "machine_channel":
            SCIENCE_MACHINE_CHANNEL
    }

    payload.update(
        RENDER_FLAGS
    )

    return payload


def build_scene_payload(
    content
):

    payload = {

        "type": "scene",

        "content": content,

        "renderer": "scene",

        "scene_type": "generic",

        "machine_channel":
            SCIENCE_MACHINE_CHANNEL
    }

    payload.update(
        RENDER_FLAGS
    )

    return payload

# =====================================================
# 🔥 MAIN INTERPRETER
# =====================================================

def interpret_graph_request(
    text,
    cognition=None,
    semantic=None
):

    text = normalize_text(
        text
    )

    cognition = cognition or {}
    semantic = semantic or {}

    safe_science_log(
        f"INPUT: {text[:80]}"
    )

    if not text:
        return None

    # =================================================
    # 🔥 SPATIAL CHECK
    # =====================================================

    if not has_spatial_intent(
        text,
        cognition
    ):

        return None

    # =================================================
    # 🔥 SCENE TYPE
    # =====================================================

    scene_type = detect_scene_type(
        text,
        cognition
    )

    # =================================================
    # 🔥 GRAPH
    # =====================================================

    if scene_type == "graph":

        expr = detect_graph_expression(
            text
        )

        if expr:

            semantic[
                "renderer_payload_expected"
            ] = True

            semantic[
                "confirmed_renderer_artifact"
            ] = "graph"

            semantic[
                "renderer_first"
            ] = True

            safe_science_log(
                "GRAPH PAYLOAD BUILT"
            )

            return build_graph_payload(
                expr
            )

    # =================================================
    # 🔥 FORMULA
    # =====================================================

    if scene_type == "formula":

        expr = detect_graph_expression(
            text
        )

        if expr:

            semantic[
                "renderer_payload_expected"
            ] = True

            semantic[
                "confirmed_renderer_artifact"
            ] = "formula"

            semantic[
                "renderer_first"
            ] = True

            safe_science_log(
                "FORMULA PAYLOAD BUILT"
            )

            return build_formula_payload(
                expr
            )

    # =================================================
    # 🔥 TABLE
    # =====================================================

    if scene_type == "table":

        semantic[
            "renderer_payload_expected"
        ] = True

        semantic[
            "confirmed_renderer_artifact"
        ] = "table"

        semantic[
            "renderer_first"
        ] = True

        safe_science_log(
            "TABLE PAYLOAD BUILT"
        )

        return build_table_payload()

    # =================================================
    # 🔥 GENERIC SCENE
    # =====================================================

    if scene_type == "scene":

        semantic[
            "renderer_payload_expected"
        ] = True

        semantic[
            "confirmed_renderer_artifact"
        ] = "scene"

        semantic[
            "renderer_first"
        ] = True

        safe_science_log(
            "SCENE PAYLOAD BUILT"
        )

        return build_scene_payload(
            text
        )

    return None
