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

        # ===============================
        # 🔥 STEP 6: CONTEXT PRIORITY (УСИЛЕННЫЙ)
        # ===============================
        if ctx:
            dialog = ctx.get("dialog_state") or {}

            # IMAGE CONTEXT
            if dialog.get("intent") == "image":

                # 🔥 1. ЯВНЫЙ EDIT
                if any(w in t for w in ["измени", "добавь", "убери", "замени"]):
                    return "image_edit"

                # 🔥 2. НЕЯВНЫЙ EDIT (КЛЮЧЕВОЕ!)
                if any(w in t for w in [
                    "сделай", "покажи", "изобрази", "нарисуй",
                    "вот это", "это", "с этим", "его", "ее"
                ]):
                    return "image_edit"

                # 🔥 3. АНАЛИЗ
                if "что" in t and "картин" in t:
                    return "image_analyze"

                # 🔥 4. ПО УМОЛЧАНИЮ → РЕДАКТИРОВАНИЕ (а не generate!)
                return "image_edit"

            # MATH CONTEXT
            if dialog.get("intent") == "math":
                return "math"

        # 🔥 1. Сначала локально (БЕСПЛАТНО)
        local = detect_intent_local(text)
        if local:
            if local == "image_edit" and not ctx:
                return "text"
            if local == "image_analyze" and not ctx:
                return "text"
            return local

        # 🔥 2. Короткие сообщения
        if len(t) < 15:
            return "text"

        # 🔥 3. AI fallback
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
