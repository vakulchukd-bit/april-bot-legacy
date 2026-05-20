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

DeepHub direction:
- scene-first;
- continuity-heavy;
- low-noise orchestration;
- calm routing;
- rooms coordination;
- stable trajectory;
- minimal recursive reasoning.
"""

# =====================================================
# 🔥 CONSTANTS
# =====================================================

LOW_VALUE_MESSAGES = [

    "ок",
    "ага",
    "понял",
    "да",
    "хорошо",
    "ясно",
    "окей",
    "угу"
]

MATH_UNRELATED = [

    "кафе",
    "одежда",
    "фото",
    "кофе",
    "дизайн",
    "ресторан"
]

IMAGE_UNRELATED = [

    "python",
    "сервер",
    "код",
    "ошибка",
    "уравнение"
]

MIN_KEYWORD_LENGTH = 4

MAX_RELEVANT_MESSAGES = 5

MAX_DIALOG_SCAN = 8

MAX_PASSIVE_MEMORY = 10

MAX_SUMMARY_LENGTH = 1200

MAX_GOAL_LENGTH = 300

MAX_IMAGE_HINT = 180

MAX_MATH_EXPR = 120

MAX_USER_MEMORY = 140

MAX_BOT_MEMORY = 180

# =====================================================
# 🔥 HELPERS
# =====================================================

def normalize_text(
    text
):

    return (
        text or ""
    ).strip()


def normalize_lower(
    text
):

    return normalize_text(
        text
    ).lower()


def safe_slice(
    value,
    limit
):

    if not value:
        return ""

    return str(value)[:limit]


def contains_any(
    text,
    words
):

    return any(
        w in text
        for w in words
    )


# =====================================================
# 🔥 TOPIC SHIFT
# =====================================================

def detect_topic_shift(
    text,
    active_flow,
    scene_state
):

    """
    DeepHub philosophy:

    topic shift detection
    должен быть спокойным.

    Мы не пытаемся
    агрессивно перескакивать
    между trajectories.

    Мы проверяем:
    реально ли сцена сменилась.
    """

    text = normalize_lower(
        text
    )

    if not active_flow:
        return False

    flow_type = active_flow.get(
        "type"
    )

    if not flow_type:
        return False

    # =================================================
    # 🔥 SCENE PRIORITY
    # =================================================

    scene_trajectory = scene_state.get(
        "trajectory"
    )

    if scene_trajectory:

        if scene_trajectory in text:

            return False

    # =================================================
    # 🔥 MATH SHIFT
    # =================================================

    if flow_type == "math":

        if contains_any(
            text,
            MATH_UNRELATED
        ):

            return True

    # =================================================
    # 🔥 IMAGE SHIFT
    # =================================================

    if flow_type == "image":

        if contains_any(
            text,
            IMAGE_UNRELATED
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

    """
    DeepHub passive memory:

    сохраняем trajectory,
    а не мусор history.
    """

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

    trajectory = active_flow.get(
        "trajectory"
    )

    compressed = (

        f"[{flow_type}] "

        f"{safe_slice(original, 120)}"
    )

    if trajectory:

        compressed += (
            f" :: {trajectory}"
        )

    if compressed not in memory:

        memory.append(
            compressed
        )

    if len(memory) > MAX_PASSIVE_MEMORY:

        memory = memory[
            -MAX_PASSIVE_MEMORY:
        ]

    state[
        "passive_memory"
    ] = memory


# =====================================================
# 🔥 SCENE BLOCK
# =====================================================

def build_scene_block(
    scene_state
):

    """
    Scene-first architecture.

    Главный источник истины:
    scene_state.
    """

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

    active_room = scene_state.get(
        "active_room"
    )

    orchestration_mode = scene_state.get(
        "orchestration_mode"
    )

    continuity_mode = scene_state.get(
        "continuity_mode"
    )

    scene_priority = scene_state.get(
        "scene_priority"
    )

    # =================================================
    # 🔥 TRAJECTORY
    # =================================================

    if trajectory:

        lines.append(
            f"Trajectory: {trajectory}"
        )

    # =================================================
    # 🔥 GOAL
    # =================================================

    if goal:

        lines.append(
            f"Goal: "
            f"{safe_slice(goal, MAX_GOAL_LENGTH)}"
        )

    # =================================================
    # 🔥 INTENT
    # =================================================

    if user_intent:

        lines.append(
            f"Intent: {user_intent}"
        )

    # =================================================
    # 🔥 DIRECTION
    # =================================================

    if confirmed_direction:

        lines.append(
            f"Direction: "
            f"{confirmed_direction}"
        )

    # =================================================
    # 🔥 VISUAL
    # =================================================

    if visual_mode:

        lines.append(
            "Visual continuity active"
        )

    # =================================================
    # 🔥 EXECUTION
    # =================================================

    if execution_mode:

        lines.append(
            "Execution mode active"
        )

    # =================================================
    # 🔥 ROOM
    # =================================================

    if active_room:

        lines.append(
            f"Coordinator room: "
            f"{active_room}"
        )

    # =================================================
    # 🔥 ORCHESTRATION
    # =================================================

    if orchestration_mode:

        lines.append(
            f"Orchestration: "
            f"{orchestration_mode}"
        )

    # =================================================
    # 🔥 CONTINUITY
    # =================================================

    if continuity_mode:

        lines.append(
            f"Continuity: "
            f"{continuity_mode}"
        )

    # =================================================
    # 🔥 PRIORITY
    # =================================================

    if scene_priority:

        lines.append(
            f"Scene priority: "
            f"{scene_priority}"
        )

    # =================================================
    # 🔥 EMPTY
    # =================================================

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
    active_flow,
    scene_state=None
):

    """
    DeepHub philosophy:

    relevant_dialog —
    это support layer,
    а НЕ главный источник context.
    """

    text = normalize_lower(
        text
    )

    keywords = []

    for word in text.split():

        if len(word) >= MIN_KEYWORD_LENGTH:

            keywords.append(word)

    relevant = []

    trajectory = None

    if scene_state:

        trajectory = scene_state.get(
            "trajectory"
        )

    # =================================================
    # 🔥 LAST IMPORTANT
    # =================================================

    for msg in reversed(
        dialog[-MAX_DIALOG_SCAN:]
    ):

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
        # 🔥 FLOW
        # =================================================

        if active_flow:

            flow_type = active_flow.get(
                "type"
            )

            if (

                flow_type
                and flow_type in lowered
            ):

                priority += 3

        # =================================================
        # 🔥 TRAJECTORY
        # =================================================

        if trajectory:

            if trajectory.lower() in lowered:

                priority += 4

        # =================================================
        # 🔥 EXECUTION SIGNAL
        # =================================================

        if (

            "сделай" in lowered
            or "исправь" in lowered
            or "продолжай" in lowered
        ):

            priority += 2

        # =================================================
        # 🔥 STORE
        # =================================================

        if priority >= 2:

            relevant.append(

                f"{role}: "

                f"{safe_slice(content, 220)}"
            )

    relevant = list(

        reversed(
            relevant[
                -MAX_RELEVANT_MESSAGES:
            ]
        )
    )

    return "\n".join(relevant)


# =====================================================
# 🔥 CONTEXT LAYERS
# =====================================================

def build_base_context():

    return """

