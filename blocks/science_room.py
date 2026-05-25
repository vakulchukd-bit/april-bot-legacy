# ===============================
# 🔥 APRIL SCIENCE ROOM
# ===============================

"""
APRIL SCIENCE ROOM

ROLE:
- math capability;
- graph capability;
- formula capability;
- scientific helper.

NOT ROLE:
- orchestration;
- final authority;
- fallback engine;
- scene ownership;
- continuation controller;
- modality dictator.

SCIENCE ROOM PRINCIPLES:

1. calm participation
2. no scene hijacking
3. no hard fallback
4. no aggressive routing
5. no modality ownership
6. April decides final scene
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
import math
import numpy as np

from sympy import (
    symbols,
    sympify,
    solve,
    simplify
)


# ===============================
# 🔥 HELPERS
# ===============================

def safe_lower(text):

    try:
        return str(text).lower()
    except:
        return ""


def detect_code_signal(text):

    t = safe_lower(text)

    code_patterns = [

        "import ",
        "from ",
        "class ",
        "def ",
        "async def",
        "return ",
        "print(",
        "console.log",
        "export default",
        "function(",
        "function ",
        "const ",
        "let ",
        "var ",
        "=>",
        "</",
        "/>",
        "{",
        "}",
        "use client",
        "typescript",
        "javascript",
        "python"
    ]

    hits = 0

    for pattern in code_patterns:

        if pattern in t:
            hits += 1

    return hits >= 2


def detect_math_signal(text):

    t = safe_lower(text)

    signals = 0

    math_patterns = [

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
        "log(",

        "x**",
        "^2",
        "^3"
    ]

    for pattern in math_patterns:

        if pattern in t:
            signals += 1

    equation_pattern = re.search(

        r"[0-9x]+\s*[\+\-\*/=]\s*[0-9x]+",

        t
    )

    if equation_pattern:
        signals += 1

    return signals >= 1


def detect_graph_intent(text):

    t = safe_lower(text)

    graph_words = [

        "построй",
        "покажи",
        "визуально",
        "нарисуй",
        "график",
        "как выглядит",
        "plot",
        "graph"
    ]

    hits = 0

    for word in graph_words:

        if word in t:
            hits += 1

    return hits >= 1


# ===============================
# 🔥 SCIENCE ROOM
# ===============================

class ScienceRoom:

    name = "science"

    # ==========================================
    # 🔥 CALM ROUTING
    # ==========================================

    def can_handle(self, text, context):

        t = safe_lower(text)

        # ======================================
        # 🔥 CODE PROTECTION
        # ======================================

        if detect_code_signal(t):

            safe_patch_log(
                "CODE DETECTED -> PASS"
            )

            return False

        # ======================================
        # 🔥 SEMANTIC HINT
        # ======================================

        semantic = context.get(
            "semantic",
            {}
        )

        if semantic.get(
            "room"
        ) == "science":

            return True

        # ======================================
        # 🔥 MATH DETECTION
        # ======================================

        if detect_math_signal(t):

            return True

        return False

    # ==========================================
    # 🔥 CALM EVALUATION
    # ==========================================

    def evaluate(self, text, context):

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

        # ======================================
        # 🔥 SEMANTIC SUPPORT
        # ======================================

        if semantic.get(
            "room"
        ) == "science":

            score += 2.0

        # ======================================
        # 🔥 GRAPH INTENT
        # ======================================

        if detect_graph_intent(t):

            score += 2.0

        # ======================================
        # 🔥 MATH SIGNAL
        # ======================================

        if detect_math_signal(t):

            score += 1.5

        # ======================================
        # 🔥 VISUAL SUPPORT
        # ======================================

        if cognition.get(
            "wants_visual",
            0.0
        ) >= 0.5:

            score += 0.5

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

        safe_patch_log(
            f"ENTER: {t[:80]}"
        )

        # ======================================
        # 🔥 CODE SAFETY
        # ======================================

        if detect_code_signal(t):

            safe_patch_log(
                "CODE -> RELEASE"
            )

            return None

        # ======================================
        # 🔥 FUNCTION EXTRACTION
        # ======================================

        expr = self.extract_function(
            t
        )

        # ======================================
        # 🔥 CONTINUATION SUPPORT
        # ======================================

        if not expr:

            last_math = state.get(
                "last_math"
            )

            if last_math:

                if detect_graph_intent(t):

                    expr = last_math.get(
                        "expr"
                    )

        # ======================================
        # 🔥 FUNCTION RESULT
        # ======================================

        if expr:

            valid, error = (
                self.validate_expression(
                    expr
                )
            )

            if not valid:

                safe_patch_log(
                    f"INVALID EXPR: {error}"
                )

                return None

            state["last_math"] = {

                "type": "function",

                "expr": expr
            }

            safe_patch_log(
                f"FUNCTION: {expr}"
            )

            return {

                "type": "function",

                "function": expr,

                "range": [-10, 10],

                "meta": {

                    "renderer":
                        "graph_block",

                    "source":
                        "science_room"
                }
            }

        # ======================================
        # 🔥 EQUATION SOLVING
        # ======================================

        solution = self.solve_equation(
            t
        )

        if solution:

            return {

                "type": "text",

                "data": solution
            }

        # ======================================
        # 🔥 CALM RELEASE
        # ======================================

        safe_patch_log(
            "NOT SCIENCE -> RELEASE"
        )

        return None

    # ==========================================
    # 🔥 FUNCTION EXTRACTION
    # ==========================================

    def extract_function(self, text):

        try:

            text = text.replace(
                "^",
                "**"
            )

            replacements = {

                "sin": "np.sin",
                "cos": "np.cos",
                "tan": "np.tan",
                "log": "np.log",
                "ln": "np.log"
            }

            for old, new in replacements.items():

                text = text.replace(
                    old,
                    new
                )

            # ==================================
            # y = ...
            # ==================================

            match = re.search(

                r"y\s*=\s*(.+)",

                text
            )

            if match:

                expr = match.group(1).strip()

                return expr

            # ==================================
            # f(x)=...
            # ==================================

            match = re.search(

                r"f\s*\(\s*x\s*\)\s*=\s*(.+)",

                text
            )

            if match:

                expr = match.group(1).strip()

                return expr

            return None

        except Exception as e:

            safe_patch_log(
                f"EXTRACT ERROR: {e}"
            )

            return None

    # ==========================================
    # 🔥 VALIDATION
    # ==========================================

    def validate_expression(

        self,
        expr
    ):

        try:

            x = np.linspace(
                -10,
                10,
                10
            )

            eval(

                expr,

                {
                    "x": x,
                    "np": np,
                    "__builtins__": {}
                }
            )

            return True, None

        except Exception as e:

            return False, str(e)

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

            x = symbols("x")

            if "=" not in expr:
                return None

            left, right = expr.split("=")

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
