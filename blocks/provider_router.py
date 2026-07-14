# =====================================================
# 🧠 APRIL PROVIDER ROUTER
# =====================================================

"""
APRIL_FILE_ID: APRIL_PROVIDER_ROUTER

ROLE:
provider_orchestration_layer

PURPOSE:
- provider coordination
- multimodal routing
- fallback stabilization
- provider recovery control
- visual provider balancing
- continuity-safe provider behavior

INPUT:
- text_requests
- image_requests
- voice_requests
- provider_state
- orchestration_signals

OUTPUT:
- normalized_provider_response
- provider_safe_output
- multimodal_response

DEPENDENCIES:
- openai
- gemini
- cognition
- semantic_core
- excrouter
- visual_system

GOLDEN RULE:
Providers generate.
April orchestrates.
"""

print("🧠 APRIL PROVIDER ROUTER LOADED")

# =====================================================
# 🔥 IMPORTS
# =====================================================

import os
import time

from openai import OpenAI
from google import genai


# =====================================================
# 🔥 PROVIDERS
# =====================================================

openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# =====================================================
# 🔥 SAFE PATCH MODE
# =====================================================

PROVIDER_PATCH_LOG = []


def provider_patch_log(msg):

    try:

        print(
            "APRIL PROVIDER:",
            msg
        )

        PROVIDER_PATCH_LOG.append(
            str(msg)
        )

    except Exception:
        pass


# =====================================================
# 🔥 ENTRY / EXIT LOGGING
# =====================================================

def provider_enter(
    provider_type,
    payload=None
):

    provider_patch_log(

        f"ENTER PROVIDER: "
        f"{provider_type}"
    )

    if payload:

        provider_patch_log(
            str(payload)[:120]
        )

    return {

        "provider_active": True,

        "provider_type":
            provider_type,

        "continuity_safe": True
    }


def provider_exit(
    provider_type,
    success=True
):

    provider_patch_log(

        f"EXIT PROVIDER: "
        f"{provider_type} "
        f"SUCCESS={success}"
    )

    return {

        "provider_complete": success,

        "provider_type":
            provider_type,

        "response_ready": True
    }


# =====================================================
# 🔥 FUTURE PLACEHOLDER
# =====================================================

def provider_future(
    *args,
    **kwargs
):

    return None


# =====================================================
# 🔥 PROVIDER STATE
# =====================================================

provider_state = {

    # =================================================
    # 🔥 PRIMARY ORCHESTRATION
    # =====================================================

    "primary": "openai",

    # =================================================
    # 🔥 VISUAL ASSIST LAYER
    # =====================================================

    "gemini_available": True,

    "last_gemini_failure": 0,

    "last_health_check": 0,

    "recovery_cooldown": 45,

    # =================================================
    # 🔥 BEHAVIOR STABILIZATION
    # =====================================================

    "visual_mode": "lightweight",

    "execution_mode": "calm",

    "route_health": 1.0,

    "provider_balance": "stable"
}


# =====================================================
# 🔥 SAFE LOG
# =====================================================

def provider_log(*args):

    try:

        print(*args)

    except Exception:
        pass


# =====================================================
# 🔥 PROVIDER BEHAVIOR
# =====================================================

def update_provider_behavior():

    now = time.time()

    last_failure = provider_state.get(
        "last_gemini_failure",
        0
    )

    delta = now - last_failure

    if delta <= 60:

        provider_state[
            "route_health"
        ] = 0.3

        provider_state[
            "provider_balance"
        ] = "recovery"

    else:

        provider_state[
            "route_health"
        ] = 1.0

        provider_state[
            "provider_balance"
        ] = "stable"

    if provider_state.get(
        "gemini_available"
    ):

        provider_state[
            "visual_mode"
        ] = "distributed"

    else:

        provider_state[
            "visual_mode"
        ] = "restricted"


# =====================================================
# 🔥 GEMINI RESTORE CHECK
# =====================================================

def should_restore_gemini():

    update_provider_behavior()

    if provider_state["gemini_available"]:

        return True

    now = time.time()

    cooldown = provider_state[
        "recovery_cooldown"
    ]

    last_failure = provider_state[
        "last_gemini_failure"
    ]

    if now - last_failure >= cooldown:

        provider_log(
            "🧠 GEMINI RECOVERY WINDOW OPEN"
        )

        provider_state[
            "gemini_available"
        ] = True

        provider_state[
            "last_health_check"
        ] = now

        provider_state[
            "provider_balance"
        ] = "probing"

        return True

    return False


