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

from blocks.room_protocol import Room


# =====================================================
# 🧠 APRIL TRIG ROOM
# =====================================================

"""
APRIL TRIG ROOM

WEB-FIRST LIGHTWEIGHT TRIGONOMETRY LAYER

ROLE:
- trigonometric interpretation
- trig equation solving
- renderer-safe graph payloads
- continuation-safe math flow
- structured math transport
- web-space compatible responses

NOT ROLE:
- orchestration authority
- routing ownership
- renderer replacement
- presentation formatting
- provider execution
- cognition control

=====================================================
🔥 APRIL PRINCIPLES
=====================================================

1. renderer-first
2. continuity-safe
3. structured payloads
4. lightweight execution
5. no scene hijacking
6. no recursive routing
7. web-space compatible
8. machine-readable output
9. provider-safe math execution
10. compact reasoning
"""

# =====================================================
# 🔥 FILE ID
# =====================================================

APRIL_FILE_ID = "APRIL_TRIG_ROOM"

APRIL_ROOM_VERSION = "WEB_STABILIZED"

# =====================================================
# 🔥 MACHINE FLAGS
# =====================================================

TRIG_ROOM_FLAGS = {

    "renderer_first": True,

    "continuity_safe": True,

    "trajectory_safe": True,

    "provider_safe": True,

    "web_ready": True,

    "botru_compatible": True,

    "structured_output": True,

    "lightweight_reasoning": True,

    "anti_trigger_behavior": True,

    "avoid_generation_fallback": True
}

# =====================================================
# 🔥 PATCH LOG
# =====================================================

PATCH_LOG = []


def safe_patch_log(msg):

    try:

        print(
            "TRIG ROOM:",
            msg
        )

        PATCH_LOG.append(msg)

    except:
        pass


# =====================================================
# 🔥 HELPERS
# =====================================================

def safe_lower(text):

    try:

        return str(
            text or ""
        ).lower().strip()

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

    "тригонометр",

    "cot(",
    "sec(",
    "csc("
]

GRAPH_WORDS = [

    "график",
    "построй",
    "plot",
    "graph",
    "визуально",
    "функция",
    "curve",
    "ось"
]

FORMULA_WORDS = [

    "формула",
    "уравнение",
    "реши",
    "решение",
    "вычисли"
]

CONTINUATION_WORDS = [

    "да",
    "ага",
    "дальше",
    "продолжай",
    "ещё",
    "еще",
    "покажи",
    "построй",
    "вот",
    "это"
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

        r'([a-z0-9\(\)\+\-\*/\.\s=,_]+)',

        t
    )

    if not equation_match:

        return None

    expr = equation_match.group(1)

    expr = expr.replace(
        "^",
        "**"
    )

    expr = expr.replace(
        "π",
        "pi"
    )

    expr = expr.strip()

    return expr


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
        "trigonometry",
        "renderer_space"
    ]


# =====================================================
# 🔥 CONTINUATION TEXT
# =====================================================

def is_soft_trig_continuation(
    text
):

    t = safe_lower(text)

    if len(t) > 42:

        return False

    return contains_any(
        t,
        CONTINUATION_WORDS
    )


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

    if semantic.get(
        "render_intent"
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
# 🔥 RENDERER PAYLOAD
# =====================================================

def build_graph_payload(expr):

    payload = {

        "type":
            "graph",

        "graph":
            expr,

        "renderer":
            "april_graph",

        "scene_type":
            "trig_graph",

        "renderer_mode":
            "spatial",

        "spatial_object":
            True,

        "scene_ready":
            True,

        "expression":
            expr,

        "source":
            "trig_room"
    }

    payload.update(
        TRIG_ROOM_FLAGS
    )

    return payload


def build_formula_payload(expr):

    payload = {

        "type":
            "formula",

        "formula":
            expr,

        "renderer":
            "april_formula",

        "scene_type":
            "trig_formula",

        "renderer_mode":
            "spatial",

        "source":
            "trig_room"
    }

    payload.update(
        TRIG_ROOM_FLAGS
    )

    return payload


def build_solution_payload(
    expr,
    solutions
):

    payload = {

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

        "source":
            "trig_room"
    }

    payload.update(
        TRIG_ROOM_FLAGS
    )

    return payload


# =====================================================
# 🧠 TRIG ROOM
# =====================================================

class TrigRoom(Room):

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

        if (

            trig_continuation_active(
                context
            )

            and is_soft_trig_continuation(
                text
            )
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
        ) in [

            "science",
            "trigonometry"
        ]:

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

            # =============================================
            # 🔥 CONTINUATION RESTORE
            # =============================================

            if not expr:

                last_trig = state.get(
                    "last_trig_expression"
                )

                if (

                    last_trig

                    and trig_continuation_active(
                        context
                    )
                ):

                    expr = last_trig

            if not expr:

                return {

                    "type": "skip"
                }

            # =============================================
            # 🔥 VALIDATION
            # =============================================

            if not validate_expression(
                expr
            ):

                safe_patch_log(
                    "INVALID EXPR"
                )

                return {

                    "type": "skip"
                }

            # =============================================
            # 🔥 SAVE STATE
            # =============================================

            state[
                "last_trig_expression"
            ] = expr

            state[
                "last_math_expression"
            ] = expr

            # =============================================
            # 🔥 SEMANTIC FLAGS
            # =============================================

            semantic[
                "renderer_payload_expected"
            ] = True

            semantic[
                "confirmed_renderer_artifact"
            ] = "formula"

            semantic[
                "math_scene_active"
            ] = True

            # =============================================
            # 🔥 GRAPH / RENDERER
            # =============================================

            if wants_renderer(
                text,
                context
            ):

                safe_patch_log(
                    "GRAPH PAYLOAD"
                )

                return build_graph_payload(
                    expr
                )

            # =============================================
            # 🔥 FORMULA ONLY
            # =============================================

            if "=" not in expr:

                safe_patch_log(
                    "FORMULA PAYLOAD"
                )

                return build_formula_payload(
                    expr
                )

            # =============================================
            # 🔥 EQUATION SOLVING
            # =============================================

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

            # =============================================
            # 🔥 EMPTY SOLUTION
            # =============================================

            if solutions == S.EmptySet:

                return {

                    "type":
                        "math_result",

                    "status":
                        "empty_solution",

                    "expression":
                        expr,

                    "content":
                        "⚠️ Нет решений",

                    "source":
                        "trig_room",

                    "continuity_safe":
                        True
                }

            safe_patch_log(
                f"SOLVED: {expr}"
            )

            return build_solution_payload(

                expr,
                solutions
            )

        except Exception as e:

            print(
                "🔥 TRIG ROOM ERROR:",
                e
            )

            return {

                "type": "skip"
            }


# =====================================================
# 🔥 ROOM EXPORT
# =====================================================

TRIG_ROOM_EXPORT = {

    "id":
        APRIL_FILE_ID,

    "version":
        APRIL_ROOM_VERSION,

    "room":
        "trigonometry",

    "renderer_safe":
        True,

    "web_ready":
        True,

    "machine_readable":
        True
}
