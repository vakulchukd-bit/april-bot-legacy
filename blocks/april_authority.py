# =========================================================
# 🧠 APRIL GOVERNANCE AUTHORITY CORE
# =========================================================

"""
APRIL GOVERNANCE AUTHORITY CORE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ROLE IN APRIL:
This file is the GOVERNANCE,
VALIDATION and COGNITIVE STABILIZATION core of April.

This helper core protects April from:
- execution chaos
- recursive instability
- broken continuity
- modality conflicts
- system leakage
- unstable cognition
- orchestration corruption

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 WHAT THIS FILE IS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file IS:
- governance layer
- cognition validator
- continuity protector
- orchestration supervisor
- modality validator
- trajectory stabilizer
- anti-chaos system
- execution sanity checker

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 WHAT THIS FILE IS NOT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file is NOT:
- second Executor
- orchestration engine
- routing authority
- response formatter
- renderer
- frontend system
- Telegram system
- override chaos layer

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 APRIL ARCHITECTURE POSITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BotRoot
 ↓
Executor
 ↓
Governance Authority Core (THIS FILE)
 ↓
Execution Rooms

Executor thinks.
Rooms execute.
This helper core validates stability.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 GOLDEN MACHINE CHANNEL RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file uses TWO isolated channels.

1. GOVERNANCE TASK CHANNEL
Executor → Governance Core

2. GOVERNANCE RESPONSE CHANNEL
Governance Core → Executor

Human-layer NEVER mixes with
internal cognition governance.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 GOLDEN APRIL PRINCIPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. continuation before override
2. renderer before generation
3. usefulness before capability
4. calm orchestration
5. governance before force
6. anti-recursive behavior
7. no hidden escalation
8. no personality leakage
9. no cognitive duplication
10. no orchestration conflict

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 IMPORTANT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DO NOT RE-ADD:
- Telegram logic
- recursive retries
- hidden rerouting
- second orchestration
- aggressive overrides
- frontend rendering
- transport formatting
- duplicated governance systems

This file must remain:
- calm
- lightweight
- validator-focused
- Executor-connected
- cognition-safe
"""

# =========================================================
# 🧠 MACHINE CHANNELS
# =========================================================

GOVERNANCE_TASK_CHANNEL = {

    "channel":
        "governance_machine_task_channel",

    "isolated":
        True
}

GOVERNANCE_RESPONSE_CHANNEL = {

    "channel":
        "governance_machine_response_channel",

    "isolated":
        True
}

# =========================================================
# 🧠 APRIL CAPABILITY REGISTRY
# =========================================================

"""
Central April capability awareness.

This registry helps Executor understand:
- what April can do
- which helper cores exist
- which modality paths are valid
"""

APRIL_CAPABILITIES = {

    # =====================================================
    # 🧠 CORE COGNITION
    # =====================================================

    "conversation": True,
    "continuation": True,
    "trajectory_tracking": True,
    "reasoning": True,
    "guidance": True,
    "execution": True,

    # =====================================================
    # 🧠 VISUAL
    # =====================================================

    "renderer_space": True,
    "scene_rendering": True,
    "graph_generation": True,
    "diagram_generation": True,
    "formula_rendering": True,
    "table_rendering": True,
    "visual_continuity": True,
    "image_analysis": True,

    # =====================================================
    # 🧠 HEAVY VISUAL
    # =====================================================

    "image_generation": True,
    "image_edit": True,

    # =====================================================
    # 🧠 KNOWLEDGE
    # =====================================================

    "web_search": True,
    "external_knowledge": True,
    "references": True,

    # =====================================================
    # 🧠 SCIENCE
    # =====================================================

    "science": True,
    "math": True,
    "engineering": True,
    "code": True,

    # =====================================================
    # 🧠 GOVERNANCE
    # =====================================================

    "validation": True,
    "trajectory_protection": True,
    "continuity_validation": True,
    "result_validation": True,
    "usefulness_validation": True,

    # =====================================================
    # 🧠 SAFETY
    # =====================================================

    "anti_loop_protection": True,
    "anti_escalation": True,
    "anti_personality_leak": True,
    "anti_recursive_generation": True
}

# =========================================================
# 🧠 TRUST LEVELS
# =========================================================

