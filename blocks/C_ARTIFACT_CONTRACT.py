from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import uuid
import time

# =====================================================
# ARTIFACT METADATA
# =====================================================

@dataclass
class ArtifactMetadata:

    artifact_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )

    artifact_version: str = "1.0"

    created_at: float = field(
        default_factory=time.time
    )

    room_source: str = ""

    artifact_type: str = ""

# =====================================================
# ARTIFACT CONTEXT
# =====================================================

@dataclass
class ArtifactContext:

    goal: Optional[str] = None

    purpose: Optional[str] = None

    role: Optional[str] = None

    active_scene: Optional[str] = None

    dependencies: List[str] = field(
        default_factory=list
    )

    # =================================================
    # PROFESSIONAL ROOM PROFILE
    # =================================================

    domain: Optional[str] = None

    specialization: Optional[str] = None

    knowledge_class: Optional[str] = None

    knowledge_scope: List[str] = field(
        default_factory=list
    )

    capabilities: List[str] = field(
        default_factory=list
    )

    research_capabilities: List[str] = field(
        default_factory=list
    )

    experiment_capabilities: List[str] = field(
        default_factory=list
    )

    artifact_outputs: List[str] = field(
        default_factory=list
    )

    # =================================================
    # COGNITIVE CONTRIBUTIONS
    # =================================================

    scene_contributions: List[Dict] = field(
        default_factory=list
    )

    focus_contributions: List[Dict] = field(
        default_factory=list
    )

    memory_contributions: List[Dict] = field(
        default_factory=list
    )

    trajectory_hints: List[str] = field(
        default_factory=list
    )

    scene_hints: List[str] = field(
        default_factory=list
    )


# =====================================================
# ARTIFACT QUALITY
# =====================================================

@dataclass
class ArtifactQuality:

    quality_score: float = 0.0

    confidence_score: float = 0.0

    completeness_score: float = 0.0

    validation_passed: bool = False

    warnings: List[str] = field(
        default_factory=list
    )


# =====================================================
# CANONICAL TEXT / PAYLOAD NORMALIZATION
# =====================================================

_CANONICAL_TEXT_KEYS = (
    "answer",
    "content",
    "summary",
    "text",
    "response",
    "explanation",
    "display_text",
    "title",
    "message",
)

_STRUCTURED_PAYLOAD_KEYS = (
    "domain",
    "topic",
    "analysis",
    "capabilities",
    "knowledge_scope",
    "research_capabilities",
    "experiment_capabilities",
    "artifact_outputs",
    "scene_contributions",
    "focus_contributions",
    "memory_contributions",
    "trajectory_hints",
    "scene_hints",
    "room_identity",
)

