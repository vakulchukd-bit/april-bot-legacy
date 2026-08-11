# =====================================================
# 🧠 APRIL RESPONSE DECISION ORCHESTRATOR
# =====================================================

"""
APRIL_FILE_ID: APRIL_RESPONSE_DECISION_ORCHESTRATOR

ROLE:
response_decision_machine_layer

PURPOSE:
- response modality selection
- trajectory-safe orchestration
- renderer-first routing
- execution stabilization
- machine decision packaging
- continuation-safe coordination

INPUT:
- semantic_state
- cognition_state
- visual_reference
- active_flow
- trajectory_state

OUTPUT:
- response_decision
- machine_routing
- execution_mode
- renderer_mode
- continuation_strategy

DEPENDENCIES:
- executor_core
- semantic_core
- cognition
- excrouter
- rooms_router
- renderer_space

GOLDEN RULE:
Decision layer selects modality.
Executor executes.
Presentation formats.
"""

print("🧠 APRIL RESPONSE DECISION LOADED")


# =====================================================
# 🔥 PATCH LOG
# =====================================================

DECISION_PATCH_LOG = []


def decision_log(msg):

    try:

        print(
            "APRIL DECISION:",
            msg
        )

        DECISION_PATCH_LOG.append(
            str(msg)
        )

    except Exception:
        pass


# =====================================================
# 🔥 ENTRY / EXIT
# =====================================================

def decision_enter():

    decision_log(
        "ENTER DECISION LAYER"
    )

    return {

        "decision_active": True,

        "machine_isolation": True,

        "trajectory_safe": True
    }


def decision_exit(result):

    decision_log(
        f"EXIT DECISION: "
        f"{result.get('final_action')}"
    )

    return {

        "decision_complete": True,

        "final_action":
            result.get(
                "final_action"
            ),

        "response_mode":
            result.get(
                "response_mode"
            )
    }


# =====================================================
# 🔥 FUTURE PLACEHOLDER
# =====================================================

def decision_future(
    *args,
    **kwargs
):

    return None


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

