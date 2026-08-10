# =====================================================
# APRIL TEXT MODULE QUANTUM 1.2
# =====================================================
"""
TEXT MODULE RESPONSIBILITY:
- receive the canonical MachineRequest prepared by Executor
- call the canonical Provider exactly once
- preserve the Provider's full MachineResponse
- preserve Markdown/text verbatim enough for Web rendering
- build the Artifact/Fiber transport envelope
- never classify text into FormulaBlock/CodeBlock/TableBlock/etc.
- never create a second AI request
- never turn summary into visible content
- never create a second visible answer

Single route:
Executor -> TextModule -> Quantum Provider -> TextModule -> Artifact Contract -> Executor
"""

from __future__ import annotations

import json
import re
import time
import traceback
from typing import Any, Dict, Optional

from storage import get_user_plan
from blocks.provider_router import generate_text
from blocks.C_ARTIFACT_CONTRACT import (
    MachineResponse,
    create_transport_contract,
)

APRIL_FILE_ID = "APRIL_TEXT_ORCHESTRATION_MODULE"
APRIL_VERSION = "QUANTUM_1_4"

TEXT_QUANTUM_SINGLE_ROUTE = True
TEXT_QUANTUM_NO_FALLBACK = True
TEXT_QUANTUM_ONE_PROVIDER_CALL = True
TEXT_QUANTUM_MODEL = "gpt-5.6-luna"
TEXT_QUANTUM_SUMMARY_VISIBLE = False

TEXT_INPUT_CHANNEL = {
    "source": "executor",
    "target": "text_module",
    "mode": "machine_request",
    "single_route": True,
}

TEXT_OUTPUT_CHANNEL = {
    "source": "text_module",
    "target": "artifact_contract",
    "mode": "machine_response",
    "single_route": True,
}

PATCH_LOG: list[str] = []
TEXT_EXECUTION_LOG: list[dict[str, Any]] = []


def safe_patch_log(message: Any) -> None:
    try:
        text = str(message)
        PATCH_LOG.append(text)
        print("TEXT MODULE:", text)
    except Exception:
        pass


def log_text_execution(stage: str, payload: Any = None) -> None:
    try:
        entry = {
            "time": time.time(),
            "stage": stage,
            "payload": str(payload)[:500] if payload is not None else None,
        }
        TEXT_EXECUTION_LOG.append(entry)
        print("🧠 TEXT:", stage)
    except Exception:
        pass


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return str(value)
    except Exception:
        return ""


def _compact_visible_text(value: Any) -> str:
    """Extract visible answer without stringifying a MachineResponse object."""
    if value is None:
        return ""

    if isinstance(value, MachineResponse):
        for key in ("answer", "content", "response"):
            candidate = safe_text(getattr(value, key, ""))
            if candidate.strip():
                return candidate.strip()
        return ""

    if isinstance(value, dict):
        mr = value.get("machine_response")
        if isinstance(mr, dict):
            for key in ("answer", "content", "response"):
                candidate = safe_text(mr.get(key, ""))
                if candidate.strip():
                    return candidate.strip()
        for key in ("answer", "content", "response", "text", "display_text", "markdown"):
            candidate = safe_text(value.get(key, ""))
            if candidate.strip():
                return candidate.strip()
        return ""

    return safe_text(value).strip()


def _clean_provider_packet(packet: Any) -> Dict[str, Any]:
    """Keep provider packet structured; never collapse it to one text string."""
    if isinstance(packet, dict):
        return packet
    return {}


def _machine_response_from_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
    mr = packet.get("machine_response")
    if isinstance(mr, dict):
        return mr
    return packet


def _canonical_answer_from_packet(packet: Dict[str, Any]) -> str:
    mr = _machine_response_from_packet(packet)
    for key in ("answer", "content", "response"):
        value = mr.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _compact_scene_summary(packet: Dict[str, Any], answer: str) -> str:
    """
    Summary is metadata only.
    It must never equal a complete visible answer.
    """
    mr = _machine_response_from_packet(packet)
    blocks = mr.get("render_blocks", [])
    types: list[str] = []

    if isinstance(blocks, list):
        for block in blocks:
            if not isinstance(block, dict):
                continue
            block_type = safe_text(
                block.get("type") or block.get("artifact_type") or "text"
            ).lower()
            if block_type not in types:
                types.append(block_type)

    first_line = answer.split("\n", 1)[0].strip() if answer else ""
    if len(first_line) > 110:
        first_line = first_line[:107] + "..."

    if types:
        return f"{first_line} | scene: {', '.join(types[:5])}".strip(" |")
    return first_line


