# =====================================================
# 🧠 APRIL SCENE CONTEXT COORDINATION SYSTEM
# =====================================================

"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APRIL FILE ID
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

APRIL_FILE_ID:
APRIL_SCENE_CONTEXT_COORDINATION_SYSTEM

ROLE:
SCENE_CONTEXT_COORDINATOR

ROOM:
CONTEXT_ROOM

INPUT:
USER_TEXT
STATE
ACTIVE_FLOW
SCENE_STATE
VISUAL_SCENE
EXECUTOR_CONTEXT

OUTPUT:
MACHINE_CONTEXT
SCENE_COORDINATION
TRAJECTORY_SYNCHRONIZATION
CONTEXT_PAYLOAD
ANALYZER_TELEMETRY

DEPENDENCIES:
EXECUTOR
SCENE_STATE
ACTIVE_FLOW_SYSTEM
VISUAL_CONTINUITY_SYSTEM

CRITICAL:
TRUE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 GOLDEN RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file NEVER:
- makes cognition decisions
- performs orchestration
- formats frontend output
- answers users

This file ONLY:
- coordinates scene context
- synchronizes trajectories
- stabilizes continuity
- prepares machine context
- protects renderer continuity
"""

# =====================================================
# 🔥 APRIL TRACE LOGS
# =====================================================

def APRIL_LOG_IN(
    room,
    metadata=None
):

    try:

        print({

            "type":
                "APRIL_LOG_IN",

            "room":
                room,

            "file":
                "APRIL_SCENE_CONTEXT_COORDINATION_SYSTEM",

            "metadata":
                metadata or {}
        })

    except Exception:
        pass


def APRIL_LOG_OUT(
    room,
    metadata=None
):

    try:

        print({

            "type":
                "APRIL_LOG_OUT",

            "room":
                room,

            "file":
                "APRIL_SCENE_CONTEXT_COORDINATION_SYSTEM",

            "metadata":
                metadata or {}
        })

    except Exception:
        pass

# =====================================================
# 🔥 SYSTEM LIMITS
# =====================================================

LOW_VALUE_MESSAGES = [

    "ок",
    "ага",
    "понял",
    "да",
    "ясно",
    "угу"
]

MAX_RELEVANT_MESSAGES = 20
MAX_DIALOG_SCAN = 40
MAX_PASSIVE_MEMORY = 10
MAX_SUMMARY_LENGTH = 1200

MAX_USER_MEMORY = 140
MAX_BOT_MEMORY = 180

MAX_IMAGE_HINT = 180
MAX_MATH_EXPR = 120
MAX_GOAL_LENGTH = 300

def build_scene_focus_snapshot(state):
    try:
        scene = state.get("active_scene", {})
        goal = scene.get("active_goal", "")
        topic = scene.get("active_topic", "")
        visual = scene.get("visual_summary", "")
        return {
            "goal": goal,
            "topic": topic,
            "visual": visual,
            "last_visual_event": scene.get(
                "last_visual_event",
                ""
            )
        }
    except Exception:
        return {}


MIN_KEYWORD_LENGTH = 4

# =====================================================
# 🔥 INTERNAL MACHINE CHANNELS
# =====================================================

INPUT_MACHINE_CHANNEL = {

    "source": "executor",
    "type": "machine_context_input",
    "isolated": True
}

OUTPUT_MACHINE_CHANNEL = {

    "target": "executor_rooms",
    "type": "machine_context_output",
    "isolated": True
}

# =====================================================
# 🔥 ANALYZER TELEMETRY
# =====================================================

def build_context_telemetry():

    APRIL_LOG_IN(

        "CONTEXT_ROOM",

        {
            "action":
                "build_context_telemetry"
        }
    )

    payload = {

        "file_id":
            "APRIL_SCENE_CONTEXT_COORDINATION_SYSTEM",

        "room":
            "CONTEXT_ROOM",

        "continuity_safe":
            True,

        "trajectory_sync":
            True,

        "renderer_continuity":
            True,

        "machine_context_active":
            True,

        "executor_connected":
            True
    }

    APRIL_LOG_OUT(

        "CONTEXT_ROOM",

        {
            "telemetry":
                "ready"
        }
    )

    return payload

# =====================================================
# 🔥 HELPERS
# =====================================================

def normalize_text(text):

    return (text or "").strip()


def normalize_lower(text):

    return normalize_text(text).lower()


def safe_slice(value, limit):

    if not value:
        return ""

    return str(value)[:limit]


def contains_any(text, words):

    return any(
        word in text
        for word in words
    )

# =====================================================
# 🔥 MACHINE CONTEXT BUILDERS
# =====================================================

def build_machine_context_payload(

    trajectory=None,
    scene_state=None,
    active_flow=None,
    visual_scene=None

):

    APRIL_LOG_IN(

        "CONTEXT_ROOM",

        {
            "action":
                "build_machine_context_payload"
        }
    )

    payload = {

        "trajectory": trajectory,

        "scene_state":
            scene_state or {},

        "active_flow":
            active_flow or {},

        "visual_scene":
            visual_scene or {},

        "visual_focus":
            scene_state.get("visual_focus", {}) if scene_state else {},

        "machine_only": True,

        "human_visible": False,

        "telemetry":
            build_context_telemetry()
    }

    APRIL_LOG_OUT(

        "CONTEXT_ROOM",

        {
            "payload":
                "machine_context_ready"
        }
    )

    return payload

# =====================================================
# 🔥 TOPIC SHIFT DETECTION
# =====================================================

def detect_topic_shift(

    text,
    active_flow,
    scene_state

):

    APRIL_LOG_IN(

        "CONTEXT_ROOM",

        {
            "action":
                "detect_topic_shift"
        }
    )

    text = normalize_lower(text)

    if not active_flow:

        APRIL_LOG_OUT(

            "CONTEXT_ROOM",

            {
                "topic_shift":
                    False
            }
        )

        return False

    flow_type = active_flow.get(
        "type"
    )

    if not flow_type:

        APRIL_LOG_OUT(

            "CONTEXT_ROOM",

            {
                "topic_shift":
                    False
            }
        )

        return False

    trajectory = scene_state.get(
        "trajectory"
    )

    if trajectory:

        if trajectory.lower() in text:

            APRIL_LOG_OUT(

                "CONTEXT_ROOM",

                {
                    "topic_shift":
                        False
                }
            )

            return False

    math_unrelated = [

        "кафе",
        "доставка",
        "погода",
        "кофе",
        "ресторан"
    ]

    image_unrelated = [

        "код",
        "python",
        "ошибка",
        "сервер"
    ]

    if flow_type == "math":

        if contains_any(
            text,
            math_unrelated
        ):

            APRIL_LOG_OUT(

                "CONTEXT_ROOM",

                {
                    "topic_shift":
                        True
                }
            )

            return True

    if flow_type == "image":

        if contains_any(
            text,
            image_unrelated
        ):

            APRIL_LOG_OUT(

                "CONTEXT_ROOM",

                {
                    "topic_shift":
                        True
                }
            )

            return True

    APRIL_LOG_OUT(

        "CONTEXT_ROOM",

        {
            "topic_shift":
                False
        }
    )

    return False

# =====================================================
# 🔥 PASSIVE MEMORY
# =====================================================

def archive_completed_flow(

    state,
    active_flow

):

    APRIL_LOG_IN(

        "CONTEXT_ROOM",

        {
            "action":
                "archive_completed_flow"
        }
    )

    if not active_flow:

        APRIL_LOG_OUT(

            "CONTEXT_ROOM",

            {
                "archive":
                    "empty_flow"
            }
        )

        return

    memory = state.get(
        "passive_memory",
        []
    )

    flow_type = active_flow.get(
        "type",
        "unknown"
    )

    trajectory = active_flow.get(
        "trajectory"
    )

    original = active_flow.get(
        "original",
        ""
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

    APRIL_LOG_OUT(

        "CONTEXT_ROOM",

        {
            "archive":
                "stored"
        }
    )

# =====================================================
# 🔥 SCENE BLOCK
# =====================================================

def build_scene_block(scene_state):

    APRIL_LOG_IN(

        "CONTEXT_ROOM",

        {
            "action":
                "build_scene_block"
        }
    )

    if not scene_state:

        APRIL_LOG_OUT(

            "CONTEXT_ROOM",

            {
                "scene":
                    "empty"
            }
        )

        return ""

    lines = []

    trajectory = scene_state.get(
        "trajectory"
    )

    goal = scene_state.get(
        "goal"
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

    if trajectory:

        lines.append(
            f"Trajectory: {trajectory}"
        )

    if goal:

        lines.append(
            f"Goal: "
            f"{safe_slice(goal, MAX_GOAL_LENGTH)}"
        )

    if active_room:

        lines.append(
            f"Room: {active_room}"
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

    if not lines:

        APRIL_LOG_OUT(

            "CONTEXT_ROOM",

            {
                "scene":
                    "no_lines"
            }
        )

        return ""

    payload = (

        "\nSCENE STATE:\n"
        + "\n".join(lines)
    )

    APRIL_LOG_OUT(

        "CONTEXT_ROOM",

        {
            "scene":
                "built"
        }
    )

    return payload

# =====================================================
# 🔥 VISUAL SCENE BLOCK
# =====================================================

def build_visual_scene_block(
    active_visual_scene
):

    APRIL_LOG_IN(

        "CONTEXT_ROOM",

        {
            "action":
                "build_visual_scene_block"
        }
    )

    if not active_visual_scene:

        APRIL_LOG_OUT(

            "CONTEXT_ROOM",

            {
                "visual_scene":
                    "empty"
            }
        )

        return ""

    lines = [

        "\nVISUAL CONTINUITY:"
    ]

    scene_type = active_visual_scene.get(
        "scene_type"
    )

    if scene_type:

        lines.append(
            f"Scene: {scene_type}"
        )

    summary = active_visual_scene.get(
        "summary"
    )

    if summary:

        lines.append(
            f"Summary: "
            f"{safe_slice(summary, 300)}"
        )

    objects = active_visual_scene.get(
        "objects",
        []
    )

    if objects:

        lines.append(
            "Objects: "
            + ", ".join(objects)
        )


    events_count = active_visual_scene.get(
        "events_count"
    )

    if events_count is not None:

        lines.append(
            f"Events: {events_count}"
        )

    package = active_visual_scene.get(
        "package"
    )

    if package:

        lines.append(
            f"Package: {package}"
        )

    session_started_utc = active_visual_scene.get(
        "session_started_utc"
    )

    if session_started_utc:

        lines.append(
            f"Session UTC: {session_started_utc}"
        )

    last_event = active_visual_scene.get(
        "last_event"
    )

    if last_event:

        lines.append(
            f"Last Event: {safe_slice(last_event, 120)}"
        )

    payload = "\n".join(lines)

    APRIL_LOG_OUT(

        "CONTEXT_ROOM",

        {
            "visual_scene":
                "built"
        }
    )

    return payload


# =====================================================
# 🔥 VISUAL FOCUS BLOCK
# =====================================================

def build_visual_focus_block(state):

    focus = state.get("visual_focus", {})

    if not focus:
        return ""

    lines = ["\nACTIVE VISUAL FOCUS:"]

    obj = focus.get("focused_object")
    if obj:
        lines.append(f"Focused Object: {obj}")

    qtype = focus.get("question_type")
    if qtype:
        lines.append(f"Question Type: {qtype}")

    confidence = focus.get("confidence")
    if confidence is not None:
        lines.append(f"Confidence: {confidence}")

    return "\\n".join(lines)


# =====================================================
# 🔥 RELEVANT DIALOG
# =====================================================

def build_relevant_dialog(

    dialog,
    text,
    active_flow,
    scene_state

):

    APRIL_LOG_IN(
        "CONTEXT_ROOM",
        {"action": "build_relevant_dialog"}
    )

    text = normalize_lower(text)

    relevant = []

    trajectory = scene_state.get("trajectory")
    dynamic_focus = scene_state.get("dynamic_focus", {})
    visual_focus = scene_state.get("visual_focus", {})

    for msg in reversed(dialog[-MAX_DIALOG_SCAN:]):

        content = str(msg.get("content", "")).strip()

        if not content:
            continue

        lowered = content.lower()

        priority = calculate_context_priority(
            lowered,
            dynamic_focus,
            visual_focus,
            trajectory
        )

        if msg in dialog[-3:]:
            priority += 2

        if priority >= 4:
            relevant.append(
                f"{msg.get('role','user')}: {safe_slice(content,220)}"
            )

    relevant = list(
        reversed(
            relevant[-MAX_RELEVANT_MESSAGES:]
        )
    )

    payload = "\n".join(relevant)

    APRIL_LOG_OUT(
        "CONTEXT_ROOM",
        {"dialog": "focus_first_built"}
    )

    return payload

# =====================================================
# 🔥 BASE MACHINE CONTEXT
# =====================================================

def build_base_context():

    APRIL_LOG_IN(

        "CONTEXT_ROOM",

        {
            "action":
                "build_base_context"
        }
    )

    payload = """

