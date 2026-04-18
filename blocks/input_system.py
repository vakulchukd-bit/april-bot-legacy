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

    return {
        "user_id": user_id,
        "text": text,
        "source": source,
        "intent": "chat"
    }


def detect_intent(text: str) -> str:
    t = text.lower()

    if any(w in t for w in ["картин", "фото", "сгенерируй"]):
        return "generate_image"

    return "chat"
