"""
APRIL — INTENT SYSTEM / QUANTUM EVIDENCE V1

Role:
    Lightweight semantic evidence layer.

This layer observes the request and emits signals.
It does NOT own the final route, room, provider, renderer, or execution decision.

Decision owner:
    QUANTUM_PROCESSOR

Single route:
    USER -> INTENT EVIDENCE -> SEMANTIC/COGNITION ->
    QUANTUM PROCESSOR -> EXECUTION/ARTIFACT -> SCENE CONTRACT -> APRIL WEB
"""

from __future__ import annotations

import time
from typing import Any, Dict, Iterable, Optional


APRIL_FILE_ID = "APRIL_INTENT_SYSTEM_QUANTUM_V1"
DECISION_OWNER = "QUANTUM_PROCESSOR"

INPUT_MACHINE_CHANNEL = {
    "source": "executor_input_pipeline",
    "type": "intent_signal_input",
    "isolated": True,
}

OUTPUT_MACHINE_CHANNEL = {
    "target": "semantic_orchestration_pipeline",
    "type": "intent_signal_output",
    "isolated": True,
}

PATCH_LOG = []
MAX_PATCH_LOGS = 120


def safe_patch_log(msg: Any) -> None:
    """Machine telemetry only; never influences intent."""
    try:
        PATCH_LOG.append({
            "timestamp": time.time(),
            "message": str(msg),
            "file_id": APRIL_FILE_ID,
            "machine_only": True,
        })
        if len(PATCH_LOG) > MAX_PATCH_LOGS:
            del PATCH_LOG[:-MAX_PATCH_LOGS]
    except Exception:
        pass


def patch_intent_detect(text: str) -> str:
    safe_patch_log(f"INTENT EVIDENCE: {text[:60]}")
    return text


def patch_intent_future(*args: Any, **kwargs: Any) -> None:
    return None


def normalize(text: str) -> str:
    return str(text or "").lower().strip()


def contains_any(text: str, words: Iterable[str]) -> bool:
    value = normalize(text)
    return any(word in value for word in words)


CONTINUATION_WORDS = (
    "да", "ага", "ок", "окей", "давай", "вот", "примерно",
    "ближе", "уже лучше", "не то", "чуть темнее", "чуть ярче",
    "продолжай", "с этого", "поехали", "дальше", "теперь",
    "еще", "ещё", "в таком стиле", "оставь", "вот это",
    "ближе к этому", "продолжим", "вернемся", "вернёмся",
)

QUESTION_WORDS = (
    "как", "что", "почему", "зачем", "умеешь", "можешь",
    "где", "когда", "сколько", "какой", "какая", "какие",
)

EDIT_WORDS = (
    "добавь", "измени", "убери", "замени", "поменяй",
    "улучши", "подправь", "ярче", "темнее", "переделай",
    "исправь", "сделай темнее", "сделай ярче",
)

GENERATION_WORDS = (
    "создай изображение", "сгенерируй изображение",
    "нарисуй картинку", "создай картинку",
    "draw image", "generate image", "ultra realistic",
    "4k render", "cinematic render", "photorealistic",
    "realistic render",
)

LIGHT_VISUAL_WORDS = (
    "пример", "референс", "концепт", "идея", "вариант",
    "атмосфера", "примерно", "визуально", "как выглядит",
    "схема", "layout", "структура", "расположение",
)

RENDER_WORDS = (
    "график", "таблица", "формула", "diagram", "диаграмма",
    "схема", "layout", "структура", "grid", "line", "point",
    "arrow", "renderer", "пространство", "scene", "композиция",
    "canvas",
)

SPATIAL_WORDS = (
    "слева", "справа", "сверху", "снизу", "по центру",
    "размести", "поставь", "расположи", "между", "рядом",
)

WEB_WORDS = (
    "погода", "новости", "курс валют", "что происходит",
    "где находится", "карта", "маршрут", "рейс", "сейчас в",
    "такси", "отель", "навигация", "локация",
)

TEXT_WORDS = (
    "сообщение", "письмо", "текст", "шаблон", "ответ клиенту",
    "напиши письмо", "напиши сообщение",
)

LINK_WORDS = (
    "ссылка", "url", "линк", "короткая ссылка",
    "сократи ссылку", "short link",
)

EXPLORATION_WORDS = (
    "идея", "вариант", "примерно", "атмосфера", "может",
    "посмотрим", "подумаем", "как думаешь",
)

