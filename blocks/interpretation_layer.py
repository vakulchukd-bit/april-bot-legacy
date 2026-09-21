"""
April Internal Interpretation Layer — dialogue trajectory owner.

This module is the canonical semantic hand-off between live dialogue state and
ProcessorScene.  It does not route providers, execute rooms or render anything.

Vector:
    USER
      -> semantic interpretation
      -> active thread reconstruction
      -> current intent resolution
      -> dialogue relation
      -> open-loop / artifact context
      -> natural next-action forecast
      -> ONE canonical understanding packet
      -> QUANTUM PROCESSOR

Important invariant:
    CONTINUE is a semantic relation, never a lexical trigger.

The existing quantum interpretation engine remains the semantic measurement
engine.  This layer turns its evidence into one internal understanding object
that the Processor can consume without running a second interpretation path.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from blocks.interpretation_layer import QUANTUM_INTERPRETATION_ENGINE


class AprilInternalInterpretation:
    VERSION = "april_internal_interpretation_v2_dialogue_trajectory"

    _ACTION_FAMILY = {
        "answer": ("уточнить ответ", "расширить объяснение", "продолжить тему"),
        "explain": ("уточнить объяснение", "расширить объяснение", "сравнить аспекты"),
        "build": ("изменить результат", "расширить результат", "создать следующий вариант"),
        "present": ("уточнить представление", "изменить представление", "расширить результат"),
        "modify": ("изменить текущий результат", "проверить изменение", "показать итоговый вариант"),
        "retrieve": ("уточнить ресурс", "получить связанный ресурс", "уточнить назначение ресурса"),
        "calculate": ("продолжить вычисление", "проверить результат", "изменить исходные данные"),
        "compare": ("сравнить другой вариант", "уточнить критерий", "расширить сравнение"),
        "analyze": ("углубить анализ", "уточнить аспект", "сравнить результаты"),
        "summarize": ("сократить или расширить итог", "уточнить пункт", "продолжить тему"),
        "list": ("добавить варианты", "уточнить критерий", "сравнить варианты"),
    }

    @staticmethod
    def _text(value: Any, limit: int = 8000) -> str:
        return " ".join(str(value or "").split())[:limit].strip()

    @staticmethod
    def _dict(value: Any) -> Dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @classmethod
    def _first_text(cls, *values: Any, limit: int = 1000) -> str:
        for value in values:
            text = cls._text(value, limit)
            if text:
                return text
        return ""

    @classmethod
    def _current_semantic_task(cls, result: Dict[str, Any]) -> Dict[str, Any]:
        task = result.get("semantic_task")
        if isinstance(task, dict):
            return dict(task)
        profile = result.get("semantic_profile")
        profile = profile if isinstance(profile, dict) else {}
        return {
            "operation": cls._text(profile.get("best_operation"), 120) or "answer",
            "object": cls._text(profile.get("best_object"), 120) or "text",
            "goal": cls._text(profile.get("best_goal"), 120) or "answer",
            "representation": cls._text(result.get("production_representation") or profile.get("best_representation"), 120) or "text",
        }

    @classmethod
    def _active_thread(cls, result: Dict[str, Any], state: Dict[str, Any], relation: str) -> Dict[str, Any]:
        task = cls._current_semantic_task(result)
        dialogue_contract = cls._dict(result.get("dialogue_contract"))
        previous = result.get("turn_meaning_transition")
        previous = previous if isinstance(previous, dict) else {}
        selected = previous.get("selected_turn_meaning") if isinstance(previous.get("selected_turn_meaning"), dict) else {}
        previous_meaning = selected.get("meaning") if isinstance(selected.get("meaning"), dict) else {}

        active_topic = cls._first_text(
            result.get("active_topic"),
            dialogue_contract.get("active_topic"),
            previous_meaning.get("topic") if relation in {"CONTINUE", "RECALL"} else "",
            state.get("april_active_topic"),
            task.get("object"),
            result.get("normalized"),
            limit=1200,
        )
        active_goal = cls._first_text(
            result.get("active_goal"),
            dialogue_contract.get("active_goal"),
            previous_meaning.get("goal") if relation in {"CONTINUE", "RECALL"} else "",
            state.get("april_active_goal"),
            task.get("goal"),
            limit=500,
        )
        entities_state = self_entities = result.get("entity_understanding")
        entities: List[str] = []
        if isinstance(entities_state, dict):
            current_entities = entities_state.get("current")
            if isinstance(current_entities, list):
                for item in current_entities:
                    value = item.get("entity") if isinstance(item, dict) else item
                    value = cls._text(value, 200)
                    if value and value.casefold() not in {x.casefold() for x in entities}:
                        entities.append(value)
        if not entities:
            entity_pack = state.get("active_entity")
            entity_pack = cls._text(entity_pack, 200)
            if entity_pack:
                entities.append(entity_pack)
        if not entities and task.get("object"):
            object_name = cls._text(task.get("object"), 200)
            if object_name and object_name.casefold() not in {"text", "image", "graph", "table", "formula", "code", "link", "diagram"}:
                entities.append(object_name)

        return {
            "topic": active_topic,
            "goal": active_goal,
            "operation": cls._text(task.get("operation"), 120) or "answer",
            "representation": cls._text(task.get("representation"), 120) or "text",
            "entities": entities[:12],
            "relation_owner": "previous_turn" if relation in {"CONTINUE", "RECALL"} else "current_turn",
        }

    @classmethod
    def _open_loops(cls, result: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        previous = result.get("turn_meaning_transition")
        previous = previous if isinstance(previous, dict) else {}
        selected = previous.get("selected_turn_meaning") if isinstance(previous.get("selected_turn_meaning"), dict) else {}
        dialogue_state = selected.get("dialogue_state") if isinstance(selected.get("dialogue_state"), dict) else {}
        open_task = dialogue_state.get("open_task") if isinstance(dialogue_state.get("open_task"), dict) else {}
        pending = state.get("april_pending_task") if isinstance(state.get("april_pending_task"), dict) else {}
        return {
            "pending_input": deepcopy(pending) if pending.get("active") else {},
            "previous_open_task": deepcopy(open_task),
        }

    @classmethod
    def _forecast(cls, task: Dict[str, Any], relation: str, reference: Dict[str, Any], open_loops: Dict[str, Any]) -> Dict[str, Any]:
        operation = cls._text(task.get("operation"), 80).lower() or "answer"
        representation = cls._text(task.get("representation"), 80).lower() or "text"
        actions = list(cls._ACTION_FAMILY.get(operation, cls._ACTION_FAMILY["answer"]))
        if representation in {"image", "gallery", "diagram"}:
            actions.insert(0, "изменить или уточнить визуальный результат")
        elif representation in {"formula", "graph", "table"}:
            actions.insert(0, "уточнить или развить структурированный результат")
        elif representation == "code":
            actions.insert(0, "изменить или проверить текущий код")
        if reference.get("resolved"):
            actions.insert(0, "действовать над разрешённым объектом")
        if open_loops.get("pending_input"):
            actions.insert(0, "завершить ожидающее уточнение")
        return {
            "mode": "semantic_affordance_forecast",
            "relation": relation,
            "next_natural_actions": list(dict.fromkeys(actions))[:4],
            "not_a_route": True,
            "not_a_trigger": True,
        }

    @classmethod
    def interpret(cls, request: str, state: Dict[str, Any] | None = None) -> Dict[str, Any]:
        state = state if isinstance(state, dict) else {}
        current = cls._text(request, 5000)
        history = state.get("dialog") if isinstance(state.get("dialog"), list) else []

        # One semantic interpretation call. The Quantum engine remains the
        # measurement layer; this wrapper is the single dialogue-trajectory owner.
        result = QUANTUM_INTERPRETATION_ENGINE.interpret(
            current,
            history=history,
            state=state,
        ) or {}

        raw_dialogue = cls._dict(result.get("dialogue_vector"))
        contract = cls._dict(result.get("dialogue_contract"))
        sequential = cls._dict(result.get("sequential_dialogue"))
        raw_relation = cls._text(
            raw_dialogue.get("three_way_relation")
            or contract.get("three_way_relation")
            or result.get("dialogue_relation")
            or sequential.get("relation"),
            40,
        ).upper()
        relation = "RECALL" if raw_relation == "RECALL" else "CONTINUE" if raw_relation in {"CONTINUE", "CONTINUE_TOPIC", "DEVELOP_CURRENT"} else "NEW"

        task = cls._current_semantic_task(result)
        production = cls._text(
            result.get("production_representation")
            or task.get("representation")
            or result.get("requested_representation"),
            80,
        ).lower() or "text"
        operation = cls._text(task.get("operation"), 80).lower() or "answer"
        goal = cls._text(task.get("goal"), 80).lower() or "answer"
        object_name = cls._text(task.get("object"), 160).lower() or production
        resolved_reference = cls._text(result.get("resolved_reference"), 500)
        reference_resolution = cls._dict(result.get("reference_resolution"))
        reference_resolved = bool(reference_resolution.get("resolved") or resolved_reference or relation == "RECALL")

        # The quantum engine has already reconstructed semantic context when the
        # turn depends on the previous one. Prefer that resolved request verbatim.
        resolved_request = cls._text(result.get("resolved_request") or contract.get("resolved_request") or current, 8000)
        if relation == "NEW":
            resolved_request = current

        active_thread = cls._active_thread(result, state, relation)
        open_loops = cls._open_loops(result, state)
        forecast = cls._forecast(task, relation, {"resolved": reference_resolved}, open_loops)
        context_understanding = result.get("context_understanding")
        context_understanding = context_understanding if isinstance(context_understanding, dict) else {}

        semantic_understanding = {
            "version": cls.VERSION,
            "current_request": current,
            "resolved_request": resolved_request,
            "relation": relation,
            "confidence": float(sequential.get("confidence") or contract.get("confidence") or result.get("confidence") or 0.0),
            "active_thread": active_thread,
            "current_task": {
                "operation": operation,
                "object": object_name,
                "goal": goal,
                "representation": production,
            },
            "reference": {
                "resolved": reference_resolved,
                "target": resolved_reference,
                "resolution": deepcopy(reference_resolution),
            },
            "open_loops": open_loops,
            "trajectory_forecast": forecast,
            "semantic_context": deepcopy(context_understanding),
            "source": "QUANTUM_INTERPRETATION_ENGINE",
            "provider_calls": 0,
            "decision_owner": "QUANTUM_PROCESSOR",
        }

        dialogue = {
            "version": "april_dialogue_contract_v2_internal",
            "relation": relation,
            "continuation": relation == "CONTINUE",
            "reference_to_previous": relation == "RECALL" or reference_resolved,
            "context_dependency": "continuation" if relation == "CONTINUE" else "recall" if relation == "RECALL" else "independent",
            "active_topic": active_thread.get("topic", ""),
            "active_goal": active_thread.get("goal", ""),
            "active_thread": deepcopy(active_thread),
            "open_loops": deepcopy(open_loops),
            "resolved_reference": resolved_reference,
            "resolved_request": resolved_request,
            "turn_trajectory": deepcopy(forecast),
            "semantic_dependency_proven": relation in {"CONTINUE", "RECALL"},
        }

        attributes = dict(result.get("visual_production") or {})
        visual_mode = cls._text(result.get("visual_production_mode"), 120)
        if visual_mode:
            attributes["visual_production_mode"] = visual_mode
        elif production == "image":
            attributes["visual_production_mode"] = "image_generation" if any(
                marker in current.casefold() for marker in ("нарисуй", "сгенерируй", "создай", "изобрази")
            ) else "image_present"
        elif production in {"diagram", "graph", "table", "code", "formula", "link"}:
            attributes["visual_production_mode"] = production
        if production == "link" and ("telegram" in current.lower() or "телеграм" in current.lower()):
            # The Telegram clarification remains a semantic pending task, not a
            # dialogue trigger. The exact destination can only be resolved from
            # the user's next semantic input.
            pending = open_loops.get("pending_input") or {}
            if not pending and not reference_resolved and not any(token in current.lower().split() for token in ("http://", "https://", "@")):
                attributes["telegram_pending"] = True
                attributes["pending_question"] = "Какой Telegram нужен: официальный канал, чат или пользовательский аккаунт?"

        intent = {
            "operation": operation,
            "object": object_name,
            "representation": production,
            "goal": goal,
            "topic": active_thread.get("topic") or object_name,
            "attributes": attributes,
            "resolved_request": resolved_request,
            "semantic_understanding": deepcopy(semantic_understanding),
        }

        return {
            "understanding": semantic_understanding,
            "dialogue": dialogue,
            "intent": intent,
            "raw": result,
        }
