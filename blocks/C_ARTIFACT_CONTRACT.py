from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from copy import deepcopy
import uuid
import time
import hashlib

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


def _normalize_table_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize table cells without selecting a route or changing semantics."""
    payload = dict(payload or {})
    columns = payload.get("columns") or payload.get("headers") or []
    if isinstance(columns, str):
        columns = [x.strip() for x in columns.split("|")] if "|" in columns else [columns.strip()]
    columns = [x for x in columns if x is not None]

    rows = payload.get("rows") or []
    if isinstance(rows, dict):
        rows = list(rows.values())
    elif not isinstance(rows, (list, tuple)):
        rows = [rows]

    normalized_rows = []
    for row in rows:
        if isinstance(row, dict):
            values = [row.get(column, "") for column in columns] if columns else list(row.values())
        elif isinstance(row, (list, tuple)):
            values = list(row)
        elif isinstance(row, str):
            if "|" in row:
                values = [part.strip() for part in row.split("|")]
            elif "\t" in row:
                values = [part.strip() for part in row.split("\t")]
            else:
                values = [row.strip()]
        else:
            values = [row]
        normalized_rows.append(values)

    width = len(columns) or max((len(row) for row in normalized_rows), default=0)
    if not columns and width:
        columns = [f"Column {i + 1}" for i in range(width)]
    for row in normalized_rows:
        if len(row) < width:
            row.extend([""] * (width - len(row)))
        elif len(row) > width:
            del row[width:]

    payload["columns"] = columns
    payload["rows"] = normalized_rows
    payload["table_schema"] = "april.table.canonical.v2"
    payload["presentation"] = {
        **dict(payload.get("presentation") or {}),
        "renderer": "TableBlock",
        "engine": "McDowell",
        "math_engine": "KaTeX",
        "payload_unchanged": True,
    }
    return payload


def _normalize_diagram_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Keep diagram semantics structural: nodes/edges/layout, never keyword routing."""
    payload = dict(payload or {})
    nodes = payload.get("nodes") or []
    edges = payload.get("edges") or []
    relations = payload.get("relations") or []

    if not isinstance(nodes, list):
        nodes = list(nodes.values()) if isinstance(nodes, dict) else [nodes]
    if not isinstance(edges, list):
        edges = list(edges.values()) if isinstance(edges, dict) else [edges]
    if not isinstance(relations, list):
        relations = list(relations.values()) if isinstance(relations, dict) else [relations]

    canonical_nodes = []
    for i, node in enumerate(nodes):
        if isinstance(node, dict):
            item = dict(node)
            item.setdefault("id", str(item.get("name") or item.get("label") or f"node_{i + 1}"))
            item.setdefault("label", str(item.get("name") or item.get("id") or ""))
            canonical_nodes.append(item)
        else:
            label = str(node).strip()
            if label:
                canonical_nodes.append({"id": f"node_{i + 1}", "label": label, "type": "node"})

    canonical_edges = []
    for edge in edges + relations:
        if not isinstance(edge, dict):
            continue
        source = edge.get("from") or edge.get("source") or edge.get("start")
        target = edge.get("to") or edge.get("target") or edge.get("end")
        if source and target:
            canonical_edges.append({
                "from": str(source),
                "to": str(target),
                **({"label": str(edge["label"])} if edge.get("label") is not None else {}),
            })

    payload["nodes"] = canonical_nodes
    payload["edges"] = canonical_edges
    payload["layout"] = payload.get("layout") or {"direction": "LR"}
    payload["diagram_schema"] = "april.diagram.canonical.v2"
    existing_presentation = dict(payload.get("presentation") or {})
    concrete_renderer = (
        payload.get("renderer")
        or existing_presentation.get("renderer")
        or "MessageTextBlock"
    )
    payload["representation"] = payload.get("representation") or (
        "geometric_figure"
        if concrete_renderer in {"GalleryBlock", "SvgBlock", "ArithmeticDiagram"}
        else "schematic"
    )
    payload["presentation"] = {
        **existing_presentation,
        "renderer": concrete_renderer,
        "engine": "McDowell",
        "payload_unchanged": True,
        "text_companion_required": True,
    }
    return payload


