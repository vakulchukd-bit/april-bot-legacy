# 🧠 APRIL ROOMS REGISTRY
# =====================================================
#
# APRIL_FILE_ID:
# APRIL_ROOMS_REGISTRY
#
# ROLE:
# ROOM_EXECUTION_REGISTRY
#
# INPUT:
# USER_TEXT
# SEMANTIC_CONTEXT
# COGNITION_CONTEXT
# ROOM_CONTEXT
# EXECUTION_CONTEXT
#
# OUTPUT:
# ROOM_CAPABILITIES
# ROOM_EXECUTION_RESULT
# MACHINE_ARTIFACTS
#
# DEPENDENCIES:
# room_protocol
# image_engine
# image_system
# science_room
# text_module
# excrouter
#
# =====================================================
#
# APRIL ROOMS REGISTRY
#
# Этот слой:
# - room registry;
# - execution-safe orchestration layer;
# - continuity-safe room collection;
# - multimodal routing bridge.
#
# Этот слой НЕ:
# - Telegram dispatcher;
# - routing authority;
# - semantic core;
# - renderer authority.
#
# =====================================================


# =====================================================
# 🔥 IMPORTS
# =====================================================

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import (
    MachineRequest,
    MachineResponse,
    UniversalArtifactContract,
)


# =====================================================
# 🔥 IMAGE
# =====================================================

from blocks.image_engine import (
    generate as image_generate
)

from blocks.image_engine import (
    edit as image_edit_engine
)

from blocks.image_system import (
    analyze_image
)

# =====================================================
# 🔥 SCIENCE
# =====================================================

from blocks.science_room import (
    ScienceRoom
)

import time
import re

# =====================================================
# 🔥 C ROOMS
# =====================================================

from blocks.C_MATHEMATICS_ROOM import ROOM as MATHEMATICS_ROOM
from blocks.C_TRIGONOMETRY_ROOM import ROOM as TRIGONOMETRY_ROOM
from blocks.C_PHYSICS_ROOM import ROOM as PHYSICS_ROOM
from blocks.C_CHEMISTRY_ROOM import ROOM as CHEMISTRY_ROOM
from blocks.C_BIOLOGY_ROOM import ROOM as BIOLOGY_ROOM
from blocks.C_LITERATURE_ROOM import ROOM as LITERATURE_ROOM
from blocks.C_WEB_ROOM import ROOM as WEB_ROOM
from blocks.C_UTC_ROOM import ROOM as UTC_ROOM
from blocks.C_ENGINEERING_ROOM import ROOM as ENGINEERING_ROOM
from blocks.C_POLITICS_ROOM import ROOM as POLITICS_ROOM
from blocks.C_NEWS_ROOM import ROOM as NEWS_ROOM
from blocks.C_SOCIAL_ROOM import ROOM as SOCIAL_ROOM
from blocks.C_IT_ROOM import ROOM as IT_ROOM


# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

INPUT_MACHINE_CHANNEL = {

    "source":
        "excrouter",

    "target":
        "rooms_registry",

    "isolated":
        True
}

OUTPUT_MACHINE_CHANNEL = {

    "source":
        "rooms_registry",

    "target":
        "executor",

    "isolated":
        True
}

# =====================================================
# 🔥 PATCH LOG
# =====================================================

ROOMS_PATCH_LOG = []

def safe_rooms_log(*args):
    # Lightweight: keep hook but avoid console spam.
    return


# =====================================================
# 🔥 SAFE IMAGE LOCK
# =====================================================

def is_repeat_generation_blocked(state):

    ts = state.get(
        "last_image_time"
    )

    if not ts:
        return False

    return (
        time.time() - ts
    ) < 8


def mark_generation_time(state):

    state[
        "last_image_time"
    ] = time.time()


def is_image_locked(state):

    return (
        state.get(
            "image_locked"
        ) is True
    )


def unlock_image(state):

    state[
        "image_locked"
    ] = False


# =====================================================
# 🔥 SAFE EXECUTOR CONTEXT
# =====================================================

def get_executor_context(context):

    # Canonical MachineRequest support
    if isinstance(context, MachineRequest):
        return {
            "machine_request": context,
            "state": {"machine_request": context},
            "chat_id": getattr(getattr(context, "identity", None), "user_id", None),
            "energy": "MEDIUM",
            "cognition": {},
            "semantic": {},
        }

    if not isinstance(context, dict):
        return {}

    return context.get(
        "context",
        context
    )


def get_chat_id(context):

    executor_context = get_executor_context(
        context
    )

    return executor_context.get(
        "chat_id"
    )


def get_state(context):

    executor_context = get_executor_context(
        context
    )

    state = executor_context.get("state", {})

    if isinstance(context, MachineRequest):
        state["machine_request"] = context

    return state


def get_cognition(context):

    executor_context = get_executor_context(
        context
    )

    return executor_context.get(
        "cognition",
        {}
    )



