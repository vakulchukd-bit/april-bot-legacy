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

# =====================================================
# 🔥 NEW CONTINUITY LAYER
# =====================================================

Visual continuity теперь работает
через semantic visual scene lifecycle.

Сцена может быть:

ACTIVE:
- сейчас обсуждается.

PASSIVE:
- недавно обсуждалась;
- может быть продолжена.

ARCHIVED:
- trajectory сохранён;
- можно мягко восстановить.

Главное:
- не повторять Gemini analysis;
- не создавать visual reload;
- не ломать continuity;
- не тащить старую сцену,
  если пользователь реально
  сменил trajectory.
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

MAX_VISUAL_SCENE_SUMMARY = 350

MAX_VISUAL_OBJECTS = 12

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
# 🔥 VISUAL CONTINUITY HELPERS
# =====================================================

def build_visual_scene_lifecycle(
    state
):

    active_visual_scene = state.get(
        "active_visual_scene"
    )

    if not active_visual_scene:
        return

    lifecycle = active_visual_scene.get(
        "lifecycle_state"
    )

    if not lifecycle:

        active_visual_scene[
            "lifecycle_state"
        ] = "ACTIVE"

    active_visual_scene[
        "continuity_active"
    ] = True

    active_visual_scene[
        "scene_alive"
    ] = True


def move_visual_scene_to_passive(
    state
):

    active_visual_scene = state.get(
        "active_visual_scene"
    )

    if not active_visual_scene:
        return

    active_visual_scene[
        "lifecycle_state"
    ] = "PASSIVE"

    active_visual_scene[
        "scene_alive"
    ] = False

    passive_visual_memory = state.get(
        "passive_visual_memory",
        []
    )

    compressed = {

        "scene_type":
            active_visual_scene.get(
                "scene_type"
            ),

        "trajectory":
            active_visual_scene.get(
                "trajectory"
            ),

        "summary":
            safe_slice(

                active_visual_scene.get(
                    "summary",
                    ""
                ),

                220
            ),

        "semantic_focus":
            active_visual_scene.get(
                "semantic_focus"
            ),

        "discussion_state":
            active_visual_scene.get(
                "discussion_state"
            )
    }

    passive_visual_memory.append(
        compressed
    )

    passive_visual_memory = (
        passive_visual_memory[-6:]
    )

    state[
        "passive_visual_memory"
    ] = passive_visual_memory


def detect_visual_scene_continuation(
    text,
    active_visual_scene
):

    if not active_visual_scene:
        return False

    text = normalize_lower(
        text
    )

    semantic_focus = normalize_lower(

        active_visual_scene.get(
            "semantic_focus",
            ""
        )
    )

    summary = normalize_lower(

        active_visual_scene.get(
            "summary",
            ""
        )
    )

    objects = [

        normalize_lower(x)

        for x in active_visual_scene.get(
            "objects",
            []
        )
    ]

    continuation_words = [

        "это",
        "ещё",
        "тут",
        "теперь",
        "на этом",
        "вот",
        "эта",
        "этот",
        "снова",
        "ещё один",
        "ещё фото",
        "ещё скрин"
    ]

    if contains_any(
        text,
        continuation_words
    ):

        return True

    if semantic_focus:

        if semantic_focus in text:

            return True

    if summary:

        summary_words = [

            w for w in summary.split()
            if len(w) >= 5
        ]

        for word in summary_words[:10]:

            if word in text:

                return True

    for obj in objects:

        if obj and obj in text:

            return True

    return False


# =====================================================
# 🔥 TOPIC SHIFT
# =====================================================

