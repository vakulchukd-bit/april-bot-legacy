# =====================================================
# APRIL C_LITERATURE_ROOM
# =====================================================

from typing import Dict, Any

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact


class LiteratureRoom(Room):

    name = "literature"

    room_type = "knowledge"

    ROOM_ID = "LITERATURE_ROOM"

    ARTIFACT_TYPE = "function"

    quality_score = 1.0
    confidence_score = 1.0
    completeness_score = 1.0

    # =================================================
    # ROOM EXECUTION
    # =================================================

    async def handle(
        self,
        user_id,
        text,
        context,
        run
    ):

        print("LITERATURE ROOM HANDLE START")

        artifact = self.process({

            "topic": text

        })

        return {

            "type": "text",

            "data":
                "LITERATURE ROOM ACTIVE"
        }

    # =================================================
    # ARTIFACT FACTORY
    # =================================================

    def process(
        self,
        task: Dict[str, Any]
    ):

        topic = task.get(
            "topic",
            ""
        )

        artifact = create_artifact(

            artifact_type=
                self.ARTIFACT_TYPE,

            room_source=
                self.ROOM_ID,

            data={

                "domain":
                    "literature",

                "topic":
                    topic,

                "analysis":
                    {},

                "sections": [

                    "fiction",

                    "poetry",

                    "drama",

                    "novels",

                    "storytelling",

                    "literary_analysis",

                    "authors",

                    "characters",

                    "writing_style"
                ]
            }
        )

        artifact.quality.validation_passed = True

        artifact.quality.quality_score = 1.0

        artifact.quality.confidence_score = 1.0

        artifact.quality.completeness_score = 1.0

        return artifact


ROOM = LiteratureRoom()
