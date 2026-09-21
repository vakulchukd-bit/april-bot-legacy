from __future__ import annotations

import copy
import asyncio
import hashlib
import json
import os
import re
import time
from typing import Any, Dict, Optional

from openai import OpenAI
from blocks.C_ARTIFACT_CONTRACT import BaseArtifact, MachineRequest
from blocks.april_personality import APRIL_IDENTITY

# ============================================================
# APRIL PROVIDER — CANONICAL LUNA ROUTE
# ============================================================

APRIL_QUANTUM_PROVIDER_VERSION = "provider_quantum_luna_3_3_semantic_scene_preservation_v3"
APRIL_QUANTUM_PROVIDER_MODEL = os.getenv("APRIL_OPENAI_MODEL", "gpt-5.6-luna")
APRIL_QUANTUM_PROVIDER_SINGLE_CALL = True
APRIL_QUANTUM_PROVIDER_NO_MODEL_ESCALATION = True
APRIL_QUANTUM_PROVIDER_NO_TEXT_FALLBACK_MODELS = True

OPENAI_PRIMARY_MODEL = APRIL_QUANTUM_PROVIDER_MODEL
OPENAI_BALANCED_MODEL = APRIL_QUANTUM_PROVIDER_MODEL
OPENAI_FAST_MODEL = APRIL_QUANTUM_PROVIDER_MODEL
OPENAI_PREMIUM_MODEL = APRIL_QUANTUM_PROVIDER_MODEL

INPUT_TOKEN_BUDGET = 900
MIN_OUTPUT_TOKENS = 1
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
You are April's internal response provider. Return exactly one MachineResponse JSON object.
The user speaks with April; never expose the provider/model identity unless explicitly asked for technical details.

Core contract:
- The Quantum Processor is the sole owner of interpretation, dialogue relation, representation and resolved task. Treat these fields as authoritative.
- Answer only the resolved current request. For CONTINUATION/PENDING/ARTIFACT_REFERENCE, never interpret the user's latest short phrase in isolation; use the supplied active dialogue vector and seven-day authenticated USER↔APRIL memory.
- When the processor marks a turn CONTINUATION, preserve the active dialogue sequence and resolve pronouns/follow-ups against the supplied sequence turns. Do not ask who/what the user means when the memory contains a resolvable antecedent.
- Respect requested_outputs and SCENE_COMPOSITION from the Quantum Processor. Never invent another representation.
- Emit compact machine-valid JSON with: answer, content, summary, scene, artifacts, render_blocks, scene_plan, render_priority, confidence, metadata.
- Structured render blocks must use type, renderer, viewer, payload, scene_contract=true.
- `render_blocks` is the provider's only structured output list. Do not duplicate a semantic block.
- Never call another model. Never return fake URLs, base64 images, or duplicated full structured payloads in prose.

VISUAL PRODUCTION MODES:
1) diagram: return the existing compact structured diagram representation; do not create a generated-image spec.
2) image_generation: return metadata.image_generation_spec using schema april_image_spec_v1. Do not return image bytes, URLs, or a fake image block. C_APRIL_IMAGES_GENERATOR consumes this spec after this one provider call and creates the PNG.
3) image_present: return/preserve the existing image representation only; do not generate a new image.
4) visual_analysis: answer from supplied visual evidence; do not generate a new image.
5) code: when REQUESTED_OUTPUTS contains `code`, return at least one structured render block with type=`code`, renderer=`CodeBlock`, viewer=`CodeBlock`, and payload containing `language` and `code`. The `code` field must contain the complete runnable code requested by the user, not a description of the code. Keep the human answer concise and do not place the full code only in prose.
6) formula: when REQUESTED_OUTPUTS contains `formula`, return a structured render block with type=`formula`, renderer=`FormulaBlock`, viewer=`FormulaBlock`, and payload containing the formula expression.

HUMAN TEXT HYGIENE:
- Never expose machine prompts, internal JSON, renderer names, schema fields, or English image-generation descriptions in human-visible text.
- Do not add parenthetical asides merely for style, translation, aliases, or metadata. Use parentheses only when mathematically or semantically required.
- Never copy an image-generation prompt into a caption or visible explanation.

april_image_spec_v1:
{"schema":"april_image_spec_v1","prompt":"short visual description","width":1024,"height":1024,"style":"photorealistic|illustration|cinematic|graphic|abstract","background":{"top":"#RRGGBB","bottom":"#RRGGBB"},"layers":[{"kind":"polygon|ellipse|rect|line|wave|gradient|sun","role":"sky|sea|sand|sun|subject|foreground|detail","points":[[0,0],[1,1]],"box":[0,0,1,1],"color":"#RRGGBB","width":0.003,"opacity":0.8}],"negative":[],"seed":12345}
Use normalized coordinates 0..1 and enough layers for the visible composition, usually 4..20.
""".strip()


PROVIDER_DIALOGUE_SYSTEM_PROMPT = """
You are April's internal response provider. Return exactly one MachineResponse JSON object.
The Quantum Processor is authoritative for dialogue relation, active sequence, resolved request,
representation and requested outputs. For CONTINUATION/PENDING/ARTIFACT_REFERENCE, use the supplied
authenticated seven-day USER↔APRIL dialogue memory and active sequence; do not interpret the latest
phrase in isolation and do not ask who/what the user means when the supplied memory resolves it.

