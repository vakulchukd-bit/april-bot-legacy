# =====================================================
# 🏭 APRIL C_LINK_ROOM
# =====================================================

from typing import Dict, Any
from C_ARTIFACT_CONTRACT import create_artifact


class LinkRoom:

    ROOM_ID = "LINK_ROOM"

    ARTIFACT_TYPE = "link"

    # =================================================
    # WORK ORDER
    # =================================================

    def build_work_order(
        self,
        task: Dict[str, Any]
    ) -> Dict[str, Any]:

        return {

            "goal":
                task.get("goal"),

            "purpose":
                task.get("purpose"),

            "url":
                task.get("url", ""),

            "title":
                task.get("title", ""),

            "description":
                task.get("description", "")
        }

    # =================================================
    # VALIDATION
    # =================================================

    def validate_url(
        self,
        url: str
    ) -> bool:

        if not url:

            return False

        return (
            url.startswith("http://")
            or
            url.startswith("https://")
        )

    # =================================================
    # PREVIEW ENGINE
    # =================================================

    def build_preview(
        self,
        url: str
    ) -> Dict:

        return {

            "url": url,

            "preview_ready": True
        }

    # =================================================
    # QUALITY ENGINE
    # =================================================

    def calculate_quality(
        self,
        url: str
    ) -> float:

        if not url:

            return 0.0

        return 1.0

    # =================================================
    # ARTIFACT BUILDER
    # =================================================

    def build_artifact(
        self,
        title: str,
        url: str,
        description: str
    ):

        artifact = create_artifact(

            artifact_type=
                self.ARTIFACT_TYPE,

            room_source=
                self.ROOM_ID,

            data={

                "title":
                    title,

                "url":
                    url,

                "description":
                    description,

                "preview":
                    self.build_preview(
                        url
                    )
            }
        )

        artifact.quality.validation_passed = True
        artifact.quality.quality_score = 1.0
        artifact.quality.confidence_score = 1.0
        artifact.quality.completeness_score = 1.0

        return artifact

    # =================================================
    # MAIN PROCESS
    # =================================================

    def process(
        self,
        task: Dict[str, Any]
    ):

        work_order = self.build_work_order(
            task
        )

        url = work_order.get(
            "url",
            ""
        )

        if not self.validate_url(
            url
        ):

            return None

        return self.build_artifact(

            work_order.get(
                "title",
                ""
            ),

            url,

            work_order.get(
                "description",
                ""
            )
        )


ROOM = LinkRoom()