def _clean_markdown_preserving_content(text: Any) -> str:
    """
    Minimal normalization only:
    preserve headings, paragraphs, lists, code fences and inline LaTeX/Markdown.
    Do NOT classify formulas or code here.
    """
    value = safe_text(text).replace("\r\n", "\n").replace("\r", "\n").strip()
    if not value:
        return ""

    # Remove accidental JSON fences only when the entire provider output is a
    # JSON wrapper; ordinary Markdown code fences remain untouched.
    if value.startswith("```json") and value.endswith("```"):
        body = value[7:-3].strip()
        try:
            decoded = json.loads(body)
            if isinstance(decoded, dict):
                return _canonical_answer_from_packet(decoded)
        except Exception:
            pass

    # Collapse excessive blank lines, but keep paragraph structure.
    value = re.sub(r"\n{4,}", "\n\n", value)
    # Remove trailing spaces, not Markdown markers.
    value = "\n".join(line.rstrip() for line in value.split("\n"))
    return value.strip()


def sanitize_model_output(value: Any) -> str:
    """Presentation-safe text cleanup without flattening Markdown."""
    text = _clean_markdown_preserving_content(value)
    if not text:
        return ""

    blocked_prefixes = (
        "internal reasoning:",
        "chain of thought:",
        "system prompt:",
        "execution room:",
        "cognitive state:",
    )

    cleaned: list[str] = []
    for line in text.split("\n"):
        lowered = line.strip().lower()
        if any(lowered.startswith(prefix) for prefix in blocked_prefixes):
            continue
        cleaned.append(line)

    return "\n".join(cleaned).strip()


def format_rich_text_for_word(text: Any) -> str:
    """
    Compatibility name retained.
    This is deliberately Markdown-preserving; it no longer flattens paragraphs
    or converts formulas into special renderer blocks.
    """
    return sanitize_model_output(text)


def apply_visual_beautify(text: Any, semantic: Optional[dict] = None) -> str:
    # Web owns renderer selection. Text module only preserves the payload.
    return sanitize_model_output(text)


def is_structured_payload(value: Any) -> bool:
    return isinstance(value, (dict, list, tuple))


def is_renderer_payload(text: Any) -> bool:
    # Kept as a compatibility predicate. It does not perform routing.
    if not isinstance(text, str):
        return False
    return any(marker in text for marker in ("[[graph", "[[formula", "[[diagram", "<svg", "<canvas"))


def trim_text(text: Any, limit: int = 5000) -> str:
    value = safe_text(text)
    return value if len(value) <= limit else value[:limit] + "…"


def trim_messages(messages: Any, limit: int = 10) -> list[dict[str, str]]:
    if not isinstance(messages, list):
        return []
    result: list[dict[str, str]] = []
    for item in messages[-limit:]:
        if not isinstance(item, dict):
            continue
        content = sanitize_model_output(item.get("content", ""))
        if not content:
            continue
        result.append({
            "role": safe_text(item.get("role") or "user"),
            "content": content,
        })
    return result


def build_message_stack(system_state: str, history: list[dict], user_text: str):
    # Compatibility helper only. The quantum route does NOT use this to call OpenAI.
    return [
        {"role": "system", "content": safe_text(system_state)},
        *trim_messages(history),
        {"role": "user", "content": sanitize_model_output(user_text)},
    ]


def build_plan_runtime(plan: Any) -> dict[str, Any]:
    plan_value = safe_text(plan).lower().strip()
    history_limits = {"free": 15, "lite": 30, "premium": 999999}
    token_modes = {"free": "compact", "lite": "balanced", "premium": "extended"}
    return {
        "plan": plan_value,
        "history_limit": history_limits.get(plan_value, 15),
        "token_mode": token_modes.get(plan_value, "compact"),
        "web_priority": plan_value in {"lite", "premium"},
        "extended_memory": plan_value == "premium",
    }


