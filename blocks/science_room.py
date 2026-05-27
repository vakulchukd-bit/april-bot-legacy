# ===============================
# 🔥 APRIL SCIENCE ROOM
# ===============================

"""
APRIL SCIENCE ROOM

Lightweight science capability layer.

ROLE:
- graph interpretation
- formula support
- equation solving
- renderer-safe math handling

NOT ROLE:
- orchestration
- routing authority
- scene ownership
- fallback control
"""

# ===============================
# 🔥 PATCH LOG
# ===============================

PATCH_LOG = []


def safe_patch_log(msg):

    try:

        print("SCIENCE:", msg)

        PATCH_LOG.append(msg)

    except:
        pass


# ===============================
# 🔥 IMPORTS
# ===============================

import re

from sympy import (
    symbols,
    sympify,
    solve,
    simplify
)

from blocks.science_interpreter import (
    interpret_graph_request
)


# ===============================
# 🔥 HELPERS
# ===============================

def safe_lower(text):

    try:
        return str(text).lower()
    except:
        return ""


# ===============================
# 🔥 CODE DETECTION
# ===============================

def detect_code_signal(text):

    t = safe_lower(text)

    patterns = [

        "import ",
        "from ",
        "class ",
        "def ",
        "async def",
        "return ",
        "const ",
        "let ",
        "var ",
        "export default",
        "=>",
        "</",
        "/>",
        "use client",
        "typescript",
        "javascript",
        "python"
    ]

    hits = 0

    for p in patterns:

        if p in t:
            hits += 1

    return hits >= 2


# ===============================
# 🔥 MATH DETECTION
# ===============================

def detect_math_signal(text):

    t = safe_lower(text)

    patterns = [

        "график",
        "функция",
        "формула",
        "уравнение",
        "реши",
        "вычисли",

        "y=",
        "y =",
        "f(x)",

        "sin(",
        "cos(",
        "tan(",

        "^2",
        "^3"
    ]

    for p in patterns:

        if p in t:
            return True

    equation = re.search(

        r"[0-9x]+\s*[\+\-\*/=]\s*[0-9x]+",

        t
    )

    return equation is not None


# ===============================
# 🔥 GRAPH INTENT
# ===============================

def detect_graph_intent(text):

    t = safe_lower(text)

    graph_words = [

        "построй",
        "график",
        "plot",
        "graph",
        "визуально",
        "нарисуй"
    ]

    return any(
        w in t
        for w in graph_words
    )


# ===============================
# 🔥 SCIENCE ROOM
# ===============================

class ScienceRoom:

    name = "science"

    # ==========================================
    # 🔥 ROUTING
    # ==========================================

    def can_handle(
        self,
        text,
        context
    ):

        t = safe_lower(text)

        if detect_code_signal(t):

            safe_patch_log(
                "CODE -> PASS"
            )

            return False

        semantic = context.get(
            "semantic",
            {}
        )

        if semantic.get(
            "room"
        ) == "science":

            return True

        return detect_math_signal(
            t
        )

    # ==========================================
    # 🔥 EVALUATION
    # ==========================================

    def evaluate(
        self,
        text,
        context
    ):

        t = safe_lower(text)

        score = 0.0

        semantic = context.get(
            "semantic",
            {}
        )

        cognition = context.get(
            "cognition",
            {}
        )

        if semantic.get(
            "room"
        ) == "science":

            score += 1.5

        if detect_math_signal(t):

            score += 1.2

        if detect_graph_intent(t):

            score += 0.8

        if cognition.get(
            "wants_visual",
            0.0
        ) >= 0.5:

            score += 0.3

        return score

    # ==========================================
    # 🔥 HANDLE
    # ==========================================

    async def handle(

        self,
        user_id,
        text,
        context,
        run_with_typing
    ):

        t = safe_lower(text)

        state = context.get(
            "state",
            {}
        )

        cognition = context.get(
            "cognition",
            {}
        )

        semantic = context.get(
            "semantic",
            {}
        )

        safe_patch_log(
            f"SCIENCE ENTER: {t[:60]}"
        )

        # ======================================
        # 🔥 CODE SAFETY
        # ======================================

        if detect_code_signal(t):

            safe_patch_log(
                "CODE RELEASE"
            )

            return None

        # ======================================
        # 🔥 RENDERER PAYLOAD
        # ======================================

        renderer_payload = (
            interpret_graph_request(
                text,
                cognition,
                semantic
            )
        )

        if renderer_payload:

            state["last_math"] = {

                "type":
                    renderer_payload.get(
                        "type"
                    ),

                "payload":
                    renderer_payload
            }

            safe_patch_log(
                "RENDERER PAYLOAD"
            )

            return renderer_payload

        # ======================================
        # 🔥 EQUATION SOLVER
        # ======================================

        solution = self.solve_equation(
            text
        )

        if solution:

            return {

                "type": "text",

                "data": solution
            }

        # ======================================
        # 🔥 RELEASE
        # ======================================

        safe_patch_log(
            "SCIENCE RELEASE"
        )

        return None

    # ==========================================
    # 🔥 EQUATION SOLVER
    # ==========================================

    def solve_equation(
        self,
        text
    ):

        try:

            expr = text.replace(
                " ",
                ""
            )

            expr = re.sub(

                r"(\d)(x)",

                r"\1*\2",

                expr
            )

            if "=" not in expr:
                return None

            left, right = expr.split("=")

            x = symbols("x")

            equation = simplify(

                sympify(left)
                - sympify(right)
            )

            solutions = solve(
                equation,
                x
            )

            if not solutions:
                return None

            return (

                "📐 Решение:\n"
                + "\n".join(
                    [
                        f"x = {s}"
                        for s in solutions
                    ]
                )
            )

        except Exception as e:

            safe_patch_log(
                f"SOLVE ERROR: {e}"
            )

            return None
