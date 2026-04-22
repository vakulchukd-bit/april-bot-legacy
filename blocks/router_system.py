# ==================== 🧠 ROUTER SYSTEM ====================

def decide_action(text: str, history: list):
    t = text.lower().strip()

    # --- запреты ---
    if any(w in t for w in ["не надо", "не делай", "не нужно"]):
        return {"action": "chat"}

    # ===== 🔥 IMAGE (ТОЛЬКО ЯВНЫЕ ДЕЙСТВИЯ) =====
    if any(w in t for w in [
        "создай",
        "сгенерируй",
        "нарисуй",
        "draw",
        "generate"
    ]):
        return {"action": "image"}

    # ===== DIAGRAM =====
    if any(w in t for w in ["чертеж", "чертёж", "схема", "диаграмма"]):
        return {"action": "diagram"}

    # ===== ВОПРОС =====
    if "?" in t or any(w in t for w in ["что", "почему", "как", "зачем"]):
        return {"action": "chat"}

    # ===== СЛАБЫЙ ЗАПРОС =====
    if len(t.split()) <= 2:
        return {"action": "clarify"}

    return {"action": "chat"}
