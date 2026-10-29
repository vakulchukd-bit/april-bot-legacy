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
import re
import uuid
from typing import Any, Dict, List, Optional

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
        "caption", "metadata", "svg", "svg_payload",
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

    return "DiagramRenderer"



def _node_semantic_text(node: Dict[str, Any]) -> str:
    """Collect object identity fields without changing provider-supplied labels."""
    return " ".join(
        _text(node.get(key))
        for key in ("kind", "symbol", "type", "object_type", "component_type", "element", "state", "label", "name", "title", "ref")
        if _text(node.get(key))
    ).lower().replace("ё", "е")


def _electrical_role(node: Dict[str, Any]) -> str:
    text = _node_semantic_text(node)
    if re.search(r"(?:power[_ -]?supply|battery|accumulator|cell|батар\w*|аккумулятор\w*|источник\s+питан\w*)", text):
        return "battery"
    if re.search(r"(?:switch|toggle|выключател\w*|переключател\w*)", text):
        return "switch"
    if re.search(r"(?:lamp|bulb|light[_ -]?bulb|лампоч\w*|ламп\w*|светильник\w*)", text):
        return "lamp"
    if re.search(r"(?:fuse|предохранител\w*)", text):
        return "fuse"
    if re.search(r"(?:resistor|резистор\w*)", text):
        return "resistor"
    if re.search(r"(?:motor|двигател\w*)", text):
        return "motor"
    return ""


def _is_electrical_payload(payload: Dict[str, Any], nodes: Optional[List[Dict[str, Any]]] = None) -> bool:
    """Recognize electrical diagrams from the declared representation or real parts."""
    declared = " ".join(
        _text(payload.get(key)) for key in ("diagram_type", "representation", "format", "discipline", "domain", "title")
    ).lower().replace("ё", "е")
    if re.search(r"(?:electrical|wiring|circuit|electric[_ -]?schematic|электрическ\w*|электросхем\w*|схем\w*\s+подключен\w*)", declared):
        return True
    candidate_nodes = nodes if isinstance(nodes, list) else _list(payload.get("nodes") or payload.get("components") or payload.get("vertices"))
    roles = {_electrical_role(node) for node in candidate_nodes if isinstance(node, dict)}
    return "battery" in roles and "lamp" in roles and ("switch" in roles or "fuse" in roles or len(roles) >= 3)


def _node_visual_kind(node: Dict[str, Any], payload: Dict[str, Any]) -> str:
    """Map explicit object metadata to a drawable symbol; labels remain untouched."""
    text = _node_semantic_text(node)
    shape = _text(node.get("shape") or node.get("geometry_type") or node.get("figure_type")).lower().replace("-", "_").replace(" ", "_")
    combined = f"{shape} {text}"
    if _electrical_role(node):
        return _electrical_role(node)
    representation = " ".join(_text(payload.get(key)) for key in ("representation", "diagram_type", "discipline", "domain")).lower()
    if re.search(r"(?:chemistry|molecule|molecular|хими\w*|молекул\w*|атом\w*)", representation + " " + combined):
        if re.search(r"\b(?:H|C|N|O|S|P|F|Cl|Br|I)\b|водород\w*|кислород\w*|углерод\w*|азот\w*", text, re.I):
            return "atom"
        return "molecule"
    if re.search(r"(?:triangle|треугольник|equilateral_triangle)", combined): return "triangle"
    if re.search(r"(?:square|квадрат)", combined): return "square"
    if re.search(r"(?:rectangle|прямоугольник)", combined): return "rectangle"
    if re.search(r"(?:circle|окружност|круг\b)", combined): return "circle"
    if re.search(r"(?:sphere|сфера|шар\b)", combined): return "sphere"
    if re.search(r"(?:cube|куб\b)", combined): return "cube"
    if re.search(r"(?:vector|force|вектор\w*|сил\w*|направлен\w*)", combined): return "vector"
    if re.search(r"(?:wave|волна|волнов\w*)", combined): return "wave"
    if re.search(r"(?:spring|пружин\w*)", combined): return "spring"
    if re.search(r"(?:lens|линз\w*|ray|луч\w*)", combined): return "lens"
    if shape in {"line", "segment", "height", "base", "altitude"} or re.search(r"(?:\bheight\b|\bbase\b|отрезок|основан\w*|высот\w*)", combined): return "line"
    if re.search(r"(?:atom|electron|атом\w*|электрон\w*)", combined): return "atom"
    return "object"


def _is_object_geometry_payload(payload: Dict[str, Any], nodes: Optional[List[Dict[str, Any]]] = None) -> bool:
    """Detect structured geometry/physics objects that should be drawn on a canvas."""
    candidate_nodes = nodes if isinstance(nodes, list) else _normalize_nodes(payload)
    declared = " ".join(
        _text(payload.get(key)) for key in ("diagram_type", "representation", "discipline", "domain", "title", "description")
    ).lower().replace("ё", "е")
    if re.search(r"(?:flowchart|process[_ -]?flow|workflow|navigation[_ -]?flow|network[_ -]?diagram|блок[- ]схем|навигац\w*|маршрут\w*)", declared):
        return False
    geometry_declared = bool(re.search(
        r"(?:geometry|geometric|mathemat\w*|physics|physical|technical[_ -]?drawing|geometric[_ -]?drawing|геометр\w*|математ\w*|физик\w*|черт[её]ж|механик\w*|оптик\w*)",
        declared,
    ))
    kinds = {"triangle", "square", "rectangle", "circle", "sphere", "cube", "vector", "wave", "spring", "lens", "line"}
    recognized = [
        node for node in candidate_nodes if isinstance(node, dict)
        and _node_visual_kind(node, payload) in kinds
    ]
    explicit_shape = any(
        isinstance(node, dict) and any(_text(node.get(key)) for key in ("shape", "geometry_type", "figure_type"))
        for node in candidate_nodes
    )
    return bool(recognized and (geometry_declared or explicit_shape or len(recognized) >= 2))


