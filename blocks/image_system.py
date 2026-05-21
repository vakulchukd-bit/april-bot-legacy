print("🔥 MAIN IMAGE SYSTEM WORKING")

import os
import re

from blocks.gemini_vision import (
    analyze_image_gemini
)


# =================================================
# 🔥 VISUAL HELPERS
# =================================================

def normalize_visual_text(
    text
):

    return str(
        text or ""
    ).lower().strip()


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
# 🔥 VISUAL SCENE BUILDER
# =================================================

def build_visual_scene(
    analysis_text: str
):

    text = str(
        analysis_text or ""
    ).strip()

    lower = text.lower()

    scene_type = "unknown"

    print(
        "🧠 BUILD VISUAL SCENE START"
    )

    # =================================================
    # 🔥 SCENE TYPE DETECTION
    # =================================================

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

    elif any(
        x in lower
        for x in [
            "машина",
            "car",
            "vehicle"
        ]
    ):

        scene_type = "car_scene"

    elif any(
        x in lower
        for x in [
            "кубик",
            "rubik",
            "cube"
        ]
    ):

        scene_type = "object_focus"

    # =================================================
    # 🔥 OBJECT DETECTION
    # =================================================

    objects = extract_visual_objects(
        text
    )

    # =================================================
    # 🔥 COLORS
    # =================================================

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
        "orange"
    ]

    for color in color_words:

        if color in lower:

            colors.append(
                color
            )

    # =================================================
    # 🔥 SUMMARY
    # =================================================

    summary = text[:400]

    # =================================================
    # 🔥 LOGGING
    # =================================================

    print(
        f"🧠 SCENE TYPE DETECTED: {scene_type}"
    )

    print(
        f"🧠 OBJECTS DETECTED: {objects}"
    )

    print(
        f"🧠 COLORS DETECTED: {colors}"
    )

    print(
        f"🧠 SUMMARY LENGTH: {len(summary)}"
    )

    # =================================================
    # 🔥 RESULT
    # =================================================

    return {

        "scene_type": scene_type,

        "summary": summary,

        "objects": objects,

        "colors": list(
            set(colors)
        ),

        "raw_analysis": text
    }


# =================================================
# 🔥 MAIN ANALYZE IMAGE
# =================================================

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
        # 🧠 CACHE
        # =================================================

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

            if cached and cached_path == path:

                print(
                    "🧠 USING CACHED IMAGE ANALYSIS"
                )

                if active_visual_scene:

                    print(
                        "🧠 VISUAL SCENE RESTORED"
                    )

                    print(
                        f"🧠 RESTORED OBJECTS: "
                        f"{active_visual_scene.get('objects')}"
                    )

                    state[
                        "active_visual_scene"
                    ] = active_visual_scene

                return cached

        # =================================================
        # 🔥 GEMINI ANALYSIS
        # =================================================

        print(
            "🧠 GEMINI IMAGE ANALYSIS START"
        )

        result = await analyze_image_gemini(
            path
        )

        print(
            "🧠 GEMINI IMAGE ANALYSIS COMPLETE"
        )

        print(
            f"🧠 ANALYSIS LENGTH: {len(result)}"
        )

        # =================================================
        # 🔥 BUILD VISUAL SCENE
        # =================================================

        visual_scene = build_visual_scene(
            result
        )

        print(
            "🧠 VISUAL SCENE CREATED"
        )

        print(
            f"🧠 FINAL SCENE TYPE: "
            f"{visual_scene.get('scene_type')}"
        )

        print(
            f"🧠 FINAL OBJECTS: "
            f"{visual_scene.get('objects')}"
        )

        print(
            f"🧠 FINAL COLORS: "
            f"{visual_scene.get('colors')}"
        )

        # =================================================
        # 🧠 SAVE CACHE
        # =================================================

        if state is not None:

            state["image_analysis"] = result

            state["image_analysis_path"] = path

            state["active_visual_scene"] = (
                visual_scene
            )

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

            print(
                "🧠 IMAGE CACHE SAVED"
            )

            print(
                "🧠 ACTIVE VISUAL SCENE SAVED"
            )

            print(
                f"🧠 VISUAL SCENE HISTORY SIZE: "
                f"{len(history)}"
            )

        # =================================================
        # 🔥 COMPLETE
        # =================================================

        print(
            "🧠 ANALYZE IMAGE COMPLETE"
        )

        return result

    except Exception as e:

        print(
            f"🔥 IMAGE SYSTEM ERROR: {str(e)}"
        )

        return (
            f"Ошибка анализа изображения: "
            f"{str(e)}"
        )
