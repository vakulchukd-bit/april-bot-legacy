from dataclasses import dataclass
from uuid import uuid4

@dataclass(frozen=True)
class InterpretationIdentity:
    interpretation_id: str
    dialog_id: str
    conversation_id: str
    message_id: str
    april_id: str

    @classmethod
    def create(cls, *, april_id, conversation_id, dialog_id, message_id, interpretation_id=None):
        for name, value in (("april_id", april_id), ("conversation_id", conversation_id), ("dialog_id", dialog_id), ("message_id", message_id)):
            if not value:
                raise ValueError(f"{name} is required")
        return cls(interpretation_id or f"interp_{uuid4().hex}", dialog_id, conversation_id, message_id, april_id)

    def as_dict(self):
        return self.__dict__.copy()
