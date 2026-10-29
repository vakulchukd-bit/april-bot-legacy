"""Premium copy of the April C-Artifact contract. The public SceneContract schema remains identical to Free.

This module is intentionally parallel and is not wired into bot.ru until the Premium route is enabled.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from copy import deepcopy
import uuid
import time
import hashlib
import re

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
    """Canonicalize supplied structure and make concrete diagrams readable on mobile."""
    payload = dict(payload or {})
    nodes = payload.get("nodes") or payload.get("components") or payload.get("vertices") or []
    edges = payload.get("edges") or []
    connections = payload.get("connections") or []
    relations = payload.get("relations") or []

    if not isinstance(nodes, list):
        nodes = list(nodes.values()) if isinstance(nodes, dict) else [nodes]
    if not isinstance(edges, list):
        edges = list(edges.values()) if isinstance(edges, dict) else [edges]
    if not isinstance(connections, list):
        connections = list(connections.values()) if isinstance(connections, dict) else [connections]
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
    for edge in edges + connections + relations:
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
    payload["components"] = payload.get("components") or deepcopy(canonical_nodes)
    payload["layout"] = payload.get("layout") or {"direction": "TB", "rankdir": "TB", "responsive": True}
    payload["diagram_schema"] = "april.diagram.canonical.v2"
    existing_presentation = dict(payload.get("presentation") or {})
    concrete_renderer = (
        payload.get("renderer")
        or existing_presentation.get("renderer")
        or "DiagramRenderer"
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
    # Use the existing C_DIAGRAM_ROOM as the single SVG builder. This is a local
    # import to avoid a module import cycle (C_DIAGRAM_ROOM uses this contract).
    try:
        from blocks.C_DIAGRAM_ROOM import ensure_readable_diagram_payload
        has_svg = any(str(payload.get(key) or "").strip() for key in ("svg", "svg_payload", "drawing"))
        # Node-only diagrams are valid when the source defines an explicit visual
        # collection (for example, a Mermaid subgraph containing lab equipment).
        # Do not invent relationships merely to satisfy an edge-only validator.
        has_node_composition = len(canonical_nodes) >= 2 and (
            str(payload.get("format") or "").strip().lower() == "mermaid"
            or bool(payload.get("groups") or payload.get("subgraphs"))
            or bool(payload.get("representation") or payload.get("layout"))
        )
        if has_node_composition or (canonical_nodes and canonical_edges) or has_svg:
            normalized = ensure_readable_diagram_payload(
                payload,
                title=str(payload.get("title") or payload.get("description") or "Схема"),
            )
            if isinstance(normalized, dict) and normalized:
                payload.update(normalized)
                if payload.get("svg") or payload.get("svg_payload"):
                    if str(payload.get("renderer") or concrete_renderer) in {"", "DiagramRenderer", "diagram"}:
                        payload["renderer"] = "SvgBlock"
                    presentation = dict(payload.get("presentation") or {})
                    presentation["renderer"] = payload.get("renderer") or presentation.get("renderer") or "SvgBlock"
                    presentation["responsive"] = True
                    payload["presentation"] = presentation
    except Exception:
        # A rendering repair failure must not drop or mutate the original source.
        pass
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
WEB_RENDERER_REGISTRY_VERSION = "3.4"

# Exact renderer contract mirrored from the actual April Web RenderMessage
# registry. This describes the destination component; it never performs routing.
WEB_RENDERER_REGISTRY = {
    "text": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["content", "text", "answer"]},
    "markdown": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["content", "text", "markdown"]},
    "formula": {"renderer": "FormulaRenderer", "viewer": "FormulaRenderer", "fallback_renderer": "", "payload_keys": ["formula", "formulas", "latex", "latex_formulas", "equation", "expression", "math", "markdown", "content"], "mode": "force_math"},
    "graph": {"renderer": "GraphBlock", "viewer": "GraphBlock", "fallback_renderer": "", "payload_keys": ["series", "datasets", "traces", "curves", "points", "data_points", "x", "y", "x_values", "y_values", "categories", "labels", "data_table", "matrix", "x_axis", "y_axis", "z_axis", "axes", "representation", "chart_type", "visualization", "graph_type", "plot_type", "fn", "function", "expression", "equation", "formula", "x_domain", "y_domain", "z_domain", "x_range", "y_range", "z_range", "domain", "surface", "surface_grid", "surface_function", "z_function", "z_expression", "grid_resolution", "spheres", "objects_3d", "objects", "shapes", "meshes", "geometry", "scene", "dimensions", "three_d", "show_curved_grid", "curved_grid", "surface_mode", "wave_effect", "wave", "waves", "wave_type", "wave_function", "wave_amplitude", "wave_frequency", "wave_phase", "color_scale", "color_map", "colormap", "colour_scale", "colour_map", "temperature_field", "thermal_field", "heat_field", "field_type", "visualization_mode", "surface_style", "show_zero_plane", "zero_plane", "color_domain", "axis_labels", "bodies", "celestial_bodies", "planets", "satellites", "moons", "comets", "primitives", "orbits", "orbit_paths", "orbital_motion", "trajectories", "paths", "lines", "curves", "vectors", "gravity_vectors", "field_vectors", "field_lines", "arrows", "forces", "velocity_vectors", "normals", "rings", "labels", "annotations", "materials", "animation", "time", "duration", "keyframes"]},
    "knowledge_graph": {"renderer": "GraphBlock", "viewer": "GraphBlock", "fallback_renderer": "", "payload_keys": ["nodes", "edges", "relations", "series", "points", "labels", "title", "description"]},
    "relation_graph": {"renderer": "GraphBlock", "viewer": "GraphBlock", "fallback_renderer": "", "payload_keys": ["nodes", "edges", "relations", "series", "points", "labels", "title", "description"]},
    "relations": {"renderer": "GraphBlock", "viewer": "GraphBlock", "fallback_renderer": "", "payload_keys": ["nodes", "edges", "relations", "title", "description"]},
    "table": {"renderer": "TableBlock", "viewer": "TableBlock", "fallback_renderer": "", "payload_keys": ["rows", "columns", "headers", "data", "values", "items", "caption", "column_roles", "cell_roles", "wrap", "download"]},
    "diagram": {"renderer": "DiagramRenderer", "viewer": "DiagramRenderer", "fallback_renderer": "", "payload_keys": ["svg", "svg_payload", "drawing", "nodes", "edges", "components", "vertices", "connections", "relations", "elements", "shapes", "points", "source", "mermaid", "format", "layout", "direction"], "specialized_renderers": ["SvgBlock", "ArithmeticDiagram"]},
    "image": {"renderer": "GalleryBlock", "viewer": "GalleryBlock", "fallback_renderer": "", "payload_keys": ["images", "items", "gallery", "sources", "src", "url", "image", "asset_url", "image_asset_url", "image_data_uri", "image_base64", "base64", "mime_type", "width", "height", "alt", "caption"]},
    "gallery": {"renderer": "GalleryBlock", "viewer": "GalleryBlock", "fallback_renderer": "", "payload_keys": ["images", "items", "gallery", "sources", "src", "url", "asset_url", "image_asset_url", "image_url", "image", "image_data_uri", "alt", "title", "caption", "source_url"]},
    "scene": {"renderer": "DiagramRenderer", "viewer": "DiagramRenderer", "fallback_renderer": "", "payload_keys": ["elements", "svg", "images", "objects", "nodes", "edges", "title", "description"]},
    "layout": {"renderer": "DiagramRenderer", "viewer": "DiagramRenderer", "fallback_renderer": "", "payload_keys": ["elements", "nodes", "edges", "svg", "title", "description", "direction"]},
    "visual": {"renderer": "DiagramRenderer", "viewer": "DiagramRenderer", "fallback_renderer": "", "payload_keys": ["elements", "nodes", "edges", "svg", "images", "title", "description"]},
    "renderer_scene": {"renderer": "DiagramRenderer", "viewer": "DiagramRenderer", "fallback_renderer": "", "payload_keys": ["elements", "nodes", "edges", "svg", "images", "title", "description"]},
    "visual_context": {"renderer": "DiagramRenderer", "viewer": "DiagramRenderer", "fallback_renderer": "", "payload_keys": ["images", "elements", "svg", "context", "title", "description"]},
    "code": {"renderer": "CodeBlock", "viewer": "CodeBlock", "fallback_renderer": "", "payload_keys": ["code", "content", "language", "filename"]},
    "link": {"renderer": "LinkCard", "viewer": "LinkCard", "fallback_renderer": "", "payload_keys": ["url", "href", "title", "description", "links", "markdown", "preview", "domain", "icon", "preview_image"]},
    "file": {"renderer": "LinkCard", "viewer": "LinkCard", "fallback_renderer": "", "payload_keys": ["url", "href", "path", "name"]},
    "audio": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["url", "src", "path", "content"]},
    "video": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["url", "src", "path", "content"]},
    "action": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["action", "target", "parameters", "content"]},
    "memory": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["content", "summary", "memory"]},
    # C rooms may emit function/domain artifacts. They remain in the same SceneContract
    # and use the canonical text renderer when they do not request a specialized visual.
    "function": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["function", "expression", "description", "analysis", "summary", "content", "text"]},
    # Domain rooms travel inside the same SceneContract. They use the normal
    # text renderer unless they emit a registered structured artifact type.
    "biology": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["description", "analysis", "summary", "content", "text"]},
    "it": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["description", "analysis", "summary", "content", "text", "code"]},
    "literature": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["description", "analysis", "summary", "content", "text"]},
    "mathematics": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["description", "analysis", "summary", "content", "text", "formula", "expression"]},
    "news": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["description", "summary", "content", "text", "sources", "links"]},
    "politics": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["description", "summary", "content", "text", "sources", "links"]},
    "social": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["description", "analysis", "summary", "content", "text"]},
    "trigonometry": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["description", "analysis", "summary", "content", "text", "formula", "expression"]},
    "utc": {"renderer": "MessageTextBlock", "viewer": "MessageTextBlock", "fallback_renderer": "", "payload_keys": ["description", "summary", "content", "text", "datetime", "timezone"]},
}

ARTIFACT_BLOCK_MAP = {kind: spec["renderer"] for kind, spec in WEB_RENDERER_REGISTRY.items()}
ARTIFACT_BLOCK_MAP["function"] = "MessageTextBlock"

# Concrete renderers that are allowed to cross the artifact/Fiber boundary.
SUPPORTED_RENDERERS = {
    "MessageTextBlock", "GraphBlock", "TableBlock", "GalleryBlock",
    "CodeBlock", "LinkCard", "FunctionBlock", "FormulaBlock", "FormulaRenderer",
    "DiagramRenderer",
    "SvgBlock", "ArithmeticDiagram",
}

# Data-driven renderer aliases. They refine a produced representation; they do
# not perform lexical routing.
ARTIFACT_RENDERER_ALIASES = {
    "text": "MessageTextBlock",
    "markdown": "MessageTextBlock",
    "message": "MessageTextBlock",
    "message_text": "MessageTextBlock",
    # These are implementation-level diagram names. They are normalized to the
    # actual Web renderer while the payload (including SVG/geometry) is untouched.
    "diagram": "DiagramRenderer",
    "diagramblock": "DiagramRenderer",
    "schematic": "DiagramRenderer",
    "svgblock": "DiagramRenderer",
    "svg": "DiagramRenderer",
    "arithmeticdiagram": "DiagramRenderer",
    "arithmetic_diagram": "DiagramRenderer",
    "gallery": "GalleryBlock",
    "image": "GalleryBlock",
    "figure": "GalleryBlock",
    "geometry": "DiagramRenderer",
    "geometric_figure": "DiagramRenderer",
}

# =====================================================
# CANONICAL APRIL ROOM REGISTRY
# =====================================================
# Registration lives here as metadata only.
#
# Important:
#   * This registry DOES NOT import room modules.
#   * This registry DOES NOT create alternate routes.
#   * Executor remains responsible for selecting/activating rooms.
#   * Room implementations remain in their existing blocks/*.py files.
#   * C_ARTIFACT_CONTRACT is the single source of truth for room identity,
#     capabilities and artifact expectations.
#
# Infrastructure components such as bot.ru, Exkrutor and the 12h memory
# subsystem are NOT rooms and therefore are intentionally not registered here.

ROOM_REGISTRY_VERSION = "1.0"

@dataclass(frozen=True)
class RoomRegistration:
    room_id: str
    module: str
    class_name: str = ""
    artifact_type: str = ""
    room_type: str = ""
    role: str = ""
    capabilities: tuple[str, ...] = ()
    enabled: bool = True
    is_engine: bool = False


ROOM_REGISTRY: Dict[str, RoomRegistration] = {
    "C_APRIL_IMAGES_GENERATOR": RoomRegistration(
        room_id="APRIL_IMAGES_GENERATION",
        module="blocks.C_APRIL_IMAGES_GENERATOR",
        class_name="AprilImagesGenerator",
        artifact_type="image",
        room_type="generator",
        role="canonical image generation engine",
        capabilities=("image_generation", "png", "gallery"),
        is_engine=True,
    ),
    "C_BIOLOGY_ROOM": RoomRegistration(
        room_id="biology",
        module="blocks.C_BIOLOGY_ROOM",
        class_name="BiologyRoom",
        room_type="knowledge",
        role="biology knowledge and research",
        capabilities=("biology", "research", "knowledge"),
    ),
    "C_DIAGRAM_ROOM": RoomRegistration(
        room_id="C_DIAGRAM_ROOM",
        module="blocks.C_DIAGRAM_ROOM",
        class_name="DiagramRoom",
        artifact_type="diagram",
        room_type="diagram_renderer",
        role="canonical diagram structure",
        capabilities=("diagram", "svg", "geometry"),
    ),
    "C_FORMULA_ROOM": RoomRegistration(
        room_id="FORMULA_ROOM",
        module="blocks.C_FORMULA_ROOM",
        class_name="FormulaRoom",
        artifact_type="formula",
        room_type="visual",
        role="formula rendering",
        capabilities=("formula", "latex", "math"),
    ),
    "C_FUNCTION_ROOM": RoomRegistration(
        room_id="FUNCTION_ROOM",
        module="blocks.C_FUNCTION_ROOM",
        class_name="FunctionRoom",
        artifact_type="function",
        room_type="visual",
        role="function representation",
        capabilities=("function", "mathematical_function"),
    ),
    "C_GALLERY_ROOM": RoomRegistration(
        room_id="GALLERY_ROOM",
        module="blocks.C_GALLERY_ROOM",
        class_name="GalleryRoom",
        artifact_type="gallery",
        room_type="visual",
        role="gallery composition",
        capabilities=("gallery", "image_collection"),
    ),
    "C_GRAPH_ROOM": RoomRegistration(
        room_id="C_GRAPH_ROOM",
        module="blocks.C_GRAPH_ROOM",
        class_name="GraphRoom",
        artifact_type="graph",
        room_type="graph_renderer",
        role="canonical graph structure",
        capabilities=("graph", "series", "data_visualization"),
    ),
    "C_IT_ROOM": RoomRegistration(
        room_id="it",
        module="blocks.C_IT_ROOM",
        class_name="ITRoom",
        room_type="knowledge",
        role="software and code analysis",
        capabilities=("software", "code", "git", "analysis", "site_navigation", "april_site_help", "user_guidance", "interface_help", "april_site_navigation", "user_interface_help", "account_guidance"),
    ),
    "C_LINK_ROOM": RoomRegistration(
        room_id="LINK_ROOM",
        module="blocks.C_LINK_ROOM",
        class_name="LinkRoom",
        artifact_type="link",
        room_type="visual",
        role="link/card representation",
        capabilities=("link", "url", "preview"),
    ),
    "C_LITERATURE_ROOM": RoomRegistration(
        room_id="LITERATURE_ROOM",
        module="blocks.C_LITERATURE_ROOM",
        class_name="LiteratureRoom",
        artifact_type="function",
        room_type="knowledge",
        role="literature knowledge and analysis",
        capabilities=("literature", "authors", "literary_analysis"),
    ),
    "C_MATHEMATICS_ROOM": RoomRegistration(
        room_id="MATHEMATICS_ROOM",
        module="blocks.C_MATHEMATICS_ROOM",
        class_name="MathematicsRoom",
        artifact_type="function",
        room_type="science",
        role="mathematical reasoning",
        capabilities=("mathematics", "calculation", "reasoning"),
    ),
    "C_NEWS_ROOM": RoomRegistration(
        room_id="NEWS_ROOM",
        module="blocks.C_NEWS_ROOM",
        class_name="NewsRoom",
        artifact_type="function",
        room_type="professional",
        role="news domain processing",
        capabilities=("news", "current_events"),
    ),
    "C_POLITICS_ROOM": RoomRegistration(
        room_id="POLITICS_ROOM",
        module="blocks.C_POLITICS_ROOM",
        class_name="PoliticsRoom",
        artifact_type="function",
        room_type="professional",
        role="politics domain processing",
        capabilities=("politics", "current_events"),
    ),
    "C_SOCIAL_ROOM": RoomRegistration(
        room_id="SOCIAL_ROOM",
        module="blocks.C_SOCIAL_ROOM",
        class_name="SocialRoom",
        artifact_type="function",
        room_type="professional",
        role="social domain processing",
        capabilities=("social", "communication"),
    ),
    "C_TABLE_ROOM": RoomRegistration(
        room_id="C_TABLE_ROOM",
        module="blocks.C_TABLE_ROOM",
        class_name="TableRoom",
        artifact_type="table",
        room_type="table_renderer",
        role="canonical table structure",
        capabilities=("table", "structured_data", "tabular"),
    ),
    "C_TRIGONOMETRY_ROOM": RoomRegistration(
        room_id="TRIGONOMETRY_ROOM",
        module="blocks.C_TRIGONOMETRY_ROOM",
        class_name="TrigonometryRoom",
        artifact_type="function",
        room_type="science",
        role="trigonometry reasoning",
        capabilities=("trigonometry", "calculation", "geometry"),
    ),
    "C_UTC_ROOM": RoomRegistration(
        room_id="UTC_ROOM",
        module="blocks.C_UTC_ROOM",
        class_name="UTCRoom",
        artifact_type="function",
        room_type="service",
        role="UTC/time service",
        capabilities=("utc", "time", "datetime"),
    ),
    "C_WEB_ROOM": RoomRegistration(
        room_id="WEB_ROOM",
        module="blocks.C_WEB_ROOM",
        class_name="WebRoom",
        artifact_type="link",
        room_type="service",
        role="web service/artifact representation",
        capabilities=("web", "links", "retrieval"),
    ),
}

# Compatibility map for existing Factory code.  It contains module paths only;
# it does not import or execute rooms and does not create a second routing path.
FACTORY_ROOM_MAP: Dict[str, str] = {
    key: registration.module
    for key, registration in ROOM_REGISTRY.items()
}


def register_room(registration: RoomRegistration) -> RoomRegistration:
    """Register one room in the canonical C-ARTIFACT registry."""
    if not isinstance(registration, RoomRegistration):
        raise TypeError("registration must be RoomRegistration")
    key = registration.module.rsplit(".", 1)[-1]
    ROOM_REGISTRY[key] = registration
    FACTORY_ROOM_MAP[key] = registration.module
    return registration


def get_room_registration(room_key: str) -> Optional[RoomRegistration]:
    """Resolve a room registration without importing or executing the room."""
    key = str(room_key or "").strip()
    if not key:
        return None
    return ROOM_REGISTRY.get(key)


def list_registered_rooms(*, include_engines: bool = True) -> List[RoomRegistration]:
    """Return the canonical room list in stable registration order."""
    values = list(ROOM_REGISTRY.values())
    if include_engines:
        return values
    return [item for item in values if not item.is_engine]


def is_room_registered(room_key: str) -> bool:
    return get_room_registration(room_key) is not None



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


def build_room_route_contract(
    request: Any,
    *,
    origin: str = "executor",
    destination: str = "rooms_registry",
    pipeline_stage: str = "artifact_route",
    context: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> UniversalArtifactContract:
    """Build the C-ARTIFACT transport envelope used before room execution.

    This is a routing envelope, not a human-visible artifact.  It carries the
    already-resolved semantic request, dialogue continuity and provider result
    into Room Register without asking Executor to call a concrete room/engine.
    """
    contract = UniversalArtifactContract()

    transport = contract.transport
    # TransportContract is intentionally lightweight in this project.  These
    # attributes are attached dynamically so existing consumers remain compatible.
    transport.origin = str(origin or "executor")
    transport.destination = str(destination or "rooms_registry")
    transport.pipeline_stage = str(pipeline_stage or "artifact_route")
    transport.route_authority = "INTERPRETATION"

    intent = deepcopy(getattr(request, "intent", {}) or {})
    conversation = deepcopy(getattr(request, "conversation", {}) or {})
    memory = deepcopy(getattr(request, "memory", {}) or {})
    visual_context = deepcopy(getattr(request, "visual_context", {}) or {})
    routing = deepcopy(getattr(request, "routing", {}) or {})
    constraints = deepcopy(getattr(request, "constraints", {}) or {})
    requested_outputs = list(getattr(request, "requested_outputs", []) or [])
    required_artifacts = list(getattr(request, "required_artifacts", []) or [])

    route_context = deepcopy(context or {})
    route_context.setdefault("current_user_request", conversation.get("current_request", ""))
    route_context.setdefault("resolved_request", conversation.get("resolved_request", ""))
    route_context.setdefault("semantic_request", intent.get("semantic_request", ""))
    route_context.setdefault("conversation", conversation)
    route_context.setdefault("memory", memory)
    route_context.setdefault("visual_context", visual_context)

    contract.payload.intent = intent
    contract.payload.context = route_context
    contract.payload.knowledge = memory
    contract.payload.scene = deepcopy(conversation.get("live_scene") or {})
    contract.payload.executor_notes = {
        "request_id": str(getattr(request, "request_id", "") or ""),
        "goal": str(getattr(request, "goal", "") or ""),
        "requested_outputs": requested_outputs,
        "required_artifacts": required_artifacts,
        "routing": routing,
        "constraints": constraints,
        "current_user_request": conversation.get("current_request", ""),
        "resolved_request": conversation.get("resolved_request", ""),
        "semantic_authority": "INTERPRETATION",
        "room_registry": "rooms_registry",
    }
    contract.metadata = {
        "contract_type": "ROOM_ROUTE_ENVELOPE",
        "route_authority": "INTERPRETATION",
        "source": str(origin or "executor"),
        "destination": str(destination or "rooms_registry"),
        "pipeline_stage": str(pipeline_stage or "artifact_route"),
        **deepcopy(metadata or {}),
    }

    return contract


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
    artifact_payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    if artifact_type == "diagram" and str(artifact_payload.get("svg") or artifact_payload.get("svg_payload") or "").strip() and renderer in {"", "DiagramRenderer", "MessageTextBlock", "TextBlock", "MarkdownBlock"}:
        renderer = "SvgBlock"

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
        # `signal` keeps the compact renderer metadata expected by existing Web
        # blocks. `render_signal` is the complete canonical signal envelope,
        # including the lossless payload, and follows the artifact to Web.
        "signal": dict(signal.get("signal") or {}),
        "render_signal": dict(signal),
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


def create_transport_contract(
    artifact_type: str,
    room_source: str,
    data: Dict[str, Any],
    user_id: str = "",
    subscription: str = "Free",
) -> UniversalArtifactContract:
    """Canonical transport factory used by artifact callers.

    The function accepts a plain artifact payload, converts it into a
    BaseArtifact, and materializes the single Fiber transport envelope
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
    user_id: str = ""
    conversation_id: str = ""
    dialogue_sequence_id: str = ""
    sequence_turn_index: int = 0
    active_task: Dict[str, Any] = field(default_factory=dict)
    dialogue_state: Dict[str, Any] = field(default_factory=dict)
    dialogue_development: Dict[str, Any] = field(default_factory=dict)
    result_event: Dict[str, Any] = field(default_factory=dict)
    open_loops: List[Dict[str, Any]] = field(default_factory=list)
    pending_obligations: List[Dict[str, Any]] = field(default_factory=list)
    authenticated_scope: Dict[str, Any] = field(default_factory=dict)
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
    """Return the registered RenderMessage component and its full payload contract."""
    key = str(payload_type or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "chart": "graph", "plot": "graph", "graph_data": "graph",
        "3d_scene": "graph", "scene3d": "graph", "scene_3d": "graph", "3d_graph": "graph", "graph3d": "graph", "graph_3d": "graph",
        "plot3d": "graph", "plot_3d": "graph", "scatter3d": "graph", "scatter_3d": "graph", "surface3d": "graph", "surface_3d": "graph",
        "3d_surface": "graph", "surface_plot": "graph", "surface_graph": "graph", "mesh3d": "graph", "mesh_3d": "graph", "wireframe": "graph",
        "table_data": "table", "generated_image": "image", "image_artifact": "image",
        "image_data": "image", "figure": "image", "math": "formula", "latex": "formula",
        "svg": "diagram", "svgblock": "diagram", "schematic": "diagram",
        "arithmeticdiagram": "diagram", "arithmetic_diagram": "diagram",
        "message": "text", "message_text": "text", "hyperlink": "link", "links": "link", "link_list": "link", "linklist": "link", "source_links": "link", "file_card": "file",
        "image_gallery": "gallery", "gallery_block": "gallery", "sources_gallery": "gallery",
        "experimental_diagram": "diagram", "mermaid": "diagram",
        "scene": "diagram", "layout": "diagram", "visual": "diagram", "renderer_scene": "diagram",
        "generated_image": "image", "image_data": "image", "image_artifact": "image", "figure": "image",
    }
    canonical = aliases.get(key, key)
    registration = WEB_RENDERER_REGISTRY.get(canonical) or WEB_RENDERER_REGISTRY["text"]
    result = dict(registration)
    result.update({
        "representation": canonical,
        "requested_representation": key,
        "web_registry_version": WEB_RENDERER_REGISTRY_VERSION,
        "payload_keys": list(registration.get("payload_keys") or []),
    })
    return result


@dataclass
class MachineScene:
    fiber: FiberCoreContract = field(default_factory=FiberCoreContract)
    scene_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scene_version: str = "3.1"
    active_scene: str = ""
    turn_id: str = ""
    flow_id: str = ""
    topic_group: str = ""
    continuation: bool = False
    user_id: str = ""
    conversation_id: str = ""
    dialogue_sequence_id: str = ""
    sequence_turn_index: int = 0
    active_task: Dict[str, Any] = field(default_factory=dict)
    dialogue_state: Dict[str, Any] = field(default_factory=dict)
    dialogue_development: Dict[str, Any] = field(default_factory=dict)
    result_event: Dict[str, Any] = field(default_factory=dict)
    open_loops: List[Dict[str, Any]] = field(default_factory=list)
    pending_obligations: List[Dict[str, Any]] = field(default_factory=list)
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
    "prepare_render_blocks_for_room_dispatch",
    "SUPPORTED_RENDERERS",
    "WEB_RENDERER_REGISTRY",
    "WEB_RENDERER_REGISTRY_VERSION",
    "ARTIFACT_RENDERER_ALIASES",
    "UNIFIED_RENDER_SIGNAL_VERSION",
    "build_scene_contract",
    "build_scene_signal",
    "CANONICAL_SCENE_VERSION",
    "ANSWER_RENDER_POLICY",
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
    """Resolve the artifact type from the whole canonical signal envelope.

    Providers/rooms may carry the representation on the block, the artifact,
    or a render signal. Reading only the top-level `type` made otherwise valid
    Table/Code/Link/Diagram signals silently become text blocks.
    """
    if not isinstance(block, dict):
        return "text"

    candidates: List[Any] = [
        block.get("type"), block.get("artifact_type"), block.get("representation"),
        block.get("payload_type"),
    ]
    for key in ("presentation", "presentation_signal", "render_signal", "room_signal", "signal"):
        envelope = block.get(key)
        if isinstance(envelope, dict):
            candidates.extend((
                envelope.get("representation"), envelope.get("artifact_type"),
                envelope.get("payload_type"), envelope.get("type"), envelope.get("kind"),
            ))
            presentation = envelope.get("presentation")
            if isinstance(presentation, dict):
                candidates.extend((presentation.get("representation"), presentation.get("kind"), presentation.get("type")))
    artifact = block.get("artifact")
    if isinstance(artifact, dict):
        candidates.extend((artifact.get("type"), artifact.get("artifact_type"), artifact.get("representation")))
        metadata = artifact.get("metadata")
        if isinstance(metadata, dict):
            candidates.append(metadata.get("artifact_type"))
        payload = artifact.get("payload")
        if isinstance(payload, dict):
            candidates.extend((payload.get("artifact_type"), payload.get("representation"), payload.get("type"), payload.get("payload_type")))
    payload = block.get("payload")
    if isinstance(payload, dict):
        candidates.extend((payload.get("artifact_type"), payload.get("representation"), payload.get("payload_type"), payload.get("type")))

    aliases = {
        "chart": "graph", "plot": "graph", "graph_data": "graph",
        "table_data": "table", "math": "formula", "latex": "formula",
        "generated_image": "image", "image_artifact": "image", "image_data": "image", "figure": "image",
        "hyperlink": "link", "links": "link", "link_list": "link", "linklist": "link", "source_links": "link", "file_card": "file",
        "image_gallery": "gallery", "gallery_block": "gallery", "sources_gallery": "gallery",
        "svg": "diagram", "svgblock": "diagram", "schematic": "diagram",
        "arithmeticdiagram": "diagram", "arithmetic_diagram": "diagram", "experimental_diagram": "diagram",
        "mermaid": "diagram", "scene": "diagram", "layout": "diagram", "visual": "diagram", "renderer_scene": "diagram",
        "message": "text", "message_text": "text",
    }
    normalized = [
        aliases.get(str(item).strip().lower().replace("-", "_"), str(item).strip().lower().replace("-", "_"))
        for item in candidates if isinstance(item, str) and item.strip()
    ]
    generic = {"text", "markdown", "message", "message_text", "unknown"}
    # Prefer a known specialist signal when the outer block only says text.
    known_types = set(WEB_RENDERER_REGISTRY) | {"function", "biology", "it", "literature", "mathematics", "news", "politics", "social", "trigonometry", "utc"}
    for item in normalized:
        if item not in generic and item in known_types:
            return item
    return next((item for item in normalized if item not in generic), "text")


def _scene_block_renderer(block: Dict[str, Any]) -> str:
    block_type = _scene_block_type(block)
    renderer = str(block.get("renderer") or block.get("viewer") or "").strip()
    canonical = ARTIFACT_BLOCK_MAP.get(block_type, "MessageTextBlock")
    generic = {"", "MessageTextBlock", "TextBlock", "MarkdownBlock"}
    # A visual artifact has exactly one specialized viewer in the SceneContract.
    if block_type in {"formula", "graph", "table", "diagram", "image", "gallery", "link", "file"} and renderer in generic:
        return canonical
    if renderer:
        return renderer
    return canonical


def _canonical_visual_payload_for_dedupe(block: Dict[str, Any]) -> Any:
    """Keep only the actual visual payload; ignore transient renderer metadata."""
    block_type = _scene_block_type(block)
    payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
    for candidate in (
        block.get("artifact", {}).get("payload") if isinstance(block.get("artifact"), dict) else None,
        block.get("signal", {}).get("payload") if isinstance(block.get("signal"), dict) else None,
        block.get("presentation", {}).get("payload_contract", {}).get("payload")
        if isinstance(block.get("presentation"), dict)
        and isinstance(block.get("presentation", {}).get("payload_contract"), dict)
        else None,
    ):
        if isinstance(candidate, dict):
            merged = dict(candidate)
            merged.update({k: v for k, v in payload.items() if v not in (None, "", [], {})})
            payload = merged

    if block_type in {"image", "gallery"}:
        images = payload.get("images") or payload.get("gallery") or []
        if isinstance(images, list):
            sources = []
            for item in images:
                if isinstance(item, str):
                    src = item
                elif isinstance(item, dict):
                    src = item.get("src") or item.get("url") or item.get("image") or item.get("asset_url")
                else:
                    src = ""
                if src:
                    sources.append(str(src).strip())
            if sources:
                return {"sources": sorted(set(sources))}
        src = str(
            block.get("src") or block.get("url") or block.get("asset_url")
            or payload.get("src") or payload.get("url") or payload.get("image_url") or ""
        ).strip()
        return {"sources": [src]} if src else {"sources": []}

    if block_type == "formula":
        formulas = payload.get("formulas") or payload.get("latex_formulas")
        if isinstance(formulas, list):
            normalized = [str(item.get("latex") if isinstance(item, dict) else item).strip() for item in formulas if str(item.get("latex") if isinstance(item, dict) else item).strip()]
            if normalized:
                return {"formulas": normalized}
        return {
            "formula": str(
                payload.get("formula") or payload.get("latex") or payload.get("equation")
                or payload.get("expression") or block.get("content") or ""
            ).strip()
        }

    if block_type == "diagram":
        svg = str(payload.get("svg") or payload.get("drawing") or payload.get("svg_payload") or "").strip()
        if svg:
            return {"svg": " ".join(svg.split())}
        return {
            "nodes": payload.get("nodes") or [],
            "edges": payload.get("edges") or [],
            "elements": payload.get("elements") or payload.get("shapes") or [],
            "points": payload.get("points") or [],
        }

    if block_type in {"graph", "table"}:
        return payload

    if block_type in {"link", "file"}:
        links = payload.get("links")
        if isinstance(links, list) and links:
            urls = []
            for item in links:
                if isinstance(item, dict):
                    value = str(item.get("url") or item.get("href") or "").strip()
                    if value:
                        urls.append(value.split("#", 1)[0].rstrip("/").lower())
            if urls:
                return {"urls": sorted(set(urls))}
        url = str(block.get("url") or block.get("href") or payload.get("url") or payload.get("href") or "").strip()
        return {"url": url.split("#", 1)[0].rstrip("/").lower()} if url else payload

    return {}


