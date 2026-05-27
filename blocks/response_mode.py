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

    t = (
        text or ""
    ).lower().strip()

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

        if active_visual_scene:
            return "visual_continuation"

        if active_flow:
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

            return artifact_map[
                artifact
            ]

        if scene_completion_required:

            semantic[
                "multi_scene_response"
            ] = True

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

                return "continuation"

    # =====================================================
    # 🔥 SEMANTIC OVERRIDES
    # =====================================================

    if semantic.get(
        "internet_context_needed"
    ):

        return "web"

    if cognition.get(
        "exploration_mode"
    ):

        return "exploration"

    # =====================================================
    # 🔥 DEFAULT
    # =====================================================

    return "normal"
