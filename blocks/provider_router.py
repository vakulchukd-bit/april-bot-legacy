
# =====================================================
# APRIL PROVIDER ROUTER - COST-SAFE FIRST CIRCLE
# =====================================================

from __future__ import annotations

import copy
import json
import os
import time
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI
from google import genai

from blocks.C_ARTIFACT_CONTRACT import MachineRequest


# =====================================================
# CLIENTS
# =====================================================

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


OPENAI_PRIMARY_MODEL = "gpt-5.6"
OPENAI_BALANCED_MODEL = "gpt-5.6-terra"
OPENAI_FAST_MODEL = "gpt-5.6-luna"


# =====================================================
# PATCH LOG
# =====================================================

PROVIDER_PATCH_LOG: list[str] = []


def provider_log(*args: Any) -> None:
    try:
        print(*args)
    except Exception:
        pass


def provider_patch_log(msg: Any) -> None:
    try:
        text = str(msg)
        print("APRIL PROVIDER:", text)
        PROVIDER_PATCH_LOG.append(text)
    except Exception:
        pass


def provider_enter(provider_type: str, payload: Any = None) -> Dict[str, Any]:
    provider_patch_log(f"ENTER PROVIDER: {provider_type}")
    if payload is not None:
        provider_patch_log(str(payload)[:160])
    return {
        "provider_active": True,
        "provider_type": provider_type,
        "continuity_safe": True,
    }


def provider_exit(provider_type: str, success: bool = True) -> Dict[str, Any]:
    provider_patch_log(f"EXIT PROVIDER: {provider_type} SUCCESS={success}")
    return {
        "provider_complete": success,
        "provider_type": provider_type,
        "response_ready": True,
    }


# =====================================================
# STATE
# =====================================================

provider_state = {
    "primary": "openai",
    "gemini_available": True,
    "last_gemini_failure": 0.0,
    "last_health_check": 0.0,
    "recovery_cooldown": 45,
    "visual_mode": "lightweight",
    "execution_mode": "calm",
    "route_health": 1.0,
    "provider_balance": "stable",
}


def update_provider_behavior() -> None:
    now = time.time()
    last_failure = provider_state.get("last_gemini_failure", 0.0)
    delta = now - last_failure

    if delta <= 60:
        provider_state["route_health"] = 0.3
        provider_state["provider_balance"] = "recovery"
    else:
        provider_state["route_health"] = 1.0
        provider_state["provider_balance"] = "stable"

    provider_state["visual_mode"] = "distributed" if provider_state.get("gemini_available") else "restricted"


def should_restore_gemini() -> bool:
    update_provider_behavior()
    if provider_state["gemini_available"]:
        return True

    now = time.time()
    cooldown = provider_state["recovery_cooldown"]
    last_failure = provider_state["last_gemini_failure"]

    if now - last_failure >= cooldown:
        provider_log("🧠 GEMINI RECOVERY WINDOW OPEN")
        provider_state["gemini_available"] = True
        provider_state["last_health_check"] = now
        provider_state["provider_balance"] = "probing"
        return True
    return False


def mark_gemini_failure() -> None:
    provider_log("🔥 GEMINI MARKED UNAVAILABLE")
    provider_state["gemini_available"] = False
    provider_state["last_gemini_failure"] = time.time()
    provider_state["provider_balance"] = "fallback"
    provider_state["route_health"] = 0.0


def mark_gemini_success() -> None:
    provider_state["gemini_available"] = True
    provider_state["last_health_check"] = time.time()
    provider_state["provider_balance"] = "stable"
    provider_state["route_health"] = 1.0


# =====================================================
# SAFE TEXT
# =====================================================

SYSTEM_LEAK_PATTERNS = [
    "system prompt",
    "response_decision",
    "cognition",
    "semantic",
    "trajectory protection",
    "machine channel",
    "provider routing",
    "renderer-first architecture",
]


def sanitize_internal_reasoning(text: str) -> str:
    if not text:
        return ""
    blocked = [
        "possibly",
        "perhaps",
        "internal reasoning",
        "chain of thought",
        "I think",
        "I am reasoning",
    ]
    result = str(text)
    for item in blocked:
        result = result.replace(item, "")
    return result.strip()


