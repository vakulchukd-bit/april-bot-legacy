def detect_intent(text: str):
    t = text.lower().strip()

    # ===== ВОПРОС =====
    question_triggers = [
        "как", "что", "почему", "зачем",
        "умеешь", "можешь", "где", "когда",
        "сколько", "какой", "какая", "какие"
    ]

    if "?" in t or any(q in t for q in question_triggers):
        return "question"

    # ===== РЕДАКТИРОВАНИЕ =====
    edit_triggers = [
        "добавь", "измени", "убери",
        "замени", "поменяй", "улучши",
        "подправь", "сделай лучше",
        "ярче", "темнее", "переделай"
    ]

    if any(v in t for v in edit_triggers):
        return "edit"

    # ===== ГЕНЕРАЦИЯ =====
    generate_triggers = [
        "создай", "сгенерируй", "нарисуй",
        "draw", "generate", "придумай",
        "напиши", "сделай"
    ]

    if any(g in t for g in generate_triggers):
        return "generate"

    # ===== ССЫЛКИ (🔥 НОВОЕ) =====
    link_triggers = [
        "ссылка",
        "url",
        "линк",
        "короткая ссылка",
        "сократи ссылку"
    ]

    if any(l in t for l in link_triggers):
        return "link"

    # ===== ТЕКСТ / СООБЩЕНИЕ =====
    text_triggers = [
        "сообщение",
        "письмо",
        "текст",
        "шаблон"
    ]

    if any(l in t for l in text_triggers):
        return "text"

    # ===== ОБЫЧНЫЙ =====
    return "chat"
