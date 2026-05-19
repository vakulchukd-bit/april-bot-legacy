print("🔥 MAIN IMAGE SYSTEM WORKING")

import os

from blocks.gemini_vision import (
    analyze_image_gemini
)


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

        # =================================================
        # 🧠 SAVE CACHE
        # =================================================

        if state is not None:

            state["image_analysis"] = result

            state["image_analysis_path"] = path

        return result

    except Exception as e:

        return (
            f"Ошибка анализа изображения: "
            f"{str(e)}"
        )