def _canonical_visual_dedupe_key(block: Dict[str, Any]) -> str:
    block_type = _scene_block_type(block)
    if block_type == "graph_data":
        return f"internal:graph_data:{str(block.get('name') or '')}"
    if block_type in {"link", "file", "formula", "graph", "table", "diagram", "image", "gallery"}:
        return f"visual:{block_type}:{_scene_hash(_canonical_visual_payload_for_dedupe(block))}"
    return ""


def _prefer_canonical_visual_block(existing: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    rank = {
        "messagetextblock": 0,
        "textblock": 0,
        "markdownblock": 0,
        "formularenderer": 100,
        "formulablock": 100,
        "graphblock": 100,
        "tableblock": 100,
        "diagramrenderer": 100,
        "galleryblock": 100,
        "linkcard": 100,
    }
    existing_renderer = str(existing.get("renderer") or "").lower()
    candidate_renderer = str(candidate.get("renderer") or "").lower()
    if rank.get(candidate_renderer, 20) > rank.get(existing_renderer, 20):
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


def _render_requested_outputs(values: Any) -> set[str]:
    if not isinstance(values, (list, tuple, set)):
        return set()
    aliases = {
        "chart": "graph", "plot": "graph", "graph_data": "graph",
        "3d_scene": "graph", "scene3d": "graph", "scene_3d": "graph", "3d_graph": "graph", "graph3d": "graph", "graph_3d": "graph",
        "plot3d": "graph", "plot_3d": "graph", "scatter3d": "graph", "scatter_3d": "graph", "surface3d": "graph", "surface_3d": "graph",
        "3d_surface": "graph", "surface_plot": "graph", "surface_graph": "graph", "mesh3d": "graph", "mesh_3d": "graph", "wireframe": "graph",
        "table_data": "table",
        "math": "formula", "latex": "formula", "generated_image": "image", "image_artifact": "image",
        "image_gallery": "gallery", "gallery_block": "gallery", "sources_gallery": "gallery",
        "svg": "diagram", "schematic": "diagram", "experimental_diagram": "diagram",
        "mermaid": "diagram", "scene": "diagram", "layout": "diagram", "visual": "diagram", "renderer_scene": "diagram",
        "hyperlink": "link", "links": "link", "link_list": "link", "linklist": "link", "source_links": "link",
    }
    return {aliases.get(str(value or "").strip().lower().replace("-", "_"), str(value or "").strip().lower().replace("-", "_")) for value in values if str(value or "").strip()}


def _split_markdown_table_row(line: str) -> List[str]:
    text = str(line or "").strip()
    if not text.startswith("|") or "|" not in text[1:]:
        return []
    text = text.strip("|")
    cells: List[str] = []
    current: List[str] = []
    escaped = False
    for char in text:
        if char == "|" and not escaped:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        escaped = (char == "\\") and not escaped
        if char != "\\":
            escaped = False
    cells.append("".join(current).strip())
    return cells


def _markdown_table_payload(answer: str) -> Dict[str, Any]:
    """Read explicit same-turn Markdown table values without inventing cells."""
    lines = str(answer or "").replace("\r", "").split("\n")
    for index in range(len(lines) - 1):
        headers = _split_markdown_table_row(lines[index])
        sep = _split_markdown_table_row(lines[index + 1])
        if len(headers) < 2 or len(sep) != len(headers):
            continue
        if not all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in sep):
            continue
        rows: List[List[str]] = []
        for line in lines[index + 2:]:
            if not line.strip():
                if rows:
                    break
                continue
            cells = _split_markdown_table_row(line)
            if len(cells) != len(headers):
                break
            rows.append(cells)
        if rows:
            return {"columns": headers, "headers": headers, "rows": rows, "title": "", "source": "same_turn_markdown_table"}
    return {}


def _strip_first_markdown_table(answer: str, expected: Dict[str, Any]) -> str:
    """Remove a Markdown table from prose only after a TableBlock was created."""
    if not answer or not expected:
        return answer
    lines = str(answer).replace("\r", "").split("\n")
    expected_columns = list(expected.get("columns") or expected.get("headers") or [])
    expected_rows = [list(row) for row in (expected.get("rows") or []) if isinstance(row, (list, tuple))]
    for index in range(len(lines) - 1):
        headers = _split_markdown_table_row(lines[index])
        separator = _split_markdown_table_row(lines[index + 1])
        if headers != expected_columns or len(separator) != len(headers):
            continue
        if not all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in separator):
            continue
        table_rows: List[List[str]] = []
        end = index + 2
        while end < len(lines) and lines[end].strip():
            cells = _split_markdown_table_row(lines[end])
            if len(cells) != len(headers):
                break
            table_rows.append(cells)
            end += 1
        if table_rows != expected_rows:
            continue
        remaining = lines[:index] + lines[end:]
        cleaned = "\n".join(remaining)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()
    return answer


def _electrical_schematic_payload(answer: str) -> Dict[str, Any]:
    """Turn an explicit ASCII battery wiring sketch into a structural diagram.

    Components and their order are read only from the fenced sketch returned in
    this turn; the adapter does not add a component that the sketch did not show.
    """
    match = re.search(r"```(?:text|plain|plaintext)?\s*\n([\s\S]*?)\n```", str(answer or ""), re.IGNORECASE)
    if not match:
        return {}
    drawing = match.group(1)
    if not re.search(r"аккумулятор|battery", drawing, re.IGNORECASE):
        return {}
    if not re.search(r"(?:предохранител|\bF\d+\b)", drawing, re.IGNORECASE):
        return {}
    if not re.search(r"(?:выключател|\bS\d+\b)", drawing, re.IGNORECASE):
        return {}
    if not re.search(r"(?:двигател|мотор|лампоч|ламп[аыуе]|светодиод|\bM\d+\b|motor|lamp|bulb|LED)", drawing, re.IGNORECASE):
        return {}

    components: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for line in drawing.splitlines():
        clean = line.strip()
        if not clean:
            continue
        found: List[tuple[str, str]] = []
        if re.search(r"(?:плюс\s+аккумулятора|аккумулятор(?:а)?\s*\(\s*\+|\+\s*12\s*в|positive\s+(?:battery|terminal))", clean, re.IGNORECASE):
            found.append(("positive", "Плюс аккумулятора (+12 В)"))
        if re.search(r"(?:предохранител|\bF\d+\b|fuse)", clean, re.IGNORECASE):
            found.append(("fuse", "Предохранитель (F1)"))
        if re.search(r"(?:выключател|\bS\d+\b|switch)", clean, re.IGNORECASE):
            found.append(("switch", "Выключатель (S1)"))
        if re.search(r"(?:двигател|мотор|лампоч|ламп[аыуе]|светодиод|\bM\d+\b|motor|lamp|bulb|LED)", clean, re.IGNORECASE):
            if re.search(r"двигател|\bM\d+\b|motor", clean, re.IGNORECASE):
                found.append(("load", "Электродвигатель 12 В"))
            elif re.search(r"светодиод|\bLED\b", clean, re.IGNORECASE):
                found.append(("load", "Светодиод"))
            else:
                found.append(("load", "Лампочка"))
        if re.search(r"(?:минус\s+аккумулятора|аккумулятор(?:а)?\s*\(\s*-|negative\s+(?:battery|terminal)|-\s*12\s*в)", clean, re.IGNORECASE):
            found.append(("negative", "Минус аккумулятора (−)"))
        for key, label in found:
            # ASCII art usually repeats each component's ID and its caption on
            # adjacent lines. Keep one node per component in the drawn order.
            if key in seen:
                continue
            seen.add(key)
            components.append({"id": key, "label": label, "level": len(components)})

    order = [item["id"] for item in components]
    if len(components) < 4 or not {"positive", "fuse", "switch", "load", "negative"}.issubset(set(order)):
        return {}
    edges = [{"from": left["id"], "to": right["id"], "label": "подключение"}
             for left, right in zip(components, components[1:])]
    return {
        "representation": "diagram",
        "layout": "hierarchical",
        "direction": "TB",
        "title": "Схема подключения аккумулятора 12 В",
        "description": "Компоненты расположены в том же порядке, что и в текстовой схеме.",
        "nodes": components,
        "edges": edges,
        "source": "same_turn_ascii_electrical_schematic",
    }


def _is_ascii_line_chart_fence(text: str) -> bool:
    """Identify a text-only line chart that should be represented by GraphBlock."""
    value = str(text or "")
    if not re.search(r"[┤│]", value):
        return False
    row_pattern = re.compile(
        r"(?im)^\s*-?\d+(?:[.,]\d+)?\s*[┤│|]\s*.*?"
        r"(?:понедельник|вторник|среда|четверг|пятница|суббота|воскресенье|"
        r"\bпн\b|\bвт\b|\bср\b|\bчт\b|\bпт\b|\bсб\b|\bвс\b|"
        r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
        re.IGNORECASE,
    )
    return len(row_pattern.findall(value)) >= 2

def _graph_payload_from_answer(answer: str, graph_policy: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Promote an explicit 2D ASCII chart or listed 3D spheres to GraphBlock data."""
    text = str(answer or "")
    policy = graph_policy if isinstance(graph_policy, dict) else {}
    preferred = str(policy.get("preferred_representation") or "").strip().lower().replace("-", "_")
    is_3d = preferred in {"scene3d", "scene_3d", "surface3d", "surface_3d", "scatter3d", "scatter_3d", "3d"} or bool(re.search(
        r"(?:\b3\s*[- ]?d\b|\b3д\b|тр[её]хмерн\w*)", text, re.IGNORECASE
    ))
    if is_3d:
        sphere_pattern = re.compile(
            r"(?im)^\s*[-*•]?\s*(?:сфера|sphere)\s*(\d+)?\s*:\s*"
            r"(?:центр|center)\s*\(([^)]{3,90})\)\s*,?\s*"
            r"(?:радиус|radius)\s*[:=]?\s*([-+]?\d+(?:[.,]\d+)?)"
        )
        objects: List[Dict[str, Any]] = []
        for index, match in enumerate(sphere_pattern.finditer(text), 1):
            coordinates = [_number_for_render(part) for part in re.split(r"\s*[,;]\s*", match.group(2).strip())]
            radius = _number_for_render(match.group(3))
            if len(coordinates) != 3 or any(value is None for value in coordinates) or radius is None or radius <= 0:
                continue
            x, y, z = coordinates
            sphere_number = match.group(1) or str(index)
            objects.append({
                "id": f"sphere-{sphere_number}",
                "shape": "sphere",
                "label": f"Сфера {sphere_number}",
                "x": x, "y": y, "z": z,
                "center": {"x": x, "y": y, "z": z},
                "radius": radius,
            })
        if objects:
            return {
                "representation": "scene3d",
                "graph_type": "scene3d",
                "dimensions": 3,
                "three_d": True,
                "title": "3D-график: сферы",
                "description": "Сферы построены по указанным центрам и радиусам.",
                "objects_3d": objects,
                "x_axis": {"title": "X"},
                "y_axis": {"title": "Y"},
                "z_axis": {"title": "Z"},
                "source": "same_turn_answer_explicit_sphere_coordinates",
            }
        # An explicit 3D request without usable 3D data must not silently become 2D.
        return {}

    # Parse common ASCII trend charts (e.g. "20 ┤ ● Понедельник"). These values
    # are verbatim values already written by the Provider, not generated data.
    weekday_aliases = {
        "понедельник": (0, "Понедельник"), "пн": (0, "Понедельник"),
        "вторник": (1, "Вторник"), "вт": (1, "Вторник"),
        "среда": (2, "Среда"), "ср": (2, "Среда"),
        "четверг": (3, "Четверг"), "чт": (3, "Четверг"),
        "пятница": (4, "Пятница"), "пт": (4, "Пятница"),
        "суббота": (5, "Суббота"), "сб": (5, "Суббота"),
        "воскресенье": (6, "Воскресенье"), "вс": (6, "Воскресенье"),
    }
    day_pattern = re.compile(r"(?<![\w])(" + "|".join(sorted(map(re.escape, weekday_aliases), key=len, reverse=True)) + r")(?![\w])", re.IGNORECASE)
    found_points: Dict[int, Dict[str, Any]] = {}
    for line in text.splitlines():
        value_match = re.match(r"^\s*(-?\d+(?:[.,]\d+)?)\s*[┤│|]\s*(.*)$", line)
        if not value_match:
            continue
        day_match = day_pattern.search(value_match.group(2))
        if not day_match:
            continue
        day_key = day_match.group(1).lower()
        day_index, day_label = weekday_aliases[day_key]
        numeric_value = _number_for_render(value_match.group(1))
        if numeric_value is not None:
            found_points[day_index] = {"x": day_label, "y": numeric_value}
    if len(found_points) >= 2:
        points = [found_points[key] for key in sorted(found_points)]
        xs = [point["x"] for point in points]
        ys = [point["y"] for point in points]
        title_match = re.search(r"(?im)^\s*(?:график|graph)\s+[^\n]{3,140}", text)
        title = re.sub(r"[`*_]+", "", title_match.group(0)).strip().rstrip(":.;") if title_match else "График изменения значения"
        axis_match = re.search(r"(?im)^\s*([^\n]{2,60}(?:грн|uah|цена|price)[^\n]{0,25})\s*$", text)
        y_title = axis_match.group(1).strip() if axis_match else "Цена / значение"
        return {
            "representation": "line",
            "chart_type": "line",
            "graph_type": "line",
            "title": title[:140],
            "series": [{"label": "Значение", "type": "line", "points": points, "x": xs, "y": ys}],
            "points": points,
            "x_values": xs,
            "y_values": ys,
            "x_axis": {"title": "День недели"},
            "y_axis": {"title": y_title[:80]},
            "source": "same_turn_ascii_chart_values",
        }
    return {}


def _is_redundant_schematic_paragraph(paragraph: str) -> bool:
    text = str(paragraph or "").strip().lower()
    if not text or not re.search(r"схем|подключени|wiring|schematic", text):
        return False
    terms = [
        r"аккумулятор|батаре", r"предохранител|fuse", r"выключател|switch",
        r"двигател|мотор|лампоч|ламп[аыуе]|светодиод|motor|lamp|bulb",
    ]
    if sum(bool(re.search(pattern, text, re.IGNORECASE)) for pattern in terms) < 3:
        return False
    return bool(re.search(r"(?:→|➜|->|-->|\bзатем\b|\bпосле\s+него\b|\bчерез\b)", text, re.IGNORECASE))

def _rendered_link_urls(render_blocks: Any) -> set[str]:
    """Return URLs which are definitely represented by a visible link renderer."""
    urls: set[str] = set()
    if not isinstance(render_blocks, list):
        return urls

    for block in render_blocks:
        if not isinstance(block, dict):
            continue
        block_type = _scene_block_type(block)
        if block_type not in {"link", "file"}:
            continue
        payload = _payload_for_render_block(block, block_type)
        candidates: List[Any] = [payload.get("url"), payload.get("href"), block.get("url"), block.get("href")]
        for key in ("links", "items", "sources"):
            values = payload.get(key)
            if isinstance(values, list):
                for item in values:
                    if isinstance(item, dict):
                        candidates.extend((item.get("url"), item.get("href")))
                    elif isinstance(item, str):
                        candidates.append(item)
        for candidate in candidates:
            value = str(candidate or "").strip().rstrip(".,;:!?)\"'}]")
            if value.startswith(("http://", "https://")):
                urls.add(value)
                urls.add(value.rstrip("/"))
    return urls


def _strip_rendered_link_urls(text: str, render_blocks: Any) -> str:
    """Remove only URL strings already carried by a visible link renderer.

    Human-readable labels and surrounding explanation are retained. Inline and
    fenced code are protected because URLs inside code are source content, not
    prose citations.
    """
    rendered_urls = _rendered_link_urls(render_blocks)
    if not rendered_urls or not text:
        return text

    def is_rendered_url(raw: str) -> bool:
        value = str(raw or "").strip().rstrip(".,;:!?)\"'}]")
        return value in rendered_urls or value.rstrip("/") in rendered_urls

    # Split off code first, and only process the non-code segments.
    segments = re.split(r"(```[\s\S]*?```|`[^`\n]*`)", str(text))
    for index in range(0, len(segments), 2):
        prose = segments[index]

        def markdown_link(match: re.Match[str]) -> str:
            label, url = match.group(1), match.group(2)
            if not is_rendered_url(url):
                return match.group(0)
            label = label.strip()
            return "" if is_rendered_url(label) else label

        prose = re.sub(r"\[([^\]]{1,300})\]\((https?://[^\s)]+)\)", markdown_link, prose, flags=re.IGNORECASE)

        def bare_url(match: re.Match[str]) -> str:
            raw = match.group(0)
            return "" if is_rendered_url(raw) else raw

        prose = re.sub(r"https?://[^\s<>\]\[()]+", bare_url, prose, flags=re.IGNORECASE)
        # Remove list markers left with no content; preserve list items whose
        # labels/descriptions remain after the URL itself is moved to the card.
        prose_lines = []
        for line in prose.splitlines():
            if re.fullmatch(r"\s*(?:[-*•]|\d+[.)])\s*", line):
                continue
            prose_lines.append(line)
        segments[index] = "\n".join(prose_lines)

    cleaned = "".join(segments)
    cleaned = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", cleaned)
    return cleaned.strip()


def _strip_rendered_segments(
    text: str,
    rendered_types: set[str],
    render_blocks: Any = None,
    suppress_unrequested_table: bool = False,
) -> str:
    """Keep narrative text while moving or suppressing structured fragments.

    Unrequested Markdown tables may also be removed when a concrete requested
    GraphBlock already represents their values. This prevents duplicate output
    without discarding the data needed to construct the graph.
    """
    cleaned = str(text or "")
    if not cleaned or not rendered_types:
        return cleaned.strip()

    if "table" in rendered_types or suppress_unrequested_table:
        # Match Markdown data to an actual TableBlock payload before removing it.
        # The source-derived fallback is retained for legacy payloads that expose
        # a table type but omit its normalized columns/rows.
        expected_tables: List[Dict[str, Any]] = []
        if isinstance(render_blocks, list):
            for block in render_blocks:
                if not isinstance(block, dict) or _scene_block_type(block) != "table":
                    continue
                payload = _payload_for_render_block(block, "table")
                columns = payload.get("columns") or payload.get("headers")
                rows = payload.get("rows") or payload.get("data")
                if isinstance(columns, list) and columns and isinstance(rows, list) and rows:
                    normalized_rows = []
                    for row in rows:
                        if isinstance(row, (list, tuple)):
                            normalized_rows.append([str(value).strip() for value in row])
                    if normalized_rows:
                        expected_tables.append({
                            "columns": [str(value).strip() for value in columns],
                            "headers": [str(value).strip() for value in columns],
                            "rows": normalized_rows,
                        })
        if not expected_tables:
            source_table = _markdown_table_payload(cleaned)
            if source_table:
                expected_tables = [source_table]
        for table in expected_tables:
            updated = _strip_first_markdown_table(cleaned, table)
            if updated != cleaned:
                cleaned = updated

    if "diagram" in rendered_types:
        match = re.search(r"```\s*mermaid\s*\n([\s\S]*?)\n```", cleaned, re.IGNORECASE)
        if match and _mermaid_payload(match.group(1).strip()):
            # Only remove the Mermaid source when a concrete DiagramRenderer is
            # present in this scene; its explanatory prose remains untouched.
            if not isinstance(render_blocks, list) or any(
                isinstance(block, dict) and _scene_block_type(block) == "diagram"
                and _has_render_payload("diagram", _payload_for_render_block(block, "diagram"), block)
                for block in render_blocks
            ):
                cleaned = cleaned.replace(match.group(0), "", 1)
        else:
            schematic_payload = _electrical_schematic_payload(cleaned)
            if schematic_payload and (not isinstance(render_blocks, list) or any(
                isinstance(block, dict) and _scene_block_type(block) == "diagram"
                and _has_render_payload("diagram", _payload_for_render_block(block, "diagram"), block)
                for block in render_blocks
            )):
                sketch = re.search(r"```(?:text|plain|plaintext)?\s*\n([\s\S]*?)\n```", cleaned, re.IGNORECASE)
                if sketch:
                    cleaned = cleaned.replace(sketch.group(0), "", 1)
                paragraphs = re.split(r"\n\s*\n", cleaned)
                paragraphs = [paragraph for paragraph in paragraphs if not _is_redundant_schematic_paragraph(paragraph)]
                cleaned = "\n\n".join(paragraphs)

    if "graph" in rendered_types:
        # Only remove an ASCII chart when the graph renderer was built from this
        # exact chart source; otherwise keep the source text rather than risk loss.
        graph_from_same_answer = False
        if isinstance(render_blocks, list):
            for block in render_blocks:
                if not isinstance(block, dict) or _scene_block_type(block) != "graph":
                    continue
                payload = _payload_for_render_block(block, "graph")
                if str(payload.get("source") or "") == "same_turn_ascii_chart_values":
                    graph_from_same_answer = True
                    break
        if graph_from_same_answer:
            for chart in list(re.finditer(r"```([\w.+-]*)\s*\n([\s\S]*?)\n```", cleaned)):
                if _is_ascii_line_chart_fence(chart.group(2)):
                    cleaned = cleaned.replace(chart.group(0), "", 1)
                    break

    if "code" in rendered_types:
        rendered_code: List[str] = []
        if isinstance(render_blocks, list):
            for block in render_blocks:
                if not isinstance(block, dict) or _scene_block_type(block) != "code":
                    continue
                payload = _payload_for_render_block(block, "code")
                value = payload.get("code") or payload.get("content") or block.get("code")
                if isinstance(value, str) and value.strip():
                    rendered_code.append(value.strip().replace("\r\n", "\n"))
        for match in list(re.finditer(r"```([\w.+-]*)\s*\n([\s\S]*?)\n```", cleaned)):
            if match.group(1).strip().lower() in {"mermaid", "diagram"}:
                continue
            fence_content = match.group(2).strip().replace("\r\n", "\n")
            if rendered_code and fence_content in rendered_code:
                cleaned = cleaned.replace(match.group(0), "", 1)

    if "formula" in rendered_types:
        rendered_formulas: set[str] = set()

        def formula_key(value: Any) -> str:
            if not isinstance(value, str):
                return ""
            candidate = value.strip()
            candidate = re.sub(r"^\s*(?:\$\$?|\\\[|\\\()", "", candidate)
            candidate = re.sub(r"(?:\$\$?|\\\]|\\\))\s*$", "", candidate)
            candidate = candidate.replace("²", "^2").replace("³", "^3").replace("⁴", "^4")
            return re.sub(r"\s+", "", candidate)

        if isinstance(render_blocks, list):
            for block in render_blocks:
                if not isinstance(block, dict) or _scene_block_type(block) != "formula":
                    continue
                payload = _payload_for_render_block(block, "formula")
                values = payload.get("formulas") or payload.get("latex_formulas")
                if isinstance(values, list):
                    for value in values:
                        if isinstance(value, str):
                            formula = value
                        elif isinstance(value, dict):
                            formula = next((value.get(key) for key in ("latex", "tex", "formula", "equation", "expression", "value") if isinstance(value.get(key), str) and value.get(key).strip()), "")
                        else:
                            formula = ""
                        key = formula_key(formula)
                        if key:
                            rendered_formulas.add(key)
                for key_name in ("formula", "latex", "equation", "expression", "math"):
                    key = formula_key(payload.get(key_name))
                    if key:
                        rendered_formulas.add(key)

        if rendered_formulas:
            # Prefer display math first so $$...$$ is not misread as two inline
            # dollar expressions. Only matching concrete renderer payloads are
            # removed; unrelated equations and ordinary currency text survive.
            formula_patterns = (
                re.compile(r"\$\$([\s\S]*?)\$\$"),
                re.compile(r"\\\[([\s\S]*?)\\\]"),
                re.compile(r"\\\(([\s\S]*?)\\\)"),
                re.compile(r"(?<!\$)\$([^$\n]{1,500})\$(?!\$)"),
            )
            for formula_pattern in formula_patterns:
                for match in list(formula_pattern.finditer(cleaned)):
                    formula = match.group(1).strip()
                    if formula_key(formula) in rendered_formulas:
                        cleaned = cleaned.replace(match.group(0), "", 1)

    if "link" in rendered_types:
        cleaned = _strip_rendered_link_urls(cleaned, render_blocks)

    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()

def _number_for_render(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value or "").strip().replace("\u00a0", "").replace(" ", "")
    if not text:
        return None
    text = re.sub(r"[^0-9,.-]", "", text)
    if not text or text in {"-", ".", ","}:
        return None
    if "," in text and "." in text:
        # When both separators appear, use the last one as the decimal mark.
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        result = float(text)
        return result if result == result and abs(result) != float("inf") else None
    except (TypeError, ValueError):
        return None




def _weekly_axis_labels(existing_x: Any = None) -> List[str]:
    """Create seven in-range labels; preserve calendar dates when both endpoints are dates."""
    import datetime as _datetime

    values = existing_x if isinstance(existing_x, list) else []
    if len(values) >= 2:
        formats = ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y")
        parsed = []
        source_format = None
        for value in (values[0], values[-1]):
            candidate = None
            candidate_format = None
            for fmt in formats:
                try:
                    candidate = _datetime.datetime.strptime(str(value).strip(), fmt).date()
                    candidate_format = fmt
                    break
                except (TypeError, ValueError):
                    continue
            parsed.append(candidate)
            if candidate_format:
                source_format = candidate_format
        if parsed[0] and parsed[1] and (parsed[1] - parsed[0]).days == 6:
            return [
                (_datetime.datetime.combine(parsed[0] + _datetime.timedelta(days=i), _datetime.time()).strftime(source_format))
                for i in range(7)
            ]
    return ["Начало недели", "День 2", "День 3", "День 4", "День 5", "День 6", "Конец недели"]


def _interpolate_weekly_graph_payload(
    payload: Dict[str, Any],
    current_request: str = "",
    answer: str = "",
) -> Dict[str, Any]:
    """Fill a requested weekly line chart between two known endpoints with labelled estimates.

    This never runs for arbitrary charts: the request/answer or axis must identify a
    week, the payload must be 2D, and a series must contain exactly two numeric values.
    Existing source endpoints are preserved verbatim in ``source_endpoints``.
    """
    if not isinstance(payload, dict) or not payload:
        return payload if isinstance(payload, dict) else {}

    representations = {
        str(payload.get(key) or "").strip().lower().replace("-", "_")
        for key in ("representation", "graph_type", "chart_type")
    }
    if representations & {
        "scene3d", "scene_3d", "surface3d", "surface_3d", "scatter3d", "scatter_3d",
        "mesh3d", "mesh_3d", "3d", "3d_scene", "spacetime_curvature",
        "bar", "bar_chart", "column", "column_chart", "histogram", "pie", "donut",
    } or payload.get("dimensions") == 3 or payload.get("three_d") is True:
        return payload

    x_axis = payload.get("x_axis") if isinstance(payload.get("x_axis"), dict) else {}
    title = str(payload.get("title") or "")
    temporal_text = " ".join((str(current_request or ""), str(answer or ""), title,
                              str(x_axis.get("title") or x_axis.get("label") or ""),
                              str(payload.get("description") or ""))).lower().replace("ё", "е")
    weekly_request = bool(re.search(r"(?:недел\w*|\bweek(?:ly)?\b|\b7\s*(?:дн\w*|days?)\b)", temporal_text, re.IGNORECASE))
    if not weekly_request:
        return payload

    raw_series = payload.get("series") or payload.get("datasets") or payload.get("traces")
    if isinstance(raw_series, dict):
        raw_series = list(raw_series.values())
    elif not isinstance(raw_series, list):
        raw_series = []

    axis_values = x_axis.get("values") if isinstance(x_axis.get("values"), list) else (
        payload.get("x_values") if isinstance(payload.get("x_values"), list) else payload.get("x")
    )
    axis_values = axis_values if isinstance(axis_values, list) else []
    normalized_series: List[Dict[str, Any]] = [deepcopy(item) for item in raw_series if isinstance(item, dict)]

    # Support a canonical top-level two-point payload as well as series[].
    if not normalized_series:
        top_points = payload.get("points") or payload.get("data_points")
        top_x = payload.get("x_values") or payload.get("x") or axis_values
        top_y = payload.get("y_values") or payload.get("y") or payload.get("values")
        if isinstance(top_points, list) and len(top_points) >= 2:
            ys = []
            xs = []
            for index, point in enumerate(top_points):
                if isinstance(point, dict):
                    xs.append(point.get("x", top_x[index] if isinstance(top_x, list) and index < len(top_x) else index + 1))
                    ys.append(point.get("y", point.get("value")))
                elif isinstance(point, (list, tuple)) and len(point) >= 2:
                    xs.append(point[0]); ys.append(point[1])
            if len(ys) >= 2:
                normalized_series = [{"label": str(payload.get("series_label") or payload.get("y_label") or title or "Значение"), "points": [{"x": x, "y": y} for x, y in zip(xs, ys)]}]
        elif isinstance(top_y, list) and len(top_y) == 2:
            xs = top_x if isinstance(top_x, list) and len(top_x) >= 2 else ["Начало недели", "Конец недели"]
            normalized_series = [{"label": str(payload.get("series_label") or payload.get("y_label") or title or "Значение"), "x": xs[:2], "y": top_y[:2], "values": top_y[:2]}]

    if not normalized_series:
        return payload

    labels = _weekly_axis_labels(axis_values)
    changed = False
    original_endpoint_records: List[Dict[str, Any]] = []
    new_series: List[Dict[str, Any]] = []
    for index, item in enumerate(normalized_series):
        original = deepcopy(item)
        item_representation = str(
            item.get("type") or item.get("chart_type") or item.get("representation") or ""
        ).strip().lower().replace("-", "_")
        if item_representation in {"bar", "bar_chart", "column", "column_chart", "histogram", "pie", "donut", "scatter"}:
            new_series.append(original)
            continue
        raw_points = item.get("points") or item.get("data_points") or item.get("data")
        point_x: List[Any] = []
        point_y: List[Any] = []
        point_templates: List[Dict[str, Any]] = []
        if isinstance(raw_points, list):
            for point_index, point in enumerate(raw_points):
                if isinstance(point, dict):
                    x_value = point.get("x", point.get("xValue", point_index + 1))
                    y_value = point.get("y", point.get("yValue", point.get("value")))
                    point_templates.append(deepcopy(point))
                elif isinstance(point, (list, tuple)) and len(point) >= 2:
                    x_value, y_value = point[0], point[1]
                    point_templates.append({"x": x_value, "y": y_value})
                else:
                    continue
                if _number_for_render(y_value) is not None:
                    point_x.append(x_value); point_y.append(y_value)

        item_x = item.get("x") if isinstance(item.get("x"), list) else item.get("x_values")
        item_y = item.get("y") if isinstance(item.get("y"), list) else item.get("y_values")
        if not isinstance(item_y, list):
            item_y = item.get("values") if isinstance(item.get("values"), list) else None
        # If the parallel y-array contains more points than a legacy points array,
        # prefer it; otherwise keep point metadata from the explicit point objects.
        if isinstance(item_y, list) and len(item_y) > len(point_y):
            point_y = list(item_y)
            chosen_x = item_x if isinstance(item_x, list) and len(item_x) >= len(point_y) else axis_values
            point_x = list(chosen_x[:len(point_y)]) if isinstance(chosen_x, list) else []
            point_templates = []
        elif not point_y and isinstance(item_y, list):
            point_y = list(item_y)
            chosen_x = item_x if isinstance(item_x, list) and len(item_x) >= len(point_y) else axis_values
            point_x = list(chosen_x[:len(point_y)]) if isinstance(chosen_x, list) else []

        numeric_values = [_number_for_render(value) for value in point_y]
        if len(numeric_values) != 2 or any(value is None for value in numeric_values):
            new_series.append(original)
            continue

        start_value = float(numeric_values[0])
        end_value = float(numeric_values[1])
        original_x = point_x[:2] if len(point_x) >= 2 else (axis_values[:2] if len(axis_values) >= 2 else ["Начало недели", "Конец недели"])
        original_endpoint_records.append({
            "series_label": str(item.get("label") or item.get("name") or f"Ряд {index + 1}"),
            "x_values": deepcopy(original_x),
            "values": [point_y[0], point_y[1]],
        })
        interpolated_values = [round(start_value + (end_value - start_value) * step / 6, 2) for step in range(7)]
        interpolated_values[0] = start_value
        interpolated_values[-1] = end_value
        generated_points: List[Dict[str, Any]] = []
        for point_index, (x_value, y_value) in enumerate(zip(labels, interpolated_values)):
            if point_index == 0 and point_templates:
                template = deepcopy(point_templates[0])
            elif point_index == 6 and len(point_templates) >= 2:
                template = deepcopy(point_templates[-1])
            else:
                template = {}
            template["x"] = x_value
            template["y"] = y_value
            if point_index not in {0, 6}:
                template["label"] = "Расчётная интерполяция"
                template["estimated"] = True
            else:
                template.setdefault("label", "Исходное значение")
                template["estimated"] = False
            generated_points.append(template)

        item["points"] = generated_points
        item["x"] = labels[:]
        item["y"] = interpolated_values[:]
        item["values"] = interpolated_values[:]
        item["interpolation"] = {
            "method": "linear",
            "derived_points_are_estimates": True,
            "observed_endpoints_preserved": True,
        }
        label = str(item.get("label") or item.get("name") or "").strip()
        if label and "расчет" not in label.lower() and "расчёт" not in label.lower() and "estimate" not in label.lower():
            item["label"] = f"{label} (расчётная интерполяция)"
        new_series.append(item)
        changed = True

    if not changed:
        return payload

    payload["series"] = new_series
    payload["x_values"] = labels[:]
    # Keep only the first series in top-level aliases; the canonical series list
    # remains authoritative for multi-series graphs.
    first_values = new_series[0].get("values") if new_series and isinstance(new_series[0].get("values"), list) else None
    if isinstance(first_values, list) and len(first_values) == 7:
        payload["y_values"] = deepcopy(first_values)
        payload["points"] = deepcopy(new_series[0].get("points") or [])
    payload["x_axis"] = {
        **x_axis,
        "title": x_axis.get("title") or x_axis.get("label") or "День недели",
        "values": labels[:],
        "granularity": "daily",
    }
    payload["source_endpoints"] = payload.get("source_endpoints") or original_endpoint_records
    existing_semantics = payload.get("data_semantics") if isinstance(payload.get("data_semantics"), dict) else {}
    payload["data_semantics"] = {
        **existing_semantics,
        "kind": existing_semantics.get("kind") or "weekly_time_series",
        "interpolation": "linear",
        "derived_points_are_estimates": True,
        "observations_claimed": False,
    }
    payload["description"] = (
        "График соединяет заданные начальное и конечное значения пятью расчётными промежуточными точками; "
        "они не являются фактическими измерениями или котировками."
    )
    payload["interpolation_applied"] = True
    payload["interpolation_method"] = "linear"
    payload["estimated_points"] = [2, 3, 4, 5, 6]
    return payload


def _graph_payload_from_request(
    current_request: str,
    answer: str = "",
    graph_policy: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build only a graph that is grounded in the current request/answer.

    Explicit equations are kept verbatim. For a weekly line chart with two known
    endpoints, missing daily points are calculated by linear interpolation and
    marked as estimates, never as observed measurements. Common 3D surfaces are
    allowed as labelled illustrative defaults when the user names the surface but
    supplies no equation.
    """
    request_text = str(current_request or "").strip()
    answer_text = str(answer or "").strip()
    text = "\n".join(part for part in (request_text, answer_text) if part)
    if not text:
        return {}

    policy = graph_policy if isinstance(graph_policy, dict) else {}
    preferred = str(policy.get("preferred_representation") or "").strip().lower().replace("-", "_")
    is_3d = preferred in {
        "scene3d", "scene_3d", "surface3d", "surface_3d",
        "scatter3d", "scatter_3d", "mesh3d", "mesh_3d", "3d",
    } or bool(re.search(r"(?:\b3\s*[- ]?d\b|\b3д\b|тр[её]хмерн\w*|3-мерн\w*)", text, re.IGNORECASE))

    if is_3d:
        # A named 3D primitive is already sufficient geometry for GraphBlock.
        # Previously this branch only reconstructed equations/surfaces or spheres;
        # a request for a cube therefore returned {} when the Provider emitted an
        # empty GraphBlock shell. SceneContract then correctly rejected that shell,
        # leaving the user with prose but no visible graph. Build a labelled unit
        # cube as an explicit illustrative default only when the current request
        # names a cube and supplies no dimensions of its own.
        cube_requested = bool(re.search(
            r"(?:куб\w*|\bcube\w*\b|\bhexahedron\w*\b)",
            request_text,
            re.IGNORECASE,
        ))
        if cube_requested:
            vertex_specs = [
                ("A", -1.0, -1.0, -1.0),
                ("B",  1.0, -1.0, -1.0),
                ("C",  1.0,  1.0, -1.0),
                ("D", -1.0,  1.0, -1.0),
                ("E", -1.0, -1.0,  1.0),
                ("F",  1.0, -1.0,  1.0),
                ("G",  1.0,  1.0,  1.0),
                ("H", -1.0,  1.0,  1.0),
            ]
            vertices = [
                {"id": name, "label": name, "x": x, "y": y, "z": z}
                for name, x, y, z in vertex_specs
            ]
            edge_indices = (
                (0, 1), (1, 2), (2, 3), (3, 0),
                (4, 5), (5, 6), (6, 7), (7, 4),
                (0, 4), (1, 5), (2, 6), (3, 7),
            )
            paths = [
                {
                    "id": f"cube-edge-{index + 1:02d}",
                    "kind": "wireframe",
                    "label": f"{vertices[left]['label']}–{vertices[right]['label']}",
                    "points": [
                        {key: vertices[left][key] for key in ("x", "y", "z", "label")},
                        {key: vertices[right][key] for key in ("x", "y", "z", "label")},
                    ],
                }
                for index, (left, right) in enumerate(edge_indices)
            ]
            cube_object = {
                "id": "cube-1",
                "shape": "cube",
                "object_type": "cube",
                "label": "Куб",
                "x": 0.0,
                "y": 0.0,
                "z": 0.0,
                "center": {"x": 0.0, "y": 0.0, "z": 0.0},
                "size": 2.0,
                "width": 2.0,
                "height": 2.0,
                "depth": 2.0,
                "vertices": vertices,
                "edges": [
                    {"from": vertices[left]["label"], "to": vertices[right]["label"]}
                    for left, right in edge_indices
                ],
            }
            return {
                "representation": "scene3d",
                "graph_type": "scene3d",
                "chart_type": "scene3d",
                "dimensions": 3,
                "three_d": True,
                "title": "Куб в трёхмерном пространстве",
                "description": (
                    "Схематический единичный куб с центром в начале координат. "
                    "Длина ребра условно равна 2 единицам, поскольку размер не задан в запросе."
                ),
                "objects_3d": [cube_object],
                "points": vertices,
                "paths": paths,
                "x_domain": [-1.5, 1.5],
                "y_domain": [-1.5, 1.5],
                "z_domain": [-1.5, 1.5],
                "x_axis": {"title": "X"},
                "y_axis": {"title": "Y"},
                "z_axis": {"title": "Z"},
                "source": "current_request_explicit_3d_cube",
            }

        equation_match = re.search(
            r"(?im)(?:^|[\s;])(?:z|f\s*\(\s*x\s*,\s*y\s*\))\s*=\s*([^\n;]+)",
            text,
        )
        expression = ""
        illustrative = False
        if equation_match:
            expression = equation_match.group(1).strip().strip("`$ ")
            expression = re.sub(r"\s+(?:в|in)\s*(?:3\s*[- ]?d|3д|3d)\b.*$", "", expression, flags=re.IGNORECASE).strip()
            expression = re.sub(r"[.!?]+$", "", expression).strip()
        elif re.search(r"парабол|paraboloid|parabola", text, re.IGNORECASE):
            expression = "x^2 + y^2"
            illustrative = True
        elif re.search(r"седлов|saddle", text, re.IGNORECASE):
            expression = "x^2 - y^2"
            illustrative = True
        elif re.search(r"волнообраз|волнов|wave surface|waveform surface", text, re.IGNORECASE):
            expression = "sin(sqrt(x^2 + y^2))"
            illustrative = True
        if expression:
            return {
                "representation": "surface3d",
                "graph_type": "surface3d",
                "chart_type": "surface3d",
                "dimensions": 3,
                "three_d": True,
                "title": "Иллюстративная 3D-поверхность" if illustrative else "3D-график функции",
                "description": (
                    "Показана стандартная иллюстративная поверхность; уравнение не задавалось явно."
                    if illustrative else "Поверхность построена по уравнению из текущего запроса."
                ),
                "equation": f"z = {expression}",
                "expression": expression,
                "surface_function": expression,
                "z_function": expression,
                "x_domain": [-5, 5],
                "y_domain": [-5, 5],
                "source": "current_request_equation" if not illustrative else "labelled_illustrative_shape_default",
            }
        return {}

    # Require a semantically explicit endpoint relation; arbitrary numbers in
    # prose are not enough to be treated as chart data.
    range_pattern = re.compile(
        r"(?i)(?:\b(?:с|от|from)\s*)"
        r"(-?\d+(?:[.,]\d+)?)\s*(?:грн\.?|uah|usd|eur|€|\$)?\s*"
        r"(?:до|to|по|through)\s*"
        r"(-?\d+(?:[.,]\d+)?)\s*(грн\.?|uah|usd|eur|€|\$)?"
    )
    range_match = range_pattern.search(text)
    if not range_match:
        # Equation-only 2D function: preserve the user/model's actual expression.
        equation_match = re.search(
            r"(?im)(?:^|[\s;])(?:y|f\s*\(\s*x\s*\))\s*=\s*([^\n;]+)",
            text,
        )
        if equation_match and re.search(r"\bx\b", equation_match.group(1), re.IGNORECASE):
            expression = equation_match.group(1).strip().strip("`$ ")
            expression = re.sub(r"[.!?]+$", "", expression).strip()
            if expression:
                return {
                    "representation": "function2d",
                    "graph_type": "function",
                    "chart_type": "line",
                    "dimensions": 2,
                    "title": "График функции",
                    "equation": f"y = {expression}",
                    "expression": expression,
                    "series": [{
                        "label": f"y = {expression}",
                        "type": "function",
                        "fn": expression,
                        "equation": f"y = {expression}",
                        "expression": expression,
                    }],
                    "x_axis": {"title": "x"},
                    "y_axis": {"title": "y"},
                    "source": "current_request_equation",
                }
        return {}

    start_value = _number_for_render(range_match.group(1))
    end_value = _number_for_render(range_match.group(2))
    if start_value is None or end_value is None:
        return {}

    combined_low = text.lower()
    if re.search(r"недел|week", combined_low):
        x_labels = ["Начало недели", "Конец недели"]
        x_title = "Период недели"
    elif re.search(r"месяц|month", combined_low):
        x_labels = ["Начало месяца", "Конец месяца"]
        x_title = "Период месяца"
    elif re.search(r"год|year", combined_low):
        x_labels = ["Начало года", "Конец года"]
        x_title = "Период года"
    elif re.search(r"день|дня|дней|day|daily", combined_low):
        x_labels = ["Начало периода", "Конец периода"]
        x_title = "Период"
    else:
        x_labels = ["Начальное значение", "Конечное значение"]
        x_title = "Период"

    currency = range_match.group(3) or ""
    if not currency:
        currency_match = re.search(r"(?i)(грн\.?|uah|usd|eur|€|\$)", text)
        currency = currency_match.group(1) if currency_match else ""
    y_title = f"Значение, {currency}" if currency else "Значение"
    title_match = re.search(
        r"(?i)(?:построй|построить|покажи|нарисуй|построить)\s+(?:мне\s+)?(?:график|диаграмму)\s+(.{3,150})",
        request_text,
    )
    title = title_match.group(1).strip() if title_match else "Изменение значения за период"
    title = re.sub(r"\s*(?:с|от)\s*-?\d+(?:[.,]\d+)?[\w\s.,]*$", "", title, flags=re.IGNORECASE).strip(" .,:;-") or "Изменение значения за период"
    points = [
        {"x": x_labels[0], "y": start_value, "label": "Исходное значение", "estimated": False},
        {"x": x_labels[1], "y": end_value, "label": "Исходное значение", "estimated": False},
    ]
    payload = {
        "representation": "line",
        "chart_type": "line",
        "graph_type": "line",
        "dimensions": 2,
        "title": title[:140],
        "description": "Начальное и конечное значения заданы явно.",
        "series": [{
            "label": y_title,
            "type": "line",
            "points": points,
            "x": x_labels,
            "y": [start_value, end_value],
            "values": [start_value, end_value],
        }],
        "points": points,
        "x_values": x_labels,
        "y_values": [start_value, end_value],
        "x_axis": {"title": x_title, "values": x_labels},
        "y_axis": {"title": y_title},
        "source": "explicit_current_request_range",
        "data_semantics": {"kind": "endpoint_range", "interpolation": "not_applied"},
    }
    return _interpolate_weekly_graph_payload(payload, request_text, answer_text)


def _geometry_diagram_payload_from_request(
    current_request: str,
    answer: str = "",
) -> Dict[str, Any]:
    """Create small SVG drawings for explicitly named elementary geometry.

    Shape identity comes from the current request. Dimension labels are shown
    only when the user supplies them; no unspecified side lengths are invented.
    """
    request_text = str(current_request or "").strip()
    text = "\n".join(part for part in (request_text, str(answer or "").strip()) if part)
    if not text:
        return {}
    low = text.lower()

    if re.search(r"треугол|triangle", low):
        shape = "triangle"
    elif re.search(r"квадрат|square", low):
        shape = "square"
    elif re.search(r"прямоугольник|прямоугольн|rectangle", low):
        shape = "rectangle"
    elif re.search(r"окружност|круг|circle", low):
        shape = "circle"
    else:
        return {}

    measures = re.findall(
        r"(?<![\w])(\d+(?:[.,]\d+)?)\s*(см|cm|мм|mm|м|meter|meters|m)\b",
        request_text,
        re.IGNORECASE,
    )
    def label_measure(item: tuple[str, str]) -> str:
        value = item[0].replace(",", ".")
        unit = item[1].lower()
        unit_map = {"cm": "см", "mm": "мм", "m": "м", "meter": "м", "meters": "м"}
        return f"{value} {unit_map.get(unit, unit)}"

    side_labels: list[str] = []
    per_each_match = re.search(
        r"(?i)(?:по|each|every side(?: is)?)\s*(\d+(?:[.,]\d+)?)\s*(см|cm|мм|mm|м|m)\b",
        request_text,
    )
    if per_each_match and shape in {"triangle", "square"}:
        side_labels = [label_measure((per_each_match.group(1), per_each_match.group(2)))] * (3 if shape == "triangle" else 4)
    elif measures:
        side_labels = [label_measure(item) for item in measures[:4]]

    if shape == "triangle":
        polygon = '<polygon points="260,48 78,318 442,318" fill="rgba(103,232,249,0.08)" stroke="#67e8f9" stroke-width="3" stroke-linejoin="round"/>'
        labels = ""
        if side_labels:
            labels_data = [
                (160, 172, side_labels[0]),
                (360, 172, side_labels[min(1, len(side_labels)-1)]),
                (260, 342, side_labels[min(2, len(side_labels)-1)]),
            ]
            labels = "".join(
                f'<text x="{x}" y="{y}" text-anchor="middle" fill="#e5e7eb" font-size="18" font-family="Arial,sans-serif">{value}</text>'
                for x, y, value in labels_data
            )
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="520" height="370" viewBox="0 0 520 370">'
            '<title>Чертёж треугольника</title>'
            '<line x1="260" y1="48" x2="78" y2="318" stroke="#67e8f9" stroke-width="3"/>'
            '<line x1="260" y1="48" x2="442" y2="318" stroke="#67e8f9" stroke-width="3"/>'
            '<line x1="78" y1="318" x2="442" y2="318" stroke="#67e8f9" stroke-width="3"/>'
            f'{labels}'
            '<text x="260" y="25" text-anchor="middle" fill="#e5e7eb" font-size="16" font-family="Arial,sans-serif">Треугольник</text>'
            '</svg>'
        )
        equilateral = len(side_labels) >= 3 and len(set(side_labels[:3])) == 1
        return {
            "representation": "diagram",
            "shape": "equilateral_triangle" if equilateral else "triangle",
            "diagram_type": "geometry",
            "title": "Чертёж равностороннего треугольника" if equilateral else "Чертёж треугольника",
            "description": "Размеры подписаны только по данным текущего запроса." if side_labels else "Схематический треугольник; размеры сторон не задавались.",
            "svg": svg,
            "source": "current_request_geometry_fallback",
        }

    if shape == "square":
        side = side_labels[0] if side_labels else ""
        svg_shape = (
            '<rect x="135" y="65" width="250" height="250" rx="1" fill="rgba(103,232,249,0.08)" stroke="#67e8f9" stroke-width="3"/>'
        )
        labels = f'<text x="260" y="52" text-anchor="middle" fill="#e5e7eb" font-size="18">{side}</text>' if side else ""
        title = "Чертёж квадрата"
        shape_name = "square"
    elif shape == "rectangle":
        left = side_labels[0] if side_labels else ""
        right = side_labels[1] if len(side_labels) > 1 else ""
        svg_shape = '<rect x="90" y="95" width="340" height="190" fill="rgba(103,232,249,0.08)" stroke="#67e8f9" stroke-width="3"/>'
        labels = (
            (f'<text x="260" y="82" text-anchor="middle" fill="#e5e7eb" font-size="18">{left}</text>' if left else "")
            + (f'<text x="448" y="196" text-anchor="middle" fill="#e5e7eb" font-size="18">{right}</text>' if right else "")
        )
        title = "Чертёж прямоугольника"
        shape_name = "rectangle"
    else:
        radius = side_labels[0] if side_labels else ""
        svg_shape = '<circle cx="260" cy="190" r="120" fill="rgba(103,232,249,0.08)" stroke="#67e8f9" stroke-width="3"/>'
        labels = f'<text x="260" y="190" text-anchor="middle" fill="#e5e7eb" font-size="18">{radius}</text>' if radius else ""
        title = "Чертёж окружности"
        shape_name = "circle"

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="520" height="380" viewBox="0 0 520 380">'
        f'<title>{title}</title>{svg_shape}{labels}</svg>'
    )
    return {
        "representation": "diagram",
        "shape": shape_name,
        "diagram_type": "geometry",
        "title": title,
        "description": "Размеры подписаны только по данным текущего запроса." if side_labels else "Схематическая геометрическая фигура; размеры не задавались.",
        "svg": svg,
        "source": "current_request_geometry_fallback",
    }