DISCUSSION_WORDS = ("обсудим", "поговорим", "как думаешь", "что думаешь")
REFLECTION_WORDS = ("почему", "объясни", "рассуждай", "размышляй")
SPACE_WORDS = ("пространство", "scene", "renderer", "график", "таблица", "формула")


def is_continuation(text: str) -> bool:
    t = normalize(text)
    if t in CONTINUATION_WORDS:
        return True
    return len(t) <= 36 and contains_any(t, CONTINUATION_WORDS)


def is_real_question(text: str) -> bool:
    t = normalize(text)
    if is_continuation(t) or len(t) <= 10:
        return False
    return "?" in t or contains_any(t, QUESTION_WORDS)


def is_edit_request(text: str) -> bool:
    return contains_any(text, EDIT_WORDS)


def is_generate_request(text: str) -> bool:
    return contains_any(text, GENERATION_WORDS)


def is_lightweight_visual_request(text: str) -> bool:
    return contains_any(text, LIGHT_VISUAL_WORDS)


def detect_renderer_subtype(text: str) -> str:
    t = normalize(text)
    if "график" in t:
        return "graph"
    if "формула" in t:
        return "formula"
    if "таблица" in t or "grid" in t:
        return "table"
    if "diagram" in t or "диаграмма" in t or "схема" in t:
        return "diagram"
    if any(x in t for x in ("layout", "пространство", "scene", "композиция")):
        return "scene"
    return "renderer"


def is_renderer_request(text: str) -> bool:
    return contains_any(text, RENDER_WORDS)


def is_spatial_request(text: str) -> bool:
    return contains_any(text, SPATIAL_WORDS)


def is_web_request(text: str) -> bool:
    return contains_any(text, WEB_WORDS)


def is_text_request(text: str) -> bool:
    return contains_any(text, TEXT_WORDS)


def is_link_request(text: str) -> bool:
    return contains_any(text, LINK_WORDS)


def is_exploration_request(text: str) -> bool:
    return contains_any(text, EXPLORATION_WORDS)


def is_discussion_request(text: str) -> bool:
    return contains_any(text, DISCUSSION_WORDS)


def is_reflection_request(text: str) -> bool:
    return contains_any(text, REFLECTION_WORDS)


def is_space_discussion_request(text: str) -> bool:
    return (
        contains_any(text, DISCUSSION_WORDS)
        and contains_any(text, SPACE_WORDS)
    )


def build_intent_result() -> Dict[str, Any]:
    """
    Canonical signal packet.

    All modality fields are soft evidence. The Quantum Processor is the only
    component allowed to arbitrate them into a final action.
    """
    return {
        "intent": "chat",
        "confidence": 0.5,
        "source": "default",

        "prefer_renderer": False,
        "prefer_lightweight": False,
        "prefer_guidance": False,
        "prefer_execution": False,
        "prefer_continuation": False,
        "prefer_web": False,

        "renderer_subtype": None,
        "lightweight_visual": False,
        "spatial_scene": False,
        "explicit_image_generation": False,

        "continuation": False,
        "trajectory_safe": True,
        "trajectory_priority": 0.5,

        "exploration": False,
        "discussion_intent": False,
        "reflection_intent": False,
        "space_discussion_intent": False,

        "avoid_heavy_generation": True,
        "avoid_hidden_escalation": True,
        "avoid_telegram_behavior": True,
        "provider_safe": True,

        "machine_only": True,
        "orchestration_ready": True,
        "renderer_first_safe": True,
        "continuity_preserved": True,

        "decision_owner": DECISION_OWNER,
        "provider_calls": 0,
        "parallel_route": False,
        "route_selection": "delegated",
        "renderer_selection": "delegated",
        "execution_selection": "delegated",
    }


def _apply_continuation(result: Dict[str, Any], state: Dict[str, Any]) -> bool:
    raw_text = normalize(result.get("_text", ""))
    # Do not let stale active_flow/visual_scene turn greetings and short social
    # questions into continuation evidence.
    if raw_text in {"привет", "приветик", "здравствуй", "здравствуйте", "добрый день", "добрый вечер", "доброе утро", "кто ты", "как тебя зовут", "как ти бязовут"}:
        return False

    if not is_continuation(result["_text"]):
        return False

    result["continuation"] = True
    result["prefer_continuation"] = True
    result["trajectory_priority"] = 0.9

    if state.get("active_flow"):
        result.update({
            "intent": "continuation",
            "confidence": 0.88,
            "source": "continuation",
        })
        return True

    if state.get("active_visual_scene"):
        result.update({
            "intent": "visual_continuation",
            "confidence": 0.84,
            "source": "visual_scene",
            "prefer_renderer": True,
        })
        return True

    return False


