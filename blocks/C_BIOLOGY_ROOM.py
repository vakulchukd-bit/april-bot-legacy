
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

        resolved_objects = resolve_objects(topic)
        resolved_domains = resolve_domains(topic)

        available_artifacts = list(
            BIOLOGY_ARTIFACT_LIBRARY.keys()
        ) if 'BIOLOGY_ARTIFACT_LIBRARY' in globals() else []

        semantic = BiologySemanticAnalyzer().analyze(topic)

        knowledge_packet = BiologyKnowledgeEngine().build_packet(semantic)
        explanation = BiologyExplanationEngine().explain(semantic)

        answer = knowledge_packet.get(
            "summary",
            explanation
        )

        if explanation and explanation not in answer:
            answer = f"{answer}\n\n{explanation}"


        return {
            "answer": answer,
            "operation": operation,
            "entities": entities,
            "domains": list(BIOLOGY_KNOWLEDGE_BASE.keys()),
            "resolved_objects": resolved_objects,
            "resolved_domains": resolved_domains,
            "available_artifacts": available_artifacts,
            "recommended_resources": globals().get('BIOLOGY_RESOURCE_LIBRARY', {}),
            "semantic": semantic,
            "intent": semantic["intent"],
            "canonical_entities": semantic["canonical_entities"],
            "concepts": semantic["concepts"],

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


# =====================================================
# V23 CANONICAL ENTITY RESOLUTION LAYER
# =====================================================

BIOLOGY_CANONICAL_ENTITIES = {
    "tiger": ["tiger", "tigers", "тигр", "тигры", "тигра", "тигров"],
    "lion": ["lion", "lions", "лев", "львы", "льва", "львов"],
    "human": ["human", "humans", "человек", "люди", "человека"],
    "dna": ["dna", "днк"],
    "gene": ["gene", "ген", "гены", "генов"],
    "photosynthesis": ["photosynthesis", "фотосинтез"]
}

def resolve_canonical_entities(text:str):
    t = text.lower()
    found = []
    for canonical, aliases in BIOLOGY_CANONICAL_ENTITIES.items():
        if any(alias in t for alias in aliases):
            found.append(canonical)
    return found

# Integration note for BiologyReasoningEngine.run():
# canonical_entities = resolve_canonical_entities(topic)
# answer generation should prefer canonical_entities over raw words.


# =====================================================
# V24 SEMANTIC REASONING LAYER
# =====================================================

class BiologySemanticAnalyzer:

    def analyze(self, text:str):

        t = text.lower()

        intent = "explain"

        if "срав" in t:
            intent = "compare"
        elif "покажи" in t or "граф" in t:
            intent = "visualize"
        elif "таблиц" in t:
            intent = "tabulate"
        elif "исслед" in t:
            intent = "research"

        canonical_entities = resolve_canonical_entities(text)

        concepts = []
        domains = []

        for entity in canonical_entities:

            if entity == "dna":
                concepts.append("genetic_information")
                domains.append("genetics")

            elif entity == "gene":
                concepts.append("inheritance")
                domains.append("genetics")

            elif entity == "photosynthesis":
                concepts.append("energy_conversion")
                domains.append("botany")

            elif entity in ["tiger", "lion", "human"]:
                concepts.append("organism")
                domains.append("zoology")

        return {
            "intent": intent,
            "canonical_entities": canonical_entities,
            "concepts": list(set(concepts)),
            "domains": list(set(domains))
        }

# Integration target:
#
# semantic = BiologySemanticAnalyzer().analyze(topic)
#
# return {
#     ...
#     "semantic": semantic,
#     "intent": semantic["intent"],
#     "canonical_entities": semantic["canonical_entities"],
#     "concepts": semantic["concepts"]
# }


# =====================================================
# V26 BIOLOGY KNOWLEDGE ENGINE
# =====================================================

BIOLOGY_KNOWLEDGE_PACKETS = {
    "human_dna": {
        "summary": "ДНК человека содержит наследственную информацию организма. Она организована в хромосомы и кодирует работу клеток, тканей и органов.",
        "domains": ["genetics"],
        "concepts": ["genetic_information", "inheritance"]
    },
    "tiger_dna": {
        "summary": "ДНК тигра хранит генетическую информацию вида Panthera tigris и используется для изучения эволюции, популяций и сохранения вида.",
        "domains": ["genetics", "zoology"],
        "concepts": ["genetic_information", "species"]
    },
    "photosynthesis": {
        "summary": "Фотосинтез — процесс преобразования световой энергии в химическую энергию с образованием органических веществ.",
        "domains": ["botany"],
        "concepts": ["energy_conversion"]
    }
}

class BiologyKnowledgeEngine:

    def build_packet(self, semantic: dict):

        entities = semantic.get("canonical_entities", [])

        if "human" in entities and "dna" in entities:
            return BIOLOGY_KNOWLEDGE_PACKETS["human_dna"]

        if "tiger" in entities and "dna" in entities:
            return BIOLOGY_KNOWLEDGE_PACKETS["tiger_dna"]

        if "photosynthesis" in entities:
            return BIOLOGY_KNOWLEDGE_PACKETS["photosynthesis"]

        return {
            "summary": "Биологическая тема распознана. Требуется углублённый анализ предметной области.",
            "domains": semantic.get("domains", []),
            "concepts": semantic.get("concepts", [])
        }


# =====================================================
# V27 CONCEPT + EXPLANATION ENGINE
# =====================================================

BIOLOGY_CONCEPT_LIBRARY = {
    "dna": {
        "type": "molecule",
        "functions": [
            "inheritance",
            "genome_storage",
            "protein_synthesis"
        ]
    },
    "gene": {
        "type": "genetic_unit",
        "functions": [
            "trait_encoding",
            "inheritance"
        ]
    },
    "photosynthesis": {
        "type": "biological_process",
        "functions": [
            "energy_conversion",
            "glucose_production",
            "oxygen_release"
        ]
    }
}

BIOLOGY_RELATION_LIBRARY = {
    "dna": ["gene", "chromosome", "cell"],
    "gene": ["dna", "protein"],
    "photosynthesis": ["plant", "chlorophyll", "sunlight"]
}

class BiologyExplanationEngine:

    def explain(self, semantic: dict):

        entities = semantic.get("canonical_entities", [])
        concepts = semantic.get("concepts", [])

        explanation_parts = []

        for entity in entities:

            if entity in BIOLOGY_CONCEPT_LIBRARY:

                node = BIOLOGY_CONCEPT_LIBRARY[entity]

                explanation_parts.append(
                    f"{entity} является объектом типа "
                    f"{node.get('type')}."
                )

                funcs = node.get("functions", [])
                if funcs:
                    explanation_parts.append(
                        "Основные функции: " +
                        ", ".join(funcs)
                    )

        if concepts:
            explanation_parts.append(
                "Связанные концепции: " +
                ", ".join(concepts)
            )

        if not explanation_parts:
            explanation_parts.append(
                "Биологическая тема распознана и подготовлена "
                "для дальнейшего анализа знаний."
            )

        return " ".join(explanation_parts)
