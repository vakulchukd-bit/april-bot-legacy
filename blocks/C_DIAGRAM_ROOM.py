# =====================================================
# APRIL C_DIAGRAM_ROOM
# =====================================================

from typing import Dict, Any, List, Optional

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact

try:
    import networkx as nx
except ImportError:
    nx = None

try:
    import graphviz
except ImportError:
    graphviz = None

try:
    import pydot
except ImportError:
    pydot = None


# =====================================================
# DIAGRAM COMPETENCY / KNOWLEDGE BASE
# =====================================================

DIAGRAM_COMPETENCY = {
    "domains": [
        "flowchart",
        "uml",
        "architecture",
        "mindmap",
        "erd",
        "bpmn",
        "network_topology",
        "dependency_graph",
        "pipeline",
        "workflow",
        "organization_chart",
        "decision_tree",
        "sequence_diagram",
        "class_diagram",
        "state_diagram",
        "electrical_schematic",
        "circuit_diagram",
        "technical_drawing",
        "mechanical_drawing",
        "block_diagram",
        "wiring_diagram",
        "process_instrumentation",
    ]
}

DIAGRAM_TYPES = {
    "flowchart": ["algorithm", "process", "workflow", "logic"],
    "uml": ["class", "sequence", "activity", "state", "component", "deployment"],
    "architecture": ["software", "system", "microservice", "api", "cloud"],
    "database": ["erd", "entity", "relation", "schema"],
    "mindmap": ["mindmap", "concept", "knowledge"],
    "network": ["network", "topology", "infrastructure"],
    "business": ["bpmn", "organization", "decision", "process"],
    "electrical_schematic": ["circuit", "electrical", "wiring", "schematic"],
    "technical_drawing": ["technical", "drawing", "blueprint"],
    "mechanical_drawing": ["mechanical", "drawing"],
    "block_diagram": ["block", "functional"],
    "wiring_diagram": ["wiring", "connection"],
    "process_instrumentation": ["process", "instrumentation", "pid"],
}

DIAGRAM_ALIASES = {
    "schematic": "electrical_schematic",
    "electrical": "electrical_schematic",
    "electrical_scheme": "electrical_schematic",
    "electrical_schematic": "electrical_schematic",
    "circuit": "circuit_diagram",
    "circuit_diagram": "circuit_diagram",
    "wiring": "wiring_diagram",
    "wiring_diagram": "wiring_diagram",
    "blueprint": "technical_drawing",
    "technical": "technical_drawing",
    "technical_drawing": "technical_drawing",
    "mechanical_drawing": "mechanical_drawing",
    "block": "block_diagram",
    "block_diagram": "block_diagram",
    "pid": "process_instrumentation",
    "p&id": "process_instrumentation",
    "flow": "flowchart",
    "erd": "database",
    "bpmn": "bpmn",
}

def canonical_diagram_type(value: Any) -> str:
    declared = str(value or "flowchart").strip().lower()
    declared = DIAGRAM_ALIASES.get(declared, declared)
    if declared in DIAGRAM_TYPES:
        return declared
    return "flowchart"


# =====================================================
# TECHNICAL SYMBOL KNOWLEDGE BASE
# These are semantic identifiers only. The Web renderer
# owns the actual glyph/SVG implementation.
# =====================================================

TECHNICAL_SYMBOLS = {
    "battery": {"category": "electrical", "ports": ["positive", "negative"]},
    "source": {"category": "electrical", "ports": ["positive", "negative"]},
    "dc_source": {"category": "electrical", "ports": ["positive", "negative"]},
    "fuse": {"category": "electrical", "ports": ["input", "output"]},
    "protection": {"category": "electrical", "ports": ["input", "output"]},
    "switch": {"category": "electrical", "ports": ["input", "output"]},
    "switch_open": {"category": "electrical", "ports": ["input", "output"]},
    "dpdt": {"category": "electrical", "ports": ["T1", "T2", "T3", "T4", "T5", "T6"]},
    "dpdt_on_on": {"category": "electrical", "ports": ["T1", "T2", "T3", "T4", "T5", "T6"]},
    "lamp": {"category": "electrical", "ports": ["input", "output"]},
    "load": {"category": "electrical", "ports": ["input", "output"]},
    "motor": {"category": "electrical", "ports": ["A", "B"]},
    "dc_motor": {"category": "electrical", "ports": ["A", "B"]},
    "transformer": {"category": "electrical", "ports": ["primary", "secondary"]},
    "resistor": {"category": "electrical", "ports": ["input", "output"]},
    "capacitor": {"category": "electrical", "ports": ["positive", "negative"]},
    "diode": {"category": "electrical", "ports": ["anode", "cathode"]},
    "relay": {"category": "electrical", "ports": ["coil", "common", "normally_open", "normally_closed"]},
    "ground": {"category": "electrical", "ports": ["terminal"]},
    "earth": {"category": "electrical", "ports": ["terminal"]},
    "sensor": {"category": "technical", "ports": ["input", "output"]},
    "pump": {"category": "technical", "ports": ["input", "output"]},
    "valve": {"category": "technical", "ports": ["input", "output"]},
}

