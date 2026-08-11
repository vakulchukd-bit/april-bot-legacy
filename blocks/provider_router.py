from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import time
from typing import Any, Dict, Optional

from openai import OpenAI
from blocks.C_ARTIFACT_CONTRACT import MachineRequest

# ============================================================
# APRIL PROVIDER — CANONICAL LUNA ROUTE
# ============================================================

APRIL_QUANTUM_PROVIDER_VERSION = "provider_quantum_luna_3_0"
APRIL_QUANTUM_PROVIDER_MODEL = os.getenv("APRIL_OPENAI_MODEL", "gpt-5.6-luna")
APRIL_QUANTUM_PROVIDER_SINGLE_CALL = True
APRIL_QUANTUM_PROVIDER_NO_MODEL_ESCALATION = True
APRIL_QUANTUM_PROVIDER_NO_TEXT_FALLBACK_MODELS = True

OPENAI_PRIMARY_MODEL = APRIL_QUANTUM_PROVIDER_MODEL
OPENAI_BALANCED_MODEL = APRIL_QUANTUM_PROVIDER_MODEL
OPENAI_FAST_MODEL = APRIL_QUANTUM_PROVIDER_MODEL
OPENAI_PREMIUM_MODEL = APRIL_QUANTUM_PROVIDER_MODEL

INPUT_TOKEN_BUDGET = 900
OUTPUT_TIER_TOKENS = {"LOW": 2000, "MEDIUM": 5000, "HIGH": 8000}
MIN_OUTPUT_TOKENS = 2000
MAX_OUTPUT_TOKENS = 8000

PROVIDER_DUPLICATE_TTL_SECONDS = 90
PROVIDER_COST_LOG_VERSION = "cost_guard_v4"
_PROVIDER_CALL_CACHE: dict[str, dict[str, Any]] = {}
_PROVIDER_INFLIGHT: set[str] = []

_openai_client = None
_gemini_client = None

def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client

def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        from google import genai
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client

PROVIDER_MACHINE_SYSTEM_PROMPT = """
You are April's single text-generation provider, GPT-5.6 Luna.

You receive one canonical MachineRequest already interpreted by April's processor.
Return exactly one MachineResponse JSON object. Do not wrap it in markdown fences.

Required fields:
answer, content, summary, scene, artifacts, render_blocks,
scene_plan, render_priority, confidence.

Rules:
- answer/content are the complete human-visible answer.
- Answer the current request, not the transport protocol.
- Use dialogue_contract only to preserve necessary continuity.
- When the request is independent, do not invent old context.
- When it is a continuation/reference, use only the supplied relevant context.
- Preserve the complete logical answer; never cut a sentence or scene for style.
- Use structured render_blocks only for representations actually required.
- Keep Markdown and inline LaTeX inside text unless a separate renderer is explicitly required.
- Never produce a second answer.
- Never call another model.
""".strip()


def provider_log(*args: Any) -> None:
    try:
        print(*args)
    except Exception:
        pass


def _safe_text(value: Any) -> str:
    return value if isinstance(value, str) else (str(value) if value is not None else "")


def normalize_response_text(text: Any) -> str:
    value = _safe_text(text).strip()
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value


def _estimate_input_tokens(text: Any) -> int:
    """
    Conservative local estimate. It is only a packing guard, not billing truth.
    It deliberately overestimates Cyrillic/JSON punctuation.
    """
    s = _safe_text(text)
    total = 0.0
    for ch in s:
        if ch.isspace():
            total += 0.15
        elif ord(ch) > 127:
            total += 0.50
        elif ch in '{}[]":,;|_-':
            total += 0.35
        else:
            total += 0.25
    return max(1, int(total + 0.999))


