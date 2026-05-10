# =====================================================
# 🧠 APRIL ENERGY MANAGER
# =====================================================

"""
Energy system больше НЕ работает
как trigger-based selector.

Теперь energy —
это внутреннее cognitive состояние April.

Он учитывает:

- trajectory;
- exploration;
- frustration;
- execution pressure;
- guidance;
- restraint;
- continuation;
- dialog fatigue;
- user direction.

Цель:
не разгонять модель без причины,
не ломать психологию диалога,
не провоцировать trigger behavior.
"""


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

        # 🔥 exploration не требует
        # aggressive HIGH energy

        energy_score -= 0.25

    # =================================================
    # 🧠 USER LEADS DIRECTION
    # =================================================

    if cognition.get(
        "user_leads_direction"
    ):

        # 🔥 меньше давления,
        # больше слушания

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

        # 🔥 не разгоняем болтовню

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
    # 🧠 NORMALIZATION
    # =================================================

    if energy_score < 0.0:

        energy_score = 0.0

    if energy_score > 1.0:

        energy_score = 1.0

    # =================================================
    # 🔥 FINAL ENERGY
    # =================================================

    if energy_score >= 0.72:

        return "HIGH"

    if energy_score <= 0.35:

        return "LOW"

    return "MEDIUM"


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
