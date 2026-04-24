def detect_response_mode(text: str) -> str:
    t = text.lower()

    # ===== КОПИРУЕМЫЕ ТЕКСТЫ =====
    copy_triggers = [
        "скопируй", "для копирования", "копировать",
        "дай текст", "готовый текст", "шаблон",
        "напиши текст", "оформи", "заявление",
        "письмо", "документ",
        "сообщение клиенту",
        "напиши красиво",
        "сделай текст"
    ]

    for w in copy_triggers:
        if w in t:
            return "copy"

    # ===== ССЫЛКИ =====
    link_triggers = [
        "ссылка",
        "url",
        "линк",
        "дай ссылку",
        "короткую ссылку",
        "сократи ссылку"
    ]

    for w in link_triggers:
        if w in t:
            return "link"

    # ===== ОФОРМЛЕНИЕ / КРАСИВО =====
    format_triggers = [
        "красиво",
        "оформи",
        "сделай красиво",
        "оформи текст",
        "структурируй"
    ]

    for w in format_triggers:
        if w in t:
            return "format"

    # ===== ОБЫЧНЫЙ =====
    return "normal"