def _compact_value(value: Any, *, depth: int = 0, max_depth: int = 3,
                   max_items: int = 8, max_keys: int = 16) -> Any:
    if depth > max_depth:
        return None
    if value in (None, "", [], {}):
        return None
    if isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        out = {}
        for key in list(value.keys())[:max_keys]:
            cleaned = _compact_value(
                value[key],
                depth=depth + 1,
                max_depth=max_depth,
                max_items=max_items,
                max_keys=max_keys,
            )
            if cleaned not in (None, "", [], {}):
                out[str(key)] = cleaned
        return out
    if isinstance(value, (list, tuple, set)):
        out = []
        for item in list(value)[:max_items]:
            cleaned = _compact_value(
                item,
                depth=depth + 1,
                max_depth=max_depth,
                max_items=max_items,
                max_keys=max_keys,
            )
            if cleaned not in (None, "", [], {}):
                out.append(cleaned)
        return out
    return _safe_text(value).strip()


def _dialogue_contract(payload: dict[str, Any]) -> dict[str, Any]:
    contract = payload.get("dialogue_contract")
    if isinstance(contract, dict):
        return contract
    conversation = payload.get("conversation")
    if isinstance(conversation, dict):
        candidate = conversation.get("dialogue_contract")
        if isinstance(candidate, dict):
            return candidate
    return {}


def machine_request_to_dict(machine_request: Any) -> dict[str, Any]:
    if isinstance(machine_request, dict):
        raw = dict(machine_request)
    elif isinstance(machine_request, MachineRequest):
        raw = {}
        names = (
            "request_id", "goal", "intent", "conversation", "memory",
            "visual_context", "available_tools", "requested_outputs",
            "required_competencies", "required_artifacts", "routing",
            "constraints", "metadata", "dialogue_contract",
            "response_decision", "semantic", "cognition",
            "response_complexity", "response_output_tokens",
        )
        for name in names:
            value = getattr(machine_request, name, None)
            if value not in (None, "", [], {}):
                raw[name] = value
        # Executor-added attributes are read from the same MachineRequest,
        # not from a second route.
        for name in ("dialogue_contract", "semantic", "response_decision"):
            value = getattr(machine_request, name, None)
            if isinstance(value, dict) and value:
                raw[name] = value
    else:
        raise TypeError("Provider accepts only canonical MachineRequest or dict.")

    dialogue = _dialogue_contract(raw)
    intent = raw.get("intent")
    if not isinstance(intent, dict):
        intent = {"normalized_text": _safe_text(intent)}

    current = (
        intent.get("normalized_text")
        or intent.get("text")
        or raw.get("canonical_prompt_text")
        or ""
    )

    compact = {
        "goal": raw.get("goal"),
        "intent": {
            "type": intent.get("type") or intent.get("intent"),
            "normalized_text": _safe_text(current).strip(),
            "dialog_act": intent.get("dialog_act") or dialogue.get("dialog_act"),
        },
        "dialogue_contract": dialogue,
        "memory": raw.get("memory") or {},
        "requested_outputs": raw.get("requested_outputs") or [],
        "required_competencies": raw.get("required_competencies") or [],
        "required_artifacts": raw.get("required_artifacts") or [],
        "visual_context": raw.get("visual_context") or {},
        "constraints": raw.get("constraints") or {},
        "response_decision": raw.get("response_decision") or {},
        "semantic": raw.get("semantic") or {},
        "cognition": raw.get("cognition") or {},
        "response_complexity": raw.get("response_complexity"),
        "response_output_tokens": raw.get("response_output_tokens"),
    }

    compact = _compact_value(compact) or {}
    compact["intent"] = {
        "type": (compact.get("intent") or {}).get("type"),
        "normalized_text": (compact.get("intent") or {}).get("normalized_text", _safe_text(current).strip()),
        "dialog_act": (compact.get("intent") or {}).get("dialog_act"),
    }
    return compact