def _graph_payload_from_table_3d(
    table: Dict[str, Any],
    graph_policy: Dict[str, Any] | None = None,
    current_request: str = "",
) -> Dict[str, Any]:
    """Promote an explicit x/y/z table to a lossless 3D scatter payload.

    This function only returns a 3D payload when the table itself contains three
    independently named numeric coordinates. It never fabricates a z-axis.
    """
    policy = graph_policy if isinstance(graph_policy, dict) else {}
    request_text = str(current_request or "").lower().replace("ё", "е")
    explicit_3d = str(policy.get("mode") or "").lower() in {
        "explicit_3d", "inferred_spatial_scene", "structured_3d_data"
    } or bool(re.search(
        r"(?:\b3\s*[- ]?d\b|3д|тр[её]хмерн\w*|three[- ]dimensional)",
        request_text, re.IGNORECASE,
    ))
    if not explicit_3d or not isinstance(table, dict):
        return {}
    columns = table.get("columns") or table.get("headers") or []
    rows = table.get("rows") or []
    if not isinstance(columns, list) or len(columns) < 3 or not isinstance(rows, list) or len(rows) < 2:
        return {}

    def normalized_header(value: Any) -> str:
        return re.sub(r"[^a-zа-яё0-9]+", " ", str(value or "").lower().replace("ё", "е")).strip()

    headers = [normalized_header(value) for value in columns]
    axis_indices: dict[str, int] = {}
    axis_patterns = {
        "x": re.compile(r"^(?:ось |координата |координаты )?x(?: координата| координаты)?(?: .*)?$|^x axis$"),
        "y": re.compile(r"^(?:ось |координата |координаты )?y(?: координата| координаты)?(?: .*)?$|^y axis$"),
        "z": re.compile(r"^(?:ось |координата |координаты )?z(?: координата| координаты)?(?: .*)?$|^z axis$"),
    }
    for axis, pattern in axis_patterns.items():
        found = next((idx for idx, header in enumerate(headers) if pattern.fullmatch(header)), None)
        if found is None:
            # Handle common headers such as “X coordinate (day)” while keeping
            # the axis letter unambiguous and isolated from arbitrary words.
            found = next((idx for idx, header in enumerate(headers)
                          if re.search(rf"(?:^|\s){axis}(?:$|\s| coordinate| координат)", header)), None)
        if found is None:
            return {}
        axis_indices[axis] = found

    points: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, (list, tuple)):
            continue
        if max(axis_indices.values()) >= len(row):
            continue
        xyz = {axis: _number_for_render(row[column_index]) for axis, column_index in axis_indices.items()}
        if any(value is None for value in xyz.values()):
            continue
        point: dict[str, Any] = {axis: value for axis, value in xyz.items()}
        label_index = next((idx for idx, header in enumerate(headers)
                            if idx not in axis_indices.values()
                            and re.search(r"(?:^|\s)(?:точка|point|метка|название|name|label|объект|object)(?:$|\s)", header)), None)
        if label_index is not None and label_index < len(row) and str(row[label_index] or "").strip():
            point["label"] = str(row[label_index]).strip()
        elif row_index < len(rows):
            point["label"] = str(row_index + 1)
        points.append(point)
    if len(points) < 2:
        return {}

    x_title = str(columns[axis_indices["x"]])
    y_title = str(columns[axis_indices["y"]])
    z_title = str(columns[axis_indices["z"]])
    title = str(table.get("title") or "Трёхмерный график по координатам X, Y, Z")
    # Discrete rows are points, not a surface grid. scatter3d is the accurate
    # renderer and preserves the third coordinate all the way into GraphBlock.
    return {
        "representation": "scatter3d",
        "graph_type": "scatter3d",
        "chart_type": "scatter3d",
        "dimensions": 3,
        "three_d": True,
        "title": title,
        "description": "Трёхмерные точки построены по значениям X, Y и Z из таблицы.",
        "series": [{"label": title, "type": "points", "points": deepcopy(points)}],
        "points": deepcopy(points),
        "x_values": [point["x"] for point in points],
        "y_values": [point["y"] for point in points],
        "z_values": [point["z"] for point in points],
        "x_axis": {"title": x_title},
        "y_axis": {"title": y_title},
        "z_axis": {"title": z_title},
        "data_table": {"columns": list(columns), "rows": deepcopy(rows)},
        "graph_policy": deepcopy(policy),
        "source": "same_turn_markdown_table_xyz",
    }


def _graph_payload_has_z_coordinates(payload: Dict[str, Any]) -> bool:
    """True when a graph payload contains actual per-point z values."""
    if not isinstance(payload, dict):
        return False
    candidates: list[Any] = [payload.get("points")]
    for series in payload.get("series") or payload.get("datasets") or payload.get("traces") or []:
        if isinstance(series, dict):
            candidates.append(series.get("points"))
    for points in candidates:
        if isinstance(points, list) and any(
            isinstance(point, dict) and _number_for_render(point.get("z")) is not None
            for point in points
        ):
            return True
    return False


def _graph_payload_from_table(table: Dict[str, Any]) -> Dict[str, Any]:
    columns = table.get("columns") or table.get("headers") or []
    rows = table.get("rows") or []
    if not isinstance(columns, list) or len(columns) < 2 or not isinstance(rows, list) or len(rows) < 2:
        return {}
    # Choose the first column as x and first numeric column with >=2 values as y.
    x_index = 0
    best_y = None
    best_values: List[float] = []
    for col_index in range(1, len(columns)):
        values = [_number_for_render(row[col_index] if isinstance(row, (list, tuple)) and len(row) > col_index else None) for row in rows]
        valid = [value for value in values if value is not None]
        if len(valid) >= 2:
            best_y = col_index
            best_values = values
            break
    if best_y is None:
        return {}
    points = []
    x_values = []
    y_values = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, (list, tuple)) or len(row) <= best_y:
            continue
        y_value = _number_for_render(row[best_y])
        if y_value is None:
            continue
        x_raw = row[x_index] if len(row) > x_index else row_index + 1
        x_num = _number_for_render(x_raw)
        x_value = x_num if x_num is not None else str(x_raw)
        points.append({"x": x_value, "y": y_value})
        x_values.append(x_value)
        y_values.append(y_value)
    if len(points) < 2:
        return {}
    return {
        "representation": "line",
        "chart_type": "line",
        "title": str(table.get("title") or "Graph"),
        "series": [{"label": str(columns[best_y]), "type": "points", "points": points, "x": x_values, "y": y_values}],
        "points": points,
        "x_values": x_values,
        "y_values": y_values,
        "x_axis": {"title": str(columns[x_index])},
        "y_axis": {"title": str(columns[best_y])},
        "data_table": {"columns": list(columns), "rows": deepcopy(rows)},
        "source": "same_turn_markdown_table",
    }


def _mermaid_payload(source: str) -> Dict[str, Any]:
    """Parse concrete Mermaid flowcharts and grouped visual compositions.

    A set of explicitly declared nodes inside a Mermaid subgraph is a drawable
    composition even when the source contains no arrows. Edges are preserved when
    supplied, but are never invented just to make a diagram pass validation.
    """
    text = str(source or "").strip()
    direction_match = re.search(r"(?im)^\s*(?:flowchart|graph)\s+(LR|RL|TB|TD|BT)\b", text)
    if not direction_match:
        return {}
    node_labels: Dict[str, str] = {}
    edges: List[Dict[str, Any]] = []
    groups: List[Dict[str, Any]] = []
    current_group: Dict[str, Any] | None = None
    node_group: Dict[str, str] = {}
    # Node declaration/edge forms: A[Label] --> B[Label], A --> B.
    edge_pattern = re.compile(r"([A-Za-z0-9_-]+)(?:\[([^\]]+)\]|\(([^\)]+)\))?\s*(?:-->|---|-.+?\.->|==>|--\s*[^-]+\s*-->)\s*([A-Za-z0-9_-]+)(?:\[([^\]]+)\]|\(([^\)]+)\))?")
    subgraph_pattern = re.compile(r"^subgraph\s+([A-Za-z0-9_-]+)(?:\s*\[\s*\"([^\"]+)\"\s*\]|\s*\[([^\]]+)\])?\s*$", re.IGNORECASE)
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.lower().startswith(("flowchart", "graph", "%%")):
            continue
        group_match = subgraph_pattern.match(line)
        if group_match:
            group_id, quoted_title, plain_title = group_match.groups()
            current_group = {"id": group_id, "label": (quoted_title or plain_title or group_id).strip(), "nodes": []}
            groups.append(current_group)
            continue
        if line.lower() == "end":
            current_group = None
            continue
        match = edge_pattern.search(line)
        if match:
            left, left_square, left_round, right, right_square, right_round = match.groups()
            node_labels.setdefault(left, (left_square or left_round or left).replace("<br/>", " ").replace("<br>", " ").strip())
            node_labels.setdefault(right, (right_square or right_round or right).replace("<br/>", " ").replace("<br>", " ").strip())
            if current_group:
                node_group.setdefault(left, str(current_group["id"]))
                node_group.setdefault(right, str(current_group["id"]))
                for node_id in (left, right):
                    if node_id not in current_group["nodes"]:
                        current_group["nodes"].append(node_id)
            edges.append({"from": left, "to": right})
            continue
        declaration = re.match(r"^([A-Za-z0-9_-]+)(?:\[([^\]]+)\]|\(([^\)]+)\))$", line)
        if declaration:
            node_id, square, round_label = declaration.groups()
            node_labels.setdefault(node_id, (square or round_label or node_id).replace("<br/>", " ").replace("<br>", " ").strip())
            if current_group:
                node_group.setdefault(node_id, str(current_group["id"]))
                if node_id not in current_group["nodes"]:
                    current_group["nodes"].append(node_id)
    nodes = []
    for key, value in node_labels.items():
        item = {"id": key, "label": value}
        if key in node_group:
            item["group_id"] = node_group[key]
        nodes.append(item)
    # A standalone `flowchart LR` is an empty shell, not a drawable payload.
    # Explicit nodes are enough for an unconnected composition, e.g. objects laid
    # out in a lab illustration; a connected process retains its edges as given.
    if len(nodes) < 2:
        return {}
    result = {
        "source": text,
        "mermaid": text,
        "format": "mermaid",
        "representation": "schematic",
        "nodes": nodes,
        "edges": edges,
        "direction": direction_match.group(1),
        "layout": {"direction": direction_match.group(1), "rankdir": direction_match.group(1), "responsive": True},
    }
    if groups:
        result["groups"] = groups
        result.setdefault("title", str(groups[0].get("label") or "Схема"))
    return result


def _experiment_steps_payload(answer: str) -> Dict[str, Any]:
    """Convert explicit experiment/procedure steps in the answer into a diagram.

    This only restructures steps already written in the answer; it does not add
    scientific steps, measurements, or claims.
    """
    lines = str(answer or "").splitlines()
    section_pattern = re.compile(r"(?:опыт|эксперимент|ход\s+работ|процедур|experiment|procedure)", re.IGNORECASE)
    item_pattern = re.compile(r"^\s*(?:\d{1,2}[.)]|[-*•])\s+(.{3,180})\s*$")
    for index, line in enumerate(lines):
        if not section_pattern.search(line):
            continue
        items: List[str] = []
        started = False
        for candidate in lines[index + 1:index + 18]:
            match = item_pattern.match(candidate)
            if match:
                items.append(re.sub(r"\s+", " ", match.group(1)).strip())
                started = True
                if len(items) >= 8:
                    break
            elif started and not candidate.strip():
                break
            elif started and re.match(r"^\s*#{1,6}\s+", candidate):
                break
            elif started and candidate.strip() and not candidate.startswith(("  ", "\t")):
                break
        if len(items) >= 2:
            nodes = [{"id": f"step_{n+1}", "label": label} for n, label in enumerate(items)]
            edges = [{"from": f"step_{n+1}", "to": f"step_{n+2}"} for n in range(len(items)-1)]
            return {"nodes": nodes, "edges": edges, "direction": "TB", "layout": "hierarchical", "source": "same_turn_experiment_steps"}
    return {}


def _section_outline_rows(answer: str, limit: int = 10) -> Dict[str, Any]:
    """Extract a grounded section outline from this turn for table/network views.

    Only headings and the first visible paragraph below them are reused. This is
    a formatting transform over the current answer, not a knowledge-generation
    step and not a lookup into dialogue history.
    """
    lines = str(answer or "").replace("\r", "").split("\n")
    headings: List[Dict[str, str]] = []
    current: Dict[str, Any] | None = None
    in_fence = False
    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not line:
            continue
        match = re.match(r"^#{1,4}\s+(.+?)\s*$", line)
        if match:
            if current:
                summary = re.sub(r"\s+", " ", " ".join(current.pop("_body", []))).strip()
                current["summary"] = summary[:260]
                headings.append(current)
            current = {"heading": re.sub(r"[*_`]", "", match.group(1)).strip(), "_body": []}
            continue
        if current is None:
            continue
        if line.startswith(("|", "!", ">", "<")):
            continue
        # Ignore repeated decorative separators and preserve only answer prose.
        if re.fullmatch(r"[-*_]{3,}", line):
            continue
        current["_body"].append(line)
    if current:
        summary = re.sub(r"\s+", " ", " ".join(current.pop("_body", []))).strip()
        current["summary"] = summary[:260]
        headings.append(current)

    if not headings:
        return {}
    title = headings[0].get("heading", "")
    # A single top-level title with no content is the graph root, not a data row.
    rows = [item for item in headings if item.get("summary")]
    if len(rows) < 2:
        return {"title": title, "sections": rows} if rows else {}
    rows = rows[:max(2, min(12, int(limit)))]
    return {"title": title, "sections": rows}


def _section_outline_table(outline: Dict[str, Any]) -> Dict[str, Any]:
    """Build a two-column table from visible answer headings and their summaries."""
    sections = outline.get("sections") if isinstance(outline, dict) else []
    if not isinstance(sections, list) or len(sections) < 2:
        return {}
    rows = [
        [str(item.get("heading") or "Раздел")[:120], str(item.get("summary") or "")[:240]]
        for item in sections if isinstance(item, dict) and str(item.get("heading") or "").strip() and str(item.get("summary") or "").strip()
    ]
    if len(rows) < 2:
        return {}
    return {
        "title": str(outline.get("title") or "Структура ответа"),
        "columns": ["Раздел", "Краткое содержание"],
        "headers": ["Раздел", "Краткое содержание"],
        "rows": rows,
        "source": "same_turn_answer_section_outline",
    }


def _section_outline_graph(outline: Dict[str, Any]) -> Dict[str, Any]:
    """Build a non-numeric concept map from the answer's own section headings."""
    sections = outline.get("sections") if isinstance(outline, dict) else []
    if not isinstance(sections, list) or len(sections) < 2:
        return {}
    title = str(outline.get("title") or "Структура ответа").strip()[:140]
    nodes = [{"id": "answer_topic", "label": title or "Тема ответа", "level": 0}]
    edges = []
    for index, item in enumerate(sections[:10], 1):
        if not isinstance(item, dict):
            continue
        label = str(item.get("heading") or "").strip()
        if not label:
            continue
        node_id = f"answer_section_{index}"
        nodes.append({"id": node_id, "label": label[:100], "level": 1, "description": str(item.get("summary") or "")[:220]})
        edges.append({"from": "answer_topic", "to": node_id, "label": "содержит раздел", "relation": "section_of"})
    if len(nodes) < 3 or not edges:
        return {}
    return {
        "representation": "network",
        "graph_type": "network",
        "chart_type": "network",
        "title": f"Карта разделов: {title}"[:180],
        "description": "Связи отражают только структуру текущего ответа, а не количественные измерения.",
        "nodes": nodes,
        "edges": edges,
        "source": "same_turn_answer_section_outline",
    }


def _section_outline_diagram(outline: Dict[str, Any]) -> Dict[str, Any]:
    """Build a structural (not causal) diagram from the current answer headings."""
    sections = outline.get("sections") if isinstance(outline, dict) else []
    if not isinstance(sections, list) or len(sections) < 2:
        return {}
    title = str(outline.get("title") or "Структура ответа").strip()[:120]
    nodes = [{"id": "answer_start", "label": title or "Тема", "level": 0}]
    edges: List[Dict[str, Any]] = []
    for index, item in enumerate(sections[:10], 1):
        if not isinstance(item, dict):
            continue
        heading = str(item.get("heading") or "").strip()
        if not heading:
            continue
        node_id = f"outline_section_{index}"
        nodes.append({
            "id": node_id,
            "label": heading[:90],
            "level": 1,
            "description": str(item.get("summary") or "")[:180],
        })
        edges.append({
            "from": "answer_start",
            "to": node_id,
            "label": "раздел ответа",
            "relation": "outline_membership",
        })
    if len(nodes) < 3 or not edges:
        return {}
    return {
        "representation": "diagram",
        "layout": "hierarchical",
        "direction": "TB",
        "title": f"Структурная схема: {title}"[:160],
        "description": "Показан порядок и состав разделов ответа; связи не обозначают причинно-следственные зависимости.",
        "nodes": nodes,
        "edges": edges,
        "source": "same_turn_answer_section_outline",
    }


