# =====================================================
# 🧠 APRIL ENGINEERING ANALYZER CORE
# =====================================================

"""
APRIL ENGINEERING ANALYZER CORE

APRIL_FILE_ID:
APRIL_ENGINEERING_ANALYZER_CORE

ROLE:
ENGINEERING_SEMANTIC_ANALYZER

INPUT:
CODE_INPUT
EXECUTOR_CONTEXT
PIPELINE_CONTEXT
RENDERER_CONTEXT

OUTPUT:
ENGINEERING_ANALYSIS
ARCHITECTURE_DIAGNOSTICS
PIPELINE_INSIGHTS
SAFE_ENGINEERING_PROMPT

THIS FILE IS:
- engineering semantic helper
- architecture diagnostics layer
- pipeline analysis assistant
- renderer conflict analyzer
- structured engineering reasoning bridge

THIS FILE IS NOT:
- orchestration layer
- renderer authority
- response formatter
- execution router
- frontend renderer
- trigger system

GOLDEN APRIL RULES:
- continuity-safe engineering
- preserve architecture integrity
- no destructive rewrites
- no orchestration duplication
- renderer-safe diagnostics
- structured engineering reasoning
"""

# =====================================================
# 🔥 IMPORTS
# =====================================================

from openai import OpenAI

import os

# =====================================================
# 🔥 OPENAI CLIENT
# =====================================================

client = OpenAI(

    api_key=os.getenv(
        "OPENAI_API_KEY"
    )
)

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

ENGINEERING_TASK_CHANNEL = {

    "channel":
        "engineering_machine_task_channel",

    "isolated":
        True
}

ENGINEERING_RESPONSE_CHANNEL = {

    "channel":
        "engineering_machine_response_channel",

    "isolated":
        True
}

# =====================================================
# 🔥 ANALYZER LOGGING
# =====================================================

def log_engineering_input(

    code,
    context=None
):

    """
    INPUT MACHINE TRACE

    Used by:
    - analyzer
    - admin diagnostics
    - pipeline tracing
    - architecture observability
    """

    return {

        "file_id":
            "APRIL_ENGINEERING_ANALYZER_CORE",

        "event":
            "engineering_input",

        "channel":
            ENGINEERING_TASK_CHANNEL,

        "code_length":
            len(code or ""),

        "context":
            context or {},

        "machine_only":
            True
    }


def log_engineering_output(
    analysis
):

    """
    OUTPUT MACHINE TRACE

    Used by:
    - analyzer
    - architecture diagnostics
    - pipeline monitoring
    """

    return {

        "file_id":
            "APRIL_ENGINEERING_ANALYZER_CORE",

        "event":
            "engineering_output",

        "channel":
            ENGINEERING_RESPONSE_CHANNEL,

        "semantic_score":
            analysis.get(
                "semantic_score",
                0.0
            ),

        "architecture_related":
            analysis.get(
                "architecture_related",
                False
            ),

        "renderer_related":
            analysis.get(
                "renderer_related",
                False
            ),

        "machine_only":
            True
    }

# =====================================================
# 🔥 HELPERS
# =====================================================

def normalize_text(text):

    return (
        text or ""
    ).strip()


def contains_any(
    text,
    words
):

    return any(
        w in text
        for w in words
    )

# =====================================================
# 🔥 ENGINEERING SEMANTICS
# =====================================================

ENGINEERING_SIGNALS = [

    "bug",
    "error",
    "exception",
    "traceback",
    "fix",
    "issue",
    "problem",
    "architecture",
    "logic",
    "routing",
    "renderer",
    "executor",
    "pipeline",
    "payload",
    "response",
    "graph",
    "table",
    "diagram",
    "continuity",
    "modality",
    "scene",
    "render"
]

CODE_SIGNALS = [

    "def ",
    "class ",
    "import ",
    "return ",
    "async ",
    "await ",
    "function ",
    "const ",
    "let ",
    "var ",
    "{",
    "}",
    "=>"
]

# =====================================================
# 🔥 ENGINEERING ANALYSIS
# =====================================================

