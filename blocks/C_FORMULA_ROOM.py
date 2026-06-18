# =====================================================
# 🏭 APRIL C_FORMULA_ROOM
# =====================================================

"""
APRIL_FILE_ID:
C_FORMULA_ROOM

ROLE:
PROFESSIONAL_FORMULA_WORKSHOP

INPUT:

- user_request
- memory_context
- active_scene
- engineering_task
- formula_text

OUTPUT:

- FormulaArtifact
"""

from typing import Dict, Any, List

from blocks.C_ARTIFACT_CONTRACT import create_artifact

# =====================================================
# 🏭 FORMULA ROOM
# =====================================================

class FormulaRoom:

    ROOM_ID = "FORMULA_ROOM"

    ARTIFACT_TYPE = "formula"

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

            "active_scene":
                task.get("active_scene"),

            "formula":
                task.get("formula")
        }

    # =================================================
    # FORMULA PARSER
    # =================================================

    def parse_formula(
        self,
        formula: str
    ) -> Dict[str, Any]:

        return {

            "raw":
                formula,

            "normalized":
                formula.strip()
        }

    # =================================================
    # VARIABLE ENGINE
    # =================================================

    def extract_variables(
        self,
        formula: str
    ) -> List[str]:

        variables = []

        for symbol in [

            "x",
            "y",
            "z",

            "a",
            "b",
            "c",

            "m",
            "v",
            "t",

            "F",
            "E",
            "P",

            "R",
            "I",
            "U"
        ]:

            if symbol in formula:

                variables.append(
                    symbol
                )

        return variables

    # =================================================
    # LATEX ENGINE
    # =================================================

    def build_latex(
        self,
        formula: str
    ) -> str:

        return formula

    # =================================================
    # EXPLANATION ENGINE
    # =================================================

    def build_explanation(
        self,
        formula: str,
        variables: List[str]
    ) -> str:

        return (
            f"Formula contains variables: "
            f"{', '.join(variables)}"
        )

    # =================================================
    # VALIDATION
    # =================================================

    def validate_formula(
        self,
        formula: str
    ) -> bool:

        return bool(
            formula and len(formula) > 0
        )

    # =================================================
    # QUALITY
    # =================================================

    def calculate_quality(
        self,
        formula: str
    ) -> float:

        if not formula:

            return 0.0

        return 1.0

    # =================================================
    # ARTIFACT BUILDER
    # =================================================

    def build_artifact(
        self,
        formula: str
    ):

        variables = self.extract_variables(
            formula
        )

        return create_artifact(

            artifact_type=
                self.ARTIFACT_TYPE,

            room_source=
                self.ROOM_ID,

            data={

                "formula":
                    formula,

                "latex":
                    self.build_latex(
                        formula
                    ),

                "variables":
                    variables,

                "explanation":
                    self.build_explanation(
                        formula,
                        variables
                    )
            }
        )

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

        formula = work_order.get(
            "formula",
            ""
        )

        if not self.validate_formula(
            formula
        ):

            return None

        return self.build_artifact(
            formula
        )


# =====================================================
# FACTORY EXPORT
# =====================================================

ROOM = FormulaRoom()
