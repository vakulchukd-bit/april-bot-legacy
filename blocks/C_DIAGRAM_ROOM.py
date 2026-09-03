# =====================================================
# APRIL C_DIAGRAM_ROOM
# CANONICAL STRUCTURED SIGNAL ENGINE v4
# =====================================================

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

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
# DIAGRAM KNOWLEDGE BASE
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
    "electrical_schematic": ["electrical", "schematic", "circuit"],
    "circuit_diagram": ["circuit"],
    "wiring_diagram": ["wiring", "connection"],
    "technical_drawing": ["technical", "drawing", "blueprint", "geometry"],
    "mechanical_drawing": ["mechanical"],
    "block_diagram": ["block", "functional"],
    "process_instrumentation": ["process", "instrumentation", "p&id"],
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
    "geometry_diagram": "technical_drawing",
    "mechanical": "mechanical_drawing",
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
    return declared if declared in DIAGRAM_TYPES else "flowchart"


# =====================================================
# TECHNICAL SYMBOL KNOWLEDGE BASE
# Semantic catalog only. Actual drawing remains in Web.
# =====================================================

TECHNICAL_SYMBOLS = {
    "battery": {"category": "electrical", "ports": ["positive", "negative"], "symbol": "battery"},
    "power_positive": {"category": "electrical", "ports": ["terminal"], "symbol": "power_positive"},
    "power_negative": {"category": "electrical", "ports": ["terminal"], "symbol": "power_negative"},
    "source": {"category": "electrical", "ports": ["positive", "negative"], "symbol": "source"},
    "dc_source": {"category": "electrical", "ports": ["positive", "negative"], "symbol": "dc_source"},
    "fuse": {"category": "electrical", "ports": ["input", "output"], "symbol": "fuse"},
    "protection": {"category": "electrical", "ports": ["input", "output"], "symbol": "protection"},
    "switch": {"category": "electrical", "ports": ["input", "output"], "symbol": "switch"},
    "switch_open": {"category": "electrical", "ports": ["input", "output"], "symbol": "switch_open"},
    "dpdt": {"category": "electrical", "ports": ["T1", "T2", "T3", "T4", "T5", "T6"], "symbol": "dpdt"},
    "dpdt_on_on": {"category": "electrical", "ports": ["T1", "T2", "T3", "T4", "T5", "T6"], "symbol": "dpdt_on_on"},
    "dpdt_common": {"category": "electrical", "ports": ["common"], "symbol": "dpdt_common"},
    "dpdt_throw": {"category": "electrical", "ports": ["terminal"], "symbol": "dpdt_throw"},
    "lamp": {"category": "electrical", "ports": ["input", "output"], "symbol": "lamp"},
    "load": {"category": "electrical", "ports": ["input", "output"], "symbol": "load"},
    "motor": {"category": "electrical", "ports": ["A", "B"], "symbol": "motor"},
    "dc_motor": {"category": "electrical", "ports": ["A", "B"], "symbol": "dc_motor"},
    "motor_terminal": {"category": "electrical", "ports": ["terminal"], "symbol": "motor_terminal"},
    "transformer": {"category": "electrical", "ports": ["primary", "secondary"], "symbol": "transformer"},
    "resistor": {"category": "electrical", "ports": ["input", "output"], "symbol": "resistor"},
    "capacitor": {"category": "electrical", "ports": ["positive", "negative"], "symbol": "capacitor"},
    "diode": {"category": "electrical", "ports": ["anode", "cathode"], "symbol": "diode"},
    "relay": {"category": "electrical", "ports": ["coil", "common", "normally_open", "normally_closed"], "symbol": "relay"},
    "ground": {"category": "electrical", "ports": ["terminal"], "symbol": "ground"},
    "earth": {"category": "electrical", "ports": ["terminal"], "symbol": "earth"},
    "sensor": {"category": "technical", "ports": ["input", "output"], "symbol": "sensor"},
    "pump": {"category": "technical", "ports": ["input", "output"], "symbol": "pump"},
    "valve": {"category": "technical", "ports": ["input", "output"], "symbol": "valve"},
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
# NORMALIZATION / EXTRACTION
# =====================================================

_EMPTY = (None, "", [], {})


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _first_present(*values: Any) -> Any:
    for value in values:
        if value not in _EMPTY:
            return value
    return None


def _normalize_node(raw: Any, index: int) -> Optional[Dict[str, Any]]:
    if isinstance(raw, dict):
        node = deepcopy(raw)
        node_id = node.get("id") or node.get("name") or node.get("key") or node.get("label")
        if node_id is None:
            node_id = f"node_{index + 1}"
        node["id"] = str(node_id)
        if node.get("label") is None:
            node["label"] = str(node.get("name") or node["id"])
        return node

    if raw is None:
        return None
    label = str(raw).strip()
    if not label:
        return None
    return {"id": f"node_{index + 1}", "label": label, "kind": "node"}


def _normalize_endpoint(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, dict):
        component = _first_present(
            value.get("component"),
            value.get("node"),
            value.get("id"),
            value.get("owner"),
        )
        terminal = _first_present(
            value.get("terminal"),
            value.get("port"),
            value.get("pin"),
            value.get("contact"),
        )
        if component and terminal:
            return f"{component}.{terminal}"
        if component:
            return str(component)

    return None


def _normalize_connection(raw: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None

    source_raw = _first_present(
        raw.get("from"), raw.get("source"), raw.get("start"),
        raw.get("source_port"), raw.get("from_port"),
    )
    target_raw = _first_present(
        raw.get("to"), raw.get("target"), raw.get("end"),
        raw.get("target_port"), raw.get("to_port"),
    )

    source = _normalize_endpoint(source_raw)
    target = _normalize_endpoint(target_raw)
    if not source or not target:
        return None

    result: Dict[str, Any] = {"from": source, "to": target}

    if isinstance(source_raw, dict):
        result["from_endpoint"] = deepcopy(source_raw)
    if isinstance(target_raw, dict):
        result["to_endpoint"] = deepcopy(target_raw)

    for key in (
        "label", "kind", "type", "state", "style", "wire",
        "waypoints", "points", "route", "geometry", "direction",
    ):
        if key in raw and raw[key] is not None:
            result[key] = deepcopy(raw[key])

    return result


def _parse_structured_object(value: Any) -> Optional[Dict[str, Any]]:
    if isinstance(value, dict):
        return deepcopy(value)
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate or not (candidate.startswith("{") and candidate.endswith("}")):
            return None
        try:
            parsed = json.loads(candidate)
        except (TypeError, ValueError):
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _extract_embedded_visual(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Read already-structured visual blocks supplied by the processor.
    This never interprets free text and never performs keyword detection.
    """
    extracted: Dict[str, Any] = {}

    for key in ("artifact_payload", "payload_contract", "payload", "scene"):
        value = task.get(key)
        parsed = _parse_structured_object(value)
        if parsed:
            extracted = parsed
            break

    render_blocks = _as_list(task.get("render_blocks"))
    if render_blocks:
        extracted["render_blocks"] = deepcopy(render_blocks)

    if isinstance(extracted.get("payload"), dict):
        nested = extracted["payload"]
        merged = dict(nested)
        for key in extracted:
            if key not in {"payload", "render_blocks"}:
                merged[key] = extracted[key]
        extracted = merged

    blocks = _as_list(extracted.get("render_blocks"))
    if blocks:
        for block in blocks:
            if not isinstance(block, dict):
                continue
            block_type = str(block.get("type") or "").strip().lower()
            payload = _parse_structured_object(block.get("payload")) or {}
            role = str(block.get("role") or ((block.get("artifact") or {}).get("role") if isinstance(block.get("artifact"), dict) else "") or "").strip().lower()
            renderer = str(block.get("renderer") or "").strip().lower()

            if block_type == "diagram" and payload:
                extracted = {**extracted, **payload}
                extracted["diagram_block"] = deepcopy(block)
                # Structured metadata says this is an SVG technical drawing; do not infer from prose.
                if role == "technical_drawing" or renderer == "svg":
                    extracted["diagram_type"] = "technical_drawing"
                break

            if block_type == "image" and payload:
                extracted = {**extracted, "svg_payload": deepcopy(payload), "image_block": deepcopy(block)}
                if role == "technical_drawing" and not extracted.get("diagram_type"):
                    extracted["diagram_type"] = "technical_drawing"

    return extracted


def _node_base_id(endpoint: str) -> str:
    return str(endpoint).split(".", 1)[0]


def _endpoint_terminal(endpoint: Any) -> Optional[str]:
    if not isinstance(endpoint, str) or "." not in endpoint:
        return None
    return endpoint.split(".", 1)[1] or None


def _build_signal_integrity(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
    node_ids = {
        str(node.get("id"))
        for node in nodes
        if isinstance(node, dict) and node.get("id") is not None
    }

    terminal_names = set()
    endpoint_refs = []
    unresolved = set()

    for edge in edges:
        for side in ("from", "to"):
            endpoint = edge.get(side)
            if not endpoint:
                continue
            endpoint = str(endpoint)
            endpoint_refs.append(endpoint)
            terminal = _endpoint_terminal(endpoint)
            if terminal:
                terminal_names.add(terminal)
            if _node_base_id(endpoint) not in node_ids:
                unresolved.add(_node_base_id(endpoint))

    return {
        "node_count": len(node_ids),
        "connection_count": len(edges),
        "terminal_qualified_connection_count": sum(
            1 for edge in edges
            if _endpoint_terminal(edge.get("from")) or _endpoint_terminal(edge.get("to"))
        ),
        "terminal_names": sorted(terminal_names),
        "endpoint_references": list(dict.fromkeys(endpoint_refs)),
        "unresolved_node_references": sorted(unresolved),
        "has_topology": bool(nodes and edges),
        "topology_valid": bool(nodes) and not unresolved if edges else bool(nodes),
    }


def _has_structured_visual_data(task: Dict[str, Any]) -> bool:
    keys = (
        "nodes", "components", "edges", "connections", "views", "geometry",
        "dimensions", "annotations", "svg", "svg_payload", "render_blocks",
    )
    return any(task.get(key) not in _EMPTY for key in keys)


# =====================================================
# CANONICAL MACHINE MODEL
# =====================================================


def build_machine_model(task: Dict[str, Any]) -> Dict[str, Any]:
    task = dict(task or {})
    embedded = _extract_embedded_visual(task)
    if embedded:
        merged = dict(embedded)
        merged.update({k: v for k, v in task.items() if v not in _EMPTY})
        task = merged

    semantic = task.get("semantic") or task.get("diagram_semantics") or {}
    if not isinstance(semantic, dict):
        semantic = {}

    declared_type = _first_present(
        semantic.get("diagram_type"),
        semantic.get("representation_subtype"),
        task.get("diagram_type"),
        task.get("representation"),
        task.get("format"),
    )
    diagram_type = canonical_diagram_type(declared_type or "flowchart")

    raw_nodes = _as_list(task.get("nodes")) or _as_list(task.get("components")) or _as_list(semantic.get("nodes")) or _as_list(semantic.get("components"))
    if not raw_nodes:
        raw_nodes = _as_list(semantic.get("entities"))

    nodes: List[Dict[str, Any]] = []
    seen_node_ids = set()
    for index, raw in enumerate(raw_nodes):
        node = _normalize_node(raw, index)
        if not node:
            continue
        node_id = str(node["id"])
        if node_id in seen_node_ids:
            continue
        seen_node_ids.add(node_id)
        nodes.append(node)

    raw_edges = _as_list(task.get("edges")) or _as_list(semantic.get("edges")) or _as_list(semantic.get("relations"))
    raw_connections = _as_list(task.get("connections")) or _as_list(semantic.get("connections"))

    edges: List[Dict[str, Any]] = []
    seen_edges = set()
    for raw in raw_edges + raw_connections:
        edge = _normalize_connection(raw)
        if not edge:
            continue
        key = (
            edge.get("from"), edge.get("to"), edge.get("label"),
            repr(edge.get("wire")), repr(edge.get("waypoints")),
            repr(edge.get("points")),
        )
        if key in seen_edges:
            continue
        seen_edges.add(key)
        edges.append(edge)

    optional_fields = (
        "views", "geometry", "dimensions", "annotations", "legend", "constraints",
        "cross_connections", "operation", "safety", "switch_states", "states",
        "notes", "caption", "metadata", "orientation", "voltage", "direction",
        "layout", "hierarchy", "flow", "mindmap", "architecture",
    )

    optional: Dict[str, Any] = {}
    for field in optional_fields:
        value = _first_present(task.get(field), semantic.get(field))
        if value not in _EMPTY:
            optional[field] = deepcopy(value)

    ascii_value = _first_present(
        task.get("ascii"), task.get("ascii_preview"),
        semantic.get("ascii"), semantic.get("ascii_preview"),
    )
    if ascii_value is not None:
        optional["ascii"] = ascii_value

    svg_payload = task.get("svg_payload") or semantic.get("svg_payload")
    if svg_payload not in _EMPTY:
        optional["svg_payload"] = deepcopy(svg_payload)
    if task.get("svg") not in _EMPTY:
        optional["svg"] = task.get("svg")

    position_count = sum(
        1 for node in nodes
        if node.get("position") is not None or node.get("coordinates") is not None
    )

    symbol_kinds = sorted({
        str(node.get("symbol") or node.get("kind") or node.get("type"))
        for node in nodes
        if node.get("symbol") or node.get("kind") or node.get("type")
    })

    operational_fields = {
        field: value
        for field in (
            "cross_connections", "operation", "safety", "switch_states", "states",
            "notes", "caption", "metadata",
        )
        if (value := _first_present(task.get(field), semantic.get(field))) not in _EMPTY
    }

    # Explicit technical-drawing SVG remains an image payload; do not coerce it into graph nodes.
    has_svg_drawing = bool(
        task.get("svg")
        or isinstance(svg_payload, dict)
        or str(task.get("format") or "").lower() == "svg"
    ) and diagram_type in {"technical_drawing", "mechanical_drawing"}

    if has_svg_drawing:
        primary_visual = "svg_image"
        text_renderer = "Image"
        engine = "svg"
    elif diagram_type in {
        "electrical_schematic",
        "circuit_diagram",
        "wiring_diagram",
        "block_diagram",
        "process_instrumentation",
        "technical_drawing",
        "mechanical_drawing",
    }:
        primary_visual = "structured_scene"
        text_renderer = "MessageTextBlock"
        engine = "schematic"
    else:
        primary_visual = "structured_diagram"
        text_renderer = "MessageTextBlock"
        engine = "diagram"

    integrity = _build_signal_integrity(nodes, edges)

    presentation = {
        "version": "april_diagram_presentation_contract_v1",
        "route": "canonical",
        "renderer": text_renderer,
        "engine": engine,
        "mode": "structured",
        "primary_visual": primary_visual,
        "secondary_visual": "ascii" if "ascii" in optional else None,
        "payload_unchanged": True,
        "preserve_structure": True,
        "text_block_recommendation": {
            "consume_structured_payload_only": True,
            "preferred_sources": [
                "nodes", "components", "edges", "connections",
                "position", "coordinates", "geometry", "views",
                "dimensions", "annotations", "legend", "constraints",
                "cross_connections", "operation", "safety", "states",
            ],
            "primary_renderer_input": "canonical_machine_model",
            "ascii_role": "supplementary" if "ascii" in optional else None,
            "do_not_reconstruct_from_description": True,
            "do_not_infer_components_from_words": True,
            "do_not_convert_schematic_to_graph": True,
        },
        "requirements": {
            "preserve_terminal_endpoints": True,
            "preserve_processor_geometry": True,
            "preserve_connection_metadata": True,
            "use_structured_symbols": True,
            "no_text_keyword_inference": True,
            "no_fallback": True,
            "no_generated_missing_components": True,
            "single_canonical_channel": True,
        },
    }

    model: Dict[str, Any] = {
        "diagram_type": diagram_type,
        "format": str(_first_present(task.get("format"), semantic.get("format"), diagram_type) or diagram_type).strip().lower(),
        "description": str(task.get("diagram") or task.get("description") or ""),
        "orientation": _first_present(task.get("orientation"), semantic.get("orientation")),
        "voltage": _first_present(task.get("voltage"), semantic.get("voltage")),
        "nodes": nodes,
        "components": deepcopy(nodes),
        "edges": edges,
        "connections": deepcopy(edges),
        "layout": _first_present(task.get("layout"), semantic.get("layout")) or {"direction": "LR"},
        "diagram_schema": "april.diagram.canonical.v4",
        "representation": (
            "technical_drawing"
            if has_svg_drawing
            else (
                "schematic"
                if diagram_type in {
                    "electrical_schematic", "circuit_diagram", "wiring_diagram",
                    "technical_drawing", "mechanical_drawing",
                }
                else diagram_type
            )
        ),
        "renderer": text_renderer,
        "viewer": text_renderer,
        "presentation": presentation,
        "signal_integrity": integrity,
        "technical_symbols_catalog": {
            kind: TECHNICAL_SYMBOLS[kind]
            for kind in symbol_kinds
            if kind in TECHNICAL_SYMBOLS
        },
        "available_libraries": DIAGRAM_LIBRARIES,
    }

    model.update(optional)
    model.update(operational_fields)

    # Preserve structured provider SVG/image payload without reinterpreting it.
    if isinstance(task.get("svg_payload"), dict):
        model["svg_payload"] = deepcopy(task["svg_payload"])

    return model


# =====================================================
# ARTIFACT PREPARATION
# =====================================================


def prepare_diagram_artifact(task: Dict[str, Any]) -> Dict[str, Any]:
    model = build_machine_model(task)
    return {
        "artifact_type": "diagram",
        "room": ROOM_ID,
        "diagram_type": model["diagram_type"],
        "machine_model": model,
        "render_ready": bool(model["nodes"] or model["edges"] or model.get("svg") or model.get("svg_payload")),
        "presentation": model["presentation"],
    }


def select_diagram_library(task: Dict[str, Any]) -> Dict[str, Any]:
    semantic = task.get("semantic") or task.get("diagram_semantics") or {}
    dtype = canonical_diagram_type(
        _first_present(
            semantic.get("diagram_type"), semantic.get("representation_subtype"),
            task.get("diagram_type"), task.get("representation"), task.get("format"),
        ) or "flowchart"
    )
    return DIAGRAM_LIBRARY.get(dtype, DIAGRAM_LIBRARY["flowchart"])


# =====================================================
# ROOM
# =====================================================


class DiagramRoom(Room):
    name = "diagram"
    id = ROOM_ID
    domains = DIAGRAM_COMPETENCY["domains"]
    providers = DIAGRAM_PROVIDERS
    room_type = "visual"
    ROOM_ID = ROOM_ID
    ARTIFACT_TYPE = "diagram"
    quality_score = 1.0
    confidence_score = 1.0
    completeness_score = 1.0

    async def handle(self, user_id, text, context, run):
        print("DIAGRAM ROOM HANDLE START")
        context = context if isinstance(context, dict) else {}
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
            "render_blocks": context.get("render_blocks") or [],
            "payload": context.get("payload"),
            "artifact_payload": context.get("artifact_payload"),
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
        if not isinstance(semantic, dict):
            semantic = {}
        return {
            "goal": task.get("goal"),
            "purpose": task.get("purpose"),
            "active_scene": task.get("active_scene"),
            "diagram": task.get("diagram") or task.get("description") or "",
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
            "representation": task.get("representation"),
            "diagram_type": task.get("diagram_type"),
            "views": task.get("views") or semantic.get("views") or [],
            "geometry": task.get("geometry") or semantic.get("geometry") or [],
            "dimensions": task.get("dimensions") or semantic.get("dimensions") or [],
            "annotations": task.get("annotations") or semantic.get("annotations") or [],
            "legend": task.get("legend") or semantic.get("legend") or {},
            "constraints": task.get("constraints") or semantic.get("constraints") or [],
            "ascii": _first_present(task.get("ascii"), semantic.get("ascii")),
            "ascii_preview": _first_present(task.get("ascii_preview"), semantic.get("ascii_preview")),
            "cross_connections": task.get("cross_connections") or semantic.get("cross_connections") or [],
            "operation": task.get("operation") or semantic.get("operation") or [],
            "safety": task.get("safety") or semantic.get("safety") or [],
            "switch_states": task.get("switch_states") or semantic.get("switch_states") or [],
            "states": task.get("states") or semantic.get("states") or [],
            "notes": task.get("notes") or semantic.get("notes") or [],
            "caption": _first_present(task.get("caption"), semantic.get("caption")),
            "metadata": task.get("metadata") or semantic.get("metadata") or {},
            "render_blocks": task.get("render_blocks") or [],
            "payload": task.get("payload"),
            "artifact_payload": task.get("artifact_payload"),
            "svg": task.get("svg"),
            "svg_payload": task.get("svg_payload"),
        }

    # =================================================
    # COMPETENCY BUILDERS
    # =================================================

    def build_nodes(self, description: str) -> List[Dict]:
        return build_machine_model({"diagram": description})["nodes"]

    def build_edges(self, description: str) -> List[Dict]:
        return build_machine_model({"diagram": description})["edges"]

    def build_flow(self, description: str) -> Dict:
        model = build_machine_model({"diagram": description})
        return {
            "start": model["nodes"][0]["id"] if model["nodes"] else None,
            "end": model["nodes"][-1]["id"] if model["nodes"] else None,
            "edges": model["edges"],
        }

    def build_hierarchy(self, description: str) -> Dict:
        return {"root": []}

    def build_mindmap(self, description: str) -> Dict:
        return {"center": "root", "branches": []}

    def build_architecture(self, description: str) -> Dict:
        return {"components": []}

    def build_layout(self, nodes: List[Dict]) -> Dict:
        positioned = sum(
            1 for node in nodes
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
    # VALIDATION / QUALITY
    # =================================================

    def validate_diagram(self, description: str, task: Optional[Dict[str, Any]] = None) -> bool:
        task = task or {}
        return bool((description or "").strip() or _has_structured_visual_data(task) or _extract_embedded_visual(task))

    def calculate_quality(self, description: str, task: Optional[Dict[str, Any]] = None) -> float:
        if task:
            model = build_machine_model(task)
            if model["signal_integrity"]["topology_valid"] or model.get("svg") or model.get("svg_payload"):
                return 1.0
            if description and description.strip():
                return 0.5
            return 0.0
        return 1.0 if description else 0.0

    # =================================================
    # ARTIFACT
    # =================================================

    def build_artifact(self, description: str, task: Optional[Dict[str, Any]] = None):
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
                "knowledge_class": "technical_visual_signal",
            },
            "knowledge_scope": DIAGRAM_COMPETENCY["domains"],
            "capabilities": [
                "normalize_nodes",
                "normalize_connections",
                "preserve_terminals",
                "preserve_geometry",
                "preserve_drawing_metadata",
                "preserve_operational_states",
                "validate_topology",
                "preserve_endpoint_metadata",
                "preserve_svg_payload",
                "technical_symbol_semantics",
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
        if not self.validate_diagram(description, work_order):
            return None
        return self.build_artifact(description, task=work_order)

    def build_machine_contribution(self, task: Dict[str, Any]) -> Dict[str, Any]:
        model = build_machine_model(task)
        model["library"] = select_diagram_library(task)
        return {
            "room": self.ROOM_ID,
            "machine_model": model,
            "artifact": prepare_diagram_artifact(task),
        }

    # =================================================
    # STRUCTURED EVALUATION
    # =================================================

    def evaluate(self, machine_request: Dict[str, Any]):
        request = machine_request if isinstance(machine_request, dict) else {}
        semantic = request.get("semantic") or request.get("diagram_semantics") or {}
        if not isinstance(semantic, dict):
            semantic = {}

        declared = _first_present(
            semantic.get("diagram_type"), semantic.get("representation_subtype"),
            request.get("diagram_type"), request.get("representation"), request.get("format"),
        )
        structured = any(
            request.get(key) not in _EMPTY
            for key in ("nodes", "components", "edges", "connections", "views", "geometry", "render_blocks", "payload")
        )

        if not declared and not structured:
            return {
                "room": self.id,
                "score": 0.0,
                "active": False,
                "reason": "no_structured_diagram_signal",
            }

        dtype = canonical_diagram_type(declared or "flowchart")
        return {
            "room": self.id,
            "score": 1.0 if dtype in DIAGRAM_TYPES else 0.0,
            "active": dtype in DIAGRAM_TYPES,
            "reason": "structured_diagram_signal",
            "diagram_type": dtype,
        }

    def execute(self, machine_request: Dict[str, Any]):
        request = machine_request if isinstance(machine_request, dict) else {}
        return self.process({
            "diagram": request.get("diagram") or request.get("query") or request.get("description", ""),
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
            "representation": request.get("representation"),
            "diagram_type": request.get("diagram_type"),
            "views": request.get("views") or [],
            "geometry": request.get("geometry") or [],
            "dimensions": request.get("dimensions") or [],
            "annotations": request.get("annotations") or [],
            "render_blocks": request.get("render_blocks") or [],
            "payload": request.get("payload"),
            "artifact_payload": request.get("artifact_payload"),
            "svg": request.get("svg"),
            "svg_payload": request.get("svg_payload"),
        })


ROOM = DiagramRoom()
