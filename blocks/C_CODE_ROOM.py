from typing import Any, Dict
import os

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import (
    create_artifact,
    MachineRequest,
    MachineResponse,
    UniversalArtifactContract,
)

ROOM_ID = "code"

CODE_COMPETENCY = {
    "domains": [
        "programming_languages",
        "software_engineering",
        "algorithms",
        "debugging",
        "system_design",
        "api_design",
        "code_review",
        "testing",
    ]
}

CODE_PROVIDERS = [
    {"id":"github","name":"GitHub","kind":"repository","enabled":True},
    {"id":"python_docs","name":"Python Docs","kind":"documentation","enabled":True},
    {"id":"mdn","name":"MDN","kind":"documentation","enabled":True},
    {"id":"typescript_docs","name":"TypeScript Docs","kind":"documentation","enabled":True},
]

CODE_CONFIG = {
    "tool": "April",
    "email": os.getenv("CODE_ROOM_EMAIL",""),
}

def configure_code() -> bool:
    return True

def code_search(term:str)->Dict[str,Any]:
    return {"provider":"code","results":[]}

def get_context(machine_request:MachineRequest)->Dict[str,Any]:
    query=""
    if isinstance(machine_request,dict):
        query=str(machine_request.get("query",""))
    return {
        "room":ROOM_ID,
        "competency":CODE_COMPETENCY,
        "providers":CODE_PROVIDERS,
        "code":code_search(query),
    }

def build_machine_contribution(machine_request:MachineRequest)->Dict[str,Any]:
    ctx=get_context(machine_request)
    return {
        "room":ROOM_ID,
        "knowledge_context":ctx,
        "prompt_fragments":[
            "Prefer correct programming terminology.",
            "Generate production-quality code when appropriate.",
            "Explain assumptions separately from code."
        ],
        "artifact_hints":{
            "code":True,
            "text":True,
            "table":False,
            "graph":False,
            "formula":False,
        },
        "presentation_policy":{
            "preferred_renderer":"CodeBlock",
            "render_priority":"code_block",
        },
    }

class CodeRoom:
    name=ROOM_ID
    id=ROOM_ID
    domains=CODE_COMPETENCY["domains"]
    providers=CODE_PROVIDERS

    def get_context(self,machine_request:MachineRequest):
        return get_context(machine_request)

    def build_machine_contribution(self,machine_request:MachineRequest):
        return build_machine_contribution(machine_request)

    def evaluate(self,machine_request:MachineRequest):
        query=""
        if isinstance(machine_request,dict):
            query=str(machine_request.get("query","")).lower()
        score=0.0
        for token in (
            # Languages
            "python","py","javascript","js","typescript","ts","java","kotlin",
            "swift","go","golang","rust","php","ruby","perl","scala",
            "c","c++","c#","sql","html","css","xml","json","yaml","bash",
            "powershell","lua","dart","r","matlab",

            # Programming concepts
            "code","код","программа","программирование","исходный код",
            "скрипт","модуль","класс","class","function","функция","метод",
            "объект","ооп","object","algorithm","алгоритм","debug","отладка",
            "рефакторинг","оптимизация","api","sdk","library","библиотека",

            # Frameworks / tools
            "flask","django","fastapi","react","angular","vue","node",
            "docker","git","github","pytest","unittest",

            # Typical requests
            "напиши программу","напиши код","создай программу",
            "создай приложение","реализуй","исправь код",
            "сгенерируй код","console","консольное приложение"
        ):
            if token in query:
                score=max(score,0.95)
        return {
            "room":self.id,
            "score":score,
            "active":score>0.0,
            "reason":"code_match" if score>0 else "no_match",
        }

    def execute(self,machine_request:MachineRequest):
        contribution=self.build_machine_contribution(machine_request)
        return create_artifact(
            room=self.id,
            artifact_type="code",
            payload=contribution,
        )

ROOM=CodeRoom()

# Remaining work:
# - connect external provider module
# - register professional code libraries
