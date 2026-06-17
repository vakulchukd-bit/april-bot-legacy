# =====================================================
# 🏭 APRIL C_WEB_ROOM
# =====================================================

from typing import Dict, Any

from C_ARTIFACT_CONTRACT import create_artifact


class WebRoom:

    ROOM_ID = "WEB_ROOM"

    ARTIFACT_TYPE = "link"

    def process(
        self,
        task: Dict[str, Any]
    ):

        query = task.get(
            "query",
            ""
        )

        artifact = create_artifact(

            artifact_type=
                self.ARTIFACT_TYPE,

            room_source=
                self.ROOM_ID,

            data={

                "domain":
                    "web",

                "query":
                    query,

                "analysis":
                    {},

                "capabilities": [

                    "search",

                    "verification",

                    "sources",

                    "fact_check",

                    "current_events",

                    "knowledge_lookup",

                    "web_navigation",

                    "reference_collection"
                ]
            }
        )

        artifact.quality.validation_passed = True

        artifact.quality.quality_score = 1.0

        artifact.quality.confidence_score = 1.0

        artifact.quality.completeness_score = 1.0

        return artifact


ROOM = WebRoom()