# =====================================================
# 🔥 APRIL MODALITY UNDERSTANDING
# =====================================================

def normalize_text(text):

    return (
        text or ""
    ).lower().strip()


def detect_visual_math_signal(text):

    t = normalize_text(text)

    patterns = [

        "график",
        "функция",
        "построй",
        "парабола",
        "синус",
        "косинус",
        "sin(",
        "cos(",
        "tan(",
        "y=",
        "y =",
        "f(x)",
        "f(x) =",
        "x**",
        "^2",
        "^3"
    ]

    if any(
        x in t
        for x in patterns
    ):

        return True

    equation = re.search(

        r"[a-z0-9]+\s*=\s*.+",

        t
    )

    if equation:

        return True

    return False


def detect_code_signal(text):

    t = text or ""

    code_patterns = [

        "import ",
        "from ",
        "export default",
        "const ",
        "let ",
        "var ",
        "function(",
        "=>",
        "return (",
        "className=",
        "</",
        "/>",
        "```",
        "async def",
        "await ",
        "use client",
        "props",
        "typescript",
        "javascript",
        "python",
        ".map(",
        "if (",
        "{",
        "};"
    ]

    hits = 0

    for p in code_patterns:

        if p in t:

            hits += 1

    return hits >= 2


def detect_link_signal(text):

    t = normalize_text(text)

    patterns = [

        "ссылка",
        "url",
        "линк",
        "website",
        "http://",
        "https://"
    ]

    return any(
        x in t
        for x in patterns
    )


def detect_image_signal(text):

    t = normalize_text(text)

    patterns = [

        "нарисуй",
        "создай изображение",
        "сгенерируй",
        "арт",
        "draw",
        "generate image"
    ]

    return any(
        x in t
        for x in patterns
    )



# =====================================================
# 🔥 ROOM INTENT VECTOR
# =====================================================

def build_room_intent_vector(text, context):

    vector = {
        "graph": 0.0,
        "formula": 0.0,
        "function": 0.0,
        "table": 0.0,
        "link": 0.0
    }

    executor_context = get_executor_context(context)

    trajectory = executor_context.get("trajectory")
    cognition = executor_context.get("cognition", {})
    semantic = executor_context.get("semantic", {})

    if trajectory == "graph":
        vector["graph"] += 5.0

    if trajectory == "formula":
        vector["formula"] += 5.0

    if trajectory == "function":
        vector["function"] += 5.0

    if detect_visual_math_signal(text):
        vector["graph"] += 2.0
        vector["formula"] += 1.0

    active_focus = str(
        cognition.get("dynamic_focus", {})
    ).lower()

    render_intent = semantic.get("render_intent", False)

    if render_intent:
        vector["graph"] += 1.5
        vector["formula"] += 1.5
        vector["function"] += 1.5

    if "graph" in active_focus:
        vector["graph"] += 2.0

    if "formula" in active_focus:
        vector["formula"] += 2.0

    return vector



# =====================================================
# 🔥 PROFESSIONAL DISCOVERY LAYER
# =====================================================

PROFESSIONAL_ROOM_CAPABILITIES = {

    "biology": ["biology","genetics","ecology","physiology","microbiology","evolution","living_systems"],
    "chemistry": ["chemistry","reactions","molecules","compounds","laboratory"],
    "physics": ["physics","mechanics","energy","motion","waves"],
    "engineering": ["engineering","systems","design","architecture"],
    "it": ["software","technology","programming","architecture"],
    "politics": ["politics","governance","policy","geopolitics"],
    "news": ["news","events","timeline","sources"],
    "social": ["social","community","audience","engagement"],
    "literature": ["literature","fiction","poetry","authors"]
}

def build_professional_room_vector(context):

    executor_context = get_executor_context(context)

    semantic = executor_context.get("semantic", {})
    cognition = executor_context.get("cognition", {})

    vector = {
        room: 0.0
        for room in PROFESSIONAL_ROOM_CAPABILITIES
    }

    dynamic_focus = str(
        cognition.get("dynamic_focus", "")
    ).lower()

    requested_domain = semantic.get("domain")

    if requested_domain in vector:
        vector[requested_domain] += 10.0

    required_capabilities = semantic.get(
        "required_capabilities",
        []
    )

    for room_name, capabilities in PROFESSIONAL_ROOM_CAPABILITIES.items():

        if room_name in dynamic_focus:
            vector[room_name] += 3.0

        for capability in required_capabilities:

            if capability in capabilities:
                vector[room_name] += 2.0

    return vector


def select_professional_rooms(context):
    # Executor is the single orchestration authority.
    # Registry exposes capabilities only and does not choose winners.
    vector = build_professional_room_vector(context)
    candidates = []

    for room_name, score in vector.items():
        if score > 0:
            candidates.append({
                "room": room_name,
                "score": score
            })

    candidates.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return candidates


