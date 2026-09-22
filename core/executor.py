from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from dataclasses import asdict, is_dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

from blocks.C_ARTIFACT_CONTRACT import (
    MachineRequest,
    MachineResponse,
    build_machine_scene,
    build_scene_contract,
)
from blocks.april_personality import APRIL_IDENTITY
from blocks.interpretation_layer import interpret_request
from blocks.provider_router import generate_text
from blocks.state_manager import get_state, update_scene_context, persist_state, build_dialogue_memory_bridge
from blocks.presentation_formatter import canonical_payload_for_block, validate_render_block_payload

PROCESSOR_VERSION = "april_sequential_processor_v1_fast_memory_scene"
PROCESSOR_MODE = "SEQUENTIAL_INTERPRETATION_MEMORY_PROVIDER_SCENE"

# ============================================================
# Canonical control tables
# ============================================================

_RENDERER_REGISTRY = {
    "text": "MessageTextBlock",
    "markdown": "MessageTextBlock",
    "formula": "MessageTextBlock",
    "code": "CodeBlock",
    "graph": "GraphBlock",
    "table": "TableBlock",
    "diagram": "GalleryBlock",
    "image": "GalleryBlock",
    "gallery": "GalleryBlock",
    "link": "LinkCard",
    "file": "LinkCard",
}

_STRUCTURED_TYPES = {"code", "graph", "table", "diagram", "image", "gallery", "formula", "link"}

_NEW_TOPIC_MARKERS = (
    "новая тема",
    "другая тема",
    "забудь это",
)

_FOLLOWUP_PREFIXES = (
    "теперь",
    "ещё",
    "еще",
    "дальше",
    "сделай",
    "покажи",
    "нарисуй",
    "измени",
    "добавь",
    "убери",
    "продолжи",
    "объясни",
    "расскажи",
    "уточни",
    "а теперь",
    "и ещё",
    "и еще",
)

_SHORT_PENDING_WORDS = {
    "официальный", "официальная", "официальное", "официально",
    "канал", "чат", "пользователь", "аккаунт", "личный", "да", "нет",
}

_PERSIST_TASKS: Dict[str, asyncio.Task] = {}


def _consume_persist_result(task: asyncio.Task) -> None:
    try:
        task.result()
    except BaseException as exc:
        if not isinstance(exc, asyncio.CancelledError):
            print("⚠️ APRIL BACKGROUND PERSIST:", exc)