def detect_intent(text: str, state: Optional[dict] = None) -> Dict[str, Any]:
    """
    Produce intent evidence without becoming a hard router.

    Important:
        The order below is evidence collection, not architectural routing.
        The returned packet must be fused with cognition, semantic state,
        dialogue history and scene state by the Quantum Processor.
    """
    t = normalize(text)
    state = state if isinstance(state, dict) else {}

    result = build_intent_result()
    result["_text"] = t
    patch_intent_detect(t)

    # -------------------------------------------------
    # Continuity evidence
    # -------------------------------------------------
    if _apply_continuation(result, state):
        result.pop("_text", None)
        return result

    result["exploration"] = is_exploration_request(t)
    result["discussion_intent"] = is_discussion_request(t)
    result["reflection_intent"] = is_reflection_request(t)
    result["space_discussion_intent"] = is_space_discussion_request(t)

    if result["exploration"]:
        result["prefer_lightweight"] = True
        result["lightweight_visual"] = True
        result["trajectory_priority"] = max(result["trajectory_priority"], 0.72)

    if result["discussion_intent"] or result["reflection_intent"] or result["space_discussion_intent"]:
        result["prefer_guidance"] = True

    # -------------------------------------------------
    # Independent evidence signals
    # -------------------------------------------------
    # We deliberately do not return early here. A user request may contain
    # multiple simultaneous signals: e.g. a graph + explanation + web lookup.
    candidates = []

    if is_web_request(t):
        candidates.append(("web", 0.88, "web"))
        result["prefer_web"] = True

    if is_link_request(t):
        candidates.append(("link", 0.92, "link"))

    if is_edit_request(t):
        candidates.append(("edit", 0.88, "edit"))
        result["prefer_execution"] = True

    if is_spatial_request(t):
        candidates.append(("spatial", 0.84, "spatial"))
        result["spatial_scene"] = True
        result["prefer_renderer"] = True

    if is_renderer_request(t):
        candidates.append(("render", 0.88, "renderer"))
        result["prefer_renderer"] = True
        result["renderer_subtype"] = detect_renderer_subtype(t)

    if is_lightweight_visual_request(t):
        candidates.append(("lightweight_visual", 0.80, "lightweight_visual"))
        result["prefer_lightweight"] = True
        result["lightweight_visual"] = True

    if is_generate_request(t):
        candidates.append(("generate", 0.90, "generate"))
        result["explicit_image_generation"] = True
        result["avoid_heavy_generation"] = False

    if is_text_request(t):
        candidates.append(("text", 0.84, "text"))
        result["prefer_guidance"] = True

    if is_real_question(t):
        candidates.append(("question", 0.72, "question"))
        result["prefer_guidance"] = True

    # Choose a descriptive primary signal only. This is NOT the final action.
    if candidates:
        primary = max(candidates, key=lambda item: item[1])
        result["intent"], result["confidence"], result["source"] = primary
        result["candidate_signals"] = [
            {"intent": intent, "confidence": confidence, "source": source}
            for intent, confidence, source in candidates
        ]

    # -------------------------------------------------
    # Active-flow evidence
    # -------------------------------------------------
    active_flow = state.get("active_flow")
    if active_flow:
        result["continuation"] = True
        result["prefer_continuation"] = True
        result["trajectory_priority"] = max(result["trajectory_priority"], 0.74)

        flow_type = active_flow.get("type") if isinstance(active_flow, dict) else None
        result["active_flow_type"] = flow_type

        if flow_type in {
            "renderer_space", "visual_scene", "image_generate",
            "image_edit", "image", "math",
        }:
            result["trajectory_evidence"] = {
                "flow_type": flow_type,
                "preserve": True,
            }

    # -------------------------------------------------
    # Canonical metadata
    # -------------------------------------------------
    result["quantum_evidence"] = {
        "current_request": t,
        "candidate_signals": result.get("candidate_signals", []),
        "continuation": result["continuation"],
        "active_flow": active_flow or {},
        "active_visual_scene": state.get("active_visual_scene", {}),
        "trajectory_priority": result["trajectory_priority"],
    }

    result["decision_owner"] = DECISION_OWNER
    result["provider_calls"] = 0
    result["parallel_route"] = False
    result["route_selection"] = "delegated"
    result["renderer_selection"] = "delegated"
    result["execution_selection"] = "delegated"
    result.pop("_text", None)

    safe_patch_log(
        f"INTENT EVIDENCE READY: {result.get('intent')} / "
        f"{len(result.get('candidate_signals', []))} candidates"
    )
    return result
