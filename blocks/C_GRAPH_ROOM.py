# =====================================================
# 🏭 APRIL C_ARTIFACT_CONTRACT
# =====================================================

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time
import uuid

# =====================================================
# 🏭 ARTIFACT METADATA
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
# 🏭 ARTIFACT CONTEXT
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
# 🏭 ARTIFACT QUALITY
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
# 🏭 RENDER CONTRACT
# =====================================================

@dataclass
class ArtifactRenderContract:

    web_block: str = ""

    viewer: str = ""

    editable: bool = True

    responsive: bool = True

    exportable: bool = True

# =====================================================
# 🏭 BASE ARTIFACT
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
# 🏭 WEB BLOCK MAP
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
# 🏭 ARTIFACT FACTORY
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
                ""
            )
        ),

        data=data
    )

# =====================================================
# 🏭 SUPPORTED ARTIFACTS
# =====================================================

SUPPORTED_ARTIFACTS = [

    "graph",

    "formula",

    "table",

    "diagram",

    "code",

    "link",

    "gallery",

    "function"
]
