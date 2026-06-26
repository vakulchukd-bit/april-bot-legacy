from typing import Any, Dict
import os

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import (
    create_artifact,
    MachineRequest,
    MachineResponse,
    UniversalArtifactContract,
)

try:
    from Bio import Entrez
    BIOPYTHON_AVAILABLE = True
except ImportError:
    Entrez = None
    BIOPYTHON_AVAILABLE = False

ROOM_ID = "biology"

BIOLOGY_COMPETENCY = {
    "domains": [
        "genetics","molecular_biology","cell_biology",
        "physiology","microbiology","botany",
        "zoology","ecology","evolution",
    ]
}

BIOLOGY_PROVIDERS = [
    {"id":"gene_ontology","name":"Gene Ontology","kind":"ontology","enabled":True},
    {"id":"ncbi","name":"NCBI","kind":"knowledge","enabled":True},
    {"id":"uniprot","name":"UniProt","kind":"protein","enabled":True},
]

NCBI_CONFIG = {
    "tool":"April",
    "email":os.getenv("NCBI_EMAIL",""),
}

def configure_ncbi()->bool:
    if not BIOPYTHON_AVAILABLE:
        return False
    Entrez.tool = NCBI_CONFIG["tool"]
    if NCBI_CONFIG["email"]:
        Entrez.email = NCBI_CONFIG["email"]
    return True

def ncbi_search(term:str, db:str="pubmed", retmax:int=5)->Dict[str,Any]:
    if not term:
        return {}
    if not configure_ncbi():
        return {"provider":"ncbi","status":"biopython_not_installed","results":[]}
    try:
        with Entrez.esearch(db=db, term=term, retmax=retmax) as h:
            data = Entrez.read(h)
        return {"provider":"ncbi","status":"ok","database":db,"ids":data.get("IdList",[])}
    except Exception as exc:
        return {"provider":"ncbi","status":"error","error":str(exc)}

def get_context(machine_request:MachineRequest)->Dict[str,Any]:
    query=""
    if isinstance(machine_request,dict):
        query=str(machine_request.get("query",""))
    return {
        "room":ROOM_ID,
        "competency":BIOLOGY_COMPETENCY,
        "providers":BIOLOGY_PROVIDERS,
        "ncbi":ncbi_search(query),
    }

def build_machine_contribution(machine_request:MachineRequest)->Dict[str,Any]:
    ctx=get_context(machine_request)
    return {
        "room":ROOM_ID,
        "knowledge_context":ctx,
        "prompt_fragments":[
            "Use accepted biological terminology.",
            "Prefer evidence-based biological explanations.",
            "State uncertainty when evidence is limited."
        ],
        "artifact_hints":{
            "text":True,
            "table":True,
            "links":True,
            "graph":False,
        },
    }



class BiologyRoom:
    name = ROOM_ID
    id = ROOM_ID
    domains = BIOLOGY_COMPETENCY["domains"]
    providers = BIOLOGY_PROVIDERS

    def get_context(self, machine_request: MachineRequest):
        return get_context(machine_request)

    def build_machine_contribution(self, machine_request: MachineRequest):
        return build_machine_contribution(machine_request)



    def evaluate(self, machine_request: MachineRequest):
        query = ""
        if isinstance(machine_request, dict):
            query = str(machine_request.get("query","")).lower()
        score = 0.0
        for token in ("днк","dna","ген","gene","клет","биолог","организм","protein","белок","эволюц"):
            if token in query:
                score = max(score,0.95)
        return {
            "room": self.id,
            "score": score,
            "active": score > 0.0,
            "reason": "biology_match" if score>0 else "no_match",
        }

    def execute(self, machine_request: MachineRequest):
        contribution = self.build_machine_contribution(machine_request)
        return create_artifact(
            room=self.id,
            artifact_type="biology",
            payload=contribution,
        )


ROOM = BiologyRoom()

