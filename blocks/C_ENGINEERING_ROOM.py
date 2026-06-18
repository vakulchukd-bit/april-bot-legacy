# =====================================================
# APRIL C_ENGINEERING_ROOM
# =====================================================

from typing import Dict, Any

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact


class EngineeringRoom(Room):

    name = "engineering"

    room_type = "professional"

    ROOM_ID = "ENGINEERING_ROOM"

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

        print("ENGINEERING ROOM HANDLE START")

        artifact = self.process({

            "topic": text

        })

        return {

            "type": "text",

            "data":
                "ENGINEERING ROOM ACTIVE"
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
                    "engineering",

                "topic":
                    topic,

                "analysis":
                    {},

                "capabilities": [

                    "system_design",

                    "architecture",

                    "mechanical_engineering",

                    "electrical_engineering",

                    "civil_engineering",

                    "process_engineering",

                    "technical_analysis",

                    "optimization",

                    "diagnostics",

                    "project_planning"
                ]
            }
        )

        artifact.quality.validation_passed = True

        artifact.quality.quality_score = 1.0

        artifact.quality.confidence_score = 1.0

        artifact.quality.completeness_score = 1.0

        return artifact


ROOM = EngineeringRoom()
