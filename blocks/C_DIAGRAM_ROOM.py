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


def _normalize_terminals(value: Any) -> Dict[str, Dict[str, Any]]:
    """Normalize terminal/port metadata without inventing electrical semantics."""
    if isinstance(value, dict):
        result: Dict[str, Dict[str, Any]] = {}
        for key, raw in value.items():
            name = _text(key)
            if not name:
                continue
            if isinstance(raw, dict):
                entry = deepcopy(raw)
                entry.setdefault("name", name)
                if "label" not in entry and raw.get("name"):
                    entry["label"] = _text(raw.get("name"))
                result[name] = entry
            else:
                result[name] = {"name": name, "label": _text(raw)}
        return result

    if isinstance(value, (list, tuple)):
        result = {}
        for index, raw in enumerate(value, start=1):
            if isinstance(raw, dict):
                name = _text(
                    raw.get("id") or raw.get("name") or raw.get("key") or f"t{index}"
                )
                entry = deepcopy(raw)
                entry.setdefault("name", name)
                result[name] = entry
            else:
                name = _text(raw) or f"t{index}"
                result[name] = {"name": name, "label": name}
        return result

    return {}


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
        node["kind"] = _text(
            node.get("kind")
            or node.get("symbol")
            or node.get("type")
            or node.get("subtype"),
            "node",
        )

        terminal_source = (
            node.get("terminals")
            if node.get("terminals") is not None
            else node.get("ports")
            if node.get("ports") is not None
            else node.get("contacts")
            if node.get("contacts") is not None
            else node.get("pins")
        )
        node["terminals"] = _normalize_terminals(terminal_source)

        # Preserve common engineering annotations when supplied by the Processor.
        if node.get("reference_designation") and not node.get("ref"):
            node["ref"] = node["reference_designation"]
        if node.get("reference") and not node.get("ref"):
            node["ref"] = node["reference"]
        if node.get("designator") and not node.get("ref"):
            node["ref"] = node["designator"]

        nodes.append(node)

    return nodes


