# blocks/router.py

from blocks.intent_ai import detect_intent_ai


# =====================================================
# 🧠 ROUTER PHILOSOPHY
# =====================================================

"""
APRIL ROUTER — WEB SPACE STABILIZED

Router больше НЕ:
- authority layer;
- hard execution switch;
- forced generation system;
- telegram-oriented dispatcher.

Router теперь:
- lightweight semantic hint system;
- continuity-safe helper;
- renderer-aware assistant;
- provider-aware routing stabilizer.

Главное правило:
router НЕ принимает финальных решений.
Финальное решение принадлежит:
semantic + cognition + response_decision.
"""

# =====================================================
# 🧠 HELPERS
# =====================================================

def normalize(text: str):

    return (
        text or ""
    ).lower().strip()


def contains_any(
    text: str,
    words: list
):

    return any(
        w in text
        for w in words
    )


# =====================================================
# 🧠 SAFE ROUTER HINT
# =====================================================

def set_router_hint(
    semantic,
    hint
):

    semantic[
        "router_suggestion"
    ] = hint

    return hint


# =====================================================
# 🧠 CONTINUATION
# =====================================================

def is_soft_continuation(
    text: str
):

    t = normalize(text)

    continuation_words = [

        "да",
        "ага",
        "ок",
        "окей",
        "давай",
        "продолжай",
        "ещё",
        "вот",
        "примерно",
        "ближе",
        "уже лучше",
        "дальше",
        "снова",
        "поехали"
    ]

    if t in continuation_words:
        return True

    if len(t) <= 24:

        if contains_any(
            t,
            continuation_words
        ):
            return True

    return False


# =====================================================
# 🧠 VISUAL CONTINUATION
# =====================================================

def detect_visual_continuation(
    text: str,
    state: dict
):

    t = normalize(text)

    active_visual_scene = state.get(
        "active_visual_scene"
    )

    if not active_visual_scene:
        return False

    visual_words = [

        "это",
        "этот",
        "эта",
        "там",
        "на картинке",
        "на фото",
        "объект",
        "цвет",
        "слева",
        "справа",
        "фон",
        "стиль",
        "атмосфера",
        "меню",
        "бокал",
        "бургер",
        "креветки"
    ]

    if contains_any(
        t,
        visual_words
    ):

        return True

    if len(t) <= 40:

        return True

    return False


# =====================================================
# 🧠 LOCAL DETECTION
# =====================================================

def detect_intent_local(
    text: str
):

    t = normalize(text)

    # =================================================
    # 🔥 SCIENCE
    # =================================================

    math_words = [

        "=",
        "+",
        "-",
        "*",
        "/",
        "^",
        "реши",
        "уравнение",
        "график",
        "функция",
        "sin(",
        "cos(",
        "tan(",
        "y="
    ]

    if contains_any(
        t,
        math_words
    ):

        return "science"

    # =================================================
    # 🔥 IMAGE GENERATION
    # =================================================

    generate_words = [

        "создай изображение",
        "сгенерируй изображение",
        "нарисуй картинку",
        "сделай картинку",
        "создай арт",
        "создай фото"
    ]

    if contains_any(
        t,
        generate_words
    ):

        return "image_generate"

    # =================================================
    # 🔥 IMAGE EDIT
    # =================================================

    edit_words = [

        "измени",
        "добавь",
        "убери",
        "замени",
        "сделай ярче",
        "сделай темнее",
        "поменяй",
        "исправь"
    ]

    if contains_any(
        t,
        edit_words
    ):

        return "image_edit"

    return None


# =====================================================
# 🧠 EXECUTION DETECTION
# =====================================================

def user_waiting_execution(
    semantic,
    cognition
):

    if semantic.get(
        "should_execute"
    ):

        return True

    if cognition.get(
        "prefer_execution"
    ):

        return True

    if cognition.get(
        "wants_result",
        0.0
    ) >= 0.72:

        return True

    return False


# =====================================================
# 🧠 MAIN ROUTER
# =====================================================

