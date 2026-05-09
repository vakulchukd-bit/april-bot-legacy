# blocks/context_system.py

def build_context_text(
    user_id,
    text,
    state
):

    """
    🧠 SEMANTIC CONTEXT SYSTEM

    Не просто хранит диалог,
    а удерживает trajectory,
    intent,
    expectations,
    visual direction
    и execution pressure.
    """

    text = (text or "").strip()

    t = text.lower()

    # =====================================================
    # 🔥 SYSTEM BASE
    # =====================================================

    base = """

Ты — April.

Главная задача:
понимать намерение пользователя,
удерживать trajectory,
не уходить в болтологию,
вести пользователя к результату.

Приоритет:
1. результат
2. понимание
3. guidance
4. краткость
5. естественность

Если пользователь ожидает:
- визуализацию → предлагай визуальный путь
- пример → давай пример
- действие → выполняй
- guidance → направляй

Не растягивай ответы без необходимости.
Не повторяйся.
Не теряй trajectory.
"""

    # =====================================================
    # 🔥 DIALOG
    # =====================================================

    dialog = state.get(
        "dialog",
        []
    )

    # =====================================================
    # 🔥 MEMORY SUMMARY
    # =====================================================

    summary = state.get(
        "memory_summary",
        ""
    )

    # =====================================================
    # 🔥 ACTIVE FLOW
    # =====================================================

    active_flow = state.get(
        "active_flow"
    )

    # =====================================================
    # 🔥 IMAGE CONTEXT
    # =====================================================

    image_context = state.get(
        "image_context"
    )

    # =====================================================
    # 🔥 LAST MATH
    # =====================================================

    last_math = state.get(
        "last_math"
    )

    # =====================================================
    # 🔥 RELEVANCE FILTERING
    # =====================================================

    relevant_dialog = []

    keywords = []

    for word in t.split():

        if len(word) >= 4:
            keywords.append(word)

    # =====================================================
    # 🔥 LAST IMPORTANT MESSAGES
    # =====================================================

    for msg in reversed(dialog[-14:]):

        content = (
            msg.get("content")
            or ""
        ).strip()

        role = msg.get(
            "role",
            "user"
        )

        if not content:
            continue

        priority = 0

        # =================================================
        # 🔥 KEYWORD MATCH
        # =================================================

        lowered = content.lower()

        for kw in keywords:

            if kw in lowered:
                priority += 2

        # =================================================
        # 🔥 EXECUTION SIGNALS
        # =================================================

        execution_words = [
            "создай",
            "сделай",
            "нарисуй",
            "сгенерируй",
            "покажи"
        ]

        if any(
            w in lowered
            for w in execution_words
        ):
            priority += 2

        # =================================================
        # 🔥 VISUAL SIGNALS
        # =================================================

        visual_words = [
            "пример",
            "картинка",
            "визуально",
            "схема",
            "референс"
        ]

        if any(
            w in lowered
            for w in visual_words
        ):
            priority += 2

        # =================================================
        # 🔥 RECENT PRIORITY
        # =================================================

        if msg in dialog[-4:]:
            priority += 2

        # =================================================
        # 🔥 FLOW PRIORITY
        # =================================================

        if active_flow:

            flow_type = active_flow.get(
                "type"
            )

            if flow_type:

                if flow_type in lowered:
                    priority += 3

        # =================================================
        # 🔥 STORE
        # =================================================

        if priority >= 2:

            relevant_dialog.append(
                f"{role}: {content[:300]}"
            )

    # =====================================================
    # 🔥 DIALOG COMPRESSION
    # =====================================================

    relevant_dialog = list(
        reversed(relevant_dialog[-8:])
    )

    compressed_dialog = "\n".join(
        relevant_dialog
    )

    # =====================================================
    # 🔥 TRAJECTORY
    # =====================================================

    trajectory = ""

    if active_flow:

        flow_type = active_flow.get(
            "type"
        )

        trajectory += (
            f"\nАктивный trajectory: "
            f"{flow_type}"
        )

        original = active_flow.get(
            "original"
        )

        if original:

            trajectory += (
                f"\nИсходная задача: "
                f"{original[:300]}"
            )

    # =====================================================
    # 🔥 SUMMARY
    # =====================================================

    summary_block = ""

    if summary:

        summary_block = (
            "\nСжатая память:\n"
            + summary[-400:]
        )

    # =====================================================
    # 🔥 IMAGE MEMORY
    # =====================================================

    image_block = ""

    if (
        image_context
        and isinstance(
            image_context,
            dict
        )
    ):

        hint = (
            image_context.get("hint")
            or image_context.get("prompt")
        )

        if hint:

            image_block = (
                "\nПоследний visual context:\n"
                + hint[:200]
            )

    # =====================================================
    # 🔥 MATH MEMORY
    # =====================================================

    math_block = ""

    if last_math:

        expr = last_math.get(
            "expr"
        )

        if expr:

            math_block = (
                "\nПоследняя math задача:\n"
                + expr[:120]
            )

    # =====================================================
    # 🔥 CURRENT USER REQUEST
    # =====================================================

    current_request = f"""

Текущий запрос пользователя:
{text}

Важно:
если пользователь продолжает тему —
НЕ теряй trajectory.

Если пользователь ожидает:
- пример → покажи пример
- визуал → предложи visual path
- результат → не затягивай диалог
- guidance → направляй

Не уходи в длинную болтологию.
"""

    # =====================================================
    # 🔥 FINAL BUILD
    # =====================================================

    full = f"""

{base}

{trajectory}

{summary_block}

{image_block}

{math_block}

Релевантный диалог:
{compressed_dialog}

{current_request}

"""

    return full


# =====================================================
# 🔥 SMART MEMORY SUMMARY
# =====================================================

def update_memory_summary(
    state,
    user_text,
    bot_reply
):

    """
    Храним trajectory,
    а не мусор диалога.
    """

    old = state.get(
        "memory_summary",
        ""
    )

    user_text = (
        user_text or ""
    ).strip()

    bot_reply = (
        bot_reply or ""
    ).strip()

    # =====================================================
    # 🔥 CLEANUP
    # =====================================================

    user_text = user_text[:140]

    bot_reply = bot_reply[:180]

    # =====================================================
    # 🔥 LOW VALUE FILTER
    # =====================================================

    ignored = [
        "ок",
        "ага",
        "да",
        "понял",
        "хорошо"
    ]

    if (
        user_text.lower() in ignored
        or len(user_text) <= 2
    ):

        return

    # =====================================================
    # 🔥 BUILD CHUNK
    # =====================================================

    chunk = (
        f"{user_text} → "
        f"{bot_reply}"
    )

    # =====================================================
    # 🔥 DUPLICATE AVOIDANCE
    # =====================================================

    if chunk in old:
        return

    combined = (
        old
        + " | "
        + chunk
    ).strip()

    # =====================================================
    # 🔥 MEMORY LIMIT
    # =====================================================

    if len(combined) > 1200:

        combined = combined[-1200:]

    state["memory_summary"] = combined
