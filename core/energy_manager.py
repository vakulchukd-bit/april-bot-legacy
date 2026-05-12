# =====================================================
# 🧠 APRIL ENERGY MANAGER
# =====================================================

"""
DeepHub Energy Architecture

Energy system больше НЕ работает
как trigger-based selector.

Теперь energy —
это helper-support layer
для Executor.

Energy:
- НЕ authority;
- НЕ coordinator;
- НЕ orchestration-core;
- НЕ trajectory-controller;
- НЕ room-dispatcher.

Energy помогает Executor:
- удерживать стабильность;
- замечать перегруз заранее;
- сглаживать execution pressure;
- сопровождать execution continuity;
- уменьшать overload;
- помогать response economy;
- стабилизировать execution pipeline.

Главная идея:
Energy работает
ТОЛЬКО:
- от имени Executor;
- с authority Executor;
- как helper-companion.

Rooms НЕ должны видеть
разницу между:
- Executor;
- Energy.

Для rooms:
всё должно выглядеть
как единый orchestration source.
"""


# =====================================================
# 🔥 NORMALIZE
# =====================================================

def normalize_score(
    value: float
) -> float:

    if value < 0.0:
        return 0.0

    if value > 1.0:
        return 1.0

    return value


# =====================================================
# 🔥 ENERGY LEVEL
# =====================================================

def resolve_energy_level(
    score: float
) -> str:

    if score >= 0.72:
        return "HIGH"

    if score <= 0.35:
        return "LOW"

    return "MEDIUM"


# =====================================================
# 🔥 OVERLOAD STATE
# =====================================================

def detect_overload_state(
    semantic: dict = None,
    cognition: dict = None,
    response_decision: dict = None,
    state: dict = None
) -> dict:

    semantic = semantic or {}
    cognition = cognition or {}
    response_decision = response_decision or {}
    state = state or {}

    overload_score = 0.0

    execution_pressure = semantic.get(
        "execution_pressure",
        0.0
    )

    dialog_fatigue = cognition.get(
        "dialog_fatigue",
        0.0
    )

    frustration = cognition.get(
        "is_frustrated",
        0.0
    )

    restraint = cognition.get(
        "assistant_restraint",
        0.0
    )

    if execution_pressure >= 0.8:

        overload_score += 0.35

    elif execution_pressure >= 0.6:

        overload_score += 0.2

    if dialog_fatigue >= 0.7:

        overload_score += 0.25

    if frustration >= 0.7:

        overload_score += 0.15

    if cognition.get(
        "prefer_execution"
    ):

        overload_score += 0.1

    if response_decision.get(
        "final_action"
    ) == "execute":

        overload_score += 0.1

    if restraint >= 0.7:

        overload_score -= 0.15

    overload_score = normalize_score(
        overload_score
    )

    predicted_overload = (
        overload_score >= 0.72
    )

    return {

        "overload_score": overload_score,

        "predicted_overload": predicted_overload,

        "should_warn_executor": (
            overload_score >= 0.58
        ),

        "should_prepare_support": (
            overload_score >= 0.45
        ),

        "should_reduce_execution_noise": (
            overload_score >= 0.55
        ),

        "should_stabilize_pipeline": (
            overload_score >= 0.65
        )
    }


# =====================================================
# 🔥 EXECUTION SUPPORT
# =====================================================

def build_execution_support(
    semantic: dict = None,
    cognition: dict = None,
    response_decision: dict = None,
    overload_state: dict = None
) -> dict:

    semantic = semantic or {}
    cognition = cognition or {}
    response_decision = response_decision or {}
    overload_state = overload_state or {}

    support = {

        # =================================================
        # 🔥 SUPPORT ROLE
        # =================================================

        "energy_is_helper": True,

        "energy_has_no_authority": True,

        "energy_supports_executor": True,

        "executor_remains_primary": True,

        # =================================================
        # 🔥 SUPPORT MODES
        # =================================================

        "assist_execution": False,

        "assist_stability": False,

        "assist_response_economy": False,

        "assist_pipeline_balance": False,

        "assist_retry_stability": False,

        "assist_execution_queue": False,

        # =================================================
        # 🔥 SAFETY
        # =================================================

        "can_override_executor": False,

        "can_change_trajectory": False,

        "can_route_rooms": False,

        "can_change_scene": False,

        "can_change_intent": False,

        # =================================================
        # 🔥 PIPELINE SUPPORT
        # =================================================

        "prepare_lightweight_mode": False,

        "prepare_safe_execution": False,

        "prepare_low_noise_mode": False,

        "prepare_stable_transition": False,

        # =================================================
        # 🔥 EXECUTION HELP
        # =================================================

        "support_heavy_execution": False,

        "support_parallel_pressure": False,

        "support_large_context": False,

        "support_long_dialog": False,

        "support_visual_pipeline": False
    }

    if overload_state.get(
        "should_prepare_support"
    ):

        support[
            "assist_execution"
        ] = True

        support[
            "assist_pipeline_balance"
        ] = True

        support[
            "assist_execution_queue"
        ] = True

    if overload_state.get(
        "should_reduce_execution_noise"
    ):

        support[
            "assist_response_economy"
        ] = True

        support[
            "prepare_low_noise_mode"
        ] = True

    if overload_state.get(
        "should_stabilize_pipeline"
    ):

        support[
            "assist_stability"
        ] = True

        support[
            "assist_retry_stability"
        ] = True

        support[
            "prepare_safe_execution"
        ] = True

        support[
            "prepare_stable_transition"
        ] = True

    if semantic.get(
        "execution_pressure",
        0.0
    ) >= 0.7:

        support[
            "support_heavy_execution"
        ] = True

    if cognition.get(
        "dialog_fatigue",
        0.0
    ) >= 0.6:

        support[
            "support_long_dialog"
        ] = True

    if cognition.get(
        "prefer_visual"
    ):

        support[
            "support_visual_pipeline"
        ] = True

    return support