def _request_identity(machine_request: Any) -> tuple[Optional[str], Optional[str]]:
    payload = machine_request_to_dict(machine_request)
    flow_id = (
        payload.get("flow_id")
        or payload.get("trace_id")
        or (payload.get("metadata") or {}).get("flow_id")
        or (payload.get("metadata") or {}).get("trace_id")
    )
    if not flow_id:
        return None, None

    stable = copy.deepcopy(payload)
    for key in ("flow_id", "trace_id", "metadata"):
        stable.pop(key, None)
    raw = json.dumps(stable, ensure_ascii=False, sort_keys=True, default=str)
    fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return str(flow_id), fingerprint


def _get_duplicate_cached_response(machine_request: Any) -> Optional[dict]:
    flow_id, fingerprint = _request_identity(machine_request)
    if not flow_id or not fingerprint:
        return None
    entry = _PROVIDER_CALL_CACHE.get(flow_id)
    if not entry:
        return None
    if time.time() - entry["ts"] > PROVIDER_DUPLICATE_TTL_SECONDS:
        _PROVIDER_CALL_CACHE.pop(flow_id, None)
        return None
    if entry["fingerprint"] != fingerprint:
        return None
    provider_log("[PROVIDER] duplicate guard hit:", flow_id)
    return copy.deepcopy(entry["response"])


def _cache_provider_response(machine_request: Any, response: dict) -> None:
    flow_id, fingerprint = _request_identity(machine_request)
    if not flow_id or not fingerprint:
        return
    _PROVIDER_CALL_CACHE[flow_id] = {
        "ts": time.time(),
        "fingerprint": fingerprint,
        "response": copy.deepcopy(response),
    }
    now = time.time()
    for key, entry in list(_PROVIDER_CALL_CACHE.items()):
        if now - entry["ts"] > PROVIDER_DUPLICATE_TTL_SECONDS:
            _PROVIDER_CALL_CACHE.pop(key, None)


def _extract_request_text(payload: dict[str, Any]) -> str:
    intent = payload.get("intent") or {}
    if isinstance(intent, dict):
        for key in ("normalized_text", "text", "query", "content"):
            value = intent.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return _safe_text(payload.get("content") or payload.get("text") or payload.get("query")).strip()


def _count_question_marks(text: str) -> int:
    return _safe_text(text).count("?") + _safe_text(text).count("？")


def _derive_complexity(payload: dict[str, Any]) -> str:
    explicit = _safe_text(payload.get("response_complexity")).upper()
    if explicit in OUTPUT_TIER_TOKENS:
        return explicit

    question_count = _count_question_marks(_extract_request_text(payload))
    outputs = payload.get("requested_outputs") or []
    artifacts = payload.get("required_artifacts") or []
    dialogue = _dialogue_contract(payload)

    complexity_signals = question_count
    complexity_signals += max(0, len(outputs) - 1)
    complexity_signals += max(0, len(artifacts) - 1)

    if dialogue.get("continuation") and dialogue.get("previous_april_turn"):
        complexity_signals += 1

    if complexity_signals >= 5:
        return "HIGH"
    if complexity_signals >= 2:
        return "MEDIUM"
    return "LOW"


def _derive_output_tokens(payload: dict[str, Any], requested: Any = None) -> int:
    complexity = _derive_complexity(payload)
    if isinstance(requested, int) and requested > 0:
        return min(max(requested, MIN_OUTPUT_TOKENS), MAX_OUTPUT_TOKENS)
    embedded = payload.get("response_output_tokens")
    if isinstance(embedded, int) and embedded > 0:
        return min(max(embedded, MIN_OUTPUT_TOKENS), MAX_OUTPUT_TOKENS)
    return OUTPUT_TIER_TOKENS[complexity]


def _render_block_renderer(block_type: str) -> str:
    return {
        "text": "TextBlock",
        "markdown": "MarkdownBlock",
        "table": "TableBlock",
        "graph": "GraphBlock",
        "diagram": "DiagramBlock",
        "formula": "FormulaBlock",
        "code": "CodeBlock",
        "gallery": "GalleryBlock",
        "image": "ImageBlock",
        "link": "LinkCard",
        "file": "FileBlock",
        "audio": "AudioBlock",
        "video": "VideoBlock",
        "action": "ActionBlock",
    }.get(block_type, "TextBlock")