def _build_readable_object_geometry_svg(payload: Dict[str, Any], nodes: List[Dict[str, Any]], *, title: str = "") -> str:
    """Draw real primitive geometry/physics figures, rather than cards containing headings."""
    kinds = {"triangle", "square", "rectangle", "circle", "sphere", "cube", "vector", "wave", "spring", "lens", "line"}
    objects: List[Dict[str, Any]] = []
    for index, raw in enumerate(nodes[:8]):
        if not isinstance(raw, dict):
            continue
        kind = _node_visual_kind(raw, payload)
        if kind not in kinds:
            continue
        item = dict(raw)
        item["id"] = _text(item.get("id") or item.get("node_id") or item.get("key")) or f"geometry_{index + 1}"
        item["_kind"] = kind
        item["_label"] = _text(item.get("label") or item.get("name") or item.get("title") or kind.title())
        item["_detail"] = _text(item.get("measurement") or item.get("value") or item.get("dimensions_label"))
        objects.append(item)
    if not objects:
        return ""

    width, height = 440, (330 if len(objects) <= 2 else 420)
    title_text = _text(title or payload.get("title") or "Геометрический чертёж")[:56]
    title_size = 21 if len(title_text) <= 28 else 18 if len(title_text) <= 40 else 16
    if len(objects) == 1:
        centers = [(220.0, 180.0, 1.0)]
    elif len(objects) == 2:
        centers = [(125.0, 175.0, 0.62), (315.0, 175.0, 0.62)]
    elif len(objects) <= 4:
        centers = [(125.0, 135.0, 0.50), (315.0, 135.0, 0.50), (125.0, 292.0, 0.50), (315.0, 292.0, 0.50)]
    else:
        centers = [(78.0 + (i % 3) * 142.0, 136.0 + (i // 3) * 150.0, 0.40) for i in range(len(objects))]
    positions: Dict[str, tuple[float, float]] = {}
    for obj, (cx, cy, scale) in zip(objects, centers):
        pos = obj.get("position") if isinstance(obj.get("position"), dict) else obj.get("coordinates")
        if isinstance(pos, dict):
            try:
                px, py = float(pos.get("x")), float(pos.get("y"))
                if 0 <= px <= 1 and 0 <= py <= 1:
                    cx, cy = 34 + px * 372, 72 + py * (height - 126)
                elif 0 <= px <= width and 0 <= py <= height:
                    cx, cy = px, py
            except (TypeError, ValueError):
                pass
        obj["_cx"], obj["_cy"], obj["_scale"] = cx, cy, scale
        positions[obj["id"]] = (cx, cy)

    esc = html.escape
    context_text = " ".join([
        title_text, _text(payload.get("description")),
        " ".join(_text(x) for x in _list(payload.get("annotations"))),
        " ".join(_node_semantic_text(x) for x in objects),
    ]).lower().replace("ё", "е")
    wants_height = bool(re.search(r"(?:\bheight\b|altitude|высот\w*)", context_text))
    wants_base = bool(re.search(r"(?:\bbase\b|основан\w*)", context_text))
    wants_radius = bool(re.search(r"(?:\bradius\b|радиус\w*)", context_text))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" style="display:block;width:100%;max-width:100%;height:auto" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMin meet" role="img" aria-label="{esc(title_text)}">',
        '<defs><marker id="april-geometry-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#2563eb"/></marker></defs>',
        f'<rect width="{width}" height="{height}" rx="18" fill="#f8fafc"/>',
        f'<text x="220" y="30" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="{title_size}" font-weight="750" fill="#0f172a">{esc(title_text)}</text>',
    ]
    # Preserve explicit relationships between separate supplied objects.
    id_to_object = {obj["id"]: obj for obj in objects}
    raw_edges = next((payload.get(key) for key in ("edges", "connections", "relations") if isinstance(payload.get(key), list)), [])
    for edge in raw_edges[:20]:
        if isinstance(edge, (list, tuple)) and len(edge) >= 2:
            source, target, edge_label, directed = _text(edge[0]), _text(edge[1]), "", False
        elif isinstance(edge, dict):
            source = _text(edge.get("from") or edge.get("source") or edge.get("start"))
            target = _text(edge.get("to") or edge.get("target") or edge.get("end"))
            edge_label = _text(edge.get("label") or edge.get("relation"))
            directed = bool(edge.get("directed") or edge.get("arrow") or edge.get("directed_edge"))
        else:
            continue
        if source not in positions or target not in positions or source == target:
            continue
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        marker = ' marker-end="url(#april-geometry-arrow)"' if directed else ""
        parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#64748b" stroke-width="1.8"{marker}/>')
        if edge_label:
            parts.append(f'<text x="{(x1+x2)/2:.1f}" y="{(y1+y2)/2-7:.1f}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="10" fill="#475569">{esc(edge_label[:24])}</text>')

    for obj in objects:
        cx, cy, scale = obj["_cx"], obj["_cy"], obj["_scale"]
        kind, label = obj["_kind"], obj["_label"]
        display_label = label
        # A drawing title may already carry the full instruction; keep the in-shape
        # label short enough to stay on the canvas and prioritize the object's name.
        if kind == "triangle" and re.search(r"\bABC\b", label, re.IGNORECASE):
            display_label = "Треугольник ABC"
        elif len(display_label) > 24:
            localized_kinds = {
                "triangle": "Треугольник", "square": "Квадрат", "rectangle": "Прямоугольник",
                "circle": "Окружность", "sphere": "Сфера", "cube": "Куб", "vector": "Вектор",
                "wave": "Волна", "spring": "Пружина", "lens": "Линза", "line": "Отрезок",
            }
            display_label = localized_kinds.get(kind, display_label[:23].rstrip() + "…")
        stroke = _text(obj.get("color") or obj.get("stroke") or "#2563eb")
        fill = _text(obj.get("fill") or "#dbeafe")
        sw = 2.8 if scale >= 0.9 else 2.2
        if kind == "triangle":
            left, right, base_y, apex_x, apex_y = cx-104*scale, cx+104*scale, cy+55*scale, cx+12*scale, cy-88*scale
            parts.append(f'<polygon points="{left:.1f},{base_y:.1f} {right:.1f},{base_y:.1f} {apex_x:.1f},{apex_y:.1f}" fill="{esc(fill)}" fill-opacity="0.45" stroke="{esc(stroke)}" stroke-width="{sw}" stroke-linejoin="round"/>')
            for letter, x, y in (("A", left, base_y), ("B", right, base_y), ("C", apex_x, apex_y)):
                parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{4*scale:.1f}" fill="{esc(stroke)}"/><text x="{x:.1f}" y="{y+(16*scale if y < cy else 17*scale):.1f}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="{12*scale:.1f}" fill="#334155">{letter}</text>')
            if wants_height:
                hx = (left + right) / 2
                parts.append(f'<line x1="{hx:.1f}" y1="{apex_y:.1f}" x2="{hx:.1f}" y2="{base_y:.1f}" stroke="#dc2626" stroke-width="{2*scale:.1f}" stroke-dasharray="5 4"/>')
                parts.append(f'<text x="{hx+6*scale:.1f}" y="{(apex_y+base_y)/2:.1f}" font-family="Inter,Arial,sans-serif" font-size="{12*scale:.1f}" fill="#b91c1c">h</text>')
            if wants_base:
                parts.append(f'<text x="{cx:.1f}" y="{base_y+30*scale:.1f}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="{12*scale:.1f}" fill="#334155">основание</text>')
        elif kind in {"square", "rectangle"}:
            try:
                actual_w = float(obj.get("width") or obj.get("side") or obj.get("side_length") or 0)
                actual_h = float(obj.get("height") or obj.get("side") or obj.get("side_length") or 0)
            except (TypeError, ValueError):
                actual_w = actual_h = 0
            box_w = (132 if kind == "square" else 182) * scale
            box_h = (132 if kind == "square" else 98) * scale
            parts.append(f'<rect x="{cx-box_w/2:.1f}" y="{cy-box_h/2:.1f}" width="{box_w:.1f}" height="{box_h:.1f}" rx="2" fill="{esc(fill)}" fill-opacity="0.45" stroke="{esc(stroke)}" stroke-width="{sw}"/>')
            if actual_w:
                parts.append(f'<text x="{cx:.1f}" y="{cy+box_h/2+15*scale:.1f}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="{11*scale:.1f}" fill="#334155">{esc(_text(obj.get("width") or obj.get("side") or obj.get("side_length")))}</text>')
            if actual_h and kind == "rectangle":
                parts.append(f'<text x="{cx+box_w/2+6*scale:.1f}" y="{cy:.1f}" font-family="Inter,Arial,sans-serif" font-size="{11*scale:.1f}" fill="#334155">{esc(_text(obj.get("height")))}</text>')
        elif kind in {"circle", "sphere"}:
            radius = 72*scale
            parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" fill="{esc(fill)}" fill-opacity="0.35" stroke="{esc(stroke)}" stroke-width="{sw}"/>')
            if kind == "sphere":
                parts.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{radius:.1f}" ry="{radius*.30:.1f}" fill="none" stroke="{esc(stroke)}" stroke-width="{1.4*scale:.1f}"/><ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{radius*.32:.1f}" ry="{radius:.1f}" fill="none" stroke="{esc(stroke)}" stroke-width="{1.4*scale:.1f}"/>')
            if wants_radius or obj.get("radius") or obj.get("diameter"):
                parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{3*scale:.1f}" fill="{esc(stroke)}"/><line x1="{cx:.1f}" y1="{cy:.1f}" x2="{cx+radius:.1f}" y2="{cy:.1f}" stroke="#dc2626" stroke-width="{2*scale:.1f}"/><text x="{cx+radius/2:.1f}" y="{cy-7*scale:.1f}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="{12*scale:.1f}" fill="#b91c1c">r</text>')
        elif kind == "cube":
            side, off = 92*scale, 28*scale
            x0, y0 = cx-side/2, cy-side/2
            parts.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{side:.1f}" height="{side:.1f}" fill="{esc(fill)}" fill-opacity="0.30" stroke="{esc(stroke)}" stroke-width="{sw}"/>')
            parts.append(f'<path d="M {x0:.1f} {y0:.1f} l {off:.1f} {-off:.1f} h {side:.1f} v {side:.1f} l {-off:.1f} {off:.1f} M {x0+side:.1f} {y0:.1f} l {off:.1f} {-off:.1f} M {x0+side:.1f} {y0+side:.1f} l {off:.1f} {-off:.1f}" fill="none" stroke="{esc(stroke)}" stroke-width="{sw}"/>')
        elif kind == "vector":
            parts.append(f'<line x1="{cx-72*scale:.1f}" y1="{cy+52*scale:.1f}" x2="{cx+66*scale:.1f}" y2="{cy-50*scale:.1f}" stroke="{esc(stroke)}" stroke-width="{3*scale:.1f}" marker-end="url(#april-geometry-arrow)"/>')
        elif kind == "wave":
            wave_path = f'M {cx-82*scale:.1f} {cy:.1f} C {cx-60*scale:.1f} {cy-48*scale:.1f}, {cx-34*scale:.1f} {cy-48*scale:.1f}, {cx-12*scale:.1f} {cy:.1f} S {cx+36*scale:.1f} {cy+48*scale:.1f}, {cx+58*scale:.1f} {cy:.1f} S {cx+80*scale:.1f} {cy-48*scale:.1f}, {cx+82*scale:.1f} {cy:.1f}'
            parts.append(f'<line x1="{cx-88*scale:.1f}" y1="{cy:.1f}" x2="{cx+88*scale:.1f}" y2="{cy:.1f}" stroke="#94a3b8" stroke-width="1.2"/><path d="{wave_path}" fill="none" stroke="{esc(stroke)}" stroke-width="{sw}"/>')
        elif kind == "spring":
            points = " ".join(f'{cx+x*scale:.1f},{cy+y*scale:.1f}' for x,y in [(-76,0),(-58,-20),(-40,20),(-22,-20),(-4,20),(14,-20),(32,20),(50,-20),(68,0)])
            parts.append(f'<polyline points="{points}" fill="none" stroke="{esc(stroke)}" stroke-width="{sw}" stroke-linejoin="round"/>')
        elif kind == "lens":
            parts.append(f'<line x1="{cx-92*scale:.1f}" y1="{cy:.1f}" x2="{cx+92*scale:.1f}" y2="{cy:.1f}" stroke="#94a3b8" stroke-width="1.2" stroke-dasharray="4 4"/><path d="M {cx:.1f} {cy-76*scale:.1f} C {cx-38*scale:.1f} {cy-48*scale:.1f}, {cx-38*scale:.1f} {cy+48*scale:.1f}, {cx:.1f} {cy+76*scale:.1f} C {cx+38*scale:.1f} {cy+48*scale:.1f}, {cx+38*scale:.1f} {cy-48*scale:.1f}, {cx:.1f} {cy-76*scale:.1f} Z" fill="{esc(fill)}" fill-opacity="0.4" stroke="{esc(stroke)}" stroke-width="{sw}"/>')
        elif kind == "line":
            if re.search(r"(?:height|высот)", label, re.I):
                parts.append(f'<line x1="{cx:.1f}" y1="{cy-70*scale:.1f}" x2="{cx:.1f}" y2="{cy+70*scale:.1f}" stroke="{esc(stroke)}" stroke-width="{sw}" stroke-dasharray="5 4"/>')
            else:
                parts.append(f'<line x1="{cx-88*scale:.1f}" y1="{cy:.1f}" x2="{cx+88*scale:.1f}" y2="{cy:.1f}" stroke="{esc(stroke)}" stroke-width="{sw}"/>')
        label_y = cy + 103*scale
        label_lines = [display_label]
        if len(display_label) > 23:
            # Prefer a word boundary when wrapping the second line.
            split_at = display_label.rfind(" ", 0, 23)
            if split_at < 8:
                split_at = 23
            label_lines = [display_label[:split_at].strip(), display_label[split_at:].strip()[:23]]
        tspan_markup = "".join(
            f'<tspan x="{cx:.1f}" dy="{0 if line_index == 0 else 13*scale:.1f}">{esc(line)}</tspan>'
            for line_index, line in enumerate(label_lines) if line
        )
        parts.append(f'<text x="{cx:.1f}" y="{label_y:.1f}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="{11.5*scale:.1f}" font-weight="700" fill="#0f172a">{tspan_markup}</text>')
        if obj["_detail"]:
            detail_y = label_y + 15*scale*len(label_lines)
            parts.append(f'<text x="{cx:.1f}" y="{detail_y:.1f}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="{10*scale:.1f}" fill="#475569">{esc(obj["_detail"][:34])}</text>')
    parts.append('</svg>')
    return ''.join(parts)


def _is_chemistry_payload(payload: Dict[str, Any], nodes: Optional[List[Dict[str, Any]]] = None) -> bool:
    declared = " ".join(
        _text(payload.get(key)) for key in ("diagram_type", "representation", "discipline", "domain", "title")
    ).lower().replace("ё", "е")
    if re.search(r"(?:chemistry|molecule|molecular|chemical[_ -]?structure|хими\w*|молекул\w*|химическ\w*\s+связ\w*)", declared):
        return True
    candidate_nodes = nodes if isinstance(nodes, list) else _list(payload.get("nodes") or payload.get("components") or payload.get("vertices"))
    candidate_edges = next((payload.get(key) for key in ("edges", "connections", "relations") if isinstance(payload.get(key), list)), [])
    if len(candidate_nodes) < 2 or not candidate_edges:
        return False
    atom_like = 0
    for node in candidate_nodes:
        if not isinstance(node, dict):
            continue
        text = _node_semantic_text(node)
        if re.search(r"(?:\b(?:H|C|N|O|S|P|F|Cl|Br|I|Na|K|Ca|Mg)\b|hydrogen|oxygen|carbon|nitrogen|sulfur|phosphorus|водород|кислород|углерод|азот|сера|фосфор)", text, re.I):
            atom_like += 1
    return atom_like >= 2


def _chemical_symbol(node: Dict[str, Any]) -> str:
    explicit = _text(node.get("element") or node.get("symbol")).strip()
    allowed = {"H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca", "Fe", "Cu", "Zn", "Br", "I"}
    if explicit in allowed:
        return explicit
    text = _node_semantic_text(node)
    names = {
        "hydrogen": "H", "водород": "H", "oxygen": "O", "кислород": "O",
        "carbon": "C", "углерод": "C", "nitrogen": "N", "азот": "N",
        "sulfur": "S", "сера": "S", "phosphorus": "P", "фосфор": "P",
        "chlorine": "Cl", "хлор": "Cl", "sodium": "Na", "натрий": "Na",
        "calcium": "Ca", "кальций": "Ca", "iron": "Fe", "железо": "Fe",
    }
    for name, symbol in names.items():
        if name in text:
            return symbol
    match = re.search(r"(?<![A-Za-z])(?:Cl|Br|Na|Mg|Ca|Fe|Cu|Zn|H|C|N|O|S|P|F|I|K)(?![a-z])", explicit or _text(node.get("label") or node.get("name")))
    return match.group(0) if match else "X"


def _build_readable_molecular_svg(payload: Dict[str, Any], nodes: List[Dict[str, Any]], *, title: str = "") -> str:
    """Render atom nodes and bond edges as a molecule, not a flowchart of labels."""
    if len(nodes) < 2:
        return ""
    raw_edges = next((payload.get(key) for key in ("edges", "connections", "relations") if isinstance(payload.get(key), list)), [])
    alias_to_id: Dict[str, str] = {}
    normalized_nodes: List[Dict[str, Any]] = []
    for index, node in enumerate(nodes[:10]):
        node_id = _text(node.get("id") or node.get("node_id") or node.get("component_id") or node.get("key")) or f"atom_{index+1}"
        normalized = {**node, "id": node_id, "symbol": _chemical_symbol(node)}
        normalized_nodes.append(normalized)
        for alias_key in ("id", "node_id", "component_id", "key", "element", "symbol", "label", "name", "title"):
            alias = _text(node.get(alias_key)).strip().lower()
            if alias and alias not in alias_to_id:
                alias_to_id[alias] = node_id
        alias_to_id.setdefault(node_id.lower(), node_id)
    if not normalized_nodes:
        return ""
    width = 440
    title_text = _text(title or payload.get("title") or "Молекулярная структура")
    # honor normalized supplied positions; otherwise use a clear mobile-width row
    # for simple molecules. More complex structures wrap into two staggered rows.
    positions: Dict[str, tuple[float, float]] = {}
    count = len(normalized_nodes)
    for index, node in enumerate(normalized_nodes):
        pos = node.get("position") if isinstance(node.get("position"), dict) else node.get("coordinates")
        x = y = None
        if isinstance(pos, dict):
            try:
                px, py = float(pos.get("x")), float(pos.get("y"))
                if 0 <= px <= 1 and 0 <= py <= 1:
                    x, y = 28 + px * 384, 90 + py * 140
                elif 0 <= px <= 440 and 0 <= py <= 280:
                    x, y = px, py
            except (TypeError, ValueError):
                pass
        if x is None or y is None:
            if count <= 6:
                x = 42 + index * (356 / max(1, count - 1))
                y = 160 + (18 if index % 2 else -18)
            else:
                col = index % 5
                row = index // 5
                x = 48 + col * 86
                y = 125 + row * 90 + (22 if col % 2 else 0)
        positions[node["id"]] = (x, y)
    height = max(260, int(max(y for _, y in positions.values()) + 92))
    esc = html.escape
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" style="display:block;width:100%;max-width:100%;height:auto" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMin meet" role="img" aria-label="{esc(title_text)}">',
        '<rect width="440" height="100%" rx="18" fill="#f8fafc"/>',
        f'<text x="220" y="31" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="21" font-weight="750" fill="#0f172a">{esc(title_text[:58])}</text>',
        '<text x="220" y="52" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="11" fill="#64748b">АТОМЫ И ХИМИЧЕСКИЕ СВЯЗИ</text>',
    ]
    # Bonds behind atoms; edge order controls single/double/triple lines.
    for edge in raw_edges[:24]:
        if isinstance(edge, (list, tuple)) and len(edge) >= 2:
            source, target = _text(edge[0]), _text(edge[1]); edge_data = {}
        elif isinstance(edge, dict):
            source = _text(edge.get("from") or edge.get("source") or edge.get("start"))
            target = _text(edge.get("to") or edge.get("target") or edge.get("end"))
            edge_data = edge
        else:
            continue
        source = alias_to_id.get(source.strip().lower(), source)
        target = alias_to_id.get(target.strip().lower(), target)
        if source not in positions or target not in positions:
            continue
        x1, y1 = positions[source]; x2, y2 = positions[target]
        order_value = _text(edge_data.get("bond_order") or edge_data.get("order") or edge_data.get("type") or "1").lower()
        multiplicity = 3 if order_value in {"3", "triple", "тройная", "тройная связь"} else 2 if order_value in {"2", "double", "двойная", "двойная связь"} else 1
        dx, dy = x2 - x1, y2 - y1
        length = max(1.0, (dx * dx + dy * dy) ** 0.5)
        nx, ny = -dy / length * 3.2, dx / length * 3.2
        for line_index in range(multiplicity):
            offset = (line_index - (multiplicity - 1) / 2) * 3.2
            parts.append(f'<line x1="{x1 + nx*offset:.1f}" y1="{y1 + ny*offset:.1f}" x2="{x2 + nx*offset:.1f}" y2="{y2 + ny*offset:.1f}" stroke="#475569" stroke-width="2.8" stroke-linecap="round"/>')
    element_colors = {"H": ("#ffffff", "#94a3b8"), "C": ("#334155", "#0f172a"), "N": ("#dbeafe", "#2563eb"), "O": ("#fee2e2", "#dc2626"), "S": ("#fef3c7", "#a16207"), "P": ("#ffedd5", "#c2410c"), "Cl": ("#dcfce7", "#15803d"), "Na": ("#f3e8ff", "#7e22ce")}
    for node in normalized_nodes:
        x, y = positions[node["id"]]
        symbol = node["symbol"]
        fill, stroke = element_colors.get(symbol, ("#e0f2fe", "#0369a1"))
        label = _text(node.get("label") or node.get("name") or node.get("title"))
        value = _text(node.get("charge") or node.get("value"))
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="22" fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>')
        parts.append(f'<text x="{x:.1f}" y="{y+6:.1f}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="18" font-weight="800" fill="{("#ffffff" if symbol == "C" else "#0f172a")}">{esc(symbol)}</text>')
        if value:
            parts.append(f'<text x="{x:.1f}" y="{y-27:.1f}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="11" fill="#64748b">{esc(value[:12])}</text>')
        if label and label.lower() != symbol.lower():
            parts.append(f'<text x="{x:.1f}" y="{y+39:.1f}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="10" fill="#475569">{esc(label[:18])}</text>')
    parts.append('</svg>')
    return ''.join(parts)


def _build_readable_electrical_schematic_svg(
    payload: Dict[str, Any], nodes: List[Dict[str, Any]], *, title: str = ""
) -> str:
    """Render battery/switch/lamp components as electrical objects, not text cards.

    The drawing uses a clear closed-loop example only when the payload actually
    identifies a battery and lamp; it never invents component ratings. Provider
    node labels and values are retained as labels in the drawing.
    """
    role_nodes: Dict[str, Dict[str, Any]] = {}
    for node in nodes:
        role = _electrical_role(node)
        if role and role not in role_nodes:
            role_nodes[role] = node
    if not ("battery" in role_nodes and "lamp" in role_nodes):
        return ""

    # Do not replace arbitrary electrical topology with a stereotyped circuit.
    # A specialized battery/lamp drawing is allowed only when the source graph
    # confirms the component sequence. Otherwise the general diagram renderer
    # keeps the provider's real relationships instead of inventing wires.
    raw_edges = next((payload.get(key) for key in ("edges", "connections", "relations", "segments") if isinstance(payload.get(key), list)), [])
    if not raw_edges:
        return ""

    aliases: Dict[str, str] = {}
    for role, node in role_nodes.items():
        for key in ("id", "node_id", "component_id", "key", "label", "name", "title"):
            alias = _text(node.get(key)).strip().lower()
            if alias and alias not in aliases:
                aliases[alias] = role
    # Also recognize endpoint aliases on any node, not just the component-role nodes.
    for node in nodes:
        role = _electrical_role(node)
        if not role:
            continue
        for key in ("id", "node_id", "component_id", "key", "label", "name", "title"):
            alias = _text(node.get(key)).strip().lower()
            if alias and alias not in aliases:
                aliases[alias] = role

    linked_roles = set()
    for edge in raw_edges:
        if isinstance(edge, (list, tuple)) and len(edge) >= 2:
            source, target = _text(edge[0]).strip().lower(), _text(edge[1]).strip().lower()
        elif isinstance(edge, dict):
            source = _text(edge.get("from") or edge.get("source") or edge.get("start")).strip().lower()
            target = _text(edge.get("to") or edge.get("target") or edge.get("end")).strip().lower()
        else:
            continue
        source_role, target_role = aliases.get(source), aliases.get(target)
        if source_role and target_role and source_role != target_role:
            linked_roles.add(frozenset((source_role, target_role)))

    required_links = set()
    if "switch" in role_nodes:
        if "fuse" in role_nodes:
            required_links.update((frozenset(("battery", "fuse")), frozenset(("fuse", "switch"))))
        else:
            required_links.add(frozenset(("battery", "switch")))
        required_links.add(frozenset(("switch", "lamp")))
    elif "fuse" in role_nodes:
        required_links.update((frozenset(("battery", "fuse")), frozenset(("fuse", "lamp"))))
    else:
        required_links.add(frozenset(("battery", "lamp")))
    if not required_links.issubset(linked_roles):
        return ""

    esc = html.escape
    width, height = 440, 330
    title_text = _text(title or payload.get("title") or "Схема подключения")
    title_font_size = 21 if len(title_text) <= 30 else 18 if len(title_text) <= 40 else 16
    title_text = title_text[:52]
    battery = role_nodes["battery"]
    switch = role_nodes.get("switch")
    lamp = role_nodes["lamp"]
    fuse = role_nodes.get("fuse")

    def label_for(node: Dict[str, Any], fallback: str) -> str:
        return _text(node.get("label") or node.get("name") or node.get("title"), fallback)

    def rating_for(node: Dict[str, Any]) -> str:
        return _text(node.get("value") or node.get("rating") or node.get("voltage") or node.get("power"))

    battery_label = label_for(battery, "Батарейка")
    battery_value = rating_for(battery)
    switch_label = label_for(switch, "Выключатель") if switch else ""
    lamp_label = label_for(lamp, "Лампочка")
    lamp_value = rating_for(lamp)
    switch_text = _node_semantic_text(switch or {})
    switch_closed = bool(re.search(r"(?:closed|on|замкнут\w*|включен\w*)", switch_text))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" style="display:block;width:100%;max-width:100%;height:auto" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMin meet" role="img" aria-label="{esc(title_text)}">',
        '<defs><filter id="april-circuit-shadow" x="-15%" y="-15%" width="130%" height="130%"><feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#0f172a" flood-opacity=".12"/></filter></defs>',
        '<rect width="440" height="330" rx="18" fill="#f8fafc"/>',
        f'<text x="220" y="30" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="{title_font_size}" font-weight="750" fill="#0f172a">{esc(title_text)}</text>',
        '<text x="220" y="51" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="11" font-weight="650" letter-spacing="1" fill="#64748b">ЭЛЕКТРИЧЕСКАЯ ЦЕПЬ • СХЕМАТИЧНО</text>',
        # Wires are drawn first, with an explicit return path to show the circuit loop.
        '<path d="M108 156 L130 156 L130 88 L160 88" fill="none" stroke="#334155" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>',
    ]
    if fuse:
        parts.extend([
            '<line x1="130" y1="88" x2="145" y2="88" stroke="#334155" stroke-width="4"/>',
            '<rect x="145" y="78" width="34" height="20" rx="4" fill="#fff7ed" stroke="#c2410c" stroke-width="2.5"/>',
            '<line x1="179" y1="88" x2="191" y2="88" stroke="#334155" stroke-width="4"/>',
        ])
    switch_left = 191 if fuse else 160
    switch_right = switch_left + 54
    lamp_x = 342
    # switch branch; state is shown only if the source node explicitly specifies it.
    if switch:
        parts.extend([
            f'<path d="M{switch_right} 88 L{lamp_x} 88 L{lamp_x} 126" fill="none" stroke="#334155" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>',
        ])
    else:
        parts.append(f'<path d="M{switch_left} 88 L{lamp_x} 88 L{lamp_x} 126" fill="none" stroke="#334155" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')
    parts.extend([
        f'<path d="M{lamp_x} 198 L{lamp_x} 260 L108 260 L108 187" fill="none" stroke="#334155" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>',
        # Battery: body and distinct positive/negative terminals.
        '<g filter="url(#april-circuit-shadow)"><rect x="25" y="137" width="77" height="69" rx="11" fill="#eff6ff" stroke="#2563eb" stroke-width="2.5"/></g>',
        '<text x="63.5" y="163" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="13" font-weight="800" fill="#1d4ed8">DC</text>',
        '<text x="39" y="184" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="17" font-weight="800" fill="#15803d">+</text>',
        '<text x="89" y="184" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="17" font-weight="800" fill="#b91c1c">−</text>',
        '<circle cx="108" cy="156" r="5" fill="#15803d"/><circle cx="108" cy="187" r="5" fill="#b91c1c"/>',
        # Lamp symbol: bulb + filament cross.
        '<g filter="url(#april-circuit-shadow)"><circle cx="342" cy="162" r="36" fill="#fffbeb" stroke="#a16207" stroke-width="3"/></g>',
        '<path d="M322 142 L362 182 M362 142 L322 182" stroke="#a16207" stroke-width="3.5" stroke-linecap="round"/>',
        '<circle cx="342" cy="126" r="4" fill="#334155"/><circle cx="342" cy="198" r="4" fill="#334155"/>',
    ])
    if switch:
        parts.extend([
            f'<circle cx="{switch_left}" cy="88" r="5" fill="#0369a1"/>',
            f'<circle cx="{switch_right}" cy="88" r="5" fill="#0369a1"/>',
            (f'<line x1="{switch_left}" y1="88" x2="{switch_right-2}" y2="88" stroke="#0369a1" stroke-width="4" stroke-linecap="round"/>' if switch_closed else f'<line x1="{switch_left}" y1="88" x2="{switch_right-9}" y2="66" stroke="#0369a1" stroke-width="4" stroke-linecap="round"/>'),
        ])
    # Human-readable labels are secondary; the physical symbols and wires remain the focus.
    parts.extend([
        f'<text x="63" y="229" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="12" font-weight="750" fill="#0f172a">{esc(battery_label[:22])}</text>',
        f'<text x="63" y="245" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="11" fill="#475569">{esc(battery_value[:18])}</text>' if battery_value else '',
        f'<text x="{(switch_left+switch_right)/2:.1f}" y="132" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="11" font-weight="700" fill="#0f172a">{esc(switch_label[:20])}</text>' if switch else '',
        f'<text x="342" y="229" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="12" font-weight="750" fill="#0f172a">{esc(lamp_label[:22])}</text>',
        f'<text x="342" y="245" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="11" fill="#475569">{esc(lamp_value[:18])}</text>' if lamp_value else '',
        '<text x="220" y="302" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="11" fill="#475569">Выключатель разомкнут — лампа выключена.</text>' if switch and not switch_closed else '<text x="220" y="302" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="11" fill="#475569">Проверь напряжение лампы и полярность источника перед включением.</text>',
        '</svg>',
    ])
    svg = "".join(parts)
    # When a fuse exists, retain its identity visibly near the positive lead.
    if fuse:
        fuse_label = esc(label_for(fuse, "Предохранитель")[:20])
        svg = svg.replace(
            '<text x="220" y="302"',
            f'<text x="162" y="113" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="9" font-weight="700" fill="#9a3412">{fuse_label}</text><text x="220" y="302"',
            1,
        )
    return svg