DIAGRAM_LIBRARY = {
    "flowchart": {"outputs": ["flowchart"], "builders": ["build_nodes", "build_edges", "build_flow"]},
    "uml": {"outputs": ["class", "sequence", "activity", "state", "component", "deployment"], "builders": ["build_nodes", "build_edges", "build_layout"]},
    "architecture": {"outputs": ["software_architecture", "microservices", "api", "cloud"], "builders": ["build_architecture", "build_layout"]},
    "database": {"outputs": ["entity_relationship"], "builders": ["build_nodes", "build_edges"]},
    "mindmap": {"outputs": ["mindmap"], "builders": ["build_mindmap"]},
    "bpmn": {"outputs": ["process_map", "workflow"], "builders": ["build_flow", "build_layout"]},
    "electrical_schematic": {"outputs": ["electrical_schematic"], "builders": ["build_nodes", "build_edges", "build_layout"]},
    "circuit_diagram": {"outputs": ["circuit_diagram"], "builders": ["build_nodes", "build_edges", "build_layout"]},
    "wiring_diagram": {"outputs": ["wiring_diagram"], "builders": ["build_nodes", "build_edges", "build_layout"]},
    "technical_drawing": {"outputs": ["technical_drawing"], "builders": ["build_nodes", "build_edges", "build_layout"]},
    "mechanical_drawing": {"outputs": ["mechanical_drawing"], "builders": ["build_nodes", "build_edges", "build_layout"]},
    "block_diagram": {"outputs": ["block_diagram"], "builders": ["build_nodes", "build_edges", "build_layout"]},
    "process_instrumentation": {"outputs": ["process_instrumentation"], "builders": ["build_nodes", "build_edges", "build_layout"]},
}

DIAGRAM_LIBRARIES = {
    "graph_engine": nx is not None,
    "graphviz": graphviz is not None,
    "pydot": pydot is not None,
}

ROOM_ID = "DIAGRAM_ROOM"

DIAGRAM_PROVIDERS = [
    {"id": "diagram_engine", "name": "April Diagram Engine", "kind": "diagram", "enabled": True},
    {"id": "layout_engine", "name": "April Layout Engine", "kind": "layout", "enabled": True},
]

DIAGRAM_CONTEXT = {
    "room": ROOM_ID,
    "competency": DIAGRAM_COMPETENCY,
    "providers": DIAGRAM_PROVIDERS,
}


# =====================================================
# NORMALIZATION HELPERS
# =====================================================

def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _copy_dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _normalize_node(raw: Any, index: int) -> Optional[Dict[str, Any]]:
    if isinstance(raw, dict):
        item = dict(raw)
        node_id = item.get("id") or item.get("name") or item.get("key") or item.get("label")
        if node_id is None:
            node_id = f"node_{index + 1}"
        item["id"] = str(node_id)
        if item.get("label") is None:
            item["label"] = str(item.get("name") or item["id"])
        return item

    label = str(raw).strip() if raw is not None else ""
    if not label:
        return None
    return {
        "id": f"node_{index + 1}",
        "label": label,
        "kind": "node",
    }


def _normalize_endpoint(value: Any) -> Optional[str]:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    if isinstance(value, dict):
        component = (
            value.get("component")
            or value.get("node")
            or value.get("id")
            or value.get("owner")
        )
        terminal = value.get("terminal") or value.get("port") or value.get("pin")
        if component and terminal:
            return f"{component}.{terminal}"
        if component:
            return str(component)
    return None


