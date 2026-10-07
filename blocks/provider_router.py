"""APRIL single OpenAI provider.

The Provider receives an already-resolved English semantic plan. It never decides
NEW/CONTINUE, never searches memory, and never selects another context.
"""
from __future__ import annotations
from typing import Any
import asyncio, hashlib, json, os, re, time
from openai import OpenAI

from blocks.C_ARTIFACT_CONTRACT import MachineRequest, MachineResponse, normalize_render_blocks

MODEL=os.getenv("APRIL_OPENAI_MODEL","gpt-5.6-luna")
MAX_OUTPUT_TOKENS=min(8000,max(256,int(os.getenv("APRIL_MAX_OUTPUT_TOKENS","2400") or 2400)))
INPUT_TOKEN_TARGET=900
_cache:dict[str,tuple[float,dict[str,Any]]]={}
_inflight:set[str]=set()
_client:OpenAI|None=None

SYSTEM_PROMPT=r"""
You are April's internal response provider. Work ONLY in English internally.

The processor has already selected the semantic relation and context.
Do not search memory or create a second route.

For CONTINUE:
- use the selected dialogue chain as the active semantic subject;
- answer the current request as a continuation of that subject;
- do not ask the user to repeat information that is already in the supplied chain.

For NEW_TOPIC:
- answer the current request independently;
- related background is informational only and must not override the current request.

Return JSON only:
{
  "answer": "complete human-readable answer in the requested display language",
  "content": "same answer or concise equivalent",
  "summary": "one-sentence summary",
  "render_blocks": [
    {"type":"text","renderer":"messagetextblock","viewer":"messagetextblock","content":"..."}
  ]
}

When code is requested, add a code render block:
{"type":"code","renderer":"codeblock","viewer":"codeblock","language":"python","code":"..."}

When a direct link is requested, keep the full URL unchanged and add a link block:
{"type":"link","renderer":"linkblock","viewer":"linkblock","url":"https://...","label":"..."}

Do not output machine metadata, internal state, or JSON inside the answer.
Never return an empty answer.
"""


def _client_get()->OpenAI:
    global _client
    if _client is None:
        key=os.getenv("OPENAI_API_KEY")
        if not key: raise RuntimeError("OPENAI_API_KEY_NOT_CONFIGURED")
        _client=OpenAI(api_key=key)
    return _client


def _text(value:Any)->str:
    if isinstance(value,str): return value.strip()
    if value is None: return ""
    return str(value).strip()


def _json_load(raw:str)->dict[str,Any]:
    raw=_text(raw)
    if raw.startswith("```"):
        raw=re.sub(r"^```(?:json)?\s*","",raw,flags=re.I)
        raw=re.sub(r"\s*```$","",raw)
    try:
        data=json.loads(raw)
        if isinstance(data,dict): return data
    except Exception:
        pass
    # Recovery only for envelope syntax; no semantic fallback.
    m=re.search(r"\{.*\}",raw,re.S)
    if m:
        try:
            data=json.loads(m.group(0))
            if isinstance(data,dict): return data
        except Exception: pass
    return {"answer":raw,"content":raw,"summary":raw[:180],"render_blocks":[]}


def _request_key(req:MachineRequest)->str:
    raw=json.dumps({
        "user_id": req.fiber.identity.user_id,
        "conversation": req.conversation,
        "intent": req.intent,
        "text": req.conversation.get("current_request") or req.goal,
        "memory": req.memory,
        "routing": req.routing,
        "constraints": req.constraints,
    }, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def _build_input(req:MachineRequest)->list[dict[str,str]]:
    plan = getattr(req, "provider_context_plan", None)
    if not isinstance(plan, dict):
        plan = dict(req.memory or {})
    relation = str(plan.get("relation") or req.intent.get("dialogue_relation") or "NEW")
    chain = plan.get("dialogue_chain") or []
    context_lines = []
    for item in chain[-4:]:
        context_lines.append(
            f"PAIR {item.get('position')}: USER={item.get('user_en','')} | APRIL={item.get('april_en','')}"
        )
    context = "\n".join(context_lines) if context_lines else "(no previous dialogue pair selected)"
    language = _text(req.constraints.get("provider_output_language") or "en")
    user_text = (
        "RELATION: " + relation + "\n"
        "CURRENT_REQUEST: " + _text(req.conversation.get("current_request") or req.goal) + "\n"
        "SELECTED_DIALOGUE_CHAIN:\n" + context + "\n"
        "RETURN_LANGUAGE: " + language + "\n"
        "OUTPUT_CONTRACT: answer + content + summary + render_blocks"
    )
    return [{"role":"system","content":SYSTEM_PROMPT}, {"role":"user","content":user_text}]

def _normalize(data:dict[str,Any])->dict[str,Any]:
    answer=_text(data.get("answer") or data.get("content") or data.get("response"))
    if not answer:
        raise RuntimeError("PROVIDER_EMPTY_ANSWER")
    blocks=normalize_render_blocks(data.get("render_blocks"),answer)
    return {
        "machine_response":{
            "answer":answer,
            "content":_text(data.get("content") or answer),
            "summary":_text(data.get("summary") or answer[:180]),
            "render_blocks":blocks,
            "metadata":{
                "provider_model":MODEL,
                "provider_language":"en",
                "provider_context_authority":"INTERPRETATION",
            },
            "artifacts":[],
        }
    }


async def generate_text(request:MachineRequest|dict[str,Any])->dict[str,Any]:
    if isinstance(request,dict):
        request=MachineRequest(**request)
    key=_request_key(request)
    cached=_cache.get(key)
    if cached and time.time()-cached[0]<90:
        return cached[1]
    if key in _inflight:
        raise RuntimeError("DUPLICATE_PROVIDER_REQUEST")
    _inflight.add(key)
    started=time.perf_counter()
    try:
        response=await asyncio.to_thread(
            _client_get().responses.create,
            model=MODEL,
            input=_build_input(request),
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        raw=_text(getattr(response,"output_text",""))
        if not raw:
            raise RuntimeError("OPENAI_EMPTY_OUTPUT")
        contract=_normalize(_json_load(raw))
        mr=contract["machine_response"]
        mr["metadata"]["provider_ms"]=round((time.perf_counter()-started)*1000,1)
        usage=getattr(response,"usage",None)
        if usage is not None:
            mr["metadata"]["usage"]={
                "input_tokens":int(getattr(usage,"input_tokens",0) or 0),
                "output_tokens":int(getattr(usage,"output_tokens",0) or 0),
                "total_tokens":int(getattr(usage,"total_tokens",0) or 0),
            }
        _cache[key]=(time.time(),contract)
        return contract
    finally:
        _inflight.discard(key)


# Compatibility names kept only because the executor imports these directly.
async def transcribe_voice(file_path:str)->str:
    with open(file_path,"rb") as handle:
        result=await asyncio.to_thread(
            _client_get().audio.transcriptions.create,
            model="gpt-4o-mini-transcribe",
            file=handle,
        )
    return _text(getattr(result,"text",""))


def normalize_provider_input(value:Any)->Any:
    return value