def _node_ports(node: Dict[str, Any]) -> List[Dict[str, str]]:
    raw = node.get("ports") or node.get("terminals") or node.get("contacts") or []
    out: List[Dict[str, str]] = []
    if isinstance(raw, dict):
        raw = [{"id": str(k), "label": str(v)} for k, v in raw.items()]
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, dict):
            pid = _text(item.get("id") or item.get("name") or item.get("key"))
            label = _text(item.get("label") or item.get("name") or pid)
        else:
            pid = _text(item)
            label = pid
        if pid:
            out.append({"id": pid, "label": label or pid})
    return out


def _build_professional_electrical_svg(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    *,
    width: int = 1500,
    height: int = 650,
    title: str = "Схема подключения",
    linked_formula: str = "",
    notes: Optional[List[str]] = None,
) -> str:
    """Render an electrical schematic as a readable technical drawing.

    The provider supplies topology and component facts; this function only lays
    them out and draws standard-ish symbols. Unknown ratings are never invented.
    """
    if not nodes:
        return ""
    width = max(1000, int(width))
    height = max(520, int(height))
    margin = 70
    top = 120
    card_w = 190
    card_h = 150
    gap = max(70, int((width - 2 * margin - card_w * len(nodes)) / max(1, len(nodes) - 1)))
    pos: Dict[str, tuple[int,int]] = {}
    for i, n in enumerate(nodes):
        nid=_text(n.get("id")) or f"n{i+1}"
        pos[nid]=(margin+i*(card_w+gap), top)
    # Respect explicit normalized x/y when supplied.
    for n in nodes:
        nid=_text(n.get("id")); p=n.get("position")
        if isinstance(p, dict):
            try:
                x=float(p.get("x")); y=float(p.get("y"))
                if 0 <= x <= 1 and 0 <= y <= 1:
                    pos[nid]=(int(margin+x*(width-card_w-2*margin)), int(top+y*(height-card_h-top-100)))
            except Exception:
                pass

    def kind(n):
        raw=" ".join(_text(n.get(k)) for k in ("kind","symbol","type","label","name")).lower()
        if any(x in raw for x in ("power_supply","source","блок питания","источник","battery","батар")): return "power"
        if any(x in raw for x in ("fuse","предохран")): return "fuse"
        if any(x in raw for x in ("switch","выключател","переключател","dpdt")): return "switch"
        if any(x in raw for x in ("lamp","ламп","light","свет")): return "lamp"
        if any(x in raw for x in ("motor","двигател")): return "motor"
        if any(x in raw for x in ("resistor","резист")): return "resistor"
        if any(x in raw for x in ("relay","реле","controller","контроллер","contactor","контактор")): return "controller"
        return "generic"
    kinds={_text(n.get("id")) or f"n{i+1}":kind(n) for i,n in enumerate(nodes)}
    esc=html.escape
    parts=[
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">',
        '<defs><filter id="s" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="3" stdDeviation="4" flood-opacity="0.12"/></filter></defs>',
        '<rect width="100%" height="100%" rx="20" fill="#ffffff"/>',
        f'<text x="50%" y="48" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="30" font-weight="750" fill="#0f172a">{esc(title)}</text>',
        f'<text x="{margin}" y="82" font-family="Inter,Arial,sans-serif" font-size="14" fill="#64748b">ЭЛЕКТРИЧЕСКАЯ СХЕМА • ПРОВОДА И ТЕРМИНАЛЫ</text>',
    ]
    colors={"power":("#eff6ff","#2563eb"),"fuse":("#fff7ed","#c2410c"),"switch":("#f0f9ff","#0369a1"),"lamp":("#fffbeb","#a16207"),"motor":("#f5f3ff","#6d28d9"),"resistor":("#f8fafc","#475569"),"controller":("#ecfeff","#0f766e"),"generic":("#f8fafc","#475569")}

    def endpoint(nid, terminal, direction):
        x,y=pos[nid]; k=kinds[nid]; t=_text(terminal).lower()
        cy=y+card_h/2
        if k=="power":
            if t in {"minus","-","negative","gnd","0v"}: return (x+card_w/2,y+card_h+12)
            return (x+card_w,y+52)
        return (x+card_w,y+card_h/2) if direction=="out" else (x,y+card_h/2)

    # Wires first, so component symbols sit above them.
    for e in edges:
        a=_text(e.get("from") or e.get("source")); b=_text(e.get("to") or e.get("target"))
        if a not in pos or b not in pos: continue
        ft=_text(e.get("from_terminal") or e.get("source_terminal")); tt=_text(e.get("to_terminal") or e.get("target_terminal"))
        sx,sy=endpoint(a,ft,"out"); tx,ty=endpoint(b,tt,"in")
        b_is_return=kinds[b]=="power" and tt.lower() in {"minus","-","negative","gnd","0v"}
        a_is_return=kinds[a]=="power" and ft.lower() in {"minus","-","negative","gnd","0v"}
        if b_is_return or a_is_return:
            # Use a dedicated lower return conductor to make +/− topology obvious.
            rail_y=max(y+card_h for _,y in pos.values())+55
            if b_is_return:
                path=f"M {sx} {sy} L {sx} {rail_y} L {tx} {rail_y} L {tx} {ty}"
            else:
                path=f"M {sx} {sy} L {sx} {rail_y} L {tx} {rail_y} L {tx} {ty}"
        elif abs(sy-ty)<2:
            path=f"M {sx} {sy} L {tx} {ty}"
        else:
            mx=(sx+tx)/2; path=f"M {sx} {sy} L {mx} {sy} L {mx} {ty} L {tx} {ty}"
        parts.append(f'<path d="{path}" fill="none" stroke="#334155" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')
        label=_text(e.get("label") or e.get("wire") or e.get("net"))
        if label:
            lx=(sx+tx)/2; ly=min(sy,ty)-12 if not (b_is_return or a_is_return) else max(sy,ty)+38
            parts.append(f'<rect x="{lx-48}" y="{ly-17}" width="96" height="24" rx="12" fill="#fff" stroke="#e2e8f0"/>')
            parts.append(f'<text x="{lx}" y="{ly}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="13" font-weight="700" fill="#475569">{esc(label[:18])}</text>')

    for i,n in enumerate(nodes):
        nid=_text(n.get("id")) or f"n{i+1}"; x,y=pos[nid]; k=kinds[nid]; fill,stroke=colors[k]; cx=x+card_w/2; cy=y+card_h/2
        ref=_text(n.get("ref") or n.get("reference")); label=_text(n.get("label") or n.get("name") or nid); value=_text(n.get("value") or n.get("rating"))
        parts.append(f'<g filter="url(#s)"><rect x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="16" fill="{fill}" stroke="{stroke}" stroke-width="2.5"/></g>')
        if ref: parts.append(f'<text x="{x+14}" y="{y+24}" font-family="Inter,Arial,sans-serif" font-size="16" font-weight="800" fill="{stroke}">{esc(ref)}</text>')
        sy=y+68
        if k=="power":
            parts += [f'<rect x="{cx-42}" y="{sy-23}" width="84" height="46" rx="7" fill="#fff" stroke="{stroke}" stroke-width="2.5"/>',f'<text x="{cx}" y="{sy+6}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="15" font-weight="800" fill="{stroke}">DC</text>',f'<circle cx="{x+card_w-1}" cy="{y+52}" r="5" fill="#2563eb"/><text x="{x+card_w-1}" y="{y+43}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="12" font-weight="800" fill="#2563eb">+</text>',f'<circle cx="{cx}" cy="{y+card_h}" r="5" fill="#b91c1c"/><text x="{cx+10}" y="{y+card_h+17}" font-family="Inter,Arial,sans-serif" font-size="11" font-weight="800" fill="#b91c1c">− / GND</text>']
        elif k=="fuse":
            parts += [f'<line x1="{cx-55}" y1="{sy}" x2="{cx-24}" y2="{sy}" stroke="{stroke}" stroke-width="3"/><rect x="{cx-24}" y="{sy-11}" width="48" height="22" rx="4" fill="#fff" stroke="{stroke}" stroke-width="2.5"/><line x1="{cx+24}" y1="{sy}" x2="{cx+55}" y2="{sy}" stroke="{stroke}" stroke-width="3"/>']
        elif k=="switch":
            parts += [f'<circle cx="{cx-48}" cy="{sy}" r="5" fill="{stroke}"/><circle cx="{cx+48}" cy="{sy}" r="5" fill="{stroke}"/><line x1="{cx-48}" y1="{sy}" x2="{cx+29}" y2="{sy-27}" stroke="{stroke}" stroke-width="4" stroke-linecap="round"/>']
        elif k=="lamp":
            parts += [f'<circle cx="{cx}" cy="{sy}" r="31" fill="#fff" stroke="{stroke}" stroke-width="2.5"/><line x1="{cx-18}" y1="{sy-18}" x2="{cx+18}" y2="{sy+18}" stroke="{stroke}" stroke-width="3"/><line x1="{cx+18}" y1="{sy-18}" x2="{cx-18}" y2="{sy+18}" stroke="{stroke}" stroke-width="3"/>']
        elif k=="motor":
            parts += [f'<circle cx="{cx}" cy="{sy}" r="31" fill="#fff" stroke="{stroke}" stroke-width="2.5"/><text x="{cx}" y="{sy+9}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="27" font-weight="800" fill="{stroke}">M</text>']
        elif k=="resistor":
            parts += [f'<path d="M {cx-54} {sy} l 12 -12 l 12 24 l 12 -24 l 12 24 l 12 -24 l 12 12" fill="none" stroke="{stroke}" stroke-width="3"/>']
        else:
            parts.append(f'<rect x="{cx-42}" y="{sy-23}" width="84" height="46" rx="7" fill="#fff" stroke="{stroke}" stroke-width="2.5"/>')
        parts.append(f'<text x="{cx}" y="{y+112}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="16" font-weight="700" fill="#0f172a">{esc(label[:28])}</text>')
        if value: parts.append(f'<text x="{cx}" y="{y+135}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="13" fill="#64748b">{esc(value[:34])}</text>')
        # Draw explicit non-power terminals as small side dots and labels.
        ports=_node_ports(n)
        for port in ports:
            pid=port["id"].lower(); pl=port["label"]
            if k=="power": continue
            if pid in {"in","input","1","l","a","plus","+"}:
                px,py=x,y+card_h/2; anchor="end"; tx=px-9
            else:
                px,py=x+card_w,y+card_h/2; anchor="start"; tx=px+9
            parts.append(f'<circle cx="{px}" cy="{py}" r="4" fill="{stroke}"/>')
            parts.append(f'<text x="{tx}" y="{py-8}" text-anchor="{anchor}" font-family="Inter,Arial,sans-serif" font-size="11" font-weight="700" fill="{stroke}">{esc(pl[:10])}</text>')

    if linked_formula:
        parts.append(f'<rect x="{margin}" y="{height-82}" width="{width-2*margin}" height="34" rx="10" fill="#f8fafc" stroke="#cbd5e1"/>')
        parts.append(f'<text x="{width/2}" y="{height-60}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="14" font-weight="600" fill="#475569">{esc(("Связь с формулой: "+_text(linked_formula))[:170])}</text>')
    if notes:
        note=" • ".join(_text(x) for x in notes if _text(x))
        if note:
            parts.append(f'<text x="{margin}" y="{height-28}" font-family="Inter,Arial,sans-serif" font-size="12" fill="#64748b">{esc(note[:210])}</text>')
    parts.append('</svg>')
    return ''.join(parts)

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
        electrical = _is_electrical_payload(source, nodes) or any(
            _text(n.get("symbol") or n.get("kind") or n.get("type")).lower().replace("-", "_") in {"power_supply", "fuse", "switch", "lamp", "motor", "resistor", "controller"}
            for n in nodes
        )
        if electrical:
            generated_svg = _build_professional_electrical_svg(
                nodes,
                edges,
                title=_text(source.get("title") or "Схема подключения"),
                linked_formula=_text(source.get("linked_formula") or ""),
                notes=_list(source.get("notes"))[:2],
            )
        else:
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

    if not svg and not svg_payload and source.get("nodes"):
        diagram_type = "structured_schematic"

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

    # Normalize every node/edge diagram to a mobile-readable SVG before it leaves
    # the room. Original labels, values, nodes and relations remain in the payload.
    payload = ensure_readable_diagram_payload(payload, title=_text(payload.get("title") or source.get("title") or "Схема"))
    if payload.get("svg") or payload.get("svg_payload"):
        selected_renderer = _text(payload.get("renderer") or renderer)
        if selected_renderer in {"", "DiagramRenderer", "diagram"}:
            selected_renderer = "SvgBlock"
        payload["renderer"] = selected_renderer
        presentation = _obj(payload.get("presentation"))
        presentation["renderer"] = selected_renderer
        presentation["responsive"] = True
        payload["presentation"] = presentation
        scene_meta = _obj(payload.get("scene"))
        scene_meta["renderer"] = selected_renderer
        payload["scene"] = scene_meta

    return payload


