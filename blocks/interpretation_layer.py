# =====================================================
# 🧠 APRIL INTERPRETATION LAYER
# =====================================================

"""
APRIL_FILE_ID:
APRIL_INTERPRETATION_LAYER

ROLE:
SEMANTIC_INTERPRETATION_BRIDGE

INPUT:
USER_TEXT
COGNITION_STATE
SEMANTIC_STATE
ACTIVE_TRAJECTORY

OUTPUT:
INTERPRETATION_HINTS
SCENE_CLASSIFICATION
SEMANTIC_SUPPORT_PAYLOAD
RENDERER_COMPATIBLE_CONTEXT

=====================================================

APRIL SEMANTIC INTERPRETATION LAYER

Этот слой:
- НЕ command router;
- НЕ execution engine;
- НЕ fallback trigger.

Interpretation layer теперь:
- semantic hint system;
- lightweight intention detector;
- continuity-aware interpreter;
- cognition-assisted interpretation layer;
- renderer-aware semantic adapter.

=====================================================

ВАЖНО:

Этот слой НЕ:
- навязывает execution;
- НЕ генерирует prompts;
- НЕ вызывает generation;
- НЕ ломает orchestration;
- НЕ force routing;
- НЕ принимает решения вместо cognition.

=====================================================

Он только:
- помогает semantic_core;
- помогает cognition;
- стабилизирует semantic continuity;
- подготавливает безопасные semantic hints;
- помогает executor понять тип сцены.
"""

import time

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

INPUT_MACHINE_CHANNEL = {

    "source":
        "semantic_core",

    "type":
        "interpretation_input",

    "isolated":
        True
}

OUTPUT_MACHINE_CHANNEL = {

    "target":
        "executor_orchestration",

    "type":
        "interpretation_output",

    "isolated":
        True
}

# =====================================================
# 🔥 PATCH LOGGING
# =====================================================

PATCH_LOG = []

MAX_PATCH_LOGS = 120


def safe_patch_log(message):

    try:

        print(
            "INTERPRETATION PATCH:",
            message
        )

        PATCH_LOG.append({

            "timestamp":
                time.time(),

            "message":
                message,

            "file_id":
                "APRIL_INTERPRETATION_LAYER",

            "machine_only":
                True
        })

        if len(PATCH_LOG) > MAX_PATCH_LOGS:

            PATCH_LOG.pop(0)

    except Exception:
        pass

# =====================================================
# 🔥 HELPERS
# =====================================================

def contains_any(
    text,
    words
):

    return any(
        w in text
        for w in words
    )

# =====================================================
# 🔥 SAFE NORMALIZATION
# =====================================================

def normalize_text(
    text: str
):

    return (
        text or ""
    ).strip()

# =====================================================
# 🔥 SAFE LOWER
# =====================================================

def normalize_lower(
    text: str
):

    return normalize_text(
        text
    ).lower()

# =====================================================
# 🔥 SEMANTIC GROUPS
# =====================================================

MATH_WORDS = [

    "график",
    "функция",
    "формула",
    "уравнение",
    "парабола",
    "синус",
    "косинус",
    "тангенс",

    "y=",
    "f(x)",
    "^2",
    "^3",
    "sin(",
    "cos(",
    "tan("
]

RENDERER_WORDS = [

    "график",
    "формула",
    "таблица",
    "сетка",
    "grid",
    "layout",
    "diagram",
    "схема",
    "line",
    "линия",
    "стрелка",
    "renderer",
    "render",
    "canvas",
    "scene",
    "пространство",
    "блок"
]

LIGHTWEIGHT_VISUAL_WORDS = [

    "пример",
    "идея",
    "вариант",
    "референс",
    "концепт",
    "атмосфера",
    "как выглядит",
    "примерно"
]

EXPLICIT_IMAGE_WORDS = [

    "создай изображение",
    "сгенерируй изображение",
    "нарисуй картинку",
    "создай арт",
    "draw image",
    "generate image",
    "сделай арт"
]

