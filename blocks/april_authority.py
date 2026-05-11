# =====================================================
# 🧠 APRIL AUTHORITY SYSTEM
# =====================================================

"""
April Supreme Authority Layer

Этот модуль является:
- финальной cognitive authority;
- системой override;
- системой trust;
- системой capability ownership;
- финальной validation системой.

Rooms,
executor,
routing,
semantic systems —
не являются финальной властью.

Final authority принадлежит April.
"""

# =====================================================
# 🔥 CAPABILITY REGISTRY
# =====================================================

APRIL_CAPABILITIES = {

    "text": True,

    "image_generation": True,

    "image_edit": True,

    "image_analysis": True,

    "science": True,

    "graphs": True,

    "web": True,

    "code": True,

    "reasoning": True
}

# =====================================================
# 🔥 TRUST STATE
# =====================================================

DEFAULT_TRUST_LEVELS = {

    "text": 1.0,

    "image_generation": 1.0,

    "image_edit": 1.0,

    "image_analysis": 1.0,

    "science": 1.0,

    "graphs": 1.0,

    "web": 1.0,

    "code": 1.0
}

# =====================================================
# 🔥 AUTHORITY STATE
# =====================================================

def build_authority_state():

    return {

        "authority_active": True,

        "override_allowed": True,

        "direct_capability_access": True,

        "final_validation": True,

        "trust_levels":
            DEFAULT_TRUST_LEVELS.copy(),

        "last_override": None,

        "last_success": None,

        "last_failure": None
    }

# =====================================================
# 🔥 INTENTION CONFIDENCE
# =====================================================

def evaluate_intention_confidence(

    semantic,
    cognition,
    response_decision

):

    confidence = 0.0

    semantic = semantic or {}
    cognition = cognition or {}
    response_decision = response_decision or {}

    # =================================================
    # 🔥 EXECUTION PRESSURE
    # =================================================

    confidence += cognition.get(
        "wants_result",
        0.0
    ) * 0.3

    confidence += cognition.get(
        "wants_visual",
        0.0
    ) * 0.2

    # =================================================
    # 🔥 USER DIRECTION
    # =================================================

    if cognition.get(
        "user_leads_direction"
    ):

        confidence += 0.2

    # =================================================
    # 🔥 EXECUTION
    # =================================================

    if semantic.get(
        "should_execute"
    ):

        confidence += 0.3

    # =================================================
    # 🔥 AMBIGUITY
    # =================================================

    ambiguity = semantic.get(
        "ambiguity_level",
        0.0
    )

    confidence -= ambiguity * 0.4

    return max(
        0.0,
        min(confidence, 1.0)
    )

# =====================================================
# 🔥 FINAL VALIDATION
# =====================================================

def validate_final_response(

    result,
    semantic,
    cognition

):

    if not result:
        return False

    output = str(
        result.get("data", "")
    ).strip()

    if len(output) <= 5:
        return False

    bad_patterns = [

        "я не могу",

        "я не умею",

        "представь себе",

        "не поддерживается"
    ]

    lowered = output.lower()

    for pattern in bad_patterns:

        if pattern in lowered:

            return False

    return True

# =====================================================
# 🔥 OVERRIDE DECISION
# =====================================================

def should_override(

    result,
    semantic,
    cognition,
    response_decision

):

    valid = validate_final_response(

        result,
        semantic,
        cognition
    )

    if not valid:
        return True

    confidence = evaluate_intention_confidence(

        semantic,
        cognition,
        response_decision
    )

    if confidence >= 0.75:

        if result.get("type") == "text":

            if cognition.get(
                "wants_visual",
                0.0
            ) >= 0.7:

                return True

    return False