_ARTIFACT_REFERENCE_FORMS = (
    "этот график",
    "на графике",
    "этот рисунок",
    "эту картинку",
    "на картинке",
    "на схеме",
    "этот файл",
    "это",
    "его",
    "её",
    "ее",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _as_dict(value: Any) -> Dict[str, Any]:
    """Safely normalize mapping-like semantic payloads to a dict.

    Executor calls this helper in several canonical request builders. The
    deployed path previously referenced it without defining it, causing every
    chat request reaching ProcessorScene.prepare() to fail with NameError.
    """
    if isinstance(value, dict):
        return value
    if is_dataclass(value) and not isinstance(value, type):
        try:
            converted = asdict(value)
            return converted if isinstance(converted, dict) else {}
        except Exception:
            return {}
    if hasattr(value, "items"):
        try:
            return dict(value.items())
        except Exception:
            return {}
    return {}


def _person_entity_from_answer(text: str) -> str:
    """Keep the latest human entity visible to the authenticated dialogue state."""
    value = _text(text)
    if not value:
        return ""
    candidates = []
    patterns = (
        r"\b(?:[А-ЯЁ][а-яё-]{2,}\s+){1,3}[А-ЯЁ][а-яё-]{2,}\b",
        r"\b[А-ЯЁ][а-яё-]{3,}\b",
    )
    ignored = {"Михаил", "Михаила", "Сергей", "Сергеевич", "Россия", "СССР", "Советский", "Президент", "Генеральный"}
    for pattern in patterns:
        for match in re.finditer(pattern, value):
            candidate = re.sub(r"\s+", " ", match.group(0)).strip(' ,.;:()"')
            if not candidate or candidate in ignored:
                continue
            # Avoid title-like fragments; prefer full person-name sequences.
            if len(candidate.split()) >= 2:
                candidates.append(candidate)
    return candidates[-1] if candidates else ""


def _tokens(value: str) -> List[str]:
    return re.findall(r"[a-zа-яё0-9_]+", value.lower())


def _compact(value: Any, depth: int = 0, max_depth: int = 3, max_items: int = 6) -> Any:
    if depth > max_depth:
        return None
    if value in (None, "", [], {}):
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key, item in list(value.items())[:16]:
            cleaned = _compact(item, depth + 1, max_depth, max_items)
            if cleaned not in (None, "", [], {}):
                out[str(key)] = cleaned
        return out
    if isinstance(value, (list, tuple, set)):
        out = []
        for item in list(value)[:max_items]:
            cleaned = _compact(item, depth + 1, max_depth, max_items)
            if cleaned not in (None, "", [], {}):
                out.append(cleaned)
        return out
    return _text(value)


def _stable_id(prefix: str, payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"



def _provider_artifact_to_block(artifact: Any) -> Dict[str, Any]:
    """Convert a Provider artifact envelope into one canonical render block."""
    if not isinstance(artifact, dict):
        return {}

    kind = _text(
        artifact.get("type")
        or artifact.get("artifact_type")
        or artifact.get("kind")
        or artifact.get("representation")
    ).lower()
    kind = {
        "chart": "graph",
        "plot": "graph",
        "picture": "image",
        "photo": "image",
    }.get(kind, kind)
    if not kind:
        return {}

    payload = artifact.get("payload") if isinstance(artifact.get("payload"), dict) else {}
    data = artifact.get("data") if isinstance(artifact.get("data"), dict) else {}
    if not payload and data:
        payload = dict(data)

    if kind == "image" and isinstance(payload, dict):
        direct = (
            payload.get("src")
            or payload.get("url")
            or payload.get("image")
            or payload.get("image_data_uri")
        )
        if direct:
            payload.setdefault("src", direct)
            payload.setdefault("url", direct)
            payload.setdefault("image", direct)

    if not payload and kind in {"text", "markdown"}:
        content = _text(artifact.get("content") or artifact.get("text"))
        if content:
            return {
                "type": kind,
                "content": content,
                "text": content,
                "renderer": "MessageTextBlock",
                "viewer": "MessageTextBlock",
                "scene_contract": True,
                "human_visible": True,
            }

    if not payload:
        return {}

    renderer = _RENDERER_REGISTRY.get(kind, "MessageTextBlock")
    return {
        "type": kind,
        "artifact_type": kind,
        "payload": payload,
        "renderer": renderer,
        "viewer": renderer,
        "scene_contract": True,
        "human_visible": True,
        "block_id": _stable_id(f"provider-{kind}", payload),
    }


def _bridge_provider_artifacts(machine_response: dict) -> dict:
    """
    Bridge structured Provider output into render_blocks before SceneContract.

    Provider/Executor owns transport normalization; Web/RenderMessage remains the
    renderer owner. This path never invents content and only promotes payloads
    already returned by Provider.
    """
    if not isinstance(machine_response, dict):
        return machine_response

    existing = machine_response.get("render_blocks")
    existing = list(existing) if isinstance(existing, list) else []
    candidates: list[dict[str, Any]] = []

    scene = machine_response.get("scene")
    if isinstance(scene, dict):
        scene_blocks = scene.get("render_blocks") or scene.get("blocks") or []
        if isinstance(scene_blocks, list):
            candidates.extend(x for x in scene_blocks if isinstance(x, dict))

    for key in ("artifacts", "artifacts_payload"):
        values = machine_response.get(key)
        if isinstance(values, list):
            candidates.extend(x for x in values if isinstance(x, dict))

    metadata = dict(machine_response.get("metadata") or {})
    for artifact in candidates:
        spec = artifact.get("image_generation_spec") if isinstance(artifact, dict) else None
        if isinstance(spec, dict) and "image_generation_spec" not in metadata:
            metadata["image_generation_spec"] = spec
    if metadata:
        machine_response["metadata"] = metadata

    seen = {
        json.dumps(
            {
                "type": _text(block.get("type")).lower(),
                "payload": block.get("payload", {}),
                "content": block.get("content", ""),
            },
            ensure_ascii=False,
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        )
        for block in existing
        if isinstance(block, dict)
    }

    bridged = list(existing)
    for candidate in candidates:
        block = (
            candidate
            if candidate.get("type") and (
                candidate.get("payload") or candidate.get("content") or candidate.get("renderer")
            )
            else _provider_artifact_to_block(candidate)
        )
        if not block:
            continue
        sig = json.dumps(
            {
                "type": _text(block.get("type")).lower(),
                "payload": block.get("payload", {}),
                "content": block.get("content", ""),
            },
            ensure_ascii=False,
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        )
        if sig not in seen:
            seen.add(sig)
            bridged.append(block)

    machine_response["render_blocks"] = bridged
    return machine_response


def _state_artifact_type(state: dict) -> str:
    artifact = state.get("last_artifact")
    if isinstance(artifact, dict):
        return _text(artifact.get("type") or artifact.get("artifact_type")).lower()
    scene = state.get("current_visual_scene")
    if isinstance(scene, dict):
        types = scene.get("render_block_types") or []
        if isinstance(types, list):
            for item in types:
                kind = _text(item).lower()
                if kind in _STRUCTURED_TYPES:
                    return kind
    return ""


class SequentialInterpretation:
    """Compatibility adapter; semantic interpretation owns dialogue relation."""

    def __init__(self) -> None:
        self.semantic_result: Dict[str, Any] = {}

    def dialogue(self, request: str, state: dict) -> Dict[str, Any]:
        state = state if isinstance(state, dict) else {}
        history = state.get("dialog")
        if not isinstance(history, list):
            history = state.get("dialogue_history") if isinstance(state.get("dialogue_history"), list) else []
        try:
            semantic_result = interpret_request(request, history=history, state=state)
        except Exception as exc:
            print("⚠️ APRIL SEMANTIC DIALOGUE:", exc)
            semantic_result = {}
        self.semantic_result = semantic_result if isinstance(semantic_result, dict) else {}

        vector = self.semantic_result.get("dialogue_vector") if isinstance(self.semantic_result.get("dialogue_vector"), dict) else {}
        contract = self.semantic_result.get("dialogue_contract") if isinstance(self.semantic_result.get("dialogue_contract"), dict) else {}
        relation = _text(vector.get("three_way_relation") or contract.get("three_way_relation") or contract.get("relation") or "NEW").upper()
        relation = {
            "CONTINUE_TOPIC": "CONTINUE",
            "CONTINUATION": "CONTINUE",
            "CONTINUE": "CONTINUE",
            "ARTIFACT_REFERENCE": "CONTINUE",
            "NEW_TOPIC": "NEW",
            "NEW": "NEW",
            "INDEPENDENT": "NEW",
            "RECALL": "RECALL",
        }.get(relation, relation)
        if relation not in {"CONTINUE", "RECALL", "NEW"}:
            relation = "NEW"

        trajectory = vector.get("trajectory") if isinstance(vector.get("trajectory"), dict) else self.semantic_result.get("dialogue_trajectory")
        trajectory = trajectory if isinstance(trajectory, dict) else {}
        canonical_topic = _text(vector.get("canonical_topic") or contract.get("canonical_topic") or self.semantic_result.get("canonical_topic"))
        pending = state.get("april_pending_task") if isinstance(state.get("april_pending_task"), dict) else {}
        pending_resolved = bool(pending.get("active") and relation == "CONTINUE")
        reference = bool(relation == "RECALL" or contract.get("reference_to_previous"))
        dependency = _text(contract.get("context_dependency"))
        if not dependency:
            dependency = "pending" if pending_resolved else "recall" if reference else "continuation" if relation == "CONTINUE" else "independent"
        anchor = "pending_task" if pending_resolved else "last_turn" if relation == "CONTINUE" else "memory" if reference else "none"
        continuation_analysis = self.semantic_result.get("continuation_content_analysis")
        continuation_analysis = continuation_analysis if isinstance(continuation_analysis, dict) else {}
        dialogue_strategy = self.semantic_result.get("dialogue_strategy")
        dialogue_strategy = dialogue_strategy if isinstance(dialogue_strategy, dict) else {}
        resolved_entity = _text(
            self.semantic_result.get("resolved_entity")
            or contract.get("resolved_entity")
            or vector.get("resolved_entity")
            or continuation_analysis.get("active_entity")
        )

        return {
            "relation": relation,
            "continuation": relation == "CONTINUE",
            "reference": reference,
            "dependency": dependency,
            "anchor": anchor,
            "pending_resolved": pending_resolved,
            "resolved_request": _text(self.semantic_result.get("resolved_request") or contract.get("resolved_request") or request),
            "resolved_reference": _text(self.semantic_result.get("resolved_reference") or contract.get("resolved_reference")),
            "resolved_entity": resolved_entity,
            "resolved_entity_source": _text(
                self.semantic_result.get("resolved_entity_source")
                or contract.get("resolved_entity_source")
                or continuation_analysis.get("active_entity_source")
            ),
            "active_entity": resolved_entity,
            "continuation_content_analysis": continuation_analysis,
            "dialogue_strategy": dialogue_strategy,
            "continuation_authority": _text(
                self.semantic_result.get("continuation_authority")
                or contract.get("continuation_authority")
                or "active_dialogue_sequence"
            ),
            "previous_user_turn": _text(
                self.semantic_result.get("previous_user_turn")
                or contract.get("previous_user_turn")
                or continuation_analysis.get("previous_user_turn")
            ),
            "previous_april_turn": _text(
                self.semantic_result.get("previous_april_turn")
                or contract.get("previous_april_turn")
                or continuation_analysis.get("previous_answer")
            ),
            "selected_memory_index": self.semantic_result.get("selected_memory_index", vector.get("selected_memory_index", -1)),
            "selected_memory_operand": vector.get("selected_memory_operand") or contract.get("selected_memory_operand") or {},
            "trajectory": trajectory,
            "canonical_topic": canonical_topic,
            "sequence_id": _text(
                vector.get("sequence_id")
                or contract.get("sequence_id")
                or (
                    (vector.get("trajectory") or {}).get("sequence_id")
                    if isinstance(vector.get("trajectory"), dict)
                    else ""
                )
            ),
            "target_sequence_id": _text(
                vector.get("target_sequence_id")
                or contract.get("target_sequence_id")
                or vector.get("sequence_id")
                or contract.get("sequence_id")
            ),
            "semantic_result": self.semantic_result,
        }

    def intent(self, request: str, state: dict, dialogue: Dict[str, Any]) -> Dict[str, Any]:
        text = request.lower()

        active = state.get("april_active_task") if isinstance(state.get("april_active_task"), dict) else {}
        pending = state.get("april_pending_task") if isinstance(state.get("april_pending_task"), dict) else {}

        # Pending task owns the representation when the user resolves it.
        if dialogue["pending_resolved"] and pending:
            representation = _text(pending.get("representation") or "text").lower()
            operation = _text(pending.get("operation") or "answer")
            topic = _text(pending.get("topic") or representation)
            attrs = {
                "resolved_pending_input": request,
                "pending_kind": _text(pending.get("expected_input_type")),
            }
            if pending.get("expected_input_type") == "telegram_target_kind":
                attrs["telegram_target_kind"] = self._telegram_kind(text)
            return self._make_intent(operation, pending.get("object") or representation, representation,
                                     pending.get("goal") or "obtain", topic, attrs)

        lexical_representation = self._representation(text)
        semantic_result = dialogue.get("semantic_result") if isinstance(dialogue.get("semantic_result"), dict) else self.semantic_result
        semantic_task = semantic_result.get("semantic_task") if isinstance(semantic_result.get("semantic_task"), dict) else {}
        semantic_representation = _text(
            semantic_result.get("production_representation")
            or semantic_result.get("representation")
            or semantic_task.get("representation")
        ).lower()
        interpretation_control = semantic_result.get("interpretation_control") if isinstance(semantic_result.get("interpretation_control"), dict) else {}
        authority_mode = _text(interpretation_control.get("render_mode")).upper()

        # Interpretation is the only production-modality authority. The previous
        # active representation may be inherited only for a proven artifact
        # continuation; ordinary CONTINUE must not turn text into a stale graph.
        representation = semantic_representation or lexical_representation or "text"
        if (
            representation == "text"
            and authority_mode == "ARTIFACT_CONTINUATION"
            and bool(interpretation_control.get("render_authorized"))
            and isinstance(active, dict)
        ):
            representation = _text(active.get("representation") or "text").lower() or "text"

        if semantic_task.get("operation"):
            operation = _text(semantic_task.get("operation")).lower()
        else:
            operation = self._operation(text, representation)
        if semantic_task.get("goal"):
            goal = _text(semantic_task.get("goal")).lower()
        else:
            goal = self._goal(operation, representation)
        semantic_object = _text(semantic_task.get("object"))
        live_scene = semantic_result.get("live_scene") if isinstance(semantic_result.get("live_scene"), dict) else {}
        semantic_topic = _text(
            semantic_task.get("topic")
            or semantic_result.get("canonical_topic")
            or live_scene.get("topic")
            or semantic_result.get("active_topic")
        )
        generic_objects = {"", "action", "text", representation}
        if authority_mode == "ARTIFACT_CONTINUATION" and bool(interpretation_control.get("render_authorized")) and active and semantic_object.lower() in generic_objects:
            object_name = _text(active.get("object")) or semantic_topic or self._object(text, representation)
        elif semantic_object and semantic_object.lower() not in generic_objects:
            object_name = semantic_object
        else:
            object_name = semantic_topic or self._object(text, representation)
        topic = semantic_topic or object_name or _text(request)[:120]
        attributes: Dict[str, Any] = {}

        semantic_understanding = semantic_result.get("semantic_understanding") if isinstance(semantic_result.get("semantic_understanding"), dict) else {}
        semantic_representation_state = semantic_understanding.get("representation") if isinstance(semantic_understanding.get("representation"), dict) else {}
        semantic_mode = _text(
            semantic_result.get("visual_production_mode")
            or semantic_representation_state.get("production_mode")
        ).lower()

        if representation == "image":
            # Interpretation owns the semantic production decision. Executor only
            # executes it; it does not classify the user's wording again.
            attributes["visual_production_mode"] = (
                semantic_mode
                if semantic_mode in {"image_generation", "image_present"}
                else "image_generation"
                if semantic_result.get("operation") in {"build", "visualize"}
                else "image_present"
            )
        elif representation == "diagram":
            attributes["visual_production_mode"] = "diagram"
        elif representation == "graph":
            attributes["visual_production_mode"] = "graph"
        elif representation == "table":
            attributes["visual_production_mode"] = "table"
        elif representation == "code":
            # Code is a structured presentation too. Keep it explicit so the
            # provider is instructed to materialize a real CodeBlock instead
            # of returning only a prose introduction.
            attributes["visual_production_mode"] = "code"
        elif representation == "formula":
            # Formula follows the same explicit structured-output contract.
            attributes["visual_production_mode"] = "formula"
        elif representation == "link":
            attributes["visual_production_mode"] = "link"

        if representation == "link" and ("telegram" in text or "телеграм" in text) and not self._telegram_target_present(text):
            attributes["telegram_pending"] = True
            attributes["pending_question"] = "Какой Telegram нужен: официальный канал, чат или пользовательский аккаунт?"

        intent = self._make_intent(operation, object_name, representation, goal, topic, attributes)
        intent.update({
            "requested_outputs": list(semantic_result.get("requested_outputs") or (["text"] if representation == "text" else ["text", representation])),
            "production_representation_locked": bool(semantic_result.get("production_representation_locked", False)),
            "render_authorized": bool(interpretation_control.get("render_authorized")),
            "render_mode": authority_mode or "TEXT_ONLY",
            "interpretation_control": _compact(interpretation_control, max_depth=3, max_items=8),
            "semantic_understanding": _compact(semantic_result.get("semantic_understanding") or {}, max_depth=5, max_items=10),
            "semantic_request": _text(
                semantic_result.get("semantic_request")
                or _as_dict(semantic_result.get("semantic_understanding")).get("provider", {}).get("semantic_request")
                or dialogue.get("resolved_request")
                or self.request
            ),
            "semantic_result": semantic_result,
        })
        return intent

    @staticmethod
    def _make_intent(operation: str, object_name: str, representation: str, goal: str, topic: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "operation": _text(operation) or "answer",
            "object": _text(object_name) or representation,
            "representation": _text(representation) or "text",
            "goal": _text(goal) or "answer",
            "topic": _text(topic),
            "attributes": attributes,
        }

    @staticmethod
    def _representation(text: str) -> str:
        if re.search(r"\b(код|python|пайтон|скрипт)\b", text):
            return "code"
        if re.search(r"\b(ссыл\w*|url|link)\b", text):
            return "link"
        if re.search(r"\b(нарисуй|изобрази|сгенерируй|создай)\b", text) or "картинк" in text or "изображени" in text or "портрет" in text:
            return "image"
        if re.search(r"\b(график|графика|кривую|кривая)\b", text):
            return "graph"
        if re.search(r"\b(таблиц\w*|табличк\w*)\b", text):
            return "table"
        if re.search(r"\b(схем\w*|блок-схем\w*)\b", text):
            return "diagram"
        if re.search(r"\b(формул\w*|уравнени\w*)\b", text):
            return "formula"
        return "text"

    @staticmethod
    def _operation(text: str, representation: str) -> str:
        if representation == "link":
            return "retrieve"
        if any(w in text for w in ("измени", "исправь", "переделай", "добавь", "убери")):
            return "modify"
        if representation in _STRUCTURED_TYPES:
            return "build"
        if any(w in text for w in ("объясни", "расскажи", "почему", "что такое")):
            return "explain"
        return "answer"

    @staticmethod
    def _goal(operation: str, representation: str) -> str:
        if operation == "retrieve":
            return "obtain"
        if representation in _STRUCTURED_TYPES:
            return "present"
        if operation == "explain":
            return "understand"
        return "answer"

    @staticmethod
    def _object(text: str, representation: str) -> str:
        if representation == "link" and ("telegram" in text or "телеграм" in text):
            return "telegram_link"
        return {
            "code": "source_code",
            "image": "illustration",
            "graph": "graph",
            "table": "table",
            "diagram": "diagram",
            "formula": "formula",
            "link": "link",
        }.get(representation, "text")

    @staticmethod
    def _telegram_kind(text: str) -> str:
        if "канал" in text:
            return "channel"
        if "чат" in text:
            return "chat"
        if "пользователь" in text or "аккаунт" in text:
            return "user"
        if "официаль" in text:
            return "official"
        return "unspecified"

    @staticmethod
    def _telegram_target_present(text: str) -> bool:
        if re.search(r"https?://t\.me/[a-z0-9_]+", text):
            return True
        if re.search(r"@[a-z0-9_]{4,}", text):
            return True
        generic = {"дай", "ссылку", "на", "telegram", "телеграм"}
        return bool(set(_tokens(text)) - generic)


class ProcessorScene:
    def __init__(self, state: dict, user_id: str, request: str):
        self.state = state
        self.user_id = _text(user_id)
        self.request = _text(request)
        self.interpreter = SequentialInterpretation()
        self._render_omissions: list[dict[str, Any]] = []

    def prepare(self) -> MachineRequest:
        dialogue = self.interpreter.dialogue(self.request, self.state)
        intent = self.interpreter.intent(self.request, self.state, dialogue)
        relation = dialogue["relation"]

        requested_outputs = ["text"]
        required_artifacts: List[str] = []
        representation = intent["representation"]
        authorized_outputs = [
            _text(x).lower() for x in (intent.get("requested_outputs") or [])
            if _text(x).strip()
        ]
        if bool(intent.get("render_authorized")) and authorized_outputs:
            for item in authorized_outputs:
                if item != "text" and item in _STRUCTURED_TYPES and item not in requested_outputs:
                    requested_outputs.append(item)
        elif representation in _STRUCTURED_TYPES:
            # Fallback only for an explicitly structured current-turn request.
            if representation != "formula" and representation not in requested_outputs:
                requested_outputs.append(representation)
            if representation == "formula" and representation not in requested_outputs:
                requested_outputs.append("formula")

        if representation in _STRUCTURED_TYPES and representation in requested_outputs:
            required_artifacts.append(representation)

        if intent["attributes"].get("telegram_pending"):
            # The answer is a clarification; the representation remains text
            # for this turn and pending state is persisted for the next turn.
            requested_outputs = ["text"]
            required_artifacts = []

        active_task = self.state.get("april_active_task") if isinstance(self.state.get("april_active_task"), dict) else {}
        pending_task = self.state.get("april_pending_task") if isinstance(self.state.get("april_pending_task"), dict) else {}

        resolved_request = _text(dialogue.get("resolved_request") or self.request)
        if dialogue["pending_resolved"] and pending_task and not dialogue.get("resolved_request"):
            base_topic = _text(pending_task.get("topic") or pending_task.get("representation"))
            resolved_request = f"Продолжение задания: {base_topic}. Ответ пользователя: {self.request}"

        semantic_result = dialogue.get("semantic_result") if isinstance(dialogue.get("semantic_result"), dict) else {}
        dialogue_memory = build_dialogue_memory_bridge(
            self.user_id,
            query=self.request,
            limit=6,
            relation=relation,
            target_sequence_id=_text(dialogue.get("target_sequence_id") or dialogue.get("sequence_id")),
        )

        continuation_analysis = semantic_result.get("continuation_content_analysis") if isinstance(semantic_result.get("continuation_content_analysis"), dict) else {}
        dialogue_strategy = semantic_result.get("dialogue_strategy") if isinstance(semantic_result.get("dialogue_strategy"), dict) else {}
        resolved_entity = _text(
            semantic_result.get("resolved_entity")
            or continuation_analysis.get("active_entity")
            or dialogue.get("resolved_reference")
            or self.state.get("april_active_entity")
        )

        # For NEW turns, the current semantic task is authoritative; do not reuse
        # the previous topic as the provider-facing active task.
        turn_active_task = active_task if relation in {"CONTINUE", "RECALL"} else {
            "operation": intent.get("operation"),
            "object": intent.get("object"),
            "representation": intent.get("representation"),
            "goal": intent.get("goal"),
            "topic": dialogue.get("canonical_topic") or intent.get("topic") or intent.get("object"),
        }

        render_mode = _text(intent.get("render_mode") or "TEXT_ONLY").upper()
        selected_artifact = semantic_result.get("target_artifact") if isinstance(semantic_result.get("target_artifact"), dict) else {}
        selected_artifact = dict(selected_artifact)
        selected_artifact_block = selected_artifact.get("render_block") if isinstance(selected_artifact.get("render_block"), dict) else {}
        live_visual_scene = (
            self.state.get("active_visual_scene")
            if isinstance(self.state.get("active_visual_scene"), dict)
            else self.state.get("current_visual_scene")
            if isinstance(self.state.get("current_visual_scene"), dict)
            else {}
        )
        artifact_context_only = (
            render_mode == "ARTIFACT_CONTINUATION"
            and bool(intent.get("render_authorized"))
        )
        artifact_visual_context = {}
        if artifact_context_only:
            artifact_visual_context = {
                "relation": relation,
                "mode": "ARTIFACT_CONTINUATION",
                "selected_artifact": _compact(selected_artifact, max_depth=4, max_items=6),
                "render_block": _compact(selected_artifact_block, max_depth=5, max_items=8),
            }
            if live_visual_scene:
                compact_scene = {
                    "scene_id": live_visual_scene.get("scene_id"),
                    "topic": live_visual_scene.get("topic"),
                    "render_block_types": live_visual_scene.get("render_block_types") or [],
                    "render_blocks": [
                        _compact(block, max_depth=5, max_items=8)
                        for block in (live_visual_scene.get("render_blocks") or live_visual_scene.get("blocks") or [])[:2]
                        if isinstance(block, dict)
                        and _text(block.get("type") or block.get("artifact_type") or "").lower() in _STRUCTURED_TYPES
                    ],
                }
                artifact_visual_context["active_visual_scene"] = compact_scene

        context = {
            "relation": relation,
            "continuation": bool(dialogue["continuation"]),
            "reference": bool(dialogue["reference"]),
            "dependency": dialogue["dependency"],
            "anchor": dialogue["anchor"],
            "active_task": _compact(turn_active_task),
            "pending_task": _compact(pending_task),
            "active_entity": resolved_entity,
            "semantic_request": _text(
                semantic_result.get("semantic_request")
                or _as_dict(semantic_result.get("semantic_understanding")).get("provider", {}).get("semantic_request")
                or resolved_request
            ),
            "semantic_understanding": _compact(semantic_result.get("semantic_understanding") or {}, max_depth=5, max_items=10),
            "continuation_content_analysis": _compact(continuation_analysis, max_depth=4, max_items=8),
            "dialogue_strategy": _compact(dialogue_strategy, max_depth=3, max_items=8),
            "live_scene": _compact(
                semantic_result.get("live_scene")
                or self.state.get("live_dialogue_scene")
                or self.state.get("scene_state")
                or {},
                max_depth=5,
                max_items=12,
            ),
            "dialogue_vector": _compact(
                semantic_result.get("dialogue_vector") or {},
                max_depth=5,
                max_items=12,
            ),
            "last_user_turn": _compact(self.state.get("last_user_turn", "")),
            "last_april_turn": _compact(self.state.get("last_april_turn", "")),
            "canonical_topic": _compact(dialogue.get("canonical_topic")),
            "sequence_id": _text(dialogue.get("sequence_id")),
            "target_sequence_id": _text(
                dialogue.get("sequence_id") or dialogue.get("target_sequence_id")
            ),
            "resolved_reference": _compact(dialogue.get("resolved_reference")),
            "selected_memory_index": dialogue.get("selected_memory_index", -1),
            "selected_memory_operand": _compact(dialogue.get("selected_memory_operand") or {}),
            "dialogue_trajectory": _compact(dialogue.get("trajectory") or {}),
            "active_dialogue_sequence": _compact(
                dialogue_memory.get("active_sequence") or {}
                if relation in {"CONTINUE", "RECALL"} and not artifact_context_only else {},
                max_depth=3,
                max_items=6,
            ),
            "seven_day_dialogue_memory": _compact(
                dialogue_memory if relation in {"CONTINUE", "RECALL"} and not artifact_context_only else {
                    "window_days": 7,
                    "turn_count_7d": dialogue_memory.get("turn_count_7d", 0),
                    "evidence_only": True,
                    "retrieval_mode": "artifact" if artifact_context_only else "none",
                    "selected_artifact": selected_artifact if artifact_context_only else {},
                },
                max_depth=5,
                max_items=6,
            ),
        }

        visual_mode = _text(intent["attributes"].get("visual_production_mode"))
        if not visual_mode:
            visual_mode = "text"


        # For a proven artifact continuation, the previous artifact is the
        # operand. A live sequence may contain a newer unrelated turn, so its
        # full conversational turns are intentionally withheld from Provider.

        # One continuous response budget for every representation.
        # The processor must not predict answer length from the renderer.
        # OpenAI may use any amount up to the canonical 8000-token ceiling;
        # the complete result is then passed to SceneContract and Web.
        output_budget = 8000

        dialogue_contract = {
            "version": "april_dialogue_contract_v2_semantic_trajectory",
            "relation": relation,
            "continuation": bool(dialogue["continuation"]),
            "reference_to_previous": bool(dialogue["reference"]),
            "context_dependency": dialogue["dependency"],
            "active_task": _compact(turn_active_task),
            "pending_task": _compact(pending_task),
            "active_entity": resolved_entity,
            "semantic_request": _text(
                semantic_result.get("semantic_request")
                or _as_dict(semantic_result.get("semantic_understanding")).get("provider", {}).get("semantic_request")
                or resolved_request
            ),
            "semantic_understanding": _compact(semantic_result.get("semantic_understanding") or {}, max_depth=5, max_items=10),
            "continuation_content_analysis": _compact(continuation_analysis, max_depth=4, max_items=8),
            "dialogue_strategy": _compact(dialogue_strategy, max_depth=3, max_items=8),
            "resolved_request": resolved_request,
            "canonical_topic": _compact(dialogue.get("canonical_topic")),
            "sequence_id": _text(dialogue.get("sequence_id")),
            "target_sequence_id": _text(dialogue.get("sequence_id") or dialogue.get("target_sequence_id")),
            "resolved_reference": _compact(dialogue.get("resolved_reference")),
            "selected_memory_index": dialogue.get("selected_memory_index", -1),
            "selected_memory_operand": _compact(dialogue.get("selected_memory_operand") or {}),
            "trajectory": _compact(dialogue.get("trajectory") or {}),
            "selected_artifact": _compact(selected_artifact, max_depth=5, max_items=6) if artifact_context_only else {},
            "active_dialogue_sequence": _compact(
                dialogue_memory.get("active_sequence") or {}
                if relation in {"CONTINUE", "RECALL"} and not artifact_context_only else {},
                max_depth=4,
                max_items=6,
            ),
            "seven_day_memory_turns": _compact(
                dialogue_memory.get("active_sequence_turns") or []
                if relation == "CONTINUE" and not artifact_context_only else [],
                max_depth=5,
                max_items=6,
            ),
            "relevant_7d_turns": _compact(
                dialogue_memory.get("relevant_7d_turns") or []
                if relation == "RECALL" else [],
                max_depth=5,
                max_items=4,
            ),
            "semantic_authority": True,
        }

        memory_packet = {
            "mode": (
                "artifact_context" if artifact_context_only
                else "active_sequence" if relation == "CONTINUE"
                else "selected_7d_thread" if relation == "RECALL"
                else "current_turn_only"
            ),
            "active_topic": _compact(dialogue.get("canonical_topic")) if relation != "NEW" else "",
            "active_goal": _compact(intent.get("goal")) if relation != "NEW" else "",
            "active_task": _compact(turn_active_task) if relation != "NEW" else {},
            "semantic_request": _text(
                semantic_result.get("semantic_request")
                or _as_dict(semantic_result.get("semantic_understanding")).get("provider", {}).get("semantic_request")
                or resolved_request
            ),
            "semantic_understanding": _compact(semantic_result.get("semantic_understanding") or {}, max_depth=5, max_items=10),
            "pending_task": _compact(pending_task) if pending_task else {},
            "last_artifact_type": _state_artifact_type(self.state) if relation == "CONTINUE" and render_mode == "ARTIFACT_CONTINUATION" else "",
            "selected_artifact": _compact(selected_artifact, max_depth=5, max_items=6) if artifact_context_only else {},
            "dialogue_sequence": _compact(dialogue_memory.get("active_sequence") or {}) if relation in {"CONTINUE", "RECALL"} and not artifact_context_only else {},
            "dialogue_memory": _compact(dialogue_memory) if relation in {"CONTINUE", "RECALL"} and not artifact_context_only else {
                "window_days": 7,
                "turn_count_7d": dialogue_memory.get("turn_count_7d", 0),
                "evidence_only": True,
                "retrieval_mode": "artifact" if artifact_context_only else "none",
                "selected_artifact": _compact(selected_artifact, max_depth=5, max_items=6) if artifact_context_only else {},
            },
            "interpretation_control": _compact(semantic_result.get("interpretation_control") or {}, max_depth=3, max_items=8),
            "window_days": 7,
            "authenticated_user_scope": {
                "user_id": self.user_id,
                "conversation_id": dialogue_memory.get("conversation_id"),
            },
        }

        request = MachineRequest(
            goal=intent["goal"],
            intent={
                "type": representation,
                "operation": intent["operation"],
                "object": intent["object"],
                "goal": intent["goal"],
                "normalized_text": self.request,
                "resolved_request": resolved_request,
                "semantic_request": _text(
                    semantic_result.get("semantic_request")
                    or _as_dict(semantic_result.get("semantic_understanding")).get("provider", {}).get("semantic_request")
                    or resolved_request
                ),
                "semantic_understanding": _compact(semantic_result.get("semantic_understanding") or {}, max_depth=5, max_items=10),
                "attributes": _compact(intent.get("attributes") or {}),
            },
            conversation={
                "current_request": self.request,
                "resolved_request": resolved_request,
                "dialogue_contract": dialogue_contract,
                "turn_meaning": context,
                "active_task": _compact(turn_active_task),
                "pending_task": _compact(pending_task),
                "live_scene": _compact(
                    semantic_result.get("live_scene")
                    or context.get("live_scene")
                    or self.state.get("live_dialogue_scene")
                    or {},
                    max_depth=5,
                    max_items=12,
                ),
                "dialogue_vector": _compact(
                    semantic_result.get("dialogue_vector")
                    or context.get("dialogue_vector")
                    or {},
                    max_depth=5,
                    max_items=12,
                ),
            },
            memory=memory_packet,
            visual_context=artifact_visual_context,
            requested_outputs=requested_outputs,
            required_artifacts=required_artifacts,
            required_competencies=[intent["operation"], representation],
            routing={
                "decision_owner": "QUANTUM_PROCESSOR",
                "route": "provider",
                "single_route": True,
                "engine": "processor->openai->scene",
            },
            constraints={
                "one_provider_call": True,
                "provider_input_token_budget": 900,
                "metadata": {
                    "identity_scope": {"user_id": self.user_id},
                    "visual_production_mode": visual_mode,
                    "semantic_request": _text(
                        semantic_result.get("semantic_request")
                        or _as_dict(semantic_result.get("semantic_understanding")).get("provider", {}).get("semantic_request")
                        or resolved_request
                    ),
                    "semantic_understanding": _compact(semantic_result.get("semantic_understanding") or {}, max_depth=5, max_items=10),
                    "dialogue_relation": relation,
                    "fast_path": True,
                    "do_not_reinterpret": True,
                    "interpretation_control": _compact(semantic_result.get("interpretation_control") or {}, max_depth=4, max_items=10),
                    "render_authorized": bool(intent.get("render_authorized")),
                    "render_mode": _text(intent.get("render_mode") or "TEXT_ONLY"),
                    "artifact_context_only": artifact_context_only,
                    "selected_artifact": _compact(selected_artifact, max_depth=5, max_items=6) if artifact_context_only else {},
                },
                "representation_plan": {
                    "representation": representation,
                    "visual_production_mode": visual_mode,
                    "renderer": _RENDERER_REGISTRY.get(representation, "MessageTextBlock"),
                    "requested_outputs": list(requested_outputs),
                    "authorized": bool(intent.get("render_authorized")),
                    "render_mode": _text(intent.get("render_mode") or "TEXT_ONLY"),
                    "artifact_context_only": artifact_context_only,
                },
                "scene_composition": requested_outputs,
            },
        )
        setattr(request, "dialogue_contract", dialogue_contract)
        setattr(request, "turn_meaning", context)
        setattr(request, "response_output_tokens", output_budget)
        setattr(request, "quantum_state", {
            "version": "april_processor_v2_semantic_trajectory",
            "relation": relation,
            "continuation": bool(dialogue["continuation"]),
            "reference": bool(dialogue["reference"]),
            "dependency": dialogue["dependency"],
            "resolved_request": resolved_request,
            "canonical_topic": dialogue.get("canonical_topic", ""),
            "resolved_reference": dialogue.get("resolved_reference", ""),
            "selected_memory_index": dialogue.get("selected_memory_index", -1),
            "selected_memory_operand": _compact(dialogue.get("selected_memory_operand") or {}),
            "trajectory": _compact(dialogue.get("trajectory") or {}),
            "sequence_id": _text(dialogue.get("sequence_id")),
            "active_entity": resolved_entity,
            "continuation_content_analysis": _compact(continuation_analysis, max_depth=4, max_items=8),
            "dialogue_strategy": _compact(dialogue_strategy, max_depth=3, max_items=8),
            "sequence_continuation_authorized": bool(dialogue.get("sequence_continuation_authorized")),
            "interpretation_control": _compact(semantic_result.get("interpretation_control") or {}, max_depth=4, max_items=10),
            "render_authorized": bool(intent.get("render_authorized")),
            "render_mode": _text(intent.get("render_mode") or "TEXT_ONLY"),
            "provider_calls": 1,
            "single_route": True,
            "interpretation_owned_by": "QUANTUM_PROCESSOR",
        })

        return request

    def build_scene(self, request: MachineRequest, provider_contract: dict) -> tuple[MachineResponse, Any, Any]:
        machine_payload = provider_contract.get("machine_response") if isinstance(provider_contract, dict) else {}
        if not isinstance(machine_payload, dict):
            raise RuntimeError("PROVIDER_MACHINE_RESPONSE_MISSING")

        # Keep only actual provider blocks; normalize metadata without changing
        # the representation chosen by the processor.
        self._render_omissions = []
        blocks = self._canonicalize_blocks(machine_payload.get("render_blocks") or [], request)
        answer = _text(machine_payload.get("answer") or machine_payload.get("content"))
        if not answer:
            raise RuntimeError("EMPTY_PROVIDER_ANSWER")
        if not blocks:
            blocks = [self._text_block(answer)]

        # Provider cannot invent another representation that the processor did
        # not request. For text-only turns, keep text only.
        requested = {str(x).lower() for x in request.requested_outputs}
        if requested == {"text"}:
            blocks = [b for b in blocks if _text(b.get("type") or "").lower() in {"text", "markdown"}]
            if not blocks:
                blocks = [self._text_block(answer)]

        response = MachineResponse(
            answer=answer,
            content=_text(machine_payload.get("content") or answer),
            response=_text(machine_payload.get("response") or answer),
            summary=_text(machine_payload.get("summary") or answer),
            explanation=_text(machine_payload.get("explanation")),
            confidence=float(machine_payload.get("confidence") or 1.0),
            render_blocks=blocks,
            artifacts_payload=list(machine_payload.get("artifacts") or []),
            artifacts=[],
            scene=dict(machine_payload.get("scene") or {}),
            scene_blueprint=dict(machine_payload.get("scene_blueprint") or {}),
            scene_plan=list(machine_payload.get("scene_plan") or request.requested_outputs or ["text"]),
            render_priority=list(machine_payload.get("render_priority") or request.requested_outputs or ["text"]),
            metadata=dict(machine_payload.get("metadata") or {}),
            continuation=bool(request.quantum_state.get("continuation")),
        )
        response.scene_id = f"{request.request_id}:scene"
        response.turn_id = str(self.state.get("april_turn_id", 0) + 1)
        response.flow_id = str(request.request_id)
        response.topic_group = _text(request.intent.get("object") or request.intent.get("type"))
        response.metadata.update({
            "processor_version": PROCESSOR_VERSION,
            "decision_owner": "QUANTUM_PROCESSOR",
            "canonical_representation": request.intent.get("type"),
            "dialogue_relation": request.dialogue_contract.get("relation"),
            "continuation": bool(request.quantum_state.get("continuation")),
            "single_route": True,
            "provider_calls": 1,
            "fast_path": True,
            "web_signal_source": "SCENE_CONTRACT",
            "semantic_scene_state": {
                "relation": request.dialogue_contract.get("relation"),
                "continuation": bool(request.quantum_state.get("continuation")),
                "resolved_request": request.intent.get("resolved_request"),
                "representation": request.intent.get("type"),
                "active_task": _compact(request.conversation.get("active_task")),
            },
        })

        scene = build_machine_scene(response)
        scene.contract = build_scene_contract(scene)
        contract = scene.contract

        # One canonical Web signal: the same list is exported as `blocks` and
        # `render_blocks` for compatibility, with the same object content.
        contract.metadata = dict(contract.metadata or {})
        contract.metadata["processor_interpretation"] = {
            "relation": request.dialogue_contract.get("relation"),
            "representation": request.intent.get("type"),
            "operation": request.intent.get("operation"),
            "goal": request.intent.get("goal"),
            "resolved_request": request.intent.get("resolved_request"),
        }
        contract.metadata["web_delivery"] = {
            "version": "april_web_scene_signal_v1",
            "source": "SCENE_CONTRACT",
            "render_blocks_canonical": True,
            "renderer_reinterpretation": False,
            "duplicate_rebuild": False,
        }
        contract.blocks = list(contract.render_blocks)
        contract.signal = {
            "signal_type": "scene",
            "signal_version": "april_web_scene_signal_v1",
            "scene_id": contract.scene_id,
            "turn_id": contract.turn_id,
            "continuation": contract.continuation,
            "single_response": True,
            "single_signal": True,
            "order": list(contract.order),
            "blocks": list(contract.render_blocks),
        }
        return response, scene, contract

    @staticmethod
    def _text_block(answer: str) -> Dict[str, Any]:
        return {
            "type": "text",
            "content": answer,
            "text": answer,
            "renderer": "MessageTextBlock",
            "viewer": "MessageTextBlock",
            "scene_contract": True,
            "human_visible": True,
        }

    def _canonicalize_blocks(self, raw_blocks: Sequence[Any], request: MachineRequest) -> List[Dict[str, Any]]:
        expected = set(str(x).lower() for x in request.requested_outputs)
        result: List[Dict[str, Any]] = []
        seen = set()
        structured = set(_STRUCTURED_TYPES) | {"audio", "video", "action", "file", "visual_context", "scene"}
        for raw in raw_blocks:
            if not isinstance(raw, dict):
                continue
            block = dict(raw)
            kind = _text(block.get("type") or block.get("artifact_type") or block.get("representation")).lower()
            if not kind:
                continue
            if kind not in expected and kind not in {"text", "markdown"}:
                continue

            canonical_payload = canonical_payload_for_block(block)
            block["type"] = kind
            block["renderer"] = _RENDERER_REGISTRY.get(kind, block.get("renderer") or "MessageTextBlock")
            block["viewer"] = block.get("viewer") or block["renderer"]
            if canonical_payload:
                block["payload"] = canonical_payload
            elif kind in structured:
                self._render_omissions.append({
                    "type": kind,
                    "reason": "missing_canonical_payload",
                    "block_id": _text(block.get("block_id") or block.get("id")),
                })
                continue

            if kind in structured:
                valid, reason = validate_render_block_payload(kind, block)
                if not valid:
                    self._render_omissions.append({
                        "type": kind,
                        "reason": reason,
                        "block_id": _text(block.get("block_id") or block.get("id")),
                    })
                    continue

            block["scene_contract"] = True
            block["block_id"] = block.get("block_id") or _stable_id(f"scene-{kind}", block.get("payload") or block.get("content"))
            sig = json.dumps({"type": kind, "payload": block.get("payload", {}), "content": block.get("content", "")}, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
            if sig in seen:
                continue
            seen.add(sig)
            block["sequence_index"] = len(result)
            result.append(block)
        return result



def _set_live_state(state: dict, request: MachineRequest, response: MachineResponse, contract: Any) -> None:
    dialogue = request.dialogue_contract or {}
    relation = _text(dialogue.get("relation")).upper() or "NEW"
    representation = _text(request.intent.get("type")).lower() or "text"
    operation = _text(request.intent.get("operation")) or "answer"
    goal = _text(request.intent.get("goal")) or "answer"
    topic = _text(dialogue.get("canonical_topic") or request.intent.get("object") or representation)

    state["april_turn_id"] = int(state.get("april_turn_id") or 0) + 1
    state["last_user_turn"] = request.conversation.get("current_request", "")
    state["last_april_turn"] = response.answer
    state["april_active_topic"] = topic
    state["april_active_goal"] = goal
    # The entity in the completed answer becomes the next-turn discourse anchor.
    # This is intentionally separate from the broader topic: a conversation can
    # stay on "Горбачёв" while the active entity becomes "Раиса Горбачёва".
    entity = _person_entity_from_answer(response.answer)
    if not entity:
        entity = _text(dialogue.get("resolved_entity") or dialogue.get("resolved_reference") or topic)
    state["april_active_entity"] = entity
    state["april_active_task"] = {
        "operation": operation,
        "object": topic,
        "representation": representation,
        "goal": goal,
        "topic": topic,
    }

    attrs = dict(request.intent.get("attributes") or {})
    if attrs.get("telegram_pending"):
        state["april_pending_task"] = {
            "active": True,
            "expected_input_type": "telegram_target_kind",
            "question": attrs.get("pending_question") or "Какой Telegram нужен: официальный канал, чат или пользовательский аккаунт?",
            "source_turn_id": state["april_turn_id"],
            "representation": "link",
            "operation": "retrieve",
            "object": "telegram_link",
            "goal": "obtain",
            "topic": "telegram_link",
        }
    elif relation == "CONTINUE" and state.get("april_pending_task"):
        state["april_pending_task"] = None
    else:
        state["april_pending_task"] = None

    blocks = list(getattr(contract, "render_blocks", []) or [])
    if blocks:
        state["last_artifact"] = {
            "type": _text(blocks[-1].get("type") or "text").lower(),
            "block_id": _text(blocks[-1].get("block_id")),
            "payload": _compact(blocks[-1].get("payload") or {}),
        }

    state["dialogue_vector"] = {
        **dict(state.get("dialogue_vector") or {}),
        **dict(dialogue),
        "three_way_relation": relation,
        "sequence_id": dialogue.get("sequence_id"),
        "target_sequence_id": dialogue.get("sequence_id"),
        "sequence_continuation_authorized": bool(dialogue.get("continuation")),
        "current_turn_authority": True,
        "historical_memory_is_evidence_only": True,
    }

    state["dialogue_resolution"] = {
        "authoritative": True,
        "relation": "CONTINUE" if relation == "CONTINUE" else "RECALL" if relation == "RECALL" else "NEW",
        "continuation": bool(dialogue.get("continuation")),
        "reference": bool(dialogue.get("reference_to_previous")),
        "context_dependency": dialogue.get("context_dependency"),
        "resolved_request": dialogue.get("resolved_request"),
        "resolved_reference": dialogue.get("resolved_reference", ""),
        "selected_memory_index": dialogue.get("selected_memory_index", -1),
        "selected_memory_operand": dialogue.get("selected_memory_operand") or {},
        "trajectory": dialogue.get("trajectory") or {},
        "source": "semantic_interpretation_layer",
    }

    state["april_live_context"] = {
        "version": "april_live_context_v1",
        "relation": relation,
        "active_topic": topic,
        "active_goal": goal,
        "active_task": _compact(state.get("april_active_task")),
        "pending_task": _compact(state.get("april_pending_task")),
        "last_user_turn": _text(state.get("last_user_turn")),
        "last_april_turn": _text(state.get("last_april_turn")),
        "active_entity": _text(state.get("april_active_entity")),
        "dialogue_strategy": _compact(dialogue.get("dialogue_strategy") if isinstance(dialogue, dict) else {}),
        "continuation_content_analysis": _compact(dialogue.get("continuation_content_analysis") if isinstance(dialogue, dict) else {}),
        "scene_id": _text(getattr(contract, "scene_id", "")),
        "render_types": [_text(b.get("type")).lower() for b in blocks if isinstance(b, dict)],
    }



async def _visual_input_context(path: str, request_text: str, state: dict) -> Dict[str, Any]:
    if not path:
        return {}
    try:
        from blocks.image_system import scan_image
        packet = await asyncio.to_thread(
            scan_image,
            path,
            user_request=request_text,
            state=state,
        )
        return _compact(packet, max_depth=3, max_items=4) or {}
    except Exception as exc:
        print("⚠️ APRIL VISUAL INPUT:", exc)
        return {"error": "visual_scan_failed"}


async def _materialize_image_if_requested(response: MachineResponse, request: MachineRequest, state: dict, user_id: str) -> None:
    representation = _text(request.intent.get("type")).lower()
    mode = _text((request.constraints.get("representation_plan") or {}).get("visual_production_mode")).lower()
    if representation != "image" or mode != "image_generation":
        return

    metadata = dict(response.metadata or {})

    # A complete Provider image payload is already renderable; preserve it and
    # do not force a second local generation step.
    for block in list(response.render_blocks or []):
        if not isinstance(block, dict):
            continue
        if _text(block.get("type") or block.get("artifact_type")).lower() not in {"image", "gallery"}:
            continue
        payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
        if any(payload.get(key) for key in ("src", "url", "image", "image_data_uri", "image_base64")):
            metadata["image_generation_status"] = "provider_artifact_preserved"
            response.metadata = metadata
            return

    spec = metadata.get("image_generation_spec")
    if not isinstance(spec, dict):
        # Some provider versions place the spec at top level.
        spec = (response.scene or {}).get("image_generation_spec") if isinstance(response.scene, dict) else None
    if not isinstance(spec, dict):
        metadata["image_generation_status"] = "missing_provider_spec"
        response.metadata = metadata
        return

    try:
        from blocks.C_APRIL_IMAGES_GENERATOR import generate_from_spec
        result = await generate_from_spec(spec, variant="provider_spec")
        if not result.get("success") or not result.get("image_bytes"):
            raise RuntimeError("IMAGE_ENGINE_EMPTY_RESULT")

        image_bytes = result["image_bytes"]
        artifact = result.get("artifact") if isinstance(result.get("artifact"), dict) else {}
        artifact_payload = artifact.get("payload") if isinstance(artifact.get("payload"), dict) else {}
        base64_value = artifact_payload.get("image_base64") or ""
        data_uri = artifact_payload.get("image_data_uri") or ""
        if not data_uri and base64_value:
            data_uri = f"data:image/png;base64,{base64_value}"
        # Machine generation instructions are never part of the canonical
        # human-visible image payload. Keep prompt/spec server-side only.
        payload = {
            "kind": "generated_image",
            "artifact_type": "image",
            "mime_type": "image/png",
            "width": result.get("width"),
            "height": result.get("height"),
            "src": data_uri,
            "url": data_uri,
            "image": data_uri,
            "image_base64": base64_value or None,
            "image_data_uri": data_uri or None,
            "images": [],
            "engine": "April Images Generation",
            "backend": result.get("backend"),
        }
        direct = payload.get("src") or payload.get("image_data_uri")
        if direct:
            payload["images"] = [{
                "src": direct,
                "url": direct,
                "image": direct,
                "mime_type": "image/png",
                "width": result.get("width"),
                "height": result.get("height"),
                "title": "Image",
                "alt": "Сгенерированное изображение",
            }]

        response.render_blocks = [
            block for block in list(response.render_blocks or [])
            if _text(block.get("type") if isinstance(block, dict) else "").lower() not in {"image", "gallery"}
        ]
        response.render_blocks.append({
            "type": "image",
            "artifact_type": "image",
            "renderer": "GalleryBlock",
            "viewer": "GalleryBlock",
            "payload": payload,
            "scene_contract": True,
            "human_visible": True,
            "block_id": _stable_id("scene-image", payload),
        })
        metadata.update({
            "image_generation_status": "success",
            "image_generation_engine": "C_APRIL_IMAGES_GENERATOR",
            "image_generation_backend": result.get("backend"),
            "image_generation_provider_calls_added": 0,
        })
        response.metadata = metadata
        state["last_image_png"] = image_bytes
        state["image_generation_spec"] = _compact(spec)
    except Exception as exc:
        metadata.update({"image_generation_status": "failed", "image_generation_error": str(exc)})
        response.metadata = metadata
        print("⚠️ APRIL IMAGE ENGINE:", exc)

async def execute(user_id, chat_id=None, text="", run_with_activity: Optional[Callable[..., Awaitable[Any]]] = None, **kwargs):
    request_text = _text(text)
    if not request_text:
        raise ValueError("EMPTY_REQUEST")

    state = get_state(user_id)
    if not isinstance(state, dict):
        raise RuntimeError("STATE_UNAVAILABLE")

    processor = ProcessorScene(state, _text(user_id), request_text)
    request = processor.prepare()

    visual_input_path = _text(kwargs.get("visual_input_path"))
    if visual_input_path:
        request.visual_context = await _visual_input_context(visual_input_path, request_text, state)
        request.conversation["visual_input_present"] = True
    else:
        request.visual_context = {}

    print("🧬 APRIL EXECUTOR BUILD:", PROCESSOR_VERSION)
    print("🧭 APRIL FLOW:", "INPUT → INTERPRETATION+LIVE_MEMORY → OPENAI → SCENE → WEB")
    print("🧠 APRIL INTERPRETATION:", _compact(request.intent))
    print("🧠 APRIL DIALOGUE:", _compact(request.dialogue_contract))

    started = time.perf_counter()
    if run_with_activity:
        try:
            activity_result = run_with_activity()
            if hasattr(activity_result, "__await__"):
                await activity_result
        except Exception:
            pass

    # Exactly one provider call. generate_text remains the owner of the OpenAI
    # transport and now offloads its synchronous SDK call from the event loop.
    provider_contract = await generate_text(request)
    provider_ms = round((time.perf_counter() - started) * 1000, 1)

    # Provider returns the image plan; the local image engine materializes it
    # before the processor creates the final SceneContract. No second provider.
    machine_preview = provider_contract.get("machine_response") if isinstance(provider_contract, dict) else {}
    if isinstance(machine_preview, dict):
        machine_preview = _bridge_provider_artifacts(machine_preview)
        preview_response = MachineResponse(
            answer=_text(machine_preview.get("answer")),
            content=_text(machine_preview.get("content")),
            response=_text(machine_preview.get("response")),
            summary=_text(machine_preview.get("summary")),
            confidence=float(machine_preview.get("confidence") or 1.0),
            render_blocks=list(machine_preview.get("render_blocks") or []),
            artifacts_payload=list(machine_preview.get("artifacts_payload") or machine_preview.get("artifacts") or []),
            scene=dict(machine_preview.get("scene") or {}),
            metadata=dict(machine_preview.get("metadata") or {}),
        )
        await _materialize_image_if_requested(preview_response, request, state, _text(user_id))
        machine_preview["render_blocks"] = list(preview_response.render_blocks or [])
        machine_preview["metadata"] = dict(preview_response.metadata or {})
        provider_contract["machine_response"] = machine_preview

    response, scene, contract = processor.build_scene(request, provider_contract)
    response.metadata["timing"] = {"provider_ms": provider_ms}

    _set_live_state(state, request, response, contract)

    # One state/scene persistence call. `update_scene_context` is the canonical
    # memory writer; no semantic matrix or second persistence pass is called.
    try:
        update_scene_context(
            user_id,
            contract,
            current_request=request_text,
            answer=response.answer,
            internal_context=bool(kwargs.get("internal_context", False)),
            persist=False,
        )

        # Persistence is durability work, not response work. Keep it off the
        # critical path; the next turn still sees the in-memory canonical state.
        uid = _text(user_id)
        previous = _PERSIST_TASKS.get(uid)
        if previous is None or previous.done():
            task = asyncio.create_task(asyncio.to_thread(persist_state, uid))
            task.add_done_callback(_consume_persist_result)
            _PERSIST_TASKS[uid] = task
    except Exception as exc:
        print("⚠️ APRIL SCENE MEMORY WRITE:", exc)

    print("✅ APRIL WEB SCENE:", {
        "scene_id": _text(getattr(contract, "scene_id", "")),
        "relation": _text(request.dialogue_contract.get("relation")),
        "blocks": [_text(b.get("type")).lower() for b in list(getattr(contract, "render_blocks", []) or []) if isinstance(b, dict)],
        "provider_ms": provider_ms,
    })

    return {
        "transport_contract": "scene_first",
        "provider_contract": "fiber_v6_quantum",
        "machine_request": request,
        "machine_response": response,
        "machine_scene": scene,
        "scene_contract": contract,
        "answer": response.answer,
        "content": response.content,
        "summary": response.summary,
        "render_blocks": list(getattr(contract, "render_blocks", []) or []),
        "artifacts": list(getattr(response, "artifacts_payload", []) or []),
        "single_route": True,
        "provider_calls_per_request": 1,
        "quantum_state": getattr(request, "quantum_state", {}),
        "visible_answer_guaranteed": True,
        "artifact_preservation": True,
        "web_delivery": {
            "version": "april_web_scene_signal_v1",
            "target": "AprilWeb",
            "transport": "SceneContract",
            "single_visible_stream": True,
            "scene_contract": contract,
            "render_blocks": list(getattr(contract, "render_blocks", []) or []),
        },
    }
