# =====================================================
# 🏭 APRIL C_GALLERY_ROOM
# =====================================================

from typing import Dict, Any, List

from blocks.C_ARTIFACT_CONTRACT import create_artifact

class GalleryRoom:

    ROOM_ID = "GALLERY_ROOM"

    ARTIFACT_TYPE = "gallery"

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

            "images":
                task.get("images", []),

            "captions":
                task.get("captions", [])
        }

    # =================================================
    # IMAGE ENGINE
    # =================================================

    def build_images(
        self,
        images: List
    ) -> List:

        return images

    # =================================================
    # CAPTION ENGINE
    # =================================================

    def build_captions(
        self,
        captions: List
    ) -> List:

        return captions

    # =================================================
    # COMPARISON ENGINE
    # =================================================

    def build_comparison(
        self,
        images: List
    ) -> Dict:

        return {

            "enabled":
                len(images) > 1,

            "count":
                len(images)
        }

    # =================================================
    # LAYOUT ENGINE
    # =================================================

    def build_layout(
        self,
        images: List
    ) -> Dict:

        return {

            "layout":
                "gallery",

            "count":
                len(images)
        }

    # =================================================
    # VALIDATION
    # =================================================

    def validate_gallery(
        self,
        images: List
    ) -> bool:

        return len(images) > 0

    # =================================================
    # ARTIFACT BUILDER
    # =================================================

    def build_artifact(
        self,
        images: List,
        captions: List
    ):

        artifact = create_artifact(

            artifact_type=
                self.ARTIFACT_TYPE,

            room_source=
                self.ROOM_ID,

            data={

                "images":
                    self.build_images(
                        images
                    ),

                "captions":
                    self.build_captions(
                        captions
                    ),

                "comparison":
                    self.build_comparison(
                        images
                    ),

                "layout":
                    self.build_layout(
                        images
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

        images = work_order.get(
            "images",
            []
        )

        captions = work_order.get(
            "captions",
            []
        )

        if not self.validate_gallery(
            images
        ):

            return None

        return self.build_artifact(
            images,
            captions
        )


ROOM = GalleryRoom()
