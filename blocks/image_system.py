print("🔥 MAIN IMAGE SYSTEM WORKING")

import os

from blocks.gemini_vision import (
    analyze_image_gemini
)
def build_visual_scene(
    analysis_text: str
):

    text = str(
        analysis_text or ""
    ).strip()

    lower = text.lower()

    scene_type = "unknown"

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

        scene_type = "restaurant_menu"

    elif any(
        x in lower
        for x in [
            "чек",
            "receipt",
            "price"
        ]
    ):

        scene_type = "receipt"

    elif any(
        x in lower
        for x in [
            "улица",
            "street",
            "road",
            "building"
        ]
    ):

        scene_type = "street"

    objects = []

    object_words = [

        "burger",
        "shrimp",
        "glass",
        "cocktail",
        "чек",
        "кревет",
        "бургер",
        "бокал"
    ]

    for word in object_words:

        if word in lower:

            objects.append(word)

    summary = text[:400]

    return {

        "scene_type": scene_type,

        "summary": summary,

        "objects": list(
            set(objects)
        ),

        "raw_analysis": text
    }


async def analyze_image(
    path: str,
    state=None
) -> str:

    try:

        # =================================================
        # 🧠 CACHE
        # =================================================

        if state:

            cached = state.get(
                "image_analysis"
            )

            cached_path = state.get(
                "image_analysis_path"
            )

            if cached and cached_path == path:

                print(
                    "🧠 USING CACHED IMAGE ANALYSIS"
                )

                return cached

        # =================================================
        # 🔥 GEMINI ANALYSIS
        # =================================================

        result = await analyze_image_gemini(
            path
        )
        visual_scene = build_visual_scene(
            result
        )

        # =================================================
        # 🧠 SAVE CACHE
        # =================================================

        if state is not None:

            state["image_analysis"] = result

            state["image_analysis_path"] = path

            # ==========================================
            # 🔥 ACTIVE VISUAL SCENE
            # ==========================================

            state["active_visual_scene"] = (
                visual_scene
            )

            # ==========================================
            # 🔥 VISUAL SCENE HISTORY
            # ==========================================

            history = state.get(
                "visual_scene_history",
                []
            )

            history.append(
                visual_scene
            )

            if len(history) > 5:

                history = history[-5:]

            state[
                "visual_scene_history"
            ] = history
