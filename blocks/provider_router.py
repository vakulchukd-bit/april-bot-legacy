from __future__ import annotations

import copy
import asyncio
import hashlib
import json
import os
import re
import time
import ast
import operator
from xml.etree import ElementTree as ET
from typing import Any, Dict, Optional

from openai import OpenAI
from blocks.C_ARTIFACT_CONTRACT import BaseArtifact, MachineRequest
from blocks.april_personality import APRIL_IDENTITY
from blocks.presentation_formatter import canonical_payload_for_block, validate_render_block_payload

# ============================================================
# APRIL PROVIDER — CANONICAL LUNA ROUTE
# ============================================================

APRIL_QUANTUM_PROVIDER_VERSION = "provider_quantum_luna_3_5_visual_plan_complement_v3_dynamic_dialogue"
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
April's internal response provider. Return exactly one MachineResponse JSON object.

The Quantum Processor owns interpretation, dialogue relation, resolved task, representation,
requested outputs and reference resolution. Treat those fields as authoritative.
When DIALOGUE_RULES/RESPONSE_SEQUENCE/TASK_RESULT_STATE are supplied, they are semantic dialogue
context. DIALOGUE_RULES is internal-only metadata. It must never create a visible prefix, counter,
letter, number, marker, or formatting token. RESPONSE_SEQUENCE is internal conversation position only.
Never derive visible formatting from task_response_count, sequence_turn_index, branch labels, task IDs,
or internal response paths. The current request is authoritative over stale branch/topic state.
Answer the resolved current request only. For continuation turns use only the supplied active branch context. For branch recall, use the
explicitly selected recalled branch. For comparisons, use only the explicitly supplied linked branches
and answer the current comparison. Never reselect memory or turn an internal branch label into visible text.
For independent turns do not import historical context.

DIALOGUE_DEVELOPMENT is the authoritative semantic trajectory: preserve the active topic,
goal, relevant result, open work and user-requested future actions. Help a hesitant user with
one useful next step when the semantic state shows a stall, but never invent a goal, turn
keywords into commands, force a question, repeat covered content, or create another route.
Keep all structured and visual output inside the same current SceneContract response.

Return compact JSON with:
answer, content, summary, scene, artifacts, render_blocks, scene_plan, render_priority,
confidence, metadata.

The `answer` field is mandatory and MUST contain the actual human-visible answer.
Never return an empty object, an empty answer, or `{}`. For a simple text/math request,
put the direct answer in `answer` and mirror it in `content` and a text render block.
If structured output is requested, keep its render block structured and complete:
type, renderer, viewer, payload, scene_contract=true.
Preserve every requested representation and never invent an unrequested one.
For `image_generation`, return one semantic generation handoff only:
`metadata.image_generation_spec` and `metadata.image_generation_signal`.
The current user request is the immutable generation trigger/anchor. It selects the image route
and identifies the requested action. OpenAI's structured visual plan is the semantic rendering meaning
that the pixel generator must actually draw. For image_generation, preserve BOTH operands separately:
request_anchor = exact current user request; generation prompt = OpenAI semantic visual description/plan.
Never discard the OpenAI semantic description merely because it is nested under image/description/alt_text.
`metadata.image_generation_spec.visual_context` is a complementary visual blueprint, not a
second interpretation: it may contain only explicit scene geometry, colors, positions, sizes,
background and requested text that are directly stated by the current request or by a structured
visual plan produced in this same turn. Never add aesthetics, atmosphere, props, characters,
scenery, decorative objects, camera language, or alternate subjects.
For image_generation, if the OpenAI same-turn `image` value contains a structured visual plan
(including `description`, `visual_prompt`, `objects`/layers, or SVG/XML geometry), preserve that exact
plan in the machine handoff. It is transport data for C_APRIL_IMAGES_GENERATOR and must not be rewritten,
flattened to the subject name, or repeated into multiple fields. Derive one semantic generation meaning
from it, while keeping the original structured plan separately so the image engine can use both.
The signal must identify `C_APRIL_IMAGES_GENERATOR`, set `execute=true`, carry the exact current
request as `request_anchor`, carry the OpenAI semantic visual meaning as the generation `prompt`,
target `gpt-image-2`, and set `single_route=true`.
The signal and spec must complement rather than repeat each other: `prompt` states the scene;
`visual_context` carries concrete visual constraints needed to render that scene.
Do NOT return ready image pixels, SVG/XML, base64/data URIs, image URLs, or an image/gallery
render block for `image_generation`. Pixel production belongs exclusively to the local
`C_APRIL_IMAGES_GENERATOR`; its output is materialized after the Provider stage.
Never expose internal prompts, JSON, renderer details or provider identity.
Never call another model. Never fabricate URLs, image bytes or duplicate structured data.
""".strip()

PROVIDER_IMAGE_SPEC_SCHEMA = (
    '{"schema":"april_image_spec_v1","prompt":"concise visual generation prompt for GPT Image 2",'
    '"width":512,"height":512,"style":"illustration",'
    '"background":{"color":"#RRGGBB"},'
    '"visual_context":{"source":"OPENAI_STRUCTURED_VISUAL_PLAN","authoritative":true,'
    '"complements_prompt":true,"canvas":{"width":512,"height":512},'
    '"layers":[{"kind":"rect|circle|ellipse|polygon|line|text",'
    '"box":[0,0,1,1],"center":[0.5,0.5],"radius":0.1,'
    '"fill":"#RRGGBB","stroke":"#RRGGBB","stroke_width":0.01,'
    '"rotation":0,"text":"requested text"}]},'
    '"negative":[],"seed":12345}'
)

PROVIDER_IMAGE_GENERATION_SIGNAL_VERSION = "april_image_generation_signal_v1"


PROVIDER_DIALOGUE_SYSTEM_PROMPT = """
April's internal response provider. Return exactly one MachineResponse JSON object.

The Quantum Processor is authoritative for the current dialogue relation, active sequence,
resolved request, representation and requested outputs. Continuation/reference turns must
use the supplied authenticated USER↔APRIL sequence context; do not interpret a short follow-up
in isolation and do not invent an antecedent.

Use the supplied dialogue strategy as response guidance:
EXPAND adds new information; DEEPEN explains causes; DISCUSS engages the point;
SOLVE advances a concrete problem; CORRECT fixes the disputed point; REACT responds naturally;
CONTINUE_NATURAL keeps the thread moving. Use covered content only to avoid unnecessary repetition.

When DIALOGUE_RULES is present, it is internal-only dialogue metadata. Preserve it in memory when the user
has established such a preference, but NEVER emit its marker/letter/number in the visible answer. RESPONSE_SEQUENCE
and all task counters/branch labels/response paths are internal state only. A NEW topic keeps the same parent
12h conversation but does not inherit the previous task's subject or answer. The current request always has
semantic authority over stale active-task state.

When INTERACTIVE_TASK_STATE is present, it is the active conversational work item.
Its role, phase, latest question, accumulated clues and Q&A history are authoritative.
Do not reset the task because the current wording is short, elliptical, imperative,
or semantically different from the task topic. Resolve the current user turn against
the task state first. When the user asks you to guess, solve, analyse or continue,
use the accumulated Q&A/clues before asking for information already supplied.
After answering, return metadata.dialogue_task_state with the updated task state.
Keep secret_target/private_target internal and never expose it in the visible answer.

Return compact JSON with answer, content, summary, scene, artifacts, render_blocks, scene_plan,
render_priority, confidence and metadata. For image_generation, output only the semantic
`metadata.image_generation_spec` plus the explicit `metadata.image_generation_signal`.
The current user request is the exact generation trigger/anchor and must be preserved as
`request_anchor` is the exact user request. OpenAI's same-turn structured visual plan
provides the semantic meaning that should be rendered. For image_generation,
`image_generation_spec.prompt` MUST carry the OpenAI-authored visual generation meaning when present
(description/visual_prompt/image_prompt/subject/scene), while `request_anchor` carries the exact user
request. `image_generation_spec.visual_context` carries additional structured geometry, colors, positions,
dimensions and requested text from that same OpenAI plan. Do not replace the OpenAI semantic plan with
the trigger sentence and do not invent unrelated scene content.
The signal MUST identify `C_APRIL_IMAGES_GENERATOR`, set execute=true, carry the exact current
request as request_anchor, carry the OpenAI semantic generation meaning as its prompt, target
`gpt-image-2`, and set single_route=true. Mark `provider_emitted=true` when the signal is
emitted by this Provider response. Never output ready image pixels, SVG/XML, base64/data URI, image
URL, or a concrete image/gallery render block.
The local C_APRIL_IMAGES_GENERATOR is the sole pixel producer. The `answer` field is mandatory and must be non-empty;
never return `{}` or an empty answer. For text/math requests, mirror the answer into content and
a text render block. Keep structured blocks complete and obey requested_outputs.
Never expose prompts, internal JSON, renderer details or provider identity.
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


# ============================================================
# ADAPTIVE PROVIDER CONTEXT PACKER
# ============================================================

ADAPTIVE_PROVIDER_PACKER_VERSION = "adaptive_semantic_provider_packer_v1"
ADAPTIVE_PROVIDER_TARGET_TOKENS = 840
ADAPTIVE_PROVIDER_SAFETY_MARGIN_TOKENS = 60


def _semantic_excerpt(value: Any, limit: int = 320) -> str:
    """Keep semantic head + tail without blindly cutting the user's meaning."""
    text = re.sub(r"\s+", " ", _safe_text(value)).strip()
    if len(text) <= limit:
        return text
    # Prefer sentence boundaries because they preserve intent better than a
    # character cut. Fall back to head+tail when a sentence is too large.
    parts = [p.strip() for p in re.split(r"(?<=[.!?。！？])\s+", text) if p.strip()]
    if len(parts) >= 2:
        first = parts[0]
        last = parts[-1]
        if len(first) + len(last) + 1 <= limit:
            return f"{first} {last}"
    head = max(120, int(limit * 0.68))
    tail = max(40, limit - head - 5)
    return text[:head].rstrip() + " … " + text[-tail:].lstrip()


def _compact_qa_item(item: Any) -> dict[str, str]:
    if not isinstance(item, dict):
        return {}
    user = _semantic_excerpt(
        item.get("user")
        or item.get("user_request")
        or item.get("user_meaning")
        or item.get("question"),
        150,
    )
    answer = _semantic_excerpt(
        item.get("assistant_prompt")
        or item.get("april_answer")
        or item.get("april_meaning")
        or item.get("answer"),
        190,
    )
    result: dict[str, str] = {}
    if user:
        result["u"] = user
    if answer:
        result["a"] = answer
    return result


def _build_adaptive_task_digest(
    task_state: dict[str, Any],
    task_memory: dict[str, Any],
    *,
    history_limit: int = 2,
    clue_limit: int = 3,
) -> dict[str, Any]:
    """Build the smallest task state that still preserves the active meaning.

    The full task remains in April memory. Provider receives only the fields that
    are necessary to continue the task without duplicating prompt/open_task/task_memory.
    """
    state = task_state if isinstance(task_state, dict) else {}
    memory = task_memory if isinstance(task_memory, dict) else {}

    question = _semantic_excerpt(
        state.get("last_question")
        or state.get("prompt")
        or memory.get("last_question"),
        250,
    )

    raw_history = (
        state.get("qa_history")
        or state.get("turns")
        or memory.get("qa_history")
        or memory.get("turns")
        or []
    )
    history = []
    for item in list(raw_history)[-max(0, history_limit):]:
        compact = _compact_qa_item(item)
        if compact:
            history.append(compact)

    clues = []
    raw_clues = state.get("known_clues") or memory.get("known_clues") or []
    for clue in list(raw_clues)[-max(0, clue_limit):]:
        text = _semantic_excerpt(clue, 100)
        if text:
            clues.append(text)

    digest: dict[str, Any] = {
        "active": True,
        "kind": _safe_text(state.get("kind") or memory.get("kind")),
        "phase": _safe_text(state.get("phase") or memory.get("phase")),
        "expected": _safe_text(
            state.get("expected_input_type") or memory.get("expected_input_type") or "answer"
        ),
        "question": question,
        "topic": _semantic_excerpt(
            state.get("topic") or state.get("canonical_topic") or memory.get("topic"),
            100,
        ),
        "goal": _semantic_excerpt(
            state.get("goal") or state.get("task_goal") or memory.get("goal"),
            110,
        ),
    }

    # IMPORTANT: candidate_answer is never inferred from last_user_answer.
    # last_user_answer can be an ordinary question or instruction and must not
    # become a fake answer candidate inside the Provider task state.
    candidate = _semantic_excerpt(
        state.get("candidate_answer")
        or state.get("answer_candidate")
        or memory.get("candidate_answer")
        or memory.get("answer_candidate"),
        110,
    )
    if candidate:
        digest["candidate"] = candidate

    if history:
        digest["qa"] = history
    if clues:
        digest["clues"] = clues

    return {k: v for k, v in digest.items() if v not in (None, "", [], {})}

def _build_live_dialogue_digest(dialogue: dict[str, Any]) -> dict[str, Any]:
    """Keep only the live conversational facts required for a continuation."""
    contract = dialogue if isinstance(dialogue, dict) else {}
    response_sequence = contract.get("response_sequence") if isinstance(contract.get("response_sequence"), dict) else {}
    dialogue_rules = contract.get("dialogue_rules") if isinstance(contract.get("dialogue_rules"), dict) else {}
    digest: dict[str, Any] = {
        "relation": _safe_text(contract.get("relation")),
        "dependency": _safe_text(contract.get("context_dependency")),
        "topic": _semantic_excerpt(contract.get("canonical_topic"), 120),
        "task_id": _safe_text(contract.get("task_id")),
        "prev_user": _semantic_excerpt(contract.get("previous_user_turn"), 170),
        "prev_april": _semantic_excerpt(contract.get("previous_april_turn"), 220),
    }
    if dialogue_rules:
        digest["dialogue_rules"] = _compact_value(dialogue_rules, max_depth=2, max_items=6, max_keys=8)
    if response_sequence:
        digest["response_sequence"] = _compact_value(response_sequence, max_depth=2, max_items=6, max_keys=8)
    previous_result = contract.get("previous_result") if isinstance(contract.get("previous_result"), dict) else {}
    if previous_result:
        digest["previous_result"] = _compact_value(previous_result, max_depth=2, max_items=8, max_keys=8)
    # Only carry the scene identity when it can matter for reference continuity.
    if contract.get("reference_to_previous") or str(contract.get("context_dependency") or "").lower() in {
        "artifact", "reference", "pending", "recall"
    }:
        scene_id = _safe_text(contract.get("scene_id"))
        if scene_id:
            digest["scene_id"] = scene_id
    return {k: v for k, v in digest.items() if v not in (None, "", [], {})}


def _build_visual_reference_digest(payload: dict[str, Any], dialogue: dict[str, Any]) -> dict[str, Any]:
    """Reference the active visual object without copying large render payloads."""
    digest: dict[str, Any] = {}
    scene_id = _safe_text(
        dialogue.get("scene_id")
        or (dialogue.get("live_scene") or {}).get("scene_id")
        or (payload.get("visual_context") or {}).get("scene_id")
    )
    if scene_id:
        digest["scene_id"] = scene_id

    vc = payload.get("visual_context") if isinstance(payload.get("visual_context"), dict) else {}
    block_types = vc.get("render_block_types") or vc.get("presentation_types") or []
    if block_types:
        digest["types"] = list(dict.fromkeys([_safe_text(x) for x in block_types if _safe_text(x)]))[:4]

    # Keep a selected artifact descriptor, but never copy image bytes / SVG / full
    # shape arrays into the 900-token provider envelope.
    selected = dialogue.get("selected_artifact") if isinstance(dialogue.get("selected_artifact"), dict) else {}
    if not selected and isinstance(payload.get("selected_artifact"), dict):
        selected = payload.get("selected_artifact")
    if selected:
        digest["artifact"] = {
            "type": _safe_text(selected.get("type") or selected.get("artifact_type")),
            "id": _safe_text(selected.get("block_id") or selected.get("render_id") or selected.get("id")),
            "title": _semantic_excerpt(selected.get("title"), 100),
        }
        digest["artifact"] = {
            k: v for k, v in digest["artifact"].items() if v not in (None, "", [], {})
        }

    return {k: v for k, v in digest.items() if v not in (None, "", [], {})}


def _json_piece(label: str, value: Any, *, depth: int = 3, items: int = 6, keys: int = 10) -> str:
    compact = _compact_value(value, max_depth=depth, max_items=items, max_keys=keys)
    return label + ": " + json.dumps(compact, ensure_ascii=False, separators=(",", ":"))


def _shrink_packet_piece(piece: str, limit: int) -> str:
    """Shrink a provider section while preserving JSON meaning when possible."""
    raw = _safe_text(piece).strip()
    if len(raw) <= limit:
        return raw
    if ":" in raw:
        label, payload = raw.split(":", 1)
        payload = payload.strip()
        if payload.startswith(("{", "[")):
            try:
                parsed = json.loads(payload)
                compact = _compact_value(parsed, max_depth=2, max_items=3, max_keys=7)
                candidate = label.strip() + ": " + json.dumps(
                    compact, ensure_ascii=False, separators=(",", ":")
                )
                if len(candidate) <= limit:
                    return candidate
            except Exception:
                pass
    return _semantic_excerpt(raw, limit)


def _adaptive_target_budget(*, mode: str, task_active: bool, continuation: bool) -> int:
    """Choose a floating soft target while preserving the hard 900 invariant."""
    normalized = _safe_text(mode).lower()
    target = 850
    if task_active:
        target -= 25
    if continuation:
        target -= 10
    if normalized in {"image_generation", "diagram", "graph", "table", "formula", "code"}:
        target -= 20
    if normalized in {"image_generation", "diagram"} and task_active:
        target -= 15
    return max(760, min(860, target))


