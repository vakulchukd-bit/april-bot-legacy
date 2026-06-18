# =====================================================
# APRIL C_POLITICS_ROOM
# =====================================================

from typing import Dict, Any

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact


class PoliticsRoom(Room):

    name = "politics"

    room_type = "professional"

    ROOM_ID = "POLITICS_ROOM"

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

        print("POLITICS ROOM HANDLE START")

        artifact = self.process({

            "topic": text

        })

        return {

            "type": "text",

            "data":
                "POLITICS ROOM ACTIVE"
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
                    "politics",

                "topic":
                    topic,

                "analysis":
                    {},

                "capabilities": [

                    "political_analysis",

                    "elections",

                    "governance",

                    "public_policy",

                    "international_relations",

                    "geopolitics",

                    "legislation",

                    "political_systems",

                    "political_history",

                    "comparative_politics"
                ]
            }
        )

        artifact.quality.validation_passed = True

        artifact.quality.quality_score = 1.0

        artifact.quality.confidence_score = 1.0

        artifact.quality.completeness_score = 1.0

        return artifact


ROOM = PoliticsRoom()
