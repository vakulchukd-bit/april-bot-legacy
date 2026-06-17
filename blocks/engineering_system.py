# =====================================================
# 🧠 APRIL ENGINEERING ANALYZER CORE
# =====================================================

from openai import OpenAI
import os

# =====================================================
# 🧠 APRIL ENGINEERING ANALYZER
# =====================================================

"""
APRIL ENGINEERING ANALYZER CORE

APRIL_FILE_ID:
APRIL_ENGINEERING_ANALYZER_CORE

ROLE:
ENGINEERING_REASONING_AND_DIAGNOSTICS

INPUT:
CODE_INPUT
PIPELINE_STRUCTURES
ARCHITECTURE_CONTEXT
RENDERER_PAYLOADS
EXECUTION_ERRORS

OUTPUT:
ENGINEERING_REPORT
SAFE_FIX_RECOMMENDATIONS
PIPELINE_DIAGNOSTICS
STRUCTURED_ANALYSIS

THIS FILE IS:
- engineering analysis helper
- executor support layer
- structured diagnostics system
- architecture reasoning helper
- continuity-safe analyzer
- pipeline diagnostics bridge

THIS FILE IS NOT:
- renderer authority
- orchestration engine
- execution router
- response formatter
- trigger system
- frontend layer

GOLDEN APRIL RULES:
- preserve continuity
- preserve orchestration structure
- avoid destructive rewrites
- avoid hidden escalation
- preserve renderer payloads
- stabilize execution flow
"""

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
# 🔥 OPENAI
# =====================================================

client = OpenAI(
    api_key=os.getenv(
        "OPENAI_API_KEY"
    )
)

# =====================================================
# 🔥 PIPELINE LOGGING
# =====================================================

def log_engineering_input(

    semantic_score=None,
    pipeline_related=False,
    renderer_related=False
):

    """
    INPUT MACHINE TRACE

    Used by:
    - analyzer
    - governance
    - admin diagnostics
    """

    return {

        "file_id":
            "APRIL_ENGINEERING_ANALYZER_CORE",

        "event":
            "engineering_input",

        "channel":
            ENGINEERING_TASK_CHANNEL,

        "semantic_score":
            semantic_score,

        "pipeline_related":
            pipeline_related,

        "renderer_related":
            renderer_related,

        "machine_only":
            True
    }


def log_engineering_output(

    success=True,
    report_generated=True
):

    """
    OUTPUT MACHINE TRACE

    Used internally by:
    - admin analytics
    - analyzer
    - recovery diagnostics
    """

    return {

        "file_id":
            "APRIL_ENGINEERING_ANALYZER_CORE",

        "event":
            "engineering_output",

        "channel":
            ENGINEERING_RESPONSE_CHANNEL,

        "success":
            success,

        "report_generated":
            report_generated,

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
# 🔥 ANALYSIS
# =====================================================

def analyze_engineering_semantics(
    code: str
):

    """
    Semantic engineering understanding.

    Detects:
    - renderer context
    - pipeline structures
    - architecture semantics
    - code reasoning relevance
    """

    text = normalize_text(code).lower()

    result = {

        "engineering_context": False,

        "renderer_related": False,

        "architecture_related": False,

        "code_detected": False,

        "pipeline_related": False,

        "semantic_score": 0.0,

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

    return result

# =====================================================
# 🔥 PROMPT BUILDER
# =====================================================

def build_engineering_prompt(
    code: str
):

    """
    Safe engineering analysis prompt.

    Preserves:
    - continuity architecture
    - renderer payload integrity
    - orchestration stability
    """

    semantics = analyze_engineering_semantics(
        code
    )

    log_engineering_input(

        semantic_score=semantics.get(
            "semantic_score"
        ),

        pipeline_related=semantics.get(
            "pipeline_related"
        ),

        renderer_related=semantics.get(
            "renderer_related"
        )
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
# 🚀 APRIL PROFESSIONAL ENGINEERING CONTRACT
# =====================================================

class WorkOrder:

    def __init__(
        self,
        goal=None,
        purpose=None,
        role=None,
        dependencies=None,
        expected_artifact=None,
        quality_target=0.95,
        active_scene=None
    ):
        self.goal = goal
        self.purpose = purpose
        self.role = role
        self.dependencies = dependencies or []
        self.expected_artifact = expected_artifact
        self.quality_target = quality_target
        self.active_scene = active_scene

    def to_dict(self):

        return {
            "goal": self.goal,
            "purpose": self.purpose,
            "role": self.role,
            "dependencies": self.dependencies,
            "expected_artifact": self.expected_artifact,
            "quality_target": self.quality_target,
            "active_scene": self.active_scene
        }


PROFESSIONAL_ARTIFACT_TARGETS = {

    "graph": "GraphArtifact",
    "formula": "FormulaArtifact",
    "table": "TableArtifact",
    "diagram": "DiagramArtifact",
    "code": "CodeArtifact",
    "link": "LinkArtifact"
}


# =====================================================
# 🔥 MAIN API
# =====================================================

def analyze_code(
    code: str
) -> str:

    """
    Main engineering analysis API.

    Used by:
    - Executor
    - diagnostics systems
    - admin engineering tools
    - pipeline debugging
    """

    prompt = build_engineering_prompt(
        code
    )

    r = client.responses.create(

        model="gpt-4o-mini",

        input=prompt
    )

    log_engineering_output(

        success=True,

        report_generated=True
    )

    return r.output_text



# =====================================================
# 🚀 APRIL EXPERT ROOM TARGETS
# =====================================================

EXPERT_ROOM_TARGETS = {

    "mathematics": "FunctionArtifact",
    "trigonometry": "FunctionArtifact",
    "physics": "FunctionArtifact",
    "chemistry": "FunctionArtifact",
    "biology": "FunctionArtifact",

    "literature": "FunctionArtifact",

    "web": "LinkArtifact",

    "utc": "FunctionArtifact",

    "engineering": "FunctionArtifact",
    "politics": "FunctionArtifact",
    "news": "FunctionArtifact",
    "social": "FunctionArtifact",
    "it": "FunctionArtifact"
}

PROFESSIONAL_ARTIFACT_TARGETS.update(
    EXPERT_ROOM_TARGETS
)
