# ==================== 🧠 ROUTER SYSTEM ====================

def decide_action(text: str, history: list):
    t = text.lower().strip()

    # --- запреты ---
    if any(w in t for w in ["не надо", "не делай", "не нужно"]):
        return {"action": "chat"}

    # --- image (ПЕРВЫМ!) ---
    if any(w in t for w in [
        "создай", "сгенерируй", "нарисуй",
        "изображение", "картинку", "картинка",
        "сделай картинку", "покажи картинку"
    ]):
        return {"action": "image"}

    # --- diagram ---
    if any(w in t for w in ["чертеж", "чертёж", "схема", "диаграмма"]):
        return {"action": "diagram"}

    # --- если вопрос ---
    if "?" in t or any(w in t for w in ["что", "почему", "как", "зачем"]):
        return {"action": "chat"}

    # --- слабый запрос ---
    if len(t.split()) <= 2:
        return {"action": "clarify"}

    return {"action": "chat"}
