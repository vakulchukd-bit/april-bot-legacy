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

        if "график" in t or "построй" in t:
            return True

        if "y=" in t or "y =" in t:
            return True

        if "=" in t or "реши" in t:
            return True

        if any(w in t for w in [
            "приведи",
            "вырази",
            "найди",
            "доведи",
            "вычисли",
            "переменн",
            "значение",
            "уравнен",
            "выражен"
        ]):
            return True

        # 🔥 ВАЖНО: распознаём переменные
        if "x" in t:
            return True

        return False

    # ===== 🔥 УСИЛЕННЫЙ evaluate =====
    def evaluate(self, text, context):
        t = text.lower()

        # 🔥 ГЛАВНОЕ: математика всегда приоритет
        if context.get("task_type") == "math":
            return 10.0

        score = 0.0

        try:
            if self.can_handle(text, context):
                score += 1.0
        except:
            pass

        if any(w in t for w in ["синус", "график", "формула", "матем", "уравнение"]):
            score += 1.0

        return score

    # ===== ОБРАБОТКА =====
    async def handle(self, user_id, text, context, run_with_typing):
        plan = get_user_plan(user_id)

        if user_id == ADMIN_ID:
            plan = "premium"

        t = text.lower()

        if "таблица" in t and "умнож" in t:
            path = self.build_multiplication_table()

            if path:
                try:
                    with open(path, "rb") as f:
                        return {
                            "type": "image",
                            "data": f.read()
                        }
                except Exception as e:
                    print("🔥 READ ERROR:", e)

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

        if "график" in t or "построй" in t or "y=" in t:

            expr = self.extract_function(text)

            if not expr:
                interpreted = self.interpret_text_graph(text)

                if interpreted:

                    if interpreted["type"] == "function":
                        expr = interpreted["expr"]

                    elif interpreted["type"] == "heatmap":
                        path = self.build_multiplication_table()

                        if path:
                            try:
                                with open(path, "rb") as f:
                                    return {
                                        "type": "image",
                                        "data": f.read()
                                    }
                            except Exception as e:
                                print("🔥 READ ERROR:", e)

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

        if "=" in t or "реши" in t or any(w in t for w in [
            "приведи",
            "доведи",
            "найди",
            "вырази",
            "вычисли"
        ]):
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

    # ===== ПАРСЕР =====
    def interpret_text_graph(self, text):
        t = text.lower()

        if any(w in t for w in ["таблица умножения", "умножения", "умножить", "перемнож"]):
            return {"type": "heatmap"}

        if any(w in t for w in ["синус", "sin", "волна", "волны", "волновой"]):
            return {"type": "function", "expr": "np.sin(x)"}

        if any(w in t for w in ["косинус", "cos"]):
            return {"type": "function", "expr": "np.cos(x)"}

        if any(w in t for w in ["парабола", "квадрат", "x^2"]):
            return {"type": "function", "expr": "x**2"}

        return None

    def build_multiplication_table(self):
        try:
            data = np.outer(range(1, 11), range(1, 11))

            plt.figure()
            plt.imshow(data)
            plt.colorbar()
            plt.title("Таблица умножения")

            path = "graph.png"
            plt.savefig(path)
            plt.close()

            return path

        except Exception as e:
            print("🔥 TABLE ERROR:", e)
            return None

    def extract_function(self, text):
        try:
            text = text.lower()
            text = text.replace("²", "**2")
            text = text.replace("^", "**")

            match = re.search(r"y\s*=\s*(.+)", text)
            if match:
                return match.group(1)

            return None
        except Exception as e:
            print("🔥 EXTRACT ERROR:", e)
            return None

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

    def solve_equation(self, text):
        try:
            expr = text.lower()

            expr = expr.replace("²", "**2")
            expr = expr.replace("^", "**")
            expr = expr.replace(":", "")

            for w in ["реши", "уравнение", "найди", "вычисли"]:
                expr = expr.replace(w, "")

            expr = expr.strip()

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