EXPLORATION_WORDS = [

    "идея",
    "вариант",
    "примерно",
    "атмосфера",
    "может",
    "посмотрим",
    "подумаем",
    "как думаешь"
]

CONTINUATION_WORDS = [

    "дальше",
    "продолжим",
    "теперь",
    "еще",
    "вернемся",
    "это",
    "этот",
    "эта",
    "снова"
]

WEB_WORDS = [

    "погода",
    "новости",
    "курс",
    "сейчас",
    "где находится",
    "маршрут",
    "рейс",
    "карта",
    "такси",
    "отель",
    "локация",
    "навигация"
]

CODE_WORDS = [

    "код",
    "кнопка",
    "анимация",
    "html",
    "css",
    "javascript",
    "python",
    "react",
    "api",
    "функция"
]

INFORMATIONAL_WORDS = [

    "информация",
    "данные",
    "расскажи",
    "объясни",
    "почему",
    "как работает",
    "что происходит",
    "можешь помочь",
    "что можешь сказать"
]



# =====================================================
# 🔥 DOMAIN COMPETENCE LAYER
# =====================================================

DOMAIN_REGISTRY = {

    "biology": {
        "description": "living systems, genetics, evolution, physiology, ecology, microbiology"
    },

    "chemistry": {
        "description": "reactions, compounds, molecules, materials"
    },

    "physics": {
        "description": "motion, energy, forces, fields, matter"
    },

    "engineering": {
        "description": "systems, design, construction, optimization"
    },

    "it": {
        "description": "software, hardware, networks, computing"
    },

    "literature": {
        "description": "books, texts, authors, narrative analysis"
    },

    "politics": {
        "description": "government, policy, diplomacy, political systems"
    },

    "news": {
        "description": "recent developments and current events"
    },

    "social": {
        "description": "society, behavior, communities, culture"
    },

    "web": {
        "description": "internet resources, search, websites"
    }
}


def detect_domain_candidates(text):

    lower = normalize_lower(text)

    candidates = []

    domain_words = {

        "biology": [
            "биология","генетика","эволюция","клетка","организм",
            "экология","бактерии","днк","животные","растения"
        ],

        "chemistry": [
            "химия","реакция","молекула","атом","вещество"
        ],

        "physics": [
            "физика","энергия","сила","ускорение","электричество"
        ],

        "engineering": [
            "инженерия","конструкция","механизм","система","проектирование"
        ],

        "it": [
            "программирование","алгоритм","сервер","код","разработка"
        ],

        "literature": [
            "литература","роман","поэзия","писатель","произведение"
        ],

        "politics": [
            "политика","государство","выборы","правительство"
        ],

        "news": [
            "новости","события","последние новости"
        ],

        "social": [
            "общество","социум","социальный"
        ],

        "web": [
            "сайт","интернет","поиск","веб"
        ]
    }

    for domain, words in domain_words.items():
        if any(w in lower for w in words):
            candidates.append(domain)

    return candidates


def detect_representation_candidates(text):

    lower = normalize_lower(text)

    reps = []

    if any(x in lower for x in ["график","plot","chart"]):
        reps.append("graph")

    if any(x in lower for x in ["таблица","table"]):
        reps.append("table")

    if any(x in lower for x in ["схема","diagram"]):
        reps.append("diagram")

    if any(x in lower for x in ["формула","уравнение"]):
        reps.append("formula")

    # Do not force text as a representation.
    # Empty means Executor decides from full context.
    if not reps:
        return []

    return reps


# =====================================================
# 🔥 DIALOGUE UNDERSTANDING
# =====================================================

DISCUSSION_WORDS = [
    "поговорим","обсудим","как думаешь","мнение",
    "рассуждение","рассуждаем","объясни","почему"
]

ACTION_WORDS = [
    "создай","сделай","построй","отрендери",
    "нарисуй","покажи","сгенерируй"
]

def detect_discussion_mode(text):
    return contains_any(
        normalize_lower(text),
        DISCUSSION_WORDS
    )