APRIL MACHINE CONTEXT

MODE:
- scene-first;
- continuity-heavy;
- low-noise orchestration;
- web-first routing;
- renderer continuity active.

RULES:
- preserve trajectory;
- avoid recursive reload;
- avoid duplicated reasoning;
- avoid scene fragmentation;
- maintain machine routing clarity.

"""

    APRIL_LOG_OUT(

        "CONTEXT_ROOM",

        {
            "base_context":
                "ready"
        }
    )

    return payload

# =====================================================
# 🔥 CURRENT REQUEST
# =====================================================

def build_current_request(
    text,
    scene_state
):

    APRIL_LOG_IN(

        "CONTEXT_ROOM",

        {
            "action":
                "build_current_request"
        }
    )

    trajectory = scene_state.get(
        "trajectory"
    )

    lines = [

        "CURRENT REQUEST:",
        text
    ]

    if trajectory:

        lines.extend([

            "",

            f"ACTIVE TRAJECTORY: "
            f"{trajectory}"
        ])

    payload = "\n".join(lines)

    APRIL_LOG_OUT(

        "CONTEXT_ROOM",

        {
            "request":
                "built"
        }
    )

    return payload

# =====================================================
# 🔥 FLOW STABILIZATION
# =====================================================

def stabilize_active_flow(
    state,
    scene_state
):

    APRIL_LOG_IN(

        "CONTEXT_ROOM",

        {
            "action":
                "stabilize_active_flow"
        }
    )

    active_flow = state.get(
        "active_flow"
    )

    if not active_flow:

        APRIL_LOG_OUT(

            "CONTEXT_ROOM",

            {
                "active_flow":
                    "empty"
            }
        )

        return

    trajectory = scene_state.get(
        "trajectory"
    )

    if not trajectory:

        APRIL_LOG_OUT(

            "CONTEXT_ROOM",

            {
                "trajectory":
                    "empty"
            }
        )

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

    APRIL_LOG_OUT(

        "CONTEXT_ROOM",

        {
            "active_flow":
                "stabilized"
        }
    )

# =====================================================
# 🔥 CONTEXT BUILD
# =====================================================

def build_context_text(

    user_id,
    text,
    state

):

    APRIL_LOG_IN(

        "CONTEXT_ROOM",

        {
            "action":
                "build_context_text",

            "user_id":
                user_id
        }
    )

    text = normalize_text(text)

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

    active_visual_scene = state.get(
        "active_visual_scene"
    )

    stabilize_active_flow(
        state,
        scene_state
    )

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

        state[
            "active_flow"
        ] = None

        active_flow = None

    base = build_base_context()

    scene_block = build_scene_block(
        scene_state
    )

    visual_scene_block = (
        build_visual_scene_block(
            active_visual_scene
        )
    )

    visual_focus_block = (
        build_visual_focus_block(
            state
        )
    )

    visual_summary_block = (
        build_visual_summary_block(
            state
        )
    )

    visual_memory_block = (
        build_visual_memory_block(
            state
        )
    )

    relevant_dialog = build_relevant_dialog(

        dialog,
        text,
        active_flow,
        scene_state
    )

    current_request = build_current_request(

        text,
        scene_state
    )

    image_block = ""

    if image_context:

        hint = (

            image_context.get(
                "hint"
            )

            or

            image_context.get(
                "prompt"
            )
        )

        if hint:

            image_block = (

                "\nIMAGE CONTEXT:\n"

                + safe_slice(
                    hint,
                    MAX_IMAGE_HINT
                )
            )

    math_block = ""

    if last_math:

        expr = last_math.get(
            "expr"
        )

        if expr:

            math_block = (

                "\nMATH CONTEXT:\n"

                + safe_slice(
                    expr,
                    MAX_MATH_EXPR
                )
            )

    passive_block = ""

    if passive_memory:

        passive_block = (

            "\nARCHIVED TRAJECTORIES:\n"

            + "\n".join(
                passive_memory[-4:]
            )
        )

    summary_block = ""

    if summary:

        summary_block = (

            "\nMEMORY SUMMARY:\n"

            + safe_slice(
                summary,
                500
            )
        )

    full_context = f"""