def _payload_for_render_block(block: Dict[str, Any], block_type: str) -> Dict[str, Any]:
    """Merge structured payload sources with the explicit block payload winning.

    A signal may carry the table rows/code/URL while the envelope carries identity
    metadata. Returning only the first dictionary discarded complementary fields.
    """
    candidates: List[Any] = []
    artifact = block.get("artifact")
    if isinstance(artifact, dict):
        artifact_data = artifact.get("data")
        if isinstance(artifact_data, dict):
            candidates.append(artifact_data.get("payload"))
        candidates.extend((artifact.get("payload"), artifact_data))
    presentation = block.get("presentation")
    if isinstance(presentation, dict):
        payload_contract = presentation.get("payload_contract")
        if isinstance(payload_contract, dict):
            candidates.append(payload_contract.get("payload"))
    for key in ("signal", "room_signal", "render_signal", "presentation_signal"):
        envelope = block.get(key)
        if isinstance(envelope, dict):
            candidates.append(envelope.get("payload"))
            nested_presentation = envelope.get("presentation")
            if isinstance(nested_presentation, dict):
                nested_contract = nested_presentation.get("payload_contract")
                if isinstance(nested_contract, dict):
                    candidates.append(nested_contract.get("payload"))
    candidates.extend((
        block.get("data"), block.get("artifact_payload"), block.get("table"),
        block.get("graph"), block.get("diagram"), block.get("link"),
        block.get("content") if isinstance(block.get("content"), dict) else None,
        block.get("payload"),
    ))
    merged: Dict[str, Any] = {}
    for candidate in candidates:
        if isinstance(candidate, dict):
            merged.update({key: deepcopy(value) for key, value in candidate.items() if value not in (None, "", [], {})})
    # Normalize common provider aliases before validation. The Web renderers
    # consume typed canonical keys, so payload data must not be rejected just
    # because a provider called it `source`, `mermaid`, or Markdown links.
    if block_type == "code" and not str(merged.get("code") or merged.get("content") or "").strip():
        source_code = merged.get("source") or block.get("source")
        if isinstance(source_code, str) and source_code.strip():
            merged["code"] = source_code
    if block_type == "link":
        link_markdown = str(merged.get("markdown") or block.get("markdown") or "")
        if link_markdown:
            found_links = [
                {"title": label.strip(), "url": url.rstrip(".,;:!?"), "href": url.rstrip(".,;:!?" )}
                for label, url in re.findall(r"\[([^\]]{1,300})\]\((https?://[^\s)]+)\)", link_markdown, re.IGNORECASE)
            ]
            if found_links:
                existing = merged.get("links") if isinstance(merged.get("links"), list) else []
                merged["links"] = [*existing, *found_links]
        if isinstance(merged.get("links"), list):
            merged["links"] = [
                ({"url": item, "href": item} if isinstance(item, str) and item.strip().lower().startswith(("http://", "https://")) else item)
                for item in merged["links"]
            ]
    if block_type == "diagram" and not (merged.get("svg") or merged.get("svg_payload") or merged.get("drawing") or merged.get("nodes")):
        # Mermaid source is frequently carried as a plain string on the block
        # envelope, not inside `payload`. Read it before generic aliases are merged
        # so the canonical parser can convert it to drawable node/edge data.
        mermaid_source = str(
            merged.get("mermaid") or merged.get("source") or block.get("mermaid")
            or block.get("source") or block.get("code") or block.get("content")
            or block.get("text") or block.get("markdown") or ""
        ).strip()
        if mermaid_source and re.search(r"(?im)^\s*(?:flowchart|graph|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|mindmap|timeline)\b", mermaid_source):
            parsed_mermaid = _mermaid_payload(mermaid_source)
            if isinstance(parsed_mermaid, dict) and parsed_mermaid:
                merged.update(parsed_mermaid)
    # Some older render blocks placed transfer data directly on the envelope.
    # Preserve actual content/URLs but never treat a filename alone as file data.
    for key in ("file_data_uri", "data_uri", "file_base64", "base64", "download_url", "file_url", "source", "content", "text", "markdown", "latex", "formula", "equation", "expression", "math"):
        value = block.get(key)
        if key not in merged and value not in (None, "", [], {}):
            merged[key] = deepcopy(value)

    # FormulaRenderer validates canonical math fields, not the transport's generic
    # `content` / `text` aliases. Promote an explicitly typed formula block without
    # changing the mathematical expression; otherwise SceneContract can silently
    # discard a real formula and leave only its surrounding prose.
    if block_type == "formula":
        expression = next((
            str(merged.get(key) or "").strip()
            for key in ("formula", "latex", "equation", "expression", "math", "content", "text", "display_text", "markdown")
            if str(merged.get(key) or "").strip()
        ), "")
        if expression and len(expression) <= 4000:
            merged.setdefault("formula", expression)
            merged.setdefault("latex", expression)
            if not isinstance(merged.get("formulas"), list) or not merged.get("formulas"):
                merged["formulas"] = [expression]

    # Accept a direct Mermaid/SVG source on a diagram's generic text aliases.
    # Diagram payload parsing happens before this adapter in older responses, so
    # repeat it after aliases are normalized to avoid dropping valid diagrams.
    if block_type == "diagram" and not (merged.get("svg") or merged.get("svg_payload") or merged.get("drawing") or merged.get("nodes")):
        direct_source = str(merged.get("mermaid") or merged.get("source") or merged.get("content") or merged.get("text") or merged.get("markdown") or "").strip()
        if direct_source.lstrip().lower().startswith("<svg"):
            merged["svg"] = direct_source
        elif direct_source and re.search(r"(?im)^\s*(?:flowchart|graph|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|mindmap|timeline)\b", direct_source):
            parsed_mermaid = _mermaid_payload(direct_source)
            if isinstance(parsed_mermaid, dict) and parsed_mermaid:
                merged.update(parsed_mermaid)
    if merged:
        return merged
    keys = (WEB_RENDERER_REGISTRY.get(block_type) or {}).get("payload_keys") or []
    fallback = {key: deepcopy(block[key]) for key in keys if key in block and block[key] not in (None, "", [], {})}
    if block_type == "code" and not fallback.get("code") and isinstance(block.get("source"), str):
        fallback["code"] = block["source"]
    return fallback


def _has_render_payload(block_type: str, payload: Dict[str, Any], block: Dict[str, Any] | None = None) -> bool:
    p = payload if isinstance(payload, dict) else {}
    if block_type == "table":
        cols = p.get("columns") or p.get("headers")
        rows = p.get("rows") or p.get("data")
        return isinstance(cols, list) and bool(cols) and isinstance(rows, list) and bool(rows)
    if block_type in {"graph", "knowledge_graph", "relation_graph", "relations"}:
        series = p.get("series") or p.get("datasets") or p.get("traces")
        nested_scene = p.get("scene") if isinstance(p.get("scene"), dict) else {}
        nested_geometry = p.get("geometry") if isinstance(p.get("geometry"), dict) else {}
        nested_surface = p.get("surface") if isinstance(p.get("surface"), dict) else {}
        has_nested_surface_expression = any(
            str(candidate or "").strip()
            for candidate in (
                nested_surface.get("surface_function"), nested_surface.get("z_function"),
                nested_surface.get("expression"), nested_surface.get("formula"),
                nested_surface.get("function"),
            )
        )
        has_nested_3d_objects = any(
            isinstance(candidate, list) and bool(candidate)
            for candidate in (
                nested_scene.get("objects"), nested_geometry.get("objects"),
                nested_geometry.get("spheres"),
            )
        )
        representation = str(p.get("representation") or p.get("graph_type") or p.get("chart_type") or "").strip().lower().replace("-", "_").replace(" ", "_")
        explicit_surface_expression = representation in {"surface3d", "surface_3d", "3d_surface", "surface", "mesh3d", "mesh_3d", "3d"} and bool(
            p.get("equation") or p.get("expression") or p.get("formula") or p.get("fn")
        )
        return bool(
            (isinstance(series, list) and any(isinstance(item, dict) and (item.get("points") or item.get("x") or item.get("y") or item.get("data") or item.get("values")) for item in series))
            or (isinstance(p.get("x_values"), list) and isinstance(p.get("y_values"), list) and min(len(p["x_values"]), len(p["y_values"])) >= 2)
            or (isinstance(p.get("x"), list) and isinstance(p.get("y"), list) and min(len(p["x"]), len(p["y"])) >= 2)
            or (isinstance(p.get("points"), list) and len(p["points"]) >= 2)
            or (isinstance(p.get("nodes"), list) and bool(p["nodes"]) and isinstance(p.get("edges"), list) and bool(p.get("edges")))
            or bool(p.get("matrix") or p.get("data_table") or p.get("surface_grid") or p.get("z_values"))
            or bool(p.get("surface_function") or p.get("z_function") or p.get("z_expression"))
            or explicit_surface_expression
            or (
                representation in {"function", "function2d", "function_2d", "line", "line_chart", "scatter", "2d"}
                and bool(p.get("equation") or p.get("expression") or p.get("fn") or p.get("function") or p.get("function_expression"))
            )
            or has_nested_surface_expression
            or has_nested_3d_objects
            or bool(p.get("objects_3d") or p.get("spheres") or p.get("objects") or p.get("shapes") or p.get("meshes"))
        )
    if block_type == "diagram":
        diagram_nodes = p.get("nodes") or p.get("components") or p.get("vertices")
        # Treat an explicit edge list (including an empty one) as structural
        # evidence that the producer supplied a diagram rather than an empty shell.
        has_explicit_edges = any(key in p and isinstance(p.get(key), list) for key in ("edges", "connections", "relations"))
        has_grouped_nodes = bool(p.get("groups") or p.get("subgraphs"))
        has_mermaid_structure = str(p.get("format") or "").strip().lower() == "mermaid" and str(p.get("source") or p.get("mermaid") or "").strip()
        return bool(
            str(p.get("svg") or p.get("svg_payload") or p.get("drawing") or "").strip()
            or (isinstance(diagram_nodes, list) and len(diagram_nodes) >= 2 and (
                (has_explicit_edges and bool(p.get("edges") or p.get("connections") or p.get("relations")))
                or (has_explicit_edges and (has_grouped_nodes or has_mermaid_structure or bool(p.get("layout"))))
            ))
            or (isinstance(p.get("elements"), list) and bool(p["elements"]))
            or (isinstance(p.get("shapes"), list) and bool(p["shapes"]))
        )
    if block_type in {"image", "gallery"}:
        images = p.get("images") or p.get("items") or p.get("gallery") or p.get("sources")
        if isinstance(images, list):
            return any((isinstance(item, str) and item.strip()) or (isinstance(item, dict) and any(str(item.get(key) or "").strip() for key in ("src", "url", "image", "asset_url", "image_data_uri", "image_base64", "base64"))) for item in images)
        return any(str(p.get(key) or "").strip() for key in ("src", "url", "image", "image_data_uri", "image_base64", "base64"))
    if block_type == "formula":
        return bool(str(p.get("formula") or p.get("latex") or p.get("equation") or p.get("expression") or p.get("markdown") or "").strip() or (isinstance(p.get("formulas"), list) and bool(p["formulas"])) or (isinstance(p.get("latex_formulas"), list) and bool(p["latex_formulas"])))
    if block_type == "code":
        return bool(str(p.get("code") or p.get("content") or (block or {}).get("code") or "").strip())
    if block_type == "link":
        links = p.get("links")
        has_link_item = isinstance(links, list) and any(
            (isinstance(item, str) and item.strip().lower().startswith(("http://", "https://")))
            or (isinstance(item, dict) and str(item.get("url") or item.get("href") or "").strip().lower().startswith(("http://", "https://")))
            for item in links
        )
        markdown_urls = re.findall(r"https?://[^\s)<>]+", str(p.get("markdown") or ""), re.IGNORECASE)
        return bool(str(p.get("url") or p.get("href") or "").strip() or has_link_item or markdown_urls)
    if block_type == "file":
        # A file renderer needs a real content/transfer reference, not just an
        # empty filename shell. Inline text files and encoded files are valid.
        return bool(any(
            str(p.get(key) or (block or {}).get(key) or "").strip()
            for key in ("url", "href", "file_url", "download_url", "file_data_uri", "data_uri", "file_base64", "base64", "content", "code")
        ))
    return bool(p)


def _canonicalize_premium_3d_payload(payload: Dict[str, Any], *, explicit_3d_type: bool = False) -> Dict[str, Any]:
    """Adapt common structured scene spellings to GraphBlock's lossless 3D schema.

    This adapter only adds canonical aliases; it never estimates or changes source
    coordinates, masses, equations, orbit points, or supplied time values.
    """
    if not isinstance(payload, dict):
        return payload
    p = dict(payload)
    scene = p.get("scene") if isinstance(p.get("scene"), dict) else {}
    geometry = p.get("geometry") if isinstance(p.get("geometry"), dict) else {}

    raw_representation = str(p.get("representation") or p.get("graph_type") or p.get("chart_type") or "").strip().lower().replace("-", "_").replace(" ", "_")
    known_3d = {
        "3d", "3d_scene", "scene3d", "scene_3d", "3d_graph", "graph3d", "graph_3d",
        "surface3d", "surface_3d", "3d_surface", "surface", "scatter3d", "scatter_3d",
        "3d_scatter", "mesh3d", "mesh_3d", "bar3d", "plot3d", "plot_3d", "spacetime_curvature",
    }
    if explicit_3d_type and raw_representation not in known_3d:
        p["representation"] = "scene3d"
        p.setdefault("dimensions", 3)
    elif raw_representation in {"3d_scene", "scene_3d", "3d_graph", "graph3d", "graph_3d", "plot3d", "plot_3d"}:
        p["representation"] = "scene3d"
        p.setdefault("dimensions", 3)

    # A scene may expose all bodies in a single list, or separate planet/moon
    # lists. Merge those known spatial collections and remove only exact duplicates.
    source_groups = [
        ("objects_3d", p.get("objects_3d")), ("spheres", p.get("spheres")),
        ("celestial_bodies", p.get("celestial_bodies")), ("bodies", p.get("bodies")),
        ("planets", p.get("planets")), ("satellites", p.get("satellites")),
        ("moons", p.get("moons")), ("comets", p.get("comets")),
        ("objects", p.get("objects")), ("shapes", p.get("shapes")), ("primitives", p.get("primitives")),
        ("meshes", p.get("meshes")), ("scene.objects_3d", scene.get("objects_3d")),
        ("scene.objects", scene.get("objects")), ("scene.bodies", scene.get("bodies")),
        ("scene.celestial_bodies", scene.get("celestial_bodies")), ("scene.planets", scene.get("planets")),
        ("scene.satellites", scene.get("satellites")), ("scene.moons", scene.get("moons")),
        ("scene.comets", scene.get("comets")), ("scene.shapes", scene.get("shapes")),
        ("scene.primitives", scene.get("primitives")), ("scene.meshes", scene.get("meshes")),
        ("geometry.objects", geometry.get("objects")), ("geometry.spheres", geometry.get("spheres")),
        ("geometry.bodies", geometry.get("bodies")), ("geometry.shapes", geometry.get("shapes")),
        ("geometry.primitives", geometry.get("primitives")), ("geometry.meshes", geometry.get("meshes")),
    ]
    merged_objects = []
    seen_object_keys = {}
    generic_body_labels = {"object", "body", "planet", "moon", "satellite", "natural satellite", "celestial body", "comet", "sphere", "unknown"}
    def _has_scene_value(value: Any) -> bool:
        return value is not None and value != "" and value != [] and value != {}
    for group_name, values in source_groups:
        if isinstance(values, dict):
            values = list(values.values())
        if not isinstance(values, list):
            continue
        group_hint = group_name.rsplit(".", 1)[-1].rstrip("s")
        for index, value in enumerate(values):
            if not isinstance(value, dict):
                # Strings can be labels in body lists; do not turn arbitrary text
                # into coordinates, but preserve them as a named spherical body.
                if not isinstance(value, str) or not value.strip():
                    continue
                item = {"label": value.strip(), "name": value.strip()}
            else:
                item = dict(value)
            label = str(item.get("label") or item.get("name") or item.get("title") or item.get("id") or "").strip()
            coords = item.get("position") if isinstance(item.get("position"), dict) else item.get("center") if isinstance(item.get("center"), dict) else {}
            xyz = tuple(item.get(axis, coords.get(axis, "")) for axis in ("x", "y", "z"))
            stable_id = str(item.get("id") or item.get("key") or "").strip().lower()
            # Prefer a stable ID, then a specific body name. Generic labels
            # ("satellite", "moon", etc.) retain coordinate/source identity so
            # several unnamed bodies remain distinct.
            normalized_label = label.lower()
            dedupe_key = (
                ("id", stable_id) if stable_id
                else ("label", normalized_label) if normalized_label and normalized_label not in generic_body_labels
                else ("value", normalized_label, tuple(str(v) for v in xyz), str(item.get("shape") or item.get("type") or group_hint).lower())
            )
            kind = str(item.get("shape") or item.get("geometry_type") or item.get("object_type") or item.get("type") or group_hint).strip().lower().replace("-", "_").replace(" ", "_")
            if dedupe_key in seen_object_keys:
                existing_index = seen_object_keys[dedupe_key]
                existing = merged_objects[existing_index]
                merged = dict(item)
                # Existing earlier fields are authoritative when populated;
                # secondary collections enrich missing coordinates/metadata.
                for field_name, field_value in existing.items():
                    if _has_scene_value(field_value):
                        if field_name in {"position", "center", "dimensions", "size_3d", "velocity", "velocity_vector"} and isinstance(field_value, dict):
                            later_nested = merged.get(field_name) if isinstance(merged.get(field_name), dict) else {}
                            merged[field_name] = {**later_nested, **{key: value for key, value in field_value.items() if _has_scene_value(value)}}
                        else:
                            merged[field_name] = field_value
                merged_objects[existing_index] = merged
                continue
            seen_object_keys[dedupe_key] = len(merged_objects)
            item.setdefault("label", label or f"{group_hint.title()} {len(merged_objects) + 1}")
            # Do not replace meaningful primitive geometry. Celestial role names
            # become spheres at the renderer boundary; comets retain a tail type.
            if not item.get("shape"):
                if kind in {"planet", "moon", "satellite", "natural_satellite", "jovian_moon", "star", "sun", "asteroid", "dwarf_planet", "celestial_body", "body", "comet"}:
                    item["shape"] = "comet" if kind == "comet" else "sphere"
                elif kind in {"sphere", "ball", "cube", "box", "cylinder", "cone", "pyramid", "triangle", "funnel", "torus", "ringed_planet", "ringed_sphere"}:
                    item["shape"] = "sphere" if kind in {"ball", "ringed_planet", "ringed_sphere"} else kind
            merged_objects.append(item)

    if merged_objects:
        p["objects_3d"] = merged_objects
        p.setdefault("dimensions", 3)
        if not str(p.get("representation") or "").strip():
            p["representation"] = "scene3d"

    # Promote nested scene collections to the stable top-level schema. Source
    # structures remain intact, so history and continuation can use their exact form.
    for canonical, candidates in {
        "orbits": (p.get("orbits"), p.get("orbit_paths"), p.get("orbital_motion"), scene.get("orbits"), scene.get("orbit_paths")),
        "trajectories": (p.get("trajectories"), p.get("paths"), scene.get("trajectories"), scene.get("paths")),
        "vectors": (p.get("vectors"), p.get("gravity_vectors"), p.get("field_vectors"), p.get("arrows"), scene.get("vectors"), scene.get("gravity_vectors")),
        "field_lines": (p.get("field_lines"), p.get("gravity_field_lines"), scene.get("field_lines")),
    }.items():
        if p.get(canonical) not in (None, "", [], {}):
            continue
        for candidate in candidates:
            if candidate not in (None, "", [], {}):
                p[canonical] = candidate
                break

    # Also accept common Plotly-like 3D traces. Keep the original `data`/`traces`
    # losslessly, while promoting a drawable canonical representation alongside it.
    # A small payload marker avoids duplicating these promoted values when this
    # adapter is called at both provider normalization and scene-contract stages.
    if not p.get("_april_3d_traces_normalized"):
        trace_groups = [p.get("data"), p.get("traces"), p.get("datasets")]
        trace_list = []
        for trace_group in trace_groups:
            if isinstance(trace_group, list):
                trace_list.extend(item for item in trace_group if isinstance(item, dict))
            elif isinstance(trace_group, dict):
                trace_list.extend(item for item in trace_group.values() if isinstance(item, dict))
        for trace_index, trace in enumerate(trace_list):
            trace_type = str(trace.get("type") or trace.get("kind") or trace.get("trace_type") or "").strip().lower().replace("-", "_")
            mode = str(trace.get("mode") or "markers").strip().lower()
            trace_name = str(trace.get("name") or trace.get("label") or f"Trace {trace_index + 1}")
            marker = trace.get("marker") if isinstance(trace.get("marker"), dict) else {}
            line_style = trace.get("line") if isinstance(trace.get("line"), dict) else {}
            x_values, y_values, z_values = trace.get("x"), trace.get("y"), trace.get("z")
            is_surface_trace = trace_type in {"surface", "surface3d", "surface_3d", "3d_surface", "mesh3d_surface"}
            if is_surface_trace and isinstance(z_values, list) and z_values and all(isinstance(row, list) for row in z_values):
                if not any(isinstance(p.get(key), list) and p.get(key) for key in ("surface_grid", "z_values", "matrix")):
                    p["surface_grid"] = z_values
                for axis, values in (("x", x_values), ("y", y_values)):
                    if isinstance(values, list) and values and all(_number_for_render(value) is not None for value in values):
                        low = min(float(_number_for_render(value)) for value in values)
                        high = max(float(_number_for_render(value)) for value in values)
                        if high > low:
                            p.setdefault(f"{axis}_domain", [low, high])
                p.setdefault("representation", "scene3d")
                p.setdefault("dimensions", 3)
                continue
            if not (isinstance(x_values, list) and isinstance(y_values, list) and isinstance(z_values, list)):
                continue
            count = min(len(x_values), len(y_values), len(z_values))
            coords = []
            for point_index in range(count):
                x = _number_for_render(x_values[point_index]); y = _number_for_render(y_values[point_index]); z = _number_for_render(z_values[point_index])
                if x is None or y is None or z is None:
                    continue
                point = {"x": float(x), "y": float(y), "z": float(z)}
                point_colors = marker.get("color")
                point_sizes = marker.get("size")
                if isinstance(point_colors, list) and point_index < len(point_colors): point["color"] = point_colors[point_index]
                elif isinstance(point_colors, str): point["color"] = point_colors
                if isinstance(point_sizes, list) and point_index < len(point_sizes): point["size"] = point_sizes[point_index]
                elif isinstance(point_sizes, (int, float)): point["size"] = point_sizes
                if trace.get("text") is not None:
                    labels = trace.get("text")
                    label = labels[point_index] if isinstance(labels, list) and point_index < len(labels) else labels if isinstance(labels, str) else None
                    if label not in (None, ""): point["label"] = str(label)
                coords.append(point)
            if not coords:
                continue
            p.setdefault("representation", "scene3d")
            p.setdefault("dimensions", 3)
            if trace_type in {"cone", "vector", "quiver", "streamtube"} and all(isinstance(trace.get(key), list) for key in ("u", "v", "w")):
                vector_rows = p.get("vectors") if isinstance(p.get("vectors"), list) else []
                for idx, point in enumerate(coords):
                    if idx >= min(len(trace["u"]), len(trace["v"]), len(trace["w"])): break
                    vector_rows.append({"start": {"x": point["x"], "y": point["y"], "z": point["z"]}, "vector": {"x": float(_number_for_render(trace["u"][idx]) or 0), "y": float(_number_for_render(trace["v"][idx]) or 0), "z": float(_number_for_render(trace["w"][idx]) or 0)}, "label": trace_name if idx == 0 else ""})
                p["vectors"] = vector_rows
                continue
            point_rows = p.get("points") if isinstance(p.get("points"), list) else []
            path_rows = p.get("paths") if isinstance(p.get("paths"), list) else []
            if trace_type in {"mesh3d", "mesh_3d", "triangulated_surface"}:
                point_rows.extend(coords)
                face_i, face_j, face_k = trace.get("i"), trace.get("j"), trace.get("k")
                if all(isinstance(values, list) for values in (face_i, face_j, face_k)):
                    for face_index in range(min(len(face_i), len(face_j), len(face_k), 2500)):
                        indices = [face_i[face_index], face_j[face_index], face_k[face_index]]
                        if all(isinstance(idx, int) and 0 <= idx < len(coords) for idx in indices):
                            path_rows.append({"id": f"{trace_name}-face-{face_index}", "kind": "mesh_edge", "color": marker.get("color", "rgba(125,211,252,0.62)"), "points": [coords[indices[0]], coords[indices[1]], coords[indices[2]], coords[indices[0]]]})
                p["points"] = point_rows
                if path_rows: p["paths"] = path_rows
                continue
            if "lines" in mode and len(coords) >= 2:
                path_rows.append({"id": str(trace.get("uid") or trace_name), "kind": "trajectory", "label": trace_name, "color": marker.get("color") or line_style.get("color") or "rgba(125,211,252,0.88)", "points": coords})
                p["paths"] = path_rows
            if "markers" in mode or trace_type in {"scatter3d", "scatter_3d", "scatter", "pointcloud", "isosurface", "volume"}:
                point_rows.extend(coords)
                p["points"] = point_rows
        if trace_list:
            p["_april_3d_traces_normalized"] = True

    field = p.get("field") if isinstance(p.get("field"), dict) else {}
    surface = p.get("surface") if isinstance(p.get("surface"), dict) else {}
    if not any(str(p.get(key) or "").strip() for key in ("surface_function", "z_function", "z_expression")):
        for candidate in (field.get("surface_function"), field.get("z_function"), field.get("expression"), field.get("formula"), field.get("function")):
            if isinstance(candidate, str) and candidate.strip():
                p["surface_function"] = candidate.strip()
                break
    if not p.get("title") and scene.get("title"):
        p["title"] = scene.get("title")
    if not p.get("description") and scene.get("description"):
        p["description"] = scene.get("description")
    return p