# =====================================================
# 🔥 GEMINI FAILURE
# =====================================================

def mark_gemini_failure():

    provider_log(
        "🔥 GEMINI MARKED UNAVAILABLE"
    )

    provider_state[
        "gemini_available"
    ] = False

    provider_state[
        "last_gemini_failure"
    ] = time.time()

    provider_state[
        "provider_balance"
    ] = "fallback"

    provider_state[
        "route_health"
    ] = 0.0


# =====================================================
# 🔥 GEMINI SUCCESS
# =====================================================

def mark_gemini_success():

    provider_state[
        "gemini_available"
    ] = True

    provider_state[
        "last_health_check"
    ] = time.time()

    provider_state[
        "provider_balance"
    ] = "stable"

    provider_state[
        "route_health"
    ] = 1.0


# =====================================================
# 🔥 RESPONSE NORMALIZER
# =====================================================

def normalize_response_text(text):

    if not text:
        return ""

    text = str(text).strip()

    text = text.replace(
        "\n\n\n",
        "\n\n"
    )

    return sanitize_internal_reasoning(text).strip()


# =====================================================
# 🔥 MACHINE RESPONSE WRAPPER
# =====================================================

def build_provider_machine_response(text, parsed_contract=None):
    """Build a unified MachineResponse transport contract."""
    parsed_contract = parsed_contract or {}

    answer = parsed_contract.get("answer") or text
    content = parsed_contract.get("content") or answer
    response = parsed_contract.get("response") or answer
    summary = parsed_contract.get("summary", "")
    explanation = parsed_contract.get("explanation", summary)
    if response is None:
        response = answer

    return {
        "type": "provider_response",
        "machine_response": {
            "summary": summary,
            "explanation": explanation,
            "content": content,
            "answer": answer,
            "response": response,
            "scene": parsed_contract.get("scene", {}),
            "render_blocks": parsed_contract.get("render_blocks", []),
            "artifacts": parsed_contract.get("artifacts", []),
            "scene_plan": parsed_contract.get("scene_plan", ["text"]),
            "confidence": parsed_contract.get("confidence", 1.0),
            "metadata": parsed_contract.get("metadata", {}),
            "provider": "openai",
            "render_priority": parsed_contract.get("render_priority", []),
            "provider_contract": "fiber_v3",
            "transport_contract": "scene_first"
        }
    }

import json
from blocks.C_ARTIFACT_CONTRACT import MachineRequest

def parse_provider_machine_contract(raw_text):
    """Parse a MachineResponse transport contract."""
    try:
        data=json.loads(raw_text)
        if isinstance(data,dict):
            return data
    except json.JSONDecodeError as e:
        provider_log(f"JSON PARSE ERROR line={e.lineno} col={e.colno} pos={e.pos}")
        start=max(0,e.pos-80)
        end=min(len(raw_text),e.pos+80)
        provider_log(raw_text[start:end])
        raise ValueError("Invalid MachineResponse JSON from provider") from e





# =====================================================
# STAGE 2 - SCENE-FIRST CONTRACT
# =====================================================

def ensure_scene_first_contract(contract):
    contract = validate_machine_response_contract(contract)
    contract.setdefault("scene", {})
    contract.setdefault("render_blocks", [])
    contract.setdefault("artifacts", [])
    return contract


# =====================================================
# 🔥 SAFE OVERLOAD RESPONSE
# =====================================================



def validate_machine_response_contract(contract):
    """Guarantee a valid transport contract for Executor."""
    if not isinstance(contract, dict):
        contract = {}

    contract.setdefault("summary", "")
    contract.setdefault("explanation", contract["summary"])
    contract.setdefault("artifacts", [])
    contract.setdefault("scene_plan", ["text"])
    contract.setdefault("render_priority", ["text"])
    contract.setdefault("confidence", 0.0)
    contract.setdefault("scene", {})
    contract.setdefault("render_blocks", [])
    contract.setdefault("metadata", {})

    return contract



# =====================================================
# STAGE 1 - CANONICAL TEXT TRANSPORT
# =====================================================