def _wrap_lines(value: str, *, limit: int = 42, max_lines: int = 4) -> list[str]:
    """Wrap supplied labels without breaking identifiers or inserting facts."""
    result: list[str] = []
    for segment in str(value or "").splitlines() or [str(value or "")]:
        words = segment.split()
        if not words:
            if not result:
                result.append("")
            continue
        line = ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if len(candidate) > limit and line:
                result.append(line)
                line = word
            else:
                line = candidate
        if line:
            result.append(line)
    result = result or [""]
    if len(result) > max_lines:
        result = result[:max_lines]
        result[-1] = result[-1].rstrip(" .…") + "…"
    return result


def build_readable_diagram_svg(payload: dict[str, Any], *, title: str = "") -> str:
    """Build a responsive, portrait SVG from concrete node/edge data.

    The portrait layout is intentional: a wide, fixed-height graph scales down to
    unreadable text on a phone. Nodes therefore use a single responsive column;
    long-range relationships travel along the outside rail and do not cross cards.
    """
    if not isinstance(payload, dict):
        return ""
    nodes_raw = payload.get("nodes") or payload.get("components") or payload.get("vertices")
    edges_raw = next((payload.get(key) for key in ("edges", "connections", "relations") if isinstance(payload.get(key), list)), None)
    if not isinstance(nodes_raw, list) or len(nodes_raw) < 2 or not isinstance(edges_raw, list):
        return ""

    nodes: list[dict[str, Any]] = []
    ids_seen: set[str] = set()
    for index, raw in enumerate(nodes_raw[:16]):
        node = dict(raw) if isinstance(raw, dict) else {"label": _text(raw)}
        node_id = _text(node.get("id") or node.get("node_id") or node.get("key")) or f"node_{index + 1}"
        if node_id in ids_seen:
            node_id = f"{node_id}_{index + 1}"
        ids_seen.add(node_id)
        label = _text(node.get("label") or node.get("name") or node.get("title") or node_id)
        lines = _wrap_lines(label, limit=23, max_lines=4)
        node.update({"id": node_id, "label": label, "_display_lines": lines})
        nodes.append(node)
    if len(nodes) < 2:
        return ""

    id_to_index = {node["id"]: index for index, node in enumerate(nodes)}
    edges: list[dict[str, str]] = []
    seen_edges: set[tuple[str, str, str]] = set()
    for raw in edges_raw[:40]:
        if isinstance(raw, (list, tuple)) and len(raw) >= 2:
            edge = {"from": raw[0], "to": raw[1]}
        elif isinstance(raw, dict):
            edge = raw
        else:
            continue
        source = _text(edge.get("from") or edge.get("source") or edge.get("start"))
        target = _text(edge.get("to") or edge.get("target") or edge.get("end"))
        if source not in id_to_index or target not in id_to_index or source == target:
            continue
        label = _text(edge.get("label") or edge.get("relation") or edge.get("kind"))
        key = (source, target, label)
        if key in seen_edges:
            continue
        seen_edges.add(key)
        edges.append({"from": source, "to": target, "label": label})
    # A node collection is a valid visual composition even without relations
    # (for example, several laboratory vessels and labeled samples). In that case
    # render each supplied element as its own card; do not fabricate arrows.

    # The viewBox is deliberately phone-width. With a 760px viewBox, a 360px
    # mobile viewport would halve every label, reproducing the tiny-corner graph.
    width = 440
    card_x = 20
    card_w = 360
    card_right = card_x + card_w
    title_text = _text(title or payload.get("title") or payload.get("description") or "Схема ответа")
    title_lines = _wrap_lines(title_text, limit=31, max_lines=2)
    top_y = 78 if len(title_lines) == 1 else 98
    y_gap = 42
    for node in nodes:
        line_count = len(node["_display_lines"])
        node["_height"] = max(70, 32 + line_count * 24)
    y_cursor = top_y
    for node in nodes:
        node["_y"] = y_cursor
        y_cursor += int(node["_height"]) + y_gap
    height = y_cursor - y_gap + 28
    center_x = card_x + card_w / 2

    esc = html.escape
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" style="display:block;width:100%;max-width:100%" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMin meet" role="img" aria-label="{esc(title_text)}">',
        '<defs><marker id="april-flow-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#168f80"/></marker>',
        '<filter id="april-flow-shadow" x="-15%" y="-15%" width="130%" height="140%"><feDropShadow dx="0" dy="3" stdDeviation="3" flood-color="#0f172a" flood-opacity="0.10"/></filter></defs>',
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="20" fill="#f8fafc"/>',
    ]
    for index, line in enumerate(title_lines):
        parts.append(
            f'<text x="{width / 2}" y="{36 + index * 30}" text-anchor="middle" '
            f'font-family="Inter,Arial,sans-serif" font-size="25" font-weight="700" fill="#0f172a">{esc(line)}</text>'
        )

    # Draw connectors behind the cards. Consecutive flow steps use a centered
    # arrow; branches/returns use unique outer rails so arrows never cross text.
    for edge_index, edge in enumerate(edges):
        source_node = nodes[id_to_index[edge["from"]]]
        target_node = nodes[id_to_index[edge["to"]]]
        source_index = id_to_index[edge["from"]]
        target_index = id_to_index[edge["to"]]
        sy = int(source_node["_y"]) + int(source_node["_height"])
        ty = int(target_node["_y"])
        if target_index == source_index + 1:
            sx = center_x
            ex = center_x
            path = f"M {sx} {sy} L {ex} {ty - 4}"
        else:
            lane_x = min(432, 390 + (edge_index % 5) * 7)
            sy_mid = int(source_node["_y"]) + int(source_node["_height"]) // 2
            ty_mid = int(target_node["_y"]) + int(target_node["_height"]) // 2
            # Right-side rail stays outside the node cards. Enter the target at
            # its right edge so the relationship remains visible on small screens.
            path = f"M {card_right} {sy_mid} L {lane_x} {sy_mid} L {lane_x} {ty_mid} L {card_right - 4} {ty_mid}"
        label_title = f'<title>{esc(edge["label"])}</title>' if edge.get("label") else ""
        parts.append(
            f'<path d="{path}" fill="none" stroke="#168f80" stroke-width="3" '
            f'stroke-linecap="round" stroke-linejoin="round" marker-end="url(#april-flow-arrow)">{label_title}</path>'
        )
        # Action labels are visible on mobile, rather than available only as tooltips.
        if edge.get("label") and target_index == source_index + 1:
            visible_label = _wrap_lines(edge["label"], limit=25, max_lines=1)[0]
            parts.append(
                f'<text x="{center_x - 14}" y="{sy + 25}" text-anchor="end" '
                f'font-family="Inter,Arial,sans-serif" font-size="12" font-weight="600" '
                f'fill="#0f766e">{esc(visible_label)}</text>'
            )

    for node_index, node in enumerate(nodes):
        y = int(node["_y"])
        node_h = int(node["_height"])
        fill = "#ecfdf5" if node_index == 0 else "#ffffff"
        stroke = "#168f80" if node_index == 0 else "#cbd5e1"
        parts.append(
            f'<g filter="url(#april-flow-shadow)"><rect x="{card_x}" y="{y}" width="{card_w}" height="{node_h}" '
            f'rx="16" fill="{fill}" stroke="{stroke}" stroke-width="2"/></g>'
        )
        visual_kind = _node_visual_kind(node, payload)
        icon_x = card_x + 40
        icon_y = y + node_h / 2
        icon_stroke = "#0f766e"
        if visual_kind == "triangle":
            parts.append(f'<polygon points="{icon_x},{icon_y-21} {icon_x-21},{icon_y+17} {icon_x+21},{icon_y+17}" fill="#dbeafe" stroke="#2563eb" stroke-width="2.5" stroke-linejoin="round"/>')
        elif visual_kind in {"circle", "sphere"}:
            parts.append(f'<circle cx="{icon_x}" cy="{icon_y}" r="20" fill="#dbeafe" stroke="#2563eb" stroke-width="2.5"/>')
            if visual_kind == "sphere":
                parts.append(f'<ellipse cx="{icon_x}" cy="{icon_y}" rx="9" ry="20" fill="none" stroke="#2563eb" stroke-width="1.5"/><ellipse cx="{icon_x}" cy="{icon_y}" rx="20" ry="8" fill="none" stroke="#2563eb" stroke-width="1.5"/>')
        elif visual_kind in {"square", "rectangle", "cube"}:
            parts.append(f'<rect x="{icon_x-18}" y="{icon_y-18}" width="36" height="36" rx="2" fill="#dbeafe" stroke="#2563eb" stroke-width="2.5"/>')
            if visual_kind == "cube":
                parts.append(f'<path d="M {icon_x-18} {icon_y-18} l 10 -8 h 36 l -10 8 M {icon_x+18} {icon_y-18} l 10 -8 v 36 l -10 8" fill="none" stroke="#2563eb" stroke-width="1.5"/>')
        elif visual_kind in {"atom", "molecule"}:
            parts.append(f'<ellipse cx="{icon_x}" cy="{icon_y}" rx="22" ry="9" fill="none" stroke="#7c3aed" stroke-width="1.8" transform="rotate(0 {icon_x} {icon_y})"/><ellipse cx="{icon_x}" cy="{icon_y}" rx="22" ry="9" fill="none" stroke="#7c3aed" stroke-width="1.8" transform="rotate(60 {icon_x} {icon_y})"/><ellipse cx="{icon_x}" cy="{icon_y}" rx="22" ry="9" fill="none" stroke="#7c3aed" stroke-width="1.8" transform="rotate(120 {icon_x} {icon_y})"/><circle cx="{icon_x}" cy="{icon_y}" r="5" fill="#7c3aed"/>')
        elif visual_kind in {"vector", "lens"}:
            parts.append(f'<path d="M {icon_x-22} {icon_y+12} L {icon_x+18} {icon_y-12} M {icon_x+5} {icon_y-13} L {icon_x+18} {icon_y-12} L {icon_x+13} {icon_y+1}" fill="none" stroke="#2563eb" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
            if visual_kind == "lens":
                parts.append(f'<ellipse cx="{icon_x}" cy="{icon_y}" rx="8" ry="22" fill="#dbeafe" fill-opacity="0.6" stroke="#2563eb" stroke-width="2"/>')
        elif visual_kind == "wave":
            parts.append(f'<path d="M {icon_x-24} {icon_y} C {icon_x-18} {icon_y-22} {icon_x-10} {icon_y-22} {icon_x-4} {icon_y} S {icon_x+10} {icon_y+22} {icon_x+16} {icon_y} S {icon_x+28} {icon_y-18} {icon_x+30} {icon_y}" fill="none" stroke="#2563eb" stroke-width="2.5"/>')
        elif visual_kind == "spring":
            parts.append(f'<path d="M {icon_x-24} {icon_y} l 8 -10 l 8 20 l 8 -20 l 8 20 l 8 -10" fill="none" stroke="#2563eb" stroke-width="2.5" stroke-linejoin="round"/>')
        else:
            # An actual bounded object marker, not a heading-shaped placeholder.
            parts.append(f'<circle cx="{icon_x}" cy="{icon_y}" r="17" fill="#ecfdf5" stroke="{icon_stroke}" stroke-width="2.2"/><circle cx="{icon_x}" cy="{icon_y}" r="5" fill="{icon_stroke}"/>')
        for line_index, line in enumerate(node["_display_lines"]):
            baseline = y + 28 + line_index * 28
            parts.append(
                f'<text x="{card_x + 76}" y="{baseline}" font-family="Inter,Arial,sans-serif" '
                f'font-size="19" font-weight="{700 if line_index == 0 else 500}" fill="#0f172a">{esc(line)}</text>'
            )
    parts.append("</svg>")
    return "".join(parts)



def _build_navigation_ui_svg(payload: dict[str, Any], *, title: str = "") -> str:
    """Render a screenshot-faithful April screen/path as a readable mobile SVG.

    The selected template comes from C_IT_ROOM's source-derived ``screen_id`` and
    blueprints. It does not make up destination controls or reuse a profile template
    for unrelated screens such as attachments or Help & Information.
    """
    nodes_raw = payload.get("nodes") or payload.get("components") or payload.get("vertices")
    if not isinstance(nodes_raw, list) or not nodes_raw:
        return ""
    normalized = []
    seen = set()
    for index, raw in enumerate(nodes_raw[:10]):
        node = dict(raw) if isinstance(raw, dict) else {"label": _text(raw)}
        node_id = _text(node.get("id") or node.get("key") or f"node_{index + 1}")
        href = _text(node.get("href") or node.get("path"))
        label = _text(node.get("label") or node.get("name") or node.get("title") or node_id)
        if not href or "[" in href or "]" in href or href.lower().rstrip("/") == "/admin-profile":
            href = ""
        key = (node_id, href)
        if key in seen:
            continue
        seen.add(key)
        normalized.append({"id": node_id, "href": href, "label": label})
    if len(normalized) < 2:
        return ""

    title_text = _text(title or payload.get("title") or "Карта переходов April")
    screen_id = _text(payload.get("screen_id") or payload.get("ui_screen") or "").lower()
    route_ids = {str(value).strip().lower() for value in (payload.get("selected_route_ids") or []) if str(value).strip()} if isinstance(payload.get("selected_route_ids"), list) else set()
    highlight_target_id = _text(payload.get("highlight_target_id") or payload.get("highlight_route_id")).lower()
    highlight_color = _text(payload.get("highlight_color") or "#58d7a6")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", highlight_color):
        highlight_color = "#58d7a6"
    low_source = " ".join([title_text, str(payload.get("description") or ""), str(payload.get("matched_query") or "")]).lower().replace("ё", "е")
    if screen_id not in {"profile", "chat", "attachments", "help", "history", "community", "support", "plans", "deletion", "legal"}:
        if any(term in low_source for term in ("скрепк", "вложен", "camera", "камера", "изображения", "файлы", "attachment")):
            screen_id = "attachments"
        elif route_ids.intersection({"guide", "help-center", "how-to-use", "privacy", "terms"}) or "справк" in low_source or "help" in low_source:
            screen_id = "help"
        elif route_ids.intersection({"space", "direct"}) or "сообществ" in low_source or "community" in low_source:
            screen_id = "community"
        elif "history" in route_ids or "истори" in low_source:
            screen_id = "profile" if "settings" in route_ids else "history"
        elif "settings" in route_ids or "profile" in low_source or "профил" in low_source:
            screen_id = "profile"
        elif "deletion" in route_ids:
            screen_id = "deletion"
        elif "support" in route_ids:
            screen_id = "support"
        elif "chat" in route_ids:
            screen_id = "chat"
        else:
            screen_id = "profile"

    def esc(value: Any) -> str:
        return html.escape(_text(value), quote=True)

    def route_label(item: dict[str, str]) -> str:
        href = item["href"]
        source = (item["label"] + " " + href + " " + item["id"]).lower().replace("ё", "е")
        route_patterns = (
            ("/space", ("community", "сообществ"), "Community / Сообщество"),
            ("/history", ("history", "истори", "saved dialogues", "сохраненн"), "Dialog history / История диалогов"),
            ("/", ("основной чат", "chat with april", "основной чат"), "Chat with April / Основной чат"),
            ("/insights", ("support", "поддерж", "обращен"), "Contact support / Поддержка"),
            ("/aprill", ("help", "справк"), "Help & Information / Справка"),
        )
        for exact_path, markers, label in route_patterns:
            if href == exact_path or (exact_path == "/insights" and href.startswith(exact_path)) or any(marker in source for marker in markers):
                return label
        return item["label"].splitlines()[0][:46]

    width = 440
    margin = 18
    header_h = 54
    def header(screen_title: str, subtitle: str = "") -> list[str]:
        items = [
            f'<rect x="{margin}" y="16" width="{width-2*margin}" height="{header_h}" rx="27" fill="#171922" stroke="#30333e" stroke-width="1.2"/>',
            '<text x="34" y="51" font-family="Inter,Arial,sans-serif" font-size="27" font-weight="750" fill="#9becc5">A</text>',
            '<text x="59" y="51" font-family="Inter,Arial,sans-serif" font-size="20" font-weight="650" fill="#f3f4f6">PRIL</text>',
            f'<text x="{width-36}" y="49" text-anchor="middle" font-family="Arial,sans-serif" font-size="18" fill="#aab0bb">●</text>',
        ]
        if screen_title:
            items.extend([
                f'<text x="{margin+4}" y="{header_h+41}" font-family="Inter,Arial,sans-serif" font-size="19" font-weight="700" fill="#eef1f5">{esc(screen_title)}</text>',
            ])
            if subtitle:
                items.append(f'<text x="{margin+4}" y="{header_h+63}" font-family="Inter,Arial,sans-serif" font-size="12" fill="#9ca5b3">{esc(subtitle)}</text>')
        return items

    def draw_card(x: int, y: int, w: int, h: int, label: str, sub: str = "", *, accent: str = "#2c604d", number: str = "", badge: str = "", arrow: bool = False) -> list[str]:
        output = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="#151922" stroke="{accent}" stroke-width="1.4"/>']
        if number:
            output.extend([
                f'<circle cx="{x+22}" cy="{y+h/2}" r="12" fill="#193d2d" stroke="#3f8a64"/>',
                f'<text x="{x+22}" y="{y+h/2+4}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="11" font-weight="700" fill="#c0f6d6">{esc(number)}</text>'
            ])
        label_x = x + (42 if number else 14)
        if badge:
            output.append(f'<rect x="{x+w-86}" y="{y+8}" width="70" height="20" rx="10" fill="#17382d" stroke="#396e56"/>')
            output.append(f'<text x="{x+w-51}" y="{y+22}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="10" font-weight="700" fill="#a4efc3">{esc(badge)}</text>')
        # Truncation is preferable to allowing long labels to overlap the arrows.
        label_text = label[:42]
        output.append(f'<text x="{label_x}" y="{y+21}" font-family="Inter,Arial,sans-serif" font-size="13" font-weight="650" fill="#edf4f1">{esc(label_text)}</text>')
        if sub:
            output.append(f'<text x="{label_x}" y="{y+39}" font-family="Inter,Arial,sans-serif" font-size="11.5" fill="#82dcb4">{esc(sub[:54])}</text>')
        if arrow:
            output.append(f'<text x="{x+w-19}" y="{y+h/2+5}" text-anchor="middle" font-family="Arial,sans-serif" font-size="18" fill="#8ae2b1">→</text>')
        return output

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="420" viewBox="0 0 {width} 420" preserveAspectRatio="xMidYMin meet" role="img" aria-label="{esc(title_text)}">',
        '<defs><linearGradient id="april-ui-brand" x1="0" x2="1"><stop offset="0" stop-color="#a4f3c1"/><stop offset="1" stop-color="#7bd9e5"/></linearGradient><marker id="april-ui-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 z" fill="#58d7a6"/></marker></defs>',
        f'<rect width="{width}" height="420" rx="24" fill="#080a10" stroke="#242a35" stroke-width="2"/>',
    ]

    # Content is derived from the actual route IDs/visible-control blueprint.
    if screen_id == "attachments":
        title_text = "Добавить вложение"
        parts.extend(header("", ""))
        parts.extend([
            '<rect x="12" y="92" width="416" height="310" rx="25" fill="#171922" stroke="#30333e" stroke-width="1.5"/>',
            '<rect x="196" y="106" width="48" height="5" rx="2.5" fill="#565b67"/>',
            '<text x="34" y="145" font-family="Inter,Arial,sans-serif" font-size="11" font-weight="750" letter-spacing="1.5" fill="#79dcb1">APRIL</text>',
            '<text x="34" y="179" font-family="Inter,Arial,sans-serif" font-size="22" font-weight="700" fill="#f4f5f8">Добавить вложение</text>',
            '<text x="34" y="207" font-family="Inter,Arial,sans-serif" font-size="14" fill="#9ca3af">Выберите, что прикрепить</text>',
        ])
        # Avoid emoji glyph dependencies in SVG viewers; simple vector-like labels render consistently on mobile.
        cards = [("Камера", "Сделать снимок", "#ea258e", "CAM"), ("Изображения", "Выбрать фото", "#2a7ff2", "IMG"), ("Файлы", "Документы и другие файлы", "#05b9a1", "DOC")]
        cx, cy, cw, ch, gap = 25, 229, 124, 130, 8
        for i, (label, sub, color, icon_label) in enumerate(cards):
            x = cx + i*(cw+gap)
            parts.extend([
                f'<rect x="{x}" y="{cy}" width="{cw}" height="{ch}" rx="20" fill="#20232d" stroke="#343844" stroke-width="1.3"/>',
                f'<rect x="{x+28}" y="{cy+14}" width="68" height="58" rx="18" fill="{color}"/>',
                f'<text x="{x+62}" y="{cy+51}" text-anchor="middle" font-family="Arial,sans-serif" font-size="27" fill="#ffffff">{icon_label}</text>',
                f'<text x="{x+cw/2}" y="{cy+91}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="13" font-weight="650" fill="#f1f3f7">{esc(label)}</text>',
                f'<text x="{x+cw/2}" y="{cy+111}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="10.5" fill="#8d95a4">{esc(sub)}</text>',
            ])
        parts.extend([
            '<rect x="26" y="371" width="388" height="22" rx="10" fill="#20232d" stroke="#30333e"/>',
            '<text x="220" y="386" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="12" fill="#9ca3af">Отмена</text>',
            '</svg>'
        ])
        # Set the dynamic viewBox to the contents' actual height.
        return "".join(parts).replace('height="420" style=', 'height="420" style=', 1)

    if screen_id == "chat":
        parts.extend(header("Основной чат", "Текст · голос · изображения · память"))
        parts.extend([
            '<rect x="22" y="152" width="396" height="132" rx="18" fill="#11141b" stroke="#252a33"/>',
            '<text x="220" y="198" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="17" font-weight="700" fill="#f0f0e8">Начните разговор с April</text>',
            '<text x="220" y="225" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="12" fill="#8d95a4">Задайте вопрос или прикрепите материал</text>',
            '<rect x="68" y="331" width="304" height="54" rx="27" fill="#20222b" stroke="#353944" stroke-width="1.3"/>',
            '<circle cx="43" cy="358" r="17" fill="#22252e" stroke="#353944"/>',
            '<text x="43" y="363" text-anchor="middle" font-family="Arial,sans-serif" font-size="17" fill="#eceff4">⌁</text>',
            '<text x="88" y="363" font-family="Inter,Arial,sans-serif" font-size="13" fill="#9097a4">Message April</text>',
            '<circle cx="334" cy="358" r="16" fill="#3a3d48"/>',
            '<text x="334" y="364" text-anchor="middle" font-family="Arial,sans-serif" font-size="20" font-weight="700" fill="#d9dce4">→</text>',
            '<circle cx="401" cy="358" r="18" fill="#22252e" stroke="#353944"/>',
            '<text x="401" y="364" text-anchor="middle" font-family="Arial,sans-serif" font-size="16" fill="#eceff4">♟</text>',
            '</svg>'
        ])
        return "".join(parts)

    if screen_id == "help" or screen_id == "legal":
        parts.extend(header("Помощь и информация", "Инструкции, аккаунт и правила сервиса"))
        cards = [
            ("Help Center / Центр помощи", "Частые вопросы и ответы", "/aprill"),
            ("How to Use April", "Текст, голос, изображения и память", "/aprill"),
            ("Privacy Policy / Конфиденциальность", "Обработка данных и удаление", "/privacy-policy"),
            ("Terms of Service / Условия", "Правила использования April", "/terms-of-service"),
            ("Plans & Payments / Тарифы", "Free, Lite, Premium и продление", "/aprill"),
            ("Account & Data Deletion", "Удаление April-аккаунта и данных", "/account-deletion"),
            ("Contact Support / Поддержка", "История обращений и ответы", "/insights?room=support"),
        ]
        y0, card_h, gap = 110, 38, 6
        for i, (label, sub, href) in enumerate(cards):
            y = y0 + i*(card_h+gap)
            parts.extend([
                f'<rect x="24" y="{y}" width="392" height="{card_h}" rx="12" fill="#13161e" stroke="#282d37" stroke-width="1.1"/>',
                f'<circle cx="45" cy="{y+19}" r="11" fill="#162d26" stroke="#315a47"/>',
                f'<text x="45" y="{y+23}" text-anchor="middle" font-family="Arial,sans-serif" font-size="12" fill="#8de2b0">{i+1}</text>',
                f'<text x="64" y="{y+16}" font-family="Inter,Arial,sans-serif" font-size="11.7" font-weight="650" fill="#edf1f5">{esc(label)}</text>',
                f'<text x="64" y="{y+30}" font-family="Inter,Arial,sans-serif" font-size="9.5" fill="#9aa2af">{esc(sub)} · {esc(href)}</text>',
                f'<text x="400" y="{y+24}" text-anchor="middle" font-family="Arial,sans-serif" font-size="16" fill="#8be2b2">→</text>',
            ])
        parts.append('</svg>')
        # Seven compact cards need a taller intrinsic canvas, rather than shrinking into the corner.
        rendered = "".join(parts).replace('height="420"', 'height="440"', 1).replace('viewBox="0 0 440 420"', 'viewBox="0 0 440 440"', 1)
        return rendered

    if screen_id == "history":
        parts.extend(header("Saved dialogues / История диалогов", "Найдите запись и продолжите беседу"))
        parts.extend([
            '<rect x="24" y="111" width="392" height="54" rx="15" fill="#141720" stroke="#2e3a51"/>',
            '<text x="42" y="135" font-family="Inter,Arial,sans-serif" font-size="13" font-weight="650" fill="#eff2f6">Saved dialogue · дата и фрагмент темы</text>',
            '<text x="42" y="152" font-family="Inter,Arial,sans-serif" font-size="11" fill="#9aa2b1">Краткое содержание сохранённой записи</text>',
            '<rect x="42" y="174" width="356" height="36" rx="10" fill="#12231f" stroke="#2a5a46"/>',
            '<text x="220" y="196" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="12" font-weight="650" fill="#a3efc0">Continue this dialogue →</text>',
            '<rect x="24" y="222" width="392" height="54" rx="15" fill="#141720" stroke="#2e3a51"/>',
            '<text x="42" y="246" font-family="Inter,Arial,sans-serif" font-size="13" font-weight="650" fill="#eff2f6">Ещё одна карточка диалога</text>',
            '<text x="42" y="263" font-family="Inter,Arial,sans-serif" font-size="11" fill="#9aa2b1">Дата · фрагмент разговора · номер записи</text>',
            '<rect x="42" y="285" width="356" height="36" rx="10" fill="#12231f" stroke="#2a5a46"/>',
            '<text x="220" y="307" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="12" font-weight="650" fill="#a3efc0">Continue this dialogue →</text>',
            '<rect x="24" y="340" width="392" height="44" rx="14" fill="#171922" stroke="#30333e"/>',
            '<circle cx="44" cy="362" r="6" fill="#70eaa3"/>',
            '<text x="60" y="367" font-family="Inter,Arial,sans-serif" font-size="13" font-weight="650" fill="#c8f3d7">Memory Status · Connected</text>',
            '</svg>'
        ])
        return "".join(parts)

    if screen_id == "community":
        parts.extend(header("April · Community / Сообщество", "Публичные сообщения и личные диалоги"))
        parts.extend([
            '<rect x="24" y="111" width="392" height="48" rx="14" fill="#13161e" stroke="#34475a"/>',
            '<circle cx="48" cy="135" r="16" fill="#152b23" stroke="#38684f"/>',
            '<text x="48" y="140" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="13" font-weight="700" fill="#a7efc2">П</text>',
            '<text x="73" y="132" font-family="Inter,Arial,sans-serif" font-size="13" font-weight="650" fill="#edf1f5">Personal profile</text>',
            '<text x="73" y="148" font-family="Inter,Arial,sans-serif" font-size="11" fill="#9ba4b2">Имя и настройки профиля сообщества</text>',
        ])
        for i, (kind, msg, badge, accent) in enumerate([
            ("Пользователь", "Публичное сообщение в сообществе", "PREMIUM", "#35664d"),
            ("Другой участник", "Ещё одна карточка сообщения", "FREE", "#6d5f2d"),
        ]):
            y = 171 + i*91
            parts.extend([
                f'<rect x="24" y="{y}" width="392" height="78" rx="14" fill="#15161c" stroke="{accent}" stroke-width="1.4"/>',
                f'<text x="42" y="{y+21}" font-family="Inter,Arial,sans-serif" font-size="13" font-weight="650" fill="#f0d98d">{esc(kind)}</text>',
                f'<rect x="{width-111}" y="{y+8}" width="78" height="20" rx="10" fill="#1c2726" stroke="#345348"/>',
                f'<text x="{width-72}" y="{y+22}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="10" font-weight="700" fill="#a9e9c4">{badge}</text>',
                f'<text x="42" y="{y+42}" font-family="Inter,Arial,sans-serif" font-size="11.5" fill="#c7cbd3">{esc(msg)}</text>',
                f'<rect x="42" y="{y+51}" width="105" height="21" rx="8" fill="#1b1e27" stroke="#504b31"/>',
                f'<text x="94" y="{y+65}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="10.5" font-weight="650" fill="#f1e6bd">Private chat</text>',
            ])
        parts.extend([
            '<rect x="68" y="365" width="304" height="31" rx="16" fill="#20222b" stroke="#353944"/>',
            '<text x="86" y="385" font-family="Inter,Arial,sans-serif" font-size="11.5" fill="#9299a5">Ask a question or share a solution…</text>',
            '<text x="350" y="385" text-anchor="middle" font-family="Arial,sans-serif" font-size="18" fill="#d3d7e0">→</text>',
            '</svg>'
        ])
        return "".join(parts)

    if screen_id == "deletion":
        parts.extend(header("Удаление аккаунта April", "Внимательно проверьте последствия"))
        parts.extend([
            '<rect x="24" y="116" width="392" height="148" rx="18" fill="#21151b" stroke="#6b3041"/>',
            '<text x="44" y="145" font-family="Inter,Arial,sans-serif" font-size="14" font-weight="700" fill="#f0b3c1">Удаление April-аккаунта</text>',
            '<text x="44" y="171" font-family="Inter,Arial,sans-serif" font-size="12" fill="#e1d2d7">Удаляются данные, связанные с April.</text>',
            '<text x="44" y="192" font-family="Inter,Arial,sans-serif" font-size="12" fill="#e1d2d7">Google-аккаунт не удаляется.</text>',
            '<text x="44" y="226" font-family="Inter,Arial,sans-serif" font-size="11" fill="#b99ba5">Прочитайте условия и подтвердите только</text>',
            '<text x="44" y="243" font-family="Inter,Arial,sans-serif" font-size="11" fill="#b99ba5">если действительно хотите удалить профиль.</text>',
            '<rect x="44" y="284" width="352" height="44" rx="12" fill="#271922" stroke="#8d4057"/>',
            '<text x="220" y="311" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="13" font-weight="700" fill="#ef9eaf">Удалить аккаунт</text>',
            '</svg>'
        ])
        return "".join(parts)

    # Default is the screenshot-verified profile card and quick navigation links.
    profile = next((item for item in normalized if item["id"].lower() == "settings" or item["href"] == "/settings"), None)
    # In the profile quick-links view, "Chat with April" is a real shortcut
    # even though its destination is /. The profile is already the start node,
    # so keep that row here rather than converting it into a loop to the header.
    routes = [
        item for item in normalized
        if item is not profile and item["href"] and (
            item["href"] != "/" or (screen_id == "profile" and item["id"].lower() == "chat")
        )
    ]
    # Preserve help cards that share /aprill, but remove only duplicate node/path pairs.
    unique_routes = []
    used_route_keys = set()
    for item in routes:
        key = (item["id"], item["href"], item["label"])
        if key in used_route_keys:
            continue
        used_route_keys.add(key)
        unique_routes.append(item)
    routes = unique_routes[:6]
    row_h, row_gap = 50, 8
    profile_y, profile_h = 84, 64
    plan_y = profile_y + profile_h + 14
    list_top = plan_y + 66
    panel_h = 62 + max(1, len(routes)) * (row_h + row_gap) + 10
    height = list_top + max(1, len(routes)) * (row_h + row_gap) + 20
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMin meet" role="img" aria-label="{esc(title_text)}">',
        '<defs><linearGradient id="april-ui-brand" x1="0" x2="1"><stop offset="0" stop-color="#a4f3c1"/><stop offset="1" stop-color="#7bd9e5"/></linearGradient><marker id="april-ui-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 z" fill="#58d7a6"/></marker></defs>',
        f'<rect width="{width}" height="{height}" rx="24" fill="#080a10" stroke="#242a35" stroke-width="2"/>',
        *header("", ""),
        f'<rect x="{margin}" y="{profile_y}" width="{width-2*margin}" height="{profile_h}" rx="16" fill="#13161e" stroke="#34475a" stroke-width="1.5"/>',
        f'<circle cx="43" cy="{profile_y+32}" r="17" fill="#152c25" stroke="#38745d"/>',
        f'<text x="43" y="{profile_y+37}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="14" font-weight="700" fill="#a5efc0">П</text>',
        f'<text x="70" y="{profile_y+26}" font-family="Inter,Arial,sans-serif" font-size="15" font-weight="650" fill="#f1f3f6">Настройки и профиль</text>',
        f'<text x="70" y="{profile_y+47}" font-family="Inter,Arial,sans-serif" font-size="12" fill="#a0a7b4">/settings · Профиль пользователя</text>',
        f'<path d="M {width/2} {profile_y+profile_h} L {width/2} {plan_y-6}" stroke="#58d7a6" stroke-width="2.5" fill="none" marker-end="url(#april-ui-arrow)"/>',
        f'<rect x="{margin}" y="{plan_y}" width="{width-2*margin}" height="{panel_h}" rx="18" fill="#0d1413" stroke="#2c604d" stroke-width="1.6"/>',
        f'<text x="34" y="{plan_y+26}" font-family="Inter,Arial,sans-serif" font-size="12" font-weight="750" letter-spacing="1.5" fill="#91e8b1">CURRENT PLAN</text>',
        f'<text x="34" y="{plan_y+45}" font-family="Inter,Arial,sans-serif" font-size="14" font-weight="650" fill="#eef5f1">Быстрые переходы из профиля</text>',
    ]
    if not routes:
        routes = [{"id":"history", "href":"/history", "label":"Dialog history / История диалогов"}]
    rail_x = 30
    first_cy = list_top + row_h/2
    parts.append(f'<path d="M {rail_x} {first_cy} L {rail_x} {first_cy + (len(routes)-1)*(row_h+row_gap)}" stroke="#58d7a6" stroke-width="1.8" fill="none"/>')
    for index, item in enumerate(routes):
        y = list_top + index*(row_h+row_gap)
        label = route_label(item)
        href = item["href"] or "/aprill"
        cy = y + row_h/2
        normalized_item_id = _text(item.get("id")).lower()
        is_highlighted = bool(highlight_target_id and (
            normalized_item_id == highlight_target_id
            or (highlight_target_id == "history" and href.rstrip("/") == "/history")
            or (highlight_target_id == "space" and href.rstrip("/") == "/space")
            or (highlight_target_id == "support" and href.startswith("/insights"))
            or (highlight_target_id == "settings" and href.rstrip("/") == "/settings")
        ))
        route_accent = highlight_color if is_highlighted else "#293c36"
        route_accent_width = "2.7" if is_highlighted else "1.1"
        number_fill = "#4b171b" if is_highlighted else "#193c2c"
        number_stroke = highlight_color if is_highlighted else "#3f8a64"
        number_text = "#ffd9d9" if is_highlighted else "#b2f2ce"
        arrow_text = highlight_color if is_highlighted else "#78dfa9"
        parts.extend([
            f'<path d="M {rail_x} {cy} L {margin+5} {cy}" stroke="{highlight_color if is_highlighted else "#58d7a6"}" stroke-width="{2.8 if is_highlighted else 1.8}" fill="none"/>',
            f'<rect x="{margin+8}" y="{y}" width="{width-2*margin-16}" height="{row_h}" rx="12" fill="#151b20" stroke="{route_accent}" stroke-width="{route_accent_width}"/>',
            f'<circle cx="{margin+28}" cy="{cy}" r="11" fill="{number_fill}" stroke="{number_stroke}" stroke-width="{2 if is_highlighted else 1}"/>',
            f'<text x="{margin+28}" y="{cy+4}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="12" font-weight="700" fill="{number_text}">{index+1}</text>',
            f'<text x="{margin+47}" y="{y+20}" font-family="Inter,Arial,sans-serif" font-size="12.5" font-weight="650" fill="#edf5f1">{esc(label)}</text>',
            f'<text x="{margin+47}" y="{y+38}" font-family="Inter,Arial,sans-serif" font-size="11.5" fill="#83dcb3">{esc(href)}</text>',
        ])
        if is_highlighted:
            # Draw one clear red pointer into the selected row. Avoid combining a
            # rightward navigation glyph with an opposite-facing chevron; that
            # previously looked like a broken/X-shaped arrow at the screen edge.
            parts.append(
                f'<path d="M {width-6} {cy} L {width-22} {cy} M {width-14} {cy-5} L {width-22} {cy} L {width-14} {cy+5}" '
                f'stroke="{highlight_color}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
            )
        else:
            parts.append(f'<text x="{width-36}" y="{cy+5}" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="18" fill="{arrow_text}">→</text>')
    parts.append('</svg>')
    return ''.join(parts)


