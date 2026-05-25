from openai import OpenAI
import asyncio

client = OpenAI()


# =====================================================
# 🧠 APRIL INTENT AI
# =====================================================

"""
APRIL MULTI-SIGNAL INTENT SYSTEM

Intent AI теперь:
- НЕ single-intent dispatcher;
- НЕ room selector;
- НЕ authority system.

Intent AI теперь:
- multimodal signal analyzer;
- orchestration helper;
- continuation-aware interpreter;
- renderer-aware signal composer;
- capability hint provider.

Главная идея:
Intent НЕ принимает решение.
Intent помогает orchestration layer
понять направление пользователя.
"""

# =====================================================
# 🧠 HELPERS
# =====================================================

def normalize(
    text: str
):

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
# 🧠 SAFE SIGNAL BUILDER
# =====================================================

def build_signal_response(

    primary_intent="text",
    confidence=0.5,
    source="local",

    signals=None,
    capability_hints=None,

    continuation=False,
    renderer=False,
    visual=False,
    execution=False,
    explanation=False,
    exploration=False,
    web=False
):

    signals = signals or {}

    capability_hints = capability_hints or []

    return {

        # =================================================
        # 🔥 LEGACY COMPATIBILITY
        # =====================================================

        "intent": primary_intent,

        # =================================================
        # 🔥 NEW ARCHITECTURE
        # =====================================================

        "primary_intent":
            primary_intent,

        "confidence":
            confidence,

        "source":
            source,

        # =================================================
        # 🔥 SIGNALS
        # =====================================================

        "signals": {

            "continuation":
                continuation,

            "renderer":
                renderer,

            "visual":
                visual,

            "execution":
                execution,

            "explanation":
                explanation,

            "exploration":
                exploration,

            "web":
                web,

            **signals
        },

        # =================================================
        # 🔥 CAPABILITIES
        # =====================================================

        "capability_hints":
            capability_hints,

        # =================================================
        # 🔥 STABILIZATION
        # =====================================================

        "orchestration_ready": True,

        "renderer_first_safe": True,

        "provider_aware": True,

        "single_route_forbidden": True
    }


# =====================================================
# 🧠 LOCAL SAFE DETECTION
# =====================================================

def detect_intent_local(
    text: str,
    state: dict = None
):

    t = normalize(text)

    state = state or {}

    active_flow = state.get(
        "active_flow",
        {}
    )

    active_visual_scene = state.get(
        "active_visual_scene",
        {}
    )

    # =================================================
    # 🔥 CONTINUATION
    # =====================================================

    continuation_words = [

        "да",
        "ага",
        "вот",
        "примерно",
        "ближе",
        "уже лучше",
        "чуть темнее",
        "чуть светлее",
        "сделай темнее",
        "сделай ярче",
        "не то",
        "переделай",
        "продолжай",
        "дальше",
        "еще",
        "оставь",
        "в таком стиле"
    ]

    if t in continuation_words:

        if active_flow:

            flow_type = active_flow.get(
                "type"
            )

            if flow_type in [

                "image_generate",
                "image_edit",
                "image",
                "renderer_space",
                "math",
                "scene"
            ]:

                return build_signal_response(

                    primary_intent="continuation",

                    confidence=0.86,

                    source="local_continuation",

                    continuation=True,

                    visual=True,

                    renderer=(
                        flow_type in [
                            "renderer_space",
                            "math",
                            "scene"
                        ]
                    ),

                    capability_hints=[

                        "continuation",
                        "trajectory",
                        "renderer_space"
                    ]
                )

        return build_signal_response(

            primary_intent="text",

            confidence=0.55,

            source="soft_continuation",

            continuation=True,

            capability_hints=[

                "conversation"
            ]
        )

    # =================================================
    # 🔥 SCIENCE / RENDERER
    # =====================================================

    math_words = [

        "график",
        "уравнение",
        "реши",
        "sin(",
        "cos(",
        "tan(",
        "y=",
        "формула",
        "функция",
        "парабола"
    ]

    if contains_any(
        t,
        math_words
    ):

        return build_signal_response(

            primary_intent="science",

            confidence=0.9,

            source="local_science",

            renderer=True,

            execution=True,

            explanation=True,

            capability_hints=[

                "science",
                "renderer_space",
                "math",
                "formula_rendering"
            ]
        )

    # =================================================
    # 🔥 EXPLICIT IMAGE GENERATION
    # =====================================================

    strong_generate_words = [

        "сгенерируй изображение",
        "создай изображение",
        "нарисуй картинку",
        "создай картинку",
        "generate image"
    ]

    if contains_any(
        t,
        strong_generate_words
    ):

        return build_signal_response(

            primary_intent="generate_image",

            confidence=0.92,

            source="local_generate",

            visual=True,

            execution=True,

            capability_hints=[

                "image_generation"
            ]
        )

    # =================================================
    # 🔥 IMAGE EDIT
    # =====================================================

    edit_words = [

        "измени",
        "добавь",
        "убери",
        "замени",
        "сделай ярче",
        "сделай темнее"
    ]

    if contains_any(
        t,
        edit_words
    ):

        if state.get(
            "image_context"
        ) or active_flow:

            return build_signal_response(

                primary_intent="edit_image",

                confidence=0.88,

                source="local_edit",

                continuation=True,

                visual=True,

                capability_hints=[

                    "image_edit",
                    "continuation"
                ]
            )

    # =================================================
    # 🔥 IMAGE ANALYSIS
    # =====================================================

    analyze_words = [

        "что на картинке",
        "что изображено",
        "что это",
        "опиши изображение",
        "что видишь"
    ]

    if contains_any(
        t,
        analyze_words
    ):

        if (

            state.get(
                "image_context"
            )

            or active_visual_scene
        ):

            return build_signal_response(

                primary_intent="analyze_image",

                confidence=0.9,

                source="local_analyze",

                visual=True,

                explanation=True,

                capability_hints=[

                    "image_analysis",
                    "visual_guidance"
                ]
            )

    # =================================================
    # 🔥 WEB
    # =====================================================

    web_words = [

        "погода",
        "новости",
        "курс валют",
        "маршрут",
        "карта",
        "где находится",
        "что происходит"
    ]

    if contains_any(
        t,
        web_words
    ):

        return build_signal_response(

            primary_intent="web",

            confidence=0.88,

            source="local_web",

            web=True,

            explanation=True,

            capability_hints=[

                "web",
                "guidance"
            ]
        )

    # =================================================
    # 🔥 VISUAL EXPLORATION
    # =====================================================

    exploration_words = [

        "атмосфера",
        "идея",
        "референс",
        "пример",
        "концепт",
        "вариант",
        "примерно",
        "в таком стиле"
    ]

    if contains_any(
        t,
        exploration_words
    ):

        return build_signal_response(

            primary_intent="exploration",

            confidence=0.76,

            source="local_exploration",

            visual=True,

            exploration=True,

            explanation=True,

            capability_hints=[

                "visual_guidance",
                "renderer_space",
                "conversation"
            ]
        )

    return None


