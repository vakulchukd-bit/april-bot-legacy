# =====================================================
# APRIL C_IT_ROOM
# =====================================================

from typing import Any, Dict

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import (
    create_artifact,
    MachineRequest,
    MachineResponse,
    UniversalArtifactContract,
)

ROOM_ID = "it"

# =====================================================
# STAGE PLAN
# =====================================================
# Stage 1:
# - Restore unified room contract.
# - Preserve machine-only architecture.
#


# Stage 5:
# - Connect providers and validate integration.

# =====================================================
# IT COMPETENCIES
# =====================================================

IT_COMPETENCY = {
    "domains": [
        "software_development",
        "programming",
        "algorithms",
        "system_architecture",
        "databases",
        "networking",
        "cybersecurity",
        "cloud_computing",
        "devops",
        "artificial_intelligence",
        "machine_learning",
        "testing",
        "version_control",
        "api_design",
    ]
}

IT_PROVIDERS = [
    {"id":"python","name":"Python","kind":"language","enabled":True},
    {"id":"git","name":"Git","kind":"version_control","enabled":True},
    {"id":"docker","name":"Docker","kind":"container","enabled":True},
    {"id":"postgresql","name":"PostgreSQL","kind":"database","enabled":True},
    {"id":"mongodb","name":"MongoDB","kind":"database","enabled":True},
    {"id":"rest_api","name":"REST API","kind":"integration","enabled":True},
]



def get_context(machine_request: MachineRequest) -> Dict[str, Any]:
    return {
        "room": ROOM_ID,
        "competency": IT_COMPETENCY,
        "providers": IT_PROVIDERS,
    }



def build_machine_contribution(machine_request: MachineRequest) -> Dict[str, Any]:
    context = get_context(machine_request)
    return {
        "room": ROOM_ID,
        "knowledge_context": context,
        "prompt_fragments": [
            "Use software engineering best practices.",
            "Prefer secure and maintainable implementations.",
            "Return machine-readable IT contribution."
        ],
        "artifact_hints": {
            "code": True,
            "table": True,
            "links": True,
            "graph": False,
        },
    }


def evaluate(machine_request: MachineRequest) -> Dict[str, Any]:
    query=""
    if isinstance(machine_request, dict):
        query=str(machine_request.get("query","")).lower()
    score=0.0
    for token in ("python","api","sql","docker","git","алгоритм","код","программ","database","network"):
        if token in query:
            score=max(score,0.95)
    return {
        "room": ROOM_ID,
        "score": score,
        "active": score>0.0,
        "reason": "it_match" if score>0 else "no_match",
    }

def execute(machine_request: MachineRequest):
    contribution=build_machine_contribution(machine_request)
    return create_artifact(
        artifact_type="function",
        room_source=ROOM_ID,
        data=contribution,
    )

class ITRoom(Room):
    name = ROOM_ID

ROOM = ITRoom()
