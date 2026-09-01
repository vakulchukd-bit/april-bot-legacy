# =====================================================
# APRIL C_DIAGRAM_ROOM
# =====================================================

from typing import Dict, Any, List

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
    ]
}


DIAGRAM_TYPES = {
    "flowchart": ["algorithm","process","workflow","logic"],
    "uml": ["class","sequence","activity","state","component","deployment"],
    "architecture": ["software","system","microservice","api","cloud"],
    "database": ["erd","entity","relation","schema"],
    "mindmap": ["mindmap","concept","knowledge"],
    "network": ["network","topology","infrastructure"],
    "business": ["bpmn","organization","decision","process"],
}

def detect_diagram_type(task: Dict[str, Any]) -> str:
    """Resolve diagram kind from explicit processor semantics, never keywords."""
    task = task or {}
    semantic = task.get("semantic") or task.get("diagram_semantics") or {}
    declared = (
        semantic.get("diagram_type")
        or semantic.get("representation_subtype")
        or task.get("diagram_type")
        or "flowchart"
    )
    declared = str(declared).strip().lower()
    aliases = {
        "schematic": "flowchart",
        "blueprint": "architecture",
        "flow": "flowchart",
        "erd": "erd",
        "bpmn": "bpmn",
    }
    return aliases.get(declared, declared if declared in DIAGRAM_TYPES else "flowchart")


DIAGRAM_LIBRARIES = {
    "graph_engine": nx is not None,
    "graphviz": graphviz is not None,
    "pydot": pydot is not None,
}


DIAGRAM_LIBRARY = {
    "flowchart": {
        "outputs": ["flowchart"],
        "builders": ["build_nodes","build_edges","build_flow"],
    },
    "uml": {
        "outputs": ["class","sequence","activity","state","component","deployment"],
        "builders": ["build_nodes","build_edges","build_layout"],
    },
    "architecture": {
        "outputs": ["software_architecture","microservices","api","cloud"],
        "builders": ["build_architecture","build_layout"],
    },
    "erd": {
        "outputs": ["entity_relationship"],
        "builders": ["build_nodes","build_edges"],
    },
    "mindmap": {
        "outputs": ["mindmap"],
        "builders": ["build_mindmap"],
    },
    "bpmn": {
        "outputs": ["process_map","workflow"],
        "builders": ["build_flow","build_layout"],
    },
}

ROOM_ID = "DIAGRAM_ROOM"

DIAGRAM_PROVIDERS = [
    {"id":"diagram_engine","name":"April Diagram Engine","kind":"diagram","enabled":True},
    {"id":"layout_engine","name":"April Layout Engine","kind":"layout","enabled":True},
]


DIAGRAM_CONTEXT = {
    "room": ROOM_ID,
    "competency": DIAGRAM_COMPETENCY,
    "providers": DIAGRAM_PROVIDERS,
}




