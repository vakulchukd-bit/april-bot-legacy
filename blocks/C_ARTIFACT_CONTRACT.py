from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import uuid
import time

# =====================================================
# ARTIFACT METADATA
# =====================================================

@dataclass
class ArtifactMetadata:

    artifact_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )

    artifact_version: str = "1.0"

    created_at: float = field(
        default_factory=time.time
    )

    room_source: str = ""

    artifact_type: str = ""

# =====================================================
# ARTIFACT CONTEXT
# =====================================================

@dataclass
class ArtifactContext:

    goal: Optional[str] = None

    purpose: Optional[str] = None

    role: Optional[str] = None

    active_scene: Optional[str] = None

    dependencies: List[str] = field(
        default_factory=list
    )

# =====================================================
# ARTIFACT QUALITY
# =====================================================

@dataclass
class ArtifactQuality:

    quality_score: float = 0.0

    confidence_score: float = 0.0

    completeness_score: float = 0.0

    validation_passed: bool = False

    warnings: List[str] = field(
        default_factory=list
    )

# =====================================================
# RENDER CONTRACT
# =====================================================

@dataclass
class ArtifactRenderContract:

    web_block: str = ""

    viewer: str = ""

    editable: bool = True

    responsive: bool = True

    exportable: bool = True

# =====================================================
# BASE ARTIFACT
# =====================================================

@dataclass
class BaseArtifact:

    metadata: ArtifactMetadata

    context: ArtifactContext

    quality: ArtifactQuality

    render: ArtifactRenderContract

    data: Dict[str, Any] = field(
        default_factory=dict
    )

# =====================================================
# BLOCK MAP
# =====================================================

ARTIFACT_BLOCK_MAP = {

    "graph": "GraphBlock",

    "formula": "FormulaBlock",

    "table": "TableBlock",

    "diagram": "DiagramBlock",

    "code": "CodeBlock",

    "link": "LinkCard",

    "gallery": "GalleryBlock",

    "function": "FunctionBlock"
}

# =====================================================
# FACTORY ROOM MAP
# =====================================================

FACTORY_ROOM_MAP = {

    "graph": "C_GRAPH_ROOM",
    "formula": "C_FORMULA_ROOM",
    "table": "C_TABLE_ROOM",
    "diagram": "C_DIAGRAM_ROOM",
    "code": "C_CODE_ROOM",
    "link": "C_LINK_ROOM",
    "gallery": "C_GALLERY_ROOM",
    "function": "C_FUNCTION_ROOM",

    "mathematics": "C_MATHEMATICS_ROOM",
    "trigonometry": "C_TRIGONOMETRY_ROOM",
    "physics": "C_PHYSICS_ROOM",
    "chemistry": "C_CHEMISTRY_ROOM",
    "biology": "C_BIOLOGY_ROOM",

    "literature": "C_LITERATURE_ROOM",
    "web": "C_WEB_ROOM",
    "utc": "C_UTC_ROOM",

    "engineering": "C_ENGINEERING_ROOM",
    "politics": "C_POLITICS_ROOM",
    "news": "C_NEWS_ROOM",
    "social": "C_SOCIAL_ROOM",
    "it": "C_IT_ROOM"
}

# =====================================================
# FACTORY STATUS
# =====================================================

FACTORY_STATUS = {

    "visual_rooms": True,

    "science_rooms": True,

    "knowledge_rooms": True,

    "professional_rooms": True
}

# =====================================================
# CREATE ARTIFACT
# =====================================================

def create_artifact(
    artifact_type: str,
    room_source: str,
    data: Dict[str, Any]
):

    return BaseArtifact(

        metadata=ArtifactMetadata(
            artifact_type=artifact_type,
            room_source=room_source
        ),

        context=ArtifactContext(),

        quality=ArtifactQuality(),

        render=ArtifactRenderContract(
            web_block=ARTIFACT_BLOCK_MAP.get(
                artifact_type,
                "FunctionBlock"
            )
        ),

        data=data
    )
