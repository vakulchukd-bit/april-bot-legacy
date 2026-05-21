print("🔥 MAIN IMAGE SYSTEM WORKING")

import os

from blocks.gemini_vision import (
    analyze_image_gemini
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

    # =================================================
    # 🔥 OBJECT DETECTION
    # =================================================

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

    # =================================================
    # 🔥 SUMMARY
    # =================================================

    summary = text[:400]

    # =================================================
    # 🔥 RESULT
    # =================================================

    return {

        "scene_type": scene_type,

        "summary": summary,

        "objects": list(
            set(objects)
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

        # =================================================
        # 🔥 START LOG
        # =================================================

        print("🧠 ANALYZE IMAGE START")
        print("🧠 IMAGE PATH:", path)
        print(
            "🧠 STATE EXISTS:",
            state is not None
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

            print(
                "🧠 CACHED EXISTS:",
                cached is not None
            )

            print(
                "🧠 CACHED PATH:",
                cached_path
            )

            # =============================================
            # 🔥 ACTIVE VISUAL SCENE
            # =============================================

            active_visual_scene = state.get(
                "active_visual_scene"
            )

            print(
                "🧠 ACTIVE VISUAL SCENE EXISTS:",
                active_visual_scene is not None
            )

            # =============================================
            # 🔥 CACHE RESTORE
            # =============================================

            if cached and cached_path == path:

                print(
                    "🧠 CACHE HIT"
                )

                print(
                    "🧠 USING CACHED IMAGE ANALYSIS"
                )

                if active_visual_scene:

                    print(
                        "🧠 VISUAL SCENE RESTORED"
                    )

                    state[
                        "active_visual_scene"
                    ] = active_visual_scene

                print(
                    "🧠 ANALYZE IMAGE COMPLETE (CACHE)"
                )

                return cached

            else:

                print(
                    "🧠 CACHE MISS"
                )

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
            "🧠 ANALYSIS LENGTH:",
            len(str(result))
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
            "🧠 SCENE TYPE:",
            visual_scene.get(
                "scene_type"
            )
        )

        print(
            "🧠 SCENE OBJECTS:",
            visual_scene.get(
                "objects"
            )
        )

        # =================================================
        # 🧠 SAVE CACHE
        # =================================================

        if state is not None:

            # ==========================================
            # 🔥 RAW ANALYSIS
            # ==========================================

            state["image_analysis"] = result

            state["image_analysis_path"] = path

            print(
                "🧠 IMAGE CACHE SAVED"
            )

            # ==========================================
            # 🔥 ACTIVE VISUAL SCENE
            # ==========================================

            state["active_visual_scene"] = (
                visual_scene
            )

            print(
                "🧠 ACTIVE VISUAL SCENE SAVED"
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

            print(
                "🧠 VISUAL SCENE HISTORY SIZE:",
                len(history)
            )

        else:

            print(
                "⚠️ STATE IS NONE"
            )

        # =================================================
        # 🔥 COMPLETE
        # =================================================

        print(
            "🧠 ANALYZE IMAGE COMPLETE"
        )

        # =================================================
        # 🔥 RETURN RESULT
        # =================================================

        return result

    except Exception as e:

        print(
            "🔥 IMAGE SYSTEM ERROR:",
            str(e)
        )

        return (
            f"Ошибка анализа изображения: "
            f"{str(e)}"
        )
