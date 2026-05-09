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
        "topic_shift": False,

        # =================================================
        # 🧠 BEHAVIOR FORMULAS
        # =================================================

        # ===== execution pressure =====
        "execution_pressure": 0.0,

        # ===== conversation usefulness =====
        "conversation_value": 1.0,

        # ===== response economy =====
        "response_economy": "balanced",

        # ===== capability confidence =====
        "capability_confidence": 0.5,

        # ===== current dialog stage =====
        "goal_stage": "exploration",

        # ===== should execute =====
        "should_execute": False,

        # ===== response mode =====
        "response_mode": "talk",

        # ===== attention weight =====
        "attention_weight": 0.5
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

        result["capability_confidence"] = 0.9

    elif intent == "code":

        result["room"] = "text"

        result["capability_confidence"] = 0.7

    elif intent == "image":

        result["room"] = "image_generate"

        result["capability_confidence"] = 0.95

    # =====================================================
    # 🔥 EXECUTION PRESSURE
    # =====================================================

    pressure = 0.0

    execution_words = [
        "сделай",
        "выполни",
        "создай",
        "нарисуй",
        "покажи",
        "сгенерируй",
        "построй"
    ]

    if any(w in t for w in execution_words):

        pressure += 0.45

    # 🔥 short continuation pressure
    if (
        result["continuation"]
        and len(t) <= 40
    ):

        pressure += 0.25

    # 🔥 repeated unresolved flow
    if flow_type:

        pressure += 0.15

    # 🔥 escalation words
    escalation_words = [
        "уже",
        "хватит",
        "просто",
        "давай"
    ]

    if any(w in t for w in escalation_words):

        pressure += 0.25

        result["attention_weight"] = 0.9

    result["execution_pressure"] = min(
        pressure,
        1.0
    )

    # =====================================================
    # 🔥 CONVERSATION VALUE
    # =====================================================

    conversation_value = 1.0

    if result["execution_pressure"] >= 0.6:

        conversation_value -= 0.5

    if len(history) >= 8:

        conversation_value -= 0.2

    result["conversation_value"] = max(
        conversation_value,
        0.1
    )

    # =====================================================
    # 🔥 GOAL STAGE
    # =====================================================

    if result["execution_pressure"] >= 0.75:

        result["goal_stage"] = "execution"

    elif result["continuation"]:

        result["goal_stage"] = "continuation"

    elif result["confidence"] >= 0.8:

        result["goal_stage"] = "clarification"

    # =====================================================
    # 🔥 SHOULD EXECUTE
    # =====================================================

    if (
        result["execution_pressure"] >= 0.65
        and result["capability_confidence"] >= 0.7
    ):

        result["should_execute"] = True

        result["response_mode"] = "execute"

    # =====================================================
    # 🔥 RESPONSE ECONOMY
    # =====================================================

    if result["execution_pressure"] >= 0.7:

        result["response_economy"] = "minimal"

    elif result["conversation_value"] >= 0.8:

        result["response_economy"] = "expanded"

    else:

        result["response_economy"] = "balanced"

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
    