def normalize_text_transport(contract):
    """
    Synchronize answer/content/response/summary/explanation so that
    a non-empty value is propagated across the transport contract.
    """
    if not isinstance(contract, dict):
        return {}

    candidate = (
        contract.get("answer")
        or contract.get("content")
        or contract.get("response")
        or contract.get("summary")
        or contract.get("explanation")
        or ""
    )

    contract["answer"] = candidate
    contract["content"] = candidate
    contract["response"] = candidate

    if not contract.get("summary"):
        contract["summary"] = candidate

    if not contract.get("explanation"):
        contract["explanation"] = contract["summary"]

    return contract


def provider_contract_ready(machine_response):
    return machine_response


# =====================================================
# 🧠 ASSISTANT-AWARE PROVIDER ROUTING
# =====================================================

def build_provider_task_state(
    cognition=None,
    response_decision=None
):

    cognition = cognition or {}
    response_decision = response_decision or {}

    return {
        "assistant_next_step":
            cognition.get("assistant_next_step"),
        "task_understanding":
            cognition.get("task_understanding", {}),
        "scene_confidence":
            cognition.get("scene_confidence", 1.0),
        "clarification_required":
            response_decision.get(
                "task_requires_clarification",
                False
            ),
        "internal_reasoning_only":
            response_decision.get(
                "internal_reasoning_only",
                False
            )
    }


def sanitize_internal_reasoning(text):
    if not text:
        return ""
    blocked=[
        "possibly",
        "perhaps",
        "internal reasoning",
        "chain of thought",
        "I think",
        "I am reasoning"
    ]
    result=str(text)
    for item in blocked:
        result=result.replace(item,"")
    return result.strip()


# =====================================================
# PROVIDER RESPONSIBILITY — OPENAI REQUEST BUILDER
# Stage 2 COMPLETE
# Canonical MachineRequest -> Canonical OpenAI Request
# =====================================================

PROVIDER_MACHINE_SYSTEM_PROMPT = """
APRIL PROTOCOL

Role:
You are the Provider transport gateway.

Your only responsibility is to transform one MachineRequest into one MachineResponse.

Return exactly one JSON object.
The response MUST be valid JSON accepted by json.loads().

Never return:
- markdown
- code fences
- comments
- ellipsis (...)
- explanatory text before or after JSON

The JSON is a MachineResponse contract.

Required fields:
answer
summary
explanation
content
scene
artifacts
render_blocks
scene_plan
render_priority
confidence
metadata

Do not omit required fields.
Do not rename fields.
Do not invent new top-level fields.
"""


def build_openai_request(machine_request):
    """
    Stage 2:
    Convert one canonical MachineRequest into one canonical
    OpenAI Responses API request.
    """
    if not isinstance(machine_request, dict):
        machine_request = {}

    intent = machine_request.get("intent") or {}
    user_text = (
        intent.get("normalized_text")
        or intent.get("text")
        or machine_request.get("content")
        or ""
    )

    payload = {
        "goal": machine_request.get("goal"),
        "intent": {
            "type": intent.get("type"),
            "normalized_text": user_text,
        },
        "memory": machine_request.get("memory"),
        "visual_context": machine_request.get("visual_context"),
        "routing": machine_request.get("routing"),
        "response_decision": machine_request.get("response_decision"),
        "renderer_preferences": machine_request.get("renderer_preferences"),
    }

    provider_log("========== MACHINE REQUEST ==========")
    provider_log(json.dumps(payload, ensure_ascii=False)[:8000])

    structured_prompt = (
        "APRIL MACHINE REQUEST\n\n"
        "Transform the following MachineRequest into exactly one MachineResponse.\n"
        "Follow the APRIL protocol exactly.\n\n"
        f"GOAL:\n{json.dumps(payload.get('goal'), ensure_ascii=False)}\n\n"
        f"SEMANTIC:\n{json.dumps(payload.get('intent'), ensure_ascii=False)}\n\n"
        f"MEMORY:\n{json.dumps(payload.get('memory'), ensure_ascii=False)}\n\n"
        f"VISUAL_CONTEXT:\n{json.dumps(payload.get('visual_context'), ensure_ascii=False)}\n\n"
        f"ROUTING:\n{json.dumps(payload.get('routing'), ensure_ascii=False)}\n\n"
        f"RESPONSE_DECISION:\n{json.dumps(payload.get('response_decision'), ensure_ascii=False)}\n\n"
        f"RENDERER:\n{json.dumps(payload.get('renderer_preferences'), ensure_ascii=False)}\n\n"
        "Output format: MachineResponse only. No markdown. No explanations."
    )

    return {
        "role": "user",
        "content": [{
            "type": "input_text",
            "text": structured_prompt
        }]
    }



