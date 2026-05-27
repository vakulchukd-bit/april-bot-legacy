import json
import os
import time

# =====================================================
# 🧠 APRIL EXECUTION STABILIZER
# =====================================================

"""
APRIL EXECUTION STABILIZER

Modern DeepHub version.

Этот слой:

✅ temporary execution continuity
✅ anti-loop protection
✅ retry suppression
✅ renderer stabilization
✅ modality cooldown support
✅ lightweight execution continuity

❌ НЕ execution memory
❌ НЕ routing memory
❌ НЕ trajectory memory
❌ НЕ cognition helper
❌ НЕ orchestration authority
❌ НЕ retry chaos system

Главная задача:

не мешать executor,
не копить noise,
не дублировать orchestration,
не хранить history,
а помогать calm execution continuity.
"""

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

    НЕ копим history.
    НЕ копим old retries.
    НЕ копим execution noise.

    Храним только
    короткий stabilization window.
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

    ВАЖНО:
    state НЕ должен
    превращаться в cognition memory.
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
    short temporary buffer
    """

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

        return

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
