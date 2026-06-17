# =====================================================
# APRIL C_ARTIFACT_CONTRACT
# =====================================================

from dataclasses import dataclass, field
from typing import Any, Dict
import uuid
import time


@dataclass
class ArtifactMetadata:

    artifact_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )

    artifact_type: str = ""

    room_source: str = ""

    created_at: float = field(
        default_factory=time.time
    )


@dataclass
class ArtifactQuality:

    quality_score: float = 0.0

    confidence_score: float = 0.0

    completeness_score: float = 0.0

    validation_passed: bool = False


@dataclass
class ArtifactRenderContract:

    web_block: str = ""


@dataclass
class BaseArtifact:

    metadata: ArtifactMetadata

    quality: ArtifactQuality

    render: ArtifactRenderContract

    data: Dict[str, Any]


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

        quality=ArtifactQuality(),

        render=ArtifactRenderContract(

            web_block=ARTIFACT_BLOCK_MAP.get(
                artifact_type,
                ""
            )
        ),

        data=data
    )
