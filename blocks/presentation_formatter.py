# =====================================================
# APRIL WEB PRESENTATION ORCHESTRATOR — UNIFIED SIGNAL ENGINE
# =====================================================

"""
April presentation coordinator.

This module is a LOSSLESS consumer of the canonical presentation signals
emitted by the Quantum Processor / Executor.

Contract:
    Provider
      -> Quantum Processor Executor
      -> presentation_signal_v4
      -> SceneContract
      -> this module
      -> April Web renderer

The formatter does NOT create a second presentation protocol, infer renderer
types from prose, mutate structured renderer payloads, or build SceneContract.
It only:
  1. extracts the Executor's canonical presentation_signal_v4;
  2. verifies signal/payload alignment;
  3. preserves the exact render_blocks/artifacts;
  4. applies human-text cleanup ONLY to plain text strings;
  5. returns the same machine route and payload shape.

Canonical signal owner:
    QUANTUM_PROCESSOR

Canonical signal version:
    presentation_signal_v4
"""

from __future__ import annotations

from copy import deepcopy
import json
import re
from typing import Any

print("APRIL PRESENTATION ORCHESTRATOR: UNIFIED SIGNAL ENGINE LOADED")


PRESENTATION_ENGINE_VERSION = "APRIL-QUANTUM-PRESENTATION-V2"
PRESENTATION_SIGNAL_VERSION = "presentation_signal_v4"
PRESENTATION_ROUTE_VERSION = "fiber_scene_v2"

SUPPORTED_SIGNAL_KINDS = {
    "text",
    "mixed",
    "structured",
    "formula",
    "table",
    "graph",
    "diagram",
    "link",
    "code",
    "gallery",
    "audio",
    "video",
    "file",
    "action",
    "memory",
}

SIGNAL_TO_WEB_RENDERER = {
    "text": ("mcdowell", "presentation_matrix"),
    "mixed": ("mcdowell", "presentation_matrix"),
    "structured": ("mcdowell", "presentation_matrix"),
    "formula": ("mcdowell", "katex"),
    "table": ("table", "table"),
    "graph": ("graph", "graph"),
    "diagram": ("graph", "diagram"),
    "link": ("link", "link_card"),
    "code": ("code", "syntax"),
    "gallery": ("gallery", "media"),
    "audio": ("audio", "media"),
    "video": ("video", "media"),
    "file": ("file", "file_card"),
    "action": ("action", "action"),
    "memory": ("memory", "memory"),
}

FORMAT_LOG = []


def _s(value: Any) -> str:
    return str(value or "").strip()


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def safe_format_log(message: str) -> None:
    try:
        print("APRIL PRESENTATION:", message)
        FORMAT_LOG.append(str(message))
    except Exception:
        pass


def presentation_enter(response: Any, semantic: dict | None = None) -> dict:
    safe_format_log(f"ENTER PRESENTATION: {_s(response)[:80]}")
    return {
        "presentation_active": True,
        "machine_isolation": True,
        "signal_version": PRESENTATION_SIGNAL_VERSION,
    }


def presentation_exit(final_response: Any) -> dict:
    safe_format_log(f"EXIT PRESENTATION: {_s(final_response)[:80]}")
    return {
        "presentation_complete": True,
        "human_output_ready": True,
        "continuity_preserved": True,
        "signal_version": PRESENTATION_SIGNAL_VERSION,
    }


def is_machine_payload(value: Any) -> bool:
    return isinstance(value, dict) and bool(value.get("machine_only"))


