# =====================================================
# APRIL C_DIAGRAM_ROOM — CANONICAL VISUAL STRUCTURE ENGINE
# =====================================================
"""
Role:
    Preserve structured diagrams/schematics/geometric drawings as one
    scene artifact.

The room never reconstructs a diagram from natural-language keywords.
Processor supplies nodes, edges, geometry, SVG, states, and semantics.
"""

from __future__ import annotations

from copy import deepcopy
import html
import uuid
from typing import Any, Dict, List, Optional

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact


ROOM_ID = "C_DIAGRAM_ROOM"
ARTIFACT_TYPE = "diagram"


def _obj(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        return list(value.values())
    return []


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _identity(task: Dict[str, Any]) -> Dict[str, Any]:
    scene = _obj(task.get("scene"))

    scene_id = _text(task.get("scene_id") or scene.get("scene_id"))
    turn_id = _text(task.get("turn_id") or scene.get("turn_id"))
    flow_id = _text(task.get("flow_id") or scene.get("flow_id"))
    topic_group = _text(task.get("topic_group") or scene.get("topic_group"))
    block_id = _text(task.get("block_id") or scene.get("block_id"))
    render_id = _text(task.get("render_id") or scene.get("render_id"))

    generated = False
    if not scene_id:
        scene_id = f"scene_{uuid.uuid4().hex[:12]}"
        generated = True
    if not turn_id:
        turn_id = f"turn_{uuid.uuid4().hex[:12]}"
        generated = True
    if not block_id:
        block_id = f"diagram_{uuid.uuid4().hex[:12]}"
        generated = True
    if not render_id:
        render_id = f"{block_id}:render"

    return {
        "scene_id": scene_id,
        "turn_id": turn_id,
        "flow_id": flow_id,
        "topic_group": topic_group,
        "continuation": bool(task.get("continuation", scene.get("continuation", False))),
        "block_id": block_id,
        "render_id": render_id,
        "identity_generated_locally": generated,
    }


def _extract_payload(task: Dict[str, Any]) -> Dict[str, Any]:
    for candidate in (
        task.get("payload"),
        task.get("diagram_payload"),
        task.get("diagram"),
        _obj(task.get("semantic")).get("diagram_payload"),
        _obj(task.get("semantic")).get("diagram"),
    ):
        if isinstance(candidate, dict) and candidate:
            return deepcopy(candidate)

    payload: Dict[str, Any] = {}
    keys = (
        "title", "description", "diagram_type", "representation", "format",
        "nodes", "components", "edges", "connections", "relations",
        "layout", "orientation", "views", "geometry", "dimensions",
        "annotations", "legend", "constraints", "cross_connections",
        "operation", "safety", "switch_states", "states", "notes",
        "caption", "metadata", "ascii", "ascii_preview", "svg", "svg_payload",
        "elements", "vertices", "points", "segments", "labels",
        "coordinate_system", "construction",
    )
    for key in keys:
        if key in task:
            payload[key] = deepcopy(task[key])
    return payload


def _normalize_nodes(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_nodes = _list(payload.get("nodes") or payload.get("components") or payload.get("vertices"))
    nodes: List[Dict[str, Any]] = []

    for index, raw in enumerate(raw_nodes):
        if isinstance(raw, dict):
            node = deepcopy(raw)
        else:
            node = {"label": _text(raw)}

        node_id = _text(
            node.get("id")
            or node.get("node_id")
            or node.get("component_id")
            or node.get("key")
        ) or f"node_{index + 1}"

        label = _text(
            node.get("label")
            or node.get("name")
            or node.get("title")
            or node_id
        )

        node["id"] = node_id
        node["label"] = label
        if not node.get("kind"):
            node["kind"] = _text(node.get("symbol") or node.get("type"), "node")
        nodes.append(node)

    return nodes


def _normalize_edges(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_edges = (
        _list(payload.get("edges"))
        + _list(payload.get("connections"))
        + _list(payload.get("relations"))
        + _list(payload.get("segments"))
    )

    edges: List[Dict[str, Any]] = []
    seen = set()

    for raw in raw_edges:
        if isinstance(raw, (list, tuple)) and len(raw) >= 2:
            raw = {"from": raw[0], "to": raw[1]}
        if not isinstance(raw, dict):
            continue

        source = _text(raw.get("from") or raw.get("source") or raw.get("start"))
        target = _text(raw.get("to") or raw.get("target") or raw.get("end"))
        if not source or not target:
            continue

        edge = deepcopy(raw)
        edge["from"] = source
        edge["to"] = target

        key = (
            source,
            target,
            _text(edge.get("label")),
            repr(edge.get("wire")),
            repr(edge.get("waypoints")),
        )
        if key in seen:
            continue
        seen.add(key)
        edges.append(edge)

    return edges


def _select_renderer(payload: Dict[str, Any]) -> str:
    explicit = _text(
        payload.get("renderer")
        or _obj(payload.get("presentation")).get("renderer")
    ).strip()

    # Structured schematics (nodes/edges) need a renderer that can actually
    # display vector geometry. GalleryBlock is an image/gallery viewer and was
    # producing an empty white card for these payloads.
    if _text(payload.get("svg") or payload.get("svg_payload")):
        return "SvgBlock"

    nodes = _list(payload.get("nodes") or payload.get("components") or payload.get("vertices"))
    edges = _list(
        payload.get("edges")
        or payload.get("connections")
        or payload.get("relations")
        or payload.get("segments")
    )
    if nodes or edges:
        if explicit in {"ArithmeticDiagram", "arithmeticdiagram", "SvgBlock", "svgblock"}:
            return "SvgBlock" if explicit.lower() == "svgblock" else "ArithmeticDiagram"
        return "SvgBlock"

    if explicit:
        return explicit

    return "GalleryBlock"


def _build_schematic_svg(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    *,
    width: int = 1400,
    height: int = 520,
) -> str:
    """Build a crisp deterministic schematic from already-supplied structure.

    This does not infer components from natural language. It only lays out the
    normalized nodes/edges already supplied by the Processor so the Web
    renderer receives an actual SVG instead of a GalleryBlock with structural
    JSON that it cannot draw.
    """
    if not nodes:
        return ""

    width = max(720, int(width))
    height = max(360, int(height))
    margin_x = 70
    center_y = height // 2
    node_w = 210
    node_h = 92
    usable = max(200, width - 2 * margin_x)
    gap = max(48, int((usable - node_w * len(nodes)) / max(1, len(nodes) - 1)))

    positions: Dict[str, tuple[int, int]] = {}
    for index, node in enumerate(nodes):
        node_id = _text(node.get("id")) or f"node_{index + 1}"
        x = margin_x + index * (node_w + gap)
        y = center_y - node_h // 2
        positions[node_id] = (x, y)

    # Prefer any explicit normalized positions when supplied.
    for node in nodes:
        node_id = _text(node.get("id"))
        pos = node.get("position")
        if isinstance(pos, dict):
            try:
                x = int(float(pos.get("x")))
                y = int(float(pos.get("y")))
                positions[node_id] = (
                    max(20, min(width - node_w - 20, x)),
                    max(20, min(height - node_h - 20, y)),
                )
            except (TypeError, ValueError):
                pass

    esc = html.escape

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="April schematic">',
        "<defs>",
        '<marker id="april-arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="8" markerHeight="8" orient="auto-start-reverse">',
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#334155"/>',
        "</marker>",
        "</defs>",
        '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff" rx="18"/>',
    ]

    # Edges first so node cards remain visually dominant.
    for edge in edges:
        source = _text(edge.get("from") or edge.get("source") or edge.get("start"))
        target = _text(edge.get("to") or edge.get("target") or edge.get("end"))
        if source not in positions or target not in positions:
            continue
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        sx = x1 + node_w
        sy = y1 + node_h // 2
        tx = x2
        ty = y2 + node_h // 2
        mid_x = (sx + tx) // 2
        path = f"M {sx} {sy} C {mid_x} {sy}, {mid_x} {ty}, {tx} {ty}"
        parts.append(
            f'<path d="{path}" fill="none" stroke="#334155" stroke-width="5" '
            f'stroke-linecap="round" marker-end="url(#april-arrow)"/>'
        )
        label = _text(edge.get("label"))
        if label:
            parts.append(
                f'<text x="{mid_x}" y="{min(sy, ty) - 14}" text-anchor="middle" '
                f'font-family="Inter,Arial,sans-serif" font-size="20" fill="#334155">'
                f'{esc(label)}</text>'
            )

    for index, node in enumerate(nodes):
        node_id = _text(node.get("id")) or f"node_{index + 1}"
        label = _text(node.get("label") or node.get("name") or node_id)
        kind = _text(node.get("kind") or node.get("type") or "node").lower()
        x, y = positions[node_id]

        if "positive" in kind or label.startswith("+"):
            fill = "#ECFDF5"
            stroke = "#047857"
        elif "negative" in kind or "−" in label or "-" == label.strip():
            fill = "#FEF2F2"
            stroke = "#B91C1C"
        elif "fuse" in kind or "предохран" in label.lower():
            fill = "#FFF7ED"
            stroke = "#C2410C"
        elif "switch" in kind or "выключ" in label.lower():
            fill = "#EFF6FF"
            stroke = "#1D4ED8"
        elif "lamp" in kind or "лампоч" in label.lower():
            fill = "#FFFBEB"
            stroke = "#A16207"
        else:
            fill = "#F8FAFC"
            stroke = "#475569"

        parts.append(
            f'<rect x="{x}" y="{y}" width="{node_w}" height="{node_h}" rx="18" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="4"/>'
        )
        parts.append(
            f'<circle cx="{x + 26}" cy="{y + 30}" r="9" fill="{stroke}"/>'
        )
        # Compactly wrap labels at a conservative character width.
        words = label.split()
        lines = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) > 22 and current:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        lines = lines[:3] or [node_id]

        base_y = y + 42 - max(0, len(lines) - 1) * 10
        for line_index, line in enumerate(lines):
            parts.append(
                f'<text x="{x + node_w / 2 + 10}" y="{base_y + line_index * 28}" '
                f'text-anchor="middle" font-family="Inter,Arial,sans-serif" '
                f'font-size="24" font-weight="600" fill="#0f172a">{esc(line)}</text>'
            )

    parts.append("</svg>")
    return "".join(parts)


def _canonical_payload(task: Dict[str, Any]) -> Dict[str, Any]:
    source = _extract_payload(task)
    identity = _identity(task)

    nodes = _normalize_nodes(source)
    edges = _normalize_edges(source)

    svg = source.get("svg")
    svg_payload = source.get("svg_payload")

    # Turn the already-supplied graph structure into a real SVG transport
    # artifact. This is a presentation normalization step, not semantic routing.
    generated_svg = ""
    if not svg and not svg_payload and (nodes or edges):
        generated_svg = _build_schematic_svg(nodes, edges)

    if generated_svg:
        source["svg"] = generated_svg
        svg = generated_svg

    renderer = _select_renderer(source)

    diagram_type = _text(
        source.get("diagram_type")
        or source.get("representation")
        or source.get("format"),
        "structured_diagram",
    ).lower()

    representation = _text(
        source.get("representation"),
        "schematic" if (nodes or edges) else "technical_drawing"
    )

    # A diagram is render-ready only when the Processor supplied real visual
    # structure: SVG, nodes/edges, geometry, or drawing elements.
    render_ready = bool(
        svg
        or svg_payload
        or nodes
        or edges
        or source.get("geometry")
        or source.get("elements")
        or source.get("vertices")
        or source.get("points")
    )

    if not render_ready:
        raise ValueError(
            "C_DIAGRAM_ROOM requires structured diagram data; "
            "it will not invent missing components."
        )

    payload = deepcopy(source)
    payload.update({
        "scene_type": "diagram",
        "artifact_type": "diagram",
        "diagram_type": diagram_type,
        "representation": representation,
        "nodes": nodes,
        "components": deepcopy(nodes),
        "edges": edges,
        "connections": deepcopy(edges),
        "renderer": renderer,
        "render_ready": True,
        "scene": {
            **identity,
            "node_type": "diagram",
            "renderer": renderer,
            "role": _text(task.get("role"), "visual_structure"),
        },
        "render_identity": identity,
        "presentation": {
            "renderer": renderer,
            "engine": "April Diagram Engine",
            "route": "canonical",
            "single_scene": True,
            "adaptive_width": True,
            "preserve_structure": True,
            "payload_unchanged": True,
            "no_text_keyword_inference": True,
        },
        "requirements": {
            "preserve_nodes": True,
            "preserve_edges": True,
            "preserve_geometry": True,
            "preserve_svg": bool(svg or svg_payload),
            "generated_svg_from_supplied_structure": bool(generated_svg),
            "no_generated_missing_components": True,
            "no_parallel_route": True,
        },
        "metadata": {
            **_obj(source.get("metadata")),
            "room": ROOM_ID,
            "scene_id": identity["scene_id"],
            "turn_id": identity["turn_id"],
        },
    })

    if svg is not None:
        payload["svg"] = svg
    if svg_payload is not None:
        payload["svg_payload"] = deepcopy(svg_payload)

    return payload


class DiagramRoom(Room):
    name = "diagram"
    room_type = "diagram_renderer"
    artifact_type = ARTIFACT_TYPE
    artifact_version = "5.0"
    web_space_ready = True
    renderer_safe = True
    continuity_safe = True
    orchestration_safe = True

    def can_handle(self, text: Any, context: Any) -> bool:
        return self.evaluate(text, context) > 0.0

    def evaluate(self, text: Any, context: Any) -> float:
        ctx = context if isinstance(context, dict) else {}
        semantic = _obj(ctx.get("semantic"))
        blueprint = _obj(ctx.get("scene_blueprint"))

        representations = (
            _list(semantic.get("renderers"))
            + _list(semantic.get("representations"))
            + _list(blueprint.get("renderers"))
            + _list(blueprint.get("representations"))
        )
        normalized = {str(v).strip().lower() for v in representations}

        if any(value in normalized for value in {
            "diagram", "diagrambloсk".replace("с", "c"),
            "schematic", "svgblock", "galleryblock",
        }):
            return 1.0
        if ctx.get("trajectory") == "diagram":
            return 0.5

        payload = (
            ctx.get("diagram_payload")
            or semantic.get("diagram_payload")
        )
        if isinstance(payload, dict) and payload:
            return 1.0
        return 0.0

    def build_work_order(self, context: Optional[Dict[str, Any]] = None):
        ctx = dict(context or {})
        return {
            "scene_id": ctx.get("scene_id"),
            "turn_id": ctx.get("turn_id"),
            "flow_id": ctx.get("flow_id"),
            "topic_group": ctx.get("topic_group"),
            "continuation": ctx.get("continuation", False),
            "block_id": ctx.get("block_id"),
            "render_id": ctx.get("render_id"),
            "role": ctx.get("role"),
            "semantic": deepcopy(_obj(ctx.get("semantic"))),
            "scene_blueprint": deepcopy(_obj(ctx.get("scene_blueprint"))),
            "payload": deepcopy(ctx.get("diagram_payload") or ctx.get("payload") or {}),
        }

    def process(self, task: Dict[str, Any]):
        payload = _canonical_payload(dict(task or {}))
        identity = payload["scene"]

        artifact = create_artifact(
            artifact_type=ARTIFACT_TYPE,
            room_source=ROOM_ID,
            data={
                "title": payload.get("title") or "Diagram",
                "description": payload.get("description") or "",
                "payload": payload,
                "renderer": payload["renderer"],
                "viewer": payload["renderer"],
                "scene_id": identity["scene_id"],
                "turn_id": identity["turn_id"],
                "flow_id": identity["flow_id"],
                "topic_group": identity["topic_group"],
                "continuation": identity["continuation"],
                "block_id": identity["block_id"],
                "render_id": identity["render_id"],
                "scene_contributions": [{
                    "scene_id": identity["scene_id"],
                    "block_id": identity["block_id"],
                    "type": ARTIFACT_TYPE,
                    "renderer": payload["renderer"],
                }],
                "presentation": payload["presentation"],
            },
        )
        artifact.quality.validation_passed = True
        artifact.quality.quality_score = 1.0
        artifact.quality.confidence_score = 1.0
        artifact.quality.completeness_score = 1.0
        return artifact

    def execute(self, machine_request: Any):
        if isinstance(machine_request, dict):
            return self.process(machine_request)
        return None

    async def handle(self, user_id, text, context, run):
        # No natural-language reconstruction. Structured visual data must come
        # from the Processor in `context`.
        ctx = context if isinstance(context, dict) else {}
        task = self.build_work_order(ctx)
        return self.process(task)


ROOM = DiagramRoom()
