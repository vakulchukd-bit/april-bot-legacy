# =====================================================
# 🧠 APRIL REASONING STATE
# =====================================================

"""
APRIL_FILE_ID: APRIL_REASONING_STATE

ROLE:
trajectory_reasoning_layer

PURPOSE:
- lightweight reasoning state
- continuity stabilization
- trajectory preservation
- execution readiness tracking
- scene continuity support
- reflection minimization

INPUT:
- user_text
- semantic_state
- scene_state
- dialog_state
- active_flow

OUTPUT:
- reasoning_state
- trajectory_state
- execution_readiness
- continuity_snapshot

DEPENDENCIES:
- semantic_core
- cognition
- scene_state
- active_flow
- executor
- excrouter

GOLDEN RULE:
Reasoning tracks direction.
Cognition decides.
"""

print("🧠 APRIL REASONING STATE LOADED")


# =====================================================
# 🔥 PATCH LOG
# =====================================================

REASONING_PATCH_LOG = []


def reasoning_log(msg):

    try:

        print(
            "APRIL REASONING:",
            msg
        )

        REASONING_PATCH_LOG.append(
            str(msg)
        )

    except Exception:
        pass


# =====================================================
# 🔥 ENTRY / EXIT
# =====================================================

def reasoning_enter(
    text
):

    reasoning_log(

        f"ENTER REASONING: "
        f"{str(text)[:80]}"
    )

    return {

        "reasoning_active": True,

        "continuity_safe": True,

        "trajectory_tracking": True
    }


def reasoning_exit(
    reasoning_state
):

    reasoning_log(
        "EXIT REASONING"
    )

    return {

        "reasoning_complete": True,

        "trajectory_active":

            reasoning_state.get(
                "trajectory_active",
                False
            ),

        "execution_ready":

            reasoning_state.get(
                "execution_ready",
                False
            )
    }


# =====================================================
# 🔥 FUTURE PLACEHOLDER
# =====================================================

def reasoning_future(
    *args,
    **kwargs
):

    return None


def _as_dict(value):
    return value if isinstance(value, dict) else {}


def _as_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _text(value, limit=5000):
    return str(value or "").strip()[:limit]


def _scene_evidence(state, semantic):
    state = state if isinstance(state, dict) else {}
    semantic = semantic if isinstance(semantic, dict) else {}
    blueprint = _as_dict(
        semantic.get("scene_blueprint")
        or _as_dict(semantic.get("semantic_scene")).get("blueprint")
        or state.get("scene_blueprint")
        or _as_dict(state.get("active_scene")).get("scene_blueprint")
    )
    representations = []
    for value in _as_list(
        blueprint.get("representations")
        or semantic.get("scene_representations")
        or _as_dict(semantic.get("semantic_scene")).get("representations")
    ):
        value = _text(value, 80).lower()
        if value and value not in representations:
            representations.append(value)

    nodes = [dict(item) for item in _as_list(
        blueprint.get("nodes") or semantic.get("scene_nodes")
    ) if isinstance(item, dict)]
    relations = [dict(item) for item in _as_list(
        blueprint.get("relations") or semantic.get("scene_relations")
    ) if isinstance(item, dict)]

    scene_state = _as_dict(state.get("scene_state"))
    active_scene = _as_dict(state.get("active_scene"))
    return {
        "scene_id": _text(
            blueprint.get("scene_id")
            or scene_state.get("active_scene_id")
            or active_scene.get("scene_id")
        , 200),
        "topic_group": _text(
            blueprint.get("topic_group")
            or scene_state.get("trajectory")
            or scene_state.get("active_topic")
        , 500),
        "goal": _text(
            blueprint.get("goal")
            or scene_state.get("goal")
            or scene_state.get("active_goal")
        , 700),
        "representations": representations or ["text"],
        "nodes": nodes,
        "relations": relations,
        "order": [
            _text(item, 120)
            for item in _as_list(
                blueprint.get("order")
                or blueprint.get("representation_order")
            )
            if _text(item, 120)
        ][:32],
        "scene_kind": _text(
            blueprint.get("scene_kind")
            or ("composite" if len(representations) > 1 else "text"),
            120,
        ),
        "present": bool(blueprint or nodes or representations),
        "one_scene": True,
        "one_response": True,
        "one_signal": True,
    }


