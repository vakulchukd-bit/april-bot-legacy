"""
April Internal Interpretation Layer
-----------------------------------
Canonical semantic owner for dialogue understanding.

The layer does not route providers or renderers. It reconstructs:
- active thread / semantic anchor
- current task
- open loops
- references to previous results
- relation to the previous turn
- natural next actions

No lexical trigger decides CONTINUE. Lexical forms may be evidence only.
"""

from __future__ import annotations

import re
from copy import deepcopy
from difflib import SequenceMatcher
from typing import Any, Dict, List

from blocks.interpretation_layer import (
    QUANTUM_INTERPRETATION_ENGINE,
    QUANTUM_TURN_MEANING_ENGINE,
)


class AprilInternalInterpretation:
    VERSION = "april_internal_interpretation_v1"

    _PRONOUNS = {
        "он", "она", "оно", "они", "его", "её", "ее", "ему", "ей", "им",
        "ими", "этот", "эта", "это", "эти", "того", "той", "тем", "такой",
        "него", "неё", "нее", "ней", "нему", "ним", "них", "который",
        "которая", "которое", "которые", "ею", "такого", "такую",
    }
    _GENERIC_WORDS = {
        "привет", "здравствуйте", "добрый", "доброго", "день", "вечер",
        "утро", "спасибо", "благодарю", "пока", "хорошо", "ладно",
    }
    _FOLLOWUP_WORDS = {
        "еще", "ещё", "дальше", "продолжи", "продолжить", "такой",
        "такие", "следующий", "следующую", "следующее", "какую", "какой",
        "какое", "какие", "опиши", "теперь", "а", "расскажи", "поясни", "объясни",
    }
    _ACTION_WORDS = {
        "сделай", "измени", "исправь", "добавь", "убери", "переделай",
        "покажи", "нарисуй", "создай", "сгенерируй", "дополни",
    }

    @staticmethod
    def _clean(value: Any, limit: int = 5000) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip())[:limit]

    @staticmethod
    def _tokens(value: Any) -> List[str]:
        return re.findall(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+", str(value or "").lower())

    @classmethod
    def _substantive_tokens(cls, value: Any) -> List[str]:
        stop = getattr(QUANTUM_INTERPRETATION_ENGINE, "_STOP", set())
        return [x for x in cls._tokens(value) if len(x) >= 3 and x not in stop]

    @classmethod
    def _generic(cls, text: str) -> bool:
        tokens = cls._tokens(text)
        if not tokens:
            return False
        return all(token in cls._GENERIC_WORDS or token in {"и", "а", "ну"} for token in tokens)

    @classmethod
    def _self_contained(cls, profile: Dict[str, Any], text: str) -> bool:
        features = profile.get("request_features") if isinstance(profile, dict) else {}
        if isinstance(features, dict) and "self_contained" in features:
            return bool(features.get("self_contained"))
        return len(cls._substantive_tokens(text)) >= 2

    @classmethod
    def _concrete_tokens(cls, text: str) -> List[str]:
        excluded = (
            set(cls._GENERIC_WORDS)
            | cls._FOLLOWUP_WORDS
            | cls._ACTION_WORDS
            | {
                "знаю", "знаешь", "знать", "можешь", "можно", "нужно", "чем", "помочь",
                "хочу", "хочешь", "дать", "дай", "покажи",
                "text", "image", "gallery", "diagram", "graph", "table",
                "formula", "code", "link", "file", "audio", "video", "action",
            }
        )
        stop = getattr(QUANTUM_INTERPRETATION_ENGINE, "_STOP", set())
        return [
            token for token in cls._tokens(text)
            if len(token) >= 3 and token not in stop and token not in excluded
        ]

    @classmethod
    def _previous_meaning(cls, state: Dict[str, Any]) -> Dict[str, Any]:
        for key in ("april_last_turn_meaning", "last_turn_meaning"):
            value = state.get(key)
            if isinstance(value, dict) and value.get("meaning"):
                return value
        return {}

    @classmethod
    def _active_terms(cls, meaning: Dict[str, Any], state: Dict[str, Any]) -> List[str]:
        terms: List[str] = []
        mb = meaning.get("meaning") if isinstance(meaning, dict) and isinstance(meaning.get("meaning"), dict) else {}

        # The processor's active task is the strongest persistent anchor.
        active = state.get("april_active_task")
        if isinstance(active, dict):
            terms += cls._substantive_tokens(active.get("object"))
            terms += cls._substantive_tokens(active.get("topic"))

        # The user's own last request is the next strongest source.
        user = cls._clean(meaning.get("user_request") if isinstance(meaning, dict) else "", 1600)
        terms += cls._substantive_tokens(user)

        # Then add semantic concepts from the completed turn.
        for concept in (mb.get("concepts") or []):
            if isinstance(concept, str) and concept:
                terms += cls._substantive_tokens(concept)
        terms += [
            cls._clean(x.get("value"), 120)
            for x in (mb.get("objects") or [])
            if isinstance(x, dict) and x.get("value")
        ]

        # Assistant prose is only weak evidence and must never become the
        # active entity when the user's request already supplied one.
        if not terms:
            answer = cls._clean(meaning.get("answer") if isinstance(meaning, dict) else "", 3000)
            terms += cls._substantive_tokens(answer)[:6]

        excluded = (
            set(cls._GENERIC_WORDS)
            | cls._FOLLOWUP_WORDS
            | cls._ACTION_WORDS
            | {
                "text", "image", "gallery", "diagram", "graph", "table",
                "formula", "code", "link", "file", "audio", "video", "action",
                "нарисуй", "напиши", "расскажи", "объясни", "опиши", "сделай", "теперь", "а", "чем", "помочь",
                "сгенерируй", "создай", "покажи", "изменить", "изменить",
            }
        )
        out: List[str] = []
        seen = set()
        for term in terms:
            term = cls._clean(term, 120)
            key = term.casefold()
            if not term or key in seen or key in excluded:
                continue
            if key in cls._PRONOUNS:
                continue
            seen.add(key)
            out.append(term)
        return out[:24]

    @classmethod
    def _resolve_reference(cls, current: str, active_terms: List[str]) -> Dict[str, Any]:
        low = current.lower()
        pronouns = [p for p in cls._PRONOUNS if re.search(
            rf"(?<![A-Za-zА-Яа-яЁёЇїІіЄєҐґ]){re.escape(p)}(?![A-Za-zА-Яа-яЁёЇїІіЄєҐґ])",
            low,
        )]
        if not pronouns and len(cls._substantive_tokens(current)) <= 1:
            # A one-word continuation can be a correction/typo of the active entity.
            token = cls._substantive_tokens(current)
            if token and active_terms:
                best = max(
                    ((SequenceMatcher(None, token[0], term.lower()).ratio(), term) for term in active_terms),
                    default=(0.0, ""),
                )
                if best[0] >= 0.62:
                    return {
                        "present": True,
                        "target": best[1],
                        "confidence": round(best[0], 4),
                        "kind": "entity_correction",
                        "pronouns": [],
                    }
            return {"present": False, "target": "", "confidence": 0.0, "kind": "", "pronouns": []}

        target = active_terms[0] if active_terms else ""
        return {
            "present": bool(target),
            "target": target,
            "confidence": 0.82 if target else 0.0,
            "kind": "anaphora" if pronouns else "contextual_reference",
            "pronouns": pronouns,
        }

    @classmethod
    def _natural_next_actions(
        cls,
        current: str,
        current_profile: Dict[str, Any],
        meaning: Dict[str, Any],
        relation: str,
        reference: Dict[str, Any],
    ) -> List[str]:
        mb = meaning.get("meaning") if isinstance(meaning.get("meaning"), dict) else {}
        rep = str(current_profile.get("best_representation") or "").lower()
        op = str(current_profile.get("best_operation") or "").lower()
        active_rep = [str(x).lower() for x in (mb.get("representations") or [])]

        actions: List[str] = []
        if relation == "CONTINUE":
            if reference.get("present"):
                actions += ["изменить или описать текущий объект", "уточнить текущий результат"]
            if active_rep:
                actions += [f"развить результат {active_rep[0]}"]
            if op in {"build", "create", "modify"} or rep in {"image", "code", "formula", "table", "graph"}:
                actions += ["изменить результат", "показать следующий вариант"]
            else:
                actions += ["уточнить", "расширить объяснение"]
        elif relation == "NEW":
            actions += ["понять самостоятельную задачу", "создать новый контекст"]
        return list(dict.fromkeys(actions))[:4]

    @classmethod
    def interpret(cls, request: str, state: Dict[str, Any] | None = None) -> Dict[str, Any]:
        state = state if isinstance(state, dict) else {}
        current = cls._clean(request, 5000)
        history = state.get("dialog") if isinstance(state.get("dialog"), list) else []
        previous = cls._previous_meaning(state)

        # One semantic measurement. No provider call.
        raw = QUANTUM_INTERPRETATION_ENGINE.interpret(
            current,
            history=history,
            state=state,
        ) or {}
        profile = QUANTUM_INTERPRETATION_ENGINE.measure(current)
        meaning = previous.get("meaning") if isinstance(previous.get("meaning"), dict) else {}

        active_terms = cls._active_terms(previous, state)
        reference = cls._resolve_reference(current, active_terms)
        self_contained = cls._self_contained(profile, current)
        generic_current = cls._generic(current)

        comparison = {}
        if previous:
            try:
                comparison = QUANTUM_TURN_MEANING_ENGINE.compare(
                    current,
                    previous,
                    semantic_engine=QUANTUM_INTERPRETATION_ENGINE,
                ) or {}
            except Exception:
                comparison = {}

        evidence = comparison.get("evidence") if isinstance(comparison.get("evidence"), dict) else {}
        relation_scores = comparison.get("relation_scores") if isinstance(comparison.get("relation_scores"), dict) else {}

        # The key decision: continuation requires dependency evidence.
        # A self-contained request with a new object is not continuation merely
        # because the previous assistant message ended with a question.
        overlap = float(evidence.get("content_overlap", 0.0) or 0.0)
        semantic_similarity = max(
            float(evidence.get("topic_similarity", 0.0) or 0.0),
            float(evidence.get("content_semantic_similarity", 0.0) or 0.0),
            float(evidence.get("anchor_similarity", 0.0) or 0.0),
        )
        continuation_semantics = float(evidence.get("continuation_semantics", 0.0) or 0.0)
        explicit_novelty = bool(evidence.get("explicit_topic_novelty"))
        active_substantive = bool(active_terms)

        concrete_current = cls._concrete_tokens(current)
        short_followup = len(cls._substantive_tokens(current)) <= 5 and not concrete_current
        action_reference = reference.get("present") and bool(
            set(cls._tokens(current)) & (cls._PRONOUNS | cls._ACTION_WORDS)
        )

        # A previous greeting / empty task cannot own the next request.
        previous_user = cls._clean(previous.get("user_request"))
        previous_goal = cls._clean(meaning.get("goal"))
        previous_operation = cls._clean(meaning.get("operation"))
        previous_topic = cls._clean(meaning.get("topic"))
        previous_answer = cls._clean(previous.get("answer"))
        previous_answer_has_entity = bool(cls._concrete_tokens(previous_answer))
        previous_is_generic = (
            cls._generic(previous_user)
            or not previous_operation
            or previous_topic.casefold() in {"привет", "здравствуйте", "добрый день", "добрый вечер", "доброе утро"}
            or (not cls._concrete_tokens(previous_user) and not previous_answer_has_entity)
        )

        # Genuine dependency evidence.
        strong_reference = bool(action_reference)
        strong_overlap = overlap >= 0.18 or semantic_similarity >= 0.22
        short_contextual = bool(
            short_followup
            and active_substantive
            and not explicit_novelty
            and not generic_current
            and (
                float(evidence.get("contextual_support", 0.0) or 0.0) >= 0.45
                or float(relation_scores.get("develop_current", 0.0) or 0.0) >= 0.12
            )
        )
        typo_reference = reference.get("kind") == "entity_correction"

        if not previous:
            relation = "NEW"
            reason = "no_previous_semantic_turn"
        elif generic_current and not strong_reference:
            relation = "NEW"
            reason = "generic_current_request"
        elif previous_is_generic and self_contained and not active_substantive:
            relation = "NEW"
            reason = "previous_turn_has_no_active_task"
        elif previous_is_generic and self_contained and not (strong_reference and active_substantive):
            relation = "NEW"
            reason = "previous_turn_has_no_active_task"
        elif explicit_novelty and not strong_reference and not short_contextual:
            relation = "NEW"
            reason = "explicit_new_topic_evidence"
        elif (strong_reference or typo_reference) and active_substantive:
            relation = "CONTINUE"
            reason = "reference_to_active_semantic_anchor"
        elif strong_overlap or continuation_semantics >= 0.12:
            relation = "CONTINUE"
            reason = "multi_evidence_semantic_dependency"
        elif short_contextual or (
            short_followup
            and active_substantive
            and not explicit_novelty
            and not generic_current
            and bool((comparison.get("evidence") or {}).get("short_followup_lock"))
        ):
            relation = "CONTINUE"
            reason = "short_request_dependent_on_active_thread"
        else:
            relation = "NEW"
            reason = "no_dependency_proof"

        # Build a human-free resolved request for the processor/provider.
        target = reference.get("target") if reference.get("present") else ""
        resolved_request = current
        if relation == "CONTINUE" and target:
            resolved_request = f"{current}\nКонтекст: текущий объект/сущность — {target}."
        elif relation == "CONTINUE" and previous_topic:
            resolved_request = f"{current}\nКонтекст текущей задачи: {previous_topic}."

        next_actions = cls._natural_next_actions(current, profile, previous, relation, reference)

        understanding = {
            "version": cls.VERSION,
            "relation": relation,
            "confidence": round(
                min(
                    1.0,
                    max(
                        0.0,
                        0.85 if strong_reference or typo_reference else
                        0.65 if strong_overlap else
                        0.58 if short_contextual else
                        0.92 if relation == "NEW" else 0.45,
                    ),
                ),
                4,
            ),
            "reason": reason,
            "current": {
                "text": current,
                "self_contained": self_contained,
                "generic": generic_current,
                "operation": profile.get("best_operation"),
                "object": profile.get("best_object"),
                "goal": profile.get("best_goal"),
                "representation": profile.get("best_representation"),
            },
            "active_thread": {
                "topic": previous_topic,
                "goal": previous_goal,
                "operation": previous_operation,
                "entities": active_terms[:12],
                "representations": list(meaning.get("representations") or []),
            },
            "reference": reference,
            "evidence": {
                "topic_similarity": round(float(evidence.get("topic_similarity", 0.0) or 0.0), 4),
                "content_similarity": round(float(semantic_similarity), 4),
                "content_overlap": round(float(overlap), 4),
                "continuation_semantics": round(float(continuation_semantics), 4),
                "explicit_topic_novelty": explicit_novelty,
                "relation_scores": relation_scores,
            },
            "open_loops": deepcopy(
                (previous.get("dialogue_state") or {}).get("open_task", {})
                if isinstance(previous.get("dialogue_state"), dict)
                else {}
            ),
            "next_natural_actions": next_actions,
            "resolved_request": resolved_request,
            "source_engine": "quantum_semantic_measurement",
        }

        return {
            "understanding": understanding,
            "raw": raw,
            "profile": profile,
        }