def detect_topic_shift(
    text,
    active_flow,
    scene_state,
    active_visual_scene=None
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

    # =================================================
    # 🔥 VISUAL CONTINUATION PRIORITY
    # =====================================================

    if detect_visual_scene_continuation(

        text,

        active_visual_scene
    ):

        return False

    if not active_flow:
        return False

    flow_type = active_flow.get(
        "type"
    )

    if not flow_type:
        return False

    # =================================================
    # 🔥 SCENE PRIORITY
    # =====================================================

    scene_trajectory = scene_state.get(
        "trajectory"
    )

    if scene_trajectory:

        if scene_trajectory in text:

            return False

    # =================================================
    # 🔥 MATH SHIFT
    # =====================================================

    if flow_type == "math":

        if contains_any(
            text,
            MATH_UNRELATED
        ):

            return True

    # =================================================
    # 🔥 IMAGE SHIFT
    # =====================================================

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

    if trajectory:

        lines.append(
            f"Trajectory: {trajectory}"
        )

    if goal:

        lines.append(
            f"Goal: "
            f"{safe_slice(goal, MAX_GOAL_LENGTH)}"
        )

    if user_intent:

        lines.append(
            f"Intent: {user_intent}"
        )

    if confirmed_direction:

        lines.append(
            f"Direction: "
            f"{confirmed_direction}"
        )

    if visual_mode:

        lines.append(
            "Visual continuity active"
        )

    if execution_mode:

        lines.append(
            "Execution mode active"
        )

    if active_room:

        lines.append(
            f"Coordinator room: "
            f"{active_room}"
        )

    if orchestration_mode:

        lines.append(
            f"Orchestration: "
            f"{orchestration_mode}"
        )

    if continuity_mode:

        lines.append(
            f"Continuity: "
            f"{continuity_mode}"
        )

    if scene_priority:

        lines.append(
            f"Scene priority: "
            f"{scene_priority}"
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
    active_flow,
    scene_state=None,
    active_visual_scene=None
):

    """
    relevant_dialog —
    support layer.

    Главный приоритет:
    continuity trajectory.
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

    visual_focus = None

    if active_visual_scene:

        visual_focus = normalize_lower(

            active_visual_scene.get(
                "semantic_focus",
                ""
            )
        )

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

        if msg in dialog[-3:]:

            priority += 3

        for kw in keywords:

            if kw in lowered:

                priority += 2

        if active_flow:

            flow_type = active_flow.get(
                "type"
            )

            if (

                flow_type
                and flow_type in lowered
            ):

                priority += 3

        if trajectory:

            if trajectory.lower() in lowered:

                priority += 4

        # =================================================
        # 🔥 VISUAL CONTINUITY PRIORITY
        # =====================================================

        if visual_focus:

            if visual_focus in lowered:

                priority += 5

        if (

            "продолж" in lowered
            or "ещё" in lowered
            or "снова" in lowered
            or "этот" in lowered
        ):

            priority += 2

        if (

            "сделай" in lowered
            or "исправь" in lowered
            or "продолжай" in lowered
        ):

            priority += 2

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

Visual continuity:
- visual scene может продолжаться;
- новый скрин может быть
  continuation;
- не начинай dialogue заново,
  если trajectory сохраняется;
- не повторяй полный visual analysis;
- используй semantic continuity.

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

    semantic_focus = active_visual_scene.get(
        "semantic_focus"
    )

    discussion_state = active_visual_scene.get(
        "discussion_state"
    )

    lifecycle_state = active_visual_scene.get(
        "lifecycle_state",
        "ACTIVE"
    )

    continuity_active = active_visual_scene.get(
        "continuity_active",
        False
    )

    lines = [

        "\nVisual scene continuity:",

        f"Scene type: {scene_type}",

        f"Lifecycle: {lifecycle_state}"
    ]

    if continuity_active:

        lines.append(
            "Scene continuity active"
        )

    if semantic_focus:

        lines.append(

            "Semantic focus: "
            + semantic_focus
        )

    if discussion_state:

        lines.append(

            "Discussion state: "
            + discussion_state
        )

    if objects:

        lines.append(

            "Objects: "
            + ", ".join(
                objects[
                    :MAX_VISUAL_OBJECTS
                ]
            )
        )

    if summary:

        lines.append(

            "Summary: "
            + safe_slice(
                summary,
                MAX_VISUAL_SCENE_SUMMARY
            )
        )

    return "\n".join(lines)


def build_current_request(
    text,
    scene_state,
    active_visual_scene=None
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

    if active_visual_scene:

        lines.extend([

            "",

            "Visual continuity rules:",

            "- новый скрин может быть continuation;",

            "- не начинай visual dialogue заново;",

            "- продолжай semantic scene;",

            "- не повторяй полный visual analysis;"
        ])

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
    # 🔥 VISUAL LIFECYCLE
    # =====================================================

    build_visual_scene_lifecycle(
        state
    )

    stabilize_active_flow(

        state,

        scene_state
    )

    topic_shift = detect_topic_shift(

        text,

        active_flow,

        scene_state,

        active_visual_scene
    )

    # =================================================
    # 🔥 FLOW CLEANUP
    # =====================================================

    if topic_shift:

        archive_completed_flow(

            state,

            active_flow
        )

        move_visual_scene_to_passive(
            state
        )

        state[
            "active_flow"
        ] = None

        active_flow = None

    base = build_base_context()

    scene_block = build_scene_block(
        scene_state
    )

    summary_block = build_summary_block(
        summary
    )

    passive_block = build_passive_memory_block(
        passive_memory
    )

    image_block = build_image_block(
        image_context
    )

    visual_scene_block = (
        build_visual_scene_block(
            active_visual_scene
        )
    )

    math_block = build_math_block(
        last_math
    )

    relevant_dialog = build_relevant_dialog(

        dialog,

        text,

        active_flow,

        scene_state,

        active_visual_scene
    )

    current_request = build_current_request(

        text,

        scene_state,

        active_visual_scene
    )

    full = f"""

{base}

{scene_block}

{summary_block}

{passive_block}

{image_block}

{visual_scene_block}

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

    if (

        normalize_lower(
            user_text
        ) in LOW_VALUE_MESSAGES

        or len(user_text) <= 2
    ):

        return

    user_text = safe_slice(

        user_text,

        MAX_USER_MEMORY
    )

    bot_reply = safe_slice(

        bot_reply,

        MAX_BOT_MEMORY
    )

    chunk = (

        f"{user_text} "

        f"→ "

        f"{bot_reply}"
    )

    if chunk in old:
        return

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

    combined = (

        old
        + " | "
        + chunk
    ).strip()

    if len(combined) > MAX_SUMMARY_LENGTH:

        combined = combined[
            -MAX_SUMMARY_LENGTH:
        ]

    state[
        "memory_summary"
    ] = combined


# =====================================================
# 🔥 SCENE SYNCHRONIZATION
# =====================================================

def synchronize_scene_state(
    state
):

    scene_state = state.get(
        "scene_state",
        {}
    )

    active_flow = state.get(
        "active_flow"
    )

    if not scene_state:
        return

    if active_flow:

        trajectory = scene_state.get(
            "trajectory"
        )

        if trajectory:

            active_flow[
                "trajectory"
            ] = trajectory

    execution_mode = scene_state.get(
        "execution_mode"
    )

    if execution_mode:

        state[
            "execution_mode"
        ] = execution_mode

    visual_mode = scene_state.get(
        "visual_mode"
    )

    if visual_mode:

        state[
            "visual_mode"
        ] = visual_mode

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

    synchronize_scene_state(
        state
    )

    return build_context_text(

        user_id,

        text,

        state
    )