# =====================================================
# 🔥 IMAGE GENERATE
# =====================================================

class ImageGenerateRoom(Room):

    name = "image_generate"

    room_type = "visual_generation"

    def can_handle(
        self,
        text,
        context
    ):

        return detect_image_signal(
            text
        )

    def evaluate(
        self,
        text,
        context
    ):

        if detect_image_signal(
            text
        ):

            return 0.92

        return 0.0

    async def handle(
        self,
        user_id,
        text,
        context,
        run
    ):

        safe_rooms_log(
            "IMAGE GENERATE START"
        )

        state = get_state(
            context
        )

        if is_image_locked(
            state
        ):

            return {

                "type": "text",

                "data":
                    "⏳ Уже генерирую изображение..."
            }

        state[
            "image_locked"
        ] = True

        try:

            result = await run(

                get_chat_id(
    context
),

                image_generate(

                    user_id,
                    text,
                    state
                )
            )

            if (
                result
                and result.get(
                    "type"
                ) == "image"
            ):

                state[
                    "last_image_prompt"
                ] = text

                mark_generation_time(
                    state
                )

                safe_rooms_log(
                    "IMAGE GENERATE SUCCESS"
                )

                return result

            return {

                "type": "error",

                "data":
                    "🎨 Ошибка генерации"
            }

        finally:

            unlock_image(
                state
            )


# =====================================================
# 🔥 IMAGE EDIT
# =====================================================

class ImageEditRoom(Room):

    name = "image_edit"

    room_type = "visual_edit"

    def can_handle(
        self,
        text,
        context
    ):

        semantic = context.get(
            "semantic",
            {}
        )

        return semantic.get(
            "room"
        ) == self.name

    def evaluate(
        self,
        text,
        context
    ):

        semantic = context.get(
            "semantic",
            {}
        )

        if semantic.get(
            "room"
        ) == self.name:

            return 0.8

        return 0.0

    async def handle(
        self,
        user_id,
        text,
        context,
        run
    ):

        safe_rooms_log(
            "IMAGE EDIT START"
        )

        state = get_state(
            context
        )

        ctx = state.get(
            "image_context"
        )

        if (
            not ctx
            or not ctx.get("path")
        ):

            return {

                "type": "text",

                "data":
                    "⚠️ Нет изображения"
            }

        try:

            hint = await analyze_image(

                ctx["path"],
                state
            )

        except:

            hint = "изображение"

        prompt = (

            hint
            + ". "
            + text
        )

        image_bytes = state.get(
            "image_current"
        )

        result = await run(

            get_chat_id(
    context
),

            image_edit_engine(

                user_id,
                image_bytes,
                prompt,
                state
            )
        )

        return result


# =====================================================
# 🔥 SCIENCE
# =====================================================

class SafeScienceRoom(ScienceRoom):

    name = "science"

    room_type = "science_renderer"

    # =================================================
    # 🔥 APRIL CAPABILITY DETECTION
    # =====================================================

    def can_handle(
        self,
        text,
        context
    ):

        # =============================================
        # 🔥 CODE PROTECTION
        # =============================================

        if detect_code_signal(
            text
        ):

            return False

        return detect_visual_math_signal(
            text
        )

    # =================================================
    # 🔥 CALM EVALUATION
    # =====================================================

    def evaluate(
        self,
        text,
        context
    ):

        # =============================================
        # 🔥 CODE PROTECTION
        # =============================================

        if detect_code_signal(
            text
        ):

            return 0.0

        score = 0.0

        t = normalize_text(
            text
        )

        # =============================================
        # 🔥 DIRECT GRAPH SIGNAL
        # =============================================

        if detect_visual_math_signal(
            text
        ):

            score += 0.9

        # =============================================
        # 🔥 EXPLICIT GRAPH REQUEST
        # =============================================

        graph_words = [

            "построй",
            "покажи график",
            "нарисуй график"
        ]

        if any(
            x in t
            for x in graph_words
        ):

            score += 0.3

        return score


# =====================================================
# 🔥 TEXT
# =====================================================

class TextRoom(Room):

    name = "text"

    room_type = "dialog"

    def can_handle(
        self,
        text,
        context
    ):

        return True

    # =================================================
    # 🔥 CALM FALLBACK
    # =====================================================

    def evaluate(
        self,
        text,
        context
    ):

        # =============================================
        # 🔥 CODE PRIORITY
        # =============================================

        if detect_code_signal(
            text
        ):

            return 1.0

        # =============================================
        # 🔥 LINK PRIORITY
        # =============================================

        if detect_link_signal(
            text
        ):

            return 0.9

        # =============================================
        # 🔥 MATH / GRAPH
        # =============================================

        if detect_visual_math_signal(
            text
        ):

            return 0.25

        return 0.55

    async def handle(
        self,
        user_id,
        text,
        context,
        run
    ):

        safe_rooms_log(
            "TEXT ROOM START"
        )

        from blocks.text_module import (
            process as text_process
        )

        cognition = get_cognition(
            context
        )

        text_input = text

        if cognition.get(
            "reduce_talking"
        ):

            text_input = (

                "Ответь коротко и по делу.\n\n"

                + text
            )

        result = await run(

            get_chat_id(
                context
            ),

            text_process(

                user_id,

                text_input,

                get_state(
                    context
                ),

                get_executor_context(
                    context
                ).get(
                    "energy",
                    "MEDIUM"
                )
            )
        )

        return result



