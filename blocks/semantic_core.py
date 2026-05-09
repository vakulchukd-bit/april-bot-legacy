# blocks/semantic_core.py

from blocks.interpretation_layer import interpret_request


def analyze(
    text: str,
    state: dict = None,
    history: list = None,
    active_flow: dict = None,
    dialog_state: dict = None
):

    text = (text or "").strip()

    t = text.lower()

    state = state or {}
    history = history or []
    active_flow = active_flow or {}
    dialog_state = dialog_state or {}

    # =====================================================
    # 🔥 BASE RESULT
    # =====================================================

    result = {

        # ===== semantic intent =====
        "intent": "text",

        # ===== confidence =====
        "confidence": 0.5,

        # ===== target room =====
        "room": "text",

        # ===== continuation =====
        "continuation": False,

        # ===== continuation target =====
        "continuation_target": None,

        # ===== active semantic entity =====
        "entity": {
            "type": None,
            "weight": 0.0
        },

        # ===== user goal =====
        "goal": None,

        # ===== normalized semantic meaning =====
        "normalized_text": text,

        # ===== AI escalation =====
        "requires_ai": False,

        # ===== complexity =====
        "complexity": "low",

        # ===== preserve flow =====
        "preserve_flow": True,

        # ===== topic changed =====
        "topic_shift": False
    }

    # =====================================================
    # 🔥 INTERPRETATION LAYER
    # =====================================================

    interpreted = interpret_request(text)

    if interpreted:

        result["intent"] = interpreted.get(
            "type",
            "text"
        )

        result["normalized_text"] = interpreted.get(
            "normalized",
            text
        )

        result["confidence"] = 0.9

    # =====================================================
    # 🔥 ACTIVE FLOW
    # =====================================================

    flow_type = active_flow.get("type")

    if flow_type:

        result["continuation"] = True
        result["continuation_target"] = flow_type

        result["entity"] = {
            "type": flow_type,
            "weight": 0.8
        }

    # =====================================================
    # 🔥 IMAGE CONTEXT
    # =====================================================

    image_ctx = state.get("image_context")

    if image_ctx:

        if len(t) < 80:

            result["entity"] = {
                "type": "image",
                "weight": 0.7
            }

    # =====================================================
    # 🔥 LAST MATH
    # =====================================================

    last_math = state.get("last_math")

    if last_math:

        if any(w in t for w in [
            "график",
            "покажи",
            "это",
            "теперь"
        ]):

            result["entity"] = {
                "type": "math",
                "weight": 0.75
            }

    # =====================================================
    # 🔥 SIMPLE INTENT MAPPING
    # =====================================================

    intent = result["intent"]

    if intent == "math":
        result["room"] = "science"

    elif intent == "code":
        result["room"] = "text"

    elif intent == "image":
        result["room"] = "image_generate"

    # =====================================================
    # 🔥 AI ESCALATION
    # =====================================================

    short_triggers = [
        "да",
        "ок",
        "ага",
        "поехали",
        "покажи"
    ]

    if (
        len(t) > 120
        or result["confidence"] < 0.6
    ):

        result["requires_ai"] = True
        result["complexity"] = "medium"

    if t in short_triggers:

        result["requires_ai"] = False
        result["complexity"] = "low"

    # =====================================================
    # 🔥 TOPIC SHIFT
    # =====================================================

    if len(t) > 30:

        if result["entity"]["type"]:

            if result["entity"]["type"] not in t:
                result["topic_shift"] = True

    return result
