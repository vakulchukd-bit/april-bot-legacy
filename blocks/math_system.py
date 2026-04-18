# ==================== 🟢 BLOCK: MATH SYSTEM ====================

def is_math_request(text: str) -> bool:
    t = text.lower()

    triggers = [
        "+", "-", "*", "/", "=",
        "сколько будет",
        "реши",
        "вычисли",
        "посчитай",
        "формула"
    ]

    return any(word in t for word in triggers)


def solve_math(text: str) -> str:
    try:
        allowed = "0123456789+-*/(). "
        expr = "".join(c for c in text if c in allowed)

        if not expr.strip():
            return "Не удалось распознать выражение"

        result = eval(expr)
        return f"Ответ: {result}"

    except Exception:
        return "Не смог решить, попробуй переформулировать"
