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
    if not isinstance(raw, dict):
        return None

    source = (
        raw.get("from")
        or raw.get("source")
        or raw.get("start")
        or raw.get("source_port")
        or raw.get("from_port")
    )
    target = (
        raw.get("to")
        or raw.get("target")
        or raw.get("end")
        or raw.get("target_port")
        or raw.get("to_port")
    )

    source = _normalize_endpoint(source)
    target = _normalize_endpoint(target)
    if not source or not target:
        return None

    result = {
        "from": source,
        "to": target,
    }

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

    declared_type = (
        semantic.get("diagram_type")
        or semantic.get("representation_subtype")
        or task.get("diagram_type")
        or task.get("format")
        or "flowchart"
    )
    diagram_type = canonical_diagram_type(declared_type)

    raw_nodes = _as_list(task.get("nodes")) or _as_list(semantic.get("nodes"))
    raw_components = _as_list(task.get("components")) or _as_list(semantic.get("components"))
    raw_nodes = raw_nodes or _as_list(semantic.get("entities"))

    nodes = []
    for index, raw in enumerate(raw_nodes + raw_components):
        normalized = _normalize_node(raw, index)
        if normalized:
            nodes.append(normalized)

    # Ordered sequence is structural input. It is not a lexical trigger.
    sequence = _as_list(task.get("sequence")) or _as_list(semantic.get("sequence"))
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

    raw_edges = (
        _as_list(task.get("edges"))
        or _as_list(semantic.get("edges"))
        or _as_list(semantic.get("relations"))
    )
    raw_connections = (
        _as_list(task.get("connections"))
        or _as_list(semantic.get("connections"))
    )

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
    ):
        value = task.get(field)
        if value in (None, [], {}, ""):
            value = semantic.get(field)
        if value not in (None, [], {}, ""):
            optional[field] = value

    ascii_value = task.get("ascii")
    if ascii_value is None:
        ascii_value = task.get("ascii_preview")
    if ascii_value is None:
        ascii_value = semantic.get("ascii")
    if ascii_value is None:
        ascii_value = semantic.get("ascii_preview")
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

    canonical_format = (
        str(task.get("format") or semantic.get("format") or "").strip().lower()
        or diagram_type
    )

    # This is a display recommendation, not a renderer switch.
    # The Web renderer receives the payload unchanged and decides how to draw it.
    presentation = {
        "renderer": "MessageTextBlock",
        "engine": (
            "schematic"
            if diagram_type in {
                "electrical_schematic",
                "circuit_diagram",
                "wiring_diagram",
                "technical_drawing",
                "mechanical_drawing",
                "block_diagram",
                "process_instrumentation",
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
        },
    }

    model = {
        "diagram_type": diagram_type,
        "format": canonical_format,
        "description": task.get("diagram", ""),
        "orientation": task.get("orientation") or semantic.get("orientation"),
        "voltage": task.get("voltage") or semantic.get("voltage"),
        "nodes": nodes,
        "components": nodes,
        "edges": unique_edges,
        "connections": unique_edges,
        "layout": task.get("layout") or semantic.get("layout") or {"direction": "LR"},
        "hierarchy": task.get("hierarchy") or semantic.get("hierarchy") or {},
        "flow": task.get("flow") or semantic.get("flow") or {},
        "mindmap": task.get("mindmap") or semantic.get("mindmap") or {},
        "architecture": task.get("architecture") or semantic.get("architecture") or {},
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
        },
        "technical_symbols_catalog": {
            kind: TECHNICAL_SYMBOLS.get(kind)
            for kind in symbol_kinds
            if kind in TECHNICAL_SYMBOLS
        },
    }

    model.update(optional)
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
        return {
            "layout": "auto",
            "position_source": "payload_when_present",
            "missing_position_policy": "compute_from_topology",
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
            "views": request.get("views") or [],
            "geometry": request.get("geometry") or [],
            "dimensions": request.get("dimensions") or [],
            "annotations": request.get("annotations") or [],
        })


ROOM = DiagramRoom()
