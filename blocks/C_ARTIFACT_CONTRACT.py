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

    # Canonical render-signal identity.
    # The payload itself remains in BaseArtifact.data["payload"]; this field
    # only describes how that payload must travel to April Web.
    signal_version: str = "1.0"
    signal_type: str = ""

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
# CANONICAL FACTORY ROOM PROFILES
# =====================================================

FACTORY_ROOM_PROFILES = {
    "diagram": {
        "room": "C_DIAGRAM_ROOM",
        "artifact_type": "diagram",
        "renderer": "DiagramBlock",
        "viewer": "DiagramBlock",
        "semantic_service": "APRIL_DIAGRAM_SYSTEM_CORE",
        "capabilities": [
            "spatial_semantics",
            "geometry",
            "relations",
            "structure",
            "engineering_layout",
        ],
        "machine_input": "MachineRequest",
        "machine_output": "BaseArtifact",
        "scene_output": "SceneContract",
        "single_route": True,
    },
}


def get_factory_room_profile(room_or_artifact_type: str) -> Dict[str, Any]:
    '''Return the canonical production-room profile without routing logic.'''
    key = str(room_or_artifact_type or "").strip()
    if key in FACTORY_ROOM_PROFILES:
        return dict(FACTORY_ROOM_PROFILES[key])
    for profile in FACTORY_ROOM_PROFILES.values():
        if key in {profile.get("room"), profile.get("artifact_type")}:
            return dict(profile)
    return {}


