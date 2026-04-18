# ==================== 🔵 BLOCK: INPUT SYSTEM ====================

async def process_input(message):
    user_id = message.from_user.id

    # --- TEXT ---
    if message.text:
        text = message.text
        source = "text"

    # --- VOICE ---
    elif message.voice:
        text = "[voice message]"
        source = "voice"

    # --- IMAGE ---
    elif message.photo:
        text = "[image message]"
        source = "image"

    else:
        text = "[unsupported]"
        source = "unknown"

    intent = detect_intent(text)

    return {
        "user_id": user_id,
        "text": text,
        "source": source,
        "intent": intent
    }


# ==================== 🟣 INTENT DETECTOR ====================

def detect_intent(text: str) -> str:
    t = text.lower()

    # 🔥 diagram приоритет
    diagram_words = [
        "чертеж",
        "чертёж",
        "схема",
        "диаграмма",
        "план",
        "планировка",
        "квартира"
    ]

    for word in diagram_words:
        if word in t:
            return "diagram"

    # 🖼 генерация изображений
    image_words = [
        "сделай картинку",
        "сгенерируй",
        "нарисуй",
        "создай изображение",
        "draw",
        "generate image"
    ]

    for word in image_words:
        if word in t:
            return "generate_image"

    return "chat"