def build_machine_model(task: Dict[str, Any]) -> Dict[str, Any]:
    """Build a structural diagram model from processor-provided relations."""
    task = dict(task or {})
    semantic = task.get("semantic") or task.get("diagram_semantics") or {}
    raw_nodes = task.get("nodes") or semantic.get("nodes") or semantic.get("entities") or []
    raw_edges = task.get("edges") or semantic.get("edges") or semantic.get("relations") or []
    sequence = task.get("sequence") or semantic.get("sequence") or []

    nodes = []
    for i, node in enumerate(raw_nodes if isinstance(raw_nodes, list) else []):
        if isinstance(node, dict):
            item = dict(node)
            item.setdefault("id", str(item.get("name") or item.get("label") or f"node_{i + 1}"))
            item.setdefault("label", str(item.get("name") or item.get("id") or ""))
            nodes.append(item)
        else:
            label = str(node).strip()
            if label:
                nodes.append({"id": f"node_{i + 1}", "label": label, "type": "node"})

    edges = []
    for edge in raw_edges if isinstance(raw_edges, list) else []:
        if isinstance(edge, dict):
            source = edge.get("from") or edge.get("source") or edge.get("start")
            target = edge.get("to") or edge.get("target") or edge.get("end")
            if source and target:
                edges.append({"from": str(source), "to": str(target), **({"label": str(edge["label"])} if edge.get("label") is not None else {})})

    # A processor may provide an ordered sequence explicitly. This is structural
    # information, not a word trigger, and creates missing nodes/edges only from
    # the declared sequence.
    if isinstance(sequence, (list, tuple)) and sequence:
        ids = []
        existing = {str(n.get("id")): n for n in nodes if isinstance(n, dict)}
        for i, value in enumerate(sequence):
            if isinstance(value, dict):
                node_id = str(value.get("id") or value.get("name") or value.get("label") or f"node_{i + 1}")
                label = str(value.get("label") or value.get("name") or node_id)
                existing.setdefault(node_id, {"id": node_id, "label": label, "type": value.get("type", "node")})
            else:
                label = str(value).strip()
                if not label:
                    continue
                node_id = f"node_{i + 1}"
                existing.setdefault(node_id, {"id": node_id, "label": label, "type": "node"})
            ids.append(node_id)
        nodes = list(existing.values())
        edges.extend({"from": a, "to": b} for a, b in zip(ids, ids[1:]))

    # Deduplicate edges while preserving order.
    seen_edges = set()
    unique_edges = []
    for edge in edges:
        key = (edge.get("from"), edge.get("to"), edge.get("label", ""))
        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(edge)

    return {
        "diagram_type": detect_diagram_type(task),
        "description": task.get("diagram", ""),
        "nodes": nodes,
        "edges": unique_edges,
        "layout": task.get("layout") or semantic.get("layout") or {"direction": "LR"},
        "hierarchy": task.get("hierarchy") or semantic.get("hierarchy") or {},
        "flow": task.get("flow") or semantic.get("flow") or {},
        "mindmap": task.get("mindmap") or semantic.get("mindmap") or {},
        "architecture": task.get("architecture") or semantic.get("architecture") or {},
        "library": select_diagram_library(task),
        "diagram_schema": "april.diagram.canonical.v2",
        "representation": "schematic",
        "renderer": "MessageTextBlock",
    }


