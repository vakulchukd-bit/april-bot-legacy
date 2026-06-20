# =====================================================
# APRIL C_BIOLOGY_ROOM V10
# ENTITY + TAXONOMY + EVIDENCE + VIEWER PAYLOAD
# =====================================================

from typing import List
from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact

ROOM_IDENTITY = {
    "specialization":"biological_sciences",
    "knowledge_class":"life_sciences",
    "mission":"study living systems, evolution and ecosystems"
}

DOMAIN_KNOWLEDGE = {
    "genetics":["DNA","RNA","Gene","Genome","Chromosome"],
    "cell_biology":["Cell","Nucleus","Mitochondria","Membrane"],
    "evolution":["Selection","Adaptation","Speciation"],
    "ecology":["Population","Community","Ecosystem","Biome"],
    "zoology":["Mammal","Bird","Fish","Reptile"],
    "botany":["Plant","Leaf","Root","Flower"],
    "microbiology":["Bacteria","Virus","Fungi","Archaea"],
    "immunology":["Antibody","Antigen","TCell","BCell"],
    "biochemistry":["Protein","Lipid","Carbohydrate","Enzyme"],
    "physiology":["Respiration","Circulation","NervousSystem"]
}

BIOLOGY_RELATIONS = {
    "gene":"part_of_genome",
    "genome":"stored_in_cell",
    "cell":"part_of_organism",
    "organism":"member_of_population",
    "population":"part_of_ecosystem"
}

TAXONOMY_LEVELS = [
    "domain","kingdom","phylum",
    "class","order","family",
    "genus","species"
]

def detect_operation(text:str)->str:
    t=text.lower()
    if "сравн" in t: return "compare"
    if "классиф" in t: return "classify"
    if "граф" in t: return "graph"
    if "таблиц" in t: return "table"
    if "исслед" in t: return "research"
    return "explain"

def detect_domains(text:str)->List[str]:
    t=text.lower()
    result=[]
    for d, concepts in DOMAIN_KNOWLEDGE.items():
        if any(c.lower() in t for c in concepts):
            result.append(d)
    return result

def extract_entities(text:str)->List[str]:
    return list(dict.fromkeys(text.lower().split()[:50]))

def build_evidence_layer(domains):
    return [
        {
            "domain":d,
            "evidence_type":"scientific_knowledge"
        }
        for d in domains
    ]

def build_taxonomy_payload(topic):
    return {
        "topic":topic,
        "levels":TAXONOMY_LEVELS
    }

def build_graph_payload(topic, entities):
    return {
        "graph_type":"biology_relation_graph",
        "topic":topic,
        "nodes":entities[:20]
    }

def build_viewer_payload(topic, operation):
    return {
        "viewer":"biology_viewer",
        "topic":topic,
        "operation":operation
    }

class BiologyReasoningEngine:

    def run(self, topic:str):

        operation = detect_operation(topic)
        domains = detect_domains(topic)
        entities = extract_entities(topic)

        return {
            "operation":operation,
            "domains":domains,
            "entities":entities,
            "evidence":build_evidence_layer(domains),
            "taxonomy":build_taxonomy_payload(topic),
            "graph":build_graph_payload(topic, entities),
            "viewer_payload":build_viewer_payload(topic, operation),
            "answer":"Biological reasoning completed.",
            "conclusion":"Scientific biological analysis prepared."
        }

class BiologyRoom(Room):

    name="biology"
    room_type="science"

    ROOM_ID="BIOLOGY_ROOM"
    ARTIFACT_TYPE="function"

    async def handle(self, user_id, text, context, run):

        result = BiologyReasoningEngine().run(text)

        artifact = create_artifact(
            artifact_type=self.ARTIFACT_TYPE,
            room_source=self.ROOM_ID,
            data={
                "domain":"biology",
                "topic":text,
                "room_identity":ROOM_IDENTITY,
                **result,
                "artifact_outputs":[
                    "explanation",
                    "comparison",
                    "classification",
                    "research_summary",
                    "taxonomy",
                    "graph",
                    "viewer_payload",
                    "conclusion"
                ]
            }
        )

        return {
            "type":"artifact",
            "artifact":artifact,
            "room":self.name,
            "domain":"biology"
        }

ROOM = BiologyRoom()
