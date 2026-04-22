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

    # ===== 🔥 МЯГКАЯ ГЕНЕРАЦИЯ (УЛУЧШЕНО) =====
    elif any(x in t for x in [
        "сделай картинку",
        "сделай изображение",
        "сделай такую",
        "сделай так",
        "можешь сделать",
        "сможешь сделать",
        "хочу такую",
        "хочу такую же",
        "давай сделаем",
        "давай такую",
        "сделай как было",
        "такую же как выше"
    ]):
        # теперь не требуем anchor жестко
        intent = "generate_image"
        confidence = 0.9

    # ===== 🔥 ПОДТВЕРЖДЕНИЕ ДЕЙСТВИЯ (НОВОЕ) =====
    confirm_phrases = [
        "давай",
        "делай",
        "сделай",
        "генерируй",
        "поехали",
        "ок",
        "хорошо",
        "начинай"
    ]

    if any(x in t for x in confirm_phrases):
        # если уже есть намерение в состоянии
        if state.get("pending_action"):
            return {
                "intent": state.get("pending_action"),
                "confidence": 0.95
            }

    # ===== 🔥 EDIT IMAGE =====
    if image_ctx and image_ctx.get("path"):
        if any(x in t for x in [
            "измени",
            "сделай",
            "добавь",
            "убери",
            "улучши",
            "ярче",
            "темнее",
            "добавь лодку",
            "сделай ярче"
        ]):
            intent = "edit_image"
            confidence = 0.9

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
