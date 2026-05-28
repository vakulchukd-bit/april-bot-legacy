# =====================================================
# 🧠 APRIL RESPONSE MODE DETECTOR
# =====================================================
#
# APRIL_FILE_ID:
# APRIL_RESPONSE_MODE_DETECTOR
#
# ROLE:
# LIGHTWEIGHT_MODALITY_CLASSIFIER
#
# INPUT:
# USER_TEXT
# STATE
# SEMANTIC_SIGNALS
# COGNITION_SIGNALS
#
# OUTPUT:
# RESPONSE_MODE
# RENDERER_MODE
# CONTINUATION_MODE
# ROUTING_HINT
#
# DEPENDENCIES:
# semantic_core
# cognition
# response_decision
# excrouter
# renderer_space
#
# =====================================================
#
# APRIL RESPONSE MODE DETECTOR
#
# Lightweight orchestration detector.
#
# Этот слой:
# - НЕ authority;
# - НЕ executor;
# - НЕ router override.
#
# Этот слой:
# - помогает orchestration;
# - удерживает continuity;
# - stabilizes renderer routing;
# - разделяет visual/render/generate;
# - уменьшает routing chaos.
#
# =====================================================

print(
    "🧠 APRIL RESPONSE MODE DETECTOR LOADED"
)

# =====================================================
# 🔥 PATCH LOG
# =====================================================

MODE_PATCH_LOG = []

def safe_mode_log(*args):

    try:

        print(
            "APRIL MODE DETECTOR:",
            *args
        )

        MODE_PATCH_LOG.append(
            " ".join(
                [str(x) for x in args]
            )
        )

    except:
        pass


# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

INPUT_MACHINE_CHANNEL = {

    "source":
        "semantic_reasoning",

    "target":
        "response_mode_detector",

    "isolated":
        True
}

OUTPUT_MACHINE_CHANNEL = {

    "source":
        "response_mode_detector",

    "target":
        "response_decision",

    "isolated":
        True
}


# =====================================================
# 🔥 SAFE HELPERS
# =====================================================

def normalize_text(
    text: str
):

    return (
        text or ""
    ).lower().strip()


# =====================================================
# 🔥 MAIN DETECTOR
# =====================================================

