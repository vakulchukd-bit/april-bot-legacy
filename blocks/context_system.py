# blocks/context_system.py

def build_context_text(user_id, text, state):
    """
    УМНЫЙ контекст April.
    Решает проблему "это" через явную структуру.
    """

    base = "Ты — April, живой собеседник. Отвечай естественно и по делу."

    history = ""
    last_user_task = None

    dialog = state.get("dialog", [])

    # ===== 🧠 ПОСЛЕДНИЕ СООБЩЕНИЯ =====
    for msg in dialog[-5:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        history += f"{role}: {content}\n"

    # ===== 🔍 ПОИСК ПОСЛЕДНЕЙ ЗАДАЧИ =====
    for msg in reversed(dialog):
        if msg.get("role") == "user":
            content = msg.get("content", "")

            if any(x in content.lower() for x in ["было", "отдал", "сколько", "задач", "яблок"]):
                last_user_task = content
                break

    # ===== 🧠 SUMMARY =====
    summary = state.get("memory_summary")
    if summary:
        short = summary[-200:]
        base += f"\nКонтекст: {short}"

    # ===== 🖼️ IMAGE CONTEXT =====
    img = state.get("image_context")
    if img and isinstance(img, dict):
        hint = img.get("hint") or img.get("prompt")
        if hint:
            short_hint = hint[:120]
            base += f"\nИзображение: {short_hint}"

    # ===== 🔥 ФИНАЛЬНАЯ СБОРКА =====
    if last_user_task:
        full = f"""
{base}

Диалог:
{history}

Последняя задача:
{last_user_task}

Текущий запрос:
{text}

Если пользователь говорит "это" — используй последнюю задачу.
"""
    else:
        full = f"""
{base}

Диалог:
{history}

Текущий запрос:
{text}
"""

    return full


# 🔥 УМНЫЙ SUMMARY (ОСТАВЛЯЕМ)
def update_memory_summary(state, user_text, bot_reply):
    """
    Сохраняем только СМЫСЛ, а не весь диалог.
    """

    old = state.get("memory_summary", "")

    user_text = (user_text or "")[:120]
    bot_reply = (bot_reply or "")[:120]

    chunk = f"{user_text} → {bot_reply}"

    combined = (old + " | " + chunk).strip()

    if len(combined) > 300:
        combined = combined[-300:]

    state["memory_summary"] = combined