def _normalize_image_gallery_payload(structured_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize one image source into the exact GalleryBlock image-item contract."""
    payload = dict(structured_payload or {})
    existing = payload.get("images") or payload.get("items") or payload.get("gallery") or payload.get("sources")
    if isinstance(existing, list) and existing:
        return payload

    direct = (
        payload.get("src")
        or payload.get("url")
        or payload.get("image")
        or payload.get("image_data_uri")
        or payload.get("data_uri")
        or ""
    )
    base64_value = payload.get("image_base64") or payload.get("base64") or ""
    mime = str(payload.get("mime_type") or "image/png").strip() or "image/png"
    if not direct and base64_value:
        direct = f"data:{mime};base64,{base64_value}"
    if not direct:
        return payload

    item = {
        "src": direct,
        "url": direct,
        "image": direct,
        "mime_type": mime,
        "width": payload.get("width"),
        "height": payload.get("height"),
        "title": payload.get("title") or "Image",
        "alt": payload.get("alt") or payload.get("prompt") or payload.get("description") or "April image",
        "caption": payload.get("caption") or payload.get("prompt") or payload.get("description") or "",
    }
    payload["images"] = [item]
    return payload


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

    if not isinstance(structured_payload, dict):
        structured_payload = {}
    if artifact_type in {"image", "gallery", "scene", "visual_context"}:
        structured_payload = _normalize_image_gallery_payload(structured_payload)
    elif artifact_type == "table":
        structured_payload = _normalize_table_payload(structured_payload)
    elif artifact_type == "diagram":
        structured_payload = _normalize_diagram_payload(structured_payload)

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
    # Canonical presentation contract transported with the same Fiber signal.
    presentation: Dict[str, Any] = field(default_factory=dict)

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

# Renderer capability map.
# artifact_type identifies the produced representation; renderer identifies
# the concrete Web viewer for this particular artifact. One room may therefore
# produce multiple concrete renderers without creating a second route.
WEB_RENDERER_REGISTRY_VERSION = "3.0"

# Exact renderer contract mirrored from the actual April Web RenderMessage
# registry. This describes the destination component; it never performs routing.
WEB_RENDERER_REGISTRY = {
    "text": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["content", "text", "answer"]},
    "markdown": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["content", "text", "markdown"]},
    "formula": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["formula", "equation", "expression", "math", "content"], "mode": "force_math"},
    "graph": {"renderer": "GraphBlock", "viewer": "GraphBlock", "fallback_renderer": "", "payload_keys": ["series", "x_axis", "data_table", "points"]},
    "table": {"renderer": "TableBlock", "viewer": "TableBlock", "fallback_renderer": "", "payload_keys": ["rows", "columns", "headers", "data", "values", "items"]},
    "diagram": {"renderer": "GalleryBlock", "viewer": "GalleryBlock", "fallback_renderer": "", "payload_keys": ["elements", "svg", "geometry", "points"], "specialized_renderers": ["SvgBlock", "ArithmeticDiagram"]},
    "image": {"renderer": "GalleryBlock", "viewer": "GalleryBlock", "fallback_renderer": "", "payload_keys": ["images", "src", "url", "image", "image_data_uri", "image_base64"]},
    "gallery": {"renderer": "GalleryBlock", "viewer": "GalleryBlock", "fallback_renderer": "", "payload_keys": ["images", "items", "gallery", "sources"]},
    "scene": {"renderer": "GalleryBlock", "viewer": "GalleryBlock", "fallback_renderer": "", "payload_keys": ["elements", "svg", "images", "objects"]},
    "visual_context": {"renderer": "GalleryBlock", "viewer": "GalleryBlock", "fallback_renderer": "", "payload_keys": ["images", "elements", "svg", "context"]},
    "code": {"renderer": "CodeBlock", "viewer": "CodeBlock", "fallback_renderer": "", "payload_keys": ["code", "content", "language"]},
    "link": {"renderer": "LinkCard", "viewer": "LinkCard", "fallback_renderer": "", "payload_keys": ["url", "href", "title", "description"]},
    "file": {"renderer": "LinkCard", "viewer": "LinkCard", "fallback_renderer": "", "payload_keys": ["url", "href", "path", "name"]},
    "audio": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["url", "src", "path", "content"]},
    "video": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["url", "src", "path", "content"]},
    "action": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["action", "target", "parameters", "content"]},
    "memory": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["content", "summary", "memory"]},
}

ARTIFACT_BLOCK_MAP = {kind: spec["renderer"] for kind, spec in WEB_RENDERER_REGISTRY.items()}
ARTIFACT_BLOCK_MAP["function"] = "MessageTextBlock"

# Concrete renderers that are allowed to cross the artifact/Fiber boundary.
SUPPORTED_RENDERERS = {
    "MessageTextBlock", "GraphBlock", "TableBlock", "GalleryBlock",
    "CodeBlock", "LinkCard", "FunctionBlock", "FormulaBlock",
    "SvgBlock", "ArithmeticDiagram",
}

# Data-driven renderer aliases. They refine a produced representation; they do
# not perform lexical routing.
ARTIFACT_RENDERER_ALIASES = {
    "text": "MessageTextBlock",
    "markdown": "MessageTextBlock",
    "message": "MessageTextBlock",
    "message_text": "MessageTextBlock",
    "diagram": "GalleryBlock",
    "diagramblock": "GalleryBlock",
    "schematic": "GalleryBlock",
    "gallery": "GalleryBlock",
    "image": "GalleryBlock",
    "figure": "GalleryBlock",
    "geometry": "GalleryBlock",
    "geometric_figure": "GalleryBlock",
    "svg": "SvgBlock",
    "arithmetic_diagram": "ArithmeticDiagram",
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
        # Default only. A concrete artifact can select its own viewer.
        "renderer": "MessageTextBlock",
        "viewer": "MessageTextBlock",
        "allowed_renderers": [
            "MessageTextBlock", "GalleryBlock", "SvgBlock", "ArithmeticDiagram"
        ],
        "semantic_service": "APRIL_DIAGRAM_SYSTEM_CORE",
        "capabilities": [
            "spatial_semantics",
            "geometry",
            "relations",
            "structure",
            "engineering_layout",
            "schematic_rendering",
            "geometric_figure_rendering",
        ],
        "machine_input": "MachineRequest",
        "machine_output": "BaseArtifact",
        "scene_output": "SceneContract",
        "single_route": True,
        "text_companion_required": True,
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
    requested_renderer = (
        payload.get("renderer")
        or (payload.get("presentation") or {}).get("renderer")
        or payload.get("viewer")
        or profile["renderer"]
    )
    requested_renderer = ARTIFACT_RENDERER_ALIASES.get(
        str(requested_renderer or "").strip().lower(),
        str(requested_renderer or "").strip(),
    )
    if requested_renderer not in profile.get("allowed_renderers", []):
        requested_renderer = profile["renderer"]

    rendering_mode = str(
        payload.get("rendering_mode")
        or (payload.get("presentation") or {}).get("rendering_mode")
        or (
            "geometric_figure"
            if requested_renderer in {"GalleryBlock", "SvgBlock", "ArithmeticDiagram"}
            else "schematic"
        )
    ).strip().lower()

    payload.update({
        "artifact_type": profile["artifact_type"],
        "room_source": profile["room"],
        "renderer": requested_renderer,
        "viewer": payload.get("viewer") or requested_renderer,
        "rendering_mode": rendering_mode,
        "allowed_renderers": list(profile.get("allowed_renderers", [])),
        "semantic": semantic,
        "diagram_semantics": semantic,
        "machine_only": bool(payload.get("machine_only", False)),
        "text_companion_required": True,
    })
    return payload


# =====================================================
# CANONICAL RENDER SIGNAL
# =====================================================
UNIFIED_RENDER_SIGNAL_VERSION = "3.0"


def _render_signal_metadata(
    artifact_type: str,
    room_source: str,
    renderer: str,
    *,
    content: str = "",
    priority: int = 100,
    complexity: str = "balanced",
    layout: str = "single",
    presentation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return only transport metadata; payload stays structured and untouched."""
    registration = WEB_RENDERER_REGISTRY.get(
        str(artifact_type or "").strip().lower(),
        WEB_RENDERER_REGISTRY["text"],
    )
    exact_renderer = str(registration.get("renderer") or renderer or "MessageTextBlock")
    fallback_renderer = str(registration.get("fallback_renderer") or "MessageTextBlock")
    candidates = [exact_renderer]
    return {
        "type": artifact_type,
        "payload_type": artifact_type,
        "renderer": exact_renderer,
        "viewer": str(registration.get("viewer") or exact_renderer),
        "web_renderer": exact_renderer,
        "fallback_renderer": fallback_renderer,
        "renderer_candidates": candidates,
        "web_registry_version": WEB_RENDERER_REGISTRY_VERSION,
        "signal_channel": "canonical_web_render_signal_v2",
        "source_room": room_source,
        "version": UNIFIED_RENDER_SIGNAL_VERSION,
        "content_present": bool(content),
        "priority": priority,
        "complexity": complexity,
        "layout": layout,
        "scene_contract": True,
        "presentation": dict(presentation or {}),
        "payload_contract_keys": list(registration.get("payload_keys") or []),
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
    presentation: Optional[Dict[str, Any]] = None,
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
            presentation=presentation,
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
        "presentation": dict(presentation or {}),
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

    explicit_renderer = (
        normalized_data.get("renderer")
        or (normalized_data.get("presentation") or {}).get("renderer")
        or normalized_data.get("viewer")
    )
    explicit_renderer = ARTIFACT_RENDERER_ALIASES.get(
        str(explicit_renderer or "").strip().lower(),
        str(explicit_renderer or "").strip(),
    )
    render_block = (
        explicit_renderer
        if explicit_renderer in SUPPORTED_RENDERERS
        else ARTIFACT_BLOCK_MAP.get(artifact_type, "FunctionBlock")
    )

    priority = normalized_data.get("priority", 100)
    complexity = normalized_data.get("complexity", "balanced")
    layout = normalized_data.get("layout", "single")
    presentation = dict(normalized_data.get("presentation") or {})
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
        presentation=presentation,
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
            presentation=presentation,
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



def _text_companion_blocks(
    artifact_type: str,
    content: str,
    data: Dict[str, Any],
    presentation: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Legacy compatibility hook. Scene-level composition owns text nodes now."""
    return []

def _artifact_canonical_render_blocks(artifact: BaseArtifact) -> List[Dict[str, Any]]:
    """Project one artifact into lossless canonical render blocks.

    Concrete renderer identity is preserved from the artifact/presentation.
    Every human-visible specialized result gets a MessageTextBlock companion
    so narrative content is never forced into the specialized renderer.
    """
    if artifact is None:
        return []

    data = dict(getattr(artifact, "data", {}) or {})
    artifact_type = getattr(getattr(artifact, "metadata", None), "artifact_type", "") or data.get("artifact_type", "")
    room_source = getattr(getattr(artifact, "metadata", None), "room_source", "") or data.get("room_source", "")
    render = getattr(artifact, "render", None)

    explicit_renderer = (
        data.get("renderer")
        or (data.get("presentation") or {}).get("renderer")
        or data.get("viewer")
    )
    explicit_renderer = ARTIFACT_RENDERER_ALIASES.get(
        str(explicit_renderer or "").strip().lower(),
        str(explicit_renderer or "").strip(),
    )
    renderer = (
        explicit_renderer
        if explicit_renderer in SUPPORTED_RENDERERS
        else getattr(render, "web_block", "")
        or ARTIFACT_BLOCK_MAP.get(artifact_type, "FunctionBlock")
    )

    priority = getattr(render, "priority", data.get("priority", 100))
    complexity = getattr(render, "complexity", data.get("complexity", "balanced"))
    layout = getattr(render, "layout", data.get("layout", "single"))
    content = _extract_text_candidate(data)

    structured_payload = data.get("payload")
    if not isinstance(structured_payload, dict):
        structured_payload = {
            key: value for key, value in data.items()
            if key not in _CANONICAL_TEXT_KEYS
            and key not in {"render_signal", "presentation", "machine_only", "human_visible"}
        }

    signal = data.get("render_signal")
    if not isinstance(signal, dict):
        signal = _build_artifact_render_signal(
            artifact_type=artifact_type, room_source=room_source, renderer=renderer,
            payload=structured_payload, content=content, priority=priority,
            complexity=complexity, layout=layout, presentation=dict(data.get("presentation") or {}),
        )
    signal = dict(signal)
    presentation = data.get("presentation")
    if not isinstance(presentation, dict):
        presentation = dict(signal.get("presentation") or {})

    signal.update({
        "renderer": renderer,
        "viewer": data.get("viewer") or renderer,
        "type": artifact_type,
        "payload_type": artifact_type,
        "source_room": room_source,
        "payload": structured_payload,
        "presentation": presentation,
        "signal_version": UNIFIED_RENDER_SIGNAL_VERSION,
        "artifact_id": signal.get("artifact_id") or getattr(getattr(artifact, "metadata", None), "artifact_id", ""),
    })

    specialized_block = {
        "type": artifact_type,
        "artifact_type": artifact_type,
        "renderer": renderer,
        "viewer": data.get("viewer") or renderer,
        "content": content,
        "text": content,
        "payload": structured_payload,
        "signal": dict(signal.get("signal") or {}),
        "signal_version": UNIFIED_RENDER_SIGNAL_VERSION,
        "source_room": room_source,
        "artifact_id": getattr(getattr(artifact, "metadata", None), "artifact_id", ""),
        "priority": priority,
        "complexity": complexity,
        "layout": layout,
        "presentation": presentation,
        "scene_contract": True,
        "provider_payload": True,
        "canonical_provider_payload": True,
        "executor_generated": False,
        "text_companion_required": bool(data.get("text_companion_required", True)),
    }

    # A room artifact is exactly one scene node. Narrative text is composed once
    # at SceneContract level, so an artifact never manufactures duplicate text
    # companions of its own.
    return [specialized_block]

def _ensure_artifact_render_signal(artifact: BaseArtifact) -> BaseArtifact:
    """Ensure a room artifact has exactly one lossless render signal."""
    blocks = _artifact_canonical_render_blocks(artifact)
    if blocks:
        specialized = next(
            (block for block in blocks if str(block.get("renderer") or "") not in {"", "MessageTextBlock", "TextBlock", "MarkdownBlock"}),
            blocks[-1],
        )
        artifact.data["render_signal"] = dict(specialized.get("signal") or blocks[-1].get("signal") or {})
        artifact.data["render_signal"]["payload"] = specialized.get("payload") if specialized.get("payload") is not None else blocks[-1].get("payload")
        artifact.data["render_signal"]["renderer"] = specialized.get("renderer") or blocks[-1].get("renderer") or "MessageTextBlock"
        artifact.data["render_signal"]["viewer"] = specialized.get("viewer") or blocks[-1].get("viewer") or "MessageTextBlock"
        artifact.data.setdefault("render_blocks", [])
        artifact.data["render_blocks"] = blocks
        artifact.render.signal_version = UNIFIED_RENDER_SIGNAL_VERSION
        artifact.render.signal_type = specialized.get("type", blocks[-1].get("type", ""))
        artifact.render.web_block = specialized.get("renderer") or blocks[-1].get("renderer", artifact.render.web_block)
        artifact.render.viewer = specialized.get("viewer") or artifact.render.web_block
        artifact.render.renderer = artifact.render.web_block
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
        presentation = artifact_payload.get("presentation")
        if not isinstance(presentation, dict):
            presentation = build_presentation_hint(
                artifact.metadata.artifact_type,
                artifact_payload.get("complexity", "balanced")
            )
            presentation = {
                "version": "1.0",
                "engine": "APRIL-QUANTUM-PRESENTATION-V1",
                "enabled": True,
                "decision_owner": "QUANTUM_PROCESSOR",
                "single_route": True,
                "mode": "semantic_presentation",
                "primary_role": "normal",
                "spans": [],
                "formulas": [],
                "key_points": [],
                "by_block": {},
                "math": {
                    "markdown": "react-markdown",
                    "markdown_extensions": ["remark-gfm"],
                    "math_parse": "remark-math",
                    "math_render": "rehype-katex",
                    "math_css": "katex/dist/katex.min.css",
                    "structural_only": True,
                },
                **presentation,
            }
            artifact_payload["presentation"] = presentation

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
                "presentation_engine": "APRIL-QUANTUM-PRESENTATION-V1",
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
            "presentation_engine": "APRIL-QUANTUM-PRESENTATION-V1",
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
        contract.fiber.renderer.supported_blocks = list(dict.fromkeys(
            str(block.get("renderer") or "")
            for block in canonical_artifact_blocks
            if isinstance(block, dict) and block.get("renderer")
        )) or [artifact.render.web_block or "MessageTextBlock"]
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
    registration = get_web_renderer_registration(artifact_type)
    renderer = registration.get("renderer", "MessageTextBlock")
    fallback = registration.get("fallback_renderer", "MessageTextBlock")
    return {
        "payload_type": artifact_type,
        "scene_block": artifact_type,
        "renderer": renderer,
        "viewer": registration.get("viewer", renderer),
        "web_renderer": renderer,
        "fallback_renderer": "",
        "renderer_candidates": [renderer],
        "web_registry_version": WEB_RENDERER_REGISTRY_VERSION,
        "signal_channel": "canonical_web_render_signal_v2",
        "priority": 100,
        "complexity": complexity,
        "layout": "flow" if complexity != "compact" else "flow",
        "frames": False,
        "cards": False,
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
    kind: spec["renderer"]
    for kind, spec in WEB_RENDERER_REGISTRY.items()
}

@dataclass
class SceneContract:
    """Canonical one-response scene. All visible renderers are children of it."""
    scene_version: str = "3.0"
    scene_id: str = ""
    turn_id: str = ""
    flow_id: str = ""
    topic_group: str = ""
    continuation: bool = False
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    render_blocks: List[Dict[str, Any]] = field(default_factory=list)
    relations: List[Dict[str, Any]] = field(default_factory=list)
    order: List[str] = field(default_factory=list)
    active_scene: str = ""
    space_continuity: Dict[str, Any] = field(default_factory=dict)
    scene_blueprint: Dict[str, Any] = field(default_factory=dict)
    signal: Dict[str, Any] = field(default_factory=dict)
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

    # One scene identity follows the complete route.
    scene_id: str = ""
    turn_id: str = ""
    flow_id: str = ""
    topic_group: str = ""
    continuation: bool = False
    render_blocks: List[Dict[str, Any]] = field(default_factory=list)
    artifacts_payload: List[Dict[str, Any]] = field(default_factory=list)
    scene: Dict[str, Any] = field(default_factory=dict)
    scene_blueprint: Dict[str, Any] = field(default_factory=dict)
    scene_relations: List[Dict[str, Any]] = field(default_factory=list)
    scene_order: List[str] = field(default_factory=list)
    scene_plan: List[str] = field(default_factory=lambda:["text"])
    render_priority: List[str] = field(default_factory=lambda:["text"])
    metadata: Dict[str, Any] = field(default_factory=dict)

def get_web_renderer_registration(payload_type: str) -> Dict[str, Any]:
    """Return the exact April Web registration for a payload type."""
    key = str(payload_type or "").strip().lower()
    return dict(WEB_RENDERER_REGISTRY.get(key) or WEB_RENDERER_REGISTRY["text"])


@dataclass
class MachineScene:
    fiber: FiberCoreContract = field(default_factory=FiberCoreContract)
    scene_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scene_version: str = "3.0"
    active_scene: str = ""
    turn_id: str = ""
    flow_id: str = ""
    topic_group: str = ""
    continuation: bool = False
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    relations: List[Dict[str, Any]] = field(default_factory=list)
    order: List[str] = field(default_factory=list)
    scene_blueprint: Dict[str, Any] = field(default_factory=dict)
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
    "build_presentation_hint",
    "get_web_renderer_registration",
    "SUPPORTED_RENDERERS",
    "WEB_RENDERER_REGISTRY",
    "WEB_RENDERER_REGISTRY_VERSION",
    "ARTIFACT_RENDERER_ALIASES",
    "UNIFIED_RENDER_SIGNAL_VERSION",
    "build_scene_contract",
    "build_scene_signal",
    "CANONICAL_SCENE_VERSION",
    "ANSWER_RENDER_POLICY",
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


CANONICAL_SCENE_VERSION = "3.0"
CANONICAL_SCENE_SIGNAL_TYPE = "scene"
ANSWER_RENDER_POLICY = "render_from_scene_blocks_only"


def _scene_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _scene_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _scene_text(value: Any) -> str:
    for key in ("answer", "content", "summary", "text", "display_text"):
        candidate = value.get(key) if isinstance(value, dict) else getattr(value, key, None)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return ""


def _scene_hash(value: Any) -> str:
    try:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    except Exception:
        raw = repr(value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _scene_block_type(block: Dict[str, Any]) -> str:
    return str(block.get("type") or block.get("artifact_type") or block.get("representation") or "text").strip().lower()


def _scene_block_renderer(block: Dict[str, Any]) -> str:
    renderer = str(block.get("renderer") or block.get("viewer") or "").strip()
    if renderer:
        return renderer
    return ARTIFACT_BLOCK_MAP.get(_scene_block_type(block), "MessageTextBlock")


def _canonical_visual_dedupe_key(block: Dict[str, Any]) -> str:
    block_type = _scene_block_type(block)
    if block_type in {"link", "file"}:
        payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
        url = str(block.get("url") or block.get("href") or payload.get("url") or payload.get("href") or "").strip()
        if url:
            return f"link:{url.split('#', 1)[0].rstrip('/').lower()}"
    if block_type == "graph_data":
        return f"internal:graph_data:{str(block.get('name') or '')}"
    return ""


def _prefer_canonical_visual_block(existing: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    existing_renderer = str(existing.get("renderer") or "").lower()
    candidate_renderer = str(candidate.get("renderer") or "").lower()
    if "linkcard" in candidate_renderer and "message" in existing_renderer:
        return candidate
    return existing

def _scene_blueprint_blocks(blueprint: Dict[str, Any], *, scene_id: str, turn_id: str, flow_id: str) -> List[Dict[str, Any]]:
    nodes = []
    for index, raw in enumerate(_scene_list(blueprint.get("nodes"))):
        if not isinstance(raw, dict):
            continue
        block = dict(raw)
        block_id = str(block.get("block_id") or block.get("id") or f"block_{index + 1}").strip()
        block_type = _scene_block_type(block)
        block["block_id"] = block_id
        block["type"] = block_type
        block["renderer"] = _scene_block_renderer(block)
        block["viewer"] = str(block.get("viewer") or block["renderer"])
        block["scene_id"] = scene_id
        block["turn_id"] = turn_id
        block["flow_id"] = flow_id
        block.setdefault("payload", {})
        block["sequence_index"] = index
        block["render_id"] = str(block.get("render_id") or f"render_{_scene_hash({'scene': scene_id, 'block': block_id, 'renderer': block['renderer']})}")
        block["scene_contract"] = True
        nodes.append(block)
    return nodes


def _canonical_scene_blocks(scene: MachineScene) -> List[Dict[str, Any]]:
    """Produce one ordered, identity-bound render stream for the scene."""
    try:
        from blocks.presentation_formatter import ensure_scene_text_block
    except Exception:
        ensure_scene_text_block = None

    blueprint = dict(scene.scene_blueprint or {})
    blocks = list(scene.blocks or [])
    if not blocks and blueprint:
        blocks = _scene_blueprint_blocks(
            blueprint,
            scene_id=scene.scene_id,
            turn_id=scene.turn_id,
            flow_id=scene.flow_id,
        )

    # Artifacts contribute one node each; never append a second narrative copy.
    existing_artifact_ids = {
        str(block.get("artifact_id"))
        for block in blocks
        if isinstance(block, dict) and block.get("artifact_id")
    }
    for artifact in list(getattr(scene, "artifacts", []) or []):
        if not isinstance(artifact, BaseArtifact):
            continue
        artifact_id = str(getattr(artifact.metadata, "artifact_id", "") or "")
        if artifact_id and artifact_id in existing_artifact_ids:
            continue
        artifact_blocks = _artifact_canonical_render_blocks(artifact)
        for block in artifact_blocks[:1]:
            block = dict(block)
            block["scene_id"] = scene.scene_id
            block["turn_id"] = scene.turn_id
            block["flow_id"] = scene.flow_id
            block["artifact_id"] = artifact_id
            blocks.append(block)
            if artifact_id:
                existing_artifact_ids.add(artifact_id)

    # The answer is a single normal text node in the same scene, not a fallback.
    answer = _scene_text(scene)
    if ensure_scene_text_block is not None:
        blocks = ensure_scene_text_block(
            blocks,
            answer,
            scene_id=scene.scene_id,
            turn_id=scene.turn_id,
            flow_id=scene.flow_id,
            blueprint=blueprint,
        )
    elif answer and not any(_scene_block_type(b) in {"text", "markdown", "formula"} and _scene_text(b) for b in blocks if isinstance(b, dict)):
        blocks.insert(0, {
            "type": "text",
            "artifact_type": "text",
            "renderer": "MessageTextBlock",
            "viewer": "MessageTextBlock",
            "content": answer,
            "text": answer,
        })

    order = [str(x).strip() for x in _scene_list(blueprint.get("order")) if str(x).strip()]
    order_pos = {value: idx for idx, value in enumerate(order)}
    normalized: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_signatures: set[str] = set()
    semantic_index: Dict[str, int] = {}

    for index, raw in enumerate(blocks):
        if not isinstance(raw, dict):
            continue
        block = dict(raw)
        block_type = _scene_block_type(block)
        if block_type == "graph_data":
            continue
        renderer = _scene_block_renderer(block)
        block["type"] = block_type
        block["artifact_type"] = str(block.get("artifact_type") or block_type)
        block["renderer"] = renderer
        block["viewer"] = str(block.get("viewer") or renderer)
        block_id = str(block.get("block_id") or block.get("id") or f"block_{index + 1}").strip()
        block["block_id"] = block_id
        block["scene_id"] = scene.scene_id
        block["turn_id"] = scene.turn_id
        block["flow_id"] = scene.flow_id
        block["topic_group"] = str(block.get("topic_group") or scene.topic_group or blueprint.get("topic_group") or "").strip()
        block["continuation"] = bool(block.get("continuation", scene.continuation))
        block["render_id"] = str(block.get("render_id") or f"render_{_scene_hash({'scene': scene.scene_id, 'block': block_id, 'renderer': renderer})}")
        block["sequence_index"] = order_pos.get(block_id, index)
        block["scene_contract"] = True
        block["signal_version"] = UNIFIED_RENDER_SIGNAL_VERSION
        related = [str(x).strip() for x in _scene_list(block.get("related_block_ids")) if str(x).strip()]
        block["related_block_ids"] = list(dict.fromkeys(related))
        signature = _scene_hash({
            "type": block_type,
            "renderer": renderer,
            "content": _scene_text(block),
            "payload": block.get("payload", {}),
        })
        semantic_key = _canonical_visual_dedupe_key(block)
        if semantic_key and semantic_key in semantic_index:
            previous_index = semantic_index[semantic_key]
            normalized[previous_index] = _prefer_canonical_visual_block(normalized[previous_index], block)
            continue
        if block_id in seen_ids or signature in seen_signatures:
            continue
        seen_ids.add(block_id)
        seen_signatures.add(signature)
        if semantic_key:
            semantic_index[semantic_key] = len(normalized)
        normalized.append(block)

    normalized.sort(key=lambda b: int(b.get("sequence_index", 0)))
    for idx, block in enumerate(normalized):
        block["sequence_index"] = idx
    return normalized


def _canonical_scene_relations(scene: MachineScene, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    blueprint = dict(scene.scene_blueprint or {})
    relations: List[Dict[str, Any]] = []
    for raw in _scene_list(blueprint.get("relations")):
        if not isinstance(raw, dict):
            continue
        source = str(raw.get("from") or raw.get("source") or "").strip()
        target = str(raw.get("to") or raw.get("target") or "").strip()
        if not source or not target:
            continue
        relations.append({
            "from": source,
            "to": target,
            "relation": str(raw.get("relation") or raw.get("type") or "related").strip(),
        })
    if not relations:
        for block in blocks:
            source = str(block.get("block_id") or "").strip()
            for target in block.get("related_block_ids") or []:
                if source and str(target).strip():
                    relations.append({"from": source, "to": str(target).strip(), "relation": "related"})
    unique: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for item in relations:
        key = f"{item['from']}|{item['relation']}|{item['to']}"
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def build_scene_signal(contract: SceneContract) -> Dict[str, Any]:
    """Create the ONE Web signal for the whole scene."""
    return {
        "signal_type": CANONICAL_SCENE_SIGNAL_TYPE,
        "signal_version": UNIFIED_RENDER_SIGNAL_VERSION,
        "scene_id": contract.scene_id,
        "turn_id": contract.turn_id,
        "flow_id": contract.flow_id,
        "topic_group": contract.topic_group,
        "continuation": contract.continuation,
        "single_response": True,
        "single_signal": True,
        "answer_render_policy": ANSWER_RENDER_POLICY,
        "answer": str(contract.metadata.get("answer") or ""),
        "order": list(contract.order),
        "relations": deepcopy(contract.relations),
        "blocks": deepcopy(contract.render_blocks),
        "presentation": deepcopy((contract.metadata.get("presentation") or {})),
    }


def build_machine_scene(response: MachineResponse) -> MachineScene:
    """Canonical MachineResponse -> one MachineScene transformation."""
    scene = create_default_machine_scene()
    scene.fiber = response.fiber
    metadata = dict(getattr(response, "metadata", {}) or {})
    source_scene = dict(getattr(response, "scene", {}) or {})
    blueprint = dict(
        getattr(response, "scene_blueprint", {})
        or source_scene.get("scene_blueprint")
        or source_scene.get("blueprint")
        or {}
    )

    scene.scene_id = str(getattr(response, "scene_id", "") or source_scene.get("scene_id") or metadata.get("scene_id") or scene.scene_id)
    scene.turn_id = str(getattr(response, "turn_id", "") or source_scene.get("turn_id") or metadata.get("turn_id") or "")
    scene.flow_id = str(getattr(response, "flow_id", "") or source_scene.get("flow_id") or metadata.get("flow_id") or "")
    scene.topic_group = str(getattr(response, "topic_group", "") or blueprint.get("topic_group") or metadata.get("topic_group") or "")
    scene.continuation = bool(getattr(response, "continuation", False) or blueprint.get("continuation", False) or metadata.get("continuation", False))
    scene.active_scene = str(source_scene.get("active_scene") or metadata.get("active_scene") or "")
    scene.scene_blueprint = blueprint

    scene.metadata = {
        "confidence": getattr(response, "confidence", 0.0),
        "diagnostics": dict(getattr(response, "diagnostics", {}) or {}),
        "quality": dict(getattr(response, "quality", {}) or {}),
        "routing_decision": dict(getattr(response, "routing_decision", {}) or {}),
        "machine_only": bool(metadata.get("machine_only", False)),
        "human_visible": metadata.get("human_visible", True),
        "answer": str(getattr(response, "answer", "") or ""),
        "content": str(getattr(response, "content", "") or ""),
        "summary": str(getattr(response, "summary", "") or ""),
        "contributions": dict(getattr(response, "contributions", {}) or {}),
        "executor_hints": dict(getattr(response, "executor_hints", {}) or {}),
        "scene_id": scene.scene_id,
        "turn_id": scene.turn_id,
        "flow_id": scene.flow_id,
        "topic_group": scene.topic_group,
        "continuation": scene.continuation,
        "scene_blueprint": deepcopy(blueprint),
    }

    scene.blocks = list(getattr(response, "render_blocks", []) or [])
    scene.relations = list(getattr(response, "scene_relations", []) or blueprint.get("relations", []) or [])
    scene.order = list(getattr(response, "scene_order", []) or blueprint.get("order", []) or [])
    setattr(scene, "artifacts", list(getattr(response, "artifacts", []) or []))
    setattr(scene, "answer", getattr(response, "answer", ""))
    setattr(scene, "content", getattr(response, "content", ""))
    setattr(scene, "summary", getattr(response, "summary", ""))

    if hasattr(response, "conversation_space"):
        setattr(scene, "conversation_space", getattr(response, "conversation_space"))
    return scene

def build_scene_contract(scene: MachineScene) -> SceneContract:
    """Finalize the one canonical SceneContract and one Web scene signal."""
    contract = scene.contract if isinstance(scene.contract, SceneContract) else create_default_scene_contract()
    contract.scene_version = CANONICAL_SCENE_VERSION
    contract.scene_id = scene.scene_id
    contract.turn_id = scene.turn_id
    contract.flow_id = scene.flow_id
    contract.topic_group = scene.topic_group
    contract.continuation = scene.continuation
    contract.active_scene = scene.active_scene
    contract.scene_blueprint = deepcopy(scene.scene_blueprint or {})

    canonical_blocks = _canonical_scene_blocks(scene)
    relations = _canonical_scene_relations(scene, canonical_blocks)
    order = [str(block.get("block_id") or "").strip() for block in canonical_blocks if str(block.get("block_id") or "").strip()]

    contract.blocks = canonical_blocks
    contract.render_blocks = list(canonical_blocks)
    contract.relations = relations
    contract.order = order
    contract.metadata = dict(scene.metadata or {})
    contract.metadata.update({
        "scene_id": scene.scene_id,
        "turn_id": scene.turn_id,
        "flow_id": scene.flow_id,
        "topic_group": scene.topic_group,
        "continuation": scene.continuation,
        "artifact_count": len(getattr(scene, "artifacts", []) or []),
        "transport_stage": "artifact_contract_scene_v3",
        "canonical_scene_contract": True,
        "single_response": True,
        "single_signal": True,
        "answer_render_policy": ANSWER_RENDER_POLICY,
        "machine_only": bool(contract.metadata.get("machine_only", False) or _scene_is_internal_only(scene)),
        "human_visible": bool(contract.metadata.get("human_visible", not contract.metadata.get("machine_only", False))),
    })

    answer = _scene_text(scene)
    if contract.metadata.get("machine_only"):
        contract.metadata["answer"] = ""
        contract.metadata["content"] = ""
        contract.metadata["summary"] = ""
    else:
        contract.metadata["answer"] = answer
        contract.metadata["content"] = answer
        contract.metadata["summary"] = answer

    # Presentation is generated once for the canonical scene, never once per
    # renderer. This keeps all renderers in one visual stream.
    try:
        from blocks.presentation_formatter import build_presentation_contract, attach_presentation_signals
        presentation = build_presentation_contract(
            scene_id=scene.scene_id,
            turn_id=scene.turn_id,
            flow_id=scene.flow_id,
            topic_group=scene.topic_group,
            continuation=scene.continuation,
            layout_mode="flow",
        )
        contract.render_blocks = attach_presentation_signals(contract.render_blocks, scene_presentation=presentation)
        contract.blocks = list(contract.render_blocks)
    except Exception:
        presentation = {
            "version": "presentation_unavailable",
            "engine": "McDowell",
            "math_engine": "KaTeX",
            "single_response": True,
            "single_signal": True,
            "layout": {"mode": "flow", "container": "adaptive_full_width", "frames": False, "cards": False},
        }
    contract.metadata["presentation"] = presentation
    contract.metadata["renderer_instances"] = list(dict.fromkeys(
        str(block.get("renderer") or "MessageTextBlock") for block in contract.render_blocks if isinstance(block, dict)
    ))
    contract.space_continuity = {
        **dict(contract.space_continuity or {}),
        "active_scene": contract.active_scene,
        "scene_id": contract.scene_id,
        "turn_id": contract.turn_id,
        "flow_id": contract.flow_id,
        "relations": deepcopy(contract.relations),
        "order": list(contract.order),
    }
    contract.signal = build_scene_signal(contract)
    contract.metadata["scene_signal"] = deepcopy(contract.signal)

    scene.contract = contract
    scene.blocks = list(contract.render_blocks)
    scene.relations = list(contract.relations)
    scene.order = list(contract.order)
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
            and renderer in {"MessageTextBlock", "GalleryBlock", "SvgBlock", "ArithmeticDiagram"}
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
