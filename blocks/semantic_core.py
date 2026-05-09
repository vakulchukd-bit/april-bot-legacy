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
        # =====================================================

        "execution_pressure": 0.0,
        "conversation_value": 1.0,
        "response_economy": "balanced",
        "capability_confidence": 0.5,
        "goal_stage": "exploration",
        "should_execute": False,
        "response_mode": "talk",
        "attention_weight": 0.5,

        # =================================================
        # 🔥 EXPECTATION MODELING
        # =====================================================

        "expected_result": None,
        "expected_output_type": "text",
        "visual_expectation": 0.0,
        "example_expectation": 0.0,
        "execution_readiness": 0.0,
        "guidance_need": 0.0,
        "ambiguity_level": 0.0,
        "needs_clarification": False,
        "should_proactively_help": False,
        "user_certainty": 0.5,
        "trajectory_strength": 0.5,
        "should_offer_visual": False,
        "should_offer_examples": False,
        "assistant_initiative": 0.0,

        # =================================================
        # 🔥 VISUAL GUIDANCE SYSTEM
        # =====================================================

        "visual_routing": False,
        "visual_lightweight_mode": False,
        "library_visual_candidate": False,
        "visual_demo_request": False,
        "visual_generation_needed": False,

        # =================================================
        # 🔥 CAPABILITY AWARENESS
        # =====================================================

        "understands_capabilities": True,
        "best_capability": None,
        "capability_route_confidence": 0.0
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

        result["trajectory_strength"] += 0.25

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

        result["expected_result"] = "solution"

        result["best_capability"] = "science"

    elif intent == "code":

        result["room"] = "text"

        result["capability_confidence"] = 0.7

        result["expected_result"] = "implementation"

        result["best_capability"] = "text"

    elif intent == "image":

        result["room"] = "image_generate"

        result["capability_confidence"] = 0.95

        result["expected_result"] = "visual"

        result["expected_output_type"] = "image"

        result["best_capability"] = "image_generate"

    # =====================================================
    # 🔥 VISUAL EXPECTATION FORMULAS
    # =====================================================

    visual_words = [
        "пример",
        "покажи",
        "визуально",
        "как выглядит",
        "референс",
        "фото",
        "картинка",
        "схема",
        "чертеж",
        "концепт",
        "дизайн",
        "стиль",
        "интерьер",
        "вариант"
    ]

    if any(w in t for w in visual_words):

        result["visual_expectation"] += 0.85

        result["example_expectation"] += 0.7

        result["should_offer_visual"] = True

        result["visual_routing"] = True

        result["expected_output_type"] = "visual"

        result["attention_weight"] += 0.2

    # =====================================================
    # 🔥 EXAMPLE DEMONSTRATION FORMULAS
    # =====================================================

    demo_words = [
        "покажи пример",
        "можешь показать",
        "примерно",
        "как это выглядит",
        "как будет выглядеть",
        "можно пример",
        "референс"
    ]

    if any(w in t for w in demo_words):

        result["visual_demo_request"] = True

        result["visual_expectation"] += 0.3

        result["example_expectation"] += 0.4

        result["assistant_initiative"] += 0.3

    # =====================================================
    # 🔥 LIGHTWEIGHT VISUAL MODE
    # =====================================================

    lightweight_words = [
        "пример",
        "идея",
        "референс",
        "вариант",
        "концепт"
    ]

    if any(w in t for w in lightweight_words):

        result["visual_lightweight_mode"] = True

        result["library_visual_candidate"] = True

    # =====================================================
    # 🔥 VISUAL ROOM ESCALATION
    # =====================================================

    if (
        result["visual_expectation"] >= 0.7
    ):

        result["room"] = "image_generate"

        result["capability_confidence"] = max(
            result["capability_confidence"],
            0.9
        )

        result["best_capability"] = "image_generate"

        result["capability_route_confidence"] = 0.9

    # =====================================================
    # 🔥 GENERATION CONTROL
    # =====================================================

    generation_words = [
        "создай",
        "сгенерируй",
        "нарисуй",
        "сделай изображение"
    ]

    if any(w in t for w in generation_words):

        result["visual_generation_needed"] = True

    else:

        # 🔥 avoid expensive generation
        if result["visual_demo_request"]:

            result["visual_generation_needed"] = False

            result["visual_lightweight_mode"] = True

    # =====================================================
    # 🔥 EXPECTATION SIGNALS
    # =====================================================

    example_words = [
        "пример",
        "вариант",
        "образец",
        "идея"
    ]

    if any(w in t for w in example_words):

        result["should_offer_examples"] = True

        result["example_expectation"] += 0.7

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

        result["execution_readiness"] += 0.5

    if (
        result["continuation"]
        and len(t) <= 40
    ):

        pressure += 0.25

        result["trajectory_strength"] += 0.2

    if flow_type:

        pressure += 0.15

    escalation_words = [
        "уже",
        "хватит",
        "просто",
        "давай"
    ]

    if any(w in t for w in escalation_words):

        pressure += 0.25

        result["attention_weight"] = 0.9

        result["assistant_initiative"] += 0.4

    result["execution_pressure"] = min(
        pressure,
        1.0
    )

    # =====================================================
    # 🔥 AMBIGUITY
    # =====================================================

    if len(t.split()) <= 3:

        result["ambiguity_level"] += 0.4

    if (
        result["visual_expectation"] >= 0.6
        and result["intent"] == "text"
    ):

        result["ambiguity_level"] += 0.3

    if result["ambiguity_level"] >= 0.65:

        result["needs_clarification"] = True

    # =====================================================
    # 🔥 GUIDANCE MODEL
    # =====================================================

    guidance_words = [
        "не знаю",
        "помоги",
        "подскажи",
        "как лучше",
        "что выбрать"
    ]

    if any(w in t for w in guidance_words):

        result["guidance_need"] += 0.8

        result["should_proactively_help"] = True

        result["assistant_initiative"] += 0.5

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

    elif result["guidance_need"] >= 0.7:

        result["goal_stage"] = "guidance"

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
    # 🔥 VISUAL ESCALATION
    # =====================================================

    if (
        result["visual_expectation"] >= 0.7
        and result["capability_confidence"] >= 0.7
    ):

        result["should_offer_visual"] = True

        result["room"] = "image_generate"

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
