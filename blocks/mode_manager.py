# =====================================================
# 🧠 APRIL MODE MANAGER
# =====================================================

"""
APRIL MODE MANAGER
LIGHTWEIGHT EXECUTION STATE LAYER

=====================================================

Этот модуль больше НЕ:
- telegram mode switcher;
- hard routing authority;
- global execution override;
- legacy FSM storage.

=====================================================

Этот модуль теперь:
- lightweight mode continuity layer;
- temporary execution state holder;
- orchestration-safe mode tracker;
- executor-compatible state helper;
- trajectory-safe context bridge.

=====================================================

APRIL PRINCIPLES:

1. mode != authority
2. executor decides
3. no hidden routing
4. no telegram FSM assumptions
5. temporary continuity only
6. lightweight stabilization
7. orchestration-safe behavior
"""

print("🧠 APRIL MODE MANAGER LOADED")

# =====================================================
# 🔥 APRIL FILE ID
# =====================================================

APRIL_FILE_ID = "APRIL_MODE_MANAGER"

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

INPUT_MACHINE_CHANNEL = {

    "source": "executor",
    "type": "mode_machine_input",
    "isolated": True
}

OUTPUT_MACHINE_CHANNEL = {

    "target": "executor_mode_pipeline",
    "type": "mode_machine_output",
    "isolated": True
}

# =====================================================
# 🔥 SAFE PATCH MODE
# =====================================================

PATCH_LOG = []


def safe_patch_log(msg):

    try:

        print(
            "MODE MANAGER PATCH:",
            msg
        )

        PATCH_LOG.append(msg)

    except Exception:
        pass


# =====================================================
# 🔥 MODE STORAGE
# =====================================================

"""
ВАЖНО:

Это НЕ long-term memory.
Это НЕ cognition storage.
Это НЕ orchestration authority.

Только lightweight temporary continuity.
"""

_modes = {}

# =====================================================
# 🔥 SAFE NORMALIZATION
# =====================================================

def normalize_mode(
    mode
):

    if mode is None:
        return None

    return str(mode).strip().lower()


# =====================================================
# 🔥 MACHINE PACKAGE
# =====================================================

def build_mode_state(
    mode
):

    normalized = normalize_mode(
        mode
    )

    return {

        "mode":
            normalized,

        "temporary":
            True,

        "continuity_safe":
            True,

        "executor_aware":
            True,

        "machine_state":
            True,

        "orchestration_safe":
            True
    }


# =====================================================
# 🔥 SET MODE
# =====================================================

def set_mode(
    user_id,
    mode
):

    normalized = normalize_mode(
        mode
    )

    safe_patch_log(

        f"SET MODE: "
        f"{user_id} -> {normalized}"
    )

    _modes[
        str(user_id)
    ] = build_mode_state(
        normalized
    )


# =====================================================
# 🔥 GET MODE
# =====================================================

def get_mode(
    user_id
):

    state = _modes.get(
        str(user_id)
    )

    if not state:
        return None

    return state.get(
        "mode"
    )


# =====================================================
# 🔥 GET FULL MODE STATE
# =====================================================

def get_mode_state(
    user_id
):

    return _modes.get(
        str(user_id)
    )


# =====================================================
# 🔥 CLEAR MODE
# =====================================================

def clear_mode(
    user_id
):

    safe_patch_log(
        f"CLEAR MODE: {user_id}"
    )

    _modes.pop(
        str(user_id),
        None
    )


# =====================================================
# 🔥 HAS MODE
# =====================================================

def has_mode(
    user_id
):

    return (
        str(user_id)
        in _modes
    )


# =====================================================
# 🔥 SAFE MODE CHECK
# =====================================================

def is_mode(
    user_id,
    mode
):

    current = get_mode(
        user_id
    )

    normalized = normalize_mode(
        mode
    )

    return current == normalized


# =====================================================
# 🔥 EXECUTION CONTINUITY
# =====================================================

def build_executor_mode_context(
    user_id
):

    state = get_mode_state(
        user_id
    )

    if not state:

        return {

            "mode_active": False,

            "continuity_safe": True
        }

    return {

        "mode_active": True,

        "mode":
            state.get(
                "mode"
            ),

        "temporary":
            state.get(
                "temporary",
                True
            ),

        "continuity_safe":
            state.get(
                "continuity_safe",
                True
            ),

        "executor_aware":
            state.get(
                "executor_aware",
                True
            ),

        "machine_state":
            True
    }