def prepare_diagram_artifact(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stage 5:
    Final preparation of the machine artifact before Executor aggregation.
    Rendering remains outside the room.
    """
    model = build_machine_model(task)
    return {
        "artifact_type": "diagram",
        "room": "DIAGRAM_ROOM",
        "diagram_type": model["diagram_type"],
        "machine_model": model,
        "render_ready": True,
    }



def select_diagram_library(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Select the most appropriate professional diagram library
    based on the semantic intent of the machine request.
    """
    dtype = detect_diagram_type(task)
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

    async def handle(
        self,
        user_id,
        text,
        context,
        run
    ):

        print("DIAGRAM ROOM HANDLE START")

        artifact = self.process({

            "diagram": text,

            "goal":
                context.get("goal"),

            "purpose":
                context.get("purpose"),

            "active_scene":
                context.get("active_scene")
        })

        if artifact is None:
            return None

        return {
            "type": "artifact",
            "artifact": artifact,
            "contract": {
                "artifact": artifact
            },
            "machine_response": {
                "artifacts": [artifact],
                "routing_decision": {},
                "executor_owner": True
            }
        }

    # =================================================
    # WORK ORDER
    # =================================================

    def build_work_order(
        self,
        task: Dict[str, Any]
    ) -> Dict[str, Any]:

        return {

            "goal":
                task.get("goal"),

            "purpose":
                task.get("purpose"),

            "active_scene":
                task.get("active_scene"),

            "diagram":
                task.get("diagram", ""),

            "semantic":
                task.get("semantic") or task.get("diagram_semantics") or {},

            "nodes":
                task.get("nodes") or [],

            "edges":
                task.get("edges") or [],

            "relations":
                task.get("relations") or [],

            "sequence":
                task.get("sequence") or [],

            "layout":
                task.get("layout") or {},

            "hierarchy":
                task.get("hierarchy") or {},

            "flow":
                task.get("flow") or {},

            "mindmap":
                task.get("mindmap") or {},

            "architecture":
                task.get("architecture") or {},
        }

    # =================================================
    # NODE ENGINE
    # =================================================

    def build_nodes(self, description: str) -> List[Dict]:
        model = build_machine_model({"diagram": description})
        return model["nodes"]

    # =================================================
    # EDGE ENGINE
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

    def build_hierarchy(
        self,
        description: str
    ) -> Dict:

        return {"root":[]}

    # =================================================
    # MINDMAP ENGINE
    # =================================================

    def build_mindmap(
        self,
        description: str
    ) -> Dict:

        return {"center":"root","branches":[]}

    # =================================================
    # ARCHITECTURE ENGINE
    # =================================================

    def build_architecture(
        self,
        description: str
    ) -> Dict:

        return {"components":[]}

    # =================================================
    # LAYOUT ENGINE
    # =================================================

    def build_layout(
        self,
        nodes: List[Dict]
    ) -> Dict:

        return {

            "layout":
                "auto"
        }

    # =================================================
    # VALIDATION ENGINE
    # =================================================

    def validate_diagram(
        self,
        description: str
    ) -> bool:

        return bool(
            description and description.strip()
        )

    # =================================================
    # QUALITY ENGINE
    # =================================================

    def calculate_quality(
        self,
        description: str
    ) -> float:

        if not description:

            return 0.0

        return 1.0

    # =================================================
    # ARTIFACT BUILDER
    # =================================================

    def build_artifact(
        self,
        description: str,
        task: Dict[str, Any] | None = None
    ):
        task = dict(task or {})
        task.setdefault("diagram", description)
        contribution = self.build_machine_contribution(task)
        return create_artifact(
            artifact_type=self.ARTIFACT_TYPE,
            room_source=self.ROOM_ID,
            data=contribution["artifact"]["machine_model"] | {
                "description": description,
                "representation": "schematic",
                "renderer": "MessageTextBlock",
                "viewer": "MessageTextBlock",
                "presentation": {
                    "renderer": "MessageTextBlock",
                    "engine": "McDowell",
                    "payload_unchanged": True,
                },
                "domain":"diagram",
                "room_identity":{
                    "specialization":"visual_structure_engine",
                    "knowledge_class":"structural_visualization"
                },
                "knowledge_scope": DIAGRAM_COMPETENCY["domains"],
                "capabilities":[
                    "build_nodes","build_edges","build_flow",
                    "build_hierarchy","build_mindmap",
                    "build_architecture","build_layout",
                    "validate_diagram","calculate_quality"
                ],
                "artifact_outputs":["diagram","graph","table"],
                "required_competencies":["diagram","layout","structure"],
                "required_artifacts":["diagram"],
            }
        )

    # =================================================
    # MAIN PROCESS
    # =================================================

    def process(
        self,
        task: Dict[str, Any]
    ):

        work_order = self.build_work_order(
            task
        )

        description = work_order.get(
            "diagram",
            ""
        )

        if not self.validate_diagram(
            description
        ):

            return None

        return self.build_artifact(
            description,
            task=work_order
        )



    def build_machine_contribution(self, task: Dict[str, Any]) -> Dict[str, Any]:
        model = build_machine_model(task)
        model["library"] = select_diagram_library(task)
        return {
            "room": self.ROOM_ID,
            "machine_model": model,
            "artifact": prepare_diagram_artifact(task),
        }


    def evaluate(self, machine_request: Dict[str, Any]):
        query = ""
        if isinstance(machine_request, dict):
            query = (
                str(machine_request.get("query", "")) + " " +
                str(machine_request.get("diagram", ""))
            ).lower()

        score = 0.0
        keywords = (
            "диаграм","схем","uml","flowchart","graph",
            "erd","bpmn","mindmap","mind map",
            "архитектур","блок-схем","sequence",
            "class diagram","state diagram"
        )
        for token in keywords:
            if token in query:
                score = max(score, 0.95)

        return {
            "room": self.id,
            "score": score,
            "active": score > 0.0,
            "reason": "diagram_match" if score > 0 else "no_match",
        }

    def execute(self, machine_request: Dict[str, Any]):
        return self.process({
            "diagram": machine_request.get("diagram")
                       or machine_request.get("query",""),
            "goal": machine_request.get("goal"),
            "purpose": machine_request.get("purpose"),
            "active_scene": machine_request.get("active_scene"),
        })

ROOM = DiagramRoom()
