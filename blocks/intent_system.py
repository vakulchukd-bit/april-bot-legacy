# blocks/intent_system.py

def detect_intent(text: str):
    t = text.lower()

    # ===== MEMORY =====
    if any(x in t for x in [
        "какая была", "что было", "напомни", "помнишь"
    ]):
        return "memory"

    # ===== ANALYZE =====
    if any(x in t for x in [
        "что на", "что изображено", "что это"
    ]):
        return "analyze"

    # ===== EDIT =====
    if any(x in t for x in [
        "измени", "сделай", "добавь", "убери", "осветли", "затемни"
    ]):
        return "edit"

    # ===== GENERATE =====
    if any(x in t for x in [
        "создай", "сгенерируй", "нарисуй"
    ]):
        return "generate"

    return "text"