def detect_space_discussion(text):
    lower = normalize_lower(text)
    return (
        contains_any(lower, ["пространство","scene","renderer","render","блок"])
        and detect_discussion_mode(lower)
    )


# =====================================================
# 🔥 SAFE DETECTORS
# =====================================================

def detect_math_expression(
    text
):

    return contains_any(
        normalize_lower(text),
        MATH_WORDS
    )


def detect_renderer_intent(
    text
):

    lower = normalize_lower(text)

    has_renderer_topic = contains_any(
        lower,
        RENDERER_WORDS
    )

    has_action = contains_any(
        lower,
        ACTION_WORDS
    )

    if detect_space_discussion(lower):
        return False

    return has_renderer_topic and has_action


def detect_lightweight_visual(
    text
):

    return contains_any(
        normalize_lower(text),
        LIGHTWEIGHT_VISUAL_WORDS
    )


def detect_explicit_image_generation(
    text
):

    return contains_any(
        normalize_lower(text),
        EXPLICIT_IMAGE_WORDS
    )


def detect_exploration(
    text
):

    return contains_any(
        normalize_lower(text),
        EXPLORATION_WORDS
    )


def detect_continuation(
    text
):

    return contains_any(
        normalize_lower(text),
        CONTINUATION_WORDS
    )


def detect_web_context(
    text
):

    return contains_any(
        normalize_lower(text),
        WEB_WORDS
    )


def detect_code_request(
    text
):

    return contains_any(
        normalize_lower(text),
        CODE_WORDS
    )


def detect_informational_request(
    text
):

    return contains_any(
        normalize_lower(text),
        INFORMATIONAL_WORDS
    )

# =====================================================
# 🔥 SCENE UNDERSTANDING
# =====================================================

def detect_scene_type(
    text,
    cognition=None
):

    cognition = cognition or {}

    lower = normalize_lower(
        text
    )

    # =================================================
    # 🔥 COGNITION PRIORITY
    # =====================================================

    if cognition.get(
        "prefer_renderer"
    ):

        if (
            "график" in lower
            or "plot" in lower
            or "graph" in lower
        ):

            return "graph"

        if (
            "формула" in lower
            or "equation" in lower
        ):

            return "formula"

        if (
            "таблица" in lower
            or "table" in lower
        ):

            return "table"

        return "scene"

    # =================================================
    # 🔥 SAFE SEMANTIC FALLBACK
    # =====================================================

    if detect_renderer_intent(
        lower
    ):

        if (
            "график" in lower
            or "plot" in lower
            or "graph" in lower
        ):

            return "graph"

        if (
            "формула" in lower
            or "equation" in lower
        ):

            return "formula"

        if (
            "таблица" in lower
            or "table" in lower
        ):

            return "table"

        return "scene"

    return None

# =====================================================
# 🔥 RESULT PACKAGE
# =====================================================

def build_result(
    text
):

    return {

        # =================================================
        # 🔥 CORE
        # =====================================================

        "type":
            "text",

        "subtype":
            None,

        "scene_type":
            None,

        "normalized":
            text,

        # =================================================
        # 🔥 SCENE COMPOSITION HINTS
        # =====================================================

        "content_role":
            None,

        "contains_object":
            False,

        "contains_explanation":
            False,

        "contains_analysis":
            False,

        "contains_legend":
            False,

        "scene_composition_ready":
            True,

        # =================================================
        # 🔥 SEMANTIC HINTS
        # =====================================================

        "renderer_intent":
            False,

        "discussion_mode":
            False,

        "space_discussion":
            False,

        "lightweight_visual":
            False,

        "exploration":
            False,

        "continuation":
            False,

        "web_context":
            False,

        "explicit_image_generation":
            False,

        # =================================================
        # 🔥 COGNITION COOPERATION
        # =====================================================

        "cognition_assisted":
            True,

        "continuity_aware":
            True,

        "scene_aware":
            True,

        "supports_executor":
            True,

        # =================================================
        # 🔥 ORCHESTRATION
        # =====================================================

        "prefer_renderer":
            False,

        "prefer_guidance":
            False,

        "prefer_execution":
            False,

        "prefer_continuation":
            False,

        "active_topic_slot":
            None,

        "topic_continuity":
            False,

        # =================================================
        # 🔥 SAFETY
        # =====================================================

        "avoid_force_generation":
            True,

        "avoid_hidden_escalation":
            True,

        "avoid_telegram_behavior":
            True,

        "avoid_trigger_execution":
            True,

        "provider_safe":
            True,

        "renderer_first":
            True,

        # =================================================
        # 🔥 MACHINE FLAGS
        # =====================================================

        "machine_only":
            True,

        "semantic_bridge":
            True,

        "orchestration_safe":
            True,

        "continuity_preserved":
            True,

        "required_domains": [],
        "candidate_domains": [],
        "required_representations": [],
        "candidate_representations": [],
        "domain_confidence": {}
    }


