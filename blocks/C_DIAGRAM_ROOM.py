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
    text = str(task.get("diagram","")).lower()
    for dtype, terms in DIAGRAM_TYPES.items():
        if any(t in text for t in terms):
            return dtype
    return "flowchart"



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
    """
    Stage 4:
    Builds the internal machine representation of the future diagram.
    Rendering is intentionally NOT performed here.
    """
    work_order = {
        "diagram_type": detect_diagram_type(task),
        "description": task.get("diagram",""),
        "nodes": [],
        "edges": [],
        "layout": "auto",
        "hierarchy": {},
        "flow": {},
        "mindmap": {},
        "architecture": {},
        "library": select_diagram_library(task),
    }
    return work_order



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

        return {

            "type": "text",

            "data":
                "DIAGRAM ROOM ACTIVE"
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
                task.get("diagram", "")
        }

    # =================================================
    # NODE ENGINE
    # =================================================

    def build_nodes(
        self,
        description: str
    ) -> List[Dict]:

        return [{"id":"root","label":description[:80] or "Diagram","type":"node"}]

    # =================================================
    # EDGE ENGINE
    # =================================================

    def build_edges(
        self,
        description: str
    ) -> List[Dict]:

        return []

    # =================================================
    # FLOW ENGINE
    # =================================================

    def build_flow(
        self,
        description: str
    ) -> Dict:

        return {"start":"root","end":"root"}

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
        description: str
    ):
        task = {"diagram": description}
        contribution = self.build_machine_contribution(task)
        return create_artifact(
            artifact_type=self.ARTIFACT_TYPE,
            room_source=self.ROOM_ID,
            data=contribution["artifact"]["machine_model"] | {
                "description": description,
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
            description
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