# =====================================================
# 🧠 SAFE AI INTENT
# =====================================================

async def detect_intent_ai(
    text: str,
    state: dict = None
):

    state = state or {}

    t = (
        text or ""
    ).strip()

    # =================================================
    # 🔥 LOCAL FIRST
    # =====================================================

    local = detect_intent_local(
        t,
        state
    )

    if local:
        return local

    # =================================================
    # 🔥 SHORT INPUT PROTECTION
    # =====================================================

    if len(t) <= 15:

        active_flow = state.get(
            "active_flow"
        )

        if active_flow:

            return build_signal_response(

                primary_intent="continuation",

                confidence=0.66,

                source="short_continuation",

                continuation=True,

                capability_hints=[

                    "continuation"
                ]
            )

        return build_signal_response(

            primary_intent="text",

            confidence=0.5,

            source="short_safe",

            capability_hints=[

                "conversation"
            ]
        )

    # =================================================
    # 🔥 AI FALLBACK
    # =====================================================

    def run():

        try:

            prompt = f"""
Ты — multimodal signal analyzer для April.

ВАЖНО:
НЕ выбирай одну capability.
НЕ принимай execution decisions.

Твоя задача:
определить:
- primary intent
- renderer needs
- visual signals
- continuation
- explanation
- execution pressure
- exploration mode

Главные правила:

1. continuation важнее trigger words
2. renderer важнее heavy generation
3. exploration != generate_image
4. visual != image_generation
5. explanation может существовать
   вместе с render/science

Верни JSON.

Формат:

{{
  "primary_intent": "...",
  "renderer": true/false,
  "visual": true/false,
  "continuation": true/false,
  "explanation": true/false,
  "execution": true/false,
  "exploration": true/false
}}

Текст:
{text}
"""

            res = client.chat.completions.create(

                model="gpt-4o-mini",

                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],

                temperature=0,

                max_tokens=120
            )

            raw = (
                res.choices[0]
                .message.content
                .strip()
            )

            lowered = raw.lower()

            primary = "text"

            if "science" in lowered:
                primary = "science"

            elif "generate_image" in lowered:
                primary = "generate_image"

            elif "edit_image" in lowered:
                primary = "edit_image"

            elif "web" in lowered:
                primary = "web"

            elif "exploration" in lowered:
                primary = "exploration"

            return build_signal_response(

                primary_intent=primary,

                confidence=0.72,

                source="openai",

                renderer=(
                    '"renderer": true'
                    in lowered
                ),

                visual=(
                    '"visual": true'
                    in lowered
                ),

                continuation=(
                    '"continuation": true'
                    in lowered
                ),

                explanation=(
                    '"explanation": true'
                    in lowered
                ),

                execution=(
                    '"execution": true'
                    in lowered
                ),

                exploration=(
                    '"exploration": true'
                    in lowered
                ),

                capability_hints=[

                    primary,

                    "renderer_space",

                    "conversation"
                ]
            )

        except Exception as e:

            print(
                "🔥 INTENT AI ERROR:",
                e
            )

            return build_signal_response(

                primary_intent="text",

                confidence=0.4,

                source="fallback_error",

                capability_hints=[

                    "conversation"
                ]
            )

    return await asyncio.to_thread(run)
