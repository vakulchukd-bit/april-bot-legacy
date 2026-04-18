# ==================== 🔵 BLOCK: INPUT SYSTEM ====================

async def process_input(message):
    """
    Универсальный вход
    Ничего не ломает, только добавляет слой понимания
    """

    user_id = message.from_user.id

    # --- TEXT ---
    if message.text:
        text = message.text
        source = "text"

    # --- VOICE (пока заглушка) ---
    elif message.voice:
        text = "[voice message]"
        source = "voice"

    # --- IMAGE (пока заглушка) ---
    elif message.photo:
        text = "[image message]"
        source = "image"

    else:
        text = "[unsupported]"
        source = "unknown"

    # --- INTENT ---
    intent = detect_intent(text)

    return {
        "user_id": user_id,
        "text": text,
        "source": source,
        "intent": intent
    }


# ==================== 🟣 INTENT DETECTOR ====================

def detect_intent(text: str) -> str:
    """
    Определяем намерение пользователя
    """

    t = text.lower()

    trigger_words = [
        "сделай картинку",
        "сгенерируй",
        "нарисуй",
        "создай изображение",
        "draw",
        "generate image"
    ]

    negative_context = [
        "я видел",
        "на картинке",
        "обсудим",
        "расскажу",
        "вопрос",
        "почему"
    ]

    for word in trigger_words:
        if word in t:
            for bad in negative_context:
                if bad in t:
                    return "chat"
            return "generate_image"

    return "chat"
