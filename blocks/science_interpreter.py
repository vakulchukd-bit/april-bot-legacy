# ==================== 🧠 SCIENCE INTERPRETER ====================

def interpret_graph_request(text: str):
    t = text.lower()

    # 🔥 Таблица умножения
    if "таблица умножения" in t:
        return {"type": "heatmap"}

    # 🔥 Синус
    if "синус" in t or "sin" in t:
        return {"type": "function", "expr": "np.sin(x)"}

    # 🔥 Косинус
    if "косинус" in t or "cos" in t:
        return {"type": "function", "expr": "np.cos(x)"}

    # 🔥 Парабола
    if "парабола" in t or "квадрат" in t:
        return {"type": "function", "expr": "x**2"}

    return None