def _compact_packet_value(value: Any, *, depth: int = 0, max_depth: int = 2,
                           max_items: int = 3, max_keys: int = 8,
                           leaf_limit: int = 90) -> Any:
    """Recursively compact provider packet data without losing the newest facts."""
    if depth > max_depth:
        return None
    if value in (None, "", [], {}):
        return None
    if isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _semantic_excerpt(value, leaf_limit)
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in list(value.items())[:max_keys]:
            compact = _compact_packet_value(
                item,
                depth=depth + 1,
                max_depth=max_depth,
                max_items=max_items,
                max_keys=max_keys,
                leaf_limit=leaf_limit,
            )
            if compact not in (None, "", [], {}):
                out[str(key)] = compact
        return out
    if isinstance(value, (list, tuple, set)):
        seq = list(value)
        if len(seq) > max_items:
            seq = seq[-max_items:]
        out = []
        for item in seq:
            compact = _compact_packet_value(
                item,
                depth=depth + 1,
                max_depth=max_depth,
                max_items=max_items,
                max_keys=max_keys,
                leaf_limit=leaf_limit,
            )
            if compact not in (None, "", [], {}):
                out.append(compact)
        return out
    return _semantic_excerpt(_safe_text(value), leaf_limit)


def _compact_packet_piece(piece: str, limit: int, *, label_floor: int = 24) -> str:
    """Compact one provider packet section while preserving its semantic label."""
    raw = _safe_text(piece).strip()
    if len(raw) <= limit:
        return raw
    if ":" not in raw:
        return _semantic_excerpt(raw, max(label_floor, limit))

    label, payload = raw.split(":", 1)
    label = label.strip()
    payload = payload.strip()
    payload_limit = max(24, limit - len(label) - 2)

    if payload.startswith(("{", "[")):
        try:
            parsed = json.loads(payload)
            for leaf_limit, max_items, max_keys, max_depth in (
                (72, 3, 8, 4),
                (54, 2, 6, 3),
                (40, 2, 5, 2),
            ):
                compact = _compact_packet_value(
                    parsed,
                    max_depth=max_depth,
                    max_items=max_items,
                    max_keys=max_keys,
                    leaf_limit=leaf_limit,
                )
                candidate = label + ": " + json.dumps(
                    compact,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    default=str,
                )
                if len(candidate) <= limit:
                    return candidate
        except Exception:
            pass

    return label + ": " + _semantic_excerpt(payload, payload_limit)


def _adaptive_pack(
    system_prompt: str,
    mandatory: list[str],
    optional_tiers: list[tuple[str, str]],
    *,
    hard_budget: int = INPUT_TOKEN_BUDGET,
    target_budget: int = ADAPTIVE_PROVIDER_TARGET_TOKENS,
) -> tuple[str, dict[str, Any]]:
    """Pack provider context with a guaranteed live-continuation packet.

    Required dialogue state is compressed before removal. A short follow-up cannot
    fail merely because the authenticated task history gained another turn.
    """
    prompt = _safe_text(system_prompt).strip()
    selected = list(mandatory)
    dropped: list[str] = []
    compressed: list[str] = []

    def total(text_parts: list[str], prompt_text: str = prompt) -> int:
        return _estimate_input_tokens(prompt_text) + _estimate_input_tokens("\n".join(text_parts))

    if total(selected) > target_budget:
        prompt = (
            "April provider. Return one compact MachineResponse JSON object. "
            "Quantum Processor is authoritative for current request, dialogue relation, "
            "task state and requested outputs. Answer the current request directly. "
            "Preserve requested structured output. Never expose internal state."
        )

    for name, raw_piece in optional_tiers:
        if not raw_piece:
            continue
        variants = [raw_piece]
        for limit in (360, 210, 150, 100):
            compact_piece = _compact_packet_piece(raw_piece, limit)
            if compact_piece not in variants:
                variants.append(compact_piece)
        chosen = None
        for idx, candidate in enumerate(variants):
            if total(selected + [candidate]) <= target_budget:
                chosen = candidate
                if idx > 0:
                    compressed.append(name)
                break
        if chosen is not None:
            selected.append(chosen)
        else:
            dropped.append(name)

    used = total(selected)

    if used > hard_budget:
        for idx in range(len(selected) - 1, len(mandatory) - 1, -1):
            removed = selected.pop(idx)
            dropped.append("hard_trim:" + removed.split(":", 1)[0])
            used = total(selected)
            if used <= hard_budget:
                break

    if used > hard_budget:
        priority_limits = {
            "REQUEST": 360,
            "DIALOGUE_ANCHOR": 220,
            "ACTIVE_TASK": 180,
            "TASK_RESULT_STATE": 180,
            "RESPONSE_SEQUENCE": 160,
            "DIALOGUE_RULES": 140,
            "SEMANTIC_CORE": 140,
            "OUTPUT_CONTRACT": 140,
            "ACTIVE_DIALOGUE_CONTEXT": 150,
            "ACTIVE_DIALOGUE_TRAJECTORY": 150,
            "SEMANTIC_FRAME": 120,
            "DIALOGUE_DEVELOPMENT": 120,
        }
        compacted: list[str] = []
        for piece in mandatory:
            label = piece.split(":", 1)[0].strip().upper()
            limit = priority_limits.get(label, 110)
            compacted_piece = _compact_packet_piece(piece, limit)
            if compacted_piece != piece:
                compressed.append("protected:" + label)
            compacted.append(compacted_piece)
        selected = compacted
        dropped.append("protected_context_recursive_compaction")
        used = total(selected)

    if used > hard_budget:
        removable_labels = [
            "ACTIVE_DIALOGUE_CONTEXT",
            "ACTIVE_DIALOGUE_TRAJECTORY",
            "SEMANTIC_FRAME",
            "DIALOGUE_DEVELOPMENT",
            "OUTPUT_CONTRACT",
            "SEMANTIC_CORE",
        ]
        for remove_label in removable_labels:
            if used <= hard_budget:
                break
            filtered = []
            removed_any = False
            for piece in selected:
                label = piece.split(":", 1)[0].strip().upper()
                if label == remove_label:
                    removed_any = True
                    continue
                filtered.append(piece)
            if removed_any:
                selected = filtered
                dropped.append("redundant_protected_trim:" + remove_label)
                used = total(selected)

    if used > hard_budget:
        pieces_by_label = {
            piece.split(":", 1)[0].strip().upper(): piece
            for piece in selected
            if ":" in piece
        }
        request_piece = next(
            (piece for piece in selected if piece.startswith("REQUEST:")),
            "REQUEST: " + _semantic_excerpt(
                next((x.split(":", 1)[1].strip() for x in selected if x.startswith("REQUEST:")), ""),
                180,
            ),
        )
        final_pieces = [
            request_piece,
            pieces_by_label.get("RELATION", "RELATION: CONTINUE"),
            pieces_by_label.get("REQUESTED", "REQUESTED: [\"text\"]"),
            pieces_by_label.get("RESPONSE_SEQUENCE", ""),
            pieces_by_label.get("DIALOGUE_ANCHOR", ""),
            pieces_by_label.get("TASK_RESULT_STATE", ""),
            pieces_by_label.get("ACTIVE_TASK", ""),
            pieces_by_label.get("DIALOGUE_RULES", ""),
            pieces_by_label.get("RESPONSE_FORMAT", "RESPONSE_FORMAT: Return one complete logical MachineResponse JSON answer."),
        ]
        final_pieces = [x for x in final_pieces if x]

        for limit_map in (
            {"REQUEST": 220, "DIALOGUE_ANCHOR": 180, "TASK_RESULT_STATE": 150, "ACTIVE_TASK": 120, "DIALOGUE_RULES": 100, "RESPONSE_SEQUENCE": 120},
            {"REQUEST": 160, "DIALOGUE_ANCHOR": 150, "TASK_RESULT_STATE": 110, "ACTIVE_TASK": 90, "DIALOGUE_RULES": 80, "RESPONSE_SEQUENCE": 100},
            {"REQUEST": 120, "DIALOGUE_ANCHOR": 120, "TASK_RESULT_STATE": 80, "ACTIVE_TASK": 60, "DIALOGUE_RULES": 60, "RESPONSE_SEQUENCE": 80},
        ):
            trial = []
            for piece in final_pieces:
                label = piece.split(":", 1)[0].strip().upper()
                trial.append(_compact_packet_piece(piece, limit_map.get(label, 100)))
            trial_used = total(trial)
            if trial_used <= hard_budget:
                final_pieces = trial
                used = trial_used
                selected = final_pieces
                break
        else:
            request = next((x.split(":", 1)[1].strip() for x in final_pieces if x.startswith("REQUEST:")), "")
            core = [
                "REQUEST: " + _semantic_excerpt(request, 90),
                pieces_by_label.get("RELATION", "RELATION: CONTINUE"),
                pieces_by_label.get("REQUESTED", "REQUESTED: [\"text\"]"),
                _compact_packet_piece(pieces_by_label.get("RESPONSE_SEQUENCE", "RESPONSE_SEQUENCE: {}"), 72),
                _compact_packet_piece(pieces_by_label.get("DIALOGUE_ANCHOR", "DIALOGUE_ANCHOR: {}"), 110),
                pieces_by_label.get("RESPONSE_FORMAT", "RESPONSE_FORMAT: Return one complete logical MachineResponse JSON answer."),
            ]
            # Keep REQUEST, RELATION and DIALOGUE_ANCHOR as the final semantic core.
            # Remove requested-output metadata before the anchor when space is tight.
            while total(core) > hard_budget and len(core) > 3:
                removed = False
                for label in ("REQUESTED", "RESPONSE_SEQUENCE"):
                    for idx in range(len(core) - 1, -1, -1):
                        if core[idx].split(":", 1)[0].strip().upper() == label:
                            core.pop(idx)
                            removed = True
                            break
                    if removed:
                        break
                if not removed:
                    break
            selected = core
            used = total(selected)
        dropped.append("protected_continuation_packet")

    return "\n".join(selected), {
        "estimated_input_tokens": used,
        "compression_level": (
            "full" if not dropped and not compressed else
            "compact" if len(dropped) <= 1 else
            "compressed" if len(dropped) <= 4 else
            "minimal"
        ),
        "compressed_context": compressed[:20],
        "dropped": dropped[:20],
        "target_budget": target_budget,
        "hard_budget": hard_budget,
    }


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
        "semantic_frame": (
            raw.get("semantic_frame")
            or (raw.get("conversation") or {}).get("semantic_frame")
            or {}
        ),
        "turn_sync": (
            raw.get("turn_sync")
            or (raw.get("conversation") or {}).get("turn_sync")
            or {}
        ),
        "constraints": raw.get("constraints") or {},
        "interpretation_control": (
            raw.get("interpretation_control")
            or (raw.get("constraints") or {}).get("interpretation_control")
            or (raw.get("constraints") or {}).get("metadata", {}).get("interpretation_control")
            or {}
        ),
        "response_decision": raw.get("response_decision") or {},
        "semantic": raw.get("semantic") or {},
        "cognition": raw.get("cognition") or {},
        "cognitive_workspace": (
            raw.get("cognitive_workspace")
            or (raw.get("conversation") or {}).get("cognitive_workspace")
            or raw.get("cognitive_context_plan")
            or (raw.get("constraints") or {}).get("cognitive_context_plan")
            or {}
        ),
        "provider_context_plan": (
            raw.get("provider_context_plan")
            or (raw.get("conversation") or {}).get("provider_context_plan")
            or (raw.get("constraints") or {}).get("provider_context_plan")
            or {}
        ),
        "cognitive_context_plan": (
            raw.get("cognitive_context_plan")
            or (raw.get("constraints") or {}).get("cognitive_context_plan")
            or (raw.get("conversation") or {}).get("cognitive_workspace")
            or raw.get("cognitive_workspace")
            or {}
        ),
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

    # The cognitive workspace is a canonical handoff, not an optional metadata
    # field. Re-attach it after generic key compaction so the provider packer
    # cannot erase the semantic continuation decision.
    workspace_raw = (
        raw.get("cognitive_workspace")
        or (raw.get("conversation") or {}).get("cognitive_workspace")
        or raw.get("cognitive_context_plan")
        or (raw.get("constraints") or {}).get("cognitive_context_plan")
        or {}
    )
    if isinstance(workspace_raw, dict) and workspace_raw:
        compact["cognitive_workspace"] = _compact_value(
            workspace_raw, max_depth=7, max_items=12, max_keys=28
        ) or {}
        compact["cognitive_context_plan"] = compact["cognitive_workspace"]

    provider_plan_raw = (
        raw.get("provider_context_plan")
        or (raw.get("conversation") or {}).get("provider_context_plan")
        or (raw.get("constraints") or {}).get("provider_context_plan")
        or {}
    )
    if isinstance(provider_plan_raw, dict) and provider_plan_raw:
        compact["provider_context_plan"] = _compact_value(
            provider_plan_raw, max_depth=7, max_items=16, max_keys=28
        ) or {}

    # Generic request compaction intentionally stays small, but interactive
    # dialogue is stateful evidence. Restore the bounded task trajectory after
    # generic compaction so the provider can actually reason over the full live
    # Q&A branch instead of receiving only the first few answers.
    compact_dialogue = compact.get("dialogue_contract")
    raw_dialogue = dialogue
    if not isinstance(compact_dialogue, dict):
        compact_dialogue = {}
        compact["dialogue_contract"] = compact_dialogue
    dialogue_relation = _safe_text(
        raw_dialogue.get("relation")
        or raw_dialogue.get("three_way_relation")
        or "NEW"
    ).upper()
    dialogue_sequence_id = _safe_text(
        raw_dialogue.get("sequence_id")
        or raw_dialogue.get("target_sequence_id")
    )
    task_state = (
        raw_dialogue.get("interactive_task_state")
        if isinstance(raw_dialogue.get("interactive_task_state"), dict)
        else raw_dialogue.get("open_task")
        if isinstance(raw_dialogue.get("open_task"), dict)
        else {}
    )
    if isinstance(task_state, dict) and task_state:
        task_sequence_id = _safe_text(task_state.get("sequence_id") or task_state.get("active_sequence_id"))
        task_owned = bool(
            raw_dialogue.get("task_continuation")
            or raw_dialogue.get("task_action")
            or raw_dialogue.get("task_definition")
        )
        if dialogue_sequence_id and task_sequence_id and task_sequence_id != dialogue_sequence_id:
            task_state = {}
        elif dialogue_relation == "NEW" and not task_owned:
            task_state = {}
        elif dialogue_relation == "CONTINUE" and not task_owned:
            task_state = {}
    if isinstance(task_state, dict) and task_state:
        task_state = _compact_value(task_state, max_depth=6, max_items=16, max_keys=20) or {}
        compact_dialogue["interactive_task_state"] = task_state
        compact_dialogue["open_task"] = task_state
        compact_dialogue["active_task"] = task_state
        compact_dialogue["task_memory"] = _compact_value(
            raw_dialogue.get("task_memory") or {
                "role": task_state.get("role"),
                "phase": task_state.get("phase"),
                "last_question": task_state.get("last_question"),
                "known_clues": task_state.get("known_clues"),
                "qa_history": task_state.get("qa_history") or task_state.get("turns"),
                "candidate_answer": task_state.get("candidate_answer"),
            },
            max_depth=6,
            max_items=16,
            max_keys=20,
        ) or {}
        compact_dialogue["task_relation"] = raw_dialogue.get("task_relation") or compact_dialogue.get("task_relation") or {}
        compact_dialogue["task_transition"] = raw_dialogue.get("task_transition") or compact_dialogue.get("task_transition") or {}
        compact_dialogue["task_action"] = bool(raw_dialogue.get("task_action"))

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
    """Return the canonical Web renderer for a semantic artifact type.

    Provider never selects an implementation-specific renderer.  It emits the
    semantic block type and this function only mirrors the canonical
    C_ARTIFACT_CONTRACT → April Web registry.
    """
    return {
        "text": "MessageTextBlock",
        "markdown": "MessageTextBlock",
        "formula": "FormulaRenderer",
        "table": "TableBlock",
        "graph": "GraphBlock",
        "diagram": "GalleryBlock",
        "gallery": "GalleryBlock",
        "image": "GalleryBlock",
        "code": "CodeBlock",
        "link": "LinkCard",
        "file": "LinkCard",
        "audio": "AudioBlock",
        "video": "VideoBlock",
        "action": "ActionBlock",
    }.get(block_type, "MessageTextBlock")


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
    structured = {
        "graph", "table", "diagram", "image", "gallery", "code", "link",
        "file", "audio", "video", "action", "scene", "visual_context",
    }

    for raw in blocks:
        block = dict(raw) if isinstance(raw, dict) else {"type": "text", "content": _safe_text(raw)}
        block_type = _safe_text(block.get("type") or block.get("artifact_type") or "text").lower()
        normalized_type = "text" if block_type == "markdown" else block_type

        content = ""
        for key in ("content", "text", "answer", "message", "value"):
            value = block.get(key)
            if isinstance(value, str) and value.strip():
                content = value.strip()
                break

        canonical_payload = canonical_payload_for_block(block)
        if canonical_payload:
            block["payload"] = canonical_payload

        if normalized_type == "text":
            signature = ("text", re.sub(r"\s+", " ", content).lower())
        else:
            if normalized_type in structured or normalized_type == "formula":
                valid, _reason = validate_render_block_payload(normalized_type, block)
                if not valid:
                    continue
            payload = block.get("payload") or canonical_payload
            if not payload and content:
                payload = {"content": content}
            signature = (
                normalized_type,
                json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)[:4000],
            )

        if signature in seen:
            continue
        seen.add(signature)
        block["type"] = normalized_type
        block["renderer"] = _render_block_renderer(normalized_type)
        block["viewer"] = block["renderer"]
        if normalized_type != "text" and canonical_payload:
            block["payload"] = canonical_payload
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
            # to avoid repetition, not the entire live dialogue ledger in prose.
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
                    "window_hours": dialogue_memory.get("window_hours", 12),
                    "active_sequence": dialogue_memory.get("active_sequence"),
                    "active_sequence_turns": dialogue_memory.get("active_sequence_turns"),
                    "relevant_window_turns": dialogue_memory.get("relevant_window_turns"),
                },
                max_depth=5,
                max_items=5,
                max_keys=12,
            )
            if compact_memory:
                fields.append(("TWELVE_HOUR_DIALOGUE_MEMORY", compact_memory))

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



