from blocks.intent_ai import detect_intent_ai


def detect_intent_local(text: str):
    t = text.lower()

    # 🔥 математика (самый приоритет)
    if any(x in t for x in ["=", "+", "-", "*", "/"]):
        return "math"

    # 🔥 генерация
    if any(x in t for x in ["нарисуй", "создай", "сгенерируй", "картинку", "изображение"]):
        return "image_generate"

    # 🔥 редактирование
    if any(x in t for x in ["измени", "добавь", "убери", "замени"]):
        return "image_edit"

    # 🔥 анализ картинки
    if any(x in t for x in ["что на картинке", "что изображено", "что это"]):
        return "image_analyze"

    return None


async def route_request(text, ctx):
    try:
        t = text.lower().strip()

        state = (ctx or {}).get("state", {})
        dialog = (ctx or {}).get("dialog_state", {}) or {}

        # ===============================
        # 🔥 NEW: META AWARENESS (СИСТЕМНЫЙ СЛОЙ)
        # ===============================
        meta = state.get("meta", {})
        last_entity = meta.get("last_entity")

        if last_entity and last_entity.get("type") == "image":
            # если пользователь не пишет длинный новый запрос —
            # считаем это продолжением работы с изображением
            if len(t) < 80:
                print("🧠 META ROUTING → IMAGE_EDIT")
                return "image_edit"

        # ===============================
        # 🔥 CONTEXT PRIORITY (ТВОЙ СЛОЙ)
        # ===============================
        if dialog.get("intent") == "image":

            # явный edit
            if any(w in t for w in ["измени", "добавь", "убери", "замени"]):
                return "image_edit"

            # анализ
            if "что" in t and "картин" in t:
                return "image_analyze"

            # по умолчанию теперь логичнее edit
            return "image_edit"

        if dialog.get("intent") == "math":
            return "math"

        # ===============================
        # 🔥 LOCAL INTENT (БЫСТРО И ДЁШЕВО)
        # ===============================
        local = detect_intent_local(text)
        if local:
            if local == "image_edit" and not ctx:
                return "text"
            if local == "image_analyze" and not ctx:
                return "text"
            return local

        # ===============================
        # 🔥 SHORT TEXT (НЕ ГОНЯЕМ В AI)
        # ===============================
        if len(t) < 15:
            return "text"

        # ===============================
        # 🔥 AI FALLBACK
        # ===============================
        intent = await detect_intent_ai(text)
        print("🧭 ROUTER INTENT:", intent)

        if intent == "generate_image":
            return "image_generate"

        if intent == "edit_image" and ctx:
            return "image_edit"

        if intent == "analyze_image" and ctx:
            return "image_analyze"

        return "text"

    except Exception as e:
        print("🔥 ROUTER ERROR:", e)
        return "text"
