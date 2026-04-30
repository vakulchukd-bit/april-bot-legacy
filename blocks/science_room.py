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

        if any(fn in t for fn in ["sin", "cos", "tan", "log"]):
            return True

        if "x" in t:
            return True

        return False

    def evaluate(self, text, context):
        if context.get("task_type") == "math":
            return 10.0
        return 1.0

    def split_into_tasks(self, text):
        t = text.lower()

        parts = re.split(r'(sin\([^)]+\)|cos\([^)]+\)|[a-z0-9\+\-\*/\(\)]+\=[a-z0-9\+\-\*/\(\)]+)', t)

        tasks = []

        for p in parts:
            p = p.strip()
            if not p:
                continue

            if "=" in p or "sin" in p or "cos" in p:
                tasks.append(p)

        return tasks

    def split_system(self, eq):
        parts = eq.split("=")

        equations = []

        if len(parts) == 3:
            equations.append(parts[0] + "=" + parts[1])
            equations.append(parts[1] + "=" + parts[2])

        elif len(parts) > 3:
            for i in range(len(parts) - 1):
                equations.append(parts[i] + "=" + parts[i + 1])

        else:
            equations.append(eq)

        return equations

    async def handle(self, user_id, text, context, run_with_typing):
        plan = get_user_plan(user_id)

        if user_id == ADMIN_ID:
            plan = "premium"

        tasks = self.split_into_tasks(text)

        equations = []
        sin_tasks = []

        for task in tasks:
            if "=" in task:
                equations.extend(self.split_system(task))
            elif "sin" in task:
                sin_tasks.append(task)

        results = []
        variables = {}

        # ===== СИСТЕМЫ =====
        if len(equations) >= 2:
            try:
                x, y = symbols('x y')

                for i in range(0, len(equations), 2):
                    if i + 1 >= len(equations):
                        break

                    eq1 = equations[i]
                    eq2 = equations[i + 1]

                    left1, right1 = eq1.split("=")
                    left2, right2 = eq2.split("=")

                    sol = solve([
                        sympify(left1) - sympify(right1),
                        sympify(left2) - sympify(right2)
                    ], (x, y))

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
        for s in sin_tasks:
            try:
                if "x" in variables:
                    val = variables["x"]
                    results.append(f"sin({val}) ≈ {round(math.sin(val), 4)}")
                else:
                    m = re.search(r'sin\(([\d\.]+)\)', s)
                    if m:
                        val = float(m.group(1))
                        results.append(f"sin({val}) ≈ {round(math.sin(val), 4)}")
            except Exception as e:
                print("🔥 SIN ERROR:", e)

        # ===== ГРАФИК =====
        expr = self.extract_function(text)

        if expr:
            # 🔥 ВАЛИДАЦИЯ (НОВОЕ)
            valid, error = self.validate_expression(expr)

            if not valid:
                return {
                    "type": "text",
                    "data": (
                        "❌ Не удалось построить график.\n"
                        f"Причина: {error}\n\n"
                        "👉 Пример корректного ввода:\n"
                        "y = x**2\n"
                        "y = np.sin(x)"
                    )
                }

            # 🔥 HTML график
            html = self.build_html_graph(expr)
            if html:
                return {
                    "type": "file",
                    "data": html,
                    "filename": "graph.html"
                }

            # 🔁 fallback PNG
            path = self.build_graph(expr)
            if path:
                try:
                    with open(path, "rb") as f:
                        return {
                            "type": "image",
                            "data": f.read(),
                            "meta": {"source": "math_graph"}
                        }
                except Exception as e:
                    print("🔥 GRAPH ERROR:", e)

        # ===== ВЫВОД =====
        if results:
            return {
                "type": "text",
                "data": "\n\n".join(results)
            }

        return None

    # 🔥 НОВОЕ: ВАЛИДАЦИЯ
    def validate_expression(self, expr):
        try:
            x = np.linspace(-10, 10, 10)

            eval(expr, {
                "x": x,
                "np": np,
                "__builtins__": {}
            })

            return True, None

        except Exception as e:
            return False, str(e)

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
            text = text.lower()
            text = text.replace("^", "**")

            text = text.replace("sin", "np.sin")
            text = text.replace("cos", "np.cos")
            text = text.replace("tan", "np.tan")
            text = text.replace("log", "np.log")

            match = re.search(r"y\s*=\s*(.+)", text)
            if match:
                return match.group(1)

            if "x" in text:
                return text

            return None
        except:
            return None

    def build_html_graph(self, expr):
        try:
            x = np.linspace(-10, 10, 200)
            y = eval(expr, {"x": x, "np": np, "__builtins__": {}})

            html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
body {{ background: #111; color: white; }}
</style>
</head>
<body>
<div id="graph"></div>
<script>
var trace = {{
  x: {x.tolist()},
  y: {y.tolist()},
  type: 'scatter'
}};

var layout = {{
  paper_bgcolor: '#111',
  plot_bgcolor: '#111',
  font: {{color: 'white'}}
}};

Plotly.newPlot('graph', [trace], layout);
</script>
</body>
</html>
"""
            return html
        except Exception as e:
            print("🔥 HTML GRAPH ERROR:", e)
            return None

    def build_graph(self, expr):
        try:
            x = np.linspace(-10, 10, 200)

            def f(x):
                return eval(expr, {
                    "x": x,
                    "np": np,
                    "__builtins__": {}
                })

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

    def solve_equation(self, text):
        try:
            expr = self.extract_math_expression(text)

            expr = expr.replace(" ", "")
            expr = re.sub(r'(\d)(x)', r'\1*\2', expr)
            expr = re.sub(r'(\d)\(', r'\1*(', expr)

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
