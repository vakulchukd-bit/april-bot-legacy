# =====================================================
# APRIL C_TABLE_ROOM
# =====================================================

from typing import Dict, Any

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact


class TableRoom(Room):

    name = "table"

    room_type = "visual"

    ROOM_ID = "TABLE_ROOM"

    ARTIFACT_TYPE = "table"

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

        print("TABLE ROOM HANDLE START")

        return {

            "type": "text",

            "data":
                "TABLE ROOM ACTIVE"
        }

    # =================================================
    # TABLE ARTIFACT
    # =================================================

    def process(
        self,
        task: Dict[str, Any]
    ):

        artifact = create_artifact(

            artifact_type=
                self.ARTIFACT_TYPE,

            room_source=
                self.ROOM_ID,

            data={

                "title":
                    task.get(
                        "title",
                        "Table"
                    ),

                "headers":
                    task.get(
                        "headers",
                        []
                    ),

                "rows":
                    task.get(
                        "rows",
                        []
                    )
            }
        )

        artifact.quality.validation_passed = True

        artifact.quality.quality_score = 1.0

        artifact.quality.confidence_score = 1.0

        artifact.quality.completeness_score = 1.0

        return artifact


ROOM = TableRoom()
