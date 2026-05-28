# =====================================================
# 🧠 APRIL ENERGY POLICY CORE
# =====================================================

"""
APRIL ENERGY POLICY CORE

APRIL_FILE_ID:
APRIL_ENERGY_POLICY_CORE

ROLE:
EXECUTION_ENERGY_COORDINATOR

INPUT:
USER_ID
SUBSCRIPTION_PLAN
EXECUTOR_REQUEST

OUTPUT:
ENERGY_LEVEL
EXECUTION_PRIORITY
RESOURCE_PROFILE

THIS FILE IS:
- execution energy layer
- lightweight policy helper
- subscription execution mapper
- admin bypass authority

THIS FILE IS NOT:
- billing system
- payment authority
- orchestration engine
- frontend logic
- telegram system

GOLDEN APRIL PRINCIPLES:
- lightweight execution
- centralized energy policy
- executor-safe architecture
- admin-safe bypass
- no duplicated subscription logic
"""

# =====================================================
# 🔥 IMPORTS
# =====================================================

from storage import (
    get_user_plan
)

# =====================================================
# 🔥 CENTRAL CONFIG
# =====================================================

"""
ADMIN_ID берётся только
из централизованного config.

Это сохраняет:
- unified authority
- stable governance
- admin consistency
"""

from blocks.tariffs_config import (
    ADMIN_ID
)

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

ENERGY_TASK_CHANNEL = {

    "channel":
        "energy_policy_task_channel",

    "isolated":
        True
}

ENERGY_RESPONSE_CHANNEL = {

    "channel":
        "energy_policy_response_channel",

    "isolated":
        True
}

# =====================================================
# 🔥 ENERGY MAP
# =====================================================

ENERGY_LEVELS = {

    "free":
        "LOW",

    "lite":
        "MEDIUM",

    "premium":
        "HIGH"
}

# =====================================================
# 🔥 EXECUTION PROFILES
# =====================================================

EXECUTION_PROFILES = {

    "LOW": {

        "renderer_priority":
            False,

        "heavy_generation":
            False,

        "context_depth":
            "minimal"
    },

    "MEDIUM": {

        "renderer_priority":
            True,

        "heavy_generation":
            False,

        "context_depth":
            "balanced"
    },

    "HIGH": {

        "renderer_priority":
            True,

        "heavy_generation":
            True,

        "context_depth":
            "extended"
    }
}

# =====================================================
# 🔥 ANALYZER LOGGING
# =====================================================

def log_energy_input(
    user_id
):

    """
    INPUT MACHINE TRACE

    Used by:
    - analyzer
    - admin monitoring
    - execution diagnostics
    """

    return {

        "file_id":
            "APRIL_ENERGY_POLICY_CORE",

        "event":
            "energy_input",

        "channel":
            ENERGY_TASK_CHANNEL,

        "user_id":
            str(user_id),

        "machine_only":
            True
    }


def log_energy_output(
    user_id,
    energy
):

    """
    OUTPUT MACHINE TRACE

    Used by:
    - analyzer
    - execution tracing
    - resource diagnostics
    """

    return {

        "file_id":
            "APRIL_ENERGY_POLICY_CORE",

        "event":
            "energy_output",

        "channel":
            ENERGY_RESPONSE_CHANNEL,

        "user_id":
            str(user_id),

        "energy":
            energy,

        "machine_only":
            True
    }

# =====================================================
# 🔥 ENERGY RESOLUTION
# =====================================================

def get_energy(user_id):

    """
    Returns execution energy level:

    LOW
    MEDIUM
    HIGH

    Executor uses this helper core
    to stabilize execution scale.
    """

    log_energy_input(user_id)

    # =================================================
    # 👑 ADMIN BYPASS
    # =====================================================

    if user_id == ADMIN_ID:

        energy = "HIGH"

        log_energy_output(
            user_id,
            energy
        )

        return energy

    # =================================================
    # 🔥 USER PLAN
    # =====================================================

    plan = get_user_plan(
        user_id
    )

    energy = ENERGY_LEVELS.get(
        plan,
        "LOW"
    )

    log_energy_output(
        user_id,
        energy
    )

    return energy

# =====================================================
# 🔥 EXECUTION PROFILE
# =====================================================

def build_energy_execution_profile(
    user_id
):

    """
    Lightweight execution profile
    for Executor coordination.

    NEVER exposed directly
    to frontend/users.
    """

    energy = get_energy(
        user_id
    )

    profile = EXECUTION_PROFILES.get(
        energy,
        EXECUTION_PROFILES["LOW"]
    )

    return {

        "channel":
            ENERGY_RESPONSE_CHANNEL,

        "file_id":
            "APRIL_ENERGY_POLICY_CORE",

        "energy":
            energy,

        "execution_profile":
            profile,

        "machine_only":
            True
    }
