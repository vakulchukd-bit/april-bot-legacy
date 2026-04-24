import re
import numpy as np
import matplotlib.pyplot as plt

from sympy import symbols, sympify, solve


class ScienceRoom:
    name = "science"

    # ===== ОПРЕДЕЛЕНИЕ =====
    def can_handle(self, text, context):
        t = text.lower()

        triggers = [
            "график", "функция", "y =", "x^",
            "реши", "уравнение", "=",
            "sin", "cos", "tan",
            "логарифм", "корень",
            "скорость", "ускорение",
        ]

        return any(w in t for w in triggers)

    # ===== ОБРАБОТКА =====
    async def handle(self, user_id, text, context, run_with_typing):
        energy = context.get("energy", "LOW")
        t = text.lower()

        # ===== LOW (FREE) =====
        if energy == "LOW":
            if "=" in t or "реши" in t:
                result = self.solve_equation(text)

                if result:
                    return {
                        "type": "text",
                        "data": f"📐 Ответ:\n{result}\n\n⚡ Для графиков перейди на LITE"
                    }

            return {
                "type": "text",
                "data": "⚠️ Доступны только простые решения"
            }

        # ===== MEDIUM (LITE) =====
        if energy == "MEDIUM":
            if "график" in t or "y =" in t:
                expr = self.extract_function(text)

                if expr:
                    path = self.build_graph(expr)

                    if path:
                        try:
                            with open(path, "rb") as f:
                                return {
                                    "type": "image",
                                    "data": f.read()
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
                "data": "⚡ LITE режим активен"
            }

        # ===== HIGH (PREMIUM) =====
        if energy == "HIGH":

            if "график" in t or "y =" in t:
                expr = self.extract_function(text)

                if expr:
                    path = self.build_graph(expr)

                    if path:
                        try:
                            with open(path, "rb") as f:
                                return {
                                    "type": "image",
                                    "data": f.read()
                                }
                        except Exception as e:
                            print("🔥 READ ERROR:", e)

            if "=" in t or "реши" in t:
                result = self.solve_equation(text)

                if result:
                    return {
                        "type": "text",
                        "data": f"📐 Решение:\n{result}\n\n🧠 Хочешь — объясню"
                    }

            return {
                "type": "text",
                "data": "🧠 Глубокий анализ..."
            }

        return None

    # ===== ИЗВЛЕЧЕНИЕ ФУНКЦИИ =====
    def extract_function(self, text):
        try:
            match = re.search(r"y\s*=\s*(.+)", text.lower())
            if match:
                expr = match.group(1)
                expr = expr.replace("^", "**")
                return expr
        except Exception as e:
            print("🔥 EXTRACT ERROR:", e)
            return None

    # ===== ПОСТРОЕНИЕ ГРАФИКА =====
    def build_graph(self, expr):
        try:
            x = np.linspace(-10, 10, 200)

            def f(x):
                return eval(expr, {"x": x, "np": np})

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

    # ===== РЕШЕНИЕ УРАВНЕНИЯ =====
    def solve_equation(self, text):
        try:
            expr = text.replace("реши", "").strip()
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
