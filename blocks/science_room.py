# ===============================
# 🔥 SAFE PATCH MODE (SCIENCE ROOM)
# ===============================

PATCH_LOG = []

def safe_patch_log(msg):
    try:
        print("SCIENCE PATCH:", msg)
        PATCH_LOG.append(msg)
    except:
        pass


# 🔥 PATCH: контроль входа в комнату
def patch_science_enter(text):
    safe_patch_log(f"SCIENCE ENTER: {text[:50]}")
    return None


# 🔥 PATCH: будущая логика графиков
def patch_science_future(*args, **kwargs):
    return None


# ===============================
# 🔥 PATCH: СТАБИЛЬНЫЙ ГРАФИК (ПОЛНЫЙ БЛОК)
# ===============================

def patch_force_graph_from_memory(state, text):
    try:
        t = text.lower()

        trigger_words = ["построй", "покажи", "график", "это"]

        if not any(w in t for w in trigger_words):
            return None

        last = state.get("last_math")

        if last and last.get("type") == "function":
            return last.get("expr")

    except Exception as e:
        print("PATCH GRAPH ERROR:", e)

    return None


def apply_graph_patch_if_needed(state, text):
    try:
        expr = patch_force_graph_from_memory(state, text)
        return expr
    except Exception as e:
        print("PATCH APPLY ERROR:", e)
        return None
        # ===============================
# 🔥 PATCH: ПЕРЕХВАТ extract_function
# ===============================

def patch_wrap_extract_function():
    try:
        original = ScienceRoom.extract_function

        def wrapped(self, text):
            try:
                state = getattr(self, "_last_state", None)

                # 🔥 сначала пробуем патч
                if state:
                    patched = patch_override_extract(self, text, state)
                    if patched:
                        return patched

                # 🔁 fallback — оригинальная логика
                return original(self, text)

            except Exception as e:
                print("WRAP ERROR:", e)
                return original(self, text)

        ScienceRoom.extract_function = wrapped

        print("✅ extract_function patched")

    except Exception as e:
        print("PATCH WRAP ERROR:", e)
        # ===============================
# 🔥 PATCH: AUTO MODIFY (БЕЗ ПРАВОК ВНУТРИ КЛАССА)
# ===============================

def patch_auto_modify_expr(expr, text):
    try:
        if not expr:
            return expr

        t = text.lower()
        original = expr

        # --- круче / резче ---
        if "круче" in t or "резче" in t:
            match = re.search(r"([\-]?\d+(\.\d+)?)\*x\*\*2", expr)
            if match:
                coef = float(match.group(1))
                expr = expr.replace(match.group(1), str(coef * 2))

        # --- плавнее ---
        elif "плавнее" in t or "менее крутой" in t:
            match = re.search(r"([\-]?\d+(\.\d+)?)\*x\*\*2", expr)
            if match:
                coef = float(match.group(1))
                expr = expr.replace(match.group(1), str(coef / 2))

        return expr

    except Exception as e:
        print("AUTO MODIFY ERROR:", e)
        return expr


def patch_wrap_extract_with_modify():
    try:
        original = ScienceRoom.extract_function

        def wrapped(self, text):
            try:
                expr = original(self, text)

                state = getattr(self, "_last_state", None)

                if state and expr:
                    new_expr = patch_auto_modify_expr(expr, text)

                    if new_expr != expr:
                        state["last_math"] = {
                            "type": "function",
                            "expr": new_expr
                        }
                        print("🔥 AUTO MODIFIED:", new_expr)
                        return new_expr

                return expr

            except Exception as e:
                print("WRAP MODIFY ERROR:", e)
                return original(self, text)

        ScienceRoom.extract_function = wrapped
        print("✅ AUTO MODIFY PATCH ACTIVE")

    except Exception as e:
        print("PATCH INIT ERROR:", e)


# 🔥 АКТИВАЦИЯ
try:
    patch_wrap_extract_with_modify()
except Exception as e:
    print("PATCH RUN ERROR:", e)