# =====================================================
# 🧠 GUIDANCE ROOM
# =====================================================

class GuidanceRoom(Room):

    name = "guidance"
    room_type = "assistant_guidance"

    def evaluate(self, text, context):

        cognition = get_cognition(context)

        if cognition.get("assistant_next_step"):
            return 0.95

        return 0.0

    async def handle(self, user_id, text, context, run):

        cognition = get_cognition(context)

        mr = MachineResponse()
        mr.contributions["guidance"] = {
            "next_step": cognition.get("assistant_next_step")
        }
        return mr


class GraphRoom(Room):

    name = "graph"
    room_type = "graph_renderer"

    def evaluate(self, text, context):

        executor_context = get_executor_context(context)
        trajectory = executor_context.get("trajectory")
        active_flow = executor_context.get("active_flow")

        if trajectory == "graph":
            return 8.0

        if isinstance(active_flow, dict) and active_flow.get("type") == "graph":
            return 7.0

        vector = build_room_intent_vector(text, context)
        return max(vector.get("graph", 0.0), 0.0)

    async def handle(self, user_id, text, context, run):

        mr = MachineResponse()
        mr.contributions["graph"] = {
            "knowledge_graph":{"nodes":[],"edges":[],"relations":[]},
            "graph_data":{"nodes":[],"edges":[]},
            "description":"Knowledge graph generated from the current request.",
            "title":"Graph",
            "source":text
        }
        return mr


class FormulaRoom(Room):

    name = "formula"
    room_type = "formula_renderer"

    def evaluate(self, text, context):

        executor_context = get_executor_context(context)

        if executor_context.get("trajectory") == "formula":
            return 8.0

        vector = build_room_intent_vector(text, context)
        return max(vector.get("formula", 0.0), 0.0)

    async def handle(self, user_id, text, context, run):

        mr = MachineResponse()
        mr.contributions["formula"]={
            "formula": extract_formula_candidate(text) or text,
            "title":"Formula",
            "latex":True,
            "variables":True
        }
        return mr


class FunctionRoom(Room):

    name = "function"
    room_type = "function_renderer"

    def evaluate(self, text, context):

        executor_context = get_executor_context(context)

        if executor_context.get("trajectory") == "function":
            return 8.0

        return 0.0

    async def handle(self, user_id, text, context, run):

        mr = MachineResponse()
        mr.contributions["function"]={"source":text}
        return mr


class TableRoom(Room):

    name = "table"
    room_type = "table_renderer"

    def evaluate(self, text, context):

        executor_context = get_executor_context(context)

        if executor_context.get("trajectory") == "table":
            return 8.0

        return 0.0

    async def handle(self, user_id, text, context, run):

        mr = MachineResponse()
        mr.contributions["table"]={
            "title":"Table",
            "source":text,
            **extract_table_payload(text)
        }
        return mr


class LinkRoom(Room):

    name = "link"
    room_type = "link_renderer"

    def evaluate(self, text, context):

        executor_context = get_executor_context(context)

        if executor_context.get("trajectory") == "link":
            return 8.0

        return 0.0

    async def handle(self, user_id, text, context, run):

        mr = MachineResponse()
        mr.contributions["link"]={"source":text}
        return mr


# =====================================================
# 🚀 APRIL V3 ARTIFACT HELPERS
# =====================================================

def build_artifact(
    artifact_type,
    data=None,
    view=None,
    edit=None,
    responsive=None,
    viewer=None
):
    return {
        "type": artifact_type,
        "data": data or {},
        "view": view or {},
        "edit": edit or {"editable": True},
        "responsive": responsive or {
            "desktop": True,
            "tablet": True,
            "mobile": True
        },
        "viewer": viewer or {}
    }


class DiagramRoom(Room):

    name = "diagram"
    room_type = "diagram_renderer"

    def evaluate(self, text, context):
        t = (text or "").lower()
        if any(x in t for x in [
            "схема","diagram","flow","архитектура",
            "pipeline","mindmap","маршрут"
        ]):
            return 7.5
        return 0.0

    async def handle(self, user_id, text, context, run):
        mr = MachineResponse()
        mr.contributions["diagram"] = {
            "title":"Diagram",
            "nodes":[],
            "edges":[],
            "source":text,
            "layout":"vertical",
            "zoom":True,
            "pan":True
        }
        return mr