# =====================================================
# 🔥 EXECUTION COMPANION
# =====================================================

def build_energy_companion_state(
    semantic: dict = None,
    cognition: dict = None,
    response_decision: dict = None,
    state: dict = None
) -> dict:

    overload_state = detect_overload_state(

        semantic=semantic,

        cognition=cognition,

        response_decision=response_decision,

        state=state
    )

    support = build_execution_support(

        semantic=semantic,

        cognition=cognition,

        response_decision=response_decision,

        overload_state=overload_state
    )

    return {

        "helper_mode": True,

        "executor_companion": True,

        "authority_locked_to_executor": True,

        "rooms_should_see_single_authority": True,

        "overload_state": overload_state,

        "support": support
    }


# =====================================================
# 🔥 DETECT ENERGY
# =====================================================

def detect_energy(
    text: str,
    intent: str = None,
    room: str = None,
    semantic: dict = None,
    cognition: dict = None,
    response_decision: dict = None
) -> str:

    t = (text or "").lower()

    semantic = semantic or {}
    cognition = cognition or {}
    response_decision = response_decision or {}

    # =================================================
    # 🔥 BASE
    # =================================================

    energy_score = 0.5

    # =================================================
    # 🧠 EXECUTION PRESSURE
    # =================================================

    execution_pressure = semantic.get(
        "execution_pressure",
        0.0
    )

    if execution_pressure >= 0.75:

        energy_score += 0.35

    elif execution_pressure >= 0.45:

        energy_score += 0.15

    # =================================================
    # 🧠 USER WANTS RESULT
    # =================================================

    if cognition.get(
        "wants_result",
        0.0
    ) >= 0.7:

        energy_score += 0.2

    # =================================================
    # 🧠 EXPLORATION MODE
    # =================================================

    if cognition.get(
        "exploration_mode"
    ):

        energy_score -= 0.25

    # =================================================
    # 🧠 USER LEADS DIRECTION
    # =================================================

    if cognition.get(
        "user_leads_direction"
    ):

        energy_score -= 0.15

    # =================================================
    # 🧠 RESTRAINT
    # =================================================

    restraint = cognition.get(
        "assistant_restraint",
        0.0
    )

    if restraint >= 0.7:

        energy_score -= 0.25

    elif restraint >= 0.4:

        energy_score -= 0.1

    # =================================================
    # 🧠 GUIDANCE MODE
    # =================================================

    if cognition.get(
        "needs_guidance"
    ):

        energy_score -= 0.1

    # =================================================
    # 🧠 FRUSTRATION
    # =================================================

    if cognition.get(
        "is_frustrated",
        0.0
    ) >= 0.7:

        energy_score -= 0.15

    # =================================================
    # 🧠 DIALOG FATIGUE
    # =================================================

    if cognition.get(
        "dialog_fatigue",
        0.0
    ) >= 0.7:

        energy_score -= 0.2

    # =================================================
    # 🧠 RESPONSE DECISION
    # =================================================

    final_action = response_decision.get(
        "final_action",
        "talk"
    )

    if final_action == "execute":

        energy_score += 0.2

    elif final_action == "guide":

        energy_score -= 0.1

    elif final_action == "reference":

        energy_score -= 0.15

    elif final_action == "wait":

        energy_score -= 0.25

    # =================================================
    # 🧠 VISUAL EXPLORATION
    # =================================================

    if cognition.get(
        "prefer_reference_over_generation"
    ):

        energy_score -= 0.2

    # =================================================
    # 🧠 CONTINUATION
    # =================================================

    if semantic.get(
        "continuation"
    ):

        energy_score += 0.05

    # =================================================
    # 🧠 LONG EXPLANATION REQUEST
    # =================================================

    detailed_words = [

        "подробно",
        "развернуто",
        "глубже",
        "объясни"
    ]

    if any(
        w in t
        for w in detailed_words
    ):

        energy_score += 0.15

    # =================================================
    # 🧠 SHORT RESPONSE REQUEST
    # =================================================

    short_words = [

        "кратко",
        "быстро",
        "коротко"
    ]

    if any(
        w in t
        for w in short_words
    ):

        energy_score -= 0.25

    # =================================================
    # 🧠 HARD EXECUTION SIGNALS
    # =================================================

    hard_execution_words = [

        "сделай",
        "выполни",
        "создай",
        "построй"
    ]

    if any(
        w in t
        for w in hard_execution_words
    ):

        energy_score += 0.15

    # =================================================
    # 🔥 NORMALIZATION
    # =================================================

    energy_score = normalize_score(
        energy_score
    )

    # =================================================
    # 🔥 FINAL ENERGY
    # =================================================

    return resolve_energy_level(
        energy_score
    )


# =====================================================
# 🔥 SUBSCRIPTION LIMITS
# =====================================================

def apply_subscription_limit(
    energy: str,
    plan: str
) -> str:

    limits = {

        "free": [
            "LOW"
        ],

        "lite": [
            "LOW",
            "MEDIUM"
        ],

        "premium": [
            "LOW",
            "MEDIUM",
            "HIGH"
        ]
    }

    allowed = limits.get(
        plan,
        ["LOW"]
    )

    if energy in allowed:

        return energy

    if "MEDIUM" in allowed:

        return "MEDIUM"

    return "LOW"
