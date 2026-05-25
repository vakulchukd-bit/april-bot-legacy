# blocks/semantic_core.py

from blocks.interpretation_layer import interpret_request


# =====================================================
# 🔥 HELPERS
# =====================================================

def clamp(
    value,
    minimum=0.0,
    maximum=1.0
):

    if value < minimum:
        return minimum

    if value > maximum:
        return maximum

    return value


def contains_any(
    text,
    words
):

    return any(
        w in text
        for w in words
    )


# =====================================================
# 🔥 SAFE RENDER DETECTION
# =====================================================

def contains_math_expression(
    text
):

    if not text:
        return False

    checks = [

        "y=",
        "y =",
        "x**",
        "^2",
        "^3",
        "sin(",
        "cos(",
        "tan(",
        "log(",
        "sqrt(",
        "f(x)",
        "f(x) ="
    ]

    return any(
        x in text.lower()
        for x in checks
    )


def looks_like_renderer_request(
    text
):

    if not text:
        return False

    t = text.lower()

    renderer_words = [

        "график",
        "графика",
        "функция",
        "формула",
        "уравнение",
        "таблица",
        "сетка",
        "layout",
        "diagram",
        "схема",
        "line",
        "стрелка"
    ]

    if contains_any(
        t,
        renderer_words
    ):

        return True

    if contains_math_expression(
        t
    ):

        return True

    return False


def is_explicit_image_generation(
    text
):

    if not text:
        return False

    t = text.lower()

    explicit_generation_words = [

        "создай изображение",
        "сгенерируй изображение",
        "нарисуй картинку",
        "создай картинку",
        "draw image",
        "generate image",
        "создай арт",
        "сделай арт"
    ]

    return contains_any(
        t,
        explicit_generation_words
    )


