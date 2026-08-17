"""
APRIL — INTENT AI / QUANTUM MULTI-SIGNAL V1

Role:
    Multimodal intent evidence analyzer.

Architecture:
    Intent AI observes.
    Cognition/Semantic layers correlate.
    Quantum Processor arbitrates.
    Executor executes.
    C-Artifact transports.
    April Web renders.

This module does NOT:
    - choose the final room;
    - choose the final renderer;
    - choose the provider;
    - execute tools;
    - create a second route;
    - make an OpenAI call as a normal intent path.

Important:
    OpenAI is deliberately removed from the Intent layer. The current
    request should reach the existing Provider path once, under the
    Quantum Processor's control. Intent AI is therefore a local evidence
    layer, not another paid reasoning request.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Iterable, Optional


APRIL_FILE_ID = "APRIL_INTENT_AI_SYSTEM_QUANTUM_V1"
DECISION_OWNER = "QUANTUM_PROCESSOR"

INPUT_MACHINE_CHANNEL = {
    "source": "executor_input_pipeline",
    "type": "intent_signal_request",
    "isolated": True,
}

OUTPUT_MACHINE_CHANNEL = {
    "target": "executor_semantic_pipeline",
    "type": "intent_signal_payload",
    "isolated": True,
}

INTENT_AI_LOGS = []
MAX_INTENT_AI_LOGS = 100


def log_intent_event(event: str, payload: Optional[Dict[str, Any]] = None) -> None:
    try:
        INTENT_AI_LOGS.append({
            "timestamp": time.time(),
            "event": event,
            "payload": payload or {},
            "file_id": APRIL_FILE_ID,
            "machine_only": True,
        })
        if len(INTENT_AI_LOGS) > MAX_INTENT_AI_LOGS:
            del INTENT_AI_LOGS[:-MAX_INTENT_AI_LOGS]
    except Exception:
        pass


def normalize(text: Any) -> str:
    return str(text or "").lower().strip()


def contains_any(text: Any, words: Iterable[str]) -> bool:
    value = normalize(text)
    return any(word in value for word in words)


CONTINUATION_WORDS = (
    "да", "ага", "вот", "примерно", "ближе", "уже лучше",
    "чуть темнее", "чуть светлее", "сделай темнее", "сделай ярче",
    "не то", "переделай", "продолжай", "дальше", "еще", "ещё",
    "оставь", "в таком стиле", "продолжим", "вернемся", "вернёмся",
)

SCIENCE_WORDS = (
    "график", "уравнение", "реши", "sin(", "cos(", "tan(",
    "y=", "формула", "функция", "парабола",
)

GENERATE_WORDS = (
    "сгенерируй изображение", "создай изображение",
    "нарисуй картинку", "создай картинку", "generate image",
)

EDIT_WORDS = (
    "измени", "добавь", "убери", "замени", "сделай ярче", "сделай темнее",
)

IMAGE_ANALYSIS_WORDS = (
    "что на картинке", "что изображено", "что это",
    "опиши изображение", "что видишь",
)

WEB_WORDS = (
    "погода", "новости", "курс валют", "маршрут", "карта",
    "где находится", "что происходит",
)

EXPLORATION_WORDS = (
    "атмосфера", "идея", "референс", "пример", "концепт",
    "вариант", "примерно", "в таком стиле",
)


def build_signal_response(
    primary_intent: str = "text",
    confidence: float = 0.5,
    source: str = "local",
    signals: Optional[Dict[str, Any]] = None,
    capability_hints: Optional[list] = None,
    continuation: bool = False,
    renderer: bool = False,
    visual: bool = False,
    execution: bool = False,
    explanation: bool = False,
    exploration: bool = False,
    web: bool = False,
) -> Dict[str, Any]:
    """
    Build one machine evidence packet.

    `primary_intent` is only the strongest descriptive signal. It is not a
    final route decision.
    """
    payload = {
        "intent": primary_intent,
        "primary_intent": primary_intent,
        "confidence": max(0.0, min(1.0, float(confidence))),
        "source": source,
        "signals": {
            "continuation": continuation,
            "renderer": renderer,
            "visual": visual,
            "execution": execution,
            "explanation": explanation,
            "exploration": exploration,
            "web": web,
            **(signals or {}),
        },
        "capability_hints": list(capability_hints or []),
        "orchestration_ready": True,
        "renderer_first_safe": True,
        "provider_aware": True,
        "single_route_forbidden": False,
        "machine_only": True,
        "semantic_signal": True,
        "decision_owner": DECISION_OWNER,
        "provider_calls": 0,
        "route_selection": "delegated",
        "renderer_selection": "delegated",
        "room_selection": "delegated",
        "execution_selection": "delegated",
    }
    log_intent_event("signal_response_created", {
        "primary_intent": primary_intent,
        "source": source,
        "confidence": payload["confidence"],
    })
    return payload


def _continuation_signal(text: str, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if normalize(text) not in CONTINUATION_WORDS:
        return None

    flow = state.get("active_flow") or {}
    flow_type = flow.get("type") if isinstance(flow, dict) else None
    visual = bool(state.get("active_visual_scene"))

    hints = ["continuation", "trajectory"]
    if flow_type:
        hints.append(str(flow_type))

    return build_signal_response(
        primary_intent="continuation",
        confidence=0.86 if flow_type else 0.66,
        source="local_continuation",
        continuation=True,
        renderer=flow_type in {"renderer_space", "math", "scene"},
        visual=visual or flow_type in {
            "image_generate", "image_edit", "image", "scene"
        },
        capability_hints=hints,
    )


def _local_candidates(text: str, state: Dict[str, Any]) -> list[Dict[str, Any]]:
    t = normalize(text)
    candidates = []

    if contains_any(t, SCIENCE_WORDS):
        candidates.append({
            "intent": "science",
            "confidence": 0.90,
            "signals": {
                "renderer": True,
                "execution": True,
                "explanation": True,
            },
            "capabilities": ["science", "renderer_space", "math", "formula_rendering"],
        })

    if contains_any(t, GENERATE_WORDS):
        candidates.append({
            "intent": "generate_image",
            "confidence": 0.92,
            "signals": {"visual": True, "execution": True},
            "capabilities": ["image_generation"],
        })

    if contains_any(t, EDIT_WORDS) and (
        state.get("image_context") or state.get("active_flow")
    ):
        candidates.append({
            "intent": "edit_image",
            "confidence": 0.88,
            "signals": {"continuation": True, "visual": True},
            "capabilities": ["image_edit", "continuation"],
        })

    if contains_any(t, IMAGE_ANALYSIS_WORDS) and (
        state.get("image_context") or state.get("active_visual_scene")
    ):
        candidates.append({
            "intent": "analyze_image",
            "confidence": 0.90,
            "signals": {"visual": True, "explanation": True},
            "capabilities": ["image_analysis", "visual_guidance"],
        })

    if contains_any(t, WEB_WORDS):
        candidates.append({
            "intent": "web",
            "confidence": 0.88,
            "signals": {"web": True, "explanation": True},
            "capabilities": ["web", "guidance"],
        })

    if contains_any(t, EXPLORATION_WORDS):
        candidates.append({
            "intent": "exploration",
            "confidence": 0.76,
            "signals": {"visual": True, "exploration": True, "explanation": True},
            "capabilities": ["visual_guidance", "renderer_space", "conversation"],
        })

    return candidates


def detect_intent_local(text: str, state: Optional[dict] = None) -> Optional[Dict[str, Any]]:
    """
    Local multi-signal detection.

    It returns the strongest descriptive signal plus ALL local candidates.
    No early return is used for competing modalities.
    """
    state = state if isinstance(state, dict) else {}
    t = normalize(text)

    log_intent_event("local_detection_started", {"text": t[:120]})

    continuation = _continuation_signal(t, state)
    candidates = _local_candidates(t, state)

    if continuation:
        candidates.append({
            "intent": "continuation",
            "confidence": continuation["confidence"],
            "signals": continuation["signals"],
            "capabilities": continuation["capability_hints"],
        })

    if not candidates:
        return None

    strongest = max(candidates, key=lambda item: item["confidence"])
    merged_signals: Dict[str, Any] = {}
    merged_caps = []

    for candidate in candidates:
        merged_signals.update(candidate.get("signals", {}))
        for capability in candidate.get("capabilities", []):
            if capability not in merged_caps:
                merged_caps.append(capability)

    result = build_signal_response(
        primary_intent=strongest["intent"],
        confidence=strongest["confidence"],
        source="local_multi_signal",
        signals={
            **merged_signals,
            "candidate_count": len(candidates),
            "candidate_signals": candidates,
        },
        capability_hints=merged_caps,
        continuation=bool(merged_signals.get("continuation")),
        renderer=bool(merged_signals.get("renderer")),
        visual=bool(merged_signals.get("visual")),
        execution=bool(merged_signals.get("execution")),
        explanation=bool(merged_signals.get("explanation")),
        exploration=bool(merged_signals.get("exploration")),
        web=bool(merged_signals.get("web")),
    )

    result["quantum_evidence"] = {
        "current_request": t,
        "candidates": candidates,
        "active_flow": state.get("active_flow") or {},
        "active_visual_scene": state.get("active_visual_scene") or {},
        "decision_owner": DECISION_OWNER,
    }

    return result


async def detect_intent_ai(
    text: str,
    state: Optional[dict] = None,
) -> Dict[str, Any]:
    """
    Compatibility entrypoint.

    Deliberately local:
        the old implementation made a second OpenAI request through gpt-4o-mini
        when local detection failed. That created a second reasoning call before
        the real Provider path. Quantum architecture removes that duplication.

    The Quantum Processor owns provider reasoning.
    """
    state = state if isinstance(state, dict) else {}
    t = normalize(text)

    log_intent_event("intent_ai_started", {"text": t[:120]})

    local = detect_intent_local(t, state)
    if local:
        local["source"] = "local_multi_signal"
        local["provider_calls"] = 0
        local["decision_owner"] = DECISION_OWNER
        log_intent_event("local_multi_signal_returned")
        return local

    if len(t) <= 15:
        # Greetings and short social turns are authoritative independent turns.
        # Existing active_flow is preserved in memory, but cannot convert a new
        # short request into continuation without an explicit reference cue.
        explicit_reference = normalize(t) in {"продолжай", "дальше", "продолжи", "ещё", "еще"}
        active_flow = state.get("active_flow") if explicit_reference else None
        result = build_signal_response(
            primary_intent="continuation" if active_flow else "text",
            confidence=0.66 if active_flow else 0.50,
            source="short_safe",
            continuation=bool(active_flow),
            capability_hints=["continuation"] if active_flow else ["conversation"],
        )
        result["quantum_evidence"] = {
            "current_request": t,
            "short_input": True,
            "active_flow": active_flow or {},
        }
        return result

    result = build_signal_response(
        primary_intent="text",
        confidence=0.40,
        source="local_neutral",
        capability_hints=["conversation", "semantic_analysis"],
    )
    result["quantum_evidence"] = {
        "current_request": t,
        "local_candidates": [],
        "needs_quantum_arbitration": True,
        "decision_owner": DECISION_OWNER,
    }
    log_intent_event("neutral_evidence_returned")
    return result