def machine_request_to_dict(machine_request):
    """Convert canonical MachineRequest object to provider payload."""
    if isinstance(machine_request, dict):
        return machine_request
    if isinstance(machine_request, MachineRequest):
        return {
            "goal": getattr(machine_request, "goal", None),
            "intent": getattr(machine_request, "intent", None),
            "memory": getattr(machine_request, "memory", None),
            "visual_context": getattr(machine_request, "visual_context", None),
            "routing": getattr(machine_request, "routing", None),
            "response_decision": getattr(machine_request, "response_decision", None),
            "renderer_preferences": getattr(machine_request, "renderer_preferences", None),
            "metadata": getattr(machine_request, "metadata", None),
        }
    raise TypeError("Provider accepts only canonical MachineRequest.")


def normalize_provider_input(machine_request):
    """Build canonical OpenAI request from MachineRequest only."""
    system_item = {
        "role": "system",
        "content": [
            {
                "type": "input_text",
                "text": PROVIDER_MACHINE_SYSTEM_PROMPT,
            }
        ],
    }

    payload = machine_request_to_dict(machine_request)
    return [system_item, build_openai_request(payload)]

# =====================================================
# STAGE 3 - UNIFIED PROVIDER CONTRACT
# =====================================================

# =====================================================
# PROVIDER RESPONSIBILITY — OPENAI RESPONSE TRANSLATOR
# STAGE 3 COMPLETE
# Provider is the single OpenAI→April translator.
# Every provider response leaves this file only as a
# validated canonical MachineResponse for the Executor.
# =====================================================



def recover_machine_contract(contract):
    """Recover a partial MachineResponse into a canonical contract."""
    if not isinstance(contract, dict):
        contract = {}
    candidate = (
        contract.get("answer")
        or contract.get("content")
        or contract.get("response")
        or contract.get("summary")
        or contract.get("explanation")
        or ""
    )
    contract["answer"] = candidate
    contract["content"] = candidate
    contract["response"] = candidate
    contract.setdefault("summary", candidate)
    contract.setdefault("explanation", contract["summary"])
    contract.setdefault("scene", {})
    contract.setdefault("artifacts", [])
    contract.setdefault("render_blocks", [])
    contract.setdefault("scene_plan", ["text"])
    contract.setdefault("render_priority", ["text"])
    contract.setdefault("metadata", {})
    if candidate and not any(isinstance(b, dict) and b.get("type")=="text" for b in contract["render_blocks"]):
        contract["render_blocks"].insert(0,{
            "type":"text",
            "content":candidate,
            "scene_contract":True
        })
    contract["metadata"]["contract_recovered"]=True
    return contract

def create_provider_contract(raw_text):
    """Stage 3: translate every OpenAI response into one canonical MachineResponse."""

    if (
        isinstance(raw_text, dict)
        and raw_text.get("type") == "provider_response"
        and isinstance(raw_text.get("machine_response"), dict)
    ):
        provider_log("🧠 STAGE3: canonical MachineResponse received")
        return provider_contract_ready(raw_text)

    parsed = raw_text if isinstance(raw_text, dict) else parse_provider_machine_contract(raw_text)
    parsed = validate_machine_response_contract(parsed)
    parsed = ensure_scene_first_contract(parsed)
    parsed = normalize_text_transport(parsed)
    parsed = recover_machine_contract(parsed)

    machine = build_provider_machine_response(raw_text, parsed)

    return provider_finalize_for_executor(machine)




