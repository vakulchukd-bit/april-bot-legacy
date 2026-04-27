import re
from sympy import symbols, sympify, solveset, S, sin, cos, tan, pi


class TrigRoom:
    name = "trigonometry"

    # ===== 🎯 ОПРЕДЕЛЕНИЕ =====
    def can_handle(self, text, context):
        t = text.lower()

        return any(w in t for w in [
            "sin", "cos", "tan",
            "синус", "косинус", "тангенс"
        ])

    # ===== 🔥 ВАЛИДАТОР (ПРИОРИТЕТ) =====
    def evaluate(self, text, context):
        t = text.lower()

        if any(w in t for w in ["sin", "cos", "tan"]):
            return 9.5  # чуть ниже 10 (math force), но выше всех

        return 0.0

    # ===== 🧠 ОБРАБОТКА =====
    async def handle(self, user_id, text, context, run_with_typing):
        try:
            expr = self.extract_expression(text)

            if not expr:
                return {"type": "skip"}

            x = symbols('x')

            left, right = expr.split("=")

            equation = sympify(left) - sympify(right)

            solutions = solveset(equation, x, domain=S.Reals)

            if not solutions:
                return {"type": "text", "data": "⚠️ Нет решений"}

            return {
                "type": "text",
                "data": f"📐 Решение:\n{expr}\n\nx ∈ {solutions}"
            }

        except Exception as e:
            print("🔥 TRIG ERROR:", e)
            return {"type": "skip"}

    # ===== 🔧 ПАРСИНГ =====
    def extract_expression(self, text):
        t = text.lower()

        t = t.replace("^", "**")
        t = t.replace(":", " ")

        match = re.search(r'([a-z()\d\+\-\*/\.\s]+=[a-z()\d\+\-\*/\.\s]+)', t)

        if match:
            return match.group(1)

        return None