def _clean_render_blocks(blocks: Any) -> list[dict]:
    if not isinstance(blocks, list):
        return []
    result: list[dict] = []
    seen: set[tuple] = set()

    for raw in blocks:
        block = dict(raw) if isinstance(raw, dict) else {"type": "text", "content": _safe_text(raw)}
        block_type = _safe_text(block.get("type") or block.get("artifact_type") or "text").lower()
        if block_type == "markdown":
            normalized_type = "text"
        else:
            normalized_type = block_type

        content = ""
        for key in ("content", "text", "answer", "message", "value"):
            value = block.get(key)
            if isinstance(value, str) and value.strip():
                content = value.strip()
                break

        if normalized_type == "text":
            signature = ("text", re.sub(r"\s+", " ", content).lower())
        else:
            payload = (
                block.get("payload")
                if block.get("payload") is not None
                else block.get("table")
                or block.get("graph")
                or block.get("images")
                or block.get("url")
                or content
            )
            signature = (
                normalized_type,
                json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)[:4000],
            )

        if signature in seen:
            continue
        seen.add(signature)
        block["type"] = normalized_type
        block.setdefault("renderer", _render_block_renderer(normalized_type))
        block.setdefault("viewer", block["renderer"])
        result.append(block)

    return result


def _compact_summary(answer: str, blocks: list[dict]) -> str:
    answer = normalize_response_text(answer)
    if not answer:
        return ""
    first = answer.split("\n", 1)[0]
    if len(first) > 120:
        first = first[:117] + "..."
    kinds = []
    for block in blocks:
        t = _safe_text(block.get("type")).lower()
        if t and t not in kinds:
            kinds.append(t)
    return f"{first} | scene: {', '.join(kinds[:5])}" if kinds else first


def _select_context_fields(payload: dict[str, Any]) -> list[tuple[str, Any]]:
    """
    Semantic context selection. It does not key off magic words.
    Current request is always first. Optional fields are admitted only when
    the processor has established a relation that makes them useful.
    """
    dialogue = _dialogue_contract(payload)
    intent = payload.get("intent") or {}
    current = _extract_request_text(payload)

    fields: list[tuple[str, Any]] = []
    fields.append(("CURRENT_REQUEST", current))

    dialog_act = _safe_text(dialogue.get("dialog_act")).lower()
    continuation = bool(dialogue.get("continuation"))
    reference = dialog_act == "reference" or bool(dialogue.get("reply_to"))
    same_goal = bool(dialogue.get("active_goal")) and bool(payload.get("goal"))
    topic_relation = bool(dialogue.get("active_topic")) and (
        continuation or reference or same_goal
    )

    # A small self-contained dialogue vector is nearly always useful when the
    # processor has already resolved a continuation/reference relation.
    if continuation or reference or topic_relation:
        vector = {
            "dialog_act": dialogue.get("dialog_act"),
            "continuation": continuation,
            "reply_to": dialogue.get("reply_to"),
            "active_goal": dialogue.get("active_goal"),
            "active_topic": dialogue.get("active_topic"),
            "previous_april_turn": dialogue.get("previous_april_turn"),
            "previous_user_turn": dialogue.get("previous_user_turn"),
        }
        fields.append(("DIALOGUE_VECTOR", _compact_value(vector, max_items=6, max_keys=8)))

    if continuation and dialogue.get("previous_april_turn"):
        fields.append(("PREVIOUS_APRIL_TURN", dialogue.get("previous_april_turn")))

    if same_goal:
        fields.append(("RESOLVED_GOAL", payload.get("goal")))

    requested_outputs = payload.get("requested_outputs") or []
    required_artifacts = payload.get("required_artifacts") or []
    competencies = payload.get("required_competencies") or []

    if requested_outputs:
        fields.append(("REQUESTED_OUTPUTS", requested_outputs))
    if required_artifacts:
        fields.append(("REQUIRED_ARTIFACTS", required_artifacts))
    if competencies:
        fields.append(("COMPETENCIES", competencies))

    # Visual context is sent only for an actual visual/artifact relation.
    visual = payload.get("visual_context")
    if visual and (reference or "structured_rendering" in competencies or requested_outputs):
        fields.append(("VISUAL_CONTEXT", visual))

    # Semantic/decision packets are compact and only used after a relation exists.
    if continuation or reference or same_goal:
        if payload.get("response_decision"):
            fields.append(("RESPONSE_DECISION", payload["response_decision"]))
        if payload.get("semantic"):
            fields.append(("SEMANTIC_STATE", payload["semantic"]))

    return fields


