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

from blocks.C_ARTIFACT_CONTRACT import create_artifact


ROOM_ID = "C_TABLE_ROOM"
ARTIFACT_TYPE = "table"
RENDERER = "TableBlock"


def _obj(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    normalized = _cell(value)
    text = str(normalized).strip() if normalized is not None else ""
    return text or default


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
        "title", "caption", "description", "columns", "headers", "column_headers",
        "rows", "data", "column_roles", "cell_roles", "width_policy",
        "wrap", "download", "metadata", "additional_sheets", "sheets",
    ):
        if key in task:
            payload[key] = deepcopy(task[key])
    return payload


def _cell(value: Any, _depth: int = 0) -> Any:
    """Convert structured cell values into readable text, never Python dict repr."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if _depth >= 5:
        return ""

    if isinstance(value, (list, tuple)):
        parts = [_cell(item, _depth + 1) for item in value]
        return " · ".join(str(part).strip() for part in parts if part is not None and str(part).strip())

    if isinstance(value, dict):
        # Prefer user-facing fields over implementation metadata.
        preferred = (
            "display", "display_text", "rendered_text", "text", "markdown",
            "description", "explanation", "summary", "label", "title",
            "name", "symbol", "formula", "content", "value",
        )
        selected = None
        for key in preferred:
            candidate = value.get(key)
            if candidate is not None and candidate != "":
                selected = _cell(candidate, _depth + 1)
                break

        unit = value.get("unit")
        ignored = {
            "id", "key", "type", "kind", "renderer", "viewer", "metadata",
            "scene", "signals", "layout", "role", "priority", "source",
            "source_id", "artifact_type", "artifactType",
        }
        if selected is not None:
            unit_text = _cell(unit, _depth + 1) if unit not in (None, "") else ""
            primary_text = str(selected).strip()
            if unit_text:
                primary_text = f"{primary_text} {str(unit_text).strip()}".strip()
            parts = [primary_text]
            preferred_keys = set(preferred)
            for key, item in value.items():
                if str(key) in ignored or str(key) in preferred_keys or key == "unit" or item is None or item == "":
                    continue
                rendered = _cell(item, _depth + 1)
                if rendered is not None and str(rendered).strip():
                    parts.append(f"{str(key).replace('_', ' ')}: {rendered}")
            return " · ".join(part for part in parts if part)

        parts = []
        for key, item in value.items():
            if str(key) in ignored or item is None or item == "":
                continue
            rendered = _cell(item, _depth + 1)
            if rendered is None or not str(rendered).strip():
                continue
            parts.append(f"{str(key).replace('_', ' ')}: {rendered}")
        return " · ".join(parts)

    return str(value)




def _column_spec(value: Any, index: int) -> tuple[str, str]:
    """Return a stable row accessor and a human-readable Excel header."""
    if isinstance(value, dict):
        key = next((str(value.get(name)).strip() for name in ("key", "field", "accessor", "id", "name", "label", "title") if value.get(name) not in (None, "")), f"column_{index + 1}")
        label = next((str(value.get(name)).strip() for name in ("label", "title", "name", "header", "key", "field", "id") if value.get(name) not in (None, "")), f"Column {index + 1}")
        return key or f"column_{index + 1}", label or f"Column {index + 1}"
    label = str(_cell(value) or f"Column {index + 1}").strip()
    return label, label


def _normalize_sheet(sheet: Any, index: int) -> Dict[str, Any] | None:
    if not isinstance(sheet, dict):
        return None
    nested = sheet.get("payload") if isinstance(sheet.get("payload"), dict) else sheet
    raw_columns = nested.get("headers") or nested.get("columns") or nested.get("column_headers") or []
    if isinstance(raw_columns, str):
        raw_columns = [part.strip() for part in raw_columns.split("|")] if "|" in raw_columns else [raw_columns.strip()]
    specs = [_column_spec(column, position) for position, column in enumerate(_list(raw_columns))]
    if not specs:
        return None
    keys = [key for key, _label in specs]
    labels = [label for _key, label in specs]
    raw_rows = nested.get("rows")
    if raw_rows is None:
        raw_rows = nested.get("data", nested.get("body", nested.get("values", [])))
    source_rows = _list(raw_rows)
    rows: List[List[Any]] = []
    for row in source_rows[:10000]:
        if isinstance(row, dict):
            values = [row.get(key, row.get(labels[position], "")) for position, key in enumerate(keys)]
        elif isinstance(row, (list, tuple)):
            values = list(row[:len(labels)])
        else:
            values = [row]
        values = [_cell(value) for value in values]
        values = values[:len(labels)] + [""] * max(0, len(labels) - len(values))
        rows.append(values)
    if not rows:
        return None
    return {
        **{key: deepcopy(value) for key, value in sheet.items() if key not in {"payload", "headers", "columns", "column_headers", "rows", "data", "body", "values"}},
        "title": _text(nested.get("title") or nested.get("name") or sheet.get("title"), f"Data {index + 1}"),
        "headers": labels,
        "columns": labels,
        "rows": rows,
    }


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

    raw_columns = source.get("columns") or source.get("headers") or source.get("column_headers") or []
    if isinstance(raw_columns, str):
        raw_columns = [part.strip() for part in raw_columns.split("|")] if "|" in raw_columns else [raw_columns.strip()]
    column_specs = [_column_spec(value, index) for index, value in enumerate(_list(raw_columns))]
    column_keys = [key for key, _label in column_specs]
    columns = [label for _key, label in column_specs]

    raw_rows = source.get("rows")
    if raw_rows is None:
        raw_rows = source.get("data", [])

    # Keep descriptor keys for object rows while exporting their readable labels.
    if _list(raw_rows) and isinstance(_list(raw_rows)[0], dict) and columns:
        normalized_rows: List[List[Any]] = []
        for row in _list(raw_rows):
            normalized_rows.append([
                _cell(row.get(key, row.get(columns[index], "")))
                for index, key in enumerate(column_keys)
            ])
    elif _list(raw_rows) and isinstance(_list(raw_rows)[0], dict):
        object_rows = _list(raw_rows)
        discovered = []
        for row in object_rows:
            for key in row:
                if key not in discovered:
                    discovered.append(key)
        columns = [str(_cell(value) or f"Column {index + 1}") for index, value in enumerate(discovered)]
        normalized_rows = [
            [_cell(row.get(key, row.get(str(key), ""))) for key in discovered]
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
        "additional_sheets": [
            normalized for index, sheet in enumerate(_list(source.get("additional_sheets") or source.get("sheets")))
            if (normalized := _normalize_sheet(sheet, index)) is not None
        ],
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


class TableRoom:
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