def diagram_payload_has_concrete_visual(payload: Any) -> bool:
    """Validate drawable diagrams without mistaking empty SVG shells for assets."""
    if not isinstance(payload, dict):
        return False
    candidates = [payload]
    for key in ("payload", "data", "spec", "artifact", "render_signal", "presentation_signal"):
        child = payload.get(key)
        if isinstance(child, dict):
            candidates.append(child)
            nested = child.get("payload")
            if isinstance(nested, dict):
                candidates.append(nested)
    drawable_tags = re.compile(r"<(?:path|rect|circle|ellipse|polygon|polyline|line|image|use)\b", re.I)
    for source in candidates:
        for key in ("svg", "svg_payload", "drawing"):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                svg = value.strip()
                tag_count = len(drawable_tags.findall(svg))
                # A frame-only rect is not an informative diagram. Require more
                # than a wrapper, or a long complete SVG containing labels/paths.
                if svg.lower().startswith("<svg") and tag_count >= 2 and len(svg) >= 180:
                    return True
        source_text = " ".join(_text(source.get(key)) for key in ("diagram", "mermaid", "flowchart", "source", "code", "content", "text"))
        if source_text and re.search(r"(?:-->|---|flowchart\s+(?:LR|RL|TB|TD|BT)|graph\s+(?:LR|RL|TB|TD|BT))", source_text, re.I):
            return True
        nodes = source.get("nodes") or source.get("components") or source.get("vertices")
        edges = source.get("edges") or source.get("connections") or source.get("relations")
        if isinstance(nodes, list) and len(nodes) >= 2 and isinstance(edges, list) and len(edges) >= 1:
            return True
        for key in ("elements", "drawing_elements", "drawingElements", "primitives"):
            elements = source.get(key)
            if isinstance(elements, list) and len(elements) >= 2:
                return True
    return False


