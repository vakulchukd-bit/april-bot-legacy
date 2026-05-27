# =====================================================
# 🧠 VISUAL REFERENCE SYSTEM
# =====================================================

"""
APRIL VISUAL REFERENCE SYSTEM

Renderer-aware semantic support layer.

ROLE:
- visual continuity support;
- trajectory-safe visual guidance;
- renderer cooperation;
- lightweight scene assistance;
- semantic visual stabilization.

NOT ROLE:
- image authority;
- orchestration layer;
- forced generation;
- trigger engine;
- scene ownership.

APRIL PRINCIPLES:

1. scene before keywords
2. continuity before escalation
3. renderer before generation
4. semantic inheritance before triggers
5. support instead of domination
6. visual cognition instead of guessing
"""

# =====================================================
# 🧠 HELPERS
# =====================================================

def normalize(
    text: str
):

    return (
        text or ""
    ).lower().strip()


def contains_any(
    text: str,
    words: list
):

    return any(
        w in text
        for w in words
    )


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
# 🧠 SAFE SCENE HELPERS
# =====================================================

def build_scene_snapshot(
    active_visual_scene
):

    if not active_visual_scene:

        return {

            "exists": False
        }

    return {

        "exists": True,

        "scene_type":
            active_visual_scene.get(
                "scene_type"
            ),

        "objects":
            active_visual_scene.get(
                "objects",
                []
            ),

        "summary":
            active_visual_scene.get(
                "summary",
                ""
            ),

        "atmosphere":
            active_visual_scene.get(
                "atmosphere"
            ),

        "continuity_weight":
            active_visual_scene.get(
                "continuity_weight",
                0.0
            )
    }


def inherit_scene_direction(
    result,
    scene_snapshot
):

    if not scene_snapshot.get(
        "exists"
    ):

        return result

    result[
        "visual_continuity"
    ] = True

    result[
        "trajectory_aligned"
    ] = True

    result[
        "dialogue_centered"
    ] = True

    result[
        "support_level"
    ] += 0.28

    result[
        "scene_inherited"
    ] = True

    atmosphere = scene_snapshot.get(
        "atmosphere"
    )

    if atmosphere:

        result[
            "atmosphere"
        ] = atmosphere

    continuity_weight = scene_snapshot.get(
        "continuity_weight",
        0.0
    )

    if continuity_weight >= 0.7:

        result[
            "reference_priority"
        ] = True

        result[
            "lightweight_mode"
        ] = True

        result[
            "suppress_generation"
        ] = True

    return result


# =====================================================
# 🧠 MACHINE SIGNALS
# =====================================================

def detect_machine_visual_state(
    semantic: dict,
    cognition: dict,
    reasoning: dict,
    state: dict
):

    signals = {

        "scene_active": False,

        "renderer_active": False,

        "continuity_active": False,

        "exploration_active": False,

        "generation_blocked": False,

        "trajectory_active": False,

        "dialogue_priority": False
    }

    # =================================================
    # 🔥 SEMANTIC
    # =====================================================

    if semantic.get(
        "visual_continuity"
    ):

        signals[
            "continuity_active"
        ] = True

    if semantic.get(
        "render_intent"
    ):

        signals[
            "renderer_active"
        ] = True

    if semantic.get(
        "prefer_renderer"
    ):

        signals[
            "renderer_active"
        ] = True

    if semantic.get(
        "dialog_state"
    ) == "exploration":

        signals[
            "exploration_active"
        ] = True

    # =================================================
    # 🔥 COGNITION
    # =====================================================

    if cognition.get(
        "renderer_space_active"
    ):

        signals[
            "renderer_active"
        ] = True

    if cognition.get(
        "needs_continuation"
    ):

        signals[
            "continuity_active"
        ] = True

    if cognition.get(
        "trajectory_locked"
    ):

        signals[
            "trajectory_active"
        ] = True

    if cognition.get(
        "response_should_continue_scene"
    ):

        signals[
            "continuity_active"
        ] = True

    if cognition.get(
        "prefer_renderer"
    ):

        signals[
            "renderer_active"
        ] = True

    # =================================================
    # 🔥 REASONING
    # =====================================================

    if reasoning.get(
        "unresolved_intent"
    ):

        signals[
            "dialogue_priority"
        ] = True

    # =================================================
    # 🔥 STATE
    # =====================================================

    if state.get(
        "active_visual_scene"
    ):

        signals[
            "scene_active"
        ] = True

    return signals


