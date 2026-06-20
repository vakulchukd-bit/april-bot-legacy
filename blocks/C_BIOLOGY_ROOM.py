
# =====================================================
# APRIL C_BIOLOGY_ROOM V11
# ANSWER ENGINE EDITION
# =====================================================

from typing import List
from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact

ROOM_IDENTITY = {
    "specialization":"biological_sciences",
    "knowledge_class":"life_sciences"
}

BIOLOGY_KNOWLEDGE = {
    "dna": """ДНК — молекула наследственности. Содержит генетическую информацию,
организована в двойную спираль, входит в состав хромосом и определяет
синтез белков через процессы транскрипции и трансляции.""",

    "gene": """Ген — участок ДНК, содержащий информацию о синтезе белка
или функциональной РНК.""",

    "cell": """Клетка — базовая структурная и функциональная единица жизни.
Содержит мембрану, цитоплазму и генетический материал.""",

    "evolution": """Эволюция — процесс изменения популяций организмов во времени
под действием отбора, мутаций, миграции и генетического дрейфа."""
}

def detect_operation(text:str)->str:
    t=text.lower()
    if "сравн" in t:
        return "compare"
    return "explain"

def detect_domains(text:str)->List[str]:
    t=text.lower()
    result=[]
    if "днк" in t or "dna" in t:
        result.append("genetics")
    if "клет" in t:
        result.append("cell_biology")
    if "эволюц" in t:
        result.append("evolution")
    return result

def extract_entities(text:str)->List[str]:
    return text.lower().split()

def generate_biology_answer(topic:str)->str:
    t = topic.lower()

    if "днк" in t:
        return """
ДНК человека — молекула, содержащая наследственную информацию организма.

Основные функции:
• хранение генетической информации;
• передача наследственных признаков;
• управление синтезом белков.

У человека геном организован в 23 пары хромосом.
Изменения в ДНК называются мутациями и могут влиять на развитие организма.

Вывод:
ДНК является фундаментальной основой наследственности и работы клеток.
""".strip()

    if "клет" in t:
        return BIOLOGY_KNOWLEDGE["cell"]

    if "эволюц" in t:
        return BIOLOGY_KNOWLEDGE["evolution"]

    return (
        "Запрос относится к биологии. Необходимо определить объект исследования, "
        "его структуру, функции, механизмы и научные выводы."
    )

class BiologyReasoningEngine:

    def run(self, topic:str):

        return {
            "operation": detect_operation(topic),
            "domains": detect_domains(topic),
            "entities": extract_entities(topic),
            "answer": generate_biology_answer(topic),
            "conclusion": "Biological answer generated."
        }

class BiologyRoom(Room):

    name="biology"
    room_type="science"
    ROOM_ID="BIOLOGY_ROOM"
    ARTIFACT_TYPE="function"

    async def handle(self, user_id, text, context, run):

        result = BiologyReasoningEngine().run(text)

        artifact = create_artifact(
            artifact_type=self.ARTIFACT_TYPE,
            room_source=self.ROOM_ID,
            data={
                "domain":"biology",
                "topic":text,
                "room_identity":ROOM_IDENTITY,
                **result
            }
        )

        return {
            "type":"artifact",
            "artifact":artifact,
            "room":self.name,
            "domain":"biology"
        }

ROOM = BiologyRoom()
