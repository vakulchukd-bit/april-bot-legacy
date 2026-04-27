import re
import numpy as np
import matplotlib.pyplot as plt

from sympy import symbols, sympify, solve, solveset, S, simplify
from storage import get_user_plan

ADMIN_ID = 2016592532


class ScienceRoom:
    name = "science"

    # ===== УМНЫЙ ДЕТЕКТ =====
    def is_math_expression(self, text):
        t = text.lower()

        # есть структура выражения
        if re.search(r'[0-9x\)\(]+\s*[\+\-\*/=]\s*[0-9x\)\(]+', t):
            return True

        # есть "=" и буквы
        if "=" in t and re.search(r'[a-z]', t):
            return True

        # trig
        if any(w in t for w in ["sin", "cos", "tan", "синус", "косинус"]):
            return True

        return False

    def can_handle(self, text, context):
        t = text.lower()

        if self.is_math_expression(text):
            return True

        if "график" in t or "y=" in t:
            return True

        return False

    def evaluate(self, text, context):
        if context.get("task_type") == "math":
            return 10.0

        if self.can_handle(text, context):
            return 2.0

        return 0.0

    async def handle(self, user_id, text, context, run_with_typing):
        plan = get_user_plan(user_id)

        if user_id == ADMIN_ID:
            plan = "premium"

        t = text.lower()

        # ===== таблица =====
        if "таблица" in t and "умнож" in t:
            path = self.build_multiplication_table()
            if path:
                with open(path, "rb") as f:
                    return {"type": "image", "data": f.read()}

        # ===== график =====
        if "график" in t or "y=" in t:
            expr = self.extract_function(text)

            if expr:
                path = self.build_graph(expr)
                if path:
                    with open(path, "rb") as f:
                        return {"type": "image", "data": f.read()}

        # ===== решение =====
        if self.is_math_expression(text):
            result = self.solve_equation(text)

            if result:
                return {"type": "text", "data": f"📐 Решение:\n{result}"}

        # 🔥 ВАЖНО
        return {"type": "skip"}

    # ===== ПАРСИНГ =====
    def extract_math_expression(self, text):
        t = text.lower()
        t = t.replace("²", "**2")
        t = t.replace("^", "**")

        match = re.search(r'([-+*/().\d x]+=[-+*/().\d x]+)', t)
        if match:
            return match.group(1)

        return t

    def extract_function(self, text):
        text = text.lower()
        text = text.replace("^", "**")

        match = re.search(r"y\s*=\s*(.+)", text)
        return match.group(1) if match else None

    # ===== ГРАФИК =====
    def build_graph(self, expr):
        try:
            x = np.linspace(-10, 10, 200)
            y = eval(expr, {"x": x, "np": np, "__builtins__": {}})

            plt.figure()
            plt.plot(x, y)
            plt.grid()

            path = "graph.png"
            plt.savefig(path)
            plt.close()

            return path
        except:
            return None

    def build_multiplication_table(self):
        data = np.outer(range(1, 11), range(1, 11))

        plt.figure()
        plt.imshow(data)
        plt.colorbar()

        path = "graph.png"
        plt.savefig(path)
        plt.close()

        return path

    # ===== РЕШЕНИЕ =====
    def solve_equation(self, text):
        try:
            expr = self.extract_math_expression(text)

            expr = re.sub(r'(\d)(x)', r'\1*\2', expr)

            x = symbols('x')

            if "=" in expr:
                left, right = expr.split("=")
                equation = simplify(sympify(left) - sympify(right))

                # 🔥 trig и сложные случаи
                solutions = solveset(equation, x, domain=S.Reals)

                if not solutions:
                    return "⚠️ Нет решения"

                return f"x ∈ {solutions}"

            else:
                equation = simplify(sympify(expr))
                solutions = solve(equation, x)

                return f"x = {solutions}"

        except Exception as e:
            print("🔥 SOLVE ERROR:", e)
            return None