"""
Trust stabilization between helper cores.

Prevents orchestration conflicts.
"""

DEFAULT_TRUST_LEVELS = {

    "executor": 1.0,

    "text": 1.0,

    "science": 1.0,

    "renderer_space": 1.0,

    "image_analysis": 1.0,

    "web": 1.0,

    "code": 1.0,

    # =====================================================
    # 🧠 HEAVY VISUAL
    # =====================================================

    "image_generation": 0.82,

    "image_edit": 0.82
}

# =========================================================
# 🧠 HELPERS
# =========================================================

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


def safe_output(result):

    if not result:
        return ""

    return str(
        result.get(
            "data",
            ""
        )
    ).strip()

# =========================================================
# 🧠 SYSTEM LEAK DETECTION
# =========================================================

def contains_system_leak(output):

    """
    Prevents internal machine leakage
    into human-layer output.
    """

    if not output:
        return False

    lowered = output.lower()

    leak_patterns = [

        "response_decision",
        "execution_pressure",
        "cognition",
        "semantic",
        "internal_noise",
        "trajectory_tracking",
        "system prompt"
    ]

    hits = 0

    for pattern in leak_patterns:

        if pattern in lowered:
            hits += 1

    return hits >= 2

# =========================================================
# 🧠 RENDERER DETECTION
# =========================================================

def is_renderer_result(result):

    """
    Detects renderer-safe outputs.
    """

    if not result:
        return False

    result_type = result.get(
        "type",
        "text"
    )

    if result_type in [

        "function",
        "graph",
        "diagram",
        "formula",
        "table",
        "scene"
    ]:

        return True

    output = safe_output(
        result
    ).lower()

    renderer_patterns = [

        "[[graph",
        "[[diagram",
        "[[formula",
        "<svg",
        "<canvas"
    ]

    return any(
        x in output
        for x in renderer_patterns
    )

# =========================================================
# 🧠 AUTHORITY STATE
# =========================================================

def build_authority_state():

    """
    Global governance stabilization state.
    """

    return {

        "authority_active": True,

        "governance_active": True,

        "validation_active": True,

        "continuity_protection": True,

        "calm_orchestration": True,

        "anti_recursive_behavior": True,

        "anti_hidden_generation": True,

        "anti_personality_leak": True,

        "avoid_force_execution": True,

        "avoid_aggressive_override": True,

        "trust_levels":
            DEFAULT_TRUST_LEVELS.copy(),

        "machine_channel":
            GOVERNANCE_RESPONSE_CHANNEL
    }

# =========================================================
# 🧠 COMPLETION ANALYSIS
# =========================================================

def analyze_completion(

    result,
    semantic,
    cognition
):

    """
    Validates whether execution
    completed successfully.
    """

    semantic = semantic or {}
    cognition = cognition or {}

    if not result:

        return {

            "completed": False,

            "reason":
                "empty_result"
        }

    result_type = result.get(
        "type",
        "text"
    )

    output = safe_output(
        result
    )

    lowered = output.lower()

    # =====================================================
    # 🧠 RENDERER SUCCESS
    # =====================================================

    if result_type in [

        "function",
        "graph",
        "diagram",
        "formula",
        "scene",
        "table"
    ]:

        return {

            "completed": True,

            "reason":
                "renderer_completed"
        }

    # =====================================================
    # 🧠 EMPTY OUTPUT
    # =====================================================

    if len(output) <= 5:

        return {

            "completed": False,

            "reason":
                "empty_output"
        }

    # =====================================================
    # 🧠 SYSTEM LEAK
    # =====================================================

    if contains_system_leak(
        output
    ):

        return {

            "completed": False,

            "reason":
                "system_leak"
        }

    # =====================================================
    # 🧠 REFUSAL DETECTION
    # =====================================================

    refusal_patterns = [

        "я не могу",
        "не умею",
        "не поддерживается"
    ]

    for pattern in refusal_patterns:

        if pattern in lowered:

            return {

                "completed": False,

                "reason":
                    "refusal"
            }

    return {

        "completed": True,

        "reason":
            "success"
    }

# =========================================================
# 🧠 USEFULNESS ANALYSIS
# =========================================================