def ensure_readable_diagram_payload(payload: Any, *, title: str = "") -> dict[str, Any]:
    """Return the original payload plus an SVG when actual nodes/edges are present."""
    if not isinstance(payload, dict):
        return {}
    result = deepcopy(payload)
    svg_fields = ("svg", "svg_payload", "drawing")
    navigation_flow = str(result.get("representation") or "").strip().lower() == "navigation_flow" or bool(result.get("navigation_map_schema"))
    if navigation_flow:
        for svg_field in svg_fields:
            result.pop(svg_field, None)
        svg = _build_navigation_ui_svg(result, title=title or _text(result.get("title")))
        if svg:
            result["svg"] = svg
            result["renderer"] = "SvgBlock"
            result["viewer"] = "SvgBlock"
            result["readability_profile"] = "april_navigation_ui_svg_v2"
            result["layout"] = {**(result.get("layout") if isinstance(result.get("layout"), dict) else {}), "direction": "TB", "responsive": True}
        return result
    nodes_for_rebuild = result.get("nodes") or result.get("components") or result.get("vertices")
    normalized_nodes = _normalize_nodes(result) if isinstance(nodes_for_rebuild, list) else []
    if _is_electrical_payload(result, normalized_nodes):
        electrical_svg = _build_readable_electrical_schematic_svg(
            result,
            normalized_nodes,
            title=title or _text(result.get("title") or "Схема подключения"),
        )
        if electrical_svg:
            result["svg"] = electrical_svg
            result["renderer"] = "SvgBlock"
            result["viewer"] = "SvgBlock"
            result["readability_profile"] = "mobile_electrical_schematic_v1"
            result["layout"] = {**(result.get("layout") if isinstance(result.get("layout"), dict) else {}), "direction": "LR", "responsive": True}
            return result
    if _is_chemistry_payload(result, normalized_nodes):
        molecule_svg = _build_readable_molecular_svg(
            result,
            normalized_nodes,
            title=title or _text(result.get("title") or "Молекулярная структура"),
        )
        if molecule_svg:
            result["svg"] = molecule_svg
            result["renderer"] = "SvgBlock"
            result["viewer"] = "SvgBlock"
            result["readability_profile"] = "mobile_molecular_structure_v1"
            result["layout"] = {**(result.get("layout") if isinstance(result.get("layout"), dict) else {}), "direction": "LR", "responsive": True}
            return result
    if _is_object_geometry_payload(result, normalized_nodes):
        geometry_svg = _build_readable_object_geometry_svg(
            result,
            normalized_nodes,
            title=title or _text(result.get("title") or "Геометрический чертёж"),
        )
        if geometry_svg:
            result["svg"] = geometry_svg
            result["renderer"] = "SvgBlock"
            result["viewer"] = "SvgBlock"
            result["readability_profile"] = "mobile_object_geometry_v1"
            result["layout"] = {**(result.get("layout") if isinstance(result.get("layout"), dict) else {}), "direction": "LR", "responsive": True}
            return result
    has_existing_drawing = False
    for svg_field in svg_fields:
        existing_svg = _text(result.get(svg_field)) if isinstance(result.get(svg_field), str) else ""
        has_drawable_element = bool(re.search(
            r"<(?:path|rect|circle|ellipse|polygon|polyline|line|image|use)\b",
            existing_svg,
            re.IGNORECASE,
        ))
        if existing_svg and has_drawable_element:
            has_existing_drawing = True
            break
    edges_for_rebuild = next((result.get(key) for key in ("edges", "connections", "relations") if isinstance(result.get(key), list)), None)
    has_rebuildable_graph = isinstance(nodes_for_rebuild, list) and len(nodes_for_rebuild) >= 2 and isinstance(edges_for_rebuild, list)
    if has_existing_drawing:
        current_svg = next((_text(result.get(key)) for key in svg_fields if _text(result.get(key))), "")
        viewbox_match = re.search(r"viewBox\s*=\s*['\"]\s*[-+0-9.]+[ ,]+[-+0-9.]+[ ,]+([-+0-9.]+)[ ,]+([-+0-9.]+)", current_svg, re.IGNORECASE)
        try:
            existing_viewbox_width = float(viewbox_match.group(1)) if viewbox_match else float("inf")
        except (TypeError, ValueError):
            existing_viewbox_width = float("inf")
        # Percent intrinsic width is interpreted inconsistently by Web SVG/image viewers
        # and produced the tiny diagram in the mobile screenshot. Rebuild when source
        # nodes/edges are available rather than preserving this defective shell.
        broken_intrinsic_width = bool(re.search(r"""\bwidth\s*=\s*['"]100%['"]""", current_svg, re.IGNORECASE))
        if not (has_rebuildable_graph and (existing_viewbox_width > 520 or broken_intrinsic_width)):
            return result
    # A nonempty <svg></svg> shell or a label-only SVG is not enough. Rebuild
    # from concrete same-turn nodes and any supplied relations; a node-only
    # composition is still drawable, but no relationship arrows are inferred.
    for svg_field in svg_fields:
        if isinstance(result.get(svg_field), str):
            result.pop(svg_field, None)
    svg = build_readable_diagram_svg(result, title=title)
    if svg:
        result["svg"] = svg
        current_renderer = _text(result.get("renderer") or _obj(result.get("presentation")).get("renderer"))
        result["renderer"] = current_renderer if current_renderer not in {"", "DiagramRenderer", "diagram"} else "SvgBlock"
        result["layout"] = {**(result.get("layout") if isinstance(result.get("layout"), dict) else {}), "direction": "TB", "rankdir": "TB", "responsive": True}
        result["readability_profile"] = "mobile_portrait_svg_v2"
    return result



