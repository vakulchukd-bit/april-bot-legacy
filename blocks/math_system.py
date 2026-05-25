# ==================== 🟢 BLOCK: MATH SYSTEM ====================

import re
import ast
import operator


# =====================================================
# 🧠 APRIL MATH SYSTEM
# =====================================================

"""
APRIL MATH SYSTEM
RENDERER-FIRST
CONTINUITY-SAFE

=====================================================

Этот модуль больше НЕ:

- telegram calculator trap;
- eval execution layer;
- formula trigger parser;
- graph blocker;
- regex hallucination;
- python execution fallback.

=====================================================

Этот модуль теперь:

- lightweight calculator;
- math intent detector;
- renderer-aware math router;
- graph-safe orchestrator;
- formula continuity bridge.

=====================================================

APRIL PRINCIPLES:

1. renderer-first
2. no eval()
3. no graph execution traps
4. no formula bypass chaos
5. calculator != graph renderer
6. spatial routing before execution
7. safe math parsing
8. continuity-safe behavior
"""

# =====================================================
# 🔥 SAFE OPERATORS
# =====================================================

SAFE_OPERATORS = {

    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


# =====================================================
# 🔥 GRAPH DETECTION
# =====================================================

def is_graph_request(
    text: str
) -> bool:

    t = (
        text or ""
    ).lower()

    graph_words = [

        "график",
        "нарисуй",
        "plot",
        "graph",
        "function",
        "функция",

        "y=",
        "y =",

        "f(x)",
        "sin(",
        "cos(",
        "tan(",

        "x^",
        "x²",
        "x +",
        "x -",
        "2x",
        "3x"
    ]

    return any(
        word in t
        for word in graph_words
    )


# =====================================================
# 🔥 FORMULA DETECTION
# =====================================================

def is_formula_request(
    text: str
) -> bool:

    t = (
        text or ""
    ).lower()

    formula_words = [

        "формула",
        "уравнение",
        "equation",
        "formula",

        "=",
        "^",
        "sqrt",
        "корень",

        "sin",
        "cos",
        "tan",
        "log"
    ]

    return any(
        word in t
        for word in formula_words
    )


# =====================================================
# 🔥 LIGHTWEIGHT CALCULATOR
# =====================================================

def is_math_request(
    text: str
) -> bool:

    if not text:
        return False

    # =================================================
    # 🔥 RENDERER-FIRST SAFETY
    # =====================================================

    if is_graph_request(text):
        return False

    # =================================================
    # 🔥 SIMPLE CALCULATOR ONLY
    # =====================================================

    t = text.lower()

    calculator_words = [

        "сколько будет",
        "вычисли",
        "посчитай",
        "calculate",
        "реши"
    ]

    has_math_symbols = any(
        symbol in t
        for symbol in [
            "+",
            "-",
            "*",
            "/"
        ]
    )

    has_numbers = bool(
        re.search(
            r"\d",
            t
        )
    )

    return (

        (
            has_math_symbols
            and has_numbers
        )

        or

        any(
            word in t
            for word in calculator_words
        )
    )


# =====================================================
# 🔥 SAFE AST CALCULATOR
# =====================================================

def safe_eval(
    node
):

    if isinstance(
        node,
        ast.Num
    ):

        return node.n

    if isinstance(
        node,
        ast.BinOp
    ):

        left = safe_eval(
            node.left
        )

        right = safe_eval(
            node.right
        )

        operator_type = type(
            node.op
        )

        if operator_type not in SAFE_OPERATORS:

            raise ValueError(
                "Unsupported operator"
            )

        return SAFE_OPERATORS[
            operator_type
        ](
            left,
            right
        )

    if isinstance(
        node,
        ast.UnaryOp
    ):

        operand = safe_eval(
            node.operand
        )

        operator_type = type(
            node.op
        )

        if operator_type not in SAFE_OPERATORS:

            raise ValueError(
                "Unsupported unary operator"
            )

        return SAFE_OPERATORS[
            operator_type
        ](
            operand
        )

    raise ValueError(
        "Unsafe expression"
    )


# =====================================================
# 🔥 SAFE EXPRESSION CLEANER
# =====================================================

def normalize_expression(
    text: str
):

    text = (
        text or ""
    )

    # =================================================
    # 🔥 HUMAN LANGUAGE CLEANUP
    # =====================================================

    replacements = {

        "умножить на": "*",
        "разделить на": "/",
        "плюс": "+",
        "минус": "-",

        "x": "*",
        "х": "*"
    }

    normalized = text.lower()

    for old, new in replacements.items():

        normalized = normalized.replace(
            old,
            new
        )

    # =================================================
    # 🔥 SAFE FILTER
    # =====================================================

    normalized = re.sub(
        r"[^0-9+\-*/(). ]",
        "",
        normalized
    )

    return normalized.strip()


# =====================================================
# 🔥 MAIN SOLVER
# =====================================================

def solve_math(
    text: str
) -> str:

    try:

        # =================================================
        # 🔥 RENDERER-FIRST BYPASS
        # =====================================================

        if is_graph_request(text):

            print(
                "🧠 GRAPH REQUEST BYPASS"
            )

            return (
                "[[graph:"
                + text.strip()
                + "]]"
            )

        # =================================================
        # 🔥 FORMULA SAFE BYPASS
        # =====================================================

        if is_formula_request(text):

            print(
                "🧠 FORMULA REQUEST BYPASS"
            )

            return text

        # =================================================
        # 🔥 NORMALIZE
        # =====================================================

        expr = normalize_expression(
            text
        )

        if not expr:

            return (
                "Не удалось распознать "
                "математическое выражение."
            )

        # =================================================
        # 🔥 AST PARSE
        # =====================================================

        parsed = ast.parse(
            expr,
            mode="eval"
        )

        result = safe_eval(
            parsed.body
        )

        # =================================================
        # 🔥 LARGE NUMBER SUPPORT
        # =====================================================

        if isinstance(
            result,
            float
        ):

            if result.is_integer():

                result = int(result)

        # =================================================
        # 🔥 RESPONSE
        # =====================================================

        return f"Ответ: {result}"

    except ZeroDivisionError:

        return (
            "⚠️ Деление на ноль невозможно."
        )

    except Exception as e:

        print(
            f"🔥 MATH SYSTEM ERROR: {e}"
        )

        return (
            "⚠️ Не удалось корректно "
            "обработать математический запрос."
        )