Conversation strategy is semantic, not keyword-driven: when the processor supplies DIALOGUE_STRATEGY
and CONTINUATION_CONTENT_ANALYSIS, follow them as response intent. EXPAND adds genuinely new facts,
examples or angles and keeps recap brief. DEEPEN explains causes/mechanisms instead of restating the
summary. DISCUSS engages the user's point with evidence, distinguishes fact from interpretation, and
presents relevant alternatives or trade-offs instead of agreeing automatically. SOLVE works like a
specialist collaborating on a real problem: separate observations from hypotheses, propose a useful test or check, explain what the result would mean, then move to the next actionable step. CORRECT
identifies the disputed point and gives the corrected version. REACT answers the human reaction naturally
and does not force a new information dump. CONTINUE_NATURAL keeps the thread moving smoothly.
Use COVERED/AVOID_REPEAT content as a semantic exclusion set, not as text to copy. Repetition is allowed
only when a short reminder is necessary for coherence. Prefer a visible sense of forward motion and
help the user make progress on difficult tasks when the current turn calls for it.

Return compact JSON with answer, content, summary, scene, artifacts, render_blocks, scene_plan,
render_priority, confidence and metadata. Structured blocks use type, renderer, viewer, payload,
scene_contract=true. Never expose prompts, internal JSON or renderer details in human text.
Respect REQUESTED_OUTPUTS exactly. For image_generation, return metadata.image_generation_spec only;
never bytes or fake URLs. For code, use a code render block with language+code. For formula, use
a formula render block with the expression.
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