def build_cognitive_state(state: dict, semantic: dict, cognition: dict, response_decision: dict) -> str:
    """
    Compatibility metadata for existing callers.
    Executor is the authoritative cognitive layer.
    """
    blocks: list[str] = []

    active_flow = state.get("active_flow")
    if isinstance(active_flow, dict) and active_flow.get("type"):
        blocks.append(f"Trajectory: {active_flow['type']}")

    behavior: list[str] = []
    if response_decision.get("should_reduce_talking"):
        behavior.append("отвечай кратко")
    if response_decision.get("should_continue_trajectory"):
        behavior.append("сохраняй continuity")
    if cognition.get("exploration_mode"):
        behavior.append("поддерживай exploration")

    if behavior:
        blocks.append("Поведение: " + ", ".join(behavior))

    active_visual_scene = state.get("active_visual_scene")
    if isinstance(active_visual_scene, dict) and active_visual_scene:
        blocks.append(
            f"Visual continuity active: {active_visual_scene.get('scene_type', 'unknown')}"
        )

    summary = safe_text(state.get("memory_summary"))
    if summary:
        blocks.append("Память: " + trim_text(summary, 1800))

    return "\n".join(blocks)


def prevent_repeat_response(state: dict, reply: Any) -> str:
    """
    Old behavior added '(continuing)' and created a second visible string.
    New behavior never mutates a valid answer into a second answer.
    """
    value = sanitize_model_output(reply)
    state["last_reply_duplicate_suppressed"] = bool(
        safe_text(state.get("last_reply")).strip() and
        safe_text(state.get("last_reply")).strip() == value.strip()
    )
    return value


def update_topic(state: dict, text: Any) -> None:
    value = safe_text(text).lower()
    if "код" in value:
        state["topic"] = "code"
    elif "бот" in value:
        state["topic"] = "bot"
    elif "сайт" in value:
        state["topic"] = "website"
    elif "дизайн" in value:
        state["topic"] = "design"


def _extract_canonical_machine_request(state: dict) -> Any:
    """
    The Executor is the sole owner of MachineRequest construction.
    TextModule must never invent a parallel request.
    """
    candidates = (
        state.get("machine_request"),
        (state.get("context") or {}).get("machine_request"),
        (state.get("executor_context") or {}).get("machine_request"),
        (state.get("transport") or {}).get("machine_request"),
    )

    for candidate in candidates:
        if candidate is not None:
            return candidate

    raise RuntimeError("Canonical MachineRequest missing: Executor must supply it.")


def normalize_provider_output(output: Any):
    """
    Preserve the full provider packet and return its canonical visible answer.
    No summary promotion, no renderer reclassification.
    """
    packet = _clean_provider_packet(output)

    if packet:
        mr = _machine_response_from_packet(packet)
        answer = _canonical_answer_from_packet(packet)

        # Keep canonical fields only when missing; do not overwrite structured content.
        if isinstance(mr, dict):
            if answer:
                mr.setdefault("answer", answer)
                mr.setdefault("content", answer)
                mr.setdefault("response", answer)
            render_blocks = mr.get("render_blocks")
            if isinstance(render_blocks, list):
                packet["render_blocks"] = render_blocks

        packet["machine_response"] = mr
        return answer, packet

    return sanitize_model_output(output), None


def _provider_packet_render_blocks(packet: Dict[str, Any]) -> list[dict]:
    mr = _machine_response_from_packet(packet)
    blocks = mr.get("render_blocks", [])
    return [dict(b) for b in blocks if isinstance(b, dict)] if isinstance(blocks, list) else []


def _provider_packet_artifacts(packet: Dict[str, Any]) -> list[Any]:
    mr = _machine_response_from_packet(packet)
    artifacts = mr.get("artifacts", [])
    return list(artifacts) if isinstance(artifacts, list) else []


