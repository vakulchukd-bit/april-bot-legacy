# =====================================================
# APRIL C_BIOLOGY_ROOM V13
# BIOLOGY FACTORY PROFESSIONAL FOUNDATION
# =====================================================

from typing import Dict, List, Any
from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact

ROOM_IDENTITY = {
    "specialization": "biological_sciences",
    "knowledge_class": "life_sciences",
    "architecture": "biology_factory_v13"
}

BIOLOGY_KNOWLEDGE_BASE = {
    "genetics": "Гены, наследственность, ДНК, РНК и геном.",
    "molecular_biology": "Молекулярные механизмы клетки.",
    "cell_biology": "Строение и функции клеток.",
    "evolution": "Изменение популяций и видов во времени.",
    "ecology": "Взаимодействие организмов и среды."
}

class BiologyOperationDetector:

    def detect(self, text: str) -> str:
        t = text.lower()

        if "срав" in t:
            return "compare"
        if "граф" in t:
            return "visualize"
        if "табл" in t:
            return "tabulate"

        return "analyze"


class BiologyEntityRegistry:

    def extract(self, text: str) -> List[str]:
        return [w.strip(".,!?()[]") for w in text.split() if len(w) > 2]


class BiologyReasoningEngine:

    def build_answer(self, topic: str, operation: str):

        q = topic.lower()

        if "днк" in q:
            return (
                "ДНК человека — молекула, содержащая наследственную "
                "информацию организма. Она состоит из нуклеотидов "
                "аденина, тимина, гуанина и цитозина. Геном человека "
                "содержит около 3 миллиардов пар оснований и организован "
                "в 23 пары хромосом. ДНК участвует в хранении, передаче "
                "и реализации генетической информации через синтез РНК "
                "и белков."
            )

        if operation == "compare":
            return (
                "Запрос определён как сравнительный биологический анализ. "
                "Необходимо выделить сходства, различия, общие признаки, "
                "эволюционные связи и функциональные особенности объектов."
            )

        return (
            "Биология изучает живые организмы, их строение, функции, "
            "развитие, наследственность, эволюцию и взаимодействие "
            "с окружающей средой. Для более точного анализа необходимо "
            "уточнение объекта исследования."
        )

    def run(self, topic: str):

        operation = BiologyOperationDetector().detect(topic)
        entities = BiologyEntityRegistry().extract(topic)

        answer = self.build_answer(topic, operation)

        return {
            "operation": operation,
            "entities": entities,
            "domains": list(BIOLOGY_KNOWLEDGE_BASE.keys()),
            "answer": answer,
            "research_summary": answer,
            "response_plan": {
                "text": True,
                "table": operation in ["compare", "tabulate"],
                "graph": operation == "visualize",
                "diagram": operation == "visualize",
                "sources": True
            },
            "table": [],
            "graph": [],
            "diagram": [],
            "sources": [],
            "comparison": {}
        }


class BiologyRoom(Room):

    name = "biology"
    room_type = "science"

    ROOM_ID = "BIOLOGY_ROOM"
    ARTIFACT_TYPE = "function"

    async def handle(self, user_id, text, context, run):

        result = BiologyReasoningEngine().run(text)

        artifact = create_artifact(
            artifact_type=self.ARTIFACT_TYPE,
            room_source=self.ROOM_ID,
            data={
                "domain": "biology",
                "topic": text,
                "room_identity": ROOM_IDENTITY,
                **result
            }
        )

        return {
            "type": "artifact",
            "artifact": artifact,
            "room": self.name,
            "domain": "biology"
        }

ROOM = BiologyRoom()