def _apply_premium_3d_visual_profile(payload: Dict[str, Any], answer: str = "") -> Dict[str, Any]:
    """Add Premium-only rendering hints to genuine 3D payloads without changing data.

    The hints are presentation metadata only: source coordinates, masses, surface
    values, and the canonical GraphBlock contract remain untouched. Free payloads
    are processed by the separate non-Premium artifact contract and never receive
    this marker.
    """
    if not isinstance(payload, dict) or not payload:
        return payload

    payload = _canonicalize_premium_3d_payload(payload)
    representation = str(
        payload.get("representation") or payload.get("graph_type") or payload.get("chart_type") or ""
    ).strip().lower().replace("-", "_").replace(" ", "_")
    three_d_representations = {
        "3d", "scene3d", "scene_3d", "3d_scene", "surface3d", "surface_3d",
        "3d_surface", "scatter3d", "scatter_3d", "3d_scatter", "mesh3d", "mesh_3d", "bar3d",
    }
    scene = payload.get("scene") if isinstance(payload.get("scene"), dict) else {}
    geometry = payload.get("geometry") if isinstance(payload.get("geometry"), dict) else {}
    surface = payload.get("surface") if isinstance(payload.get("surface"), dict) else {}
    object_groups = [
        payload.get("objects_3d"), payload.get("spheres"), payload.get("celestial_bodies"),
        payload.get("bodies"), payload.get("planets"), payload.get("satellites"),
        payload.get("moons"), payload.get("comets"), payload.get("objects"),
        payload.get("shapes"), payload.get("primitives"), payload.get("meshes"),
        scene.get("objects"), scene.get("bodies"), scene.get("celestial_bodies"),
        scene.get("satellites"), geometry.get("objects"), geometry.get("spheres"),
    ]
    canonical_objects = payload.get("objects_3d")
    if isinstance(canonical_objects, list) and canonical_objects:
        objects = [item for item in canonical_objects if isinstance(item, dict)]
    else:
        seen_profile_objects = set()
        objects = []
        for group in object_groups:
            if not isinstance(group, list):
                continue
            for item in group:
                if not isinstance(item, dict):
                    continue
                label_key = str(item.get("id") or item.get("key") or item.get("name") or item.get("label") or item.get("title") or "").strip().lower()
                position = item.get("position") if isinstance(item.get("position"), dict) else {}
                coords_key = tuple(str(item.get(axis, position.get(axis, ""))) for axis in ("x", "y", "z"))
                identity_key = (label_key, coords_key)
                if identity_key in seen_profile_objects:
                    continue
                seen_profile_objects.add(identity_key)
                objects.append(item)
    grid = payload.get("surface_grid") or payload.get("z_values") or payload.get("matrix")
    if not isinstance(grid, list):
        grid = surface.get("surface_grid") or surface.get("z_values") or surface.get("matrix") or surface.get("grid")
    has_surface_grid = isinstance(grid, list) and sum(
        1 for row in grid if isinstance(row, list) and sum(
            1 for value in row if isinstance(value, (int, float)) or (isinstance(value, str) and value.strip() and _number_for_render(value) is not None)
        ) >= 2
    ) >= 2
    point_groups = [payload.get("points"), payload.get("coordinates"), payload.get("data_points")]
    has_xyz_points = any(
        isinstance(item, (list, tuple)) and len(item) >= 3 and _number_for_render(item[2]) is not None
        or isinstance(item, dict) and any(_number_for_render(item.get(key)) is not None for key in ("z", "value_z"))
        for group in point_groups if isinstance(group, list) for item in group
    )
    has_surface_formula = any(
        isinstance(value, str) and value.strip()
        for value in (
            payload.get("surface_function"), payload.get("z_function"), payload.get("z_expression"),
            surface.get("surface_function"), surface.get("z_function"), surface.get("expression"),
            surface.get("formula"), surface.get("function"),
        )
    )
    is_3d = (
        representation in three_d_representations
        or payload.get("dimensions") == 3
        or payload.get("three_d") is True
        or (has_surface_grid and representation in three_d_representations)
        or has_xyz_points
        or (bool(objects) and (representation in three_d_representations or payload.get("dimensions") == 3 or payload.get("three_d") is True))
        or (has_surface_formula and representation in three_d_representations)
    )
    if not is_3d:
        return payload

    labels = []
    for item in objects:
        for key in ("label", "name", "title", "id", "type", "object_type"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                labels.append(value.strip())
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    scene_title = scene.get("title") if isinstance(scene.get("title"), str) else ""
    semantic_text = " ".join(str(value or "") for value in (
        answer, payload.get("title"), payload.get("description"), payload.get("topic"),
        payload.get("domain"), scene_title, metadata.get("topic"), metadata.get("domain"), *labels,
    )).lower()
    # Only enable the orbital animation for a scene that actually describes
    # planets/solar motion, or already provides explicit orbit data.
    mentions_planets = bool(re.search(r"planet|планет|юпитер|jupiter|сатурн|saturn|земл[яи]|earth|марс|mars|плутон|pluto", semantic_text))
    mentions_sun = bool(re.search(r"sun|solar|солнц|сонц", semantic_text))
    mentions_satellites = bool(re.search(r"satellite|moon|moons|спутник|спутник[аоим]?|луна|луны|галилеев", semantic_text))
    mentions_comet = bool(re.search(r"comet|комет|asteroid|астероид", semantic_text))
    mentions_gravity = bool(re.search(r"gravit|гравитац|тяготен|поле притяж", semantic_text))
    mentions_orbit = bool(re.search(r"orbit|орбит|вращени|траектор|trajectory|движени|летит|летящ", semantic_text))
    explicit_orbits = bool(payload.get("orbits") or payload.get("orbit_paths") or payload.get("orbital_motion"))
    has_multi_body_scene = len(objects) >= 2
    # Central-body scenes do not need to contain the Sun: Jupiter, Earth, a
    # comet's target, or any other labelled massive body can anchor the system.
    named_central_body = any(re.search(r"sun|sol|солнц|jupiter|юпитер|saturn|сатурн|earth|земл|mars|марс|planet|планет|central|центр", str(item.get("label") or item.get("name") or item.get("title") or ""), re.I) for item in objects)
    orbital_scene = explicit_orbits or (
        has_multi_body_scene and (mentions_orbit or mentions_satellites or (mentions_gravity and (mentions_planets or named_central_body)) or (mentions_comet and mentions_orbit))
    )
    supplied = payload.get("april_premium_3d")
    supplied = supplied if isinstance(supplied, dict) else {}
    minor_step = supplied.get("minor_grid_step", payload.get("grid_minor_step", payload.get("minor_grid_step", 0.1)))
    if _number_for_render(minor_step) is None or _number_for_render(minor_step) <= 0:
        minor_step = 0.1
    payload["april_premium_3d"] = {
        **supplied,
        "enabled": True,
        "show_elevated_grid": supplied.get("show_elevated_grid", True),
        "minor_grid_step": float(_number_for_render(minor_step) or 0.1),
        "vertical_exaggeration": supplied.get("vertical_exaggeration", 1.55),
        "animate_orbits": supplied.get("animate_orbits", orbital_scene),
        "draw_gravity_vectors": supplied.get("draw_gravity_vectors", (has_multi_body_scene and mentions_gravity) or orbital_scene),
        "show_gravity_waves": supplied.get("show_gravity_waves", has_multi_body_scene and mentions_gravity),
        "gravity_wave_amplitude": supplied.get("gravity_wave_amplitude", 0.22),
        "orbital_speed": supplied.get("orbital_speed", 0.34),
        "schema": "april.premium.3d.visual.v1",
        "presentation_only": True,
    }
    return payload


def prepare_render_blocks_for_room_dispatch(
    render_blocks: Any,
    answer: str = "",
    requested_outputs: Any = None,
    graph_policy: Any = None,
    current_request: str = "",
) -> List[Dict[str, Any]]:
    """Bind same-turn structured content to the canonical Web renderer types.

    This is a deterministic adapter, not a second route. It promotes a structure
    only when Interpretation requested it OR the same-turn answer already contains
    an unambiguous representation (Markdown table, fenced source code, Mermaid
    flowchart, delimited math, or literal URL). It never invents data or assets.
    """
    requested = _render_requested_outputs(requested_outputs)
    interpreted_graph_policy = deepcopy(graph_policy) if isinstance(graph_policy, dict) else {}
    source_answer = str(answer or "")
    section_outline = _section_outline_rows(source_answer)
    section_table_from_answer = _section_outline_table(section_outline)
    section_graph_from_answer = _section_outline_graph(section_outline)
    # The answer may already contain a structured representation even when the
    # user did not name its renderer explicitly. Reuse that evidence rather than
    # forcing a valid table/code/diagram to remain trapped inside a text block.
    table_from_answer = _markdown_table_payload(source_answer)
    mermaid_match = re.search(r"```\s*mermaid\s*\n([\s\S]*?)\n```", source_answer, re.IGNORECASE)
    mermaid_from_answer = mermaid_match.group(1).strip() if mermaid_match else ""
    diagram_from_answer = _mermaid_payload(mermaid_from_answer) if mermaid_from_answer else {}
    experiment_steps_from_answer = _experiment_steps_payload(source_answer) if "diagram" in requested else {}
    code_match = re.search(r"```([\w.+-]*)\s*\n([\s\S]*?)\n```", source_answer)
    if code_match and code_match.group(1).strip().lower() in {"mermaid", "diagram"}:
        code_match = None
    electrical_diagram_from_answer = _electrical_schematic_payload(source_answer) if "diagram" in requested else {}
    diagram_from_request = _geometry_diagram_payload_from_request(current_request, source_answer) if "diagram" in requested else {}
    if code_match and "graph" in requested and _is_ascii_line_chart_fence(code_match.group(2)):
        # This code fence is a visual representation of the graph, not source code.
        # Values are transferred to GraphBlock below; don't render it a second time.
        code_match = None
    if code_match and electrical_diagram_from_answer:
        # The ASCII sketch is source evidence for the diagram, not a separate code artifact.
        code_match = None
    formula_matches = re.findall(r"\\\[([\s\S]*?)\\\]|\\\((.*?)\\\)", source_answer)
    formulas_from_answer = [a or b for a, b in formula_matches if (a or b).strip()]
    # Also promote standalone equation lines that the Provider returned as plain
    # Markdown text. Values are extracted verbatim; no formula or measurement is invented.
    equation_pattern = re.compile(
        r"^\s*(?:[-*•]\s*)?([A-Za-zА-Яа-яΑ-ω][^\n]{0,100}?(?:=|≈|≠|≤|≥|∝|↔|→)[^\n]{1,150})\s*$"
    )
    for line in source_answer.splitlines():
        clean_line = re.sub(r"[`*_]", "", line).strip()
        equation_match = equation_pattern.match(clean_line)
        if equation_match:
            equation = equation_match.group(1).strip()
            # Avoid converting ordinary prose containing a comparison into math.
            if re.search(r"\d|[+*/^_]|\b(?:sin|cos|tan|sqrt|frac|mc|E|H|P|F|v|m|c)\b|[Α-ω]", equation, re.IGNORECASE):
                if equation not in formulas_from_answer:
                    formulas_from_answer.append(equation)
        if len(formulas_from_answer) >= 12:
            break
    for math_match in re.finditer(r"\$\$([\s\S]+?)\$\$|(?<!\$)\$([^$\n]{1,180})\$(?!\$)", source_answer):
        candidate = (math_match.group(1) or math_match.group(2) or "").strip()
        if candidate and candidate not in formulas_from_answer:
            formulas_from_answer.append(candidate)
    urls_from_answer = list(dict.fromkeys(re.findall(r"https?://[^\s<>\]\[()]+", source_answer, re.IGNORECASE)))
    # Explicit Markdown image embeds are already concrete visual evidence from
    # this answer. Promote them to the same gallery contract when the user asked
    # for source images, even if Provider omitted the separate gallery block.
    markdown_images = [
        {"src": str(url).rstrip(".,;:!?"), "url": str(url).rstrip(".,;:!?"),
         "alt": str(alt or "").strip(), "title": str(alt or "").strip(),
         "source_url": str(url).rstrip(".,;:!?")}
        for alt, url in re.findall(r"!\[([^\]]{0,180})\]\((https?://[^\s)]+)(?:\s+['\"][^)]*?)?\)", source_answer, re.IGNORECASE)
    ]
    source_blocks = [deepcopy(item) for item in render_blocks if isinstance(item, dict)] if isinstance(render_blocks, list) else []
    aliases = {
        "chart": "graph", "plot": "graph", "graph_data": "graph",
        "3d_scene": "graph", "scene3d": "graph", "scene_3d": "graph", "3d_graph": "graph", "graph3d": "graph", "graph_3d": "graph",
        "plot3d": "graph", "plot_3d": "graph", "scatter3d": "graph", "scatter_3d": "graph", "surface3d": "graph", "surface_3d": "graph",
        "3d_surface": "graph", "surface_plot": "graph", "surface_graph": "graph", "mesh3d": "graph", "mesh_3d": "graph", "wireframe": "graph",
        "table_data": "table",
        "math": "formula", "latex": "formula", "generated_image": "image", "image_artifact": "image",
        "hyperlink": "link", "links": "link", "link_list": "link", "linklist": "link", "source_links": "link", "file_card": "file",
        "image_gallery": "gallery", "gallery_block": "gallery", "sources_gallery": "gallery",
        "svg": "diagram", "schematic": "diagram", "experimental_diagram": "diagram",
        "mermaid": "diagram", "scene": "diagram", "layout": "diagram", "visual": "diagram", "renderer_scene": "diagram",
        "svgblock": "diagram", "arithmeticdiagram": "diagram", "arithmetic_diagram": "diagram",
        "generated_image": "image", "image_artifact": "image", "image_data": "image", "figure": "image",
        "message": "text", "message_text": "text",
    }
    prepared: List[Dict[str, Any]] = []
    for block in source_blocks:
        raw_type = _scene_block_type(block)
        block_type = aliases.get(raw_type, raw_type)
        explicit_3d_type = raw_type in {
            "3d_scene", "scene3d", "scene_3d", "3d_graph", "graph3d", "graph_3d",
            "plot3d", "plot_3d", "scatter3d", "scatter_3d", "surface3d", "surface_3d",
            "3d_surface", "surface_plot", "surface_graph", "mesh3d", "mesh_3d", "wireframe",
        }
        block["type"] = block_type
        block["artifact_type"] = str(block.get("artifact_type") or block_type)
        registration = get_web_renderer_registration(block_type)
        block.setdefault("renderer", registration.get("renderer") or "MessageTextBlock")
        block.setdefault("viewer", registration.get("viewer") or block.get("renderer") or "MessageTextBlock")
        payload = _payload_for_render_block(block, block_type)
        if block_type == "graph" and explicit_3d_type:
            payload.setdefault("representation", "scene3d")
            payload.setdefault("dimensions", 3)
        if block_type == "graph" and interpreted_graph_policy.get("mode") in {"explicit_3d", "inferred_spatial_scene", "structured_3d_data"}:
            preferred_3d = str(interpreted_graph_policy.get("preferred_representation") or "scene3d")
            has_structured_spatial_data = any(
                payload.get(key) not in (None, "", [], {})
                for key in ("objects_3d", "spheres", "bodies", "celestial_bodies", "planets", "satellites", "moons", "comets", "points", "coordinates", "data_points", "surface_grid", "z_values", "matrix", "surface_function", "z_function", "z_expression")
            ) or any(isinstance(payload.get(key), dict) and bool(payload[key]) for key in ("scene", "geometry", "surface"))
            if has_structured_spatial_data:
                payload.setdefault("representation", preferred_3d)
                payload.setdefault("dimensions", 3)
        if block_type == "graph":
            table_graph_3d = _graph_payload_from_table_3d(
                table_from_answer, interpreted_graph_policy, current_request
            ) if "graph" in requested and table_from_answer else {}
            if table_graph_3d and not _graph_payload_has_z_coordinates(payload):
                # The table is the lossless source of coordinates. Prefer it over a
                # provider's accidental 2D placeholder when the user explicitly asked
                # for 3D; do not overwrite a graph that already has real z values.
                for metadata_key in ("title", "description", "caption", "step_index", "step_title"):
                    if payload.get(metadata_key) not in (None, "", [], {}):
                        table_graph_3d.setdefault(metadata_key, deepcopy(payload[metadata_key]))
                payload = table_graph_3d
                block["source_room"] = block.get("source_room") or "C_GRAPH_ROOM"
            if block_type == "graph" and explicit_3d_type:
                payload.setdefault("representation", "scene3d")
                payload.setdefault("dimensions", 3)
            payload = _canonicalize_premium_3d_payload(payload, explicit_3d_type=explicit_3d_type)

        # Room payloads are hydrated only from evidence already returned for this turn.
        if block_type == "table" and not _has_render_payload("table", payload):
            if table_from_answer:
                payload = deepcopy(table_from_answer)
                block["source_room"] = block.get("source_room") or "C_TABLE_ROOM"
        elif block_type == "graph" and not _has_render_payload("graph", payload):
            if "graph" in requested and table_from_answer:
                candidate_graph = _graph_payload_from_table_3d(
                    table_from_answer, interpreted_graph_policy, current_request
                ) or _graph_payload_from_table(table_from_answer)
                if candidate_graph:
                    payload = candidate_graph
                    block["source_room"] = block.get("source_room") or "C_GRAPH_ROOM"
            if "graph" in requested and not _has_render_payload("graph", payload):
                candidate_graph = _graph_payload_from_answer(source_answer, interpreted_graph_policy)
                if not candidate_graph:
                    candidate_graph = _graph_payload_from_request(current_request, source_answer, interpreted_graph_policy)
                if candidate_graph:
                    payload = candidate_graph
                    block["source_room"] = block.get("source_room") or "C_GRAPH_ROOM"
        elif block_type == "diagram" and not _has_render_payload("diagram", payload):
            source = str(payload.get("source") or payload.get("mermaid") or block.get("source") or block.get("mermaid") or "")
            if not source and mermaid_from_answer:
                source = mermaid_from_answer
            parsed = _mermaid_payload(source)
            if parsed:
                payload = {**payload, **parsed}
                block["source_room"] = block.get("source_room") or "C_DIAGRAM_ROOM"
            elif electrical_diagram_from_answer:
                payload = {**payload, **deepcopy(electrical_diagram_from_answer)}
                block["source_room"] = block.get("source_room") or "C_DIAGRAM_ROOM"
            elif experiment_steps_from_answer:
                payload = {**payload, **deepcopy(experiment_steps_from_answer)}
                block["source_room"] = block.get("source_room") or "C_DIAGRAM_ROOM"
            elif diagram_from_request:
                payload = {**payload, **deepcopy(diagram_from_request)}
                block["source_room"] = block.get("source_room") or "C_DIAGRAM_ROOM"
        elif block_type == "gallery" and not _has_render_payload("gallery", payload):
            if markdown_images:
                payload = {"images": deepcopy(markdown_images), "source": "same_turn_markdown_image"}
                block["source_room"] = block.get("source_room") or "GALLERY_ROOM"
        elif block_type == "link":
            if not _has_render_payload("link", payload) and urls_from_answer:
                payload = {"url": urls_from_answer[0], "links": [{"url": url} for url in urls_from_answer], "source": "same_turn_answer"}
                block["source_room"] = block.get("source_room") or "C_LINK_ROOM"
            elif _has_render_payload("link", payload) and urls_from_answer:
                # Merge grounded URLs from the answer into the provider's link block.
                # This retains provider metadata while preventing all-but-first links
                # from being lost when the response's dedicated block is incomplete.
                existing_links = payload.get("links") if isinstance(payload.get("links"), list) else []
                links: List[Dict[str, Any]] = [deepcopy(item) for item in existing_links if isinstance(item, dict)]
                seen_urls = {str(item.get("url") or item.get("href") or "").strip().rstrip(".,;:!?") for item in links}
                markdown_links = re.findall(r"\[([^\]]{1,180})\]\((https?://[^\s)]+)\)", source_answer, re.IGNORECASE)
                grounded = [{"url": str(url).rstrip(".,;:!?"), "title": str(title).strip()} for title, url in markdown_links]
                grounded.extend({"url": str(url).rstrip(".,;:!?")} for url in urls_from_answer)
                for item in grounded:
                    url = str(item.get("url") or "").strip()
                    if url and url not in seen_urls:
                        links.append(item)
                        seen_urls.add(url)
                if links:
                    payload["links"] = links
                    payload.setdefault("url", str(links[0].get("url") or links[0].get("href") or ""))
        elif block_type == "code" and not _has_render_payload("code", payload, block):
            if code_match:
                payload = {"code": code_match.group(2), "content": code_match.group(2), "language": code_match.group(1) or "text", "filename": "generated-code.txt"}
        elif block_type == "formula" and not _has_render_payload("formula", payload):
            if formulas_from_answer:
                payload = {"formulas": formulas_from_answer, "formula": formulas_from_answer[0], "latex": formulas_from_answer[0]}

        if block_type == "graph" and payload and interpreted_graph_policy:
            # Carry Interpretation's decision to the Web renderer. The renderer
            # validates data integrity; it does not rediscover dialogue intent.
            payload_policy = payload.get("graph_policy") if isinstance(payload.get("graph_policy"), dict) else {}
            payload["graph_policy"] = {**payload_policy, **interpreted_graph_policy}
            payload.setdefault(
                "fallback_representation",
                interpreted_graph_policy.get("fallback_representation")
                or interpreted_graph_policy.get("preferred_representation")
                or "line",
            )
        if block_type == "graph" and payload:
            payload = _apply_premium_3d_visual_profile(payload, source_answer)
            payload = _interpolate_weekly_graph_payload(payload, current_request, source_answer)
        if payload:
            block["payload"] = payload
        if block_type in {"table", "graph", "diagram", "image", "gallery", "formula", "code", "link", "file"}:
            if not _has_render_payload(block_type, payload, block):
                # Keep no empty visual shell; RenderMessage must never mount a fake card.
                continue
        prepared.append(block)

    existing_types = {str(b.get("type") or "").lower() for b in prepared if isinstance(b, dict)}
    # The provider sometimes returns valid Mermaid in its text answer but omits the
    # separate DiagramBlock. Parse and promote only that explicit source; otherwise
    # Scene Contract silently loses a user-requested diagram.
    if "diagram" in requested and diagram_from_answer and "diagram" not in existing_types:
        prepared.append({
            "type": "diagram", "artifact_type": "diagram", "renderer": "DiagramRenderer",
            "viewer": "DiagramRenderer", "payload": deepcopy(diagram_from_answer),
            "source_room": "C_DIAGRAM_ROOM", "source": "same_turn_mermaid_source",
        })
        existing_types.add("diagram")
    if "diagram" in requested and experiment_steps_from_answer and "diagram" not in existing_types:
        prepared.append({
            "type": "diagram", "artifact_type": "diagram", "renderer": "DiagramRenderer",
            "viewer": "DiagramRenderer", "payload": deepcopy(experiment_steps_from_answer),
            "source_room": "C_DIAGRAM_ROOM", "source": "same_turn_experiment_steps",
        })
        existing_types.add("diagram")
    # An outline diagram is opt-in. Automatically drawing the answer's headings
    # duplicates the same structure the user just read and adds no new evidence.
    outline_requested = bool(re.search(
        r"(?:структур\w*\s+(?:ответ\w*|тем\w*|разговор\w*|обсужден\w*)|карта\s+(?:тем|разделов|мыслей|ответа)|mind\s*map|answer\s+outline|outline\s+of\s+the\s+answer)",
        current_request.lower().replace("ё", "е"),
    ))
    if outline_requested and "diagram" in requested and "diagram" not in existing_types:
        outline_diagram = _section_outline_diagram(section_outline)
        if outline_diagram and _has_render_payload("diagram", outline_diagram):
            prepared.append({
                "type": "diagram", "artifact_type": "diagram", "renderer": "DiagramRenderer",
                "viewer": "DiagramRenderer", "payload": outline_diagram,
                "source_room": "C_ARTIFACT_CONTRACT", "source": "explicit_answer_section_outline_request",
            })
            existing_types.add("diagram")
    # A requested source gallery may be absent as a separate block even though
    # the same answer contains explicit Markdown image embeds. Reuse only those
    # URLs; never convert ordinary source links into guessed image URLs.
    if "gallery" in requested and "gallery" not in existing_types and markdown_images:
        prepared.append({
            "type": "gallery", "artifact_type": "gallery", "renderer": "GalleryBlock",
            "viewer": "GalleryBlock", "payload": {"images": deepcopy(markdown_images), "source": "same_turn_markdown_image"},
            "source_room": "GALLERY_ROOM",
        })
        existing_types.add("gallery")

    # A requested table may be absent as a block even though the model returned
    # its literal Markdown table. Promote that same table, without changing cells.
    table_candidate = table_from_answer or section_table_from_answer
    # A Markdown table may be useful as source data for a requested graph, but it
    # must not become a second standalone TableBlock unless the user requested a
    # table too. Keep the parsed table available above for graph-data extraction.
    allow_answer_table_block = "table" in requested or (bool(table_from_answer) and "graph" not in requested)
    if allow_answer_table_block and "table" not in existing_types and table_candidate and _has_render_payload("table", table_candidate):
        prepared.append({"type": "table", "artifact_type": "table", "renderer": "TableBlock", "viewer": "TableBlock", "payload": table_candidate, "source_room": "C_TABLE_ROOM" if table_from_answer else "C_ARTIFACT_CONTRACT"})
        existing_types.add("table")
    if "graph" in requested and "graph" not in existing_types:
        graph_payload = (
            _graph_payload_from_table_3d(table_from_answer, interpreted_graph_policy, current_request)
            or _graph_payload_from_table(table_from_answer)
        ) if table_from_answer else {}
        if not graph_payload and section_graph_from_answer:
            graph_payload = deepcopy(section_graph_from_answer)
        if not graph_payload:
            graph_payload = _graph_payload_from_answer(source_answer, interpreted_graph_policy)
        if not graph_payload:
            graph_payload = _graph_payload_from_request(current_request, source_answer, interpreted_graph_policy)
        if graph_payload and interpreted_graph_policy:
            graph_payload_policy = graph_payload.get("graph_policy") if isinstance(graph_payload.get("graph_policy"), dict) else {}
            graph_payload["graph_policy"] = {**graph_payload_policy, **interpreted_graph_policy}
            graph_payload.setdefault(
                "fallback_representation",
                interpreted_graph_policy.get("fallback_representation")
                or interpreted_graph_policy.get("preferred_representation")
                or "line",
            )
        if graph_payload and _has_render_payload("graph", graph_payload):
            graph_payload = _apply_premium_3d_visual_profile(graph_payload, source_answer)
            graph_payload = _interpolate_weekly_graph_payload(graph_payload, current_request, source_answer)
            prepared.append({"type": "graph", "artifact_type": "graph", "renderer": "GraphBlock", "viewer": "GraphBlock", "payload": graph_payload, "source_room": "C_GRAPH_ROOM"})
            existing_types.add("graph")
    if ("link" in requested or urls_from_answer) and "link" not in existing_types:
        if urls_from_answer:
            # Preserve every source URL from the same-turn answer. Previously only
            # urls_from_answer[0] reached LinkRenderer, silently dropping citations.
            markdown_links = re.findall(
                r"\[([^\]]{1,180})\]\((https?://[^\s)]+)\)",
                source_answer,
                re.IGNORECASE,
            )
            links: List[Dict[str, Any]] = []
            seen_urls: set[str] = set()
            for title, url in markdown_links:
                clean_url = str(url or "").rstrip(".,;:!?")
                if clean_url and clean_url not in seen_urls:
                    links.append({"url": clean_url, "title": str(title or "").strip()})
                    seen_urls.add(clean_url)
            for url in urls_from_answer:
                clean_url = str(url or "").rstrip(".,;:!?")
                if clean_url and clean_url not in seen_urls:
                    links.append({"url": clean_url})
                    seen_urls.add(clean_url)
            prepared.append({
                "type": "link", "artifact_type": "link", "renderer": "LinkCard",
                "viewer": "LinkCard", "payload": {"url": links[0]["url"], "links": links, "source": "same_turn_answer"},
                "source_room": "C_LINK_ROOM",
            })
            existing_types.add("link")
    if ("diagram" in requested or diagram_from_answer or electrical_diagram_from_answer or diagram_from_request) and "diagram" not in existing_types:
        diagram_payload = diagram_from_answer or electrical_diagram_from_answer or diagram_from_request
        if diagram_payload:
            prepared.append({"type": "diagram", "artifact_type": "diagram", "renderer": "DiagramRenderer", "viewer": "DiagramRenderer", "payload": diagram_payload, "source_room": "C_DIAGRAM_ROOM"})
            existing_types.add("diagram")
    if ("code" in requested or code_match) and "code" not in existing_types:
        if code_match:
            prepared.append({"type": "code", "artifact_type": "code", "renderer": "CodeBlock", "viewer": "CodeBlock", "payload": {"code": code_match.group(2), "content": code_match.group(2), "language": code_match.group(1) or "text", "filename": "generated-code.txt"}})
            existing_types.add("code")
    if ("formula" in requested or formulas_from_answer) and "formula" not in existing_types:
        if formulas_from_answer:
            prepared.append({"type": "formula", "artifact_type": "formula", "renderer": "FormulaRenderer", "viewer": "FormulaRenderer", "payload": {"formulas": formulas_from_answer, "formula": formulas_from_answer[0], "latex": formulas_from_answer[0]}})

    # Adaptive diagrams complement substantial structured explanations only when
    # no different visual form was explicitly requested. The outline is derived
    # from this turn's real headings/paragraphs, never from fixed topic templates.
    try:
        from blocks.C_DIAGRAM_ROOM import (
            build_answer_outline_payload as _build_answer_outline_payload,
            ensure_readable_diagram_payload as _ensure_readable_diagram_payload,
            should_add_adaptive_diagram as _should_add_adaptive_diagram,
        )
        present_diagrams = [
            item for item in prepared
            if isinstance(item, dict) and _scene_block_type(item) == "diagram"
        ]
        if not present_diagrams and _should_add_adaptive_diagram(current_request, source_answer, requested):
            adaptive_payload = _build_answer_outline_payload(source_answer)
            if adaptive_payload:
                prepared.append({
                    "type": "diagram", "artifact_type": "diagram",
                    "renderer": "DiagramRenderer", "viewer": "DiagramRenderer",
                    "title": adaptive_payload.get("title"), "payload": adaptive_payload,
                    "description": adaptive_payload.get("description"),
                    "source_room": "C_ARTIFACT_CONTRACT",
                    "source": "same_turn_adaptive_answer_outline",
                    "adaptive_visual": True,
                })
        # The canonical web diagram renderer was receiving node/edge-only graphs.
        # On mobile those could collapse to tiny labels in the corner. Convert all
        # concrete node/edge diagrams to a readable portrait SVG before the shared
        # SceneContract sees them; preserve supplied SVG and all original fields.
        for visual_block in prepared:
            if not isinstance(visual_block, dict) or _scene_block_type(visual_block) != "diagram":
                continue
            direct_payload = visual_block.get("payload") if isinstance(visual_block.get("payload"), dict) else {}
            raw_payload = direct_payload or _payload_for_render_block(visual_block, "diagram")
            if not isinstance(raw_payload, dict) or not raw_payload:
                continue
            readable_payload = _ensure_readable_diagram_payload(
                raw_payload,
                title=str(visual_block.get("title") or raw_payload.get("title") or ""),
            )
            if readable_payload:
                visual_block["payload"] = readable_payload
                if readable_payload.get("svg") or readable_payload.get("svg_payload"):
                    renderer = str(readable_payload.get("renderer") or visual_block.get("renderer") or "SvgBlock")
                    if renderer in {"", "DiagramRenderer", "diagram"}:
                        renderer = "SvgBlock"
                    visual_block["renderer"] = renderer
                    visual_block["viewer"] = renderer
                    visual_block["diagram_layout_repaired"] = True
    except Exception as _diagram_quality_error:
        # Visual repair must never make the text response fail. SceneContract's
        # existing payload validation remains the fallback if an unusual payload
        # cannot be converted by this optional layout helper.
        try:
            print("[APRIL_DIAGRAM_LAYOUT_REPAIR] " + json.dumps({
                "status": "fallback_to_existing_contract",
                "error_type": type(_diagram_quality_error).__name__,
            }, ensure_ascii=False, separators=(",", ":")), flush=True)
        except Exception:
            pass

    # Remove duplicates based on actual payload, not renderer metadata. Keep text
    # and each different selected representation in the same ordered response.
    result: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for block in prepared:
        block_type = str(block.get("type") or "text").lower()
        signature_payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
        signature = f"{block_type}:{hashlib.sha256(repr(signature_payload).encode('utf-8')).hexdigest()[:16]}"
        if block_type in {"text", "markdown"}:
            signature = f"{block_type}:{hashlib.sha256(str(block.get('content') or block.get('text') or '').encode('utf-8')).hexdigest()[:16]}"
        if signature in seen:
            continue
        seen.add(signature)
        result.append(block)

    # If the user asked for a graph but not a table, the graph owns the requested
    # visual output. Do not expose a second table merely because the model included
    # Markdown rows in its prose. The parsed rows above remain available for graph
    # construction; explicit graph+table requests are unaffected.
    suppress_unrequested_table = "graph" in requested and "table" not in requested and any(
        isinstance(item, dict)
        and _scene_block_type(item) == "graph"
        and _has_render_payload("graph", _payload_for_render_block(item, "graph"), item)
        for item in result
    )
    if suppress_unrequested_table:
        result = [item for item in result if not (isinstance(item, dict) and _scene_block_type(item) == "table")]

    # The visual representation now owns its exact table/code/diagram/math body.
    # Keep only surrounding narrative in the text node to avoid rendering the
    # same content twice while still preserving explanatory prose.
    rendered_types = {str(item.get("type") or "").lower() for item in result if isinstance(item, dict)}
    if rendered_types & {"table", "code", "diagram", "formula", "graph"}:
        for item in result:
            if not isinstance(item, dict) or str(item.get("type") or "").lower() not in {"text", "markdown"}:
                continue
            original_text = str(item.get("content") or item.get("text") or "")
            cleaned_text = _strip_rendered_segments(original_text, rendered_types, result, suppress_unrequested_table=suppress_unrequested_table)
            if original_text.strip() and not cleaned_text.strip():
                # Do not produce an empty text bubble if the entire source answer
                # was a table/code/diagram; the structured renderer now owns it.
                cyrillic = bool(re.search(r"[А-Яа-яІіЇїЄєҐґ]", original_text))
                if "table" in rendered_types:
                    cleaned_text = "Данные представлены в таблице." if cyrillic else "The data is shown in the table."
                elif "diagram" in rendered_types:
                    cleaned_text = "Схема представлена ниже." if cyrillic else "The diagram is shown below."
                elif "code" in rendered_types:
                    cleaned_text = "Код представлен отдельным блоком." if cyrillic else "The code is shown in a separate block."
                else:
                    cleaned_text = "Формула представлена отдельным блоком." if cyrillic else "The formula is shown in a separate block."
            item["content"] = cleaned_text
            item["text"] = cleaned_text
            payload = item.get("payload")
            if isinstance(payload, dict):
                for key in ("content", "text", "markdown", "display_text"):
                    if isinstance(payload.get(key), str):
                        payload[key] = cleaned_text

    # Preserve a substantial narrative alongside visual artifacts. The current
    # full answer is the source of truth; the 60% threshold protects against a
    # renderer-cleanup pass accidentally replacing prose with a one-line caption.
    canonical_text = _strip_rendered_segments(source_answer, rendered_types, result, suppress_unrequested_table=suppress_unrequested_table).strip()
    text_indices = [
        index for index, item in enumerate(result)
        if isinstance(item, dict) and str(item.get("type") or "").lower() in {"text", "markdown", "message", "message_text"}
    ]
    text_chars = sum(
        len(str(result[index].get("content") or result[index].get("text") or result[index].get("markdown") or "").strip())
        for index in text_indices
    )
    retention_target = int(len(canonical_text) * 0.60)
    if canonical_text and text_chars < retention_target:
        if text_indices:
            target_index = max(text_indices, key=lambda idx: len(str(result[idx].get("content") or result[idx].get("text") or "")))
            result[target_index]["content"] = canonical_text
            result[target_index]["text"] = canonical_text
            result[target_index]["text_integrity_repaired"] = True
            action = "restored_full_answer_to_text_block"
        else:
            result.insert(0, {
                "type": "text", "artifact_type": "text",
                "renderer": "MessageTextBlock", "viewer": "MessageTextBlock",
                "content": canonical_text, "text_integrity_repaired": True,
            })
            action = "inserted_full_answer_text_block"
        text_chars = len(canonical_text)
        try:
            print("[APRIL_RENDER_TEXT_RETENTION] " + json.dumps({
                "action": action,
                "answer_chars": len(canonical_text),
                "text_chars_after": text_chars,
                "retention_ratio": round(text_chars / max(1, len(canonical_text)), 3),
            }, ensure_ascii=False, separators=(",", ":")), flush=True)
        except Exception:
            pass

    render_aliases = {"gallery": "image", "image_gallery": "image", "generated_image": "image", "svg": "diagram", "math": "formula", "latex": "formula", "chart": "graph", "plot": "graph", "links": "link", "hyperlink": "link"}
    rendered_types = {
        render_aliases.get(str(item.get("type") or item.get("artifact_type") or "").strip().lower(), str(item.get("type") or item.get("artifact_type") or "").strip().lower())
        for item in result if isinstance(item, dict)
    }
    requested_visual = sorted(requested.intersection({"image", "gallery", "table", "graph", "diagram", "formula", "link", "code", "file"}))
    present_visual = sorted(set(requested_visual).intersection(rendered_types))
    missing_visual = sorted(set(requested_visual) - set(present_visual))
    coverage = round(len(present_visual) / max(1, len(requested_visual)), 3) if requested_visual else 1.0
    try:
        print("[APRIL_RENDER_COVERAGE] " + json.dumps({
            "requested_outputs": sorted(requested),
            "requested_visual_outputs": requested_visual,
            "rendered_types": sorted(rendered_types),
            "rendered_requested_types": present_visual,
            "missing_requested_types": missing_visual,
            "requested_renderer_coverage": coverage,
            "text_chars": text_chars,
            "answer_chars": len(canonical_text),
            "text_retention_ratio": round(text_chars / max(1, len(canonical_text)), 3) if canonical_text else 0.0,
            "minimum_text_retention": 0.60,
            "minimum_renderer_coverage": 0.50,
        }, ensure_ascii=False, separators=(",", ":")), flush=True)
    except Exception:
        pass
    return result

def _scene_payload_has_content(block_type: str, payload: Dict[str, Any], block: Dict[str, Any] | None = None) -> bool:
    return _has_render_payload(block_type, payload, block)


_PREMIUM_EXPLAINED_RENDER_TYPES = {
    "formula", "graph", "table", "diagram", "image", "gallery", "code", "link", "file", "audio", "video"
}


def _explanation_language(answer: str, language_hint: Any = "") -> str:
    """Resolve a user-facing fallback language, normalizing browser and legacy aliases."""
    hint = str(language_hint or "").strip().lower().replace("_", "-")
    code = hint.split("-", 1)[0]
    if code in {"ua"}:
        code = "uk"
    if code in {"ru", "uk", "en", "es", "de", "fr", "it", "pl", "pt", "nl", "ja", "zh", "ko", "ar", "hi", "el"}:
        return code

    low = (answer or "").lower()
    if any(ch in low for ch in "їєґ") or re.search(r"\b(це|який|яка|формула|посилання|зображення|таблиця|графік|схема|рівняння|пояснює)\b", low):
        return "uk"
    if re.search(r"[а-яё]", low):
        return "ru"
    if re.search(r"[\u3040-\u30ff]", answer or ""):
        return "ja"
    if re.search(r"[\u4e00-\u9fff]", answer or ""):
        return "zh"
    if re.search(r"[\uac00-\ud7af]", answer or ""):
        return "ko"
    if re.search(r"[\u0600-\u06ff]", answer or ""):
        return "ar"
    if re.search(r"[\u0900-\u097f]", answer or ""):
        return "hi"
    if re.search(r"[\u0370-\u03ff]", answer or ""):
        return "el"
    if any(ch in low for ch in "éèàçùœ") or re.search(r"\b(la formule|ce lien|ce graphique|ce tableau|cette image|ce schéma|bonjour|merci)\b", low):
        return "fr"
    if any(ch in low for ch in "ñ¿¡") or re.search(r"\b(hola|gracias|necesito|por favor|explicación)\b", low):
        return "es"
    if any(ch in low for ch in "ßäöü") or re.search(r"\b(hallo|danke|bitte|erklärung)\b", low):
        return "de"
    if any(ch in low for ch in "ãõ") or re.search(r"\b(olá|obrigado|obrigada|explicação)\b", low):
        return "pt"
    if any(ch in low for ch in "łśźżąćęńó") or re.search(r"\b(cześć|dziękuję|wyjaśnienie)\b", low):
        return "pl"
    if re.search(r"\b(ciao|grazie|spiegazione|formula|immagine)\b", low):
        return "it"
    if re.search(r"\b(hallo|bedankt|uitleg|deze|het|een)\b", low):
        return "nl"
    return "en"


def _render_payload(block: Dict[str, Any]) -> Dict[str, Any]:
    payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
    if not payload and isinstance(block.get("data"), dict):
        payload = block.get("data")
    return payload


def _render_block_field(block: Dict[str, Any], payload: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = block.get(key)
        if value not in (None, "", [], {}):
            return value
        value = payload.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _answer_sections_for_explanation(answer: str) -> List[tuple[str, str]]:
    text = str(answer or "").strip()
    if not text:
        return []
    matches = list(re.finditer(r"(?m)^\s{0,3}#{1,4}\s+([^\n#][^\n]*)\s*$", text))
    sections: List[tuple[str, str]] = []
    if not matches:
        # Treat paragraph-sized passages as separate candidates. Returning the
        # entire answer here would cause the full response to repeat under every
        # renderer when an answer has no Markdown headings.
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
        return [("", part) for part in paragraphs[:80]]
    if matches[0].start() > 0 and text[:matches[0].start()].strip():
        sections.append(("", text[:matches[0].start()].strip()))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match.group(1).strip(), text[match.end():end].strip()))
    return sections


