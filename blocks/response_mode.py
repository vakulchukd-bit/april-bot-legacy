def detect_response_mode(text: str) -> str:
    t = text.lower()

    copy_triggers = [
        "скопируй", "для копирования", "копировать",
        "дай текст", "готовый текст", "шаблон",
        "напиши текст", "оформи", "заявление",
        "письмо", "документ"
    ]

    for w in copy_triggers:
        if w in t:
            return "copy"

    return "normal"
