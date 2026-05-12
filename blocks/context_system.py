# blocks/context_system.py

# =====================================================
# 🧠 APRIL DEEPHUB CONTEXT SYSTEM
# =====================================================

"""
DeepHub Context Architecture

Главная идея:
context больше НЕ строится
через тупое накопление dialog/history.

Теперь главный источник:
scene_state.

Это:
- уменьшает шум;
- уменьшает повторный анализ;
- удерживает trajectory;
- стабилизирует continuity;
- снижает fragmentation;
- уменьшает cognitive reload.
"""


# =====================================================
# 🔥 TOPIC SHIFT
# =====================================================

def detect_topic_shift(
    text,
    active_flow,
    scene_state
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
            "одежда",
            "фото",
            "кофе",
            "дизайн",
            "ресторан"
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

            "python",
            "сервер",
            "код",
            "ошибка",
            "уравнение"
        ]

        if any(
            w in text
            for w in unrelated
        ):

            return True

    return False


# =====================================================
# 🔥 PASSIVE MEMORY
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

    if len(memory) > 10:

        memory = memory[-10:]

    state["passive_memory"] = memory


# =====================================================
# 🔥 SCENE BLOCK
# =====================================================

def build_scene_block(
    scene_state
):

    if not scene_state:
        return ""

    lines = []

    trajectory = scene_state.get(
        "trajectory"
    )

    goal = scene_state.get(
        "goal"
    )

    user_intent = scene_state.get(
        "user_intent"
    )

    confirmed_direction = scene_state.get(
        "confirmed_direction"
    )

    visual_mode = scene_state.get(
        "visual_mode"
    )

    execution_mode = scene_state.get(
        "execution_mode"
    )

    if trajectory:

        lines.append(
            f"Trajectory: {trajectory}"
        )

    if goal:

        lines.append(
            f"Goal: {goal[:300]}"
        )

    if user_intent:

        lines.append(
            f"Intent: {user_intent}"
        )

    if confirmed_direction:

        lines.append(
            f"Direction: {confirmed_direction}"
        )

    if visual_mode:

        lines.append(
            "Visual continuity active"
        )

    if execution_mode:

        lines.append(
            "Execution mode active"
        )

    if not lines:
        return ""

    return (
        "\nSCENE STATE:\n"
        + "\n".join(lines)
    )


# =====================================================
# 🔥 RELEVANT DIALOG
# =====================================================

def build_relevant_dialog(
    dialog,
    text,
    active_flow
):

    text = (
        text or ""
    ).lower()

    keywords = []

    for word in text.split():

        if len(word) >= 4:

            keywords.append(word)

    relevant = []

    # =================================================
    # 🔥 LAST IMPORTANT
    # =================================================

    for msg in reversed(dialog[-8:]):

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

        lowered = content.lower()

        priority = 0

        # =================================================
        # 🔥 RECENT
        # =================================================

        if msg in dialog[-3:]:

            priority += 3

        # =================================================
        # 🔥 KEYWORDS
        # =================================================

        for kw in keywords:

            if kw in lowered:

                priority += 2

        # =================================================
        # 🔥 FLOW MATCH
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

            relevant.append(
                f"{role}: {content[:220]}"
            )

    relevant = list(
        reversed(relevant[-5:])
    )

    return "\n".join(relevant)


# =====================================================
# 🔥 CONTEXT BUILD
# =====================================================

def build_context_text(
    user_id,
    text,
    state
):

    text = (
        text or ""
    ).strip()

    # =================================================
    # 🔥 CORE
    # =================================================

    base = """

Ты — April.

Главное:
- удерживать trajectory;
- понимать намерение;
- помогать;
- сохранять continuity;
- избегать болтологии;
- двигаться к результату.

Не повторяйся.
Не анализируй одно и то же повторно.
Не ломай continuity сцены.
"""

    # =================================================
    # 🔥 STATE
    # =================================================

    dialog = state.get(
        "dialog",
        []
    )

    summary = state.get(
        "memory_summary",
        ""
    )

    active_flow = state.get(
        "active_flow"
    )

    passive_memory = state.get(
        "passive_memory",
        []
    )

    image_context = state.get(
        "image_context"
    )

    last_math = state.get(
        "last_math"
    )

    scene_state = state.get(
        "scene_state",
        {}
    )

    # =================================================
    # 🔥 TOPIC SHIFT
    # =================================================

    topic_shift = detect_topic_shift(

        text,

        active_flow,

        scene_state
    )

    if topic_shift:

        archive_completed_flow(

            state,

            active_flow
        )

        state["active_flow"] = None

        active_flow = None

    # =================================================
    # 🔥 SCENE
    # =================================================

    scene_block = build_scene_block(
        scene_state
    )

    # =================================================
    # 🔥 MEMORY SUMMARY
    # =================================================

    summary_block = ""

    if summary:

        summary_block = (
            "\nMemory summary:\n"
            + summary[-500:]
        )

    # =================================================
    # 🔥 PASSIVE MEMORY
    # =================================================

    passive_block = ""

    if passive_memory:

        compressed = "\n".join(
            passive_memory[-4:]
        )

        passive_block = (
            "\nArchived trajectories:\n"
            + compressed
        )

    # =================================================
    # 🔥 IMAGE CONTEXT
    # =================================================

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
                "\nVisual context:\n"
                + hint[:180]
            )

    # =================================================
    # 🔥 LAST MATH
    # =================================================

    math_block = ""

    if last_math:

        expr = last_math.get(
            "expr"
        )

        if expr:

            math_block = (
                "\nMath context:\n"
                + expr[:120]
            )

    # =================================================
    # 🔥 RELEVANT DIALOG
    # =================================================

    relevant_dialog = build_relevant_dialog(

        dialog,

        text,

        active_flow
    )

    # =================================================
    # 🔥 CURRENT REQUEST
    # =================================================

    current_request = f"""

Current user request:
{text}

Важно:
если trajectory продолжается —
сохраняй continuity.

Если trajectory завершён —
не тащи старую сцену.
"""

    # =================================================
    # 🔥 FINAL
    # =================================================

    full = f"""

{base}

{scene_block}

{summary_block}

{passive_block}

{image_block}

{math_block}

Relevant dialog:
{relevant_dialog}

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
    DeepHub memory philosophy:

    хранить trajectory,
    а не мусор history.
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

    # =================================================
    # 🔥 CLEANUP
    # =================================================

    user_text = user_text[:140]

    bot_reply = bot_reply[:180]

    # =================================================
    # 🔥 LOW VALUE
    # =================================================

    ignored = [

        "ок",
        "ага",
        "понял",
        "да",
        "хорошо"
    ]

    if (
        user_text.lower() in ignored
        or len(user_text) <= 2
    ):

        return

    # =================================================
    # 🔥 BUILD
    # =================================================

    chunk = (
        f"{user_text} → "
        f"{bot_reply}"
    )

    # =================================================
    # 🔥 DUPLICATES
    # =================================================

    if chunk in old:
        return

    combined = (
        old
        + " | "
        + chunk
    ).strip()

    # =================================================
    # 🔥 LIMIT
    # =================================================

    if len(combined) > 1200:

        combined = combined[-1200:]

    state["memory_summary"] = combined
