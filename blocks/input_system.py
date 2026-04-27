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


def detect_intent(text: str) -> str:
    t = text.lower()

    # 🔥 МАТЕМАТИКА (ДОЛЖНА БЫТЬ ПЕРВОЙ)
    if any(x in t for x in ["=", "x", "+", "-", "*", "/"]):
        return "math"

    # --- ИЗОБРАЖЕНИЯ ---
    if any(w in t for w in ["картин", "фото", "сгенерируй"]):
        return "generate_image"

    # --- ДИАГРАММЫ ---
    if any(w in t for w in ["чертеж", "схема", "диаграмма"]):
        return "diagram"

    # --- ОБЫЧНЫЙ ЧАТ ---
    return "chat"