# =====================================================
# 🔥 CONTENT ROLE ANALYSIS
# =====================================================

def detect_explanation_content(text):

    lower = normalize_lower(text)

    markers = [
        "объясни",
        "объяснение",
        "пояснение",
        "расшифровка",
        "что означает",
        "что значит"
    ]

    return contains_any(lower, markers)


def detect_analysis_content(text):

    lower = normalize_lower(text)

    markers = [
        "анализ",
        "вывод",
        "заключение",
        "интерпретация"
    ]

    return contains_any(lower, markers)


def detect_legend_content(text):

    lower = normalize_lower(text)

    markers = [
        "обозначение",
        "обозначения",
        "легенда",
        "расшифровка"
    ]

    return contains_any(lower, markers)


def detect_object_content(text):

    return (
        detect_math_expression(text)
        or detect_renderer_intent(text)
    )




# =====================================================
# 🔥 APRIL DOMAIN INFERENCE BOOST
# =====================================================

def build_domain_confidence(text):

    candidates = detect_domain_candidates(text)

    confidence = {}

    for domain in candidates:
        confidence[domain] = 0.85

    return confidence



# =====================================================
# 🔥 FACTORY ORDER PROTOCOL
# =====================================================

DOMAIN_ROOM_MAP = {
    "biology": ["biology"],
    "chemistry": ["chemistry"],
    "physics": ["physics"],
    "engineering": ["engineering"],
    "it": ["it"],
    "literature": ["literature"],
    "politics": ["politics"],
    "news": ["news"],
    "social": ["social"],
    "web": ["web"]
}

def build_factory_order(result):

    required_domains = result.get(
        "required_domains",
        []
    )

    required_rooms = []

    for domain in required_domains:

        required_rooms.extend(
            DOMAIN_ROOM_MAP.get(
                domain,
                []
            )
        )

    return {

        "intent":
            result.get("type"),

        "goal":
            result.get("subtype"),

        "required_domains":
            required_domains,

        "required_rooms":
            list(set(required_rooms)),

        "required_artifacts":
            required_domains,

        "quality_target":
            0.95
    }




# =====================================================
# 🔥 SCENE STRATEGY LAYER
# =====================================================

def build_scene_strategy(result):

    role = result.get(
        "content_role"
    )

    reps = result.get(
        "required_representations",
        []
    )

    strategy = {

        "scene_strategy":
            "default",

        "preferred_blocks":
            ["text"],

        "scene_priority":
            "normal",

        "scene_contribution_mode":
            True,

        "scene_builder_profile":
            "generic"
    }

    if role == "explanation":

        strategy.update({

            "scene_strategy":
                "knowledge_explanation",

            "preferred_blocks": [
                "knowledge_card",
                "relations",
                "resources"
            ],

            "scene_priority":
                "high",

            "scene_builder_profile":
                "knowledge"
        })

    elif role == "analysis":

        strategy.update({

            "scene_strategy":
                "analysis",

            "preferred_blocks": [
                "summary",
                "table",
                "resources"
            ],

            "scene_builder_profile":
                "analysis"
        })

    elif "graph" in reps:

        strategy.update({

            "scene_strategy":
                "knowledge_graph",

            "preferred_blocks": [
                "graph",
                "relations",
                "summary"
            ],

            "scene_builder_profile":
                "graph"
        })

    elif "table" in reps:

        strategy.update({

            "scene_strategy":
                "comparison",

            "preferred_blocks": [
                "table",
                "summary"
            ],

            "scene_builder_profile":
                "comparison"
        })

    return strategy


