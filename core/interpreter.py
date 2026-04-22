def interpret(text: str, state: dict, anchor: dict, image_ctx: dict):
    t = text.lower()

    intent = "chat"
    confidence = 0.5

    # ===== IMAGE GENERATION =====
    if any(x in t for x in ["нарисуй", "сгенерируй", "создай"]):
        intent = "generate_image"
        confidence = 0.9

    # ===== EDIT IMAGE =====
    if image_ctx and image_ctx.get("path"):
        if any(x in t for x in ["измени", "сделай", "добавь", "убери"]):
            intent = "edit_image"
            confidence = 0.8

    # ===== QUESTION =====
    if any(x in t for x in ["что", "кто", "какая", "почему", "как"]):
        intent = "question"
        confidence = 0.8

    # ===== FOLLOW-UP =====
    if any(x in t for x in ["что на ней", "что это", "что здесь"]):
        if image_ctx:
            intent = "describe_image"
            confidence = 0.9

    return {
        "intent": intent,
        "confidence": confidence
    }