# =====================================================
# 🧠 VISUAL REFERENCE INHERITANCE
# =====================================================

def build_scene_references(
    scene_snapshot
):

    references = []

    if not scene_snapshot.get(
        "exists"
    ):

        return references

    scene_type = scene_snapshot.get(
        "scene_type"
    )

    atmosphere = scene_snapshot.get(
        "atmosphere"
    )

    objects = scene_snapshot.get(
        "objects",
        []
    )

    if scene_type:

        references.append({

            "type": "scene",

            "title":
                f"Scene continuity: {scene_type}",

            "weight": 0.92
        })

    if atmosphere:

        references.append({

            "type": "atmosphere",

            "title":
                f"Atmosphere continuity: {atmosphere}",

            "weight": 0.88
        })

    for obj in objects[:4]:

        references.append({

            "type": "object",

            "title":
                f"Scene object: {obj}",

            "weight": 0.72
        })

    return references


# =====================================================
# 🧠 EXPLORATION DETECTION
# =====================================================

def detect_exploration_state(
    text: str,
    semantic: dict,
    cognition: dict
):

    t = normalize(text)

    exploration_words = [

        "примерно",
        "не уверен",
        "не знаю",
        "может",
        "вариант",
        "идея",
        "атмосфера",
        "направление",
        "референс",
        "пример"
    ]

    score = 0.0

    if contains_any(
        t,
        exploration_words
    ):

        score += 0.45

    if semantic.get(
        "ambiguity_level",
        0.0
    ) >= 0.4:

        score += 0.3

    if cognition.get(
        "needs_guidance"
    ):

        score += 0.2

    if semantic.get(
        "dialog_state"
    ) == "exploration":

        score += 0.25

    return clamp(score)


# =====================================================
# 🧠 MAIN
# =====================================================

