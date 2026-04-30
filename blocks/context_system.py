# blocks/context_system.py

def build_context_text(state=None):
    """
    Главный контекст April.
    УЖАТЫЙ и адаптивный → не перегружает токены.
    """

    base = "Ты — April, живой собеседник. Отвечай естественно и по делу."

    if state:

        # --- настроение (оставляем, это дешево и полезно) ---
        mood = state.get("mood")
        if mood:
            base += f"\nСостояние пользователя: {mood}"

        # ===== 🧠 СЖАТЫЙ SUMMARY =====
        summary = state.get("memory_summary")
        if summary:
            # 🔥 ограничиваем до короткого смысла
            short = summary[-200:]
            base += f"\nКонтекст: {short}"

        # ===== 🖼️ IMAGE CONTEXT (ТОЖЕ СЖАТЫЙ) =====
        img = state.get("image_context")
        if img and isinstance(img, dict):

            hint = img.get("hint") or img.get("prompt")

            if hint:
                short_hint = hint[:120]
                base += f"\nИзображение: {short_hint}"

    return base


# 🔥 УМНЫЙ SUMMARY (РЕАЛЬНО СЖАТЫЙ)
def update_memory_summary(state, user_text, bot_reply):
    """
    Сохраняем только СМЫСЛ, а не весь диалог.
    Бесплатно и очень компактно.
    """

    old = state.get("memory_summary", "")

    user_text = (user_text or "")[:120]

    # 🔥 берём только начало ответа (смысл)
    bot_reply = (bot_reply or "")[:120]

    # 🔥 короткая форма (без "Пользователь/Ответ")
    chunk = f"{user_text} → {bot_reply}"

    combined = (old + " | " + chunk).strip()

    # 🔥 ЖЁСТКОЕ ограничение
    if len(combined) > 300:
        combined = combined[-300:]

    state["memory_summary"] = combined
