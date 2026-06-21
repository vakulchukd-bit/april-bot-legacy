
# =====================================================
# APRIL C_BIOLOGY_ROOM V19
# MERGED UPGRADE (V12 + V17 + V18 + KNOWLEDGE GRAPH)
# =====================================================

from typing import Dict, List, Any
from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact

ROOM_IDENTITY = {
    "specialization": "biological_sciences",
    "knowledge_class": "life_sciences",
    "architecture": "biology_factory_v19"
}

BIOLOGY_ENTITY_REGISTRY = {
    "organism": [], "species": [], "population": [], "ecosystem": [],
    "gene": [], "protein": [], "cell": [], "tissue": [], "organ": [],
    "animal": [], "plant": [], "fungi": [], "bacteria": [], "virus": []
}

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

BIOLOGY_ENTITY_GRAPH = {
    "gene": {
        "domain":"genetics",
        "related_to":["allele","chromosome","genome","mutation"],
        "processes":["replication","transcription","translation"]
    },
    "cell": {
        "domain":"cell_biology",
        "related_to":["protein","tissue","membrane"]
    },
    "species": {
        "domain":"taxonomy",
        "related_to":["population","ecosystem"]
    }
}

BIOLOGY_RELATION_GRAPH = {
    "gene->protein":"encodes",
    "protein->cell":"participates_in",
    "cell->tissue":"forms",
    "population->ecosystem":"inhabits"
}

BIOLOGY_PROCESS_GRAPH = {
    "replication":["dna","polymerase","chromosome"],
    "transcription":["dna","rna"],
    "translation":["rna","protein"]
}

class BiologyOperationDetector:
    def detect(self, text:str)->str:
        t=text.lower()
        if "срав" in t: return "compare"
        if "классиф" in t: return "classify"
        if "граф" in t: return "visualize"
        if "таблиц" in t: return "tabulate"
        if "исслед" in t: return "research"
        return "analyze"

class BiologyEntityRegistry:
    def extract(self, text:str):
        return [x for x in text.lower().split() if len(x)>2]

class BiologyResponsePlanner:
    def build(self, operation:str):
        return {
            "text": True,
            "table": operation in ["compare","tabulate"],
            "graph": operation=="visualize",
            "diagram": operation in ["classify","visualize"],
            "sources": True,
            "comparison": operation=="compare"
        }

class BiologyReasoningEngine:
    def run(self, topic:str):
        operation = BiologyOperationDetector().detect(topic)
        entities = BiologyEntityRegistry().extract(topic)
        planner = BiologyResponsePlanner().build(operation)

        return {
            "operation": operation,
            "entities": entities,
            "domains": list(BIOLOGY_KNOWLEDGE_BASE.keys()),
            "response_plan": planner,
            "knowledge_graph": BIOLOGY_ENTITY_GRAPH,
            "relation_graph": BIOLOGY_RELATION_GRAPH,
            "process_graph": BIOLOGY_PROCESS_GRAPH,
            "table": [],
            "graph": [],
            "diagram": [],
            "sources": [],
            "comparison": {}
        }

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
                "domain":"biology",
                "topic":text,
                "room_identity":ROOM_IDENTITY,
                **result
            }
        )

        return {
            "type":"artifact",
            "artifact":artifact,
            "room":self.name,
            "domain":"biology"
        }

ROOM = BiologyRoom()


# =====================================================
# V20 KNOWLEDGE EXPANSION LAYERS
# =====================================================

BIOLOGY_OBJECT_GRAPH = {
    "human": {
        "type": "species",
        "genus": "Homo",
        "family": "Hominidae",
        "domains": ["genetics", "physiology", "evolution"]
    },
    "lion": {
        "type": "species",
        "genus": "Panthera",
        "family": "Felidae",
        "domains": ["genetics", "ecology", "evolution"]
    },
    "tiger": {
        "type": "species",
        "genus": "Panthera",
        "family": "Felidae",
        "domains": ["genetics", "ecology", "evolution"]
    }
}

BIOLOGY_DOMAIN_GRAPH = {
    "genetics": ["dna", "gene", "chromosome", "genome", "mutation"],
    "ecology": ["population", "ecosystem", "food_chain"],
    "evolution": ["adaptation", "selection", "speciation"],
    "zoology": ["animal", "mammal", "bird", "reptile"],
    "botany": ["plant", "photosynthesis", "root", "leaf"]
}

BIOLOGY_ARTIFACT_LIBRARY = {
    "population_growth": {
        "supports_graph": True,
        "supports_table": True,
        "supports_comparison": True
    },
    "species_comparison": {
        "supports_graph": True,
        "supports_table": True,
        "supports_comparison": True
    }
}

BIOLOGY_RESOURCE_LIBRARY = {
    "genetics": ["NCBI", "Ensembl"],
    "ecology": ["IUCN"],
    "evolution": ["Tree of Life"]
}


# =====================================================
# V21 INTEGRATION LAYER
# =====================================================

def resolve_objects(text: str):
    t = text.lower()
    found = []
    for obj in BIOLOGY_OBJECT_GRAPH.keys():
        if obj in t:
            found.append(obj)
    return found

def resolve_domains(text: str):
    t = text.lower()
    domains = []
    for domain, concepts in BIOLOGY_DOMAIN_GRAPH.items():
        if any(c in t for c in concepts):
            domains.append(domain)
    return domains

# Suggested patch for BiologyReasoningEngine:
# resolved_objects = resolve_objects(topic)
# resolved_domains = resolve_domains(topic)
# available_artifacts = [
#   k for k,v in BIOLOGY_ARTIFACT_LIBRARY.items()
#   if v.get("supports_graph") or v.get("supports_table")
# ]
#
# return {
#   ...existing fields...,
#   "resolved_objects": resolved_objects,
#   "resolved_domains": resolved_domains,
#   "available_artifacts": available_artifacts,
#   "recommended_resources": BIOLOGY_RESOURCE_LIBRARY
# }
