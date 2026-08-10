
# =====================================================
# STAGE 3 - FULL RESPONSE PRESERVATION
# =====================================================

def provider_preserve_full_response(data):
    if not isinstance(data, dict):
        return {"content": str(data), "_provider_payload": data}

    if "_provider_payload" not in data:
        data["_provider_payload"] = dict(data)

    data.setdefault("provider_raw", data["_provider_payload"])
    data.setdefault("processor_input", data["_provider_payload"])
    return data


# =====================================================
# STAGE 2 - CANONICAL CONTRACT
# =====================================================

CANONICAL_PROVIDER_TEXT_FIELD = "content"

def provider_canonicalize_contract(data):
    """
    Stage 1:
    Preserve semantic fields. Do not overwrite answer/content/summary.
    Only ensure the transport aliases exist.
    """
    if not isinstance(data, dict):
        data = {CANONICAL_PROVIDER_TEXT_FIELD: str(data)}

    if "content" not in data and "answer" in data:
        data["content"] = data["answer"]
    elif "answer" not in data and "content" in data:
        data["answer"] = data["content"]

    for key in ("text", "message", "output_text"):
        if key not in data:
            if "content" in data:
                data[key] = data["content"]
            elif "answer" in data:
                data[key] = data["answer"]

    return data


# =====================================================
# STAGE 1D - PROVIDER NORMALIZER
# =====================================================

def provider_normalize_contract(data):
    if not isinstance(data, dict):
        data = {"answer": str(data), "content": str(data)}
    data.setdefault("scene", {})
    data.setdefault("render_blocks", [])
    data.setdefault("artifacts", [])
    data.setdefault("summary", data.get("answer", data.get("content","")))
    return data


# =====================================================
# STAGE 1C - PROVIDER VALIDATOR
# =====================================================

def provider_validate_contract(data):
    if not isinstance(data, dict):
        return {"answer": str(data), "content": str(data)}
    if "answer" not in data and "content" in data:
        data["answer"]=data["content"]
    if "content" not in data and "answer" in data:
        data["content"]=data["answer"]
    return data

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
# OPENAI MODEL CONFIGURATION
# =====================================================

# COST POLICY — April text generation is Luna-only.
# Sol/Terra switching is disabled in this router.
OPENAI_PRIMARY_MODEL = "gpt-5.6-luna"
OPENAI_BALANCED_MODEL = "gpt-5.6-luna"
OPENAI_FAST_MODEL = "gpt-5.6-luna"
OPENAI_PREMIUM_MODEL = "gpt-5.6-luna"

PROVIDER_DUPLICATE_TTL_SECONDS = 90
PROVIDER_COST_LOG_VERSION = "cost_guard_v3"



# =====================================================
# 🔥 SAFE PATCH MODE
# =====================================================

PROVIDER_PATCH_LOG = []

# Short-lived idempotency cache. It is keyed only by an explicit flow/trace id,
# so two genuinely separate user requests are never collapsed together.
_PROVIDER_CALL_CACHE = {}


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


# =====================================================
# 💰 COST / ROUTING GUARDS
# =====================================================

def _safe_text(value):
    return value if isinstance(value, str) else (str(value) if value is not None else "")


def _extract_request_text(machine_request):
    """Return only the current user request text, never the whole history."""
    if isinstance(machine_request, dict):
        intent = machine_request.get("intent") or {}
        if isinstance(intent, dict):
            for key in ("normalized_text", "text", "query", "content"):
                value = intent.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        for key in ("content", "text", "query", "user_text"):
            value = machine_request.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    else:
        intent = getattr(machine_request, "intent", None)
        if isinstance(intent, dict):
            for key in ("normalized_text", "text", "query", "content"):
                value = intent.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        for key in ("content", "text", "query", "user_text"):
            value = getattr(machine_request, key, None)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _count_explicit_questions(text):
    """Count actual question marks in the CURRENT request.

    We intentionally do not infer question count from conversation history,
    commas, context size, or the number of requested renderers. This prevents
    expensive-model selection merely because the conversation is long.
    """
    if not text:
        return 0
    normalized = text.replace("？", "?")
    return normalized.count("?")


def _select_cost_model(machine_request, requested_model=None):
    """Luna only. No provider-side model escalation."""
    current_text = _extract_request_text(machine_request)
    question_count = _count_explicit_questions(current_text)
    selected = OPENAI_PRIMARY_MODEL
    tier = "LUNA_ONLY"

    provider_log({
        "cost_policy": PROVIDER_COST_LOG_VERSION,
        "requested_model": requested_model,
        "selected_model": selected,
        "tier": tier,
        "question_count": question_count,
        "current_request_chars": len(current_text),
        "model_escalation_disabled": True,
    })
    return selected, question_count, tier


def _request_identity(machine_request):
    """Return (flow_id, fingerprint) for safe same-flow duplicate suppression."""
    if isinstance(machine_request, dict):
        metadata = machine_request.get("metadata") or {}
        flow_id = (
            machine_request.get("flow_id")
            or machine_request.get("trace_id")
            or metadata.get("flow_id")
            or metadata.get("trace_id")
        )
    else:
        metadata = getattr(machine_request, "metadata", {}) or {}
        flow_id = (
            getattr(machine_request, "flow_id", None)
            or getattr(machine_request, "trace_id", None)
            or metadata.get("flow_id")
            or metadata.get("trace_id") if isinstance(metadata, dict) else None
        )
    if not flow_id:
        return None, None
    try:
        payload = machine_request_to_dict(machine_request)
        # Avoid fingerprinting volatile transport metadata.
        payload = dict(payload)
        payload.pop("metadata", None)
        payload.pop("trace_id", None)
        payload.pop("flow_id", None)
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        raw = repr(machine_request)
    import hashlib
    fingerprint = hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()
    return str(flow_id), fingerprint


