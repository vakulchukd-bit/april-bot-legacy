"""Shared File Delivery Room for Free and Premium SceneContracts.

This room creates FileDeliveryBlock renderer artifacts from already-produced
TableBlock, CodeBlock, long-form text, or authenticated saved asset references.
It does not generate source content, decide plan entitlement, or persist bytes;
executors persist the payload and attach authenticated dialogue-memory references.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict
import csv
import io
import json
import re
import uuid
from pathlib import PurePath

from blocks.C_ARTIFACT_CONTRACT import create_artifact

ROOM_ID = "C_FILE_DELIVERY_ROOM"
ARTIFACT_TYPE = "file"
RENDERER = "FileDeliveryBlock"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _safe_sheet_title(value: Any, fallback: str) -> str:
    title = re.sub(r"[\\/*?:\[\]]", " ", str(value or fallback)).strip().strip("'")
    title = re.sub(r"\s+", " ", title)[:31]
    return title or fallback[:31]


def _safe_xlsx_filename(value: Any) -> str:
    raw = str(value or "april-table").replace("\\", "/").split("/")[-1]
    if re.search(r"[А-Яа-яЁё]", raw):
        if re.search(r"менделеев|периодическ", raw, re.I):
            raw = "periodic_table"
        else:
            translit = {
                "а":"a", "б":"b", "в":"v", "г":"g", "д":"d", "е":"e", "ё":"e", "ж":"zh", "з":"z", "и":"i", "й":"i", "к":"k", "л":"l", "м":"m", "н":"n", "о":"o", "п":"p", "р":"r", "с":"s", "т":"t", "у":"u", "ф":"f", "х":"kh", "ц":"ts", "ч":"ch", "ш":"sh", "щ":"shch", "ъ":"", "ы":"y", "ь":"", "э":"e", "ю":"yu", "я":"ya",
            }
            raw = "".join(translit.get(char.lower(), char) for char in raw)
    raw = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw).strip("._")[:100]
    if not raw:
        raw = "april-table"
    if raw.lower().endswith(".csv"):
        raw = raw[:-4]
    if raw.lower().endswith(".xlsx"):
        return raw
    raw = re.sub(r"\.[A-Za-z0-9]{1,8}$", "", raw)
    return f"{raw or 'april-table'}.xlsx"


def normalize_table_export_payload(table: Any) -> dict[str, Any] | None:
    """Return a rectangular, renderer-independent table payload for XLSX export."""
    source = _object(table)
    nested = source.get("payload") if isinstance(source.get("payload"), dict) else {}
    data = dict(source)
    data.update(nested)
    export = data.get("export_payload") if isinstance(data.get("export_payload"), dict) else {}
    if export:
        merged = dict(data)
        merged.update(export)
        data = merged

    headers = data.get("headers") or data.get("columns") or data.get("column_headers") or []
    rows = data.get("rows") or data.get("data") or data.get("values") or data.get("records") or []
    if not isinstance(headers, (list, tuple)) or not isinstance(rows, (list, tuple)) or not rows:
        return None
    if not headers and not isinstance(rows[0], dict):
        return None

    keys: list[str] = []
    labels: list[str] = []
    for index, column in enumerate(headers):
        if isinstance(column, dict):
            key = str(column.get("key") or column.get("field") or column.get("id") or column.get("name") or column.get("header") or column.get("title") or f"column_{index + 1}")
            label = str(column.get("label") or column.get("title") or column.get("name") or column.get("header") or column.get("key") or key)
        else:
            label = str(column if column is not None else f"Column {index + 1}")
            key = label
        keys.append(key)
        labels.append(label[:320])

    normalized_rows: list[list[Any]] = []
    if rows and isinstance(rows[0], dict):
        if not keys:
            keys = list(dict.fromkeys(str(key) for row in rows if isinstance(row, dict) for key in row.keys()))
            labels = list(keys)
        for row in rows:
            if not isinstance(row, dict):
                continue
            normalized_rows.append([
                row.get(key, row.get(labels[index] if index < len(labels) else key, ""))
                for index, key in enumerate(keys)
            ])
    else:
        for row in rows:
            if isinstance(row, (list, tuple)):
                normalized_rows.append([row[index] if index < len(row) else "" for index in range(len(labels))])
    if not labels or not normalized_rows:
        return None

    additional = data.get("additional_sheets") or data.get("sheets") or []
    normalized_sheets: list[dict[str, Any]] = []
    if isinstance(additional, list):
        for sheet in additional[:20]:
            if not isinstance(sheet, dict):
                continue
            normalized_sheet = normalize_table_export_payload(sheet)
            if normalized_sheet:
                normalized_sheets.append(normalized_sheet)
    return {
        "title": str(data.get("title") or data.get("caption") or "April table")[:160],
        "headers": labels,
        "rows": normalized_rows,
        "additional_sheets": normalized_sheets,
    }


def table_payload_to_xlsx_bytes(table: Any) -> bytes:
    """Create a real XLSX workbook (not a CSV renamed to .xlsx)."""
    normalized = normalize_table_export_payload(table)
    if not normalized:
        raise ValueError("TABLE_EXPORT_HAS_NO_RECTANGULAR_DATA")
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
    except Exception as exc:  # pragma: no cover - dependency installation failure
        raise RuntimeError("OPENPYXL_DEPENDENCY_MISSING") from exc

    workbook = Workbook()

    def append_sheet(sheet: Any, title: str, *, first: bool = False) -> None:
        name = _safe_sheet_title(title, "Данные")
        if first:
            worksheet = workbook.active
            worksheet.title = name
        else:
            candidate = name
            suffix = 2
            while candidate in workbook.sheetnames:
                tag = f" {suffix}"
                candidate = f"{name[:31-len(tag)]}{tag}"
                suffix += 1
            worksheet = workbook.create_sheet(candidate)

        headers = sheet["headers"]
        rows = sheet["rows"]
        worksheet.append(headers)
        for row in rows:
            worksheet.append(list(row))
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions
        for cell in worksheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(fill_type="solid", fgColor="24445C")
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        worksheet.row_dimensions[1].height = 30
        for column_index, header in enumerate(headers, 1):
            sample_values = [str(header or "")]
            sample_values.extend(str(row[column_index - 1] or "") for row in rows[:250] if column_index - 1 < len(row))
            width = min(42, max(10, max((len(value) for value in sample_values), default=10) + 2))
            worksheet.column_dimensions[get_column_letter(column_index)].width = width
        # Treat all strings as literal cell values; user/model text must never
        # become an executable spreadsheet formula.
        for row in worksheet.iter_rows(min_row=2):
            for cell in row:
                if isinstance(cell.value, str):
                    cell.data_type = "s"
                    cell.alignment = Alignment(vertical="top", wrap_text=True)

    append_sheet(normalized, normalized["title"], first=True)
    for sheet in normalized["additional_sheets"]:
        append_sheet(sheet, sheet["title"])

    stream = io.BytesIO()
    workbook.save(stream)
    content = stream.getvalue()
    if not content.startswith(b"PK\x03\x04"):
        raise ValueError("XLSX_SIGNATURE_INVALID")
    return content


def csv_text_to_xlsx_bytes(text: str, *, title: str = "April data") -> bytes:
    """Convert a legacy CSV text payload into a genuine XLSX workbook."""
    source = str(text or "").lstrip("\ufeff")
    if not source.strip():
        raise ValueError("CSV_SOURCE_EMPTY")
    sample = source[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t|")
    except csv.Error:
        delimiter = "\t" if sample.count("\t") > max(sample.count(";"), sample.count(",")) else (";" if sample.count(";") > sample.count(",") else ",")
        rows = [row for row in csv.reader(io.StringIO(source), delimiter=delimiter) if any(str(cell).strip() for cell in row)]
    else:
        rows = [row for row in csv.reader(io.StringIO(source), dialect) if any(str(cell).strip() for cell in row)]
    if len(rows) < 2 or len(rows[0]) < 2:
        raise ValueError("CSV_SOURCE_NOT_TABULAR")
    headers = [str(cell).strip()[:320] or f"Column {index + 1}" for index, cell in enumerate(rows[0])]
    values = []
    for row in rows[1:1_000_001]:
        values.append([str(row[index]).strip()[:32000] if index < len(row) else "" for index in range(len(headers))])
    if not values:
        raise ValueError("CSV_SOURCE_HAS_NO_DATA_ROWS")
    return table_payload_to_xlsx_bytes({"title": title, "headers": headers, "rows": values})


def _object(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _identity(task: Dict[str, Any]) -> Dict[str, Any]:
    scene = _object(task.get("scene"))
    scene_id = str(task.get("scene_id") or scene.get("scene_id") or f"scene_{uuid.uuid4().hex[:12]}")
    turn_id = str(task.get("turn_id") or scene.get("turn_id") or f"turn_{uuid.uuid4().hex[:12]}")
    block_id = str(task.get("block_id") or scene.get("block_id") or f"file_{uuid.uuid4().hex[:12]}")
    return {"scene_id": scene_id, "turn_id": turn_id, "flow_id": str(task.get("flow_id") or scene.get("flow_id") or ""),
            "block_id": block_id, "render_id": str(task.get("render_id") or scene.get("render_id") or f"{block_id}:render")}


class FileDeliveryRoom:
    name = ROOM_ID
    room_type = "file_delivery"
    artifact_type = ARTIFACT_TYPE
    artifact_version = "1.0"
    web_space_ready = True
    renderer_safe = True
    continuity_safe = True
    orchestration_safe = True

    def can_handle(self, text: Any, context: Any) -> bool:
        return self.evaluate(text, context) > 0

    def evaluate(self, text: Any, context: Any) -> float:
        ctx = _object(context)
        semantic = _object(ctx.get("semantic"))
        requested = semantic.get("requested_outputs") or ctx.get("requested_outputs") or []
        return 1.0 if "file" in {str(item).lower() for item in requested if item} else 0.0

    def build_work_order(self, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        ctx = dict(context or {})
        return {"scene_id": ctx.get("scene_id"), "turn_id": ctx.get("turn_id"), "flow_id": ctx.get("flow_id"),
                "block_id": ctx.get("block_id"), "render_id": ctx.get("render_id"),
                "payload": deepcopy(ctx.get("file_payload") or ctx.get("payload") or {}),
                "title": ctx.get("title"), "filename": ctx.get("filename")}

    def process(self, task: Dict[str, Any]):
        source = dict(task or {})
        payload = _object(source.get("payload") or source.get("file_payload"))
        filename = str(payload.get("filename") or payload.get("name") or source.get("filename") or "april-file.txt").strip()
        filename = filename.replace("\\", "_").replace("/", "_").replace("\r", "").replace("\n", "")[:180] or "april-file.txt"
        mime = str(payload.get("mime_type") or source.get("mime_type") or "application/octet-stream")[:120]
        asset_ref = _object(payload.get("asset_ref") or source.get("asset_ref"))
        export_payload = _object(payload.get("export_payload") or source.get("export_payload"))
        content = payload.get("content") or payload.get("text") or payload.get("code") or source.get("content")
        # Keep raw binary data out of the SceneContract. A table may instead carry
        # its structured source for the existing protected XLSX export endpoint.
        if not asset_ref and not export_payload and not (isinstance(content, str) and content.strip()):
            raise ValueError("C_FILE_DELIVERY_ROOM requires content, asset_ref, or export_payload")
        identity = _identity(source)
        normalized = {"title": str(payload.get("title") or source.get("title") or filename),
                      "filename": filename, "mime_type": mime,
                      "size_bytes": int(payload.get("size_bytes") or 0),
                      "asset_ref": deepcopy(asset_ref), "export_payload": deepcopy(export_payload),
                      "source": str(payload.get("source") or "dialogue_asset"),
                      "description": str(payload.get("description") or source.get("description") or ""),
                      "scene": identity, "room": ROOM_ID, "payload_version": "april.file.v1"}
        if isinstance(content, str) and content.strip() and not asset_ref:
            normalized["content"] = content
        artifact = create_artifact(artifact_type=ARTIFACT_TYPE, room_source=ROOM_ID,
            data={"title": normalized["title"], "description": normalized["description"],
                  "payload": normalized, "renderer": RENDERER, "viewer": RENDERER,
                  "scene_id": identity["scene_id"], "turn_id": identity["turn_id"],
                  "flow_id": identity["flow_id"], "block_id": identity["block_id"],
                  "render_id": identity["render_id"], "text_companion_required": False})
        artifact.quality.validation_passed = True
        artifact.quality.quality_score = artifact.quality.confidence_score = artifact.quality.completeness_score = 1.0
        return artifact

    def execute(self, machine_request: Any):
        return self.process(machine_request) if isinstance(machine_request, dict) else None

    async def handle(self, user_id, text, context, run):
        return self.process(self.build_work_order(dict(context or {})))


ROOM = FileDeliveryRoom()



def build_memory_artifact_sources(render_blocks: Any) -> list[dict[str, Any]]:
    """Keep editable table/code sources when file-only UI hides their blocks.

    These are stored in a private structured-response field, never in the
    visible SceneContract. Binary payloads are removed; exact tabular values
    and source code remain available to Premium continuation/edit requests.
    """
    preserved: list[dict[str, Any]] = []

    def strip_binary(value: Any, depth: int = 0) -> Any:
        if depth > 10:
            return None
        if isinstance(value, dict):
            cleaned = {}
            for key, child in value.items():
                normalized = str(key).lower()
                if normalized in {"image_base64", "base64_data", "binary_payload", "raw_bytes", "content_base64", "file_base64", "b64_json"}:
                    continue
                if normalized in {"src", "data_uri", "image_data", "image_base64", "video_data", "audio_data"}:
                    if isinstance(child, str) and child.strip().lower().startswith("data:"):
                        continue
                cleaned[key] = strip_binary(child, depth + 1)
            return cleaned
        if isinstance(value, list):
            return [strip_binary(child, depth + 1) for child in value[:1000]]
        if isinstance(value, str) and value.strip().lower().startswith("data:"):
            return "[binary asset stored separately]"
        return value

    for block in render_blocks or []:
        if not isinstance(block, dict):
            continue
        kind = str(block.get("type") or block.get("artifact_type") or block.get("kind") or "").strip().lower()
        if kind not in {"table", "table_data", "code", "source_code"}:
            continue
        safe = strip_binary(deepcopy(block))
        try:
            if len(json.dumps(safe, ensure_ascii=False, default=str)) <= 24000:
                preserved.append(safe)
        except Exception:
            continue
        if len(preserved) >= 8:
            break
    return preserved


def _attach_premium_persisted_file_blocks(
    render_blocks: Any,
    output_asset_refs: Any,
    requested_outputs: Any,
    *,
    file_delivery_mode: str,
    language: str,
    message_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Premium-only delivery: expose only files verified in the asset store."""
    blocks = [deepcopy(item) for item in (render_blocks or []) if isinstance(item, dict)]
    requested = {str(item).strip().lower() for item in (requested_outputs or []) if str(item).strip()}
    if "file" not in requested:
        return blocks, []

    refs: list[dict[str, Any]] = []
    seen_refs: set[tuple[str, str]] = set()
    for raw_ref in output_asset_refs or []:
        if not isinstance(raw_ref, dict):
            continue
        ref = dict(raw_ref)
        filename = str(ref.get("filename") or "").strip()
        mime = str(ref.get("mime_type") or "").lower()
        digest = str(ref.get("sha256") or "")
        owner_message = str(ref.get("message_id") or message_id or "").strip()
        if filename.lower().endswith(".csv") or "csv" in mime:
            continue
        if str(ref.get("asset_role") or "april_output") != "april_output":
            continue
        if str(ref.get("output_type") or "").lower() not in {"code", "file", "spreadsheet"}:
            continue
        if not owner_message or not filename or not re.fullmatch(r"[a-f0-9]{64}", digest, re.I):
            continue
        key = (owner_message, digest.lower())
        if key in seen_refs:
            continue
        seen_refs.add(key)
        refs.append(ref)

    table_blocks = [
        block for block in blocks
        if str(block.get("type") or block.get("artifact_type") or "").strip().lower() == "table"
    ]
    code_blocks = [
        block for block in blocks
        if str(block.get("type") or block.get("artifact_type") or "").strip().lower() == "code"
    ]
    table_requested = "table" in requested or "spreadsheet" in requested
    code_requested = "code" in requested

    def is_xlsx(ref: dict[str, Any]) -> bool:
        filename = str(ref.get("filename") or "").lower()
        mime = str(ref.get("mime_type") or "").lower()
        return filename.endswith(".xlsx") and ("spreadsheetml" in mime or mime == XLSX_MIME)

    # A requested table must resolve to an actual XLSX workbook. Code assets
    # must retain their language-specific extension; all other files may be TXT
    # or another explicitly supported native format, but never CSV.
    selected: list[dict[str, Any]] = []
    table_refs = [ref for ref in refs if is_xlsx(ref)]
    code_refs = [ref for ref in refs if str(ref.get("output_type") or "").lower() == "code"]
    requires_table_asset = table_requested or bool(table_blocks)
    requires_code_asset = code_requested or bool(code_blocks)
    if requires_table_asset:
        selected.extend(table_refs)
    if requires_code_asset:
        selected.extend(code_refs)
    if not requires_table_asset and not requires_code_asset:
        selected.extend(refs)

    # Never let an unrelated TXT/other file satisfy a requested table or code
    # export. A file-only response is all-or-nothing for every requested family,
    # even when the provider forgot to emit the matching renderer block.
    required_family_missing = bool(
        (requires_table_asset and not table_refs) or (requires_code_asset and not code_refs)
    )
    if required_family_missing:
        selected = []

    cards: list[dict[str, Any]] = []
    for ref in selected[:8]:
        filename = str(ref.get("filename") or "april-output.txt")[:180]
        mime = str(ref.get("mime_type") or "text/plain; charset=utf-8")
        asset_ref = {
            "message_id": str(ref.get("message_id") or message_id),
            "sha256": str(ref.get("sha256") or ""),
            "filename": filename,
            "mime_type": mime,
            "size_bytes": int(ref.get("size_bytes") or 0),
        }
        cards.append({
            "type": "file",
            "artifact_type": "file",
            "renderer": RENDERER,
            "viewer": RENDERER,
            "source_room": ROOM_ID,
            "payload": {
                "title": filename,
                "filename": filename,
                "mime_type": mime,
                "size_bytes": asset_ref["size_bytes"],
                "asset_ref": asset_ref,
                "source": "premium_dialogue_asset",
                "description": "",
            },
        })

    # Remove unverified provider file blocks, legacy CSV blocks and links to
    # ephemeral sandbox paths. The authenticated asset card is the only route.
    cleaned: list[dict[str, Any]] = []
    for block in blocks:
        kind = str(block.get("type") or block.get("artifact_type") or "").strip().lower()
        if kind in {"file", "document", "file_card", "text_file", "code_file", "spreadsheet"}:
            continue
        if kind == "link":
            payload = block.get("payload") if isinstance(block.get("payload"), dict) else block
            url = str(payload.get("url") or payload.get("href") or payload.get("uri") or "")
            label = " ".join(str(payload.get(key) or "") for key in (
                "title", "label", "text", "description", "filename", "name"
            )).lower()
            looks_like_download = bool(re.search(
                r"(?:скача\w*|загруз\w*|download|attachment|\bfile\b|\bфайл\w*)",
                label, re.IGNORECASE,
            ))
            if url.lower().startswith("sandbox:") or "/mnt/data/" in url.lower() or looks_like_download:
                continue
        if kind in {"text", "markdown", "message", "message_text", "answer"}:
            targets = [block]
            if isinstance(block.get("payload"), dict):
                targets.append(block["payload"])
            for target in targets:
                for key in ("content", "text", "answer", "summary", "markdown"):
                    value = target.get(key)
                    if not isinstance(value, str):
                        continue
                    # Remove Markdown download links supplied by the model; only
                    # the persisted asset_ref card is a verified download route.
                    value = re.sub(
                        r"\[([^\]]*(?:скача\w*|загруз\w*|download|\bfile\b|файл\w*)[^\]]*)\]\([^)]+\)",
                        r"\1", value, flags=re.I,
                    )
                    value = re.sub(r"\[[^\]]*\]\(sandbox:[^)]+\)", "", value, flags=re.I)
                    value = re.sub(r"sandbox:/mnt/data/\S+", "", value, flags=re.I)
                    value = re.sub(r"(?i)\bCSV(?:-файл| файл| file)?\b", "Excel-файл", value)
                    target[key] = re.sub(r"[ \t]{2,}", " ", value).strip()
        cleaned.append(block)

    cleaned.extend(cards)
    delivered = cards
    if str(file_delivery_mode or "").lower() == "file_only" and delivered:
        cleaned = [block for block in cleaned if str(block.get("type") or block.get("artifact_type") or "").lower() not in {
            "code", "table", "text", "markdown", "message", "message_text", "answer"
        }]
        localized = {
            "ru": "Файл прикреплён к сообщению.",
            "uk": "Файл прикріплено до повідомлення.",
            "ua": "Файл прикріплено до повідомлення.",
            "en": "The file is attached to this message.",
        }
        notice = localized.get(str(language or "en").lower().split("-")[0], localized["en"])
        cleaned.insert(0, {"type": "text", "artifact_type": "text", "content": notice,
                           "renderer": "MessageTextBlock", "viewer": "MessageTextBlock"})
    return cleaned, delivered


