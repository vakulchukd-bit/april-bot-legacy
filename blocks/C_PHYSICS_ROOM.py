# =====================================================
# APRIL C_PHYSICS_ROOM
# =====================================================

from typing import Dict, Any

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact


class PhysicsRoom(Room):

    name = "physics"

    room_type = "science"

    ROOM_ID = "PHYSICS_ROOM"

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

        print("PHYSICS ROOM HANDLE START")

        artifact = self.process({

            "topic": text

        })

        return {

            "type": "text",

            "data":
                "PHYSICS ROOM ACTIVE"
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
                    "physics",

                "topic":
                    topic,

                "analysis":
                    {},

                "sections": [

                    "mechanics",

                    "kinematics",

                    "dynamics",

                    "electricity",

                    "magnetism",

                    "optics",

                    "thermodynamics",

                    "waves"
                ]
            }
        )

        artifact.quality.validation_passed = True

        artifact.quality.quality_score = 1.0

        artifact.quality.confidence_score = 1.0

        artifact.quality.completeness_score = 1.0

        return artifact


ROOM = PhysicsRoom()
