from typing import Any, Dict
import os

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import (
    create_artifact,
    MachineRequest,
    MachineResponse,
    UniversalArtifactContract,
)

ROOM_ID = "chemistry"

CHEMISTRY_COMPETENCY = {
    "domains": [
        "organic_chemistry",
        "inorganic_chemistry",
        "physical_chemistry",
        "analytical_chemistry",
        "biochemistry",
        "electrochemistry",
        "thermochemistry",
        "chemical_kinetics",
        "equilibrium",
        "materials_science",
    ]
}

CHEMISTRY_PROVIDERS = [
    {"id":"pubchem","name":"PubChem","kind":"compound","enabled":True},
    {"id":"chebi","name":"ChEBI","kind":"ontology","enabled":True},
    {"id":"chemspider","name":"ChemSpider","kind":"compound","enabled":False},
    {"id":"nist","name":"NIST Chemistry","kind":"reference","enabled":True},
]

CHEMISTRY_CONFIG = {
    "tool":"April",
    "email":os.getenv("CHEMISTRY_EMAIL",""),
}

def configure_chemistry()->bool:
    return True

def chemistry_search(term:str)->Dict[str,Any]:
    return {
        "provider":"chemistry",
        "results":[],
    }

def get_context(machine_request:MachineRequest)->Dict[str,Any]:
    query=""
    if isinstance(machine_request,dict):
        query=str(machine_request.get("query",""))
    return {
        "room":ROOM_ID,
        "competency":CHEMISTRY_COMPETENCY,
        "providers":CHEMISTRY_PROVIDERS,
        "chemistry":chemistry_search(query),
    }

def build_machine_contribution(machine_request:MachineRequest)->Dict[str,Any]:
    ctx=get_context(machine_request)
    return {
        "room":ROOM_ID,
        "knowledge_context":ctx,
        "prompt_fragments":[
            "Use accepted chemical terminology.",
            "Prefer evidence-based chemistry.",
            "Prefer IUPAC nomenclature when appropriate.",
            "State uncertainty when evidence is limited."
        ],
        "artifact_hints":{
            "text":True,
            "table":True,
            "links":True,
            "graph":False,
            "formula":True,
        },
    }

class ChemistryRoom:
    name=ROOM_ID
    id=ROOM_ID
    domains=CHEMISTRY_COMPETENCY["domains"]
    providers=CHEMISTRY_PROVIDERS

    def get_context(self,machine_request:MachineRequest):
        return get_context(machine_request)

    def build_machine_contribution(self,machine_request:MachineRequest):
        return build_machine_contribution(machine_request)

    def evaluate(self,machine_request:MachineRequest):
        query=""
        if isinstance(machine_request,dict):
            query=str(machine_request.get("query","")).lower()
        score=0.0
        for token in ("хими","chem","молек","реакц","атом","ион","кислот","щелоч","элемент"):
            if token in query:
                score=max(score,0.95)
        return {
            "room":self.id,
            "score":score,
            "active":score>0.0,
            "reason":"chemistry_match" if score>0 else "no_match",
        }

    def execute(self,machine_request:MachineRequest):
        contribution=self.build_machine_contribution(machine_request)
        return create_artifact(
            room=self.id,
            artifact_type="chemistry",
            payload=contribution,
        )

ROOM=ChemistryRoom()