class CodeRoom(Room):

    name = "code"
    room_type = "code_renderer"

    def evaluate(self, text, context):
        return 8.0 if detect_code_signal(text) else 0.0

    async def handle(self, user_id, text, context, run):
        mr = MachineResponse()
        mr.contributions["code"] = {
            "language":"auto",
            "filename":"generated.txt",
            "source":text,
            "line_numbers":True
        }
        return mr



# =====================================================
# 🚀 ARTIFACT EXTRACTORS V4
# =====================================================

def extract_formula_candidate(text):
    patterns = [
        r"y\s*=\s*[^\n,;]+",
        r"f\(x\)\s*=\s*[^\n,;]+",
        r"[A-Za-zА-Яа-я]+\s*=\s*[^\n,;]+"
    ]
    for p in patterns:
        m = re.search(p, text or "")
        if m:
            return m.group(0).strip()
    return ""

def extract_graph_formula(text):
    formula = extract_formula_candidate(text)
    if formula:
        return formula
    return "y=x"

def extract_table_payload(text):
    return {
        "columns":["Column 1","Column 2"],
        "rows":[["Value 1","Value 2"]]
    }



# =====================================================
# 🚀 PROFESSIONAL ROOM REGISTRY V1
# =====================================================

PROFESSIONAL_ROOMS = {

    "graph": {
        "artifact": "GraphArtifact",
                "quality_target": 0.95
    },

    "formula": {
        "artifact": "FormulaArtifact",
                "quality_target": 0.95
    },

    "table": {
        "artifact": "TableArtifact",
                "quality_target": 0.95
    },

    "diagram": {
        "artifact": "DiagramArtifact",
                "quality_target": 0.95
    },

    "code": {
        "artifact": "CodeArtifact",
                "quality_target": 0.95
    },

    "link": {
        "artifact": "LinkArtifact",
                "quality_target": 0.95
    }
,
    "mathematics": {"artifact":"KnowledgeArtifact","quality_target":0.95},
    "trigonometry": {"artifact":"KnowledgeArtifact","quality_target":0.95},
    "physics": {"artifact":"KnowledgeArtifact","quality_target":0.95},
    "chemistry": {"artifact":"KnowledgeArtifact","quality_target":0.95},
    "biology": {"artifact":"KnowledgeArtifact","quality_target":0.95},
    "literature": {"artifact":"KnowledgeArtifact","quality_target":0.95},
    "web": {"artifact":"KnowledgeArtifact","quality_target":0.95},
    "utc": {"artifact":"KnowledgeArtifact","quality_target":0.95},
    "engineering": {"artifact":"KnowledgeArtifact","quality_target":0.95},
    "politics": {"artifact":"KnowledgeArtifact","quality_target":0.95},
    "news": {"artifact":"KnowledgeArtifact","quality_target":0.95},
    "social": {"artifact":"KnowledgeArtifact","quality_target":0.95},
    "it": {"artifact":"KnowledgeArtifact","quality_target":0.95}

}

# =====================================================
# 🚀 ROOMS
# =====================================================

ROOMS = [

    GuidanceRoom(),

    GraphRoom(),

    FormulaRoom(),


    TableRoom(),

    DiagramRoom(),

    CodeRoom(),

    LinkRoom(),

    SafeScienceRoom(),

    ImageEditRoom(),

    ImageGenerateRoom(),

    MATHEMATICS_ROOM,
    TRIGONOMETRY_ROOM,
    PHYSICS_ROOM,
    CHEMISTRY_ROOM,
    BIOLOGY_ROOM,
    LITERATURE_ROOM,
    WEB_ROOM,
    UTC_ROOM,
    ENGINEERING_ROOM,
    POLITICS_ROOM,
    NEWS_ROOM,
    SOCIAL_ROOM,
    IT_ROOM,

    TextRoom(),
]

# =====================================================
# 🔥 REGISTRY METADATA
# =====================================================

ROOM_REGISTRY_STATE = {

    "registry_ready":
        True,

    "web_space_ready":
        True,

    "renderer_safe":
        True,

    "continuity_safe":
        True,

    "telegram_bound":
        False,

    "machine_isolated":
        True
}


# =====================================================
# APRIL FIBER REGISTRY BRIDGE
# =====================================================


def _machine_response_has_payload(mr):
    if mr is None:
        return False
    return bool(
        getattr(mr, "answer", None)
        or getattr(mr, "content", None)
        or getattr(mr, "summary", None)
        or list(getattr(mr, "render_blocks", []) or [])
        or list(getattr(mr, "artifacts", []) or [])
    )


def _registry_is_text(value):
    return isinstance(value, str) and bool(value.strip())


def _registry_copy_text_field(target, field, value):
    if _registry_is_text(value):
        try:
            setattr(target, field, value.strip())
        except Exception:
            pass


def _registry_copy_structured_field(target, field, value):
    if value in (None, "", [], {}):
        return
    try:
        setattr(target, field, value)
    except Exception:
        pass


