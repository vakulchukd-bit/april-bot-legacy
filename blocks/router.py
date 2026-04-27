from blocks.intent_ai import detect_intent_ai


async def route_request(text, ctx):
    try:
        intent = await detect_intent_ai(text)
        print("🧭 ROUTER INTENT:", intent)

        # 🔥 НЕ ДАЁМ AI ПЕРЕБИТЬ МАТЕМАТИКУ
        t = text.lower()

        if any(x in t for x in ["=", "x", "+", "-", "*", "/"]):
            return "math"

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