def _extract_text_candidate(value: Any, *, allow_topic: bool = False) -> str:
    """Return a safe human-readable string without stringifying raw dicts."""
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, (int, float, bool)):
        return str(value).strip()

    if isinstance(value, dict):
        for key in _CANONICAL_TEXT_KEYS:
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()

        if allow_topic:
            topic = value.get("topic")
            if isinstance(topic, str) and topic.strip():
                return topic.strip()

        for key in ("label", "name", "kind", "type", "renderer", "viewer"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()

        return ""

    if isinstance(value, (list, tuple, set)):
        parts = []
        for item in value:
            candidate = _extract_text_candidate(item, allow_topic=allow_topic)
            if candidate:
                parts.append(candidate)
        return ", ".join(parts)

    try:
        return str(value).strip()
    except Exception:
        return ""


def _canonicalize_artifact_data(
    data: Dict[str, Any],
    *,
    artifact_type: str = "",
    room_source: str = "",
) -> Dict[str, Any]:
    """Keep internal payloads structured while preserving visible text fields."""
    payload = dict(data or {})

    structured_payload = payload.get("payload")
    if structured_payload is None:
        structured_payload = {
            key: value
            for key, value in payload.items()
            if key not in _CANONICAL_TEXT_KEYS
            and key not in ("presentation", "machine_only", "human_visible")
        }

    canonical_text = ""
    for key in _CANONICAL_TEXT_KEYS:
        canonical_text = _extract_text_candidate(payload.get(key))
        if canonical_text:
            break

    machine_only = bool(payload.get("machine_only", False))
    human_visible = payload.get("human_visible")
    if human_visible is None:
        human_visible = not machine_only

    # If the payload is purely structural, default it to machine-only before
    # any topic/title fallback can leak internal payloads into the UI.
    if not canonical_text and structured_payload and payload.get("human_visible") is None and payload.get("machine_only") is None:
        machine_only = True
        human_visible = False

    if not canonical_text and not human_visible and _extract_text_candidate(payload.get("display_text")):
        canonical_text = _extract_text_candidate(payload.get("display_text"))

    if not canonical_text and human_visible and not machine_only:
        canonical_text = _extract_text_candidate(payload.get("topic"), allow_topic=True)
        if not canonical_text:
            canonical_text = _extract_text_candidate(payload.get("title"))

    normalized = dict(payload)
    normalized["artifact_type"] = artifact_type or normalized.get("artifact_type", "")
    normalized["room_source"] = room_source or normalized.get("room_source", "")
    normalized["machine_only"] = machine_only
    normalized["human_visible"] = bool(human_visible)
    normalized["payload"] = structured_payload

    normalized["answer"] = canonical_text
    normalized["content"] = canonical_text
    normalized["summary"] = canonical_text
    normalized["text"] = canonical_text
    normalized.setdefault("display_text", canonical_text)

    normalized.setdefault(
        "signal",
        {
            "artifact_type": normalized["artifact_type"],
            "room_source": normalized["room_source"],
            "machine_only": normalized["machine_only"],
            "human_visible": normalized["human_visible"],
        },
    )

    return normalized


def _scene_is_internal_only(scene: Any) -> bool:
    metadata = {}
    if hasattr(scene, "metadata"):
        metadata = getattr(scene, "metadata") or {}
    elif isinstance(scene, dict):
        metadata = scene.get("metadata", {}) or {}

    return bool(metadata.get("machine_only")) or metadata.get("human_visible") is False


def _scene_text_fallback(scene: Any) -> str:
    for attr in ("answer", "content", "summary"):
        if hasattr(scene, attr):
            candidate = _extract_text_candidate(getattr(scene, attr))
            if candidate:
                return candidate
    if isinstance(scene, dict):
        for key in ("answer", "content", "summary"):
            candidate = _extract_text_candidate(scene.get(key))
            if candidate:
                return candidate
    return ""

# =====================================================
# RENDER CONTRACT
# =====================================================


@dataclass
class ArtifactRenderContract:

    web_block: str = ""

    viewer: str = ""

    editable: bool = True

    responsive: bool = True

    exportable: bool = True

    machine_only: bool = False

    human_visible: bool = True

    # Stage 1 transport hints
    payload_type: str = ""
    scene_block: str = ""
    renderer: str = ""
    priority: int = 100
    complexity: str = "balanced"
    layout: str = "single"

# =====================================================
# BASE ARTIFACT
# =====================================================

@dataclass
class BaseArtifact:

    metadata: ArtifactMetadata

    context: ArtifactContext

    quality: ArtifactQuality

    render: ArtifactRenderContract

    data: Dict[str, Any] = field(
        default_factory=dict
    )

# =====================================================
# BLOCK MAP
# =====================================================

ARTIFACT_BLOCK_MAP = {
    "text": "TextBlock",
    "markdown": "MarkdownBlock",
    "graph": "GraphBlock",

    "formula": "FormulaBlock",

    "table": "TableBlock",

    "diagram": "DiagramBlock",

    "code": "CodeBlock",

    "link": "LinkCard",

    "gallery": "GalleryBlock",

    "function": "FunctionBlock"
}

# =====================================================
# FACTORY ROOM MAP
# =====================================================

FACTORY_ROOM_MAP = {

    "graph": "C_GRAPH_ROOM",

    "formula": "C_FORMULA_ROOM",

    "table": "C_TABLE_ROOM",

    "diagram": "C_DIAGRAM_ROOM",


    "link": "C_LINK_ROOM",

    "gallery": "C_GALLERY_ROOM",

    "function": "C_FUNCTION_ROOM",

    "mathematics": "C_MATHEMATICS_ROOM",

    "trigonometry": "C_TRIGONOMETRY_ROOM",

    "physics": "C_PHYSICS_ROOM",

    "chemistry": "C_CHEMISTRY_ROOM",

    "biology": "C_BIOLOGY_ROOM",

    "literature": "C_LITERATURE_ROOM",

    "web": "C_WEB_ROOM",

    "utc": "C_UTC_ROOM",

    "engineering": "C_ENGINEERING_ROOM",

    "politics": "C_POLITICS_ROOM",

    "news": "C_NEWS_ROOM",

    "social": "C_SOCIAL_ROOM",

    "it": "C_IT_ROOM"
}

# =====================================================
# FACTORY STATUS
# =====================================================

FACTORY_STATUS = {

    "visual_rooms": True,

    "science_rooms": True,

    "knowledge_rooms": True,

    "professional_rooms": True
}

# =====================================================
# CREATE ARTIFACT
# =====================================================


def create_artifact(
    artifact_type: str,
    room_source: str,
    data: Dict[str, Any]
):

    normalized_data = _canonicalize_artifact_data(
        data,
        artifact_type=artifact_type,
        room_source=room_source,
    )

    room_identity = normalized_data.get(
        "room_identity",
        {}
    )

    render_block = ARTIFACT_BLOCK_MAP.get(
        artifact_type,
        "FunctionBlock"
    )

    return BaseArtifact(

        metadata=ArtifactMetadata(

            artifact_type=
                artifact_type,

            room_source=
                room_source
        ),

        context=ArtifactContext(

            domain=normalized_data.get(
                "domain"
            ),

            specialization=room_identity.get(
                "specialization"
            ),

            knowledge_class=room_identity.get(
                "knowledge_class"
            ),

            knowledge_scope=normalized_data.get(
                "knowledge_scope",
                []
            ),

            capabilities=normalized_data.get(
                "capabilities",
                []
            ),

            research_capabilities=normalized_data.get(
                "research_capabilities",
                []
            ),

            experiment_capabilities=normalized_data.get(
                "experiment_capabilities",
                []
            ),

            artifact_outputs=normalized_data.get(
                "artifact_outputs",
                []
            ),

            scene_contributions=normalized_data.get(
                "scene_contributions",
                []
            ),

            focus_contributions=normalized_data.get(
                "focus_contributions",
                []
            ),

            memory_contributions=normalized_data.get(
                "memory_contributions",
                []
            ),

            trajectory_hints=normalized_data.get(
                "trajectory_hints",
                []
            ),

            scene_hints=normalized_data.get(
                "scene_hints",
                []
            )
        ),

        quality=ArtifactQuality(),

        render=ArtifactRenderContract(

            web_block=
                render_block,

            viewer=
                render_block,

            renderer=
                render_block,

            scene_block=
                artifact_type,

            payload_type=
                artifact_type,

            priority=
                normalized_data.get("priority", 100),

            complexity=
                normalized_data.get("complexity", "balanced"),

            layout=
                normalized_data.get("layout", "single"),

            machine_only=
                bool(normalized_data.get("machine_only", False)),

            human_visible=
                bool(normalized_data.get("human_visible", True))
        ),

        data=normalized_data
    )

# =====================================================
# FIBER INSPECTION API
# =====================================================

TRACE_STAGES = [
    "CONTRACT","REGISTRY","ROOM","OPENAI_REQUEST",
    "OPENAI_RESPONSE","EXECUTOR","SCENE","WEB","DONE"
]

def build_trace_snapshot(trace: TraceContract) -> Dict[str, Any]:
    return {
        "trace_id": trace.trace_id,
        "lane": trace.lane,
        "stage": trace.stage,
        "room": trace.room,
        "elapsed_ms": trace.elapsed_ms,
        "status": trace.status,
    }

def build_metrics_snapshot(metrics: MetricsContract) -> Dict[str, Any]:
    return {
        "payload_size": metrics.payload_size,
        "block_count": metrics.block_count,
        "attachment_count": metrics.attachment_count,
        "elapsed_ms": metrics.elapsed_ms,
        "lane": metrics.lane,
    }

def build_identity_snapshot(identity: IdentityContract) -> Dict[str, Any]:
    return {
        "user_id": identity.user_id,
        "subscription": identity.subscription,
        "capabilities": list(identity.capabilities),
        "limits": dict(identity.limits),
    }

def build_capability_snapshot(cap: CapabilityContract) -> Dict[str, Any]:
    return {
        "tools": list(cap.tools),
        "renderers": list(cap.renderers),
        "viewers": list(cap.viewers),
        "permissions": list(cap.permissions),
    }

def build_diagnostic_snapshot(diag: DiagnosticContract) -> Dict[str, Any]:
    return {
        "stage": diag.stage,
        "status": diag.status,
        "message": diag.message,
    }


# =====================================================
# FIBER FACTORY INTEGRATION
# =====================================================


def build_universal_contract(
    artifact: Optional[BaseArtifact] = None,
    user_id: str = "",
    subscription: str = "Free",
) -> UniversalArtifactContract:
    contract = UniversalArtifactContract()
    contract.artifact = artifact
    contract.fiber.identity.user_id = user_id
    contract.fiber.identity.subscription = subscription

    if artifact is not None:
        artifact_payload = _canonicalize_artifact_data(
            dict(artifact.data or {}),
            artifact_type=getattr(artifact.metadata, "artifact_type", ""),
            room_source=getattr(artifact.metadata, "room_source", ""),
        )
        presentation = artifact_payload.setdefault(
            "presentation",
            build_presentation_hint(
                artifact.metadata.artifact_type,
                artifact_payload.get("complexity", "balanced")
            )
        )

        canonical_text = _extract_text_candidate(
            artifact_payload,
            allow_topic=not artifact_payload.get("machine_only", False),
        )

        artifact_payload["answer"] = canonical_text
        artifact_payload["content"] = canonical_text
        artifact_payload["summary"] = canonical_text
        artifact_payload.setdefault("render_blocks", list(artifact_payload.get("render_blocks", []) or []))
        artifact_payload.setdefault("scene", artifact_payload.get("scene", {}))
        artifact_payload["presentation"] = presentation

        contract.payload.artifacts.append(artifact_payload)
        contract.payload.scene.update({
            "presentation": presentation,
            "answer": artifact_payload.get("answer", ""),
            "content": artifact_payload.get("content", ""),
            "summary": artifact_payload.get("summary", ""),
            "render_blocks": artifact_payload.get("render_blocks", []),
            "machine_only": artifact_payload.get("machine_only", False),
            "human_visible": artifact_payload.get("human_visible", True),
        })

        machine_response = MachineResponse(
            answer=canonical_text,
            content=canonical_text,
            response=canonical_text,
            summary=canonical_text,
            render_blocks=list(artifact_payload.get("render_blocks", []) or []),
            artifacts=[artifact],
            metadata={
                "artifact_contract_stage": "stage4_final",
                "room_source": artifact.metadata.room_source,
                "artifact_type": artifact.metadata.artifact_type,
                "presentation": presentation,
                "machine_only": artifact_payload.get("machine_only", False),
                "human_visible": artifact_payload.get("human_visible", True),
            },
        )
        machine_response.executor_hints["presentation"] = presentation
        contract.machine_response = machine_response

        machine_scene = build_machine_scene(machine_response)
        machine_scene.metadata.update({
            "artifact_contract_stage": "stage4_final",
            "presentation": presentation,
            "machine_only": artifact_payload.get("machine_only", False),
            "human_visible": artifact_payload.get("human_visible", True),
        })
        machine_scene.answer = canonical_text
        machine_scene.content = canonical_text
        machine_scene.summary = canonical_text
        machine_scene.blocks = list(machine_response.render_blocks or [])
        machine_scene.contract.blocks = list(machine_scene.blocks)
        contract.machine_scene = machine_scene

        scene_contract = build_scene_contract(machine_scene)
        scene_contract.metadata.setdefault("artifact_contract_stage", "stage4_final")
        scene_contract.metadata.setdefault("presentation", presentation)
        scene_contract.metadata.setdefault("answer", canonical_text)
        scene_contract.metadata.setdefault("content", canonical_text)
        scene_contract.metadata.setdefault("summary", canonical_text)
        contract.scene_contract = scene_contract

        contract.fiber.metrics.block_count = max(1, len(machine_response.render_blocks or []) or 1)
        contract.fiber.metrics.payload_size = len(str(artifact_payload))
        contract.fiber.trace.room = artifact.metadata.room_source
        contract.fiber.renderer.supported_blocks = [artifact.render.web_block]
        contract.metadata.setdefault("artifact_contract_stage", "stage4_final")

    return contract


def create_transport_contract(
    artifact_type: str,
    room_source: str,
    data: Dict[str, Any],
    user_id: str = "",
    subscription: str = "Free",
) -> UniversalArtifactContract:
    """Canonical transport factory used by text_module and room executors.

    The function accepts a plain artifact payload, converts it into a
    BaseArtifact, and then materializes the single Fiber transport envelope
    used throughout the April pipeline.
    """
    payload = dict(data or {})
    payload.setdefault("artifact_type", artifact_type)
    payload.setdefault("room_source", room_source)

    artifact = create_artifact(
        artifact_type=artifact_type,
        room_source=room_source,
        data=payload,
    )

    contract = build_universal_contract(
        artifact=artifact,
        user_id=user_id,
        subscription=subscription,
    )

    # Preserve room-level payload for downstream processors.
    contract.payload.context = {
        "artifact_type": artifact_type,
        "room_source": room_source,
        "user_id": user_id,
        "subscription": subscription,
    }
    contract.payload.intent = dict(payload.get("intent", {}) or {})
    contract.payload.context.update(dict(payload.get("context", {}) or {}))
    contract.payload.knowledge = dict(payload.get("knowledge", {}) or {})
    contract.payload.attachments = list(payload.get("attachments", []) or [])
    contract.payload.media = dict(payload.get("media", {}) or contract.payload.media)
    contract.payload.executor_notes = dict(payload.get("executor_notes", {}) or {})

    # Keep the canonical machine response in sync with the transport payload.
    if contract.machine_response is None:
        contract.machine_response = MachineResponse(
            answer=payload.get("answer", ""),
            content=payload.get("content", payload.get("answer", "")),
            response=payload.get("response", payload.get("answer", "")),
            summary=payload.get("summary", payload.get("answer", "")),
            explanation=payload.get("explanation", payload.get("summary", payload.get("answer", ""))),
            render_blocks=list(payload.get("render_blocks", []) or []),
            scene=dict(payload.get("scene", {}) or {}),
            metadata=dict(payload.get("metadata", {}) or {}),
        )

    # Ensure scene payload is exposed for compatibility checks.
    contract.payload.scene.setdefault("answer", payload.get("answer", ""))
    contract.payload.scene.setdefault("content", payload.get("content", payload.get("answer", "")))
    contract.payload.scene.setdefault("summary", payload.get("summary", payload.get("answer", "")))
    contract.payload.scene.setdefault("render_blocks", list(payload.get("render_blocks", []) or []))

    return contract



# =====================================================
# FACTORY INSPECTION API
# =====================================================
# FACTORY INSPECTION API
# =====================================================

def extract_room_profile(
    artifact
):

    if not artifact:

        return {}

    return {

        "domain":
            artifact.context.domain,

        "specialization":
            artifact.context.specialization,

        "knowledge_class":
            artifact.context.knowledge_class,

        "knowledge_scope":
            artifact.context.knowledge_scope,

        "capabilities":
            artifact.context.capabilities,

        "research_capabilities":
            artifact.context.research_capabilities,

        "experiment_capabilities":
            artifact.context.experiment_capabilities,

        "artifact_outputs":
            artifact.context.artifact_outputs,

        "room_source":
            artifact.metadata.room_source
    }

# =====================================================
# FACTORY CAPABILITY API
# =====================================================

def artifact_has_capability(
    artifact,
    capability: str
):

    if not artifact:

        return False

    return capability in (

        artifact.context.capabilities
        or []
    )

# =====================================================
# FACTORY KNOWLEDGE API
# =====================================================

def artifact_has_knowledge(
    artifact,
    knowledge_area: str
):

    if not artifact:

        return False

    return knowledge_area in (

        artifact.context.knowledge_scope
        or []
    )

# =====================================================
# FACTORY OUTPUT API
# =====================================================

def artifact_can_output(
    artifact,
    output_type: str
):

    if not artifact:

        return False

    return output_type in (

        artifact.context.artifact_outputs
        or []
    )



# =====================================================
# FIBER CORE FOUNDATION
# =====================================================

@dataclass
class FiberLaneContract:
    lane_id: str = "A"
    lane_name: str = "Lane A"
    active: bool = True
    current_load: int = 0
    max_parallel_jobs: int = 1
    status: str = "ready"

@dataclass
class FiberRouteContract:
    route_id: str = "APRIL_FIBER_ROUTE"
    route_version: str = "1.0"
    dispatcher: str = "default"
    active_lane: str = "A"
    lane_count: int = 3
    transport_policy: str = "single_route_multi_lane"
    scaling_policy: str = "horizontal_lane_scaling"

@dataclass
class DispatcherContract:
    selected_lane: str = "A"
    selection_reason: str = "available"
    queue_position: int = 0
    dispatch_time: float = field(default_factory=time.time)

@dataclass
class TraceContract:
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    lane: str = "A"
    stage: str = "CONTRACT"
    room: str = ""
    elapsed_ms: float = 0.0
    payload_size: int = 0
    block_count: int = 0
    attachment_count: int = 0
    status: str = "ACTIVE"

@dataclass
class MetricsContract:
    payload_size: int = 0
    block_count: int = 0
    attachment_count: int = 0
    elapsed_ms: float = 0.0
    lane: str = "A"

@dataclass
class IdentityContract:
    user_id: str = ""
    subscription: str = "Free"
    capabilities: list = field(default_factory=list)
    limits: dict = field(default_factory=dict)

@dataclass
class CapabilityContract:
    tools: list = field(default_factory=list)
    renderers: list = field(default_factory=list)
    viewers: list = field(default_factory=list)
    permissions: list = field(default_factory=list)

@dataclass
class MemoryContract:
    working_memory: dict = field(default_factory=dict)
    persistent_memory: dict = field(default_factory=dict)
    scene_memory: dict = field(default_factory=dict)
    visual_memory: dict = field(default_factory=dict)

@dataclass
class VisualContract:
    active_images: list = field(default_factory=list)
    anchors: list = field(default_factory=list)
    gallery: list = field(default_factory=list)
    focus: dict = field(default_factory=dict)

@dataclass
class RendererContract:
    scene_renderer: str = "default"
    supported_blocks: list = field(default_factory=list)
    responsive: bool = True

@dataclass
class DiagnosticContract:
    stage: str = "CONTRACT"
    status: str = "OK"
    message: str = ""


@dataclass
class FiberCoreContract:
    route: FiberRouteContract = field(default_factory=FiberRouteContract)
    dispatcher: DispatcherContract = field(default_factory=DispatcherContract)
    lane: FiberLaneContract = field(default_factory=FiberLaneContract)
    trace: TraceContract = field(default_factory=TraceContract)
    metrics: MetricsContract = field(default_factory=MetricsContract)
    identity: IdentityContract = field(default_factory=IdentityContract)
    capabilities: CapabilityContract = field(default_factory=CapabilityContract)
    memory: MemoryContract = field(default_factory=MemoryContract)
    visual: VisualContract = field(default_factory=VisualContract)
    renderer: RendererContract = field(default_factory=RendererContract)
    diagnostics: DiagnosticContract = field(default_factory=DiagnosticContract)

# =====================================================
# UNIVERSAL TRANSPORT CONTRACT (APRIL FIBER CHANNEL)
# =====================================================

@dataclass
class TransportContract:
    """Payload envelope only. All routing belongs to FiberCore."""
    transport_version: str = "2.0"

@dataclass
class MachinePayload:
    intent: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    knowledge: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    scene: Dict[str, Any] = field(default_factory=dict)
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    media: Dict[str, Any] = field(default_factory=lambda:{
        "text":[],
        "markdown":[],
        "tables":[],
        "graphs":[],
        "formulas":[],
        "images":[],
        "gallery":[],
        "files":[],
        "audio":[],
        "video":[],
        "code":[],
        "links":[],
        "diagrams":[],
        "actions":[]
    })
    executor_notes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UniversalArtifactContract:
    # FiberCore is the single owner of routing state.
    fiber: FiberCoreContract = field(default_factory=FiberCoreContract)
    transport: TransportContract = field(default_factory=TransportContract)
    payload: MachinePayload = field(default_factory=MachinePayload)
    artifact: Optional[BaseArtifact] = None
    machine_response: Optional["MachineResponse"] = None
    machine_scene: Optional["MachineScene"] = None
    scene_contract: Optional["SceneContract"] = None
    metadata: Dict[str, Any] = field(default_factory=dict)



# =====================================================
# STAGE 2 PRESENTATION TRANSPORT
# =====================================================
# STAGE 2 PRESENTATION TRANSPORT (TEST)
# =====================================================
# Canonical presentation helper.


def build_presentation_hint(artifact_type: str, complexity: str = "balanced") -> dict:
    renderer = SCENE_BLOCK_REGISTRY.get(artifact_type, "TextBlock")
    return {
        "payload_type": artifact_type,
        "scene_block": artifact_type,
        "renderer": renderer,
        "viewer": renderer,
        "priority": 100,
        "complexity": complexity,
        "layout": "single" if complexity == "compact" else "adaptive",
    }


# =====================================================
# UNIVERSAL PAYLOAD REGISTRY
# =====================================================

SUPPORTED_PAYLOAD_TYPES = {
    "text",
    "markdown",
    "table",
    "formula",
    "graph",
    "diagram",
    "image",
    "gallery",
    "code",
    "link",
    "file",
    "audio",
    "video",
    "action",
    "memory",
    "visual_context",
    "scene"
}

SCENE_BLOCK_REGISTRY = {
    "text": "TextBlock",
    "markdown": "MarkdownBlock",
    "table": "TableBlock",
    "formula": "FormulaBlock",
    "graph": "GraphBlock",
    "diagram": "DiagramBlock",
    "image": "ImageBlock",
    "gallery": "GalleryBlock",
    "code": "CodeBlock",
    "link": "LinkCard",
    "file": "FileBlock",
    "audio": "AudioBlock",
    "video": "VideoBlock",
    "action": "ActionBlock",
}

@dataclass
class SceneContract:
    scene_version: str = "2.0"
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    render_blocks: List[Dict[str, Any]] = field(default_factory=list)
    active_scene: str = ""
    space_continuity: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    supported_payloads: List[str] = field(
        default_factory=lambda: sorted(SUPPORTED_PAYLOAD_TYPES)
    )

def register_payload_type(payload_type: str) -> None:
    SUPPORTED_PAYLOAD_TYPES.add(payload_type)

def register_scene_block(payload_type: str, renderer: str) -> None:
    SCENE_BLOCK_REGISTRY[payload_type] = renderer

# =====================================================
# UNIVERSAL MACHINE PIPELINE CONTRACTS
# =====================================================

@dataclass
class MachineRequest:
    fiber: FiberCoreContract = field(default_factory=FiberCoreContract)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    intent: Dict[str, Any] = field(default_factory=dict)
    conversation: Dict[str, Any] = field(default_factory=dict)
    memory: Dict[str, Any] = field(default_factory=dict)
    visual_context: Dict[str, Any] = field(default_factory=dict)
    available_tools: List[str] = field(default_factory=list)
    requested_outputs: List[str] = field(default_factory=list)
    required_competencies: List[str] = field(default_factory=list)
    required_artifacts: List[str] = field(default_factory=list)
    routing: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MachineResponse:
    # Canonical transport fields
    fiber: FiberCoreContract = field(default_factory=FiberCoreContract)
    artifacts: List[BaseArtifact] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    quality: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    contributions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    executor_hints: Dict[str, Any] = field(default_factory=dict)
    routing_decision: Dict[str, Any] = field(default_factory=dict)

    answer: str = ""
    content: str = ""
    response: str = ""
    summary: str = ""
    explanation: str = ""

    render_blocks: List[Dict[str, Any]] = field(default_factory=list)
    artifacts_payload: List[Dict[str, Any]] = field(default_factory=list)
    scene: Dict[str, Any] = field(default_factory=dict)
    scene_plan: List[str] = field(default_factory=lambda:["text"])
    render_priority: List[str] = field(default_factory=lambda:["text"])
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MachineScene:
    fiber: FiberCoreContract = field(default_factory=FiberCoreContract)
    scene_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scene_version: str = "1.0"
    active_scene: str = ""
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    contract: SceneContract = field(default_factory=SceneContract)


# =====================================================
# FIBER CORE FINALIZATION
# =====================================================

# Stage 4: finalized canonical transport contract
FIBER_CORE_VERSION = "1.0"
FIBER_CORE_SINGLE_ROUTE = True
FIBER_ROUTE_NAME = "APRIL_FIBER_ROUTE"

DEFAULT_FIBER_LANES = (
    "A",
    "B",
    "C",
)

DEFAULT_TRACE_SEQUENCE = (
    "CONTRACT",
    "REGISTRY",
    "ROOM",
    "OPENAI_REQUEST",
    "OPENAI_RESPONSE",
    "EXECUTOR",
    "SCENE",
    "WEB",
    "DONE",
)

def create_default_scene_contract() -> SceneContract:
    return SceneContract()

def create_default_machine_request() -> MachineRequest:
    return MachineRequest()

def create_default_machine_response() -> MachineResponse:
    return MachineResponse()

def create_default_machine_scene() -> MachineScene:
    return MachineScene()

def validate_universal_contract(
    contract: UniversalArtifactContract,
) -> Dict[str, bool]:
    return {
        "has_fiber": contract.fiber is not None,
        "has_route": contract.fiber.route is not None,
        "has_trace": contract.fiber.trace is not None,
        "has_payload": contract.payload is not None,
        "has_identity": contract.fiber.identity is not None,
        "has_renderer": contract.fiber.renderer is not None,
        "has_artifact": contract.artifact is not None,
    }

__all__ = [
    "ArtifactMetadata",
    "ArtifactContext",
    "ArtifactQuality",
    "ArtifactRenderContract",
    "BaseArtifact",
    "TransportContract",
    "MachinePayload",
    "UniversalArtifactContract",
    "MachineRequest",
    "MachineResponse",
    "MachineScene",
    "SceneContract",
    "FiberRouteContract",
    "FiberLaneContract",
    "DispatcherContract",
    "TraceContract",
    "MetricsContract",
    "IdentityContract",
    "CapabilityContract",
    "MemoryContract",
    "VisualContract",
    "RendererContract",
    "DiagnosticContract",
    "build_universal_contract",
    "create_transport_contract",
    "validate_universal_contract",
    "build_machine_scene",
    "build_scene_contract",
]


# =====================================================
# FIBER CORE ACCESS API
# =====================================================

def get_fiber_core(contract: UniversalArtifactContract) -> FiberCoreContract:
    """Canonical access point for the single Fiber Route."""
    return contract.fiber


# =====================================================
# FIBER ROUTE API
# =====================================================

def dispatch_lane(contract: UniversalArtifactContract) -> str:
    """Return the active lane from the single Fiber Route."""
    return contract.fiber.route.active_lane

def current_trace_id(contract: UniversalArtifactContract) -> str:
    """Canonical trace identifier for the entire pipeline."""
    return contract.fiber.trace.trace_id


# =====================================================
# FIBER CORE FINAL VALIDATION
# =====================================================

def validate_fiber_core(contract: UniversalArtifactContract) -> dict:
    """Validate that the transport is centered on the single Fiber Core."""
    return {
        "single_route": True,
        "route_policy_ok": contract.fiber.route.transport_policy == "single_route_multi_lane",
        "single_trace": bool(current_trace_id(contract)),
        "lane": dispatch_lane(contract),
        "scene_contract": hasattr(contract, "payload"),
        "artifact_contract": contract.artifact is not None or True,
    }


# =====================================================
# CANONICAL CONTRIBUTION API
# =====================================================

def add_room_contribution(response: MachineResponse, room: str, payload: Dict[str, Any]) -> None:
    """Canonical API: each room writes its named contribution."""
    response.contributions[room] = payload




# =====================================================
# CANONICAL MACHINE SCENE BUILDER
# =====================================================


def build_machine_scene(response: MachineResponse) -> MachineScene:
    """Canonical MachineResponse -> MachineScene transformation.
    The Factory owns Scene construction; Executor only invokes it.
    """
    scene = create_default_machine_scene()

    # Preserve Fiber ownership.
    scene.fiber = response.fiber

    response_metadata = getattr(response, "metadata", {}) or {}

    # Carry metadata when available.
    scene.metadata = {
        "confidence": getattr(response, "confidence", 0.0),
        "diagnostics": getattr(response, "diagnostics", {}),
        "quality": getattr(response, "quality", {}),
        "routing_decision": getattr(response, "routing_decision", {}),
        "machine_only": bool(response_metadata.get("machine_only", False)),
        "human_visible": response_metadata.get("human_visible", True),
    }

    # Reuse render blocks if Executor already materialized them.
    blocks = list(getattr(response, "render_blocks", []) or [])
    scene.blocks = blocks
    scene.contract.blocks = blocks

    # Stage 2: carry canonical transport fields into the scene.
    # Carry canonical response payload.
    scene.metadata.update({
        "answer": getattr(response, "answer", ""),
        "content": getattr(response, "content", ""),
        "summary": getattr(response, "summary", ""),
        "contributions": dict(getattr(response, "contributions", {}) or {}),
        "executor_hints": dict(getattr(response, "executor_hints", {}) or {}),
    })

    setattr(scene, "artifacts", list(getattr(response, "artifacts", []) or []))
    setattr(scene, "answer", getattr(response, "answer", ""))
    setattr(scene, "content", getattr(response, "content", ""))
    setattr(scene, "summary", getattr(response, "summary", ""))

    # Preserve optional runtime context.
    if hasattr(response, "conversation_space"):
        setattr(scene, "conversation_space", getattr(response, "conversation_space"))

    return scene


# =====================================================
# STAGE 3 PRESENTATION TRANSPORT (TEST)
# =====================================================



def build_canonical_scene_blocks(scene):
    """
    Stage 3 (test):
    Build a default render block from presentation hints when
    no render_blocks were produced upstream.
    """
    if _scene_is_internal_only(scene):
        return []

    blocks = list(scene.blocks or [])
    if blocks:
        return blocks

    metadata = scene.metadata or {}
    presentation = metadata.get("presentation", {})

    payload_type = presentation.get("payload_type", "text")
    renderer = presentation.get(
        "renderer",
        SCENE_BLOCK_REGISTRY.get(payload_type, "TextBlock")
    )

    content = _scene_text_fallback(scene)

    if not content:
        return []

    return [{
        "type": payload_type,
        "renderer": renderer,
        "viewer": presentation.get("viewer", renderer),
        "content": content,
        "priority": presentation.get("priority", 100),
    }]


def build_scene_contract(scene: MachineScene) -> SceneContract:
    # Stage 3: finalize the canonical SceneContract from MachineScene.
    """Canonical SceneContract builder from MachineScene."""
    contract = scene.contract or create_default_scene_contract()
    contract.blocks = build_canonical_scene_blocks(scene)
    contract.render_blocks = list(contract.blocks)
    contract.metadata.update(scene.metadata or {})
    # Canonical transport fields must always reflect the latest scene state.
    canonical_text = _scene_text_fallback(scene)
    contract.metadata["answer"] = canonical_text
    contract.metadata["content"] = canonical_text
    contract.metadata["summary"] = canonical_text
    contract.metadata["artifact_count"] = len(getattr(scene, "artifacts", []) or [])
    contract.metadata["transport_stage"] = "artifact_contract_stage2"
    contract.metadata["canonical_scene_contract"] = True
    contract.metadata["machine_only"] = bool(contract.metadata.get("machine_only", False) or _scene_is_internal_only(scene))
    contract.metadata["human_visible"] = bool(contract.metadata.get("human_visible", not contract.metadata["machine_only"]))
    if contract.metadata["machine_only"]:
        contract.metadata["answer"] = ""
        contract.metadata["content"] = ""
        contract.metadata["summary"] = ""
    contract.active_scene = getattr(scene, "active_scene", "")
    contract.space_continuity = {
        "active_scene": contract.active_scene,
        "render_blocks": contract.render_blocks,
    }
    scene.contract = contract
    return contract


# =====================================================
# CPU COORDINATION API (Stage 1)
# Factory remains autonomous internally.
# CPU becomes the single coordinator.
# =====================================================

FACTORY_CPU_HOOKS = {
    "begin": None,
    "success": None,
    "error": None,
}

def register_cpu_hooks(begin=None, success=None, error=None):
    FACTORY_CPU_HOOKS["begin"] = begin
    FACTORY_CPU_HOOKS["success"] = success
    FACTORY_CPU_HOOKS["error"] = error

def factory_stage_begin(stage:str,payload:dict|None=None):
    cb=FACTORY_CPU_HOOKS.get("begin")
    if cb:
        cb(stage,payload or {})

def factory_stage_success(stage:str,payload:dict|None=None):
    cb=FACTORY_CPU_HOOKS.get("success")
    if cb:
        cb(stage,payload or {})

def factory_stage_error(stage:str,error):
    cb=FACTORY_CPU_HOOKS.get("error")
    if cb:
        cb(stage,error)


# =====================================================
# CPU FACTORY EVENTS (Stage 2)
# =====================================================

def factory_room_begin(room_name:str, request:dict|None=None):
    factory_stage_begin("ROOM_BEGIN",{
        "room":room_name,
        "input":request or {}
    })

def factory_room_success(room_name:str, artifact=None):
    factory_stage_success("ROOM_SUCCESS",{
        "room":room_name,
        "artifact":type(artifact).__name__ if artifact is not None else None
    })

def factory_room_error(room_name:str, error):
    factory_stage_error(f"{room_name}: {error}")

def factory_response_complete(response=None):
    factory_stage_success("FACTORY_COMPLETE",{
        "response_type":type(response).__name__ if response is not None else None
    })


# =====================================================
# CPU FACTORY BRIDGE (Stage 3)
# =====================================================

FACTORY_CPU_REGISTERED = False

def factory_register_cpu_bridge(register_callback):
    """Register CPU hooks exactly once."""
    global FACTORY_CPU_REGISTERED
    if FACTORY_CPU_REGISTERED:
        return
    register_callback(
        begin=factory_stage_begin,
        success=factory_stage_success,
        error=factory_stage_error,
    )
    FACTORY_CPU_REGISTERED = True

def factory_room_selected(room_name:str):
    factory_stage_success("ROOM_SELECTED",{
        "room":room_name
    })

def factory_machine_response_ready(response):
    factory_response_complete(response)


# =====================================================
# APRIL QUANTUM ARTIFACT CONTRACT 1.2 — FINAL CANONICAL OVERRIDES
# =====================================================
# Design laws:
# 1. One Fiber route.
# 2. MachineResponse is the canonical response object.
# 3. render_blocks are preserved exactly when supplied upstream.
# 4. Summary is metadata/context only; never a visible render block.
# 5. Text/Markdown are not reclassified into FormulaBlock/CodeBlock/etc.
# 6. Structured artifacts remain structured payloads for AprilWeb.
# 7. SceneContract is a projection of the canonical MachineResponse, never
#    a second semantic reconstruction.
# =====================================================

APRIL_ARTIFACT_CONTRACT_VERSION = "quantum_1_4"
APRIL_ARTIFACT_SINGLE_ROUTE = True
APRIL_ARTIFACT_SUMMARY_VISIBLE = False

_ARTIFACT_RENDERER_MAP = {
    "text": "TextBlock",
    "markdown": "MarkdownBlock",
    "table": "TableBlock",
    "graph": "GraphBlock",
    "diagram": "DiagramBlock",
    "formula": "FormulaBlock",
    "code": "CodeBlock",
    "link": "LinkCard",
    "gallery": "GalleryBlock",
    "image": "ImageBlock",
    "file": "FileBlock",
    "audio": "AudioBlock",
    "video": "VideoBlock",
    "action": "ActionBlock",
}

def _artifact_norm_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()

def _artifact_block_type(block):
    if not isinstance(block, dict):
        return "text"
    value = block.get("type") or block.get("artifact_type") or "text"
    value = _artifact_norm_text(value).lower()
    if value == "markdown":
        return "markdown"
    return value if value in _ARTIFACT_RENDERER_MAP else "text"

def _artifact_block_signature(block):
    if not isinstance(block, dict):
        return ("text", _artifact_norm_text(block))
    btype = _artifact_block_type(block)
    payload = block.get("payload")
    if isinstance(payload, (dict, list)):
        try:
            payload_key = repr(payload)
        except Exception:
            payload_key = str(payload)
    else:
        payload_key = _artifact_norm_text(
            block.get("content") or block.get("text") or block.get("url") or ""
        )
    return (btype, payload_key[:4000])

def _artifact_clean_render_blocks(blocks):
    """Preserve order and distinct artifact types; collapse only exact duplicates."""
    if not isinstance(blocks, list):
        return []
    result = []
    seen = set()
    for raw in blocks:
        if not isinstance(raw, dict):
            raw = {"type": "text", "content": _artifact_norm_text(raw)}
        block = dict(raw)
        btype = _artifact_block_type(block)
        block["type"] = btype
        renderer = block.get("renderer") or block.get("viewer") or _ARTIFACT_RENDERER_MAP.get(btype, "TextBlock")
        block["renderer"] = renderer
        block["viewer"] = block.get("viewer") or renderer
        sig = _artifact_block_signature(block)
        if sig in seen:
            continue
        seen.add(sig)
        result.append(block)
    return result

def _artifact_visible_text_from_response(response):
    if response is None:
        return ""
    for field in ("answer", "content", "response"):
        value = getattr(response, field, "")
        if isinstance(value, str) and value.strip():
            return value.strip()
    if isinstance(response, dict):
        for field in ("answer", "content", "response"):
            value = response.get(field, "")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""

def _artifact_compact_summary(response_or_text, block_types=None):
    """Metadata-only scene summary; never the visible answer itself."""
    if isinstance(response_or_text, str):
        text = response_or_text.strip()
    else:
        text = _artifact_visible_text_from_response(response_or_text)

    block_types = [b for b in (block_types or []) if b]
    if not text:
        return f"scene: {', '.join(block_types[:5])}" if block_types else ""

    first_line = text.split("\n", 1)[0].strip()
    if len(first_line) > 110:
        first_line = first_line[:107] + "..."

    if block_types:
        return f"{first_line} | scene: {', '.join(dict.fromkeys(block_types)[:5])}"
    return first_line

def build_universal_contract(
    artifact: Optional[BaseArtifact] = None,
    user_id: str = "",
    subscription: str = "Free",
) -> UniversalArtifactContract:
    """Canonical artifact -> single Fiber envelope; never invent a second visible scene."""
    contract = UniversalArtifactContract()
    contract.artifact = artifact
    contract.fiber.identity.user_id = user_id
    contract.fiber.identity.subscription = subscription
    contract.metadata["artifact_contract_version"] = APRIL_ARTIFACT_CONTRACT_VERSION
    contract.metadata["single_route"] = True

    if artifact is None:
        return contract

    data = dict(getattr(artifact, "data", {}) or {})
    artifact_type = getattr(artifact.metadata, "artifact_type", "") or data.get("artifact_type", "")
    room_source = getattr(artifact.metadata, "room_source", "") or data.get("room_source", "")

    # Preserve structured provider render signals exactly.
    render_blocks = _artifact_clean_render_blocks(data.get("render_blocks", []) or [])
    artifact_payload = _canonicalize_artifact_data(
        data,
        artifact_type=artifact_type,
        room_source=room_source,
    )
    artifact_payload["render_blocks"] = render_blocks
    artifact_payload["scene"] = dict(data.get("scene", {}) or {})
    artifact_payload["artifacts"] = list(data.get("artifacts", []) or [])

    canonical_text = (
        _artifact_norm_text(data.get("answer"))
        or _artifact_norm_text(data.get("content"))
        or _artifact_norm_text(data.get("response"))
        or _artifact_norm_text(data.get("display_text"))
    )

    block_types = [_artifact_block_type(b) for b in render_blocks]
    summary = _artifact_compact_summary(canonical_text, block_types)

    artifact_payload["answer"] = canonical_text
    artifact_payload["content"] = canonical_text
    artifact_payload["summary"] = summary
    artifact_payload["text"] = canonical_text
    artifact_payload["presentation"] = data.get(
        "presentation",
        build_presentation_hint(artifact_type or "text", data.get("complexity", "balanced")),
    )

    contract.payload.artifacts.append(artifact_payload)
    contract.payload.scene = dict(artifact_payload.get("scene", {}) or {})
    contract.payload.scene.update({
        "answer": canonical_text,
        "content": canonical_text,
        "summary": summary,
        "render_blocks": render_blocks,
        "presentation": artifact_payload["presentation"],
        "machine_only": bool(artifact_payload.get("machine_only", False)),
        "human_visible": bool(artifact_payload.get("human_visible", True)),
    })

    machine_response = MachineResponse(
        answer=canonical_text,
        content=canonical_text,
        response=canonical_text,
        summary=summary,
        explanation=_artifact_norm_text(data.get("explanation")),
        render_blocks=render_blocks,
        artifacts=[artifact],
        scene=dict(artifact_payload.get("scene", {}) or {}),
        scene_plan=list(data.get("scene_plan", []) or block_types or ["text"]),
        render_priority=list(data.get("render_priority", []) or block_types or ["text"]),
        confidence=float(data.get("confidence", 1.0) or 1.0),
        metadata={
            "artifact_contract_version": APRIL_ARTIFACT_CONTRACT_VERSION,
            "room_source": room_source,
            "artifact_type": artifact_type,
            "summary_visible": False,
            "single_route": True,
            "render_block_count": len(render_blocks),
            "block_types": block_types,
        },
    )
    machine_response.executor_hints["presentation"] = artifact_payload["presentation"]
    contract.machine_response = machine_response

    machine_scene = build_machine_scene(machine_response)
    machine_scene.metadata.update(machine_response.metadata)
    machine_scene.answer = canonical_text
    machine_scene.content = canonical_text
    machine_scene.summary = summary
    machine_scene.blocks = list(render_blocks)
    machine_scene.contract.blocks = list(render_blocks)
    machine_scene.contract.render_blocks = list(render_blocks)
    contract.machine_scene = machine_scene

    scene_contract = build_scene_contract(machine_scene)
    scene_contract.blocks = list(render_blocks)
    scene_contract.render_blocks = list(render_blocks)
    scene_contract.metadata.update({
        "artifact_contract_version": APRIL_ARTIFACT_CONTRACT_VERSION,
        "answer": canonical_text,
        "content": canonical_text,
        "summary": summary,
        "summary_visible": False,
        "single_route": True,
        "render_block_count": len(render_blocks),
        "block_types": block_types,
        "renderer_state": {
            "keys": [],
            "source": "provider_blocks",
            "single_route": True,
        },
    })
    contract.scene_contract = scene_contract

    contract.fiber.metrics.block_count = len(render_blocks)
    contract.fiber.metrics.payload_size = len(repr(artifact_payload))
    contract.fiber.trace.room = room_source
    contract.fiber.trace.block_count = len(render_blocks)
    contract.fiber.trace.status = "READY"
    contract.fiber.renderer.supported_blocks = sorted(set(block_types or [artifact.render.web_block]))

    return contract

def create_transport_contract(
    artifact_type: str,
    room_source: str,
    data: Dict[str, Any],
    user_id: str = "",
    subscription: str = "Free",
) -> UniversalArtifactContract:
    """Single canonical Fiber transport builder used by text rooms and other rooms."""
    payload = dict(data or {})
    payload.setdefault("artifact_type", artifact_type)
    payload.setdefault("room_source", room_source)

    # The provider owns the structured scene. The artifact layer only transports it.
    render_blocks = _artifact_clean_render_blocks(payload.get("render_blocks", []) or [])
    payload["render_blocks"] = render_blocks
    payload["scene"] = dict(payload.get("scene", {}) or {})
    payload["scene"]["render_blocks"] = render_blocks
    payload["scene"]["answer"] = _artifact_norm_text(payload.get("answer") or payload.get("content"))
    payload["scene"]["content"] = payload["scene"]["answer"]
    payload["scene"]["summary"] = _artifact_compact_summary(payload["scene"]["answer"], [_artifact_block_type(b) for b in render_blocks])
    payload["summary_visible"] = False
    payload["single_route"] = True

    artifact = create_artifact(
        artifact_type=artifact_type,
        room_source=room_source,
        data=payload,
    )

    contract = build_universal_contract(
        artifact=artifact,
        user_id=user_id,
        subscription=subscription,
    )

    contract.payload.context = {
        "artifact_type": artifact_type,
        "room_source": room_source,
        "user_id": user_id,
        "subscription": subscription,
        "single_route": True,
    }
    contract.payload.context.update(dict(payload.get("context", {}) or {}))
    contract.payload.intent = dict(payload.get("intent", {}) or {})
    contract.payload.knowledge = dict(payload.get("knowledge", {}) or {})
    contract.payload.attachments = list(payload.get("attachments", []) or [])
    contract.payload.media = dict(payload.get("media", {}) or contract.payload.media)
    contract.payload.executor_notes = dict(payload.get("executor_notes", {}) or {})

    # Keep canonical MachineResponse aligned with the exact provider scene.
    if contract.machine_response is None:
        contract.machine_response = MachineResponse(
            answer=payload["scene"].get("answer", ""),
            content=payload["scene"].get("content", ""),
            response=payload["scene"].get("answer", ""),
            summary=payload["scene"].get("summary", ""),
            render_blocks=render_blocks,
            scene=payload["scene"],
            metadata={
                "artifact_contract_version": APRIL_ARTIFACT_CONTRACT_VERSION,
                "summary_visible": False,
                "single_route": True,
            },
        )
    else:
        contract.machine_response.render_blocks = list(render_blocks)
        contract.machine_response.scene = dict(payload["scene"])
        contract.machine_response.summary = payload["scene"].get("summary", "")
        contract.machine_response.metadata["summary_visible"] = False
        contract.machine_response.metadata["single_route"] = True

    # Final SceneContract is strictly a projection.
    if contract.scene_contract is not None:
        contract.scene_contract.render_blocks = list(render_blocks)
        contract.scene_contract.blocks = list(render_blocks)
        contract.scene_contract.metadata["summary_visible"] = False
        contract.scene_contract.metadata["single_route"] = True

    return contract

def build_canonical_scene_blocks(scene):
    """Strict projection; never invent a renderer block from text/summary."""
    if _scene_is_internal_only(scene):
        return []
    return _artifact_clean_render_blocks(list(getattr(scene,"blocks",[]) or []))

def build_scene_contract(scene: MachineScene) -> SceneContract:
    """Strict projection of MachineScene -> SceneContract."""
    contract=scene.contract or create_default_scene_contract()
    blocks=build_canonical_scene_blocks(scene)
    contract.blocks=list(blocks)
    contract.render_blocks=list(blocks)
    contract.metadata.update(scene.metadata or {})
    answer=_scene_text_fallback(scene)
    types=[_artifact_block_type(b) for b in blocks]
    contract.metadata.update({
        "answer":answer,"content":answer,
        "summary":_artifact_compact_summary(answer,types),
        "artifact_count":len(getattr(scene,"artifacts",[]) or []),
        "transport_stage":"artifact_quantum_1_3",
        "canonical_scene_contract":True,"single_route":True,
        "summary_visible":False,"render_block_count":len(blocks),
        "block_types":types,
    })
    contract.active_scene=getattr(scene,"active_scene","")
    contract.space_continuity={"active_scene":contract.active_scene,"render_blocks":list(blocks)}
    scene.contract=contract
    return contract

def validate_quantum_artifact_contract(contract):
    """Explicit invariant check for the four-file quantum route."""
    response = getattr(contract, "machine_response", None)
    scene = getattr(contract, "machine_scene", None)
    scene_contract = getattr(contract, "scene_contract", None)
    response_blocks = list(getattr(response, "render_blocks", []) or []) if response else []
    scene_blocks = list(getattr(scene, "blocks", []) or []) if scene else []
    contract_blocks = list(getattr(scene_contract, "render_blocks", []) or []) if scene_contract else []
    return {
        "single_route": True,
        "machine_response_present": response is not None,
        "machine_scene_present": scene is not None,
        "scene_contract_present": scene_contract is not None,
        "render_blocks_consistent": response_blocks == scene_blocks == contract_blocks,
        "summary_visible": False,
        "response_block_count": len(response_blocks),
        "scene_block_count": len(scene_blocks),
        "contract_block_count": len(contract_blocks),
        "block_types": [_artifact_block_type(b) for b in contract_blocks],
    }

# Keep a public alias used by diagnostics.
validate_universal_quantum_contract = validate_quantum_artifact_contract
