import re
import numpy as np
import matplotlib.pyplot as plt

from sympy import symbols, sympify, solve
from storage import get_user_plan

ADMIN_ID = 2016592532


class ScienceRoom:
    name = "science"

    # ===== ОПРЕДЕЛЕНИЕ =====
    def can_handle(self, text, context):
        t = text.lower()

        # 🔥 ЖЁСТКИЙ ТРИГГЕР (фикс)
        if "график" in t or "построй" in t:
            return True

        if "y=" in t or "y =" in t:
            return True

        if "=" in t or "реши" in t:
            return True

        return False

    # ===== ОБРАБОТКА =====
    async def handle(self, user_id, text, context, run_with_typing):
        plan = get_user_plan(user_id)

        if user_id == ADMIN_ID:
            plan = "premium"

        t = text.lower()

        # ===== FREE =====
        if plan == "free":
            if "=" in t or "реши" in t:
                result = self.solve_equation(text)

                if result:
                    return {
                        "type": "text",
                        "data": f"📐 Ответ:\n{result}\n\n⚡ Для графиков перейди на LITE"
                    }

            return {
                "type": "text",
                "data": "⚠️ Только простые решения доступны"
            }

        # ===== LITE / PREMIUM =====
        if "график" in t or "y" in t or "построй" in t:
            expr = self.extract_function(text)

            if expr:
                path = self.build_graph(expr)

                if path:
                    try:
                        with open(path, "rb") as f:
                            return {
                                "type": "image",
                                "data": f.read()  # 🔥 ФИКС
                            }
                    except Exception as e:
                        print("🔥 READ ERROR:", e)

        if "=" in t or "реши" in t:
            result = self.solve_equation(text)

            if result:
                return {
                    "type": "text",
                    "data": f"📐 Решение:\n{result}"
                }

        return {
            "type": "text",
            "data": "🧠 Не понял задачу, попробуй уточнить"
        }

    # ===== ИЗВЛЕЧЕНИЕ ФУНКЦИИ =====
    def extract_function(self, text):
        try:
            text = text.lower().replace("^", "**")

            match = re.search(r"y\s*=\s*(.+)", text)
            if match:
                return match.group(1)

            return None
        except Exception as e:
            print("🔥 EXTRACT ERROR:", e)
            return None

    # ===== ПОСТРОЕНИЕ ГРАФИКА =====
    def build_graph(self, expr):
        try:
            x = np.linspace(-10, 10, 200)

            def f(x):
                return eval(expr, {"x": x, "np": np, "__builtins__": {}})

            y = f(x)

            plt.figure()
            plt.plot(x, y)
            plt.title(f"y = {expr}")
            plt.grid()

            path = "graph.png"
            plt.savefig(path)
            plt.close()

            return path

        except Exception as e:
            print("🔥 GRAPH ERROR:", e)
            return None

    # ===== РЕШЕНИЕ =====
    def solve_equation(self, text):
        try:
            expr = text.lower().replace("реши", "").strip()
            expr = expr.replace("^", "**")

            x = symbols('x')

            if "=" in expr:
                left, right = expr.split("=")
                equation = sympify(left) - sympify(right)
            else:
                equation = sympify(expr)

            solution = solve(equation, x)

            return solution

        except Exception as e:
            print("🔥 SOLVE ERROR:", e)
            return None