def detect_response_mode(
    text: str,
    state: dict = None,
    semantic: dict = None,
    cognition: dict = None
) -> str:

    """
    APRIL RESPONSE MODE DETECTOR

    Lightweight orchestration detector.

    Этот слой:
    - НЕ authority;
    - НЕ executor;
    - НЕ router override.

    Этот слой:
    - помогает orchestration;
    - удерживает continuity;
    - stabilizes renderer routing;
    - разделяет visual/render/generate;
    - уменьшает routing chaos.
    """

    safe_mode_log(
        "MODE DETECTION START"
    )

    t = normalize_text(text)

    state = state or {}
    semantic = semantic or {}
    cognition = cognition or {}

    active_flow = state.get(
        "active_flow",
        {}
    )

    active_visual_scene = state.get(
        "active_visual_scene",
        {}
    )

    safe_mode_log(
        "INPUT:",
        t[:120]
    )

    # =====================================================
    # 🔥 SEMANTIC SIGNALS
    # =====================================================

    expected_artifact = semantic.get(
        "expected_artifact"
    )

    render_type = semantic.get(
        "render_type"
    )

    render_intent = semantic.get(
        "render_intent",
        False
    )

    prefer_renderer = semantic.get(
        "prefer_renderer",
        False
    )

    renderer_payload_expected = semantic.get(
        "renderer_payload_expected",
        False
    )

    scene_completion_required = semantic.get(
        "scene_completion_required",
        False
    )

    # =====================================================
    # 🔥 CONTINUATION
    # =====================================================

    continuation_triggers = [

        "да",
        "ага",
        "ок",
        "окей",
        "вот",
        "примерно",
        "ближе",
        "уже лучше",
        "дальше",
        "продолжай",
        "не то",
        "оставь",
        "в таком стиле"
    ]

    if t in continuation_triggers:

        safe_mode_log(
            "CONTINUATION DETECTED"
        )

        if active_visual_scene:

            safe_mode_log(
                "VISUAL CONTINUATION"
            )

            return "visual_continuation"

        if active_flow:

            safe_mode_log(
                "FLOW CONTINUATION"
            )

            return "continuation"

        return "casual"

    # =====================================================
    # 🔥 RENDERER LOCK
    # =====================================================

    renderer_lock = bool(

        render_intent
        or prefer_renderer
        or renderer_payload_expected
    )

    if renderer_lock:

        safe_mode_log(
            "RENDERER LOCK ACTIVE"
        )

        semantic[
            "renderer_scene_locked"
        ] = True

        semantic[
            "renderer_payload_expected"
        ] = True

        artifact_map = {

            "graph":
                "renderer_graph",

            "formula":
                "renderer_formula",

            "table":
                "renderer_table",

            "diagram":
                "renderer_diagram",

            "code":
                "renderer_code",

            "link":
                "renderer_link"
        }

        artifact = (
            expected_artifact
            or render_type
        )

        if artifact in artifact_map:

            semantic[
                "confirmed_renderer_artifact"
            ] = artifact

            safe_mode_log(
                "RENDER ARTIFACT:",
                artifact
            )

            return artifact_map[
                artifact
            ]

        if scene_completion_required:

            semantic[
                "multi_scene_response"
            ] = True

            safe_mode_log(
                "MULTI RENDERER MODE"
            )

            return "renderer_multi"

        return "renderer"

    # =====================================================
    # 🔥 KEYWORD GROUPS
    # =====================================================

    mode_groups = {

        "renderer": [

            "график",
            "формула",
            "таблица",
            "diagram",
            "диаграмма",
            "схема",
            "layout",
            "grid",
            "scene",
            "renderer",
            "canvas"
        ],

        "spatial": [

            "слева",
            "справа",
            "сверху",
            "снизу",
            "размести",
            "расположи",
            "между"
        ],

        "link": [

            "ссылка",
            "url",
            "линк",
            "short link"
        ],

        "web": [

            "погода",
            "новости",
            "курс валют",
            "маршрут",
            "карта",
            "рейс",
            "сейчас"
        ],

        "copy": [

            "шаблон",
            "письмо",
            "документ",
            "напиши сообщение",
            "готовый текст"
        ],

        "format": [

            "оформи",
            "структурируй",
            "разбей текст",
            "сделай красиво"
        ],

        "visual": [

            "что на фото",
            "что изображено",
            "что видишь",
            "проанализируй фото"
        ],

        "lightweight_visual": [

            "референс",
            "пример",
            "концепт",
            "идея",
            "атмосфера"
        ],

        "generate": [

            "создай изображение",
            "сгенерируй изображение",
            "создай арт",
            "4k render",
            "ultra realistic"
        ],

        "supportive": [

            "помоги",
            "объясни",
            "что делать",
            "подскажи"
        ],

        "casual": [

            "привет",
            "hello",
            "доброе утро",
            "как дела"
        ]
    }

    # =====================================================
    # 🔥 MODE DETECTION
    # =====================================================

    for mode, words in mode_groups.items():

        if any(
            word in t
            for word in words
        ):

            safe_mode_log(
                "MODE DETECTED:",
                mode
            )

            return mode

    # =====================================================
    # 🔥 ACTIVE FLOW
    # =====================================================

    if active_flow:

        flow_type = active_flow.get(
            "type"
        )

        if flow_type in [

            "renderer_space",
            "visual_scene",
            "image_generate",
            "image_edit",
            "math"
        ]:

            if len(t) <= 40:

                safe_mode_log(
                    "ACTIVE FLOW CONTINUATION:",
                    flow_type
                )

                return "continuation"

    # =====================================================
    # 🔥 SEMANTIC OVERRIDES
    # =====================================================

    if semantic.get(
        "internet_context_needed"
    ):

        safe_mode_log(
            "WEB OVERRIDE"
        )

        return "web"

    if cognition.get(
        "exploration_mode"
    ):

        safe_mode_log(
            "EXPLORATION OVERRIDE"
        )

        return "exploration"

    # =====================================================
    # 🔥 DEFAULT
    # =====================================================

    safe_mode_log(
        "DEFAULT NORMAL MODE"
    )

    return "normal"