Ты — April.

Главное:
- удерживать trajectory;
- понимать намерение;
- помогать;
- сохранять continuity;
- избегать болтологии;
- двигаться к результату.

DeepHub principles:
- scene-first;
- continuity-heavy;
- low-noise;
- calm orchestration;
- no recursive overthinking;
- no repeated analysis;
- no trajectory fragmentation.

Rooms architecture:
- комнаты выполняют задачи;
- April координирует;
- trajectory важнее history;
- continuity важнее болтовни.

Не повторяйся.
Не анализируй одно и то же повторно.
Не ломай continuity сцены.
"""


def build_summary_block(
    summary
):

    if not summary:
        return ""

    return (

        "\nMemory summary:\n"

        + safe_slice(
            summary,
            500
        )
    )


def build_passive_memory_block(
    passive_memory
):

    if not passive_memory:
        return ""

    compressed = "\n".join(

        passive_memory[-4:]
    )

    return (

        "\nArchived trajectories:\n"

        + compressed
    )


def build_image_block(
    image_context
):

    if (
        not image_context
        or not isinstance(
            image_context,
            dict
        )
    ):

        return ""

    hint = (

        image_context.get(
            "hint"
        )

        or

        image_context.get(
            "prompt"
        )
    )

    if not hint:
        return ""

    return (

        "\nVisual context:\n"

        + safe_slice(
            hint,
            MAX_IMAGE_HINT
        )
    )


def build_math_block(
    last_math
):

    if not last_math:
        return ""

    expr = last_math.get(
        "expr"
    )

    if not expr:
        return ""

    return (

        "\nMath context:\n"

        + safe_slice(
            expr,
            MAX_MATH_EXPR
        )
    )
# =====================================================
# 🔥 VISUAL SCENE BLOCK
# =====================================================

def build_visual_scene_block(
    active_visual_scene
):

    if (
        not active_visual_scene
        or not isinstance(
            active_visual_scene,
            dict
        )
    ):

        return ""

    scene_type = active_visual_scene.get(
        "scene_type",
        "unknown"
    )

    summary = active_visual_scene.get(
        "summary",
        ""
    )

    objects = active_visual_scene.get(
        "objects",
        []
    )

    lines = [

        "\nVisual scene continuity:",

        f"Scene type: {scene_type}"
    ]

    if objects:

        lines.append(

            "Objects: "
            + ", ".join(objects)
        )

    if summary:

        lines.append(

            "Summary: "
            + safe_slice(
                summary,
                300
            )
        )

    return "\n".join(lines)


def build_current_request(
    text,
    scene_state
):

    trajectory = scene_state.get(
        "trajectory"
    )

    continuity = scene_state.get(
        "continuity_mode"
    )

    lines = [

        "Current user request:",

        text,

        "",

        "Важно:",

        "если trajectory продолжается —",

        "сохраняй continuity.",

        "",

        "Если trajectory завершён —",

        "не тащи старую сцену."
    ]

    if trajectory:

        lines.extend([

            "",

            f"Current trajectory: "
            f"{trajectory}"
        ])

    if continuity:

        lines.extend([

            "",

            f"Continuity mode: "
            f"{continuity}"
        ])

    return "\n".join(lines)


# =====================================================
# 🔥 FLOW STABILIZATION
# =====================================================

def stabilize_active_flow(
    state,
    scene_state
):

    """
    Active flow теперь
    должен быть связан
    с scene_state,
    а не жить отдельно.
    """

    active_flow = state.get(
        "active_flow"
    )

    if not active_flow:
        return

    trajectory = scene_state.get(
        "trajectory"
    )

    if not trajectory:
        return

    active_flow[
        "trajectory"
    ] = trajectory

    active_flow[
        "scene_bound"
    ] = True

    active_flow[
        "continuity_priority"
    ] = True


# =====================================================
# 🔥 CONTEXT BUILD
# =====================================================

def build_context_text(
    user_id,
    text,
    state
):

    text = normalize_text(
        text
    )

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
    # =================================================
    # 🔥 ACTIVE VISUAL SCENE
    # =================================================

    active_visual_scene = state.get(
        "active_visual_scene"
    )

    last_math = state.get(
        "last_math"
    )

    scene_state = state.get(
        "scene_state",
        {}
    )

    # =================================================
    # 🔥 FLOW STABILIZATION
    # =====================================================

    stabilize_active_flow(

        state,

        scene_state
    )

    # =================================================
    # 🔥 TOPIC SHIFT
    # =====================================================

    topic_shift = detect_topic_shift(

        text,

        active_flow,

        scene_state
    )

    # =================================================
    # 🔥 FLOW CLEANUP
    # =====================================================

    if topic_shift:

        archive_completed_flow(

            state,

            active_flow
        )

        state[
            "active_flow"
        ] = None

        active_flow = None

    # =================================================
    # 🔥 BASE
    # =====================================================

    base = build_base_context()

    # =================================================
    # 🔥 SCENE
    # =====================================================

    scene_block = build_scene_block(
        scene_state
    )

    # =================================================
    # 🔥 SUMMARY
    # =====================================================

    summary_block = build_summary_block(
        summary
    )

    # =================================================
    # 🔥 PASSIVE
    # =====================================================

    passive_block = build_passive_memory_block(
        passive_memory
    )

    # =================================================
    # 🔥 IMAGE
    # =====================================================

    image_block = build_image_block(
        image_context
    )
    # =================================================
    # 🔥 VISUAL SCENE
    # =====================================================

    visual_scene_block = (
        build_visual_scene_block(
            active_visual_scene
        )
    )

    # =================================================
    # 🔥 MATH
    # =====================================================

    math_block = build_math_block(
        last_math
    )

    # =================================================
    # 🔥 RELEVANT DIALOG
    # =====================================================

    relevant_dialog = build_relevant_dialog(

        dialog,

        text,

        active_flow,

        scene_state
    )

    # =================================================
    # 🔥 REQUEST
    # =====================================================

    current_request = build_current_request(

        text,

        scene_state
    )

    # =================================================
    # 🔥 FINAL
    # =====================================================

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

    Summary теперь:
    - мягче;
    - спокойнее;
    - без recursive duplication;
    - без cognitive overload.
    """

    old = state.get(
        "memory_summary",
        ""
    )

    user_text = normalize_text(
        user_text
    )

    bot_reply = normalize_text(
        bot_reply
    )

    # =================================================
    # 🔥 LOW VALUE
    # =====================================================

    if (

        normalize_lower(
            user_text
        ) in LOW_VALUE_MESSAGES

        or len(user_text) <= 2
    ):

        return

    # =================================================
    # 🔥 CLEANUP
    # =====================================================

    user_text = safe_slice(

        user_text,

        MAX_USER_MEMORY
    )

    bot_reply = safe_slice(

        bot_reply,

        MAX_BOT_MEMORY
    )

    # =================================================
    # 🔥 BUILD
    # =====================================================

    chunk = (

        f"{user_text} "

        f"→ "

        f"{bot_reply}"
    )

    # =================================================
    # 🔥 DUPLICATE PROTECTION
    # =====================================================

    if chunk in old:
        return

    # =================================================
    # 🔥 TRAJECTORY PRIORITY
    # =====================================================

    scene_state = state.get(
        "scene_state",
        {}
    )

    trajectory = scene_state.get(
        "trajectory"
    )

    if trajectory:

        chunk = (
            f"[{trajectory}] "
            + chunk
        )

    # =================================================
    # 🔥 COMBINE
    # =====================================================

    combined = (

        old
        + " | "
        + chunk
    ).strip()

    # =================================================
    # 🔥 OVERLOAD CONTROL
    # =====================================================

    if len(combined) > MAX_SUMMARY_LENGTH:

        combined = combined[
            -MAX_SUMMARY_LENGTH:
        ]

    # =================================================
    # 🔥 SAVE
    # =====================================================

    state[
        "memory_summary"
    ] = combined


