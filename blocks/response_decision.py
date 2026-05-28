# =====================================================
# 🧠 APRIL RESPONSE DECISION ORCHESTRATOR
# =====================================================

"""
APRIL RESPONSE DECISION SYSTEM
WEB-SPACE EXECUTION ARCHITECTURE

=====================================================
ROLE
=====================================================

Этот файл является:

- lightweight orchestration layer;
- response modality selector;
- execution stabilizer;
- renderer-first decision coordinator;
- continuity-safe action router;
- machine decision bridge.

=====================================================
🔥 MAIN PURPOSE
=====================================================

Система отвечает за:

- выбор response modality;
- стабилизацию trajectory;
- renderer-first behavior;
- execution/guidance balancing;
- continuation-safe routing;
- anti-chaos orchestration;
- machine decision packaging.

=====================================================
🧠 GOLDEN APRIL CONCEPT
=====================================================

Executor НЕ принимает
финальное решение напрямую.

Executor:
- анализирует;
- координирует;
- собирает сигналы.

Response Decision:
- выбирает действие;
- определяет modality;
- стабилизирует поведение;
- подготавливает machine routing.

=====================================================
🔥 MACHINE CHANNEL ARCHITECTURE
=====================================================

INPUT MACHINE CHANNEL:
Executor → Decision Layer

OUTPUT MACHINE CHANNEL:
Decision Layer → Rooms Router

=====================================================
🔥 IMPORTANT
=====================================================

Этот слой НЕ:

- authority engine;
- renderer engine;
- cognition core;
- semantic analyzer;
- room executor;
- image generator;
- web formatter.

=====================================================
🌐 WEB-FIRST APRIL
=====================================================

Система подготовлена под:

- web orchestration;
- BotRU web pipeline;
- multimodal UI;
- renderer-safe routing;
- future cognitive rooms;
- spatial architecture.

=====================================================
🔥 GOLDEN RULE
=====================================================

Decision Layer
НЕ смешивает:

- machine routing;
- human formatting;
- renderer payloads;
- execution output.

Только routing logic.
Только orchestration.
Только decision signals.

=====================================================
"""

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

INPUT_MACHINE_CHANNEL = {

    "source": "executor_core",
    "target": "response_decision",

    "mode": "machine_input",

    "isolated": True
}

OUTPUT_MACHINE_CHANNEL = {

    "source": "response_decision",
    "target": "rooms_router",

    "mode": "machine_output",

    "isolated": True
}

# =====================================================
# 🔥 DECISION MODES
# =====================================================

DECISION_MODES = [

    "talk",
    "guide",
    "execute",
    "render",
    "generate"
]

# =====================================================
# 🔥 RESPONSE DECISION
# =====================================================

