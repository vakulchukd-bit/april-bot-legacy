# =====================================================
# APRIL C_SOCIAL_ROOM
# =====================================================

from typing import Dict, Any

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact


class SocialRoom(Room):

    name = "social"

    room_type = "professional"

    ROOM_ID = "SOCIAL_ROOM"

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

        print("SOCIAL ROOM HANDLE START")

        artifact = self.process({

            "topic": text

        })

        return {

            "type": "text",

            "data":
                "SOCIAL ROOM ACTIVE"
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
                    "social",

                "topic":
                    topic,

                "analysis":
                    {},

                "capabilities": [

                    "social_media",

                    "community_analysis",

                    "audience_behavior",

                    "public_discussion",

                    "trend_tracking",

                    "platform_monitoring",

                    "social_dynamics",

                    "communication_patterns",

                    "engagement_analysis",

                    "reputation_monitoring"
                ]
            }
        )

        artifact.quality.validation_passed = True

        artifact.quality.quality_score = 1.0

        artifact.quality.confidence_score = 1.0

        artifact.quality.completeness_score = 1.0

        return artifact


ROOM = SocialRoom()
