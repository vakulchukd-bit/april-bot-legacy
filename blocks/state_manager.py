"""APRIL 12-hour dialogue state.

One responsibility: maintain the authenticated live dialogue window and the
active semantic sequence. Renderer/provider decisions do not live here.
"""
from __future__ import annotations

from datetime import datetime, timezone
from copy import deepcopy
import threading
import time
import uuid
from typing import Any

from storage import load_dialogue_pairs, save_dialogue_pair, init_db

DIALOGUE_WINDOW_HOURS=12
_LOCK=threading.RLock()
_STATES:dict[str,dict[str,Any]]={}


def _new_sequence() -> dict[str,Any]:
    return {
        "sequence_id": f"seq-{uuid.uuid4().hex[:20]}",
        "turn_index": 0,
        "topic": "",
        "task": {},
        "updated_at": time.time(),
    }


def _state(user_id:str)->dict[str,Any]:
    return {
        "user_id":user_id,
        "dialogue_pairs":[],
        "active_sequence":_new_sequence(),
        "language":"en",
        "updated_at":time.time(),
    }


def get_state(user_id:Any)->dict[str,Any]:
    uid=str(user_id or "").strip()
    if not uid:
        raise ValueError("USER_ID_REQUIRED")
    with _LOCK:
        state=_STATES.get(uid)
        if state is None:
            state=_state(uid)
            _STATES[uid]=state
        # Refresh the canonical 12h pair window on first use and after inactivity.
        rows=load_dialogue_pairs(uid,limit=0)
        state["dialogue_pairs"]=rows
        state["updated_at"]=time.time()
        return state


def refresh_state(user_id:Any)->dict[str,Any]:
    return get_state(user_id)


def set_language(user_id:Any, language:str)->None:
    state=get_state(user_id)
    state["language"]=str(language or "en")
    state["updated_at"]=time.time()


def get_language(user_id:Any)->str:
    return str(get_state(user_id).get("language") or "en")


def get_dialogue_pairs(user_id:Any)->list[dict[str,Any]]:
    return [dict(x) for x in get_state(user_id).get("dialogue_pairs",[]) if isinstance(x,dict)]


def get_active_sequence(user_id:Any)->dict[str,Any]:
    return deepcopy(get_state(user_id).get("active_sequence") or _new_sequence())


def begin_new_topic(user_id:Any, topic:str, task:dict[str,Any]|None=None)->dict[str,Any]:
    state=get_state(user_id)
    sequence=_new_sequence()
    sequence["topic"]=str(topic or "").strip()
    sequence["task"]=deepcopy(task or {})
    state["active_sequence"]=sequence
    state["updated_at"]=time.time()
    return deepcopy(sequence)


def continue_topic(user_id:Any, topic:str="", task:dict[str,Any]|None=None)->dict[str,Any]:
    state=get_state(user_id)
    sequence=state.get("active_sequence") or _new_sequence()
    sequence["turn_index"]=int(sequence.get("turn_index") or 0)+1
    if topic:
        sequence["topic"]=str(topic).strip()
    if task:
        sequence["task"]=deepcopy(task)
    sequence["updated_at"]=time.time()
    state["active_sequence"]=sequence
    state["updated_at"]=time.time()
    return deepcopy(sequence)


def save_pair(
    user_id:Any,
    user_text_original:str,
    april_text_original:str,
    *,
    user_text_en:str,
    april_text_en:str,
    language:str,
    relation:str,
)->dict[str,Any]:
    state=get_state(user_id)
    sequence=state.get("active_sequence") or _new_sequence()
    turn_index=int(sequence.get("turn_index") or 0)
    ok=save_dialogue_pair(
        user_id,user_text_original,april_text_original,
        user_en=user_text_en,april_en=april_text_en,
        language=language,turn_index=turn_index,
    )
    if not ok:
        return {"saved":False}
    rows=load_dialogue_pairs(user_id,limit=0)
    state["dialogue_pairs"]=rows
    state["last_relation"]=relation
    state["last_original_user"]=user_text_original
    state["last_internal_user"]=user_text_en
    state["last_original_answer"]=april_text_original
    state["last_internal_answer"]=april_text_en
    state["updated_at"]=time.time()
    return {"saved":True,"turn_index":turn_index,"pair_count":len(rows)}


def add_dialog(user_id:Any, role:str, content:str, metadata:dict[str,Any]|None=None, *, persist:bool=True)->bool:
    # Compatibility for the gateway only. Canonical persistence is save_pair().
    state=get_state(user_id)
    state.setdefault("dialogue_events",[]).append({
        "role":str(role),"content":str(content or ""),
        "metadata":deepcopy(metadata or {}),"created_at":time.time(),
    })
    state["dialogue_events"]=state["dialogue_events"][-50:]
    return True


def update_scene_context(user_id:Any, contract:dict[str,Any], *,
                         current_request:str, answer:str,
                         provider_result:dict[str,Any]|None=None,
                         internal_user_request:str="",
                         internal_answer:str="",
                         display_language:str="en",
                         relation:str="NEW")->dict[str,Any]:
    topic=str((contract.get("dialogue_state") or {}).get("topic") or current_request).strip()
    if relation=="CONTINUE":
        continue_topic(user_id,topic=topic,task=(contract.get("active_task") or {}))
    else:
        begin_new_topic(user_id,topic,task=(contract.get("active_task") or {}))
    return save_pair(
        user_id,current_request,answer,
        user_text_en=internal_user_request or current_request,
        april_text_en=internal_answer or answer,
        language=display_language,relation=relation,
    )


def initialize() -> None:
    try: init_db()
    except Exception: pass
