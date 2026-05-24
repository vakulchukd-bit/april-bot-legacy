print("🔥 MAIN IMAGE SYSTEM WORKING")

from blocks.gemini_vision import (
    analyze_image_gemini
)

# =====================================================
# 🧠 APRIL IMAGE SYSTEM
# =====================================================

"""
APRIL IMAGE SYSTEM — WEB-FIRST STABILIZED

Главная идея:

Image system больше НЕ:
- Telegram image analyzer;
- isolated OCR layer;
- raw image interpreter;
- detached visual pipeline.

Image system теперь:
- visual continuity system;
- scene-aware analyzer;
- web-space visual bridge;
- semantic visual memory layer.

Visual authority:
принадлежит April Web Space.
"""

# =================================================
# 🔥 VISUAL HELPERS
# =====================================================

def normalize_visual_text(
    text
):

    return str(
        text or ""
    ).lower().strip()


# =================================================
# 🔥 VISUAL OBJECT EXTRACTION
# =====================================================

def extract_visual_objects(
    text
):

    lower = normalize_visual_text(
        text
    )

    detected = []

    object_map = {

        "кубик": [
            "кубик",
            "rubik",
            "cube"
        ],

        "машина": [
            "машина",
            "car",
            "vehicle",
            "автомобиль"
        ],

        "рука": [
            "рука",
            "hand",
            "finger",
            "палец"
        ],

        "бургер": [
            "burger",
            "бургер"
        ],

        "креветки": [
            "shrimp",
            "кревет"
        ],

        "бокал": [
            "glass",
            "cocktail",
            "бокал"
        ],

        "меню": [
            "menu",
            "меню"
        ],

        "чек": [
            "receipt",
            "чек"
        ],

        "улица": [
            "street",
            "road",
            "улица"
        ]
    }

    for object_name, triggers in object_map.items():

        if any(
            trigger in lower
            for trigger in triggers
        ):

            detected.append(
                object_name
            )

    return list(
        set(detected)
    )


# =================================================
# 🔥 VISUAL COLOR EXTRACTION
# =====================================================

def extract_visual_colors(
    text
):

    lower = normalize_visual_text(
        text
    )

    colors = []

    color_words = [

        "красный",
        "red",

        "синий",
        "blue",

        "зелёный",
        "green",

        "желтый",
        "yellow",

        "белый",
        "white",

        "оранжевый",
        "orange",

        "фиолетовый",
        "purple",

        "черный",
        "black"
    ]

    for color in color_words:

        if color in lower:

            colors.append(
                color
            )

    return list(
        set(colors)
    )


# =================================================
# 🔥 VISUAL ATMOSPHERE
# =====================================================

def detect_visual_atmosphere(
    text
):

    lower = normalize_visual_text(
        text
    )

    if any(

        x in lower

        for x in [

            "уют",
            "теплый",
            "лампа",
            "спокойный",
            "мягкий свет"
        ]
    ):

        return "calm_cozy"

    if any(

        x in lower

        for x in [

            "неон",
            "cyberpunk",
            "футурист",
            "фиолетовый свет"
        ]
    ):

        return "futuristic"

    if any(

        x in lower

        for x in [

            "минимализм",
            "minimal",
            "чисто",
            "аккуратно"
        ]
    ):

        return "minimal"

    return "neutral"


# =================================================
# 🔥 SCENE TYPE DETECTION
# =====================================================

def detect_scene_type(
    lower
):

    if any(
        x in lower
        for x in [
            "меню",
            "menu",
            "dish",
            "burger",
            "еда"
        ]
    ):

        return "restaurant_menu"

    if any(
        x in lower
        for x in [
            "чек",
            "receipt",
            "price"
        ]
    ):

        return "receipt"

    if any(
        x in lower
        for x in [
            "улица",
            "street",
            "road",
            "building"
        ]
    ):

        return "street"

    if any(
        x in lower
        for x in [
            "машина",
            "car",
            "vehicle"
        ]
    ):

        return "car_scene"

    if any(
        x in lower
        for x in [
            "кубик",
            "rubik",
            "cube"
        ]
    ):

        return "object_focus"

    return "general_scene"


# =================================================
# 🔥 VISUAL SCENE BUILDER
# =====================================================