async def route_request(
    text,
    ctx
):

    try:

        t = normalize(text)

        ctx = ctx or {}

        state = ctx.get(
            "state",
            {}
        )

        semantic = ctx.get(
            "semantic",
            {}
        )

        cognition = ctx.get(
            "cognition",
            {}
        )

        reasoning = ctx.get(
            "reasoning",
            {}
        )

        response_decision = ctx.get(
            "response_decision",
            {}
        )

        visual_reference = ctx.get(
            "visual_reference",
            {}
        )

        # =================================================
        # 🧠 SAFE DEFAULTS
        # =================================================

        semantic[
            "router_is_soft"
        ] = True

        semantic[
            "router_authority"
        ] = "weak_hint"

        semantic[
            "router_provider_aware"
        ] = True

        semantic[
            "router_renderer_aware"
        ] = True

        # =================================================
        # 🧠 ACTIVE FLOW
        # =================================================

        active_flow = state.get(
            "active_flow"
        )

        continuation_target = reasoning.get(
            "continuation_target"
        )

        # =================================================
        # 🧠 SCIENCE CONTINUATION
        # =================================================

        if continuation_target == "math":

            semantic[
                "math_continuation"
            ] = True

            return set_router_hint(
                semantic,
                "science"
            )

        # =================================================
        # 🧠 VISUAL CONTINUITY
        # =================================================

        if detect_visual_continuation(
            text,
            state
        ):

            semantic[
                "visual_continuity"
            ] = True

            semantic[
                "renderer_scene_continuity"
            ] = True

            if user_waiting_execution(
                semantic,
                cognition
            ):

                semantic[
                    "visual_execution_expected"
                ] = True

            return set_router_hint(
                semantic,
                "image_edit"
            )

        # =================================================
        # 🧠 EXPLORATION MODE
        # =================================================

        if cognition.get(
            "exploration_mode"
        ):

            semantic[
                "exploration_active"
            ] = True

            semantic[
                "generation_should_wait"
            ] = True

            # 🔥 exploration больше
            # НЕ форсит generation

            if visual_reference.get(
                "lightweight_mode"
            ):

                semantic[
                    "lightweight_visual_mode"
                ] = True

                return set_router_hint(
                    semantic,
                    "text"
                )

        # =================================================
        # 🧠 REFERENCE MODE
        # =================================================

        if response_decision.get(
            "should_offer_reference"
        ):

            semantic[
                "reference_mode"
            ] = True

            semantic[
                "lightweight_visual_mode"
            ] = True

            return set_router_hint(
                semantic,
                "text"
            )

        # =================================================
        # 🧠 HARD EXECUTION
        # =================================================

        if semantic.get(
            "should_execute"
        ):

            room = semantic.get(
                "room"
            )

            if room:

                semantic[
                    "execution_locked"
                ] = True

                return set_router_hint(
                    semantic,
                    room
                )

        # =================================================
        # 🧠 LOCAL DETECTION
        # =================================================

        local = detect_intent_local(
            text
        )

        if local:

            semantic[
                "local_detection_used"
            ] = True

            return set_router_hint(
                semantic,
                local
            )

        # =================================================
        # 🧠 ACTIVE FLOW SUPPORT
        # =================================================

        if active_flow:

            flow_type = active_flow.get(
                "type"
            )

            if flow_type == "math":

                return set_router_hint(
                    semantic,
                    "science"
                )

            if flow_type in [

                "image",
                "image_generate",
                "image_edit"
            ]:

                semantic[
                    "image_flow_active"
                ] = True

                if is_soft_continuation(
                    text
                ):

                    return set_router_hint(
                        semantic,
                        "image_edit"
                    )

        # =================================================
        # 🧠 SHORT INPUT
        # =================================================

        if len(t) <= 12:

            semantic[
                "short_input_detected"
            ] = True

            return semantic.get(
                "router_suggestion",
                "text"
            )

        # =================================================
        # 🧠 AI DETECTION
        # =================================================

        intent = await detect_intent_ai(
            text
        )

        print(
            "🧠 AI ROUTER INTENT:",
            intent
        )

        # =================================================
        # 🧠 AI IMAGE GENERATION
        # =================================================

        if intent == "generate_image":

            semantic[
                "ai_image_generation"
            ] = True

            # 🔥 provider-aware:
            # generation только
            # при явном intent

            if cognition.get(
                "exploration_mode"
            ):

                return set_router_hint(
                    semantic,
                    "text"
                )

            return set_router_hint(
                semantic,
                "image_generate"
            )

        # =================================================
        # 🧠 AI IMAGE EDIT
        # =================================================

        if intent == "edit_image":

            if state.get(
                "image_context"
            ) or state.get(
                "active_visual_scene"
            ):

                semantic[
                    "ai_image_edit"
                ] = True

                return set_router_hint(
                    semantic,
                    "image_edit"
                )

        # =================================================
        # 🧠 AI IMAGE ANALYSIS
        # =================================================

        if intent == "analyze_image":

            if state.get(
                "image_context"
            ) or state.get(
                "active_visual_scene"
            ):

                semantic[
                    "ai_image_analysis"
                ] = True

                # 🔥 analyze_image теперь
                # НЕ форсит generation

                return set_router_hint(
                    semantic,
                    "text"
                )

        # =================================================
        # 🧠 WEB / REALTIME
        # =================================================

        if cognition.get(
            "internet_context_needed"
        ):

            semantic[
                "web_context_route"
            ] = True

            return set_router_hint(
                semantic,
                "text"
            )

        # =================================================
        # 🧠 DEFAULT SAFE ROUTE
        # =================================================

        return semantic.get(
            "router_suggestion",
            "text"
        )

    except Exception as e:

        print(
            "🔥 ROUTER ERROR:",
            e
        )

        return "text"
