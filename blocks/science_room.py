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

        # 🔥 ДОБАВЛЕНО: ранний перехват таблицы (чтобы не терялась)
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
        # 🔥 ИСПРАВЛЕНО: убрали "y" (он ломал всё)
        if "график" in t or "построй" in t or "y=" in t:

            # 🔥 СТАРАЯ ЛОГИКА (НЕ ТРОГАЕМ)
            expr = self.extract_function(text)

            # ================== 🔥 НОВОЕ (НЕ ЛОМАЕТ СТАРОЕ) ==================
            if not expr:
                interpreted = self.interpret_text_graph(text)

                if interpreted:

                    # 👉 ФУНКЦИЯ
                    if interpreted["type"] == "function":
                        expr = interpreted["expr"]

                    # 👉 ТАБЛИЦА УМНОЖЕНИЯ (дублируем безопасно)
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
            # ===============================================================

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
            "data": "🧠 Не понял задачу, попробуй уточнить"
        }

    # ===== 🔥 УСИЛЕННЫЙ PARSER =====
    def interpret_text_graph(self, text):
        t = text.lower()

        # таблица умножения (расширено)
        if any(w in t for w in ["таблица умножения", "умножения", "умножить", "перемнож"]):
            return {"type": "heatmap"}

        # синус
        if any(w in t for w in ["синус", "sin", "волна"]):
            return {"type": "function", "expr": "np.sin(x)"}

        # косинус
        if any(w in t for w in ["косинус", "cos"]):
            return {"type": "function", "expr": "np.cos(x)"}

        # парабола
        if any(w in t for w in ["парабола", "квадрат", "x^2"]):
            return {"type": "function", "expr": "x**2"}

        # линия
        if any(w in t for w in ["линия", "прямая", "линейный"]):
            return {"type": "function", "expr": "x"}

        return None

    # ===== 🔥 НОВОЕ: ТАБЛИЦА УМНОЖЕНИЯ =====
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
            # 🔥 УЛУЧШЕНО: теперь ловит "уравнение"
            expr = text.lower().replace("реши", "").replace("уравнение", "").strip()
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