{base}

{scene_block}

{visual_scene_block}

{visual_focus_block}

{visual_summary_block}

{visual_memory_block}

{summary_block}

{passive_block}

{image_block}

{math_block}

RELEVANT DIALOG:
{relevant_dialog}

{current_request}

"""

    APRIL_LOG_OUT(

        "CONTEXT_ROOM",

        {
            "context":
                "built"
        }
    )

    return full_context

# =====================================================
# 🔥 MEMORY SUMMARY
# =====================================================

def update_memory_summary(

    state,
    user_text,
    bot_reply

):

    APRIL_LOG_IN(

        "CONTEXT_ROOM",

        {
            "action":
                "update_memory_summary"
        }
    )

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

        APRIL_LOG_OUT(

            "CONTEXT_ROOM",

            {
                "summary":
                    "ignored_low_value"
            }
        )

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

        APRIL_LOG_OUT(

            "CONTEXT_ROOM",

            {
                "summary":
                    "duplicate"
            }
        )

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

    APRIL_LOG_OUT(

        "CONTEXT_ROOM",

        {
            "summary":
                "updated"
        }
    )

# =====================================================
# 🔥 SCENE SYNCHRONIZATION
# =====================================================

def synchronize_scene_state(
    state
):

    APRIL_LOG_IN(

        "CONTEXT_ROOM",

        {
            "action":
                "synchronize_scene_state"
        }
    )

    scene_state = state.get(
        "scene_state",
        {}
    )

    active_flow = state.get(
        "active_flow"
    )

    if not scene_state:

        APRIL_LOG_OUT(

            "CONTEXT_ROOM",

            {
                "scene_sync":
                    "empty"
            }
        )

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

    APRIL_LOG_OUT(

        "CONTEXT_ROOM",

        {
            "scene_sync":
                "complete"
        }
    )

# =====================================================
# 🔥 MAIN ENTRY
# =====================================================

def build_deephub_context(

    user_id,
    text,
    state

):

    APRIL_LOG_IN(

        "CONTEXT_ROOM",

        {
            "action":
                "build_deephub_context",

            "user_id":
                user_id
        }
    )

    synchronize_scene_state(
        state
    )

    machine_payload = (

        build_machine_context_payload(

            trajectory=state.get(
                "scene_state",
                {}
            ).get("trajectory"),

            scene_state=state.get(
                "scene_state",
                {}
            ),

            active_flow=state.get(
                "active_flow"
            ),

            visual_scene=state.get(
                "active_visual_scene"
            )
        )
    )

    state[
        "_machine_context"
    ] = machine_payload

    payload = build_context_text(

        user_id,
        text,
        state
    )

    APRIL_LOG_OUT(

        "CONTEXT_ROOM",

        {
            "deephub_context":
                "ready"
        }
    )

    return payload


# =====================================================
# 🧠 DYNAMIC FOCUS CONTEXT UPGRADE
# =====================================================

def build_context_focus_snapshot(text, state):

    focus = state.get("focus_state", {}) if state.get("focus_state") else state.get("dynamic_focus", {})

    return {
        "active_topic": focus.get("primary_focus"),
        "secondary_topic": focus.get("secondary_focus"),
        "focus_strength": focus.get("focus_strength", 0.0),
        "current_request": safe_slice(text, 180)
    }


def detect_context_refresh_needed(text, state):

    focus = state.get("focus_state", {}) if state.get("focus_state") else state.get("dynamic_focus", {})

    active_topic = str(
        focus.get("primary_focus", "")
    ).lower()

    current = normalize_lower(text)

    if not active_topic:
        return False

    overlap = 0

    for word in active_topic.split():
        if len(word) >= 4 and word in current:
            overlap += 1

    return overlap == 0


# =====================================================
# 🚀 APRIL FOCUS-FIRST CONTEXT UPGRADE
# =====================================================

def build_dynamic_focus_block(state):

    focus = state.get("focus_state", {}) if state.get("focus_state") else state.get("dynamic_focus", {})

    if not focus:
        return ""

    lines = ["\nDYNAMIC FOCUS:"]

    primary = focus.get("primary_focus")
    secondary = focus.get("secondary_focus")

    if primary:
        lines.append(f"Primary Focus: {primary}")

    if secondary:
        lines.append(f"Secondary Focus: {secondary}")

    strength = focus.get("focus_strength")

    if strength is not None:
        lines.append(f"Focus Strength: {strength}")

    return "\n".join(lines)


def build_visual_anchors_block(state):

    scene = state.get("active_visual_scene") or {}
    focus = state.get("visual_focus") or {}

    lines = ["\nVISUAL ANCHORS:"]

    focused = focus.get("focused_object")

    if focused:
        lines.append(f"Focused Object: {focused}")

    objects = scene.get("objects", [])

    if objects:
        lines.append(
            "Scene Objects: " + ", ".join(objects[:10])
        )

    if len(lines) == 1:
        return ""

    return "\n".join(lines)


def build_focus_priority_score(
    lowered,
    dynamic_focus,
    visual_focus,
    trajectory
):

    score = 0

    primary = str(
        dynamic_focus.get("primary_focus", "")
    ).lower()

    secondary = str(
        dynamic_focus.get("secondary_focus", "")
    ).lower()

    focused_object = str(
        visual_focus.get("focused_object", "")
    ).lower()

    if primary and primary in lowered:
        score += 8

    if secondary and secondary in lowered:
        score += 4

    if focused_object and focused_object in lowered:
        score += 6

    if trajectory and trajectory.lower() in lowered:
        score += 6

    return score


# =====================================================
# 🚀 FOCUS-FIRST RELEVANCE STRATEGY
# =====================================================

FOCUS_FIRST_MODE = True

def calculate_context_priority(
    lowered,
    dynamic_focus,
    visual_focus,
    trajectory
):

    score = build_focus_priority_score(
        lowered,
        dynamic_focus,
        visual_focus,
        trajectory
    )

    return score




def build_visual_summary_block(state):

    visual_summary = state.get("visual_summary", {})

    if not visual_summary:
        return ""

    lines = ["\nVISUAL SUMMARY:"]

    if visual_summary.get("scene_events_count") is not None:
        lines.append(
            f"Events: {visual_summary.get('scene_events_count')}"
        )

    if visual_summary.get("package"):
        lines.append(
            f"Package: {visual_summary.get('package')}"
        )

    if visual_summary.get("last_event"):
        lines.append(
            f"Last Event: {safe_slice(visual_summary.get('last_event'),120)}"
        )

    return "\n".join(lines)


def build_visual_memory_block(state):

    memory = (
        state.get("memory_timeline", {})
        .get("day_0", {})
        .get("visual_scenes", [])
    )

    if not memory:
        return ""

    return (
        "\nVISUAL MEMORY:\n"
        f"Snapshots: {len(memory)}"
    )




# =====================================================
# 🚀 USER SPACE FOUNDATION (APRIL UPGRADE)
# =====================================================

def build_user_space(state):
    """
    Unified machine workspace used as the single source of truth.
    This is an architectural facade over the existing state structure.
    No new state manager or parallel memory is introduced.
    """

    scene = state.get("scene_state", {})
    visual_scene = state.get("active_visual_scene", {})

    return {
        "active_scene": scene,
        "dialog": state.get("dialog", []),
        "current_request": state.get("current_request"),
        "dynamic_focus": state.get("focus_state", state.get("dynamic_focus", {})),
        "goal_hierarchy": state.get("goal_hierarchy", {}),
        "active_flow": state.get("active_flow", {}),
        "memory_timeline": state.get("memory_timeline", {}),
        "visual_summary": state.get("visual_summary", {}),
        "memory_summary": state.get("memory_summary", ""),
        "renderer_state": state.get("renderer_state", {}),
        "workspace_state": {
            "visual_scene": visual_scene,
            "visual_focus": state.get("visual_focus", {}),
            "execution_mode": state.get("execution_mode"),
            "visual_mode": state.get("visual_mode"),
        },
    }


def build_scene_contract(state):
    """
    Canonical scene payload shared with downstream components.
    """
    return {
        "version": 1,
        "user_space": build_user_space(state),
        "scene": state.get("scene_state", {}),
        "renderer_state": state.get("renderer_state", {}),
    }


# =====================================================
# 🧠 APRIL CONTEXT SYSTEM V2 MEMORY INTEGRATION
# =====================================================

def build_memory_timeline_block(state):

    timeline = state.get("memory_timeline", {})

    if not timeline:
        return ""

    lines = ["\nMEMORY RECALL:"]

    day0 = timeline.get("day_0", {})
    day1 = timeline.get("day_1", {})

    if day0:
        lines.append("Today Memory Active")

        for slot in ["A", "B"]:
            entries = day0.get(slot, [])
            if entries:
                lines.append(
                    f"{slot}: {len(entries)} active topics"
                )

    if day1:
        lines.append("Yesterday Memory Available")

    return "\n".join(lines)


def build_unified_focus_block(state):

    focus_state = state.get("focus_state", {})

    if focus_state:

        lines = ["\nFOCUS STATE:"]

        if focus_state.get("active_topic"):
            lines.append(
                f"Active Topic: {focus_state.get('active_topic')}"
            )

        if focus_state.get("active_goal"):
            lines.append(
                f"Active Goal: {focus_state.get('active_goal')}"
            )

        if focus_state.get("priority_score") is not None:
            lines.append(
                f"Priority: {focus_state.get('priority_score')}"
            )

        if focus_state.get("intent_freshness") is not None:
            lines.append(
                f"Intent Freshness: {focus_state.get('intent_freshness')}"
            )

        return "\n".join(lines)

    return build_dynamic_focus_block(state)  # compatibility fallback


def calculate_context_priority_v2(
    lowered,
    dynamic_focus,
    visual_focus,
    trajectory,
    focus_state=None
):

    score = calculate_context_priority(
        lowered,
        dynamic_focus,
        visual_focus,
        trajectory
    )

    focus_state = focus_state or {}

    active_topic = str(
        focus_state.get("active_topic", "")
    ).lower()

    if active_topic and active_topic in lowered:
        score += 10

    score += int(
        focus_state.get(
            "priority_score",
            0
        )
    )

    return score


def build_context_memory_bridge(state):

    return {
        "focus_state":
            state.get("focus_state", {}),

        "memory_timeline":
            state.get("memory_timeline", {}),

        "memory_cycle":
            state.get("memory_cycle", {}),

        # legacy dynamic_focus retained temporarily for compatibility
        "dynamic_focus": state.get("dynamic_focus", {}),

        "goal_hierarchy":
            state.get("goal_hierarchy", {}),

        "open_loops":
            state.get("open_loops", []),

        "memory_signals":
            state.get("memory_signals", {}),

        "visual_summary":
            state.get(
                "visual_summary",
                {}
            ),

        "active_visual_scene":
            state.get(
                "active_visual_scene",
                {}
            ),

        "today_visual_memory":
            state.get(
                "memory_timeline",
                {}
            ).get(
                "day_0",
                {}
            ).get(
                "visual_scenes",
                []
            )
    }
