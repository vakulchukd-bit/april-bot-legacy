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
        "coordinate_system", "construction", "ascii", "ascii_preview",
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

    # Plain ASCII schematics are still canonical diagrams. The Web renderer
    # displays them directly from the artifact payload; do not downgrade them
    # to GalleryBlock, which has no textual schematic renderer.
    if _text(payload.get("ascii") or payload.get("ascii_preview")):
        return "DiagramRenderer"

    if explicit:
        return explicit

    return "DiagramRenderer"


def _build_schematic_svg(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    *,
    width: int = 1400,
    height: int = 560,
    title: str = "Схема подключения",
    linked_formula: str = "",
) -> str:
    """Render supplied schematic data as a clean technical SVG.

    The room only visualizes normalized nodes/edges. Component symbols are
    selected from explicit node metadata; values/ratings/terminal names are
    shown only when supplied upstream. No missing electrical parameter is
    fabricated here.
    """
    if not nodes:
        return ""

    width = max(900, int(width))
    height = max(460, int(height))
    margin_x = 70
    title_y = 38
    node_w = 210
    node_h = 168
    canvas_y = 150
    usable = max(300, width - 2 * margin_x)
    gap = max(55, int((usable - node_w * len(nodes)) / max(1, len(nodes) - 1)))

    positions: Dict[str, tuple[int, int]] = {}
    for index, node in enumerate(nodes):
        node_id = _text(node.get("id")) or f"node_{index + 1}"
        x = margin_x + index * (node_w + gap)
        y = canvas_y
        positions[node_id] = (x, y)

    for node in nodes:
        node_id = _text(node.get("id"))
        pos = node.get("position")
        if isinstance(pos, dict):
            try:
                px = float(pos.get("x"))
                py = float(pos.get("y"))
                if 0.0 <= px <= 1.0 and 0.0 <= py <= 1.0:
                    positions[node_id] = (
                        int(40 + px * max(100, width - node_w - 80)),
                        int(canvas_y + py * max(40, height - canvas_y - node_h - 70)),
                    )
                else:
                    positions[node_id] = (
                        max(30, min(width - node_w - 30, int(px))),
                        max(canvas_y, min(height - node_h - 60, int(py))),
                    )
            except (TypeError, ValueError):
                pass

    esc = html.escape

    def node_kind(node: Dict[str, Any]) -> str:
        raw = " ".join(
            _text(node.get(key))
            for key in ("symbol", "kind", "type", "label", "name")
        ).lower()
        if any(x in raw for x in ("power_supply", "source", "блок питания", "источник", "battery", "батар")):
            return "power"
        if any(x in raw for x in ("fuse", "предохран")):
            return "fuse"
        if any(x in raw for x in ("switch", "выключател", "переключател", "dpdt")):
            return "switch"
        if any(x in raw for x in ("lamp", "ламп", "гирлянд", "light")):
            return "lamp"
        if any(x in raw for x in ("motor", "двигател")):
            return "motor"
        if any(x in raw for x in ("resistor", "резист")):
            return "resistor"
        if any(x in raw for x in ("controller", "контроллер", "relay", "реле", "contactor", "контактор")):
            return "controller"
        return "generic"

    def text_lines(value: Any, limit: int = 28, max_lines: int = 2) -> List[str]:
        label = _text(value)
        if not label:
            return []
        words = label.split()
        lines: List[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) > limit and current:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines[:max_lines]

    kind_by_id = {
        _text(node.get("id")) or f"node_{index + 1}": node_kind(node)
        for index, node in enumerate(nodes)
    }
    electrical_schematic = any(
        kind in {"power", "fuse", "switch", "lamp", "motor", "resistor", "controller"}
        for kind in kind_by_id.values()
    )

    def endpoint(node_id: str, terminal: str, side: str) -> tuple[float, float]:
        x, y = positions[node_id]
        kind = kind_by_id.get(node_id, "generic")
        cy = y + node_h / 2
        terminal = _text(terminal).lower()

        if kind == "power":
            if terminal in {"minus", "-", "negative"}:
                return (x + node_w / 2, y + node_h + 14)
            return (x + node_w, cy - 20)

        if side == "out":
            return (x + node_w, cy)
        return (x, cy)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title or "Схема")}">',
        "<defs>",
        '<filter id="april-shadow" x="-20%" y="-20%" width="140%" height="140%">'
        '<feDropShadow dx="0" dy="5" stdDeviation="5" flood-opacity="0.12"/>'
        "</filter>",
        '<marker id="april-arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">',
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#334155"/>',
        "</marker>",
        "</defs>",
        '<rect x="0" y="0" width="100%" height="100%" rx="18" fill="#ffffff"/>',
        f'<text x="50%" y="{title_y}" text-anchor="middle" font-family="Inter,Arial,sans-serif" '
        f'font-size="28" font-weight="700" fill="#0f172a">{esc(title or "Схема подключения")}</text>',
    ]

    for edge in edges:
        source = _text(edge.get("from") or edge.get("source") or edge.get("start"))
        target = _text(edge.get("to") or edge.get("target") or edge.get("end"))
        if source not in positions or target not in positions:
            continue

        from_terminal = _text(edge.get("from_terminal") or edge.get("source_terminal"))
        to_terminal = _text(edge.get("to_terminal") or edge.get("target_terminal"))

        sx, sy = endpoint(source, from_terminal, "out")
        tx, ty = endpoint(target, to_terminal, "in")

        # Return conductor to a source minus terminal gets a lower orthogonal
        # route so it does not run through the component cards.
        target_kind = kind_by_id.get(target, "generic")
        target_is_bottom_port = target_kind == "power" and to_terminal.lower() in {"minus", "-", "negative"}

        if target_is_bottom_port:
            route_y = max(y + node_h for _, y in positions.values()) + 48
            path = f"M {sx} {sy} L {sx} {route_y} L {tx} {route_y} L {tx} {ty}"
            label_x = (sx + tx) / 2
            label_y = route_y - 12
        elif abs(ty - sy) < 2:
            path = f"M {sx} {sy} L {tx} {ty}"
            label_x = (sx + tx) / 2
            label_y = sy - 14
        else:
            mid_x = (sx + tx) / 2
            path = f"M {sx} {sy} L {mid_x} {sy} L {mid_x} {ty} L {tx} {ty}"
            label_x = mid_x
            label_y = min(sy, ty) - 14

        marker = "" if electrical_schematic else ' marker-end="url(#april-arrow)"'
        parts.append(
            f'<path d="{path}" fill="none" stroke="#334155" stroke-width="4" '
            f'stroke-linecap="round" stroke-linejoin="round"{marker}/>'
        )

        edge_label = _text(edge.get("label") or edge.get("wire") or edge.get("net"))
        if edge_label:
            parts.append(
                f'<text x="{label_x}" y="{label_y}" text-anchor="middle" '
                f'font-family="Inter,Arial,sans-serif" font-size="16" font-weight="600" '
                f'fill="#475569">{esc(edge_label[:70])}</text>'
            )

    for index, node in enumerate(nodes):
        node_id = _text(node.get("id")) or f"node_{index + 1}"
        x, y = positions[node_id]
        kind = kind_by_id.get(node_id, "generic")

        styles = {
            "power": ("#eff6ff", "#1d4ed8"),
            "fuse": ("#fff7ed", "#c2410c"),
            "switch": ("#f0f9ff", "#0369a1"),
            "lamp": ("#fffbeb", "#a16207"),
            "motor": ("#f5f3ff", "#6d28d9"),
            "resistor": ("#f8fafc", "#475569"),
            "controller": ("#ecfeff", "#0f766e"),
            "generic": ("#f8fafc", "#475569"),
        }
        fill, stroke = styles.get(kind, styles["generic"])

        parts.append(
            f'<g filter="url(#april-shadow)">'
            f'<rect x="{x}" y="{y}" width="{node_w}" height="{node_h}" rx="18" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="3"/>'
            f'</g>'
        )

        ref = _text(node.get("ref") or node.get("reference"))
        if ref:
            parts.append(
                f'<text x="{x + 16}" y="{y + 26}" font-family="Inter,Arial,sans-serif" '
                f'font-size="17" font-weight="700" fill="{stroke}">{esc(ref[:24])}</text>'
            )

        cx = x + node_w / 2
        sy = y + 78

        if kind == "power":
            parts.extend([
                f'<rect x="{cx-46}" y="{sy-27}" width="92" height="54" rx="8" '
                f'fill="#ffffff" stroke="{stroke}" stroke-width="3"/>',
                f'<text x="{cx}" y="{sy+7}" text-anchor="middle" font-family="Inter,Arial,sans-serif" '
                f'font-size="15" font-weight="700" fill="{stroke}">DC</text>',
                f'<line x1="{cx+46}" y1="{sy-20}" x2="{cx+68}" y2="{sy-20}" stroke="{stroke}" stroke-width="3"/>',
                f'<line x1="{cx+68}" y1="{sy+20}" x2="{cx+68}" y2="{sy+20}" stroke="#b91c1c" stroke-width="3"/>',
                f'<line x1="{cx+46}" y1="{sy+20}" x2="{cx+68}" y2="{sy+20}" stroke="#b91c1c" stroke-width="3"/>',
                f'<text x="{cx+76}" y="{sy-14}" font-family="Inter,Arial,sans-serif" font-size="15" font-weight="700" fill="{stroke}">+</text>',
                f'<text x="{cx+76}" y="{sy+26}" font-family="Inter,Arial,sans-serif" font-size="15" font-weight="700" fill="#b91c1c">−</text>',
                f'<line x1="{cx}" y1="{sy+27}" x2="{cx}" y2="{y+node_h+14}" stroke="#b91c1c" stroke-width="3"/>',
            ])
        elif kind == "fuse":
            parts.extend([
                f'<line x1="{cx-58}" y1="{sy}" x2="{cx-28}" y2="{sy}" stroke="{stroke}" stroke-width="3"/>',
                f'<rect x="{cx-28}" y="{sy-13}" width="56" height="26" rx="5" fill="#ffffff" stroke="{stroke}" stroke-width="3"/>',
                f'<line x1="{cx+28}" y1="{sy}" x2="{cx+58}" y2="{sy}" stroke="{stroke}" stroke-width="3"/>',
            ])
        elif kind == "switch":
            parts.extend([
                f'<circle cx="{cx-48}" cy="{sy}" r="5" fill="{stroke}"/>',
                f'<circle cx="{cx+48}" cy="{sy}" r="5" fill="{stroke}"/>',
                f'<line x1="{cx-48}" y1="{sy}" x2="{cx+28}" y2="{sy-28}" stroke="{stroke}" stroke-width="4" stroke-linecap="round"/>',
            ])
        elif kind == "lamp":
            parts.extend([
                f'<circle cx="{cx}" cy="{sy}" r="34" fill="#ffffff" stroke="{stroke}" stroke-width="3"/>',
                f'<line x1="{cx-20}" y1="{sy-20}" x2="{cx+20}" y2="{sy+20}" stroke="{stroke}" stroke-width="3"/>',
                f'<line x1="{cx+20}" y1="{sy-20}" x2="{cx-20}" y2="{sy+20}" stroke="{stroke}" stroke-width="3"/>',
            ])
        elif kind == "motor":
            parts.extend([
                f'<circle cx="{cx}" cy="{sy}" r="34" fill="#ffffff" stroke="{stroke}" stroke-width="3"/>',
                f'<text x="{cx}" y="{sy+8}" text-anchor="middle" font-family="Inter,Arial,sans-serif" '
                f'font-size="28" font-weight="700" fill="{stroke}">M</text>',
            ])
        elif kind == "resistor":
            parts.extend([
                f'<path d="M {cx-55} {sy} l 14 -14 l 14 28 l 14 -28 l 14 28 l 14 -28 l 14 14" '
                f'fill="none" stroke="{stroke}" stroke-width="3" stroke-linejoin="round"/>',
            ])
        elif kind == "controller":
            parts.extend([
                f'<rect x="{cx-50}" y="{sy-30}" width="100" height="60" rx="8" '
                f'fill="#ffffff" stroke="{stroke}" stroke-width="3"/>',
                f'<text x="{cx}" y="{sy+6}" text-anchor="middle" font-family="Inter,Arial,sans-serif" '
                f'font-size="15" font-weight="700" fill="{stroke}">CTRL</text>',
            ])
        else:
            parts.append(
                f'<rect x="{cx-45}" y="{sy-26}" width="90" height="52" rx="8" '
                f'fill="#ffffff" stroke="{stroke}" stroke-width="3"/>'
            )

        label_lines = text_lines(node.get("label") or node.get("name") or node_id)
        for line_index, line in enumerate(label_lines):
            parts.append(
                f'<text x="{cx}" y="{y+116+line_index*22}" text-anchor="middle" '
                f'font-family="Inter,Arial,sans-serif" font-size="18" font-weight="600" '
                f'fill="#0f172a">{esc(line)}</text>'
            )

        value = _text(node.get("value") or node.get("rating"))
        if value:
            parts.append(
                f'<text x="{cx}" y="{y+156}" text-anchor="middle" '
                f'font-family="Inter,Arial,sans-serif" font-size="14" fill="#64748b">'
                f'{esc(value[:54])}</text>'
            )

    if linked_formula:
        formula = _text(linked_formula)
        parts.append(
            f'<rect x="{margin_x}" y="{height-78}" width="{width-2*margin_x}" height="36" rx="10" '
            f'fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5"/>'
        )
        parts.append(
            f'<text x="{width/2}" y="{height-54}" text-anchor="middle" '
            f'font-family="Inter,Arial,sans-serif" font-size="15" font-weight="600" '
            f'fill="#475569">{esc(("Связь с формулой: " + formula)[:150])}</text>'
        )

    # Reference designators are already shown on each component card;\n    # keep the SVG uncluttered by a second legend line.\n
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
    diagram_type = _text(
        source.get("diagram_type")
        or source.get("representation")
        or source.get("format"),
        "structured_diagram",
    ).lower()

    if not svg and not svg_payload and (nodes or edges):
        generated_svg = _build_schematic_svg(
            nodes,
            edges,
            title=_text(source.get("title") or "Схема подключения"),
            linked_formula=_text(source.get("linked_formula") or ""),
        )

    if generated_svg:
        source["svg"] = generated_svg
        svg = generated_svg

    renderer = _select_renderer(source)

    if not svg and not svg_payload and source.get("ascii"):
        diagram_type = "ascii_schematic"

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
        or source.get("ascii")
        or source.get("ascii_preview")
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
