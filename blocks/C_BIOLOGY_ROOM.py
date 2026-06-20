# =====================================================
# APRIL C_BIOLOGY_ROOM V12
# BIOLOGY FACTORY FOUNDATION
# =====================================================

from typing import Dict, List, Any
from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact

ROOM_IDENTITY = {
    "specialization": "biological_sciences",
    "knowledge_class": "life_sciences",
    "architecture": "biology_factory_v12"
}

# -----------------------------------------------------
# ENTITY REGISTRY
# -----------------------------------------------------

BIOLOGY_ENTITY_REGISTRY = {
    "organism": [],
    "species": [],
    "population": [],
    "ecosystem": [],
    "gene": [],
    "protein": [],
    "cell": [],
    "tissue": [],
    "organ": [],
    "animal": [],
    "plant": [],
    "fungi": [],
    "bacteria": [],
    "virus": []
}

# -----------------------------------------------------
# CONCEPT GRAPH
# -----------------------------------------------------

BIOLOGY_CONCEPT_GRAPH = {
    "gene": ["protein"],
    "protein": ["cell"],
    "cell": ["tissue"],
    "tissue": ["organ"],
    "organ": ["organism"],
    "organism": ["population"],
    "population": ["species"],
    "species": ["ecosystem"]
}

# -----------------------------------------------------
# KNOWLEDGE DOMAINS
# -----------------------------------------------------

BIOLOGY_KNOWLEDGE_BASE = {
    "genetics": {},
    "molecular_biology": {},
    "cell_biology": {},
    "anatomy": {},
    "physiology": {},
    "biochemistry": {},
    "immunology": {},
    "microbiology": {},
    "zoology": {},
    "botany": {},
    "ecology": {},
    "evolution": {},
    "taxonomy": {},
    "population_biology": {}
}

# -----------------------------------------------------
# OPERATION DETECTOR
# -----------------------------------------------------

class BiologyOperationDetector:

    def detect(self, text: str) -> str:

        t = text.lower()

        if "срав" in t:
            return "compare"

        if "классиф" in t:
            return "classify"

        if "граф" in t:
            return "visualize"

        if "таблиц" in t:
            return "tabulate"

        if "исслед" in t:
            return "research"

        return "analyze"

# -----------------------------------------------------
# ENTITY EXTRACTION
# -----------------------------------------------------

class BiologyEntityRegistry:

    def extract(self, text: str) -> List[str]:
        return [x for x in text.lower().split() if len(x) > 2]

# -----------------------------------------------------
# RESPONSE PLANNER
# -----------------------------------------------------

class BiologyResponsePlanner:

    def build(self, operation: str) -> Dict[str, Any]:

        return {
            "text": True,
            "table": operation in ["compare", "tabulate"],
            "graph": operation == "visualize",
            "diagram": operation in ["classify", "visualize"],
            "sources": True,
            "comparison": operation == "compare"
        }

# -----------------------------------------------------
# REASONING ENGINE
# -----------------------------------------------------

class BiologyReasoningEngine:

    def run(self, topic: str):

        operation = BiologyOperationDetector().detect(topic)

        entities = BiologyEntityRegistry().extract(topic)

        planner = BiologyResponsePlanner().build(operation)

        return {
            "operation": operation,
            "entities": entities,
            "domains": list(BIOLOGY_KNOWLEDGE_BASE.keys()),
            "answer": (
                "Биологический запрос обработан через "
                "Biology Factory Foundation. "
                "Определены сущности, операция и план артефактов."
            ),
            "response_plan": planner,
            "table": [],
            "graph": [],
            "diagram": [],
            "sources": [],
            "comparison": {}
        }

# -----------------------------------------------------
# ROOM
# -----------------------------------------------------

class BiologyRoom(Room):

    name = "biology"
    room_type = "science"

    ROOM_ID = "BIOLOGY_ROOM"

    ARTIFACT_TYPE = "function"

    async def handle(self, user_id, text, context, run):

        result = BiologyReasoningEngine().run(text)

        artifact = create_artifact(
            artifact_type=self.ARTIFACT_TYPE,
            room_source=self.ROOM_ID,
            data={
                "domain": "biology",
                "topic": text,
                "room_identity": ROOM_IDENTITY,
                **result
            }
        )

        return {
            "type": "artifact",
            "artifact": artifact,
            "room": self.name,
            "domain": "biology"
        }

ROOM = BiologyRoom()
