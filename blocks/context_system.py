# blocks/context_system.py

def build_context_text(state=None):
    """
    Главный контекст April.
    НЕ импортирует другие модули → нет циклов.
    """

    # 🔥 УЖАТЫЙ SYSTEM (экономия токенов)
    base = "Ты — April, живой собеседник и анализатор личности. Отвечай естественно, точно и адаптируйся под пользователя."

    # ===== 🔥 ДИНАМИКА =====
    if state:

        # --- настроение ---
        mood = state.get("mood")
        if mood:
            base += f"\nТекущее состояние пользователя: {mood}"

        # ===== 🧠 SUMMARY (СМЫСЛ ПРОШЛОГО) =====
        summary = state.get("memory_summary")
        if summary:
            base += f"\n\nКонтекст диалога (смысл):\n{summary}"

        # ===== 🖼️ IMAGE CONTEXT =====
        img = state.get("image_context")
        if img and isinstance(img, dict):

            hint = img.get("hint") or img.get("prompt")

            if hint:
                base += f"\n\nПоследняя работа с изображением:\n{hint}"

    return base


# 🔥 НОВОЕ: УМНЫЙ SUMMARY (дешёвый, без API)
def update_memory_summary(state, user_text, bot_reply):
    """
    Сжимает диалог в смысл.
    Без использования OpenAI → бесплатно.
    """

    old = state.get("memory_summary", "")

    # защищаемся от None
    user_text = user_text or ""
    bot_reply = bot_reply or ""

    # 🔥 формируем смысловой кусок
    chunk = f"Пользователь: {user_text}\nОтвет: {bot_reply}"

    combined = (old + "\n" + chunk).strip()

    # 🔥 ограничение размера (очень важно для токенов)
    if len(combined) > 1000:
        combined = combined[-1000:]

    state["memory_summary"] = combined
