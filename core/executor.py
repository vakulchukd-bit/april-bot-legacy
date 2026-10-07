"""APRIL clean executor.

Single route:
BotRU translation -> Interpretation/12h semantic dialogue -> OpenAI -> SceneContract.
No legacy room chain, no duplicate interpreter, no renderer selection inside executor.
"""
from __future__ import annotations
from typing import Any
import time, uuid

from blocks.state_manager import get_state, update_scene_context, begin_new_topic, continue_topic
from blocks.interpretation_layer import interpret_request
from blocks.provider_router import generate_text
from blocks.C_ARTIFACT_CONTRACT import MachineRequest, MachineResponse, build_scene_contract, serialize_scene_for_web

PROCESSOR_VERSION="april_clean_context_first_12h_v1"


def _text(x:Any)->str:
    return str(x or "").strip()


def _next_dialogue_contract(base:dict[str,Any], state:dict[str,Any], relation:str)->dict[str,Any]:
    dialogue=dict(base or {})
    seq=state.get("active_sequence") or {}
    dialogue["dialogue_sequence_id"]=str(seq.get("sequence_id") or "")
    dialogue["sequence_turn_index"]=int(seq.get("turn_index") or 0)
    dialogue["relation"]=relation
    return dialogue


async def execute(
    user_id:str,
    chat_id:Any=None,
    text:str="",
    *,
    internal_text:str="",
    display_language:str="en",
    flow_id:str="",
    conversation_id:str="",
    **kwargs:Any,
)->dict[str,Any]:
    request_text=_text(internal_text or text)
    if not request_text:
        raise ValueError("EMPTY_REQUEST")
    uid=_text(user_id)
    if not uid:
        raise ValueError("USER_ID_REQUIRED")

    state=get_state(uid)
    history=list(state.get("dialogue_pairs") or [])
    previous_relation=state.get("last_relation_state") if isinstance(state.get("last_relation_state"),dict) else {}
    interpretation=interpret_request(
        request_text,
        history=history,
        state={**state,"last_relation_state":previous_relation},
        display_language=display_language,
    )

    relation=str(interpretation.get("dialogue_relation") or "NEW")
    dialogue=_next_dialogue_contract(interpretation.get("dialogue_contract"),state,relation)
    metadata={
        "conversation_id":conversation_id,
        "relation_reason":interpretation.get("relation_reason"),
        "relation_confidence":interpretation.get("relation_confidence"),
        "display_language":display_language,
    }

    # Do not mutate the active sequence before OpenAI succeeds.
    # The canonical sequence is committed exactly once after SceneContract build.
    sequence=state.get("active_sequence") or {}
    if relation=="CONTINUE":
        dialogue["sequence_turn_index"]=int(sequence.get("turn_index") or 0)+1
        dialogue["dialogue_sequence_id"]=str(sequence.get("sequence_id") or "")
    else:
        dialogue["sequence_turn_index"]=1
        dialogue["dialogue_sequence_id"]=f"seq-{uuid.uuid4().hex[:20]}"

    flow=str(flow_id or uuid.uuid4())
    machine_request=MachineRequest(
        request_id=flow,
        user_id=uid,
        text=request_text,
        intent=interpretation,
        dialogue_contract=dialogue,
        provider_context_plan=interpretation.get("provider_context_plan") or {},
        requested_outputs=["text"],
        display_language=display_language,
        metadata=metadata,
    )

    started=time.perf_counter()
    provider=await generate_text(machine_request)
    provider_ms=round((time.perf_counter()-started)*1000,1)
    mr=provider.get("machine_response") if isinstance(provider,dict) else {}
    if not isinstance(mr,dict):
        raise RuntimeError("PROVIDER_CONTRACT_MISSING")

    response=MachineResponse(
        answer=_text(mr.get("answer") or mr.get("content")),
        content=_text(mr.get("content") or mr.get("answer")),
        summary=_text(mr.get("summary")),
        render_blocks=list(mr.get("render_blocks") or []),
        metadata={**dict(mr.get("metadata") or {}),"provider_ms":provider_ms},
        artifacts=list(mr.get("artifacts") or []),
    )
    if not response.answer:
        raise RuntimeError("CANONICAL_ANSWER_MISSING")

    contract=build_scene_contract(request=machine_request,response=response,flow_id=flow)

    # Canonical 12h memory is written only AFTER the final scene has been built,
    # so a provider transport error can never poison the dialogue with an error string.
    update_scene_context(
        uid,contract,
        current_request=str(kwargs.get("original_user_text") or text or request_text),
        answer=response.answer,
        provider_result=provider,
        internal_user_request=request_text,
        internal_answer=response.answer,
        display_language=display_language,
        relation=relation,
    )
    state=get_state(uid)
    state["last_relation_state"]={
        "relation":relation,
        "selected_index":dialogue.get("selected_memory_index",-1),
        "topic":dialogue.get("canonical_topic",""),
    }

    result=serialize_scene_for_web(contract)
    result.update({
        "flow_id":flow,
        "provider_calls_per_request":1,
        "processor_version":PROCESSOR_VERSION,
        "provider_context_plan":machine_request.provider_context_plan,
        "provider_context_authority":"INTERPRETATION",
        "display_language":display_language,
        "internal_language":"en",
    })
    return result
