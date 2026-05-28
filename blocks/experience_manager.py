# =====================================================
# 🧠 APRIL EXECUTION STABILIZER CORE
# =====================================================

"""
APRIL EXECUTION STABILIZER CORE

APRIL_FILE_ID:
APRIL_EXECUTION_STABILIZER_CORE_V2

ROLE:
TEMPORARY_EXECUTION_CONTINUITY_AND_ANTI_LOOP_SUPPORT

INPUT:
EXECUTION_STATE
LAST_ACTION
EXECUTION_RESULT
MODALITY_CONTEXT
RETRY_CONTEXT

OUTPUT:
TEMPORARY_EXECUTION_BUFFER
ANTI_LOOP_STABILIZATION
RETRY_SUPPRESSION_STATE
EXECUTION_CONTINUITY_SUPPORT

THIS FILE IS:
- temporary execution continuity layer
- anti-loop stabilizer
- retry suppression helper
- renderer stabilization support
- modality cooldown helper
- lightweight execution continuity layer

THIS FILE IS NOT:
- execution memory
- routing memory
- cognition engine
- orchestration authority
- trajectory memory
- retry chaos system

GOLDEN APRIL PRINCIPLES:
- lightweight before heavy
- stabilization before retry
- continuity before recursion
- executor-safe architecture
- no orchestration duplication
- no execution noise accumulation
"""

import json
import os
import time
from datetime import datetime

# =====================================================
# 🔥 FILE ID
# =====================================================

APRIL_FILE_ID = (
    "APRIL_EXECUTION_STABILIZER_CORE_V2"
)

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

EXECUTION_STABILIZER_TASK_CHANNEL = {

    "channel":
        "execution_stabilizer_task_channel",

    "isolated":
        True
}

EXECUTION_STABILIZER_RESPONSE_CHANNEL = {

    "channel":
        "execution_stabilizer_response_channel",

    "isolated":
        True
}

# =====================================================
# 🔥 CONFIG
# =====================================================

DATA_FILE = "experience.json"

# =====================================================
# 🔥 STABILIZATION LIMITS
# =====================================================

MAX_ACTIONS = 5

EXECUTION_TTL = 120

# =====================================================
# 🔥 MODALITIES
# =====================================================

VISUAL_MODALITIES = {

    "graph",
    "diagram",
    "formula",
    "scene",
    "renderer",
    "image",
    "visual"
}

# =====================================================
# 🔥 MACHINE LOGGING
# =====================================================

def build_input_log():

    """
    INPUT MACHINE TRACE

    Used internally by:
    - Executor
    - Governance
    - diagnostics
    - retry stabilization
    """

    return {

        "file_id":
            APRIL_FILE_ID,

        "event":
            "execution_stabilizer_input",

        "channel":
            EXECUTION_STABILIZER_TASK_CHANNEL,

        "timestamp":
            datetime.utcnow().isoformat(),

        "machine_only":
            True
    }


def build_output_log(
    user_id,
    execution_state
):

    """
    OUTPUT MACHINE TRACE

    Used internally by:
    - Executor
    - analytics
    - anti-loop diagnostics
    """

    return {

        "file_id":
            APRIL_FILE_ID,

        "event":
            "execution_stabilizer_output",

        "channel":
            EXECUTION_STABILIZER_RESPONSE_CHANNEL,

        "user_id":
            str(user_id),

        "execution_state":
            execution_state,

        "timestamp":
            datetime.utcnow().isoformat(),

        "machine_only":
            True
    }

# =====================================================
# 🔥 HELPERS
# =====================================================

def normalize_text(
    value
):

    return str(
        value or ""
    ).strip()


def normalize_lower(
    value
):

    return normalize_text(
        value
    ).lower()

# =====================================================
# 🔥 LOAD
# =====================================================

def load_experience():

    """
    Safe stabilization loading.
    """

    if not os.path.exists(
        DATA_FILE
    ):

        return {}

    try:

        with open(

            DATA_FILE,

            "r",

            encoding="utf-8"

        ) as f:

            return json.load(f)

    except Exception as e:

        print(
            "🔥 LOAD ERROR:",
            e
        )

        return {}

# =====================================================
# 🔥 SAVE
# =====================================================

def save_experience(
    data
):

    """
    Safe stabilization saving.
    """

    try:

        with open(

            DATA_FILE,

            "w",

            encoding="utf-8"

        ) as f:

            json.dump(

                data,

                f,

                ensure_ascii=False,

                indent=2
            )

    except Exception as e:

        print(
            "🔥 SAVE ERROR:",
            e
        )

# =====================================================
# 🔥 CLEANUP
# =====================================================

def cleanup_old_actions(
    actions
):

    """
    DeepHub cleanup philosophy:

    DO NOT:
    - store long execution history
    - preserve retry loops
    - accumulate orchestration noise

    ONLY:
    - maintain short stabilization window
    """

    if not isinstance(
        actions,
        list
    ):

        return []

    now = time.time()

    cleaned = []

    for action in actions:

        timestamp = action.get(
            "timestamp",
            0
        )

        if (

            now - timestamp

            <= EXECUTION_TTL
        ):

            cleaned.append(
                action
            )

    return cleaned[
        -MAX_ACTIONS:
    ]

# =====================================================
# 🔥 MODALITY
# =====================================================