def _clean_render_explanation_context(value: str, block_type: str) -> str:
    text = str(value or "")
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)|\$\$[\s\S]*?\$\$|(?<!\$)\$[^$\n]{1,220}\$(?!\$)", " ", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", text, flags=re.IGNORECASE)
    text = re.sub(r"https?://\S+", " ", text, flags=re.IGNORECASE)
    cleaned_lines: List[str] = []
    for line in text.splitlines():
        candidate = line.strip()
        if not candidate or re.match(r"^#{1,4}\s", candidate):
            continue
        if candidate.startswith("|") and candidate.endswith("|"):
            continue
        # When an equation and its meaning share one line, retain the prose after
        # the separator instead of repeating the equation beneath the renderer.
        equation_explanation = re.split(r"\s+[—–]\s+", candidate, maxsplit=1)
        if len(equation_explanation) == 2 and any(mark in equation_explanation[0] for mark in ("=", "≈", "→", "↔")) and len(equation_explanation[1].split()) >= 4:
            candidate = equation_explanation[1].strip()
        if re.match(r"^\s*[-*•]?\s*`{0,1}[A-Za-zА-Яа-яΑ-ω_\\{}^0-9().,+*/ =<>≤≥≠≈:-]{2,90}`?\s*$", candidate) and any(mark in candidate for mark in ("=", "≈", "→", "↔")) and len(candidate.split()) <= 8:
            continue
        cleaned_lines.append(candidate)
    text = re.sub(r"\s+", " ", " ".join(cleaned_lines)).strip(" \t\n-–—:;,.•")
    text = re.sub(r"\s+", " ", text)
    return text[:850]


def _render_section_context(block_type: str, block: Dict[str, Any], answer: str) -> tuple[str, str]:
    sections = _answer_sections_for_explanation(answer)
    payload = _render_payload(block)
    title = str(_render_block_field(block, payload, "step_title", "title", "section", "filename") or "").strip()
    title_low = title.lower()
    patterns = {
        "formula": r"формул|рівнян|уравнен|equation|formula|math|mathemat|релят|relativ|mass.?energy",
        "link": r"посилан|ссылк|джерел|источник|ресурс|source|reference|resource|links?|bibliograph|фотоелектр",
        "image": r"зображ|зображенн|картин|портрет|ілюстрац|иллюстрац|фото|image|picture|portrait|illustration|photo",
        "gallery": r"зображ|картин|портрет|ілюстрац|иллюстрац|фото|image|picture|portrait|illustration|photo",
        "code": r"код|скрипт|реаліза|реализац|implementation|source code|code|script|change|змін|измен",
        "table": r"таблиц|порівня|сравнен|comparison|table|data",
        "graph": r"графік|график|залежн|діаграм|chart|graph|plot|function|функці|функци",
        "diagram": r"схем|діаграм|диаграм|експеримент|эксперимент|дослід|опыт|experiment|diagram|flow|process",
        "file": r"файл|документ|document|file|attachment|вміст|содерж",
        "audio": r"аудіо|голос|audio|voice|sound|звук",
        "video": r"відео|видео|video|сцена|кадр|frame",
    }
    pattern = patterns.get(block_type, r"$^")
    ranked: List[tuple[int, str, str]] = []
    for heading, body in sections:
        hlow = heading.lower()
        score = 0
        if title_low and hlow:
            title_terms = {term for term in re.findall(r"[\wА-Яа-яІіЇїЄєҐґ]{3,}", title_low) if term not in {"the", "and", "для", "про", "this", "that"}}
            heading_terms = set(re.findall(r"[\wА-Яа-яІіЇїЄєҐґ]{3,}", hlow))
            overlap = len(title_terms & heading_terms)
            if hlow == title_low:
                score += 6
            elif overlap:
                score += min(5, overlap * 2)
        if re.search(pattern, hlow, re.IGNORECASE):
            score += 4
        if re.search(pattern, body, re.IGNORECASE):
            score += 2
        if title_low and re.search(re.escape(title_low), body.lower(), re.IGNORECASE):
            score += 3
        cleaned = _clean_render_explanation_context(body, block_type)
        if len(cleaned) >= 45:
            score += 1
        if cleaned:
            ranked.append((score, heading, cleaned))
    if not ranked:
        return "", ""
    ranked.sort(key=lambda item: (item[0], len(item[2])), reverse=True)
    score, heading, context = ranked[0]
    if score <= 1 and len(sections) > 1:
        # Do not associate an artifact with an unrelated section merely because
        # it happens to be the longest paragraph.
        return "", ""
    # Prefer two concise paragraphs from a well-matched section when available.
    if score >= 4 and len(sections) > 1:
        selected = next((body for h, body in sections if h == heading), "")
        cleaned_selected = _clean_render_explanation_context(selected, block_type)
        if cleaned_selected:
            context = cleaned_selected
    return heading, context[:720]


def _localized_explanation_prefix(language: str, block_type: str) -> str:
    """Human-facing labels for system-generated render explanations."""
    labels = {
        "ru": {"formula": "Пояснение к формуле", "link": "Зачем нужна ссылка", "image": "Что показывает изображение", "gallery": "Что показывает изображение", "code": "Что делает код", "table": "Как читать таблицу", "graph": "Что показывает график", "diagram": "Что показывает схема", "file": "Что содержит файл", "audio": "Что содержит аудиоблок", "video": "Что показывает видеоблок"},
        "uk": {"formula": "Пояснення до формули", "link": "Для чого потрібне посилання", "image": "Що показує зображення", "gallery": "Що показує зображення", "code": "Що робить код", "table": "Як читати таблицю", "graph": "Що показує графік", "diagram": "Що показує схема", "file": "Що містить файл", "audio": "Що містить аудіоблок", "video": "Що показує відеоблок"},
        "fr": {"formula": "Explication de la formule", "link": "Utilité du lien", "image": "Ce que montre l’image", "gallery": "Ce que montre l’image", "code": "Rôle du code", "table": "Lecture du tableau", "graph": "Ce que montre le graphique", "diagram": "Ce que montre le schéma", "file": "Contenu du fichier", "audio": "Contenu du bloc audio", "video": "Contenu du bloc vidéo"},
        "en": {"formula": "Formula explanation", "link": "Why this link is included", "image": "What the image shows", "gallery": "What the image shows", "code": "What the code does", "table": "How to read the table", "graph": "What the graph shows", "diagram": "What the diagram shows", "file": "What the file contains", "audio": "What the audio block contains", "video": "What the video block shows"},
        "es": {"formula": "Explicación de la fórmula", "link": "Para qué sirve el enlace", "image": "Qué muestra la imagen", "gallery": "Qué muestra la imagen", "code": "Qué hace el código", "table": "Cómo leer la tabla", "graph": "Qué muestra el gráfico", "diagram": "Qué muestra el diagrama", "file": "Qué contiene el archivo", "audio": "Qué contiene el bloque de audio", "video": "Qué muestra el vídeo"},
        "de": {"formula": "Erläuterung der Formel", "link": "Wozu dieser Link dient", "image": "Was das Bild zeigt", "gallery": "Was das Bild zeigt", "code": "Was der Code bewirkt", "table": "So lesen Sie die Tabelle", "graph": "Was das Diagramm zeigt", "diagram": "Was das Schema zeigt", "file": "Was die Datei enthält", "audio": "Was der Audioblock enthält", "video": "Was das Video zeigt"},
        "it": {"formula": "Spiegazione della formula", "link": "A cosa serve il collegamento", "image": "Cosa mostra l’immagine", "gallery": "Cosa mostra l’immagine", "code": "Cosa fa il codice", "table": "Come leggere la tabella", "graph": "Cosa mostra il grafico", "diagram": "Cosa mostra lo schema", "file": "Cosa contiene il file", "audio": "Contenuto del blocco audio", "video": "Cosa mostra il video"},
        "pl": {"formula": "Objaśnienie wzoru", "link": "Do czego służy link", "image": "Co przedstawia obraz", "gallery": "Co przedstawia obraz", "code": "Co robi kod", "table": "Jak czytać tabelę", "graph": "Co przedstawia wykres", "diagram": "Co przedstawia schemat", "file": "Co zawiera plik", "audio": "Co zawiera blok audio", "video": "Co przedstawia wideo"},
        "pt": {"formula": "Explicação da fórmula", "link": "Para que serve o link", "image": "O que a imagem mostra", "gallery": "O que a imagem mostra", "code": "O que o código faz", "table": "Como ler a tabela", "graph": "O que o gráfico mostra", "diagram": "O que o diagrama mostra", "file": "O que o ficheiro contém", "audio": "O que contém o bloco de áudio", "video": "O que o vídeo mostra"},
        "nl": {"formula": "Uitleg bij de formule", "link": "Waarvoor deze link dient", "image": "Wat de afbeelding laat zien", "gallery": "Wat de afbeelding laat zien", "code": "Wat de code doet", "table": "De tabel lezen", "graph": "Wat de grafiek laat zien", "diagram": "Wat het schema laat zien", "file": "Wat het bestand bevat", "audio": "Wat het audioblok bevat", "video": "Wat de video laat zien"},
        "ja": {"formula": "数式の説明", "link": "リンクの目的", "image": "画像の内容", "gallery": "画像の内容", "code": "コードの動作", "table": "表の読み方", "graph": "グラフの内容", "diagram": "図の内容", "file": "ファイルの内容", "audio": "音声ブロックの内容", "video": "動画の内容"},
        "zh": {"formula": "公式说明", "link": "链接用途", "image": "图像内容", "gallery": "图像内容", "code": "代码的作用", "table": "表格读法", "graph": "图表内容", "diagram": "示意图内容", "file": "文件内容", "audio": "音频块内容", "video": "视频内容"},
        "ko": {"formula": "수식 설명", "link": "링크의 용도", "image": "이미지 설명", "gallery": "이미지 설명", "code": "코드의 기능", "table": "표 읽는 방법", "graph": "그래프 설명", "diagram": "도식 설명", "file": "파일 내용", "audio": "오디오 블록 내용", "video": "동영상 설명"},
        "ar": {"formula": "شرح المعادلة", "link": "الغرض من الرابط", "image": "ما الذي توضحه الصورة", "gallery": "ما الذي توضحه الصورة", "code": "وظيفة الشيفرة", "table": "كيفية قراءة الجدول", "graph": "ما الذي يوضحه الرسم البياني", "diagram": "ما الذي يوضحه المخطط", "file": "محتوى الملف", "audio": "محتوى المقطع الصوتي", "video": "ما الذي يعرضه الفيديو"},
        "hi": {"formula": "सूत्र की व्याख्या", "link": "लिंक का उद्देश्य", "image": "चित्र क्या दिखाता है", "gallery": "चित्र क्या दिखाता है", "code": "कोड क्या करता है", "table": "तालिका कैसे पढ़ें", "graph": "ग्राफ़ क्या दिखाता है", "diagram": "आरेख क्या दिखाता है", "file": "फ़ाइल में क्या है", "audio": "ऑडियो खंड में क्या है", "video": "वीडियो क्या दिखाता है"},
        "el": {"formula": "Επεξήγηση τύπου", "link": "Χρήση του συνδέσμου", "image": "Τι δείχνει η εικόνα", "gallery": "Τι δείχνει η εικόνα", "code": "Τι κάνει ο κώδικας", "table": "Πώς διαβάζεται ο πίνακας", "graph": "Τι δείχνει το γράφημα", "diagram": "Τι δείχνει το διάγραμμα", "file": "Περιεχόμενο αρχείου", "audio": "Περιεχόμενο ήχου", "video": "Τι δείχνει το βίντεο"},
    }
    generic = {"ru": "Пояснение", "uk": "Пояснення", "fr": "Explication", "en": "Explanation", "es": "Explicación", "de": "Erklärung", "it": "Spiegazione", "pl": "Objaśnienie", "pt": "Explicação", "nl": "Uitleg", "ja": "説明", "zh": "说明", "ko": "설명", "ar": "شرح", "hi": "व्याख्या", "el": "Επεξήγηση"}
    selected = labels.get(language) or labels["en"]
    return selected.get(block_type, generic.get(language, "Explanation"))
def _fallback_render_explanation_extended(block_type: str, block: Dict[str, Any], answer: str, language: str) -> str:
    """Localized source-grounded fallback text for the remaining UI languages."""
    payload = _render_payload(block)
    section, context = _render_section_context(block_type, block, answer)
    block_title = str(_render_block_field(block, payload, "step_title", "title", "section") or "").strip()
    title = str(section or block_title).strip()
    title_ref = f" «{title[:100]}»" if title else ""

    templates = {
        "es": {
            "link_plain": "Este enlace se incluye como fuente para comprobar o ampliar el tema{title}.",
            "formula": "Esta fórmula se relaciona con la sección{title}. Explica: {context}", "link": "Este enlace lleva a una fuente asociada con la sección{title}. Contexto: {context}", "image": "La imagen se relaciona con la sección{title} y muestra: {context}", "gallery": "La imagen se relaciona con la sección{title} y muestra: {context}", "code": "El bloque de código complementa la sección{title}. Su finalidad es: {context}", "table": "La tabla organiza los datos de la sección{title} para compararlos. Contenido: {context}", "graph": "El gráfico representa los datos o la relación de la sección{title}. Contenido: {context}", "diagram": "El diagrama muestra un proceso o unas relaciones de la sección{title}. Descripción: {context}", "file": "El archivo está relacionado con la sección{title}. En esta respuesta sirve para: {context}", "audio": "El bloque de audio está relacionado con la sección{title}: {context}", "video": "El bloque de vídeo está relacionado con la sección{title}: {context}", "generated": "Es una ilustración generada, no una fotografía de archivo.", "edited": "Cambios indicados: {note}", "formula_plain": "Este bloque matemático representa una relación cuantitativa de la sección{title}. Interpreta los símbolos según el contexto de la respuesta.", "table_plain": "La tabla agrupa valores relacionados para facilitar su comparación.{details} Las conclusiones deben basarse solo en las filas mostradas.", "graph_plain": "El gráfico representa la relación entre las variables de los ejes. {details} La tendencia debe leerse a partir de los datos mostrados, sin inferir valores ausentes.", "diagram_plain": "El diagrama ilustra una estructura o una secuencia de pasos. {details}", "block_plain": "Este bloque está relacionado con la sección{title}. {details}", "open": "Abre el bloque para consultar su contenido.", "columns": " Columnas: {headers}.", "rows": " Número de filas de datos: {count}.", "relationship": "La imagen ilustra «{title}»; por sí sola no constituye una prueba factual."},
        "de": {
            "link_plain": "Dieser Link dient als Quelle, um das Thema{title} zu prüfen oder zu vertiefen.",
            "formula": "Diese Formel gehört zum Abschnitt{title}. Sie erklärt: {context}", "link": "Dieser Link führt zu einer Quelle für den Abschnitt{title}. Kontext: {context}", "image": "Das Bild gehört zum Abschnitt{title} und zeigt: {context}", "gallery": "Das Bild gehört zum Abschnitt{title} und zeigt: {context}", "code": "Der Codeblock ergänzt den Abschnitt{title}. Sein Zweck: {context}", "table": "Die Tabelle ordnet die Daten aus dem Abschnitt{title} zum Vergleich. Inhalt: {context}", "graph": "Das Diagramm veranschaulicht Daten oder Beziehungen aus dem Abschnitt{title}. Inhalt: {context}", "diagram": "Das Schema zeigt einen Ablauf oder Beziehungen aus dem Abschnitt{title}. Beschreibung: {context}", "file": "Die Datei gehört zum Abschnitt{title}. In dieser Antwort dient sie dazu: {context}", "audio": "Der Audioblock gehört zum Abschnitt{title}: {context}", "video": "Der Videoblock gehört zum Abschnitt{title}: {context}", "generated": "Dies ist eine generierte Illustration und kein Archivfoto.", "edited": "Dokumentierte Änderungen: {note}", "formula_plain": "Dieser mathematische Block beschreibt einen quantitativen Zusammenhang im Abschnitt{title}. Deute die Symbole im Kontext der Antwort.", "table_plain": "Die Tabelle bündelt zusammengehörige Werte zum Vergleich.{details} Schlussfolgerungen dürfen sich nur auf die angezeigten Zeilen stützen.", "graph_plain": "Das Diagramm zeigt den Zusammenhang zwischen den Achsenvariablen. {details} Lies den Trend aus den angezeigten Daten ab und ergänze keine fehlenden Werte.", "diagram_plain": "Das Schema veranschaulicht eine Struktur oder eine Abfolge von Schritten. {details}", "block_plain": "Dieser Block gehört zum aktuellen Abschnitt{title}. {details}", "open": "Öffne den Block, um seinen Inhalt anzusehen.", "columns": " Spalten: {headers}.", "rows": " Anzahl der Datenzeilen: {count}.", "relationship": "Das Bild veranschaulicht „{title}“, ist für sich genommen aber kein faktischer Beleg."},
        "it": {
            "link_plain": "Questo collegamento è una fonte per verificare o approfondire il tema{title}.",
            "formula": "Questa formula è collegata alla sezione{title}. Spiega: {context}", "link": "Questo collegamento porta a una fonte relativa alla sezione{title}. Contesto: {context}", "image": "L’immagine è collegata alla sezione{title} e mostra: {context}", "gallery": "L’immagine è collegata alla sezione{title} e mostra: {context}", "code": "Il blocco di codice integra la sezione{title}. La sua funzione è: {context}", "table": "La tabella organizza i dati della sezione{title} per confrontarli. Contenuto: {context}", "graph": "Il grafico visualizza dati o relazioni della sezione{title}. Contenuto: {context}", "diagram": "Lo schema mostra un processo o relazioni della sezione{title}. Descrizione: {context}", "file": "Il file è collegato alla sezione{title}. In questa risposta serve a: {context}", "audio": "Il blocco audio è collegato alla sezione{title}: {context}", "video": "Il blocco video è collegato alla sezione{title}: {context}", "generated": "È un’illustrazione generata, non una fotografia d’archivio.", "edited": "Modifiche indicate: {note}", "formula_plain": "Questo blocco matematico rappresenta una relazione quantitativa della sezione{title}. Interpreta i simboli nel contesto della risposta.", "table_plain": "La tabella raccoglie valori correlati per facilitarne il confronto.{details} Le conclusioni devono basarsi sulle righe effettivamente mostrate.", "graph_plain": "Il grafico rappresenta la relazione tra le variabili degli assi. {details} La tendenza va letta dai dati visualizzati, senza inventare valori mancanti.", "diagram_plain": "Lo schema illustra una struttura o una sequenza di passaggi. {details}", "block_plain": "Questo blocco è collegato alla sezione{title}. {details}", "open": "Apri il blocco per consultarne il contenuto.", "columns": " Colonne: {headers}.", "rows": " Numero di righe di dati: {count}.", "relationship": "L’immagine illustra «{title}», ma da sola non costituisce una prova fattuale."},
        "pl": {
            "link_plain": "Ten link prowadzi do źródła, które pozwala sprawdzić lub pogłębić temat{title}.",
            "formula": "Ten wzór jest związany z sekcją{title}. Wyjaśnia: {context}", "link": "Ten link prowadzi do źródła związanego z sekcją{title}. Kontekst: {context}", "image": "Obraz jest związany z sekcją{title} i przedstawia: {context}", "gallery": "Obraz jest związany z sekcją{title} i przedstawia: {context}", "code": "Blok kodu uzupełnia sekcję{title}. Jego przeznaczenie: {context}", "table": "Tabela porządkuje dane z sekcji{title}, aby można je było porównać. Zawartość: {context}", "graph": "Wykres przedstawia dane lub zależność z sekcji{title}. Zawartość: {context}", "diagram": "Schemat pokazuje proces lub zależności z sekcji{title}. Opis: {context}", "file": "Plik jest związany z sekcją{title}. W tej odpowiedzi służy do: {context}", "audio": "Blok audio jest związany z sekcją{title}: {context}", "video": "Blok wideo jest związany z sekcją{title}: {context}", "generated": "To wygenerowana ilustracja, a nie fotografia archiwalna.", "edited": "Odnotowane zmiany: {note}", "formula_plain": "Ten blok matematyczny przedstawia zależność ilościową z sekcji{title}. Symbole należy interpretować w kontekście odpowiedzi.", "table_plain": "Tabela porządkuje powiązane wartości, aby ułatwić ich porównanie.{details} Wnioski powinny wynikać wyłącznie z widocznych wierszy.", "graph_plain": "Wykres przedstawia zależność między zmiennymi na osiach. {details} Trend należy odczytać z pokazanych danych, bez dopowiadania brakujących wartości.", "diagram_plain": "Schemat ilustruje strukturę lub kolejność kroków. {details}", "block_plain": "Ten blok jest związany z bieżącą sekcją{title}. {details}", "open": "Otwórz blok, aby zobaczyć jego zawartość.", "columns": " Kolumny: {headers}.", "rows": " Liczba wierszy danych: {count}.", "relationship": "Obraz ilustruje temat „{title}”, ale sam w sobie nie jest dowodem faktu."},
        "pt": {
            "link_plain": "Este link é uma fonte para verificar ou aprofundar o tema{title}.",
            "formula": "Esta fórmula está relacionada com a secção{title}. Explica: {context}", "link": "Este link conduz a uma fonte relacionada com a secção{title}. Contexto: {context}", "image": "A imagem está relacionada com a secção{title} e mostra: {context}", "gallery": "A imagem está relacionada com a secção{title} e mostra: {context}", "code": "O bloco de código complementa a secção{title}. A sua finalidade é: {context}", "table": "A tabela organiza os dados da secção{title} para comparação. Conteúdo: {context}", "graph": "O gráfico representa dados ou relações da secção{title}. Conteúdo: {context}", "diagram": "O diagrama mostra um processo ou relações da secção{title}. Descrição: {context}", "file": "O ficheiro está relacionado com a secção{title}. Nesta resposta, serve para: {context}", "audio": "O bloco de áudio está relacionado com a secção{title}: {context}", "video": "O bloco de vídeo está relacionado com a secção{title}: {context}", "generated": "É uma ilustração gerada, não uma fotografia de arquivo.", "edited": "Alterações registadas: {note}", "formula_plain": "Este bloco matemático representa uma relação quantitativa da secção{title}. Interprete os símbolos no contexto da resposta.", "table_plain": "A tabela reúne valores relacionados para facilitar a comparação.{details} As conclusões devem basear-se apenas nas linhas apresentadas.", "graph_plain": "O gráfico representa a relação entre as variáveis dos eixos. {details} A tendência deve ser lida nos dados apresentados, sem inventar valores em falta.", "diagram_plain": "O diagrama ilustra uma estrutura ou uma sequência de etapas. {details}", "block_plain": "Este bloco está relacionado com a secção atual{title}. {details}", "open": "Abra o bloco para consultar o seu conteúdo.", "columns": " Colunas: {headers}.", "rows": " Número de linhas de dados: {count}.", "relationship": "A imagem ilustra «{title}», mas por si só não constitui prova factual."},
        "nl": {
            "link_plain": "Deze link is een bron om het onderwerp{title} te controleren of verder te verkennen.",
            "formula": "Deze formule hoort bij het onderdeel{title}. De formule verklaart: {context}", "link": "Deze link verwijst naar een bron bij het onderdeel{title}. Context: {context}", "image": "De afbeelding hoort bij het onderdeel{title} en laat zien: {context}", "gallery": "De afbeelding hoort bij het onderdeel{title} en laat zien: {context}", "code": "Het codeblok vult het onderdeel{title} aan. Het doel is: {context}", "table": "De tabel ordent de gegevens uit het onderdeel{title}, zodat ze te vergelijken zijn. Inhoud: {context}", "graph": "De grafiek geeft gegevens of verbanden uit het onderdeel{title} weer. Inhoud: {context}", "diagram": "Het schema toont een proces of relaties uit het onderdeel{title}. Beschrijving: {context}", "file": "Het bestand hoort bij het onderdeel{title}. In dit antwoord wordt het gebruikt voor: {context}", "audio": "Het audioblok hoort bij het onderdeel{title}: {context}", "video": "Het videoblok hoort bij het onderdeel{title}: {context}", "generated": "Dit is een gegenereerde illustratie, geen archieffoto.", "edited": "Vermelde wijzigingen: {note}", "formula_plain": "Dit wiskundige blok geeft een kwantitatief verband uit het onderdeel{title} weer. Interpreteer de symbolen in de context van het antwoord.", "table_plain": "De tabel groepeert verwante waarden om ze gemakkelijker te vergelijken.{details} Conclusies moeten gebaseerd zijn op de daadwerkelijk getoonde rijen.", "graph_plain": "De grafiek toont het verband tussen de asvariabelen. {details} Lees de trend af uit de weergegeven gegevens en vul ontbrekende waarden niet zelf in.", "diagram_plain": "Het schema toont een structuur of een reeks stappen. {details}", "block_plain": "Dit blok hoort bij het huidige onderdeel{title}. {details}", "open": "Open het blok om de inhoud te bekijken.", "columns": " Kolommen: {headers}.", "rows": " Aantal gegevensrijen: {count}.", "relationship": "De afbeelding illustreert „{title}”, maar is op zichzelf geen feitelijk bewijs."},
        "ja": {
            "link_plain": "このリンクは、{title}の内容を確認したり詳しく調べたりするための資料です。",
            "formula": "この数式はセクション{title}に関連しています。説明：{context}", "link": "このリンクはセクション{title}に関連する資料です。内容：{context}", "image": "この画像はセクション{title}に関連し、次の内容を示しています：{context}", "gallery": "この画像はセクション{title}に関連し、次の内容を示しています：{context}", "code": "このコードブロックはセクション{title}を補足します。目的：{context}", "table": "この表はセクション{title}のデータを整理して比較しやすくします。内容：{context}", "graph": "このグラフはセクション{title}のデータや関係を示しています。内容：{context}", "diagram": "この図はセクション{title}の手順や関係を示しています。説明：{context}", "file": "このファイルはセクション{title}に関連しています。この回答では次の目的で使用します：{context}", "audio": "この音声ブロックはセクション{title}に関連しています：{context}", "video": "この動画ブロックはセクション{title}に関連しています：{context}", "generated": "これは生成されたイラストであり、ストック写真ではありません。", "edited": "変更内容：{note}", "formula_plain": "この数式ブロックはセクション{title}の数量的な関係を表しています。記号は回答の文脈に沿って解釈してください。", "table_plain": "この表は関連する値をまとめ、比較しやすくしています。{details} 結論は表示された行だけに基づいてください。", "graph_plain": "このグラフは軸の変数間の関係を表しています。{details} 傾向は表示データから読み取り、欠けている値を推測で補わないでください。", "diagram_plain": "この図は構造または手順を示しています。{details}", "block_plain": "このブロックはセクション{title}に関連しています。{details}", "open": "ブロックを開いて内容を確認してください。", "columns": " 列：{headers}。", "rows": " データ行数：{count}。", "relationship": "この画像は「{title}」を示していますが、それだけで事実の証明にはなりません。"},
        "zh": {
            "link_plain": "此链接可用于核实或深入了解{title}相关内容。",
            "formula": "此公式与{title}部分有关，说明了：{context}", "link": "此链接指向与{title}部分相关的资料。内容：{context}", "image": "此图像与{title}部分相关，展示了：{context}", "gallery": "此图像与{title}部分相关，展示了：{context}", "code": "此代码块补充了{title}部分。用途：{context}", "table": "此表整理了{title}部分的数据，便于比较。内容：{context}", "graph": "此图表展示了{title}部分的数据或关系。内容：{context}", "diagram": "此示意图展示了{title}部分的流程或关系。说明：{context}", "file": "此文件与{title}部分相关，在本回答中用于：{context}", "audio": "此音频块与{title}部分相关：{context}", "video": "此视频块与{title}部分相关：{context}", "generated": "这是生成的插图，不是图库照片。", "edited": "记录的修改：{note}", "formula_plain": "此数学内容表示{title}部分中的数量关系。请结合回答上下文理解各个符号。", "table_plain": "此表汇总了相关数值，便于比较。{details} 结论应仅依据实际显示的行。", "graph_plain": "此图表展示了坐标轴变量之间的关系。{details} 请根据显示的数据判断趋势，不要推测缺失数值。", "diagram_plain": "此示意图展示了结构或步骤顺序。{details}", "block_plain": "此内容块与当前部分{title}有关。{details}", "open": "打开此内容块以查看详细内容。", "columns": " 列：{headers}。", "rows": " 数据行数：{count}。", "relationship": "该图像用于说明“{title}”，但单凭图像本身不能证明事实。"},
        "ko": {
            "link_plain": "이 링크는 {title} 주제를 확인하거나 더 자세히 살펴볼 수 있는 자료입니다.",
            "formula": "이 수식은 {title} 부분과 관련이 있으며 다음을 설명합니다: {context}", "link": "이 링크는 {title} 부분과 관련된 자료로 연결됩니다. 내용: {context}", "image": "이 이미지는 {title} 부분과 관련되며 다음을 보여 줍니다: {context}", "gallery": "이 이미지는 {title} 부분과 관련되며 다음을 보여 줍니다: {context}", "code": "이 코드 블록은 {title} 부분을 보완합니다. 목적: {context}", "table": "이 표는 {title} 부분의 데이터를 정리해 비교하기 쉽게 합니다. 내용: {context}", "graph": "이 그래프는 {title} 부분의 데이터나 관계를 나타냅니다. 내용: {context}", "diagram": "이 다이어그램은 {title} 부분의 과정이나 관계를 보여 줍니다. 설명: {context}", "file": "이 파일은 {title} 부분과 관련이 있으며, 이 답변에서는 다음 용도로 사용됩니다: {context}", "audio": "이 오디오 블록은 {title} 부분과 관련이 있습니다: {context}", "video": "이 비디오 블록은 {title} 부분과 관련이 있습니다: {context}", "generated": "이 이미지는 생성된 삽화이며 스톡 사진이 아닙니다.", "edited": "기록된 수정 사항: {note}", "formula_plain": "이 수학 블록은 {title} 부분의 정량적 관계를 나타냅니다. 기호는 답변의 문맥에 맞게 해석하세요.", "table_plain": "이 표는 관련 값을 모아 비교하기 쉽게 합니다. {details} 결론은 실제로 표시된 행에만 근거해야 합니다.", "graph_plain": "이 그래프는 축 변수 사이의 관계를 나타냅니다. {details} 추세는 표시된 데이터를 바탕으로 읽고 누락된 값은 추측하지 마세요.", "diagram_plain": "이 다이어그램은 구조 또는 단계의 순서를 보여 줍니다. {details}", "block_plain": "이 블록은 현재 섹션{title}과 관련이 있습니다. {details}", "open": "블록을 열어 내용을 확인하세요.", "columns": " 열: {headers}.", "rows": " 데이터 행 수: {count}.", "relationship": "이 이미지는 ‘{title}’을 보여 주지만, 이미지 자체만으로 사실을 입증하지는 않습니다."},
        "ar": {
            "link_plain": "يُدرج هذا الرابط كمصدر للتحقق من موضوع {title} أو التعمق فيه.",
            "formula": "ترتبط هذه المعادلة بالقسم {title} وتوضح: {context}", "link": "ينقل هذا الرابط إلى مصدر مرتبط بالقسم {title}. السياق: {context}", "image": "ترتبط هذه الصورة بالقسم {title} وتوضح: {context}", "gallery": "ترتبط هذه الصورة بالقسم {title} وتوضح: {context}", "code": "تُكمل كتلة الشيفرة القسم {title}. الغرض منها: {context}", "table": "ينظم الجدول بيانات القسم {title} لتسهيل المقارنة. المحتوى: {context}", "graph": "يعرض الرسم البياني بيانات أو علاقات القسم {title}. المحتوى: {context}", "diagram": "يوضح المخطط عملية أو علاقات في القسم {title}. الوصف: {context}", "file": "يرتبط الملف بالقسم {title} ويُستخدم في هذه الإجابة من أجل: {context}", "audio": "ترتبط كتلة الصوت بالقسم {title}: {context}", "video": "ترتبط كتلة الفيديو بالقسم {title}: {context}", "generated": "هذا رسم توضيحي مولّد، وليس صورة أرشيفية.", "edited": "التعديلات المسجلة: {note}", "formula_plain": "تمثل هذه الكتلة الرياضية علاقة كمية في القسم {title}. فسّر الرموز وفق سياق الإجابة.", "table_plain": "يجمع الجدول القيم المرتبطة لتسهيل المقارنة. {details} يجب أن تستند الاستنتاجات إلى الصفوف المعروضة فقط.", "graph_plain": "يعرض الرسم العلاقة بين متغيرات المحاور. {details} استخلص الاتجاه من البيانات الظاهرة ولا تفترض قيماً غير معروضة.", "diagram_plain": "يوضح المخطط بنية أو تسلسلاً من الخطوات. {details}", "block_plain": "ترتبط هذه الكتلة بالقسم الحالي {title}. {details}", "open": "افتح الكتلة للاطلاع على محتواها.", "columns": " الأعمدة: {headers}.", "rows": " عدد صفوف البيانات: {count}.", "relationship": "توضح الصورة موضوع «{title}»، لكنها لا تُعد دليلاً واقعياً بمفردها."},
        "hi": {
            "link_plain": "यह लिंक {title} विषय की जाँच करने या उसके बारे में और जानने के लिए स्रोत के रूप में दिया गया है।",
            "formula": "यह सूत्र {title} अनुभाग से संबंधित है। इसका अर्थ है: {context}", "link": "यह लिंक {title} अनुभाग से संबंधित स्रोत पर ले जाता है। संदर्भ: {context}", "image": "यह चित्र {title} अनुभाग से संबंधित है और दिखाता है: {context}", "gallery": "यह चित्र {title} अनुभाग से संबंधित है और दिखाता है: {context}", "code": "यह कोड ब्लॉक {title} अनुभाग को पूरा करता है। इसका उद्देश्य: {context}", "table": "यह तालिका {title} अनुभाग के आँकड़ों को तुलना के लिए व्यवस्थित करती है। सामग्री: {context}", "graph": "यह ग्राफ {title} अनुभाग के आँकड़े या संबंध दिखाता है। सामग्री: {context}", "diagram": "यह आरेख {title} अनुभाग की प्रक्रिया या संबंध दिखाता है। विवरण: {context}", "file": "यह फ़ाइल {title} अनुभाग से संबंधित है। इस उत्तर में इसका उपयोग: {context}", "audio": "यह ऑडियो ब्लॉक {title} अनुभाग से संबंधित है: {context}", "video": "यह वीडियो ब्लॉक {title} अनुभाग से संबंधित है: {context}", "generated": "यह AI द्वारा बनाया गया चित्रण है, संग्रह की वास्तविक तस्वीर नहीं।", "edited": "दर्ज किए गए बदलाव: {note}", "formula_plain": "यह गणितीय ब्लॉक {title} अनुभाग के मात्रात्मक संबंध को दर्शाता है। प्रतीकों को उत्तर के संदर्भ में समझें।", "table_plain": "तालिका संबंधित मानों को तुलना के लिए व्यवस्थित करती है। {details} निष्कर्ष केवल दिखाई गई पंक्तियों पर आधारित होने चाहिए।", "graph_plain": "ग्राफ अक्षों के चरों के बीच संबंध दिखाता है। {details} रुझान को दिखाए गए आँकड़ों से समझें; अनुपस्थित मानों का अनुमान न लगाएँ।", "diagram_plain": "यह आरेख संरचना या चरणों का क्रम दिखाता है। {details}", "block_plain": "यह ब्लॉक वर्तमान अनुभाग {title} से संबंधित है। {details}", "open": "सामग्री देखने के लिए ब्लॉक खोलें।", "columns": " कॉलम: {headers}।", "rows": " डेटा पंक्तियों की संख्या: {count}।", "relationship": "यह चित्र ‘{title}’ को दर्शाता है, लेकिन अपने आप में तथ्य का प्रमाण नहीं है।"},
        "el": {
            "link_plain": "Αυτός ο σύνδεσμος παρατίθεται ως πηγή για έλεγχο ή περαιτέρω διερεύνηση του θέματος{title}.",
            "formula": "Ο τύπος σχετίζεται με την ενότητα{title}. Εξηγεί: {context}", "link": "Ο σύνδεσμος οδηγεί σε πηγή σχετική με την ενότητα{title}. Πλαίσιο: {context}", "image": "Η εικόνα σχετίζεται με την ενότητα{title} και δείχνει: {context}", "gallery": "Η εικόνα σχετίζεται με την ενότητα{title} και δείχνει: {context}", "code": "Το μπλοκ κώδικα συμπληρώνει την ενότητα{title}. Σκοπός: {context}", "table": "Ο πίνακας οργανώνει τα δεδομένα της ενότητας{title} για σύγκριση. Περιεχόμενο: {context}", "graph": "Το γράφημα απεικονίζει δεδομένα ή σχέσεις της ενότητας{title}. Περιεχόμενο: {context}", "diagram": "Το διάγραμμα δείχνει μια διαδικασία ή σχέσεις της ενότητας{title}. Περιγραφή: {context}", "file": "Το αρχείο σχετίζεται με την ενότητα{title}. Σε αυτή την απάντηση χρησιμεύει για: {context}", "audio": "Το μπλοκ ήχου σχετίζεται με την ενότητα{title}: {context}", "video": "Το μπλοκ βίντεο σχετίζεται με την ενότητα{title}: {context}", "generated": "Πρόκειται για εικόνα που δημιουργήθηκε τεχνητά, όχι για φωτογραφία αρχείου.", "edited": "Καταγεγραμμένες αλλαγές: {note}", "formula_plain": "Αυτό το μαθηματικό μπλοκ αναπαριστά μια ποσοτική σχέση της ενότητας{title}. Ερμηνεύστε τα σύμβολα με βάση το πλαίσιο της απάντησης.", "table_plain": "Ο πίνακας συγκεντρώνει σχετικά δεδομένα για ευκολότερη σύγκριση. {details} Τα συμπεράσματα πρέπει να βασίζονται μόνο στις εμφανιζόμενες γραμμές.", "graph_plain": "Το γράφημα δείχνει τη σχέση μεταξύ των μεταβλητών των αξόνων. {details} Η τάση πρέπει να προκύπτει από τα εμφανιζόμενα δεδομένα, χωρίς επινόηση τιμών που λείπουν.", "diagram_plain": "Το διάγραμμα παρουσιάζει μια δομή ή μια ακολουθία βημάτων. {details}", "block_plain": "Αυτό το μπλοκ σχετίζεται με την τρέχουσα ενότητα{title}. {details}", "open": "Ανοίξτε το μπλοκ για να δείτε το περιεχόμενό του.", "columns": " Στήλες: {headers}.", "rows": " Αριθμός γραμμών δεδομένων: {count}.", "relationship": "Η εικόνα απεικονίζει το θέμα «{title}», αλλά από μόνη της δεν αποτελεί πραγματολογική απόδειξη."},
    }
    t = templates[language]
    context_templates = t
    if context:
        if block_type in context_templates:
            return context_templates[block_type].format(title=title_ref, context=context)

    if block_type == "link":
        description = str(_render_block_field(block, payload, "description", "summary") or "").strip()
        return description or t["link_plain"].format(title=title_ref)

    if block_type == "formula":
        formula_values = payload.get("formulas") or payload.get("latex_formulas") or []
        if not isinstance(formula_values, list):
            formula_values = [formula_values]
        for key in ("formula", "latex", "equation", "expression", "math"):
            value = payload.get(key)
            if value and value not in formula_values:
                formula_values.append(value)
        formulas = []
        for item in formula_values[:6]:
            value = (item.get("latex") or item.get("formula") or item.get("equation")) if isinstance(item, dict) else item
            if isinstance(value, str) and value.strip():
                formulas.append(re.sub(r"\s+", " ", value.strip())[:100])
        formula = ", ".join(formulas)
        base = f"{formula}. " if formula else ""
        return base + t["formula_plain"].format(title=title_ref)

    if block_type in {"image", "gallery"}:
        images = payload.get("images") or payload.get("items") or []
        if not isinstance(images, list):
            images = [images]
        descriptions = []
        for item in images[:5]:
            if isinstance(item, dict):
                desc = str(item.get("description") or item.get("alt") or item.get("title") or item.get("caption") or "").strip()
            else:
                desc = str(item).strip()
            if desc:
                descriptions.append(re.sub(r"\s+", " ", desc)[:220])
        described = "; ".join(descriptions)
        edit_note = str(_render_block_field(block, payload, "edit_description", "modification_summary", "changes", "change_summary") or "").strip()
        generated = str(payload.get("kind") or payload.get("source") or "").lower() in {"generated_image", "april_generated", "c_april_images_generator"} or bool(block.get("generated"))
        if edit_note:
            core = t["edited"].format(note=edit_note)
        elif described:
            core = ((t["generated"] + " ") if generated else "") + described
        else:
            subject_defaults = {
                "es": "el tema de la respuesta", "de": "das Thema der Antwort", "it": "il tema della risposta",
                "pl": "temat odpowiedzi", "pt": "o tema da resposta", "nl": "het onderwerp van het antwoord",
                "ja": "回答のテーマ", "zh": "回答中的主题", "ko": "답변의 주제", "ar": "موضوع الإجابة",
                "hi": "उत्तर का विषय", "el": "το θέμα της απάντησης",
            }
            subject = title or subject_defaults[language]
            core = t["relationship"].format(title=subject)
        if generated and t["generated"].lower() not in core.lower():
            core += " " + t["generated"]
        return core

    if block_type == "table":
        headers = payload.get("headers") or payload.get("columns") or payload.get("column_names") or []
        if isinstance(headers, dict):
            headers = list(headers.keys())
        if isinstance(headers, list):
            header_text = ", ".join(str(item.get("label") or item.get("name") or item) if isinstance(item, dict) else str(item) for item in headers[:8])
        else:
            header_text = str(headers)
        rows = payload.get("rows") or payload.get("data") or payload.get("values") or []
        row_count = len(rows) if isinstance(rows, list) else 0
        details = t["columns"].format(headers=header_text) if header_text else ""
        details += t["rows"].format(count=row_count) if row_count else ""
        return t["table_plain"].format(details=details)

    if block_type == "graph":
        axis_defaults = {
            "es": ("eje X", "eje Y"), "de": ("X-Achse", "Y-Achse"), "it": ("asse X", "asse Y"),
            "pl": ("oś X", "oś Y"), "pt": ("eixo X", "eixo Y"), "nl": ("X-as", "Y-as"),
            "ja": ("X軸", "Y軸"), "zh": ("X轴", "Y轴"), "ko": ("X축", "Y축"),
            "ar": ("المحور X", "المحور Y"), "hi": ("X-अक्ष", "Y-अक्ष"), "el": ("άξονας X", "άξονας Y"),
        }
        default_x, default_y = axis_defaults[language]
        x_axis = str(_render_block_field(block, payload, "x_axis", "xAxisLabel", "x_axis_label") or default_x)
        y_axis = str(_render_block_field(block, payload, "y_axis", "yAxisLabel", "y_axis_label") or default_y)
        graph_title = str(_render_block_field(block, payload, "title", "name") or title or "")
        details = f"{graph_title + ': ' if graph_title else ''}X — {x_axis}; Y — {y_axis}."
        return t["graph_plain"].format(details=details)

    if block_type == "diagram":
        labels = []
        for key in ("nodes", "elements", "steps", "items"):
            values = payload.get(key)
            if isinstance(values, list):
                for item in values[:10]:
                    if isinstance(item, dict):
                        label = str(item.get("label") or item.get("title") or item.get("name") or item.get("text") or "").strip()
                    else:
                        label = str(item).strip()
                    if label:
                        labels.append(label[:80])
        detail = str(payload.get("description") or payload.get("caption") or "").strip()
        if not detail and labels:
            heads = {
                "es": "Elementos principales", "de": "Hauptelemente", "it": "Elementi principali", "pl": "Główne elementy", "pt": "Elementos principais", "nl": "Belangrijkste onderdelen",
                "ja": "主な要素", "zh": "主要元素", "ko": "주요 요소", "ar": "العناصر الرئيسية", "hi": "मुख्य तत्व", "el": "Κύρια στοιχεία",
            }
            detail = heads[language] + ": " + "; ".join(dict.fromkeys(labels[:7]))
        return t["diagram_plain"].format(details=detail or t["open"])

    details = str(_render_block_field(block, payload, "description", "caption", "alt", "title", "filename", "name") or title or "")
    if not details:
        details = t["open"]
    return t["block_plain"].format(title=title_ref, details=details)


