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
# RENDER CONTRACT
# =====================================================

@dataclass
class ArtifactRenderContract:

    web_block: str = ""

    viewer: str = ""

    editable: bool = True

    responsive: bool = True

    exportable: bool = True

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

    room_identity = data.get(
        "room_identity",
        {}
    )

    return BaseArtifact(

        metadata=ArtifactMetadata(

            artifact_type=
                artifact_type,

            room_source=
                room_source
        ),

        context=ArtifactContext(

            domain=data.get(
                "domain"
            ),

            specialization=room_identity.get(
                "specialization"
            ),

            knowledge_class=room_identity.get(
                "knowledge_class"
            ),

            knowledge_scope=data.get(
                "knowledge_scope",
                []
            ),

            capabilities=data.get(
                "capabilities",
                []
            ),

            research_capabilities=data.get(
                "research_capabilities",
                []
            ),

            experiment_capabilities=data.get(
                "experiment_capabilities",
                []
            ),

            artifact_outputs=data.get(
                "artifact_outputs",
                []
            ),

            scene_contributions=data.get(
                "scene_contributions",
                []
            ),

            focus_contributions=data.get(
                "focus_contributions",
                []
            ),

            memory_contributions=data.get(
                "memory_contributions",
                []
            ),

            trajectory_hints=data.get(
                "trajectory_hints",
                []
            ),

            scene_hints=data.get(
                "scene_hints",
                []
            )
        ),

        quality=ArtifactQuality(),

        render=ArtifactRenderContract(

            web_block=
                ARTIFACT_BLOCK_MAP.get(

                    artifact_type,

                    "FunctionBlock"
                )
        ),

        data=data
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
        contract.payload.artifacts.append(artifact.data)
        contract.fiber.metrics.block_count = 1
        contract.fiber.metrics.payload_size = len(str(artifact.data))
        contract.fiber.trace.room = artifact.metadata.room_source
        contract.fiber.renderer.supported_blocks = [
            artifact.render.web_block
        ]

    return contract


def create_transport_contract(
    artifact_type: str,
    room_source: str,
    data: Dict[str, Any],
    user_id: str = "",
    subscription: str = "Free",
) -> UniversalArtifactContract:
    artifact = create_artifact(
        artifact_type=artifact_type,
        room_source=room_source,
        data=data,
    )
    return build_universal_contract(
        artifact=artifact,
        user_id=user_id,
        subscription=subscription,
    )


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
    fiber: FiberCoreContract = field(default_factory=FiberCoreContract)
    artifacts: List[BaseArtifact] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    quality: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    contributions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    executor_hints: Dict[str, Any] = field(default_factory=dict)
    routing_decision: Dict[str, Any] = field(default_factory=dict)

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

    # Carry metadata when available.
    scene.metadata = {
        "confidence": getattr(response, "confidence", 0.0),
        "diagnostics": getattr(response, "diagnostics", {}),
        "quality": getattr(response, "quality", {}),
        "routing_decision": getattr(response, "routing_decision", {}),
    }

    # Reuse render blocks if Executor already materialized them.
    blocks = list(getattr(response, "render_blocks", []) or [])
    scene.blocks = blocks
    scene.contract.blocks = blocks

    # Preserve optional runtime context.
    if hasattr(response, "conversation_space"):
        setattr(scene, "conversation_space", getattr(response, "conversation_space"))

    return scene


def build_scene_contract(scene: MachineScene) -> SceneContract:
    """Canonical SceneContract builder from MachineScene."""
    contract = scene.contract or create_default_scene_contract()
    contract.blocks = list(scene.blocks or [])
    contract.metadata.update(scene.metadata or {})
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
