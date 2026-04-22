def detect_intent(text: str):
    t = text.lower().strip()

    # ===== ВОПРОС =====
    if "?" in t or any(q in t for q in [
        "как", "что", "почему", "зачем",
        "умеешь", "можешь"
    ]):
        return "question"

    # ===== РЕДАКТИРОВАНИЕ =====
    if any(v in t for v in [
        "добавь", "измени", "убери",
        "замени", "поменяй", "улучши",
        "подправь", "ярче", "темнее"
    ]):
        return "edit"

    # ===== ГЕНЕРАЦИЯ (ТОЛЬКО ДЕЙСТВИЯ) =====
    if any(g in t for g in [
        "создай", "сгенерируй", "нарисуй",
        "draw", "generate"
    ]):
        return "generate"

    # ===== ОБЫЧНЫЙ ТЕКСТ =====
    return "chat"
