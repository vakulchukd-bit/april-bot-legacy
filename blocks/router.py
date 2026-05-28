# blocks/router.py

# =====================================================
# 🧠 APRIL WEB ROUTER
# =====================================================

"""
APRIL ROUTER — WEB SPACE ORCHESTRATION

Router теперь:
- calm orchestration layer;
- continuity-safe semantic router;
- renderer-first stabilizer;
- lightweight capability guide;
- provider-safe helper.

Router НЕ:
- authority system;
- execution owner;
- recursive retry source;
- hidden generation trigger;
- telegram dispatcher.

CORE PRINCIPLES:

1. continuation before reroute
2. renderer before generation
3. lightweight before heavy
4. preserve active scene
5. avoid hidden escalation
6. no provider chaos
7. no room wars
"""

# =====================================================
# 🔥 OPTIONAL AI HINT
# =====================================================

try:

    from blocks.intent_ai import (
        detect_intent_ai
    )

    AI_INTENT_AVAILABLE = True

except Exception:

    AI_INTENT_AVAILABLE = False

    async def detect_intent_ai(text):

        return None

# =====================================================
# 🔥 MACHINE IDENTITY
# =====================================================

APRIL_FILE_ID = "APRIL_WEB_ROUTER"

ROUTER_MACHINE_CHANNEL = {

    "type": "semantic_router",

    "mode": "supportive",

    "authority": "soft",

    "web_safe": True,

    "renderer_first": True,

    "continuity_safe": True
}

# =====================================================
# 🔥 ROUTER CONTRACT
# =====================================================

def build_router_contract():

    return {

        "router_type":
            "lightweight_semantic_stabilizer",

        "execution_authority":
            False,

        "renderer_authority":
            False,

        "generation_authority":
            False,

        "provider_authority":
            False,

        "semantic_mutation_minimized":
            True,

        "continuity_first":
            True,

        "web_oriented":
            True
    }

# =====================================================
# 🔥 LOGGING
# =====================================================

ROUTER_PATCH_LOG = []

def safe_router_log(msg):

    try:

        print(
            "APRIL ROUTER:",
            msg
        )

        ROUTER_PATCH_LOG.append(
            str(msg)
        )

    except:
        pass

safe_router_log(
    "APRIL WEB ROUTER INITIALIZED"
)

ROUTER_CONTRACT = build_router_contract()

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

    semantic[
        "router_last_hint"
    ] = hint

    return hint

# =====================================================
# 🧠 SAFE FLAGS
# =====================================================

def apply_router_stabilization(
    semantic: dict
):

    semantic[
        "router_is_soft"
    ] = True

    semantic[
        "router_authority"
    ] = "supportive"

    semantic[
        "router_renderer_aware"
    ] = True

    semantic[
        "router_continuity_first"
    ] = True

    semantic[
        "router_renderer_first"
    ] = True

    semantic[
        "router_anti_escalation"
    ] = True

    semantic[
        "router_anti_recursion"
    ] = True

    semantic[
        "router_preserve_scene"
    ] = True

    semantic[
        "router_preserve_flow"
    ] = True

    semantic[
        "router_generation_requires_intent"
    ] = True

    semantic[
        "router_lightweight_priority"
    ] = True

    semantic[
        "router_hidden_generation_blocked"
    ] = True

    return semantic

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
        "еще",
        "вот",
        "примерно",
        "ближе",
        "уже лучше",
        "дальше",
        "снова",
        "поехали",
        "оставь",
        "так",
        "в таком стиле"
    ]

    if t in continuation_words:
        return True

    if len(t) <= 28:

        if contains_any(
            t,
            continuation_words
        ):

            return True

    return False

# =====================================================
# 🧠 VISUAL CONTINUITY
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
        "цвет",
        "слева",
        "справа",
        "фон",
        "стиль",
        "атмосфера",
        "форма",
        "размер"
    ]

    if contains_any(
        t,
        visual_words
    ):

        return True

    if len(t) <= 48:

        return True

    return False

# =====================================================
# 🧠 LOCAL DETECTION
# =====================================================

