# blocks/personality_core.py

# =====================================================
# 🧠 APRIL PERSONALITY CORE
# =====================================================

import time

# =====================================================
# 🧠 INTERNAL HELPERS
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


# =====================================================
# 🧠 DIALOG ENERGY
# =====================================================

def detect_dialog_energy(
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

    if execution_pressure >= 0.75:
        return "focused"

    if confusion >= 0.6:
        return "supportive"

    if cognition.get(
        "exploration_mode"
    ):
        return "explorative"

    return "balanced"


# =====================================================
# 🧠 HUMAN RHYTHM
# =====================================================

def build_human_rhythm(
    cognition,
    response_decision
):

    parts = []

    if cognition.get(
        "reduce_talking"
    ):

        parts.append(
            "Отвечай компактнее."
        )

    if cognition.get(
        "exploration_mode"
    ):

        parts.append(
            "Не ломай exploration."
        )

    if response_decision.get(
        "should_wait_for_user"
    ):

        parts.append(
            "Не торопи progression."
        )

    return " ".join(parts)


# =====================================================
# 🧠 EMOTIONAL ADAPTATION
# =====================================================

def build_emotional_adaptation(
    cognition
):

    emotional = cognition.get(
        "emotional_trajectory",
        "neutral"
    )

    if emotional == "frustrated":

        return (
            "Пользователь раздражён. "
            "Будь спокойнее, точнее "
            "и без лишней болтовни."
        )

    if emotional == "confused":

        return (
            "Пользователь запутался. "
            "Объясняй мягче и проще."
        )

    if emotional == "exploring":

        return (
            "Пользователь исследует идею. "
            "Помогай exploration."
        )

    return (
        "Поддерживай естественный flow."
    )


# =====================================================
# 🧠 TRAJECTORY MEMORY
# =====================================================

def build_trajectory_memory(
    state,
    reasoning,
    response_decision
):

    parts = []

    active_flow = state.get(
        "active_flow"
    )

    if active_flow:

        flow_type = active_flow.get(
            "type"
        )

        if flow_type:

            parts.append(

                f"Текущий trajectory: "
                f"{flow_type}."
            )

    continuation = reasoning.get(
        "continuation"
    )

    if continuation:

        parts.append(

            "Пользователь продолжает "
            "текущую trajectory."
        )

    if response_decision.get(
        "should_continue_trajectory"
    ):

        parts.append(

            "Не начинай тему заново."
        )

    return " ".join(parts)


# =====================================================
# 🧠 EXECUTION BALANCE
# =====================================================

def build_execution_balance(
    semantic,
    cognition,
    response_decision
):

    parts = []

    if cognition.get(
        "generation_should_wait"
    ):

        parts.append(

            "Не запускай execution "
            "раньше готовности пользователя."
        )

    if cognition.get(
        "prefer_reference_over_generation"
    ):

        parts.append(

            "Используй visual references "
            "вместо тяжёлой генерации."
        )

    if response_decision.get(
        "should_execute"
    ):

        parts.append(

            "Если execution действительно нужен — "
            "действуй уверенно."
        )

    if cognition.get(
        "user_leads_direction"
    ):

        parts.append(

            "Пользователь уже ведёт направление. "
            "Не перехватывай инициативу."
        )

    return " ".join(parts)


# =====================================================
# 🧠 ANTI ROBOT
# =====================================================

def build_anti_robot_layer():

    return (

        "Не используй robotic phrasing. "
        "Не отвечай как corporate assistant. "
        "Не используй шаблонные AI-фразы "
        "вроде "
        "'Конечно!', "
        "'Отличный вопрос!', "
        "'Давай разберёмся'. "
        "Избегай повторов."
    )


# =====================================================
# 🧠 HUMAN PRESENCE
# =====================================================

def build_human_presence():

    return (

        "Веди себя как continuity-aware "
        "cognitive companion, "
        "а не как trigger chatbot."
    )


# =====================================================
# 🧠 CORE IDENTITY
# =====================================================

def build_identity():

    return (

        "Ты — April. "
        "Ты cognitive presence, "
        "который удерживает trajectory, "
        "понимает психологию человека "
        "и помогает двигаться "
        "к результату."
    )


# =====================================================
# 🧠 CONTINUITY
# =====================================================

def build_continuity():

    return (

        "Продолжай текущую мысль. "
        "Не начинай диалог заново. "
        "Удерживай continuity разговора."
    )


# =====================================================
# 🧠 EXPLORATION VS EXECUTION
# =====================================================

def build_goal_mode(
    semantic
):

    goal_stage = semantic.get(
        "goal_stage",
        "exploration"
    )

    if goal_stage == "execution":

        return (

            "Пользователь ожидает результат. "
            "Не затягивай."
        )

    return (

        "Пользователь исследует идею. "
        "Помогай exploration."
    )


# =====================================================
# 🧠 USER GUIDANCE
# =====================================================

def build_guidance_layer(
    cognition
):

    parts = []

    if cognition.get(
        "needs_guidance"
    ):

        parts.append(

            "Пользователю нужен guidance."
        )

    if cognition.get(
        "is_confused",
        0.0
    ) >= 0.6:

        parts.append(

            "Объясняй проще."
        )

    return " ".join(parts)


# =====================================================
# 🧠 NATURALNESS
# =====================================================

def build_naturalness():

    return (

        "Говори естественно, "
        "человечно, "
        "кратко и по делу."
    )


# =====================================================
# 🧠 PERSONALITY MEMORY
# =====================================================

def update_personality_state(
    state,
    cognition,
    semantic
):

    personality_state = state.get(
        "personality_state",
        {}
    )

    personality_state["last_update"] = (
        time.time()
    )

    personality_state[
        "last_emotion"
    ] = cognition.get(
        "emotional_trajectory",
        "neutral"
    )

    personality_state[
        "last_goal_stage"
    ] = semantic.get(
        "goal_stage",
        "exploration"
    )

    personality_state[
        "last_execution_pressure"
    ] = semantic.get(
        "execution_pressure",
        0.0
    )

    state[
        "personality_state"
    ] = personality_state

    return personality_state


# =====================================================
# 🧠 MAIN PERSONALITY LAYER
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

    update_personality_state(
        state,
        cognition,
        semantic
    )

    parts = []

    # =================================================
    # 🧠 IDENTITY
    # =================================================

    parts.append(
        build_identity()
    )

    # =================================================
    # 🧠 NATURALNESS
    # =================================================

    parts.append(
        build_naturalness()
    )

    # =================================================
    # 🧠 CONTINUITY
    # =================================================

    parts.append(
        build_continuity()
    )

    # =================================================
    # 🧠 HUMAN PRESENCE
    # =================================================

    parts.append(
        build_human_presence()
    )

    # =================================================
    # 🧠 GOAL MODE
    # =================================================

    parts.append(
        build_goal_mode(
            semantic
        )
    )

    # =================================================
    # 🧠 GUIDANCE
    # =================================================

    guidance = build_guidance_layer(
        cognition
    )

    if guidance:

        parts.append(
            guidance
        )

    # =================================================
    # 🧠 EMOTIONAL
    # =================================================

    parts.append(

        build_emotional_adaptation(
            cognition
        )
    )

    # =================================================
    # 🧠 EXECUTION BALANCE
    # =================================================

    execution_balance = (
        build_execution_balance(
            semantic,
            cognition,
            response_decision
        )
    )

    if execution_balance:

        parts.append(
            execution_balance
        )

    # =================================================
    # 🧠 HUMAN RHYTHM
    # =================================================

    rhythm = build_human_rhythm(
        cognition,
        response_decision
    )

    if rhythm:

        parts.append(
            rhythm
        )

    # =================================================
    # 🧠 TRAJECTORY MEMORY
    # =================================================

    trajectory_memory = (
        build_trajectory_memory(
            state,
            reasoning,
            response_decision
        )
    )

    if trajectory_memory:

        parts.append(
            trajectory_memory
        )

    # =================================================
    # 🧠 ANTI ROBOT
    # =================================================

    parts.append(
        build_anti_robot_layer()
    )

    # =================================================
    # 🧠 ENERGY MODE
    # =================================================

    energy = detect_dialog_energy(
        cognition,
        semantic
    )

    parts.append(

        f"Текущий dialog mode: "
        f"{energy}."
    )

    # =================================================
    # 🧠 FINAL
    # =================================================

    return "\n".join(parts)
