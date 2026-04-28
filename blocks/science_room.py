import re
import numpy as np
import matplotlib.pyplot as plt
import math

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

    # ===== 🔥 СИНТАКСИЧЕСКИЙ ПАРСЕР =====
    def extract_math_chunks(self, text):
        t = text.lower()
        t = re.sub(r'[^\dx\+\-\*/=\(\)\.\s]', ' ', t)

        parts = t.split()

        chunks = []
        current = ""

        for p in parts:
            if any(c in p for c in "=+-*/x"):
                current += p
            else:
                if current:
                    chunks.append(current)
                    current = ""

        if current:
            chunks.append(current)

        return chunks

    def parse_equations(self, chunk):
        parts = chunk.split("=")

        equations = []

        if len(parts) == 3:
            equations.append(parts[0] + "=" + parts[1])
            equations.append(parts[1] + "=" + parts[2])

        elif len(parts) > 3:
            for i in range(len(parts) - 1):
                equations.append(parts[i] + "=" + parts[i + 1])

        else:
            equations.append(chunk)

        return equations

    async def handle(self, user_id, text, context, run_with_typing):
        plan = get_user_plan(user_id)

        if user_id == ADMIN_ID:
            plan = "premium"

        t = text.lower()

        # 🔥 ПАРСИНГ
        chunks = self.extract_math_chunks(text)

        equations = []
        for c in chunks:
            equations.extend(self.parse_equations(c))

        results = []
        variables = {}

        # ===== СИСТЕМА =====
        if len(equations) >= 2:
            try:
                x, y = symbols('x y')

                eqs = []
                for eq in equations[:2]:
                    left, right = eq.split("=")
                    eqs.append(sympify(left) - sympify(right))

                sol = solve(eqs, (x, y))

                variables["x"] = float(sol[x])
                variables["y"] = float(sol[y])

                results.append(f"📐 Система:\nx = {sol[x]}, y = {sol[y]}")

            except Exception as e:
                print("🔥 SYSTEM ERROR:", e)

        # ===== ОДИНОЧНЫЕ =====
        for eq in equations:
            if len(equations) >= 2:
                break

            res = self.solve_equation(eq)
            if res:
                results.append(f"📐 {res}")

                match = re.search(r'x\s*=\s*([\-0-9\.]+)', res)
                if match:
                    variables["x"] = float(match.group(1))

        # ===== SIN =====
        if "sin" in t:
            try:
                if "x" in variables:
                    val = variables["x"]
                    results.append(f"sin({val}) ≈ {round(math.sin(val), 4)}")
                else:
                    m = re.search(r'sin\(([\d\.]+)\)', t)
                    if m:
                        val = float(m.group(1))
                        results.append(f"sin({val}) ≈ {round(math.sin(val), 4)}")
            except Exception as e:
                print("🔥 SIN ERROR:", e)

        # ===== ГРАФИК =====
        if "график" in t or "построй" in t:
            expr = self.extract_function(text)

            if not expr:
                m = re.search(r'x\+y=(\d+)', t)
                if m:
                    expr = f"{m.group(1)} - x"

            if expr:
                path = self.build_graph(expr)
                if path:
                    try:
                        with open(path, "rb") as f:
                            return {"type": "image", "data": f.read()}
                    except Exception as e:
                        print("🔥 GRAPH ERROR:", e)

        # ===== ВЫВОД =====
        if results:
            return {
                "type": "text",
                "data": "\n\n".join(results)
            }

        return {
            "type": "text",
            "data": "⚠️ Не удалось распознать задачу."
        }

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
        try:
            text = text.lower().replace("^", "**")
            match = re.search(r"y\s*=\s*(.+)", text)
            if match:
                return match.group(1)
            return None
        except:
            return None

    def build_graph(self, expr):
        try:
            x = np.linspace(-10, 10, 200)

            def f(x):
                return eval(expr, {"x": x, "np": np, "__builtins__": {}})

            y = f(x)

            plt.figure()
            plt.plot(x, y)
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
            expr = self.extract_math_expression(text)

            expr = re.sub(r'(\d)(x)', r'\1*\2', expr)

            x = symbols('x')

            if "=" in expr:
                left, right = expr.split("=")

                equation = simplify(sympify(left) - sympify(right))
                solutions = solve(equation, x)

                if solutions:
                    return f"x = {solutions[0]}"

        except Exception as e:
            print("🔥 SOLVE ERROR:", e)

        return None