def _provider_context_plan(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the Interpretation-authored provider context plan, if present.

    Provider never creates or revises this plan. It only serializes it into the
    OpenAI input envelope and applies the hard token budget.
    """
    if not isinstance(payload, dict):
        return {}
    candidates = (
        payload.get("provider_context_plan"),
        (payload.get("conversation") or {}).get("provider_context_plan")
        if isinstance(payload.get("conversation"), dict) else None,
        (payload.get("constraints") or {}).get("provider_context_plan")
        if isinstance(payload.get("constraints"), dict) else None,
    )
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate:
            return candidate
    return {}


def _plan_section_text(section: dict[str, Any]) -> str:
    if not isinstance(section, dict):
        return ""
    key = _safe_text(section.get("key") or section.get("name")).upper()
    if not key:
        return ""
    value = section.get("value")
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
    return f"{key}: {value}"



def _minimal_plan_context(plan: dict[str, Any]) -> dict[str, Any]:
    """Reduce protected Interpretation decisions to a semantic core for emergency packing.

    This is only used when the full selected plan itself is too large. It preserves
    the current turn, relation, core task semantics and output contract rather than
    falling back to a bare request.
    """
    relation = _safe_text(plan.get("relation") or "NEW").upper()
    out: dict[str, Any] = {
        "relation": relation,
        "current_request": _semantic_excerpt(plan.get("current_user_request") or "", 360),
    }

    by_key: dict[str, Any] = {}
    for bucket in ("required_context", "optional_context"):
        for section in list(plan.get(bucket) or []):
            if not isinstance(section, dict):
                continue
            key = _safe_text(section.get("key") or section.get("name")).upper()
            if key and key not in by_key:
                by_key[key] = section.get("value")

    semantic = by_key.get("SEMANTIC_CORE")
    if isinstance(semantic, dict):
        keep = ("intent", "operation", "goal", "domain", "subdomain", "topic", "entity", "representation")
        out["semantic_core"] = {
            key: _semantic_excerpt(semantic.get(key), 100)
            for key in keep
            if semantic.get(key) not in (None, "", [], {})
        }
    elif semantic not in (None, "", [], {}):
        out["semantic_core"] = _semantic_excerpt(semantic, 220)

    contract = by_key.get("OUTPUT_CONTRACT")
    if isinstance(contract, dict):
        keep = ("representation", "requested_outputs", "operation", "render_authorized")
        out["output_contract"] = {
            key: contract.get(key)
            for key in keep
            if contract.get(key) not in (None, "", [], {})
        }
    elif contract not in (None, "", [], {}):
        out["output_contract"] = _semantic_excerpt(contract, 180)

    task = by_key.get("ACTIVE_TASK")
    if isinstance(task, dict):
        keep = (
            "task_id", "sequence_id", "kind", "role", "phase", "expected_input_type", "topic", "goal",
            "last_question", "candidate_answer", "last_user_answer",
            "response_count", "task_response_count", "last_result", "last_answer_basis",
        )
        out["active_task"] = {
            key: _semantic_excerpt(task.get(key), 160)
            for key in keep
            if task.get(key) not in (None, "", [], {})
        }

    rules = by_key.get("DIALOGUE_RULES")
    if isinstance(rules, dict) and rules:
        out["dialogue_rules"] = _compact_value(rules, max_depth=2, max_items=6, max_keys=8)
    sequence = by_key.get("RESPONSE_SEQUENCE")
    if isinstance(sequence, dict) and sequence:
        out["response_sequence"] = _compact_value(sequence, max_depth=2, max_items=6, max_keys=8)
    result_state = by_key.get("TASK_RESULT_STATE")
    if isinstance(result_state, dict) and result_state:
        out["task_result_state"] = _compact_value(result_state, max_depth=3, max_items=6, max_keys=8)

    anchor = by_key.get("DIALOGUE_ANCHOR")
    if isinstance(anchor, dict):
        keep = ("previous_user_turn", "previous_april_turn", "topic", "entity", "turn_relation")
        out["dialogue_anchor"] = {
            key: _semantic_excerpt(anchor.get(key), 180)
            for key in keep
            if anchor.get(key) not in (None, "", [], {})
        }

    development = by_key.get("DIALOGUE_DEVELOPMENT")
    if isinstance(development, dict):
        keep = (
            "relation", "same_dialogue", "sequence_id", "active_topic", "active_goal",
            "active_entity", "current_request", "previous_result", "latest_result_event",
            "open_loops", "pending_obligations", "ready_obligations",
            "user_needs_guidance", "initiative_policy", "next_logical_step",
            "continuation_anchor", "visual_continuity",
        )
        out["dialogue_development"] = {
            key: _compact_value(development.get(key), max_depth=3, max_items=6, max_keys=8)
            for key in keep
            if development.get(key) not in (None, "", [], {})
        }
    elif development not in (None, "", [], {}):
        out["dialogue_development"] = _semantic_excerpt(development, 520)

    memory = by_key.get("MEMORY_RECALL")
    if relation == "RECALL" and memory not in (None, "", [], {}):
        if isinstance(memory, list):
            out["memory_recall"] = [
                _compact_value(item, max_depth=2, max_items=4, max_keys=8)
                for item in memory[:2]
                if isinstance(item, dict)
            ]
        else:
            out["memory_recall"] = _semantic_excerpt(memory, 260)

    return {
        key: value for key, value in out.items()
        if value not in (None, "", [], {})
    }


def _build_provider_user_text_from_plan(
    payload: dict[str, Any],
    plan: dict[str, Any],
    *,
    system_prompt: str,
) -> tuple[str, dict[str, Any]]:
    """Serialize the Interpretation plan without reselecting context.

    Required/optional/excluded context has already been decided upstream.
    The provider packer only performs progressive compression to fit the 900-token
    envelope. The current user request remains the first semantic operand.
    """
    current_request = _safe_text(
        plan.get("current_user_request")
        or (payload.get("intent") or {}).get("normalized_text")
        or _extract_request_text(payload)
    )
    relation = _safe_text(plan.get("relation") or "NEW").upper()
    requested = payload.get("requested_outputs") or []
    if isinstance(requested, str):
        requested = [requested]
    requested = [x for x in requested if _safe_text(x).strip()]

    # A NEW topic is isolated from other task operands, but a dialogue-level rule
    # (for example sequential numbering) still belongs to the authenticated sequence.
    # Preserve only the explicitly protected task-scoped sections; never import old topic data.
    if relation == "NEW" and bool(plan.get("new_topic_minimal_context")):
        sections = {
            _safe_text(x.get("key") or x.get("name")).upper(): x.get("value")
            for x in list(plan.get("required_context") or [])
            if isinstance(x, dict)
        }
        protected_parts = [
            "APRIL CANONICAL REQUEST",
            "REQUEST: " + current_request,
            "RELATION: NEW",
        ]
        rules = sections.get("DIALOGUE_RULES")
        if rules not in (None, "", [], {}):
            protected_parts.append(_json_piece("DIALOGUE_RULES", rules, depth=2, items=6, keys=8))
        sequence = sections.get("RESPONSE_SEQUENCE")
        if sequence not in (None, "", [], {}):
            protected_parts.append(_json_piece("RESPONSE_SEQUENCE", sequence, depth=2, items=6, keys=8))
        result_state = sections.get("TASK_RESULT_STATE")
        if result_state not in (None, "", [], {}):
            protected_parts.append(_json_piece("TASK_RESULT_STATE", result_state, depth=3, items=6, keys=8))
        protected_parts.append("RESPONSE_FORMAT: Return exactly one complete logical answer as MachineResponse JSON.")
        minimal = "\n".join(protected_parts)
        return minimal, {
            "provider_context_plan_version": _safe_text(plan.get("version")),
            "provider_context_authority": "INTERPRETATION",
            "provider_must_not_reselect_context": True,
            "plan_required_selected": ["CURRENT_REQUEST", "DIALOGUE_RULES", "RESPONSE_SEQUENCE", "TASK_RESULT_STATE"],
            "plan_optional_candidates": [],
            "plan_excluded": [
                _safe_text(x.get("key") or x.get("name"))
                for x in list(plan.get("excluded_context") or [])[:32]
                if isinstance(x, dict)
            ],
            "new_topic_minimal_context": True,
            "current_request_length_chars": len(current_request),
            "estimated_input_tokens": _estimate_input_tokens(minimal),
            "hard_budget_tokens": int(plan.get("hard_budget_tokens") or INPUT_TOKEN_BUDGET),
            "soft_target_tokens": int(plan.get("soft_target_tokens") or min(850, INPUT_TOKEN_BUDGET)),
        }

    mandatory: list[str] = [
        "APRIL CANONICAL REQUEST",
        "REQUEST: " + current_request,
        "RELATION: " + relation,
        "REQUESTED: " + json.dumps(requested[:6], ensure_ascii=False, separators=(",", ":")),
        "RESPONSE_FORMAT: Return exactly one complete logical answer as MachineResponse JSON. Use only the supplied context plan.",
    ]

    development = plan.get("dialogue_development")
    # CONTINUE already carries the compact DIALOGUE_ANCHOR +
    # CONTINUATION_INTEREST sections. Serializing a second development object
    # duplicates the same state and consumes the hard input envelope. Keep the
    # development section only for RECALL/other non-continuation paths.
    if development not in (None, "", [], {}) and relation != "CONTINUE":
        mandatory.append(
            _json_piece("DIALOGUE_DEVELOPMENT", development, depth=3, items=4, keys=7)
        )
    if any(_safe_text(x).strip().lower() == "image_generation" for x in requested):
        mandatory.extend([
            "IMAGE_GENERATION_HANDOFF: emit metadata.image_generation_signal in the same response; route=C_APRIL_IMAGES_GENERATOR, execute=true, request_anchor=REQUEST exactly, prompt_source=OPENAI_STRUCTURED_VISUAL_PLAN, target_model=gpt-image-2, single_route=true.",
            "IMAGE_GENERATION_PROMPT_RULE: metadata.image_generation_spec.prompt and image_generation_signal.prompt must carry the OpenAI-authored semantic visual generation meaning; request_anchor remains the exact current user trigger. Preserve the OpenAI-described subject and attributes, and never replace the semantic plan with the trigger sentence.",
            "GPT_IMAGE_2_TARGET: prepare a concrete visual generation prompt for gpt-image-2; one scene, explicit subject first, requested attributes only, no conversational filler, no prior-scene carryover, no pixels/URLs/data URIs/alternate providers.",
        ])

    required = [
        x for x in (plan.get("required_context") or [])
        if isinstance(x, dict) and _safe_text(x.get("key") or x.get("name")).upper() != "CURRENT_REQUEST"
    ]
    optional = [
        x for x in (plan.get("optional_context") or [])
        if isinstance(x, dict)
    ]
    required.sort(key=lambda x: (-float(x.get("priority", 0.0) or 0.0), _safe_text(x.get("key") or x.get("name"))))
    optional.sort(key=lambda x: (-float(x.get("priority", 0.0) or 0.0), _safe_text(x.get("key") or x.get("name"))))

    for section in required:
        key = _safe_text(section.get("key") or section.get("name")).upper()
        if relation == "CONTINUE" and key == "DIALOGUE_DEVELOPMENT":
            # CONTINUATION_INTEREST is the single compact progression contract.
            continue
        piece = _plan_section_text(section)
        if piece:
            mandatory.append(piece)

    optional_tiers: list[tuple[str, str]] = []
    for section in optional:
        piece = _plan_section_text(section)
        if piece:
            optional_tiers.append((
                _safe_text(section.get("key") or section.get("name")).lower(),
                piece,
            ))

    hard = int(plan.get("hard_budget_tokens") or INPUT_TOKEN_BUDGET)
    soft = int(plan.get("soft_target_tokens") or min(850, hard - 50))
    system_tokens = _estimate_input_tokens(system_prompt)
    user_hard = max(1, hard - system_tokens)
    user_target = max(1, min(soft - system_tokens, user_hard))

    user_text, meta = _adaptive_pack(
        "",
        mandatory,
        optional_tiers,
        hard_budget=user_hard,
        target_budget=user_target,
    )

    return user_text, {
        **meta,
        "provider_context_plan_version": _safe_text(plan.get("version")),
        "provider_context_authority": "INTERPRETATION",
        "provider_must_not_reselect_context": True,
        "plan_required_selected": [
            _safe_text(x.get("key") or x.get("name"))
            for x in required[:16]
        ],
        "plan_optional_candidates": [
            _safe_text(x.get("key") or x.get("name"))
            for x in optional[:16]
        ],
        "plan_excluded": [
            _safe_text(x.get("key") or x.get("name"))
            for x in list(plan.get("excluded_context") or [])[:16]
            if isinstance(x, dict)
        ],
        "current_request_length_chars": len(current_request),
    }


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
    """Compatibility view over the single canonical Interpretation handoff."""
    payload = machine_request_to_dict(machine_request)
    packets = normalize_provider_input(payload)
    if len(packets) < 2:
        raise RuntimeError("PROVIDER_CANONICAL_PACKET_INCOMPLETE")
    return packets[-1]



def _provider_system_prompt_for_payload(payload: dict[str, Any]) -> str:
    provider_plan = _provider_context_plan(payload)
    if provider_plan:
        relation = _safe_text(provider_plan.get("relation") or "NEW").upper()
        task_active = bool(provider_plan.get("active_task"))
        recall = relation == "RECALL"
        continuation = relation == "CONTINUE"
        return PROVIDER_DIALOGUE_SYSTEM_PROMPT if continuation or recall or task_active else PROVIDER_MACHINE_SYSTEM_PROMPT

    dialogue = _dialogue_contract(payload)
    workspace = (
        payload.get("cognitive_workspace")
        if isinstance(payload.get("cognitive_workspace"), dict)
        else (payload.get("conversation") or {}).get("cognitive_workspace")
        if isinstance(payload.get("conversation"), dict) and isinstance((payload.get("conversation") or {}).get("cognitive_workspace"), dict)
        else payload.get("cognitive_context_plan")
        if isinstance(payload.get("cognitive_context_plan"), dict)
        else {}
    )
    continuation = bool(workspace.get("continuation") or workspace.get("semantic_continuation")) if workspace else bool(dialogue.get("continuation"))
    reference = bool(workspace.get("reference")) if workspace else bool(dialogue.get("reference_to_previous"))
    pending = str(dialogue.get("context_dependency") or "").lower() == "pending"
    if workspace:
        task_state = workspace.get("active_task_context") if isinstance(workspace.get("active_task_context"), dict) else {}
        task_active = bool(workspace.get("task_continuation"))
    else:
        task_state = (
            dialogue.get("interactive_task_state")
            if isinstance(dialogue.get("interactive_task_state"), dict)
            else dialogue.get("open_task")
            if isinstance(dialogue.get("open_task"), dict)
            else {}
        )
        task_active = bool(
            isinstance(task_state, dict)
            and (
                task_state.get("active")
                or task_state.get("open")
                or task_state.get("kind") in {"game", "riddle", "question", "choice"}
            )
        )
    return (
        PROVIDER_DIALOGUE_SYSTEM_PROMPT
        if continuation or reference or pending or task_active
        else PROVIDER_MACHINE_SYSTEM_PROMPT
    )



def normalize_provider_input(machine_request: Any) -> list[dict]:
    """Build the OpenAI packet with adaptive semantic compression inside 900 tokens."""
    payload = machine_request_to_dict(machine_request)
    system_prompt = _provider_system_prompt_for_payload(payload)

    # Keep a bounded system envelope. The longer dialogue prompt is retained when
    # it fits; otherwise use the compact equivalent rather than failing the turn.
    if _estimate_input_tokens(system_prompt) > 420:
        system_prompt = (
            "April internal response provider. Return exactly one MachineResponse JSON object. "
            "Quantum Processor owns current request, relation, task, representation and context plan. "
            "DIALOGUE_RULES/OUTPUT_RULE/RESPONSE_SEQUENCE are internal semantic metadata only; never emit counters, letters, "
            "markers or branch labels. The current request is authoritative; TASK_RESULT_STATE is supplied history only. "
            "Use only supplied context; never reselect or reinterpret branch state. "
            "do not reselect, search, reinterpret or substitute context. Never expose internal state."
        )

    # New canonical path: Interpretation has already selected context semantically.
    # Provider only serializes and compresses the plan to <= 900 total input tokens.
    provider_plan = _provider_context_plan(payload)
    dialogue_contract = _dialogue_contract(payload)
    if dialogue_contract and not provider_plan:
        raise RuntimeError("DIALOGUE_PROVIDER_PLAN_MISSING")
    if provider_plan:
        authoritative_request = _safe_text(provider_plan.get("current_user_request"))
        payload_request = _extract_request_text(payload)
        if authoritative_request and payload_request and authoritative_request != payload_request:
            raise RuntimeError("INTERPRETATION_REQUEST_MUTATION")
        user_text, plan_meta = _build_provider_user_text_from_plan(
            payload,
            provider_plan,
            system_prompt=system_prompt,
        )
        estimated_total = _estimate_input_tokens(system_prompt) + _estimate_input_tokens(user_text)

        # Absolute last-resort guard: progressively compact the current request while
        # retaining relation/output contract. This branch should rarely execute because
        # _adaptive_pack already enforces the hard envelope.
        if estimated_total > INPUT_TOKEN_BUDGET:
            request_text = _safe_text(
                provider_plan.get("current_user_request")
                or _extract_request_text(payload)
            )
            relation = _safe_text(provider_plan.get("relation") or "NEW").upper()
            outputs = payload.get("requested_outputs") or []
            minimal_context = _minimal_plan_context(provider_plan)
            compact_system = (
                "April provider. Return one MachineResponse JSON object. "
                "Quantum Processor is authoritative. Use only supplied plan context. "
                "Answer the current request and preserve requested output."
            )

            for request_limit in (420, 320, 260, 220, 180, 150, 120, 90, 70, 50):
                candidate_request = _semantic_excerpt(request_text, request_limit)
                for context_limit in (260, 220, 180, 150, 120):
                    context_for_try = dict(minimal_context)
                    context_for_try["current_request"] = candidate_request

                    # Keep the semantic core, output contract and active dialogue/task
                    # in the protected emergency packet. Larger historical payloads
                    # are intentionally omitted rather than allowed to displace meaning.
                    for key, value in list(context_for_try.items()):
                        if key == "current_request":
                            continue
                        if isinstance(value, dict):
                            for inner_key, inner_value in list(value.items()):
                                if isinstance(inner_value, str):
                                    value[inner_key] = _semantic_excerpt(inner_value, context_limit)
                        elif isinstance(value, list):
                            context_for_try[key] = value[:2]

                    candidate_user = (
                        "REQUEST: " + candidate_request + "\n"
                        "RELATION: " + relation + "\n"
                        "CONTEXT_CORE: " + json.dumps(
                            context_for_try,
                            ensure_ascii=False,
                            separators=(",", ":"),
                            default=str,
                        ) + "\n"
                        "REQUESTED: " + json.dumps(outputs[:4], ensure_ascii=False, separators=(",", ":")) + "\n"
                        "RESPONSE_FORMAT: Return one complete logical MachineResponse JSON answer."
                    )
                    trial_total = _estimate_input_tokens(compact_system) + _estimate_input_tokens(candidate_user)
                    if trial_total <= INPUT_TOKEN_BUDGET:
                        system_prompt = compact_system
                        user_text = candidate_user
                        estimated_total = trial_total
                        plan_meta["compression_level"] = "minimal_protected_context"
                        plan_meta["compressed_context"] = list(plan_meta.get("compressed_context") or []) + [
                            "PROTECTED_CONTEXT_EMERGENCY_COMPACTION"
                        ]
                        plan_meta["current_request_semantic_compression"] = request_limit < len(request_text)
                        break
                else:
                    continue
                break
            else:
                raise RuntimeError("PROVIDER_INPUT_BUDGET_PACK_FAILURE")

        # Emit exactly one compact telemetry record for the plan-driven route.
        provider_log({
            "input_token_budget": INPUT_TOKEN_BUDGET,
            "input_budget_target": provider_plan.get("soft_target_tokens"),
            "estimated_input_tokens": estimated_total,
            "input_budget_enforced": True,
            "context_strategy": "interpretation_provider_context_plan_v2",
            "compression_level": plan_meta.get("compression_level"),
            "compressed_context": plan_meta.get("compressed_context") or [],
            "dropped_context": plan_meta.get("dropped") or [],
            "provider_context_plan_version": provider_plan.get("version"),
            "provider_context_authority": "INTERPRETATION",
            "provider_must_not_reselect_context": True,
            "provider_context_required": plan_meta.get("plan_required_selected") or [],
            "provider_context_optional": plan_meta.get("plan_optional_candidates") or [],
            "provider_context_excluded": plan_meta.get("plan_excluded") or [],
            "current_request_semantic_compression": bool(plan_meta.get("current_request_semantic_compression")),
            "current_request_semantics_preserved": True,
            "dialogue_system_prompt": bool(system_prompt == PROVIDER_DIALOGUE_SYSTEM_PROMPT),
            "current_request_length_chars": plan_meta.get("current_request_length_chars", 0),
            "canonical_packet_fingerprint": _provider_packet_fingerprint(user_text),
        })

        return [
            {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": user_text}]},
        ]

    constraints = payload.get("constraints") if isinstance(payload.get("constraints"), dict) else {}
    plan = constraints.get("representation_plan") if isinstance(constraints.get("representation_plan"), dict) else {}
    metadata = constraints.get("metadata") if isinstance(constraints.get("metadata"), dict) else {}
    interpretation_control = (
        payload.get("interpretation_control")
        if isinstance(payload.get("interpretation_control"), dict)
        else constraints.get("interpretation_control")
        if isinstance(constraints.get("interpretation_control"), dict)
        else metadata.get("interpretation_control")
        if isinstance(metadata.get("interpretation_control"), dict)
        else {}
    )

    mode = _safe_text(
        plan.get("visual_production_mode")
        or metadata.get("visual_production_mode")
        or ""
    ).strip()
    request_text = _extract_request_text(payload)
    outputs = list(payload.get("requested_outputs") or [])
    conversation_payload = payload.get("conversation") if isinstance(payload.get("conversation"), dict) else {}
    workspace = (
        payload.get("cognitive_workspace")
        if isinstance(payload.get("cognitive_workspace"), dict)
        else conversation_payload.get("cognitive_workspace")
        if isinstance(conversation_payload.get("cognitive_workspace"), dict)
        else payload.get("cognitive_context_plan")
        if isinstance(payload.get("cognitive_context_plan"), dict)
        else {}
    )
    dialogue = payload.get("dialogue_contract") if isinstance(payload.get("dialogue_contract"), dict) else {}
    semantic_frame = payload.get("semantic_frame") if isinstance(payload.get("semantic_frame"), dict) else {}
    if workspace and isinstance(workspace.get("semantic_frame"), dict):
        # The pre-provider workspace is the canonical semantic handoff. Do not
        # reintroduce the older raw frame after semantic selection has already
        # normalized it.
        semantic_frame = dict(workspace.get("semantic_frame") or {})
    turn_sync = payload.get("turn_sync") if isinstance(payload.get("turn_sync"), dict) else {}

    # Canonical mandatory core. The cognitive workspace owns semantic selection.
    # Provider packing may compact the representation, but it must not make a
    # relevance decision or silently discard the output contract.
    workspace_request = _safe_text(workspace.get("current_request") or "")
    request_excerpt = _semantic_excerpt(workspace_request or request_text, 520)
    output_modes = [str(x) for x in outputs if _safe_text(x).strip()]
    effective_mode = _safe_text(mode or (output_modes[0] if output_modes else "text"))
    mandatory = [
        "APRIL REQUEST CORE",
        "REQUEST: " + request_excerpt,
        "OUTPUT_MODE: " + effective_mode,
        "REQUESTED: " + json.dumps(output_modes[:4], ensure_ascii=False, separators=(",", ":")),
    ]

    # Modality rules are mandatory because they define the shape that downstream
    # rooms/executors must receive. They are intentionally tiny so they cannot
    # crowd out the active task or current request.
    if effective_mode == "image_generation":
        mandatory.append(
            "MODE_RULE: image_generation requires metadata.image_generation_spec with prompt,width,height,style,background,layers,negative,seed."
        )
    elif effective_mode == "diagram":
        mandatory.append(
            "MODE_RULE: return one complete diagram with explicit nodes/edges or vector shapes; no duplicates."
        )
    elif effective_mode == "graph":
        mandatory.append(
            "MODE_RULE: return one complete graph payload with labels, values and axes."
        )
    elif effective_mode == "table":
        mandatory.append(
            "MODE_RULE: return one complete table payload with columns and rows."
        )

    if workspace:
        workspace_contract = workspace.get("output_contract") if isinstance(workspace.get("output_contract"), dict) else {}
        workspace_core = {
            "version": workspace.get("version"),
            "relation": workspace.get("relation"),
            "resolved_request": _semantic_excerpt(workspace.get("resolved_request") or "", 360),
            "active_topic": workspace.get("active_topic"),
            "active_entity": workspace.get("active_entity"),
            "conversation_continuation": bool(workspace.get("conversation_continuation")),
            "semantic_continuation": bool(workspace.get("continuation") or workspace.get("semantic_continuation")),
            "task_continuation": bool(workspace.get("task_continuation")),
            "continuation": bool(workspace.get("continuation")),
            "reference": bool(workspace.get("reference")),
            "active_task": bool(workspace.get("task_continuation")),
            "operation": workspace.get("operation"),
            "goal": workspace.get("goal"),
            "representation": workspace.get("representation"),
            "dependencies": list(workspace.get("context_dependencies") or [])[:8],
            "protected": list(workspace.get("protected_context") or [])[:10],
            "excluded": [
                x.get("key") if isinstance(x, dict) else str(x)
                for x in list(workspace.get("excluded_context") or [])[:8]
            ],
        }
        mandatory.append("COGNITIVE_CORE: " + json.dumps(workspace_core, ensure_ascii=False, separators=(",", ":"), default=str))
        if workspace.get("request_directives"):
            mandatory.append("REQUEST_DIRECTIVES: " + json.dumps(list(workspace.get("request_directives") or [])[:6], ensure_ascii=False, separators=(",", ":"), default=str))
        if workspace.get("request_identifiers") and (effective_mode == "code" or workspace.get("operation") == "build"):
            mandatory.append("REQUEST_IDENTIFIERS: " + json.dumps(list(workspace.get("request_identifiers") or [])[:10], ensure_ascii=False, separators=(",", ":"), default=str))
        mandatory.append("SEMANTIC_FRAME: " + json.dumps(semantic_frame, ensure_ascii=False, separators=(",", ":"), default=str))
        mandatory.append("RENDER_CONTRACT: " + json.dumps({
            "mode": workspace_contract.get("representation") or effective_mode,
            "requested": list(workspace_contract.get("requested_outputs") or output_modes[:4])[:4],
            "authorized": bool(workspace_contract.get("render_authorized")),
            "render_mode": workspace_contract.get("render_mode") or "TEXT_ONLY",
            "structured_required": bool(workspace_contract.get("requested_outputs") and any(x != "text" for x in workspace_contract.get("requested_outputs") or [])),
        }, ensure_ascii=False, separators=(",", ":"), default=str))

    closure_policy = dialogue.get("closure_policy") if isinstance(dialogue.get("closure_policy"), dict) else {}

    relation = _safe_text(dialogue.get("relation") or "")
    dependency = _safe_text(dialogue.get("context_dependency") or "")
    reference = bool(dialogue.get("reference_to_previous"))
    task_state = (
        dialogue.get("interactive_task_state")
        if isinstance(dialogue.get("interactive_task_state"), dict)
        else dialogue.get("open_task")
        if isinstance(dialogue.get("open_task"), dict)
        else {}
    )
    task_sequence_id = _safe_text(task_state.get("sequence_id") or task_state.get("active_sequence_id")) if isinstance(task_state, dict) else ""
    dialogue_sequence_id = _safe_text(
        dialogue.get("sequence_id")
        or dialogue.get("target_sequence_id")
    )
    task_owned = bool(
        dialogue.get("task_continuation")
        or dialogue.get("task_action")
        or dialogue.get("task_definition")
    )
    if dialogue_sequence_id and task_sequence_id and task_sequence_id != dialogue_sequence_id:
        task_state = {}
    elif relation == "NEW" and not task_owned:
        task_state = {}
    elif relation == "CONTINUE" and not task_owned:
        task_state = {}
    task_memory = (
        dialogue.get("task_memory")
        if isinstance(dialogue.get("task_memory"), dict)
        else payload.get("task_memory")
        if isinstance(payload.get("task_memory"), dict)
        else {}
    )
    task_is_active = bool(
        workspace.get("active_task")
        if workspace
        else (
            isinstance(task_state, dict)
            and (
                task_state.get("active")
                or task_state.get("open")
                or task_state.get("kind") in {"game", "riddle", "question", "choice", "logic_riddle"}
            )
        )
    )

    if workspace:
        relation = _safe_text(workspace.get("relation") or relation)
        dependency = "continuation" if workspace.get("continuation") else dependency
        reference = bool(workspace.get("reference"))

    structured_outputs_requested = any(
        _safe_text(x).lower() not in {"text", "markdown"} for x in outputs
    ) or bool(payload.get("required_artifacts"))
    if workspace and isinstance(workspace_contract, dict):
        structured_outputs_requested = structured_outputs_requested or bool(
            workspace_contract.get("requested_outputs")
            and any(_safe_text(x).lower() != "text" for x in workspace_contract.get("requested_outputs") or [])
        )
    render_authorized = bool(
        workspace_contract.get("render_authorized") if workspace else interpretation_control.get("render_authorized")
    )
    visual_relation = bool(
        interpretation_control.get("render_mode") == "ARTIFACT_CONTINUATION"
        or reference
        or str(dependency).lower() in {"artifact", "reference", "pending", "recall"}
        or str(relation).upper() in {"ARTIFACT_REFERENCE", "PENDING", "RECALL"}
    )

    optional: list[tuple[str, str]] = []

    if workspace:
        # The cognitive workspace has already decided relevance. Protected semantic
        # sections are promoted to the provider core; ranked optional sections are
        # passed to the budget packer as candidates.
        required_keys = {
            _safe_text(x.get("key")).upper()
            for x in list(workspace.get("required_context") or [])
            if isinstance(x, dict)
        }
        for section in list(workspace.get("required_context") or []):
            if not isinstance(section, dict):
                continue
            name = _safe_text(section.get("key") or section.get("name"))
            value = section.get("value")
            if not name or value in (None, "", [], {}):
                continue
            if name.upper() in {
                "CURRENT_REQUEST", "SEMANTIC_FRAME", "OUTPUT_CONTRACT",
                "REQUEST_DIRECTIVES", "REQUEST_IDENTIFIERS", "COGNITIVE_CORE",
            }:
                continue
            mandatory.append(
                _json_piece(name.upper(), value, depth=3, items=5, keys=10)
            )

        for section in list(workspace.get("optional_context") or []):
            if not isinstance(section, dict):
                continue
            name = _safe_text(section.get("key") or section.get("name"))
            value = section.get("value")
            if not name or value in (None, "", [], {}):
                continue
            # Do not re-add a field already promoted to the protected core.
            if name.upper() in required_keys:
                continue
            optional.append(
                (name.lower(), _json_piece(name.upper(), value, depth=3, items=5, keys=10))
            )
    else:
        # Legacy compatibility path for callers that do not yet provide the
        # cognitive workspace. It remains secondary to the new semantic workspace.
        if task_is_active:
            task_digest = _build_adaptive_task_digest(
                task_state,
                task_memory,
                history_limit=2,
                clue_limit=3,
            )
            optional.append(("active_task", _json_piece(
                "ACTIVE_TASK", task_digest, depth=3, items=5, keys=10
            )))
            sync_digest = turn_sync or _build_live_dialogue_digest(dialogue)
            if sync_digest:
                optional.append(("turn_sync", _json_piece(
                    "TURN_SYNC", sync_digest, depth=2, items=5, keys=8
                )))
        elif dialogue.get("continuation") or reference or str(dependency).lower() in {
            "continuation", "pending", "recall"
        }:
            live_digest = _build_live_dialogue_digest(dialogue)
            if live_digest:
                optional.append(("live_dialogue", _json_piece(
                    "LIVE_DIALOGUE", live_digest, depth=2, items=5, keys=8
                )))

        if semantic_frame:
            optional.append(("semantic_frame", _json_piece(
                "SEMANTIC_FRAME", semantic_frame, depth=2, items=6, keys=10
            )))

        if task_is_active or dialogue.get("continuation") or reference:
            strategy = dialogue.get("dialogue_strategy") if isinstance(dialogue.get("dialogue_strategy"), dict) else {}
            analysis = dialogue.get("continuation_content_analysis") if isinstance(dialogue.get("continuation_content_analysis"), dict) else {}
            strategy_digest = {
                "mode": strategy.get("mode") or analysis.get("mode"),
                "intent": strategy.get("intent") or analysis.get("intent"),
                "next": strategy.get("next_direction") or analysis.get("next_direction"),
                "avoid": (analysis.get("avoid_repeat_content") or analysis.get("covered_content") or [])[:2],
            }
            strategy_digest = {k: v for k, v in strategy_digest.items() if v not in (None, "", [], {})}
            if strategy_digest:
                optional.append(("continuation_plan", _json_piece(
                    "CONTINUATION_PLAN", strategy_digest, depth=2, items=4, keys=6
                )))

        if closure_policy.get("eligible_if_completed"):
            optional.append((
                "closure_policy",
                "CLOSURE: when this difficult work is genuinely achieved, naturally name the resolved topic and what was achieved together; do not use a generic task-solved phrase and do not force a closing on simple turns.",
            ))

        if visual_relation or structured_outputs_requested:
            visual_ref = _build_visual_reference_digest(payload, dialogue)
            if visual_ref:
                optional.append(("visual_reference", _json_piece(
                    "VISUAL_REFERENCE", visual_ref, depth=2, items=4, keys=8
                )))

        output_contract = {
            "mode": mode or "text",
            "requested": output_modes[:4],
            "authorized": render_authorized,
            "structured_required": structured_outputs_requested,
        }
        optional.append(("output_contract", _json_piece(
            "RENDER_CONTRACT", output_contract, depth=2, items=4, keys=6
        )))

        memory = payload.get("memory") if isinstance(payload.get("memory"), dict) else {}
        dialogue_memory = memory.get("dialogue_memory") if isinstance(memory.get("dialogue_memory"), dict) else {}
        if dialogue_memory and not task_is_active:
            active_turns = dialogue_memory.get("active_sequence_turns") or []
            recent = []
            for turn in list(active_turns)[-2:]:
                compact = _compact_qa_item(turn)
                if compact:
                    recent.append(compact)
            if recent:
                optional.append(("dialogue_window_memory", _json_piece(
                    "MEMORY_EVIDENCE", {"window_hours": dialogue_memory.get("window_hours", 12), "recent": recent},
                    depth=3, items=3, keys=4
                )))

    # Floating semantic target: leave more room for task/visual continuation while
    # preserving the hard 900-token ceiling.
    target_budget = _adaptive_target_budget(
        mode=effective_mode,
        task_active=task_is_active,
        continuation=bool(dialogue.get("continuation")),
    )
    user_text, pack_meta = _adaptive_pack(
        system_prompt,
        mandatory,
        optional,
        hard_budget=INPUT_TOKEN_BUDGET,
        target_budget=target_budget,
    )

    system_tokens = _estimate_input_tokens(system_prompt)
    estimated_total = system_tokens + _estimate_input_tokens(user_text)
    if estimated_total > INPUT_TOKEN_BUDGET:
        # Defensive invariant. Preserve the current semantic core and render
        # contract rather than falling back to a bare request/mode pair.
        compact_request = _semantic_excerpt(
            workspace_request or request_text,
            300,
        )
        system_prompt = (
            "April provider. Return one compact MachineResponse JSON object. "
            "Quantum Processor owns the current semantic task and output contract. "
            "Answer the current request directly and preserve requested structured output."
        )
        user_text = (
            "REQUEST: " + compact_request + "\n"
            "OUTPUT_MODE: " + _safe_text(mode or "text") + "\n"
            "REQUESTED: " + json.dumps(output_modes[:4], ensure_ascii=False, separators=(",", ":")) + "\n"
            "RENDER_CONTRACT: " + json.dumps({
                "authorized": render_authorized,
                "render_mode": workspace_contract.get("render_mode") if isinstance(workspace, dict) and isinstance(workspace.get("output_contract"), dict) else _safe_text(interpretation_control.get("render_mode") or "TEXT_ONLY"),
                "structured_required": structured_outputs_requested,
            }, ensure_ascii=False, separators=(",", ":"))
        )
        estimated_total = _estimate_input_tokens(system_prompt) + _estimate_input_tokens(user_text)

    provider_log({
        "input_token_budget": INPUT_TOKEN_BUDGET,
        "input_budget_target": target_budget,
        "estimated_input_tokens": estimated_total,
        "input_budget_enforced": True,
        "context_strategy": ADAPTIVE_PROVIDER_PACKER_VERSION,
        "compression_level": pack_meta.get("compression_level"),
        "compressed_context": pack_meta.get("compressed_context") or [],
        "dropped_context": pack_meta.get("dropped") or [],
        "history_sent_to_provider": False,
        "dialogue_memory_sent_to_provider": bool(
            dialogue.get("continuation")
            or dialogue.get("reference_to_previous")
            or str(dependency).lower() in {"pending", "continuation", "recall"}
            or task_is_active
        ),
        "interactive_task_state_sent_to_provider": bool(task_is_active),
        "current_request_truncation": False if workspace else len(request_text) > len(request_excerpt),
        "current_request_semantic_compression": bool(workspace and len(request_text) > len(request_excerpt)),
        "current_request_semantics_preserved": bool(workspace),
        "cognitive_workspace_version": _safe_text(workspace.get("version")),
        "cognitive_workspace_protected": list(workspace.get("protected_context") or [])[:12],
        "cognitive_workspace_excluded": [
            x.get("key") if isinstance(x, dict) else str(x)
            for x in list(workspace.get("excluded_context") or [])[:8]
        ],
        "cognitive_workspace_selected": [
            x.get("key") if isinstance(x, dict) else str(x)
            for x in list(workspace.get("required_context") or [])[:12]
            + list(workspace.get("optional_context") or [])[:12]
        ],
        "dialogue_system_prompt": bool(system_prompt == PROVIDER_DIALOGUE_SYSTEM_PROMPT),
        "visual_production_mode": mode,
        "canonical_packet_fingerprint": _provider_packet_fingerprint(user_text),
    })

    return [
        {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
        {"role": "user", "content": [{"type": "input_text", "text": user_text}]},
    ]


def _object_to_plain(value: Any, *, max_depth: int = 5, _depth: int = 0) -> Any:
    """Convert OpenAI SDK response objects into plain Python data safely.

    Recent Responses API object shapes can expose the same payload through
    ``output_text``, ``output`` objects, or SDK model instances. The provider
    must treat all of those as one transport representation.
    """
    if value is None or _depth > max_depth:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {
            str(k): _object_to_plain(v, max_depth=max_depth, _depth=_depth + 1)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [
            _object_to_plain(v, max_depth=max_depth, _depth=_depth + 1)
            for v in value
        ]

    # Pydantic/OpenAI SDK model instances.
    for method_name in ("model_dump", "to_dict", "dict"):
        method = getattr(value, method_name, None)
        if callable(method):
            try:
                dumped = method()
                return _object_to_plain(
                    dumped, max_depth=max_depth, _depth=_depth + 1
                )
            except Exception:
                pass

    # Last-resort iterable support for SDK collection wrappers.
    try:
        if not isinstance(value, (bytes, bytearray)):
            return [
                _object_to_plain(v, max_depth=max_depth, _depth=_depth + 1)
                for v in value
            ]
    except Exception:
        pass

    return None


def _collect_text_candidates(value: Any, *, max_depth: int = 7, _depth: int = 0) -> list[str]:
    """Collect actual output text while ignoring IDs/diagnostic metadata."""
    if value is None or _depth > max_depth:
        return []
    if isinstance(value, str):
        clean = normalize_response_text(value)
        return [clean] if clean else []
    if isinstance(value, dict):
        results: list[str] = []
        # Prefer semantic text-bearing fields and preserve their order.
        for key in ("output_text", "text", "value", "answer", "content", "response", "final_text", "message"):
            if key in value:
                results.extend(
                    _collect_text_candidates(
                        value.get(key), max_depth=max_depth, _depth=_depth + 1
                    )
                )
        # Then recurse into the remaining structure (bounded) to handle SDK
        # wrappers such as response.output[*].content[*].
        for key, child in value.items():
            if key in {"output_text", "text", "value", "answer", "content", "response", "final_text", "message"}:
                continue
            results.extend(
                _collect_text_candidates(
                    child, max_depth=max_depth, _depth=_depth + 1
                )
            )
        return results
    if isinstance(value, (list, tuple, set)):
        results: list[str] = []
        for child in value:
            results.extend(
                _collect_text_candidates(
                    child, max_depth=max_depth, _depth=_depth + 1
                )
            )
        return results
    return []


def _extract_openai_text(response: Any) -> str:
    """Extract the model's actual textual payload across Responses API shapes."""
    direct = getattr(response, "output_text", None)
    if isinstance(direct, str) and direct.strip():
        return normalize_response_text(direct)

    plain = _object_to_plain(response)
    candidates = _collect_text_candidates(plain)
    if candidates:
        # The first candidate may be a duplicated wrapper field. Prefer the
        # longest meaningful candidate when multiple SDK paths expose it.
        candidates = [x for x in candidates if normalize_response_text(x)]
        if candidates:
            return max(candidates, key=len).strip()

    # Some SDK versions expose ``output`` as a custom iterable without a useful
    # model_dump implementation. Keep the direct walk as a compatibility path.
    pieces: list[str] = []
    output = getattr(response, "output", None)
    try:
        for item in output or []:
            content = getattr(item, "content", None)
            try:
                for part in content or []:
                    value = getattr(part, "text", None)
                    if isinstance(value, str) and value.strip():
                        pieces.append(value.strip())
                    elif isinstance(part, dict):
                        value = part.get("text") or part.get("value")
                        if isinstance(value, str) and value.strip():
                            pieces.append(value.strip())
            except Exception:
                pass
    except Exception:
        pass
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
    """Extract a human answer from both flat and nested model envelopes."""
    if isinstance(value, dict):
        # Canonical provider payloads can occasionally arrive wrapped as
        # {"machine_response": {...}}, {"result": {...}} or similar.
        for key in (
            "answer", "content", "response", "summary", "final_text", "text",
            "machine_response", "result", "data", "output",
        ):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return _unwrap_model_answer(candidate)
            if isinstance(candidate, dict):
                nested = _unwrap_model_answer(candidate)
                if nested:
                    return nested
        return ""

    if not isinstance(value, str):
        plain = _object_to_plain(value)
        if isinstance(plain, dict):
            return _unwrap_model_answer(plain)
        return normalize_response_text(value)

    text = normalize_response_text(value)
    if not text or not text.lstrip().startswith(("{", "[")):
        return text
    try:
        obj = json.loads(text)
    except Exception:
        return text
    if isinstance(obj, dict):
        for key in (
            "answer", "content", "response", "summary", "final_text", "text",
            "machine_response", "result", "data", "output",
        ):
            candidate = obj.get(key)
            if isinstance(candidate, str) and candidate.strip():
                nested = _unwrap_model_answer(candidate)
                if nested and nested != text:
                    return nested
            elif isinstance(candidate, dict):
                nested = _unwrap_model_answer(candidate)
                if nested:
                    return nested
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



def _coerce_human_answer(value: Any) -> str:
    """Coerce provider answer values without losing scalar/nested values."""
    if value is None:
        return ""
    if isinstance(value, str):
        text = normalize_response_text(value)
        if not text:
            return ""
        # A nested JSON envelope can arrive as a string.
        if text.lstrip().startswith(("{", "[")):
            try:
                obj = json.loads(text)
            except Exception:
                return text
            if obj != text:
                nested = _coerce_human_answer(obj)
                return nested or text
        return text
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        for key in (
            "answer", "content", "response", "final_text", "text", "value",
            "result", "data", "output", "message", "summary",
        ):
            if key in value:
                nested = _coerce_human_answer(value.get(key))
                if nested:
                    return nested
        return ""
    plain = _object_to_plain(value)
    if plain is not None and plain is not value:
        return _coerce_human_answer(plain)
    return normalize_response_text(value)


def _extract_current_request_for_recovery(source_request: Any) -> str:
    payload = source_request if isinstance(source_request, dict) else machine_request_to_dict(source_request)
    intent = payload.get("intent") if isinstance(payload.get("intent"), dict) else {}
    conversation = payload.get("conversation") if isinstance(payload.get("conversation"), dict) else {}
    plan = payload.get("provider_context_plan") if isinstance(payload.get("provider_context_plan"), dict) else {}
    return normalize_response_text(
        plan.get("current_user_request")
        or intent.get("normalized_text")
        or conversation.get("current_user_request")
        or payload.get("canonical_prompt_text")
        or ""
    )


def _safe_numeric_expression(expr: str) -> Optional[str]:
    """Evaluate only a closed arithmetic expression with numeric literals."""
    normalized = expr.replace("×", "*").replace("÷", "/").replace("−", "-")
    try:
        tree = ast.parse(normalized, mode="eval")
    except Exception:
        return None

    ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        if isinstance(node, ast.UnaryOp) and type(node.op) in ops:
            return ops[type(node.op)](ev(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in ops:
            left = ev(node.left)
            right = ev(node.right)
            # Protect the process from pathological powers/huge integers.
            if isinstance(right, (int, float)) and abs(right) > 1000 and isinstance(node.op, ast.Pow):
                raise ValueError("power too large")
            result = ops[type(node.op)](left, right)
            if isinstance(result, (int, float)) and abs(result) > 10**100:
                raise ValueError("result too large")
            return result
        raise ValueError("unsupported expression")

    try:
        result = ev(tree)
    except Exception:
        return None
    if isinstance(result, float) and result.is_integer():
        return str(int(result))
    return str(result)


def _recover_answer_from_source_request(source_request: Any) -> str:
    """Last-resort transport recovery, without a second model call."""
    request = _extract_current_request_for_recovery(source_request)
    if not request:
        return ""

    # Recover a closed arithmetic expression embedded in a natural-language request.
    candidates = re.findall(
        r"(?<![\w.])(?:\d+(?:\.\d+)?(?:\s*[+\-−×÷*/%]\s*\d+(?:\.\d+)?)+(?:\s*)|\(\s*[0-9+\-*/%().\s×÷−]+\))(?![\w.])",
        request,
    )
    for candidate in candidates:
        answer = _safe_numeric_expression(candidate.strip())
        if answer is not None:
            return answer

    # A completely empty provider object must never produce an empty UI bubble.
    return f"Не удалось сформировать ответ на запрос: {request}"


# ---------------------------------------------------------------------------
# Canonical visual-output promotion
# ---------------------------------------------------------------------------

_TOP_LEVEL_VISUAL_TYPES = ("image", "gallery", "diagram", "graph", "table", "formula", "code", "link")


def _image_source_value(value: Any) -> str:
    """Return a concrete image source, never a natural-language description."""
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return ""
        if value.startswith(("data:image/", "http://", "https://", "blob:", "/")):
            return value
        return ""
    if not isinstance(value, dict):
        return ""
    for key in (
        "src",
        "url",
        "image_url",
        "image_data_uri",
        "data_uri",
        "image_base64",
        "base64",
        "image",
    ):
        candidate = value.get(key)
        if isinstance(candidate, str):
            candidate = candidate.strip()
            if candidate.startswith(("data:image/", "http://", "https://", "blob:", "/")):
                if key in {"image_base64", "base64"}:
                    mime = _safe_text(value.get("mime_type") or "image/png") or "image/png"
                    return f"data:{mime};base64,{candidate}"
                return candidate
    return ""


def _image_prompt_from_provider_payload(value: Any) -> str:
    """Extract only semantic image instructions, never render payloads."""
    if isinstance(value, str):
        text = value.strip()
        if not text or _image_source_value(text):
            return ""
        # Provider may return ready SVG/XML/base64 content. That is a render
        # artifact, not a prompt for C_APRIL_IMAGES_GENERATOR.
        if re.search(r"<\/?(?:svg|path|rect|circle|ellipse|polygon|g)\b|data:image/|^iVBOR", text, flags=re.IGNORECASE):
            return ""
        return text
    if not isinstance(value, dict):
        return ""

    # Explicit semantic fields have priority. `content`/`text` are deliberately
    # excluded here because provider image payloads commonly store SVG there.
    for key in (
        "prompt", "description", "visual_prompt", "image_prompt",
        "caption", "alt", "title", "subject", "scene", "request",
    ):
        candidate = value.get(key)
        if isinstance(candidate, str):
            text = candidate.strip()
            if text and not re.search(
                r"<\/?(?:svg|path|rect|circle|ellipse|polygon|g)\b|data:image/|^iVBOR",
                text,
                flags=re.IGNORECASE,
            ):
                return text

    for key in ("image", "visual", "visual_context", "spec", "data"):
        nested = value.get(key)
        if nested is value:
            continue
        candidate = _image_prompt_from_provider_payload(nested)
        if candidate:
            return candidate
    return ""




def _image_render_profile_from_context(source_payload: Any, visual_context: Any, semantic_plan: str = "") -> dict[str, str]:
    """Select a deterministic April render profile only inside the image route.

    The profile changes *rendering discipline*, not scene content.  Interpretation
    remains authoritative for intent; OpenAI remains authoritative for the same-turn
    visual plan.  No profile is allowed to add subjects, props, locations or story.
    """
    payload = source_payload if isinstance(source_payload, dict) else {}
    constraints = payload.get("constraints") if isinstance(payload.get("constraints"), dict) else {}
    metadata = constraints.get("metadata") if isinstance(constraints.get("metadata"), dict) else {}
    plan = constraints.get("representation_plan") if isinstance(constraints.get("representation_plan"), dict) else {}
    intent = payload.get("intent") if isinstance(payload.get("intent"), dict) else {}
    frame = payload.get("semantic_frame") if isinstance(payload.get("semantic_frame"), dict) else {}

    explicit = (
        metadata.get("render_profile")
        or metadata.get("image_render_profile")
        or metadata.get("style_profile")
        or metadata.get("image_style")
        or plan.get("render_profile")
        or plan.get("style_profile")
        or intent.get("render_profile")
        or intent.get("style_profile")
    )
    explicit_text = re.sub(r"[^a-z0-9_\- ]+", " ", _safe_text(explicit).strip().lower())
    aliases = {
        "wildlife": "naturalistic_wildlife",
        "natural_wildlife": "naturalistic_wildlife",
        "scientific_wildlife": "scientific_natural_history",
        "natural_history": "scientific_natural_history",
        "botanical": "botanical_documentation",
        "marine": "marine_landscape",
        "seascape": "marine_landscape",
        "landscape": "natural_landscape",
        "cinematic": "cinematic_landscape",
        "portrait": "portrait_realistic",
        "product": "product_photography",
        "architecture": "architectural_visualization",
        "math": "mathematical_diagram",
        "mathematics": "mathematical_diagram",
        "geometry": "technical_geometry",
        "technical": "technical_diagram",
        "scientific": "scientific_diagram",
        "watercolor": "watercolor_illustration",
        "watercolour": "watercolor_illustration",
        "oil": "oil_painting",
        "sketch": "line_art_sketch",
        "line_art": "line_art_sketch",
        "isometric": "isometric_illustration",
        "3d": "three_d_render",
        "three_d": "three_d_render",
        "cartoon": "cartoon_illustration",
        "children": "children_illustration",
        "documentary": "documentary_visual",
        "artistic": "artistic_illustration",
    }
    if explicit_text:
        for key, value in aliases.items():
            if key in explicit_text:
                return {"name": value, "source": "explicit"}
        allowed = {
            "neutral_realistic", "naturalistic_wildlife", "scientific_natural_history",
            "botanical_documentation", "marine_landscape", "natural_landscape",
            "cinematic_landscape", "portrait_realistic", "product_photography",
            "architectural_visualization", "mathematical_diagram", "technical_geometry",
            "technical_diagram", "scientific_diagram", "watercolor_illustration",
            "oil_painting", "line_art_sketch", "isometric_illustration", "three_d_render",
            "cartoon_illustration", "children_illustration", "documentary_visual",
            "artistic_illustration",
        }
        if explicit_text in allowed:
            return {"name": explicit_text, "source": "explicit"}

    pieces = [
        _safe_text(intent.get("domain")),
        _safe_text(intent.get("subject_domain")),
        _safe_text(intent.get("topic")),
        _safe_text(intent.get("object")),
        _safe_text(intent.get("semantic_request")),
        _safe_text(frame.get("topic")),
        _safe_text(frame.get("entity")),
        _safe_text(semantic_plan),
        json.dumps(visual_context or {}, ensure_ascii=False, default=str),
    ]
    text = " ".join(x for x in pieces if x).lower()

    # Explicit user-style words take precedence over domain defaults.
    style_rules = (
        (r"акварел|watercolor|watercolour", "watercolor_illustration"),
        (r"маслян|oil painting|oil-paint", "oil_painting"),
        (r"скетч|эскиз|line art|линейн", "line_art_sketch"),
        (r"изометр|isometric", "isometric_illustration"),
        (r"3d|3-d|рендеринг|three\s*d", "three_d_render"),
        (r"мультфильм|мультяш|cartoon|анимац", "cartoon_illustration"),
        (r"детск.*книг|children.*illustration", "children_illustration"),
        (r"документаль|documentary", "documentary_visual"),
        (r"кинематограф|cinematic|кадр фильма", "cinematic_landscape"),
    )
    for pattern, profile in style_rules:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return {"name": profile, "source": "same_turn_style"}

    # Domain-specific professional profiles. These are rendering disciplines,
    # not new scene content.
    if re.search(r"математ|formula|формул|график функции|equation|алгебр|тригоном|calculus", text, flags=re.IGNORECASE):
        return {"name": "mathematical_diagram", "source": "domain"}
    if re.search(r"геометр|geometry|геометрическ|угол|треугольник|круг|квадрат|размер|dimension|метрическ", text, flags=re.IGNORECASE):
        return {"name": "technical_geometry", "source": "domain"}
    if re.search(r"техническ.*схем|схем|диаграм|schematic|technical diagram|blueprint|чертеж", text, flags=re.IGNORECASE):
        return {"name": "technical_diagram", "source": "domain"}
    if re.search(r"ботан|растен|цветок|цветы|тюльпан|дерев|лист|флора|botanical|plant|flower|flora", text, flags=re.IGNORECASE):
        return {"name": "botanical_documentation", "source": "domain"}
    if re.search(r"биолог|вид животн|зоолог|анатом|species|biology|zoolog|natural history", text, flags=re.IGNORECASE):
        return {"name": "scientific_natural_history", "source": "domain"}
    if re.search(r"животн|заяц|черепах|волк|лиса|кот|кошка|собак|лошад|птиц|рыб|ежик|wildlife|animal|bird|fish", text, flags=re.IGNORECASE):
        return {"name": "naturalistic_wildlife", "source": "domain"}
    if re.search(r"море|океан|пляж|побереж|морск|sea|ocean|beach|coast|marine", text, flags=re.IGNORECASE):
        return {"name": "marine_landscape", "source": "domain"}
    if re.search(r"пейзаж|ландшафт|горы|лес|поле|landscape|mountain|forest", text, flags=re.IGNORECASE):
        return {"name": "natural_landscape", "source": "domain"}
    if re.search(r"портрет|лицо человека|человек.*крупн|portrait|headshot", text, flags=re.IGNORECASE):
        return {"name": "portrait_realistic", "source": "domain"}
    if re.search(r"товар|продукт|каталог|product photography|e-commerce|предмет.*на белом", text, flags=re.IGNORECASE):
        return {"name": "product_photography", "source": "domain"}
    if re.search(r"архитект|здание|дом|интерьер|architecture|building|interior", text, flags=re.IGNORECASE):
        return {"name": "architectural_visualization", "source": "domain"}
    if re.search(r"иллюстрац|рисунок|illustration|art", text, flags=re.IGNORECASE):
        return {"name": "artistic_illustration", "source": "domain"}

    return {"name": "neutral_realistic", "source": "default"}


def _image_structured_plan_raw(value: Any) -> Any:
    """Preserve the same-turn OpenAI visual plan without normalizing or rewriting it."""
    if isinstance(value, (dict, list, str)):
        return copy.deepcopy(value)
    return None

def _svg_attr_number(value: Any, default: float = 0.0) -> float:
    text = _safe_text(value).strip()
    if not text:
        return float(default)
    match = re.match(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text)
    if not match:
        return float(default)
    try:
        return float(match.group(0))
    except (TypeError, ValueError, OverflowError):
        return float(default)


def _parse_svg_visual_context(svg_text: Any) -> dict[str, Any] | None:
    """Convert a same-turn Provider SVG into explicit geometry/color constraints."""
    raw = _safe_text(svg_text).strip()
    if not raw or "<svg" not in raw.lower():
        return None
    try:
        root = ET.fromstring(raw)
    except (ET.ParseError, ValueError):
        return None

    def local_name(tag: Any) -> str:
        return _safe_text(tag).split("}", 1)[-1].lower()

    width = _svg_attr_number(root.attrib.get("width"), 512)
    height = _svg_attr_number(root.attrib.get("height"), 512)
    view_box_text = _safe_text(root.attrib.get("viewBox") or root.attrib.get("viewbox")).strip()
    vb: list[float] = []
    if view_box_text:
        parts = re.split(r"[,\s]+", view_box_text)
        if len(parts) == 4:
            try:
                vb = [float(x) for x in parts]
            except (TypeError, ValueError, OverflowError):
                vb = []
    if len(vb) == 4:
        ox, oy, cw, ch = vb
        width = width if width > 0 else cw
        height = height if height > 0 else ch
    else:
        ox, oy, cw, ch = 0.0, 0.0, max(width, 1.0), max(height, 1.0)

    def nx(x: float) -> float:
        return round(max(0.0, min(1.0, (x - ox) / max(cw, 1.0))), 4)
    def ny(y: float) -> float:
        return round(max(0.0, min(1.0, (y - oy) / max(ch, 1.0))), 4)
    def nw(v: float) -> float:
        return round(max(0.0, min(1.0, v / max(cw, 1.0))), 4)
    def nh(v: float) -> float:
        return round(max(0.0, min(1.0, v / max(ch, 1.0))), 4)
    def color(v: Any) -> str:
        t = _safe_text(v).strip()
        return t[:24] if t and t.lower() not in {"none", "transparent"} else ""

    background_color = ""
    layers: list[dict[str, Any]] = []

    for el in root.iter():
        tag = local_name(el.tag)
        attrs = el.attrib

        if tag == "rect":
            x = _svg_attr_number(attrs.get("x"), 0)
            y = _svg_attr_number(attrs.get("y"), 0)
            w = _svg_attr_number(attrs.get("width"), cw)
            h = _svg_attr_number(attrs.get("height"), ch)
            fill = color(attrs.get("fill"))
            if not fill and attrs.get("style"):
                m = re.search(r"(?:^|;)\s*fill\s*:\s*([^;]+)", _safe_text(attrs.get("style")))
                fill = color(m.group(1) if m else "")
            if x <= ox + 1e-6 and y <= oy + 1e-6 and w >= cw - 1e-6 and h >= ch - 1e-6 and fill and not background_color:
                background_color = fill
                continue
            item = {"kind": "rect", "box": [nx(x), ny(y), nx(x+w), ny(y+h)]}
            if fill:
                item["fill"] = fill
            rx = _svg_attr_number(attrs.get("rx"), 0)
            if rx > 0:
                item["radius"] = nw(rx)
            layers.append(item)

        elif tag in {"circle", "ellipse"}:
            cx = _svg_attr_number(attrs.get("cx"), 0)
            cy = _svg_attr_number(attrs.get("cy"), 0)
            item = {"kind": tag, "center": [nx(cx), ny(cy)]}
            if tag == "circle":
                r = _svg_attr_number(attrs.get("r"), 0)
                item["radius"] = round(min(nw(r), nh(r)), 4)
            else:
                item["radius_x"] = nw(_svg_attr_number(attrs.get("rx"), 0))
                item["radius_y"] = nh(_svg_attr_number(attrs.get("ry"), 0))
            fill = color(attrs.get("fill"))
            if fill:
                item["fill"] = fill
            stroke = color(attrs.get("stroke"))
            if stroke:
                item["stroke"] = stroke
            layers.append(item)

        elif tag in {"polygon", "polyline"}:
            raw_points = _safe_text(attrs.get("points"))
            nums = re.findall(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", raw_points)
            points = []
            for i in range(0, len(nums)-1, 2):
                try:
                    points.append([nx(float(nums[i])), ny(float(nums[i+1]))])
                except (TypeError, ValueError):
                    pass
            if points:
                item = {"kind": "polygon", "points": points[:64]}
                fill = color(attrs.get("fill"))
                if fill:
                    item["fill"] = fill
                layers.append(item)

        elif tag == "line":
            item = {
                "kind": "line",
                "points": [
                    [nx(_svg_attr_number(attrs.get("x1"), 0)), ny(_svg_attr_number(attrs.get("y1"), 0))],
                    [nx(_svg_attr_number(attrs.get("x2"), 0)), ny(_svg_attr_number(attrs.get("y2"), 0))],
                ],
            }
            stroke = color(attrs.get("stroke"))
            if stroke:
                item["stroke"] = stroke
            layers.append(item)

        elif tag == "text":
            value = "".join(el.itertext()).strip()
            if value:
                layers.append({
                    "kind": "text",
                    "text": value[:240],
                    "position": [nx(_svg_attr_number(attrs.get("x"), 0)), ny(_svg_attr_number(attrs.get("y"), 0))],
                })

    if not background_color and not layers:
        return None

    return {
        "source": "OPENAI_STRUCTURED_VISUAL_PLAN",
        "authoritative": True,
        "complements_prompt": True,
        "canvas": {
            "width": int(round(width)),
            "height": int(round(height)),
            "view_box": [round(x, 4) for x in vb] if vb else [0, 0, int(round(width)), int(round(height))],
        },
        "background": {"color": background_color} if background_color else {},
        "layers": layers[:32],
    }


def _visual_layer_key(layer: Any) -> str:
    """Stable structural identity for one OpenAI visual layer.

    Layer identity is semantic/structural rather than textual.  This prevents
    the same object from being duplicated when the same-turn OpenAI plan is
    represented both as explicit visual_context and as parsed SVG/XML.
    """
    if not isinstance(layer, dict):
        return json.dumps(layer, ensure_ascii=False, sort_keys=True, default=str)
    return json.dumps(layer, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _dedupe_visual_layers(layers: Any, *, limit: int = 32) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    if not isinstance(layers, list):
        return unique
    for layer in layers:
        if not isinstance(layer, dict):
            continue
        key = _visual_layer_key(layer)
        if key in seen:
            continue
        seen.add(key)
        unique.append(dict(layer))
        if len(unique) >= max(1, int(limit)):
            break
    return unique


def _merge_visual_context(base: Any, supplement: Any) -> dict[str, Any]:
    merged = dict(base) if isinstance(base, dict) else {}
    if not isinstance(supplement, dict):
        if isinstance(merged.get("layers"), list):
            merged["layers"] = _dedupe_visual_layers(merged.get("layers"), limit=32)
            if merged["layers"]:
                merged["object_count"] = len(merged["layers"])
        return merged
    for key, value in supplement.items():
        if key == "layers" and isinstance(value, list):
            current = list(merged.get("layers") or []) if isinstance(merged.get("layers"), list) else []
            current.extend(value)
            merged["layers"] = _dedupe_visual_layers(current, limit=32)
            if merged["layers"]:
                merged["object_count"] = len(merged["layers"])
        elif key == "background" and isinstance(value, dict):
            bg = dict(merged.get("background") or {}) if isinstance(merged.get("background"), dict) else {}
            for bk, bv in value.items():
                if bv not in (None, ""):
                    bg.setdefault(bk, bv)
            merged["background"] = bg
        elif key == "object_count" and merged.get("layers"):
            merged["object_count"] = len(_dedupe_visual_layers(merged.get("layers"), limit=32))
        elif value not in (None, "", {}, []):
            merged.setdefault(key, value)
    if isinstance(merged.get("layers"), list):
        merged["layers"] = _dedupe_visual_layers(merged.get("layers"), limit=32)
        if merged["layers"]:
            merged["object_count"] = len(merged["layers"])
    return merged


def _semantic_prompt_from_visual_context(
    visual_context: Any,
    *,
    fallback_prompt: str = "",
) -> str:
    """Compile OpenAI visual meaning without discarding structured geometry.

    Description, background and explicit layers are complementary operands.  A
    short description such as ``Черепаха`` must never cause the structured SVG
    geometry to be dropped.  Duplicate semantic fragments are removed by exact
    normalized identity; ordering remains stable.
    """
    if not isinstance(visual_context, dict):
        return ""

    fallback_norm = re.sub(r"\s+", " ", _safe_text(fallback_prompt)).strip().casefold()

    def clean(value: Any, limit: int = 8000) -> str:
        text = re.sub(r"\s+", " ", _safe_text(value)).strip()
        return text[:limit] if text else ""

    pieces: list[str] = []
    seen: set[str] = set()

    def add_piece(value: Any) -> None:
        text = clean(value)
        if not text:
            return
        normalized = text.casefold()
        if normalized == fallback_norm or normalized in seen:
            return
        seen.add(normalized)
        pieces.append(text)

    description = (
        visual_context.get("description")
        or visual_context.get("visual_description")
        or visual_context.get("visual_prompt")
        or visual_context.get("image_prompt")
        or visual_context.get("scene")
        or visual_context.get("subject")
        or visual_context.get("entity")
    )
    add_piece(description)

    bg = visual_context.get("background")
    if isinstance(bg, dict):
        color = clean(bg.get("color") or bg.get("fill"), 40)
        if color:
            add_piece(f"solid {color} background")

    layers = _dedupe_visual_layers(visual_context.get("layers"), limit=32)
    for layer in layers:
        kind = clean(layer.get("kind") or layer.get("shape") or "object", 80).lower()
        if kind == "rect" and str(layer.get("shape") or "").lower() == "square":
            kind = "square"
        fill = clean(layer.get("fill") or layer.get("color"), 40)
        color_word = f"{fill} " if fill else ""
        details: list[str] = []
        center = layer.get("center")
        if isinstance(center, (list, tuple)) and len(center) >= 2:
            try:
                details.append(f"center ({float(center[0]):.3f}, {float(center[1]):.3f})")
            except (TypeError, ValueError):
                pass
        box = layer.get("box")
        if isinstance(box, (list, tuple)) and len(box) >= 4:
            try:
                details.append(
                    "box " + ",".join(f"{float(x):.3f}" for x in box[:4])
                )
            except (TypeError, ValueError):
                pass
        radius = layer.get("radius")
        if radius not in (None, ""):
            try:
                details.append(f"radius {float(radius):.3f}")
            except (TypeError, ValueError):
                pass
        text_value = clean(layer.get("text") or "", 240)
        if text_value:
            details.append(f"text {text_value!r}")
        item = f"{color_word}{kind}".strip()
        if details:
            item += " (" + ", ".join(details) + ")"
        add_piece(item)

    if pieces:
        return "OpenAI visual plan: " + "; ".join(pieces)
    return ""


def _visual_context_from_structured_image(value: Any) -> dict[str, Any]:
    """Project same-turn OpenAI image objects into rendering constraints.

    The exact current user request remains the immutable scene anchor. This helper
    only converts OpenAI's structured visual plan into complementary geometry/color
    evidence for C_APRIL_IMAGES_GENERATOR; it never replaces the request.
    """
    if not isinstance(value, dict):
        return {}

    objects = value.get("objects")
    background = value.get("background")
    if not isinstance(objects, list):
        objects = []

    def clean_color(raw: Any) -> str:
        text = _safe_text(raw).strip()
        return text[:24] if text else ""

    def normalized_position(obj: dict[str, Any]) -> list[float] | None:
        for key in ("center", "position", "location"):
            pos = obj.get(key)
            if isinstance(pos, (list, tuple)) and len(pos) >= 2:
                try:
                    x, y = float(pos[0]), float(pos[1])
                    if abs(x) > 1 or abs(y) > 1:
                        x /= 512.0
                        y /= 512.0
                    return [round(max(0.0, min(1.0, x)), 4), round(max(0.0, min(1.0, y)), 4)]
                except (TypeError, ValueError, OverflowError):
                    pass
        return None

    def normalized_box(obj: dict[str, Any]) -> list[float] | None:
        box = obj.get("box") or obj.get("bbox") or obj.get("bounding_box")
        if isinstance(box, (list, tuple)) and len(box) >= 4:
            try:
                vals = [float(x) for x in box[:4]]
                if any(abs(v) > 1 for v in vals):
                    vals = [v / 512.0 for v in vals]
                return [round(max(0.0, min(1.0, v)), 4) for v in vals]
            except (TypeError, ValueError, OverflowError):
                pass
        return None

    # OpenAI may return a semantic-only image plan such as:
    # {"description": "...", "alt_text": "..."} without explicit geometry.
    # Preserve that meaning so it can cross the Provider -> generator boundary.
    def clean_semantic(raw: Any, limit: int = 8000) -> str:
        text = _safe_text(raw).strip()
        if not text:
            return ""
        return re.sub(r"\s+", " ", text)[:limit]

    semantic_description = clean_semantic(
        value.get("description") or value.get("visual_description")
        or value.get("visual_prompt") or value.get("prompt")
        or value.get("scene") or value.get("subject") or value.get("entity")
    )
    semantic_alt = clean_semantic(value.get("alt_text") or value.get("alt"), 2000)
    semantic_type = clean_semantic(value.get("type") or value.get("style"), 120)

    layers: list[dict[str, Any]] = []
    for obj in objects[:24]:
        if not isinstance(obj, dict):
            continue
        shape = _safe_text(obj.get("shape") or obj.get("kind") or obj.get("type") or "object").strip().lower()
        color = clean_color(obj.get("color") or obj.get("fill"))

        if shape in {"square", "rectangle", "rect"}:
            layer: dict[str, Any] = {
                "kind": "rect",
                "shape": "square" if shape == "square" else "rectangle",
            }
        elif shape in {"circle", "ellipse", "polygon", "line"}:
            layer = {"kind": shape}
        else:
            layer = {"kind": "object", "shape": shape}

        if color:
            layer["fill"] = color
        pos = normalized_position(obj)
        if pos:
            layer["center"] = pos
        box = normalized_box(obj)
        if box:
            layer["box"] = box

        for key in ("width", "height", "size", "rotation", "radius"):
            raw = obj.get(key)
            if raw in (None, ""):
                continue
            if isinstance(raw, (int, float)):
                value_num = float(raw)
                if key in {"width", "height", "size", "radius"} and abs(value_num) > 1:
                    value_num /= 512.0
                layer[key] = round(value_num, 4)
            else:
                layer[key] = raw

        text_value = _safe_text(obj.get("text") or obj.get("label") or "").strip()
        if text_value:
            layer["text"] = text_value[:240]
        layers.append(layer)

    result: dict[str, Any] = {
        "source": "OPENAI_STRUCTURED_VISUAL_PLAN",
        "authoritative": True,
        "complements_prompt": True,
        "object_count": len(layers),
        "layers": layers[:24],
    }
    if semantic_description:
        result["description"] = semantic_description
    if semantic_alt:
        result["alt_text"] = semantic_alt
    if semantic_type:
        result["plan_type"] = semantic_type
    if isinstance(background, dict):
        bg_color = clean_color(background.get("color") or background.get("fill"))
        if bg_color:
            result["background"] = {"color": bg_color}
    return {k: v for k, v in result.items() if v not in (None, "", [], {})}


def _structured_visual_context_from_provider_value(value: Any) -> dict[str, Any]:
    """Find same-turn structured visual evidence without treating it as a prompt replacement."""
    if not isinstance(value, dict):
        return {}
    existing = value.get("visual_context")
    derived = _visual_context_from_structured_image(value)
    if isinstance(existing, dict) and existing:
        return _merge_visual_context(existing, derived) if derived else dict(existing)
    if derived:
        return derived
    for key in ("image", "visual", "spec", "data"):
        nested = value.get(key)
        if isinstance(nested, dict):
            nested_context = _structured_visual_context_from_provider_value(nested)
            if nested_context:
                return nested_context
    return {}


def _build_image_generation_spec_from_provider(
    value: Any,
    *,
    fallback_prompt: str = "",
) -> dict[str, Any] | None:
    """Build the image handoff while preserving the original OpenAI plan.

    The current user request is stored only as ``request_anchor``.  The actual
    generation meaning comes from OpenAI's same-turn visual plan.  The original
    plan is retained verbatim in ``openai_structured_visual_plan_raw`` so the
    generator can parse it without Provider rewriting it.
    """
    raw_plan = _image_structured_plan_raw(value)
    svg_context = None
    if isinstance(value, str):
        svg_context = _parse_svg_visual_context(value)
    elif isinstance(value, dict) and _safe_text(value.get("format")).strip().lower() in {"svg", "xml"}:
        svg_context = _parse_svg_visual_context(value.get("content") or value.get("data"))

    structured_context = _structured_visual_context_from_provider_value(value)
    combined_structured_context = _merge_visual_context(structured_context, svg_context)

    # Keep the semantic text operand separate from structured geometry.  The
    # generator will consume visual_context exactly once, so putting derived
    # layers into this field as well would duplicate the plan downstream.
    direct_semantic = _image_prompt_from_provider_payload(value)
    direct_norm = re.sub(r"\s+", " ", direct_semantic).strip().casefold()
    fallback_norm = re.sub(r"\s+", " ", fallback_prompt).strip().casefold()
    semantic_plan_prompt = direct_semantic if direct_semantic and direct_norm != fallback_norm else ""
    if not semantic_plan_prompt and not direct_semantic:
        # Structured objects/SVG without a prose description are intentionally
        # represented through visual_context; no second textual paraphrase is
        # manufactured here.
        semantic_plan_prompt = ""

    if isinstance(value, dict) and _safe_text(value.get("schema")).strip() == "april_image_spec_v1":
        candidate = dict(value)
        existing_raw = candidate.get("openai_structured_visual_plan_raw")
        if existing_raw is not None:
            raw_plan = copy.deepcopy(existing_raw)
        existing_context = candidate.get("visual_context") if isinstance(candidate.get("visual_context"), dict) else {}
        candidate["visual_context"] = _merge_visual_context(existing_context, combined_structured_context)
        if semantic_plan_prompt:
            candidate["prompt"] = semantic_plan_prompt
        elif not _safe_text(candidate.get("prompt")).strip():
            candidate["prompt"] = fallback_prompt.strip()
        if raw_plan is not None:
            candidate["openai_structured_visual_plan_raw"] = raw_plan
        candidate["openai_structured_visual_plan_semantic"] = semantic_plan_prompt or _safe_text(candidate.get("prompt"))
        return candidate if candidate.get("prompt") else None

    if not semantic_plan_prompt and not direct_semantic and not raw_plan:
        return None

    width, height = 512, 512
    style = "illustration"
    quality = "standard"
    negative: list[str] = []
    seed = None
    if isinstance(value, dict):
        is_render_artifact = _safe_text(value.get("format")).lower() in {"svg", "xml", "png", "jpeg", "jpg", "webp"}
        if not is_render_artifact:
            try:
                width = int(value.get("width") or width)
                height = int(value.get("height") or height)
            except (TypeError, ValueError, OverflowError):
                width, height = 512, 512
        style = _safe_text(value.get("style") or "illustration") or "illustration"
        quality = _safe_text(value.get("quality") or "standard") or "standard"
        negative = [str(x) for x in (value.get("negative") or []) if str(x).strip()] if isinstance(value.get("negative"), list) else []
        seed = value.get("seed")

    explicit_layers = (
        list(value.get("layers") or [])
        if isinstance(value, dict) and isinstance(value.get("layers"), list)
        else []
    )
    visual_context = _merge_visual_context(
        value.get("visual_context") if isinstance(value, dict) and isinstance(value.get("visual_context"), dict) else {},
        combined_structured_context,
    )

    return {
        "schema": "april_image_spec_v1",
        "prompt": semantic_plan_prompt or fallback_prompt.strip(),
        "width": max(256, min(width, 1536)),
        "height": max(256, min(height, 1536)),
        "style": style,
        "quality": quality,
        "background": dict(value.get("background") or {}) if isinstance(value, dict) and isinstance(value.get("background"), dict) else {},
        "layers": explicit_layers,
        "visual_context": visual_context,
        "openai_structured_visual_plan_raw": raw_plan,
        "openai_structured_visual_plan_semantic": semantic_plan_prompt or fallback_prompt.strip(),
        "negative": negative,
        "seed": seed,
    }

def _top_level_visual_block(kind: str, value: Any) -> dict[str, Any] | None:
    """Promote one concrete provider visual into a canonical semantic block."""
    kind = _safe_text(kind).lower()
    if kind not in _TOP_LEVEL_VISUAL_TYPES:
        return None

    if kind in {"image", "gallery"}:
        # A description/prompt is an instruction for Executor materialization,
        # not a renderable block.  Only a concrete source enters SceneContract.
        items = value if kind == "gallery" and isinstance(value, list) else (
            value.get("images") if isinstance(value, dict) and isinstance(value.get("images"), list) else None
        )
        if isinstance(items, list):
            concrete = []
            for item in items[:8]:
                src = _image_source_value(item)
                if not src:
                    continue
                if isinstance(item, dict):
                    normalized = dict(item)
                else:
                    normalized = {"src": src}
                normalized.setdefault("src", src)
                normalized.setdefault("url", src)
                normalized.setdefault("image", src)
                concrete.append(normalized)
            if concrete:
                payload = {"images": concrete}
                if isinstance(value, dict):
                    for key in ("title", "caption", "prompt", "description", "mime_type", "width", "height"):
                        if key in value and key not in payload:
                            payload[key] = value[key]
                return {
                    "type": "gallery" if kind == "gallery" or len(concrete) > 1 else "image",
                    "artifact_type": "gallery" if kind == "gallery" or len(concrete) > 1 else "image",
                    "renderer": "GalleryBlock",
                    "viewer": "GalleryBlock",
                    "payload": payload,
                    "scene_contract": True,
                    "human_visible": True,
                }

        src = _image_source_value(value)
        if src:
            payload = {"src": src, "url": src, "image": src, "images": [{"src": src, "url": src, "image": src}]}
            if isinstance(value, dict):
                for key in ("prompt", "description", "caption", "alt", "mime_type", "width", "height"):
                    if key in value:
                        payload[key] = value[key]
            return {
                "type": "image",
                "artifact_type": "image",
                "renderer": "GalleryBlock",
                "viewer": "GalleryBlock",
                "payload": payload,
                "scene_contract": True,
                "human_visible": True,
            }
        return None

    # Other structured top-level fields already carry a semantic payload.
    payload = dict(value) if isinstance(value, dict) else (
        {"content": value} if value not in (None, "") else {}
    )
    if not payload:
        return None
    return {
        "type": kind,
        "artifact_type": kind,
        "renderer": _render_block_renderer(kind),
        "viewer": _render_block_renderer(kind),
        "payload": payload,
        "scene_contract": True,
        "human_visible": True,
    }


def _promote_top_level_visual_outputs(
    payload: dict[str, Any],
    *,
    image_generation_mode: bool = False,
    fallback_prompt: str = "",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Convert provider top-level visual keys into render blocks/specs once.

    In image_generation mode the Provider may describe the image, but it is not
    allowed to become the concrete render artifact. The local C_APRIL generator
    owns raster production, so provider image blocks are treated only as semantic
    input and are never promoted to a renderable image block.
    """
    if not isinstance(payload, dict):
        return [], {}

    blocks: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}
    specs: list[dict[str, Any]] = []

    for kind in _TOP_LEVEL_VISUAL_TYPES:
        if kind not in payload:
            continue
        value = payload.get(kind)
        block = _top_level_visual_block(kind, value)
        if block and not (image_generation_mode and kind in {"image", "gallery"}):
            blocks.append(block)

        if kind in {"image", "gallery"}:
            if kind == "gallery" and isinstance(value, list):
                values = value
            elif isinstance(value, dict) and isinstance(value.get("images"), list):
                values = value.get("images")
            else:
                values = [value]
            for item in values:
                spec = _build_image_generation_spec_from_provider(
                    item,
                    fallback_prompt=fallback_prompt,
                )
                if spec:
                    specs.append(spec)

    # De-duplicate specs without making the Provider answer another semantic
    # decision.  Room Register owns image-room execution; the concrete image engine materializes below the room.
    unique_specs: list[dict[str, Any]] = []
    seen = set()
    for spec in specs:
        key = json.dumps(spec, ensure_ascii=False, sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        unique_specs.append(spec)

    if unique_specs:
        metadata["image_generation_specs"] = unique_specs
        metadata["image_generation_spec"] = unique_specs[0]

    if blocks:
        metadata["provider_visual_types"] = [
            _safe_text(block.get("type")).lower()
            for block in blocks
            if isinstance(block, dict)
        ]

    return blocks, metadata


_IMAGE_TECHNICAL_FALLBACK = "Изображение не может быть отображено в текущем ответе."


def _strip_image_technical_fallback(value: Any) -> str:
    """Remove only the known image-provider technical fallback from user-visible text.

    The raw OpenAI response is logged before this sanitizer runs, so diagnostics
    retain the exact model output while the technical transport phrase never
    leaks into the canonical user response or image-generation handoff.
    """
    text = _safe_text(value)
    if not text:
        return ""
    cleaned = re.sub(re.escape(_IMAGE_TECHNICAL_FALLBACK), "", text, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", cleaned).strip(" \t\r\n-—:;")


def _is_image_technical_fallback(value: Any) -> bool:
    raw = re.sub(r"\s+", " ", _safe_text(value)).strip().casefold()
    expected = _IMAGE_TECHNICAL_FALLBACK.casefold()
    return raw == expected


def create_provider_contract(raw_text: Any, source_request: Any = None) -> dict[str, Any]:
    if isinstance(raw_text, dict) and raw_text.get("type") == "provider_response":
        return raw_text

    parsed = raw_text if isinstance(raw_text, dict) else _parse_provider_json(raw_text)

    # Accept one level of provider-envelope wrapping without changing the
    # canonical contract. This is a transport repair, not a semantic rewrite.
    canonical_payload = parsed
    if isinstance(parsed, dict):
        for wrapper_key in ("machine_response", "result", "data", "output"):
            wrapped = parsed.get(wrapper_key)
            if isinstance(wrapped, dict) and any(
                key in wrapped
                for key in ("answer", "content", "response", "text", "render_blocks", "artifacts", "image", "gallery", "diagram", "graph", "table")
            ):
                canonical_payload = wrapped
                break

    source_payload = machine_request_to_dict(source_request) if source_request is not None else {}
    source_constraints = source_payload.get("constraints") if isinstance(source_payload.get("constraints"), dict) else {}
    source_plan = source_constraints.get("representation_plan") if isinstance(source_constraints.get("representation_plan"), dict) else {}
    source_metadata = source_constraints.get("metadata") if isinstance(source_constraints.get("metadata"), dict) else {}
    visual_mode = _safe_text(
        source_plan.get("visual_production_mode")
        or source_metadata.get("visual_production_mode")
        or ""
    ).lower()
    image_generation_mode = visual_mode == "image_generation"
    fallback_image_prompt = _safe_text(
        (source_payload.get("intent") or {}).get("semantic_request")
        or (source_payload.get("intent") or {}).get("resolved_request")
        or _extract_request_text(source_payload)
        or (source_payload.get("conversation") or {}).get("resolved_request")
        or (source_payload.get("conversation") or {}).get("current_request")
    ).strip()

    top_level_visual_blocks, top_level_visual_metadata = _promote_top_level_visual_outputs(
        canonical_payload,
        image_generation_mode=image_generation_mode,
        fallback_prompt=fallback_image_prompt,
    )
    answer = _coerce_human_answer(canonical_payload.get("answer"))
    if not answer:
        answer = _coerce_human_answer(canonical_payload.get("content"))
    if not answer:
        answer = _coerce_human_answer(canonical_payload.get("response"))
    if not answer:
        answer = _coerce_human_answer(canonical_payload.get("text"))
    if not answer and canonical_payload is not parsed:
        answer = _coerce_human_answer(parsed.get("answer"))
    if not answer:
        answer = _coerce_human_answer(parsed.get("content"))
    if not answer:
        answer = _coerce_human_answer(parsed.get("response"))
    if not answer:
        answer = _coerce_human_answer(parsed.get("text"))
    if not answer:
        for block in canonical_payload.get("render_blocks", []) or []:
            if isinstance(block, dict):
                candidate = normalize_response_text(
                    block.get("content") or block.get("text") or block.get("answer") or ""
                )
                if candidate:
                    answer = candidate
                    break

    # This is transport-level text emitted by the first OpenAI step. Keep it in
    # IMAGE PROMPT TRACE: OPENAI RAW OUTPUT, but never allow it into the visible
    # provider answer or downstream image-generation content.
    if image_generation_mode:
        sanitized_answer = _strip_image_technical_fallback(answer)
        if sanitized_answer != answer:
            answer = sanitized_answer

    if not answer and visual_mode == "image_generation":
        candidate_metadata = dict(canonical_payload.get("metadata") or {}) if isinstance(canonical_payload.get("metadata"), dict) else {}
        candidate_metadata.update(top_level_visual_metadata)
        candidate_spec = candidate_metadata.get("image_generation_spec")
        if not isinstance(candidate_spec, dict):
            candidate_spec = canonical_payload.get("image_generation_spec") if isinstance(canonical_payload.get("image_generation_spec"), dict) else None
        if isinstance(candidate_spec, dict):
            answer = "Готово — изображение подготовлено."

    # Transport invariant: a non-empty OpenAI response must never collapse into
    # an empty canonical answer. When the model returns an empty JSON envelope
    # such as `{}`, recover locally from the current authoritative request.
    recovery_used = False
    if not answer:
        answer = _recover_answer_from_source_request(source_request)
        recovery_used = bool(answer)
    if not answer:
        answer = "Не удалось сформировать ответ."
        recovery_used = True

    # Never preserve a machine JSON envelope as visible content. The canonical
    # human content follows the already-unwrapped answer.
    content = _unwrap_model_answer(canonical_payload.get("content") or answer)
    if not content:
        content = answer
    blocks = _sanitize_render_block_texts(
        _clean_render_blocks(canonical_payload.get("render_blocks", []) or []),
        answer,
    )

    if top_level_visual_blocks:
        blocks.extend(top_level_visual_blocks)
    if not blocks:
        blocks = [{
            "type": "text",
            "content": answer,
            "text": answer,
            "renderer": "TextBlock",
            "viewer": "TextBlock",
            "scene_contract": True,
        }]

    raw_metadata = canonical_payload.get("metadata")
    metadata = dict(raw_metadata) if isinstance(raw_metadata, dict) else {}
    if top_level_visual_metadata:
        if top_level_visual_metadata.get("image_generation_specs"):
            existing_specs = metadata.get("image_generation_specs")
            merged_specs = list(existing_specs) if isinstance(existing_specs, list) else []
            merged_specs.extend(top_level_visual_metadata.get("image_generation_specs") or [])
            metadata["image_generation_specs"] = merged_specs
            metadata["image_generation_spec"] = merged_specs[0]
        for key, value in top_level_visual_metadata.items():
            metadata.setdefault(key, value)
    # Transport diagnostics: keep separate measurements for the model output and
    # the canonical fields so a later stage cannot be mistaken for an OpenAI
    # generation truncation. These are machine-only diagnostics.
    metadata["provider_transport_input"] = {
        "raw_text_chars": len(_safe_text(raw_text)),
        "parsed_answer_chars": len(answer),
        "parsed_content_chars": len(content),
        "canonical_answer_recovery_used": bool(recovery_used),
        "parsed_render_blocks": len(canonical_payload.get("render_blocks") or []) if isinstance(canonical_payload.get("render_blocks"), list) else 0,
        "parsed_artifacts": len(canonical_payload.get("artifacts") or []) if isinstance(canonical_payload.get("artifacts"), list) else 0,
    }
    # Keep the provider's semantic task update in the canonical metadata channel.
    # This makes task state round-trip through Provider -> Executor -> StateManager.
    for key in ("dialogue_task_state", "interactive_task_state", "open_task", "task_state"):
        if key in canonical_payload and isinstance(canonical_payload.get(key), dict):
            metadata["dialogue_task_state"] = canonical_payload[key]
            break
    if "dialogue_task_state" not in metadata and isinstance(metadata.get("interactive_task_state"), dict):
        metadata["dialogue_task_state"] = metadata["interactive_task_state"]
    if "image_generation_spec" not in metadata and isinstance(
        canonical_payload.get("image_generation_spec"), dict
    ):
        metadata["image_generation_spec"] = canonical_payload.get("image_generation_spec")

    if image_generation_mode:
        # IMAGE ROUTE ONLY. Ordinary dialogue never reaches this branch.
        # request_anchor = WHAT triggered generation; OpenAI plan = WHAT TO DRAW.
        candidate_spec = metadata.get("image_generation_spec")
        if not isinstance(candidate_spec, dict):
            candidate_spec = canonical_payload.get("image_generation_spec")

        provider_signal = None
        candidate_metadata = canonical_payload.get("metadata")
        if isinstance(candidate_metadata, dict) and isinstance(candidate_metadata.get("image_generation_signal"), dict):
            provider_signal = candidate_metadata.get("image_generation_signal")
        if provider_signal is None and isinstance(metadata.get("image_generation_signal"), dict):
            provider_signal = metadata.get("image_generation_signal")
        if not isinstance(provider_signal, dict):
            provider_signal = {}

        signal_route = _safe_text(provider_signal.get("route")).strip().upper()
        signal_execute = provider_signal.get("execute") is True
        signal_anchor = _safe_text(provider_signal.get("request_anchor")).strip()
        signal_prompt = _image_prompt_from_provider_payload(provider_signal.get("prompt"))
        provider_signal_valid = bool(
            signal_route == "C_APRIL_IMAGES_GENERATOR"
            and signal_execute
            and signal_anchor
            and (not fallback_image_prompt or re.sub(r"\s+", " ", signal_anchor).casefold() == re.sub(r"\s+", " ", fallback_image_prompt).casefold())
            and signal_prompt
        )

        normalized_spec = _build_image_generation_spec_from_provider(
            candidate_spec if isinstance(candidate_spec, dict) else canonical_payload.get("image"),
            fallback_prompt=fallback_image_prompt,
        )
        if normalized_spec is None and fallback_image_prompt:
            normalized_spec = _build_image_generation_spec_from_provider(
                canonical_payload.get("image") if isinstance(canonical_payload.get("image"), (dict, str)) else {"prompt": fallback_image_prompt},
                fallback_prompt=fallback_image_prompt,
            )
        if normalized_spec:
            semantic_generation_prompt = _safe_text(
                normalized_spec.get("openai_structured_visual_plan_semantic")
                or normalized_spec.get("prompt")
            ).strip()
            if not semantic_generation_prompt:
                semantic_generation_prompt = fallback_image_prompt.strip()

            profile = _image_render_profile_from_context(
                source_payload,
                normalized_spec.get("visual_context"),
                semantic_generation_prompt,
            )
            normalized_spec["prompt"] = semantic_generation_prompt
            normalized_spec["request_anchor"] = fallback_image_prompt
            normalized_spec["render_profile"] = profile["name"]
            normalized_spec["render_profile_source"] = profile["source"]

            raw_plan = normalized_spec.get("openai_structured_visual_plan_raw")
            raw_plan_text = json.dumps(raw_plan, ensure_ascii=False, default=str) if raw_plan is not None else ""
            metadata["image_generation_prompt_grounding"] = "OPENAI_SEMANTIC_PLAN_PLUS_STRUCTURED_PLAN"
            metadata["image_generation_user_trigger"] = fallback_image_prompt
            metadata["image_generation_semantic_prompt"] = semantic_generation_prompt[:12000]
            metadata["image_render_profile"] = profile["name"]
            metadata["image_render_profile_source"] = profile["source"]
            metadata["openai_structured_visual_plan_preserved"] = raw_plan is not None
            metadata["openai_structured_visual_plan_format"] = (
                _safe_text(raw_plan.get("format")).strip().lower()
                if isinstance(raw_plan, dict) else ""
            )
            metadata["openai_structured_visual_plan_chars"] = len(raw_plan_text)

            if provider_signal_valid and signal_prompt:
                metadata["openai_renderer_prompt_received"] = signal_prompt[:12000]

            metadata["image_generation_spec"] = normalized_spec
            metadata["image_generation_specs"] = [normalized_spec]
            metadata["image_generation_execution"] = "C_APRIL_IMAGES_GENERATOR"
            metadata["provider_image_render_ignored"] = True
            metadata["provider_pixels_disallowed"] = True

            metadata["image_generation_signal"] = {
                "schema": PROVIDER_IMAGE_GENERATION_SIGNAL_VERSION,
                "route": "C_APRIL_IMAGES_GENERATOR",
                "execute": True,
                "request_anchor": fallback_image_prompt,
                "prompt_source": "OPENAI_STRUCTURED_VISUAL_PLAN",
                "prompt": semantic_generation_prompt,
                "target_model": "gpt-image-2",
                "single_route": True,
                "provider_emitted": True,
                "openai_plan_preserved": raw_plan is not None,
                "render_profile": profile["name"],
                "request_id": str(source_payload.get("request_id") or "").strip(),
            }

        blocks = [
            block for block in blocks
            if _safe_text(
                block.get("type") or block.get("artifact_type") or block.get("representation")
            ).lower() not in {"image", "gallery"}
        ]

    raw_scene = canonical_payload.get("scene")
    scene = dict(raw_scene) if isinstance(raw_scene, dict) else {}
    raw_artifacts = canonical_payload.get("artifacts")
    artifacts = list(raw_artifacts) if isinstance(raw_artifacts, list) else []
    if image_generation_mode:
        artifacts = [
            artifact for artifact in artifacts
            if not isinstance(artifact, dict)
            or _safe_text(
                artifact.get("type") or artifact.get("artifact_type") or artifact.get("representation")
            ).lower() not in {"image", "gallery"}
        ]
    raw_scene_plan = canonical_payload.get("scene_plan")
    scene_plan = list(raw_scene_plan) if isinstance(raw_scene_plan, list) else ([str(raw_scene_plan)] if raw_scene_plan else ["text"])
    raw_render_priority = canonical_payload.get("render_priority")
    render_priority = list(raw_render_priority) if isinstance(raw_render_priority, list) else []


    # Current-request authority: when the Processor requested text only, a
    # model-side table/graph/link is not allowed to manufacture a second
    # presentation. Preserve only text/markdown blocks in that case.
    source_outputs = list(source_payload.get("requested_outputs") or [])
    source_requires_structured = bool(source_payload.get("required_artifacts")) or any(
        str(x).lower() not in {"text", "markdown"}
        for x in source_outputs
    )
    if source_outputs and not source_requires_structured and all(str(x).lower() in {"text", "markdown"} for x in source_outputs):
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

    visible_response = _strip_image_technical_fallback(_unwrap_model_answer(canonical_payload.get("response") or answer)) if image_generation_mode else _unwrap_model_answer(canonical_payload.get("response") or answer)
    visible_summary = _strip_image_technical_fallback(_unwrap_model_answer(canonical_payload.get("summary") or _compact_summary(answer, blocks))) if image_generation_mode else _unwrap_model_answer(canonical_payload.get("summary") or _compact_summary(answer, blocks))
    if image_generation_mode and not answer:
        answer = "Готово — изображение подготовлено."
    if image_generation_mode and not visible_response:
        visible_response = answer
    if image_generation_mode and not visible_summary:
        visible_summary = _compact_summary(answer, blocks)

    return {
        "type": "provider_response",
        "machine_response": {
            "answer": answer,
            "content": answer,
            "response": visible_response,
            "summary": visible_summary,
            "explanation": _strip_image_technical_fallback(normalize_response_text(canonical_payload.get("explanation") or "")) if image_generation_mode else normalize_response_text(canonical_payload.get("explanation") or ""),
            "scene": scene,
            "artifacts": artifacts,
            "render_blocks": blocks,
            "scene_plan": scene_plan,
            "render_priority": render_priority,
            "confidence": canonical_payload.get("confidence", 1.0),
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
    source_preview = contract.get("processor_input") if isinstance(contract.get("processor_input"), dict) else {}
    source_constraints_preview = source_preview.get("constraints") if isinstance(source_preview.get("constraints"), dict) else {}
    source_plan_preview = source_constraints_preview.get("representation_plan") if isinstance(source_constraints_preview.get("representation_plan"), dict) else {}
    image_generation_preview = _safe_text(source_plan_preview.get("visual_production_mode") or "").strip().lower() == "image_generation"
    if image_generation_preview:
        answer = _strip_image_technical_fallback(answer)
        if not answer:
            answer = "Готово — изображение подготовлено."
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
    mr.setdefault("metadata", {})["post_provider_render_stage"] = "AFTER_PROVIDER"
    mr.setdefault("metadata", {})["post_provider_render_authority"] = "EXECUTOR_SCENE_CONTRACT"
    response_text = normalize_response_text(mr.get("response") or answer)
    mr["response"] = _strip_image_technical_fallback(response_text) if image_generation_preview else response_text
    mr["content"] = _strip_image_technical_fallback(mr["content"]) if image_generation_preview else mr["content"]

    original_blocks = mr.get("render_blocks") or []
    mr["artifacts"] = list(mr.get("artifacts") or [])
    mr.setdefault("metadata", {})["provider_pre_finalize_counts"] = {
        "answer_length": len(mr.get("answer") or ""),
        "content_length": len(mr.get("content") or ""),
        "render_blocks": len(original_blocks) if isinstance(original_blocks, list) else 0,
        "artifacts": len(mr.get("artifacts") or []),
    }

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
    # Final canonical transport safety: structured blocks without usable
    # payload are never exposed to the SceneContract/Web renderer.
    before_count = len(original_blocks) if isinstance(original_blocks, list) else 0
    after_count = len(mr.get("render_blocks") or [])
    mr.setdefault("metadata", {})["invalid_structured_blocks_dropped"] = max(0, before_count - after_count)
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
        "render_payload_canonicalization": True,
        "render_payload_non_empty_guard": True,
        "interpretation_control_honored": True,
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

        provider_plan = _provider_context_plan(source_request)
        provider_log({
            "provider_version": APRIL_QUANTUM_PROVIDER_VERSION,
            "model": APRIL_QUANTUM_PROVIDER_MODEL,
            "complexity": complexity,
            "max_output_tokens": output_tokens,
            "input_token_budget": INPUT_TOKEN_BUDGET,
            "single_call": True,
            "no_model_escalation": True,
            "provider_context_plan_version": _safe_text(provider_plan.get("version")),
            "provider_context_authority": "INTERPRETATION" if provider_plan else "LEGACY",
            "provider_must_not_reselect_context": bool(provider_plan),
        })

        # OpenAI's synchronous SDK would block the async Web/Telegram event loop.
        # Offload this single call to a worker thread; provider count remains 1.
        response = await asyncio.to_thread(_get_openai_client().responses.create, **request)
        usage = _extract_usage(response)
        raw_text = _extract_openai_text(response)

        # IMAGE PROMPT TRACE: capture the exact textual payload returned by
        # OpenAI before any local Provider parsing/normalization occurs.
        # This is intentionally limited to image_generation turns so normal
        # text traffic is not flooded with model output.
        source_constraints = source_request.get("constraints") if isinstance(source_request.get("constraints"), dict) else {}
        source_representation_plan = (
            source_constraints.get("representation_plan")
            if isinstance(source_constraints.get("representation_plan"), dict)
            else {}
        )
        source_metadata = (
            source_constraints.get("metadata")
            if isinstance(source_constraints.get("metadata"), dict)
            else {}
        )
        source_semantic = source_request.get("semantic") if isinstance(source_request.get("semantic"), dict) else {}
        source_output_modes = [
            _safe_text(item).strip().lower()
            for item in (source_request.get("requested_outputs") or [])
            if _safe_text(item).strip()
        ]
        normalized_input_text = json.dumps(normalized_input, ensure_ascii=False, default=str).lower()
        image_trace = any(
            candidate == "image_generation"
            for candidate in (
                _safe_text(source_representation_plan.get("visual_production_mode")).strip().lower(),
                _safe_text(source_metadata.get("visual_production_mode")).strip().lower(),
                _safe_text(source_semantic.get("visual_production_mode")).strip().lower(),
                _safe_text(source_semantic.get("representation")).strip().lower(),
                _safe_text((provider_plan or {}).get("visual_production_mode")).strip().lower(),
                _safe_text((provider_plan or {}).get("representation")).strip().lower(),
                *source_output_modes,
            )
        ) or "output_mode\": image_generation" in normalized_input_text or "output_mode: image_generation" in normalized_input_text or "\"output_mode\":\"image_generation\"" in normalized_input_text
        if image_trace:
            provider_log(
                "\n===== IMAGE PROMPT TRACE: INPUT TO OPENAI =====",
                json.dumps({
                    "current_user_request": _extract_request_text(source_request),
                    "normalized_input": normalized_input,
                }, ensure_ascii=False, indent=2, default=str)[:12000],
                "===== END INPUT TO OPENAI =====\n",
            )
            provider_log(
                "\n===== IMAGE PROMPT TRACE: OPENAI RAW OUTPUT =====",
                _safe_text(raw_text)[:12000],
                "===== END OPENAI RAW OUTPUT =====\n",
            )

        provider_log({
            "provider_output_transport": {
                "response_type": type(response).__name__,
                "direct_output_text_chars": len(_safe_text(getattr(response, "output_text", None))),
                "raw_text_chars": len(_safe_text(raw_text)),
                "raw_text_preview": _safe_text(raw_text)[:160],
                "output_items": len(getattr(response, "output", None) or [])
                if hasattr(getattr(response, "output", None), "__len__") else None,
            }
        })
        if not raw_text:
            raise RuntimeError("GPT-5.6 Luna returned no textual output.")

        contract = create_provider_contract(raw_text, source_request=messages)

        if image_trace:
            traced_metadata = {}
            try:
                traced_metadata = dict((contract.get("machine_response") or {}).get("metadata") or {})
            except Exception:
                traced_metadata = {}
            traced_spec = traced_metadata.get("image_generation_spec")
            traced_signal = traced_metadata.get("image_generation_signal")
            provider_log(
                "===== IMAGE PROMPT TRACE: PROVIDER SPEC AFTER PARSE =====",
                json.dumps(
                    traced_spec,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )[:12000] if isinstance(traced_spec, dict) else _safe_text(traced_spec),
                "===== END PROVIDER SPEC AFTER PARSE =====",
            )
            provider_log(
                "===== IMAGE PROMPT TRACE: PROVIDER GENERATION SIGNAL =====",
                json.dumps(traced_signal, ensure_ascii=False, indent=2, default=str)[:5000]
                if isinstance(traced_signal, dict) else _safe_text(traced_signal),
                "===== END PROVIDER GENERATION SIGNAL =====",
            )
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
            "provider_context_plan_version": _safe_text(provider_plan.get("version")),
            "provider_context_authority": "INTERPRETATION" if provider_plan else "LEGACY",
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
# Provider emits the semantic image plan; Room Register executes image_generate,
# which delegates concrete raster production to C_APRIL_IMAGES_GENERATOR.
# Text generation, voice transcription, and visual analysis remain unchanged.