def build_response_decision(

    semantic: dict,
    cognition: dict,
    visual_reference: dict,
    state: dict

):

    """
    LIGHTWEIGHT RESPONSE DECISION

    Главная задача:
    выбрать спокойное
    trajectory-safe действие.

    Без giant orchestration.
    Без recursive chaos.
    Без duplicated logic.
    """

    semantic = semantic or {}
    cognition = cognition or {}
    visual_reference = visual_reference or {}
    state = state or {}

    active_flow = state.get(
        "active_flow"
    )

    # =================================================
    # 🔥 CORE SIGNALS
    # =====================================================

    ambiguity = semantic.get(
        "ambiguity_level",
        0.0
    )

    execution_pressure = cognition.get(
        "execution_pressure",
        0.0
    )

    wants_result = cognition.get(
        "wants_result",
        0.0
    )

    wants_visual = cognition.get(
        "wants_visual",
        0.0
    )

    assistant_restraint = cognition.get(
        "assistant_restraint",
        0.0
    )

    unresolved_intent = semantic.get(
        "unresolved_intent",
        True
    )

    goal_stage = semantic.get(
        "goal_stage",
        "exploration"
    )

    # =================================================
    # 🔥 RENDERER SIGNALS
    # =====================================================

    prefer_renderer = semantic.get(
        "prefer_renderer",
        False
    )

    render_intent = semantic.get(
        "render_intent",
        False
    )

    render_type = semantic.get(
        "render_type"
    )

    renderer_request = semantic.get(
        "renderer_request",
        False
    )

    visual_generation_needed = semantic.get(
        "visual_generation_needed",
        False
    )

    explicit_image_generation_only = semantic.get(
        "explicit_image_generation_only",
        False
    )

    avoid_image_generation_fallback = semantic.get(
        "avoid_image_generation_fallback",
        True
    )

    lightweight_visual = semantic.get(
        "visual_lightweight_mode",
        False
    )

    # =================================================
    # 🔥 EXECUTION DETECTION
    # =====================================================

    should_execute = False

    if semantic.get(
        "should_execute"
    ):

        should_execute = True

    if (

        execution_pressure >= 0.78
        and ambiguity <= 0.35

    ):

        should_execute = True

    if (

        wants_result >= 0.82
        and ambiguity <= 0.35

    ):

        should_execute = True

    # =================================================
    # 🔥 USER LEADS
    # =====================================================

    if (

        cognition.get(
            "user_leads_direction"
        )

        and cognition.get(
            "exploration_mode"
        )
    ):

        should_execute = False

    # =================================================
    # 🔥 RENDERER LOCK
    # =====================================================

    renderer_lock = bool(

        render_intent
        or prefer_renderer
        or renderer_request
        or render_type
    )

    # =================================================
    # 🔥 GENERATION LOCK
    # =====================================================

    should_generate = False

    if (

        visual_generation_needed

        and explicit_image_generation_only

        and not renderer_lock

        and not lightweight_visual

        and not avoid_image_generation_fallback

        and ambiguity <= 0.35

        and assistant_restraint < 0.7
    ):

        should_generate = True

    # =================================================
    # 🔥 RENDER DECISION
    # =====================================================

    should_render = False

    if renderer_lock:

        should_render = True

    if (

        lightweight_visual
        and not should_generate

    ):

        should_render = True

    # =================================================
    # 🔥 GUIDANCE
    # =====================================================

    should_guide = False

    if cognition.get(
        "needs_guidance"
    ):

        should_guide = True

    if cognition.get(
        "exploration_mode"
    ):

        should_guide = True

    # =================================================
    # 🔥 CONTINUATION
    # =====================================================

    should_continue = False

    if cognition.get(
        "needs_continuation"
    ):

        should_continue = True

    if active_flow:

        should_continue = True

    # =================================================
    # 🔥 FINAL ACTION
    # =====================================================

    final_action = "talk"

    if should_render:

        final_action = "render"

    elif should_generate:

        final_action = "generate"

    elif should_execute:

        final_action = "execute"

    elif should_guide:

        final_action = "guide"

    # =================================================
    # 🔥 RESPONSE MODE
    # =====================================================

    response_mode = "balanced"

    if final_action == "render":

        response_mode = "renderer_space"

    elif final_action == "generate":

        response_mode = "visual_generation"

    elif final_action == "execute":

        response_mode = "execution"

    elif final_action == "guide":

        response_mode = "guidance"

    # =================================================
    # 🔥 COMPACT MODE
    # =====================================================

    if cognition.get(
        "reduce_talking"
    ):

        response_mode = "compact"

    # =================================================
    # 🔥 EXPLORATION
    # =====================================================

    exploration_active = bool(

        cognition.get(
            "exploration_mode"
        )
    )

    # =================================================
    # 🔥 MACHINE ROUTING
    # =====================================================

    machine_routing = {

        "input_channel":

            INPUT_MACHINE_CHANNEL,

        "output_channel":

            OUTPUT_MACHINE_CHANNEL,

        "routing_mode":
            "isolated_machine_logic",

        "human_layer_allowed":
            False,

        "renderer_safe":
            True,

        "presentation_mutation_allowed":
            False
    }

    # =================================================
    # 🔥 FINAL MACHINE STATE
    # =====================================================

    result = {

        # =================================================
        # 🔥 MACHINE ROUTING
        # =====================================================

        "machine_routing":
            machine_routing,

        # =================================================
        # 🔥 ACTION
        # =====================================================

        "final_action":
            final_action,

        "response_mode":
            response_mode,

        # =================================================
        # 🔥 EXECUTION
        # =====================================================

        "should_execute":
            should_execute,

        "execution_allowed":
            should_execute,

        # =================================================
        # 🔥 RENDER
        # =====================================================

        "should_render":
            should_render,

        "render_allowed":
            should_render,

        "renderer_first_mode":
            should_render,

        "renderer_hard_lock":
            should_render,

        # =================================================
        # 🔥 GENERATION
        # =====================================================

        "should_generate":
            should_generate,

        "generation_allowed":
            should_generate,

        "avoid_heavy_generation":
            not should_generate,

        # =================================================
        # 🔥 GUIDANCE
        # =====================================================

        "should_guide":
            should_guide,

        "guidance_allowed":
            should_guide,

        # =================================================
        # 🔥 CONTINUITY
        # =====================================================

        "should_continue_trajectory":
            should_continue,

        "maintain_dialog_continuity":
            True,

        "maintain_goal_trajectory":
            True,

        # =================================================
        # 🔥 USER UNDERSTANDING
        # =====================================================

        "understands_user_goal":

            (
                wants_result >= 0.5
                or wants_visual >= 0.5
            ),

        "understands_user_direction":

            cognition.get(
                "user_leads_direction",
                False
            ),

        "should_follow_user":

            cognition.get(
                "user_leads_direction",
                False
            ),

        # =================================================
        # 🔥 RESPONSE CONTROL
        # =====================================================

        "should_reduce_talking":

            cognition.get(
                "reduce_talking",
                False
            ),

        "should_wait_for_user":

            cognition.get(
                "generation_should_wait",
                False
            ),

        "should_offer_reference":

            cognition.get(
                "prefer_reference_over_generation",
                False
            ),

        # =================================================
        # 🔥 STABILIZATION
        # =====================================================

        "trajectory_protection":
            True,

        "human_continuity":
            True,

        "avoid_trigger_behavior":
            True,

        "avoid_overthinking":
            True,

        "avoid_recursive_analysis":
            True,

        "avoid_context_rebuild":
            True,

        # =================================================
        # 🔥 SCENE
        # =====================================================

        "dialogue_still_alive":
            True,

        "goal_completed":
            False,

        "scene_practical_goal_alive":

            (
                wants_result >= 0.45
                or execution_pressure >= 0.45
            ),

        "scene_completion_required":
            unresolved_intent,

        # =================================================
        # 🔥 REFLECTION
        # =====================================================

        "needs_reflection":

            ambiguity >= 0.45,

        "needs_post_action_analysis":

            (
                should_execute
                or should_generate
                or should_render
            ),

        # =================================================
        # 🔥 SAFETY
        # =====================================================

        "high_ambiguity_detected":
            ambiguity >= 0.45,

        "response_requires_clarification":
            ambiguity >= 0.45,

        "block_image_generation_fallback":
            True,

        "allow_only_explicit_generation":
            True,

        "provider_safe_rendering":
            True,

        # =================================================
        # 🔥 WEB SPACE
        # =====================================================

        "web_space_ready":
            True,

        "botru_compatible":
            True,

        "renderer_payload_safe":
            True,

        "presentation_layer_separated":
            True,

        # =================================================
        # 🔥 MACHINE MODES
        # =====================================================

        "decision_style":
            "lightweight",

        "continuity_mode":
            "active",

        "reasoning_pressure":
            "reduced",

        "scene_priority":
            True,

        "dialog_priority":
            False,

        "exploration_active":
            exploration_active,

        "goal_stage":
            goal_stage
    }

    return result