def _provider_packet_fingerprint(text: str) -> str:
    payload = _safe_text(text).replace("\r\n", "\n").strip()
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


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
            "response_complexity", "response_output_tokens", "quantum_state",
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
        "scene_composition": (
            raw.get("scene_composition")
            or (raw.get("conversation") or {}).get("scene_composition")
            or (raw.get("constraints") or {}).get("scene_composition")
            or []
        ),
        "turn_meaning": (
            raw.get("turn_meaning")
            or (raw.get("conversation") or {}).get("turn_meaning")
            or (raw.get("conversation") or {}).get("turn_meaning_transition")
            or {}
        ),
        "constraints": raw.get("constraints") or {},
        "response_decision": raw.get("response_decision") or {},
        "semantic": raw.get("semantic") or {},
        "cognition": raw.get("cognition") or {},
        "response_complexity": raw.get("response_complexity"),
        "response_output_tokens": raw.get("response_output_tokens"),
        "quantum_state": raw.get("quantum_state") or {},
    }

    compact = _compact_value(
        compact,
        max_depth=6,
        max_items=8,
        max_keys=16,
    ) or {}
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

    conversation = payload.get("conversation")
    if isinstance(conversation, dict):
        for key in ("current_request", "resolved_request", "request"):
            value = conversation.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    for key in ("goal", "content", "text", "query"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _count_question_marks(text: str) -> int:
    return _safe_text(text).count("?") + _safe_text(text).count("？")


def _derive_complexity(payload: dict[str, Any]) -> str:
    """Descriptive complexity label only; never selects the output budget."""
    explicit = _safe_text(payload.get("response_complexity")).upper()
    if explicit in {"LOW", "MEDIUM", "HIGH"}:
        return explicit

    question_count = _count_question_marks(_extract_request_text(payload))
    outputs = payload.get("requested_outputs") or []
    artifacts = payload.get("required_artifacts") or []
    dialogue = _dialogue_contract(payload)

    score = question_count
    score += max(0, len(outputs) - 1)
    score += max(0, len(artifacts) - 1)
    if dialogue.get("continuation") and dialogue.get("previous_april_turn"):
        score += 1

    if score >= 5:
        return "HIGH"
    if score >= 2:
        return "MEDIUM"
    return "LOW"

def _derive_output_tokens(payload: dict[str, Any], requested: Any = None) -> int:
    """Return the single April response ceiling.

    Input remains separately limited to 900 tokens. Output is intentionally
    independent of representation/renderer/complexity: the model may produce
    any amount required by the current answer up to 8000 tokens, and the whole
    provider result is forwarded to SceneContract and AprilWeb.
    """
    del payload, requested
    return MAX_OUTPUT_TOKENS


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


def _canonical_requested_outputs(payload: dict[str, Any]) -> list[str]:
    """Return the processor-owned multi-output plan without trigger routing."""
    requested = payload.get("requested_outputs") or []
    if isinstance(requested, str):
        requested = [requested]
    result = []
    aliases = {
        "markdown": "text",
        "renderer_scene": "diagram",
        "visual": "graph",
        "image_generate": "image",
    }
    for item in requested:
        name = _safe_text(item).strip().lower()
        name = aliases.get(name, name)
        if name and name not in result:
            result.append(name)
    if any(x != "text" for x in result) and "text" not in result:
        result.insert(0, "text")
    return result or ["text"]


def _strip_duplicate_structured_text(answer: str, requested_outputs: list[str]) -> str:
    """Keep the visible answer aligned with the canonical output plan.

    For text-only turns, structured markdown emitted by the model is not a
    second presentation channel; it is removed so the Web renderer can own
    representation. For explicit table output, the dedicated TableBlock owns
    the table and the prose copy is removed as before.
    """
    if not answer:
        return answer
    text_only = list(requested_outputs or []) == ["text"]
    if not text_only and "table" not in requested_outputs:
        return answer

    lines = answer.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        is_pipe = line.count("|") >= 2
        if is_pipe:
            j = i
            run = 0
            separator = False
            while j < len(lines) and lines[j].count("|") >= 2:
                current = lines[j].strip()
                if re.fullmatch(r"\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?", current):
                    separator = True
                run += 1
                j += 1
            if run >= 3 and separator:
                i = j
                continue
        out.append(line)
        i += 1

    cleaned = "\n".join(out).strip()
    return re.sub(r"\n{3,}", "\n\n", cleaned)



def _artifact_type_and_payload(raw: Any) -> tuple[str, dict[str, Any], str, str, str]:
    """Read provider artifact dictionaries without inventing a new route."""
    if isinstance(raw, BaseArtifact):
        artifact_type = _safe_text(getattr(getattr(raw, "metadata", None), "artifact_type", ""))
        data = dict(getattr(raw, "data", {}) or {})
        signal = data.get("render_signal") if isinstance(data.get("render_signal"), dict) else {}
        payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
        if not payload:
            payload = {
                k: v for k, v in data.items()
                if k not in {"answer", "content", "summary", "render_signal", "presentation", "machine_only", "human_visible"}
            }
        content = normalize_response_text(
            data.get("content") or data.get("answer") or data.get("summary") or ""
        )
        artifact_id = _safe_text(getattr(getattr(raw, "metadata", None), "artifact_id", ""))
        renderer = _safe_text(
            getattr(getattr(raw, "render", None), "web_block", "")
            or signal.get("renderer")
            or ""
        )
        return artifact_type, payload, content, renderer, artifact_id

    if not isinstance(raw, dict):
        return "", {}, _safe_text(raw), "", ""

    data = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    artifact_type = _safe_text(
        raw.get("artifact_type")
        or raw.get("type")
        or data.get("artifact_type")
        or data.get("type")
    ).lower()
    signal = data.get("render_signal") if isinstance(data.get("render_signal"), dict) else {}
    payload = (
        raw.get("payload")
        if isinstance(raw.get("payload"), dict)
        else data.get("payload")
        if isinstance(data.get("payload"), dict)
        else {}
    )
    if not payload:
        payload = {
            k: v for k, v in data.items()
            if k not in {
                "answer", "content", "summary", "render_signal",
                "presentation", "metadata", "artifact_id",
                "artifact_type", "type", "renderer", "viewer",
                "machine_only", "human_visible",
            }
        }
    content = normalize_response_text(
        raw.get("content")
        or raw.get("answer")
        or raw.get("summary")
        or data.get("content")
        or data.get("answer")
        or data.get("summary")
        or signal.get("content")
        or ""
    )
    renderer = _safe_text(
        raw.get("renderer")
        or data.get("renderer")
        or signal.get("renderer")
    )
    artifact_id = _safe_text(
        raw.get("artifact_id")
        or data.get("artifact_id")
        or signal.get("artifact_id")
    )
    return artifact_type, payload, content, renderer, artifact_id


def _materialize_artifacts_as_render_blocks(
    artifacts: Any,
    existing_blocks: list[dict],
) -> list[dict]:
    """
    Project provider artifacts into the same canonical render-block shape used by
    C_ARTIFACT_CONTRACT. This is materialization, not a second route.
    """
    if not isinstance(artifacts, list) or not artifacts:
        return list(existing_blocks or [])

    result = list(existing_blocks or [])
    existing_keys = {
        (
            _safe_text(block.get("type") or block.get("artifact_type")).lower(),
            _safe_text(block.get("artifact_id") or block.get("render_id")),
        )
        for block in result
        if isinstance(block, dict)
    }
    existing_payload_keys = {
        (
            _safe_text(block.get("type") or block.get("artifact_type")).lower(),
            json.dumps(
                block.get("payload")
                if isinstance(block.get("payload"), dict)
                else block.get("table")
                or block.get("graph")
                or block.get("url")
                or block.get("content"),
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )[:8000],
        )
        for block in result
        if isinstance(block, dict)
    }

    renderer_map = {
        "text": "TextBlock",
        "markdown": "MarkdownBlock",
        "table": "TableBlock",
        "graph": "GraphBlock",
        "diagram": "GraphBlock",
        "formula": "FormulaBlock",
        "gallery": "GalleryBlock",
        "image": "GalleryBlock",
        "link": "LinkCard",
        "code": "CodeBlock",
        "function": "FunctionBlock",
    }

    for raw in artifacts:
        artifact_type, payload, content, renderer, artifact_id = _artifact_type_and_payload(raw)
        if not artifact_type:
            continue
        renderer = renderer or renderer_map.get(artifact_type, "TextBlock")
        key = (artifact_type, artifact_id)
        payload_key = (
            artifact_type,
            json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)[:8000],
        )
        if (artifact_id and key in existing_keys) or payload_key in existing_payload_keys:
            continue
        result.append({
            "type": artifact_type,
            "artifact_type": artifact_type,
            "renderer": renderer,
            "viewer": renderer,
            "content": content,
            "text": content,
            "payload": payload,
            "artifact": raw,
            "artifact_id": artifact_id,
            "scene_contract": True,
            "provider_payload": True,
            "canonical_provider_payload": True,
        })
        existing_keys.add(key)
        existing_payload_keys.add(payload_key)

    return result