def attach_file_delivery_blocks(
    render_blocks: Any,
    output_asset_refs: Any,
    requested_outputs: Any,
    *,
    file_delivery_mode: str = "with_inline",
    language: str = "en",
    message_id: str = "",
    require_persisted_asset: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Attach explicit file deliveries to existing blocks in one SceneContract.

    This adapter is plan-neutral. Free/Premium interpreters and executors decide
    their own limits; this function only binds already-persisted bytes or an
    existing structured table payload to the common FileDeliveryBlock renderer.
    """
    if require_persisted_asset:
        return _attach_premium_persisted_file_blocks(
            render_blocks, output_asset_refs, requested_outputs,
            file_delivery_mode=file_delivery_mode, language=language,
            message_id=message_id,
        )
    blocks = [deepcopy(item) for item in (render_blocks or []) if isinstance(item, dict)]
    refs = [dict(item) for item in (output_asset_refs or []) if isinstance(item, dict)]
    requested = {str(item).strip().lower() for item in (requested_outputs or []) if str(item).strip()}
    wants_file = "file" in requested
    if not wants_file:
        return blocks, []

    def block_payload(block: dict[str, Any]) -> dict[str, Any]:
        payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
        merged = dict(block)
        merged.update(payload)
        return merged

    file_blocks: list[dict[str, Any]] = []
    table_blocks = [
        block for block in blocks
        if str(block.get("type") or block.get("artifact_type") or "").strip().lower() == "table"
    ]
    # TableBlock has its own export control only when the table is also shown
    # inline. An explicit file-only request must instead produce a real XLSX
    # FileDeliveryBlock so the user receives one downloadable workbook.
    wants_inline_table = (
        "table" in requested and bool(table_blocks)
        and str(file_delivery_mode or "").lower() != "file_only"
    )
    existing_file_names = {
        str(block_payload(block).get("filename") or block_payload(block).get("name") or "").strip().casefold()
        for block in blocks if str(block.get("type") or block.get("artifact_type") or "").lower() in {"file", "document", "file_card", "text_file", "code_file"}
    }

    # Attach already-saved output bytes. Image payloads are intentionally excluded.
    saved_refs = [ref for ref in refs
                  if str(ref.get("asset_role") or "april_output") == "april_output"
                  and str(ref.get("output_type") or "").lower() in {"code", "file"}
                  and re.fullmatch(r"[a-f0-9]{64}", str(ref.get("sha256") or ""), re.I)]
    if str(file_delivery_mode or "").lower() == "file_only" and table_blocks:
        # When the table itself is the requested deliverable, the protected XLSX
        # export below is canonical. Do not also attach the provider's CSV asset
        # as a second, competing download card.
        saved_refs = [ref for ref in saved_refs
                      if not str(ref.get("filename") or "").lower().endswith(".csv")
                      and "text/csv" not in str(ref.get("mime_type") or "").lower()]
    if saved_refs:
        for block in blocks:
            block_type = str(block.get("type") or block.get("artifact_type") or "").lower()
            if block_type not in {"file", "document", "file_card", "text_file", "code_file"}:
                continue
            payload = block_payload(block)
            existing_ref = payload.get("asset_ref") if isinstance(payload.get("asset_ref"), dict) else {}
            existing_ref_is_valid = bool(
                str(existing_ref.get("message_id") or "").strip()
                and re.fullmatch(r"[a-f0-9]{64}", str(existing_ref.get("sha256") or ""), re.I)
            )
            # Inline text is useful for preview/share, but it is not a durable
            # mobile download route. Prefer the already-persisted, owner-scoped
            # asset reference whenever one can be matched to this file.
            if existing_ref_is_valid or isinstance(payload.get("export_payload"), dict):
                continue
            filename = str(payload.get("filename") or payload.get("name") or "").strip().casefold()
            ref = next((item for item in saved_refs if filename and str(item.get("filename") or "").strip().casefold() == filename), None)
            if ref is None and len(saved_refs) == 1:
                ref = saved_refs[0]
            if ref:
                asset_ref = {
                    "message_id": str(ref.get("message_id") or message_id),
                    "sha256": str(ref.get("sha256") or ""),
                    "filename": str(ref.get("filename") or payload.get("filename") or "april-output.txt"),
                    "mime_type": str(ref.get("mime_type") or "text/plain; charset=utf-8"),
                    "size_bytes": int(ref.get("size_bytes") or 0),
                }
                payload.update({"filename": asset_ref["filename"], "mime_type": asset_ref["mime_type"],
                                "size_bytes": asset_ref["size_bytes"], "asset_ref": asset_ref,
                                "source": "dialogue_asset"})
                block["payload"] = payload
                block["type"] = "file"
                block["artifact_type"] = "file"
                block["renderer"] = RENDERER
                block["viewer"] = RENDERER

        for ref in saved_refs[:8]:
            filename = str(ref.get("filename") or "april-output.txt")[:180]
            if filename.casefold() in existing_file_names:
                continue
            asset_ref = {
                "message_id": str(ref.get("message_id") or message_id),
                "sha256": str(ref.get("sha256") or ""),
                "filename": filename,
                "mime_type": str(ref.get("mime_type") or "text/plain; charset=utf-8"),
                "size_bytes": int(ref.get("size_bytes") or 0),
            }
            file_blocks.append({
                "type": "file", "artifact_type": "file", "renderer": RENDERER, "viewer": RENDERER,
                "source_room": ROOM_ID,
                "payload": {
                    "title": filename, "filename": filename,
                    "mime_type": asset_ref["mime_type"], "size_bytes": asset_ref["size_bytes"],
                    "asset_ref": asset_ref, "source": "dialogue_asset",
                    "description": "",
                },
            })
            existing_file_names.add(filename.casefold())

    # If the model produced both an inline table and a CSV file for the same
    # table request, fold the CSV rows into a second worksheet. This prevents
    # two competing downloads (CSV + XLSX) and preserves the full row dataset.
    csv_blocks_to_remove: set[int] = set()
    table_extra_sheets: list[dict[str, Any]] = []
    if table_blocks:
        for file_block in blocks:
            file_type = str(file_block.get("type") or file_block.get("artifact_type") or "").strip().lower()
            if file_type not in {"file", "document", "file_card", "text_file"}:
                continue
            file_payload = block_payload(file_block)
            filename_hint = str(file_payload.get("filename") or file_payload.get("name") or "").strip().lower()
            mime_hint = str(file_payload.get("mime_type") or file_payload.get("content_type") or "").strip().lower()
            if not (filename_hint.endswith(".csv") or "text/csv" in mime_hint or "application/csv" in mime_hint):
                continue
            csv_content = file_payload.get("content") or file_payload.get("text")
            if not isinstance(csv_content, str) or not csv_content.strip():
                continue
            try:
                csv_text = csv_content.lstrip("\ufeff")
                sample = csv_text[:4096]
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=";\t,|")
                except csv.Error:
                    dialect = csv.excel
                    dialect.delimiter = ";" if ";" in sample else ","
                csv_rows = list(csv.reader(io.StringIO(csv_text), dialect))
                csv_rows = [row for row in csv_rows if any(str(cell).strip() for cell in row)]
                if len(csv_rows) < 2 or len(csv_rows[0]) < 2:
                    continue
                csv_headers = [str(cell).strip()[:320] for cell in csv_rows[0]]
                csv_data = [
                    [str(row[index]).strip()[:32000] if index < len(row) else "" for index in range(len(csv_headers))]
                    for row in csv_rows[1:10001]
                ]
                if not csv_data:
                    continue
                sheet_title = "Все элементы" if any("атом" in h.lower() or "элемент" in h.lower() for h in csv_headers) else "Полные данные"
                table_extra_sheets.append({"title": sheet_title, "headers": csv_headers, "rows": csv_data})
                csv_blocks_to_remove.add(id(file_block))
            except Exception:
                # An unparseable CSV remains a separate file; never discard its content.
                continue

        if table_extra_sheets:
            primary_table = table_blocks[0]
            primary_payload = block_payload(primary_table)
            existing_sheets = primary_payload.get("additional_sheets")
            combined_sheets = list(existing_sheets) if isinstance(existing_sheets, list) else []
            known_sheet_names = {str(item.get("title") or "").casefold() for item in combined_sheets if isinstance(item, dict)}
            for sheet in table_extra_sheets:
                if str(sheet.get("title") or "").casefold() not in known_sheet_names:
                    combined_sheets.append(sheet)
                    known_sheet_names.add(str(sheet.get("title") or "").casefold())
            primary_table["additional_sheets"] = combined_sheets
            primary_table_payload = primary_table.get("payload") if isinstance(primary_table.get("payload"), dict) else {}
            primary_table_payload["additional_sheets"] = combined_sheets
            primary_table["payload"] = primary_table_payload
            blocks = [item for item in blocks if id(item) not in csv_blocks_to_remove]

            # Keep the visible response accurate after replacing the CSV card
            # with a single Excel workbook.
            language_key = str(language or "en").lower().split("-")[0]
            csv_replacements = {
                "ru": [(r"CSV[- ]файл", "Excel-файл"), (r"CSV", "Excel")],
                "ua": [(r"CSV[- ]файл", "Excel-файл"), (r"CSV", "Excel")],
                "uk": [(r"CSV[- ]файл", "Excel-файл"), (r"CSV", "Excel")],
                "en": [(r"CSV\s+file", "Excel workbook"), (r"CSV", "Excel")],
                "es": [(r"archivo\s+CSV", "libro de Excel"), (r"CSV", "Excel")],
                "de": [(r"CSV-Datei", "Excel-Datei"), (r"CSV", "Excel")],
                "fr": [(r"fichier\s+CSV", "classeur Excel"), (r"CSV", "Excel")],
                "it": [(r"file\s+CSV", "file Excel"), (r"CSV", "Excel")],
                "pl": [(r"plik\s+CSV", "plik Excel"), (r"CSV", "Excel")],
                "pt": [(r"arquivo\s+CSV", "arquivo Excel"), (r"CSV", "Excel")],
                "nl": [(r"CSV-bestand", "Excel-bestand"), (r"CSV", "Excel")],
            }
            replacements = csv_replacements.get(language_key, [(r"CSV", "Excel")])
            for text_block in blocks:
                if str(text_block.get("type") or text_block.get("artifact_type") or "").strip().lower() not in {"text", "markdown", "message", "message_text", "answer"}:
                    continue
                targets = [text_block]
                nested_payload = text_block.get("payload")
                if isinstance(nested_payload, dict):
                    targets.append(nested_payload)
                for target in targets:
                    for text_key in ("content", "text", "answer", "summary"):
                        current_text = target.get(text_key)
                        if not isinstance(current_text, str) or "csv" not in current_text.lower():
                            continue
                        for pattern, replacement in replacements:
                            current_text = re.sub(pattern, replacement, current_text, flags=re.IGNORECASE)
                        target[text_key] = current_text

    # A file-only table request uses the protected XLSX endpoint. When the user
    # also requested an inline table, TableBlock itself owns the same XLSX
    # download/share actions, so a second FileDeliveryBlock would be a duplicate.
    for block in blocks:
        block_type = str(block.get("type") or block.get("artifact_type") or "").strip().lower()
        if block_type != "table":
            continue
        table = block_payload(block)
        headers = table.get("headers") or table.get("columns") or table.get("column_headers") or []
        rows = table.get("rows") or table.get("data") or table.get("values") or []
        if not isinstance(headers, list) or not isinstance(rows, list) or not rows:
            continue
        # Match TableBlock's structural normalization so the existing XLSX
        # endpoint receives string headers and rectangular array rows even when
        # the model supplied column descriptors or object-shaped records.
        column_keys: list[str] = []
        normalized_headers: list[str] = []
        for index, column in enumerate(headers):
            if isinstance(column, dict):
                key = str(column.get("key") or column.get("field") or column.get("id") or column.get("name") or column.get("header") or column.get("title") or column.get("label") or f"column_{index + 1}")
                label = str(column.get("label") or column.get("title") or column.get("name") or column.get("header") or column.get("key") or column.get("field") or column.get("id") or f"Column {index + 1}")
            else:
                label = str(column if column is not None else f"Column {index + 1}")
                key = label
            column_keys.append(key)
            normalized_headers.append(label)
        if isinstance(rows[0], dict):
            if not column_keys:
                seen_keys: list[str] = []
                for row in rows:
                    if isinstance(row, dict):
                        for key in row.keys():
                            key_text = str(key)
                            if key_text not in seen_keys:
                                seen_keys.append(key_text)
                column_keys = seen_keys
                normalized_headers = list(seen_keys)
            normalized_rows = [
                [row.get(key, row.get(normalized_headers[index] if index < len(normalized_headers) else key, "")) if isinstance(row, dict) else ""
                 for index, key in enumerate(column_keys)]
                for row in rows
            ]
        elif isinstance(rows[0], list):
            normalized_rows = [
                [row[index] if index < len(row) else "" for index in range(len(normalized_headers))]
                for row in rows if isinstance(row, list)
            ]
            if not normalized_headers and normalized_rows:
                width = max(len(row) for row in normalized_rows)
                normalized_headers = [f"Column {index + 1}" for index in range(width)]
                normalized_rows = [row + [""] * (width - len(row)) for row in normalized_rows]
        else:
            continue
        if not normalized_headers or not normalized_rows:
            continue
        if wants_inline_table:
            # The visible TableBlock has a built-in XLSX export menu. Keeping an
            # extra FileDeliveryBlock here would create a second, inconsistent file.
            continue
        default_table_title = "Таблица" if str(language or "").lower().startswith(("ru", "uk", "ua")) else "April table"
        title = str(table.get("title") or table.get("caption") or default_table_title)[:120]
        filename = re.sub(r"[^\w.-]+", "_", title, flags=re.UNICODE).strip("._")[:90] or "april-table"
        filename = filename if filename.lower().endswith(".xlsx") else f"{filename}.xlsx"
        if filename.casefold() in existing_file_names:
            continue
        file_blocks.append({
            "type": "file", "artifact_type": "file", "renderer": RENDERER, "viewer": RENDERER,
            "source_room": ROOM_ID,
            "payload": {
                "title": title, "filename": filename,
                "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "source": "table_export",
                "description": "",
                "export_payload": {
                    "title": title,
                    "headers": normalized_headers,
                    "rows": normalized_rows,
                    "additional_sheets": table.get("additional_sheets") if isinstance(table.get("additional_sheets"), list) else [],
                },
                # Keep the table's typed source beside the file so later Premium
                # turns can continue editing/reusing the same table branch even
                # though file_only removes the visible TableBlock.
                "source_artifacts": [{
                    "type": "table", "title": title,
                    "headers": normalized_headers, "rows": normalized_rows,
                    "additional_sheets": table.get("additional_sheets") if isinstance(table.get("additional_sheets"), list) else [],
                }],
            },
        })
        existing_file_names.add(filename.casefold())

    # Code requested as a file must be a real downloadable source file, not only
    # an inline CodeBlock. Preserve the requested language and choose a safe,
    # conventional extension without changing the source text.
    code_blocks = [
        block for block in blocks
        if str(block.get("type") or block.get("artifact_type") or "").strip().lower() == "code"
    ]
    for code_block in code_blocks:
        code_payload = block_payload(code_block)
        code_text = next((str(code_payload.get(key) or "") for key in ("code", "source_code", "source", "content", "text")
                          if str(code_payload.get(key) or "").strip()), "")
        if not code_text:
            continue
        language_key = str(code_payload.get("language") or code_block.get("language") or "text").strip().lower()
        extensions = {
            "python": (".py", "text/x-python"), "py": (".py", "text/x-python"),
            "javascript": (".js", "text/javascript"), "js": (".js", "text/javascript"),
            "typescript": (".ts", "text/typescript"), "ts": (".ts", "text/typescript"),
            "tsx": (".tsx", "text/typescript"), "jsx": (".jsx", "text/javascript"),
            "json": (".json", "application/json"), "html": (".html", "text/html"),
            "css": (".css", "text/css"), "sql": (".sql", "application/sql"),
            "bash": (".sh", "text/x-shellscript"), "shell": (".sh", "text/x-shellscript"),
            "yaml": (".yml", "application/yaml"), "yml": (".yml", "application/yaml"),
            "xml": (".xml", "application/xml"), "markdown": (".md", "text/markdown"),
        }
        extension, mime_type = extensions.get(language_key, (".txt", "text/plain; charset=utf-8"))
        preferred_name = str(code_payload.get("filename") or code_block.get("filename") or "").strip()
        safe_name = re.sub(r"[^\w.-]+", "_", preferred_name, flags=re.UNICODE).strip("._")[:90]
        filename = safe_name or f"april_code{extension}"
        if not filename.lower().endswith(extension):
            filename = re.sub(r"\.[A-Za-z0-9]{1,8}$", "", filename) + extension
        if filename.casefold() in existing_file_names:
            continue
        file_blocks.append({
            "type": "file", "artifact_type": "file", "renderer": RENDERER, "viewer": RENDERER,
            "source_room": ROOM_ID,
            "payload": {
                "title": str(code_payload.get("title") or "Code file")[:120],
                "filename": filename, "mime_type": mime_type,
                "content": code_text, "source": "code_block_export", "description": "",
                "source_artifacts": [{
                    "type": "code", "language": language_key,
                    "filename": filename, "code": code_text,
                }],
            },
        })
        existing_file_names.add(filename.casefold())

    # When the user explicitly asks for a long answer as a file, create a Markdown
    # document from the complete assistant text. Tables and code are handled by
    # their typed exporters above, so they are not flattened into a text document.
    if not table_blocks and not code_blocks and not any(
        str(block.get("type") or block.get("artifact_type") or "").strip().lower() == "file"
        and any(str((block.get("payload") or {}).get(key) or "").strip() for key in ("content", "text", "code"))
        for block in blocks
    ):
        text_candidates: list[str] = []
        for text_block in blocks:
            if str(text_block.get("type") or text_block.get("artifact_type") or "").strip().lower() not in {"text", "markdown", "message", "message_text", "answer"}:
                continue
            text_payload = block_payload(text_block)
            candidate = next((str(text_payload.get(key) or "") for key in ("content", "markdown", "text", "answer")
                              if str(text_payload.get(key) or "").strip()), "")
            if candidate.strip():
                text_candidates.append(candidate)
        long_text = max(text_candidates, key=len) if text_candidates else ""
        if len(long_text.strip()) >= 500:
            filename = "april_answer.md"
            if filename.casefold() not in existing_file_names:
                file_blocks.append({
                    "type": "file", "artifact_type": "file", "renderer": RENDERER, "viewer": RENDERER,
                    "source_room": ROOM_ID,
                    "payload": {
                        "title": "April answer", "filename": filename,
                        "mime_type": "text/markdown; charset=utf-8",
                        "content": long_text, "source": "long_text_export", "description": "",
                        "source_artifacts": [{
                            "type": "copy", "filename": filename,
                            "content": long_text, "text": long_text,
                        }],
                    },
                })
                existing_file_names.add(filename.casefold())

    # Existing File blocks may already contain the bytes inline or a saved ref.
    for block in blocks:
        block_type = str(block.get("type") or block.get("artifact_type") or "").lower()
        if block_type not in {"file", "document", "file_card", "text_file", "code_file"}:
            continue
        payload = block_payload(block)
        filename = str(payload.get("filename") or payload.get("name") or "").strip()
        if isinstance(payload.get("asset_ref"), dict) or isinstance(payload.get("export_payload"), dict) or any(
            str(payload.get(key) or "").strip() for key in ("content", "text", "code", "data_uri", "file_data_uri", "download_url", "file_url")
        ):
            block["type"] = "file"
            block["artifact_type"] = "file"
            block["renderer"] = RENDERER
            block["viewer"] = RENDERER
            block.setdefault("source_room", ROOM_ID)

    blocks.extend(file_blocks)
    def has_downloadable_source(block: dict[str, Any]) -> bool:
        payload = block_payload(block)
        asset_ref = payload.get("asset_ref") if isinstance(payload.get("asset_ref"), dict) else {}
        if asset_ref.get("message_id") and re.fullmatch(r"[a-f0-9]{64}", str(asset_ref.get("sha256") or ""), re.I):
            return True
        export = payload.get("export_payload") if isinstance(payload.get("export_payload"), dict) else {}
        headers = export.get("headers") or export.get("columns")
        rows = export.get("rows") or export.get("data")
        if isinstance(headers, list) and headers and isinstance(rows, list) and rows:
            return True
        if any(str(payload.get(key) or "").strip() for key in ("content", "text", "code")):
            return True
        if str(payload.get("data_uri") or payload.get("file_data_uri") or "").startswith("data:"):
            return True
        return bool(re.match(r"^https://", str(payload.get("download_url") or payload.get("file_url") or ""), re.I))

    # Empty FileDeliveryBlock shells can coexist with a concrete artifact after
    # provider restoration (the mobile UI then displays a second, blank card).
    # Keep only file blocks that carry bytes, an authenticated asset reference,
    # an XLSX export payload, or a validated download URL.
    blocks = [
        block for block in blocks
        if str(block.get("type") or block.get("artifact_type") or "").lower() != "file"
        or has_downloadable_source(block)
    ]
    delivered_file_blocks = [
        block for block in blocks
        if str(block.get("type") or block.get("artifact_type") or "").lower() == "file"
        and has_downloadable_source(block)
    ]
    if str(file_delivery_mode or "").lower() == "file_only" and delivered_file_blocks:
        # Preserve the file's source in its own payload; do not duplicate huge
        # code/table data in the visible chat when the user explicitly asked for
        # a file only. Images and diagrams remain independent visual artifacts.
        blocks = [block for block in blocks if str(block.get("type") or block.get("artifact_type") or "").lower() not in {"code", "table"}]
        localized = {
            "ru": "Файл подготовлен.", "ua": "Файл підготовлено.", "uk": "Файл підготовлено.",
            "en": "The file is ready.", "fr": "Le fichier est prêt.", "de": "Die Datei ist fertig.",
            "es": "El archivo está listo.", "it": "Il file è pronto.", "pl": "Plik jest gotowy.",
            "pt": "O arquivo está pronto.", "nl": "Het bestand is klaar.",
        }
        notice = localized.get(str(language or "en").lower().split("-")[0], localized["en"])
        blocks = [block for block in blocks if str(block.get("type") or block.get("artifact_type") or "").lower() not in {"text", "markdown", "message", "message_text", "answer"}]
        blocks.insert(0, {"type": "text", "artifact_type": "text", "content": notice,
                          "renderer": "MessageTextBlock", "viewer": "MessageTextBlock"})
    return blocks, delivered_file_blocks
