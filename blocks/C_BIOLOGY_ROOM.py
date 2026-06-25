
# ===== SOURCE: C_BIOLOGY_ROOM_skeleton.py =====

# =====================================================
# APRIL BIOLOGY ROOM (SKELETON)
# Temporary placeholder after architecture reset.
# =====================================================

from typing import Dict, List, Any

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import (
    create_artifact,
    MachineRequest,
    MachineResponse,
    UniversalArtifactContract,
)


# ===== SOURCE: C_BIOLOGY_ROOM_stage1_provider.py =====


# =====================================================
# APRIL BIOLOGY ROOM
# Stage 1: Knowledge Provider skeleton
# =====================================================

from typing import Dict, List, Any, Protocol

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import (
    create_artifact,
    MachineRequest,
    MachineResponse,
    UniversalArtifactContract,
)

DOMAIN = "biology"

class KnowledgeProvider(Protocol):
    name: str
    def search(self, topic: str) -> Dict[str, Any]: ...

class GeneOntologyProvider:
    """Stage-1 placeholder for future Gene Ontology integration."""

    name = "gene_ontology"

    def search(self, topic: str) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "domain": DOMAIN,
            "topic": topic,
            "status": "provider_registered",
            "prompt_fragments": [
                "Use accepted biological terminology.",
                "Prefer molecular biology and genetics context when relevant.",
                "State uncertainty when evidence is insufficient."
            ],
            "artifact_hints": {
                "markdown": True,
                "table": True,
                "graph": False
            }
        }

PROVIDERS: Dict[str, KnowledgeProvider] = {
    "gene_ontology": GeneOntologyProvider(),
}

def get_biology_context(topic: str) -> Dict[str, Any]:
    provider = PROVIDERS["gene_ontology"]
    return provider.search(topic)


# ===== SOURCE: C_BIOLOGY_ROOM_stage2.py =====

# =====================================================
# APRIL BIOLOGY ROOM
# Stage 1 - Competency + Real Provider Registry
# =====================================================

from typing import Dict, List, Any

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import (
    create_artifact,
    MachineRequest,
    MachineResponse,
    UniversalArtifactContract,
)

ROOM_ID="biology"

BIOLOGY_COMPETENCY={
    "domains":[
        "genetics",
        "molecular_biology",
        "cell_biology",
        "physiology",
        "microbiology",
        "botany",
        "zoology",
        "ecology",
        "evolution",
    ]
}

# Open knowledge providers (registry only)
BIOLOGY_PROVIDERS=[
    {
        "id":"gene_ontology",
        "name":"Gene Ontology",
        "kind":"ontology",
        "access":"api_or_download",
        "enabled":True,
    },
    {
        "id":"ncbi",
        "name":"NCBI",
        "kind":"knowledge",
        "access":"entrez",
        "enabled":True,
    },
    {
        "id":"uniprot",
        "name":"UniProt",
        "kind":"protein",
        "access":"rest",
        "enabled":True,
    },
]

def get_context(machine_request: MachineRequest)->Dict[str,Any]:
    return {
        "room":ROOM_ID,
        "competency":BIOLOGY_COMPETENCY,
        "providers":BIOLOGY_PROVIDERS,
        "machine_request":machine_request,
    }


# ===== SOURCE: C_BIOLOGY_ROOM_stage3.py =====

# =====================================================
# APRIL BIOLOGY ROOM
# Stage 1 - Competency + Real Provider Registry
# =====================================================

from typing import Dict, List, Any
import os
from Bio import Entrez

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import (
    create_artifact,
    MachineRequest,
    MachineResponse,
    UniversalArtifactContract,
)

ROOM_ID="biology"

BIOLOGY_COMPETENCY={
    "domains":[
        "genetics",
        "molecular_biology",
        "cell_biology",
        "physiology",
        "microbiology",
        "botany",
        "zoology",
        "ecology",
        "evolution",
    ]
}

# Open knowledge providers (registry only)
BIOLOGY_PROVIDERS=[
    {
        "id":"gene_ontology",
        "name":"Gene Ontology",
        "kind":"ontology",
        "access":"api_or_download",
        "enabled":True,
    },
    {
        "id":"ncbi",
        "name":"NCBI",
        "kind":"knowledge",
        "access":"entrez",
        "enabled":True,
    },
    {
        "id":"uniprot",
        "name":"UniProt",
        "kind":"protein",
        "access":"rest",
        "enabled":True,
    },
]

