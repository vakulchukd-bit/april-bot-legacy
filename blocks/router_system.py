# ==================== 🧠 ROUTER SYSTEM ====================

def decide_action(text: str, history: list):
    t = text.lower().strip()

    # --- запреты ---
    if any(w in t for w in ["не надо", "не делай", "не нужно"]):
        return {"action": "chat"}

    # --- если вопрос ---
    if "?" in t or any(w in t for w in ["что", "почему", "как", "зачем"]):
        return {"action": "chat"}

    # --- слабый запрос ---
    if len(t.split()) <= 2:
        return {"action": "clarify"}

    # --- diagram ---
    if any(w in t for w in ["чертеж", "чертёж", "схема", "диаграмма"]):
        return {"action": "diagram"}

    # --- image ---
    if any(w in t for w in ["создай", "сгенерируй", "нарисуй", "изображение"]):
        return {"action": "image"}

    return {"action": "chat"}
