from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from dataclasses import asdict, is_dataclass
from copy import deepcopy
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

from blocks.C_ARTIFACT_CONTRACT import (
    MachineRequest,
    MachineResponse,
    build_machine_scene,
    build_scene_contract,
    build_scene_signal,
    BaseArtifact,
    create_artifact,
    create_diagram_artifact,
    build_room_route_contract,
    _artifact_canonical_render_blocks,
)
from blocks.april_personality import APRIL_IDENTITY
from blocks.interpretation_layer import interpret_request, QuantumInterpretationEngine
from blocks.provider_router import generate_text
from blocks.reasoning_state import build_turn_synchronization_snapshot
from blocks.goal_engine import build_goal_evidence, evaluate_goal_progress
from blocks.response_decision import build_completion_decision
from blocks.state_manager import get_state, update_scene_context, persist_state, build_dialogue_memory_bridge
from blocks.presentation_formatter import canonical_payload_for_block, validate_render_block_payload
from blocks.rooms_registry import registry_route_machine_request

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


def _compact_task_state(value: Any) -> Any:
    """Compact task state without truncating the semantic Q&A trajectory.

    Generic scene compaction is intentionally small, but an interactive task
    is a state machine: its accumulated questions/answers are the evidence
    needed for a later solve/guess turn. Keep the bounded task history intact.
    """
    return _compact(value, depth=0, max_depth=6, max_items=16)


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


