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
                    return {
                        "type": "image",
                        "data": path
                    }

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
                    return {
                        "type": "image",
                        "data": path
                    }

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