def normalize_response_text(text: Any) -> str:
    if not text:
        return ""
    text = str(text).strip().replace("\n\n\n", "\n\n")
    return sanitize_internal_reasoning(text).strip()


def _provider_trim_text(value: Any, limit: int = 240) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if not value:
        return ""
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def _provider_turn_summary(turn: Any, limit: int = 240) -> str:
    if not turn:
        return ""
    if isinstance(turn, dict):
        for key in ("summary", "content", "answer", "text", "message"):
            value = turn.get(key)
            if value:
                return _provider_trim_text(value, limit)
        try:
            return _provider_trim_text(json.dumps(turn, ensure_ascii=False), limit)
        except Exception:
            return _provider_trim_text(str(turn), limit)
    return _provider_trim_text(turn, limit)


# =====================================================
# REQUEST BUILDING
# =====================================================

PROVIDER_MACHINE_SYSTEM_PROMPT = (
    "APRIL PROVIDER. Return one valid JSON object only. "
    "Use CURRENT USER REQUEST as the task. "
    "Use REFERENCE CONTEXT only as background if present. "
    "Do not repeat history, visuals, memory dumps, or previous turns."
)


def machine_request_to_dict(machine_request: Any) -> Dict[str, Any]:
    if isinstance(machine_request, dict):
        return dict(machine_request)

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
            "provider_reference_context": getattr(machine_request, "provider_reference_context", None),
            "first_circle_goal": getattr(machine_request, "first_circle_goal", None),
            "first_circle_only": getattr(machine_request, "first_circle_only", None),
            "second_circle_context": getattr(machine_request, "second_circle_context", None),
        }

    raise TypeError("Provider accepts only canonical MachineRequest.")


