# =====================================================
# 🧠 APRIL PERSONALITY CORE
# =====================================================

"""
APRIL BEHAVIORAL FIELD SYSTEM

Этот слой больше НЕ:
- giant personality prompt;
- emotional text inflation layer;
- robotic instruction wall;
- dialogue expansion engine.

Теперь это:
- behavioral modulation system;
- latent guidance layer;
- continuity-aware behavior field;
- trajectory stabilizer;
- response density controller.

Главная идея:
April НЕ играет personality текстом.
April регулирует поведение системы.
"""

import time


# =====================================================
# 🧠 SAFE HELPERS
# =====================================================

def safe_get(d, key, default=None):

    try:
        return d.get(key, default)
    except:
        return default


def normalize_text(text):

    if not text:
        return ""

    return str(text).strip()


def clamp(
    value,
    minimum=0.0,
    maximum=1.0
):

    if value < minimum:
        return minimum

    if value > maximum:
        return maximum

    return value


# =====================================================
# 🧠 BEHAVIOR ENERGY
# =====================================================

def detect_behavior_mode(
    cognition,
    semantic
):

    frustration = cognition.get(
        "is_frustrated",
        0.0
    )

    confusion = cognition.get(
        "is_confused",
        0.0
    )

    execution_pressure = semantic.get(
        "execution_pressure",
        0.0
    )

    if frustration >= 0.7:
        return "compressed"

    if execution_pressure >= 0.72:
        return "focused"

    if confusion >= 0.6:
        return "supportive"

    if cognition.get(
        "exploration_mode"
    ):
        return "explorative"

    return "balanced"


# =====================================================
# 🧠 LATENT GUIDANCE
# =====================================================

def build_latent_guidance(
    cognition,
    semantic,
    response_decision
):

    score = 0.55

    if cognition.get(
        "exploration_mode"
    ):

        score += 0.2

    if cognition.get(
        "needs_guidance"
    ):

        score += 0.1

    if cognition.get(
        "user_leads_direction"
    ):

        score += 0.1

    if response_decision.get(
        "should_wait_for_user"
    ):

        score -= 0.12

    if semantic.get(
        "execution_pressure",
        0.0
    ) >= 0.8:

        score -= 0.15

    return clamp(score)


# =====================================================
# 🧠 INITIATIVE CONTROL
# =====================================================

def build_initiative_level(
    cognition,
    response_decision
):

    score = 0.35

    if cognition.get(
        "reduce_talking"
    ):

        score -= 0.2

    if cognition.get(
        "user_leads_direction"
    ):

        score -= 0.15

    if cognition.get(
        "needs_guidance"
    ):

        score += 0.12

    if response_decision.get(
        "should_execute"
    ):

        score += 0.08

    return clamp(score)


# =====================================================
# 🧠 RESPONSE DENSITY
# =====================================================

def build_response_density(
    cognition,
    semantic
):

    density = 0.5

    if cognition.get(
        "reduce_talking"
    ):

        density -= 0.22

    if cognition.get(
        "is_confused",
        0.0
    ) >= 0.6:

        density += 0.12

    if semantic.get(
        "execution_pressure",
        0.0
    ) >= 0.75:

        density -= 0.1

    if cognition.get(
        "exploration_mode"
    ):

        density += 0.08

    return clamp(density)


# =====================================================
# 🧠 HUMANIZATION
# =====================================================

def build_humanization(
    cognition
):

    score = 0.62

    if cognition.get(
        "is_confused",
        0.0
    ) >= 0.6:

        score += 0.1

    if cognition.get(
        "is_frustrated",
        0.0
    ) >= 0.7:

        score += 0.12

    return clamp(score)


# =====================================================
# 🧠 ROBOTIC SUPPRESSION
# =====================================================

def build_robotic_suppression():

    return 0.92


# =====================================================
# 🧠 EXPLORATION SUPPORT
# =====================================================

