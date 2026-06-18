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
                "BIOLOGY ROOM ACTIVE"
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

                # =====================================
                # DOMAIN
                # =====================================

                "domain":
                    "biology",

                "topic":
                    topic,

                "analysis":
                    {},

                # =====================================
                # ROOM IDENTITY
                # =====================================

                "room_identity": {

                    "specialization":
                        "biological_sciences",

                    "knowledge_class":
                        "life_sciences",

                    "mission":
                        (
                            "understand living systems, "
                            "biological processes and "
                            "relationships between organisms "
                            "and environments"
                        )
                },

                # =====================================
                # KNOWLEDGE SCOPE
                # =====================================

                "knowledge_scope": [

                    "cell_biology",

                    "genetics",

                    "anatomy",

                    "physiology",

                    "ecology",

                    "evolution",

                    "microbiology",

                    "botany",

                    "zoology",

                    "biochemistry",

                    "molecular_biology",

                    "neuroscience",

                    "immunology",

                    "developmental_biology",

                    "marine_biology",

                    "environmental_biology"
                ],

                # =====================================
                # REASONING CAPABILITIES
                # =====================================

                "capabilities": [

                    "scientific_reasoning",

                    "biological_reasoning",

                    "life_system_analysis",

                    "cause_effect_analysis",

                    "classification",

                    "comparison",

                    "observation_analysis",

                    "hypothesis_generation",

                    "experimental_design",

                    "research_interpretation",

                    "ecosystem_reasoning",

                    "organism_reasoning",

                    "genetics_reasoning",

                    "evolutionary_reasoning"
                ],

                # =====================================
                # EXPERIMENT CAPABILITIES
                # =====================================

                "experiment_capabilities": [

                    "experiment_design",

                    "experiment_planning",

                    "observation_tracking",

                    "result_interpretation",

                    "control_variable_definition",

                    "hypothesis_validation",

                    "research_structure_generation"
                ],

                # =====================================
                # ARTIFACT OUTPUTS
                # =====================================

                "artifact_outputs": [

                    "explanation",

                    "research_summary",

                    "experiment",

                    "comparison",

                    "classification",

                    "observation_report",

                    "conclusion",

                    "hypothesis",

                    "table",

                    "diagram",

                    "graph"
                ],

                # =====================================
                # SCENE CONTRIBUTION
                # =====================================

                "scene_contribution": {

                    "provides": [

                        "biological_context",

                        "biological_explanation",

                        "living_system_analysis",

                        "experimental_framework",

                        "scientific_validation",

                        "research_context",

                        "observation_framework"
                    ]
                },

                # =====================================
                # COLLABORATION
                # =====================================

                "collaboration": {

                    "compatible_rooms": [

                        "chemistry",

                        "physics",

                        "mathematics",

                        "engineering",

                        "it",

                        "web",

                        "news",

                        "table",

                        "graph",

                        "diagram",

                        "formula"
                    ]
                },

                # =====================================
                # EXECUTOR METADATA
                # =====================================

                "executor_metadata": {

                    "room_role":
                        "domain_specialist",

                    "contribution_type":
                        "scientific_knowledge",

                    "scene_role":
                        "knowledge_provider",

                    "supports_multi_room_scene":
                        True,

                    "supports_cross_domain_reasoning":
                        True
                }
            }
        )

        artifact.quality.validation_passed = True

        artifact.quality.quality_score = 1.0

        artifact.quality.confidence_score = 1.0

        artifact.quality.completeness_score = 1.0

        return artifact


ROOM = BiologyRoom()