def _get_duplicate_cached_response(machine_request):
    flow_id, fingerprint = _request_identity(machine_request)
    if not flow_id or not fingerprint:
        return None
    entry = _PROVIDER_CALL_CACHE.get(flow_id)
    if not entry:
        return None
    if time.time() - entry.get("ts", 0) > PROVIDER_DUPLICATE_TTL_SECONDS:
        _PROVIDER_CALL_CACHE.pop(flow_id, None)
        return None
    if entry.get("fingerprint") != fingerprint:
        return None
    provider_log({
        "duplicate_guard": "HIT",
        "flow_id": flow_id,
        "age_seconds": round(time.time() - entry.get("ts", 0), 3),
        "openai_call_skipped": True,
    })
    return copy.deepcopy(entry.get("response"))


def _cache_provider_response(machine_request, response):
    flow_id, fingerprint = _request_identity(machine_request)
    if not flow_id or not fingerprint:
        return
    _PROVIDER_CALL_CACHE[flow_id] = {
        "ts": time.time(),
        "fingerprint": fingerprint,
        "response": copy.deepcopy(response),
    }
    # Keep this cache bounded.
    now = time.time()
    for key, entry in list(_PROVIDER_CALL_CACHE.items()):
        if now - entry.get("ts", 0) > PROVIDER_DUPLICATE_TTL_SECONDS:
            _PROVIDER_CALL_CACHE.pop(key, None)


def _extract_usage(response):
    usage = getattr(response, "usage", None)
    if usage is None:
        return {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    def read(obj, name, default=0):
        value = getattr(obj, name, None)
        if value is None and isinstance(obj, dict):
            value = obj.get(name, default)
        return value if isinstance(value, (int, float)) else default
    input_tokens = read(usage, "input_tokens")
    output_tokens = read(usage, "output_tokens")
    total_tokens = read(usage, "total_tokens", input_tokens + output_tokens)
    details = getattr(usage, "input_tokens_details", None)
    cached = read(details, "cached_tokens") if details is not None else 0
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached,
        "uncached_input_tokens": max(0, input_tokens - cached),
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


# Standard API rates per 1M tokens. These are used only for telemetry; the
# provider remains the source of truth for the actual billed amount.
_MODEL_PRICING_PER_MTOK = {
    OPENAI_PRIMARY_MODEL: {"input": 1.00, "cached_input": 0.10, "output": 6.00},
}


def _estimate_usage_cost(model, usage):
    rates = _MODEL_PRICING_PER_MTOK.get(model)
    if not rates:
        return None
    uncached = usage.get("uncached_input_tokens", 0)
    cached = usage.get("cached_input_tokens", 0)
    output = usage.get("output_tokens", 0)
    return round(
        (uncached / 1_000_000) * rates["input"]
        + (cached / 1_000_000) * rates["cached_input"]
        + (output / 1_000_000) * rates["output"],
        8,
    )

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

def build_provider_machine_response(text, parsed_contract=None, source_request=None):
    """Build a unified MachineResponse transport contract."""
    parsed_contract = parsed_contract or {}

    fallback = normalize_response_text(text)

    answer = (
        parsed_contract.get("answer")
        or parsed_contract.get("content")
        or parsed_contract.get("response")
        or fallback
    )

    content = (
        parsed_contract.get("content")
        or answer
    )

    response = (
        parsed_contract.get("response")
        or answer
    )

    summary = (
        parsed_contract.get("summary")
        or provider_compact_summary(answer, parsed_contract)
    )

    explanation = (
        parsed_contract.get("explanation")
        or summary
        or provider_compact_summary(answer, parsed_contract)
    )
    if response is None:
        response = answer

    processor_input = {}
    execution_round = 1
    execution_phase = "FIRST_CIRCLE"
    if isinstance(source_request, dict):
        try:
            processor_input = copy.deepcopy(source_request)
        except Exception:
            processor_input = dict(source_request)
        execution_round = source_request.get("execution_round", execution_round) or execution_round
        execution_phase = source_request.get("execution_phase", execution_phase) or execution_phase

    machine = {
        "type": "provider_response",
        "execution_round": execution_round,
        "execution_phase": execution_phase,
        "processor_input": processor_input,
        "provider_source_request": processor_input,
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
            "transport_contract": "scene_first",
            "execution_round": execution_round,
            "execution_phase": execution_phase,
        }
    }

    if processor_input:
        machine["machine_response"]["metadata"].setdefault("processor_input", processor_input)
        machine["machine_response"]["metadata"].setdefault("provider_source_request", processor_input)
        machine["machine_response"]["metadata"].setdefault("provider_first_circle", True)
        machine["machine_response"]["metadata"].setdefault("second_circle_ready", True)
        machine["machine_response"]["metadata"].setdefault("execution_round", execution_round)
        machine["machine_response"]["metadata"].setdefault("execution_phase", execution_phase)

    return machine

import copy
import json
from blocks.C_ARTIFACT_CONTRACT import MachineRequest



# =====================================================
# STAGE 1B - PROVIDER DECODER PIPELINE
# =====================================================

def provider_decode_json(raw_text):
    try:
        import json
        data = json.loads(raw_text)
        if isinstance(data, dict):
            return data
    except Exception:
        return None
    return None

def provider_decode_response(raw_text):
    """
    Stage 1B:
    Canonical decoder pipeline.
    JSON -> legacy parser.
    Future stages will add semantic decoding here.
    """
    parsed = provider_decode_json(raw_text)
    if parsed is None:
        parsed = parse_provider_machine_contract(raw_text)
    parsed = provider_validate_contract(parsed)
    parsed = provider_normalize_contract(parsed)
    parsed = provider_canonicalize_contract(parsed)
    parsed = provider_preserve_full_response(parsed)
    return parsed


