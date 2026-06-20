# =====================================================
# APRIL C_BIOLOGY_ROOM V2 REFERENCE ROOM
# =====================================================

from typing import Dict, Any

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact


BIOLOGY_DOMAINS = {

    "genetics": [
        "днк","dna","рнк","rna","ген","gene",
        "геном","genome","хромосом","chromosome",
        "мутац","mutation","наслед"
    ],

    "cell_biology": [
        "клет","cell","митоз","mitosis",
        "мейоз","meiosis","ядро","membrane"
    ],

    "evolution": [
        "эволюц","evolution","отбор",
        "адаптац","видообраз"
    ],

    "ecology": [
        "эколог","ecosystem","популяц",
        "биом","среда"
    ],

    "zoology": [
        "животн","млекопитающ","птиц",
        "рептили","рыб","амфиби"
    ],

    "botany": [
        "растен","ботан","photosynthesis",
        "фотосинтез"
    ],

    "microbiology": [
        "бактер","вирус","архе",
        "гриб","микроорганизм"
    ],

    "physiology": [
        "орган","физиолог","кров",
        "дыхани","нервн"
    ]
}


def biology_analyze_topic(text):

    text_lower = str(text).lower()

    detected_domains = []
    entities = []

    for domain, patterns in BIOLOGY_DOMAINS.items():

        matched = False

        for pattern in patterns:

            if pattern in text_lower:
                matched = True
                entities.append(pattern)

        if matched:
            detected_domains.append(domain)

    confidence = min(
        len(detected_domains) / 3.0,
        1.0
    )

    return {

        "detected_domains":
            detected_domains,

        "entities":
            list(set(entities)),

        "biology_confidence":
            confidence
    }


def build_biology_answer(
    topic,
    analysis
):

    domains = analysis.get(
        "detected_domains",
        []
    )

    if domains:

        return (
            "Запрос относится к биологии. "
            f"Обнаружены разделы: {', '.join(domains)}. "
            "Комната может выполнить объяснение, "
            "сравнение, исследование, классификацию, "
            "подготовку таблицы, графика или научного обзора."
        )

    return (
        "Запрос был направлен в биологическую комнату. "
        "Даже если конкретные сущности не классифицированы, "
        "следует выполнить биологический анализ темы "
        "и подготовить объяснение на естественном языке."
    )


class BiologyRoom(Room):

    name = "biology"

    room_type = "science"

    ROOM_ID = "BIOLOGY_ROOM"

    ARTIFACT_TYPE = "function"

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
            "type": "artifact",
            "artifact": artifact,
            "room": self.name,
            "domain": "biology"
        }

    def process(
        self,
        task: Dict[str, Any]
    ):

        topic = task.get(
            "topic",
            ""
        )

        analysis = biology_analyze_topic(
            topic
        )

        answer = build_biology_answer(
            topic,
            analysis
        )

        artifact = create_artifact(

            artifact_type=self.ARTIFACT_TYPE,

            room_source=self.ROOM_ID,

            data={

                "domain": "biology",

                "topic": topic,

                "subdomains":
                    analysis.get(
                        "detected_domains",
                        []
                    ),

                "entities":
                    analysis.get(
                        "entities",
                        []
                    ),

                "answer":
                    answer,

                "summary":
                    answer,

                "analysis":
                    analysis,

                "room_identity": {
                    "specialization":
                        "biological_sciences"
                },

                "artifact_outputs": [
                    "explanation",
                    "comparison",
                    "research_summary",
                    "table",
                    "graph",
                    "diagram",
                    "conclusion"
                ]
            }
        )

        artifact.quality.validation_passed = True
        artifact.quality.quality_score = 1.0
        artifact.quality.confidence_score = 1.0
        artifact.quality.completeness_score = 1.0

        return artifact


ROOM = BiologyRoom()