def enrich_machine_response(contract):
    """
    Normalize fields expected by Executor.
    """
    mr = contract.setdefault("machine_response", {})

    content = mr.get("content") or mr.get("answer") or mr.get("summary") or ""
    if isinstance(content, dict):
        if isinstance(content.get("text"), str):
            mr["answer"] = content["text"]
        elif isinstance(content.get("answer"), str):
            mr["answer"] = content["answer"]
        elif isinstance(content.get("summary"), str):
            mr["answer"] = content["summary"]
        else:
            mr.setdefault("answer","")
    else:
        mr.setdefault("answer", content)
    mr["content"] = content
    mr.setdefault("summary", content[:500] if isinstance(content, str) else "")
    mr.setdefault("scene", {})
    mr.setdefault("render_blocks", [])
    mr.setdefault("artifacts", [])
    mr.setdefault("scene_plan", ["text"])
    mr.setdefault("render_priority", ["text"])
    mr.setdefault("metadata", {})
    return contract



def infer_executor_rendering(machine_response):
    """
    Provider validates transport only.
    Executor decides rendering.
    """
    mr = machine_response.setdefault("machine_response", {})
    mr.setdefault("render_blocks", [])
    mr.setdefault("scene_plan", ["text"])
    mr.setdefault("render_priority", ["text"])
    return machine_response



def detect_executor_artifacts(machine_response):
    """
    Stage 3:
    Normalize artifacts and ensure a canonical text block exists.
    """
    mr = machine_response.setdefault("machine_response", {})
    render_blocks = mr.setdefault("render_blocks", [])
    artifacts = mr.setdefault("artifacts", [])
    metadata = mr.setdefault("metadata", {})

    answer = (
        mr.get("answer")
        or mr.get("content")
        or mr.get("summary")
        or ""
    )

    if answer and not any(
        isinstance(b, dict) and b.get("type") == "text"
        for b in render_blocks
    ):
        render_blocks.insert(0, {
            "type": "text",
            "content": answer,
            "scene_contract": True,
        })

    metadata["provider_stage"] = "stage3"
    metadata["artifact_count"] = len(artifacts)
    metadata["render_block_count"] = len(render_blocks)

    return machine_response

    render_blocks = mr.setdefault("render_blocks", [])
    artifacts = mr.setdefault("artifacts", [])
    metadata = mr.setdefault("metadata", {})

    mapping = {
        "table":"table",
        "graph":"graph",
        "knowledge_graph":"knowledge_graph",
        "relation_graph":"relation_graph",
        "relations":"relations",
        "gallery":"gallery",
        "image":"image",
        "images":"gallery",
        "diagram":"diagram",
        "scene":"scene",
        "layout":"layout",
        "visual":"visual",
        "renderer_scene":"renderer_scene",
        "code":"code",
        "formula":"formula",
        "function":"function",
        "markdown":"markdown",
        "text":"text",
        "link":"link",
        "links":"link",
    }

    for key, block_type in mapping.items():
        if key not in content:
            continue
        payload = content[key]
        block={"type":block_type}
        if block_type=="text":
            block["content"]=payload
        elif block_type=="table" and isinstance(payload,dict):
            block.update(payload)
        elif block_type=="gallery":
            block["images"]=payload
        elif block_type=="image":
            block["url"]=payload
        elif block_type=="code":
            block["content"]=payload
        elif block_type=="link":
            block["links"]=payload
        else:
            block["payload"]=payload
        render_blocks.append(block)
        artifacts.append({
            "type": block_type,
            "payload": payload
        })
        if key in ("link","links"):
            metadata["links"] = payload

    if mr.get("answer"):
        if not any(b.get("type")=="text" for b in render_blocks):
            render_blocks.insert(0,{
                "type":"text",
                "content":mr["answer"]
            })

    return machine_response




# =====================================================
# STAGE 2 - EXECUTOR HANDOFF
# =====================================================

def provider_finalize_for_executor(contract):
    """
    Canonical Provider -> Executor bridge.
    Ensures the payload is normalized before leaving Provider.
    """
    contract = enrich_machine_response(contract)
    contract = infer_executor_rendering(contract)
    contract = detect_executor_artifacts(contract)
    return contract



# =====================================================
# STAGE 4 - PROVIDER AUDIT
# =====================================================

def provider_transport_audit(machine_response):
    """
    Final verification before handing off to Executor.
    """
    mr = machine_response.setdefault("machine_response", {})
    audit = {
        "answer_length": len(mr.get("answer") or ""),
        "content_length": len(mr.get("content") or ""),
        "summary_length": len(mr.get("summary") or ""),
        "artifact_count": len(mr.get("artifacts", []) or []),
        "render_block_count": len(mr.get("render_blocks", []) or []),
        "scene_valid": isinstance(mr.get("scene"), dict),
    }
    mr.setdefault("metadata", {})["provider_audit"] = audit
    provider_log(f"PROVIDER AUDIT: {audit}")
    return machine_response


