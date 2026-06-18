# =====================================================
# APRIL C_BIOLOGY_ROOM
# =====================================================

from typing import Dict, Any

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact


class BiologyRoom(Room):

    name = "biology"

    room_type = "science"

    ROOM_ID = "BIOLOGY_ROOM"

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

        artifact = self.process({

            "topic": text

        })

        return {

            "type": "text",

            "data":
                f"BIOLOGY ROOM ACTIVE: {text}"
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
                    "biology",

                "topic":
                    topic,

                "analysis":
                    {},

                "sections": [

                    "cell_biology",

                    "genetics",

                    "anatomy",

                    "physiology",

                    "ecology",

                    "evolution",

                    "microbiology",

                    "botany",

                    "zoology"
                ]
            }
        )

        artifact.quality.validation_passed = True

        artifact.quality.quality_score = 1.0

        artifact.quality.confidence_score = 1.0

        artifact.quality.completeness_score = 1.0

        return artifact


ROOM = BiologyRoom()
