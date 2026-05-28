# =====================================================
# 🧠 APRIL EXECUTION STABILIZER CORE
# =====================================================

"""
APRIL EXECUTION STABILIZER CORE

APRIL_FILE_ID:
APRIL_EXECUTION_STABILIZER_CORE

ROLE:
TEMPORARY_EXECUTION_CONTINUITY_AND_ANTI_LOOP_SUPPORT

INPUT:
EXECUTION_STATE
LAST_ACTION
EXECUTION_RESULT
TEMPORARY_RETRY_CONTEXT

OUTPUT:
SHORT_TERM_EXECUTION_BUFFER
ANTI_LOOP_STABILIZATION
TEMPORARY_EXECUTION_CONTINUITY
EXECUTOR_SUPPORT_CONTEXT

THIS FILE IS:
- temporary execution stabilizer
- short execution buffer
- anti-loop helper
- retry stabilization support
- lightweight execution continuity layer

THIS FILE IS NOT:
- long-term memory
- execution historian
- routing memory
- orchestration authority
- cognition engine
- analytics system
- permanent experience storage

GOLDEN APRIL RULES:
- lightweight before heavy
- continuity before recursion
- stabilization before retry
- no execution noise accumulation
- no old-pattern pollution
- executor-safe architecture
"""

import json
import os
from datetime import datetime

# =====================================================
# 🔥 FILE ID
# =====================================================

APRIL_FILE_ID = (
    "APRIL_EXECUTION_STABILIZER_CORE"
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
# 🔥 TEMPORARY MEMORY LIMIT
# =====================================================

"""
DeepHub philosophy:

Store ONLY:
- short stabilization history
- temporary continuity state
- anti-loop execution traces

Avoid:
- long-term execution memory
- orchestration pollution
- recursive retry patterns
"""

MAX_ACTIONS = 5

# =====================================================
# 🔥 MACHINE LOGS
# =====================================================

def build_execution_input_log():

    """
    INPUT MACHINE TRACE

    Used internally by:
    - Executor
    - Governance
    - diagnostics
    - stabilization analytics
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


def build_execution_output_log(
    user_id,
    entry
):

    """
    OUTPUT MACHINE TRACE

    Used internally by:
    - Executor
    - continuity systems
    - retry diagnostics
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

        "entry":
            entry,

        "timestamp":
            datetime.utcnow().isoformat(),

        "machine_only":
            True
    }

# =====================================================
# 🔥 LOAD
# =====================================================

def load_experience():

    """
    Safe stabilization loading.

    Temporary execution memory only.
    """

    if not os.path.exists(DATA_FILE):

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

def save_experience(data):

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

def cleanup_old_actions(actions):

    """
    DeepHub stabilization philosophy:

    DO NOT:
    - accumulate execution history
    - preserve recursive retry chains
    - keep orchestration pollution

    ONLY:
    - short temporary stabilization buffer
    """

    if not isinstance(
        actions,
        list
    ):

        return []

    return actions[-MAX_ACTIONS:]

# =====================================================
# 🔥 EXECUTION ANALYSIS
# =====================================================

def analyze_execution_pattern(
    actions
):

    """
    Lightweight anti-loop diagnostics.

    Helps Executor detect:
    - repeated failures
    - recursive retries
    - unstable execution flow
    """

    if not actions:

        return {

            "loop_risk":
                False,

            "failure_pressure":
                0.0
        }

    failures = 0

    last_types = []

    for action in actions[-3:]:

        status = action.get(
            "status"
        )

        action_type = action.get(
            "type"
        )

        if status == "failed":

            failures += 1

        if action_type:

            last_types.append(
                action_type
            )

    repeated = (

        len(set(last_types)) == 1
        and len(last_types) >= 3
    )

    return {

        "loop_risk":
            repeated and failures >= 2,

        "failure_pressure":
            min(
                failures * 0.35,
                1.0
            )
    }

# =====================================================
# 🔥 UPDATE EXPERIENCE
# =====================================================

def update_experience(
    user_id,
    state
):

    """
    Main stabilization entry.

    Stores ONLY:
    - temporary execution state
    - short continuity traces
    - anti-loop stabilization info
    """

    build_execution_input_log()

    data = load_experience()

    user_id = str(user_id)

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

    entry = {

        "type":
            last.get(
                "type",
                "unknown"
            ),

        "intent":
            last.get(
                "intent",
                "unknown"
            ),

        "status":
            last.get(
                "status",
                "unknown"
            )
    }

    print(
        "🧠 TEMP EXECUTION:",
        entry
    )

    data[user_id][
        "actions"
    ].append(entry)

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

    save_experience(data)

    # =================================================
    # 🔥 ANALYTICS
    # =====================================================

    diagnostics = analyze_execution_pattern(

        data[user_id][
            "actions"
        ]
    )

    build_execution_output_log(

        user_id,

        entry
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

        "loop_risk":
            diagnostics.get(
                "loop_risk",
                False
            ),

        "failure_pressure":
            diagnostics.get(
                "failure_pressure",
                0.0
            ),

        "stored_actions":
            len(
                data[user_id][
                    "actions"
                ]
            )
    }

# =====================================================
# 🔥 STABILIZATION SNAPSHOT
# =====================================================

def build_execution_snapshot(
    user_id
):

    """
    Executor stabilization snapshot.

    Used internally by:
    - Executor
    - Governance
    - retry protection
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

    diagnostics = analyze_execution_pattern(
        actions
    )

    return {

        "channel":
            EXECUTION_STABILIZER_RESPONSE_CHANNEL,

        "file_id":
            APRIL_FILE_ID,

        "actions":
            actions,

        "loop_risk":
            diagnostics.get(
                "loop_risk",
                False
            ),

        "failure_pressure":
            diagnostics.get(
                "failure_pressure",
                0.0
            ),

        "temporary_memory":
            True,

        "machine_only":
            True
    }
