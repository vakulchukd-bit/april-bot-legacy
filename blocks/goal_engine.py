def detect_goal(
    text: str,
    state: dict,
    semantic: dict
):

    t = text.lower()

    active = state.get(
        "active_flow"
    )

    # =================================================
    # 🔥 ACTIVE FLOW FIRST
    # =================================================

    if active:

        flow_type = active.get(
            "type"
        )

        # =============================
        # IMAGE CONTINUATION
        # =============================

        if flow_type == "image":

            continuation_words = [
                "сделай",
                "добавь",
                "измени",
                "убери",
                "ярче",
                "темнее",
                "ещё",
                "дальше",
                "теперь"
            ]

            if any(w in t for w in continuation_words):

                return {
                    "goal": "continue_image",
                    "room": "image_edit",
                    "confidence": 0.9
                }

        # =============================
        # MATH CONTINUATION
        # =============================

        if flow_type == "math":

            continuation_words = [
                "построй",
                "покажи",
                "реши",
                "это",
                "дальше",
                "теперь"
            ]

            if any(w in t for w in continuation_words):

                return {
                    "goal": "continue_math",
                    "room": "science",
                    "confidence": 0.9
                }

    # =================================================
    # 🔥 FALLBACK TO SEMANTIC
    # =================================================

    return semantic
