
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
            "graph": False,
            "diagram": False,
            "sources": True,
            "comparison": operation=="compare"
        }


class BiologyReasoningSynthesizer:

    def synthesize(self, semantic, knowledge_context):

        entities = semantic.get("canonical_entities", [])
        concepts = semantic.get("concepts", [])
        nodes = knowledge_context.get("knowledge_nodes", [])
        relations = knowledge_context.get("relations", [])

        parts = []

        if "dna" in entities:
            parts.append(
                "ДНК — молекула, которая хранит наследственную информацию организма. "
                "Она организована в гены и хромосомы и используется клетками для синтеза белков."
            )

        elif "gene" in entities:
            parts.append(
                "Ген представляет собой участок ДНК, содержащий инструкции для синтеза функциональных продуктов клетки."
            )

        elif nodes:
            parts.append(
                f"Обнаружено {len(nodes)} связанных биологических объектов и {len(relations)} связей между ними."
            )

        if concepts:
            parts.append(
                "Ключевые концепции: " + ", ".join(concepts)
            )

        return "\n\n".join(parts) if parts else "Недостаточно знаний для формирования ответа."


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

        knowledge_context = build_biology_knowledge_context(semantic)

        answer = ""
        internal_explanation = ""

        # Scene-first architecture:
        # Biology room provides knowledge payload only.

        result = {
            "answer": answer,
            "internal_explanation": internal_explanation,
            "scene_mode": "knowledge_first",
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

        result = enrich_reasoning_result_with_knowledge(
            result,
            semantic
        )

        return result

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


# =====================================================
# V29 KNOWLEDGE RESOLVER ARCHITECTURE
# =====================================================

class BiologyKnowledgeProvider:
    provider_name = "base"

    def resolve(self, entities, concepts, domains):
        return {
            "knowledge_nodes": [],
            "relations": [],
            "sources": [],
            "graph_data": [],
            "table_data": []
        }


class LocalBiologyProvider(BiologyKnowledgeProvider):

    provider_name = "local_biology"

    def resolve(self, entities, concepts, domains):

        nodes = []
        relations = []

        for entity in entities:

            if entity in BIOLOGY_CONCEPT_LIBRARY:
                nodes.append({
                    "id": entity,
                    **BIOLOGY_CONCEPT_LIBRARY[entity]
                })

            if entity in BIOLOGY_RELATION_LIBRARY:
                relations.append({
                    "entity": entity,
                    "relations": BIOLOGY_RELATION_LIBRARY[entity]
                })

        return {
            "knowledge_nodes": nodes,
            "relations": relations,
            "sources": ["local_library"],
            "graph_data": relations,
            "table_data": nodes
        }


class WikidataBiologyProvider(BiologyKnowledgeProvider):

    provider_name = "wikidata"

    def resolve(self, entities, concepts, domains):

        return {
            "knowledge_nodes": [],
            "relations": [],
            "sources": ["wikidata_placeholder"],
            "graph_data": [],
            "table_data": []
        }


class BiologyKnowledgeResolver:

    def __init__(self):

        self.providers = [
            LocalBiologyProvider(),
            WikidataBiologyProvider()
        ]

    def resolve(self, entities, concepts, domains):

        result = {
            "knowledge_nodes": [],
            "relations": [],
            "sources": [],
            "graph_data": [],
            "table_data": []
        }

        for provider in self.providers:

            provider_result = provider.resolve(
                entities,
                concepts,
                domains
            )

            for key in result:
                result[key].extend(
                    provider_result.get(key, [])
                )

        return result


# =====================================================
# V30 RESOLVER INTEGRATION LAYER
# =====================================================

class BiologyReasoningContextBuilder:

    def build(self, semantic):

        resolver = BiologyKnowledgeResolver()

        knowledge = resolver.resolve(
            entities=semantic.get("canonical_entities", []),
            concepts=semantic.get("concepts", []),
            domains=semantic.get("domains", [])
        )

        return {
            "semantic": semantic,
            "knowledge": knowledge,
            "knowledge_nodes": knowledge.get("knowledge_nodes", []),
            "relations": knowledge.get("relations", []),
            "sources": knowledge.get("sources", []),
            "graph_data": knowledge.get("graph_data", []),
            "table_data": knowledge.get("table_data", [])
        }


# Suggested integration for BiologyReasoningEngine.run():
#
# semantic = BiologySemanticAnalyzer().analyze(topic)
# context = BiologyReasoningContextBuilder().build(semantic)
#
# knowledge_nodes = context["knowledge_nodes"]
# relations = context["relations"]
# sources = context["sources"]
#
# artifact payload should expose:
# knowledge_nodes
# relations
# sources
# graph_data
# table_data
#
# so Scene Builder can consume them directly.


# =====================================================
# V31 RESOLVER -> ENGINE INTEGRATION
# =====================================================

class BiologyKnowledgeSceneAdapter:

    def build_scene_payload(self, context):

        return {
            "knowledge_nodes": context.get("knowledge_nodes", []),
            "relations": context.get("relations", []),
            "sources": context.get("sources", []),
            "graph_data": context.get("graph_data", []),
            "table_data": context.get("table_data", [])
        }


# Integration target for BiologyReasoningEngine.run():
#
# semantic = BiologySemanticAnalyzer().analyze(topic)
#
# context = BiologyReasoningContextBuilder().build(
#     semantic
# )
#
# scene_payload = BiologyKnowledgeSceneAdapter().build_scene_payload(
#     context
# )
#
# return {
#     ...existing fields...,
#     "knowledge_nodes": scene_payload["knowledge_nodes"],
#     "relations": scene_payload["relations"],
#     "knowledge_sources": scene_payload["sources"],
#     "graph_data": scene_payload["graph_data"],
#     "table_data": scene_payload["table_data"]
# }
#
# This preserves compatibility while exposing
# internal and external knowledge providers
# to Executor and Scene Builder.


# =====================================================
# V32 EXTERNAL KNOWLEDGE PROVIDER CONTRACT
# =====================================================

BIOLOGY_EXTERNAL_PROVIDER_CONFIG = {
    "wikidata": {
        "enabled": True,
        "provider": "WikidataBiologyProvider"
    },
    "gene_ontology": {
        "enabled": False,
        "provider": "GeneOntologyProvider"
    },
    "ncbi": {
        "enabled": False,
        "provider": "NCBIProvider"
    },
    "ensembl": {
        "enabled": False,
        "provider": "EnsemblProvider"
    }
}


class GeneOntologyProvider(BiologyKnowledgeProvider):

    provider_name = "gene_ontology"

    def resolve(self, entities, concepts, domains):

        return {
            "knowledge_nodes": [],
            "relations": [],
            "sources": ["gene_ontology_placeholder"],
            "graph_data": [],
            "table_data": []
        }


class NCBIProvider(BiologyKnowledgeProvider):

    provider_name = "ncbi"

    def resolve(self, entities, concepts, domains):

        return {
            "knowledge_nodes": [],
            "relations": [],
            "sources": ["ncbi_placeholder"],
            "graph_data": [],
            "table_data": []
        }


class EnsemblProvider(BiologyKnowledgeProvider):

    provider_name = "ensembl"

    def resolve(self, entities, concepts, domains):

        return {
            "knowledge_nodes": [],
            "relations": [],
            "sources": ["ensembl_placeholder"],
            "graph_data": [],
            "table_data": []
        }


# =====================================================
# V33 DYNAMIC PROVIDER REGISTRY
# =====================================================

class BiologyProviderRegistry:

    def build_providers(self):

        providers = [LocalBiologyProvider()]

        cfg = BIOLOGY_EXTERNAL_PROVIDER_CONFIG

        if cfg.get("wikidata", {}).get("enabled"):
            providers.append(WikidataBiologyProvider())

        if cfg.get("gene_ontology", {}).get("enabled"):
            providers.append(GeneOntologyProvider())

        if cfg.get("ncbi", {}).get("enabled"):
            providers.append(NCBIProvider())

        if cfg.get("ensembl", {}).get("enabled"):
            providers.append(EnsemblProvider())

        return providers


class DynamicBiologyKnowledgeResolver(BiologyKnowledgeResolver):

    def __init__(self):

        registry = BiologyProviderRegistry()
        self.providers = registry.build_providers()
        
        
# Integration target:
#
# resolver = DynamicBiologyKnowledgeResolver()
#
# knowledge = resolver.resolve(
#     entities=semantic["canonical_entities"],
#     concepts=semantic["concepts"],
#     domains=semantic["domains"]
# )
#
# This removes hardcoded providers and routes
# all knowledge access through the provider registry.


# =====================================================
# V34 ACTIVE RESOLVER INTEGRATION PATCH
# =====================================================

def build_biology_knowledge_context(semantic: dict):

    resolver = DynamicBiologyKnowledgeResolver()

    knowledge = resolver.resolve(
        entities=semantic.get("canonical_entities", []),
        concepts=semantic.get("concepts", []),
        domains=semantic.get("domains", [])
    )

    return {
        "knowledge_nodes": knowledge.get("knowledge_nodes", []),
        "relations": knowledge.get("relations", []),
        "knowledge_sources": knowledge.get("sources", []),
        "graph_data": knowledge.get("graph_data", []),
        "table_data": knowledge.get("table_data", [])
    }

# Integration target inside BiologyReasoningEngine.run():
#
# semantic = BiologySemanticAnalyzer().analyze(topic)
# knowledge_context = build_biology_knowledge_context(semantic)
#
# result.update(knowledge_context)
#
# This keeps backward compatibility while exposing
# resolver-driven knowledge to Artifact and Scene layers.


# =====================================================
# V35 SCRUTER VISIBILITY CONTRACT
# =====================================================

def enrich_reasoning_result_with_knowledge(result: dict, semantic: dict):

    try:
        knowledge_context = build_biology_knowledge_context(semantic)

        result.update({
            "knowledge_nodes": knowledge_context.get("knowledge_nodes", []),
            "relations": knowledge_context.get("relations", []),
            "knowledge_sources": knowledge_context.get("knowledge_sources", []),
            "graph_data": knowledge_context.get("graph_data", []),
            "table_data": knowledge_context.get("table_data", []),
            "scene_ready": True,
            "knowledge_provider_mode": "dynamic",
            "artifact_expansion_ready": True,
            "machine_payload": True,
            "scene_contribution_mode": True
        })

    except Exception as e:
        result["knowledge_error"] = str(e)

    return result


# PATCH TARGET INSIDE BiologyReasoningEngine.run():
#
# semantic = BiologySemanticAnalyzer().analyze(topic)
# result = {...existing payload...}
# result = enrich_reasoning_result_with_knowledge(
#     result,
#     semantic
# )
# return result
#
# Scruter / Scene Builder fields:
#   knowledge_nodes
#   relations
#   knowledge_sources
#   graph_data
#   table_data
#   scene_ready


# =====================================================
# V40 CANONICAL RELATION CONTRACT
# =====================================================

def build_canonical_relations():
    canonical = []
    for entity, rels in BIOLOGY_RELATION_LIBRARY.items():
        canonical.append({
            "entity": entity,
            "relations": rels
        })
    return canonical