# blocks/science_room.py

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

        state = context.get("state", {})

        # 🔥 НОВОЕ: КОНТЕКСТНЫЙ ТРИГГЕР (КЛЮЧЕВОЙ ФИКС)
        if state.get("last_math"):
            if any(w in t for w in ["покажи", "сделай", "давай", "построй", "это", "теперь"]):
                return True

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

        parts = re.split(
            r'(sin\([^)]+\)|cos\([^)]+\)|[a-z0-9\+\-\*/\(\)]+\=[a-z0-9\+\-\*/\(\)]+)',
            t
        )

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

        state = context.get("state", {})

        expr = self.extract_function(text)

        if expr:
            state["last_math"] = {
                "type": "function",
                "expr": expr
            }

        if not expr:
            last = state.get("last_math")
            if last and last.get("type") == "function":
                expr = last.get("expr")

        if expr:
            valid, error = self.validate_expression(expr)

            if not valid:
                return {
                    "type": "text",
                    "data": (
                        "Не получилось построить график — давай поправим 👇\n\n"
                        f"Причина: {error}\n\n"
                        "Попробуй так:\n"
                        "y = sin(x)\n"
                        "или\n"
                        "y = x**2\n\n"
                        "Если хочешь — скажи «покажи», и я построю 🙂"
                    )
                }

            path = self.build_graph(expr)

            if path:
                state["fail_count"] = 0

                try:
                    with open(path, "rb") as f:
                        return {
                            "type": "image",
                            "data": f.read(),
                            "meta": {"source": "math_graph"}
                        }
                except Exception as e:
                    print("🔥 GRAPH ERROR:", e)

            return {
                "type": "text",
                "data": "❌ Не удалось построить график (ошибка генерации)"
            }

        # ===== старая логика =====

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

        for eq in equations:
            if len(equations) >= 2:
                break

            if eq.strip().startswith("y=") or eq.strip().startswith("y ="):
                continue

            res = self.solve_equation(eq)

            if res:
                results.append(f"📐 {res}")
                state["fail_count"] = 0

                match = re.search(r'x\s*=\s*([\-0-9\.]+)', res)
                if match:
                    variables["x"] = float(match.group(1))

        for s in sin_tasks:
            try:
                if "x" in variables:
                    val = variables["x"]
                    results.append(f"sin({val}) ≈ {round(math.sin(val), 4)}")
                    state["fail_count"] = 0
                else:
                    m = re.search(r'sin\(([\d\.]+)\)', s)
                    if m:
                        val = float(m.group(1))
                        results.append(f"sin({val}) ≈ {round(math.sin(val), 4)}")
                        state["fail_count"] = 0
            except Exception as e:
                print("🔥 SIN ERROR:", e)

        if results:
            return {
                "type": "text",
                "data": "\n\n".join(results)
            }

        fail = state.get("fail_count", 0) + 1
        state["fail_count"] = fail

        return {
            "type": "text",
            "data": "Не до конца понял, уточни чуть подробнее 🙂"
        }

    # 🔥 ДОБАВЛЕННЫЙ ФИКС
    def extract_function(self, text):
        try:
            text = text.lower().replace("^", "**")

            text = text.replace("sin", "np.sin")
            text = text.replace("cos", "np.cos")
            text = text.replace("tan", "np.tan")
            text = text.replace("log", "np.log")
            text = text.replace("ln", "np.log")

            match = re.search(r"(y|f|s|c)\s*\(\s*[a-z]\s*\)\s*=\s*(.+)", text)
            if match:
                return match.group(2).strip()

            match = re.search(r"y\s*=\s*(.+)", text)
            if match:
                return match.group(1).strip()

            return None

        except:
            return None

    def validate_expression(self, expr):
        try:
            x = np.linspace(-10, 10, 10)
            eval(expr, {"x": x, "np": np, "__builtins__": {}})
            return True, None
        except Exception as e:
            return False, str(e)

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
        except Exception as e:
            print("🔥 GRAPH ERROR:", e)
            return None

    def solve_equation(self, text):
        try:
            text = text.lower()
            text = text.replace("реши", "")
            text = text.strip()

            expr = text.replace(" ", "")
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
