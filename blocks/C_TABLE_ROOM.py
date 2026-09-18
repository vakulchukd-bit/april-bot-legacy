# =====================================================
# APRIL C_TABLE_ROOM — CANONICAL SCENE TABLE ENGINE
# =====================================================
"""
Role:
    Normalize explicit table data into one canonical artifact.

This room does not parse user language, route requests, or create placeholder
rows. Missing semantic table data is a missing input, not a reason to invent it.
"""

from __future__ import annotations

from copy import deepcopy
import uuid
from typing import Any, Dict, List, Optional

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact


ROOM_ID = "C_TABLE_ROOM"
ARTIFACT_TYPE = "table"
RENDERER = "TableBlock"


def _obj(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        return list(value.values())
    return []


def _identity(task: Dict[str, Any]) -> Dict[str, Any]:
    scene = _obj(task.get("scene"))
    scene_id = _text(task.get("scene_id") or scene.get("scene_id"))
    turn_id = _text(task.get("turn_id") or scene.get("turn_id"))
    flow_id = _text(task.get("flow_id") or scene.get("flow_id"))
    topic_group = _text(task.get("topic_group") or scene.get("topic_group"))
    block_id = _text(task.get("block_id") or scene.get("block_id"))
    render_id = _text(task.get("render_id") or scene.get("render_id"))

    generated = False
    if not scene_id:
        scene_id = f"scene_{uuid.uuid4().hex[:12]}"
        generated = True
    if not turn_id:
        turn_id = f"turn_{uuid.uuid4().hex[:12]}"
        generated = True
    if not block_id:
        block_id = f"table_{uuid.uuid4().hex[:12]}"
        generated = True
    if not render_id:
        render_id = f"{block_id}:render"

    return {
        "scene_id": scene_id,
        "turn_id": turn_id,
        "flow_id": flow_id,
        "topic_group": topic_group,
        "continuation": bool(task.get("continuation", scene.get("continuation", False))),
        "block_id": block_id,
        "render_id": render_id,
        "identity_generated_locally": generated,
    }


def _extract_payload(task: Dict[str, Any]) -> Dict[str, Any]:
    for candidate in (
        task.get("payload"),
        task.get("table_payload"),
        task.get("table"),
        _obj(task.get("semantic")).get("table_payload"),
        _obj(task.get("semantic")).get("table"),
    ):
        if isinstance(candidate, dict) and candidate:
            return deepcopy(candidate)

    payload: Dict[str, Any] = {}
    for key in (
        "title", "caption", "description", "columns", "headers",
        "rows", "data", "column_roles", "cell_roles", "width_policy",
        "wrap", "download", "metadata",
    ):
        if key in task:
            payload[key] = deepcopy(task[key])
    return payload


def _cell(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _normalize_rows(raw_rows: Any, width: int) -> List[List[Any]]:
    rows = _list(raw_rows)
    result: List[List[Any]] = []

    for raw in rows:
        if isinstance(raw, dict):
            result.append([_cell(raw.get(str(i), raw.get(i, ""))) for i in range(width)])
            continue
        if isinstance(raw, (list, tuple)):
            values = [_cell(v) for v in raw]
        else:
            values = [_cell(raw)]

        if width:
            values = values[:width] + [""] * max(0, width - len(values))
        result.append(values)

    return result


def _canonical_payload(task: Dict[str, Any]) -> Dict[str, Any]:
    source = _extract_payload(task)
    identity = _identity(task)

    columns = source.get("columns") or source.get("headers") or []
    if isinstance(columns, str):
        columns = [part.strip() for part in columns.split("|")] if "|" in columns else [columns.strip()]
    columns = [_cell(v) for v in _list(columns)]

    raw_rows = source.get("rows")
    if raw_rows is None:
        raw_rows = source.get("data", [])

    # Object rows are more useful when keyed by the canonical columns.
    if _list(raw_rows) and isinstance(_list(raw_rows)[0], dict) and columns:
        normalized_rows: List[List[Any]] = []
        for row in _list(raw_rows):
            normalized_rows.append([
                _cell(row.get(column, ""))
                for column in columns
            ])
    elif _list(raw_rows) and isinstance(_list(raw_rows)[0], dict):
        object_rows = _list(raw_rows)
        discovered = []
        for row in object_rows:
            for key in row:
                if key not in discovered:
                    discovered.append(key)
        columns = [_cell(v) for v in discovered]
        normalized_rows = [
            [_cell(row.get(column, "")) for column in columns]
            for row in object_rows
        ]
    else:
        width = len(columns)
        raw_list = _list(raw_rows)
        if not width and raw_list:
            width = max(
                (len(row) if isinstance(row, (list, tuple)) else 1)
                for row in raw_list
            )
            columns = [f"Column {i + 1}" for i in range(width)]
        normalized_rows = _normalize_rows(raw_rows, width)

    if not columns or not normalized_rows:
        raise ValueError(
            "C_TABLE_ROOM requires explicit columns/rows; "
            "placeholder table data is not allowed."
        )

    return {
        "scene_type": "table",
        "artifact_type": "table",
        "title": _text(source.get("title") or task.get("title"), "Table"),
        "caption": _text(source.get("caption") or task.get("caption")),
        "description": _text(
            source.get("description") or task.get("description")
        ),
        "columns": columns,
        "headers": columns,
        "rows": normalized_rows,
        "column_roles": deepcopy(source.get("column_roles") or []),
        "cell_roles": deepcopy(source.get("cell_roles") or []),
        "width_policy": _text(
            source.get("width_policy") or task.get("width_policy"),
            "adaptive",
        ),
        "wrap": bool(source.get("wrap", task.get("wrap", True))),
        "download": bool(source.get("download", task.get("download", True))),
        "table_schema": "april.table.scene.v3",
        "scene": {
            **identity,
            "node_type": "table",
            "renderer": RENDERER,
            "role": _text(task.get("role"), "source_data"),
        },
        "render_identity": identity,
        "presentation": {
            "renderer": RENDERER,
            "engine": "McDowell",
            "math_engine": "KaTeX",
            "route": "canonical",
            "single_scene": True,
            "adaptive_width": True,
            "preserve_cells": True,
            "payload_unchanged": True,
        },
        "metadata": {
            **_obj(source.get("metadata")),
            "room": ROOM_ID,
            "scene_id": identity["scene_id"],
            "turn_id": identity["turn_id"],
        },
    }


class TableRoom(Room):
    name = "table"
    room_type = "table_renderer"
    artifact_type = ARTIFACT_TYPE
    artifact_version = "3.0"
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

        if "table" in normalized or "tableblock" in normalized:
            return 1.0
        if ctx.get("trajectory") == "table":
            return 0.5

        payload = ctx.get("table_payload") or semantic.get("table_payload")
        return 1.0 if isinstance(payload, dict) and payload else 0.0

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
            "payload": deepcopy(ctx.get("table_payload") or ctx.get("payload") or {}),
        }

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
                "scene_contributions": [{
                    "scene_id": identity["scene_id"],
                    "block_id": identity["block_id"],
                    "type": ARTIFACT_TYPE,
                    "renderer": RENDERER,
                }],
                "presentation": payload["presentation"],
            },
        )
        valid = bool(payload["columns"] and payload["rows"])
        artifact.quality.validation_passed = valid
        artifact.quality.quality_score = 1.0 if valid else 0.0
        artifact.quality.confidence_score = 1.0 if valid else 0.0
        artifact.quality.completeness_score = 1.0 if valid else 0.0
        return artifact

    def execute(self, machine_request: Any):
        if isinstance(machine_request, dict):
            return self.process(machine_request)
        return None

    async def handle(self, user_id, text, context, run):
        # Text is not parsed. The table must arrive as structured Processor data.
        ctx = context if isinstance(context, dict) else {}
        task = self.build_work_order(ctx)
        return self.process(task)


ROOM = TableRoom()