def _build_provider_user_text(payload: dict[str, Any], budget_tokens: int) -> str:
    fields = _select_context_fields(payload)
    complexity = _derive_complexity(payload)
    output_tokens = _derive_output_tokens(payload)

    def render(label: str, value: Any) -> str:
        if isinstance(value, (dict, list, tuple)):
            value = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
        return f"{label}: {value}"

    mandatory = [
        "APRIL CANONICAL REQUEST",
        render("REQUEST", fields[0][1]),
        render("COMPLEXITY", complexity),
        render("OUTPUT_CAP", output_tokens),
    ]

    pieces = list(mandatory)
    used = _estimate_input_tokens("\n".join(pieces))
    soft_limit = max(1, budget_tokens - 10)

    for label, value in fields[1:]:
        candidate = render(label, value)
        candidate_total = _estimate_input_tokens("\n".join(pieces + [candidate]))
        if candidate_total <= soft_limit:
            pieces.append(candidate)

    pieces.append("Return one complete logical answer as JSON.")
    return "\n".join(pieces)


def build_openai_request(machine_request: Any) -> dict:
    payload = machine_request_to_dict(machine_request)
    user_text = _build_provider_user_text(
        payload,
        budget_tokens=max(1, INPUT_TOKEN_BUDGET - _estimate_input_tokens(PROVIDER_MACHINE_SYSTEM_PROMPT)),
    )
    return {
        "role": "user",
        "content": [{"type": "input_text", "text": user_text}],
    }


def normalize_provider_input(machine_request: Any) -> list[dict]:
    system_tokens = _estimate_input_tokens(PROVIDER_MACHINE_SYSTEM_PROMPT)
    remaining = max(1, INPUT_TOKEN_BUDGET - system_tokens - 8)
    user_message = build_openai_request(machine_request)
    user_text = user_message["content"][0]["text"]

    # If the conservative estimator still exceeds the boundary, rebuild using
    # mandatory units only. We never character-cut the current request.
    if _estimate_input_tokens(user_text) > remaining:
        payload = machine_request_to_dict(machine_request)
        current = _extract_request_text(payload)
        complexity = _derive_complexity(payload)
        output_tokens = _derive_output_tokens(payload)
        user_text = "\n".join([
            "APRIL CANONICAL REQUEST",
            f"REQUEST: {current}",
            f"COMPLEXITY: {complexity}",
            f"OUTPUT_CAP: {output_tokens}",
            "Return one complete logical answer as JSON.",
        ])
        user_message = {
            "role": "user",
            "content": [{"type": "input_text", "text": user_text}],
        }

    estimated = system_tokens + _estimate_input_tokens(user_text)
    provider_log({
        "input_token_budget": INPUT_TOKEN_BUDGET,
        "estimated_input_tokens": estimated,
        "input_budget_enforced": estimated <= INPUT_TOKEN_BUDGET,
        "context_strategy": "semantic_field_selection",
        "current_request_truncation": False,
    })

    return [
        {
            "role": "system",
            "content": [{"type": "input_text", "text": PROVIDER_MACHINE_SYSTEM_PROMPT}],
        },
        user_message,
    ]


