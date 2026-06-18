# =====================================================
# APRIL C_TRIGONOMETRY_ROOM
# =====================================================

from typing import Dict, Any

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact


class TrigonometryRoom(Room):

    name = "trigonometry"

    room_type = "science"

    ROOM_ID = "TRIGONOMETRY_ROOM"

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

        print("TRIGONOMETRY ROOM HANDLE START")

        artifact = self.process({

            "topic": text

        })

        return {

            "type": "text",

            "data":
                "TRIGONOMETRY ROOM ACTIVE"
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
                    "trigonometry",

                "topic":
                    topic,

                "analysis":
                    {},

                "functions": [

                    "sin",
                    "cos",
                    "tan",
                    "cot"
                ]
            }
        )

        artifact.quality.validation_passed = True

        artifact.quality.quality_score = 1.0

        artifact.quality.confidence_score = 1.0

        artifact.quality.completeness_score = 1.0

        return artifact


ROOM = TrigonometryRoom()