def build_diagram_room_payload(
    semantic: Optional[Dict[str, Any]] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    '''Normalize diagram-room semantics into one artifact payload.'''
    semantic = dict(semantic or {})
    payload = dict(payload or {})
    profile = get_factory_room_profile("diagram")
    payload.update({
        "artifact_type": profile["artifact_type"],
        "room_source": profile["room"],
        "renderer": profile["renderer"],
        "viewer": profile["viewer"],
        "semantic": semantic,
        "diagram_semantics": semantic,
        "machine_only": bool(payload.get("machine_only", False)),
    })
    return payload


# =====================================================
# CANONICAL RENDER SIGNAL
# =====================================================
UNIFIED_RENDER_SIGNAL_VERSION = "1.0"


def _render_signal_metadata(
    artifact_type: str,
    room_source: str,
    renderer: str,
    *,
    content: str = "",
    priority: int = 100,
    complexity: str = "balanced",
    layout: str = "single",
) -> Dict[str, Any]:
    """Return only transport metadata; payload stays structured and untouched."""
    return {
        "type": artifact_type,
        "payload_type": artifact_type,
        "renderer": renderer,
        "viewer": renderer,
        "source_room": room_source,
        "version": UNIFIED_RENDER_SIGNAL_VERSION,
        "content_present": bool(content),
        "priority": priority,
        "complexity": complexity,
        "layout": layout,
        "scene_contract": True,
    }


def _build_artifact_render_signal(
    *,
    artifact_type: str,
    room_source: str,
    renderer: str,
    payload: Dict[str, Any],
    content: str = "",
    priority: int = 100,
    complexity: str = "balanced",
    layout: str = "single",
) -> Dict[str, Any]:
    """Canonical room -> Fiber render signal.

    The structured payload is carried once at top-level ``payload``.
    ``signal`` contains identity/routing metadata only, so no payload is
    duplicated or rewritten while crossing the single route.
    """
    return {
        "type": artifact_type,
        "payload_type": artifact_type,
        "signal_version": UNIFIED_RENDER_SIGNAL_VERSION,
        "signal": _render_signal_metadata(
            artifact_type,
            room_source,
            renderer,
            content=content,
            priority=priority,
            complexity=complexity,
            layout=layout,
        ),
        "renderer": renderer,
        "viewer": renderer,
        "source_room": room_source,
        "content": content,
        "text": content,
        "payload": payload,
        "priority": priority,
        "complexity": complexity,
        "layout": layout,
        "scene_contract": True,
    }

# =====================================================
# CREATE ARTIFACT
# =====================================================


def create_artifact(
    artifact_type: str,
    room_source: str,
    data: Dict[str, Any]
):
    """Create a BaseArtifact with one canonical, lossless render signal."""
    normalized_data = _canonicalize_artifact_data(
        data,
        artifact_type=artifact_type,
        room_source=room_source,
    )

    room_identity = normalized_data.get("room_identity", {})
    if not isinstance(room_identity, dict):
        room_identity = {}

    render_block = ARTIFACT_BLOCK_MAP.get(
        artifact_type,
        "FunctionBlock"
    )

    priority = normalized_data.get("priority", 100)
    complexity = normalized_data.get("complexity", "balanced")
    layout = normalized_data.get("layout", "single")
    canonical_text = _extract_text_candidate(normalized_data)

    structured_payload = normalized_data.get("payload")
    if not isinstance(structured_payload, dict):
        structured_payload = {}

    render_signal = _build_artifact_render_signal(
        artifact_type=artifact_type,
        room_source=room_source,
        renderer=render_block,
        payload=structured_payload,
        content=canonical_text,
        priority=priority,
        complexity=complexity,
        layout=layout,
    )
    normalized_data["render_signal"] = render_signal

    artifact = BaseArtifact(
        metadata=ArtifactMetadata(
            artifact_type=artifact_type,
            room_source=room_source
        ),
        context=ArtifactContext(
            domain=normalized_data.get("domain"),
            specialization=room_identity.get("specialization"),
            knowledge_class=room_identity.get("knowledge_class"),
            knowledge_scope=normalized_data.get("knowledge_scope", []),
            capabilities=normalized_data.get("capabilities", []),
            research_capabilities=normalized_data.get("research_capabilities", []),
            experiment_capabilities=normalized_data.get("experiment_capabilities", []),
            artifact_outputs=normalized_data.get("artifact_outputs", []),
            scene_contributions=normalized_data.get("scene_contributions", []),
            focus_contributions=normalized_data.get("focus_contributions", []),
            memory_contributions=normalized_data.get("memory_contributions", []),
            trajectory_hints=normalized_data.get("trajectory_hints", []),
            scene_hints=normalized_data.get("scene_hints", [])
        ),
        quality=ArtifactQuality(),
        render=ArtifactRenderContract(
            web_block=render_block,
            viewer=render_block,
            renderer=render_block,
            scene_block=artifact_type,
            payload_type=artifact_type,
            priority=priority,
            complexity=complexity,
            layout=layout,
            machine_only=bool(normalized_data.get("machine_only", False)),
            human_visible=bool(normalized_data.get("human_visible", True)),
            signal_version=UNIFIED_RENDER_SIGNAL_VERSION,
            signal_type=artifact_type,
        ),
        data=normalized_data
    )

    # Make artifact identity observable without changing the payload.
    try:
        artifact.data["render_signal"]["artifact_id"] = artifact.metadata.artifact_id
        artifact.data["render_signal"]["signal"]["artifact_id"] = artifact.metadata.artifact_id
    except Exception:
        pass

    return artifact


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



def _artifact_canonical_render_blocks(artifact: BaseArtifact) -> List[Dict[str, Any]]:
    """Project one artifact into the single canonical render-block shape."""
    if artifact is None:
        return []

    data = dict(getattr(artifact, "data", {}) or {})
    artifact_type = getattr(getattr(artifact, "metadata", None), "artifact_type", "") or data.get("artifact_type", "")
    room_source = getattr(getattr(artifact, "metadata", None), "room_source", "") or data.get("room_source", "")
    render = getattr(artifact, "render", None)
    renderer = getattr(render, "web_block", "") or ARTIFACT_BLOCK_MAP.get(artifact_type, "FunctionBlock")
    priority = getattr(render, "priority", data.get("priority", 100))
    complexity = getattr(render, "complexity", data.get("complexity", "balanced"))
    layout = getattr(render, "layout", data.get("layout", "single"))
    content = _extract_text_candidate(data)

    structured_payload = data.get("payload")
    if not isinstance(structured_payload, dict):
        structured_payload = {
            key: value
            for key, value in data.items()
            if key not in _CANONICAL_TEXT_KEYS
            and key not in {"render_signal", "presentation", "machine_only", "human_visible"}
        }

    signal = data.get("render_signal")
    if not isinstance(signal, dict):
        signal = _build_artifact_render_signal(
            artifact_type=artifact_type,
            room_source=room_source,
            renderer=renderer,
            payload=structured_payload,
            content=content,
            priority=priority,
            complexity=complexity,
            layout=layout,
        )

    signal = dict(signal)
    signal.setdefault("artifact_id", getattr(getattr(artifact, "metadata", None), "artifact_id", ""))
    signal.setdefault("signal_version", UNIFIED_RENDER_SIGNAL_VERSION)
    signal.setdefault("type", artifact_type)
    signal.setdefault("payload_type", artifact_type)
    signal.setdefault("renderer", renderer)
    signal.setdefault("viewer", renderer)
    signal.setdefault("source_room", room_source)
    signal.setdefault("payload", structured_payload)

    block = {
        "type": artifact_type,
        "artifact_type": artifact_type,
        "renderer": renderer,
        "viewer": renderer,
        "content": content,
        "text": content,
        "payload": structured_payload,
        "signal": dict(signal.get("signal") or {
            "type": artifact_type,
            "payload_type": artifact_type,
            "renderer": renderer,
            "viewer": renderer,
            "source_room": room_source,
            "version": UNIFIED_RENDER_SIGNAL_VERSION,
            "scene_contract": True,
        }),
        "signal_version": UNIFIED_RENDER_SIGNAL_VERSION,
        "source_room": room_source,
        "artifact_id": getattr(getattr(artifact, "metadata", None), "artifact_id", ""),
        "priority": priority,
        "complexity": complexity,
        "layout": layout,
        "scene_contract": True,
        "provider_payload": True,
        "canonical_provider_payload": True,
        "executor_generated": False,
    }
    return [block]


def _ensure_artifact_render_signal(artifact: BaseArtifact) -> BaseArtifact:
    """Ensure a room artifact has exactly one lossless render signal."""
    blocks = _artifact_canonical_render_blocks(artifact)
    if blocks:
        artifact.data["render_signal"] = dict(blocks[0].get("signal") or {})
        artifact.data["render_signal"]["payload"] = blocks[0].get("payload")
        artifact.data.setdefault("render_blocks", [])
        artifact.data["render_blocks"] = blocks
        artifact.render.signal_version = UNIFIED_RENDER_SIGNAL_VERSION
        artifact.render.signal_type = blocks[0].get("type", "")
    return artifact

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
        artifact = _ensure_artifact_render_signal(artifact)
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
        canonical_artifact_blocks = _artifact_canonical_render_blocks(artifact)
        existing_room_blocks = list(artifact_payload.get("render_blocks", []) or [])
        artifact_payload["render_blocks"] = canonical_artifact_blocks or existing_room_blocks
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


def create_diagram_artifact(
    semantic: Optional[Dict[str, Any]] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> BaseArtifact:
    '''Create the canonical C_DIAGRAM_ROOM artifact for the same Fiber route.'''
    data = build_diagram_room_payload(semantic, payload)
    return create_artifact(
        artifact_type="diagram",
        room_source="C_DIAGRAM_ROOM",
        data=data,
    )


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
    "FACTORY_ROOM_PROFILES",
    "get_factory_room_profile",
    "build_diagram_room_payload",
    "create_diagram_artifact",
    "FactoryRoomContribution",
    "QuantumFactoryState",
    "bind_request_to_fiber",
    "create_quantum_factory_state",
    "quantum_factory_room_begin",
    "quantum_factory_accept_artifact",
    "quantum_factory_accept_response",
    "quantum_factory_finalize",
    "coordinate_factory_response",
    "validate_quantum_factory_result",
    "validate_diagram_factory_artifact",
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


def _ensure_visible_text_block(scene: Any, blocks: list) -> list:
    """Guarantee one canonical text block when a visible textual answer exists.

    This is a transport invariant, not a fallback route: the same SceneContract
    remains authoritative, but a plain answer must never disappear merely because
    no renderer block was materialized upstream.
    """
    normalized = list(blocks or [])
    if normalized or _scene_is_internal_only(scene):
        return normalized

    content = _scene_text_fallback(scene)
    if not content:
        return normalized

    metadata = getattr(scene, "metadata", {}) or {}
    presentation = metadata.get("presentation", {}) or {}
    payload_type = presentation.get("payload_type", "text") or "text"
    renderer = presentation.get("renderer") or SCENE_BLOCK_REGISTRY.get(payload_type, "TextBlock")
    viewer = presentation.get("viewer") or renderer

    return [{
        "type": payload_type,
        "renderer": renderer,
        "viewer": viewer,
        "content": content,
        "priority": presentation.get("priority", 100),
    }]


def build_scene_contract(scene: MachineScene) -> SceneContract:
    # Stage 3: finalize the canonical SceneContract from MachineScene.
    """Canonical SceneContract builder from MachineScene."""
    contract = scene.contract or create_default_scene_contract()

    # One canonical transport path: MachineResponse -> MachineScene ->
    # SceneContract. Never let an empty renderer list erase an existing answer.
    canonical_blocks = build_canonical_scene_blocks(scene)
    canonical_blocks = _ensure_visible_text_block(scene, canonical_blocks)
    contract.blocks = canonical_blocks
    contract.render_blocks = list(canonical_blocks)
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
    # Final transport invariant: visible text and render_blocks must agree.
    if canonical_text and not contract.metadata.get("machine_only") and not contract.render_blocks:
        contract.render_blocks = _ensure_visible_text_block(scene, [])
        contract.blocks = list(contract.render_blocks)

    scene.contract = contract
    return contract



# =====================================================
# QUANTUM FACTORY CONTROL
# =====================================================
# The Factory does not become a second processor and does not create a
# second route.  It is a coordinated production layer controlled by the
# Quantum Executor through the same Fiber Core.
#
# Design invariant:
#   Quantum Executor
#       -> one MachineRequest
#       -> one Fiber Core / one route
#       -> one factory control session
#       -> zero or more domain-room contributions
#       -> one MachineResponse
#       -> one MachineScene
#       -> one SceneContract
#       -> April Web
#
# Room selection/meaning comes from the processor's contextual analysis.
# This layer never uses keyword triggers to select a room.
# =====================================================

QUANTUM_FACTORY_VERSION = "april_quantum_factory_control_v1"
QUANTUM_FACTORY_SINGLE_ROUTE = True


@dataclass
class FactoryRoomContribution:
    """One room's contribution inside the current Fiber transaction."""
    room: str = ""
    artifact: Optional[BaseArtifact] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    accepted: bool = False
    sequence: int = 0


@dataclass
class QuantumFactoryState:
    """Per-request factory state. Never shared between users."""
    request_id: str = ""
    flow_id: str = ""
    user_id: str = ""
    route_id: str = FIBER_ROUTE_NAME
    lane: str = "A"
    status: str = "READY"
    expected_rooms: List[str] = field(default_factory=list)
    active_rooms: List[str] = field(default_factory=list)
    completed_rooms: List[str] = field(default_factory=list)
    contributions: List[FactoryRoomContribution] = field(default_factory=list)
    render_blocks: List[Dict[str, Any]] = field(default_factory=list)
    diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _request_flow_id(request: Optional[MachineRequest]) -> str:
    if request is None:
        return ""
    metadata = _safe_dict(getattr(request, "metadata", {}))
    if metadata.get("flow_id"):
        return str(metadata["flow_id"])
    routing = _safe_dict(getattr(request, "routing", {}))
    return str(routing.get("flow_id", "") or "")


def bind_request_to_fiber(
    request: MachineRequest,
    *,
    user_id: str = "",
    flow_id: str = "",
    lane: str = "A",
) -> MachineRequest:
    """Bind processor identity/trace to the existing Fiber Core.

    This only enriches the canonical request. It does not create a route,
    Provider, memory, Executor, or renderer.
    """
    if request is None:
        raise ValueError("request is required")

    fiber = request.fiber or FiberCoreContract()
    request.fiber = fiber

    fiber.identity.user_id = str(user_id or fiber.identity.user_id or "")
    fiber.route.active_lane = str(lane or fiber.route.active_lane or "A")
    fiber.lane.lane_id = fiber.route.active_lane
    fiber.lane.lane_name = f"Lane {fiber.route.active_lane}"
    fiber.metrics.lane = fiber.route.active_lane
    fiber.trace.lane = fiber.route.active_lane

    resolved_flow = str(flow_id or _request_flow_id(request) or "")
    if resolved_flow:
        request.metadata = dict(getattr(request, "metadata", {}) or {})
        request.metadata["flow_id"] = resolved_flow
        request.routing = dict(request.routing or {})
        request.routing["flow_id"] = resolved_flow

    request.metadata = dict(getattr(request, "metadata", {}) or {})
    request.metadata.update({
        "quantum_factory_version": QUANTUM_FACTORY_VERSION,
        "single_route": True,
        "fiber_route": FIBER_ROUTE_NAME,
        "user_bound": bool(fiber.identity.user_id),
    })
    request.routing = dict(request.routing or {})
    request.routing["single_route"] = True
    request.routing["fiber_route"] = FIBER_ROUTE_NAME
    return request


def create_quantum_factory_state(
    request: MachineRequest,
    *,
    user_id: str = "",
    flow_id: str = "",
) -> QuantumFactoryState:
    """Create isolated factory state for exactly one request/user."""
    request = bind_request_to_fiber(
        request,
        user_id=user_id,
        flow_id=flow_id,
        lane=request.fiber.route.active_lane if request.fiber else "A",
    )

    expected = []
    for value in (
        list(getattr(request, "required_competencies", []) or [])
        + list(getattr(request, "required_artifacts", []) or [])
    ):
        value = str(value or "").strip()
        if value and value not in expected:
            expected.append(value)

    return QuantumFactoryState(
        request_id=str(getattr(request, "request_id", "") or ""),
        flow_id=str(_request_flow_id(request) or ""),
        user_id=str(user_id or request.fiber.identity.user_id or ""),
        lane=str(request.fiber.route.active_lane or "A"),
        expected_rooms=expected,
    )


def quantum_factory_room_begin(
    factory: QuantumFactoryState,
    room_name: str,
) -> None:
    """Mark a processor-selected room as active on the same Fiber route."""
    if not factory:
        return
    room = str(room_name or "").strip()
    if not room:
        return

    factory.status = "RUNNING"
    if room not in factory.active_rooms:
        factory.active_rooms.append(room)
    factory_stage_begin("ROOM_BEGIN", {
        "room": room,
        "request_id": factory.request_id,
        "flow_id": factory.flow_id,
        "user_id": factory.user_id,
        "lane": factory.lane,
        "single_route": True,
        "quantum_factory_version": QUANTUM_FACTORY_VERSION,
    })


def quantum_factory_accept_artifact(
    factory: QuantumFactoryState,
    room_name: str,
    artifact: Optional[BaseArtifact],
) -> Optional[FactoryRoomContribution]:
    """Accept one room artifact without rewriting its payload."""
    if not factory or artifact is None:
        return None

    room = str(room_name or getattr(artifact.metadata, "room_source", "") or "").strip()
    if not room:
        room = str(getattr(artifact.metadata, "room_source", "") or "UNKNOWN_ROOM")

    # Re-materialize the canonical signal only when the artifact has not
    # already got one. Existing room payload is never replaced.
    artifact = _ensure_artifact_render_signal(artifact)

    contribution = FactoryRoomContribution(
        room=room,
        artifact=artifact,
        payload=dict(getattr(artifact, "data", {}) or {}),
        accepted=True,
        sequence=len(factory.contributions) + 1,
    )
    factory.contributions.append(contribution)

    if room not in factory.completed_rooms:
        factory.completed_rooms.append(room)

    blocks = _artifact_canonical_render_blocks(artifact)
    for block in blocks:
        if block not in factory.render_blocks:
            factory.render_blocks.append(block)

    factory_stage_success("ROOM_SUCCESS", {
        "room": room,
        "request_id": factory.request_id,
        "flow_id": factory.flow_id,
        "user_id": factory.user_id,
        "lane": factory.lane,
        "artifact": getattr(artifact.metadata, "artifact_type", ""),
        "render_blocks": len(blocks),
        "single_route": True,
    })
    return contribution


def quantum_factory_accept_response(
    factory: QuantumFactoryState,
    response: MachineResponse,
) -> MachineResponse:
    """Merge room contributions into the canonical MachineResponse."""
    if not factory or response is None:
        return response

    response.fiber = response.fiber or FiberCoreContract()
    response.fiber.identity.user_id = factory.user_id
    response.fiber.route.active_lane = factory.lane
    response.fiber.lane.lane_id = factory.lane
    response.fiber.lane.lane_name = f"Lane {factory.lane}"
    response.fiber.trace.lane = factory.lane
    response.fiber.metrics.lane = factory.lane

    existing = list(getattr(response, "render_blocks", []) or [])
    merged = existing[:]

    for block in factory.render_blocks:
        if block not in merged:
            merged.append(block)

    response.render_blocks = merged

    response.artifacts = list(getattr(response, "artifacts", []) or [])
    for contribution in factory.contributions:
        if contribution.artifact is not None and contribution.artifact not in response.artifacts:
            response.artifacts.append(contribution.artifact)

    response.contributions = dict(getattr(response, "contributions", {}) or {})
    for contribution in factory.contributions:
        response.contributions[contribution.room] = dict(contribution.payload)

    response.metadata = dict(getattr(response, "metadata", {}) or {})
    response.metadata.update({
        "quantum_factory_version": QUANTUM_FACTORY_VERSION,
        "factory_request_id": factory.request_id,
        "flow_id": factory.flow_id,
        "user_id": factory.user_id,
        "factory_lane": factory.lane,
        "factory_rooms": list(factory.completed_rooms),
        "factory_contribution_count": len(factory.contributions),
        "single_route": True,
        "canonical_factory_merge": True,
    })

    return response


def quantum_factory_finalize(
    factory: QuantumFactoryState,
    response: MachineResponse,
) -> MachineResponse:
    """Close the current factory transaction and preserve one route."""
    response = quantum_factory_accept_response(factory, response)

    if factory:
        factory.status = "COMPLETE"
        factory_stage_success("FACTORY_COMPLETE", {
            "request_id": factory.request_id,
            "flow_id": factory.flow_id,
            "user_id": factory.user_id,
            "lane": factory.lane,
            "rooms": list(factory.completed_rooms),
            "contributions": len(factory.contributions),
            "render_blocks": len(factory.render_blocks),
            "single_route": True,
            "quantum_factory_version": QUANTUM_FACTORY_VERSION,
        })

    return response


def coordinate_factory_response(
    request: MachineRequest,
    response: MachineResponse,
    *,
    user_id: str = "",
    flow_id: str = "",
) -> tuple[MachineResponse, QuantumFactoryState]:
    """Canonical Quantum Executor -> Factory coordination point.

    The processor remains the authority for interpretation. The Factory
    receives the already-decided request, accepts domain-room artifacts,
    merges them into the same MachineResponse, and returns that response
    to the existing SceneContract path.
    """
    request = bind_request_to_fiber(
        request,
        user_id=user_id,
        flow_id=flow_id,
    )
    factory = create_quantum_factory_state(
        request,
        user_id=user_id,
        flow_id=flow_id,
    )

    # Existing response artifacts are already authoritative room output.
    # Accept them without inventing room selection.
    for artifact in list(getattr(response, "artifacts", []) or []):
        room = str(getattr(getattr(artifact, "metadata", None), "room_source", "") or "")
        quantum_factory_accept_artifact(factory, room, artifact)

    response = quantum_factory_finalize(factory, response)
    return response, factory


# =====================================================
# FACTORY OUTPUT VALIDATION
# =====================================================

def validate_diagram_factory_artifact(artifact: Optional[BaseArtifact]) -> Dict[str, Any]:
    '''Validate canonical diagram -> DiagramBlock transport.'''
    if artifact is None:
        return {"ok": False, "reason": "missing_artifact"}
    metadata = getattr(artifact, "metadata", None)
    render = getattr(artifact, "render", None)
    artifact_type = getattr(metadata, "artifact_type", "")
    room = getattr(metadata, "room_source", "")
    renderer = getattr(render, "web_block", "")
    return {
        "ok": (
            artifact_type == "diagram"
            and room == "C_DIAGRAM_ROOM"
            and renderer == "DiagramBlock"
        ),
        "artifact_type": artifact_type,
        "room_source": room,
        "renderer": renderer,
        "single_route": True,
    }


def validate_quantum_factory_result(
    request: MachineRequest,
    response: MachineResponse,
    factory: QuantumFactoryState,
) -> Dict[str, Any]:
    """Check the single-route invariants before SceneContract creation."""
    request_user = str(getattr(request.fiber.identity, "user_id", "") or "")
    response_user = str(getattr(response.fiber.identity, "user_id", "") or "")

    return {
        "ok": bool(
            factory
            and factory.status == "COMPLETE"
            and factory.route_id == FIBER_ROUTE_NAME
            and request_user == response_user
        ),
        "single_route": True,
        "route_id": FIBER_ROUTE_NAME,
        "request_id": factory.request_id if factory else "",
        "flow_id": factory.flow_id if factory else "",
        "user_id": response_user,
        "lane": factory.lane if factory else "",
        "room_count": len(factory.completed_rooms) if factory else 0,
        "artifact_count": len(getattr(response, "artifacts", []) or []),
        "render_block_count": len(getattr(response, "render_blocks", []) or []),
    }


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
    factory_stage_error(
        f"{room_name}: {error}",
        error,
    )

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