def _dedupe_render_blocks(blocks: list[dict], answer: str, requested_outputs: list[str]) -> list[dict]:
    """Canonicalize one answer + structured artifacts without losing unique payloads."""
    clean = _clean_render_blocks(blocks)
    result: list[dict] = []
    seen = set()
    text_added = False

    for block in clean:
        btype = _safe_text(block.get("type") or block.get("artifact_type") or "text").lower()
        payload = block.get("payload", block.get("table", block.get("graph", block.get("images", block.get("url")))))
        if btype in {"text", "markdown"}:
            content = normalize_response_text(block.get("content") or block.get("text") or block.get("answer") or "")
            if not content:
                continue
            # Remove an exact duplicate of the canonical answer.
            if text_added and re.sub(r"\s+", " ", content).strip().lower() == re.sub(r"\s+", " ", answer).strip().lower():
                continue
            if text_added and content.strip().lower() == answer.strip().lower():
                continue
            block["type"] = "text"
            block["renderer"] = "TextBlock"
            block["viewer"] = "TextBlock"
            text_added = True
            result.append(block)
            continue

        sig = (btype, json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)[:8000])
        if sig in seen:
            continue
        seen.add(sig)
        result.append(block)

    # Guarantee one text block, but do not duplicate a provider text block.
    if not text_added and answer:
        result.insert(0, {
            "type": "text",
            "content": answer,
            "text": answer,
            "renderer": "TextBlock",
            "viewer": "TextBlock",
            "scene_contract": True,
        })
    return result


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
            "active_entity": dialogue.get("active_entity"),
            "previous_april_turn": dialogue.get("previous_april_turn"),
            "previous_user_turn": dialogue.get("previous_user_turn"),
        }
        fields.append(("DIALOGUE_VECTOR", _compact_value(vector, max_items=6, max_keys=9)))

        strategy = dialogue.get("dialogue_strategy")
        analysis = dialogue.get("continuation_content_analysis")
        if isinstance(strategy, dict) and strategy:
            fields.append(("DIALOGUE_STRATEGY", _compact_value(strategy, max_depth=3, max_items=8, max_keys=12)))
        if isinstance(analysis, dict) and analysis.get("active"):
            # Compact delta only: the provider needs enough prior-content knowledge
            # to avoid repetition, not the entire seven-day ledger in prose.
            delta = {
                "mode": analysis.get("mode"),
                "intent": analysis.get("intent"),
                "active_entity": analysis.get("active_entity"),
                "new_information_required": analysis.get("new_information_required"),
                "novelty_target": analysis.get("novelty_target"),
                "recap_ratio_max": analysis.get("recap_ratio_max"),
                "covered_content": analysis.get("avoid_repeat_content") or analysis.get("covered_content"),
                "next_direction": analysis.get("next_direction"),
            }
            fields.append(("CONTINUATION_CONTENT_ANALYSIS", _compact_value(delta, max_depth=3, max_items=7, max_keys=10)))

        memory = payload.get("memory") if isinstance(payload.get("memory"), dict) else {}
        dialogue_memory = memory.get("dialogue_memory")
        if isinstance(dialogue_memory, dict):
            compact_memory = _compact_value(
                {
                    "window_days": dialogue_memory.get("window_days", 7),
                    "active_sequence": dialogue_memory.get("active_sequence"),
                    "active_sequence_turns": dialogue_memory.get("active_sequence_turns"),
                    "relevant_7d_turns": dialogue_memory.get("relevant_7d_turns"),
                },
                max_depth=5,
                max_items=5,
                max_keys=12,
            )
            if compact_memory:
                fields.append(("SEVEN_DAY_DIALOGUE_MEMORY", compact_memory))

    if continuation and dialogue.get("previous_april_turn"):
        fields.append(("PREVIOUS_APRIL_TURN", dialogue.get("previous_april_turn")))

    if same_goal:
        fields.append(("RESOLVED_GOAL", payload.get("goal")))

    requested_outputs = payload.get("requested_outputs") or []
    required_artifacts = payload.get("required_artifacts") or []
    competencies = payload.get("required_competencies") or []

    if requested_outputs:
        fields.append(("REQUESTED_OUTPUTS", requested_outputs))

    # The scene composition is a semantic decomposition of the current request.
    # Pass it as its own provider context surface so multiple task parts remain
    # distinct instead of being reduced to one dominant representation.
    scene_composition = payload.get("scene_composition")
    if not isinstance(scene_composition, list):
        constraints = payload.get("constraints")
        scene_composition = (
            constraints.get("scene_composition")
            if isinstance(constraints, dict)
            else []
        )
    if isinstance(scene_composition, list) and scene_composition:
        fields.append(("SCENE_COMPOSITION", scene_composition))

    # Turn meaning is the hot semantic memory of the immediately completed turn.
    # It is more authoritative than an old memory summary and should survive
    # input packing whenever the request is a continuation/reference.
    turn_meaning = payload.get("turn_meaning")
    if not isinstance(turn_meaning, dict):
        conversation = payload.get("conversation")
        turn_meaning = (
            conversation.get("turn_meaning_transition")
            if isinstance(conversation, dict)
            else {}
        )
    if isinstance(turn_meaning, dict) and turn_meaning:
        fields.append(("TURN_MEANING", turn_meaning))

    if required_artifacts:
        fields.append(("REQUIRED_ARTIFACTS", required_artifacts))
    if competencies:
        fields.append(("COMPETENCIES", competencies))

    memory = payload.get("memory") if isinstance(payload.get("memory"), dict) else {}
    memory_mode = _safe_text(memory.get("retrieval_mode") or "").lower()
    dynamic_memory = memory.get("dynamic_memory")
    if memory_mode == "memory_query" and dynamic_memory:
        fields.append(("MEMORY_RECALL", dynamic_memory))

    # Visual context is sent only for an actual visual/artifact relation.
    visual = payload.get("visual_context")
    if visual and memory_mode != "memory_query" and (reference or "structured_rendering" in competencies or requested_outputs):
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
        render("REQUESTED_OUTPUTS", payload.get("requested_outputs") or []),
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