def _extract_openai_text(response: Any) -> str:
    direct = getattr(response, "output_text", None)
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    pieces = []
    output = getattr(response, "output", None)
    if isinstance(output, (list, tuple)):
        for item in output:
            content = getattr(item, "content", None)
            if isinstance(content, (list, tuple)):
                for part in content:
                    value = getattr(part, "text", None)
                    if isinstance(value, str) and value.strip():
                        pieces.append(value.strip())
                    elif isinstance(part, dict):
                        value = part.get("text") or part.get("value")
                        if isinstance(value, str) and value.strip():
                            pieces.append(value.strip())
    return "\n".join(pieces).strip()


def _parse_provider_json(raw_text: str) -> dict[str, Any]:
    raw = normalize_response_text(raw_text)
    if not raw:
        raise RuntimeError("GPT-5.6 Luna returned no textual output.")

    candidate = raw
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.I)
        candidate = re.sub(r"\s*```$", "", candidate)

    try:
        value = json.loads(candidate)
    except Exception:
        value = None

    if isinstance(value, dict):
        return value

    return {
        "answer": raw,
        "content": raw,
        "summary": _compact_summary(raw, [{"type": "text"}]),
        "scene": {},
        "render_blocks": [{
            "type": "text",
            "content": raw,
            "text": raw,
            "renderer": "TextBlock",
            "viewer": "TextBlock",
        }],
        "artifacts": [],
        "scene_plan": ["text"],
        "render_priority": ["text"],
        "confidence": 0.5,
        "metadata": {"provider_json_invalid": True},
    }


def create_provider_contract(raw_text: Any, source_request: Any = None) -> dict[str, Any]:
    if isinstance(raw_text, dict) and raw_text.get("type") == "provider_response":
        return raw_text

    parsed = raw_text if isinstance(raw_text, dict) else _parse_provider_json(raw_text)
    answer = normalize_response_text(
        parsed.get("answer") or parsed.get("content") or parsed.get("response") or ""
    )

    if not answer:
        for block in parsed.get("render_blocks", []) or []:
            if isinstance(block, dict):
                candidate = normalize_response_text(
                    block.get("content") or block.get("text") or block.get("answer") or ""
                )
                if candidate:
                    answer = candidate
                    break

    if not answer:
        raise RuntimeError("GPT-5.6 Luna returned an empty canonical answer.")

    content = normalize_response_text(parsed.get("content") or answer)
    blocks = _clean_render_blocks(parsed.get("render_blocks", []) or [])
    if not blocks:
        blocks = [{
            "type": "text",
            "content": answer,
            "text": answer,
            "renderer": "TextBlock",
            "viewer": "TextBlock",
            "scene_contract": True,
        }]

    metadata = dict(parsed.get("metadata") or {})
    metadata.update({
        "provider_version": APRIL_QUANTUM_PROVIDER_VERSION,
        "provider_model": APRIL_QUANTUM_PROVIDER_MODEL,
        "provider_calls": 1,
        "single_route": True,
        "summary_visible": False,
        "render_blocks_source": "luna",
    })

    return {
        "type": "provider_response",
        "machine_response": {
            "answer": answer,
            "content": content,
            "response": normalize_response_text(parsed.get("response") or answer),
            "summary": normalize_response_text(parsed.get("summary") or _compact_summary(answer, blocks)),
            "explanation": normalize_response_text(parsed.get("explanation") or ""),
            "scene": dict(parsed.get("scene") or {}),
            "artifacts": list(parsed.get("artifacts") or []),
            "render_blocks": blocks,
            "scene_plan": list(parsed.get("scene_plan") or ["text"]),
            "render_priority": list(parsed.get("render_priority") or []),
            "confidence": parsed.get("confidence", 1.0),
            "provider": "openai",
            "provider_contract": "fiber_v6_quantum",
            "transport_contract": "scene_first",
            "provider_original_answer": answer,
            "provider_original_content": content,
            "metadata": metadata,
        },
        "processor_input": machine_request_to_dict(source_request) if source_request is not None else {},
        "provider_source_request": machine_request_to_dict(source_request) if source_request is not None else {},
        "provider_model": APRIL_QUANTUM_PROVIDER_MODEL,
        "provider_calls": 1,
        "single_route": True,
    }


