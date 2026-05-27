import re

from sympy import (
    symbols,
    sympify,
    solveset,
    S,
    sin,
    cos,
    tan,
    pi
)


# =====================================================
# 🧠 APRIL TRIG ROOM
# =====================================================

"""
APRIL TRIG ROOM

ROLE:
- trigonometric understanding;
- trig equation solving;
- trig graph support;
- renderer-compatible math payloads.

NOT ROLE:
- orchestration;
- hard routing;
- scene ownership;
- renderer replacement;
- dialogue control.

APRIL PRINCIPLES:
1. renderer-first
2. continuity-safe
3. structured payloads
4. no trigger chaos
5. no scene hijacking
6. machine-readable output
"""


# =====================================================
# 🔥 PATCH LOG
# =====================================================

PATCH_LOG = []


def safe_patch_log(msg):

    try:

        print("TRIG:", msg)

        PATCH_LOG.append(msg)

    except:
        pass


# =====================================================
# 🔥 HELPERS
# =====================================================

def safe_lower(text):

    try:
        return str(text).lower().strip()

    except:
        return ""


def contains_any(
    text,
    words
):

    return any(
        word in text
        for word in words
    )


# =====================================================
# 🔥 MACHINE SIGNALS
# =====================================================

TRIG_KEYWORDS = [

    "sin(",
    "cos(",
    "tan(",

    "sin x",
    "cos x",
    "tan x",

    "синус",
    "косинус",
    "тангенс",

    "тригонометр"
]

GRAPH_WORDS = [

    "график",
    "построй",
    "plot",
    "graph",
    "визуально",
    "функция"
]

FORMULA_WORDS = [

    "формула",
    "уравнение",
    "реши",
    "решение"
]


# =====================================================
# 🔥 SAFE EXPRESSION DETECTION
# =====================================================

def detect_trig_expression(text):

    t = safe_lower(text)

    if not contains_any(
        t,
        TRIG_KEYWORDS
    ):

        return None

    equation_match = re.search(

        r'([a-z0-9\(\)\+\-\*/\.\s=]+)',

        t
    )

    if not equation_match:
        return None

    expr = equation_match.group(1)

    expr = expr.replace(
        "^",
        "**"
    )

    expr = expr.strip()

    return expr


# =====================================================
# 🔥 RENDERER DETECTION
# =====================================================

def wants_renderer(
    text,
    context
):

    semantic = context.get(
        "semantic",
        {}
    )

    cognition = context.get(
        "cognition",
        {}
    )

    t = safe_lower(text)

    if semantic.get(
        "prefer_renderer"
    ):

        return True

    if cognition.get(
        "prefer_renderer"
    ):

        return True

    if contains_any(
        t,
        GRAPH_WORDS
    ):

        return True

    return False


# =====================================================
# 🔥 CONTINUITY
# =====================================================

def trig_continuation_active(
    context
):

    state = context.get(
        "state",
        {}
    )

    active_flow = state.get(
        "active_flow"
    )

    if not active_flow:
        return False

    flow_type = active_flow.get(
        "type"
    )

    return flow_type in [

        "science",
        "math",
        "graph",
        "formula",
        "trigonometry"
    ]


# =====================================================
# 🔥 VALIDATION
# =====================================================

def validate_expression(expr):

    if not expr:
        return False

    allowed = re.fullmatch(

        r"[a-zA-Z0-9\(\)\+\-\*/=\.\s,_]+",

        expr
    )

    return bool(allowed)


# =====================================================
# 🧠 TRIG ROOM
# =====================================================

class TrigRoom:

    name = "trigonometry"

    # =================================================
    # 🔥 CAN HANDLE
    # =====================================================

    def can_handle(
        self,
        text,
        context
    ):

        expr = detect_trig_expression(
            text
        )

        if expr:
            return True

        if trig_continuation_active(
            context
        ):

            return True

        return False

    # =================================================
    # 🔥 EVALUATE
    # =====================================================

    def evaluate(
        self,
        text,
        context
    ):

        score = 0.0

        expr = detect_trig_expression(
            text
        )

        if expr:
            score += 6.5

        if wants_renderer(
            text,
            context
        ):

            score += 1.8

        if trig_continuation_active(
            context
        ):

            score += 1.2

        semantic = context.get(
            "semantic",
            {}
        )

        if semantic.get(
            "room"
        ) == "science":

            score += 1.0

        return score

    # =================================================
    # 🔥 HANDLE
    # =====================================================

    async def handle(

        self,
        user_id,
        text,
        context,
        run_with_typing
    ):

        try:

            semantic = context.get(
                "semantic",
                {}
            )

            state = context.get(
                "state",
                {}
            )

            expr = detect_trig_expression(
                text
            )

            if not expr:

                last_trig = state.get(
                    "last_trig_expression"
                )

                if last_trig:

                    if trig_continuation_active(
                        context
                    ):

                        expr = last_trig

            if not expr:

                return {

                    "type": "skip"
                }

            if not validate_expression(
                expr
            ):

                safe_patch_log(
                    "INVALID EXPR"
                )

                return {

                    "type": "skip"
                }

            state[
                "last_trig_expression"
            ] = expr

            # =================================================
            # 🔥 RENDERER-FIRST
            # =====================================================

            if wants_renderer(
                text,
                context
            ):

                safe_patch_log(
                    "RENDERER PAYLOAD"
                )

                return {

                    "type":
                        "graph_payload",

                    "renderer":
                        "april_graph",

                    "scene_type":
                        "trig_graph",

                    "expression":
                        expr,

                    "renderer_mode":
                        "spatial",

                    "spatial_object":
                        True,

                    "scene_ready":
                        True,

                    "renderer_first":
                        True,

                    "avoid_generation":
                        True,

                    "continuity_safe":
                        True,

                    "source":
                        "trig_room"
                }

            # =================================================
            # 🔥 EQUATION SOLVING
            # =====================================================

            if "=" not in expr:

                return {

                    "type":
                        "formula_payload",

                    "formula":
                        expr,

                    "scene_type":
                        "trig_formula",

                    "renderer":
                        "april_formula",

                    "renderer_mode":
                        "spatial",

                    "source":
                        "trig_room"
                }

            x = symbols("x")

            left, right = expr.split("=")

            equation = (

                sympify(left)
                - sympify(right)
            )

            solutions = solveset(

                equation,
                x,
                domain=S.Reals
            )

            if solutions == S.EmptySet:

                return {

                    "type":
                        "math_result",

                    "status":
                        "empty_solution",

                    "expression":
                        expr,

                    "content":
                        "⚠️ Нет решений"
                }

            safe_patch_log(
                f"SOLVED: {expr}"
            )

            return {

                "type":
                    "math_result",

                "expression":
                    expr,

                "solutions":
                    str(solutions),

                "scene_type":
                    "trig_solution",

                "renderer":
                    "april_formula",

                "renderer_mode":
                    "spatial",

                "structured":
                    True,

                "continuity_safe":
                    True,

                "source":
                    "trig_room"
            }

        except Exception as e:

            print(
                "🔥 TRIG ERROR:",
                e
            )

            return {

                "type": "skip"
            }
