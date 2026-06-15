# blocks/semantic_core.py

from blocks.interpretation_layer import (
    interpret_request
)

# =====================================================
# 🧠 APRIL SEMANTIC CORE
# =====================================================

"""
APRIL SEMANTIC CORE

ROLE:
- lightweight semantic analysis
- memory-aware semantic analysis
- renderer-first semantic hints
- continuity-safe interpretation
- machine-safe orchestration support
- execution pressure estimation

SEMANTIC CORE НЕ:
- authority system
- hard router
- renderer executor
- generation trigger
- orchestration owner
"""

# =====================================================
# 🔥 MACHINE IDENTITY
# =====================================================

APRIL_FILE_ID = "APRIL_SEMANTIC_CORE"

SEMANTIC_MACHINE_CHANNEL = {

    "type": "semantic_core",

    "mode": "machine_understanding",

    "isolated": True,

    "continuity_safe": True,

    "renderer_safe": True,

    "web_safe": True
}

# =====================================================
# 🔥 PATCH LOG
# =====================================================

SEMANTIC_PATCH_LOG = []

def safe_semantic_log(msg):

    try:

        print(
            "SEMANTIC CORE:",
            msg
        )

        SEMANTIC_PATCH_LOG.append(
            str(msg)
        )

    except:
        pass

safe_semantic_log(
    "SEMANTIC CORE INITIALIZED"
)

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


def safe_probability(
    value,
    boost=0.0
):

    return clamp(
        value + boost
    )

# =====================================================
# 🔥 MACHINE SIGNALS
# =====================================================

def detect_renderer_probability(
    text
):

    t = (text or "").lower()

    probability = 0.0

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
        "стрелка",
        "plot",
        "chart",
        "y=",
        "f(x)",
        "sin(",
        "cos(",
        "tan("
    ]

    for word in renderer_words:

        if word in t:
            probability += 0.12

    return clamp(probability)


def detect_image_generation_probability(
    text
):

    t = (text or "").lower()

    probability = 0.0

    generation_words = [

        "создай изображение",
        "сгенерируй изображение",
        "нарисуй картинку",
        "создай арт",
        "draw image",
        "generate image"
    ]

    for word in generation_words:

        if word in t:
            probability += 0.25

    return clamp(probability)


def detect_visual_probability(
    text
):

    t = (text or "").lower()

    probability = 0.0

    visual_words = [

        "пример",
        "визуально",
        "референс",
        "атмосфера",
        "концепт",
        "дизайн",
        "стиль",
        "схема",
        "чертеж",
        "layout"
    ]

    for word in visual_words:

        if word in t:
            probability += 0.1

    return clamp(probability)


def detect_execution_probability(
    text
):

    t = (text or "").lower()

    probability = 0.0

    execution_words = [

        "сделай",
        "создай",
        "выполни",
        "отправь",
        "построй",
        "покажи"
    ]

    for word in execution_words:

        if word in t:
            probability += 0.12

    return clamp(probability)



# =====================================================
# 🔥 DIALOGUE AWARENESS
# =====================================================

def detect_discussion_probability(text):

    t = (text or "").lower()

    words = [
        "давай обсудим",
        "как думаешь",
        "что думаешь",
        "поговорим",
        "обсудим",
        "подскажи",
        "посоветуй",
        "объясни",
        "расскажи",
        "помоги понять",
        "можешь показать",
        "интересно",
        "хочу понять",
        "какой лучше",
        "какой график",
        "какая функция"
    ]

    probability = 0.0

    for word in words:
        if word in t:
            probability += 0.18

    return clamp(probability)


def detect_reflection_probability(text):

    t = (text or "").lower()

    words = [
        "почему",
        "объясни",
        "рассуждай",
        "размышляй",
        "как ты пришла"
    ]

    probability = 0.0

    for word in words:
        if word in t:
            probability += 0.15

    return clamp(probability)


def detect_space_discussion_probability(text):

    t = (text or "").lower()

    words = [
        "пространство",
        "scene",
        "renderer",
        "блок",
        "галерея",
        "график"
    ]

    probability = 0.0

    for word in words:
        if word in t:
            probability += 0.12

    return clamp(probability)


# =====================================================
# 🧠 REPRESENTATION ANALYSIS
# =====================================================