def _normalize_edges(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_edges = (
        _list(payload.get("edges"))
        + _list(payload.get("connections"))
        + _list(payload.get("relations"))
        + _list(payload.get("segments"))
        + _list(payload.get("wires"))
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
        edge["from_node"] = source.split(".", 1)[0]
        edge["to_node"] = target.split(".", 1)[0]
        edge["from_terminal"] = source.split(".", 1)[1] if "." in source else ""
        edge["to_terminal"] = target.split(".", 1)[1] if "." in target else ""

        if "wire" not in edge and edge.get("conductor") is not None:
            edge["wire"] = edge.get("conductor")
        if "net" not in edge and edge.get("net_name") is not None:
            edge["net"] = edge.get("net_name")
        if "label" not in edge and edge.get("description") is not None:
            edge["label"] = edge.get("description")

        waypoints = edge.get("waypoints") or edge.get("points") or edge.get("path")
        if waypoints is not None:
            edge["waypoints"] = deepcopy(waypoints)

        key = (
            source,
            target,
            _text(edge.get("label")),
            _text(edge.get("net")),
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


def _symbol_color(kind: str) -> str:
    k = _text(kind).lower()
    if any(token in k for token in ("source", "supply", "battery", "dc_source", "ac_source")):
        return "#166534"
    if any(token in k for token in ("fuse", "breaker", "rcd", "rccb", "uzo", "protection", "protect")):
        return "#b45309"
    if any(token in k for token in ("switch", "contactor", "relay", "selector", "dpdt")):
        return "#1d4ed8"
    if any(token in k for token in ("motor", "load", "lamp", "actuator")):
        return "#7c3aed"
    if any(token in k for token in ("ground", "earth", "pe")):
        return "#047857"
    return "#475569"


def _split_label(text: str, limit: int = 24, max_lines: int = 3) -> List[str]:
    words = _text(text).split()
    if not words:
        return [""]
    lines: List[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > limit:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: max(0, limit - 1)] + "…"
    return lines


def _node_dimensions(node: Dict[str, Any]) -> tuple[int, int]:
    kind = _text(node.get("kind") or node.get("symbol") or node.get("type")).lower()
    if any(token in kind for token in ("contactor", "relay", "breaker", "rcd", "rccb", "thermal")):
        return (230, 118)
    if any(token in kind for token in ("motor", "source", "battery", "transformer")):
        return (220, 118)
    return (210, 110)


def _explicit_position(node: Dict[str, Any]) -> Optional[tuple[float, float]]:
    position = node.get("position")
    if isinstance(position, dict):
        x = position.get("x")
        y = position.get("y")
        try:
            return float(x), float(y)
        except (TypeError, ValueError):
            return None
    if isinstance(position, (list, tuple)) and len(position) >= 2:
        try:
            return float(position[0]), float(position[1])
        except (TypeError, ValueError):
            return None
    if node.get("x") is not None and node.get("y") is not None:
        try:
            return float(node.get("x")), float(node.get("y"))
        except (TypeError, ValueError):
            return None
    return None


def _resolve_positions(nodes: List[Dict[str, Any]], payload: Dict[str, Any], width: int, height: int) -> Dict[str, tuple[float, float]]:
    positions: Dict[str, tuple[float, float]] = {}
    explicit = False
    for node in nodes:
        pos = _explicit_position(node)
        if pos is not None:
            explicit = True
            positions[_text(node.get("id"))] = pos

    # Explicit coordinates can be either pixel coordinates or normalized [0,1].
    if explicit:
        values = list(positions.values())
        normalized = bool(values) and all(0 <= x <= 1 and 0 <= y <= 1 for x, y in values)
        if normalized:
            left, top, right, bottom = 90, 145, width - 90, height - 145
            positions = {
                node_id: (left + x * (right - left), top + y * (bottom - top))
                for node_id, (x, y) in positions.items()
            }
        return positions

    sections = _list(payload.get("sections"))
    section_rows = []
    for section in sections:
        if isinstance(section, dict):
            section_rows.append(_text(section.get("id") or section.get("name") or section.get("title")))
    if section_rows and len(section_rows) > 1:
        # Group by supplied node section; unknowns remain on the first row.
        groups: Dict[str, List[Dict[str, Any]]] = {row: [] for row in section_rows}
        groups.setdefault("", [])
        for node in nodes:
            key = _text(node.get("section") or node.get("group") or node.get("layer"))
            groups.setdefault(key if key in groups else "", []).append(node)
        usable_rows = [g for g in groups.values() if g]
    else:
        usable_rows = [nodes]

    top = 170
    row_gap = 220
    for row_index, row_nodes in enumerate(usable_rows):
        if not row_nodes:
            continue
        gap = 54
        widths = [_node_dimensions(node)[0] for node in row_nodes]
        total = sum(widths) + gap * max(0, len(row_nodes) - 1)
        start_x = max(70, (width - total) / 2)
        cursor = start_x
        y = top + row_index * row_gap
        for node, node_w in zip(row_nodes, widths):
            positions[_text(node.get("id"))] = (cursor + node_w / 2, y)
            cursor += node_w + gap

    return positions


def _terminal_point(
    node: Dict[str, Any],
    center: tuple[float, float],
    terminal_name: str,
    node_w: int,
    node_h: int,
    *,
    target_center: Optional[tuple[float, float]] = None,
) -> tuple[float, float]:
    cx, cy = center
    terminals = node.get("terminals") or {}
    spec = terminals.get(terminal_name) if isinstance(terminals, dict) else None
    side = _text(spec.get("side") if isinstance(spec, dict) else "").lower()
    explicit = spec.get("position") if isinstance(spec, dict) else None

    if isinstance(explicit, dict):
        try:
            px, py = float(explicit.get("x")), float(explicit.get("y"))
            if 0 <= px <= 1 and 0 <= py <= 1:
                return cx - node_w / 2 + px * node_w, cy - node_h / 2 + py * node_h
            return px, py
        except (TypeError, ValueError):
            pass

    if not side and target_center is not None:
        side = "right" if target_center[0] >= cx else "left"

    names = list(terminals.keys()) if isinstance(terminals, dict) else []
    index = names.index(terminal_name) if terminal_name in names else 0
    count = max(1, len(names))

    if side in {"top", "bottom"}:
        x = cx - node_w / 2 + node_w * ((index + 1) / (count + 1))
        y = cy - node_h / 2 if side == "top" else cy + node_h / 2
        return x, y

    y = cy - node_h / 2 + node_h * ((index + 1) / (count + 1))
    x = cx + node_w / 2 if side == "right" else cx - node_w / 2
    return x, y


def _symbol_svg(kind: str, cx: float, cy: float, accent: str) -> str:
    k = _text(kind).lower()
    parts: List[str] = []
    if "motor" in k:
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="28" fill="none" stroke="{accent}" stroke-width="4"/>')
        parts.append(f'<text x="{cx}" y="{cy + 8}" text-anchor="middle" font-size="26" font-weight="700" fill="{accent}">M</text>')
    elif "lamp" in k or "light" in k:
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="26" fill="none" stroke="{accent}" stroke-width="4"/>')
        parts.append(f'<path d="M {cx-14} {cy-14} L {cx+14} {cy+14} M {cx+14} {cy-14} L {cx-14} {cy+14}" stroke="{accent}" stroke-width="3"/>')
    elif "fuse" in k:
        parts.append(f'<rect x="{cx-32}" y="{cy-12}" width="64" height="24" rx="5" fill="none" stroke="{accent}" stroke-width="4"/>')
        parts.append(f'<path d="M {cx-22} {cy} L {cx-8} {cy} L {cx} {cy-7} L {cx+8} {cy+7} L {cx+22} {cy}" fill="none" stroke="{accent}" stroke-width="3"/>')
    elif any(token in k for token in ("switch", "selector", "dpdt", "contactor")):
        parts.append(f'<circle cx="{cx-22}" cy="{cy+14}" r="5" fill="{accent}"/>')
        parts.append(f'<circle cx="{cx+22}" cy="{cy-14}" r="5" fill="{accent}"/>')
        parts.append(f'<path d="M {cx-17} {cy+11} L {cx+18} {cy-12}" stroke="{accent}" stroke-width="4" stroke-linecap="round"/>')
        if "contactor" in k:
            parts.append(f'<rect x="{cx-34}" y="{cy+20}" width="68" height="20" rx="4" fill="none" stroke="{accent}" stroke-width="3"/>')
    elif any(token in k for token in ("breaker", "rcd", "rccb", "uzo", "protection")):
        parts.append(f'<rect x="{cx-28}" y="{cy-30}" width="56" height="60" rx="8" fill="none" stroke="{accent}" stroke-width="4"/>')
        parts.append(f'<path d="M {cx-15} {cy+18} L {cx+12} {cy-15}" stroke="{accent}" stroke-width="4" stroke-linecap="round"/>')
        if any(token in k for token in ("rcd", "rccb", "uzo")):
            parts.append(f'<circle cx="{cx+12}" cy="{cy+17}" r="6" fill="none" stroke="{accent}" stroke-width="3"/>')
    elif "source" in k or "supply" in k or "battery" in k:
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="28" fill="none" stroke="{accent}" stroke-width="4"/>')
        parts.append(f'<text x="{cx}" y="{cy+8}" text-anchor="middle" font-size="22" font-weight="700" fill="{accent}">DC</text>')
    elif "ground" in k or "earth" in k:
        parts.append(f'<path d="M {cx} {cy-18} L {cx} {cy+2} M {cx-18} {cy+2} L {cx+18} {cy+2} M {cx-12} {cy+10} L {cx+12} {cy+10} M {cx-6} {cy+18} L {cx+6} {cy+18}" stroke="{accent}" stroke-width="3"/>')
    else:
        parts.append(f'<rect x="{cx-30}" y="{cy-24}" width="60" height="48" rx="8" fill="none" stroke="{accent}" stroke-width="3"/>')
    return "".join(parts)


def _build_schematic_svg(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    *,
    width: int = 1600,
    height: int = 820,
    payload: Optional[Dict[str, Any]] = None,
) -> str:
    """Build a deterministic engineering-style SVG from supplied topology.

    The renderer never invents a component or a connection. It only visualizes
    nodes, terminal metadata, positions, wires and annotations already present.
    """
    if not nodes and not edges:
        return ""

    payload = payload or {}
    width = max(1000, int(width))
    height = max(600, int(height))
    esc = html.escape
    positions = _resolve_positions(nodes, payload, width, height)
    node_map = {_text(node.get("id")): node for node in nodes}

    # Keep canvas tall enough for long labels/notes.
    notes = [x for x in _list(payload.get("notes")) if _text(x)]
    legend = payload.get("legend")
    title = _text(payload.get("title")) or "Схема"
    description = _text(payload.get("description"))
    orientation = _text(payload.get("orientation"))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">',
        "<defs>",
        '<marker id="april-wire-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">',
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#334155"/>',
        "</marker>",
        "</defs>",
        '<rect width="100%" height="100%" fill="#ffffff" rx="20"/>',
        f'<text x="60" y="58" font-family="Inter,Arial,sans-serif" font-size="28" font-weight="700" fill="#0f172a">{esc(title)}</text>',
    ]
    if description:
        parts.append(f'<text x="60" y="88" font-family="Inter,Arial,sans-serif" font-size="16" fill="#64748b">{esc(description)}</text>')
    if orientation:
        parts.append(f'<text x="{width-60}" y="58" text-anchor="end" font-family="Inter,Arial,sans-serif" font-size="14" fill="#64748b">{esc(orientation)}</text>')
    parts.append(f'<line x1="50" y1="115" x2="{width-50}" y2="115" stroke="#e2e8f0" stroke-width="2"/>')

    # Optional section bands are visual only and use supplied section names.
    raw_sections = [section for section in _list(payload.get("sections")) if isinstance(section, dict)]
    if raw_sections:
        section_names = [_text(section.get("id") or section.get("name") or section.get("title")) for section in raw_sections]
        section_names = [name for name in section_names if name]
        if section_names:
            y = 145
            parts.append(f'<text x="60" y="{y}" font-family="Inter,Arial,sans-serif" font-size="12" font-weight="700" fill="#94a3b8">РАЗДЕЛ</text>')
            for idx, name in enumerate(section_names):
                x = 120 + idx * 190
                parts.append(f'<text x="{x}" y="{y}" font-family="Inter,Arial,sans-serif" font-size="13" font-weight="600" fill="#475569">{esc(name)}</text>')

    # Draw wires behind components. Explicit waypoints are honored when provided.
    for edge in edges:
        source_node = node_map.get(_text(edge.get("from_node")) or _text(edge.get("from")).split(".", 1)[0])
        target_node = node_map.get(_text(edge.get("to_node")) or _text(edge.get("to")).split(".", 1)[0])
        if not source_node or not target_node:
            continue
        sid, tid = _text(source_node.get("id")), _text(target_node.get("id"))
        sc = positions.get(sid)
        tc = positions.get(tid)
        if not sc or not tc:
            continue
        sw, sh = _node_dimensions(source_node)
        tw, th = _node_dimensions(target_node)
        sp = _terminal_point(source_node, sc, _text(edge.get("from_terminal")), sw, sh, target_center=tc)
        tp = _terminal_point(target_node, tc, _text(edge.get("to_terminal")), tw, th, target_center=sc)

        points = [sp]
        raw_waypoints = edge.get("waypoints")
        if isinstance(raw_waypoints, (list, tuple)):
            for raw in raw_waypoints:
                if isinstance(raw, dict):
                    try:
                        wx, wy = float(raw.get("x")), float(raw.get("y"))
                    except (TypeError, ValueError):
                        continue
                    if 0 <= wx <= 1 and 0 <= wy <= 1:
                        wx = 70 + wx * (width - 140)
                        wy = 155 + wy * (height - 240)
                    points.append((wx, wy))
                elif isinstance(raw, (list, tuple)) and len(raw) >= 2:
                    try:
                        points.append((float(raw[0]), float(raw[1])))
                    except (TypeError, ValueError):
                        pass
        if len(points) == 1:
            # Orthogonal elbow avoids overlapping text and reads like a wiring document.
            mx = (sp[0] + tp[0]) / 2
            points.extend([(mx, sp[1]), (mx, tp[1])])
        points.append(tp)
        path_d = " M ".join((f"{x:.1f},{y:.1f}" for x, y in points))
        path_d = "M " + path_d

        label = _text(edge.get("label"))
        net = _text(edge.get("net"))
        wire = edge.get("wire")
        wire_text = _text(wire) if not isinstance(wire, dict) else _text(wire.get("id") or wire.get("name") or wire.get("type"))
        info = " · ".join([item for item in (net, label, wire_text) if item])
        stroke = _text(edge.get("color")) or "#334155"
        dash = _text(edge.get("line_style") or edge.get("style"))
        dash_attr = ' stroke-dasharray="8 6"' if dash.lower() in {"dashed", "dash", "signal"} else ""
        parts.append(f'<path d="{path_d}" fill="none" stroke="{esc(stroke)}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"{dash_attr}/>')
        if edge.get("arrow") or edge.get("directed"):
            parts.append(f'<path d="M {tp[0]-10:.1f},{tp[1]:.1f} L {tp[0]:.1f},{tp[1]:.1f}" fill="none" stroke="{esc(stroke)}" stroke-width="3" marker-end="url(#april-wire-arrow)"/>')
        if info:
            lx = (sp[0] + tp[0]) / 2
            ly = (sp[1] + tp[1]) / 2 - 10
            parts.append(f'<rect x="{lx-90:.1f}" y="{ly-12:.1f}" width="180" height="22" rx="7" fill="#ffffff" stroke="#e2e8f0"/>')
            parts.append(f'<text x="{lx:.1f}" y="{ly+4:.1f}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="12" fill="#475569">{esc(info[:52])}</text>')

    # Junctions are explicit only; they are not inferred from crossings.
    for junction in _list(payload.get("junctions")):
        if not isinstance(junction, dict):
            continue
        try:
            jx, jy = float(junction.get("x")), float(junction.get("y"))
        except (TypeError, ValueError):
            continue
        if 0 <= jx <= 1 and 0 <= jy <= 1:
            jx = 70 + jx * (width - 140)
            jy = 155 + jy * (height - 240)
        parts.append(f'<circle cx="{jx}" cy="{jy}" r="7" fill="#0f172a"/>')

    for node in nodes:
        node_id = _text(node.get("id"))
        if node_id not in positions:
            continue
        cx, cy = positions[node_id]
        node_w, node_h = _node_dimensions(node)
        x, y = cx - node_w / 2, cy - node_h / 2
        kind = _text(node.get("kind") or node.get("symbol") or node.get("type"), "node")
        accent = _symbol_color(kind)
        ref = _text(node.get("ref") or node.get("reference_designation") or node.get("reference"))
        value = _text(node.get("value") or node.get("rating") or node.get("specification"))
        label = _text(node.get("label") or node.get("name") or node_id)
        fill = "#f8fafc"
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{node_w}" height="{node_h}" rx="16" fill="{fill}" stroke="#cbd5e1" stroke-width="2"/>')
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="8" height="{node_h}" rx="4" fill="{accent}"/>')
        parts.append(_symbol_svg(kind, x + 62, cy - 2, accent))

        text_x = x + 105
        if ref:
            parts.append(f'<text x="{text_x:.1f}" y="{y+24:.1f}" font-family="Inter,Arial,sans-serif" font-size="12" font-weight="700" fill="{accent}">{esc(ref)}</text>')
        lines = _split_label(label, 22, 3)
        base_y = y + (46 if ref else 34)
        for i, line in enumerate(lines):
            parts.append(f'<text x="{text_x:.1f}" y="{base_y + i*21:.1f}" font-family="Inter,Arial,sans-serif" font-size="15" font-weight="600" fill="#0f172a">{esc(line)}</text>')
        if value:
            parts.append(f'<text x="{text_x:.1f}" y="{y+node_h-16:.1f}" font-family="Inter,Arial,sans-serif" font-size="11" fill="#64748b">{esc(value[:44])}</text>')

        # Explicit terminal names are rendered at their connection side.
        terminals = node.get("terminals") or {}
        if isinstance(terminals, dict):
            for terminal_name, spec in terminals.items():
                tp = _terminal_point(node, (cx, cy), terminal_name, node_w, node_h)
                parts.append(f'<circle cx="{tp[0]:.1f}" cy="{tp[1]:.1f}" r="5" fill="#ffffff" stroke="{accent}" stroke-width="2"/>')
                term_label = _text(spec.get("label") if isinstance(spec, dict) else "") or terminal_name
                side = _text(spec.get("side") if isinstance(spec, dict) else "").lower()
                anchor = "start" if side == "right" else "end" if side == "left" else "middle"
                dx = 9 if anchor == "start" else -9 if anchor == "end" else 0
                parts.append(f'<text x="{tp[0]+dx:.1f}" y="{tp[1]-8:.1f}" text-anchor="{anchor}" font-family="Inter,Arial,sans-serif" font-size="10" fill="#64748b">{esc(term_label[:18])}</text>')

    # Explicit legend / notes remain compact and do not alter topology.
    bottom = height - 110
    if legend:
        legend_items = []
        if isinstance(legend, dict):
            legend_items = [f"{_text(k)}: {_text(v)}" for k, v in legend.items() if _text(k) and _text(v)]
        else:
            legend_items = [_text(item) for item in _list(legend) if _text(item)]
        if legend_items:
            parts.append(f'<text x="60" y="{bottom}" font-family="Inter,Arial,sans-serif" font-size="12" font-weight="700" fill="#475569">Легенда</text>')
            parts.append(f'<text x="60" y="{bottom+24}" font-family="Inter,Arial,sans-serif" font-size="12" fill="#64748b">{esc(" · ".join(legend_items)[:180])}</text>')
    if notes:
        note_text = " · ".join(_text(note) for note in notes)[:220]
        parts.append(f'<text x="60" y="{height-42}" font-family="Inter,Arial,sans-serif" font-size="12" fill="#64748b">{esc(note_text)}</text>')

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
        generated_svg = _build_schematic_svg(nodes, edges, payload=source)

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
        "diagram_schema": "april.diagram.canonical.v3",
        "professional_render_model": {
            "component_metadata": True,
            "terminal_topology": True,
            "wire_metadata": True,
            "explicit_geometry": True,
            "junctions_explicit_only": True,
            "symbol_vocabulary": "iec60617_inspired",
        },
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
            "no_invented_topology": True,
            "terminal_topology_explicit": True,
            "wire_metadata_preserved": True,
            "reference_designations_preserved": True,
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
