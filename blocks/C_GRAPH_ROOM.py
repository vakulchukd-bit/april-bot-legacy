# =====================================================
# APRIL C_GRAPH_ROOM — CANONICAL SCENE GRAPH ENGINE
# =====================================================
"""
Role:
    Build exactly one graph artifact from structured semantic data.

Architecture:
    Processor -> Scene Blueprint -> C_GRAPH_ROOM -> Artifact Contract
               -> SceneContract -> RenderMessage -> GraphBlock

This room is NOT a router and does not infer graph intent from natural
language. It consumes explicit structured graph data produced by the
Quantum Processor.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import uuid
from typing import Any, Dict, Iterable, List, Optional

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact


ROOM_ID = "C_GRAPH_ROOM"
ARTIFACT_TYPE = "graph"
RENDERER = "GraphBlock"


def _obj(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        return list(value.values())
    return []


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _number(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def _identity(task: Dict[str, Any]) -> Dict[str, Any]:
    scene = _obj(task.get("scene"))
    blueprint = _obj(task.get("scene_blueprint"))
    source = _obj(task.get("source_context"))

    scene_id = (
        _text(task.get("scene_id"))
        or _text(scene.get("scene_id"))
        or _text(blueprint.get("scene_id"))
    )
    turn_id = (
        _text(task.get("turn_id"))
        or _text(scene.get("turn_id"))
        or _text(source.get("turn_id"))
    )
    flow_id = (
        _text(task.get("flow_id"))
        or _text(scene.get("flow_id"))
        or _text(source.get("flow_id"))
    )
    topic_group = (
        _text(task.get("topic_group"))
        or _text(scene.get("topic_group"))
        or _text(blueprint.get("topic_group"))
    )
    continuation = bool(
        task.get("continuation", scene.get("continuation", False))
    )

    generated = False
    if not scene_id:
        scene_id = f"scene_{uuid.uuid4().hex[:12]}"
        generated = True
    if not turn_id:
        turn_id = f"turn_{uuid.uuid4().hex[:12]}"
        generated = True

    block_id = _text(
        task.get("block_id")
        or scene.get("block_id")
    )
    if not block_id:
        block_id = f"graph_{uuid.uuid4().hex[:12]}"
        generated = True

    render_id = _text(
        task.get("render_id")
        or scene.get("render_id")
    ) or f"{block_id}:render"

    return {
        "scene_id": scene_id,
        "turn_id": turn_id,
        "flow_id": flow_id,
        "topic_group": topic_group,
        "continuation": continuation,
        "block_id": block_id,
        "render_id": render_id,
        "identity_generated_locally": generated,
    }


def _structured_payload(task: Dict[str, Any]) -> Dict[str, Any]:
    candidates = [
        task.get("payload"),
        task.get("graph_payload"),
        task.get("graph"),
        _obj(task.get("semantic")).get("graph_payload"),
        _obj(task.get("semantic")).get("graph"),
    ]
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate:
            return deepcopy(candidate)

    # Accept a JSON object supplied through a machine envelope only.
    for candidate in (
        task.get("machine_payload"),
        task.get("machine_response"),
    ):
        if isinstance(candidate, dict):
            return deepcopy(candidate)
        if isinstance(candidate, str):
            try:
                decoded = json.loads(candidate)
            except (TypeError, ValueError):
                continue
            if isinstance(decoded, dict):
                return decoded

    return {
        key: deepcopy(task[key])
        for key in (
            "title", "description", "representation",
            "series", "labels", "values", "x_values", "y_values",
            "x_axis", "y_axis", "x_label", "y_label",
            "x_domain", "y_domain", "legend", "annotations",
            "markers", "reference_lines", "regions",
            "visual_elements", "matrix", "fn", "equation",
            "expression", "function", "grid", "style", "metadata",
        )
        if key in task
    }


def _normalize_series(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_series = _list(payload.get("series"))
    result: List[Dict[str, Any]] = []

    for index, item in enumerate(raw_series):
        if isinstance(item, dict):
            series = deepcopy(item)
        elif isinstance(item, (list, tuple)):
            series = {"values": list(item)}
        else:
            continue

        points = _list(series.get("points"))
        if points:
            normalized_points = []
            for point in points:
                if isinstance(point, dict):
                    x = point.get("x")
                    y = _number(point.get("y"))
                    if y is not None and x is not None:
                        normalized_points.append({"x": x, "y": y})
            if normalized_points:
                series["points"] = normalized_points

        x_values = _list(series.get("x") or series.get("x_values"))
        y_values = _list(series.get("y") or series.get("y_values"))
        if x_values and y_values:
            pairs = []
            for x_value, y_value in zip(x_values, y_values):
                numeric_y = _number(y_value)
                if numeric_y is not None:
                    pairs.append({"x": x_value, "y": numeric_y})
            if pairs:
                series["points"] = pairs
                series["x"] = [p["x"] for p in pairs]
                series["y"] = [p["y"] for p in pairs]

        if not series.get("label"):
            series["label"] = f"Series {index + 1}"
        result.append(series)

    if result:
        return result

    labels = _list(payload.get("labels") or payload.get("x_values"))
    values = _list(payload.get("values") or payload.get("y_values"))
    if labels and values:
        pairs = []
        for x_value, y_value in zip(labels, values):
            numeric_y = _number(y_value)
            if numeric_y is not None:
                pairs.append({"x": x_value, "y": numeric_y})
        if pairs:
            return [{
                "label": _text(payload.get("series_name") or payload.get("title"), "Series"),
                "type": "points",
                "points": pairs,
                "x": [p["x"] for p in pairs],
                "y": [p["y"] for p in pairs],
            }]

    function_value = (
        payload.get("fn")
        or payload.get("equation")
        or payload.get("expression")
        or payload.get("function")
    )
    if isinstance(function_value, str) and function_value.strip():
        return [{
            "label": _text(payload.get("label") or payload.get("title"), "f(x)"),
            "type": "function",
            "fn": function_value.strip(),
        }]

    return []


def _normalize_axis(value: Any, fallback_title: str) -> Dict[str, Any]:
    if isinstance(value, dict):
        axis = deepcopy(value)
    else:
        axis = {}
    axis.setdefault("title", fallback_title)
    return axis


def _canonical_payload(task: Dict[str, Any]) -> Dict[str, Any]:
    payload = _structured_payload(task)
    identity = _identity(task)

    series = _normalize_series(payload)
    if not series:
        raise ValueError(
            "C_GRAPH_ROOM requires structured graph data; "
            "the room does not invent a graph from user text."
        )

    representation = _text(
        payload.get("representation")
        or payload.get("chart_type")
        or payload.get("graph_type")
        or ("function" if any(s.get("fn") for s in series) else "line"),
        "line",
    ).lower()

    title = _text(payload.get("title") or task.get("title"), "Graph")
    description = _text(
        payload.get("description") or task.get("description")
    )

    x_axis = _normalize_axis(
        payload.get("x_axis"),
        _text(payload.get("x_label"), "X"),
    )
    y_axis = _normalize_axis(
        payload.get("y_axis"),
        _text(payload.get("y_label"), "Y"),
    )

    canonical = deepcopy(payload)
    canonical.update({
        "scene_type": "graph",
        "artifact_type": "graph",
        "representation": representation,
        "title": title,
        "description": description,
        "series": series,
        "x_axis": x_axis,
        "y_axis": y_axis,
        "x_label": _text(payload.get("x_label") or x_axis.get("title")),
        "y_label": _text(payload.get("y_label") or y_axis.get("title")),
        "scene": {
            **identity,
            "node_type": "graph",
            "renderer": RENDERER,
            "role": _text(task.get("role"), "visualization"),
        },
        "render_identity": identity,
        "presentation": {
            "renderer": RENDERER,
            "engine": "GraphBlock",
            "route": "canonical",
            "single_scene": True,
            "adaptive_width": True,
            "preserve_payload": True,
        },
    })

    if "x_domain" in payload:
        canonical["x_domain"] = deepcopy(payload["x_domain"])
    if "y_domain" in payload:
        canonical["y_domain"] = deepcopy(payload["y_domain"])

    canonical.setdefault("grid", True)
    canonical.setdefault("metadata", {})
    canonical["metadata"] = {
        **_obj(canonical.get("metadata")),
        "room": ROOM_ID,
        "scene_id": identity["scene_id"],
        "turn_id": identity["turn_id"],
    }
    return canonical


class GraphRoom(Room):
    """Canonical graph construction node; no routing or text inference."""

    name = "graph"
    room_type = "graph_renderer"
    artifact_type = ARTIFACT_TYPE
    artifact_version = "2.0"
    web_space_ready = True
    renderer_safe = True
    continuity_safe = True
    orchestration_safe = True

    def can_handle(self, text: Any, context: Any) -> bool:
        return self.evaluate(text, context) > 0.0

    def evaluate(self, text: Any, context: Any) -> float:
        ctx = context if isinstance(context, dict) else {}
        semantic = _obj(ctx.get("semantic"))
        blueprint = _obj(ctx.get("scene_blueprint"))
        representations = (
            _list(semantic.get("renderers"))
            + _list(semantic.get("representations"))
            + _list(blueprint.get("renderers"))
            + _list(blueprint.get("representations"))
        )
        normalized = {str(v).strip().lower() for v in representations}
        if "graph" in normalized or "graphblock" in normalized:
            return 1.0
        if ctx.get("trajectory") == "graph":
            return 0.5
        payload = ctx.get("graph_payload") or semantic.get("graph_payload")
        if isinstance(payload, dict) and payload:
            return 1.0
        return 0.0

    def process(self, task: Dict[str, Any]):
        payload = _canonical_payload(dict(task or {}))
        identity = payload["scene"]
        artifact = create_artifact(
            artifact_type=ARTIFACT_TYPE,
            room_source=ROOM_ID,
            data={
                "title": payload["title"],
                "description": payload["description"],
                "payload": payload,
                "renderer": RENDERER,
                "viewer": RENDERER,
                "scene_id": identity["scene_id"],
                "turn_id": identity["turn_id"],
                "flow_id": identity["flow_id"],
                "topic_group": identity["topic_group"],
                "continuation": identity["continuation"],
                "block_id": identity["block_id"],
                "render_id": identity["render_id"],
                "role": identity["role"] if "role" in identity else payload["scene"]["role"],
                "scene_contributions": [{
                    "scene_id": identity["scene_id"],
                    "block_id": identity["block_id"],
                    "type": ARTIFACT_TYPE,
                    "renderer": RENDERER,
                }],
                "presentation": payload["presentation"],
            },
        )
        artifact.quality.validation_passed = True
        artifact.quality.quality_score = 1.0
        artifact.quality.confidence_score = 1.0
        artifact.quality.completeness_score = 1.0
        return artifact

    def build_work_order(self, context: Optional[Dict[str, Any]] = None):
        ctx = dict(context or {})
        return {
            "scene_id": ctx.get("scene_id"),
            "turn_id": ctx.get("turn_id"),
            "flow_id": ctx.get("flow_id"),
            "topic_group": ctx.get("topic_group"),
            "continuation": ctx.get("continuation", False),
            "block_id": ctx.get("block_id"),
            "render_id": ctx.get("render_id"),
            "role": ctx.get("role"),
            "semantic": deepcopy(_obj(ctx.get("semantic"))),
            "scene_blueprint": deepcopy(_obj(ctx.get("scene_blueprint"))),
            "payload": deepcopy(ctx.get("graph_payload") or ctx.get("payload") or {}),
            "source_context": deepcopy(ctx),
        }

    def execute(self, machine_request: Any):
        if isinstance(machine_request, dict):
            return self.process(machine_request)
        return None

    async def handle(self, user_id, text, context, run):
        # `text` is intentionally not parsed. The Processor must supply the
        # structured graph payload in context.
        ctx = context if isinstance(context, dict) else {}
        task = self.build_work_order({
            **ctx,
            "user_id": user_id,
        })
        return self.process(task)


ROOM = GraphRoom()