# =====================================================
# 🔥 MAIN REASONING STATE
# =====================================================

def build_reasoning_state(
    text: str,
    state: dict,
    semantic: dict = None
):

    """
    APRIL LIGHTWEIGHT REASONING STATE

    Новый reasoning:

    - меньше token pressure
    - меньше recursive reflection
    - меньше semantic duplication
    - меньше dialog rebuild

    Главная задача:
    удерживать trajectory,
    continuity,
    scene direction
    и execution readiness.

    Reasoning больше НЕ:
    - giant semantic snapshot
    - second cognition layer
    - self-analysis engine
    - over-monitoring system
    """

    reasoning_enter(
        text
    )

    semantic = semantic or {}

    state = state or {}

    # =================================================
    # 🔥 STATE
    # =================================================

    dialog = state.get(
        "dialog",
        []
    )

    active_flow = state.get(
        "active_flow"
    )

    scene_state = state.get(
        "scene_state",
        {}
    )

    active_scene = state.get(
        "active_scene",
        {}
    )

    visual_continuity = state.get(
        "visual_continuity_summary",
        {}
    )

    focus_snapshot = state.get(
        "focus_snapshot",
        {}
    )

    scene_evidence = _scene_evidence(state, semantic)
    scene_blueprint = _as_dict(semantic.get("scene_blueprint"))

    # =================================================
    # 🔥 SCENE
    # =================================================

    scene_goal = scene_state.get(
        "goal"
    )

    scene_trajectory = scene_state.get(
        "trajectory"
    )

    scene_direction = scene_state.get(
        "confirmed_direction"
    )

    scene_continuity = bool(
        scene_state.get(
            "continuity",
            scene_evidence.get("present") or bool(active_scene),
        )
    )

    # =================================================
    # 🔥 LIGHTWEIGHT SEMANTIC
    # =================================================

    dialogue_contract = _as_dict(semantic.get("dialogue_contract"))
    continuation = bool(
        semantic.get("continuation", False)
        or dialogue_contract.get("continuation", False)
    )

    continuation_target = (
        semantic.get("continuation_target")
        or dialogue_contract.get("reply_to")
        or scene_evidence.get("scene_id")
        or scene_evidence.get("topic_group")
    )

    execution_pressure = semantic.get(
        "execution_pressure",
        0.0
    )

    should_execute = semantic.get(
        "should_execute",
        False
    )

    response_mode = semantic.get(
        "response_mode",
        "talk"
    )

    goal_stage = semantic.get(
        "goal_stage",
        "exploration"
    )

    ambiguity_level = semantic.get(
        "ambiguity_level",
        0.0
    )

    capability_confidence = semantic.get(
        "capability_confidence",
        0.5
    )

    conversation_value = semantic.get(
        "conversation_value",
        1.0
    )

    # =================================================
    # 🔥 DIALOG DEPTH
    # =================================================

    dialog_depth = len(dialog)

    # =================================================
    # 🔥 LAST USER
    # =================================================

    last_user = None

    for msg in reversed(dialog[-8:]):
        if not isinstance(msg, dict):
            continue
        if msg.get("role") == "user":
            content = (
                msg.get("content")
                or msg.get("text")
                or msg.get("answer")
                or ""
            ).strip()
            if content and content != text:
                last_user = content
                break

    # =================================================
    # 🔥 LAST ASSISTANT
    # =================================================

    last_assistant = None

    for msg in reversed(dialog[-6:]):
        if not isinstance(msg, dict):
            continue
        if msg.get("role") in {"assistant", "april", "bot"}:
            last_assistant = (
                msg.get("content")
                or msg.get("answer")
                or msg.get("summary")
                or msg.get("text")
                or ""
            ).strip()
            if last_assistant:
                break

    # =================================================
    # 🔥 TRAJECTORY
    # =================================================

    trajectory_active = bool(

        active_flow
        or scene_trajectory
    )

    trajectory_locked = bool(
        continuation
        or (
            scene_continuity
            and bool(scene_trajectory or scene_evidence.get("present"))
        )
    )

    # =================================================
    # 🔥 EXECUTION READINESS
    # =================================================

    high_confidence_execution = (

        should_execute

        and execution_pressure >= 0.82

        and ambiguity_level <= 0.25

        and capability_confidence >= 0.8
    )

    # =================================================
    # 🔥 REFLECTION CONTROL
    # =================================================

    needs_reflection = True

    if high_confidence_execution:

        needs_reflection = False

    if trajectory_active:

        needs_reflection = False

    # =================================================
    # 🔥 DIALOG HEALTH
    # =================================================

    dialog_overextended = (

        dialog_depth >= 12

        and conversation_value <= 0.45
    )

    unresolved_intent = not (

        should_execute

        and ambiguity_level <= 0.25

        and execution_pressure >= 0.82
    )

    # =================================================
    # 🔥 MACHINE STATE
    # =================================================

    reasoning = {

        # =================================================
        # 🔥 CORE
        # =====================================================

        "input": text,

        "conversation_alive": True,

        "reasoning_id":
            "APRIL_REASONING_STATE",

        # =================================================
        # 🔥 TRAJECTORY
        # =====================================================

        "trajectory_active":
            trajectory_active,

        "trajectory_locked":
            trajectory_locked,

        "continuation":
            continuation,

        "continuation_target":
            continuation_target,

        "preserve_trajectory": True,

        "preserve_continuity": True,

        # =================================================
        # 🔥 SCENE
        # =====================================================

        "scene_goal":
            scene_goal,

        "scene_trajectory":
            scene_trajectory,

        "scene_direction":
            scene_direction,

        "scene_continuity":
            scene_continuity,

        "active_scene":
            active_scene,

        "scene_blueprint":
            scene_blueprint,

        "scene_evidence":
            scene_evidence,

        "scene_representations":
            list(scene_evidence.get("representations") or ["text"]),

        "scene_nodes":
            list(scene_evidence.get("nodes") or []),

        "scene_relations":
            list(scene_evidence.get("relations") or []),

        "scene_order":
            list(scene_evidence.get("order") or []),

        "one_scene":
            True,

        "one_response":
            True,

        "one_signal":
            True,

        "visual_continuity":
            visual_continuity,

        "focus_snapshot":
            focus_snapshot,

        "scene_awareness":
            True,

        # =================================================
        # 🔥 EXECUTION
        # =====================================================

        "should_execute":
            should_execute,

        "execution_pressure":
            execution_pressure,

        "execution_ready":
            high_confidence_execution,

        "response_mode":
            response_mode,

        "goal_stage":
            goal_stage,

        # =================================================
        # 🔥 STABILIZATION
        # =====================================================

        "needs_reflection":
            needs_reflection,

        "unresolved_intent":
            unresolved_intent,

        "dialog_overextended":
            dialog_overextended,

        "avoid_recursive_analysis":
            True,

        "avoid_context_rebuild":
            True,

        "avoid_overthinking":
            True,

        # =================================================
        # 🔥 MEMORY
        # =====================================================

        "last_user":
            last_user,

        "last_assistant":
            last_assistant,

        # =================================================
        # 🔥 INTERNAL MACHINE MODES
        # =====================================================

        "state_mode":
            "trajectory_reasoning",

        "continuity_mode":
            "active",

        "reasoning_style":
            "lightweight",

        "scene_priority":
            True,

        "dialog_priority":
            False,

        "reflection_mode":
            "minimal",

        # =================================================
        # 🔥 APRIL WEB STABILIZATION
        # =====================================================

        "web_ready": True,

        "scene_composition_ready":
            bool(scene_evidence.get("present")),

        "scene_relationships_preserved":
            bool(scene_evidence.get("relations")),

        "scene_layout_mode":
            _as_dict(scene_blueprint.get("layout")).get("mode", "flow"),

        "scene_free_width":
            bool(_as_dict(scene_blueprint.get("layout")).get("free_width", True)),

        "machine_context_safe": True,

        "renderer_safe": True,

        "provider_safe": True,

        "continuity_safe": True
    }

    reasoning_exit(
        reasoning
    )

    return reasoning


# =====================================================
# 🧠 DYNAMIC FOCUS REASONING UPGRADE
# =====================================================

def build_reasoning_focus_state(state):

    focus = state.get("dynamic_focus", {})

    return {
        "active_focus":
            focus.get("primary_focus"),

        "secondary_focus":
            focus.get("secondary_focus"),

        "focus_strength":
            focus.get("focus_strength", 0.0)
    }
