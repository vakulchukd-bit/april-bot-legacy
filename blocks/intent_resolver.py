def is_explicit(text: str) -> bool:
    if not text:
        return False

    ops = ["+", "-", "*", "/", "="]
    keywords = ["реши", "посчитай", "вычисли", "найди"]

    t = text.lower()

    return (
        any(op in text for op in ops)
        or any(word in t for word in keywords)
    )


def is_reference(text: str) -> bool:
    if not text:
        return False

    t = text.lower().strip()

    return t in [
        "да",
        "ок",
        "давай",
        "с этого",
        "начни",
        "поехали"
    ]


def contradicts(last: str, task: str) -> bool:
    """
    Проверяем, не перебивает ли последнее сообщение задачу
    """
    if not last or not task:
        return False

    l = last.lower()

    # если пользователь явно сменил тему
    triggers = [
        "не надо",
        "забудь",
        "отмена",
        "другое",
        "погоди",
    ]

    return any(t in l for t in triggers)


def find_explicit_task(history: list) -> str | None:
    for msg in reversed(history):
        text = msg.get("content", "")
        if is_explicit(text):
            return text
    return None


def resolve_input(history: list) -> dict:
    """
    Главная логика выбора

    return:
    {
        "mode": "execute" | "dialog",
        "text": str
    }
    """

    if not history:
        return {"mode": "dialog", "text": ""}

    last = history[-1]["content"]
    task = find_explicit_task(history)

    # 1. Последнее сообщение = явная задача
    if is_explicit(last):
        return {"mode": "execute", "text": last}

    # 2. Последнее сообщение = ссылка (да/ок)
    if is_reference(last) and task:
        return {"mode": "execute", "text": task}

    # 3. Есть задача в истории и нет конфликта
    if task and not contradicts(last, task):
        return {"mode": "execute", "text": task}

    # 4. Обычный диалог
    return {"mode": "dialog", "text": last}