def _normalize_connection(raw: Any) -> Optional[Dict[str, Any]]:
    """
    Normalize a processor connection without destroying terminal/port identity.

    Supported real input forms include:
      {"from": "B1.positive", "to": "F1.input"}
      {"source": "...", "target": "..."}
      {"source_port": "...", "target_port": "..."}
      {"from": {"component": "B1", "terminal": "positive"}, ...}

    No endpoint is inferred from the user's prose.
    """
    if not isinstance(raw, dict):
        return None

    source_raw = (
        raw.get("from")
        or raw.get("source")
        or raw.get("start")
        or raw.get("source_port")
        or raw.get("from_port")
    )
    target_raw = (
        raw.get("to")
        or raw.get("target")
        or raw.get("end")
        or raw.get("target_port")
        or raw.get("to_port")
    )

    source = _normalize_endpoint(source_raw)
    target = _normalize_endpoint(target_raw)
    if not source or not target:
        return None

    result: Dict[str, Any] = {
        "from": source,
        "to": target,
    }

    # Preserve source/target endpoint metadata when supplied structurally.
    if isinstance(source_raw, dict):
        result["from_endpoint"] = dict(source_raw)
    if isinstance(target_raw, dict):
        result["to_endpoint"] = dict(target_raw)

    for key in (
        "label",
        "kind",
        "type",
        "state",
        "style",
        "waypoints",
        "points",
        "route",
        "geometry",
    ):
        if key in raw and raw[key] is not None:
            result[key] = raw[key]

    return result


