# blocks/context_system.py

# =====================================================
# 🧠 TRAJECTORY MEMORY SYSTEM
# =====================================================

def detect_topic_shift(
    text,
    active_flow,
    state
):

    text = (text or "").lower()

    if not active_flow:
        return False

    flow_type = active_flow.get(
        "type"
    )

    if not flow_type:
        return False

    # =================================================
    # 🔥 MATH SHIFT
    # =================================================

    if flow_type == "math":

        unrelated = [
            "кафе",
            "дизайн",
            "сайт",
            "одежда",
            "фото",
            "кофе"
        ]

        if any(
            w in text
            for w in unrelated
        ):

            return True

    # =================================================
    # 🔥 IMAGE SHIFT
    # =================================================

    if flow_type == "image":

        unrelated = [
            "код",
            "python",
            "ошибка",
            "уравнение",
            "сервер"
        ]

        if any(
            w in text
            for w in unrelated
        ):

            return True

    return False


# =====================================================
# 🔥 PASSIVE MEMORY ARCHIVE
# =====================================================

def archive_completed_flow(
    state,
    active_flow
):

    if not active_flow:
        return

    memory = state.get(
        "passive_memory",
        []
    )

    flow_type = active_flow.get(
        "type",
        "unknown"
    )

    original = active_flow.get(
        "original",
        ""
    )

    compressed = (
        f"[{flow_type}] "
        f"{original[:120]}"
    )

    if compressed not in memory:

        memory.append(
            compressed
        )

    if len(memory) > 12:

        memory = memory[-12:]

    state["passive_memory"] = memory


# =====================================================
# 🔥 CONTEXT BUILD
# =====================================================

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
- визуализацию → предлагай visual path
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
    # 🔥 PASSIVE MEMORY
    # =====================================================

    passive_memory = state.get(
        "passive_memory",
        []
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
    # 🔥 TOPIC SHIFT DETECTION
    # =====================================================

    topic_shift = detect_topic_shift(
        text,
        active_flow,
        state
    )

    # =====================================================
    # 🔥 FLOW RELEASE
    # =====================================================

    if topic_shift:

        archive_completed_flow(
            state,
            active_flow
        )

        state["active_flow"] = None

        active_flow = None

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

        lowered = content.lower()

        # =================================================
        # 🔥 KEYWORD MATCH
        # =================================================

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

    else:

        trajectory += (
            "\nТекущий trajectory "
            "не зафиксирован."
        )

    # =====================================================
    # 🔥 SUMMARY
    # =====================================================

    summary_block = ""

    if summary:

        summary_block = (
            "\nСжатая память:\n"
            + summary[-500:]
        )

    # =====================================================
    # 🔥 PASSIVE MEMORY BLOCK
    # =====================================================

    passive_block = ""

    if passive_memory:

        compressed = "\n".join(
            passive_memory[-5:]
        )

        passive_block = (
            "\nАрхив trajectory:\n"
            + compressed
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

Если тема сменилась —
не тащи старый flow насильно.

Если пользователь ожидает:
- пример → покажи пример
- visual path → предложи visual guidance
- результат → не затягивай
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

{passive_block}

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

    if len(combined) > 1400:

        combined = combined[-1400:]

    state["memory_summary"] = combined
