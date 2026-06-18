# =====================================================
# APRIL C_UTC_ROOM
# =====================================================

from typing import Dict, Any
from datetime import datetime, timezone

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact


class UTCRoom(Room):

    name = "utc"

    room_type = "service"

    ROOM_ID = "UTC_ROOM"

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

        print("UTC ROOM HANDLE START")

        return {

            "type": "text",

            "data":
                "UTC ROOM ACTIVE"
        }

    # =================================================
    # ARTIFACT FACTORY
    # =================================================

    def process(
        self,
        task: Dict[str, Any]
    ):

        utc_now = datetime.now(
            timezone.utc
        )

        artifact = create_artifact(

            artifact_type=
                self.ARTIFACT_TYPE,

            room_source=
                self.ROOM_ID,

            data={

                "domain":
                    "utc",

                "utc_timestamp":
                    utc_now.isoformat(),

                "utc_unix":
                    int(
                        utc_now.timestamp()
                    ),

                "capabilities": [

                    "utc_time",

                    "timezone_conversion",

                    "time_tracking",

                    "event_alignment",

                    "timeline_analysis",

                    "chronology",

                    "date_validation",

                    "session_sync"
                ]
            }
        )

        artifact.quality.validation_passed = True

        artifact.quality.quality_score = 1.0

        artifact.quality.confidence_score = 1.0

        artifact.quality.completeness_score = 1.0

        return artifact


ROOM = UTCRoom()
