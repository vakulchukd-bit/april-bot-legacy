from openai import OpenAI
import os

# =====================================================
# 🧠 APRIL ENGINEERING ANALYZER
# =====================================================

"""
Engineering helper.

Этот слой:

✅ помогает engineering analysis
✅ помогает executor
✅ помогает code reasoning
✅ помогает structured diagnostics

❌ НЕ renderer authority
❌ НЕ orchestration layer
❌ НЕ trigger system
❌ НЕ final response formatter

Главная задача:
semantic engineering understanding.
"""

# =====================================================
# 🔥 OPENAI
# =====================================================

client = OpenAI(
    api_key=os.getenv(
        "OPENAI_API_KEY"
    )
)

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
# 🔥 ANALYSIS
# =====================================================

def analyze_engineering_semantics(
    code: str
):

    text = normalize_text(code).lower()

    result = {

        "engineering_context": False,

        "renderer_related": False,

        "architecture_related": False,

        "code_detected": False,

        "pipeline_related": False,

        "semantic_score": 0.0
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

    return result


# =====================================================
# 🔥 PROMPT BUILDER
# =====================================================

def build_engineering_prompt(
    code: str
):

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

    return (

        "\n".join(system_lines)

        + "\n\nКод:\n"

        + code
    )


# =====================================================
# 🔥 MAIN API
# =====================================================

def analyze_code(
    code: str
) -> str:

    prompt = build_engineering_prompt(
        code
    )

    r = client.responses.create(

        model="gpt-4o-mini",

        input=prompt
    )

    return r.output_text