def _visual_hydration_key(block: Any) -> str:
    """Return a semantic key for image/diagram carriers of the same artifact.

    Provider responses can legally expose one visual artifact both in
    ``scene.render_blocks`` and in ``artifacts``.  Those are transport carriers,
    not two visible scene nodes.  The key intentionally ignores renderer/UI
    metadata and keeps only the visual payload identity.
    """
    if not isinstance(block, dict):
        return ""
    kind = _text(
        block.get("type") or block.get("artifact_type") or block.get("representation")
    ).lower()
    if kind not in {"image", "diagram"}:
        return ""

    payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
    if kind == "image":
        images = payload.get("images")
        if isinstance(images, list) and images:
            sources = []
            for item in images:
                if isinstance(item, dict):
                    source = (
                        item.get("src")
                        or item.get("url")
                        or item.get("image")
                        or item.get("image_data_uri")
                        or item.get("image_base64")
                    )
                    if source:
                        sources.append(str(source))
            if sources:
                return "image:" + hashlib.sha1(
                    json.dumps(sources, ensure_ascii=False, sort_keys=True).encode("utf-8")
                ).hexdigest()[:20]
        direct = (
            payload.get("src")
            or payload.get("url")
            or payload.get("image")
            or payload.get("image_data_uri")
            or payload.get("image_base64")
        )
        if direct:
            return "image:" + hashlib.sha1(str(direct).encode("utf-8")).hexdigest()[:20]
        return ""

    raw_nodes = payload.get("nodes") or payload.get("components") or payload.get("vertices") or []
    raw_edges = payload.get("edges") or payload.get("connections") or payload.get("relations") or payload.get("segments") or []

    nodes = []
    for node in raw_nodes if isinstance(raw_nodes, list) else []:
        if isinstance(node, dict):
            nodes.append({
                "id": str(node.get("id") or node.get("node_id") or node.get("name") or node.get("label") or ""),
                "label": str(node.get("label") or node.get("name") or node.get("title") or ""),
            })
        else:
            nodes.append({"id": str(node), "label": str(node)})

    edges = []
    for edge in raw_edges if isinstance(raw_edges, list) else []:
        if isinstance(edge, (list, tuple)) and len(edge) >= 2:
            source, target = edge[0], edge[1]
            label = ""
        elif isinstance(edge, dict):
            source = edge.get("from") or edge.get("source") or edge.get("start")
            target = edge.get("to") or edge.get("target") or edge.get("end")
            label = edge.get("label") or ""
        else:
            continue
        if source and target:
            edges.append({
                "from": str(source),
                "to": str(target),
                "label": str(label),
            })

    semantic = {
        "svg": payload.get("svg") or payload.get("svg_payload"),
        "nodes": nodes,
        "edges": edges,
        "geometry": payload.get("geometry"),
        "elements": payload.get("elements"),
        "points": payload.get("points"),
        "shapes": payload.get("shapes"),
    }
    if not any(value not in (None, "", [], {}) for value in semantic.values()):
        return ""
    return "diagram:" + hashlib.sha1(
        json.dumps(semantic, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:20]


def _hydrate_scene_artifacts(response: MachineResponse, request: MachineRequest) -> None:
    """Promote every concrete structured render block into the canonical artifact route.

    Image and diagram used to stop at ``render_blocks`` while graph/table could
    already participate in the artifact contract.  This bridge makes the
    artifact lifecycle uniform without changing the representation selected by
    Interpretation or the concrete Web renderer.
    """
    existing: list[BaseArtifact] = [
        item for item in list(getattr(response, "artifacts", []) or [])
        if isinstance(item, BaseArtifact)
    ]
    known_ids = {
        str(getattr(getattr(item, "metadata", None), "artifact_id", "") or "")
        for item in existing
    }

    room_for_type = {
        "image": "APRIL_IMAGES_GENERATION",
        "gallery": "C_GALLERY_ROOM",
        "diagram": "C_DIAGRAM_ROOM",
        "graph": "C_GRAPH_ROOM",
        "table": "C_TABLE_ROOM",
        "code": "C_FUNCTION_ROOM",
        "link": "C_LINK_ROOM",
        "formula": "C_FORMULA_ROOM",
    }

    hydrated_blocks: list[dict[str, Any]] = []
    seen_hydration_keys: set[str] = set()
    for raw in list(getattr(response, "render_blocks", []) or []):
        if not isinstance(raw, dict):
            continue
        kind = _text(raw.get("type") or raw.get("artifact_type") or raw.get("representation")).lower()
        if kind not in {"image", "diagram"}:
            continue

        payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}
        if kind == "image":
            has_source = any(payload.get(k) for k in ("src", "url", "image", "image_data_uri", "image_base64")) or bool(payload.get("images"))
            if not has_source:
                continue
        elif kind == "diagram":
            has_structure = any(
                payload.get(k) not in (None, "", [], {})
                for k in ("nodes", "edges", "geometry", "elements", "points", "segments", "svg", "svg_payload", "shapes")
            )
            if not has_structure:
                continue
        else:
            # Existing routes have their own structured validators; here we only
            # hydrate blocks that already contain meaningful payload data.
            if not payload and kind not in {"formula", "link"}:
                continue

        hydration_key = _visual_hydration_key(raw)
        if hydration_key and hydration_key in seen_hydration_keys:
            continue
        if hydration_key:
            seen_hydration_keys.add(hydration_key)

        try:
            if kind == "diagram":
                identity_payload = dict(payload)
                if raw.get("renderer") and identity_payload.get("renderer") is None:
                    identity_payload["renderer"] = raw.get("renderer")
                if raw.get("viewer") and identity_payload.get("viewer") is None:
                    identity_payload["viewer"] = raw.get("viewer")
                response_identity = {
                    "scene_id": getattr(response, "scene_id", ""),
                    "turn_id": getattr(response, "turn_id", ""),
                    "flow_id": getattr(response, "flow_id", ""),
                    "topic_group": getattr(response, "topic_group", ""),
                    "continuation": getattr(response, "continuation", False),
                }
                for key in ("scene_id", "turn_id", "flow_id", "topic_group", "continuation", "block_id", "render_id"):
                    candidate = raw.get(key) if raw.get(key) is not None else response_identity.get(key)
                    if candidate is not None and identity_payload.get(key) is None:
                        identity_payload[key] = candidate
                artifact = create_diagram_artifact(
                    semantic=raw.get("semantic") if isinstance(raw.get("semantic"), dict) else {},
                    payload=identity_payload,
                )
            else:
                data = {
                    "payload": payload,
                    "title": raw.get("title") or payload.get("title") or "",
                    "description": raw.get("description") or payload.get("description") or "",
                    "renderer": raw.get("renderer"),
                    "viewer": raw.get("viewer"),
                    "presentation": raw.get("presentation") if isinstance(raw.get("presentation"), dict) else {},
                    "scene_id": raw.get("scene_id") or getattr(response, "scene_id", ""),
                    "turn_id": raw.get("turn_id") or getattr(response, "turn_id", ""),
                    "flow_id": raw.get("flow_id") or getattr(response, "flow_id", ""),
                    "topic_group": raw.get("topic_group") or getattr(response, "topic_group", ""),
                    "continuation": raw.get("continuation") if raw.get("continuation") is not None else getattr(response, "continuation", False),
                    "block_id": raw.get("block_id"),
                    "render_id": raw.get("render_id"),
                    "human_visible": True,
                    "machine_only": False,
                }
                artifact = create_artifact(
                    artifact_type=kind,
                    room_source=room_for_type.get(kind, "C_ARTIFACT_CONTRACT"),
                    data=data,
                )

            artifact_id = str(getattr(getattr(artifact, "metadata", None), "artifact_id", "") or "")
            if artifact_id and artifact_id not in known_ids:
                existing.append(artifact)
                known_ids.add(artifact_id)
            elif not artifact_id:
                existing.append(artifact)

            # Re-project through the exact same canonical artifact->render-block
            # formatter used by every other room. This is the unification point.
            for block in _artifact_canonical_render_blocks(artifact):
                block = dict(block)
                if raw.get("scene_id") and not block.get("scene_id"):
                    block["scene_id"] = raw.get("scene_id")
                if raw.get("turn_id") and not block.get("turn_id"):
                    block["turn_id"] = raw.get("turn_id")
                if raw.get("flow_id") and not block.get("flow_id"):
                    block["flow_id"] = raw.get("flow_id")
                hydrated_blocks.append(block)
        except Exception as exc:
            print("⚠️ APRIL ARTIFACT HYDRATION:", kind, exc)

    if existing:
        response.artifacts = existing
        response.artifacts_payload = [
            deepcopy(getattr(item, "data", {}) or {}) for item in existing
        ]

    if hydrated_blocks:
        existing_signatures = {
            json.dumps({
                "type": _text(block.get("type")).lower(),
                "payload": block.get("payload", {}),
                "content": block.get("content", ""),
            }, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
            for block in list(response.render_blocks or []) if isinstance(block, dict)
        }
        merged = [
            block for block in list(response.render_blocks or [])
            if isinstance(block, dict)
            and _text(block.get("type") or block.get("artifact_type")).lower() not in {"image", "diagram"}
        ]
        for block in hydrated_blocks:
            sig = json.dumps({
                "type": _text(block.get("type")).lower(),
                "payload": block.get("payload", {}),
                "content": block.get("content", ""),
            }, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
            if sig not in existing_signatures:
                existing_signatures.add(sig)
                merged.append(block)
        for idx, block in enumerate(merged):
            block["sequence_index"] = idx
        response.render_blocks = merged


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

        cognitive_workspace = self.semantic_result.get("cognitive_workspace") if isinstance(self.semantic_result.get("cognitive_workspace"), dict) else {}
        vector = self.semantic_result.get("dialogue_vector") if isinstance(self.semantic_result.get("dialogue_vector"), dict) else {}
        contract = self.semantic_result.get("dialogue_contract") if isinstance(self.semantic_result.get("dialogue_contract"), dict) else {}
        relation = _text(
            cognitive_workspace.get("relation")
            or cognitive_workspace.get("topic_relation")
            or vector.get("three_way_relation")
            or contract.get("three_way_relation")
            or contract.get("relation")
            or "NEW"
        ).upper()
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
        reference = bool(
            cognitive_workspace.get("reference")
            if cognitive_workspace
            else (relation == "RECALL" or contract.get("reference_to_previous"))
        )
        dependency = _text(contract.get("context_dependency"))
        if not dependency:
            dependency = "pending" if pending_resolved else "recall" if reference else "continuation" if relation == "CONTINUE" else "independent"
        anchor = "pending_task" if pending_resolved else "last_turn" if relation == "CONTINUE" else "memory" if reference else "none"
        continuation_analysis = self.semantic_result.get("continuation_content_analysis")
        continuation_analysis = continuation_analysis if isinstance(continuation_analysis, dict) else {}
        dialogue_strategy = self.semantic_result.get("dialogue_strategy")
        dialogue_strategy = dialogue_strategy if isinstance(dialogue_strategy, dict) else {}
        resolved_entity = _text(
            cognitive_workspace.get("active_entity")
            or self.semantic_result.get("resolved_entity")
            or contract.get("resolved_entity")
            or vector.get("resolved_entity")
            or continuation_analysis.get("active_entity")
        )
        if cognitive_workspace:
            task_state = (
                cognitive_workspace.get("active_task_context")
                if bool(cognitive_workspace.get("task_continuation")) and isinstance(cognitive_workspace.get("active_task_context"), dict)
                else {}
            )
        else:
            task_state = (
                self.semantic_result.get("interactive_task_state")
                if isinstance(self.semantic_result.get("interactive_task_state"), dict)
                else self.semantic_result.get("open_task")
                if isinstance(self.semantic_result.get("open_task"), dict)
                else contract.get("interactive_task_state")
                if isinstance(contract.get("interactive_task_state"), dict)
                else contract.get("open_task")
                if isinstance(contract.get("open_task"), dict)
                else {}
            )
        task_memory = (
            self.semantic_result.get("task_memory")
            if isinstance(self.semantic_result.get("task_memory"), dict)
            else contract.get("task_memory")
            if isinstance(contract.get("task_memory"), dict)
            else {}
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
            "active_task": task_state,
            "open_task": task_state,
            "interactive_task_state": task_state,
            "task_memory": task_memory,
            "task_relation": contract.get("task_relation") or self.semantic_result.get("task_relation") or {},
            "task_transition": contract.get("task_transition") or self.semantic_result.get("task_transition") or {},
            "task_action": bool(contract.get("task_action") or self.semantic_result.get("task_action")),
            "sequence_id": _text(
                cognitive_workspace.get("sequence_id")
                or vector.get("sequence_id")
                or contract.get("sequence_id")
                or (
                    (vector.get("trajectory") or {}).get("sequence_id")
                    if isinstance(vector.get("trajectory"), dict)
                    else ""
                )
            ),
            "conversation_continuation": bool(cognitive_workspace.get("conversation_continuation")) if cognitive_workspace else bool(relation == "CONTINUE"),
            "semantic_continuation": bool(cognitive_workspace.get("semantic_continuation")) if cognitive_workspace else bool(relation == "CONTINUE"),
            "task_continuation": bool(cognitive_workspace.get("task_continuation")) if cognitive_workspace else bool(task_state),
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
            # A current-turn image build is a production request.  The previous
            # code trusted a stale `image_present` semantic field even when the
            # current operation was `build`, which made Provider return only text
            # and prevented C_APRIL_IMAGES_GENERATOR from ever materializing the
            # image.  Artifact continuation is still one semantic image route; it
            # simply uses the previous scene as the operand.
            artifact_reference = bool(
                interpretation_control.get("artifact_reference")
                or interpretation_control.get("render_mode") == "ARTIFACT_CONTINUATION"
            )
            if operation in {"build", "visualize", "modify", "transform", "redraw"}:
                attributes["visual_production_mode"] = "image_generation"
            elif semantic_mode in {"image_generation", "image_present"}:
                attributes["visual_production_mode"] = semantic_mode
            else:
                attributes["visual_production_mode"] = "image_present"
            attributes["artifact_reference"] = artifact_reference
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
        # This is only the Executor's compatibility view after semantic
        # interpretation.  Specific structured forms outrank the generic
        # "draw/create" modality, so "нарисуй это в схеме" remains a diagram
        # rather than collapsing to image.
        if re.search(r"\b(код|python|пайтон|скрипт)\b", text):
            return "code"
        if re.search(r"\b(ссыл\w*|url|link)\b", text):
            return "link"
        if re.search(r"\b(формул\w*|уравнени\w*)\b", text):
            return "formula"
        if re.search(r"\b(график|графика|кривую|кривая)\b", text):
            return "graph"
        if re.search(r"\b(таблиц\w*|табличк\w*)\b", text):
            return "table"
        if re.search(r"\b(схем\w*|блок-схем\w*)\b", text):
            return "diagram"
        if re.search(r"\b(нарисуй|изобрази|сгенерируй|создай)\b", text) or "картинк" in text or "изображени" in text or "портрет" in text:
            return "image"
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
        # Snapshot the operand before interpretation can update the live scene.
        # Artifact-continuation requests must resolve against the previous
        # successful visual result, never against the scene being constructed for
        # the current turn.
        prior_visual_scene = (
            dict(self.state.get("active_visual_scene"))
            if isinstance(self.state.get("active_visual_scene"), dict)
            else dict(self.state.get("current_visual_scene"))
            if isinstance(self.state.get("current_visual_scene"), dict)
            else {}
        )
        dialogue = self.interpreter.dialogue(self.request, self.state)
        intent = self.interpreter.intent(self.request, self.state, dialogue)

        # The semantic result/workspace is produced by Interpretation and must be
        # available before task ownership is resolved below.  Keep this binding
        # local to prepare() so the fast path never references it before assignment.
        semantic_result = (
            dialogue.get("semantic_result")
            if isinstance(dialogue.get("semantic_result"), dict)
            else {}
        )
        cognitive_workspace = (
            semantic_result.get("cognitive_workspace")
            if isinstance(semantic_result.get("cognitive_workspace"), dict)
            else {}
        )

        provider_context_plan = (
            semantic_result.get("provider_context_plan")
            if isinstance(semantic_result.get("provider_context_plan"), dict)
            else (
                cognitive_workspace.get("provider_context_plan")
                if isinstance(cognitive_workspace.get("provider_context_plan"), dict)
                else {}
            )
        )
        # Current request is immutable across the handoff. Derived semantic/request text
        # is a separate field and can never replace the raw authenticated user turn.
        if cognitive_workspace:
            cognitive_workspace["current_user_request"] = self.request
            cognitive_workspace["current_request_raw"] = self.request

        # Interpretation owns the dialogue relation. Executor records the decision
        # but never upgrades NEW -> CONTINUE merely because the representation is structured.
        # A new graph/table/image request is allowed to start a new semantic branch.
        interpretation_relation_audit = {
            "interpretation_relation": _text(dialogue.get("relation") or "NEW"),
            "interpretation_turn_relation": _text(
                dialogue.get("semantic_result", {}).get("turn_relation")
            ) if isinstance(dialogue.get("semantic_result"), dict) else "",
            "relation_overridden": False,
            "authority": "INTERPRETATION",
        }

        # Final semantic handoff: once the Processor has a resolved representation,
        # Interpretation remains the authority for render authorization.  This
        # closes the old gap where the representation was correctly resolved to
        # image/diagram/table but interpretation_control was empty, so Provider
        # was instructed to return text only.
        resolved_control = intent.get("interpretation_control") if isinstance(intent.get("interpretation_control"), dict) else {}
        if intent.get("representation") in _STRUCTURED_TYPES and not resolved_control.get("render_authorized"):
            live_visual = (
                self.state.get("active_visual_scene")
                if isinstance(self.state.get("active_visual_scene"), dict)
                else self.state.get("current_visual_scene")
                if isinstance(self.state.get("current_visual_scene"), dict)
                else {}
            )
            resolved_control = QuantumInterpretationEngine._build_interpretation_control(
                text=self.request,
                representation=_text(intent.get("representation")),
                operation=_text(intent.get("operation")),
                relation=_text(dialogue.get("relation")),
                previous_user=_text(self.state.get("last_user_turn")),
                previous_assistant=_text(self.state.get("last_april_turn")),
                live_scene=live_visual,
                explicit_boundary=False,
            )
            intent["interpretation_control"] = resolved_control
            intent["render_authorized"] = bool(resolved_control.get("render_authorized"))
            intent["render_mode"] = _text(resolved_control.get("render_mode") or "STRUCTURED_OUTPUT")
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

        # The current Interpretation representation is authoritative for the
        # current turn.  A stale requested_outputs list may come from an older
        # scene (for example graph/diagram left in dialogue memory) and must not
        # be allowed to suppress the current image/diagram artifact.
        if representation in _STRUCTURED_TYPES and representation not in requested_outputs:
            requested_outputs.append(representation)

        if representation in _STRUCTURED_TYPES and representation in requested_outputs:
            required_artifacts.append(representation)

        if intent["attributes"].get("telegram_pending"):
            # The answer is a clarification; the representation remains text
            # for this turn and pending state is persisted for the next turn.
            requested_outputs = ["text"]
            required_artifacts = []

        semantic_task_state = dialogue.get("interactive_task_state") if isinstance(dialogue.get("interactive_task_state"), dict) else {}
        persisted_task_state = self.state.get("interactive_task_state") if isinstance(self.state.get("interactive_task_state"), dict) else {}
        if cognitive_workspace:
            active_task = (
                semantic_task_state
                if bool(cognitive_workspace.get("task_continuation")) and isinstance(semantic_task_state, dict)
                else {}
            )
        else:
            active_task = semantic_task_state or persisted_task_state or (
                self.state.get("april_active_task")
                if isinstance(self.state.get("april_active_task"), dict)
                else {}
            )
        pending_task = self.state.get("april_pending_task") if isinstance(self.state.get("april_pending_task"), dict) else {}

        resolved_request = _text(dialogue.get("resolved_request") or self.request)
        if dialogue["pending_resolved"] and pending_task and not dialogue.get("resolved_request"):
            base_topic = _text(pending_task.get("topic") or pending_task.get("representation"))
            resolved_request = f"Продолжение задания: {base_topic}. Ответ пользователя: {self.request}"

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
            cognitive_workspace.get("active_entity")
            or semantic_result.get("resolved_entity")
            or continuation_analysis.get("active_entity")
            or dialogue.get("resolved_reference")
            or self.state.get("april_active_entity")
        )

        # The semantic task is authoritative whenever an interactive task exists.
        # A replacement/new-task request may be NEW at the scene level but still
        # carries the newly created task frame to the provider.
        semantic_task_active = bool(
            isinstance(active_task, dict) and active_task.get("active")
        )
        turn_active_task = active_task if semantic_task_active else {
            "operation": intent.get("operation"),
            "object": intent.get("object"),
            "representation": intent.get("representation"),
            "goal": intent.get("goal"),
            "topic": dialogue.get("canonical_topic") or intent.get("topic") or intent.get("object"),
        }

        render_mode = _text(intent.get("render_mode") or "TEXT_ONLY").upper()
        selected_artifact = semantic_result.get("target_artifact") if isinstance(semantic_result.get("target_artifact"), dict) else {}
        selected_artifact = dict(selected_artifact)
        live_visual_scene = prior_visual_scene or (
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

        # The active visual scene is the canonical fallback operand when
        # Interpretation identified an artifact continuation but did not attach
        # a separate target_artifact object.  This keeps the operand inside the
        # same dialogue/SceneContract instead of inventing a second visual route.
        if artifact_context_only and not selected_artifact and live_visual_scene:
            visual_blocks = [
                block for block in (live_visual_scene.get("render_blocks") or live_visual_scene.get("blocks") or [])
                if isinstance(block, dict)
                and _text(block.get("type") or block.get("artifact_type") or "").lower() in _STRUCTURED_TYPES
            ]
            if visual_blocks:
                selected_artifact = {
                    "scene_id": live_visual_scene.get("scene_id"),
                    "type": _text(visual_blocks[-1].get("type") or visual_blocks[-1].get("artifact_type")),
                    "render_block": _compact(visual_blocks[-1], max_depth=6, max_items=10),
                    "source": "active_visual_scene",
                }

        selected_artifact_block = selected_artifact.get("render_block") if isinstance(selected_artifact.get("render_block"), dict) else {}
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

        semantic_frame = dict(semantic_result.get("semantic_frame") or {})
        workspace_frame = (cognitive_workspace.get("semantic_frame")
                           if isinstance(cognitive_workspace.get("semantic_frame"), dict)
                           else {})
        semantic_frame.update({
            "topic": _text(
                workspace_frame.get("topic")
                or cognitive_workspace.get("active_topic")
                or intent.get("topic")
                or semantic_frame.get("topic")
                or representation
            ),
            "operation": _text(
                cognitive_workspace.get("operation")
                or workspace_frame.get("operation")
                or intent.get("operation")
                or semantic_frame.get("operation")
                or "answer"
            ),
            "goal": _text(
                cognitive_workspace.get("goal")
                or workspace_frame.get("goal")
                or intent.get("goal")
                or semantic_frame.get("goal")
                or "answer"
            ),
            "representation": _text(
                cognitive_workspace.get("representation")
                or workspace_frame.get("representation")
                or representation
                or semantic_frame.get("representation")
                or "text"
            ).lower(),
            "entity": _text(
                cognitive_workspace.get("active_entity")
                or workspace_frame.get("entity")
                or intent.get("object")
                or semantic_frame.get("entity")
            ),
            "relation": _text(
                cognitive_workspace.get("relation")
                or workspace_frame.get("relation")
                or dialogue.get("relation")
                or semantic_frame.get("relation")
                or "NEW"
            ).upper(),
        })
        semantic_result["semantic_frame"] = semantic_frame

        turn_sync = build_turn_synchronization_snapshot(self.request, self.state, semantic_result)
        goal_evidence = build_goal_evidence(self.request, self.state, semantic_result)
        closure_readiness = build_completion_decision(
            {
                **goal_evidence,
                "goal_completed": False,
                "closure": {
                    **(goal_evidence.get("closure") if isinstance(goal_evidence.get("closure"), dict) else {}),
                    "allowed_now": False,
                },
            },
            semantic_result,
        )

        context = {
            "relation": relation,
            "continuation": bool(dialogue["continuation"]),
            "reference": bool(dialogue["reference"]),
            "dependency": dialogue["dependency"],
            "anchor": dialogue["anchor"],
            "active_task": _compact_task_state(turn_active_task),
            "interactive_task_state": _compact_task_state(
                dialogue.get("interactive_task_state") or active_task
            ),
            "task_memory": _compact_task_state(
                dialogue.get("task_memory") or {}
            ),
            "task_relation": _compact(dialogue.get("task_relation") or {}),
            "task_transition": _compact(dialogue.get("task_transition") or {}),
            "task_action": bool(dialogue.get("task_action")),
            "pending_task": _compact(pending_task),
            "active_entity": resolved_entity,
            "provider_context_plan": _compact(provider_context_plan, max_depth=7, max_items=14),
            "provider_context_authority": "INTERPRETATION",
            "interpretation_relation_audit": interpretation_relation_audit,
            "current_user_request": self.request,
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
            "active_task": _compact_task_state(turn_active_task),
            "open_task": _compact_task_state(dialogue.get("open_task") or active_task),
            "interactive_task_state": _compact_task_state(dialogue.get("interactive_task_state") or active_task),
            "task_memory": _compact(dialogue.get("task_memory") or {}),
            "task_relation": _compact(dialogue.get("task_relation") or {}),
            "task_transition": _compact(dialogue.get("task_transition") or {}),
            "task_action": bool(dialogue.get("task_action")),
            "pending_task": _compact(pending_task),
            "active_entity": resolved_entity,
            "semantic_frame": _compact(semantic_result.get("semantic_frame") or {}, max_depth=3, max_items=8),
            "turn_sync": _compact(turn_sync, max_depth=4, max_items=10),
            "closure_policy": closure_readiness,
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
            "sequence_turn_index": int((dialogue_memory.get("active_sequence") or {}).get("turn_count", 0) or 0) + (1 if relation in {"NEW", "CONTINUE"} else 0),
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
            "current_user_request": self.request,
            "provider_context_plan": _compact(provider_context_plan, max_depth=7, max_items=14),
            "provider_context_authority": "INTERPRETATION",
            "provider_must_not_reselect_context": True,
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
            "active_task": _compact_task_state(turn_active_task) if semantic_task_active else {},
            "interactive_task_state": _compact_task_state(dialogue.get("interactive_task_state") or active_task) if semantic_task_active else {},
            "task_memory": _compact_task_state(dialogue.get("task_memory") or {}) if semantic_task_active else {},
            "task_relation": _compact(dialogue.get("task_relation") or {}) if semantic_task_active else {},
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
            "provider_context_plan": _compact(provider_context_plan, max_depth=7, max_items=14),
            "provider_context_authority": "INTERPRETATION",
            "current_user_request": self.request,
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
                "semantic_frame": _compact(semantic_result.get("semantic_frame") or {}, max_depth=3, max_items=8),
                "semantic_understanding": _compact(semantic_result.get("semantic_understanding") or {}, max_depth=5, max_items=10),
                "attributes": _compact(intent.get("attributes") or {}),
            },
            conversation={
                "current_request": self.request,
                "resolved_request": resolved_request,
                "dialogue_contract": dialogue_contract,
                "turn_meaning": context,
                "active_task": _compact_task_state(turn_active_task),
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
                "semantic_frame": _compact(semantic_result.get("semantic_frame") or {}, max_depth=3, max_items=8),
                "turn_sync": _compact(turn_sync, max_depth=4, max_items=10),
                "scene_blueprint": _compact(semantic_result.get("scene_blueprint") or {}, max_depth=5, max_items=16),
                "cognitive_workspace": _compact(cognitive_workspace, max_depth=5, max_items=14),
                "provider_context_plan": _compact(provider_context_plan, max_depth=7, max_items=14),
                "provider_context_authority": "INTERPRETATION",
                "current_user_request": self.request,
                "user_id": self.user_id,
                "conversation_id": dialogue_memory.get("conversation_id"),
            },
            memory=memory_packet,
            visual_context=artifact_visual_context,
            requested_outputs=requested_outputs,
            required_artifacts=required_artifacts,
            required_competencies=[intent["operation"], representation],
            routing={
                "decision_owner": "QUANTUM_PROCESSOR",
                "route": (
                    "artifact_room"
                    if representation in {"image", "gallery"}
                    else "provider"
                ),
                "single_route": True,
                "engine": (
                    "processor->openai->c_artifact->rooms_registry->room->scene"
                    if representation in {"image", "gallery"}
                    else "processor->openai->scene"
                ),
            },
            constraints={
                "one_provider_call": True,
                "provider_input_token_budget": 900,
                "provider_hard_input_budget": provider_context_plan.get("hard_budget_tokens", 900),
                "provider_soft_input_target": provider_context_plan.get("soft_target_tokens"),
                "provider_context_plan": _compact(provider_context_plan, max_depth=7, max_items=14),
                "provider_context_authority": "INTERPRETATION",
                "provider_must_not_reselect_context": True,
                "cognitive_context_plan": _compact(cognitive_workspace, max_depth=5, max_items=14),
                "metadata": {
                    "identity_scope": {
                        "user_id": self.user_id,
                        "conversation_id": dialogue_memory.get("conversation_id"),
                        "dialogue_sequence_id": _text(dialogue.get("sequence_id")),
                    },
                    "visual_production_mode": visual_mode,
                    "semantic_request": _text(
                        semantic_result.get("semantic_request")
                        or _as_dict(semantic_result.get("semantic_understanding")).get("provider", {}).get("semantic_request")
                        or resolved_request
                    ),
                    "semantic_understanding": _compact(semantic_result.get("semantic_understanding") or {}, max_depth=5, max_items=10),
                    "dialogue_relation": relation,
                    "semantic_frame": _compact(semantic_result.get("semantic_frame") or {}, max_depth=3, max_items=8),
                    "turn_sync": _compact(turn_sync, max_depth=4, max_items=10),
                    "closure_policy": closure_readiness,
                    "fast_path": True,
                    "do_not_reinterpret": True,
                    "interpretation_control": _compact(intent.get("interpretation_control") or semantic_result.get("interpretation_control") or {}, max_depth=4, max_items=10),
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
            "interpretation_control": _compact(intent.get("interpretation_control") or semantic_result.get("interpretation_control") or {}, max_depth=4, max_items=10),
            "cognitive_workspace_version": _text(cognitive_workspace.get("version")),
            "cognitive_workspace_protected": list(cognitive_workspace.get("protected_context") or [])[:12],
            "cognitive_workspace_excluded": list(cognitive_workspace.get("excluded_context") or [])[:8],
            "provider_context_plan_version": _text(provider_context_plan.get("version")),
            "provider_context_required": [
                _text(x.get("key") or x.get("name"))
                for x in list(provider_context_plan.get("required_context") or [])[:16]
                if isinstance(x, dict)
            ],
            "provider_context_optional": [
                _text(x.get("key") or x.get("name"))
                for x in list(provider_context_plan.get("optional_context") or [])[:16]
                if isinstance(x, dict)
            ],
            "provider_context_excluded": [
                _text(x.get("key") or x.get("name"))
                for x in list(provider_context_plan.get("excluded_context") or [])[:16]
                if isinstance(x, dict)
            ],
            "provider_context_authority": "INTERPRETATION",
            "provider_must_not_reselect_context": True,
            "current_user_request": self.request,
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
        provider_blocks = machine_payload.get("render_blocks") or []
        provider_artifacts = machine_payload.get("artifacts") or []
        blocks = self._canonicalize_blocks(provider_blocks, request)
        answer = _text(machine_payload.get("answer") or machine_payload.get("content"))
        if not answer:
            raise RuntimeError("EMPTY_PROVIDER_ANSWER")

        # Transport invariant: a human-visible answer must never be represented
        # by an empty text block. Some provider payloads contain a valid answer
        # at the MachineResponse level but an empty/partial companion text block.
        # Hydrate that canonical block from the already-validated answer instead
        # of letting the Web create an empty assistant bubble.
        text_like_types = {"text", "markdown"}
        text_block_found = False
        hydrated_blocks = []
        for block in list(blocks or []):
            item = dict(block) if isinstance(block, dict) else {}
            kind = _text(
                item.get("type") or item.get("artifact_type") or item.get("representation") or ""
            ).lower()
            if kind in text_like_types:
                content = _text(item.get("content") or item.get("text") or item.get("answer"))
                if not content:
                    item["type"] = "text"
                    item["renderer"] = "MessageTextBlock"
                    item["viewer"] = "MessageTextBlock"
                    item["content"] = answer
                    item["text"] = answer
                    item["human_visible"] = True
                    item["scene_contract"] = True
                    item["text_recovered_from_answer"] = True
                    item["recovery_reason"] = "provider_text_block_empty_but_machine_answer_present"
                text_block_found = True
            hydrated_blocks.append(item)

        blocks = hydrated_blocks

        # When text is part of the processor-owned output plan, guarantee one
        # visible text carrier even if the provider emitted only structured blocks.
        expected_outputs = {
            _text(x).lower() for x in list(request.requested_outputs or [])
            if _text(x)
        }
        if answer and "text" in expected_outputs and not text_block_found:
            blocks.insert(0, self._text_block(answer))

        if not blocks:
            blocks = [self._text_block(answer)]

        # The scene is composed once below. No renderer-specific side route is
        # allowed to strip blocks after canonicalization. A truly text-only
        # request simply arrives with one text block.

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
            "provider_transport_counts": {
                "provider_render_blocks_received": len(provider_blocks) if isinstance(provider_blocks, list) else 0,
                "provider_artifacts_received": len(provider_artifacts) if isinstance(provider_artifacts, list) else 0,
                "scene_render_blocks_after_canonicalization": len(blocks),
            },
            "render_omissions": list(self._render_omissions)[:24],
            "processor_version": PROCESSOR_VERSION,
            "decision_owner": "QUANTUM_PROCESSOR",
            "canonical_representation": request.intent.get("type"),
            "dialogue_relation": request.dialogue_contract.get("relation"),
            "continuation": bool(request.quantum_state.get("continuation")),
            "single_route": True,
            "provider_calls": 1,
            "fast_path": True,
            "web_signal_source": "SCENE_CONTRACT",
            "user_id": self.user_id,
            "conversation_id": _text(request.memory.get("authenticated_user_scope", {}).get("conversation_id")),
            "dialogue_sequence_id": _text(request.dialogue_contract.get("sequence_id")),
            "sequence_turn_index": int(request.dialogue_contract.get("sequence_turn_index") or 0),
            "identity_scope": {
                "user_id": self.user_id,
                "conversation_id": _text(request.memory.get("authenticated_user_scope", {}).get("conversation_id")),
                "dialogue_sequence_id": _text(request.dialogue_contract.get("sequence_id")),
            },
            "active_task": _compact_task_state(request.dialogue_contract.get("active_task") or {}),
            "interactive_task_state": _compact_task_state(request.dialogue_contract.get("interactive_task_state") or {}),
            "dialogue_state": {
                "relation": request.dialogue_contract.get("relation"),
                "continuation": bool(request.dialogue_contract.get("continuation")),
                "sequence_id": _text(request.dialogue_contract.get("sequence_id")),
                "resolved_request": request.dialogue_contract.get("resolved_request"),
            },
            "semantic_scene_state": {
                "relation": request.dialogue_contract.get("relation"),
                "continuation": bool(request.quantum_state.get("continuation")),
                "resolved_request": request.intent.get("resolved_request"),
                "representation": request.intent.get("type"),
                "active_task": _compact(request.conversation.get("active_task")),
            },
        })

        _hydrate_scene_artifacts(response, request)

        scene = build_machine_scene(response)
        scene.contract = build_scene_contract(scene)
        contract = scene.contract

        # build_scene_contract already produced the canonical v3.1 signal.
        # Never downgrade it to an older Web signal or rebuild the scene here.
        contract.metadata = dict(contract.metadata or {})
        contract.metadata["processor_interpretation"] = {
            "relation": request.dialogue_contract.get("relation"),
            "representation": request.intent.get("type"),
            "operation": request.intent.get("operation"),
            "goal": request.intent.get("goal"),
            "resolved_request": request.intent.get("resolved_request"),
        }
        contract.metadata["web_delivery"] = {
            "version": "scene_contract_v3_1",
            "source": "C_ARTIFACT_CONTRACT.build_scene_contract",
            "render_blocks_canonical": True,
            "renderer_reinterpretation": False,
            "duplicate_rebuild": False,
            "single_visible_stream": True,
            "identity_bound": True,
        }
        contract.signal = build_scene_signal(contract)
        contract.blocks = list(contract.render_blocks)
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
        expected = {str(x).lower() for x in request.requested_outputs}
        representation_plan = request.constraints.get("representation_plan", {}) if isinstance(request.constraints, dict) else {}
        if isinstance(representation_plan, dict):
            expected.update(str(x).lower() for x in (representation_plan.get("requested_outputs") or []))
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
            # Do not discard a valid provider artifact merely because a stale
            # requested_outputs list omitted one member of the already-built
            # composite scene. Only reject an unplanned structured block.
            if kind not in expected and kind not in {"text", "markdown"}:
                provider_plan = {str(x).lower() for x in (raw.get("scene_plan") or [])} if isinstance(raw.get("scene_plan"), list) else set()
                scene_plan = request.conversation.get("scene_blueprint") if isinstance(request.conversation.get("scene_blueprint"), dict) else {}
                blueprint_reps = {str(x).lower() for x in (scene_plan.get("representations") or [])}
                if kind not in provider_plan and kind not in blueprint_reps:
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



def _normalize_interactive_task(value: Any) -> dict[str, Any]:
    """Normalize the cross-layer interactive task state without owning routing."""
    if not isinstance(value, dict):
        return {}

    nested = value.get("interactive_task_state") or value.get("open_task") or value.get("active_task")
    merged = dict(value)
    if isinstance(nested, dict):
        merged.update(nested)

    active = bool(
        merged.get("active")
        or merged.get("open")
        or merged.get("pending_input")
        or merged.get("status") in {"open", "active", "answer_received", "assistant_turn"}
        or merged.get("kind") in {"game", "riddle", "question", "choice"}
    )
    if not active:
        return {}

    task = {
        "active": True,
        "status": _text(merged.get("status") or "open").lower(),
        "kind": _text(merged.get("kind") or merged.get("type") or "task").lower(),
        "role": _text(merged.get("role") or merged.get("task_role")),
        "phase": _text(merged.get("phase") or merged.get("task_phase")),
        "prompt": _text(merged.get("prompt") or merged.get("task_prompt") or merged.get("question")),
        "last_question": _text(merged.get("last_question") or merged.get("question")),
        "expected_input_type": _text(merged.get("expected_input_type") or merged.get("input_type") or "answer"),
        "target": _text(merged.get("target") or merged.get("target_entity")),
        "secret_target": _text(
            merged.get("secret_target")
            or merged.get("hidden_target")
            or merged.get("private_target")
        ),
        "candidate_answer": _text(merged.get("candidate_answer") or merged.get("answer_candidate")),
        "last_user_answer": _text(merged.get("last_user_answer") or merged.get("user_answer")),
        "last_user_action": _text(merged.get("last_user_action")),
        "known_clues": list(merged.get("known_clues") or [])[-12:],
        "qa_history": list(merged.get("qa_history") or merged.get("turns") or [])[-12:],
        "turns": list(merged.get("qa_history") or merged.get("turns") or [])[-12:],
        "awaiting_user": bool(
            merged.get("awaiting_user")
            or merged.get("awaiting_input")
            or merged.get("expected_input_type") in {"answer", "user_answer"}
        ),
        "completed": bool(merged.get("completed")),
        "topic": _text(merged.get("topic") or merged.get("canonical_topic")),
        "goal": _text(merged.get("goal") or merged.get("task_goal")),
        "sequence_id": _text(merged.get("sequence_id") or merged.get("active_sequence_id")),
        "scene_id": _text(merged.get("scene_id") or merged.get("source_scene_id")),
        "task_revision": int(merged.get("task_revision") or 0),
        "source": _text(merged.get("source") or "executor_task_bridge"),
        "replacement_requested": bool(merged.get("replacement_requested")),
        "reset_memory": bool(merged.get("reset_memory")),
    }
    return task


def _provider_task_state(response: MachineResponse) -> dict[str, Any]:
    metadata = response.metadata if isinstance(response.metadata, dict) else {}
    candidates = [
        metadata.get("dialogue_task_state"),
        metadata.get("interactive_task_state"),
        metadata.get("open_task"),
        metadata.get("task_state"),
    ]
    scene = response.scene if isinstance(response.scene, dict) else {}
    candidates.extend([
        scene.get("interactive_task_state"),
        scene.get("open_task"),
        scene.get("task_state"),
    ])
    for value in candidates:
        task = _normalize_interactive_task(value)
        if task:
            return task
    return {}


def _advance_task_from_answer(task: dict[str, Any], request_text: str, answer: str) -> dict[str, Any]:
    """Merge the provider turn into the task state while preserving its history."""
    task = _normalize_interactive_task(task)
    if not task:
        return {}

    answer_text = _text(answer)
    merged = dict(task)

    # Provider metadata is authoritative when present; this fallback only derives
    # the next waiting phase from the semantic shape of the actual answer.
    lower_answer = answer_text.lower()
    qa_history = list(merged.get("qa_history") or [])

    if request_text:
        last_kind = "task_action" if not merged.get("awaiting_user") and merged.get("last_user_action") else "turn"
        if merged.get("candidate_answer") == _text(request_text):
            last_kind = "answer"
        if not qa_history or qa_history[-1].get("user") != _text(request_text):
            qa_history.append({
                "user": _text(request_text),
                "assistant_prompt": _text(merged.get("last_question") or merged.get("prompt")),
                "kind": last_kind,
            })

    merged["qa_history"] = qa_history[-12:]
    merged["turns"] = list(merged["qa_history"])

    # A provider question means the user now owns the next turn.
    if "?" in answer_text or "？" in answer_text:
        merged["last_question"] = answer_text
        merged["prompt"] = answer_text
        merged["phase"] = "awaiting_user_answer"
        merged["status"] = "open"
        merged["expected_input_type"] = "answer"
        merged["awaiting_user"] = True
    elif merged.get("role") == "april_holds_secret":
        # The setup response establishes the game and asks the user to begin.
        if any(x in lower_answer for x in ("загадал", "загадала", "уже загад", "задавай вопросы", "угадай слово")):
            merged["phase"] = "awaiting_user_input"
            merged["status"] = "open"
            merged["expected_input_type"] = "answer"
            merged["awaiting_user"] = True
    if "угадал" in lower_answer and not ("не угадал" in lower_answer):
        merged["completed"] = True
        merged["status"] = "completed"
        merged["phase"] = "completed"
        merged["awaiting_user"] = False

    merged["task_revision"] = int(merged.get("task_revision") or 0) + 1
    merged["source"] = "executor_live_task_state"
    return merged


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

    # Interactive task state has its own ownership. It must survive provider
    # execution and must never be replaced by the generic topic task.
    request_task = _normalize_interactive_task(
        dialogue.get("interactive_task_state")
        or dialogue.get("open_task")
        or dialogue.get("active_task")
    )
    response_task = _provider_task_state(response)
    task = dict(request_task)
    if response_task:
        task.update(response_task)

    if task:
        task = _advance_task_from_answer(
            task,
            request.conversation.get("current_request", ""),
            response.answer,
        )
        state["interactive_task_state"] = _compact(task, max_depth=5, max_items=16)
        state["open_task"] = _compact(task, max_depth=5, max_items=16)
        state["active_task"] = _compact(task, max_depth=5, max_items=16)
        # `april_active_task` remains the compatibility mirror, but it mirrors
        # the semantic task rather than rebuilding one from topic/object.
        state["april_active_task"] = _compact(task, max_depth=5, max_items=16)
    else:
        # Only replace the compatibility task when no interactive task exists.
        state["april_active_task"] = {
            "operation": operation,
            "object": topic,
            "representation": representation,
            "goal": goal,
            "topic": topic,
        }
        state["interactive_task_state"] = {}
        state["open_task"] = {}
        state["active_task"] = {}

    # Generic active entity is a discourse entity, not a hidden secret target.
    entity = _person_entity_from_answer(response.answer)
    if not entity:
        entity = _text(
            dialogue.get("active_entity")
            or dialogue.get("resolved_entity")
            or dialogue.get("resolved_reference")
        )
    state["april_active_entity"] = entity

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
        "target_sequence_id": dialogue.get("sequence_id") or dialogue.get("target_sequence_id"),
        "sequence_continuation_authorized": bool(dialogue.get("continuation")),
        "current_turn_authority": True,
        "historical_memory_is_evidence_only": True,
        "interactive_task_state": _compact_task_state(task) if task else {},
        "task_memory": _compact({
            "role": task.get("role"),
            "phase": task.get("phase"),
            "last_question": task.get("last_question"),
            "known_clues": task.get("known_clues"),
            "qa_history": task.get("qa_history"),
            "candidate_answer": task.get("candidate_answer"),
        }, max_depth=5, max_items=16) if task else {},
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
        "interactive_task_state": _compact_task_state(task) if task else {},
        "source": "semantic_interpretation_layer",
    }

    provider_plan = (
        request.conversation.get("provider_context_plan")
        if isinstance(request.conversation, dict)
        and isinstance(request.conversation.get("provider_context_plan"), dict)
        else {}
    )
    state["interpretation_provider_context_plan"] = _compact(provider_plan, max_depth=7, max_items=14)
    state["provider_context_authority"] = "INTERPRETATION"

    state["april_live_context"] = {
        "version": "april_live_context_v3_provider_context",
        "relation": relation,
        "active_topic": topic,
        "active_goal": goal,
        "active_task": _compact(state.get("april_active_task")),
        "interactive_task_state": _compact_task_state(task) if task else {},
        "pending_task": _compact(state.get("april_pending_task")),
        "last_user_turn": _text(state.get("last_user_turn")),
        "last_april_turn": _text(state.get("last_april_turn")),
        "active_entity": _text(state.get("april_active_entity")),
        "dialogue_strategy": _compact(dialogue.get("dialogue_strategy") if isinstance(dialogue, dict) else {}),
        "continuation_content_analysis": _compact(dialogue.get("continuation_content_analysis") if isinstance(dialogue, dict) else {}),
        "scene_id": _text(getattr(contract, "scene_id", "")),
        "render_types": [_text(b.get("type")).lower() for b in blocks if isinstance(b, dict)],
        "current_user_request": _text(request.conversation.get("current_request")),
        "provider_context_plan": _compact(provider_plan, max_depth=7, max_items=14),
        "provider_context_authority": "INTERPRETATION",
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


async def _route_image_through_room_registry(
    response: MachineResponse,
    request: MachineRequest,
    state: dict,
    user_id: str,
    chat_id=None,
    run_with_activity: Optional[Callable[..., Awaitable[Any]]] = None,
) -> None:
    """Route an image request through C-ARTIFACT -> Room Register.

    Interpretation owns the representation and dialogue continuity. Provider
    remains a single semantic call. The Room Register then executes the already
    authorized image task; concrete raster production stays below the room in
    C_APRIL_IMAGES_GENERATOR. Executor only merges the room result into the
    canonical SceneContract stream.
    """
    constraints = request.constraints if isinstance(request.constraints, dict) else {}
    plan = constraints.get("representation_plan")
    plan = plan if isinstance(plan, dict) else {}

    representation = _text(request.intent.get("type")).lower()
    requested_outputs = {
        _text(x).lower()
        for x in (request.requested_outputs or [])
        if _text(x)
    }
    requested_outputs.update(
        _text(x).lower()
        for x in (plan.get("requested_outputs") or [])
        if _text(x)
    )

    visual_requested = representation in {"image", "gallery"} or bool(
        {"image", "gallery"} & requested_outputs
    )
    if not visual_requested:
        return

    metadata = dict(response.metadata or {})

    def _concrete_image_payload(payload: dict[str, Any]) -> bool:
        if not isinstance(payload, dict):
            return False
        direct = (
            payload.get("src")
            or payload.get("url")
            or payload.get("image")
            or payload.get("image_data_uri")
            or payload.get("image_base64")
        )
        if direct:
            return True
        images = payload.get("images")
        if isinstance(images, list):
            for item in images:
                if isinstance(item, str) and item.strip():
                    return True
                if isinstance(item, dict):
                    if any(
                        item.get(key)
                        for key in (
                            "src", "url", "image", "image_url",
                            "image_data_uri", "image_base64"
                        )
                    ):
                        return True
        return False

    # A true concrete image is already a valid artifact result. Preserve it and
    # do not run a second image operation.
    concrete_provider_image = False
    for block in list(response.render_blocks or []):
        if not isinstance(block, dict):
            continue
        kind = _text(
            block.get("type")
            or block.get("artifact_type")
            or block.get("representation")
        ).lower()
        if kind not in {"image", "gallery"}:
            continue
        payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
        if _concrete_image_payload(payload):
            concrete_provider_image = True
            break

    if concrete_provider_image:
        metadata.update({
            "image_generation_status": "provider_artifact_preserved",
            "renderer_route": "INTERPRETATION→PROVIDER→C_ARTIFACT→ROOM_REGISTER→ROOM→C_ARTIFACT→SCENE_CONTRACT→WEB",
            "room_route_status": "not_needed_provider_artifact",
        })
        response.metadata = metadata
        return

    provider_metadata = dict(response.metadata or {})
    provider_answer = _text(
        response.answer or response.content or response.response
    )

    conversation = request.conversation if isinstance(request.conversation, dict) else {}
    dialogue_contract = conversation.get("dialogue_contract")
    dialogue_contract = dialogue_contract if isinstance(dialogue_contract, dict) else {}

    route_contract = build_room_route_contract(
        request,
        origin="executor",
        destination="rooms_registry",
        pipeline_stage="artifact_route",
        context={
            "current_user_request": _text(conversation.get("current_request") or request.intent.get("normalized_text")),
            "resolved_request": _text(conversation.get("resolved_request") or request.intent.get("resolved_request")),
            "semantic_request": _text(request.intent.get("semantic_request") or request.intent.get("resolved_request")),
            "dialogue_contract": deepcopy(dialogue_contract),
            "dialogue_vector": deepcopy(conversation.get("dialogue_vector") or {}),
            "semantic_frame": deepcopy(conversation.get("semantic_frame") or {}),
            "visual_context": deepcopy(request.visual_context or {}),
            "provider_metadata": deepcopy(provider_metadata),
            "provider_answer": provider_answer,
        },
        metadata={
            "request_id": str(request.request_id),
            "representation": representation,
            "route": "C_ARTIFACT→ROOM_REGISTER→ROOM",
        },
    )

    try:
        room_response = await registry_route_machine_request(
            request,
            route_contract,
            user_id=_text(user_id),
            chat_id=chat_id,
            state=state,
            provider_response=response,
            run=run_with_activity,
        )
    except Exception as exc:
        metadata.update({
            "image_generation_status": "failed",
            "image_generation_error": str(exc),
            "room_route_status": "dispatch_error",
            "renderer_route": "INTERPRETATION→PROVIDER→C_ARTIFACT→ROOM_REGISTER→ROOM→C_ARTIFACT→SCENE_CONTRACT→WEB",
        })
        response.metadata = metadata
        print("⚠️ APRIL IMAGE ROOM ROUTE:", exc)
        return

    room_blocks = [
        dict(block)
        for block in list(getattr(room_response, "render_blocks", []) or [])
        if isinstance(block, dict)
    ]
    room_artifacts = [
        artifact
        for artifact in list(getattr(room_response, "artifacts", []) or [])
        if isinstance(artifact, BaseArtifact)
    ]
    room_metadata = dict(getattr(room_response, "metadata", {}) or {})

    # If the room did not produce a concrete artifact, keep the provider text and
    # diagnostics intact rather than inventing a visual block.
    concrete_room_blocks = []
    for block in room_blocks:
        kind = _text(
            block.get("type")
            or block.get("artifact_type")
            or block.get("representation")
        ).lower()
        if kind in {"image", "gallery"}:
            payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
            if _concrete_image_payload(payload):
                concrete_room_blocks.append(block)

    if concrete_room_blocks:
        preserved = []
        for block in list(response.render_blocks or []):
            if not isinstance(block, dict):
                continue
            kind = _text(
                block.get("type")
                or block.get("artifact_type")
                or block.get("representation")
            ).lower()
            if kind not in {"image", "gallery"}:
                preserved.append(block)
                continue
            payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
            if _concrete_image_payload(payload):
                preserved.append(block)

        existing_signatures = {
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
            for block in preserved
        }

        response.render_blocks = preserved
        for block in concrete_room_blocks:
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
            if sig not in existing_signatures:
                existing_signatures.add(sig)
                response.render_blocks.append(block)

    if room_artifacts:
        existing_artifacts = [
            artifact
            for artifact in list(response.artifacts or [])
            if isinstance(artifact, BaseArtifact)
        ]
        known_ids = {
            _text(getattr(getattr(item, "metadata", None), "artifact_id", ""))
            for item in existing_artifacts
        }
        for artifact in room_artifacts:
            artifact_id = _text(
                getattr(getattr(artifact, "metadata", None), "artifact_id", "")
            )
            if not artifact_id or artifact_id not in known_ids:
                existing_artifacts.append(artifact)
                if artifact_id:
                    known_ids.add(artifact_id)
        response.artifacts = existing_artifacts
        response.artifacts_payload = [
            deepcopy(getattr(item, "data", {}) or {})
            for item in existing_artifacts
        ]

    route_status = _text(
        room_metadata.get("room_route_status")
        or ("completed" if concrete_room_blocks else "no_artifact")
    )

    metadata.update(room_metadata)
    metadata.update({
        "image_generation_status": (
            "success" if concrete_room_blocks else
            room_metadata.get("image_generation_status") or "not_materialized"
        ),
        "image_generation_engine": (
            room_metadata.get("image_generation_engine")
            or ("C_APRIL_IMAGES_GENERATOR" if concrete_room_blocks else "")
        ),
        "room_route_status": route_status,
        "room_route": room_metadata.get("room_route") or "rooms_registry.image_generate",
        "artifact_route": "C_ARTIFACT_CONTRACT",
        "renderer_route": "INTERPRETATION→PROVIDER→C_ARTIFACT→ROOM_REGISTER→ROOM→C_ARTIFACT→SCENE_CONTRACT→WEB",
        "provider_calls_added": 0,
        "room_artifact_count": len(room_artifacts),
        "room_render_block_count": len(concrete_room_blocks),
    })
    response.metadata = metadata

    # Keep the canonical generation spec in StateManager so a later visual
    # continuation can resolve against the same dialogue sequence/artifact.
    spec = provider_metadata.get("image_generation_spec")
    if not isinstance(spec, dict):
        specs = provider_metadata.get("image_generation_specs")
        if isinstance(specs, list):
            spec = next((item for item in specs if isinstance(item, dict)), None)
    if isinstance(spec, dict):
        state["image_generation_spec"] = deepcopy(spec)
        state["last_image_generation_route"] = (
            "INTERPRETATION→C_ARTIFACT→ROOM_REGISTER→image_generate→C_APRIL_IMAGES_GENERATOR"
        )

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
    print("🧭 APRIL FLOW:", "INPUT → INTERPRETATION+LIVE_MEMORY → OPENAI → C_ARTIFACT → ROOM_REGISTER → ROOM → C_ARTIFACT → SCENE → WEB")
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
        await _route_image_through_room_registry(
            preview_response,
            request,
            state,
            _text(user_id),
            chat_id=chat_id,
            run_with_activity=run_with_activity,
        )
        machine_preview["render_blocks"] = list(preview_response.render_blocks or [])
        machine_preview["metadata"] = dict(preview_response.metadata or {})
        provider_contract["machine_response"] = machine_preview

    response, scene, contract = processor.build_scene(request, provider_contract)
    response.metadata["timing"] = {"provider_ms": provider_ms}

    # Post-result goal analysis is read-only. It decides only whether a difficult
    # completed turn deserves a natural synthesis; ordinary turns remain plain.
    semantic_for_goal = {
        "semantic_frame": request.intent.get("semantic_frame") if isinstance(request.intent, dict) else {},
        "dialogue_contract": request.dialogue_contract or {},
        "active_goal": request.intent.get("goal") if isinstance(request.intent, dict) else "",
        "active_topic": (request.dialogue_contract or {}).get("canonical_topic"),
        "visual_production_mode": ((request.constraints or {}).get("representation_plan") or {}).get("visual_production_mode"),
        "interactive_task_state": (request.dialogue_contract or {}).get("interactive_task_state") or {},
    }
    goal_progress = evaluate_goal_progress(
        request_text,
        state,
        semantic_for_goal,
        response={
            "answer": response.answer,
            "content": response.content,
            "render_blocks": list(getattr(response, "render_blocks", []) or []),
        },
    )
    completion_decision = build_completion_decision(goal_progress, semantic_for_goal)
    response.metadata["goal_progress"] = goal_progress
    response.metadata["completion_decision"] = completion_decision

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
        "provider_context_plan": (request.conversation or {}).get("provider_context_plan", {}),
        "provider_context_authority": "INTERPRETATION",
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