def _base_build_response_decision(

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

    decision_enter()

    semantic = semantic or {}
    cognition = cognition or {}
    visual_reference = visual_reference or {}
    state = state or {}

    active_flow = state.get(
        "active_flow"
    )

    scene_state = state.get("scene_state", {})

    active_scene = state.get(
        "active_scene",
        {}
    )

    visual_continuity = state.get(
        "visual_continuity_summary",
        {}
    )

    # =================================================
    # 🔥 GOLDEN MEMORY DECISION INPUT
    # =====================================================

    focus_recommendation = cognition.get(
        "focus_recommendation",
        cognition.get("dynamic_focus", {})
    )

    goal_analysis = cognition.get(
        "goal_analysis",
        cognition.get("goal_hierarchy", {})
    )

    loop_analysis = cognition.get(
        "loop_analysis",
        cognition.get("open_loops", {})
    )

    memory_analysis = cognition.get(
        "memory_analysis",
        cognition.get("memory_signals", {})
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
    # 🔥 REPRESENTATION UNDERSTANDING
    # =====================================================

    representation = cognition.get(
        "representation_understanding",
        {}
    ) or semantic.get(
        "representation_understanding",
        {}
    )

    prefer_text_explanation = representation.get(
        "prefer_text_explanation",
        False
    )

    interaction_mode = representation.get(
        "interaction_mode"
    )

    requested_representation = semantic.get(
        "requested_representation"
    ) or semantic.get(
        "current_representation"
    ) or representation.get(
        "requested_representation"
    )

    preferred_representation = requested_representation or None

    # =================================================
    # 🔥 ARTIFACT UNDERSTANDING
    # =====================================================

    artifact_bundle = semantic.get(
        "artifact_bundle",
        {}
    )

    primary_artifacts = artifact_bundle.get(
        "primary",
        []
    )

    secondary_artifacts = artifact_bundle.get(
        "secondary",
        []
    )

    artifact_scene = []

    for artifact in primary_artifacts:
        artifact_scene.append(artifact)

    for artifact in secondary_artifacts:
        artifact_scene.append(artifact)




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
    # 🔥 DIALOGUE AWARENESS
    # =====================================================

    discussion_mode = semantic.get(
        "discussion_mode",
        False
    )

    reflection_mode = semantic.get(
        "reflection_mode",
        False
    )

    space_discussion = semantic.get(
        "space_discussion",
        False
    )

    tool_discussion = semantic.get(
        "tool_discussion",
        False
    )

    self_action_discussion = semantic.get(
        "self_action_discussion",
        False
    )

    explanation_mode = semantic.get(
        "explanation_mode",
        False
    )

    dialog_priority_active = bool(

        discussion_mode
        or reflection_mode
        or space_discussion
        or tool_discussion
        or self_action_discussion
        or explanation_mode

    )

    # APRIL PATCH
    if unresolved_intent:
        dialog_priority_active = True

    if preferred_representation in {"table", "graph", "diagram", "formula", "gallery", "link"}:
        # A direct representation request should not be downgraded to a plain talk reply.
        dialog_priority_active = False
        render_intent = True
        prefer_renderer = True
        renderer_request = True
        unresolved_intent = False

    # =================================================
    # 🔥 ASSISTANT TASK AWARENESS
    # =====================================================

    scene_has_visual = bool(
        visual_reference
        or visual_continuity
    )

    scene_has_active_objects = bool(
        active_scene
    )

    task_requires_clarification = False
    missing_information_type = None

    if semantic.get("needs_image") and not scene_has_visual:
        task_requires_clarification = True
        missing_information_type = "image"

    if semantic.get("needs_formula") and not semantic.get("formula_present"):
        task_requires_clarification = True
        missing_information_type = "formula"

    if semantic.get("needs_comparison") and not semantic.get("comparison_ready"):
        task_requires_clarification = True
        missing_information_type = "comparison_source"

    scene_confidence = 1.0

    if not scene_has_visual and wants_visual >= 0.5:
        scene_confidence = 0.35

    if ambiguity >= 0.45:
        scene_confidence = min(scene_confidence, 0.5)

    internal_reasoning_only = bool(
        reflection_mode
        or tool_discussion
        or self_action_discussion
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
        or preferred_representation in {"table", "graph", "diagram", "formula", "gallery", "link"}
    )

    if prefer_text_explanation:
        renderer_lock = False

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

    if task_requires_clarification:
        should_render = False

    elif renderer_lock and not dialog_priority_active:

        should_render = True

    if (

        lightweight_visual
        and not should_generate
        and not dialog_priority_active

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
    # 🔥 MEMORY TRAJECTORY PRIORITY
    # =====================================================

    if loop_analysis.get("has_open_loops"):
        should_continue = True

    if memory_analysis.get("memory_priority", 0) >= 0.7:
        should_execute = should_execute or bool(
            goal_analysis.get("strategic_goal")
        )

    if focus_recommendation.get("focus_locked"):
        should_guide = False

    # =================================================
    # 🔥 FINAL ACTION
    # =====================================================

    final_action = "talk"

    if prefer_text_explanation:

        final_action = "talk"

    elif should_render:

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
        # 🔥 APRIL FILE
        # =====================================================

        "decision_id":
            "APRIL_RESPONSE_DECISION_ORCHESTRATOR",

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

        "preferred_representation":
            preferred_representation,

        "requested_representation":
            requested_representation,

        "required_representations":
            list(
                dict.fromkeys(
                    list(semantic.get("required_representations", []))
                    + ([preferred_representation] if preferred_representation else [])
                )
            ),

        "candidate_representations":
            list(
                dict.fromkeys(
                    list(semantic.get("candidate_representations", []))
                    + ([preferred_representation] if preferred_representation else [])
                )
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
            dialog_priority_active,

        "discussion_mode":
            discussion_mode,

        "reflection_mode":
            reflection_mode,

        "space_discussion":
            space_discussion,

        "tool_discussion":
            tool_discussion,

        "self_action_discussion":
            self_action_discussion,

        "explanation_mode":
            explanation_mode,

        "exploration_active":
            exploration_active,

        "goal_stage":
            goal_stage,

        "memory_priority":
            memory_analysis.get("memory_priority", 0),

        "focus_locked":
            focus_recommendation.get("focus_locked", False),

        "has_open_loops":
            loop_analysis.get("has_open_loops", False),

        "active_scene":
            active_scene,

        "visual_continuity":
            visual_continuity,

        "scene_driven_response":
            True,

        "renderer_intelligence_enabled":
            True,

        "task_requires_clarification":
            task_requires_clarification,

        "missing_information_type":
            missing_information_type,

        "scene_confidence":
            scene_confidence,

        "scene_has_visual":
            scene_has_visual,

        "scene_has_active_objects":
            scene_has_active_objects,

        "internal_reasoning_only":
            internal_reasoning_only,

        "assistant_guidance_priority":
            task_requires_clarification or should_guide,

        # =================================================
        # 🔥 ARTIFACT SYSTEM
        # =====================================================

        "artifact_bundle":
            artifact_bundle,

        "artifact_scene":
            artifact_scene,

        "scene_composition_ready":
            len(artifact_scene) > 0
    }

    decision_exit(
        result
    )

    return result

# APRIL PATCH: internal reasoning never becomes final answer.

# =========================================================
# APRIL RESPONSE DECISION V2
# =========================================================
# Preserve the existing decision engine and enrich its final decision with the
# semantic dialogue contract.  This is not a second router.

_legacy_build_response_decision = _base_build_response_decision

def build_response_decision(semantic: dict, cognition: dict, visual_reference: dict, state: dict):
    result = _legacy_build_response_decision(
        semantic=semantic,
        cognition=cognition,
        visual_reference=visual_reference,
        state=state,
    )
    result = result if isinstance(result, dict) else {}

    contract = semantic.get("dialogue_contract", {}) if isinstance(semantic, dict) else {}
    if not isinstance(contract, dict):
        contract = {}

    dialog_act = contract.get("dialog_act", "statement")
    continuation = bool(contract.get("continuation"))
    active_goal = contract.get("active_goal") or cognition.get("active_goal")
    active_topic = contract.get("active_topic") or cognition.get("active_topic")

    if dialog_act in {"affirmation", "continuation"} and continuation:
        result["final_action"] = "talk"
        result["response_mode"] = "continuation"
        result["should_continue_trajectory"] = True
        result["maintain_dialog_continuity"] = True
    elif dialog_act == "rejection":
        result["final_action"] = "clarify"
        result["response_mode"] = "correction"
    elif dialog_act == "correction":
        result["final_action"] = "correct"
        result["response_mode"] = "correction"

    result["dialogue_contract"] = contract
    result["dialog_act"] = dialog_act
    result["reply_to"] = contract.get("reply_to")
    result["active_goal"] = active_goal
    result["active_topic"] = active_topic
    result["resolved_request"] = contract.get("resolved_request") or semantic.get("normalized_text", "")
    result["response_goal"] = active_goal or result.get("goal") or semantic.get("normalized_text", "")
    result["response_strategy"] = (
        "continue_previous_turn" if continuation else "answer_current_request"
    )
    result["avoid_machine_echo"] = True
    result["avoid_duplicate_answer"] = True
    result["single_canonical_answer"] = True
    result["context_dependency"] = (
        contract.get("context_dependency")
        or semantic.get("context_dependency")
        or ("continuation" if continuation else "independent")
    )
    result["context_policy"] = semantic.get("context_policy", {
        "current_request": True,
        "dialogue_vector": continuation,
        "previous_turn": bool(contract.get("reply_to") or contract.get("previous_april_turn")),
        "active_goal": bool(active_goal and continuation),
        "full_history": False,
    })

    return result