def analyze_engineering_semantics(
    code: str
):

    log_engineering_input(code)

    text = normalize_text(
        code
    ).lower()

    result = {

        "engineering_context":
            False,

        "renderer_related":
            False,

        "architecture_related":
            False,

        "code_detected":
            False,

        "pipeline_related":
            False,

        "semantic_score":
            0.0,

        "machine_channel":
            ENGINEERING_RESPONSE_CHANNEL
    }

    score = 0.0

    # =================================================
    # 🔥 ENGINEERING
    # =====================================================

    if contains_any(
        text,
        ENGINEERING_SIGNALS
    ):

        result[
            "engineering_context"
        ] = True

        score += 0.45

    # =================================================
    # 🔥 CODE
    # =====================================================

    if contains_any(
        text,
        CODE_SIGNALS
    ):

        result[
            "code_detected"
        ] = True

        score += 0.35

    # =================================================
    # 🔥 RENDERER
    # =====================================================

    if contains_any(

        text,

        [
            "renderer",
            "graph",
            "diagram",
            "scene",
            "payload",
            "modality"
        ]
    ):

        result[
            "renderer_related"
        ] = True

        score += 0.25

    # =================================================
    # 🔥 ARCHITECTURE
    # =====================================================

    if contains_any(

        text,

        [
            "executor",
            "pipeline",
            "routing",
            "architecture",
            "continuity"
        ]
    ):

        result[
            "architecture_related"
        ] = True

        result[
            "pipeline_related"
        ] = True

        score += 0.25

    result[
        "semantic_score"
    ] = min(score, 1.0)

    log_engineering_output(
        result
    )

    return result

# =====================================================
# 🔥 PROMPT BUILDER
# =====================================================

def build_engineering_prompt(
    code: str
):

    """
    Structured engineering prompt builder.

    Preserves:
    - architecture integrity
    - renderer continuity
    - execution stability
    """

    semantics = analyze_engineering_semantics(
        code
    )

    system_lines = [

        "Ты engineering analysis system.",

        "Главная задача:",

        "- находить архитектурные проблемы;",
        "- находить pipeline conflicts;",
        "- находить renderer conflicts;",
        "- находить execution mismatch;",
        "- предлагать безопасные исправления;",
        "- сохранять continuity architecture;",
        "- избегать destructive rewrites;",
        "- избегать hidden escalation;"
    ]

    # =================================================
    # 🔥 RENDERER
    # =====================================================

    if semantics.get(
        "renderer_related"
    ):

        system_lines.extend([

            "",

            "Renderer context active:",

            "- preserve renderer payloads;",
            "- avoid flattening;",
            "- avoid text downgrade;",
            "- preserve modality;"
        ])

    # =================================================
    # 🔥 PIPELINE
    # =====================================================

    if semantics.get(
        "pipeline_related"
    ):

        system_lines.extend([

            "",

            "Pipeline context active:",

            "- preserve orchestration;",
            "- preserve execution flow;",
            "- preserve structured return;"
        ])

    system_lines.extend([

        "",

        "Формат ответа:",

        "🛠 ENGINEERING REPORT",

        "",

        "Проблемы:",
        "- ...",

        "",

        "Решение:",
        "(код)"
    ])

    prompt = (

        "\n".join(system_lines)

        + "\n\nКод:\n"

        + code
    )

    return {

        "channel":
            ENGINEERING_RESPONSE_CHANNEL,

        "file_id":
            "APRIL_ENGINEERING_ANALYZER_CORE",

        "prompt":
            prompt,

        "renderer_safe":
            True,

        "machine_only":
            True
    }

# =====================================================
# 🔥 MAIN API
# =====================================================

def analyze_code(
    code: str
) -> str:

    """
    Main engineering analysis entry.

    Used internally by:
    - Executor
    - analyzer systems
    - architecture diagnostics
    - admin engineering tools
    """

    payload = build_engineering_prompt(
        code
    )

    r = client.responses.create(

        model="gpt-4o-mini",

        input=payload.get(
            "prompt"
        )
    )

    return r.output_text