def build_visual_scene(
    analysis_text: str
):

    text = str(
        analysis_text or ""
    ).strip()

    lower = text.lower()

    print(
        "🧠 BUILD VISUAL SCENE START"
    )

    # =================================================
    # 🔥 CORE SEMANTICS
    # =====================================================

    scene_type = detect_scene_type(
        lower
    )

    objects = extract_visual_objects(
        text
    )

    colors = extract_visual_colors(
        text
    )

    atmosphere = detect_visual_atmosphere(
        text
    )

    summary = text[:500]

    # =================================================
    # 🔥 CONTINUITY WEIGHT
    # =====================================================

    continuity_weight = 0.5

    if len(objects) >= 1:

        continuity_weight += 0.2

    if atmosphere != "neutral":

        continuity_weight += 0.15

    if len(colors) >= 1:

        continuity_weight += 0.1

    continuity_weight = min(
        continuity_weight,
        1.0
    )

    # =================================================
    # 🔥 LOGGING
    # =====================================================

    print(
        f"🧠 SCENE TYPE: {scene_type}"
    )

    print(
        f"🧠 OBJECTS: {objects}"
    )

    print(
        f"🧠 COLORS: {colors}"
    )

    print(
        f"🧠 ATMOSPHERE: {atmosphere}"
    )

    print(
        f"🧠 CONTINUITY: {continuity_weight}"
    )

    # =================================================
    # 🔥 RESULT
    # =====================================================

    return {

        "scene_type": scene_type,

        "summary": summary,

        "objects": objects,

        "colors": colors,

        "atmosphere": atmosphere,

        "continuity_weight":
            continuity_weight,

        "web_space_ready": True,

        "renderer_compatible": True,

        "raw_analysis": text
    }


# =================================================
# 🔥 VISUAL MEMORY HISTORY
# =====================================================

def update_visual_history(
    state,
    visual_scene
):

    history = state.get(
        "visual_scene_history",
        []
    )

    history.append(
        visual_scene
    )

    if len(history) > 7:

        history = history[-7:]

    state[
        "visual_scene_history"
    ] = history

    return history


# =================================================
# 🔥 MAIN ANALYZE IMAGE
# =====================================================

async def analyze_image(
    path: str,
    state=None
) -> str:

    try:

        print(
            "🧠 ANALYZE IMAGE START"
        )

        print(
            f"🧠 IMAGE PATH: {path}"
        )

        # =================================================
        # 🔥 CACHE
        # =====================================================

        if state:

            cached = state.get(
                "image_analysis"
            )

            cached_path = state.get(
                "image_analysis_path"
            )

            active_visual_scene = state.get(
                "active_visual_scene"
            )

            if (

                cached
                and cached_path == path

            ):

                print(
                    "🧠 USING IMAGE CACHE"
                )

                if active_visual_scene:

                    print(
                        "🧠 VISUAL SCENE RESTORED"
                    )

                return cached

        # =================================================
        # 🔥 GEMINI ANALYSIS
        # =====================================================

        print(
            "🧠 GEMINI ANALYSIS START"
        )

        result = await analyze_image_gemini(
            path
        )

        print(
            "🧠 GEMINI ANALYSIS COMPLETE"
        )

        # =================================================
        # 🔥 EMPTY SAFETY
        # =====================================================

        if not result:

            return (
                "⚠️ Не удалось "
                "проанализировать изображение."
            )

        # =================================================
        # 🔥 BUILD VISUAL SCENE
        # =====================================================

        visual_scene = build_visual_scene(
            result
        )

        print(
            "🧠 VISUAL SCENE CREATED"
        )

        # =================================================
        # 🔥 SAVE STATE
        # =====================================================

        if state is not None:

            state["image_analysis"] = (
                result
            )

            state["image_analysis_path"] = (
                path
            )

            state["active_visual_scene"] = (
                visual_scene
            )

            update_visual_history(
                state,
                visual_scene
            )

            state[
                "last_visual_analysis"
            ] = {

                "summary":
                    visual_scene.get(
                        "summary"
                    ),

                "scene_type":
                    visual_scene.get(
                        "scene_type"
                    ),

                "objects":
                    visual_scene.get(
                        "objects"
                    ),

                "continuity_weight":
                    visual_scene.get(
                        "continuity_weight"
                    )
            }

            print(
                "🧠 VISUAL STATE SAVED"
            )

        # =================================================
        # 🔥 COMPLETE
        # =====================================================

        print(
            "🧠 ANALYZE IMAGE COMPLETE"
        )

        return result

    except Exception as e:

        print(
            f"🔥 IMAGE SYSTEM ERROR: {str(e)}"
        )

        return (
            "⚠️ Ошибка анализа изображения."
        )
