def interpret(text: str, state: dict, anchor: dict, image_ctx: dict):
    t = text.lower()

    intent = "chat"
    confidence = 0.5

    # ===== 🔥 ЯВНАЯ ГЕНЕРАЦИЯ =====
    if any(x in t for x in [
        "нарисуй",
        "сгенерируй",
        "создай",
        "draw",
        "generate"
    ]):
        intent = "generate_image"
        confidence = 0.95

    # ===== 🔥 МЯГКАЯ ГЕНЕРАЦИЯ (НОВОЕ — КЛЮЧ) =====
    elif any(x in t for x in [
        "сделай картинку",
        "сделай изображение",
        "сделай такую",
        "сделай так",
        "можешь сделать",
        "сможешь сделать",
        "хочу такую",
        "хочу такую же"
    ]):
        if anchor:
            intent = "generate_image"
            confidence = 0.9

    # ===== 🔥 EDIT IMAGE =====
    if image_ctx and image_ctx.get("path"):
        if any(x in t for x in [
            "измени",
            "сделай",
            "добавь",
            "убери",
            "улучши",
            "ярче",
            "темнее"
        ]):
            intent = "edit_image"
            confidence = 0.85

    # ===== 🔥 FOLLOW-UP =====
    follow_phrases = [
        "что на ней",
        "что это",
        "что здесь",
        "опиши",
        "расскажи про это",
        "и что",
        "что дальше"
    ]

    if any(x in t for x in follow_phrases):
        if image_ctx and image_ctx.get("path"):
            return {
                "intent": "describe_image",
                "confidence": 0.95
            }

        if anchor:
            return {
                "intent": "follow_context",
                "confidence": 0.85
            }

    # ===== 🔥 ВОПРОС =====
    if any(x in t for x in ["что", "кто", "какая", "почему", "как"]):
        intent = "question"
        confidence = 0.8

    return {
        "intent": intent,
        "confidence": confidence
    }
