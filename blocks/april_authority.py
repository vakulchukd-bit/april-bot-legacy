# =========================================================
# 🧠 APRIL GOVERNANCE AUTHORITY CORE
# =========================================================

"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APRIL FILE ID
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

APRIL_FILE_ID:
APRIL_GOVERNANCE_AUTHORITY_CORE

ROLE:
COGNITIVE_GOVERNANCE_AND_VALIDATION_SYSTEM

ROOM:
GOVERNANCE_ROOM

INPUT:
EXECUTOR_VALIDATION_REQUEST
COGNITIVE_RESULT
SEMANTIC_STATE
RESPONSE_DECISION
CONTINUITY_STATE
TRAJECTORY_STATE

OUTPUT:
GOVERNANCE_DECISION
VALIDATION_RESULT
USEFULNESS_ANALYSIS
CAPABILITY_COORDINATION
ANALYZER_GOVERNANCE_PAYLOAD

DEPENDENCIES:
EXECUTOR
RENDERER_SPACE
COGNITIVE_ROOMS
ANCHOR_SYSTEM
POLICY_CORE
ANALYZER_SYSTEM

CRITICAL:
TRUE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 GOLDEN RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file NEVER:
- performs cognition
- replaces Executor
- performs orchestration
- formats frontend output

This file ONLY:
- validates stability
- protects continuity
- blocks orchestration chaos
- validates cognition sanity
- coordinates governance safety
- exposes governance telemetry

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 ANALYZER VISIBILITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Analyzer may observe:
- governance stability
- validation pressure
- modality conflicts
- continuity protection
- recursive protection
- orchestration safety

Analyzer may NEVER:
- override governance
- alter cognition
- replace Executor authority
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
# 🔥 APRIL TRACE LOGS
# =========================================================

def APRIL_LOG_IN(
    room,
    metadata=None
):

    try:

        print({

            "type":
                "APRIL_LOG_IN",

            "room":
                room,

            "file":
                "APRIL_GOVERNANCE_AUTHORITY_CORE",

            "metadata":
                metadata or {}
        })

    except Exception:
        pass


def APRIL_LOG_OUT(
    room,
    metadata=None
):

    try:

        print({

            "type":
                "APRIL_LOG_OUT",

            "room":
                room,

            "file":
                "APRIL_GOVERNANCE_AUTHORITY_CORE",

            "metadata":
                metadata or {}
        })

    except Exception:
        pass

# =========================================================
# 🧠 APRIL CAPABILITY REGISTRY
# =========================================================

APRIL_CAPABILITIES = {

    "conversation": True,
    "continuation": True,
    "trajectory_tracking": True,
    "reasoning": True,
    "guidance": True,
    "execution": True,

    "renderer_space": True,
    "scene_rendering": True,
    "graph_generation": True,
    "diagram_generation": True,
    "formula_rendering": True,
    "table_rendering": True,
    "visual_continuity": True,
    "image_analysis": True,

    "image_generation": True,
    "image_edit": True,

    "web_search": True,
    "external_knowledge": True,
    "references": True,

    "science": True,
    "math": True,
    "engineering": True,
    "code": True,

    "validation": True,
    "trajectory_protection": True,
    "continuity_validation": True,
    "result_validation": True,
    "usefulness_validation": True,

    "anti_loop_protection": True,
    "anti_escalation": True,
    "anti_personality_leak": True,
    "anti_recursive_generation": True
}

# =========================================================
# 🧠 TRUST LEVELS
# =========================================================