def detect_representation_request(text):

    t = (text or "").lower()

    graph_words = [
        "покажи",
        "визуально",
        "график",
        "построй"
    ]

    table_words = [
        "таблица",
        "значения",
        "сравни"
    ]

    link_words = [
        "источник",
        "ссылка",
        "документация"
    ]

    if any(w in t for w in graph_words):
        return "graph"

    if any(w in t for w in table_words):
        return "table"

    if any(w in t for w in link_words):
        return "link"

    return None

# =====================================================
# 🧠 GRAPH ACTION DETECTION
# =====================================================

def detect_graph_action(text):

    t = (text or "").lower()

    if "почему" in t:
        return "explain"

    if "исправ" in t:
        return "fix"

    if "анализ" in t:
        return "analyze"

    if "сравни" in t:
        return "compare"

    if (
        "построй" in t
        or "нарисуй" in t
    ):
        return "build"

    return "unknown"

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
    # 🔥 GOLDEN MEMORY INPUT
    # =====================================================

    cognition_state = state.get("cognition", {})

    dynamic_focus = cognition_state.get("dynamic_focus", {})

    goal_hierarchy = cognition_state.get("goal_hierarchy", {})

    open_loops = cognition_state.get("open_loops", {})

    memory_signals = cognition_state.get("memory_signals", {})

    # =====================================================
    # 🧠 TOPIC MEMORY INPUT
    # =====================================================

    visual_topic_registry = state.get(
        "visual_topic_registry",
        []
    )

    task_context_storage = state.get(
        "task_context_storage",
        []
    )

    continuity_context_storage = state.get(
        "continuity_context_storage",
        []
    )

    memory_anchor_storage = state.get(
        "memory_anchor_storage",
        []
    )

    active_topic_slot = state.get(
        "active_topic_slot",
        "A"
    )

    if not isinstance(open_loops, dict):

        open_loops = {
            "has_open_loops": bool(open_loops)
        }

    safe_semantic_log(
        f"INPUT: {t[:80]}"
    )

    # =====================================================
    # 🔥 MACHINE PROBABILITIES
    # =====================================================

    renderer_probability = (
        detect_renderer_probability(text)
    )

    image_generation_probability = (
        detect_image_generation_probability(text)
    )

    visual_probability = (
        detect_visual_probability(text)
    )

    execution_probability = (
        detect_execution_probability(text)
    )

    discussion_probability = (
        detect_discussion_probability(text)
    )

    reflection_probability = (
        detect_reflection_probability(text)
    )

    space_discussion_probability = (
        detect_space_discussion_probability(text)
    )

    # =====================================================
    # 🔥 BASE RESULT
    # =====================================================

    result = {

        # =================================================
        # 🧠 MACHINE
        # =====================================================

        "machine_channel":
            SEMANTIC_MACHINE_CHANNEL,

        "semantic_core_active":
            True,

        "web_safe":
            True,

        "renderer_safe":
            True,

        "provider_safe":
            True,

        # =================================================
        # 🧠 CORE
        # =====================================================

        "intent": "text",

        "confidence": 0.5,

        "normalized_text": text,

        # =================================================
        # 🧠 MACHINE LANGUAGE
        # =====================================================

        "semantic_role": "understanding_only",

        "semantic_authority": False,

        "semantic_machine_layer": True,

        "semantic_probability_based": True,

        "semantic_executor_expected": True,

        # =================================================
        # 🧠 MACHINE SIGNALS
        # =====================================================

        "renderer_probability":
            renderer_probability,

        "image_generation_probability":
            image_generation_probability,

        "visual_probability":
            visual_probability,

        "execution_probability":
            execution_probability,
        
        "discussion_probability":
            discussion_probability,

        "reflection_probability":
            reflection_probability,

        "space_discussion_probability":
            space_discussion_probability,

        # =================================================
        # 🧠 SOFT HINTS
        # =====================================================

        "possible_room": "text",

        "possible_output": "text",

        "possible_scene_type": None,

        "possible_capability": "text",

        # =================================================
        # 🧠 CONTINUITY
        # =====================================================

        "continuation": False,

        "continuation_target": None,

        "trajectory_active": True,

        "trajectory_strength": 0.5,

        "preserve_flow": True,

        "conversation_alive": True,

        # =================================================
        # 🧠 REPRESENTATION CONTEXT
        # =====================================================

        "current_topic": None,

        "current_object": None,

        "current_representation": "text",

        "requested_representation": None,

        # =================================================
        # 🧠 SCENE COMPOSITION
        # =====================================================

        "content_role": None,

        "contains_object": False,

        "contains_explanation": False,

        "contains_analysis": False,

        "contains_legend": False,

        "scene_composition_ready": False,

        "same_task": False,

        "representation_shift": False,

        "context_visual_followup": False,

        "unresolved_intent": True,

        # =================================================
        # 🧠 VISUAL
        # =====================================================

        "visual_continuity": False,

        "visual_routing": False,

        "active_visual_scene_detected": False,

        "scene_reference_detected": False,

        # =================================================
        # 🧠 RENDERER-FIRST
        # =====================================================

        "render_intent": False,

        "prefer_renderer": False,

        "renderer_scene_object": False,

        "renderer_lightweight": True,

        "renderer_priority": 0.0,

        "prefer_local_rendering": False,

        # =================================================
        # 🧠 IMAGE SAFETY
        # =====================================================

        "visual_generation_needed": False,

        "explicit_image_generation_only": False,

        "avoid_image_generation_fallback": True,

        # =================================================
        # 🧠 EXECUTION
        # =====================================================

        "should_execute": False,

        "execution_pressure": 0.0,

        "execution_readiness": 0.0,

        # =================================================
        # 🧠 RESPONSE
        # =====================================================

        "response_mode": "talk",

        "response_economy": "balanced",

        # =================================================
        # 🧠 PROVIDER SAFETY
        # =====================================================

        "provider_safe_mode": True,

        "provider_aware": True,

        "renderer_first": True,

        "anti_trigger_behavior": True,

        "anti_room_wars": True,

        "anti_hidden_escalation": True,

        # =================================================
        # 🧠 MEMORY AWARENESS
        # =====================================================

        "dynamic_focus":
            dynamic_focus,

        "goal_hierarchy":
            goal_hierarchy,

        "open_loops":
            open_loops,

        "memory_signals":
            memory_signals,

        "visual_topic_registry":
            visual_topic_registry,

        "task_context_storage":
            task_context_storage,

        "continuity_context_storage":
            continuity_context_storage,

        "memory_anchor_storage":
            memory_anchor_storage,

        "active_topic_slot":
            active_topic_slot
    }

    # =====================================================
    # 🔥 INTERPRETATION
    # =====================================================

    interpreted = interpret_request(

        text,

        cognition=state.get(
            "cognition",
            {}
        ),

        semantic=result
    )

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

        result[
            "possible_scene_type"
        ] = interpreted.get(
            "scene_type"
        )

        # ================================================
        # 🔥 CONTINUATION
        # ================================================

        if interpreted.get(
            "continuation"
        ):

            result[
                "continuation"
            ] = True

        # ================================================
        # 🔥 RENDERER
        # ================================================

        if interpreted.get(
            "prefer_renderer"
        ):

            result[
                "prefer_renderer"
            ] = True

            result[
                "render_intent"
            ] = True

            result[
                "renderer_scene_object"
            ] = True

        # ================================================
        # 🔥 IMAGE
        # ================================================

        if interpreted.get(
            "explicit_image_generation"
        ):

            result[
                "visual_generation_needed"
            ] = True

            result[
                "explicit_image_generation_only"
            ] = True

        # ================================================
        # 🔥 SCENE COMPOSITION HINTS
        # ================================================

        result["content_role"] = interpreted.get(
            "content_role"
        )

        result["contains_object"] = interpreted.get(
            "contains_object",
            False
        )

        result["contains_explanation"] = interpreted.get(
            "contains_explanation",
            False
        )

        result["contains_analysis"] = interpreted.get(
            "contains_analysis",
            False
        )

        result["contains_legend"] = interpreted.get(
            "contains_legend",
            False
        )

        result["scene_composition_ready"] = interpreted.get(
            "scene_composition_ready",
            False
        )

    # =====================================================
    # 🔥 ACTIVE FLOW
    # =====================================================

    flow_type = active_flow.get(
        "type"
    )

    if flow_type:

        result["continuation"] = True

        result["continuation_target"] = (
            flow_type
        )

        result["trajectory_strength"] = (
            safe_probability(
                result[
                    "trajectory_strength"
                ],
                0.2
            )
        )

    
    # =====================================================
    # 🧠 REPRESENTATION CONTINUITY
    # =====================================================

    requested_representation = detect_representation_request(text)

    result["requested_representation"] = requested_representation

    result["graph_action"] = detect_graph_action(text)

    last_math = state.get("last_math", {})

    if last_math:

        result["same_task"] = True

        result["current_object"] = last_math.get("type")

        if requested_representation:

            result["representation_shift"] = True
            result["context_visual_followup"] = True
            result["render_intent"] = True
            result["prefer_renderer"] = True