def _looks_like_image_prompt_echo(value: Any) -> bool:
    """Reject user commands and generator instructions masquerading as captions."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return False
    # A short conversational prefix must not make a copied imperative look like
    # a real caption (for example, "Вот что получилось: Нарисуй фотку...").
    text = re.sub(
        r"(?i)^(?:вот что получилось|вот результат|готово|here(?:'|’)s the result|here is the result|done|voilà le résultat|voici le résultat)\s*[:—-]\s*",
        "", text,
    ).strip()
    if re.match(
        r"(?i)^(?:user request|openai visual meaning|semantic generation prompt|generation prompt|"
        r"edit the supplied source image|follow the request|preserve the source image|"
        r"according to this exact user instruction|image prompt|prompt)\b",
        text,
    ):
        return True
    # Caption text should describe the result, not repeat the user's imperative.
    if re.match(
        r"(?i)^(?:нарисуй|нарисуйте|добавь|добавьте|измени|измените|сделай|сделайте|"
        r"создай|создайте|сгенерируй|сгенерируйте|покажи|покажите|убери|уберите|"
        r"удали|удалите|замени|замените|перенеси|перенесите|сохрани|сохраните|"
        r"draw|create|make|generate|add|edit|change|remove|delete|replace|preserve|"
        r"show me|put|insert|retouch|transform)\b",
        text,
    ):
        return True
    return False


def _caption_duplicates_answer(caption: str, answer: str) -> bool:
    """True only when a caption is effectively the same sentence as the answer."""
    def normalize(value: str) -> str:
        value = re.sub(r"(?i)^\s*(?:вот что получилось|готово|вот фотография|вот изображение|here(?:'|’)s the result|done)\s*[:—-]?\s*", "", value or "")
        value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE).lower()
        return re.sub(r"\s+", " ", value).strip()
    cap = normalize(caption)
    ans = normalize(answer)
    return bool(cap and ans and cap == ans)


def _naturalize_image_caption(value: Any, language: str = "ru") -> str:
    """Turn contract-style image explanations into a short conversational caption."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    text = re.sub(
        r"(?i)^\s*(?:\*\*|__)?(?:что показывает изображение|что показывает картинка|"
        r"описание изображения|пояснение к изображению|що показує зображення|"
        r"ce que montre l’image|what the image shows|what the picture shows|"
        r"was das bild zeigt|qué muestra la imagen)\s*[:.\-—]*\s*(?:\*\*|__)?",
        "", text,
    ).strip()
    # Remove the generated contract's mechanical lead-in but keep its specific detail.
    generic_leadins = (
        r"(?i)^это сгенерированная иллюстрация к текущему разделу\s*[:—-]\s*",
        r"(?i)^изображение связано с разделом.{0,180}?(?:наглядно|визуально )?показывает\s*[:—-]\s*",
        r"(?i)^картинка связана с разделом.{0,180}?(?:наглядно|визуально )?показывает\s*[:—-]\s*",
        r"(?i)^це згенерована ілюстрація до поточного розділу\s*[:—-]\s*",
        r"(?i)^зображення пов.?язане з розділом.{0,180}?(?:наочно|візуально )?показує\s*[:—-]\s*",
        r"(?i)^this image is associated with the section.{0,180}?(?:and )?(?:illustrates|shows)\s*[:—-]\s*",
        r"(?i)^this is a generated illustration for the current section\s*[:—-]\s*",
        r"(?i)^l’image est liée à la section.{0,180}?(?:et )?(?:illustre|montre)\s*[:—-]\s*",
    )
    for pattern in generic_leadins:
        text = re.sub(pattern, "", text, count=1).strip()
    text = re.sub(r"\s*([,;])\s*", r"\1 ", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" .;:-—")
    if not text:
        return ""
    # Keep first-person, natural phrasing when present; otherwise add a small
    # conversational bridge instead of a machine-generated heading.
    low = text.lower()
    if language == "uk":
        if not re.match(r"^(?:ось|готово|додала|змінила|зберегла|підготувала|я\s|зрозуміла)", low):
            text = "Ось що вийшло: " + text
    elif language in {"en", "en-us", "en-gb"}:
        if not re.match(r"^(?:here|done|i\s|i've|i’ve|understood|i understand)", low):
            text = "Here’s how it turned out: " + text
    elif language == "fr":
        if not re.match(r"^(?:voici|c’est prêt|j’ai|j'ai|j’ajoute|j'ajoute|j’ai ajouté|j'ai ajouté|j’ai compris|j'ai compris)", low):
            text = "Voilà le résultat : " + text
    else:
        if not re.match(r"^(?:вот|готово|добавила|добавляю|изменила|сохранила|подготовила|сделала|внесла|поняла|я\s)", low):
            text = "Вот что получилось: " + text
    return text[:900].rstrip()