def parse_provider_machine_contract(raw_text):
    """One local decode only. No second provider/model pass."""
    raw_text = raw_text if isinstance(raw_text, str) else str(raw_text or "")
    try:
        data=json.loads(raw_text)
        return data if isinstance(data,dict) else {}
    except Exception as exc:
        provider_log(f"PROVIDER JSON DECODE ERROR: {exc}")
        text=raw_text.strip()
        return {
            "answer":text,"content":text,"response":text,
            "summary":provider_compact_summary(text,{}),
            "explanation":"","scene":{},"artifacts":[],
            "render_blocks":[{"type":"text","content":text,"renderer":"TextBlock","viewer":"TextBlock","scene_contract":True}] if text else [],
            "scene_plan":["text"],"render_priority":["text"],
            "confidence":0.5,"metadata":{"provider_json_invalid":True}
        }

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
    Stage 2:
    Non-destructive transport normalization.
    Preserve semantic fields and only fill missing aliases.
    """
    if not isinstance(contract, dict):
        return {}

    candidate=(
        contract.get("answer")
        or contract.get("content")
        or contract.get("response")
        or contract.get("summary")
        or contract.get("explanation")
        or ""
    )

    contract.setdefault("answer", candidate)
    contract.setdefault("content", candidate)
    contract.setdefault("response", candidate)
    contract.setdefault("summary", candidate)
    contract.setdefault("explanation", contract.get("summary",""))

    return contract


def attach_processor_input(contract, source_request=None):
    """Preserve the second-circle input for the processor without sending it
    to OpenAI. The source request stays attached to the returned contract so
    the executor can reuse it for memory, history, and scene integration.
    """
    if not isinstance(contract, dict) or source_request is None:
        return contract

    try:
        cloned = copy.deepcopy(source_request)
    except Exception:
        cloned = source_request

    contract.setdefault("processor_input", cloned)
    contract.setdefault("provider_source_request", cloned)

    mr = contract.setdefault("machine_response", {})
    metadata = mr.setdefault("metadata", {})
    metadata.setdefault("processor_input", cloned)
    metadata.setdefault("provider_source_request", cloned)
    metadata.setdefault("provider_first_circle", True)
    metadata.setdefault("second_circle_ready", True)

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


def provider_compact_summary(answer, parsed_contract=None):
    """Provider-local summary; never depends on Executor helpers."""
    parsed_contract = parsed_contract if isinstance(parsed_contract, dict) else {}
    text = _safe_text(
        parsed_contract.get("provider_original_content")
        or parsed_contract.get("provider_original_answer")
        or parsed_contract.get("content")
        or parsed_contract.get("answer")
        or answer
    ).strip()
    if not text:
        return ""
    low=text.lower()
    kind="text"
    if re.search(r"\|.*\|\s*\n\s*\|?\s*[-:| ]+\|",text):
        kind="table"
    elif "```" in text or re.search(r"</?(html|script|style|div)\b",low):
        kind="code"
    elif re.search(r"https?://\S+",text):
        kind="link"
    first=text.split("\n",1)[0].strip()
    if len(first)>110: first=first[:107]+"..."
    return f"{first} | scene: {kind}"

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

    # STAGE 2 - Compact Provider Payload
    memory = machine_request.get("memory") or {}
    visual = machine_request.get("visual_context") or {}

    payload = {
        "goal": machine_request.get("goal"),
        "intent": {
            "type": intent.get("type"),
            "normalized_text": user_text,
        },
        "conversation": machine_request.get("conversation"),
        "memory": memory,
        "visual_context": visual,
        "available_tools": machine_request.get("available_tools"),
        "requested_outputs": machine_request.get("requested_outputs"),
        "required_competencies": machine_request.get("required_competencies"),
        "required_artifacts": machine_request.get("required_artifacts"),
        "routing": machine_request.get("routing"),
        "constraints": machine_request.get("constraints"),
    }

    def _meaningful(value):
        if value is None:
            return False
        if value == "":
            return False
        if value == {}:
            return False
        if value == []:
            return False
        return True

    payload = {k: v for k, v in payload.items() if _meaningful(v)}

    provider_log("========== MACHINE REQUEST ==========")
    provider_log(json.dumps(payload, ensure_ascii=False)[:8000])

    # Always include the canonical MachineRequest payload for normal text requests.
    # A minimal prompt causes the model to answer about the protocol itself.
    sections=[]
    order=[
        ("goal","GOAL"),
        ("intent","SEMANTIC"),
        ("memory","MEMORY"),
        ("conversation","CONVERSATION"),
        ("visual_context","VISUAL_CONTEXT"),
        ("available_tools","AVAILABLE_TOOLS"),
        ("requested_outputs","REQUESTED_OUTPUTS"),
        ("required_competencies","REQUIRED_COMPETENCIES"),
        ("required_artifacts","REQUIRED_ARTIFACTS"),
        ("routing","ROUTING"),
        ("constraints","CONSTRAINTS"),
    ]
    for key,title in order:
        if key in payload:
            sections.append(f"{title}:\n{json.dumps(payload[key], ensure_ascii=False)}\n")

    structured_prompt=(
        "APRIL MACHINE REQUEST\n\n"
        "Transform the following MachineRequest into exactly one MachineResponse.\n"
        "Follow the APRIL protocol exactly.\n\n"
        + "\n".join(sections)
        + "\nOutput format: MachineResponse only. No markdown. No explanations."
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
            "conversation": getattr(machine_request, "conversation", None),
            "memory": getattr(machine_request, "memory", None),
            "visual_context": getattr(machine_request, "visual_context", None),
            "available_tools": getattr(machine_request, "available_tools", None),
            "requested_outputs": getattr(machine_request, "requested_outputs", None),
            "required_competencies": getattr(machine_request, "required_competencies", None),
            "required_artifacts": getattr(machine_request, "required_artifacts", None),
            "routing": getattr(machine_request, "routing", None),
            "constraints": getattr(machine_request, "constraints", None),
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
    contract.setdefault("answer", candidate)
    contract.setdefault("content", contract.get("answer", candidate))
    contract.setdefault("response", contract.get("answer", candidate))
    contract.setdefault("summary", provider_compact_summary(candidate, contract))
    contract.setdefault("explanation", contract["summary"])
    contract.setdefault("scene", {})
    contract.setdefault("artifacts", [])
    contract.setdefault("render_blocks", [])
    contract.setdefault("scene_plan", ["text"])
    contract.setdefault("render_priority", ["text"])
    contract.setdefault("metadata", {})
    if candidate and not any(isinstance(b, dict) and b.get("type")=="text" for b in contract["render_blocks"]):
        pass  # inserted to preserve valid Python block
        # STAGE2: legacy automatic TextBlock injection disabled.
        # contract["render_blocks"].insert(0,{
#             "type":"text",
#             "content":candidate,
#             "scene_contract":True
#         })
    # STAGE1 LEGACY: automatic recovery path retained for compatibility.
    contract["metadata"]["contract_recovered"]=True
    contract["metadata"]["transport_stage"]="provider_stage2"
    return contract

def create_provider_contract(raw_text, source_request=None):
    """Stage 3: translate every OpenAI response into one canonical MachineResponse.
    Stage 1 upgrade: avoid repeated normalization and preserve canonical transport."""

    if (
        isinstance(raw_text, dict)
        and raw_text.get("type") == "provider_response"
        and isinstance(raw_text.get("machine_response"), dict)
    ):
        provider_log("🧠 STAGE3: canonical MachineResponse received")
        return provider_contract_ready(raw_text)

    parsed = raw_text if isinstance(raw_text, dict) else provider_decode_response(raw_text)
    # STAGE 1: single canonical validation pass
    # STAGE3: semantic-first pipeline
    parsed = ensure_scene_first_contract(parsed)
    parsed = normalize_text_transport(parsed)
    # Legacy recovery kept temporarily for compatibility.
    # STAGE4: compatibility recovery bypassed.
    parsed = recover_machine_contract(parsed)

    # STAGE 3: build one canonical provider response then perform a single executor handoff
    # STAGE4: canonical builder becomes the single assembly point.
    machine = build_provider_machine_response(raw_text, parsed, source_request=source_request)

    mr = machine.setdefault("machine_response", {})
    if mr.get("answer"):
        mr["provider_original_answer"] = mr["answer"]
        mr["provider_original_content"] = mr.get("content", mr["answer"])
    elif mr.get("content"):
        mr["provider_original_content"] = mr["content"]

    candidate = (
        mr.get("answer")
        or mr.get("content")
        or mr.get("response")
        or mr.get("summary")
        or ""
    )
    if candidate:
        mr.setdefault("answer", candidate)
        mr.setdefault("content", candidate)
        mr.setdefault("response", candidate)
        mr["summary"] = mr.get("summary") or provider_compact_summary(candidate, mr)

    # STAGE4: executor handoff preserved.
    machine = provider_finalize_for_executor(machine)
    machine = attach_processor_input(machine, source_request)
    return machine


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
        pass  # preserve empty branch after legacy removal
        # STAGE2: legacy automatic executor TextBlock injection disabled.
        # render_blocks.insert(0, {
#             "type": "text",
#             "content": answer,
#             "scene_contract": True,
#         })

    # STAGE1 LEGACY: automatic TextBlock injection will be removed in Stage2.
    metadata["provider_stage"] = "stage3"
    metadata["canonical_handoff"] = True
    metadata["artifact_count"] = len(artifacts)
    metadata["render_block_count"] = len(render_blocks)

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

    mr = contract.setdefault("machine_response", {})
    candidate = (
        mr.get("answer")
        or mr.get("content")
        or mr.get("response")
        or mr.get("summary")
        or mr.get("explanation")
        or mr.get("provider_original_answer")
        or mr.get("provider_original_content")
        or ""
    )

    if candidate:
        mr["answer"] = candidate
        mr["content"] = candidate
        mr["response"] = candidate
        mr["summary"] = mr.get("summary") or provider_compact_summary(candidate, mr)

        blocks = mr.setdefault("render_blocks", [])
        if not any(isinstance(b, dict) and b.get("type") == "text" for b in blocks):
            blocks.insert(0, {
                "type": "text",
                "content": candidate,
                "scene_contract": True,
            })

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
    """Stage 4: final canonical Provider -> Executor transport pipeline.
    This is the single validated handoff to the Executor."""
    # Stage 4: execute one ordered canonical transport pipeline.
    for step in (
        enrich_machine_response,
        infer_executor_rendering,
        detect_executor_artifacts,
        provider_transport_audit,
    ):
        machine_response = step(machine_response)
    return machine_response



def provider_final_guard(contract):
    """
    Final protection before Executor.
    Prevents valid text responses from becoming empty contracts.
    """
    mr = contract.setdefault("machine_response", {})

    candidate = (
        mr.get("answer")
        or mr.get("content")
        or mr.get("response")
        or mr.get("summary")
        or mr.get("explanation")
        or mr.get("provider_original_answer")
        or mr.get("provider_original_content")
        or ""
    )

    original = mr.get("provider_original_answer") or mr.get("provider_original_content")
    if candidate.startswith("Не удалось сформировать ответ") and original:
        candidate = original

    if candidate:
        mr["answer"] = candidate
        mr["content"] = candidate
        mr["response"] = candidate
        mr["summary"] = mr.get("summary") or provider_compact_summary(candidate, mr)

        blocks = mr.setdefault("render_blocks", [])
        if not any(isinstance(b, dict) and b.get("type") == "text" for b in blocks):
            blocks.insert(0, {
                "type": "text",
                "content": candidate,
                "scene_contract": True,
            })

    return contract


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




def provider_stage_log(stage, payload=None):
    try:
        if isinstance(payload, dict):
            info={}
            for k,v in payload.items():
                if isinstance(v,str):
                    info[k]=f"<str:{len(v)}>"
                elif isinstance(v,(list,dict)):
                    info[k]=f"<{type(v).__name__}:{len(v)}>"
                else:
                    info[k]=v
            provider_log(f"[PROVIDER:{stage}] {info}")
        else:
            provider_log(f"[PROVIDER:{stage}] {payload}")
    except Exception:
        pass

async def generate_text(

    messages,
    temperature=0.7,
    max_output_tokens=None,
    model=OPENAI_PRIMARY_MODEL
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

        # Canonical source request is captured once and reused throughout the route.
        source_request = machine_request_to_dict(messages)

        duplicate = _get_duplicate_cached_response(messages)
        if duplicate is not None:
            provider_exit("openai_text_duplicate_guard", True)
            return duplicate

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

        provider_stage_log("INPUT", {"type":type(messages).__name__})
        normalized_input = normalize_provider_input(messages)
        provider_stage_log("OPENAI_REQUEST", {"items":len(normalized_input)})

        provider_log("========== OPENAI REQUEST BUILDER ==========")
        provider_log(json.dumps(normalized_input, ensure_ascii=False)[:8000])

        selected_model, question_count, cost_tier = _select_cost_model(
            messages,
            requested_model=model,
        )

        # Respect the caller's output ceiling, but never allow an accidental
        # unbounded request. Terra is reserved for 5+ explicit questions and
        # gets a larger ceiling only when the caller explicitly provided one.
        safe_default_output = 1400 if cost_tier == "LUNA_DEFAULT" else 3000
        effective_max_output_tokens = (
            max_output_tokens
            if isinstance(max_output_tokens, int) and max_output_tokens > 0
            else safe_default_output
        )
        effective_max_output_tokens = min(
            effective_max_output_tokens,
            3200 if cost_tier == "TERRA_5PLUS_QUESTIONS" else 1800,
        )

        request = {
            "model": selected_model,
            "input": normalized_input,
            "max_output_tokens": effective_max_output_tokens,
        }

        # GPT-5.6 Responses API compatibility:
        # only legacy models receive temperature.
        legacy_temperature_models = {
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4.1",
            "gpt-4.1-mini",
        }

        if (
            temperature is not None
            and selected_model in legacy_temperature_models
        ):
            request["temperature"] = temperature

        provider_log({
            "provider_model_requested": model,
            "provider_model_selected": selected_model,
            "provider_tier": cost_tier,
            "question_count": question_count,
            "max_output_tokens": effective_max_output_tokens,
            "request_keys": list(request.keys()),
        })

        response = (
            openai_client.responses.create(
                **request
            )
        )

        usage = _extract_usage(response)
        estimated_cost_usd = _estimate_usage_cost(selected_model, usage)
        response_id = getattr(response, "id", None)
        provider_log({
            "billing_trace": PROVIDER_COST_LOG_VERSION,
            "response_id": response_id,
            "model_billed_route": selected_model,
            "usage": usage,
            "estimated_cost_usd": estimated_cost_usd,
            "cost_note": "estimate from model token rates; billing dashboard is authoritative",
        })

        provider_log("========== RAW OPENAI OUTPUT ==========")
        provider_log(response.output_text[:8000] if response.output_text else "EMPTY")

        raw_text = response.output_text or ""
        provider_stage_log("OPENAI_RESPONSE", {"chars":len(raw_text)})
        provider_log(f"OPENAI OUTPUT LENGTH: {len(raw_text)}")
        if hasattr(response,"incomplete_details"):
            provider_log(f"OPENAI INCOMPLETE: {response.incomplete_details}")

        provider_log("TRACE STAGE: raw_provider_output", raw_text[:300])

        if not raw_text:

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

        provider_log({"trace_stage":"before_create_provider_contract","raw_len":len(raw_text),"preview":raw_text[:300]})
        contract = create_provider_contract(raw_text, source_request=source_request)

        if isinstance(contract, dict):
            mr = contract.get("machine_response")
            if isinstance(mr, dict):
                for field in ("answer","content","summary","explanation","response"):
                    if isinstance(mr.get(field), str):
                        mr[field] = normalize_response_text(mr[field])
        provider_log({"trace_stage":"after_create_provider_contract","keys":list(contract.keys()) if isinstance(contract,dict) else str(type(contract))})

        # ================= TEST DIAGNOSTICS =================
        if isinstance(contract, dict):
            mr = contract.get("machine_response", {})
            provider_log("========== MACHINE RESPONSE DIAGNOSTICS ==========")
            provider_log({
                "answer_len": len(mr.get("answer") or ""),
                "content_len": len(mr.get("content") or ""),
                "summary_len": len(mr.get("summary") or ""),
                "artifact_count": len(mr.get("artifacts", [])),
                "render_block_count": len(mr.get("render_blocks", [])),
            })

            for i, artifact in enumerate(mr.get("artifacts", [])):
                if isinstance(artifact, dict):
                    atype = artifact.get("type")
                    if atype == "table":
                        provider_log(f"[TABLE #{i}] rows={len(artifact.get('rows', []))}")
                        provider_log(f"[TABLE #{i}] headers={artifact.get('headers', [])}")
                    elif atype == "graph":
                        provider_log(f"[GRAPH #{i}] series={len(artifact.get('series', []))}")
                    elif atype == "text":
                        provider_log(f"[TEXT #{i}] chars={len(artifact.get('content',''))}")

            provider_log("========== MACHINE RESPONSE SUMMARY ==========")
            provider_log({
                "fields": list(mr.keys()),
                "answer_len": len(mr.get("answer") or ""),
                "content_len": len(mr.get("content") or ""),
                "summary_len": len(mr.get("summary") or ""),
                "artifact_count": len(mr.get("artifacts", []) or []),
                "render_block_count": len(mr.get("render_blocks", []) or []),
            })
        # ====================================================


        # =====================================================
        # STAGE 5 - FINAL PROVIDER->EXECUTOR TRANSPORT
        # Single canonical handoff with final audit.
        # =====================================================
        provider_log({"trace_stage":"before_finalize_executor","machine_keys":list(contract.get("machine_response",{}).keys()) if isinstance(contract,dict) else []})
        contract = finalize_executor_contract(contract)
        contract = provider_final_guard(contract)
        mr=contract.get("machine_response",{}) if isinstance(contract,dict) else {}
        provider_log({"trace_stage":"after_finalize_executor","answer_len":len(mr.get("answer") or ""),"content_len":len(mr.get("content") or ""),"summary_len":len(mr.get("summary") or ""),"render_blocks":len(mr.get("render_blocks",[]))})
        provider_stage_log("EXECUTOR_HANDOFF", mr)

        # Persist billing/routing telemetry inside the canonical transport.
        mr.setdefault("metadata", {})["provider_cost_policy"] = PROVIDER_COST_LOG_VERSION
        mr["metadata"]["provider_model_requested"] = model
        mr["metadata"]["provider_model_selected"] = selected_model
        mr["metadata"]["provider_tier"] = cost_tier
        mr["metadata"]["provider_question_count"] = question_count
        mr["metadata"]["provider_usage"] = usage
        mr["metadata"]["provider_estimated_cost_usd"] = estimated_cost_usd
        mr["metadata"]["provider_response_id"] = response_id

        _cache_provider_response(messages, contract)
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

                    model=OPENAI_FAST_MODEL,

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


PROVIDER_ROUTE_VERSION="provider_router_luna_cost_guard_v1"
PROVIDER_LEGACY_MODE=False


# ============================================================
# STAGE9 FINAL (provider_router_9)
# ============================================================
# Final cleanup checkpoint.
#
# Goals achieved in the staged test series:
# 1. Legacy automatic TextBlock injection disabled.
# 2. Compatibility recovery isolated.
# 3. Semantic-first pipeline marked as canonical.
# 4. build_provider_machine_response() remains the single
#    assembly point for MachineResponse.
# 5. Provider -> Executor handoff preserved for regression tests.
#
# TEST CHECKLIST
# [ ] Plain text response
# [ ] Markdown response
# [ ] Table artifact
# [ ] Graph artifact
# [ ] Formula artifact
# [ ] Gallery artifact
# [ ] Diagram artifact
# [ ] Multi-artifact scene
# [ ] Empty response handling
# [ ] Executor rendering verification
# ============================================================


# =====================================================
# 🔥 IMAGE GENERATION
# =====================================================

async def generate_image(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "auto",
):
    provider_enter("image_generation", {"size": size})

    provider_log("🔒 IMAGE GENERATION DISABLED (Premium only)")
    provider_exit("image_generation", True)

    return {
        "success": False,
        "premium_required": True,
        "image_generation_disabled": True,
        "reason": "Image generation is temporarily disabled."
    }

provider_generate_image = generate_image



# ============================================================
# APRIL QUANTUM PROVIDER 1.1 — LUNA SINGLE CALL CORE
# ============================================================
# Final definitions intentionally override earlier staged functions.
#
# Contract:
#   MachineRequest -> ONE GPT-5.6 Luna call -> canonical MachineResponse
#
# The Provider generates/translates transport. It does not execute a second
# AI pass, call another text model, or create a second visible answer.
# Structured render_blocks from Luna are preserved. Summary is metadata only.
# ============================================================

APRIL_QUANTUM_PROVIDER_VERSION = "provider_quantum_luna_1_1"
APRIL_QUANTUM_PROVIDER_MODEL = "gpt-5.6-luna"
APRIL_QUANTUM_PROVIDER_SINGLE_CALL = True
APRIL_QUANTUM_PROVIDER_NO_MODEL_ESCALATION = True
APRIL_QUANTUM_PROVIDER_NO_TEXT_FALLBACK_MODELS = True

OPENAI_PRIMARY_MODEL = APRIL_QUANTUM_PROVIDER_MODEL
OPENAI_BALANCED_MODEL = APRIL_QUANTUM_PROVIDER_MODEL
OPENAI_FAST_MODEL = APRIL_QUANTUM_PROVIDER_MODEL
OPENAI_PREMIUM_MODEL = APRIL_QUANTUM_PROVIDER_MODEL

_PROVIDER_INFLIGHT = set()


def _quantum_provider_compact_summary(answer, parsed_contract=None):
    """
    Metadata-only summary. It deliberately does not contain the full answer.
    """
    parsed_contract = parsed_contract or {}
    if not isinstance(answer, str):
        answer = str(answer or "")
    text = answer.strip()
    if not text:
        return ""

    block_types = []
    for block in parsed_contract.get("render_blocks", []) if isinstance(parsed_contract, dict) else []:
        if isinstance(block, dict):
            t = normalize_response_text(block.get("type") or block.get("artifact_type") or "text").lower()
            if t not in block_types:
                block_types.append(t)
    if not block_types:
        block_types = ["text"]

    first_line = text.split("\n", 1)[0].strip()
    if len(first_line) > 110:
        first_line = first_line[:107] + "..."
    return f"{first_line} | scene: {', '.join(block_types[:5])}"


def _quantum_provider_clean_blocks(blocks):
    """
    Preserve provider-owned structured blocks and collapse equivalent visible
    text blocks. No conversion of Markdown/formula text to FormulaBlock.
    """
    if not isinstance(blocks, list):
        return []

    result = []
    seen_text = set()
    seen_structured = set()

    for raw in blocks:
        block = dict(raw) if isinstance(raw, dict) else {
            "type": "text",
            "content": str(raw),
        }

        block_type = normalize_response_text(
            block.get("type") or block.get("artifact_type") or "text"
        ).lower()
        if block_type == "markdown":
            block_type = "text"
        block["type"] = block_type

        content = ""
        for key in ("content", "text", "answer", "message", "value"):
            value = block.get(key)
            if isinstance(value, str) and value.strip():
                content = value.strip()
                break

        if block_type == "text":
            key = re.sub(r"\s+", " ", content).strip().lower()
            if not key or key in seen_text:
                continue
            seen_text.add(key)
            block.setdefault("renderer", "TextBlock")
            block.setdefault("viewer", "TextBlock")
            result.append(block)
            continue

        payload = (
            block.get("table")
            or block.get("graph")
            or block.get("images")
            or block.get("url")
            or block.get("payload")
            or content
        )
        try:
            payload_key = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        except Exception:
            payload_key = str(payload)
        key = (block_type, payload_key[:4000])
        if key in seen_structured:
            continue
        seen_structured.add(key)

        renderer_map = {
            "code": "CodeBlock",
            "table": "TableBlock",
            "graph": "GraphBlock",
            "diagram": "GraphBlock",
            "formula": "FormulaBlock",
            "gallery": "GalleryBlock",
            "image": "GalleryBlock",
            "link": "LinkCard",
        }
        block.setdefault("renderer", renderer_map.get(block_type, "TextBlock"))
        block.setdefault("viewer", block["renderer"])
        result.append(block)

    return result


def _quantum_provider_parse(raw_text):
    """
    Strict one-pass JSON decode. No second OpenAI call and no alternate model.
    If Luna returns plain text, keep it as one text response.
    """
    raw_text = (raw_text or "").strip()
    if not raw_text:
        raise RuntimeError("Provider returned empty response")

    try:
        data = json.loads(raw_text)
        if not isinstance(data, dict):
            raise ValueError("MachineResponse JSON must be an object")
        return data
    except Exception:
        # Transport-level normalization only: preserve Luna's complete answer as
        # text rather than inventing a second semantic/AI route.
        return {
            "answer": raw_text,
            "content": raw_text,
            "response": raw_text,
            "summary": _quantum_provider_compact_summary(raw_text, {}),
            "explanation": "",
            "scene": {},
            "artifacts": [],
            "render_blocks": [{
                "type": "text",
                "content": raw_text,
                "renderer": "TextBlock",
                "viewer": "TextBlock",
                "scene_contract": True,
            }],
            "scene_plan": ["text"],
            "render_priority": ["text"],
            "confidence": 0.5,
            "metadata": {"provider_json_invalid": True},
        }


def _quantum_provider_canonical_response(parsed, source_request):
    parsed = parsed if isinstance(parsed, dict) else {}

    answer = normalize_response_text(
        parsed.get("answer")
        or parsed.get("content")
        or parsed.get("response")
        or ""
    )
    content_value = parsed.get("content")
    if isinstance(content_value, dict):
        content = normalize_response_text(
            content_value.get("text")
            or content_value.get("content")
            or content_value.get("answer")
            or ""
        )
    else:
        content = normalize_response_text(content_value or answer)

    if not answer:
        answer = content

    response = normalize_response_text(parsed.get("response") or answer)

    # Summary is never allowed to replace visible answer/content.
    summary = normalize_response_text(
        parsed.get("summary")
        or _quantum_provider_compact_summary(answer, parsed)
    )

    render_blocks = _quantum_provider_clean_blocks(parsed.get("render_blocks", []))
    artifacts = list(parsed.get("artifacts", []) or [])

    # If provider returned artifacts but no render_blocks, keep artifacts intact;
    # Executor will materialize them without creating another provider request.
    metadata = parsed.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    metadata.update({
        "provider_version": APRIL_QUANTUM_PROVIDER_VERSION,
        "provider_model": APRIL_QUANTUM_PROVIDER_MODEL,
        "provider_calls": 1,
        "summary_visible": False,
        "render_blocks_source": "luna",
        "single_route": True,
    })

    machine = {
        "type": "provider_response",
        "execution_round": getattr(source_request, "execution_round", 1) if source_request is not None else 1,
        "execution_phase": getattr(source_request, "execution_phase", "FIRST_CIRCLE") if source_request is not None else "FIRST_CIRCLE",
        "processor_input": machine_request_to_dict(source_request),
        "provider_source_request": machine_request_to_dict(source_request),
        "machine_response": {
            "summary": summary,
            "explanation": normalize_response_text(parsed.get("explanation") or ""),
            "content": content,
            "answer": answer,
            "response": response,
            "scene": parsed.get("scene", {}) if isinstance(parsed.get("scene", {}), dict) else {},
            "render_blocks": render_blocks,
            "artifacts": artifacts,
            "scene_plan": list(parsed.get("scene_plan") or ["text"]),
            "confidence": parsed.get("confidence", 1.0),
            "metadata": metadata,
            "provider": "openai",
            "render_priority": list(parsed.get("render_priority") or []),
            "provider_contract": "fiber_v3_quantum",
            "transport_contract": "scene_first",
            "provider_calls": 1,
            "provider_original_answer": answer,
            "provider_original_content": content,
        },
        "provider_model": APRIL_QUANTUM_PROVIDER_MODEL,
        "provider_calls": 1,
        "single_route": True,
    }

    # Keep processor input available for continuity without resending it.
    mr = machine["machine_response"]
    metadata.setdefault("processor_input", machine["processor_input"])
    metadata.setdefault("provider_source_request", machine["provider_source_request"])

    return machine


def create_provider_contract(raw_text, source_request=None):
    # Accept an already canonical MachineResponse only; otherwise decode exactly once.
    if (
        isinstance(raw_text, dict)
        and raw_text.get("type") == "provider_response"
        and isinstance(raw_text.get("machine_response"), dict)
    ):
        return raw_text

    parsed = raw_text if isinstance(raw_text, dict) else _quantum_provider_parse(raw_text)
    return _quantum_provider_canonical_response(parsed, source_request)


def provider_finalize_for_executor(contract):
    """
    Single Provider -> Executor handoff. No automatic text block insertion when
    structured blocks already exist, and summary never becomes visible content.
    """
    if not isinstance(contract, dict):
        raise RuntimeError("Provider contract must be a dict")

    mr = contract.setdefault("machine_response", {})
    answer = normalize_response_text(mr.get("answer") or mr.get("content") or "")
    content = normalize_response_text(mr.get("content") or answer)

    mr["answer"] = answer
    mr["content"] = content
    mr["response"] = normalize_response_text(mr.get("response") or answer)
    mr["summary"] = normalize_response_text(
        mr.get("summary") or _quantum_provider_compact_summary(answer, mr)
    )
    mr.setdefault("explanation", "")
    mr["render_blocks"] = _quantum_provider_clean_blocks(mr.get("render_blocks", []))
    mr["artifacts"] = list(mr.get("artifacts", []) or [])
    mr.setdefault("scene", {})
    mr.setdefault("scene_plan", ["text"])
    mr.setdefault("render_priority", [])
    mr.setdefault("metadata", {})

    if not mr["render_blocks"] and not mr["artifacts"] and answer:
        mr["render_blocks"] = [{
            "type": "text",
            "content": answer,
            "text": answer,
            "renderer": "TextBlock",
            "viewer": "TextBlock",
            "scene_contract": True,
        }]

    mr["metadata"]["provider_model"] = APRIL_QUANTUM_PROVIDER_MODEL
    mr["metadata"]["provider_calls"] = 1
    mr["metadata"]["summary_visible"] = False
    mr["metadata"]["single_route"] = True

    return contract


def provider_transport_audit(machine_response):
    mr = machine_response.setdefault("machine_response", {})
    audit = {
        "answer_length": len(mr.get("answer") or ""),
        "content_length": len(mr.get("content") or ""),
        "summary_length": len(mr.get("summary") or ""),
        "artifact_count": len(mr.get("artifacts") or []),
        "render_block_count": len(mr.get("render_blocks") or []),
        "model": APRIL_QUANTUM_PROVIDER_MODEL,
        "provider_calls": 1,
        "single_route": True,
        "summary_visible": False,
    }
    mr.setdefault("metadata", {})["provider_audit"] = audit
    provider_log(f"[PROVIDER:FINAL_AUDIT] {audit}")
    return machine_response


async def generate_text(messages, temperature=0.7, max_output_tokens=None, model=APRIL_QUANTUM_PROVIDER_MODEL):
    """
    Exactly one OpenAI text generation call for one canonical MachineRequest.
    """
    if isinstance(messages, dict):
        machine_request = messages
    else:
        machine_request = messages

    source_request = machine_request_to_dict(machine_request)

    # Exact duplicate suppression for accidental re-entry of the same request.
    cached = _get_duplicate_cached_response(machine_request)
    if cached is not None:
        provider_log("[PROVIDER] DUPLICATE_GUARD: returned cached canonical response")
        return cached

    request_fingerprint = _request_identity(machine_request)
    lock_key = request_fingerprint[1] if request_fingerprint and request_fingerprint[1] else None
    if lock_key in _PROVIDER_INFLIGHT:
        raise RuntimeError("Provider request already in flight for this canonical request")
    if lock_key:
        _PROVIDER_INFLIGHT.add(lock_key)

    try:
        normalized_input = normalize_provider_input(machine_request)

        request = {
            "model": APRIL_QUANTUM_PROVIDER_MODEL,
            "input": normalized_input,
            "max_output_tokens": (
                max_output_tokens
                if isinstance(max_output_tokens, int) and max_output_tokens > 0
                else 1800
            ),
        }

        provider_log({
            "quantum_provider": APRIL_QUANTUM_PROVIDER_VERSION,
            "model": APRIL_QUANTUM_PROVIDER_MODEL,
            "one_openai_call": True,
            "model_escalation": False,
            "secondary_model": None,
            "request_items": len(normalized_input),
        })

        response = openai_client.responses.create(**request)

        usage = _extract_usage(response)
        estimated_cost_usd = _estimate_usage_cost(APRIL_QUANTUM_PROVIDER_MODEL, usage)

        raw_text = getattr(response, "output_text", "") or ""
        provider_log({
            "billing_trace": PROVIDER_COST_LOG_VERSION,
            "model_billed_route": APRIL_QUANTUM_PROVIDER_MODEL,
            "usage": usage,
            "estimated_cost_usd": estimated_cost_usd,
            "provider_calls": 1,
        })

        contract = create_provider_contract(raw_text, source_request=machine_request)
        contract = provider_finalize_for_executor(contract)
        contract = provider_transport_audit(contract)

        mr = contract.setdefault("machine_response", {})
        mr.setdefault("metadata", {}).update({
            "provider_model": APRIL_QUANTUM_PROVIDER_MODEL,
            "provider_usage": usage,
            "provider_estimated_cost_usd": estimated_cost_usd,
            "provider_response_id": getattr(response, "id", None),
            "provider_calls": 1,
            "single_route": True,
            "summary_visible": False,
        })

        _cache_provider_response(machine_request, contract)
        provider_log({
            "trace_stage": "EXECUTOR_HANDOFF",
            "answer_len": len(mr.get("answer") or ""),
            "content_len": len(mr.get("content") or ""),
            "summary_len": len(mr.get("summary") or ""),
            "render_blocks": len(mr.get("render_blocks") or []),
            "artifacts": len(mr.get("artifacts") or []),
            "model": APRIL_QUANTUM_PROVIDER_MODEL,
        })
        return contract

    finally:
        if lock_key:
            _PROVIDER_INFLIGHT.discard(lock_key)