def _registry_materialize_response(result):
    """
    Normalize any room result into a MachineResponse without turning internal
    dict/object payloads into human-visible answer/content text.
    """
    if result is None:
        return None

    if isinstance(result, MachineResponse):
        return result

    if isinstance(result, dict) and isinstance(result.get("machine_response"), MachineResponse):
        return result["machine_response"]

    response = MachineResponse()
    payload_seen = False

    # Copy contributions first so room-specific signals are preserved.
    if isinstance(result, dict):
        contributions = result.get("contributions")
        if isinstance(contributions, dict):
            try:
                response.contributions.update(contributions)
                payload_seen = payload_seen or bool(contributions)
            except Exception:
                pass

        artifacts = result.get("artifacts")
        if isinstance(artifacts, list):
            try:
                response.artifacts.extend(artifacts)
                payload_seen = payload_seen or bool(artifacts)
            except Exception:
                pass

        # Preserve canonical text fields only when they are already text.
        for field in (
            "answer", "content", "summary", "response", "explanation",
            "text", "message", "output", "output_text",
        ):
            if field in result:
                value = result.get(field)
                if _registry_is_text(value):
                    _registry_copy_text_field(response, field, value)
                    payload_seen = True

        for field in (
            "scene", "metadata", "scene_plan", "render_priority",
            "provider", "provider_contract", "transport_contract",
            "provider_original_answer", "provider_original_content",
            "processor_input", "provider_source_request",
            "scene_contract", "scene_runtime", "conversation_space",
            "current_turn", "timeline", "dialog", "goal", "goal_hierarchy",
            "focus", "visual_reference", "visual_summary", "active_visual_scene",
            "executor_decision", "executor_presentation_plan",
            "executor_scene_profile", "provider_reference_context",
            "second_circle_context",
        ):
            if field in result and result.get(field) not in (None, "", [], {}):
                _registry_copy_structured_field(response, field, result.get(field))
                payload_seen = True

        render_blocks = result.get("render_blocks")
        if isinstance(render_blocks, list):
            try:
                response.render_blocks = list(render_blocks)
                payload_seen = payload_seen or bool(render_blocks)
            except Exception:
                pass

        # If an artifact-shaped payload is present, keep it in artifacts rather
        # than promoting it to human-visible text.
        artifact = result.get("artifact")
        if artifact is not None and not isinstance(artifact, str):
            try:
                response.artifacts.append(artifact)
                payload_seen = True
            except Exception:
                pass

        return response if payload_seen or _machine_response_has_payload(response) else None

    # Fallback: inspect attributes of custom objects and preserve them safely.
    try:
        if hasattr(result, "__dict__"):
            attrs = {k: v for k, v in vars(result).items() if not k.startswith("_")}
        else:
            attrs = {}
    except Exception:
        attrs = {}

    if not attrs:
        return None

    for field in (
        "answer", "content", "summary", "response", "explanation",
        "text", "message", "output", "output_text",
    ):
        if field in attrs and _registry_is_text(attrs[field]):
            _registry_copy_text_field(response, field, attrs[field])
            payload_seen = True

    for field in (
        "scene", "metadata", "scene_plan", "render_priority",
        "provider", "provider_contract", "transport_contract",
        "provider_original_answer", "provider_original_content",
        "processor_input", "provider_source_request",
        "scene_contract", "scene_runtime", "conversation_space",
        "current_turn", "timeline", "dialog", "goal", "goal_hierarchy",
        "focus", "visual_reference", "visual_summary", "active_visual_scene",
        "executor_decision", "executor_presentation_plan",
        "executor_scene_profile", "provider_reference_context",
        "second_circle_context",
    ):
        if field in attrs and attrs[field] not in (None, "", [], {}):
            _registry_copy_structured_field(response, field, attrs[field])
            payload_seen = True

    artifacts = attrs.get("artifacts")
    if isinstance(artifacts, list):
        try:
            response.artifacts.extend(artifacts)
            payload_seen = payload_seen or bool(artifacts)
        except Exception:
            pass

    contributions = attrs.get("contributions")
    if isinstance(contributions, dict):
        try:
            response.contributions.update(contributions)
            payload_seen = payload_seen or bool(contributions)
        except Exception:
            pass

    render_blocks = attrs.get("render_blocks")
    if isinstance(render_blocks, list):
        try:
            response.render_blocks = list(render_blocks)
            payload_seen = payload_seen or bool(render_blocks)
        except Exception:
            pass

    return response if payload_seen or _machine_response_has_payload(response) else None