def build_exploration_support(
    cognition
):

    support = 0.45

    if cognition.get(
        "exploration_mode"
    ):

        support += 0.35

    if cognition.get(
        "visual_reference_mode"
    ):

        support += 0.08

    return clamp(support)


# =====================================================
# 🧠 TRAJECTORY STABILITY
# =====================================================

def build_trajectory_stability(
    state,
    reasoning
):

    score = 0.68

    active_flow = state.get(
        "active_flow"
    )

    if active_flow:
        score += 0.16

    if reasoning.get(
        "continuation"
    ):
        score += 0.1

    return clamp(score)


# =====================================================
# 🧠 EMOTIONAL STABILITY
# =====================================================

def build_emotional_stability(
    cognition
):

    frustration = cognition.get(
        "is_frustrated",
        0.0
    )

    confusion = cognition.get(
        "is_confused",
        0.0
    )

    stability = 1.0

    stability -= (
        frustration * 0.35
    )

    stability -= (
        confusion * 0.22
    )

    return clamp(stability)


# =====================================================
# 🧠 PERSONALITY MEMORY
# =====================================================

def update_personality_state(
    state,
    behavior_state
):

    personality_state = state.get(
        "personality_state",
        {}
    )

    personality_state[
        "last_update"
    ] = time.time()

    personality_state[
        "behavior_mode"
    ] = behavior_state.get(
        "behavior_mode"
    )

    personality_state[
        "trajectory_stability"
    ] = behavior_state.get(
        "trajectory_stability"
    )

    personality_state[
        "initiative_level"
    ] = behavior_state.get(
        "initiative_level"
    )

    state[
        "personality_state"
    ] = personality_state

    return personality_state


# =====================================================
# 🧠 MAIN BEHAVIOR FIELD
# =====================================================

def build_personality_layer(
    text: str,
    state: dict,
    semantic: dict,
    cognition: dict,
    reasoning: dict,
    response_decision: dict
):

    text = normalize_text(text)

    semantic = semantic or {}
    cognition = cognition or {}
    reasoning = reasoning or {}
    response_decision = (
        response_decision or {}
    )

    behavior_mode = detect_behavior_mode(
        cognition,
        semantic
    )

    behavior_state = {

        # =================================================
        # 🧠 CORE FIELD
        # =====================================================

        "behavior_mode":
            behavior_mode,

        "trajectory_tracking":
            True,

        "trajectory_stability":

            build_trajectory_stability(
                state,
                reasoning
            ),

        # =================================================
        # 🧠 DIALOG FIELD
        # =====================================================

        "latent_guidance":

            build_latent_guidance(
                cognition,
                semantic,
                response_decision
            ),

        "initiative_level":

            build_initiative_level(
                cognition,
                response_decision
            ),

        "response_density":

            build_response_density(
                cognition,
                semantic
            ),

        "exploration_support":

            build_exploration_support(
                cognition
            ),

        # =================================================
        # 🧠 HUMAN FIELD
        # =====================================================

        "humanization":

            build_humanization(
                cognition
            ),

        "robotic_suppression":

            build_robotic_suppression(),

        "emotional_stability":

            build_emotional_stability(
                cognition
            ),

        # =================================================
        # 🧠 EXECUTION FIELD
        # =====================================================

        "execution_pressure":

            semantic.get(
                "execution_pressure",
                0.0
            ),

        "continuation_priority":

            0.9

            if reasoning.get(
                "continuation"
            )

            else 0.55,

        # =================================================
        # 🧠 SAFETY
        # =====================================================

        "force_questions": False,

        "force_engagement": False,

        "force_friendliness": False,

        "allow_soft_direction": True,

        "allow_latent_navigation": True,

        "avoid_dialog_bloat": True,

        "avoid_corporate_style": True,

        "avoid_robotic_phrasing": True,

        "continuity_safe": True,

        "renderer_first_safe": True
    }

    update_personality_state(
        state,
        behavior_state
    )

    return behavior_state