# =====================================================
# 🔥 SCENE SYNCHRONIZATION
# =====================================================

def synchronize_scene_state(
    state
):

    """
    DeepHub synchronization layer.

    Scene_state —
    главный источник истины.

    Не dialog.
    Не summary.
    Не keywords.
    """

    scene_state = state.get(
        "scene_state",
        {}
    )

    active_flow = state.get(
        "active_flow"
    )

    if not scene_state:
        return

    # =================================================
    # 🔥 FLOW SYNC
    # =====================================================

    if active_flow:

        trajectory = scene_state.get(
            "trajectory"
        )

        if trajectory:

            active_flow[
                "trajectory"
            ] = trajectory

    # =================================================
    # 🔥 EXECUTION SYNC
    # =====================================================

    execution_mode = scene_state.get(
        "execution_mode"
    )

    if execution_mode:

        state[
            "execution_mode"
        ] = execution_mode

    # =================================================
    # 🔥 VISUAL SYNC
    # =====================================================

    visual_mode = scene_state.get(
        "visual_mode"
    )

    if visual_mode:

        state[
            "visual_mode"
        ] = visual_mode

    # =================================================
    # 🔥 CONTINUITY
    # =====================================================

    continuity_mode = scene_state.get(
        "continuity_mode"
    )

    if continuity_mode:

        state[
            "continuity_mode"
        ] = continuity_mode


# =====================================================
# 🔥 CONTEXT ENTRY
# =====================================================

def build_deephub_context(
    user_id,
    text,
    state
):

    """
    Главная точка входа
    DeepHub context system.
    """

    synchronize_scene_state(
        state
    )

    return build_context_text(

        user_id,

        text,

        state
    )
