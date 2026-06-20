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



# =====================================================
# APRIL V17 MASTER SCIENTIFIC EXTENSIONS
# =====================================================

BIOLOGY_ONTOLOGY_GRAPH = {
    "gene":["transcript"],
    "transcript":["protein"],
    "protein":["pathway"],
    "pathway":["cell_process"],
    "cell_process":["phenotype"],
    "phenotype":["adaptation"]
}

MECHANISM_CHAINS = {
    "cellular_respiration":[
        "glucose",
        "glycolysis",
        "pyruvate",
        "krebs_cycle",
        "electron_transport_chain",
        "oxidative_phosphorylation",
        "ATP"
    ]
}

class BiologyMechanismEngine:

    def explain(self, topic:str):
        t = topic.lower()

        if "атф" in t or "mitochond" in t:
            return MECHANISM_CHAINS["cellular_respiration"]

        return []


class BiologyResearchEngine:

    def build(self, topic:str):
        return {
            "research_summary": f"Scientific review generated for: {topic}",
            "hypothesis": f"Biological hypothesis regarding: {topic}",
            "methods": ["literature_review","comparative_analysis"],
            "results": [],
            "discussion": [],
            "conclusion": []
        }


_original_run = BiologyReasoningEngine.run

def _v17_run(self, topic:str):

    result = _original_run(self, topic)

    result["knowledge_graph"] = BIOLOGY_ONTOLOGY_GRAPH

    result["mechanism_chain"] = (
        BiologyMechanismEngine().explain(topic)
    )

    result["research"] = (
        BiologyResearchEngine().build(topic)
    )

    result["evidence"] = [
        "genetics",
        "molecular_biology",
        "cell_biology",
        "physiology"
    ]

    result["taxonomy"] = {
        "domain":"biology",
        "knowledge_level":"master_degree"
    }

    return result

BiologyReasoningEngine.run = _v17_run



# =====================================================
# APRIL V18 MASTER RESEARCH LAYER
# =====================================================

ADVANCED_DOMAINS = {
    "genomics": {},
    "proteomics": {},
    "transcriptomics": {},
    "epigenetics": {},
    "systems_biology": {},
    "bioinformatics": {},
    "neuroscience": {},
    "immunology": {},
    "biochemistry": {}
}

class BiologyKnowledgeGraphEngine:

    def build_graph(self, topic):
        return {
            "gene":["transcript"],
            "transcript":["protein"],
            "protein":["interaction_network"],
            "interaction_network":["pathway"],
            "pathway":["cellular_response"],
            "cellular_response":["phenotype"]
        }

class BiologyComparisonEngine:

    def compare(self, a, b):
        return {
            "object_a": a,
            "object_b": b,
            "similarities": [],
            "differences": [],
            "scientific_summary": f"Comparison between {a} and {b}"
        }

class BiologyEvidenceEngine:

    def collect(self, topic):
        return {
            "evidence_strength": "medium",
            "evidence_tree": [
                "molecular_level",
                "cellular_level",
                "organism_level",
                "population_level"
            ]
        }

_original_v17_run = BiologyReasoningEngine.run

def _v18_run(self, topic):

    result = _original_v17_run(self, topic)

    result["advanced_domains"] = list(ADVANCED_DOMAINS.keys())

    result["knowledge_graph_v2"] = (
        BiologyKnowledgeGraphEngine().build_graph(topic)
    )

    result["evidence_report"] = (
        BiologyEvidenceEngine().collect(topic)
    )

    result["research_level"] = "master_thesis"

    return result

BiologyReasoningEngine.run = _v18_run
