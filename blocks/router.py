# blocks/router.py

from blocks.intent_ai import detect_intent_ai


# =====================================================
# 🧠 LOCAL SIGNALS
# =====================================================

def detect_intent_local(text: str):

    t = (text or "").lower().strip()

    # =================================================
    # 🔥 MATH
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
        "sin(",
        "cos("
    ]

    if any(x in t for x in math_words):

        return "science"

    # =================================================
    # 🔥 IMAGE GENERATION
    # =================================================

    image_generate_words = [

        "нарисуй",
        "создай изображение",
        "сгенерируй",
        "сделай картинку",
        "покажи изображение"
    ]

    if any(x in t for x in image_generate_words):

        return "image_generate"

    # =================================================
    # 🔥 IMAGE EDIT
    # =================================================

    image_edit_words = [

        "измени",
        "добавь",
        "убери",
        "замени",
        "сделай ярче",
        "сделай темнее",
        "поменяй"
    ]

    if any(x in t for x in image_edit_words):

        return "image_edit"

    return None


# =====================================================
# 🧠 CONTINUATION DETECTION
# =====================================================

def is_soft_continuation(text: str):

    t = (text or "").lower().strip()

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
        "уже лучше"
    ]

    if t in continuation_words:
        return True

    if len(t) <= 20:

        if any(
            w in t
            for w in continuation_words
        ):
            return True

    return False


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
    ) >= 0.7:
        return True

    return False


# =====================================================
# 🧠 EXPLORATION DETECTION
# =====================================================

def user_in_exploration(
    cognition,
    response_decision
):

    if cognition.get(
        "exploration_mode"
    ):
        return True

    if cognition.get(
        "inspiration_mode"
    ):
        return True

    if response_decision.get(
        "should_wait_for_user"
    ):
        return True

    return False


# =====================================================
# 🧠 SAFE ROUTER SUGGESTION
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
# 🧠 MAIN ROUTER
# =====================================================

async def route_request(
    text,
    ctx
):

    try:

        t = (
            text or ""
        ).lower().strip()

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
        # 🧠 META MEMORY
        # =================================================

        meta = state.get(
            "meta",
            {}
        )

        last_entity = meta.get(
            "last_entity"
        )

        active_flow = state.get(
            "active_flow"
        )

        # =================================================
        # 🧠 DEFAULT SAFE STATE
        # =================================================

        semantic[
            "router_is_soft"
        ] = True

        semantic[
            "router_authority"
        ] = "weak_hint"

        # =================================================
        # 🧠 REASONING AUTHORITY
        # =================================================

        continuation_target = reasoning.get(
            "continuation_target"
        )

        if continuation_target == "math":

            return set_router_hint(
                semantic,
                "science"
            )

        # =================================================
        # 🧠 IMAGE CONTINUATION
        # =================================================

        if continuation_target == "image":

            semantic[
                "image_continuation_detected"
            ] = True

            if is_soft_continuation(
                text
            ):

                semantic[
                    "soft_visual_continuation"
                ] = True

                set_router_hint(
                    semantic,
                    "image_edit"
                )

            if user_waiting_execution(
                semantic,
                cognition
            ):

                semantic[
                    "visual_execution_expected"
                ] = True

                set_router_hint(
                    semantic,
                    "image_edit"
                )

        # =================================================
        # 🧠 USER LEADS DIRECTION
        # =================================================

        if cognition.get(
            "user_leads_direction"
        ):

            semantic[
                "user_guided_scene"
            ] = True

            if cognition.get(
                "prefer_reference_over_generation"
            ):

                semantic[
                    "reference_priority"
                ] = True

        # =================================================
        # 🧠 VISUAL REFERENCE MODE
        # =================================================

        if response_decision.get(
            "should_offer_reference"
        ):

            semantic[
                "reference_mode"
            ] = True

        # =================================================
        # 🧠 EXPLORATION MODE
        # =================================================

        if cognition.get(
            "exploration_mode"
        ):

            semantic[
                "exploration_active"
            ] = True

        # =================================================
        # 🧠 VISUAL LIGHTWEIGHT MODE
        # =================================================

        if visual_reference.get(
            "lightweight_mode"
        ):

            semantic[
                "lightweight_visual_mode"
            ] = True

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

                return set_router_hint(
                    semantic,
                    room
                )

        # =================================================
        # 🧠 VISUAL EXECUTION
        # =================================================

        if (
            cognition.get(
                "prefer_visual"
            )
            and cognition.get(
                "wants_result",
                0.0
            ) >= 0.7
        ):

            semantic[
                "visual_execution_mode"
            ] = True

            set_router_hint(
                semantic,
                "image_generate"
            )

        # =================================================
        # 🧠 SCIENCE AUTHORITY
        # =================================================

        if semantic.get(
            "room"
        ) == "science":

            return set_router_hint(
                semantic,
                "science"
            )

        # =================================================
        # 🧠 META IMAGE MEMORY
        # =================================================

        if (
            last_entity
            and last_entity.get(
                "type"
            ) == "image"
        ):

            semantic[
                "image_memory_active"
            ] = True

            if is_soft_continuation(
                text
            ):

                semantic[
                    "image_memory_continuation"
                ] = True

                set_router_hint(
                    semantic,
                    "image_edit"
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
        # 🧠 SHORT TEXTS
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
        # 🧠 AI FALLBACK
        # =================================================

        intent = await detect_intent_ai(
            text
        )

        print(
            "🧠 AI ROUTER INTENT:",
            intent
        )

        # =================================================
        # 🧠 AI IMAGE GENERATE
        # =================================================

        if intent == "generate_image":

            semantic[
                "ai_image_generation"
            ] = True

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
            ):

                semantic[
                    "ai_image_edit"
                ] = True

                return set_router_hint(
                    semantic,
                    "image_edit"
                )

        # =================================================
        # 🧠 AI IMAGE ANALYZE
        # =================================================

        if intent == "analyze_image":

            if state.get(
                "image_context"
            ):

                semantic[
                    "ai_image_analysis"
                ] = True

                return set_router_hint(
                    semantic,
                    "image_edit"
                )

        # =================================================
        # 🧠 DEFAULT
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