DEFAULT_TRUST_LEVELS = {

    "executor": 1.0,

    "text": 1.0,

    "science": 1.0,

    "renderer_space": 1.0,

    "image_analysis": 1.0,

    "web": 1.0,

    "code": 1.0,

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

    if governance_type(result) == "artifact":

        artifact = governance_get(result, "artifact")

        try:
            return str(
                getattr(artifact, "data", "")
            )
        except Exception:
            return str(result)

    value = (
        governance_get(result, "data", None)
        or governance_get(result, "content", None)
        or governance_get(result, "summary", None)
        or governance_get(result, "answer", "")
    )
    return str(value).strip()



# =========================================================
# 🧠 GOVERNANCE RESULT ADAPTER (STAGE 1)
# =========================================================

def governance_get(result, key, default=None):
    if result is None:
        return default
    if isinstance(result, dict):
        return result.get(key, default)
    try:
        value = getattr(result, key)
        if value is not None:
            return value
    except Exception:
        pass
    getter = getattr(result, "get", None)
    if callable(getter):
        try:
            return getter(key, default)
        except Exception:
            pass
    return default

def governance_type(result):
    return governance_get(result, "type", "text")

# =========================================================
# 🧠 SYSTEM LEAK DETECTION
# =========================================================

def contains_system_leak(output):

    APRIL_LOG_IN(

        "GOVERNANCE_ROOM",

        {
            "action":
                "contains_system_leak"
        }
    )

    if not output:

        APRIL_LOG_OUT(

            "GOVERNANCE_ROOM",

            {
                "result":
                    False
            }
        )

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

    result = hits >= 2

    APRIL_LOG_OUT(

        "GOVERNANCE_ROOM",

        {
            "system_leak":
                result
        }
    )

    return result

# =========================================================
# 🧠 RENDERER DETECTION
# =========================================================

def is_renderer_result(result):

    APRIL_LOG_IN(

        "GOVERNANCE_ROOM",

        {
            "action":
                "is_renderer_result"
        }
    )

    if not result:

        APRIL_LOG_OUT(

            "GOVERNANCE_ROOM",

            {
                "renderer":
                    False
            }
        )

        return False

    result_type = governance_type(result)

    if result_type in [

        "function",
        "graph",
        "diagram",
        "formula",
        "table",
        "scene"
    ]:

        APRIL_LOG_OUT(

            "GOVERNANCE_ROOM",

            {
                "renderer":
                    True
            }
        )

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

    detected = any(
        x in output
        for x in renderer_patterns
    )

    APRIL_LOG_OUT(

        "GOVERNANCE_ROOM",

        {
            "renderer":
                detected
        }
    )

    return detected

# =========================================================
# 🧠 AUTHORITY STATE
# =========================================================

def build_authority_state():

    APRIL_LOG_IN(

        "GOVERNANCE_ROOM",

        {
            "action":
                "build_authority_state"
        }
    )

    payload = {

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

    APRIL_LOG_OUT(

        "GOVERNANCE_ROOM",

        {
            "authority":
                "active"
        }
    )

    return payload


# =========================================================
# 🏭 FACTORY ARTIFACT REGISTRY
# =========================================================

FACTORY_DOMAIN_ROOMS = {
    "biology",
    "chemistry",
    "physics",
    "mathematics",
    "trigonometry",
    "engineering",
    "it",
    "web",
    "news",
    "social",
    "politics",
    "literature"
}


# =========================================================
# 🧠 COMPLETION ANALYSIS
# =========================================================

def analyze_completion(

    result,
    semantic,
    cognition
):

    APRIL_LOG_IN(

        "GOVERNANCE_ROOM",

        {
            "action":
                "analyze_completion"
        }
    )

    semantic = semantic or {}
    cognition = cognition or {}

    if not result:

        payload = {

            "completed": False,

            "reason":
                "empty_result"
        }

        APRIL_LOG_OUT(

            "GOVERNANCE_ROOM",

            payload
        )

        return payload

    result_type = governance_type(result)

    output = safe_output(result)
    lowered = output.lower()

    # Canonical machine-response fallback
    if not output:
        output = str(
            governance_get(result, "content", "")
            or governance_get(result, "summary", "")
            or governance_get(result, "answer", "")
        ).strip()
        lowered = output.lower()

    if result_type in [

        "artifact",
        "function",
        "graph",
        "diagram",
        "formula",
        "scene",
        "table"
    ]:

        payload = {

            "completed": True,

            "reason":
                "renderer_completed"
        }

        APRIL_LOG_OUT(

            "GOVERNANCE_ROOM",

            payload
        )

        return payload

    if len(output) <= 5:

        payload = {

            "completed": False,

            "reason":
                "empty_output"
        }

        APRIL_LOG_OUT(

            "GOVERNANCE_ROOM",

            payload
        )

        return payload

    if contains_system_leak(
        output
    ):

        payload = {

            "completed": False,

            "reason":
                "system_leak"
        }

        APRIL_LOG_OUT(

            "GOVERNANCE_ROOM",

            payload
        )

        return payload

    refusal_patterns = [

        "я не могу",
        "не умею",
        "не поддерживается"
    ]

    for pattern in refusal_patterns:

        if pattern in lowered:

            payload = {

                "completed": False,

                "reason":
                    "refusal"
            }

            APRIL_LOG_OUT(

                "GOVERNANCE_ROOM",

                payload
            )

            return payload

    payload = {

        "completed": True,

        "reason":
            "success"
    }

    APRIL_LOG_OUT(

        "GOVERNANCE_ROOM",

        payload
    )

    return payload

# =========================================================
# 🧠 USEFULNESS ANALYSIS
# =========================================================

def evaluate_usefulness(

    result,
    semantic,
    cognition
):

    APRIL_LOG_IN(

        "GOVERNANCE_ROOM",

        {
            "action":
                "evaluate_usefulness"
        }
    )

    if not result:

        APRIL_LOG_OUT(

            "GOVERNANCE_ROOM",

            {
                "usefulness":
                    0.0
            }
        )

        return 0.0

    usefulness = 1.0

    output = safe_output(
        result
    )

    lowered = output.lower()

    result_kind = governance_type(result)

    if result_kind in [

        "artifact",
        "graph",
        "diagram",
        "formula",
        "scene"
    ]:

        usefulness += 0.25

    if len(output) < 15:

        usefulness -= 0.4

    if "не могу" in lowered:

        usefulness -= 0.5

    if contains_system_leak(
        output
    ):

        usefulness -= 0.7

    usefulness = clamp(
        usefulness
    )

    APRIL_LOG_OUT(

        "GOVERNANCE_ROOM",

        {
            "usefulness":
                usefulness
        }
    )

    return usefulness

# =========================================================
# 🧠 FINAL VALIDATION
# =========================================================

def validate_final_response(

    result,
    semantic,
    cognition,
    state=None
):

    APRIL_LOG_IN(

        "GOVERNANCE_ROOM",

        {
            "action":
                "validate_final_response"
        }
    )

    completion = analyze_completion(

        result,
        semantic,
        cognition
    )

    if not governance_get(completion, "completed"):

        APRIL_LOG_OUT(

            "GOVERNANCE_ROOM",

            {
                "validated":
                    False
            }
        )

        return False

    usefulness = evaluate_usefulness(

        result,
        semantic,
        cognition
    )

    valid = usefulness >= 0.45

    APRIL_LOG_OUT(

        "GOVERNANCE_ROOM",

        {
            "validated":
                valid
        }
    )

    return valid

# =========================================================
# 🧠 OVERRIDE VALIDATION
# =========================================================

def should_override(

    result,
    semantic,
    cognition,
    state=None
):

    APRIL_LOG_IN(

        "GOVERNANCE_ROOM",

        {
            "action":
                "should_override"
        }
    )

    semantic = semantic or {}
    cognition = cognition or {}

    valid = validate_final_response(

        result,
        semantic,
        cognition,
        state
    )

    if not valid:

        APRIL_LOG_OUT(

            "GOVERNANCE_ROOM",

            {
                "override":
                    True
            }
        )

        return True

    if semantic.get(
        "prefer_renderer"
    ):

        if governance_type(result) == "image":

            APRIL_LOG_OUT(

                "GOVERNANCE_ROOM",

                {
                    "override":
                        True
                }
            )

            return True

    APRIL_LOG_OUT(

        "GOVERNANCE_ROOM",

        {
            "override":
                False
        }
    )

    return False

# =========================================================
# 🧠 CAPABILITY PATH GOVERNANCE
# =========================================================

def choose_best_capability_path(

    semantic,
    cognition,
    state
):

    APRIL_LOG_IN(

        "GOVERNANCE_ROOM",

        {
            "action":
                "choose_best_capability_path"
        }
    )

    semantic = semantic or {}
    cognition = cognition or {}
    state = state or {}

    if semantic.get(
        "prefer_renderer"
    ):

        result = "renderer_space"

    elif semantic.get(
        "internet_context_needed"
    ):

        result = "web"

    elif semantic.get(
        "should_execute"
    ):

        result = "execution"

    else:

        continuation_target = semantic.get(
            "continuation_target"
        )

        if continuation_target == "math":

            result = "science"

        else:

            result = "text"

    APRIL_LOG_OUT(

        "GOVERNANCE_ROOM",

        {
            "capability":
                result
        }
    )

    return result

# =========================================================
# 🧠 ANALYZER GOVERNANCE PAYLOAD
# =========================================================

def build_governance_telemetry_payload():

    APRIL_LOG_IN(

        "GOVERNANCE_ROOM",

        {
            "action":
                "build_governance_telemetry_payload"
        }
    )

    payload = {

        "file_id":
            "APRIL_GOVERNANCE_AUTHORITY_CORE",

        "room":
            "GOVERNANCE_ROOM",

        "governance_active":
            True,

        "validation_active":
            True,

        "anti_recursive_protection":
            True,

        "continuity_protection":
            True,

        "renderer_priority":
            True,

        "executor_connected":
            True,

        "registered_capabilities":
            len(
                APRIL_CAPABILITIES
            )
    }

    APRIL_LOG_OUT(

        "GOVERNANCE_ROOM",

        {
            "telemetry":
                "ready"
        }
    )

    return payload

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

    APRIL_LOG_IN(

        "GOVERNANCE_ROOM",

        {
            "action":
                "build_authority_decision"
        }
    )

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

    payload = {

        "channel":
            GOVERNANCE_RESPONSE_CHANNEL,

        "override":
            override,

        "allow_response":
            not override,

        "completed":
            governance_get(completion, "completed", False),

        "completion_reason":
            governance_get(completion, "reason"),

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
            True,

        "telemetry":
            build_governance_telemetry_payload()
    }

    APRIL_LOG_OUT(

        "GOVERNANCE_ROOM",

        {
            "authority_decision":
                "ready"
        }
    )

    return payload