# =====================================================
    # 🔥 VISUAL CONTINUITY
    # =====================================================

    active_visual_scene = state.get(
        "active_visual_scene"
    )

    if active_visual_scene:

        result[
            "active_visual_scene_detected"
        ] = True

        if len(t) <= 120:

            result[
                "visual_continuity"
            ] = True

            result[
                "scene_reference_detected"
            ] = True

            result[
                "visual_routing"
            ] = True

            result[
                "trajectory_strength"
            ] = safe_probability(
                result[
                    "trajectory_strength"
                ],
                0.25
            )

    # =====================================================
    # 🔥 RENDERER MACHINE LOGIC
    # =====================================================

    if (

        renderer_probability >= 0.45

        and not discussion_probability >= 0.25

        and not reflection_probability >= 0.25

    ):

        result["render_intent"] = True

        result["prefer_renderer"] = True

        result[
            "renderer_scene_object"
        ] = True

        result[
            "prefer_local_rendering"
        ] = True

        result[
            "renderer_priority"
        ] = renderer_probability

        result[
            "possible_capability"
        ] = "renderer"

        result[
            "possible_room"
        ] = "science"

        result[
            "possible_output"
        ] = "renderer"

        result[
            "visual_generation_needed"
        ] = False

    # =====================================================
    # 🔥 IMAGE GENERATION
    # =====================================================

    if image_generation_probability >= 0.45:

        result[
            "explicit_image_generation_only"
        ] = True

        result[
            "visual_generation_needed"
        ] = True

        result[
            "possible_room"
        ] = "image_generate"

        result[
            "possible_output"
        ] = "image"

        result[
            "possible_capability"
        ] = "image_generation"

    # =====================================================
    # 🔥 VISUAL GUIDANCE
    # =====================================================

    if visual_probability >= 0.3:

        result[
            "visual_routing"
        ] = True

        result[
            "renderer_lightweight"
        ] = True

    # =====================================================
    # 🔥 EXECUTION MODEL
    # =====================================================

    pressure = execution_probability

    if renderer_probability >= 0.45:
        pressure += 0.25

    if flow_type:
        pressure += 0.08

    result["execution_pressure"] = clamp(
        pressure
    )

    result["execution_readiness"] = clamp(
        pressure
    )

    # =====================================================
    # 🔥 SAFE EXECUTION
    # =====================================================

    if (

        result[
            "execution_pressure"
        ] >= 0.72

        and not result[
            "visual_generation_needed"
        ]

    ):

        result[
            "should_execute"
        ] = True

    # =====================================================
    # 🔥 RESPONSE ECONOMY
    # =====================================================

    if result[
        "execution_pressure"
    ] >= 0.75:

        result[
            "response_economy"
        ] = "minimal"

    elif result[
        "visual_probability"
    ] >= 0.55:

        result[
            "response_economy"
        ] = "expanded"


    # =====================================================
    # 🔥 MEMORY REINFORCEMENT
    # =====================================================

    if memory_signals.get("memory_priority", 0) >= 0.7:
        result["trajectory_strength"] = safe_probability(
            result["trajectory_strength"],
            0.15
        )

    if open_loops.get("has_open_loops"):
        result["continuation"] = True

    if goal_hierarchy.get("strategic_goal"):
        result["trajectory_active"] = True

    # =====================================================
    # 🧠 TOPIC CONTINUITY SUPPORT
    # =====================================================

    if continuity_context_storage:

        result[
            "continuation"
        ] = True

        result[
            "trajectory_strength"
        ] = safe_probability(
            result[
                "trajectory_strength"
            ],
            0.10
        )

    if memory_anchor_storage:

        result[
            "trajectory_active"
        ] = True

    if active_topic_slot:

        result[
            "active_topic_slot"
        ] = active_topic_slot

    # =====================================================
    # 🔥 FINAL MACHINE NORMALIZATION
    # =====================================================

    float_keys = [

        "confidence",
        "trajectory_strength",
        "renderer_probability",
        "image_generation_probability",
        "visual_probability",
        "execution_probability",
        "renderer_priority",
        "execution_pressure",
        "execution_readiness"
    ]

    for key in float_keys:

        result[key] = clamp(
            result.get(key, 0.0)
        )

    safe_semantic_log(
        f"INTENT: {result['intent']}"
    )

    safe_semantic_log(
        f"ROOM: {result['possible_room']}"
    )

    return result