def build_visual_reference(
    semantic: dict,
    cognition: dict,
    text: str,
    state: dict
):

    t = normalize(text)

    reasoning = state.get(
        "reasoning",
        {}
    )

    active_flow = state.get(
        "active_flow"
    )

    active_visual_scene = state.get(
        "active_visual_scene"
    )

    scene_snapshot = build_scene_snapshot(
        active_visual_scene
    )

    machine = detect_machine_visual_state(

        semantic,
        cognition,
        reasoning,
        state
    )

    # =================================================
    # 🧠 BASE
    # =====================================================

    result = {

        # =================================================
        # CORE
        # =====================================================

        "enabled": False,

        "mode": None,

        "references": [],

        # =================================================
        # GENERATION
        # =====================================================

        "should_generate": False,

        "suppress_generation": False,

        "generation_allowed": False,

        # =================================================
        # LIGHTWEIGHT
        # =====================================================

        "lightweight_mode": False,

        "renderer_mode": True,

        "reference_priority": False,

        # =================================================
        # CONTINUITY
        # =====================================================

        "trajectory_aligned": True,

        "dialogue_centered": True,

        "visual_should_continue_dialogue": True,

        "visual_should_not_interrupt": True,

        "visual_continuity": False,

        "scene_inherited": False,

        # =================================================
        # SUPPORT
        # =====================================================

        "support_level": 0.0,

        "reference_confidence": 0.0,

        "direction_detected": False,

        "guidance": None,

        # =================================================
        # STYLE
        # =====================================================

        "response_style": "guidance",

        "emotion": None,

        "atmosphere": None,

        # =================================================
        # MACHINE STATE
        # =====================================================

        "renderer_cooperation": True,

        "semantic_inheritance": True,

        "trajectory_support": True,

        "machine_context_mode": True,

        # =================================================
        # SAFETY
        # =====================================================

        "visual_is_supportive": True,

        "visual_requires_context": True,

        "visual_requires_meaning": True,

        "visual_is_not_random": True,

        "capability_awareness": True,

        "provider_aware": True,

        "avoid_heavy_generation": True
    }

    # =================================================
    # 🧠 SCENE INHERITANCE
    # =====================================================

    result = inherit_scene_direction(

        result,
        scene_snapshot
    )

    inherited_refs = build_scene_references(
        scene_snapshot
    )

    result["references"].extend(
        inherited_refs
    )

    # =================================================
    # 🧠 MACHINE COOPERATION
    # =====================================================

    if machine.get(
        "renderer_active"
    ):

        result[
            "renderer_mode"
        ] = True

        result[
            "suppress_generation"
        ] = True

        result[
            "lightweight_mode"
        ] = True

        result[
            "support_level"
        ] += 0.25

    if machine.get(
        "continuity_active"
    ):

        result[
            "visual_continuity"
        ] = True

        result[
            "trajectory_aligned"
        ] = True

        result[
            "dialogue_centered"
        ] = True

        result[
            "support_level"
        ] += 0.22

    if machine.get(
        "trajectory_active"
    ):

        result[
            "reference_priority"
        ] = True

    if machine.get(
        "dialogue_priority"
    ):

        result[
            "visual_should_continue_dialogue"
        ] = True

        result[
            "lightweight_mode"
        ] = True

    # =================================================
    # 🧠 EXPLORATION
    # =====================================================

    exploration_score = (
        detect_exploration_state(
            text,
            semantic,
            cognition
        )
    )

    if exploration_score >= 0.45:

        result["enabled"] = True

        result["mode"] = (
            "exploration"
        )

        result[
            "lightweight_mode"
        ] = True

        result[
            "reference_priority"
        ] = True

        result[
            "suppress_generation"
        ] = True

        result[
            "response_style"
        ] = "soft_guidance"

        result[
            "support_level"
        ] += exploration_score

    # =================================================
    # 🧠 VISUAL EXPECTATION
    # =====================================================

    visual_expectation = semantic.get(
        "visual_expectation",
        0.0
    )

    example_expectation = semantic.get(
        "example_expectation",
        0.0
    )

    if visual_expectation >= 0.45:

        result["enabled"] = True

        result[
            "support_level"
        ] += 0.2

    if example_expectation >= 0.45:

        result["enabled"] = True

        result[
            "reference_priority"
        ] = True

        result[
            "support_level"
        ] += 0.25

    # =================================================
    # 🧠 SCREENSHOT CONTINUITY
    # =====================================================

    screenshot_words = [

        "скрин",
        "скриншот",
        "screenshot"
    ]

    if contains_any(
        t,
        screenshot_words
    ):

        result["enabled"] = True

        result["mode"] = (
            "context_support"
        )

        result[
            "lightweight_mode"
        ] = True

        result[
            "reference_priority"
        ] = True

        result[
            "suppress_generation"
        ] = True

        result["guidance"] = (

            "Screenshot treated as "
            "continuation context."
        )

    # =================================================
    # 🧠 EXPLICIT GENERATION
    # =====================================================

    explicit_generation_words = [

        "создай изображение",
        "сгенерируй изображение",
        "нарисуй картинку",
        "сделай картинку",
        "generate image",
        "draw image"
    ]

    explicit_generation = contains_any(

        t,
        explicit_generation_words
    )

    if explicit_generation:

        if (

            not result[
                "suppress_generation"
            ]

            and semantic.get(
                "ambiguity_level",
                0.0
            ) < 0.4

            and semantic.get(
                "dialog_state"
            ) != "exploration"

            and not cognition.get(
                "needs_guidance"
            )
        ):

            result[
                "should_generate"
            ] = True

            result[
                "generation_allowed"
            ] = True

            result[
                "avoid_heavy_generation"
            ] = False

    # =================================================
    # 🧠 ACTIVE FLOW
    # =====================================================

    if active_flow:

        result[
            "trajectory_aligned"
        ] = True

        result[
            "dialogue_centered"
        ] = True

        result[
            "support_level"
        ] += 0.12

    # =================================================
    # 🧠 REFERENCE SORT
    # =====================================================

    result["references"] = sorted(

        result["references"],

        key=lambda x: x.get(
            "weight",
            0.0
        ),

        reverse=True
    )

    # =================================================
    # 🧠 NORMALIZATION
    # =====================================================

    result[
        "support_level"
    ] = clamp(
        result[
            "support_level"
        ]
    )

    result[
        "reference_confidence"
    ] = clamp(
        result[
            "reference_confidence"
        ]
    )

    # =================================================
    # 🧠 FINAL SAFETY
    # =====================================================

    if result[
        "lightweight_mode"
    ]:

        result[
            "should_generate"
        ] = False

    if result.get(
        "renderer_mode"
    ):

        result[
            "avoid_heavy_generation"
        ] = True

    return result