def build_provider_reference_context(machine_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tiny, non-repeating background context for continuations.
    Executor can pass provider_reference_context directly; fallback uses a tiny
    slice of conversation if available.
    """
    if not isinstance(machine_request, dict):
        return {}

    direct = machine_request.get("provider_reference_context")
    if isinstance(direct, dict) and direct:
        return direct

    conversation = machine_request.get("conversation") or {}
    response_decision = machine_request.get("response_decision") or {}
    intent = machine_request.get("intent") or {}

    timeline = conversation.get("timeline")
    if not isinstance(timeline, list):
        timeline = []

    last_user_turn = conversation.get("last_user_turn")
    last_april_turn = conversation.get("last_april_turn")

    if not last_user_turn and timeline:
        for item in reversed(timeline):
            if isinstance(item, dict) and item.get("user"):
                last_user_turn = item.get("user")
                break

    if not last_april_turn and timeline:
        for item in reversed(timeline):
            if isinstance(item, dict) and item.get("april"):
                last_april_turn = item.get("april")
                break

    active_topic = (
        conversation.get("active_topic")
        or conversation.get("topic")
        or conversation.get("goal_hierarchy", {}).get("active_topic")
        or response_decision.get("goal")
        or intent.get("type")
        or ""
    )

    focus = (
        conversation.get("focus")
        or conversation.get("dialog_focus")
        or response_decision.get("dialog_focus")
        or {}
    )

    reference_context = {
        "active_topic": _provider_trim_text(active_topic, 80),
        "last_user_turn_summary": _provider_turn_summary(last_user_turn, 180),
        "last_april_turn_summary": _provider_turn_summary(last_april_turn, 180),
        "dialog_focus": focus if isinstance(focus, dict) else _provider_trim_text(focus, 120),
    }

    return {k: v for k, v in reference_context.items() if v not in ("", {}, [], None)}


def build_openai_request(machine_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a compact first-circle prompt:
    - current user request
    - optional tiny reference context
    - fixed JSON contract
    """
    if not isinstance(machine_request, dict):
        machine_request = {}

    intent = machine_request.get("intent") or {}
    user_text = (
        machine_request.get("goal")
        or intent.get("normalized_text")
        or intent.get("text")
        or machine_request.get("content")
        or ""
    )
    user_text = str(user_text).strip()

    reference_context = build_provider_reference_context(machine_request)

    provider_log("CURRENT REQUEST:", _provider_trim_text(user_text, 800))
    if reference_context:
        provider_log("REFERENCE CONTEXT:", _provider_trim_text(json.dumps(reference_context, ensure_ascii=False), 800))

    prompt_parts = [
        "CURRENT USER REQUEST",
        user_text,
    ]

    if reference_context:
        prompt_parts.extend([
            "",
            "REFERENCE CONTEXT (background only; do not repeat):",
            json.dumps(reference_context, ensure_ascii=False),
        ])

    prompt_parts.extend([
        "",
        "Return one valid JSON object only.",
        "Required keys: answer, content, summary, explanation, scene, artifacts, render_blocks, scene_plan, render_priority, confidence.",
        "Answer only the current request.",
    ])

    return {
        "role": "user",
        "content": [{
            "type": "input_text",
            "text": "\n".join(prompt_parts).strip(),
        }],
    }


def normalize_provider_input(machine_request: Any) -> list[dict]:
    system_item = {
        "role": "system",
        "content": [{
            "type": "input_text",
            "text": PROVIDER_MACHINE_SYSTEM_PROMPT,
        }],
    }
    payload = machine_request_to_dict(machine_request)
    return [system_item, build_openai_request(payload)]


# =====================================================
# CONTRACT DECODING
# =====================================================

CANONICAL_PROVIDER_TEXT_FIELD = "content"


def provider_validate_contract(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {"answer": str(data), "content": str(data)}
    if "answer" not in data and "content" in data:
        data["answer"] = data["content"]
    if "content" not in data and "answer" in data:
        data["content"] = data["answer"]
    return data


def provider_normalize_contract(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        data = {"answer": str(data), "content": str(data)}
    data.setdefault("scene", {})
    data.setdefault("render_blocks", [])
    data.setdefault("artifacts", [])
    data.setdefault("summary", data.get("answer", data.get("content", "")))
    return data


def provider_canonicalize_contract(data: Any) -> Dict[str, Any]:
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


def provider_preserve_full_response(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {"content": str(data), "_provider_payload": data}
    if "_provider_payload" not in data:
        data["_provider_payload"] = dict(data)
    data.setdefault("provider_raw", data["_provider_payload"])
    data.setdefault("processor_input", data["_provider_payload"])
    return data


def validate_machine_response_contract(contract: Any) -> Dict[str, Any]:
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


def ensure_scene_first_contract(contract: Any) -> Dict[str, Any]:
    contract = validate_machine_response_contract(contract)
    contract.setdefault("scene", {})
    contract.setdefault("render_blocks", [])
    contract.setdefault("artifacts", [])
    return contract


def recover_machine_contract(contract: Any) -> Dict[str, Any]:
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
    contract.setdefault("summary", candidate)
    contract.setdefault("explanation", contract["summary"])
    contract.setdefault("scene", {})
    contract.setdefault("artifacts", [])
    contract.setdefault("render_blocks", [])
    contract.setdefault("scene_plan", ["text"])
    contract.setdefault("render_priority", ["text"])
    contract.setdefault("metadata", {})
    contract["metadata"]["contract_recovered"] = True
    contract["metadata"]["transport_stage"] = "provider_stage2"
    return contract


def provider_decode_json(raw_text: Any) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(raw_text)
        if isinstance(data, dict):
            return data
    except Exception:
        return None
    return None


def parse_provider_machine_contract(raw_text: Any) -> Dict[str, Any]:
    try:
        data = json.loads(raw_text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError as e:
        provider_log(f"JSON PARSE ERROR line={e.lineno} col={e.colno} pos={e.pos}")
        start = max(0, e.pos - 120)
        end = min(len(raw_text), e.pos + 120)
        provider_log(raw_text[start:end])

        repaired = (raw_text or "").strip()
        first = repaired.find("{")
        last = repaired.rfind("}")

        if first != -1 and last > first:
            repaired = repaired[first:last + 1]
            try:
                data = json.loads(repaired)
                if isinstance(data, dict):
                    provider_log("JSON RECOVERY SUCCESS")
                    return data
            except Exception:
                pass

        provider_log("SECOND PASS: building canonical contract from raw provider text")

        import re

        def _grab(name: str) -> str:
            m = re.search(r'"%s"\s*:\s*"((?:\\.|[^"])*)"' % name, raw_text, re.S)
            if not m:
                return ""
            value = m.group(1)
            try:
                value = json.loads(f'"{value}"')
            except Exception:
                pass
            return value

        recovered_answer = _grab("answer") or _grab("content") or _grab("response") or raw_text.strip()
        recovered_summary = _grab("summary") or recovered_answer
        recovered_explanation = _grab("explanation") or recovered_summary

        return {
            "answer": recovered_answer,
            "content": recovered_answer,
            "response": recovered_answer,
            "summary": recovered_summary,
            "explanation": recovered_explanation,
            "scene": {},
            "artifacts": [],
            "render_blocks": [{
                "type": "text",
                "content": recovered_answer or recovered_summary or "",
                "scene_contract": True,
            }],
            "scene_plan": ["text"],
            "render_priority": ["text"],
            "confidence": 0.5,
            "metadata": {
                "provider_second_pass": True,
                "parse_failed": True,
                "raw_provider_text": raw_text,
            },
        }
    return {}


def provider_decode_response(raw_text: Any) -> Dict[str, Any]:
    parsed = provider_decode_json(raw_text)
    if parsed is None:
        parsed = parse_provider_machine_contract(raw_text)
    parsed = provider_validate_contract(parsed)
    parsed = provider_normalize_contract(parsed)
    parsed = provider_canonicalize_contract(parsed)
    parsed = provider_preserve_full_response(parsed)
    return parsed


# =====================================================
# MACHINE RESPONSE ASSEMBLY
# =====================================================

def provider_contract_ready(machine_response: Dict[str, Any]) -> Dict[str, Any]:
    return machine_response


def build_provider_machine_response(text: Any, parsed_contract: Optional[Dict[str, Any]] = None, source_request: Any = None) -> Dict[str, Any]:
    parsed_contract = parsed_contract or {}

    fallback = normalize_response_text(text)

    answer = (
        parsed_contract.get("answer")
        or parsed_contract.get("content")
        or parsed_contract.get("response")
        or fallback
    )

    content = parsed_contract.get("content") or answer
    response = parsed_contract.get("response") or answer
    summary = parsed_contract.get("summary") or answer
    explanation = parsed_contract.get("explanation") or summary
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
        },
    }

    mr = machine["machine_response"]
    if processor_input:
        metadata = mr.setdefault("metadata", {})
        metadata.setdefault("processor_input", processor_input)
        metadata.setdefault("provider_source_request", processor_input)
        metadata.setdefault("provider_first_circle", True)
        metadata.setdefault("second_circle_ready", True)
        metadata.setdefault("execution_round", execution_round)
        metadata.setdefault("execution_phase", execution_phase)

    return machine


def enrich_machine_response(contract: Dict[str, Any]) -> Dict[str, Any]:
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
            mr.setdefault("answer", "")
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


def infer_executor_rendering(machine_response: Dict[str, Any]) -> Dict[str, Any]:
    mr = machine_response.setdefault("machine_response", {})
    mr.setdefault("render_blocks", [])
    mr.setdefault("scene_plan", ["text"])
    mr.setdefault("render_priority", ["text"])
    return machine_response


def detect_executor_artifacts(machine_response: Dict[str, Any]) -> Dict[str, Any]:
    mr = machine_response.setdefault("machine_response", {})
    render_blocks = mr.setdefault("render_blocks", [])
    artifacts = mr.setdefault("artifacts", [])
    metadata = mr.setdefault("metadata", {})

    answer = mr.get("answer") or mr.get("content") or mr.get("summary") or ""
    metadata["provider_stage"] = "stage3"
    metadata["canonical_handoff"] = True
    metadata["artifact_count"] = len(artifacts)
    metadata["render_block_count"] = len(render_blocks)

    if answer and not any(isinstance(b, dict) and b.get("type") == "text" for b in render_blocks):
        pass

    return machine_response


def provider_finalize_for_executor(contract: Dict[str, Any]) -> Dict[str, Any]:
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
        mr.setdefault("summary", candidate)

        blocks = mr.setdefault("render_blocks", [])
        if not any(isinstance(b, dict) and b.get("type") == "text" for b in blocks):
            blocks.insert(0, {
                "type": "text",
                "content": candidate,
                "scene_contract": True,
            })

    return contract


def provider_transport_audit(machine_response: Dict[str, Any]) -> Dict[str, Any]:
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


def finalize_executor_contract(machine_response: Dict[str, Any]) -> Dict[str, Any]:
    for step in (
        enrich_machine_response,
        infer_executor_rendering,
        detect_executor_artifacts,
        provider_transport_audit,
    ):
        machine_response = step(machine_response)
    return machine_response


def provider_final_guard(contract: Dict[str, Any]) -> Dict[str, Any]:
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
        mr.setdefault("summary", candidate)

        blocks = mr.setdefault("render_blocks", [])
        if not any(isinstance(b, dict) and b.get("type") == "text" for b in blocks):
            blocks.insert(0, {
                "type": "text",
                "content": candidate,
                "scene_contract": True,
            })

    return contract


def build_provider_overload_contract(space: Any):
    raise RuntimeError(f"Provider route failed: {space}")


# =====================================================
# GENERATION
# =====================================================

def provider_should_bypass_openai(messages: Any) -> Tuple[bool, Optional[Dict[str, Any]]]:
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


def provider_stage_log(stage: str, payload: Any = None) -> None:
    try:
        if isinstance(payload, dict):
            info = {}
            for k, v in payload.items():
                if isinstance(v, str):
                    info[k] = f"<str:{len(v)}>"
                elif isinstance(v, (list, dict)):
                    info[k] = f"<{type(v).__name__}:{len(v)}>"
                else:
                    info[k] = v
            provider_log(f"[PROVIDER:{stage}] {info}")
        else:
            provider_log(f"[PROVIDER:{stage}] {payload}")
    except Exception:
        pass


def _serialize_output_text(raw_text: str) -> Dict[str, Any]:
    parsed = provider_decode_response(raw_text)
    parsed = ensure_scene_first_contract(parsed)
    parsed = normalize_text_transport(parsed)
    parsed = recover_machine_contract(parsed)
    return parsed


async def generate_text(
    messages: Any,
    temperature: float = 0.7,
    max_output_tokens: Optional[int] = None,
    model: str = OPENAI_PRIMARY_MODEL,
):
    provider_enter("openai_text", messages)

    bypass, payload = provider_should_bypass_openai(messages)
    if bypass:
        provider_exit("cpu_redirect", True)
        payload["executor_cpu_redirect"] = True
        payload["route_target"] = "executor_cpu"
        payload["next_stage"] = "EXECUTOR_CPU"
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
        provider_log("OPENAI TEXT START")
        provider_log("RAW MESSAGE TYPE:", type(messages))
        provider_stage_log("INPUT", {"type": type(messages).__name__})

        normalized_input = normalize_provider_input(messages)
        provider_stage_log("OPENAI_REQUEST", {"items": len(normalized_input)})

        request = {
            "model": model,
            "input": normalized_input,
        }

        effective_max_output_tokens = max_output_tokens if max_output_tokens is not None else 1200
        request["max_output_tokens"] = effective_max_output_tokens

        legacy_temperature_models = {
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4.1",
            "gpt-4.1-mini",
        }
        if temperature is not None and model in legacy_temperature_models:
            request["temperature"] = temperature

        provider_log({
            "provider_model": model,
            "request_keys": list(request.keys()),
        })

        response = openai_client.responses.create(**request)

        raw_text = response.output_text or ""
        provider_stage_log("OPENAI_RESPONSE", {"chars": len(raw_text)})
        provider_log(f"OPENAI OUTPUT LENGTH: {len(raw_text)}")
        if hasattr(response, "incomplete_details"):
            provider_log(f"OPENAI INCOMPLETE: {response.incomplete_details}")

        if not raw_text:
            provider_exit("openai_text", False)
            raise RuntimeError("Provider returned empty response")

        provider_exit("openai_text", True)

        source_request = machine_request_to_dict(messages) if not isinstance(messages, dict) else dict(messages)
        contract = create_provider_contract(raw_text, source_request=source_request)

        if isinstance(contract, dict):
            mr = contract.get("machine_response")
            if isinstance(mr, dict):
                for field in ("answer", "content", "summary", "explanation", "response"):
                    if isinstance(mr.get(field), str):
                        mr[field] = normalize_response_text(mr[field])

        provider_stage_log("EXECUTOR_HANDOFF", contract.get("machine_response", {}) if isinstance(contract, dict) else {})
        return contract

    except Exception as e:
        provider_log("OPENAI TEXT ERROR:", e)
        provider_exit("openai_text", False)
        raise


# =====================================================
# CONTRACT CREATION
# =====================================================

def create_provider_contract(raw_text: Any, source_request: Any = None) -> Dict[str, Any]:
    if isinstance(raw_text, dict) and raw_text.get("type") == "provider_response" and isinstance(raw_text.get("machine_response"), dict):
        provider_log("STAGE3: canonical MachineResponse received")
        return provider_contract_ready(raw_text)

    parsed = raw_text if isinstance(raw_text, dict) else provider_decode_response(raw_text)
    parsed = ensure_scene_first_contract(parsed)
    parsed = normalize_text_transport(parsed)
    parsed = recover_machine_contract(parsed)

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
        mr.setdefault("summary", candidate)

    machine = provider_finalize_for_executor(machine)
    machine = attach_processor_input(machine, source_request)
    return machine


def attach_processor_input(contract: Dict[str, Any], source_request: Any = None) -> Dict[str, Any]:
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


# =====================================================
# VOICE / IMAGE / IMAGE-GEN
# =====================================================

async def transcribe_voice(file_path: str) -> str:
    provider_enter("voice_transcription", file_path)
    try:
        provider_log("OPENAI VOICE START")
        with open(file_path, "rb") as f:
            transcript = openai_client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=f,
            )

        text = normalize_response_text(transcript.text if transcript.text else "")
        provider_log("OPENAI VOICE RESPONSE:", text[:120] if text else "EMPTY")

        if text:
            provider_exit("voice_transcription", True)
            return text

        provider_exit("voice_transcription", False)
        return ""

    except Exception as e:
        provider_log("OPENAI VOICE ERROR:", e)
        provider_exit("voice_transcription", False)
        return ""


async def analyze_image(path: str, prompt: str):
    provider_enter("image_analysis", path)
    update_provider_behavior()

    if should_restore_gemini():
        try:
            provider_log("GEMINI IMAGE START")
            uploaded = gemini_client.files.upload(file=path)
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[uploaded, prompt],
            )
            text = normalize_response_text(response.text if response.text else "")
            if text:
                mark_gemini_success()
                provider_exit("gemini_image", True)
                return create_provider_contract(text)
        except Exception as e:
            provider_log("GEMINI IMAGE ERROR:", e)
            mark_gemini_failure()

    try:
        provider_log("OPENAI IMAGE ROUTE")
        with open(path, "rb") as image_file:
            response = openai_client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {"type": "input_image", "image": image_file.read()},
                        ],
                    }
                ],
                max_output_tokens=250,
            )

        text = normalize_response_text(response.output_text if response.output_text else "")
        if text:
            provider_exit("openai_image", True)
            return create_provider_contract(text)

        provider_exit("openai_image", False)
        raise RuntimeError("Visual provider route failed")

    except Exception as e:
        provider_log("OPENAI IMAGE ERROR:", e)
        provider_exit("openai_image", False)
        raise RuntimeError("Visual provider route failed")


async def generate_image(prompt: str, size: str = "1024x1024", quality: str = "auto"):
    provider_enter("image_generation", {"size": size})
    provider_log("IMAGE GENERATION DISABLED (Premium only)")
    provider_exit("image_generation", True)
    return {
        "success": False,
        "premium_required": True,
        "image_generation_disabled": True,
        "reason": "Image generation is temporarily disabled.",
    }


provider_generate_image = generate_image


PROVIDER_ROUTE_VERSION = "provider_router_10"
PROVIDER_LEGACY_MODE = False