def provider_finalize_for_executor(contract: dict) -> dict:
    if not isinstance(contract, dict):
        raise RuntimeError("Provider contract must be a dict.")
    mr = contract.setdefault("machine_response", {})
    answer = normalize_response_text(mr.get("answer") or mr.get("content") or mr.get("response") or "")
    if not answer:
        raise RuntimeError("Canonical MachineResponse contains no visible answer.")

    mr["answer"] = answer
    mr["content"] = normalize_response_text(mr.get("content") or answer)
    mr["response"] = normalize_response_text(mr.get("response") or answer)
    mr["summary"] = normalize_response_text(mr.get("summary") or _compact_summary(answer, mr.get("render_blocks") or []))
    mr["render_blocks"] = _clean_render_blocks(mr.get("render_blocks") or [])
    if not mr["render_blocks"] and not mr.get("artifacts"):
        mr["render_blocks"] = [{
            "type": "text",
            "content": answer,
            "text": answer,
            "renderer": "TextBlock",
            "viewer": "TextBlock",
        }]
    mr.setdefault("artifacts", [])
    mr.setdefault("scene", {})
    mr.setdefault("scene_plan", ["text"])
    mr.setdefault("render_priority", [])
    mr.setdefault("metadata", {})
    mr["metadata"].update({
        "provider_model": APRIL_QUANTUM_PROVIDER_MODEL,
        "provider_calls": 1,
        "single_route": True,
        "summary_visible": False,
        "canonical_answer_verified": True,
    })
    return contract


def provider_transport_audit(contract: dict) -> dict:
    mr = contract.setdefault("machine_response", {})
    audit = {
        "answer_length": len(mr.get("answer") or ""),
        "content_length": len(mr.get("content") or ""),
        "summary_length": len(mr.get("summary") or ""),
        "artifact_count": len(mr.get("artifacts") or []),
        "render_block_count": len(mr.get("render_blocks") or []),
        "model": APRIL_QUANTUM_PROVIDER_MODEL,
        "provider_calls": 1,
        "single_route": True,
    }
    mr.setdefault("metadata", {})["provider_audit"] = audit
    return contract


def _extract_usage(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    def read(obj: Any, name: str, default: int = 0) -> int:
        if obj is None:
            return default
        value = getattr(obj, name, None)
        if value is None and isinstance(obj, dict):
            value = obj.get(name, default)
        return int(value) if isinstance(value, (int, float)) else default
    input_tokens = read(usage, "input_tokens")
    output_tokens = read(usage, "output_tokens")
    total = read(usage, "total_tokens", input_tokens + output_tokens)
    details = getattr(usage, "input_tokens_details", None)
    cached = read(details, "cached_tokens")
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached,
        "uncached_input_tokens": max(0, input_tokens - cached),
        "output_tokens": output_tokens,
        "total_tokens": total,
    }


_MODEL_PRICING_PER_MTOK = {
    APRIL_QUANTUM_PROVIDER_MODEL: {
        "input": 1.00,
        "cached_input": 0.10,
        "output": 6.00,
    }
}


def _estimate_usage_cost(model: str, usage: dict[str, int]) -> Optional[float]:
    rates = _MODEL_PRICING_PER_MTOK.get(model)
    if not rates:
        return None
    return round(
        usage.get("uncached_input_tokens", 0) / 1_000_000 * rates["input"]
        + usage.get("cached_input_tokens", 0) / 1_000_000 * rates["cached_input"]
        + usage.get("output_tokens", 0) / 1_000_000 * rates["output"],
        8,
    )