def evaluate_usefulness(

    result,
    semantic,
    cognition
):

    """
    Measures practical usefulness
    of execution output.
    """

    if not result:

        return 0.0

    usefulness = 1.0

    output = safe_output(
        result
    )

    lowered = output.lower()

    # =====================================================
    # 🧠 VISUAL BONUS
    # =====================================================

    if result.get("type") in [

        "graph",
        "diagram",
        "formula",
        "scene"
    ]:

        usefulness += 0.25

    # =====================================================
    # 🧠 WEAK OUTPUT
    # =====================================================

    if len(output) < 15:

        usefulness -= 0.4

    # =====================================================
    # 🧠 REFUSAL PENALTY
    # =====================================================

    if "не могу" in lowered:

        usefulness -= 0.5

    # =====================================================
    # 🧠 SYSTEM LEAK PENALTY
    # =====================================================

    if contains_system_leak(
        output
    ):

        usefulness -= 0.7

    return clamp(
        usefulness
    )

# =========================================================
# 🧠 FINAL VALIDATION
# =========================================================

def validate_final_response(

    result,
    semantic,
    cognition,
    state=None
):

    """
    Final cognition stability validation.
    """

    completion = analyze_completion(

        result,
        semantic,
        cognition
    )

    if not completion.get(
        "completed"
    ):

        return False

    usefulness = evaluate_usefulness(

        result,
        semantic,
        cognition
    )

    if usefulness < 0.45:

        return False

    return True

# =========================================================
# 🧠 OVERRIDE VALIDATION
# =========================================================

def should_override(

    result,
    semantic,
    cognition,
    state=None
):

    """
    Calm override validation.

    NOT aggressive.
    NOT recursive.
    """

    semantic = semantic or {}
    cognition = cognition or {}

    valid = validate_final_response(

        result,
        semantic,
        cognition,
        state
    )

    if not valid:

        return True

    # =====================================================
    # 🧠 RENDERER PRIORITY
    # =====================================================

    if semantic.get(
        "prefer_renderer"
    ):

        if result.get(
            "type"
        ) == "image":

            return True

    return False

# =========================================================
# 🧠 CAPABILITY PATH GOVERNANCE
# =========================================================

def choose_best_capability_path(

    semantic,
    cognition,
    state
):

    """
    Governance-level capability coordination.

    Prevents helper-core conflicts.
    """

    semantic = semantic or {}
    cognition = cognition or {}
    state = state or {}

    if semantic.get(
        "prefer_renderer"
    ):

        return "renderer_space"

    if semantic.get(
        "internet_context_needed"
    ):

        return "web"

    if semantic.get(
        "should_execute"
    ):

        return "execution"

    continuation_target = semantic.get(
        "continuation_target"
    )

    if continuation_target == "math":

        return "science"

    return "text"

# =========================================================
# 🧠 EXECUTIVE GOVERNANCE DECISION
# =========================================================

def build_authority_decision(

    result,
    semantic,
    cognition,
    response_decision,
    state=None
):

    """
    Final governance payload for Executor.

    This helper core NEVER orchestrates.
    It only validates and stabilizes.
    """

    completion = analyze_completion(

        result,
        semantic,
        cognition
    )

    usefulness = evaluate_usefulness(

        result,
        semantic,
        cognition
    )

    override = should_override(

        result,
        semantic,
        cognition,
        state
    )

    capability_path = (

        choose_best_capability_path(

            semantic,
            cognition,
            state or {}
        )
    )

    return {

        "channel":
            GOVERNANCE_RESPONSE_CHANNEL,

        "override":
            override,

        "allow_response":
            not override,

        "completed":
            completion.get(
                "completed",
                False
            ),

        "completion_reason":
            completion.get(
                "reason"
            ),

        "usefulness":
            usefulness,

        "best_capability":
            capability_path,

        "preferred_modality":
            capability_path,

        "governance_mode":
            "calm",

        "avoid_recursive_retry":
            True,

        "avoid_hidden_generation":
            True,

        "avoid_personality_leak":
            True,

        "avoid_double_orchestration":
            True,

        "maintain_continuity":
            True,

        "maintain_humanity":
            True,

        "maintain_dialog_flow":
            True,

        "authority_confident":
            True
    }
