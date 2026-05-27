def detect_response_mode(
    text: str,
    state: dict = None,
    semantic: dict = None,
    cognition: dict = None
) -> str:

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

    expected_artifact = semantic.get(
        "expected_artifact"
    )

    expected_output_type = semantic.get(
        "expected_output_type"
    )

    render_type = semantic.get(
        "render_type"
    )

    renderer_payload_expected = semantic.get(
        "renderer_payload_expected",
        False
    )

    renderer_scene_priority = semantic.get(
        "renderer_scene_priority",
        False
    )

    render_intent = semantic.get(
        "render_intent",
        False
    )

    prefer_renderer = semantic.get(
        "prefer_renderer",
        False
    )

    scene_completion_required = semantic.get(
        "scene_completion_required",
        False
    )

    # =====================================================
    # 🔥 CONTINUATION SAFETY
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
        "сделай темнее",
        "сделай ярче",
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
    # 🔥 SEMANTIC RENDERER LOCK
    # =====================================================

    if (

        render_intent
        or prefer_renderer
        or renderer_payload_expected
        or renderer_scene_priority
    ):

        # =================================================
        # 🔥 GRAPH
        # =====================================================

        if (

            expected_artifact == "graph"
            or expected_output_type == "graph"
            or render_type == "graph"
        ):

            semantic[
                "confirmed_renderer_artifact"
            ] = "graph"

            semantic[
                "renderer_payload_expected"
            ] = True

            semantic[
                "renderer_scene_locked"
            ] = True

            return "renderer_graph"

        # =================================================
        # 🔥 FORMULA
        # =====================================================

        if (

            expected_artifact == "formula"
            or expected_output_type == "formula"
            or render_type == "formula"
        ):

            semantic[
                "confirmed_renderer_artifact"
            ] = "formula"

            semantic[
                "renderer_payload_expected"
            ] = True

            semantic[
                "renderer_scene_locked"
            ] = True

            return "renderer_formula"

        # =================================================
        # 🔥 TABLE
        # =====================================================

        if (

            expected_artifact == "table"
            or expected_output_type == "table"
            or render_type == "table"
        ):

            semantic[
                "confirmed_renderer_artifact"
            ] = "table"

            semantic[
                "renderer_payload_expected"
            ] = True

            semantic[
                "renderer_scene_locked"
            ] = True

            return "renderer_table"

        # =================================================
        # 🔥 DIAGRAM
        # =====================================================

        if (

            expected_artifact == "diagram"
            or expected_output_type == "diagram"
            or render_type == "diagram"
        ):

            semantic[
                "confirmed_renderer_artifact"
            ] = "diagram"

            semantic[
                "renderer_payload_expected"
            ] = True

            semantic[
                "renderer_scene_locked"
            ] = True

            return "renderer_diagram"

        # =================================================
        # 🔥 CODE
        # =====================================================

        if (

            expected_artifact == "code"
            or expected_output_type == "code"
            or render_type == "code"
        ):

            semantic[
                "confirmed_renderer_artifact"
            ] = "code"

            semantic[
                "renderer_payload_expected"
            ] = True

            semantic[
                "renderer_scene_locked"
            ] = True

            return "renderer_code"

        # =================================================
        # 🔥 LINK
        # =====================================================

        if (

            expected_artifact == "link"
            or expected_output_type == "link"
            or render_type == "link"
        ):

            semantic[
                "confirmed_renderer_artifact"
            ] = "link"

            semantic[
                "renderer_payload_expected"
            ] = True

            semantic[
                "renderer_scene_locked"
            ] = True

            return "renderer_link"

        # =================================================
        # 🔥 MULTI BLOCK
        # =====================================================

        if scene_completion_required:

            semantic[
                "multi_scene_response"
            ] = True

            semantic[
                "renderer_payload_expected"
            ] = True

            semantic[
                "renderer_scene_locked"
            ] = True

            return "renderer_multi"

        # =================================================
        # 🔥 SAFE GENERIC RENDERER
        # =====================================================

        semantic[
            "renderer_payload_expected"
        ] = True

        semantic[
            "renderer_scene_locked"
        ] = True

        return "renderer"

    # =====================================================
    # 🔥 RENDERER-FIRST
    # =====================================================

    renderer_triggers = [

        "график",
        "формула",
        "таблица",
        "diagram",
        "диаграмма",
        "схема",
        "layout",
        "структура",
        "grid",
        "scene",
        "пространство",
        "renderer",
        "canvas"
    ]

    for w in renderer_triggers:

        if w in t:

            return "renderer"

    # =====================================================
    # 🔥 SPATIAL / SCENE
    # =====================================================

    spatial_triggers = [

        "слева",
        "справа",
        "сверху",
        "снизу",
        "по центру",
        "расположи",
        "размести",
        "между",
        "рядом"
    ]

    for w in spatial_triggers:

        if w in t:

            return "spatial"

    # =====================================================
    # ===== LINK MODE
    # =====================================================

    link_triggers = [

        "ссылка",
        "url",
        "линк",
        "дай ссылку",
        "короткую ссылку",
        "сократи ссылку",
        "сокращённую ссылку",
        "short link"
    ]

    for w in link_triggers:

        if w in t:

            return "link"

    # =====================================================
    # 🔥 WEB / LIVE
    # =====================================================

    web_triggers = [

        "погода",
        "новости",
        "курс валют",
        "что происходит",
        "маршрут",
        "карта",
        "рейс",
        "сейчас"
    ]

    for w in web_triggers:

        if w in t:

            return "web"

    # =====================================================
    # ===== COPY / READY TEXT
    # =====================================================

    copy_triggers = [

        "скопируй",
        "для копирования",
        "копировать",
        "дай текст",
        "готовый текст",
        "шаблон",
        "напиши текст",
        "заявление",
        "письмо",
        "документ",
        "сообщение клиенту",
        "напиши сообщение",
        "сделай текст",
        "напиши красиво"
    ]

    for w in copy_triggers:

        if w in t:

            return "copy"

    # =====================================================
    # ===== FORMATTED / STRUCTURED
    # =====================================================

    format_triggers = [

        "красиво",
        "оформи",
        "сделай красиво",
        "оформи текст",
        "структурируй",
        "сделай читабельно",
        "разбей текст"
    ]

    for w in format_triggers:

        if w in t:

            return "format"

    # =====================================================
    # ===== VISUAL / CAMERA / IMAGE
    # =====================================================

    visual_triggers = [

        "что на фото",
        "что это",
        "что изображено",
        "что видишь",
        "посмотри",
        "проанализируй фото",
        "объясни фото",
        "что за место",
        "что за объект",
        "что это такое"
    ]

    for w in visual_triggers:

        if w in t:

            return "visual"

    # =====================================================
    # 🔥 LIGHTWEIGHT VISUAL
    # =====================================================

    lightweight_visual_triggers = [

        "референс",
        "пример",
        "концепт",
        "идея",
        "атмосфера",
        "примерно как",
        "визуально"
    ]

    for w in lightweight_visual_triggers:

        if w in t:

            return "lightweight_visual"

    # =====================================================
    # 🔥 HEAVY IMAGE GENERATION
    # =====================================================

    generate_triggers = [

        "создай изображение",
        "сгенерируй изображение",
        "нарисуй картинку",
        "создай арт",
        "создай фото",
        "ultra realistic",
        "4k render"
    ]

    for w in generate_triggers:

        if w in t:

            return "generate"

    # =====================================================
    # ===== SUPPORTIVE / HUMAN
    # =====================================================

    supportive_triggers = [

        "помоги",
        "не понимаю",
        "объясни",
        "что делать",
        "как быть",
        "подскажи",
        "посоветуй"
    ]

    for w in supportive_triggers:

        if w in t:

            return "supportive"

    # =====================================================
    # ===== SHORT CASUAL
    # =====================================================

    short_triggers = [

        "привет",
        "хай",
        "hello",
        "доброе утро",
        "добрый вечер",
        "как дела"
    ]

    for w in short_triggers:

        if w in t:

            return "casual"

    # =====================================================
    # 🔥 ACTIVE FLOW CONTINUITY
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
        "render_intent"
    ):

        return "renderer"

    if semantic.get(
        "internet_context_needed"
    ):

        return "web"

    if cognition.get(
        "exploration_mode"
    ):

        return "exploration"

    # =====================================================
    # ===== DEFAULT
    # =====================================================

    return "normal"
