import re
import numpy as np
import matplotlib.pyplot as plt

from sympy import symbols, sympify, solve, solveset, S, simplify
from storage import get_user_plan

ADMIN_ID = 2016592532


class ScienceRoom:
    name = "science"

    def can_handle(self, text, context):
        t = text.lower()

        if "график" in t or "построй" in t:
            return True

        if "y=" in t or "y =" in t:
            return True

        if "=" in t or "реши" in t:
            return True

        if any(w in t for w in [
            "приведи", "вырази", "найди", "доведи",
            "вычисли", "переменн", "значение",
            "уравнен", "выражен"
        ]):
            return True

        if "x" in t:
            return True

        return False

    def evaluate(self, text, context):
        t = text.lower()

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

    # ===== 🔥 НОВОЕ: РАЗБИВКА НА ЗАДАЧИ =====
    def split_tasks(self, text):
        parts = re.split(r'(реши|найди)', text.lower())
        tasks = []

        current = ""
        for p in parts:
            if p.strip() in ["реши", "найди"]:
                if current:
                    tasks.append(current.strip())
                current = p
            else:
                current += " " + p

        if current.strip():
            tasks.append(current.strip())

        return tasks if len(tasks) > 1 else [text]

    async def handle(self, user_id, text, context, run_with_typing):
        plan = get_user_plan(user_id)

        if user_id == ADMIN_ID:
            plan = "premium"

        t = text.lower()

        # ===== 🔥 MULTI TASK FIX =====
        tasks = self.split_tasks(text)
        results = []

        for task in tasks:

            # ===== ГРАФИКИ =====
            if "график" in task or "построй" in task or "y=" in task:
                expr = self.extract_function(task)

                if not expr:
                    interpreted = self.interpret_text_graph(task)
                    if interpreted:
                        if interpreted["type"] == "function":
                            expr = interpreted["expr"]
                        elif interpreted["type"] == "heatmap":
                            path = self.build_multiplication_table()
                            if path:
                                try:
                                    with open(path, "rb") as f:
                                        return {"type": "image", "data": f.read()}
                                except Exception as e:
                                    print("🔥 READ ERROR:", e)

                if expr:
                    path = self.build_graph(expr)
                    if path:
                        try:
                            with open(path, "rb") as f:
                                return {"type": "image", "data": f.read()}
                        except Exception as e:
                            print("🔥 READ ERROR:", e)

            # ===== FREE =====
            if plan == "free":
                if "=" in task or "реши" in task:
                    result = self.solve_equation(task)
                    if result:
                        results.append(f"📐 Ответ:\n{result}")
                continue

            # ===== РЕШЕНИЕ =====
            if "=" in task or "реши" in task or any(w in task for w in [
                "приведи", "доведи", "найди", "вырази", "вычисли"
            ]):
                result = self.solve_equation(task)
                if result:
                    results.append(f"📐 Решение:\n{result}")

        if results:
            return {
                "type": "text",
                "data": "\n\n".join(results)
            }

        return {"type": "skip"}

    # ===== ПАРСИНГ =====
    def extract_math_expression(self, text):
        t = text.lower()

        t = t.replace("²", "**2")
        t = t.replace("^", "**")
        t = t.replace(":", " ")

        match = re.search(r'([-+*/().\d x]+=[-+*/().\d x]+)', t)
        if match:
            return match.group(1)

        match = re.search(r'([-+*/().\d x]+)', t)
        if match:
            return match.group(1)

        return t

    def interpret_text_graph(self, text):
        t = text.lower()

        if any(w in t for w in ["таблица умножения", "умножения", "умножить", "перемнож"]):
            return {"type": "heatmap"}

        if any(w in t for w in ["синус", "sin"]):
            return {"type": "function", "expr": "np.sin(x)"}

        if any(w in t for w in ["косинус", "cos"]):
            return {"type": "function", "expr": "np.cos(x)"}

        if any(w in t for w in ["парабола", "x^2"]):
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

    # ===== РЕШЕНИЕ =====
    def solve_equation(self, text):
        try:
            expr = self.extract_math_expression(text).strip()

            expr = re.sub(r'(\d)(x)', r'\1*\2', expr)
            expr = re.sub(r'(x)(\d)', r'\1*\2', expr)
            expr = re.sub(r'(\d)\(', r'\1*(', expr)
            expr = re.sub(r'\)\(', r')*(', expr)
            expr = re.sub(r'(x)\(', r'\1*(', expr)
            expr = re.sub(r'(?<!\w)-x', r'-1*x', expr)

            x = symbols('x')

            if "=" in expr:
                left, right = expr.split("=")

                steps = []
                steps.append(f"{left} = {right}")

                equation = simplify(sympify(left) - sympify(right))
                steps.append(f"{equation} = 0")

                solutions = solve(equation, x)

                if not solutions:
                    solutions = solveset(equation, x, domain=S.Reals)

                if not solutions:
                    return "⚠️ Нет решения"

                if isinstance(solutions, set) or hasattr(solutions, '__iter__'):
                    sol_list = list(solutions)
                else:
                    sol_list = [solutions]

                if len(sol_list) == 1:
                    steps.append(f"x = {sol_list[0]}")
                else:
                    sol_str = " или ".join([f"x = {s}" for s in sol_list])
                    steps.append(sol_str)

                return "\n".join(steps)

            else:
                equation = simplify(sympify(expr))
                solutions = solve(equation, x)

                if len(solutions) == 1:
                    return f"x = {solutions[0]}"
                else:
                    return " или ".join([f"x = {s}" for s in solutions])

        except Exception as e:
            print("🔥 SOLVE ERROR:", e)
            return None
