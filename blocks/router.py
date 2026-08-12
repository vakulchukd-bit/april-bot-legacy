"""
APRIL WEB ROUTER — QUANTUM EVIDENCE V1

Role:
    Lightweight orchestration evidence layer.

The router observes already-produced signals and packages them for the
Quantum Processor. It does not own the final route.

Single route:
    USER -> SEMANTIC/COGNITION -> QUANTUM PROCESSOR ->
    EXECUTION/ARTIFACT -> SCENE CONTRACT -> APRIL WEB

The router deliberately does NOT:
    - call OpenAI/Provider;
    - select a final room;
    - lock a renderer;
    - trigger generation;
    - execute tools;
    - create fallback/parallel routes;
    - contain Telegram dispatch logic.

Compatibility:
    route_request(text, ctx) remains async and updates ctx["semantic"].
    Legacy helper names are preserved where practical.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional


APRIL_FILE_ID = "APRIL_WEB_ROUTER_QUANTUM_V1"
DECISION_OWNER = "QUANTUM_PROCESSOR"

ROUTER_MACHINE_CHANNEL = {
    "type": "semantic_router",
    "mode": "evidence",
    "authority": "none",
    "web_safe": True,
    "renderer_first": True,
    "continuity_safe": True,
    "decision_owner": DECISION_OWNER,
}

ROUTER_PATCH_LOG = []
MAX_ROUTER_LOGS = 120


def safe_router_log(msg: Any) -> None:
    try:
        ROUTER_PATCH_LOG.append(str(msg))
        if len(ROUTER_PATCH_LOG) > MAX_ROUTER_LOGS:
            del ROUTER_PATCH_LOG[:-MAX_ROUTER_LOGS]
    except Exception:
        pass


def normalize(text: Any) -> str:
    return str(text or "").lower().strip()


def contains_any(text: Any, words: Iterable[str]) -> bool:
    value = normalize(text)
    return any(word in value for word in words)


def build_router_contract() -> Dict[str, Any]:
    return {
        "router_type": "quantum_evidence_stabilizer",
        "execution_authority": False,
        "renderer_authority": False,
        "generation_authority": False,
        "provider_authority": False,
        "semantic_mutation_minimized": True,
        "continuity_first": True,
        "web_oriented": True,
        "decision_owner": DECISION_OWNER,
        "provider_calls": 0,
        "parallel_route": False,
    }


ROUTER_CONTRACT = build_router_contract()


def set_router_hint(semantic: Dict[str, Any], hint: str) -> str:
    """
    Compatibility field only.

    A hint is descriptive evidence; it is NOT a command to another room.
    """
    semantic["router_suggestion"] = hint
    semantic["router_last_hint"] = hint
    return hint


def apply_router_stabilization(semantic: Dict[str, Any]) -> Dict[str, Any]:
    semantic.update({
        "router_is_soft": True,
        "router_authority": "supportive",
        "router_renderer_aware": True,
        "router_continuity_first": True,
        "router_renderer_first": True,
        "router_anti_escalation": True,
        "router_anti_recursion": True,
        "router_preserve_scene": True,
        "router_preserve_flow": True,
        "router_generation_requires_intent": True,
        "router_lightweight_priority": True,
        "router_hidden_generation_blocked": True,
        "router_decision_owner": DECISION_OWNER,
        "router_provider_calls": 0,
        "router_parallel_route": False,
    })
    return semantic


CONTINUATION_WORDS = (
    "да", "ага", "ок", "окей", "давай", "продолжай", "ещё", "еще",
    "вот", "примерно", "ближе", "уже лучше", "дальше", "снова",
    "поехали", "оставь", "так", "в таком стиле",
)

VISUAL_REFERENCE_WORDS = (
    "это", "этот", "эта", "там", "на картинке", "на фото",
    "цвет", "слева", "справа", "фон", "стиль", "атмосфера",
    "форма", "размер",
)

SCIENCE_WORDS = (
    "реши", "уравнение", "график", "функция", "sin(", "cos(",
    "tan(", "y=", "формула",
)

RENDER_WORDS = (
    "таблица", "формула", "diagram", "диаграмма", "схема",
    "layout", "grid", "renderer", "пространство", "scene",
    "композиция", "canvas", "блок", "график",
)

GENERATION_WORDS = (
    "создай изображение", "сгенерируй изображение",
    "нарисуй картинку", "создай картинку", "draw image",
    "generate image", "создай арт", "сделай арт",
)

EDIT_WORDS = (
    "измени", "добавь", "убери", "замени", "сделай ярче",
    "сделай темнее", "поменяй", "исправь",
)

WEB_WORDS = (
    "погода", "новости", "курс валют", "маршрут", "карта",
    "где находится", "что происходит",
)


def is_soft_continuation(text: str) -> bool:
    t = normalize(text)
    if t in CONTINUATION_WORDS:
        return True
    return len(t) <= 28 and contains_any(t, CONTINUATION_WORDS)


def detect_visual_continuation(text: str, state: Dict[str, Any]) -> bool:
    if not state.get("active_visual_scene"):
        return False
    t = normalize(text)
    if contains_any(t, VISUAL_REFERENCE_WORDS):
        return True
    return len(t) <= 48


def detect_intent_local(text: str) -> Optional[str]:
    """
    Descriptive local signal only. It never owns routing.
    """
    t = normalize(text)
    if contains_any(t, SCIENCE_WORDS):
        return "science"
    if contains_any(t, RENDER_WORDS):
        return "renderer_space"
    if contains_any(t, GENERATION_WORDS):
        return "image_generate"
    if contains_any(t, EDIT_WORDS):
        return "image_edit"
    if contains_any(t, WEB_WORDS):
        return "web"
    return None


def user_waiting_execution(semantic: Dict[str, Any], cognition: Dict[str, Any]) -> bool:
    return bool(
        semantic.get("should_execute")
        or cognition.get("prefer_execution")
        or cognition.get("wants_result", 0.0) >= 0.72
    )


def renderer_priority_active(
    semantic: Dict[str, Any],
    cognition: Dict[str, Any],
) -> bool:
    return bool(
        semantic.get("prefer_renderer")
        or semantic.get("render_intent")
        or cognition.get("prefer_renderer")
    )


def _add_signal(
    evidence: list,
    name: str,
    confidence: float,
    source: str,
    **data: Any,
) -> None:
    evidence.append({
        "signal": name,
        "confidence": max(0.0, min(1.0, confidence)),
        "source": source,
        **data,
    })


def _build_quantum_evidence(
    text: str,
    ctx: Dict[str, Any],
    semantic: Dict[str, Any],
    cognition: Dict[str, Any],
    reasoning: Dict[str, Any],
    response_decision: Dict[str, Any],
    visual_reference: Dict[str, Any],
) -> Dict[str, Any]:
    state = ctx.get("state") or {}
    active_flow = state.get("active_flow") or {}
    evidence = []

    if renderer_priority_active(semantic, cognition):
        _add_signal(evidence, "renderer_candidate", 0.88, "semantic_cognition")

    if semantic.get("should_execute") or cognition.get("prefer_execution"):
        _add_signal(evidence, "execution_candidate", 0.88, "semantic_cognition")

    continuation_target = reasoning.get("continuation_target")
    if continuation_target:
        _add_signal(
            evidence,
            "continuation",
            0.86,
            "reasoning",
            target=continuation_target,
        )

    if is_soft_continuation(text):
        _add_signal(evidence, "soft_continuation", 0.78, "router_local")

    if detect_visual_continuation(text, state):
        _add_signal(
            evidence,
            "visual_continuation",
            0.82,
            "visual_scene",
            active_scene=True,
        )

    local = detect_intent_local(text)
    if local:
        _add_signal(evidence, "local_intent_candidate", 0.80, "router_local", intent=local)

    if cognition.get("exploration_mode"):
        _add_signal(evidence, "exploration", 0.78, "cognition")

    if visual_reference.get("lightweight_mode"):
        _add_signal(evidence, "lightweight_visual", 0.80, "visual_reference")

    if response_decision.get("should_offer_reference"):
        _add_signal(evidence, "reference_offer", 0.72, "response_decision")

    if cognition.get("internet_context_needed"):
        _add_signal(evidence, "web_context", 0.86, "cognition")

    if active_flow:
        _add_signal(
            evidence,
            "active_flow",
            0.78,
            "session_state",
            flow_type=active_flow.get("type"),
        )

    # Do not choose a final route here. The strongest signal is only a
    # compatibility hint for older consumers.
    strongest = max(evidence, key=lambda item: item["confidence"], default=None)

    return {
        "current_request": str(text or ""),
        "signals": evidence,
        "strongest_hint": strongest["signal"] if strongest else "text",
        "strongest_confidence": strongest["confidence"] if strongest else 0.40,
        "active_flow": active_flow,
        "visual_scene_active": bool(state.get("active_visual_scene")),
        "decision_owner": DECISION_OWNER,
        "provider_calls": 0,
        "parallel_route": False,
        "route_selection": "delegated",
        "room_selection": "delegated",
        "renderer_selection": "delegated",
        "execution_selection": "delegated",
    }


async def route_request(text: str, ctx: Optional[Dict[str, Any]]) -> str:
    """
    Aggregate router evidence without becoming a hard router.

    Compatibility:
        Returns a string because existing callers may expect it.
        The returned string is only the strongest descriptive hint.
        The canonical decision remains in ctx["semantic"]["quantum_router_evidence"].
    """
    try:
        ctx = ctx if isinstance(ctx, dict) else {}
        semantic = ctx.setdefault("semantic", {})
        cognition = ctx.get("cognition") or {}
        reasoning = ctx.get("reasoning") or {}
        response_decision = ctx.get("response_decision") or {}
        visual_reference = ctx.get("visual_reference") or {}
        state = ctx.get("state") or {}

        apply_router_stabilization(semantic)

        evidence = _build_quantum_evidence(
            text=text,
            ctx=ctx,
            semantic=semantic,
            cognition=cognition,
            reasoning=reasoning,
            response_decision=response_decision,
            visual_reference=visual_reference,
        )

        semantic["quantum_router_evidence"] = evidence
        semantic["router_candidate_signals"] = evidence["signals"]
        semantic["router_final_decision_delegated"] = True
        semantic["router_provider_calls"] = 0
        semantic["router_parallel_route"] = False

        hint = evidence["strongest_hint"]
        # Compatibility hint mapping; no execution lock is created.
        hint_map = {
            "renderer_candidate": "renderer_space",
            "execution_candidate": "execution_candidate",
            "continuation": "continuation",
            "soft_continuation": "continuation",
            "visual_continuation": "visual_continuation",
            "local_intent_candidate": "semantic_candidate",
            "exploration": "exploration",
            "lightweight_visual": "lightweight_visual",
            "reference_offer": "reference",
            "web_context": "web_candidate",
            "active_flow": "active_flow",
        }
        compatibility_hint = hint_map.get(hint, "text")

        set_router_hint(semantic, compatibility_hint)
        safe_router_log(
            f"EVIDENCE: {hint} / {evidence['strongest_confidence']:.2f}"
        )

        return compatibility_hint

    except Exception as exc:
        safe_router_log(f"ROUTER EVIDENCE ERROR: {exc}")
        # Safe compatibility value only; no alternate route is created.
        return "text"