def is_scene_contract(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return (
        value.get("type") == "scene_contract"
        or isinstance(value.get("render_blocks"), list)
        and (
            value.get("transport_contract") == "scene_first"
            or value.get("scene_version")
            or value.get("supported_payloads")
        )
    )


def _decode_json_object(value: Any) -> Any:
    """Decode JSON-shaped wrappers without turning structured payloads into text."""
    current = value
    for _ in range(4):
        if not isinstance(current, str):
            break
        text = current.strip()
        if not text or text[0] not in "[{":
            break
        try:
            parsed = json.loads(text)
        except Exception:
            break
        if not isinstance(parsed, (dict, list)):
            break
        current = parsed
    return current


def _signal_from_block(block: dict) -> dict:
    signal = block.get("presentation")
    if isinstance(signal, dict):
        return signal

    # The Executor may expose the signal under explicit machine metadata.
    for key in ("presentation_signal", "presentation_contract"):
        candidate = block.get(key)
        if isinstance(candidate, dict):
            return candidate

    return {}


def _canonical_payload(block: dict) -> dict:
    payload = block.get("payload")
    if isinstance(payload, dict):
        return payload

    artifact = block.get("artifact")
    if isinstance(artifact, dict):
        nested = artifact.get("payload")
        if isinstance(nested, dict):
            return nested
        return artifact

    return {}


def _payload_keys_for_alignment(kind: str) -> set[str]:
    return {
        "formula": {"steps", "formula", "equation", "expression", "math", "content"},
        "table": {"columns", "headers", "rows", "cells", "values"},
        "graph": {"series", "data", "x", "y", "axes"},
        "diagram": {"nodes", "edges", "elements", "items"},
        "link": {"url", "href", "title", "description", "domain", "icon"},
        "code": {"language", "source", "content", "code"},
        "gallery": {"items", "images", "src", "url", "caption", "alt"},
        "audio": {"url", "src", "path", "mime", "duration", "title"},
        "video": {"url", "src", "path", "mime", "duration", "thumbnail", "title"},
        "file": {"url", "path", "file", "mime", "size", "name", "title"},
        "action": {"actions", "target", "parameters", "label", "description"},
        "memory": {"items", "content", "title", "description"},
    }.get(kind, set())


def validate_executor_signal(block: dict) -> dict:
    """
    Validate the signal emitted by Executor without rewriting it.

    A warning is diagnostic only. The function never substitutes another
    renderer, never invents payload and never changes the block.
    """
    signal = _signal_from_block(block)
    payload = _canonical_payload(block)

    if not signal:
        return {
            "valid": False,
            "reason": "missing_presentation_signal_v4",
            "version": "",
        }

    version = _s(signal.get("version"))
    kind = _s(signal.get("kind") or block.get("type")).lower()
    renderer = _s(signal.get("renderer")).lower()
    engine = _s(signal.get("engine")).lower()

    expected = SIGNAL_TO_WEB_RENDERER.get(kind)
    expected_renderer, expected_engine = expected if expected else ("", "")

    warnings = []
    if version != PRESENTATION_SIGNAL_VERSION:
        warnings.append(f"unsupported_signal_version:{version or 'missing'}")
    if expected and (renderer != expected_renderer or engine != expected_engine):
        warnings.append(
            f"engine_mismatch:{renderer}/{engine}!={expected_renderer}/{expected_engine}"
        )

    contract = signal.get("payload_contract")
    contract_payload = contract.get("payload") if isinstance(contract, dict) else None

    if kind in _payload_keys_for_alignment(kind):
        # executor v4 should preserve the full payload. Empty contract with a
        # non-empty source payload is a diagnostic signal, not a reason to drop it.
        if payload and isinstance(contract_payload, dict) and not contract_payload:
            warnings.append("empty_payload_contract")

    if signal.get("payload_unchanged") is not True:
        warnings.append("payload_unchanged_invariant_missing")

    return {
        "valid": not warnings,
        "version": version,
        "kind": kind,
        "renderer": renderer,
        "engine": engine,
        "warnings": warnings,
        "payload_present": bool(payload),
    }


def canonicalize_signal_metadata(block: dict) -> dict:
    """
    Preserve Executor v4 exactly while exposing compact Web diagnostics.

    The original signal object remains untouched. Only `presentation_audit` is
    added to the containing block.
    """
    result = dict(block)
    audit = validate_executor_signal(result)
    result["presentation_audit"] = audit
    if not audit["valid"]:
        safe_format_log(
            f"SIGNAL DIAGNOSTIC: {audit.get('kind','')} -> "
            + ", ".join(audit.get("warnings", []))
        )
    return result


def canonicalize_render_blocks(blocks: Any) -> list[dict]:
    """
    Consume Executor's single canonical stream.

    No deduplication by semantic text, no payload merging, no renderer
    inference. Executor v30 owns block composition and identity.
    """
    result = []
    for raw in _list(blocks):
        if not isinstance(raw, dict):
            continue
        result.append(canonicalize_signal_metadata(raw))
    return result


def normalize_presentation_signal(
    response: Any = None,
    semantic: dict | None = None,
    cognition: dict | None = None,
    response_decision: dict | None = None,
    renderer_payloads: Any = None,
) -> dict:
    """
    Return the exact Executor presentation_signal_v4.

    This function is intentionally NOT a presentation signal generator.
    """
    candidates = []

    def collect(source: Any) -> None:
        if not isinstance(source, dict):
            return
        for key in ("presentation", "presentation_signal", "presentation_contract"):
            candidate = source.get(key)
            if isinstance(candidate, dict):
                candidates.append(candidate)
        meta = source.get("metadata")
        if isinstance(meta, dict):
            for key in ("presentation", "presentation_signal", "presentation_contract"):
                candidate = meta.get(key)
                if isinstance(candidate, dict):
                    candidates.append(candidate)

    collect(response)
    collect(renderer_payloads)
    collect(response_decision)
    collect(semantic)
    collect(cognition)

    # Prefer the first canonical v4 signal in source order.
    for candidate in candidates:
        if _s(candidate.get("version")) == PRESENTATION_SIGNAL_VERSION:
            return candidate

    if candidates:
        return candidates[0]

    return {}


def attach_presentation_signal(
    payload: Any,
    *,
    semantic: dict | None = None,
    cognition: dict | None = None,
    response_decision: dict | None = None,
    renderer_payloads: Any = None,
):
    """
    Pass through Executor signals.

    Scene and block payloads remain authoritative. No signal synthesis occurs
    here.
    """
    if not isinstance(payload, dict):
        return payload

    result = payload

    scene_signal = normalize_presentation_signal(
        response=payload,
        semantic=semantic,
        cognition=cognition,
        response_decision=response_decision,
        renderer_payloads=renderer_payloads,
    )
    if scene_signal:
        result["presentation"] = scene_signal

    blocks = result.get("render_blocks")
    if isinstance(blocks, list):
        result["render_blocks"] = canonicalize_render_blocks(blocks)
        # The block-local signal is the actual renderer instruction.
        # The scene-level signal is retained only as a reference.
        result.setdefault(
            "presentation_stream_version",
            "quantum_presentation_stream_v2",
        )

    return result


def finalize_quantum_presentation_payload(
    payload: Any,
    *,
    semantic: dict | None = None,
    cognition: dict | None = None,
    response_decision: dict | None = None,
    renderer_payloads: Any = None,
):
    return attach_presentation_signal(
        payload,
        semantic=semantic,
        cognition=cognition,
        response_decision=response_decision,
        renderer_payloads=renderer_payloads,
    )



def presentation_future(*args, **kwargs):
    return None


RENDERER_TYPES = set(SUPPORTED_SIGNAL_KINDS) | {
    "artifact",
    "canvas",
    "svg",
    "message_block",
    "renderer",
    "layout",
    "scene",
    "visual",
}


def is_renderer_payload(value: Any) -> bool:
    if isinstance(value, dict):
        kind = _s(value.get("type") or value.get("artifact_type") or value.get("representation")).lower()
        return kind in RENDERER_TYPES or isinstance(value.get("presentation"), dict)
    if isinstance(value, list):
        return any(is_renderer_payload(item) for item in value)
    return False


def looks_like_json(text: Any) -> bool:
    if not isinstance(text, str):
        return False
    try:
        json.loads(text.strip())
        return True
    except Exception:
        return False


def is_code_payload(text: Any) -> bool:
    if not isinstance(text, str) or not text:
        return False
    return "```" in text or any(
        marker in text
        for marker in (
            "import ", "from ", "const ", "let ", "var ",
            "function ", "async function", "export default",
            "def ", "async def", "console.log(", "<div", "</div>",
        )
    )


def normalize_math_explanations(text: Any):
    if not isinstance(text, str):
        return text
    return text


def detect_primary_emoji(text: Any):
    return None


def apply_visual_enrichment(text: Any, behavior: dict | None = None):
    # Presentation v2 never invents visual semantics from prose.
    return text


def suppress_internal_status(text: Any):
    return text


def clamp(value, minimum=0.0, maximum=1.0):
    try:
        value = float(value)
    except Exception:
        return minimum
    return max(minimum, min(maximum, value))

# ---------------------------------------------------------------------
# Human-text cleanup.
# These functions are used ONLY when the value being formatted is plain
# human text, never when a scene/block/payload/signal object is present.
# ---------------------------------------------------------------------

def extract_behavior_field(cognition: dict | None = None) -> dict:
    behavior = _dict(_dict(cognition).get("behavior_state"))
    return {
        "response_density": behavior.get("response_density", 0.5),
        "initiative_level": behavior.get("initiative_level", 0.35),
        "latent_guidance": behavior.get("latent_guidance", 0.6),
        "robotic_suppression": behavior.get("robotic_suppression", 0.9),
        "humanization": behavior.get("humanization", 0.6),
    }


def suppress_internal_reasoning(text: str) -> str:
    if not isinstance(text, str):
        return text
    for item in ("возможно", "предположительно", "скорее всего", "я думаю",
                 "мне кажется", "вероятно"):
        text = text.replace(item, "")
    return text.strip()


def suppress_dialog_bloat(text: str, behavior: dict | None = None) -> str:
    if not isinstance(text, str):
        return text
    behavior = behavior or {}
    if behavior.get("response_density", 0.5) >= 0.55:
        return text
    for old in (
        "Я думаю, что",
        "Мне кажется, что",
        "Стоит отметить, что",
        "Можно сказать, что",
        "Важно понимать, что",
        "Следует отметить, что",
    ):
        text = text.replace(old, "")
    return text.strip()


def suppress_robotic_phrasing(text: str, behavior: dict | None = None) -> str:
    if not isinstance(text, str):
        return text
    behavior = behavior or {}
    if behavior.get("robotic_suppression", 0.9) < 0.5:
        return text
    for phrase in (
        "Конечно!",
        "Отличный вопрос!",
        "Давай разберемся.",
        "Я готов помочь.",
        "Чем еще помочь?",
        "Буду рад помочь.",
        "С удовольствием.",
    ):
        text = text.replace(phrase, "")
    return text.strip()


def stabilize_semantic_flow(text: str, behavior: dict | None = None) -> str:
    if not isinstance(text, str):
        return text
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text.strip()


def apply_april_final_voice(text: str, behavior: dict | None = None) -> str:
    if not isinstance(text, str):
        return text
    text = re.sub(r"\n{3,}", "\n\n", text)
    return re.sub(r"[ ]{2,}", " ", text).strip()


def beautify_response(
    text: Any,
    semantic: dict | None = None,
    cognition: dict | None = None,
    response_decision: dict | None = None,
    user_text: str = "",
):
    if not isinstance(text, str):
        return text

    behavior = extract_behavior_field(cognition)

    text = suppress_internal_reasoning(text)
    text = suppress_robotic_phrasing(text, behavior)
    text = suppress_dialog_bloat(text, behavior)
    text = stabilize_semantic_flow(text, behavior)
    text = apply_april_final_voice(text, behavior)
    return text


def should_skip_formatting(
    text: Any,
    semantic: dict | None = None,
    response_decision: dict | None = None,
) -> bool:
    if isinstance(text, (dict, list)):
        return True
    if is_machine_payload(text):
        return True
    if is_scene_contract(text):
        return True
    return not isinstance(text, str) or not text


def normalize_text_payload(value: Any):
    if isinstance(value, (dict, list)):
        return value
    if value is None:
        return ""
    return str(value)


def format_response_presentation(
    text: Any = "",
    response: Any = "",
    semantic: dict | None = None,
    cognition: dict | None = None,
    response_decision: dict | None = None,
    user_text: str = "",
    visual_reference: Any = None,
):
    """
    Final presentation boundary.

    Machine/SceneContract values stay machine values. Plain text alone is
    formatted for human readability.
    """
    final_value = response if response not in ("", None) else text
    presentation_enter(final_value, semantic)

    if isinstance(final_value, dict):
        if "render_blocks" in final_value:
            result = attach_presentation_signal(
                final_value,
                semantic=semantic,
                cognition=cognition,
                response_decision=response_decision,
                renderer_payloads=visual_reference,
            )
            presentation_exit(result)
            return result

        if final_value.get("presentation_mode") == "scene_pipeline":
            machine = final_value.get("machine_response")
            if isinstance(machine, dict):
                result = attach_presentation_signal(
                    machine,
                    semantic=semantic,
                    cognition=cognition,
                    response_decision=response_decision,
                    renderer_payloads=visual_reference,
                )
                presentation_exit(result)
                return result

        presentation_exit(final_value)
        return final_value

    if should_skip_formatting(final_value, semantic, response_decision):
        presentation_exit(final_value)
        return final_value

    result = beautify_response(
        normalize_text_payload(final_value),
        semantic=semantic,
        cognition=cognition,
        response_decision=response_decision,
        user_text=user_text,
    )
    presentation_exit(result)
    return result


def preserve_scene_pipeline(payload: Any):
    return payload


def build_scene_contract_legacy(machine_response: Any):
    """
    Compatibility read-only view.

    Canonical SceneContract construction remains in Executor/C_ARTIFACT_CONTRACT.
    This helper never claims ownership of that contract.
    """
    return machine_response


def finalize_presentation_payload(payload: Any):
    """
    Compatibility entry point.

    SceneContract ownership remains with Executor. This function only ensures
    block-local Executor signals are preserved.
    """
    if isinstance(payload, dict) and isinstance(payload.get("render_blocks"), list):
        return attach_presentation_signal(payload)
    if (
        isinstance(payload, dict)
        and payload.get("presentation_mode") == "scene_pipeline"
        and isinstance(payload.get("machine_response"), dict)
    ):
        return attach_presentation_signal(payload["machine_response"])
    return payload


# Explicit aliases expected by older callers.
presentation_engine = PRESENTATION_ENGINE_VERSION
PRESENTATION_ENGINE = PRESENTATION_ENGINE_VERSION
INPUT_MACHINE_CHANNEL = {
    "source": "executor",
    "type": "presentation_machine_input",
    "isolated": True,
}
OUTPUT_HUMAN_CHANNEL = {
    "target": "botru_web_output",
    "type": "human_response_output",
    "isolated": True,
}
