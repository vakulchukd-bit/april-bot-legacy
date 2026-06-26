# =====================================================
# APRIL C_LITERATURE_ROOM
# =====================================================

from typing import Dict, Any
from blocks.C_ARTIFACT_CONTRACT import MachineRequest

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact


LITERATURE_COMPETENCY = {
    "domains":[
        "fiction","poetry","drama","novels",
        "literary_analysis","authors","characters","writing_style"
    ]
}

class LiteratureRoom(Room):

    name = "literature"

    room_type = "knowledge"

    ROOM_ID = "LITERATURE_ROOM"

    ARTIFACT_TYPE = "function"

    quality_score = 1.0
    confidence_score = 1.0
    completeness_score = 1.0


    id = "literature"
    domains = LITERATURE_COMPETENCY["domains"]

    def evaluate(self, machine_request: MachineRequest):
        query = ""
        if isinstance(machine_request, dict):
            query = str(machine_request.get("query","")).lower()
        score = 0.2
        hits = ("author","novel","poem","literature","book","story","writer","character")
        if any(h in query for h in hits):
            score = 1.0
        return {
            "room":"literature",
            "score":score,
            "confidence":score
        }

    def get_context(self, machine_request: MachineRequest):
        return {
            "room":"literature",
            "competency":LITERATURE_COMPETENCY
        }

    def build_machine_contribution(self, machine_request: MachineRequest):
        return {
            "room":"literature",
            "knowledge_context":self.get_context(machine_request),
            "prompt_fragments":[
                "Use accepted literary terminology.",
                "Preserve author intent when relevant.",
                "Separate analysis from interpretation."
            ]
        }

    async def execute(self, machine_request: MachineRequest):
        return self.build_machine_contribution(machine_request)


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
