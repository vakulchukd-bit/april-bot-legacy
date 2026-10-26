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
        electrical = diagram_type in {"electrical_schematic", "wiring", "circuit", "electrical"} or any(
            _text(n.get("symbol") or n.get("kind")).lower() in {"power_supply","fuse","switch","lamp","motor","resistor","controller"}
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
    edges_raw = payload.get("edges") or payload.get("connections") or payload.get("relations")
    if not isinstance(nodes_raw, list) or len(nodes_raw) < 2 or not isinstance(edges_raw, list) or not edges_raw:
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
        lines = _wrap_lines(label, limit=31, max_lines=4)
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
    if not edges:
        return ""

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
        f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="{height}" style="display:block;width:100%;height:auto;max-width:100%" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMin meet" role="img" aria-label="{esc(title_text)}">',
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
        for line_index, line in enumerate(node["_display_lines"]):
            baseline = y + 28 + line_index * 28
            parts.append(
                f'<text x="{card_x + 22}" y="{baseline}" font-family="Inter,Arial,sans-serif" '
                f'font-size="21" font-weight="{700 if line_index == 0 else 500}" fill="#0f172a">{esc(line)}</text>'
            )
    parts.append("</svg>")
    return "".join(parts)


def ensure_readable_diagram_payload(payload: Any, *, title: str = "") -> dict[str, Any]:
    """Return the original payload plus an SVG when actual nodes/edges are present."""
    if not isinstance(payload, dict):
        return {}
    result = deepcopy(payload)
    svg_fields = ("svg", "svg_payload", "drawing")
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
    nodes_for_rebuild = result.get("nodes") or result.get("components") or result.get("vertices")
    edges_for_rebuild = result.get("edges") or result.get("connections") or result.get("relations")
    has_rebuildable_graph = isinstance(nodes_for_rebuild, list) and len(nodes_for_rebuild) >= 2 and isinstance(edges_for_rebuild, list) and bool(edges_for_rebuild)
    if has_existing_drawing:
        current_svg = next((_text(result.get(key)) for key in svg_fields if _text(result.get(key))), "")
        viewbox_match = re.search(r"viewBox\s*=\s*['\"]\s*[-+0-9.]+[ ,]+[-+0-9.]+[ ,]+([-+0-9.]+)[ ,]+([-+0-9.]+)", current_svg, re.IGNORECASE)
        try:
            existing_viewbox_width = float(viewbox_match.group(1)) if viewbox_match else float("inf")
        except (TypeError, ValueError):
            existing_viewbox_width = float("inf")
        # Preserve an already compact SVG unless actual node/edge data lets us
        # regenerate a wide diagram that would shrink labels on a mobile screen.
        if not (has_rebuildable_graph and existing_viewbox_width > 520):
            return result
    # A nonempty <svg></svg> shell, a label-only SVG, or an over-wide node graph
    # is not enough. Rebuild only from concrete same-turn nodes and edges.
    for svg_field in svg_fields:
        if isinstance(result.get(svg_field), str):
            result.pop(svg_field, None)
    svg = build_readable_diagram_svg(result, title=title)
    if svg:
        result["svg"] = svg
        current_renderer = _text(result.get("renderer") or _obj(result.get("presentation")).get("renderer"))
        result["renderer"] = current_renderer if current_renderer not in {"", "DiagramRenderer", "diagram"} else "SvgBlock"
        result["layout"] = {**(result.get("layout") if isinstance(result.get("layout"), dict) else {}), "direction": "TB", "rankdir": "TB", "responsive": True}
        result["readability_profile"] = "mobile_portrait_svg_v1"
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
    """Add a diagram only when it complements the answer and respects the requested format."""
    low_request = _text(request).lower().replace("ё", "е")
    low_answer = _text(answer).lower()
    outputs = {str(item or "").strip().lower().replace("-", "_") for item in (requested_outputs or []) if str(item or "").strip()}
    explicit_diagram = bool(re.search(r"(?:диаграмм\w*|схем\w*|flowchart|diagram)", low_request)) or "diagram" in outputs
    explicit_no = bool(re.search(
        r"(?:только\s+текст|без\s+(?:схем|диаграмм|визуализац)|не\s+(?:нужна|нужно|надо)\s+(?:схема|диаграмма)|no\s+(?:diagram|visual)|text\s+only)",
        low_request,
    ))
    explicit_other_only = bool(re.search(
        r"(?:только\s+(?:ссылк\w*|код|таблиц\w*|изображен\w*|картинк\w*|график\w*|формул\w*|файл\w*)|"
        r"only\s+(?:a\s+)?(?:link|code|table|image|graph|formula|file))",
        low_request,
    ))
    if explicit_no or (explicit_other_only and not explicit_diagram):
        return False
    # Another renderer explicitly requested by the user wins when no diagram was
    # requested. If the user explicitly asks for both a diagram and (say) a table,
    # an absent/empty diagram must still be recovered instead of silently lost.
    competing = outputs.intersection({"image", "gallery", "code", "table", "graph", "formula", "link", "file"})
    if competing and not explicit_diagram:
        return False
    if len(_text(answer)) < (360 if explicit_diagram else 450):
        return False
    heading_count = len(re.findall(r"(?m)^\s{0,3}#{1,4}\s+", answer))
    paragraph_count = sum(1 for part in re.split(r"\n\s*\n", answer) if len(part.strip()) >= 55)
    numbered_steps = len(re.findall(r"(?m)^\s*\d+[.)]\s+", answer))
    if heading_count >= 3 or paragraph_count >= 4 or numbered_steps >= 5:
        # Don't add a redundant outline if the user already requested a visual
        # and it is not a diagram; that intent was handled above.
        return True
    # No fixed subject/keyword list: eligibility comes from structure of this turn.
    return False


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
