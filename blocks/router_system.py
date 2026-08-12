"""
APRIL LEGACY ROUTER SYSTEM — QUANTUM EVIDENCE V1

Role:
    Compatibility evidence layer only.

The original router contained many sequential action overrides:
    exploration -> guide -> visual -> image -> diagram -> question -> continue.

That structure could silently replace one signal with another.

Quantum version:
    - collects all applicable signals;
    - preserves their confidence and provenance;
    - never owns final routing;
    - never invokes Provider/OpenAI;
    - never triggers generation;
    - never selects a room or renderer;
    - keeps decide_action() for compatibility.

Final authority:
    QUANTUM_PROCESSOR

Single route:
    USER -> EVIDENCE -> QUANTUM PROCESSOR -> EXECUTION/ARTIFACT ->
    SCENE CONTRACT -> APRIL WEB
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


APRIL_FILE_ID = "APRIL_LEGACY_ROUTER_QUANTUM_V1"
DECISION_OWNER = "QUANTUM_PROCESSOR"

ROUTER_MACHINE_CHANNEL = {
    "type": "legacy_compatibility_evidence",
    "mode": "supportive",
    "authority": "none",
    "continuity_safe": True,
    "web_safe": True,
    "renderer_first": True,
    "decision_owner": DECISION_OWNER,
    "provider_calls": 0,
    "parallel_route": False,
}


def build_router_contract() -> Dict[str, Any]:
    return {
        "legacy_compatible": True,
        "execution_authority": False,
        "generation_authority": False,
        "renderer_authority": False,
        "hard_trigger_behavior": False,
        "continuity_first": True,
        "trajectory_safe": True,
        "web_oriented": True,
        "decision_owner": DECISION_OWNER,
        "provider_calls": 0,
        "parallel_route": False,
    }


ROUTER_CONTRACT = build_router_contract()

ROUTER_PATCH_LOG: List[str] = []
MAX_ROUTER_LOGS = 100


def safe_router_log(msg: Any) -> None:
    try:
        ROUTER_PATCH_LOG.append(str(msg))
        if len(ROUTER_PATCH_LOG) > MAX_ROUTER_LOGS:
            del ROUTER_PATCH_LOG[:-MAX_ROUTER_LOGS]
    except Exception:
        pass


safe_router_log("LEGACY COMPATIBILITY EVIDENCE INITIALIZED")


def normalize(text: Any) -> str:
    return str(text or "").lower().strip()


def contains_any(text: Any, words: Iterable[str]) -> bool:
    value = normalize(text)
    return any(word in value for word in words)


def has_negation(text: str) -> bool:
    return contains_any(text, (
        "не надо",
        "не делай",
        "не нужно",
        "не хочу",
        "не генерируй",
        "не создавай",
    ))


def is_exploration(text: str) -> bool:
    return contains_any(text, (
        "примерно",
        "может",
        "наверное",
        "идея",
        "атмосфера",
        "посмотрим",
        "подумаем",
        "направление",
        "что-то",
        "как будто",
        "не уверен",
        "вариант",
        "настроение",
    ))


def user_leads_direction(text: str) -> bool:
    return contains_any(text, (
        "вот",
        "в таком стиле",
        "ближе",
        "примерно так",
        "вот это",
        "атмосфера",
        "идея",
    ))


def wants_visual_reference(text: str) -> bool:
    return contains_any(text, (
        "референс",
        "пример",
        "атмосфера",
        "визуально",
        "идея",
        "примерно",
        "стиль",
    ))


def wants_real_generation(text: str) -> bool:
    return contains_any(text, (
        "сгенерируй",
        "создай изображение",
        "нарисуй",
        "сделай картинку",
        "покажи изображение",
    ))


def is_short_continuation(text: str) -> bool:
    t = normalize(text)
    if len(t.split()) > 3:
        return False
    return contains_any(t, (
        "да",
        "ага",
        "вот",
        "не то",
        "ближе",
        "примерно",
        "уже лучше",
        "не знаю",
        "ну вот",
    ))


def build_result() -> Dict[str, Any]:
    """
    Compatibility packet.

    `action` is retained for callers that still expect it, but it is only
    the strongest descriptive hint. `quantum_evidence` contains the complete
    signal set and the Quantum Processor owns final arbitration.
    """
    return {
        "action": "chat",
        "confidence": 0.5,

        "is_soft_decision": True,
        "trajectory_safe": True,
        "continuity_safe": True,

        "exploration_mode": False,
        "visual_guidance": False,
        "generation_allowed": False,
        "continuation_detected": False,

        "legacy_router": True,
        "hard_authority": False,
        "executor_override_allowed": True,
        "renderer_first": True,
        "web_safe": True,

        "decision_owner": DECISION_OWNER,
        "provider_calls": 0,
        "parallel_route": False,

        "candidate_signals": [],
        "quantum_evidence": {},
    }


def _add_signal(
    result: Dict[str, Any],
    name: str,
    confidence: float,
    source: str,
    **metadata: Any,
) -> None:
    result["candidate_signals"].append({
        "signal": name,
        "confidence": max(0.0, min(1.0, float(confidence))),
        "source": source,
        **metadata,
    })


def _strongest_signal(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    signals = result.get("candidate_signals") or []
    if not signals:
        return None
    return max(signals, key=lambda item: item.get("confidence", 0.0))


def decide_action(
    text: str,
    history: Optional[list],
) -> Dict[str, Any]:
    """
    Collect legacy compatibility evidence.

    Important:
        No early return is used while collecting signals.
        A request can simultaneously be exploratory, visual, generative,
        diagram-related and conversational. All evidence survives.

        The returned `action` is only a compatibility hint.
    """
    t = normalize(text)
    result = build_result()

    safe_router_log(f"INPUT: {t[:80]}")

    # -------------------------------------------------
    # NEGATION — strongest safety evidence
    # -------------------------------------------------
    if has_negation(t):
        _add_signal(
            result,
            "negation",
            0.94,
            "legacy_local",
            suppress_generation=True,
        )

    # -------------------------------------------------
    # CONTINUATION
    # -------------------------------------------------
    if is_short_continuation(t):
        result["continuation_detected"] = True
        _add_signal(
            result,
            "continuation",
            0.85,
            "legacy_local",
        )

    # -------------------------------------------------
    # EXPLORATION
    # -------------------------------------------------
    if is_exploration(t):
        result["exploration_mode"] = True
        _add_signal(
            result,
            "exploration",
            0.76,
            "legacy_local",
        )

    # -------------------------------------------------
    # USER DIRECTION
    # -------------------------------------------------
    if user_leads_direction(t):
        result["exploration_mode"] = True
        _add_signal(
            result,
            "user_direction",
            0.80,
            "legacy_local",
        )

    # -------------------------------------------------
    # VISUAL GUIDANCE
    # -------------------------------------------------
    if wants_visual_reference(t):
        result["visual_guidance"] = True
        _add_signal(
            result,
            "visual_reference",
            0.76,
            "legacy_local",
        )

    # -------------------------------------------------
    # IMAGE GENERATION
    # -------------------------------------------------
    if wants_real_generation(t):
        result["generation_allowed"] = not has_negation(t)
        _add_signal(
            result,
            "image_generation_candidate",
            0.90,
            "legacy_local",
            blocked_by_negation=has_negation(t),
        )

    # -------------------------------------------------
    # DIAGRAM
    # -------------------------------------------------
    if contains_any(t, (
        "чертеж",
        "чертёж",
        "схема",
        "диаграмма",
    )):
        _add_signal(
            result,
            "diagram_candidate",
            0.80,
            "legacy_local",
        )

    # -------------------------------------------------
    # QUESTION
    # -------------------------------------------------
    if "?" in t or contains_any(t, ("что", "почему", "как", "зачем")):
        _add_signal(
            result,
            "question",
            0.70,
            "legacy_local",
        )

    # -------------------------------------------------
    # SHORT INPUT
    # -------------------------------------------------
    if len(t.split()) <= 2 and t:
        _add_signal(
            result,
            "short_input",
            0.55,
            "legacy_local",
        )

    # -------------------------------------------------
    # HISTORY / TRAJECTORY AS WEAK CONTEXT
    # -------------------------------------------------
    if history:
        _add_signal(
            result,
            "history_available",
            0.40,
            "session_context",
            history_size=len(history),
        )

    # -------------------------------------------------
    # FINAL COMPATIBILITY HINT
    # -------------------------------------------------
    strongest = _strongest_signal(result)

    if strongest:
        signal = strongest["signal"]

        compatibility_map = {
            "negation": "chat",
            "continuation": "continue",
            "exploration": "guide",
            "user_direction": "guide",
            "visual_reference": "reference",
            "image_generation_candidate": "image",
            "diagram_candidate": "diagram",
            "question": "chat",
            "short_input": "continue",
            "history_available": "chat",
        }

        result["action"] = compatibility_map.get(signal, "chat")
        result["confidence"] = strongest["confidence"]

    # Safety normalization:
    # negation can suppress generation without deleting the generation
    # evidence itself.
    if has_negation(t):
        result["generation_allowed"] = False

    result["hard_authority"] = False
    result["executor_override_allowed"] = True
    result["trajectory_safe"] = True
    result["continuity_safe"] = True

    result["quantum_evidence"] = {
        "current_request": text,
        "signals": list(result["candidate_signals"]),
        "history_available": bool(history),
        "decision_owner": DECISION_OWNER,
        "final_route": "delegated",
        "final_room": "delegated",
        "final_renderer": "delegated",
        "final_execution": "delegated",
        "provider_calls": 0,
        "parallel_route": False,
    }

    safe_router_log(
        f"EVIDENCE: {len(result['candidate_signals'])} signals / "
        f"hint={result['action']}"
    )

    return result