def _registry_response_score(response):
    if response is None:
        return -1
    score = 0
    answer = _registry_is_text(getattr(response, "answer", None))
    content = _registry_is_text(getattr(response, "content", None))
    summary = _registry_is_text(getattr(response, "summary", None))

    if answer:
        score += len(getattr(response, "answer")) * 5
    if content:
        score += len(getattr(response, "content")) * 4
    if summary:
        score += len(getattr(response, "summary")) * 3

    blocks = list(getattr(response, "render_blocks", []) or [])
    artifacts = list(getattr(response, "artifacts", []) or [])
    contributions = getattr(response, "contributions", {}) or {}
    scene = getattr(response, "scene", None)

    score += len(blocks) * 150
    score += len(artifacts) * 100
    score += len(contributions) * 8

    if scene not in (None, {}, []):
        score += 50

    if answer and content and summary:
        score += 40

    if any(
        _registry_is_text(getattr(response, field, None))
        for field in ("provider_original_answer", "provider_original_content")
    ):
        score += 20

    return score


def _registry_merge_response_payload(target, source):
    if target is None or source is None:
        return target

    # Keep the strongest text already present unless the target is empty.
    for field in ("answer", "content", "summary"):
        current = getattr(target, field, None)
        incoming = getattr(source, field, None)
        if _registry_is_text(incoming) and not _registry_is_text(current):
            _registry_copy_text_field(target, field, incoming)

    # Merge structural fields conservatively.
    for field in ("scene", "metadata", "scene_plan", "render_priority",
                  "provider", "provider_contract", "transport_contract",
                  "provider_original_answer", "provider_original_content",
                  "processor_input", "provider_source_request",
                  "scene_contract", "scene_runtime", "conversation_space",
                  "current_turn", "timeline", "dialog", "goal", "goal_hierarchy",
                  "focus", "visual_reference", "visual_summary", "active_visual_scene",
                  "executor_decision", "executor_presentation_plan",
                  "executor_scene_profile", "provider_reference_context",
                  "second_circle_context"):
        incoming = getattr(source, field, None)
        if incoming not in (None, "", [], {}):
            current = getattr(target, field, None)
            if current in (None, "", [], {}):
                _registry_copy_structured_field(target, field, incoming)

    # Merge contributions and artifacts.
    try:
        target.contributions.update(getattr(source, "contributions", {}) or {})
    except Exception:
        pass

    try:
        target.artifacts.extend(getattr(source, "artifacts", []) or [])
    except Exception:
        pass

    # Prefer explicit render blocks, but never replace an existing textual answer
    # with a structured payload.
    incoming_blocks = list(getattr(source, "render_blocks", []) or [])
    if incoming_blocks:
        current_blocks = list(getattr(target, "render_blocks", []) or [])
        if not current_blocks:
            try:
                target.render_blocks = list(incoming_blocks)
            except Exception:
                pass

    return target


def registry_accept_request(request: MachineRequest)->MachineRequest:
    return request

def registry_collect_responses(responses):
    """Preserve the strongest text-bearing MachineResponse and merge room signals."""
    mr = None
    best_score = -1

    for r in responses:
        if r is None:
            continue

        candidate = _registry_materialize_response(r)
        if candidate is None:
            continue

        candidate_score = _registry_response_score(candidate)

        if mr is None:
            mr = candidate
            best_score = candidate_score
            continue

        # Keep the strongest text-bearing response as the primary payload, but
        # merge every room's contributions and artifacts into the same response.
        if candidate_score > best_score and _machine_response_has_payload(candidate):
            preserved = mr
            mr = candidate
            best_score = candidate_score
            try:
                mr.contributions.update(getattr(preserved, "contributions", {}) or {})
                mr.artifacts.extend(getattr(preserved, "artifacts", []) or [])
            except Exception:
                pass
        else:
            _registry_merge_response_payload(mr, candidate)

    if mr is None:
        mr = MachineResponse()

    # Normalize empty text fields so downstream code never treats non-text
    # objects as a human answer.
    for field in ("answer", "content", "summary"):
        value = getattr(mr, field, None)
        if not _registry_is_text(value):
            try:
                setattr(mr, field, "")
            except Exception:
                pass

    # If the registry has a text answer but no blocks, provide a plain text
    # block so the executor/web chain has a stable signal to render.
    if _registry_is_text(getattr(mr, "answer", None)) and not list(getattr(mr, "render_blocks", []) or []):
        try:
            mr.render_blocks = [{
                "type": "text",
                "content": getattr(mr, "answer", ""),
                "signal": "TEXT",
                "source_type": "text",
                "renderer": "TextBlock",
                "viewer": "TextBlock",
                "label": "text",
                "priority": 0,
            }]
        except Exception:
            pass

    return mr

def registry_export_contract(response: MachineResponse):
    contract=UniversalArtifactContract()
    contract.transport.origin="rooms_registry"
    contract.transport.destination="executor"
    contract.transport.pipeline_stage="registry_output"
    contract.payload.artifacts = list(getattr(response, "artifacts", []) or [])
    try:
        contract.payload.render_blocks = list(getattr(response, "render_blocks", []) or [])
    except Exception:
        pass
    try:
        contract.payload.answer = getattr(response, "answer", "")
        contract.payload.content = getattr(response, "content", "")
        contract.payload.summary = getattr(response, "summary", "")
    except Exception:
        pass
    if getattr(response, "artifacts", []):
        contract.artifact=response.artifacts[0]
    return contract