def get_context(machine_request: MachineRequest)->Dict[str,Any]:
    return {
        "room":ROOM_ID,
        "competency":BIOLOGY_COMPETENCY,
        "providers":BIOLOGY_PROVIDERS,
        "machine_request":machine_request,
    }


NCBI_CONFIG={
    "tool":"April",
    "email":os.getenv("NCBI_EMAIL",""),
}

def configure_ncbi()->None:
    if NCBI_CONFIG["email"]:
        Entrez.email=NCBI_CONFIG["email"]
    Entrez.tool=NCBI_CONFIG["tool"]

def ncbi_search(term:str, db:str="pubmed", retmax:int=5)->Dict[str,Any]:
    configure_ncbi()
    handle=Entrez.esearch(db=db, term=term, retmax=retmax)
    result=Entrez.read(handle)
    handle.close()
    return result


# ===== SOURCE: C_BIOLOGY_ROOM_stage4.py =====

# =====================================================
# APRIL BIOLOGY ROOM
# Stage 1 - Competency + Real Provider Registry
# =====================================================

from typing import Dict, List, Any

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import (
    create_artifact,
    MachineRequest,
    MachineResponse,
    UniversalArtifactContract,
)

ROOM_ID="biology"

BIOLOGY_COMPETENCY={
    "domains":[
        "genetics",
        "molecular_biology",
        "cell_biology",
        "physiology",
        "microbiology",
        "botany",
        "zoology",
        "ecology",
        "evolution",
    ]
}

# Open knowledge providers (registry only)
BIOLOGY_PROVIDERS=[
    {
        "id":"gene_ontology",
        "name":"Gene Ontology",
        "kind":"ontology",
        "access":"api_or_download",
        "enabled":True,
    },
    {
        "id":"ncbi",
        "name":"NCBI",
        "kind":"knowledge",
        "access":"entrez",
        "enabled":True,
    },
    {
        "id":"uniprot",
        "name":"UniProt",
        "kind":"protein",
        "access":"rest",
        "enabled":True,
    },
]



# ------------------------------------------------------------------
# Stage 3 - NCBI integration foundation
# ------------------------------------------------------------------

import os

try:
    from Bio import Entrez
    BIOPYTHON_AVAILABLE = True
except Exception:
    Entrez = None
    BIOPYTHON_AVAILABLE = False

NCBI_CONFIG = {
    "tool": "April",
    "email": os.getenv("NCBI_EMAIL", ""),
}

def configure_ncbi() -> bool:
    if not BIOPYTHON_AVAILABLE:
        return False
    Entrez.tool = NCBI_CONFIG["tool"]
    if NCBI_CONFIG["email"]:
        Entrez.email = NCBI_CONFIG["email"]
    return True

def ncbi_search(term: str, db: str = "pubmed", retmax: int = 5) -> Dict[str, Any]:
    if not configure_ncbi():
        return {
            "provider": "ncbi",
            "status": "biopython_not_installed",
            "results": [],
        }

    try:
        with Entrez.esearch(db=db, term=term, retmax=retmax) as handle:
            data = Entrez.read(handle)

        return {
            "provider": "ncbi",
            "status": "ok",
            "database": db,
            "ids": data.get("IdList", []),
            "count": data.get("Count", "0"),
        }
    except Exception as exc:
        return {
            "provider": "ncbi",
            "status": "error",
            "error": str(exc),
        }

def get_context(machine_request: MachineRequest) -> Dict[str, Any]:
    context = {
        "room": ROOM_ID,
        "competency": BIOLOGY_COMPETENCY,
        "providers": BIOLOGY_PROVIDERS,
        "machine_request": machine_request,
    }

    topic = ""
    if isinstance(machine_request, dict):
        topic = str(machine_request.get("query", ""))

    if topic:
        context["ncbi"] = ncbi_search(topic)

    return context


# ===== SOURCE: C_BIOLOGY_ROOM_stage5.py =====

# =====================================================
# APRIL BIOLOGY ROOM
# Stage 1 - Competency + Real Provider Registry
# =====================================================

from typing import Dict, List, Any

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import (
    create_artifact,
    MachineRequest,
    MachineResponse,
    UniversalArtifactContract,
)

