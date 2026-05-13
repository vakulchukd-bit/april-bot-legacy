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
        # 🧠 DIALOG STATE
        # =====================================================

        "dialog_state": "exploration",

        "dialog_continuity": True,

        "trajectory_active": True,

        "trajectory_priority": 1.0,

        "unresolved_intent": True,

        "conversation_alive": True,

        "response_requires_reflection": True,

        # =================================================
        # 🧠 CURRENT MESSAGE DOMINANCE
        # =====================================================

        "current_message_mode": "continue",

        "current_message_priority": 0.5,

        "current_request_overrides_flow": False,

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

        "capability_route_confidence": 0.0,

        "capability_should_wait": False,

        "capability_is_guidance": False,

        "capability_is_supportive": True,

        "capability_requires_permission": True,

        "capability_must_follow_dialogue": True
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

        result["confidence"] = 0.82

    # =====================================================
    # 🔥 CURRENT MESSAGE ANALYSIS
    # =====================================================

    execution_words = [

        "создай",
        "сгенерируй",
        "нарисуй",
        "сделай",
        "построй",
        "покажи",
        "отправь"
    ]

    return_words = [

        "вернёмся",
        "продолжим",
        "дальше",
        "снова"
    ]

    exploration_words = [

        "как думаешь",
        "идея",
        "вариант",
        "может",
        "примерно"
    ]

    if any(w in t for w in execution_words):

        result["current_message_mode"] = (
            "execute_now"
        )

        result["current_message_priority"] = 0.92

    elif any(w in t for w in return_words):

        result["current_message_mode"] = (
            "return"
        )

        result["current_message_priority"] = 0.75

    elif any(w in t for w in exploration_words):

        result["current_message_mode"] = (
            "exploration"
        )

        result["current_message_priority"] = 0.45

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

        result["dialog_state"] = "continuation"

        # =================================================
        # 🔥 FLOW OVERRIDE LOGIC
        # =====================================================

        if (
            result["current_message_mode"]
            == "execute_now"
        ):

            if flow_type != "image":

                result[
                    "current_request_overrides_flow"
                ] = True

                result["continuation"] = False

                result["trajectory_strength"] *= 0.4

                result["dialog_state"] = "execution"

    # =====================================================
    # 🔥 IMAGE CONTEXT
    # =====================================================

    image_ctx = state.get("image_context")

    if image_ctx:

        if len(t) < 80:

            result["entity"] = {
                "type": "image",
                "weight": 0.55
            }

            # 🔥 image context НЕ должен ломать trajectory
            result["trajectory_strength"] += 0.1

    # =====================================================
    # 🔥 LAST MATH
    # =====================================================

    last_math = state.get("last_math")

    if last_math:

        if any(w in t for w in [
            "график",
            "это",
            "теперь"
        ]):

            result["entity"] = {
                "type": "math",
                "weight": 0.7
            }

    # =====================================================
    # 🔥 SIMPLE INTENT MAPPING
    # =====================================================

    intent = result["intent"]

    if intent == "math":

        result["room"] = "science"

        result["capability_confidence"] = 0.88

        result["expected_result"] = "solution"

        result["best_capability"] = "science"

    elif intent == "code":

        result["room"] = "text"

        result["capability_confidence"] = 0.72

        result["expected_result"] = "implementation"

        result["best_capability"] = "text"

    elif intent == "image":

        result["room"] = "image_generate"

        result["capability_confidence"] = 0.88

        result["expected_result"] = "visual"

        result["expected_output_type"] = "image"

        result["best_capability"] = "image_generate"

    # =====================================================
    # 🔥 EXPLORATION DETECTION
    # =====================================================

    exploration_words = [
        "что умеешь",
        "примерно",
        "идея",
        "вариант",
        "посмотрим",
        "подумаем",
        "как думаешь",
        "что можешь",
        "референс",
        "атмосфера"
    ]

    if any(w in t for w in exploration_words):

        result["dialog_state"] = "exploration"

        result["ambiguity_level"] += 0.35

        result["conversation_value"] += 0.25

        result["trajectory_strength"] += 0.25

        result["capability_should_wait"] = True

        result["needs_clarification"] = True

        result["goal_stage"] = "exploration"

    # =====================================================
    # 🔥 VISUAL EXPECTATION FORMULAS
    # =====================================================

    visual_words = [
        "пример",
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

        result["visual_expectation"] += 0.55

        result["example_expectation"] += 0.45

        result["should_offer_visual"] = True

        result["visual_routing"] = True

        result["expected_output_type"] = "visual"

        result["attention_weight"] += 0.15

    # =====================================================
    # 🔥 DEMO / GUIDED VISUALS
    # =====================================================

    demo_words = [
        "покажи пример",
        "можешь показать",
        "как это выглядит",
        "можно пример"
    ]

    if any(w in t for w in demo_words):

        result["visual_demo_request"] = True

        result["visual_expectation"] += 0.2

        result["example_expectation"] += 0.3

        result["assistant_initiative"] += 0.2

        result["visual_lightweight_mode"] = True

        result["capability_is_guidance"] = True

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

        result["capability_should_wait"] = True

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

        result["execution_readiness"] += 0.35

    else:

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

        result["example_expectation"] += 0.5

    # =====================================================
    # 🔥 CAPABILITY UNDERSTANDING LAYER
    # =====================================================

    capability_signals = 0.0

    informational_signals = [

        "информация",
        "данные",
        "что известно",
        "что происходит",
        "расскажи",
        "объясни",
        "покажи",
        "помоги понять",
        "можешь помочь",
        "что можешь сказать"
    ]

    execution_signals = [

        "создай",
        "сгенерируй",
        "нарисуй",
        "построй",
        "выполни"
    ]

    continuation_signals = [

        "дальше",
        "продолжим",
        "вернемся",
        "теперь",
        "еще"
    ]

    if any(w in t for w in informational_signals):

        capability_signals += 0.25

        result["conversation_alive"] = True

        result["unresolved_intent"] = True

        result["response_requires_reflection"] = True

        result["capability_is_supportive"] = True

        result["capability_must_follow_dialogue"] = True

        result["assistant_initiative"] += 0.15

    if any(w in t for w in execution_signals):

        capability_signals += 0.45

        result["execution_readiness"] += 0.35

    if any(w in t for w in continuation_signals):

        capability_signals += 0.15

        result["trajectory_strength"] += 0.15

        result["dialog_continuity"] = True

    result["capability_route_confidence"] = min(
        1.0,
        result["capability_route_confidence"]
        + capability_signals
    )

    # =====================================================
    # 🔥 EXECUTION PRESSURE
    # =====================================================

    pressure = 0.0

    execution_words = [
        "сделай",
        "выполни",
        "создай",
        "нарисуй",
        "сгенерируй",
        "построй"
    ]

    if any(w in t for w in execution_words):

        pressure += 0.4

        result["execution_readiness"] += 0.4

    if (
        result["continuation"]
        and len(t) <= 40
    ):

        pressure += 0.15

        result["trajectory_strength"] += 0.2

    if flow_type:

        pressure += 0.08

    escalation_words = [
        "уже",
        "хватит",
        "просто",
        "давай"
    ]

    if any(w in t for w in escalation_words):

        pressure += 0.2

        result["attention_weight"] = 0.9

        result["assistant_initiative"] += 0.3

    result["execution_pressure"] = min(
        pressure,
        1.0
    )

    # =====================================================
    # 🔥 AMBIGUITY
    # =====================================================

    if len(t.split()) <= 3:

        result["ambiguity_level"] += 0.35

    if (
        result["visual_expectation"] >= 0.6
        and result["intent"] == "text"
    ):

        result["ambiguity_level"] += 0.25

    if result["dialog_state"] == "exploration":

        result["ambiguity_level"] += 0.2

    if result["ambiguity_level"] >= 0.55:

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

        result["assistant_initiative"] += 0.4

        result["dialog_state"] = "guidance"

    # =====================================================
    # 🔥 CONVERSATION VALUE
    # =====================================================

    conversation_value = 1.0

    if result["execution_pressure"] >= 0.65:

        conversation_value -= 0.25

    if len(history) >= 8:

        conversation_value -= 0.15

    if result["dialog_state"] == "exploration":

        conversation_value += 0.2

    result["conversation_value"] = max(
        conversation_value,
        0.1
    )

    # =====================================================
    # 🔥 GOAL STAGE
    # =====================================================

    if result["dialog_state"] == "exploration":

        result["goal_stage"] = "exploration"

    elif result["guidance_need"] >= 0.7:

        result["goal_stage"] = "guidance"

    elif result["execution_pressure"] >= 0.8:

        result["goal_stage"] = "execution"

    elif result["continuation"]:

        result["goal_stage"] = "continuation"

    # =====================================================
    # 🔥 SHOULD EXECUTE
    # =====================================================

    if (
        result["execution_pressure"] >= 0.72
        and result["capability_confidence"] >= 0.72
        and not result["capability_should_wait"]
        and result["ambiguity_level"] < 0.55
    ):

        result["should_execute"] = True

        result["response_mode"] = "execute"

    else:

        result["should_execute"] = False

        result["response_mode"] = "talk"

    # =====================================================
    # 🔥 VISUAL ESCALATION
    # =====================================================

    if (
        result["visual_expectation"] >= 0.8
        and result["visual_generation_needed"]
        and not result["capability_should_wait"]
    ):

        result["should_offer_visual"] = True

        result["room"] = "image_generate"

    # =====================================================
    # 🔥 RESPONSE ECONOMY
    # =====================================================

    if result["execution_pressure"] >= 0.75:

        result["response_economy"] = "minimal"

    elif result["conversation_value"] >= 0.85:

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
        "поехали"
    ]

    if (
        len(t) > 120
        or result["confidence"] < 0.58
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

    # =====================================================
    # 🔥 FINAL TRAJECTORY STABILIZATION
    # =====================================================

    if result["dialog_state"] == "exploration":

        result["preserve_flow"] = True

        result["conversation_alive"] = True

        result["unresolved_intent"] = True

        result["response_requires_reflection"] = True

    return result