def finalize_executor_contract(machine_response):
    """Canonical Provider -> Executor transport pipeline. Provider validates only; Executor owns scene construction."""
    for step in (
        enrich_machine_response,
        infer_executor_rendering,
        detect_executor_artifacts,
        provider_transport_audit,
    ):
        machine_response = step(machine_response)
    return machine_response


def build_provider_overload_contract(space):
    raise RuntimeError(f"Provider route failed: {space}")


# =====================================================
# 🔥 TEXT GENERATION
# =====================================================

# =====================================================
# PROVIDER ROUTE
# Canonical flow:
# MachineRequest -> OpenAI -> MachineResponse -> Executor
# =====================================================


# =====================================================
# STAGE 4 - CPU PHASE GUARD
# =====================================================

def provider_should_bypass_openai(messages):
    """
    Detect post-provider execution phases.
    Returns (bypass, payload).
    """
    phase = None

    if isinstance(messages, dict):
        phase = messages.get("execution_phase")
    else:
        phase = getattr(messages, "execution_phase", None)

    if phase in ("POST_PROVIDER", "POST_REASONING", "SCENE_READY"):
        provider_log(f"CPU ROUTE GUARD: bypass OpenAI (phase={phase})")
        return True, {
            "type": "provider_cpu_redirect",
            "execution_phase": phase,
            "provider_bypassed": True,
        }

    return False, None



async def generate_text(

    messages,
    temperature=0.7,
    max_output_tokens=700,
    model="gpt-4o-mini"
):

    provider_enter(
        "openai_text",
        messages
    )

    # Legacy messages[] route removed.
    # Only canonical MachineRequest is accepted beyond this point.

    bypass, payload = provider_should_bypass_openai(messages)
    if bypass:
        provider_exit("cpu_redirect", True)
        payload["executor_cpu_redirect"] = True
        payload["route_target"] = "executor_cpu"
        payload["next_stage"] = "EXECUTOR_CPU"

        # Stage 9: preserve transport information for Executor CPU.
        if isinstance(messages, dict):
            payload["machine_response"] = messages.get("machine_response")
            payload["trace_id"] = messages.get("trace_id")
            payload["fiber_pass"] = messages.get("fiber_pass", 2)
        else:
            payload["machine_response"] = getattr(messages, "machine_response", None)
            payload["trace_id"] = getattr(messages, "trace_id", None)
            payload["fiber_pass"] = getattr(messages, "fiber_pass", 2)

        return payload


    try:

        update_provider_behavior()

        provider_log(
            "🧠 OPENAI TEXT START"
        )

        provider_log(
            "========== PROVIDER INPUT =========="
        )
        provider_log("RAW MESSAGE TYPE:", type(messages))
        provider_log("RAW MESSAGE:", str(messages)[:4000])

        provider_log(
            "🧠 PROVIDER BALANCE:",
            provider_state.get(
                "provider_balance"
            )
        )

        normalized_input = normalize_provider_input(messages)

        provider_log("========== OPENAI REQUEST BUILDER ==========")
        provider_log(json.dumps(normalized_input, ensure_ascii=False)[:8000])

        response = (

            openai_client.responses.create(

                model=model,

                input=normalized_input,

                temperature=temperature,

                max_output_tokens=max_output_tokens
            )
        )

        provider_log("========== RAW OPENAI OUTPUT ==========")
        provider_log(response.output_text[:8000] if response.output_text else "EMPTY")

        text = normalize_response_text(

            response.output_text
            if response.output_text
            else ""
        )

        if not text:

            provider_log(
                "🔥 OPENAI EMPTY RESPONSE"
            )

            provider_exit(
                "openai_text",
                False
            )

            raise RuntimeError("Provider returned empty response")

        provider_log(
            "🧠 OPENAI TEXT SUCCESS"
        )

        provider_exit(
            "openai_text",
            True
        )

        contract = create_provider_contract(text)
        return contract

    except Exception as e:

        provider_log(
            "🔥 OPENAI TEXT ERROR:",
            e
        )

        provider_exit(
            "openai_text",
            False
        )

        raise


