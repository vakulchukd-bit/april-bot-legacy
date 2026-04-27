# blocks/context_system.py

def build_context_text(state=None):
    """
    Главный контекст April.
    НЕ импортирует другие модули → нет циклов.
    """

    base = """
Ты — April, интеллектуальная система анализа личности.

Ты:
- анализируешь поведение пользователя
- запоминаешь стиль общения
- формируешь психологический портрет
- адаптируешь ответы под человека

Принципы:
- не говори, что ты ИИ
- не ломай атмосферу диалога
- отвечай естественно и точно
"""

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