def detect_intent_local(
    text: str
):

    t = normalize(text)

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

    renderer_words = [

        "таблица",
        "формула",
        "diagram",
        "диаграмма",
        "схема",
        "layout",
        "grid",
        "renderer",
        "пространство",
        "scene",
        "композиция",
        "canvas",
        "блок"
    ]

    if contains_any(
        t,
        renderer_words
    ):

        return "renderer_space"

    generate_words = [

        "создай изображение",
        "сгенерируй изображение",
        "нарисуй картинку",
        "создай картинку",
        "draw image",
        "generate image",
        "создай арт",
        "сделай арт"
    ]

    if contains_any(
        t,
        generate_words
    ):

        return "image_generate"

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
# 🧠 RENDERER PRIORITY
# =====================================================

def renderer_priority_active(
    semantic,
    cognition
):

    if semantic.get(
        "prefer_renderer"
    ):

        return True

    if semantic.get(
        "render_intent"
    ):

        return True

    if cognition.get(
        "prefer_renderer"
    ):

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

        apply_router_stabilization(
            semantic
        )

        active_flow = state.get(
            "active_flow"
        )

        continuation_target = reasoning.get(
            "continuation_target"
        )

        # =================================================
        # 🔥 RENDERER PRIORITY
        # =====================================================

        if renderer_priority_active(
            semantic,
            cognition
        ):

            semantic[
                "renderer_route_locked"
            ] = True

            return set_router_hint(
                semantic,
                "renderer_space"
            )

        # =================================================
        # 🔥 SCIENCE CONTINUATION
        # =====================================================

        if continuation_target == "math":

            semantic[
                "math_continuation"
            ] = True

            return set_router_hint(
                semantic,
                "science"
            )

        # =================================================
        # 🔥 VISUAL CONTINUITY
        # =====================================================

        if detect_visual_continuation(
            text,
            state
        ):

            semantic[
                "router_visual_continuity"
            ] = True

            return set_router_hint(
                semantic,
                "image_edit"
            )

        # =================================================
        # 🔥 EXPLORATION MODE
        # =====================================================

        if cognition.get(
            "exploration_mode"
        ):

            semantic[
                "exploration_active"
            ] = True

            semantic[
                "generation_should_wait"
            ] = True

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
        # 🔥 REFERENCE MODE
        # =====================================================

        if response_decision.get(
            "should_offer_reference"
        ):

            semantic[
                "reference_mode"
            ] = True

            return set_router_hint(
                semantic,
                "text"
            )

        # =================================================
        # 🔥 HARD EXECUTION
        # =====================================================

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
        # 🔥 LOCAL DETECTION
        # =====================================================

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
        # 🔥 ACTIVE FLOW
        # =====================================================

        if active_flow:

            flow_type = active_flow.get(
                "type"
            )

            semantic[
                "active_flow_detected"
            ] = True

            if flow_type == "math":

                return set_router_hint(
                    semantic,
                    "science"
                )

            if flow_type in [

                "renderer_space",
                "visual_scene"
            ]:

                return set_router_hint(
                    semantic,
                    "renderer_space"
                )

            if flow_type in [

                "image",
                "image_generate",
                "image_edit"
            ]:

                if is_soft_continuation(
                    text
                ):

                    return set_router_hint(
                        semantic,
                        "image_edit"
                    )

        # =================================================
        # 🔥 SHORT INPUT
        # =====================================================

        if len(t) <= 12:

            semantic[
                "short_input_detected"
            ] = True

            return semantic.get(
                "router_suggestion",
                "text"
            )

        # =================================================
        # 🔥 OPTIONAL AI HINT
        # =====================================================

        intent = None

        if (

            AI_INTENT_AVAILABLE

            and not semantic.get(
                "renderer_route_locked"
            )

        ):

            try:

                intent = await detect_intent_ai(
                    text
                )

                safe_router_log(
                    f"AI HINT: {intent}"
                )

            except Exception as e:

                safe_router_log(
                    f"AI HINT ERROR: {e}"
                )

                intent = None

        # =================================================
        # 🔥 AI IMAGE GENERATION
        # =====================================================

        if intent == "generate_image":

            semantic[
                "ai_image_generation"
            ] = True

            if cognition.get(
                "exploration_mode"
            ):

                semantic[
                    "generation_should_wait"
                ] = True

                return set_router_hint(
                    semantic,
                    "text"
                )

            return set_router_hint(
                semantic,
                "image_generate"
            )

        # =================================================
        # 🔥 AI IMAGE EDIT
        # =====================================================

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
        # 🔥 WEB CONTEXT
        # =====================================================

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
        # 🔥 DEFAULT SAFE ROUTE
        # =====================================================

        semantic[
            "default_safe_route"
        ] = True

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