# =====================================================
# 🔥 VOICE TRANSCRIPTION
# =====================================================

async def transcribe_voice(
    file_path
):

    provider_enter(
        "voice_transcription",
        file_path
    )

    try:

        provider_log(
            "🧠 OPENAI VOICE START"
        )

        provider_log(
            "🧠 OPENAI AUDIO PATH:",
            file_path
        )

        with open(file_path, "rb") as f:

            transcript = (

                openai_client.audio.transcriptions.create(

                    model="gpt-4o-mini-transcribe",

                    file=f
                )
            )

        text = normalize_response_text(

            transcript.text
            if transcript.text
            else ""
        )

        provider_log(
            "🧠 OPENAI VOICE RESPONSE:",
            text[:120] if text else "EMPTY"
        )

        if text:

            provider_log(
                "🧠 OPENAI VOICE SUCCESS"
            )

            provider_exit(
                "voice_transcription",
                True
            )

            # Voice pipeline must return the recognized text itself.
            # checkout_server.normalize_voice_transcript() expects a plain
            # transcript (or a simple text field), not a provider wrapper.
            return text

        provider_exit(
            "voice_transcription",
            False
        )

        return ""

    except Exception as e:

        provider_log(
            "🔥 OPENAI VOICE ERROR:",
            e
        )

        provider_exit(
            "voice_transcription",
            False
        )

        return ""


# =====================================================
# 🔥 IMAGE ANALYSIS
# =====================================================

async def analyze_image(
    path,
    prompt
):

    provider_enter(
        "image_analysis",
        path
    )

    update_provider_behavior()

    # =================================================
    # 🔥 GEMINI VISUAL PRIMARY
    # =====================================================

    if should_restore_gemini():

        try:

            provider_log(
                "🧠 GEMINI IMAGE START"
            )

            provider_log(
                "🧠 VISUAL MODE:",
                provider_state.get(
                    "visual_mode"
                )
            )

            provider_log(
                "🧠 GEMINI IMAGE PATH:",
                path
            )

            uploaded = gemini_client.files.upload(
                file=path
            )

            provider_log(
                "🧠 GEMINI IMAGE UPLOADED"
            )

            response = (

                gemini_client.models.generate_content(

                    model="gemini-2.5-flash",

                    contents=[
                        uploaded,
                        prompt
                    ]
                )
            )

            text = normalize_response_text(

                response.text
                if response.text
                else ""
            )

            provider_log(
                "🧠 GEMINI IMAGE RESPONSE:",
                text[:120] if text else "EMPTY"
            )

            if text:

                mark_gemini_success()

                provider_exit(
                    "gemini_image",
                    True
                )

                return create_provider_contract(text)

        except Exception as e:

            provider_log(
                "🔥 GEMINI IMAGE ERROR:",
                e
            )

            mark_gemini_failure()

    # =================================================
    # 🔥 OPENAI VISUAL FALLBACK
    # =====================================================

    try:

        provider_log(
            "OPENAI IMAGE ROUTE"
        )

        provider_log(
            "🧠 FALLBACK PRESSURE:",
            provider_state.get(
                "route_health"
            )
        )

        with open(path, "rb") as image_file:

            response = (

                openai_client.responses.create(

                    model="gpt-4o-mini",

                    input=[

                        {
                            "role": "user",

                            "content": [

                                {
                                    "type": "input_text",

                                    "text": prompt
                                },

                                {
                                    "type": "input_image",

                                    "image":
                                        image_file.read()
                                }
                            ]
                        }
                    ],

                    max_output_tokens=250
                )
            )

        text = normalize_response_text(

            response.output_text
            if response.output_text
            else ""
        )

        if text:

            provider_exit(
                "openai_image",
                True
            )

            return create_provider_contract(text)

        provider_exit(
            "openai_image",
            False
        )

        raise RuntimeError("Visual provider route failed")

    except Exception as e:

        provider_log(
            "🔥 OPENAI IMAGE ERROR:",
            e
        )

        provider_exit(
            "openai_image",
            False
        )

        raise RuntimeError("Visual provider route failed")


PROVIDER_ROUTE_VERSION="fiber_scene_v4"
PROVIDER_LEGACY_MODE=False
