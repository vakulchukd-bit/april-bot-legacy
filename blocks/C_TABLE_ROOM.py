# =====================================================
# APRIL C_TABLE_ROOM — CANONICAL TABLE ENGINE
# =====================================================

from typing import Any, Dict, List

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact


class TableRoom(Room):
    """Builds lossless table payloads for the existing single route.

    This room does not select routes, inspect keywords, score requests, or
    create a second rendering path. It only normalizes table data into the
    canonical columns/rows shape consumed by the existing TableBlock.
    """

    name = "table"
    room_type = "visual"
    ROOM_ID = "TABLE_ROOM"
    ARTIFACT_TYPE = "table"

    @staticmethod
    def _cell(value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

    @classmethod
    def _row(cls, row: Any, width: int) -> List[Any]:
        if isinstance(row, dict):
            # Dict rows are kept in column order by the caller.
            values = list(row.values())
        elif isinstance(row, (list, tuple)):
            values = list(row)
        elif isinstance(row, str):
            text = row.strip()
            if "|" in text:
                values = [part.strip() for part in text.split("|")]
            elif "\t" in text:
                values = [part.strip() for part in text.split("\t")]
            else:
                values = [text]
        else:
            values = [row]

        values = [cls._cell(value) for value in values]
        if width > 0:
            if len(values) < width:
                values.extend([""] * (width - len(values)))
            elif len(values) > width:
                values = values[:width]
        return values

    @classmethod
    def normalize_payload(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(data or {})
        columns = data.get("columns") or data.get("headers") or []
        if isinstance(columns, str):
            columns = [x.strip() for x in columns.split("|")] if "|" in columns else [columns.strip()]
        columns = [cls._cell(x) for x in columns if x is not None]

        raw_rows = data.get("rows") or []
        if isinstance(raw_rows, dict):
            raw_rows = list(raw_rows.values())
        elif not isinstance(raw_rows, (list, tuple)):
            raw_rows = [raw_rows]

        rows = [cls._row(row, len(columns)) for row in raw_rows]

        # If rows arrived before headers, derive a stable width without
        # changing the route or inventing semantic columns.
        width = len(columns) or max((len(row) for row in rows), default=0)
        if not columns and width:
            columns = [f"Column {i + 1}" for i in range(width)]
        rows = [cls._row(row, width) for row in rows]

        return {
            "title": data.get("title") or "Table",
            "columns": columns,
            "rows": rows,
            "table_schema": "april.table.canonical.v2",
            "preserve_cells": True,
            "math_render": "mcdowell+katex",
        }

    async def handle(self, user_id, text, context, run):
        # Room execution remains transport-compatible. Actual structured data
        # is supplied through process() by the existing artifact route.
        return {"type": "text", "data": "TABLE ROOM ACTIVE"}

    def process(self, task: Dict[str, Any]):
        payload = self.normalize_payload(task)
        artifact = create_artifact(
            artifact_type=self.ARTIFACT_TYPE,
            room_source=self.ROOM_ID,
            data={
                "title": payload["title"],
                "payload": payload,
                "columns": payload["columns"],
                "rows": payload["rows"],
                "presentation": {
                    "renderer": "TableBlock",
                    "engine": "McDowell",
                    "math_engine": "KaTeX",
                    "payload_unchanged": True,
                },
            },
        )
        artifact.quality.validation_passed = bool(payload["columns"] and payload["rows"])
        artifact.quality.quality_score = 1.0 if artifact.quality.validation_passed else 0.0
        artifact.quality.confidence_score = 1.0 if artifact.quality.validation_passed else 0.0
        artifact.quality.completeness_score = 1.0 if artifact.quality.validation_passed else 0.0
        return artifact


ROOM = TableRoom()
