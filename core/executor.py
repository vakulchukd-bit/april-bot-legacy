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
from blocks.provider_router import generate_text
from blocks.state_manager import get_state, update_scene_context, persist_state

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
    """Single cheap interpretation pass; memory is state, not a classifier."""

    def dialogue(self, request: str, state: dict) -> Dict[str, Any]:
        current = request.lower().strip()
        pending = state.get("april_pending_task")

        if isinstance(pending, dict) and pending.get("active"):
            if any(current.startswith(marker) for marker in _NEW_TOPIC_MARKERS):
                return {
                    "relation": "NEW",
                    "continuation": False,
                    "reference": False,
                    "dependency": "independent",
                    "anchor": "none",
                    "pending_resolved": False,
                }
            return {
                "relation": "CONTINUE",
                "continuation": True,
                "reference": False,
                "dependency": "pending",
                "anchor": "pending_task",
                "pending_resolved": True,
            }

        if state.get("last_artifact") is not None and any(form in current for form in _ARTIFACT_REFERENCE_FORMS):
            return {
                "relation": "CONTINUE",
                "continuation": True,
                "reference": True,
                "dependency": "artifact",
                "anchor": "last_artifact",
                "pending_resolved": False,
            }

        if state.get("april_active_task") and (
            current.startswith(_FOLLOWUP_PREFIXES)
            or (len(_tokens(current)) <= 3 and any(t in _SHORT_PENDING_WORDS for t in _tokens(current)))
        ):
            return {
                "relation": "CONTINUE",
                "continuation": True,
                "reference": False,
                "dependency": "continuation",
                "anchor": "active_task",
                "pending_resolved": False,
            }

        return {
            "relation": "NEW",
            "continuation": False,
            "reference": False,
            "dependency": "independent",
            "anchor": "none",
            "pending_resolved": False,
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

        representation = self._representation(text)
        if dialogue["continuation"] and active and representation == "text":
            representation = _text(active.get("representation") or "text").lower() or "text"

        operation = self._operation(text, representation)
        goal = self._goal(operation, representation)
        object_name = self._object(text, representation)
        topic = object_name or _text(request)[:120]
        attributes: Dict[str, Any] = {}

        if representation == "image":
            attributes["visual_production_mode"] = "image_generation" if any(w in text for w in ("нарисуй", "сгенерируй", "создай")) else "image_present"
        elif representation == "diagram":
            attributes["visual_production_mode"] = "diagram"
        elif representation == "graph":
            attributes["visual_production_mode"] = "graph"
        elif representation == "table":
            attributes["visual_production_mode"] = "table"
        elif representation == "link":
            attributes["visual_production_mode"] = "link"

        if representation == "link" and ("telegram" in text or "телеграм" in text) and not self._telegram_target_present(text):
            attributes["telegram_pending"] = True
            attributes["pending_question"] = "Какой Telegram нужен: официальный канал, чат или пользовательский аккаунт?"

        return self._make_intent(operation, object_name, representation, goal, topic, attributes)

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

    def prepare(self) -> MachineRequest:
        dialogue = self.interpreter.dialogue(self.request, self.state)
        intent = self.interpreter.intent(self.request, self.state, dialogue)
        relation = dialogue["relation"]

        requested_outputs = ["text"]
        required_artifacts: List[str] = []
        representation = intent["representation"]
        if representation in _STRUCTURED_TYPES and representation != "formula":
            requested_outputs.append(representation)
            required_artifacts.append(representation)
        elif representation == "formula":
            requested_outputs.append("formula")
            required_artifacts.append("formula")

        if intent["attributes"].get("telegram_pending"):
            # The answer is a clarification; the representation remains text
            # for this turn and pending state is persisted for the next turn.
            requested_outputs = ["text"]
            required_artifacts = []

        active_task = self.state.get("april_active_task") if isinstance(self.state.get("april_active_task"), dict) else {}
        pending_task = self.state.get("april_pending_task") if isinstance(self.state.get("april_pending_task"), dict) else {}

        resolved_request = self.request
        if dialogue["pending_resolved"] and pending_task:
            base_topic = _text(pending_task.get("topic") or pending_task.get("representation"))
            resolved_request = f"Продолжение задания: {base_topic}. Ответ пользователя: {self.request}"

        context = {
            "relation": relation,
            "continuation": bool(dialogue["continuation"]),
            "reference": bool(dialogue["reference"]),
            "dependency": dialogue["dependency"],
            "anchor": dialogue["anchor"],
            "active_task": _compact(active_task),
            "pending_task": _compact(pending_task),
            "last_user_turn": _compact(self.state.get("last_user_turn", "")),
            "last_april_turn": _compact(self.state.get("last_april_turn", "")),
        }

        visual_mode = _text(intent["attributes"].get("visual_production_mode"))
        if not visual_mode:
            visual_mode = "text"

        output_budget = {
            "text": 900,
            "code": 1400,
            "formula": 900,
            "graph": 1200,
            "table": 1200,
            "diagram": 1200,
            "image": 1100,
            "link": 700,
        }.get(representation, 900)

        dialogue_contract = {
            "version": "april_dialogue_contract_v1",
            "relation": relation,
            "continuation": bool(dialogue["continuation"]),
            "reference_to_previous": bool(dialogue["reference"]),
            "context_dependency": dialogue["dependency"],
            "active_task": _compact(active_task),
            "pending_task": _compact(pending_task),
            "resolved_request": resolved_request,
        }

        memory_packet = {
            "mode": "live_state",
            "active_topic": self.state.get("april_active_topic", ""),
            "active_goal": self.state.get("april_active_goal", ""),
            "active_task": _compact(active_task),
            "pending_task": _compact(pending_task),
            "last_artifact_type": _state_artifact_type(self.state),
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
                "attributes": _compact(intent.get("attributes") or {}),
            },
            conversation={
                "current_request": self.request,
                "resolved_request": resolved_request,
                "dialogue_contract": dialogue_contract,
                "turn_meaning": context,
                "active_task": _compact(active_task),
                "pending_task": _compact(pending_task),
            },
            memory=memory_packet,
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
                    "dialogue_relation": relation,
                    "fast_path": True,
                    "do_not_reinterpret": True,
                },
                "representation_plan": {
                    "representation": representation,
                    "visual_production_mode": visual_mode,
                    "renderer": _RENDERER_REGISTRY.get(representation, "MessageTextBlock"),
                },
                "scene_composition": requested_outputs,
            },
        )
        setattr(request, "dialogue_contract", dialogue_contract)
        setattr(request, "turn_meaning", context)
        setattr(request, "response_output_tokens", output_budget)
        setattr(request, "quantum_state", {
            "version": "april_processor_v1",
            "relation": relation,
            "continuation": bool(dialogue["continuation"]),
            "reference": bool(dialogue["reference"]),
            "dependency": dialogue["dependency"],
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
        for raw in raw_blocks:
            if not isinstance(raw, dict):
                continue
            block = dict(raw)
            kind = _text(block.get("type") or block.get("artifact_type") or block.get("representation")).lower()
            if not kind:
                continue
            # Processor-authorized type only. The provider may not turn image into
            # diagram, graph into diagram, etc.
            if kind not in expected and kind not in {"text", "markdown"}:
                continue
            payload = block.get("payload")
            if payload is None:
                payload = {}
            if not isinstance(payload, dict):
                payload = {"content": _text(payload)}
            block["type"] = kind
            block["renderer"] = _RENDERER_REGISTRY.get(kind, block.get("renderer") or "MessageTextBlock")
            block["viewer"] = block.get("viewer") or block["renderer"]
            block["payload"] = payload
            block["scene_contract"] = True
            block["block_id"] = block.get("block_id") or _stable_id(f"scene-{kind}", payload)
            sig = json.dumps({"type": kind, "payload": payload}, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
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
    topic = _text(request.intent.get("object") or representation)

    state["april_turn_id"] = int(state.get("april_turn_id") or 0) + 1
    state["last_user_turn"] = request.conversation.get("current_request", "")
    state["last_april_turn"] = response.answer
    state["april_active_topic"] = topic
    state["april_active_goal"] = goal
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

    state["april_live_context"] = {
        "version": "april_live_context_v1",
        "relation": relation,
        "active_topic": topic,
        "active_goal": goal,
        "active_task": _compact(state.get("april_active_task")),
        "pending_task": _compact(state.get("april_pending_task")),
        "last_user_turn": _text(state.get("last_user_turn")),
        "last_april_turn": _text(state.get("last_april_turn")),
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
            "prompt": result.get("prompt") or spec.get("prompt") or "",
            "engine": "April Images Generation",
            "backend": result.get("backend"),
            "render_spec": spec,
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
                "alt": payload["prompt"],
                "caption": payload["prompt"],
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
        preview_response = MachineResponse(
            answer=_text(machine_preview.get("answer")),
            content=_text(machine_preview.get("content")),
            response=_text(machine_preview.get("response")),
            summary=_text(machine_preview.get("summary")),
            confidence=float(machine_preview.get("confidence") or 1.0),
            render_blocks=list(machine_preview.get("render_blocks") or []),
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
    relation = _text(request.dialogue_contract.get("relation")).upper() or "NEW"
    state["dialogue_resolution"] = {
        "authoritative": True,
        "relation": "CONTINUE" if relation == "CONTINUE" else "NEW",
        "continuation": bool(request.dialogue_contract.get("continuation")),
        "reference": bool(request.dialogue_contract.get("reference_to_previous")),
        "context_dependency": request.dialogue_contract.get("context_dependency"),
        "selected_memory_index": -1,
        "selected_memory_operand": {},
    }

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