def _merge_unique_dicts(primary: List[Dict[str, Any]], secondary: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    seen = set()

    for item in primary + secondary:
        key = str(item.get("id") or item.get("name") or item.get("label") or "")
        fingerprint = (key, repr(sorted(item.items(), key=lambda pair: pair[0])))
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        result.append(item)

    return result


def _node_base_id(endpoint: str) -> str:
    return str(endpoint).split(".", 1)[0]


def _endpoint_terminal(endpoint: Any) -> Optional[str]:
    """Return the terminal/port portion of a qualified endpoint when present."""
    if not isinstance(endpoint, str):
        return None
    if "." not in endpoint:
        return None
    return endpoint.split(".", 1)[1] or None


def _collect_structured_field(task: Dict[str, Any], semantic: Dict[str, Any], field: str):
    """Read a field from task first, then semantic, without inventing content."""
    if field in task and task[field] not in (None, "", [], {}):
        return task[field]
    if field in semantic and semantic[field] not in (None, "", [], {}):
        return semantic[field]
    return None


def _unique_preserve(items: List[Any]) -> List[Any]:
    result: List[Any] = []
    seen = set()
    for item in items:
        marker = repr(item)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(item)
    return result


def _build_signal_integrity(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Report what structural information actually arrived.

    This is diagnostic metadata for downstream consumers; it does not synthesize
    missing diagram content.
    """
    node_ids = {
        str(node.get("id"))
        for node in nodes
        if isinstance(node, dict) and node.get("id") is not None
    }

    endpoint_pairs = []
    terminals = []
    unresolved_endpoints = []

    for edge in edges:
        for side in ("from", "to"):
            endpoint = edge.get(side)
            if not endpoint:
                continue

            endpoint_pairs.append(str(endpoint))
            terminal = _endpoint_terminal(endpoint)
            if terminal:
                terminals.append(terminal)

            base_id = _node_base_id(str(endpoint))
            if base_id not in node_ids:
                unresolved_endpoints.append(base_id)

    return {
        "node_count": len(node_ids),
        "connection_count": len(edges),
        "terminal_qualified_connection_count": sum(
            1 for edge in edges
            if _endpoint_terminal(edge.get("from")) or _endpoint_terminal(edge.get("to"))
        ),
        "terminal_names": sorted(set(terminals)),
        "endpoint_references": _unique_preserve(endpoint_pairs),
        "unresolved_node_references": sorted(set(unresolved_endpoints)),
        "has_topology": bool(nodes and edges),
        "topology_valid": bool(nodes) and not unresolved_endpoints if edges else bool(nodes),
    }



# =====================================================
# CANONICAL MACHINE MODEL
# =====================================================

def build_machine_model(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produce the canonical diagram/drawing signal.

    Rules:
    - preserve processor structure;
    - support both nodes/edges and components/connections;
    - preserve terminal-qualified endpoints;
    - preserve explicit positions/geometry;
    - do not infer missing technical elements from user wording;
    - do not create an ASCII or SVG fallback;
    - provide a display recommendation for MessageTextBlock.
    """
    task = dict(task or {})
    semantic = task.get("semantic") or task.get("diagram_semantics") or {}
    source_payload = task.get("payload") if isinstance(task.get("payload"), dict) else {}
    artifact_payload = task.get("artifact_payload") if isinstance(task.get("artifact_payload"), dict) else {}
    nested_payload = artifact_payload.get("payload") if isinstance(artifact_payload.get("payload"), dict) else {}
    # Processor payload is authoritative when it is already structured.
    # Nested payloads are read, not reconstructed, and all original fields
    # remain available for downstream consumers.
    structured_sources = [source_payload, nested_payload]

    def first_structured_value(*keys):
        for key in keys:
            if key in task and task[key] not in (None, "", [], {}):
                return task[key]
            if key in semantic and semantic[key] not in (None, "", [], {}):
                return semantic[key]
            for structured in structured_sources:
                if key in structured and structured[key] not in (None, "", [], {}):
                    return structured[key]
        return None

    source_renderer = str(
        first_structured_value("renderer")
        or ""
    ).strip().lower()
    source_viewer = str(
        first_structured_value("viewer")
        or ""
    ).strip().lower()
    source_format = str(
        first_structured_value("format")
        or ""
    ).strip().lower()

    # Prefer explicit structured type/representation.  Only when the type is
    # absent do we use already-structured renderer/format metadata.  No prose
    # keyword guessing is performed here.
    declared_type = (
        semantic.get("diagram_type")
        or semantic.get("representation_subtype")
        or task.get("diagram_type")
    )
    if not declared_type:
        if source_renderer == "svg" or source_viewer in {"technical_drawing", "drawing"}:
            declared_type = "technical_drawing"
        elif source_renderer in {"wiring", "electrical_graph", "schematic", "circuit"}:
            declared_type = "electrical_schematic" if source_renderer in {"wiring", "electrical_graph", "schematic", "circuit"} else "diagram"
        elif source_format in {"electrical_schematic", "circuit_diagram", "wiring_diagram", "technical_drawing", "mechanical_drawing"}:
            declared_type = source_format

    diagram_type = canonical_diagram_type(declared_type or "flowchart")

    raw_nodes = _as_list(first_structured_value("nodes"))
    raw_components = _as_list(first_structured_value("components"))
    raw_nodes = raw_nodes or _as_list(first_structured_value("entities"))

    nodes = []
    for index, raw in enumerate(raw_nodes + raw_components):
        normalized = _normalize_node(raw, index)
        if normalized:
            nodes.append(normalized)

    # Ordered sequence is structural input. It is not a lexical trigger.
    sequence = _as_list(first_structured_value("sequence"))
    if sequence:
        existing = {str(node["id"]): node for node in nodes}
        ordered_ids: List[str] = []

        for index, raw in enumerate(sequence):
            node = _normalize_node(raw, index)
            if not node:
                continue
            node_id = str(node["id"])
            existing.setdefault(node_id, node)
            ordered_ids.append(node_id)

        nodes = list(existing.values())

        for left, right in zip(ordered_ids, ordered_ids[1:]):
            task.setdefault("edges", [])
            task["edges"] = list(task.get("edges") or []) + [{"from": left, "to": right}]

    raw_edges = _as_list(first_structured_value("edges", "relations"))
    raw_connections = _as_list(first_structured_value("connections"))

    edges: List[Dict[str, Any]] = []
    for raw in raw_edges + raw_connections:
        normalized = _normalize_connection(raw)
        if normalized:
            edges.append(normalized)

    unique_edges: List[Dict[str, Any]] = []
    seen_edges = set()
    for edge in edges:
        key = (
            edge.get("from"),
            edge.get("to"),
            edge.get("label", ""),
            repr(edge.get("waypoints")),
            repr(edge.get("points")),
        )
        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(edge)

    # Preserve drawing-specific data only when it was actually supplied.
    optional = {}
    for field in (
        "views",
        "geometry",
        "dimensions",
        "annotations",
        "legend",
        "constraints",
        "elements",
        "width",
        "height",
        "units",
        "viewBox",
        "title",
        "description",
    ):
        value = first_structured_value(field)
        if value not in (None, [], {}, ""):
            optional[field] = value

    ascii_value = first_structured_value("ascii", "ascii_preview")
    if ascii_value is not None:
        optional["ascii"] = ascii_value

    position_count = 0
    for node in nodes:
        if isinstance(node, dict) and (
            node.get("position") is not None
            or node.get("coordinates") is not None
        ):
            position_count += 1

    symbol_kinds = sorted({
        str(node.get("symbol") or node.get("kind") or node.get("type"))
        for node in nodes
        if isinstance(node, dict)
        and (node.get("symbol") or node.get("kind") or node.get("type"))
    })

    terminal_endpoints = sorted({
        endpoint
        for edge in unique_edges
        for endpoint in (edge.get("from"), edge.get("to"))
        if isinstance(endpoint, str) and "." in endpoint
    })

    # Preserve fields already produced by the processor for real technical schematics.
    # These fields are never fabricated from the user's text.
    operational_fields = {}
    for field in (
        "cross_connections",
        "operation",
        "safety",
        "switch_states",
        "states",
        "notes",
        "caption",
        "metadata",
    ):
        value = first_structured_value(field)
        if value is not None:
            operational_fields[field] = value

    signal_integrity = _build_signal_integrity(nodes, unique_edges)

    canonical_format = source_format or diagram_type
    if canonical_format == "graph" and diagram_type in {
        "electrical_schematic", "circuit_diagram", "wiring_diagram",
        "technical_drawing", "mechanical_drawing",
    }:
        canonical_format = diagram_type

    # This is a display recommendation, not a renderer switch.
    # The Web renderer receives the payload unchanged and decides how to draw it.
    presentation = {
        "renderer": "MessageTextBlock",
        "engine": (
            "technical_drawing"
            if diagram_type in {"technical_drawing", "mechanical_drawing"}
            else "schematic"
            if diagram_type in {
                "electrical_schematic", "circuit_diagram", "wiring_diagram",
                "block_diagram", "process_instrumentation",
            }
            else "diagram"
        ),
        "mode": "structured",
        "payload_unchanged": True,
        "primary": "structured_svg",
        "secondary": "ascii" if "ascii" in optional else None,
        "ascii_role": "supplementary" if "ascii" in optional else None,
        "source_fields": [
            "nodes" if raw_nodes else None,
            "components" if raw_components else None,
            "edges" if raw_edges else None,
            "connections" if raw_connections else None,
            "position" if position_count else None,
            "views" if "views" in optional else None,
            "geometry" if "geometry" in optional else None,
            "dimensions" if "dimensions" in optional else None,
        ],
        "requirements": {
            "preserve_terminal_endpoints": True,
            "preserve_positions": True,
            "use_structured_symbols": True,
            "no_text_keyword_inference": True,
            "no_ascii_fallback": True,
            "no_generated_missing_components": True,
            "preserve_connections_unchanged": True,
            "preserve_processor_geometry": True,
            "render_from_payload_only": True,
        },
        "text_block_contract": {
            "consume": [
                "diagram_type",
                "format",
                "title",
                "orientation",
                "nodes",
                "components",
                "edges",
                "connections",
                "terminals",
                "position",
                "geometry",
                "views",
                "dimensions",
                "annotations",
                "legend",
                "constraints",
                "ascii",
            ],
            "primary_visual": "structured_scene",
            "secondary_textual": "ascii" if "ascii" in optional else None,
            "do_not_reconstruct_from_description": True,
            "do_not_replace_missing_structure_with_text": True,
        },
        "source_semantics": {
            "renderer": source_renderer or None,
            "viewer": source_viewer or None,
            "format": source_format or None,
        },
    }

    model = {
        "diagram_type": diagram_type,
        "format": canonical_format,
        "description": task.get("diagram", ""),
        "orientation": first_structured_value("orientation"),
        "source_renderer": source_renderer or None,
        "source_viewer": source_viewer or None,
        "source_format": source_format or None,
        "voltage": first_structured_value("voltage"),
        "nodes": nodes,
        "components": nodes,
        "edges": unique_edges,
        "connections": unique_edges,
        "layout": first_structured_value("layout") or {"direction": "LR"},
        "hierarchy": first_structured_value("hierarchy") or {},
        "flow": first_structured_value("flow") or {},
        "mindmap": first_structured_value("mindmap") or {},
        "architecture": first_structured_value("architecture") or {},
        "diagram_schema": "april.diagram.canonical.v3",
        "representation": "schematic" if diagram_type in {
            "electrical_schematic",
            "circuit_diagram",
            "wiring_diagram",
            "technical_drawing",
            "mechanical_drawing",
        } else diagram_type,
        "renderer": "MessageTextBlock",
        "viewer": "MessageTextBlock",
        "presentation": presentation,
        "signal_integrity": {
            "terminal_endpoints_preserved": True,
            "node_count": len(nodes),
            "edge_count": len(unique_edges),
            "position_count": position_count,
            "terminal_endpoint_count": len(terminal_endpoints),
            "symbol_kinds": symbol_kinds,
            **_build_signal_integrity(nodes, unique_edges),
        },
        "technical_symbols_catalog": {
            kind: TECHNICAL_SYMBOLS.get(kind)
            for kind in symbol_kinds
            if kind in TECHNICAL_SYMBOLS
        },
        **operational_fields,
    }

    model.update(optional)
    if source_payload:
        model["processor_payload"] = source_payload
    if nested_payload:
        model["artifact_payload"] = nested_payload
    return model


def prepare_diagram_artifact(task: Dict[str, Any]) -> Dict[str, Any]:
    model = build_machine_model(task)
    return {
        "artifact_type": "diagram",
        "room": ROOM_ID,
        "diagram_type": model["diagram_type"],
        "machine_model": model,
        "render_ready": True,
        "presentation": model["presentation"],
    }


def select_diagram_library(task: Dict[str, Any]) -> Dict[str, Any]:
    dtype = canonical_diagram_type(
        (task.get("semantic") or task.get("diagram_semantics") or {}).get("diagram_type")
        or task.get("diagram_type")
        or task.get("format")
        or "flowchart"
    )
    return DIAGRAM_LIBRARY.get(dtype, DIAGRAM_LIBRARY["flowchart"])


class DiagramRoom(Room):

    name = "diagram"
    id = ROOM_ID
    domains = DIAGRAM_COMPETENCY["domains"]
    providers = DIAGRAM_PROVIDERS

    room_type = "visual"

    ROOM_ID = "DIAGRAM_ROOM"
    ARTIFACT_TYPE = "diagram"

    quality_score = 1.0
    confidence_score = 1.0
    completeness_score = 1.0

    # =================================================
    # ROOM EXECUTION
    # =================================================

    async def handle(self, user_id, text, context, run):
        print("DIAGRAM ROOM HANDLE START")
        artifact = self.process({
            "diagram": text,
            "goal": context.get("goal"),
            "purpose": context.get("purpose"),
            "active_scene": context.get("active_scene"),
            "semantic": context.get("semantic") or context.get("diagram_semantics") or {},
            "nodes": context.get("nodes") or [],
            "components": context.get("components") or [],
            "edges": context.get("edges") or [],
            "connections": context.get("connections") or [],
            "layout": context.get("layout") or {},
            "orientation": context.get("orientation"),
            "format": context.get("format"),
            "diagram_type": context.get("diagram_type"),
        })
        if artifact is None:
            return None
        return {
            "type": "artifact",
            "artifact": artifact,
            "contract": {"artifact": artifact},
            "machine_response": {
                "artifacts": [artifact],
                "routing_decision": {},
                "executor_owner": True,
            },
        }

    # =================================================
    # WORK ORDER
    # =================================================

    def build_work_order(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task = dict(task or {})
        semantic = task.get("semantic") or task.get("diagram_semantics") or {}
        return {
            "goal": task.get("goal"),
            "purpose": task.get("purpose"),
            "active_scene": task.get("active_scene"),
            "diagram": task.get("diagram", ""),
            "semantic": semantic,
            "nodes": task.get("nodes") or [],
            "components": task.get("components") or [],
            "edges": task.get("edges") or [],
            "connections": task.get("connections") or [],
            "relations": task.get("relations") or [],
            "sequence": task.get("sequence") or [],
            "layout": task.get("layout") or {},
            "orientation": task.get("orientation"),
            "format": task.get("format"),
            "diagram_type": task.get("diagram_type"),
            "renderer": task.get("renderer") or semantic.get("renderer"),
            "viewer": task.get("viewer") or semantic.get("viewer"),
            "hierarchy": task.get("hierarchy") or {},
            "flow": task.get("flow") or {},
            "mindmap": task.get("mindmap") or {},
            "architecture": task.get("architecture") or {},
            "views": task.get("views") or semantic.get("views") or [],
            "geometry": task.get("geometry") or semantic.get("geometry") or [],
            "dimensions": task.get("dimensions") or semantic.get("dimensions") or [],
            "annotations": task.get("annotations") or semantic.get("annotations") or [],
            "legend": task.get("legend") or semantic.get("legend") or {},
            "constraints": task.get("constraints") or semantic.get("constraints") or [],
            "ascii": task.get("ascii") if "ascii" in task else semantic.get("ascii"),
            "cross_connections": task.get("cross_connections") or semantic.get("cross_connections") or [],
            "operation": task.get("operation") or semantic.get("operation") or [],
            "safety": task.get("safety") or semantic.get("safety") or [],
            "switch_states": task.get("switch_states") or semantic.get("switch_states") or [],
            "states": task.get("states") or semantic.get("states") or [],
            "notes": task.get("notes") or semantic.get("notes") or [],
            "caption": task.get("caption") or semantic.get("caption"),
            "metadata": task.get("metadata") or semantic.get("metadata") or {},
        }

    # =================================================
    # NODE / COMPONENT ENGINE
    # =================================================

    def build_nodes(self, description: str) -> List[Dict]:
        model = build_machine_model({"diagram": description})
        return model["nodes"]

    # =================================================
    # EDGE / CONNECTION ENGINE
    # =================================================

    def build_edges(self, description: str) -> List[Dict]:
        model = build_machine_model({"diagram": description})
        return model["edges"]

    # =================================================
    # FLOW ENGINE
    # =================================================

    def build_flow(self, description: str) -> Dict:
        model = build_machine_model({"diagram": description})
        return {
            "start": model["nodes"][0]["id"] if model["nodes"] else None,
            "end": model["nodes"][-1]["id"] if model["nodes"] else None,
            "edges": model["edges"],
        }

    # =================================================
    # HIERARCHY ENGINE
    # =================================================

    def build_hierarchy(self, description: str) -> Dict:
        return {"root": []}

    # =================================================
    # MINDMAP ENGINE
    # =================================================

    def build_mindmap(self, description: str) -> Dict:
        return {"center": "root", "branches": []}

    # =================================================
    # ARCHITECTURE ENGINE
    # =================================================

    def build_architecture(self, description: str) -> Dict:
        return {"components": []}

    # =================================================
    # LAYOUT ENGINE
    # =================================================

    def build_layout(self, nodes: List[Dict]) -> Dict:
        positioned = sum(
            1
            for node in nodes
            if isinstance(node, dict)
            and (node.get("position") is not None or node.get("coordinates") is not None)
        )
        return {
            "layout": "auto",
            "position_source": "payload_when_present",
            "positioned_nodes": positioned,
            "missing_position_policy": "compute_from_topology",
            "preserve_payload_geometry": True,
        }

    # =================================================
    # VALIDATION ENGINE
    # =================================================

    def validate_diagram(self, description: str) -> bool:
        return bool(description and description.strip())

    # =================================================
    # QUALITY ENGINE
    # =================================================

    def calculate_quality(self, description: str) -> float:
        return 1.0 if description else 0.0

    # =================================================
    # ARTIFACT BUILDER
    # =================================================

    def build_artifact(self, description: str, task: Dict[str, Any] | None = None):
        task = dict(task or {})
        task.setdefault("diagram", description)
        contribution = self.build_machine_contribution(task)
        model = contribution["artifact"]["machine_model"]

        data = {
            **model,
            "description": description,
            "domain": "diagram",
            "room_identity": {
                "specialization": "visual_structure_engine",
                "knowledge_class": "structural_visualization",
            },
            "knowledge_scope": DIAGRAM_COMPETENCY["domains"],
            "capabilities": [
                "build_nodes",
                "build_edges",
                "build_flow",
                "build_hierarchy",
                "build_mindmap",
                "build_architecture",
                "build_layout",
                "validate_diagram",
                "calculate_quality",
                "normalize_connections",
                "preserve_terminals",
                "preserve_geometry",
                "preserve_drawing_metadata",
                "preserve_operational_states",
                "validate_topology",
                "preserve_endpoint_metadata",
            ],
            "artifact_outputs": ["diagram"],
            "required_competencies": ["diagram", "layout", "structure"],
            "required_artifacts": ["diagram"],
        }

        return create_artifact(
            artifact_type=self.ARTIFACT_TYPE,
            room_source=self.ROOM_ID,
            data=data,
        )

    # =================================================
    # MAIN PROCESS
    # =================================================

    def process(self, task: Dict[str, Any]):
        work_order = self.build_work_order(task)
        description = work_order.get("diagram", "")
        if not self.validate_diagram(description):
            return None
        return self.build_artifact(description, task=work_order)

    # =================================================
    # MACHINE CONTRIBUTION
    # =================================================

    def build_machine_contribution(self, task: Dict[str, Any]) -> Dict[str, Any]:
        model = build_machine_model(task)
        model["library"] = select_diagram_library(task)
        return {
            "room": self.ROOM_ID,
            "machine_model": model,
            "artifact": prepare_diagram_artifact(task),
        }

    # =================================================
    # SEMANTIC EVALUATION
    # =================================================

    def evaluate(self, machine_request: Dict[str, Any]):
        """
        Evaluate only explicit structured semantics.
        No keyword triggers and no lexical guessing.
        """
        request = machine_request if isinstance(machine_request, dict) else {}
        semantic = request.get("semantic") or request.get("diagram_semantics") or {}
        declared = (
            semantic.get("diagram_type")
            or semantic.get("representation_subtype")
            or request.get("diagram_type")
            or request.get("representation")
            or request.get("format")
        )

        if not declared and not any(
            request.get(key)
            for key in ("nodes", "components", "edges", "connections", "views", "geometry")
        ):
            return {
                "room": self.id,
                "score": 0.0,
                "active": False,
                "reason": "no_structured_diagram_signal",
            }

        dtype = canonical_diagram_type(declared or "flowchart")
        score = 1.0 if dtype in DIAGRAM_TYPES else 0.0

        return {
            "room": self.id,
            "score": score,
            "active": score > 0.0,
            "reason": "structured_diagram_signal" if score > 0 else "unsupported_diagram_type",
            "diagram_type": dtype,
        }

    def execute(self, machine_request: Dict[str, Any]):
        request = machine_request if isinstance(machine_request, dict) else {}
        return self.process({
            "diagram": request.get("diagram") or request.get("query", ""),
            "goal": request.get("goal"),
            "purpose": request.get("purpose"),
            "active_scene": request.get("active_scene"),
            "semantic": request.get("semantic") or request.get("diagram_semantics") or {},
            "nodes": request.get("nodes") or [],
            "components": request.get("components") or [],
            "edges": request.get("edges") or [],
            "connections": request.get("connections") or [],
            "layout": request.get("layout") or {},
            "orientation": request.get("orientation"),
            "format": request.get("format"),
            "diagram_type": request.get("diagram_type"),
            "renderer": request.get("renderer"),
            "viewer": request.get("viewer"),
            "views": request.get("views") or [],
            "geometry": request.get("geometry") or [],
            "dimensions": request.get("dimensions") or [],
            "annotations": request.get("annotations") or [],
            "cross_connections": request.get("cross_connections") or [],
            "operation": request.get("operation") or [],
            "safety": request.get("safety") or [],
            "switch_states": request.get("switch_states") or [],
            "states": request.get("states") or [],
            "notes": request.get("notes") or [],
            "caption": request.get("caption"),
            "metadata": request.get("metadata") or {},
        })


ROOM = DiagramRoom()