def _provider_system_prompt_for_payload(payload: dict[str, Any]) -> str:
    dialogue = _dialogue_contract(payload)
    continuation = bool(dialogue.get("continuation"))
    reference = bool(dialogue.get("reference_to_previous"))
    pending = str(dialogue.get("context_dependency") or "").lower() == "pending"
    return (
        PROVIDER_DIALOGUE_SYSTEM_PROMPT
        if continuation or reference or pending
        else PROVIDER_MACHINE_SYSTEM_PROMPT
    )


def normalize_provider_input(machine_request: Any) -> list[dict]:
    """Build the OpenAI packet inside the canonical 900-token envelope."""
    payload = machine_request_to_dict(machine_request)
    system_prompt = _provider_system_prompt_for_payload(payload)
    system_tokens = _estimate_input_tokens(system_prompt)
    if system_tokens >= INPUT_TOKEN_BUDGET:
        raise RuntimeError("Provider system prompt exceeds canonical 900-token envelope")
    remaining = INPUT_TOKEN_BUDGET - system_tokens

    constraints = payload.get("constraints") if isinstance(payload.get("constraints"), dict) else {}
    plan = constraints.get("representation_plan") if isinstance(constraints.get("representation_plan"), dict) else {}
    metadata = constraints.get("metadata") if isinstance(constraints.get("metadata"), dict) else {}
    mode = _safe_text(plan.get("visual_production_mode") or metadata.get("visual_production_mode") or "").strip()
    request_text = _extract_request_text(payload)
    outputs = list(payload.get("requested_outputs") or [])

    candidates = [
        "APRIL CANONICAL REQUEST",
        f"REQUEST: {request_text}",
        f"VISUAL_PRODUCTION_MODE: {mode}",
        f"REQUESTED_OUTPUTS: {json.dumps(outputs, ensure_ascii=False, separators=(',', ':'))}",
    ]

    # The Processor owns interpretation. For continuation/pending/reference turns
    # send only compact live state so Luna resolves the task in context without
    # re-running a second semantic classifier.
    dialogue = payload.get("dialogue_contract") if isinstance(payload.get("dialogue_contract"), dict) else {}
    if dialogue.get("continuation") or dialogue.get("reference_to_previous") or str(dialogue.get("context_dependency") or "").lower() == "pending":
        compact_context = {
            "relation": dialogue.get("relation"),
            "context_dependency": dialogue.get("context_dependency"),
            "active_task": dialogue.get("active_task"),
            "active_entity": dialogue.get("active_entity"),
            "pending_task": dialogue.get("pending_task"),
            "resolved_request": dialogue.get("resolved_request"),
        }
        candidates.append(
            "LIVE_DIALOGUE_STATE: " + json.dumps(_compact_value(compact_context), ensure_ascii=False, separators=(',', ':'))
        )

        strategy = dialogue.get("dialogue_strategy") if isinstance(dialogue.get("dialogue_strategy"), dict) else {}
        analysis = dialogue.get("continuation_content_analysis") if isinstance(dialogue.get("continuation_content_analysis"), dict) else {}
        if strategy or analysis.get("active"):
            strategy_packet = {
                "mode": strategy.get("mode") or analysis.get("mode"),
                "intent": strategy.get("intent") or analysis.get("intent"),
                "posture": strategy.get("conversational_posture"),
                "new_information_required": strategy.get("new_information_required", analysis.get("new_information_required")),
                "novelty_target": strategy.get("novelty_target", analysis.get("novelty_target")),
                "recap_ratio_max": strategy.get("recap_ratio_max", analysis.get("recap_ratio_max")),
                "active_entity": dialogue.get("active_entity") or analysis.get("active_entity"),
                "expertise_behavior": strategy.get("expertise_behavior") or analysis.get("expertise_behavior"),
                "covered_content": (analysis.get("avoid_repeat_content") or analysis.get("covered_content") or [])[:4],
                "next_direction": strategy.get("next_direction") or analysis.get("next_direction"),
            }
            candidates.append(
                "CONTINUATION_PLAN: " + json.dumps(
                    _compact_value(strategy_packet, max_depth=3, max_items=6, max_keys=9),
                    ensure_ascii=False, separators=(',', ':')
                )
            )

        memory = payload.get("memory") if isinstance(payload.get("memory"), dict) else {}
        dialogue_memory = memory.get("dialogue_memory")
        if isinstance(dialogue_memory, dict):
            active_turns = dialogue_memory.get("active_sequence_turns") or []
            # The continuation plan already carries the previous-answer delta and
            # covered content. Keep only the last two user/assistant turns here so
            # the 900-token envelope retains headroom for the actual request.
            recent_turns: list[dict[str, str]] = []
            for turn in (active_turns[-2:] if isinstance(active_turns, list) else []):
                if not isinstance(turn, dict):
                    continue
                user_turn = _safe_text(turn.get("user_request") or turn.get("user_meaning"))[:180]
                answer_turn = _safe_text(turn.get("april_answer") or turn.get("april_meaning"))[:320]
                if user_turn or answer_turn:
                    recent_turns.append({"user": user_turn, "answer": answer_turn})
            compact_dialogue_memory = {
                "window_days": dialogue_memory.get("window_days", 7),
                "active_sequence_turns": recent_turns,
            }
            if str(dialogue.get("context_dependency") or "").lower() == "recall":
                compact_dialogue_memory["relevant_7d_turns"] = (dialogue_memory.get("relevant_7d_turns") or [])[:2]
            candidates.append(
                "SEVEN_DAY_DIALOGUE_MEMORY: "
                + json.dumps(
                    _compact_value(
                        compact_dialogue_memory,
                        max_depth=5,
                        max_items=4,
                        max_keys=9,
                    ),
                    ensure_ascii=False,
                    separators=(',', ':'),
                )
            )
        candidates.append("PROCESSOR_AUTHORITY: relation, task, representation, resolved_request and continuation strategy are authoritative; use the live active sequence for current-turn context and treat generic memory as evidence-only.")

    visual_context = payload.get("visual_context")
    if isinstance(visual_context, dict) and visual_context:
        compact_visual = _compact_value(visual_context, max_depth=2, max_items=3, max_keys=12)
        candidates.append(
            "VISUAL_CONTEXT: " + json.dumps(compact_visual, ensure_ascii=False, separators=(',', ':'))
        )

    candidates.append(
        "OUTPUT_CONTRACT: return exactly the requested representation(s); never add graph/diagram/image/link blocks that are not in REQUESTED_OUTPUTS."
    )
    if mode == "image_generation":
        candidates.append("IMAGE_GENERATION_MODE: return compact JSON containing metadata.image_generation_spec; never return image bytes, URLs, or fake image blocks.")
    elif mode == "diagram":
        candidates.append("DIAGRAM_MODE: preserve the existing compact structured diagram representation.")

    selected=[]
    for piece in candidates:
        if _estimate_input_tokens("\n".join(selected+[piece])) <= remaining:
            selected.append(piece)

    if not any(x.startswith("REQUEST:") for x in selected):
        minimal=f"REQUEST: {request_text}"
        if _estimate_input_tokens(minimal) > remaining:
            raise RuntimeError("Provider input budget exceeded: current request cannot fit inside 900 tokens")
        selected=["APRIL CANONICAL REQUEST", minimal]
        if mode and _estimate_input_tokens("\n".join(selected+[f"VISUAL_PRODUCTION_MODE: {mode}"])) <= remaining:
            selected.append(f"VISUAL_PRODUCTION_MODE: {mode}")

    user_text="\n".join(selected)
    estimated_total=system_tokens+_estimate_input_tokens(user_text)
    if estimated_total > INPUT_TOKEN_BUDGET:
        raise RuntimeError(f"Provider input budget invariant failed: {estimated_total} > {INPUT_TOKEN_BUDGET}")

    provider_log({
        "input_token_budget": INPUT_TOKEN_BUDGET,
        "estimated_input_tokens": estimated_total,
        "input_budget_enforced": True,
        "context_strategy": "semantic_visual_route_compact",
        "current_request_truncation": False,
        "history_sent_to_provider": False,
        "dialogue_memory_sent_to_provider": bool(
            dialogue.get("continuation")
            or dialogue.get("reference_to_previous")
            or str(dialogue.get("context_dependency") or "").lower() == "pending"
        ),
        "dialogue_system_prompt": system_prompt is PROVIDER_DIALOGUE_SYSTEM_PROMPT,
        "visual_production_mode": mode,
        "canonical_packet_fingerprint": _provider_packet_fingerprint(user_text),
    })

    return [
        {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
        {"role": "user", "content": [{"type": "input_text", "text": user_text}]},
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


def _unwrap_model_answer(value: Any) -> str:
    """Extract the human answer when the model accidentally returns its own JSON envelope."""
    if not isinstance(value, str):
        return normalize_response_text(value)
    text = normalize_response_text(value)
    if not text or not text.lstrip().startswith("{"):
        return text
    try:
        obj = json.loads(text)
    except Exception:
        return text
    if not isinstance(obj, dict):
        return text
    for key in ("answer", "content", "response", "summary", "final_text", "text"):
        candidate = obj.get(key)
        if isinstance(candidate, str) and candidate.strip():
            nested = normalize_response_text(candidate)
            if nested and nested != text:
                return _unwrap_model_answer(nested)
    return text


def _sanitize_render_block_texts(blocks: Any, answer: str) -> list:
    sanitized = []
    for block in list(blocks or []):
        if not isinstance(block, dict):
            continue
        item = dict(block)
        block_type = str(item.get("type") or item.get("artifact_type") or "").strip().lower()
        if block_type in {"text", "markdown"}:
            raw = item.get("content") or item.get("text") or item.get("answer") or ""
            clean = _unwrap_model_answer(raw)
            if not clean or (clean.lstrip().startswith("{") and "render_blocks" in clean):
                clean = answer
            item["content"] = clean
            item["text"] = clean
        sanitized.append(item)
    return sanitized


def create_provider_contract(raw_text: Any, source_request: Any = None) -> dict[str, Any]:
    if isinstance(raw_text, dict) and raw_text.get("type") == "provider_response":
        return raw_text

    parsed = raw_text if isinstance(raw_text, dict) else _parse_provider_json(raw_text)
    answer = _unwrap_model_answer(
        parsed.get("answer") or parsed.get("content") or parsed.get("response") or ""
    )
    source_payload = machine_request_to_dict(source_request) if source_request is not None else {}
    source_constraints = source_payload.get("constraints") if isinstance(source_payload.get("constraints"), dict) else {}
    source_plan = source_constraints.get("representation_plan") if isinstance(source_constraints.get("representation_plan"), dict) else {}
    source_metadata = source_constraints.get("metadata") if isinstance(source_constraints.get("metadata"), dict) else {}
    visual_mode = _safe_text(source_plan.get("visual_production_mode") or source_metadata.get("visual_production_mode") or "").lower()

    if not answer:
        for block in parsed.get("render_blocks", []) or []:
            if isinstance(block, dict):
                candidate = normalize_response_text(
                    block.get("content") or block.get("text") or block.get("answer") or ""
                )
                if candidate:
                    answer = candidate
                    break

    if not answer and visual_mode == "image_generation":
        candidate_metadata = parsed.get("metadata") if isinstance(parsed.get("metadata"), dict) else {}
        candidate_spec = candidate_metadata.get("image_generation_spec")
        if not isinstance(candidate_spec, dict):
            candidate_spec = parsed.get("image_generation_spec") if isinstance(parsed.get("image_generation_spec"), dict) else None
        if isinstance(candidate_spec, dict):
            answer = "Готово — изображение подготовлено."
    if not answer:
        raise RuntimeError("GPT-5.6 Luna returned an empty canonical answer.")

    # Never preserve a machine JSON envelope as visible content. The canonical
    # human content follows the already-unwrapped answer.
    content = _unwrap_model_answer(parsed.get("content") or answer)
    if not content:
        content = answer
    blocks = _sanitize_render_block_texts(
        _clean_render_blocks(parsed.get("render_blocks", []) or []),
        answer,
    )

    if not blocks:
        blocks = [{
            "type": "text",
            "content": answer,
            "text": answer,
            "renderer": "TextBlock",
            "viewer": "TextBlock",
            "scene_contract": True,
        }]

    raw_metadata = parsed.get("metadata")
    metadata = dict(raw_metadata) if isinstance(raw_metadata, dict) else {}
    if "image_generation_spec" not in metadata and isinstance(
        parsed.get("image_generation_spec"), dict
    ):
        metadata["image_generation_spec"] = parsed.get("image_generation_spec")
    raw_scene = parsed.get("scene")
    scene = dict(raw_scene) if isinstance(raw_scene, dict) else {}
    raw_artifacts = parsed.get("artifacts")
    artifacts = list(raw_artifacts) if isinstance(raw_artifacts, list) else []
    raw_scene_plan = parsed.get("scene_plan")
    scene_plan = list(raw_scene_plan) if isinstance(raw_scene_plan, list) else ([str(raw_scene_plan)] if raw_scene_plan else ["text"])
    raw_render_priority = parsed.get("render_priority")
    render_priority = list(raw_render_priority) if isinstance(raw_render_priority, list) else []

    source_payload = machine_request_to_dict(source_request) if source_request is not None else {}

    # Current-request authority: when the Processor requested text only, a
    # model-side table/graph/link is not allowed to manufacture a second
    # presentation. Preserve only text/markdown blocks in that case.
    source_outputs = list(source_payload.get("requested_outputs") or [])
    if source_outputs and all(str(x).lower() in {"text", "markdown"} for x in source_outputs):
        blocks = [
            block for block in blocks
            if str(block.get("type") or block.get("artifact_type") or "").lower() in {"text", "markdown"}
        ]
    metadata.update({
        "provider_version": APRIL_QUANTUM_PROVIDER_VERSION,
        "provider_model": APRIL_QUANTUM_PROVIDER_MODEL,
        "provider_calls": 1,
        "single_route": True,
        "summary_visible": False,
        "render_blocks_source": "luna",
        "requested_outputs": list(source_payload.get("requested_outputs") or []),
        "response_budget": source_payload.get("response_output_tokens"),
    })

    return {
        "type": "provider_response",
        "machine_response": {
            "answer": answer,
            "content": content,
            "response": _unwrap_model_answer(parsed.get("response") or answer),
            "summary": _unwrap_model_answer(parsed.get("summary") or _compact_summary(answer, blocks)),
            "explanation": normalize_response_text(parsed.get("explanation") or ""),
            "scene": scene,
            "artifacts": artifacts,
            "render_blocks": blocks,
            "scene_plan": scene_plan,
            "render_priority": render_priority,
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

    source = contract.get("processor_input")
    payload = source if isinstance(source, dict) else {}
    requested_outputs = _canonical_requested_outputs(payload)
    identity_request = bool((payload.get("constraints") or {}).get("metadata", {}).get("identity_request")) if isinstance(payload.get("constraints"), dict) else False
    if identity_request:
        requested_outputs = ["text"]
    mr.setdefault("metadata", {})["canonical_output_plan_before_finalize"] = list(requested_outputs)

    # Remove duplicated full structured representations from the narrative channel.
    answer = _strip_duplicate_structured_text(answer, requested_outputs)

    constraints = payload.get("constraints", {}) if isinstance(payload.get("constraints"), dict) else {}
    metadata = constraints.get("metadata", {}) if isinstance(constraints.get("metadata"), dict) else {}
    intent = payload.get("intent") if isinstance(payload.get("intent"), dict) else {}
    identity_request = bool(
        metadata.get("identity_request")
        or intent.get("type") == "self_identification"
        or (constraints.get("dialogue_act") == "self_identification")
    )

    # Identity is a processor-owned semantic decision. Provider never infers it
    # from phrases and never exposes its internal model identity to the user.
    if identity_request:
        identity = APRIL_IDENTITY if isinstance(APRIL_IDENTITY, dict) else {}
        identity_name = _safe_text(identity.get("name") or "April")
        capabilities = identity.get("capabilities") if isinstance(identity.get("capabilities"), list) else []
        capability_text = ", ".join(str(x) for x in capabilities[:6] if x)
        answer = (
            f"Я — {identity_name}. Я веду с тобой единый диалог, понимаю смысл запроса, "
            f"учитываю релевантный контекст и могу работать с текстом, голосом, изображениями "
            f"и структурированными представлениями ответа"
            + (f", включая {capability_text}." if capability_text else ".")
            + " Внутри April использует модельные и вычислительные инструменты, "
              "но пользователь общается именно с April."
        )

    mr["answer"] = answer
    mr["content"] = answer
    mr["response"] = normalize_response_text(mr.get("response") or answer)

    original_blocks = mr.get("render_blocks") or []
    mr["artifacts"] = list(mr.get("artifacts") or [])

    # Structured artifacts are first-class output. If the model returned them
    # without render_blocks, project them into the canonical scene stream once.
    original_blocks = _materialize_artifacts_as_render_blocks(
        mr["artifacts"],
        original_blocks,
    )
    mr["render_blocks"] = _dedupe_render_blocks(
        original_blocks,
        answer,
        requested_outputs,
    )
    mr.setdefault("scene", {})
    mr.setdefault("scene_plan", list(requested_outputs))
    mr.setdefault("render_priority", list(requested_outputs))
    mr.setdefault("metadata", {})

    # Canonical output plan survives Provider untouched.
    mr["metadata"].update({
        "provider_model": APRIL_QUANTUM_PROVIDER_MODEL,
        "provider_calls": 1,
        "single_route": True,
        "summary_visible": False,
        "canonical_answer_verified": True,
        "canonical_output_plan": requested_outputs,
        "duplicate_guard": True,
        "answer_artifact_separation": True,
        "structured_output_deduplication": True,
    })

    # Never create duplicate text blocks for artifact-only plans.
    if requested_outputs != ["text"]:
        mr["metadata"]["structured_outputs"] = [
            x for x in requested_outputs if x != "text"
        ]

    return contract


def provider_transport_audit(contract: dict) -> dict:
    mr = contract.setdefault("machine_response", {})
    audit = {
        "answer_length": len(mr.get("answer") or ""),
        "content_length": len(mr.get("content") or ""),
        "summary_length": len(mr.get("summary") or ""),
        "artifact_count": len(mr.get("artifacts") or []),
        "render_block_count": len(mr.get("render_blocks") or []),
        "text_block_count": sum(1 for b in (mr.get("render_blocks") or []) if isinstance(b, dict) and _safe_text(b.get("type")).lower() in {"text", "markdown"}),
        "table_block_count": sum(1 for b in (mr.get("render_blocks") or []) if isinstance(b, dict) and _safe_text(b.get("type")).lower() == "table"),
        "graph_block_count": sum(1 for b in (mr.get("render_blocks") or []) if isinstance(b, dict) and _safe_text(b.get("type")).lower() in {"graph", "diagram", "visual", "renderer_scene"}),
        "formula_block_count": sum(1 for b in (mr.get("render_blocks") or []) if isinstance(b, dict) and _safe_text(b.get("type")).lower() == "formula"),
        "artifact_materialization": True,
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


# Standard OpenAI API pricing for GPT-5.6 Luna (September 2026).
# Fast service tier is NOT selected by this route, so the standard rates apply.
_MODEL_PRICING_PER_MTOK = {
    APRIL_QUANTUM_PROVIDER_MODEL: {
        "input": 0.20,
        "cached_input": 0.02,
        "output": 1.20,
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
        # Canonical budget belongs to the MachineRequest/Quantum Processor.
        # The optional argument is accepted for compatibility but never outranks
        # the request's own response budget.
        output_tokens = _derive_output_tokens(source_request, None)
        if not (MIN_OUTPUT_TOKENS <= output_tokens <= MAX_OUTPUT_TOKENS):
            raise RuntimeError("Provider budget outside canonical 1..8000 range")
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

        # OpenAI's synchronous SDK would block the async Web/Telegram event loop.
        # Offload this single call to a worker thread; provider count remains 1.
        response = await asyncio.to_thread(_get_openai_client().responses.create, **request)
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
            "output_budget_mode": "continuous_64_signal_budget",
            "output_budget_source": "QUANTUM_PROCESSOR",
            "output_budget_range": [MIN_OUTPUT_TOKENS, MAX_OUTPUT_TOKENS],
            "quantum_cores": 8,
            "quantum_lanes_per_core": 8,
            "quantum_signal_count": 64,
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

        transcript = normalize_response_text(
            getattr(result, "text", "")
        )

        provider_log(
            "[VOICE] transcription completed:",
            {"has_text": bool(transcript), "chars": len(transcript)},
        )

        return transcript

    except Exception as exc:
        provider_log("[VOICE] transcription error:", exc)
        # Keep an actual transcription-service failure distinguishable from a
        # successful transcription that simply contains no words.
        raise RuntimeError("VOICE_TRANSCRIPTION_FAILED") from exc


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


# Image generation has no Provider implementation.
# Image creation belongs exclusively to C_APRIL_IMAGES_GENERATOR.
# Text generation, voice transcription, and visual analysis remain unchanged.