def detect_modality(
    last
):

    """
    Detects execution modality.
    """

    action_type = normalize_lower(

        last.get(
            "type",
            "unknown"
        )
    )

    if action_type in VISUAL_MODALITIES:

        return "renderer"

    return "execution"

# =====================================================
# 🔥 EXECUTION STATE
# =====================================================

def build_execution_state(
    last
):

    """
    Machine-readable stabilization state.

    IMPORTANT:
    This is NOT cognition memory.
    """

    action_type = normalize_lower(

        last.get(
            "type",
            "unknown"
        )
    )

    status = normalize_lower(

        last.get(
            "status",
            "unknown"
        )
    )

    modality = detect_modality(
        last
    )

    return {

        # =================================================
        # 🔥 CORE
        # =====================================================

        "modality":
            modality,

        "action_class":
            action_type,

        "status":
            status,

        # =================================================
        # 🔥 STABILIZATION
        # =====================================================

        "renderer_related":

            modality == "renderer",

        "execution_related":

            modality == "execution",

        "success":

            status == "success",

        "failed":

            status == "failed",

        "retry":

            status in [

                "retry",
                "failed"
            ],

        # =================================================
        # 🔥 CONTINUITY
        # =====================================================

        "continuation_safe":
            True,

        "temporary":
            True,

        "stabilizer":
            True,

        # =================================================
        # 🔥 META
        # =====================================================

        "timestamp":
            time.time()
    }

# =====================================================
# 🔥 EXECUTION ANALYSIS
# =====================================================

def analyze_execution_pressure(
    actions
):

    """
    Lightweight anti-loop analysis.
    """

    if not actions:

        return {

            "retry_pressure":
                0.0,

            "loop_risk":
                False
        }

    failures = 0

    retries = 0

    action_classes = []

    for action in actions[-3:]:

        if action.get(
            "failed"
        ):

            failures += 1

        if action.get(
            "retry"
        ):

            retries += 1

        action_class = action.get(
            "action_class"
        )

        if action_class:

            action_classes.append(
                action_class
            )

    repeated_flow = (

        len(set(action_classes)) == 1
        and len(action_classes) >= 3
    )

    pressure = min(

        (
            failures * 0.35
            + retries * 0.2
        ),

        1.0
    )

    return {

        "retry_pressure":
            round(
                pressure,
                3
            ),

        "loop_risk":
            repeated_flow and failures >= 2
    }

# =====================================================
# 🔥 EXECUTION UPDATE
# =====================================================

def update_experience(
    user_id,
    state
):

    """
    Lightweight execution stabilization.

    Flow:

    executor action
        ↓
    stabilization snapshot
        ↓
    anti-loop continuity
        ↓
    temporary execution buffer
    """

    build_input_log()

    data = load_experience()

    user_id = str(
        user_id
    )

    if user_id not in data:

        data[user_id] = {

            "actions": []
        }

    last = state.get(
        "last_action"
    )

    if not last:

        print(
            "⚠️ last_action отсутствует"
        )

        return {

            "success": False,

            "reason":
                "missing_last_action",

            "channel":
                EXECUTION_STABILIZER_RESPONSE_CHANNEL
        }

    # =================================================
    # 🔥 EXECUTION STATE
    # =====================================================

    execution_state = (
        build_execution_state(
            last
        )
    )

    print(
        "🧠 EXECUTION STABILIZER:",
        execution_state
    )

    # =================================================
    # 🔥 BUFFER
    # =====================================================

    data[user_id][
        "actions"
    ].append(
        execution_state
    )

    # =================================================
    # 🔥 CLEANUP
    # =====================================================

    data[user_id][
        "actions"
    ] = cleanup_old_actions(

        data[user_id][
            "actions"
        ]
    )

    # =================================================
    # 🔥 SAVE
    # =====================================================

    save_experience(
        data
    )

    # =================================================
    # 🔥 ANALYTICS
    # =====================================================

    analytics = analyze_execution_pressure(

        data[user_id][
            "actions"
        ]
    )

    build_output_log(

        user_id,

        execution_state
    )

    # =================================================
    # 🔥 RESPONSE
    # =====================================================

    return {

        "success":
            True,

        "channel":
            EXECUTION_STABILIZER_RESPONSE_CHANNEL,

        "stabilization_active":
            True,

        "temporary_memory":
            True,

        "retry_pressure":
            analytics.get(
                "retry_pressure",
                0.0
            ),

        "loop_risk":
            analytics.get(
                "loop_risk",
                False
            ),

        "stored_actions":
            len(
                data[user_id][
                    "actions"
                ]
            ),

        "machine_only":
            True
    }

# =====================================================
# 🔥 EXECUTOR SNAPSHOT
# =====================================================

def build_executor_stabilization_snapshot(
    user_id
):

    """
    Executor stabilization snapshot.

    Used internally by:
    - Executor
    - Governance
    - retry suppression
    - diagnostics
    """

    data = load_experience()

    user_id = str(user_id)

    actions = data.get(
        user_id,
        {}
    ).get(
        "actions",
        []
    )

    analytics = analyze_execution_pressure(
        actions
    )

    return {

        "channel":
            EXECUTION_STABILIZER_RESPONSE_CHANNEL,

        "file_id":
            APRIL_FILE_ID,

        "actions":
            actions,

        "retry_pressure":
            analytics.get(
                "retry_pressure",
                0.0
            ),

        "loop_risk":
            analytics.get(
                "loop_risk",
                False
            ),

        "temporary_memory":
            True,

        "machine_only":
            True
    }