ROOM_ID="biology"

BIOLOGY_COMPETENCY={
    "domains":[
        "genetics",
        "molecular_biology",
        "cell_biology",
        "physiology",
        "microbiology",
        "botany",
        "zoology",
        "ecology",
        "evolution",
    ]
}

# Open knowledge providers (registry only)
BIOLOGY_PROVIDERS=[
    {
        "id":"gene_ontology",
        "name":"Gene Ontology",
        "kind":"ontology",
        "access":"api_or_download",
        "enabled":True,
    },
    {
        "id":"ncbi",
        "name":"NCBI",
        "kind":"knowledge",
        "access":"entrez",
        "enabled":True,
    },
    {
        "id":"uniprot",
        "name":"UniProt",
        "kind":"protein",
        "access":"rest",
        "enabled":True,
    },
]



# ------------------------------------------------------------------
# Stage 3 - NCBI integration foundation
# ------------------------------------------------------------------

import os

try:
    from Bio import Entrez
    BIOPYTHON_AVAILABLE = True
except Exception:
    Entrez = None
    BIOPYTHON_AVAILABLE = False

NCBI_CONFIG = {
    "tool": "April",
    "email": os.getenv("NCBI_EMAIL", ""),
}

def configure_ncbi() -> bool:
    if not BIOPYTHON_AVAILABLE:
        return False
    Entrez.tool = NCBI_CONFIG["tool"]
    if NCBI_CONFIG["email"]:
        Entrez.email = NCBI_CONFIG["email"]
    return True

def ncbi_search(term: str, db: str = "pubmed", retmax: int = 5) -> Dict[str, Any]:
    if not configure_ncbi():
        return {
            "provider": "ncbi",
            "status": "biopython_not_installed",
            "results": [],
        }

    try:
        with Entrez.esearch(db=db, term=term, retmax=retmax) as handle:
            data = Entrez.read(handle)

        return {
            "provider": "ncbi",
            "status": "ok",
            "database": db,
            "ids": data.get("IdList", []),
            "count": data.get("Count", "0"),
        }
    except Exception as exc:
        return {
            "provider": "ncbi",
            "status": "error",
            "error": str(exc),
        }

def get_context(machine_request: MachineRequest) -> Dict[str, Any]:
    context = {
        "room": ROOM_ID,
        "competency": BIOLOGY_COMPETENCY,
        "providers": BIOLOGY_PROVIDERS,
        "machine_request": machine_request,
    }

    topic = ""
    if isinstance(machine_request, dict):
        topic = str(machine_request.get("query", ""))

    if topic:
        context["ncbi"] = ncbi_search(topic)

    return context


# ------------------------------------------------------------------
# Stage 4 - NCBI summary extraction
# ------------------------------------------------------------------

def ncbi_summary(db: str, ids: list[str]) -> Dict[str, Any]:
    if not ids:
        return {"provider": "ncbi", "status": "empty", "documents": []}

    if not configure_ncbi():
        return {"provider": "ncbi", "status": "biopython_not_installed", "documents": []}

    try:
        with Entrez.esummary(db=db, id=",".join(ids)) as handle:
            summary = Entrez.read(handle)

        docs = []
        for item in summary:
            docs.append({
                "uid": item.get("Id") or item.get("uid"),
                "title": item.get("Title", ""),
            })

        return {
            "provider": "ncbi",
            "status": "ok",
            "documents": docs,
        }
    except Exception as exc:
        return {
            "provider": "ncbi",
            "status": "error",
            "error": str(exc),
            "documents": [],
        }


# ===== SOURCE: C_BIOLOGY_ROOM_stage6_executor_ready.py =====

# =====================================================
# APRIL BIOLOGY ROOM
# Stage 1 - Competency + Real Provider Registry
# =====================================================

from typing import Dict, List, Any

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import (
    create_artifact,
    MachineRequest,
    MachineResponse,
    UniversalArtifactContract,
)

ROOM_ID="biology"

BIOLOGY_COMPETENCY={
    "domains":[
        "genetics",
        "molecular_biology",
        "cell_biology",
        "physiology",
        "microbiology",
        "botany",
        "zoology",
        "ecology",
        "evolution",
    ]
}

