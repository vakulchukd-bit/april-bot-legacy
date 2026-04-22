def interpret(text: str, state: dict, anchor: dict, image_ctx: dict):
    t = text.lower().strip()

    intent = "chat"
    confidence = 0.5

    # ===== 🔥 1. СНАЧАЛА ОПРЕДЕЛЯЕМ ВОПРОС (КРИТИЧЕСКОЕ) =====
    question_markers = [
        "можешь", "сможешь", "ты бы", "если", "а ты",
        "умеешь", "можно", "получится"
    ]

    is_question = "?" in text or any(x in t for x in question_markers)

    if is_question:
        return {
            "intent": "question",
            "confidence": 0.95
        }

    # ===== 🔥 2. ПОДТВЕРЖДЕНИЕ ДЕЙСТВИЯ =====
    confirm_phrases = [
        "давай",
        "делай",
        "сделай",
        "генерируй",
        "поехали",
        "ок",
        "хорошо",
        "начинай",
        "да"
    ]

    if any(x in t for x in confirm_phrases):
        if state.get("pending_action"):
            return {
                "intent": state.get("pending_action"),
                "confidence": 0.95
            }

    # ===== 🔥 3. ЯВНАЯ ГЕНЕРАЦИЯ =====
    if any(x in t for x in [
        "нарисуй",
        "сгенерируй",
        "создай",
        "draw",
        "generate"
    ]):
        intent = "generate_image"
        confidence = 0.95

    # ===== 🔥 4. МЯГКАЯ ГЕНЕРАЦИЯ (НО ТОЛЬКО НЕ ВОПРОС) =====
    elif any(x in t for x in [
        "сделай картинку",
        "сделай изображение",
        "сделай такую",
        "сделай так",
        "хочу такую",
        "хочу такую же",
        "давай сделаем",
        "давай такую",
        "сделай как было",
        "такую же как выше"
    ]):
        intent = "generate_image"
        confidence = 0.9

    # ===== 🔥 5. EDIT IMAGE =====
    if image_ctx and image_ctx.get("path"):
        if any(x in t for x in [
            "измени",
            "добавь",
            "убери",
            "замени",
            "поменяй",
            "осветли",
            "затемни",
            "улучши",
            "ярче",
            "темнее"
        ]):
            intent = "edit_image"
            confidence = 0.9

    # ===== 🔥 6. FOLLOW-UP =====
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

    # ===== 🔥 7. ОБЫЧНЫЙ ВОПРОС =====
    if any(x in t for x in ["что", "кто", "какая", "почему", "как"]):
        intent = "question"
        confidence = 0.8

    return {
        "intent": intent,
        "confidence": confidence
    }
