# =====================================================
# APRIL C_FORMULA_ROOM
# =====================================================

from typing import Dict, Any, List

from blocks.C_ARTIFACT_CONTRACT import create_artifact


class FormulaRoom:

    name = "formula"

    room_type = "visual"

    ROOM_ID = "FORMULA_ROOM"

    ARTIFACT_TYPE = "formula"

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

        print("FORMULA ROOM HANDLE START")

        payload = context.get("formula_payload") or context.get("payload") or {}
        formulas = self._extract_formulas(payload, text)
        formula = formulas[0] if formulas else ""

        artifact = self.process({
            "formula": str(formula or ""),
            "formulas": formulas,
            "goal": context.get("goal"),
            "purpose": context.get("purpose"),
            "active_scene": context.get("active_scene"),
            "scene_id": context.get("scene_id"),
            "turn_id": context.get("turn_id"),
            "flow_id": context.get("flow_id"),
            "topic_group": context.get("topic_group"),
            "continuation": context.get("continuation", False),
            "block_id": context.get("block_id"),
            "render_id": context.get("render_id"),
            "markdown": context.get("markdown"),
            "katex": True,
        })

        return artifact


    # =================================================
    # CANONICAL FORMULA LIST
    # =================================================

    def _extract_formulas(self, payload: Any, text: Any = "") -> List[str]:
        """Extract all explicitly supplied formulas without semantic rewriting."""
        values: List[Any] = []
        if isinstance(payload, dict):
            for key in ("formulas", "formulae", "equations", "expressions"):
                candidate = payload.get(key)
                if isinstance(candidate, list):
                    values.extend(candidate)
                elif isinstance(candidate, str) and candidate.strip():
                    values.append(candidate)
            for key in ("formula", "latex", "equation", "expression", "content"):
                candidate = payload.get(key)
                if candidate not in (None, "", []):
                    values.append(candidate)
        elif payload not in (None, ""):
            values.append(payload)
        # Never infer a formula from the current user sentence.  FormulaRoom only
        # materializes formulas that were explicitly carried by the canonical provider
        # payload.  This prevents an ordinary text answer such as "Напиши формулу..."
        # from becoming a second synthetic FormulaRenderer block.
        result: List[str] = []
        for value in values:
            if isinstance(value, dict):
                value = value.get("latex") or value.get("tex") or value.get("formula") or value.get("equation") or value.get("expression") or value.get("value")
            value = str(value or "").strip()
            if value and value not in result:
                result.append(value)
        return result

    def build_markdown(self, formulas: List[str]) -> str:
        """Build one canonical Markdown transport containing all formulas."""
        blocks = []
        for formula in formulas:
            value = str(formula or "").strip()
            if not value:
                continue
            if value.startswith("$$") and value.endswith("$$"):
                blocks.append(value)
            elif value.startswith("\\[") and value.endswith("\\]"):
                blocks.append(value)
            else:
                blocks.append(f"$$\n{value}\n$$")
        return "\n\n".join(blocks)

    # =================================================
    # WORK ORDER
    # =================================================

    def build_work_order(
        self,
        task: Dict[str, Any]
    ) -> Dict[str, Any]:

        formulas = task.get("formulas")
        if not isinstance(formulas, list):
            formulas = self._extract_formulas({"formula": task.get("formula")})

        return {

            "goal":
                task.get("goal"),

            "purpose":
                task.get("purpose"),

            "active_scene":
                task.get("active_scene"),

            "formula":
                task.get("formula"),

            "formulas":
                formulas,

            "markdown":
                task.get("markdown") or self.build_markdown(formulas),

            "katex":
                True
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
        formula: str,
        formulas: List[str] | None = None,
        markdown: str = "",
    ):

        formulas = [str(x).strip() for x in (formulas or [formula]) if str(x).strip()]
        variables = sorted({v for item in formulas for v in self.extract_variables(item)})
        formula = formulas[0] if formulas else formula
        markdown = markdown or self.build_markdown(formulas)

        artifact = create_artifact(

            artifact_type=
                self.ARTIFACT_TYPE,

            room_source=
                self.ROOM_ID,

            data={

                "formula": formula,

                "latex": self.build_latex(formula),

                "formulas": formulas,

                "latex_formulas": [self.build_latex(item) for item in formulas],

                "markdown": markdown,

                "katex": True,

                "variables": variables,

                "explanation": self.build_explanation(
                    formula,
                    variables
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

        formulas = work_order.get("formulas") or self._extract_formulas({"formula": work_order.get("formula")})
        if not formulas:
            return None

        formula = formulas[0]
        if not self.validate_formula(formula):
            return None

        return self.build_artifact(
            formula,
            formulas=formulas,
            markdown=work_order.get("markdown") or self.build_markdown(formulas),
        )


ROOM = FormulaRoom()