def _build_text_artifact_data(reply: str, packet: Dict[str, Any], runtime: dict) -> dict:
    mr = _machine_response_from_packet(packet)
    blocks = _provider_packet_render_blocks(packet)
    artifacts = _provider_packet_artifacts(packet)

    return {
        # "text" identifies the source room, not the visual renderer.
        "type": "text",
        "artifact_type": "text",
        "content": reply,
        "answer": reply,
        "summary": _compact_scene_summary(packet, reply),
        "presentation_mode": "markdown",
        "render_blocks": blocks,
        "artifacts": artifacts,
        "scene": mr.get("scene", {}) if isinstance(mr, dict) else {},
        "scene_plan": list(mr.get("scene_plan", []) or []) if isinstance(mr, dict) else [],
        "render_priority": list(mr.get("render_priority", []) or []) if isinstance(mr, dict) else [],
        "provider_response": packet,
        "provider_machine_response": mr,
        "runtime": {
            "plan": runtime.get("plan"),
            "token_mode": runtime.get("token_mode"),
        },
        "machine_channels": {
            "input": TEXT_INPUT_CHANNEL,
            "output": TEXT_OUTPUT_CHANNEL,
        },
        "single_route": True,
        "summary_visible": False,
    }


async def process(user_id, text, state, energy="MEDIUM"):
    """Canonical TextModule bridge: Executor request -> one Luna call -> one transport envelope."""
    log_text_execution("TEXT_MODULE_ENTER", text)
    state = state if isinstance(state, dict) else {}
    machine_request = _extract_canonical_machine_request(state)
    plan = get_user_plan(user_id)
    runtime = build_plan_runtime(plan)

    log_text_execution("CANONICAL_MACHINE_REQUEST_READY", {"type":type(machine_request).__name__, "model":TEXT_QUANTUM_MODEL})
    output = await generate_text(messages=machine_request, temperature=None, max_output_tokens=None, model=TEXT_QUANTUM_MODEL)

    packet = _clean_provider_packet(output)
    reply, packet = normalize_provider_output(packet)
    reply = sanitize_model_output(reply)
    if not reply:
        raise RuntimeError("Quantum Provider returned an empty canonical answer.")

    reply = prevent_repeat_response(state, reply)
    state["last_reply"] = reply
    state["last_text_time"] = time.time()
    state["provider_response"] = packet
    state["provider_machine_response"] = _machine_response_from_packet(packet)

    artifact_data = _build_text_artifact_data(reply, packet, runtime)
    transport_contract = create_transport_contract(
        artifact_type="text",
        room_source="TEXT_ROOM",
        data=artifact_data,
        user_id=user_id,
        subscription=runtime.get("plan","Free"),
    )

    mr=getattr(transport_contract,"machine_response",None)
    sc=getattr(transport_contract,"scene_contract",None)
    blocks=list(getattr(mr,"render_blocks",[]) or []) if mr else _provider_packet_render_blocks(packet)
    artifacts=list(getattr(mr,"artifacts",[]) or []) if mr else _provider_packet_artifacts(packet)

    log_text_execution("TEXT_ARTIFACT_READY", {"answer_len":len(reply),"render_blocks":len(blocks),"artifacts":len(artifacts),"provider_calls":1,"model":TEXT_QUANTUM_MODEL})

    return {
        "type":"text","content":reply,"answer":reply,
        "summary":getattr(mr,"summary","") if mr else _compact_scene_summary(packet,reply),
        "machine_response":mr,"scene_contract":sc,
        "artifact_contract":transport_contract,"transport_contract":transport_contract,
        "runtime":artifact_data["runtime"],"machine_channels":artifact_data["machine_channels"],
        "provider_response":packet,"provider_machine_response":state.get("provider_machine_response",{}),
        "render_blocks":blocks,"artifacts":artifacts,
        "single_route":True,"provider_calls":1,"provider_model":TEXT_QUANTUM_MODEL,"summary_visible":False,
    }

def get_text_execution_log() -> list[dict[str, Any]]:
    return list(TEXT_EXECUTION_LOG)


def get_text_patch_log() -> list[str]:
    return list(PATCH_LOG)


__all__ = [
    "process",
    "generate",
    "execute",
    "normalize_provider_output",
    "format_rich_text_for_word",
    "apply_visual_beautify",
    "create_transport_contract",
    "TEXT_QUANTUM_MODEL",
    "TEXT_QUANTUM_SINGLE_ROUTE",
    "TEXT_QUANTUM_ONE_PROVIDER_CALL",
]
