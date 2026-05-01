# ===============================
# 🔥 SAFE PATCH MODE (INTENT SYSTEM)
# ===============================

PATCH_LOG = []

def safe_patch_log(msg):
    try:
        print("INTENT PATCH:", msg)
        PATCH_LOG.append(msg)
    except:
        pass


# 🔥 PATCH: контроль определения намерения
def patch_intent_detect(text):
    safe_patch_log(f"INTENT DETECT: {text[:50]}")
    return text


# 🔥 PATCH: будущая логика намерений
def patch_intent_future(*args, **kwargs):
    return None
def detect_intent(text: str):
    t = text.lower().strip()

    # ===== ССЫЛКИ (СНАЧАЛА — ЧТОБ НЕ ПЕРЕБИВАЛОСЬ) =====
    link_triggers = [
        "ссылка",
        "url",
        "линк",
        "короткая ссылка",
        "сократи ссылку",
        "short link"
    ]

    if any(l in t for l in link_triggers):
        return "link"

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
        "ярче", "темнее", "переделай",
        "исправь"
    ]

    if any(v in t for v in edit_triggers):
        return "edit"

    # ===== ГЕНЕРАЦИЯ (ВАЖНО: ПОСЛЕ EDIT) =====
    generate_triggers = [
        "создай", "сгенерируй", "нарисуй",
        "draw", "generate", "придумай",
        "напиши", "сделай"
    ]

    if any(g in t for g in generate_triggers):
        return "generate"

    # ===== ТЕКСТ / СООБЩЕНИЕ =====
    text_triggers = [
        "сообщение",
        "письмо",
        "текст",
        "шаблон",
        "ответ клиенту"
    ]

    if any(l in t for l in text_triggers):
        return "text"

    # ===== ОБЫЧНЫЙ =====
    return "chat"