# =====================================================
# 🔥 MAIN INTERPRETER
# =====================================================

def interpret_request(
    text: str,
    cognition: dict = None,
    semantic: dict = None
):

    text = normalize_text(
        text
    )

    cognition = cognition or {}

    semantic = semantic or {}

    # =====================================================
    # 🧠 TOPIC MEMORY INPUT
    # =====================================================

    active_topic_slot = cognition.get(
        "active_topic_slot"
    )

    continuity_context_storage = cognition.get(
        "continuity_context_storage",
        []
    )

    memory_anchor_storage = cognition.get(
        "memory_anchor_storage",
        []
    )

    if not text:

        safe_patch_log(
            "EMPTY REQUEST"
        )

        return None

    t = normalize_lower(
        text
    )

    result = build_result(
        text
    )

    domain_candidates = detect_domain_candidates(t)
    representation_candidates = detect_representation_candidates(t)

    result["candidate_domains"] = domain_candidates
    result["required_domains"] = list(domain_candidates)
    result["domain_confidence"] = build_domain_confidence(t)

    result["candidate_representations"] = representation_candidates
    result["required_representations"] = list(representation_candidates)

    # Stage: Executor owns routing; interpretation provides only understanding.
    result["factory_order"] = {}
    safe_patch_log("FACTORY ORDER DEFERRED TO EXECUTOR")


    if detect_discussion_mode(t):
        result["discussion_mode"] = True
        result["prefer_guidance"] = True

    if detect_space_discussion(t):
        result["space_discussion"] = True


    # =====================================================
    # 🔥 CONTINUATION
    # =====================================================

    if (
        detect_continuation(t)
        or cognition.get(
            "needs_continuation"
        )
    ):

        result[
            "continuation"
        ] = True

        result[
            "prefer_continuation"
        ] = True

        safe_patch_log(
            "CONTINUATION DETECTED"
        )

    # =====================================================
    # 🔥 EXPLORATION
    # =====================================================

    if (
        detect_exploration(t)
        or cognition.get(
            "exploration_mode"
        )
    ):

        result[
            "exploration"
        ] = True

        result[
            "lightweight_visual"
        ] = True

        safe_patch_log(
            "EXPLORATION MODE"
        )

    # =====================================================
    # 🔥 WEB
    # =====================================================

    if (
        detect_web_context(t)
        or cognition.get(
            "internet_context_needed"
        )
    ):

        result[
            "web_context"
        ] = True

        result[
            "prefer_guidance"
        ] = True

        result[
            "subtype"
        ] = "web"

        safe_patch_log(
            "WEB CONTEXT DETECTED"
        )

    # =====================================================
    # 🔥 IMAGE GENERATION
    # =====================================================

    if detect_explicit_image_generation(
        t
    ):

        result[
            "type"
        ] = "image"

        result[
            "subtype"
        ] = "generation"

        result[
            "explicit_image_generation"
        ] = True

        safe_patch_log(
            "EXPLICIT IMAGE GENERATION"
        )

    # =====================================================
    # 🔥 COGNITION-FIRST RENDERER
    # =====================================================

    elif (

        cognition.get(
            "prefer_renderer"
        )

        or cognition.get(
            "renderer_space_active"
        )

        or detect_renderer_intent(
            t
        )
    ):

        result[
            "renderer_intent"
        ] = True

        result[
            "prefer_renderer"
        ] = True

        result[
            "type"
        ] = "render"

        scene_type = detect_scene_type(
            t,
            cognition
        )

        result[
            "scene_type"
        ] = scene_type

        result[
            "subtype"
        ] = scene_type

        safe_patch_log(
            f"RENDERER MODE: {scene_type}"
        )

    # =====================================================
    # 🔥 MATH
    # =====================================================

    elif (

        detect_math_expression(
            t
        )

        or cognition.get(
            "math_reasoning"
        )
    ):

        result[
            "type"
        ] = "math"

        result[
            "subtype"
        ] = "graph"

        result[
            "renderer_intent"
        ] = True

        result[
            "prefer_renderer"
        ] = True

        safe_patch_log(
            "MATH INTERPRETATION"
        )

    # =====================================================
    # 🔥 CODE
    # =====================================================

    elif detect_code_request(
        t
    ):

        result[
            "type"
        ] = "code"

        result[
            "subtype"
        ] = "implementation"

        result[
            "prefer_execution"
        ] = True

        safe_patch_log(
            "CODE REQUEST"
        )

    # =====================================================
    # 🔥 INFORMATIONAL
    # =====================================================

    elif (

        detect_informational_request(
            t
        )

        or cognition.get(
            "needs_guidance"
        )
    ):

        result[
            "type"
        ] = "text"

        result[
            "subtype"
        ] = "guidance"

        result[
            "prefer_guidance"
        ] = True

        safe_patch_log(
            "GUIDANCE REQUEST"
        )

    # =====================================================
    # 🔥 LIGHTWEIGHT VISUALS
    # =====================================================

    if (
        detect_lightweight_visual(
            t
        )

        or cognition.get(
            "visual_reference_mode"
        )
    ):

        result[
            "lightweight_visual"
        ] = True

        safe_patch_log(
            "LIGHTWEIGHT VISUAL MODE"
        )

    # =====================================================
    # 🔥 CONTINUITY STABILIZATION
    # =====================================================

    if cognition.get(
        "tracks_multiple_topics"
    ):

        result[
            "continuity_aware"
        ] = True

    if cognition.get(
        "avoid_topic_loss"
    ):

        result[
            "scene_aware"
        ] = True

    # =====================================================
    # 🧠 TOPIC CONTINUITY SUPPORT
    # =====================================================

    if continuity_context_storage:

        result[
            "continuation"
        ] = True

        result[
            "topic_continuity"
        ] = True

    if memory_anchor_storage:

        result[
            "continuity_aware"
        ] = True

    if active_topic_slot:

        result[
            "active_topic_slot"
        ] = active_topic_slot


    # =====================================================
    # 🔥 SCENE COMPOSITION HINTS
    # =====================================================

    if detect_object_content(t):

        result["contains_object"] = True

    if detect_explanation_content(t):

        result["contains_explanation"] = True
        result["content_role"] = "explanation"

    if detect_analysis_content(t):

        result["contains_analysis"] = True

        if not result.get("content_role"):
            result["content_role"] = "analysis"

    if detect_legend_content(t):

        result["contains_legend"] = True

        if not result.get("content_role"):
            result["content_role"] = "legend"


    result["scene_strategy"] = build_scene_strategy(
        result
    )


    # =====================================================
    # 🔥 FINAL STABILIZATION
    # =====================================================

    if result.get(
        "prefer_renderer"
    ):

        result[
            "avoid_force_generation"
        ] = True

        result[
            "explicit_image_generation"
        ] = False

    # =====================================================
    # 🔥 EXECUTION STABILIZATION
    # =====================================================

    if cognition.get(
        "prefer_execution"
    ):

        result[
            "prefer_execution"
        ] = True

    # =====================================================
    # 🔥 OUTPUT LOG
    # =====================================================

    safe_patch_log(

        f"INTERPRETATION COMPLETE | "
        f"type={result.get('type')} | "
        f"subtype={result.get('subtype')}"
    )

    # =====================================================
    # 🔥 FINAL
    # =====================================================

    return result