# Open knowledge providers (registry only)
BIOLOGY_PROVIDERS=[
    {
        "id":"gene_ontology",
        "name":"Gene Ontology",
        "kind":"ontology",
        "access":"api_or_download",
        "enabled":True,
    },
    {
        "id":"ncbi",
        "name":"NCBI",
        "kind":"knowledge",
        "access":"entrez",
        "enabled":True,
    },
    {
        "id":"uniprot",
        "name":"UniProt",
        "kind":"protein",
        "access":"rest",
        "enabled":True,
    },
]



# ------------------------------------------------------------------
# Stage 3 - NCBI integration foundation
# ------------------------------------------------------------------

import os

try:
    from Bio import Entrez
    BIOPYTHON_AVAILABLE = True
except Exception:
    Entrez = None
    BIOPYTHON_AVAILABLE = False

NCBI_CONFIG = {
    "tool": "April",
    "email": os.getenv("NCBI_EMAIL", ""),
}

def configure_ncbi() -> bool:
    if not BIOPYTHON_AVAILABLE:
        return False
    Entrez.tool = NCBI_CONFIG["tool"]
    if NCBI_CONFIG["email"]:
        Entrez.email = NCBI_CONFIG["email"]
    return True

def ncbi_search(term: str, db: str = "pubmed", retmax: int = 5) -> Dict[str, Any]:
    if not configure_ncbi():
        return {
            "provider": "ncbi",
            "status": "biopython_not_installed",
            "results": [],
        }

    try:
        with Entrez.esearch(db=db, term=term, retmax=retmax) as handle:
            data = Entrez.read(handle)

        return {
            "provider": "ncbi",
            "status": "ok",
            "database": db,
            "ids": data.get("IdList", []),
            "count": data.get("Count", "0"),
        }
    except Exception as exc:
        return {
            "provider": "ncbi",
            "status": "error",
            "error": str(exc),
        }

def get_context(machine_request: MachineRequest) -> Dict[str, Any]:
    context = {
        "room": ROOM_ID,
        "competency": BIOLOGY_COMPETENCY,
        "providers": BIOLOGY_PROVIDERS,
        "machine_request": machine_request,
    }

    topic = ""
    if isinstance(machine_request, dict):
        topic = str(machine_request.get("query", ""))

    if topic:
        context["ncbi"] = ncbi_search(topic)

    return context


# ------------------------------------------------------------------
# Stage 4 - NCBI summary extraction
# ------------------------------------------------------------------

def ncbi_summary(db: str, ids: list[str]) -> Dict[str, Any]:
    if not ids:
        return {"provider": "ncbi", "status": "empty", "documents": []}

    if not configure_ncbi():
        return {"provider": "ncbi", "status": "biopython_not_installed", "documents": []}

    try:
        with Entrez.esummary(db=db, id=",".join(ids)) as handle:
            summary = Entrez.read(handle)

        docs = []
        for item in summary:
            docs.append({
                "uid": item.get("Id") or item.get("uid"),
                "title": item.get("Title", ""),
            })

        return {
            "provider": "ncbi",
            "status": "ok",
            "documents": docs,
        }
    except Exception as exc:
        return {
            "provider": "ncbi",
            "status": "error",
            "error": str(exc),
            "documents": [],
        }


# ------------------------------------------------------------------
# Stage 5 - Unified Machine Contribution
# ------------------------------------------------------------------

def build_machine_contribution(machine_request: MachineRequest) -> Dict[str, Any]:
    query = ""
    if isinstance(machine_request, dict):
        query = str(machine_request.get("query",""))

    search = ncbi_search(query) if query else {}
    summary = {}
    if search.get("status") == "ok":
        summary = ncbi_summary(search.get("database","pubmed"), search.get("ids", []))

    return {
        "room": ROOM_ID,
        "confidence": 0.95 if query else 0.0,
        "knowledge_context": {
            "competency": BIOLOGY_COMPETENCY,
            "providers": BIOLOGY_PROVIDERS,
            "ncbi_search": search,
            "ncbi_summary": summary,
        },
        "prompt_fragments": [
            "Use accepted biological terminology.",
            "Prefer evidence-based biological explanations.",
            "Mention uncertainty when evidence is limited."
        ],
        "artifact_hints": {
            "text": True,
            "table": True,
            "graph": False,
            "links": True,
        },
    }