# =====================================================
# 🧠 EXECUTOR CPU REGISTRY BRIDGE (Stage 1)
# =====================================================

REGISTRY_CPU_TRACE = {
    "enabled": False,
    "history": [],
}

def registry_trace(stage, **payload):
    if not REGISTRY_CPU_TRACE["enabled"]:
        return
    REGISTRY_CPU_TRACE["history"].append({
        "stage": stage,
        "payload": payload,
    })

def registry_execute(machine_request: MachineRequest, room_results):
    """
    Canonical entrypoint used by Executor.
    Aggregates room results into one MachineResponse without allowing internal
    room payloads to replace the canonical human-facing answer.
    """
    registry_trace("request_received", request_type=type(machine_request).__name__)

    response = registry_collect_responses(room_results)

    response.contributions.setdefault(
        "registry",
        {
            "rooms_processed": len(room_results),
            "artifacts": len(getattr(response, "artifacts", []) or []),
            "has_text": bool(_registry_is_text(getattr(response, "answer", None))),
        },
    )

    # Preserve request provenance for diagnostics without exposing it as answer.
    try:
        response.contributions.setdefault(
            "request_provenance",
            {
                "request_type": type(machine_request).__name__,
                "machine_request_present": machine_request is not None,
            },
        )
    except Exception:
        pass

    registry_trace(
        "response_ready",
        artifacts=len(getattr(response, "artifacts", []) or []),
        contributions=list(getattr(response, "contributions", {}).keys()),
    )

    response = registry_validate_response(response)
    return response


# =====================================================
# 🧠 PARENT ROOM DISPATCH (Stage 2)
# =====================================================

PARENT_ROOM_GROUPS = {
    "knowledge": [
        "mathematics","trigonometry","physics","chemistry",
        "biology","literature","engineering","it","web",
        "politics","news","social","utc"
    ],
    "presentation": [
        "graph","formula","table","diagram","code","link"
    ],
    "visual": [
        "image_generate","image_edit"
    ],
    "dialog": [
        "text","guidance"
    ],
}

def registry_execution_summary(response: MachineResponse):
    return {
        "artifacts": len(getattr(response, "artifacts", []) or []),
        "contributions": sorted(list(getattr(response, "contributions", {}).keys())),
        "parent_groups": list(PARENT_ROOM_GROUPS.keys()),
        "has_text": bool(_registry_is_text(getattr(response, "answer", None))),
        "has_render_blocks": bool(list(getattr(response, "render_blocks", []) or [])),
    }

def registry_parent_dispatch(machine_request: MachineRequest, room_results):
    """
    Canonical parent-dispatch endpoint.
    Executor calls only this API.
    """
    response = registry_execute(machine_request, room_results)
    response.contributions.setdefault(
        "registry_summary",
        registry_execution_summary(response)
    )
    registry_trace(
        "parent_dispatch_complete",
        summary=response.contributions["registry_summary"]
    )
    return response


# =====================================================
# 🧠 MACHINE RESPONSE VALIDATION (Stage 3)
# =====================================================

REQUIRED_RESPONSE_FIELDS = (
    "artifacts",
    "contributions",
)

def registry_validate_response(response: MachineResponse):
    diagnostics = {
        "valid": True,
        "missing": [],
        "artifact_count": len(getattr(response, "artifacts", [])),
        "contribution_count": len(getattr(response, "contributions", {})),
        "has_text": bool(_registry_is_text(getattr(response, "answer", None))),
        "has_render_blocks": bool(list(getattr(response, "render_blocks", []) or [])),
    }

    for field in REQUIRED_RESPONSE_FIELDS:
        if not hasattr(response, field):
            diagnostics["valid"] = False
            diagnostics["missing"].append(field)

    # Keep the canonical text fields safe and predictable.
    for field in ("answer", "content", "summary"):
        value = getattr(response, field, None)
        if not _registry_is_text(value):
            try:
                setattr(response, field, "")
            except Exception:
                pass

    # Ensure a plain text render block exists whenever a canonical answer exists.
    if _registry_is_text(getattr(response, "answer", None)) and not list(getattr(response, "render_blocks", []) or []):
        try:
            response.render_blocks = [{
                "type": "text",
                "content": getattr(response, "answer", ""),
                "signal": "TEXT",
                "source_type": "text",
                "renderer": "TextBlock",
                "viewer": "TextBlock",
                "label": "text",
                "priority": 0,
            }]
        except Exception:
            pass

    response.contributions.setdefault(
        "registry_diagnostics",
        diagnostics
    )

    registry_trace("validation_complete", **diagnostics)
    return response
