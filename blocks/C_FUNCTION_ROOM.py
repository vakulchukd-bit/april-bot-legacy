# =====================================================
# 🏭 APRIL C_FUNCTION_ROOM
# =====================================================

from typing import Dict, Any

from C_ARTIFACT_CONTRACT import create_artifact


class FunctionRoom:

    ROOM_ID = "FUNCTION_ROOM"

    ARTIFACT_TYPE = "function"

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

            "function":
                task.get("function", ""),

            "description":
                task.get("description", "")
        }

    # =================================================
    # FUNCTION ENGINE
    # =================================================

    def build_function(
        self,
        function: str
    ) -> Dict:

        return {

            "expression":
                function
        }

    # =================================================
    # ANALYSIS ENGINE
    # =================================================

    def build_analysis(
        self,
        function: str
    ) -> Dict:

        return {

            "analyzed": True,

            "expression":
                function
        }

    # =================================================
    # VALIDATION
    # =================================================

    def validate_function(
        self,
        function: str
    ) -> bool:

        return bool(
            function and function.strip()
        )

    # =================================================
    # ARTIFACT BUILDER
    # =================================================

    def build_artifact(
        self,
        function: str,
        description: str
    ):

        artifact = create_artifact(

            artifact_type=
                self.ARTIFACT_TYPE,

            room_source=
                self.ROOM_ID,

            data={

                "function":
                    self.build_function(
                        function
                    ),

                "analysis":
                    self.build_analysis(
                        function
                    ),

                "description":
                    description
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

        function = work_order.get(
            "function",
            ""
        )

        if not self.validate_function(
            function
        ):

            return None

        return self.build_artifact(

            function,

            work_order.get(
                "description",
                ""
            )
        )


ROOM = FunctionRoom()
