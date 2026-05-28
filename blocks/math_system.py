# ==================== 🟢 BLOCK: MATH SYSTEM ====================

import re
import ast
import time
import operator

# =====================================================
# 🧠 APRIL MATH SYSTEM
# =====================================================

"""
APRIL_FILE_ID:
APRIL_MATH_SYSTEM

ROLE:
RENDERER_SAFE_MATH_BRIDGE

INPUT:
USER_TEXT
SEMANTIC_STATE
ACTIVE_FLOW
RENDERER_CONTEXT

OUTPUT:
MATH_RESULT
GRAPH_BYPASS_SIGNAL
FORMULA_CONTINUITY_PAYLOAD
RENDERER_SAFE_RESPONSE

=====================================================

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
# 🔥 MACHINE CHANNELS
# =====================================================

INPUT_MACHINE_CHANNEL = {

    "source":
        "semantic_core",

    "type":
        "math_input",

    "isolated":
        True
}

OUTPUT_MACHINE_CHANNEL = {

    "target":
        "renderer_or_executor",

    "type":
        "math_output",

    "isolated":
        True
}

# =====================================================
# 🔥 PATCH LOGGING
# =====================================================

PATCH_LOG = []

MAX_PATCH_LOGS = 120


def safe_patch_log(message):

    try:

        print(
            "MATH PATCH:",
            message
        )

        PATCH_LOG.append({

            "timestamp":
                time.time(),

            "message":
                message,

            "file_id":
                "APRIL_MATH_SYSTEM",

            "machine_only":
                True
        })

        if len(PATCH_LOG) > MAX_PATCH_LOGS:

            PATCH_LOG.pop(0)

    except Exception:
        pass

# =====================================================
# 🔥 SAFE OPERATORS
# =====================================================

SAFE_OPERATORS = {

    ast.Add:
        operator.add,

    ast.Sub:
        operator.sub,

    ast.Mult:
        operator.mul,

    ast.Div:
        operator.truediv,

    ast.Pow:
        operator.pow,

    ast.USub:
        operator.neg,
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

    detected = any(
        word in t
        for word in graph_words
    )

    if detected:

        safe_patch_log(
            "GRAPH REQUEST DETECTED"
        )

    return detected

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

    detected = any(
        word in t
        for word in formula_words
    )

    if detected:

        safe_patch_log(
            "FORMULA REQUEST DETECTED"
        )

    return detected

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

    detected = (

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

    if detected:

        safe_patch_log(
            "LIGHTWEIGHT MATH REQUEST"
        )

    return detected

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

    normalized = normalized.strip()

    safe_patch_log(
        f"NORMALIZED EXPRESSION: {normalized}"
    )

    return normalized

# =====================================================
# 🔥 MACHINE RESULT PACKAGE
# =====================================================

def build_math_payload(
    mode,
    content,
    renderer_safe=True
):

    return {

        "mode":
            mode,

        "content":
            content,

        "renderer_safe":
            renderer_safe,

        "continuity_safe":
            True,

        "machine_only":
            True,

        "orchestration_ready":
            True,

        "timestamp":
            time.time()
    }

# =====================================================
# 🔥 MAIN SOLVER
# =====================================================

def solve_math(
    text: str
) -> str:

    try:

        safe_patch_log(
            f"MATH REQUEST: {str(text)[:80]}"
        )

        # =================================================
        # 🔥 RENDERER-FIRST BYPASS
        # =====================================================

        if is_graph_request(text):

            print(
                "🧠 GRAPH REQUEST BYPASS"
            )

            payload = build_math_payload(

                mode="graph",

                content=text.strip()
            )

            safe_patch_log(
                "GRAPH PAYLOAD CREATED"
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

            payload = build_math_payload(

                mode="formula",

                content=text.strip()
            )

            safe_patch_log(
                "FORMULA PAYLOAD CREATED"
            )

            return text

        # =================================================
        # 🔥 NORMALIZE
        # =====================================================

        expr = normalize_expression(
            text
        )

        if not expr:

            safe_patch_log(
                "EMPTY EXPRESSION"
            )

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

        safe_patch_log(
            f"MATH RESULT: {result}"
        )

        # =================================================
        # 🔥 RESPONSE
        # =====================================================

        return f"Ответ: {result}"

    except ZeroDivisionError:

        safe_patch_log(
            "DIVISION BY ZERO"
        )

        return (
            "⚠️ Деление на ноль невозможно."
        )

    except Exception as e:

        print(
            f"🔥 MATH SYSTEM ERROR: {e}"
        )

        safe_patch_log(
            f"MATH ERROR: {str(e)}"
        )

        return (
            "⚠️ Не удалось корректно "
            "обработать математический запрос."
        )