# =====================================================
# 🔥 ANALYZE
# =====================================================

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
        # 🔥 RENDERER-FIRST SYSTEM
        # =====================================================

        "render_intent": False,

        "render_type": None,

        "renderer_priority": 0.0,

        "renderer_expected_output": None,

        "renderer_scene_object": False,

        "renderer_lightweight": True,

        "prefer_renderer": False,

        "explicit_image_generation_only": False,

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

        "capability_must_follow_dialogue": True,

        # =================================================
        # 🔥 WEB-FIRST STABILIZATION
        # =====================================================

        "prefer_web_context": False,

        "internet_context_needed": False,

        "travel_context": False,

        "geo_context": False,

        "realtime_context": False,

        # =================================================
        # 🔥 VISUAL CONTINUITY
        # =====================================================

        "visual_continuity": False,

        "active_visual_scene_detected": False,

        "scene_reference_detected": False,

        # =================================================
        # 🔥 PROVIDER-AWARE
        # =====================================================

        "prefer_local_rendering": False,

        "avoid_image_generation_fallback": True,

        "provider_safe_mode": True
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

    if contains_any(
        t,
        execution_words
    ):

        result["current_message_mode"] = (
            "execute_now"
        )

        result["current_message_priority"] = 0.92

    elif contains_any(
        t,
        return_words
    ):

        result["current_message_mode"] = (
            "return"
        )

        result["current_message_priority"] = 0.75

    elif contains_any(
        t,
        exploration_words
    ):

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

        if (
            result["current_message_mode"]
            == "execute_now"
        ):

            if flow_type not in [

                "image",
                "image_generate",
                "image_edit"
            ]:

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

            result["trajectory_strength"] += 0.1

    # =====================================================
    # 🔥 VISUAL SCENE CONTINUITY
    # =====================================================

    active_visual_scene = state.get(
        "active_visual_scene"
    )

    if active_visual_scene:

        result[
            "active_visual_scene_detected"
        ] = True

        visual_objects = active_visual_scene.get(
            "objects",
            []
        )

        visual_summary = active_visual_scene.get(
            "summary",
            ""
        ).lower()

        short_followup = (
            len(t) <= 120
        )

        visual_reference_words = [

            "это",
            "этот",
            "эта",
            "цвет",
            "сторона",
            "объект",
            "кубик",
            "картинка",
            "фото",
            "изображение",
            "меню",
            "бокал",
            "бургер",
            "креветки",
            "улица",
            "машина"
        ]

        reference_match = any(
            w in t
            for w in visual_reference_words
        )

        object_match = any(
            obj.lower() in t
            for obj in visual_objects
        )

        summary_match = any(
            word in visual_summary
            for word in t.split()
            if len(word) >= 4
        )

        visual_continuation_confidence = 0.0

        if short_followup:
            visual_continuation_confidence += 0.25

        if reference_match:
            visual_continuation_confidence += 0.35

        if object_match:
            visual_continuation_confidence += 0.35

        if summary_match:
            visual_continuation_confidence += 0.2

        if (
            visual_continuation_confidence
            >= 0.45
        ):

            result["continuation"] = True

            result["continuation_target"] = (
                "visual_scene"
            )

            result["entity"] = {
                "type": "image",
                "weight": 0.92
            }

            result["trajectory_strength"] += 0.45

            result["dialog_state"] = (
                "visual_continuation"
            )

            result["visual_routing"] = True

            result["expected_output_type"] = (
                "visual"
            )

            result["attention_weight"] += 0.25

            result["capability_confidence"] = max(
                result["capability_confidence"],
                0.88
            )

            result["preserve_flow"] = True

            result["visual_continuity"] = True

            result[
                "scene_reference_detected"
            ] = True

            print(
                "🧠 VISUAL CONTINUITY DETECTED"
            )

    # =====================================================
    # 🔥 LAST MATH
    # =====================================================

    last_math = state.get("last_math")

    if last_math:

        if contains_any(
            t,
            [
                "график",
                "это",
                "теперь"
            ]
        ):

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

    if contains_any(
        t,
        exploration_words
    ):

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

    if contains_any(
        t,
        visual_words
    ):

        result["visual_expectation"] += 0.55

        result["example_expectation"] += 0.45

        result["should_offer_visual"] = True

        result["visual_routing"] = True

        result["expected_output_type"] = "visual"

        result["attention_weight"] += 0.15

    # =====================================================
    # 🔥 WEB / REALTIME DETECTION
    # =====================================================

    web_words = [

        "погода",
        "курс валют",
        "новости",
        "что происходит",
        "сейчас",
        "где находится",
        "маршрут",
        "как доехать",
        "карта",
        "рейс",
        "поезд",
        "автобус",
        "такси",
        "отель",
        "локация"
    ]

    if contains_any(
        t,
        web_words
    ):

        result[
            "internet_context_needed"
        ] = True

        result[
            "prefer_web_context"
        ] = True

        result[
            "realtime_context"
        ] = True

        result[
            "capability_should_wait"
        ] = True

        result[
            "response_mode"
        ] = "guidance"

    # =====================================================
    # 🔥 RENDERER-FIRST DETECTION
    # =====================================================

    renderer_graph_words = [

        "график",
        "графика",
        "функция",
        "plot",
        "chart",
        "y=",
        "sin(",
        "cos(",
        "tan("
    ]

    renderer_formula_words = [

        "формула",
        "уравнение",
        "реши",
        "математика",
        "formula"
    ]

    renderer_table_words = [

        "таблица",
        "сетка",
        "grid",
        "layout"
    ]

    renderer_diagram_words = [

        "схема",
        "diagram",
        "line",
        "линия",
        "стрелка"
    ]

    # =====================================================
    # 🔥 EXPLICIT IMAGE GENERATION
    # =====================================================

    if is_explicit_image_generation(
        t
    ):

        result[
            "explicit_image_generation_only"
        ] = True

        result[
            "visual_generation_needed"
        ] = True

        result["room"] = "image_generate"

        result[
            "expected_output_type"
        ] = "image"

        result[
            "expected_result"
        ] = "image"

        result[
            "best_capability"
        ] = "image_generate"

        result[
            "renderer_priority"
        ] = 0.0

        result[
            "prefer_renderer"
        ] = False

    # =====================================================
    # 🔥 GRAPH RENDER
    # =====================================================

    elif contains_any(
        t,
        renderer_graph_words
    ) or contains_math_expression(
        t
    ):

        result["render_intent"] = True

        result["render_type"] = "graph"

        result[
            "renderer_expected_output"
        ] = "graph"

        result[
            "renderer_scene_object"
        ] = True

        result["prefer_renderer"] = True

        result[
            "prefer_local_rendering"
        ] = True

        result[
            "renderer_priority"
        ] = 0.95

        result[
            "visual_generation_needed"
        ] = False

        result["room"] = "science"

        result[
            "expected_output_type"
        ] = "graph"

        result[
            "expected_result"
        ] = "graph"

        result[
            "best_capability"
        ] = "science"

        result[
            "capability_confidence"
        ] = max(
            result[
                "capability_confidence"
            ],
            0.92
        )

    # =====================================================
    # 🔥 FORMULA RENDER
    # =====================================================

    elif contains_any(
        t,
        renderer_formula_words
    ):

        result["render_intent"] = True

        result["render_type"] = "formula"

        result[
            "renderer_expected_output"
        ] = "formula"

        result[
            "renderer_scene_object"
        ] = True

        result["prefer_renderer"] = True

        result[
            "prefer_local_rendering"
        ] = True

        result[
            "renderer_priority"
        ] = 0.88

        result[
            "visual_generation_needed"
        ] = False

        result["room"] = "science"

        result[
            "expected_output_type"
        ] = "formula"

        result[
            "expected_result"
        ] = "formula"

        result[
            "best_capability"
        ] = "science"

    # =====================================================
    # 🔥 TABLE RENDER
    # =====================================================

    elif contains_any(
        t,
        renderer_table_words
    ):

        result["render_intent"] = True

        result["render_type"] = "table"

        result[
            "renderer_expected_output"
        ] = "table"

        result[
            "renderer_scene_object"
        ] = True

        result["prefer_renderer"] = True

        result[
            "prefer_local_rendering"
        ] = True

        result[
            "renderer_priority"
        ] = 0.82

        result[
            "visual_generation_needed"
        ] = False

        result[
            "expected_output_type"
        ] = "table"

        result[
            "expected_result"
        ] = "table"

    # =====================================================
    # 🔥 DIAGRAM RENDER
    # =====================================================

    elif contains_any(
        t,
        renderer_diagram_words
    ):

        result["render_intent"] = True

        result["render_type"] = "diagram"

        result[
            "renderer_expected_output"
        ] = "diagram"

        result[
            "renderer_scene_object"
        ] = True

        result["prefer_renderer"] = True

        result[
            "prefer_local_rendering"
        ] = True

        result[
            "renderer_priority"
        ] = 0.84

        result[
            "visual_generation_needed"
        ] = False

        result[
            "expected_output_type"
        ] = "diagram"

        result[
            "expected_result"
        ] = "diagram"

    # =====================================================
    # 🔥 DEMO / GUIDED VISUALS
    # =====================================================

    demo_words = [
        "покажи пример",
        "можешь показать",
        "как это выглядит",
        "можно пример"
    ]

    if contains_any(
        t,
        demo_words
    ):

        result[
            "visual_demo_request"
        ] = True

        result[
            "visual_expectation"
        ] += 0.2

        result[
            "example_expectation"
        ] += 0.3

        result[
            "assistant_initiative"
        ] += 0.2

        result[
            "visual_lightweight_mode"
        ] = True

        result[
            "capability_is_guidance"
        ] = True

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

    if contains_any(
        t,
        lightweight_words
    ):

        result[
            "visual_lightweight_mode"
        ] = True

        result[
            "library_visual_candidate"
        ] = True

        result[
            "capability_should_wait"
        ] = True

    # =====================================================
    # 🔥 GENERATION CONTROL
    # =====================================================

    generation_words = [
        "создай",
        "сгенерируй",
        "нарисуй",
        "сделай изображение"
    ]

    if (

        contains_any(
            t,
            generation_words
        )

        and not result.get(
            "prefer_renderer"
        )

    ):

        result[
            "visual_generation_needed"
        ] = True

        result[
            "execution_readiness"
        ] += 0.35

    else:

        if result[
            "visual_demo_request"
        ]:

            result[
                "visual_generation_needed"
            ] = False

            result[
                "visual_lightweight_mode"
            ] = True

    # =====================================================
    # 🔥 EXPECTATION SIGNALS
    # =====================================================

    example_words = [
        "пример",
        "вариант",
        "образец",
        "идея"
    ]

    if contains_any(
        t,
        example_words
    ):

        result[
            "should_offer_examples"
        ] = True

        result[
            "example_expectation"
        ] += 0.5

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

    if contains_any(
        t,
        execution_words
    ):

        pressure += 0.4

        result[
            "execution_readiness"
        ] += 0.4

    if (
        result["continuation"]
        and len(t) <= 40
    ):

        pressure += 0.15

        result[
            "trajectory_strength"
        ] += 0.2

    if flow_type:

        pressure += 0.08

    # =====================================================
    # 🔥 RENDERER PRIORITY BOOST
    # =====================================================

    if result.get(
        "prefer_renderer"
    ):

        pressure += 0.35

        result[
            "execution_readiness"
        ] += 0.35

    result["execution_pressure"] = clamp(
        pressure
    )

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
        and result["explicit_image_generation_only"]
        and not result["capability_should_wait"]

    ):

        result["should_offer_visual"] = True

        result["room"] = "image_generate"

    # =====================================================
    # 🔥 RENDERER PROTECTION
    # =====================================================

    if result.get("render_intent"):

        result[
            "visual_generation_needed"
        ] = False

        result[
            "should_offer_visual"
        ] = False

        result["prefer_renderer"] = True

        result[
            "capability_should_wait"
        ] = False

        result["should_execute"] = True

        result["response_mode"] = "execute"

        result[
            "execution_readiness"
        ] = max(
            result[
                "execution_readiness"
            ],
            0.9
        )

        result[
            "ambiguity_level"
        ] *= 0.5

    # =====================================================
    # 🔥 PROVIDER SAFETY
    # =====================================================

    if result.get(
        "prefer_renderer"
    ):

        result[
            "avoid_image_generation_fallback"
        ] = True

        result[
            "visual_generation_needed"
        ] = False

        result[
            "explicit_image_generation_only"
        ] = False

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
    # 🔥 FINAL TRAJECTORY STABILIZATION
    # =====================================================

    if result["dialog_state"] == "exploration":

        result["preserve_flow"] = True

        result["conversation_alive"] = True

        result["unresolved_intent"] = True

        result[
            "response_requires_reflection"
        ] = True

    # =====================================================
    # 🔥 FINAL NORMALIZATION
    # =====================================================

    float_keys = [

        "confidence",
        "trajectory_strength",
        "visual_expectation",
        "example_expectation",
        "execution_readiness",
        "guidance_need",
        "ambiguity_level",
        "user_certainty",
        "assistant_initiative",
        "execution_pressure",
        "conversation_value",
        "capability_confidence",
        "renderer_priority",
        "attention_weight"
    ]

    for key in float_keys:

        result[key] = clamp(
            result.get(key, 0.0)
        )

    return result