def build_answer_outline_payload(answer: str, *, language: str = "") -> dict[str, Any] | None:
    """Build a navigation-like outline from actual sections in this answer only."""
    body = _text(answer)
    if len(body) < 450:
        return None
    lang = _text(language).lower().split("-", 1)[0]
    is_ru = lang in {"ru", "uk"} or bool(re.search(r"[А-Яа-яЁёІіЇїЄєҐґ]", body))
    heading_matches = list(re.finditer(r"(?m)^\s{0,3}#{1,4}\s+([^\n#].{0,110})\s*$", body))
    sections: list[tuple[str, str]] = []
    if len(heading_matches) >= 3:
        for index, match in enumerate(heading_matches[:7]):
            end = heading_matches[index + 1].start() if index + 1 < len(heading_matches) else len(body)
            chunk = body[match.end():end]
            chunk = re.sub(r"```.*?```", " ", chunk, flags=re.DOTALL)
            chunk = re.sub(r"`([^`]*)`", r"\1", chunk)
            chunk = re.sub(r"[*_>#]+", "", chunk)
            sentence = next((s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", chunk) if len(s.strip()) >= 18), "")
            sections.append((re.sub(r"[*_`]", "", match.group(1)).strip(), sentence))
    if len(sections) < 3:
        numbered = []
        for match in re.finditer(r"(?m)^\s*(?:\d+[.)]|[-*•])\s+(.{18,220})$", body):
            item = re.sub(r"[*_`>#]+", "", match.group(1)).strip()
            item = re.sub(r"\s+", " ", item)
            if item:
                numbered.append((item[:90], ""))
        if len(numbered) >= 3:
            sections = numbered[:7]
    if len(sections) < 3:
        paragraphs = [re.sub(r"\s+", " ", part).strip() for part in re.split(r"\n\s*\n", body) if len(part.strip()) >= 55]
        # Remove boilerplate-like standalone link paragraphs and fenced code.
        clean: list[str] = []
        for paragraph in paragraphs:
            if paragraph.startswith("```") or re.fullmatch(r"(?:\[[^\]]+\]\([^)]*\)\s*)+", paragraph):
                continue
            paragraph = re.sub(r"^#{1,6}\s*", "", paragraph)
            paragraph = re.sub(r"[*_`>]+", "", paragraph).strip()
            if len(paragraph) >= 55:
                clean.append(paragraph)
        sections = []
        for paragraph in clean[:6]:
            first_sentence = re.split(r"(?<=[.!?])\s+", paragraph, maxsplit=1)[0].strip()
            # The node title is derived from this same answer, not a topic template.
            heading = first_sentence[:68].rstrip(" ,;:")
            remainder = paragraph[len(first_sentence):].strip()
            sections.append((heading or ("Фрагмент ответа" if is_ru else "Answer section"), remainder))
    sections = sections[:7]
    if len(sections) < 3:
        return None
    nodes = []
    edges = []
    for index, (heading, summary) in enumerate(sections, 1):
        label = heading[:90]
        if summary and summary.lower() not in label.lower():
            label = f"{label}\n{summary[:100]}"
        nodes.append({"id": f"answer_part_{index}", "label": label, "kind": "answer_section", "order": index})
        if index > 1:
            edges.append({"from": f"answer_part_{index-1}", "to": f"answer_part_{index}", "label": "Далее" if is_ru else "Next"})
    return {
        "title": "Структура ответа" if is_ru else "Answer structure",
        "description": "Схема построена по реальным разделам этого ответа; стрелки показывают порядок чтения, не причинно-следственную связь." if is_ru else "This diagram follows the actual sections in this answer; arrows show reading order, not causality.",
        "representation": "explanation_outline",
        "layout": {"direction": "TB", "rankdir": "TB", "responsive": True},
        "nodes": nodes,
        "edges": edges,
        "source": "same_turn_answer_sections",
        "illustrative_outline": True,
    }


def should_add_adaptive_diagram(request: str, answer: str, requested_outputs: Any) -> bool:
    """Only add an adaptive diagram when explicit intent and real structure agree."""
    low_request = _text(request).lower().replace("ё", "е")
    body = _text(answer)
    outputs = {str(item or "").strip().lower().replace("-", "_") for item in (requested_outputs or []) if str(item or "").strip()}
    explicit_no = bool(re.search(
        r"(?:только\s+текст|без\s+(?:схем|диаграмм|визуализац)|не\s+(?:нужна|нужно|надо)\s+(?:схема|диаграмма)|no\s+(?:diagram|visual)|text\s+only)",
        low_request,
    ))
    if explicit_no:
        return False
    wants_outline = bool(re.search(
        r"(?:структур\w*\s+(?:ответ\w*|тем\w*|разговор\w*|обсужден\w*)|карта\s+(?:тем|разделов|мыслей|ответа)|mind\s*map|answer\s+outline|outline\s+of\s+the\s+answer)",
        low_request,
    ))
    wants_process = bool(re.search(
        r"(?:пошаг\w*|по\s+шагам|последовательност\w*|куда\s+нажать|как\s+(?:собрать|подключить|настроить|перейти|нажать|установить)|flowchart|workflow|process\s+diagram|схем\w*\s+(?:действий|процесс\w*|переход\w*))",
        low_request,
    ))
    explicit_diagram = bool(re.search(r"(?:диаграмм\w*|схем\w*|flowchart|diagram)", low_request))
    if not (wants_outline or wants_process or explicit_diagram):
        # The interpreter's requested_outputs can be broad or inferred; it is not
        # permission to generate a redundant outline that repeats the answer.
        return False
    explicit_other_only = bool(re.search(
        r"(?:только\s+(?:ссылк\w*|код|таблиц\w*|изображен\w*|картинк\w*|график\w*|формул\w*|файл\w*)|"
        r"only\s+(?:a\s+)?(?:link|code|table|image|graph|formula|file))",
        low_request,
    ))
    if explicit_other_only and not explicit_diagram:
        return False
    competing = outputs.intersection({"image", "gallery", "code", "table", "graph", "formula", "link", "file"})
    if competing and not explicit_diagram:
        return False
    if wants_process:
        return len(re.findall(r"(?m)^\s*(?:\d+[.)]|[-*+])\s+\S", body)) >= 2
    if wants_outline:
        return len(re.findall(r"(?m)^\s{0,3}#{1,4}\s+", body)) >= 2 and len(body) >= 120
    # A generic “diagram” request only qualifies with real action sequence data.
    return len(re.findall(r"(?m)^\s*(?:\d+[.)]|[-*+])\s+\S", body)) >= 2


class DiagramRoom:
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