async def generate_text(messages: Any, temperature: Any = None,
                        max_output_tokens: Optional[int] = None,
                        model: str = APRIL_QUANTUM_PROVIDER_MODEL):
    cached = _get_duplicate_cached_response(messages)
    if cached is not None:
        return cached

    source_request = machine_request_to_dict(messages)
    identity = _request_identity(messages)
    lock_key = identity[1] if identity and identity[1] else None
    if lock_key and lock_key in _PROVIDER_INFLIGHT:
        raise RuntimeError("Duplicate in-flight Provider request.")
    if lock_key:
        _PROVIDER_INFLIGHT.add(lock_key)

    try:
        complexity = _derive_complexity(source_request)
        output_tokens = _derive_output_tokens(source_request, max_output_tokens)
        normalized_input = normalize_provider_input(source_request)

        request = {
            "model": APRIL_QUANTUM_PROVIDER_MODEL,
            "input": normalized_input,
            "max_output_tokens": output_tokens,
        }

        provider_log({
            "provider_version": APRIL_QUANTUM_PROVIDER_VERSION,
            "model": APRIL_QUANTUM_PROVIDER_MODEL,
            "complexity": complexity,
            "max_output_tokens": output_tokens,
            "input_token_budget": INPUT_TOKEN_BUDGET,
            "single_call": True,
            "no_model_escalation": True,
        })

        response = _get_openai_client().responses.create(**request)
        usage = _extract_usage(response)
        raw_text = _extract_openai_text(response)
        if not raw_text:
            raise RuntimeError("GPT-5.6 Luna returned no textual output.")

        contract = create_provider_contract(raw_text, source_request=messages)
        contract = provider_finalize_for_executor(contract)
        contract = provider_transport_audit(contract)

        estimated_cost = _estimate_usage_cost(APRIL_QUANTUM_PROVIDER_MODEL, usage)
        mr = contract["machine_response"]
        mr["metadata"].update({
            "provider_usage": usage,
            "provider_estimated_cost_usd": estimated_cost,
            "provider_response_id": getattr(response, "id", None),
            "response_complexity": complexity,
            "response_output_tokens": output_tokens,
            "input_token_budget": INPUT_TOKEN_BUDGET,
        })

        provider_log({
            "provider_usage": usage,
            "estimated_cost_usd": estimated_cost,
            "output_cap": output_tokens,
            "answer_len": len(mr.get("answer") or ""),
            "render_blocks": len(mr.get("render_blocks") or []),
            "artifacts": len(mr.get("artifacts") or []),
        })

        _cache_provider_response(messages, contract)
        return contract
    finally:
        if lock_key:
            _PROVIDER_INFLIGHT.discard(lock_key)


# ============================================================
# Voice / Visual compatibility
# ============================================================

async def transcribe_voice(file_path: str) -> str:
    try:
        with open(file_path, "rb") as handle:
            result = _get_openai_client().audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=handle,
            )
        return normalize_response_text(getattr(result, "text", ""))
    except Exception as exc:
        provider_log("[VOICE] transcription error:", exc)
        return ""


async def analyze_image(path: str, prompt: str):
    """
    Existing visual lane is preserved. Text generation still remains Luna-only.
    """
    try:
        uploaded = _get_gemini_client().files.upload(file=path)
        response = _get_gemini_client().models.generate_content(
            model="gemini-2.5-flash",
            contents=[uploaded, prompt],
        )
        text = normalize_response_text(getattr(response, "text", ""))
        if text:
            return create_provider_contract(text)
    except Exception as exc:
        provider_log("[VISION] Gemini analysis error:", exc)

    raise RuntimeError("Visual provider route failed")


async def generate_image(prompt: str, size: str = "1024x1024", quality: str = "auto"):
    return {
        "success": False,
        "premium_required": True,
        "image_generation_disabled": True,
        "reason": "Image generation is temporarily disabled.",
    }


provider_generate_image = generate_image