def _fallback_render_explanation(block_type: str, block: Dict[str, Any], answer: str, language: str) -> str:
    payload = _render_payload(block)
    section, context = _render_section_context(block_type, block, answer)
    block_title = str(_render_block_field(block, payload, "step_title", "title", "section") or "").strip()
    title = str(section or block_title).strip()
    title_for_text = f" «{title[:100]}»" if title else ""
    if block_type in {"image", "gallery"}:
        edit_note = str(_render_block_field(block, payload, "edit_description", "modification_summary", "changes", "change_summary") or "").strip()
        images = payload.get("images") or payload.get("items") or []
        if not isinstance(images, list):
            images = [images]
        descriptions = []
        for item in images[:4]:
            desc = (item.get("description") or item.get("alt") or item.get("title") or item.get("caption") or "") if isinstance(item, dict) else item
            desc = re.sub(r"\s+", " ", str(desc or "")).strip()
            if desc:
                descriptions.append(desc[:220])
        described = "; ".join(descriptions)
        detail = edit_note or described or context or title
        lang = str(language or "ru").lower()
        if edit_note:
            if lang in {"uk", "ua", "uk-ua"}:
                caption = f"Готово — я внесла цю зміну: {detail}. Інші деталі сцени залишила без змін."
            elif lang in {"en", "en-us", "en-gb"}:
                caption = f"Done — I made this change: {detail}. I left the rest of the scene as it was."
            elif lang == "fr":
                caption = f"C’est fait — j’ai appliqué cette modification : {detail}. J’ai conservé le reste de la scène."
            else:
                caption = f"Готово — я внесла эту правку: {detail}. Остальную сцену оставила как была."
        elif detail:
            caption = _naturalize_image_caption(str(detail), lang)
        elif lang in {"uk", "ua", "uk-ua"}:
            caption = "Ось результат за твоїм запитом."
        elif lang in {"en", "en-us", "en-gb"}:
            caption = "Here’s the result based on your request."
        elif lang == "fr":
            caption = "Voici le résultat selon ta demande."
        else:
            caption = "Вот результат по твоему запросу."
        return caption[:1000]
    if language in {"es", "de", "it", "pl", "pt", "nl", "ja", "zh", "ko", "ar", "hi", "el"}:
        return _fallback_render_explanation_extended(block_type, block, answer, language)
    if context:
        if language == "uk":
            bodies = {
                "formula": f"Ця формула пов’язана з розділом{title_for_text}. Вона пояснює: {context}",
                "link": f"Посилання веде до джерела, доданого для розділу{title_for_text}. Контекст відповіді: {context}",
                "image": f"Зображення пов’язане з розділом{title_for_text} і візуально показує: {context}",
                "gallery": f"Зображення пов’язане з розділом{title_for_text} і візуально показує: {context}",
                "code": f"Кодовий блок доповнює розділ{title_for_text}. Пояснення його призначення: {context}",
                "table": f"Таблиця впорядковує дані з розділу{title_for_text}. Її зміст: {context}",
                "graph": f"Графік візуалізує залежність або дані з розділу{title_for_text}. Його зміст: {context}",
                "diagram": f"Схема показує процес або зв’язки з розділу{title_for_text}. Відповідний опис: {context}",
                "file": f"Файл пов’язаний з розділом{title_for_text}. У відповіді він потрібен для: {context}",
                "audio": f"Аудіоблок пов’язаний з розділом{title_for_text}: {context}",
                "video": f"Відеоблок пов’язаний з розділом{title_for_text}: {context}",
            }
        elif language == "fr":
            bodies = {
                "formula": f"Cette formule se rapporte à la section{title_for_text}. Elle exprime : {context}",
                "link": f"Ce lien renvoie à une source associée à la section{title_for_text}. Le contexte de la réponse est : {context}",
                "image": f"Cette image se rapporte à la section{title_for_text} et illustre : {context}",
                "gallery": f"Cette image se rapporte à la section{title_for_text} et illustre : {context}",
                "code": f"Ce bloc de code complète la section{title_for_text}. Son rôle est décrit ici : {context}",
                "table": f"Ce tableau organise les données de la section{title_for_text} : {context}",
                "graph": f"Ce graphique visualise les données ou la relation de la section{title_for_text} : {context}",
                "diagram": f"Ce schéma montre les étapes ou relations de la section{title_for_text} : {context}",
                "file": f"Ce fichier se rapporte à la section{title_for_text} : {context}",
                "audio": f"Ce bloc audio se rapporte à la section{title_for_text} : {context}",
                "video": f"Ce bloc vidéo se rapporte à la section{title_for_text} : {context}",
            }
        else:
            bodies = {
                "formula": f"Эта формула связана с разделом{title_for_text}. Она объясняет: {context}" if language == "ru" else f"This formula belongs to the section{title_for_text}. It explains: {context}",
                "link": f"Ссылка ведёт к источнику, указанному для раздела{title_for_text}. В контексте ответа она нужна для проверки и углубления темы: {context}" if language == "ru" else f"This link points to a source associated with the section{title_for_text}. In this answer it is provided to verify or explore: {context}",
                "image": f"Изображение связано с разделом{title_for_text} и наглядно показывает: {context}" if language == "ru" else f"This image is associated with the section{title_for_text} and illustrates: {context}",
                "gallery": f"Изображение связано с разделом{title_for_text} и наглядно показывает: {context}" if language == "ru" else f"This image is associated with the section{title_for_text} and illustrates: {context}",
                "code": f"Кодовый блок дополняет раздел{title_for_text}. Его назначение по поясняющему тексту: {context}" if language == "ru" else f"This code block complements the section{title_for_text}. Its purpose in the answer is: {context}",
                "table": f"Таблица структурирует данные из раздела{title_for_text}. Она нужна, чтобы увидеть: {context}" if language == "ru" else f"This table organizes the data in the section{title_for_text}. It helps show: {context}",
                "graph": f"График визуализирует данные или зависимость из раздела{title_for_text}. Его смысл: {context}" if language == "ru" else f"This graph visualizes the data or relationship in the section{title_for_text}: {context}",
                "diagram": f"Схема показывает этапы или связи из раздела{title_for_text}. Пояснение: {context}" if language == "ru" else f"This diagram shows the steps or relationships in the section{title_for_text}: {context}",
                "file": f"Файл относится к разделу{title_for_text}. По пояснению в ответе он нужен для: {context}" if language == "ru" else f"This file relates to the section{title_for_text}: {context}",
                "audio": f"Аудиоблок относится к разделу{title_for_text}: {context}" if language == "ru" else f"This audio block relates to the section{title_for_text}: {context}",
                "video": f"Видеоблок относится к разделу{title_for_text}: {context}" if language == "ru" else f"This video block relates to the section{title_for_text}: {context}",
            }
        explanation = bodies.get(block_type, context)
        if block_type in {"image", "gallery"}:
            edit_note = str(_render_block_field(block, payload, "edit_description", "modification_summary", "changes", "change_summary") or "").strip()
            generated = str(payload.get("kind") or payload.get("source") or "").lower() in {"generated_image", "april_generated", "c_april_images_generator"} or bool(block.get("generated"))
            if edit_note:
                if language == "uk":
                    explanation += f" Окремо зафіксовані зміни: {edit_note}"
                elif language == "ru":
                    explanation += f" Отдельно указанные изменения: {edit_note}"
                elif language == "fr":
                    explanation += f" Modifications indiquées : {edit_note}"
                else:
                    explanation += f" Explicitly recorded changes: {edit_note}"
            if generated:
                caveat = " Це згенерована ілюстрація, а не архівна фотографія." if language == "uk" else " Это сгенерированная иллюстрация, а не архивная фотография." if language == "ru" else " Il s’agit d’une illustration générée, pas d’une photographie d’archive." if language == "fr" else " It is a generated illustration, not an archival photograph."
                if not any(marker in explanation.lower() for marker in ("згенерована ілюстрація", "сгенерированная иллюстрация", "illustration générée", "generated illustration")):
                    explanation += caveat
        return explanation

    # Renderer-specific, source-grounded fallbacks for older model output that
    # doesn't yet include an explanation field or a matching narrative section.
    if block_type == "formula":
        formula_values = payload.get("formulas") or payload.get("latex_formulas") or []
        if not isinstance(formula_values, list):
            formula_values = [formula_values]
        for key in ("formula", "latex", "equation", "expression", "math"):
            value = payload.get(key)
            if value and value not in formula_values:
                formula_values.append(value)
        formulas = []
        for item in formula_values[:6]:
            value = item.get("latex") or item.get("formula") or item.get("equation") if isinstance(item, dict) else item
            if isinstance(value, str) and value.strip():
                formulas.append(re.sub(r"\s+", " ", value.strip())[:100])
        formula = ", ".join(formulas)
        normalized = re.sub(r"[\s{}\\$()^_]", "", formula).lower().replace("²", "2")
        if re.search(r"e=mc2", normalized):
            specific = ("Эта формула выражает эквивалентность массы и энергии: E — энергия, m — масса, c — скорость света; множитель c² показывает, почему даже небольшая масса соответствует большой энергии." if language == "ru" else "Ця формула виражає еквівалентність маси та енергії: E — енергія, m — маса, c — швидкість світла; множник c² показує, чому невелика маса відповідає великій енергії." if language == "uk" else "Cette formule exprime l’équivalence masse-énergie : E est l’énergie, m la masse et c la vitesse de la lumière." if language == "fr" else "This formula expresses mass–energy equivalence: E is energy, m is mass, and c is the speed of light; the factor c² explains why a small mass corresponds to a large amount of energy.")
            return specific
        if formula:
            base = f"{formula}. "
        else:
            base = ""
        if language == "uk":
            return f"{base}Цей математичний блок записує кількісний зв’язок між величинами, згаданими в поточному розділі{title_for_text}. Не трактуйте символи окремо від визначень і припущень у тексті відповіді."
        if language == "ru":
            return f"{base}Этот математический блок записывает количественную связь между величинами из текущего раздела{title_for_text}. Символы нужно толковать вместе с определениями и условиями, приведёнными в тексте ответа."
        if language == "fr":
            return f"{base}Ce bloc mathématique représente une relation entre les grandeurs du sujet{title_for_text}. Les symboles doivent être lus avec les définitions et hypothèses données dans la réponse."
        return f"{base}This mathematical block records a quantitative relationship relevant to{title_for_text or ' the current topic'}. Interpret its symbols using the definitions and assumptions in the answer."

    if block_type == "link":
        links = payload.get("links") if isinstance(payload.get("links"), list) else []
        if not links:
            links = [payload]
        items = []
        for item in links[:3]:
            if not isinstance(item, dict):
                continue
            label = str(item.get("title") or item.get("name") or item.get("description") or "").strip()
            url = str(item.get("url") or item.get("href") or "").strip()
            domain_match = re.search(r"https?://([^/\s?#]+)", url, re.IGNORECASE)
            destination = domain_match.group(1) if domain_match else url
            if label and destination:
                items.append(f"{label} ({destination})")
            elif label or destination:
                items.append(label or destination)
        subject = "; ".join(items) or title or "источник из этого ответа"
        if language == "uk":
            return f"Посилання відкриває {subject}. Його додано як джерело для перевірки або поглиблення поточної теми; точний зміст сторінки слід звірити після відкриття."
        if language == "ru":
            return f"Ссылка открывает {subject}. Она добавлена как источник для проверки или углубления текущей темы; точное содержание страницы следует сверить после перехода."
        if language == "fr":
            return f"Ce lien ouvre {subject}. Il sert de source pour vérifier ou approfondir le sujet ; le contenu exact doit être confirmé sur la page ouverte."
        return f"This link opens {subject}. It is included as a source to verify or explore the current topic; confirm the exact page contents after opening it."

    if block_type == "code":
        code = str(_render_block_field(block, payload, "code", "content", "text") or payload.get("source") or "")
        language_name = str(_render_block_field(block, payload, "language", "lang") or "text")
        filename = str(_render_block_field(block, payload, "filename", "file_name") or "").strip()
        symbols = re.findall(r"(?m)^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(|^\s*class\s+([A-Za-z_]\w*)\b|^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_]\w*)\s*\(", code)
        symbol_names = [next((part for part in row if part), "") for row in symbols]
        symbol_text = ", ".join(dict.fromkeys(symbol_names[:5]))
        file_text = f" «{filename[:100]}»" if filename else ""
        if language == "uk":
            return f"Це блок коду мовою {language_name}{file_text}. {('У ньому визначено: ' + symbol_text + '. ') if symbol_text else ''}Використовуйте його разом із поясненням до цього кроку; без контексту решти проєкту не можна надійно стверджувати про побічні ефекти під час запуску."
        if language == "ru":
            return f"Это блок кода на {language_name}{file_text}. {('В нём определены: ' + symbol_text + '. ') if symbol_text else ''}Используйте его вместе с пояснением к этому шагу; без остального контекста проекта нельзя надёжно утверждать о побочных эффектах при запуске."
        if language == "fr":
            return f"Ce bloc contient du code {language_name}{file_text}. {('Les éléments définis sont : ' + symbol_text + '. ') if symbol_text else ''}Il doit être interprété avec le contexte du projet ; sans celui-ci, les effets à l’exécution ne peuvent pas être affirmés avec certitude."
        return f"This block contains {language_name} code{file_text}. {('It defines: ' + symbol_text + '. ') if symbol_text else ''}Interpret it in the surrounding project context; runtime side effects cannot be stated reliably without the rest of the project."

    if block_type in {"image", "gallery"}:
        images = payload.get("images") or payload.get("items") or payload.get("gallery") or []
        if isinstance(images, dict):
            images = [images]
        image_descriptions = []
        for image in images[:3] if isinstance(images, list) else []:
            if not isinstance(image, dict):
                continue
            description = str(image.get("description") or image.get("alt") or image.get("title") or image.get("caption") or "").strip()
            if description:
                description = re.sub(r"\s+", " ", description)[:220]
                image_descriptions.append(description)
        described = "; ".join(image_descriptions)
        generated = str(payload.get("kind") or payload.get("source") or "").lower() in {"generated_image", "april_generated", "c_april_images_generator"} or bool(block.get("generated"))
        edit_note = str(_render_block_field(block, payload, "edit_description", "modification_summary", "changes", "change_summary") or "").strip()
        if edit_note:
            core = f"Изображение показывает внесённые изменения: {edit_note}" if language == "ru" else f"Зображення показує внесені зміни: {edit_note}" if language == "uk" else f"L’image montre les modifications suivantes : {edit_note}" if language == "fr" else f"The image shows these changes: {edit_note}"
        elif described:
            core = ("Это сгенерированная иллюстрация к текущему разделу: " if language == "ru" and generated else "Це згенерована ілюстрація до поточного розділу: " if language == "uk" and generated else "Il s’agit d’une illustration générée pour cette section : " if language == "fr" and generated else "This is a generated illustration for the current section: " if generated else "Это изображение, связанное с текущим разделом: " if language == "ru" else "Це зображення, пов’язане з поточним розділом: " if language == "uk" else "Cette image est associée à la section actuelle : " if language == "fr" else "This image is associated with the current section: ") + described
        else:
            subject = title or "тему текущего ответа"
            core = f"Изображение относится к теме «{subject}»; его роль — визуальная иллюстрация, а не самостоятельное подтверждение фактов." if language == "ru" else f"Зображення стосується теми «{subject}»; воно є візуальною ілюстрацією, а не самостійним підтвердженням фактів." if language == "uk" else f"L’image illustre le sujet « {subject} » sans constituer à elle seule une preuve factuelle." if language == "fr" else f"The image illustrates “{subject}”; it is not, by itself, evidence for a factual claim."
        if generated:
            caveat = " Это сгенерированная иллюстрация, а не архивная фотография." if language == "ru" else " Це згенерована ілюстрація, а не архівна фотографія." if language == "uk" else " Il s’agit d’une illustration générée, pas d’une photographie d’archive." if language == "fr" else " It is a generated illustration, not an archival photograph."
            if "генерированная иллюстрация" not in core.lower() and "згенерована ілюстрація" not in core.lower() and "illustration générée" not in core.lower() and "generated illustration" not in core.lower():
                core += caveat
        return core

    if block_type == "table":
        headers = payload.get("headers") or payload.get("columns") or payload.get("column_names") or []
        if isinstance(headers, dict):
            headers = list(headers.keys())
        if isinstance(headers, list):
            header_text = ", ".join(str(item.get("label") or item.get("name") or item) if isinstance(item, dict) else str(item) for item in headers[:8])
        else:
            header_text = str(headers)
        rows = payload.get("rows") or payload.get("data") or payload.get("values") or []
        row_count = len(rows) if isinstance(rows, list) else 0
        details = f" Столбцы: {header_text}." if header_text else ""
        details += f" Количество строк данных: {row_count}." if row_count else ""
        if language == "uk":
            return f"Таблиця збирає пов’язані значення в одному місці, щоб їх можна було зіставити.{details} Висновок слід робити за фактичними рядками таблиці, а не за відсутніми даними."
        if language == "ru":
            return f"Таблица собирает связанные значения, чтобы их было удобно сопоставить.{details} Вывод следует делать по фактическим строкам таблицы, а не по отсутствующим данным."
        if language == "fr":
            return f"Ce tableau regroupe les valeurs pour faciliter leur comparaison.{details} La conclusion doit être fondée sur les lignes réellement affichées."
        return f"This table groups related values for comparison.{details} Any takeaway should be based on the rows actually shown."

    if block_type == "graph":
        axis_defaults = {"ru": ("ось X", "ось Y"), "uk": ("вісь X", "вісь Y"), "fr": ("axe X", "axe Y"), "en": ("X axis", "Y axis")}
        default_x, default_y = axis_defaults.get(language, axis_defaults["en"])
        x_axis = str(_render_block_field(block, payload, "x_axis", "xAxisLabel", "x_axis_label") or default_x)
        y_axis = str(_render_block_field(block, payload, "y_axis", "yAxisLabel", "y_axis_label") or default_y)
        title_value = str(_render_block_field(block, payload, "title", "name") or title or "")
        details = f"{title_value + ': ' if title_value else ''}X — {x_axis}; Y — {y_axis}."
        if language == "uk":
            return f"Графік показує залежність між величинами, відкладеними по осях. {details} Тренд потрібно читати за відображеними точками або поверхнею; відсутні значення не домислюються."
        if language == "ru":
            return f"График показывает зависимость между величинами по осям. {details} Тренд следует читать по отображённым точкам или поверхности; отсутствующие значения не домысливаются."
        if language == "fr":
            return f"Le graphique représente une relation entre les grandeurs des axes. {details} La tendance doit être lue à partir des points ou de la surface affichés, sans inventer de valeurs manquantes."
        return f"The graph represents a relationship between the axis variables. {details} Read the trend from the displayed points or surface; missing values are not inferred."

    if block_type == "diagram":
        labels: List[str] = []
        for key in ("nodes", "elements", "steps", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                for item in value[:10]:
                    if isinstance(item, dict):
                        label = str(item.get("label") or item.get("title") or item.get("name") or item.get("text") or "").strip()
                    else:
                        label = str(item).strip()
                    if label:
                        labels.append(label[:80])
        description = str(payload.get("description") or payload.get("caption") or "").strip()
        detail = description or ("Основные элементы: " + "; ".join(dict.fromkeys(labels[:7])) if labels else "")
        if language == "uk":
            return f"Схема візуально пояснює структуру або послідовність кроків. {detail or 'Зв’язки слід читати за стрілками та підписами в самій схемі.'}"
        if language == "ru":
            return f"Схема визуально поясняет структуру или последовательность шагов. {detail or 'Связи следует читать по стрелкам и подписям в самой схеме.'}"
        if language == "fr":
            return f"Ce schéma illustre une structure ou une succession d’étapes. {detail or 'Lisez les relations à partir des flèches et des libellés affichés.'}"
        return f"This diagram illustrates a structure or sequence of steps. {detail or 'Read the relationships from the arrows and labels shown.'}"

    # File, audio and video blocks may have only a title/caption and no textual
    # body; describe the visible metadata without inventing its contents.
    details = str(_render_block_field(block, payload, "description", "caption", "alt", "title", "filename", "name") or title or "")
    if language == "ru":
        return f"Этот блок связан с текущим разделом{title_for_text}. {details or 'Откройте рендер, чтобы ознакомиться с его содержимым.'}"
    if language == "uk":
        return f"Цей блок пов’язаний із поточним розділом{title_for_text}. {details or 'Відкрийте рендер, щоб ознайомитися з його вмістом.'}"
    if language == "fr":
        return f"Ce bloc est associé à la section actuelle{title_for_text}. {details or 'Ouvrez le bloc pour consulter son contenu.'}"
    return f"This block is associated with the current section{title_for_text}. {details or 'Open the renderer to inspect its content.'}"


def _explanation_body_for_dedupe(value: Any) -> str:
    text = str(value or "").strip()
    # Strip only known renderer labels, including bold Markdown labels. Repeat
    # because older responses occasionally contain two stacked labels.
    labels = (
        r"formula explanation|what the image shows|what the graph shows|how to read the table|"
        r"what the code does|what the diagram shows|пояснение|пояснення|explication|explanation|"
        r"explicación|explicação|explicacao|erklärung|spiegazione|objaśnienie|wyjaśnienie|uitleg|"
        r"説明|说明|설명|شرح|व्याख्या|επεξήγηση"
    )
    for _ in range(3):
        updated = re.sub(
            rf"^\s*\*\*\s*(?:{labels})\b[^*]*\*\*\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        if updated == text:
            updated = re.sub(
                rf"^\s*(?:{labels})\b[^:\n]*\s*[:.]\s*",
                "",
                text,
                flags=re.IGNORECASE,
            )
        if updated == text:
            break
        text = updated.strip()
    return text.strip()


def _strip_duplicate_explanations_from_narrative(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep one explanation per renderer and avoid repeating it in the narrative."""
    text_types = {"text", "markdown", "message", "message_text"}

    # Older provider responses can include an explicit explanation and the
    # contract can also synthesize one immediately after the renderer. Keep the
    # first linked explanation in stream order so it remains adjacent to its
    # owner, then drop later copies for the same render id.
    seen_targets: set[str] = set()
    unique_blocks: List[Dict[str, Any]] = []
    for block in blocks:
        if isinstance(block, dict) and _scene_block_type(block) in text_types:
            target = str(block.get("explanation_for_block_id") or block.get("explanation_for") or "").strip()
            if target:
                if target in seen_targets:
                    continue
                seen_targets.add(target)
        unique_blocks.append(block)
    blocks = unique_blocks

    explanation_bodies: List[str] = []
    for block in blocks:
        if not isinstance(block, dict) or _scene_block_type(block) not in text_types:
            continue
        source = str(block.get("source") or "").lower()
        if not (block.get("explanation_for_block_id") or block.get("explanation_for") or "render_explanation_contract" in source):
            continue
        body = _explanation_body_for_dedupe(_scene_text(block))
        if len(body) >= 48:
            explanation_bodies.append(body)

    if not explanation_bodies:
        return blocks

    for block in blocks:
        if not isinstance(block, dict) or _scene_block_type(block) not in text_types:
            continue
        source = str(block.get("source") or "").lower()
        if block.get("explanation_for_block_id") or block.get("explanation_for") or "render_explanation_contract" in source:
            continue
        visible_source = _scene_text(block)
        if not visible_source:
            continue

        cleaned_visible = visible_source
        changed = False
        for body in explanation_bodies:
            # Match whitespace flexibly, while otherwise requiring an exact copy.
            # This avoids risky semantic deletion of merely related prose.
            pattern = re.compile(r"\s+".join(re.escape(part) for part in re.split(r"\s+", body)), re.IGNORECASE)
            cleaned_visible, removed = pattern.subn("", cleaned_visible, count=1)
            changed = changed or bool(removed)
        if not changed:
            continue

        # If the copied sentence had a bold explanation label immediately before
        # it, do not leave that label stranded as a second empty explanation.
        cleaned_visible = re.sub(
            r"(?i)\*\*(?:formula explanation|what the image shows|what the graph shows|how to read the table|what the code does|what the diagram shows|пояснение[^*]*|пояснення[^*]*)\*\*\s*(?=\n|$)",
            "",
            cleaned_visible,
        )
        cleaned_visible = re.sub(r"[ \t]{2,}", " ", cleaned_visible)
        cleaned_visible = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", cleaned_visible).strip()
        for key in ("answer", "content", "summary", "text", "markdown", "display_text"):
            value = block.get(key)
            if isinstance(value, str) and value.strip() == visible_source.strip():
                block[key] = cleaned_visible
        payload = block.get("payload")
        if isinstance(payload, dict):
            for key in ("answer", "content", "summary", "text", "markdown", "display_text"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip() == visible_source.strip():
                    payload[key] = cleaned_visible

    return blocks


def _ensure_premium_render_explanations(blocks: List[Dict[str, Any]], answer: str, language_hint: Any = "") -> List[Dict[str, Any]]:
    """Guarantee a visible text explanation immediately after every concrete Premium renderer.

    Provider-created `explanation` is preferred. Older output is repaired from the
    matching answer section and actual renderer payload; this never creates a
    renderer or invents a URL, equation, row, image edit, or numeric data.
    """
    language = _explanation_language(answer, language_hint)
    ordered: List[Dict[str, Any]] = []
    additions = 0
    for original_index, original in enumerate(blocks):
        if not isinstance(original, dict):
            continue
        block = dict(original)
        block_type = _scene_block_type(block)
        if block_type not in _PREMIUM_EXPLAINED_RENDER_TYPES or not _scene_payload_has_content(block_type, _render_payload(block), block):
            ordered.append(block)
            continue

        # Keep stable references even when the renderer had no explicit block id.
        block_id = str(block.get("block_id") or block.get("id") or f"block_{original_index + 1}").strip()
        block.setdefault("block_id", block_id)
        ordered.append(block)

        # If the source explicitly has a following explanation linked to this block,
        # preserve it and do not duplicate it.
        following = blocks[original_index + 1] if original_index + 1 < len(blocks) else None
        if isinstance(following, dict) and _scene_block_type(following) in {"text", "markdown", "message", "message_text"}:
            linked_to = str(following.get("explanation_for_block_id") or following.get("explanation_for") or "").strip()
            if linked_to and linked_to in {block_id, str(block.get("id") or "")}:
                continue

        # For an anchored renderer with a real continuation, the next text
        # fragment is already the explanation in context. Avoid inserting a
        # second, synthetic paraphrase between that fragment and the answer.
        if block.get("_anchor_has_continuation") and isinstance(following, dict) and _scene_block_type(following) in {"text", "markdown", "message", "message_text"}:
            continue

        payload = _render_payload(block)
        explanation = str(_render_block_field(block, payload, "explanation", "render_explanation", "what_it_shows") or "").strip()
        if block_type in {"image", "gallery"} and _looks_like_image_prompt_echo(explanation):
            explanation = ""
        if len(explanation) < 24:
            description = str(_render_block_field(block, payload, "description", "summary") or "").strip()
            if len(description) >= 48 and not (
                block_type in {"image", "gallery"} and _looks_like_image_prompt_echo(description)
            ):
                explanation = description
        if len(explanation) < 24:
            explanation = _fallback_render_explanation(block_type, block, answer, language)
        if not explanation:
            continue
        if block_type in {"image", "gallery"}:
            explanation = _naturalize_image_caption(explanation, language)
            if _looks_like_image_prompt_echo(explanation):
                # If no grounded image-specific description is available, prefer
                # a brief ready-state caption over exposing an instruction/prompt.
                explanation = {
                    "uk": "Готово — зображення створено за твоїм запитом.",
                    "en": "Done — the image is ready.",
                    "fr": "C’est prêt — l’image a été créée.",
                    "es": "Listo: la imagen está preparada.",
                    "de": "Fertig — das Bild ist erstellt.",
                }.get(language, "Готово — изображение создано по вашему запросу.")
            if _caption_duplicates_answer(explanation, answer):
                # The canonical answer is already shown in the same turn. Do not
                # repeat that exact sentence as a second block below the image.
                continue
            already_labeled = True
            prefix = ""
        else:
            already_labeled = bool(re.match(
                r"(?i)^\s*(?:\*\*|__)?\s*(?:пояснение|пояснення|explication|explanation|formula explanation|what the image shows|what the graph shows|how to read the table|what the code does|what the diagram shows|explicación|explicação|explicacao|erklärung|spiegazione|objaśnienie|wyjaśnienie|uitleg|説明|说明|설명|شرح|व्याख्या|επεξήγηση)\b",
                explanation,
            ))
            already_labeled = already_labeled or explanation.lstrip().startswith(("数式の説明", "画像の内容", "コードの動作", "公式说明", "图像内容", "代码的作用", "수식 설명", "이미지 설명", "코드의 기능"))
            prefix = _localized_explanation_prefix(language, block_type)
            if not already_labeled and not explanation.lstrip().lower().startswith(prefix.lower()):
                explanation = f"**{prefix}.** {explanation}"
        explanation = explanation[:1400]

        step_index = block.get("step_index", 1)
        explanation_block = {
            "type": "text",
            "artifact_type": "text",
            "renderer": "MessageTextBlock",
            "viewer": "MessageTextBlock",
            "content": explanation,
            "text": explanation,
            "block_id": f"explanation_{block_id}",
            "explanation_for_block_id": block_id,
            "related_block_ids": [block_id],
            "step_index": step_index,
            "step_title": ("" if block_type in {"image", "gallery"} else f"{_localized_explanation_prefix(language, block_type)}"[:100]),
            "sequence_index": len(ordered),
            "source": "premium_render_explanation_contract",
        }
        ordered.append(explanation_block)
        additions += 1

    ordered = _strip_duplicate_explanations_from_narrative(ordered)

    try:
        if additions:
            print("[APRIL_RENDER_EXPLANATION_ENRICHMENT] " + __import__("json").dumps({
                "status": "added_inline_explanations",
                "added": additions,
                "language": language,
                "render_types": [str(block.get("type") or "") for block in ordered if isinstance(block, dict) and str(block.get("type") or "").lower() in _PREMIUM_EXPLAINED_RENDER_TYPES],
            }, ensure_ascii=False, separators=(",", ":")), flush=True)
    except Exception:
        pass
    return ordered


def _set_scene_text_aliases(block: Dict[str, Any], value: str) -> None:
    """Synchronize visible text aliases without duplicating the full narrative."""
    text_keys = ("content", "text", "markdown", "display_text")
    found = False
    for key in text_keys:
        if isinstance(block.get(key), str):
            block[key] = value
            found = True
    if not found:
        block["content"] = value
    payload = block.get("payload")
    if isinstance(payload, dict):
        payload = dict(payload)
        payload_found = False
        for key in text_keys:
            if isinstance(payload.get(key), str):
                payload[key] = value
                payload_found = True
        if not payload_found and any(key in payload for key in ("content", "text", "markdown", "display_text")):
            payload["content"] = value
        block["payload"] = payload


def _interleave_scene_blocks_by_anchor(blocks: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], bool]:
    """Place renderer blocks after exact provider-authored anchors in the answer.

    This implements the existing provider contract (`anchor_text` / `insert_after_text`)
    without topic keywords or new intent triggers. The sentence remains in the left
    text fragment; the following explanation continues in a distinct fragment.
    Unmatched anchors are left in their original stream position rather than guessed.
    """
    stream = [dict(block) for block in blocks if isinstance(block, dict)]
    anchored_blocks = [
        block for block in stream
        if _scene_block_type(block) not in {"text", "markdown", "message", "message_text"}
        and not bool(block.get("final_output"))
        and str(block.get("anchor_text") or block.get("insert_after_text") or (
            (block.get("payload") or {}).get("anchor_text") if isinstance(block.get("payload"), dict) else ""
        ) or "").strip()
    ]
    changed = False
    used_ids = {str(b.get("block_id") or b.get("id") or "") for b in stream}

    for visual in anchored_blocks:
        if not any(candidate is visual for candidate in stream):
            continue
        payload = visual.get("payload") if isinstance(visual.get("payload"), dict) else {}
        anchor = str(visual.get("anchor_text") or visual.get("insert_after_text") or payload.get("anchor_text") or payload.get("insert_after_text") or "").strip()
        if not anchor or len(anchor) > 260:
            continue
        # The anchor must be a unique exact substring of one visible text block.
        target_index = -1
        target_text = ""
        for index, candidate in enumerate(stream):
            if _scene_block_type(candidate) not in {"text", "markdown", "message", "message_text"}:
                continue
            candidate_text = _scene_text(candidate)
            if candidate_text and candidate_text.count(anchor) == 1:
                target_index, target_text = index, candidate_text
                break
        if target_index < 0:
            continue
        end = target_text.find(anchor) + len(anchor)
        left_text = target_text[:end].rstrip()
        right_text = target_text[end:].lstrip()
        target = stream[target_index]
        base_id = str(target.get("block_id") or target.get("id") or f"text_anchor_{target_index + 1}")
        left = dict(target)
        _set_scene_text_aliases(left, left_text)
        insert_items: List[Dict[str, Any]] = [left, visual]
        if right_text:
            # The following provider-authored text is the continuation after this
            # renderer; it serves as the explanation and should not receive an
            # automatically generated paraphrase in between.
            visual["_anchor_has_continuation"] = True
            right = dict(target)
            candidate_id = f"{base_id}_continuation_{_scene_hash({'anchor': anchor, 'text': right_text})[:8]}"
            while candidate_id in used_ids:
                candidate_id += "_2"
            used_ids.add(candidate_id)
            right["block_id"] = candidate_id
            right.pop("id", None)
            _set_scene_text_aliases(right, right_text)
            insert_items.append(right)
        # Remove the visual at its previous location, then replace the located text.
        visual_index = next((i for i, candidate in enumerate(stream) if candidate is visual), -1)
        if visual_index >= 0:
            stream.pop(visual_index)
        if visual_index < target_index:
            target_index -= 1
        stream[target_index:target_index + 1] = insert_items
        changed = True

    if changed:
        # `final_output=true` is already defined by the provider contract as the
        # terminal item. Keep it terminal after moving anchored renderers in-stream.
        stream = [item for item in stream if not bool(item.get("final_output"))] + [
            item for item in stream if bool(item.get("final_output"))
        ]
        for item in stream:
            item["_anchor_order_override"] = True
    return stream, changed


def _canonical_scene_blocks(scene: MachineScene) -> List[Dict[str, Any]]:
    """Produce one ordered, identity-bound render stream for the scene."""
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

    # Executor carries the canonical answer in render_blocks, while MachineScene
    # intentionally has no dedicated `answer` field. Read the scene envelope first,
    # then recover the longest visible text block if the envelope is textless. Without
    # this step, render extraction ran on an empty string and silently left all
    # explanatory output trapped in the one provider text block.
    answer = _scene_text(scene)
    if not answer:
        metadata = scene.metadata if isinstance(scene.metadata, dict) else {}
        answer = _scene_text(metadata)
    if not answer:
        text_candidates: List[str] = []
        for candidate_block in blocks:
            if not isinstance(candidate_block, dict):
                continue
            if _scene_block_type(candidate_block) not in {"text", "markdown", "message", "message_text"}:
                continue
            candidate_text = _scene_text(candidate_block)
            if candidate_text:
                text_candidates.append(candidate_text)
        if text_candidates:
            answer = max(text_candidates, key=len)
    active_task = scene.active_task if isinstance(scene.active_task, dict) else {}
    metadata_for_request = scene.metadata if isinstance(scene.metadata, dict) else {}
    interpretation_for_request = metadata_for_request.get("interpretation") if isinstance(metadata_for_request.get("interpretation"), dict) else {}
    interpretation_input = interpretation_for_request.get("input") if isinstance(interpretation_for_request.get("input"), dict) else {}
    request_structure = interpretation_for_request.get("request_structure") if isinstance(interpretation_for_request.get("request_structure"), dict) else {}
    dialogue_structure = interpretation_for_request.get("dialogue") if isinstance(interpretation_for_request.get("dialogue"), dict) else {}
    new_dialogue = dialogue_structure.get("new_dialogue") if isinstance(dialogue_structure.get("new_dialogue"), dict) else {}
    current_request = str(
        interpretation_input.get("original_request")
        or interpretation_input.get("normalized_request")
        or request_structure.get("user_goal")
        or request_structure.get("new_dialogue_request")
        or new_dialogue.get("request")
        or ""
    ).strip()
    blocks = prepare_render_blocks_for_room_dispatch(
        blocks,
        answer,
        active_task.get("requested_outputs"),
        graph_policy=active_task.get("graph_policy"),
        current_request=current_request,
    )
    visible_types = {str(item.get("type") or "").lower() for item in blocks if isinstance(item, dict)}
    requested_outputs = _render_requested_outputs(active_task.get("requested_outputs"))
    suppress_unrequested_table = "graph" in requested_outputs and "table" not in requested_outputs and any(
        isinstance(item, dict)
        and _scene_block_type(item) == "graph"
        and _has_render_payload("graph", _payload_for_render_block(item, "graph"), item)
        for item in blocks
    )
    source_answer = answer
    answer = _strip_rendered_segments(
        answer, visible_types, blocks,
        suppress_unrequested_table=suppress_unrequested_table,
    )

    # Critical integrity step: the old code cleaned the local `answer` string,
    # but left the original full answer inside the existing MessageTextBlock.
    # RenderMessage consumes render_blocks, so the table/code/URL stayed in the
    # text block and then appeared again in its dedicated renderer. Write the
    # cleaned narrative back into the visible text block(s), updating every text
    # alias together so a legacy `text`/`markdown` field cannot reintroduce it.
    text_keys = ("content", "text", "markdown", "display_text")
    for block in blocks:
        if not isinstance(block, dict) or _scene_block_type(block) not in {"text", "markdown", "message", "message_text"}:
            continue
        block_source_text = _scene_text(block)
        if not block_source_text:
            continue
        if block_source_text.strip() == source_answer.strip():
            cleaned_text = answer
        else:
            # A shorter text section may contain a renderable fragment too. Clean
            # only exact structures which have a corresponding concrete renderer.
            cleaned_text = _strip_rendered_segments(block_source_text, visible_types, blocks, suppress_unrequested_table=suppress_unrequested_table)
        present_text_keys = [key for key in text_keys if isinstance(block.get(key), str)]
        for key in (present_text_keys or ["content"]):
            block[key] = cleaned_text
        # `prepare_render_blocks_for_room_dispatch()` also hydrates text into the
        # block's payload. Keep that canonical payload synchronized with the
        # visible fields; otherwise a viewer reading payload.content could still
        # receive the old Markdown table/code/URLs after the top-level text was
        # cleaned.
        payload = block.get("payload")
        if isinstance(payload, dict):
            payload_text_keys = [key for key in text_keys if isinstance(payload.get(key), str)]
            for key in payload_text_keys:
                payload[key] = cleaned_text

    # Honor renderer placement anchors emitted by the provider. This happens only
    # after invalid render shells are filtered and the cleaned text is synchronized,
    # so a missing renderer cannot cause its explanatory sentence to disappear.
    blocks, anchor_order_override = _interleave_scene_blocks_by_anchor(blocks)

    # Empty text shells must not mount in Web. The structured renderer remains;
    # useful prose is preserved in `answer` and restored below when necessary.
    blocks = [
        block for block in blocks
        if isinstance(block, dict)
        and (
            _scene_block_type(block) not in {"text", "markdown", "message", "message_text"}
            or bool(_scene_text(block))
        )
    ]
    metadata_for_language = scene.metadata if isinstance(scene.metadata, dict) else {}
    interpretation_for_language = metadata_for_language.get("interpretation") if isinstance(metadata_for_language.get("interpretation"), dict) else {}
    language_hint = (
        interpretation_for_language.get("display_language")
        or interpretation_for_language.get("language")
        or metadata_for_language.get("display_language")
        or ""
    )
    if answer and not any(_scene_block_type(b) in {"text", "markdown", "formula"} and _scene_text(b) for b in blocks if isinstance(b, dict)):
        blocks.insert(0, {
            "type": "text",
            "artifact_type": "text",
            "renderer": "MessageTextBlock",
            "viewer": "MessageTextBlock",
            "content": answer,
            "text": answer,
        })

    # Run after the canonical-answer fallback so an explanation block cannot be
    # mistaken for the primary user-facing answer when the source list had no text.
    blocks = _ensure_premium_render_explanations(blocks, source_answer or answer, language_hint)

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
        block["sequence_index"] = index if anchor_order_override or block.pop("_anchor_order_override", False) else order_pos.get(block_id, index)
        block.pop("_anchor_order_override", None)
        block["scene_contract"] = True
        block.pop("_anchor_has_continuation", None)
        block.pop("_anchor_order_override", None)
        block["signal_version"] = UNIFIED_RENDER_SIGNAL_VERSION
        block_payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
        if block_type in {"formula", "graph", "table", "diagram", "image", "gallery", "code", "link", "file", "audio", "video"} and not _scene_payload_has_content(block_type, block_payload, block):
            continue
        related = [str(x).strip() for x in _scene_list(block.get("related_block_ids")) if str(x).strip()]
        block["related_block_ids"] = list(dict.fromkeys(related))
        signature = _scene_hash({
            "type": block_type,
            "renderer": renderer,
            "content": _scene_text(block),
            "payload": block.get("payload", {}),
            # Two renderers can legitimately need the same wording while still
            # requiring separate visible explanations. Include this relation in
            # the signature only for explanation blocks, preserving normal dedupe.
            "explanation_for_block_id": str(block.get("explanation_for_block_id") or ""),
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
    """Create the single Web signal for the authenticated dialogue scene."""
    return {
        "signal_type": CANONICAL_SCENE_SIGNAL_TYPE,
        "signal_version": UNIFIED_RENDER_SIGNAL_VERSION,
        "scene_version": contract.scene_version,
        "scene_id": contract.scene_id,
        "turn_id": contract.turn_id,
        "flow_id": contract.flow_id,
        "topic_group": contract.topic_group,
        "continuation": contract.continuation,
        "single_response": True,
        "single_signal": True,
        "answer_render_policy": ANSWER_RENDER_POLICY,
        "answer": str(contract.metadata.get("answer") or ""),
        "identity": {
            "user_id": contract.user_id,
            "conversation_id": contract.conversation_id,
            "dialogue_sequence_id": contract.dialogue_sequence_id,
            "sequence_turn_index": int(contract.sequence_turn_index or 0),
        },
        "authenticated_scope": deepcopy(contract.authenticated_scope),
        "dialogue_state": deepcopy(contract.dialogue_state),
        "dialogue_development": deepcopy(contract.dialogue_development),
        "result_event": deepcopy(contract.result_event),
        "open_loops": deepcopy(contract.open_loops),
        "pending_obligations": deepcopy(contract.pending_obligations),
        "active_task": deepcopy(contract.active_task),
        "order": list(contract.order),
        "relations": deepcopy(contract.relations),
        "blocks": deepcopy(contract.render_blocks),
        "render_blocks": deepcopy(contract.render_blocks),
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
    identity_scope = dict(metadata.get("identity_scope") or metadata.get("authenticated_scope") or {})
    fiber_identity = getattr(getattr(response, "fiber", None), "identity", None)
    scene.user_id = str(identity_scope.get("user_id") or getattr(response, "user_id", "") or getattr(fiber_identity, "user_id", "") or "")
    scene.conversation_id = str(identity_scope.get("conversation_id") or getattr(response, "conversation_id", "") or metadata.get("conversation_id") or "")
    scene.dialogue_sequence_id = str(metadata.get("dialogue_sequence_id") or "")
    try:
        scene.sequence_turn_index = int(metadata.get("sequence_turn_index") or 0)
    except (TypeError, ValueError):
        scene.sequence_turn_index = 0
    scene.active_task = deepcopy(metadata.get("active_task") or metadata.get("interactive_task_state") or source_scene.get("active_task") or {}) if isinstance(metadata.get("active_task") or metadata.get("interactive_task_state") or source_scene.get("active_task") or {}, dict) else {}
    scene.dialogue_state = deepcopy(metadata.get("dialogue_state") or metadata.get("processor_interpretation") or {})
    scene.dialogue_development = deepcopy(
        metadata.get("dialogue_development")
        or scene.dialogue_state.get("dialogue_development")
        or {}
    ) if isinstance(metadata.get("dialogue_development") or scene.dialogue_state.get("dialogue_development") or {}, dict) else {}
    scene.result_event = deepcopy(metadata.get("result_event") or scene.dialogue_development.get("latest_result_event") or {}) if isinstance(metadata.get("result_event") or scene.dialogue_development.get("latest_result_event") or {}, dict) else {}
    scene.open_loops = deepcopy(metadata.get("open_loops") or scene.dialogue_development.get("open_loops") or []) if isinstance(metadata.get("open_loops") or scene.dialogue_development.get("open_loops") or [], list) else []
    scene.pending_obligations = deepcopy(metadata.get("pending_obligations") or scene.dialogue_development.get("pending_obligations") or []) if isinstance(metadata.get("pending_obligations") or scene.dialogue_development.get("pending_obligations") or [], list) else []
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
        "user_id": scene.user_id,
        "conversation_id": scene.conversation_id,
        "dialogue_sequence_id": scene.dialogue_sequence_id,
        "sequence_turn_index": scene.sequence_turn_index,
        "active_task": deepcopy(scene.active_task),
        "dialogue_state": deepcopy(scene.dialogue_state),
        "dialogue_development": deepcopy(scene.dialogue_development),
        "result_event": deepcopy(scene.result_event),
        "open_loops": deepcopy(scene.open_loops),
        "pending_obligations": deepcopy(scene.pending_obligations),
        "identity_scope": {"user_id": scene.user_id, "conversation_id": scene.conversation_id, "dialogue_sequence_id": scene.dialogue_sequence_id},
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
    contract.user_id = str(scene.user_id or scene.metadata.get("user_id") or "")
    contract.conversation_id = str(scene.conversation_id or scene.metadata.get("conversation_id") or "")
    contract.dialogue_sequence_id = str(scene.dialogue_sequence_id or scene.metadata.get("dialogue_sequence_id") or "")
    contract.sequence_turn_index = int(scene.sequence_turn_index or scene.metadata.get("sequence_turn_index") or 0)
    contract.active_task = deepcopy(scene.active_task or scene.metadata.get("active_task") or {})
    contract.dialogue_state = deepcopy(scene.dialogue_state or scene.metadata.get("dialogue_state") or {})
    contract.dialogue_development = deepcopy(scene.dialogue_development or scene.metadata.get("dialogue_development") or {})
    contract.result_event = deepcopy(scene.result_event or scene.metadata.get("result_event") or {})
    contract.open_loops = deepcopy(scene.open_loops or scene.metadata.get("open_loops") or [])
    contract.pending_obligations = deepcopy(scene.pending_obligations or scene.metadata.get("pending_obligations") or [])
    contract.authenticated_scope = {
        "user_id": contract.user_id,
        "conversation_id": contract.conversation_id,
        "dialogue_sequence_id": contract.dialogue_sequence_id,
    }
    contract.active_scene = scene.active_scene
    contract.scene_blueprint = deepcopy(scene.scene_blueprint or {})

    canonical_blocks = _canonical_scene_blocks(scene)
    for block in canonical_blocks:
        if isinstance(block, dict):
            block["user_id"] = contract.user_id
            block["conversation_id"] = contract.conversation_id
            block["dialogue_sequence_id"] = contract.dialogue_sequence_id
            block["sequence_turn_index"] = contract.sequence_turn_index
            block["scene_id"] = contract.scene_id
            block["turn_id"] = contract.turn_id
            block["flow_id"] = contract.flow_id
            route_meta = (scene.metadata or {}).get("route") if isinstance((scene.metadata or {}).get("route"), dict) else {}
            selected_rooms = route_meta.get("selected_rooms") or (scene.metadata or {}).get("selected_rooms") or []
            registration = get_web_renderer_registration(str(block.get("type") or block.get("artifact_type") or "text"))
            source_room = str(block.get("source_room") or block.get("room_source") or "")
            payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
            identity_signal = {
                "signal_type": CANONICAL_SCENE_SIGNAL_TYPE,
                "signal_version": UNIFIED_RENDER_SIGNAL_VERSION,
                "signal_channel": "canonical_web_render_signal_v2",
                "web_registry_version": WEB_RENDERER_REGISTRY_VERSION,
                "representation": str(block.get("type") or block.get("artifact_type") or "text"),
                "type": str(block.get("type") or block.get("artifact_type") or "text"),
                "renderer": str(block.get("renderer") or registration.get("renderer") or "MessageTextBlock"),
                "viewer": str(block.get("viewer") or registration.get("viewer") or "MessageTextBlock"),
                "payload_contract_keys": list(registration.get("payload_keys") or []),
                "payload_present": _scene_payload_has_content(str(block.get("type") or "text"), payload, block),
                "content_present": bool(_scene_text(block)),
                "source_room": source_room,
                "room_id": source_room,
                "selected_room_ids": [str(item.get("room") or item.get("room_id") or "") for item in selected_rooms if isinstance(item, dict) and str(item.get("room") or item.get("room_id") or "")],
                "selected_room_registry_keys": [str(item.get("registry_key") or "") for item in selected_rooms if isinstance(item, dict) and str(item.get("registry_key") or "")],
                "payload_ref": "payload",
                "identity": {"user_id": contract.user_id, "conversation_id": contract.conversation_id, "dialogue_sequence_id": contract.dialogue_sequence_id, "turn_id": contract.turn_id, "flow_id": contract.flow_id, "scene_id": contract.scene_id, "interpretation_id": str((scene.metadata or {}).get("identity", {}).get("interpretation_id") or "")},
                "user_id": contract.user_id,
                "conversation_id": contract.conversation_id,
                "dialogue_sequence_id": contract.dialogue_sequence_id,
                "dialog_id": contract.dialogue_sequence_id,
                "message_id": contract.turn_id,
                "turn_id": contract.turn_id,
                "flow_id": contract.flow_id,
                "scene_id": contract.scene_id,
                "interpretation_id": str((scene.metadata or {}).get("identity", {}).get("interpretation_id") or ""),
            }
            existing_render_signal = block.get("render_signal") if isinstance(block.get("render_signal"), dict) else {}
            existing_render_signal = {**existing_render_signal, **identity_signal, "payload": payload}
            block["render_signal"] = existing_render_signal
            existing_signal = block.get("signal") if isinstance(block.get("signal"), dict) else {}
            block["signal"] = {**existing_signal, **identity_signal}
            block["payload_contract_keys"] = list(registration.get("payload_keys") or [])
            block["source_room"] = source_room
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
        "user_id": contract.user_id,
        "conversation_id": contract.conversation_id,
        "dialogue_sequence_id": contract.dialogue_sequence_id,
        "sequence_turn_index": contract.sequence_turn_index,
        "active_task": deepcopy(contract.active_task),
        "dialogue_state": deepcopy(contract.dialogue_state),
        "dialogue_development": deepcopy(contract.dialogue_development),
        "result_event": deepcopy(contract.result_event),
        "open_loops": deepcopy(contract.open_loops),
        "pending_obligations": deepcopy(contract.pending_obligations),
        "authenticated_scope": deepcopy(contract.authenticated_scope),
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
    # Presentation metadata is kept inside the existing SceneContract.
    presentation = {
        "version": "scene_presentation_v1",
        "engine": "McDowell",
        "math_engine": "KaTeX",
        "single_response": True,
        "single_signal": True,
        "layout": {
            "mode": "flow",
            "container": "adaptive_full_width",
            "frames": False,
            "cards": False,
        },
        "scene_id": scene.scene_id,
        "turn_id": scene.turn_id,
        "flow_id": scene.flow_id,
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
        "dialogue_development": deepcopy(contract.dialogue_development),
        "result_event": deepcopy(contract.result_event),
        "open_loops": deepcopy(contract.open_loops),
        "pending_obligations": deepcopy(contract.pending_obligations),
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
